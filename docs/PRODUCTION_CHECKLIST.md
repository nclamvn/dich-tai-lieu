# Production / Beta hardening checklist

Steps to take the app from the local `development` default (auth OFF, everything
public) to a **limited public beta**. The app **refuses to boot** in
`SECURITY_MODE=production` unless the required secrets and flags below are set —
this is intentional (`config/settings.py::_validate_security_settings`).

## 1. Required environment (production refuses to boot without these)

```bash
SECURITY_MODE=production
SESSION_AUTH_ENABLED=true                 # or API_KEY_AUTH_ENABLED=true
SESSION_SECRET=<64 hex chars>             # python -c "import secrets; print(secrets.token_hex(32))"
JWT_SECRET_KEY=<64+ random chars>         # python -c "import secrets; print(secrets.token_urlsafe(48))"
CORS_ORIGINS=https://app.yourdomain.com   # explicit; no wildcard in production
# If CSRF is enabled for browser clients:
CSRF_ENABLED=true
CSRF_SECRET_KEY=<64 hex chars>
# Rate limiting is auto-on in production; override / tune if needed:
# RATE_LIMIT_ENABLED=true    # force on/off regardless of SECURITY_MODE
# RATE_LIMIT=240/minute      # global per-user/IP backstop
# Prometheus scraping (optional — /metrics is 403 in production without it):
# METRICS_TOKEN=<random>     # scraper sends "Authorization: Bearer <token>"
```

The boot guard rejects: a default/placeholder `SESSION_SECRET`, a secret shorter
than 32 chars, auth left disabled, empty `CORS_ORIGINS`, a **wildcard**
`CORS_ORIGINS=*` (credentials are allowed, so `*` is unsafe), a missing /
placeholder / `<32`-char `JWT_SECRET_KEY` (unset means a **random per-process**
key: every restart invalidates all JWTs and each worker signs with a different
one), and — when `CSRF_ENABLED=true` — a placeholder or `<32`-char
`CSRF_SECRET_KEY`.

## 2. What turns on automatically in production

- **Auth is enforced per request.** With `SESSION_AUTH_ENABLED=true`,
  `get_current_user_id` rejects a missing or invalid `X-Session-Token` with
  **HTTP 401** — it never falls back to `default_user`. (In development, auth is
  off and `default_user` is returned so local dev needs no token.)
- **System-internal endpoints require auth**: `/api/health/detailed`,
  `/api/monitoring/costs`, `/api/monitoring/audit`, `/api/monitoring/errors`,
  `/api/monitoring/errors/recent`. The basic `/health` liveness probe stays
  public for load balancers.
- **Control-plane / cost / upload endpoints require auth** (fail-closed via
  `get_current_user_id`): `/api/processor/start|stop`, `/api/cache/clear|stats`,
  `/api/queue/stats`, `/api/system/info|status`, `/api/ocr/*`, and `/api/upload`.
  Guarded by `tests/security/test_endpoint_authz.py`.
- **Router-level auth sweep.** Every all-private session-token router is gated at
  the `include_router` site with `dependencies=[Depends(get_current_user_id)]`:
  author, editor, tm, cinema, screenplay, settings, dashboard, provider, system,
  book-writer (v1/v2), jobs, batch (+legacy), preview, job-outputs, error-dashboard,
  **glossary** (per-user CRUD — gated since the P1 debt paydown).
  Fail-closed in production, no-op in dev. Guarded by
  `tests/security/test_router_authz.py`. Deliberately NOT session-gated (each for a
  reason): `auth` (login must be anonymous); `usage`/`api_keys` (JWT-bearer on
  **every** endpoint — `/plans` and `/scopes/available` were closed in the P1
  paydown; locked by `test_jwt_routers_have_no_open_endpoints`); `aps_v2`
  (per-route session deps); `health` (public `/health`); `metrics` (own bearer
  gate, next bullet).
- **`/metrics` is fail-closed.** With `METRICS_TOKEN` set, scrapers must send
  `Authorization: Bearer <token>` (enforced in every mode, constant-time compare).
  Without it, `/metrics` stays open in development but returns **403 in
  production** — the path/latency/error tables are a recon map of the API.
  Guarded by `tests/security/test_metrics_gate.py`.
- **Server error messages are sanitized.** Any `HTTPException(500, …)` returns a
  generic message + `error_id` (the real detail is logged), so raised exception
  strings (paths, DB errors) never reach clients; `<500` and other `5xx` keep their
  curated text. Guarded by `tests/security/test_error_sanitize.py`.
