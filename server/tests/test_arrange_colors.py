"""배치 초안 칸의 계획 색 시험 — SPEC-LDRHYTHM-001 「자동 배치 계획 색」.

켜는 칸마다 계획 색(콘솔 퍼센트 RGB)이 붙는다. 계획 색은 콘솔 값이 아니라 화면 표시용이라
「반영 이후 바뀐 칸」 비교와 콘솔 묶음에 닿지 않는다. 색 우선순위는 곡별 주석 색(칸 하나) >
역광 역할(BACK) > 앞빛 역할(FOH, 표준 Warm White) > 구간 색이다. 쉬는 칸(「—」)에는 색이 없다.

합성 마디 지도(4/4, 박 500밀리초, 40마디)와 LOVE ATTACK 기본 격자의 트랙 구성으로 잡는다.

후렴 판정은 곡 안의 상대 에너지로 한다(가장 조용한 구간 0, 가장 큰 구간 1). 절대 기준이면
LOVE ATTACK 의 모든 구간이 후렴이 되어 벌스가 하나도 없었다. 그 회귀는 실제 마디 음량 픽스처
시험이 지킨다.
"""

from __future__ import annotations

import copy
import dataclasses
import json
from pathlib import Path

import pytest

from server.audio.bar_map_store import build_bar_map_payload
from server.design.arrange_apply import apply_arrangement_draft
from server.design.arrange_generator import REST_LABEL, generate_arrangement_draft
from server.design.arrange_policy import ArrangementPalette, ArrangementPolicy
from server.design.arrange_segments import generate_segment_draft
from server.design.beat_grid import LOVE_ATTACK_TITLE, default_beat_grid
from server.design.beat_grid_planned import annotated_cell_colors, attach_planned_marks
from server.design.beat_grid_send import beat_grid_cell_snapshot, unsent_beat_grid_cells
from server.design.color_names import COLOR_PALETTE_SEQUENCE
from server.design.preset_plan import load_preset_annotations

BARS = 40
FIXTURES_DIR = Path(__file__).parent / "fixtures"
REAL_BAR_FEATURES = FIXTURES_DIR / "love_attack_bar_features_real.json"
PALETTE = ArrangementPalette()
KICK_AT_5 = [{"kind": "kick_entry", "start_bar": 5, "end_bar": 5, "start_beat": 1}]
KICK_AT_9 = [{"kind": "kick_entry", "start_bar": 9, "end_bar": 9, "start_beat": 1}]
KICK_AT_13 = [{"kind": "kick_entry", "start_bar": 13, "end_bar": 13, "start_beat": 1}]
DROP_17_18 = [{"kind": "drop", "start_bar": 17, "end_bar": 18, "start_beat": 1}]
BREAK_25_26 = [{"kind": "break", "start_bar": 25, "end_bar": 26, "start_beat": 1}]


def _bar_map(events: list[dict] | None = None, energy: dict[int, float] | None = None) -> dict:
    beats = [index * 500 for index in range(BARS * 4)]
    return build_bar_map_payload(beats, 0, bpm=120.0, events=events or [], bar_energy=energy)


def _layout() -> list[dict]:
    return list(default_beat_grid(LOVE_ATTACK_TITLE)["tracks"])


def _draft(
    events: list[dict] | None = None,
    *,
    energy: dict[int, float] | None = None,
    policy: ArrangementPolicy | None = None,
    planned_colors: dict | None = None,
) -> dict:
    return generate_arrangement_draft(
        _bar_map(events, energy), _layout(), policy, planned_colors=planned_colors
    )


def _cues(draft: dict, name: str) -> dict[int, dict]:
    track = next(item for item in draft["tracks"] if item["group_name"] == name)
    return {cue["bar"]: cue for cue in track["cues"]}


def _wash(draft: dict, bar: int) -> list[int] | None:
    """WASH-ALL 은 어느 구간에서나 「유지」로 켜 두는 칸이라 구간 색을 그대로 보인다."""
    return _cues(draft, "WASH-ALL")[bar].get("planned_color")


