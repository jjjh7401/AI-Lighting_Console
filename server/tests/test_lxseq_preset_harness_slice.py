"""하네스 시트 자르기 — `--skip` 오프셋 (SPEC-COPILOT-LXSEQ-003 M4).

왜 이 검사가 있나: 매퍼는 이름 중복을 안 본다(점유 안 된 슬롯을 오름차순으로 고를
뿐이다). 그래서 「이미 들어간 행을 다시 안 쏜다」를 **자르기 단계**가 책임진다.
오프셋이 한 칸 어긋나면 이미 있는 프리셋이 다른 슬롯에 하나 더 생기고,
`Delete` 계열이 블랙리스트인지 안 쟀으므로 **되돌릴 방법이 없다.**
"""

from __future__ import annotations

from pathlib import Path

import pytest

from server.tools.lxseq_presets_e2e import _sliced

#: 정본 dim 시트. 발사 대상 판단이 이 파일의 **행 순서**에 걸려 있다.
CANONICAL_DIM = (
    Path(__file__).resolve().parents[2]
    / "src/Lighting_Designer/02_RIG팩/LXSEQ_RIG_01_ShowBase_r3.preset-dim.csv"
)

HEADER = "ID,Name,Level,Purpose"
ROWS = (
    "DIM.FULL,풀,100%,정점",
    "DIM.SHOW,쇼 하이,85%,일반",
    "DIM.MID,미드,60%,벌스",
)


@pytest.fixture
def sheet(tmp_path: Path) -> Path:
    path = tmp_path / "preset-dim.csv"
    path.write_text("\n".join((HEADER,) + ROWS) + "\n", encoding="utf-8")
    return path


def _lines(payload: bytes) -> list[str]:
    return payload.decode("utf-8").splitlines()


def test_skip_zero_keeps_the_old_behaviour(sheet: Path) -> None:
    """오프셋 없음 = 예전 그대로. 앞에서 N행."""
    assert _lines(_sliced(sheet, 1, skip=0)) == [HEADER, ROWS[0]]


def test_skip_one_yields_exactly_the_second_row(sheet: Path) -> None:
    """이번 발사가 걸려 있는 조항 — 1행을 건너뛰고 **2행 한 건만**."""
    assert _lines(_sliced(sheet, 1, skip=1)) == [HEADER, ROWS[1]]


def test_skip_never_drops_the_header(sheet: Path) -> None:
    """헤더가 빠지면 파서가 1행을 헤더로 먹어 조용히 한 건을 잃는다."""
    for skip in range(len(ROWS) + 2):
        assert _lines(_sliced(sheet, 1, skip=skip))[0] == HEADER


def test_skip_past_the_end_yields_no_rows(sheet: Path) -> None:
    """범위를 넘기면 0건이다 — 되감아 1행을 쏘지 않는다."""
    assert _lines(_sliced(sheet, 1, skip=99)) == [HEADER]


def test_limit_none_takes_the_rest_after_skip(sheet: Path) -> None:
    """상한 없음 + 오프셋 = 나머지 전부."""
    assert _lines(_sliced(sheet, None, skip=1)) == [HEADER, ROWS[1], ROWS[2]]


def test_canonical_sheet_row_two_is_dim_show() -> None:
    """`--skip 1` 이 DIM.SHOW 를 쏜다는 전제를 정본 시트에 대고 못박는다.

    시트 행 순서가 바뀌면 이 검사가 먼저 빨개진다 — 콘솔이 아니라.
    """
    second = _lines(_sliced(CANONICAL_DIM, 1, skip=1))
    assert len(second) == 2, second
    assert second[1].startswith("DIM.SHOW,"), second[1]
