// 칸 하나의 왼쪽·오른쪽 따로 색(서버 `cue.split`) 순수 파생 시험 — 나뉜 칸 고르기, L·R 자식 줄 만들기.
// 그룹 이름·색 이름은 시험 자료다(앱 상수가 아니다).
import { describe, expect, it } from "vitest";

import type { BeatGridCue, BeatGridCueSplit } from "../../protocol";
import { cellSplitChildRows, cellSplitSegments, type CellSplitSegment } from "./cellSplit";

function cue(bar: number, split?: BeatGridCueSplit | null): BeatGridCue {
  return {
    bar,
    label: `칸 ${bar}`,
    brightness: { mode: null, value_percent: null, preset_no: null },
    position_preset_no: null,
    color_preset_no: null,
    effect_preset_no: null,
    effect_kind: null,
    entry: { fade_bars: null, mib_mode: null },
    source_ref: null,
    app_movement: null,
    evidence: null,
    ...(split === undefined ? {} : { split }),
  };
}

function segment(bar: number, endBar: number, split?: BeatGridCueSplit | null): CellSplitSegment {
  return { cue: cue(bar, split), startBar: bar, endBar };
}

const RED_BLUE: BeatGridCueSplit = {
  left: { color: "Red", color_rgb: [100, 0, 0] },
  right: { color: "Blue", color_rgb: [5, 20, 100] },
};

describe("cellSplitSegments — 나뉜 칸만 고른다", () => {
  it("split 이 없거나 null 인 칸은 거른다", () => {
    const plain = segment(0, 4);
    const nulled = segment(4, 8, null);
    const split = segment(8, 12, RED_BLUE);
    expect(cellSplitSegments([plain, nulled, split])).toEqual([split]);
  });

  it("받은 구간 객체를 그대로 돌려준다(복사하지 않는다) — 호출부가 includes 로 숨길 칸을 가린다", () => {
    const split = segment(8, 12, RED_BLUE);
    const [picked] = cellSplitSegments([segment(0, 8), split]);
    expect(picked).toBe(split);
  });

  it("나뉜 칸이 없으면 빈 배열이다", () => {
    expect(cellSplitSegments([segment(0, 4), segment(4, 8)])).toEqual([]);
    expect(cellSplitSegments([])).toEqual([]);
  });

  it("칸 순서를 지킨다", () => {
    const a = segment(2, 4, RED_BLUE);
    const b = segment(6, 9, RED_BLUE);
    expect(cellSplitSegments([a, segment(4, 6), b])).toEqual([a, b]);
  });
});

describe("cellSplitChildRows — L·R 두 줄", () => {
  const track = { group_name: "FOOBAR" };

  it("나뉜 칸이 없으면 빈 배열이다", () => {
    expect(cellSplitChildRows(track, [segment(0, 4), segment(4, 8)])).toEqual([]);
    expect(cellSplitChildRows(track, [])).toEqual([]);
  });

  it("줄 둘 — L 다음 R, 라벨은 그룹 이름을 그대로 잇는다", () => {
    const rows = cellSplitChildRows(track, [segment(0, 4), segment(4, 8, RED_BLUE)]);
    expect(rows.map((row) => [row.side, row.label])).toEqual([
      ["L", "FOOBAR L"],
      ["R", "FOOBAR R"],
    ]);
  });

  it("줄마다 나뉜 칸의 구간·색 이름·RGB 를 쪽에 맞춰 싣는다", () => {
    const [left, right] = cellSplitChildRows(track, [segment(0, 4), segment(4, 8, RED_BLUE)]);
    expect(left.cells).toEqual([{ startBar: 4, endBar: 8, color: "Red", color_rgb: [100, 0, 0] }]);
    expect(right.cells).toEqual([{ startBar: 4, endBar: 8, color: "Blue", color_rgb: [5, 20, 100] }]);
  });

  it("나뉜 칸이 여럿이면 칸 순서대로 줄마다 칸이 하나씩 늘어난다", () => {
    const other: BeatGridCueSplit = {
      left: { color: "Green", color_rgb: [0, 100, 10] },
      right: { color: "Amber", color_rgb: [100, 55, 5] },
    };
    const [left, right] = cellSplitChildRows(track, [
      segment(0, 4, RED_BLUE),
      segment(4, 8),
      segment(8, 12, other),
    ]);
    expect(left.cells.map((c) => [c.startBar, c.endBar, c.color])).toEqual([
      [0, 4, "Red"],
      [8, 12, "Green"],
    ]);
    expect(right.cells.map((c) => [c.startBar, c.endBar, c.color])).toEqual([
      [0, 4, "Blue"],
      [8, 12, "Amber"],
    ]);
  });

  it("색을 정하지 않은 쪽·RGB 를 못 푼 쪽은 null 로 남는다 — 지어내지 않는다", () => {
    const half: BeatGridCueSplit = {
      left: { color: "Red", color_rgb: [100, 0, 0] },
      right: { color: null, color_rgb: null },
    };
    const unresolved: BeatGridCueSplit = {
      left: { color: "no-such-color", color_rgb: null },
      right: { color: "Red" }, // color_rgb 키 자체가 없는 옛 응답
    };
    const [left, right] = cellSplitChildRows(track, [segment(0, 4, half), segment(4, 8, unresolved)]);
    expect(right.cells[0]).toEqual({ startBar: 0, endBar: 4, color: null, color_rgb: null });
    expect(left.cells[1]).toEqual({ startBar: 4, endBar: 8, color: "no-such-color", color_rgb: null });
    expect(right.cells[1]).toEqual({ startBar: 4, endBar: 8, color: "Red", color_rgb: null });
  });

  it("이미 걸러진 구간을 받아도 같은 결과다", () => {
    const all = [segment(0, 4), segment(4, 8, RED_BLUE)];
    expect(cellSplitChildRows(track, cellSplitSegments(all))).toEqual(cellSplitChildRows(track, all));
  });

  it("입력을 바꾸지 않는다", () => {
    const all = [segment(0, 4), segment(4, 8, RED_BLUE)];
    const before = JSON.stringify(all);
    cellSplitChildRows(track, all);
    expect(JSON.stringify(all)).toBe(before);
  });
});
