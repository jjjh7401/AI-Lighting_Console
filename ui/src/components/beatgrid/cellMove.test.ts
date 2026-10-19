// 칸 가로 끌기로 같은 줄에서 옮기기 — 순수 계산 시험(카드 WT-cell-edit-live, SPEC-LDRHYTHM-001).
// 실제 `<BeatGrid>` 에서 포인터를 끄는 시험은 `../BeatGrid.cellMove.test.tsx` 가 따로 본다. 여기서는 끌기 상태 전이와
// 어느 칸이 몇 마디 옮겨지는지를 DOM 없이 고정한다.
import { describe, expect, it } from "vitest";

import { SEAM_DRAG_THRESHOLD_PX } from "../beatGridSeam";
import {
  CELL_DRAG_THRESHOLD_PX,
  cellMoveOps,
  cellsToMove,
  reduceCellMove,
  type CellMoveEvent,
  type CellMoveOutcome,
  type CellMoveState,
} from "./cellMove";
import type { CueCell } from "./cellSelection";

const cell = (group_name: string, bar: number): CueCell => ({ group_name, bar });
const IDLE: CellMoveState = { phase: "idle" };

const down = (x: number, target: CueCell = cell("AAA", 5), pointerId = 1): CellMoveEvent => ({
  type: "down",
  pointerId,
  x,
  cell: target,
});
const move = (x: number, pointerId = 1): CellMoveEvent => ({ type: "move", pointerId, x });
const up = (x: number, extra: { pxPerBar?: number; picked?: readonly CueCell[]; pointerId?: number } = {}): CellMoveEvent => ({
  type: "up",
  pointerId: extra.pointerId ?? 1,
  x,
  pxPerBar: extra.pxPerBar ?? 42,
  picked: extra.picked ?? [],
});
const cancel = (pointerId = 1): CellMoveEvent => ({ type: "cancel", pointerId });

/** 이벤트를 차례로 먹여 마지막 결과를 돌려준다. */
function run(events: readonly CellMoveEvent[], from: CellMoveState = IDLE): CellMoveOutcome {
  let outcome: CellMoveOutcome = { state: from, ops: null, suppressClick: false };
  for (const event of events) outcome = reduceCellMove(outcome.state, event);
  return outcome;
}

describe("끌기 임계값", () => {
  it("이음매 끌기와 같은 3px 다 — 떨림을 끌기로 치지 않는 기준이 두 곳에서 어긋나지 않는다", () => {
    expect(CELL_DRAG_THRESHOLD_PX).toBe(3);
    expect(CELL_DRAG_THRESHOLD_PX).toBe(SEAM_DRAG_THRESHOLD_PX);
  });
});

