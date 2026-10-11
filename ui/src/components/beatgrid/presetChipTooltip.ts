// 프리셋 칩 툴팁 문자열(REQ-LDBEAT-023(c)) — "그 프리셋의 설명 텍스트와
// 이 곡에서 쓰는 큐 수를 함께" 보여준다. SPEC-LDBEAT-001 M9 step 6, 카드
// t560.
//
// 카드 t569(리드 결정 B) — 설명의 출처는 서버가 `description_source`로
// 알려 준다. "app"이면 앱이 그 프리셋을 만들 때 저장한 설명, "show"면
// 콘솔에서 읽은 쇼 프리셋이다. 칩 위 글자가 이미 콘솔 이름이라 "show"는
// 이름을 툴팁에 다시 쓰지 않고 출처만 붙인다. 출처도 설명도 없으면 사용
// 큐 수만 보여준다 — 지어내지 않는다(REQ-LDBEAT-015(f)와 같은 원칙).
// 콘솔 NOTE 는 읽지 않는다(t569 실측: 칩 서랍 34칸 모두 빈 값).
import type {
  BeatGridDrawerEntry,
  BeatGridDrawerSection,
  PresetDescriptionSource,
} from "../../protocol";

const SHOW_PRESET_SOURCE_LABEL = "쇼에 있던 프리셋";

export function formatPresetChipTooltip(
  description: string | null | undefined,
  usageCount: number,
  source?: PresetDescriptionSource | null,
): string {
  const usagePart = `이 곡에서 큐 ${usageCount}곳 사용`;
  const trimmed = description?.trim();
  if (trimmed) return `${trimmed} · ${usagePart}`;
  if (source === "show") return `${SHOW_PRESET_SOURCE_LABEL} · ${usagePart}`;
  return usagePart;
}

// 카드 t560 후속(REQ-LDBEAT-023(c), plan.md M9 step 6) — 「이 마디 한눈에」
// 표 칸(밝기·위치·색·움직임)의 프리셋 칩은 그 칸이 참조하는 preset_no만
// 가지고, 어느 서랍 섹션(위치·색·디머)에 속하는지는 미리 모른다(예:
// 칸의 `effect_preset_no`는 위치 풀의 효과 번호대다, `BeatGrid.tsx`
// `buildEffectPresetChanges` 주석과 같은 사실). 그래서 풀 이름 없이
// 번호 하나로 모든 섹션을 가로질러 찾는다.
/** 모든 서랍 섹션을 가로질러 `preset_no`로 항목을 찾는다. 섹션이
 * 없거나(`null`, 서랍을 아직 못 받음) 어느 섹션에도 없으면 `null`
 * (지어내지 않는다 — 찾지 못했다는 사실 자체가 정보다). */
export function findDrawerEntryByPresetNo(
  sections: BeatGridDrawerSection[] | null,
  presetNo: string,
): BeatGridDrawerEntry | null {
  if (!sections) return null;
  for (const section of sections) {
    const entry = section.entries.find((candidate) => candidate.preset_no === presetNo);
    if (entry) return entry;
  }
  return null;
}
