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
    OSC_TEMPLATE_ASSETS,
    RESPONDER_ASSETS,
    InstallResult,
    ProvisioningError,
    bundled_osc_template_dir,
    bundled_responder_dir,
    install_osc_templates,
    install_responder,
    osc_bootstrap_guide,
    osc_template_status,
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
        assert self._slot_line(import_dir / "copilot_responder.lua").startswith("osc_slot = 2,")

    def test_reinstall_does_not_revert_the_site_slot(self, tmp_path):
        # The actual reported defect, as a regression test.
        import_dir = tmp_path / "plugins"
        install_responder(import_dir, osc_slot=2)
        install_responder(import_dir, osc_slot=2)
        assert self._slot_line(import_dir / "copilot_responder.lua").startswith("osc_slot = 2,")

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
        (source / "copilot_responder.lua").write_text("local CONFIG = {}\n", encoding="utf-8")
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


class TestBundledOscTemplates:
    def test_bundled_dir_contains_the_osc_template_assets(self):
        bundle = bundled_osc_template_dir()
        assert bundle.is_dir()
        for name in OSC_TEMPLATE_ASSETS:
            assert (bundle / name).is_file(), f"missing bundled OSC template: {name}"

    def test_asset_set_is_the_receive_and_send_row_pair(self):
        assert set(OSC_TEMPLATE_ASSETS) == {
            "copilot_osc_row1_receive.xml",
            "copilot_osc_row2_send.xml",
        }

    def test_frozen_bundle_dir_resolves_under_meipass(self, monkeypatch):
        import sys

        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "_MEIPASS", "/frozen/app", raising=False)
        resolved = bundled_osc_template_dir()
        assert resolved == Path("/frozen/app") / "console" / "osc"


class TestInstallOscTemplates:
    def test_install_copies_every_template_into_the_import_dir(self, tmp_path):
        import_dir = tmp_path / "osc"
        result = install_osc_templates(import_dir)
        assert set(result.installed) == set(OSC_TEMPLATE_ASSETS)
        assert result.import_dir == str(import_dir)
        for name in OSC_TEMPLATE_ASSETS:
            assert (import_dir / name).is_file()

    def test_install_raises_when_a_bundled_template_is_missing(self, tmp_path):
        empty_source = tmp_path / "empty"
        empty_source.mkdir()
        with pytest.raises(ProvisioningError):
            install_osc_templates(tmp_path / "osc", source_dir=empty_source)

    def test_install_from_an_explicit_source_dir(self, tmp_path):
        source = tmp_path / "src"
        source.mkdir()
        for name in OSC_TEMPLATE_ASSETS:
            (source / name).write_text('Port="1"', encoding="utf-8")
        import_dir = tmp_path / "osc"

        result = install_osc_templates(import_dir, source_dir=source)

        assert set(result.installed) == set(OSC_TEMPLATE_ASSETS)
        for name in OSC_TEMPLATE_ASSETS:
            assert (import_dir / name).read_text(encoding="utf-8") == 'Port="1"'


