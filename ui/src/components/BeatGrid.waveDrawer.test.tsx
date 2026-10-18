// @vitest-environment jsdom
// 칸을 여럿 고른 뒤 프리셋 서랍을 열면 웨이브 직접 만들기의 「선택한 칸 N개에도 적용」이 보이는지 — 실제 `<BeatGrid>` 를 그려
// Cmd(Ctrl) 클릭으로 칸을 고르고 서랍 단추(▤ 프리셋 서랍 · 📁 프리셋)를 누른다(시험 결함 2, 리드 실기 시험).
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { BeatGridCue, BeatGridDrawerSection, BeatGridTrack, BeatGridView } from "../protocol";
import { BeatGrid, type BeatGridFixturePoint } from "./BeatGrid";

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
    entries: [{ preset_no: "1.1", name: "Full", usage_count: 1, used_by: [], is_effect_band: false }],
  },
];

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

/** 세 줄 모두 1·3·5 마디에서 시작하는 칸 — 칸 막대는 줄 순서대로 아홉 개다. */
const THREE_BY_THREE = () => [track("AAA", [1, 3, 5]), track("BBB", [1, 3, 5]), track("CCC", [1, 3, 5])];

function setup(tracks: BeatGridTrack[]) {
  const handlers = {
    onEditRequest: vi.fn(),
    onEditCellsRequest: vi.fn(),
    onApply: vi.fn(),
    onApplyCells: vi.fn(),
    onPreviewBar: vi.fn(),
    onDrawerRequest: vi.fn(),
    onWavePresetRequest: vi.fn(),
    onWaveCustomRequest: vi.fn(),
  };
  act(() =>
    root.render(
      <BeatGrid
        grid={gridOf(tracks)}
        fixtures={fixturesOf(tracks.map((t) => t.group_name))}
        drawerSections={DRAWER}
        {...handlers}
      />,
    ),
  );
  return handlers;
}

const cueButtons = () => Array.from(container.querySelectorAll<HTMLButtonElement>("button.beat-grid-cue"));
/** 줄 번호(0부터)와 칸 번호(0부터)로 칸 막대를 누른다. */
function clickCue(row: number, col: number, keys: { meta?: boolean } = {}, perRow = 3) {
  const button = cueButtons()[row * perRow + col];
  if (!button) throw new Error(`cue button not found: ${row},${col}`);
  act(() => {
    button.dispatchEvent(new MouseEvent("click", { bubbles: true, metaKey: !!keys.meta }));
  });
}
const multiCount = () => container.querySelectorAll("button.beat-grid-cue.is-multi").length;
/** 프리셋 서랍을 여는 단추 — 위 상단 바(`▤ 프리셋 서랍`) 또는 명령창 줄(`📁 프리셋`). */
function drawerButton(title: string): HTMLButtonElement {
  const button = container.querySelector<HTMLButtonElement>(`button[title^="${title}"]`);
  if (!button) throw new Error(`drawer button not found: ${title}`);
  return button;
}
function pressDrawer(title: string) {
  act(() => {
    drawerButton(title).dispatchEvent(new MouseEvent("click", { bubbles: true }));
  });
}

describe("칸을 여럿 고른 뒤 프리셋 서랍 — 웨이브 직접 만들기의 칸 적용", () => {
  it("Cmd 로 두 칸을 고르면 칸 두 개가 표시되고 일괄 바꾸기 줄이 보인다(서랍을 열기 전)", () => {
    setup(THREE_BY_THREE());
    clickCue(0, 0);
    clickCue(1, 0, { meta: true });
    expect(multiCount()).toBe(2);
  });

  it("상단 바 「▤ 프리셋 서랍」을 열면 고른 두 칸이 그대로이고 「선택한 칸 2개에도 적용」이 보인다", () => {
    setup(THREE_BY_THREE());
    clickCue(0, 0);
    clickCue(1, 0, { meta: true });
    pressDrawer("▤ 프리셋 서랍");
    expect(multiCount()).toBe(2);
    expect(container.textContent).toContain("선택한 칸 2개에도 적용");
  });

  it("명령창 「📁 프리셋」을 열어도 고른 두 칸이 서랍에 넘어가 「선택한 칸 2개에도 적용」이 보인다", () => {
    setup(THREE_BY_THREE());
    clickCue(0, 0);
    clickCue(1, 0, { meta: true });
    pressDrawer("풀별");
    expect(multiCount()).toBe(2);
    expect(container.textContent).toContain("선택한 칸 2개에도 적용");
  });

  it("앞박(0마디) 칸만 고른 채 서랍을 열면 칸 적용 자리에 그 이유가 보인다 — 조용히 빠지지 않는다", () => {
    setup([track("AAA", [0, 2, 4]), track("BBB", [0, 2, 4]), track("CCC", [0, 2, 4])]);
    clickCue(0, 0);
    clickCue(1, 0, { meta: true });
    pressDrawer("▤ 프리셋 서랍");
    expect(container.textContent).not.toContain("선택한 칸");
    expect(container.textContent).toContain("0마디(앞박) 칸 2개는 칸 단위로 바꿀 수 없어요");
  });

  it("0마디 칸과 1마디 이상 칸을 섞어 고르면 체크는 보낼 칸만 세고, 빠진 칸 수를 말한다", () => {
    setup([track("AAA", [0, 2, 4]), track("BBB", [1, 3, 5]), track("CCC", [1, 3, 5])]);
    clickCue(0, 0);
    clickCue(1, 0, { meta: true });
    pressDrawer("▤ 프리셋 서랍");
    expect(container.textContent).toContain("선택한 칸 1개에도 적용");
    expect(container.textContent).toContain("0마디(앞박) 칸 1개는 칸 단위로 바꿀 수 없어요");
  });
});
