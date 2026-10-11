// 「이 마디 한눈에」 표 칼럼(밝기·위치·색·움직임·전환) 칸 값 + 「바뀐 것」
// 표시(REQ-LDBEAT-023(a)(c)(d), 시안 `cellHTML`/`rowHTML`/`changedTxt`).
// SPEC-LDBEAT-001 M9 step 2·4(나)·6, 카드 t560 후속.
//
// 역할별 칼럼 노출은 `roleFields.ts`의 `roleFieldHints`(오른쪽 큐 편집
// 칸과 같은 판정, 중복 없음)를 그대로 쓴다 — 시안의 특정 역할 목록
// (foh/wash/side/blind/strobe 등)을 다시 베끼지 않는다(일반화,
// feedback-generalize-beyond-test-rig). 프리셋 번호가 있는 칸은 서랍
// (`drawerSections`)에서 설명·사용 수를 찾아 칩으로 보여준다
// (`presetChipTooltip.ts` `findDrawerEntryByPresetNo`) — 못 찾으면
// (서랍 미수신 등) 번호만 보여준다(지어내지 않음).
import type { BeatGridCue, BeatGridDrawerSection } from "../../protocol";
import { findDrawerEntryByPresetNo, formatPresetChipTooltip } from "./presetChipTooltip";
import { roleFieldHints } from "./roleFields";

/** `BeatGrid.tsx` `UNSET_FIELD_LABEL`과 같은 문구("미정") — 구조화
 * 필드가 있지만 값이 비어 있을 때. 모듈 순환 참조를 피하려고 문구 하나만
 * 복제한다(로직이 아니라 라벨 상수라 분기 위험 없음). */
const UNSET = "미정";
/** 역할이 그 칼럼을 쓰지 않을 때(mockup `cellHTML`의 "—"), 또는 칸 자체가
 * 없을 때(아직 선언 안 됨). */
const NOT_APPLICABLE = "—";

export type GlanceCellValue =
  | { kind: "chip"; presetNo: string; label: string; tooltip: string }
  | { kind: "text"; text: string };

function chipOrUnset(presetNo: string | null, sections: BeatGridDrawerSection[] | null): GlanceCellValue {
  if (!presetNo) return { kind: "text", text: UNSET };
  const entry = findDrawerEntryByPresetNo(sections, presetNo);
  return {
    kind: "chip",
    presetNo,
    label: entry ? `${presetNo} ${entry.name}` : presetNo,
    tooltip: formatPresetChipTooltip(entry?.description, entry?.usage_count ?? 0),
  };
}

/** 밝기 칸 — 값(%)/디머 프리셋/디머 효과 세 모드 중 하나(REQ-LDBEAT-006
 * (i-2)). 프리셋·효과 모드는 칩으로, 값 모드는 퍼센트 텍스트로. */
export function brightnessCell(cue: BeatGridCue | null, sections: BeatGridDrawerSection[] | null): GlanceCellValue {
  if (!cue) return { kind: "text", text: NOT_APPLICABLE };
  const b = cue.brightness;
  if (b.mode === "value") {
    return { kind: "text", text: b.value_percent === null ? UNSET : `${b.value_percent}%` };
  }
  if (b.mode === "dimmer_preset" || b.mode === "dimmer_effect") {
    return chipOrUnset(b.preset_no, sections);
  }
  return { kind: "text", text: UNSET };
}

/** 위치 칸 — 역할이 위치를 쓰지 않으면(`roleFieldHints`) 대시. */
export function positionCell(
  cue: BeatGridCue | null,
  role: string | null,
  sections: BeatGridDrawerSection[] | null,
): GlanceCellValue {
  if (!roleFieldHints(role).includes("위치")) return { kind: "text", text: NOT_APPLICABLE };
  if (!cue) return { kind: "text", text: NOT_APPLICABLE };
  return chipOrUnset(cue.position_preset_no, sections);
}

/** 색 칸 — 역할이 색을 쓰지 않으면(무빙, `roleFieldHints`) 대시. */
export function colorCell(
  cue: BeatGridCue | null,
  role: string | null,
  sections: BeatGridDrawerSection[] | null,
): GlanceCellValue {
  if (!roleFieldHints(role).includes("색")) return { kind: "text", text: NOT_APPLICABLE };
  if (!cue) return { kind: "text", text: NOT_APPLICABLE };
  return chipOrUnset(cue.color_preset_no, sections);
}

/** 움직임 칸 — 무빙 역할에서만(`roleFieldHints`) 효과 프리셋을 보여준다. */
export function movementCell(
  cue: BeatGridCue | null,
  role: string | null,
  sections: BeatGridDrawerSection[] | null,
): GlanceCellValue {
  if (!roleFieldHints(role).includes("움직임")) return { kind: "text", text: NOT_APPLICABLE };
  if (!cue) return { kind: "text", text: NOT_APPLICABLE };
  return chipOrUnset(cue.effect_preset_no, sections);
}

/** 전환 칸(mockup `rowHTML` 여섯째 칸) — 지금 보는 마디가 그 칸의
 * **시작** 마디이고(곡 전체의 첫 칸이 아닐 때만) 들어오는 전환(들어올
 * 때 마디 수)을 보여준다. 호출부가 `isTransitionBar`를 계산해 넘긴다
 * (`cue.bar === viewBar && track.cues.indexOf(cue) > 0` — 이 모듈은
 * `track.cues` 전체를 모르므로 그 판정은 호출부 몫). 그 밖(칸 중간 마디)
 * 은 "유지". */
export function transitionCell(cue: BeatGridCue | null, isTransitionBar: boolean): GlanceCellValue {
  if (!cue) return { kind: "text", text: NOT_APPLICABLE };
  if (!isTransitionBar) return { kind: "text", text: "유지" };
  return { kind: "text", text: cue.entry.fade_bars === null ? UNSET : `${cue.entry.fade_bars}마디` };
}

/** 「바뀐 것」 표시(mockup `changedTxt`) — derivable한 것만 보여준다
 * (지어내지 않음): 구조화 필드 중 실제로 다른 것의 이름을 나열한다.
 * `isFirstBarOfRange`면(곡 표시 범위의 첫 마디) 비교할 "이전"이 없다는
 * 뜻이라 늘 빈 문자열(mockup의 `b===0` 가드와 같다). */
export function changedFieldsLabel(
  previousCue: BeatGridCue | null,
  currentCue: BeatGridCue | null,
  isFirstBarOfRange: boolean,
): string {
  if (!currentCue || isFirstBarOfRange) return "";
  if (!previousCue) return "● 여기서 시작";
  if (previousCue === currentCue) return "";
  const changed: string[] = [];
  if (JSON.stringify(previousCue.brightness) !== JSON.stringify(currentCue.brightness)) changed.push("밝기");
  if (previousCue.position_preset_no !== currentCue.position_preset_no) changed.push("위치");
  if (previousCue.color_preset_no !== currentCue.color_preset_no) changed.push("색");
  if (previousCue.effect_preset_no !== currentCue.effect_preset_no) changed.push("움직임");
  return `● ${changed.length > 0 ? changed.join("·") : "큐"} 바뀜`;
}
