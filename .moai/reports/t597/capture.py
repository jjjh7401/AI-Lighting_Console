"""t597 — 일반 편집(밝기 값)을 서버가 거절할 때 그 사유가 칸 옆에 보이는지 전후로 찍는다.

실행(t589 serve_fake.py 가 떠 있어야 한다 — 콘솔은 FakeConsole, 쓰기는 파일로 남는다):
  uv run --with uvicorn python .moai/reports/t589/serve_fake.py 8901 dist-before
  uv run --with uvicorn python .moai/reports/t589/serve_fake.py 8902 dist
  uv run --with playwright python .moai/reports/t597/capture.py 8901 before
  uv run --with playwright python .moai/reports/t597/capture.py 8902 after
거절을 일으키는 법: 밝기 값(%)에 150 을 넣고 「적용」 — 화면은 숫자인지만 보고 보내고,
서버(`beat_grid_edit._validate_brightness`)가 0~100 범위로 거절한다.
출력: .moai/reports/t597/{tag}/ — 칸 크롭·전체 캡처 + steps.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

W, H = 1450, 1000
CUES = ".beat-grid-cue:not(.beat-grid-cue-gap):not(.beat-grid-cue-ghost)"
PANEL = ".beat-grid-cue-panel"
REASON = "밝기 값(%)은 0~100 사이여야 합니다"


def _open(page: Page, base: str) -> None:
    page.add_init_script("localStorage.setItem('ma3-copilot.runbook-mode', 'true')")
    page.goto(base)
    runbook = page.get_by_role("button", name="런북 모드 켜기")
    runbook.wait_for(timeout=15000)
    runbook.click()
    page.get_by_role("button", name="박자 배치 전체화면 열기").click(timeout=15000)
    page.locator(".beat-grid").first.wait_for(timeout=15000)
    page.wait_for_timeout(1500)


def _pick_value_cue(page: Page) -> int | None:
    """밝기 값(%) 입력이 보이는 첫 막대를 고른다(모드가 값이 아니면 값으로 바꾼다)."""
    cues = page.locator(CUES)
    for i in range(cues.count()):
        cues.nth(i).click()
        page.wait_for_timeout(250)
        mode = page.get_by_label("밝기 모드", exact=True)
        if not (mode.count() and mode.first.is_visible()):
            continue
        mode.first.select_option("value")
        page.wait_for_timeout(150)
        box = page.get_by_label("밝기 값(%)", exact=True)
        if box.count() and box.first.is_visible() and box.first.is_enabled():
            return i
    return None


def main() -> None:
    port, tag = int(sys.argv[1]), sys.argv[2]
    out = Path(__file__).resolve().parent / tag
    out.mkdir(parents=True, exist_ok=True)
    steps: dict[str, object] = {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": W, "height": H})
        _open(page, f"http://127.0.0.1:{port}/")
        idx = _pick_value_cue(page)
        steps["cue_index"] = idx
        if idx is not None:
            page.get_by_label("밝기 값(%)", exact=True).first.fill("150")
            page.locator(PANEL).first.screenshot(path=str(out / "1_filled_150.png"))
            apply_btn = page.locator(PANEL).get_by_role("button", name="적용").first
            apply_btn.click()
            page.wait_for_timeout(1200)
            page.locator(PANEL).first.screenshot(path=str(out / "2_after_apply.png"))
            page.screenshot(path=str(out / "2_after_apply_full.png"))
            panel = page.locator(PANEL).first.inner_text()
            steps["panel_after_apply"] = panel
            steps["reason_in_panel"] = REASON in panel
            steps["reason_anywhere_on_page"] = REASON in page.locator("body").inner_text()
            steps["reject_note_count"] = page.locator(".beat-grid-edit-reject").count()
        browser.close()
    (out / "steps.json").write_text(json.dumps(steps, ensure_ascii=False, indent=1))
    print(json.dumps({k: v for k, v in steps.items() if k != "panel_after_apply"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
