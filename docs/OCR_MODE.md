# OCR Mode - Scanned Document Translation

Guide to using OCR (Optical Character Recognition) for translating scanned or handwritten documents.

## Overview

The translator supports three types of PDF inputs:

1. **Native PDF** - Text-based PDFs with selectable/copyable text
2. **Scanned PDF** - Image-based PDFs from scanners (printed documents)
3. **Handwritten PDF** - Image-based PDFs with handwritten content

For scanned and handwritten PDFs, OCR is required to extract text before translation.

## Quick Start

### Basic Usage

```bash
# Translate a scanned PDF with OCR
python translate_pdf.py scanned_document.pdf --ocr

# Translate handwritten notes
python translate_pdf.py handwritten_notes.pdf --ocr --ocr-mode handwriting

# Specify source language
python translate_pdf.py scanned_french.pdf --ocr --source-lang fr
```

### Python API

```python
from pathlib import Path
from core.ocr import DeepseekOcrClient, OcrPipeline

# Create OCR client
ocr_client = DeepseekOcrClient()

# Create OCR pipeline
pipeline = OcrPipeline(
    ocr_client=ocr_client,
    dpi=300,  # Image resolution (higher = better quality)
    language="auto"  # or "en", "fr", "zh", etc.
)

# Process scanned PDF
ocr_pages = pipeline.process_pdf(
    Path("scanned.pdf"),
    mode="document"  # or "handwriting"
)

# Get extracted text
for page in ocr_pages:
    print(f"Page {page.page_num + 1}: {page.text}")
    print(f"Confidence: {page.confidence:.1%}")

# Merge all pages to single text
full_text = pipeline.merge_pages_to_text(ocr_pages)

# Get statistics
stats = pipeline.get_statistics(ocr_pages)
print(f"Success rate: {stats['success_rate']:.1%}")
```

## Configuration

### Environment Variables

Set these environment variables to configure the OCR client:

```bash
# DeepSeek OCR API Configuration
export DEEPSEEK_OCR_ENDPOINT="https://api.deepseek.com/v1/ocr"
export DEEPSEEK_OCR_API_KEY="your-api-key-here"
export DEEPSEEK_OCR_TIMEOUT=30  # Request timeout in seconds
```

### Configuration File

Alternatively, configure via `config/settings.py`:

```python
OCR_CONFIG = {
    "endpoint": "https://api.deepseek.com/v1/ocr",
    "api_key": "your-api-key",
    "timeout": 30,
    "max_retries": 3
}
```

## OCR Modes

### Document Mode (Default)

Optimized for **printed** text from scanners:

- Books, papers, articles
- Official documents
- Receipts, invoices
- Printed forms

```bash
python translate_pdf.py scanned.pdf --ocr --ocr-mode document
```

### Handwriting Mode

Optimized for **handwritten** text:

- Handwritten notes
- Filled forms
- Signatures and annotations

```bash
python translate_pdf.py handwritten.pdf --ocr --ocr-mode handwriting
```

## Image Quality Settings

### DPI (Dots Per Inch)

Controls image resolution for OCR:

- **150 DPI**: Fast, lower quality (good for clean documents)
- **300 DPI**: Default, balanced quality and speed
- **600 DPI**: High quality (recommended for small text or poor scans)

```python
pipeline = OcrPipeline(ocr_client, dpi=600)
```

### Image Format

Choose between PNG and JPEG:

- **PNG**: Lossless, larger files (recommended)
- **JPEG**: Lossy compression, smaller files

```python
pipeline = OcrPipeline(ocr_client, image_format="PNG")
```

## Language Hints

Provide language hints to improve OCR accuracy:

```bash
# Auto-detect language
python translate_pdf.py scanned.pdf --ocr

# Specify source language
python translate_pdf.py scanned_french.pdf --ocr --source-lang fr
python translate_pdf.py scanned_chinese.pdf --ocr --source-lang zh
```

