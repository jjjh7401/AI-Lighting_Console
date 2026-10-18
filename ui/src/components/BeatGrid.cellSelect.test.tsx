// @vitest-environment jsdom
// 타임라인 칸 여러 개 고르기·일괄 바꾸기·칸 단위 반영 — 실제 `<BeatGrid>` 를 그려 클릭(보통·Shift·Ctrl/Cmd)이 고른 칸을
// 어떻게 바꾸는지, 일괄 바꾸기 줄이 서버에 한 메시지로 무엇을 올리는지, 「⇪ 콘솔에 반영」이 어느 칸을 보내는지, 결과 줄과
// 칸별 표시가 어떻게 보이는지 잰다(카드 WT-cell-apply). 순수 함수는 `beatgrid/cell*.test.ts` 가 따로 본다.
// DOM 이 필요해 `BeatGrid.stageSelect.test.tsx` 와 같은 방식(jsdom + `act`).
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type {
  BeatGridCue,
  BeatGridDrawerSection,
  BeatGridSendStatus,
  BeatGridTrack,
  BeatGridUnsentCell,
  BeatGridView,
} from "../protocol";
import {
  BEAT_GRID_EDIT_OK_SUMMARY,
  BEAT_GRID_REJECTION_SUMMARY,
  BeatGrid,
  buildBrightnessDimmerEffectChanges,
  buildBrightnessPresetChanges,
  buildBrightnessValueChanges,
  presetPickChanges,
  splitDimmerSection,
  type BeatGridFixturePoint,
  type BeatGridProps,
} from "./BeatGrid";
import { createConsoleFollowRelay } from "./beatgrid/consoleFollowRelay";

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

function gridOf(tracks: BeatGridTrack[], extra: Partial<BeatGridView> = {}): BeatGridView {
  return {
    song_title: "LOVE ATTACK",
    bar_range: { start: 0, end: 12 },
    tracks,
    scene_memos: [],
    probe_results: {},
    source: "empty",
    note: null,
    console_audio_offset_seconds: 0,
    ...extra,
  };
}

/** 줄마다 무대에 장비 한 대 — 무대 줄 고르기(#834)가 그대로인지 보려고 쓴다. */
function fixturesOf(names: string[]): BeatGridFixturePoint[] {
  return names.map((name, index) => ({
    fid: index + 1,
    name: `${name}-1`,
    x: index * 10,
    y: 0,
    z: 0,
    rotx: 0,
    roty: 0,
    rotz: 0,
    confirmedGroupName: name,
  }));
}

const DRAWER: BeatGridDrawerSection[] = [
  {
    pool_name: "Dimmer",
    title: "디머",
    pool_no: 1,
    unread: false,
    bands_confirmed: true,
    entries: [
      { preset_no: "1.1", name: "Full", usage_count: 1, used_by: [], is_effect_band: false },
      { preset_no: "1.2", name: "Half", usage_count: 0, used_by: [], is_effect_band: false },
      { preset_no: "1.60", name: "Pulse", usage_count: 0, used_by: [], is_effect_band: true },
    ],
  },
  {
    pool_name: "Color",
    title: "색",
    pool_no: 4,
    unread: false,
    bands_confirmed: true,
    entries: [
      { preset_no: "4.2", name: "Red", usage_count: 1, used_by: [], is_effect_band: false },
      { preset_no: "4.40", name: "Rainbow", usage_count: 0, used_by: [], is_effect_band: true },
    ],
  },
];
const COLOR_SECTION = DRAWER[1];

function status(overrides: Partial<BeatGridSendStatus> = {}): BeatGridSendStatus {
  return {
    pending_apply_count: 0,
    last_action: "apply",
    ok: true,
    reason: null,
    blocked_cells: [],
    approval_vs_sent: null,
    ...overrides,
  };
}

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

/** 세 줄(AAA·BBB·CCC) 모두 1·3·5 마디에서 시작하는 칸 셋 — 칸 막대는 줄 순서대로 아홉 개다. */
const THREE_BY_THREE = () => [track("AAA", [1, 3, 5]), track("BBB", [1, 3, 5]), track("CCC", [1, 3, 5])];
/** 무대 줄은 보는 마디(처음엔 0)에 칸이 있어야 눌린다 — 0마디에서 시작하는 세 줄. */
const FROM_BAR_ZERO = () => [track("AAA", [0, 2, 4]), track("BBB", [0, 2, 4]), track("CCC", [0, 2, 4])];

function setup(tracks: BeatGridTrack[], initial: Partial<BeatGridProps> = {}, gridExtra: Partial<BeatGridView> = {}) {
  const handlers = {
    onEditRequest: vi.fn(),
    onEditCellsRequest: vi.fn(),
    onApply: vi.fn(),
    onApplyCells: vi.fn(),
    onPreviewBar: vi.fn(),
  };
  let current: Partial<BeatGridProps> = { ...initial };
  let currentGrid = gridOf(tracks, gridExtra);
  const render = (patch: Partial<BeatGridProps> = {}, gridPatch: Partial<BeatGridView> = {}) => {
    current = { ...current, ...patch };
    currentGrid = { ...currentGrid, ...gridPatch };
    act(() =>
      root.render(
        <BeatGrid
          grid={currentGrid}
          fixtures={fixturesOf(tracks.map((t) => t.group_name))}
          drawerSections={DRAWER}
          {...handlers}
          {...current}
        />,
      ),
    );
  };
  render();
  return { handlers, render };
}

const cueButtons = () => Array.from(container.querySelectorAll<HTMLButtonElement>("button.beat-grid-cue"));
/** 줄 번호(0부터)와 칸 번호(0부터)로 칸 막대를 누른다. */
function clickCue(row: number, col: number, keys: { shift?: boolean; ctrl?: boolean; meta?: boolean } = {}, perRow = 3) {
  const button = cueButtons()[row * perRow + col];
  if (!button) throw new Error(`cue button not found: ${row},${col}`);
  act(() => {
    button.dispatchEvent(
      new MouseEvent("click", { bubbles: true, shiftKey: !!keys.shift, ctrlKey: !!keys.ctrl, metaKey: !!keys.meta }),
    );
  });
}
const multiButtons = () => Array.from(container.querySelectorAll<HTMLButtonElement>("button.beat-grid-cue.is-multi"));
const multiCount = () => multiButtons().length;
/** 여러 칸으로 고른 칸 막대의 DOM 순서 번호들. */
const multiIndexes = () =>
  cueButtons().flatMap((button, index) => (button.classList.contains("is-multi") ? [index] : []));
const bar = () => container.querySelector<HTMLElement>("section.beat-grid-cell-bar");
const panelHeading = () => container.querySelector("aside.beat-grid-cue-panel header span")?.textContent ?? "";

function stageClick(name: string, shift = false) {
  const hit = container.querySelector(`rect.beat-grid-stage-hit[data-track="${name}"]`);
  if (!hit) throw new Error(`stage zone not found: ${name}`);
  act(() => {
    hit.dispatchEvent(new MouseEvent("click", { bubbles: true, shiftKey: shift }));
  });
}
function outlined(): string[] {
  const hits = Array.from(container.querySelectorAll("rect.beat-grid-stage-hit"));
  return Array.from(container.querySelectorAll("rect.beat-grid-stage-selected")).map((rect) => {
    const same = hits.find((hit) => hit.getAttribute("x") === rect.getAttribute("x") && hit.getAttribute("y") === rect.getAttribute("y"));
    return same?.getAttribute("data-track") ?? "?";
  });
}

