// 칸 단위 반영 (SPEC-LDRHYTHM-001, 카드 WT-cell-apply) — 화면이 정하는 것들.
//
// 「⇪ 콘솔에 반영」은 바뀐 칸만 콘솔에 덧쓰는 칸 단위 반영이 기본이고, 곡 전체를 다시 보내는 길은 「전체 다시
// 반영」으로 따로 남는다. 어느 칸을 보낼지, 못 보낼 때 무엇을 말할지, 보낸 뒤 결과를 어떻게 줄여 보일지,
// 칸마다 콘솔과 같은지를 여기서 순수하게 정한다. 무엇을 콘솔에 쓰는지는 서버가 정한다(UI는 칸 주소만 올린다).
import type { BeatGridSubsetStatus } from "../../protocol";
import { CELL_WIRE_MAX, cellKey, skippedBarNote, wireCells, type CueCell } from "./cellSelection";

/** 반영 기록(마지막 반영 스냅샷)이 없는 곡 — 칸 단위로는 무엇이 바뀌었는지 모른다. */
export const PARTIAL_NO_RECORD_HINT = "이 곡은 아직 반영 기록이 없어요 — 「전체 다시 반영」을 먼저 누르세요";
export const PARTIAL_NOTHING_CHANGED_HINT = "바뀐 칸이 없어요";
export const PARTIAL_PICKED_NOTHING_CHANGED_HINT = "고른 칸 중 바뀐 칸이 없어요";

export type PartialApplyPlan =
  | {
      kind: "ready";
      /** 서버로 보낼 `[줄 이름, 마디]` — 바뀐 칸만. */
      cells: [string, number][];
      /** 화면에 보이는 한 줄: 무엇을 보내는지(+ 못 보내는 칸이 있으면 그 사실). */
      note: string;
    }
  | {
      kind: "blocked";
      /** 버튼 title 과 화면 안내에 쓰는 이유. */
      reason: string;
      why: "no-record" | "nothing-changed" | "too-many" | "bar-zero";
    };

/** 「⇪ 콘솔에 반영」이 보낼 칸 — 고른 칸이 있으면 그 칸들, 없으면 바뀐 칸 전부 중에서 **바뀐 칸만**.
 * `unsent` 는 서버 `unsent_cells`(마지막 반영 뒤 바뀐 칸). `null`/`undefined` 면 반영 기록이 없어 칸 단위로 못 보낸다. */