Supported languages:
- `en` - English
- `fr` - French
- `de` - German
- `es` - Spanish
- `it` - Italian
- `pt` - Portuguese
- `zh` - Chinese
- `ja` - Japanese
- `ko` - Korean
- `ar` - Arabic
- `auto` - Auto-detect (default)

## Error Handling

OCR pipeline includes automatic error recovery:

1. **Retry Logic**: Failed pages are retried up to 3 times
2. **Exponential Backoff**: Delays increase between retries
3. **Partial Results**: Continues processing if some pages fail
4. **Error Reporting**: Failed pages are tracked in results

```python
# Check for failed pages
stats = pipeline.get_statistics(ocr_pages)

if stats['failed_pages']:
    print(f"Failed pages: {stats['failed_pages']}")
    print(f"Success rate: {stats['success_rate']:.1%}")
```

## Performance Tips

### Optimize for Speed

```python
# Use lower DPI for clean documents
pipeline = OcrPipeline(ocr_client, dpi=150)

# Process page range instead of entire document
ocr_pages = pipeline.process_pdf(
    pdf_path,
    page_range=(0, 10)  # First 10 pages only
)
```

### Optimize for Quality

```python
# Use higher DPI for poor quality scans
pipeline = OcrPipeline(ocr_client, dpi=600)

# Use PNG for lossless quality
pipeline = OcrPipeline(ocr_client, image_format="PNG")
```

### Batch Processing

```python
from core.batch_processor import BatchProcessor

# Process multiple scanned PDFs
batch = BatchProcessor(
    source_lang="fr",
    target_lang="en",
    ocr_enabled=True,
    ocr_mode="document"
)

batch.add_file("scanned1.pdf")
batch.add_file("scanned2.pdf")
batch.add_file("scanned3.pdf")

batch.process_all()
```

## Output Formats

### Preserve Layout (PDF)

Maintains original document layout:

```bash
python translate_pdf.py scanned.pdf --ocr --output-mode preserve
```

Features:
- Same page size and dimensions
- Same text positioning
- Same fonts and formatting (where possible)

### Reflow (DOCX)

Creates structured, reflowed document:

```bash
python translate_pdf.py scanned.pdf --ocr --output-mode reflow
```

Features:
- Single-column layout
- Semantic formatting (titles, headings, paragraphs)
- Editable DOCX format
- Better for long documents

## Troubleshooting

### OCR Returns Empty Text

**Causes:**
- Image quality too low
- Text too small or blurry
- Incorrect OCR mode (document vs handwriting)

**Solutions:**
```python
# Increase DPI
pipeline = OcrPipeline(ocr_client, dpi=600)

# Try different OCR mode
pipeline.process_pdf(pdf_path, mode="handwriting")
```

### Low Confidence Scores

**Causes:**
- Poor scan quality
- Unusual fonts or layouts
- Mixed languages

**Solutions:**
- Rescan at higher resolution
- Use language hints
- Pre-process images (contrast, rotation)

### API Rate Limits

**Causes:**
- Too many requests to OCR API
- Exceeded quota

**Solutions:**
```python
# Increase retry delays
ocr_client = DeepseekOcrClient(max_retries=5)

# Process in smaller batches
pipeline.process_pdf(pdf_path, page_range=(0, 10))
```

### Connection Timeouts

**Causes:**
- Slow network
- Large images
- API server issues

**Solutions:**
```python
# Increase timeout
ocr_client = DeepseekOcrClient(timeout=60)

# Use lower DPI to reduce image size
pipeline = OcrPipeline(ocr_client, dpi=150)
```

## Advanced Features

### Custom OCR Client

Implement your own OCR client:

```python
from core.ocr.base import OcrClient

class CustomOcrClient(OcrClient):
    def extract(self, image_bytes, mode="document", language=None):
        # Your OCR implementation
        return extracted_text

    def extract_structured(self, image_bytes, mode="document", language=None):
        # Return structured data with blocks and confidence
        return {
            "text": extracted_text,
            "confidence": 0.95,
            "blocks": [...],
            "metadata": {...}
        }

# Use custom client
pipeline = OcrPipeline(CustomOcrClient())
```

