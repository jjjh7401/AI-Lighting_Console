"""CopilotResponder provisioning (M4 — REQ-DEPLOY-009/010/011, AC-DEPLOY-006/007).

Filesystem-only provisioning: the bundled responder plugin files are copied into
the operator's onPC plugin-import directory, and a guide describes the onPC-load
steps + OSC-output-port setting. NO OSC/console-send happens in this layer — the
source-scan guard at the bottom enforces that (AC-DEPLOY-014 ③ / SAFETY-1).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from server.deploy.provisioning import (
    RESPONDER_ASSETS,
    InstallResult,
    ProvisioningError,
    bundled_responder_dir,
    install_responder,
    responder_guide,
    responder_status,
)


class TestBundledAssets:
    def test_bundled_dir_contains_the_responder_assets(self):
        # AC-DEPLOY-006 ①: the deploy artifact bundles the responder plugin
        # (copilot_responder.lua + native import XML).
        bundle = bundled_responder_dir()
        assert bundle.is_dir()
        for name in RESPONDER_ASSETS:
            assert (bundle / name).is_file(), f"missing bundled asset: {name}"

    def test_asset_set_is_the_lua_component_plus_native_import_xml(self):
        # onPC needs the native import XML together with the Lua component.
        assert set(RESPONDER_ASSETS) == {"copilot_responder.xml", "copilot_responder.lua"}

    def test_frozen_bundle_dir_resolves_under_meipass(self, monkeypatch):
        # FEAS-1 heads-up: in a frozen PyInstaller bundle the assets resolve under
        # sys._MEIPASS/console/lua (dev resolves under the repo). The resolver was
        # generalised at M6 into the shared server.resources.resource_base, which
        # gates on sys.frozen (research §A.4) — so a bundle sets BOTH sys.frozen
        # and sys._MEIPASS.
        import sys

        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "_MEIPASS", "/frozen/app", raising=False)
        resolved = bundled_responder_dir()
        assert resolved == Path("/frozen/app") / "console" / "lua"


class TestInstallResponder:
    def test_install_copies_every_asset_into_the_import_dir(self, tmp_path):
        # AC-DEPLOY-006 ②: install → the configured import directory receives the
        # plugin files (temp-dir target).
        import_dir = tmp_path / "plugins"
        result = install_responder(import_dir)

        assert isinstance(result, InstallResult)
        assert set(result.installed) == set(RESPONDER_ASSETS)
        for name in RESPONDER_ASSETS:
            copied = import_dir / name
            assert copied.is_file()
            # Bytes match the bundled source verbatim.
            assert copied.read_bytes() == (bundled_responder_dir() / name).read_bytes()

    def test_install_creates_a_missing_import_dir(self, tmp_path):
        import_dir = tmp_path / "deep" / "nested" / "plugins"
        assert not import_dir.exists()
        install_responder(import_dir)
        assert import_dir.is_dir()

    def test_install_is_idempotent_reinstall_overwrites(self, tmp_path):
        import_dir = tmp_path / "plugins"
        install_responder(import_dir)
        # Corrupt one file, then re-install — the bundled bytes are restored.
        (import_dir / "copilot_responder.lua").write_text("stale", encoding="utf-8")
        install_responder(import_dir)
        restored = (import_dir / "copilot_responder.lua").read_bytes()
        assert restored == (bundled_responder_dir() / "copilot_responder.lua").read_bytes()

    def test_install_from_an_explicit_source_dir(self, tmp_path):
        # source_dir override lets the module be tested in full isolation.
        source = tmp_path / "src"
        source.mkdir()
        for name in RESPONDER_ASSETS:
            (source / name).write_text(f"content:{name}", encoding="utf-8")
        import_dir = tmp_path / "plugins"

        result = install_responder(import_dir, source_dir=source)

        assert set(result.installed) == set(RESPONDER_ASSETS)
        assert (import_dir / "copilot_responder.lua").read_text(encoding="utf-8") == (
            "content:copilot_responder.lua"
        )

    def test_install_raises_when_a_bundled_asset_is_missing(self, tmp_path):
        empty_source = tmp_path / "empty"
        empty_source.mkdir()
        with pytest.raises(ProvisioningError):
            install_responder(tmp_path / "plugins", source_dir=empty_source)


class TestResponderStatus:
    def test_status_is_false_before_install_true_after(self, tmp_path):
        import_dir = tmp_path / "plugins"
        before = responder_status(import_dir)
        assert before == {name: False for name in RESPONDER_ASSETS}

        install_responder(import_dir)
        after = responder_status(import_dir)
        assert after == {name: True for name in RESPONDER_ASSETS}


class TestResponderGuide:
    def test_guide_carries_the_receive_port_and_onpc_load_steps(self):
        # AC-DEPLOY-007: the guide surfaces onPC-load steps + the instruction to
        # set onPC OSC output to the app's feedback receive port.
        guide = responder_guide(9000)
        assert guide["receive_port"] == 9000
        assert isinstance(guide["steps"], list)
        assert len(guide["steps"]) >= 2
        joined = " ".join(guide["steps"])
        # The port must appear in the OSC-output instruction, and the guide must
        # mention loading the plugin in onPC.
        assert "9000" in joined
        assert "OSC" in joined

    def test_guide_reflects_a_custom_receive_port(self):
        guide = responder_guide(9123)
        assert guide["receive_port"] == 9123
        assert "9123" in " ".join(guide["steps"])


# ------------------------------------------------------------------ SAFETY: no OSC surface


class TestNoOscSendSurface:
    def test_provisioning_module_has_no_console_send_path(self):
        # AC-DEPLOY-014 ③ / SAFETY-1 + E6': provisioning is filesystem-only. A
        # static source scan proves it never reaches a raw socket / OSC module /
        # the safety gate. The ONLY console command provisioning MAY issue (Import
        # Plugin, via the deploy pipeline) lives in server.safety and transits the
        # single gate + audit (REQ-DEPLOY-011a) — it is NOT in this module.
        import server.deploy.provisioning as module

        source = Path(module.__file__).read_text(encoding="utf-8")
        forbidden = (
            "socket.socket",
            "UdpSocket",
            "pythonosc",
            "python_osc",
            "SafetyGate",
            "send_command",
            "OscBridge",
            "server.bridge",
            "server.safety",
        )
        offenders = [token for token in forbidden if token in source]
        assert offenders == [], f"provisioning must not touch the OSC send surface: {offenders}"
