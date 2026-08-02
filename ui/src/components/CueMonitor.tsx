// Live cue-progress monitor pane (T-C, wave 2 — ad-hoc contract, no SPEC on
// file; coordinator directive, 2026-08-02).
//
// Renders the two read paths server/web/cue_monitor.py builds: per-executor
// cue progress (sequence name + cue list + an independently-Optional current
// cue) and a console-independent recent-execution history. Deliberately NO
// progress percentage and NO timer field — out of scope by contract, since no
// channel here confirms a fade's remaining time. An unavailable current cue
// explains WHY it is empty rather than rendering a blank or a guessed number.
//
// T-H (coordinator directive, 2026-08-02) adds a THIRD, independent claim on
// top of the two above: the status chip + run/stop affordance. The chip
// NEVER means "the console is playing this now" — the live-probe findings
// this task is built on establish that no channel here can confirm that. It
// means only "what did the app itself last send this executor, and did the
// console ok it" (`entry.last_app_action`, server/web/cue_monitor.py's T-H
// attribution). Three grades, distinguished by TEXT + icon glyph, never
// color alone (colour-blind accessibility):
//   - confirmed (✓, green)  — the app sent a command and the console ok'd it
//   - failed    (✕, red)    — the app sent a command that failed/no reply
//   - unknown   (○, grey)   — the app has never sent this executor anything
//     (a console operated by hand is invisible to the app either way)
// The pulse animation fires ONLY for a few seconds right after a fresh
// "confirmed" event — an acknowledgement flash, not a running indicator —
// and degrades to a static emphasis under prefers-reduced-motion (styles.css).
//
// T-H2 (user feedback, 2026-08-02): the same "current cue confirm 불가"
// sentence was repeating verbatim on every executor row — a single fact
// about this console/responder combination, said 8 times, which reads as
// noise rather than information. Fixed WITHOUT hiding the fact: when every
// row's current-cue read fails for the SAME reason, that shared fact is
// said ONCE at panel level (`CurrentCueBanner`/`currentCueBannerState`);
// each row keeps only a short "현재 큐 —" placeholder (`currentCueRowView`)
// with the full explanation moved to its `title` tooltip. If reasons ever
// differ across rows (a future responder answering some but not others),
// the banner is withheld and each row states its own case individually —
// see `currentCueBannerState`'s three-way branch.
//
// T-H3 (coordinator live probe, 2026-08-02): the current-cue value's shape
// on the wire is now `"<index>"` or `"<index> — <name>"` (server/web/
// cue_monitor.py's own index/name composition off the Sequence handle). This
// module's `currentCueMatch` re-derives the leading index CLIENT-side so the
// cue sheet (below) can highlight the matching row — a UI-only re-derivation
// of a value the server already computed, not a new claim.
//
// T-H4 (user feedback, 2026-08-02) redesigns the presentation layer to read
// as a CONSOLE surface, not a document, per two concrete defects the user
// found plus an MA3-benchmarked layout:
//   - Defect 1: "Executor 101Sequence 50" — two adjacent <span>s with no
//     layout gap between them read as one glued string. Fixed by the tile
//     layout below (each fact gets its own line/row, never adjacent inline
//     spans with no separator).
//   - Defect 2: the history's raw ISO timestamp glued to the command text
//     ("2026-08-02T10:38:32...Go+ Executor 191"). Fixed by `formatHistoryTime`
//     (local HH:MM:SS) plus a real layout gap between the two fields.
//   - Layout: executors render as a GRID of small tiles (`ExecutorTile`),
//     never a vertical list — MA3's own executor-bar convention. A tile
//     shows only the number (corner), sequence name (title), current cue
//     (emphasized), and a status+Go/Off footer; the full cue list stays
//     COLLAPSED behind a click that opens ONE `CueSheet` at a time (a
//     compact table: Cue No / 이름, current row highlighted) — never every
//     tile's cue list expanded simultaneously.
// None of this changes what is CLAIMED — the three status grades, the pulse
// window, the fail-closed button posture, the current-cue three-way branch,
// and the "never estimate progress/time" boundary are all unchanged; only
// how they are laid out on screen changes.
//
// No internal hooks, same convention as DashBoard.tsx — a hook-free
// component callable directly as a plain function in tests (this project has
// no DOM/jsdom test harness; see protocol.ts's own header note). "Which cue
// sheet is open" is therefore a CONTROLLED prop (`openExecutorNo` /
// `onToggleExecutor`), lifted to App.tsx's own `useState` — the same pattern
// `chatCollapsed`/`sectionTileSizes` already use there.
import {
  type CueExecutorEntry,
  type CueHistoryEntry,
  type CueItem,
  type CueMonitorState,
} from "../protocol";
import { formatSyncTime } from "./DashBoard";

