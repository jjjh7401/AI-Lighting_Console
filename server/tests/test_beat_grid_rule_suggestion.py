"""자동 배치 규칙 AI 제안 소스 시험 (WT-beatgrid-suggest-real).

규칙 소스는 열린 곡의 마디 지도와 격자에서 한 칸을 고른다. 칸 종류는 생성기 라벨을 편집 경로가
받는 구조화 필드 ``effect_kind`` 로 옮겨 제안하고, 「적용」은 기존 편집 경로가 맡는다. 세션 시험은
가짜 콘솔로 돌아 콘솔 쓰기가 없음을 함께 확인한다(``FakeConsole.executed == []``).
"""

from __future__ import annotations

import pytest

from server.audio.bar_map_store import build_bar_map_payload
from server.design.arrange_generator import (
    BLIND_LABEL,
    CHASE_LABEL,
    MOTION_LABEL,
    PULSE_LABEL,
    REST_LABEL,
    STROBE_LABEL,
    generate_arrangement_draft,
)
from server.design.beat_grid import LOVE_ATTACK_TITLE, default_beat_grid
from server.design.beat_grid_suggestion_rules import ArrangementRuleSuggestionSource
from server.web.session import SongTimelineStore

from .test_session_beat_grid_edit_t551 import _new_session

BARS = 40
EVENTS = [
    {"kind": "kick_entry", "start_bar": 9, "end_bar": 9, "start_beat": 1, "grade": "measured"},
    {"kind": "drop", "start_bar": 17, "end_bar": 18, "start_beat": 1, "grade": "measured"},
]

#: 시험이 기대하는 라벨 → effect_kind. 휴식 칸은 효과가 없다(None).
EXPECTED_EFFECT = {
    MOTION_LABEL: "position",
    PULSE_LABEL: "dimmer",
    BLIND_LABEL: "dimmer",
    STROBE_LABEL: "dimmer",
    CHASE_LABEL: "mixed",
    REST_LABEL: None,
}


def _bar_map() -> dict:
    beats = [index * 500 for index in range(BARS * 4)]
    return build_bar_map_payload(beats, 0, bpm=120.0, events=EVENTS)


def _grid() -> dict:
    """리그 트랙 구성만 가져온 격자 — 손으로 찍은 칸(cues)은 비운다."""
    grid = dict(default_beat_grid(LOVE_ATTACK_TITLE))
    grid["tracks"] = [{**track, "cues": []} for track in grid["tracks"]]
    return grid


def _find_cell(bar_map: dict, label: str) -> tuple[str, int]:
    """생성기가 그 라벨을 고르는 (줄, 마디) 한 칸 — 시험 입력을 생성기 결과에서 얻는다."""
    draft = generate_arrangement_draft(bar_map, _grid()["tracks"])
    for track in draft["tracks"]:
        for cue in track["cues"]:
            if cue["label"] == label:
                return track["group_name"], cue["bar"]
    raise AssertionError(f"라벨 {label!r} 칸이 초안에 없다")


def _set_effect(grid: dict, track_name: str, bar: int, effect_kind: str) -> None:
    for track in grid["tracks"]:
        if track["group_name"] == track_name:
            track["cues"].append({"bar": bar, "label": "", "effect_kind": effect_kind})


def test_drop_start_on_strobe_row_proposes_dimmer_with_drop_reason() -> None:
    assert generate_arrangement_draft(_bar_map(), _grid()["tracks"])["tracks"]
    source = ArrangementRuleSuggestionSource(bar_map_of=_bar_map)
    result = source(_grid(), 17, "STROBE")
    assert result is not None
    changes, rationale = result
    assert changes == {"effect_kind": "dimmer"}
    assert "드롭 시작" in rationale
    assert STROBE_LABEL in rationale


def test_kick_entry_on_blind_row_reads_kick_reason() -> None:
    source = ArrangementRuleSuggestionSource(bar_map_of=_bar_map)
    result = source(_grid(), 9, "BLIND")
    assert result is not None
    changes, rationale = result
    assert changes == {"effect_kind": "dimmer"}
    assert "킥 진입" in rationale


