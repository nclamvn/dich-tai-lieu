"""
Quick Start: Cost-Effective Translation
AI Publisher Pro

Đây là implementation đơn giản nhất để giảm chi phí 10-30x.
Chỉ cần copy và chạy!
"""

import asyncio
import os
from pathlib import Path
from typing import List, Optional

# =========================================
# Quick Config
# =========================================

# Chọn model rẻ nhất
CHEAP_MODEL = "deepseek-chat"  # $0.27/$1.10 per 1M tokens
# hoặc
# CHEAP_MODEL = "gemini-1.5-flash"  # $0.075/$0.30 per 1M tokens

# API Keys
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Parallel processing
MAX_CONCURRENT = 10


# =========================================
# Simple OCR Wrapper
# =========================================

def extract_text_with_paddle(image_path: str) -> str:
    """Extract text using PaddleOCR - FREE"""
    try:
        from paddleocr import PaddleOCR
        
        ocr = PaddleOCR(use_angle_cls=True, lang='ch', show_log=False)
        result = ocr.ocr(image_path, cls=True)
        
        if not result or not result[0]:
            return ""
        
        lines = [line[1][0] for line in result[0]]
        return "\n".join(lines)
    
    except ImportError:
        print("Install PaddleOCR: pip install paddleocr paddlepaddle")
        return ""


def extract_text_with_easyocr(image_path: str) -> str:
    """Extract text using EasyOCR - FREE"""
    try:
        import easyocr
        
        reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)
        result = reader.readtext(image_path)
        
        lines = [r[1] for r in result]
        return "\n".join(lines)
    
    except ImportError:
        print("Install EasyOCR: pip install easyocr")
        return ""


# =========================================
# Cheap Translation Functions
# =========================================

async def translate_with_deepseek(
    text: str,
    source_lang: str = "Chinese",
    target_lang: str = "Vietnamese"
) -> str:
    """
    Translate using DeepSeek - $0.27/$1.10 per 1M tokens
    That's ~30x cheaper than Claude Sonnet!
    """
    try:
        from openai import AsyncOpenAI
        
        client = AsyncOpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com"
        )
        
        response = await client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {
                    "role": "system",
                    "content": f"""You are an expert translator from {source_lang} to {target_lang}.
Translate the following text accurately, preserving formatting and meaning.
Output ONLY the translation, no explanations."""
                },
                {"role": "user", "content": text}
            ],
            temperature=0.3
        )
        
        return response.choices[0].message.content
    
    except Exception as e:
        print(f"DeepSeek error: {e}")
        return text


async def translate_with_gemini(
    text: str,
    source_lang: str = "Chinese",
    target_lang: str = "Vietnamese"
) -> str:
    """
    Translate using Gemini Flash - $0.075/$0.30 per 1M tokens
    That's ~100x cheaper than Claude Sonnet!
    """
    try:
        import google.generativeai as genai
        
        genai.configure(api_key=GOOGLE_API_KEY)
        
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""You are an expert translator from {source_lang} to {target_lang}.
Translate the following text accurately, preserving formatting and meaning.
Output ONLY the translation, no explanations.

Text to translate:
{text}"""
        
        response = await model.generate_content_async(prompt)
        return response.text
    
    except Exception as e:
        print(f"Gemini error: {e}")
        return text


# =========================================
# Main Pipeline
# =========================================

async def translate_page(
    image_path: str,
    source_lang: str = "Chinese",
    target_lang: str = "Vietnamese",
    use_model: str = "deepseek"
) -> str:
    """Translate a single page: OCR + Cheap Model"""
    
    # Step 1: Extract text with OCR (FREE)
    text = extract_text_with_paddle(image_path)
    
    if not text.strip():
        return ""
    
    # Step 2: Translate with cheap model
    if use_model == "deepseek":
        translated = await translate_with_deepseek(text, source_lang, target_lang)
    else:
        translated = await translate_with_gemini(text, source_lang, target_lang)
    
    return translated


async def translate_document_cheap(
    image_paths: List[str],
    source_lang: str = "Chinese",
    target_lang: str = "Vietnamese",
    use_model: str = "deepseek",
    max_concurrent: int = MAX_CONCURRENT
) -> List[str]:
    """
    Translate entire document cheaply.
    
    For 223 pages:
    - Before: $15, 3 hours
    - After: $0.50-1.00, 20-30 minutes
    """
    import time
    
    start = time.time()
    total = len(image_paths)
    translations = []
    
    print(f"🚀 Starting translation of {total} pages")
    print(f"   Model: {use_model}")
    print(f"   Concurrent: {max_concurrent}")
    
    # Process in batches
    for i in range(0, total, max_concurrent):
        batch = image_paths[i:i + max_concurrent]
        
        # Translate batch in parallel
        tasks = [
            translate_page(path, source_lang, target_lang, use_model)
            for path in batch
        ]
        
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for j, result in enumerate(batch_results):
            if isinstance(result, Exception):
                print(f"   ❌ Error on page {i+j+1}: {result}")
                translations.append("")
            else:
                translations.append(result)
        
        # Progress
        done = min(i + max_concurrent, total)
        elapsed = time.time() - start
        rate = done / elapsed * 60 if elapsed > 0 else 0
        
        print(f"   ✅ {done}/{total} pages ({done/total*100:.1f}%) - {rate:.1f} pages/min")
    
    elapsed = time.time() - start
    
    print(f"\n🎉 Complete!")
    print(f"   Time: {elapsed/60:.1f} minutes")
    print(f"   Rate: {total/elapsed*60:.1f} pages/minute")
    
    # Estimate cost
    total_chars = sum(len(t) for t in translations)
    tokens_est = total_chars / 4  # Rough estimate
    
    if use_model == "deepseek":
        cost = tokens_est * 2 / 1_000_000 * 0.7  # avg cost
    else:
        cost = tokens_est * 2 / 1_000_000 * 0.2  # Gemini cheaper
    
    print(f"   Estimated cost: ${cost:.2f}")
    
    return translations


# =========================================
# Helper: Convert PDF to Images
# =========================================

def pdf_to_images(pdf_path: str, output_dir: str = None) -> List[str]:
    """Convert PDF to images for OCR"""
    try:
        from pdf2image import convert_from_path
    except ImportError:
        print("Install: pip install pdf2image")
        print("Also need: apt install poppler-utils")
        return []
    
    if output_dir is None:
        output_dir = Path(pdf_path).stem + "_images"
    
    Path(output_dir).mkdir(exist_ok=True)
    
    print(f"📄 Converting PDF to images...")
    images = convert_from_path(pdf_path, dpi=150)
    
    paths = []
    for i, img in enumerate(images):
        path = f"{output_dir}/page_{i+1:04d}.png"
        img.save(path)
        paths.append(path)
    
    print(f"   Created {len(paths)} images")
    return paths


# =========================================
# Usage Example
# =========================================

async def main():
    """Example usage"""
    
    # 1. Convert PDF to images
    pdf_path = "your_document.pdf"
    image_paths = pdf_to_images(pdf_path)
    
    # 2. Translate cheaply
    translations = await translate_document_cheap(
        image_paths,
        source_lang="Chinese",
        target_lang="Vietnamese",
        use_model="deepseek",  # or "gemini"
        max_concurrent=10
    )
    
    # 3. Save results
    output_path = "translations.txt"
    with open(output_path, "w", encoding="utf-8") as f:
        for i, text in enumerate(translations):
            f.write(f"=== Page {i+1} ===\n")
            f.write(text)
            f.write("\n\n")
    
    print(f"✅ Saved to {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
