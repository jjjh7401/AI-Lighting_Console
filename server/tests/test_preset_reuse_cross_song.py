"""SPEC-LDRHYTHM-001 WT-preset-reuse-cross-song — 다른 곡을 새로 분석해도 콘솔에 이미
저장한 프리셋을 다시 쓴다.

리드 새 곡 점검(2026-10-18, 「FRESH TEST 1018」 = LOVE ATTACK 음원에 ID3 제목만 바꿈,
sha256 4a739547…):
직전 작업본(LOVE ATTACK, 9ab52dfb…)에는 저장 기록(``dimmer_presets`` 5 · ``preset_colors`` 6 ·
``preset_labels`` 20 · ``preset_movements`` 2 · ``preset_positions`` 6)이 있었는데, 새 분석이 연 새
작업본은 다섯 기록이 모두 비었고 계획은 프리셋 18개를 전부 새 번호로 저장했다(재사용 0).

원인: 새 분석이 기록을 옮기는 조건이 「같은 곡」이다(``session.py`` ``same_song and …`` →
``carry_console_preset_records``). 프리셋 기록은 곡의 것이 아니라 콘솔에 지금 있는 것의 사실이다
(``analysis_timeline.CONSOLE_PRESET_RECORD_KEYS``). 내용이 같은지는 재사용 판정이 기록·콘솔 이름으로
따로 가른다. 콘솔 접촉 0건.
"""

from __future__ import annotations

import copy

from server.design.analysis_timeline import CONSOLE_PRESET_RECORD_KEYS
from server.design.preset_plan import (
    _effect_signature,
    _json_signature,
    _reusable_color_slot,
    _reusable_dimmer_slot,
    _reusable_effect_slot,
    _reusable_position_slot,
)

from .test_new_analysis_timeline import _session
from .test_preset_reuse_after_new_analysis import _RECORDS


def test_a_new_analysis_of_another_song_keeps_the_console_preset_records(
    tmp_path, monkeypatch
) -> None:
    session, store, _sent, _console, _library = _session(tmp_path, monkeypatch)
    store.latest = {
        **store.latest,
        "song_title": "OTHER SONG",
        "beat_grid": {
            **store.latest["beat_grid"],
            **copy.deepcopy(_RECORDS),
            "song_title": "OTHER SONG",
        },
    }

    session.analyse_bar_map(1)

    fresh = store.latest["beat_grid"]
    assert fresh.get("source") == "analysis"
    assert sum(len(track["cues"]) for track in fresh["tracks"]) == 0
    for key in CONSOLE_PRESET_RECORD_KEYS:
        assert fresh.get(key) == _RECORDS[key], key


# -- 이어받은 기록은 콘솔에 그 번호가 지금 있고 이름·기록이 같을 때만 재사용 근거다 -----------
#
# 콘솔 풀은 ``(풀 번호, {슬롯: 콘솔 이름})``. 세 경우: 그대로 있음(「#숫자」 붙음) → 재사용,
# 기록은 있는데 콘솔에 없음 → 재사용 안 함, 같은 번호에 다른 이름 → 재사용 안 함.

_MOVEMENT = {"shape": "sine", "axes": ["pan"], "period_unit": "bar", "period_value": 2}
_POSITION = {"group": "MOVER-U", "aim": "Center", "value": "중앙 (계획)"}
_INHERITED = {
    "dimmer_presets": {"1.912": {"percent": 100, "attribute_group_nos": [["Dimmer", [3]]]}},
    "preset_colors": {"4.147": {"r": 0, "g": 60, "b": 100, "groups": ["WASH-ALL"]}},
    "preset_labels": {
        "1.912": "DIM-100",
        "4.147": "SKY",
        "21.19": "WAVE PAN 2 BAR",
        "2.87": "CENTER MOVER-U",
    },
    "preset_movements": {
        "21.19": {
            "group_no": 11,
            "signature": _json_signature(_effect_signature(_MOVEMENT)),
            "bpm": 112.0,
        }
    },
    "preset_positions": {"2.87": dict(_POSITION)},
    "tracks": [],
}

_CASES = {
    "present": {
        1: (1, {912: "DIM-100#2"}),
        4: (4, {147: "SKY#3"}),
        21: (21, {19: "WAVE PAN 2 BAR"}),
        2: (2, {87: "CENTER MOVER-U#5"}),
    },
    "missing": {
        1: (1, {913: "DIM-100"}),
        4: (4, {148: "SKY"}),
        21: (21, {20: "WAVE PAN 2 BAR"}),
        2: (2, {88: "CENTER MOVER-U"}),
    },
    "renamed": {
        1: (1, {912: "DIM-50"}),
        4: (4, {147: "PINK"}),
        21: (21, {19: "WAVE TILT 2 BAR"}),
        2: (2, {87: "HOME MOVER-U"}),
    },
}


def _reuse(case: str) -> dict[str, str | None]:
    pools = _CASES[case]
    grid = copy.deepcopy(_INHERITED)
    return {
        "dimmer": _reusable_dimmer_slot(grid, pools[1], "DIM-100", 100, [("Dimmer", (3,))]),
        "color": _reusable_color_slot(grid, pools[4], (0, 60, 100), "WASH-ALL"),
        "effect": _reusable_effect_slot(
            grid,
            pools[21],
            name="WAVE PAN 2 BAR",
            group_name="MOVER-U",
            group_no=11,
            movement=_MOVEMENT,
            bpm=112.0,
        ),
        "position": _reusable_position_slot(grid, pools[2], "CENTER MOVER-U", dict(_POSITION)),
    }


def test_an_inherited_record_is_reused_when_the_console_still_holds_that_preset() -> None:
    assert _reuse("present") == {
        "dimmer": "1.912",
        "color": "4.147",
        "effect": "21.19",
        "position": "2.87",
    }


def test_an_inherited_record_whose_number_is_gone_from_the_console_is_not_reused() -> None:
    assert _reuse("missing") == dict.fromkeys(("dimmer", "color", "effect", "position"))


def test_an_inherited_record_whose_console_name_changed_is_not_reused() -> None:
    # 색·효과는 전에는 기록만 보고 판정해서, 같은 번호가 다른 이름이어도 재사용했다.
    assert _reuse("renamed") == dict.fromkeys(("dimmer", "color", "effect", "position"))
