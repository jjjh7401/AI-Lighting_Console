import { describe, expect, it } from "vitest";

import {
  addUserMessage,
  buildApprovalDecision,
  buildChat,
  buildLock,
  buildReviewDecision,
  healthGuidance,
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
  it("maps all three health states to Korean and passes unknown through", () => {
    // AC-DEPLOY-008: online / console_offline / responder_degraded all surface.
    expect(healthLabel("online")).toContain("온라인");
    expect(healthLabel("console_offline")).toContain("콘솔 오프라인");
    expect(healthLabel("responder_degraded")).toContain("응답기");
    expect(healthLabel("weird_state")).toBe("weird_state");
  });
});

describe("healthGuidance", () => {
  // AC-DEPLOY-012 ①②: human-friendly cause+action guidance for the two degraded
  // states — REQ-DEPLOY-018 (console_offline) and REQ-DEPLOY-019 (responder).
  const STACK_MARKERS = ["Traceback", "Error", "Exception", "  at ", "raise "];

  it("gives console_offline a cause+action instruction (REQ-DEPLOY-018)", () => {
    const guidance = healthGuidance("console_offline");
    expect(guidance).not.toBeNull();
    expect(guidance).toContain("onPC");
    expect(guidance).toContain("OSC");
  });

  it("gives responder_degraded a responder-load + OSC-output-port instruction (REQ-DEPLOY-019)", () => {
    const guidance = healthGuidance("responder_degraded");
    expect(guidance).not.toBeNull();
    expect(guidance).toContain("CopilotResponder");
    expect(guidance).toContain("OSC");
  });

  it("shows no guidance for the healthy or unknown states", () => {
    expect(healthGuidance("online")).toBeNull();
    expect(healthGuidance("weird_state")).toBeNull();
  });

  it("never leaks a stack trace or raw-SDK marker in any guidance string", () => {
    for (const health of ["console_offline", "responder_degraded"]) {
      const guidance = healthGuidance(health) ?? "";
      for (const marker of STACK_MARKERS) {
        expect(guidance).not.toContain(marker);
      }
    }
  });
});

describe("healthGuidance with the console-input discriminator", () => {
  // Live-observed defect: the responder plugin stopped while onPC stayed up with
  // its OSC input live, and console_offline's guidance sent the operator to check
  // the two subsystems that were already fine while never naming the responder.
  // The backend now attaches a bind-probe verdict for the console's OSC input
  // port; the guidance must consume it.
  const STACK_MARKERS = ["Traceback", "Error", "Exception", "  at ", "raise "];
  const CURRENT_OFFLINE = healthGuidance("console_offline");

  it("names the responder when the console's OSC input port IS listening", () => {
    const guidance = healthGuidance("console_offline", "listening");
    expect(guidance).not.toBeNull();
    expect(guidance).toContain("CopilotResponder");
    // It must NOT be the old message: sending the operator to verify a healthy
    // onPC is exactly the wrong-cause report being fixed.
    expect(guidance).not.toBe(CURRENT_OFFLINE);
    expect(guidance).not.toContain("실행 중인지");
  });

  it("keeps the current message when nothing is listening (it is correct there)", () => {
    expect(healthGuidance("console_offline", "silent")).toBe(CURRENT_OFFLINE);
  });

  it("keeps the current message when the probe is undetermined (remote console)", () => {
    expect(healthGuidance("console_offline", "undetermined")).toBe(CURRENT_OFFLINE);
    expect(healthGuidance("console_offline", undefined)).toBe(CURRENT_OFFLINE);
    expect(healthGuidance("console_offline")).toBe(CURRENT_OFFLINE);
  });

  it("ignores the discriminator for every other health state", () => {
    expect(healthGuidance("online", "listening")).toBeNull();
    expect(healthGuidance("weird_state", "listening")).toBeNull();
    expect(healthGuidance("responder_degraded", "listening")).toBe(
      healthGuidance("responder_degraded"),
    );
  });

  it("never leaks a stack trace or raw-SDK marker in the new guidance", () => {
    const guidance = healthGuidance("console_offline", "listening") ?? "";
    for (const marker of STACK_MARKERS) {
      expect(guidance).not.toContain(marker);
    }
  });

  it("keeps the console_input verdict on the reduced status state", () => {
    const next = reduceServerEvent(
      initialState,
      event({
        type: "status",
        health: "console_offline",
        live_lock: false,
        executions_blocked: true,
        console_input: "listening",
      }),
    );
    expect(next.status?.console_input).toBe("listening");
  });

  it("tolerates a status frame from a server that sends no verdict", () => {
    const next = reduceServerEvent(
      initialState,
      event({
        type: "status",
        health: "console_offline",
        live_lock: false,
        executions_blocked: true,
      }),
    );
    expect(next.status?.health).toBe("console_offline");
    expect(healthGuidance("console_offline", next.status?.console_input)).toBe(CURRENT_OFFLINE);
  });
});

