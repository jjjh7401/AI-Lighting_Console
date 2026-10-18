// @vitest-environment jsdom
// 무대에서 줄 고르기와 「적용」 — 실제 `<BeatGrid>` 를 그려 무대 클릭(보통·Shift)이 고른 줄을 어떻게 바꾸고,
// 큐 편집 칸의 「적용」이 고른 줄 전부에 칸마다 요청 하나씩 보내는지 잰다. 순수 함수는
// `BeatGridStageSelection.test.ts` 가 따로 본다. DOM 이 필요해 `BeatGrid.flowChain.test.tsx` 와 같은 방식(jsdom + `act`).
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { BeatGridCue, BeatGridTrack, BeatGridView } from "../protocol";
import { BeatGrid, buildBrightnessValueChanges, type BeatGridFixturePoint } from "./BeatGrid";

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

/** 줄마다 무대에 장비 한 대 — 좌표가 있어야 줄마다 눌리는 영역이 생긴다. */
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

function mount(tracks: BeatGridTrack[]) {
  const onEditRequest = vi.fn();
  act(() =>
    root.render(
      <BeatGrid
        grid={gridOf(tracks)}
        fixtures={fixturesOf(tracks.map((t) => t.group_name))}
        onEditRequest={onEditRequest}
      />,
    ),
  );
  return { onEditRequest };
}

/** 무대의 줄 영역을 이름으로 누른다 — `shift` 면 Shift+클릭. */
function stageClick(name: string, shift = false) {
  const hit = container.querySelector(`rect.beat-grid-stage-hit[data-track="${name}"]`);
  if (!hit) throw new Error(`stage zone not found: ${name}`);
  act(() => {
    hit.dispatchEvent(new MouseEvent("click", { bubbles: true, shiftKey: shift }));
  });
}

/** 노란 점선이 둘러진 줄 이름들(무대 그림 순서) — 점선은 같은 자리의 눌리는 영역과 좌표가 같다. */
function outlined(): string[] {
  const hits = Array.from(container.querySelectorAll("rect.beat-grid-stage-hit"));
  return Array.from(container.querySelectorAll("rect.beat-grid-stage-selected")).map((rect) => {
    const same = hits.find((hit) => hit.getAttribute("x") === rect.getAttribute("x") && hit.getAttribute("y") === rect.getAttribute("y"));
    return same?.getAttribute("data-track") ?? "?";
  });
}

/** 무대 머리의 「N마디」 — 지금 보는 마디. */
function stageTitle(): string {
  return container.querySelector("h5.beat-grid-stage-title")?.textContent ?? "";
}

/** 큐 편집 칸 머리 글자(「AAA · Cue 1 '칸0'」…) — 편집 칸이 펼쳐 보이는 줄을 가린다. */
function panelHeading(): string {
  return container.querySelector("aside.beat-grid-cue-panel header span")?.textContent ?? "";
}

/** 밝기 「값 ▾」에서 값을 고르고 밝기 「적용」을 누른다. */
function applyBrightness(percent: number) {
  const select = container.querySelector<HTMLSelectElement>('select[aria-label="밝기 값(%)"]');
  if (!select) throw new Error("brightness value select not found");
  act(() => {
    select.value = String(percent);
    select.dispatchEvent(new Event("change", { bubbles: true }));
  });
  const apply = Array.from(container.querySelectorAll('.beat-grid-cue-field[data-field="밝기"] button')).find(
    (button) => button.textContent === "적용",
  );
  if (!apply) throw new Error("brightness apply button not found");
  act(() => (apply as HTMLButtonElement).click());
}

function nextBar(times: number) {
  const next = container.querySelector<HTMLButtonElement>('button[title="다음 마디 (→)"]');
  if (!next) throw new Error("next-bar button not found");
  for (let i = 0; i < times; i += 1) act(() => next.click());
}

/** 모든 줄의 첫 칸이 0마디에서 시작한다 — 어느 마디를 봐도 줄마다 같은 칸을 가리킨다. */
const ALIGNED = () => [track("AAA", [0]), track("BBB", [0]), track("CCC", [0])];

