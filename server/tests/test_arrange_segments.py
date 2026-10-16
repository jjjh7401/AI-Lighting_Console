"""구간 단위 배치 초안 생성기 시험 — SPEC-LDRHYTHM-001 「음악 분석 이벤트로 나눈 희소 칸」.

기존 ``generate_arrangement_draft`` 는 모든 줄의 모든 마디에 칸을 하나씩 낸다. 새 생성기
(``generate_segment_draft``)는 마디 지도의 이벤트로 곡을 구간으로 나누고, 줄마다 값이 바뀌는
마디에만 칸을 낸다. 합성 마디 지도(4/4, 박 500밀리초, 40마디)와 LOVE ATTACK 기본 격자의 트랙
구성으로 규칙을 잡고, 실제 LOVE ATTACK 마디 특징 픽스처로 강조·예고 마디를 확인한다.

- 칸은 구조화 값(밝기·움직임·효과·위치·진입)이 같은 연속 마디의 묶음이다. 구간 종류와 계획 색은
  칸을 나누는 값이 아니다. 색은 칸의 속성이고, 색이 바뀌는 마디에서 칸을 나누는 줄은 워시 줄뿐이다.
- 쉬는 연속 마디는 밝기 0의 「—」 한 칸이다.
- 라벨은 기본 격자(love_attack.yaml)와 배치 규칙서의 말이다.
- 빌드 구간 끝 마디에서 후렴이 바로 시작하면 블라인드 줄에 예고(밝기 0) 칸이 선다.

희소 초안에서 「그 마디의 칸」은 마디 이하에서 가장 가까운 행이다(앞 행의 상태가 이어진다).
"""

from __future__ import annotations

import copy
import inspect
import json
from pathlib import Path

import pytest

from server.audio.bar_map import BarFeatures, classify_bar_events, compute_bar_energy
from server.audio.bar_map_store import attach_rhythm, build_bar_map_payload
from server.design import arrange_segments
from server.design.arrange_apply import apply_arrangement_draft
from server.design.arrange_generator import REST_LABEL, UNCONFIRMED_NOTE
from server.design.arrange_policy import ArrangementPalette, ArrangementPolicy
from server.design.arrange_segments import SegmentSection, generate_segment_draft, split_sections
from server.design.beat_grid import LOVE_ATTACK_TITLE, default_beat_grid
from server.design.grid_shape import pattern_category

BARS = 40
FIXTURES_DIR = Path(__file__).parent / "fixtures"
PALETTE = ArrangementPalette()

#: 칸 라벨의 정본 — 기본 격자(love_attack.yaml)와 배치 규칙서(effect-arrangement-rules)의 말이다.
#: 시험이 따로 들고 있어서 구현의 상수를 바꿔도 시험이 따라 바뀌지 않는다.
PULSE_LABEL = "킥 1·2·4박"  # BACK 펄스. 예전 「펄스 1·2·4박」이 아니다.
CHASE_LABEL = "SIDE-L/R 2·4박 번갈이"
MOTION_LABEL = "팬 웨이브(한 바퀴 2마디)"
HOLD_LABEL = "정지"
FOH_LABEL = "FOH 켬"
WASH_LABEL = "워시"
BLIND_LABEL = "BLIND 2박"
STROBE_LABEL = "STROBE 1마디 박마다"
PRE_HIT_LABEL = "3·4박 전부 비움(예고)"  # 큰 히트 전 비움(예고). 기본 격자 BLIND 17마디 칸의 말.


def _ev(kind: str, start: int, end: int | None = None) -> dict:
    return {"kind": kind, "start_bar": start, "end_bar": start if end is None else end}


#: 합성 곡. 7 마디 브레이크 뒤엔 드롭이 가깝지 않다(벌스). 33~34 마디 브레이크는 끝 마디 34 의 둘째
#: 마디 뒤(36)에 드롭이 시작한다(브릿지). 드롭은 36~39 마디라 40 마디가 마지막 후렴이다.
SYNTHETIC_EVENTS = [
    _ev("break", 7),
    _ev("kick_entry", 9),
    _ev("build", 14, 17),
    _ev("kick_entry", 18),
    _ev("break", 33, 34),
    _ev("drop", 36, 39),
]
SYNTHETIC_SECTIONS = [
    SegmentSection(1, 6, "intro"),
    SegmentSection(7, 8, "verse"),
    SegmentSection(9, 13, "chorus"),
    SegmentSection(14, 17, "build"),
    SegmentSection(18, 32, "chorus"),
    SegmentSection(33, 35, "bridge"),
    SegmentSection(36, 39, "drop"),
    SegmentSection(40, 40, "last_chorus"),
]
#: 실제 LOVE ATTACK 에서 운영 분류기(``classify_bar_events``)가 내는 이벤트.
REAL_EVENTS = [
    ("kick_entry", 4, 4),
    ("build", 14, 17),
    ("kick_entry", 18, 18),
    ("break", 33, 33),
    ("build", 42, 45),
    ("kick_entry", 46, 46),
    ("break", 61, 61),
    ("drop", 63, 66),
    ("break", 82, 82),
]
REAL_SECTIONS = [
    SegmentSection(0, 3, "intro"),
    SegmentSection(4, 13, "chorus"),
    SegmentSection(14, 17, "build"),
    SegmentSection(18, 32, "chorus"),
    SegmentSection(33, 41, "verse"),
    SegmentSection(42, 45, "build"),
    SegmentSection(46, 60, "chorus"),
    SegmentSection(61, 62, "bridge"),
    SegmentSection(63, 66, "drop"),
    SegmentSection(67, 81, "last_chorus"),
    SegmentSection(82, 82, "verse"),
]


def _bar_map(events: list[dict] | None = None, bars: int = BARS) -> dict:
    beats = [index * 500 for index in range(bars * 4)]
    return build_bar_map_payload(beats, 0, bpm=120.0, events=events or [])


def _layout() -> list[dict]:
    return list(default_beat_grid(LOVE_ATTACK_TITLE)["tracks"])


def _draft(
    events: list[dict] | None = None,
    *,
    policy: ArrangementPolicy | None = None,
    planned_colors: dict | None = None,
    layout: list[dict] | None = None,
) -> dict:
    return generate_segment_draft(
        _bar_map(events),
        _layout() if layout is None else layout,
        policy,
        planned_colors=planned_colors,
    )


def _cues(draft: dict, name: str) -> dict[int, dict]:
    track = next(item for item in draft["tracks"] if item["group_name"] == name)
    return {cue["bar"]: cue for cue in track["cues"]}


def _rows(draft: dict, name: str) -> list[int]:
    return sorted(_cues(draft, name))