def _is_rgb(value: object) -> bool:
    return (
        isinstance(value, list)
        and len(value) == 3
        and all(type(channel) is int and 0 <= channel <= 100 for channel in value)
    )


# -- a. 켜는 칸마다 색, 쉬는 칸은 색 없음 ----------------------------------------------------


def test_every_lit_cell_has_a_valid_planned_color_and_rest_cells_have_none() -> None:
    draft = _draft(KICK_AT_9 + DROP_17_18 + BREAK_25_26)
    lit = rest = 0
    for track in draft["tracks"]:
        for cue in track["cues"]:
            if cue["label"] == REST_LABEL:
                rest += 1
                assert "planned_color" not in cue
            else:
                lit += 1
                assert _is_rgb(cue["planned_color"]), (track["group_name"], cue["bar"])
    assert lit > 0 and rest > 0


# -- b. 구간 종류별 색 -----------------------------------------------------------------------


def test_verse_window_uses_the_verse_color() -> None:
    draft = _draft(KICK_AT_9 + DROP_17_18 + BREAK_25_26)
    assert _wash(draft, 2) == list(PALETTE.verse)
    assert _wash(draft, 13) == list(PALETTE.verse)


def test_window_with_a_kick_entry_uses_the_chorus_color() -> None:
    draft = _draft(KICK_AT_9 + DROP_17_18 + BREAK_25_26)
    assert _wash(draft, 9) == list(PALETTE.chorus)
    assert _wash(draft, 11) == list(PALETTE.chorus)


def test_drop_window_uses_the_drop_color() -> None:
    draft = _draft(KICK_AT_9 + DROP_17_18 + BREAK_25_26)
    assert _wash(draft, 17) == list(PALETTE.drop)
    assert _wash(draft, 19) == list(PALETTE.drop)


def test_break_window_uses_the_bridge_color() -> None:
    draft = _draft(KICK_AT_9 + DROP_17_18 + BREAK_25_26)
    assert _wash(draft, 25) == list(PALETTE.bridge)
    assert _wash(draft, 27) == list(PALETTE.bridge)


def test_drop_beats_break_when_a_window_has_both() -> None:
    events = [
        {"kind": "drop", "start_bar": 17, "end_bar": 17, "start_beat": 1},
        {"kind": "break", "start_bar": 18, "end_bar": 18, "start_beat": 1},
    ]
    assert _wash(_draft(events), 17) == list(PALETTE.drop)


def test_a_clearly_louder_window_becomes_a_chorus_without_a_kick_entry() -> None:
    # 두 구간 모두 옛 절대 기준(0.6)을 넘는다. 곡 안에서 상대적으로 큰 쪽만 후렴이다.
    energy = {bar: 0.95 for bar in range(8, 12)} | {bar: 0.75 for bar in range(12, 16)}
    draft = _draft(energy=energy)
    assert _wash(draft, 9) == list(PALETTE.chorus)
    assert _wash(draft, 13) == list(PALETTE.verse)


def test_a_quieter_window_stays_a_verse_but_a_kick_entry_still_makes_it_a_chorus() -> None:
    energy = {bar: 0.9 for bar in range(8, 12)} | {bar: 0.2 for bar in range(12, 16)}
    assert _wash(_draft(energy=energy), 13) == list(PALETTE.verse)
    # 가장 조용한 구간(위치 0)이라도 킥 진입이 있으면 후렴이다.
    assert _wash(_draft(KICK_AT_13, energy=energy), 13) == list(PALETTE.chorus)


def test_bars_without_energy_are_ignored_not_counted_as_zero() -> None:
    # 8~11 마디는 두 마디만 에너지(0.8)가 있고 12~15 마디는 모두 0.4 다. 없는 마디를 0 으로 세면
    # 앞 구간 평균이 0.4 로 떨어져 두 구간이 같아지고(평평한 곡) 후렴이 사라진다.
    energy = {8: 0.8, 9: 0.8} | {bar: 0.4 for bar in range(12, 16)}
    draft = _draft(energy=energy)
    assert _wash(draft, 9) == list(PALETTE.chorus)
    assert _wash(draft, 13) == list(PALETTE.verse)
    # 에너지가 한 마디도 없는 구간은 곡 안 위치를 정할 수 없어 벌스다.
    assert _wash(draft, 2) == list(PALETTE.verse)


