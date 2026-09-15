"""t415 후속 — 분할로 올린 곡을 브라우저에서 「분석」까지 태운다 (콘솔 가짜 포트)."""

import json
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).parent / "t415-evidence"
OUT.mkdir(exist_ok=True)
path = sys.argv[1]
name = Path(path).name

with sync_playwright() as pw:
    browser = pw.chromium.launch()
    page = browser.new_page()
    cards: list[dict] = []
    errors: list[str] = []

    def on_ws(ws):
        def on_recv(payload):
            if not isinstance(payload, str):
                return
            try:
                event = json.loads(payload)
            except ValueError:
                return
            if event.get("type") == "question_request":
                cards.append(event)
            if event.get("type") == "error":
                errors.append(f"{event.get('kind')}: {event.get('message')}")

        ws.on("framereceived", on_recv)

    page.on("websocket", on_ws)
    page.goto("http://127.0.0.1:8799/")
    page.wait_for_timeout(2500)
    page.locator("input.composer-file-input").set_input_files(path)
    page.get_by_text(f"곡 «{name}» 첨부됨").wait_for(timeout=60000)
    started = time.monotonic()
    page.get_by_role("button", name="분석").click()
    deadline = started + 180
    while not cards and not errors and time.monotonic() < deadline:
        page.wait_for_timeout(500)
    elapsed = round(time.monotonic() - started, 1)
    page.wait_for_timeout(1500)
    page.screenshot(path=str(OUT / "analyse.png"), full_page=True)
    browser.close()

card = cards[0] if cards else None
summary = {
    "file": name,
    "seconds_to_card": elapsed,
    "card_arrived": card is not None,
    "errors": errors,
    "question": card.get("question") if card else None,
    "multi": card.get("multi") if card else None,
    "option_count": len(card.get("options", [])) if card else 0,
    "options_head": (card.get("options") or [])[:3] if card else [],
}
(OUT / "analyse.json").write_text(
    json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(json.dumps(summary, ensure_ascii=False, indent=2)[:2500])
