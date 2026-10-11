// 카드 t594 — 「＋ 새 프리셋 만들기」 창의 "색" 필드: R·G·B(0~100%) + 미리보기.
// 이 프로젝트는 jsdom 이 없다 — 순수 함수와 `renderToStaticMarkup`으로 잰다.
import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

import { NewPresetDialog } from "./BeatGrid";
import {
  colorSwatchValue,
  isValidColorChannel,
  type NewPresetColorFieldsProps,
} from "./beatgrid/newPresetColor";
import { buildBeatGridNewPreset } from "../protocol";

const noop = () => {};

function color(overrides: Partial<NewPresetColorFieldsProps> = {}): NewPresetColorFieldsProps {
  return {
    r: "",
    g: "",
    b: "",
    onRChange: noop,
    onGChange: noop,
    onBChange: noop,
    ...overrides,
  };
}

function dialog(colorProps: NewPresetColorFieldsProps | undefined): string {
  return renderToStaticMarkup(
    <NewPresetDialog
      enabled
      label="LA Wave"
      description="따뜻한 빨강"
      onLabelChange={noop}
      onDescriptionChange={noop}
      onCreate={noop}
      onCancel={noop}
      color={colorProps}
    />,
  );
}

function createDisabled(html: string): boolean {
  return /<button type="button" disabled="">만들기<\/button>/.test(html);
}

describe("isValidColorChannel", () => {
  it("0~100 범위의 수만 받는다", () => {
    expect(isValidColorChannel("0")).toBe(true);
    expect(isValidColorChannel("100")).toBe(true);
    expect(isValidColorChannel("50.5")).toBe(true);
    for (const bad of ["", "-1", "101", "abc", " ", "NaN"]) {
      expect(isValidColorChannel(bad)).toBe(false);
    }
  });
});

describe("colorSwatchValue", () => {
  it("셋이 다 차면 0~255 환산 rgb() 문자열", () => {
    expect(colorSwatchValue({ r: "100", g: "0", b: "0" })).toBe("rgb(255, 0, 0)");
    expect(colorSwatchValue({ r: "0", g: "0", b: "0" })).toBe("rgb(0, 0, 0)");
  });

  it("하나라도 모자라거나 범위 밖이면 null", () => {
    expect(colorSwatchValue({ r: "", g: "0", b: "0" })).toBeNull();
    expect(colorSwatchValue({ r: "101", g: "0", b: "0" })).toBeNull();
  });
});

describe("NewPresetDialog — 색 칸", () => {
  it("R·G·B 세 입력과 미리보기 조각이 있다", () => {
    const html = dialog(color({ r: "50", g: "0", b: "0" }));
    expect(html).toContain('aria-label="R (%)"');
    expect(html).toContain('aria-label="G (%)"');
    expect(html).toContain('aria-label="B (%)"');
    expect(html).toContain("beat-grid-new-preset-color-swatch");
  });

  it("셋이 다 차기 전엔 「만들기」가 꺼져 있다", () => {
    expect(createDisabled(dialog(color()))).toBe(true);
    expect(createDisabled(dialog(color({ r: "50" })))).toBe(true);
    expect(createDisabled(dialog(color({ r: "50", g: "0" })))).toBe(true);
    expect(createDisabled(dialog(color({ r: "50", g: "0", b: "0" })))).toBe(false);
  });

  it("범위 밖 값은 켜지지 않고 안내가 보인다", () => {
    const html = dialog(color({ r: "101", g: "0", b: "0" }));
    expect(createDisabled(html)).toBe(true);
    expect(html).toContain("0~100 범위의 수예요");
  });

  it("색이 아닌 칸(color 없음)은 예전 그대로 — R·G·B 칸이 없다", () => {
    const html = dialog(undefined);
    expect(html).not.toContain('aria-label="R (%)"');
    expect(createDisabled(html)).toBe(false);
  });
});

describe("buildBeatGridNewPreset — rgb 싣기", () => {
  it("색이면 rgb 를 싣고, 아니면 키가 없다", () => {
    const rgb = { r: 50, g: 0, b: 0 };
    const withRgb = JSON.parse(
      buildBeatGridNewPreset(1, "BACK", "color", "LA", "d", undefined, undefined, rgb),
    );
    expect(withRgb.rgb).toEqual(rgb);
    expect("aim" in withRgb).toBe(false);
    expect("fx" in withRgb).toBe(false);
    const without = JSON.parse(buildBeatGridNewPreset(1, "BACK", "position", "LA", "d"));
    expect("rgb" in without).toBe(false);
  });
});
