// 색 프리셋 목표 RGB(0~100%) → 화면 색. 서버 `color_preset_rgb` 와 같은 범위(0~100%)를
// 쓰고, 값이 없거나 범위 밖이면 `undefined` 를 돌려 지어내지 않는다.
import type { BeatGridPresetRgb } from "../../protocol";

const isPercent = (value: number) => Number.isFinite(value) && value >= 0 && value <= 100;

/** 세 채널이 모두 0~100% 면 `#rrggbb`, 하나라도 없거나 범위 밖이면 `undefined`. */
export function presetRgbHex(rgb: BeatGridPresetRgb | null | undefined): string | undefined {
  if (!rgb) return undefined;
  const channels = [rgb.r, rgb.g, rgb.b];
  if (!channels.every(isPercent)) return undefined;
  return `#${channels.map((value) => Math.round((value / 100) * 255).toString(16).padStart(2, "0")).join("")}`;
}

/** 칸에 실린 색 `color_rgb` = [r, g, b] 배열(0~100%) → `#rrggbb`. 길이가 3이 아니거나 범위 밖이면 `undefined`. */
export function cueRgbHex(rgb: readonly number[] | null | undefined): string | undefined {
  if (!rgb || rgb.length !== 3) return undefined;
  return presetRgbHex({ r: rgb[0], g: rgb[1], b: rgb[2] });
}

/** 곡 격자의 `preset_colors` 전체를 번호 → hex 표로. 색을 모르는 번호는 표에 넣지 않는다. */
export function presetColorHexMap(
  presetColors: Readonly<Record<string, BeatGridPresetRgb | null | undefined>> | null | undefined,
): Record<string, string> {
  const out: Record<string, string> = {};
  if (!presetColors) return out;
  for (const [presetNo, rgb] of Object.entries(presetColors)) {
    const hex = presetRgbHex(rgb);
    if (hex !== undefined) out[presetNo] = hex;
  }
  return out;
}