describe("reduceCellMove — 상태 전이", () => {
  it("누르면 눌림 상태가 되고 아직 아무것도 보내지 않으며 클릭도 무시하지 않는다", () => {
    const outcome = run([down(100)]);
    expect(outcome.state).toEqual({ phase: "pressed", pointerId: 1, startX: 100, cell: cell("AAA", 5) });
    expect(outcome.ops).toBeNull();
    expect(outcome.suppressClick).toBe(false);
  });

  it("임계값 미만(2px)으로 움직이면 눌림 그대로고, 임계값(3px)에 닿는 순간 끌기가 된다", () => {
    expect(run([down(100), move(102)]).state.phase).toBe("pressed");
    expect(run([down(100), move(103)]).state.phase).toBe("dragging");
    expect(run([down(100), move(97)]).state.phase).toBe("dragging");
  });

  it("끌기가 된 뒤에는 시작점 근처로 돌아와도 끌기다 — 한 번 끈 손짓이 클릭으로 바뀌지 않는다", () => {
    expect(run([down(100), move(184), move(101)]).state.phase).toBe("dragging");
  });

  it("임계값을 넘지 않은 채 놓으면 보통 클릭이다 — 보내는 것도 클릭 무시도 없다", () => {
    const outcome = run([down(100), move(102), up(102)]);
    expect(outcome.state).toEqual(IDLE);
    expect(outcome.ops).toBeNull();
    expect(outcome.suppressClick).toBe(false);
  });

  it("마디 폭이 아주 좁아 2px 이 한 마디로 반올림되는 줄이어도 임계값 미만이면 옮기지 않는다 — 임계값이 따로 일한다", () => {
    // 마디 폭 1px: 반올림만 보면 2px = 2마디다. 그래도 끌기가 아니니 보내지 않고 클릭을 무시하지도 않는다.
    const outcome = run([down(100), up(102, { pxPerBar: 1 })]);
    expect(outcome.ops).toBeNull();
    expect(outcome.suppressClick).toBe(false);
    // 대조군: 임계값에 닿으면(3px) 같은 마디 폭에서 3마디로 옮겨진다.
    expect(run([down(100), up(103, { pxPerBar: 1 })]).ops).toEqual([
      { op: "move", group_name: "AAA", bar: 5, to_bar: 8 },
    ]);
  });

  it("끌어서 놓으면 끈 마디 수만큼 옮기는 목록을 내고 뒤따르는 클릭을 무시한다", () => {
    const outcome = run([down(100), move(130), move(184), up(184)]);
    expect(outcome.state).toEqual(IDLE);
    expect(outcome.ops).toEqual([{ op: "move", group_name: "AAA", bar: 5, to_bar: 7 }]);
    expect(outcome.suppressClick).toBe(true);
  });

  it("왼쪽으로 끌면 앞 마디로 옮긴다", () => {
    expect(run([down(200), move(116), up(116)]).ops).toEqual([{ op: "move", group_name: "AAA", bar: 5, to_bar: 3 }]);
  });

  it("움직임 이벤트 없이 놓더라도 놓는 자리가 임계값을 넘었으면 끌기로 본다 — 놓는 좌표가 결정한다", () => {
    const outcome = run([down(100), up(184)]);
    expect(outcome.ops).toEqual([{ op: "move", group_name: "AAA", bar: 5, to_bar: 7 }]);
    expect(outcome.suppressClick).toBe(true);
  });

  it("마디 수가 0 으로 반올림되는 끌기는 보내지 않지만 끌기는 끌기라서 클릭을 무시한다", () => {
    const outcome = run([down(100), move(115), up(115)]);
    expect(outcome.ops).toBeNull();
    expect(outcome.suppressClick).toBe(true);
  });

  it("옮길 자리가 1마디 미만이면 보내지 않지만 클릭은 무시한다", () => {
    const outcome = run([down(100, cell("AAA", 1)), move(58), up(58)]);
    expect(outcome.ops).toBeNull();
    expect(outcome.suppressClick).toBe(true);
  });

  it("끌었다가 마디 수가 0 으로 돌아와 놓아도 클릭을 무시한다", () => {
    const outcome = run([down(100), move(184), move(101), up(101)]);
    expect(outcome.ops).toBeNull();
    expect(outcome.suppressClick).toBe(true);
  });

  it("골라 둔 칸 안의 칸을 끌면 같은 줄의 고른 칸 전부를 같은 마디 수만큼 옮긴다", () => {
    const picked = [cell("AAA", 1), cell("AAA", 5), cell("BBB", 1)];
    const outcome = run([down(100), move(184), up(184, { picked })]);
    expect(outcome.ops).toEqual([
      { op: "move", group_name: "AAA", bar: 1, to_bar: 3 },
      { op: "move", group_name: "AAA", bar: 5, to_bar: 7 },
    ]);
  });

  it("다른 포인터의 이벤트는 무시한다", () => {
    const pressed = run([down(100)]).state;
    expect(run([move(184, 2)], pressed).state).toEqual(pressed);
    expect(run([up(184, { pointerId: 2 })], pressed)).toEqual({ state: pressed, ops: null, suppressClick: false });
  });

  it("누른 적 없이 오는 움직임·놓기·취소는 아무 일도 하지 않는다", () => {
    for (const event of [move(184), up(184), cancel()]) {
      expect(run([event])).toEqual({ state: IDLE, ops: null, suppressClick: false });
    }
  });

  it("취소: 끌던 중이면 클릭을 무시하고, 아직 눌림이면 무시하지 않는다 — 어느 쪽도 보내지 않는다", () => {
    expect(run([down(100), move(184), cancel()])).toEqual({ state: IDLE, ops: null, suppressClick: true });
    expect(run([down(100), cancel()])).toEqual({ state: IDLE, ops: null, suppressClick: false });
  });

  it("끌던 중에 다시 누르면 새 눌림으로 처음부터 시작한다", () => {
    const outcome = run([down(100), move(184), down(300, cell("BBB", 9))]);
    expect(outcome.state).toEqual({ phase: "pressed", pointerId: 1, startX: 300, cell: cell("BBB", 9) });
  });
});

