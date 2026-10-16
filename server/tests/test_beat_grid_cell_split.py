"""칸 하나의 왼쪽·오른쪽 따로 색(`split`) — 데이터 모양 · 서버가 싣는 화면용 값 · 프리셋 계획.

콘솔 접촉 0건. 그룹 이름·색은 시험 자료인 일반 격자(곡·리그 고유값 없음)다. 시험이 재는 것:

1. 서버 화면용 값 — `split` 이 있는 칸만 쪽마다 `color_rgb` 를 받고, 없는 칸은 키 자체가 없다.
2. 모양이 틀린 `split` 은 조용히 버려지지 않고 그룹·마디를 말하는 `ValueError` 가 된다.
3. 칸을 읽는 화이트리스트(`normalize_beat_grid_cue`)를 지나도 `split` 이 살아남는다 — 기본값 로드 ·
   서빙 경계 · 편집 병합 세 길 모두.
4. 프리셋 계획 — 색이 정해진 쪽마다 후보 한 줄, 비어 있는 쪽은 「미정」 한 줄. 저장 줄도 칸
   참조도 없다.
"""

from __future__ import annotations

import copy
import json
from dataclasses import replace

import pytest
import yaml

from server.design import beat_grid as beat_grid_module
from server.design.beat_grid import (
    attach_beat_grid_runtime_extras,
    default_beat_grid,
    normalize_beat_grid_cue,
)
from server.design.beat_grid_cell_split import (
    CELL_SPLIT_SIDES,
    attach_cell_split_to_cues,
    cell_split_side_rgb,
    validate_cell_split,
)
from server.design.beat_grid_edit import apply_beat_grid_edit, load_preset_pool_policy
from server.design.beat_grid_send import beat_grid_cell_snapshot, unsent_beat_grid_cells
from server.design.beat_grid_ui_values import attach_beat_grid_ui_values
from server.design.preset_plan import (
    LoveAttackPlan,
    PlanPreset,
    apply_plan_references,
    build_preset_plan,
    card_reason,
    plan_table_markdown,
    save_commands,
)

GROUP = "SIDE-ALL"
SPLIT = {"left": {"color": "Red"}, "right": {"color": "Blue"}}
SPLIT_RGB = {
    "left": {"color": "Red", "color_rgb": [100, 0, 0]},
    "right": {"color": "Blue", "color_rgb": [5, 20, 100]},
}


def _cue(bar: int, **fields: object) -> dict:
    return dict(normalize_beat_grid_cue({"bar": bar, "label": f"칸 {bar}", **fields}))


def _grid(*cues: dict) -> dict:
    return {
        "tracks": [
            {
                "group_no": 21,
                "group_no_confirmed": True,
                "group_name": GROUP,
                "layer_role": "side",
                "cues": list(cues),
            }
        ]
    }


def _payload_cues(grid: dict) -> list[dict]:
    return attach_beat_grid_ui_values({"beat_grid": grid})["beat_grid"]["tracks"][0]["cues"]


# == 서버 화면용 값 ===================================================================


class TestPayload:
    def test_split_is_emitted_with_color_rgb_per_side(self) -> None:
        cue = _payload_cues(_grid(_cue(7, split=SPLIT)))[0]
        assert cue["split"] == SPLIT_RGB

    def test_a_cue_without_split_has_no_split_key(self) -> None:
        cues = _payload_cues(_grid(_cue(0), _cue(7, split=SPLIT), _cue(14)))
        assert [("split" in cue) for cue in cues] == [False, True, False]

    def test_a_grid_without_any_split_carries_no_split_anywhere(self) -> None:
        grid = _grid(_cue(0), _cue(7))
        out = attach_beat_grid_ui_values({"beat_grid": grid})
        assert '"split"' not in json.dumps(out)

    def test_a_grid_without_split_comes_back_equal(self) -> None:
        grid = _grid(_cue(0), _cue(7))
        assert attach_cell_split_to_cues(grid) == grid

    def test_an_explicit_null_split_is_dropped_not_emitted(self) -> None:
        grid = {"tracks": [{"group_name": GROUP, "cues": [{"bar": 3, "split": None}]}]}
        cue = attach_cell_split_to_cues(grid)["tracks"][0]["cues"][0]
        assert "split" not in cue

    def test_an_unresolvable_or_missing_color_gives_null_rgb(self) -> None:
        split = {"left": {"color": "no-such-color"}, "right": {"color": None}}
        cue = _payload_cues(_grid(_cue(7, split=split)))[0]
        assert cue["split"] == {
            "left": {"color": "no-such-color", "color_rgb": None},
            "right": {"color": None, "color_rgb": None},
        }

    def test_a_side_without_a_color_key_reads_as_undecided(self) -> None:
        split = {"left": {}, "right": {"color": "Red"}}
        cue = _payload_cues(_grid(_cue(7, split=split)))[0]
        assert cue["split"]["left"] == {"color": None, "color_rgb": None}
        assert cue["split"]["right"] == {"color": "Red", "color_rgb": [100, 0, 0]}

    def test_the_input_grid_is_not_mutated(self) -> None:
        grid = _grid(_cue(7, split=SPLIT))
        before = copy.deepcopy(grid)
        attach_beat_grid_ui_values({"beat_grid": grid})
        assert grid == before

    def test_color_rgb_is_a_list_of_ints_from_the_palette(self) -> None:
        assert cell_split_side_rgb("Red") == [100, 0, 0]
        assert cell_split_side_rgb("블루") == [5, 20, 100]  # 한국어 원색 표기도 같은 표를 쓴다
        assert cell_split_side_rgb(None) is None
        assert cell_split_side_rgb("no-such-color") is None