def _state(draft: dict, name: str, bar: int) -> dict:
    """그 마디에 적용되는 칸 — 마디 이하에서 가장 가까운 행이다."""
    return [cue for bar_no, cue in sorted(_cues(draft, name).items()) if bar_no <= bar][-1]


def _hits(draft: dict, name: str, label: str) -> list[int]:
    """칸이 이어지는 마디 전체에서 그 줄이 그 라벨인 마디. 강조가 한 마디짜리인지까지 본다."""
    span = draft["bar_range"]
    return [
        bar
        for bar in range(span["start"], span["end"] + 1)
        if _state(draft, name, bar)["label"] == label
    ]


def _signature(cue: dict) -> tuple:
    return (
        cue["label"],
        cue["brightness"]["value_percent"],
        cue["app_movement"],
        cue.get("planned_color"),
        cue["source_ref"],
    )


def _values(cue: dict) -> str:
    """칸을 나누는 값 — 라벨과 구조화 값 전부. 마디·계획 색·출처만 뺀다.

    라벨을 넣는 까닭: 예고 칸과 쉼 칸은 밝기가 같아서 구조화 값만으로는 가를 수 없다.
    """
    skipped = ("bar", "planned_color", "source_ref")
    kept = {key: value for key, value in cue.items() if key not in skipped}
    return json.dumps(kept, sort_keys=True, ensure_ascii=False)


# -- 구간 나누기와 종류 ---------------------------------------------------------------------


def test_sections_start_at_the_first_bar_every_event_and_after_a_drop() -> None:
    assert split_sections(_bar_map(SYNTHETIC_EVENTS)) == SYNTHETIC_SECTIONS


@pytest.mark.parametrize(
    "events",
    [[], SYNTHETIC_EVENTS, [_ev("drop", 38, 40)], [_ev("kick_entry", 1)], [_ev("break", 40)]],
)
def test_sections_cover_every_bar_exactly_once(events: list[dict]) -> None:
    sections = split_sections(_bar_map(events))
    covered = [bar for section in sections for bar in range(section.start_bar, section.end_bar + 1)]
    assert covered == list(range(1, BARS + 1))


@pytest.mark.parametrize(
    ("events", "start", "kind"),
    [
        ([], 1, "intro"),
        # 첫 마디에 이벤트가 있으면 도입이 아니다.
        ([_ev("kick_entry", 1)], 1, "chorus"),
        ([_ev("build", 1, 3)], 1, "build"),
        ([_ev("break", 1)], 1, "verse"),
        # 한 마디에 이벤트가 겹치면 먼저 맞는 규칙이다: 드롭 > 마지막 후렴 > 킥 진입 > 빌드.
        ([_ev("kick_entry", 20), _ev("drop", 20, 21)], 20, "drop"),
        ([_ev("drop", 10, 11), _ev("kick_entry", 12)], 12, "last_chorus"),
        ([_ev("drop", 10, 11), _ev("build", 12, 14)], 12, "last_chorus"),
        ([_ev("build", 10), _ev("break", 10)], 10, "build"),
        ([_ev("kick_entry", 10), _ev("build", 10)], 10, "chorus"),
    ],
)
def test_section_kind_follows_the_first_matching_rule(
    events: list[dict], start: int, kind: str
) -> None:
    sections = {section.start_bar: section.kind for section in split_sections(_bar_map(events))}
    assert sections[start] == kind


@pytest.mark.parametrize(
    ("break_start", "break_end", "drop_start", "kind"),
    [
        (30, 30, 31, "bridge"),  # 브레이크 끝 바로 다음 마디
        (30, 30, 32, "bridge"),  # 둘째 마디 — 경계
        (30, 30, 33, "verse"),  # 셋째 마디는 멀다
        (33, 33, 36, "verse"),  # 「33 마디 브레이크, 36~39 드롭」: 셋째 마디라 벌스
        (33, 34, 36, "bridge"),  # 「33~34 마디 브레이크」면 둘째 마디라 브릿지
    ],
)
def test_a_break_is_a_bridge_only_when_a_drop_starts_within_two_bars_after_it(
    break_start: int, break_end: int, drop_start: int, kind: str
) -> None:
    events = [_ev("break", break_start, break_end), _ev("drop", drop_start, drop_start + 1)]
    sections = {section.start_bar: section.kind for section in split_sections(_bar_map(events))}
    assert sections[break_start] == kind


def test_a_drop_at_the_last_bar_has_no_section_after_it() -> None:
    sections = split_sections(_bar_map([_ev("drop", 38, 40)]))
    assert sections[-1] == SegmentSection(38, 40, "drop")
    assert max(section.start_bar for section in sections) == 38


def test_energy_does_not_choose_section_kinds() -> None:
    beats = [index * 500 for index in range(BARS * 4)]
    energy = {bar: (bar % 7) / 7 for bar in range(1, BARS + 1)}
    with_energy = build_bar_map_payload(
        beats, 0, bpm=120.0, events=SYNTHETIC_EVENTS, bar_energy=energy
    )
    assert split_sections(with_energy) == SYNTHETIC_SECTIONS
    assert generate_segment_draft(with_energy, _layout()) == _draft(SYNTHETIC_EVENTS)


# -- 구간 색 ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("bar", "expected"),
    [
        (3, PALETTE.verse),  # 도입
        (7, PALETTE.verse),  # 벌스
        (10, PALETTE.chorus),  # 후렴
        (15, PALETTE.verse),  # 빌드는 팔레트 항목이 없어 벌스 색을 빌린다
        (20, PALETTE.chorus),
        (34, PALETTE.bridge),
        (37, PALETTE.drop),
        (40, PALETTE.last_chorus[0]),
    ],
)
def test_section_colors_come_from_the_palette(bar: int, expected: tuple[int, int, int]) -> None:
    draft = _draft(SYNTHETIC_EVENTS)
    assert _state(draft, "WASH-ALL", bar)["planned_color"] == list(expected)


def test_last_chorus_colors_cycle_by_the_number_of_earlier_last_chorus_sections() -> None:
    palette = ArrangementPalette(last_chorus=((1, 1, 1), (2, 2, 2), (3, 3, 3)))
    events = [_ev("drop", 6, 7), _ev("drop", 14, 15), _ev("drop", 22, 23), _ev("drop", 30, 31)]
    draft = _draft(events, policy=ArrangementPolicy(palette=palette))
    starts = [8, 16, 24, 32]
    assert [_state(draft, "WASH-ALL", bar)["planned_color"] for bar in starts] == [
        [1, 1, 1],
        [2, 2, 2],
        [3, 3, 3],
        [1, 1, 1],
    ]


