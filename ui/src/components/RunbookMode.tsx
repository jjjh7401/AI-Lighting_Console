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
// The execution view sources `cue_monitor`; the adjacent director timeline is
// a server-authored review projection with no executable command fields.
// Both remain read-only until App.tsx drives the existing approval route.
//
// No internal hooks, same convention as CueMonitor.tsx/DashBoard.tsx — a
// hook-free component callable directly as a plain function in tests (this
// project has no DOM/jsdom test harness; see protocol.ts's own header note).
import type { ReactNode } from "react";

import {
  type CueExecutorEntry,
  type CueMonitorState,
  type SongTimelineView,
} from "../protocol";
import { CueSheetTimeline } from "./CueSheetTimeline";
import { SongTimeline } from "./SongTimeline";
import { formatSyncTime } from "./DashBoard";
import { sequenceLabel } from "./CueMonitor";

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
  timeline?: SongTimelineView | null;
  timelineStale?: boolean;
  timelineIsExample?: boolean;
  /** Adds a visibly marked, non-executable fixture for UI review only. */
  onShowTimelineExample?: () => void;
  /** Timeline library panel (save/load named versions) — rendered above the
   * timeline when App supplies it; RunbookMode itself stays hook-free. */
  librarySlot?: ReactNode;
  /** t281 — 큐시트 초안 편집 배선. 전부 선택 prop 이라, 넘기지 않으면
   * 큐시트는 t280 의 읽기 전용 모습 그대로다. */
  onSelectCue?: (cueNumber: number) => void;
  onUndoDraft?: () => void;
  onRedoDraft?: () => void;
  onSaveDraft?: () => void;
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

/** Best-effort cue-sheet grouping derived only from console-authored cue
 * names. No musical timing is invented: unrecognised names remain a cue. */
export type RunbookSection = "Intro" | "Verse" | "Pre-Chorus" | "Chorus" | "Bridge" | "Outro" | "Cue";

export function runbookSection(name: string): RunbookSection {
  const value = name.toLowerCase();
  if (/\bintro\b|opening|start/.test(value)) return "Intro";
  if (/\bpre[- ]?chorus\b/.test(value)) return "Pre-Chorus";
  if (/\bchorus\b|hook|refrain/.test(value)) return "Chorus";
  if (/\bverse\b/.test(value)) return "Verse";
  if (/\bbridge\b|solo|breakdown/.test(value)) return "Bridge";
  if (/\boutro\b|ending|end song|blackout/.test(value)) return "Outro";
  return "Cue";
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
  const activeCue = entry.current_cue?.status === "ok" ? entry.current_cue.value : null;

  return (
    <li className={`runbook-item${running ? " runbook-item-live" : ""}`} data-executor-no={entry.executor_no}>
      <div className="runbook-track-header">
        <span className="runbook-item-no">{String(index + 1).padStart(2, "0")}</span>
        <div className="runbook-track-title">
          <span className="runbook-track-kicker">EXEC {entry.executor_no}</span>
          <span className="runbook-item-name">{sequenceLabel(entry)}</span>
        </div>
        <div className="runbook-track-status">
          <span className={`runbook-status-dot${running ? " is-live" : ""}`} />
          {running ? "LIVE" : "READY"}
        </div>
        <button
          className={`runbook-item-run${running ? " runbook-item-run-active" : ""}`}
          onClick={() => onExecute?.(entry.executor_no)}
          disabled={!runnable}
        >
          {runbookButtonLabel(entry, running)}
        </button>
      </div>

      {entry.status === "ok" && entry.cues.length > 0 && (
        <div className="runbook-cue-sheet">
          <div className="runbook-sheet-heading">
            <span>CUE</span><span>SECTION / SCENE</span><span>LOOK / NOTE</span>
          </div>
          {entry.cues.map((cue, cueIndex) => {
            const cueNo = String(cue.cue_no ?? cue.no);
            const section = runbookSection(cue.name);
            const isCurrent = activeCue === cueNo;
            const sectionChanged = cueIndex === 0 || runbookSection(entry.cues[cueIndex - 1].name) !== section;
            return (
              <div className={`runbook-sheet-row${isCurrent ? " is-current" : ""}`} key={cue.no}>
                <span className="runbook-sheet-cue">{cueNo}{isCurrent && <em>CURRENT</em>}</span>
                <span className={`runbook-sheet-section section-${section.toLowerCase().replace("-", "")}`}>
                  {sectionChanged ? section : ""}
                </span>
                <span className="runbook-sheet-name">{cue.name}</span>
              </div>
            );
          })}
        </div>
      )}
      {caution && <div className="runbook-item-caution">⚠ {caution}</div>}
    </li>
  );
}

export function RunbookMode({
  cueMonitor,
  isExecutorRunning,
  onExecute,
  onRefresh,
  timeline = null,
  timelineStale = false,
  timelineIsExample = false,
  onShowTimelineExample,
  librarySlot = null,
  onSelectCue,
  onUndoDraft,
  onRedoDraft,
  onSaveDraft,
}: RunbookModeProps) {
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
      {librarySlot}
      {timeline === null ? (
        <section className="runbook-timeline-pending" aria-label="감독 타임라인 대기">
          <div>
            <p>감독 타임라인</p>
            <span>실제 설계가 완료되면 구간별 Cue 계획이 실행 런북 위에 표시됩니다.</span>
          </div>
          {onShowTimelineExample && (
            <button className="runbook-timeline-example" onClick={onShowTimelineExample}>
              예제 보기
            </button>
          )}
        </section>
      ) : (
        <>
          {/* t280 — 두 축(가로 타임라인 창 + 세로 큐시트) 읽기 전용 뷰.
              기존 카드형 타임라인은 아래에 그대로 남는다. */}
          <CueSheetTimeline
            timeline={timeline}
            onSelectCue={onSelectCue}
            onUndoDraft={onUndoDraft}
            onRedoDraft={onRedoDraft}
            onSaveDraft={onSaveDraft}
          />
          <SongTimeline
            timeline={timeline}
            cueMonitor={cueMonitor}
            stale={timelineStale}
            isExample={timelineIsExample}
          />
        </>
      )}
      <p className="runbook-execution-label">실행 런북 · 현재 콘솔 큐</p>
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
