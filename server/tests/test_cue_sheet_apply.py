"""t291 — 초안을 콘솔로 보내는 **계획**: 범위·주소·정직한 부분 성공.

이 파일이 재는 것은 계획뿐이다(순수 함수라 콘솔이 없다). 계획이 실제로 어느
경로로 나가는지 — 미리보기·승인·LiveLock — 는 세션 층 시험
(`test_web_cue_sheet_draft.py`)이 잰다.

가장 무거운 단언 둘: **건드리지 않은 큐는 계획에 나타나지 않는다**, 그리고
**보내지 못한 큐는 사유 문자열과 함께 보고된다**(「전부 반영」을 말하지 않는다).
"""

from __future__ import annotations

import copy

import pytest

from server.design.cue_sheet_apply import (
    ROLE_UNADDRESSED,
    UNMAPPED_LOOK,
    UNSOURCED_FIELD_REASONS,
    ConsoleApplyError,
    changed_cue_numbers,
    plan_console_apply,
)


def _timeline() -> dict:
    return {
        "song_title": "Sugar",
        "sequence_number": 210,
        "layer_mapping": [
            {"role": "key", "group_no": 11, "group_name": "KEY"},
            {"role": "back", "group_no": 12, "group_name": "BACK"},
        ],
        "sections": [
            {
                "index": 1,
                "label": "INTRO",
                "cue_number": 10,
                "start_ms": 0,
                "d_level": 3,
                "intensity": [{"group": "KEY", "level": 55}],
                "fixture_groups": ["KEY"],
                "mood": "화사",
            },
            {
                "index": 2,
                "label": "VERSE1",
                "cue_number": 20,
                "start_ms": 8_000,
                "d_level": 4,
                "intensity": [{"group": "KEY", "level": 70}, {"group": "BACK", "level": 35}],
                "fixture_groups": ["KEY", "BACK"],
                "mood": "경쾌",
            },
        ],
    }


def _brighten(timeline: dict, cue: int, level: int) -> dict:
    updated = copy.deepcopy(timeline)
    for section in updated["sections"]:
        if section["cue_number"] == cue:
            section["intensity"] = [{**entry, "level": level} for entry in section["intensity"]]
            section["d_level"] = max(1, min(5, round(level / 20)))
    return updated


# -- 범위: 바뀐 큐만 -------------------------------------------------------------


def test_only_the_changed_cue_is_planned():
    baseline = _timeline()
    current = _brighten(baseline, 20, 90)
    plan = plan_console_apply(baseline, current)
    assert plan.applied == (20,)
    assert "Store Sequence 210 Cue 20 /Merge" in plan.commands


def test_an_untouched_cue_is_not_named_anywhere_in_the_plan():
    """건드리지 않은 큐 10 은 명령에도, 건너뜀 목록에도 없다 — 콘솔에서 그대로다."""
    baseline = _timeline()
    plan = plan_console_apply(baseline, _brighten(baseline, 20, 90))
    assert all("Cue 10" not in command for command in plan.commands)
    assert [skip.cue_number for skip in plan.skipped] == []


def test_the_merge_form_is_used_so_the_cues_other_columns_survive():
    baseline = _timeline()
    plan = plan_console_apply(baseline, _brighten(baseline, 20, 90))
    stores = [c for c in plan.commands if c.startswith("Store ")]
    assert stores == ["Store Sequence 210 Cue 20 /Merge"]


def test_a_value_reverted_by_undo_is_not_sent():
    """되돌리기로 원래 값이 된 큐는 「바뀐 큐」가 아니다 — 값으로 비교하므로."""
    baseline = _timeline()
    there_and_back = _brighten(_brighten(baseline, 10, 75), 10, 55)
    assert changed_cue_numbers(baseline, there_and_back) == ()
    with pytest.raises(ConsoleApplyError, match="달라진 큐가 없습니다"):
        plan_console_apply(baseline, there_and_back)


def test_the_group_selection_addresses_only_that_cues_groups():
    baseline = _timeline()
    plan = plan_console_apply(baseline, _brighten(baseline, 20, 90))
    assert "Group 11 + 12 ; Attribute 'Dimmer' At 90" in plan.commands


# -- 정직한 부분 성공 -----------------------------------------------------------


def test_a_group_with_no_console_number_is_skipped_as_role_unaddressed():
    baseline = _timeline()
    current = _brighten(baseline, 20, 90)
    current["sections"][1]["fixture_groups"] = ["MOVER-U"]
    plan = plan_console_apply(baseline, current)
    assert plan.commands == ()
    (skip,) = plan.skipped
    assert skip.cue_number == 20
    assert skip.reason == ROLE_UNADDRESSED
    assert "MOVER-U" in skip.detail


def test_a_partially_addressed_cue_reports_both_what_went_and_what_did_not():
    baseline = _timeline()
    current = _brighten(baseline, 20, 90)
    current["sections"][1]["fixture_groups"] = ["KEY", "MOVER-U"]
    plan = plan_console_apply(baseline, current)
    assert plan.applied == (20,)
    assert "Group 11 ; Attribute 'Dimmer' At 90" in plan.commands
    (skip,) = plan.skipped
    assert skip.reason == ROLE_UNADDRESSED
    assert "MOVER-U" in skip.detail


