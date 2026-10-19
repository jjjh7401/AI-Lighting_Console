"""칸 방향 값(``direction``) 단위 시험 — SPEC-LDRHYTHM-001 D4·D8·D9·D10·D11 (리드 지시 2026-10-16).

칸 하나는 구조화된 「방향 값」 하나를 가진다. 라벨·무대 미리보기·프리셋 계획·콘솔 송신은 전부
이 값에서 나온다. 콘솔 접촉 0건 — 순수 계산과 가짜 격자만 쓴다.
"""

from __future__ import annotations

import re

import pytest

from server.audio.bar_map_store import build_bar_map_payload
from server.design.arrange_apply import apply_arrangement_draft
from server.design.arrange_generator import generate_arrangement_draft
from server.design.arrange_policy import ARRANGEMENT_COLOR_NAMES, ArrangementPalette
from server.design.beat_grid import (
    check_app_movement_axis_conflict,
    movement_carried_by_effect,
    normalize_beat_grid_cue,
)
from server.design.beat_grid_edit import apply_beat_grid_edit
from server.design.beat_grid_emit import (
    SongTiming,
    _cue_attribute_commands,
    required_m1_items_for_cue,
)
from server.design.beat_grid_send import unsent_beat_grid_cells
from server.design.cell_direction import (
    BASIC_WORDS,
    SEGMENT_WORDS,
    assign_color_names,
    direction_label,
    label_value_mismatches,
    normalize_direction,
)
from server.web.messages import beat_grid_draft_event

_ASCII_NAME = re.compile(r"[A-Z0-9]+( [A-Z0-9]+)*")
_PINK = (100, 50, 75)


# --- 색 이름 ----------------------------------------------------------------------------------


def _palette_rgbs() -> set[tuple[int, int, int]]:
    palette = ArrangementPalette()
    return {
        palette.verse,
        palette.chorus,
        palette.drop,
        palette.bridge,
        palette.backlight,
        *palette.last_chorus,
    }


def test_arrangement_palette_is_fully_named() -> None:
    missing = [rgb for rgb in _palette_rgbs() if rgb not in ARRANGEMENT_COLOR_NAMES]
    assert missing == []
    assert all(_ASCII_NAME.fullmatch(name) for name in ARRANGEMENT_COLOR_NAMES.values())


def test_standard_palette_names_are_reused_for_the_same_rgb() -> None:
    assert ARRANGEMENT_COLOR_NAMES[(55, 35, 100)] == "LAVENDER"
    assert ARRANGEMENT_COLOR_NAMES[(100, 55, 5)] == "AMBER"
    assert ARRANGEMENT_COLOR_NAMES[(85, 95, 100)] == "COOL WHITE"
    # 표준 팔레트에 없는 팔레트 색 둘은 곡 주석의 콘솔 이름과 같다.
    assert ARRANGEMENT_COLOR_NAMES[_PINK] == "PINK"
    assert ARRANGEMENT_COLOR_NAMES[(40, 65, 95)] == "SKY"


def test_table_rgbs_get_their_table_names() -> None:
    names = assign_color_names(_palette_rgbs())
    assert names[_PINK] == "PINK"
    assert names[(40, 65, 95)] == "SKY"


def test_unknown_rgb_takes_the_nearest_table_name() -> None:
    assert assign_color_names([(99, 50, 75)]) == {(99, 50, 75): "PINK"}
    assert assign_color_names([(2, 18, 98)]) == {(2, 18, 98): "BLUE"}


def test_colliding_nearest_names_get_a_number_suffix() -> None:
    # 정확히 PINK 인 색이 있으면 그 색이 이름을 가진다. 가까운 다른 색들은 번호가 붙는다.
    names = assign_color_names([(99, 50, 75), _PINK, (98, 50, 75)])
    assert names[_PINK] == "PINK"
    assert names[(98, 50, 75)] == "PINK 2"
    assert names[(99, 50, 75)] == "PINK 3"
    assert len(set(names.values())) == 3


def test_names_do_not_depend_on_input_order() -> None:
    rgbs = [(99, 50, 75), _PINK, (98, 50, 75), (13, 77, 41), (0, 0, 0)]
    assert assign_color_names(rgbs) == assign_color_names(reversed(rgbs))
    assert assign_color_names(rgbs) == assign_color_names(rgbs)


