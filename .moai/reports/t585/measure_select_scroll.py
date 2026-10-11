"""t585 — 막대를 고를 때 박자 격자 틀(.beat-grid)이 세로로 얼마나 밀리는지, 무엇이 미는지 잰다.

실행: uv run --with playwright python .moai/reports/t585/measure_select_scroll.py 8811 1450 1000
"""

import json
import sys

from playwright.sync_api import sync_playwright

port, width, height = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
with sync_playwright() as pw:
    browser = pw.chromium.launch()
    page = browser.new_page(viewport={"width": width, "height": height})
    page.goto(f"http://127.0.0.1:{port}/")
    page.get_by_role("button", name="런북 모드 켜기").click(timeout=15000)
    page.get_by_role("button", name="박자 배치 전체화면 열기").click(timeout=15000)
    page.locator(".beat-grid").first.wait_for(timeout=15000)
    page.wait_for_timeout(1000)
    # scrollIntoView / focus 호출을 가로채 누가 불렀는지 남긴다(동작은 그대로 통과).
    page.evaluate(
        """() => {
      window.__calls = [];
      const orig = Element.prototype.scrollIntoView;
      Element.prototype.scrollIntoView = function (...a) {
        window.__calls.push(
          {kind: 'scrollIntoView', cls: String(this.className), arg: JSON.stringify(a)});
        return orig.apply(this, a);
      };
      const of = HTMLElement.prototype.focus;
      HTMLElement.prototype.focus = function (...a) {
        window.__calls.push({kind: 'focus', cls: String(this.className), arg: JSON.stringify(a)});
        return of.apply(this, a);
      };
      document.querySelector('.beat-grid').addEventListener('scroll', e => {
        window.__calls.push({kind: 'frame-scroll', top: e.target.scrollTop});
      });
    }"""
    )
    before = page.evaluate("document.querySelector('.beat-grid').scrollTop")
    cue = page.locator(".beat-grid-cue:not(.beat-grid-cue-gap):not(.beat-grid-cue-ghost)").nth(2)
    cue.click()
    page.wait_for_timeout(600)
    after = page.evaluate("document.querySelector('.beat-grid').scrollTop")
    calls = page.evaluate("window.__calls")
    print(
        json.dumps(
            {"frame_scrollTop_before": before, "after": after, "calls": calls[:12]},
            ensure_ascii=False,
            indent=1,
        )
    )
    browser.close()