def test_a_custom_palette_changes_the_section_colors() -> None:
    palette = ArrangementPalette(verse=(1, 2, 3), bridge=(4, 5, 6))
    draft = _draft(SYNTHETIC_EVENTS, policy=ArrangementPolicy(palette=palette))
    for bar in (3, 7, 15):  # 도입·벌스·빌드는 모두 벌스 색
        assert _state(draft, "WASH-ALL", bar)["planned_color"] == [1, 2, 3]
    assert _state(draft, "WASH-ALL", 34)["planned_color"] == [4, 5, 6]


def test_lit_back_cells_use_the_backlight_color_in_every_section() -> None:
    draft = _draft(SYNTHETIC_EVENTS)
    kinds = set()
    for section in split_sections(_bar_map(SYNTHETIC_EVENTS)):
        for bar in range(section.start_bar, section.end_bar + 1):
            cue = _state(draft, "BACK", bar)
            if cue["label"] != REST_LABEL:
                assert cue["planned_color"] == list(PALETTE.backlight)
                kinds.add(section.kind)
    assert len(kinds) >= 4, "역광이 켜진 구간 종류가 적으면 시험이 비어 있다"


def test_planned_color_override_wins_over_the_section_color_and_the_backlight() -> None:
    plain = _draft(SYNTHETIC_EVENTS)
    assert _state(plain, "WASH-ALL", 20)["planned_color"] == list(PALETTE.chorus)
    lit_back = next(
        bar for bar in range(1, BARS + 1) if _state(plain, "BACK", bar)["label"] == PULSE_LABEL
    )
    colors = {("WASH-ALL", 20): (1, 2, 3), ("BACK", lit_back): (4, 5, 6)}
    draft = _draft(SYNTHETIC_EVENTS, planned_colors=colors)
    wash = _cues(draft, "WASH-ALL")
    assert wash[20]["planned_color"] == [1, 2, 3]  # 구간 색을 이긴다
    assert wash[21]["planned_color"] == list(PALETTE.chorus)  # 다음 마디는 구간 색으로 돌아온다
    assert _cues(draft, "BACK")[lit_back]["planned_color"] == [4, 5, 6]  # 역광 색을 이긴다
    assert colors == {("WASH-ALL", 20): (1, 2, 3), ("BACK", lit_back): (4, 5, 6)}


def test_planned_color_on_a_rest_cell_is_ignored() -> None:
    plain = _draft(SYNTHETIC_EVENTS)
    rest_bar = next(
        bar for bar in range(1, BARS + 1) if _state(plain, "BACK", bar)["label"] == REST_LABEL
    )
    assert _draft(SYNTHETIC_EVENTS, planned_colors={("BACK", rest_bar): (7, 8, 9)}) == plain


# -- 칸 내기(압축) ---------------------------------------------------------------------------


def test_a_constant_lane_over_a_seven_bar_verse_has_exactly_one_row() -> None:
    events = [_ev("kick_entry", 3), _ev("break", 8), _ev("kick_entry", 15)]
    assert SegmentSection(8, 14, "verse") in split_sections(_bar_map(events))
    draft = _draft(events)
    # 워시 줄은 색이 바뀌는 구간 경계에서만 칸을 나눈다. 7마디 벌스는 한 칸이다.
    wash = _rows(draft, "WASH-ALL")
    assert [bar for bar in wash if 8 <= bar <= 14] == [8]
    assert wash == [1, 3, 8, 15]
    # 얼굴 빛은 구간 색이 바뀌어도 값이 같아서 곡 전체가 한 칸이다.
    assert _rows(draft, "FOH") == [1]


def test_a_four_bar_alternating_lane_has_a_row_only_where_its_plan_changes() -> None:
    # 이벤트가 없으면 1~40 마디가 도입 한 구간이고 4마디 창이 열 개다. 주인공은 펄스 → 체이스 →
    # 움직임 순으로 돌고 보통 구간은 둘이 움직이니, 펄스 층(BACK)은 창 0·2·3·5·6·8·9 에서 켜진다.
    draft = _draft([])
    back = _cues(draft, "BACK")
    assert [(bar, back[bar]["label"]) for bar in sorted(back)] == [
        (1, PULSE_LABEL),
        (5, REST_LABEL),
        (9, PULSE_LABEL),  # 창 2·3 이 이어져 8 마디 한 칸
        (17, REST_LABEL),
        (21, PULSE_LABEL),
        (29, REST_LABEL),
        (33, PULSE_LABEL),
    ]


def test_back_lane_over_the_synthetic_song_is_the_hand_derived_run_list() -> None:
    # 창이 구간 시작부터 4마디씩이고(1-4, 5-6, 7-8, 9-12, 13, 14-17, …) 주인공 순서가 곡 전체에서
    # 이어질 때 펄스 층이 켜진 연속 구간이다. 구간 경계를 넘어 이어지는 칸은 한 칸으로 묶인다.
    back = _cues(_draft(SYNTHETIC_EVENTS), "BACK")
    assert [(bar, back[bar]["label"]) for bar in sorted(back)] == [
        (1, PULSE_LABEL),
        (5, REST_LABEL),
        (7, PULSE_LABEL),
        (13, REST_LABEL),
        (14, PULSE_LABEL),
        (22, REST_LABEL),
        (26, PULSE_LABEL),
        (33, REST_LABEL),
        (36, PULSE_LABEL),
    ]


@pytest.mark.parametrize("events", [[], SYNTHETIC_EVENTS])
def test_no_two_consecutive_rows_of_a_track_share_the_same_plan(events: list[dict]) -> None:
    for track in _draft(events)["tracks"]:
        signatures = [_signature(cue) for cue in track["cues"]]
        assert all(left != right for left, right in zip(signatures, signatures[1:], strict=False))


def test_every_track_has_a_row_at_the_first_bar_and_a_rest_run_is_one_row() -> None:
    draft = _draft(SYNTHETIC_EVENTS)
    for track in draft["tracks"]:
        assert track["cues"][0]["bar"] == 1
    # 강조 줄: 첫 마디의 쉼, 강조 한 마디, 다시 쉼. 빌드(14~17) 끝 마디(17)의 예고 뒤가 강조(18)다.
    assert _rows(draft, "BLIND") == [1, 9, 10, 17, 18, 19, 40]
    assert _rows(draft, "STROBE") == [1, 36, 37]
    assert _cues(draft, "BLIND")[10]["label"] == REST_LABEL


def test_a_song_without_events_still_gives_every_track_one_row() -> None:
    draft = _draft([])
    assert _rows(draft, "FOH") == [1]
    assert _rows(draft, "STROBE") == [1]
    assert _cues(draft, "STROBE")[1]["label"] == REST_LABEL
    assert _cues(draft, "FOH")[1]["label"] == FOH_LABEL


