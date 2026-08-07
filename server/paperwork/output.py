"""Frozen-aware write location for paperwork HTML files (T-J).

Mirrors ``server.safety.bootstrap.resolve_runtime_audit_dir``'s frozen-aware
split without importing that module — ``server.safety.bootstrap`` composes the
whole production console stack (OSC bridge, console link, gate), and pulling
it in here just to resolve a directory would give the read-only paperwork
package a live import of the OSC send surface for no reason
(``test_paperwork_boundary.py`` forbids exactly that). This module repeats the
same two-line frozen check against the same
``server.deploy.settings.user_data_dir`` helper instead.

Every file is written under a DETERMINISTIC, overwrite-on-write basename — a
show's patch sheet is ``patch_sheet.html`` every time, never a per-run
timestamped file, so re-running a build tool never litters the directory.
"""

from __future__ import annotations

import sys
from pathlib import Path

from server.deploy.settings import user_data_dir

# Dev-checkout default: sibling to server/paperwork/, matching the
# DEFAULT_AUDIT_DIR idiom (server/safety/audit.py) of one directory per
# runtime-output kind under the repo root.
DEFAULT_PAPERWORK_DIR = Path(__file__).resolve().parents[1] / "paperwork_output"


def resolve_paperwork_dir(*, frozen: bool | None = None) -> Path:
    """Where the running app writes paperwork HTML (frozen-aware).

    ``frozen`` defaults to ``sys.frozen`` (set by PyInstaller). A frozen
    bundle's own tree is read-only, so it routes under the OS-standard
    per-user DATA dir — the exact split
    ``server.safety.bootstrap.resolve_runtime_audit_dir`` makes for audit
    logs; a dev checkout keeps the repo-relative default unchanged.
    """
    if frozen is None:
        frozen = bool(getattr(sys, "frozen", False))
    if frozen:
        return user_data_dir() / "paperwork"
    return DEFAULT_PAPERWORK_DIR


def resolve_handover_dir(*, frozen: bool | None = None) -> Path:
    """Where the running app writes the handover pack (frozen-aware).

    A ``handover/`` subdirectory of :func:`resolve_paperwork_dir` — same
    frozen/dev split, one level deeper so the pack's four files (index +
    three sheets) sit together instead of mixed in with paperwork any other
    tool writes directly under the paperwork dir.
    """
    return resolve_paperwork_dir(frozen=frozen) / "handover"


def write_paperwork_html(filename: str, html: str, *, directory: Path | None = None) -> Path:
    """Write ``html`` to ``filename`` under the resolved paperwork dir.

    Overwrites unconditionally — ``filename`` is a plain deterministic
    basename (e.g. ``"patch_sheet.html"``), never caller-composed from model
    or operator text, so a rebuild replaces the same file instead of the
    directory accumulating one file per run.
    """
    target_dir = directory if directory is not None else resolve_paperwork_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / filename
    path.write_text(html, encoding="utf-8")
    return path


__all__ = [
    "DEFAULT_PAPERWORK_DIR",
    "resolve_paperwork_dir",
    "resolve_handover_dir",
    "write_paperwork_html",
]