- **Interactive API docs are disabled** (`/docs`, `/redoc`, `/openapi.json` → 404;
  `/` returns a plain liveness JSON) so the endpoint surface isn't self-documented
  to anonymous callers. In development they stay on.
- **Passwordless session login is refused** in production — the credentialed
  login in `auth_router` (`/api/auth/login`, JWT + bcrypt) is the only login.
- **Rate limiting is enforced.** One shared limiter (`api/rate_limiter.py`),
  **enabled only in production** (`RATE_LIMIT_ENABLED` env overrides, so dev/tests
  are never throttled). `SlowAPIMiddleware` applies a generous global backstop
  (`RATE_LIMIT`, default 240/min per user/IP; the `/health` probe is exempt), and
  tight per-route limits guard the abuse surface: login `10/min`, register `5/min`,
  `/api/upload` `20/min`, plus the existing `/api/cache/clear` and `/api/ocr/upload`.
  Over the limit returns **HTTP 429** with a `Retry-After` header. Guarded by
  `tests/security/test_rate_limiting.py`.

## 3. Secrets & data hygiene

- Provide provider keys via env (`OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / …).
- `data/.encryption_key` is generated per deployment and **must never be
  committed** (it is gitignored). Back it up out-of-band; losing it makes
  encrypted data unreadable.
- Never log secrets or API keys.

## 4. Before opening the beta

- Run the full backend test suite green (incl. `tests/security/`).
- Set up automated backups of the SQLite `.db` files under `data/` with the
  **WAL-safe** `python scripts/backup_db.py --dest <dir>` (SQLite online-backup
  API — a plain `cp`/`tar` of a live WAL database can be torn) and confirm a
  restore per `docs/BACKUP_RESTORE.md`. `backup.sh` (naive `cp` + `.env`/uploads
  archive) is convenience only — do **not** rely on it for the databases.
- Keep `--workers 1` unless `WS_REDIS_URL` is set (multi-worker is opt-in).
- Watch `/api/monitoring/costs` for LLM spend; set per-user quotas (roadmap P6).

## 5. Quick verification

```bash
# Boot guard: this MUST fail (insecure default secret in production)
SECURITY_MODE=production SESSION_AUTH_ENABLED=true python -c "from config.settings import Settings; Settings(security_mode='production')" \
  && echo "UNEXPECTED: booted" || echo "OK: production refused insecure config"

# Enforcement + boot guard unit tests
pytest tests/security/test_auth_enforcement.py tests/security/test_endpoint_authz.py \
       tests/security/test_router_authz.py tests/security/test_error_sanitize.py -q
```

> **Validate the auth sweep in staging before a wide launch.** The router-level
> sweep (§2) is session-token deny-by-default in production; confirm the frontend's
> real flow doesn't rely on any of the newly-gated routes being anonymous, and that
> the remaining public exemptions (aps_v2 reference GETs, `/health`) are the
> intended set. Remember `/metrics` needs `METRICS_TOKEN` in your scrape config.

## 6. Known follow-ups (not yet enforced — do before a *wide* launch)

These are tracked from the security audit. None blocks a small, trusted beta, but
each should be closed before opening the doors wide. (Rate limiting, the dead
`cors_config` footgun, the per-router auth sweep, and 500 error-detail sanitizing
— previously listed here — are now **done**; see §2.)

- **WebSocket auth**: the deny-by-default sweep is HTTP-only. `WS /ws` self-guards,
  but `WS /api/preview/stream/{job_id}`, `WS /api/cinema/ws/jobs/{job_id}` and the
  book-writer WS endpoints stream by id with **no token check** — add a `?token=`
  check like `/ws` has.
- **Sensitive sub-routes on the exempt routers**: ~~glossary~~ (now fully
  session-gated), ~~`/metrics`~~ (now bearer-token / production-403 fail-closed),
  ~~usage/api_keys catalog endpoints~~ (now JWT-gated). Remaining: `aps_v2` keeps
  public reference GETs by design — re-audit its non-reference routes per-route
  before a wide launch.
- **Two auth systems**: product endpoints authenticate via **session token**
  (`get_current_user_id`), while the live login issues **JWTs**
  (`get_current_active_user`). They don't interoperate — decide on one, or bridge
  them, so a logged-in user can actually obtain a session token in prod. (This is
  the interop question the staging validation above will surface.)
