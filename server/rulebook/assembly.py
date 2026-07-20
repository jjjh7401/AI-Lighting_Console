"""Deterministic assembly of the MA3 rulebook fixed prefix (REQ-MVP-007/008/042).

The rulebook is the FIXED system-prompt prefix: MA3 command grammar, an object
model summary, and the Korean field-lighting term dictionary axis. It is
assembled from static markdown assets under ``assets/v<version>/`` in sorted
filename order — nothing else. No timestamps, session IDs, or any per-turn
variable value may enter this string: providers cache the prefix byte-for-byte
(Anthropic prompt caching / Gemini context caching, REQ-MVP-041), and a single
changed byte invalidates the whole cache (AC-MVP-014 part 1 pins byte identity).

Versioning: one asset directory per supported MA3 release (plan.md section A-2
pins grandMA3 onPC 2.4.2 for Phase 1). Grammar-coverage QUALITY is measured at
M6 against the error-rate corpus; this module only guarantees structure and
byte stability.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from server.resources import resource_base

# grandMA3 onPC version pinned by plan.md section A-2 (Phase 0 environment).
RULEBOOK_VERSION = "2.4.2"

_KOREAN_TERMS_FILENAME = "20_korean_terms.md"


def _assets_dir() -> Path:
    """Resolve the rulebook asset root (dev root or frozen ``_MEIPASS``).

    Routes through :func:`server.resources.resource_base` for frozen-bundle
    consistency (research §A.4 — lower severity than serve/config since the
    mirrored ``--add-data`` tree resolves via ``__file__`` too, but unified here).
    """
    return resource_base() / "server" / "rulebook" / "assets"


class RulebookError(RuntimeError):
    """Raised when rulebook assets are missing or malformed."""


@dataclass(frozen=True)
class KoreanTermEntry:
    """One Korean field-lighting term mapped to MA3 vocabulary (REQ-MVP-042)."""

    korean: str
    ma3_vocabulary: str
    note: str = ""


def rulebook_dir(version: str = RULEBOOK_VERSION) -> Path:
    """Return the asset directory for one rulebook version."""
    directory = _assets_dir() / f"v{version}"
    if not directory.is_dir():
        raise RulebookError(f"no rulebook assets for MA3 version {version!r}: {directory}")
    return directory


def rulebook_asset_files(version: str = RULEBOOK_VERSION) -> list[Path]:
    """Static asset files in the deterministic (sorted-filename) assembly order."""
    files = sorted(path for path in rulebook_dir(version).iterdir() if path.suffix == ".md")
    if not files:
        raise RulebookError(f"rulebook asset directory for {version!r} contains no .md files")
    return files


# @MX:ANCHOR: [AUTO] the fixed system-prompt prefix is built ONLY here — both provider
#   adapters, the orchestrator, and the AC-MVP-014/028 tests all pin this output
# @MX:REASON: byte identity of this string is the provider cache-prefix contract
#   (REQ-MVP-008); a second assembly path would silently fork the cached prefix
def assemble_prefix(version: str = RULEBOOK_VERSION) -> str:
    """Assemble the fixed prefix from static assets — deterministic, byte-stable."""
    parts = [path.read_text(encoding="utf-8").strip() for path in rulebook_asset_files(version)]
    return "\n\n".join(parts) + "\n"


def korean_term_entries(version: str = RULEBOOK_VERSION) -> list[KoreanTermEntry]:
    """Parse the Korean term dictionary axis table (AC-MVP-028 assert surface).

    The dictionary axis lives in ``20_korean_terms.md`` as a markdown table:
    ``| korean | ma3 vocabulary | note |``. Header and separator rows are
    skipped; every data row becomes one :class:`KoreanTermEntry`.
    """
    source = rulebook_dir(version) / _KOREAN_TERMS_FILENAME
    if not source.is_file():
        raise RulebookError(f"korean term dictionary asset missing: {source}")
    entries: list[KoreanTermEntry] = []
    for line in source.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) < 2:
            continue
        if cells[0] in ("한국어 용어", "") or set(cells[0]) <= {"-", ":", " "}:
            continue  # header / separator rows
        entries.append(
            KoreanTermEntry(
                korean=cells[0],
                ma3_vocabulary=cells[1],
                note=cells[2] if len(cells) > 2 else "",
            )
        )
    return entries
