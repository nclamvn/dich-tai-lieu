# 🔗 Test Links - AI Translator Pro

Server đang chạy tại: **http://localhost:8000**

---

## 📊 Health & Monitoring Endpoints

### 1. Basic Health Check
```
http://localhost:8000/health
```
**Mô tả:** Health check cơ bản
**Method:** GET
**Response:** Status, version, timestamp

---

### 2. Detailed Health Check ⭐ MỚI
```
http://localhost:8000/api/health/detailed
```
**Mô tả:** Kiểm tra chi tiết tất cả components
**Method:** GET
**Response:**
- System resources (CPU, memory, disk)
- Database connectivity
- Storage availability
- API provider configuration

---

### 3. Cost Tracking ⭐ MỚI
```
http://localhost:8000/api/monitoring/costs
http://localhost:8000/api/monitoring/costs?time_period_hours=24
http://localhost:8000/api/monitoring/costs?time_period_hours=168
```
**Mô tả:** Theo dõi chi phí API
**Method:** GET
**Parameters:**
- `time_period_hours` (optional): Time window (default: 24h)

**Response:**
- Total tokens used
- Total cost USD
- Cost by provider
- Cost by model
- Average cost per job
- Jobs processed

---

### 4. Error Statistics ⭐ MỚI
```
http://localhost:8000/api/monitoring/errors
http://localhost:8000/api/monitoring/errors?time_period_hours=24
```
**Mô tả:** Thống kê lỗi hệ thống
**Method:** GET
**Parameters:**
- `time_period_hours` (optional): Time window (default: 24h)

**Response:**
- Total unique errors
- Total occurrences
- Unresolved count
- By severity breakdown
- By category breakdown

---

### 5. Recent Errors ⭐ MỚI
```
http://localhost:8000/api/monitoring/errors/recent
http://localhost:8000/api/monitoring/errors/recent?limit=10
http://localhost:8000/api/monitoring/errors/recent?severity=high
http://localhost:8000/api/monitoring/errors/recent?severity=critical&limit=5
```
**Mô tả:** Danh sách lỗi gần đây
**Method:** GET
**Parameters:**
- `limit` (optional): Max records (default: 50)
- `severity` (optional): Filter by severity (low, medium, high, critical)

**Response:** Array of error records with:
- error_type
- error_message
- severity
- category
- occurrence_count
- last_seen timestamp

---

## 🎯 Main Application Endpoints

### 6. Dashboard UI
```
http://localhost:8000/
http://localhost:8000/ui
```
**Mô tả:** Web dashboard interface
**Method:** GET
**Response:** HTML page

---

### 7. API Documentation (Swagger)
```
http://localhost:8000/docs
```
**Mô tả:** Interactive API documentation
**Method:** GET
**Response:** Swagger UI with all endpoints

---

### 8. System Information
```
http://localhost:8000/api/system/info
```
**Mô tả:** System information
**Method:** GET
**Response:** Version, status, uptime

---

## 📋 Job Management Endpoints

### 9. List Jobs
```
http://localhost:8000/api/jobs
http://localhost:8000/api/jobs?status=pending
http://localhost:8000/api/jobs?status=completed
```
**Mô tả:** Danh sách jobs
**Method:** GET
**Parameters:**
- `status` (optional): Filter by status

---

### 10. Queue Statistics
```
http://localhost:8000/api/queue/stats
```
**Mô tả:** Thống kê queue
**Method:** GET
**Response:** Total, pending, processing, completed

---

## 🧪 Testing with cURL

### Health Check
```bash
curl http://localhost:8000/health
```

### Detailed Health (formatted)
```bash
curl http://localhost:8000/api/health/detailed | python -m json.tool
```

### Cost Tracking (last 24h)
```bash
curl http://localhost:8000/api/monitoring/costs | python -m json.tool
```

### Cost Tracking (last 7 days)
```bash
curl "http://localhost:8000/api/monitoring/costs?time_period_hours=168" | python -m json.tool
```

### Error Statistics
```bash
curl http://localhost:8000/api/monitoring/errors | python -m json.tool
```

### Recent Errors (High severity only)
```bash
curl "http://localhost:8000/api/monitoring/errors/recent?severity=high&limit=10" | python -m json.tool
```

