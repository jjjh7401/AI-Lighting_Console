// 타임라인 칸 여러 개 고르기 — 순수 함수 시험(카드 WT-cell-apply). 사각형(줄 × 마디), 기준 칸 방향, 빈 범위,
// 범위 안에 칸이 없는 줄, 토글과 기준 규칙, 서버 `cells` 변환.
import { describe, expect, it } from "vitest";

import type { BeatGridCue, BeatGridTrack } from "../../protocol";
import {
  CELL_WIRE_MAX,
  EMPTY_CELL_SELECTION,
  applyCellClick,
  cellClickMode,
  cellKey,
  existingCells,
  rectangleCells,
  skippedBarNote,
  toggleCell,
  wireCells,
  type CellSelection,
  type CueCell,
} from "./cellSelection";

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

const cellOf = (group_name: string, bar: number): CueCell => ({ group_name, bar });
const pairs = (cells: readonly CueCell[]) => cells.map((cell) => `${cell.group_name}@${cell.bar}`);

// A: 0 2 4 6 / B: 0 3 6 / C: 1 2 5 / D: (칸 없음)
const ROWS = [track("A", [0, 2, 4, 6]), track("B", [0, 3, 6]), track("C", [1, 2, 5]), track("D", [])];

describe("cellClickMode", () => {
  const keys = (shiftKey = false, ctrlKey = false, metaKey = false) => ({ shiftKey, ctrlKey, metaKey });

  it("수정키가 없으면 보통 클릭이다", () => {
    expect(cellClickMode(keys())).toBe("plain");
  });

  it("Shift 는 범위, Ctrl 과 Cmd 는 토글이다", () => {
    expect(cellClickMode(keys(true))).toBe("range");
    expect(cellClickMode(keys(false, true))).toBe("toggle");
    expect(cellClickMode(keys(false, false, true))).toBe("toggle");
  });

  it("Shift 와 Ctrl 을 함께 누르면 Shift(범위)가 이긴다", () => {
    expect(cellClickMode(keys(true, true))).toBe("range");
    expect(cellClickMode(keys(true, false, true))).toBe("range");
  });
});

describe("rectangleCells — 줄 × 마디 사각형", () => {
  it("기준과 누른 칸 사이의 줄 전부, 칸이 시작하는 마디가 두 마디 사이(양끝 포함)인 칸만 줄 위→아래·마디 앞→뒤로 모은다", () => {
    const cells = rectangleCells(ROWS, cellOf("A", 2), cellOf("C", 5));
    expect(pairs(cells)).toEqual(["A@2", "A@4", "B@3", "C@2", "C@5"]);
  });

  it("기준이 오른쪽 아래, 누른 칸이 왼쪽 위여도 같은 칸이 같은 순서로 모인다", () => {
    const forward = rectangleCells(ROWS, cellOf("A", 2), cellOf("C", 5));
    const reversed = rectangleCells(ROWS, cellOf("C", 5), cellOf("A", 2));
    expect(pairs(reversed)).toEqual(pairs(forward));
    // 줄은 위→아래인데 마디만 거꾸로인 대각선(왼쪽 아래 → 오른쪽 위)도 같은 사각형이다.
    expect(pairs(rectangleCells(ROWS, cellOf("C", 2), cellOf("A", 4)))).toEqual(["A@2", "A@4", "B@3", "C@2"]);
    expect(pairs(rectangleCells(ROWS, cellOf("A", 4), cellOf("C", 2)))).toEqual(["A@2", "A@4", "B@3", "C@2"]);
  });

  it("같은 칸을 기준과 누른 칸으로 주면 그 칸 하나다", () => {
    expect(pairs(rectangleCells(ROWS, cellOf("B", 3), cellOf("B", 3)))).toEqual(["B@3"]);
  });

  it("같은 줄 안에서는 마디 범위의 칸만 모은다", () => {
    expect(pairs(rectangleCells(ROWS, cellOf("A", 2), cellOf("A", 6)))).toEqual(["A@2", "A@4", "A@6"]);
  });

  it("범위 안에 칸이 하나도 없는 줄은 건너뛴다 — 칸을 지어내지 않는다", () => {
    // 마디 4~5: A 는 4, B 는 칸 없음(3·6 은 밖), C 는 5.
    const cells = rectangleCells(ROWS, cellOf("A", 4), cellOf("C", 5));
    expect(pairs(cells)).toEqual(["A@4", "C@5"]);
    // 칸이 전혀 없는 줄(D)이 사이에 있어도 건너뛴다.
    expect(pairs(rectangleCells(ROWS, cellOf("C", 1), cellOf("D", 5)))).toEqual(["C@1", "C@2", "C@5"]);
  });

  it("빈 범위는 빈 목록이다 — 두 마디 사이에 칸이 없다", () => {
    // 마디 7~8 에는 어느 줄에도 칸이 없다.
    expect(rectangleCells(ROWS, cellOf("A", 7), cellOf("C", 8))).toEqual([]);
  });

  it("기준이나 누른 칸의 줄이 보이는 줄 목록에 없으면 빈 목록이다", () => {
    expect(rectangleCells(ROWS, cellOf("ZZZ", 2), cellOf("C", 5))).toEqual([]);
    expect(rectangleCells(ROWS, cellOf("A", 2), cellOf("ZZZ", 5))).toEqual([]);
    expect(rectangleCells([], cellOf("A", 2), cellOf("A", 4))).toEqual([]);
  });

  it("줄 순서는 호출부가 넘긴 화면 순서를 따른다 — 사이에 낀 줄만 들어간다", () => {
    const visual = [ROWS[0], ROWS[2], ROWS[1]]; // A, C, B
    expect(pairs(rectangleCells(visual, cellOf("A", 0), cellOf("C", 1)))).toEqual(["A@0", "C@1"]);
    expect(pairs(rectangleCells(visual, cellOf("A", 0), cellOf("B", 3)))).toEqual(["A@0", "A@2", "C@1", "C@2", "B@0", "B@3"]);
  });

  it("받은 줄 목록은 고치지 않는다", () => {
    const before = JSON.stringify(ROWS);
    rectangleCells(ROWS, cellOf("A", 2), cellOf("C", 5));
    expect(JSON.stringify(ROWS)).toBe(before);
  });
});

