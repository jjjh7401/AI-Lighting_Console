"""t589 — 편집 칸에서 「＋ 새 프리셋 만들기…」를 고른 모습을 전후로 찍는다.

실행(serve_fake.py 가 떠 있어야 한다 — 콘솔은 FakeConsole):
  uv run --with playwright python .moai/reports/t589/capture.py 8872 before
  uv run --with playwright python .moai/reports/t589/capture.py 8872 after
출력: .moai/reports/t589/{tag}/  — 칸 크롭·창 캡처 + steps.json(무엇을 눌렀고 무엇이 보였나)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

W, H = 1450, 1000
CUES = ".beat-grid-cue:not(.beat-grid-cue-gap):not(.beat-grid-cue-ghost)"
PANEL = ".beat-grid-cue-panel"


def _open(page: Page, base: str) -> None:
    page.add_init_script("localStorage.setItem('ma3-copilot.runbook-mode', 'true')")
    page.goto(base)
    runbook = page.get_by_role("button", name="런북 모드 켜기")
    runbook.wait_for(timeout=15000)
    runbook.click()
    page.get_by_role("button", name="박자 배치 전체화면 열기").click(timeout=15000)
    page.locator(".beat-grid").first.wait_for(timeout=15000)
    page.wait_for_timeout(1500)
    # 편집 칸 드롭다운은 서랍이 풀을 읽은 뒤에 켜진다 — 한 번 열었다 닫는다.
    drawer = page.locator('button[title^="▤ 프리셋 서랍"]').first
    if drawer.count() and drawer.is_enabled():
        drawer.click()
        page.wait_for_timeout(1200)
        page.locator('[aria-label="프리셋 서랍"] [aria-label="닫기"]').first.click()
        page.wait_for_timeout(300)


def _pick_cue_with(page: Page, aria: str) -> int | None:
    """``aria`` 드롭다운이 켜진 첫 막대를 고른다."""
    cues = page.locator(CUES)
    for i in range(cues.count()):
        cues.nth(i).click()
        page.wait_for_timeout(250)
        sel = page.get_by_label(aria, exact=True)
        if sel.count() and sel.first.is_visible() and sel.first.is_enabled():
            return i
    return None


def _panel_text(page: Page) -> str:
    loc = page.locator(PANEL).first
    return loc.inner_text() if loc.count() else ""


def _effect_success(page: Page, out: Path) -> dict[str, object]:
    """효과 종류가 정해진 칸을 찾아 「만들기」가 번호를 배정하는 장면을 찍는다.
    종류를 모르는 칸은 서버가 거절하므로(격자는 그대로) 다음 칸으로 넘어간다."""
    aria = "효과(움직임) 프리셋"
    cues = page.locator(CUES)
    tried = 0
    for i in range(cues.count()):
        cues.nth(i).click()
        page.wait_for_timeout(250)
        sel = page.get_by_label(aria, exact=True)
        if not (sel.count() and sel.first.is_visible() and sel.first.is_enabled()):
            continue
        tried += 1
        sel.first.select_option("__new")
        page.wait_for_timeout(200)
        page.get_by_label("콘솔 이름(영문·숫자)").first.fill("LA Test Wave")
        page.get_by_label("설명(한국어)").first.fill("시험용 파도 움직임")
        page.get_by_role("button", name="만들기").first.click()
        page.wait_for_timeout(1200)
        text = _panel_text(page)
        if "승인 대기" in text:
            page.locator(PANEL).first.screenshot(path=str(out / "effect_ok_after_create.png"))
            page.screenshot(path=str(out / "effect_ok_after_create_full.png"))
            line = next((x for x in text.split("\n") if "승인 대기" in x), "")
            return {"effect_ok_cue_index": i, "effect_ok_tries": tried, "effect_ok_reply": line}
    return {"effect_ok_cue_index": None, "effect_ok_tries": tried}


def main() -> None:
    port, tag = int(sys.argv[1]), sys.argv[2]
    out = Path(__file__).resolve().parent / tag
    out.mkdir(parents=True, exist_ok=True)
    steps: dict[str, object] = {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": W, "height": H})
        _open(page, f"http://127.0.0.1:{port}/")
        for key, aria in (("effect", "효과(움직임) 프리셋"), ("position", "위치 프리셋")):
            idx = _pick_cue_with(page, aria)
            steps[f"{key}_cue_index"] = idx
            if idx is None:
                continue
            page.get_by_label(aria, exact=True).first.select_option("__new")
            page.wait_for_timeout(300)
            steps[f"{key}_dialog_visible"] = page.locator(
                "[data-testid=beat-grid-new-preset-dialog]"
            ).count()
            page.locator(PANEL).first.screenshot(path=str(out / f"{key}_1_selected_new.png"))
            steps[f"{key}_panel_after_select"] = _panel_text(page)
            if not steps[f"{key}_dialog_visible"]:
                continue
            page.get_by_label("콘솔 이름(영문·숫자)").first.fill("LA Test Wave")
            page.get_by_label("설명(한국어)").first.fill("시험용 파도 움직임")
            page.locator(PANEL).first.screenshot(path=str(out / f"{key}_2_filled.png"))
            page.get_by_role("button", name="만들기").first.click()
            page.wait_for_timeout(1200)
            page.screenshot(path=str(out / f"{key}_3_after_create_full.png"))
            page.locator(PANEL).first.screenshot(path=str(out / f"{key}_3_after_create.png"))
            steps[f"{key}_panel_after_create"] = _panel_text(page)
            steps[f"{key}_page_mentions"] = [
                s
                for s in ("승인 대기", "번호대가 없어", "새 프리셋", "콘솔 빈칸 미확인")
                if s in page.locator("body").inner_text()
            ]
        if tag == "after":
            steps.update(_effect_success(page, out))
        browser.close()
    (out / "steps.json").write_text(json.dumps(steps, ensure_ascii=False, indent=1))
    print(json.dumps({k: v for k, v in steps.items() if "panel" not in k}, ensure_ascii=False))


if __name__ == "__main__":
    main()
