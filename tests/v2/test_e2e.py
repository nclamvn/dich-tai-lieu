#!/usr/bin/env python3
"""
End-to-End Test for APS V2

Tests the complete pipeline with real documents.
"""

import asyncio
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import httpx

BASE_URL = "http://localhost:3001"
TEST_DOCS_DIR = Path(__file__).parent / "test_documents"


async def test_health():
    """Test health endpoint"""
    print("\n" + "="*60)
    print("TEST: Health Check")
    print("="*60)

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/api/v2/health")

        if response.status_code == 200:
            data = response.json()
            print(f"  Status: {data['status']}")
            print(f"   Version: {data['version']}")
            print(f"   Dependencies:")
            for dep, available in data['dependencies'].items():
                status = "OK" if available else "MISSING"
                print(f"     {status} {dep}")
            return True
        else:
            print(f"  Health check failed: {response.status_code}")
            return False


async def test_profiles():
    """Test profiles endpoint"""
    print("\n" + "="*60)
    print("TEST: Publishing Profiles")
    print("="*60)

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/api/v2/profiles")

        if response.status_code == 200:
            data = response.json()
            print(f"  Found {data['total']} profiles:")
            for profile in data['profiles']:
                print(f"   - {profile['id']}: {profile['name']}")
            return True
        else:
            print(f"  Profiles failed: {response.status_code}")
            return False


async def publish_and_wait(
    content: str,
    profile_id: str,
    source_lang: str = "en",
    target_lang: str = "vi",
    output_formats: list = ["docx"],
    filename: str = "test",
    timeout: int = 300,
) -> dict:
    """Publish content and wait for completion"""

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Start job
        response = await client.post(
            f"{BASE_URL}/api/v2/publish/text",
            json={
                "content": content,
                "source_language": source_lang,
                "target_language": target_lang,
                "profile_id": profile_id,
                "output_formats": output_formats,
                "filename": filename,
            }
        )

        if response.status_code != 200:
            return {"error": f"Failed to start job: {response.text}"}

        job = response.json()
        job_id = job["job_id"]
        print(f"   Job started: {job_id}")

        # Poll for completion
        start_time = time.time()
        last_progress = -1

        while time.time() - start_time < timeout:
            await asyncio.sleep(2)

            response = await client.get(f"{BASE_URL}/api/v2/jobs/{job_id}")
            if response.status_code != 200:
                return {"error": f"Failed to get job status: {response.text}"}

            job = response.json()

            # Print progress updates
            if job["progress"] != last_progress:
                stage = job.get('current_stage', '')
                print(f"   [{job['progress']:.0f}%] {stage}")
                last_progress = job["progress"]

            # Check completion
            if job["status"] == "complete":
                elapsed = time.time() - start_time
                job["elapsed_time"] = elapsed
                return job
            elif job["status"] == "failed":
                return {"error": job.get("error", "Unknown error")}

        return {"error": "Timeout waiting for job completion"}


async def test_novel():
    """Test A: Novel translation"""
    print("\n" + "="*60)
    print("TEST A: Novel Translation")
    print("="*60)

    # Load test document
    doc_path = TEST_DOCS_DIR / "novel_sample.txt"
    if not doc_path.exists():
        print(f"  Test document not found: {doc_path}")
        return False

    content = doc_path.read_text(encoding='utf-8')
    print(f"   Input: {len(content)} chars, ~{len(content.split())} words")
    print(f"   Profile: novel")
    print(f"   Direction: en -> vi")

    result = await publish_and_wait(
        content=content,
        profile_id="novel",
        source_lang="en",
        target_lang="vi",
        output_formats=["docx"],
        filename="novel_test",
    )

    if result.get("error"):
        print(f"  Failed: {result['error']}")
        return False

    print(f"\n   COMPLETED!")
    print(f"   Time: {result.get('elapsed_time', 0):.1f}s")

    dna = result.get('dna') or {}
    print(f"   DNA detected genre: {dna.get('genre', 'N/A')}")
    print(f"   Has chapters: {dna.get('has_chapters', False)}")
    print(f"   Chunks: {result.get('chunks_count', 0)}")
    print(f"   Quality: {result.get('quality_level', 'N/A')} ({result.get('quality_score', 0):.2f})")
    print(f"   Outputs: {list(result.get('output_paths', {}).keys())}")

    # Verify outputs
    for fmt, path in result.get('output_paths', {}).items():
        full_path = Path('/Users/mac/translator_project') / path
        if full_path.exists():
            size = full_path.stat().st_size
            print(f"   - {fmt}: {size:,} bytes OK")
        else:
            print(f"   - {fmt}: NOT FOUND at {full_path}")

    return True


