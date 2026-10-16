// @vitest-environment jsdom
// 상단 바 반영 흐름 띠 시험 — `flow` 를 넘길 때만 상단 바 **아래**에 띠가 생기고, 다음 단계가 「반영」일
// 때만 「⇪ 콘솔에 반영」에 강조 클래스(`is-next`)가 붙는다. 번호 쓰기 버튼은 눌러야 하므로 DOM 이 필요하다
// (`songAudioLinkRequest.test.tsx` 와 같은 방식 — jsdom + `act`).
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { BeatGridTopBar, type BeatGridTopBarProps } from "./BeatGridTopBar";
import { NO_FLOW_DONE, type FlowDone } from "./beatgrid/flowChain";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

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

function render(overrides: Partial<BeatGridTopBarProps> = {}) {
  act(() =>
    root.render(
      <BeatGridTopBar
        songTitle="LOVE ATTACK"
        versionLabel={null}
        bpm={112}
        currentBar={1}
        barRange={{ start: 0, end: 82 }}
        onBarChange={() => {}}
        onApply={() => {}}
        {...overrides}
      />,
    ),
  );
}

const done = (overrides: Partial<FlowDone> = {}): FlowDone => ({ ...NO_FLOW_DONE, ...overrides });

function strip(): HTMLElement | null {
  return container.querySelector<HTMLElement>(".beat-grid-flow-strip");
}

/** 띠 안 단계 글자 셋(앞 세 칸 — 그 뒤는 안내 문장). */
function stepTexts(): string[] {
  return Array.from(strip()?.querySelectorAll("span") ?? [])
    .slice(0, 3)
    .map((span) => span.textContent ?? "");
}

function applyButton(): HTMLButtonElement {
  const found = Array.from(container.querySelectorAll("button")).find((button) =>
    (button.textContent ?? "").includes("⇪"),
  );
  if (!found) throw new Error("apply button not found");
  return found;
}

function suggestionButton(): HTMLButtonElement | null {
  return strip()?.querySelector("button") ?? null;
}

describe("흐름 띠 — flow 를 넘길 때만 생긴다", () => {
  it("flow 가 없으면(생략·null) 띠도 강조 클래스도 없고, 마크업은 둘이 같다", () => {
    render();
    const omitted = container.innerHTML;
    expect(strip()).toBeNull();
    expect(container.querySelector(".is-next")).toBeNull();
    expect(container.children).toHaveLength(1);
    expect(container.firstElementChild?.tagName).toBe("HEADER");
    expect(applyButton().className).toBe("tbtn");

    render({ flow: null });
    expect(container.innerHTML).toBe(omitted);
  });

  it("flow 를 넘기면 상단 바 헤더 **바로 뒤** 별도 줄로 생기고, 헤더 안에는 들어가지 않는다", () => {
    render({ flow: { done: done(), timecodeSuggestion: null } });
    const header = container.querySelector("header.beat-grid-topbar");
    const el = strip();
    expect(header).not.toBeNull();
    expect(el).not.toBeNull();
    expect(header?.contains(el)).toBe(false);
    expect(header?.nextElementSibling).toBe(el);
    expect(el?.getAttribute("aria-label")).toBe("반영 흐름");
    expect(stepTexts()).toEqual(["1/3 프리셋 저장", "2/3 반영", "3/3 콘솔 재생"]);
  });

  it("띠를 더해도 헤더 안은 그대로다 — flow 없이 그린 헤더와 글자·구조가 같다", () => {
    const common = { timecodeNumber: null, onTimecodeSubmit: () => {} };
    render(common);
    const without = container.querySelector("header")?.outerHTML;
    render({ ...common, flow: { done: done({ preset: true }), timecodeSuggestion: 12 } });
    const withFlow = container.querySelector("header")?.outerHTML;
    // 다음 단계가 「반영」이라 반영 버튼에 강조 클래스만 더해진다 — 그 밖은 같다.
    expect(withFlow).toContain('class="tbtn is-next"');
    expect(withFlow?.replace('class="tbtn is-next"', 'class="tbtn"')).toBe(without);
  });
});

