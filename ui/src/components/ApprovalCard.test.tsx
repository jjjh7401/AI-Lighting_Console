// ApprovalCard decision-guard tests (M6c-8 backlog item 2 —
// server/rulebook comprehensive-review backlog ref ApprovalCard.tsx:35, no
// button debounce). The 승인/거부 buttons previously called onDecision
// directly with no guard, so a double-click (or any rapid repeated click)
// could submit a decision for the same request_id more than once.
//
// Mocked-fidelity bound: this project has no DOM/jsdom test harness (see
// useCopilotSocket.test.ts header — "Pure functions only... unit-testable
// without a DOM"). The debounce guard is implemented as the pure, DOM-free
// `createDecisionGuard` factory the component wires into its onClick
// handlers via useRef; this test exercises that guard directly rather than
// rendering the component and simulating real click events.
import { describe, expect, it, vi } from "vitest";

import { createDecisionGuard } from "./ApprovalCard";

describe("createDecisionGuard", () => {
  it("submits the first decision and reports success", () => {
    const onDecision = vi.fn();
    const guard = createDecisionGuard(onDecision);

    const submitted = guard("req-1", true);

    expect(submitted).toBe(true);
    expect(onDecision).toHaveBeenCalledTimes(1);
    expect(onDecision).toHaveBeenCalledWith("req-1", true);
  });

  it("ignores a second call for the same approval — quick double-click debounce", () => {
    const onDecision = vi.fn();
    const guard = createDecisionGuard(onDecision);

    guard("req-1", true);
    const secondSubmitted = guard("req-1", true);

    expect(secondSubmitted).toBe(false);
    expect(onDecision).toHaveBeenCalledTimes(1);
  });

  it("ignores a later opposite decision once the first has landed — reject after approve is a no-op", () => {
    const onDecision = vi.fn();
    const guard = createDecisionGuard(onDecision);

    guard("req-1", true);
    const secondSubmitted = guard("req-1", false);

    expect(secondSubmitted).toBe(false);
    expect(onDecision).toHaveBeenCalledTimes(1);
    expect(onDecision).toHaveBeenCalledWith("req-1", true);
  });

  it("each ApprovalCard instance gets its own independent guard", () => {
    const onDecisionA = vi.fn();
    const onDecisionB = vi.fn();
    const guardA = createDecisionGuard(onDecisionA);
    const guardB = createDecisionGuard(onDecisionB);

    guardA("req-A", true);
    guardB("req-B", false);

    expect(onDecisionA).toHaveBeenCalledTimes(1);
    expect(onDecisionA).toHaveBeenCalledWith("req-A", true);
    expect(onDecisionB).toHaveBeenCalledTimes(1);
    expect(onDecisionB).toHaveBeenCalledWith("req-B", false);
  });

  it("many rapid repeated calls still submit exactly once", () => {
    const onDecision = vi.fn();
    const guard = createDecisionGuard(onDecision);

    const results = [guard("req-1", true), guard("req-1", true), guard("req-1", true)];

    expect(results).toEqual([true, false, false]);
    expect(onDecision).toHaveBeenCalledTimes(1);
  });
});