async def test_stem():
    """Test B: STEM paper translation"""
    print("\n" + "="*60)
    print("TEST B: STEM Paper Translation")
    print("="*60)

    # Load test document
    doc_path = TEST_DOCS_DIR / "stem_paper.txt"
    if not doc_path.exists():
        print(f"  Test document not found: {doc_path}")
        return False

    content = doc_path.read_text(encoding='utf-8')
    print(f"   Input: {len(content)} chars")
    print(f"   Profile: arxiv_paper")
    print(f"   Direction: en -> vi")
    print(f"   Contains: LaTeX formulas")

    result = await publish_and_wait(
        content=content,
        profile_id="arxiv_paper",
        source_lang="en",
        target_lang="vi",
        output_formats=["docx"],
        filename="stem_test",
    )

    if result.get("error"):
        print(f"  Failed: {result['error']}")
        return False

    print(f"\n   COMPLETED!")
    print(f"   Time: {result.get('elapsed_time', 0):.1f}s")

    dna = result.get('dna') or {}
    print(f"   DNA detected genre: {dna.get('genre', 'N/A')}")
    print(f"   Has formulas: {dna.get('has_formulas', False)}")
    print(f"   Quality: {result.get('quality_level', 'N/A')} ({result.get('quality_score', 0):.2f})")
    print(f"   Outputs: {list(result.get('output_paths', {}).keys())}")

    # Verify outputs
    for fmt, path in result.get('output_paths', {}).items():
        full_path = Path('/Users/mac/translator_project') / path
        if full_path.exists():
            size = full_path.stat().st_size
            print(f"   - {fmt}: {size:,} bytes OK")
        else:
            print(f"   - {fmt}: NOT FOUND")

    return True


async def test_business():
    """Test C: Business report translation"""
    print("\n" + "="*60)
    print("TEST C: Business Report Translation")
    print("="*60)

    # Load test document
    doc_path = TEST_DOCS_DIR / "business_report.txt"
    if not doc_path.exists():
        print(f"  Test document not found: {doc_path}")
        return False

    content = doc_path.read_text(encoding='utf-8')
    print(f"   Input: {len(content)} chars")
    print(f"   Profile: business_report")
    print(f"   Direction: en -> vi")
    print(f"   Contains: tables, statistics")

    result = await publish_and_wait(
        content=content,
        profile_id="business_report",
        source_lang="en",
        target_lang="vi",
        output_formats=["docx"],
        filename="business_test",
    )

    if result.get("error"):
        print(f"  Failed: {result['error']}")
        return False

    print(f"\n   COMPLETED!")
    print(f"   Time: {result.get('elapsed_time', 0):.1f}s")

    dna = result.get('dna') or {}
    print(f"   DNA detected genre: {dna.get('genre', 'N/A')}")
    print(f"   Has tables: {dna.get('has_tables', False)}")
    print(f"   Quality: {result.get('quality_level', 'N/A')} ({result.get('quality_score', 0):.2f})")
    print(f"   Outputs: {list(result.get('output_paths', {}).keys())}")

    # Verify outputs
    for fmt, path in result.get('output_paths', {}).items():
        full_path = Path('/Users/mac/translator_project') / path
        if full_path.exists():
            size = full_path.stat().st_size
            print(f"   - {fmt}: {size:,} bytes OK")
        else:
            print(f"   - {fmt}: NOT FOUND")

    return True


async def run_all_tests():
    """Run all tests"""
    print("\n" + "="*70)
    print("       APS V2 END-TO-END TESTS")
    print("="*70)

    results = {}

    # Health check
    results['health'] = await test_health()
    if not results['health']:
        print("\n  Server not healthy, aborting tests")
        return results

    # Profiles
    results['profiles'] = await test_profiles()

    # Document tests
    results['novel'] = await test_novel()
    results['stem'] = await test_stem()
    results['business'] = await test_business()

    # Summary
    print("\n" + "="*70)
    print("       TEST SUMMARY")
    print("="*70)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, passed_test in results.items():
        status = "PASS" if passed_test else "FAIL"
        print(f"   {test_name:<15}: {status}")

    print(f"\n   TOTAL: {passed}/{total} tests passed")

    if passed == total:
        print("\n   ALL TESTS PASSED!")
    else:
        print(f"\n   {total - passed} test(s) failed")

    return results


if __name__ == "__main__":
    asyncio.run(run_all_tests())
