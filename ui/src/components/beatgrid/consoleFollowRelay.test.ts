// 「콘솔 같이」 중계 순수 함수 시험 — 전체화면을 닫은 사이에 온 콘솔 재생 응답을 기록하는 규칙.
//
// 못박는 것: 기다리는 중일 때 **새 객체**의 콘솔 재생 응답만 이번 요청의 답으로 받아들이고(앞 응답·
// 다른 종류의 응답·응답 없음은 무시), 성공이면 받은 시각을 기록하고, 거절이면 이유만 남긴다.
// 음원 자리 계산은 부호와 값이 맞아야 한다(음수 = 아직 틀 때가 아니다).
import { describe, expect, it } from "vitest";

import type { BeatGridSendStatus } from "../../protocol";
import {
  CONSOLE_DELAY_MISSING_MESSAGE,
  CONSOLE_NO_SONG_AUDIO_MESSAGE,
  consoleAudioPositionSeconds,
  shouldStopConsoleAtSongEnd,
  createConsoleFollowRelay,
  observeConsoleFollowStatus,
  observeConsoleRunStatus,
} from "./consoleFollowRelay";
import { resolveConsolePlayResponse } from "./consoleSyncAudio";

/** 응답마다 새 객체 — 리듀서의 REPLACE 와 같다. */
function status(overrides: Partial<BeatGridSendStatus> = {}): BeatGridSendStatus {
  return {
    pending_apply_count: 0,
    last_action: "console_play",
    ok: true,
    reason: null,
    blocked_cells: [],
    approval_vs_sent: null,
    ...overrides,
  };
}

describe("createConsoleFollowRelay — 처음 상태", () => {
  it("전부 꺼짐·비어 있음이다", () => {
    expect(createConsoleFollowRelay()).toEqual({
      consoleFollow: false,
      awaiting: false,
      pressedAgainst: null,
      responseAtMs: null,
      audioStarted: false,
      failure: null,
      consoleMayRun: false,
      runStatusSeen: null,
      awaitingBusyAt: 0,
      stopping: false,
      stopPressedAgainst: null,
      stopBusyAt: 0,
      playQueued: false,
      timecodePaused: false,
      startSeconds: 0,
    });
  });

  it("호출할 때마다 새 객체다(앱 둘이 한 객체를 나눠 쓰지 않는다)", () => {
    expect(createConsoleFollowRelay()).not.toBe(createConsoleFollowRelay());
  });
});

describe("observeConsoleFollowStatus — 이번 요청의 답인가", () => {
  it("기다리는 중이 아니면 어떤 응답도 받아들이지 않고 아무것도 바꾸지 않는다", () => {
    const relay = createConsoleFollowRelay();
    expect(observeConsoleFollowStatus(relay, status(), 1000)).toBe(false);
    expect(relay).toEqual(createConsoleFollowRelay());
  });

  it("응답이 없으면(null) 계속 기다린다", () => {
    const relay = { ...createConsoleFollowRelay(), awaiting: true };
    expect(observeConsoleFollowStatus(relay, null, 1000)).toBe(false);
    expect(relay.awaiting).toBe(true);
    expect(relay.responseAtMs).toBeNull();
  });

  it("▶ 를 누를 때 화면에 있던 바로 그 객체는 앞 응답이라 답이 아니다 — 계속 기다린다", () => {
    const old = status();
    const relay = { ...createConsoleFollowRelay(), awaiting: true, pressedAgainst: old };
    expect(observeConsoleFollowStatus(relay, old, 1000)).toBe(false);
    expect(relay.awaiting).toBe(true);
    expect(relay.responseAtMs).toBeNull();
  });

  it("콘솔 재생이 아닌 응답(반영·미리보기·정지)은 답이 아니다 — 계속 기다린다", () => {
    const relay = { ...createConsoleFollowRelay(), awaiting: true };
    for (const lastAction of ["apply", "preview", "preview_off", "edit", "console_stop"] as const) {
      expect(observeConsoleFollowStatus(relay, status({ last_action: lastAction }), 1000)).toBe(false);
    }
    expect(relay.awaiting).toBe(true);
    expect(relay.responseAtMs).toBeNull();
    expect(relay.failure).toBeNull();
  });

  it("누를 때 화면에 응답이 없었으면(null) 어떤 콘솔 재생 응답이든 답이다", () => {
    const relay = { ...createConsoleFollowRelay(), awaiting: true, pressedAgainst: null };
    expect(observeConsoleFollowStatus(relay, status(), 1000)).toBe(true);
  });

  it("서버가 콘솔이 돌기 시작한 시각을 실었으면 응답 도착 시각 대신 그 시각을 기록한다", () => {
    // 콘솔 응답이 1.75초 늦게 왔다 — 음원은 콘솔이 실제로 출발한 시각(4000)에 맞춰 잰다.
    const relay = { ...createConsoleFollowRelay(), awaiting: true, pressedAgainst: null };
    expect(observeConsoleFollowStatus(relay, status({ console_started_at_ms: 4000 }), 5750)).toBe(true);
    expect(relay.responseAtMs).toBe(4000);
  });

  it("성공 응답이면 기다림을 끝내고 받은 시각을 기록한다", () => {
    const old = status();
    const relay = { ...createConsoleFollowRelay(), awaiting: true, pressedAgainst: old };
    expect(observeConsoleFollowStatus(relay, status(), 123456)).toBe(true);
    expect(relay.awaiting).toBe(false);
    expect(relay.responseAtMs).toBe(123456);
    expect(relay.failure).toBeNull();
  });

  it("거절 응답이면 이유만 남기고 시각은 기록하지 않는다", () => {
    const relay = { ...createConsoleFollowRelay(), awaiting: true };
    expect(
      observeConsoleFollowStatus(relay, status({ ok: false, reason: "반영 기록 없음" }), 1000),
    ).toBe(true);
    expect(relay.awaiting).toBe(false);
    expect(relay.failure).toBe("반영 기록 없음");
    expect(relay.responseAtMs).toBeNull();
  });

  it("이유 없는 거절이면 기본 문구를 남긴다", () => {
    const relay = { ...createConsoleFollowRelay(), awaiting: true };
    expect(observeConsoleFollowStatus(relay, status({ ok: false, reason: null }), 1000)).toBe(true);
    expect(relay.failure).toBe("콘솔 타임코드 재생이 거절됐습니다.");
  });

  it("거절 뒤 다시 눌러 성공하면 앞의 거절 이유가 지워진다", () => {
    const relay = { ...createConsoleFollowRelay(), awaiting: true, failure: "반영 기록 없음" };
    expect(observeConsoleFollowStatus(relay, status(), 5000)).toBe(true);
    expect(relay.failure).toBeNull();
    expect(relay.responseAtMs).toBe(5000);
  });

  it("답을 받은 뒤 같은 응답이 다시 보여도 두 번째는 받아들이지 않는다", () => {
    const relay = { ...createConsoleFollowRelay(), awaiting: true };
    const answer = status();
    expect(observeConsoleFollowStatus(relay, answer, 1000)).toBe(true);
    expect(observeConsoleFollowStatus(relay, answer, 9000)).toBe(false);
    expect(relay.responseAtMs).toBe(1000);
  });
});

