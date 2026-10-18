// 칸 막대 가로 끌기로 같은 줄 안에서 옮기기 (SPEC-LDRHYTHM-001, 카드 WT-cell-edit-live).
//
// 칸 막대를 좌우로 끌면 그 칸(들)을 끈 거리만큼 마디 단위로 옮긴다. 이 모듈은 끌기 상태 전이와 어느 칸이 몇 마디 옮겨지는지만
// 순수하게 정한다 — 포인터 이벤트를 어떻게 받는지, 서버에 어떻게 올리는지는 호출부(BeatGrid.tsx)의 소관이다. 이음매 끌기
// (`../beatGridSeam.ts`)와 같은 모양이다: 누르기 → 임계값을 넘으면 끌기 → 놓을 때만 결과를 내고, 끌었으면 뒤따르는 클릭을 무시한다.
import type { BeatGridCellOp } from "../../protocol";
import { SEAM_DRAG_THRESHOLD_PX } from "../beatGridSeam";
import { cellKey, type CueCell } from "./cellSelection";

/** 이 거리(px) 미만으로 움직이면 끌기가 아니라 누르기다 — 이음매 끌기와 같은 값이다. */
export const CELL_DRAG_THRESHOLD_PX = SEAM_DRAG_THRESHOLD_PX;

/** 끌기 상태 — 누르기부터 놓기까지. `pressed` 는 아직 끌기가 아니다(임계값 전). */
export type CellMoveState =
  | { phase: "idle" }
  | { phase: "pressed"; pointerId: number; startX: number; cell: CueCell }
  | { phase: "dragging"; pointerId: number; startX: number; cell: CueCell };

export const IDLE_CELL_MOVE: CellMoveState = { phase: "idle" };

export type CellMoveEvent =
  | { type: "down"; pointerId: number; x: number; cell: CueCell }
  | { type: "move"; pointerId: number; x: number }
  // 놓는 순간에 필요한 것을 같이 받는다: 마디 한 칸의 폭(px)과 지금 골라 둔 칸.
  | { type: "up"; pointerId: number; x: number; pxPerBar: number; picked: readonly CueCell[] }
  | { type: "cancel"; pointerId: number };

export interface CellMoveOutcome {
  state: CellMoveState;
  /** 놓을 때 서버에 올릴 옮기기 목록 — 끌었고, 옮길 마디가 0 이 아니고, 갈 수 있을 때만. 그 밖에는 `null`. */
  ops: BeatGridCellOp[] | null;
  /** 끌었으면 뒤따르는 클릭(칸 고르기)을 무시한다. 마디로는 0 이거나 갈 수 없어 못 옮겼어도 끈 손짓은 클릭이 아니다. */
  suppressClick: boolean;
}

const exceedsThreshold = (deltaPx: number) => Math.abs(deltaPx) >= CELL_DRAG_THRESHOLD_PX;

/** 끌기 한 걸음 — 상태와 이벤트를 받아 새 상태, 놓을 때의 옮기기 목록, 클릭 무시 여부를 돌려준다. */
export function reduceCellMove(state: CellMoveState, event: CellMoveEvent): CellMoveOutcome {
  const keep = (next: CellMoveState): CellMoveOutcome => ({ state: next, ops: null, suppressClick: false });
  // 새로 누르면 앞 상태가 무엇이든 처음부터 시작한다(놓는 이벤트를 놓친 경우에도 앞 끌기가 새 누르기로 새지 않는다).
  if (event.type === "down") {
    return keep({ phase: "pressed", pointerId: event.pointerId, startX: event.x, cell: event.cell });
  }
  if (state.phase === "idle" || state.pointerId !== event.pointerId) return keep(state);
  switch (event.type) {
    case "move":
      // 한 번 끌기가 되면 시작점 근처로 돌아와도 끌기로 남는다 — 끈 손짓이 클릭으로 바뀌지 않는다.
      return state.phase === "pressed" && !exceedsThreshold(event.x - state.startX)
        ? keep(state)
        : keep({ ...state, phase: "dragging" });
    case "up": {
      const deltaPx = event.x - state.startX;
      // 임계값을 넘은 적이 없고 놓는 자리도 안 넘었으면 보통 클릭이다. 움직임 이벤트가 합쳐져 빠져도 놓는 좌표가 정한다.
      if (state.phase === "pressed" && !exceedsThreshold(deltaPx)) return keep(IDLE_CELL_MOVE);
      const ops = cellMoveOps(cellsToMove(state.cell, event.picked), Math.round(deltaPx / event.pxPerBar));
      return { state: IDLE_CELL_MOVE, ops, suppressClick: true };
    }
    case "cancel":
      return { state: IDLE_CELL_MOVE, ops: null, suppressClick: state.phase === "dragging" };
  }
}

/** 끈 칸(`dragged`)과 골라 둔 칸(`picked`)으로 함께 옮길 칸을 가린다. 끈 칸이 골라 둔 칸 가운데 하나면 골라 둔 칸 중 **같은 줄**의
 * 칸 전부를 고른 순서대로, 아니면 끈 칸 하나만 옮긴다. 다른 줄의 칸은 고르기에 들어 있어도 옮기지 않는다. */
export function cellsToMove(dragged: CueCell, picked: readonly CueCell[]): CueCell[] {
  const key = cellKey(dragged);
  if (!picked.some((held) => cellKey(held) === key)) return [dragged];
  return picked.filter((held) => held.group_name === dragged.group_name);
}

/** 옮길 칸들과 옮길 마디 수(`deltaBars`, 음수는 앞으로)로 서버에 올릴 옮기기 목록을 만든다. 보낼 수 없으면 `null`:
 * 옮길 칸이 없거나, 마디 수가 0 이거나 정수가 아니거나, 옛 마디나 옮길 마디가 1 미만인 칸이 하나라도 있을 때다. 서버는 마디가
 * 1 이상의 정수가 아닌 항목이 하나라도 섞이면 메시지를 통째로 거절하므로 일부만 보내지 않고 통째로 보내지 않는다. */
export function cellMoveOps(cells: readonly CueCell[], deltaBars: number): BeatGridCellOp[] | null {
  if (!Number.isInteger(deltaBars) || deltaBars === 0 || cells.length === 0) return null;
  const ops = cells.map(
    ({ group_name, bar }): BeatGridCellOp => ({ op: "move", group_name, bar, to_bar: bar + deltaBars }),
  );
  return ops.every((op) => op.bar >= 1 && op.to_bar >= 1) ? ops : null;
}
