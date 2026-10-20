// 칸 단위 반영 (SPEC-LDRHYTHM-001, 카드 WT-cell-apply) — 화면이 정하는 것들.
//
// 「⇪ 콘솔에 반영」은 바뀐 칸만 콘솔에 덧쓰는 칸 단위 반영이 기본이고, 곡 전체를 다시 보내는 길은 「전체 다시
// 반영」으로 따로 남는다. 어느 칸을 보낼지, 못 보낼 때 무엇을 말할지, 보낸 뒤 결과를 어떻게 줄여 보일지,
// 칸마다 콘솔과 같은지를 여기서 순수하게 정한다. 무엇을 콘솔에 쓰는지는 서버가 정한다(UI는 칸 주소만 올린다).
import type { BeatGridPartialBaseline, BeatGridSubsetStatus } from "../../protocol";
import { CELL_WIRE_MAX, cellKey, skippedBarNote, wireCells, type CueCell } from "./cellSelection";

// 바뀐 칸을 가려낼 기준이 없으면 「⇪ 콘솔에 반영」은 막지 않고 곡 전체를 보낸다(「전체 다시 반영」과 같은 길) — 2026-10-20
// 헤드리스 E2E 실측: 자동 배치 → 프리셋 승인 → TC 뒤 첫 반영에서 이 버튼이 꺼져 「전체 다시 반영」만 됐다.
/** 기준이 없는 곡(`partial_baseline` 이 `null`) — 첫 반영이라 곡 전체를 보낸다. 이 말은 이때만 보인다. */
export const PARTIAL_WHOLE_NO_RECORD_NOTE = "아직 반영 기록이 없어 곡 전체를 보내요 (「전체 다시 반영」과 같아요)";
/** 기록 기준(`"record"`)에서 고른 칸이 없을 때 — 어느 칸이 바뀌었는지 모르니 곡 전체를 보낸다. 칸만 보내려면 고른다. */
export const PARTIAL_WHOLE_RECORD_NOTE =
  "바뀐 칸을 알 수 없어 곡 전체를 보내요 (「전체 다시 반영」과 같아요) — 칸만 보내려면 칸을 고르세요";
export const PARTIAL_NOTHING_CHANGED_HINT = "바뀐 칸이 없어요";
export const PARTIAL_PICKED_NOTHING_CHANGED_HINT = "고른 칸 중 바뀐 칸이 없어요";
/** 기록 기준으로 보낼 때의 주의 — 지운 값은 가려내지 못해 콘솔에 남을 수 있다. 보내기 전 안내와 보낸 뒤 결과가 같은 말을 한다. */
export const PARTIAL_RECORD_WARNING = "지운 값은 콘솔에 남을 수 있어요 — 지운 칸은 「전체 다시 반영」으로";

export type PartialApplyPlan =
  | {
      kind: "ready";
      /** 서버로 보낼 `[줄 이름, 마디]` — 칸 기록 기준이면 바뀐 칸과 콘솔 상태를 모르는 칸(콘솔과 같은 칸은 뺀다), 기록 기준이면 고른 칸 모두. */
      cells: [string, number][];
      /** 화면에 보이는 한 줄: 무엇을 보내는지(+ 못 보내는 칸이 있으면 그 사실). */
      note: string;
    }
  | {
      /** 바뀐 칸을 가려낼 기준이 없어 곡 전체를 보낸다 — 「전체 다시 반영」과 같은 콜백을 부른다. */
      kind: "whole";
      /** 화면에 보이는 한 줄: 왜 곡 전체를 보내는지. */
      note: string;
      why: "no-record" | "nothing-picked";
    }
  | {
      kind: "blocked";
      /** 버튼 title 과 화면 안내에 쓰는 이유. */
      reason: string;
      why: "nothing-changed" | "too-many" | "bar-zero";
    };

