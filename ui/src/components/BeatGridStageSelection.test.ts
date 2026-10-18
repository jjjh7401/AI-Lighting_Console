// 무대에서 고른 줄 — 순수 함수 시험: `toggleStageRow`(Shift+클릭으로 더하고 빼기)와
// `stageSelectionCells`(「적용」이 닿는 칸들). 화면 쪽 배선은 `BeatGrid.stageSelect.test.tsx` 가 잰다.
import { describe, expect, it } from "vitest";

import type { BeatGridCue, BeatGridTrack } from "../protocol";
import { stageSelectionCells, toggleStageRow } from "./BeatGrid";

function cue(bar: number): BeatGridCue {
  return {
    bar,
    label: `칸${bar}`,
    brightness: { mode: null, value_percent: null, preset_no: null },
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

describe("toggleStageRow", () => {
  it("없던 줄은 맨 뒤에 더한다", () => {
    expect(toggleStageRow([], 2)).toEqual([2]);
    expect(toggleStageRow([0, 1], 3)).toEqual([0, 1, 3]);
  });

  it("든 줄은 뺀다 — 나머지 순서는 그대로", () => {
    expect(toggleStageRow([0, 1, 2], 1)).toEqual([0, 2]);
    expect(toggleStageRow([4, 5], 4)).toEqual([5]);
  });

  it("든 줄이 하나뿐이면 못 뺀다 — 그대로 돌려준다", () => {
    expect(toggleStageRow([3], 3)).toEqual([3]);
  });

  it("받은 배열을 고치지 않는다(더할 때도 뺄 때도 못 뺄 때도)", () => {
    const rows = Object.freeze([0, 1]) as readonly number[];
    expect(toggleStageRow(rows, 2)).toEqual([0, 1, 2]);
    expect(toggleStageRow(rows, 0)).toEqual([1]);
    expect(rows).toEqual([0, 1]);
    const single = Object.freeze([7]) as readonly number[];
    const same = toggleStageRow(single, 7);
    expect(same).toEqual([7]);
    expect(single).toEqual([7]);
    // 돌려준 배열을 고쳐도 받은 배열에 번지지 않는다.
    same.push(9);
    expect(single).toEqual([7]);
  });
});

describe("stageSelectionCells", () => {
  const tracks = [
    track("A", [0, 4]), // 마디 5 → 4 칸
    track("B", [0, 8]), // 마디 5 → 0 칸
    track("C", [6]), // 마디 5 → 칸 없음(첫 칸이 6)
    track("D", [2]), // 마디 5 → 2 칸
  ];
  const viewBar = 5;

  it("고른 줄은 고른 순서대로, 줄마다 지금 마디에 걸친 칸의 시작 마디로 센다", () => {
    expect(stageSelectionCells([3, 0, 1], null, tracks, viewBar)).toEqual([
      { trackIndex: 3, bar: 2 },
      { trackIndex: 0, bar: 4 },
      { trackIndex: 1, bar: 0 },
    ]);
  });

  it("편집 칸이 펼쳐 보이는 칸(focus)은 맨 뒤에 붙는다", () => {
    expect(stageSelectionCells([0], { trackIndex: 3, bar: 2 }, tracks, viewBar)).toEqual([
      { trackIndex: 0, bar: 4 },
      { trackIndex: 3, bar: 2 },
    ]);
  });

  it("focus 가 고른 줄의 칸과 같은 (줄, 마디)면 한 번만 센다", () => {
    expect(stageSelectionCells([0, 1], { trackIndex: 0, bar: 4 }, tracks, viewBar)).toEqual([
      { trackIndex: 0, bar: 4 },
      { trackIndex: 1, bar: 0 },
    ]);
  });

  it("같은 줄이어도 마디가 다르면 다른 칸이다 — focus 가 그 줄의 다른 칸이면 둘 다 센다", () => {
    expect(stageSelectionCells([0], { trackIndex: 0, bar: 0 }, tracks, viewBar)).toEqual([
      { trackIndex: 0, bar: 4 },
      { trackIndex: 0, bar: 0 },
    ]);
  });

  it("지금 마디에 칸이 없는 줄은 건너뛴다", () => {
    expect(stageSelectionCells([2, 0], null, tracks, viewBar)).toEqual([{ trackIndex: 0, bar: 4 }]);
    expect(stageSelectionCells([2], null, tracks, viewBar)).toEqual([]);
  });

  it("범위 밖 줄 번호는 건너뛴다", () => {
    expect(stageSelectionCells([9, -1, 0], null, tracks, viewBar)).toEqual([{ trackIndex: 0, bar: 4 }]);
  });

  it("고른 줄이 없으면 focus 하나뿐이다 — 한 칸 편집과 같다", () => {
    expect(stageSelectionCells([], { trackIndex: 1, bar: 8 }, tracks, viewBar)).toEqual([{ trackIndex: 1, bar: 8 }]);
  });

  it("focus 도 고른 줄도 없으면 비어 있다", () => {
    expect(stageSelectionCells([], null, tracks, viewBar)).toEqual([]);
  });

  it("같은 줄을 두 번 골라도 한 번만 센다", () => {
    expect(stageSelectionCells([0, 0], null, tracks, viewBar)).toEqual([{ trackIndex: 0, bar: 4 }]);
  });

  it("받은 배열·focus 를 고치지 않는다", () => {
    const rows = Object.freeze([0, 1]) as readonly number[];
    const focus = Object.freeze({ trackIndex: 3, bar: 2 });
    stageSelectionCells(rows, focus, tracks, viewBar);
    expect(rows).toEqual([0, 1]);
    expect(focus).toEqual({ trackIndex: 3, bar: 2 });
  });
});
