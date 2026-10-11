"""t588 — 무빙 줄 막대를 고르면 「움직임」 고르기가 처음부터 열리는지, 되돌리기가 되는지 잰다.

실행: uv run --with playwright python .moai/reports/t588/probe_mover.py 8831 after
"""

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent
port, tag = int(sys.argv[1]), sys.argv[2]
report: dict = {}
with sync_playwright() as pw:
    browser = pw.chromium.launch()
    page = browser.new_page(viewport={"width": 1450, "height": 1000})
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(f"http://127.0.0.1:{port}/")
    page.get_by_role("button", name="런북 모드 켜기").click(timeout=15000)
    page.get_by_role("button", name="박자 배치 전체화면 열기").click(timeout=15000)
    page.locator(".beat-grid").first.wait_for(timeout=15000)
    page.wait_for_timeout(800)
    row = page.locator(
        ".beat-grid-track", has=page.locator(".beat-grid-track-name", has_text="MOVER-U")
    )
    row.locator(".beat-grid-cue:not(.beat-grid-cue-gap):not(.beat-grid-cue-ghost)").nth(1).click()
    page.wait_for_timeout(400)
    panel = page.locator(".beat-grid-cue-panel")
    movement = panel.locator(".beat-grid-cue-field[data-field='움직임']")
    report["movement_selects_open"] = movement.locator("select").count()
    shape = movement.locator("select[aria-label='움직임 모양']")
    report["shape_before"] = shape.input_value() if shape.count() else None
    if shape.count():
        options = shape.locator("option").evaluate_all("os => os.map(o => o.value)")
        pick = next((v for v in options if v and v != report["shape_before"]), None)
        if pick:
            shape.select_option(pick)
            report["shape_changed_to"] = shape.input_value()
            movement.get_by_role("button", name="되돌리기").click()
            page.wait_for_timeout(300)
            report["shape_after_cancel"] = movement.locator(
                "select[aria-label='움직임 모양']"
            ).input_value()
    report["panel_selects_total"] = panel.locator("select").count()
    panel.screenshot(path=str(OUT / f"probe_{tag}_mover_panel.png"))
    report["page_errors"] = errors
    browser.close()
print(json.dumps(report, ensure_ascii=False, indent=1))
