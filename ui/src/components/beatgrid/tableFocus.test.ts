// REQ-LDBEAT-021(a) / plan.md M9 step 4(나) — 「이 마디 한눈에」 표 칸·줄
// 클릭이 그 자리에서 고치지 않고(서버 요청 0건), 오른쪽 편집 칸에 초점
// 식별자만 올려 보내는 "얇은 콜백"의 데이터 모양 시험. SPEC-LDBEAT-001
// M9 step 4, 카드 t560.
import { describe, expect, it } from "vitest";

import { buildGlanceFocusTarget, glanceFocusAction } from "./tableFocus";

// 카드 t560 — 표 칼럼 → t561 편집 칸 초점 입력(selectCue + setFocusField).
describe("glanceFocusAction", () => {
  it("전환 칼럼은 같은 편집 칸을 전환 화면으로 열고 초점 필드는 없다", () => {
    expect(glanceFocusAction("전환")).toEqual({ transition: true, focusField: null });
  });

  it("값 칼럼은 큐 편집 화면을 열고 그 필드에 초점을 둔다", () => {
    for (const field of ["밝기", "위치", "색", "움직임"] as const) {
      expect(glanceFocusAction(field)).toEqual({ transition: false, focusField: field });
    }
  });

  it("줄 이름 칸은 초점 없이 큐 편집 화면을 연다", () => {
    expect(glanceFocusAction(null)).toEqual({ transition: false, focusField: null });
  });
});

describe("buildGlanceFocusTarget", () => {
  it("트랙·마디만으로도 초점 식별자를 만든다(필드 생략 시 null)", () => {
    expect(buildGlanceFocusTarget("FOOBAR-ALL", 11)).toEqual({
      groupName: "FOOBAR-ALL",
      bar: 11,
      field: null,
    });
  });

  it("필드를 주면 그 필드까지 식별자에 담는다", () => {
    expect(buildGlanceFocusTarget("FOOBAR-ALL", 11, "밝기")).toEqual({
      groupName: "FOOBAR-ALL",
      bar: 11,
      field: "밝기",
    });
  });

  it("값을 바꾸는 필드가 전혀 없다 — 반환 값은 식별자뿐이다(서버 요청·값 변경 0건을 구조로 보증)", () => {
    const target = buildGlanceFocusTarget("FOOBAR-ALL", 11);
    expect(Object.keys(target).sort()).toEqual(["bar", "field", "groupName"]);
  });
});
