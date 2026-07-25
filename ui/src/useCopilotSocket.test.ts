// useCopilotSocket reducer tests (M6c-4 finding 3 — stale approval/review
// cards must clear on disconnect, since the server fail-safe-denies every
// pending request for that session on its own disconnect).
//
// Mocked-fidelity bound: this project has no DOM/jsdom test harness (see
// protocol.ts's own header — "Pure functions only... so the module is
// unit-testable without a DOM"). The exported `reducer` is the same pure
// state transition `socket.onclose` dispatches via
// `dispatch({ kind: "disconnected" })`; this exercises that transition
// directly rather than instantiating a real WebSocket + React render.
import { afterEach, describe, expect, it } from "vitest";

import {
  buildPanelCatalogRequest,
  buildStatusRequest,
  initialState,
  type PanelItem,
  type ReviewRequestView,
  type UiState,
} from "./protocol";
import {
  BASE_SUBPROTOCOL,
  TOKEN_SUBPROTOCOL_PREFIX,
  connectProtocols,
  connectResyncFrames,
  dashResyncFrame,
  launchToken,
  reducer,
  resyncFrames,
} from "./useCopilotSocket";

const REVIEW: ReviewRequestView = {
  request_id: "review-1",
  plugin_name: "Cleaner",
  source_preview: 'Cmd("Delete Sequence 5")',
  source_length: 24,
  source_truncated: false,
  compile_ok: true,
  scan: { destructive: false, findings: [], dynamic_calls: [], caveat: "" },
};

function stateWithPending(): UiState {
  return {
    ...initialState,
    pendingApprovals: [{ request_id: "approval-1", items: [] }],
    pendingReviews: [REVIEW],
  };
}

describe("reducer — disconnect clears stale pending cards", () => {
  it("clears pendingApprovals and pendingReviews on disconnect", () => {
    const next = reducer(stateWithPending(), { kind: "disconnected" });
    expect(next.pendingApprovals).toEqual([]);
    expect(next.pendingReviews).toEqual([]);
  });

  it("leaves chat entries and status untouched on disconnect", () => {
    const state: UiState = {
      ...stateWithPending(),
      entries: [{ kind: "notice", message: "백업 실패" }],
      status: { health: "online", live_lock: false, executions_blocked: false },
    };
    const next = reducer(state, { kind: "disconnected" });
    expect(next.entries).toEqual(state.entries);
    expect(next.status).toEqual(state.status);
  });

  it("is a no-op when nothing is pending", () => {
    const next = reducer(initialState, { kind: "disconnected" });
    expect(next).toEqual(initialState);
  });
});

// M5 (REQ-SHOWUI-015/016, AC-SHOWUI-010) — fail-closed on a dropped socket.
//
// Running state is an OBSERVATION of the console, and the observation ends when
// the socket does. Rendering a tile as RUN across a connection gap tells the
// operator something the app cannot currently know, and that is the render that
// gets Off pressed on playback that already stopped — or leaves one running
// that did not. The tile LIST survives, because it is server state rather than
// an observation, so the grid stays put (REQ-SHOWUI-017) while inert.
const TILE: PanelItem = {
  id: "executor:41",
  kind: "executor",
  target_kind: "executor",
  target: 41,
  name: "Summer Rock",
  appearance: null,
  source: "rig",
};

function stateWithRunningTile(): UiState {
  return {
    ...initialState,
    panel: {
      items: [TILE],
      sections: [],
      running: { "executor:41": { running: true, cue: "3" } },
      busy: { id: "executor:41", message: "실행 중 — 잠시 후 다시" },
    },
  };
}

describe("reducer — disconnect erases the panel's volatile running state", () => {
  it("clears every tile's running record on disconnect", () => {
    const next = reducer(stateWithRunningTile(), { kind: "disconnected" });
    expect(next.panel.running).toEqual({});
  });

  it("clears the busy refusal too — it describes a server that is now gone", () => {
    const next = reducer(stateWithRunningTile(), { kind: "disconnected" });
    expect(next.panel.busy).toBeNull();
  });

  it("keeps the tile list so the grid does not reflow on reconnect", () => {
    // The list is server state, not an observation; dropping it would empty the
    // grid and re-lay it out under the operator's finger when it came back.
    const next = reducer(stateWithRunningTile(), { kind: "disconnected" });
    expect(next.panel.items).toEqual([TILE]);
  });

  it("never reports a tile as still running after the socket drops", () => {
    // The AC proposition stated directly: no tile survives a disconnect in a
    // RUN render, whatever the record shape.
    const next = reducer(stateWithRunningTile(), { kind: "disconnected" });
    const stillRunning = Object.values(next.panel.running).filter((tile) => tile.running);
    expect(stillRunning).toEqual([]);
  });

  it("clears pending cards AND panel state together (§D edge case 8)", () => {
    // A connection that drops mid-approval hits both halves at once: the server
    // fail-safe-denies the pending request, and the panel loses its observer.
    // One action must clear both — half-cleared state is the failure mode.
    const state: UiState = { ...stateWithPending(), panel: stateWithRunningTile().panel };
    const next = reducer(state, { kind: "disconnected" });
    expect(next.pendingApprovals).toEqual([]);
    expect(next.pendingReviews).toEqual([]);
    expect(next.panel.running).toEqual({});
    expect(next.panel.busy).toBeNull();
  });
});

