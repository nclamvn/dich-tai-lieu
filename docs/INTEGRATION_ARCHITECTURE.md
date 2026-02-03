# NHÀ XUẤT BẢN SỐ HOÀN CHỈNH
## Kiến Trúc Microservices Tích Hợp

**Ngày:** 2026-01-18
**Version:** 1.0.0
**Trạng thái:** Thiết kế

---

## 1. TỔNG QUAN

### 1.1 Mục Tiêu
Tích hợp 2 hệ thống thành **NHÀ XUẤT BẢN SỐ** hoàn chỉnh:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     NHÀ XUẤT BẢN SỐ HOÀN CHỈNH                         │
│                                                                         │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │
│  │   SÁNG TÁC   │───▶│   DỊCH THUẬT │───▶│   XUẤT BẢN   │              │
│  │  Companion   │    │  AI Publisher │    │   Unified    │              │
│  │   Writer     │    │     Pro       │    │   Export     │              │
│  └──────────────┘    └──────────────┘    └──────────────┘              │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Hai Hệ Thống

| Component | Companion Writer | AI Publisher Pro |
|-----------|------------------|------------------|
| **Vai trò** | Sáng tác & Chắp bút | Dịch thuật & Xuất bản |
| **Tech** | Next.js (TypeScript) | FastAPI (Python) |
| **Port** | 3002 | 3000 |
| **Database** | PostgreSQL + Prisma | File-based jobs |
| **AI** | OpenAI/Anthropic/Gemini | OpenAI/Anthropic/DeepSeek |

---

## 2. KIẾN TRÚC MICROSERVICES

### 2.1 Tổng Quan Kiến Trúc

```
                              ┌─────────────────┐
                              │   API Gateway   │
                              │   (Nginx/Kong)  │
                              │    Port: 80     │
                              └────────┬────────┘
                                       │
        ┌──────────────────────────────┼──────────────────────────────┐
        │                              │                              │
        ▼                              ▼                              ▼
┌───────────────┐            ┌─────────────────┐            ┌───────────────┐
│  Companion    │            │   Integration   │            │ AI Publisher  │
│   Writer      │◀──────────▶│     Bridge      │◀──────────▶│     Pro       │
│  Port: 3002   │            │   Port: 3003    │            │  Port: 3000   │
│  (Next.js)    │            │   (FastAPI)     │            │  (FastAPI)    │
└───────────────┘            └─────────────────┘            └───────────────┘
        │                              │                              │
        ▼                              ▼                              ▼
┌───────────────┐            ┌─────────────────┐            ┌───────────────┐
│  PostgreSQL   │            │     Redis       │            │  Job Queue    │
│   Database    │            │   (Pub/Sub)     │            │  (File-based) │
└───────────────┘            └─────────────────┘            └───────────────┘
```

### 2.2 Integration Bridge (Cầu Nối)

Service mới kết nối 2 hệ thống:

```python
# integration_bridge/main.py
from fastapi import FastAPI

app = FastAPI(title="NXB Integration Bridge")

# Endpoints
POST /api/bridge/projects/{cw_project_id}/translate    # CW → APP translate
POST /api/bridge/documents/{app_doc_id}/export         # APP → CW export
GET  /api/bridge/jobs/{job_id}/status                  # Unified job status
POST /api/bridge/webhooks/translation-complete          # Callback from APP
POST /api/bridge/webhooks/export-complete               # Callback from CW
```

---

## 3. QUY TRÌNH XUẤT BẢN HOÀN CHỈNH

### 3.1 Flow: Sáng Tác → Dịch → Xuất Bản

