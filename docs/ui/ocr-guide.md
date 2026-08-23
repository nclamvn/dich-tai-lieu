> **📜 TÀI LIỆU LỊCH SỬ — không phản ánh hiện trạng.** Snapshot tại thời điểm
> viết; kiến trúc, cổng, cờ cấu hình và đường dẫn trong này có thể đã đổi.
> Hiện trạng đúng: `PROJECT_XRAY.md` (bản đồ hệ thống) + `CLAUDE.md` (quy ước
> làm việc) + `docs/PRODUCTION_CHECKLIST.md` (điều kiện production).

# 🔍 OCR Quickstart Guide - Vietnamese Edition

## Tổng quan

Dashboard **AI Translator Pro** (phiên bản Việt Nam) hiện đã tích hợp **Deepseek OCR** để nhận dạng:
- ✍️ Chữ viết tay (handwriting)
- 📄 Tài liệu scan (scanned documents)
- 🌍 Đa ngôn ngữ (Việt, Anh, Trung, Nhật, Hàn)

---

## 🚀 Bước 1: Mở Dashboard

```bash
# Mở dashboard tiếng Việt
open ~/translator_project/ui/dashboard_premium_vn.html
```

Hoặc double-click vào file `dashboard_premium_vn.html`

---

## 🔑 Bước 2: Cấu hình API Keys

### Option A: Dùng Dashboard (Đơn giản)

1. Chọn tab **"OCR Viết tay/Scan"**
2. Nhập **Khóa API** của Deepseek
3. Chọn **Mô hình AI**: Deepseek Vision

### Option B: Dùng Backend API (Production)

Thêm vào file `.env`:

```bash
# API Keys
DEEPSEEK_API_KEY=sk-your-deepseek-key-here
OPENAI_API_KEY=sk-your-openai-key-here  # For translation
```

Khởi động API server:

```bash
cd ~/translator_project
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

API docs: http://localhost:8000/docs

---

## 📸 Bước 3: Test OCR với Demo Images

Dashboard đã có 3 sample images sẵn trong `ui/demo_files/`:

### 1. **sample_handwriting.jpg** - Chữ viết tay
```
Nội dung:
Xin chào! Đây là chữ viết tay.
Tôi đang học tiếng Anh.
I want to translate this text.
Cảm ơn bạn!
```

**Test:**
1. Click vào box **"Tải ảnh Viết tay hoặc Scan"**
2. Chọn `sample_handwriting.jpg`
3. Xem preview
4. Click **"Nhận dạng & Dịch"**
5. Chờ OCR processing (2-5 giây)
6. Xem kết quả văn bản + bản dịch

### 2. **sample_document_scan.jpg** - Biên bản họp
```
Nội dung:
BIÊN BẢN HỌP
Ngày: 12/11/2024
Địa điểm: Phòng họp A
...
```

**Test:**
- Upload → OCR → Translate to English
- Verify accuracy của OCR Vietnamese

### 3. **sample_mixed_language.png** - Multi-language
```
Nội dung:
AI Translator Pro
English, Tiếng Việt, 中文, 日本語, 한국어
```

**Test:**
- Upload → Auto-detect languages
- Check multi-script recognition

---

## 🧪 Bước 4: Test API Endpoints

### Endpoint 1: `/api/ocr/recognize` - Basic OCR

```bash
# Encode ảnh thành base64
IMAGE_B64=$(base64 -i ~/translator_project/ui/demo_files/sample_handwriting.jpg)

# Call API
curl -X POST http://localhost:8000/api/ocr/recognize \
  -H "Content-Type: application/json" \
  -d "{
    \"image_base64\": \"$IMAGE_B64\",
    \"language\": \"vi\",
    \"mode\": \"handwriting\"
  }"
