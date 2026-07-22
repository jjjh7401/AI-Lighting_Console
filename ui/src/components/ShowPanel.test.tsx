// Show-control panel tests (SPEC-COPILOT-SHOWUI-001 M4 — AC-SHOWUI-011 vitest
// half, AC-SHOWUI-008 vitest half, AC-SHOWUI-015 vitest half).
//
// Mocked-fidelity bound: no DOM/jsdom harness in this project (see
// ApprovalCard.test.tsx header). The arm→fire state machine, the All Off bundle
// composition and the panel-level gate are pure exported functions precisely so
// the safety-critical assertions below need no renderer.
import { describe, expect, it } from "vitest";

import {
  ALL_OFF_LABEL,
  ALL_OFF_SUBLABEL,
  ARM_IDLE,
  ARM_TIMEOUT_MS,
  allOffFrames,
  allOffPress,
  allOffTargets,
  isArmed,
  panelGate,
  pressArm,
  sectionHints,
} from "./ShowPanel";
import { type PanelItem, type PanelItemState, type PanelSection, type StatusState } from "../protocol";

function item(overrides: Partial<PanelItem> & Pick<PanelItem, "id" | "target">): PanelItem {
  return {
    kind: "sequence",
    target_kind: "executor",
    name: `Tile ${overrides.target}`,
    appearance: null,
    source: "auto",
    ...overrides,
  };
}

const RUNNING: PanelItemState = { running: true, cue: null };
const STOPPED: PanelItemState = { running: false, cue: null };

function status(overrides: Partial<StatusState> = {}): StatusState {
  return { health: "online", live_lock: false, executions_blocked: false, ...overrides };
}

// -- arm→fire (REQ-SHOWUI-024, design.md §5) ----------------------------------

describe("arm→fire protects the destructive fire class", () => {
  it("fires NOTHING on the first press — the press only arms", () => {
    const { next, fire } = pressArm(ARM_IDLE, 1_000);

    expect(fire).toBe(false);
    expect(isArmed(next, 1_000)).toBe(true);
  });

  it("fires on the second press and disarms itself", () => {
    const armed = pressArm(ARM_IDLE, 1_000).next;
    const { next, fire } = pressArm(armed, 1_200);

    expect(fire).toBe(true);
    expect(isArmed(next, 1_200)).toBe(false);
  });

  it("re-arms instead of firing when the second press is too late", () => {
    const armed = pressArm(ARM_IDLE, 1_000).next;
    const late = pressArm(armed, 1_000 + ARM_TIMEOUT_MS);

    expect(late.fire).toBe(false);
    expect(isArmed(late.next, 1_000 + ARM_TIMEOUT_MS)).toBe(true);
  });

  it("auto-disarms on its own once the window elapses", () => {
    const armed = pressArm(ARM_IDLE, 1_000).next;

    expect(isArmed(armed, 1_000 + ARM_TIMEOUT_MS - 1)).toBe(true);
    expect(isArmed(armed, 1_000 + ARM_TIMEOUT_MS)).toBe(false);
  });

  it("uses a window short enough to not stay armed and long enough to reach", () => {
    expect(ARM_TIMEOUT_MS).toBeGreaterThanOrEqual(2_000);
    expect(ARM_TIMEOUT_MS).toBeLessThanOrEqual(6_000);
  });

  it("takes three presses to fire twice — arming is never skipped", () => {
    let state = ARM_IDLE;
    const fired: number[] = [];
    for (const [press, now] of [[1, 0], [2, 100], [3, 200], [4, 300]] as const) {
      const result = pressArm(state, now);
      state = result.next;
      if (result.fire) fired.push(press);
    }
    expect(fired).toEqual([2, 4]);
  });
});

// -- All Off bundle (REQ-SHOWUI-025/026, AC-SHOWUI-011) -----------------------

