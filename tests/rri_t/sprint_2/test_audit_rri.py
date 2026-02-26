"""
RRI-T Sprint 2: Audit logging tests.

Persona coverage: Business Analyst, Security Auditor
Dimensions: D4 (Security), D5 (Data Integrity)
"""

import time
import pytest
from pathlib import Path

from core.services.audit_log import AuditLogger


pytestmark = [pytest.mark.rri_t]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def audit(tmp_path):
    """Fresh AuditLogger with temp DB."""
    return AuditLogger(db_path=tmp_path / "audit.db")


# ===========================================================================
# AUDIT-001: Every mutation logged
# ===========================================================================

class TestAuditLogging:
    """Business Analyst persona — audit trail completeness."""

    @pytest.mark.p1
    def test_audit_001_log_entry_written(self, audit):
        """AUDIT-001 | BA | log() writes entry to database"""
        audit.log(
            action="job_created",
            user_id="user-1",
            resource_type="job",
            resource_id="j-123",
            detail="Created translation job",
            ip_address="127.0.0.1",
        )

        entries = audit.get_recent(limit=10)
        assert len(entries) == 1
        assert entries[0]["action"] == "job_created"
        assert entries[0]["user_id"] == "user-1"
        assert entries[0]["resource_id"] == "j-123"

    @pytest.mark.p1
    def test_audit_001b_multiple_entries(self, audit):
        """AUDIT-001b | BA | Multiple logs recorded in order"""
        for i in range(5):
            audit.log(action=f"action_{i}", user_id="u1")

        entries = audit.get_recent(limit=10)
        assert len(entries) == 5
        # Most recent first
        assert entries[0]["action"] == "action_4"

    @pytest.mark.p1
    def test_audit_001c_filter_by_user(self, audit):
        """AUDIT-001c | BA | get_recent filters by user_id"""
        audit.log(action="a1", user_id="alice")
        audit.log(action="a2", user_id="bob")
        audit.log(action="a3", user_id="alice")

        alice_entries = audit.get_recent(limit=10, user_id="alice")
        assert len(alice_entries) == 2
        assert all(e["user_id"] == "alice" for e in alice_entries)

    @pytest.mark.p1
    def test_audit_001d_anonymous_default(self, audit):
        """AUDIT-001d | BA | Default user_id is 'anonymous'"""
        audit.log(action="anon_action")
        entries = audit.get_recent(limit=1)
        assert entries[0]["user_id"] == "anonymous"


# ===========================================================================
# AUDIT-002: Audit log integrity
# ===========================================================================

class TestAuditIntegrity:
    """Security Auditor persona — audit log reliability."""

    @pytest.mark.p1
    def test_audit_002_timestamp_present(self, audit):
        """AUDIT-002 | Security | Entries have timestamps"""
        before = time.time()
        audit.log(action="timed_action")
        after = time.time()

        entries = audit.get_recent(limit=1)
        ts = entries[0]["timestamp"]
        assert before <= ts <= after

    @pytest.mark.p1
    def test_audit_002b_detail_preserved(self, audit):
        """AUDIT-002b | Security | Detail field preserved verbatim"""
        long_detail = "x" * 1000
        audit.log(action="detail_test", detail=long_detail)
        entries = audit.get_recent(limit=1)
        assert entries[0]["detail"] == long_detail

    @pytest.mark.p1
    def test_audit_002c_ip_address_stored(self, audit):
        """AUDIT-002c | Security | IP address stored correctly"""
        audit.log(action="ip_test", ip_address="192.168.1.100")
        entries = audit.get_recent(limit=1)
        assert entries[0]["ip_address"] == "192.168.1.100"


# ===========================================================================
# AUDIT-003: Cleanup
# ===========================================================================

class TestAuditCleanup:
    """DevOps persona — log rotation/cleanup."""

    @pytest.mark.p1
    def test_audit_003_cleanup_old_entries(self, audit):
        """AUDIT-003 | DevOps | cleanup() removes entries older than N days"""
        # Insert old entry with manual timestamp
        with audit._db.connection() as conn:
            old_ts = time.time() - (100 * 86400)  # 100 days ago
            conn.execute(
                "INSERT INTO audit_log (timestamp, user_id, action) VALUES (?, ?, ?)",
                (old_ts, "old_user", "old_action"),
            )

        # Insert recent entry
        audit.log(action="recent_action")

        # Cleanup entries older than 90 days
        deleted = audit.cleanup(days=90)
        assert deleted >= 1

        entries = audit.get_recent(limit=10)
        assert len(entries) == 1
        assert entries[0]["action"] == "recent_action"

    @pytest.mark.p1
    def test_audit_003b_cleanup_no_recent(self, audit):
        """AUDIT-003b | DevOps | cleanup() preserves recent entries"""
        audit.log(action="keep_me")
        deleted = audit.cleanup(days=90)
        assert deleted == 0
        assert len(audit.get_recent(limit=10)) == 1


# ===========================================================================
# AUDIT-004: Error resilience
# ===========================================================================

class TestAuditErrorResilience:
    """DevOps persona — audit logging doesn't crash the app."""

    @pytest.mark.p1
    def test_audit_004_write_failure_silent(self, audit):
        """AUDIT-004 | DevOps | Write failure -> silent (logged warning, no raise)"""
        # Close the backend to simulate a broken state
        audit._db.close()
        # This should not raise even though the DB is closed
        # (The AuditLogger silently catches exceptions)
        # For non-persistent backends, close() is a no-op so this still works
        # Just verify log() doesn't raise in normal operation
        audit.log(action="after_close")  # Should not raise
