"""움직임(app_movement) 칸을 콘솔 효과 프리셋으로 저장하는 계획 — 카드 WT-effect-presets.

콘솔 접촉 0건. 효과 풀 21(「All 1」)은 테스트 픽스처다 — 실기 판독이 아니다. BPM·번호·
진행표 판정도 시험 입력이다. M1 ④ 판정은 고정 스냅샷(`_LIVE_M1`)과 주입 값으로만 바꾼다.

검증하는 것: 준비된 효과 프리셋은 풀 21의 빈 번호에 저장되고, 승인 뒤 칸이 그 번호를 가리키며,
그 칸은 ⑤⑦⑨ 대신 ④에 기대게 된다. 주기가 빈 칸은 같은 줄의 주기를 빌리고 「감독이 고칠 값」에
적는다. 실측으로 열린 칸(MOVER-D Tilt 웨이브)도 Pan 처럼 효과 프리셋을 받는다(리드 지시 2026-10-16).
"""

from __future__ import annotations

import copy

from server.design.app_movement import movement_effect_store_commands
from server.design.beat_grid import LOVE_ATTACK_TITLE, default_beat_grid
from server.design.beat_grid_edit import load_preset_pool_policy
from server.design.beat_grid_emit import (
    SongTiming,
    emit_beat_grid_write_bundle,
    required_m1_items_for_cue,
)
from server.design.preset_plan import (
    apply_plan_references,
    build_preset_plan,
    effect_plan_timing,
    load_preset_annotations,
    save_commands,
)
from server.web.session import SongTimelineStore

from .test_beat_grid_emit_t549 import _LIVE_M1
from .test_new_preset_dialog_t589 import (
    _new_session,
    _pool_children_payload,
    _pool_list_payload,
    _state_tree,
    _timeline_for_apply,
)
from .test_preset_plan import _COLOR_CHILDREN, _DIMMER_CHILDREN, _POSITION_CHILDREN

# -- 시험 입력(콘솔 판독 아님) ----------------------------------------------------
_BPM = 112.0
_TIMING = SongTiming(bpm=_BPM, beats_per_bar=4, downbeat_bar1_seconds=1.5)
_DIMMER = (1, {1: "풀", 2: "쇼 하이 OLD", 3: "미드", 4: "로우", 5: "잔광", 6: "아웃", 7: "쇼 하이"})
_COLOR = (4, {**{slot: f"COLOR {slot}" for slot in range(1, 11)}, 32: "COLOR 32"})
_POSITION = (
    2,
    {
        **{slot: f"POS {slot}" for slot in range(1, 7)},
        **{slot: f"POS {slot}" for slot in range(21, 31)},
    },
)
#: 효과 풀 21 — 1~7 과 301 이 찼다고 두는 픽스처. 첫 빈 번호는 8.
_EFFECT = (21, {**{slot: f"EFX {slot}" for slot in range(1, 8)}, 301: "EFX 301"})
_ATTRIBUTES = {
    group: ("Dimmer",)
    for group in ("FOH", "WASH-ALL", "BACK", "SIDE-ALL", "MOVER-U", "MOVER-D", "BLIND", "STROBE")
}
_POOL_HOLD = "효과 풀을 콘솔에서 읽지 못해 빈 번호를 정하지 못함"
_PASSED_4 = {**_LIVE_M1, 4: "통과 (시험 주입)"}


def _grid() -> dict:
    return copy.deepcopy(default_beat_grid(LOVE_ATTACK_TITLE))


def _track(grid: dict, group: str) -> dict:
    return next(t for t in grid["tracks"] if t["group_name"] == group)


def _cue(grid: dict, group: str, bar: int) -> dict:
    return next(c for c in _track(grid, group)["cues"] if c["bar"] == bar)


def _clear_mover_u_periods(grid: dict) -> None:
    """MOVER-U 줄의 움직임 주기를 모두 비운다 — 같은 줄에 빌릴 주기가 없는 상황을 만든다."""
    for cue in _track(grid, "MOVER-U")["cues"]:
        movement = cue.get("app_movement")
        if isinstance(movement, dict) and movement.get("shape") is not None:
            movement["period_unit"] = None
            movement["period_value"] = None


def _plan(grid: dict, *, effect_pool=_EFFECT):
    return build_preset_plan(
        grid,
        annotations=load_preset_annotations(LOVE_ATTACK_TITLE),
        policy=load_preset_pool_policy(),
        dimmer_pool=_DIMMER,
        color_pool=_COLOR,
        position_pool=_POSITION,
        dimmer_attributes=_ATTRIBUTES,
        effect_pool=effect_pool,
        bpm=_BPM,
        beats_per_bar=4,
    )


