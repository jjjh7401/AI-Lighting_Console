// 「이 마디 한눈에」 줄 이름 ▸ 펼침의 상세 한 줄(REQ-LDBEAT-023(b)) —
// `buildGlanceRowDetail`이 계산한 값을 그대로 그린다(로직 0, 표시만).
// SPEC-LDBEAT-001 M9 step 6, 카드 t560.
//
// 카드 t560 후속(REQ-LDBEAT-019(c), plan.md M9 step 2) — "이 구간 L·R
// 따로"/"다시 합치기" 토글을 타임라인 줄 이름 칸에서 이 펼침 상세 줄로
// 옮겼다(mockup `detailRow` :434 — `data-split`/`data-unsplit` 링크와
// 같은 자리·같은 글귀). `lrSplit`이 없으면(분리 불가 트랙) 링크 자체가
// 없다 — 데이터 없음 = 숨김.
import type { GlanceRowDetail } from "./glanceRowDetail";

export interface GlanceRowDetailLRSplitControl {
  isSplit: boolean;
  onToggle: () => void;
}

export interface GlanceRowDetailCellsProps {
  detail: GlanceRowDetail;
  /** 펼쳐진 줄의 실제 칼럼 수 — colSpan으로 가로 전체를 쓴다. */
  colSpan: number;
  lrSplit?: GlanceRowDetailLRSplitControl | null;
}

export function GlanceRowDetailCells({ detail, colSpan, lrSplit }: GlanceRowDetailCellsProps) {
  const fixtureLabel = Array.isArray(detail.fixtureNumbers)
    ? detail.fixtureNumbers.join(", ")
    : detail.fixtureNumbers;
  return (
    <tr className="beat-grid-glance-detail-row">
      <td colSpan={colSpan}>
        <span className="beat-grid-glance-detail-field">장비 {fixtureLabel}</span>
        <span className="beat-grid-glance-detail-field">Seq/Cue {detail.seqCue}</span>
        <span className="beat-grid-glance-detail-field">{detail.barRangeLabel}</span>
        <span className="beat-grid-glance-detail-field">길이 {detail.lengthBars}마디</span>
        <span className="beat-grid-glance-detail-field">TC {detail.timecodeLabel}</span>
        <span className="beat-grid-glance-detail-field">명령 {detail.consoleCommand}</span>
        {lrSplit && (
          <button
            type="button"
            className="beat-grid-glance-lr-split-toggle"
            onClick={(event) => {
              event.stopPropagation();
              lrSplit.onToggle();
            }}
          >
            {lrSplit.isSplit ? "L·R 다시 합치기" : "이 구간 왼쪽·오른쪽 따로"}
          </button>
        )}
      </td>
    </tr>
  );
}