describe("All Off is a bounded enumeration", () => {
  const items = [
    item({ id: "executor:1", target: 1 }),
    item({ id: "executor:5", target: 5 }),
    item({ id: "executor:91", target: 91 }),
    item({ id: "sequence:41", target: 41, target_kind: "sequence" }),
  ];

  it("emits exactly one stop per tracked-running tile — N commands for N tiles", () => {
    const running = {
      "executor:1": RUNNING,
      "executor:5": STOPPED,
      "executor:91": RUNNING,
      "sequence:41": RUNNING,
    };

    const frames = allOffFrames(items, running);

    expect(frames).toHaveLength(3);
    expect(frames.map((frame) => JSON.parse(frame))).toEqual([
      { v: 1, type: "panel_stop", target_kind: "executor", target: 1 },
      { v: 1, type: "panel_stop", target_kind: "executor", target: 91 },
      { v: 1, type: "panel_stop", target_kind: "sequence", target: 41 },
    ]);
  });

  it("omits nothing — every running tile is in the bundle", () => {
    const running = Object.fromEntries(items.map((tile) => [tile.id, RUNNING]));
    const targeted = allOffTargets(items, running).map((tile) => tile.id);

    expect(targeted).toEqual(items.map((tile) => tile.id));
  });

  it("duplicates nothing — a pinned tile also enumerated by the rig is stopped once", () => {
    // The grid legitimately holds the same object twice: pins render first,
    // then the rig enumeration (M2 frozen contract). Stopping it twice would
    // race the stop lane against itself.
    const pinned = item({ id: "executor:91", target: 91, source: "pin" });
    const withDuplicate = [pinned, ...items];

    const frames = allOffFrames(withDuplicate, { "executor:91": RUNNING });

    expect(frames).toHaveLength(1);
  });

  it("uses no wide target anywhere in the bundle (REQ-SHOWUI-026)", () => {
    const running = Object.fromEntries(items.map((tile) => [tile.id, RUNNING]));
    const wire = allOffFrames(items, running).join("\n");

    for (const forbidden of ["Thru", "thru", "*", "Everything", "everything"]) {
      expect(wire).not.toContain(forbidden);
    }
  });

  it("carries only a closed shape — one type, one class, one positive integer", () => {
    const running = Object.fromEntries(items.map((tile) => [tile.id, RUNNING]));

    for (const frame of allOffFrames(items, running)) {
      const parsed = JSON.parse(frame);
      expect(Object.keys(parsed).sort()).toEqual(["target", "target_kind", "type", "v"]);
      expect(parsed.type).toBe("panel_stop");
      expect(["executor", "sequence"]).toContain(parsed.target_kind);
      expect(Number.isInteger(parsed.target)).toBe(true);
      expect(parsed.target).toBeGreaterThan(0);
    }
  });

  it("is a no-op when nothing is tracked as running", () => {
    expect(allOffFrames(items, {})).toEqual([]);
    expect(allOffTargets(items, { "executor:1": STOPPED })).toEqual([]);
  });

  it("ignores running records for tiles the grid no longer holds", () => {
    // A stale record must not resurrect a command for a tile that is gone.
    expect(allOffFrames([], { "executor:9999": RUNNING })).toEqual([]);
  });

  it("labels its own scope honestly (design.md §6, spec.md §A)", () => {
    expect(ALL_OFF_LABEL).toContain("패널");
    expect(ALL_OFF_SUBLABEL).toContain("패널");
    // The limitation is stated, not implied: playback the panel does not track
    // keeps running, and the operator is told so before pressing.
    expect(ALL_OFF_SUBLABEL.length).toBeGreaterThan(10);
  });
});

// -- arm→fire ∘ bundle, as one decision (AC-SHOWUI-011) -----------------------
//
// The two halves above are correct in isolation; what AC-SHOWUI-011 actually
// asserts is their COMPOSITION — "one press, zero commands". Testing them
// separately would leave the join between them (the place a mis-wire would put
// a blackout one press away) covered by nothing.

describe("a press of All Off emits commands only on the second one", () => {
  const items = [
    item({ id: "executor:1", target: 1 }),
    item({ id: "executor:5", target: 5 }),
    item({ id: "executor:91", target: 91 }),
  ];
  const running = Object.fromEntries(items.map((tile) => [tile.id, RUNNING]));

  it("emits ZERO commands after exactly one press, with tiles running", () => {
    const { next, frames } = allOffPress(ARM_IDLE, 1_000, items, running);

    expect(frames).toEqual([]);
    expect(isArmed(next, 1_000)).toBe(true);
  });

  it("emits one stop per running tile on the second press", () => {
    const armed = allOffPress(ARM_IDLE, 1_000, items, running).next;
    const { next, frames } = allOffPress(armed, 1_200, items, running);

    expect(frames).toHaveLength(items.length);
    expect(frames.map((frame) => JSON.parse(frame).target)).toEqual([1, 5, 91]);
    expect(isArmed(next, 1_200)).toBe(false);
  });

  it("emits nothing again on a third press — firing re-arms from scratch", () => {
    let state = ARM_IDLE;
    const emitted: number[] = [];
    for (const now of [0, 100, 200]) {
      const result = allOffPress(state, now, items, running);
      state = result.next;
      emitted.push(result.frames.length);
    }
    expect(emitted).toEqual([0, 3, 0]);
  });

  it("emits nothing when the arm window has already lapsed", () => {
    const armed = allOffPress(ARM_IDLE, 1_000, items, running).next;
    const late = allOffPress(armed, 1_000 + ARM_TIMEOUT_MS, items, running);

    expect(late.frames).toEqual([]);
    expect(isArmed(late.next, 1_000 + ARM_TIMEOUT_MS)).toBe(true);
  });

  it("still emits nothing on the second press when nothing is running", () => {
    const armed = allOffPress(ARM_IDLE, 1_000, items, {}).next;
    expect(allOffPress(armed, 1_200, items, {}).frames).toEqual([]);
  });

  it("reads the running set at FIRE time, not at arm time", () => {
    // A tile that stopped between the two presses must not be stopped again,
    // and one that started must not be left playing after an All Off.
    const armed = allOffPress(ARM_IDLE, 1_000, items, { "executor:1": RUNNING }).next;
    const { frames } = allOffPress(armed, 1_200, items, { "executor:91": RUNNING });

    expect(frames.map((frame) => JSON.parse(frame).target)).toEqual([91]);
  });

  it("carries no wide target on either press (REQ-SHOWUI-026)", () => {
    const armed = allOffPress(ARM_IDLE, 1_000, items, running).next;
    const wire = allOffPress(armed, 1_200, items, running).frames.join("\n");

    for (const forbidden of ["Thru", "thru", "*", "Everything", "everything"]) {
      expect(wire).not.toContain(forbidden);
    }
  });
});

