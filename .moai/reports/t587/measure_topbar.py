"""t587 — 상단 바가 창 크기마다 잘리는지 재고, 시안과 앱 상단 바를 같은 창으로 찍는다.

실행(serve_fake.py 가 떠 있어야 한다):
  uv run --with playwright python .moai/reports/t587/measure_topbar.py 8799 before
출력: .moai/reports/t587/{tag}/
  topbar_{tag}.json            창마다 상단 바 상자·넘침·버튼 오른쪽 끝·BPM 알약 글자
  app_{W}x{H}_topbar.png       앱 상단 바 크롭
  app_{W}x{H}_full.png         앱 창(스크롤 없이 보이는 부분)
  mockup_{W}x{H}_topbar.png    시안 상단 바 크롭
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[3]
MOCKUP = (
    ROOT
    / ".moai"
    / "specs"
    / "SPEC-LDBEAT-001"
    / "design"
    / "ldbeat-runbook-ui-proposal-20261008.html"
)
SIZES = [(w, h) for w in (1450, 1700) for h in (900, 1000, 1200)]

_MEASURE_JS = """
() => {
  const bar = document.querySelector('.beat-grid-topbar');
  if (!bar) return null;
  const r = bar.getBoundingClientRect();
  const kids = Array.from(bar.children).map(c => {
    const b = c.getBoundingClientRect();
    return {cls: typeof c.className === 'string' ? c.className : '',
            text: (c.innerText || '').trim().slice(0, 60),
            left: Math.round(b.left), right: Math.round(b.right),
            top: Math.round(b.top), width: Math.round(b.width)};
  });
  const rows = new Set(kids.map(k => k.top)).size;
  const clipped = kids.filter(k => k.right > Math.round(r.right) + 1).map(k => k.text);
  const bpm = Array.from(bar.querySelectorAll('.beat-grid-pill')).map(p => p.innerText.trim())
    .find(t => t.startsWith('BPM')) || null;
  return {viewport: [window.innerWidth, window.innerHeight],
          doc_client_width: document.documentElement.clientWidth,
          bar: [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)],
          bar_scroll_width: bar.scrollWidth, bar_client_width: bar.clientWidth,
          overflow: bar.scrollWidth > bar.clientWidth + 1, rows, clipped, bpm_text: bpm,
          children: kids};
}
"""


def main() -> None:
    port = int(sys.argv[1])
    tag = sys.argv[2]
    out = Path(__file__).resolve().parent / tag
    out.mkdir(parents=True, exist_ok=True)
    base = f"http://127.0.0.1:{port}/"
    result = {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for w, h in SIZES:
            key = f"{w}x{h}"
            page = browser.new_page(viewport={"width": w, "height": h})
            page.add_init_script("localStorage.setItem('ma3-copilot.runbook-mode', 'true')")
            page.goto(base)
            runbook = page.get_by_role("button", name="런북 모드 켜기")
            runbook.wait_for(timeout=15000)
            runbook.click()
            page.get_by_role("button", name="박자 배치 전체화면 열기").click(timeout=15000)
            page.locator(".beat-grid-topbar").first.wait_for(timeout=15000)
            page.wait_for_timeout(1200)
            result[key] = page.evaluate(_MEASURE_JS)
            page.screenshot(path=str(out / f"app_{key}_full.png"))
            page.locator(".beat-grid-topbar").first.screenshot(
                path=str(out / f"app_{key}_topbar.png")
            )
            page.close()

            mp = browser.new_page(viewport={"width": w, "height": h})
            mp.goto(MOCKUP.as_uri())
            mp.wait_for_timeout(500)
            mp.locator(".top").first.screenshot(path=str(out / f"mockup_{key}_topbar.png"))
            mp.close()
        browser.close()
    (out / f"topbar_{tag}.json").write_text(json.dumps(result, ensure_ascii=False, indent=1))
    for key, m in result.items():
        if m is None:
            print(key, "topbar not found")
            continue
        print(
            key,
            "doc_w",
            m["doc_client_width"],
            "bar_w",
            m["bar"][2],
            "scrollW",
            m["bar_scroll_width"],
            "overflow",
            m["overflow"],
            "rows",
            m["rows"],
            "clipped",
            m["clipped"],
            "|",
            m["bpm_text"],
        )


if __name__ == "__main__":
    main()