```
┌────────────────────────────────────────────────────────────────────────┐
│                          QUY TRÌNH NXB SỐ                              │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  [1] SÁNG TÁC (Companion Writer)                                       │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  User viết truyện tiếng Việt                                    │   │
│  │  • Phỏng vấn với AI → Thu thập ý tưởng                          │   │
│  │  • Memory Vault → Lưu trữ ý tưởng                               │   │
│  │  • AI Companion → Hỗ trợ viết nháp                              │   │
│  │  • Draft System → Version control                                │   │
│  │  → Output: Draft (Vietnamese)                                    │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                   │
│                                    ▼                                   │
│  [2] DỊCH THUẬT (AI Publisher Pro)                                     │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Draft được gửi đến AI Publisher Pro                            │   │
│  │  • Smart Extraction → Phân tích nội dung                        │   │
│  │  • Parallel Translation → Dịch song song (5 chunks)             │   │
│  │  • Multi-provider fallback (OpenAI → Claude → DeepSeek)         │   │
│  │  → Output: Translated Document (English)                        │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                   │
│                                    ▼                                   │
│  [3] BIÊN TẬP (Both Systems)                                           │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Biên tập viên review bản dịch                                  │   │
│  │  • CW Editor Agent → Review & suggest                           │   │
│  │  • Human review → Final approval                                │   │
│  │  → Output: Final Manuscript                                     │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                   │
│                                    ▼                                   │
│  [4] XUẤT BẢN (Unified Export)                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Xuất ra các định dạng chuyên nghiệp                            │   │
│  │  • PDF (APP Template Engine) → Professional layout              │   │
│  │  • DOCX (APP DOCX Engine) → Word document                       │   │
│  │  • EPUB (CW Export) → E-book format                             │   │
│  │  → Output: Published Files                                      │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                   │
│                                    ▼                                   │
│  [5] PHÂN PHỐI (Companion Writer)                                      │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Chia sẻ & Phân phối                                            │   │
│  │  • Public Links → Share with readers                            │   │
│  │  • Reader Feedback → Collect comments                           │   │
│  │  • Analytics → Track engagement                                 │   │
│  │  → Output: Published & Distributed                              │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Data Flow

```
CW_Draft                    Integration Bridge                 APP_Document
   │                               │                                │
   │  POST /translate              │                                │
   │──────────────────────────────▶│                                │
   │                               │  POST /api/v2/translate        │
   │                               │───────────────────────────────▶│
   │                               │                                │
   │                               │  WebSocket: progress updates   │
   │◀──────────────────────────────│◀───────────────────────────────│
   │                               │                                │
   │                               │  POST /webhook/complete        │
   │◀──────────────────────────────│◀───────────────────────────────│
   │                               │                                │
   │  Update Draft with translation│                                │
   │◀──────────────────────────────│                                │
```

---

## 4. API SPECIFICATIONS

### 4.1 Integration Bridge APIs

#### 4.1.1 Translate Draft
```http
POST /api/bridge/translate
Content-Type: application/json

{
  "cw_project_id": "clxyz123",
  "cw_draft_id": "draft_456",
  "source_lang": "vi",
  "target_lang": "en",
  "options": {
    "provider": "auto",
    "preserve_formatting": true,
    "glossary": {
      "nhà xuất bản": "publisher",
      "bản thảo": "manuscript"
    }
  }
}

Response:
{
  "job_id": "bridge_job_789",
  "status": "queued",
  "estimated_time": "5-10 min",
  "tracking_url": "/api/bridge/jobs/bridge_job_789"
}
```

#### 4.1.2 Export Document
```http
POST /api/bridge/export
Content-Type: application/json

{
  "source": "app",  // or "cw"
  "document_id": "doc_123",
  "formats": ["pdf", "docx", "epub"],
  "template": "professional",
  "options": {
    "include_toc": true,
    "font_family": "Times New Roman",
    "page_size": "a4"
  }
}

Response:
{
  "job_id": "export_job_456",
  "status": "processing",
  "files": []
}
```

#### 4.1.3 Job Status
```http
GET /api/bridge/jobs/{job_id}