# == 모양 검증 ========================================================================


_MALFORMED_SPLITS = [
    pytest.param("Red", id="non-mapping-string"),
    pytest.param(["left", "right"], id="non-mapping-list"),
    pytest.param({}, id="empty-mapping"),
    pytest.param({"left": {"color": "Red"}}, id="missing-right"),
    pytest.param({"right": {"color": "Red"}}, id="missing-left"),
    pytest.param({**SPLIT, "center": {"color": "Red"}}, id="unknown-top-key"),
    pytest.param({"left": "Red", "right": {"color": None}}, id="side-not-a-mapping"),
    pytest.param(
        {"left": {"color": "Red", "alpha": 1}, "right": {"color": None}}, id="unknown-side-key"
    ),
    pytest.param({"left": {"color": 5}, "right": {"color": None}}, id="non-str-color"),
    pytest.param({"left": {"color": ["Red"]}, "right": {"color": None}}, id="list-color"),
]


class TestMalformedSplit:
    @pytest.mark.parametrize("bad", _MALFORMED_SPLITS)
    def test_the_payload_path_raises_naming_group_and_bar(self, bad: object) -> None:
        grid = _grid(_cue(0), _cue(7, split=bad))
        with pytest.raises(ValueError) as error:
            attach_beat_grid_ui_values({"beat_grid": grid})
        assert f"{GROUP} 7마디" in str(error.value)

    @pytest.mark.parametrize("bad", _MALFORMED_SPLITS)
    def test_the_plan_path_raises_naming_group_and_bar(self, bad: object) -> None:
        grid = _grid(_cue(0), _cue(7, split=bad))
        with pytest.raises(ValueError) as error:
            _plan(grid)
        assert f"{GROUP} 7마디" in str(error.value)

    def test_validate_returns_the_clean_stored_shape_or_none(self) -> None:
        assert validate_cell_split(None, group_name=GROUP, bar=7) is None
        clean = validate_cell_split(SPLIT, group_name=GROUP, bar=7)
        assert clean == SPLIT
        assert clean is not SPLIT
        assert tuple(clean) == CELL_SPLIT_SIDES

    def test_an_empty_color_string_is_not_malformed_just_unresolvable(self) -> None:
        split = {"left": {"color": ""}, "right": SPLIT["right"]}
        cue = _payload_cues(_grid(_cue(7, split=split)))[0]
        assert cue["split"]["left"] == {"color": "", "color_rgb": None}


# == 칸을 읽는 화이트리스트를 지나도 살아남는다 =====================================


