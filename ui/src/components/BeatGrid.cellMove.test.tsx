// @vitest-environment jsdom
// 칸 막대 가로 끌기로 같은 줄 안에서 옮기기 — 실제 `<BeatGrid>` 를 그려, 포인터로 끌었을 때 서버로 올리는 옮기기 목록과
// 끌고 난 뒤 따라오는 클릭이 고른 칸을 건드리지 않는지 잰다(카드 WT-cell-edit-live, SPEC-LDRHYTHM-001).
// 끌기 상태 전이와 어느 칸이 옮겨지는지는 `beatgrid/cellMove.test.ts` 가 순수 함수로 따로 본다.
//
// jsdom 은 레인 폭을 못 재서 마디 폭이 42px 로 떨어지고(첫 시험이 그 가정을 칸 폭으로 확인한다), 포인터 캡처가 없어
// `setPointerCapture` 를 흉내 낸다. 놓은 뒤 브라우저가 보내는 클릭은 jsdom 이 만들어 주지 않으므로 시험이 직접 보낸다.
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { BeatGridCue, BeatGridTrack, BeatGridView } from "../protocol";
import { BeatGrid, type BeatGridProps } from "./BeatGrid";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

function cue(bar: number): BeatGridCue {
  return {
    bar,
    label: `칸${bar}`,
    brightness: { mode: "value", value_percent: 100, preset_no: null },
    position_preset_no: null,
    color_preset_no: null,
    effect_preset_no: null,
    effect_kind: null,
    entry: { fade_bars: null, mib_mode: null },
    source_ref: null,
    app_movement: null,
    evidence: null,
  };
}

function track(name: string, bars: number[]): BeatGridTrack {
  return { group_no: null, group_no_confirmed: false, group_name: name, layer_role: null, cues: bars.map(cue) };
}

function gridOf(tracks: BeatGridTrack[]): BeatGridView {
  return {
    song_title: "LOVE ATTACK",
    bar_range: { start: 0, end: 12 },
    tracks,
    scene_memos: [],
    probe_results: {},
    source: "empty",
    note: null,
    console_audio_offset_seconds: 0,
  };
}

/** 두 줄(AAA·BBB) 모두 1·5·9 마디에서 시작하는 칸 셋 — 칸 막대는 AAA 셋, BBB 셋 순서로 여섯 개다. */
const TWO_ROWS = () => [track("AAA", [1, 5, 9]), track("BBB", [1, 5, 9])];
/** 두 줄 모두 1·2·9 마디 — 붙은 두 칸(1·2)을 같이 골라 옮기는 시험용. */
const ADJACENT = () => [track("AAA", [1, 2, 9]), track("BBB", [1, 2, 9])];

let container: HTMLElement;
let root: Root;
let setPointerCapture: ReturnType<typeof vi.fn>;

beforeEach(() => {
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
  setPointerCapture = vi.fn();
  Object.defineProperty(HTMLElement.prototype, "setPointerCapture", { configurable: true, value: setPointerCapture });
});

afterEach(() => {
  act(() => root.unmount());
  container.remove();
  delete (HTMLElement.prototype as unknown as Record<string, unknown>).setPointerCapture;
});

function setup(tracks: BeatGridTrack[], props: Partial<BeatGridProps> = {}) {
  const onMoveCells = vi.fn();
  const onEditRequest = vi.fn();
  act(() =>
    root.render(<BeatGrid grid={gridOf(tracks)} onMoveCells={onMoveCells} onEditRequest={onEditRequest} {...props} />),
  );
  return { onMoveCells, onEditRequest };
}

const cueButtons = () => Array.from(container.querySelectorAll<HTMLButtonElement>("button.beat-grid-cue"));
/** 줄 번호(0부터)와 칸 번호(0부터)로 칸 막대를 가린다 — 줄마다 칸이 셋이다. */
function cellAt(row: number, col: number): HTMLButtonElement {
  const button = cueButtons()[row * 3 + col];
  if (!button) throw new Error(`cue button not found: ${row},${col}`);
  return button;
}
/** 편집 칸에 열린(보통 클릭으로 고른) 칸 막대의 DOM 순서 번호. 없으면 -1. */
const selectedIndex = () => cueButtons().findIndex((button) => button.classList.contains("is-selected"));
const multiCount = () => container.querySelectorAll("button.beat-grid-cue.is-multi").length;

