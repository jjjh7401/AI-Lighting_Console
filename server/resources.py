"""Frozen-aware resource-base resolver (M6 — FEAS-1 / research §A.4).

Every bundled-asset path in the app (built UI, seed config, rulebook assets,
responder plugin) routes through :func:`resource_base` so it resolves correctly
in BOTH a dev checkout and a frozen PyInstaller bundle:

* **dev checkout** -> the project root (the directory holding ``server/``,
  ``ui/``, ``config/``, ``console/``).
* **frozen bundle** -> ``sys._MEIPASS``. PyInstaller sets ``sys.frozen=True`` and
  ``sys._MEIPASS`` for BOTH onedir (``_MEIPASS`` = the ``_internal`` folder) and
  onefile (``_MEIPASS`` = a temp extraction dir), so one resolver covers both.

This is the single generalisation of the ``sys._MEIPASS`` pattern that
``server.deploy.provisioning`` first introduced (M4); every frozen-sensitive
path now shares this one helper instead of forking a divergent resolver.

⚠️ M6 ``--add-data`` obligation (research §A.5): the PyInstaller onedir spec MUST
mirror the asset trees into the bundle so the resolved paths exist — ``ui/dist``,
``config/provider.toml``, ``console/lua``, ``server/rulebook/assets``.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Dev-mode project root: server/resources.py -> parents[1] is the repo root
# (the same root the legacy `Path(__file__).resolve().parents[2]` climbs in
# server/web/serve.py and server/llm/config.py resolved to).
_DEV_PROJECT_ROOT = Path(__file__).resolve().parents[1]


# @MX:ANCHOR: [AUTO] the sole frozen/dev resource-base resolver — serve.py
#   (ui/dist), config.py (provider.toml), rulebook assembly (assets), and
#   deploy provisioning (console/lua) all route asset paths through here.
# @MX:REASON: FEAS-1 — a frozen PyInstaller bundle has no dev project root; a
#   path that climbs to it (parents[2]) breaks in the bundle. A second, divergent
#   resolver would silently fork frozen resolution and reintroduce that break.
# @MX:SPEC: SPEC-COPILOT-DEPLOY-001
def resource_base() -> Path:
    """Return the base directory for bundled resources (dev root or ``_MEIPASS``).

    Frozen bundle -> ``Path(sys._MEIPASS)``; dev checkout -> the project root.
    Discriminates on ``getattr(sys, "frozen", False)`` only (research §A.4) — a
    stray ``sys._MEIPASS`` without ``sys.frozen`` does NOT flip to bundle mode.
    """
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]  # set by PyInstaller
    return _DEV_PROJECT_ROOT
