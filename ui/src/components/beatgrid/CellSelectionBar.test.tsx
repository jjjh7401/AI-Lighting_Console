// @vitest-environment jsdom
// 고른 칸 일괄 바꾸기 줄 시험(카드 WT-cell-apply) — 마크업은 `renderToStaticMarkup`, 고르기·누르기는 jsdom + `act`.
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  BULK_GUIDE_HINT,
  BULK_NOTHING_CHOSEN_HINT,
  BULK_SCOPE_HINT,
  CellSelectionBar,
  bulkChoiceOf,
  type BulkChoice,
  type CellSelectionBarProps,
} from "./CellSelectionBar";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const DIMMER_OPTIONS = (
  <>
    <option value="" disabled>
      — 미정 —
    </option>
    <optgroup label="이 곡 프리셋">
      <option value="1.1">1.1 Full</option>
      <option value="1.2">1.2 Half</option>
    </optgroup>
    <optgroup label="디머 효과">
      <option value="1.60">1.60 Pulse</option>
    </optgroup>
  </>
);
const COLOR_OPTIONS = (
  <>
    <option value="" disabled>
      — 미정 —
    </option>
    <option value="4.2">4.2 Red</option>
    <option value="4.3">4.3 Blue</option>
  </>
);

function props(overrides: Partial<CellSelectionBarProps> = {}): CellSelectionBarProps {
  return {
    count: 3,
    onClear: () => {},
    dimmerOptions: DIMMER_OPTIONS,
    colorOptions: COLOR_OPTIONS,
    dimmerEffectNos: ["1.60"],
    valueChoices: [0, 25, 60, 100],
    onApply: () => {},
    ...overrides,
  };
}

describe("bulkChoiceOf — 초안 → 선택", () => {
  const effects = ["1.60"];
  const drafts = (dimmerNo = "", valueText = "", colorNo = "") => ({ dimmerNo, valueText, colorNo });

  it("아무것도 안 골랐으면 null 이다", () => {
    expect(bulkChoiceOf(drafts(), effects)).toBeNull();
  });

  it("밝기 값(%)은 숫자로 읽는다 — 0% 도 고른 값이다", () => {
    expect(bulkChoiceOf(drafts("", "60"), effects)).toEqual({ dimmer: { kind: "value", percent: 60 }, color: null });
    expect(bulkChoiceOf(drafts("", "0"), effects)).toEqual({ dimmer: { kind: "value", percent: 0 }, color: null });
  });

  it("디머 번호가 효과 목록에 있으면 효과, 아니면 프리셋이다", () => {
    expect(bulkChoiceOf(drafts("1.60"), effects)?.dimmer).toEqual({ kind: "effect", no: "1.60" });
    expect(bulkChoiceOf(drafts("1.1"), effects)?.dimmer).toEqual({ kind: "preset", no: "1.1" });
  });

  it("색만 골라도 선택이다", () => {
    expect(bulkChoiceOf(drafts("", "", "4.2"), effects)).toEqual({ dimmer: null, color: { no: "4.2" } });
  });

  it("디머와 색을 함께 고르면 한 선택에 같이 담는다", () => {
    expect(bulkChoiceOf(drafts("", "25", "4.3"), effects)).toEqual({
      dimmer: { kind: "value", percent: 25 },
      color: { no: "4.3" },
    });
  });

  it("숫자가 아닌 값은 고른 것으로 치지 않는다", () => {
    expect(bulkChoiceOf(drafts("", "abc"), effects)).toBeNull();
    expect(bulkChoiceOf(drafts("", "  "), effects)).toBeNull();
  });
});

