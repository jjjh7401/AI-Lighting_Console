// Live Rail tile — the panel's signature anatomy (SPEC-COPILOT-SHOWUI-001 M4,
// design.md §4, REQ-SHOWUI-018/020).
//
// One structure serves every tile kind: an emissive appearance chip on the left
// edge, the console's own name plus a type badge, and a bottom rail that is the
// tile's state voice — dark when stopped, live-amber when running. Identity,
// state and safety ride one element, and that element appears nowhere else in
// the app.
//
// Every decision below lives in a pure function rather than in JSX. This project
// has no DOM test harness (see useCopilotSocket.test.ts header), so anything
// branching inside a component would be untestable; extracting the branches
// leaves the JSX as a straight projection of `tileView`.
import { useEffect, useRef, useState } from "react";

import { createDecisionGuard } from "./ApprovalCard";
import {
  buildPanelExecute,
  buildPanelStop,
  type PanelItem,
  type PanelItemKind,
  type PanelItemState,
} from "../protocol";

/**
 * The console's verbs, not a media player's (REQ-SHOWUI-020, design.md §7).
 *
 * An operator who reads `Go+` knows exactly which console action fires; `▶`
 * only means "something starts". Icons may decorate these labels, never replace
 * them.
 */
export const VERB_GO = "Go+";
export const VERB_OFF = "Off";

/**
 * State always carries text as well as colour (REQ-SHOWUI-018). Amber alone
 * fails a colour-blind operator and a washed-out FOH monitor equally.
 */
export const BADGE_RUN = "RUN";
export const BADGE_OFF = "OFF";

export const TYPE_BADGES: Record<PanelItemKind, string> = {
  look: "LOOK",
  effect: "FX",
  sequence: "SEQ",
  // SPEC-COPILOT-DASHUI-001 M2 — macro joined the panel_execute/panel_stop
  // target_kind set (server/web/panel.py PANEL_CATALOG_SECTIONS); the show
  // panel's own type badge follows the same closed-set invariant as the
  // dash catalog: every PanelItemKind the console actually fires gets one.
  macro: "MACRO",
};

/** How the panel as a whole is currently permitted to act. */
export type TileGate = "ready" | "proposal" | "blocked";

export type TilePressVerb = "go" | "off";

export interface TileView {
  mode: "running" | "idle";
  badge: string;
  typeBadge: string;
  railClass: string;
  tileClass: string;
  /** The running cue, as the console's own string ("1.5" is a cue number). */
  cue: string | null;
  goDisabled: boolean;
  offDisabled: boolean;
  /** Persistent status line ON the tile — never a toast (design.md §7). */
  note: string | null;
}

export interface TileViewArgs {
  item: PanelItem;
  state: PanelItemState | undefined;
  gate: TileGate;
  gateMessage: string | null;
  busyMessage: string | null;
  /** A fire press is latched until its terminal event lands (REQ-SHOWUI-011). */
  pending: boolean;
}

export function tileView({
  item,
  state,
  gate,
  gateMessage,
  busyMessage,
  pending,
}: TileViewArgs): TileView {
  // Running is an OBSERVATION, not a permission: a blocked panel still shows a
  // tile that is playing, because the console did not stop when the app lost
  // its ability to talk to it. Only a disconnect erases running state, and that
  // erasure happens upstream in `clearOnDisconnect`.
  const running = state?.running === true;

  // The one place live-amber is spent (design.md §3). A static look holds
  // solid; anything with motion in it sweeps, which is what separates a look
  // from a phaser at a glance without reading either label.
  const railClass = running
    ? item.kind === "look"
      ? "panel-rail panel-rail-live"
      : "panel-rail panel-rail-live panel-rail-sweep"
    : "panel-rail";

  const tileClass = [
    "panel-tile",
    running ? "is-running" : "",
    gate === "blocked" ? "is-blocked" : "",
    gate === "proposal" ? "is-proposal" : "",
    gate === "ready" && busyMessage !== null ? "is-busy" : "",
  ]
    .filter(Boolean)
    .join(" ");

  const blocked = gate !== "ready";

  return {
    mode: running ? "running" : "idle",
    badge: running ? BADGE_RUN : BADGE_OFF,
    typeBadge: TYPE_BADGES[item.kind],
    railClass,
    tileClass,
    cue: running ? (state?.cue ?? null) : null,
    // Fire is the gated class: a press latches the tile so a burst of taps
    // converges to one decision.
    goDisabled: blocked || pending,
    // Stop is not. It is exempt from the fire latch AND from the server's
    // busy guard (REQ-SHOWUI-012) — a panel whose Off can be busy is a panel
    // that cannot be trusted. Only a gate that sends nothing at all disables it.
    offDisabled: blocked,
    // A block outranks a busy note: it is the stronger and more recent truth.
    note: blocked ? gateMessage : busyMessage,
  };
}

