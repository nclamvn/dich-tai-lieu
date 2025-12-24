#!/usr/bin/env python3
"""
Book Translation CLI - Specialized tool for translating books (novels, fiction, non-fiction)

This script provides a streamlined interface for translating book PDFs with optimal settings:
- Automatic book layout detection and formatting
- Chapter/section structure preservation
- Professional ebook styling (Georgia font, proper spacing, scene breaks)
- Paragraph intelligent merging
- Book-specific polish (quotes, dashes, widow/orphan control)
- Optional translation quality enhancement

Usage:
    python translate_book.py input.pdf
    python translate_book.py input.pdf --output my_book.docx
    python translate_book.py input.pdf --quality light
    python translate_book.py input.pdf --chapters-only 1-3

Examples:
    # Basic usage (will create translated_input.docx)
    python translate_book.py "My Novel.pdf"

    # With custom output and quality enhancement
    python translate_book.py book.pdf --output novel_vi.docx --quality light

    # Test first 50 pages only
    python translate_book.py largebook.pdf --pages 1-50 --output sample.docx
"""

import argparse
import sys
import os
import requests
import time
from pathlib import Path
from datetime import datetime


def get_default_output(input_path: str) -> str:
    """Generate default output filename."""
    input_file = Path(input_path)
    return f"translated_{input_file.stem}.docx"


def submit_book_translation(
    input_path: str,
    output_path: str = None,
    quality_mode: str = "off",
    source_lang: str = "en",
    target_lang: str = "vi",
    pages: str = None,
    api_url: str = "http://localhost:8000"
) -> dict:
    """
    Submit a book translation job to the API.

    Args:
        input_path: Path to input PDF
        output_path: Path for output DOCX (auto-generated if None)
        quality_mode: Translation quality mode ("off", "light", "aggressive")
        source_lang: Source language code
        target_lang: Target language code
        pages: Page range (e.g., "1-50" for testing)
        api_url: API server URL

    Returns:
        Job details dict
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    if output_path is None:
        output_path = get_default_output(input_path)

    print(f"\n{'='*70}")
    print(f"📚 BOOK TRANSLATION - Starting")
    print(f"{'='*70}")
    print(f"Input:  {input_path}")
    print(f"Output: {output_path}")
    print(f"Quality mode: {quality_mode}")
    if pages:
        print(f"Pages: {pages} (testing sample)")
    print(f"{'='*70}\n")

    # Prepare request
    with open(input_path, 'rb') as f:
        files = {'file': (os.path.basename(input_path), f, 'application/pdf')}

        data = {
            'source_lang': source_lang,
            'target_lang': target_lang,
            'domain': 'book',  # Critical: mark as book domain
            'layout_mode': 'book',  # Critical: use book layout
            'output_path': output_path,
        }

        # Add quality mode to metadata
        if quality_mode != "off":
            data['translation_quality_mode'] = quality_mode

        # Add page range if testing
        if pages:
            data['page_range'] = pages

        print("📤 Uploading file to server...")
        response = requests.post(f"{api_url}/api/translate", files=files, data=data)
        response.raise_for_status()

    job = response.json()
    print(f"✅ Job submitted: {job['job_id']}")
    return job


def monitor_job(job_id: str, api_url: str = "http://localhost:8000") -> dict:
    """
    Monitor job progress until completion.

    Args:
        job_id: Job ID to monitor
        api_url: API server URL

    Returns:
        Final job details
    """
    print(f"\n🔍 Monitoring job {job_id}...")
    print(f"{'='*70}")

    url = f"{api_url}/api/jobs/{job_id}"
    start_time = time.time()

    while True:
        try:
            resp = requests.get(url, timeout=5)
            resp.raise_for_status()
            data = resp.json()

            status = data['status']
            progress = data.get('progress', 0) * 100
            elapsed = int(time.time() - start_time)

            # Print progress
            timestamp = time.strftime('%H:%M:%S')
            bar_length = 40
            filled = int(bar_length * data.get('progress', 0))
            bar = '█' * filled + '░' * (bar_length - filled)

            print(f"\r[{timestamp}] [{bar}] {progress:5.1f}% | Status: {status:12s} | Time: {elapsed}s",
                  end='', flush=True)

            # Check completion
            if status == 'completed':
                print(f"\n{'='*70}")
                print(f"✅ Translation completed successfully!")
                print(f"{'='*70}")
                print(f"📄 Output file: {data.get('output_path', 'N/A')}")
                print(f"⏱️  Total time: {elapsed}s ({elapsed//60}m {elapsed%60}s)")
                print(f"💰 Cost: ${data.get('total_cost_usd', 0):.3f}")
                print(f"📊 Quality score: {data.get('quality_score', 0):.1%}")

                # Show book-specific stats if available
                metadata = data.get('metadata', {})
                if 'paragraph_merge_stats' in metadata:
                    stats = metadata['paragraph_merge_stats']
                    print(f"\n📖 Book Processing Stats:")
                    print(f"   • Paragraphs merged: {stats.get('paragraphs_merged', 0)}")
                    print(f"   • Fragments merged: {stats.get('fragments_merged', 0)}")

                if 'book_polish_stats' in metadata:
                    stats = metadata['book_polish_stats']
                    print(f"   • Polish fixes applied: {stats.get('total_fixes', 0)}")

                if 'translation_quality_stats' in metadata:
                    stats = metadata['translation_quality_stats']
                    print(f"   • Quality issues fixed: {stats.get('issues_fixed', 0)}")

                print(f"{'='*70}\n")
                return data

            elif status == 'failed':
                print(f"\n{'='*70}")
                print(f"❌ Translation failed!")
                print(f"{'='*70}")
                print(f"Error: {data.get('error_message', 'Unknown error')}")
                print(f"{'='*70}\n")
                return data

            time.sleep(3)

        except Exception as e:
            print(f"\n⚠️  Error monitoring job: {e}")
            time.sleep(5)


def main():
    parser = argparse.ArgumentParser(
        description="Translate books (novels, fiction, non-fiction) with professional ebook formatting",
        epilog="""
