// WebSocket hook — owns the connection, folds server events into UI state.
import { useCallback, useEffect, useReducer, useRef, useState } from "react";

import {
  addUserMessage,
  buildApprovalDecision,
  buildChat,
  buildLock,
  initialState,
  parseServerEvent,
  reduceServerEvent,
  type UiState,
} from "./protocol";

type Action = { kind: "server"; raw: string } | { kind: "user"; text: string };

function reducer(state: UiState, action: Action): UiState {
  if (action.kind === "user") return addUserMessage(state, action.text);
  const event = parseServerEvent(action.raw);
  return event === null ? state : reduceServerEvent(state, event);
}

function defaultUrl(): string {
  const scheme = window.location.protocol === "https:" ? "wss" : "ws";
  return `${scheme}://${window.location.host}/ws`;
}

export interface CopilotSocket {
  state: UiState;
  connected: boolean;
  sendChat: (text: string) => void;
  sendDecision: (requestId: string, approved: boolean) => void;
  sendLock: (active: boolean) => void;
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
      const socket = new WebSocket(url ?? defaultUrl());
      socketRef.current = socket;
      socket.onopen = () => {
        retryDelay = 500;
        setConnected(true);
      };
      socket.onmessage = (message) => dispatch({ kind: "server", raw: String(message.data) });
      socket.onclose = () => {
        setConnected(false);
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
  const sendLock = useCallback((active: boolean) => send(buildLock(active)), [send]);

  return { state, connected, sendChat, sendDecision, sendLock };
}