describe("흐름 띠 — 지금 단계와 끝난 단계", () => {
  it("끝난 단계에는 ✓ 가 붙고 지금 가야 할 단계 하나에만 aria-current=step 이 붙는다", () => {
    render({ flow: { done: done({ preset: true }), timecodeSuggestion: null } });
    expect(stepTexts()).toEqual(["✓ 1/3 프리셋 저장", "2/3 반영", "3/3 콘솔 재생"]);
    const current = strip()?.querySelectorAll('[aria-current="step"]');
    expect(current).toHaveLength(1);
    expect(current?.[0].textContent).toBe("2/3 반영");
  });

  it("아무것도 안 끝났으면 1/3 이 지금 단계다", () => {
    render({ flow: { done: done(), timecodeSuggestion: null } });
    expect(stepTexts()).toEqual(["1/3 프리셋 저장", "2/3 반영", "3/3 콘솔 재생"]);
    expect(strip()?.querySelector('[aria-current="step"]')?.textContent).toBe("1/3 프리셋 저장");
  });

  it("앞 두 단계가 끝났으면 3/3 이 지금 단계다", () => {
    render({ flow: { done: done({ preset: true, reflect: true }), timecodeSuggestion: null } });
    expect(stepTexts()).toEqual(["✓ 1/3 프리셋 저장", "✓ 2/3 반영", "3/3 콘솔 재생"]);
    expect(strip()?.querySelector('[aria-current="step"]')?.textContent).toBe("3/3 콘솔 재생");
  });

  it("셋 다 끝나면 지금 단계가 없다", () => {
    render({ flow: { done: done({ preset: true, reflect: true, console: true }), timecodeSuggestion: null } });
    expect(stepTexts()).toEqual(["✓ 1/3 프리셋 저장", "✓ 2/3 반영", "✓ 3/3 콘솔 재생"]);
    expect(strip()?.querySelector("[aria-current]")).toBeNull();
  });
});

describe("흐름 띠 — 다음 안내 한 줄", () => {
  it("다음이 반영이고 초안에 번호가 있으면 그 번호를 말한다", () => {
    render({ timecodeNumber: 20, flow: { done: done({ preset: true }), timecodeSuggestion: 12 } });
    expect(strip()?.textContent).toContain("다음: 타임코드 20 에 반영");
  });

  it("초안 번호가 없고 권유 번호만 있으면 권유 번호를 말한다", () => {
    render({ flow: { done: done({ preset: true }), timecodeSuggestion: 12 } });
    expect(strip()?.textContent).toContain("다음: 타임코드 12 에 반영");
  });

  it("둘 다 없으면 번호를 정하라고 말한다", () => {
    render({ flow: { done: done({ preset: true }), timecodeSuggestion: null } });
    expect(strip()?.textContent).toContain("다음: 타임코드 번호를 정한 뒤 반영");
  });

  it("다음이 반영이 아니면 안내 문장이 없다", () => {
    render({ flow: { done: done(), timecodeSuggestion: 12 } });
    expect(strip()?.textContent).not.toContain("다음:");
    render({ flow: { done: done({ preset: true, reflect: true }), timecodeSuggestion: 12 } });
    expect(strip()?.textContent).not.toContain("다음:");
  });
});

describe("흐름 띠 — 「N 번 쓰기」 버튼", () => {
  const ready = { done: done({ preset: true }), timecodeSuggestion: 12 };

  it("프리셋은 저장됐고 반영 전이며 초안 번호가 없고 권유 번호가 있을 때만 보이고, 누르면 그 번호를 올린다", () => {
    const onTimecodeSubmit = vi.fn();
    render({ timecodeNumber: null, onTimecodeSubmit, flow: ready });
    const button = suggestionButton();
    expect(button?.textContent).toBe("12 번 쓰기");
    expect(onTimecodeSubmit).not.toHaveBeenCalled();

    act(() => button?.click());
    expect(onTimecodeSubmit).toHaveBeenCalledTimes(1);
    expect(onTimecodeSubmit).toHaveBeenCalledWith(12);
  });

  it("초안에 번호가 이미 있으면 없다", () => {
    render({ timecodeNumber: 5, onTimecodeSubmit: () => {}, flow: ready });
    expect(suggestionButton()).toBeNull();
  });

  it("권유 번호가 없으면 없다", () => {
    render({ onTimecodeSubmit: () => {}, flow: { ...ready, timecodeSuggestion: null } });
    expect(suggestionButton()).toBeNull();
  });

  it("프리셋 저장 전이면 없다", () => {
    render({ onTimecodeSubmit: () => {}, flow: { ...ready, done: done() } });
    expect(suggestionButton()).toBeNull();
  });

  it("이미 반영했으면 없다", () => {
    render({ onTimecodeSubmit: () => {}, flow: { ...ready, done: done({ preset: true, reflect: true }) } });
    expect(suggestionButton()).toBeNull();
  });

  it("번호를 올릴 콜백이 없으면 없다", () => {
    render({ flow: ready });
    expect(suggestionButton()).toBeNull();
  });
});