export function partialApplyPlan(
  unsent: readonly CueCell[] | null | undefined,
  picks: readonly CueCell[],
): PartialApplyPlan {
  if (unsent === null || unsent === undefined) {
    return { kind: "blocked", reason: PARTIAL_NO_RECORD_HINT, why: "no-record" };
  }
  const changedKeys = new Set(unsent.map(cellKey));
  const wanted = picks.length > 0 ? picks : unsent;
  const seen = new Set<string>();
  const changed = wanted.filter((cell) => {
    const key = cellKey(cell);
    if (!changedKeys.has(key) || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
  if (changed.length === 0) {
    return {
      kind: "blocked",
      reason: picks.length > 0 ? PARTIAL_PICKED_NOTHING_CHANGED_HINT : PARTIAL_NOTHING_CHANGED_HINT,
      why: "nothing-changed",
    };
  }
  const wire = wireCells(changed);
  if (wire.cells.length === 0) {
    return {
      kind: "blocked",
      reason: `${skippedBarNote(wire.skipped)} — 「전체 다시 반영」을 누르세요`,
      why: "bar-zero",
    };
  }
  if (wire.cells.length > CELL_WIRE_MAX) {
    return {
      kind: "blocked",
      reason: `한 번에 ${CELL_WIRE_MAX}칸까지만 보낼 수 있어요 — 칸을 나눠 고르거나 「전체 다시 반영」을 누르세요`,
      why: "too-many",
    };
  }
  const scope =
    picks.length > 0
      ? `고른 ${picks.length}칸 중 바뀐 ${wire.cells.length}칸만 보내요`
      : `바뀐 ${wire.cells.length}칸만 보내요`;
  return {
    kind: "ready",
    cells: wire.cells,
    note: wire.skipped > 0 ? `${scope} · ${skippedBarNote(wire.skipped)}` : scope,
  };
}

/** 칸 단위 반영이 끝난 뒤 알림 줄에 보이는 요약. */
export interface SubsetSummary {
  /** 「N칸 반영 · 못 보낸 칸 M개」 + 앞쪽 사유 셋. */
  text: string;
  /** 칸마다 전부(마우스를 올리면 보인다). */
  title: string;
  /** 보낸 첫 칸의 마디 — 그 마디를 콘솔에서 보러 간다. */
  firstBar: number;
}

const SUMMARY_REASON_LIMIT = 3;

/** 서버 `subset` → 알림 요약. 보낸 칸이 하나도 없으면(`applied` 가 비면) 요약할 성공이 없으니 `null`.
 * 사유는 같은 말을 되풀이하지 않고 처음 나온 순서대로 셋까지 보인다. */
export function subsetSummary(subset: BeatGridSubsetStatus | null | undefined): SubsetSummary | null {
  if (!subset || subset.applied.length === 0) return null;
  const skipped = subset.not_applied;
  const reasons = [...new Set(skipped.map((cell) => cell.reason))];
  const shown = reasons.slice(0, SUMMARY_REASON_LIMIT).join(" · ");
  const more = reasons.length > SUMMARY_REASON_LIMIT ? " …" : "";
  const head = `${subset.applied.length}칸 반영 · 못 보낸 칸 ${skipped.length}개`;
  const lines = [
    `고른 ${subset.requested}칸 중 ${subset.applied.length}칸 반영`,
    `반영한 칸: ${subset.applied.map(([name, bar]) => `${name} ${bar}마디`).join(", ")}`,
    ...skipped.map((cell) => `못 보낸 칸: ${cell.group_name} ${cell.bar}마디 — ${cell.reason}`),
  ];
  return {
    text: skipped.length > 0 ? `${head} — ${shown}${more}` : head,
    title: lines.join("\n"),
    firstBar: subset.applied[0][1],
  };
}

export const CUE_SYNC_APP_ONLY_LABEL = "앱에서만 바뀜";
export const CUE_SYNC_IN_SYNC_LABEL = "콘솔과 같음";

export interface CueSyncMark {
  kind: "app-only" | "in-sync";
  /** 눈에 보이는 기호 — 색에만 기대지 않게 늘 같이 그린다. */
  glyph: string;
  /** title·aria-label 에 쓰는 글. */
  label: string;
}

/** 서버 `unsent_cells` → 칸 키 집합. `null`/`undefined`(반영 기록이 없거나 옛 서버)는 `null` 이라 칸마다 아무 표시도
 * 안 한다 — 빈 배열(기록은 있고 바뀐 칸이 없음)과 다르다. */
export function unsentKeySet(unsent: readonly CueCell[] | null | undefined): Set<string> | null {
  return unsent === null || unsent === undefined ? null : new Set(unsent.map(cellKey));
}

/** 칸 하나가 콘솔과 같은지: 바뀐 칸 집합에 있으면 앱에서만 바뀜, 집합은 있는데 없으면 콘솔과 같음, 집합이 없으면 표시 없음. */
export function cueSyncMark(unsentKeys: ReadonlySet<string> | null, cell: CueCell): CueSyncMark | null {
  if (unsentKeys === null) return null;
  return unsentKeys.has(cellKey(cell))
    ? { kind: "app-only", glyph: "✎", label: CUE_SYNC_APP_ONLY_LABEL }
    : { kind: "in-sync", glyph: "✓", label: CUE_SYNC_IN_SYNC_LABEL };
}
