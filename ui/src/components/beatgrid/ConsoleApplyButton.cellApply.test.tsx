// @vitest-environment jsdom
// 「⇪ 콘솔에 반영」 칸 단위 모드 시험(카드 WT-cell-apply) — 주 버튼은 바뀐 칸만 보내고, 뒤따르는 「전체 다시 반영」이
// 곡 전체를 보낸다. 예전 단일 버튼 동작은 `ConsoleApplyButton.test.tsx` 가 계속 잰다(`partial` 을 안 주면 그대로).
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  PARTIAL_NOTHING_CHANGED_HINT,
  PARTIAL_RECORD_WARNING,
  PARTIAL_WHOLE_NO_RECORD_NOTE,
  PARTIAL_WHOLE_RECORD_NOTE,
  partialApplyPlan,
  type PartialApplyPlan,
} from "./cellApply";
import {
  CONSOLE_APPLY_LABEL,
  CONSOLE_APPLY_WHOLE_LABEL,
  ConsoleApplyButton,
  type ConsoleApplyButtonProps,
} from "./ConsoleApplyButton";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const noop = () => {};
const READY: PartialApplyPlan = partialApplyPlan(
  [
    { group_name: "BACK", bar: 1 },
    { group_name: "FOH", bar: 3 },
  ],
  [],
  "snapshot",
);
const NO_RECORD: PartialApplyPlan = partialApplyPlan(null, [], null);
const NOTHING: PartialApplyPlan = partialApplyPlan([], [], "snapshot");
// 기록 기준(record) — 칸 기록은 없고 이 곡의 반영 기록만 있다: 안 고르면 곡 전체, 고르면 고른 칸을 모두 보낸다.
const RECORD_NOTHING_PICKED: PartialApplyPlan = partialApplyPlan(null, [], "record");
const RECORD_READY: PartialApplyPlan = partialApplyPlan(
  null,
  [
    { group_name: "BACK", bar: 1 },
    { group_name: "FOH", bar: 3 },
    { group_name: "SIDE", bar: 5 },
  ],
  "record",
);

function renderMarkup(props: Partial<ConsoleApplyButtonProps> = {}) {
  return renderToStaticMarkup(<ConsoleApplyButton {...props} />);
}

describe("글자와 구성", () => {
  it("전체 다시 반영은 새 이름이고, 주 버튼 글자는 그대로 「⇪ 콘솔에 반영」이다", () => {
    expect(CONSOLE_APPLY_LABEL).toBe("⇪ 콘솔에 반영");
    expect(CONSOLE_APPLY_WHOLE_LABEL).toBe("전체 다시 반영");
    const html = renderMarkup({ onApply: noop, partial: { plan: READY, onApplyCells: noop } });
    expect(html).toContain(">⇪ 콘솔에 반영</button>");
    expect(html).toContain(">전체 다시 반영</button>");
    // 주 버튼 다음에 보조 버튼이 온다.
    expect(html.indexOf("⇪ 콘솔에 반영")).toBeLessThan(html.indexOf("전체 다시 반영"));
  });

  it("칸 단위 모드가 아니면 보조 버튼도 안내 줄도 없다 — 예전 단일 버튼 그대로", () => {
    const html = renderMarkup({ onApply: noop });
    expect(html).not.toContain("전체 다시 반영");
    expect(html).not.toContain("beat-grid-apply-scope");
    expect(html).not.toContain("beat-grid-apply-whole");
  });

  it("보조 버튼은 눈에 덜 띄는 모양을 위한 클래스를 가진다", () => {
    const html = renderMarkup({ onApply: noop, partial: { plan: READY, onApplyCells: noop } });
    expect(html).toContain('class="tbtn beat-grid-apply-whole"');
  });

  it("바뀐 칸을 보낼 수 있으면 주 버튼 title 과 안내 줄이 무엇을 보내는지 말한다", () => {
    const html = renderMarkup({ onApply: noop, partial: { plan: READY, onApplyCells: noop } });
    expect(html).toContain('title="⇪ 콘솔에 반영 — 바뀐 2칸만 보내요"');
    expect(html).toContain('<small class="beat-grid-apply-scope">바뀐 2칸만 보내요</small>');
    expect(html).not.toMatch(/class="tbtn" title="[^"]*" disabled/);
  });

  it("대기 수 배지는 주 버튼에 그대로 붙는다", () => {
    const html = renderMarkup({ onApply: noop, pendingApplyCount: 5, partial: { plan: READY, onApplyCells: noop } });
    expect(html).toContain('<span class="badge">5</span>');
  });

  it("진행 문구는 두 버튼 뒤에 따라붙는다", () => {
    const html = renderMarkup({
      onApply: noop,
      applyProgress: "콘솔을 읽는 중 · 3초",
      partial: { plan: READY, onApplyCells: noop },
    });
    expect(html.indexOf("전체 다시 반영")).toBeLessThan(html.indexOf("beat-grid-apply-progress"));
    expect(html).toContain("콘솔을 읽는 중 · 3초");
  });
});

