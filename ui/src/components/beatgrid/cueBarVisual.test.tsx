import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { BeatGridAppMovement, BeatGridCue } from "../../protocol";
import {
  CueBarVisual,
  barShortText,
  brightnessLinePercent,
  cueBarMetaText,
  cueBarVisualClass,
  effectShapeIcon,
} from "./cueBarVisual";

function cue(overrides: Partial<BeatGridCue> = {}): BeatGridCue {
  return {
    bar: 7,
    label: "칸",
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
  };
}

function movement(shape: BeatGridAppMovement["shape"]): BeatGridAppMovement {
  return { shape, axes: ["Pan"], period_unit: null, period_value: null, phase_spread: null };
}

describe("brightnessLinePercent — 밝기 선은 값 모드의 퍼센트만", () => {
  it("값 모드의 퍼센트를 그대로 쓴다", () => {
    expect(brightnessLinePercent(cue({ brightness: { mode: "value", value_percent: 55, preset_no: null } }))).toBe(55);
  });

  it("0~100 밖의 값은 잘라서 쓴다", () => {
    expect(brightnessLinePercent(cue({ brightness: { mode: "value", value_percent: 120, preset_no: null } }))).toBe(100);
    expect(brightnessLinePercent(cue({ brightness: { mode: "value", value_percent: -5, preset_no: null } }))).toBe(0);
  });

  it("디머 프리셋이거나 값이 미정이면 선을 긋지 않는다", () => {
    expect(
      brightnessLinePercent(cue({ brightness: { mode: "dimmer_preset", value_percent: null, preset_no: "1.1" } })),
    ).toBeNull();
    expect(brightnessLinePercent(cue({ brightness: { mode: "value", value_percent: null, preset_no: null } }))).toBeNull();
    expect(brightnessLinePercent(cue())).toBeNull();
  });
});

describe("effectShapeIcon — 시안 아이콘이 있는 구조화 모양만", () => {
  it("웨이브와 스윕은 그린다", () => {
    expect(effectShapeIcon(cue({ app_movement: movement("wave") }))).toBe("wave");
    expect(effectShapeIcon(cue({ app_movement: movement("sweep") }))).toBe("sweep");
  });

  it("시안에 아이콘이 없는 모양은 그리지 않는다", () => {
    expect(effectShapeIcon(cue({ app_movement: movement("circle") }))).toBeNull();
    expect(effectShapeIcon(cue({ app_movement: movement("flyout") }))).toBeNull();
    expect(effectShapeIcon(cue({ app_movement: movement("ballyhoo") }))).toBeNull();
  });

  it("구조화 필드가 없으면 글자에 '스윕'이 있어도 그리지 않는다(글자 역산 금지)", () => {
    expect(effectShapeIcon(cue({ label: "가속 스윕 4박", app_movement: null }))).toBeNull();
    expect(effectShapeIcon(cue())).toBeNull();
  });
});

describe("barShortText — 위치·밝기 짧은 글자, 없으면 null", () => {
  it("위치 번호와 밝기 퍼센트를 쓴다", () => {
    expect(
      barShortText(cue({ position_preset_no: "2.61", brightness: { mode: "value", value_percent: 55, preset_no: null } })),
    ).toEqual({ position: "위치 2.61", brightness: "55%" });
  });

  it("디머 프리셋 번호는 밝기 자리에 그대로 쓴다", () => {
    expect(barShortText(cue({ brightness: { mode: "dimmer_preset", value_percent: null, preset_no: "1.1" } }))).toEqual({
      position: null,
      brightness: "1.1",
    });
  });

  it("값이 없으면 그 자리는 null이다", () => {
    expect(barShortText(cue())).toEqual({ position: null, brightness: null });
  });
});

describe("cueBarMetaText / cueBarVisualClass", () => {
  it("두 값을 가운뎃점으로 잇고, 둘 다 없으면 빈 문자열이다", () => {
    expect(
      cueBarMetaText(cue({ position_preset_no: "2.61", brightness: { mode: "value", value_percent: 55, preset_no: null } })),
    ).toBe("위치 2.61 · 55%");
    expect(cueBarMetaText(cue())).toBe("");
  });

  it("그릴 요소가 있는 칸에만 modifier 클래스를 붙인다", () => {
    expect(cueBarVisualClass(cue())).toBe("");
    expect(cueBarVisualClass(cue({ app_movement: movement("wave") }))).toBe(" has-cue-shape");
    expect(cueBarVisualClass(cue({ position_preset_no: "2.61" }))).toBe(" has-cue-meta");
    expect(cueBarVisualClass(cue({ app_movement: movement("sweep"), position_preset_no: "2.61" }))).toBe(
      " has-cue-shape has-cue-meta",
    );
  });
});

describe("CueBarVisual 렌더 — 시안 요소만 내보낸다", () => {
  it("그릴 것이 없는 칸은 아무 요소도 내지 않는다", () => {
    expect(renderToStaticMarkup(<CueBarVisual cue={cue()} />)).toBe("");
  });

  it("밝기 선·모양·글자가 모두 있으면 셋 다 낸다", () => {
    const html = renderToStaticMarkup(
      <CueBarVisual
        cue={cue({
          position_preset_no: "2.61",
          brightness: { mode: "value", value_percent: 55, preset_no: null },
          app_movement: movement("wave"),
        })}
      />,
    );
    expect(html).toContain('class="beat-grid-cue-ib"');
    expect(html).toContain("width:55%");
    expect(html).toContain('data-shape="wave"');
    expect(html).toContain("위치 2.61 · 55%");
  });

  it("디머 프리셋 칸에는 밝기 선과 모양이 없다", () => {
    const html = renderToStaticMarkup(
      <CueBarVisual
        cue={cue({
          brightness: { mode: "dimmer_preset", value_percent: null, preset_no: "1.1" },
          app_movement: movement("circle"),
        })}
      />,
    );
    expect(html).not.toContain("beat-grid-cue-ib");
    expect(html).not.toContain("<svg");
    expect(html).toContain("1.1");
  });
});

describe("barShortText — 콘솔 프리셋 이름은 위치 번호 옆에", () => {
  it("칸이 위치 이름을 실으면 번호 뒤에 이름을 붙인다(「LA 」는 뗀다)", () => {
    expect(barShortText(cue({ position_preset_no: "2.46", position_preset_name: "LA Back Aim" }))).toEqual({
      position: "위치 2.46 Back Aim",
      brightness: null,
    });
  });

  it("이름이 없으면 번호만 쓴다", () => {
    expect(barShortText(cue({ position_preset_no: "2.46" }))).toEqual({ position: "위치 2.46", brightness: null });
  });

  it("번호가 없으면 이름이 있어도 위치 글자는 없다", () => {
    expect(barShortText(cue({ position_preset_name: "LA Back Aim" }))).toEqual({ position: null, brightness: null });
  });

  it("렌더된 마크업에도 번호 옆 이름이 나온다", () => {
    const html = renderToStaticMarkup(
      <CueBarVisual cue={cue({ position_preset_no: "2.46", position_preset_name: "LA Back Aim" })} />,
    );
    expect(html).toContain("위치 2.46 Back Aim");
  });
});
