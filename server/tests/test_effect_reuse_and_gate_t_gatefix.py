"""효과 프리셋 재사용 · 반영 때 진행표 재독 · 자동 배치 무빙 변환 — 카드 WT-gate-reuse-fix.

콘솔 접촉 0건(가짜 콘솔). 효과 풀 21 · BPM · 진행표 판정은 전부 시험 입력이다(실기 판독 아님).

실기에서 본 세 가지를 재현한다.
1. 같은 이름·같은 내용의 효과 프리셋을 승인할 때마다 새 번호(21.10 · 21.11)로 또 만들었다.
2. 진행표 ④ 가 「통과」인데 저장된 격자의 낡은 판정이 반영을 막았다.
3. 자동 배치 초안의 무빙 칸은 축이 소문자 ``pan`` 이라 효과 프리셋 계획에서 거절됐고,
   그 칸은 (5,7,9) 에 막힌 채 남았다.
"""

from __future__ import annotations

import copy
import json

from server.audio.bar_map_store import build_bar_map_payload
from server.design.arrange_apply import apply_arrangement_draft
from server.design.arrange_generator import generate_arrangement_draft
from server.design.beat_grid import LOVE_ATTACK_TITLE, default_beat_grid
from server.design.beat_grid_measured import canonical_axes
from server.design.preset_plan import save_commands, saved_presets
from server.web.session import SongTimelineStore

from .test_beat_grid_emit_t549 import _LIVE_M1
from .test_beat_grid_reapply_t572 import (
    _ALL_PASS,
    _effect_cue,
    _new_session,
    _progress_table,
    _three_cell_timeline,
)
from .test_beat_grid_reapply_t572 import _cue as _t572_cue
from .test_movement_effect_preset import (
    _EFFECT,
    _approve,
    _emit,
    _m1_blocked,
    _plan,
)

_EVENTS = [
    {"kind": "kick_entry", "start_bar": 9, "end_bar": 9, "start_beat": 1, "grade": "measured"},
    {"kind": "drop", "start_bar": 17, "end_bar": 18, "start_beat": 1, "grade": "measured"},
]
_PASSED_4 = {**_LIVE_M1, 4: "통과"}


def _auto_arranged_grid() -> dict:
    """LOVE ATTACK 기본 격자 위에 자동 배치 초안을 그대로 반영한 격자."""
    grid = copy.deepcopy(default_beat_grid(LOVE_ATTACK_TITLE))
    bar_map = build_bar_map_payload([i * 500 for i in range(160)], 0, bpm=120.0, events=_EVENTS)
    layout = [
        {k: t[k] for k in ("group_no", "group_no_confirmed", "group_name", "layer_role")}
        for t in grid["tracks"]
    ]
    draft = generate_arrangement_draft(bar_map, layout)
    applied, _report = apply_arrangement_draft(grid, draft)
    return applied


def _moving_cells(grid: dict) -> list[tuple[str, int, dict]]:
    return [
        (track["group_name"], cue["bar"], cue["app_movement"])
        for track in grid["tracks"]
        for cue in track["cues"]
        if isinstance(cue.get("app_movement"), dict) and cue["app_movement"].get("shape")
    ]


class TestAutoArrangedMovementsBecomeEffectPresets:
    def test_the_generator_writes_the_console_spelling_of_the_axis(self) -> None:
        axes = {tuple(m["axes"]) for _g, _b, m in _moving_cells(_auto_arranged_grid())}
        assert ("pan",) not in axes
        assert all(set(canonical_axes(a)) == set(a) for a in axes)

    def test_a_stored_lowercase_pan_grid_is_read_as_the_same_axis(self) -> None:
        assert canonical_axes(("pan", "tilt", "Pan", "other")) == ("Pan", "Tilt", "Pan", "other")

    def test_lowercase_pan_cells_from_a_stored_grid_still_convert(self) -> None:
        grid = _auto_arranged_grid()
        for _g, _b, movement in _moving_cells(grid):
            movement["axes"] = ["pan"]  # 이전 버전이 저장해 둔 격자
        plan = _plan(grid)
        effects = [preset for preset in plan.presets if preset.kind == "effect"]
        assert effects and all(preset.ready for preset in effects), [
            (p.name, p.hold) for p in effects
        ]

    def test_every_periodic_movement_cell_points_at_an_effect_and_the_gate_clears(self) -> None:
        grid = _auto_arranged_grid()
        before = _moving_cells(grid)
        assert before, "자동 배치에 무빙 칸이 있어야 한다"
        plan = _plan(grid)
        approved = _approve(grid, plan)
        numbered = {
            (track["group_name"], cue["bar"])
            for track in approved["tracks"]
            for cue in track["cues"]
            if cue.get("effect_preset_no")
        }
        # 움직임은 효과 번호를 받아도 칸에 남는다(화면이 읽는다) — 번호를 받았는지를 본다.
        left = [
            (g, b)
            for g, b, _m in _moving_cells(approved)
            # 실기 기록으로 이미 열린 칸(MOVER-D Tilt)은 바꾸지 않는다.
            if not (g == "MOVER-D" and tuple(_m.get("axes") or ()) == ("Tilt",))
            and (g, b) not in numbered
        ]
        assert left == [], f"효과 프리셋으로 안 바뀐 칸: {left}"
        result = _emit(approved, _PASSED_4)
        assert _m1_blocked(result) == set()
        mover_lines = [line for line in result.commands if "At Preset 21." in line]
        assert mover_lines, "송신 묶음에 `At Preset 21.` 줄이 있어야 한다"