// 2026-10-20 헤드리스 E2E 실측: 첫 반영에서 주 버튼이 「고른 칸을 먼저 골라 주세요」로 꺼져 있었고 「전체 다시 반영」만
// 됐다. 바뀐 칸을 가려낼 기준이 없으면 주 버튼이 곡 전체를 보낸다(「전체 다시 반영」과 같은 콜백).
describe("바뀐 칸을 가려낼 기준이 없을 때 — 곡 전체", () => {
  it("반영 기록이 없으면 주 버튼은 켜져 있고 title 과 안내 줄이 곡 전체를 보낸다고 말한다", () => {
    const html = renderMarkup({ onApply: noop, partial: { plan: NO_RECORD, onApplyCells: noop } });
    expect(html).toContain(`title="⇪ 콘솔에 반영 — ${PARTIAL_WHOLE_NO_RECORD_NOTE}">`);
    expect(html).toContain(`<small class="beat-grid-apply-scope">${PARTIAL_WHOLE_NO_RECORD_NOTE}</small>`);
    expect(html).not.toMatch(/class="tbtn" title="[^"]*" disabled/);
    expect(html).toMatch(/class="tbtn beat-grid-apply-whole" title="[^"]*">전체 다시 반영/);
  });

  it("기록 기준에서 고른 칸이 없으면 주 버튼은 켜져 있고 곡 전체를 보낸다고 말한다", () => {
    const html = renderMarkup({ onApply: noop, partial: { plan: RECORD_NOTHING_PICKED, onApplyCells: noop } });
    expect(html).toContain(`title="⇪ 콘솔에 반영 — ${PARTIAL_WHOLE_RECORD_NOTE}">`);
    expect(html).toContain(`<small class="beat-grid-apply-scope">${PARTIAL_WHOLE_RECORD_NOTE}</small>`);
    expect(html).not.toMatch(/class="tbtn" title="[^"]*" disabled/);
  });

  it("전체 반영 콜백이 없으면 주 버튼도 꺼지고 아직 배선 안 됨을 말한다", () => {
    const html = renderMarkup({ partial: { plan: NO_RECORD, onApplyCells: noop } });
    expect(html).toMatch(/class="tbtn" title="⇪ 콘솔에 반영 — 아직 배선 안 됨[^"]*" disabled/);
  });
});

