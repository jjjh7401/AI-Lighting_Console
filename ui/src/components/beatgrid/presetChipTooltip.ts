// 프리셋 칩 툴팁 문자열(REQ-LDBEAT-023(c)) — "그 프리셋의 설명 텍스트와
// 이 곡에서 쓰는 큐 수를 함께" 보여준다. SPEC-LDBEAT-001 M9 step 6, 카드
// t560.
//
// §Gaps(카드 t560 보고, 카드 t568 재조사로 재확인) — 콘솔이 실제로
// 돌려주는 프리셋 "설명 텍스트"(시안 원문 예시 「펄스 30↔60 · 4박」 꼴)는
// 읽는 경로가 이 저장소에 없다 — `entry.name`은 콘솔이 읽은 짧은
// **이름**일 뿐 효과 설명이 아니고(`server/design/beat_grid_presets.py`
// `build_preset_drawer`가 콘솔 슬롯 이름을 그대로 옮긴다, 확인됨),
// `paged_pool_children`(t480)이 돌려받는 자식 필드는 슬롯 번호·이름뿐이다
// (t568 조사, 새 콘솔 프로브 없이는 못 채움). 그래서 서버는 이 필드를
// 명시적 `null`로 보내고(카드 t568), 이 함수는 설명 텍스트가 없을 때
// (`null`/`undefined`/빈 문자열) 사용 큐 수만 보여준다 — 그 예시 문자열을
// 지어내 채우지 않는다(REQ-LDBEAT-015(f)와 같은 원칙). 설명 데이터가
// 실제로 생기면(서버가 새 프로브로 그 값을 읽게 되면) 호출부가 그 값을
// 그대로 넘기면 된다 — 이 함수 자체는 바꿀 필요 없다.
import type { BeatGridDrawerEntry, BeatGridDrawerSection } from "../../protocol";

export function formatPresetChipTooltip(
  description: string | null | undefined,
  usageCount: number,
): string {
  const usagePart = `이 곡에서 큐 ${usageCount}곳 사용`;
  const trimmed = description?.trim();
  if (!trimmed) return usagePart;
  return `${trimmed} · ${usagePart}`;
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
