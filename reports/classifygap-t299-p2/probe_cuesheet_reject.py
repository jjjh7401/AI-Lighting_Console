"""t299 Phase 2 — 카드 한 장을 **거절**하면 콘솔에 0건 나가는가.

「카드가 한 장이 됐다」만으로는 부족하다. 질문자를 게이트로 옮긴 뒤에도 거절이
실제로 막는지를 따로 재야 한다 — 카드를 한 장으로 줄이면서 거절 경로를 잃으면
그건 개선이 아니라 게이트 우회다.

같은 하네스를 쓰고 폴러만 바꾼다: 뜨는 카드를 전부 **거절**한다.

실행:  uv run python reports/classifygap-t299-p2/probe_cuesheet_reject.py
"""

from __future__ import annotations

import sys
import tempfile
import threading
from pathlib import Path

from probe_cuesheet_cards import _build

import server
from server.safety.audit import AuditLog
from server.safety.ruleset import load_ruleset


def _decline_everything(session, sent, channel, text):
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
                channel.resolve(request_id, approved=False)
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
    print(f"ruleset ver : {rs.version}\n")

    tmp = Path(tempfile.mkdtemp(prefix="t299p2-reject-"))
    session, console, sent, channel = _build(tmp)

    session.run_instruction("이 구간 더 밝게 해줘", 10)
    event = _decline_everything(session, sent, channel, "초안을 콘솔에 반영해줘")

    cards = [e for e in sent if e.get("type") == "approval_request"]
    print(f"한 동작(초안 반영) -> 승인 요청 : {len(cards)} 장 (전부 거절함)")
    print(f"콘솔에 나간 명령               : {console.executed}")
    print(f"답장 발췌                      : {event['text'][:120]!r}")

    audit = AuditLog(tmp / "audit")
    kinds = [
        (e.get("event"), e.get("kind"))
        for e in audit.iter_events()
        if e.get("event") in ("approved", "rejected")
    ]
    print(f"감사 로그 승인/거절 항목        : {kinds}")


if __name__ == "__main__":
    main()