export interface CueMonitorProps {
  cueMonitor: CueMonitorState;
  /** Dispatches a manual `cue_monitor_request`. Optional, same pattern as
   * `DashBoard`'s `onRefresh` — a stub caller never breaks. */
  onRefresh?: () => void;
  /** Whether this executor is currently shown as running (mirrors
   * DashBoard's `isItemRunning` — same `panel.running` app-observed state,
   * itself never a claim about the console's own playback). */
  isExecutorRunning?: (executorNo: number) => boolean;
  /** Fires `panel_execute` (Go+) — the SAME wire path DashBoard's executor
   * tiles use; no second route to the console exists. */
  onExecute?: (executorNo: number) => void;
  /** Fires `panel_stop` (Off) — same path as `onExecute`. */
  onStop?: (executorNo: number) => void;
  /** T-H4 — which executor's cue sheet is open, or `null`/omitted for none.
   * Controlled by the caller (App.tsx `useState`) — this component has no
   * internal state of its own (see module header). */
  openExecutorNo?: number | null;
  /** T-H4 — toggles the given executor's cue sheet (open <-> closed). A
   * caller SHOULD implement "one at a time" by tracking a single open
   * executor number and flipping it to `null` when the same one reopens. */
  onToggleExecutor?: (executorNo: number) => void;
}

/** The three status grades T-H's chip renders — see module header note for
 * what each does and does NOT claim. */
export type LastActionGrade = "confirmed" | "failed" | "unknown";

/** Derives the grade from `entry.last_app_action` — pure, no clock read. */
export function lastActionGrade(entry: CueExecutorEntry): LastActionGrade {
  const action = entry.last_app_action;
  if (action === null || action === undefined) return "unknown";
  return action.ok ? "confirmed" : "failed";
}

/** Icon + text together (never a color-only signal) for each grade. */
const GRADE_LABEL: Record<LastActionGrade, string> = {
  confirmed: "✓ 확인됨",
  failed: "✕ 실패/무응답",
  unknown: "○ 미확인",
};

/** How long after a confirmed action the acknowledgement pulse plays. */
export const APP_ACTION_PULSE_WINDOW_MS = 6_000;

/**
 * `HH:MM:SS` age spelled out in relative Korean ("12초 전"), or `""` when
 * `ts` cannot be parsed. `nowMs` is an explicit parameter (not a hidden
 * `Date.now()` read) so this stays a pure, deterministically testable
 * function — the caller (a live render) passes the real clock.
 */
