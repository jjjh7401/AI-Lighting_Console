"""칸 라벨 편집 시험 — 편집 경로(apply_beat_grid_edit)가 라벨을 받는다.

제안을 「적용」하면 효과 종류뿐 아니라 칸 라벨(화면의 막대 이름표)도 바뀌어야 한다.
이 시험은 편집 경로 자체의 라벨 규칙을 본다: 한 줄짜리 글, 40자 이하, 빈 글 거절,
같은 줄에만 쓰기, 원자적 거절.
"""

from __future__ import annotations

import copy

import pytest

from server.design.beat_grid import LOVE_ATTACK_TITLE, default_beat_grid
from server.design.beat_grid_edit import (
    EDITABLE_CUE_FIELD_LABELS,
    BeatGridEditError,
    apply_beat_grid_edit,
)


def _grid() -> dict:
    grid = dict(default_beat_grid(LOVE_ATTACK_TITLE))
    grid["tracks"] = [{**track, "cues": []} for track in grid["tracks"]]
    return grid


def _cue(grid: dict, track_name: str, bar: int) -> dict | None:
    for track in grid["tracks"]:
        if track["group_name"] == track_name:
            return next((cue for cue in track["cues"] if cue["bar"] == bar), None)
    raise AssertionError(f"트랙 없음: {track_name}")


def test_label_is_an_editable_field_with_a_korean_name() -> None:
    assert EDITABLE_CUE_FIELD_LABELS["label"] == "라벨"


def test_label_change_sets_the_cue_label_and_reports_it() -> None:
    updated, report = apply_beat_grid_edit(
        _grid(), bar=17, target="STROBE", changes={"label": "스트로브 1마디"}
    )
    assert _cue(updated, "STROBE", 17)["label"] == "스트로브 1마디"
    assert any("라벨" in line and "17마디" in line for line in report)


def test_label_change_creates_the_cue_when_the_bar_has_none() -> None:
    grid = _grid()
    assert _cue(grid, "BLIND", 9) is None
    updated, _ = apply_beat_grid_edit(
        grid, bar=9, target="BLIND", changes={"label": "블라인드 2박"}
    )
    assert _cue(updated, "BLIND", 9)["label"] == "블라인드 2박"


def test_label_and_effect_kind_apply_together() -> None:
    updated, _ = apply_beat_grid_edit(
        _grid(),
        bar=17,
        target="STROBE",
        changes={"label": "스트로브 1마디", "effect_kind": "dimmer"},
    )
    cue = _cue(updated, "STROBE", 17)
    assert cue["label"] == "스트로브 1마디"
    assert cue["effect_kind"] == "dimmer"


def test_label_change_leaves_structured_fields_of_the_cue_alone() -> None:
    first, _ = apply_beat_grid_edit(
        _grid(), bar=17, target="STROBE", changes={"effect_kind": "dimmer"}
    )
    second, _ = apply_beat_grid_edit(
        first, bar=17, target="STROBE", changes={"label": "스트로브 1마디"}
    )
    cue = _cue(second, "STROBE", 17)
    assert cue["effect_kind"] == "dimmer"
    assert cue["label"] == "스트로브 1마디"


def test_label_change_touches_only_the_target_row() -> None:
    updated, _ = apply_beat_grid_edit(
        _grid(), bar=17, target="STROBE", changes={"label": "스트로브 1마디"}
    )
    assert _cue(updated, "BACK", 17) is None


@pytest.mark.parametrize("bad", ["", "   ", "a\nb", "탭\t글", "x" * 41, 5])
def test_invalid_label_is_rejected_with_a_label_reason(bad) -> None:
    with pytest.raises(BeatGridEditError) as excinfo:
        apply_beat_grid_edit(_grid(), bar=17, target="STROBE", changes={"label": bad})
    assert "라벨" in str(excinfo.value)


def test_label_of_exactly_forty_characters_is_accepted() -> None:
    updated, _ = apply_beat_grid_edit(
        _grid(), bar=17, target="STROBE", changes={"label": "가" * 40}
    )
    assert _cue(updated, "STROBE", 17)["label"] == "가" * 40


def test_rejected_label_leaves_the_grid_untouched_even_with_other_changes() -> None:
    """부분 적용 금지 — 라벨이 거절되면 같이 온 효과 종류도 쓰이지 않는다."""
    grid = _grid()
    before = copy.deepcopy(grid)
    with pytest.raises(BeatGridEditError):
        apply_beat_grid_edit(
            grid, bar=17, target="STROBE", changes={"effect_kind": "dimmer", "label": ""}
        )
    assert grid == before


def test_unknown_field_still_rejected_and_message_lists_the_label_field() -> None:
    with pytest.raises(BeatGridEditError) as excinfo:
        apply_beat_grid_edit(_grid(), bar=17, target="STROBE", changes={"not_a_real_field": 1})
    assert "not_a_real_field" in str(excinfo.value)
    assert "라벨" in str(excinfo.value)
