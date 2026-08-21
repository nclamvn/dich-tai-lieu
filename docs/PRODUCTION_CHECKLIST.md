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
CORS_ORIGINS=https://app.yourdomain.com   # explicit; no wildcard in production
# If CSRF is enabled for browser clients:
CSRF_ENABLED=true
CSRF_SECRET_KEY=<64 hex chars>
# Rate limiting is auto-on in production; override / tune if needed:
# RATE_LIMIT_ENABLED=true    # force on/off regardless of SECURITY_MODE
# RATE_LIMIT=240/minute      # global per-user/IP backstop
```

The boot guard rejects: a default/placeholder `SESSION_SECRET`, a secret shorter
than 32 chars, auth left disabled, empty `CORS_ORIGINS`, a **wildcard**
`CORS_ORIGINS=*` (credentials are allowed, so `*` is unsafe), and — when
`CSRF_ENABLED=true` — a placeholder or `<32`-char `CSRF_SECRET_KEY`.

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
pytest tests/security/test_auth_enforcement.py tests/security/test_endpoint_authz.py -q
```

## 6. Known follow-ups (not yet enforced — do before a *wide* launch)

These are tracked from the security audit. None blocks a small, trusted beta, but
each should be closed before opening the doors wide. (Rate limiting and the dead
`cors_config` footgun — previously listed here — are now **done**; see §2.)

- **Comprehensive per-router auth audit**: this pass gated the endpoints defined
  in `api/main.py` + `/api/upload`. The other ~20 included routers were spot-checked
  (jobs, monitoring, aps_v2, auth/api-keys/usage are guarded); a full sweep to
  confirm every state-changing route on every router is fail-closed is still owed.
  A deny-by-default auth middleware (allow-list `/`, `/health*`, `/api/auth/*`,
  docs) would make new routes protected automatically.
- **Two auth systems**: product endpoints authenticate via **session token**
  (`get_current_user_id`), while the live login issues **JWTs**
  (`get_current_active_user`). They don't interoperate — decide on one, or bridge
  them, so a logged-in user can actually call the session-token endpoints in prod.
- **Error-detail leakage**: several handlers `raise HTTPException(500, detail=f"…{e}")`,
  leaking exception strings (paths, DB errors) to clients; route them through the
  generic sanitizer used for uncaught 500s.
