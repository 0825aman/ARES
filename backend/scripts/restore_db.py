#!/usr/bin/env python3
"""restore_db.py — Restore MAAR SQLite database from a backup.

Restores a previously created backup over the target database file.
The backup file must be a valid SQLite database (validated before restore).

Usage:
    python scripts/restore_db.py --backup ./backups/maar_20261114_103000.db --target ./maar_dev.db --confirm

Options:
    --backup PATH   Path to the backup file to restore from. Required.
    --target PATH   Path to the target database to restore into.
                    Default: ./maar_dev.db
    --confirm       Required flag to prevent accidental overwrites.

WARNING: This will OVERWRITE the target database. Stop the MAAR application
before running this script to avoid data corruption.
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import datetime
from pathlib import Path


def is_valid_sqlite(path: Path) -> bool:
    """Return True if the file exists and is a valid SQLite database."""
    if not path.exists() or not path.is_file():
        return False
    try:
        conn = sqlite3.connect(str(path))
        conn.execute("SELECT 1")
        conn.close()
        return True
    except sqlite3.DatabaseError:
        return False


def restore(backup_path: str, target_path: str) -> None:
    backup = Path(backup_path).resolve()
    target = Path(target_path).resolve()

    if not backup.exists():
        print(f"ERROR: Backup file not found: {backup}", file=sys.stderr)
        sys.exit(1)

    if not is_valid_sqlite(backup):
        print(
            f"ERROR: Backup file is not a valid SQLite database: {backup}",
            file=sys.stderr,
        )
        sys.exit(1)

    backup_size_bytes = backup.stat().st_size
    backup_size_mb = backup_size_bytes / (1024 * 1024)

    print(f"Backup:      {backup}")
    print(f"  Size:      {backup_size_bytes:,} bytes ({backup_size_mb:.2f} MB)")
    print(f"Target:      {target}")

    if target.exists():
        target_size_bytes = target.stat().st_size
        print(f"  Current:   {target_size_bytes:,} bytes (will be overwritten)")
    else:
        print(f"  Current:   (does not exist — will be created)")

    print("Restoring...")

    # Create target parent directory if needed
    target.parent.mkdir(parents=True, exist_ok=True)

    backup_conn = sqlite3.connect(str(backup))
    target_conn = sqlite3.connect(str(target))
    try:
        backup_conn.backup(target_conn)
    finally:
        backup_conn.close()
        target_conn.close()

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    final_size = target.stat().st_size
    print(f"Restore complete.")
    print(f"  Timestamp: {timestamp}")
    print(f"  Target:    {target} ({final_size:,} bytes)")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Restore the MAAR SQLite database from a backup file."
    )
    parser.add_argument(
        "--backup",
        required=True,
        help="Path to the backup file to restore from.",
    )
    parser.add_argument(
        "--target",
        default="./maar_dev.db",
        help="Path to the target database to restore into (default: ./maar_dev.db)",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Required: confirm you want to overwrite the target database.",
    )
    args = parser.parse_args()

    if not args.confirm:
        print(
            "ERROR: --confirm flag is required to prevent accidental restores.\n"
            "       This operation will OVERWRITE your target database.\n"
            "       Stop the MAAR application before restoring.\n"
            "       Re-run with --confirm to proceed.",
            file=sys.stderr,
        )
        sys.exit(1)

    restore(args.backup, args.target)


if __name__ == "__main__":
    main()
