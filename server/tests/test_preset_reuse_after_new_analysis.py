"""SPEC-LDRHYTHM-001 3차 전체 실행 E-10·I-08 — 같은 곡을 다시 분석해도 저장한 프리셋을 다시 쓴다.

실서버(2026-10-17, 앱 저장본·라이브러리 백업 판독): 첫 계획 뒤 작업본(자동 v27)에는 저장 기록
(``dimmer_presets`` 1.908–1.911 · ``preset_colors`` 4.141–4.146 · ``preset_labels`` 13개 ·
``preset_movements`` 21.17·21.18)이 있었고 「분석 전 백업 (자동 v4)」에도 남았다. 그런데 새 분석이
연 새 작업본(자동 v28)은 기록이 비었고, 두 번째 계획은 17개를 전부 새 번호로 다시 저장했다
(콘솔은 같은 이름에 「#숫자」를 붙임). 원인 둘:

1. 새 분석의 새 작업본이 콘솔 저장 기록을 버린다 — 재사용 판정이 읽을 기록이 없다(11개).
2. 계획 위치(자동 배치 무빙 위치)에는 재사용 단계가 아예 없었다(6개).

콘솔 접촉 0건.
"""

from __future__ import annotations

import copy

from server.design.analysis_timeline import (
    CONSOLE_PRESET_RECORD_KEYS,
    carry_console_preset_records,
)
from server.design.beat_grid import LOVE_ATTACK_TITLE
from server.design.beat_grid_edit import load_preset_pool_policy
from server.design.preset_plan import (
    apply_plan_references,
    build_preset_plan,
    load_preset_annotations,
    save_commands,
)
from server.design.preset_plan_store import attach_color_store, attach_floor_position_store

from .test_new_analysis_timeline import _session
from .test_planned_color_presets import _applied_grid, _fake_reads
from .test_planned_positions import _COLOR_POOL, _POSITION_POOL
from .test_preset_plan_store_all import _FRAMES, _MEMBERS

_RECORDS = {
    "dimmer_presets": {"1.908": {"percent": 100, "attribute_group_nos": [["Dimmer", [3]]]}},
    "preset_colors": {"4.141": {"r": 0, "g": 60, "b": 100, "groups": ["WASH-ALL"]}},
    "preset_labels": {"4.141": "SKY", "2.75": "FLOOR MOVER-U", "21.17": "WAVE PAN 2 BAR"},
    "preset_descriptions": {"4.141": "하늘색"},
    "preset_movements": {"21.17": {"group_no": 11, "signature": ["pan"], "bpm": 112.0}},
    "preset_positions": {"2.77": {"group": "MOVER-U", "aim": "Center", "value": "중앙 (계획)"}},
}


def test_every_record_key_this_card_reads_is_carried() -> None:
    assert set(_RECORDS) == set(CONSOLE_PRESET_RECORD_KEYS)


def test_a_new_analysis_of_the_same_song_keeps_the_console_preset_records(
    tmp_path, monkeypatch
) -> None:
    session, store, _sent, _console, _library = _session(tmp_path, monkeypatch)
    store.latest["beat_grid"] = {**store.latest["beat_grid"], **copy.deepcopy(_RECORDS)}

    session.analyse_bar_map(1)

    fresh = store.latest["beat_grid"]
    assert fresh.get("source") == "analysis"
    assert sum(len(track["cues"]) for track in fresh["tracks"]) == 0
    for key, value in _RECORDS.items():
        assert fresh.get(key) == value, key


def test_a_new_analysis_of_another_song_inherits_no_preset_records(tmp_path, monkeypatch) -> None:
    session, store, _sent, _console, _library = _session(tmp_path, monkeypatch)
    store.latest["beat_grid"] = {
        **store.latest["beat_grid"],
        **copy.deepcopy(_RECORDS),
        "song_title": "OTHER SONG",
    }

    session.analyse_bar_map(1)

    fresh = store.latest["beat_grid"]
    for key in CONSOLE_PRESET_RECORD_KEYS:
        assert key not in fresh, key


def _store_plan(grid: dict, *, color_pool, position_pool):
    plan = build_preset_plan(
        grid,
        annotations=load_preset_annotations(LOVE_ATTACK_TITLE),
        policy=load_preset_pool_policy(),
        dimmer_pool=None,
        color_pool=color_pool,
        position_pool=position_pool,
        dimmer_attributes={},
    )
    members, channels = _fake_reads(grid)
    plan = attach_color_store(plan, grid, members=members, channel_names=channels)
    return attach_floor_position_store(plan, grid, members=_MEMBERS, frames=_FRAMES)


def _console_after(pool, plan, kind: str, suffix: str):
    """첫 저장 뒤 콘솔 풀 — 같은 이름이 이미 있어 콘솔이 「#숫자」를 붙였다고 본다."""
    pool_no, children = pool
    children = dict(children)
    for preset in plan.presets:
        if preset.kind == kind and preset.slot and (preset.store is not None):
            children[int(preset.slot.split(".")[1])] = f"{preset.name}{suffix}"
    return (pool_no, children)


def test_the_second_plan_after_a_new_analysis_stores_no_color_or_position_again() -> None:
    # 첫 계획: 자동 배치 적용 격자 → 색·위치 저장 → 승인 뒤 격자에 기록.
    first_grid = _applied_grid()
    first = _store_plan(first_grid, color_pool=_COLOR_POOL, position_pool=_POSITION_POOL)
    stored = [p for p in first.presets if p.kind in {"color", "position"} and p.store is not None]
    assert {p.kind for p in stored} == {"color", "position"}
    applied = apply_plan_references(
        first_grid, first, by="supervisor", date="2026-10-17", source="t"
    )
    color_pool = _console_after(_COLOR_POOL, first, "color", "#3")
    position_pool = _console_after(_POSITION_POOL, first, "position", "#5")

    # 같은 곡을 새로 분석: 칸이 빈 새 격자에 자동 배치를 다시 적용하고, 기록만 이어받는다.
    second_grid = carry_console_preset_records(applied, {"beat_grid": _applied_grid()})["beat_grid"]
    second = _store_plan(second_grid, color_pool=color_pool, position_pool=position_pool)

    by_name = {(p.kind, p.name): p for p in second.presets if p.kind in {"color", "position"}}
    for preset in stored:
        again = by_name[(preset.kind, preset.name)]
        assert again.reused is True, preset.name
        assert again.slot == preset.slot, preset.name
    commands = save_commands(second)
    for preset in stored:
        assert not any(f"Preset {preset.slot}" in line for line in commands), preset.name
