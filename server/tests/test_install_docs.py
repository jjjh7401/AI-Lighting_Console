"""Open-install path verification (M6 — AC-MVP-029 ②③ automated half, REQ-MVP-043).

② automated: dependency version-pin files (lockfiles) exist + the install
documentation exists and covers BOTH the server and the UI from scratch.
③ automated slice: the install documentation references no closed resource
(beta signup / manually distributed bundle) — the full document review and the
macOS clean-machine boot (①) remain the M6b semi-automated half.
"""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _readme() -> str:
    return (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")


class TestVersionPins:
    def test_python_dependency_lockfile_exists(self):
        # AC-MVP-029 ②: server dependencies are version-pinned (uv.lock).
        assert (PROJECT_ROOT / "uv.lock").is_file()

    def test_ui_dependency_lockfile_exists(self):
        # AC-MVP-029 ②: UI dependencies are version-pinned (package-lock.json).
        assert (PROJECT_ROOT / "ui" / "package-lock.json").is_file()

    def test_python_version_is_pinned(self):
        pin = (PROJECT_ROOT / ".python-version").read_text(encoding="utf-8").strip()
        assert pin.startswith("3.")


class TestInstallDocumentation:
    def test_install_documentation_exists_and_covers_server_and_ui(self):
        # AC-MVP-029 ②: a from-scratch install path is documented for BOTH
        # halves — server (uv sync) and chat UI (npm install + build).
        readme = _readme()
        assert "uv sync" in readme
        assert "npm install" in readme
        assert "npm run build" in readme
        # Boot instructions for the server (onPC-less boot included).
        assert "python -m server.web" in readme

    def test_console_side_responder_install_is_documented(self):
        # The console-side Lua responder (M2) needs its own install step.
        readme = _readme()
        assert "responder" in readme.lower()

    def test_install_path_references_no_closed_resource(self):
        # AC-MVP-029 ③ (automated slice): no beta signup, no manual bundle,
        # no invitation-gated download anywhere in the install documentation.
        readme = _readme().lower()
        markers = ("beta signup", "베타 신청", "manual bundle", "수동 배포 번들", "invite-only")
        for marker in markers:
            assert marker not in readme, f"closed-resource marker found: {marker!r}"
