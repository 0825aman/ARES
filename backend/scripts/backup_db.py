#!/usr/bin/env python3
"""backup_db.py — SQLite hot backup for MAAR.

Creates a consistent point-in-time backup of the SQLite database using the
sqlite3 Online Backup API (safe while the application is running).

Usage:
    python scripts/backup_db.py --source ./maar_dev.db --dest ./backups/maar_backup.db
    python scripts/backup_db.py  # uses defaults from .env / defaults

Options:
    --source PATH   Path to the source SQLite database file.
                    Default: ./maar_dev.db
    --dest PATH     Path to write the backup file.
                    Default: ./backups/maar_<YYYYMMDD_HHMMSS>.db
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path


def backup(source_path: str, dest_path: str) -> None:
    source = Path(source_path).resolve()
    dest = Path(dest_path).resolve()

    if not source.exists():
        print(f"ERROR: Source database not found: {source}", file=sys.stderr)
        sys.exit(1)

    if not source.is_file():
        print(f"ERROR: Source path is not a file: {source}", file=sys.stderr)
        sys.exit(1)

    # Create destination directory if needed
    dest.parent.mkdir(parents=True, exist_ok=True)

    print(f"Source:      {source}")
    print(f"Destination: {dest}")
    print("Starting backup...")

    source_conn = sqlite3.connect(str(source))
    dest_conn = sqlite3.connect(str(dest))
    try:
        source_conn.backup(dest_conn)
    finally:
        source_conn.close()
        dest_conn.close()

    size_bytes = dest.stat().st_size
    size_mb = size_bytes / (1024 * 1024)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(f"Backup complete.")
    print(f"  Size:      {size_bytes:,} bytes ({size_mb:.2f} MB)")
    print(f"  Timestamp: {timestamp}")
    print(f"  Path:      {dest}")


def main() -> None:
    default_dest = f"./backups/maar_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"

    parser = argparse.ArgumentParser(
        description="Create a consistent SQLite backup of the MAAR database."
    )
    parser.add_argument(
        "--source",
        default="./maar_dev.db",
        help="Path to the source SQLite database file (default: ./maar_dev.db)",
    )
    parser.add_argument(
        "--dest",
        default=default_dest,
        help=f"Path to write the backup file (default: {default_dest})",
    )
    args = parser.parse_args()
    backup(args.source, args.dest)


if __name__ == "__main__":
    main()
