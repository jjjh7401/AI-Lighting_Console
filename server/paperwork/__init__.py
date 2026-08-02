"""Read-only paperwork generation: patch sheet, cue sheet, preset list.

Query-only (SPEC-COPILOT-PAPERWORK-001) — this package never imports the OSC
send surface or any command-execution port. See ``server/paperwork/data.py``
for the builders and ``server/paperwork/render.py`` for the self-contained
HTML renderers.
"""

from server.paperwork.data import (
    PatchRow,
    PatchSheet,
    Pool,
    PoolEntry,
    PoolListing,
    build_cue_sheet,
    build_patch_sheet,
    build_preset_list,
)
from server.paperwork.render import render_cue_sheet, render_patch_sheet, render_preset_list

__all__ = [
    "PatchRow",
    "PatchSheet",
    "Pool",
    "PoolEntry",
    "PoolListing",
    "build_cue_sheet",
    "build_patch_sheet",
    "build_preset_list",
    "render_cue_sheet",
    "render_patch_sheet",
    "render_preset_list",
]