# -- 쉬는 칸 ---------------------------------------------------------------------------------


@pytest.mark.parametrize("events", [[], SYNTHETIC_EVENTS])
def test_a_run_of_consecutive_rest_bars_is_one_rest_cell_of_brightness_zero(
    events: list[dict],
) -> None:
    for track in _draft(events)["tracks"]:
        cues = track["cues"]
        for cue in cues:
            if cue["label"] == REST_LABEL:
                assert cue["brightness"]["mode"] == "value"
                assert cue["brightness"]["value_percent"] == 0
                assert "planned_color" not in cue
        # 쉼 칸 둘이 이웃하면 연속 마디를 한 칸으로 묶지 않은 것이다.
        assert not any(
            left["label"] == REST_LABEL and right["label"] == REST_LABEL
            for left, right in zip(cues, cues[1:], strict=False)
        ), track["group_name"]


def test_a_rest_run_across_sections_and_windows_is_a_single_row() -> None:
    draft = _draft(SYNTHETIC_EVENTS)
    # 블라인드 줄의 10~16 마디는 창 두 개를 넘는 쉼이다. 행은 첫 마디(10) 하나뿐이다.
    assert [bar for bar in _rows(draft, "BLIND") if 10 <= bar <= 16] == [10]
    assert all(_state(draft, "BLIND", bar)["label"] == REST_LABEL for bar in range(10, 17))
    # 구간 경계를 일곱 번 넘도록 내내 쉬는 줄(느린 곡의 STROBE)도 첫 마디의 한 칸이다.
    slow = _draft(SYNTHETIC_EVENTS, policy=ArrangementPolicy(slow_song=True))
    assert _rows(slow, "STROBE") == [1]


def test_rests_stay_rows_instead_of_disappearing_from_the_draft() -> None:
    draft = _draft(SYNTHETIC_EVENTS)
    assert _cues(draft, "BACK")[5]["label"] == REST_LABEL
    assert _cues(draft, "SIDE-ALL")[7]["label"] == REST_LABEL
    assert _cues(draft, "STROBE")[1]["label"] == REST_LABEL


# -- 칸을 나누는 값 --------------------------------------------------------------------------


def test_color_alone_never_splits_a_run_off_the_wash_line() -> None:
    draft = _draft(SYNTHETIC_EVENTS)
    for track in draft["tracks"]:
        if track["layer_role"] == "wash":
            continue
        name = track["group_name"]
        values = [_values(cue) for cue in track["cues"]]
        assert all(left != right for left, right in zip(values, values[1:], strict=False)), name


def test_a_cell_off_the_wash_line_carries_the_color_of_its_first_bar() -> None:
    draft = _draft(SYNTHETIC_EVENTS)
    # 얼굴 빛은 40마디 내내 한 칸이고, 색은 그 칸 첫 마디(도입)의 색이다.
    foh = _cues(draft, "FOH")
    assert sorted(foh) == [1]
    assert foh[1]["planned_color"] == list(PALETTE.verse)
    # 체이스 칸 30~40 은 후렴·브릿지·드롭·마지막 후렴을 지나는 한 칸이다. 색은 30 마디(후렴) 색이다.
    side = _cues(draft, "SIDE-ALL")
    assert 30 in side
    assert not any(31 <= bar <= 40 for bar in side)
    assert side[30]["planned_color"] == list(PALETTE.chorus)


def test_the_wash_line_splits_where_its_planned_color_changes() -> None:
    wash = _cues(_draft(SYNTHETIC_EVENTS), "WASH-ALL")
    assert [(bar, wash[bar]["planned_color"]) for bar in sorted(wash)] == [
        (1, list(PALETTE.verse)),  # 도입(1~6)과 벌스(7~8)는 종류가 달라도 같은 색이라 한 칸이다
        (9, list(PALETTE.chorus)),
        (14, list(PALETTE.verse)),  # 빌드는 벌스 색을 빌린다
        (18, list(PALETTE.chorus)),
        (33, list(PALETTE.bridge)),
        (36, list(PALETTE.drop)),
        (40, list(PALETTE.last_chorus[0])),
    ]
    assert {cue["label"] for cue in wash.values()} == {WASH_LABEL}


def test_an_annotation_color_inside_a_run_gets_its_own_cell_on_any_line() -> None:
    draft = _draft(SYNTHETIC_EVENTS, planned_colors={("FOH", 20): (1, 2, 3)})
    foh = _cues(draft, "FOH")
    assert sorted(foh) == [1, 20, 21]
    assert foh[1]["planned_color"] == list(PALETTE.verse)
    assert foh[20]["planned_color"] == [1, 2, 3]
    assert foh[21]["planned_color"] == list(PALETTE.chorus)  # 다음 마디는 구간 색으로 돌아온다
    assert {cue["label"] for cue in foh.values()} == {FOH_LABEL}


def test_an_annotation_color_equal_to_the_planned_color_adds_no_cell() -> None:
    # LOVE ATTACK 은 BACK 0 마디에 하늘색 주석이 있고 그 값이 역광 색과 같다. 칸은 늘지 않는다.
    plain = _draft(SYNTHETIC_EVENTS)
    same = _draft(SYNTHETIC_EVENTS, planned_colors={("BACK", 1): PALETTE.backlight})
    assert same == plain


def test_the_draft_is_much_sparser_than_one_row_per_bar() -> None:
    draft = _draft(SYNTHETIC_EVENTS)
    rows = sum(len(track["cues"]) for track in draft["tracks"])
    assert rows < len(draft["tracks"]) * BARS / 2


def test_track_without_a_role_stays_at_rest_with_one_row() -> None:
    layout = [
        {"group_no": 1, "group_no_confirmed": True, "group_name": "EXTRA", "layer_role": None}
    ]
    draft = _draft(SYNTHETIC_EVENTS, layout=layout)
    assert [(bar, cue["label"]) for bar, cue in _cues(draft, "EXTRA").items()] == [(1, REST_LABEL)]


# -- 강조 ------------------------------------------------------------------------------------


def test_blind_is_only_on_chorus_and_last_chorus_starts_and_strobe_only_on_drop_starts() -> None:
    draft = _draft(SYNTHETIC_EVENTS)
    sections = split_sections(_bar_map(SYNTHETIC_EVENTS))
    blind_starts = [s.start_bar for s in sections if s.kind in ("chorus", "last_chorus")]
    drop_starts = [s.start_bar for s in sections if s.kind == "drop"]
    assert _hits(draft, "BLIND", BLIND_LABEL) == blind_starts == [9, 18, 40]
    assert _hits(draft, "STROBE", STROBE_LABEL) == drop_starts == [36]


