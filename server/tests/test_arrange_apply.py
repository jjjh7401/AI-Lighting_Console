"""배치 초안 적용 함수와 보류 저장소 시험 — SPEC-LDARRANGE-001 두 번째 묶음.

적용은 칸이 없는 마디에도 칸을 만들고, 있는 칸의 라벨을 초안 값으로 바꾼다. 손으로 넣은 밝기·
프리셋 같은 구조화 필드는 그대로 둔다. 검증에 걸리면 원본 격자는 그대로다.
"""

from __future__ import annotations

import copy

import pytest

from server.audio.bar_map_store import build_bar_map_payload
from server.design.arrange_apply import ArrangementApplyError, apply_arrangement_draft
from server.design.arrange_draft_store import PendingDraftStore
from server.design.arrange_generator import generate_arrangement_draft
from server.design.beat_grid import LOVE_ATTACK_TITLE, default_beat_grid

EVENTS = [
    {"kind": "kick_entry", "start_bar": 9, "end_bar": 9, "start_beat": 1, "grade": "measured"},
    {"kind": "drop", "start_bar": 17, "end_bar": 18, "start_beat": 1, "grade": "measured"},
]


def _layout() -> list[dict]:
    return list(default_beat_grid(LOVE_ATTACK_TITLE)["tracks"])


def _draft(bars: int = 40, layout: list[dict] | None = None) -> dict:
    beats = [index * 500 for index in range(bars * 4)]
    bar_map = build_bar_map_payload(beats, 0, bpm=120.0, events=EVENTS)
    return generate_arrangement_draft(bar_map, _layout() if layout is None else layout)


def _grid() -> dict:
    return copy.deepcopy(default_beat_grid(LOVE_ATTACK_TITLE))


def _track(grid: dict, name: str) -> dict:
    return next(track for track in grid["tracks"] if track["group_name"] == name)


def test_creates_cells_for_bars_the_grid_did_not_have() -> None:
    grid = _grid()
    assert 30 not in {cue["bar"] for cue in _track(grid, "BACK")["cues"]}
    updated, _report = apply_arrangement_draft(grid, _draft())
    assert 30 in {cue["bar"] for cue in _track(updated, "BACK")["cues"]}


def test_applying_widens_the_grid_bar_range_to_the_draft() -> None:
    # 「채운 범위」와 「N마디~ 아직 배치 안 함」은 bar_range 로 그린다. 칸을 40마디까지 만들고
    # bar_range 를 기본값 0~25 에 두면 26마디부터 칸이 있는데도 빗금으로 보인다.
    grid = _grid()
    assert grid["bar_range"] == {"start": 0, "end": 25}
    updated, _report = apply_arrangement_draft(grid, _draft())
    assert updated["bar_range"] == {"start": 0, "end": 40}


def test_applying_a_draft_inside_the_range_keeps_the_bar_range() -> None:
    updated, _report = apply_arrangement_draft(_grid(), _draft(bars=20))
    assert updated["bar_range"] == {"start": 0, "end": 25}


def _approved(cue: dict, source: str) -> dict:
    return {
        **cue,
        "evidence": {
            "grade": None,
            "approval": {"by": "supervisor", "date": "2026-10-16", "source": source},
        },
    }


def test_replaces_seed_cells_with_the_draft_cell() -> None:
    # 시드 칸(손 설계 원본)은 초안 칸으로 바뀐다 — 라벨만 바꾸고 남기면 칸이 조각난다.
    grid = _grid()
    draft = _draft()
    draft_cell = next(
        cue
        for cue in next(t for t in draft["tracks"] if t["group_name"] == "BACK")["cues"]
        if cue["bar"] == 7
    )
    updated, _report = apply_arrangement_draft(grid, draft)
    after = next(cue for cue in _track(updated, "BACK")["cues"] if cue["bar"] == 7)
    assert after["source_ref"] == draft_cell["source_ref"]
    draft_bars = {
        cue["bar"] for cue in next(t for t in draft["tracks"] if t["group_name"] == "BACK")["cues"]
    }
    first = draft["bar_range"]["start"]
    in_range = {cue["bar"] for cue in _track(updated, "BACK")["cues"] if cue["bar"] >= first}
    assert in_range == draft_bars


