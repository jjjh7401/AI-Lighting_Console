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
from server.audio.bar_map_store import attach_rhythm, build_bar_map_payload, read_bar_map
from server.design import arrange_segments
from server.design.arrange_apply import apply_arrangement_draft
from server.design.arrange_generator import REST_LABEL, UNCONFIRMED_NOTE
from server.design.arrange_policy import ArrangementPalette, ArrangementPolicy
from server.design.arrange_segments import SegmentSection, generate_segment_draft, split_sections
from server.design.beat_grid import LOVE_ATTACK_TITLE, default_beat_grid
from server.design.beat_grid_mib import MIB_MIN_DARK_SECONDS, plan_mib_premoves
from server.design.beat_grid_planned import annotated_cell_colors
from server.design.grid_shape import _layout_item, build_context, compare_grids, pattern_category
from server.design.preset_plan import load_preset_annotations

BARS = 40
FIXTURES_DIR = Path(__file__).parent / "fixtures"
PALETTE = ArrangementPalette()

#: 칸 라벨의 정본 — 기본 격자(love_attack.yaml)와 배치 규칙서(effect-arrangement-rules)의 말이다.
#: 시험이 따로 들고 있어서 구현의 상수를 바꿔도 시험이 따라 바뀌지 않는다.
PULSE_LABEL = "킥 1·2·4박"  # BACK 펄스. 예전 「펄스 1·2·4박」이 아니다.
CHASE_LABEL = "SIDE-L/R 2·4박 번갈이"
MOTION_LABEL = "팬 웨이브(한 바퀴 2마디)"
#: 실측 기록(measured_movements.yaml)이 팬 웨이브를 닫고 틸트 웨이브를 연 무빙
#: (이 리그의 MOVER-D)의 말.
TILT_MOTION_LABEL = "틸트 웨이브(한 바퀴 2마디)"
MOVING_LABELS = frozenset({MOTION_LABEL, TILT_MOTION_LABEL})
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
    SegmentSection(4, 13, "verse"),
    SegmentSection(14, 17, "build"),
    SegmentSection(18, 32, "chorus"),
    SegmentSection(33, 41, "verse"),
    SegmentSection(42, 45, "build"),
    SegmentSection(46, 60, "chorus"),
    SegmentSection(61, 62, "bridge"),
    SegmentSection(63, 66, "drop"),
    SegmentSection(67, 81, "last_chorus"),
    SegmentSection(82, 82, "outro"),  # 곡 끝 브레이크, 뒤에 사건 없음
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
    # 워시 줄은 구간마다 한 칸이라 구간 첫 마디의 주석 색만 칸에 닿는다(리드 결정 2026-10-16).
    section = next(
        s for s in split_sections(_bar_map(SYNTHETIC_EVENTS)) if s.start_bar <= 20 <= s.end_bar
    )
    head = section.start_bar
    colors = {("WASH-ALL", head): (1, 2, 3), ("BACK", lit_back): (4, 5, 6)}
    draft = _draft(SYNTHETIC_EVENTS, planned_colors=colors)
    wash = _cues(draft, "WASH-ALL")
    assert wash[head]["planned_color"] == [1, 2, 3]  # 구간 색을 이긴다
    assert not [bar for bar in wash if head < bar <= section.end_bar]  # 구간 안에서 쪼개지 않는다
    assert _cues(draft, "BACK")[lit_back]["planned_color"] == [4, 5, 6]  # 역광 색을 이긴다
    assert colors == {("WASH-ALL", head): (1, 2, 3), ("BACK", lit_back): (4, 5, 6)}


def test_a_mid_section_planned_color_does_not_split_the_wash_line() -> None:
    section = next(
        s for s in split_sections(_bar_map(SYNTHETIC_EVENTS)) if s.start_bar <= 20 <= s.end_bar
    )
    assert section.start_bar < 20 <= section.end_bar
    plain = _draft(SYNTHETIC_EVENTS)
    draft = _draft(SYNTHETIC_EVENTS, planned_colors={("WASH-ALL", 20): (1, 2, 3)})
    assert _rows(draft, "WASH-ALL") == _rows(plain, "WASH-ALL")
    assert 20 not in _rows(draft, "WASH-ALL")


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
    # 워시 줄은 색이 바뀌는 구간 경계에서만 칸을 나눈다. 7마디 벌스 안에는 칸이 새로 서지 않는다.
    # 도입 뒤 곧바로 들어온 3마디 킥도 벌스라서 1~14마디가 같은 벌스 색 한 칸이다.
    wash = _rows(draft, "WASH-ALL")
    assert [bar for bar in wash if 8 < bar <= 14] == []
    assert wash == [1, 15]
    # 얼굴 빛은 구간 색이 바뀌어도 값이 같아서 한 칸이고, 마지막 구간 첫 마디(15)에 Release 를
    # 받을 같은 값의 끝 칸이 하나 더 선다(인수 D-11).
    assert _rows(draft, "FOH") == [1, 15]


def test_a_lit_rhythm_lane_gets_a_new_cell_at_every_phrase() -> None:
    # 이벤트가 없으면 1~40 마디가 도입 한 구간이고 4마디 창이 열 개다. 주인공(움직임)은 구간 종류가
    # 정하고, 보조층은 창마다 펄스(BACK)와 체이스(SIDE)를 번갈아 맡는다(카드 WT-side-allocation).
    # 켜는 칸은 창(프레이즈) 시작마다 선다 — 기본 격자도 「킥 1·2·4박」을 4마디마다 다시 찍는다.
    draft = _draft([])
    back = _cues(draft, "BACK")
    side = _cues(draft, "SIDE-ALL")
    assert [(bar, back[bar]["label"]) for bar in sorted(back)] == [
        (bar, PULSE_LABEL if bar % 8 == 1 else REST_LABEL) for bar in range(1, BARS + 1, 4)
    ]
    assert [(bar, side[bar]["label"]) for bar in sorted(side)] == [
        (bar, CHASE_LABEL if bar % 8 == 5 else REST_LABEL) for bar in range(1, BARS + 1, 4)
    ]


