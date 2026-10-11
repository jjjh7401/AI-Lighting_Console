"""t585 — 배치 결함 4건의 원인을 계산된 스타일로 잰다(읽기만, 화면 조작은 클릭뿐).

실행(serve_fake.py 가 떠 있어야 한다):
  uv run --with playwright python .moai/reports/t585/measure_layout.py 8799 1450 1000 before
출력: .moai/reports/t585/measure_{tag}_{W}x{H}.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent

#: 요소에서 시작해 <body> 까지 올라가며 크기를 정하는 계산된 스타일을 모은다.
_CHAIN_JS = """
(sel) => {
  const props = ["display","position","height","min-height","max-height","flex","flex-basis",
    "flex-grow","flex-shrink","grid-template-rows","grid-template-columns","grid-row","grid-column",
    "overflow","overflow-x","overflow-y","align-self","z-index","left","top"];
  const out = [];
  let el = document.querySelector(sel);
  while (el && el !== document.documentElement) {
    const cs = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    const plain = el.className && el.className.baseVal === undefined;
    const row = {tag: el.tagName.toLowerCase(), cls: plain ? el.className : "",
      box: [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)],
      scroll: [el.scrollWidth, el.scrollHeight, el.scrollLeft, el.scrollTop]};
    for (const p of props) row[p] = cs.getPropertyValue(p);
    out.push(row);
    el = el.parentElement;
  }
  return out;
}
"""

#: 한 요소의 직계 자식들의 상자와 위치 규칙.
_CHILDREN_JS = """
(sel) => {
  const el = document.querySelector(sel);
  if (!el) return null;
  return Array.from(el.children).map(c => {
    const r = c.getBoundingClientRect(); const cs = getComputedStyle(c);
    return {tag: c.tagName.toLowerCase(), cls: typeof c.className === "string" ? c.className : "",
      text: (c.textContent || "").trim().slice(0, 50),
      box: [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)],
      position: cs.position, zIndex: cs.zIndex, left: cs.left, background: cs.backgroundColor,
      gridColumn: cs.gridColumn};
  });
}
"""


def main() -> None:
    port, width, height, tag = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    result: dict = {"viewport": [width, height]}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": height})
        page.goto(f"http://127.0.0.1:{port}/")
        page.get_by_role("button", name="런북 모드 켜기").click(timeout=15000)
        page.get_by_role("button", name="박자 배치 전체화면 열기").click(timeout=15000)
        page.locator(".beat-grid").first.wait_for(timeout=15000)
        page.wait_for_timeout(1200)
        result["lanes_chain"] = page.evaluate(_CHAIN_JS, ".beat-grid-lanes")
        result["mid_children"] = page.evaluate(_CHILDREN_JS, ".beat-grid-mid")
        result["beat_grid_children"] = page.evaluate(_CHILDREN_JS, "section.beat-grid")
        result["stage_pane_children"] = page.evaluate(_CHILDREN_JS, ".beat-grid-stage-pane")
        result["stage_box_children"] = page.evaluate(_CHILDREN_JS, ".beat-grid-stage-box")
        result["stage_notes_chain"] = page.evaluate(_CHAIN_JS, ".beat-grid-stage-notes")[:3]
        result["doc_scroll"] = page.evaluate("[document.documentElement.scrollHeight, innerHeight]")
        cues = page.locator(".beat-grid-cue:not(.beat-grid-cue-gap):not(.beat-grid-cue-ghost)")
        cues.nth(2).click()
        page.wait_for_timeout(500)
        result["selected_lanes_chain"] = page.evaluate(_CHAIN_JS, ".beat-grid-lanes")[:2]
        result["selected_first_track_children"] = page.evaluate(_CHILDREN_JS, ".beat-grid-track")
        result["selected_mid_children"] = page.evaluate(_CHILDREN_JS, ".beat-grid-mid")
        result["cue_panel_chain"] = page.evaluate(_CHAIN_JS, ".beat-grid-cue-panel")[:3]
        toggle = page.locator(".beat-grid-transition-toggle").first
        if toggle.count() and toggle.is_enabled():
            toggle.click()
            page.wait_for_timeout(400)
        result["transition_panel_chain"] = page.evaluate(_CHAIN_JS, ".beat-grid-cue-panel")[:3]
        browser.close()
    target = OUT / f"measure_{tag}_{width}x{height}.json"
    target.write_text(json.dumps(result, ensure_ascii=False, indent=1))
    print(target)


if __name__ == "__main__":
    main()