describe("칸 고르기 — 보통·Shift·Ctrl/Cmd 클릭", () => {
  it("보통 클릭은 예전 그대로 한 칸을 고르고 여러 칸 표시는 없다", () => {
    setup(THREE_BY_THREE());
    clickCue(1, 1);
    expect(container.querySelectorAll("button.beat-grid-cue.is-selected").length).toBe(1);
    expect(panelHeading()).toMatch(/^BBB · Cue 2/);
    expect(multiCount()).toBe(0);
    expect(bar()).toBeNull();
  });

  it("Shift+클릭은 기준 칸(보통 클릭한 칸)에서 누른 칸까지의 사각형을 고르고, 고른 수만큼 표시가 늘어난다", () => {
    setup(THREE_BY_THREE());
    clickCue(0, 0); // AAA 1마디
    clickCue(2, 1, { shift: true }); // CCC 3마디 → 줄 AAA~CCC × 마디 1~3
    expect(multiCount()).toBe(6);
    expect(container.querySelectorAll(".beat-grid-cue-multi-mark").length).toBe(6);
    expect(bar()?.textContent).toContain("6칸 고름");
    // 편집 칸은 기준 칸에 그대로 있다.
    expect(panelHeading()).toMatch(/^AAA · Cue 1/);
  });

  it("기준보다 위·왼쪽을 Shift+클릭해도 같은 사각형이다", () => {
    setup(THREE_BY_THREE());
    clickCue(2, 1); // CCC 3마디
    clickCue(0, 0, { shift: true }); // AAA 1마디
    expect(multiCount()).toBe(6);
  });

  it("다시 Shift+클릭하면 같은 기준에서 새 사각형으로 바뀐다(더해지지 않는다)", () => {
    setup(THREE_BY_THREE());
    clickCue(0, 0);
    clickCue(2, 2, { shift: true }); // 3줄 × 마디 1~5 = 9칸
    expect(multiCount()).toBe(9);
    clickCue(0, 1, { shift: true }); // AAA 3마디 → 한 줄 × 마디 1~3 = 2칸
    expect(multiCount()).toBe(2);
    expect(bar()?.textContent).toContain("2칸 고름");
  });

  it("고른 칸이 하나도 없는 상태의 Shift+클릭은 누른 칸 하나를 고른다", () => {
    setup(THREE_BY_THREE());
    clickCue(1, 2, { shift: true });
    expect(multiCount()).toBe(1);
    expect(bar()?.textContent).toContain("1칸 고름");
  });

  it("Ctrl+클릭은 칸 하나를 더하고, 같은 칸을 다시 누르면 뺀다 — Cmd 도 같다", () => {
    setup(THREE_BY_THREE());
    clickCue(0, 0); // AAA 1마디(칸 막대 0번)
    clickCue(1, 1, { ctrl: true }); // 처음이라 보통 클릭한 AAA 1마디가 먼저 들어가고 BBB 3마디(4번)가 더해진다
    expect(multiIndexes()).toEqual([0, 4]);
    clickCue(2, 2, { meta: true }); // CCC 5마디(8번)
    expect(multiIndexes()).toEqual([0, 4, 8]);
    clickCue(1, 1, { ctrl: true }); // BBB 3마디를 뺀다
    expect(multiIndexes()).toEqual([0, 8]);
  });

  it("Ctrl+클릭으로 모두 빼면 일괄 바꾸기 줄이 사라진다", () => {
    setup(THREE_BY_THREE());
    clickCue(1, 1, { ctrl: true });
    expect(bar()).not.toBeNull();
    clickCue(1, 1, { ctrl: true });
    expect(bar()).toBeNull();
    expect(multiCount()).toBe(0);
  });

  it("여러 칸 표시는 색에만 기대지 않는다 — ✔ 기호와 aria-pressed 가 같이 있다", () => {
    setup(THREE_BY_THREE());
    clickCue(0, 0);
    clickCue(0, 2, { shift: true });
    for (const button of multiButtons()) {
      expect(button.getAttribute("aria-pressed")).toBe("true");
      expect(button.querySelector(".beat-grid-cue-multi-mark")?.textContent).toBe("✔");
    }
    const others = cueButtons().filter((button) => !button.classList.contains("is-multi"));
    expect(others.length).toBe(6);
    for (const button of others) expect(button.hasAttribute("aria-pressed")).toBe(false);
  });

  it("보통 클릭은 고른 칸을 비우고 그 칸 하나만 남긴다", () => {
    setup(THREE_BY_THREE());
    clickCue(0, 0);
    clickCue(2, 2, { shift: true });
    expect(multiCount()).toBe(9);
    clickCue(1, 1);
    expect(multiCount()).toBe(0);
    expect(bar()).toBeNull();
    expect(panelHeading()).toMatch(/^BBB · Cue 2/);
  });

  it("「선택 해제」는 고른 칸만 비우고 편집 칸의 선택은 그대로 둔다", () => {
    setup(THREE_BY_THREE());
    clickCue(0, 0);
    clickCue(2, 2, { shift: true });
    const clear = Array.from(container.querySelectorAll("section.beat-grid-cell-bar button")).find(
      (button) => button.textContent === "선택 해제",
    );
    act(() => (clear as HTMLButtonElement).click());
    expect(multiCount()).toBe(0);
    expect(bar()).toBeNull();
    expect(panelHeading()).toMatch(/^AAA · Cue 1/);
  });

  it("접힌 폴더의 줄은 사각형에서 건너뛴다 — 안 보이는 칸을 몰래 고르지 않는다", () => {
    // 층 역할이 다른 세 줄 = 폴더 셋(앞빛·역광·옆빛). 역광(BBB) 폴더를 접고 위아래 폴더 사이를 Shift+클릭한다.
    const tracks = [track("AAA", [1, 3]), track("BBB", [1, 3]), track("CCC", [1, 3])];
    tracks[0].layer_role = "key";
    tracks[1].layer_role = "back";
    tracks[2].layer_role = "side";
    setup(tracks);
    const heads = () => Array.from(container.querySelectorAll<HTMLButtonElement>("button.beat-grid-folder-head"));
    const toggleFolderNamed = (label: string) => act(() => heads().find((head) => head.textContent?.includes(label))?.click());
    act(() => container.querySelector<HTMLButtonElement>("button.beat-grid-fold-all")?.click()); // 모두 접기
    toggleFolderNamed("앞빛");
    toggleFolderNamed("옆빛");
    expect(cueButtons().length).toBe(4); // AAA 둘 + CCC 둘 — 역광 폴더는 접혀 있다
    clickCue(0, 0, {}, 2); // AAA 1마디
    clickCue(1, 1, { shift: true }, 2); // CCC 3마디(보이는 줄은 AAA·CCC 둘뿐)
    expect(multiCount()).toBe(4);
    // 접힌 역광(BBB)을 펴 보면 그 줄의 칸은 고르지 않았다 — 칸 막대 순서는 AAA(0·1) BBB(2·3) CCC(4·5).
    toggleFolderNamed("역광");
    expect(cueButtons().length).toBe(6);
    expect(multiIndexes()).toEqual([0, 1, 4, 5]);
  });
});

describe("무대 줄 고르기(#834)는 그대로다", () => {
  it("무대의 보통·Shift 클릭은 여러 칸 표시를 만들지 않고, 줄 점선만 바꾼다", () => {
    setup(FROM_BAR_ZERO());
    stageClick("AAA");
    stageClick("BBB", true);
    expect(outlined()).toEqual(["AAA", "BBB"]);
    expect(multiCount()).toBe(0);
    expect(bar()).toBeNull();
  });

  it("타임라인에서 여러 칸을 고른 뒤 무대 줄을 누르면 고른 칸은 비워지고 그 줄만 남는다 — 선택이 하나뿐이다", () => {
    setup(FROM_BAR_ZERO());
    clickCue(0, 0);
    clickCue(2, 2, { shift: true });
    expect(multiCount()).toBe(9);
    stageClick("BBB");
    expect(multiCount()).toBe(0);
    expect(bar()).toBeNull();
    expect(outlined()).toEqual(["BBB"]);
  });

  it("무대 줄을 고른 뒤 타임라인 칸을 Shift+클릭해도 무대 점선은 그대로다", () => {
    setup(FROM_BAR_ZERO());
    stageClick("AAA");
    clickCue(2, 2, { shift: true });
    expect(outlined()).toEqual(["AAA"]);
    expect(multiCount()).toBeGreaterThan(0);
  });
});

