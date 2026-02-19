"""
Unit tests for api/routes/uploads.py — upload, analyze, detect-language endpoints.
"""
import io
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from api.main import app


class TestUploadFile:
    """Test POST /api/upload."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_upload_txt_success(self, client):
        content = b"Hello world, this is a test document."
        files = {"file": ("test.txt", io.BytesIO(content), "text/plain")}
        resp = client.post("/api/upload", files=files)
        assert resp.status_code == 200
        data = resp.json()
        assert data["filename"] == "test.txt"
        assert data["size"] == len(content)
        assert "server_path" in data

    def test_upload_pdf_success(self, client):
        content = b"%PDF-1.4 fake pdf content"
        files = {"file": ("doc.pdf", io.BytesIO(content), "application/pdf")}
        resp = client.post("/api/upload", files=files)
        assert resp.status_code == 200
        assert resp.json()["filename"] == "doc.pdf"

    def test_upload_docx_success(self, client):
        content = b"PK\x03\x04 fake docx"
        files = {"file": ("report.docx", io.BytesIO(content), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        resp = client.post("/api/upload", files=files)
        assert resp.status_code == 200

    def test_upload_srt_success(self, client):
        content = b"1\n00:00:01,000 --> 00:00:02,000\nHello"
        files = {"file": ("sub.srt", io.BytesIO(content), "text/plain")}
        resp = client.post("/api/upload", files=files)
        assert resp.status_code == 200

    def test_upload_invalid_extension(self, client):
        files = {"file": ("script.py", io.BytesIO(b"print('hi')"), "text/plain")}
        resp = client.post("/api/upload", files=files)
        assert resp.status_code == 400
        assert "Invalid file type" in resp.json()["detail"]

    def test_upload_too_large(self, client):
        # Set MAX_UPLOAD_SIZE_MB to 1 for testing
        with patch.dict("os.environ", {"MAX_UPLOAD_SIZE_MB": "1"}):
            big_content = b"x" * (2 * 1024 * 1024)  # 2MB
            files = {"file": ("big.txt", io.BytesIO(big_content), "text/plain")}
            resp = client.post("/api/upload", files=files)
            assert resp.status_code == 400
            assert "too large" in resp.json()["detail"]


class TestAnalyzeFile:
    """Test POST /api/analyze."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_analyze_english_text(self, client, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("The quick brown fox jumps over the lazy dog. " * 100)

        with patch("api.routes.uploads.read_document", return_value=f.read_text()):
            resp = client.post("/api/analyze", json={"file_path": str(f)})

        assert resp.status_code == 200
        data = resp.json()
        assert data["detected_language"] == "Tiếng Anh"
        assert data["word_count"] > 0
        assert data["chunks_estimate"] >= 1

    def test_analyze_vietnamese_text(self, client, tmp_path):
        f = tmp_path / "vi.txt"
        vi_text = "Đây là một đoạn văn bản tiếng Việt có nhiều ký tự đặc biệt như ăâêôơưđ " * 50
        f.write_text(vi_text)

        with patch("api.routes.uploads.read_document", return_value=vi_text):
            resp = client.post("/api/analyze", json={"file_path": str(f)})

        assert resp.status_code == 200
        assert resp.json()["detected_language"] == "Tiếng Việt"

    def test_analyze_chinese_text(self, client, tmp_path):
        f = tmp_path / "zh.txt"
        zh_text = "这是一段中文文本用于测试语言检测功能" * 20
        f.write_text(zh_text)

        with patch("api.routes.uploads.read_document", return_value=zh_text):
            resp = client.post("/api/analyze", json={"file_path": str(f)})

        assert resp.status_code == 200
        assert resp.json()["detected_language"] == "Trung/Nhật"

    def test_analyze_file_not_found(self, client):
        resp = client.post("/api/analyze", json={"file_path": "/nonexistent/file.txt"})
        assert resp.status_code == 500  # wrapped in generic exception handler


class TestDetectLanguage:
    """Test POST /api/v2/detect-language."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_detect_english(self, client):
        text = "The quick brown fox jumps over the lazy dog and the cat sits on the mat"
        with patch("api.routes.uploads.read_document", return_value=text):
            files = {"file": ("doc.txt", io.BytesIO(text.encode()), "text/plain")}
            resp = client.post("/api/v2/detect-language", files=files)

        assert resp.status_code == 200
        data = resp.json()
        assert data["language"] == "en"
        assert data["confidence"] > 0

    def test_detect_vietnamese(self, client):
        text = "Đây là một đoạn văn bản tiếng Việt có nhiều ký tự đặc biệt ăâêôơưđ " * 10
        with patch("api.routes.uploads.read_document", return_value=text):
            files = {"file": ("doc.txt", io.BytesIO(text.encode()), "text/plain")}
            resp = client.post("/api/v2/detect-language", files=files)

        assert resp.status_code == 200
        assert resp.json()["language"] == "vi"

    def test_detect_chinese(self, client):
        text = "这是一段中文文本用于测试语言检测功能这是一段中文文本" * 5
        with patch("api.routes.uploads.read_document", return_value=text):
            files = {"file": ("doc.txt", io.BytesIO(text.encode()), "text/plain")}
            resp = client.post("/api/v2/detect-language", files=files)

        assert resp.status_code == 200
        assert resp.json()["language"] == "zh"

    def test_detect_empty_file(self, client):
        with patch("api.routes.uploads.read_document", return_value=""):
            files = {"file": ("empty.txt", io.BytesIO(b""), "text/plain")}
            resp = client.post("/api/v2/detect-language", files=files)

        assert resp.status_code == 200
        data = resp.json()
        assert data["language"] == "en"
        assert data["confidence"] == 0.5
