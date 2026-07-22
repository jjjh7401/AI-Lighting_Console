// WebSocket protocol v1 — TypeScript mirror of server/web/PROTOCOL.md.
// Pure functions only (parse / build / reduce) so the module is unit-testable
// without a DOM; the socket hook and components consume it.

export const PROTOCOL_VERSION = 1;

export interface CommandView {
  command: string;
  status: string;
  label: string;
  detail: string;
}

export interface ApprovalItem {
  command: string;
  risk_reasons: string[];
  warnings: string[];
}

// -- M7 deploy review (REQ-MVP-019/027) ---------------------------------------

export interface ScanFinding {
  line: number;
  command: string;
  kind: string; // "blacklisted" | "invoking" | "unparseable"
  matched_entry: string | null;
  reasons: string[];
}

export interface DynamicCallView {
  line: number;
  snippet: string;
}

export interface ScanReportView {
  destructive: boolean;
  findings: ScanFinding[];
  dynamic_calls: DynamicCallView[];
  caveat: string;
}

export interface ReviewRequestView {
  request_id: string;
  plugin_name: string;
  source_preview: string;
  source_length: number;
  source_truncated: boolean;
  compile_ok: boolean;
  scan: ScanReportView;
}

/**
 * The console-OSC-input reachability verdict carried on `status`.
 *
 * Three values, not two: "undetermined" (a remote console whose port cannot be
 * bound from here, or a server that did not probe) must stay distinguishable
 * from "silent". Collapsing them would show a confident wrong cause again —
 * the exact defect the verdict exists to remove.
 */
export type ConsoleInput = "listening" | "silent" | "undetermined";

export type ServerEvent =
  | {
      v: 1;
      type: "chat_response";
      status: string;
      summary: string;
      text: string;
      commands: CommandView[];
    }
  | {
      v: 1;
      type: "approval_request";
      request_id: string;
      items: ApprovalItem[];
      actions: string[];
    }
  | { v: 1; type: "approval_resolved"; request_id: string; approved: boolean }
  | ({
      v: 1;
      type: "review_request";
      actions: string[];
    } & ReviewRequestView)
  | { v: 1; type: "review_resolved"; request_id: string; approved: boolean }
  | {
      v: 1;
      type: "status";
      health: string;
      live_lock: boolean;
      executions_blocked: boolean;
      // Additive (protocol stays v1) — the console-OSC-input bind verdict.
      // Absent from a server that does not probe; treated as "undetermined".
      console_input?: ConsoleInput;
      // Additive — the reply-port MISMATCH pair, present together or not at all:
      // a console reply was observed on `reply_port` while the app listens on
      // `receive_port`. Reported, never applied (REQ-DEPLOY-026).
      reply_port?: number | null;
      receive_port?: number | null;
    }
  | { v: 1; type: "proposal"; commands: string[]; reasons: string[] }
  | { v: 1; type: "error"; message: string; kind: string }
  | { v: 1; type: "busy"; message: string }
  | { v: 1; type: "notice"; message: string };

const SERVER_EVENT_TYPES = new Set([
  "chat_response",
  "approval_request",
  "approval_resolved",
  "review_request",
  "review_resolved",
  "status",
  "proposal",
  "error",
  "busy",
  "notice",
]);

/** Parse one server frame; unknown/foreign frames return null (ignored). */
export function parseServerEvent(raw: string): ServerEvent | null {
  let data: unknown;
  try {
    data = JSON.parse(raw);
  } catch {
    return null;
  }
  if (typeof data !== "object" || data === null) return null;
  const event = data as { v?: unknown; type?: unknown };
  if (event.v !== PROTOCOL_VERSION) return null;
  if (typeof event.type !== "string" || !SERVER_EVENT_TYPES.has(event.type)) return null;
  return data as ServerEvent;
}

// -- client -> server builders -------------------------------------------------

export function buildChat(text: string): string {
  return JSON.stringify({ v: PROTOCOL_VERSION, type: "chat", text });
}

export function buildApprovalDecision(requestId: string, approved: boolean): string {
  return JSON.stringify({
    v: PROTOCOL_VERSION,
    type: "approval_decision",
    request_id: requestId,
    approved,
  });
}

