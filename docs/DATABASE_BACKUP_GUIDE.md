# Database Backup and Restore Guide

## Overview

MAAR uses SQLite as its local database. SQLite is a single-file database, which makes
backup straightforward using the built-in Online Backup API. The backup is performed
while the application is running — no downtime is required.

---

## Backup

### Quick backup

From the `maar/backend/` directory:

```bash
python scripts/backup_db.py
```

This creates a timestamped backup in `./backups/maar_YYYYMMDD_HHMMSS.db`.

### Custom source and destination

```bash
python scripts/backup_db.py --source ./maar_dev.db --dest ./backups/my_backup.db
```

### Options

| Option     | Default                              | Description                            |
|------------|--------------------------------------|----------------------------------------|
| `--source` | `./maar_dev.db`                      | Path to the source SQLite database     |
| `--dest`   | `./backups/maar_YYYYMMDD_HHMMSS.db` | Path to write the backup file          |

### What the backup script does

- Uses `sqlite3.connect(source).backup(dest)` — the official SQLite Online Backup API.
- Safe to run while MAAR is running — no locks required.
- Creates the destination directory if it does not exist.
- Prints backup size and completion timestamp.

---

## Restore

> **WARNING:** Restoring will OVERWRITE the target database. Stop the MAAR
> application before restoring to avoid data corruption.

### Restore from backup

```bash
# Stop MAAR backend first, then:
python scripts/restore_db.py --backup ./backups/maar_20261114_103000.db --confirm
```

### Options

| Option      | Default          | Description                                              |
|-------------|------------------|----------------------------------------------------------|
| `--backup`  | (required)       | Path to the backup file to restore from                  |
| `--target`  | `./maar_dev.db`  | Path to the target database to restore into              |
| `--confirm` | (flag, required) | Required to prevent accidental overwrites                |

### What the restore script does

- Validates the backup file is a valid SQLite database before proceeding.
- Uses `sqlite3.connect(backup).backup(target)` for a consistent restore.
- Requires `--confirm` flag to prevent accidents.
- Prints file sizes before and after restore.

---

## Backup Recommendations

### Frequency

For a local development tool, back up before:

- Applying database migrations.
- Running destructive operations (bulk deletes, schema changes).
- Updating the MAAR application to a new version.

### Storage

Keep backups outside the project directory for safety:

```bash
python scripts/backup_db.py --dest ~/maar-backups/maar_$(date +%Y%m%d_%H%M%S).db
```

### Retention

There is no automatic retention management. Remove old backups manually or with a
simple script:

```bash
# Remove backups older than 30 days (macOS/Linux)
find ~/maar-backups/ -name "maar_*.db" -mtime +30 -delete
```

---

## Database Location

By default, MAAR creates its database at:

```
maar/backend/maar_dev.db
```

This path is controlled by the `DATABASE_URL` environment variable in `backend/.env`:

```env
DATABASE_URL=sqlite+aiosqlite:///./maar_dev.db
```

---

## Verifying a Backup

To verify that a backup file is valid:

```bash
sqlite3 ./backups/my_backup.db "SELECT count(*) FROM research_projects;"
```

Or open it in any SQLite browser tool (DB Browser for SQLite, DBeaver, etc.).

---

## Docker Volume Backups

When running MAAR in Docker (Phase 6 M6.7), the database is stored in a named volume
(`maar-db`). To back up from Docker:

```bash
# Copy the database file out of the container
docker compose cp backend:/app/maar_dev.db ./backups/maar_docker_$(date +%Y%m%d_%H%M%S).db
```

Refer to `docs/DOCKER_GUIDE.md` for more details on Docker volume management.