def test_slow_song_suppresses_strobe_but_keeps_blind() -> None:
    draft = _draft(SYNTHETIC_EVENTS, policy=ArrangementPolicy(slow_song=True))
    assert _hits(draft, "STROBE", STROBE_LABEL) == []
    assert _rows(draft, "STROBE") == [1]
    assert _hits(draft, "BLIND", BLIND_LABEL) == [9, 18, 40]


def test_a_kick_entry_on_a_drop_start_gives_strobe_not_blind() -> None:
    # 20 마디는 킥 진입과 드롭이 함께 시작해 드롭 구간이다. 블라인드는 마지막 후렴(22)에만 있다.
    draft = _draft([_ev("kick_entry", 20), _ev("drop", 20, 21)])
    assert _hits(draft, "STROBE", STROBE_LABEL) == [20]
    assert _hits(draft, "BLIND", BLIND_LABEL) == [22]


def test_a_kick_entry_on_the_first_bar_makes_that_bar_a_blind_chorus_start() -> None:
    draft = _draft([_ev("kick_entry", 1)])
    assert _hits(draft, "BLIND", BLIND_LABEL) == [1]


def test_builds_breaks_verses_and_intros_get_no_accent() -> None:
    draft = _draft([_ev("break", 5), _ev("build", 12, 14), _ev("break", 25)])
    assert _hits(draft, "BLIND", BLIND_LABEL) == []
    assert _hits(draft, "STROBE", STROBE_LABEL) == []


# -- 창과 리듬층 -----------------------------------------------------------------------------


def test_windows_are_four_bar_blocks_counted_from_each_section_start() -> None:
    windows = _draft(SYNTHETIC_EVENTS)["windows"]
    assert [(window["start_bar"], window["end_bar"]) for window in windows] == [
        (1, 4),
        (5, 6),
        (7, 8),
        (9, 12),
        (13, 13),
        (14, 17),
        (18, 21),
        (22, 25),
        (26, 29),
        (30, 32),
        (33, 35),
        (36, 39),
        (40, 40),
    ]
    assert [window["drop"] for window in windows].count(True) == 1


def test_window_bars_come_from_the_policy() -> None:
    draft = _draft([], policy=ArrangementPolicy(window_bars=8))
    back = _cues(draft, "BACK")
    assert [(bar, back[bar]["label"]) for bar in sorted(back)] == [
        (1, PULSE_LABEL),
        (9, REST_LABEL),
        (17, PULSE_LABEL),
        (33, REST_LABEL),
    ]


def test_rhythmic_tracks_per_bar_stay_within_the_layer_caps() -> None:
    draft = _draft(SYNTHETIC_EVENTS)
    rhythmic = {PULSE_LABEL, CHASE_LABEL, MOTION_LABEL}
    roles = {"back", "side", "mover"}
    counts_in_drop = []
    for window in draft["windows"]:
        for bar in range(window["start_bar"], window["end_bar"] + 1):
            count = sum(
                1
                for track in draft["tracks"]
                if track["layer_role"] in roles
                and _state(draft, track["group_name"], bar)["label"] in rhythmic
            )
            assert count <= (3 if window["drop"] else 2)
            if window["drop"]:
                counts_in_drop.append(count)
    assert max(counts_in_drop) == 3, "드롭 구간에서는 셋까지 실제로 움직인다"


def test_motion_alternates_between_the_two_movers_and_the_other_holds() -> None:
    draft = _draft(SYNTHETIC_EVENTS)
    turns = []
    for window in draft["windows"]:
        if "motion" not in window["active"]:
            continue
        upper = _state(draft, "MOVER-U", window["start_bar"])["label"]
        lower = _state(draft, "MOVER-D", window["start_bar"])["label"]
        assert {upper, lower} == {MOTION_LABEL, HOLD_LABEL}
        turns.append("U" if upper == MOTION_LABEL else "D")
    assert len(turns) >= 4
    assert all(left != right for left, right in zip(turns, turns[1:], strict=False))


def test_layout_without_rhythm_tracks_has_no_lead() -> None:
    layout = [track for track in _layout() if track["group_name"] == "WASH-ALL"]
    draft = _draft(SYNTHETIC_EVENTS, layout=layout)
    assert all(window["lead"] is None and window["active"] == [] for window in draft["windows"])
    # 도입(1~6)과 벌스(7~8)는 같은 벌스 색이라 한 칸이다. 마지막 후렴(40)은 드롭 뒤라 색이 바뀐다.
    assert _rows(draft, "WASH-ALL") == [1, 9, 14, 18, 33, 36, 40]


# -- 칸의 구조화 값과 정책 --------------------------------------------------------------------


def test_rows_carry_the_structured_fields_of_the_dense_generator() -> None:
    draft = _draft(SYNTHETIC_EVENTS)
    rows = [cue for track in draft["tracks"] for cue in track["cues"]]
    for cue in rows:
        assert cue["brightness"]["mode"] == "value"
        assert cue["entry"]["trigger_beat"] == 1
        assert str(cue["source_ref"]).startswith("arrangement_segments:")
        if cue["label"] in (REST_LABEL, PRE_HIT_LABEL):  # 꺼진 칸: 밝기 0, 색 없음
            assert cue["brightness"]["value_percent"] == 0
            assert "planned_color" not in cue
        else:
            assert cue["brightness"]["value_percent"] == 100
            assert len(cue["planned_color"]) == 3
        if cue["label"] == MOTION_LABEL:
            movement = cue["app_movement"]
            assert (movement["shape"], movement["period_unit"], movement["period_value"]) == (
                "wave",
                "bar",
                2,
            )
        else:
            assert cue["app_movement"] is None
    labels = {cue["label"] for cue in rows}
    assert {
        PULSE_LABEL,
        CHASE_LABEL,
        MOTION_LABEL,
        HOLD_LABEL,
        FOH_LABEL,
        WASH_LABEL,
        BLIND_LABEL,
        STROBE_LABEL,
        PRE_HIT_LABEL,
        REST_LABEL,
    } <= labels


def test_brightness_comes_from_the_policy() -> None:
    draft = _draft(SYNTHETIC_EVENTS, policy=ArrangementPolicy(lit_percent=80, rest_percent=10))
    for track in draft["tracks"]:
        for cue in track["cues"]:
            expected = 10 if cue["label"] in (REST_LABEL, PRE_HIT_LABEL) else 80
            assert cue["brightness"]["value_percent"] == expected


# -- 라벨 ------------------------------------------------------------------------------------