/** 서버 `known_cells`(`BeatGridView`) — 부분 칸 기록이 아는 칸 `[줄 이름, 마디]` 전수. `null`/`undefined` 는 모든 칸을 안다는 뜻이다
 * (전체 기록이거나 기록이 없다). 빈 배열은 아는 칸이 하나도 없다는 뜻이라 모든 칸이 모르는 칸이다. */
export type KnownCells = readonly (readonly [string, number])[] | null | undefined;

/** `known_cells` → 칸 키 집합. `null` 이면 모든 칸을 안다(집합으로 거를 것이 없다). */
export function knownKeySet(known: KnownCells): Set<string> | null {
  return known === null || known === undefined
    ? null
    : new Set(known.map(([group_name, bar]) => cellKey({ group_name, bar })));
}

/** 서버로 보낼 칸 목록이 서버가 받는 꼴인지 거른다 — 0마디(앞박)는 빼고, 비었거나 상한을 넘으면 막는다. 칸 기록 기준과 기록
 * 기준이 같이 쓴다. 비어 있는 칸 목록은 절대 `ready` 로 내보내지 않는다(빈 `cells` 는 프레임에서 빠져 곡 전체 반영이 된다).
 * `readyNote` 는 실제로 보낼 칸 목록과 (뺀 칸이 있으면) 그 안내를 받아 화면에 보일 한 줄을 만든다. */
function wirePlan(
  cells: readonly CueCell[],
  readyNote: (sent: readonly (readonly [string, number])[], skippedNote: string | null) => string,
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
    note: readyNote(wire.cells, wire.skipped > 0 ? skippedBarNote(wire.skipped) : null),
  };
}

/** 칸 기록 기준에서 고른 칸 가운데 콘솔과 같아 보내지 않고 뺀 칸이 있을 때 안내 끝에 붙는 말. */
export function leftOutNote(count: number): string {
  return `콘솔과 같아 뺀 ${count}칸`;
}

/** 「⇪ 콘솔에 반영」이 보낼 칸. 무엇을 기준으로 삼는지는 서버가 정한다(`baseline` = `beat_grid.partial_baseline`):
 * - `null`/`undefined`: 기준이 없다(첫 반영) — 곡 전체를 보낸다(`whole`, 「전체 다시 반영」과 같다).
 * - `"record"`: 칸 기록이 없어 바뀐 칸을 모른다. 고른 칸을 **모두** 보낸다(`unsent`·`known` 으로 거르지 않는다). 고른 칸이
 *   없으면 곡 전체를 보낸다(`whole`). 지운 값은 가려내지 못해 콘솔에 남을 수 있다 — 안내에 그렇게 적는다.
 * - `"snapshot"`: `unsent`(마지막 반영 뒤 바뀐 칸)가 목록이다. `known` 은 칸 기록이 **부분**일 때 그 기록이 아는 칸이다
 *   (없으면 모든 칸을 안다). 고른 칸이 있으면 갈라서: 아는 칸인데 안 바뀐 칸은 콘솔과 같아 **뺀다**(안내에 몇 칸 뺐는지 적는다).
 *   바뀐 칸과 모르는 칸(`known` 에 없는 칸 — 콘솔과 같은지 알 수 없다)은 **보낸다**. 고른 칸이 없으면 바뀐 아는 칸 전부다.
 *   보낼 칸이 하나도 없으면 막는다. */