```

**Expected Response:**
```json
{
  "text": "Xin chào! Đây là chữ viết tay...",
  "confidence": 0.92,
  "language": "vi",
  "processing_time": 2.3,
  "regions": [...]
}
```

### Endpoint 2: `/api/ocr/handwriting` - Handwriting-specific

```bash
curl -X POST http://localhost:8000/api/ocr/handwriting \
  -H "Content-Type: application/json" \
  -d "{
    \"image_base64\": \"$IMAGE_B64\",
    \"language\": \"vi\"
  }"
```

### Endpoint 3: `/api/ocr/translate` - OCR + Translation

```bash
curl -X POST http://localhost:8000/api/ocr/translate \
  -H "Content-Type: application/json" \
  -d "{
    \"image_base64\": \"$IMAGE_B64\",
    \"target_lang\": \"en\",
    \"source_lang\": \"auto\"
  }"
```

**Expected Response:**
```json
{
  "ocr": {
    "text": "Xin chào! Đây là chữ viết tay...",
    "confidence": 0.92,
    "language": "vi",
    "processing_time": 2.3
  },
  "translation": {
    "text": "Hello! This is handwriting...",
    "source_lang": "vi",
    "target_lang": "en"
  }
}
```

### Endpoint 4: `/api/ocr/upload` - File Upload

```bash
curl -X POST http://localhost:8000/api/ocr/upload \
  -F "file=@~/translator_project/ui/demo_files/sample_handwriting.jpg"
```

Returns base64 encoded image.

---

## 🎨 Bước 5: UI Features Tour

### Tab Navigation
```
┌─────────────────────────────────────────┐
│  [Dịch Văn bản]  [OCR Viết tay/Scan]  │
└─────────────────────────────────────────┘
```

**Tab 1: Dịch Văn bản**
- Upload: PDF, DOCX, TXT, SRT
- Translation only (existing feature)

**Tab 2: OCR Viết tay/Scan**
- Upload: JPG, PNG, HEIC
- OCR + Translation pipeline

### OCR Zone Features

```
┌────────────────────────────────────────┐
│    🖼️  Tải ảnh Viết tay hoặc Scan    │
│                                        │
│  JPG · PNG · HEIC · Hỗ trợ chữ viết tay│
│                                        │
│  [Drag & Drop hoặc Click để Upload]   │
└────────────────────────────────────────┘
```

**Upload methods:**
- Click vào box
- Drag & Drop từ Finder
- API upload endpoint

**Preview:**
- Ảnh hiển thị trước khi OCR
- Thông tin: filename, size, dimensions
- Option: Tiền xử lý ảnh (coming soon)

---

## 📊 Bước 6: Theo dõi Progress

### Progress Stages

```
0-30%:   OCR Processing     [████░░░░░░░░]
30-60%:  Text Extraction    [████████░░░░]
60-100%: Translation        [████████████]
```

### Status Indicators

```
⏸️  Chờ           - Waiting for upload
✅ Sẵn sàng       - File loaded, ready to process
⚡ Đang xử lý     - OCR/Translation in progress
✅ Hoàn thành     - Completed successfully
```

---

## 💡 Best Practices

### 1. Ảnh chất lượng cao
✅ **Good:**
- Resolution: > 1000px width
- Format: JPG, PNG (not compressed)
- Clear text, good contrast
- Straight orientation (not tilted)

❌ **Avoid:**
- Blurry images
- Low resolution (< 500px)
- Heavy compression
- Multiple pages in one image

### 2. Preprocessing
```python
# Tự động tiền xử lý (built-in)
DeepseekOCR.preprocess_image(
    "input.jpg",
    enhance=True,      # Tăng độ tương phản
    deskew=True        # Chỉnh góc nghiêng
)
```

### 3. Language Selection
- **"auto"**: Tự động phát hiện (recommended)
- **"vi"**: Force Vietnamese (nếu chắc chắn)
- **"en"**: English documents
- **"zh"**: Chinese characters

### 4. Mode Selection
- **"handwriting"**: Chữ viết tay
- **"accurate"**: Tài liệu in (chậm hơn, chính xác hơn)
- **"fast"**: Scanning nhanh (ít chính xác)

---

## 🐛 Troubleshooting

### Issue 1: OCR không hoạt động

**Checklist:**
```bash
# 1. Check API key
echo $DEEPSEEK_API_KEY