describe("cellsToMove — 어느 칸이 함께 옮겨지나", () => {
  it("끈 칸이 골라 둔 칸이 아니면 그 칸 하나만 옮긴다 — 골라 둔 칸은 건드리지 않는다", () => {
    const picked = [cell("AAA", 1), cell("AAA", 9)];
    expect(cellsToMove(cell("AAA", 5), picked)).toEqual([cell("AAA", 5)]);
    expect(picked).toEqual([cell("AAA", 1), cell("AAA", 9)]);
  });

  it("고른 칸이 없으면 끈 칸 하나다", () => {
    expect(cellsToMove(cell("AAA", 5), [])).toEqual([cell("AAA", 5)]);
  });

  it("끈 칸이 골라 둔 칸이면 같은 줄의 고른 칸 전부를 고른 순서대로 옮긴다", () => {
    const picked = [cell("AAA", 9), cell("AAA", 1), cell("AAA", 5)];
    expect(cellsToMove(cell("AAA", 5), picked)).toEqual([cell("AAA", 9), cell("AAA", 1), cell("AAA", 5)]);
  });

  it("다른 줄의 칸은 고르기에 들어 있어도 옮기지 않는다", () => {
    const picked = [cell("AAA", 1), cell("BBB", 1), cell("AAA", 5), cell("BBB", 5), cell("CCC", 5)];
    expect(cellsToMove(cell("AAA", 5), picked)).toEqual([cell("AAA", 1), cell("AAA", 5)]);
    expect(cellsToMove(cell("BBB", 5), picked)).toEqual([cell("BBB", 1), cell("BBB", 5)]);
  });

  it("줄 이름이 같아도 마디가 다르면 같은 칸이 아니다 — 끈 칸이 고른 칸에 없으면 하나만", () => {
    expect(cellsToMove(cell("AAA", 5), [cell("AAA", 6), cell("BBB", 5)])).toEqual([cell("AAA", 5)]);
  });
});

describe("cellMoveOps — 보낼 목록", () => {
  it("칸마다 옛 마디와 옮길 마디를 담은 옮기기 항목 하나씩이다", () => {
    expect(cellMoveOps([cell("AAA", 1), cell("AAA", 5)], 2)).toEqual([
      { op: "move", group_name: "AAA", bar: 1, to_bar: 3 },
      { op: "move", group_name: "AAA", bar: 5, to_bar: 7 },
    ]);
    expect(cellMoveOps([cell("AAA", 5)], -2)).toEqual([{ op: "move", group_name: "AAA", bar: 5, to_bar: 3 }]);
  });

  it("옮길 마디가 0 이면 보내지 않는다 — 서버도 같은 마디로 옮기기를 거절한다", () => {
    expect(cellMoveOps([cell("AAA", 5)], 0)).toBeNull();
    expect(cellMoveOps([cell("AAA", 5)], -0)).toBeNull();
  });

  it("정수가 아닌 마디 수(0.5·NaN·무한)는 보내지 않는다", () => {
    for (const delta of [0.5, Number.NaN, Number.POSITIVE_INFINITY, Number.NEGATIVE_INFINITY]) {
      expect(cellMoveOps([cell("AAA", 5)], delta)).toBeNull();
    }
  });

  it("옮길 칸이 없으면 보내지 않는다", () => {
    expect(cellMoveOps([], 2)).toBeNull();
  });

  it("옮길 자리가 1마디 미만이면 보내지 않는다", () => {
    expect(cellMoveOps([cell("AAA", 1)], -1)).toBeNull();
    expect(cellMoveOps([cell("AAA", 3)], -4)).toBeNull();
    // 1마디에 닿는 것은 된다.
    expect(cellMoveOps([cell("AAA", 3)], -2)).toEqual([{ op: "move", group_name: "AAA", bar: 3, to_bar: 1 }]);
  });

  it("칸 하나라도 옮길 수 없으면 전부 보내지 않는다 — 일부만 옮기지 않는다", () => {
    expect(cellMoveOps([cell("AAA", 1), cell("AAA", 5)], -1)).toBeNull();
  });

  it("옛 마디가 0(앞박) 인 칸이 섞이면 전부 보내지 않는다 — 서버는 마디 1 미만 항목이 하나라도 있으면 통째로 거절한다", () => {
    expect(cellMoveOps([cell("AAA", 0)], 2)).toBeNull();
    expect(cellMoveOps([cell("AAA", 0), cell("AAA", 5)], 2)).toBeNull();
  });
});