class TestEffectPresetsAreReused:
    def test_a_second_plan_reuses_the_stored_effect_presets(self) -> None:
        grid = _auto_arranged_grid()
        first = _plan(grid)
        stored = [p for p in saved_presets(first) if p.kind == "effect"]
        assert stored and all(not p.reused for p in stored)
        approved = _approve(grid, first)

        # 자동 배치를 다시 돌려 무빙 칸이 되돌아온 상황 — 격자 단위 기록(이름 · 내용)은 남는다.
        again = _auto_arranged_grid()
        for key in ("preset_labels", "preset_movements"):
            again[key] = copy.deepcopy(approved[key])
        used = {p.slot for p in stored}
        pool = (21, {**_EFFECT[1], **{int(s.split(".")[1]): "WAVE" for s in used}})
        second = _plan(again, effect_pool=pool)
        effects = [p for p in saved_presets(second) if p.kind == "effect"]
        assert {p.slot for p in effects} == used
        assert all(p.reused for p in effects)
        assert not [line for line in save_commands(second) if "Store Preset 21." in line]

    def test_the_same_name_for_another_group_is_not_reused(self) -> None:
        grid = _auto_arranged_grid()
        first = _plan(grid)
        approved = _approve(grid, first)
        again = _auto_arranged_grid()
        records = copy.deepcopy(approved["preset_movements"])
        for record in records.values():
            record["group_no"] = 999  # 다른 그룹에 저장된 같은 이름
        again["preset_labels"] = copy.deepcopy(approved["preset_labels"])
        again["preset_movements"] = records
        used = {p.slot for p in saved_presets(first) if p.kind == "effect"}
        pool = (21, {**_EFFECT[1], **{int(s.split(".")[1]): "WAVE" for s in used}})
        second = _plan(again, effect_pool=pool)
        effects = [p for p in saved_presets(second) if p.kind == "effect"]
        assert effects and not any(p.reused for p in effects)

    def test_an_unread_effect_pool_never_reuses(self) -> None:
        grid = _auto_arranged_grid()
        approved = _approve(grid, _plan(grid))
        again = _auto_arranged_grid()
        for key in ("preset_labels", "preset_movements"):
            again[key] = copy.deepcopy(approved[key])
        second = _plan(again, effect_pool=None)
        assert not [p for p in second.presets if p.kind == "effect" and p.reused]


class TestApplyReadsTheCurrentProgressFile:
    def test_a_stale_stored_item_4_does_not_block_a_fresh_apply(
        self, tmp_path, monkeypatch
    ) -> None:
        progress = tmp_path / "progress.md"
        monkeypatch.setattr("server.web.session.default_progress_md_path", lambda: progress)
        progress.write_text(_progress_table(_ALL_PASS), encoding="utf-8")
        store = SongTimelineStore()
        # 저장된 격자는 ④ 가 「미확인」이던 때의 판정을 들고 있다.
        store.latest = _three_cell_timeline({**_ALL_PASS, 4: "미확인"})
        session, console, _approval, _audit = _new_session(tmp_path, store=store)

        status = session.beat_grid_apply()

        assert status["ok"] is True
        assert any("At Preset 3.1" in line for line in console.executed), console.executed
        assert not status.get("blocked_cells")

    def test_a_progress_file_that_regressed_blocks_again(self, tmp_path, monkeypatch) -> None:
        progress = tmp_path / "progress.md"
        monkeypatch.setattr("server.web.session.default_progress_md_path", lambda: progress)
        progress.write_text(_progress_table({**_ALL_PASS, 4: "미확인"}), encoding="utf-8")
        store = SongTimelineStore()
        # 저장된 격자는 모두 「통과」라고 하지만 진행표가 우선이다.
        store.latest = _three_cell_timeline(_ALL_PASS)
        session, console, _approval, _audit = _new_session(tmp_path, store=store)

        session.beat_grid_apply()

        assert not any("At Preset 3.1" in line for line in console.executed)


def test_json_roundtrip_keeps_the_effect_records() -> None:
    grid = _auto_arranged_grid()
    approved = _approve(grid, _plan(grid))
    assert json.loads(json.dumps(approved))["preset_movements"] == approved["preset_movements"]
    # 안 쓰는 import 경고 방지용 참조
    assert _t572_cue and _effect_cue
