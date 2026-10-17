// 재생 시계 순수 함수 시험 (SPEC-LDBEAT-001 M9 step 7, 카드 t570,
// REQ-LDBEAT-024(b)(d)(f) / AC-LDBEAT-024(d)(f)(h)).
//
// jsdom 시험대가 없으므로(BeatGrid.test.tsx 같은 메모) DOM·오디오 엘리먼트를
// 흉내 내지 않고, 시계 산수·키 판정·자동 스크롤 목표·오류 흡수만 순수
// 함수로 시험한다.
import { describe, expect, it, vi } from "vitest";

import {
  audioClockSeconds,
  clampPlaybackSeconds,
  elapsedPlaybackSeconds,
  followPauseEnded,
  followScrollTarget,
  formatPlaybackClock,
  hasReachedPlaybackEnd,
  isPlaybackSpaceToggleKey,
  playheadPixelX,
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

describe("audioClockSeconds — 음원이 실제로 도는 동안은 음원 시간이 시계다", () => {
  it("재생 중이면 음원의 currentTime 을 그대로 쓴다", () => {
    expect(audioClockSeconds({ paused: false, currentTime: 12.5, error: null })).toBe(12.5);
  });

  it("음원이 없거나 멈췄거나 오류가 나면 null — 호출자는 성능시계로 이어 간다", () => {
    expect(audioClockSeconds(null)).toBeNull();
    expect(audioClockSeconds({ paused: true, currentTime: 12.5, error: null })).toBeNull();
    expect(audioClockSeconds({ paused: false, currentTime: 12.5, error: { code: 4 } })).toBeNull();
  });

  it("값이 유한하지 않으면 null, 음수면 0으로 자른다", () => {
    expect(audioClockSeconds({ paused: false, currentTime: Number.NaN, error: null })).toBeNull();
    expect(audioClockSeconds({ paused: false, currentTime: -0.5, error: null })).toBe(0);
  });
});

describe("playheadPixelX — 재생 위치(초) → 가로 픽셀(칸과 같은 식, 마디 단위로 끊기지 않음)", () => {
  it("1마디 = pxPerBar 픽셀, 초는 박 길이(secondsPerBar)로 나눈다", () => {
    expect(playheadPixelX(0, 2, 42)).toBe(0);
    expect(playheadPixelX(2, 2, 42)).toBe(42);
    expect(playheadPixelX(3, 2, 42)).toBe(63); // 1.5마디
  });

  it("마디 사이 중간 시각도 소수 픽셀로 나온다", () => {
    const a = playheadPixelX(1, 2, 42) as number;
    const b = playheadPixelX(1.1, 2, 42) as number;
    expect(b - a).toBeCloseTo(2.1, 6);
  });

  it("박 길이를 모르면 null — 지어내지 않는다", () => {
    expect(playheadPixelX(3, null, 42)).toBeNull();
    expect(playheadPixelX(3, 0, 42)).toBeNull();
  });
});

describe("followScrollTarget — 재생선이 보이는 칸의 1/3 을 넘으면 연속으로 따라간다(AC-LDBEAT-024(h))", () => {
  it("재생선이 1/3 안쪽에 있으면 스크롤하지 않는다(null)", () => {
    // 보이는 폭 300 → 1/3 = 100.
    expect(followScrollTarget(50, 0, 300)).toBeNull();
    expect(followScrollTarget(99.9, 0, 300)).toBeNull();
  });

  it("1/3 을 넘으면 재생선이 그 자리에 머물도록 스크롤 목표를 준다", () => {
    expect(followScrollTarget(150, 0, 300)).toBe(50);
    expect(followScrollTarget(400, 200, 300)).toBe(300);
  });

  it("보이는 칸 밖으로 크게 건너뛰면(앞이든 뒤든) 1/3 자리로 바로 옮긴다", () => {
    expect(followScrollTarget(2000, 0, 300)).toBe(1900);
    expect(followScrollTarget(50, 500, 300)).toBe(0);
  });

  it("보이는 폭이 0 이하(아직 측정 전)이면 null", () => {
    expect(followScrollTarget(500, 0, 0)).toBeNull();
  });

  it("재생선을 따라가는 동안 스크롤은 재생선 이동량만큼 매 프레임 움직인다(페이지 넘김 없음)", () => {
    const visible = 300;
    let scroll = 0;
    let x = 0;
    let previousScroll = 0;
    for (let frame = 0; frame < 400; frame++) {
      x += 1.5; // 한 프레임에 1.5px 전진
      const target = followScrollTarget(x, scroll, visible);
      if (target !== null) scroll = target;
      // 재생선은 보이는 칸 안에 항상 있다.
      expect(x - scroll).toBeLessThanOrEqual(visible);
      expect(x - scroll).toBeGreaterThanOrEqual(0);
      // 1/3 을 넘은 뒤로는 한 프레임에 1.5px 만큼만 움직인다.
      if (frame > 200) expect(scroll - previousScroll).toBeCloseTo(1.5, 6);
      previousScroll = scroll;
    }
  });
});

describe("followPauseEnded — 사용자가 직접 스크롤하면 잠시 따라가기를 멈춘다", () => {
  it("직접 스크롤한 적이 없으면 멈춤이 끝난 것이다", () => {
    expect(followPauseEnded(null, 1000)).toBe(true);
  });

  it("직접 스크롤 뒤 3초가 안 지났으면 아직 멈춤", () => {
    expect(followPauseEnded(1000, 3999)).toBe(false);
  });

  it("직접 스크롤 뒤 3초가 지나면 다시 따라간다", () => {
    expect(followPauseEnded(1000, 4000)).toBe(true);
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

// 3차 전체 실행 G-19 — LOVE ATTACK 마디 지도의 1마디 첫 박은 1.498초, 한 마디 2.14282초라
// 0마디는 1.498 − 2.14282 = −0.64482초에 시작한다(콘솔 큐와 같은 기준). 0초 기준이면 화면
// 마디 경계가 콘솔보다 0.645초 늦었다.
describe("0마디 시작 시각(bar_origin_seconds) 기준", () => {
  const spb = 240 / 112.00191993244025;
  const origin = 1.498 - spb;

  it("재생선은 1마디 첫 박에서 정확히 1마디 자리다", () => {
    expect(playheadPixelX(1.498, spb, 100, origin)).toBeCloseTo(100, 6);
    expect(playheadPixelX(1.498 + 26 * spb, spb, 100, origin)).toBeCloseTo(2700, 6);
  });

  it("기준이 없으면 예전 그대로 0초가 0마디 시작이다", () => {
    expect(playheadPixelX(spb, spb, 100)).toBeCloseTo(100, 6);
    expect(playheadPixelX(spb, spb, 100, null)).toBeCloseTo(100, 6);
  });
});
