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
import { describe, expect, it } from "vitest";

import { initialState, type ReviewRequestView, type UiState } from "./protocol";
import { reducer } from "./useCopilotSocket";

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