type PointerType = "pointerdown" | "pointermove" | "pointerup" | "pointercancel";
function pointer(target: Element, type: PointerType, clientX: number, init: PointerEventInit = {}) {
  act(() => {
    target.dispatchEvent(new PointerEvent(type, { bubbles: true, pointerId: 1, button: 0, clientX, ...init }));
  });
}
const START_X = 100;
/** 칸 막대를 누르고 `dx` px 끌어 놓는다. 따라오는 클릭은 `click` 으로 따로 보낸다. */
function drag(target: Element, dx: number, init: PointerEventInit = {}) {
  pointer(target, "pointerdown", START_X, init);
  pointer(target, "pointermove", START_X + dx, init);
  pointer(target, "pointerup", START_X + dx, init);
}
function click(target: Element, keys: { shift?: boolean } = {}) {
  act(() => {
    target.dispatchEvent(new MouseEvent("click", { bubbles: true, shiftKey: !!keys.shift }));
  });
}

describe("칸 가로 끌기 — 올리는 옮기기 목록", () => {
  it("[보정] 이 DOM 에서 마디 한 칸은 42px 다 — 아래 끌기 거리의 근거", () => {
    setup(TWO_ROWS());
    // AAA 1마디 칸은 1~4마디(다음 칸이 5마디) = 네 마디 폭 - 2px.
    expect(cellAt(0, 0).style.width).toBe(`${4 * 42 - 2}px`);
  });

  it("5마디 칸을 오른쪽으로 두 마디(84px) 끌면 그 칸 하나를 7마디로 옮기는 목록을 정확히 한 번 올린다", () => {
    const { onMoveCells } = setup(TWO_ROWS());
    drag(cellAt(0, 1), 84);
    expect(onMoveCells).toHaveBeenCalledTimes(1);
    expect(onMoveCells).toHaveBeenCalledWith([{ op: "move", group_name: "AAA", bar: 5, to_bar: 7 }]);
  });

  it.each([
    [-84, 3],
    [30, 6], // 30px = 0.71마디 → 한 마디로 반올림
    [-30, 4],
    [126, 8],
  ])("%ipx 끌면 5마디 칸이 %i마디로 간다", (dx, toBar) => {
    const { onMoveCells } = setup(TWO_ROWS());
    drag(cellAt(1, 1), dx);
    expect(onMoveCells).toHaveBeenCalledTimes(1);
    expect(onMoveCells).toHaveBeenCalledWith([{ op: "move", group_name: "BBB", bar: 5, to_bar: toBar }]);
  });

  it("누른 자리가 아니라 움직인 거리로 옮긴다 — 시작 x 가 달라도 같은 목록이다", () => {
    const { onMoveCells } = setup(TWO_ROWS());
    const target = cellAt(0, 1);
    pointer(target, "pointerdown", 400);
    pointer(target, "pointermove", 484);
    pointer(target, "pointerup", 484);
    expect(onMoveCells).toHaveBeenCalledWith([{ op: "move", group_name: "AAA", bar: 5, to_bar: 7 }]);
  });

  it("움직임 이벤트 없이 놓는 좌표만으로도 끌기가 된다", () => {
    const { onMoveCells } = setup(TWO_ROWS());
    const target = cellAt(0, 1);
    pointer(target, "pointerdown", START_X);
    pointer(target, "pointerup", START_X + 84);
    expect(onMoveCells).toHaveBeenCalledWith([{ op: "move", group_name: "AAA", bar: 5, to_bar: 7 }]);
  });
});

