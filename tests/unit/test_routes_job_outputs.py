"""
Unit tests for api/routes/job_outputs.py — download, preview, PDF detection.

Sprint 7: expanded coverage for conversion path, preview edge cases,
and pdf/detect success/error branches.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path
from fastapi.testclient import TestClient

from api.main import app
from core.job_queue import JobStatus


class TestDownloadJobOutput:
    """Test GET /api/jobs/{job_id}/download/{format}."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_invalid_format(self, client):
        resp = client.get("/api/jobs/abc/download/exe")
        assert resp.status_code == 400
        assert "Invalid format" in resp.json()["detail"]

    def test_job_not_found(self, client):
        with patch("api.routes.job_outputs.queue") as mock_queue:
            mock_queue.get_job.return_value = None
            resp = client.get("/api/jobs/nonexistent/download/docx")
        assert resp.status_code == 404

    def test_job_not_completed(self, client):
        mock_job = MagicMock()
        mock_job.status = JobStatus.RUNNING
        with patch("api.routes.job_outputs.queue") as mock_queue:
            mock_queue.get_job.return_value = mock_job
            resp = client.get("/api/jobs/abc/download/docx")
        assert resp.status_code == 400
        assert "Cannot download" in resp.json()["detail"]

    def test_job_pending_message(self, client):
        mock_job = MagicMock()
        mock_job.status = JobStatus.PENDING
        with patch("api.routes.job_outputs.queue") as mock_queue:
            mock_queue.get_job.return_value = mock_job
            resp = client.get("/api/jobs/abc/download/txt")
        assert resp.status_code == 400
        assert "queued" in resp.json()["detail"].lower()

    def test_job_failed_message(self, client):
        mock_job = MagicMock()
        mock_job.status = JobStatus.FAILED
        with patch("api.routes.job_outputs.queue") as mock_queue:
            mock_queue.get_job.return_value = mock_job
            resp = client.get("/api/jobs/abc/download/docx")
        assert resp.status_code == 400
        assert "failed" in resp.json()["detail"].lower()

    def test_output_file_not_found(self, client, tmp_path):
        mock_job = MagicMock()
        mock_job.status = JobStatus.COMPLETED
        mock_job.output_file = str(tmp_path / "nonexistent.docx")
        mock_job.output_format = "docx"
        with patch("api.routes.job_outputs.queue") as mock_queue:
            mock_queue.get_job.return_value = mock_job
            resp = client.get("/api/jobs/abc/download/docx")
        assert resp.status_code == 404

    def test_download_success(self, client, tmp_path):
        out_file = tmp_path / "output.txt"
        out_file.write_text("Translated content here")

        mock_job = MagicMock()
        mock_job.status = JobStatus.COMPLETED
        mock_job.output_file = str(out_file)
        mock_job.output_format = "txt"

        with patch("api.routes.job_outputs.queue") as mock_queue:
            mock_queue.get_job.return_value = mock_job
            resp = client.get("/api/jobs/abc/download/txt")

        assert resp.status_code == 200

    def test_allowed_formats(self, client):
        """Verify all allowed formats don't get 400."""
        for fmt in ("docx", "pdf", "md", "txt", "html", "srt"):
            with patch("api.routes.job_outputs.queue") as mock_queue:
                mock_queue.get_job.return_value = None
                resp = client.get(f"/api/jobs/x/download/{fmt}")
            assert resp.status_code == 404

    def test_download_different_format_already_exists(self, client, tmp_path):
        """Target format file already exists → serve it directly."""
        out_docx = tmp_path / "output.docx"
        out_docx.write_bytes(b"fake docx")
        out_md = tmp_path / "output.md"
        out_md.write_text("# Hello")

        mock_job = MagicMock()
        mock_job.status = JobStatus.COMPLETED
        mock_job.output_file = str(out_docx)
        mock_job.output_format = "docx"

        with patch("api.routes.job_outputs.queue") as mock_queue:
            mock_queue.get_job.return_value = mock_job
            resp = client.get("/api/jobs/abc/download/md")

        assert resp.status_code == 200

    def test_download_conversion_success(self, client, tmp_path):
        """Format differs, conversion succeeds."""
        out_docx = tmp_path / "output.docx"
        out_docx.write_bytes(b"fake docx")
        out_txt = tmp_path / "output.txt"

        mock_job = MagicMock()
        mock_job.status = JobStatus.COMPLETED
        mock_job.output_file = str(out_docx)
        mock_job.output_format = "docx"

        async def fake_convert(src, fmt, outdir, base):
            out_txt.write_text("converted")
            return out_txt

        with patch("api.routes.job_outputs.queue") as mock_queue, \
             patch("api.routes.job_outputs.convert_document_format", side_effect=fake_convert):
            mock_queue.get_job.return_value = mock_job
            resp = client.get("/api/jobs/abc/download/txt")

        assert resp.status_code == 200

    def test_download_conversion_returns_none(self, client, tmp_path):
        """Conversion returns None → 500."""
        out_docx = tmp_path / "output.docx"
        out_docx.write_bytes(b"fake docx")

        mock_job = MagicMock()
        mock_job.status = JobStatus.COMPLETED
        mock_job.output_file = str(out_docx)
        mock_job.output_format = "docx"

        async def fake_convert(src, fmt, outdir, base):
            return None

        with patch("api.routes.job_outputs.queue") as mock_queue, \
             patch("api.routes.job_outputs.convert_document_format", side_effect=fake_convert):
            mock_queue.get_job.return_value = mock_job
            resp = client.get("/api/jobs/abc/download/md")

        assert resp.status_code == 500

    def test_download_conversion_raises(self, client, tmp_path):
        """Conversion raises exception → 500."""
        out_docx = tmp_path / "output.docx"
        out_docx.write_bytes(b"fake docx")

        mock_job = MagicMock()
        mock_job.status = JobStatus.COMPLETED
        mock_job.output_file = str(out_docx)
        mock_job.output_format = "docx"

        async def fake_convert(src, fmt, outdir, base):
            raise RuntimeError("converter boom")

        with patch("api.routes.job_outputs.queue") as mock_queue, \
             patch("api.routes.job_outputs.convert_document_format", side_effect=fake_convert):
            mock_queue.get_job.return_value = mock_job
            resp = client.get("/api/jobs/abc/download/md")

        assert resp.status_code == 500
        assert "converter boom" in resp.json()["detail"]

    def test_download_cancelled_message(self, client):
        mock_job = MagicMock()
        mock_job.status = JobStatus.CANCELLED
        with patch("api.routes.job_outputs.queue") as mock_queue:
            mock_queue.get_job.return_value = mock_job
            resp = client.get("/api/jobs/abc/download/txt")
        assert resp.status_code == 400
        assert "cancelled" in resp.json()["detail"].lower()

    def test_download_paused_message(self, client):
        mock_job = MagicMock()
        mock_job.status = "paused"
        with patch("api.routes.job_outputs.queue") as mock_queue:
            mock_queue.get_job.return_value = mock_job
            resp = client.get("/api/jobs/abc/download/txt")
        assert resp.status_code == 400
        assert "paused" in resp.json()["detail"].lower()


