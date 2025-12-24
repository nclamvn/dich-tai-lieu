#!/usr/bin/env python3
"""
Phase 4.2 - PDF Export Adapter

Converts DOCX files to PDF using multiple strategies:
1. LibreOffice Headless (primary) - Free, cross-platform, high-quality
2. CloudConvert API (fallback) - Cloud-based conversion service

Requirements:
- LibreOffice: brew install libreoffice (macOS) or apt-get install libreoffice (Linux)
- CloudConvert API Key (optional): Set CLOUDCONVERT_API_KEY environment variable
"""

import subprocess
import os
import shutil
from pathlib import Path
from typing import Optional, Tuple, List
import requests
import time

from config.logging_config import get_logger
logger = get_logger(__name__)

# Font verification support (optional dependency)
try:
    from PyPDF2 import PdfReader
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False
    logger.debug("PyPDF2 not available - font verification will be skipped")


class PDFConversionError(Exception):
    """Raised when PDF conversion fails."""
    pass


def is_libreoffice_available() -> bool:
    """
    Check if LibreOffice is installed and available.

    Returns:
        True if LibreOffice is available, False otherwise.
    """
    # Common LibreOffice executable locations
    possible_paths = [
        "soffice",  # In PATH
        "libreoffice",  # In PATH
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",  # macOS
        "/usr/bin/soffice",  # Linux
        "/usr/bin/libreoffice",  # Linux
    ]

    for path in possible_paths:
        try:
            result = subprocess.run(
                [path, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                logger.info(f"LibreOffice found: {path}")
                logger.debug(f"LibreOffice version: {result.stdout.strip()}")
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue

    return False


def _get_libreoffice_path() -> Optional[str]:
    """
    Get the path to the LibreOffice executable.

    Returns:
        Path to soffice executable, or None if not found.
    """
    possible_paths = [
        "soffice",
        "libreoffice",
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
        "/usr/bin/soffice",
        "/usr/bin/libreoffice",
    ]

    for path in possible_paths:
        if shutil.which(path) or os.path.exists(path):
            return path

    return None


def convert_docx_to_pdf_libreoffice(
    docx_path: Path,
    output_pdf_path: Optional[Path] = None,
    timeout: int = 60
) -> Path:
    """
    Convert DOCX to PDF using LibreOffice headless mode.

    Args:
        docx_path: Path to input DOCX file.
        output_pdf_path: Path to output PDF file (optional, auto-generated if None).
        timeout: Conversion timeout in seconds.

    Returns:
        Path to generated PDF file.

    Raises:
        PDFConversionError: If conversion fails.
    """
    if not docx_path.exists():
        raise PDFConversionError(f"Input DOCX file not found: {docx_path}")

    soffice = _get_libreoffice_path()
    if not soffice:
        raise PDFConversionError(
            "LibreOffice not found. Install with:\n"
            "  macOS: brew install libreoffice\n"
            "  Linux: apt-get install libreoffice"
        )

    # Determine output directory and file name
    if output_pdf_path:
        output_dir = output_pdf_path.parent
        output_dir.mkdir(parents=True, exist_ok=True)
    else:
        output_dir = docx_path.parent
        output_pdf_path = output_dir / f"{docx_path.stem}.pdf"

    # LibreOffice converts to the output directory with the same base name
    # So we need to use the input file's directory for conversion, then move if needed
    temp_output_dir = docx_path.parent
    expected_pdf = temp_output_dir / f"{docx_path.stem}.pdf"

    logger.info(f"Converting {docx_path} to PDF using LibreOffice...")
    logger.debug(f"LibreOffice path: {soffice}")
    logger.debug(f"Output directory: {temp_output_dir}")

    # Note on font embedding: LibreOffice's headless mode has limited control over
    # font embedding during PDF export. To ensure proper Vietnamese rendering:
    # 1. Use widely-available fonts (Times New Roman, Arial) in source DOCX
    # 2. LibreOffice will attempt to embed fonts automatically
    # 3. If rendering issues occur, fonts may not be installed on conversion system
    logger.info("Font embedding: Using Times New Roman ensures compatibility with Vietnamese characters")

    try:
        # Run LibreOffice in headless mode
        # --convert-to pdf: Convert to PDF format
        # --outdir: Output directory
        #
        # Note: LibreOffice CLI doesn't support advanced PDF export options like:
        # - Explicit font embedding flags
        # - PDF/A compliance settings
        # - Subset font embedding
        # These would require using LibreOffice's UNO API or GUI automation,
        # which is beyond the scope of this headless conversion.
        cmd = [
            soffice,
            "--headless",
            "--convert-to", "pdf",
            "--outdir", str(temp_output_dir),
            str(docx_path)
        ]

        logger.debug(f"Running command: {' '.join(cmd)}")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        if result.returncode != 0:
            logger.error(f"LibreOffice conversion failed with code {result.returncode}")
            logger.error(f"STDOUT: {result.stdout}")
            logger.error(f"STDERR: {result.stderr}")
            raise PDFConversionError(
                f"LibreOffice conversion failed: {result.stderr or result.stdout}"
            )

        # Check if PDF was created
        if not expected_pdf.exists():
            raise PDFConversionError(
                f"PDF file not created at expected location: {expected_pdf}"
            )

        # Move to final output path if different
        if expected_pdf != output_pdf_path:
            if output_pdf_path.exists():
                output_pdf_path.unlink()  # Remove existing file
            shutil.move(str(expected_pdf), str(output_pdf_path))

        file_size = output_pdf_path.stat().st_size
        logger.info(f"PDF created successfully: {output_pdf_path} ({file_size:,} bytes)")

        # Phase 4.2: Verify font embedding for Vietnamese character support
        font_check = verify_font_embedding(output_pdf_path)
        if font_check.get("warning"):
            logger.warning(f"Font embedding issue: {font_check['warning']}")
            if font_check.get("recommendation"):
                logger.info(f"Recommendation: {font_check['recommendation']}")

        return output_pdf_path

    except subprocess.TimeoutExpired:
        logger.error(f"LibreOffice conversion timed out after {timeout}s")
        raise PDFConversionError(f"Conversion timed out after {timeout} seconds")
    except Exception as e:
        logger.error(f"LibreOffice conversion error: {e}")
        raise PDFConversionError(f"Conversion failed: {e}")


def convert_docx_to_pdf_cloudconvert(
    docx_path: Path,
    output_pdf_path: Optional[Path] = None,
    api_key: Optional[str] = None,
    timeout: int = 300
) -> Path:
    """
    Convert DOCX to PDF using CloudConvert API.

    Args:
        docx_path: Path to input DOCX file.
        output_pdf_path: Path to output PDF file (optional, auto-generated if None).
        api_key: CloudConvert API key (reads from CLOUDCONVERT_API_KEY env var if None).
        timeout: API request timeout in seconds.

    Returns:
        Path to generated PDF file.

    Raises:
        PDFConversionError: If conversion fails.
    """
    if not docx_path.exists():
        raise PDFConversionError(f"Input DOCX file not found: {docx_path}")

    # Get API key
    api_key = api_key or os.getenv("CLOUDCONVERT_API_KEY")
    if not api_key:
        raise PDFConversionError(
            "CloudConvert API key not found. Set CLOUDCONVERT_API_KEY environment variable.\n"
            "Get a free API key at: https://cloudconvert.com/register"
        )

    # Determine output path
    if not output_pdf_path:
        output_pdf_path = docx_path.parent / f"{docx_path.stem}.pdf"

    logger.info(f"Converting {docx_path} to PDF using CloudConvert API...")

    try:
        # Step 1: Create a job
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        job_payload = {
            "tasks": {
                "import-docx": {
                    "operation": "import/upload"
                },
                "convert-to-pdf": {
                    "operation": "convert",
                    "input": "import-docx",
                    "output_format": "pdf"
                },
                "export-pdf": {
                    "operation": "export/url",
                    "input": "convert-to-pdf"
                }
            }
        }

        logger.debug("Creating CloudConvert job...")
        response = requests.post(
            "https://api.cloudconvert.com/v2/jobs",
            json=job_payload,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()
        job_data = response.json()

        # Step 2: Upload DOCX file
        upload_task = job_data["data"]["tasks"][0]
        upload_url = upload_task["result"]["form"]["url"]
        upload_params = upload_task["result"]["form"]["parameters"]

        logger.debug(f"Uploading DOCX to CloudConvert...")
        with open(docx_path, "rb") as f:
            files = {"file": f}
            response = requests.post(
                upload_url,
                data=upload_params,
                files=files,
                timeout=60
            )
            response.raise_for_status()

        # Step 3: Wait for conversion to complete
        job_id = job_data["data"]["id"]
        logger.debug(f"Waiting for conversion (job_id: {job_id})...")

        start_time = time.time()
        while time.time() - start_time < timeout:
            response = requests.get(
                f"https://api.cloudconvert.com/v2/jobs/{job_id}",
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            job_status = response.json()

            status = job_status["data"]["status"]
            logger.debug(f"Job status: {status}")

            if status == "finished":
                # Step 4: Download PDF
                export_task = [
                    t for t in job_status["data"]["tasks"]
                    if t["name"] == "export-pdf"
                ][0]
                download_url = export_task["result"]["files"][0]["url"]

                logger.debug(f"Downloading PDF from CloudConvert...")
                response = requests.get(download_url, timeout=60)
                response.raise_for_status()

                # Save PDF
                output_pdf_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_pdf_path, "wb") as f:
                    f.write(response.content)

                file_size = output_pdf_path.stat().st_size
                logger.info(
                    f"PDF created successfully via CloudConvert: "
                    f"{output_pdf_path} ({file_size:,} bytes)"
                )

                return output_pdf_path

            elif status == "error":
                error_msg = job_status["data"].get("message", "Unknown error")
                raise PDFConversionError(f"CloudConvert conversion failed: {error_msg}")

            # Wait before polling again
            time.sleep(3)

        raise PDFConversionError(f"CloudConvert conversion timed out after {timeout}s")

    except requests.exceptions.RequestException as e:
        logger.error(f"CloudConvert API error: {e}")
        raise PDFConversionError(f"CloudConvert API request failed: {e}")
    except Exception as e:
        logger.error(f"CloudConvert conversion error: {e}")
        raise PDFConversionError(f"Conversion failed: {e}")


def convert_docx_to_pdf(
    docx_path: Path,
    output_pdf_path: Optional[Path] = None,
    method: str = "auto",
    cloudconvert_api_key: Optional[str] = None,
    timeout: int = 60
) -> Tuple[Path, str]:
    """
    Convert DOCX to PDF using the best available method.

    Args:
        docx_path: Path to input DOCX file.
        output_pdf_path: Path to output PDF file (optional).
        method: Conversion method - "auto", "libreoffice", or "cloudconvert".
        cloudconvert_api_key: CloudConvert API key (for cloudconvert method).
        timeout: Conversion timeout in seconds.

    Returns:
        Tuple of (pdf_path, method_used).

    Raises:
        PDFConversionError: If all conversion methods fail.
    """
    docx_path = Path(docx_path)
    if output_pdf_path:
        output_pdf_path = Path(output_pdf_path)

    if method == "libreoffice":
        # Force LibreOffice method
        pdf_path = convert_docx_to_pdf_libreoffice(docx_path, output_pdf_path, timeout)
        return pdf_path, "libreoffice"

    elif method == "cloudconvert":
        # Force CloudConvert method
        pdf_path = convert_docx_to_pdf_cloudconvert(
            docx_path, output_pdf_path, cloudconvert_api_key, timeout
        )
        return pdf_path, "cloudconvert"

    else:  # method == "auto"
        # Phase 4.3: Auto-fallback with font verification
        # Try LibreOffice first, verify font embedding, fallback to CloudConvert if needed
        errors = []
        libreoffice_pdf_path = None

        # Try LibreOffice
        if is_libreoffice_available():
            try:
                logger.info("Attempting PDF conversion with LibreOffice...")
                libreoffice_pdf_path = convert_docx_to_pdf_libreoffice(docx_path, output_pdf_path, timeout)

                # Phase 4.3: Verify font embedding (self-healing system)
                font_check = verify_font_embedding(libreoffice_pdf_path)

                # Check if fallback is needed
                needs_fallback = (
                    font_check.get("non_embedded_fonts") or  # Has non-embedded fonts
                    not font_check.get("has_vietnamese_support")  # No Vietnamese fonts
                )

                if not needs_fallback:
                    logger.info("✅ LibreOffice conversion successful with proper font embedding")
                    return libreoffice_pdf_path, "libreoffice"
                else:
                    # Font embedding issue detected
                    logger.warning(
                        f"⚠️  Font embedding issue detected: {font_check.get('warning')}\n"
                        f"   Recommendation: {font_check.get('recommendation', 'Use CloudConvert for better font support')}"
                    )

                    # Check if CloudConvert is available for fallback
                    if cloudconvert_api_key or os.getenv("CLOUDCONVERT_API_KEY"):
                        logger.info("🔄 Falling back to CloudConvert for reliable font embedding...")
                        # Delete the improperly embedded PDF
                        libreoffice_pdf_path.unlink(missing_ok=True)
                        libreoffice_pdf_path = None  # Clear path to trigger fallback
                        errors.append(f"LibreOffice: Font embedding issue - {font_check.get('warning')}")
                    else:
                        # No CloudConvert API key - use LibreOffice result despite font issues
                        logger.warning(
                            "⚠️  CloudConvert not configured - using LibreOffice result despite font issues.\n"
                            "   Set CLOUDCONVERT_API_KEY environment variable for automatic fallback."
                        )
                        return libreoffice_pdf_path, "libreoffice"

            except PDFConversionError as e:
                errors.append(f"LibreOffice: {e}")
                logger.warning(f"LibreOffice conversion failed: {e}")
        else:
            errors.append("LibreOffice: Not installed")
            logger.info("LibreOffice not available, skipping...")

        # Try CloudConvert as fallback
        if cloudconvert_api_key or os.getenv("CLOUDCONVERT_API_KEY"):
            try:
                logger.info("Attempting PDF conversion with CloudConvert API...")
                pdf_path = convert_docx_to_pdf_cloudconvert(
                    docx_path, output_pdf_path, cloudconvert_api_key, timeout * 5
                )

                # Verify CloudConvert result
                font_check = verify_font_embedding(pdf_path)
                if font_check.get("warning"):
                    logger.warning(f"Note: {font_check.get('warning')}")
                else:
                    logger.info("✅ CloudConvert fallback successful with proper font embedding")

                return pdf_path, "cloudconvert"
            except PDFConversionError as e:
                errors.append(f"CloudConvert: {e}")
                logger.warning(f"CloudConvert conversion failed: {e}")
        else:
            errors.append("CloudConvert: No API key configured")
            logger.info("CloudConvert API key not configured, skipping...")

        # All methods failed
        error_summary = "\n".join(f"  - {err}" for err in errors)
        raise PDFConversionError(
            f"All PDF conversion methods failed:\n{error_summary}\n\n"
            "Solutions:\n"
            "  1. Install LibreOffice: brew install libreoffice (macOS)\n"
            "  2. Set CLOUDCONVERT_API_KEY environment variable with API key from cloudconvert.com"
        )


def verify_pdf_quality(pdf_path: Path) -> dict:
    """
    Verify the quality of the generated PDF.

    This is a basic check that verifies the file exists and has content.
    More sophisticated checks (font embedding, equation rendering, etc.)
    would require PyPDF2 or similar libraries.

    Args:
        pdf_path: Path to PDF file to verify.

    Returns:
        Dictionary with quality check results.
    """
    if not pdf_path.exists():
        return {
            "valid": False,
            "error": "PDF file not found"
        }

    file_size = pdf_path.stat().st_size

    if file_size < 100:
        return {
            "valid": False,
            "error": f"PDF file too small ({file_size} bytes), likely corrupted"
        }

    # Basic validity check: PDFs start with "%PDF-"
    with open(pdf_path, "rb") as f:
        header = f.read(5)
        if header != b"%PDF-":
            return {
                "valid": False,
                "error": "Invalid PDF header"
            }

    return {
        "valid": True,
        "file_size": file_size,
        "file_size_mb": file_size / (1024 * 1024)
    }


def verify_font_embedding(pdf_path: Path) -> dict:
    """
    Verify font embedding in PDF file.

    Phase 4.2: Font embedding verification for Vietnamese character support.
    Checks if fonts are properly embedded to ensure Vietnamese diacritics render correctly.

    Args:
        pdf_path: Path to PDF file to check.

    Returns:
        Dictionary with font embedding status:
        {
            "fonts_checked": bool,
            "embedded_fonts": List[str],
            "non_embedded_fonts": List[str],
            "has_vietnamese_support": bool,
            "warning": str (optional),
            "recommendation": str (optional)
        }
    """
    result = {
        "fonts_checked": False,
        "embedded_fonts": [],
        "non_embedded_fonts": [],
        "has_vietnamese_support": None,
        "warning": None,
        "recommendation": None
    }

    if not PYPDF2_AVAILABLE:
        result["warning"] = "PyPDF2 not available - font verification skipped"
        result["recommendation"] = "Install PyPDF2 for font verification: pip install PyPDF2"
        logger.debug("PyPDF2 not available - skipping font verification")
        return result

    if not pdf_path.exists():
        result["warning"] = "PDF file not found"
        return result

    try:
        reader = PdfReader(str(pdf_path))

        # Check fonts in PDF
        embedded_fonts = []
        non_embedded_fonts = []

        # Iterate through pages to find fonts
        for page_num, page in enumerate(reader.pages):
            if '/Font' in page.get('/Resources', {}):
                fonts = page['/Resources']['/Font']

                for font_name in fonts:
                    font_obj = fonts[font_name]

                    # Check if font is embedded (has /FontFile, /FontFile2, or /FontFile3)
                    is_embedded = any(
                        key in font_obj.get_object()
                        for key in ['/FontFile', '/FontFile2', '/FontFile3']
                    )

                    # Get font base name
                    base_font = font_obj.get_object().get('/BaseFont', 'Unknown')
                    if isinstance(base_font, str):
                        font_display_name = base_font.replace('/', '')
                    else:
                        font_display_name = str(base_font)

                    if is_embedded:
                        if font_display_name not in embedded_fonts:
                            embedded_fonts.append(font_display_name)
                    else:
                        if font_display_name not in non_embedded_fonts:
                            non_embedded_fonts.append(font_display_name)

        result["fonts_checked"] = True
        result["embedded_fonts"] = embedded_fonts
        result["non_embedded_fonts"] = non_embedded_fonts

        # Check for Vietnamese-compatible fonts (Times New Roman, Arial, etc.)
        vietnamese_fonts = [
            'TimesNewRoman', 'Times-Roman', 'Times',
            'Arial', 'Liberation', 'DejaVu'
        ]

        has_vietnamese_font = any(
            any(vn_font.lower() in font.lower() for vn_font in vietnamese_fonts)
            for font in embedded_fonts
        )

        result["has_vietnamese_support"] = has_vietnamese_font

        # Generate warnings and recommendations
        if non_embedded_fonts:
            result["warning"] = (
                f"Some fonts are not embedded: {', '.join(non_embedded_fonts)}. "
                "Vietnamese characters may not display correctly."
            )
            result["recommendation"] = (
                "1. Ensure Times New Roman is installed system-wide\n"
                "2. Try using CloudConvert API for better font handling\n"
                "3. Set CLOUDCONVERT_API_KEY environment variable"
            )
            logger.warning(f"PDF has non-embedded fonts: {non_embedded_fonts}")

        if not has_vietnamese_font and embedded_fonts:
            result["warning"] = (
                "No Vietnamese-compatible fonts detected. "
                "Vietnamese diacritics may appear as black squares."
            )
            result["recommendation"] = (
                "Regenerate PDF with Times New Roman font:\n"
                "1. Install Times New Roman: brew install font-times-new-roman\n"
                "2. Or use CloudConvert API for cloud-based conversion"
            )
            logger.warning("No Vietnamese-compatible fonts found in PDF")

        logger.info(
            f"Font check: {len(embedded_fonts)} embedded, "
            f"{len(non_embedded_fonts)} non-embedded, "
            f"Vietnamese support: {has_vietnamese_font}"
        )

    except Exception as e:
        result["warning"] = f"Font verification failed: {str(e)}"
        logger.error(f"Font verification error: {e}")

    return result


if __name__ == "__main__":
    # Quick test
    import sys

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    logger.info("=" * 50)
    logger.info("Phase 4.2 - PDF Export Adapter Test")
    logger.info("=" * 50)

    logger.info(f"LibreOffice available: {is_libreoffice_available()}")
    logger.info(f"CloudConvert API key: {'Yes' if os.getenv('CLOUDCONVERT_API_KEY') else 'No'}")

    if len(sys.argv) > 1:
        input_docx = Path(sys.argv[1])
        if input_docx.exists():
            try:
                pdf_path, method = convert_docx_to_pdf(input_docx)
                logger.info(f"Conversion successful using {method}")
                logger.info(f"Output: {pdf_path}")

                # Phase 4.2: Basic quality check
                quality = verify_pdf_quality(pdf_path)
                logger.info(f"Basic quality check: {quality}")

                # Phase 4.2: Font embedding verification
                logger.info("Phase 4.2: Font Embedding Verification")
                logger.info("=" * 50)
                font_check = verify_font_embedding(pdf_path)
                if font_check["fonts_checked"]:
                    logger.info(f"Embedded fonts: {font_check['embedded_fonts']}")
                    logger.info(f"Non-embedded fonts: {font_check['non_embedded_fonts']}")
                    logger.info(f"Vietnamese support: {font_check['has_vietnamese_support']}")
                    if font_check.get("warning"):
                        logger.warning(f"Warning: {font_check['warning']}")
                    if font_check.get("recommendation"):
                        logger.info(f"Recommendation: {font_check['recommendation']}")
                else:
                    logger.info(f"Font check skipped: {font_check.get('warning', 'Unknown')}")
            except PDFConversionError as e:
                logger.error(f"Conversion failed: {e}")
        else:
            logger.error(f"File not found: {input_docx}")
    else:
        logger.info("Usage: python pdf_adapter.py <input.docx>")
