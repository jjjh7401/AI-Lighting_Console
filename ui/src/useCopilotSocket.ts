// WebSocket hook — owns the connection, folds server events into UI state.
import { useCallback, useEffect, useReducer, useRef, useState } from "react";

import { backendBase } from "./launchContext";
import {
  addUserMessage,
  buildApprovalDecision,
  buildChat,
  buildLock,
  buildPanelCatalogRequest,
  buildPanelPin,
  buildReviewDecision,
  buildStatusRequest,
  clearOnDisconnect,
  initialState,
  parseServerEvent,
  reduceServerEvent,
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
  if (action.kind === "disconnected") return clearOnDisconnect(state);
  const event = parseServerEvent(action.raw);
  return event === null ? state : reduceServerEvent(state, event);
}

/**
 * What a freshly-opened socket asks the server for (REQ-SHOWUI-015/016).
 *
 * The disconnect above erased the panel's running state because the app stopped
 * being able to observe the console. Coming back, it rebuilds that picture from
 * the SERVER's answer and from nothing else — no cache, no client-side
 * reconstruction, no assumption that what was playing still is.
 *
 * Both frames are read-side requests. Nothing here re-sends a command: a
 * reconnect must never replay an execution nobody confirmed (REQ-MVP-032,
 * inherited unchanged), so the recovery path is deliberately incapable of
 * emitting one.
 *
 * The server also pushes a status snapshot on accept (server/web/app.py), which
 * makes the status request belt-and-braces rather than the only source — the UI
 * asks for what it needs instead of depending on a server behaviour it cannot
 * verify from here.
 */
export function resyncFrames(): string[] {
  return [buildPanelCatalogRequest(), buildStatusRequest()];
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

export interface CopilotSocket {
  state: UiState;
  connected: boolean;
  sendChat: (text: string) => void;
  sendDecision: (requestId: string, approved: boolean) => void;
  sendReviewDecision: (requestId: string, approved: boolean) => void;
  sendLock: (active: boolean) => void;
  // -- show-control panel (SHOWUI M4) -----------------------------------------
  //
  // Tile presses and the All Off bundle arrive here as frames already built by
  // protocol.ts builders (`tilePressFrame`, `allOffFrames`, `buildPanelUnpin`),
  // because WHICH frames a press produces is the safety-critical decision and
  // it belongs in a pure, tested function rather than in this hook. The two
  // payload-free messages get named helpers since there is nothing to compose.
  sendPanelFrame: (frame: string) => void;
  sendPanelFrames: (frames: string[]) => void;
  sendPanelPin: () => void;
  sendPanelCatalogRequest: () => void;
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
        // Resynchronise on EVERY open, not only on a reconnect: the first
        // connect needs the same picture, and a path that runs once per session
        // is a path whose reconnect behaviour nobody exercises.
        for (const frame of resyncFrames()) socket.send(frame);
      };
      socket.onmessage = (message) => dispatch({ kind: "server", raw: String(message.data) });
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

  const sendPanelFrame = useCallback((frame: string) => send(frame), [send]);
  const sendPanelFrames = useCallback(
    // Sequential, in bundle order. The server's stop lane serialises them
    // anyway (M3), and preserving order keeps the audit log readable.
    (frames: string[]) => frames.forEach(send),
    [send],
  );
  const sendPanelPin = useCallback(() => send(buildPanelPin()), [send]);
  const sendPanelCatalogRequest = useCallback(() => send(buildPanelCatalogRequest()), [send]);

  return {
    state,
    connected,
    sendChat,
    sendDecision,
    sendReviewDecision,
    sendLock,
    sendPanelFrame,
    sendPanelFrames,
    sendPanelPin,
    sendPanelCatalogRequest,
  };
}