/** The single frame one press emits. Zero-step: press → frame, nothing between. */
export function tilePressFrame(item: PanelItem, verb: TilePressVerb): string {
  return verb === "go"
    ? buildPanelExecute(item.target_kind, item.target)
    : buildPanelStop(item.target_kind, item.target);
}

/**
 * Safety release for the fire latch.
 *
 * Every panel command produces exactly one terminal event (PROTOCOL.md § Panel
 * command outcomes), so the latch normally clears the moment the server
 * answers. This timer covers the case where that answer never arrives: a tile
 * stuck latched forever is worse than one that can be pressed twice.
 */
export const PRESS_LATCH_TIMEOUT_MS = 4000;

export function PanelTile({
  item,
  state,
  gate,
  gateMessage,
  busyMessage,
  onSend,
  onUnpin,
}: {
  item: PanelItem;
  state: PanelItemState | undefined;
  gate: TileGate;
  gateMessage: string | null;
  busyMessage: string | null;
  onSend: (frame: string) => void;
  onUnpin: (item: PanelItem) => void;
}) {
  const [pending, setPending] = useState(false);
  // useRef, not useState, for the guard itself: two clicks can land before
  // React re-renders, and only a ref is synchronously consistent across them
  // (the same reason ApprovalCard holds its guard this way).
  const guardRef = useRef<((requestId: string, approved: boolean) => boolean) | null>(null);

  const release = () => {
    guardRef.current = null;
    setPending(false);
  };

  // A terminal event for this tile arrives as a fresh `state` record or a fresh
  // busy message; either one ends the press cycle.
  useEffect(release, [state, busyMessage]);

  useEffect(() => {
    if (!pending) return;
    const timer = window.setTimeout(release, PRESS_LATCH_TIMEOUT_MS);
    return () => window.clearTimeout(timer);
  }, [pending]);

  const view = tileView({ item, state, gate, gateMessage, busyMessage, pending });

  const fire = () => {
    // The ApprovalCard guard, reused verbatim (spec.md §E): first call wins,
    // repeats are no-ops. Its boolean argument is unused here — a fire press
    // carries one decision, not a yes/no one.
    if (guardRef.current === null) {
      guardRef.current = createDecisionGuard(() => onSend(tilePressFrame(item, "go")));
    }
    if (guardRef.current(item.id, true)) setPending(true);
  };

  // Deliberately unguarded: see `offDisabled` above. A repeated Off is
  // harmless (stopping a stopped executor is a no-op on the console); an Off
  // that refuses to fire is not.
  const stop = () => onSend(tilePressFrame(item, "off"));

  return (
    <div className={view.tileClass}>
      <span
        className="panel-chip"
        style={item.appearance ? { background: item.appearance } : undefined}
        aria-hidden="true"
      />
      <div className="panel-tile-body">
        <div className="panel-tile-head">
          <span className="panel-tile-name">{item.name}</span>
          <span className="panel-type-badge">{view.typeBadge}</span>
        </div>
        <div className="panel-tile-meta">
          <span className={`panel-state-badge ${view.mode === "running" ? "is-run" : "is-off"}`}>
            {view.badge}
          </span>
          <span className="panel-tile-address">
            {item.target_kind === "executor" ? "Exec" : "Seq"} {item.target}
          </span>
          {view.cue !== null && <span className="panel-tile-cue">Cue {view.cue}</span>}
          {item.source === "pin" && <span className="panel-pin-mark">핀</span>}
        </div>
        {view.note !== null && <div className="panel-tile-note">{view.note}</div>}
        <div className="panel-tile-actions">
          <button className="panel-go" onClick={fire} disabled={view.goDisabled}>
            {VERB_GO}
          </button>
          <button className="panel-off" onClick={stop} disabled={view.offDisabled}>
            {VERB_OFF}
          </button>
          {item.source === "pin" && (
            <button className="panel-unpin" onClick={() => onUnpin(item)}>
              핀 해제
            </button>
          )}
        </div>
      </div>
      <div className={view.railClass} />
    </div>
  );
}
