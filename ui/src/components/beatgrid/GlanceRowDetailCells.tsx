// 「이 마디 한눈에」 줄 이름 ▸ 펼침의 상세 한 줄(REQ-LDBEAT-023(b)) —
// `buildGlanceRowDetail`이 계산한 값을 그대로 그린다(로직 0, 표시만).
// SPEC-LDBEAT-001 M9 step 6, 카드 t560.
import type { GlanceRowDetail } from "./glanceRowDetail";

export interface GlanceRowDetailCellsProps {
  detail: GlanceRowDetail;
  /** 펼쳐진 줄의 실제 칼럼 수 — colSpan으로 가로 전체를 쓴다. */
  colSpan: number;
}

export function GlanceRowDetailCells({ detail, colSpan }: GlanceRowDetailCellsProps) {
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
      </td>
    </tr>
  );
}
