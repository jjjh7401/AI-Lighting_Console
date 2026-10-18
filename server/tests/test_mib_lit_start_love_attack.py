"""LOVE ATTACK 반영본의 무빙 — 켜지기 전 어둠 속 이동 (감독 결정 2026-10-18 D1·D2·D3(a)).

관찰: 곡 시작부터, 그리고 칸이 바뀔 때 무빙이 밝은 채로 움직인다.
측정(반영본 = 자동 배치 + 번호 붙임): 곡 시작에 MOVER-U·D 가 0마디부터 켜진 채 위치를 잡는다.
(어둠 0.96초). 웨이브가 꺼진 칸 없이 켜진 칸에서 시작하는 곳이 7곳이다(후렴·마지막 후렴 6, 절 1).

- D1 곡 시작: 무빙은 인트로(0~3마디)를 어둠으로 두고, 사전이동은 1마디, 4마디부터 켠다.
- D2 절 37마디 웨이브: 33마디부터 쉼, 사전이동 34마디, 37마디에 웨이브 — 어두운 시간이 4.6초 이상.
- D3(a) 후렴·마지막 후렴의 켜진 채 움직임 시작 6곳은 그대로 두고
  「켜진 채 움직임 시작」으로 표시한다.
  (콘솔의 페이저 폭 페이드는 실측된 적이 없어 (c) 대신 (a).)

콘솔 접촉 없음 — 생성기·판정기 순수 시험.
"""

from __future__ import annotations

import copy

from server.design.beat_grid_mib import (
    MIB_MIN_DARK_SECONDS,
    cue_is_lit,
    movement_lit_starts,
    plan_mib_premoves,
)
from server.design.beat_grid_send import build_song_timing_from_bar_map

from .test_annotation_position_holds_while_lit import _MOVERS, _cues, _generated, _plan


def _numbered() -> tuple[dict, object]:
    """반영 직전 칸 — 위치 번호를 계획대로 붙인다(저장·승인 뒤 칸이 받을 번호와 같다)."""
    grid, bar_map = _generated()
    plan = _plan(grid, float(bar_map["bpm"]))
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
    return numbered, timing


def test_d1_the_movers_are_dark_in_the_intro_and_light_from_bar_4_after_a_premove() -> None:
    numbered, timing = _numbered()
    for group in _MOVERS:
        cues = _cues(numbered, group)
        assert cues[0]["bar"] == 0 and not cue_is_lit(cues[0]), group
        first_lit = next(cue for cue in cues if cue_is_lit(cue))
        assert first_lit["bar"] == 4, (group, first_lit["bar"])
        # 첫 켜는 칸의 위치는 어둠 속에서 미리 잡혀 있어야 한다. 꺼진 칸이 같은 위치를 싣고 있거나,
        # 사전이동 큐가 그 위치를 어둠 속에서 쓴다.
        # 어둠은 위치를 쓴 마디부터 켜는 마디까지 4.6초 이상이다.
        if cues[0].get("position_preset_no") == first_lit.get("position_preset_no"):
            set_bar = 0
        else:
            premoves, notes = plan_mib_premoves(cues, timing)
            set_bars = [
                premove["bar"]
                for premove in premoves
                if premove["position_preset_no"] == first_lit.get("position_preset_no")
            ]
            assert set_bars, (group, notes)
            set_bar = min(set_bars)
        dark = timing.bar_start_seconds(4) - timing.bar_start_seconds(set_bar)
        assert dark >= MIB_MIN_DARK_SECONDS, (group, set_bar, dark)


def test_d2_the_verse_wave_of_mover_d_starts_after_a_dark_window() -> None:
    numbered, timing = _numbered()
    cues = _cues(numbered, "MOVER-D")
    before = next(cue for cue in cues if cue["bar"] == 33)
    wave = next(cue for cue in cues if cue["bar"] == 37)
    assert not cue_is_lit(before)
    assert wave.get("app_movement")
    premoves, notes = plan_mib_premoves(cues, timing)
    assert 34 in [premove["bar"] for premove in premoves], notes
    dark = timing.bar_start_seconds(37) - timing.bar_start_seconds(34)
    assert dark >= MIB_MIN_DARK_SECONDS, dark


def test_d3_the_six_lit_wave_starts_are_kept_and_flagged_as_lit_movement_starts() -> None:
    numbered, timing = _numbered()
    assert movement_lit_starts(_cues(numbered, "MOVER-U")) == [26, 54, 75]
    assert movement_lit_starts(_cues(numbered, "MOVER-D")) == [22, 50, 71]
    _premoves, notes = plan_mib_premoves(_cues(numbered, "MOVER-D"), timing)
    assert any(note.startswith("22마디") and "켜진 채 움직임 시작" in note for note in notes), notes