@pytest.mark.parametrize("level", [0.1, 0.7, 1.0])
def test_a_flat_song_has_no_energy_based_chorus_and_does_not_divide_by_zero(level: float) -> None:
    # 0.1 과 0.7 은 3마디 구간과 4마디 구간의 평균이 부동소수 오차로 미세하게 달라진다.
    # 그래도 평평한 곡이라 어느 구간도 후렴이 되면 안 된다.
    energy = {bar: level for bar in range(1, BARS + 1)}
    draft = _draft(energy=energy)
    assert {tuple(_wash(draft, bar)) for bar in range(1, BARS + 1)} == {PALETTE.verse}


def test_the_cut_is_the_policy_chorus_energy_cut_and_a_window_at_the_cut_is_a_verse() -> None:
    # 세 구간의 에너지가 0.25 / 0.5 / 0.75 라 가운데 구간의 상대 위치는 정확히 0.5 다.
    energy = (
        {bar: 0.25 for bar in range(8, 12)}
        | {bar: 0.5 for bar in range(12, 16)}
        | {bar: 0.75 for bar in range(16, 20)}
    )
    assert _wash(_draft(energy=energy), 13) == list(PALETTE.verse)  # 0.5 는 기준 0.5 를 넘지 않는다
    lowered = _draft(energy=energy, policy=ArrangementPolicy(chorus_energy_cut=0.4))
    assert _wash(lowered, 13) == list(PALETTE.chorus)
    assert _wash(lowered, 9) == list(PALETTE.verse)  # 가장 조용한 구간(위치 0)은 기준을 낮춰도 벌스
    raised = _draft(energy=energy, policy=ArrangementPolicy(chorus_energy_cut=0.9))
    assert _wash(raised, 17) == list(PALETTE.chorus)
    assert _wash(raised, 13) == list(PALETTE.verse)


def test_real_love_attack_bar_energies_give_both_verse_and_chorus_windows() -> None:
    """실제 LOVE ATTACK 마디 음량으로 초안을 만들면 벌스 구간과 후렴 구간이 둘 다 나온다.

    옛 절대 기준(0.6)에서는 4마디 구간 평균이 전부 0.710 ~ 1.000 이라 모든 구간이 후렴이었다.
    """
    with REAL_BAR_FEATURES.open(encoding="utf-8") as handle:
        fixture = json.load(handle)
    rows = fixture["bar_features"]
    # 마디 지도의 에너지는 0~1 이라 1.0 을 넘는 음량은 1.0 으로 자른다.
    energy = {int(row["bar"]): min(1.0, float(row["volume_norm"])) for row in rows}
    offset = int(fixture["first_beat_offset"])
    beats = [index * 500 for index in range(offset + 4 * len(rows))]
    bar_map = build_bar_map_payload(beats, offset, bpm=120.0, events=[], bar_energy=energy)
    draft = generate_arrangement_draft(bar_map, _layout())
    colors = {tuple(cue["planned_color"]) for cue in _cues(draft, "WASH-ALL").values()}
    assert {PALETTE.verse, PALETTE.chorus} <= colors


# -- c. 마지막 드롭 뒤 돌림 ------------------------------------------------------------------


def test_windows_after_the_last_drop_cycle_through_the_last_chorus_colors() -> None:
    draft = _draft(DROP_17_18)
    after = [_wash(draft, bar) for bar in (20, 24, 28, 32)]
    cycle = [list(color) for color in PALETTE.last_chorus]
    assert after[:3] == cycle
    assert after[3] == cycle[0]
    assert len({tuple(color) for color in after}) >= 2