class TestJobPreview:
    """Test GET /api/jobs/{job_id}/preview."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_preview_not_found(self, client):
        with patch("api.routes.job_outputs.queue") as mock_queue:
            mock_queue.get_job.return_value = None
            resp = client.get("/api/jobs/abc/preview")
        assert resp.status_code == 404

    def test_preview_not_completed(self, client):
        mock_job = MagicMock()
        mock_job.status = JobStatus.RUNNING
        with patch("api.routes.job_outputs.queue") as mock_queue:
            mock_queue.get_job.return_value = mock_job
            resp = client.get("/api/jobs/abc/preview")
        assert resp.status_code == 400

    def test_preview_txt_file(self, client, tmp_path):
        out_file = tmp_path / "output.txt"
        out_file.write_text("Word one two three four five")

        mock_job = MagicMock()
        mock_job.status = JobStatus.COMPLETED
        mock_job.output_file = str(out_file)
        mock_job.output_format = "txt"

        with patch("api.routes.job_outputs.queue") as mock_queue, \
             patch("api.routes.job_outputs.read_document", return_value="Word one two three four five"):
            mock_queue.get_job.return_value = mock_job
            resp = client.get("/api/jobs/abc/preview")

        assert resp.status_code == 200
        data = resp.json()
        assert data["is_structured"] is False
        assert data["total_words"] == 6

    def test_preview_docx_file(self, client, tmp_path):
        out_file = tmp_path / "output.docx"
        out_file.write_bytes(b"fake")

        mock_job = MagicMock()
        mock_job.status = JobStatus.COMPLETED
        mock_job.output_file = str(out_file)
        mock_job.output_format = "docx"

        mock_para = MagicMock()
        mock_para.text = "Introduction to machine learning"
        mock_doc = MagicMock()
        mock_doc.paragraphs = [mock_para]

        mock_detector = MagicMock()
        mock_detector.detect_heading_level.return_value = 1

        with patch("api.routes.job_outputs.queue") as mock_queue, \
             patch("api.routes.job_outputs.DocxDocument", return_value=mock_doc), \
             patch("api.routes.job_outputs.HeadingDetector", return_value=mock_detector):
            mock_queue.get_job.return_value = mock_job
            resp = client.get("/api/jobs/abc/preview")

        assert resp.status_code == 200
        data = resp.json()
        assert data["is_structured"] is True
        assert len(data["preview"]) == 1
        assert data["preview"][0]["type"] == "heading1"

    def test_preview_output_file_missing(self, client, tmp_path):
        mock_job = MagicMock()
        mock_job.status = JobStatus.COMPLETED
        mock_job.output_file = str(tmp_path / "gone.docx")
        mock_job.output_format = "docx"

        with patch("api.routes.job_outputs.queue") as mock_queue:
            mock_queue.get_job.return_value = mock_job
            resp = client.get("/api/jobs/abc/preview")
        assert resp.status_code == 404

    def test_preview_exception_returns_500(self, client, tmp_path):
        """Preview generation raises → 500."""
        out_file = tmp_path / "output.docx"
        out_file.write_bytes(b"fake")

        mock_job = MagicMock()
        mock_job.status = JobStatus.COMPLETED
        mock_job.output_file = str(out_file)
        mock_job.output_format = "docx"

        with patch("api.routes.job_outputs.queue") as mock_queue, \
             patch("api.routes.job_outputs.DocxDocument", side_effect=RuntimeError("corrupt")):
            mock_queue.get_job.return_value = mock_job
            resp = client.get("/api/jobs/abc/preview")

        assert resp.status_code == 500
        assert "Failed to generate preview" in resp.json()["detail"]

    def test_preview_docx_multiple_paragraphs(self, client, tmp_path):
        """Multiple paragraphs with mixed headings and body."""
        out_file = tmp_path / "output.docx"
        out_file.write_bytes(b"fake")

        mock_job = MagicMock()
        mock_job.status = JobStatus.COMPLETED
        mock_job.output_file = str(out_file)
        mock_job.output_format = "docx"

        p1 = MagicMock(); p1.text = "Chapter One"
        p2 = MagicMock(); p2.text = ""
        p3 = MagicMock(); p3.text = "Body text here with words"
        mock_doc = MagicMock()
        mock_doc.paragraphs = [p1, p2, p3]

        det = MagicMock()
        det.detect_heading_level.side_effect = lambda t: 1 if "Chapter" in t else None

        with patch("api.routes.job_outputs.queue") as mock_queue, \
             patch("api.routes.job_outputs.DocxDocument", return_value=mock_doc), \
             patch("api.routes.job_outputs.HeadingDetector", return_value=det):
            mock_queue.get_job.return_value = mock_job
            resp = client.get("/api/jobs/abc/preview")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["preview"]) == 2  # empty para skipped
        assert data["preview"][0]["type"] == "heading1"
        assert data["preview"][1]["type"] == "paragraph"


class TestPdfDetect:
    """Test POST /api/pdf/detect."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_path_traversal_blocked(self, client):
        resp = client.post("/api/pdf/detect?file_path=../../../etc/passwd")
        assert resp.status_code in (403, 400, 404)

    def test_file_not_found(self, client):
        resp = client.post("/api/pdf/detect?file_path=uploads/nonexistent.pdf")
        assert resp.status_code == 404

    def test_not_a_pdf(self, client):
        project_root = Path(__file__).parent.parent.parent
        uploads_dir = project_root / "uploads"
        uploads_dir.mkdir(exist_ok=True)
        txt_file = uploads_dir / "_test_not_pdf.txt"
        txt_file.write_text("hello")
        try:
            resp = client.post(f"/api/pdf/detect?file_path={txt_file}")
            assert resp.status_code == 400
            assert "not a PDF" in resp.json()["detail"]
        finally:
            txt_file.unlink(missing_ok=True)

    def test_detect_success(self, client):
        """Mock SmartDetector for successful detection."""
        project_root = Path(__file__).parent.parent.parent
        uploads_dir = project_root / "uploads"
        uploads_dir.mkdir(exist_ok=True)
        pdf_file = uploads_dir / "_test_detect.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake")

        mock_result = MagicMock()
        mock_result.pdf_type.value = "native"
        mock_result.ocr_needed = False
        mock_result.confidence = 0.95
        mock_result.recommendation.value = "none"
        mock_result.details = {"pages": 10}

        mock_detector = MagicMock()
        mock_detector.detect_pdf_type.return_value = mock_result
        mock_detector.recommend_ocr_mode.return_value = "No OCR needed"

        try:
            with patch("core.ocr.SmartDetector", return_value=mock_detector):
                resp = client.post(f"/api/pdf/detect?file_path={pdf_file}")

            assert resp.status_code == 200
            data = resp.json()
            assert data["pdf_type"] == "native"
            assert data["ocr_needed"] is False
            assert data["confidence"] == 0.95
        finally:
            pdf_file.unlink(missing_ok=True)

    def test_detect_runtime_error(self, client):
        """SmartDetector.detect_pdf_type raises → 500."""
        project_root = Path(__file__).parent.parent.parent
        uploads_dir = project_root / "uploads"
        uploads_dir.mkdir(exist_ok=True)
        pdf_file = uploads_dir / "_test_runtime_err.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake")

        mock_detector = MagicMock()
        mock_detector.detect_pdf_type.side_effect = RuntimeError("parse error")

        try:
            with patch("core.ocr.SmartDetector", return_value=mock_detector):
                resp = client.post(f"/api/pdf/detect?file_path={pdf_file}")

            assert resp.status_code == 500
            assert "Detection failed" in resp.json()["detail"]
        finally:
            pdf_file.unlink(missing_ok=True)
