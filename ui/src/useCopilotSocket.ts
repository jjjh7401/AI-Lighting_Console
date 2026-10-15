// WebSocket hook — owns the connection, folds server events into UI state.
import { useCallback, useEffect, useReducer, useRef, useState } from "react";

import { backendBase } from "./launchContext";
import {
  addUserMessage,
  buildApprovalDecision,
  buildBarMapAnalyse,
  buildBeatGridApply,
  buildBeatGridDrawerRequest,
  buildBeatGridStageRequest,
  buildBeatGridEdit,
  buildBeatGridEditSentence,
  buildBeatGridNewPreset,
  buildBeatGridPreview,
  buildBeatGridPreviewOff,
  buildBeatGridConsolePlay,
  buildBeatGridConsoleStop,
  buildBeatGridSuggest,
  buildBeatGridSuggestionApply,
  buildBeatGridSuggestionReject,
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
  buildTimelineDraftRedo,
  buildTimelineDraftUndo,
  buildVectorworksExportUpload,
  buildLayoutImageUpload,
  buildSongAudioAnalyse,
  buildSongAudioLinkRequest,
  buildSongAudioUploadBegin,
  buildSongAudioUploadChunk,
  buildSongAudioUploadEnd,
  buildHistoryRestore,
  CHAT_STORAGE_KEY,
  clearOnDisconnect,
  initialState,
  parseServerEvent,
  parseStoredEntries,
  reduceServerEvent,
  serializeEntriesForStorage,
  type PanelTargetKind,
  type ServerEvent,
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
  if (action.kind === "disconnected") return clearOnDisconnect(state);
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

/**
 * 카드 t648(SPEC-LDBARMAP-003) — 훅의 소비자가 받는 알림. 둘 다 선택이다.
 *
 * 훅이 상태를 접는 일(`state`)과 별개로, 소비자가 자기 상태(마디 지도 진입 컨트롤의
 * 리듀서)에 같은 사건을 먹일 수 있게 한다. 훅은 이 콜백을 최신 것으로 읽으므로
 * 호출부가 렌더마다 새 객체를 넘겨도 소켓은 다시 연결되지 않는다.
 */
export interface CopilotSocketOptions {
  /** 서버 프레임 하나가 이벤트로 파싱될 때마다 부른다. 파싱되지 않은 프레임은 부르지 않는다. */
  onServerEvent?: (event: ServerEvent) => void;
  /** 현재 연결이 닫힐 때 부른다. 재연결 시도가 실패해 닫힐 때도 부른다. */
  onSocketClosed?: () => void;
}

export interface CopilotSocket {
  state: UiState;
  connected: boolean;
  /** True from an accepted chat frame until its terminal response/error arrives. */
  responding: boolean;
  sendChat: (text: string, selectedCue?: number | null) => void;
  sendTimelineDraftUndo: () => void;
  sendTimelineDraftRedo: () => void;
  /** 카드 t551(SPEC-LDBEAT-001 M3) — 편집 경로 ①(직접 고르기). */
  sendBeatGridEdit: (bar: number, target: string, changes: Record<string, unknown>) => void;
  /** 카드 t551(M3) — 편집 경로 ②(문장). */
  sendBeatGridEditSentence: (sentence: string) => void;
  /** 카드 t551(M3) — 편집 경로 ③(AI 제안) 1단계. */
  sendBeatGridSuggest: (bar: number, target: string) => void;
  /** 카드 t551 후속(지시 1항) — mockup aOk/aNo. */
  sendBeatGridSuggestionApply: (suggestionId: string) => void;
  sendBeatGridSuggestionReject: (suggestionId: string) => void;
  /** 카드 t551 후속(지시 1항) — mockup #bLib(프리셋 서랍). */
  sendBeatGridDrawerRequest: () => void;
  /** 카드 t589(REQ-LDBEAT-015(h)) — "+ 새 프리셋 만들기" 다이얼로그.
   * 카드 t599(REQ-LDBEAT-015(i-3)) — "position" 필드만 `aim`을 싣는다.
   * 카드 t603 — "effect" 필드만 효과 레시피 `fx`를 싣는다.
   * 카드 t594(REQ-LDBEAT-015(i-5)) — "color" 필드만 목표 RGB `rgb`를 싣는다. */
  sendBeatGridNewPreset: (
    bar: number,
    target: string,
    field: "dimmer_preset" | "dimmer_effect" | "position" | "color" | "effect",
    label: string,
    description: string,
    aim?: { x: number; y: number; z: number },
    fx?: { fx_id: string; period_unit: "beat" | "bar"; period_value: number },
    rgb?: { r: number; g: number; b: number },
  ) => void;
  /** 카드 t563 — 상단 바 「⇪ 콘솔에 반영」. */
  sendBeatGridApply: () => void;
  /** 카드 t563 — 상단 바 「▶ 이 마디 콘솔에서 보기」. */
  sendBeatGridPreview: (bar: number) => void;
  /** 카드 t563 — 상단 바 「■ 끄기」. */
  sendBeatGridPreviewOff: () => void;
  /** 카드 t578 — 「콘솔 같이」 타임코드 재생·정지. */
  sendBeatGridConsolePlay: () => void;
  sendBeatGridConsoleStop: () => void;
  /** 카드 t565 — 2D 무대 판독 요청(콘솔 읽기만). */
  sendBeatGridStageRequest: () => void;
  /** 카드 t571(REQ-LDBEAT-024(c) 후속) — 지금 곡에 저장된 오디오 링크
   * 요청(디스크 읽기만). */
  sendSongAudioLinkRequest: () => void;
  sendDecision: (requestId: string, approved: boolean) => void;
  sendReviewDecision: (requestId: string, approved: boolean) => void;
  sendQuestionAnswer: (requestId: string, answer: string) => void;
  sendVectorworksExportUpload: (fileName: string, contentBase64: string) => boolean;
  /** SPEC-COPILOT-IMGLAYOUT-001 M1 — attach a design/reference image. */
  sendLayoutImageUpload: (fileName: string, mimeType: string, contentBase64: string) => boolean;
  /** REQ-MUSICSYNC-027 — 곡은 조각(base64 문자열 배열)으로 보낸다. */
  sendSongAudioUpload: (
    fileName: string,
    mimeType: string,
    totalBytes: number,
    chunks: string[],
  ) => boolean;
  /** M2 후속 — 담아 둔 곡을 재라고 부른다. 답은 확인 카드로 돌아온다. */
  sendSongAudioAnalyse: () => void;
  /** 카드 t648(SPEC-LDBARMAP-003) — 마디 지도 분석 요청. 연결이 열려 있어 보냈으면 `true`,
   * 열려 있지 않으면 프레임도 화면 기록도 남기지 않고 `false`. `songName` 은 이 훅이 쓰지
   * 않는다(호출부가 `sent` 사건에 직접 싣는다) — 계획의 시그니처를 그대로 둔 것이다. */
  sendBarMapAnalyse: (offset: number, songName: string | null) => boolean;
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
export function useCopilotSocket(url?: string, options?: CopilotSocketOptions): CopilotSocket {
  const [state, dispatch] = useReducer(reducer, initialState, restoredInitialState);
  const [connected, setConnected] = useState(false);
  const [responding, setResponding] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);
  // Fresh transcript for the (re)connect handler below — the connect effect
  // closes over [url] only, so it reads the entries through this ref.
  const entriesRef = useRef(state.entries);
  entriesRef.current = state.entries;
  // 소비자 알림(`options`)도 같은 이유로 ref 로 읽는다. 연결 효과는 [url] 만 닫고 있어서,
  // 렌더마다 새로 만들어지는 콜백을 직접 닫으면 첫 렌더의 콜백만 계속 불린다.
  const optionsRef = useRef(options);
  optionsRef.current = options;

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
        // 소비자에게는 맨 끝에서 알린다. 위의 갱신(답 상태, 재동기 프레임)이 다 끝난 뒤에
        // 불러서, 소비자 콜백의 예외가 이 훅의 기존 동작을 막지 못하게 한다.
        if (event !== null) optionsRef.current?.onServerEvent?.(event);
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
        // 재연결 예약까지 마친 뒤에 알린다. 소비자 콜백이 던져도 재연결은 이미 걸려 있다.
        optionsRef.current?.onSocketClosed?.();
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

  // t281 — 선택된 큐를 요청에 실어 보낸다. 생략하면 프레임에 필드가 없다.
  const sendChat = useCallback((text: string, selectedCue?: number | null) => {
    const socket = socketRef.current;
    if (socket === null || socket.readyState !== WebSocket.OPEN) return;
    dispatch({ kind: "user", text });
    setResponding(true);
    socket.send(buildChat(text, selectedCue));
  }, []);
  /** t281 — 큐시트 초안 되돌리기/다시하기. 콘솔·라이브러리와 무관하다. */
  const sendTimelineDraftUndo = useCallback(() => send(buildTimelineDraftUndo()), [send]);
  const sendTimelineDraftRedo = useCallback(() => send(buildTimelineDraftRedo()), [send]);
  // 카드 t551(SPEC-LDBEAT-001 M3) — 편집 세 길. 직접 고르기(changes)/문장
  // (sentence) 모두 콘솔 무접촉 전용 메시지 타입(`beat_grid_edit`)으로
  // 올라간다 — 채팅(`sendChat`)과는 분리된 채널이다(AC-LDBEAT-005).
  const sendBeatGridEdit = useCallback(
    (bar: number, target: string, changes: Record<string, unknown>) =>
      send(buildBeatGridEdit(bar, target, changes)),
    [send],
  );
  const sendBeatGridEditSentence = useCallback(
    (sentence: string) => send(buildBeatGridEditSentence(sentence)),
    [send],
  );
  const sendBeatGridSuggest = useCallback(
    (bar: number, target: string) => send(buildBeatGridSuggest(bar, target)),
    [send],
  );
  // 카드 t551 후속(지시 1항) — mockup aOk/aNo 핸들러.
  const sendBeatGridSuggestionApply = useCallback(
    (suggestionId: string) => send(buildBeatGridSuggestionApply(suggestionId)),
    [send],
  );
  const sendBeatGridSuggestionReject = useCallback(
    (suggestionId: string) => send(buildBeatGridSuggestionReject(suggestionId)),
    [send],
  );
  // 카드 t565 — 2D 무대 판독(좌표 + 그룹 소속).
  const sendBeatGridStageRequest = useCallback(() => send(buildBeatGridStageRequest()), [send]);
  // 카드 t571(REQ-LDBEAT-024(c) 후속) — 저장된 오디오 링크 조회.
  const sendSongAudioLinkRequest = useCallback(
    () => send(buildSongAudioLinkRequest()),
    [send],
  );
  // 카드 t551 후속(지시 1항) — mockup #bLib(프리셋 서랍 열기).
  const sendBeatGridDrawerRequest = useCallback(
    () => send(buildBeatGridDrawerRequest()),
    [send],
  );
  // 카드 t589(REQ-LDBEAT-015(h)) — "+ 새 프리셋 만들기" 다이얼로그.
  // 카드 t599(REQ-LDBEAT-015(i-3)) — "position"만 `aim`을 함께 싣는다.
  // 카드 t603 — "effect"만 효과 레시피 `fx`를 함께 싣는다.
  // 카드 t594(REQ-LDBEAT-015(i-5)) — "color"만 목표 RGB `rgb`를 함께 싣는다.
  const sendBeatGridNewPreset = useCallback(
    (
      bar: number,
      target: string,
      field: "dimmer_preset" | "dimmer_effect" | "position" | "color" | "effect",
      label: string,
      description: string,
      aim?: { x: number; y: number; z: number },
      fx?: { fx_id: string; period_unit: "beat" | "bar"; period_value: number },
      rgb?: { r: number; g: number; b: number },
    ) => send(buildBeatGridNewPreset(bar, target, field, label, description, aim, fx, rgb)),
    [send],
  );
  // 카드 t563 — 상단 바 콘솔 버튼 셋. 콘솔에 **쓰는** 경로라
  // `beat_grid_edit` 류(콘솔 무접촉)와는 분리된 메시지 타입이다.
  const sendBeatGridApply = useCallback(() => send(buildBeatGridApply()), [send]);
  const sendBeatGridPreview = useCallback(
    (bar: number) => send(buildBeatGridPreview(bar)),
    [send],
  );
  const sendBeatGridPreviewOff = useCallback(() => send(buildBeatGridPreviewOff()), [send]);
  const sendBeatGridConsolePlay = useCallback(() => send(buildBeatGridConsolePlay()), [send]);
  const sendBeatGridConsoleStop = useCallback(() => send(buildBeatGridConsoleStop()), [send]);
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
  const sendSongAudioUpload = useCallback(
    (fileName: string, mimeType: string, totalBytes: number, chunks: string[]) => {
      const socket = socketRef.current;
      if (socket === null || socket.readyState !== WebSocket.OPEN) return false;
      dispatch({ kind: "user", text: `곡 첨부: ${fileName}` });
      socket.send(buildSongAudioUploadBegin(fileName, mimeType, totalBytes, chunks.length));
      chunks.forEach((chunk, index) => socket.send(buildSongAudioUploadChunk(index, chunk)));
      socket.send(buildSongAudioUploadEnd());
      return true;
    },
    [],
  );
  // 업로드와 달리 화면 기록(``dispatch``)을 남긴다: 분석은 사람이 **누른**
  // 행동이고, 뒤이어 뜨는 확인 카드가 무엇 때문에 떴는지가 기록에 없으면
  // 카드가 맥락 없이 튀어나온 것처럼 읽힌다.
  const sendSongAudioAnalyse = useCallback(() => {
    dispatch({ kind: "user", text: "곡 분석 요청" });
    send(buildSongAudioAnalyse());
  }, [send]);
  // 카드 t648(SPEC-LDBARMAP-003) — 마디 지도 분석 요청. 위 `sendSongAudioAnalyse` 와 같은
  // 이유로 화면 기록을 남기되, 연결이 열려 있지 않으면 **아무것도 남기지 않고** `false`
  // 를 돌려준다(REQ-LDBARUI-004: 보내지 못한 요청은 대기도, 기록도 시작하지 않는다).
  // 호출부가 이 값으로 리듀서에 `sent` 와 `not-connected` 중 어느 쪽을 먹일지 가른다.
  // 둘째 인자 `songName` 은 훅이 쓰지 않아 `_` 로 받는다(호출부가 `sent` 사건에 싣는다).
  const sendBarMapAnalyse = useCallback((offset: number, _songName: string | null): boolean => {
    const socket = socketRef.current;
    if (socket === null || socket.readyState !== WebSocket.OPEN) return false;
    dispatch({ kind: "user", text: `마디 지도 분석 요청 (첫 박 오프셋 ${offset})` });
    socket.send(buildBarMapAnalyse(offset));
    return true;
  }, []);
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
    sendTimelineDraftUndo,
    sendTimelineDraftRedo,
    sendBeatGridEdit,
    sendBeatGridEditSentence,
    sendBeatGridSuggest,
    sendBeatGridSuggestionApply,
    sendBeatGridSuggestionReject,
    sendBeatGridDrawerRequest,
    sendBeatGridNewPreset,
    sendBeatGridApply,
    sendBeatGridPreview,
    sendBeatGridPreviewOff,
    sendBeatGridConsolePlay,
    sendBeatGridConsoleStop,
    sendBeatGridStageRequest,
    sendSongAudioLinkRequest,
    sendVectorworksExportUpload,
    sendLayoutImageUpload,
    sendSongAudioUpload,
    sendSongAudioAnalyse,
    sendBarMapAnalyse,
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
