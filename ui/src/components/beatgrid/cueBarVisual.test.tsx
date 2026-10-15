import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { BeatGridAppMovement, BeatGridCue } from "../../protocol";
import {
  CueBarVisual,
  barNameText,
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
  it("웨이브와 스윕은 app_movement 로도 그린다", () => {
    expect(effectShapeIcon(cue({ app_movement: movement("wave") }))).toBe("wave");
    expect(effectShapeIcon(cue({ app_movement: movement("sweep") }))).toBe("sweep");
  });

  it("서버 effect_shape 의 펄스·체이스는 app_movement 없이도 그린다", () => {
    expect(effectShapeIcon(cue({ effect_shape: "pulse" }))).toBe("pulse");
    expect(effectShapeIcon(cue({ effect_shape: "chase" }))).toBe("chase");
  });

  it("effect_shape 가 있으면 app_movement.shape 보다 먼저 쓴다", () => {
    expect(effectShapeIcon(cue({ effect_shape: "pulse", app_movement: movement("wave") }))).toBe("pulse");
  });

  it("effect_shape 가 없거나 null 이면 app_movement.shape 로 간다", () => {
    expect(effectShapeIcon(cue({ app_movement: movement("sweep") }))).toBe("sweep");
    expect(effectShapeIcon(cue({ effect_shape: null, app_movement: movement("wave") }))).toBe("wave");
  });

  it("모르는 effect_shape 값은 없는 것으로 보고 app_movement 로 간다", () => {
    expect(
      effectShapeIcon(cue({ effect_shape: "flash" as unknown as BeatGridCue["effect_shape"], app_movement: movement("wave") })),
    ).toBe("wave");
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
    expect(cueBarVisualClass(cue({ effect_shape: "pulse" }))).toBe(" has-cue-shape");
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

  it("펄스·체이스 칸은 효과 모양을 내고, 펄스는 시안 경로 그대로 그린다", () => {
    const pulse = renderToStaticMarkup(<CueBarVisual cue={cue({ effect_shape: "pulse" })} />);
    expect(pulse).toContain('data-shape="pulse"');
    expect(pulse).toContain('d="M1 9 H4 V2 H7 V9 H10 V2 H13 V9 H16"');
    const chase = renderToStaticMarkup(<CueBarVisual cue={cue({ effect_shape: "chase" })} />);
    expect(chase).toContain('data-shape="chase"');
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

describe("barNameText — 둘째 줄과 같은 밝기 글자는 이름에서 뗀다", () => {
  const value = (percent: number, label: string) =>
    cue({ label, brightness: { mode: "value", value_percent: percent, preset_no: null } });
  const dimmer = (presetNo: string, label: string) =>
    cue({ label, brightness: { mode: "dimmer_preset", value_percent: null, preset_no: presetNo } });

  it("값 모드의 퍼센트를 칸 글자에서 뗀다", () => {
    expect(barNameText(value(40, "라벤더 워시 40%(2마디 번짐)"))).toBe("라벤더 워시 (2마디 번짐)");
    expect(barNameText(value(25, "워시 25% 덜어냄"))).toBe("워시 덜어냄");
    expect(barNameText(value(60, "킥 1·2·4박 60%"))).toBe("킥 1·2·4박");
  });

  it("디머 프리셋 번호를 칸 글자에서 뗀다", () => {
    expect(barNameText(dimmer("1.1", "FOH 켬1.1"))).toBe("FOH 켬");
  });

  it("다른 숫자의 일부는 건드리지 않는다", () => {
    expect(barNameText(value(40, "가속 140%"))).toBe("가속 140%");
    expect(barNameText(dimmer("1.1", "FOH 11.1"))).toBe("FOH 11.1");
  });

  it("떼고 나서 남는 글자가 없으면 원래 글자를 쓴다", () => {
    expect(barNameText(value(40, "40%"))).toBe("40%");
  });

  it("밝기 글자가 없으면 칸 글자 그대로다", () => {
    expect(barNameText(cue({ label: "앞박 1회" }))).toBe("앞박 1회");
    expect(barNameText(value(40, "앞박 1회"))).toBe("앞박 1회");
  });
});
