// PoolTile — one numbered onPC-style pool cell (SPEC-COPILOT-DASHUI-001 M4,
// design.md §3 "풀 셀(슬롯)" / §7 rule 7, REQ-DASHUI-010/011/016/017).
//
// Renders ONE occupied slot: the console's REAL number as the primary
// visual element, the name, and an optional appearance-colour chip. Empty
// gap-slot rendering (design.md's "빈 슬롯" row) is a documented M4 scope
// cut — see progress.md §E.2 Gaps: `build_dash_catalog` (server/web/dash.py)
// returns only occupied objects, with no adjacent-gap metadata to
// synthesize empty cells from.
//
// press-able vs read-only (REQ-DASHUI-007/010/011/023) is a CALLER decision
// (DashBoard/PoolSection), never inferred here from data shape — DashItem
// structurally carries no target_kind (info-only shape; see protocol.ts's
// own header), so this component has nothing of its own to key a decision
// on. `pressable` is the single switch: true renders a verb button with
// press affordance; false renders a flat read-only cell with NO click
// affordance (design.md §7 rule 7 — a dead-looking button is worse than no
// button).
//
// M5 (design.md §4/§8, REQ-DASHUI-017): `running` is likewise a CALLER
// decision — this component has no `panel.running` access of its own (that
// lookup is keyed by `panelItemId(target_kind, no)`, one layer up in
// DashBoard). `running` only ever applies alongside `pressable` (a
// read-only tile has no press-driven state to reflect) and toggles the
// live-amber `.pool-tile-running` class exclusively — no other visual
// channel changes.
//
// No internal hooks by design — this project has no DOM/jsdom test harness
// (see protocol.ts's own header); PoolTile is called directly as a plain
// function in PoolTile.test.tsx.
import { type DashItem } from "../protocol";

export interface PoolTileProps {
  item: DashItem;
  /** Caller-computed: does THIS tile carry press affordance? */
  pressable: boolean;
  /** The console verb shown on a press-able tile (e.g. "Go+", "Off", "Macro"). */
  verb?: string;
  /** Caller-computed playback state (M5) — ignored when `pressable` is false. */
  running?: boolean;
  /** Fires `gate.screen()` via panel_execute/panel_stop (M5 wires the caller). */
  onPress?: (item: DashItem) => void;
}

export function PoolTile({ item, pressable, verb, running, onPress }: PoolTileProps) {
  const unresolved = !pressable && item.meta?.resolved === false;
  const runningClass = pressable && running ? " pool-tile-running" : "";
  return (
    <div className={`pool-tile ${pressable ? "pool-tile-press" : "pool-tile-info"}${runningClass}`}>
      <span className="pool-tile-no">{item.no}</span>
      <span className="pool-tile-name">{item.name || "—"}</span>
      {item.appearance ? (
        <span className="pool-tile-appearance" style={{ background: item.appearance }} />
      ) : null}
      {unresolved ? <span className="pool-tile-unresolved">정보만</span> : null}
      {pressable ? (
        <button
          type="button"
          className="pool-tile-verb"
          onClick={onPress ? () => onPress(item) : undefined}
        >
          {verb ?? "Go+"}
        </button>
      ) : null}
    </div>
  );
}
