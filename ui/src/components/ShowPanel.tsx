// Show-control panel — the console wing beside the chat
// (SPEC-COPILOT-SHOWUI-001 M4, design.md §5/§6/§8).
//
// The grid is the wire order, unsorted and append-only (REQ-SHOWUI-017): a tile
// that moves under the operator's finger mid-show is a misfire waiting to
// happen. The fixed corner holds All Off, which despite its name is a
// DESTRUCTIVE FIRE action and takes arm→fire — the per-tile Off is the stop
// class and takes one press (REQ-SHOWUI-012/024; the two classes are disjoint).
import { useEffect, useState } from "react";

import { PanelTile, type TileGate } from "./PanelTile";
import {
  buildPanelStop,
  buildPanelUnpin,
  healthLabel,
  type PanelItem,
  type PanelItemState,
  type PanelSection,
  type PanelState,
  type StatusState,
} from "../protocol";

// -- arm → fire (REQ-SHOWUI-024, design.md §5) --------------------------------

/**
 * How long an armed control stays armed.
 *
 * Long enough to reach with a gloved hand in the dark, short enough that a
 * control armed by accident does not sit waiting for the next brush past it.
 */
export const ARM_TIMEOUT_MS = 4000;

export interface ArmState {
  armedAt: number | null;
}

export const ARM_IDLE: ArmState = { armedAt: null };

export function isArmed(state: ArmState, now: number): boolean {
  return state.armedAt !== null && now - state.armedAt < ARM_TIMEOUT_MS;
}

/**
 * One press of an arm→fire control.
 *
 * The first press arms and sends NOTHING; the second within the window fires.
 * There is no confirmation modal anywhere in this path — safety is the rail and
 * the two presses (REQ-SHOWUI-019, design.md §7).
 *
 * Time is a parameter rather than a closure over `Date.now` so the machine is
 * pure: the expiry is decided by comparison at press time, not by a timer, and
 * a dropped timer can therefore never leave a control armed.
 */
export function pressArm(state: ArmState, now: number): { next: ArmState; fire: boolean } {
  if (isArmed(state, now)) return { next: ARM_IDLE, fire: true };
  return { next: { armedAt: now }, fire: false };
}

// -- All Off (REQ-SHOWUI-025/026, design.md §6) -------------------------------

/**
 * The label states the scope, because the scope is smaller than the words
 * "all off" promise: playback the panel never started stays running
 * (spec.md §A). Hiding that would be the one failure this design cannot afford.
 */
export const ALL_OFF_LABEL = "ALL OFF (패널)";
export const ALL_OFF_SUBLABEL =
  "패널이 추적하는 재생만 정지 — 콘솔에서 직접 올린 재생은 계속됩니다";
export const ALL_OFF_ARMED_LABEL = "한 번 더 누르면 정지";

/**
 * The tiles All Off will stop: every tile the panel currently tracks as
 * running, once each, in grid order.
 *
 * Deduplicated by tile id because the grid legitimately holds one object twice
 * — pins render before the rig enumeration (M2 frozen contract), and a pinned
 * executor that the rig also lists would otherwise be stopped twice, racing the
 * server's stop lane against itself.
 */
export function allOffTargets(
  items: PanelItem[],
  running: Record<string, PanelItemState>,
): PanelItem[] {
  const seen = new Set<string>();
  const targets: PanelItem[] = [];
  for (const item of items) {
    if (running[item.id]?.running !== true) continue;
    if (seen.has(item.id)) continue;
    seen.add(item.id);
    targets.push(item);
  }
  return targets;
}

/**
 * The bounded enumeration itself: one `panel_stop` per tracked-running tile.
 *
 * There is no wide-target form to reach for — the frame builder takes one
 * object class and one positive integer, so a `Thru`/`*`/`Everything` bundle
 * cannot be expressed here at all (REQ-SHOWUI-026). That is the point: a wide
 * target would trip the risk classifier's open-target hold and raise an
 * approval card during a blackout.
 */
export function allOffFrames(
  items: PanelItem[],
  running: Record<string, PanelItemState>,
): string[] {
  return allOffTargets(items, running).map((item) =>
    buildPanelStop(item.target_kind, item.target),
  );
}

