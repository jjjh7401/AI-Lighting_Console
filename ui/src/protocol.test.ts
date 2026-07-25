import { describe, expect, it } from "vitest";

import {
  addUserMessage,
  buildApprovalDecision,
  buildChat,
  buildDashCatalogRequest,
  buildLock,
  buildPanelCatalogRequest,
  buildPanelExecute,
  buildPanelPin,
  buildPanelStop,
  buildPanelUnpin,
  buildReviewDecision,
  clearOnDisconnect,
  healthGuidance,
  healthLabel,
  initialState,
  panelItemId,
  parseServerEvent,
  PROTOCOL_VERSION,
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

  it("appends execution previews to the transcript", () => {
    const next = reduceServerEvent(
      initialState,
      event({
        type: "execution_preview",
        preview_id: "preview-1",
        summary: "실행 전 미리보기 — 1개 명령",
        risk_level: "caution",
        commands: [
          {
            command: "Store /Overwrite Cue 4",
            action: "store_overwrite",
            target_kind: "cue",
            target: "4",
            label: "Cue 4 덮어쓰기",
          },
        ],
        warnings: [
          {
            severity: "caution",
            label: "덮어쓰기",
            detail: "기존 cue를 바꿀 수 있습니다.",
            command: "Store /Overwrite Cue 4",
          },
        ],
      }),
    );

    expect(next.entries).toHaveLength(1);
    expect(next.entries[0].kind).toBe("preview");
    if (next.entries[0].kind === "preview") {
      expect(next.entries[0].preview.preview_id).toBe("preview-1");
      expect(next.entries[0].preview.warnings[0].label).toBe("덮어쓰기");
    }
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

// -- SPEC-COPILOT-SHOWUI-001 M1 — show-control panel protocol contract ---------
//
// The panel types are an ADDITIVE v1 extension registered on BOTH allowlists
// (REQ-SHOWUI-014). This side's unknown-type contract — silently drop — is
// deliberately NOT the server's (which rejects loudly), and both halves are
// pinned so a later milestone cannot "harmonise" them into one behaviour.

const catalogEvent = {
  type: "panel_catalog",
  items: [
    {
      id: "executor:191",
      kind: "sequence",
      target_kind: "executor",
      target: 191,
      name: "Summer Rock",
      appearance: "#ff3fa4",
      source: "auto",
    },
    {
      id: "sequence:7",
      kind: "look",
      target_kind: "sequence",
      target: 7,
      name: "Cyan Look",
      appearance: null,
      source: "pin",
    },
  ],
  sections: [
    {
      name: "sequences",
      status: "ok",
      truncated: true,
      drilldown_capped: false,
      contents_unavailable: false,
    },
    {
      name: "pages",
      status: "path_not_resolved",
      truncated: false,
      drilldown_capped: false,
      contents_unavailable: false,
    },
  ],
};

describe("panel protocol parity (AC-SHOWUI-001, client half)", () => {
  it("parses every new panel event", () => {
    expect(parseServerEvent(JSON.stringify({ v: 1, ...catalogEvent }))?.type).toBe("panel_catalog");
    expect(
      parseServerEvent(
        JSON.stringify({
          v: 1,
          type: "panel_item_state",
          id: "executor:191",
          target_kind: "executor",
          target: 191,
          running: true,
          cue: "3",
        }),
      )?.type,
    ).toBe("panel_item_state");
    expect(
      parseServerEvent(
        JSON.stringify({
          v: 1,
          type: "panel_busy",
          id: "executor:191",
          target_kind: "executor",
          target: 191,
          message: "실행 처리 중입니다",
        }),
      )?.type,
    ).toBe("panel_busy");
  });

  it("still drops the wrong version and unknown types silently", () => {
    // The asymmetric half of REQ-SHOWUI-014: this side returns null, it does
    // NOT throw. Widening the allowlist must not turn it into a prefix match.
    expect(parseServerEvent(JSON.stringify({ v: 2, ...catalogEvent }))).toBeNull();
    expect(parseServerEvent(JSON.stringify({ v: 1, type: "panel_mystery" }))).toBeNull();
    expect(parseServerEvent(JSON.stringify({ v: 1, type: "panel_catalog_extra" }))).toBeNull();
  });

  it("builds every new client frame at v1", () => {
    expect(JSON.parse(buildPanelExecute("executor", 191))).toEqual({
      v: 1,
      type: "panel_execute",
      target_kind: "executor",
      target: 191,
    });
    expect(JSON.parse(buildPanelStop("sequence", 41))).toEqual({
      v: 1,
      type: "panel_stop",
      target_kind: "sequence",
      target: 41,
    });
    expect(JSON.parse(buildPanelUnpin("executor", 201))).toEqual({
      v: 1,
      type: "panel_unpin",
      target_kind: "executor",
      target: 201,
    });
    // REQ-SHOWUI-004: the pin seed is server-side `_last_created`, so the
    // client sends no target it could get wrong.
    expect(JSON.parse(buildPanelPin())).toEqual({ v: 1, type: "panel_pin" });
    expect(JSON.parse(buildPanelCatalogRequest())).toEqual({
      v: 1,
      type: "panel_catalog_request",
    });
  });

  it("keys tiles by the real object number, never by list position", () => {
    // REQ-SHOWUI-003 — pool numbers are non-contiguous.
    expect(panelItemId("executor", 191)).toBe("executor:191");
    expect(panelItemId("sequence", 7)).toBe("sequence:7");
  });
});

describe("panel reducer", () => {
  it("starts with an empty panel", () => {
    expect(initialState.panel.items).toEqual([]);
    expect(initialState.panel.sections).toEqual([]);
    expect(initialState.panel.running).toEqual({});
    expect(initialState.panel.busy).toBeNull();
  });

  it("stores the catalog in wire order without sorting it", () => {
    // REQ-SHOWUI-017: the grid never reflows during a show. Wire order IS
    // grid order; a "helpful" sort would move a tile under the operator.
    const next = reduceServerEvent(initialState, event(catalogEvent));
    expect(next.panel.items.map((item) => item.id)).toEqual(["executor:191", "sequence:7"]);
    expect(next.panel.items[0].name).toBe("Summer Rock");
    expect(next.panel.items[1].appearance).toBeNull();
  });

  it("keeps the two catalog failure causes distinct (REQ-SHOWUI-002)", () => {
    const next = reduceServerEvent(
      initialState,
      event({
        ...catalogEvent,
        sections: [
          { name: "sequences", status: "console_unreachable" },
          { name: "pages", status: "path_not_resolved" },
        ],
      }),
    );
    expect(next.panel.sections.map((section) => section.status)).toEqual([
      "console_unreachable",
      "path_not_resolved",
    ]);
  });

  it("carries the completeness flags through to the UI (REQ-SHOWUI-001)", () => {
    const next = reduceServerEvent(initialState, event(catalogEvent));
    expect(next.panel.sections[0].truncated).toBe(true);
    expect(next.panel.sections[0].drilldown_capped).toBe(false);
    expect(next.panel.sections[0].contents_unavailable).toBe(false);
  });

  it("replaces the catalog on refresh rather than appending a duplicate", () => {
    const first = reduceServerEvent(initialState, event(catalogEvent));
    const second = reduceServerEvent(first, event(catalogEvent));
    expect(second.panel.items).toHaveLength(2);
  });

  it("tracks per-tile running state keyed by the real object number", () => {
    let state = reduceServerEvent(initialState, event(catalogEvent));
    state = reduceServerEvent(
      state,
      event({
        type: "panel_item_state",
        id: "executor:191",
        target_kind: "executor",
        target: 191,
        running: true,
        cue: "3",
      }),
    );
    expect(state.panel.running["executor:191"]).toEqual({ running: true, cue: "3" });
    expect(state.panel.running["sequence:7"]).toBeUndefined();

    state = reduceServerEvent(
      state,
      event({
        type: "panel_item_state",
        id: "executor:191",
        target_kind: "executor",
        target: 191,
        running: false,
        cue: null,
      }),
    );
    expect(state.panel.running["executor:191"]).toEqual({ running: false, cue: null });
  });

  it("records a busy refusal against the tile that was pressed", () => {
    // REQ-SHOWUI-011: a persistent per-tile state, never a toast (design.md §7).
    const state = reduceServerEvent(
      initialState,
      event({
        type: "panel_busy",
        id: "executor:191",
        target_kind: "executor",
        target: 191,
        message: "실행 처리 중입니다",
      }),
    );
    expect(state.panel.busy).toEqual({ id: "executor:191", message: "실행 처리 중입니다" });
  });

  it("leaves the rest of the UI state untouched", () => {
    const state = reduceServerEvent(initialState, event(catalogEvent));
    expect(state.entries).toEqual([]);
    expect(state.status).toBeNull();
  });
});

describe("clearOnDisconnect (REQ-SHOWUI-015/016 — fail closed)", () => {
  function connectedState() {
    let state = reduceServerEvent(initialState, event(catalogEvent));
    state = reduceServerEvent(
      state,
      event({
        type: "panel_item_state",
        id: "executor:191",
        target_kind: "executor",
        target: 191,
        running: true,
        cue: "3",
      }),
    );
    state = reduceServerEvent(
      state,
      event({
        type: "panel_busy",
        id: "sequence:7",
        target_kind: "sequence",
        target: 7,
        message: "실행 처리 중입니다",
      }),
    );
    return reduceServerEvent(
      state,
      event({
        type: "approval_request",
        request_id: "req-1",
        items: [{ command: "Go+ Executor 191", risk_reasons: [], warnings: [] }],
        actions: ["approve", "reject"],
      }),
    );
  }

  it("erases running state — never renders 'probably still running'", () => {
    const cleared = clearOnDisconnect(connectedState());
    expect(cleared.panel.running).toEqual({});
    expect(cleared.panel.busy).toBeNull();
  });

  it("keeps the catalog so the panel can re-render while offline", () => {
    // Only running state is volatile derived state; the tile list is not.
    const cleared = clearOnDisconnect(connectedState());
    expect(cleared.panel.items).toHaveLength(2);
    expect(cleared.panel.sections).toHaveLength(2);
  });

  it("also denies the pending approval cards it already cleared", () => {
    const cleared = clearOnDisconnect(connectedState());
    expect(cleared.pendingApprovals).toHaveLength(0);
    expect(cleared.pendingReviews).toHaveLength(0);
  });

  it("is a no-op on an already-clean state", () => {
    expect(clearOnDisconnect(initialState)).toBe(initialState);
  });
});

// -- SPEC-COPILOT-DASHUI-001 M1 — console-info dashboard protocol contract -----
//
// Another ADDITIVE v1 extension on the panel family's terms (AC-DASHUI-001):
// PROTOCOL_VERSION stays 1, the new event type lands on BOTH allowlists in the
// same change, and this side's unknown-type contract — silently drop — stays
// deliberately different from the server's loud ProtocolError.

const dashCatalogEvent = {
  type: "dash_catalog",
  sections: [
    {
      name: "groups",
      status: "ok",
      truncated: false,
      drilldown_capped: false,
      contents_unavailable: false,
      items: [
        { no: 3, name: "Vocals", appearance: "#00c8ff" },
        { no: 11, name: "Drums", appearance: null },
      ],
    },
    {
      name: "presets",
      status: "console_unreachable",
      truncated: false,
      drilldown_capped: true,
      contents_unavailable: false,
      items: [],
    },
  ],
};

describe("dash protocol parity (AC-DASHUI-001, client half)", () => {
  it("keeps the protocol at v1", () => {
    expect(PROTOCOL_VERSION).toBe(1);
  });

  it("parses a dash_catalog event", () => {
    const parsed = parseServerEvent(JSON.stringify({ v: 1, ...dashCatalogEvent }));
    expect(parsed?.type).toBe("dash_catalog");
  });

  it("still drops the wrong version and unknown types silently", () => {
    // The asymmetric half of REQ-DASHUI-006's parity: this side returns null,
    // it does NOT throw — and widening must not turn it into a prefix match.
    expect(parseServerEvent(JSON.stringify({ v: 2, ...dashCatalogEvent }))).toBeNull();
    expect(parseServerEvent(JSON.stringify({ v: 1, type: "dash_mystery" }))).toBeNull();
    expect(parseServerEvent(JSON.stringify({ v: 1, type: "dash_catalog_extra" }))).toBeNull();
  });

  it("builds the dash_catalog_request frame at v1", () => {
    // REQ-DASHUI-006: payload-free — sent on connect and on manual refresh.
    expect(JSON.parse(buildDashCatalogRequest())).toEqual({
      v: 1,
      type: "dash_catalog_request",
    });
  });

  it("builds a macro panel_execute frame (additive target class)", () => {
    // REQ-DASHUI-010/012: the enum widening on this side; the type must both
    // compile and serialize the new class unchanged.
    expect(JSON.parse(buildPanelExecute("macro", 3))).toEqual({
      v: 1,
      type: "panel_execute",
      target_kind: "macro",
      target: 3,
    });
  });
});

describe("dash reducer (REQ-DASHUI-006 replace + freshness)", () => {
  it("starts empty, never-synced, and not stale", () => {
    expect(initialState.dash.sections).toEqual([]);
    expect(initialState.dash.lastSyncAt).toBeNull();
    expect(initialState.dash.stale).toBe(false);
  });

  it("stores sections in wire order and stamps the sync time", () => {
    const next = reduceServerEvent(initialState, event(dashCatalogEvent), 1_753_300_000_000);
    expect(next.dash.sections.map((section) => section.name)).toEqual(["groups", "presets"]);
    expect(next.dash.sections[0].items.map((item) => item.no)).toEqual([3, 11]);
    expect(next.dash.lastSyncAt).toBe(1_753_300_000_000);
    expect(next.dash.stale).toBe(false);
  });

  it("REPLACES the catalog on refresh rather than merging", () => {
    // REQ-DASHUI-006: merging would keep pools the showfile no longer has.
    const first = reduceServerEvent(initialState, event(dashCatalogEvent), 1000);
    const second = reduceServerEvent(
      first,
      event({
        type: "dash_catalog",
        sections: [{ name: "macros", status: "ok", items: [{ no: 9, name: "Blackout" }] }],
      }),
      2000,
    );
    expect(second.dash.sections).toHaveLength(1);
    expect(second.dash.sections[0].name).toBe("macros");
    expect(second.dash.lastSyncAt).toBe(2000);
  });

  it("keeps the two failure causes distinct (REQ-DASHUI-004)", () => {
    const next = reduceServerEvent(
      initialState,
      event({
        type: "dash_catalog",
        sections: [
          { name: "groups", status: "path_not_resolved", items: [] },
          { name: "presets", status: "console_unreachable", items: [] },
        ],
      }),
      1000,
    );
    expect(next.dash.sections.map((section) => section.status)).toEqual([
      "path_not_resolved",
      "console_unreachable",
    ]);
  });

  it("carries info entries through without inventing a fire address", () => {
    // AC-DASHUI-003 type half: the wire shape has no target_kind and the
    // reducer must not add one.
    const next = reduceServerEvent(initialState, event(dashCatalogEvent), 1000);
    for (const section of next.dash.sections) {
      for (const item of section.items) {
        expect(Object.keys(item)).not.toContain("target_kind");
        expect(Object.keys(item)).not.toContain("id");
      }
    }
  });

  it("leaves chat, status, and panel state untouched", () => {
    const next = reduceServerEvent(initialState, event(dashCatalogEvent), 1000);
    expect(next.entries).toEqual([]);
    expect(next.status).toBeNull();
    expect(next.panel).toBe(initialState.panel);
  });
});

describe("clearOnDisconnect dash extension (AC-DASHUI-017, reducer half)", () => {
  function syncedState() {
    let state = reduceServerEvent(initialState, event(dashCatalogEvent), 1000);
    state = reduceServerEvent(state, event(catalogEvent));
    state = reduceServerEvent(
      state,
      event({
        type: "panel_item_state",
        id: "executor:191",
        target_kind: "executor",
        target: 191,
        running: true,
        cue: "3",
      }),
    );
    return state;
  }

  it("marks a synced dash catalog stale instead of guessing freshness", () => {
    // REQ-DASHUI-015: the catalog on screen may no longer match the console —
    // say so, rather than rendering yesterday's rig as current.
    const cleared = clearOnDisconnect(syncedState());
    expect(cleared.dash.stale).toBe(true);
  });

  it("keeps the dash sections so the dashboard renders (inert) offline", () => {
    const cleared = clearOnDisconnect(syncedState());
    expect(cleared.dash.sections).toHaveLength(2);
    expect(cleared.dash.lastSyncAt).toBe(1000);
  });

  it("still clears the panel volatile state alongside", () => {
    // One function, all the volatile state — a disconnect handler must not be
    // able to clear half of it and keep the other half on screen.
    const cleared = clearOnDisconnect(syncedState());
    expect(cleared.panel.running).toEqual({});
    expect(cleared.panel.busy).toBeNull();
  });

  it("a fresh catalog after reconnect clears the stale mark", () => {
    const cleared = clearOnDisconnect(syncedState());
    const resynced = reduceServerEvent(cleared, event(dashCatalogEvent), 2000);
    expect(resynced.dash.stale).toBe(false);
    expect(resynced.dash.lastSyncAt).toBe(2000);
  });

  it("does not mark stale when the dash never synced", () => {
    // Before the first catalog there is no freshness claim to withdraw.
    const chatOnly = addUserMessage(initialState, "안녕");
    expect(clearOnDisconnect(chatOnly).dash.stale).toBe(false);
  });

  it("remains a no-op on an already-clean state", () => {
    expect(clearOnDisconnect(initialState)).toBe(initialState);
  });
});