describe("고른 칸 일괄 바꾸기 줄", () => {
  const choose = (label: string, value: string) =>
    act(() => {
      const target = container.querySelector<HTMLSelectElement>(`select[aria-label="${label}"]`);
      if (!target) throw new Error(`select not found: ${label}`);
      target.value = value;
      target.dispatchEvent(new Event("change", { bubbles: true }));
    });
  const applyBulk = () => {
    const found = Array.from(container.querySelectorAll("section.beat-grid-cell-bar button")).find(
      (button) => button.textContent === "적용",
    );
    if (!found) throw new Error("bulk apply button not found");
    act(() => (found as HTMLButtonElement).click());
  };
  const selectSixCells = () => {
    clickCue(0, 0);
    clickCue(2, 1, { shift: true });
  };
  const SIX = [
    ["AAA", 1],
    ["AAA", 3],
    ["BBB", 1],
    ["BBB", 3],
    ["CCC", 1],
    ["CCC", 3],
  ];

  it("밝기 값을 고르고 적용하면 고른 칸 전부를 한 메시지로 올린다 — 칸마다 보내지 않는다", () => {
    const { handlers } = setup(THREE_BY_THREE());
    selectSixCells();
    choose("일괄 밝기 값(%)", "60");
    applyBulk();
    expect(handlers.onEditCellsRequest).toHaveBeenCalledTimes(1);
    expect(handlers.onEditCellsRequest).toHaveBeenCalledWith({ cells: SIX, changes: buildBrightnessValueChanges(60) });
    expect(handlers.onEditRequest).not.toHaveBeenCalled();
  });

  it("디머 프리셋·디머 효과는 한 칸 편집과 같은 changes 모양이다", () => {
    const { handlers } = setup(THREE_BY_THREE());
    selectSixCells();
    choose("일괄 디머 프리셋", "1.2");
    applyBulk();
    choose("일괄 디머 프리셋", "1.60");
    applyBulk();
    expect(handlers.onEditCellsRequest.mock.calls.map(([request]) => request.changes)).toEqual([
      buildBrightnessPresetChanges("1.2"),
      buildBrightnessDimmerEffectChanges("1.60"),
    ]);
  });

  it("색 프리셋은 presetPickChanges 모양이다 — 효과 번호대 항목은 색 효과로 간다", () => {
    const { handlers } = setup(THREE_BY_THREE());
    selectSixCells();
    choose("일괄 색 프리셋", "4.2");
    applyBulk();
    choose("일괄 색 프리셋", "4.40");
    applyBulk();
    expect(handlers.onEditCellsRequest.mock.calls.map(([request]) => request.changes)).toEqual([
      presetPickChanges(COLOR_SECTION, "Color", "4.2"),
      presetPickChanges(COLOR_SECTION, "Color", "4.40"),
    ]);
    expect(presetPickChanges(COLOR_SECTION, "Color", "4.40")).toEqual({ effect_preset_no: "4.40", effect_kind: "color" });
  });

  it("디머와 색을 함께 고르면 한 changes 에 같이 담아 한 번만 올린다", () => {
    const { handlers } = setup(THREE_BY_THREE());
    selectSixCells();
    choose("일괄 밝기 값(%)", "25");
    choose("일괄 색 프리셋", "4.2");
    applyBulk();
    expect(handlers.onEditCellsRequest).toHaveBeenCalledTimes(1);
    expect(handlers.onEditCellsRequest.mock.calls[0][0].changes).toEqual({
      ...buildBrightnessValueChanges(25),
      ...presetPickChanges(COLOR_SECTION, "Color", "4.2"),
    });
  });

  it("「＋ 새 프리셋 만들기」는 일괄 바꾸기에서 고를 수 없다", () => {
    setup(THREE_BY_THREE());
    selectSixCells();
    const options = Array.from(bar()?.querySelectorAll("option") ?? []).map((option) => option.textContent);
    expect(options.some((text) => text?.includes("새 프리셋 만들기"))).toBe(false);
    expect(options).toEqual(expect.arrayContaining(["1.1 Full", "1.60 Pulse", "4.2 Red"]));
  });

  it("고른 칸의 순서는 줄 위→아래, 마디 앞→뒤다", () => {
    const { handlers } = setup(THREE_BY_THREE());
    clickCue(2, 1); // CCC 3마디가 기준
    clickCue(0, 0, { shift: true }); // AAA 1마디
    choose("일괄 밝기 값(%)", "0");
    applyBulk();
    expect(handlers.onEditCellsRequest.mock.calls[0][0].cells).toEqual(SIX);
    expect(handlers.onEditCellsRequest.mock.calls[0][0].changes).toEqual(buildBrightnessValueChanges(0));
  });

  it("고른 뒤에도 고른 칸은 그대로라 이어서 「⇪ 콘솔에 반영」을 누를 수 있다", () => {
    setup(THREE_BY_THREE());
    selectSixCells();
    choose("일괄 밝기 값(%)", "60");
    applyBulk();
    expect(multiCount()).toBe(6);
  });

  it("일괄 바꾸기 콜백이 없으면 「적용」은 꺼져 있고 이유를 말한다", () => {
    setup(THREE_BY_THREE(), { onEditCellsRequest: undefined });
    selectSixCells();
    choose("일괄 밝기 값(%)", "60");
    const apply = Array.from(bar()?.querySelectorAll("button") ?? []).find((button) => button.textContent === "적용");
    expect((apply as HTMLButtonElement).disabled).toBe(true);
    expect(bar()?.textContent).toContain("아직 화면에 연결되지 않았어요");
  });

  it("0마디(앞박) 칸은 서버 cells 로 못 보내 뺀다 — 몇 개 뺐는지 말하고 나머지에만 적용한다", () => {
    const tracks = [track("AAA", [0, 2]), track("BBB", [0, 2])];
    const { handlers } = setup(tracks);
    clickCue(0, 0, {}, 2); // AAA 0마디
    clickCue(1, 1, { shift: true }, 2); // BBB 2마디 → 4칸(0마디 둘 포함)
    expect(bar()?.textContent).toContain("4칸 고름");
    expect(bar()?.textContent).toContain("0마디(앞박) 칸 2개는 칸 단위로 바꿀 수 없어요");
    choose("일괄 밝기 값(%)", "60");
    applyBulk();
    expect(handlers.onEditCellsRequest).toHaveBeenCalledWith({
      cells: [
        ["AAA", 2],
        ["BBB", 2],
      ],
      changes: buildBrightnessValueChanges(60),
    });
  });

  it("0마디 칸만 골랐으면 보낼 칸이 없어 「적용」이 꺼진다", () => {
    const { handlers } = setup([track("AAA", [0, 2])]);
    clickCue(0, 0, { shift: true }, 2);
    choose("일괄 밝기 값(%)", "60");
    const apply = Array.from(bar()?.querySelectorAll("button") ?? []).find((button) => button.textContent === "적용");
    expect((apply as HTMLButtonElement).disabled).toBe(true);
    expect(handlers.onEditCellsRequest).not.toHaveBeenCalled();
  });

  it("서버가 거절한 이유는 방금 누른 뒤에 온 것만 줄에 보인다", () => {
    const { render } = setup(THREE_BY_THREE(), { lastServerReply: { text: "옛 거절", seq: 1, summary: BEAT_GRID_REJECTION_SUMMARY } });
    selectSixCells();
    choose("일괄 밝기 값(%)", "60");
    applyBulk();
    expect(bar()?.textContent).not.toContain("옛 거절");
    render({
      lastServerReply: {
        text: "박자 격자를 수정하지 않았습니다 — 선택한 6칸 중 1칸을 고칠 수 없어 아무 칸도 바꾸지 않았습니다",
        seq: 2,
        summary: BEAT_GRID_REJECTION_SUMMARY,
      },
    });
    expect(bar()?.textContent).toContain("아무 칸도 바꾸지 않았습니다");
  });

  it("서버가 바빠서 거절하면(busy) 그 사실을 말한다", () => {
    const { render } = setup(THREE_BY_THREE(), { busyCount: 0 });
    selectSixCells();
    choose("일괄 밝기 값(%)", "60");
    applyBulk();
    expect(bar()?.textContent).not.toContain("다른 일을 처리하는 중");
    render({ busyCount: 1 });
    expect(bar()?.textContent).toContain("다른 일을 처리하는 중이라 거절됐어요");
  });
});

