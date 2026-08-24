#!/usr/bin/env bash
# dev.sh — bật backend + frontend cùng lúc, TỰ NÉ CỔNG BẬN.
# Chạy:      bash dev.sh
# Ép cổng:   BACKEND_PORT=8001 FRONTEND_PORT=3001 bash dev.sh
# Dừng:      Ctrl-C   (tắt cả hai server)
set -euo pipefail

# Về đúng thư mục repo dù gọi từ đâu (—— chặn lỗi "dirname illegal option")
cd "$(dirname -- "${BASH_SOURCE[0]:-$0}")"

# Kích hoạt venv nếu có
if [ -f venv/bin/activate ]; then
  # shellcheck disable=SC1091
  source venv/bin/activate
fi

port_busy() { lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1; }

# ── Dọn "xác chết" dev cũ CỦA CHÍNH REPO NÀY trước khi bật ──
# Một phiên trước tắt không sạch để lại: next dev giữ khóa frontend/.next/dev/lock
# (né cổng cũng vô ích — lock theo THƯ MỤC, không theo cổng) và uvicorn giữ :8000.
# Chỉ giết tiến trình xác định là của repo này — không đụng dự án khác.

# 1) next dev cũ: tiến trình đang giữ file lock chính là nó.
LOCK="frontend/.next/dev/lock"
if [ -e "$LOCK" ]; then
  HOLDERS="$(lsof -t "$LOCK" 2>/dev/null || true)"
  if [ -n "$HOLDERS" ]; then
    echo "⚠ next dev cũ của repo này còn sống (PID: $HOLDERS) — tắt để nhường chỗ."
    # shellcheck disable=SC2086
    kill -9 $HOLDERS 2>/dev/null || true
    sleep 1
  fi
  rm -f "$LOCK"   # lock mồ côi (tiến trình chết rồi) thì dọn luôn
fi

# 2) uvicorn cũ: nhận diện qua cwd của tiến trình == thư mục repo này.
for pid in $(pgrep -f "uvicorn api.main:app" 2>/dev/null || true); do
  PCWD="$(lsof -a -p "$pid" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p' | head -1)"
  if [ "$PCWD" = "$PWD" ]; then
    echo "⚠ uvicorn cũ của repo này còn sống (PID: $pid) — tắt để nhường chỗ."
    kill -9 "$pid" 2>/dev/null || true
  fi
done

# Backend: mặc định 8000, bận thì dò tiếp 8001, 8002… (CORS không phụ thuộc
# cổng backend — chỉ origin của frontend mới phải nằm trong allowlist).
if [ -z "${BACKEND_PORT:-}" ]; then
  BACKEND_PORT=8000
  while port_busy "$BACKEND_PORT"; do BACKEND_PORT=$((BACKEND_PORT + 1)); done
fi

# Frontend: chỉ thử các cổng nằm sẵn trong CORS dev của backend
# (config/settings.py::get_cors_origins) — cổng lạ sẽ bị backend chặn CORS.
if [ -z "${FRONTEND_PORT:-}" ]; then
  for p in 3000 3001 3003 4000 5173; do
    if ! port_busy "$p"; then FRONTEND_PORT="$p"; break; fi
  done
  if [ -z "${FRONTEND_PORT:-}" ]; then
    echo "✗ Các cổng frontend 3000/3001/3003/4000/5173 đều bận." >&2
    echo "  Giải phóng một cổng:  lsof -ti:3000 | xargs kill -9" >&2
    exit 1
  fi
fi

[ "$BACKEND_PORT" != "8000" ] && echo "⚠ Cổng 8000 bận → backend chuyển sang :$BACKEND_PORT"
[ "$FRONTEND_PORT" != "3000" ] && echo "⚠ Cổng 3000 bận → frontend chuyển sang :$FRONTEND_PORT"
echo "→ Backend : http://localhost:$BACKEND_PORT"
echo "→ Frontend: http://localhost:$FRONTEND_PORT   (mở cái này để test)"
echo "  Ctrl-C để tắt cả hai."
echo

# Backend
uvicorn api.main:app --reload --port "$BACKEND_PORT" &
# Frontend — NEXT_PUBLIC_API_URL trỏ đúng cổng backend vừa chọn (khi khác 8000,
# fallback localhost:8000 trong lib/api/config.ts sẽ sai nếu thiếu biến này).
(
  cd frontend
  NEXT_PUBLIC_API_URL="http://localhost:$BACKEND_PORT" npm run dev -- -p "$FRONTEND_PORT"
) &

# Ctrl-C / thoát → tắt gọn cả hai tiến trình con (trap tự gỡ để chỉ chạy MỘT lần
# — bản cũ in "Đang tắt..." ba lần vì EXIT/INT/TERM cùng bắn)
trap 'trap - EXIT INT TERM; echo; echo "Đang tắt backend + frontend..."; kill 0' EXIT INT TERM
wait
