// 타임라인 큐 막대의 네 가지 표시 상태(REQ-LDBEAT-019(a)) — "고친 막대는
// 초록·같은 프리셋을 쓰는 막대는 노랑·AI 제안 막대는 점선으로 구분된다".
// SPEC-LDBEAT-001 M9 step 2, 카드 t560.
//
// 이 모듈은 어느 모양(색·테두리)으로 그릴지 정하지 않는다 — 그 매핑은
// BeatGrid.tsx·styles.css의 소관이고, 여기서는 "넷 중 어떤 상태냐"만
// 순수하게 판정한다. 호출부가 넘긴 불리언 신호만 본다 — 추측 0건(예:
// "같은 프리셋" 판정은 호출부의 기존 `cueReferencesPreset`가 이미 계산해
// `referencesHighlightedPreset`로 넘긴다, 중복 구현 금지).
export type CueDisplayState = "edited" | "same-preset" | "ai-suggestion" | "default";

export interface CueDisplayStateInput {
  /** 기존 `cueIsActive(cue.label)`와 같은 축 — 꺼진 칸은 네 상태 구분과
   * 무관하게 항상 기본으로 본다. */
  isActive: boolean;
  /** 이번 세션에 이 칸을 고쳤는가(로컬 신호) — "서버가 실제로 받아들였나"
   * 가 아니라 "고치기를 시도했다"는 뜻이다. 추적 자체는 이 함수 밖
   * (호출부가 Set 등으로 관리)에서 한다. */
  isEdited: boolean;
  /** 이 칸이 보류 중인 AI 제안의 대상인가. */
  hasPendingSuggestion: boolean;
  /** 지금 강조된 프리셋(프리셋 서랍/칩에서 고른 값)을 이 칸이 쓰는가. */
  referencesHighlightedPreset: boolean;
}

/** 우선순위: 꺼짐 > AI 제안 > 고침 > 같은 프리셋 > 기본. 네 상태를
 * 서로 배타적인 하나의 값으로 돌려준다(REQ-LDBEAT-019(a) "구분된다"). */
export function deriveCueDisplayState(input: CueDisplayStateInput): CueDisplayState {
  if (!input.isActive) return "default";
  if (input.hasPendingSuggestion) return "ai-suggestion";
  if (input.isEdited) return "edited";
  if (input.referencesHighlightedPreset) return "same-preset";
  return "default";
}

/** 로컬 "고침" 추적 Set의 키 꼴 — 콘솔 그룹 이름 + 마디(한 트랙 안에서
 * 마디는 유일 키, REQ-LDBEAT-004 "줄 하나 = 콘솔 그룹 하나"). 호출부가
 * `Set<string>`에 이 키를 담아 `isEdited` 판정에 쓴다. */
export function cueEditKey(groupName: string, bar: number): string {
  return `${groupName}|${bar}`;
}
