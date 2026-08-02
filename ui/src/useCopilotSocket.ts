// WebSocket hook — owns the connection, folds server events into UI state.
import { useCallback, useEffect, useReducer, useRef, useState } from "react";

import { backendBase } from "./launchContext";
import {
  addUserMessage,
  buildApprovalDecision,
  buildChat,
  buildCueMonitorRequest,
  buildDashCatalogRequest,
  buildLock,
  buildPanelBack,
  buildPanelCatalogRequest,
  buildPanelExecute,
  buildPanelGoto,
  buildPanelStop,
  buildReviewDecision,
  buildStatusRequest,
  clearPendingRequests,
  initialState,
  parseServerEvent,
  reduceServerEvent,
  type PanelTargetKind,
  type UiState,
} from "./protocol";

export type Action =
  | { kind: "server"; raw: string }
  | { kind: "user"; text: string }
  | { kind: "disconnected" };

// Exported for direct unit testing (see useCopilotSocket.test.ts): the hook
// itself needs a DOM/renderer this project's test setup doesn't provide, but
// the state transition is a pure function like the rest of protocol.ts.
export function reducer(state: UiState, action: Action): UiState {
  if (action.kind === "user") return addUserMessage(state, action.text);
  if (action.kind === "disconnected") return clearPendingRequests(state);
  const event = parseServerEvent(action.raw);
  return event === null ? state : reduceServerEvent(state, event);
}

function defaultUrl(): string {
  // Stage-2: the window is served from tauri://localhost, so window.location is
  // the app origin, not the backend. Use the injected absolute backend base and
  // turn its http(s) scheme into ws(s). Stage-1: no base injected → same-origin,
  // exactly as before.
  const base = backendBase();
  if (base) return `${base.replace(/^http/, "ws")}/ws`;
  const scheme = window.location.protocol === "https:" ? "wss" : "ws";
  return `${scheme}://${window.location.host}/ws`;
}

// M7.1 (REQ-DEPLOY-002a) — per-launch token consumption seam.
//
// The server authorizes every /ws upgrade on Origin + token BEFORE accept()
// (server/web/handshake.py). The token rides Sec-WebSocket-Protocol because it
// is the only handshake field the browser WebSocket API lets us set, and unlike
// a query string it stays out of access logs and Referer headers.
//
// Delivery is mode-specific: Stage-2 (Tauri) injects the token into the webview
// context over IPC — an in-process channel no other local process can read
// (wired at M7.4). Stage-1 browser mode has no such channel, so `launchToken()`
// returns undefined and the connect stays exactly as it was pre-M7.1; there the
// server's Origin allowlist is the real CSWSH closer.
export const BASE_SUBPROTOCOL = "copilot.v1";
export const TOKEN_SUBPROTOCOL_PREFIX = "copilot-token.";

type TokenContext = { __COPILOT_LAUNCH_TOKEN__?: string };

export function launchToken(): string | undefined {
  return (globalThis as TokenContext).__COPILOT_LAUNCH_TOKEN__ || undefined;
}

export function connectProtocols(token: string | undefined): string[] | undefined {
  // The base protocol is offered alongside the token so the server has a
  // non-secret value to echo back in the handshake response (RFC 6455 lets it
  // select only an offered subprotocol).
  if (!token) return undefined;
  return [BASE_SUBPROTOCOL, `${TOKEN_SUBPROTOCOL_PREFIX}${token}`];
}

/**
 * The frames sent on every successful (re)connect (AC-DASHUI-017,
 * design.md §5 "접속(재접속 포함) 시 자동 1회") — panel catalog, dash
 * catalog, and status, so a reconnect rebuilds both catalogs plus health
 * from scratch rather than trusting the (now possibly stale) pre-disconnect
 * state. A pure function so the dispatch set is unit-testable without a
 * live WebSocket (this project's no-DOM-harness convention).
 */
export function connectResyncFrames(): string[] {
  return [
    buildPanelCatalogRequest(),
    buildDashCatalogRequest(),
    buildCueMonitorRequest(),
    buildStatusRequest(),
  ];
}

// T-C, wave 2 (ad-hoc contract, no SPEC on file): unlike `dash_catalog`
// (REQ-DASHUI-021 forbids timer polling — it resyncs only on connect and on
// an executed chat command), the cue monitor is explicitly contracted to
// poll, because "which cue is live right now" goes stale between chat turns
// with nothing else to trigger a refresh. Kept as a named constant so the
// cadence is a single, documented choice rather than a magic number buried
// in the effect below.
export const CUE_MONITOR_POLL_INTERVAL_MS = 5_000;

/**
 * The dash resync frame one incoming server event earns, or null.
 *
 * M6-UX v2 (user finding): a chat-side mutation ("Delete Group 20") left the
 * console pane stale until a manual 새로고침. REQ-DASHUI-021 forbids
 * TIMER-driven polling, not event-driven refresh — so a `chat_response`
 * whose command list contains at least one actually-EXECUTED command
 * (`executed_ok`) triggers exactly one `dash_catalog_request`. Blocked /
 * proposal-only / command-less responses trigger nothing: nothing on the
 * console changed.
 */
export function dashResyncFrame(raw: string): string | null {
  const event = parseServerEvent(raw);
  if (event === null || event.type !== "chat_response") return null;
  const executed = event.commands.some((command) => command.status === "executed_ok");
  return executed ? buildDashCatalogRequest() : null;
}

