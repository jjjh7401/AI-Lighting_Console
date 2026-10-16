/** 격자 막대 표현 — 시안(`reports/ldbeat-runbook-ui-proposal-20261008.html`)의
 * `.clip .ib`(아래 흰 밝기 선)·`.wave`(우상단 모양 아이콘)·`.s`(위치·밝기 글자).
 *
 * 세 요소 모두 구조화 필드만 본다. 칸의 `label` 글자를 파싱해 값을 역산하지
 * 않고(protocol.ts `BeatGridCue` — REQ-LDBEAT-006(ii-2)), 없는 값은 그리지
 * 않는다. 그래서 아래 함수들은 "그릴 것이 없음"을 `null`로 돌려준다.
 *
 * 계획 표시(리드 결정 2026-10-16, 콘솔에 아직 없음) — 계획 색 칸은 색을 칠하되 점선 테두리와
 * 제목 글로 구분하고, 콘솔 번호가 없는 디머·위치 자리는 계획 이름을 흐리게 보인다. */
import { Fragment } from "react";

import type { BeatGridCue } from "../../protocol";
import { presetDisplayName } from "./glanceCells";
import { cueRgbHex } from "./presetColorHex";

/** 아래쪽 흰 밝기 선의 너비(%). 값 모드(`value`)의 `value_percent`만 쓴다.
 * 디머 프리셋은 퍼센트가 아니라서 선을 긋지 않는다. */
export function brightnessLinePercent(cue: BeatGridCue): number | null {
  const { mode, value_percent: value } = cue.brightness;
  if (mode !== "value" || value === null || !Number.isFinite(value)) return null;
  return Math.min(100, Math.max(0, value));
}

/** 시안에 아이콘이 있는 모양만 그린다. 서버가 주는 `effect_shape`(펄스·체이스·웨이브·
 * 스윕)를 먼저 읽고, 없으면 구조화 필드 `app_movement.shape`(웨이브·스윕)로 간다.
 * 원·플라이아웃·발리후는 시안에 아이콘이 없어 아직 그리지 않는다. */
export type CueShapeIcon = "pulse" | "chase" | "wave" | "sweep";

/** 그릴 수 있는 모양이면 그 모양, 아니면 `null`. 모르는 값은 없는 것과 같다. */
function shapeIconOf(shape: string | null | undefined): CueShapeIcon | null {
  return shape === "pulse" || shape === "chase" || shape === "wave" || shape === "sweep" ? shape : null;
}

export function effectShapeIcon(cue: BeatGridCue): CueShapeIcon | null {
  return shapeIconOf(cue.effect_shape) ?? shapeIconOf(cue.app_movement?.shape);
}

/** 위치·밝기 짧은 글자. 값이 없는 쪽은 `null`이고, 「—」 같은 자리표시도 쓰지 않는다. */
export function barShortText(cue: BeatGridCue): { position: string | null; brightness: string | null } {
  const { mode, value_percent: value, preset_no: presetNo } = cue.brightness;
  // 위치 번호 옆에 콘솔 프리셋 이름(시안 「2.46 Back Aim」)을 붙인다 — 이름이 없으면 번호만.
  const positionNo = cue.position_preset_no ? `위치 ${cue.position_preset_no}` : null;
  const positionName = presetDisplayName(cue.position_preset_name);
  const position = positionNo !== null && positionName !== null ? `${positionNo} ${positionName}` : positionNo;
  let brightness: string | null = null;
  if (mode === "value" && value !== null && Number.isFinite(value)) {
    brightness = `${value}%`;
  } else if ((mode === "dimmer_preset" || mode === "dimmer_effect") && presetNo) {
    brightness = presetNo;
  }
  return { position, brightness };
}

/** 둘째 줄 한 조각. `planned` 가 참이면 콘솔 번호가 없어 계획 이름을 흐리게 보인다. */
export interface CueMetaPart {
  text: string;
  planned: boolean;
}

/** 둘째 줄 조각 — 위치(번호와 이름, 번호가 없으면 계획 이름) · 밝기(값 또는 디머 번호) ·
 * 계획 디머 이름. 값이 없는 조각은 빠지고, 계획 이름은 콘솔 번호가 없을 때만 나온다. */
export function cueBarMetaParts(cue: BeatGridCue): CueMetaPart[] {
  const { position, brightness } = barShortText(cue);
  const parts: CueMetaPart[] = [];
  if (position !== null) {
    parts.push({ text: position, planned: false });
  } else if (cue.planned_position_name && !cue.position_preset_no) {
    parts.push({ text: `위치 ${cue.planned_position_name}`, planned: true });
  }
  if (brightness !== null) parts.push({ text: brightness, planned: false });
  if (cue.planned_dimmer_name && !cue.brightness.preset_no) {
    parts.push({ text: cue.planned_dimmer_name, planned: true });
  }
  return parts;
}

/** 두 번째 줄에 올릴 글자(위치 · 밝기 · 계획 이름). 조각이 하나도 없으면 빈 문자열. */
export function cueBarMetaText(cue: BeatGridCue): string {
  return cueBarMetaParts(cue)
    .map((part) => part.text)
    .join(" · ");
}

