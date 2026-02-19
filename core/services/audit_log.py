"""
Audit logging service — tracks who did what, when.

Stores entries in SQLite for query and compliance.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)


class AuditLogger:
    """Lightweight audit log backed by SQLite."""

    def __init__(self, db_path: Path | None = None):
        if db_path is None:
            from config.settings import BASE_DIR
            db_path = BASE_DIR / "data" / "audit.db"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True, parents=True)
        self._init_db()

    def _init_db(self):
        import sqlite3
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                user_id TEXT NOT NULL DEFAULT 'anonymous',
                action TEXT NOT NULL,
                resource_type TEXT,
                resource_id TEXT,
                detail TEXT,
                ip_address TEXT
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_timestamp
            ON audit_log(timestamp DESC)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_user
            ON audit_log(user_id, timestamp DESC)
        """)
        conn.commit()
        conn.close()

    def log(
        self,
        action: str,
        user_id: str = "anonymous",
        resource_type: str | None = None,
        resource_id: str | None = None,
        detail: str | None = None,
        ip_address: str | None = None,
    ):
        """Write an audit entry."""
        import sqlite3
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.execute(
                "INSERT INTO audit_log (timestamp, user_id, action, resource_type, resource_id, detail, ip_address) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (time.time(), user_id, action, resource_type, resource_id, detail, ip_address),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"Audit log write failed: {e}")

    def get_recent(self, limit: int = 50, user_id: str | None = None) -> list[dict]:
        """Read recent audit entries."""
        import sqlite3
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        if user_id:
            rows = conn.execute(
                "SELECT * FROM audit_log WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
                (user_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def cleanup(self, days: int = 90) -> int:
        """Remove entries older than N days."""
        import sqlite3
        cutoff = time.time() - (days * 86400)
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.execute("DELETE FROM audit_log WHERE timestamp < ?", (cutoff,))
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        return deleted


_audit_logger: AuditLogger | None = None


def get_audit_logger() -> AuditLogger:
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger
