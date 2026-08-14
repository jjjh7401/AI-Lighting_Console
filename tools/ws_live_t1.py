"""One-shot WS driver for T1 live verification.

Sends one chat instruction to the running copilot server, auto-approves
approval cards, answers question cards with a scripted answer, prints every
event, and exits on the chat_response. Usage:

    uv run python tools/ws_live_t1.py "<instruction>" [--answer TEXT]
"""

from __future__ import annotations

import argparse
import asyncio
import json

import websockets

URL = "ws://127.0.0.1:8765/ws"


async def drive(instruction: str, answer: str | None) -> None:
    async with websockets.connect(
        URL,
        max_size=2**24,
        origin="http://127.0.0.1:8765",
        subprotocols=["copilot.v1"],
    ) as ws:
        await ws.send(json.dumps({"v": 1, "type": "chat", "text": instruction}))
        while True:
            event = json.loads(await asyncio.wait_for(ws.recv(), timeout=180))
            kind = event.get("type")
            if kind == "approval_request":
                print(f"[approve] {event.get('request_id')} :: {event.get('summary', '')[:120]}")
                await ws.send(
                    json.dumps(
                        {
                            "v": 1, "type": "approval_decision",
                            "request_id": event["request_id"],
                            "approved": True,
                        }
                    )
                )
            elif kind == "question" and answer is not None:
                print(f"[answer:{answer}] {event.get('prompt', '')[:120]}")
                await ws.send(
                    json.dumps(
                        {
                            "v": 1, "type": "question_answer",
                            "request_id": event["request_id"],
                            "answer": answer,
                        }
                    )
                )
            elif kind == "chat_response":
                print(json.dumps(event, ensure_ascii=False, indent=2))
                return
            else:
                print(f"[{kind}] {json.dumps(event, ensure_ascii=False)[:200]}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("instruction")
    parser.add_argument("--answer", default=None)
    args = parser.parse_args()
    asyncio.run(drive(args.instruction, args.answer))


if __name__ == "__main__":
    main()
