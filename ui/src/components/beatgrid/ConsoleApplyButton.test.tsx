// @vitest-environment jsdom
// 큐 편집 칸의 「⇪ 콘솔에 반영」 시험 — 예전에 상단 바에 있던 버튼이라, 상단 바 시험
// (`BeatGridTopBar.test.tsx`·`BeatGridTopBarApplyProgress.test.tsx`·`BeatGridTopBar.flowChain.test.tsx`)이
// 재던 동작을 그대로 옮겨 잰다: 글자·title·비활성·대기 수 배지·진행 문구·강조 클래스.
// 마크업은 `renderToStaticMarkup`, 누르기는 jsdom + `act` 로 본다.
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CONSOLE_APPLY_LABEL, ConsoleApplyButton, type ConsoleApplyButtonProps } from "./ConsoleApplyButton";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const noop = () => {};
const NOTE = "이 곡의 기본값 없음";

function renderMarkup(props: Partial<ConsoleApplyButtonProps> = {}) {
  return renderToStaticMarkup(<ConsoleApplyButton {...props} />);
}

describe("글자와 title", () => {
  it("풀네임 글자만 그린다 — 상단 바의 lbl-full/lbl-short 짝은 쓰지 않는다", () => {
    expect(CONSOLE_APPLY_LABEL).toBe("⇪ 콘솔에 반영");
    const html = renderMarkup({ onApply: noop });
    expect(html).toContain(">⇪ 콘솔에 반영</button>");
    expect(html).not.toContain("lbl-full");
    expect(html).not.toContain("lbl-short");
    expect(html).not.toContain("⇪ 반영");
  });

  it("배선된 버튼은 켜져 있고 title 은 풀네임이다", () => {
    const html = renderMarkup({ onApply: noop, pendingApplyCount: 2 });
    expect(html).toContain('<button type="button" class="tbtn" title="⇪ 콘솔에 반영">');
    expect(html).not.toContain("disabled");
  });

  it("콜백이 없으면 비활성이고 그 사실을 title 로 말한다", () => {
    const html = renderMarkup({ pendingApplyCount: 2 });
    expect(html).toMatch(/title="⇪ 콘솔에 반영 — 아직 배선 안 됨[^"]*" disabled/);
  });
});

describe("대기 수 배지", () => {
  it("숫자는 그 개수 배지이고, 격자 출처 안내는 배지 툴팁으로 간다(버튼 title 에는 싣지 않는다)", () => {
    const html = renderMarkup({ note: NOTE, onApply: noop, pendingApplyCount: 2 });
    expect(html).toContain(`<span class="badge" title="${NOTE}">2</span>`);
    expect(html).toContain('<button type="button" class="tbtn" title="⇪ 콘솔에 반영">');
    expect(html).not.toContain("badge-dash");
  });

  it("0 도 숫자라 배지로 보인다 — 없음(undefined)·기록 없음(null)과 다르다", () => {
    expect(renderMarkup({ onApply: noop, pendingApplyCount: 0 })).toContain('<span class="badge">0</span>');
  });

  it("숫자 배지에 안내가 없으면 title 을 두지 않는다", () => {
    const html = renderMarkup({ onApply: noop, pendingApplyCount: 2 });
    expect(html).toContain('<span class="badge">2</span>');
  });

  it("반영 기록이 아직 없으면(null) 숫자 대신 「—」 배지와 이유 title 을 보인다", () => {
    const html = renderMarkup({ onApply: noop, pendingApplyCount: null });
    expect(html).toContain(
      '<span class="badge badge-dash" title="반영 기록 없음 — 첫 반영 뒤에 숫자가 보인다">—</span>',
    );
    expect(html).not.toContain('class="badge"');
  });

  it("「—」 배지는 반영 기록 없음 이유 뒤에 안내를 잇는다", () => {
    const html = renderMarkup({ note: NOTE, onApply: noop, pendingApplyCount: null });
    expect(html).toContain(`title="반영 기록 없음 — 첫 반영 뒤에 숫자가 보인다 · ${NOTE}"`);
  });

  it("배지가 없는 배선 전 상태(undefined)에서는 안내를 버튼 title 에 싣는다", () => {
    const html = renderMarkup({ note: NOTE, onApply: noop });
    expect(html).toContain(`title="⇪ 콘솔에 반영 · ${NOTE}"`);
    expect(html).not.toContain('class="badge"');
    expect(html).not.toContain("badge-dash");
  });

  it("배선도 안 됐고 안내도 있으면 둘을 이어 title 에 싣는다", () => {
    const html = renderMarkup({ note: NOTE });
    expect(html).toMatch(/title="⇪ 콘솔에 반영 — 아직 배선 안 됨[^"]*· 이 곡의 기본값 없음" disabled/);
  });
});

