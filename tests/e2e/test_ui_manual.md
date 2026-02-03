# Manual UI Test Checklist

## Pre-conditions
- [ ] Server running: `uvicorn api.main:app --port 3000`
- [ ] Browser open: http://localhost:3000/ui

---

## TC-UI-01: Basic File Upload
**Steps:**
1. Click dropzone hoặc drag PDF vào
2. Observe file name hiển thị
3. Click "Bắt đầu dịch"

**Expected:**
- [ ] File name hiển thị đúng
- [ ] File size hiển thị
- [ ] Button "Bắt đầu" enabled

---

## TC-UI-02: Cover Image Upload
**Steps:**
1. Click "Tùy chọn nâng cao"
2. Scroll đến "Ảnh bìa (Tùy chọn)"
3. Click hoặc drag ảnh PNG/JPG vào
4. Observe preview

**Expected:**
- [ ] Preview thumbnail hiển thị
- [ ] Dimensions hiển thị (e.g., 1200 x 1800px)
- [ ] File size hiển thị (e.g., 2.3MB)
- [ ] Remove button (❌) hoạt động

---

## TC-UI-03: Cover Image Validation
**Steps:**
1. Upload file > 5MB
2. Upload file không phải image (e.g., .txt)

**Expected:**
- [ ] Error message cho file > 5MB
- [ ] Error message cho wrong format
- [ ] File không được accept

---

## TC-UI-04: Image Extraction Toggle
**Steps:**
1. Click "Tùy chọn nâng cao"
2. Toggle "Trích xuất ảnh từ PDF" ON/OFF

**Expected:**
- [ ] Toggle state lưu đúng
- [ ] Visual feedback khi toggle

---

## TC-UI-05: Full Publishing Flow
**Steps:**
1. Upload PDF có images
2. Upload cover image
3. Bật "Trích xuất ảnh"
4. Chọn ngôn ngữ đích
5. Click "Bắt đầu dịch"
6. Wait for completion
7. Download output

**Expected:**
- [ ] Progress indicators hoạt động
- [ ] WebSocket updates hiển thị
- [ ] Download link xuất hiện
- [ ] Output file downloadable

---

## TC-UI-06: Options Panel Toggle
**Steps:**
1. Click "Tùy chọn nâng cao"
2. Observe panel mở rộng
3. Click lại để đóng

**Expected:**
- [ ] Panel slides smoothly
- [ ] Icon rotates (chevron)
- [ ] State persists during session

---

## TC-UI-07: Language Selection
**Steps:**
1. Click dropdown ngôn ngữ nguồn
2. Select "Chinese"
3. Click dropdown ngôn ngữ đích
4. Select "Vietnamese"

**Expected:**
- [ ] Dropdowns hiển thị đầy đủ options
- [ ] Selection highlights correctly
- [ ] Values persist

---

## TC-UI-08: Error States
**Steps:**
1. Upload invalid file (e.g., .exe)
2. Try to start without file
3. Disconnect network and try to upload

**Expected:**
- [ ] Appropriate error messages
- [ ] UI remains functional
- [ ] Clear recovery path

---

## Test Results Summary

| Test ID | Status | Notes |
|---------|--------|-------|
| TC-UI-01 | ⬜ | |
| TC-UI-02 | ⬜ | |
| TC-UI-03 | ⬜ | |
| TC-UI-04 | ⬜ | |
| TC-UI-05 | ⬜ | |
| TC-UI-06 | ⬜ | |
| TC-UI-07 | ⬜ | |
| TC-UI-08 | ⬜ | |

**Legend:** ✅ Pass | ❌ Fail | ⬜ Not Tested

**Tested By:** ________________
**Date:** ________________
**Browser/Version:** ________________
