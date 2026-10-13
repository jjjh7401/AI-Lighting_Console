// 반영 대기 배지 값 (카드 t630). 서버 `BeatGridView.unsent_cells`를 상단 바
// 「⇪ 반영」 배지가 읽는 모양으로 바꾼다 — DOM 무관한 순수 함수.
import type { BeatGridUnsentCell } from "../../protocol";

/** `unsent_cells` → 배지 값. 숫자는 반영 기록이 있을 때만 세고 지어내지 않는다.
 * `undefined`(필드 없는 옛 서버 응답)는 배지를 숨기고, `null`(아직 반영 기록
 * 없음)은 「—」로 보이며, 배열은 그 길이다. */
export function pendingApplyCountOf(
  unsentCells: BeatGridUnsentCell[] | null | undefined,
): number | null | undefined {
  return unsentCells === null ? null : unsentCells?.length;
}