describe("곡이 바뀌면 고른 칸을 비운다", () => {
  it("다른 곡의 같은 줄 이름·마디에 일괄 바꾸기가 가지 않는다", () => {
    const { render } = setup(THREE_BY_THREE());
    clickCue(0, 0);
    clickCue(2, 1, { shift: true });
    expect(multiCount()).toBe(6);
    render({}, { song_title: "OTHER SONG" });
    expect(multiCount()).toBe(0);
    expect(bar()).toBeNull();
  });

  it("같은 곡의 격자가 새로 와도(칸 값만 바뀜) 고른 칸은 남는다", () => {
    const { render } = setup(THREE_BY_THREE());
    clickCue(0, 0);
    clickCue(2, 1, { shift: true });
    render({}, { unsent_cells: [{ group_name: "AAA", bar: 1 }] });
    expect(multiCount()).toBe(6);
  });
});

describe("앞 거절 이유는 다음 고르기에 남지 않는다", () => {
  it("고른 칸을 풀었다 다시 고르면 옛 거절 줄이 되살아나지 않는다", () => {
    const { render } = setup(THREE_BY_THREE(), {
      lastServerReply: { text: "옛 답", seq: 1, summary: BEAT_GRID_REJECTION_SUMMARY },
    });
    clickCue(0, 0);
    clickCue(2, 1, { shift: true });
    const choose = (label: string, value: string) =>
      act(() => {
        const target = container.querySelector<HTMLSelectElement>(`select[aria-label="${label}"]`);
        if (!target) throw new Error("select not found");
        target.value = value;
        target.dispatchEvent(new Event("change", { bubbles: true }));
      });
    choose("일괄 밝기 값(%)", "60");
    const apply = Array.from(bar()?.querySelectorAll("button") ?? []).find((button) => button.textContent === "적용");
    act(() => (apply as HTMLButtonElement).click());
    render({ lastServerReply: { text: "거절 이유 하나", seq: 2, summary: BEAT_GRID_REJECTION_SUMMARY } });
    expect(bar()?.textContent).toContain("거절 이유 하나");
    // 선택을 풀고 다시 고른다.
    clickCue(1, 1); // 보통 클릭 = 고른 칸 비움
    clickCue(0, 0);
    clickCue(2, 1, { shift: true });
    expect(bar()?.textContent).not.toContain("거절 이유 하나");
  });
});

describe("격자가 바뀌어도 같은 인스턴스에서 사라진 칸은 빠진다", () => {
  it("줄이 사라지면 그 줄의 칸만 센다", () => {
    const tracks = THREE_BY_THREE();
    setup(tracks);
    clickCue(0, 0);
    clickCue(2, 1, { shift: true });
    expect(bar()?.textContent).toContain("6칸 고름");
    // 같은 BeatGrid 인스턴스에 CCC 가 없는 새 격자를 준다.
    act(() =>
      root.render(
        <BeatGrid grid={gridOf([tracks[0], tracks[1]])} drawerSections={DRAWER} onEditCellsRequest={vi.fn()} />,
      ),
    );
    expect(bar()?.textContent).toContain("4칸 고름");
    expect(multiCount()).toBe(4);
  });
});

