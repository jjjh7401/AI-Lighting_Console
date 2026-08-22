"""Song/MA3 pipeline output-path guard (card t20).

Six sibling scripts wrote to a hardcoded `/home/claude/plugin-run/out/` path,
so they only ran on the machine that authored them. They now derive their
directory from `__file__` and accept an override, the same shape make_rig.py
uses (card t17).

The control is the point: these commits moved paths and nothing else, so every
regenerated artifact must match the committed one. Four are byte-comparable.
The xlsx is not — openpyxl embeds timestamps and its namespace serialization
differs across versions — so it is compared by cell value instead.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
RIG_DIR = REPO_ROOT / "src" / "Lighting_Designer"
SCRIPTS = RIG_DIR / "90_빌드파이프라인"
SONG_SRC = RIG_DIR / "03_곡파일_Sugar"
MA3_SRC = RIG_DIR / "04_grandMA3"
STEM = "LXSEQ_SAMPLE_01_Sugar_r3"

# artifact -> (committed dir, which generated dir it lands in)
BYTE_EQUAL = {
    f"{STEM}.cue-ex.csv": (SONG_SRC, "song"),
    f"{STEM}.timeline.html": (SONG_SRC, "song"),
    f"{STEM}.ma3.txt": (MA3_SRC, "ma3"),
    f"{STEM}.macros.xml": (MA3_SRC, "ma3"),
}


def _run(script, env):
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / script)],
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"{script}: {result.stderr}"
    return result


@pytest.fixture(scope="module")
def regenerated(tmp_path_factory):
    """Rebuild the song and MA3 artifacts into throwaway directories."""
    song = tmp_path_factory.mktemp("song")
    ma3 = tmp_path_factory.mktemp("ma3")
    env = {
        "LXSEQ_SONG_OUT": str(song),
        "LXSEQ_MA3_OUT": str(ma3),
        "PATH": "/usr/bin:/bin",
    }
    # make_exec reads the workbook make_xlsx writes, so order matters here.
    for script in ("make_xlsx.py", "make_exec.py", "make_timeline.py", "make_ma3.py"):
        _run(script, env)
    return {"song": song, "ma3": ma3, "env": env}


@pytest.mark.parametrize("artifact", sorted(BYTE_EQUAL))
def test_artifact_is_byte_identical(regenerated, artifact):
    committed_dir, which = BYTE_EQUAL[artifact]
    generated = regenerated[which] / artifact
    assert generated.exists(), f"{artifact} was not regenerated"
    assert generated.read_bytes() == (committed_dir / artifact).read_bytes()


def test_workbook_matches_by_cell_value(regenerated):
    """The xlsx is not byte-reproducible; its cell values still must match."""
    openpyxl = pytest.importorskip("openpyxl")
    name = f"{STEM}.xlsx"
    got = openpyxl.load_workbook(regenerated["song"] / name)
    want = openpyxl.load_workbook(SONG_SRC / name)
    assert got.sheetnames == want.sheetnames
    for sheet in want.sheetnames:
        rows_got = list(got[sheet].iter_rows(values_only=True))
        rows_want = list(want[sheet].iter_rows(values_only=True))
        assert rows_got == rows_want, f"{sheet} drifted"


@pytest.mark.parametrize("script", ["validate.py", "validate_ma3.py"])
def test_validators_read_the_override(regenerated, script):
    """Readers must honour the override too, not just the writers."""
    _run(script, regenerated["env"])


def test_no_hardcoded_output_paths():
    """The defect family this card drained: one site left is the whole bug back."""
    offenders = [
        p.name for p in SCRIPTS.glob("*.py")
        if "/home/claude/" in p.read_text(encoding="utf-8")
    ]
    assert offenders == []