class TestOscTemplatePortsAreRenderedFromSettings:
    """Row 1 must track console_port (the send target OscBridge uses) and row 2
    must track receive_port (this app's bound feedback listener) — both are
    per-site settings, exactly like osc_slot is for the responder Lua."""

    def test_row1_port_renders_from_console_port(self, tmp_path):
        import_dir = tmp_path / "osc"
        install_osc_templates(import_dir, console_port=8123)
        text = (import_dir / "copilot_osc_row1_receive.xml").read_text(encoding="utf-8")
        assert 'Port="8123"' in text
        assert 'Prefix="copilot"' in text  # untouched by the substitution

    def test_row2_port_renders_from_receive_port(self, tmp_path):
        import_dir = tmp_path / "osc"
        install_osc_templates(import_dir, receive_port=9456)
        text = (import_dir / "copilot_osc_row2_send.xml").read_text(encoding="utf-8")
        assert 'Port="9456"' in text

    def test_reinstall_re_renders_to_the_new_ports(self, tmp_path):
        import_dir = tmp_path / "osc"
        install_osc_templates(import_dir, console_port=8000, receive_port=9000)
        install_osc_templates(import_dir, console_port=8001, receive_port=9001)
        row1 = (import_dir / "copilot_osc_row1_receive.xml").read_text(encoding="utf-8")
        row2 = (import_dir / "copilot_osc_row2_send.xml").read_text(encoding="utf-8")
        assert 'Port="8001"' in row1
        assert 'Port="9001"' in row2

    def test_omitting_a_port_keeps_the_bundled_default_byte_identical(self, tmp_path):
        import_dir = tmp_path / "osc"
        install_osc_templates(import_dir)
        row1 = (import_dir / "copilot_osc_row1_receive.xml").read_bytes()
        row2 = (import_dir / "copilot_osc_row2_send.xml").read_bytes()
        bundle = bundled_osc_template_dir()
        assert row1 == (bundle / "copilot_osc_row1_receive.xml").read_bytes()
        assert row2 == (bundle / "copilot_osc_row2_send.xml").read_bytes()

    def test_a_template_without_a_port_attribute_fails_loudly(self, tmp_path):
        source = tmp_path / "src"
        source.mkdir()
        (source / "copilot_osc_row1_receive.xml").write_text(
            "<GMA3><OSCData/></GMA3>", encoding="utf-8"
        )
        (source / "copilot_osc_row2_send.xml").write_text(
            "<GMA3><OSCData/></GMA3>", encoding="utf-8"
        )
        with pytest.raises(ProvisioningError):
            install_osc_templates(tmp_path / "osc", source_dir=source, console_port=8000)


class TestOscTemplateStatus:
    def test_status_is_false_before_install_true_after(self, tmp_path):
        import_dir = tmp_path / "osc"
        before = osc_template_status(import_dir)
        assert before == {name: False for name in OSC_TEMPLATE_ASSETS}

        install_osc_templates(import_dir)
        after = osc_template_status(import_dir)
        assert after == {name: True for name in OSC_TEMPLATE_ASSETS}


class TestOscBootstrapGuide:
    def test_guide_carries_both_ports_and_the_manual_interface_step(self):
        # The Interface/Enable toggles have no export/import path in onPC
        # 2.4.2 (AC-DEPLOY-011a lineage) — the guide must still name them so
        # the operator does not silently skip the step that actually broke
        # connectivity in the 2026-08-12 live session (en0 vs lo0).
        guide = osc_bootstrap_guide(8000, 9005)
        assert guide["console_port"] == 8000
        assert guide["receive_port"] == 9005
        joined = " ".join(guide["steps"])
        assert "8000" in joined
        assert "9005" in joined
        assert "lo0" in joined
        assert "Enable Output" in joined and "Enable Input" in joined

    def test_guide_sets_preferred_ip_before_the_interface_step(self):
        # Live 2026-09-18: with Preferred IP left at onPC's 10.0.0.0/8, picking
        # lo0 in the Interface list did not stick (stayed <None>), and once the
        # Mac's IP left 10.x onPC bound no OSC socket at all. Preferred IP must
        # admit 127.x first — the step order is the fix, so it is asserted.
        steps = osc_bootstrap_guide(8000, 9005)["steps"]
        preferred = next(i for i, s in enumerate(steps) if s.startswith("Preferred IP"))
        interface = next(i for i, s in enumerate(steps) if s.startswith("Interface") and "lo0" in s)
        assert "127.0.0.1/8" in steps[preferred]
        assert preferred < interface

    def test_guide_ends_by_saving_the_show(self):
        # OSC config lives in the show file — an unsaved fix reverts on reload.
        steps = osc_bootstrap_guide(8000, 9005)["steps"]
        assert any("저장" in s for s in steps)

    def test_guide_reflects_custom_ports(self):
        guide = osc_bootstrap_guide(8100, 9200)
        joined = " ".join(guide["steps"])
        assert "8100" in joined
        assert "9200" in joined


# ------------------------------------------------------------------ SAFETY: no OSC surface
#
# The interim M4 per-module OSC-send-surface guard for provisioning is
# CONSOLIDATED into the M10 AC-DEPLOY-014 ③ fail-closed allowlist scan
# (``server/tests/test_deploy_safety_invariants.py`` ::
# ``TestAcDeploy014OscSendSurfaceAllowlist``), which scans every server module —
# including server/deploy/provisioning.py — against one named send-surface allowlist.
