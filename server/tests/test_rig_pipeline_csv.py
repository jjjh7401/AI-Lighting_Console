"""RIG pipeline CSV export guard (card t17).

`make_rig.py` generates the machine-readable CSVs that LXSEQ-002/003/004 will
consume. Until this file existed the pipeline sat outside the pytest collection
range, so a full-suite pass said nothing about it — the suite count was
identical with and without the export working.

Three things are pinned here:

1. Row counts per sheet. A silently truncated export still writes a valid file.
2. The utf-8-sig BOM. Every existing machine CSV in this repo carries it
   (patch.csv, cue-ex.csv were measured); a consumer reading without it gets a
   corrupted first header cell.
3. A control: the regenerated patch.csv must stay byte-identical to the
   committed one. This is the assertion that catches a refactor changing
   existing output while the new exports look fine.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
RIG_DIR = REPO_ROOT / "src" / "Lighting_Designer"
SCRIPT = RIG_DIR / "90_빌드파이프라인" / "make_rig.py"
COMMITTED_PATCH = RIG_DIR / "02_RIG팩" / "LXSEQ_RIG_01_ShowBase_r3.patch.csv"
STEM = "LXSEQ_RIG_01_ShowBase_r3"
BOM = bytes([0xEF, 0xBB, 0xBF])

# suffix -> data row count (header excluded). Measured from rig_data.py.
EXPECTED_ROWS = {
    "patch": 86,
    "group": 18,
    "preset-dim": 6,
    "preset-col": 8,
    "preset-pos": 8,
    "preset-bm": 5,
    "fx": 8,
}


@pytest.fixture(scope="module")
def generated(tmp_path_factory):
    """Run make_rig.py into a throwaway directory and return that path."""
    out = tmp_path_factory.mktemp("rig_out")
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        env={"LXSEQ_RIG_OUT": str(out), "PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return out


@pytest.mark.parametrize("suffix,rows", sorted(EXPECTED_ROWS.items()))
def test_csv_has_expected_row_count(generated, suffix, rows):
    path = generated / f"{STEM}.{suffix}.csv"
    assert path.exists(), f"{suffix}.csv was not generated"
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    assert len(lines) - 1 == rows, f"{suffix}: header + {rows} rows expected"


@pytest.mark.parametrize("suffix", sorted(EXPECTED_ROWS))
def test_csv_is_utf8_sig(generated, suffix):
    raw = (generated / f"{STEM}.{suffix}.csv").read_bytes()
    assert raw.startswith(BOM), f"{suffix}.csv lost its utf-8-sig BOM"


def test_patch_csv_is_unchanged(generated):
    """Control: existing output must survive the export refactor byte for byte."""
    assert (generated / f"{STEM}.patch.csv").read_bytes() == COMMITTED_PATCH.read_bytes()