def test_a_bridge_after_the_last_drop_does_not_use_up_a_last_chorus_color() -> None:
    # 25~26 마디 브레이크가 든 구간(24~27)은 브릿지라 마지막 후렴이 아니다. 돌림 차례를 쓰지 않는다.
    draft = _draft(DROP_17_18 + BREAK_25_26)
    cycle = [list(color) for color in PALETTE.last_chorus]
    assert _wash(draft, 20) == cycle[0]
    assert _wash(draft, 25) == list(PALETTE.bridge)
    assert [_wash(draft, bar) for bar in (28, 32, 36)] == [cycle[1], cycle[2], cycle[0]]


def test_windows_before_the_last_drop_do_not_use_the_last_chorus_cycle() -> None:
    draft = _draft(KICK_AT_9 + DROP_17_18)
    assert _wash(draft, 13) == list(PALETTE.verse)


def test_no_drop_means_no_last_chorus() -> None:
    draft = _draft()
    assert {tuple(_wash(draft, bar)) for bar in (2, 14, 30, 38)} == {PALETTE.verse}


# -- d. 역광은 모든 구간에서 차가운 하늘색 ----------------------------------------------------


@pytest.mark.parametrize(
    "events",
    [[], KICK_AT_5, DROP_17_18, BREAK_25_26, KICK_AT_9 + DROP_17_18 + BREAK_25_26],
)
def test_lit_back_cells_use_the_backlight_color_in_every_section(events: list[dict]) -> None:
    draft = _draft(events)
    lit = [cue for cue in _cues(draft, "BACK").values() if cue["label"] != REST_LABEL]
    assert lit
    for cue in lit:
        assert cue["planned_color"] == list(PALETTE.backlight)


def test_backlight_is_a_cool_color() -> None:
    red, green, blue = PALETTE.backlight
    assert blue == max(red, green, blue)
    assert red == min(red, green, blue)


def test_back_cells_differ_from_the_section_color_somewhere() -> None:
    # 역광이 구간 색을 따라가지 않는다는 증거 — 같은 마디에서 워시와 역광 색이 다른 칸이 있다.
    draft = _draft(KICK_AT_9 + DROP_17_18 + BREAK_25_26)
    back, wash = _cues(draft, "BACK"), _cues(draft, "WASH-ALL")
    differing = [
        bar
        for bar, cue in back.items()
        if cue["label"] != REST_LABEL and cue["planned_color"] != wash[bar]["planned_color"]
    ]
    assert len(differing) >= 3


# -- e. 정책이 기본 팔레트를 덮는다 ------------------------------------------------------------


def test_a_custom_palette_changes_the_verse_cells() -> None:
    policy = ArrangementPolicy(palette=ArrangementPalette(verse=(1, 2, 3)))
    draft = _draft(KICK_AT_9, policy=policy)
    assert _wash(draft, 2) == [1, 2, 3]
    assert _wash(draft, 9) == list(PALETTE.chorus)


def test_the_default_palette_values_are_the_director_agreed_ones() -> None:
    assert PALETTE.verse == (55, 35, 100)
    assert PALETTE.chorus == (100, 50, 75)
    assert PALETTE.drop == (100, 55, 5)
    assert PALETTE.bridge == (85, 95, 100)
    assert PALETTE.backlight == (40, 65, 95)
    assert PALETTE.last_chorus == ((100, 50, 75), (55, 35, 100), (100, 55, 5))
    assert ArrangementPolicy().chorus_energy_cut == 0.5


def test_palette_and_policy_reject_bad_values() -> None:
    with pytest.raises(ValueError):
        ArrangementPalette(verse=(0, 0, 101))
    with pytest.raises(ValueError):
        ArrangementPalette(verse=(0, 0))  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        ArrangementPalette(verse=(True, 0, 0))  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        ArrangementPalette(last_chorus=())
    with pytest.raises(ValueError):
        ArrangementPolicy(chorus_energy_cut=1.1)
    with pytest.raises(ValueError):
        ArrangementPolicy(chorus_energy_cut=-0.1)
    with pytest.raises(ValueError):
        ArrangementPolicy(chorus_energy_cut=True)  # bool 은 숫자로 치지 않는다
    assert ArrangementPolicy(chorus_energy_cut=0.0).chorus_energy_cut == 0.0
    assert ArrangementPolicy(chorus_energy_cut=1.0).chorus_energy_cut == 1.0
    assert dataclasses.is_dataclass(PALETTE)


