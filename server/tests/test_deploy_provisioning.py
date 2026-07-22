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
    read_installed_osc_slot,
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
            # Byte identity now holds only at the DEFAULT osc_slot: the Lua is
            # rendered from settings (site config would otherwise be reverted
            # on every re-provision), the XML is still copied verbatim.
            assert copied.read_bytes() == (bundled_responder_dir() / name).read_bytes()

    def test_install_creates_a_missing_import_dir(self, tmp_path):
        import_dir = tmp_path / "deep" / "nested" / "plugins"
        assert not import_dir.exists()
        install_responder(import_dir)
        assert import_dir.is_dir()

    def test_install_is_idempotent_reinstall_overwrites(self, tmp_path):
        import_dir = tmp_path / "plugins"
        install_responder(import_dir)
        # Corrupt one file, then re-install — the rendered bytes are restored.
        # At the default osc_slot the rendering is a no-op, so this is still
        # the bundled content.
        (import_dir / "copilot_responder.lua").write_text("stale", encoding="utf-8")
        install_responder(import_dir)
        restored = (import_dir / "copilot_responder.lua").read_bytes()
        assert restored == (bundled_responder_dir() / "copilot_responder.lua").read_bytes()


class TestOscSlotIsRenderedFromSettings:
    """Live 2026-07-22: this console replies on OSC row 2 (row 1 targets the
    broadcast address 192.168.0.255 and never reaches 127.0.0.1). The operator
    hand-edited the installed Lua, and `POST /api/provision/responder` then
    copied the bundle default back over it with no backup — killing the console
    link, and set to do so again on every re-provision.

    Rendering the slot from settings is what makes re-provisioning idempotent
    *with respect to site config* rather than hostile to it.
    """

    def _slot_line(self, path: Path) -> str:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("osc_slot"):
                return line.strip()
        raise AssertionError(f"no osc_slot line in {path}")

    def test_the_configured_slot_lands_in_the_installed_lua(self, tmp_path):
        import_dir = tmp_path / "plugins"
        install_responder(import_dir, osc_slot=2)
        assert self._slot_line(import_dir / "copilot_responder.lua").startswith(
            "osc_slot = 2,"
        )

    def test_reinstall_does_not_revert_the_site_slot(self, tmp_path):
        # The actual reported defect, as a regression test.
        import_dir = tmp_path / "plugins"
        install_responder(import_dir, osc_slot=2)
        install_responder(import_dir, osc_slot=2)
        assert self._slot_line(import_dir / "copilot_responder.lua").startswith(
            "osc_slot = 2,"
        )

    def test_omitting_the_slot_keeps_the_bundled_default(self, tmp_path):
        # Callers that do not care must get byte-identical behaviour.
        import_dir = tmp_path / "plugins"
        install_responder(import_dir)
        lua = (import_dir / "copilot_responder.lua").read_bytes()
        assert lua == (bundled_responder_dir() / "copilot_responder.lua").read_bytes()

    def test_the_xml_is_never_rendered(self, tmp_path):
        # Only the Lua carries CONFIG; the XML must stay a verbatim copy.
        import_dir = tmp_path / "plugins"
        install_responder(import_dir, osc_slot=7)
        assert (import_dir / "copilot_responder.xml").read_bytes() == (
            bundled_responder_dir() / "copilot_responder.xml"
        ).read_bytes()

    def test_the_rendered_lua_still_has_exactly_one_slot_assignment(self, tmp_path):
        # A substitution that matched too broadly would corrupt the send path,
        # where CONFIG.osc_slot is READ three times.
        import_dir = tmp_path / "plugins"
        install_responder(import_dir, osc_slot=3)
        text = (import_dir / "copilot_responder.lua").read_text(encoding="utf-8")
        assert len([ln for ln in text.splitlines() if ln.strip().startswith("osc_slot")]) == 1
        assert text.count("CONFIG.osc_slot") == 4  # 3 senders + the log line

    def test_the_installed_slot_can_be_read_back(self, tmp_path):
        # Reading the value back is what lets the caller notice that the file
        # on disk disagrees with the configured value BEFORE overwriting it.
        import_dir = tmp_path / "plugins"
        install_responder(import_dir, osc_slot=2)
        assert read_installed_osc_slot(import_dir) == 2

    def test_reading_an_absent_install_yields_none(self, tmp_path):
        assert read_installed_osc_slot(tmp_path / "nothing-here") is None

    def test_reading_a_file_without_the_anchor_yields_none(self, tmp_path):
        # "Unknown", not "default" — a caller must not be told the file says 1
        # when it says nothing readable at all.
        import_dir = tmp_path / "plugins"
        import_dir.mkdir()
        (import_dir / "copilot_responder.lua").write_text("-- nope\n", encoding="utf-8")
        assert read_installed_osc_slot(import_dir) is None

    def test_a_source_without_the_anchor_line_fails_loudly(self, tmp_path):
        # If the Lua is refactored so the anchor no longer matches, installing
        # a WRONG slot silently is far worse than refusing: the operator would
        # get a console that never replies and no signal as to why.
        source = tmp_path / "src"
        source.mkdir()
        (source / "copilot_responder.xml").write_text("<xml/>", encoding="utf-8")
        (source / "copilot_responder.lua").write_text(
            "local CONFIG = {}\n", encoding="utf-8"
        )
        with pytest.raises(ProvisioningError):
            install_responder(tmp_path / "plugins", osc_slot=2, source_dir=source)

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
#
# The interim M4 per-module OSC-send-surface guard for provisioning is
# CONSOLIDATED into the M10 AC-DEPLOY-014 ③ fail-closed allowlist scan
# (``server/tests/test_deploy_safety_invariants.py`` ::
# ``TestAcDeploy014OscSendSurfaceAllowlist``), which scans every server module —
# including server/deploy/provisioning.py — against one named send-surface allowlist.
