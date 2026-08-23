"""Sensitive endpoints require authentication (beta hardening).

Control-plane, internal-state, cost-incurring (OCR) and file-upload endpoints
must carry the ``get_current_user_id`` dependency so they are fail-closed in
production (401 without a valid session) instead of anonymous-public. In
development the dependency is a no-op (returns ``default_user``), so this only
tightens production.

The checks inspect each route's resolved dependency tree directly (not an HTTP
round trip) so they don't depend on optional routers loading in every env.
"""

from api.deps import get_current_user_id

# main.py @app endpoints that must be gated (still defined inline at app level).
SENSITIVE_APP_PATHS = {
    "/api/ocr/recognize",
    "/api/ocr/handwriting",
    "/api/ocr/translate",
    "/api/ocr/upload",
}

# Control-plane paths that moved to api/routes/system.py (P2 dedup — the inline
# main.py duplicates were unreachable and are gone). They are session-gated at
# the include site (dependencies=_AUTH_REQUIRED, locked by test_router_authz.py).
# Under FastAPI's lazy include (_IncludedRouter) they don't appear as top-level
# app.routes entries, so presence is asserted on the router module and
# enforcement is asserted over HTTP with auth enabled.
SENSITIVE_SYSTEM_ROUTER_PATHS = {
    "/api/cache/clear": "post",
    "/api/cache/stats": "get",
    "/api/processor/start": "post",
    "/api/processor/stop": "post",
    "/api/queue/stats": "get",
    "/api/system/info": "get",
    "/api/system/status": "get",
}


def _requires_auth(route) -> bool:
    """True if get_current_user_id is anywhere in the route's dependency tree."""
    dependant = getattr(route, "dependant", None)
    if dependant is None:
        return False
    stack = list(getattr(dependant, "dependencies", []) or [])
    while stack:
        dep = stack.pop()
        if getattr(dep, "call", None) is get_current_user_id:
            return True
        stack.extend(getattr(dep, "dependencies", []) or [])
    return False


def test_sensitive_app_endpoints_require_auth():
    import api.main as m

    by_path = {}
    for route in m.app.routes:
        path = getattr(route, "path", None)
        if path in SENSITIVE_APP_PATHS:
            by_path[path] = route

    missing = SENSITIVE_APP_PATHS - by_path.keys()
    assert not missing, f"expected sensitive routes not registered: {sorted(missing)}"

    ungated = sorted(p for p, r in by_path.items() if not _requires_auth(r))
    assert not ungated, f"sensitive endpoints missing auth dependency: {ungated}"


def test_file_upload_requires_auth():
    # Inspected on the router object so the check is independent of app assembly.
    from api.routes.uploads import router

    upload = [r for r in router.routes if getattr(r, "path", None) == "/api/upload"]
    assert upload, "/api/upload route not found on uploads router"
    assert _requires_auth(upload[0]), "/api/upload must require authentication"


def test_system_router_covers_moved_control_plane_paths():
    # The paths deleted from main.py must all exist on the canonical router —
    # otherwise the dedup silently dropped an endpoint.
    from api.routes.system import router

    present = {getattr(r, "path", None) for r in router.routes}
    missing = set(SENSITIVE_SYSTEM_ROUTER_PATHS) - present
    assert not missing, f"control-plane paths lost in dedup: {sorted(missing)}"


def test_system_router_paths_fail_closed_when_auth_enabled(client, monkeypatch):
    # End-to-end proof the include-level dependency actually bites through
    # FastAPI's lazy-include machinery: with session auth ON, every moved path
    # must 401 for an anonymous caller (not 404 — that would mean the route
    # vanished; not 2xx/5xx — that would mean the gate is dead).
    from config.settings import settings

    monkeypatch.setattr(settings, "session_auth_enabled", True)
    for path, method in sorted(SENSITIVE_SYSTEM_ROUTER_PATHS.items()):
        resp = getattr(client, method)(path)
        assert resp.status_code == 401, (
            f"{method.upper()} {path} expected 401 with auth enabled, "
            f"got {resp.status_code}"
        )


def test_jwt_routers_have_no_open_endpoints():
    """Every usage/api_keys endpoint must resolve a JWT user dependency.

    These routers are exempt from the session-token router gate (their scheme is
    JWT bearer), which is only safe if NO endpoint slips through unauthenticated.
    /api/usage/plans and /api/api-keys/scopes/available were exactly that hole.
    """
    from core.auth.dependencies import get_current_user, get_current_active_user, get_token_payload
    from core.auth.dependencies import require_role  # noqa: F401  (factory — closures checked by name)
    from api.usage_router import router as usage_router
    from api.api_keys_router import router as api_keys_router

    jwt_deps = {get_current_user, get_current_active_user, get_token_payload}

    def _has_jwt_auth(route) -> bool:
        dependant = getattr(route, "dependant", None)
        if dependant is None:
            return False
        stack = list(getattr(dependant, "dependencies", []) or [])
        while stack:
            dep = stack.pop()
            call = getattr(dep, "call", None)
            if call in jwt_deps:
                return True
            # require_role(...) returns a closure named role_checker whose own
            # dependency tree includes get_current_active_user; recursing below
            # covers it, but accept it by name too in case the tree is pruned.
            if getattr(call, "__name__", "") == "role_checker":
                return True
            stack.extend(getattr(dep, "dependencies", []) or [])
        return False

    open_routes = []
    for router in (usage_router, api_keys_router):
        for route in router.routes:
            if not _has_jwt_auth(route):
                open_routes.append(f"{getattr(route, 'methods', '?')} {getattr(route, 'path', '?')}")
    assert not open_routes, f"JWT routers expose unauthenticated endpoints: {open_routes}"


def test_metrics_endpoint_is_guarded():
    """GET /metrics must carry _metrics_guard (token / production fail-closed)."""
    from api.routes.metrics import router, _metrics_guard

    routes = [r for r in router.routes if getattr(r, "path", None) == "/metrics"]
    assert routes, "/metrics route not found on metrics router"
    dependant = routes[0].dependant
    calls = [getattr(d, "call", None) for d in (dependant.dependencies or [])]
    assert _metrics_guard in calls, "/metrics missing _metrics_guard dependency"
