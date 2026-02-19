"""
Upload, analyze, and language detection endpoints.
"""

import math
import os
import re
import uuid
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, Request

from api.models import AnalyzeRequest, AnalyzeResponse
from api.services.file_handler import validate_project_path
from core.batch_processor import read_document
from config.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["Uploads"])


@router.post("/api/upload")
async def upload_file(
    request: Request,
    file: UploadFile = File(...)
):
    """
    Upload file for translation

    Accepts: TXT, PDF, DOCX, SRT, MD, EPUB
    Max size: 50MB (configurable)
    Returns: Server file path for job creation

    BIZ-01: Streaming upload (1MB chunks, incremental size check)
    BIZ-02: MIME magic-byte validation after write
    """
    limiter = request.app.state.limiter

    # Validate file type (BIZ-01: added .md and .epub)
    allowed_extensions = [".txt", ".pdf", ".docx", ".srt", ".md", ".epub"]

    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
        )

    # Max size (configurable via MAX_UPLOAD_SIZE_MB env var, default 50MB)
    max_size_mb = int(os.getenv("MAX_UPLOAD_SIZE_MB", "50"))
    max_size_bytes = max_size_mb * 1024 * 1024

    # Create uploads directory if not exists
    upload_dir = Path(__file__).parent.parent.parent / "uploads"
    upload_dir.mkdir(exist_ok=True)

    # Generate unique filename
    unique_filename = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = upload_dir / unique_filename

    # BIZ-01: Stream file to disk in 1MB chunks with incremental size check
    CHUNK_SIZE = 1024 * 1024  # 1MB
    total_written = 0
    try:
        with open(file_path, "wb") as f:
            while True:
                chunk = await file.read(CHUNK_SIZE)
                if not chunk:
                    break
                total_written += len(chunk)
                if total_written > max_size_bytes:
                    # Clean up oversized file
                    f.close()
                    file_path.unlink(missing_ok=True)
                    raise HTTPException(status_code=400, detail=f"File too large (max {max_size_mb}MB)")
                f.write(chunk)
    except HTTPException:
        raise
    except Exception as e:
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

    # BIZ-02: Validate MIME magic bytes after writing
    try:
        with open(file_path, "rb") as f:
            magic_bytes = f.read(8)

        # PDF must start with %PDF
        if file_ext == ".pdf" and not magic_bytes.startswith(b"%PDF"):
            file_path.unlink(missing_ok=True)
            raise HTTPException(status_code=400, detail="Invalid PDF file (magic bytes mismatch)")

        # DOCX and EPUB are ZIP archives — must start with PK
        if file_ext in (".docx", ".epub") and not magic_bytes.startswith(b"PK"):
            file_path.unlink(missing_ok=True)
            raise HTTPException(status_code=400, detail=f"Invalid {file_ext.upper()} file (magic bytes mismatch)")

    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"MIME validation skipped: {e}")

    return {
        "filename": file.filename,
        "server_path": str(file_path),
        "size": total_written,
        "content_type": file.content_type
    }


@router.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze_file(
    request: AnalyzeRequest,
    http_request: Request = None
):
    """
    Analyze uploaded file and return accurate word count and language detection
    """
    try:
        # Validate path stays within project directory (prevent path traversal)
        try:
            file_path = validate_project_path(request.file_path)
        except ValueError:
            raise HTTPException(status_code=403, detail="Access denied: path outside project directory")

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")

        # Extract text from document
        text = read_document(file_path)

        # Detect language using statistical analysis
        cjk_char_pattern = r'[\u4e00-\u9fff]'
        vi_pattern = r'[ăâđêôơưàáảãạèéẻẽẹìíỉĩịòóỏõọùúủũụỳýỷỹỵ]'

        # Count character types for statistical detection
        total_chars = len(re.sub(r'\s', '', text))
        cjk_chars = len(re.findall(cjk_char_pattern, text))
        vi_chars = len(re.findall(vi_pattern, text, re.IGNORECASE))

        # Calculate proportions
        cjk_ratio = cjk_chars / total_chars if total_chars > 0 else 0
        vi_ratio = vi_chars / total_chars if total_chars > 0 else 0

        if cjk_ratio > 0.10:
            detected_lang = 'Trung/Nhật'
            word_count = cjk_chars
        elif vi_ratio > 0.03:
            detected_lang = 'Tiếng Việt'
            words = re.split(r'\s+', text.strip())
            word_count = len([w for w in words if w])
        else:
            detected_lang = 'Tiếng Anh'
            words = re.split(r'\s+', text.strip())
            word_count = len([w for w in words if w])

        # Calculate chunks estimate (3000 words per chunk)
        chunks_estimate = math.ceil(word_count / 3000) if word_count > 0 else 1

        return AnalyzeResponse(
            word_count=word_count,
            character_count=len(text),
            detected_language=detected_lang,
            chunks_estimate=chunks_estimate
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis failed for {request.file_path}: {e}")
        raise HTTPException(status_code=500, detail="Analysis failed. Please check the file and try again.")


@router.post("/api/v2/detect-language")
async def detect_language(file: UploadFile = File(...)):
    """
    Detect language from uploaded file.

    Returns language code (en, zh, ja, ko, fr, de, es, ru, vi) and confidence.
    """
    try:
        # Save uploaded file temporarily
        suffix = Path(file.filename).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        try:
            # Extract text
            text = read_document(Path(tmp_path))
            sample = text[:5000]

            # Character pattern detection
            patterns = {
                'zh': (r'[\u4e00-\u9fff]', 0.10),
                'ja': (r'[\u3040-\u309f\u30a0-\u30ff]', 0.05),
                'ko': (r'[\uac00-\ud7af]', 0.05),
                'ru': (r'[\u0400-\u04ff]', 0.10),
                'vi': (r'[àáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđ]', 0.03),
            }

            total_chars = len(re.sub(r'\s', '', sample))
            if total_chars == 0:
                return {"language": "en", "confidence": 0.5}

            for lang, (pattern, threshold) in patterns.items():
                matches = len(re.findall(pattern, sample, re.IGNORECASE))
                ratio = matches / total_chars
                if ratio > threshold:
                    confidence = min(0.95, ratio * 5)
                    return {"language": lang, "confidence": confidence}

            # European language detection by common words
            word_patterns = {
                'fr': r'\b(le|la|les|de|du|des|et|est|un|une|que|qui|dans|pour|sur|avec)\b',
                'de': r'\b(der|die|das|und|ist|ein|eine|zu|den|von|mit|für|auf|nicht|auch)\b',
                'es': r'\b(el|la|los|las|de|en|y|que|es|un|una|por|con|para|del|al|se)\b',
                'en': r'\b(the|be|to|of|and|a|in|that|have|it|for|not|on|with|he|as|you)\b',
            }

            max_lang = 'en'
            max_count = 0

            for lang, pattern in word_patterns.items():
                count = len(re.findall(pattern, sample, re.IGNORECASE))
                if count > max_count:
                    max_count = count
                    max_lang = lang

            confidence = min(0.9, max_count / 50)
            return {"language": max_lang, "confidence": confidence}

        finally:
            os.unlink(tmp_path)

    except Exception as e:
        logger.error(f"Language detection failed: {e}")
        return {"language": "en", "confidence": 0.5}
