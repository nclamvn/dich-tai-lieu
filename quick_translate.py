#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick Translation Script - Sử dụng TranslatorEngine thật
"""

import sys
import os
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from core.translator import TranslatorEngine
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def translate_file():
    """Dịch file với TranslatorEngine thật"""

    print("="*60)
    print("🌐 AI TRANSLATOR - Quick Translation")
    print("="*60)

    # Get input file
    input_file = input("\n📁 Nhập đường dẫn file cần dịch: ").strip()

    if not os.path.exists(input_file):
        print(f"❌ Lỗi: Không tìm thấy file '{input_file}'")
        return

    # Get output file
    default_output = input_file.replace('.', '_vi.')
    output_file = input(f"📄 Tên file output [{default_output}]: ").strip() or default_output

    # Get API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        api_key = input("🔑 Nhập OpenAI API Key: ").strip()

    if not api_key or len(api_key) < 10:
        print("❌ Lỗi: API key không hợp lệ")
        return

    # Choose model
    print("\n🤖 Chọn model:")
    print("  1. GPT-4o Mini (Nhanh, rẻ - $0.010/1K words)")
    print("  2. GPT-4.1 Mini (Cân bằng - $0.015/1K words)")
    print("  3. Claude 3.5 Sonnet (Chất lượng cao - $0.003/1K words)")

    model_choice = input("Chọn (1/2/3) [1]: ").strip() or "1"

    model_map = {
        "1": ("openai", "gpt-4o-mini"),
        "2": ("openai", "gpt-4-mini"),
        "3": ("anthropic", "claude-3-5-sonnet-20241022")
    }

    provider, model = model_map.get(model_choice, ("openai", "gpt-4o-mini"))

    # Choose languages
    source_lang = input("\n🌍 Ngôn ngữ nguồn [auto]: ").strip() or "auto"
    target_lang = input("🇻🇳 Ngôn ngữ đích [vi]: ").strip() or "vi"

    # Choose domain
    print("\n📚 Domain (lĩnh vực):")
    print("  1. General (Chung - mặc định)")
    print("  2. STEM (Khoa học, Công nghệ, Toán, Lập trình - bảo toàn công thức & code)")
    print("  3. Finance (Tài chính)")
    print("  4. Medical (Y học)")
    print("  5. Literature (Văn học)")

    domain_choice = input("Chọn (1/2/3/4/5) [1]: ").strip() or "1"

    domain_map = {
        "1": None,
        "2": "stem",
        "3": "finance",
        "4": "medical",
        "5": "literature"
    }

    domain = domain_map.get(domain_choice, None)

    # Phase 3: STEM-specific options with smart detection
    input_type = "native_pdf"
    output_mode = "docx_reflow"
    enable_ocr = False
    ocr_mode = "auto"
    mathpix_app_id = None
    mathpix_app_key = None
    enable_quality_check = False
    enable_chemical_formulas = False

    if domain == "stem":
        print("\n🔬 STEM Mode - Advanced Options:")

        # Smart detection for PDF files
        if input_file.lower().endswith('.pdf') and os.path.exists(input_file):
            try:
                from core.ocr import SmartDetector
                print("\n🔍 Analyzing PDF...")
                detector = SmartDetector()
                detection = detector.detect_pdf_type(input_file)

                print(f"   📊 Type: {detection.pdf_type.value.upper()}")
                print(f"   📈 Confidence: {detection.confidence:.1%}")
                print(f"   💡 Recommendation: {detection.recommendation.value}")

                if detection.ocr_needed:
                    print(f"   ⚠️  OCR recommended for best results")
                else:
                    print(f"   ✅ Native PDF - no OCR needed")

            except ImportError:
                print("\n⚠️  Smart detection unavailable (install OCR dependencies)")
            except Exception as e:
                print(f"\n⚠️  Detection failed: {str(e)}")

        # Input type selection
        print("\n  📄 Input Type:")
        print("    1. Native PDF (text-based, can copy text)")
        print("    2. Scanned PDF (image-based, needs OCR)")
        print("    3. Handwritten PDF (needs OCR with handwriting mode)")

        input_choice = input("  Choose input type (1/2/3) [1]: ").strip() or "1"
        input_type_map = {
            "1": "native_pdf",
            "2": "scanned_pdf",
            "3": "handwritten_pdf"
        }
        input_type = input_type_map.get(input_choice, "native_pdf")
        enable_ocr = (input_type in ["scanned_pdf", "handwritten_pdf"])

        # OCR mode selection (if OCR enabled)
        if enable_ocr:
            print("\n  🤖 OCR Mode:")
            print("    1. Auto (smart detection chooses best mode)")
            print("    2. PaddleOCR only (local, free, fast)")
            print("    3. Hybrid (PaddleOCR + MathPix for formulas) - RECOMMENDED for STEM")
            print("    4. MathPix only (formula-specialized, requires API key)")

            ocr_choice = input("  Choose OCR mode (1/2/3/4) [3]: ").strip() or "3"
            ocr_mode_map = {
                "1": "auto",
                "2": "paddle",
                "3": "hybrid",
                "4": "mathpix"
            }
            ocr_mode = ocr_mode_map.get(ocr_choice, "hybrid")

            # MathPix API key prompt (if hybrid or mathpix mode)
            if ocr_mode in ["hybrid", "mathpix"]:
                print("\n  🔑 MathPix API credentials (optional, press Enter to use env vars):")
                mathpix_app_id = input("     App ID: ").strip() or None
                if mathpix_app_id:
                    mathpix_app_key = input("     App Key: ").strip() or None
                else:
                    print("     Using MATHPIX_APP_ID and MATHPIX_APP_KEY from environment")

                if not mathpix_app_id and not os.getenv('MATHPIX_APP_ID'):
                    print("     ⚠️  No MathPix credentials found - will use PaddleOCR only")

        # Output mode selection
        print("\n  📤 Output Mode:")
        print("    1. Preserve Layout PDF (keeps original layout, multi-column)")
        print("    2. Reflow DOCX (clean, editable, single-column)")

        output_choice = input("  Choose output mode (1/2) [2]: ").strip() or "2"
        output_mode_map = {
            "1": "pdf_preserve",
            "2": "docx_reflow"
        }
        output_mode = output_mode_map.get(output_choice, "docx_reflow")

        # Chemical formula detection
        print("\n  ⚗️ Enable chemical formula detection (H2O, CH3CH2OH, etc.)? (y/n) [y]: ", end="")
        chem_choice = input().strip().lower() or "y"
        enable_chemical_formulas = (chem_choice == "y")

        # Quality checker
        print("  ✅ Enable quality checker (validates translation)? (y/n) [y]: ", end="")
        quality_choice = input().strip().lower() or "y"
        enable_quality_check = (quality_choice == "y")

    print("\n" + "="*60)
    print("🚀 Bắt đầu dịch...")
    print("="*60)

    try:
        print(f"\n📊 Provider: {provider.upper()}")
        print(f"🤖 Model: {model}")
        print(f"📥 Input: {input_file}")
        print(f"📤 Output: {output_file}")
        print(f"🌐 {source_lang.upper()} → {target_lang.upper()}")
        if domain:
            print(f"📚 Domain: {domain.upper()}")
            if domain == "stem":
                print(f"   🔬 STEM mode: Công thức & code sẽ được bảo toàn")
                if enable_ocr:
                    print(f"   👁️  OCR: Enabled ({input_type})")
                if enable_chemical_formulas:
                    print(f"   ⚗️  Chemical formulas: Enabled")
                if enable_quality_check:
                    print(f"   ✅ Quality checker: Enabled")
                print(f"   📄 Output mode: {output_mode}")
        print()

        # Set environment variables for the BatchProcessor pipeline
        os.environ['OPENAI_API_KEY'] = api_key
        os.environ['PROVIDER'] = provider
        os.environ['MODEL'] = model

        # Translate (Phase 3 parameters passed as metadata)
        metadata = {
            "input_type": input_type,
            "output_mode": output_mode,
            "enable_ocr": enable_ocr,
            "enable_quality_check": enable_quality_check,
            "enable_chemical_formulas": enable_chemical_formulas
        }

        # Add OCR mode and MathPix credentials if applicable
        if enable_ocr:
            metadata["ocr_mode"] = ocr_mode
            if mathpix_app_id:
                metadata["mathpix_app_id"] = mathpix_app_id
            if mathpix_app_key:
                metadata["mathpix_app_key"] = mathpix_app_key

        # PHASE 1.7.1 FIX: Use exact same pipeline as Web UI via BatchProcessor
        import asyncio
        from core.job_queue import JobQueue, JobPriority
        from core.batch_processor import BatchProcessor

        # Auto-enable academic mode for STEM (Phase 1.7.1 requirement)
        if domain == "stem":
            metadata["academic_mode"] = True
            print("   📚 Academic mode: Auto-enabled for STEM")

        # Create job queue
        queue = JobQueue()

        # Determine output format
        if output_file.endswith('.docx'):
            output_format = 'docx'
        elif output_file.endswith('.pdf'):
            output_format = 'pdf'
        else:
            output_format = 'txt'

        # Create job with metadata
        job = queue.create_job(
            job_name=f"Quick Translate: {os.path.basename(input_file)}",
            input_file=input_file,
            output_file=output_file,
            priority=JobPriority.NORMAL,
            domain=domain,
            source_lang=source_lang,
            target_lang=target_lang,
            output_format=output_format,
            concurrency=5,
            metadata=metadata
        )

        print(f"\n📝 Job created: {job.job_id}")
        print(f"📋 Using EXACT Web UI pipeline (BatchProcessor)")

        # Process job using BatchProcessor (exact same pipeline as Web UI)
        processor = BatchProcessor(queue)

        # Process the job synchronously
        async def process():
            await processor._process_job_impl(job)

        asyncio.run(process())

        # Reload job to get final status
        final_job = queue.get_job(job.job_id)

        # Print results
        print("\n" + "="*60)
        if final_job.status.value == 'completed':
            print("✅ HOÀN THÀNH!")
        else:
            print(f"⚠️  Status: {final_job.status.value}")
        print("="*60)
        print(f"\n📄 File đã lưu: {output_file}")

        # Print statistics from job metadata
        stats = final_job.metadata or {}
        print(f"\n📊 Thống kê:")
        print(f"  - Tổng chunks: {stats.get('total_chunks', 'N/A')}")
        print(f"  - Thành công: {stats.get('successful_chunks', 'N/A')}")
        print(f"  - Thất bại: {stats.get('failed_chunks', 0)}")
        print(f"  - Chất lượng TB: {stats.get('avg_quality_score', 0):.1%}")
        print(f"  - Chi phí: ${stats.get('estimated_cost_usd', 0):.4f}")

        # STEM-specific stats
        if domain == "stem" and stats.get('stem_preservation'):
            pres = stats['stem_preservation']
            print(f"\n🔬 STEM Preservation:")
            print(f"  - Formulas: {pres.get('formulas_preserved', 0)}/{pres.get('formulas_detected', 0)}")
            print(f"  - Code blocks: {pres.get('code_preserved', 0)}/{pres.get('code_detected', 0)}")
            print(f"  - Preservation rate: {pres.get('preservation_rate', 0):.1%}")

        # Academic polishing stats (if applied)
        if stats.get('academic_polish_stats'):
            polish = stats['academic_polish_stats']
            print(f"\n📚 Academic Polish:")
            print(f"  - Terms normalized: {polish.get('terms_normalized', 0)}")
            print(f"  - Phrases improved: {polish.get('phrases_improved', 0)}")

        print()

    except KeyboardInterrupt:
        print("\n\n⚠️  Dịch bị hủy bởi người dùng")
    except Exception as e:
        print(f"\n❌ Lỗi: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    try:
        translate_file()
    except KeyboardInterrupt:
        print("\n\n👋 Đã thoát")