def test_back_lane_over_the_synthetic_song_is_the_hand_derived_run_list() -> None:
    # 창은 구간 시작부터 4마디씩이고 창 길이에 못 미치는 끝 창은 앞 창에 붙는다(1-6, 7-8, 9-13,
    # 14-17, 18-21, 22-25, 26-32, …). 펄스는 빌드·브릿지(체이스 + 움직임)에서 쉬고, 후렴 18~32 의
    # 둘째 창(22~25)에서는 보조 자리를 체이스에 넘겨 쉰다(카드 WT-side-allocation).
    back = _cues(_draft(SYNTHETIC_EVENTS), "BACK")
    assert [(bar, back[bar]["label"]) for bar in sorted(back)] == [
        (1, PULSE_LABEL),
        (7, PULSE_LABEL),
        (9, PULSE_LABEL),
        (14, REST_LABEL),
        (18, PULSE_LABEL),
        (22, REST_LABEL),
        (26, PULSE_LABEL),
        (33, REST_LABEL),
        (36, PULSE_LABEL),
        (40, PULSE_LABEL),
    ]


@pytest.mark.parametrize("events", [[], SYNTHETIC_EVENTS])
def test_two_consecutive_rows_share_a_plan_only_at_a_phrase_start_of_a_lit_cell(
    events: list[dict],
) -> None:
    draft = _draft(events)
    phrases = {window["start_bar"] for window in draft["windows"]}
    for track in draft["tracks"]:
        for left, right in zip(track["cues"], track["cues"][1:], strict=False):
            if _signature(left) == _signature(right):
                assert right["bar"] in phrases, (track["group_name"], right["bar"])
                assert right["label"] != REST_LABEL
                # 칸 하나뿐인 켜진 줄(FOH)의 끝 칸은 같은 값이다 — Release 를 받으려고 선 칸이다.
                assert track["layer_role"] in ("back", "side", "mover") or (
                    right is track["cues"][-1] and len(track["cues"]) == 2
                )


def test_every_track_has_a_row_at_the_first_bar_and_a_rest_run_is_one_row() -> None:
    draft = _draft(SYNTHETIC_EVENTS)
    for track in draft["tracks"]:
        assert track["cues"][0]["bar"] == 1
    # 강조 줄: 첫 마디의 쉼, 예고, 강조 한 마디, 다시 쉼. 강조 구간(후렴 9·18, 드롭 36, 마지막 후렴
    # 40) 바로 앞 마디(8·17·35·39)마다 예고가 선다. 드롭의 강조는 스트로브 줄이라 36 은 쉼이다.
    assert _rows(draft, "BLIND") == [1, 8, 9, 10, 17, 18, 19, 35, 36, 39, 40]
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
    assert _cues(draft, "BACK")[14]["label"] == REST_LABEL
    assert _cues(draft, "SIDE-ALL")[18]["label"] == REST_LABEL
    assert _cues(draft, "STROBE")[1]["label"] == REST_LABEL


# -- 칸을 나누는 값 --------------------------------------------------------------------------


def test_color_alone_never_splits_a_run_off_the_wash_line() -> None:
    draft = _draft(SYNTHETIC_EVENTS)
    phrases = {window["start_bar"] for window in draft["windows"]}
    for track in draft["tracks"]:
        if track["layer_role"] == "wash":
            continue
        name = track["group_name"]
        for left, right in zip(track["cues"], track["cues"][1:], strict=False):
            # 값이 같은 이웃 칸은 켜는 칸이 프레이즈 시작에서 새로 선 것뿐이다(색 때문이 아니다).
            if _values(left) == _values(right):
                assert right["bar"] in phrases and right["label"] != REST_LABEL, name


def test_a_cell_off_the_wash_line_carries_the_color_of_its_first_bar() -> None:
    draft = _draft(SYNTHETIC_EVENTS)
    # 얼굴 빛(FOH)은 40마디 내내 같은 값이고(끝 칸 40 은 Release 를 받을 같은 값), 앞빛 역할이라
    # 구간과 상관없이 표준 Warm White 다.
    foh = _cues(draft, "FOH")
    assert sorted(foh) == [1, 40]
    assert foh[1]["planned_color"] == foh[40]["planned_color"] == list(PALETTE.key)
    # 체이스 칸 33~35(브릿지)와 36~39(드롭)는 값이 같아도 프레이즈마다 새 칸이고,
    # 칸마다 그 구간 색이다.
    side = _cues(draft, "SIDE-ALL")
    assert side[33]["planned_color"] == list(PALETTE.bridge)
    assert side[36]["planned_color"] == list(PALETTE.drop)


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
    assert foh[1]["planned_color"] == list(PALETTE.key)
    assert foh[20]["planned_color"] == [1, 2, 3]
    assert foh[21]["planned_color"] == list(PALETTE.key)  # 다음 마디는 앞빛 색으로 돌아온다
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


