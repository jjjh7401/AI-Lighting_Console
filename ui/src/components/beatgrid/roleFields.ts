// 역할별 조건부 노출(REQ-LDBEAT-004(c)) — 무빙만 "움직임"을 더한다. "색"은 무빙을 포함해
// 모든 역할에 있다: 무빙의 색은 무대(SCENE) 구간 색을 따른다(규칙서 effect-arrangement-rules §2).
//
// 카드 t560 후속(SPEC-LDBEAT-001 M9 step 2·4(나)·6) — `BeatGrid.tsx`에
// 있던 함수를 이 모듈로 옮겼다(로직 이동, 복제 아님). 오른쪽 큐 편집
// 칸(`BeatGrid.tsx`)과 「이 마디 한눈에」 표 칼럼(`glanceCells.ts`)이
// 이제 같은 판정 함수 하나를 그대로 공유한다 — 두 자리가 서로 다른 역할
// 목록을 베껴 쓰다 어긋나는 일을 막는다.
export function roleFieldHints(role: string | null): string[] {
  const hints: string[] = ["밝기"];
  if (role === "mover" || role === "back" || role === "side" || role === "wash") hints.push("위치");
  hints.push("색");
  if (role === "mover") hints.push("움직임");
  return hints;
}