// M5 (REQ-SHOWUI-015 second half / REQ-SHOWUI-016) — reconnect resynchronises.
//
// Having erased the running state, the panel must rebuild it from the server
// rather than from anything it remembers. These frames are what a fresh socket
// asks for; nothing reconstructs state client-side, and nothing an unconfirmed
// command left behind is re-sent (REQ-MVP-032 inherited unchanged).
describe("reconnect resynchronisation", () => {
  it("asks the server for the catalog and the status", () => {
    expect(resyncFrames()).toEqual([buildPanelCatalogRequest(), buildStatusRequest()]);
  });

  it("re-requests rather than replaying — no execute or stop rides along", () => {
    // The one assertion that matters for REQ-SHOWUI-016: a reconnect must never
    // become an auto-resend of a command nobody confirmed.
    const joined = resyncFrames().join("");
    expect(joined).not.toMatch(/panel_execute|panel_stop|"type":"chat"/);
  });

  it("sends only read-side requests, both at protocol version 1", () => {
    const types = resyncFrames().map((frame) => JSON.parse(frame));
    expect(types.map((frame) => frame.type)).toEqual([
      "panel_catalog_request",
      "status_request",
    ]);
    expect(types.every((frame) => frame.v === 1)).toBe(true);
  });
});

// M7.1 (REQ-DEPLOY-002a / AC-DEPLOY-025+029) — the token-consumption seam.
// The token arrives from the injected runtime context (Stage-2: Tauri IPC
// init-script, wired at M7.4); Stage-1 browser mode has no such context, so the
// hook must connect exactly as before. Pure functions, same no-DOM bound as the
// reducer tests above.
type TokenGlobal = { __COPILOT_LAUNCH_TOKEN__?: string };

afterEach(() => {
  delete (globalThis as TokenGlobal).__COPILOT_LAUNCH_TOKEN__;
});

describe("launch-token seam", () => {
  it("reads the token from the injected runtime context", () => {
    (globalThis as TokenGlobal).__COPILOT_LAUNCH_TOKEN__ = "tok-123";
    expect(launchToken()).toBe("tok-123");
  });

  it("returns undefined in Stage-1 browser mode (no injected context)", () => {
    expect(launchToken()).toBeUndefined();
  });

  it("presents the token as a subprotocol alongside the base protocol", () => {
    expect(connectProtocols("tok-123")).toEqual([
      BASE_SUBPROTOCOL,
      `${TOKEN_SUBPROTOCOL_PREFIX}tok-123`,
    ]);
  });

  it("offers no subprotocols when no token is available", () => {
    // Stage-1 regression guard: the browser path must stay a bare connect.
    expect(connectProtocols(undefined)).toBeUndefined();
    expect(connectProtocols("")).toBeUndefined();
  });
});

// AC-DASHUI-017 — every (re)connect re-requests panel catalog + dash catalog
// + status, so a reconnect rebuilds from scratch rather than trusting
// pre-disconnect state. Pure function, same no-DOM bound as above; the live
// `socket.onopen` handler calls this exact function (see useCopilotSocket.ts).
describe("connectResyncFrames — reconnect resync dispatch (AC-DASHUI-017)", () => {
  it("returns exactly three frames: panel_catalog_request, dash_catalog_request, status_request", () => {
    const frames = connectResyncFrames().map((frame) => JSON.parse(frame).type);
    expect(frames).toEqual(["panel_catalog_request", "dash_catalog_request", "status_request"]);
  });

  it("every frame is protocol v1 and payload-free besides v/type", () => {
    for (const frame of connectResyncFrames()) {
      const parsed = JSON.parse(frame);
      expect(parsed.v).toBe(1);
      expect(Object.keys(parsed).sort()).toEqual(["type", "v"]);
    }
  });

  it("is deterministic and side-effect-free — calling it twice sends nothing on its own", () => {
    expect(connectResyncFrames()).toEqual(connectResyncFrames());
  });
});

// M6-UX v2 — a chat-side mutation must resync the console pane without a
// manual refresh (user finding: "Delete Group 20" executed but Group 20
// stayed on the dashboard until 새로고침 was pressed).
describe("dashResyncFrame", () => {
  it("returns a dash_catalog_request for a chat_response carrying an executed command", () => {
    const frame = dashResyncFrame(
      JSON.stringify({
        v: 1,
        type: "chat_response",
        status: "done",
        summary: "",
        text: "",
        commands: [{ command: "Delete Group 20", status: "executed_ok", label: "", detail: "" }],
      }),
    );
    expect(frame).toContain("dash_catalog_request");
  });

  it("returns null when nothing was actually executed (refresh-on-demand stays the rule)", () => {
    const noCommands = JSON.stringify({
      v: 1,
      type: "chat_response",
      status: "done",
      summary: "",
      text: "",
      commands: [],
    });
    expect(dashResyncFrame(noCommands)).toBeNull();
    const blockedOnly = JSON.stringify({
      v: 1,
      type: "chat_response",
      status: "blocked",
      summary: "",
      text: "",
      commands: [{ command: "Delete Group 20", status: "blocked", label: "", detail: "" }],
    });
    expect(dashResyncFrame(blockedOnly)).toBeNull();
    expect(dashResyncFrame(JSON.stringify({ v: 1, type: "status" }))).toBeNull();
    expect(dashResyncFrame("not json")).toBeNull();
  });
});
