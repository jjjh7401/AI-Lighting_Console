import { describe, expect, it } from "vitest";

import { statusDetails } from "./StatusBanner";

describe("statusDetails", () => {
  it("shows a server reconnect detail while disconnected", () => {
    expect(statusDetails(null, false)).toEqual([
      { label: "서버", value: "재연결 중", tone: "bad" },
    ]);
  });

  it("shows an explicit gate-pending row before the first status event", () => {
    expect(statusDetails(null, true)).toEqual([
      { label: "서버", value: "연결됨", tone: "ok" },
      { label: "게이트", value: "상태 확인 중", tone: "muted" },
    ]);
  });

  it("surfaces console, OSC input, execution, and live-lock state for operators", () => {
    const details = statusDetails(
      {
        health: "console_offline",
        live_lock: true,
        executions_blocked: true,
        console_input: "listening",
      },
      true,
    );

    expect(details).toContainEqual({
      label: "콘솔",
      value: "콘솔 오프라인 — 신규 실행 차단",
      tone: "bad",
    });
    expect(details).toContainEqual({ label: "OSC 입력", value: "입력 포트 열림", tone: "ok" });
    expect(details).toContainEqual({ label: "실행", value: "차단", tone: "bad" });
    expect(details).toContainEqual({ label: "라이브 잠금", value: "제안만", tone: "warn" });
  });

  it("names a reply-port mismatch only when both observed numbers are present", () => {
    const details = statusDetails(
      {
        health: "console_offline",
        live_lock: false,
        executions_blocked: true,
        console_input: "listening",
        reply_port: 9002,
        receive_port: 9001,
      },
      true,
    );

    expect(details).toContainEqual({
      label: "응답 포트",
      value: "9002 → 9001 불일치",
      tone: "warn",
    });
  });
});
