# 💰 Chi Phí Translation - Phân Tích & Tối Ưu

## 📊 So Sánh Chi Phí Cho 223 Trang

### Hiện Tại (Vision + Claude Sonnet)

```
Chi phí = Vision API + Translation API

Vision:
  - $0.05-0.10 per page × 223 pages = $11-22
  
Translation (Sonnet):
  - Input: ~223,000 tokens × $3/1M = $0.67
  - Output: ~223,000 tokens × $15/1M = $3.35
  
TỔNG: $15-26 💸💸💸
```

### Phương Án Tối Ưu

| Phương án | Chi phí | Thời gian | Chất lượng |
|-----------|---------|-----------|------------|
| **A: OCR + DeepSeek** | $0.30-0.50 | 15-20 phút | ⭐⭐⭐ |
| **B: OCR + Gemini Flash** | $0.15-0.25 | 10-15 phút | ⭐⭐⭐ |
| **C: OCR + Mixed** | $0.50-1.50 | 20-30 phút | ⭐⭐⭐⭐ |
| **D: OCR + Haiku** | $0.40-0.80 | 15-25 phút | ⭐⭐⭐⭐ |

---

## 🎯 Phương Án Đề Xuất: Smart Mixed Pipeline

### Strategy

```
┌─────────────────────────────────────────────────────────────────────┐
│                    SMART MIXED PIPELINE                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Step 1: OCR Text Extraction (FREE)                                 │
│  ├── PaddleOCR cho Chinese                                          │
│  ├── Không dùng Vision API                                          │
│  └── Confidence score để filter                                     │
│                                                                     │
│  Step 2: Content Analysis (FREE)                                    │
│  ├── Detect complexity: simple/medium/complex                       │
│  ├── Identify: formulas, tables, code                               │
│  └── Route to appropriate model                                     │
│                                                                     │
│  Step 3: Tiered Translation                                         │
│  ├── 80% Simple text   → DeepSeek/Gemini Flash  ($0.10/1M)         │
│  ├── 15% Medium text   → Haiku/GPT-4o-mini      ($0.50/1M)         │
│  └──  5% Complex text  → Sonnet (only when needed) ($3/1M)         │
│                                                                     │
│  Step 4: Parallel Processing                                        │
│  ├── 10 concurrent requests                                         │
│  └── ~15 pages/minute                                               │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Chi Phí Breakdown (223 trang)

```
OCR Extraction:
  - Cost: $0 (local processing)
  - Time: ~5 minutes

Translation (Mixed):
  - 178 pages (80%) → DeepSeek: ~$0.20
  - 34 pages (15%)  → Haiku: ~$0.15  
  - 11 pages (5%)   → Sonnet: ~$0.50
  
TỔNG: ~$0.85 (giảm 95% so với $15!)
Thời gian: ~25 phút (giảm 85% so với 3h!)
```

---

## 🛠️ Implementation Guide

### Step 1: Install OCR

```bash
# Option A: PaddleOCR (recommended for Chinese)
pip install paddleocr paddlepaddle

# Option B: EasyOCR (easier setup)
pip install easyocr

# Option C: Tesseract (free, widely available)
apt install tesseract-ocr tesseract-ocr-chi-sim
pip install pytesseract

# PDF to image conversion
pip install pdf2image
apt install poppler-utils
```

### Step 2: Add Cheap Providers

```bash
# DeepSeek - $0.27/$1.10 per 1M tokens
export DEEPSEEK_API_KEY=sk-...

# Gemini - $0.075/$0.30 per 1M tokens  
export GOOGLE_API_KEY=AIza...
```

### Step 3: Update Translation Logic

```python
from smart_tiered_pipeline import SmartTieredPipeline, PipelineConfig

# Configure for cost optimization
config = PipelineConfig(
    ocr_engine="paddle",
    ocr_languages=["ch", "en"],
    
    # Use cheapest models by default
    economy_model="deepseek-chat",      # $0.27/1M
    standard_model="gemini-1.5-flash",  # $0.075/1M
    premium_model="claude-3-5-haiku",   # $0.25/1M (not Sonnet!)
    
    # Aggressive cost optimization
    prefer_economy=True,
    max_concurrent=10,  # Faster
    
    # Alert if cost too high
    max_cost_usd=2.0
)

