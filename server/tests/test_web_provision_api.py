"""Responder provisioning REST API (M4 — REQ-DEPLOY-010/011, AC-DEPLOY-006/007).

Mirrors test_web_settings_api: two endpoints let the packaged UI install the
bundled responder plugin into the M1-configured import directory and read the
onPC-load guide. Wiring parity with the settings router is verified through
create_app; the no-OSC-send guard mirrors the settings-API guard.

    GET  /api/provision/responder   install status + guide (import dir + port)
    POST /api/provision/responder   copy the bundled plugin into the import dir
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.deploy.provisioning import (
    RESPONDER_ASSETS,
    install_responder,
    read_installed_osc_slot,
)
from server.deploy.settings import UserSettings, save_user_settings
from server.web.provision_api import ProvisionDeps, build_provision_router


def _settings_file(tmp_path, *, import_dir, receive_port=9000, osc_slot=1):
    settings = UserSettings(
        active_provider="gemini",
        console_host="127.0.0.1",
        console_port=8000,
        receive_port=receive_port,
        web_host="127.0.0.1",
        web_port=8765,
        plugin_import_dir=str(import_dir),
        osc_slot=osc_slot,
    )
    path = tmp_path / "settings.toml"
    save_user_settings(settings, path)
    return path


def _client(tmp_path, *, import_dir, receive_port=9000, osc_slot=1):
    settings_path = _settings_file(
        tmp_path, import_dir=import_dir, receive_port=receive_port, osc_slot=osc_slot
    )
    deps = ProvisionDeps(settings_path=settings_path, seed_path=tmp_path / "no-seed.toml")
    app = FastAPI()
    app.include_router(build_provision_router(deps))
    return TestClient(app)


class TestProvisionStatus:
    def test_get_reports_not_installed_before_install(self, tmp_path):
        import_dir = tmp_path / "plugins"
        client = _client(tmp_path, import_dir=import_dir)
        body = client.get("/api/provision/responder").json()

        assert body["import_dir"] == str(import_dir)
        assert body["installed"] == {name: False for name in RESPONDER_ASSETS}
        assert body["installed_all"] is False
        # The guide carries the receive port + onPC-load steps (AC-DEPLOY-007).
        assert body["guide"]["receive_port"] == 9000
        assert "9000" in " ".join(body["guide"]["steps"])

    def test_guide_uses_the_configured_receive_port(self, tmp_path):
        client = _client(tmp_path, import_dir=tmp_path / "plugins", receive_port=9222)
        body = client.get("/api/provision/responder").json()
        assert body["guide"]["receive_port"] == 9222
        assert "9222" in " ".join(body["guide"]["steps"])


class TestProvisionInstall:
    def test_post_installs_the_bundle_into_the_import_dir(self, tmp_path):
        # AC-DEPLOY-006 ②: POST copies the bundled plugin into the import dir.
        import_dir = tmp_path / "plugins"
        client = _client(tmp_path, import_dir=import_dir)

        response = client.post("/api/provision/responder")
        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is True
        assert set(body["installed"]) == set(RESPONDER_ASSETS)
        for name in RESPONDER_ASSETS:
            assert (import_dir / name).is_file()

        # A subsequent status read now reports fully installed.
        status = client.get("/api/provision/responder").json()
        assert status["installed_all"] is True

    def test_the_configured_osc_slot_reaches_the_installed_file(self, tmp_path):
        # End-to-end through the router, not just install_responder: the value
        # has to survive settings -> _resolve -> install_responder. A unit test
        # on either end alone passes while the wiring between them is missing —
        # the same shape as the unmounted-router defect the package E2E caught.
        import_dir = tmp_path / "plugins"
        client = _client(tmp_path, import_dir=import_dir, osc_slot=2)

        assert client.post("/api/provision/responder").status_code == 200

        lua = (import_dir / "copilot_responder.lua").read_text(encoding="utf-8")
        slot_lines = [ln.strip() for ln in lua.splitlines() if ln.strip().startswith("osc_slot")]
        # Assert the VALUE reached the file, not the comment prose beside it:
        # pinning the whole line made an explanatory edit to the Lua comment
        # fail a test about settings wiring.
        assert len(slot_lines) == 1, slot_lines
        assert slot_lines[0].startswith("osc_slot = 2,"), slot_lines[0]

    def test_post_returns_the_guide(self, tmp_path):
        client = _client(tmp_path, import_dir=tmp_path / "plugins", receive_port=9007)
        body = client.post("/api/provision/responder").json()
        assert body["guide"]["receive_port"] == 9007

    def test_install_failure_returns_human_friendly_500(self, tmp_path):
        # Edge case (acceptance.md): import dir path unusable → human-friendly
        # Korean guidance, not a raw OS traceback. Point the import dir under an
        # existing FILE so mkdir(parents=True) raises NotADirectoryError.
        blocker = tmp_path / "not-a-dir"
        blocker.write_text("i am a file", encoding="utf-8")
        client = _client(tmp_path, import_dir=blocker / "plugins")

        response = client.post("/api/provision/responder")
        assert response.status_code == 500
        detail = response.json()["detail"]
        assert detail["error"] == "install_failed"
        # No raw OS error string leaks as the message.
        assert "확인해 주세요" in detail["message"]


class TestOscSlotMismatchGuard:
    """Rendering the slot from settings only helps if the settings are right.

    The live console replies on row 2, but the shipped default is 1 — so an
    operator who installs before setting the row silently re-breaks the link,
    which is the exact failure the rendering was added to prevent. A blind
    overwrite is refused; the operator either fixes the setting or says
    explicitly that the configured value should win.
    """

    def test_status_reports_both_values_and_the_mismatch(self, tmp_path):
        import_dir = tmp_path / "plugins"
        install_responder(import_dir, osc_slot=2)
        client = _client(tmp_path, import_dir=import_dir, osc_slot=1)

        body = client.get("/api/provision/responder").json()
        assert body["configured_osc_slot"] == 1
        assert body["installed_osc_slot"] == 2
        assert body["osc_slot_mismatch"] is True

    def test_matching_values_are_not_a_mismatch(self, tmp_path):
        import_dir = tmp_path / "plugins"
        install_responder(import_dir, osc_slot=2)
        client = _client(tmp_path, import_dir=import_dir, osc_slot=2)

        body = client.get("/api/provision/responder").json()
        assert body["osc_slot_mismatch"] is False

    def test_nothing_installed_is_not_a_mismatch(self, tmp_path):
        # A first install has nothing to disagree with.
        client = _client(tmp_path, import_dir=tmp_path / "plugins", osc_slot=2)
        body = client.get("/api/provision/responder").json()
        assert body["installed_osc_slot"] is None
        assert body["osc_slot_mismatch"] is False

    def test_install_is_refused_on_a_mismatch(self, tmp_path):
        import_dir = tmp_path / "plugins"
        install_responder(import_dir, osc_slot=2)
        client = _client(tmp_path, import_dir=import_dir, osc_slot=1)

        response = client.post("/api/provision/responder")
        assert response.status_code == 409
        detail = response.json()["detail"]
        # Both numbers must be named, or the operator cannot tell which way to
        # resolve it.
        assert detail["configured_osc_slot"] == 1
        assert detail["installed_osc_slot"] == 2

    def test_a_refused_install_does_not_touch_the_file(self, tmp_path):
        # A guard that reports the conflict and overwrites anyway is worthless.
        import_dir = tmp_path / "plugins"
        install_responder(import_dir, osc_slot=2)
        before = (import_dir / "copilot_responder.lua").read_bytes()

        client = _client(tmp_path, import_dir=import_dir, osc_slot=1)
        assert client.post("/api/provision/responder").status_code == 409

        assert (import_dir / "copilot_responder.lua").read_bytes() == before

    def test_an_explicit_confirmation_lets_the_configured_value_win(self, tmp_path):
        import_dir = tmp_path / "plugins"
        install_responder(import_dir, osc_slot=2)
        client = _client(tmp_path, import_dir=import_dir, osc_slot=1)

        response = client.post("/api/provision/responder?confirm_osc_slot=true")
        assert response.status_code == 200
        assert read_installed_osc_slot(import_dir) == 1

    def test_a_matching_install_needs_no_confirmation(self, tmp_path):
        import_dir = tmp_path / "plugins"
        install_responder(import_dir, osc_slot=2)
        client = _client(tmp_path, import_dir=import_dir, osc_slot=2)
        assert client.post("/api/provision/responder").status_code == 200

    def test_the_first_install_needs_no_confirmation(self, tmp_path):
        client = _client(tmp_path, import_dir=tmp_path / "plugins", osc_slot=2)
        assert client.post("/api/provision/responder").status_code == 200

    def test_an_unreadable_installed_slot_still_warns_before_overwriting(self, tmp_path):
        # A hand-mangled or refactored file whose slot cannot be read is the
        # case where an operator most needs to look before it is replaced.
        import_dir = tmp_path / "plugins"
        import_dir.mkdir()
        (import_dir / "copilot_responder.lua").write_text("-- edited\n", encoding="utf-8")
        client = _client(tmp_path, import_dir=import_dir, osc_slot=2)

        response = client.post("/api/provision/responder")
        assert response.status_code == 409
        assert response.json()["detail"]["installed_osc_slot"] is None


class TestCreateAppWiring:
    def test_provision_router_mounts_via_create_app(self, tmp_path):
        # Parity with the M3 settings router: WebDeps.provision is included by
        # create_app, alongside /api/settings and the SPA static mount.
        from server.safety.audit import AuditLog
        from server.web.app import WebDeps, create_app

        import_dir = tmp_path / "plugins"
        settings_path = _settings_file(tmp_path, import_dir=import_dir)

        gate, _console, _audit = _minimal_gate(tmp_path)
        deps = WebDeps(
            gate=gate,
            provider=_NullProvider(),
            system_prefix="PREFIX",
            audit=AuditLog(tmp_path / "audit"),
            approval_channel=_NullChannel(),
            provision=ProvisionDeps(
                settings_path=settings_path, seed_path=tmp_path / "no-seed.toml"
            ),
        )
        with TestClient(create_app(deps)) as client:
            status = client.get("/api/provision/responder")
            assert status.status_code == 200
            assert status.json()["import_dir"] == str(import_dir)

            installed = client.post("/api/provision/responder")
            assert installed.status_code == 200
            for name in RESPONDER_ASSETS:
                assert (import_dir / name).is_file()


# AC-DEPLOY-014 ③ / SAFETY-1: the interim per-module OSC-send-surface guard (M4
# ``test_provision_api_module_has_no_console_send_path``) is CONSOLIDATED into the
# M10 AC-DEPLOY-014 ③ fail-closed allowlist scan —
# ``server/tests/test_deploy_safety_invariants.py`` — which scans server/web/provision_api.py
# (and every other server module) against one named send-surface allowlist. See
# ``TestAcDeploy014OscSendSurfaceAllowlist`` there.


# ---------------------------------------------------------------- minimal WebDeps doubles


class _NullProvider:
    def complete(self, *args, **kwargs):  # pragma: no cover - never invoked here
        raise NotImplementedError


class _NullChannel:
    def resolve(self, *args, **kwargs):  # pragma: no cover - never invoked here
        return False


def _minimal_gate(tmp_path):
    from server.safety.audit import AuditLog
    from server.safety.gate import SafetyGate

    from .test_deploy_transport import DeployableFakeConsole

    console = DeployableFakeConsole()
    audit = AuditLog(tmp_path / "gate-audit")
    return SafetyGate(console=console, audit=audit), console, audit