describe("toggleCell", () => {
  it("없는 칸은 끝에 더하고 든 칸은 뺀다", () => {
    const one = toggleCell([], cellOf("A", 2));
    expect(pairs(one)).toEqual(["A@2"]);
    const two = toggleCell(one, cellOf("B", 3));
    expect(pairs(two)).toEqual(["A@2", "B@3"]);
    expect(pairs(toggleCell(two, cellOf("A", 2)))).toEqual(["B@3"]);
  });

  it("같은 줄의 다른 마디는 다른 칸이다", () => {
    expect(pairs(toggleCell([cellOf("A", 2)], cellOf("A", 4)))).toEqual(["A@2", "A@4"]);
  });

  it("받은 목록은 고치지 않는다", () => {
    const held = [cellOf("A", 2)];
    toggleCell(held, cellOf("A", 2));
    toggleCell(held, cellOf("B", 3));
    expect(pairs(held)).toEqual(["A@2"]);
  });
});

describe("applyCellClick — 클릭 하나가 고른 칸을 바꾸는 법", () => {
  const ctx = (selected: CueCell | null) => ({ rows: ROWS, selected });

  it("범위: 편집 칸의 선택(기준 없음)에서 누른 칸까지의 사각형으로 바꾸고, 기준은 그 선택이 된다", () => {
    const next = applyCellClick(EMPTY_CELL_SELECTION, "range", cellOf("C", 5), ctx(cellOf("A", 2)));
    expect(pairs(next.cells)).toEqual(["A@2", "A@4", "B@3", "C@2", "C@5"]);
    expect(next.anchor).toEqual(cellOf("A", 2));
  });

  it("범위: 다시 Shift+클릭하면 같은 기준에서 새 사각형으로 바꾼다(더하지 않는다)", () => {
    const first = applyCellClick(EMPTY_CELL_SELECTION, "range", cellOf("C", 5), ctx(cellOf("A", 2)));
    const second = applyCellClick(first, "range", cellOf("B", 3), ctx(cellOf("A", 2)));
    // A@2 에서 B@3 까지 — 마디 2~3 안에 칸이 있는 건 A@2 와 B@3 뿐이다(앞서 골랐던 A@4·C 칸은 빠진다).
    expect(pairs(second.cells)).toEqual(["A@2", "B@3"]);
    expect(second.anchor).toEqual(cellOf("A", 2));
  });

  it("범위: 기준(Ctrl 로 마지막에 누른 칸)이 편집 칸의 선택보다 앞선다", () => {
    const state: CellSelection = { cells: [cellOf("B", 3)], anchor: cellOf("B", 3) };
    const next = applyCellClick(state, "range", cellOf("C", 5), ctx(cellOf("A", 0)));
    expect(pairs(next.cells)).toEqual(["B@3", "C@5"]);
    expect(next.anchor).toEqual(cellOf("B", 3));
  });

  it("범위: 기준도 선택도 없으면 누른 칸 하나를 고르고 그 칸이 기준이 된다", () => {
    const next = applyCellClick(EMPTY_CELL_SELECTION, "range", cellOf("B", 3), ctx(null));
    expect(pairs(next.cells)).toEqual(["B@3"]);
    expect(next.anchor).toEqual(cellOf("B", 3));
  });

  it("범위: 사각형을 못 그리면(기준 줄이 안 보임) 누른 칸 하나만 고른다", () => {
    const next = applyCellClick(EMPTY_CELL_SELECTION, "range", cellOf("C", 5), ctx(cellOf("HIDDEN", 2)));
    expect(pairs(next.cells)).toEqual(["C@5"]);
  });

  it("토글: 처음 Ctrl+클릭은 편집 칸의 선택을 먼저 넣고 시작한다 — 보통 클릭한 칸이 빠지지 않는다", () => {
    const next = applyCellClick(EMPTY_CELL_SELECTION, "toggle", cellOf("B", 3), ctx(cellOf("A", 2)));
    expect(pairs(next.cells)).toEqual(["A@2", "B@3"]);
    expect(next.anchor).toEqual(cellOf("B", 3));
  });

  it("토글: 선택이 없으면 누른 칸 하나로 시작한다", () => {
    const next = applyCellClick(EMPTY_CELL_SELECTION, "toggle", cellOf("B", 3), ctx(null));
    expect(pairs(next.cells)).toEqual(["B@3"]);
  });

  it("토글: 든 칸을 다시 누르면 빠지고, 다 빠져 비어도 선택을 다시 끼워 넣지 않는다", () => {
    const first = applyCellClick(EMPTY_CELL_SELECTION, "toggle", cellOf("A", 2), ctx(cellOf("A", 2)));
    // 시작 선택(A@2)을 넣은 뒤 같은 칸을 누르니 빠져 비었다.
    expect(first.cells).toEqual([]);
    expect(first.anchor).toEqual(cellOf("A", 2));
    const second = applyCellClick(first, "toggle", cellOf("B", 3), ctx(cellOf("A", 2)));
    expect(pairs(second.cells)).toEqual(["B@3"]);
  });

  it("토글 뒤 Shift+클릭은 토글로 누른 마지막 칸에서 사각형을 그린다", () => {
    const toggled = applyCellClick(EMPTY_CELL_SELECTION, "toggle", cellOf("B", 3), ctx(null));
    const ranged = applyCellClick(toggled, "range", cellOf("C", 5), ctx(null));
    // B@3 에서 C@5 까지 — B 는 3, C 는 5 만 마디 3~5 안에 칸이 있다.
    expect(pairs(ranged.cells)).toEqual(["B@3", "C@5"]);
  });

  it("받은 상태는 고치지 않는다", () => {
    const state: CellSelection = { cells: [cellOf("A", 2)], anchor: cellOf("A", 2) };
    applyCellClick(state, "toggle", cellOf("B", 3), ctx(null));
    applyCellClick(state, "range", cellOf("C", 5), ctx(null));
    expect(pairs(state.cells)).toEqual(["A@2"]);
    expect(pairs(EMPTY_CELL_SELECTION.cells)).toEqual([]);
  });
});