describe("막힐 때", () => {
  it("바뀐 칸이 없으면 주 버튼은 꺼지고 「바뀐 칸이 없어요」", () => {
    const html = renderMarkup({ onApply: noop, partial: { plan: NOTHING, onApplyCells: noop } });
    expect(html).toContain(`title="${PARTIAL_NOTHING_CHANGED_HINT}" disabled`);
  });

  it("기록 기준에서 칸을 골랐으면 주 버튼은 켜져 있고, title 과 안내 줄이 기록 기준·지운 값 주의를 말한다", () => {
    const html = renderMarkup({ onApply: noop, partial: { plan: RECORD_READY, onApplyCells: noop } });
    const note = `고른 3칸을 보내요 (기록 기준) · ${PARTIAL_RECORD_WARNING}`;
    expect(html).toContain(`title="⇪ 콘솔에 반영 — ${note}"`);
    expect(html).toContain(`<small class="beat-grid-apply-scope">${note}</small>`);
    expect(html).not.toMatch(/class="tbtn" title="[^"]*" disabled/);
  });

  it("전체 반영 콜백이 없으면 보조 버튼은 꺼지고 아직 배선 안 됨을 title 로 말한다", () => {
    const html = renderMarkup({ partial: { plan: READY, onApplyCells: noop } });
    expect(html).toMatch(/title="전체 다시 반영 — 곡 전체를 콘솔에 다시 반영해요 — 아직 배선 안 됨[^"]*" disabled/);
  });
});

