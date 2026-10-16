// 「이 마디 한눈에」 칩 앞 색 네모 — 서버가 프리셋 항목에 색(rgb, 각 0~100%)을 실을 때만 그린다(리드 결정).
import { describe, expect, it } from "vitest";

import type { BeatGridCue, BeatGridDrawerSection } from "../../protocol";
import { colorCell, presetSplitSwatch, presetSwatchColor } from "./glanceCells";

function cue(overrides: Partial<BeatGridCue> = {}): BeatGridCue {
  return {
    bar: 0,
    label: "테스트 칸",
    brightness: { mode: "value", value_percent: 60, preset_no: null },
    position_preset_no: null,
    color_preset_no: null,
    effect_preset_no: null,
    effect_kind: null,
    entry: { fade_bars: null, mib_mode: null },
    source_ref: null,
    app_movement: null,
    evidence: null,
    ...overrides,
  };
}

const COLOR_SECTION: BeatGridDrawerSection[] = [
  {
    pool_name: "Color",
    title: "색",
    pool_no: 4,
    unread: false,
    bands_confirmed: true,
    entries: [
      { preset_no: "4.21", name: "LA Red", usage_count: 1, used_by: [], is_effect_band: false, rgb: [100, 50, 0] },
      { preset_no: "4.22", name: "LA Blue", usage_count: 0, used_by: [], is_effect_band: false },
    ],
  },
];

describe("presetSwatchColor", () => {
  it("색 값이 없으면 네모를 그리지 않는다(null)", () => {
    expect(presetSwatchColor(undefined)).toBeNull();
    expect(presetSwatchColor(null)).toBeNull();
  });

  it("0~100% 를 0~255 바이트로 바꾼다", () => {
    expect(presetSwatchColor([100, 50, 0])).toBe("rgb(255, 128, 0)");
    expect(presetSwatchColor([0, 0, 0])).toBe("rgb(0, 0, 0)");
  });
});

describe("colorCell 칩의 색 네모", () => {
  it("서버가 색 값을 실은 프리셋이면 칩에 색 네모 값이 있다", () => {
    expect(colorCell(cue({ color_preset_no: "4.21" }), "side", COLOR_SECTION)).toMatchObject({
      kind: "chip",
      presetNo: "4.21",
      name: "Red",
      swatch: "rgb(255, 128, 0)",
    });
  });

  it("색 값이 없는 프리셋이면 네모 키가 없다(네모 생략)", () => {
    const result = colorCell(cue({ color_preset_no: "4.22" }), "side", COLOR_SECTION);
    expect(result).toMatchObject({ kind: "chip", presetNo: "4.22", name: "Blue" });
    expect(result).not.toHaveProperty("swatch");
  });

  it("서랍 색이 없으면 칸이 낼 색(color_rgb)을 네모로 쓴다", () => {
    const result = colorCell(
      cue({ color_preset_no: "4.22", color_rgb: [0, 50, 100] }),
      "side",
      COLOR_SECTION,
    );
    expect(result).toMatchObject({ kind: "chip", presetNo: "4.22", swatch: "rgb(0, 128, 255)" });
  });

  it("서랍 색이 있으면 칸 색보다 서랍 색을 쓴다", () => {
    const result = colorCell(
      cue({ color_preset_no: "4.21", color_rgb: [0, 0, 0] }),
      "side",
      COLOR_SECTION,
    );
    expect(result).toMatchObject({ kind: "chip", presetNo: "4.21", swatch: "rgb(255, 128, 0)" });
  });
});

describe("presetSplitSwatch — 색이 둘이면 네모를 반반 나눈다", () => {
  it("두 색이면 가로로 반반 나눈 띠다", () => {
    expect(
      presetSplitSwatch([
        [100, 50, 0],
        [0, 0, 100],
      ]),
    ).toBe("linear-gradient(to right, rgb(255, 128, 0) 0% 50%, rgb(0, 0, 255) 50% 100%)");
  });

  it("색이 한 개 이하이면 나누지 않는다(null — 호출부가 한 색 네모를 쓴다)", () => {
    expect(presetSplitSwatch(undefined)).toBeNull();
    expect(presetSplitSwatch([])).toBeNull();
    expect(presetSplitSwatch([[100, 50, 0]])).toBeNull();
  });

  it("세 색이면 세 구간으로 나눈다", () => {
    const swatch = presetSplitSwatch([
      [100, 0, 0],
      [0, 100, 0],
      [0, 0, 100],
    ]);
    expect(swatch?.startsWith("linear-gradient(to right, rgb(255, 0, 0) 0% ")).toBe(true);
    expect(swatch?.split("rgb(").length).toBe(4);
  });
});

describe("colorCell 칩의 색 네모 — 색 목록이 둘이면 반반", () => {
  it("color_rgbs 가 둘이면 서랍 색보다 반반 띠를 쓴다", () => {
    expect(
      colorCell(
        cue({
          color_preset_no: "4.21",
          color_rgbs: [
            [100, 0, 0],
            [0, 0, 100],
          ],
        }),
        "side",
        COLOR_SECTION,
      ),
    ).toMatchObject({
      kind: "chip",
      presetNo: "4.21",
      swatch: "linear-gradient(to right, rgb(255, 0, 0) 0% 50%, rgb(0, 0, 255) 50% 100%)",
    });
  });

  it("color_rgbs 가 한 개면 기존처럼 서랍 색 한 개를 쓴다", () => {
    expect(colorCell(cue({ color_preset_no: "4.21", color_rgbs: [[0, 0, 0]] }), "side", COLOR_SECTION)).toMatchObject({
      swatch: "rgb(255, 128, 0)",
    });
  });
});

describe("colorCell 계획 색 — 프리셋 번호 없이 계획 색만 있는 칸", () => {
  it("계획 색이면 「—」 대신 흐린 네모를 단다", () => {
    expect(colorCell(cue({ color_rgb: [40, 65, 95], color_planned: true }), "side", COLOR_SECTION)).toEqual({
      kind: "text",
      text: "—",
      dim: true,
      swatch: "rgb(102, 166, 242)",
    });
  });

  it("계획 표시가 없는 색 값은 그대로 「—」이고 네모가 없다", () => {
    expect(colorCell(cue({ color_rgb: [40, 65, 95] }), "side", COLOR_SECTION)).toEqual({ kind: "text", text: "—" });
  });

  it("역할이 색을 안 쓰면(무빙) 계획 색도 그리지 않는다", () => {
    expect(colorCell(cue({ color_rgb: [40, 65, 95], color_planned: true }), "mover", null)).toEqual({
      kind: "text",
      text: "—",
    });
  });
});