export function buildReviewDecision(requestId: string, approved: boolean): string {
  return JSON.stringify({
    v: PROTOCOL_VERSION,
    type: "review_decision",
    request_id: requestId,
    approved,
  });
}

export function buildLock(active: boolean): string {
  return JSON.stringify({ v: PROTOCOL_VERSION, type: "lock", active });
}

export function buildStatusRequest(): string {
  return JSON.stringify({ v: PROTOCOL_VERSION, type: "status_request" });
}

// -- UI state reducer ------------------------------------------------------------

export type ChatEntry =
  | { kind: "user"; text: string }
  | {
      kind: "assistant";
      status: string;
      summary: string;
      text: string;
      commands: CommandView[];
    }
  | { kind: "proposal"; commands: string[]; reasons: string[] }
  | { kind: "error"; message: string; errorKind: string }
  | { kind: "notice"; message: string }
  | { kind: "busy"; message: string };

export interface StatusState {
  health: string;
  live_lock: boolean;
  executions_blocked: boolean;
  console_input?: ConsoleInput;
  reply_port?: number | null;
  receive_port?: number | null;
}

export interface PendingApproval {
  request_id: string;
  items: ApprovalItem[];
}

export interface UiState {
  entries: ChatEntry[];
  status: StatusState | null;
  pendingApprovals: PendingApproval[];
  pendingReviews: ReviewRequestView[];
}

export const initialState: UiState = {
  entries: [],
  status: null,
  pendingApprovals: [],
  pendingReviews: [],
};

/** Fold one server event into the UI state. */
export function reduceServerEvent(state: UiState, event: ServerEvent): UiState {
  switch (event.type) {
    case "chat_response":
      return {
        ...state,
        entries: [
          ...state.entries,
          {
            kind: "assistant",
            status: event.status,
            summary: event.summary,
            text: event.text,
            commands: event.commands,
          },
        ],
      };
    case "approval_request":
      return {
        ...state,
        pendingApprovals: [
          ...state.pendingApprovals,
          { request_id: event.request_id, items: event.items },
        ],
      };
    case "approval_resolved":
      return {
        ...state,
        pendingApprovals: state.pendingApprovals.filter(
          (pending) => pending.request_id !== event.request_id,
        ),
      };
    case "review_request":
      return {
        ...state,
        pendingReviews: [
          ...state.pendingReviews,
          {
            request_id: event.request_id,
            plugin_name: event.plugin_name,
            source_preview: event.source_preview,
            source_length: event.source_length,
            source_truncated: event.source_truncated,
            compile_ok: event.compile_ok,
            scan: event.scan,
          },
        ],
      };
    case "review_resolved":
      return {
        ...state,
        pendingReviews: state.pendingReviews.filter(
          (pending) => pending.request_id !== event.request_id,
        ),
      };
    case "status":
      return {
        ...state,
        status: {
          health: event.health,
          live_lock: event.live_lock,
          executions_blocked: event.executions_blocked,
          console_input: event.console_input,
          reply_port: event.reply_port,
          receive_port: event.receive_port,
        },
      };
    case "proposal":
      return {
        ...state,
        entries: [
          ...state.entries,
          { kind: "proposal", commands: event.commands, reasons: event.reasons },
        ],
      };
    case "error":
      return {
        ...state,
        entries: [...state.entries, { kind: "error", message: event.message, errorKind: event.kind }],
      };
    case "busy":
      return { ...state, entries: [...state.entries, { kind: "busy", message: event.message }] };
    case "notice":
      return { ...state, entries: [...state.entries, { kind: "notice", message: event.message }] };
  }
}

/** Append the user's own chat line (echoed locally on send). */
export function addUserMessage(state: UiState, text: string): UiState {
  return { ...state, entries: [...state.entries, { kind: "user", text }] };
}

/**
 * Drop every pending approval/review card. The server fail-safe-denies all
 * of a session's own outstanding requests on that session's disconnect —
 * without this, a stale card sits in the UI forever after a reconnect,
 * misleading the operator into thinking a decision is still awaited when
 * the server already resolved it.
 */
