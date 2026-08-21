#!/usr/bin/env bash
# dev.sh — bật backend (:8000) + frontend (:3000) cùng lúc.
# Chạy:  bash dev.sh     (hoặc  chmod +x dev.sh && ./dev.sh)
# Dừng:  Ctrl-C          (tắt cả hai server)
set -euo pipefail

# Về đúng thư mục repo dù gọi từ đâu (—— chặn lỗi "dirname illegal option")
cd "$(dirname -- "${BASH_SOURCE[0]:-$0}")"

# Kích hoạt venv nếu có
if [ -f venv/bin/activate ]; then
  # shellcheck disable=SC1091
  source venv/bin/activate
fi

echo "→ Backend : http://localhost:8000"
echo "→ Frontend: http://localhost:3000   (mở cái này để test)"
echo "  Ctrl-C để tắt cả hai."
echo

# Backend
uvicorn api.main:app --reload --port 8000 &
# Frontend
( cd frontend && npm run dev ) &

# Ctrl-C / thoát → tắt gọn cả hai tiến trình con
trap 'echo; echo "Đang tắt backend + frontend..."; kill 0' EXIT INT TERM
wait