class TestSplitSurvivesCellNormalization:
    def test_normalize_keeps_a_copy_of_split(self) -> None:
        raw = {"bar": 1, "split": copy.deepcopy(SPLIT)}
        cue = normalize_beat_grid_cue(raw)
        assert cue["split"] == SPLIT
        raw["split"]["left"]["color"] = "Green"  # type: ignore[index]
        assert cue["split"] == SPLIT  # 사본이라 원본을 고쳐도 변하지 않는다

    def test_normalize_without_split_has_no_key_even_when_null(self) -> None:
        assert "split" not in normalize_beat_grid_cue({"bar": 1})
        assert "split" not in normalize_beat_grid_cue({"bar": 1, "split": None})

    def test_the_yaml_loader_carries_split(self, monkeypatch, tmp_path) -> None:
        song = "Cell Split Song"
        document = {
            "source": "cell_split_default",
            "tracks": [
                {
                    "group_name": GROUP,
                    "group_no": 21,
                    "group_no_confirmed": True,
                    "cues": [
                        {"bar": 0, "label": "보통"},
                        {"bar": 7, "label": "따로", "split": SPLIT},
                    ],
                }
            ],
            "scene_memos": [],
        }
        path = tmp_path / "cell_split.yaml"
        path.write_text(yaml.safe_dump(document, allow_unicode=True), encoding="utf-8")
        key = beat_grid_module._group_key(song)
        monkeypatch.setitem(beat_grid_module._SONG_DEFAULT_FILES, key, path)

        cues = default_beat_grid(song)["tracks"][0]["cues"]

        assert "split" not in cues[0]
        assert cues[1]["split"] == SPLIT

    def test_the_serving_boundary_keeps_split(self, tmp_path) -> None:
        raw = {"beat_grid": _grid({"bar": 0, "label": "보통"}, {"bar": 7, "split": SPLIT})}
        served = attach_beat_grid_runtime_extras(raw, progress_md_path=tmp_path / "absent.md")
        cues = served["beat_grid"]["tracks"][0]["cues"]
        assert "split" not in cues[0]
        assert cues[1]["split"] == SPLIT

    def test_an_edit_merge_keeps_the_cells_split(self) -> None:
        grid = _grid(_cue(0), _cue(7, split=SPLIT))
        updated, _report = apply_beat_grid_edit(
            grid,
            bar=7,
            target=GROUP,
            changes={"brightness": {"mode": "value", "value_percent": 40, "preset_no": None}},
        )
        cue = updated["tracks"][0]["cues"][1]
        assert cue["brightness"]["value_percent"] == 40
        assert cue["split"] == SPLIT


# == 「반영 뒤 바뀐 칸」 비교 · 곡 기본값 ===============================================


class TestUnsentComparison:
    def test_a_split_cell_is_not_unsent_right_after_an_apply(self) -> None:
        grid = _grid(_cue(0), _cue(7, split=SPLIT))
        snapshot = beat_grid_cell_snapshot(grid)  # 반영 때 찍는 저장 모양
        # 서빙 모양 — 쪽마다 color_rgb 가 붙어 있다.
        served = attach_beat_grid_ui_values({"beat_grid": grid})["beat_grid"]
        assert unsent_beat_grid_cells(served, snapshot) == []

    def test_changing_a_side_color_after_the_apply_makes_the_cell_unsent(self) -> None:
        grid = _grid(_cue(7, split=SPLIT))
        snapshot = beat_grid_cell_snapshot(grid)
        edited = copy.deepcopy(grid)
        edited["tracks"][0]["cues"][0]["split"]["right"]["color"] = "Green"
        served = attach_beat_grid_ui_values({"beat_grid": edited})["beat_grid"]
        assert unsent_beat_grid_cells(served, snapshot) == [{"group_name": GROUP, "bar": 7}]

    def test_the_snapshot_of_a_cell_without_split_is_the_cell_itself(self) -> None:
        cue = _cue(3)
        assert beat_grid_cell_snapshot(_grid(cue))[(GROUP, 3)] == cue


class TestShippedSongDefaults:
    def test_every_registered_default_grid_has_well_formed_split_cells(self) -> None:
        # 곡 기본값 YAML 은 손으로 쓴다. 모양이 틀린 split 은 서빙 때 터지므로(화면 프레임이 나가지
        # 않는다) 출하 전에 여기서 먼저 잡는다 — 틀리면 ValueError 가 그룹·마디를 말한다.
        for key in beat_grid_module._SONG_DEFAULT_FILES:
            attach_cell_split_to_cues(default_beat_grid(key))


# == 프리셋 계획 ======================================================================

_COLOR_POOL = (4, {slot: f"COLOR {slot}" for slot in range(1, 11)})
_NAME_HOLD = "콘솔 이름 미정 — 칸 색 이름은 감독이 정한다"
_COLOR_PATH_HOLD = "색 저장은 기존 「＋ 새 프리셋」 색 경로(t594)로 만든다 — 이 카드 범위 밖"


