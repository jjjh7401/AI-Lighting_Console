"""t281 — 큐시트 초안 편집: 성공 경로 · 거절 사유 · 되돌리기 · 콘솔 무접촉.

가장 무거운 단언은 마지막 계열이다: **어느 경로에서도 콘솔 명령이 나가지
않는다.** 편집·되돌리기·저장 셋 다 `run_commands` 를 부르지 않는다는 것을
레지스트리 첩자로 직접 잰다 — 「안 나갔을 것이다」가 아니라 「센 결과 0건」.
"""

from __future__ import annotations

import copy

import pytest

from server.design.cue_sheet_edit import (
    CueSheetEditError,
    apply_cue_sheet_edit,
    parse_cue_sheet_edit_request,
    section_intensity_percent,
)
from server.web.timeline_draft import DRAFT_HISTORY_LIMIT, TimelineDraftHistory
from server.web.timeline_library import SongTimelineLibrary


def _timeline() -> dict:
    return {
        "song_title": "Sugar",
        "sequence_number": 210,
        "lifecycle": "planned",
        "sections": [
            {
                "index": 0,
                "label": "INTRO",
                "start_ms": 0,
                "cue_number": 1,
                "d_level": 2,
                "palette": ["#ff00aa"],
                "position": "Center",
                "texture": "flat",
                "fx": [],
                "accents": [],
                "mib": False,
                "trig_time_seconds": None,
                "mood": "차분",
                "palette_primary": "P1 앰버",
                "intensity": [{"group": "MOVER-U", "level": 40}],
                "movement": "STATIC",
                "effect": "없음",
                "trans": "FADE",
                "fade_seconds": 2.0,
                "note": "",
            },
            {
                "index": 1,
                "label": "CHORUS",
                "start_ms": 30_000,
                "cue_number": 2,
                "d_level": 4,
                "palette": ["#00ffcc"],
                "position": "Fan Out",
                "texture": "punch",
                "fx": ["CHASE"],
                "accents": [],
                "mib": False,
                "trig_time_seconds": None,
            },
        ],
    }


# -- 성공 경로 ------------------------------------------------------------------


def test_absolute_intensity_edit_reports_before_and_after():
    before = _timeline()
    updated, report = apply_cue_sheet_edit(before, 1, {"intensity": 80})
    assert updated["sections"][0]["intensity"] == [{"group": "MOVER-U", "level": 80}]
    assert updated["sections"][0]["d_level"] == 4
    assert report == ["조도 40 → 80"]
    # 원본은 그대로다 — 되돌리기가 「직전 상태 그대로」를 복원할 수 있어야 한다.
    assert before["sections"][0]["intensity"] == [{"group": "MOVER-U", "level": 40}]


def test_relative_brighter_uses_the_sections_own_current_value():
    request = parse_cue_sheet_edit_request("이 구간 더 밝게 해줘")
    assert request == {"cue": None, "changes": {"intensity_delta": 20}}
    updated, report = apply_cue_sheet_edit(_timeline(), 1, request["changes"])
    assert section_intensity_percent(updated["sections"][0]) == 60
    assert report == ["조도 40 → 60"]


def test_text_fields_are_parsed_and_applied_with_a_field_by_field_report():
    request = parse_cue_sheet_edit_request("큐 1 무드를 격렬함으로 바꿔줘")
    assert request["cue"] == 1
    updated, report = apply_cue_sheet_edit(_timeline(), 1, request["changes"])
    assert updated["sections"][0]["mood"] == "격렬함"
    assert report == ["무드 차분 → 격렬함"]


def test_fade_and_trans_edit_together():
    updated, report = apply_cue_sheet_edit(_timeline(), 1, {"fade_seconds": 0.5, "trans": "SNAP"})
    assert updated["sections"][0]["fade_seconds"] == 0.5
    assert updated["sections"][0]["trans"] == "SNAP"
    assert report == ["전환 FADE → SNAP", "페이드 2초 → 0.5초"]


def test_a_section_without_the_optional_fields_still_edits():
    """t279 확장 필드가 없는 구간(큐 2)도 고쳐진다 — 부재가 회귀를 부르지 않는다."""
    updated, report = apply_cue_sheet_edit(_timeline(), 2, {"mood": "폭발"})
    assert updated["sections"][1]["mood"] == "폭발"
    assert report == ["무드 — → 폭발"]


# -- 거절 경로: 사유 문자열 자체를 단언한다 --------------------------------------


def test_unknown_field_is_refused_by_name_and_lists_what_is_editable():
    with pytest.raises(CueSheetEditError) as caught:
        apply_cue_sheet_edit(_timeline(), 1, {"gobo": "star"})
    message = str(caught.value)
    assert "'gobo'은(는) 큐시트가 가진 항목이 아닙니다" in message
    assert "무드" in message and "페이드" in message


def test_out_of_range_intensity_is_refused_with_the_requested_value():
    with pytest.raises(CueSheetEditError) as caught:
        apply_cue_sheet_edit(_timeline(), 1, {"intensity": 120})
    assert str(caught.value) == "조도는 0~100 사이여야 합니다 (요청값: 120)."


def test_relative_edit_below_zero_is_refused_rather_than_clamped_silently():
    with pytest.raises(CueSheetEditError) as caught:
        apply_cue_sheet_edit(_timeline(), 1, {"intensity_delta": -60})
    assert str(caught.value) == "조도는 0~100 사이여야 합니다 (요청값: -20)."


