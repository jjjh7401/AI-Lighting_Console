// PlanCueRequestGeneratorView — 훅 없는 순수 뷰 시험(jsdom 없음, 이
// 프로젝트의 CueMonitor.test.tsx와 같은 "함수를 직접 호출해 엘리먼트
// 트리를 훑는다" 패턴). 상태를 쥔 훅(usePlanCueRequestGenerator)은 여기서
// 직접 부르지 않는다(React 디스패처가 없어 훅 호출은 이 환경에서 던진다) —
// 뷰가 훅과 정확히 분리돼 있다는 사실 자체가 AC-034~044/052/053을 검증
// 가능하게 만드는 전제다.
import type { ReactElement } from "react";
import { describe, expect, it, vi } from "vitest";

import {
  applyTurnResult,
  isGroupLocked,
  PlanCueRequestGeneratorView,
  turnAccepted,
  type PlanCueRequestGeneratorViewModel,
  type StackEntry,
} from "./PlanCueRequestGenerator";
import { PresetPoolPopup } from "./PresetPoolPopup";
import type { SongTimelineReserveItem } from "../protocol";

function childArray(element: ReactElement): unknown[] {
  const children = element.props.children;
  if (children === undefined) return [];
  const list = Array.isArray(children) ? children : [children];
  return list.flat(Infinity).filter((child) => child !== null && child !== undefined && child !== false);
}

function findAllByType(root: ReactElement, type: unknown): ReactElement[] {
  const results: ReactElement[] = [];
  for (const child of childArray(root)) {
    const el = child as ReactElement;
    if (el?.type === type) results.push(el);
    if (el?.props) results.push(...findAllByType(el, type));
  }
  return results;
}

function findAllByClassIncludes(root: ReactElement, needle: string): ReactElement[] {
  const results: ReactElement[] = [];
  for (const child of childArray(root)) {
    const el = child as ReactElement;
    if (typeof el?.props?.className === "string" && el.props.className.includes(needle)) {
      results.push(el);
    }
    if (el?.props) results.push(...findAllByClassIncludes(el, needle));
  }
  return results;
}

function textOf(element: ReactElement | unknown): string {
  if (element === null || element === undefined || element === false) return "";
  if (typeof element === "string" || typeof element === "number") return String(element);
  const el = element as ReactElement;
  if (!el?.props) return "";
  return childArray(el).map(textOf).join("");
}

function baseViewModel(overrides: Partial<PlanCueRequestGeneratorViewModel> = {}): PlanCueRequestGeneratorViewModel {
  return {
    cueNumber: 3,
    statusLabel: "바뀐 항목 없음",
    groups: ["KEY", "BACK"],
    selectedGroups: [],
    isGroupLocked: () => false,
    onToggleGroup: vi.fn(),
    intensityInput: "",
    onIntensityInputChange: vi.fn(),
    onApplyIntensity: vi.fn(),
    beforeIntensityLabel: "70%",
    fadeInput: "",
    onFadeInputChange: vi.fn(),
    onApplyFade: vi.fn(),
    transValue: "SNAP",
    onApplyTrans: vi.fn(),
    positionLabel: "—",
    colorLabel: "—",
    colorButtonDisabled: true,
    dimLabel: "—",
    effectLabel: "—",
    onOpenPopup: vi.fn(),
    stack: [],
    onRemoveEntry: vi.fn(),
    removeDisabledId: null,
    freeText: "",
    onFreeTextChange: vi.fn(),
    onCancelSelection: vi.fn(),
    cancelDisabled: true,
    onSendAll: vi.fn(),
    sendDisabled: true,
    popup: null,
    onClosePopup: vi.fn(),
    onPopupRefresh: vi.fn(),
    onPopupSelect: vi.fn(),
    ...overrides,
  };
}

function stackEntry(overrides: Partial<StackEntry> = {}): StackEntry {
  return {
    id: "gen-1",
    change: { field: "intensity", groups: ["KEY", "BACK"], value: 95, before: "혼합" },
    warnings: [],
    state: "selected",
    ...overrides,
  };
}