/**
 * One press of All Off, arm gate and bundle together.
 *
 * This join is the whole safety property (AC-SHOWUI-011): "one press emits zero
 * commands" is a statement about arming AND bundling as one decision, so it
 * lives in one function that can be asserted directly. Split across the two
 * halves, the wiring between them — the exact place a mistake puts a blackout
 * one press away — would be covered by nothing.
 *
 * The running set is read at FIRE time, not at arm time: the bundle must
 * describe what is playing when the operator commits, not what was playing when
 * they first reached for the control.
 */
export function allOffPress(
  arm: ArmState,
  now: number,
  items: PanelItem[],
  running: Record<string, PanelItemState>,
): { next: ArmState; frames: string[] } {
  const { next, fire } = pressArm(arm, now);
  return { next, frames: fire ? allOffFrames(items, running) : [] };
}

// -- panel gate (REQ-SHOWUI-009/010) ------------------------------------------

export type PanelBlockReason =
  | "disconnected"
  | "status_unknown"
  | "executions_blocked"
  | "health";

export type PanelGate =
  | { mode: "ready" }
  | { mode: "proposal"; message: string }
  | { mode: "blocked"; reason: PanelBlockReason; message: string };

export const LIVE_LOCK_MESSAGE = "라이브 잠금 — 제안 전용, 콘솔로 전송되지 않습니다";

/**
 * What the panel is allowed to do right now.
 *
 * Ordered strongest-truth-first. A live lock under an offline console is still
 * an offline console, and telling the operator "proposal only" there would name
 * the wrong reason for the same silence.
 *
 * A missing status blocks: the panel has not been told the console is healthy,
 * and assuming it is would be the one guess this design forbids
 * (REQ-SHOWUI-015/016 fail-closed).
 */
export function panelGate(status: StatusState | null, connected: boolean): PanelGate {
  if (!connected) {
    return { mode: "blocked", reason: "disconnected", message: "서버 연결 끊김 — 실행 불가" };
  }
  if (status === null) {
    return { mode: "blocked", reason: "status_unknown", message: "상태 미수신 — 실행 보류" };
  }
  if (status.executions_blocked) {
    return { mode: "blocked", reason: "executions_blocked", message: "실행 차단됨" };
  }
  if (status.health !== "online") {
    return { mode: "blocked", reason: "health", message: healthLabel(status.health) };
  }
  if (status.live_lock) {
    return { mode: "proposal", message: LIVE_LOCK_MESSAGE };
  }
  return { mode: "ready" };
}

// -- catalog section reporting (REQ-SHOWUI-001/002) ---------------------------

export interface SectionHint {
  level: "error" | "warn";
  text: string;
}

const SECTION_STATUS_TEXT: Record<string, string> = {
  // Kept distinct, never merged (REQ-SHOWUI-002): one asks the operator to look
  // at the showfile, the other to look at the console link.
  path_not_resolved: "이 쇼파일에 해당 경로가 없습니다",
  console_unreachable: "콘솔이 응답하지 않았습니다",
};

export function sectionHints(section: PanelSection): SectionHint[] {
  const hints: SectionHint[] = [];
  const statusText = SECTION_STATUS_TEXT[section.status];
  if (statusText !== undefined) hints.push({ level: "error", text: statusText });
  if (section.truncated) hints.push({ level: "warn", text: "목록이 잘렸습니다 — 일부 항목 누락" });
  if (section.drilldown_capped) {
    hints.push({ level: "warn", text: "조회 예산 초과 — 일부 실행기가 나열되지 않았습니다" });
  }
  if (section.contents_unavailable) {
    // "could not open" is not "verified empty"; collapsing them would show a
    // console that failed mid-walk as a show with nothing configured.
    hints.push({ level: "warn", text: "일부 항목을 열지 못했습니다 (비어 있음과 다름)" });
  }
  return hints;
}

// -- component -----------------------------------------------------------------

function SectionReport({ sections }: { sections: PanelSection[] }) {
  const reported = sections
    .map((section) => ({ section, hints: sectionHints(section) }))
    .filter(({ hints }) => hints.length > 0);
  if (reported.length === 0) return null;

  return (
    <div className="panel-sections">
      {reported.map(({ section, hints }) => (
        <div key={section.name} className="panel-section-row">
          <span className="panel-section-name">{section.name}</span>
          {hints.map((hint) => (
            <span key={hint.text} className={`panel-section-hint level-${hint.level}`}>
              {hint.text}
            </span>
          ))}
        </div>
      ))}
    </div>
  );
}