describe("무대 클릭 — 고른 줄", () => {
  it("보통 클릭은 그 줄 하나로 바꾸고, 그 줄이 편집 칸에 펼쳐진다", () => {
    mount(ALIGNED());
    expect(outlined()).toEqual([]);
    stageClick("AAA");
    expect(outlined()).toEqual(["AAA"]);
    expect(panelHeading()).toMatch(/^AAA · Cue 1/);
    stageClick("BBB");
    expect(outlined()).toEqual(["BBB"]);
    expect(panelHeading()).toMatch(/^BBB · Cue 1/);
  });

  it("Shift+클릭은 고른 줄에 더하고, 더한 줄이 편집 칸에 펼쳐진다 — 점선은 고른 줄 전부에 둘린다", () => {
    mount(ALIGNED());
    stageClick("AAA");
    stageClick("BBB", true);
    expect(outlined()).toEqual(["AAA", "BBB"]);
    expect(panelHeading()).toMatch(/^BBB · /);
    stageClick("CCC", true);
    expect(outlined()).toEqual(["AAA", "BBB", "CCC"]);
    expect(panelHeading()).toMatch(/^CCC · /);
  });

  it("Shift+클릭으로 든 줄을 다시 누르면 뺀다 — 편집 칸은 남은 줄의 마지막으로 옮겨 간다", () => {
    mount(ALIGNED());
    stageClick("AAA");
    stageClick("BBB", true);
    stageClick("CCC", true);
    stageClick("BBB", true);
    expect(outlined()).toEqual(["AAA", "CCC"]);
    expect(panelHeading()).toMatch(/^CCC · /);
  });

  it("마지막 한 줄은 Shift+클릭으로도 못 뺀다", () => {
    mount(ALIGNED());
    stageClick("AAA");
    stageClick("AAA", true);
    expect(outlined()).toEqual(["AAA"]);
    expect(panelHeading()).toMatch(/^AAA · /);
  });

  it("여럿 골라 둔 뒤 보통 클릭하면 그 줄 하나로 돌아간다", () => {
    mount(ALIGNED());
    stageClick("AAA");
    stageClick("BBB", true);
    stageClick("CCC");
    expect(outlined()).toEqual(["CCC"]);
  });

  it("지금 마디에 칸이 없는 줄은 눌러도 아무 일 없다 — Shift+클릭도 마찬가지", () => {
    mount([track("AAA", [0]), track("LATE", [6])]);
    stageClick("AAA");
    stageClick("LATE", true);
    expect(outlined()).toEqual(["AAA"]);
    expect(panelHeading()).toMatch(/^AAA · /);
  });

  it("타임라인의 칸을 누르면 고른 줄이 비워지고 그 칸 하나만 남는다", () => {
    mount(ALIGNED());
    stageClick("AAA");
    stageClick("BBB", true);
    expect(outlined()).toEqual(["AAA", "BBB"]);
    const timelineCue = container.querySelectorAll<HTMLButtonElement>("button.beat-grid-cue")[2]; // CCC 의 첫 칸
    act(() => timelineCue.click());
    expect(panelHeading()).toMatch(/^CCC · /);
    // 점선은 고른 칸의 줄(CCC) 하나뿐이다.
    expect(outlined()).toEqual(["CCC"]);
  });

  it("편집 칸의 ✕ 로 닫으면 고른 줄도 비워진다", () => {
    mount(ALIGNED());
    stageClick("AAA");
    stageClick("BBB", true);
    const close = container.querySelector<HTMLButtonElement>('aside.beat-grid-cue-panel button[aria-label="닫기"]');
    act(() => close?.click());
    expect(outlined()).toEqual([]);
    expect(container.querySelector("aside.beat-grid-cue-panel header")).toBeNull();
    // 닫은 뒤 Shift+클릭은 닫기 전 줄을 되살리지 않는다.
    stageClick("CCC", true);
    expect(outlined()).toEqual(["CCC"]);
  });
});

describe("큐 편집 칸 「적용」 — 고른 줄 전부", () => {
  it("줄을 안 골랐으면(타임라인 칸 하나) 그 칸 하나에만 보낸다 — 기존과 같다", () => {
    const { onEditRequest } = mount(ALIGNED());
    act(() => container.querySelectorAll<HTMLButtonElement>("button.beat-grid-cue")[1].click()); // BBB 의 첫 칸
    applyBrightness(60);
    expect(onEditRequest.mock.calls).toEqual([
      [{ bar: 0, target: "BBB", changes: buildBrightnessValueChanges(60) }],
    ]);
  });

  it("무대에서 한 줄만 보통 클릭했어도 그 칸 하나에만 보낸다", () => {
    const { onEditRequest } = mount(ALIGNED());
    stageClick("CCC");
    applyBrightness(25);
    expect(onEditRequest.mock.calls).toEqual([
      [{ bar: 0, target: "CCC", changes: buildBrightnessValueChanges(25) }],
    ]);
  });

  it("무대에서 셋을 골랐으면 줄마다 요청 하나씩, 고른 순서대로 같은 변경을 보낸다", () => {
    const { onEditRequest } = mount(ALIGNED());
    stageClick("BBB");
    stageClick("AAA", true);
    stageClick("CCC", true);
    applyBrightness(60);
    const changes = buildBrightnessValueChanges(60);
    expect(onEditRequest.mock.calls).toEqual([
      [{ bar: 0, target: "BBB", changes }],
      [{ bar: 0, target: "AAA", changes }],
      [{ bar: 0, target: "CCC", changes }],
    ]);
  });

  it("뺀 줄에는 보내지 않는다", () => {
    const { onEditRequest } = mount(ALIGNED());
    stageClick("AAA");
    stageClick("BBB", true);
    stageClick("CCC", true);
    stageClick("BBB", true);
    applyBrightness(40);
    expect(onEditRequest.mock.calls.map(([request]) => request.target)).toEqual(["AAA", "CCC"]);
  });

  it("봐 둔 마디를 옮기면 고른 줄은 그대로 두고, 그 마디에 걸친 칸을 따라가며 편집 칸의 칸도 함께 보낸다", () => {
    // AAA: 0·4 / BBB: 0·2 — 마디 5 에서는 AAA 의 4 칸, BBB 의 2 칸이 걸친다.
    const { onEditRequest } = mount([track("AAA", [0, 4]), track("BBB", [0, 2])]);
    stageClick("AAA");
    stageClick("BBB", true);
    nextBar(5);
    expect(outlined()).toEqual(["AAA", "BBB"]);
    applyBrightness(70);
    const changes = buildBrightnessValueChanges(70);
    expect(onEditRequest.mock.calls).toEqual([
      [{ bar: 4, target: "AAA", changes }],
      [{ bar: 2, target: "BBB", changes }],
      // 편집 칸이 펼쳐 보이던 칸(BBB 0마디)은 줄을 고른 것과 별개로 늘 포함된다.
      [{ bar: 0, target: "BBB", changes }],
    ]);
  });
});

