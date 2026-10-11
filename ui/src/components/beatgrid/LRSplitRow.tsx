// 자식 줄 하나(REQ-LDBEAT-019(c)) — "이 구간 L·R 따로" 선언이 만든 두
// 줄(L/R) 중 하나를 그린다. SPEC-LDBEAT-001 M9 step 2, 카드 t560.
//
// §Gaps(카드 t560 보고) — 이 자식 줄은 **표시 전용**이다. 실제 장비 패치
// (fid 목록)·그룹 번호를 모르고(`lrSplit.ts` 모듈 주석 참조), 칸별 편집
// 가능한 큐 데이터도 서버가 아직 주지 않는다 — 그래서 선언된 구간을
// 라벨+틀로만 보여주고, 그 안의 값을 지어내지 않는다. 편집 가능한 L/R
// 전용 칸(REQ-LDBEAT-021(b) "옆빛 L·R" 필드)은 이 카드 범위 밖이다(편집
// 칸 내부 — t561).
import type { LRChildRow } from "./lrSplit";

export interface LRSplitRowProps {
  child: LRChildRow;
  /** 부모 트랙의 `barToX(child.startBar)`와 같은 가로 좌표(px). */
  left: number;
  /** `barToX(child.endBar) - barToX(child.startBar) - 2`와 같은 너비(px). */
  width: number;
}

export function LRSplitRow({ child, left, width }: LRSplitRowProps) {
  return (
    <div className="beat-grid-track beat-grid-track-child" role="row">
      <span className="beat-grid-track-label beat-grid-track-label-child">└ {child.label}</span>
      <div className="beat-grid-track-cues">
        <span
          className="beat-grid-cue beat-grid-cue-split-child"
          style={{ left, width }}
          title={`${child.startBar}~${child.endBar - 1}마디 — ${child.label} 따로(표시 전용, 편집은 M3+)`}
        >
          {child.label}
        </span>
      </div>
    </div>
  );
}
