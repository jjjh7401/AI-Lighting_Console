// Deploy review card (M7 — REQ-MVP-019/027): plugin name, compile verdict,
// destructive-scan report (blacklisted lines highlighted), dynamic-assembly
// notes, bounded source preview, and approve/reject. The static scan is a
// best-effort assist signal — the human reviewer is the authoritative control.
import { useRef, useState } from "react";

import { type ReviewRequestView } from "../protocol";
import { createDecisionGuard } from "./ApprovalCard";

const KIND_LABELS: Record<string, string> = {
  blacklisted: "블랙리스트 명령",
  invoking: "간접 호출 (배포 시점 검증 불가)",
  unparseable: "해석 불가 명령",
};

export function ReviewCard({
  review,
  onDecision,
}: {
  review: ReviewRequestView;
  onDecision: (requestId: string, approved: boolean) => void;
}) {
  const { scan } = review;
  const [decided, setDecided] = useState(false);
  const guardRef = useRef<((requestId: string, approved: boolean) => boolean) | null>(null);
  if (guardRef.current === null) {
    guardRef.current = createDecisionGuard(onDecision);
  }

  const decide = (approved: boolean) => {
    const submitted = guardRef.current!(review.request_id, approved);
    if (submitted) setDecided(true);
  };

  return (
    <div className={`review-card${scan.destructive ? " destructive" : ""}`}>
      <div className="review-title">
        플러그인 배포 리뷰 — <code>{review.plugin_name}</code>
      </div>
      <div className="review-meta">
        <span>컴파일: {review.compile_ok ? "통과" : "실패"}</span>
        <span>
          소스 {review.source_length}자{review.source_truncated ? " (미리보기 일부)" : ""}
        </span>
      </div>
      {scan.destructive && (
        <div className="review-destructive-banner">
          ⚠ 파괴적 내용 감지 — 승인 시 "파괴적" 플래그와 함께 등록되며, 이후 호출마다
          인간 승인이 필요합니다.
        </div>
      )}
      {scan.findings.length > 0 && (
        <ul className="review-findings">
          {scan.findings.map((finding) => (
            <li
              key={`${finding.line}-${finding.command}`}
              className={`finding ${finding.kind}`}
            >
              <span className="finding-line">{finding.line}행</span>{" "}
              <code>{finding.command}</code> — {KIND_LABELS[finding.kind] ?? finding.kind}
              {finding.matched_entry !== null && (
                <span className="finding-entry"> (블랙리스트: {finding.matched_entry})</span>
              )}
            </li>
          ))}
        </ul>
      )}
      {scan.dynamic_calls.length > 0 && (
        <div className="review-dynamic">
          동적 문자열 조립 Cmd() 호출 {scan.dynamic_calls.length}건 — 정적 스캔으로
          검증되지 않습니다:
          <ul>
            {scan.dynamic_calls.map((call) => (
              <li key={`${call.line}-${call.snippet}`}>
                {call.line}행: <code>{call.snippet}</code>
              </li>
            ))}
          </ul>
        </div>
      )}
      <pre className="review-source">{review.source_preview}</pre>
      <div className="review-caveat">
        정적 스캔은 최선 노력(best-effort) 보조 신호입니다 — 동적 문자열 조립은
        탐지되지 않을 수 있으며, 최종 판단 권한은 리뷰어에게 있습니다.
      </div>
      <div className="review-actions">
        <button className="approve" onClick={() => decide(true)} disabled={decided}>
          배포 승인
        </button>
        <button className="reject" onClick={() => decide(false)} disabled={decided}>
          거부
        </button>
      </div>
    </div>
  );
}
