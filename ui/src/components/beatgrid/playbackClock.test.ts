// 재생 시계 순수 함수 시험 (SPEC-LDBEAT-001 M9 step 7, 카드 t570,
// REQ-LDBEAT-024(b)(d)(f) / AC-LDBEAT-024(d)(f)(h)).
//
// jsdom 시험대가 없으므로(BeatGrid.test.tsx 같은 메모) DOM·오디오 엘리먼트를
// 흉내 내지 않고, 시계 산수·키 판정·자동 스크롤 목표·오류 흡수만 순수
// 함수로 시험한다.
import { describe, expect, it, vi } from "vitest";

import {
  formatPlaybackClock,
  autoScrollTargetForPlayhead,
  clampPlaybackSeconds,
  elapsedPlaybackSeconds,
  hasReachedPlaybackEnd,
  isPlaybackSpaceToggleKey,
  runPlaybackFrameUpdate,
} from "./playbackClock";

describe("elapsedPlaybackSeconds — 재생 앵커 + 성능시계로 지금 위치 계산", () => {
  it("경과한 ms 만큼 앵커 초에 더한다", () => {
    expect(elapsedPlaybackSeconds(10, 1000, 1000)).toBe(10);
    expect(elapsedPlaybackSeconds(10, 1000, 2500)).toBe(11.5);
  });

  it("시계가 거꾸로 가도(음수 경과) 앵커 초 밑으로 떨어지지 않는다", () => {
    expect(elapsedPlaybackSeconds(10, 2000, 1000)).toBe(10);
  });
});

describe("clampPlaybackSeconds — ±10초 스킵 클램프(AC-LDBEAT-024(d))", () => {
  it("범위 [0, max] 안으로 클램프한다", () => {
    expect(clampPlaybackSeconds(5, -10, 100)).toBe(0);
    expect(clampPlaybackSeconds(95, 10, 100)).toBe(100);
    expect(clampPlaybackSeconds(50, 10, 100)).toBe(60);
  });
});

describe("hasReachedPlaybackEnd — 곡 끝 도달 판정", () => {
  it("현재 위치가 끝 이상이면 true", () => {
    expect(hasReachedPlaybackEnd(100, 100)).toBe(true);
    expect(hasReachedPlaybackEnd(100.1, 100)).toBe(true);
    expect(hasReachedPlaybackEnd(99.9, 100)).toBe(false);
  });

  it("max 가 없으면(null) 끝에 도달할 수 없다(지어내지 않음)", () => {
    expect(hasReachedPlaybackEnd(100, null)).toBe(false);
  });
});

describe("isPlaybackSpaceToggleKey — 스페이스바 판정(REQ-LDBEAT-024(a))", () => {
  it("스페이스는 토글 키다", () => {
    expect(isPlaybackSpaceToggleKey({ code: "Space" })).toBe(true);
  });

  it("입력칸·선택칸·contenteditable 안의 스페이스는 토글하지 않는다", () => {
    expect(isPlaybackSpaceToggleKey({ code: "Space", targetTag: "INPUT" })).toBe(false);
    expect(isPlaybackSpaceToggleKey({ code: "Space", targetTag: "TEXTAREA" })).toBe(false);
    expect(isPlaybackSpaceToggleKey({ code: "Space", targetTag: "SELECT" })).toBe(false);
    expect(isPlaybackSpaceToggleKey({ code: "Space", isContentEditable: true })).toBe(false);
  });

  it("다른 키는 토글하지 않는다", () => {
    expect(isPlaybackSpaceToggleKey({ code: "Enter" })).toBe(false);
  });
});

describe("autoScrollTargetForPlayhead — 재생 중 자동 스크롤 목표(AC-LDBEAT-024(h))", () => {
  it("플레이헤드가 이미 보이는 범위 안이면 스크롤하지 않는다(null)", () => {
    // 마디 10, pxPerBar 10 → x=100. scrollLeft 0~1000 visible.
    expect(autoScrollTargetForPlayhead(10, 10, 0, 0, 1000)).toBeNull();
  });

  it("범위를 벗어나면 1/3 지점을 목표로 돌려준다(mockup keepVisible)", () => {
    // x = 100*10=1000, scrollLeft=0, visibleWidth=100 → vw-bw*2=100-20=80, x(1000)>0+80 → 스크롤.
    const target = autoScrollTargetForPlayhead(100, 10, 0, 0, 100);
    expect(target).toBe(Math.max(0, 1000 - 100 / 3));
  });

  it("보이는 폭이 0 이하이면(아직 측정 전) null", () => {
    expect(autoScrollTargetForPlayhead(10, 10, 0, 0, 0)).toBeNull();
  });

  it("목표는 0 밑으로 내려가지 않는다", () => {
    const target = autoScrollTargetForPlayhead(0, 10, 10, 500, 50);
    expect(target).not.toBeNull();
    expect(target as number).toBeGreaterThanOrEqual(0);
  });
});

describe("runPlaybackFrameUpdate — 화면 오류가 나도 재생이 멈추지 않음(REQ-LDBEAT-024(f))", () => {
  it("예외를 던지면 onError 로만 넘기고 다시 던지지 않는다", () => {
    const onError = vi.fn();
    expect(() =>
      runPlaybackFrameUpdate(() => {
        throw new Error("화면 쪽 오류");
      }, onError),
    ).not.toThrow();
    expect(onError).toHaveBeenCalledWith("화면 쪽 오류");
  });

  it("오류가 없으면 onError 를 부르지 않는다", () => {
    const onError = vi.fn();
    const update = vi.fn();
    runPlaybackFrameUpdate(update, onError);
    expect(update).toHaveBeenCalledOnce();
    expect(onError).not.toHaveBeenCalled();
  });

  it("Error 가 아닌 값을 던져도 문자열로 바꿔 넘긴다", () => {
    const onError = vi.fn();
    runPlaybackFrameUpdate(() => {
      // eslint-disable-next-line @typescript-eslint/no-throw-literal
      throw "문자열 오류";
    }, onError);
    expect(onError).toHaveBeenCalledWith("문자열 오류");
  });
});

// 카드 t570 — 시안 시계 모양 「분:초.소수1자리」(mockup `fmtT`, 초기값 「0:00.0」).
describe("formatPlaybackClock", () => {
  it("0초는 0:00.0", () => {
    expect(formatPlaybackClock(0)).toBe("0:00.0");
  });

  it("1분 미만은 초를 두 자리로 채운다", () => {
    expect(formatPlaybackClock(5.25)).toBe("0:05.3");
  });

  it("1분을 넘으면 분이 올라간다", () => {
    expect(formatPlaybackClock(125.04)).toBe("2:05.0");
  });
});
