"""t591 — 늘 열린 편집 칸에서 무빙 줄 막대를 골랐을 때, 스크롤 없이 첫 화면에 몇 칸이 보이나 센다.

「보인다」 = 칸(.beat-grid-cue-field)의 위·아래가 모두 편집 칸 상자(.beat-grid-cue-panel)의
보이는 영역 안, 그리고 창(viewport) 안에 있다. 반만 걸친 칸은 따로 센다.

실행: uv run --with playwright python .moai/reports/t591/probe_fields.py 8842 after
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
    for width in (1450, 1700):
        page = browser.new_page(viewport={"width": width, "height": 1000})
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
        page.wait_for_timeout(500)
        panel = page.locator(".beat-grid-cue-panel")
        result = panel.evaluate(
            """(panel) => {
              const p = panel.getBoundingClientRect();
              const top = Math.max(p.top, 0), bottom = Math.min(p.bottom, window.innerHeight);
              const fields = [...panel.querySelectorAll('.beat-grid-cue-field')].map((f) => {
                const r = f.getBoundingClientRect();
                const label = (f.querySelector('.beat-grid-cue-field-label')||{}).textContent || f.dataset.field;
                const state = r.top >= top && r.bottom <= bottom ? 'full'
                  : (r.bottom > top && r.top < bottom ? 'partial' : 'hidden');
                return { label: label.trim(), editing: f.classList.contains('is-editing'),
                         top: Math.round(r.top), bottom: Math.round(r.bottom), state };
              });
              return { panel: { top: Math.round(p.top), bottom: Math.round(p.bottom),
                                height: Math.round(p.height), scrollHeight: panel.scrollHeight,
                                clientHeight: panel.clientHeight },
                       viewport_h: window.innerHeight, fields };
            }"""
        )
        result["full"] = sum(1 for f in result["fields"] if f["state"] == "full")
        result["partial"] = sum(1 for f in result["fields"] if f["state"] == "partial")
        result["total"] = len(result["fields"])
        result["page_errors"] = errors
        panel.screenshot(path=str(OUT / f"{tag}_{width}_mover_panel.png"))
        report[str(width)] = result
        page.close()
    browser.close()
(OUT / f"probe_fields_{tag}.json").write_text(json.dumps(report, ensure_ascii=False, indent=1))
for w, r in report.items():
    print(w, "full", r["full"], "partial", r["partial"], "total", r["total"], "errors", len(r["page_errors"]),
          [(f["label"], f["state"]) for f in r["fields"]])