Response:
{
  "job_id": "bridge_job_789",
  "type": "translation",
  "status": "completed",  // queued | processing | completed | failed
  "progress": 100,
  "result": {
    "original_word_count": 5000,
    "translated_word_count": 5200,
    "provider_used": "gpt-4o",
    "cost": 0.15,
    "download_urls": {
      "docx": "/downloads/translated.docx",
      "pdf": "/downloads/translated.pdf"
    }
  }
}
```

### 4.2 Webhook Events

```python
# CW → Bridge: Translation request
{
  "event": "translation.requested",
  "project_id": "clxyz123",
  "draft_id": "draft_456",
  "content_hash": "sha256:abc123"
}

# APP → Bridge: Translation complete
{
  "event": "translation.completed",
  "app_job_id": "app_job_789",
  "bridge_job_id": "bridge_job_789",
  "output_files": ["translated.docx", "translated.pdf"]
}

# Bridge → CW: Update project
{
  "event": "draft.translated",
  "project_id": "clxyz123",
  "draft_id": "draft_456",
  "translated_content": "...",
  "metadata": {...}
}
```

---

## 5. DATABASE SCHEMA INTEGRATION

### 5.1 New Integration Tables (PostgreSQL)

```sql
-- In Companion Writer's Prisma schema

model TranslationJob {
  id              String   @id @default(cuid())
  projectId       String
  project         Project  @relation(fields: [projectId], references: [id])
  draftId         String
  draft           Draft    @relation(fields: [draftId], references: [id])

  appJobId        String?  // AI Publisher Pro job ID
  bridgeJobId     String   @unique

  sourceLang      String   @default("vi")
  targetLang      String   @default("en")

  status          TranslationStatus @default(PENDING)
  progress        Int      @default(0)

  originalContent String?  @db.Text
  translatedContent String? @db.Text

  providerUsed    String?
  tokenCount      Int?
  cost            Float?

  errorMessage    String?

  createdAt       DateTime @default(now())
  updatedAt       DateTime @updatedAt
  completedAt     DateTime?
}

model ExportJob {
  id              String   @id @default(cuid())
  projectId       String
  project         Project  @relation(fields: [projectId], references: [id])

  bridgeJobId     String   @unique

  formats         String[] // ["pdf", "docx", "epub"]
  template        String   @default("professional")

  status          ExportStatus @default(PENDING)
  progress        Int      @default(0)

  outputFiles     Json?    // {"pdf": "url", "docx": "url"}

  createdAt       DateTime @default(now())
  completedAt     DateTime?
}

enum TranslationStatus {
  PENDING
  QUEUED
  EXTRACTING
  TRANSLATING
  FORMATTING
  COMPLETED
  FAILED
}

