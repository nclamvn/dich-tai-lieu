"""
E2E API Tests for AI Publisher Pro

Tests API endpoints for:
- Health check
- Job creation with various options
- Job status retrieval
- Cover image handling

Run: pytest tests/e2e/test_api_endpoints.py -v
"""

import pytest
import httpx
import base64
from pathlib import Path

BASE_URL = "http://localhost:3000"


# ============================================================
# TC-API-01: Health Check
# ============================================================

def test_health_check(check_server_running, server_url):
    """API should return healthy status"""
    response = httpx.get(f"{server_url}/health")

    assert response.status_code == 200
    data = response.json()
    assert data.get("status") in ["healthy", "ok"]


# ============================================================
# TC-API-02: Create Job - Basic (No Cover, No Images)
# ============================================================

def test_create_job_basic(check_server_running, server_url, sample_text_only_pdf):
    """Create job without cover and image extraction"""
    # Upload file first
    with open(sample_text_only_pdf, 'rb') as f:
        files = {'file': ('test.pdf', f, 'application/pdf')}
        upload_response = httpx.post(
            f"{server_url}/api/upload",
            files=files,
            timeout=30.0
        )

    assert upload_response.status_code == 200
    upload_data = upload_response.json()
    file_path = upload_data.get('file_path') or upload_data.get('path')

    # Create job
    payload = {
        "job_name": "Test Job Basic",
        "input_file": file_path,
        "output_file": "/tmp/test_output.docx",
        "source_lang": "en",
        "target_lang": "vi",
        "output_format": "docx",
        "include_images": False
    }

    response = httpx.post(
        f"{server_url}/api/jobs",
        json=payload,
        timeout=30.0
    )

    assert response.status_code == 201
    data = response.json()
    assert "job_id" in data


# ============================================================
# TC-API-03: Create Job - With Cover Image
# ============================================================

def test_create_job_with_cover(check_server_running, server_url, sample_text_only_pdf, sample_cover_image_b64):
    """Create job with cover image"""
    # Upload file first
    with open(sample_text_only_pdf, 'rb') as f:
        files = {'file': ('test.pdf', f, 'application/pdf')}
        upload_response = httpx.post(
            f"{server_url}/api/upload",
            files=files,
            timeout=30.0
        )

    assert upload_response.status_code == 200
    upload_data = upload_response.json()
    file_path = upload_data.get('file_path') or upload_data.get('path')

    # Create job with cover
    payload = {
        "job_name": "Test Job With Cover",
        "input_file": file_path,
        "output_file": "/tmp/test_output_cover.docx",
        "source_lang": "en",
        "target_lang": "vi",
        "output_format": "docx",
        "cover_image": sample_cover_image_b64,
        "include_images": False
    }

    response = httpx.post(
        f"{server_url}/api/jobs",
        json=payload,
        timeout=30.0
    )

    assert response.status_code == 201
    data = response.json()
    assert "job_id" in data

    # Verify cover_image is in metadata
    job_id = data["job_id"]
    status_response = httpx.get(f"{server_url}/api/jobs/{job_id}")
    assert status_response.status_code == 200
    job_data = status_response.json()

    # Check metadata contains cover_image
    metadata = job_data.get("metadata", {})
    assert metadata.get("cover_image") is not None or "cover_image" in str(metadata)


# ============================================================
# TC-API-04: Create Job - With Image Extraction
# ============================================================

def test_create_job_with_image_extraction(check_server_running, server_url, sample_with_images_pdf):
    """Create job with image extraction enabled"""
    # Upload file first
    with open(sample_with_images_pdf, 'rb') as f:
        files = {'file': ('test_images.pdf', f, 'application/pdf')}
        upload_response = httpx.post(
            f"{server_url}/api/upload",
            files=files,
            timeout=30.0
        )

    assert upload_response.status_code == 200
    upload_data = upload_response.json()
    file_path = upload_data.get('file_path') or upload_data.get('path')

    # Create job with image extraction
    payload = {
        "job_name": "Test Job With Images",
        "input_file": file_path,
        "output_file": "/tmp/test_output_images.docx",
        "source_lang": "en",
        "target_lang": "vi",
        "output_format": "docx",
        "include_images": True
    }

    response = httpx.post(
        f"{server_url}/api/jobs",
        json=payload,
        timeout=30.0
    )

    assert response.status_code == 201
    data = response.json()
    assert "job_id" in data


# ============================================================
# TC-API-05: Create Job - Full Options
# ============================================================

def test_create_job_full_options(check_server_running, server_url, sample_with_images_pdf, sample_cover_image_b64):
    """Create job with all options enabled"""
    # Upload file first
    with open(sample_with_images_pdf, 'rb') as f:
        files = {'file': ('test_full.pdf', f, 'application/pdf')}
        upload_response = httpx.post(
            f"{server_url}/api/upload",
            files=files,
            timeout=30.0
        )

    assert upload_response.status_code == 200
    upload_data = upload_response.json()
    file_path = upload_data.get('file_path') or upload_data.get('path')

    # Create job with all options
    payload = {
        "job_name": "Test Job Full",
        "input_file": file_path,
        "output_file": "/tmp/test_output_full.docx",
        "source_lang": "en",
        "target_lang": "vi",
        "output_format": "docx",
        "cover_image": sample_cover_image_b64,
        "include_images": True,
        "ui_layout_mode": "professional"
    }

    response = httpx.post(
        f"{server_url}/api/jobs",
        json=payload,
        timeout=30.0
    )

    assert response.status_code == 201
    data = response.json()
    assert "job_id" in data


# ============================================================
# TC-API-06: Get Job Status
# ============================================================

def test_get_job_status(check_server_running, server_url, sample_text_only_pdf):
    """Get job status after creation"""
    # Create job first
    with open(sample_text_only_pdf, 'rb') as f:
        files = {'file': ('test.pdf', f, 'application/pdf')}
        upload_response = httpx.post(
            f"{server_url}/api/upload",
            files=files,
            timeout=30.0
        )

    upload_data = upload_response.json()
    file_path = upload_data.get('file_path') or upload_data.get('path')

    payload = {
        "job_name": "Test Job Status",
        "input_file": file_path,
        "output_file": "/tmp/test_status.docx",
        "source_lang": "en",
        "target_lang": "vi"
    }

    create_response = httpx.post(
        f"{server_url}/api/jobs",
        json=payload,
        timeout=30.0
    )
    job_id = create_response.json()["job_id"]

    # Get status
    status_response = httpx.get(f"{server_url}/api/jobs/{job_id}")

    assert status_response.status_code == 200
    data = status_response.json()
    assert data["job_id"] == job_id
    assert "status" in data


# ============================================================
# TC-API-07: Job Not Found
# ============================================================

def test_job_not_found(check_server_running, server_url):
    """API should return 404 for non-existent job"""
    response = httpx.get(f"{server_url}/api/jobs/nonexistent-job-id-12345")

    assert response.status_code == 404


# ============================================================
# TC-API-08: List Jobs
# ============================================================

def test_list_jobs(check_server_running, server_url):
    """API should return list of jobs"""
    response = httpx.get(f"{server_url}/api/jobs")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, (list, dict))


# ============================================================
# TC-API-09: Queue Stats
# ============================================================

def test_queue_stats(check_server_running, server_url):
    """API should return queue statistics"""
    response = httpx.get(f"{server_url}/api/stats")

    # May be /api/stats or /api/queue/stats
    if response.status_code == 404:
        response = httpx.get(f"{server_url}/api/queue/stats")

    assert response.status_code == 200
    data = response.json()
    # Should have some stats fields
    assert isinstance(data, dict)
