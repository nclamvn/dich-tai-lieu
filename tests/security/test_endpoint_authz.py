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

# main.py @app endpoints that must be gated
SENSITIVE_APP_PATHS = {
    "/api/cache/clear",
    "/api/cache/stats",
    "/api/processor/start",
    "/api/processor/stop",
    "/api/queue/stats",
    "/api/system/info",
    "/api/system/status",
    "/api/ocr/recognize",
    "/api/ocr/handwriting",
    "/api/ocr/translate",
    "/api/ocr/upload",
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
