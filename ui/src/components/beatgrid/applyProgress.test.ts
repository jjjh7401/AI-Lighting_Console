// 「⇪ 콘솔에 반영」 진행 표시·거절 알림 숨김 시험 (SPEC-LDRHYTHM-001, 카드 apply-latency). 순수 함수만 본다.
import { describe, expect, it } from "vitest";

import { APPLY_RUN_IDLE, applyProgressNote, failureNoteVisible, stepApplyRun } from "./applyProgress";

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

  it("승인 뒤 콘솔에 보내는 동안은 「보내는 중」과 창을 닫지 말라는 말을 적는다", () => {
    expect(applyProgressNote(1000, 75000, false, true)).toBe(
      "콘솔에 보내는 중 · 74초 — 끝날 때까지 창을 닫지 마세요",
    );
  });
});

// 2026-10-20 실측(LOVE ATTACK) — 승인 뒤 명령 1,113개가 74초 동안 나가는데 진행 문구가 승인 순간 사라졌다.
describe("stepApplyRun — 반영 진행 단계(읽는 중 → 승인 대기 → 보내는 중 → 끝)", () => {
  const before = { ok: true, reason: null };
  const result = { ok: true, reason: "반영 끝" };
  const started = { ...APPLY_RUN_IDLE, startedAtMs: 1000, staleStatus: before };

  it("승인 카드가 뜨면 승인 대기 시각을 잡는다", () => {
    const run = stepApplyRun(started, true, before, 5000);
    expect(run.approvalSinceMs).toBe(5000);
    expect(run.sendingSinceMs).toBeNull();
  });

  it("반영 승인 뒤 결과가 아직 없으면 「보내는 중」으로 넘어간다 — 진행 문구를 거두지 않는다", () => {
    const waiting = stepApplyRun(started, true, before, 5000);
    const sending = stepApplyRun(waiting, false, before, 9000);
    expect(sending.startedAtMs).toBe(1000);
    expect(sending.approvalSinceMs).toBeNull();
    expect(sending.sendingSinceMs).toBe(9000);
  });

  it("보내는 중에 다른 것이 바뀌지 않으면 그대로 보내는 중이다", () => {
    const sending = stepApplyRun(stepApplyRun(started, true, before, 5000), false, before, 9000);
    expect(stepApplyRun(sending, false, before, 20000)).toEqual(sending);
  });

  it("마지막 결과(새 응답)가 오면 끝난다", () => {
    const sending = stepApplyRun(stepApplyRun(started, true, before, 5000), false, before, 9000);
    const done = stepApplyRun(sending, false, result, 83000);
    expect(done.startedAtMs).toBeNull();
    expect(done.sendingSinceMs).toBeNull();
    expect(done.staleStatus).toBe(before);
  });

  it("반영을 누르지 않은 승인(콘솔 재생 카드 등)은 결정 뒤 「보내는 중」을 만들지 않는다", () => {
    const waiting = stepApplyRun(APPLY_RUN_IDLE, true, before, 5000);
    const decided = stepApplyRun(waiting, false, before, 9000);
    expect(decided.sendingSinceMs).toBeNull();
    expect(decided.startedAtMs).toBeNull();
    expect(decided.approvalSinceMs).toBeNull();
  });

  it("승인과 결과가 한꺼번에 오면(거절 등) 바로 끝난다", () => {
    const waiting = stepApplyRun(started, true, before, 5000);
    const done = stepApplyRun(waiting, false, result, 9000);
    expect(done.startedAtMs).toBeNull();
    expect(done.sendingSinceMs).toBeNull();
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
