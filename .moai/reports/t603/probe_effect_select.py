"""t603 — 캡처 전 점검: 편집 칸의 고르기 상자 이름표와 효과 상자 선택지를 본다(읽기만)."""

from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from capture import CUES, PANEL, _open  # noqa: E402

with sync_playwright() as pw:
    browser = pw.chromium.launch()
    page = browser.new_page(viewport={"width": 1450, "height": 1000})
    _open(page, f"http://127.0.0.1:{sys.argv[1]}/")
    cues = page.locator(CUES)
    print("cues", cues.count())
    labels: list = []
    for i in range(min(cues.count(), 40)):
        cues.nth(i).click()
        page.wait_for_timeout(200)
        labels = [
            (s.get_attribute("aria-label"), s.is_enabled())
            for s in page.locator(PANEL + " select").all()
        ]
        effect = [entry for entry in labels if entry[0] and "효과" in entry[0]]
        if effect:
            print(i, effect)
            select = page.get_by_label("효과 프리셋", exact=True)
            if select.count():
                print("  options", select.first.locator("option").all_inner_texts()[:8])
            break
    else:
        print("no effect select; last labels", labels)
    browser.close()