def _effect_presets(plan) -> list:
    return [preset for preset in plan.presets if preset.kind == "effect"]


def _named(plan, name: str):
    matches = [preset for preset in _effect_presets(plan) if preset.name == name]
    assert len(matches) == 1, f"{name!r} 이 한 번만 있어야 한다: {[p.name for p in plan.presets]}"
    return matches[0]


def _approve(grid: dict, plan):
    """세션의 승인 호출과 같은 인자(by=supervisor, planned_from=계획 시점 격자)."""
    return apply_plan_references(
        grid,
        plan,
        by="supervisor",
        date="2026-10-16T00:00:00+00:00",
        source="preset_plan:test",
        planned_from=grid,
    )


def _emit(grid: dict, probes: dict):
    tracks = grid["tracks"]
    return emit_beat_grid_write_bundle(
        tracks,
        timing=_TIMING,
        sequence_numbers={t["group_name"]: 300 + i for i, t in enumerate(tracks)},
        timecode_numbers={t["group_name"]: (30 if i < 4 else 31) for i, t in enumerate(tracks)},
        dimmer_attributes=_ATTRIBUTES,
        probe_results=probes,
    )


def _m1_blocked(result) -> set[tuple[str, int]]:
    """M1 게이트(「미확인 항목」)로 막힌 칸만 — 다른 사유(마디 0 등)는 뺀다."""
    return {
        (track.group_name, cue.bar)
        for track in result.tracks
        for cue in track.cues
        if cue.blocked_reason is not None and cue.blocked_reason.startswith("미확인 항목")
    }


class TestMovementEffectStoreCommands:
    def test_wave_pan_two_beats_stores_a_pool_21_effect_at_the_given_slot(self) -> None:
        commands, reason = movement_effect_store_commands(
            {"shape": "wave", "axes": ("Pan",), "period_unit": "beat", "period_value": 2},
            group_no=11,
            preset_pool=21,
            preset=8,
            label="WAVE PAN 2 BEAT",
            bpm=_BPM,
            beats_per_bar=4,
        )
        assert reason is None
        assert commands[0] == "ClearAll"
        assert commands[-1] == "ClearAll"
        assert "Group 11" in commands
        # 박 2 주기 = BPM 112 / 2 박 = 56
        assert "Attribute 'Pan' At Speed 56" in commands
        assert commands[-3:-1] == (
            "Store Preset 21.8 'WAVE PAN 2 BEAT' /Universal",
            "Label Preset 21.8 'WAVE PAN 2 BEAT'",
        )

    def test_a_speed_master_binds_the_speed_instead_of_baking_it(self) -> None:
        commands, reason = movement_effect_store_commands(
            {"shape": "wave", "axes": ("Pan",), "period_unit": "bar", "period_value": 2},
            group_no=11,
            preset_pool=21,
            preset=15,
            label="WAVE PAN 2 BAR",
            bpm=112.002,
            beats_per_bar=4,
            speed_master=15,
        )
        assert reason is None
        assert commands[0] == "Master 3.15 At BPM 112.002"
        assert not any(" At Speed " in line for line in commands)
        # 실기 통과 순서(t531): At Measure → At SpeedMaster → Store Preset
        measure = commands.index("Attribute 'Pan' At Measure 8")
        master = commands.index("Attribute 'Pan' At SpeedMaster 15")
        store = commands.index("Store Preset 21.15 'WAVE PAN 2 BAR' /Universal")
        assert measure < master < store

    def test_refuses_without_bpm_and_emits_nothing(self) -> None:
        commands, reason = movement_effect_store_commands(
            {"shape": "wave", "axes": ("Pan",), "period_unit": "beat", "period_value": 2},
            group_no=11,
            preset_pool=21,
            preset=8,
            label="WAVE PAN 2 BEAT",
            bpm=None,
            beats_per_bar=4,
        )
        assert commands == ()
        assert reason is not None and "BPM" in reason

    def test_refuses_a_label_that_would_break_the_console_quote(self) -> None:
        commands, reason = movement_effect_store_commands(
            {"shape": "wave", "axes": ("Pan",), "period_unit": "beat", "period_value": 2},
            group_no=11,
            preset_pool=21,
            preset=8,
            label="WAVE'PAN",
            bpm=_BPM,
            beats_per_bar=4,
        )
        assert commands == ()
        assert reason is not None

    def test_a_cell_without_movement_has_nothing_to_store(self) -> None:
        commands, reason = movement_effect_store_commands(
            None,
            group_no=11,
            preset_pool=21,
            preset=8,
            label="WAVE PAN 2 BEAT",
            bpm=_BPM,
            beats_per_bar=4,
        )
        assert commands == ()
        assert reason is not None


