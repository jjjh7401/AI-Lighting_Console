// Live Rail tile tests (SPEC-COPILOT-SHOWUI-001 M4 — REQ-SHOWUI-018/020,
// AC-SHOWUI-011 vitest half).
//
// Mocked-fidelity bound: this project has no DOM/jsdom harness (see
// useCopilotSocket.test.ts and ApprovalCard.test.tsx headers). Every decision a
// tile makes — which colour it wears, which badge it shows, which button is
// live, which frame a press emits — is therefore computed by pure exported
// functions that the component only renders. Those functions are what is tested
// here; the JSX around them carries no branching of its own.
import { describe, expect, it } from "vitest";

import {
  BADGE_OFF,
  BADGE_RUN,
  TYPE_BADGES,
  VERB_GO,
  VERB_OFF,
  tilePressFrame,
  tileView,
} from "./PanelTile";
import { type PanelItem, type PanelItemState } from "../protocol";

const executor: PanelItem = {
  id: "executor:191",
  kind: "sequence",
  target_kind: "executor",
  target: 191,
  name: "Summer Rock",
  appearance: "#ff3fa4",
  source: "auto",
};

const look: PanelItem = {
  id: "sequence:41",
  kind: "look",
  target_kind: "sequence",
  target: 41,
  name: "Cyan Look",
  appearance: "#00c8ff",
  source: "pin",
};

const RUNNING: PanelItemState = { running: true, cue: "1.5" };
const STOPPED: PanelItemState = { running: false, cue: null };

function view(overrides: Partial<Parameters<typeof tileView>[0]> = {}) {
  return tileView({
    item: executor,
    state: undefined,
    gate: "ready",
    gateMessage: null,
    busyMessage: null,
    pending: false,
    ...overrides,
  });
}

describe("console verbs (REQ-SHOWUI-020)", () => {
  it("labels the two actions with the console's own verbs", () => {
    expect(VERB_GO).toBe("Go+");
    expect(VERB_OFF).toBe("Off");
  });

  it("uses no media-player glyph as a verb — the console has no play button", () => {
    for (const verb of [VERB_GO, VERB_OFF]) {
      expect(verb).not.toMatch(/[▶⏸⏹■]/);
    }
  });

  it("badges each tile kind with its console type", () => {
    // SPEC-COPILOT-DASHUI-001 M2 — macro joined the closed PanelItemKind set.
    expect(TYPE_BADGES).toEqual({ look: "LOOK", effect: "FX", sequence: "SEQ", macro: "MACRO" });
  });
});

describe("live-amber is exclusive to running (REQ-SHOWUI-018, design.md §3)", () => {
  it("wears the live rail while running", () => {
    const rendered = view({ state: RUNNING });
    expect(rendered.mode).toBe("running");
    expect(rendered.railClass).toContain("panel-rail-live");
    expect(rendered.tileClass).toContain("is-running");
  });

  it("drops the live rail the moment the tile is not running", () => {
    for (const state of [undefined, STOPPED]) {
      const rendered = view({ state });
      expect(rendered.mode).toBe("idle");
      expect(rendered.railClass).not.toContain("live");
      expect(rendered.tileClass).not.toContain("is-running");
    }
  });

  it("never spends live-amber on busy, blocked or proposal — those are not running", () => {
    const busy = view({ busyMessage: "다른 실행이 진행 중입니다" });
    const blocked = view({ gate: "blocked", gateMessage: "콘솔 오프라인" });
    const proposal = view({ gate: "proposal", gateMessage: "라이브 잠금" });

    for (const rendered of [busy, blocked, proposal]) {
      expect(rendered.railClass).not.toContain("live");
      expect(rendered.tileClass).not.toContain("is-running");
    }
  });

  it("sweeps for playback and holds solid for a static look (design.md §4)", () => {
    expect(view({ item: executor, state: RUNNING }).railClass).toContain("panel-rail-sweep");
    expect(view({ item: look, state: RUNNING }).railClass).not.toContain("panel-rail-sweep");
    // Both are still live — only the motion differs.
    expect(view({ item: look, state: RUNNING }).railClass).toContain("panel-rail-live");
  });
});