describe("isGroupLocked — AC-037의 순수 판정 로직 (REQ-090)", () => {
  const reserve: SongTimelineReserveItem[] = [
    { name: "BLIND", kind: "group", released_q: 23, screen_position: 5 },
  ];

  it("locks before the release cue", () => {
    expect(isGroupLocked("BLIND", reserve, 10)).toBe(true);
  });

  it("unlocks at and after the release cue", () => {
    expect(isGroupLocked("BLIND", reserve, 23)).toBe(false);
    expect(isGroupLocked("BLIND", reserve, 30)).toBe(false);
  });

  it("never locks a non-reserve group", () => {
    expect(isGroupLocked("KEY", reserve, 1)).toBe(false);
  });

  it("does not lock when reserve data is absent (no fabricated lock)", () => {
    expect(isGroupLocked("BLIND", undefined, 1)).toBe(false);
  });
});

describe("turnAccepted / applyTurnResult — AC-044의 순수 판정 로직 (REQ-095)", () => {
  it("a depth increase is the only accept signal", () => {
    expect(turnAccepted(2, 3)).toBe(true);
    expect(turnAccepted(2, 2)).toBe(false);
    expect(turnAccepted(3, 2)).toBe(false);
  });

  it("marks the sent line applied on accept, leaving other lines untouched", () => {
    const stack = [stackEntry({ id: "a", state: "requested" }), stackEntry({ id: "b" })];
    const next = applyTurnResult(stack, "a", { accepted: true });
    expect(next.find((e) => e.id === "a")?.state).toBe("applied");
    expect(next.find((e) => e.id === "b")?.state).toBe("selected");
  });

  it("marks the sent line rejected with the server's reason on refusal", () => {
    const stack = [stackEntry({ id: "a", state: "requested" })];
    const next = applyTurnResult(stack, "a", { accepted: false, rejectionReason: "큐 3에는 BACK 그룹이 없습니다." });
    expect(next[0].state).toBe("rejected");
    expect(next[0].rejectionReason).toBe("큐 3에는 BACK 그룹이 없습니다.");
  });
});

describe("PlanCueRequestGeneratorView — AC-035 혼합 표시", () => {
  it("shows the mixed-value label when selected groups disagree", () => {
    const vm = baseViewModel({ selectedGroups: ["KEY", "BACK"], beforeIntensityLabel: "혼합" });
    const el = PlanCueRequestGeneratorView(vm);
    const before = findAllByClassIncludes(el, "plan-cue-generator-before")[0];
    expect(textOf(before)).toContain("혼합");
  });
});

describe("PlanCueRequestGeneratorView — AC-036 프리셋 이름 저장·표시", () => {
  it("shows the selected preset NAME, not a raw value, in the console-values panel", () => {
    const vm = baseViewModel({ positionLabel: "Sweep L", dimLabel: "1.18 Dim 90" });
    const el = PlanCueRequestGeneratorView(vm);
    const rows = findAllByClassIncludes(el, "plan-cue-generator-row");
    expect(rows.map(textOf).some((text) => text.includes("Sweep L"))).toBe(true);
    expect(rows.map(textOf).some((text) => text.includes("1.18 Dim 90"))).toBe(true);
  });
});

describe("PlanCueRequestGeneratorView — AC-037 BLIND 잠금", () => {
  it("renders a locked chip as disabled and does not fire onToggleGroup", () => {
    const onToggleGroup = vi.fn();
    const vm = baseViewModel({
      groups: ["KEY", "BLIND"],
      isGroupLocked: (g) => g === "BLIND",
      onToggleGroup,
    });
    const el = PlanCueRequestGeneratorView(vm);
    const chips = findAllByClassIncludes(el, "plan-cue-chip");
    const blindChip = chips.find((chip) => textOf(chip).includes("BLIND"));
    expect(blindChip?.props.disabled).toBe(true);
    // 잠긴 칩을 눌러도(핸들러가 호출돼도) 훅 쪽에서 무시한다 — 여기서는
    // disabled 인 chip 이 렌더됐다는 사실만 확인한다(disabled 버튼은 DOM에서
    // 클릭 이벤트 자체가 나가지 않는다).
    const keyChip = chips.find((chip) => textOf(chip).includes("KEY"));
    expect(keyChip?.props.disabled).toBe(false);
  });
});