def test_unknown_cue_is_refused_and_names_the_cues_that_exist():
    with pytest.raises(CueSheetEditError) as caught:
        apply_cue_sheet_edit(_timeline(), 9, {"mood": "격렬"})
    assert str(caught.value) == "큐 9가 이 큐시트에 없습니다. (보유 큐: 1, 2)"


def test_unknown_trans_value_is_refused_and_names_the_allowed_set():
    with pytest.raises(CueSheetEditError) as caught:
        apply_cue_sheet_edit(_timeline(), 1, {"trans": "WIPE"})
    assert str(caught.value) == (
        "전환 값은 SNAP, XFADE, FADE 중 하나여야 합니다 (받은 값: 'WIPE')."
    )


def test_a_refused_edit_writes_nothing_at_all():
    """부분 적용 금지 — 사유를 던지기 전에 한 칸도 바뀌지 않는다."""
    before = _timeline()
    snapshot = copy.deepcopy(before)
    with pytest.raises(CueSheetEditError):
        apply_cue_sheet_edit(before, 1, {"mood": "격렬", "intensity": 999})
    assert before == snapshot


def test_vocabulary_this_module_does_not_own_falls_through_as_none():
    """「내 것이 아니다」와 「내 것인데 틀렸다」를 가른다 — 오라우팅 방지."""
    assert parse_cue_sheet_edit_request("타임라인 큐 3을 무대 중앙으로 수정해줘") is None
    assert parse_cue_sheet_edit_request("지금 상태 알려줘") is None


# -- 되돌리기/다시하기 -----------------------------------------------------------


def test_undo_restores_the_previous_draft_exactly():
    history = TimelineDraftHistory()
    original = _timeline()
    history.record(original)
    edited, _ = apply_cue_sheet_edit(original, 1, {"intensity": 80})
    restored = history.undo(edited)
    assert restored == original
    assert restored is not original  # 깊은 사본이라 이후 편집이 이력을 오염시키지 않는다


def test_redo_returns_the_state_undo_stepped_back_from():
    history = TimelineDraftHistory()
    original = _timeline()
    history.record(original)
    edited, _ = apply_cue_sheet_edit(original, 1, {"intensity": 80})
    restored = history.undo(edited)
    assert history.redo(restored) == edited


def test_undo_on_an_empty_history_returns_none_rather_than_raising():
    assert TimelineDraftHistory().undo(_timeline()) is None


def test_a_new_edit_drops_the_redo_branch():
    history = TimelineDraftHistory()
    history.record(_timeline())
    history.undo(_timeline())
    assert history.can_redo is True
    history.record(_timeline())
    assert history.can_redo is False


def test_history_is_bounded_at_the_declared_limit():
    history = TimelineDraftHistory()
    for _ in range(DRAFT_HISTORY_LIMIT + 5):
        history.record(_timeline())
    assert history.depth == DRAFT_HISTORY_LIMIT


# -- 저장은 콘솔이 아니라 라이브러리로 간다 --------------------------------------


def test_save_writes_a_library_entry_and_does_not_touch_the_console(tmp_path):
    library = SongTimelineLibrary(tmp_path / "library.json")
    edited, _ = apply_cue_sheet_edit(_timeline(), 1, {"intensity": 80})
    entry = library.save("Sugar 초안", edited)
    assert entry["name"] == "Sugar 초안"
    assert library.get(entry["id"])["timeline"]["sections"][0]["d_level"] == 4
    # 저장은 파일 한 개다. 명령 문자열이 들어갈 자리가 없다.
    assert "commands" not in entry
    assert (tmp_path / "library.json").exists()


def test_undo_does_not_touch_saved_library_entries(tmp_path):
    library = SongTimelineLibrary(tmp_path / "library.json")
    original = _timeline()
    edited, _ = apply_cue_sheet_edit(original, 1, {"intensity": 80})
    saved = library.save("Sugar v1", edited)
    history = TimelineDraftHistory()
    history.record(edited)
    history.undo(edited)
    # 저장본은 되돌리기와 무관하다 — 초안만 물러난다.
    assert library.get(saved["id"])["timeline"]["sections"][0]["d_level"] == 4


# -- 오라우팅 방지: 큐 지시어가 필수 게이트다 -----------------------------------


def test_a_whole_song_brief_is_not_a_cue_sheet_edit():
    """실측 회귀(2026-09-06): 브리핑의 「어둡게」 하나가 이 라우트에 삼켜져
    곡 설계 인터뷰 32건이 깨졌다. 구간 지시어를 필수로 둬서 막는다."""
    brief = (
        "곡은 약 1분 40초의 밝은 팝 무대야.\n"
        "0:00 도입은 무대를 어둡게 두고 보컬에게만 시선을 모아줘.\n"
        "1:32 마지막 후렴은 따뜻하고 환하게, 가장 큰 에너지로 끝내줘."
    )
    assert parse_cue_sheet_edit_request(brief) is None


@pytest.mark.parametrize(
    "anchor",
    ["큐 3", "이 구간", "이 큐", "선택한 구간", "선택된 큐"],
)
def test_every_accepted_cue_anchor_opens_the_route(anchor):
    assert parse_cue_sheet_edit_request(f"{anchor} 더 밝게 해줘") is not None


def test_an_edit_verb_without_a_cue_anchor_falls_through():
    assert parse_cue_sheet_edit_request("전체적으로 더 밝게 해줘") is None