def test_track_without_a_role_joins_the_chase_layer_with_its_own_label() -> None:
    # 카드 WT-side-allocation — 역할을 못 정한 줄도 체이스 층으로 리듬에 들어간다(예전에는 곡 내내
    # 쉼 한 칸이었다). 그 줄은 SIDE 가 아니라서 칸 이름에 SIDE 를 쓰지 않는다.
    layout = [
        {"group_no": 1, "group_no_confirmed": True, "group_name": "EXTRA", "layer_role": None}
    ]
    draft = _draft(SYNTHETIC_EVENTS, layout=layout)
    labels = {cue["label"] for cue in _cues(draft, "EXTRA").values()}
    assert "2·4박 번갈이" in labels
    assert not any("SIDE" in label for label in labels)


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
    # 창 길이에 못 미치는 끝 창(1~6 의 5~6, 9~13 의 13, 26~32 의 30~32)은 앞 창에 붙는다. 구간이
    # 창 하나보다 짧으면(7~8, 40) 그 구간이 곧 창 하나다.
    windows = _draft(SYNTHETIC_EVENTS)["windows"]
    assert [(window["start_bar"], window["end_bar"]) for window in windows] == [
        (1, 6),
        (7, 8),
        (9, 13),
        (14, 17),
        (18, 21),
        (22, 25),
        (26, 32),
        (33, 35),
        (36, 39),
        (40, 40),
    ]
    assert [window["drop"] for window in windows].count(True) == 1


def test_window_bars_come_from_the_policy() -> None:
    draft = _draft([], policy=ArrangementPolicy(window_bars=8))
    back = _cues(draft, "BACK")
    # 8마디 창마다 칸이 서고, 보조층이 창마다 번갈아 펄스가 켜졌다 쉰다.
    assert [(bar, back[bar]["label"]) for bar in sorted(back)] == [
        (1, PULSE_LABEL),
        (9, REST_LABEL),
        (17, PULSE_LABEL),
        (25, REST_LABEL),
        (33, PULSE_LABEL),
    ]


def test_same_kind_sections_get_the_same_layers_and_the_same_moving_mover() -> None:
    # 후렴(9~13, 18~32)과 마지막 후렴(40)은 같은 처리다: 켜는 층이 같고
    # 첫 창에서 같은 무빙이 움직인다.
    draft = _draft(SYNTHETIC_EVENTS)
    firsts = {}
    for window in draft["windows"]:
        firsts.setdefault(window["start_bar"], window)
    chorus_starts = [9, 18, 40]
    assert len({tuple(firsts[bar]["active"]) for bar in chorus_starts}) == 1
    assert {_state(draft, "MOVER-U", bar)["label"] for bar in chorus_starts} == {MOTION_LABEL}
    assert {_state(draft, "MOVER-D", bar)["label"] for bar in chorus_starts} == {HOLD_LABEL}
    # 주인공은 구간 안에서 돌지 않고, 보조층만 창마다 번갈아 든다(카드 WT-side-allocation — 예전에는
    # 보조층도 고정이라 후렴에서 SIDE 가 한 번도 켜지지 않았다).
    assert firsts[18]["active"][0] == firsts[22]["active"][0] == firsts[26]["active"][0]
    assert firsts[18]["active"] == firsts[26]["active"] != firsts[22]["active"]


def test_a_kick_straight_out_of_the_intro_is_a_verse() -> None:
    # 곡의 첫 사건이 도입 뒤 킥 진입이면 비트가 들어오는 벌스다. 블라인드 강조가 서지 않는다.
    sections = split_sections(
        _bar_map([_ev("kick_entry", 5), _ev("build", 12, 15), _ev("kick_entry", 16)])
    )
    assert [(section.start_bar, section.kind) for section in sections] == [
        (1, "intro"),
        (5, "verse"),
        (12, "build"),
        (16, "chorus"),
    ]
    draft = _draft([_ev("kick_entry", 5), _ev("build", 12, 15), _ev("kick_entry", 16)])
    assert _hits(draft, "BLIND", BLIND_LABEL) == [16]


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
    # 움직이는 무빙은 구간 안에서 창마다 번갈고, 구간마다 위 무빙(U)부터 다시 센다. 사전이동(MIB)
    # 쉼 칸이 있는 마디는 그 무빙이 쉬므로 뺀다.
    draft = _draft([])
    turns = []
    for window in draft["windows"]:
        upper = _state(draft, "MOVER-U", window["start_bar"])["label"]
        lower = _state(draft, "MOVER-D", window["start_bar"])["label"]
        assert {upper, lower} in ({MOTION_LABEL, HOLD_LABEL}, {TILT_MOTION_LABEL, HOLD_LABEL})
        turns.append("U" if upper in MOVING_LABELS else "D")
    assert turns == ["U", "D"] * 5


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
        if cue["label"] in MOVING_LABELS:
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
    # 무빙은 위치를 바꾸기 전에 사전이동(MIB) 쉼 칸을 둔다.
    # MOVER-D 는 실측 기록이 팬 웨이브를 닫고 틸트 웨이브를 열어 틸트로 움직인다
    # (probe-moverd D1·D3).
    assert labels["MOVER-U"] == {MOTION_LABEL, HOLD_LABEL, REST_LABEL}
    assert labels["MOVER-D"] == {TILT_MOTION_LABEL, HOLD_LABEL, REST_LABEL}
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
    assert _hits(draft, "BLIND", PRE_HIT_LABEL) == [8, 17, 35, 39]


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
        [_ev("build", 5, 8)],  # 빌드가 곡 끝까지 이어진다
        [_ev("build", 5, 8), _ev("build", 9, 12)],  # 빌드 뒤가 또 빌드
    ],
)
def test_no_notice_unless_an_accent_section_starts_right_after(events: list[dict]) -> None:
    draft = _draft(events)
    for track in draft["tracks"]:
        assert all(cue["label"] != PRE_HIT_LABEL for cue in track["cues"]), track["group_name"]


