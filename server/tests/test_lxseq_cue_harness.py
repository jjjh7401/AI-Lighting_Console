"""큐 하네스의 인구조사·큐 단위 자르기·유출 탐지 검사.

이 파일이 못 박는 것은 하나다: **`Note` 텍스트는 영상 콜 판별기가 될 수 없다.**
다음 사람이 「`Note` 로 매칭하면 되지 않나」를 다시 생각하지 못하도록, 왜 안 되는지가
검사에 박혀 있어야 한다 — 실측으로 6 중 5만 걸리고, 5/6 은 그럴듯해서 눈에 안 띈다.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from server.tools.lxseq_cues_e2e import (
    VIDEO_CALL_GROUP,
    census,
    leaked_commands,
    read_rows,
    slice_by_cue,
)

CUE_CSV = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "Lighting_Designer"
    / "03_곡파일_Sugar"
    / "LXSEQ_SAMPLE_01_Sugar_r3.cue-ex.csv"
)


@pytest.fixture(scope="module")
def sheet() -> dict:
    return census(read_rows(CUE_CSV))


def test_census_splits_console_rows_from_video_calls(sheet: dict) -> None:
    """89 를 하나로 뭉개지 않는다 — 콘솔 대상과 영상 콜을 나란히 센다."""
    assert sheet["total_rows"] == 89
    assert sheet["cue_count"] == 18
    assert sheet["video_call_rows"] == 6
    assert sheet["console_rows"] == 83
    assert sheet["console_rows"] + sheet["video_call_rows"] == sheet["total_rows"]


def test_note_text_is_not_a_discriminator(sheet: dict) -> None:
    """🔴 이 검사가 이 파일의 이유다.

    `Note` 로 매칭하면 6 행 중 5 행만 걸린다. 남는 1 행(Q170 「영상 페이드아웃 동기」)은
    콘솔 명령으로 새고, 집계는 5/6 이라 그럴듯해 보여 눈에 띄지 않는다. 유출 사고가
    났던 자리에서 가장 안 보이는 형태로 새는 것이다.

    그러므로 판별기는 그룹명 하나여야 한다.
    """
    assert sheet["note_pattern_hits"] == 5
    assert sheet["note_pattern_would_miss"] == 1
    assert sheet["note_pattern_hits"] < sheet["video_call_rows"], (
        "Note 패턴이 그룹 판별과 같은 수를 잡으면 이 검사의 전제가 바뀐 것이다 — "
        "시트가 바뀌었는지 확인하고, 판별기를 Note 로 되돌리지는 마라."
    )


def test_group_discriminator_catches_every_video_row() -> None:
    """그룹명 판별은 전수다 — Note 가 어떻게 쓰였든 걸린다."""
    rows = read_rows(CUE_CSV)
    by_group = [row for row in rows if row["Group"] == VIDEO_CALL_GROUP]
    assert len(by_group) == 6
    # 그중 하나는 Note 가 LW- 형태가 아니다. 그래도 그룹으로는 걸린다.
    off_pattern = [row for row in by_group if "LW-" not in (row.get("Note") or "")]
    assert len(off_pattern) == 1
    assert off_pattern[0]["Q#"] == "Q170"


def _cues_in(payload: bytes) -> list[str]:
    lines = [line for line in payload.decode("utf-8").splitlines() if line.strip()]
    order: list[str] = []
    for line in lines[1:]:
        cue = line.split(",")[0]
        if cue not in order:
            order.append(cue)
    return order


def _rows_in(payload: bytes) -> int:
    return len([line for line in payload.decode("utf-8").splitlines() if line.strip()]) - 1


def test_slice_never_splits_a_cue() -> None:
    """§11.1 1열 「부분집합 금지 — 모든 큐에 최소 1행」.

    형제 프리셋 하네스는 행으로 자르지만 큐는 그러면 안 된다. 경계에 걸린 큐가
    반쪽이 되면 발사기가 스스로 명세서를 어긴다.
    """
    rows = read_rows(CUE_CSV)
    first_cue = rows[0]["Q#"]
    expected_rows = len([row for row in rows if row["Q#"] == first_cue])
    assert expected_rows > 1, "첫 큐가 1행뿐이면 이 검사가 아무것도 구분하지 못한다"

    payload = slice_by_cue(CUE_CSV, 1)
    assert _cues_in(payload) == [first_cue]
    assert _rows_in(payload) == expected_rows


def test_slice_skip_moves_by_cue_not_by_row() -> None:
    rows = read_rows(CUE_CSV)
    order = list(dict.fromkeys(row["Q#"] for row in rows))
    payload = slice_by_cue(CUE_CSV, 1, skip=1)
    assert _cues_in(payload) == [order[1]]


def test_slice_with_no_limit_keeps_every_row() -> None:
    payload = slice_by_cue(CUE_CSV, None)
    assert _rows_in(payload) == 89
    assert len(_cues_in(payload)) == 18


def test_leak_detector_fires_on_a_fabricated_leak() -> None:
    """양성 대조군. 안 터지는 탐지기는 0 을 증거로 쓸 수 없다."""
    leaking = [("Group 9 At 55", "Group " + VIDEO_CALL_GROUP + " At 55")]
    assert len(leaked_commands(leaking)) == 1


def test_leak_detector_is_silent_on_clean_bundles() -> None:
    clean = [("Group 1 At 55", "Group 2 At 40")]
    assert leaked_commands(clean) == []