def test_every_rgb_gets_a_console_safe_name_and_names_are_unique() -> None:
    rgbs = [(0, 0, 0), (100, 100, 100), (13, 77, 41), (50, 50, 50), (99, 1, 1), (100, 0, 0)]
    names = assign_color_names(rgbs)
    assert set(names) == set(rgbs)
    assert all(_ASCII_NAME.fullmatch(name) for name in names.values())
    assert len(set(names.values())) == len(rgbs)


def test_preferred_names_win_over_hints_and_stay_unique() -> None:
    # 곡 주석의 콘솔 이름이 먼저고, 칸에 이미 실린 이름이 그다음이다. 같은 이름을 다른 색이
    # 또 바라면 번호가 붙는다.
    names = assign_color_names(
        [_PINK, (99, 50, 75)], preferred={_PINK: "LOVE"}, hints={(99, 50, 75): "LOVE"}
    )
    assert names[_PINK] == "LOVE"
    assert names[(99, 50, 75)] == "LOVE 2"


# --- 라벨은 값에서만 --------------------------------------------------------------------------


def _direction(kind: str, *, brightness: int = 100, movement: bool = False) -> dict:
    return {
        "brightness_percent": brightness,
        "color": None,
        "position": None,
        "effect_kind": kind,
        "movement": (
            {
                "shape": "wave",
                "axes": ["Pan"],
                "period_unit": "bar",
                "period_value": 2,
                "phase_spread": None,
            }
            if movement
            else None
        ),
        "entry": {"trigger_beat": 1},
    }


@pytest.mark.parametrize(
    ("kind", "role", "label"),
    [
        ("rest", "back", "—"),
        ("hold", "mover", "정지"),
        ("pulse", "back", "킥 1·2·4박"),
        ("chase", "side", "SIDE-L/R 2·4박 번갈이"),
        ("motion", "mover", "팬 웨이브(한 바퀴 2마디)"),
        ("blind", "effect", "BLIND 2박"),
        ("strobe", "effect", "STROBE 1마디 박마다"),
        ("pre_hit", "effect", "3·4박 전부 비움(예고)"),
        ("static", "key", "FOH 켬"),
        ("static", "wash", "워시"),
        ("static", "audience", "유지"),
    ],
)
def test_segment_label_comes_from_the_direction_value(kind: str, role: str, label: str) -> None:
    assert direction_label(_direction(kind, movement=kind == "motion"), role) == label


def test_basic_wording_is_a_separate_word_set_of_the_same_function() -> None:
    assert direction_label(_direction("pulse"), "back", words=BASIC_WORDS) == "펄스 1·2·4박"
    assert direction_label(_direction("motion", movement=True), "mover", words=BASIC_WORDS) == (
        "팬 웨이브 2마디"
    )
    assert set(SEGMENT_WORDS) >= set(BASIC_WORDS)


def test_the_wave_label_says_the_period_the_cell_actually_has() -> None:
    # 라벨의 주기는 칸의 움직임 값에서 온다 — 박 나누기 규칙으로 주기가 바뀌어도 어긋나지 않는다.
    direction = _direction("motion", movement=True)
    for unit, value, text in (("bar", 1, "1마디"), ("bar", 2, "2마디"), ("beat", 4, "4박")):
        moved = {
            **direction,
            "movement": {**direction["movement"], "period_unit": unit, "period_value": value},
        }
        assert direction_label(moved, "mover") == f"팬 웨이브(한 바퀴 {text})"
    broken = {**direction, "movement": {**direction["movement"], "period_unit": "second"}}
    assert direction_label(broken, "mover") is None


# --- 값 정규화(모양이 틀린 부분은 버린다, 라벨은 읽지 않는다) ---------------------------------


def test_normalize_direction_keeps_a_well_formed_value() -> None:
    raw = {
        "brightness_percent": 80,
        "color": {"name": "PINK", "rgb": [100, 50, 75]},
        "position": {"name": "Center"},
        "effect_kind": "motion",
        "movement": {
            "shape": "wave",
            "axes": ["Pan"],
            "period_unit": "bar",
            "period_value": 2,
            "phase_spread": None,
        },
        "entry": {"trigger_beat": 1},
    }
    assert normalize_direction(raw) == raw