enum ExportStatus {
  PENDING
  PROCESSING
  COMPLETED
  FAILED
}
```

### 5.2 Reference Table

```sql
-- Cross-system reference table
CREATE TABLE system_references (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  cw_project_id   VARCHAR(50),
  cw_draft_id     VARCHAR(50),
  app_document_id VARCHAR(50),
  app_job_id      VARCHAR(50),

  sync_status     VARCHAR(20) DEFAULT 'active',
  last_synced_at  TIMESTAMP,

  created_at      TIMESTAMP DEFAULT NOW(),
  updated_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_cw_project ON system_references(cw_project_id);
CREATE INDEX idx_app_document ON system_references(app_document_id);
```

---

## 6. IMPLEMENTATION PLAN

### Phase 1: Foundation (Week 1)
- [ ] Create Integration Bridge service
- [ ] Set up shared Redis for Pub/Sub
- [ ] Implement basic health checks
- [ ] Docker Compose configuration

### Phase 2: Translation Flow (Week 2)
- [ ] CW → Bridge → APP translation pipeline
- [ ] WebSocket progress tracking
- [ ] Webhook callbacks
- [ ] Error handling & retry logic

### Phase 3: Export Enhancement (Week 3)
- [ ] Unified export API
- [ ] Share APP's professional templates with CW
- [ ] Support all formats (PDF, DOCX, EPUB)
- [ ] Quality comparison testing

### Phase 4: UI Integration (Week 4)
- [ ] CW: Add "Translate" button in Draft view
- [ ] CW: Add translation progress indicator
- [ ] CW: Language switcher in Reading view
- [ ] APP: Add "Import from CW" feature

### Phase 5: Production (Week 5)
- [ ] Performance optimization
- [ ] Rate limiting & cost controls
- [ ] Monitoring & logging
- [ ] Documentation & handover

---

## 7. DOCKER COMPOSE

```yaml
# docker-compose.yml
version: '3.8'

services:
  # API Gateway
  gateway:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - companion-writer
      - ai-publisher
      - integration-bridge

  # Companion Writer (Next.js)
  companion-writer:
    build: ./maianhRioBook/companion-writer
    ports:
      - "3002:3002"
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/companion_writer
      - REDIS_URL=redis://redis:6379
      - INTEGRATION_BRIDGE_URL=http://integration-bridge:3003
    depends_on:
      - postgres
      - redis

  # AI Publisher Pro (FastAPI)
  ai-publisher:
    build: ./ai-publisher-pro-public
    ports:
      - "3000:3000"
    environment:
      - REDIS_URL=redis://redis:6379
      - INTEGRATION_BRIDGE_URL=http://integration-bridge:3003
    depends_on:
      - redis

  # Integration Bridge (FastAPI)
  integration-bridge:
    build: ./integration-bridge
    ports:
      - "3003:3003"
    environment:
      - CW_API_URL=http://companion-writer:3002
      - APP_API_URL=http://ai-publisher:3000
      - REDIS_URL=redis://redis:6379
      - DATABASE_URL=postgresql://user:pass@postgres:5432/integration
    depends_on:
      - postgres
      - redis

  # PostgreSQL
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
      POSTGRES_DB: companion_writer
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  # Redis (Pub/Sub & Caching)
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

---

## 8. QUICK START

### 8.1 Development
```bash
# Terminal 1: AI Publisher Pro
cd /Users/mac/ai-publisher-pro-public
uvicorn api.main:app --host 0.0.0.0 --port 3000 --reload

# Terminal 2: Companion Writer
cd /Users/mac/maianhRioBook/companion-writer/companion-writer
npm run dev

# Terminal 3: Integration Bridge (sau khi implement)
cd /Users/mac/ai-publisher-pro-public/integration_bridge
uvicorn main:app --host 0.0.0.0 --port 3003 --reload
```

### 8.2 Production (Docker)
```bash
cd /Users/mac/ai-publisher-pro-public
docker-compose up -d
```

---

## 9. NEXT STEPS

1. **Tạo Integration Bridge service** - `integration_bridge/` folder
2. **Implement translation endpoint** - CW draft → APP translation
3. **Add webhook handlers** - Status updates between systems
4. **UI integration** - "Translate" button in CW
5. **Testing** - End-to-end workflow test

---

## 10. UI INTEGRATION (Implemented)

### Files đã tạo/sửa trong Companion Writer:

| File | Mô tả |
|------|-------|
| `src/components/workspace/TranslateModal.tsx` | **NEW** - Modal dịch thuật (426 lines) |
| `src/components/workspace/WorkspaceLayout.tsx` | **MODIFIED** - Thêm Translate button |
| `.env.example` | **MODIFIED** - Thêm NEXT_PUBLIC_BRIDGE_API_URL |

### TranslateModal Features:

- Auto-detect ngôn ngữ nguồn (Việt/Anh)
- Hỗ trợ 11 ngôn ngữ
- Progress bar real-time
- Poll Integration Bridge API cho status
- Copy/Apply kết quả dịch

### Vị trí nút Translate:

```
Header Toolbar:
[Voice🎙] [Ghostwriter👻] [Translate🌐] [Stats📊] [Share📤] [Export⬇] | [Draft] [Views]
```

---

**Document này mô tả kiến trúc tích hợp. Integration Bridge và UI đã được implement.**