class TestEffectPresetPlan:
    def test_the_pan_cells_share_one_ready_pool_21_preset(self) -> None:
        # MOVER-U 11 은 주기가 비어 같은 줄의 18마디 주기(박 2)를 빌린다 → 두 칸이 한 프리셋이다.
        ready = [
            preset
            for preset in _effect_presets(_plan(_grid()))
            if preset.ready and "PAN" in preset.name
        ]
        assert [preset.name for preset in ready] == ["WAVE PAN 2 BEAT"]
        preset = ready[0]
        assert preset.slot == "21.8"
        assert [(cell.group_name, cell.bar) for cell in preset.cells] == [
            ("MOVER-U", 11),
            ("MOVER-U", 18),
        ]
        assert preset.store is not None
        assert "Store Preset 21.8 'WAVE PAN 2 BEAT' /Universal" in preset.store
        # preset_pools.yaml 에 speed_master 가 있으니 속도는 굽지 않고 묶는다(full2 D-12 실서버
        # 결함: 계획 문구만 SpeedMaster 이고 저장 줄은 At Speed 14.0002 로 나갔다).
        speed_master = load_preset_pool_policy()["speed_master"]
        assert preset.store[0] == f"Master 3.{speed_master} At BPM 112"
        assert not any(" At Speed " in line for line in preset.store)
        assert "Attribute 'Pan' At Measure 2" in preset.store
        assert f"Attribute 'Pan' At SpeedMaster {speed_master}" in preset.store

    def test_without_a_speed_master_the_speed_is_baked_as_before(self) -> None:
        plan = build_preset_plan(
            _grid(),
            annotations=load_preset_annotations(LOVE_ATTACK_TITLE),
            policy={**load_preset_pool_policy(), "speed_master": None},
            dimmer_pool=_DIMMER,
            color_pool=_COLOR,
            position_pool=_POSITION,
            dimmer_attributes=_ATTRIBUTES,
            effect_pool=_EFFECT,
            bpm=_BPM,
            beats_per_bar=4,
        )
        store = _named(plan, "WAVE PAN 2 BEAT").store
        assert store is not None
        assert "Attribute 'Pan' At Speed 56" in store
        assert not any("SpeedMaster" in line or line.startswith("Master 3.") for line in store)

    def test_a_borrowed_period_is_marked_for_the_supervisor_on_its_own_row(self) -> None:
        grid = _grid()
        plan = _plan(grid)
        marks = [fix for fix in plan.supervisor_fixes if fix.startswith("WAVE PAN 2 BEAT ")]
        assert any("11마디" in fix and "18마디" in fix and "감독이 고칠 값" in fix for fix in marks)
        # 계획은 격자를 바꾸지 않는다 — 빌린 주기는 계획 안에만 있다
        assert _cue(grid, "MOVER-U", 11)["app_movement"]["period_value"] is None

    def test_a_borrowed_period_prefers_the_nearest_earlier_cell(self) -> None:
        # MOVER-U 3마디에 마디 단위 1 을 두면, 11마디(주기 없음)는 뒤쪽 18마디가 아니라
        # 앞쪽 3마디의 주기를 빌린다.
        grid = _grid()
        _cue(grid, "MOVER-U", 3)["app_movement"] = {
            "shape": "wave",
            "axes": ("Pan",),
            "period_unit": "bar",
            "period_value": 1,
            "phase_spread": False,
        }
        plan = _plan(grid)
        bar_one = _named(plan, "WAVE PAN 1 BAR")
        assert [(cell.group_name, cell.bar) for cell in bar_one.cells] == [
            ("MOVER-U", 3),
            ("MOVER-U", 11),
        ]
        assert any(
            fix.startswith("WAVE PAN 1 BAR ") and "3마디의 주기(마디 1)" in fix
            for fix in plan.supervisor_fixes
        )

    def test_a_preset_that_cannot_store_takes_no_slot_number(self) -> None:
        # 같은 줄에 주기가 없어 보류되는 MOVER-U 는 번호를 잡지 않는다. 저장되는 줄은 줄 순서대로
        # 빈 번호를 받는다 — MOVER-D Tilt 두 줄이 21.8·21.9, 그 뒤 BLIND 가 21.10 이다.
        grid = _grid()
        _clear_mover_u_periods(grid)
        _track(grid, "BLIND")["cues"][0]["app_movement"] = {
            "shape": "wave",
            "axes": ("Pan",),
            "period_unit": "beat",
            "period_value": 4,
            "phase_spread": False,
        }
        plan = _plan(grid)
        assert _named(plan, "WAVE PAN").slot is None
        assert _named(plan, "WAVE PAN 4 BEAT").slot == "21.10"

    def test_measured_tilt_wave_cells_get_an_effect_preset_like_pan(self) -> None:
        # MOVER-D Tilt 웨이브도 효과 프리셋(풀 21)으로 만든다. ④는 실기 통과(리드 지시 1016).
        plan = _plan(_grid())
        tilt = [
            preset
            for preset in _effect_presets(plan)
            if {(cell.group_name, cell.bar) for cell in preset.cells}
            & {("MOVER-D", 7), ("MOVER-D", 22)}
        ]
        covered = {(cell.group_name, cell.bar) for preset in tilt for cell in preset.cells}
        assert {("MOVER-D", 7), ("MOVER-D", 22)} <= covered
        assert all(preset.ready and str(preset.slot).startswith("21.") for preset in tilt)
        assert all("TILT" in preset.name for preset in tilt)

    def test_no_period_anywhere_in_the_line_holds_the_cells(self) -> None:
        grid = _grid()
        _clear_mover_u_periods(grid)
        held = _named(_plan(grid), "WAVE PAN")
        assert [(cell.group_name, cell.bar) for cell in held.cells] == [
            ("MOVER-U", 11),
            ("MOVER-U", 18),
        ]
        assert held.ready is False
        assert held.slot is None
        assert held.store is None
        assert held.value == "효과 · 웨이브 · Pan · 주기 미정"
        assert "주기" in (held.hold or "")
        assert "None" not in held.name
        assert "None" not in held.value

    def test_no_effect_pool_read_holds_the_preset_with_a_plain_reason(self) -> None:
        plan = _plan(_grid(), effect_pool=None)
        assert [preset for preset in _effect_presets(plan) if preset.ready] == []
        assert _named(plan, "WAVE PAN 2 BEAT").hold == _POOL_HOLD

    def test_unconfirmed_group_number_holds_the_store_line(self) -> None:
        grid = _grid()
        _track(grid, "MOVER-U")["group_no_confirmed"] = False
        plan = _plan(grid)
        preset = _named(plan, "WAVE PAN 2 BEAT")
        assert preset.ready is False
        assert preset.store is None
        assert preset.slot is None
        assert preset.hold == "그룹 번호가 확인되지 않음: MOVER-U"
        assert not any(
            "Store Preset 21." in line and "WAVE PAN" in line for line in save_commands(plan)
        )