def test_labels_use_the_default_grid_and_rules_document_vocabulary() -> None:
    draft = _draft(SYNTHETIC_EVENTS)
    labels = {
        track["group_name"]: {cue["label"] for cue in track["cues"]} for track in draft["tracks"]
    }
    assert labels["FOH"] == {FOH_LABEL}
    assert labels["WASH-ALL"] == {WASH_LABEL}
    assert labels["BACK"] == {PULSE_LABEL, REST_LABEL}
    assert labels["SIDE-ALL"] == {CHASE_LABEL, REST_LABEL}
    assert labels["MOVER-U"] == labels["MOVER-D"] == {MOTION_LABEL, HOLD_LABEL}
    assert labels["BLIND"] == {BLIND_LABEL, PRE_HIT_LABEL, REST_LABEL}
    assert labels["STROBE"] == {STROBE_LABEL, REST_LABEL}


def test_the_old_generator_wording_is_not_used() -> None:
    old = {"펄스 1·2·4박", "체이스 2·4박", "팬 웨이브 2마디", "블라인드 2박", "스트로브 1마디"}
    draft = _draft(SYNTHETIC_EVENTS)
    labels = {cue["label"] for track in draft["tracks"] for cue in track["cues"]}
    assert labels.isdisjoint(old | {"유지"})


def test_each_label_sits_in_a_pattern_class_the_default_grid_line_also_has() -> None:
    # 판정기(grid_shape)가 칸 라벨을 나누는 박 패턴 종류로 보아, 라벨마다 기본 격자의 같은 줄에도
    # 그 종류의 칸이 있다. 기본 격자의 말을 가져왔는지 확인하는 시험이다. 판정기를 통과하려고
    # 라벨을 고르는 시험이 아니다 — 라벨의 정본은 위 상수(기본 격자와 배치 규칙서의 말)다.
    base = {
        track["group_name"]: {pattern_category(cue["label"]) for cue in track["cues"]}
        for track in default_beat_grid(LOVE_ATTACK_TITLE)["tracks"]
    }
    assert pattern_category(PULSE_LABEL) in base["BACK"]
    assert pattern_category(CHASE_LABEL) in base["SIDE-ALL"]
    assert pattern_category(HOLD_LABEL) in base["MOVER-U"]
    assert pattern_category(MOTION_LABEL) in base["MOVER-U"]
    assert pattern_category(FOH_LABEL) in base["FOH"]
    assert pattern_category(WASH_LABEL) in base["WASH-ALL"]
    assert pattern_category(BLIND_LABEL) in base["BLIND"]
    assert pattern_category(PRE_HIT_LABEL) in base["BLIND"]
    assert pattern_category(REST_LABEL) in base["BACK"]


# -- 예고(큰 히트 전 비움) ---------------------------------------------------------------------


def test_the_last_bar_of_a_build_before_a_chorus_gets_a_notice_cell_on_the_blind_line() -> None:
    draft = _draft(SYNTHETIC_EVENTS)  # 빌드 14~17 바로 뒤 18 마디가 후렴
    blind = _cues(draft, "BLIND")
    notice = blind[17]
    assert notice["label"] == PRE_HIT_LABEL
    assert notice["brightness"]["value_percent"] == 0
    assert "planned_color" not in notice
    assert notice["source_ref"] == "arrangement_segments:pre_hit"
    assert blind[18]["label"] == BLIND_LABEL  # 임팩트 마디의 강조는 그대로 다음 마디에 있다
    assert [bar for bar in sorted(blind) if 14 <= bar <= 19] == [17, 18, 19]


def test_the_notice_is_not_an_accent() -> None:
    draft = _draft(SYNTHETIC_EVENTS)
    assert _hits(draft, "BLIND", BLIND_LABEL) == [9, 18, 40]
    assert _hits(draft, "BLIND", PRE_HIT_LABEL) == [17]


def test_the_notice_sits_on_the_bar_before_the_chorus_when_the_build_event_ended_early() -> None:
    # 빌드 이벤트는 5~8 마디인데 후렴은 10 마디다. 구간으로는 빌드가 9 마디까지라 예고는 9 마디다.
    draft = _draft([_ev("build", 5, 8), _ev("kick_entry", 10)])
    assert _hits(draft, "BLIND", PRE_HIT_LABEL) == [9]
    assert _hits(draft, "BLIND", BLIND_LABEL) == [10]


@pytest.mark.parametrize(
    "events",
    [
        [_ev("kick_entry", 9)],  # 빌드 없이 후렴
        [_ev("build", 5, 8), _ev("break", 9)],  # 빌드 뒤가 브레이크
        [_ev("build", 5, 8), _ev("drop", 9, 10)],  # 빌드 뒤가 드롭 — 예고는 후렴 앞에만 둔다
        [_ev("build", 5, 8)],  # 빌드가 곡 끝까지 이어진다
        [_ev("build", 5, 8), _ev("build", 9, 12)],  # 빌드 뒤가 또 빌드
    ],
)
def test_no_notice_unless_a_chorus_starts_right_after_the_build(events: list[dict]) -> None:
    draft = _draft(events)
    for track in draft["tracks"]:
        assert all(cue["label"] != PRE_HIT_LABEL for cue in track["cues"]), track["group_name"]


def test_the_notice_is_only_on_the_blind_line() -> None:
    draft = _draft(SYNTHETIC_EVENTS)
    for track in draft["tracks"]:
        has_notice = any(cue["label"] == PRE_HIT_LABEL for cue in track["cues"])
        assert has_notice == (track["group_name"] == "BLIND"), track["group_name"]


def test_an_annotation_color_on_the_notice_bar_is_ignored_like_on_any_rest() -> None:
    plain = _draft(SYNTHETIC_EVENTS)
    assert _draft(SYNTHETIC_EVENTS, planned_colors={("BLIND", 17): (7, 8, 9)}) == plain


def test_the_notice_survives_the_slow_song_flag_and_follows_the_rest_brightness() -> None:
    slow = _draft(SYNTHETIC_EVENTS, policy=ArrangementPolicy(slow_song=True))
    assert _hits(slow, "BLIND", PRE_HIT_LABEL) == [17]
    dim = _draft(SYNTHETIC_EVENTS, policy=ArrangementPolicy(rest_percent=10))
    assert _cues(dim, "BLIND")[17]["brightness"]["value_percent"] == 10


def test_draft_shape_matches_the_dense_generator() -> None:
    draft = _draft(SYNTHETIC_EVENTS)
    assert draft["source"] == "arrangement_segments"
    assert draft["note"] is None
    assert draft["bar_range"] == {"start": 1, "end": BARS}
    assert [track["group_name"] for track in draft["tracks"]] == [
        track["group_name"] for track in _layout()
    ]
    for track, source in zip(draft["tracks"], _layout(), strict=True):
        assert track["group_no"] == source["group_no"]
        assert track["group_no_confirmed"] == source["group_no_confirmed"]
        assert track["layer_role"] == source["layer_role"]


