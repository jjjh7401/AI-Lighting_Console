"""t603 — 효과 칸에서 「＋ 새 프리셋 만들기…」를 고르고 만든 뒤, 「⇪ 콘솔에 반영」 승인 카드까지 전후로 찍는다.

실행(serve_fake.py 가 떠 있어야 한다 — 콘솔은 FakeConsole):
  uv run --with uvicorn python .moai/reports/t603/serve_fake.py 8874
  uv run --with playwright python .moai/reports/t603/capture.py 8874 before
  uv run --with playwright python .moai/reports/t603/capture.py 8874 after
출력: .moai/reports/t603/{tag}/ — 칸 크롭 + steps.json(무엇을 눌렀고 무엇이 보였나)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

W, H = 1450, 1000
CUES = ".beat-grid-cue:not(.beat-grid-cue-gap):not(.beat-grid-cue-ghost)"
PANEL = ".beat-grid-cue-panel"
ARIA = "효과(움직임) 프리셋"  # 편집 칸 효과 고르기 상자의 이름표(probe_effect_select.py 로 확인)
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
        # 셋째 인자: 찍을 칸 번호(전·후를 같은 칸으로 비교). 없으면 창 안에 「효과 틀」
        # 상자가 나오는 첫 칸(= 효과 종류가 정해진 칸)을 찾는다.
        forced = int(sys.argv[3]) if len(sys.argv) > 3 else None
        idx = None
        for i in [forced] if forced is not None else range(cues.count()):
            cues.nth(i).click()
            page.wait_for_timeout(250)
            sel = page.get_by_label(ARIA, exact=True)
            if not (sel.count() and sel.first.is_visible() and sel.first.is_enabled()):
                continue
            options = sel.first.locator("option").all_inner_texts()
            if not any("새 프리셋" in o for o in options):
                continue
            sel.first.select_option("__new")
            page.wait_for_timeout(300)
            if forced is not None or page.locator(DIALOG).first.get_by_label("효과 틀").count():
                idx = i
                break
            page.get_by_role("button", name="취소").first.click()
            page.wait_for_timeout(200)
        steps["cue_index"] = idx
        if idx is not None:
            steps["dialog_visible"] = page.locator(DIALOG).count()
            page.locator(PANEL).first.screenshot(path=str(out / "1_selected_new.png"))
            if steps["dialog_visible"]:
                dialog = page.locator(DIALOG).first
                steps["dialog_text"] = dialog.inner_text()
                page.get_by_label("콘솔 이름(영문·숫자)").first.fill("LA Sweep 2")
                page.get_by_label("설명(한국어)").first.fill("부드러운 좌우 2박")
                template = dialog.get_by_label("효과 틀")
                steps["template_select"] = template.count()
                if template.count():
                    options = template.first.locator("option").all_inner_texts()
                    steps["template_options"] = options
                    values = template.first.locator("option").evaluate_all(
                        "els => els.map(e => e.value).filter(v => v)"
                    )
                    if values:
                        # 이름(LA Sweep 2)과 맞는 좌우 스윕 틀. 목록에 없으면 첫 틀.
                        chosen = "sweep-soft-wide" if "sweep-soft-wide" in values else values[0]
                        template.first.select_option(chosen)
                        steps["template_chosen"] = chosen
                    dialog.get_by_label("한 바퀴 길이").first.fill("2")
                page.locator(PANEL).first.screenshot(path=str(out / "2_filled.png"))
                create = page.get_by_role("button", name="만들기").first
                steps["create_enabled"] = create.is_enabled()
                if create.is_enabled():
                    create.click()
                    page.wait_for_timeout(1500)
                page.locator(PANEL).first.screenshot(path=str(out / "3_after_create.png"))
                body = page.locator("body").inner_text()
                steps["reply_lines"] = [
                    line
                    for line in body.split("\n")
                    if any(
                        k in line for k in ("승인 대기", "거절", "빈 효과", "빈 프리셋", "레시피")
                    )
                ][:8]
                sel = page.get_by_label(ARIA, exact=True).first
                steps["select_value_after"] = sel.input_value() if sel.count() else None
                page.screenshot(path=str(out / "3_after_create_full.png"))
        browser.close()
    (out / "steps.json").write_text(json.dumps(steps, ensure_ascii=False, indent=1))
    print(json.dumps(steps, ensure_ascii=False))


if __name__ == "__main__":
    main()