def test_normalize_direction_drops_malformed_parts_only() -> None:
    raw = {
        "brightness_percent": 250,
        "color": {"name": "", "rgb": [100, 50]},
        "position": {"name": 7},
        "effect_kind": "teleport",
        "movement": {"shape": None, "axes": ["Pan"]},
        "entry": {"trigger_beat": "one"},
    }
    assert normalize_direction(raw) == {
        "brightness_percent": None,
        "color": None,
        "position": None,
        "effect_kind": None,
        "movement": None,
        "entry": {"trigger_beat": None},
    }
    assert normalize_direction("킥 1·2·4박") is None
    assert normalize_direction(None) is None


def test_cue_normalization_keeps_direction_and_never_reads_the_label() -> None:
    cue = normalize_beat_grid_cue({"bar": 3, "label": "팬 웨이브(한 바퀴 2마디)"})
    assert "direction" not in cue
    kept = normalize_beat_grid_cue(
        {"bar": 3, "label": "x", "direction": _direction("rest", brightness=0)}
    )
    assert kept["direction"]["effect_kind"] == "rest"


# --- 라벨·값 불일치 ---------------------------------------------------------------------------


def _grid(role: str, cue: dict) -> dict:
    return {
        "tracks": [{"group_name": "G", "layer_role": role, "cues": [normalize_beat_grid_cue(cue)]}]
    }


def _cue_of(kind: str, *, label: str | None = None, **extra) -> dict:
    direction = _direction(
        kind, brightness=0 if kind in ("rest", "pre_hit") else 100, movement=kind == "motion"
    )
    return {
        "bar": 1,
        "label": label if label is not None else direction_label(direction, "mover"),
        "brightness": {"mode": "value", "value_percent": direction["brightness_percent"]},
        "entry": {"trigger_beat": 1},
        "app_movement": direction["movement"],
        "direction": direction,
        **extra,
    }


def test_a_consistent_cell_has_no_mismatch() -> None:
    assert label_value_mismatches(_grid("mover", _cue_of("motion"))) == []
    assert label_value_mismatches(_grid("mover", _cue_of("rest"))) == []


def test_cells_without_a_direction_are_not_judged() -> None:
    grid = _grid(
        "mover",
        {"bar": 1, "label": "아무 글자", "brightness": {"mode": "value", "value_percent": 50}},
    )
    assert label_value_mismatches(grid) == []


def test_label_that_the_values_do_not_produce_is_flagged() -> None:
    reasons = label_value_mismatches(
        _grid("mover", _cue_of("hold", label="팬 웨이브(한 바퀴 2마디)"))
    )
    assert [item["reason"] for item in reasons] == ["라벨이 값과 다름"]


def test_movement_without_motion_kind_is_flagged() -> None:
    cue = _cue_of("hold")
    cue["direction"]["movement"] = _direction("motion", movement=True)["movement"]
    assert any("움직임" in item["reason"] for item in label_value_mismatches(_grid("mover", cue)))


def test_mover_effect_number_without_movement_is_flagged() -> None:
    cue = _cue_of("hold", effect_preset_no="21.8")
    assert any(
        "효과 번호" in item["reason"] for item in label_value_mismatches(_grid("mover", cue))
    )


def test_zero_brightness_and_rest_must_agree() -> None:
    cue = _cue_of("pulse")
    cue["direction"]["brightness_percent"] = 0
    cue["brightness"] = {"mode": "value", "value_percent": 0}
    assert any("밝기" in item["reason"] for item in label_value_mismatches(_grid("back", cue)))


def test_direction_must_agree_with_the_legacy_fields() -> None:
    cue = _cue_of("pulse")
    cue["brightness"] = {"mode": "value", "value_percent": 40}
    assert any("밝기" in item["reason"] for item in label_value_mismatches(_grid("back", cue)))


# --- 송신: 효과 번호와 앱 움직임이 함께 있으면 효과 번호만 낸다 -------------------------------

_TIMING = SongTiming(bpm=128.0, beats_per_bar=4, downbeat_bar1_seconds=0.0)
_MOVEMENT = {"shape": "wave", "axes": ["Pan"], "period_unit": "bar", "period_value": 2}


def _both(**extra) -> dict:
    return normalize_beat_grid_cue(
        {
            "bar": 11,
            "label": "팬 웨이브(한 바퀴 2마디)",
            "brightness": {"mode": "value", "value_percent": 100},
            "app_movement": _MOVEMENT,
            "effect_preset_no": "21.8",
            "effect_kind": "position",
            "movement_effect_no": "21.8",
            **extra,
        }
    )


