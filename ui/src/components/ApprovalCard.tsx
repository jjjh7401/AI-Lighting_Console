// Pending-approval card (REQ-MVP-021): command + risk reasons + warnings +
// approve/reject. The decision flows back to the safety gate over the socket.
import { type PendingApproval } from "../protocol";

export function ApprovalCard({
  approval,
  onDecision,
}: {
  approval: PendingApproval;
  onDecision: (requestId: string, approved: boolean) => void;
}) {
  return (
    <div className="approval-card">
      <div className="approval-title">승인 대기 — 위험 명령</div>
      {approval.items.map((item) => (
        <div key={item.command} className="approval-item">
          <code className="approval-command">{item.command}</code>
          <ul className="approval-reasons">
            {item.risk_reasons.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
          {item.warnings.length > 0 && (
            <div className="approval-warnings">
              {item.warnings.map((warning) => (
                <div key={warning} className="warning">
                  ⚠ {warning}
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
      <div className="approval-actions">
        <button
          className="approve"
          onClick={() => onDecision(approval.request_id, true)}
        >
          승인
        </button>
        <button
          className="reject"
          onClick={() => onDecision(approval.request_id, false)}
        >
          거부
        </button>
      </div>
      <div className="approval-note">거부 시 번들 전체가 실행되지 않습니다 (all-or-nothing).</div>
    </div>
  );
}