@pytest.mark.parametrize(
    ("events", "notices"),
    [
        # 빌드 뒤 드롭(8), 드롭 끝 뒤 마지막 후렴(10)
        ([_ev("build", 5, 8), _ev("drop", 9, 10)], [8, 10]),
        # 브리지 뒤 드롭(6 — 곡 후반 62마디 꼴), 드롭 뒤 마지막 후렴(9 — 66마디 꼴)
        ([_ev("break", 5), _ev("drop", 7, 9)], [6, 9]),
        ([_ev("build", 3, 4), _ev("drop", 5, 8)], [4, 8]),
    ],
)
def test_a_notice_stands_before_a_drop_and_before_the_last_chorus_too(
    events: list[dict], notices: list[int]
) -> None:
    assert _hits(_draft(events), "BLIND", PRE_HIT_LABEL) == notices


def test_a_one_bar_accent_section_gets_no_notice_on_its_own_accent_bar() -> None:
    # 드롭이 한 마디(9)이고 바로 마지막 후렴(10)이 오면 9 마디는 드롭 강조라 예고를 두지 않는다.
    draft = _draft([_ev("build", 5, 8), _ev("drop", 9, 9)])
    assert _hits(draft, "BLIND", PRE_HIT_LABEL) == [8]


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
    assert _hits(slow, "BLIND", PRE_HIT_LABEL) == [8, 17, 35, 39]
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


def test_apply_replaces_each_row_inside_the_draft_range_with_its_draft_cells() -> None:
    # 리드 지시 2026-10-16 — 초안 범위 안의 줄은 초안 칸으로 교체한다. 시드 칸을 남기면 그 사이에
    # 새 칸이 끼어 칸이 조각난다. 범위 밖의 칸은 그대로다.
    grid = copy.deepcopy(default_beat_grid(LOVE_ATTACK_TITLE))
    draft = _draft(SYNTHETIC_EVENTS)
    updated, report = apply_arrangement_draft(grid, draft)
    assert any("새로 만들" in line for line in report)
    assert updated["bar_range"] == {"start": 0, "end": BARS}
    first, last = draft["bar_range"]["start"], draft["bar_range"]["end"]
    for draft_track in draft["tracks"]:
        name = draft_track["group_name"]
        before = next(t for t in grid["tracks"] if t["group_name"] == name)["cues"]
        after = next(t for t in updated["tracks"] if t["group_name"] == name)["cues"]
        inside = {cue["bar"] for cue in after if first <= cue["bar"] <= last}
        assert inside == {cue["bar"] for cue in draft_track["cues"]}, name
        outside_before = [cue for cue in before if not first <= cue["bar"] <= last]
        assert [cue for cue in after if not first <= cue["bar"] <= last] == outside_before


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
    # 4마디 킥은 도입 뒤 곧바로 들어오는 벌스라 강조가 없다(기본 격자도 4마디에 BLIND 가 없다).
    assert _hits(draft, "BLIND", BLIND_LABEL) == [18, 46, 67]
    assert _hits(draft, "STROBE", STROBE_LABEL) == [63]
    # 예고는 강조 구간 바로 앞 마디에 선다: 후렴 18·46 앞 17·45, 곡 후반의 드롭 63 앞 62(브리지 끝),
    # 마지막 후렴 67 앞 66(드롭 끝) — 인수 D-07(2026-10-17). 강조 마디는 그대로다.
    assert _hits(draft, "BLIND", PRE_HIT_LABEL) == [17, 45, 62, 66]
    assert _rows(draft, "BLIND") == [0, 17, 18, 19, 45, 46, 47, 62, 63, 66, 67, 68]
    # 워시 줄의 칸은 색이 바뀌는 구간 경계에서만 생긴다. 얼굴 빛은 곡 전체가 같은 값이고, 마지막
    # 구간(아웃트로 82) 첫 마디에 Release 를 받을 끝 칸이 선다.
    starts = {section.start_bar for section in REAL_SECTIONS}
    assert set(_rows(draft, "WASH-ALL")) <= starts
    assert _rows(draft, "FOH") == [0, REAL_SECTIONS[-1].start_bar]


# -- 리듬 블록(rhythm): 구간 경계는 그대로, 구간 등급은 메타데이터 -------------------------


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


#: 합성 곡에 얹는 리듬 구간. 21 마디의 경계만 합성 곡의 구간 시작에 없다(경계로는 쓰이지 않는다).
RHYTHM_SECTIONS = [(1, 8, 2), (9, 20, 4), (21, 40, 3)]


def _starts(sections: list[SegmentSection]) -> list[int]:
    return [section.start_bar for section in sections]


def _triples(sections: list[SegmentSection]) -> list[tuple[int, int, str]]:
    return [(s.start_bar, s.end_bar, s.kind) for s in sections]


def test_rhythm_section_starts_do_not_change_the_event_derived_boundaries() -> None:
    plain = split_sections(_bar_map(SYNTHETIC_EVENTS))
    with_rhythm = split_sections(_rhythm_map(SYNTHETIC_EVENTS, RHYTHM_SECTIONS))
    assert _starts(plain) == [1, 7, 9, 14, 18, 33, 36, 40]
    # 리듬 구간 시작 21 은 구간 시작이 되지 않는다. 후렴 18~32 는 그대로 한 구간이다.
    assert _triples(with_rhythm) == _triples(plain)
    assert (18, 32, "chorus") in _triples(with_rhythm)


