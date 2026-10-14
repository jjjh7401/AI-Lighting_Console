// 반영 대기 배지 값 시험 (카드 t630). DOM 시험대 없음(BeatGrid.test.tsx와
// 같은 관례) — 내보낸 순수 함수만 직접 부른다.
import { describe, expect, it } from "vitest";

import { pendingApplyCountOf } from "./pendingApplyCount";

// 서버 `BeatGridView.unsent_cells` → 상단 바 「⇪ 반영」 배지에 넘길 값.
describe("pendingApplyCountOf", () => {
  it("필드가 없는 옛 서버 응답(undefined)이면 undefined — 배지를 숨긴다", () => {
    expect(pendingApplyCountOf(undefined)).toBeUndefined();
  });

  it("아직 반영 기록이 없으면(null) null — 숫자를 지어내지 않는다", () => {
    expect(pendingApplyCountOf(null)).toBeNull();
  });

  it("빈 배열(반영 뒤 바뀐 칸 없음)이면 0", () => {
    expect(pendingApplyCountOf([])).toBe(0);
  });

  it("두 칸이면 2", () => {
    expect(
      pendingApplyCountOf([
        { group_name: "GROUP-A", bar: 3 },
        { group_name: "GROUP-B", bar: 9 },
      ]),
    ).toBe(2);
  });
});
