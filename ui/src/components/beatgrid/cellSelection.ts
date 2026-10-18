// 타임라인 칸 여러 개 고르기 (SPEC-LDRHYTHM-001, 카드 WT-cell-apply).
//
// 보통 클릭은 기존 한 칸 선택(`selectCue`)이고, Shift+클릭은 기준 칸과 누른 칸 사이의 사각형,
// Ctrl/Cmd+클릭은 칸 하나를 더하거나 뺀다. 이 모듈은 어느 칸이 골라지는지만 순수하게 정한다 — 칸을
// 어떻게 그리는지, 서버에 무엇을 보내는지는 호출부(BeatGrid.tsx·cellApply.ts)의 소관이다.
// 칸은 `cueEditKey(줄 이름, 마디)` 로 가린다(서버가 칸을 부르는 주소와 같다).
import type { BeatGridTrack } from "../../protocol";
import { cueEditKey } from "./cueDisplayState";

/** 칸 하나 — 콘솔 그룹 이름과 그 칸이 시작하는 마디. */
export interface CueCell {
  group_name: string;
  bar: number;
}

export type CellClickMode = "plain" | "range" | "toggle";

/** 클릭에서 읽는 수정키 — React/DOM 마우스 이벤트가 그대로 맞는다. */
export interface CellClickKeys {
  shiftKey: boolean;
  ctrlKey: boolean;
  metaKey: boolean;
}

/** Shift 가 이긴다. Ctrl 과 Cmd 는 같은 뜻이다(맥에서 Ctrl+클릭은 오른쪽 클릭으로 가로채이는 일이 있다). */
export function cellClickMode(keys: CellClickKeys): CellClickMode {
  if (keys.shiftKey) return "range";
  if (keys.ctrlKey || keys.metaKey) return "toggle";
  return "plain";
}

export function cellKey(cell: CueCell): string {
  return cueEditKey(cell.group_name, cell.bar);
}

/** 고른 칸들과 기준 칸. 기준은 Ctrl 로 마지막에 누른 칸이고, 없으면 호출부가 편집 칸의 선택(`selected`)을 쓴다. */
export interface CellSelection {
  cells: readonly CueCell[];
  anchor: CueCell | null;
}

export const EMPTY_CELL_SELECTION: CellSelection = Object.freeze({ cells: [], anchor: null });

/** 줄(`rows`, 화면에 보이는 순서)이 기준 칸과 누른 칸 사이에 있고, 칸이 시작하는 마디가 두 마디 사이(양끝 포함)에
 * 있는 칸 전부 — 줄 위→아래, 마디 앞→뒤 순서다. 기준·누른 방향과 무관하다. 두 칸 중 한 줄이 `rows` 에 없으면 `[]`. */
export function rectangleCells(rows: readonly BeatGridTrack[], anchor: CueCell, target: CueCell): CueCell[] {
  const from = rows.findIndex((row) => row.group_name === anchor.group_name);
  const to = rows.findIndex((row) => row.group_name === target.group_name);
  if (from < 0 || to < 0) return [];
  const [rowLo, rowHi] = from <= to ? [from, to] : [to, from];
  const [barLo, barHi] = anchor.bar <= target.bar ? [anchor.bar, target.bar] : [target.bar, anchor.bar];
  const found = new Map<string, CueCell>();
  for (let index = rowLo; index <= rowHi; index += 1) {
    for (const cue of rows[index].cues) {
      if (cue.bar < barLo || cue.bar > barHi) continue;
      const cell = { group_name: rows[index].group_name, bar: cue.bar };
      found.set(cellKey(cell), cell);
    }
  }
  return [...found.values()];
}

/** 이미 든 칸이면 빼고, 아니면 끝에 더한다. 받은 목록은 고치지 않는다. */
export function toggleCell(cells: readonly CueCell[], cell: CueCell): CueCell[] {
  const key = cellKey(cell);
  return cells.some((held) => cellKey(held) === key) ? cells.filter((held) => cellKey(held) !== key) : [...cells, cell];
}

/** 클릭 하나가 고른 칸을 어떻게 바꾸는가(보통 클릭은 호출부가 `selectCue` 로 처리하고 여기 오지 않는다).
 * - 범위: 기준(없으면 `selected`)에서 누른 칸까지의 사각형으로 **바꾼다**. 기준은 그대로다. 기준이 없거나 사각형을
 *   못 그리면 누른 칸 하나다.
 * - 토글: 누른 칸을 더하거나 뺀다. 아직 아무것도 안 골랐고 Ctrl/Shift 를 한 번도 안 눌렀다면 편집 칸의 선택(`selected`)을
 *   먼저 넣고 시작한다(보통 클릭한 칸이 빠지지 않게). 누른 칸이 새 기준이다. */
export function applyCellClick(
  state: CellSelection,
  mode: Exclude<CellClickMode, "plain">,
  clicked: CueCell,
  ctx: { rows: readonly BeatGridTrack[]; selected: CueCell | null },
): CellSelection {
  if (mode === "toggle") {
    const seed = state.cells.length === 0 && state.anchor === null && ctx.selected ? [ctx.selected] : state.cells;
    return { cells: toggleCell(seed, clicked), anchor: clicked };
  }
  const anchor = state.anchor ?? ctx.selected;
  if (!anchor) return { cells: [clicked], anchor: clicked };
  const cells = rectangleCells(ctx.rows, anchor, clicked);
  return { cells: cells.length > 0 ? cells : [clicked], anchor };
}

/** 골라 둔 칸 가운데 지금 격자에 아직 있는 칸만. 서버가 격자를 새로 보내 칸이 사라졌으면 빠진다. */
export function existingCells(cells: readonly CueCell[], tracks: readonly BeatGridTrack[]): CueCell[] {
  if (cells.length === 0) return cells.slice();
  const barsByGroup = new Map<string, Set<number>>();
  for (const track of tracks) {
    const bars = barsByGroup.get(track.group_name) ?? new Set<number>();
    for (const cue of track.cues) bars.add(cue.bar);
    barsByGroup.set(track.group_name, bars);
  }
  return cells.filter((cell) => barsByGroup.get(cell.group_name)?.has(cell.bar) === true);
}

/** 서버가 한 번에 받는 `cells` 상한(`server/web/messages.py` 의 `BEAT_GRID_CELLS_MAX`). 넘기면 메시지 통째로 거절된다. */
export const CELL_WIRE_MAX = 400;

/** 서버로 보낼 `[줄 이름, 마디]` 목록과, 보낼 수 없어 뺀 칸 수. 서버의 `cells` 는 마디가 1 이상인 정수만 받는다 —
 * 0마디(앞박) 칸이 하나라도 섞이면 메시지 통째로 거절되므로 여기서 뺀다(빼는 사실은 호출부가 화면에 말한다). */
export function wireCells(cells: readonly CueCell[]): { cells: [string, number][]; skipped: number } {
  const wire: [string, number][] = [];
  for (const cell of cells) {
    if (Number.isInteger(cell.bar) && cell.bar >= 1) wire.push([cell.group_name, cell.bar]);
  }
  return { cells: wire, skipped: cells.length - wire.length };
}

/** 앞박(0마디) 칸을 서버 `cells` 로 못 보낼 때 화면에 말하는 문구. `action` 은 반영(`send`)인지 일괄 바꾸기(`edit`)인지. */
export function skippedBarNote(skipped: number, action: "send" | "edit" = "send"): string {
  return `0마디(앞박) 칸 ${skipped}개는 칸 단위로 ${action === "send" ? "보낼" : "바꿀"} 수 없어요`;
}