describe("healthGuidance with the reply-port mismatch", () => {
  // The third console_offline cause. A grandMA3 OSC entry has ONE port used for
  // BOTH directions, so the port the console replies through and the port the
  // app listens on are two hand-synchronised numbers. When they drift the link
  // goes quiet with both subsystems healthy — the responder message would then
  // be wrong in a new way (the plugin IS running; it is answering elsewhere).
  const RESPONDER = healthGuidance("console_offline", "listening");

  it("names BOTH ports so the operator can reconcile them", () => {
    const guidance = healthGuidance("console_offline", "listening", 9005, 9000);
    expect(guidance).not.toBeNull();
    expect(guidance).toContain("9005");
    expect(guidance).toContain("9000");
    expect(guidance).not.toBe(RESPONDER);
  });

  it("offers both fixes and applies neither", () => {
    // REQ-DEPLOY-026 — the app never changes its own effective port. The
    // guidance must read as a choice for the operator, not as a report of a
    // change the app already made.
    const guidance = healthGuidance("console_offline", "listening", 9005, 9000) ?? "";
    expect(guidance).toContain("onPC");
    expect(guidance).toContain("설정");
    for (const applied of ["변경했습니다", "자동으로", "적용했습니다", "전환했습니다"]) {
      expect(guidance).not.toContain(applied);
    }
  });

  it("takes priority over the responder message when both apply", () => {
    // "input listening" is true in BOTH cases; the mismatch is the more specific
    // finding, and it names a cause the responder message would misattribute.
    expect(healthGuidance("console_offline", "listening", 9005, 9000)).not.toBe(RESPONDER);
  });

  it("falls back to the responder message when discovery found nothing", () => {
    expect(healthGuidance("console_offline", "listening", null, 9000)).toBe(RESPONDER);
    expect(healthGuidance("console_offline", "listening", undefined, undefined)).toBe(RESPONDER);
  });

  it("ignores a reported port that equals the configured one", () => {
    // Not a mismatch; reporting it would be a contradiction on screen.
    expect(healthGuidance("console_offline", "listening", 9000, 9000)).toBe(RESPONDER);
  });

  it("ignores the mismatch for every other health state", () => {
    expect(healthGuidance("online", "listening", 9005, 9000)).toBeNull();
    expect(healthGuidance("responder_degraded", "listening", 9005, 9000)).toBe(
      healthGuidance("responder_degraded"),
    );
  });

  it("keeps both port numbers on the reduced status state", () => {
    const next = reduceServerEvent(
      initialState,
      event({
        type: "status",
        health: "console_offline",
        live_lock: false,
        executions_blocked: true,
        console_input: "listening",
        reply_port: 9005,
        receive_port: 9000,
      }),
    );
    expect(next.status?.reply_port).toBe(9005);
    expect(next.status?.receive_port).toBe(9000);
  });

  it("tolerates a status frame from a server that does not diagnose", () => {
    const next = reduceServerEvent(
      initialState,
      event({
        type: "status",
        health: "console_offline",
        live_lock: false,
        executions_blocked: true,
        console_input: "listening",
      }),
    );
    expect(
      healthGuidance(
        next.status!.health,
        next.status?.console_input,
        next.status?.reply_port,
        next.status?.receive_port,
      ),
    ).toBe(RESPONDER);
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