/** 모양 아이콘이나 두 번째 줄이 있을 때만 붙는 modifier 클래스. 버튼 레이아웃
 * (오른쪽 여백·줄 높이)은 그 칸에만 바뀐다. */
export function cueBarVisualClass(cue: BeatGridCue): string {
  return `${effectShapeIcon(cue) !== null ? " has-cue-shape" : ""}${
    cueBarMetaText(cue) !== "" ? " has-cue-meta" : ""
  }`;
}

/** 계획 색 표시(리드 결정, 콘솔에 아직 없음) — `color_planned` 이고 `color_rgb` 가 유효한 색일 때만 참. */
export function isCuePlannedColor(cue: BeatGridCue): boolean {
  return cue.color_planned === true && cueRgbHex(cue.color_rgb) !== undefined;
}

/** 계획 색 칸의 제목 글 — 콘솔에 아직 없는 색임을 알린다. */
export const CUE_PLANNED_COLOR_TITLE = "계획 색 — 아직 콘솔에 없음";

/** 켜진 계획 색 칸의 modifier 클래스(점선 테두리). 꺼진 칸·콘솔 색 칸에는 붙지 않는다. */
export function cuePlannedClassName(cue: BeatGridCue, active: boolean): string {
  return active && isCuePlannedColor(cue) ? " is-color-planned" : "";
}

/** 켜진 계획 색 칸의 제목 글 덧붙임 — 「· 계획 색 — 아직 콘솔에 없음」. 해당 없으면 빈 문자열. */
export function cuePlannedTitleSuffix(cue: BeatGridCue, active: boolean): string {
  return active && isCuePlannedColor(cue) ? ` · ${CUE_PLANNED_COLOR_TITLE}` : "";
}

/** 둘째 줄에 쓰는 밝기 글자의 원래 값 — 값 모드는 「40%」, 디머 프리셋은 번호. 없으면 `null`. */
function brightnessToken(cue: BeatGridCue): string | null {
  const { mode, value_percent: value, preset_no: presetNo } = cue.brightness;
  if (mode === "value" && value !== null && Number.isFinite(value)) return `${value}%`;
  if ((mode === "dimmer_preset" || mode === "dimmer_effect") && presetNo) return presetNo;
  return null;
}

/** 막대의 이름 글자. 칸 글자 안에 둘째 줄과 같은 밝기 글자(「40%」·디머 번호)가 있으면 그 글자만 뗀다 —
 * 밝기는 둘째 줄에 한 번만 보이게 하려는 표시 정리다. 다른 숫자의 일부(「140%」·「11.1」)는 건드리지 않고,
 * 떼고 나서 아무것도 안 남으면 원래 글자를 쓴다. */
export function barNameText(cue: BeatGridCue): string {
  const token = brightnessToken(cue);
  if (token === null) return cue.label;
  const escaped = token.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const stripped = cue.label.replace(new RegExp(`(?<![\\d.])${escaped}(?![\\d.])`, "g"), "");
  const name = stripped.replace(/\s+/g, " ").trim();
  return name === "" ? cue.label : name;
}

/** 시안 `.wave` 자리(18×11, 흰색 선 1.5). 펄스는 시안의 ЛЛ 경로 그대로다. 체이스는
 * 시안에 따로 아이콘이 없어(프로토타입도 펄스 모양을 쓴다) 한 칸씩 밀리는 세 획으로
 * 그렸다. 스윕은 같은 자리의 화살표. */
const SHAPE_PATH: Record<CueShapeIcon, string> = {
  pulse: "M1 9 H4 V2 H7 V9 H10 V2 H13 V9 H16",
  chase: "M1 9 H6 M6 6 H11 M11 3 H16",
  wave: "M1 6 C4 0 7 0 9 6 S14 12 17 6",
  sweep: "M2 5.5 H15 M11 2 L15 5.5 L11 9",
};

/** 격자 막대 안의 세 요소. 그릴 것이 없으면 아무것도 내지 않는다. */
export function CueBarVisual({ cue }: { cue: BeatGridCue }) {
  const linePercent = brightnessLinePercent(cue);
  const shape = effectShapeIcon(cue);
  const parts = cueBarMetaParts(cue);
  return (
    <>
      {linePercent !== null && (
        <span className="beat-grid-cue-ib" style={{ width: `${linePercent}%` }} aria-hidden="true" />
      )}
      {shape !== null && (
        <svg
          className="beat-grid-cue-shape"
          data-shape={shape}
          width={18}
          height={11}
          viewBox="0 0 18 11"
          aria-hidden="true"
          focusable="false"
        >
          <path d={SHAPE_PATH[shape]} fill="none" stroke="#fff" strokeWidth={1.5} />
        </svg>
      )}
      {parts.length > 0 && (
        <span className="beat-grid-cue-meta">
          {parts.map((part, index) => (
            <Fragment key={`${index}:${part.text}`}>
              {index > 0 && " · "}
              {part.planned ? (
                <span className="is-planned-name" title="계획 이름 — 아직 콘솔에 없음">
                  {part.text}
                </span>
              ) : (
                part.text
              )}
            </Fragment>
          ))}
        </span>
      )}
    </>
  );
}