def _plan(grid: dict, *, annotations=None, color_pool=_COLOR_POOL, dimmer=None):
    return build_preset_plan(
        grid,
        annotations=annotations or {},
        policy=load_preset_pool_policy(),
        dimmer_pool=dimmer,
        color_pool=color_pool,
        position_pool=None,
        dimmer_attributes={GROUP: ("Dimmer",)} if dimmer else {},
    )


class TestPresetPlanFromSplit:
    def test_two_candidates_per_split_cell_with_the_right_rgb(self) -> None:
        plan = _plan(_grid(_cue(0), _cue(7, split=SPLIT), _cue(14)))

        assert [p.split_side for p in plan.presets] == ["left", "right"]
        left, right = plan.presets
        assert (left.value, right.value) == ("RGB 100 0 0", "RGB 5 20 100")
        for preset in plan.presets:
            assert preset.kind == "color"
            assert preset.name == ""
            assert preset.cells[0].group_name == GROUP and preset.cells[0].bar == 7
            assert len(preset.cells) == 1
            assert preset.groups == (GROUP,)
            assert preset.ready is False
            assert preset.deferred is True
            assert preset.hold is not None and preset.hold.startswith(_NAME_HOLD)
            assert _COLOR_PATH_HOLD in preset.hold
        assert left.slot is not None and right.slot is not None and left.slot != right.slot
        assert left.slot.startswith("4.") and right.slot.startswith("4.")

    def test_a_null_side_has_no_candidate_and_one_unresolved_note(self) -> None:
        split = {"left": {"color": "Red"}, "right": {"color": None}}
        plan = _plan(_grid(_cue(14, split=split)))

        assert [p.split_side for p in plan.presets] == ["left"]
        assert plan.unresolved == (f"{GROUP} 14마디 오른쪽 칸 색 미정 — 감독이 정한다",)

    def test_both_sides_undecided_gives_two_notes_and_no_candidate(self) -> None:
        split = {"left": {"color": None}, "right": {}}
        plan = _plan(_grid(_cue(3, split=split)))

        assert plan.presets == ()
        assert plan.unresolved == (
            f"{GROUP} 3마디 왼쪽 칸 색 미정 — 감독이 정한다",
            f"{GROUP} 3마디 오른쪽 칸 색 미정 — 감독이 정한다",
        )

    def test_a_color_name_outside_the_palette_keeps_the_candidate_with_rgb_unset(self) -> None:
        split = {"left": {"color": "no-such-color"}, "right": {"color": "Red"}}
        plan = _plan(_grid(_cue(7, split=split)))

        left, right = plan.presets
        assert left.value == "RGB 미정"
        assert left.deferred is False and left.ready is False
        assert left.hold is not None and left.hold.startswith(_NAME_HOLD)
        assert "RGB 미정 —" in left.hold and _COLOR_PATH_HOLD not in left.hold
        assert right.deferred is True
        # 값이 정해지지 않은 쪽은 「미정」, 정해진 쪽은 「이 카드 밖」에 사유와 함께 남는다.
        assert any(line.startswith(f"{GROUP} 7마디 왼쪽 칸 RGB 미정") for line in plan.unresolved)
        assert any(
            line.startswith(f"{GROUP} 7마디 오른쪽 칸 RGB 100 0 0") for line in plan.deferred
        )

    def test_normal_cells_get_no_candidate(self) -> None:
        plan = _plan(_grid(_cue(0), _cue(7), _cue(14)))
        assert plan.presets == ()
        assert plan.unresolved == ()
        assert plan.deferred == ()

    def test_an_unreadable_color_pool_holds_without_a_slot(self) -> None:
        plan = _plan(_grid(_cue(7, split=SPLIT)), color_pool=None)

        for preset in plan.presets:
            assert preset.slot is None
            assert preset.hold is not None and "색 풀을 콘솔에서 읽지 못해" in preset.hold

    def test_split_candidates_come_after_the_annotation_colors_and_keep_their_slots(self) -> None:
        annotations = {
            "colors": [
                {
                    "name": "Lavender",
                    "console_name": "LAV",
                    "note": "",
                    "cells": [{"group_name": GROUP, "bar": 0}],
                }
            ]
        }
        without = _plan(_grid(_cue(0), _cue(7)), annotations=annotations)
        with_split = _plan(_grid(_cue(0), _cue(7, split=SPLIT)), annotations=annotations)

        lavender = [p for p in with_split.presets if p.name == "LAV"]
        assert [p.slot for p in lavender] == [p.slot for p in without.presets]
        taken = {p.slot for p in with_split.presets}
        assert len(taken) == 3  # 주석 색 하나 + 쪽 둘, 번호가 겹치지 않는다

    def test_a_plan_preset_built_the_old_way_has_no_split_side(self) -> None:
        preset = PlanPreset(
            kind="dimmer",
            value="40%",
            name="DIM-40",
            slot=None,
            cells=(),
            groups=(),
            ready=False,
            hold="x",
        )
        assert preset.split_side is None