describe("진행 문구", () => {
  it("진행 문구가 없으면 진행 표시를 그리지 않는다", () => {
    expect(renderMarkup({ onApply: noop })).not.toContain("beat-grid-apply-progress");
  });

  it("진행 문구가 있으면 반영 버튼 곁(뒤)에 상태 알림으로 보인다", () => {
    const html = renderMarkup({ onApply: noop, applyProgress: "콘솔을 읽는 중 · 12초" });
    expect(html).toContain('class="beat-grid-apply-progress"');
    expect(html).toContain('role="status"');
    expect(html).toContain("콘솔을 읽는 중 · 12초");
    expect(html.indexOf("</button>")).toBeLessThan(html.indexOf("beat-grid-apply-progress"));
  });

  it("누를 곳(승인 대기 중)이 없으면 글자일 뿐 버튼이 아니다", () => {
    const html = renderMarkup({ onApply: noop, applyProgress: "승인 카드를 기다리는 중" });
    expect(html).toContain('<span class="beat-grid-apply-progress" role="status">승인 카드를 기다리는 중</span>');
    expect(html).not.toContain("beat-grid-apply-progress-link");
  });

  it("누를 곳이 있으면 승인 카드로 가는 버튼이 된다", () => {
    const html = renderMarkup({ onApply: noop, applyProgress: "승인 카드를 기다리는 중", onApplyProgressClick: noop });
    expect(html).toContain("beat-grid-apply-progress beat-grid-apply-progress-link");
    expect(html).toContain('title="눌러서 승인 카드로 가기"');
    expect(html).toContain("승인 카드를 기다리는 중 — 승인 카드 보기");
  });
});

describe("강조 클래스(is-next)", () => {
  it("다음 단계가 「반영」일 때(isNext)만 tbtn is-next 이고, 아니면 tbtn 뿐이다", () => {
    expect(renderMarkup({ onApply: noop, isNext: true })).toContain('class="tbtn is-next"');
    expect(renderMarkup({ onApply: noop, isNext: false })).toContain('class="tbtn"');
    expect(renderMarkup({ onApply: noop })).toContain('class="tbtn"');
    expect(renderMarkup({ onApply: noop })).not.toContain("is-next");
  });
});

describe("누르기", () => {
  let container: HTMLElement;
  let root: Root;

  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
  });

  const mount = (props: Partial<ConsoleApplyButtonProps>) => act(() => root.render(<ConsoleApplyButton {...props} />));
  const applyButton = () => container.querySelector<HTMLButtonElement>("button.tbtn");

  it("누르면 onApply 를 한 번 부른다", () => {
    const onApply = vi.fn();
    mount({ onApply });
    act(() => applyButton()?.click());
    expect(onApply).toHaveBeenCalledTimes(1);
  });

  it("콜백이 없으면 비활성이라 눌러도 아무 일 없다", () => {
    mount({});
    expect(applyButton()?.disabled).toBe(true);
    act(() => applyButton()?.click());
    expect(container.querySelector("button.tbtn")).not.toBeNull();
  });

  it("진행 문구 버튼을 누르면 승인 카드 콜백만 부르고 반영은 부르지 않는다", () => {
    const onApply = vi.fn();
    const onApplyProgressClick = vi.fn();
    mount({ onApply, applyProgress: "승인 카드를 기다리는 중", onApplyProgressClick });
    const link = container.querySelector<HTMLButtonElement>("button.beat-grid-apply-progress-link");
    expect(link).not.toBeNull();
    act(() => link?.click());
    expect(onApplyProgressClick).toHaveBeenCalledTimes(1);
    expect(onApply).not.toHaveBeenCalled();
  });
});

// 클래스 이름만 있고 스타일이 없으면 상단 바 밖에서는 버튼이 맨 글자로 보이고 강조도 안 보인다 —
// 다른 어떤 검사에도 안 걸리므로 여기서 못박는다. jsdom 에서는 전역 `URL` 이 jsdom 것이라 문자열 경로를 쓴다.
describe("큐 편집 칸 스타일", () => {
  const css = readFileSync(resolve(dirname(fileURLToPath(import.meta.url)), "../../styles.css"), "utf-8");
  const escapeRegExp = (text: string) => text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const ruleBody = (selector: string): string => {
    const found = css.match(new RegExp(`(?:^|\\})\\s*${escapeRegExp(selector)}\\s*\\{([^}]*)\\}`, "m"));
    if (!found) throw new Error(`rule not found: ${selector}`);
    return found[1].replace(/\s+/g, " ").trim();
  };

  it("강조는 상단 바 시절과 같은 테두리·그림자다", () => {
    const panel = ruleBody(".beat-grid-cue-panel .tbtn.is-next");
    expect(panel).toMatch(/box-shadow:\s*0 0 0 \d+px #[0-9a-f]+/i);
    expect(panel).toBe(ruleBody(".beat-grid-topbar .tbtn.is-next"));
  });

  it("버튼·배지 모양은 상단 바와 같다 — 이 줄 안으로만 한정해 편집 칸의 다른 버튼에 번지지 않는다", () => {
    expect(ruleBody(".beat-grid-console-apply .tbtn")).toBe(ruleBody(".beat-grid-topbar .tbtn"));
    expect(ruleBody(".beat-grid-console-apply .badge")).toBe(ruleBody(".beat-grid-topbar .badge"));
    expect(ruleBody(".beat-grid-console-apply .tbtn:disabled")).toBe(ruleBody(".beat-grid-topbar .tbtn:disabled"));
  });

  it("「—」 배지는 상단 바처럼 폭으로 숨기지 않는다 — 이 칸에는 한 줄 제약이 없다", () => {
    expect(css).not.toMatch(/\.beat-grid-console-apply[^{]*\.badge-dash\s*\{/);
  });
});
