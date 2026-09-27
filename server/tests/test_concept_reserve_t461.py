"""카드 t461 ② — 컨셉 리포트에 리저브 해제 큐와 행별 잔여 그룹 수(추가만).

REQ-090(BLIND 잠금)·REQ-093 경고 (3)(4)의 서버 원천. 새 계산은 없다 —
잔여 그룹 수는 ``headroom.compute_cue_headroom().unused_groups`` 를, 해제 큐는
해석된 큐 상태(``build.states``)에서 그 그룹이 처음 켜지는 행을 그대로 읽는다.
유보색은 입력이 실어 올 때(``raw_song["reserved"]``)만 나온다 — 상수 팔레트의
흰색은 증거가 아니므로 쓰지 않는다(카드 t444).
"""

from __future__ import annotations

from server.concept.gates import build_song
from server.concept.session_bridge import (
    _concept_reserve,
    _concept_rows,
    _raw_sections_from_pairs,
)

_PAIRS = [
    ("Intro", 0),
    ("Verse 1", 15000),
    ("Chorus 1", 40000),
    ("Verse 2", 60000),
    ("Chorus 2", 85000),
    ("Bridge", 105000),
    ("Chorus 3", 125000),
    ("Outro", 150000),
]


def _build(reserved: tuple[str, ...] = ()):
    raw = _raw_sections_from_pairs(_PAIRS)
    song: dict[str, object] = {"song": "t461", "bpm": 120.0, "sections": raw}
    if reserved:
        song["reserved"] = list(reserved)
    return build_song(song)


def test_rows_carry_unused_group_count() -> None:
    rows, _pairing = _concept_rows(_build(), screen_count=8)
    # .moai/reports/t461/measure_reserve.out.txt 실측
    assert [row["unused_groups"] for row in rows] == [
        10, 9, 7, 7, 6, 6, 4, 7, 6, 4, 4, 4, 9, 6, 1, 1, 1, 1, 1, 11,
    ]  # fmt: skip


def test_blind_release_is_the_first_row_it_turns_on() -> None:
    build = _build()
    rows, _pairing = _concept_rows(build, screen_count=8)
    reserve = _concept_reserve(build, rows)
    assert reserve == [
        {"name": "BLIND", "kind": "group", "released_q": 15, "screen_position": 6},
        {"name": "STROBE", "kind": "group", "released_q": None, "screen_position": None},
    ]


def test_reserved_colour_comes_only_from_input() -> None:
    build = _build(reserved=("흰색",))
    rows, _pairing = _concept_rows(build, screen_count=8)
    reserve = _concept_reserve(build, rows)
    colours = [item for item in reserve if item["kind"] == "color"]
    assert colours and colours[0]["name"] == "흰색"


def test_unpaired_report_keeps_release_q_but_no_screen_position() -> None:
    build = _build()
    rows, _pairing = _concept_rows(build, screen_count=7)
    reserve = _concept_reserve(build, rows)
    blind = next(item for item in reserve if item["name"] == "BLIND")
    assert blind["released_q"] == 15
    assert blind["screen_position"] is None
