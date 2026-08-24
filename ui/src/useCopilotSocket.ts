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
  buildQuestionAnswer,
  buildReviewDecision,
  buildStatusRequest,
  buildVectorworksExportUpload,
  buildLayoutImageUpload,
  buildHistoryRestore,
  CHAT_STORAGE_KEY,
  clearPendingRequests,
  initialState,
  parseServerEvent,
  parseStoredEntries,
  reduceServerEvent,
  serializeEntriesForStorage,
  type PanelTargetKind,
  type UiState,
} from "./protocol";

export type Action =
  | { kind: "server"; raw: string }
  | { kind: "user"; text: string }
  | { kind: "disconnected" }
  | { kind: "clear_chat" };

// Exported for direct unit testing (see useCopilotSocket.test.ts): the hook
// itself needs a DOM/renderer this project's test setup doesn't provide, but
// the state transition is a pure function like the rest of protocol.ts.
export function reducer(state: UiState, action: Action): UiState {
  if (action.kind === "user") return addUserMessage(state, action.text);
  if (action.kind === "disconnected") return clearPendingRequests(state);
  if (action.kind === "clear_chat") return { ...state, entries: [] };
  const event = parseServerEvent(action.raw);
  return event === null ? state : reduceServerEvent(state, event);
}

/** Restore the persisted transcript at mount so a refresh keeps the visible
 *  conversation; storage failures degrade to a clean start, never a crash. */