export function formatRelativeAgo(ts: string, nowMs: number = Date.now()): string {
  const then = Date.parse(ts);
  if (Number.isNaN(then)) return "";
  const diffMs = nowMs - then;
  if (diffMs < 5_000) return "방금 전";
  const sec = Math.floor(diffMs / 1000);
  if (sec < 60) return `${sec}초 전`;
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min}분 전`;
  const hour = Math.floor(min / 60);
  return `${hour}시간 전`;
}

/** Whether a `last_app_action.ts` is fresh enough to still pulse. */
export function isRecentAppAction(ts: string, nowMs: number = Date.now()): boolean {
  const then = Date.parse(ts);
  if (Number.isNaN(then)) return false;
  const diffMs = nowMs - then;
  return diffMs >= 0 && diffMs < APP_ACTION_PULSE_WINDOW_MS;
}

/**
 * T-H4 defect 2 — the history row's LOCAL wall-clock time, `HH:MM:SS`. The
 * server emits a raw ISO-8601 UTC timestamp (`AuditLog.record`'s
 * `datetime.isoformat()`); rendering that verbatim next to the command with
 * no separator is exactly the "unreadable, glued to the command" defect the
 * user reported. Falls back to the raw string (never a blank) when `ts`
 * cannot be parsed — an honest "couldn't format this" beats silently
 * dropping the timestamp.
 */
export function formatHistoryTime(ts: string): string {
  const date = new Date(ts);
  if (Number.isNaN(date.getTime())) return ts;
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
}

/**
 * Fail-closed reason an executor's run/stop button is disabled, or `null`
 * when it is fireable. Only a console-confirmed ("ok") or an answered-but-
 * unassigned executor is fireable — "unavailable" (the live identity read
 * itself failed) is refused, same posture as DashBoard's unresolved-executor
 * guard (never fire on a target the console did not just confirm exists).
 */
export function executorFireDisabledReason(entry: CueExecutorEntry): string | null {
  if (entry.status === "unavailable") {
    return "콘솔 상태를 확인할 수 없어 안전을 위해 버튼이 비활성화되었습니다.";
  }
  return null;
}

/** The sequence identity line, or why one is not shown. */
export function sequenceLabel(entry: CueExecutorEntry): string {
  if (entry.status === "unassigned") return "할당된 시퀀스 없음";
  if (entry.status === "unavailable") return "확인 불가 — 콘솔 응답 없음";
  return entry.sequence_name && entry.sequence_name.length > 0
    ? entry.sequence_name
    : `시퀀스 ${entry.sequence_no ?? "?"}`;
}

/**
 * The current-cue line — independently Optional (contract item 1): an
 * "unavailable" read is expected and normal (no MA3 property confirmed to
 * expose it), so this always explains the gap rather than rendering a blank.
 *
 * Kept verbatim for RunbookMode.tsx, which still wants the full sentence
 * inline (one big row at a time there, so repetition is not the problem
 * T-H2 fixes). CueMonitor's own row rendering below uses the SHORT
 * `currentCueRowView` instead — see the T-H2 module note.
 */
export function currentCueLabel(entry: CueExecutorEntry): string {
  const current = entry.current_cue;
  if (current === null || current === undefined || current.status !== "ok" || !current.value) {
    return "현재 큐: 확인 불가 — 이 콘솔/응답기 조합에서 읽을 수 있는 속성이 확인되지 않았습니다";
  }
  return `현재 큐: ${current.value}`;
}

/**
 * T-H2 (user feedback, 2026-08-02): the FULL reason a current-cue read is
 * unavailable, or `null` when the entry actually has a value (nothing to
 * explain). Distinct from `currentCueLabel` in two ways: (a) it names the
 * property names actually tried (`current_cue.tried`), so two entries that
 * failed for genuinely DIFFERENT reasons produce genuinely different text —
 * this is what lets `currentCueBannerState` below tell "every row failed
 * the same way" apart from "rows failed for different reasons" once the
 * responder is extended and some rows start answering; (b) it returns
 * `null` (not a sentence) when there IS a value, so callers can test
 * "has an explanation" without re-deriving `hasValue` themselves.
 */
export function currentCueUnavailableReason(entry: CueExecutorEntry): string | null {
  const current = entry.current_cue;
  if (current && current.status === "ok" && current.value) return null;
  const tried = current?.tried;
  const triedClause =
    tried && tried.length > 0 ? `${tried.join(", ")} 속성을` : "읽을 수 있는 속성이";
  return `현재 큐 확인 불가 — 이 콘솔/응답기 조합에서 ${triedClause} 확인되지 않았습니다`;
}

/** The SHORT per-row placeholder T-H2 replaces the repeated sentence with:
 * the value when there is one, else a bare dash — never a silent blank,
 * never the long sentence repeated on every row. The full reason still
 * rides along as `reason`, for the row's `title` tooltip. */
export interface CurrentCueRowView {
  hasValue: boolean;
  label: string;
  reason: string | null;
}

export function currentCueRowView(entry: CueExecutorEntry): CurrentCueRowView {
  const current = entry.current_cue;
  const hasValue = !!(current && current.status === "ok" && current.value);
  if (hasValue) {
    return { hasValue: true, label: `현재 큐: ${current!.value}`, reason: null };
  }
  return { hasValue: false, label: "현재 큐 —", reason: currentCueUnavailableReason(entry) };
}

/**
 * T-H2 §3 — the panel-level banner's three-way branch. ONLY the "uniform"
 * branch renders the shared-fact banner (per-row text stays short either
 * way): every "ok"-status executor's current-cue read failed, and every one
 * of them failed for the exact SAME reason — the observed present-day case
 * (a single fixed candidate-property list), stated once instead of 8 times.
 *
 * "mixed" (rows fail for genuinely different reasons) and "none" (at least
 * one row already has a value, or there is nothing to report at all) both
 * render NO banner — a blanket claim would be false in either case, so each
 * row is left to speak for itself via `currentCueRowView`.
 *
 * Non-"ok" executors (unassigned/unavailable) never attempt a current-cue
 * read in the first place (see `ExecutorTile` below) and are excluded.
 */
export type CurrentCueBannerState =
  | { kind: "none" }
  | { kind: "uniform"; reason: string }
  | { kind: "mixed" };

export function currentCueBannerState(executors: CueExecutorEntry[]): CurrentCueBannerState {
  const reasons = executors
    .filter((entry) => entry.status === "ok")
    .map((entry) => currentCueUnavailableReason(entry));
  if (reasons.length === 0) return { kind: "none" };
  if (reasons.some((reason) => reason === null)) return { kind: "none" };
  const unique = new Set(reasons as string[]);
  if (unique.size > 1) return { kind: "mixed" };
  return { kind: "uniform", reason: reasons[0] as string };
}

/**
 * T-H3/T-H4 — the leading integer off a composed current-cue value
 * (`"<index>"` or `"<index> — <name>"`, per server/web/cue_monitor.py's own
 * composition), or `null` when there is none to find. A UI-only
 * re-derivation of a value the server already parsed — used solely to
 * decide which row of the cue sheet to highlight, never to re-derive the
 * displayed text itself (that stays `currentCueRowView.label` verbatim).
 */
export function currentCueIndexFromValue(value: string | null | undefined): number | null {
  if (!value) return null;
  const match = /^(\d+)/.exec(value);
  return match ? Number(match[1]) : null;
}

/** Which cue in `entry.cues` the current-cue value points at, or `null`
 * when there is no current-cue value or no cue in the list carries a
 * matching identifier. Mirrors server/web/cue_monitor.py's own preference
 * order (`_cue_name_for_index`): the responder's real cue number
 * (`cue_no`) first, the pool slot (`no`) as a fallback — so the row this
 * highlights is the SAME row the server would have named, had it found one. */
export interface CurrentCueMatch {
  by: "cue_no" | "no";
  index: number;
}

export function currentCueMatch(entry: CueExecutorEntry): CurrentCueMatch | null {
  const current = entry.current_cue;
  if (!current || current.status !== "ok" || !current.value) return null;
  const index = currentCueIndexFromValue(current.value);
  if (index === null) return null;
  if (entry.cues.some((cue) => cue.cue_no === index)) return { by: "cue_no", index };
  if (entry.cues.some((cue) => cue.no === index)) return { by: "no", index };
  return null;
}

/** Whether `cue` is the one row `match` (from `currentCueMatch`) points at. */
export function isCueRowCurrent(match: CurrentCueMatch | null, cue: CueItem): boolean {
  if (match === null) return false;
  return match.by === "cue_no" ? cue.cue_no === match.index : cue.no === match.index;
}

export function ExecutorStatusChip({ entry }: { entry: CueExecutorEntry }) {
  const grade = lastActionGrade(entry);
  const action = entry.last_app_action;
  const pulsing = grade === "confirmed" && !!action && isRecentAppAction(action.ts);
  const title = action
    ? `${action.command} · ${action.ok ? "ok" : "실패"} · ${formatRelativeAgo(action.ts)}`
    : "이 실행기로 앱이 보낸 명령이 아직 없습니다 — 콘솔에서 직접 조작했을 수 있습니다.";
  return (
    <span
      className={`cue-status-chip cue-status-chip-${grade}${pulsing ? " cue-status-chip-pulse" : ""}`}
      title={title}
    >
      {GRADE_LABEL[grade]}
      {action && <span className="cue-status-chip-age">{formatRelativeAgo(action.ts)}</span>}
    </span>
  );
}

export function ExecutorActions({
  entry,
  running,
  onExecute,
  onStop,
}: {
  entry: CueExecutorEntry;
  running: boolean;
  onExecute?: (executorNo: number) => void;
  onStop?: (executorNo: number) => void;
}) {
  const disabledReason = executorFireDisabledReason(entry);
  const fireable = disabledReason === null;
  const handleClick = () => {
    if (running) {
      onStop?.(entry.executor_no);
    } else {
      onExecute?.(entry.executor_no);
    }
  };
  return (
    <div className="cue-monitor-actions">
      <button
        type="button"
        className={`cue-monitor-action-btn${running ? " cue-monitor-action-btn-stop" : ""}`}
        onClick={handleClick}
        disabled={!fireable}
        aria-label={`Executor ${entry.executor_no} ${running ? "정지" : "실행"}`}
      >
        {running ? "■ 정지" : "▶ 실행"}
      </button>
      {disabledReason && <span className="cue-monitor-action-reason">{disabledReason}</span>}
    </div>
  );
}

/**
 * T-H4 — one executor as an MA3-style tile: (a) executor number small in a
 * corner, (b) sequence name as the tile's own title, (c) current cue
 * emphasized below it (the value an operator checks most often), (d)
 * status chip + Go/Off footer. The full cue list stays collapsed; clicking
 * the tile body toggles its `CueSheet` (rendered by the caller, `CueMonitor`
 * below) rather than expanding inline — see module header.
 *
 * The tile itself is the click target for OPENING the sheet; the Go/Off
 * button inside it stops that click from bubbling (`stopPropagation`) so a
 * press on Go/Off never also toggles the sheet open/closed.
 */
export function ExecutorTile({
  entry,
  running,
  isOpen,
  onToggleOpen,
  onExecute,
  onStop,
}: {
  entry: CueExecutorEntry;
  running?: boolean;
  isOpen?: boolean;
  onToggleOpen?: (executorNo: number) => void;
  onExecute?: (executorNo: number) => void;
  onStop?: (executorNo: number) => void;
}) {
  const handleToggle = () => onToggleOpen?.(entry.executor_no);
  const view = currentCueRowView(entry);
  return (
    <div
      className={`cue-tile${isOpen ? " cue-tile-open" : ""}`}
      data-executor-no={entry.executor_no}
      role="button"
      tabIndex={0}
      aria-expanded={!!isOpen}
      aria-label={`Executor ${entry.executor_no} 큐 시트 ${isOpen ? "닫기" : "열기"}`}
      onClick={handleToggle}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          handleToggle();
        }
      }}
    >
      <div className="cue-tile-topline">
        <span className="cue-tile-no">{entry.executor_no}</span>
        <ExecutorStatusChip entry={entry} />
      </div>
      <div className="cue-tile-sequence">{sequenceLabel(entry)}</div>
      <div className="cue-tile-current-cue" title={view.reason ?? undefined}>
        {view.label}
      </div>
      <div
        className="cue-tile-footer"
        onClick={(event) => event.stopPropagation()}
        onKeyDown={(event) => event.stopPropagation()}
      >
        <ExecutorActions entry={entry} running={running ?? false} onExecute={onExecute} onStop={onStop} />
      </div>
    </div>
  );
}

/**
 * T-H4 — the collapsed cue list, opened for exactly one executor at a time
 * (`CueMonitor` renders at most one). A compact table (`Cue No` / `이름`)
 * mirroring an MA3 sequence sheet, NOT the bullet list T-H4 replaces — only
 * columns this project's data actually carries (no invented Trig/Fade/Delay).
 * The current cue's row is highlighted via `currentCueMatch`/`isCueRowCurrent`
 * — the SAME index the tile's own `currentCueRowView` label already shows,
 * re-matched against the cue list rather than re-derived independently.
 */
export function CueSheet({
  entry,
  onClose,
}: {
  entry: CueExecutorEntry;
  onClose?: () => void;
}) {
  const match = currentCueMatch(entry);
  return (
    <section className="cue-sheet" aria-label={`Executor ${entry.executor_no} 큐 시트`}>
      <header className="cue-sheet-header">
        <span className="cue-sheet-title">
          Executor {entry.executor_no} — {sequenceLabel(entry)}
        </span>
        <button
          type="button"
          className="cue-sheet-close"
          onClick={() => onClose?.()}
          aria-label="큐 시트 닫기"
        >
          ✕
        </button>
      </header>
      <table className="cue-sheet-table">
        <thead>
          <tr>
            <th>Cue No</th>
            <th>이름</th>
          </tr>
        </thead>
        <tbody>
          {entry.cues.map((cue) => (
            <tr
              key={cue.no}
              className={isCueRowCurrent(match, cue) ? "cue-sheet-row-current" : undefined}
            >
              <td className="cue-sheet-cue-no">{cue.cue_no !== undefined ? cue.cue_no : `#${cue.no}`}</td>
              <td>{cue.name}</td>
            </tr>
          ))}
          {entry.cues.length === 0 && (
            <tr>
              <td className="cue-sheet-empty" colSpan={2}>
                큐 없음
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </section>
  );
}

