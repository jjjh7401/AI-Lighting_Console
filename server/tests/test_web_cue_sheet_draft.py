"""t281 — 세션 층에서 본 큐시트 초안 편집.

이 파일의 중심 단언은 하나다: **편집·되돌리기·저장 어느 경로에서도 콘솔에
명령이 한 줄도 나가지 않는다.** `FakeConsole.executed` 는 콘솔로 나간 문자열을
그대로 쌓으므로, 그 목록이 비었다는 것이 「콘솔 무접촉」의 실측 증거다
(「안 나갔을 것이다」가 아니라 「센 결과 0건」).

두 번째 축은 선택 전달이다 — 화면이 고른 큐가 요청에 실려 오면, 문장에 번호가
없어도 그 큐가 고쳐진다.
"""

from __future__ import annotations

import pytest

from server.safety.approval import ApprovalRequest
from server.safety.audit import AuditLog
from server.safety.gate import SafetyGate
from server.web.approval_bridge import ApprovalChannel
from server.web.messages import ProtocolError, parse_client_message
from server.web.session import ChatSession, SongTimelineStore
from server.web.timeline_library import SongTimelineLibrary

from .test_safety_gate import FakeConsole


class RefusingProvider:
    """모델을 부르면 시험이 깨진다 — 이 경로는 제공자 없이 동작해야 한다."""

    def complete(self, *args, **kwargs):  # pragma: no cover - 불려선 안 된다
        raise AssertionError("이 경로는 모델을 부르지 않는다")


def _timeline() -> dict:
    return {
        "song_title": "Sugar",
        "sequence_number": 210,
        "lifecycle": "planned",
        "approval": "approved",
        "director_decisions": [],
        "lint": [],
        "unresolved": [],
        "disabled": [],
        "readback": {"verified": None, "message": None},
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
                "intensity": [{"group": "MOVER-U", "level": 40}],
                "trans": "FADE",
                "fade_seconds": 2.0,
            }
        ],
    }


@pytest.fixture
def harness(tmp_path):
    console = FakeConsole()
    audit = AuditLog(tmp_path / "audit")
    channel = ApprovalChannel(timeout_seconds=1.0)
    gate = SafetyGate(console=console, audit=audit, approval_port=channel)
    store = SongTimelineStore()
    store.latest = _timeline()
    sent: list[dict] = []
    session = ChatSession(
        gate=gate,
        provider=RefusingProvider(),
        system_prefix="PREFIX",
        audit=audit,
        send_event=sent.append,
        approval_channel=channel,
        timeline_store=store,
        timeline_library=SongTimelineLibrary(tmp_path / "library.json"),
    )
    return session, console, store, sent


def _timelines(sent: list[dict]) -> list[dict]:
    return [event["timeline"] for event in sent if event.get("type") == "song_timeline"]


# -- 성공 경로 ------------------------------------------------------------------


def test_selection_carries_the_cue_when_the_sentence_omits_the_number(harness):
    session, console, store, sent = harness
    session.run_instruction("이 구간 더 밝게 해줘", 1)
    assert store.latest["sections"][0]["intensity"] == [{"group": "MOVER-U", "level": 60}]
    assert console.executed == []


def test_the_reply_reports_the_change_field_by_field(harness):
    session, _console, _store, sent = harness
    event = session.run_instruction("이 구간 더 밝게 해줘", 1)
    assert "조도 40 → 60" in event["text"]
    assert "초안" in event["text"]


def test_the_pushed_timeline_carries_a_draft_badge(harness):
    session, _console, store, sent = harness
    session.run_instruction("이 구간 더 밝게 해줘", 1)
    pushed = _timelines(sent)
    assert pushed and pushed[-1]["draft"] == {
        "dirty": True,
        "depth": 1,
        "last_change": ["조도 40 → 60"],
    }
    assert store.latest["draft"]["dirty"] is True


# -- 거절 경로 ------------------------------------------------------------------


def test_no_selection_and_no_number_is_refused_with_an_honest_reason(harness):
    """「이 구간」이라 말했는데 선택이 없다 — 어느 큐인지 **지어내지 않는다**."""
    session, console, store, _sent = harness
    event = session.run_instruction("이 구간 더 밝게 해줘")
    assert "어느 큐를 고칠지 알 수 없습니다" in event["text"]
    assert "콘솔에는 아무것도 쓰지 않았습니다" in event["text"]
    # 무응답(silent no-op)이 아니다 — 초안은 그대로다.
    assert store.latest["sections"][0]["intensity"] == [{"group": "MOVER-U", "level": 40}]
    assert console.executed == []


