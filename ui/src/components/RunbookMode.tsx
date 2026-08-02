// Volunteer runbook mode (T-E, UI-only — ad-hoc contract, no SPEC on file;
// coordinator directive, 2026-08-02).
//
// An extreme-simplicity view for a non-expert operator: one big vertical
// list of the show's songs/cues (one row per executor entry from
// `cue_monitor`, since the executor is the only unit the existing
// panel_execute path can fire), each row down to (a) a running number,
// (b) the song/sequence name, (c) exactly one "run" button, and (d) a
// caution line — shown ONLY when there is something to explain (an unknown
// current cue, an unassigned executor, or a console that would not answer).
// No tool list, no full pool catalog, no settings, no approval cards live
// here — those are hidden by App.tsx's mode switch, not by this component.
//
// Sources ONLY `cue_monitor` state (no new server endpoint, per contract).
// The run button reuses the EXACT SAME panel_execute wire path DashBoard's
// executor tiles use (App.tsx wires it in) — a required approval/gate still
// surfaces the normal ApprovalCard/ReviewCard, since this mode never
// bypasses that flow (App.tsx keeps rendering them above/below this list).
//
// No internal hooks, same convention as CueMonitor.tsx/DashBoard.tsx — a
// hook-free component callable directly as a plain function in tests (this
// project has no DOM/jsdom test harness; see protocol.ts's own header note).
import { type CueExecutorEntry, type CueMonitorState } from "../protocol";
import { formatSyncTime } from "./DashBoard";
import { currentCueLabel, sequenceLabel } from "./CueMonitor";

export interface RunbookModeProps {
  cueMonitor: CueMonitorState;
  /** Whether pressing "run" on an executor is currently shown as running
   * (mirrors DashBoard's `isItemRunning` — same `panel.running` state). */
  isExecutorRunning?: (executorNo: number) => boolean;
  /** Fires the executor's run/stop — same panel_execute/panel_stop path the
   * console-info dashboard's executor tiles already use. */
  onExecute?: (executorNo: number) => void;
  /** Manual `cue_monitor_request` dispatch, same as CueMonitor's refresh. */
  onRefresh?: () => void;
}

/**
 * The one-line reason a row cannot safely be run right now, or `null` when
 * there is nothing to warn about. Independently Optional by design (item d
 * of the contract: "주의사항 한 줄(있으면)만 노출") — never fabricated,
 * only ever derived from a field `cue_monitor` already reports.
 */
export function runbookCaution(entry: CueExecutorEntry): string | null {
  if (entry.status === "unassigned") {
    return "이 실행기에는 배정된 시퀀스가 없습니다 — 실행할 수 없습니다.";
  }
  if (entry.status === "unavailable") {
    return "콘솔이 응답하지 않아 상태를 확인할 수 없습니다 — 실행할 수 없습니다.";
  }
  if (entry.current_cue === null || entry.current_cue.status !== "ok") {
    return "현재 큐 번호를 확인할 수 없습니다 — 실행하면 다음 큐로 넘어갑니다.";
  }
  return null;
}

/** Literal description of what pressing the button does (never the generic
 * "지금 실행" — the beginner UX requirement asks for e.g. "큐 3 실행"). */
export function runbookButtonLabel(entry: CueExecutorEntry, running: boolean): string {
  if (entry.status !== "ok") return "실행 불가";
  if (running) return "정지";
  const currentCue = entry.current_cue;
  const cueValue = currentCue && currentCue.status === "ok" ? currentCue.value : undefined;
  return cueValue ? `큐 ${cueValue} 실행` : "다음 큐 실행";
}

/** Only an "ok" executor is fireable — an unassigned/unavailable row has no
 * console-confirmed target to safely advance (fail-closed, same posture as
 * DashBoard's unresolved-executor guard). */
export function runbookIsRunnable(entry: CueExecutorEntry): boolean {
  return entry.status === "ok";
}

function RunbookRow({
  entry,
  index,
  running,
  onExecute,
}: {
  entry: CueExecutorEntry;
  index: number;
  running: boolean;
  onExecute?: (executorNo: number) => void;
}) {
  const runnable = runbookIsRunnable(entry);
  const caution = runbookCaution(entry);
  return (
    <li className="runbook-item" data-executor-no={entry.executor_no}>
      <div className="runbook-item-main">
        <span className="runbook-item-no">{index + 1}</span>
        <span className="runbook-item-name">{sequenceLabel(entry)}</span>
        <button
          className={`runbook-item-run${running ? " runbook-item-run-active" : ""}`}
          onClick={() => onExecute?.(entry.executor_no)}
          disabled={!runnable}
        >
          {runbookButtonLabel(entry, running)}
        </button>
      </div>
      {entry.status === "ok" && (
        <div className="runbook-item-current-cue">{currentCueLabel(entry)}</div>
      )}
      {caution && <div className="runbook-item-caution">⚠ {caution}</div>}
      {entry.status === "ok" && entry.cues.length > 0 && (
        <ol className="runbook-item-cues">
          {entry.cues.map((cue) => (
            <li key={cue.no} className="runbook-item-cue">
              {cue.cue_no !== undefined ? `큐 ${cue.cue_no}` : `#${cue.no}`} — {cue.name}
            </li>
          ))}
        </ol>
      )}
    </li>
  );
}

export function RunbookMode({ cueMonitor, isExecutorRunning, onExecute, onRefresh }: RunbookModeProps) {
  const staleSuffix = cueMonitor.stale ? " (오래됨 — 콘솔 연결을 확인하세요)" : "";

  return (
    <section className="runbook-mode" aria-label="런북 모드">
      <header className="runbook-header">
        <span className="runbook-title">오늘의 곡·큐 순서</span>
        <span className="runbook-syncline">
          동기화 {formatSyncTime(cueMonitor.lastSyncAt)}
          {staleSuffix}
        </span>
        <button className="runbook-refresh" onClick={() => onRefresh?.()} aria-label="목록 새로고침">
          ⟳ 새로고침
        </button>
      </header>
      {cueMonitor.executors.length === 0 ? (
        <div className="runbook-empty">
          확인된 곡·큐가 없습니다 — 콘솔이 아직 연결되지 않았거나 응답이 없을 수 있습니다.
        </div>
      ) : (
        <ol className="runbook-list">
          {cueMonitor.executors.map((entry, index) => (
            <RunbookRow
              key={entry.executor_no}
              entry={entry}
              index={index}
              running={isExecutorRunning?.(entry.executor_no) ?? false}
              onExecute={onExecute}
            />
          ))}
        </ol>
      )}
    </section>
  );
}
