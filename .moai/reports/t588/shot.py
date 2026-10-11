"""t586 — 작업 중 빠른 확인용: 앱 전체 화면(기본·막대 선택·전환)을 한 크기로 찍는다.

실행: uv run --with playwright python .moai/reports/t586/shot.py 8821 wip 1450 1000
"""

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent
port, tag = int(sys.argv[1]), sys.argv[2]
width = int(sys.argv[3]) if len(sys.argv) > 3 else 1450
height = int(sys.argv[4]) if len(sys.argv) > 4 else 1000
with sync_playwright() as pw:
    browser = pw.chromium.launch()
    page = browser.new_page(viewport={"width": width, "height": height})
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(f"http://127.0.0.1:{port}/")
    page.get_by_role("button", name="런북 모드 켜기").click(timeout=15000)
    page.get_by_role("button", name="박자 배치 전체화면 열기").click(timeout=15000)
    page.locator(".beat-grid").first.wait_for(timeout=15000)
    page.wait_for_timeout(1000)
    page.screenshot(path=str(OUT / f"{tag}_{width}x{height}_default.png"))
    page.locator(".beat-grid-cue:not(.beat-grid-cue-gap):not(.beat-grid-cue-ghost)").nth(2).click()
    page.wait_for_timeout(400)
    page.screenshot(path=str(OUT / f"{tag}_{width}x{height}_selected.png"))
    toggle = page.locator(".beat-grid-transition-toggle").first
    if toggle.count() and toggle.is_enabled():
        toggle.click()
        page.wait_for_timeout(400)
    page.screenshot(path=str(OUT / f"{tag}_{width}x{height}_transition.png"))
    # 틀 아래쪽(명령 줄·조작 안내) — 틀째 스크롤한 뒤(카드 t585 이후 틀이 스크롤한다).
    page.evaluate("document.querySelector('.beat-grid').scrollTop = 1e6")
    page.wait_for_timeout(300)
    page.screenshot(path=str(OUT / f"{tag}_{width}x{height}_bottom.png"))
    browser.close()
print("page errors:", errors)
