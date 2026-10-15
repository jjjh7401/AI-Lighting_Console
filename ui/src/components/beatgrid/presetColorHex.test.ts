// 색 프리셋 목표 RGB(0~100%)를 화면 색으로 옮긴다. 값이 없거나 범위 밖이면 지어내지
// 않는다 — 그 번호의 막대는 중립(해칭)으로 남는다(REQ-LDBEAT-015(f)와 같은 원칙).
import { describe, expect, it } from "vitest";

import { presetColorHexMap, presetRgbHex } from "./presetColorHex";

describe("presetRgbHex — 0~100% 를 화면 색으로", () => {
  it("라벤더 시안 값(60·30·100%)은 #994dff 다", () => {
    expect(presetRgbHex({ r: 60, g: 30, b: 100 })).toBe("#994dff");
  });

  it("0%와 100%는 끝 값이다", () => {
    expect(presetRgbHex({ r: 0, g: 0, b: 0 })).toBe("#000000");
    expect(presetRgbHex({ r: 100, g: 100, b: 100 })).toBe("#ffffff");
  });

  it("값이 없거나 범위 밖이면 undefined — 지어내지 않는다", () => {
    expect(presetRgbHex(undefined)).toBeUndefined();
    expect(presetRgbHex(null)).toBeUndefined();
    expect(presetRgbHex({ r: 101, g: 0, b: 0 })).toBeUndefined();
    expect(presetRgbHex({ r: Number.NaN, g: 0, b: 0 })).toBeUndefined();
  });
});

describe("presetColorHexMap — 모르는 번호는 표에 넣지 않는다", () => {
  it("값이 있는 번호만 옮긴다", () => {
    expect(
      presetColorHexMap({ "4.21": { r: 55, g: 80, b: 100 }, "4.22": null, "4.23": undefined }),
    ).toEqual({ "4.21": "#8cccff" });
  });

  it("preset_colors 가 없으면 빈 표다", () => {
    expect(presetColorHexMap(undefined)).toEqual({});
    expect(presetColorHexMap(null)).toEqual({});
  });
});
