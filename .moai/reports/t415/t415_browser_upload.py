"""t415 — 실제 브라우저에서 곡 업로드를 관측한다 (콘솔 가짜 포트, 읽기 전용 실측).

증거로 남기는 것: 보낸 WS 프레임의 종류와 크기, 서버 고지 문구(sha256·바이트 수), 스크린샷.
"""

import hashlib
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8799/"
OUT = Path(__file__).parent / "t415-evidence"
OUT.mkdir(exist_ok=True)

results = []
with sync_playwright() as pw:
    browser = pw.chromium.launch()
    page = browser.new_page()
    sent: list[tuple[str, int]] = []
    received: list[str] = []

    def on_ws(ws):
        def on_sent(payload):
            text = payload if isinstance(payload, str) else payload.decode("utf-8", "replace")
            try:
                kind = json.loads(text).get("type", "?")
            except ValueError:
                kind = "?"
            sent.append((kind, len(text.encode("utf-8"))))

        def on_recv(payload):
            text = payload if isinstance(payload, str) else ""
            if "첨부됨" in text or "song_audio" in text:
                received.append(text[:400])

        ws.on("framesent", on_sent)
        ws.on("framereceived", on_recv)

    page.on("websocket", on_ws)
    page.goto(URL)
    page.wait_for_timeout(2500)
    file_input = page.locator("input.composer-file-input")
    print("input disabled:", file_input.is_disabled())

    for path in sys.argv[1:]:
        data = Path(path).read_bytes()
        sent.clear()
        received.clear()
        file_input.set_input_files(path)
        name = Path(path).name
        try:
            page.get_by_text(f"곡 «{name}» 첨부됨").wait_for(timeout=60000)
            ui_attached = True
        except Exception:
            ui_attached = False
        page.wait_for_timeout(4000)  # 서버 고지 도착 대기
        shot = OUT / f"{hashlib.md5(name.encode()).hexdigest()[:8]}.png"
        page.screenshot(path=str(shot), full_page=True)
        row = {
            "file": name,
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "ui_attached_label": ui_attached,
            "frames_sent": [k for k, _ in sent if k.startswith("song_audio")],
            "max_frame_bytes": max((n for _, n in sent), default=0),
            "server_notice_has_sha256": any(
                hashlib.sha256(data).hexdigest() in r for r in received
            ),
            "server_notices": received,
            "screenshot": str(shot),
        }
        results.append(row)
        printable = {k: v for k, v in row.items() if k != "server_notices"}
        print(json.dumps(printable, ensure_ascii=False))
    browser.close()

(OUT / "results.json").write_text(
    json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
)