describe("마크업", () => {
  it("「N칸 고름」과 「선택 해제」가 있다", () => {
    const html = renderToStaticMarkup(<CellSelectionBar {...props({ count: 6 })} />);
    expect(html).toContain("6칸 고름");
    expect(html).toContain("선택 해제");
  });

  it("디머 프리셋·밝기 값·색 프리셋 고르기와 「적용」이 있고, 한 칸 편집의 고르기와 이름이 겹치지 않는다", () => {
    const html = renderToStaticMarkup(<CellSelectionBar {...props()} />);
    expect(html).toContain('aria-label="일괄 디머 프리셋"');
    expect(html).toContain('aria-label="일괄 밝기 값(%)"');
    expect(html).toContain('aria-label="일괄 색 프리셋"');
    expect(html).toContain(">적용</button>");
    // 한 칸 편집의 고르기 이름과 같으면 안 된다 — 그쪽 시험이 첫 번째 고르기를 이름으로 찾는다.
    expect(html).not.toContain('aria-label="밝기 값(%)"');
    expect(html).not.toContain('aria-label="색 프리셋"');
  });

  it("받은 고르기 목록을 그대로 쓰고, 값 고르기에는 선택지가 퍼센트로 나온다", () => {
    const html = renderToStaticMarkup(<CellSelectionBar {...props()} />);
    expect(html).toContain('<optgroup label="디머 효과"><option value="1.60">1.60 Pulse</option></optgroup>');
    expect(html).toContain('<option value="4.2">4.2 Red</option>');
    expect(html).toContain('<option value="60">60%</option>');
    expect(html).not.toContain("새 프리셋 만들기");
  });

  it("처음에는 아무것도 안 골랐으니 「적용」이 꺼져 있고 이유를 title 로 말한다", () => {
    const html = renderToStaticMarkup(<CellSelectionBar {...props()} />);
    expect(html).toMatch(/disabled="" title="디머나 색을 먼저 고르세요">적용<\/button>/);
    expect(BULK_NOTHING_CHOSEN_HINT).toBe("디머나 색을 먼저 고르세요");
  });

  it("고른 칸만 콘솔에 보내는 길을 한 줄로 안내한다 — 칸 고르기 → 디머·색 바꾸기 → 「⇪ 콘솔에 반영」", () => {
    const html = renderToStaticMarkup(<CellSelectionBar {...props()} />);
    expect(BULK_GUIDE_HINT).toBe("칸을 고르고 디머·색을 바꾼 뒤 「⇪ 콘솔에 반영」을 누르면 고른 칸만 콘솔에 보냅니다.");
    expect(html).toContain(`<p class="beat-grid-cell-bar-hint">${BULK_GUIDE_HINT}</p>`);
    // 안내는 한 줄이다 — 같은 문장이 되풀이되지 않는다.
    expect(html.split(BULK_GUIDE_HINT).length - 1).toBe(1);
  });

  it("프리셋 번호를 바꾼 칸은 전체 반영이 필요하다는 옛 안내는 없다 — 프리셋 번호도 칸 단위 반영이 보낸다", () => {
    const html = renderToStaticMarkup(<CellSelectionBar {...props()} />);
    expect(html).not.toContain("프리셋 번호를 바꾼 칸");
    expect(html).not.toContain("거절해요");
    // 「전체 다시 반영」 말은 이 줄에 나오지 않는다 — 안내가 가리키는 길은 「⇪ 콘솔에 반영」뿐이다.
    expect(html).not.toContain("전체 다시 반영");
  });

  it("이 줄의 적용과 아래 한 칸 편집의 적용이 다르다는 안내가 있다", () => {
    const html = renderToStaticMarkup(<CellSelectionBar {...props()} />);
    expect(html).toContain(BULK_SCOPE_HINT);
    expect(BULK_SCOPE_HINT).toContain("고른 칸 전부");
    expect(BULK_SCOPE_HINT).toContain("한 칸에만");
  });

  it("목록 상태·뺀 칸·거절 이유는 있을 때만 보인다", () => {
    const quiet = renderToStaticMarkup(<CellSelectionBar {...props()} />);
    expect(quiet).not.toContain('role="status"');
    const loud = renderToStaticMarkup(
      <CellSelectionBar
        {...props({
          poolNote: "디머: 프리셋 목록을 콘솔에서 받는 중입니다.",
          skippedNote: "0마디(앞박) 칸 1개는 칸 단위로 바꿀 수 없어요",
          replyNote: "박자 격자를 수정하지 않았습니다 — 거절",
        })}
      />,
    );
    expect(loud).toContain("디머: 프리셋 목록을 콘솔에서 받는 중입니다.");
    expect(loud).toContain("0마디(앞박) 칸 1개는 칸 단위로 바꿀 수 없어요");
    expect(loud).toContain('role="status">박자 격자를 수정하지 않았습니다 — 거절');
  });

  it("풀을 못 읽었으면 그 고르기만 꺼진다", () => {
    const html = renderToStaticMarkup(<CellSelectionBar {...props({ dimmerDisabled: true })} />);
    expect(html).toMatch(/aria-label="일괄 디머 프리셋"[^>]*disabled=""/);
    expect(html).not.toMatch(/aria-label="일괄 색 프리셋"[^>]*disabled=""/);
    expect(html).not.toMatch(/aria-label="일괄 밝기 값\(%\)"[^>]*disabled=""/);
  });
});

