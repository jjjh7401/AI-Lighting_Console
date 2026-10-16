// REQ-LDBEAT-004(c) — 역할별 조건부 노출 시험(`BeatGrid.tsx`에서 이
// 모듈로 옮긴 기존 동작, 카드 t560 후속).
import { describe, expect, it } from "vitest";

import { roleFieldHints } from "./roleFields";

describe("roleFieldHints", () => {
  it("모든 역할에 밝기를 포함한다", () => {
    expect(roleFieldHints(null)).toContain("밝기");
    expect(roleFieldHints("key")).toContain("밝기");
  });

  it("무빙·역광·옆빛·워시만 위치를 포함한다", () => {
    expect(roleFieldHints("mover")).toContain("위치");
    expect(roleFieldHints("back")).toContain("위치");
    expect(roleFieldHints("side")).toContain("위치");
    expect(roleFieldHints("wash")).toContain("위치");
    expect(roleFieldHints("key")).not.toContain("위치");
    expect(roleFieldHints(null)).not.toContain("위치");
  });

  it("모든 역할이 색을 포함한다 — 무빙도 무대 구간 색을 따른다", () => {
    expect(roleFieldHints("key")).toContain("색");
    expect(roleFieldHints("side")).toContain("색");
    expect(roleFieldHints("mover")).toContain("색");
  });

  it("무빙은 위치 다음, 움직임 앞에 색을 둔다", () => {
    expect(roleFieldHints("mover")).toEqual(["밝기", "위치", "색", "움직임"]);
  });

  it("무빙만 움직임을 포함한다", () => {
    expect(roleFieldHints("mover")).toContain("움직임");
    expect(roleFieldHints("back")).not.toContain("움직임");
  });
});
