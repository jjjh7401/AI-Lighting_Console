// Pending-approval card (REQ-MVP-021): command + risk reasons + warnings +
// approve/reject. The decision flows back to the safety gate over the socket.
import { useRef, useState } from "react";

import { type PendingApproval } from "../protocol";

// A per-approval guard preventing more than one decision from reaching
// onDecision — a rapid double-click (or any repeated click before the
// buttons re-render as disabled) is a no-op once the first decision has
// already been submitted. Returns true when this call was the one that
// submitted the decision, false when it was ignored as a repeat.
//
// Pure and DOM-free so it is unit-testable per this project's no-DOM-harness
// convention (see useCopilotSocket.test.ts header — "Pure functions
// only... unit-testable without a DOM").
export function createDecisionGuard(
  onDecision: (requestId: string, approved: boolean) => void,
): (requestId: string, approved: boolean) => boolean {
  let decided = false;
  return (requestId, approved) => {
    if (decided) return false;
    decided = true;
    onDecision(requestId, approved);
    return true;
  };
}

export function ApprovalCard({
  approval,
  onDecision,
}: {
  approval: PendingApproval;
  onDecision: (requestId: string, approved: boolean) => void;
}) {
  const [decided, setDecided] = useState(false);
  // useRef (not useState) for the guard itself: it must be synchronously
  // consistent across two clicks that land before React re-renders, which a
  // plain state-checked closure would not guarantee. One card = one
  // approval (App.tsx keys each ApprovalCard by approval.request_id), so a
  // single guard for this component instance's lifetime is sufficient.
  const guardRef = useRef<((requestId: string, approved: boolean) => boolean) | null>(null);
  if (guardRef.current === null) {
    guardRef.current = createDecisionGuard(onDecision);
  }

  const decide = (approved: boolean) => {
    const submitted = guardRef.current!(approval.request_id, approved);
    if (submitted) setDecided(true);
  };

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
          onClick={() => decide(true)}
          disabled={decided}
        >
          승인
        </button>
        <button
          className="reject"
          onClick={() => decide(false)}
          disabled={decided}
        >
          거부
        </button>
      </div>
      <div className="approval-note">거부 시 번들 전체가 실행되지 않습니다 (all-or-nothing).</div>
    </div>
  );
}