def test_rest_cell_with_an_effect_proposes_clearing_it() -> None:
    bar_map = _bar_map()
    track, bar = _find_cell(bar_map, REST_LABEL)
    grid = _grid()
    _set_effect(grid, track, bar, "dimmer")
    result = ArrangementRuleSuggestionSource(bar_map_of=lambda: bar_map)(grid, bar, track)
    assert result is not None
    assert result[0] == {"effect_kind": None}


def test_cell_already_matching_the_rule_proposes_nothing() -> None:
    bar_map = _bar_map()
    track, bar = _find_cell(bar_map, STROBE_LABEL)
    grid = _grid()
    _set_effect(grid, track, bar, "dimmer")
    assert ArrangementRuleSuggestionSource(bar_map_of=lambda: bar_map)(grid, bar, track) is None


def test_every_rule_label_maps_to_its_effect_kind() -> None:
    """생성기가 실제로 고르는 라벨마다 제안 값이 표와 같아야 한다 — 표가 어긋나면 여기서 잡힌다."""
    bar_map = _bar_map()
    draft = generate_arrangement_draft(bar_map, _grid()["tracks"])
    source = ArrangementRuleSuggestionSource(bar_map_of=lambda: bar_map)
    seen: set[str] = set()
    for track in draft["tracks"]:
        for cue in track["cues"]:
            label = cue["label"]
            if label not in EXPECTED_EFFECT:
                continue
            seen.add(label)
            result = source(_grid(), cue["bar"], track["group_name"])
            expected = EXPECTED_EFFECT[label]
            where = (track["group_name"], cue["bar"], label)
            if expected is None:
                assert result is None, where
            else:
                assert result is not None and result[0] == {"effect_kind": expected}, where
    assert len(seen) >= 4, f"관찰된 라벨이 너무 적다: {sorted(seen)}"


def test_no_bar_map_means_no_suggestion() -> None:
    source = ArrangementRuleSuggestionSource(bar_map_of=lambda: None)
    assert source(_grid(), 17, "STROBE") is None


def test_unknown_row_means_no_suggestion() -> None:
    source = ArrangementRuleSuggestionSource(bar_map_of=_bar_map)
    assert source(_grid(), 17, "NO-SUCH-ROW") is None


def test_empty_track_layout_means_no_suggestion() -> None:
    source = ArrangementRuleSuggestionSource(bar_map_of=_bar_map)
    assert source({"tracks": []}, 17, "STROBE") is None


@pytest.fixture
def harness(tmp_path):
    store = SongTimelineStore()
    store.latest = {
        "song_title": "시험곡",
        "sequence_number": 1,
        "beat_grid": _grid(),
        "bar_map": _bar_map(),
    }
    sent: list[dict] = []
    session, console = _new_session(tmp_path, store=store, sent=sent)
    return session, console, store, sent


def test_session_suggest_uses_the_open_song_bar_map(harness) -> None:
    session, console, _store, _sent = harness
    event = session.beat_grid_suggest(17, "STROBE")
    assert event["type"] == "beat_grid_suggestion"
    assert (event["bar"], event["target"]) == (17, "STROBE")
    assert event["changes"] == {"effect_kind": "dimmer"}
    assert "드롭 시작" in event["rationale"]
    assert console.executed == []


def test_session_suggest_without_bar_map_says_no_suggestion(tmp_path) -> None:
    store = SongTimelineStore()
    store.latest = {"song_title": "시험곡", "sequence_number": 1, "beat_grid": _grid()}
    session, console = _new_session(tmp_path, store=store, sent=[])
    event = session.beat_grid_suggest(17, "STROBE")
    assert event["type"] == "chat_response"
    assert "제안이 없습니다" in event["text"]
    assert console.executed == []


def test_suggestion_apply_writes_effect_kind_into_grid_only(harness) -> None:
    session, console, store, _sent = harness
    suggestion = session.beat_grid_suggest(17, "STROBE")
    session.beat_grid_suggestion_apply(suggestion["suggestion_id"])
    grid = store.latest["beat_grid"]
    cue = next(
        cue
        for track in grid["tracks"]
        if track["group_name"] == "STROBE"
        for cue in track["cues"]
        if cue["bar"] == 17
    )
    assert cue["effect_kind"] == "dimmer"
    assert console.executed == []
