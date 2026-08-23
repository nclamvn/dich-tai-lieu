"""Router-level auth sweep — sensitive routers are fail-closed in production.

PR #23 gated the endpoints defined in api/main.py + /api/upload. This sweep adds
``dependencies=[Depends(get_current_user_id)]`` at the ``include_router`` site for
every all-private, session-token router, so their routes are fail-closed in
production (401 without a valid X-Session-Token) and a no-op in development.

The check is on the wiring itself (the include_router calls), which is
deterministic — it doesn't depend on optional routers being importable in every
environment — and it forces a conscious decision for any *new* router: it must be
listed as protected or as a documented public/JWT exemption, or this test fails.
"""

import pathlib
import re

import api.main

# Session-token routers whose include must carry the auth dependency.
PROTECTED_ROUTERS = {
    "author.router",
    "editor_router",
    "batch_router",
    "provider_router",
    "glossary_router",
    "error_router",
    "tm_router",
    "preview_router",
    "cinema_router",
    "screenplay_router",
    "settings_router",
    "system_router",
    "book_writer_router",
    "book_writer_v2_router",
    "dashboard_router",
    "jobs_router",
    "uploads_router",
    "batch_legacy_router",
    "job_outputs_router",
}

# Intentionally NOT blanket-protected here, each for a documented reason:
#  - auth: login/register must be reachable anonymously (JWT issuance)
#  - usage/api_keys: JWT-bearer self-enforcing on EVERY endpoint (a session-token
#    dep would demand both schemes at once) — test_jwt_routers_have_no_open_endpoints
#    in test_endpoint_authz.py locks the every-endpoint part
#  - aps_v2: per-route session deps (public profiles + health remain open)
#  - health: public /health liveness (+ its own _PROTECT on monitoring)
#  - metrics: own bearer-token gate (_metrics_guard): METRICS_TOKEN when set,
#    fail-closed 403 in production when unset — session auth can't serve scrapers
EXEMPT_ROUTERS = {
    "auth_router",
    "usage_router",
    "api_keys_router",
    "aps_v2_router",
    "health_router",
    "metrics_router",
}

_INCLUDE = re.compile(r"app\.include_router\(\s*([A-Za-z0-9_.]+)\s*(,.*)?\)")


def _includes():
    """Return {router_arg: full_line} for every app.include_router(...) call."""
    text = pathlib.Path(api.main.__file__).read_text(encoding="utf-8")
    out = {}
    for line in text.splitlines():
        m = _INCLUDE.search(line)
        if m:
            out[m.group(1)] = line
    return out


def test_every_router_is_classified():
    # A new router must be consciously placed in PROTECTED or EXEMPT — not left
    # to slip in unauthenticated by omission.
    included = set(_includes())
    unclassified = included - PROTECTED_ROUTERS - EXEMPT_ROUTERS
    assert not unclassified, f"router(s) not classified protected/exempt: {unclassified}"


def test_protected_routers_declare_auth_dependency():
    includes = _includes()
    missing = []
    for router in PROTECTED_ROUTERS:
        line = includes.get(router)
        assert line is not None, f"{router} is no longer included in api/main.py"
        if "dependencies=_AUTH_REQUIRED" not in line:
            missing.append(router)
    assert not missing, f"sensitive routers missing the auth dependency: {missing}"


def test_exempt_routers_are_not_session_gated():
    # These must stay off the session-token gate (public reference or JWT-auth).
    includes = _includes()
    wrongly_gated = [
        r for r in EXEMPT_ROUTERS
        if includes.get(r) and "dependencies=_AUTH_REQUIRED" in includes[r]
    ]
    assert not wrongly_gated, f"exempt routers wrongly session-gated: {wrongly_gated}"
