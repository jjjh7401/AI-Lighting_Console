import { describe, expect, it } from "vitest";
import { CONSOLE_SEEK_MAX_GAP_MS, consoleSeekSendDelayMs } from "./consoleSeekPlan";

const DEBOUNCE_MS = 250;

/** 컴포넌트의 예약 규칙을 그대로 옮긴 모형: 대기 중이면 값만 바꾸고, 없으면 지연만큼 뒤에 보낸다. */
function simulateSends(pressesMs: number[]): number[] {
  const sends: number[] = [];
  let timerAt: number | null = null;
  let lastSent: number | null = null;
  const presses = [...pressesMs].sort((a, b) => a - b);
  const end = (presses[presses.length - 1] ?? 0) + 1000;
  let next = 0;
  for (let t = 0; t <= end; t++) {
    while (next < presses.length && presses[next] === t) {
      if (timerAt === null) {
        const since = lastSent === null ? null : t - lastSent;
        timerAt = t + consoleSeekSendDelayMs(since, DEBOUNCE_MS);
      }
      next++;
    }
    if (timerAt === t) {
      sends.push(t);
      lastSent = t;
      timerAt = null;
    }
  }
  return sends;
}

describe("연타 중 콘솔 보내기 간격", () => {
  it("아직 한 번도 안 보냈으면 디바운스만큼 기다린다", () => {
    expect(consoleSeekSendDelayMs(null, DEBOUNCE_MS)).toBe(DEBOUNCE_MS);
  });

  it("보낸 지 상한 간격이 지났으면 바로 보낸다", () => {
    expect(consoleSeekSendDelayMs(CONSOLE_SEEK_MAX_GAP_MS + 50, DEBOUNCE_MS)).toBe(0);
  });

  it("상한 안이면 상한까지 남은 만큼 기다리되 디바운스를 넘지 않는다", () => {
    expect(consoleSeekSendDelayMs(200, DEBOUNCE_MS)).toBe(200);
    expect(consoleSeekSendDelayMs(100, DEBOUNCE_MS)).toBe(DEBOUNCE_MS);
  });

  it("0.2초 간격 연타 중에도 콘솔은 상한 간격마다 따라온다", () => {
    const presses = Array.from({ length: 16 }, (_, i) => i * 200);
    const sends = simulateSends(presses);
    expect(sends.length).toBeGreaterThanOrEqual(6);
    for (let i = 1; i < sends.length; i++) {
      expect(sends[i] - sends[i - 1]).toBeLessThanOrEqual(CONSOLE_SEEK_MAX_GAP_MS);
    }
    // 마지막 누름 뒤 상한 안에 마지막 자리가 나간다.
    expect(sends[sends.length - 1]).toBeLessThanOrEqual(presses[presses.length - 1] + CONSOLE_SEEK_MAX_GAP_MS);
  });

  it("띄엄띄엄 누르면 첫 누름은 디바운스 뒤, 보낸 지 상한이 지난 누름은 바로 보낸다", () => {
    const sends = simulateSends([0, 1000]);
    expect(sends).toEqual([DEBOUNCE_MS, 1000]);
  });
});
