import { describe, expect, it } from "vitest";

import {
  addUserMessage,
  buildApprovalDecision,
  buildChat,
  buildLock,
  buildReviewDecision,
  healthLabel,
  initialState,
  parseServerEvent,
  reduceServerEvent,
  type ServerEvent,
} from "./protocol";

function event(fields: Record<string, unknown>): ServerEvent {
  const parsed = parseServerEvent(JSON.stringify({ v: 1, ...fields }));
  if (parsed === null) throw new Error("fixture did not parse");
  return parsed;
}

describe("parseServerEvent", () => {
  it("parses a known event", () => {
    const parsed = parseServerEvent(
      JSON.stringify({ v: 1, type: "status", health: "online", live_lock: false, executions_blocked: false }),
    );
    expect(parsed?.type).toBe("status");
  });

  it("rejects non-JSON, wrong version, and unknown types", () => {
    expect(parseServerEvent("not json")).toBeNull();
    expect(parseServerEvent(JSON.stringify({ v: 2, type: "status" }))).toBeNull();
    expect(parseServerEvent(JSON.stringify({ v: 1, type: "mystery" }))).toBeNull();
    expect(parseServerEvent(JSON.stringify(["array"]))).toBeNull();
  });
});

describe("builders", () => {
  it("builds versioned client frames", () => {
    expect(JSON.parse(buildChat("보컬 그룹 만들어줘"))).toEqual({
      v: 1,
      type: "chat",
      text: "보컬 그룹 만들어줘",
    });
    expect(JSON.parse(buildApprovalDecision("req-1", true))).toEqual({
      v: 1,
      type: "approval_decision",
      request_id: "req-1",
      approved: true,
    });
    expect(JSON.parse(buildLock(true))).toEqual({ v: 1, type: "lock", active: true });
  });
});

describe("reduceServerEvent", () => {
  it("appends chat responses to the transcript", () => {
    const next = reduceServerEvent(
      initialState,
      event({ type: "chat_response", status: "ok", summary: "완료", text: "했어요", commands: [] }),
    );
    expect(next.entries).toHaveLength(1);
    expect(next.entries[0].kind).toBe("assistant");
  });

  it("tracks pending approvals until resolved", () => {
    const requested = reduceServerEvent(
      initialState,
      event({
        type: "approval_request",
        request_id: "req-9",
        items: [{ command: "Delete Sequence 5", risk_reasons: ["blacklist"], warnings: [] }],
        actions: ["approve", "reject"],
      }),
    );
    expect(requested.pendingApprovals).toHaveLength(1);
    const resolved = reduceServerEvent(
      requested,
      event({ type: "approval_resolved", request_id: "req-9", approved: false }),
    );
    expect(resolved.pendingApprovals).toHaveLength(0);
  });

  it("stores the latest status", () => {
    const next = reduceServerEvent(
      initialState,
      event({ type: "status", health: "console_offline", live_lock: true, executions_blocked: true }),
    );
    expect(next.status?.health).toBe("console_offline");
    expect(next.status?.live_lock).toBe(true);
  });

  it("appends proposal, error, busy, and notice entries", () => {
    let state = reduceServerEvent(
      initialState,
      event({ type: "proposal", commands: ["Store Cue 1"], reasons: ["live lock"] }),
    );
    state = reduceServerEvent(state, event({ type: "error", message: "오류", kind: "rate_limit" }));
    state = reduceServerEvent(state, event({ type: "busy", message: "처리 중" }));
    state = reduceServerEvent(state, event({ type: "notice", message: "백업 실패" }));
    expect(state.entries.map((entry) => entry.kind)).toEqual([
      "proposal",
      "error",
      "busy",
      "notice",
    ]);
  });

  it("echoes user messages locally", () => {
    const next = addUserMessage(initialState, "안녕");
    expect(next.entries[0]).toEqual({ kind: "user", text: "안녕" });
  });
});

describe("healthLabel", () => {
  it("maps known states to Korean and passes unknown through", () => {
    expect(healthLabel("console_offline")).toContain("콘솔 오프라인");
    expect(healthLabel("weird_state")).toBe("weird_state");
  });
});

describe("M7 deploy review flow", () => {
  const reviewRequest = {
    type: "review_request",
    request_id: "review-1",
    plugin_name: "Cleaner",
    source_preview: 'Cmd("Delete Sequence 5")',
    source_length: 24,
    source_truncated: false,
    compile_ok: true,
    scan: {
      destructive: true,
      findings: [
        {
          line: 1,
          command: "Delete Sequence 5",
          kind: "blacklisted",
          matched_entry: "Delete",
          reasons: ["blacklisted command (matches closed-set entry 'Delete')"],
        },
      ],
      dynamic_calls: [],
      caveat: "static Cmd() scan is a best-effort reviewer-assist signal",
    },
    actions: ["approve", "reject"],
  };

  it("parses a review_request event", () => {
    const parsed = parseServerEvent(JSON.stringify({ v: 1, ...reviewRequest }));
    expect(parsed?.type).toBe("review_request");
  });

  it("builds a review_decision frame", () => {
    expect(JSON.parse(buildReviewDecision("review-1", false))).toEqual({
      v: 1,
      type: "review_decision",
      request_id: "review-1",
      approved: false,
    });
  });

  it("tracks pending reviews across request and resolution", () => {
    const withReview = reduceServerEvent(initialState, event(reviewRequest));
    expect(withReview.pendingReviews).toHaveLength(1);
    expect(withReview.pendingReviews[0].plugin_name).toBe("Cleaner");
    expect(withReview.pendingReviews[0].scan.destructive).toBe(true);

    const resolved = reduceServerEvent(
      withReview,
      event({ type: "review_resolved", request_id: "review-1", approved: true }),
    );
    expect(resolved.pendingReviews).toHaveLength(0);
  });

  it("keeps unrelated pending reviews on resolution", () => {
    const withReview = reduceServerEvent(initialState, event(reviewRequest));
    const stillPending = reduceServerEvent(
      withReview,
      event({ type: "review_resolved", request_id: "review-999", approved: true }),
    );
    expect(stillPending.pendingReviews).toHaveLength(1);
  });
});
