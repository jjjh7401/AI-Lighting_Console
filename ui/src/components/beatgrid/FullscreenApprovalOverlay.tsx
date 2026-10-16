// 박자 배치 전체화면 위의 승인 카드 — 전체화면은 채팅 열을 숨기므로, 「⇪ 반영」·프리셋 계획·
// 「콘솔 같이 ▶」가 띄운 승인 요청(approval_request)이 전체화면 뒤에 묻혀 감독이 못 찾았다.
// 전체화면이 열려 있는 동안 대기 중인 승인을 오른쪽 위에 겹쳐 그대로 보인다(기존
// `ApprovalCard` 재사용 — 승인·거부·명령 펼치기가 채팅 열과 같다). 결정은 같은 `onDecision`
// 으로만 나가므로 승인 경로가 둘로 갈리지 않는다.
import { useEffect, useRef } from "react";

import type { PendingApproval } from "../../protocol";
import { ApprovalCard } from "../ApprovalCard";

export function FullscreenApprovalOverlay({
  approvals,
  onDecision,
  focusSignal = 0,
}: {
  approvals: readonly PendingApproval[];
  onDecision: (requestId: string, approved: boolean) => void;
  /** 값이 바뀔 때마다 카드로 화면을 옮기고 초점을 준다(대기 문구를 눌렀을 때). */
  focusSignal?: number;
}) {
  const ref = useRef<HTMLElement | null>(null);
  useEffect(() => {
    if (focusSignal === 0) return;
    ref.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    ref.current?.focus();
  }, [focusSignal]);
  if (approvals.length === 0) return null;
  return (
    <aside
      ref={ref}
      className="beat-grid-approval-overlay"
      role="dialog"
      aria-label="승인 대기"
      tabIndex={-1}
    >
      <p className="beat-grid-approval-overlay-title">승인이 필요해요 — 여기서 승인하거나 거부하세요</p>
      {approvals.map((approval) => (
        <ApprovalCard key={approval.request_id} approval={approval} onDecision={onDecision} />
      ))}
    </aside>
  );
}
