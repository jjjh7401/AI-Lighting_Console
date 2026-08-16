"""One-shot WS driver for the two remaining live checks (2026-08-16).

Sends one chat instruction, answers question cards by PROMPT-KEYWORD routing
(first matching rule wins; default = first option), auto-approves approval
cards, prints every event compactly, exits on chat_response.

    uv run python tools/ws_live_check.py "<instruction>"
"""

from __future__ import annotations

import asyncio
import json
import sys

import websockets

URL = "ws://127.0.0.1:8765/ws"

#: (prompt substring, answer) — answer None means "first option label".
RULES: list[tuple[str, str | None]] = [
    ("어느 시퀀스에 저장", None),  # verified-empty pick → first proposal
    ("프리셋 몇 번부터", None),  # verified-ready start → first proposal
    ("타이밍 방식", "수동 Go"),
    ("레이어 역할을 추정", "이 매핑 사용"),
    ("무드를 다시 지정", None),  # requery → first role option
    ("베이스 컬러", None),
    ("타임코드", "취소 (계획 보존)"),  # unexpected timecode conflict → bail safely
    ("저장할까요", "승인"),
    ("배분 계획", "승인"),  # setlist plan card headline
    ("어느 번호부터 배분", None),  # alternate base proposal
]


def pick_answer(prompt: str, options: list[str]) -> str:
    for needle, fixed in RULES:
        if needle in prompt:
            return fixed if fixed is not None else (options[0] if options else "승인")
    # Interview Q1~Q5 and anything else: first option, else free text.
    return options[0] if options else "승인"


async def drive(instruction: str) -> None:
    async with websockets.connect(
        URL,
        max_size=2**24,
        origin="http://127.0.0.1:8765",
        subprotocols=["copilot.v1"],
    ) as ws:
        await ws.send(json.dumps({"v": 1, "type": "chat", "text": instruction}))
        while True:
            event = json.loads(await asyncio.wait_for(ws.recv(), timeout=300))
            kind = event.get("type")
            if kind == "approval_request":
                print(f"[approve] {event.get('summary', '')[:150]}")
                await ws.send(
                    json.dumps(
                        {
                            "v": 1,
                            "type": "approval_decision",
                            "request_id": event["request_id"],
                            "approved": True,
                        }
                    )
                )
            elif kind == "question_request":
                prompt = event.get("prompt", "")
                options = [o.get("label", "") for o in event.get("options", [])]
                answer = pick_answer(prompt, options)
                print(f"[card] {prompt[:110]!r} opts={options} -> {answer!r}")
                await ws.send(
                    json.dumps(
                        {
                            "v": 1,
                            "type": "question_answer",
                            "request_id": event["request_id"],
                            "answer": answer,
                        }
                    )
                )
            elif kind == "chat_response":
                print("=== RESPONSE ===")
                print(event.get("text", "")[:1200])
                print("--- commands ---")
                for row in event.get("commands", [])[:40]:
                    print(f"  {row.get('status', '?'):14s} {row.get('command', '')[:110]}")
                return
            elif kind == "song_timeline":
                tl = event.get("timeline", {})
                print(f"[timeline] lifecycle={tl.get('lifecycle')} seq={tl.get('sequence_number')}")
            else:
                print(f"[{kind}]")


if __name__ == "__main__":
    asyncio.run(drive(sys.argv[1]))