describe("「⇪ 콘솔에 반영」 — 칸 단위", () => {
  const UNSENT: BeatGridUnsentCell[] = [
    { group_name: "AAA", bar: 1 },
    { group_name: "BBB", bar: 3 },
    { group_name: "CCC", bar: 5 },
  ];
  /** 칸 기록(snapshot)이 있는 곡 — 바뀐 칸이 목록이다. */
  const SNAPSHOT = { unsent_cells: UNSENT, partial_baseline: "snapshot" } as const;
  /** 칸 기록은 없고 반영 기록만 있는 곡(서버를 다시 띄운 뒤) — 바뀐 칸을 모른다. */
  const RECORD = { unsent_cells: null, partial_baseline: "record" } as const;
  const panelButtons = () => Array.from(container.querySelectorAll<HTMLButtonElement>("aside.beat-grid-cue-panel .beat-grid-console-apply button"));
  const mainApply = () => panelButtons().find((button) => button.textContent?.includes("⇪")) as HTMLButtonElement;
  const wholeApply = () => panelButtons().find((button) => button.textContent === "전체 다시 반영") as HTMLButtonElement;
  const scope = () => container.querySelector(".beat-grid-apply-scope")?.textContent ?? "";
  const NO_RECORD_HINT = "이 곡은 아직 반영 기록이 없어요 — 「전체 다시 반영」을 먼저 누르세요";
  const SIX = [
    ["AAA", 1],
    ["AAA", 3],
    ["BBB", 1],
    ["BBB", 3],
    ["CCC", 1],
    ["CCC", 3],
  ];

  describe("칸 기록 기준(snapshot)", () => {
    it("고른 칸이 없으면 바뀐 칸 전부를 보낸다", () => {
      const { handlers } = setup(THREE_BY_THREE(), {}, SNAPSHOT);
      expect(mainApply().disabled).toBe(false);
      expect(scope()).toBe("바뀐 3칸만 보내요");
      act(() => mainApply().click());
      expect(handlers.onApplyCells).toHaveBeenCalledTimes(1);
      expect(handlers.onApplyCells).toHaveBeenCalledWith([
        ["AAA", 1],
        ["BBB", 3],
        ["CCC", 5],
      ]);
      expect(handlers.onApply).not.toHaveBeenCalled();
    });

    it("고른 칸이 있으면 그 가운데 바뀐 칸만 보낸다", () => {
      const { handlers } = setup(THREE_BY_THREE(), {}, SNAPSHOT);
      clickCue(0, 0);
      clickCue(2, 1, { shift: true }); // 6칸 — 바뀐 칸 가운데 AAA1·BBB3 이 든다(CCC5 는 밖)
      expect(scope()).toBe("고른 6칸 중 바뀐 2칸만 보내요 · 콘솔과 같아 뺀 4칸");
      act(() => mainApply().click());
      expect(handlers.onApplyCells).toHaveBeenCalledWith([
        ["AAA", 1],
        ["BBB", 3],
      ]);
    });

    it("고른 칸 가운데 바뀐 칸이 없으면 꺼지고 그렇게 말한다", () => {
      const { handlers } = setup(THREE_BY_THREE(), {}, SNAPSHOT);
      clickCue(1, 0); // BBB 1마디
      clickCue(1, 2, { ctrl: true }); // BBB 5마디를 더한다 — 둘 다 안 바뀐 칸(바뀐 BBB 칸은 3마디뿐)
      expect(multiCount()).toBe(2);
      expect(mainApply().disabled).toBe(true);
      expect(mainApply().title).toBe("고른 칸 중 바뀐 칸이 없어요");
      expect(scope()).toBe("고른 칸 중 바뀐 칸이 없어요");
      act(() => mainApply().click());
      expect(handlers.onApplyCells).not.toHaveBeenCalled();
    });

    it("바뀐 칸이 하나도 없으면(빈 배열) 「바뀐 칸이 없어요」로 꺼진다", () => {
      setup(THREE_BY_THREE(), {}, { unsent_cells: [], partial_baseline: "snapshot" });
      expect(mainApply().disabled).toBe(true);
      expect(mainApply().title).toBe("바뀐 칸이 없어요");
    });
  });

  // 칸 단위 반영만 한 곡의 칸 기록은 부분이다 — 서버가 아는 칸을 known_cells 로 싣는다(unsent_cells 는 그 가운데 바뀐 칸).
  // 아는데 안 바뀐 칸은 콘솔과 같아 빼고, 바뀐 칸과 모르는 칸은 보낸다.
  describe("칸 기록이 부분일 때(known_cells)", () => {
    // 아는 칸: AAA1 · AAA3 · BBB1 / 그 가운데 바뀐 칸: AAA3 / 나머지 여섯 칸은 모르는 칸.
    const PARTIAL: Partial<BeatGridView> = {
      unsent_cells: [{ group_name: "AAA", bar: 3 }],
      known_cells: [
        ["AAA", 1],
        ["AAA", 3],
        ["BBB", 1],
      ],
      partial_baseline: "snapshot",
    };

    it("고른 칸을 갈라 — 아는데 안 바뀐 칸은 빼고, 바뀐 칸과 모르는 칸은 보낸다", () => {
      const { handlers } = setup(THREE_BY_THREE(), {}, PARTIAL);
      clickCue(0, 0);
      clickCue(2, 1, { shift: true }); // AAA1 AAA3 BBB1 BBB3 CCC1 CCC3
      expect(mainApply().disabled).toBe(false);
      expect(scope()).toBe(
        "고른 6칸 중 4칸을 보내요 (바뀐 1칸 · 콘솔 상태를 모르는 3칸) · 콘솔과 같아 뺀 2칸",
      );
      act(() => mainApply().click());
      expect(handlers.onApplyCells).toHaveBeenCalledTimes(1);
      expect(handlers.onApplyCells).toHaveBeenCalledWith([
        ["AAA", 3], // 바뀐 칸
        ["BBB", 3], // 모르는 칸
        ["CCC", 1], // 모르는 칸
        ["CCC", 3], // 모르는 칸
      ]);
    });

    it("고른 칸이 없으면 바뀐 아는 칸만 보낸다 — 모르는 칸은 고르지 않으면 안 보낸다", () => {
      const { handlers } = setup(THREE_BY_THREE(), {}, PARTIAL);
      expect(scope()).toBe("바뀐 1칸만 보내요");
      act(() => mainApply().click());
      expect(handlers.onApplyCells).toHaveBeenCalledWith([["AAA", 3]]);
    });

    it("아는데 안 바뀐 칸만 골랐으면 꺼지고 「고른 칸 중 바뀐 칸이 없어요」", () => {
      const { handlers } = setup(THREE_BY_THREE(), {}, PARTIAL);
      clickCue(0, 0); // AAA1
      clickCue(1, 0, { ctrl: true }); // BBB1 을 더한다 — 둘 다 아는데 안 바뀐 칸
      expect(multiCount()).toBe(2);
      expect(mainApply().disabled).toBe(true);
      expect(mainApply().title).toBe("고른 칸 중 바뀐 칸이 없어요");
      act(() => mainApply().click());
      expect(handlers.onApplyCells).not.toHaveBeenCalled();
    });

    it("모르는 칸만 골라도 켜지고 모두 보낸다 — 같다고 보지 않는다", () => {
      const { handlers } = setup(THREE_BY_THREE(), {}, PARTIAL);
      clickCue(2, 0); // CCC1
      clickCue(2, 1, { ctrl: true }); // CCC3 을 더한다 — 둘 다 모르는 칸
      expect(mainApply().disabled).toBe(false);
      expect(scope()).toBe("고른 2칸 중 2칸을 보내요 (콘솔 상태를 모르는 2칸)");
      act(() => mainApply().click());
      expect(handlers.onApplyCells).toHaveBeenCalledWith([
        ["CCC", 1],
        ["CCC", 3],
      ]);
    });

    it("known_cells 가 없는 전체 기록이면 예전처럼 안 바뀐 칸은 모두 뺀다", () => {
      const { handlers } = setup(THREE_BY_THREE(), {}, { unsent_cells: UNSENT, partial_baseline: "snapshot" });
      clickCue(0, 0);
      clickCue(2, 1, { shift: true }); // 6칸 가운데 바뀐 칸은 AAA1·BBB3 뿐 — 모르는 칸은 없다
      expect(scope()).toBe("고른 6칸 중 바뀐 2칸만 보내요 · 콘솔과 같아 뺀 4칸");
      act(() => mainApply().click());
      expect(handlers.onApplyCells).toHaveBeenCalledWith([
        ["AAA", 1],
        ["BBB", 3],
      ]);
    });
  });

  describe("기록 기준(record) — 칸 기록은 없고 반영 기록만 있다", () => {
    it("고른 칸이 없으면 꺼지고, 바뀐 칸을 알 수 없으니 먼저 고르라고 말한다 — 「전체 다시 반영 먼저」 안내가 아니다", () => {
      const { handlers } = setup(THREE_BY_THREE(), {}, RECORD);
      const hint = "고른 칸을 먼저 골라 주세요 — 기록 기준이라 바뀐 칸을 알 수 없어요";
      expect(mainApply().disabled).toBe(true);
      expect(mainApply().title).toBe(hint);
      expect(scope()).toBe(hint);
      expect(container.textContent).not.toContain(NO_RECORD_HINT);
      expect(wholeApply().disabled).toBe(false);
      act(() => mainApply().click());
      expect(handlers.onApplyCells).not.toHaveBeenCalled();
    });

    it("칸을 고르면 켜지고, 누르면 고른 칸을 모두 보낸다 — 바뀐 칸으로 거르지 않는다", () => {
      const { handlers } = setup(THREE_BY_THREE(), {}, RECORD);
      clickCue(0, 0);
      clickCue(2, 1, { shift: true });
      expect(mainApply().disabled).toBe(false);
      act(() => mainApply().click());
      expect(handlers.onApplyCells).toHaveBeenCalledTimes(1);
      expect(handlers.onApplyCells).toHaveBeenCalledWith(SIX);
      expect(handlers.onApply).not.toHaveBeenCalled();
    });

    it("안내 줄과 버튼 title 이 기록 기준이라는 것과 지운 값이 콘솔에 남을 수 있다는 것을 말한다", () => {
      setup(THREE_BY_THREE(), {}, RECORD);
      clickCue(0, 0);
      clickCue(2, 1, { shift: true });
      const note =
        "고른 6칸을 보내요 (기록 기준) · 지운 값은 콘솔에 남을 수 있어요 — 지운 칸은 「전체 다시 반영」으로";
      expect(scope()).toBe(note);
      expect(mainApply().title).toBe(`⇪ 콘솔에 반영 — ${note}`);
    });

    it("칸 표시(앱에서만 바뀜 · 콘솔과 같음)는 unsent_cells 가 null 이라 여전히 없다", () => {
      setup(THREE_BY_THREE(), {}, RECORD);
      expect(container.querySelectorAll(".beat-grid-cue-sync").length).toBe(0);
      clickCue(0, 0);
      clickCue(2, 1, { shift: true });
      expect(container.querySelectorAll(".beat-grid-cue-sync").length).toBe(0);
    });

    it("선택을 풀면 다시 꺼진다", () => {
      setup(THREE_BY_THREE(), {}, RECORD);
      clickCue(0, 0);
      clickCue(2, 1, { shift: true });
      expect(mainApply().disabled).toBe(false);
      clickCue(1, 1); // 보통 클릭 = 고른 칸 비움
      expect(mainApply().disabled).toBe(true);
    });
  });

  describe("기준이 없을 때(partial_baseline null/undefined)", () => {
    it("반영 기록이 없으면(unsent_cells null, 기준 null) 꺼지고, 「전체 다시 반영」을 먼저 누르라는 안내가 보인다", () => {
      const { handlers } = setup(THREE_BY_THREE(), {}, { unsent_cells: null, partial_baseline: null });
      expect(mainApply().disabled).toBe(true);
      expect(mainApply().title).toBe(NO_RECORD_HINT);
      expect(scope()).toBe(NO_RECORD_HINT);
      expect(wholeApply().disabled).toBe(false);
      act(() => mainApply().click());
      expect(handlers.onApplyCells).not.toHaveBeenCalled();
    });

    it("고른 칸이 있어도 같다 — 기준이 없으면 칸 단위로 보낼 수 없다", () => {
      const { handlers } = setup(THREE_BY_THREE(), {}, { unsent_cells: null, partial_baseline: null });
      clickCue(0, 0);
      clickCue(2, 1, { shift: true });
      expect(mainApply().disabled).toBe(true);
      expect(scope()).toBe(NO_RECORD_HINT);
      act(() => mainApply().click());
      expect(handlers.onApplyCells).not.toHaveBeenCalled();
    });

    it("옛 서버라 필드가 없을 때(둘 다 undefined)도 같다", () => {
      setup(THREE_BY_THREE());
      expect(mainApply().disabled).toBe(true);
      expect(mainApply().title).toBe(NO_RECORD_HINT);
    });

    it("기준 필드가 없으면 unsent_cells 가 목록이어도 칸 단위로 보내지 않는다", () => {
      setup(THREE_BY_THREE(), {}, { unsent_cells: UNSENT });
      expect(mainApply().disabled).toBe(true);
      expect(mainApply().title).toBe(NO_RECORD_HINT);
    });
  });

  it("「전체 다시 반영」은 칸 없이 예전 전체 반영 콜백만 한 번 부른다", () => {
    const { handlers } = setup(THREE_BY_THREE(), {}, SNAPSHOT);
    act(() => wholeApply().click());
    expect(handlers.onApply).toHaveBeenCalledTimes(1);
    expect(handlers.onApply).toHaveBeenCalledWith();
    expect(handlers.onApplyCells).not.toHaveBeenCalled();
  });

  it("기록 기준에서도 「전체 다시 반영」은 그대로 전체 반영이다", () => {
    const { handlers } = setup(THREE_BY_THREE(), {}, RECORD);
    act(() => wholeApply().click());
    expect(handlers.onApply).toHaveBeenCalledTimes(1);
    expect(handlers.onApplyCells).not.toHaveBeenCalled();
  });

  it("칸 단위 콜백이 없으면 예전 단일 버튼이다 — 「전체 다시 반영」도 안내 줄도 없다", () => {
    const { handlers } = setup(THREE_BY_THREE(), { onApplyCells: undefined }, SNAPSHOT);
    expect(wholeApply()).toBeUndefined();
    expect(scope()).toBe("");
    act(() => mainApply().click());
    expect(handlers.onApply).toHaveBeenCalledTimes(1);
  });

  it("누르면 진행 문구가 뜬다 — 전체 반영과 같다", () => {
    setup(THREE_BY_THREE(), {}, SNAPSHOT);
    expect(container.querySelector(".beat-grid-apply-progress")).toBeNull();
    act(() => mainApply().click());
    expect(container.querySelector(".beat-grid-apply-progress")?.textContent).toContain("콘솔을 읽는 중");
  });
});

