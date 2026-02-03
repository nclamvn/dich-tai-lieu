"""
NXB Integration Bridge

Microservice cầu nối giữa:
- Companion Writer (Sáng tác) - Port 3002
- AI Publisher Pro (Dịch thuật/Xuất bản) - Port 3000

Chạy service:
    uvicorn integration_bridge.main:app --port 3003 --reload
"""
__version__ = "1.0.0"
