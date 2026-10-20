// 「⇪ 콘솔에 반영」 진행 표시 (SPEC-LDRHYTHM-001, 카드 apply-latency).
//
// 반영을 누르면 콘솔을 읽고 승인 카드를 만드는 데 수십 초가 걸린다. 그동안 화면이 멈춘
// 것처럼 보이지 않도록 진행 문구를 보이고, 승인 카드가 떠 있으면 「승인 대기」로 바꾼다.
// 순수 함수만 둔다: 시계와 상태는 호출하는 쪽이 쥔다.

/** 반영을 누른 뒤 지난 시간을 적은 진행 문구. 반영이 진행 중이 아니면 `null`.
 * `sending` 이면 승인 뒤 콘솔에 명령을 보내는 중이다 — 서버는 명령마다 진행을 알리지 않으므로 끝 응답이 올
 * 때까지 지난 초와 「창을 닫지 마세요」를 적는다(2026-10-20 실측: 명령 1,113개 · 74초). */
export function applyProgressNote(
  startedAtMs: number | null,
  nowMs: number,
  approvalPending: boolean,
  sending = false,
): string | null {
  if (startedAtMs === null) return null;
  const seconds = Math.max(0, Math.round((nowMs - startedAtMs) / 1000));
  if (approvalPending) return `승인 카드를 기다리는 중 · ${seconds}초`;
  if (sending) return `콘솔에 보내는 중 · ${seconds}초 — 끝날 때까지 창을 닫지 마세요`;
  return `콘솔을 읽는 중 · ${seconds}초`;
}

/** 「⇪ 콘솔에 반영」 한 번의 진행 — 누른 시각, 승인 카드가 뜬 시각, 승인 뒤 보내기 시작한 시각, 그리고 누르기
 * 전이나 카드가 뜰 때 화면에 있던 결과(이번 반영의 결과가 아니다). */
export interface ApplyRun<T> {
  startedAtMs: number | null;
  approvalSinceMs: number | null;
  sendingSinceMs: number | null;
  staleStatus: T | null;
}

export const APPLY_RUN_IDLE: ApplyRun<never> = {
  startedAtMs: null,
  approvalSinceMs: null,
  sendingSinceMs: null,
  staleStatus: null,
};

/**
 * 승인 카드 유무나 서버 결과가 바뀔 때 반영 진행을 한 걸음 옮긴다.
 *
 * - 승인 카드가 떠 있으면 승인 대기 시각을 잡고, 그때 화면의 결과를 「이번 결과 아님」으로 둔다.
 * - 반영을 누른 뒤의 승인 카드가 결정됐는데 새 결과가 아직 없으면 콘솔에 보내는 중이다 — 예전에는 여기서 진행
 *   문구를 거둬 수십 초 동안 아무것도 안 보였다.
 * - 읽는 중·보내는 중에 새 결과가 없으면 그대로 둔다. 새 결과가 오면(성공·실패·거절) 끝난다.
 * - 반영을 누르지 않은 승인(콘솔 재생·정지 카드)은 결정되면 그냥 거둔다.
 */
export function stepApplyRun<T>(run: ApplyRun<T>, approvalPending: boolean, status: T | null, nowMs: number): ApplyRun<T> {
  if (approvalPending) {
    return { ...run, approvalSinceMs: run.approvalSinceMs ?? nowMs, sendingSinceMs: null, staleStatus: status };
  }
  const noNewResult = status === run.staleStatus;
  if (run.startedAtMs !== null && noNewResult) {
    if (run.approvalSinceMs !== null) return { ...run, approvalSinceMs: null, sendingSinceMs: nowMs };
    // 보내는 중이거나 아직 콘솔을 읽는 중(카드 전) — 끝 응답이 올 때까지 그대로다.
    return run;
  }
  return { ...run, startedAtMs: null, approvalSinceMs: null, sendingSinceMs: null };
}

/**
 * 「⚠ 콘솔에 반영 안 됨」을 지금 보여도 되는가.
 *
 * 승인 카드가 떠 있는 동안에는 화면의 결과가 이번 반영의 결과일 수 없다 — 승인이 아직
 * 끝나지 않았다. 누르기 전이나 카드가 뜰 때 화면에 있던 결과(`staleStatus`)도 이번 반영의
 * 결과가 아니므로, 결정 뒤에도 새 결과가 올 때까지 숨긴다.
 */
export function failureNoteVisible<T>(
  approvalPending: boolean,
  status: T | null | undefined,
  staleStatus: T | null | undefined,
): boolean {
  return !approvalPending && status !== staleStatus;
}