### Queue Stats
```bash
curl http://localhost:8000/api/queue/stats | python -m json.tool
```

---

## 🧪 Testing with Browser

**Mở các link sau trong browser:**

1. **Dashboard:** http://localhost:8000
2. **API Docs:** http://localhost:8000/docs
3. **Health Check:** http://localhost:8000/api/health/detailed
4. **Cost Dashboard:** http://localhost:8000/api/monitoring/costs
5. **Error Dashboard:** http://localhost:8000/api/monitoring/errors
6. **Recent Errors:** http://localhost:8000/api/monitoring/errors/recent

---

## 📝 Test Scenarios

### Scenario 1: Check System Health
```bash
# Basic check
curl http://localhost:8000/health

# Detailed check
curl http://localhost:8000/api/health/detailed | python -m json.tool
```

### Scenario 2: Monitor Costs
```bash
# Today's costs
curl http://localhost:8000/api/monitoring/costs | python -m json.tool

# This week's costs
curl "http://localhost:8000/api/monitoring/costs?time_period_hours=168" | python -m json.tool
```

### Scenario 3: Track Errors
```bash
# Get error statistics
curl http://localhost:8000/api/monitoring/errors | python -m json.tool

# Get critical errors only
curl "http://localhost:8000/api/monitoring/errors/recent?severity=critical" | python -m json.tool
```

### Scenario 4: View Queue Status
```bash
# Queue statistics
curl http://localhost:8000/api/queue/stats | python -m json.tool

# List all jobs
curl http://localhost:8000/api/jobs | python -m json.tool

# List pending jobs only
curl "http://localhost:8000/api/jobs?status=pending" | python -m json.tool
```

---

## 🎨 Pretty Print với jq (nếu có)

```bash
# Install jq first: brew install jq

curl http://localhost:8000/api/health/detailed | jq '.'
curl http://localhost:8000/api/monitoring/costs | jq '.total_cost_usd'
curl http://localhost:8000/api/monitoring/errors | jq '.total_unique_errors'
```

---

## 🔍 Quick Reference

| Endpoint | Type | Description |
|----------|------|-------------|
| `/health` | GET | Basic health |
| `/api/health/detailed` | GET | Full health check ⭐ |
| `/api/monitoring/costs` | GET | Cost tracking ⭐ |
| `/api/monitoring/errors` | GET | Error statistics ⭐ |
| `/api/monitoring/errors/recent` | GET | Recent errors ⭐ |
| `/` | GET | Dashboard UI |
| `/docs` | GET | API documentation |
| `/api/system/info` | GET | System info |
| `/api/jobs` | GET | List jobs |
| `/api/queue/stats` | GET | Queue stats |

**⭐ = New endpoints added in this update**

---

## 📊 Expected Response Examples

### Health Check Response
```json
{
  "status": "healthy",
  "version": "2.4.0",
  "timestamp": 1699876543.21
}
```

### Cost Tracking Response
```json
{
  "total_tokens_used": 125000,
  "total_cost_usd": 0.2500,
  "cost_by_provider": {
    "openai": 0.1800,
    "anthropic": 0.0700
  },
  "cost_by_model": {
    "gpt-4o-mini": 0.1800,
    "claude-3-5-sonnet": 0.0700
  },
  "average_cost_per_job": 0.0125,
  "jobs_processed": 20,
  "time_period": "24h"
}
```

### Error Statistics Response
```json
{
  "time_window_hours": 24,
  "total_unique_errors": 5,
  "total_occurrences": 12,
  "unresolved_count": 3,
  "by_severity": {
    "high": {"unique": 2, "occurrences": 5},
    "medium": {"unique": 3, "occurrences": 7}
  },
  "by_category": {
    "api_error": {"unique": 2, "occurrences": 8},
    "validation_error": {"unique": 3, "occurrences": 4}
  }
}
```

---

## 🚀 Start Server (if not running)

```bash
# Option 1: Direct
python api/main.py

# Option 2: Background script
./start_server.sh

# Option 3: Uvicorn
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

---

## 🛑 Stop Server

```bash
# Option 1: Stop script
./stop_server.sh

# Option 2: Find and kill process
lsof -ti:8000 | xargs kill -9
```

---

**Cập nhật:** 2025-11-13
**Server:** http://localhost:8000
**Documentation:** http://localhost:8000/docs