def test_effect_number_with_app_movement_emits_the_effect_once_and_no_two_step_movement() -> None:
    commands, reason = _cue_attribute_commands(
        _both(position_preset_no="2.31"),
        group_name="MOVER-U",
        group_no=7,
        timing=_TIMING,
        dimmer_attributes={"MOVER-U": ("Dimmer",)},
    )
    assert reason is None
    assert commands.count("Group 7 ; At Preset 21.8") == 1
    assert not [line for line in commands if "Speed" in line or "'Pan'" in line]
    # 위치 번호는 그대로 부른다(움직임이 아니라 자리다).
    assert "Group 7 ; At Preset 2.31" in commands


def test_app_movement_alone_still_emits_the_two_step_movement() -> None:
    cue = normalize_beat_grid_cue(
        {
            "bar": 11,
            "label": "x",
            "brightness": {"mode": "value", "value_percent": 100},
            "app_movement": _MOVEMENT,
        }
    )
    commands, _reason = _cue_attribute_commands(
        cue,
        group_name="MOVER-U",
        group_no=7,
        timing=_TIMING,
        dimmer_attributes={"MOVER-U": ("Dimmer",)},
    )
    assert any("Speed" in line for line in commands)


def test_gate_requires_only_item_4_when_the_effect_carries_the_movement() -> None:
    assert movement_carried_by_effect(_both())
    assert required_m1_items_for_cue(_both()) == frozenset({4})
    assert check_app_movement_axis_conflict(_both()) is None


def test_a_different_effect_number_is_not_the_carrier_and_still_conflicts() -> None:
    cue = _both(effect_preset_no="21.9")  # movement_effect_no 21.8 != 21.9
    assert not movement_carried_by_effect(cue)
    assert check_app_movement_axis_conflict(cue) is not None
    assert required_m1_items_for_cue(cue) == frozenset({4, 5, 7, 9})


# --- 송신 비교: direction 만 새로 생긴 격자는 미반영 칸을 늘리지 않는다 -----------------------


def test_a_grid_that_only_gains_direction_adds_no_unsent_cells() -> None:
    old = _grid(
        "back",
        {"bar": 1, "label": "킥 1·2·4박", "brightness": {"mode": "value", "value_percent": 100}},
    )
    snapshot = {("G", 1): dict(old["tracks"][0]["cues"][0])}
    upgraded = _grid("back", {**old["tracks"][0]["cues"][0], "direction": _direction("pulse")})
    assert unsent_beat_grid_cells(upgraded, snapshot) == []


def test_changing_direction_after_the_snapshot_counts_as_a_changed_cell() -> None:
    first = _grid("back", {"bar": 1, "label": "킥 1·2·4박", "direction": _direction("pulse")})
    snapshot = {("G", 1): dict(first["tracks"][0]["cues"][0])}
    changed = _grid(
        "back", {"bar": 1, "label": "킥 1·2·4박", "direction": _direction("pulse", brightness=60)}
    )
    assert unsent_beat_grid_cells(changed, snapshot) == [{"group_name": "G", "bar": 1}]


# --- 생성기와 전송 ----------------------------------------------------------------------------

_BAR_MAP = build_bar_map_payload(
    [index * 500 for index in range(16 * 4)],
    0,
    bpm=120.0,
    events=[
        {"kind": "kick_entry", "start_bar": 9, "end_bar": 9, "start_beat": 1, "grade": "measured"}
    ],
)
_LAYOUT = [
    {"group_no": 1, "group_no_confirmed": True, "group_name": "BACK", "layer_role": "back"},
    {"group_no": 2, "group_no_confirmed": True, "group_name": "MOVER-U", "layer_role": "mover"},
]


def test_basic_generator_cells_carry_a_direction_that_matches_their_legacy_fields() -> None:
    draft = generate_arrangement_draft(_BAR_MAP, _LAYOUT)
    assert draft["note"] is None
    for track in draft["tracks"]:
        for cue in track["cues"]:
            direction = cue["direction"]
            assert direction["brightness_percent"] == cue["brightness"]["value_percent"]
            assert direction["entry"]["trigger_beat"] == cue["entry"]["trigger_beat"]
            if direction["brightness_percent"]:
                assert direction["color"]["rgb"] == cue["planned_color"]
                assert direction["color"]["name"]
    assert label_value_mismatches({"tracks": draft["tracks"]}) == []