def test_a_section_without_fixture_groups_falls_back_to_its_intensity_groups():
    """실측 사다리 ②: 설계 인터뷰가 만든 판에는 Fixture Group 칸이 없다."""
    baseline = _timeline()
    del baseline["sections"][1]["fixture_groups"]
    current = _brighten(baseline, 20, 90)
    plan = plan_console_apply(baseline, current)
    assert "Group 11 + 12 ; Attribute 'Dimmer' At 90" in plan.commands


def test_a_section_with_neither_names_addresses_every_recorded_group():
    """사다리 ③: 이름이 아예 없으면 감독이 기록한 그룹 전부다(리그 전체가 아니라)."""
    baseline = _timeline()
    section = baseline["sections"][1]
    del section["fixture_groups"]
    del section["intensity"]
    current = copy.deepcopy(baseline)
    current["sections"][1]["d_level"] = 5
    plan = plan_console_apply(baseline, current)
    assert "Group 11 + 12 ; Attribute 'Dimmer' At 100" in plan.commands


def test_with_no_address_book_at_all_the_cue_is_reported_not_guessed():
    baseline = _timeline()
    baseline["layer_mapping"] = []
    current = _brighten(baseline, 20, 90)
    plan = plan_console_apply(baseline, current)
    assert plan.commands == ()
    (skip,) = plan.skipped
    assert skip.reason == ROLE_UNADDRESSED


def test_a_change_with_no_console_value_form_is_skipped_as_unmapped_look():
    """무드만 고친 큐는 콘솔로 보낼 값이 없다 — 조용히 버리지 않고 보고한다."""
    baseline = _timeline()
    current = copy.deepcopy(baseline)
    current["sections"][1]["mood"] = "격렬"
    plan = plan_console_apply(baseline, current)
    assert plan.commands == ()
    (skip,) = plan.skipped
    assert skip.cue_number == 20
    assert skip.reason == UNMAPPED_LOOK
    # 사유는 「지원 안 함」이 아니라 **그 칸이 왜 안 나가는지**다(t293).
    assert skip.detail == UNSOURCED_FIELD_REASONS["mood"] + ". 초안과 저장본에는 남아 있습니다."


# -- t293: 조도 말고도 나가는 칸 ---------------------------------------------------


def _legend_timeline() -> dict:
    timeline = _timeline()
    timeline["palette_legend"] = [
        {"id": "P1", "name": "골드 앰버", "color": "#FFB43C"},
        {"id": "P4", "name": "핫 핑크", "color": "#FF3C9E"},
    ]
    timeline["sections"][1]["palette_primary"] = "P1 골드앰버"
    timeline["sections"][1]["fade_seconds"] = 2.0
    return timeline


def test_a_colour_edit_emits_the_sourced_colorrgb_line():
    """컬러는 팔레트 범례의 색을 백분율 ColorRGB 세 축으로 싣는다."""
    baseline = _legend_timeline()
    current = copy.deepcopy(baseline)
    current["sections"][1]["palette_primary"] = "P4 핫핑크"
    plan = plan_console_apply(baseline, current)
    assert plan.applied == (20,)
    # #FF3C9E → 255,60,158 → 100,24,62 (백분율 축은 룩 라이브러리와 같다).
    assert (
        "Group 11 + 12 ; Attribute 'Dimmer' At 70 ; Attribute 'ColorRGB_R' At 100 ; "
        "Attribute 'ColorRGB_G' At 24 ; Attribute 'ColorRGB_B' At 62" in plan.commands
    )
    assert plan.summaries[20] == "조도 70% · 컬러 P4 핫핑크"


def test_a_colour_name_absent_from_the_legend_is_skipped_not_guessed():
    baseline = _legend_timeline()
    current = copy.deepcopy(baseline)
    current["sections"][1]["palette_primary"] = "P9 없는색"
    plan = plan_console_apply(baseline, current)
    (skip,) = plan.skipped
    assert skip.reason == UNMAPPED_LOOK
    assert "팔레트 범례에 없는 이름입니다" in skip.detail
    # 컬러는 못 갔지만 큐 자체는 나간다 — 조도는 실을 값이 있다.
    assert plan.applied == (20,)
    assert not any("ColorRGB" in command for command in plan.commands)


# -- t408: 범례가 없어도 표준 팔레트 이름은 값을 낸다 -----------------------------