# 2. Verify httpx installed
pip3 show httpx

# 3. Test connectivity
curl https://api.deepseek.com/v1/health

# 4. Check logs
tail -f /tmp/translator_api.log
```

### Issue 2: Low confidence score (< 0.5)

**Fix:**
- Preprocess image (tăng độ tương phản)
- Use higher resolution image
- Select correct language
- Try "accurate" mode instead of "fast"

### Issue 3: Wrong language detected

**Fix:**
- Force language: `language="vi"` thay vì `"auto"`
- Check if image contains mixed languages
- Verify Vietnamese characters render correctly

### Issue 4: Slow processing (> 10s)

**Optimize:**
- Compress image (< 2MB recommended)
- Use "fast" mode for quick scanning
- Batch processing: `recognize_batch()` for multiple images

---

## 📈 Performance Metrics

### OCR Speed
```
Fast mode:        1-2s per image
Accurate mode:    2-5s per image
Handwriting mode: 3-6s per image

Translation:      +1-3s (depends on length)
Total pipeline:   4-9s (OCR + Translation)
```

### Cost Estimation
```
Deepseek OCR:
- $0.002 / image (< 5MB)
- $0.005 / image (5-20MB)

Translation (OpenAI):
- $0.015 / 1K words (GPT-4.1 Mini)
- $0.010 / 1K words (GPT-4o Mini)

Example:
- 10 images OCR: $0.02
- 5,000 words translate: $0.075
- Total: ~$0.10
```

---

## 🔒 Security Notes

### API Keys
```javascript
// Dashboard: sessionStorage (cleared on tab close)
sessionStorage.setItem('deepseek_key', key);

// Backend: Environment variables (recommended)
export DEEPSEEK_API_KEY=sk-xxx
```

### Image Handling
- Images uploaded to temp files (auto-deleted)
- No server-side storage
- Direct API passthrough
- HTTPS only in production

### CORS
```python
# api/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # Restrict in production
    allow_methods=["POST"],
    allow_headers=["*"]
)
```

---

## 📚 API Documentation

### Full API Docs
```bash
# Start server
cd ~/translator_project
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000

# Open docs
open http://localhost:8000/docs
```

### Interactive Testing
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Test all endpoints in browser
- See request/response schemas

---

## 🎯 Next Steps

### Immediate
- ✅ Test với demo images
- ✅ Verify API endpoints
- ✅ Try handwriting recognition
- ✅ Test multi-language

### Short-term
- [ ] Add more demo images (real handwriting)
- [ ] Implement image preprocessing UI
- [ ] Add OCR quality indicators
- [ ] Batch upload multiple images

### Long-term
- [ ] Custom OCR model training
- [ ] Offline OCR (TensorFlow.js)
- [ ] Mobile app integration
- [ ] OCR history/cache

---

## 💬 Support

### Documentation
- Architecture: `ARCHITECTURE_VN.md`
- Main guide: `QUICKSTART.md`
- This guide: `OCR_QUICKSTART.md`

### Issues
- GitHub: Create issue with screenshots
- Email: support@aitranslatorpro.vn
- Include: API logs, image samples, error messages

---

## ✨ Success Checklist

- [ ] Dashboard mở được (Vietnamese UI)
- [ ] Tab "OCR Viết tay/Scan" hiển thị
- [ ] Upload demo image thành công
- [ ] Xem preview ảnh
- [ ] OCR nhận dạng được text
- [ ] Translation hoạt động
- [ ] Download kết quả (DOCX/PDF)
- [ ] API endpoints test OK
- [ ] Lucide icons hiển thị đẹp

---

**Chúc mừng!** Bạn đã tích hợp thành công Deepseek OCR vào AI Translator Pro! 🎉

---

© 2024 AI Translator Pro · Vietnamese Enterprise Edition