pipeline = SmartTieredPipeline(config, provider_manager)

# Process document
result = await pipeline.process_document(
    image_paths=page_images,
    source_lang="Chinese",
    target_lang="Vietnamese"
)

print(f"Cost: ${result['cost_estimate']:.2f}")
print(f"Time: {result['elapsed_minutes']:.1f} minutes")
```

---

## 📈 Cost Comparison Table

### Per 1M Tokens Pricing

| Model | Input | Output | Total (avg) |
|-------|-------|--------|-------------|
| **Gemini 1.5 Flash** | $0.075 | $0.30 | $0.19 |
| **DeepSeek V3** | $0.27 | $1.10 | $0.69 |
| **Haiku** | $0.25 | $1.25 | $0.75 |
| **GPT-4o-mini** | $0.15 | $0.60 | $0.38 |
| **Sonnet** | $3.00 | $15.00 | $9.00 |
| **GPT-4o** | $2.50 | $10.00 | $6.25 |

### Vision API Cost

| Provider | Per Image |
|----------|-----------|
| Claude Vision | ~$0.05-0.10 |
| GPT-4o Vision | ~$0.02-0.05 |
| Gemini Vision | ~$0.01-0.02 |

**Key Insight**: Vision ~50-100x đắt hơn text processing!

---

## ⚡ Quick Win Optimizations

### 1. Không dùng Vision cho text pages

```python
# TRƯỚC (đắt)
response = await claude.analyze_with_vision(page_image)

# SAU (rẻ)
text = ocr.extract(page_image)
response = await deepseek.translate(text)
```

**Tiết kiệm: $0.05-0.10 per page**

### 2. Dùng model rẻ nhất có thể

```python
# TRƯỚC
model = "claude-3-5-sonnet"  # $9/1M avg

# SAU  
model = "deepseek-chat"      # $0.69/1M avg
# hoặc
model = "gemini-1.5-flash"   # $0.19/1M avg
```

**Tiết kiệm: 10-50x**

### 3. Parallel processing

```python
# TRƯỚC: Sequential (3 hours)
for page in pages:
    result = await translate(page)

# SAU: Parallel (25 minutes)
results = await asyncio.gather(*[
    translate(page) for page in pages
], max_concurrent=10)
```

**Tiết kiệm: 6-10x thời gian**

### 4. Cache translations

```python
# Cache identical segments
cache_key = hash(text + source + target)
if cache_key in cache:
    return cache[cache_key]
```

**Tiết kiệm: Tùy nội dung (có thể 10-30%)**

---

## 🎯 Recommended Setup

### For Chinese → Vietnamese Translation

```yaml
# config.yaml
ocr:
  engine: paddle
  languages: [ch, en]
  
translation:
  primary_model: deepseek-chat     # 80% content
  fallback_model: gemini-1.5-flash # Alternative
  premium_model: claude-3-5-haiku  # Complex only
  
processing:
  max_concurrent: 10
  batch_size: 20
  
cost_control:
  max_per_page: 0.01  # Alert if > $0.01/page
  max_total: 2.00     # Alert if > $2 total
```

### Expected Results (223 pages)

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Time | 3 hours | 20-30 min | **6-10x** |
| Cost | $15 | $0.50-1.50 | **10-30x** |
| Quality | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Same |

---

## 🚨 Khi Nào Dùng Vision?

Chỉ dùng Vision API khi:

1. **OCR confidence < 60%** - Text không rõ, scan chất lượng kém
2. **Mathematical formulas** - Cần hiểu layout của công thức
3. **Complex diagrams** - Flowcharts, architecture diagrams
4. **Tables với borders phức tạp** - OCR không giữ được structure
5. **Handwritten content** - OCR không nhận được

```python
def should_use_vision(page_analysis):
    return (
        page_analysis.ocr_confidence < 0.6 or
        page_analysis.has_complex_formulas or
        page_analysis.has_diagrams
    )
```

**Mục tiêu: < 5% pages dùng Vision**
