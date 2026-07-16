"""Production entry-point tests (M5 — REQ-MVP-043 runnable server).

``python -m server.web`` composes: provider config (TOML) -> provider adapter,
rulebook fixed prefix, gate-owned console stack (server.safety.bootstrap),
fallback detector + round-trip recorder, approval channel — then serves the
FastAPI app with uvicorn (injectable for tests; no real socket binding here).
"""

from __future__ import annotations

import sys

import pytest
from fastapi.testclient import TestClient

from server.web.serve import build_runtime, main, parse_args


class TestParseArgs:
    def test_defaults(self):
        args = parse_args([])
        assert args.host == "127.0.0.1"
        assert args.port == 8765
        assert args.console_port == 8000
        assert args.receive_port == 9000
        assert args.no_session_backup is False

    def test_overrides(self):
        args = parse_args(
            [
                "--port",
                "9001",
                "--console-host",
                "10.0.0.5",
                "--receive-port",
                "0",
                "--no-session-backup",
            ]
        )
        assert args.port == 9001
        assert args.console_host == "10.0.0.5"
        assert args.receive_port == 0
        assert args.no_session_backup is True


class TestBuildRuntime:
    def test_builds_a_servable_app_from_the_repo_config(self):
        # The repo config pins the providers; adapters build their SDK clients
        # lazily, so NO key is needed until a completion is attempted.
        args = parse_args(["--receive-port", "0", "--no-session-backup"])
        app, stack = build_runtime(args)
        try:
            with TestClient(app) as client:
                payload = client.get("/healthz").json()
                assert payload["ok"] is True
        finally:
            stack.stop()


class TestMain:
    def test_main_runs_uvicorn_and_stops_the_stack(self):
        calls: list[dict] = []

        def fake_run(app, **kwargs):
            calls.append({"app": app, **kwargs})

        code = main(
            ["--receive-port", "0", "--no-session-backup", "--port", "9017"],
            run=fake_run,
        )
        assert code == 0
        assert calls and calls[0]["port"] == 9017

    def test_module_entry_help_exits_zero(self, monkeypatch):
        import runpy

        monkeypatch.setattr(sys, "argv", ["server.web", "--help"])
        with pytest.raises(SystemExit) as excinfo:
            runpy.run_module("server.web", run_name="__main__", alter_sys=False)
        assert excinfo.value.code == 0


class TestM7ReviewWiring:
    def test_wires_the_deploy_review_flow(self):
        args = parse_args(["--receive-port", "0", "--no-session-backup"])
        app, stack = build_runtime(args)
        try:
            deps = app.state.deps
            assert deps.review_channel is not None
            assert deps.review_channel is not deps.approval_channel
            assert deps.deploy_pipeline is not None
            # The pipeline registers into the SAME registry the gate consults.
            assert deps.deploy_pipeline._registry is stack.registry
        finally:
            stack.stop()