### Multi-Page Processing

```python
# Process specific pages
ocr_pages = pipeline.process_pdf(
    pdf_path,
    page_range=(5, 15)  # Pages 6-15 (0-indexed)
)

# Process single image
ocr_page = pipeline.process_image(
    Path("scanned_page.png"),
    mode="document"
)
```

### Structured Output

Access detailed OCR results:

```python
for page in ocr_pages:
    print(f"Page {page.page_num + 1}:")
    print(f"  Text: {len(page.text)} chars")
    print(f"  Confidence: {page.confidence:.1%}")

    # Access text blocks
    for block in page.blocks:
        print(f"  Block: {block['text'][:50]}...")
        print(f"    BBox: {block['bbox']}")
        print(f"    Confidence: {block['confidence']:.1%}")
```

## Examples

### Example 1: Translate Scanned Research Paper

```bash
python translate_pdf.py research_paper_scanned.pdf \
    --ocr \
    --ocr-mode document \
    --source-lang en \
    --target-lang fr \
    --output-mode preserve \
    --dpi 300
```

### Example 2: Translate Handwritten Notes

```bash
python translate_pdf.py handwritten_notes.pdf \
    --ocr \
    --ocr-mode handwriting \
    --source-lang en \
    --target-lang es \
    --output-mode reflow \
    --dpi 600
```

### Example 3: Batch Process Scanned Invoices

```python
from pathlib import Path
from core.batch_processor import BatchProcessor

# Setup batch processor with OCR
batch = BatchProcessor(
    source_lang="en",
    target_lang="fr",
    ocr_enabled=True,
    ocr_mode="document",
    dpi=300
)

# Add all scanned invoices
invoice_dir = Path("scanned_invoices")
for pdf_file in invoice_dir.glob("*.pdf"):
    batch.add_file(pdf_file)

# Process all
results = batch.process_all()

# Review results
for result in results:
    print(f"{result.filename}: {result.status}")
    if result.ocr_confidence:
        print(f"  OCR confidence: {result.ocr_confidence:.1%}")
```

## Cost Estimation

OCR API calls have costs. Estimate before processing:

```python
import fitz  # PyMuPDF

# Count pages
doc = fitz.open("scanned.pdf")
page_count = doc.page_count
doc.close()

# Estimate cost (example: $0.01 per page)
estimated_cost = page_count * 0.01
print(f"Estimated cost: ${estimated_cost:.2f}")
```

## Best Practices

1. **Test on Sample Pages**: Process 1-2 pages first to verify quality
2. **Choose Right DPI**: Balance quality and speed (300 DPI is usually good)
3. **Use Language Hints**: Improves accuracy significantly
4. **Check Confidence Scores**: Review pages with low confidence manually
5. **Handle Errors Gracefully**: Some pages may fail - handle partial results
6. **Monitor API Usage**: Track API calls to avoid quota issues
7. **Cache Results**: Save OCR results to avoid re-processing

## Limitations

- **No OCR for Native PDFs**: OCR is only needed for scanned/handwritten documents
- **Quality Dependent**: OCR accuracy depends on scan quality
- **API Dependency**: Requires active OCR API service
- **Cost**: OCR API calls may incur costs
- **Processing Time**: OCR is slower than native text extraction

## See Also

- [Translation Pipeline](TRANSLATION_PIPELINE.md) - Main translation workflow
- [STEM Translation](STEM_TRANSLATION.md) - Handling formulas and code
- [Batch Processing](BATCH_PROCESSING.md) - Processing multiple files
- [Performance Tuning](PERFORMANCE.md) - Optimization strategies

---

**Last Updated**: Phase 3 Complete (v3.0.0)
**Status**: Production Ready