class TestSplitCandidatesAreNeverSavedOrReferenced:
    def test_save_commands_is_empty_for_a_split_only_grid(self) -> None:
        plan = _plan(_grid(_cue(7, split=SPLIT)))
        assert plan.presets  # 후보는 있다
        assert save_commands(plan) == ()

    def test_apply_plan_references_leaves_a_split_only_grid_unchanged(self) -> None:
        grid = _grid(_cue(7, split=SPLIT))
        plan = _plan(grid)
        applied = apply_plan_references(grid, plan, by="supervisor", date="d", source="s")
        assert applied == grid
        assert applied["tracks"][0]["cues"][0]["color_preset_no"] is None

    def test_the_explicit_skip_holds_even_if_a_split_candidate_were_flagged_ready(self) -> None:
        # 방어: 후보는 ready 가 아니게 만들어지지만, 누군가 ready 디머 꼴로 바꿔도 split_side 가
        # 있으면 저장 줄도 칸 참조도 만들지 않는다(save_commands · apply_plan_references ·
        # card_reason).
        grid = _grid(_cue(7, split=SPLIT))
        plan = _plan(grid)
        forced = replace(
            plan,
            presets=tuple(
                replace(p, ready=True, kind="dimmer", value_percent=40) for p in plan.presets
            ),
        )
        assert save_commands(forced) == ()
        assert apply_plan_references(grid, forced, by="s", date="d", source="s") == grid
        assert card_reason(forced).startswith("디머 프리셋 0개 저장")

    def test_dimmer_lines_and_references_do_not_change_when_a_split_cell_is_added(self) -> None:
        dimmer = (1, {1: "기존"})
        plain = _grid(
            _cue(0, brightness={"mode": "value", "value_percent": 40, "preset_no": None}),
            _cue(7),
            _cue(14, brightness={"mode": "value", "value_percent": 40, "preset_no": None}),
        )
        with_split = copy.deepcopy(plain)
        with_split["tracks"][0]["cues"][1]["split"] = copy.deepcopy(SPLIT)

        plan_plain = _plan(plain, dimmer=dimmer)
        plan_split = _plan(with_split, dimmer=dimmer)

        assert save_commands(plan_plain)  # 비교가 뜻이 있으려면 저장 줄이 있어야 한다
        assert save_commands(plan_split) == save_commands(plan_plain)
        applied_plain = apply_plan_references(plain, plan_plain, by="s", date="d", source="s")
        applied_split = apply_plan_references(with_split, plan_split, by="s", date="d", source="s")
        del applied_split["tracks"][0]["cues"][1]["split"]
        assert applied_split == applied_plain

    def test_split_rows_show_in_the_table_with_a_dash_and_the_reason_names_the_cell(self) -> None:
        split = {"left": {"color": "Red"}, "right": {"color": None}}
        plan = _plan(_grid(_cue(7, split=split)))
        (preset,) = plan.presets

        table = plan_table_markdown(plan)

        assert f"| — | RGB 100 0 0 | {preset.slot} | 1 | 이 카드 밖 |" in table
        reason = f"{GROUP} 7마디 왼쪽 칸 RGB 100 0 0(칸 1개, 후보 {preset.slot}): {_NAME_HOLD}"
        assert f"- {reason}" in table
        assert f"- {GROUP} 7마디 오른쪽 칸 색 미정 — 감독이 정한다" in table
        assert card_reason(plan).startswith("디머 프리셋 0개 저장")

    def test_table_rows_of_a_plan_without_split_keep_their_old_shape(self) -> None:
        # 이름이 없는 줄이라도 쪽 후보가 아니면 예전처럼 빈 칸이다(줄표는 쪽 후보에만).
        preset = PlanPreset(
            kind="color",
            value="RGB 미정",
            name="",
            slot=None,
            cells=(),
            groups=(),
            ready=False,
            hold="x",
        )
        plan = LoveAttackPlan(presets=(preset,), unresolved=(), kept=())
        assert "|  | RGB 미정 |" in plan_table_markdown(plan)
