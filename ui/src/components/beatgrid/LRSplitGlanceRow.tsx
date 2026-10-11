// 「이 마디 한눈에」 표의 자식 줄(L/R) 하나(REQ-LDBEAT-019(c), mockup
// `drawBar` 의 `id==="side"&&SPLIT&&b>=SPLIT.a&&b<=SPLIT.b` 분기와 같은
// 자리 — "└ 이름" 줄). SPEC-LDBEAT-001 M9 step 2, 카드 t560 후속.
//
// §Gaps(카드 t560 보고, `lrSplit.ts`/`LRSplitRow.tsx` 모듈 주석과 같은
// 경계) — 이 자식 줄은 **표시 전용**이다. 실제 장비 패치·칸별 편집
// 가능한 큐 데이터를 몰라, 나머지 다섯 칸(밝기~전환)을 지어내지 않고
// 하나로 합쳐 "—"(미정)로 둔다.
import type { LRChildRow } from "./lrSplit";

export interface LRSplitGlanceRowProps {
  child: LRChildRow;
  /** 나머지 다섯 칸(밝기·위치·색·움직임·전환)을 합쳐 보이는 칸 수. */
  remainingColSpan: number;
}

export function LRSplitGlanceRow({ child, remainingColSpan }: LRSplitGlanceRowProps) {
  return (
    <tr className="beat-grid-glance-row beat-grid-glance-child-row">
      <td>
        └ {child.label} <small>· {child.memberCount}대</small>
      </td>
      <td colSpan={remainingColSpan}>—</td>
    </tr>
  );
}
