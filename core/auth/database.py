#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
User Database - SQLite-based user storage

Provides persistent storage for users with proper indexing.
"""

import sqlite3
import json
import logging
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from .models import User, UserRole, UserStatus

logger = logging.getLogger(__name__)

# Database path
USER_DB_PATH = Path("data/users/users.db")


class UserDatabase:
    """SQLite-based user storage."""

    def __init__(self, db_path: Path | None = None):
        """Initialize user database."""
        if db_path is None:
            db_path = USER_DB_PATH
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = None
        self._init_database()

    def _init_database(self):
        """Initialize database schema."""
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.row_factory = sqlite3.Row

        cursor = self.conn.cursor()

        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT,
                organization TEXT,
                role TEXT NOT NULL DEFAULT 'user',
                status TEXT NOT NULL DEFAULT 'active',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                last_login REAL,
                preferences TEXT DEFAULT '{}',
                jobs_count INTEGER DEFAULT 0,
                tokens_used INTEGER DEFAULT 0
            )
        """)

        # Refresh tokens table (for token invalidation)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS refresh_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token_hash TEXT UNIQUE NOT NULL,
                created_at REAL NOT NULL,
                expires_at REAL NOT NULL,
                revoked BOOLEAN DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # Password reset tokens
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token_hash TEXT UNIQUE NOT NULL,
                created_at REAL NOT NULL,
                expires_at REAL NOT NULL,
                used BOOLEAN DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # Indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_status ON users(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user ON refresh_tokens(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_refresh_tokens_hash ON refresh_tokens(token_hash)")

        self.conn.commit()
        logger.info(f"User database initialized at {self.db_path}")

    # ========================================================================
    # User CRUD Operations
    # ========================================================================

    def create_user(self, user: User) -> User:
        """Create a new user."""
        cursor = self.conn.cursor()

        now = datetime.now().timestamp()

        cursor.execute("""
            INSERT INTO users (
                email, username, password_hash, full_name, organization,
                role, status, created_at, updated_at, preferences
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user.email,
            user.username,
            user.password_hash,
            user.full_name,
            user.organization,
            user.role.value,
            user.status.value,
            now,
            now,
            json.dumps(user.preferences)
        ))

        self.conn.commit()
        user.id = cursor.lastrowid
        user.created_at = datetime.fromtimestamp(now)
        user.updated_at = datetime.fromtimestamp(now)

        logger.info(f"Created user: {user.email} (id={user.id})")
        return user

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return self._row_to_user(row) if row else None

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email.lower(),))
        row = cursor.fetchone()
        return self._row_to_user(row) if row else None

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        return self._row_to_user(row) if row else None

    def update_user(self, user: User) -> User:
        """Update user details."""
        cursor = self.conn.cursor()

        now = datetime.now().timestamp()

        cursor.execute("""
            UPDATE users SET
                full_name = ?,
                organization = ?,
                role = ?,
                status = ?,
                updated_at = ?,
                preferences = ?,
                jobs_count = ?,
                tokens_used = ?
            WHERE id = ?
        """, (
            user.full_name,
            user.organization,
            user.role.value,
            user.status.value,
            now,
            json.dumps(user.preferences),
            user.jobs_count,
            user.tokens_used,
            user.id
        ))

        self.conn.commit()
        user.updated_at = datetime.fromtimestamp(now)
        return user

    def update_password(self, user_id: int, password_hash: str) -> bool:
        """Update user password."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE users SET password_hash = ?, updated_at = ?
            WHERE id = ?
        """, (password_hash, datetime.now().timestamp(), user_id))
        self.conn.commit()
        return cursor.rowcount > 0

    def update_last_login(self, user_id: int) -> bool:
        """Update last login timestamp."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE users SET last_login = ?
            WHERE id = ?
        """, (datetime.now().timestamp(), user_id))
        self.conn.commit()
        return cursor.rowcount > 0

    def delete_user(self, user_id: int) -> bool:
        """Delete user (soft delete by setting status to inactive)."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE users SET status = ?, updated_at = ?
            WHERE id = ?
        """, (UserStatus.INACTIVE.value, datetime.now().timestamp(), user_id))
        self.conn.commit()
        return cursor.rowcount > 0

    def list_users(
        self,
        role: Optional[UserRole] = None,
        status: Optional[UserStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[User]:
        """List users with optional filters."""
        cursor = self.conn.cursor()

        query = "SELECT * FROM users WHERE 1=1"
        params = []

        if role:
            query += " AND role = ?"
            params.append(role.value)

        if status:
            query += " AND status = ?"
            params.append(status.value)

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(query, params)
        return [self._row_to_user(row) for row in cursor.fetchall()]

    def count_users(
        self,
        role: Optional[UserRole] = None,
        status: Optional[UserStatus] = None
    ) -> int:
        """Count users with optional filters."""
        cursor = self.conn.cursor()

        query = "SELECT COUNT(*) FROM users WHERE 1=1"
        params = []

        if role:
            query += " AND role = ?"
            params.append(role.value)

        if status:
            query += " AND status = ?"
            params.append(status.value)

        cursor.execute(query, params)
        return cursor.fetchone()[0]

    # ========================================================================
    # Refresh Token Operations
    # ========================================================================

    def store_refresh_token(
        self,
        user_id: int,
        token_hash: str,
        expires_at: datetime
    ) -> int:
        """Store a refresh token."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO refresh_tokens (user_id, token_hash, created_at, expires_at)
            VALUES (?, ?, ?, ?)
        """, (user_id, token_hash, datetime.now().timestamp(), expires_at.timestamp()))
        self.conn.commit()
        return cursor.lastrowid

    def get_refresh_token(self, token_hash: str) -> Optional[dict]:
        """Get refresh token by hash."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM refresh_tokens
            WHERE token_hash = ? AND revoked = 0
        """, (token_hash,))
        row = cursor.fetchone()

        if row:
            return {
                "id": row["id"],
                "user_id": row["user_id"],
                "token_hash": row["token_hash"],
                "created_at": datetime.fromtimestamp(row["created_at"]),
                "expires_at": datetime.fromtimestamp(row["expires_at"]),
                "revoked": bool(row["revoked"])
            }
        return None

    def revoke_refresh_token(self, token_hash: str) -> bool:
        """Revoke a refresh token."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE refresh_tokens SET revoked = 1
            WHERE token_hash = ?
        """, (token_hash,))
        self.conn.commit()
        return cursor.rowcount > 0

    def revoke_all_user_tokens(self, user_id: int) -> int:
        """Revoke all refresh tokens for a user (logout everywhere)."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE refresh_tokens SET revoked = 1
            WHERE user_id = ? AND revoked = 0
        """, (user_id,))
        self.conn.commit()
        return cursor.rowcount

    def cleanup_expired_tokens(self) -> int:
        """Remove expired tokens."""
        cursor = self.conn.cursor()
        cursor.execute("""
            DELETE FROM refresh_tokens
            WHERE expires_at < ? OR revoked = 1
        """, (datetime.now().timestamp(),))
        self.conn.commit()
        return cursor.rowcount

    # ========================================================================
    # Password Reset Token Operations
    # ========================================================================

    def store_password_reset_token(
        self,
        user_id: int,
        token_hash: str,
        expires_at: datetime
    ) -> int:
        """Store a password reset token."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO password_reset_tokens (user_id, token_hash, created_at, expires_at)
            VALUES (?, ?, ?, ?)
        """, (user_id, token_hash, datetime.now().timestamp(), expires_at.timestamp()))
        self.conn.commit()
        return cursor.lastrowid

    def get_password_reset_token(self, token_hash: str) -> Optional[dict]:
        """Get password reset token by hash."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM password_reset_tokens
            WHERE token_hash = ? AND used = 0 AND expires_at > ?
        """, (token_hash, datetime.now().timestamp()))
        row = cursor.fetchone()

        if row:
            return {
                "id": row["id"],
                "user_id": row["user_id"],
                "token_hash": row["token_hash"],
                "created_at": datetime.fromtimestamp(row["created_at"]),
                "expires_at": datetime.fromtimestamp(row["expires_at"])
            }
        return None

    def mark_password_reset_used(self, token_hash: str) -> bool:
        """Mark password reset token as used."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE password_reset_tokens SET used = 1
            WHERE token_hash = ?
        """, (token_hash,))
        self.conn.commit()
        return cursor.rowcount > 0

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _row_to_user(self, row: sqlite3.Row) -> User:
        """Convert database row to User model."""
        return User(
            id=row["id"],
            email=row["email"],
            username=row["username"],
            password_hash=row["password_hash"],
            full_name=row["full_name"],
            organization=row["organization"],
            role=UserRole(row["role"]),
            status=UserStatus(row["status"]),
            created_at=datetime.fromtimestamp(row["created_at"]),
            updated_at=datetime.fromtimestamp(row["updated_at"]),
            last_login=datetime.fromtimestamp(row["last_login"]) if row["last_login"] else None,
            preferences=json.loads(row["preferences"]) if row["preferences"] else {},
            jobs_count=row["jobs_count"],
            tokens_used=row["tokens_used"]
        )

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()


# Global instance
_user_db: Optional[UserDatabase] = None


def get_user_db() -> UserDatabase:
    """Get global user database instance."""
    global _user_db
    if _user_db is None:
        _user_db = UserDatabase()
    return _user_db
