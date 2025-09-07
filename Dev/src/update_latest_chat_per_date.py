#!/usr/bin/env python3
import argparse
import datetime
import os
import re
import shutil
import sqlite3
import sys
import urllib.parse
import yaml
from typing import Any, Dict, List, Tuple


def default_flow_root() -> str:
    cwd_flow = os.path.abspath(os.path.join(os.getcwd(), 'Flow'))
    if os.path.isdir(cwd_flow):
        return cwd_flow
    return os.path.expanduser('~/Flow')


def default_db_path() -> str:
    if sys.platform == 'darwin':
        return os.path.expanduser('~/Library/Application Support/Cursor/User/globalStorage/state.vscdb')
    if sys.platform.startswith('win'):
        appdata = os.environ.get('APPDATA') or os.path.expanduser('~\\AppData\\Roaming')
        return os.path.join(appdata, 'Cursor', 'User', 'globalStorage', 'state.vscdb')
    xdg = os.environ.get('XDG_CONFIG_HOME') or os.path.expanduser('~/.config')
    return os.path.join(xdg, 'Cursor', 'User', 'globalStorage', 'state.vscdb')


def connect_db_readonly(db_path: str) -> sqlite3.Connection:
    uri = f"file:{urllib.parse.quote(db_path)}?mode=ro"
    return sqlite3.connect(uri, uri=True)


def text_of(content: Any) -> str:
    if isinstance(content, (dict, list)):
        import json
        return json.dumps(content, ensure_ascii=False, indent=2)
    return '' if content is None else str(content)


def derive_title20(s: str) -> str:
    s = (s or '').strip()
    s = re.sub(r"\s+", " ", s)[:20]
    for a, b in [('/', '／'), ('\\', '＼'), (':', '：'), ('*', '＊'), ('?', '？'), ('"', '”'), ('<', '＜'), ('>', '＞'), ('|', '｜')]:
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


def group_messages(bubbles: List[Tuple[str, str]]) -> List[Dict[str, Any]]:
    import json
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


def fetch_threads_for_date(conn: sqlite3.Connection, target_date: str) -> List[Tuple[str, int]]:
    y, m, d = map(int, target_date.split('-'))
    start = datetime.datetime(y, m, d, 0, 0, 0)
    end = start + datetime.timedelta(days=1)
    start_ms = int(start.timestamp() * 1000)
    end_ms = int(end.timestamp() * 1000)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT substr(key, length('composerData:')+1) AS cid,
               json_extract(value,'$.createdAt') AS createdAt
        FROM cursorDiskKV
        WHERE key LIKE 'composerData:%'
          AND json_extract(value,'$.createdAt') >= ?
          AND json_extract(value,'$.createdAt') < ?
        ORDER BY createdAt ASC
        """,
        (start_ms, end_ms),
    )
    return [(row[0], int(row[1])) for row in cur.fetchall()]


def fetch_bubbles(conn: sqlite3.Connection, cid: str) -> List[Tuple[str, str]]:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT key, value FROM cursorDiskKV
        WHERE key LIKE ?
        ORDER BY COALESCE(json_extract(value,'$.createdAt'),0) ASC
        """,
        (f"bubbleId:{cid}:%",),
    )
    return cur.fetchall()


def write_chat_yaml(folder: str, cid: str, created_dt: str, title20: str, grouped: List[Dict[str, Any]]) -> None:
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


def main() -> None:
    parser = argparse.ArgumentParser(description='Rebuild chats for a specific date (clear & re-extract).')
    parser.add_argument('--date', required=True, help='Target date YYYY-MM-DD (local)')
    parser.add_argument('--db', default=default_db_path(), help='Path to Cursor state.vscdb')
    parser.add_argument('--flow', default=default_flow_root(), help='Flow root folder')
    args = parser.parse_args()

    target_date = args.date
    ym = target_date[:4] + target_date[5:7]
    date_path = os.path.join(args.flow, ym, target_date)
    chats_dir = os.path.join(date_path, 'chats')
    os.makedirs(chats_dir, exist_ok=True)

    # 1) clear existing chats content
    removed = 0
    for name in os.listdir(chats_dir):
        p = os.path.join(chats_dir, name)
        if os.path.isdir(p):
            shutil.rmtree(p)
            removed += 1
        else:
            try:
                os.remove(p)
                removed += 1
            except Exception:
                pass

    # 2) query threads for date and rebuild folders
    conn = connect_db_readonly(args.db)
    threads = fetch_threads_for_date(conn, target_date)
    created = 0
    for cid, created_ms in threads:
        dt = datetime.datetime.fromtimestamp(created_ms / 1000).strftime('%Y-%m-%d_%H-%M-%S')
        time_part = dt.split('_')[1]
        bubbles = fetch_bubbles(conn, cid)
        # derive title
        head = ''
        for _, v in bubbles:
            try:
                import json
                o = json.loads(v)
            except Exception:
                o = {"content": v}
            s = text_of(o.get('content') or o.get('text') or o.get('richText') or o.get('message'))
            if s.strip():
                head = s.strip()
                break
        title20 = derive_title20(head)
        if title20 == 'untitled':
            continue
        folder_name = f"{target_date}_{time_part}_{title20}_{cid[:8]}"
        folder = os.path.join(chats_dir, folder_name)
        grouped = group_messages(bubbles)
        write_chat_yaml(folder, cid, dt, title20, grouped)
        created += 1

    print({'date': target_date, 'removed': removed, 'created': created, 'path': date_path})


if __name__ == '__main__':
    main()


