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
```

The boot guard rejects: a default/placeholder `SESSION_SECRET`, a secret shorter
than 32 chars, auth left disabled, or empty `CORS_ORIGINS`.

## 2. What turns on automatically in production

- **Auth is enforced per request.** With `SESSION_AUTH_ENABLED=true`,
  `get_current_user_id` rejects a missing or invalid `X-Session-Token` with
  **HTTP 401** — it never falls back to `default_user`. (In development, auth is
  off and `default_user` is returned so local dev needs no token.)
- **System-internal endpoints require auth**: `/api/health/detailed`,
  `/api/monitoring/costs`, `/api/monitoring/audit`, `/api/monitoring/errors`,
  `/api/monitoring/errors/recent`. The basic `/health` liveness probe stays
  public for load balancers.
- **Rate limiting** (`slowapi`) is active on the translate/upload/auth routes;
  tune limits in `api/rate_limiter.py` (`RateLimitConfig`).

## 3. Secrets & data hygiene

- Provide provider keys via env (`OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / …).
- `data/.encryption_key` is generated per deployment and **must never be
  committed** (it is gitignored). Back it up out-of-band; losing it makes
  encrypted data unreadable.
- Never log secrets or API keys.

## 4. Before opening the beta

- Run the full backend test suite green (incl. `tests/security/`).
- Set up automated backups of the SQLite `.db` files under `data/` (see
  `backup.sh`) and confirm a restore.
- Keep `--workers 1` unless `WS_REDIS_URL` is set (multi-worker is opt-in).
- Watch `/api/monitoring/costs` for LLM spend; set per-user quotas (roadmap P6).

## 5. Quick verification

```bash
# Boot guard: this MUST fail (insecure default secret in production)
SECURITY_MODE=production SESSION_AUTH_ENABLED=true python -c "from config.settings import Settings; Settings(security_mode='production')" \
  && echo "UNEXPECTED: booted" || echo "OK: production refused insecure config"

# Enforcement + boot guard unit tests
pytest tests/security/test_auth_enforcement.py -q
```
