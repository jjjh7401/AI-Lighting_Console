"""t299 Phase 3 — 큐시트 반영 한 번에 승인 카드가 몇 장 뜨는가.

배차서가 지목한 자리다. `_cue_sheet_draft_apply`(`server/web/session.py:9041`)는
`ExecutionContext(approval_owned_by_caller=True)` 로 디스패치하고, 그 직전에
`_accept_draft_apply_batch`(:8980)가 **자기 채널로** 수락을 한 번 받는다.
그 플래그는 *봉합* 카드를 막는 장치이고(t323), 분류 층이 만드는 카드는 막지
않는다 — `gate.screen(risk=None)` 은 `held` 가 비지 않으면 요청을 만든다
(`server/safety/gate.py:399·415`).

그래서 이 프로브는 「한 동작 → 카드 몇 장」을 **센다**. 추론이 아니라 실측이다.
확대 전에 한 번, 확대 후에 한 번 돌리면 두 회차가 바로 대조가 된다.

카드마다 사유·항목 수를 함께 찍는다 — 두 장이면 그 둘이 같은 카드의 재전송이
아니라 서로 다른 요청임을 문면으로 보여야 한다.

실행:  uv run python reports/classifygap-t299-p3/probe_cuesheet_cards.py
"""

from __future__ import annotations

import sys
import tempfile
import threading
from pathlib import Path

import server
from server.safety.audit import AuditLog
from server.safety.gate import SafetyGate
from server.safety.ruleset import load_ruleset
from server.tests.test_safety_gate import FakeConsole
from server.web.approval_bridge import ApprovalChannel
from server.web.session import ChatSession, SongTimelineStore
from server.web.timeline_library import SongTimelineLibrary


class RefusingProvider:
    def complete(self, *args, **kwargs):
        raise AssertionError("이 경로는 모델을 부르지 않는다")


def _timeline() -> dict:
    """`test_web_cue_sheet_apply.py::_timeline` 과 같은 초안."""
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


def _build(tmp: Path):
    console = FakeConsole()
    audit = AuditLog(tmp / "audit")
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
        timeline_library=SongTimelineLibrary(tmp / "library.json"),
    )
    return session, console, sent, channel


def _approve_everything(session, sent, channel, text):
    """카드가 몇 장 뜨든 **전부** 승인한다.

    스위트의 폴러는 첫 장을 승인하고 곧바로 돌아간다(`test_web_cue_sheet_apply.py`
    `_run_with_auto_approval`, `test_seeded_song_apply.py` `_run_with_auto_approval`).
    그래서 카드가 두 장이면 둘째 장은 아무도 승인하지 않고 타임아웃으로 거절된다 —
    그것이 그 일곱 검사가 빨개지는 기전이다. 이 프로브는 그 기전을 배제한 채
    **장수만** 재려고 전부 승인한다.
    """
    stop = threading.Event()
    resolved: set[str] = set()

    def poller():
        while not stop.is_set():
            for event in list(sent):
                if event.get("type") != "approval_request":
                    continue
                request_id = event["request_id"]
                if request_id in resolved:
                    continue
                resolved.add(request_id)
                channel.resolve(request_id, approved=True)
            stop.wait(0.01)

    thread = threading.Thread(target=poller)
    thread.start()
    try:
        return session.run_instruction(text)
    finally:
        stop.set()
        thread.join(timeout=3.0)


def main() -> None:
    rs = load_ruleset()
    print(f"interpreter : {sys.version.split()[0]}")
    print(f"server pkg  : {server.__file__}")
    print(f"ruleset ver : {rs.version}")
    print(f"blacklist   : {list(rs.blacklist)}\n")

    tmp = Path(tempfile.mkdtemp(prefix="t299p3-cuesheet-"))
    session, console, sent, channel = _build(tmp)

    # 1) 편집만 — 아직 콘솔 0건이어야 한다.
    session.run_instruction("이 구간 더 밝게 해줘", 10)
    print(f"편집 뒤 콘솔 실행    : {console.executed}")

    # 2) 반영 한 동작. 카드를 전부 승인하면서 장수를 센다.
    event = _approve_everything(session, sent, channel, "초안을 콘솔에 반영해줘")

    cards = [e for e in sent if e.get("type") == "approval_request"]
    print(f"\n한 동작(초안 반영) -> 승인 요청 : {len(cards)} 장")
    for index, card in enumerate(cards, start=1):
        items = card.get("items") or ()
        print(f"\n  카드 {index}/{len(cards)}  request_id={card.get('request_id')!r}")
        print(f"    항목 수: {len(items)}")
        for item in items:
            command = (
                item.get("command") if isinstance(item, dict) else getattr(item, "command", None)
            )
            reasons = (
                item.get("risk_reasons")
                if isinstance(item, dict)
                else getattr(item, "risk_reasons", None)
            )
            print(f"      {command!r:52} | {reasons}")

    print(f"\n콘솔에 나간 명령 : {console.executed}")
    print(f"답장 발췌        : {event['text'][:160]!r}")

    audit = AuditLog(tmp / "audit")
    kinds = [
        (e.get("event"), e.get("kind"))
        for e in audit.iter_events()
        if e.get("event") in ("approved", "rejected")
    ]
    print(f"감사 로그 승인/거절 항목: {kinds}")


if __name__ == "__main__":
    main()