export function clearPendingRequests(state: UiState): UiState {
  if (state.pendingApprovals.length === 0 && state.pendingReviews.length === 0) return state;
  return { ...state, pendingApprovals: [], pendingReviews: [] };
}

// -- Korean display labels ---------------------------------------------------------

export const HEALTH_LABELS: Record<string, string> = {
  online: "콘솔 온라인",
  console_offline: "콘솔 오프라인 — 신규 실행 차단",
  responder_degraded: "응답기 저하 — 결과 확인 불가",
};

export function healthLabel(health: string): string {
  return HEALTH_LABELS[health] ?? health;
}

// Cause + action guidance for each degraded health state (REQ-DEPLOY-018/019).
// Human-friendly Korean only — NEVER a stack trace or raw SDK original. The
// healthy state (and any unknown state) yields null so no guidance line shows.
export const HEALTH_GUIDANCE: Record<string, string> = {
  console_offline: "onPC가 실행 중인지, OSC 입력이 켜져 있는지 확인해 주세요.",
  responder_degraded:
    "CopilotResponder를 onPC에서 로드하고, onPC OSC 출력을 앱의 피드백 수신 포트로 설정해 주세요.",
};

// console_offline is reached by TWO different situations: onPC is genuinely
// down, and onPC is up with its OSC input live but the responder plugin — the
// only thing that ever sends — has stopped. The backend's bind probe tells them
// apart; without this refinement the second one is sent to inspect the two
// subsystems that are already healthy while the real cause goes unnamed.
// Claim discipline: the port sentence states what was actually observed (the
// port is held), and the cause stays hedged — a held port proves something is
// listening, not that it is onPC.
export const CONSOLE_OFFLINE_RESPONDER_GUIDANCE =
  "콘솔 OSC 입력 포트는 열려 있습니다 — CopilotResponder 플러그인이 실행 중이 아닐 수 있습니다. " +
  "onPC의 Plugins 풀에서 CopilotResponder를 실행해 주세요.";

// The third console_offline cause. A grandMA3 OSC entry has ONE port used for
// BOTH directions, so the port the console replies THROUGH lives in the
// console's OSC table while the port the app listens ON lives in the app's
// settings — two numbers, two places, kept in sync by hand. When they drift the
// link goes quiet with every subsystem healthy, and the responder message above
// would be wrong in a NEW way: the plugin is running, it is just answering
// somewhere nobody is listening.
//
// Both numbers are named and both fixes are offered, because the app must not
// change its own effective port (REQ-DEPLOY-026) — the operator decides whether
// the console moves or the app does.
export function consoleOfflineReplyPortGuidance(replyPort: number, receivePort: number): string {
  return (
    `콘솔이 응답을 다른 포트로 보내고 있습니다 — 콘솔은 ${replyPort}번 포트로 회신하는데 ` +
    `앱은 ${receivePort}번 포트에서 수신 대기 중입니다. ` +
    `onPC의 OSC 설정에서 해당 항목 Port를 ${receivePort}(으)로 맞추거나, ` +
    `앱 설정(Settings)의 수신 포트를 ${replyPort}(으)로 바꾼 뒤 다시 시작해 주세요.`
  );
}

/**
 * Cause+action guidance for a health state, refined by the backend's diagnosis.
 *
 * Ordered most-specific first. A reply-port mismatch implies the console's input
 * IS listening, so both refinements apply at once — but only the mismatch names
 * the real cause, and the responder message would misattribute it.
 *
 * Every argument is optional: absent / "undetermined" / "silent" / no observed
 * reply port all keep the message that is correct in that case, so a server that
 * does not diagnose behaves exactly as before.
 */
export function healthGuidance(
  health: string,
  consoleInput?: ConsoleInput,
  replyPort?: number | null,
  receivePort?: number | null,
): string | null {
  if (health === "console_offline") {
    if (
      typeof replyPort === "number" &&
      typeof receivePort === "number" &&
      replyPort !== receivePort
    ) {
      return consoleOfflineReplyPortGuidance(replyPort, receivePort);
    }
    if (consoleInput === "listening") {
      return CONSOLE_OFFLINE_RESPONDER_GUIDANCE;
    }
  }
  return HEALTH_GUIDANCE[health] ?? null;
}