function AllOffControl({
  items,
  running,
  targets,
  onSend,
  disabled,
}: {
  items: PanelItem[];
  running: Record<string, PanelItemState>;
  /** Pre-computed for the count label; the bundle itself is built at fire time. */
  targets: PanelItem[];
  onSend: (frames: string[]) => void;
  disabled: boolean;
}) {
  const [arm, setArm] = useState<ArmState>(ARM_IDLE);
  const armed = arm.armedAt !== null;

  // Visual disarm. Correctness does not depend on this timer — `pressArm`
  // re-checks the window on every press — so a dropped timer cannot leave the
  // control secretly armed.
  useEffect(() => {
    if (!armed) return;
    const timer = window.setTimeout(() => setArm(ARM_IDLE), ARM_TIMEOUT_MS);
    return () => window.clearTimeout(timer);
  }, [armed, arm.armedAt]);

  // Nothing tracked as running: a no-op, and rendered as one rather than
  // pretending it will do something (design.md §6 edge).
  const inert = disabled || targets.length === 0;

  // A straight projection of `allOffPress` — the arm gate and the bundle are
  // decided there, under test, and this handler only carries the result out.
  const press = () => {
    const { next, frames } = allOffPress(arm, Date.now(), items, running);
    setArm(next);
    if (frames.length > 0) onSend(frames);
  };

  return (
    <div className={`panel-alloff ${armed && !inert ? "is-armed" : ""}`}>
      <button className="panel-alloff-button" onClick={press} disabled={inert}>
        <span className="panel-alloff-label">{ALL_OFF_LABEL}</span>
        <span className="panel-alloff-count">
          {targets.length > 0 ? `${targets.length}개 정지` : "정지할 재생 없음"}
        </span>
      </button>
      <div className="panel-alloff-sub">
        {armed && !inert ? ALL_OFF_ARMED_LABEL : ALL_OFF_SUBLABEL}
      </div>
      {/* The rail doubles as the arm progress indicator (design.md §4). */}
      <div
        className={`panel-rail ${armed && !inert ? "panel-rail-arming" : ""}`}
        style={armed && !inert ? { animationDuration: `${ARM_TIMEOUT_MS}ms` } : undefined}
      />
    </div>
  );
}

export function ShowPanel({
  panel,
  status,
  connected,
  onSend,
  onSendMany,
  onRefresh,
}: {
  panel: PanelState;
  status: StatusState | null;
  connected: boolean;
  onSend: (frame: string) => void;
  onSendMany: (frames: string[]) => void;
  onRefresh: () => void;
}) {
  const gate = panelGate(status, connected);
  const tileGate: TileGate =
    gate.mode === "blocked" ? "blocked" : gate.mode === "proposal" ? "proposal" : "ready";
  const gateMessage = gate.mode === "ready" ? null : gate.message;
  const targets = allOffTargets(panel.items, panel.running);

  return (
    <aside className="show-panel">
      <div className="panel-head">
        <h2>연출 패널</h2>
        <button className="panel-refresh" onClick={onRefresh} disabled={!connected}>
          새로고침
        </button>
      </div>

      {gate.mode === "blocked" && (
        <div className="panel-block-banner">⛔ {gate.message}</div>
      )}
      {gate.mode === "proposal" && (
        <div className="panel-proposal-banner">🔒 {gate.message}</div>
      )}

      <SectionReport sections={panel.sections} />

      <div className="panel-grid">
        {panel.items.length === 0 && (
          <div className="panel-empty">
            표시할 타일이 없습니다 — 새로고침하거나 채팅에서 만든 연출을 패널에 추가하세요.
          </div>
        )}
        {panel.items.map((item) => (
          <PanelTile
            key={item.id}
            item={item}
            state={panel.running[item.id]}
            gate={tileGate}
            gateMessage={gateMessage}
            busyMessage={panel.busy?.id === item.id ? panel.busy.message : null}
            onSend={onSend}
            onUnpin={(pinned) => onSend(buildPanelUnpin(pinned.target_kind, pinned.target))}
          />
        ))}
      </div>

      <AllOffControl
        items={panel.items}
        running={panel.running}
        targets={targets}
        disabled={gate.mode !== "ready"}
        onSend={onSendMany}
      />
    </aside>
  );
}
