#!/usr/bin/env python3
import argparse
import os
import re
import shutil
from typing import Dict, Tuple


def default_flow_root() -> str:
    # default to ./Flow relative to cwd if exists, else ~/Flow
    cwd_flow = os.path.abspath(os.path.join(os.getcwd(), 'Flow'))
    if os.path.isdir(cwd_flow):
        return cwd_flow
    return os.path.expanduser('~/Flow')


def default_src_root() -> str:
    # default to ./@chat_history relative to cwd
    return os.path.abspath(os.path.join(os.getcwd(), '@chat_history'))


def parse_folder_date(name: str) -> Tuple[str, str]:
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})_", name)
    if not m:
        return ("", "")
    yyyy, mm, dd = m.groups()
    return (f"{yyyy}{mm}", f"{yyyy}-{mm}-{dd}")


def move_exported_to_flow(src_root: str, flow_root: str) -> Dict[str, int]:
    moved = 0
    skipped = 0
    errors = 0
    if not os.path.isdir(src_root):
        return {'moved': 0, 'skipped': 0, 'errors': 0}
    for name in sorted(os.listdir(src_root)):
        src_path = os.path.join(src_root, name)
        if not os.path.isdir(src_path):
            continue
        ym, date = parse_folder_date(name)
        if not ym:
            skipped += 1
            continue
        dest_dir = os.path.join(flow_root, ym, date)
        os.makedirs(dest_dir, exist_ok=True)
        dest_path = os.path.join(dest_dir, name)
        base = dest_path
        k = 1
        while os.path.exists(dest_path):
            dest_path = base + f"-{k}"
            k += 1
        try:
            shutil.move(src_path, dest_path)
            moved += 1
        except Exception:
            errors += 1
    return {'moved': moved, 'skipped': skipped, 'errors': errors}


def organize_chats_subfolders(flow_root: str) -> Dict[str, int]:
    totals: Dict[str, int] = {}
    if not os.path.isdir(flow_root):
        return {'total_dates_updated': 0, 'moved_by_date': totals}
    for ym in sorted(os.listdir(flow_root)):
        ym_path = os.path.join(flow_root, ym)
        if not os.path.isdir(ym_path) or not re.fullmatch(r"\d{6}", ym):
            continue
        for date in sorted(os.listdir(ym_path)):
            date_path = os.path.join(ym_path, date)
            if not os.path.isdir(date_path) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
                continue
            chats_dir = os.path.join(date_path, 'chats')
            os.makedirs(chats_dir, exist_ok=True)
            moved = 0
            for name in os.listdir(date_path):
                if name == 'chats':
                    continue
                src = os.path.join(date_path, name)
                if not os.path.isdir(src):
                    continue
                if not name.startswith(date + '_'):
                    continue
                dest = os.path.join(chats_dir, name)
                base = dest
                k = 1
                while os.path.exists(dest):
                    dest = base + f"-{k}"
                    k += 1
                shutil.move(src, dest)
                moved += 1
            if moved:
                totals[os.path.join(ym, date)] = moved
    return {
        'total_dates_updated': len(totals),
        'moved_by_date': totals,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description='Move exported chats to Flow and organize into chats/ subfolders.')
    parser.add_argument('--src', default=default_src_root(), help='Source folder (exported @chat_history)')
    parser.add_argument('--flow', default=default_flow_root(), help='Flow root folder')
    args = parser.parse_args()

    move_stats = move_exported_to_flow(args.src, args.flow)
    org_stats = organize_chats_subfolders(args.flow)
    print({'move': move_stats, 'organize': org_stats, 'flow_root': args.flow})


if __name__ == '__main__':
    main()