@pytest.mark.parametrize(
    "rhythm_sections",
    [
        RHYTHM_SECTIONS,
        [(1, 40, 3)],
        [(1, 12, 1), (13, 25, 2), (26, 40, 3)],
        [(1, 6, 1), (7, 8, 2), (9, 17, 3), (18, 35, 4), (36, 40, 5)],
        [(2, 3, 1), (20, 21, 5), (39, 40, 2)],
    ],
)
def test_any_rhythm_layout_gives_the_same_section_triples_as_no_rhythm(
    rhythm_sections: list[tuple[int, int, int]],
) -> None:
    # 리듬 구간이 곡 전체를 덮든, 사건 경계와 겹치든, 사건 한가운데를 가르든 경계 집합은 같다.
    assert _triples(split_sections(_rhythm_map(SYNTHETIC_EVENTS, rhythm_sections))) == _triples(
        SYNTHETIC_SECTIONS
    )


def test_an_event_section_that_a_rhythm_section_cuts_in_the_middle_stays_one_section() -> None:
    # 후렴 18~32 를 21 마디의 리듬 경계가 가운데서 자른다. 그래도 후렴은 한 구간이다.
    cut = [(1, 20, 2), (21, 40, 5)]
    plain = split_sections(_bar_map(SYNTHETIC_EVENTS))
    with_rhythm = split_sections(_rhythm_map(SYNTHETIC_EVENTS, cut))
    assert _triples(with_rhythm) == _triples(plain)
    assert 21 not in _starts(with_rhythm)
    chorus = [s for s in with_rhythm if s.start_bar == 18]
    assert [(s.start_bar, s.end_bar, s.kind) for s in chorus] == [(18, 32, "chorus")]
    # 등급은 시작 마디 18 을 품은 리듬 구간(1~20, 등급 2)에서 온다. 21 마디의 등급 5 가 아니다.
    assert chorus[0].d_level == 2


def test_without_rhythm_the_boundaries_are_the_event_derived_ones() -> None:
    assert split_sections(_bar_map(SYNTHETIC_EVENTS)) == SYNTHETIC_SECTIONS
    assert "rhythm" not in _bar_map(SYNTHETIC_EVENTS)


def test_every_bar_is_still_covered_once_with_a_rhythm_block() -> None:
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
    # 리듬 구간은 경계를 바꾸지 않으니 초안이 리듬 없는 초안과 같다.
    rhythm_map = _rhythm_map(SYNTHETIC_EVENTS, RHYTHM_SECTIONS)
    layout = _layout()
    with_rhythm = generate_segment_draft(rhythm_map, layout)
    assert with_rhythm == generate_segment_draft(_bar_map(SYNTHETIC_EVENTS), layout)
    assert "d_level" not in json.dumps(with_rhythm, ensure_ascii=False)
    assert set(with_rhythm) == {"tracks", "windows", "bar_range", "source", "note"}


def test_rhythm_boundaries_do_not_reach_the_draft_windows() -> None:
    layout = _layout()
    draft = generate_segment_draft(_rhythm_map(SYNTHETIC_EVENTS, RHYTHM_SECTIONS), layout)
    plain = generate_segment_draft(_bar_map(SYNTHETIC_EVENTS), layout)
    assert draft["windows"] == plain["windows"]
    assert 21 not in {window["start_bar"] for window in draft["windows"]}
    assert "d_level" not in json.dumps(draft, ensure_ascii=False)


# -- 리듬 블록(rhythm): 큰 히트가 블라인드 강조 마디가 된다 ---------------------------------------

#: 합성 곡을 한 덩이로 덮는 리듬 구간. 큰 히트의 효과만 따로 본다.
WHOLE_SONG = [(1, 40, 3)]


def _hit_draft(
    hits: list[tuple[int, int]],
    events: list[dict] | None = None,
    sections: list[tuple[int, int, int]] | None = None,
) -> dict:
    rhythm_map = _rhythm_map(
        SYNTHETIC_EVENTS if events is None else events,
        WHOLE_SONG if sections is None else sections,
        hits,
    )
    return generate_segment_draft(rhythm_map, _layout())


def test_the_blind_cell_moves_to_the_first_big_hit_inside_a_chorus() -> None:
    draft = _hit_draft([(11, 1)])  # 후렴 9~13 의 11 마디에 큰 히트
    assert _hits(draft, "BLIND", BLIND_LABEL) == [11, 18, 40]
    assert _state(draft, "BLIND", 9)["label"] == REST_LABEL
    assert _state(draft, "BLIND", 10)["label"] == REST_LABEL
    assert _state(draft, "BLIND", 12)["label"] == REST_LABEL
    moved = _cues(draft, "BLIND")[11]
    assert moved["brightness"]["value_percent"] == ArrangementPolicy().lit_percent


def test_the_first_big_hit_wins_and_a_hit_in_the_start_bar_changes_nothing() -> None:
    # 입력 순서가 아니라 마디가 앞선 히트가 첫 히트다. 한 마디의 두 히트도 그 마디 하나다.
    draft = _hit_draft([(12, 1), (11, 3), (11, 1), (13, 2)])
    assert _hits(draft, "BLIND", BLIND_LABEL) == [11, 18, 40]
    at_start = _hit_draft([(9, 1), (12, 1), (18, 4), (25, 2)])
    assert _hits(at_start, "BLIND", BLIND_LABEL) == [9, 18, 40]


def test_every_blind_section_takes_its_own_first_big_hit() -> None:
    draft = _hit_draft([(11, 1), (25, 2), (30, 1)])
    assert _hits(draft, "BLIND", BLIND_LABEL) == [11, 25, 40]
    # 마지막 후렴(40 마디 한 칸)에 히트가 있어도 시작 마디 그대로다.
    assert _hits(_hit_draft([(40, 3)]), "BLIND", BLIND_LABEL) == [9, 18, 40]


