// 「⇪ 콘솔에 반영」 진행 표시 (SPEC-LDRHYTHM-001, 카드 apply-latency).
//
// 반영을 누르면 콘솔을 읽고 승인 카드를 만드는 데 수십 초가 걸린다. 그동안 화면이 멈춘
// 것처럼 보이지 않도록 진행 문구를 보이고, 승인 카드가 떠 있으면 「승인 대기」로 바꾼다.
// 순수 함수만 둔다: 시계와 상태는 호출하는 쪽이 쥔다.

/** 반영을 누른 뒤 지난 시간을 적은 진행 문구. 반영이 진행 중이 아니면 `null`. */
export function applyProgressNote(
  startedAtMs: number | null,
  nowMs: number,
  approvalPending: boolean,
): string | null {
  if (startedAtMs === null) return null;
  const seconds = Math.max(0, Math.round((nowMs - startedAtMs) / 1000));
  return approvalPending
    ? `승인 카드를 기다리는 중 · ${seconds}초`
    : `콘솔을 읽는 중 · ${seconds}초`;
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