describe("observeConsoleRunStatus — 콘솔 타임코드가 돌고 있을 수 있는가(N11)", () => {
  it("재생 성공에서 켜지고 정지 성공에서만 꺼진다", () => {
    const relay = createConsoleFollowRelay();
    expect(observeConsoleRunStatus(relay, status())).toBe(true);
    expect(relay.consoleMayRun).toBe(true);
    expect(observeConsoleRunStatus(relay, status({ last_action: "console_stop" }))).toBe(true);
    expect(relay.consoleMayRun).toBe(false);
  });

  it("정지가 거절·만료되면 켜진 채로 둔다(앱은 멈춰도 콘솔은 돈다)", () => {
    const relay = createConsoleFollowRelay();
    observeConsoleRunStatus(relay, status());
    const rejected = status({ last_action: "console_stop", ok: false, reason: "승인 거절" });
    expect(observeConsoleRunStatus(relay, rejected)).toBe(false);
    expect(relay.consoleMayRun).toBe(true);
  });

  it("재생 거절은 켜지 않고, 같은 응답은 두 번 세지 않으며, 다른 종류 응답은 바꾸지 않는다", () => {
    const relay = createConsoleFollowRelay();
    expect(observeConsoleRunStatus(relay, status({ ok: false }))).toBe(false);
    const played = status();
    observeConsoleRunStatus(relay, played);
    relay.consoleMayRun = false; // 같은 객체가 다시 와도 다시 켜지지 않는다
    expect(observeConsoleRunStatus(relay, played)).toBe(false);
    relay.consoleMayRun = true;
    expect(observeConsoleRunStatus(relay, status({ last_action: "apply" }))).toBe(false);
    expect(observeConsoleRunStatus(relay, null)).toBe(false);
    expect(relay.consoleMayRun).toBe(true);
  });
});

describe("consoleAudioPositionSeconds — 지금 음원이 있어야 할 자리", () => {
  it("응답을 받은 직후엔 지연만큼 음수다(아직 틀 때가 아니다)", () => {
    expect(consoleAudioPositionSeconds(10_000, 3, 10_000)).toBe(-3);
    expect(consoleAudioPositionSeconds(10_000, 3, 11_000)).toBe(-2);
  });

  it("지연이 지난 순간엔 0 이다", () => {
    expect(consoleAudioPositionSeconds(10_000, 3, 13_000)).toBe(0);
  });

  it("지연이 지나면 지난 시간에서 지연을 뺀 자리다", () => {
    expect(consoleAudioPositionSeconds(10_000, 3, 22_000)).toBe(9);
    expect(consoleAudioPositionSeconds(10_000, 0, 10_500)).toBe(0.5);
  });

  it("소수 지연도 그대로 뺀다", () => {
    expect(consoleAudioPositionSeconds(0, 3.002, 12_002)).toBeCloseTo(9, 9);
  });
});

describe("안내 문구", () => {
  it("지연 측정값 없음 문구는 기존 응답 판정(`resolveConsolePlayResponse`)의 문구와 같다", () => {
    const decision = resolveConsolePlayResponse(
      true,
      { last_action: "console_play", ok: true, reason: null },
      null,
    );
    expect(decision).toEqual({ kind: "fail", reason: CONSOLE_DELAY_MISSING_MESSAGE });
  });

  it("음원이 없을 때 문구", () => {
    expect(CONSOLE_NO_SONG_AUDIO_MESSAGE).toBe("이 곡에 연결된 음원이 없어 콘솔 타임코드만 재생 중입니다.");
  });
});

describe("shouldStopConsoleAtSongEnd — 전체 실행 G-22", () => {
  it("곡 끝에서 「콘솔 같이」이고 콘솔이 돌 수 있을 때만 끈다", () => {
    const relay = createConsoleFollowRelay();
    expect(shouldStopConsoleAtSongEnd(relay)).toBe(false);
    relay.consoleFollow = true;
    expect(shouldStopConsoleAtSongEnd(relay)).toBe(false);
    relay.consoleMayRun = true;
    expect(shouldStopConsoleAtSongEnd(relay)).toBe(true);
    relay.consoleFollow = false;
    expect(shouldStopConsoleAtSongEnd(relay)).toBe(false);
  });
});
