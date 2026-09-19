"""SPEC-LDWIRE-001 M7 -- REQ-LDWIRE-008/009/010, AC-LDWIRE-008/009/010/011.

The direct evidence that spec.md section 1.1 measured gap ("never actually
connected") is closed by THIS SPEC -- drives the REAL server.web.serve
build_runtime() assembly (the exact production entry point main() calls) and
confirms the director routes are actually mounted, a freshly issued credential
actually authenticates, and no sqlite3.ProgrammingError happens across repeated
requests. RED first: build_runtime() does not pass director= to WebDeps(...) yet.
"""

from __future__ import annotations

import socket

from fastapi.testclient import TestClient

from server.web.serve import build_runtime, parse_args

#: The 10 contract Section 3 route (method, path) pairs director_api.py wires
#: (spec.md section 1.1 grep-measured count -- see plan-auditor D1 fix).
_EXPECTED_DIRECTOR_ROUTES = {
    ("GET", "/api/director/v1/projects/{project_id}/context"),
    ("GET", "/api/director/v1/projects/{project_id}/knowledge"),
    ("GET", "/api/director/v1/projects/{project_id}/plans/{plan_id}"),
    (
        "POST",
        "/api/director/v1/projects/{project_id}/plans/{plan_id}/revisions/{revision}/approvals",
    ),
    (
        "POST",
        "/api/director/v1/projects/{project_id}/plans/{plan_id}/revisions/{revision}/rejections",
    ),
    ("POST", "/api/director/v1/projects/{project_id}/validations"),
    ("PUT", "/api/director/v1/projects/{project_id}/plans/{plan_id}"),
    (
        "POST",
        "/api/director/v1/projects/{project_id}/plans/{plan_id}/revisions/{revision}/apply",
    ),
    ("GET", "/api/director/v1/projects/{project_id}/executions/{execution_id}"),
    ("POST", "/api/director/v1/projects/{project_id}/feedback-proposals"),
}


def _free_udp_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _collect_mounted_routes(app) -> set[tuple[str, str]]:
    """(method, path) pairs across app.routes, recursing into fastapi 0.139s
    lazy ``_IncludedRouter`` wrapper (its own routes live under
    ``.original_router.routes``, not flattened into ``app.routes`` directly --
    measured on this repos installed fastapi==0.139.1)."""
    collected: set[tuple[str, str]] = set()
    for route in app.routes:
        if type(route).__name__ == "_IncludedRouter":
            for sub in route.original_router.routes:
                for method in getattr(sub, "methods", ()):
                    if method != "HEAD":
                        collected.add((method, sub.path))
            continue
        for method in getattr(route, "methods", ()):
            if method != "HEAD":
                collected.add((method, route.path))
    return collected


def _build(**overrides) -> tuple:
    argv = ["--receive-port", "0", "--no-session-backup", "--console-port", str(_free_udp_port())]
    return build_runtime(parse_args(argv))


class TestDirectorDepsInjected:
    def test_webdeps_director_is_not_none(self) -> None:
        app, stack = _build()
        try:
            assert app.state.deps.director is not None
        finally:
            stack.stop()

    def test_apply_coordinator_reuses_the_same_gate_instance(self) -> None:
        """AC-LDWIRE-008 -- identity comparison, not equality: no second SafetyGate."""
        app, stack = _build()
        try:
            deps = app.state.deps.director
            assert deps.apply_coordinator is not None
            assert deps.apply_coordinator._gate is stack.gate
        finally:
            stack.stop()


class TestRoutesActuallyMounted:
    def test_all_ten_contract_routes_are_present(self) -> None:
        app, stack = _build()
        try:
            mounted = _collect_mounted_routes(app)
            missing = _EXPECTED_DIRECTOR_ROUTES - mounted
            assert missing == set(), f"director routes not mounted: {sorted(missing)}"
        finally:
            stack.stop()


class TestIssuedCredentialAuthenticatesInProduction:
    def test_bearer_token_from_boot_reaches_200_on_get_context(self) -> None:
        """AC-LDWIRE-010 -- end-to-end evidence the section 1.1 measured gap is
        closed: the mounted app, driven with the M5-issued credential, answers
        200 (not 401/403) on GET context."""
        app, stack = _build()
        try:
            director = app.state.deps.director
            with TestClient(app) as client:
                response = client.get(
                    "/api/director/v1/projects/default/context",
                    headers={
                        "authorization": f"Bearer {director.operator_bearer_token}",
                        "host": "127.0.0.1",
                    },
                )
            assert response.status_code == 200, response.text
            assert response.json()["schema_version"] == "1.0.0"
        finally:
            stack.stop()


class TestNoCrossThreadSqliteError:
    def test_repeated_requests_never_raise_programming_error(self) -> None:
        """AC-LDWIRE-011 / REQ-LDWIRE-010 -- DirectorStore/ExecutionJournal are
        constructed in build_director_deps(), called from build_runtime() on the
        SAME thread that (in production) later drives the uvicorn event loop; the
        async route handlers here run through TestClients own portal thread, so a
        thread mismatch would surface as sqlite3.ProgrammingError on ANY of these
        repeated calls."""
        app, stack = _build()
        try:
            director = app.state.deps.director
            headers = {
                "authorization": f"Bearer {director.operator_bearer_token}",
                "host": "127.0.0.1",
            }
            with TestClient(app) as client:
                for _ in range(5):
                    response = client.get(
                        "/api/director/v1/projects/default/context", headers=headers
                    )
                    assert response.status_code == 200, response.text
        finally:
            stack.stop()