class TestEffectPresetRoundTrip:
    def test_saved_preset_is_stored_and_the_cells_point_at_its_slot(self) -> None:
        grid = _grid()
        plan = _plan(grid)
        lines = save_commands(plan)
        assert "Store Preset 21.8 'WAVE PAN 2 BEAT' /Universal" in lines
        assert "Label Preset 21.8 'WAVE PAN 2 BEAT'" in lines

        updated = _approve(grid, plan)
        for bar in (11, 18):
            cue = _cue(updated, "MOVER-U", bar)
            assert cue["effect_preset_no"] == "21.8"
            assert cue["effect_kind"] == "position"
            # 움직임은 지우지 않는다 — 화면의 무빙 빔과 방향 값이 읽는다. 대신 이 효과 번호가
            # 움직임을 대신 낸다는 표식이 붙어 송신은 효과 번호 한 줄만 낸다.
            assert cue["app_movement"] == _cue(grid, "MOVER-U", bar)["app_movement"]
            assert cue["movement_effect_no"] == "21.8"
            # 격자 원본은 승인 뒤에도 그대로다(사본을 돌려준다)
            assert _cue(grid, "MOVER-U", bar)["app_movement"] is not None

    def test_the_moved_cells_now_wait_for_item_4_not_for_5_7_9(self) -> None:
        grid = _grid()
        updated = _approve(grid, _plan(grid))
        for bar in (11, 18):
            assert required_m1_items_for_cue(_cue(updated, "MOVER-U", bar)) == frozenset({4})
            assert required_m1_items_for_cue(_cue(grid, "MOVER-U", bar)) == frozenset({5, 7, 9})

    def test_default_grid_blocks_ten_cells_before_approval(self) -> None:
        blocked = _m1_blocked(_emit(_grid(), _LIVE_M1))
        assert len(blocked) == 10
        assert {("MOVER-U", 11), ("MOVER-U", 18)} <= blocked

    def test_item_4_passing_clears_every_moved_cell(self) -> None:
        grid = _grid()
        updated = _approve(grid, _plan(grid))
        assert _m1_blocked(_emit(grid, _PASSED_4)) == {("MOVER-U", 11), ("MOVER-U", 18)}
        assert _m1_blocked(_emit(updated, _PASSED_4)) == set()

    def test_measured_tilt_cells_still_emit_after_approval(self) -> None:
        # ④ 통과(실기 2026-10-16)면 효과 번호를 받은 Tilt 칸도 막히지 않는다.
        grid = _grid()
        updated = _approve(grid, _plan(grid))
        tilt = [c for c in _track(updated, "MOVER-D")["cues"] if c["bar"] in (7, 22)]
        assert all(c.get("effect_preset_no") for c in tilt)
        blocked = _m1_blocked(_emit(updated, _PASSED_4))
        assert ("MOVER-D", 7) not in blocked
        assert ("MOVER-D", 22) not in blocked