describe("강조 클래스(is-next)", () => {
  it("칸 단위 모드에서는 흐름의 「반영」이 곡 전체 반영이라 보조 버튼이 받는다", () => {
    const html = renderMarkup({ onApply: noop, isNext: true, partial: { plan: NO_RECORD, onApplyCells: noop } });
    expect(html).toContain('class="tbtn beat-grid-apply-whole is-next"');
    expect(html).not.toContain('class="tbtn is-next"');
  });

  it("강조가 아니면 둘 다 평범하다", () => {
    const html = renderMarkup({ onApply: noop, partial: { plan: READY, onApplyCells: noop } });
    expect(html).not.toContain("is-next");
  });

  it("칸 단위 모드가 아니면 주 버튼이 받는다 — 예전 그대로", () => {
    expect(renderMarkup({ onApply: noop, isNext: true })).toContain('class="tbtn is-next"');
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
  const buttonWith = (text: string) => {
    const found = Array.from(container.querySelectorAll("button")).find((button) => (button.textContent ?? "").includes(text));
    if (!found) throw new Error(`button not found: ${text}`);
    return found as HTMLButtonElement;
  };

  it("주 버튼은 판정한 칸 목록으로 칸 단위 콜백을 한 번 부르고, 전체 반영은 부르지 않는다", () => {
    const onApply = vi.fn();
    const onApplyCells = vi.fn();
    mount({ onApply, partial: { plan: READY, onApplyCells } });
    act(() => buttonWith("⇪").click());
    expect(onApplyCells).toHaveBeenCalledTimes(1);
    expect(onApplyCells).toHaveBeenCalledWith([
      ["BACK", 1],
      ["FOH", 3],
    ]);
    expect(onApply).not.toHaveBeenCalled();
  });

  it("전체 다시 반영은 인자 없이 전체 반영 콜백만 한 번 부른다", () => {
    const onApply = vi.fn();
    const onApplyCells = vi.fn();
    mount({ onApply, partial: { plan: READY, onApplyCells } });
    act(() => buttonWith("전체 다시 반영").click());
    expect(onApply).toHaveBeenCalledTimes(1);
    expect(onApply).toHaveBeenCalledWith();
    expect(onApplyCells).not.toHaveBeenCalled();
  });

  it("막힌 주 버튼은 눌러도 아무것도 안 보낸다 — 빈 칸 목록이 전체 반영으로 새지 않는다", () => {
    const onApply = vi.fn();
    const onApplyCells = vi.fn();
    mount({ onApply, partial: { plan: NOTHING, onApplyCells } });
    expect(buttonWith("⇪").disabled).toBe(true);
    act(() => buttonWith("⇪").click());
    expect(onApplyCells).not.toHaveBeenCalled();
    expect(onApply).not.toHaveBeenCalled();
  });

  it("반영 기록이 없을 때 주 버튼은 인자 없이 전체 반영 콜백을 한 번 부른다 — 칸 단위 콜백은 안 부른다", () => {
    const onApply = vi.fn();
    const onApplyCells = vi.fn();
    mount({ onApply, partial: { plan: NO_RECORD, onApplyCells } });
    expect(buttonWith("⇪").disabled).toBe(false);
    act(() => buttonWith("⇪").click());
    expect(onApply).toHaveBeenCalledTimes(1);
    expect(onApply).toHaveBeenCalledWith();
    expect(onApplyCells).not.toHaveBeenCalled();
  });

  it("기록 기준에서 주 버튼은 고른 칸 모두를 칸 단위 콜백으로 한 번 보낸다", () => {
    const onApply = vi.fn();
    const onApplyCells = vi.fn();
    mount({ onApply, partial: { plan: RECORD_READY, onApplyCells } });
    act(() => buttonWith("⇪").click());
    expect(onApplyCells).toHaveBeenCalledTimes(1);
    expect(onApplyCells).toHaveBeenCalledWith([
      ["BACK", 1],
      ["FOH", 3],
      ["SIDE", 5],
    ]);
    expect(onApply).not.toHaveBeenCalled();
  });

  it("기록 기준에서 고른 칸이 없을 때 주 버튼은 곡 전체를 보낸다 — 전체 반영 콜백 한 번", () => {
    const onApply = vi.fn();
    const onApplyCells = vi.fn();
    mount({ onApply, partial: { plan: RECORD_NOTHING_PICKED, onApplyCells } });
    expect(buttonWith("⇪").disabled).toBe(false);
    act(() => buttonWith("⇪").click());
    expect(onApply).toHaveBeenCalledTimes(1);
    expect(onApplyCells).not.toHaveBeenCalled();
  });

  it("기록이 없을 때 전체 다시 반영은 눌린다", () => {
    const onApply = vi.fn();
    mount({ onApply, partial: { plan: NO_RECORD, onApplyCells: vi.fn() } });
    expect(buttonWith("전체 다시 반영").disabled).toBe(false);
    act(() => buttonWith("전체 다시 반영").click());
    expect(onApply).toHaveBeenCalledTimes(1);
  });
});

// 새 클래스가 스타일 없이 맨 글자로 보이지 않게 — 다른 어떤 검사에도 안 걸리므로 여기서 못박는다.
describe("스타일", () => {
  const css = readFileSync(resolve(dirname(fileURLToPath(import.meta.url)), "cellSelection.css"), "utf-8");
  const escapeRegExp = (text: string) => text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const ruleBody = (selector: string): string => {
    const found = css.match(new RegExp(`(?:^|\\})\\s*${escapeRegExp(selector)}\\s*\\{([^}]*)\\}`, "m"));
    if (!found) throw new Error(`rule not found: ${selector}`);
    return found[1].replace(/\s+/g, " ").trim();
  };

  it("보조 버튼은 주 버튼보다 눈에 덜 띈다 — 바탕이 없고 글자가 흐리고 작다", () => {
    const body = ruleBody(".beat-grid-console-apply .tbtn.beat-grid-apply-whole");
    expect(body).toMatch(/background:\s*transparent/);
    expect(body).toMatch(/color:\s*var\(--muted\)/);
    expect(body).toMatch(/font-size:\s*1[01](\.\d+)?px/);
  });

  it("강조(is-next) 중인 보조 버튼의 테두리 색은 덮지 않는다 — 강조 테두리가 이긴다", () => {
    expect(css).toMatch(/\.beat-grid-console-apply \.tbtn\.beat-grid-apply-whole:not\(\.is-next\)\s*\{[^}]*border-color/);
    expect(ruleBody(".beat-grid-console-apply .tbtn.beat-grid-apply-whole")).not.toMatch(/border-color/);
  });

  it("안내 줄은 버튼 아래로 줄을 바꿔 한 줄을 다 쓴다", () => {
    expect(ruleBody(".beat-grid-apply-scope")).toMatch(/flex:\s*1 0 100%/);
  });
});