def test_draft_wire_frame_carries_each_cells_direction() -> None:
    draft = generate_arrangement_draft(_BAR_MAP, _LAYOUT)
    event = beat_grid_draft_event(draft_id="d1", draft=draft)
    for wire, track in zip(event["tracks"], draft["tracks"], strict=True):
        for cell, cue in zip(wire["cells"], track["cues"], strict=True):
            assert cell["direction"] == cue["direction"]
            assert cell["label"] == cue["label"]


def test_a_director_kept_cell_takes_the_new_planned_position_in_its_direction_too() -> None:
    # 감독이 고쳐 승인한 칸은 그대로 남지만 계획 위치는 새 초안 값을 얹는다. 방향 값의 위치도
    # 같이 가야 계획 위치와 방향 값이 서로 다른 말을 하지 않는다.
    kept = _cue_of("hold")
    kept["direction"]["position"] = {"name": "Home"}
    kept["planned_position"] = "Home"
    kept["evidence"] = {
        "grade": None,
        "approval": {"by": "supervisor", "date": "2026-10-16", "source": "beat_grid_apply:x"},
    }
    grid = {
        "tracks": [
            {
                "group_no": 4,
                "group_no_confirmed": True,
                "group_name": "MOVER-U",
                "layer_role": "mover",
                "cues": [normalize_beat_grid_cue(kept)],
            }
        ]
    }
    fresh = _cue_of("hold")
    fresh["direction"]["position"] = {"name": "Center"}
    fresh["planned_position"] = "Center"
    draft = {
        "tracks": [
            {
                "group_no": 4,
                "group_no_confirmed": True,
                "group_name": "MOVER-U",
                "layer_role": "mover",
                "cues": [normalize_beat_grid_cue(fresh)],
            }
        ],
        "windows": [],
        "bar_range": {"start": 1, "end": 1},
        "source": "arrangement_segments",
        "note": None,
    }
    updated, _report = apply_arrangement_draft(grid, draft)
    cue = updated["tracks"][0]["cues"][0]
    assert cue["planned_position"] == "Center"
    assert cue["direction"]["position"] == {"name": "Center"}
    assert label_value_mismatches(updated) == []


# --- 감독 편집: 방향 값이 낡은 값으로 남지 않는다 -------------------------------------------


def _edited(changes: dict) -> dict:
    cue = _cue_of("motion", label="팬 웨이브(한 바퀴 2마디)")
    grid = {
        "tracks": [
            {
                "group_no": 4,
                "group_no_confirmed": True,
                "group_name": "MOVER-U",
                "layer_role": "mover",
                "cues": [normalize_beat_grid_cue(cue)],
            }
        ]
    }
    updated, _report = apply_beat_grid_edit(
        grid, bar=1, target="MOVER-U", changes=changes, beats_per_bar=4
    )
    return updated["tracks"][0]["cues"][0]


def test_a_brightness_edit_moves_the_direction_with_it() -> None:
    cue = _edited({"brightness": {"mode": "value", "value_percent": 60, "preset_no": None}})
    assert cue["brightness"]["value_percent"] == 60
    assert cue["direction"]["brightness_percent"] == 60


def test_an_entry_edit_moves_the_direction_with_it() -> None:
    cue = _edited({"entry": {"trigger_beat": 3}})
    assert cue["direction"]["entry"]["trigger_beat"] == 3


def test_a_movement_edit_moves_the_direction_with_it() -> None:
    cue = _edited(
        {
            "app_movement": {
                "shape": "wave",
                "axes": ["Tilt"],
                "period_unit": "bar",
                "period_value": 4,
                "phase_spread": None,
            }
        }
    )
    assert cue["direction"]["movement"]["axes"] == ["Tilt"]
    assert cue["direction"]["movement"]["period_value"] == 4


def test_clearing_the_movement_clears_it_in_the_direction_too() -> None:
    assert _edited({"app_movement": None})["direction"]["movement"] is None


def test_an_edit_of_something_else_leaves_the_direction_alone() -> None:
    cue = _edited({"color_preset_no": "4.7"})
    assert cue["direction"] == _cue_of("motion")["direction"]