describe("existingCells — 격자에서 사라진 칸은 빠진다", () => {
  it("지금 격자에 줄과 마디가 있는 칸만 남는다", () => {
    const held = [cellOf("A", 2), cellOf("A", 3), cellOf("GONE", 1), cellOf("B", 3)];
    expect(pairs(existingCells(held, ROWS))).toEqual(["A@2", "B@3"]);
  });

  it("고른 칸이 없으면 빈 목록이다", () => {
    expect(existingCells([], ROWS)).toEqual([]);
  });

  it("줄 이름이 같은 줄이 둘이면 두 줄의 마디를 합쳐서 본다", () => {
    const twins = [track("A", [1]), track("A", [5])];
    expect(pairs(existingCells([cellOf("A", 1), cellOf("A", 5), cellOf("A", 3)], twins))).toEqual(["A@1", "A@5"]);
  });
});

describe("wireCells — 서버 cells 로 보낼 목록", () => {
  it("[줄 이름, 마디] 쌍으로 바꾼다", () => {
    expect(wireCells([cellOf("A", 2), cellOf("B", 3)])).toEqual({
      cells: [
        ["A", 2],
        ["B", 3],
      ],
      skipped: 0,
    });
  });

  it("서버가 받지 못하는 0마디(앞박) 칸은 빼고 몇 개 뺐는지 센다", () => {
    expect(wireCells([cellOf("A", 0), cellOf("A", 2), cellOf("B", 0)])).toEqual({ cells: [["A", 2]], skipped: 2 });
  });

  it("정수가 아닌 마디도 뺀다", () => {
    expect(wireCells([cellOf("A", 1.5), cellOf("A", 2)])).toEqual({ cells: [["A", 2]], skipped: 1 });
  });

  it("상한은 서버의 BEAT_GRID_CELLS_MAX 와 같은 400 이다", () => {
    expect(CELL_WIRE_MAX).toBe(400);
  });

  it("뺀 칸 안내는 반영과 일괄 바꾸기에서 동사만 다르다", () => {
    expect(skippedBarNote(2)).toBe("0마디(앞박) 칸 2개는 칸 단위로 보낼 수 없어요");
    expect(skippedBarNote(2, "edit")).toBe("0마디(앞박) 칸 2개는 칸 단위로 바꿀 수 없어요");
  });
});

describe("cellKey", () => {
  it("cueEditKey 와 같은 「줄|마디」 꼴이다", () => {
    expect(cellKey(cellOf("BACK", 3))).toBe("BACK|3");
  });
});