describe("칸 가로 끌기 — 올리지 않는 경우", () => {
  it("2px 만 움직이면 끌기가 아니다 — 아무것도 올리지 않고 뒤따르는 클릭은 보통 클릭으로 칸을 고른다", () => {
    const { onMoveCells } = setup(TWO_ROWS());
    const target = cellAt(0, 1);
    drag(target, 2);
    click(target);
    expect(onMoveCells).not.toHaveBeenCalled();
    expect(selectedIndex()).toBe(1);
  });

  it("3px 를 넘겼지만 마디로는 0(15px = 0.36마디)이면 올리지 않고, 끈 것이라 뒤따르는 클릭도 칸을 고르지 않는다", () => {
    const { onMoveCells } = setup(TWO_ROWS());
    const target = cellAt(0, 1);
    drag(target, 15);
    click(target);
    expect(onMoveCells).not.toHaveBeenCalled();
    expect(selectedIndex()).toBe(-1);
  });

  it("1마디 미만으로 가는 끌기는 올리지 않는다 — 1마디 칸을 한 마디 앞으로, 5마디 칸을 다섯·여섯 마디 앞으로", () => {
    const { onMoveCells } = setup(TWO_ROWS());
    drag(cellAt(0, 0), -42); // 1 → 0
    drag(cellAt(0, 1), -210); // 5 → 0
    drag(cellAt(0, 1), -252); // 5 → -1
    expect(onMoveCells).not.toHaveBeenCalled();
  });

  it("1마디에 닿는 끌기는 된다 — 5마디 칸을 네 마디 앞으로", () => {
    const { onMoveCells } = setup(TWO_ROWS());
    drag(cellAt(0, 1), -168);
    expect(onMoveCells).toHaveBeenCalledWith([{ op: "move", group_name: "AAA", bar: 5, to_bar: 1 }]);
  });

  it("고른 칸 가운데 하나라도 1마디 미만이 되면 아무것도 올리지 않는다 — 일부만 옮기지 않고, 고르기도 그대로다", () => {
    const { onMoveCells } = setup(TWO_ROWS());
    click(cellAt(0, 0));
    click(cellAt(0, 1), { shift: true }); // AAA 1·5마디 고름
    expect(multiCount()).toBe(2);
    drag(cellAt(0, 1), -42); // 5 → 4 는 되지만 1 → 0 이 안 된다
    click(cellAt(0, 1));
    expect(onMoveCells).not.toHaveBeenCalled();
    expect(multiCount()).toBe(2);
  });

  it("앞박(0마디) 칸은 옮기지 않는다 — 서버는 마디 1 미만 항목이 하나라도 있으면 메시지를 통째로 거절한다", () => {
    const { onMoveCells } = setup([track("AAA", [0, 5, 9]), track("BBB", [0, 5, 9])]);
    drag(cellAt(0, 0), 84);
    expect(onMoveCells).not.toHaveBeenCalled();
  });

  it("오른쪽 단추로는 끌기를 시작하지 않는다", () => {
    const { onMoveCells } = setup(TWO_ROWS());
    drag(cellAt(0, 1), 84, { button: 2 });
    expect(onMoveCells).not.toHaveBeenCalled();
  });

  it("끄는 도중 포인터가 취소되면 아무것도 올리지 않는다", () => {
    const { onMoveCells } = setup(TWO_ROWS());
    const target = cellAt(0, 1);
    pointer(target, "pointerdown", START_X);
    pointer(target, "pointermove", START_X + 84);
    pointer(target, "pointercancel", START_X + 84);
    pointer(target, "pointerup", START_X + 84);
    expect(onMoveCells).not.toHaveBeenCalled();
  });

  it("빈 구간(첫 칸 앞 「꺼짐」)은 칸이 아니라 끌 수 없다", () => {
    const { onMoveCells } = setup([track("AAA", [5, 9])]);
    const gap = container.querySelector("span.beat-grid-cue-gap");
    expect(gap).not.toBeNull();
    drag(gap as Element, 84);
    expect(onMoveCells).not.toHaveBeenCalled();
  });
});