# -- f. 곡별 주석 색이 이긴다 ------------------------------------------------------------------


def test_annotation_color_wins_over_the_section_color() -> None:
    # 5 마디에 킥 진입이 있어 4~7 마디 구간은 후렴 색이다. 주석 색은 그것과 다르다.
    plain = _draft(KICK_AT_5)
    assert _wash(plain, 7) == list(PALETTE.chorus)
    draft = _draft(KICK_AT_5, planned_colors={("WASH-ALL", 7): (55, 35, 100)})
    assert _wash(draft, 7) == [55, 35, 100]
    assert _wash(draft, 6) == list(PALETTE.chorus)


def test_annotation_color_wins_over_the_backlight() -> None:
    plain = _draft(KICK_AT_5)
    lit_back = next(bar for bar, cue in _cues(plain, "BACK").items() if cue["label"] != REST_LABEL)
    draft = _draft(KICK_AT_5, planned_colors={("BACK", lit_back): (1, 2, 3)})
    assert _cues(draft, "BACK")[lit_back]["planned_color"] == [1, 2, 3]


def test_annotation_color_on_a_rest_cell_is_ignored() -> None:
    plain = _draft(KICK_AT_5)
    rest_bar = next(bar for bar, cue in _cues(plain, "BACK").items() if cue["label"] == REST_LABEL)
    draft = _draft(KICK_AT_5, planned_colors={("BACK", rest_bar): (1, 2, 3)})
    assert "planned_color" not in _cues(draft, "BACK")[rest_bar]


def test_the_generator_stays_pure_with_planned_colors() -> None:
    colors = {("WASH-ALL", 7): (55, 35, 100)}
    first = _draft(KICK_AT_5, planned_colors=colors)
    assert first == _draft(KICK_AT_5, planned_colors=colors)
    assert colors == {("WASH-ALL", 7): (55, 35, 100)}


# -- g. 실제 LOVE ATTACK 주석에서 칸 색 ---------------------------------------------------------


def test_annotated_cell_colors_on_the_real_love_attack_annotations() -> None:
    colors = annotated_cell_colors(load_preset_annotations(LOVE_ATTACK_TITLE))
    assert colors[("WASH-ALL", 7)] == (55, 35, 100)
    assert colors[("WASH-ALL", 14)] == (55, 35, 100)
    assert colors[("WASH-ALL", 18)] == (100, 50, 75)
    assert colors[("WASH-ALL", 22)] == (100, 75, 60)
    assert colors[("BACK", 0)] == (40, 65, 95)


def test_annotated_cell_colors_is_empty_without_annotations() -> None:
    assert annotated_cell_colors({}) == {}
    assert annotated_cell_colors(None) == {}  # type: ignore[arg-type]
    assert annotated_cell_colors({"colors": None}) == {}
    assert annotated_cell_colors(load_preset_annotations("곡 이름 없음")) == {}


def test_annotated_cell_colors_resolves_names_skips_unknown_and_drops_ambiguous() -> None:
    annotations = {
        "colors": [
            {"name": "Lavender", "rgb": None, "cells": [{"group_name": "A", "bar": 1}]},
            {"name": "없는색", "rgb": None, "cells": [{"group_name": "A", "bar": 2}]},
            {"name": "x", "rgb": [101, 0, 0], "cells": [{"group_name": "A", "bar": 3}]},
            {"name": "y", "rgb": [1, 2, 3], "cells": [{"group_name": "A", "bar": 4}]},
            {"name": "z", "rgb": [4, 5, 6], "cells": [{"group_name": "A", "bar": 4}]},
            {"name": "w", "rgb": [1, 2, 3], "cells": [{"group_name": "A", "bar": 5}]},
            {"name": "w2", "rgb": [1, 2, 3], "cells": [{"group_name": "A", "bar": 5}]},
        ]
    }
    assert annotated_cell_colors(annotations) == {("A", 1): (55, 35, 100), ("A", 5): (1, 2, 3)}


