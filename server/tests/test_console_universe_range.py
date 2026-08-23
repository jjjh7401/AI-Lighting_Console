"""Console-setup universe range must cover the rig that is actually patched (card t25).

The console setup table is what an operator configures the desk from. It said
`sACN · Universe 1–4` while the patch CSV placed 26 of 86 fixtures on universe 5 —
follow the table and 30% of the rig receives no DMX, silently.

The guard computes the upper bound from the CSV rather than pinning a constant, so
the rig can grow a universe without this test going quietly stale.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
RIG_DIR = REPO_ROOT / "src" / "Lighting_Designer"
PATCH_CSV = RIG_DIR / "02_RIG팩" / "LXSEQ_RIG_01_ShowBase_r3.patch.csv"
SCRIPTS = RIG_DIR / "90_빌드파이프라인"

#: `sACN · Universe 1–5 (+U6 예비) · …` — captures the range end (5), not the spare.
_RANGE = re.compile(r"Universe\s*(\d+)\s*[–-]\s*(\d+)")


def _max_universe_in_use() -> int:
    """Highest universe the patch CSV actually places a fixture on."""
    with PATCH_CSV.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows, "patch CSV is empty — the guard would pass vacuously"
    return max(int(row["Universe"]) for row in rows)


def _declared_ranges() -> list[tuple[str, int, int]]:
    """Every `Universe <a>–<b>` the rig data declares, with its source line."""
    text = (SCRIPTS / "rig_data.py").read_text(encoding="utf-8")
    found = []
    for line in text.splitlines():
        match = _RANGE.search(line)
        if match:
            found.append((line.strip(), int(match.group(1)), int(match.group(2))))
    return found


def test_the_csv_actually_uses_more_than_one_universe():
    """Guard the guard: a single-universe rig would make the check vacuous."""
    with PATCH_CSV.open(encoding="utf-8-sig", newline="") as handle:
        universes = {int(row["Universe"]) for row in csv.DictReader(handle)}
    assert len(universes) > 1, universes


def test_rig_data_declares_a_universe_range():
    """A missing declaration must fail loudly, not pass by absence."""
    assert _declared_ranges(), "no `Universe a–b` found in rig_data.py"


@pytest.mark.parametrize("index", range(4))
def test_every_declared_range_covers_the_patched_rig(index):
    """Each declared range must reach the highest universe actually patched."""
    ranges = _declared_ranges()
    if index >= len(ranges):
        pytest.skip(f"only {len(ranges)} declaration(s)")
    line, low, high = ranges[index]
    in_use = _max_universe_in_use()
    assert low <= 1, f"range starts above universe 1: {line}"
    assert high >= in_use, (
        f"declared Universe {low}-{high} but the CSV patches up to {in_use} — "
        f"an operator following this table leaves universe(s) dark: {line}"
    )
