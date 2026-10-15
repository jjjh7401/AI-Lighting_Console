// 격자 축 끝 마디 계산 시험 — 칸·곡 마디 수에 따라 축이 넓어지고, 줄어들지는 않는다.
import { describe, expect, it } from "vitest";

import { cellBarsOf, gridAxisEnd } from "./gridAxis";

const DEFAULT_RANGE = { start: 0, end: 25 };

describe("격자 축 끝 마디", () => {
  it("칸과 곡 마디 수가 기본 범위 안이면 기본 범위 끝을 쓴다", () => {
    expect(gridAxisEnd(DEFAULT_RANGE, [0, 5, 25], null)).toBe(25);
  });

  it("칸이 기본 범위 밖에 있으면 마지막 칸의 마디까지 넓힌다", () => {
    expect(gridAxisEnd(DEFAULT_RANGE, [3, 82, 40], null)).toBe(82);
  });

  it("곡 마디 수가 기본 범위보다 크면 곡 마디 수까지 넓힌다", () => {
    expect(gridAxisEnd(DEFAULT_RANGE, [3], 82)).toBe(82);
  });

  it("축을 줄이지는 않는다", () => {
    expect(gridAxisEnd({ start: 0, end: 40 }, [3], 10)).toBe(40);
  });

  it("유한하지 않은 값은 무시한다", () => {
    expect(gridAxisEnd(DEFAULT_RANGE, [Number.NaN], Number.POSITIVE_INFINITY)).toBe(25);
  });
});

describe("칸이 있는 마디 모으기", () => {
  it("모든 줄의 칸 마디를 한 목록으로 모은다", () => {
    const tracks = [{ cues: [{ bar: 1 }, { bar: 2 }] }, { cues: [{ bar: 7 }] }];
    expect(cellBarsOf(tracks)).toEqual([1, 2, 7]);
  });
});