def test_a_blind_section_without_a_big_hit_keeps_its_start_bar() -> None:
    draft = _hit_draft([(11, 1)])  # 18~32 와 40 에는 히트가 없다
    blind_bars = _hits(draft, "BLIND", BLIND_LABEL)
    assert 18 in blind_bars
    assert 40 in blind_bars
    assert _hits(_hit_draft([]), "BLIND", BLIND_LABEL) == [9, 18, 40]


def test_a_big_hit_in_a_section_that_is_not_blind_changes_nothing() -> None:
    baseline = generate_segment_draft(_bar_map(SYNTHETIC_EVENTS), _layout())
    # 도입(5)·벌스(8)·빌드(15)·브릿지(34)·드롭(37) 안의 히트다. 이웃 후렴으로 번지지도 않는다.
    draft = _hit_draft([(5, 1), (8, 2), (15, 1), (34, 3), (37, 1)])
    assert draft == baseline


def test_a_big_hit_in_the_last_chorus_of_a_long_tail_moves_its_blind_cell() -> None:
    events = [_ev("drop", 20, 21)]  # 드롭 20~21, 마지막 후렴 22~40
    draft = _hit_draft([(30, 1)], events=events)
    assert _hits(draft, "BLIND", BLIND_LABEL) == [30]
    assert _hits(_hit_draft([], events=events), "BLIND", BLIND_LABEL) == [22]


def test_only_the_blind_line_changes_when_the_emphasis_moves() -> None:
    baseline = generate_segment_draft(_bar_map(SYNTHETIC_EVENTS), _layout())
    draft = _hit_draft([(11, 1), (25, 2)])
    assert draft["windows"] == baseline["windows"]
    assert draft["bar_range"] == baseline["bar_range"]
    for track, base in zip(draft["tracks"], baseline["tracks"], strict=True):
        if track["group_name"] == "BLIND":
            assert track != base
        else:
            assert track == base, track["group_name"]


def test_the_drop_start_strobe_and_the_pre_hit_notice_stay_where_they_were() -> None:
    draft = _hit_draft([(11, 1), (25, 2), (38, 1)])
    assert _hits(draft, "STROBE", STROBE_LABEL) == [36]
    assert _hits(draft, "BLIND", PRE_HIT_LABEL) == [8, 17, 35, 39]
    # 예고 칸은 강조 구간 바로 앞 마디에 서고 큰 히트가 구간 안 어디에 있어도 움직이지 않는다.
    on_start = _hit_draft([(18, 1)])
    assert _hits(on_start, "BLIND", PRE_HIT_LABEL) == [8, 17, 35, 39]
    assert _hits(on_start, "BLIND", BLIND_LABEL) == [9, 18, 40]


def test_a_big_hit_in_a_chorus_that_a_rhythm_section_cuts_belongs_to_that_chorus() -> None:
    # 리듬 구간 21 은 후렴(18~32)을 가르지 못한다. 25 마디 히트는 같은 후렴 안이라 그 후렴의
    # 블라인드 마디가 된다. 20 마디 히트도 마찬가지다.
    draft = _hit_draft([(25, 1)], sections=RHYTHM_SECTIONS)
    assert _hits(draft, "BLIND", BLIND_LABEL) == [9, 25, 40]
    inside = _hit_draft([(20, 1)], sections=RHYTHM_SECTIONS)
    assert _hits(inside, "BLIND", BLIND_LABEL) == [9, 20, 40]


def test_without_a_big_hit_the_draft_equals_the_one_without_rhythm() -> None:
    baseline = generate_segment_draft(_bar_map(SYNTHETIC_EVENTS), _layout())
    assert _hit_draft([]) == baseline
    assert _hits(baseline, "BLIND", BLIND_LABEL) == [9, 18, 40]


# -- 이동 전 어둠(MIB) ------------------------------------------------------------------------


class _Clock:
    """마디 지도의 마디 시작 시각(초)을 주는 시계 — 반영 단계 MIB 계획기에 넣는다."""

    def __init__(self, bar_map: dict) -> None:
        self._seconds = {bar["bar"]: bar["start_ms"] / 1000 for bar in bar_map["bars"]}

    def bar_start_seconds(self, bar: int) -> float | None:
        return self._seconds.get(bar)


def _mib(bar_map: dict) -> tuple[int, list[str]]:
    """초안의 무빙 줄을 반영 단계 MIB 계획기(``plan_mib_premoves``)에 넣는다.

    돌려주는 값은 (사전이동 수, 불가 사유 목록)이다.
    """
    draft = generate_segment_draft(bar_map, _layout())
    premoves = 0
    notes: list[str] = []
    for track in draft["tracks"]:
        if track["layer_role"] != "mover":
            continue
        # 계획 위치 이름을 위치 번호 자리에 넣는다
        # — 계획 단계가 이름마다 번호 하나를 붙이는 것과 같다.
        cues = [{**cue, "position_preset_no": cue.get("planned_position")} for cue in track["cues"]]
        made, why = plan_mib_premoves(cues, _Clock(bar_map))
        premoves += len(made)
        notes += why
    return premoves, notes


@pytest.mark.parametrize("song", ["real", "synthetic"])
def test_every_mover_position_change_can_premove_in_the_dark(song: str) -> None:
    # 무빙이 위치를 바꾸는 칸 앞에는 사전이동이 가능한 쉼이 있다. 쉼을 둘 수 없으면 그 구간에서는
    # 위치를 바꾸지 않는다. 그래서 반영 단계 MIB 계획기가 「불가」를 하나도 내지 않는다(main 은 실제
    # 곡에서 15건이었다).
    bar_map = _real_love_attack() if song == "real" else _bar_map(SYNTHETIC_EVENTS)
    premoves, notes = _mib(bar_map)
    assert notes == []
    assert premoves >= 2


