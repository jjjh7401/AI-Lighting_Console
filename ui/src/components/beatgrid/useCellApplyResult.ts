// 칸 단위 반영 결과 알림 (SPEC-LDRHYTHM-001, 카드 WT-cell-apply).
//
// 서버는 칸 단위 반영이 성공하면 상태 응답(`beat_grid_send_status`)에 `subset` 을 싣는다. 이 훅은 새 응답 하나가 올 때만
// 반응한다: 보낸 칸이 있으면 알림 줄에 보일 요약을 쥐고, 보낸 첫 칸의 마디를 콘솔에서 보러 간다(`onPreviewBar`).
// 결과는 상태로 쥔다 — 마디를 보러 가면 `last_action: "preview"` 응답이 곧바로 이어 와서 `sendStatus` 가 바뀌는데,
// 그때 요약이 같이 사라지면 안 되기 때문이다.
import { useEffect, useRef, useState } from "react";

import type { BeatGridSendStatus } from "../../protocol";
import { subsetSummary, type SubsetSummary } from "./cellApply";

export interface CellApplyResultOptions {
  sendStatus: BeatGridSendStatus | null;
  /** 보낸 첫 칸의 마디를 콘솔에서 본다(「▶ 이 마디 콘솔에서 보기」와 같은 길). 없으면 마디를 보러 가지 않는다. */
  onPreviewBar?: (bar: number) => void;
  /** 재생 중이거나 콘솔 타임코드가 돌고 있을 수 있으면 참 — 그때는 콘솔을 그 마디로 옮기지 않는다. */
  previewBlocked?: boolean;
}

export function useCellApplyResult({ sendStatus, onPreviewBar, previewBlocked = false }: CellApplyResultOptions) {
  const [result, setResult] = useState<SubsetSummary | null>(null);
  // 마운트 전에 이미 있던 응답에는 반응하지 않는다 — 새 응답 객체가 올 때만 한 번 반응한다.
  const seenRef = useRef(sendStatus);
  const latestRef = useRef({ onPreviewBar, previewBlocked });
  latestRef.current = { onPreviewBar, previewBlocked };
  useEffect(() => {
    if (sendStatus === seenRef.current) return;
    seenRef.current = sendStatus;
    // 반영 결과만 이 알림을 바꾼다 — 미리보기·편집 응답은 요약을 그대로 둔다.
    if (sendStatus === null || sendStatus.last_action !== "apply") return;
    const summary = sendStatus.ok ? subsetSummary(sendStatus.subset) : null;
    setResult(summary);
    if (summary && !latestRef.current.previewBlocked) latestRef.current.onPreviewBar?.(summary.firstBar);
  }, [sendStatus]);
  return { result, dismiss: () => setResult(null) };
}
