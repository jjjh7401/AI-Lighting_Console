// 「⇪ 콘솔에 반영」 진행 표시·거절 알림 숨김 시험 (SPEC-LDRHYTHM-001, 카드 apply-latency). 순수 함수만 본다.
import { describe, expect, it } from "vitest";

import { applyProgressNote, failureNoteVisible } from "./applyProgress";

describe("applyProgressNote — 「⇪ 콘솔에 반영」 진행 문구", () => {
  it("반영이 진행 중이 아니면 문구가 없다", () => {
    expect(applyProgressNote(null, 5000, false)).toBeNull();
  });

  it("콘솔을 읽는 동안은 지난 초를 적는다", () => {
    expect(applyProgressNote(1000, 13400, false)).toBe("콘솔을 읽는 중 · 12초");
  });

  it("승인 카드가 떠 있으면 승인 대기 문구로 바뀐다", () => {
    expect(applyProgressNote(1000, 63000, true)).toBe("승인 카드를 기다리는 중 · 62초");
  });

  it("시계가 거꾸로 가도 음수 초를 적지 않는다", () => {
    expect(applyProgressNote(5000, 4000, false)).toBe("콘솔을 읽는 중 · 0초");
  });
});

describe("failureNoteVisible — 승인 대기 중에는 「⚠ 콘솔에 반영 안 됨」을 보이지 않는다", () => {
  const earlier = { ok: false, reason: "지난 반영" };
  const fresh = { ok: false, reason: "이번 반영" };

  it("승인 카드가 떠 있으면 거절 알림을 숨긴다", () => {
    expect(failureNoteVisible(true, fresh, null)).toBe(false);
  });

  it("이번 반영 전이나 카드가 뜰 때 화면에 있던 결과는 결정 뒤에도 숨긴다 — 이번 반영의 결과가 아니다", () => {
    expect(failureNoteVisible(false, earlier, earlier)).toBe(false);
  });

  it("결정 뒤 새 결과가 오면 실패 알림을 보인다", () => {
    expect(failureNoteVisible(false, fresh, earlier)).toBe(true);
  });

  it("카드가 없었으면 실패 결과를 그대로 보인다", () => {
    expect(failureNoteVisible(false, fresh, null)).toBe(true);
  });
});