describe("PlanCueRequestGeneratorView — AC-038 상태 라벨 + 항목별 경고 병기", () => {
  it("shows the 확인 대기 status label and attaches warnings to their own diff line", () => {
    const vm = baseViewModel({
      statusLabel: "바꾼 것 2 — 코파일럿 확인 대기",
      stack: [
        stackEntry({ id: "a", warnings: [] }),
        stackEntry({
          id: "b",
          change: { field: "palette_primary", groups: ["BACK"], value: "흰색", before: "—" },
          warnings: ["⚠ 흰색은(는) 리저브 대상이다 — 해제 큐(미해제) 이전"],
        }),
      ],
    });
    const el = PlanCueRequestGeneratorView(vm);
    const status = findAllByClassIncludes(el, "plan-cue-generator-status")[0];
    expect(textOf(status)).toBe("바꾼 것 2 — 코파일럿 확인 대기");
    const diffLines = findAllByClassIncludes(el, "plan-cue-generator-diff");
    expect(diffLines).toHaveLength(2);
    expect(textOf(diffLines[0])).not.toContain("⚠");
    expect(textOf(diffLines[1])).toContain("⚠ 흰색은(는) 리저브 대상이다");
  });

  it("keeps the 확인 대기 label even for a 'requested' (in-flight) line — never 반영됨 prematurely", () => {
    const vm = baseViewModel({
      statusLabel: "바꾼 것 1 — 코파일럿 확인 대기",
      stack: [stackEntry({ id: "a", state: "requested" })],
    });
    const el = PlanCueRequestGeneratorView(vm);
    const status = findAllByClassIncludes(el, "plan-cue-generator-status")[0];
    expect(textOf(status)).not.toContain("반영됨");
    expect(textOf(status)).toContain("확인 대기");
  });
});

describe("PlanCueRequestGeneratorView — AC-042 선택 취소는 onSend류를 부르지 않는다", () => {
  it("선택 취소 button calls only onCancelSelection, never onSendAll", () => {
    const onCancelSelection = vi.fn();
    const onSendAll = vi.fn();
    const vm = baseViewModel({
      stack: [stackEntry()],
      cancelDisabled: false,
      onCancelSelection,
      onSendAll,
    });
    const el = PlanCueRequestGeneratorView(vm);
    const buttons = findAllByType(el, "button");
    const cancelButton = buttons.find((b) => textOf(b) === "선택 취소");
    cancelButton?.props.onClick();
    expect(onCancelSelection).toHaveBeenCalledTimes(1);
    expect(onSendAll).not.toHaveBeenCalled();
  });
});

describe("PlanCueRequestGeneratorView — AC-043 라벨 문자열 충돌 금지", () => {
  it("never renders the exact string 되돌리기 anywhere in this component", () => {
    const vm = baseViewModel({ stack: [stackEntry()] });
    const el = PlanCueRequestGeneratorView(vm);
    const buttons = findAllByType(el, "button");
    expect(buttons.some((b) => textOf(b).includes("되돌리기"))).toBe(false);
    expect(buttons.some((b) => textOf(b) === "선택 취소")).toBe(true);
  });
});

