// 프리셋 칩 툴팁 문자열(REQ-LDBEAT-023(c)) — "그 프리셋의 설명 텍스트와
// 이 곡에서 쓰는 큐 수를 함께" 보여준다. SPEC-LDBEAT-001 M9 step 6, 카드
// t560.
//
// §Gaps(카드 t560 보고) — 콘솔이 실제로 돌려주는 프리셋 "설명 텍스트"
// (시안 원문 예시 「펄스 30↔60 · 4박」 꼴)는 지금 클라이언트 모델
// (`BeatGridDrawerEntry`)에 없다 — `entry.name`은 콘솔이 읽은 짧은
// **이름**일 뿐 효과 설명이 아니다(`server/design/beat_grid_presets.py`
// `build_preset_drawer`가 콘솔 슬롯 이름을 그대로 옮긴다, 확인됨). 그래서
// 이 함수는 설명 텍스트가 없을 때(`null`/`undefined`/빈 문자열) 사용 큐
// 수만 보여준다 — 그 예시 문자열을 지어내 채우지 않는다(REQ-LDBEAT-015(f)
// 와 같은 원칙). 설명 데이터가 실제로 생기면(서버가 그 필드를 채우면)
// 호출부가 그 값을 그대로 넘기면 된다 — 이 함수 자체는 바꿀 필요 없다.
export function formatPresetChipTooltip(
  description: string | null | undefined,
  usageCount: number,
): string {
  const usagePart = `이 곡에서 큐 ${usageCount}곳 사용`;
  const trimmed = description?.trim();
  if (!trimmed) return usagePart;
  return `${trimmed} · ${usagePart}`;
}
