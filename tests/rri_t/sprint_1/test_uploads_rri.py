"""
RRI-T Sprint 1: Upload endpoint tests.

Persona coverage: End User, QA Destroyer, Security Auditor
Dimensions: D2 (API), D4 (Security), D5 (Data Integrity), D7 (Edge Cases)
"""

import io
import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from api.main import app


pytestmark = [pytest.mark.rri_t]


class TestUploadHappyPath:
    """End User persona — successful file uploads."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.mark.p0
    def test_upload_001_txt_file_succeeds(self, client, tmp_path):
        """UPLOAD-001 | End User | Upload .txt file -> 200 with metadata"""
        content = b"Hello world. This is a test document."
        resp = client.post(
            "/api/upload",
            files={"file": ("test.txt", io.BytesIO(content), "text/plain")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "server_path" in data
        assert data["filename"] == "test.txt"
        assert data["size"] == len(content)

    @pytest.mark.p0
    def test_upload_001b_pdf_file_succeeds(self, client):
        """UPLOAD-001b | End User | Upload valid PDF -> 200"""
        pdf_bytes = (
            b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
            b"2 0 obj\n<< /Type /Pages /Kids [] /Count 0 >>\nendobj\n"
            b"xref\n0 3\n0000000000 65535 f \n0000000009 00000 n \n"
            b"0000000058 00000 n \ntrailer\n<< /Size 3 /Root 1 0 R >>\n"
            b"startxref\n115\n%%EOF"
        )
        resp = client.post(
            "/api/upload",
            files={"file": ("doc.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        )
        assert resp.status_code == 200
        assert resp.json()["filename"] == "doc.pdf"

    @pytest.mark.p1
    def test_upload_001c_md_file_succeeds(self, client):
        """UPLOAD-001c | End User | Upload .md file -> 200"""
        resp = client.post(
            "/api/upload",
            files={"file": ("readme.md", io.BytesIO(b"# Title\nContent"), "text/markdown")},
        )
        assert resp.status_code == 200

    @pytest.mark.p1
    def test_upload_001d_srt_file_succeeds(self, client):
        """UPLOAD-001d | End User | Upload .srt subtitle file -> 200"""
        srt_content = b"1\n00:00:01,000 --> 00:00:04,000\nHello world\n"
        resp = client.post(
            "/api/upload",
            files={"file": ("sub.srt", io.BytesIO(srt_content), "text/plain")},
        )
        assert resp.status_code == 200


class TestUploadZeroByte:
    """QA Destroyer persona — empty file rejection."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.mark.p1
    def test_upload_002_zero_byte_file_rejected(self, client):
        """UPLOAD-002 | QA Destroyer | Zero-byte file -> 400"""
        resp = client.post(
            "/api/upload",
            files={"file": ("empty.txt", io.BytesIO(b""), "text/plain")},
        )
        assert resp.status_code == 400
        assert "empty" in resp.json()["detail"].lower()


class TestUploadPathTraversal:
    """Security Auditor persona — path traversal prevention."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.mark.p0
    def test_upload_003_path_traversal_in_filename(self, client):
        """UPLOAD-003 | Security Auditor | Path traversal in filename -> file saved safely"""
        # The filename contains traversal, but uuid prefix should prevent any damage
        content = b"Some content to write"
        resp = client.post(
            "/api/upload",
            files={"file": ("../../etc/passwd.txt", io.BytesIO(content), "text/plain")},
        )
        # Should either reject or safely save with sanitized name
        if resp.status_code == 200:
            server_path = resp.json()["server_path"]
            # Verify the file is within uploads directory, not in /etc
            assert "/etc/" not in server_path
            assert "uploads" in server_path


class TestUploadFileTypeValidation:
    """Security Auditor persona — file type restrictions."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.mark.p1
    def test_upload_004_executable_rejected(self, client):
        """UPLOAD-004 | Security Auditor | .exe file -> 400"""
        resp = client.post(
            "/api/upload",
            files={"file": ("malware.exe", io.BytesIO(b"MZ\x90"), "application/octet-stream")},
        )
        assert resp.status_code == 400
        assert "invalid file type" in resp.json()["detail"].lower()

    @pytest.mark.p1
    def test_upload_004b_py_file_rejected(self, client):
        """UPLOAD-004b | Security Auditor | .py file -> 400"""
        resp = client.post(
            "/api/upload",
            files={"file": ("script.py", io.BytesIO(b"import os"), "text/x-python")},
        )
        assert resp.status_code == 400

    @pytest.mark.p1
    def test_upload_004c_sh_file_rejected(self, client):
        """UPLOAD-004c | Security Auditor | .sh file -> 400"""
        resp = client.post(
            "/api/upload",
            files={"file": ("hack.sh", io.BytesIO(b"#!/bin/bash\nrm -rf /"), "text/x-sh")},
        )
        assert resp.status_code == 400

    @pytest.mark.p1
    def test_upload_004d_double_extension_rejected(self, client):
        """UPLOAD-004d | Security Auditor | .txt.exe double extension -> 400"""
        resp = client.post(
            "/api/upload",
            files={"file": ("readme.txt.exe", io.BytesIO(b"MZ"), "application/octet-stream")},
        )
        assert resp.status_code == 400