def test_movers_are_never_darkened_inside_a_chorus_or_a_drop() -> None:
    bar_map = _real_love_attack()
    draft = generate_segment_draft(bar_map, _layout())
    hits = [s for s in split_sections(bar_map) if s.kind in ("chorus", "last_chorus", "drop")]
    for name in ("MOVER-U", "MOVER-D"):
        for section in hits:
            for bar in range(section.start_bar, section.end_bar + 1):
                assert _state(draft, name, bar)["label"] != REST_LABEL, (name, bar)


@pytest.mark.parametrize("bpm", [90.0, 120.0, 160.0])
def test_the_pre_move_rest_is_long_enough_for_the_move_at_the_song_tempo(bpm: float) -> None:
    # 쉼 길이는 곡의 마디 시각에서 잰다(마디 수 상수가 아니다).
    beat_ms = 60000 / bpm
    bar_map = build_bar_map_payload(
        [round(index * beat_ms) for index in range(BARS * 4)], 0, bpm=bpm, events=SYNTHETIC_EVENTS
    )
    seconds = {bar["bar"]: bar["start_ms"] / 1000 for bar in bar_map["bars"]}
    draft = generate_segment_draft(bar_map, _layout())
    rests = 0
    for track in draft["tracks"]:
        if track["layer_role"] != "mover":
            continue
        cues = track["cues"]
        for rest, after in zip(cues, cues[1:], strict=False):
            if rest["label"] == REST_LABEL and after["label"] != REST_LABEL:
                rests += 1
                dark = seconds[after["bar"]] - seconds[rest["bar"] + 1]
                assert dark >= MIB_MIN_DARK_SECONDS, (track["group_name"], rest["bar"])
    assert rests >= 1


def test_the_app_path_love_attack_draft_is_similar_to_the_hand_grid() -> None:
    # 운영 경로(구간 생성기 → 빈 골격에 적용)로 만든 LOVE ATTACK 격자가 판정기에서 「비슷함」이다.
    # 콘솔 프리셋 계획이 계획 색을 색 번호로 바꾼 뒤에도 같다
    # (⑥ 은 번호의 유무가 아니라 바뀜을 센다).
    with (FIXTURES_DIR / "love_attack_shape_timeline.json").open(encoding="utf-8") as handle:
        timeline = json.load(handle)
    base = default_beat_grid(LOVE_ATTACK_TITLE)
    annotations = load_preset_annotations(LOVE_ATTACK_TITLE)
    layout = [_layout_item(track) for track in base["tracks"]]
    draft = generate_segment_draft(
        read_bar_map(timeline), layout, planned_colors=annotated_cell_colors(annotations)
    )
    skeleton = {
        "song_title": base["song_title"],
        "bar_range": dict(base["bar_range"]),
        "tracks": [{**item, "cues": []} for item in layout],
        "scene_memos": [],
        "source": "skeleton",
    }
    candidate, _ = apply_arrangement_draft(skeleton, draft)
    numbered = copy.deepcopy(candidate)
    numbers: dict = {}
    for track in numbered["tracks"]:
        for cue in track["cues"]:
            if cue.get("planned_color") and cue["label"] != REST_LABEL:
                key = (track["group_name"], tuple(cue["planned_color"]))
                cue["color_preset_no"] = numbers.setdefault(key, f"4.{len(numbers) + 1}")
    context = build_context(timeline, annotations)
    for grid in (candidate, numbered):
        report = compare_grids(base, grid, context)
        assert report.verdict == "비슷함", report.failing


def test_a_final_break_section_with_nothing_after_it_is_the_outro() -> None:
    # 곡 끝 구간이 브레이크로 시작하고 뒤에 사건이 없으면 아웃트로다(실제 곡 82마디 꼴).
    sections = split_sections(_bar_map([_ev("kick_entry", 4), _ev("break", 9)]))
    assert sections[-1].kind == "outro"


def test_a_break_followed_by_a_drop_is_still_a_bridge_not_an_outro() -> None:
    sections = split_sections(
        _bar_map([_ev("kick_entry", 4), _ev("break", 9), _ev("drop", 10, 11)])
    )
    assert "outro" not in [section.kind for section in sections]


# -- 트래킹(인수 D-11): 첫 칸 Block · 끝 칸 Release · 구간 첫 칸 Track · 그 밖 Cue Only ----------


def _tracking(draft: dict, name: str) -> list[tuple[int, object]]:
    return [
        (int(cue["bar"]), (cue.get("entry") or {}).get("tracking"))
        for track in draft["tracks"]
        if track["group_name"] == name
        for cue in track["cues"]
    ]


def test_every_line_blocks_its_first_cell_and_releases_its_last() -> None:
    draft = generate_segment_draft(_real_love_attack(), _layout())
    for track in draft["tracks"]:
        values = [(cue.get("entry") or {}).get("tracking") for cue in track["cues"]]
        assert values[0] == "Block", track["group_name"]
        if len(values) > 1:
            assert values[-1] == "Release", track["group_name"]