def test_a_bare_color_name_with_no_legend_at_all_still_emits_colorrgb():
    """실제 곡 분석 경로는 palette_legend 를 아예 안 싣는다(t408 실측) — 그래도
    표준 무대 팔레트 10색(spec.md §A.2)에 있는 순정 이름이면 값이 나가야 한다."""
    baseline = _timeline()
    assert "palette_legend" not in baseline
    current = copy.deepcopy(baseline)
    current["sections"][1]["palette_primary"] = "warm white"
    plan = plan_console_apply(baseline, current)
    assert plan.applied == (20,)
    # Warm White (100,75,40) — spec.md §A.2 표준 팔레트, 지어낸 값이 아니다.
    assert (
        "Group 11 + 12 ; Attribute 'Dimmer' At 70 ; Attribute 'ColorRGB_R' At 100 ; "
        "Attribute 'ColorRGB_G' At 75 ; Attribute 'ColorRGB_B' At 40" in plan.commands
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("cold blue", (5, 20, 100)),  # 수식어를 벗기면 blue — hue 는 그대로.
        ("deep blue", (5, 20, 100)),
        ("블루", (5, 20, 100)),  # 한국어 원색 표기 → blue.
        ("warm white", (100, 75, 40)),
    ],
)
def test_the_real_songs_measured_palette_values_all_resolve(value, expected):
    """카드 t408 이 실측한 실제 곡의 네 값 — 고치기 전엔 전부 None 이었다."""
    baseline = _timeline()
    current = copy.deepcopy(baseline)
    current["sections"][1]["palette_primary"] = value
    plan = plan_console_apply(baseline, current)
    assert not plan.skipped or all(skip.reason != UNMAPPED_LOOK for skip in plan.skipped)
    r, g, b = expected
    assert (
        f"Attribute 'ColorRGB_R' At {r:g} ; Attribute 'ColorRGB_G' At {g:g} ; "
        f"Attribute 'ColorRGB_B' At {b:g}" in " ".join(plan.commands)
    )


def test_a_color_outside_the_standard_ten_still_fails_loudly_not_guessed():
    """ "gold"·"warm special" 은 표준 팔레트 10색에 없다 — 지어내지 않고 skip."""
    baseline = _timeline()
    current = copy.deepcopy(baseline)
    current["sections"][1]["palette_primary"] = "warm special"
    plan = plan_console_apply(baseline, current)
    assert not any("ColorRGB" in command for command in plan.commands)
    (skip,) = plan.skipped
    assert skip.reason == UNMAPPED_LOOK
    assert "팔레트 범례에 없는 이름입니다" in skip.detail


def test_a_fade_edit_rides_the_store_line_as_cuefade():
    baseline = _legend_timeline()
    current = copy.deepcopy(baseline)
    current["sections"][1]["fade_seconds"] = 3.5
    plan = plan_console_apply(baseline, current)
    assert "Store Sequence 210 Cue 20 CueFade 3.5 /Merge" in plan.commands
    assert plan.summaries[20] == "조도 70% · 페이드 3.5초"


def test_an_unchanged_fade_does_not_reappear_on_the_store_line():
    """조도만 고친 큐의 Store 줄은 t291 그대로다 — 안 바뀐 페이드를 다시 쓰지 않는다."""
    baseline = _legend_timeline()
    plan = plan_console_apply(baseline, _brighten(baseline, 20, 90))
    assert "Store Sequence 210 Cue 20 /Merge" in plan.commands


@pytest.mark.parametrize("field", ["movement", "effect", "trans", "note", "palette_secondary"])
def test_an_unsourced_column_is_reported_with_its_own_reason(field):
    """출처 없는 칸은 칸마다 다른 사유로 건너뛴다 — 한 문장으로 뭉뚱그리지 않는다."""
    baseline = _legend_timeline()
    current = copy.deepcopy(baseline)
    current["sections"][1][field] = "무엇이든"
    plan = plan_console_apply(baseline, current)
    assert plan.commands == ()
    (skip,) = plan.skipped
    assert skip.reason == UNMAPPED_LOOK
    assert UNSOURCED_FIELD_REASONS[field] in skip.detail


def test_an_unsourced_column_alongside_a_sourced_one_is_still_reported():
    """조도와 이펙트를 같이 고치면 조도는 나가고 이펙트는 사유와 함께 남는다."""
    baseline = _legend_timeline()
    current = _brighten(baseline, 20, 90)
    current["sections"][1]["effect"] = "스트로브"
    plan = plan_console_apply(baseline, current)
    assert plan.applied == (20,)
    (skip,) = plan.skipped
    assert UNSOURCED_FIELD_REASONS["effect"] in skip.detail


# -- 계획 자체가 불가능한 자리 ---------------------------------------------------


def test_a_timeline_without_a_console_sequence_number_refuses_by_name():
    baseline = _timeline()
    current = _brighten(baseline, 20, 90)
    current["sequence_number"] = 0
    with pytest.raises(ConsoleApplyError, match="콘솔 시퀀스 번호가 없습니다"):
        plan_console_apply(baseline, current)


def test_the_plan_carries_the_sequence_number_the_operator_will_read():
    """시퀀스 슬롯이 그 사이 바뀌었을 위험의 방어는 승인 카드다 — 번호를 싣는다."""
    baseline = _timeline()
    plan = plan_console_apply(baseline, _brighten(baseline, 20, 90))
    assert plan.sequence_number == 210
