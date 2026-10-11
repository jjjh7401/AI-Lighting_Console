"""t588 — 늘 열린 고르기에서 적용하지 않은 입력이 다른 막대로 새지 않는지 잰다.

막대 A 의 밝기 값에 70 을 넣고(적용 안 함) → 막대 B 로 갔다가 → 다시 A 로 오면 A 의
현재 값이 보여야 한다. B 에서도 70 이 아니라 B 의 값이 보여야 한다.

실행: uv run --with playwright python .moai/reports/t588/probe_reseed.py 8831
"""

import json
import sys

from playwright.sync_api import sync_playwright

port = int(sys.argv[1])
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
    value = page.locator(".beat-grid-cue-panel input[aria-label='밝기 값(%)']")

    cues.nth(2).click()
    page.wait_for_timeout(300)
    report["A_initial"] = value.input_value() if value.count() else None
    value.fill("70")
    report["A_typed"] = value.input_value()

    cues.nth(5).click()
    page.wait_for_timeout(300)
    report["B_shown"] = (
        value.input_value() if value.count() else "(밝기 값 칸 없음 — 모드가 값이 아님)"
    )

    cues.nth(2).click()
    page.wait_for_timeout(300)
    report["A_back"] = value.input_value() if value.count() else None
    browser.close()
report["typed_value_leaked"] = report.get("B_shown") == "70" or report.get("A_back") == "70"
print(json.dumps(report, ensure_ascii=False, indent=1))