def test_section_starts_track_and_other_cells_are_cue_only() -> None:
    bar_map = _real_love_attack()
    starts = {section.start_bar for section in split_sections(bar_map)}
    draft = generate_segment_draft(bar_map, _layout())
    for track in draft["tracks"]:
        for cue in track["cues"][1:-1]:
            expected = None if int(cue["bar"]) in starts else "Cue Only"
            got = (cue.get("entry") or {}).get("tracking")
            assert got == expected, (track["group_name"], cue["bar"])
    # BLIND: 첫 칸(0) Block, 예고·쉼은 Cue Only, 강조가 구간 첫 마디면 Track, 끝 칸(68) Release.
    assert _tracking(draft, "BLIND") == [
        (0, "Block"),
        (17, "Cue Only"),
        (18, None),
        (19, "Cue Only"),
        (45, "Cue Only"),
        (46, None),
        (47, "Cue Only"),
        (62, "Cue Only"),
        (63, None),
        (66, "Cue Only"),
        (67, None),
        (68, "Release"),
    ]
    # 값이 하나뿐인 줄(FOH)도 끝 칸이 Release 다 — full3 D-11 「FOH 만 Release 없음」.
    assert _tracking(draft, "FOH") == [(0, "Block"), (82, "Release")]
    assert all(
        track["cues"][-1]["entry"].get("tracking") == "Release"
        for track in draft["tracks"]
        if len(track["cues"]) > 1
    )
    lit_lines = [
        t for t in draft["tracks"] if any(c["brightness"]["value_percent"] for c in t["cues"])
    ]
    assert all(len(track["cues"]) > 1 for track in lit_lines)


def test_every_line_ends_dark_with_release_at_the_last_bar() -> None:
    """4차 전체 실행 D-11 — 끝 칸이 켜진 값이면 Release 를 받아도 그 칸이 쥔 값(밝기)은 남아서
    곡 끝 Off(g 181.1)까지 3 초 켜져 있었다(MOVER-D 82마디 DIM-100, FOH·WASH·BACK·MOVER-U 도 같은
    모양). 켜진 채 끝나는 줄은 곡의 마지막 마디에 꺼진 끝 칸을 받는다. 이미 꺼진 채 끝나는 줄은
    그대로다."""
    bar_map = _real_love_attack()
    last_bar = max(int(entry["bar"]) for entry in bar_map["bars"])
    draft = generate_segment_draft(bar_map, _layout())
    for track in draft["tracks"]:
        end = track["cues"][-1]
        assert end["brightness"]["value_percent"] == 0, (track["group_name"], end["bar"])
        assert end["entry"].get("tracking") == "Release", track["group_name"]
        lit_before = [c for c in track["cues"][:-1] if c["brightness"]["value_percent"]]
        assert lit_before, track["group_name"]  # 곡 안에서 켜진 칸은 그대로 남는다
    # 켜진 채 끝나던 줄은 마지막 마디(82)에서 꺼지고, 꺼진 채 끝나던 줄은 끝 칸이 그대로다.
    assert _rows(draft, "FOH") == [0, last_bar]
    assert _rows(draft, "MOVER-D")[-1] == last_bar
    assert _rows(draft, "BLIND")[-1] == 68


def test_tracking_survives_applying_the_draft_to_the_grid() -> None:
    # 적용이 entry.tracking 을 지우면 반영 명령에 Block·Release·/CueOnly 가 안 나간다.
    draft = generate_segment_draft(_real_love_attack(), _layout())
    base = copy.deepcopy(default_beat_grid(LOVE_ATTACK_TITLE))
    grid, _report = apply_arrangement_draft(base, draft)
    for track in draft["tracks"]:
        applied = {
            int(cue["bar"]): cue["entry"].get("tracking")
            for t in grid["tracks"]
            if t["group_name"] == track["group_name"]
            for cue in t["cues"]
        }
        for cue in track["cues"]:
            assert applied[int(cue["bar"])] == (cue.get("entry") or {}).get("tracking")


# 1018 기록(aura): BACK·SIDE 줄에 계획 위치가 없으면 헤드가 가운데에 머물러 빔이 천장으로 간다.
# 조준할 수 있는 줄(기종에 Pan·Tilt 있음 — 줄의 ``pan_tilt``)의 켜진 칸에만
# 무대 중앙 기본 위치를 준다.
def _with_pan_tilt(layout: list[dict], names: set[str]) -> list[dict]:
    return [
        {**track, "pan_tilt": True} if track["group_name"] in names else track for track in layout
    ]


def test_a_back_or_side_line_that_can_aim_gets_the_stage_facing_default_position() -> None:
    plain = _draft(SYNTHETIC_EVENTS)
    aimed = _draft(SYNTHETIC_EVENTS, layout=_with_pan_tilt(_layout(), {"BACK", "SIDE-ALL"}))
    for name in ("BACK", "SIDE-ALL"):
        assert all(cue.get("planned_position") is None for cue in _cues(plain, name).values())
        cues = list(_cues(aimed, name).values())
        lit = [cue for cue in cues if cue["brightness"]["value_percent"] > 0]
        assert lit, f"{name} 줄에 켜진 칸이 없어 시험이 빈 말이 된다"
        assert {cue.get("planned_position") for cue in lit} == {"Center"}
        assert all(
            cue.get("planned_position") is None
            for cue in cues
            if cue["brightness"]["value_percent"] == 0
        )


def test_lines_that_cannot_aim_and_the_other_moving_lines_keep_their_positions() -> None:
    plain = _draft(SYNTHETIC_EVENTS)
    aimed = _draft(SYNTHETIC_EVENTS, layout=_with_pan_tilt(_layout(), {"BACK", "SIDE-ALL"}))
    for name in ("MOVER-U", "MOVER-D", "FOH", "WASH-ALL", "BLIND", "STROBE"):
        assert _cues(aimed, name) == _cues(plain, name)
