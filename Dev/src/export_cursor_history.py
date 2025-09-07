#!/usr/bin/env python3
import argparse
import datetime
import json
import os
import re
import sqlite3
import sys
import time
import urllib.parse
from typing import Any, Dict, List, Tuple


def default_db_path() -> str:
    """Return a cross-platform default path to Cursor state.vscdb."""
    if sys.platform == 'darwin':
        # macOS
        return os.path.expanduser('~/Library/Application Support/Cursor/User/globalStorage/state.vscdb')
    if sys.platform.startswith('win'):
        # Windows
        appdata = os.environ.get('APPDATA') or os.path.expanduser('~\\AppData\\Roaming')
        return os.path.join(appdata, 'Cursor', 'User', 'globalStorage', 'state.vscdb')
    # Linux / others
    xdg = os.environ.get('XDG_CONFIG_HOME') or os.path.expanduser('~/.config')
    return os.path.join(xdg, 'Cursor', 'User', 'globalStorage', 'state.vscdb')


def connect_db_readonly(db_path: str) -> sqlite3.Connection:
    uri = f"file:{urllib.parse.quote(db_path)}?mode=ro"
    return sqlite3.connect(uri, uri=True)


def fetch_all_threads(conn: sqlite3.Connection, order_desc: bool) -> List[Tuple[str, int]]:
    order = "DESC" if order_desc else "ASC"
    cur = conn.cursor()
    query = (
        f"""
        SELECT substr(key, length('composerData:')+1) AS cid,
               json_extract(value,'$.createdAt') AS createdAt
        FROM cursorDiskKV
        WHERE key LIKE 'composerData:%' AND json_extract(value,'$.createdAt') IS NOT NULL
        ORDER BY createdAt {order}
        """
    )
    cur.execute(query)
    return [(row[0], int(row[1])) for row in cur.fetchall()]


def text_of(content: Any) -> str:
    if isinstance(content, (dict, list)):
        return json.dumps(content, ensure_ascii=False, indent=2)
    return '' if content is None else str(content)