def test_an_out_of_range_level_is_refused_with_the_requested_value(harness):
    session, console, store, _sent = harness
    event = session.run_instruction("큐 1 조도 120으로 바꿔줘", 1)
    assert "조도는 0~100 사이여야 합니다 (요청값: 120)." in event["text"]
    assert store.latest["sections"][0]["intensity"] == [{"group": "MOVER-U", "level": 40}]
    assert console.executed == []


def test_an_unknown_cue_is_refused_and_names_the_cues_that_exist(harness):
    session, console, _store, _sent = harness
    event = session.run_instruction("큐 9 조도 80으로 바꿔줘")
    assert "큐 9가 이 큐시트에 없습니다. (보유 큐: 1)" in event["text"]
    assert console.executed == []


# -- 되돌리기 / 다시하기 ---------------------------------------------------------


def test_undo_restores_the_previous_draft_exactly(harness):
    session, console, store, _sent = harness
    before = dict(store.latest)
    session.run_instruction("이 구간 더 밝게 해줘", 1)
    session.undo_timeline_draft()
    assert store.latest["sections"] == before["sections"]
    assert store.latest["draft"]["dirty"] is False
    assert console.executed == []


def test_redo_reapplies_the_undone_edit(harness):
    session, console, store, _sent = harness
    session.run_instruction("이 구간 더 밝게 해줘", 1)
    edited = store.latest["sections"][0]["intensity"]
    session.undo_timeline_draft()
    session.redo_timeline_draft()
    assert store.latest["sections"][0]["intensity"] == edited
    assert console.executed == []


def test_undo_with_nothing_to_undo_says_so_instead_of_failing(harness):
    session, console, _store, _sent = harness
    event = session.undo_timeline_draft()
    assert "되돌리기할 초안 단계가 없습니다" in event["text"]
    assert console.executed == []


def test_undo_does_not_touch_saved_library_entries(harness, tmp_path):
    session, console, store, _sent = harness
    library = SongTimelineLibrary(tmp_path / "saved.json")
    session.run_instruction("이 구간 더 밝게 해줘", 1)
    saved = library.save("Sugar v1", store.latest)
    session.undo_timeline_draft()
    assert library.get(saved["id"])["timeline"]["sections"][0]["intensity"] == [
        {"group": "MOVER-U", "level": 60}
    ]
    assert console.executed == []


# -- 콘솔 무접촉을 통째로 다시 잰다 ---------------------------------------------


def test_the_whole_edit_undo_save_round_trip_emits_zero_console_commands(harness, tmp_path):
    session, console, store, _sent = harness
    library = SongTimelineLibrary(tmp_path / "roundtrip.json")
    session.run_instruction("이 구간 더 밝게 해줘", 1)
    session.run_instruction("큐 1 페이드 0.5초로 바꿔줘")
    library.save("Sugar 초안", store.latest)
    session.undo_timeline_draft()
    session.redo_timeline_draft()
    library.save("Sugar 초안 2", store.latest)
    assert console.executed == []


def test_no_approval_card_is_raised_by_any_draft_path(harness):
    """콘솔 쓰기 게이트는 승인 카드를 띄운다 — 카드가 0장이면 게이트도 안 지났다."""
    session, _console, _store, sent = harness
    session.run_instruction("이 구간 더 밝게 해줘", 1)
    session.undo_timeline_draft()
    assert [event for event in sent if event.get("type") == "approval_request"] == []
    assert not isinstance(sent[-1], ApprovalRequest)


# -- 프레임 규약 ----------------------------------------------------------------


def test_chat_frame_carries_an_optional_selected_cue():
    parsed = parse_client_message('{"v":1,"type":"chat","text":"더 밝게","selected_cue":3}')
    assert parsed["selected_cue"] == 3
    legacy = parse_client_message('{"v":1,"type":"chat","text":"더 밝게"}')
    assert legacy["selected_cue"] is None


def test_a_boolean_selected_cue_is_refused_rather_than_read_as_cue_one():
    with pytest.raises(ProtocolError):
        parse_client_message('{"v":1,"type":"chat","text":"x","selected_cue":true}')


def test_draft_undo_and_redo_frames_survive_the_parser_as_themselves():
    """마지막 폴백이 이들을 ``status_request`` 로 바꿔치지 않는다."""
    for kind in ("timeline_draft_undo", "timeline_draft_redo"):
        assert parse_client_message(f'{{"v":1,"type":"{kind}"}}')["type"] == kind
