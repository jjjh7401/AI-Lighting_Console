"""t599 — 위치 칸에서 「＋ 새 프리셋 만들기…」를 고른 모습을 전후로 찍는다.

실행(serve_fake.py 가 떠 있어야 한다 — 콘솔은 FakeConsole,
가짜 위치 풀 {41: 'LA Center', 61: 이름 없음}):
  uv run --with uvicorn python .moai/reports/t599/serve_fake.py 8873
  uv run --with playwright python .moai/reports/t599/capture.py 8873 before
  uv run --with playwright python .moai/reports/t599/capture.py 8873 after
출력: .moai/reports/t599/{tag}/ — 칸 크롭 + steps.json(무엇을 눌렀고 무엇이 보였나)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

W, H = 1450, 1000
CUES = ".beat-grid-cue:not(.beat-grid-cue-gap):not(.beat-grid-cue-ghost)"
PANEL = ".beat-grid-cue-panel"
ARIA = "위치 프리셋"
DIALOG = "[data-testid=beat-grid-new-preset-dialog]"


def _open(page: Page, base: str) -> None:
    page.add_init_script("localStorage.setItem('ma3-copilot.runbook-mode', 'true')")
    page.goto(base)
    runbook = page.get_by_role("button", name="런북 모드 켜기")
    runbook.wait_for(timeout=15000)
    runbook.click()
    page.get_by_role("button", name="박자 배치 전체화면 열기").click(timeout=15000)
    page.locator(".beat-grid").first.wait_for(timeout=15000)
    page.wait_for_timeout(1500)
    drawer = page.locator('button[title^="▤ 프리셋 서랍"]').first
    if drawer.count() and drawer.is_enabled():
        drawer.click()
        page.wait_for_timeout(1200)
        page.locator('[aria-label="프리셋 서랍"] [aria-label="닫기"]').first.click()
        page.wait_for_timeout(300)


def _panel_text(page: Page) -> str:
    loc = page.locator(PANEL).first
    return loc.inner_text() if loc.count() else ""


def main() -> None:
    port, tag = int(sys.argv[1]), sys.argv[2]
    out = Path(__file__).resolve().parent / tag
    out.mkdir(parents=True, exist_ok=True)
    steps: dict[str, object] = {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": W, "height": H})
        _open(page, f"http://127.0.0.1:{port}/")
        cues = page.locator(CUES)
        idx = None
        for i in range(cues.count()):
            cues.nth(i).click()
            page.wait_for_timeout(250)
            sel = page.get_by_label(ARIA, exact=True)
            if sel.count() and sel.first.is_visible() and sel.first.is_enabled():
                idx = i
                break
        steps["cue_index"] = idx
        if idx is not None:
            page.get_by_label(ARIA, exact=True).first.select_option("__new")
            page.wait_for_timeout(300)
            steps["dialog_visible"] = page.locator(DIALOG).count()
            page.locator(PANEL).first.screenshot(path=str(out / "1_selected_new.png"))
            if steps["dialog_visible"]:
                dialog = page.locator(DIALOG).first
                steps["dialog_text"] = dialog.inner_text()
                coord_inputs = dialog.locator("input[type=number]")
                steps["coord_inputs"] = coord_inputs.count()
                page.get_by_label("콘솔 이름(영문·숫자)").first.fill("LA Center Front")
                page.get_by_label("설명(한국어)").first.fill("무대 앞 가운데 바닥")
                for n, value in enumerate(("0", "-2", "0")[: coord_inputs.count()]):
                    coord_inputs.nth(n).fill(value)
                page.locator(PANEL).first.screenshot(path=str(out / "2_filled.png"))
                create = page.get_by_role("button", name="만들기").first
                steps["create_enabled"] = create.is_enabled()
                if create.is_enabled():
                    create.click()
                    page.wait_for_timeout(1500)
                page.screenshot(path=str(out / "3_after_create_full.png"))
                page.locator(PANEL).first.screenshot(path=str(out / "3_after_create.png"))
                body = page.locator("body").inner_text()
                steps["reply_lines"] = [
                    line
                    for line in body.split("\n")
                    if any(
                        k in line for k in ("승인 대기", "번호대", "기본 풀", "위치 프리셋", "거절")
                    )
                ][:8]
                sel = page.get_by_label(ARIA, exact=True).first
                steps["select_value_after"] = sel.input_value() if sel.count() else None
        browser.close()
    (out / "steps.json").write_text(json.dumps(steps, ensure_ascii=False, indent=1))
    print(json.dumps(steps, ensure_ascii=False))


if __name__ == "__main__":
    main()