def fetch_bubbles(conn: sqlite3.Connection, cid: str) -> List[Tuple[str, str]]:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT key, value
        FROM cursorDiskKV
        WHERE key LIKE ?
        ORDER BY COALESCE(json_extract(value,'$.createdAt'),0) ASC
        """,
        (f"bubbleId:{cid}:%",),
    )
    return cur.fetchall()


def first_nonempty_content(bubbles: List[Tuple[str, str]]) -> str:
    for _, v in bubbles:
        try:
            o = json.loads(v)
        except Exception:
            o = {"content": v}
        s = text_of(o.get('content') or o.get('text') or o.get('richText') or o.get('message'))
        if s.strip():
            return s.strip()
    return ''


def derive_title20(s: str) -> str:
    s = (s or '').strip()
    s = re.sub(r"\s+", " ", s)[:20]
    for a, b in [
        ('/', '／'), ('\\', '＼'), (':', '：'), ('*', '＊'), ('?', '？'), ('"', '”'), ('<', '＜'), ('>', '＞'), ('|', '｜')
    ]:
        s = s.replace(a, b)
    return s or 'untitled'


def map_role(o: Dict[str, Any]) -> str:
    role_raw = o.get('role') or o.get('authorRole') or o.get('sender')
    if isinstance(role_raw, str):
        r = role_raw.lower()
        if r in ('user', 'human', 'client'):
            return 'user'
        if r in ('assistant', 'ai', 'agent', 'bot', 'model', 'system', 'tool'):
            return 'assistant'
    t = o.get('type')
    if isinstance(t, int):
        if t == 1:
            return 'user'
        if t == 2:
            return 'assistant'
    return 'other'


def group_messages_by_role(bubbles: List[Tuple[str, str]]) -> List[Dict[str, Any]]:
    grouped: List[Dict[str, Any]] = []
    for _, v in bubbles:
        try:
            o = json.loads(v)
        except Exception:
            o = {"content": v}
        s = text_of(o.get('content') or o.get('text') or o.get('richText') or o.get('message'))
        if not s.strip():
            continue
        role = map_role(o)
        if grouped and grouped[-1]['role'] == role:
            grouped[-1]['texts'].append(s)
        else:
            grouped.append({'role': role, 'texts': [s]})
    return grouped


def write_yaml(folder: str, cid: str, created_dt: str, title20: str, grouped: List[Dict[str, Any]]) -> None:
    os.makedirs(folder, exist_ok=True)
    p = os.path.join(folder, 'chat.yaml')
    with open(p, 'w', encoding='utf-8') as f:
        f.write('---\n')
        f.write(f"threadId: \"{cid}\"\n")
        f.write(f"created_at: \"{created_dt}\"\n")
        f.write(f"title20: \"{title20}\"\n")
        f.write("messages:\n")
        for g in grouped:
            f.write(f"  - role: \"{g['role']}\"\n")
            f.write("    content: |-\n")
            block = '\n\n'.join(g['texts']).rstrip('\n')
            for line in block.splitlines():
                f.write("      " + line + "\n")


def atomic_write_json(path: str, data: Any) -> None:
    tmp = path + ".tmp"
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def load_manifest(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {}
    try:
        return json.load(open(path, 'r', encoding='utf-8'))
    except Exception:
        return {}


def ensure_manifest(manifest_path: str, conn: sqlite3.Connection, order_desc: bool) -> Dict[str, Any]:
    manifest = load_manifest(manifest_path)
    if manifest.get('items'):
        return manifest
    items = []
    threads = fetch_all_threads(conn, order_desc=order_desc)
    for cid, created_ms in threads:
        items.append({
            'cid': cid,
            'createdAtMs': int(created_ms),
            'processed': False,
            'skipped': False,
            'folder': '',
        })
    manifest = {
        'order': 'desc' if order_desc else 'asc',
        'total': len(items),
        'items': items,
        'last_index': -1,
    }
    atomic_write_json(manifest_path, manifest)
    return manifest


def export_batch(
    conn: sqlite3.Connection,
    out_root: str,
    manifest_path: str,
    start_index: int,
    batch_size: int,
) -> Tuple[int, int]:
    manifest = load_manifest(manifest_path)
    items = manifest.get('items', [])
    end_index = min(len(items), start_index + batch_size)
    done = 0
    skipped = 0
    for idx in range(start_index, end_index):
        it = items[idx]
        if it.get('processed'):
            continue
        cid = it['cid']
        created_ms = it['createdAtMs']
        bubbles = fetch_bubbles(conn, cid)
        head = first_nonempty_content(bubbles)
        title20 = derive_title20(head)
        if title20 == 'untitled':
            it['processed'] = True
            it['skipped'] = True
            manifest['last_index'] = idx
            atomic_write_json(manifest_path, manifest)
            skipped += 1
            continue
        created_dt = datetime.datetime.fromtimestamp(int(created_ms) / 1000).strftime('%Y-%m-%d_%H-%M-%S')
        folder = os.path.join(out_root, f"{created_dt}_{title20}_{cid[:8]}")
        grouped = group_messages_by_role(bubbles)
        write_yaml(folder, cid, created_dt, title20, grouped)
        it['processed'] = True
        it['skipped'] = False
        it['folder'] = folder
        manifest['last_index'] = idx
        atomic_write_json(manifest_path, manifest)
        done += 1
        time.sleep(0.05)
    return done, skipped


def main() -> None:
    parser = argparse.ArgumentParser(description='Export Cursor chat history to YAML (grouped) in batches.')
    parser.add_argument('--db', default=default_db_path(), help='Path to Cursor state.vscdb')
    parser.add_argument('--out', default=os.path.abspath(os.path.join(os.getcwd(), '@chat_history')))
    parser.add_argument('--batch-size', type=int, default=50)
    parser.add_argument('--start-index', type=int, default=0)
    parser.add_argument('--order', choices=['desc', 'asc'], default='desc', help='desc=newest first (default)')
    parser.add_argument('--rescan', action='store_true', help='Rebuild manifest before exporting')
    parser.add_argument('--all', action='store_true', help='Process all threads in one go (ignores batch-size and start-index)')
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)
    manifest_path = os.path.join(args.out, 'export_manifest.json')

    conn = connect_db_readonly(args.db)
    if args.rescan or not os.path.exists(manifest_path):
        ensure_manifest(manifest_path, conn, order_desc=(args.order == 'desc'))

    if args.all:
        # Process all threads in one go
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        total_threads = len(manifest.get('threads', []))
        done, skipped = export_batch(conn, args.out, manifest_path, 0, total_threads)
        summary = {
            'mode': 'all',
            'total_threads': total_threads,
            'processed': done,
            'skipped': skipped,
            'manifest': manifest_path,
        }
    else:
        # Process in batches
        done, skipped = export_batch(conn, args.out, manifest_path, args.start_index, args.batch_size)
        summary = {
            'mode': 'batch',
            'start_index': args.start_index,
            'batch_size': args.batch_size,
            'processed': done,
            'skipped': skipped,
            'manifest': manifest_path,
        }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()


