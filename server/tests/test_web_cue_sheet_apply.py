"""t291 — 초안 콘솔 반영: 기존 게이트 경로 그대로, 정직한 부분 성공.

세 단언이 이 파일의 중심이다:

1. **저장은 콘솔에 한 건도 보내지 않는다** — 반영이 생겼다고 저장이 새는 일이
   없어야 한다(핀).
2. **반영은 미리보기 카드를 먼저 띄운다** — 감독이 보낼 명령을 보고 승인한다.
   두 번째 경로도, 우회 플래그도 없다: `run_commands` 하나뿐이다.
3. **못 보낸 큐는 사유와 함께 보고된다** — 「전부 반영」을 말하지 않는다.
"""

from __future__ import annotations

import threading

import pytest

from server.safety.audit import AuditLog
from server.safety.gate import SafetyGate
from server.web.approval_bridge import ApprovalChannel
from server.web.session import ChatSession, SongTimelineStore
from server.web.timeline_library import SongTimelineLibrary

from .test_safety_gate import FakeConsole


class RefusingProvider:
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
        "layer_mapping": [
            {"role": "key", "group_no": 11, "group_name": "KEY"},
            {"role": "back", "group_no": 12, "group_name": "BACK"},
        ],
        "sections": [
            {
                "index": 1,
                "label": "INTRO",
                "start_ms": 0,
                "cue_number": 10,
                "d_level": 3,
                "palette": [],
                "position": "Center",
                "texture": "flat",
                "fx": [],
                "accents": [],
                "mib": False,
                "trig_time_seconds": None,
                "intensity": [{"group": "KEY", "level": 60}],
                "fixture_groups": ["KEY"],
                "mood": "차분",
            },
            {
                "index": 2,
                "label": "VERSE1",
                "start_ms": 8_000,
                "cue_number": 20,
                "d_level": 3,
                "palette": [],
                "position": "Center",
                "texture": "flat",
                "fx": [],
                "accents": [],
                "mib": False,
                "trig_time_seconds": None,
                "intensity": [{"group": "KEY", "level": 60}],
                "fixture_groups": ["KEY"],
                "mood": "경쾌",
            },
        ],
    }


@pytest.fixture
def harness(tmp_path):
    console = FakeConsole()
    audit = AuditLog(tmp_path / "audit")
    channel = ApprovalChannel(timeout_seconds=2.0)
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
    return session, console, store, sent, channel


def _run_with_auto_approval(session, sent, channel, text):
    """카드가 뜨면 승인한다. 카드가 없으면 아무 일도 하지 않는다."""
    stop = threading.Event()

    def approve():
        for event in sent:
            if event.get("type") == "approval_request":
                channel.resolve(event["request_id"], approved=True)
                return True
        return False

    def poller():
        while not stop.is_set():
            if approve():
                return
            stop.wait(0.01)

    thread = threading.Thread(target=poller)
    thread.start()
    try:
        return session.run_instruction(text)
    finally:
        stop.set()
        thread.join(timeout=2.0)


# -- 저장과 반영은 다른 행위다 ---------------------------------------------------


def test_saving_a_draft_still_sends_nothing_to_the_console(harness, tmp_path):
    """핀: 반영이 생겨도 저장은 라이브러리에만 남는다 — 콘솔 0건."""
    session, console, store, _sent, _channel = harness
    session.run_instruction("이 구간 더 밝게 해줘", 10)
    library = SongTimelineLibrary(tmp_path / "save-only.json")
    library.save("Sugar 초안", store.latest)
    assert console.executed == []
    assert library.items()


# -- 반영 경로 -------------------------------------------------------------------


def test_apply_sends_only_the_changed_cue_through_the_preview_gate(harness):
    session, console, store, sent, channel = harness
    session.run_instruction("이 구간 더 밝게 해줘", 10)
    assert console.executed == []  # 편집만으로는 아직 0건
    event = _run_with_auto_approval(session, sent, channel, "초안을 콘솔에 반영해줘")
    assert [e for e in sent if e.get("type") == "execution_preview"]
    assert "Store Sequence 210 Cue 10 /Merge" in console.executed
    assert all("Cue 20" not in command for command in console.executed)
    assert "Group 11 ; Attribute 'Dimmer' At 80" in console.executed
    assert "Sequence 210" in event["text"]


def test_apply_before_any_edit_refuses_and_writes_nothing(harness):
    session, console, _store, sent, channel = harness
    event = _run_with_auto_approval(session, sent, channel, "초안을 콘솔에 반영해줘")
    assert "달라진 큐가 없습니다" in event["text"]
    assert console.executed == []


def test_a_cue_whose_groups_have_no_console_number_is_reported_not_claimed(harness):
    """주소 없는 대상은 「반영했습니다」에 섞이지 않는다 — 사유가 답장에 뜬다."""
    session, console, store, sent, channel = harness
    store.latest["sections"][1]["fixture_groups"] = ["MOVER-U"]
    session.run_instruction("큐 20 더 밝게 해줘", 20)
    event = _run_with_auto_approval(session, sent, channel, "초안을 콘솔에 반영해줘")
    assert "role_unaddressed" in event["text"]
    assert "MOVER-U" in event["text"]
    assert "0건" in event["text"]
    assert console.executed == []


def test_a_mood_only_edit_is_reported_as_not_appliable(harness):
    session, console, store, sent, channel = harness
    session.run_instruction("큐 20 무드를 격렬로 바꿔줘", 20)
    event = _run_with_auto_approval(session, sent, channel, "초안을 콘솔에 반영해줘")
    assert "unmapped_look" in event["text"]
    assert console.executed == []


def test_applying_twice_does_not_resend_the_same_cue(harness):
    session, console, store, sent, channel = harness
    session.run_instruction("이 구간 더 밝게 해줘", 10)
    _run_with_auto_approval(session, sent, channel, "초안을 콘솔에 반영해줘")
    first = list(console.executed)
    event = _run_with_auto_approval(session, sent, channel, "초안을 콘솔에 반영해줘")
    assert console.executed == first
    assert "달라진 큐가 없습니다" in event["text"]