def test_keeps_a_director_edited_cell_and_skips_the_draft_cell_there() -> None:
    grid = _grid()
    back = _track(grid, "BACK")
    back["cues"] = [
        _approved(cue, "beat_grid_apply:abc") if cue["bar"] == 3 else cue for cue in back["cues"]
    ]
    kept = copy.deepcopy(next(cue for cue in back["cues"] if cue["bar"] == 3))
    updated, report = apply_arrangement_draft(grid, _draft())
    assert next(cue for cue in _track(updated, "BACK")["cues"] if cue["bar"] == 3) == kept
    assert "감독이 고친 칸 1개" in report[0]


def test_preset_plan_approval_alone_is_not_a_director_edit() -> None:
    grid = _grid()
    back = _track(grid, "BACK")
    back["cues"] = [
        _approved(cue, "preset_plan:abc") if cue["bar"] == 3 else cue for cue in back["cues"]
    ]
    updated, _report = apply_arrangement_draft(grid, _draft())
    cell = next(cue for cue in _track(updated, "BACK")["cues"] if cue["bar"] == 3)
    assert str(cell["source_ref"]).startswith("arrangement_")


def test_applying_the_same_draft_twice_gives_the_same_grid() -> None:
    draft = _draft()
    once, _ = apply_arrangement_draft(_grid(), draft)
    twice, _ = apply_arrangement_draft(once, draft)
    assert twice == once


def test_cells_outside_the_draft_range_are_untouched() -> None:
    grid = _grid()
    back = _track(grid, "BACK")
    outside = {"bar": 60, "label": "범위 밖"}
    back["cues"].append(outside)
    updated, _report = apply_arrangement_draft(grid, _draft(bars=40))
    assert outside in _track(updated, "BACK")["cues"]


def test_creates_a_track_the_grid_did_not_have() -> None:
    layout = _layout() + [
        {"group_no": 99, "group_no_confirmed": False, "group_name": "EXTRA", "layer_role": None}
    ]
    grid = _grid()
    assert "EXTRA" not in {track["group_name"] for track in grid["tracks"]}
    updated, _report = apply_arrangement_draft(grid, _draft(layout=layout))
    extra = _track(updated, "EXTRA")
    assert extra["group_no"] == 99
    assert len(extra["cues"]) == 40


def test_overlap_is_refused_and_the_grid_stays_unchanged() -> None:
    draft = copy.deepcopy(_draft())
    draft["tracks"].append(
        {
            "group_no": 99,
            "group_no_confirmed": True,
            "group_name": "MOVER-ALL",
            "layer_role": "mover",
            "cues": [{"bar": 1, "label": "정지"}],
        }
    )
    grid = _grid()
    before = copy.deepcopy(grid)
    with pytest.raises(ArrangementApplyError):
        apply_arrangement_draft(grid, draft)
    assert grid == before


def test_apply_never_mutates_the_input_grid() -> None:
    grid = _grid()
    before = copy.deepcopy(grid)
    apply_arrangement_draft(grid, _draft())
    assert grid == before


def test_report_names_the_created_and_changed_cells() -> None:
    _updated, report = apply_arrangement_draft(_grid(), _draft())
    assert report
    assert any("새로 만들" in line for line in report)


class TestPendingDraftStore:
    def test_create_peek_consume_and_consume_only_once(self) -> None:
        store = PendingDraftStore()
        draft = _draft()
        draft_id = store.create(draft)
        assert store.peek(draft_id) == draft
        assert len(store) == 1
        assert store.consume(draft_id) == draft
        assert store.consume(draft_id) is None
        assert len(store) == 0

    def test_unknown_id_is_none(self) -> None:
        store = PendingDraftStore()
        assert store.peek("no-such-draft") is None
        assert store.consume("no-such-draft") is None