class TestUploadMaxSize:
    """QA Destroyer persona — size limit enforcement."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.mark.p0
    def test_upload_005_file_over_max_size(self, client):
        """UPLOAD-005 | QA Destroyer | File > MAX_UPLOAD_SIZE_MB -> 400"""
        # Use a very small max to test without creating huge files
        with patch.dict(os.environ, {"MAX_UPLOAD_SIZE_MB": "0"}):
            content = b"x" * 1024  # 1KB > 0MB
            resp = client.post(
                "/api/upload",
                files={"file": ("big.txt", io.BytesIO(content), "text/plain")},
            )
        assert resp.status_code == 400
        assert "too large" in resp.json()["detail"].lower()


class TestUploadMIMEValidation:
    """Security Auditor persona — magic byte validation."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.mark.p0
    def test_upload_006_fake_pdf_rejected(self, client):
        """UPLOAD-006 | Security Auditor | Non-PDF content with .pdf extension -> 400"""
        resp = client.post(
            "/api/upload",
            files={"file": ("fake.pdf", io.BytesIO(b"This is not a PDF"), "application/pdf")},
        )
        assert resp.status_code == 400
        assert "magic bytes" in resp.json()["detail"].lower()

    @pytest.mark.p0
    def test_upload_006b_fake_docx_rejected(self, client):
        """UPLOAD-006b | Security Auditor | Non-DOCX content with .docx extension -> 400"""
        resp = client.post(
            "/api/upload",
            files={"file": ("fake.docx", io.BytesIO(b"Not a ZIP/DOCX"), "application/vnd.openxmlformats")},
        )
        assert resp.status_code == 400
        assert "magic bytes" in resp.json()["detail"].lower()


class TestAnalyzeEndpoint:
    """End User persona — file analysis."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.mark.p1
    def test_analyze_001_valid_file(self, client, sample_txt_file):
        """ANALYZE-001 | End User | Analyze valid text file -> word count + language"""
        with patch("api.routes.uploads.validate_project_path", return_value=sample_txt_file), \
             patch("api.routes.uploads.read_document", return_value="This is test content " * 100):
            resp = client.post("/api/analyze", json={"file_path": str(sample_txt_file)})

        assert resp.status_code == 200
        data = resp.json()
        assert data["word_count"] > 0
        assert data["character_count"] > 0
        assert data["detected_language"] in ["Tiếng Anh", "Tiếng Việt", "Trung/Nhật"]
        assert data["chunks_estimate"] >= 1

    @pytest.mark.p0
    def test_analyze_002_path_traversal_blocked(self, client):
        """ANALYZE-002 | Security | Path traversal in analyze -> 403"""
        with patch("api.routes.uploads.validate_project_path", side_effect=ValueError("outside project")):
            resp = client.post("/api/analyze", json={"file_path": "../../etc/passwd"})
        assert resp.status_code == 403
        assert "access denied" in resp.json()["detail"].lower()

    @pytest.mark.p1
    def test_analyze_003_file_not_found(self, client):
        """ANALYZE-003 | QA Destroyer | Analyze non-existent file -> 404"""
        nonexistent = Path("/tmp/nonexistent_rri_test_file.txt")
        with patch("api.routes.uploads.validate_project_path", return_value=nonexistent):
            resp = client.post("/api/analyze", json={"file_path": str(nonexistent)})
        assert resp.status_code == 404

    @pytest.mark.p1
    def test_analyze_004_vietnamese_detection(self, client, tmp_path):
        """ANALYZE-004 | BA | Vietnamese text detected correctly"""
        vi_text = "Xin chào thế giới. Đây là một bài kiểm tra bằng tiếng Việt. " * 50
        f = tmp_path / "vi.txt"
        f.write_text(vi_text)
        with patch("api.routes.uploads.validate_project_path", return_value=f), \
             patch("api.routes.uploads.read_document", return_value=vi_text):
            resp = client.post("/api/analyze", json={"file_path": str(f)})
        assert resp.status_code == 200
        assert resp.json()["detected_language"] == "Tiếng Việt"

    @pytest.mark.p1
    def test_analyze_005_cjk_detection(self, client, tmp_path):
        """ANALYZE-005 | BA | CJK text detected correctly"""
        cjk_text = "这是一个测试文档。" * 100  # Chinese characters
        f = tmp_path / "zh.txt"
        f.write_text(cjk_text)
        with patch("api.routes.uploads.validate_project_path", return_value=f), \
             patch("api.routes.uploads.read_document", return_value=cjk_text):
            resp = client.post("/api/analyze", json={"file_path": str(f)})
        assert resp.status_code == 200
        assert resp.json()["detected_language"] == "Trung/Nhật"