/** T-H2 — renders the shared-fact banner ONLY in the "uniform" branch; `null`
 * (no DOM node at all) for "mixed"/"none", per `currentCueBannerState`. */
function CurrentCueBanner({ executors }: { executors: CueExecutorEntry[] }) {
  const state = currentCueBannerState(executors);
  if (state.kind !== "uniform") return null;
  return (
    <div className="cue-monitor-current-cue-banner" role="status">
      ⚠ {state.reason}
    </div>
  );
}

function CueHistoryRow({ entry }: { entry: CueHistoryEntry }) {
  return (
    <li className={`cue-monitor-history-item${entry.ok ? "" : " cue-monitor-history-failed"}`}>
      <span className="cue-monitor-history-ts">{formatHistoryTime(entry.ts)}</span>
      <span className="cue-monitor-history-command">{entry.command}</span>
    </li>
  );
}

export function CueMonitor({
  cueMonitor,
  onRefresh,
  isExecutorRunning,
  onExecute,
  onStop,
  openExecutorNo,
  onToggleExecutor,
}: CueMonitorProps) {
  const handleRefresh = () => {
    if (onRefresh) {
      onRefresh();
    } else {
      // eslint-disable-next-line no-console -- App.tsx wires the real dispatch.
      console.debug("cue monitor: manual refresh requested");
    }
  };

  const staleSuffix = cueMonitor.stale ? " (오래됨)" : "";
  const openEntry =
    openExecutorNo === null || openExecutorNo === undefined
      ? null
      : (cueMonitor.executors.find((entry) => entry.executor_no === openExecutorNo) ?? null);

  return (
    <section className="cue-monitor" aria-label="라이브 큐 진행 모니터">
      <header className="cue-monitor-header">
        <span className="cue-monitor-title">큐 진행 모니터</span>
        <span className="cue-monitor-syncline">
          동기화 {formatSyncTime(cueMonitor.lastSyncAt)}
          {staleSuffix}
        </span>
        <button
          className="cue-monitor-refresh"
          onClick={handleRefresh}
          aria-label="큐 모니터 새로고침"
        >
          ⟳ 새로고침
        </button>
      </header>
      <CurrentCueBanner executors={cueMonitor.executors} />
      <div className="cue-monitor-body">
        <div className="cue-monitor-grid">
          {cueMonitor.executors.map((entry) => (
            <ExecutorTile
              key={entry.executor_no}
              entry={entry}
              running={isExecutorRunning?.(entry.executor_no) ?? false}
              isOpen={openExecutorNo === entry.executor_no}
              onToggleOpen={onToggleExecutor}
              onExecute={onExecute}
              onStop={onStop}
            />
          ))}
          {cueMonitor.executors.length === 0 && (
            <div className="cue-monitor-empty">확인된 익스큐터 없음</div>
          )}
        </div>
        {openEntry && (
          <CueSheet entry={openEntry} onClose={() => onToggleExecutor?.(openEntry.executor_no)} />
        )}
        <div className="cue-monitor-history">
          <span className="cue-monitor-history-title">최근 실행 이력</span>
          <ul>
            {cueMonitor.history.map((entry, index) => (
              <CueHistoryRow key={`${entry.ts}-${index}`} entry={entry} />
            ))}
            {cueMonitor.history.length === 0 && (
              <li className="cue-monitor-history-empty">실행 이력 없음</li>
            )}
          </ul>
        </div>
      </div>
    </section>
  );
}
