#!/usr/bin/env python3
import argparse
import subprocess
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description='Rebuild chats for multiple dates (loop).')
    parser.add_argument('--dates', nargs='+', required=True, help='List of dates YYYY-MM-DD')
    parser.add_argument('--db', default=None, help='Optional DB path override')
    parser.add_argument('--flow', default=None, help='Optional Flow root override')
    args = parser.parse_args()

    updated = 0
    for d in args.dates:
        cmd = [
            sys.executable,
            'update_latest_chat_per_date.py',
            '--date', d,
        ]
        if args.db:
            cmd += ['--db', args.db]
        if args.flow:
            cmd += ['--flow', args.flow]
        print('Running:', ' '.join(cmd))
        subprocess.run(cmd, check=False)
        updated += 1
    print({'dates_processed': updated})


if __name__ == '__main__':
    main()


