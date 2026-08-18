# Vibecode — Phase "Now": Gỡ chốt chặn deploy (VERIFY REPORT)

Ngày: 2026-08-18 · Nhánh: `feat/engine-quickwins` · Chủ thầu tự SCAN + sửa + VERIFY (rule #8: 6 vá đều ≤ vài dòng, cần phán đoán codebase mà Chủ thầu nắm rõ nhất từ vòng audit — dispatch Thợ cho mỗi vá thêm round-trip mà không tăng an toàn; đã log lý do).

Mục tiêu (theo `docs/TECH_DEBT_AND_ROADMAP.md` §4 NOW): đưa dự án về trạng thái **deploy sạch** — `docker build` + Render buildCommand chạy được, hết lỗi 500 nền, và thêm 1 rào CI bắt sống lỗi tái diễn.

## Đã làm

| ID | Vá | File | Bằng chứng verify |
|----|-----|------|-------------------|
| P0-1 | Thêm `get_settings()` | `config/settings.py` | import resolve về singleton; 22 test security/auth xanh |
| P0-2 | Khai báo `SQLAlchemy` | `requirements.txt`, `requirements.lock` | `pip install -r requirements.txt` rồi `import api.main` chạy sạch; module ORM glossary/TM import OK |
| P0-3 | Bỏ `COPY ui/` | `Dockerfile` | thư mục `ui/` không tồn tại; dòng COPY xóa, thêm ghi chú |
| P0-4 | Bỏ lồng prefix provider+glossary | `api/main.py`, `tests/api/test_glossary_tm.py` | 217 path OpenAPI, **0 path lồng**; `GET /api/v2/providers`→200, `/api/glossary/`→200, path lồng cũ→404 |
| P0-5 | Gộp `ConnectionManager` về `api.deps` | `api/main.py` | `api.main.manager is api.deps.manager` → **True**; `/ws` và broadcaster v1/v2 chung 1 instance |
| P0-6 | `--workers 2 → 1` | `render.yaml` | khớp Dockerfile CMD; ghi chú lý do (state in-process) |
| CI | Job `import-smoke` clean-room | `.github/workflows/ci.yml` | chạy đúng lệnh cục bộ → exit 0 sau khi vá |
| +1 | Pin `bcrypt<4.1` | `requirements.txt` | **phát hiện mới** (xem dưới); auth 86/86 xanh với bcrypt 4.0.1 |

## Phát hiện mới trong lúc VERIFY (clean-room install)

Chạy đúng những gì Render làm (`pip install -r requirements.txt`) lộ ra một **chốt chặn deploy chưa có trong sổ nợ**: `requirements.txt` để `passlib[bcrypt]` **không pin**, nên bản cài mới kéo `bcrypt` 5.x. `passlib` 1.7.x (`detect_wrap_bug`) ném `ValueError: password cannot be longer than 72 bytes` ngay lần hash đầu → **mọi thao tác đăng nhập/mật khẩu 500 trên Render**. Docker thoát nạn chỉ vì build từ `requirements.lock` (đã pin `bcrypt==4.0.1`). Đã pin `bcrypt>=4.0,<4.1` cho khớp lock. Đây đúng là hiện thân P0 của nợ P2-4 (requirements floor-only) đã ghi trong sổ.

## SCENARIO / kết quả VERIFY (Chủ thầu chạy thật)

- **Clean-room import**: cài **chỉ** `requirements.txt` → `import api.main; get_settings()` → `import-smoke OK`. (P0-1, P0-2)
- **Định tuyến** (qua OpenAPI + request thật bằng TestClient): 217 path, provider/glossary ở prefix đơn, path lồng cũ trả 404. (P0-4)
- **WebSocket**: `api.main.manager is api.deps.manager` = True; route `/ws` đăng ký client vào đúng manager mà v1+v2 broadcast. (P0-5)
- **Hồi quy**: `tests/unit/test_routes_*` = **64 passed**; `tests/security/` = **22 passed**; `tests/api/` = **86 passed / 0 failed** (với `bcrypt==4.0.1` như lock). Engine `core_v2` không đụng tới nên 254 test engine không đổi.

### Về 15 "fail" ban đầu ở `tests/api/` (đã truy nguyên tận gốc, không bỏ qua)
- **11 fail** = artifact sandbox: sandbox cài `bcrypt` 5.x (vì test bằng `requirements.txt`); về `4.0.1` như lock → hết. Không phải lỗi code.
- **4 fail** = test **mã hoá sẵn cái bug**: `GLOSSARY_BASE = "/api/glossary/api/glossary"` (có cả comment mô tả bug). Vá P0-4 sửa định tuyến đúng nên test gọi path lồng bị 404. Đã sửa test trỏ về `/api/glossary`. → chứng minh ngược rằng P0-4 đúng.

## OVERALL STATUS: READY (deploy-sạch)

Tất cả 6 chốt P0 trong sổ nợ đã gỡ, +1 chốt bcrypt phát hiện thêm. Không hồi quy. Việc còn phải làm ngoài sandbox: chạy `docker build` thật + deploy thử Render (sandbox không có Docker/không deploy được), và chạy `scripts/e2e_translation_smoke.py` với key thật (nghiệm thu engine-quickwins).

## Commit (nhánh `feat/engine-quickwins`)

- `814a097` fix(config): add get_settings() accessor to unblock API (P0)
- `a45b164` fix(deps): declare SQLAlchemy — glossary + TM v1 import it (P0)
- `33e4a21` fix(api): unify WebSocket manager and drop doubled router prefixes (P0)
- `817cca9` fix(deploy): drop non-existent ui/ copy and pin one worker (P0)
- `92acfd0` ci: clean-room import-smoke job guarding the two import P0s
- `a1d026f` docs: technical-debt register, bottleneck analysis and roadmap
- `8cfe75b` test(api): assert correct glossary path after prefix fix (P0-4)
- `284a25d` fix(deps): pin bcrypt<4.1 for passlib compatibility (deploy blocker)
