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
  | {
      v: 1;
      type: "status";
      health: string;
      live_lock: boolean;
      executions_blocked: boolean;
    }
  | { v: 1; type: "proposal"; commands: string[]; reasons: string[] }
  | { v: 1; type: "error"; message: string; kind: string }
  | { v: 1; type: "busy"; message: string }
  | { v: 1; type: "notice"; message: string };

const SERVER_EVENT_TYPES = new Set([
  "chat_response",
  "approval_request",
  "approval_resolved",
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
}

export interface PendingApproval {
  request_id: string;
  items: ApprovalItem[];
}

export interface UiState {
  entries: ChatEntry[];
  status: StatusState | null;
  pendingApprovals: PendingApproval[];
}

export const initialState: UiState = {
  entries: [],
  status: null,
  pendingApprovals: [],
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
    case "status":
      return {
        ...state,
        status: {
          health: event.health,
          live_lock: event.live_lock,
          executions_blocked: event.executions_blocked,
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

// -- Korean display labels ---------------------------------------------------------

export const HEALTH_LABELS: Record<string, string> = {
  online: "콘솔 온라인",
  console_offline: "콘솔 오프라인 — 신규 실행 차단",
  responder_degraded: "응답기 저하 — 결과 확인 불가",
};

export function healthLabel(health: string): string {
  return HEALTH_LABELS[health] ?? health;
}
