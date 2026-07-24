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
// button). live-amber/RUN styling is deliberately NOT wired here yet: dash
// sections carry no running/tracked state (that lives in `panel.running`,
// keyed by `panelItemId`, unreachable from a DashItem) — wiring it is an M5
// concern (see progress.md §E.2 Gaps).
//
// No internal hooks by design — this project has no DOM/jsdom test harness
// (see protocol.ts's own header); PoolTile is called directly as a plain
// function in PoolTile.test.tsx.
import { type DashItem } from "../protocol";

export interface PoolTileProps {
  item: DashItem;
  /** Caller-computed: does THIS tile carry press affordance? */
  pressable: boolean;
  /** The console verb shown on a press-able tile (e.g. "Go+", "Macro"). */
  verb?: string;
  /** M5 wires the actual gate.screen() dispatch; M4 renders the affordance only. */
  onPress?: (item: DashItem) => void;
}

export function PoolTile({ item, pressable, verb, onPress }: PoolTileProps) {
  const unresolved = !pressable && item.meta?.resolved === false;
  return (
    <div className={`pool-tile ${pressable ? "pool-tile-press" : "pool-tile-info"}`}>
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