# -- 입력이 없거나 틀릴 때, 순수성 -------------------------------------------------------------


@pytest.mark.parametrize("bad", [None, {"schema_version": 99}])
def test_missing_or_invalid_bar_map_returns_an_empty_draft_with_a_note(bad: object) -> None:
    draft = generate_segment_draft(bad, _layout())  # type: ignore[arg-type]
    assert draft["tracks"] == []
    assert draft["windows"] == []
    assert draft["bar_range"] == {}
    assert draft["source"] == "arrangement_segments"
    assert UNCONFIRMED_NOTE in (draft["note"] or "")


def test_overlapping_group_tracks_and_unknown_roles_are_rejected() -> None:
    overlap = _layout() + [
        {
            "group_no": 99,
            "group_no_confirmed": True,
            "group_name": "MOVER-ALL",
            "layer_role": "mover",
        }
    ]
    with pytest.raises(ValueError):
        generate_segment_draft(_bar_map(), overlap)
    unknown = [
        {"group_no": 1, "group_no_confirmed": True, "group_name": "EXTRA", "layer_role": "laser"}
    ]
    with pytest.raises(ValueError):
        generate_segment_draft(_bar_map(), unknown)


def test_generator_is_pure_same_input_same_draft_and_inputs_untouched() -> None:
    bar_map, layout = _bar_map(SYNTHETIC_EVENTS), _layout()
    colors = {("WASH-ALL", 20): (1, 2, 3)}
    snapshot = copy.deepcopy((bar_map, layout, colors))
    first = generate_segment_draft(bar_map, layout, planned_colors=colors)
    assert (bar_map, layout, colors) == snapshot
    assert first == generate_segment_draft(bar_map, layout, planned_colors=colors)


def test_generator_source_has_no_console_or_file_access() -> None:
    source = inspect.getsource(arrange_segments)
    for token in ("ConsoleLink", ".exec(", ".deploy(", "open(", "pathlib", "write_text"):
        assert token not in source


# -- 격자에 반영 -----------------------------------------------------------------------------


def test_apply_accepts_a_sparse_draft_and_bars_without_a_row_keep_their_cues() -> None:
    grid = copy.deepcopy(default_beat_grid(LOVE_ATTACK_TITLE))
    draft = _draft(SYNTHETIC_EVENTS)
    updated, report = apply_arrangement_draft(grid, draft)
    assert any("새로 만들" in line for line in report)
    assert updated["bar_range"] == {"start": 0, "end": BARS}
    kept = 0
    for draft_track in draft["tracks"]:
        name = draft_track["group_name"]
        before = {
            cue["bar"]: cue
            for cue in next(t for t in grid["tracks"] if t["group_name"] == name)["cues"]
        }
        after = {
            cue["bar"]: cue
            for cue in next(t for t in updated["tracks"] if t["group_name"] == name)["cues"]
        }
        row_bars = {cue["bar"] for cue in draft_track["cues"]}
        assert set(after) == set(before) | row_bars, "행이 없는 마디에는 새 칸이 생기지 않는다"
        for bar, cue in before.items():
            if bar not in row_bars:
                assert after[bar] == cue, (name, bar)
                kept += 1
    assert kept >= 10, "행이 없는 마디의 기존 칸이 충분히 있어야 시험이 의미가 있다"


# -- 실제 LOVE ATTACK ------------------------------------------------------------------------


def _real_love_attack() -> dict:
    """실제 마디 특징에 운영 함수로 이벤트·에너지를 뽑아 마디 지도를 만든다."""
    with (FIXTURES_DIR / "love_attack_bar_features_real.json").open(encoding="utf-8") as handle:
        rows = json.load(handle)["bar_features"]
    with (FIXTURES_DIR / "love_attack_beat_grid.json").open(encoding="utf-8") as handle:
        grid = json.load(handle)
    features = [
        BarFeatures(
            bar=int(row["bar"]),
            volume_norm=float(row["volume_norm"]),
            low_band_norm=float(row["low_band_norm"]),
            vocal_band_ratio=row["vocal_band_ratio"],
            onset_count=row["onset_count"],
        )
        for row in rows
    ]
    return build_bar_map_payload(
        [int(ms) for ms in grid["beat_times_ms"]],
        int(grid["expected_first_beat_offset"]),
        bpm=float(grid["bpm"]),
        events=classify_bar_events(features),
        bar_energy=compute_bar_energy(features),
    )


def test_real_love_attack_events_sections_and_accents() -> None:
    bar_map = _real_love_attack()
    # 전제: 운영 분류기가 실제 곡에서 내는 이벤트. 이게 바뀌면 강조 단언이 아니라 여기서 알린다.
    assert [(e["kind"], e["start_bar"], e["end_bar"]) for e in bar_map["events"]] == REAL_EVENTS
    assert split_sections(bar_map) == REAL_SECTIONS
    draft = generate_segment_draft(bar_map, _layout())
    assert draft["bar_range"] == {"start": 0, "end": 82}
    assert _hits(draft, "BLIND", BLIND_LABEL) == [4, 18, 46, 67]
    assert _hits(draft, "STROBE", STROBE_LABEL) == [63]
    # 예고는 빌드(14~17·42~45) 끝 마디에만 있고, 강조 마디는 그대로다.
    assert _hits(draft, "BLIND", PRE_HIT_LABEL) == [17, 45]
    assert _rows(draft, "BLIND") == [0, 4, 5, 17, 18, 19, 45, 46, 47, 67, 68]
    # 워시 줄의 칸은 색이 바뀌는 구간 경계에서만 생긴다. 얼굴 빛은 곡 전체가 한 칸이다.
    starts = {section.start_bar for section in REAL_SECTIONS}
    assert set(_rows(draft, "WASH-ALL")) <= starts
    assert _rows(draft, "FOH") == [0]


# -- 리듬 블록(rhythm): 구간 경계와 구간 등급 ----------------------------------------------------