describe("칸 단위 반영 결과", () => {
  const SUBSET = {
    requested: 3,
    applied: [
      ["BBB", 3],
      ["AAA", 1],
    ] as [string, number][],
    not_applied: [{ group_name: "CCC", bar: 5, reason: "콘솔과 같음" }],
  };
  const resultLine = () => container.querySelector<HTMLElement>(".beat-grid-apply-result");
  const failLine = () => container.querySelector<HTMLElement>(".beat-grid-apply-fail");

  it("성공하면 한 줄로 요약하고 칸마다 전부는 title 에 둔다", () => {
    const { render } = setup(THREE_BY_THREE(), { sendStatus: null });
    expect(resultLine()).toBeNull();
    render({ sendStatus: status({ subset: SUBSET }) });
    expect(resultLine()?.textContent).toContain("2칸 반영 · 못 보낸 칸 1개 — 콘솔과 같음");
    expect(resultLine()?.title).toContain("반영한 칸: BBB 3마디, AAA 1마디");
    expect(resultLine()?.title).toContain("못 보낸 칸: CCC 5마디 — 콘솔과 같음");
    expect(failLine()).toBeNull();
  });

  it("기록 기준으로 보냈으면 요약 끝에 그 사실을 붙인다 — 칸 기록 기준에는 붙지 않는다", () => {
    const { render } = setup(THREE_BY_THREE(), { sendStatus: null });
    render({ sendStatus: status({ subset: { ...SUBSET, baseline: "record" } }) });
    expect(resultLine()?.textContent).toContain(
      "2칸 반영 · 못 보낸 칸 1개 — 콘솔과 같음 · 기록 기준으로 보냄(지운 값은 확인 못 함)",
    );
    // 칸 목록 title 은 그대로다.
    expect(resultLine()?.title).toContain("반영한 칸: BBB 3마디, AAA 1마디");
    render({ sendStatus: status({ subset: { ...SUBSET, baseline: "snapshot" } }) });
    expect(resultLine()?.textContent).not.toContain("기록 기준");
  });

  it("성공하면 보낸 첫 칸의 마디를 콘솔에서 보러 간다 — 한 번만", () => {
    const { handlers, render } = setup(THREE_BY_THREE(), { sendStatus: null });
    const done = status({ subset: SUBSET });
    render({ sendStatus: done });
    expect(handlers.onPreviewBar).toHaveBeenCalledTimes(1);
    expect(handlers.onPreviewBar).toHaveBeenCalledWith(3);
    render({ sendStatus: done, busyCount: 0 }); // 같은 응답 객체로 다시 그려도 되풀이하지 않는다
    expect(handlers.onPreviewBar).toHaveBeenCalledTimes(1);
    render({ sendStatus: status({ subset: SUBSET }) }); // 새 응답이 오면 그때 다시 한 번
    expect(handlers.onPreviewBar).toHaveBeenCalledTimes(2);
  });

  it("마디를 보러 간 뒤 미리보기 응답이 와도 요약은 남는다", () => {
    const { handlers, render } = setup(THREE_BY_THREE(), { sendStatus: null });
    render({ sendStatus: status({ subset: SUBSET }) });
    render({ sendStatus: status({ last_action: "preview" }) });
    expect(resultLine()?.textContent).toContain("2칸 반영");
    expect(handlers.onPreviewBar).toHaveBeenCalledTimes(1);
  });

  it("콘솔이 돌고 있을 수 있으면(정지 확인 전) 요약은 보이되 콘솔을 그 마디로 옮기지 않는다", () => {
    const relay = createConsoleFollowRelay();
    relay.consoleMayRun = true;
    const { handlers, render } = setup(THREE_BY_THREE(), { sendStatus: null, consoleFollowRelay: relay });
    render({ sendStatus: status({ subset: SUBSET }) });
    expect(resultLine()?.textContent).toContain("2칸 반영");
    expect(handlers.onPreviewBar).not.toHaveBeenCalled();
  });

  it("마운트 때 이미 있던 응답에는 반응하지 않는다 — 요약도 마디 이동도 없다", () => {
    const { handlers } = setup(THREE_BY_THREE(), { sendStatus: status({ subset: SUBSET }) });
    expect(resultLine()).toBeNull();
    expect(handlers.onPreviewBar).not.toHaveBeenCalled();
  });

  it("전체 반영 성공(subset 없음)이나 보낸 칸이 0개인 응답은 요약도 마디 이동도 없다", () => {
    const { handlers, render } = setup(THREE_BY_THREE(), { sendStatus: null });
    render({ sendStatus: status({ completed: "reflected" }) });
    render({ sendStatus: status({ subset: { ...SUBSET, applied: [] } }) });
    expect(resultLine()).toBeNull();
    expect(handlers.onPreviewBar).not.toHaveBeenCalled();
  });

  it("실패하면 이유를 알림 줄에 보인다 — 요약은 없다", () => {
    const { handlers, render } = setup(THREE_BY_THREE(), { sendStatus: null });
    render({
      sendStatus: status({
        ok: false,
        reason: "칸 단위로 보낼 수 있는 칸이 없습니다 — AAA 1마디: 콘솔과 같음",
      }),
    });
    expect(failLine()?.textContent).toBe(
      "⚠ 콘솔에 반영 안 됨 — 칸 단위로 보낼 수 있는 칸이 없습니다 — AAA 1마디: 콘솔과 같음",
    );
    expect(resultLine()).toBeNull();
    expect(handlers.onPreviewBar).not.toHaveBeenCalled();
  });

  it("다시 누르면 앞 요약은 지워진다", () => {
    const { render } = setup(
      THREE_BY_THREE(),
      { sendStatus: null },
      { unsent_cells: [{ group_name: "AAA", bar: 1 }], partial_baseline: "snapshot" },
    );
    render({ sendStatus: status({ subset: SUBSET }) });
    expect(resultLine()).not.toBeNull();
    const main = Array.from(container.querySelectorAll<HTMLButtonElement>("aside.beat-grid-cue-panel .beat-grid-console-apply button")).find(
      (button) => button.textContent?.includes("⇪"),
    );
    act(() => main?.click());
    expect(resultLine()).toBeNull();
  });

  it("✕ 로 닫을 수 있다", () => {
    const { render } = setup(THREE_BY_THREE(), { sendStatus: null });
    render({ sendStatus: status({ subset: SUBSET }) });
    act(() => resultLine()?.querySelector("button")?.click());
    expect(resultLine()).toBeNull();
  });

  it("칸 단위 반영 성공은 「콘솔 같이」를 켜지 않는다 — 전체 반영 성공은 켠다(예전 그대로)", () => {
    const consoleHandlers = {
      onConsolePlay: vi.fn(),
      onConsolePause: vi.fn(),
      onConsoleResume: vi.fn(),
      onConsoleStop: vi.fn(),
    };
    const { render } = setup(THREE_BY_THREE(), { sendStatus: null, ...consoleHandlers });
    const toggle = () =>
      Array.from(container.querySelectorAll<HTMLButtonElement>("header.beat-grid-topbar button")).find((button) =>
        (button.textContent ?? "").includes("콘솔 같이"),
      ) as HTMLButtonElement;
    expect(toggle().getAttribute("aria-pressed")).toBe("false");
    render({ sendStatus: status({ completed: "reflected", subset: SUBSET }) });
    expect(toggle().getAttribute("aria-pressed")).toBe("false");
    render({ sendStatus: status({ completed: "reflected" }) });
    expect(toggle().getAttribute("aria-pressed")).toBe("true");
  });
});

