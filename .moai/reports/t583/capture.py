"""t583 — 시안과 앱의 런북 박자 격자 화면을 같은 뷰포트로 찍어 영역별로 나란히 붙인다.

실행(앱 서버가 먼저 떠 있어야 한다 — serve_fake.py):
  uv run --with playwright --with pillow python .moai/reports/t583/capture.py 8798

출력: .moai/reports/t583/side_by_side/
  {mockup,app}_{W}_full.png           전체 화면
  {mockup,app}_{W}_{region}.png       영역 크롭
  {W}_{region}.png                    왼쪽 시안 | 오른쪽 앱
  regions.json                         영역마다 잡혔는지·크기(px)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import Page, sync_playwright

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent / "side_by_side"
MOCKUP = ROOT / "reports" / "ldbeat-runbook-ui-proposal-20261008.html"
WIDTHS = (1450, 1700)
HEIGHT = 1000

#: 영역 이름 -> (시안 선택자, 앱 선택자)
REGIONS = {
    "1_topbar": (".top", ".beat-grid-topbar"),
    "2_play_cluster": (".top .play", ".beat-grid-play-cluster"),
    "3_song_map": (".ov", ".song-overview"),
    "4_timeline": ("#scroller", ".beat-grid-lanes"),
    "5_glance_table": (".pane.tpane", ".beat-grid-glance-pane"),
    "6_stage_2d": (".pane.stage", ".beat-grid-stage-pane"),
    "7_edit_panel": ("#sidePane", ".beat-grid-cue-panel"),
    "8_transition": ("#sidePane", ".beat-grid-cue-panel"),
}


def _shot(page: Page, selector: str, path: Path) -> dict:
    loc = page.locator(selector).first
    if loc.count() == 0 or not loc.is_visible():
        return {"selector": selector, "found": False}
    box = loc.bounding_box()
    loc.screenshot(path=str(path))
    return {"selector": selector, "found": True, "box": box}


def _mockup(page: Page, width: int) -> dict:
    page.goto(MOCKUP.as_uri())
    page.wait_for_timeout(600)
    page.screenshot(path=str(OUT / f"mockup_{width}_full.png"), full_page=True)
    found = {}
    for name, (sel, _) in REGIONS.items():
        if name == "7_edit_panel":
            clip = page.locator("#track .clip[data-r]").nth(2)
            clip.click()
            page.wait_for_timeout(300)
            page.screenshot(path=str(OUT / f"mockup_{width}_full_selected.png"), full_page=True)
        if name == "8_transition":
            page.locator("#track .jt").first.click()
            page.wait_for_timeout(300)
            page.screenshot(path=str(OUT / f"mockup_{width}_full_transition.png"), full_page=True)
        found[name] = _shot(page, sel, OUT / f"mockup_{width}_{name}.png")
    return found


def _app(page: Page, width: int, base: str) -> dict:
    page.add_init_script("localStorage.setItem('ma3-copilot.runbook-mode', 'true')")
    page.goto(base)
    runbook = page.get_by_role("button", name="런북 모드 켜기")
    runbook.wait_for(timeout=15000)
    runbook.click()
    page.get_by_role("button", name="박자 배치 전체화면 열기").click(timeout=15000)
    page.locator(".beat-grid").first.wait_for(timeout=15000)
    page.wait_for_timeout(1500)
    page.screenshot(path=str(OUT / f"app_{width}_full.png"), full_page=True)
    found = {}
    cues = page.locator(".beat-grid-cue:not(.beat-grid-cue-gap):not(.beat-grid-cue-ghost)")
    for name, (_, sel) in REGIONS.items():
        if name == "7_edit_panel":
            cues.nth(2).click()
            page.wait_for_timeout(400)
            page.screenshot(path=str(OUT / f"app_{width}_full_selected.png"), full_page=True)
        if name == "8_transition":
            toggle = page.locator(".beat-grid-transition-toggle").first
            if toggle.count() and toggle.is_enabled():
                toggle.click()
                page.wait_for_timeout(400)
            page.screenshot(path=str(OUT / f"app_{width}_full_transition.png"), full_page=True)
        found[name] = _shot(page, sel, OUT / f"app_{width}_{name}.png")
    found["cue_count"] = cues.count()
    return found


def _font(size: int):
    for candidate in (
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
    ):
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def _pair(width: int, name: str) -> str | None:
    left_p = OUT / f"mockup_{width}_{name}.png"
    right_p = OUT / f"app_{width}_{name}.png"
    imgs = [Image.open(p) if p.exists() else None for p in (left_p, right_p)]
    if all(i is None for i in imgs):
        return None
    pad, head = 16, 34
    blank = Image.new("RGB", (480, 120), (40, 20, 20))
    left, right = (i if i is not None else blank for i in imgs)
    w = left.width + right.width + pad * 3
    h = max(left.height, right.height) + head + pad * 2
    canvas = Image.new("RGB", (w, h), (20, 22, 26))
    draw = ImageDraw.Draw(canvas)
    font = _font(18)
    draw.text((pad, 8), f"시안 · {width}px · {name}" + ("" if imgs[0] else " — 못 찾음"), fill=(230, 230, 230), font=font)
    draw.text((left.width + pad * 2, 8), "앱(구현)" + ("" if imgs[1] else " — 못 찾음"), fill=(230, 230, 230), font=font)
    canvas.paste(left, (pad, head + pad))
    canvas.paste(right, (left.width + pad * 2, head + pad))
    target = OUT / f"{width}_{name}.png"
    canvas.save(target)
    return target.name


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8798
    base = f"http://127.0.0.1:{port}/"
    OUT.mkdir(parents=True, exist_ok=True)
    report: dict = {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for width in WIDTHS:
            m_page = browser.new_page(viewport={"width": width, "height": HEIGHT})
            a_page = browser.new_page(viewport={"width": width, "height": HEIGHT})
            errors: list[str] = []
            a_page.on("pageerror", lambda e, errors=errors: errors.append(str(e)))
            report[str(width)] = {
                "mockup": _mockup(m_page, width),
                "app": _app(a_page, width, base),
                "app_page_errors": errors,
            }
            report[str(width)]["pairs"] = [p for p in (_pair(width, n) for n in REGIONS) if p]
            m_page.close()
            a_page.close()
        browser.close()
    (OUT / "regions.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps({w: {k: v for k, v in r.items() if k in ("pairs", "app_page_errors")} for w, r in report.items()}, ensure_ascii=False))


if __name__ == "__main__":
    main()
