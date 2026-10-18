// 칸 단위 반영 (SPEC-LDRHYTHM-001, 카드 WT-cell-apply) — 화면이 정하는 것들.
//
// 「⇪ 콘솔에 반영」은 바뀐 칸만 콘솔에 덧쓰는 칸 단위 반영이 기본이고, 곡 전체를 다시 보내는 길은 「전체 다시
// 반영」으로 따로 남는다. 어느 칸을 보낼지, 못 보낼 때 무엇을 말할지, 보낸 뒤 결과를 어떻게 줄여 보일지,
// 칸마다 콘솔과 같은지를 여기서 순수하게 정한다. 무엇을 콘솔에 쓰는지는 서버가 정한다(UI는 칸 주소만 올린다).
import type { BeatGridPartialBaseline, BeatGridSubsetStatus } from "../../protocol";
import { CELL_WIRE_MAX, cellKey, skippedBarNote, wireCells, type CueCell } from "./cellSelection";

/** 기준이 없는 곡 — 칸 단위 반영의 기준(`partial_baseline`)이 `null` 이라 칸 단위로 보낼 수 없다. 이 말은 이때만 보인다. */
export const PARTIAL_NO_RECORD_HINT = "이 곡은 아직 반영 기록이 없어요 — 「전체 다시 반영」을 먼저 누르세요";
export const PARTIAL_NOTHING_CHANGED_HINT = "바뀐 칸이 없어요";
export const PARTIAL_PICKED_NOTHING_CHANGED_HINT = "고른 칸 중 바뀐 칸이 없어요";
/** 기록 기준(`"record"`)에서 고른 칸이 없을 때 — 어느 칸이 바뀌었는지 모르니 보낼 칸은 사람이 골라야 한다. */
export const PARTIAL_NOTHING_PICKED_HINT = "고른 칸을 먼저 골라 주세요 — 기록 기준이라 바뀐 칸을 알 수 없어요";
/** 기록 기준으로 보낼 때의 주의 — 지운 값은 가려내지 못해 콘솔에 남을 수 있다. 보내기 전 안내와 보낸 뒤 결과가 같은 말을 한다. */
export const PARTIAL_RECORD_WARNING = "지운 값은 콘솔에 남을 수 있어요 — 지운 칸은 「전체 다시 반영」으로";

export type PartialApplyPlan =
  | {
      kind: "ready";
      /** 서버로 보낼 `[줄 이름, 마디]` — 칸 기록 기준이면 바뀐 칸만, 기록 기준이면 고른 칸 모두. */
      cells: [string, number][];
      /** 화면에 보이는 한 줄: 무엇을 보내는지(+ 못 보내는 칸이 있으면 그 사실). */
      note: string;
    }
  | {
      kind: "blocked";
      /** 버튼 title 과 화면 안내에 쓰는 이유. */
      reason: string;
      why: "no-record" | "nothing-picked" | "nothing-changed" | "too-many" | "bar-zero";
    };

/** 서버로 보낼 칸 목록이 서버가 받는 꼴인지 거른다 — 0마디(앞박)는 빼고, 비었거나 상한을 넘으면 막는다. 칸 기록 기준과 기록
 * 기준이 같이 쓴다. 비어 있는 칸 목록은 절대 `ready` 로 내보내지 않는다(빈 `cells` 는 프레임에서 빠져 곡 전체 반영이 된다). */
function wirePlan(
  cells: readonly CueCell[],
  readyNote: (sent: number, skippedNote: string | null) => string,
): PartialApplyPlan {
  const wire = wireCells(cells);
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
  return {
    kind: "ready",
    cells: wire.cells,
    note: readyNote(wire.cells.length, wire.skipped > 0 ? skippedBarNote(wire.skipped) : null),
  };
}

/** 「⇪ 콘솔에 반영」이 보낼 칸. 무엇을 기준으로 삼는지는 서버가 정한다(`baseline` = `beat_grid.partial_baseline`):
 * - `null`/`undefined`: 기준이 없어 막는다 — 「전체 다시 반영」을 먼저 눌러야 한다.
 * - `"record"`: 칸 기록이 없어 바뀐 칸을 모른다. 고른 칸을 **모두** 보낸다(`unsent` 로 거르지 않는다). 고른 칸이 없으면 막는다.
 *   지운 값은 가려내지 못해 콘솔에 남을 수 있다 — 안내에 그렇게 적는다.
 * - `"snapshot"`: `unsent`(마지막 반영 뒤 바뀐 칸)가 목록이다. 고른 칸이 있으면 그 칸들, 없으면 바뀐 칸 전부 중에서
 *   **바뀐 칸만** 보낸다. */
export function partialApplyPlan(
  unsent: readonly CueCell[] | null | undefined,
  picks: readonly CueCell[],
  baseline: BeatGridPartialBaseline | null | undefined,
): PartialApplyPlan {
  if (baseline === "record") {
    if (picks.length === 0) {
      return { kind: "blocked", reason: PARTIAL_NOTHING_PICKED_HINT, why: "nothing-picked" };
    }
    const unique = [...new Map(picks.map((cell) => [cellKey(cell), cell] as const)).values()];
    return wirePlan(unique, (sent, skippedNote) => {
      const picked = skippedNote === null ? `고른 ${sent}칸` : `고른 ${unique.length}칸 중 ${sent}칸`;
      return [`${picked}을 보내요 (기록 기준)`, PARTIAL_RECORD_WARNING, skippedNote].filter((part) => part !== null).join(" · ");
    });
  }
  if (baseline !== "snapshot" || unsent === null || unsent === undefined) {
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
  return wirePlan(changed, (sent, skippedNote) => {
    const scope = picks.length > 0 ? `고른 ${picks.length}칸 중 바뀐 ${sent}칸만 보내요` : `바뀐 ${sent}칸만 보내요`;
    return skippedNote === null ? scope : `${scope} · ${skippedNote}`;
  });
}

/** 칸 단위 반영이 끝난 뒤 알림 줄에 보이는 요약. */
export interface SubsetSummary {
  /** 「N칸 반영 · 못 보낸 칸 M개」 + 앞쪽 사유 셋(+ 기록 기준으로 보냈으면 그 사실). */
  text: string;
  /** 칸마다 전부(마우스를 올리면 보인다). */
  title: string;
  /** 보낸 첫 칸의 마디 — 그 마디를 콘솔에서 보러 간다. */
  firstBar: number;
}

const SUMMARY_REASON_LIMIT = 3;

/** 기록 기준(`subset.baseline === "record"`)으로 보냈을 때 요약 끝에 붙는 말 — 바뀐 칸을 가려내지 못했고 지운 값도 확인 못 했다. */
export const SUBSET_RECORD_BASELINE_NOTE = "기록 기준으로 보냄(지운 값은 확인 못 함)";

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
  const text = skipped.length > 0 ? `${head} — ${shown}${more}` : head;
  return {
    text: subset.baseline === "record" ? `${text} · ${SUBSET_RECORD_BASELINE_NOTE}` : text,
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
