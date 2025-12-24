#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Simple PDF Translation Script - Uses API Server
Usage: python3 translate_pdf.py <input.pdf> [options]

Options:
  --domain DOMAIN         Translation domain: general, stem (default: general)
  --ocr-backend BACKEND   OCR backend: auto, paddle, hybrid, mathpix (default: auto)
  --mathpix-id ID        MathPix App ID (optional)
  --mathpix-key KEY      MathPix App Key (optional)
  --provider PROVIDER     AI provider: openai, anthropic (default: openai)
  --model MODEL          AI model name (default: gpt-4o-mini)

Examples:
  # Basic translation
  python3 translate_pdf.py document.pdf

  # STEM document with hybrid OCR
  python3 translate_pdf.py thesis.pdf --domain stem --ocr-backend hybrid

  # STEM with MathPix credentials
  python3 translate_pdf.py paper.pdf --domain stem --ocr-backend hybrid \\
      --mathpix-id your-app-id --mathpix-key your-app-key
"""

import sys
import os
import time
import requests
import argparse
from pathlib import Path
from core.document_classifier import classify_document

def translate_pdf(
    pdf_path: str,
    domain: str = 'general',
    ocr_backend: str = 'auto',
    mathpix_app_id: str = None,
    mathpix_app_key: str = None,
    provider: str = 'openai',
    model: str = 'gpt-4o-mini',
    layout_mode: str = 'simple',
    equation_rendering: str = 'latex_text',
    auto_detect: bool = True
):
    """Translate PDF file to Vietnamese using API server

    Args:
        pdf_path: Path to PDF file
        domain: Translation domain (general, stem)
        ocr_backend: OCR backend (auto, paddle, hybrid, mathpix)
        mathpix_app_id: MathPix App ID (optional)
        mathpix_app_key: MathPix App Key (optional)
        provider: AI provider (openai, anthropic)
        model: AI model name
        layout_mode: DOCX layout mode (simple, academic) - Phase 2.0
        equation_rendering: Equation rendering mode (latex_text, omml) - Phase 2.0.4
        auto_detect: Enable intelligent document type detection - Phase 2.1.1
    """

    # Validate input
    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        print(f"❌ File not found: {pdf_path}")
        return

    # Phase 2.1.1: Intelligent Document Detection
    if auto_detect:
        print("🔍 Analyzing document type...")
        classification = classify_document(pdf_path, check_content=True)

        doc_type = classification['document_type']
        confidence = classification['confidence']

        print(f"✓ Detected: {doc_type.upper()} document (confidence: {confidence:.0%})")

        if classification['reasons']:
            print(f"   Reasons: {', '.join(classification['reasons'])}")

        # Apply recommended settings only if parameters weren't explicitly set by user
        # (We'll handle this by checking if they differ from defaults)
        recommended = classification['recommended_settings']

        # Override defaults with recommended settings
        if domain == 'general':  # User didn't specify domain
            domain = recommended['domain']
        if layout_mode == 'simple':  # User didn't specify layout mode
            layout_mode = recommended['layout_mode']
        if equation_rendering == 'latex_text':  # User didn't specify equation rendering
            equation_rendering = recommended['equation_rendering']

        print(f"✓ Using optimized settings for {doc_type.upper()} document")
        print()

    # Show configuration
    print(f"📖 Translating PDF: {pdf_file.name}")
    print(f"   Domain: {domain}")
    if domain == 'stem':
        print(f"   OCR Backend: {ocr_backend}")
        if mathpix_app_id:
            print(f"   MathPix: Provided (App ID: {mathpix_app_id[:8]}...)")
        else:
            print(f"   MathPix: Using server default")
    print(f"   Provider: {provider}")
    print(f"   Model: {model}\n")

    # API settings
    api_base = "http://localhost:8000/api"

    # Check if server is running
    try:
        response = requests.get("http://localhost:8000/health", timeout=2)
        if response.status_code != 200:
            print("❌ API server is not running!")
            print("💡 Start it with: ./start_server.sh")
            return
    except requests.exceptions.RequestException:
        print("❌ Cannot connect to API server!")
        print("💡 Start it with: ./start_server.sh")
        return

    print("✓ API server is running\n")

    # Step 1: Upload file
    print("📤 Uploading file...")

    try:
        with open(pdf_file, 'rb') as f:
            files = {'file': (pdf_file.name, f, 'application/pdf')}
            response = requests.post(f"{api_base}/upload", files=files)

            if response.status_code != 200:
                print(f"❌ Error uploading file: {response.text}")
                return

            upload_result = response.json()
            server_path = upload_result['server_path']
            print(f"✓ File uploaded: {upload_result['filename']}")

    except Exception as e:
        print(f"❌ Error uploading: {e}")
        return

    # Step 2: Create translation job
    print("📝 Creating translation job...")

    try:
        job_data = {
            'job_name': f"Translate {pdf_file.name}",
            'input_file': server_path,
            'output_file': f"/tmp/output_{pdf_file.stem}.docx",
            'source_lang': 'en',
            'target_lang': 'vi',
            'output_format': 'docx',
            'domain': domain,
            'provider': provider,
            'model': model,
            'chunk_size': 3000,
            'concurrency': 5,
            'layout_mode': layout_mode,  # Phase 2.0.1: DOCX layout mode
            'equation_rendering_mode': equation_rendering  # Phase 2.0.4: Equation rendering
        }

        # Add OCR settings for STEM domain
        if domain == 'stem':
            job_data['ocr_mode'] = ocr_backend  # API expects 'ocr_mode'
            job_data['enable_ocr'] = True
            if mathpix_app_id:
                job_data['mathpix_app_id'] = mathpix_app_id
            if mathpix_app_key:
                job_data['mathpix_app_key'] = mathpix_app_key

        response = requests.post(f"{api_base}/jobs", json=job_data)

        if response.status_code != 201:
            print(f"❌ Error creating job: {response.text}")
            return

        job = response.json()
        job_id = job['job_id']
        print(f"✓ Job created: {job_id}\n")

    except Exception as e:
        print(f"❌ Error creating job: {e}")
        return

    # Poll for completion
    print("🌐 Translating...")
    last_progress = 0

    while True:
        try:
            response = requests.get(f"{api_base}/jobs/{job_id}")
            if response.status_code != 200:
                print(f"❌ Error checking job: {response.text}")
                return

            job_status = response.json()
            status = job_status['status']
            progress = int(job_status.get('progress', 0) * 100)

            # Show progress
            if progress != last_progress:
                print(f"   Progress: {progress}%", end='\r')
                last_progress = progress

            # Check if done
            if status == 'completed':
                print(f"\n✅ Translation completed!\n")
                break
            elif status == 'failed':
                error = job_status.get('error_message', 'Unknown error')
                print(f"\n❌ Translation failed: {error}")
                return
            elif status == 'cancelled':
                print(f"\n⚠️  Translation cancelled")
                return

            time.sleep(2)  # Check every 2 seconds

        except KeyboardInterrupt:
            print(f"\n\n⚠️  Cancelling job...")
            requests.post(f"{api_base}/jobs/{job_id}/cancel")
            return
        except Exception as e:
            print(f"\n❌ Error: {e}")
            return

    # Download results
    print("💾 Downloading results...")
    output_base = pdf_file.stem + "_Vietnamese"

    # Download DOCX
    try:
        response = requests.get(f"{api_base}/jobs/{job_id}/download/docx")
        if response.status_code == 200:
            docx_path = f"{output_base}.docx"
            with open(docx_path, 'wb') as f:
                f.write(response.content)
            print(f"✓ Saved: {docx_path}")
        else:
            print(f"⚠️  DOCX not available: {response.text}")
    except Exception as e:
        print(f"⚠️  Error downloading DOCX: {e}")

    # Download PDF
    try:
        response = requests.get(f"{api_base}/jobs/{job_id}/download/pdf")
        if response.status_code == 200:
            pdf_out_path = f"{output_base}.pdf"
            with open(pdf_out_path, 'wb') as f:
                f.write(response.content)
            print(f"✓ Saved: {pdf_out_path}")
        else:
            print(f"⚠️  PDF not available")
    except Exception as e:
        print(f"⚠️  Error downloading PDF: {e}")

    # Get final statistics
    print(f"\n📊 Summary:")
    print(f"   Job ID: {job_id}")
    if 'chunks_total' in job_status:
        print(f"   Total chunks: {job_status['chunks_total']}")
    if 'chunks_completed' in job_status:
        print(f"   Completed: {job_status['chunks_completed']}")
    if 'quality_score' in job_status and job_status['quality_score']:
        print(f"   Quality: {job_status['quality_score']:.1%}")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Translate PDF files using AI Translator API server',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic translation
  python3 translate_pdf.py document.pdf

  # STEM document with hybrid OCR (MathPix + PaddleOCR)
  python3 translate_pdf.py thesis.pdf --domain stem --ocr-backend hybrid

  # STEM with MathPix credentials
  python3 translate_pdf.py paper.pdf --domain stem --ocr-backend hybrid \\
      --mathpix-id your-app-id --mathpix-key your-app-key

  # Use Anthropic Claude
  python3 translate_pdf.py document.pdf --provider anthropic --model claude-3-5-sonnet-20241022

Note: API server must be running (./start_server.sh)
        """
    )

    parser.add_argument('pdf_file', help='Input PDF file to translate')
    parser.add_argument('--domain', choices=['general', 'stem'], default='general',
                        help='Translation domain (default: general)')
    parser.add_argument('--ocr-backend', choices=['auto', 'paddle', 'hybrid', 'mathpix'],
                        default='auto', help='OCR backend for scanned PDFs (default: auto)')
    parser.add_argument('--mathpix-id', help='MathPix App ID (optional)')
    parser.add_argument('--mathpix-key', help='MathPix App Key (optional)')
    parser.add_argument('--provider', choices=['openai', 'anthropic'], default='openai',
                        help='AI provider (default: openai)')
    parser.add_argument('--model', help='AI model name (default: auto-select based on provider)')
    parser.add_argument('--layout-mode', choices=['simple', 'academic'], default='simple',
                        help='DOCX layout mode: simple (clean reflow) or academic (semantic structure) - Phase 2.0 (default: simple)')
    parser.add_argument('--equation-rendering', choices=['latex_text', 'omml'], default='latex_text',
                        help='Equation rendering mode for academic layout: latex_text (plain LaTeX) or omml (Word native math, requires pandoc) - Phase 2.0.4 (default: latex_text)')
    parser.add_argument('--latex-source', metavar='PATH',
                        help='LaTeX source file (.tex, .zip, .tar.gz) for arXiv papers - Phase 2.1.0 (experimental)')
    parser.add_argument('--no-auto-detect', action='store_true',
                        help='Disable intelligent document type detection - Phase 2.1.1 (default: auto-detection enabled)')

    args = parser.parse_args()

    # Auto-select model if not specified
    if not args.model:
        args.model = 'gpt-4o-mini' if args.provider == 'openai' else 'claude-3-5-sonnet-20241022'

    translate_pdf(
        pdf_path=args.pdf_file,
        domain=args.domain,
        ocr_backend=args.ocr_backend,
        mathpix_app_id=args.mathpix_id,
        mathpix_app_key=args.mathpix_key,
        provider=args.provider,
        model=args.model,
        layout_mode=args.layout_mode,
        equation_rendering=args.equation_rendering,
        auto_detect=not args.no_auto_detect  # Phase 2.1.1: Intelligent detection
    )