def _rhythm_block(
    bar_map: dict,
    sections: list[tuple[int, int, int]],
    hits: list[tuple[int, int]] | None = None,
) -> dict:
    """마디 지도에 맞는 ``rhythm`` 블록. 구간은 (시작, 끝, 등급) 마디, 히트는 (마디, 박)이다."""
    starts = {bar["bar"]: bar["start_ms"] for bar in bar_map["bars"]}
    beats = [
        {
            "bar": bar["bar"],
            "beat": index,
            "t_ms": time_ms,
            "kick": 0.5,
            "snare": 0.5,
            "onset": 0.5,
            "kick_hit": False,
            "snare_hit": False,
        }
        for bar in bar_map["bars"]
        for index, time_ms in enumerate(bar["beats_ms"], start=1)
    ]
    times = {(item["bar"], item["beat"]): item["t_ms"] for item in beats}
    return {
        "beats": beats,
        "hits": [
            {"bar": bar, "beat": beat, "t_ms": times[(bar, beat)], "strength": 0.9, "kind": "big"}
            for bar, beat in (hits or [])
        ],
        "sections": [
            {
                "start_bar": start,
                "end_bar": end,
                "bars": end - start + 1,
                "start_ms": starts[start],
                "end_ms": starts[end] + 2000,
                "d_level": level,
            }
            for start, end, level in sections
        ],
    }


def _rhythm_map(
    events: list[dict],
    sections: list[tuple[int, int, int]],
    hits: list[tuple[int, int]] | None = None,
) -> dict:
    bar_map = _bar_map(events)
    return attach_rhythm(bar_map, _rhythm_block(bar_map, sections, hits))


#: 합성 곡에 얹는 리듬 구간. 21 마디의 경계만 합성 곡의 구간 시작에 없다.
RHYTHM_SECTIONS = [(1, 8, 2), (9, 20, 4), (21, 40, 3)]


def _starts(sections: list[SegmentSection]) -> list[int]:
    return [section.start_bar for section in sections]


def test_rhythm_section_starts_are_added_to_the_event_derived_boundaries() -> None:
    plain = split_sections(_bar_map(SYNTHETIC_EVENTS))
    with_rhythm = split_sections(_rhythm_map(SYNTHETIC_EVENTS, RHYTHM_SECTIONS))
    assert _starts(plain) == [1, 7, 9, 14, 18, 33, 36, 40]
    assert _starts(with_rhythm) == [1, 7, 9, 14, 18, 21, 33, 36, 40]
    # 21 마디에서 후렴(18~32)이 둘로 갈린다. 이벤트가 없는 마디에서 시작하니 벌스다.
    assert [(s.start_bar, s.end_bar, s.kind) for s in with_rhythm if 18 <= s.start_bar <= 21] == [
        (18, 20, "chorus"),
        (21, 32, "verse"),
    ]


def test_rhythm_never_removes_an_event_derived_boundary() -> None:
    # 리듬 구간이 곡 전체를 한 덩이로 덮어도 이벤트가 만든 경계는 그대로다.
    one_block = split_sections(_rhythm_map(SYNTHETIC_EVENTS, [(1, 40, 3)]))
    assert [(s.start_bar, s.end_bar, s.kind) for s in one_block] == [
        (s.start_bar, s.end_bar, s.kind) for s in SYNTHETIC_SECTIONS
    ]
    shifted = split_sections(_rhythm_map(SYNTHETIC_EVENTS, [(1, 12, 1), (13, 25, 2), (26, 40, 3)]))
    assert set(_starts(shifted)) == set(_starts(SYNTHETIC_SECTIONS)) | {13, 26}


def test_a_rhythm_start_that_is_already_a_boundary_adds_nothing() -> None:
    sections = [(1, 6, 1), (7, 8, 2), (9, 17, 3), (18, 35, 4), (36, 40, 5)]
    assert _starts(split_sections(_rhythm_map(SYNTHETIC_EVENTS, sections))) == _starts(
        SYNTHETIC_SECTIONS
    )


def test_without_rhythm_the_boundaries_are_the_event_derived_ones() -> None:
    assert split_sections(_bar_map(SYNTHETIC_EVENTS)) == SYNTHETIC_SECTIONS
    assert "rhythm" not in _bar_map(SYNTHETIC_EVENTS)


def test_every_bar_is_still_covered_once_after_rhythm_boundaries() -> None:
    sections = split_sections(_rhythm_map(SYNTHETIC_EVENTS, RHYTHM_SECTIONS))
    covered = [bar for section in sections for bar in range(section.start_bar, section.end_bar + 1)]
    assert covered == list(range(1, BARS + 1))


def test_each_section_carries_the_d_level_of_the_rhythm_section_holding_its_start_bar() -> None:
    sections = split_sections(_rhythm_map(SYNTHETIC_EVENTS, RHYTHM_SECTIONS))
    assert [(s.start_bar, s.d_level) for s in sections] == [
        (1, 2),
        (7, 2),
        (9, 4),
        (14, 4),
        (18, 4),
        (21, 3),
        (33, 3),
        (36, 3),
        (40, 3),
    ]


def test_a_section_starting_outside_every_rhythm_section_has_no_d_level() -> None:
    # 리듬 구간이 9~20 마디뿐이다. 거기에 시작 마디가 든 구간만 등급을 가진다.
    sections = split_sections(_rhythm_map(SYNTHETIC_EVENTS, [(9, 20, 5)]))
    assert [(s.start_bar, s.d_level) for s in sections] == [
        (1, None),
        (7, None),
        (9, 5),
        (14, 5),
        (18, 5),
        (33, None),
        (36, None),
        (40, None),
    ]


def test_without_rhythm_every_section_d_level_is_none() -> None:
    assert [s.d_level for s in split_sections(_bar_map(SYNTHETIC_EVENTS))] == [None] * 8


def test_segment_section_still_builds_from_three_positional_fields() -> None:
    section = SegmentSection(1, 6, "intro")
    assert (section.start_bar, section.end_bar, section.kind) == (1, 6, "intro")
    assert section.d_level is None
    assert section == (1, 6, "intro", None)
    assert SegmentSection(1, 6, "intro", 3).d_level == 3
    assert SegmentSection._fields[-1] == "d_level"


def test_d_level_stays_out_of_the_draft_and_does_not_reshape_it() -> None:
    # 곡 전체를 덮는 리듬 구간 하나는 경계를 더하지 않으니 초안이 리듬 없는 초안과 같다.
    rhythm_map = _rhythm_map(SYNTHETIC_EVENTS, [(1, 40, 4)])
    layout = _layout()
    with_rhythm = generate_segment_draft(rhythm_map, layout)
    assert with_rhythm == generate_segment_draft(_bar_map(SYNTHETIC_EVENTS), layout)
    assert "d_level" not in json.dumps(with_rhythm, ensure_ascii=False)
    assert set(with_rhythm) == {"tracks", "windows", "bar_range", "source", "note"}


def test_rhythm_boundaries_reach_the_draft_windows() -> None:
    draft = generate_segment_draft(_rhythm_map(SYNTHETIC_EVENTS, RHYTHM_SECTIONS), _layout())
    window_starts = {window["start_bar"] for window in draft["windows"]}
    assert 21 in window_starts
    assert "d_level" not in json.dumps(draft, ensure_ascii=False)