describe("「⇪ 콘솔에 반영」 강조", () => {
  it("다음 단계가 반영일 때만 is-next 가 붙는다", () => {
    const cases: [Partial<FlowDone>, boolean][] = [
      [{}, false], // 다음 = 프리셋
      [{ preset: true }, true], // 다음 = 반영
      [{ preset: true, reflect: true }, false], // 다음 = 콘솔
      [{ preset: true, reflect: true, console: true }, false], // 다음 없음
      [{ reflect: true }, false], // 프리셋이 아직이라 다음 = 프리셋
    ];
    for (const [flags, expected] of cases) {
      render({ flow: { done: done(flags), timecodeSuggestion: null } });
      expect(applyButton().classList.contains("is-next"), JSON.stringify(flags)).toBe(expected);
    }
  });

  it("강조 클래스는 반영 버튼에만 붙는다", () => {
    render({ flow: { done: done({ preset: true }), timecodeSuggestion: null } });
    expect(container.querySelectorAll(".is-next")).toHaveLength(1);
    expect(container.querySelector(".is-next")).toBe(applyButton());
  });
});

// 클래스 이름만 있고 스타일이 없으면 강조가 눈에 안 보인다 — 다른 어떤 검사에도 안 걸리므로 여기서 못박는다.
describe("반영 흐름 스타일", () => {
  // jsdom 환경에서는 전역 `URL` 이 jsdom 것이라 `new URL(..., import.meta.url)` 을 `fileURLToPath` 에 못 넘긴다 —
  // 문자열 그대로 넘겨 이 파일 위치에서 경로를 푼다.
  const css = readFileSync(resolve(dirname(fileURLToPath(import.meta.url)), "../styles.css"), "utf-8");
  const escapeRegExp = (text: string) => text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const ruleBody = (selector: string): string => {
    const found = css.match(new RegExp(`(?:^|\\})\\s*${escapeRegExp(selector)}\\s*\\{([^}]*)\\}`, "m"));
    if (!found) throw new Error(`rule not found: ${selector}`);
    return found[1];
  };

  it("띠는 한 줄짜리 작은 흐린 글씨이고, 지금 단계만 굵게 강조색이다", () => {
    const strip = ruleBody(".beat-grid-flow-strip");
    expect(strip).toMatch(/font-size:\s*\d+px/);
    expect(strip).toMatch(/color:\s*var\(--muted\)/);
    expect(strip).toMatch(/white-space:\s*nowrap/);
    const current = ruleBody('.beat-grid-flow-strip [aria-current="step"]');
    expect(current).toMatch(/font-weight:\s*700/);
    // 「⇪ 반영」 강조 테두리와 같은 색(`.tbtn.pri`) — 새 테마 색을 만들지 않는다.
    expect(current).toContain(ruleBody(".beat-grid-topbar .tbtn.pri").match(/background:\s*(#[0-9a-f]+)/i)?.[1] ?? "?");
  });

  it("다음 단계 버튼에는 눈에 보이는 테두리 강조가 있다", () => {
    const next = ruleBody(".beat-grid-topbar .tbtn.is-next");
    expect(next).toMatch(/box-shadow:\s*0 0 0 \d+px #[0-9a-f]+/i);
  });
});