describe("고르기와 적용", () => {
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

  const mount = (overrides: Partial<CellSelectionBarProps> = {}) => act(() => root.render(<CellSelectionBar {...props(overrides)} />));
  const select = (label: string) => {
    const found = container.querySelector<HTMLSelectElement>(`select[aria-label="${label}"]`);
    if (!found) throw new Error(`select not found: ${label}`);
    return found;
  };
  const choose = (label: string, value: string) =>
    act(() => {
      const target = select(label);
      target.value = value;
      target.dispatchEvent(new Event("change", { bubbles: true }));
    });
  const applyButton = () => {
    const found = Array.from(container.querySelectorAll("button")).find((button) => button.textContent === "적용");
    if (!found) throw new Error("apply button not found");
    return found as HTMLButtonElement;
  };

  it("처음에는 세 고르기 모두 자리표시(— 미정 — / — 값 —)에 있다 — 첫 선택지가 골라진 것처럼 보이지 않는다", () => {
    mount();
    expect(select("일괄 디머 프리셋").value).toBe("");
    expect(select("일괄 밝기 값(%)").value).toBe("");
    expect(select("일괄 색 프리셋").value).toBe("");
    expect(select("일괄 디머 프리셋").selectedOptions[0]?.textContent).toBe("— 미정 —");
    expect(select("일괄 밝기 값(%)").selectedOptions[0]?.textContent).toBe("— 값 —");
  });

  it("밝기 값을 고르면 「적용」이 켜지고, 누르면 그 선택을 한 번 올린다", () => {
    const onApply = vi.fn<(choice: BulkChoice) => void>();
    mount({ onApply });
    expect(applyButton().disabled).toBe(true);
    choose("일괄 밝기 값(%)", "60");
    expect(applyButton().disabled).toBe(false);
    act(() => applyButton().click());
    expect(onApply).toHaveBeenCalledTimes(1);
    expect(onApply).toHaveBeenCalledWith({ dimmer: { kind: "value", percent: 60 }, color: null });
  });

  it("디머 프리셋과 디머 효과를 가려서 올린다", () => {
    const onApply = vi.fn<(choice: BulkChoice) => void>();
    mount({ onApply });
    choose("일괄 디머 프리셋", "1.2");
    act(() => applyButton().click());
    choose("일괄 디머 프리셋", "1.60");
    act(() => applyButton().click());
    expect(onApply.mock.calls.map(([choice]) => choice.dimmer)).toEqual([
      { kind: "preset", no: "1.2" },
      { kind: "effect", no: "1.60" },
    ]);
  });

  it("디머 프리셋을 고르면 밝기 값은 비워지고, 값을 고르면 프리셋이 비워진다 — 한 칸 편집과 같다", () => {
    mount();
    choose("일괄 밝기 값(%)", "25");
    choose("일괄 디머 프리셋", "1.1");
    expect(select("일괄 밝기 값(%)").value).toBe("");
    expect(select("일괄 디머 프리셋").value).toBe("1.1");
    choose("일괄 밝기 값(%)", "100");
    expect(select("일괄 디머 프리셋").value).toBe("");
    expect(select("일괄 밝기 값(%)").value).toBe("100");
  });

  it("색만 골라도 되고, 디머와 같이 골라도 한 번에 올린다", () => {
    const onApply = vi.fn<(choice: BulkChoice) => void>();
    mount({ onApply });
    choose("일괄 색 프리셋", "4.3");
    act(() => applyButton().click());
    choose("일괄 밝기 값(%)", "25");
    act(() => applyButton().click());
    expect(onApply.mock.calls.map(([choice]) => choice)).toEqual([
      { dimmer: null, color: { no: "4.3" } },
      { dimmer: { kind: "value", percent: 25 }, color: { no: "4.3" } },
    ]);
  });

  it("적용을 못 하는 이유(blockedReason)가 있으면 골라도 꺼져 있고 이유가 보인다", () => {
    const onApply = vi.fn();
    mount({ onApply, blockedReason: "한 번에 400칸까지만 바꿀 수 있어요 — 칸을 줄여 주세요" });
    choose("일괄 밝기 값(%)", "60");
    expect(applyButton().disabled).toBe(true);
    expect(applyButton().title).toBe("한 번에 400칸까지만 바꿀 수 있어요 — 칸을 줄여 주세요");
    expect(container.textContent).toContain("한 번에 400칸까지만 바꿀 수 있어요");
    act(() => applyButton().click());
    expect(onApply).not.toHaveBeenCalled();
  });

  it("「선택 해제」는 onClear 만 부른다", () => {
    const onClear = vi.fn();
    const onApply = vi.fn();
    mount({ onClear, onApply });
    const clear = Array.from(container.querySelectorAll("button")).find((button) => button.textContent === "선택 해제");
    act(() => (clear as HTMLButtonElement).click());
    expect(onClear).toHaveBeenCalledTimes(1);
    expect(onApply).not.toHaveBeenCalled();
  });

  it("고른 칸 수가 바뀌어도 골라 둔 값은 남는다", () => {
    mount({ count: 3 });
    choose("일괄 밝기 값(%)", "60");
    mount({ count: 5 });
    expect(container.textContent).toContain("5칸 고름");
    expect(select("일괄 밝기 값(%)").value).toBe("60");
  });
});