describe("칸별 표시 — 앱에서만 바뀜 · 콘솔과 같음", () => {
  const syncOf = (index: number) => cueButtons()[index].querySelector<HTMLElement>(".beat-grid-cue-sync");

  it("바뀐 칸에는 「앱에서만 바뀜」이, 나머지에는 「콘솔과 같음」이 기호와 함께 붙는다", () => {
    setup(THREE_BY_THREE(), {}, { unsent_cells: [{ group_name: "AAA", bar: 3 }], partial_baseline: "snapshot" });
    const changed = syncOf(1);
    expect(changed?.classList.contains("is-app-only")).toBe(true);
    expect(changed?.getAttribute("aria-label")).toBe("앱에서만 바뀜");
    expect(changed?.title).toBe("앱에서만 바뀜");
    expect(changed?.textContent).toBe("✎");
    expect(changed?.getAttribute("role")).toBe("img");
    const same = syncOf(0);
    expect(same?.classList.contains("is-in-sync")).toBe(true);
    expect(same?.getAttribute("aria-label")).toBe("콘솔과 같음");
    expect(same?.textContent).toBe("✓");
    expect(container.querySelectorAll(".beat-grid-cue-sync.is-app-only").length).toBe(1);
    expect(container.querySelectorAll(".beat-grid-cue-sync.is-in-sync").length).toBe(8);
  });

  it("고친 칸의 초록 강조(is-edited)는 그대로 남는다", () => {
    setup(THREE_BY_THREE(), {}, { unsent_cells: [{ group_name: "AAA", bar: 3 }] });
    expect(cueButtons()[1].classList.contains("is-edited")).toBe(true);
    expect(cueButtons()[0].classList.contains("is-edited")).toBe(false);
  });

  it("반영 기록이 없으면(null) 아무 표시도 없다", () => {
    setup(THREE_BY_THREE(), {}, { unsent_cells: null });
    expect(container.querySelectorAll(".beat-grid-cue-sync").length).toBe(0);
  });

  it("기록 기준(record)이어도 unsent_cells 가 null 이면 아무 표시도 없다 — 칸 단위로 보낼 수 있는 것과 별개다", () => {
    setup(THREE_BY_THREE(), {}, { unsent_cells: null, partial_baseline: "record" });
    expect(container.querySelectorAll(".beat-grid-cue-sync").length).toBe(0);
  });

  describe("칸 기록이 부분일 때(known_cells) — 모르는 칸에는 표시가 없다", () => {
    // 아는 칸: AAA1(0번) · AAA3(1번) · BBB1(3번) / 그 가운데 바뀐 칸: AAA3 / 나머지 여섯 칸(2·4~8번)은 모르는 칸.
    const PARTIAL: Partial<BeatGridView> = {
      unsent_cells: [{ group_name: "AAA", bar: 3 }],
      known_cells: [
        ["AAA", 1],
        ["AAA", 3],
        ["BBB", 1],
      ],
      partial_baseline: "snapshot",
    };

    it("아는 칸만 표시한다 — 바뀐 칸은 앱에서만 바뀜, 안 바뀐 칸은 콘솔과 같음, 모르는 칸은 없음", () => {
      setup(THREE_BY_THREE(), {}, PARTIAL);
      expect(syncOf(1)?.classList.contains("is-app-only")).toBe(true); // AAA3
      expect(syncOf(0)?.classList.contains("is-in-sync")).toBe(true); // AAA1
      expect(syncOf(3)?.classList.contains("is-in-sync")).toBe(true); // BBB1
      for (const unknown of [2, 4, 5, 6, 7, 8]) expect(syncOf(unknown)).toBeNull();
      expect(container.querySelectorAll(".beat-grid-cue-sync").length).toBe(3);
    });

    it("known_cells 가 없으면(전체 기록) 모든 칸이 아는 칸이라 아홉 칸 모두 표시한다", () => {
      setup(THREE_BY_THREE(), {}, { unsent_cells: [{ group_name: "AAA", bar: 3 }], partial_baseline: "snapshot" });
      expect(container.querySelectorAll(".beat-grid-cue-sync").length).toBe(9);
    });

    it("아는 칸이 하나도 없으면(빈 배열) 아무 표시도 없다", () => {
      setup(THREE_BY_THREE(), {}, { unsent_cells: [], known_cells: [], partial_baseline: "snapshot" });
      expect(container.querySelectorAll(".beat-grid-cue-sync").length).toBe(0);
    });

    it("known_cells 가 있어도 unsent_cells 가 null 이면 아무 표시도 없다", () => {
      setup(THREE_BY_THREE(), {}, { unsent_cells: null, known_cells: [["AAA", 1]], partial_baseline: "snapshot" });
      expect(container.querySelectorAll(".beat-grid-cue-sync").length).toBe(0);
    });

    it("격자가 새로 오면 아는 칸이 늘어난 대로 표시가 따라온다", () => {
      const { render } = setup(THREE_BY_THREE(), {}, PARTIAL);
      expect(container.querySelectorAll(".beat-grid-cue-sync").length).toBe(3);
      render({}, { known_cells: [...(PARTIAL.known_cells ?? []), ["CCC", 1]] });
      expect(container.querySelectorAll(".beat-grid-cue-sync").length).toBe(4);
      expect(syncOf(6)?.classList.contains("is-in-sync")).toBe(true); // CCC1
    });

    it("고친 칸의 초록 강조(is-edited)는 아는 칸 여부와 상관없이 unsent_cells 를 따른다", () => {
      setup(THREE_BY_THREE(), {}, PARTIAL);
      expect(cueButtons()[1].classList.contains("is-edited")).toBe(true); // AAA3
      expect(cueButtons()[0].classList.contains("is-edited")).toBe(false);
    });
  });

  it("필드가 없는 옛 서버 응답(undefined)에도 아무 표시가 없다", () => {
    setup(THREE_BY_THREE());
    expect(container.querySelectorAll(".beat-grid-cue-sync").length).toBe(0);
  });

  it("빈 배열(기록은 있고 바뀐 칸이 없음)이면 모든 칸이 「콘솔과 같음」이다", () => {
    setup(THREE_BY_THREE(), {}, { unsent_cells: [] });
    expect(container.querySelectorAll(".beat-grid-cue-sync.is-in-sync").length).toBe(9);
    expect(container.querySelectorAll(".beat-grid-cue-sync.is-app-only").length).toBe(0);
  });

  it("위쪽 대기 수 배지는 그대로 부모가 넘긴 값이다", () => {
    setup(THREE_BY_THREE(), { pendingApplyCount: 7 }, { unsent_cells: [{ group_name: "AAA", bar: 3 }] });
    expect(container.querySelector(".beat-grid-console-apply .badge")?.textContent).toBe("7");
  });
});