# -- i. 앞빛(FOH) 은 구간과 상관없이 표준 Warm White ----------------------------------------------

WARM_WHITE = dict(COLOR_PALETTE_SEQUENCE)["Warm White"]


def test_front_light_stays_warm_white_in_every_section_on_both_generators() -> None:
    # 앞빛(FOH, key)은 드롭·브릿지·후렴 어디서나 표준 Warm White 다. 구간 색을 받으면 안 된다.
    # 생성기와 운영 경로(구간 생성기) 둘 다 같아야 한다.
    bar_map = _bar_map(KICK_AT_5 + DROP_17_18 + BREAK_25_26)
    assert PALETTE.key == WARM_WHITE
    for draft in (
        generate_arrangement_draft(bar_map, _layout()),
        generate_segment_draft(bar_map, _layout()),
    ):
        front = _cues(draft, "FOH").values()
        assert {tuple(cue["planned_color"]) for cue in front} == {WARM_WHITE}


# -- h. 적용 -------------------------------------------------------------------------------------


def _grid() -> dict:
    return copy.deepcopy(default_beat_grid(LOVE_ATTACK_TITLE))


def _track(grid: dict, name: str) -> dict:
    return next(track for track in grid["tracks"] if track["group_name"] == name)


def test_apply_gives_new_cells_a_planned_color() -> None:
    draft = _draft(KICK_AT_9 + DROP_17_18)
    updated, _report = apply_arrangement_draft(_grid(), draft)
    wash = {cue["bar"]: cue for cue in _track(updated, "WASH-ALL")["cues"]}
    assert wash[30]["planned_color"] == list(PALETTE.last_chorus[2])
    lit_new = [
        cue
        for track in updated["tracks"]
        for cue in track["cues"]
        if cue["bar"] > 25 and cue["label"] != REST_LABEL
    ]
    assert lit_new and all(_is_rgb(cue["planned_color"]) for cue in lit_new)


def test_apply_gives_blank_placeholder_cells_a_planned_color() -> None:
    draft = _draft(KICK_AT_9 + DROP_17_18)
    grid = _grid()
    wash = _track(grid, "WASH-ALL")
    wash["cues"].append({"bar": 30, "label": "—"})  # 이전 적용이 남긴 라벨뿐인 빈 칸
    updated, _report = apply_arrangement_draft(grid, draft)
    cell = next(cue for cue in _track(updated, "WASH-ALL")["cues"] if cue["bar"] == 30)
    assert _is_rgb(cell.get("planned_color"))


def test_apply_keeps_an_existing_cell_with_a_color_preset_and_adds_no_planned_color() -> None:
    draft = _draft(KICK_AT_9 + DROP_17_18)
    grid = _grid()
    cell = next(cue for cue in _track(grid, "WASH-ALL")["cues"] if cue["bar"] == 7)
    cell["color_preset_no"] = "5"
    updated, _report = apply_arrangement_draft(grid, draft)
    after = next(cue for cue in _track(updated, "WASH-ALL")["cues"] if cue["bar"] == 7)
    assert "planned_color" not in after
    assert after["color_preset_no"] == "5"
    assert after["brightness"] == cell["brightness"]


def test_normalize_drops_an_invalid_planned_color_and_never_writes_none() -> None:
    from server.design.beat_grid import normalize_beat_grid_cue

    assert "planned_color" not in normalize_beat_grid_cue({"bar": 1, "label": "x"})
    for bad in (None, [1, 2], [1, 2, 300], "abc", [True, 0, 0], [1.5, 2, 3]):
        cue = normalize_beat_grid_cue({"bar": 1, "label": "x", "planned_color": bad})
        assert "planned_color" not in cue, bad
    good = normalize_beat_grid_cue({"bar": 1, "label": "x", "planned_color": (1, 2, 3)})
    assert good["planned_color"] == [1, 2, 3]