Examples:
  %(prog)s "My Novel.pdf"
  %(prog)s book.pdf --output novel_vi.docx --quality light
  %(prog)s largebook.pdf --pages 1-50 --output sample.docx
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        'input',
        help='Input PDF file (book to translate)'
    )

    parser.add_argument(
        '-o', '--output',
        help='Output DOCX file (default: translated_<input>.docx)'
    )

    parser.add_argument(
        '-q', '--quality',
        choices=['off', 'light', 'aggressive'],
        default='off',
        help='Translation quality enhancement mode (default: off)'
    )

    parser.add_argument(
        '--pages',
        help='Page range for testing (e.g., "1-50" to translate first 50 pages only)'
    )

    parser.add_argument(
        '--source-lang',
        default='en',
        help='Source language code (default: en)'
    )

    parser.add_argument(
        '--target-lang',
        default='vi',
        help='Target language code (default: vi)'
    )

    parser.add_argument(
        '--api-url',
        default='http://localhost:8000',
        help='API server URL (default: http://localhost:8000)'
    )

    parser.add_argument(
        '--no-wait',
        action='store_true',
        help='Submit job and exit (do not wait for completion)'
    )

    args = parser.parse_args()

    try:
        # Submit job
        job = submit_book_translation(
            input_path=args.input,
            output_path=args.output,
            quality_mode=args.quality,
            source_lang=args.source_lang,
            target_lang=args.target_lang,
            pages=args.pages,
            api_url=args.api_url
        )

        if args.no_wait:
            print(f"\n✅ Job submitted: {job['job_id']}")
            print(f"Monitor at: {args.api_url}/api/jobs/{job['job_id']}")
            return 0

        # Monitor until completion
        result = monitor_job(job['job_id'], args.api_url)

        return 0 if result['status'] == 'completed' else 1

    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        return 1
    except requests.exceptions.ConnectionError:
        print(f"\n❌ Error: Cannot connect to API server at {args.api_url}", file=sys.stderr)
        print(f"Make sure the server is running.", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