export interface CopilotSocket {
  state: UiState;
  connected: boolean;
  sendChat: (text: string) => void;
  sendDecision: (requestId: string, approved: boolean) => void;
  sendReviewDecision: (requestId: string, approved: boolean) => void;
  sendLock: (active: boolean) => void;
  sendPanelExecute: (targetKind: PanelTargetKind, target: number) => void;
  sendPanelStop: (targetKind: PanelTargetKind, target: number) => void;
  /** T-H5 — step to the previous cue (Go-). */
  sendPanelBack: (targetKind: PanelTargetKind, target: number) => void;
  /** T-H5 — jump to a specific cue (Goto). */
  sendPanelGoto: (targetKind: PanelTargetKind, target: number, cue: number) => void;
  sendDashRefresh: () => void;
  sendCueMonitorRefresh: () => void;
}

export function useCopilotSocket(url?: string): CopilotSocket {
  const [state, dispatch] = useReducer(reducer, initialState);
  const [connected, setConnected] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let disposed = false;
    let retryDelay = 500;
    let timer: number | undefined;

    const connect = () => {
      const target = url ?? defaultUrl();
      const protocols = connectProtocols(launchToken());
      const socket = protocols ? new WebSocket(target, protocols) : new WebSocket(target);
      socketRef.current = socket;
      socket.onopen = () => {
        retryDelay = 500;
        setConnected(true);
        // AC-DASHUI-017: every (re)connect re-requests both catalogs + status
        // rather than trusting pre-disconnect state, which `dispatch({ kind:
        // "disconnected" })` has already marked stale/cleared on the prior close.
        connectResyncFrames().forEach((frame) => socket.send(frame));
      };
      socket.onmessage = (message) => {
        const raw = String(message.data);
        dispatch({ kind: "server", raw });
        // Event-driven console-pane resync after an executed chat command
        // (see dashResyncFrame) — never timer-driven (REQ-DASHUI-021).
        const resync = dashResyncFrame(raw);
        if (resync !== null && socket.readyState === WebSocket.OPEN) {
          socket.send(resync);
        }
      };
      socket.onclose = () => {
        setConnected(false);
        // The server fail-safe-denies every pending approval/review for
        // this session on disconnect (M6c-1) — clear the stale cards so a
        // reconnect never leaves the operator staring at a decision the
        // server already resolved (M6c-4 finding 3).
        dispatch({ kind: "disconnected" });
        if (!disposed) {
          timer = window.setTimeout(connect, retryDelay);
          retryDelay = Math.min(retryDelay * 2, 10_000);
        }
      };
    };

    connect();
    return () => {
      disposed = true;
      if (timer !== undefined) window.clearTimeout(timer);
      socketRef.current?.close();
    };
  }, [url]);

  // Cue-monitor poll (contracted, unlike dash_catalog — see
  // CUE_MONITOR_POLL_INTERVAL_MS). Only sends while the socket is actually
  // open; a tick during a reconnect backoff is silently skipped rather than
  // queued, since the next successful connect's resync frame already covers it.
  useEffect(() => {
    const poll = window.setInterval(() => {
      const socket = socketRef.current;
      if (socket !== null && socket.readyState === WebSocket.OPEN) {
        socket.send(buildCueMonitorRequest());
      }
    }, CUE_MONITOR_POLL_INTERVAL_MS);
    return () => window.clearInterval(poll);
  }, []);

  const send = useCallback((frame: string) => {
    const socket = socketRef.current;
    if (socket !== null && socket.readyState === WebSocket.OPEN) socket.send(frame);
  }, []);

  const sendChat = useCallback(
    (text: string) => {
      dispatch({ kind: "user", text });
      send(buildChat(text));
    },
    [send],
  );
  const sendDecision = useCallback(
    (requestId: string, approved: boolean) => send(buildApprovalDecision(requestId, approved)),
    [send],
  );
  const sendReviewDecision = useCallback(
    (requestId: string, approved: boolean) => send(buildReviewDecision(requestId, approved)),
    [send],
  );
  const sendLock = useCallback((active: boolean) => send(buildLock(active)), [send]);
  const sendPanelExecute = useCallback(
    (targetKind: PanelTargetKind, target: number) => send(buildPanelExecute(targetKind, target)),
    [send],
  );
  const sendPanelStop = useCallback(
    (targetKind: PanelTargetKind, target: number) => send(buildPanelStop(targetKind, target)),
    [send],
  );
  const sendPanelBack = useCallback(
    (targetKind: PanelTargetKind, target: number) => send(buildPanelBack(targetKind, target)),
    [send],
  );
  const sendPanelGoto = useCallback(
    (targetKind: PanelTargetKind, target: number, cue: number) =>
      send(buildPanelGoto(targetKind, target, cue)),
    [send],
  );
  const sendDashRefresh = useCallback(() => send(buildDashCatalogRequest()), [send]);
  const sendCueMonitorRefresh = useCallback(() => send(buildCueMonitorRequest()), [send]);

  return {
    state,
    connected,
    sendChat,
    sendDecision,
    sendReviewDecision,
    sendLock,
    sendPanelExecute,
    sendPanelStop,
    sendPanelBack,
    sendPanelGoto,
    sendDashRefresh,
    sendCueMonitorRefresh,
  };
}