export function partialApplyPlan(
  unsent: readonly CueCell[] | null | undefined,
  picks: readonly CueCell[],
  baseline: BeatGridPartialBaseline | null | undefined,
  known?: KnownCells,
): PartialApplyPlan {
  if (baseline === "record") {
    if (picks.length === 0) {
      return { kind: "whole", note: PARTIAL_WHOLE_RECORD_NOTE, why: "nothing-picked" };
    }
    const unique = [...new Map(picks.map((cell) => [cellKey(cell), cell] as const)).values()];
    return wirePlan(unique, (sentCells, skippedNote) => {
      const sent = sentCells.length;
      const picked = skippedNote === null ? `고른 ${sent}칸` : `고른 ${unique.length}칸 중 ${sent}칸`;
      return [`${picked}을 보내요 (기록 기준)`, PARTIAL_RECORD_WARNING, skippedNote].filter((part) => part !== null).join(" · ");
    });
  }
  if (baseline !== "snapshot" || unsent === null || unsent === undefined) {
    return { kind: "whole", note: PARTIAL_WHOLE_NO_RECORD_NOTE, why: "no-record" };
  }
  const knownKeys = knownKeySet(known);
  const isKnown = (cell: CueCell) => knownKeys === null || knownKeys.has(cellKey(cell));
  const changedKeys = new Set(unsent.map(cellKey));
  // 고른 칸이 없으면 바뀐 아는 칸 전부, 있으면 고른 칸들(같은 칸은 한 번만).
  const wanted = picks.length > 0 ? picks : unsent.filter(isKnown);
  const seen = new Set<string>();
  const sendable: CueCell[] = [];
  let same = 0;
  for (const cell of wanted) {
    const key = cellKey(cell);
    if (seen.has(key)) continue;
    seen.add(key);
    // 바뀐 칸과 모르는 칸은 보내고, 아는데 안 바뀐 칸은 콘솔과 같으니 뺀다.
    if (changedKeys.has(key) || !isKnown(cell)) sendable.push(cell);
    else same += 1;
  }
  if (sendable.length === 0) {
    return {
      kind: "blocked",
      reason: picks.length > 0 ? PARTIAL_PICKED_NOTHING_CHANGED_HINT : PARTIAL_NOTHING_CHANGED_HINT,
      why: "nothing-changed",
    };
  }
  return wirePlan(sendable, (sentCells, skippedNote) => {
    const sent = sentCells.length;
    const changedSent = sentCells.filter(([group_name, bar]) => changedKeys.has(cellKey({ group_name, bar }))).length;
    const unknownSent = sent - changedSent;
    let scope: string;
    if (picks.length === 0) {
      scope = `바뀐 ${sent}칸만 보내요`;
    } else if (unknownSent === 0) {
      scope = `고른 ${seen.size}칸 중 바뀐 ${sent}칸만 보내요`;
    } else {
      const detail = [changedSent > 0 ? `바뀐 ${changedSent}칸` : null, `콘솔 상태를 모르는 ${unknownSent}칸`];
      scope = `고른 ${seen.size}칸 중 ${sent}칸을 보내요 (${detail.filter((part) => part !== null).join(" · ")})`;
    }
    return [scope, same > 0 ? leftOutNote(same) : null, skippedNote].filter((part) => part !== null).join(" · ");
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

/** 칸 하나가 콘솔과 같은지: 바뀐 칸 집합에 있으면 앱에서만 바뀜, 집합은 있는데 없으면 콘솔과 같음, 집합이 없으면 표시 없음.
 * `knownKeys`(`knownKeySet(known_cells)`)가 집합이고 그 칸이 거기 없으면 콘솔과 같은지 **모르는** 칸이라 표시하지 않는다 —
 * 같다고도 다르다고도 말하지 않는다. `null`(생략)이면 모든 칸을 안다. */
export function cueSyncMark(
  unsentKeys: ReadonlySet<string> | null,
  cell: CueCell,
  knownKeys: ReadonlySet<string> | null = null,
): CueSyncMark | null {
  if (unsentKeys === null) return null;
  if (knownKeys !== null && !knownKeys.has(cellKey(cell))) return null;
  return unsentKeys.has(cellKey(cell))
    ? { kind: "app-only", glyph: "✎", label: CUE_SYNC_APP_ONLY_LABEL }
    : { kind: "in-sync", glyph: "✓", label: CUE_SYNC_IN_SYNC_LABEL };
}