describe("고른 칸을 끌 때", () => {
  it("같은 줄에서 Shift 로 고른 두 칸 가운데 하나를 끌면 둘 다 같은 마디 수만큼 옮기고, 뒤따르는 클릭은 고르기를 건드리지 않는다", () => {
    const { onMoveCells } = setup(ADJACENT());
    click(cellAt(0, 0));
    click(cellAt(0, 1), { shift: true }); // AAA 1·2마디 고름
    expect(multiCount()).toBe(2);
    const dragged = cellAt(0, 1);
    drag(dragged, 84);
    expect(onMoveCells).toHaveBeenCalledTimes(1);
    expect(onMoveCells).toHaveBeenCalledWith([
      { op: "move", group_name: "AAA", bar: 1, to_bar: 3 },
      { op: "move", group_name: "AAA", bar: 2, to_bar: 4 },
    ]);
    // 끌고 난 뒤 브라우저가 보내는 클릭 — 보통 클릭으로 처리되면 고른 칸이 비워지고 이 칸 하나만 남는다.
    click(dragged);
    expect(multiCount()).toBe(2);
    expect(selectedIndex()).toBe(0);
  });

  it("다른 줄의 칸이 같이 골라져 있어도 끈 줄의 칸만 옮긴다", () => {
    const { onMoveCells } = setup(ADJACENT());
    click(cellAt(0, 0));
    click(cellAt(1, 1), { shift: true }); // AAA~BBB 줄 × 1~2마디 = 네 칸 고름
    expect(multiCount()).toBe(4);
    drag(cellAt(0, 1), 84);
    expect(onMoveCells).toHaveBeenCalledTimes(1);
    expect(onMoveCells).toHaveBeenCalledWith([
      { op: "move", group_name: "AAA", bar: 1, to_bar: 3 },
      { op: "move", group_name: "AAA", bar: 2, to_bar: 4 },
    ]);
  });

  it("끈 줄이 다르면 그 줄의 칸만 옮긴다 — 같은 고르기에서 BBB 칸을 끈다", () => {
    const { onMoveCells } = setup(ADJACENT());
    click(cellAt(0, 0));
    click(cellAt(1, 1), { shift: true });
    drag(cellAt(1, 0), 84);
    expect(onMoveCells).toHaveBeenCalledWith([
      { op: "move", group_name: "BBB", bar: 1, to_bar: 3 },
      { op: "move", group_name: "BBB", bar: 2, to_bar: 4 },
    ]);
  });

  it("끈 칸이 고른 칸에 없으면 그 칸 하나만 옮기고 고른 칸은 그대로다", () => {
    const { onMoveCells } = setup(ADJACENT());
    click(cellAt(0, 0));
    click(cellAt(0, 1), { shift: true }); // AAA 1·2마디 고름
    const outside = cellAt(0, 2); // AAA 9마디 — 고르지 않은 칸
    drag(outside, 84);
    click(outside);
    expect(onMoveCells).toHaveBeenCalledTimes(1);
    expect(onMoveCells).toHaveBeenLastCalledWith([{ op: "move", group_name: "AAA", bar: 9, to_bar: 11 }]);
    expect(multiCount()).toBe(2);
    // 다른 줄의 고르지 않은 칸도 마찬가지다.
    drag(cellAt(1, 0), 84);
    expect(onMoveCells).toHaveBeenLastCalledWith([{ op: "move", group_name: "BBB", bar: 1, to_bar: 3 }]);
  });
});

describe("onMoveCells 가 없으면", () => {
  it("끌어도 아무 일도 없다 — 던지지 않고, 포인터를 붙들지도 않고, 클릭은 예전처럼 칸을 고른다", () => {
    setup(TWO_ROWS(), { onMoveCells: undefined });
    const target = cellAt(0, 1);
    expect(() => {
      drag(target, 84);
      click(target);
    }).not.toThrow();
    expect(setPointerCapture).not.toHaveBeenCalled();
    expect(selectedIndex()).toBe(1);
  });
});

describe("포인터 캡처", () => {
  it("누르면 그 칸 막대가 포인터를 붙든다 — 끌다가 칸 밖으로 나가도 놓는 순간을 받는다", () => {
    setup(TWO_ROWS());
    const target = cellAt(0, 1);
    drag(target, 84);
    expect(setPointerCapture).toHaveBeenCalledTimes(1);
    expect(setPointerCapture).toHaveBeenCalledWith(1);
    expect(setPointerCapture.mock.contexts[0]).toBe(target);
  });

  it("setPointerCapture 가 없는 환경에서도 끌 수 있다", () => {
    delete (HTMLElement.prototype as unknown as Record<string, unknown>).setPointerCapture;
    const { onMoveCells } = setup(TWO_ROWS());
    expect(() => drag(cellAt(0, 1), 84)).not.toThrow();
    expect(onMoveCells).toHaveBeenCalledWith([{ op: "move", group_name: "AAA", bar: 5, to_bar: 7 }]);
  });
});

describe("이음매 끌기는 그대로다", () => {
  it("이음매(◆)를 끌면 예전처럼 전환 편집 요청이 나가고 칸 옮기기는 올라가지 않는다", () => {
    const { onMoveCells, onEditRequest } = setup(TWO_ROWS(), { timeSignature: "4/4" });
    const joint = container.querySelector<HTMLButtonElement>("button.beat-grid-joint");
    expect(joint).not.toBeNull();
    // 마디 42px, 한 마디 4박 → 한 박 10.5px. 두 박(21px) 오른쪽으로 끌면 트리거 박이 1 → 3.
    drag(joint as HTMLButtonElement, 21);
    expect(onEditRequest).toHaveBeenCalledTimes(1);
    expect(onEditRequest.mock.calls[0][0]).toMatchObject({
      bar: 5,
      target: "AAA",
      changes: { entry: { trigger_beat: 3 } },
    });
    expect(onMoveCells).not.toHaveBeenCalled();
  });
});
