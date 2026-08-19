# Backup & restore runbook (SQLite)

The app keeps state in SQLite databases under `data/` (jobs, users, glossary,
translation memory, usage, analytics, …). This is the procedure to back them up
consistently and restore them.

## What & how

`scripts/backup_db.py` snapshots **every `*.db` under `data/`** using SQLite's
online backup API — each copy is transactionally consistent even while the app
is writing (a plain `cp` of a live WAL database can be torn). The relative
folder layout is preserved.

```bash
# one-off backup into a timestamped folder (backups/20260819-0230/…)
python3 scripts/backup_db.py --dest backups
```

Automate it (daily 02:30) with cron:

```cron
30 2 * * *  cd /path/to/dich-tai-lieu && python3 scripts/backup_db.py --dest /var/backups/dtl
```

Keep several days of backups and copy them off the machine (another disk / object
storage). Prune old ones on whatever retention you choose.

## The encryption key (read this)

`data/.encryption_key` is generated per deployment, is **git-ignored**, and is
**not** a `.db` — so it is NOT included in these backups by design. Any data
encrypted with it becomes unreadable if the key is lost. **Back the key up
separately and securely** (a secrets manager / sealed storage), never in the
same place as the database backups.

## Restore

1. **Stop the app** (no writers): `./stop_server.sh` (or stop the container).
2. Pick the backup folder to restore from (e.g. `backups/20260819-0230/`).
3. Copy the databases back over `data/`, preserving structure:
   ```bash
   rsync -a backups/20260819-0230/ data/
   # or: cp -a backups/20260819-0230/. data/
   ```
4. If the deployment uses encryption, ensure the matching `data/.encryption_key`
   is in place (from its separate secure backup).
5. **Start the app** and verify: hit `/health`, then `/api/health/detailed`
   (requires auth in production) and confirm the databases report healthy.

## Verify a backup without restoring

```bash
sqlite3 backups/20260819-0230/data/jobs.db "PRAGMA integrity_check;"   # -> ok
sqlite3 backups/20260819-0230/data/jobs.db "SELECT count(*) FROM aps_jobs;"
```

## Notes

- Backups are WAL-safe: no need to also copy `*.db-wal` / `*.db-shm`.
- `scripts/backup_db.py` exits non-zero if any database fails to copy — wire that
  into your cron alerting so a silent backup failure is caught.
