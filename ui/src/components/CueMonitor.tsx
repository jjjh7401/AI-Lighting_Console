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
// No internal hooks, same convention as DashBoard.tsx — a hook-free
// component callable directly as a plain function in tests (this project has
// no DOM/jsdom test harness; see protocol.ts's own header note).
import { type CueExecutorEntry, type CueHistoryEntry, type CueMonitorState } from "../protocol";
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
 * read in the first place (see `CueExecutorRow` below) and are excluded.
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

export function CueExecutorRow({
  entry,
  running,
  onExecute,
  onStop,
}: {
  entry: CueExecutorEntry;
  running?: boolean;
  onExecute?: (executorNo: number) => void;
  onStop?: (executorNo: number) => void;
}) {
  return (
    <li className="cue-monitor-executor" data-executor-no={entry.executor_no}>
      <div className="cue-monitor-executor-header">
        <span className="cue-monitor-executor-no">Executor {entry.executor_no}</span>
        <span className="cue-monitor-sequence-name">{sequenceLabel(entry)}</span>
        <ExecutorStatusChip entry={entry} />
      </div>
      {entry.status === "ok" && (
        <>
          <div
            className="cue-monitor-current-cue"
            title={currentCueRowView(entry).reason ?? undefined}
          >
            {currentCueRowView(entry).label}
          </div>
          <ol className="cue-monitor-cue-list">
            {entry.cues.map((cue) => (
              <li key={cue.no} className="cue-monitor-cue-item">
                {cue.cue_no !== undefined ? `Cue ${cue.cue_no}` : `#${cue.no}`} — {cue.name}
              </li>
            ))}
            {entry.cues.length === 0 && <li className="cue-monitor-cue-empty">큐 없음</li>}
          </ol>
        </>
      )}
      <ExecutorActions
        entry={entry}
        running={running ?? false}
        onExecute={onExecute}
        onStop={onStop}
      />
    </li>
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
      <span className="cue-monitor-history-ts">{entry.ts}</span>
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
        <ul className="cue-monitor-executors">
          {cueMonitor.executors.map((entry) => (
            <CueExecutorRow
              key={entry.executor_no}
              entry={entry}
              running={isExecutorRunning?.(entry.executor_no) ?? false}
              onExecute={onExecute}
              onStop={onStop}
            />
          ))}
          {cueMonitor.executors.length === 0 && (
            <li className="cue-monitor-empty">확인된 익스큐터 없음</li>
          )}
        </ul>
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