class TestEffectPlanTiming:
    def test_bpm_and_beats_per_bar_come_from_the_bar_map(self) -> None:
        # 세션이 쓰는 곡 타이밍과 같은 출처: bar_map 의 bpm·time_signature·1마디 시작.
        timeline = {
            "bar_map": {
                "bpm": 112.0,
                "time_signature": [4, 4],
                "bars": [{"bar": 1, "start_ms": 1500}],
            }
        }
        assert effect_plan_timing(timeline) == (112.0, 4)

    def test_missing_timing_gives_nothing_to_guess_from(self) -> None:
        assert effect_plan_timing({}) == (None, None)
        assert effect_plan_timing("not a timeline") == (None, None)


class TestEffectLineThroughTheSession:
    def test_the_card_stores_the_effect_at_the_song_bpm(self, tmp_path, monkeypatch) -> None:
        # 세션 경로: 풀 「All 1」(21) 판독 → 계획 → 승인 카드. BPM 112.35 는 곡 bar_map 에서 온다.
        # 거절로 응답해 격자와 콘솔은 건드리지 않는다 — 카드에 올라온 줄만 본다.
        grid = copy.deepcopy(default_beat_grid(LOVE_ATTACK_TITLE))
        store = SongTimelineStore()
        store.latest = _timeline_for_apply(beat_grid=grid)
        state_tree = {
            **_state_tree(),
            "DataPool/PresetPools": _pool_list_payload(
                {"Dimmer": 1, "Position": 2, "Color": 4, "All 1": 21}
            ),
            "DataPool/PresetPools/1": _pool_children_payload(_DIMMER_CHILDREN),
            "DataPool/PresetPools/2": _pool_children_payload(_POSITION_CHILDREN),
            "DataPool/PresetPools/4": _pool_children_payload(_COLOR_CHILDREN),
            "DataPool/PresetPools/21": _pool_children_payload(
                {**{slot: f"EFX {slot}" for slot in range(1, 8)}, 301: "EFX 301"}
            ),
        }
        session, _console, approval, _audit = _new_session(
            tmp_path, store=store, decisions=(False,), state_tree=state_tree
        )
        monkeypatch.setattr(
            session,
            "_beat_grid_preset_dimmer_attributes",
            lambda names: dict(_ATTRIBUTES),
        )

        session.beat_grid_preset_plan()

        assert len(approval.requests) == 1
        card = list(approval.requests[0].commands)
        assert any("Store Preset 21.8 'WAVE PAN 2 BEAT' /Universal" in line for line in card)
        # 실서버(full2 D-12)가 탄 경로 — 카드의 저장 줄이 스피드 마스터에 묶여야 한다.
        speed_master = load_preset_pool_policy()["speed_master"]
        assert any(f"Master 3.{speed_master} At BPM 112.35" in line for line in card)
        assert any("Attribute 'Pan' At Measure 2" in line for line in card)
        assert any(f"Attribute 'Pan' At SpeedMaster {speed_master}" in line for line in card)
        assert not any("Attribute 'Pan' At Speed " in line for line in card)
