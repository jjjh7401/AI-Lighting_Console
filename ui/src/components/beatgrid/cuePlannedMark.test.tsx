/** 계획 표시(리드 결정 2026-10-16, 콘솔에 아직 없음) — 계획 색 칸은 점선·제목 글로 구분하고,
 * 콘솔 번호가 없는 디머·위치 자리는 계획 이름을 흐리게 그린다. 막대·「이 마디 한눈에」·무대 장비는
 * 같은 계획 색 값을 쓴다. */
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { BeatGridCue, BeatGridTrack } from "../../protocol";
import { cueColorFill, trackStageColor } from "../BeatGrid";
import {
  CUE_PLANNED_COLOR_TITLE,
  CueBarVisual,
  cueBarMetaParts,
  cueBarMetaText,
  cuePlannedClassName,
  cuePlannedTitleSuffix,
  isCuePlannedColor,
} from "./cueBarVisual";
import { presetSwatchColor } from "./glanceCells";

function cue(overrides: Partial<BeatGridCue> = {}): BeatGridCue {
  return {
    bar: 18,
    label: "핑크 70% 끊어 바꿈 · 밝기 올림",
    brightness: { mode: null, value_percent: null, preset_no: null },
    position_preset_no: null,
    color_preset_no: null,
    effect_preset_no: null,
    effect_kind: null,
    entry: { fade_bars: null, mib_mode: null },
    source_ref: null,
    app_movement: null,
    evidence: null,
    ...overrides,
  } as BeatGridCue;
}

function track(cues: BeatGridCue[]): BeatGridTrack {
  return { group_name: "WASH-ALL", layer_role: "wash", cues } as unknown as BeatGridTrack;
}

/** 계획 색(콘솔에 없음) — 핑크(100·50·75). */
const PINK_PLANNED = { color_planned: true, color_rgb: [100, 50, 75] as [number, number, number] };

describe("isCuePlannedColor — 계획 색은 표시 플래그와 유효한 색 값이 함께 있을 때만", () => {
  it("color_planned 이고 색 값이 0~100 안이면 계획 색이다", () => {
    expect(isCuePlannedColor(cue(PINK_PLANNED))).toBe(true);
  });

  it("플래그가 없거나 거짓이거나 색 값이 범위 밖이면 계획 색이 아니다", () => {
    expect(isCuePlannedColor(cue({ color_rgb: [100, 50, 75] }))).toBe(false);
    expect(isCuePlannedColor(cue({ color_planned: false, color_rgb: [100, 50, 75] }))).toBe(false);
    expect(isCuePlannedColor(cue({ color_planned: true, color_rgb: [150, 50, 75] }))).toBe(false);
  });
});

describe("cuePlannedClassName · cuePlannedTitleSuffix — 켜진 계획 색 칸에만 점선과 제목 글", () => {
  it("켜진 계획 색 칸은 점선 modifier 와 「계획 색 — 아직 콘솔에 없음」 글을 받는다", () => {
    expect(cuePlannedClassName(cue(PINK_PLANNED), true)).toBe(" is-color-planned");
    expect(cuePlannedTitleSuffix(cue(PINK_PLANNED), true)).toBe(` · ${CUE_PLANNED_COLOR_TITLE}`);
    expect(CUE_PLANNED_COLOR_TITLE).toBe("계획 색 — 아직 콘솔에 없음");
  });

  it("꺼진 칸이거나 콘솔 색 칸이면 아무것도 붙이지 않는다", () => {
    expect(cuePlannedClassName(cue(PINK_PLANNED), false)).toBe("");
    expect(cuePlannedTitleSuffix(cue(PINK_PLANNED), false)).toBe("");
    expect(cuePlannedClassName(cue({ color_rgb: [100, 50, 75] }), true)).toBe("");
    expect(cuePlannedTitleSuffix(cue({ color_rgb: [100, 50, 75] }), true)).toBe("");
  });
});

describe("계획 이름 — 콘솔 번호가 없을 때만 둘째 줄에 흐리게", () => {
  it("위치 계획 이름 · 밝기 · 계획 디머 이름을 조각별로 준다", () => {
    const floor = cue({
      brightness: { mode: "value", value_percent: 100, preset_no: null },
      planned_position_name: "FLOOR",
      planned_dimmer_name: "DIM-100",
    });

    expect(cueBarMetaParts(floor)).toEqual([
      { text: "위치 FLOOR", planned: true },
      { text: "100%", planned: false },
      { text: "DIM-100", planned: true },
    ]);
    expect(cueBarMetaText(floor)).toBe("위치 FLOOR · 100% · DIM-100");
  });

  it("콘솔 디머 번호가 있으면 계획 디머 이름은 나오지 않는다", () => {
    const onConsole = cue({
      brightness: { mode: "dimmer_preset", value_percent: null, preset_no: "1.8" },
      planned_dimmer_name: "DIM-40",
    });

    expect(cueBarMetaParts(onConsole)).toEqual([{ text: "1.8", planned: false }]);
  });

  it("콘솔 위치 번호가 있으면 계획 위치 이름은 나오지 않는다", () => {
    const withNumber = cue({ position_preset_no: "2.1", planned_position_name: "FLOOR" });

    expect(cueBarMetaParts(withNumber)).toEqual([{ text: "위치 2.1", planned: false }]);
  });

  it("계획 이름이 없는 칸은 예전 둘째 줄 글 그대로다", () => {
    expect(cueBarMetaText(cue({ brightness: { mode: "value", value_percent: 40, preset_no: null } }))).toBe("40%");
    expect(cueBarMetaText(cue())).toBe("");
  });

  it("화면에는 계획 이름 조각만 흐린 글자(is-planned-name)로 그린다", () => {
    const html = renderToStaticMarkup(
      <CueBarVisual
        cue={cue({ brightness: { mode: "value", value_percent: 100, preset_no: null }, planned_dimmer_name: "DIM-100" })}
      />,
    );

    expect(html).toContain('<span class="is-planned-name" title="계획 이름 — 아직 콘솔에 없음">DIM-100</span>');
    expect(html).toContain("100%");
    expect(html).not.toContain('class="is-planned-name">100%');
  });
});

describe("같은 값 — 막대·「이 마디 한눈에」·무대 장비가 한 계획 색을 쓴다", () => {
  it("라벤더(55·35·100): 막대 #8c59ff · 한눈에 rgb(140, 89, 255) · 무대 rgb(140, 89, 255)", () => {
    const lavender = cue({ bar: 7, label: "라벤더 워시 40%", color_planned: true, color_rgb: [55, 35, 100] });

    expect(cueColorFill(lavender).background).toBe("#8c59ff");
    expect(cueColorFill(lavender).isColorUnset).toBe(false);
    expect(presetSwatchColor(lavender.color_rgb)).toBe("rgb(140, 89, 255)");
    expect(trackStageColor(track([lavender]), 0, 7)).toBe("rgb(140, 89, 255)");
  });

  it("핑크(100·50·75): 막대 #ff80bf · 한눈에 rgb(255, 128, 191) · 무대 rgb(255, 128, 191)", () => {
    const pink = cue({ bar: 18, ...PINK_PLANNED });

    expect(cueColorFill(pink).background).toBe("#ff80bf");
    expect(presetSwatchColor(pink.color_rgb)).toBe("rgb(255, 128, 191)");
    expect(trackStageColor(track([pink]), 0, 18)).toBe("rgb(255, 128, 191)");
  });
});
