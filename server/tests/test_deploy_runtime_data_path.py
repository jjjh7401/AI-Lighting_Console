"""M10 Part A — runtime-writable data-path fix (AC-DEPLOY-014 prerequisite).

The MVP audit log defaults its storage under ``server/audit_logs`` via
``Path(__file__).resolve().parents[1]`` (:data:`server.safety.audit.DEFAULT_AUDIT_DIR`).
Inside a frozen PyInstaller bundle that path resolves under ``sys._MEIPASS`` —
a READ-ONLY tree — so a real gate-executed command in the packaged ``.app``
cannot write its audit entry, and the AC-MVP-006 1:1 send<->audit completeness
invariant would silently break.

This module (a) reproduces that failure against a read-only bundle-like dir and
(b) pins the fix: when frozen the audit_logs directory routes under the
OS-standard user-writable DATA dir, while dev behaviour stays byte-identical.
The MVP write semantics (``AuditLog.record`` / ``_purge``) are NOT touched by
the fix — only the directory the serve path hands to ``AuditLog`` changes.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from server.deploy.settings import APP_NAME, _resolve_data_dir, user_data_dir
from server.safety.audit import DEFAULT_AUDIT_DIR, AuditLog
from server.safety.bootstrap import resolve_runtime_audit_dir

_IS_ROOT = hasattr(os, "geteuid") and os.geteuid() == 0


class TestReproduceReadOnlyBundle:
    """Reproduce the packaged-app failure: audit_logs under a read-only tree."""

    @pytest.mark.skipif(_IS_ROOT, reason="root bypasses directory-mode permissions")
    def test_record_into_readonly_bundle_dir_fails(self, tmp_path):
        """A read-only ``_MEIPASS/server`` cannot host the audit_logs the app writes.

        Simulates the frozen bundle: ``server/`` inside the extraction root is
        read-only, so ``AuditLog(<read-only>/server/audit_logs)`` cannot create
        or append to its daily file. This is the exact failure a gate-executed
        command hits in ``dist/GrandMA3 Copilot.app`` today.
        """
        meipass_server = tmp_path / "bundle" / "server"
        meipass_server.mkdir(parents=True)
        audit_dir = meipass_server / "audit_logs"  # == DEFAULT_AUDIT_DIR shape in-bundle
        meipass_server.chmod(0o500)  # read + execute, NO write (read-only bundle)
        try:
            with pytest.raises(OSError):
                # __init__ mkdir fails (dir absent) OR, if it existed, record() append fails.
                log = AuditLog(audit_dir)
                log.log_executed("Store 1", kind="command")
        finally:
            meipass_server.chmod(0o700)  # restore so tmp_path teardown can clean up


class TestUserDataDir:
    """OS-standard per-user DATA dir resolution — mirrors ``_resolve_config_dir``.

    Audit logs are runtime DATA, not config: macOS puts both under Application
    Support, but POSIX/Windows split data (``$XDG_DATA_HOME`` / ``%LOCALAPPDATA%``)
    from config (``$XDG_CONFIG_HOME`` / ``%APPDATA%``).
    """

    def test_macos_uses_application_support(self):
        home = Path("/Users/op")
        got = _resolve_data_dir(APP_NAME, platform="darwin", os_name="posix", environ={}, home=home)
        assert got == home / "Library" / "Application Support" / "GrandMA3 Copilot"

    def test_windows_uses_localappdata_env(self):
        got = _resolve_data_dir(
            APP_NAME,
            platform="win32",
            os_name="nt",
            environ={"LOCALAPPDATA": r"C:\Users\op\AppData\Local"},
            home=Path(r"C:\Users\op"),
        )
        assert got == Path(r"C:\Users\op\AppData\Local") / "GrandMA3 Copilot"

    def test_windows_without_localappdata_falls_back_to_home_local(self):
        home = Path(r"C:\Users\op")
        got = _resolve_data_dir(APP_NAME, platform="win32", os_name="nt", environ={}, home=home)
        assert got == home / "AppData" / "Local" / "GrandMA3 Copilot"

    def test_linux_honours_xdg_data_home(self):
        got = _resolve_data_dir(
            APP_NAME,
            platform="linux",
            os_name="posix",
            environ={"XDG_DATA_HOME": "/home/op/.data-alt"},
            home=Path("/home/op"),
        )
        assert got == Path("/home/op/.data-alt") / "GrandMA3 Copilot"

    def test_linux_defaults_to_dot_local_share(self):
        home = Path("/home/op")
        got = _resolve_data_dir(APP_NAME, platform="linux", os_name="posix", environ={}, home=home)
        assert got == home / ".local" / "share" / "GrandMA3 Copilot"

    def test_public_helper_returns_a_real_app_path(self):
        directory = user_data_dir()
        assert directory.name == "GrandMA3 Copilot"


class TestResolveRuntimeAuditDir:
    """Frozen-aware audit-dir selection: dev byte-identical, frozen user-writable."""

    def test_dev_is_byte_identical(self):
        """Not frozen -> the exact MVP dev default (no behaviour change)."""
        assert resolve_runtime_audit_dir(frozen=False) == DEFAULT_AUDIT_DIR

    def test_default_flag_reads_sys_frozen(self, monkeypatch):
        """Absent an explicit flag, the resolver reads ``sys.frozen`` (dev = False)."""
        monkeypatch.delattr("sys.frozen", raising=False)
        assert resolve_runtime_audit_dir() == DEFAULT_AUDIT_DIR

    def test_frozen_routes_under_user_data_dir_not_meipass(self, monkeypatch, tmp_path):
        """Frozen -> audit_logs under the user DATA dir, never under ``_MEIPASS``."""
        fake_meipass = tmp_path / "meipass_readonly"
        monkeypatch.setattr("sys._MEIPASS", str(fake_meipass), raising=False)
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "home"))

        got = resolve_runtime_audit_dir(frozen=True)

        assert got == user_data_dir() / "audit_logs"
        assert got.name == "audit_logs"
        # The load-bearing invariant: the writable audit dir is NOT inside the bundle.
        assert fake_meipass not in got.parents
        assert str(fake_meipass) not in str(got)

    def test_frozen_record_roundtrip_succeeds(self, monkeypatch, tmp_path):
        """The frozen-resolved dir is genuinely writable — a record() lands there."""
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "home"))
        audit_dir = resolve_runtime_audit_dir(frozen=True)

        log = AuditLog(audit_dir)
        log.log_executed("Store 1", kind="command")

        events = list(log.iter_events())
        assert len(events) == 1
        assert events[0]["event"] == "executed"
        assert events[0]["command"] == "Store 1"
        assert audit_dir.is_dir()
        assert (tmp_path / "home") in audit_dir.parents
