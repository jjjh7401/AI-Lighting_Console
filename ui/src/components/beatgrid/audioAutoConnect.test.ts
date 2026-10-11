// 음원 자동 연결 순수 함수 시험 (SPEC-LDBEAT-001 M9 step 7, 카드 t570,
// REQ-LDBEAT-024(c) / AC-LDBEAT-024(a)(b)(c)).
//
// 이 모듈은 실제 File/HTMLAudioElement 를 다루지 않는다(DOM 시험대 없음,
// BeatGrid.test.tsx 같은 메모) — 연결 상태 전이·버튼 문구·재생 큐잉
// 판정만 순수 함수로 시험한다.
import { describe, expect, it } from "vitest";

import {
  audioButtonLabel,
  audioSourceId,
  formatAudioConnectFailureReason,
  resolvePlayIntentOnReady,
  shouldAutoConnectAudio,
  shouldDeferPlayPress,
} from "./audioAutoConnect";

describe("audioSourceId — 파일 하나를 구분하는 안정적 식별자", () => {
  it("이름+크기로 만든다", () => {
    expect(audioSourceId({ name: "LOVE ATTACK.mp3", size: 1234 })).toBe("LOVE ATTACK.mp3:1234");
  });

  it("파일이 없으면 null", () => {
    expect(audioSourceId(null)).toBeNull();
  });
});

describe("shouldAutoConnectAudio — 런북 뷰를 열 때 자동 연결할지(AC-LDBEAT-024(a))", () => {
  it("첨부된 음원이 없으면(null) 연결하지 않는다", () => {
    expect(shouldAutoConnectAudio({ status: "idle", connectedSourceId: null }, null)).toBe(false);
  });

  it("첨부된 음원이 있고 아직 그 음원을 연결한 적 없으면 연결한다", () => {
    expect(shouldAutoConnectAudio({ status: "idle", connectedSourceId: null }, "a.mp3:10")).toBe(true);
  });

  it("이미 그 음원에 연결돼 있으면 다시 연결하지 않는다(루프 방지)", () => {
    expect(shouldAutoConnectAudio({ status: "connected", connectedSourceId: "a.mp3:10" }, "a.mp3:10")).toBe(
      false,
    );
  });

  it("다른 음원으로 바뀌면 다시 연결한다", () => {
    expect(shouldAutoConnectAudio({ status: "connected", connectedSourceId: "a.mp3:10" }, "b.mp3:20")).toBe(
      true,
    );
  });

  it("불러오는 중이면 겹쳐 연결하지 않는다", () => {
    expect(shouldAutoConnectAudio({ status: "loading", connectedSourceId: null }, "a.mp3:10")).toBe(false);
  });
});

describe("audioButtonLabel — ♪ 버튼 문구(AC-LDBEAT-024(a))", () => {
  it("연결되면 체크(✓)와 파일명", () => {
    expect(audioButtonLabel("connected", "LOVE ATTACK.mp3")).toBe("✓ LOVE ATTACK.mp3");
  });

  it("불러오는 중이면 그 사실을 보인다", () => {
    expect(audioButtonLabel("loading", "LOVE ATTACK.mp3")).toBe("불러오는 중…");
  });

  it("idle·failed 는 기본 안내", () => {
    expect(audioButtonLabel("idle", null)).toBe("음원");
    expect(audioButtonLabel("failed", "x.mp3")).toBe("음원");
  });
});

describe("formatAudioConnectFailureReason — 연결 실패 이유(AC-LDBEAT-024(c))", () => {
  it("파일명을 포함한 이유 문자열을 돌려준다", () => {
    expect(formatAudioConnectFailureReason("x.mp3")).toContain("x.mp3");
  });
});

describe("shouldDeferPlayPress — 불러오는 중엔 ▶ 를 지금 처리하지 않음(AC-LDBEAT-024(b))", () => {
  it("loading 일 때만 뒤로 미룬다", () => {
    expect(shouldDeferPlayPress("loading")).toBe(true);
    expect(shouldDeferPlayPress("idle")).toBe(false);
    expect(shouldDeferPlayPress("connected")).toBe(false);
    expect(shouldDeferPlayPress("failed")).toBe(false);
  });
});

describe("resolvePlayIntentOnReady — 큐잉된 재생이 준비되면 바로 시작(AC-LDBEAT-024(b))", () => {
  it("큐잉 없음이면 아무것도 안 한다", () => {
    expect(resolvePlayIntentOnReady(false, "loading")).toEqual({ shouldStart: false, nextPending: false });
  });

  it("큐잉 중 + 아직 loading 이면 큐잉을 유지한다", () => {
    expect(resolvePlayIntentOnReady(true, "loading")).toEqual({ shouldStart: false, nextPending: true });
  });

  it("큐잉 중 + connected 가 되면 즉시 시작하고 큐잉을 지운다(대기 없이)", () => {
    expect(resolvePlayIntentOnReady(true, "connected")).toEqual({ shouldStart: true, nextPending: false });
  });

  it("큐잉 중 + failed 가 되면 시작하지 않고 큐잉을 지운다", () => {
    expect(resolvePlayIntentOnReady(true, "failed")).toEqual({ shouldStart: false, nextPending: false });
  });
});
