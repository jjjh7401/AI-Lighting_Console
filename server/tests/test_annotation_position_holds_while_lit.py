"""주석 위치는 같은 줄이 켜진 채 이어지는 칸까지 머문다 — 곡 첫 부분 MIB (full2 D-09).

full2 실서버: 주석(``preset_annotations/love_attack.yaml``)이 0마디 MOVER-U·D 를 「바닥 쪽」으로
정했고, 자동 배치는 4마디도 켠 채 Home 으로 뒀다. 반영 알림 「4마디 MIB 불가 — 앞 큐가 켜져 있어
켜진 채 이동합니다」 2건. 주석 위치가 처음 꺼지는 칸까지 머물면 위치는 어둠 뒤에서만 바뀐다.
"""

from __future__ import annotations

import copy

from server.design.arrange_apply import apply_arrangement_draft
from server.design.arrange_segments import generate_segment_draft
from server.design.beat_grid import LOVE_ATTACK_TITLE, default_beat_grid
from server.design.beat_grid_edit import load_preset_pool_policy
from server.design.beat_grid_mib import cue_is_lit, plan_mib_premoves
from server.design.beat_grid_send import build_song_timing_from_bar_map
from server.design.preset_plan import build_preset_plan, load_preset_annotations

from .test_arrange_segments import _real_love_attack
from .test_movement_effect_preset import _ATTRIBUTES, _COLOR, _DIMMER, _EFFECT

#: 위치 풀 2 — 1~6 이 찼다고 두는 픽스처(콘솔 판독 아님).
_POSITION = (2, {slot: f"POS {slot}" for slot in range(1, 7)})
_MOVERS = ("MOVER-U", "MOVER-D")


def _generated() -> tuple[dict, dict]:
    bar_map = _real_love_attack()
    base = copy.deepcopy(default_beat_grid(LOVE_ATTACK_TITLE))
    grid, _ = apply_arrangement_draft(base, generate_segment_draft(bar_map, base["tracks"]))
    return grid, bar_map


def _plan(grid: dict, bpm: float):
    return build_preset_plan(
        grid,
        annotations=load_preset_annotations(LOVE_ATTACK_TITLE),
        policy=load_preset_pool_policy(),
        dimmer_pool=_DIMMER,
        color_pool=_COLOR,
        position_pool=_POSITION,
        dimmer_attributes=_ATTRIBUTES,
        effect_pool=_EFFECT,
        bpm=bpm,
        beats_per_bar=4,
    )


def _cues(grid: dict, group: str) -> list[dict]:
    track = next(t for t in grid["tracks"] if t["group_name"] == group)
    return sorted(track["cues"], key=lambda cue: cue["bar"])


def test_the_floor_annotation_holds_until_the_first_dark_cell() -> None:
    grid, bar_map = _generated()
    plan = _plan(grid, float(bar_map["bpm"]))
    for group in _MOVERS:
        cues = _cues(grid, group)
        # 전제(감독 결정 D1): 곡 첫 0~3마디는 어둡고, 4마디부터 켜진 칸이 처음 선다.
        # 이 전제가 바뀌면 여기서 알린다.
        assert cues[0]["bar"] == 0 and not cue_is_lit(cues[0])
        first_lit = next(cue["bar"] for cue in cues if cue_is_lit(cue))
        assert first_lit == 4
        first_dark = next(
            cue["bar"] for cue in cues if cue["bar"] > first_lit and not cue_is_lit(cue)
        )
        lit_run = [cue["bar"] for cue in cues if first_lit <= cue["bar"] < first_dark]
        floor = next(p for p in plan.presets if p.kind == "position" and p.name == f"FLOOR {group}")
        # D1: 어둠 머리 첫 마디(0마디)에도 바닥 위치를 실어 둔다.
        # 그래서 4마디부터 켜질 때 옮기지 않는다(어둠 속 사전이동).
        assert [cell.bar for cell in floor.cells] == [cues[0]["bar"], *lit_run]
        # 계획 위치(Home 등)는 그 칸들을 잡지 않는다 — 한 칸에 위치가 둘이 아니다.
        others = {
            cell.bar
            for p in plan.presets
            if p.kind == "position" and p is not floor
            for cell in p.cells
            if cell.group_name == group
        }
        assert others.isdisjoint(lit_run)


def test_with_the_planned_numbers_no_mover_moves_while_lit_at_the_song_start() -> None:
    grid, bar_map = _generated()
    plan = _plan(grid, float(bar_map["bpm"]))
    # 저장·승인 뒤 칸이 받을 위치 번호를 계획에서 그대로 붙인다(위치 저장 줄은 콘솔 판독 뒤에 붙어
    # 이 시험에선 ``apply_plan_references`` 가 번호를 쓰지 않는다 — 그래서 직접 붙인다).
    numbered = copy.deepcopy(grid)
    for preset in plan.presets:
        if preset.kind != "position" or preset.slot is None:
            continue
        for cell in preset.cells:
            for cue in _cues(numbered, cell.group_name):
                if cue["bar"] == cell.bar:
                    cue["position_preset_no"] = preset.slot
    timing = build_song_timing_from_bar_map(bar_map)
    assert timing is not None
    for group in _MOVERS:
        cues = _cues(numbered, group)
        # 전제(감독 결정 D1): 0~3마디는 어둡고, 4마디부터 켜진 칸이 처음 선다.
        # 그 칸에 위치 번호가 붙어야 잰다.
        first_lit = next(cue for cue in cues if cue_is_lit(cue))
        assert first_lit["position_preset_no"] is not None
        # 반영 단계와 같은 MIB 판정(beat_grid_mib) — 처음 켜진 구간에 켜진 채 이동이 없다.
        # 「켜진 채 움직임 시작」은 감독 결정 D3(a) 의 경고라서 이동 위반으로 세지 않는다.
        first_dark = next(
            cue["bar"] for cue in cues if cue["bar"] > first_lit["bar"] and not cue_is_lit(cue)
        )
        _premoves, notes = plan_mib_premoves(cues, timing)
        lit_moves = [
            n for n in notes if "켜진 채 이동" in n and int(n.split("마디")[0]) <= first_dark
        ]
        assert lit_moves == [], (group, lit_moves)
