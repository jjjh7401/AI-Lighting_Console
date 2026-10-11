// 「이 마디 한눈에」 표 칸·줄 클릭 → 오른쪽 편집 칸 초점(REQ-LDBEAT-021(a),
// plan.md M9 step 4(나)). SPEC-LDBEAT-001, 카드 t560.
//
// 이 식별자는 "그 자리에서 값을 바꾸는" 데이터가 아니다 — 트랙 이름·마디·
// (있으면) 필드 이름만 담아 위로 올려 보내는 "얇은" 모양이다. 호출부
// (BeatGrid.tsx)는 이 식별자를 받아 기존 `selected`(타임라인 막대를 눌렀을
// 때와 같은 상태)를 그대로 설정해 오른쪽 칸을 그 항목에 초점을 두고
// 연다 — 새 서버 요청은 0건이다(AC-LDBEAT-021(a)).
export type GlanceFocusField = "밝기" | "위치" | "색" | "움직임" | "전환" | null;

export interface GlanceFocusTarget {
  groupName: string;
  bar: number;
  field: GlanceFocusField;
}

export function buildGlanceFocusTarget(
  groupName: string,
  bar: number,
  field: GlanceFocusField = null,
): GlanceFocusTarget {
  return { groupName, bar, field };
}

/** 카드 t560 — 표 칼럼을 t561 편집 칸의 초점 입력으로 옮긴다. 「전환」
 * 칼럼은 같은 편집 칸을 전환 화면으로 연다(REQ-LDBEAT-020(d)) — 초점
 * 필드는 없다. 나머지 칼럼은 큐 편집 화면을 열고 그 필드에 초점을 둔다.
 * 줄 이름 칸(`field === null`)은 초점 없이 연다. */
export interface GlanceFocusAction {
  transition: boolean;
  focusField: Exclude<GlanceFocusField, "전환" | null> | null;
}

export function glanceFocusAction(field: GlanceFocusField): GlanceFocusAction {
  if (field === "전환") return { transition: true, focusField: null };
  return { transition: false, focusField: field };
}
