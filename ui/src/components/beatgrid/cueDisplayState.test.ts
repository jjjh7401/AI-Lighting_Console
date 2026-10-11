// REQ-LDBEAT-019(a) — 타임라인 큐 막대 4종 상태 판정(순수 함수) 시험.
// SPEC-LDBEAT-001 M9 step 2, 카드 t560. DOM 시험대 없음(BeatGrid.test.tsx와
// 같은 관례) — 내보낸 순수 함수만 직접 부른다.
import { describe, expect, it } from "vitest";

import { cueEditKey, deriveCueDisplayState, editedCueKeysFromUnsent } from "./cueDisplayState";

// 카드 t568 ② — 서버 `BeatGridView.unsent_cells`(마지막 반영 뒤 바뀐 칸,
// t563 공급) → 「고침=초록」 키 집합. 리드 결정: 스냅숏이 없으면 null.
describe("editedCueKeysFromUnsent", () => {
  it("null(아직 반영 기록 없음)이면 초록 칸이 없다", () => {
    expect(editedCueKeysFromUnsent(null).size).toBe(0);
  });

  it("필드가 없는 옛 서버 응답(undefined)도 초록 칸이 없다", () => {
    expect(editedCueKeysFromUnsent(undefined).size).toBe(0);
  });

  it("빈 배열(반영 뒤 바뀐 칸 없음)이면 초록 칸이 없다", () => {
    expect(editedCueKeysFromUnsent([]).size).toBe(0);
  });

  it("여러 칸이면 칸마다 cueEditKey 로 들어간다", () => {
    const keys = editedCueKeysFromUnsent([
      { group_name: "GROUP-A", bar: 3 },
      { group_name: "GROUP-B", bar: 3 },
      { group_name: "GROUP-A", bar: 9 },
    ]);
    expect([...keys].sort()).toEqual(
      [cueEditKey("GROUP-A", 3), cueEditKey("GROUP-B", 3), cueEditKey("GROUP-A", 9)].sort(),
    );
  });
});

describe("deriveCueDisplayState", () => {
  it("꺼진 칸은 다른 신호가 전부 있어도 기본으로 떨어진다", () => {
    expect(
      deriveCueDisplayState({
        isActive: false,
        isEdited: true,
        hasPendingSuggestion: true,
        referencesHighlightedPreset: true,
      }),
    ).toBe("default");
  });

  it("AI 제안 대상이면 다른 신호보다 우선한다", () => {
    expect(
      deriveCueDisplayState({
        isActive: true,
        isEdited: true,
        hasPendingSuggestion: true,
        referencesHighlightedPreset: true,
      }),
    ).toBe("ai-suggestion");
  });

  it("이번 세션에 고친 칸은 초록(edited)이다", () => {
    expect(
      deriveCueDisplayState({
        isActive: true,
        isEdited: true,
        hasPendingSuggestion: false,
        referencesHighlightedPreset: true,
      }),
    ).toBe("edited");
  });

  it("강조된 프리셋을 쓰는 칸은 노랑(same-preset)이다", () => {
    expect(
      deriveCueDisplayState({
        isActive: true,
        isEdited: false,
        hasPendingSuggestion: false,
        referencesHighlightedPreset: true,
      }),
    ).toBe("same-preset");
  });

  it("아무 신호도 없으면 기본이다", () => {
    expect(
      deriveCueDisplayState({
        isActive: true,
        isEdited: false,
        hasPendingSuggestion: false,
        referencesHighlightedPreset: false,
      }),
    ).toBe("default");
  });
});

describe("cueEditKey", () => {
  it("콘솔 그룹 이름과 마디를 구분자로 묶는다", () => {
    expect(cueEditKey("MOVER-D", 7)).toBe("MOVER-D|7");
  });

  it("다른 그룹·같은 마디는 다른 키다", () => {
    expect(cueEditKey("MOVER-D", 7)).not.toBe(cueEditKey("MOVER-U", 7));
  });

  it("같은 그룹·다른 마디는 다른 키다", () => {
    expect(cueEditKey("MOVER-D", 7)).not.toBe(cueEditKey("MOVER-D", 8));
  });
});
