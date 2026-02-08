"""Tests for FileCleanupService."""

import os
import time
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from core.services.file_cleanup import FileCleanupService, CleanupResult


@pytest.fixture
def cleanup_dirs(tmp_path):
    """Create temp directory structure for cleanup tests."""
    dirs = {
        "temp": tmp_path / "temp",
        "input": tmp_path / "input",
        "output": tmp_path / "output",
        "checkpoints": tmp_path / "checkpoints",
    }
    for d in dirs.values():
        d.mkdir()
    return dirs


@pytest.fixture
def mock_settings(cleanup_dirs):
    """Mock settings to use temp directories."""
    settings = MagicMock()
    settings.temp_dir = cleanup_dirs["temp"]
    settings.input_dir = cleanup_dirs["input"]
    settings.output_dir = cleanup_dirs["output"]
    settings.checkpoint_dir = cleanup_dirs["checkpoints"]
    settings.cleanup_temp_max_age_hours = 24
    settings.cleanup_upload_retention_days = 7
    settings.cleanup_output_retention_days = 30
    settings.cleanup_checkpoint_retention_days = 7
    return settings


def _create_old_file(directory: Path, name: str, age_hours: int) -> Path:
    """Create a file with a modified time in the past."""
    f = directory / name
    f.write_text("test content")
    old_time = time.time() - (age_hours * 3600)
    os.utime(f, (old_time, old_time))
    return f


class TestFileCleanupService:

    def test_clean_temp_files(self, cleanup_dirs, mock_settings):
        """Old temp files should be removed."""
        # Create an old file (48 hours) and a new file
        _create_old_file(cleanup_dirs["temp"], "old.tmp", age_hours=48)
        new_file = cleanup_dirs["temp"] / "new.tmp"
        new_file.write_text("recent")

        with patch("core.services.file_cleanup.FileCleanupService.__init__", return_value=None):
            svc = FileCleanupService.__new__(FileCleanupService)
            svc.temp_dir = mock_settings.temp_dir
            svc.input_dir = mock_settings.input_dir
            svc.output_dir = mock_settings.output_dir
            svc.checkpoint_dir = mock_settings.checkpoint_dir
            svc.temp_max_age_hours = 24
            svc.upload_retention_days = 7
            svc.output_retention_days = 30
            svc.checkpoint_retention_days = 7

        result = svc.run_cleanup()

        assert result.temp_files_removed == 1
        assert not (cleanup_dirs["temp"] / "old.tmp").exists()
        assert new_file.exists()

    def test_dry_run_does_not_delete(self, cleanup_dirs, mock_settings):
        """Dry run should not delete files."""
        _create_old_file(cleanup_dirs["temp"], "old.tmp", age_hours=48)

        with patch("core.services.file_cleanup.FileCleanupService.__init__", return_value=None):
            svc = FileCleanupService.__new__(FileCleanupService)
            svc.temp_dir = mock_settings.temp_dir
            svc.input_dir = mock_settings.input_dir
            svc.output_dir = mock_settings.output_dir
            svc.checkpoint_dir = mock_settings.checkpoint_dir
            svc.temp_max_age_hours = 24
            svc.upload_retention_days = 7
            svc.output_retention_days = 30
            svc.checkpoint_retention_days = 7

        result = svc.run_cleanup(dry_run=True)

        assert result.temp_files_removed == 1
        assert result.dry_run is True
        assert (cleanup_dirs["temp"] / "old.tmp").exists()  # NOT deleted

    def test_clean_old_outputs(self, cleanup_dirs, mock_settings):
        """Output files older than retention should be removed."""
        _create_old_file(cleanup_dirs["output"], "old_output.pdf", age_hours=31 * 24)
        new_output = cleanup_dirs["output"] / "new_output.pdf"
        new_output.write_text("recent")

        with patch("core.services.file_cleanup.FileCleanupService.__init__", return_value=None):
            svc = FileCleanupService.__new__(FileCleanupService)
            svc.temp_dir = mock_settings.temp_dir
            svc.input_dir = mock_settings.input_dir
            svc.output_dir = mock_settings.output_dir
            svc.checkpoint_dir = mock_settings.checkpoint_dir
            svc.temp_max_age_hours = 24
            svc.upload_retention_days = 7
            svc.output_retention_days = 30
            svc.checkpoint_retention_days = 7

        result = svc.run_cleanup()

        assert result.old_outputs_removed == 1
        assert not (cleanup_dirs["output"] / "old_output.pdf").exists()
        assert new_output.exists()

    def test_cleanup_result_str(self):
        result = CleanupResult(
            temp_files_removed=3,
            bytes_freed=1024 * 1024 * 5,
        )
        s = str(result)
        assert "temp=3" in s
        assert "5.0MB" in s

    def test_cleanup_nonexistent_dirs(self, tmp_path, mock_settings):
        """Service should handle missing directories gracefully."""
        with patch("core.services.file_cleanup.FileCleanupService.__init__", return_value=None):
            svc = FileCleanupService.__new__(FileCleanupService)
            svc.temp_dir = tmp_path / "nonexistent_temp"
            svc.input_dir = tmp_path / "nonexistent_input"
            svc.output_dir = tmp_path / "nonexistent_output"
            svc.checkpoint_dir = tmp_path / "nonexistent_checkpoints"
            svc.temp_max_age_hours = 24
            svc.upload_retention_days = 7
            svc.output_retention_days = 30
            svc.checkpoint_retention_days = 7

        result = svc.run_cleanup()
        assert result.temp_files_removed == 0