export function restoredInitialState(): UiState {
  if (typeof window === "undefined") return initialState;
  try {
    return {
      ...initialState,
      entries: parseStoredEntries(window.localStorage.getItem(CHAT_STORAGE_KEY)),
    };
  } catch {
    return initialState;
  }
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
 * 조작자가 콘솔 앞에서 무언가를 하기를 기다리는 중인가.
 *
 * [round24 후속] 폴링은 콘솔의 Command Line History에 왕복마다 두 줄을 남긴다.
 * 카드가 "콘솔 명령줄에서 이것을 실행하라"고 청해 놓고 그 이력을 초당 수십 줄로
 * 밀어내면, 조작자는 자기가 친 명령조차 확인할 수 없다 — 실측에서 실제로 그랬다.
 */
export function awaitingOperatorAction(state: UiState): boolean {
  return state.pendingQuestions.length > 0;
}

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

/**
 * The cue-monitor refresh earned by a completed executor playback request.
 *
 * `panel_item_state` is emitted only after the server has finished the gate /
 * console-result path for the press. The monitor otherwise polls at 5 seconds,
 * which left the highlighted cue visibly stale after Go+ / Go- even when the
 * console had already advanced. Restrict this to executor state events:
 * macro state has no cue to read, and catalog/state-query events must never
 * cause a refresh loop.
 *
 * An execution that the console refuses may also emit a state event. Refreshing
 * then is deliberate: it replaces any old cue claim with a fresh console read,
 * rather than optimistically moving the highlight client-side.
 */
export function cueMonitorResyncFrame(raw: string): string | null {
  const event = parseServerEvent(raw);
  return event?.type === "panel_item_state" && event.target_kind === "executor"
    ? buildCueMonitorRequest()
    : null;
}

export interface CopilotSocket {
  state: UiState;
  connected: boolean;
  /** True from an accepted chat frame until its terminal response/error arrives. */
  responding: boolean;
  sendChat: (text: string) => void;
  sendDecision: (requestId: string, approved: boolean) => void;
  sendReviewDecision: (requestId: string, approved: boolean) => void;
  sendQuestionAnswer: (requestId: string, answer: string) => void;
  sendVectorworksExportUpload: (fileName: string, contentBase64: string) => boolean;
  /** SPEC-COPILOT-IMGLAYOUT-001 M1 — attach a design/reference image. */
  sendLayoutImageUpload: (fileName: string, mimeType: string, contentBase64: string) => boolean;
  sendLock: (active: boolean) => void;
  sendPanelExecute: (targetKind: PanelTargetKind, target: number) => void;
  sendPanelStop: (targetKind: PanelTargetKind, target: number) => void;
  /** T-H5 — step to the previous cue (Go-). */
  sendPanelBack: (targetKind: PanelTargetKind, target: number) => void;
  /** T-H5 — jump to a specific cue (Goto). */
  sendPanelGoto: (targetKind: PanelTargetKind, target: number, cue: number) => void;
  sendDashRefresh: () => void;
  sendCueMonitorRefresh: () => void;
  /** Clear the persisted transcript (the top-right 대화 지우기 button). */
  clearChat: () => void;
  /** Apply a library-loaded timeline as if a `song_timeline` frame arrived. */
  applySongTimeline: (timeline: unknown) => void;
}
export function useCopilotSocket(url?: string): CopilotSocket {
  const [state, dispatch] = useReducer(reducer, initialState, restoredInitialState);
  const [connected, setConnected] = useState(false);
  const [responding, setResponding] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);
  // Fresh transcript for the (re)connect handler below — the connect effect
  // closes over [url] only, so it reads the entries through this ref.
  const entriesRef = useRef(state.entries);
  entriesRef.current = state.entries;

  // Best-effort persistence: quota/denied storage must never break the chat.
  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      window.localStorage.setItem(CHAT_STORAGE_KEY, serializeEntriesForStorage(state.entries));
    } catch {
      /* persistence is best effort */
    }
  }, [state.entries]);

  useEffect(() => {
    let disposed = false;
    let retryDelay = 500;
    let timer: number | undefined;
    let ownedSocket: WebSocket | null = null;
    const connect = () => {
      const target = url ?? defaultUrl();
      const protocols = connectProtocols(launchToken());
      const socket = protocols ? new WebSocket(target, protocols) : new WebSocket(target);
      ownedSocket = socket;
      socketRef.current = socket;
      socket.onopen = () => {
        if (disposed || socketRef.current !== socket) {
          socket.close();
          return;
        }
        retryDelay = 500;
        setConnected(true);
        // AC-DASHUI-017: every (re)connect re-requests both catalogs + status
        // rather than trusting pre-disconnect state, which `dispatch({ kind:
        // "disconnected" })` has already marked stale/cleared on the prior close.
        connectResyncFrames().forEach((frame) => socket.send(frame));
        // Refresh survival, model half: the server session is NEW on every
        // connection, so reinject the restored transcript to seed its rolling
        // memory. The server seeds an EMPTY session only, making this
        // idempotent across reconnects mid-conversation.
        const restore = buildHistoryRestore(entriesRef.current);
        if (restore !== null) socket.send(restore);
      };
      socket.onmessage = (message) => {
        if (socketRef.current !== socket) return;
        const raw = String(message.data);
        const event = parseServerEvent(raw);
        if (event?.type === "chat_response" || event?.type === "error") setResponding(false);
        dispatch({ kind: "server", raw });
        // A chat mutation refreshes the catalog; a completed executor press
        // refreshes the separate current-cue snapshot immediately. Both are
        // event-driven, never additional timers.
        const resync = dashResyncFrame(raw) ?? cueMonitorResyncFrame(raw);
        if (resync !== null && socket.readyState === WebSocket.OPEN) {
          socket.send(resync);
        }
      };
      socket.onclose = () => {
        // An older connection can close after its replacement opened. It must
        // never clear the replacement's connected state or overwrite
        // socketRef with a retrying rejected connection.
        if (socketRef.current !== socket) return;
        socketRef.current = null;
        setResponding(false);
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
      ownedSocket?.close();
    };
  }, [url]);

  // Cue-monitor poll (contracted, unlike dash_catalog — see
  // CUE_MONITOR_POLL_INTERVAL_MS). Only sends while the socket is actually
  // open; a tick during a reconnect backoff is silently skipped rather than
  // queued, since the next successful connect's resync frame already covers it.
  //
  // [round24 후속] **물음이 떠 있는 동안은 멈춘다.** 이 폴링은 콘솔의 Command Line
  // History에 왕복마다 두 줄을 남긴다. 조작자가 카드의 지시대로 콘솔 명령줄에서
  // 무언가를 실행해야 하는 그 순간에, 앱이 초당 수십 줄로 이력을 밀어내면 자기가
  // 친 명령이 화면 밖으로 사라진다 — 실측에서 그 때문에 실행 여부조차 확인할 수
  // 없었다. 기다리는 동안 리그 상태가 굳는 대가는 작고, 답이 오면 곧 재개된다.
  const awaitingOperator = awaitingOperatorAction(state);
  useEffect(() => {
    if (awaitingOperator) return;
    const poll = window.setInterval(() => {
      const socket = socketRef.current;
      if (socket !== null && socket.readyState === WebSocket.OPEN) {
        socket.send(buildCueMonitorRequest());
      }
    }, CUE_MONITOR_POLL_INTERVAL_MS);
    return () => window.clearInterval(poll);
  }, [awaitingOperator]);

  const send = useCallback((frame: string) => {
    const socket = socketRef.current;
    if (socket !== null && socket.readyState === WebSocket.OPEN) socket.send(frame);
  }, []);

  const sendChat = useCallback((text: string) => {
    const socket = socketRef.current;
    if (socket === null || socket.readyState !== WebSocket.OPEN) return;
    dispatch({ kind: "user", text });
    setResponding(true);
    socket.send(buildChat(text));
  }, []);
  const sendVectorworksExportUpload = useCallback(
    (fileName: string, contentBase64: string) => {
      const socket = socketRef.current;
      if (socket === null || socket.readyState !== WebSocket.OPEN) return false;
      dispatch({ kind: "user", text: `파일 업로드: ${fileName}` });
      socket.send(buildVectorworksExportUpload(fileName, contentBase64));
      return true;
    },
    [],
  );
  const sendLayoutImageUpload = useCallback(
    (fileName: string, mimeType: string, contentBase64: string) => {
      const socket = socketRef.current;
      if (socket === null || socket.readyState !== WebSocket.OPEN) return false;
      dispatch({ kind: "user", text: `이미지 첨부: ${fileName}` });
      socket.send(buildLayoutImageUpload(fileName, mimeType, contentBase64));
      return true;
    },
    [],
  );
  const sendDecision = useCallback(
    (requestId: string, approved: boolean) => send(buildApprovalDecision(requestId, approved)),
    [send],
  );
  const sendReviewDecision = useCallback(
    (requestId: string, approved: boolean) => send(buildReviewDecision(requestId, approved)),
    [send],
  );
  const sendQuestionAnswer = useCallback(
    (requestId: string, answer: string) => send(buildQuestionAnswer(requestId, answer)),
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
  const clearChat = useCallback(() => dispatch({ kind: "clear_chat" }), []);
  /** Apply a library-loaded timeline locally, riding the SAME parse/reduce
   * path as a server `song_timeline` frame (the server store was already
   * updated by the load call, so replays stay consistent). */
  const applySongTimeline = useCallback((timeline: unknown) => {
    dispatch({
      kind: "server",
      raw: JSON.stringify({ v: 1, type: "song_timeline", timeline }),
    });
  }, []);

  return {
    state,
    connected,
    responding,
    sendChat,
    sendVectorworksExportUpload,
    sendLayoutImageUpload,
    sendDecision,
    sendReviewDecision,
    sendQuestionAnswer,
    sendLock,
    sendPanelExecute,
    sendPanelStop,
    sendPanelBack,
    sendPanelGoto,
    sendDashRefresh,
    sendCueMonitorRefresh,
    clearChat,
    applySongTimeline,
  };
}
