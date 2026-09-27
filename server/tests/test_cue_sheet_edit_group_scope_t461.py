"""카드 t461 ① — 큐시트 편집 문장의 그룹 스코프(SPEC-LDDESIGN-001 REQ-087 전제).

문법(리드 승인 2026-09-27): 큐 지시어 + 그룹 목록(라틴 이름, · , + / 와 랑 으로 잇기)
+ (의/그룹) + 항목 + 값. 받는 그룹 = 그 큐의 ``intensity[].group``(대소문자 무시).
모르는 이름은 지어내지 않고 사유와 함께 거절한다. 그룹 토큰이 없는 문장은 기존
경로 그대로다(``.moai/reports/t461/parse_corpus_base.json`` 대조).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from server.design.cue_sheet_edit import (
    CueSheetEditError,
    apply_cue_sheet_edit,
    parse_cue_sheet_edit_request,
)


def _timeline() -> dict:
    return {
        "sections": [
            {
                "cue_number": 3,
                "label": "Chorus",
                "intensity": [{"group": "KEY", "level": 90}, {"group": "BACK", "level": 72}],
                "d_level": 5,
                "palette_primary": "블루",
                "fade_seconds": 1.5,
            },
            {"cue_number": 4, "label": "Verse", "d_level": 3, "fade_seconds": 1.5},
        ]
    }


def _levels(timeline: dict, cue: int = 3) -> dict[str, int]:
    section = next(s for s in timeline["sections"] if s["cue_number"] == cue)
    return {entry["group"]: entry["level"] for entry in section["intensity"]}


def _edit(text: str, *, cue_selected: bool = False) -> tuple[dict, list[str]]:
    request = parse_cue_sheet_edit_request(text, cue_selected=cue_selected)
    assert request is not None, text
    return apply_cue_sheet_edit(_timeline(), request["cue"] or 3, request["changes"])


# --- 받는 예 1~6 -------------------------------------------------------------


def test_1_one_group_absolute_leaves_the_other_group() -> None:
    request = parse_cue_sheet_edit_request("큐 3 BACK 밝기 70%로 바꿔줘")
    assert request == {"cue": 3, "changes": {"intensity": 70, "groups": ["BACK"]}}
    updated, report = _edit("큐 3 BACK 밝기 70%로 바꿔줘")
    assert _levels(updated) == {"KEY": 90, "BACK": 70}
    assert "BACK 72→70" in report[0]
    assert "KEY" not in report[0]


def test_2_all_groups_named_behaves_like_the_whole_cue() -> None:
    grouped, grouped_report = _edit("큐 3 KEY·BACK 밝기 95%로 바꿔줘")
    whole, whole_report = apply_cue_sheet_edit(_timeline(), 3, {"intensity": 95})
    assert grouped == whole
    assert grouped_report == whole_report


def test_3_one_group_relative() -> None:
    updated, report = _edit("큐 3 BACK 더 밝게 해줘")
    assert _levels(updated) == {"KEY": 90, "BACK": 92}
    assert "+20" in report[0]


def test_3b_relative_hits_the_ceiling_with_the_existing_refusal_shape() -> None:
    with pytest.raises(CueSheetEditError, match="천장 100"):
        apply_cue_sheet_edit(
            {
                "sections": [
                    {
                        "cue_number": 3,
                        "intensity": [
                            {"group": "KEY", "level": 90},
                            {"group": "BACK", "level": 100},
                        ],
                    }
                ]
            },
            3,
            {"intensity_delta": 20, "groups": ["BACK"]},
        )


def test_4_back_colour_goes_to_the_secondary_slot() -> None:
    updated, report = _edit("큐 3 BACK 컬러 앰버로 바꿔줘")
    section = updated["sections"][0]
    assert section["palette_secondary"] == "앰버"
    assert section["palette_primary"] == "블루"


def test_5_key_colour_is_the_primary_slot() -> None:
    grouped, _ = _edit("큐 3 KEY 컬러 레드로 바꿔줘")
    whole, _ = apply_cue_sheet_edit(_timeline(), 3, {"palette_primary": "레드"})
    assert grouped == whole


def test_6_anchorless_with_selected_cue() -> None:
    request = parse_cue_sheet_edit_request("BACK 밝기 50%로 해줘", cue_selected=True)
    assert request == {"cue": None, "changes": {"intensity": 50, "groups": ["BACK"]}}


def test_group_list_separators_and_case() -> None:
    for text in ("큐 3 key, back 밝기 60%로 바꿔줘", "큐 3 KEY와 BACK 밝기 60%로 바꿔줘"):
        request = parse_cue_sheet_edit_request(text)
        assert request is not None and [g.upper() for g in request["changes"]["groups"]] == [
            "KEY",
            "BACK",
        ], text


# --- 거절 예 a~d -------------------------------------------------------------


def test_a_unknown_group_is_refused_with_the_known_names() -> None:
    with pytest.raises(CueSheetEditError) as caught:
        _edit("큐 3 FOH 밝기 95%로 바꿔줘")
    message = str(caught.value)
    assert "'FOH'" in message and "KEY, BACK" in message and "지어내지 않습니다" in message


def test_b_colour_for_several_groups_is_refused() -> None:
    with pytest.raises(CueSheetEditError, match="그룹 하나에만"):
        _edit("큐 3 KEY·BACK 컬러 앰버로 바꿔줘")


def test_c_cue_wide_fields_refuse_a_group() -> None:
    for text in ("큐 3 BACK 페이드 2초로 바꿔줘", "큐 3 BACK 무브먼트 스윕으로 바꿔줘"):
        with pytest.raises(CueSheetEditError, match="큐 전체 값"):
            _edit(text)


def test_d_cue_without_group_levels_refuses_a_group() -> None:
    request = parse_cue_sheet_edit_request("큐 4 BACK 밝기 50%로 바꿔줘")
    assert request is not None
    with pytest.raises(CueSheetEditError, match="그룹별 조도가 없습니다"):
        apply_cue_sheet_edit(_timeline(), 4, request["changes"])


def test_refusal_writes_nothing() -> None:
    timeline = _timeline()
    before = json.dumps(timeline, sort_keys=True)
    with pytest.raises(CueSheetEditError):
        apply_cue_sheet_edit(timeline, 3, {"intensity": 50, "groups": ["FOH"]})
    assert json.dumps(timeline, sort_keys=True) == before


# --- 기존 문장 바이트 동일 ------------------------------------------------------


def test_existing_sentences_parse_exactly_as_before() -> None:
    """수정 전(6f89e9eb)에 떠 둔 스냅샷 — server/tests 의 한국어 문자열 전부."""
    base = json.loads(Path(".moai/reports/t461/parse_corpus_base.json").read_text("utf-8"))
    changed = [
        text
        for text, (plain, selected) in base.items()
        if [
            parse_cue_sheet_edit_request(text, cue_selected=False),
            parse_cue_sheet_edit_request(text, cue_selected=True),
        ]
        != [plain, selected]
    ]
    assert changed == []
    assert len(base) > 1000