// 일괄 바꾸기가 편집 칸이 펼친 칸의 값을 바꿔도, 한 칸 편집의 고르기는 칸을 고를 때 채운 옛 값(예: 4.167)에 머물렀다.
// 서버는 격자(song_timeline)를 먼저, 성공 답(chat_response)을 나중에 보낸다 — 성공 답이 오면 고르기를 지금 칸 값으로 다시 채운다.
describe("일괄 바꾸기가 성공하면 한 칸 편집 고르기가 서버 값으로 다시 채워진다", () => {
  const COLOR_DRAWER: BeatGridDrawerSection[] = [
    DRAWER[0],
    {
      ...DRAWER[1],
      entries: [
        { preset_no: "4.167", name: "Warm", usage_count: 3, used_by: [], is_effect_band: false },
        { preset_no: "4.168", name: "Cool", usage_count: 0, used_by: [], is_effect_band: false },
      ],
    },
  ];
  /** 세 줄 모두 칸마다 같은 색·밝기를 가진 격자. */
  const withValues = (colorNo: string, percent: number) =>
    THREE_BY_THREE().map((row) => ({
      ...row,
      cues: row.cues.map((item) => ({
        ...item,
        color_preset_no: colorNo,
        brightness: { mode: "value" as const, value_percent: percent, preset_no: null },
      })),
    }));
  const okReply = (seq: number) => ({ text: "AAA 1마디 … (콘솔 무접촉)", seq, summary: BEAT_GRID_EDIT_OK_SUMMARY });
  const rejectReply = (seq: number) => ({
    text: "박자 격자를 수정하지 않았습니다 — 선택한 6칸 중 1칸을 고칠 수 없어요",
    seq,
    summary: BEAT_GRID_REJECTION_SUMMARY,
  });
  const editorColor = () => container.querySelector<HTMLSelectElement>('select[aria-label="색 프리셋"]');
  const editorBrightness = () => container.querySelector<HTMLSelectElement>('select[aria-label="밝기 값(%)"]');
  const change = (target: HTMLSelectElement | null, value: string) =>
    act(() => {
      if (!target) throw new Error("select not found");
      target.value = value;
      target.dispatchEvent(new Event("change", { bubbles: true }));
    });
  const chooseInBar = (label: string, value: string) =>
    change(bar()?.querySelector<HTMLSelectElement>(`select[aria-label="${label}"]`) ?? null, value);
  const pressBulkApply = () => {
    const found = Array.from(bar()?.querySelectorAll("button") ?? []).find((button) => button.textContent === "적용");
    act(() => (found as HTMLButtonElement).click());
  };
  /** AAA 1마디를 눌러 편집 칸을 펼치고, 3줄 × 마디 1~3 = 6칸을 고른다. */
  const openEditorAndPickSix = () => {
    clickCue(0, 0);
    clickCue(2, 1, { shift: true });
  };

  it("편집 칸이 펼친 칸의 색이 바뀌면 고르기가 새 값(4.168)을 보인다 — 옛 값(4.167)에 머물지 않는다", () => {
    const { handlers, render } = setup(withValues("4.167", 100), { drawerSections: COLOR_DRAWER });
    openEditorAndPickSix();
    expect(editorColor()?.value).toBe("4.167");
    chooseInBar("일괄 색 프리셋", "4.168");
    pressBulkApply();
    expect(handlers.onEditCellsRequest).toHaveBeenCalledTimes(1);
    // 서버가 보낸 순서 그대로: 새 격자 → 성공 답.
    render({}, { tracks: withValues("4.168", 100) });
    render({ lastServerReply: okReply(1) });
    expect(editorColor()?.value).toBe("4.168");
  });

  it("밝기도 마찬가지다 — 고르기가 서버 값으로 바뀐다", () => {
    const { render } = setup(withValues("4.167", 100), { drawerSections: COLOR_DRAWER });
    openEditorAndPickSix();
    expect(editorBrightness()?.value).toBe("100");
    chooseInBar("일괄 밝기 값(%)", "60");
    pressBulkApply();
    render({}, { tracks: withValues("4.167", 60) });
    render({ lastServerReply: okReply(1) });
    expect(editorBrightness()?.value).toBe("60");
  });

  it("거절 답이 오면 다시 채우지 않는다 — 편집 칸에서 고치던 값이 그대로 남는다", () => {
    const { render } = setup(withValues("4.167", 100), { drawerSections: COLOR_DRAWER });
    openEditorAndPickSix();
    change(editorColor(), "4.168"); // 한 칸 편집에서 고르는 중(아직 적용 전)
    chooseInBar("일괄 밝기 값(%)", "60");
    pressBulkApply();
    render({ lastServerReply: rejectReply(1) });
    expect(editorColor()?.value).toBe("4.168");
    expect(bar()?.textContent).toContain("고칠 수 없어요");
  });

  it("누르기 전에 와 있던 성공 답으로는 다시 채우지 않고, 누른 뒤의 새 성공 답에만 채운다", () => {
    const { render } = setup(withValues("4.167", 100), { drawerSections: COLOR_DRAWER, lastServerReply: okReply(1) });
    openEditorAndPickSix();
    change(editorColor(), "4.168");
    chooseInBar("일괄 밝기 값(%)", "60");
    pressBulkApply();
    render({ lastServerReply: okReply(1) }); // 같은 옛 답으로 다시 그려도
    expect(editorColor()?.value).toBe("4.168");
    render({ lastServerReply: okReply(2) }); // 누른 뒤의 성공 답
    expect(editorColor()?.value).toBe("4.167"); // 격자 값(이 시험에서는 안 바뀜)으로 돌아간다
  });

  it("한 번만 다시 채운다 — 그 뒤 다른 편집의 성공 답이 와도 고치던 값을 지우지 않는다", () => {
    const { render } = setup(withValues("4.167", 100), { drawerSections: COLOR_DRAWER });
    openEditorAndPickSix();
    chooseInBar("일괄 색 프리셋", "4.168");
    pressBulkApply();
    render({}, { tracks: withValues("4.168", 100) });
    render({ lastServerReply: okReply(1) });
    expect(editorColor()?.value).toBe("4.168");
    change(editorColor(), "4.167"); // 이제 편집 칸에서 다시 고르는 중
    render({ lastServerReply: okReply(2) }); // 한 칸 편집 등 다른 성공 답
    expect(editorColor()?.value).toBe("4.167");
  });

  it("성공한 뒤에는 앞 답 기다림을 지운다 — 늦게 온 busy 가 그 일괄 바꾸기의 거절처럼 보이지 않는다", () => {
    const { render } = setup(withValues("4.167", 100), { drawerSections: COLOR_DRAWER, busyCount: 0 });
    openEditorAndPickSix();
    chooseInBar("일괄 색 프리셋", "4.168");
    pressBulkApply();
    render({}, { tracks: withValues("4.168", 100) });
    render({ lastServerReply: okReply(1) });
    render({ busyCount: 1 }); // 다른 요청(서랍 등)이 바빠서 거절됐다
    expect(bar()?.textContent).not.toContain("다른 일을 처리하는 중");
  });

  it("일괄 바꾸기를 누르지 않았다면 성공 답이 와도 고르던 값을 건드리지 않는다", () => {
    const { render } = setup(withValues("4.167", 100), { drawerSections: COLOR_DRAWER });
    openEditorAndPickSix();
    change(editorColor(), "4.168");
    render({ lastServerReply: okReply(1) });
    expect(editorColor()?.value).toBe("4.168");
  });
});

describe("splitDimmerSection", () => {
  it("효과 번호대는 「디머 효과」로, 나머지는 「디머 프리셋」으로 가른다", () => {
    const { presetSection, effects } = splitDimmerSection(DRAWER[0]);
    expect(presetSection?.entries.map((entry) => entry.preset_no)).toEqual(["1.1", "1.2"]);
    expect(effects.map((entry) => entry.preset_no)).toEqual(["1.60"]);
  });

  it("섹션이 없거나 풀을 못 읽었으면 가르지 않는다", () => {
    expect(splitDimmerSection(null)).toEqual({ presetSection: null, effects: [] });
    const unread = { ...DRAWER[0], unread: true };
    expect(splitDimmerSection(unread)).toEqual({ presetSection: unread, effects: [] });
  });
});