// 줄마다 칸이 시작하는 마디가 다르면, 클릭할 때마다 보던 마디가 그 칸의 시작 마디로 끌려가는 순간 「적용」이
// 닿는 칸이 사용자가 보던 마디가 아닌 앞 칸으로 밀려난다(실측: 5마디를 보다가 AAA·BBB·CCC 를 고르면
// AAA@0·BBB@0·CCC@0 으로 갔다). 무대 클릭은 보던 마디를 옮기지 않아야 한다.
describe("무대 클릭은 보던 마디를 옮기지 않는다", () => {
  // 5마디에 걸친 칸: AAA 는 4, BBB 는 2, CCC 는 0.
  const STAGGERED = () => [track("AAA", [0, 4]), track("BBB", [0, 2]), track("CCC", [0, 6])];

  it("보통 클릭도 Shift+클릭도 무대 머리의 「N마디」를 그대로 둔다", () => {
    mount(STAGGERED());
    nextBar(5);
    expect(stageTitle()).toContain("5마디");
    stageClick("AAA");
    expect(stageTitle()).toContain("5마디");
    expect(panelHeading()).toMatch(/^AAA · Cue 2 '칸4'/); // 5마디에 걸친 칸이 펼쳐진다
    stageClick("BBB", true);
    expect(stageTitle()).toContain("5마디");
    expect(panelHeading()).toMatch(/^BBB · Cue 2 '칸2'/);
    stageClick("CCC", true);
    expect(stageTitle()).toContain("5마디");
    expect(panelHeading()).toMatch(/^CCC · Cue 1 '칸0'/);
  });

  it("칸이 시작하는 마디가 줄마다 달라도 「적용」은 보던 마디에 걸친 칸 하나씩에 간다", () => {
    const { onEditRequest } = mount(STAGGERED());
    nextBar(5);
    stageClick("AAA");
    stageClick("BBB", true);
    stageClick("CCC", true);
    applyBrightness(60);
    const changes = buildBrightnessValueChanges(60);
    expect(onEditRequest.mock.calls).toEqual([
      [{ bar: 4, target: "AAA", changes }],
      [{ bar: 2, target: "BBB", changes }],
      [{ bar: 0, target: "CCC", changes }],
    ]);
  });

  it("보통 클릭 한 줄도 보던 마디에 걸친 칸에 간다", () => {
    const { onEditRequest } = mount(STAGGERED());
    nextBar(5);
    stageClick("AAA");
    applyBrightness(25);
    expect(onEditRequest.mock.calls).toEqual([
      [{ bar: 4, target: "AAA", changes: buildBrightnessValueChanges(25) }],
    ]);
  });

  it("무대를 누른 뒤 ◀▶ 로 마디를 옮기면 그 마디를 따라간다", () => {
    mount(STAGGERED());
    nextBar(5);
    stageClick("AAA");
    nextBar(2);
    expect(stageTitle()).toContain("7마디");
  });
});

describe("「⇪ 콘솔에 반영」은 무대 선택과 무관하다", () => {
  it("줄을 골라도 큐 편집 칸 머리의 반영 버튼은 그대로 있다", () => {
    mount(ALIGNED());
    stageClick("AAA");
    stageClick("BBB", true);
    const first = container.querySelector("aside.beat-grid-cue-panel")?.firstElementChild;
    expect(first?.classList.contains("beat-grid-console-apply")).toBe(true);
    expect(first?.querySelector("button")?.textContent).toContain("⇪ 콘솔에 반영");
  });
});
