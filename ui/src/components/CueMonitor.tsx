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
 */
export function currentCueLabel(entry: CueExecutorEntry): string {
  const current = entry.current_cue;
  if (current === null || current === undefined || current.status !== "ok" || !current.value) {
    return "현재 큐: 확인 불가 — 이 콘솔/응답기 조합에서 읽을 수 있는 속성이 확인되지 않았습니다";
  }
  return `현재 큐: ${current.value}`;
}

function CueExecutorRow({ entry }: { entry: CueExecutorEntry }) {
  return (
    <li className="cue-monitor-executor" data-executor-no={entry.executor_no}>
      <div className="cue-monitor-executor-header">
        <span className="cue-monitor-executor-no">Executor {entry.executor_no}</span>
        <span className="cue-monitor-sequence-name">{sequenceLabel(entry)}</span>
      </div>
      {entry.status === "ok" && (
        <>
          <div className="cue-monitor-current-cue">{currentCueLabel(entry)}</div>
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
    </li>
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

export function CueMonitor({ cueMonitor, onRefresh }: CueMonitorProps) {
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
      <div className="cue-monitor-body">
        <ul className="cue-monitor-executors">
          {cueMonitor.executors.map((entry) => (
            <CueExecutorRow key={entry.executor_no} entry={entry} />
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
