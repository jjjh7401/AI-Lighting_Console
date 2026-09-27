"""카드 t466 — 큐시트 편집 파서 어휘 확장: 트래킹·MIB·페이저·포지션 프리셋.

**고치기 전에 실측한 것** (트리 ``WT-parser-vocab`` @ 1a2ecf50): 아래 네 종류 문장은
``parse_cue_sheet_edit_request`` 가 ``None`` 을 돌려 편집 라우트를 안 탔다 — 그래서
lane-3 의 수정요청 생성기(t460)는 이 네 조작을 버튼으로 만들지 못했다(t460 계획 F3·D2).

값 어휘는 SPEC 이 닫아 둔 것을 쓴다 — 트래킹은 REQ-LDDESIGN-053 의 4모드
(``server/concept/cue_model.py`` ``TRACKING_MODES``), MIB 는 REQ-082 의 표시 3종 + 없음.
닫힌 어휘 밖의 값은 짐작하지 않고 사유를 붙여 거절한다(쓰기 전에, 부분 적용 없음).

이 네 칸은 **초안에만** 남는다 — 콘솔 명령 형태가 실측된 적이 없어
``cue_sheet_apply.UNSOURCED_FIELD_REASONS`` 가 칸마다 사유를 달고 건너뛴다.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from server.design.cue_sheet_apply import UNSOURCED_FIELD_REASONS, plan_console_apply
from server.design.cue_sheet_edit import (
    CueSheetEditError,
    apply_cue_sheet_edit,
    parse_cue_sheet_edit_request,
)
from server.tests.test_cue_sheet_apply import _legend_timeline


def _changes(text: str, **kwargs):
    parsed = parse_cue_sheet_edit_request(text, **kwargs)
    assert parsed is not None, f"파서가 못 읽었다: {text!r}"
    return parsed["changes"]


# --- 읽기 ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("큐 3 트래킹 Block으로 바꿔줘", "Block"),
        ("큐 3 트래킹을 Cue Only로 설정", "Cue Only"),
        ("큐 3 트래킹 Release로 바꿔줘", "Release"),
        ("큐 3 트래킹 Track으로 바꿔줘", "Track"),
        ("큐 3 트래킹 블록으로 바꿔줘", "Block"),
        ("큐 3 트래킹 큐온리로 바꿔줘", "Cue Only"),
        ("큐 3 트래킹 릴리즈로 바꿔줘", "Release"),
        ("큐 3 트래킹 트랙으로 바꿔줘", "Track"),
    ],
)
def test_tracking_sentences_are_read_into_the_closed_vocabulary(text, expected):
    assert _changes(text) == {"tracking": expected}


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("큐 3 MIB dark로 설정", "dark"),
        ("큐 3 MIB mark로 바꿔줘", "mark"),
        ("큐 3 MIB live로 바꿔줘", "live"),
        ("큐 3 MIB 없음으로 바꿔줘", "none"),
        ("큐 3 MIB 다크로 바꿔줘", "dark"),
        ("큐 3 MIB 라이브로 바꿔줘", "live"),
    ],
)
def test_mib_sentences_are_read_into_the_closed_vocabulary(text, expected):
    assert _changes(text) == {"mib_mode": expected}


def test_phaser_sentence_carries_the_preset_name():
    assert _changes("큐 3 페이저 Ph 2 step으로 바꿔줘") == {"phaser": "Ph 2 step"}


def test_position_sentence_splits_number_and_name():
    assert _changes("큐 3 포지션 2.11 Sweep L로 바꿔줘") == {
        "position": "Sweep L",
        "position_preset_no": "2.11",
    }


def test_position_sentence_by_name_only():
    assert _changes("큐 3 포지션 Center로 바꿔줘") == {"position": "Center"}


def test_the_selected_cue_path_reads_the_new_vocabulary_without_an_anchor():
    assert _changes("트래킹 Block으로 바꿔줘", cue_selected=True) == {"tracking": "Block"}


def test_an_unknown_tracking_value_is_passed_through_raw_for_apply_to_reject():
    # 짐작하지 않는다 — 파서는 원문 그대로 넘기고, 거절 사유는 apply 가 붙인다.
    assert _changes("큐 3 트래킹 Blok으로 바꿔줘") == {"tracking": "Blok"}


# --- 적용 ---------------------------------------------------------------------


def _timeline():
    return {
        "sections": [
            {"cue_number": 3, "label": "Chorus 1", "d_level": 5, "position": "Home", "mib": False},
        ]
    }


@pytest.mark.parametrize(
    ("changes", "field", "value", "report_head"),
    [
        ({"tracking": "Block"}, "tracking", "Block", "트래킹 Track → Block"),
        ({"mib_mode": "dark"}, "mib_mode", "dark", "MIB 없음 → dark"),
        ({"phaser": "Ph 2 step"}, "phaser", "Ph 2 step", "페이저 — → Ph 2 step"),
    ],
)
def test_apply_writes_the_new_field_and_reports_it(changes, field, value, report_head):
    updated, report = apply_cue_sheet_edit(_timeline(), 3, changes)
    assert updated["sections"][0][field] == value
    assert report == [report_head]


def test_apply_keeps_the_computed_mib_flag_untouched():
    updated, _report = apply_cue_sheet_edit(_timeline(), 3, {"mib_mode": "live"})
    assert updated["sections"][0]["mib"] is False


def test_apply_writes_position_name_and_number():
    updated, report = apply_cue_sheet_edit(
        _timeline(), 3, {"position": "Sweep L", "position_preset_no": "2.11"}
    )
    section = updated["sections"][0]
    assert (section["position"], section["position_preset_no"]) == ("Sweep L", "2.11")
    assert report == ["포지션 Home → 2.11 Sweep L"]


@pytest.mark.parametrize(
    ("changes", "reason_fragment"),
    [
        ({"tracking": "Blok"}, "트래킹 값은 Track, Block, Cue Only, Release 중 하나"),
        ({"mib_mode": "darkish"}, "MIB 값은 없음, dark, mark, live 중 하나"),
        ({"position": "2.11"}, "번호만으로는 포지션 이름을 알 수 없습니다"),
        ({"position": "Sweep L", "position_preset_no": "4.2"}, "포지션 프리셋은 풀 2"),
        ({"phaser": "  "}, "페이저 값이 비어 있습니다"),
    ],
)
def test_apply_rejects_out_of_vocabulary_values_before_writing(changes, reason_fragment):
    timeline = _timeline()
    before = json.dumps(timeline, sort_keys=True)
    with pytest.raises(CueSheetEditError, match=reason_fragment):
        apply_cue_sheet_edit(timeline, 3, changes)
    assert json.dumps(timeline, sort_keys=True) == before


def test_new_fields_are_cue_wide_and_refuse_a_group_scope():
    timeline = {
        "sections": [
            {
                "cue_number": 3,
                "intensity": [{"group": "KEY", "level": 80}, {"group": "BACK", "level": 60}],
            }
        ]
    }
    with pytest.raises(CueSheetEditError, match="큐 전체 값입니다"):
        apply_cue_sheet_edit(timeline, 3, {"tracking": "Block", "groups": ["KEY"]})


# --- 콘솔 반영: 초안에만 남고 사유가 붙는다 ----------------------------------


@pytest.mark.parametrize("field", ["tracking", "mib_mode", "phaser", "position"])
def test_the_new_fields_are_skipped_on_the_console_with_their_own_reason(field):
    baseline = _legend_timeline()
    current = copy.deepcopy(baseline)
    current["sections"][1][field] = "무엇이든"
    plan = plan_console_apply(baseline, current)
    assert plan.commands == ()
    (skip,) = plan.skipped
    assert UNSOURCED_FIELD_REASONS[field] in skip.detail


# --- 기존 문장 바이트 동일 ----------------------------------------------------


def test_existing_sentences_parse_exactly_as_before():
    """수정 전(1a2ecf50)에 떠 둔 스냅샷 — server/tests 의 한국어 문자열 전부."""
    base = json.loads(Path(".moai/reports/t466/parse_corpus_base.json").read_text("utf-8"))
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
    assert len(base) > 6000


# --- 세션 경로 끝까지: 앞선 콘솔 라우트에 삼켜지지 않는다 ------------------------
#
# 이 파서 앞에는 콘솔로 쓰는 라우트가 줄지어 있다(페이저 recall·포지션 프리셋 등,
# `session.py` 라우트 사슬). 「페이저」「포지션」 문장이 그쪽에 먼저 걸리면 초안이
# 아니라 **콘솔**이 움직인다 — 그래서 실제 세션으로 끝까지 태워 콘솔 명령 0건을 센다.


@pytest.mark.parametrize(
    ("text", "field", "value"),
    [
        ("큐 1 트래킹 Block으로 바꿔줘", "tracking", "Block"),
        ("큐 1 MIB dark로 설정", "mib_mode", "dark"),
        ("큐 1 페이저 Ph 2 step으로 바꿔줘", "phaser", "Ph 2 step"),
        # 페이저 recall 라우트는 카탈로그 30종 라벨이 필수 게이트다 — 진짜 라벨을
        # 실어도 발사 동사(쳐줘·쏴·걸어…)가 없으면 그쪽이 비켜서야 한다.
        ("큐 1 페이저 Breathe Soft로 바꿔줘", "phaser", "Breathe Soft"),
        ("큐 1 포지션 2.11 Sweep L로 바꿔줘", "position", "Sweep L"),
    ],
)
def test_the_session_routes_the_new_sentences_to_the_draft_without_touching_the_console(
    draft_harness, text, field, value
):
    session, console, store, _sent = draft_harness
    event = session.run_instruction(text, None)
    assert store.latest["sections"][0][field] == value
    assert "초안 수정 (콘솔 무접촉)" in event["text"]
    assert console.executed == []


@pytest.fixture
def draft_harness(tmp_path):
    from server.safety.audit import AuditLog
    from server.safety.gate import SafetyGate
    from server.web.approval_bridge import ApprovalChannel
    from server.web.session import ChatSession, SongTimelineStore
    from server.web.timeline_library import SongTimelineLibrary

    from .test_safety_gate import FakeConsole
    from .test_web_cue_sheet_draft import RefusingProvider
    from .test_web_cue_sheet_draft import _timeline as _session_timeline

    console = FakeConsole()
    audit = AuditLog(tmp_path / "audit")
    channel = ApprovalChannel(timeout_seconds=1.0)
    store = SongTimelineStore()
    store.latest = _session_timeline()
    sent: list[dict] = []
    session = ChatSession(
        gate=SafetyGate(console=console, audit=audit, approval_port=channel),
        provider=RefusingProvider(),
        system_prefix="PREFIX",
        audit=audit,
        send_event=sent.append,
        approval_channel=channel,
        timeline_store=store,
        timeline_library=SongTimelineLibrary(tmp_path / "library.json"),
    )
    return session, console, store, sent