// -- panel gate (REQ-SHOWUI-009/010, AC-SHOWUI-008 / AC-SHOWUI-015) -----------

describe("panel-level gate", () => {
  it("is ready on a healthy, unlocked, connected console", () => {
    expect(panelGate(status(), true)).toEqual({ mode: "ready" });
  });

  it("blocks the whole panel when health is not online (AC-SHOWUI-015)", () => {
    const gate = panelGate(status({ health: "console_offline" }), true);

    expect(gate.mode).toBe("blocked");
    expect(gate.mode === "blocked" && gate.reason).toBe("health");
    expect(gate.mode === "blocked" && gate.message).toContain("콘솔");
  });

  it("blocks the whole panel when executions are blocked (AC-SHOWUI-015)", () => {
    const gate = panelGate(status({ executions_blocked: true }), true);

    expect(gate.mode).toBe("blocked");
    expect(gate.mode === "blocked" && gate.reason).toBe("executions_blocked");
  });

  it("blocks on a degraded responder too — not only on a fully offline console", () => {
    const gate = panelGate(status({ health: "responder_degraded" }), true);
    expect(gate.mode).toBe("blocked");
  });

  it("degrades to proposal-only under the live lock (AC-SHOWUI-008)", () => {
    const gate = panelGate(status({ live_lock: true }), true);

    expect(gate.mode).toBe("proposal");
    expect(gate.mode === "proposal" && gate.message).toContain("제안");
  });

  it("blocks rather than proposes when the console is also down — the stronger truth wins", () => {
    const gate = panelGate(status({ live_lock: true, health: "console_offline" }), true);
    expect(gate.mode).toBe("blocked");
  });

  it("blocks while disconnected — a dead socket cannot fire anything", () => {
    const gate = panelGate(status(), false);

    expect(gate.mode).toBe("blocked");
    expect(gate.mode === "blocked" && gate.reason).toBe("disconnected");
  });

  it("blocks before any status has arrived — fail closed, never assume online", () => {
    const gate = panelGate(null, true);

    expect(gate.mode).toBe("blocked");
    expect(gate.mode === "blocked" && gate.reason).toBe("status_unknown");
  });
});

// -- catalog section reporting (REQ-SHOWUI-001/002) ---------------------------

describe("section hints", () => {
  function section(overrides: Partial<PanelSection> = {}): PanelSection {
    return { name: "sequences", status: "ok", ...overrides };
  }

  it("says nothing about a complete section", () => {
    expect(sectionHints(section())).toEqual([]);
  });

  it("keeps the two failure causes distinct — never merged (REQ-SHOWUI-002)", () => {
    const unresolved = sectionHints(section({ status: "path_not_resolved" }));
    const unreachable = sectionHints(section({ status: "console_unreachable" }));

    expect(unresolved).toHaveLength(1);
    expect(unreachable).toHaveLength(1);
    expect(unresolved[0].text).not.toBe(unreachable[0].text);
    expect(unresolved[0].level).toBe("error");
    expect(unreachable[0].level).toBe("error");
  });

  it("surfaces every incompleteness flag rather than dropping it", () => {
    const hints = sectionHints(
      section({ truncated: true, drilldown_capped: true, contents_unavailable: true }),
    );

    expect(hints).toHaveLength(3);
    expect(hints.every((hint) => hint.level === "warn")).toBe(true);
    expect(new Set(hints.map((hint) => hint.text)).size).toBe(3);
  });

  it("reports a failed section's flags alongside its cause", () => {
    const hints = sectionHints(section({ status: "console_unreachable", truncated: true }));

    expect(hints.map((hint) => hint.level)).toEqual(["error", "warn"]);
  });
});