# -- i. 화면에 보낼 사본의 계획 표시 -------------------------------------------------------------


def _grid_with(cues: list[dict], name: str = "WASH-ALL") -> dict:
    return {
        "tracks": [
            {
                "group_no": 10,
                "group_no_confirmed": True,
                "group_name": name,
                "layer_role": "wash",
                "cues": cues,
            }
        ]
    }


def test_attach_planned_marks_uses_the_cue_planned_color_without_annotations() -> None:
    grid = _grid_with(
        [
            {"bar": 1, "label": "유지", "planned_color": [1, 2, 3]},
            {"bar": 2, "label": "유지", "planned_color": [1, 2, 3], "color_preset_no": "5"},
            {"bar": 3, "label": "유지", "planned_color": [1, 2, 3], "color_rgb": [9, 9, 9]},
            {"bar": 4, "label": "유지", "planned_color": [1, 2, 300]},
            {"bar": 5, "label": "유지"},
        ]
    )
    served = attach_planned_marks(grid, "곡 이름 없음")
    cues = {cue["bar"]: cue for cue in served["tracks"][0]["cues"]}
    assert cues[1]["color_rgb"] == [1, 2, 3] and cues[1]["color_planned"] is True
    assert "color_rgb" not in cues[2] and "color_planned" not in cues[2]
    assert cues[3]["color_rgb"] == [9, 9, 9] and "color_planned" not in cues[3]
    assert "color_rgb" not in cues[4] and "color_planned" not in cues[4]
    assert "color_rgb" not in cues[5]
    assert "color_rgb" not in grid["tracks"][0]["cues"][0]  # 원본 불변


def test_attach_planned_marks_prefers_the_annotation_color_over_the_cue_planned_color() -> None:
    grid = _grid_with(
        [
            {"bar": 18, "label": "x", "planned_color": [1, 2, 3]},
            {"bar": 30, "label": "x", "planned_color": [1, 2, 3]},
        ]
    )
    served = attach_planned_marks(grid, LOVE_ATTACK_TITLE)
    cues = {cue["bar"]: cue for cue in served["tracks"][0]["cues"]}
    assert cues[18]["color_rgb"] == [100, 50, 75] and cues[18]["color_planned"] is True
    assert cues[30]["color_rgb"] == [1, 2, 3] and cues[30]["color_planned"] is True


# -- j. 「반영 이후 바뀐 칸」 비교에서 뺀다 -----------------------------------------------------


def test_planned_color_does_not_make_a_cell_unsent() -> None:
    base = _grid_with([{"bar": 1, "label": "유지", "planned_color": [1, 2, 3]}])
    snapshot = beat_grid_cell_snapshot(base)
    changed = copy.deepcopy(base)
    changed["tracks"][0]["cues"][0]["planned_color"] = [9, 8, 7]
    assert unsent_beat_grid_cells(changed, snapshot) == []
    removed = copy.deepcopy(base)
    del removed["tracks"][0]["cues"][0]["planned_color"]
    assert unsent_beat_grid_cells(removed, snapshot) == []
    assert "planned_color" not in snapshot[("WASH-ALL", 1)]


def test_the_served_copy_with_planned_marks_does_not_make_a_cell_unsent() -> None:
    base = _grid_with([{"bar": 1, "label": "유지", "planned_color": [1, 2, 3]}])
    stored = copy.deepcopy(base)
    del stored["tracks"][0]["cues"][0]["planned_color"]
    snapshot = beat_grid_cell_snapshot(stored)
    served = attach_planned_marks(base, "곡 이름 없음")
    assert served["tracks"][0]["cues"][0]["color_planned"] is True
    assert unsent_beat_grid_cells(served, snapshot) == []
