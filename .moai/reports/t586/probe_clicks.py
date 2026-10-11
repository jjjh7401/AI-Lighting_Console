"""t586 — t583 에서 안 눌러 본 두 동작을 잰다: 편집 칸 ✎ 와 타임라인 이음매 ◆.

실행: uv run --with playwright python .moai/reports/t586/probe_clicks.py 8822 <tag>
출력: .moai/reports/t586/probe_<tag>_*.png + 표준출력 JSON
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
    page.goto(f"http://127.0.0.1:{port}/")
    page.get_by_role("button", name="런북 모드 켜기").click(timeout=15000)
    page.get_by_role("button", name="박자 배치 전체화면 열기").click(timeout=15000)
    page.locator(".beat-grid").first.wait_for(timeout=15000)
    page.wait_for_timeout(800)
    cues = page.locator(".beat-grid-cue:not(.beat-grid-cue-gap):not(.beat-grid-cue-ghost)")
    cues.nth(2).click()
    page.wait_for_timeout(400)
    panel = page.locator(".beat-grid-cue-panel")
    report["panel_text_before"] = panel.inner_text()[:400]
    report["panel_controls_before"] = panel.locator("select, input").count()
    pencil = panel.locator(
        ".beat-grid-cue-field[data-field='밝기'] .beat-grid-cue-field-value"
    ).first
    report["pencil_found"] = pencil.count()
    if pencil.count():
        pencil.click()
        page.wait_for_timeout(300)
        report["panel_controls_after_pencil"] = panel.locator("select, input").count()
        panel.screenshot(path=str(OUT / f"probe_{tag}_pencil.png"))
    # 이음매 ◆ — 막대 사이 마름모. 클래스 이름을 모르니 글자로 찾는다.
    panel.get_by_role("button", name="닫기", exact=True).first.click()
    page.wait_for_timeout(300)
    seam = page.locator(".beat-grid-lanes .beat-grid-joint").nth(1)
    report["seam_found"] = seam.count()
    if seam.count():
        report["seam_tag"] = seam.evaluate("e => e.tagName + '.' + e.className")
        seam.click()
        page.wait_for_timeout(400)
        report["after_seam_panel"] = panel.inner_text()[:200] if panel.count() else None
        report["transition_view_open"] = page.locator(".beat-grid-transition-view").count()
        page.screenshot(path=str(OUT / f"probe_{tag}_seam.png"))
    browser.close()
print(json.dumps(report, ensure_ascii=False, indent=1))