describe("PlanCueRequestGeneratorView — AC-052 항목별 ✕는 그 줄만 지운다", () => {
  it("✕ on one diff line calls onRemoveEntry with only that line's id", () => {
    const onRemoveEntry = vi.fn();
    const vm = baseViewModel({
      stack: [stackEntry({ id: "a" }), stackEntry({ id: "b" }), stackEntry({ id: "c" }), stackEntry({ id: "d" })],
      onRemoveEntry,
    });
    const el = PlanCueRequestGeneratorView(vm);
    const removeButtons = findAllByClassIncludes(el, "plan-cue-generator-remove");
    expect(removeButtons).toHaveLength(4);
    removeButtons[1].props.onClick();
    expect(onRemoveEntry).toHaveBeenCalledTimes(1);
    expect(onRemoveEntry).toHaveBeenCalledWith("b");
  });

  it("disables ✕ only for the line currently in flight", () => {
    const vm = baseViewModel({
      stack: [stackEntry({ id: "a", state: "requested" }), stackEntry({ id: "b" })],
      removeDisabledId: "a",
    });
    const el = PlanCueRequestGeneratorView(vm);
    const removeButtons = findAllByClassIncludes(el, "plan-cue-generator-remove");
    expect(removeButtons[0].props.disabled).toBe(true);
    expect(removeButtons[1].props.disabled).toBe(false);
  });
});

describe("PlanCueRequestGeneratorView — AC-053 자유 입력", () => {
  it("renders the free-text input bound to the view model", () => {
    const onFreeTextChange = vi.fn();
    const vm = baseViewModel({ freeText: "그리고 반 박자 당겨줘", onFreeTextChange });
    const el = PlanCueRequestGeneratorView(vm);
    const inputs = findAllByType(el, "input").filter((input) => input.props.type === "text");
    expect(inputs).toHaveLength(1);
    expect(inputs[0].props.value).toBe("그리고 반 박자 당겨줘");
    inputs[0].props.onChange({ target: { value: "new text" } });
    expect(onFreeTextChange).toHaveBeenCalledWith("new text");
  });
});

describe("PlanCueRequestGeneratorView — AC-034 컴포넌트 존재 여부 스냅샷", () => {
  it("renders a recognisable, single generator root", () => {
    const el = PlanCueRequestGeneratorView(baseViewModel());
    expect(el.props["aria-label"]).toBe("PLAN CUE 수정요청 생성기");
    expect(el.props.className).toBe("plan-cue-generator");
  });
});

describe("PlanCueRequestGeneratorView — 반영 요청 버튼", () => {
  it("is disabled with an empty stack and enabled once a line is selected", () => {
    const empty = PlanCueRequestGeneratorView(baseViewModel({ sendDisabled: true }));
    const withOne = PlanCueRequestGeneratorView(baseViewModel({ stack: [stackEntry()], sendDisabled: false }));
    const submitOf = (root: ReactElement) =>
      findAllByType(root, "button").find((b) => textOf(b) === "코파일럿에게 반영 요청");
    expect(submitOf(empty)?.props.disabled).toBe(true);
    expect(submitOf(withOne)?.props.disabled).toBe(false);
  });
});

describe("PlanCueRequestGeneratorView — 프리셋 팝업 마운트(REQ-089 재사용)", () => {
  it("mounts PresetPoolPopup only while popup state is set, wired to onPopupSelect", () => {
    const withoutPopup = PlanCueRequestGeneratorView(baseViewModel({ popup: null }));
    expect(findAllByType(withoutPopup, PresetPoolPopup)).toHaveLength(0);

    const onPopupSelect = vi.fn();
    const withPopup = PlanCueRequestGeneratorView(
      baseViewModel({
        popup: {
          field: "movement",
          state: {
            phase: "ready",
            contents: { pool: { no: 2, name: "POS" }, presets: [{ no: 1, name: "Sweep L" }], truncated: false, total: 1 },
          },
        },
        onPopupSelect,
      }),
    );
    const mounted = findAllByType(withPopup, PresetPoolPopup);
    expect(mounted).toHaveLength(1);
    expect(mounted[0].props.onSelect).toBe(onPopupSelect);
  });
});