describe("status is never colour alone (REQ-SHOWUI-018)", () => {
  it("carries a text badge in both states", () => {
    expect(view({ state: RUNNING }).badge).toBe(BADGE_RUN);
    expect(view({ state: STOPPED }).badge).toBe(BADGE_OFF);
    expect(BADGE_RUN).toBe("RUN");
    expect(BADGE_OFF).toBe("OFF");
  });

  it("shows the running cue as the string the console uses", () => {
    expect(view({ state: RUNNING }).cue).toBe("1.5");
    // A stopped tile has no cue to show, even if one lingers in the record.
    expect(view({ state: { running: false, cue: "1.5" } }).cue).toBeNull();
  });
});

describe("stop class and fire class are disjoint (REQ-SHOWUI-012/024, design.md §5)", () => {
  it("keeps Off live while a fire press is latched — stop is never gated by busy", () => {
    const rendered = view({ pending: true });
    expect(rendered.goDisabled).toBe(true);
    expect(rendered.offDisabled).toBe(false);
  });

  it("keeps Off live while the server is refusing new executions as busy", () => {
    const rendered = view({ busyMessage: "다른 실행이 진행 중입니다" });
    expect(rendered.offDisabled).toBe(false);
  });

  it("emits exactly one frame per press, for either verb — zero-step", () => {
    const go = tilePressFrame(executor, "go");
    const off = tilePressFrame(executor, "off");

    expect(JSON.parse(go)).toEqual({
      v: 1,
      type: "panel_execute",
      target_kind: "executor",
      target: 191,
    });
    expect(JSON.parse(off)).toEqual({
      v: 1,
      type: "panel_stop",
      target_kind: "executor",
      target: 191,
    });
  });

  it("addresses a sequence tile as a sequence, not as an executor", () => {
    expect(JSON.parse(tilePressFrame(look, "off"))).toEqual({
      v: 1,
      type: "panel_stop",
      target_kind: "sequence",
      target: 41,
    });
  });
});

describe("blocked and proposal renders (REQ-SHOWUI-009/010)", () => {
  it("disables both verbs and names the reason when the panel is blocked", () => {
    const rendered = view({ gate: "blocked", gateMessage: "콘솔 오프라인 — 신규 실행 차단" });

    expect(rendered.goDisabled).toBe(true);
    expect(rendered.offDisabled).toBe(true);
    expect(rendered.note).toBe("콘솔 오프라인 — 신규 실행 차단");
    expect(rendered.tileClass).toContain("is-blocked");
  });

  it("degrades to proposal-only under the live lock", () => {
    const rendered = view({ gate: "proposal", gateMessage: "라이브 잠금 — 제안 전용" });

    expect(rendered.goDisabled).toBe(true);
    expect(rendered.offDisabled).toBe(true);
    expect(rendered.tileClass).toContain("is-proposal");
    expect(rendered.note).toBe("라이브 잠금 — 제안 전용");
  });

  it("keeps a busy refusal on the tile as persistent state, not a toast", () => {
    const rendered = view({ busyMessage: "다른 실행이 진행 중입니다" });

    expect(rendered.note).toBe("다른 실행이 진행 중입니다");
    expect(rendered.tileClass).toContain("is-busy");
  });

  it("lets a block outrank a stale busy note — the stronger truth is shown", () => {
    const rendered = view({
      gate: "blocked",
      gateMessage: "콘솔 오프라인",
      busyMessage: "다른 실행이 진행 중입니다",
    });
    expect(rendered.note).toBe("콘솔 오프라인");
  });

  it("shows a running tile as running even while the panel is blocked — observation, not permission", () => {
    // The tile stopped being pressable; it did not stop playing.
    const rendered = view({ state: RUNNING, gate: "blocked", gateMessage: "콘솔 오프라인" });
    expect(rendered.mode).toBe("running");
    expect(rendered.badge).toBe(BADGE_RUN);
  });
});
