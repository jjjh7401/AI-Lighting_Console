// 카드 t603 — 「＋ 새 프리셋 만들기」 창의 효과 종류: 효과 틀(서버 목록) + 한 바퀴(박/마디).
// 이 프로젝트는 jsdom 이 없다 — 순수 함수와 `renderToStaticMarkup`으로 잰다.
import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

import { NewPresetDialog } from "./BeatGrid";
import {
  fxRecipeFromDraft,
  fxTemplatesForKind,
  isValidFxPeriod,
  type NewPresetFxFieldsProps,
} from "./beatgrid/newPresetFx";
import { buildBeatGridNewPreset, type BeatGridFxTemplate } from "../protocol";

const TEMPLATES: BeatGridFxTemplate[] = [
  { fx_id: "sweep-soft-wide", display_name: "부드러운 좌우 스윕", attributes: ["Pan"], kinds: ["position", "mixed"] },
  {
    fx_id: "chase-warm-cool",
    display_name: "따뜻함에서 차가움으로",
    attributes: ["ColorRGB_R", "ColorRGB_G", "ColorRGB_B"],
    kinds: ["color", "mixed"],
  },
  { fx_id: "pulse-beat", display_name: "박자 펄스", attributes: ["Dimmer"], kinds: ["mixed"] },
];

const noop = () => {};

function fx(overrides: Partial<NewPresetFxFieldsProps> = {}): NewPresetFxFieldsProps {
  return {
    templates: TEMPLATES,
    kind: "position",
    fxId: "",
    period: "",
    unit: "beat",
    onFxIdChange: noop,
    onPeriodChange: noop,
    onUnitChange: noop,
    ...overrides,
  };
}

function dialog(fxProps: NewPresetFxFieldsProps | undefined): string {
  return renderToStaticMarkup(
    <NewPresetDialog
      enabled
      label="LA Sweep 2"
      description="부드러운 좌우 2박"
      onLabelChange={noop}
      onDescriptionChange={noop}
      onCreate={noop}
      onCancel={noop}
      fx={fxProps}
    />,
  );
}

function createDisabled(html: string): boolean {
  return /<button type="button" disabled="">만들기<\/button>/.test(html);
}

describe("fxTemplatesForKind", () => {
  it("그 칸의 효과 종류에 쓸 수 있는 틀만 남긴다(서버 kinds 그대로)", () => {
    expect(fxTemplatesForKind(TEMPLATES, "position").map((t) => t.fx_id)).toEqual(["sweep-soft-wide"]);
    expect(fxTemplatesForKind(TEMPLATES, "color").map((t) => t.fx_id)).toEqual(["chase-warm-cool"]);
    expect(fxTemplatesForKind(TEMPLATES, "mixed")).toHaveLength(3);
  });

  it("종류를 모르거나 목록이 없으면 빈 목록", () => {
    expect(fxTemplatesForKind(TEMPLATES, null)).toEqual([]);
    expect(fxTemplatesForKind(undefined, "position")).toEqual([]);
  });
});

describe("isValidFxPeriod / fxRecipeFromDraft", () => {
  it("1 이상의 정수만 받는다", () => {
    expect(isValidFxPeriod("2")).toBe(true);
    for (const bad of ["", "0", "-1", "1.5", "abc", " "]) expect(isValidFxPeriod(bad)).toBe(false);
  });

  it("셋이 다 차면 서버 레시피 모양", () => {
    expect(fxRecipeFromDraft({ fxId: "sweep-soft-wide", period: "2", unit: "beat" })).toEqual({
      fx_id: "sweep-soft-wide",
      period_unit: "beat",
      period_value: 2,
    });
    expect(fxRecipeFromDraft({ fxId: "", period: "2", unit: "beat" })).toBeNull();
    expect(fxRecipeFromDraft({ fxId: "sweep-soft-wide", period: "0", unit: "bar" })).toBeNull();
  });
});

describe("NewPresetDialog — 효과 칸", () => {
  it("효과 틀은 그 종류에 맞는 것만 보이고, 한 바퀴 박/마디 칸이 있다", () => {
    const html = dialog(fx());
    expect(html).toContain('aria-label="효과 틀"');
    expect(html).toContain("부드러운 좌우 스윕");
    expect(html).not.toContain("따뜻함에서 차가움으로");
    expect(html).toContain('aria-label="한 바퀴 길이"');
    expect(html).toContain(">박</option>");
    expect(html).toContain(">마디</option>");
  });

  it("틀·주기가 다 차기 전엔 「만들기」가 꺼져 있다", () => {
    expect(createDisabled(dialog(fx()))).toBe(true);
    expect(createDisabled(dialog(fx({ fxId: "sweep-soft-wide" })))).toBe(true);
    expect(createDisabled(dialog(fx({ period: "2" })))).toBe(true);
    expect(createDisabled(dialog(fx({ fxId: "sweep-soft-wide", period: "2" })))).toBe(false);
  });

  it("다른 종류의 틀 id 가 남아 있으면(종류가 바뀐 칸) 켜지지 않는다", () => {
    expect(createDisabled(dialog(fx({ fxId: "chase-warm-cool", period: "2" })))).toBe(true);
  });

  it("칸의 효과 종류를 모르면 먼저 정하라고 안내하고 켜지지 않는다", () => {
    const html = dialog(fx({ kind: null, fxId: "sweep-soft-wide", period: "2" }));
    expect(html).toContain("효과 종류(위치·색·혼합)를 먼저 정해야");
    expect(createDisabled(html)).toBe(true);
  });

  it("효과가 아닌 칸(fx 없음)은 예전 그대로 — 효과 틀 칸이 없다", () => {
    const html = dialog(undefined);
    expect(html).not.toContain("효과 틀");
    expect(createDisabled(html)).toBe(false);
  });
});

describe("buildBeatGridNewPreset — fx 싣기", () => {
  it("효과면 fx 를 싣고, 아니면 키가 없다", () => {
    const recipe = { fx_id: "sweep-soft-wide", period_unit: "beat" as const, period_value: 2 };
    const withFx = JSON.parse(buildBeatGridNewPreset(1, "BACK", "effect", "LA", "d", undefined, recipe));
    expect(withFx.fx).toEqual(recipe);
    expect("aim" in withFx).toBe(false);
    const without = JSON.parse(buildBeatGridNewPreset(1, "BACK", "color", "LA", "d"));
    expect("fx" in without).toBe(false);
  });
});
