#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script for layout-preserving PDF translation
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.layout_preserving_translator import LayoutPreservingTranslator
from core.stem.stem_translator import STEMTranslator
from core.translator import TranslatorEngine


async def translate_text_wrapper(text: str) -> str:
    """
    Wrapper function to translate text using STEM translator.

    This integrates with our existing translation pipeline.
    """
    # Initialize translator (simplified for testing)
    try:
        # Use OpenAI translator
        from core.config import get_config
        config = get_config()

        base_translator = TranslatorEngine(
            provider="openai",
            api_key=config.get("openai_api_key"),
            model="gpt-4o-mini"
        )

        stem_translator = STEMTranslator(base_translator)

        # Translate
        result = await stem_translator.translate_document(
            text=text,
            source_lang="en",
            target_lang="vi"
        )

        return result.translated_text

    except Exception as e:
        print(f"Translation error: {e}")
        return text  # Fallback to original


async def main():
    """Main test function"""

    if len(sys.argv) < 2:
        print("Usage: python3 translate_pdf_preserve_layout.py <input.pdf> [output.pdf]")
        sys.exit(1)

    input_pdf = sys.argv[1]
    output_pdf = sys.argv[2] if len(sys.argv) > 2 else input_pdf.replace(".pdf", "_translated_layout.pdf")

    print(f"📖 Layout-Preserving PDF Translation")
    print(f"   Input:  {input_pdf}")
    print(f"   Output: {output_pdf}")
    print()

    # Initialize translator
    translator = LayoutPreservingTranslator(translator_func=translate_text_wrapper)

    # Run translation
    print("⚙️  Extracting layout...")
    stats = await translator.translate_pdf(input_pdf, output_pdf)

    print()
    print("✅ Translation completed!")
    print(f"   📊 Statistics:")
    print(f"      - Pages: {stats['pages']}")
    print(f"      - Text blocks: {stats['total_blocks']}")
    print(f"      - Translated: {stats['translated_blocks']}")
    print(f"      - Layout: {stats['layout_preservation']}")
    print()
    print(f"✓ Saved: {output_pdf}")


if __name__ == "__main__":
    asyncio.run(main())
