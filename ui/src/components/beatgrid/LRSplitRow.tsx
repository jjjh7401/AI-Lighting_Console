// 자식 줄 하나(REQ-LDBEAT-019(c)) — "이 구간 L·R 따로" 선언이 만든 두
// 줄(L/R) 중 하나를 그린다. SPEC-LDBEAT-001 M9 step 2, 카드 t560 후속
// (리드 결정 2026-10-11 — 이름 규칙 폐기, 실측 대수 표시로 교체).
//
// §Gaps(카드 t560 보고, 이어서 유효) — 이 자식 줄은 **표시 전용**이다.
// 실제 장비 패치(fid 목록)·그룹 번호를 모르고(`lrSplit.ts` 모듈 주석
// 참조 — 아는 것은 소속 확인된 "대수"뿐), 칸별 편집 가능한 큐 데이터도
// 서버가 아직 주지 않는다 — 그래서 선언된 구간을 라벨+틀로만 보여주고,
// 그 안의 값을 지어내지 않는다. 편집 가능한 L/R 전용 칸(REQ-LDBEAT-021(b)
// "옆빛 L·R" 필드)은 이 카드 범위 밖이다(편집 칸 내부 — t561).
//
// 카드 t570(REQ-LDBEAT-024(e)) — `onSelect`가 생기면 이 자식 줄을 누를
// 수 있다("보고 있는 줄"을 L·R로 선택). 실제 편집 가능 데이터는 여전히
// 부모 트랙 것뿐이다 — `onSelect`는 "지금 보는 줄이 이 자식이다"는
// 표시만 위로 올리고, 편집 칸 값 자체는 바꾸지 않는다(위 §Gaps와
// 같은 경계). 선언 구간이 시작하는 자리라 "여기서 갈라짐"을 항상
// 보인다(이 줄 자체가 그 구간 전체를 담당하므로 마디별 반복 없이
// 한 번만).
import type { LRChildRow } from "./lrSplit";

export interface LRSplitRowProps {
  child: LRChildRow;
  /** 부모 트랙의 `barToX(child.startBar)`와 같은 가로 좌표(px). */
  left: number;
  /** `barToX(child.endBar) - barToX(child.startBar) - 2`와 같은 너비(px). */
  width: number;
  /** 카드 t570 — 이 자식 줄을 "보는 중"으로 선택. 없으면(기존과 동일)
   * 표시 전용이다. */
  onSelect?: () => void;
}

export function LRSplitRow({ child, left, width, onSelect }: LRSplitRowProps) {
  return (
    <div
      className={`beat-grid-track beat-grid-track-child${onSelect ? " beat-grid-track-child-selectable" : ""}`}
      role="row"
      onClick={onSelect}
    >
      <span className="beat-grid-track-label beat-grid-track-label-child">
        └ {child.label} <small>· {child.memberCount}대</small>
      </span>
      <div className="beat-grid-track-cues">
        <span
          className="beat-grid-cue beat-grid-cue-split-child"
          style={{ left, width }}
          title={`${child.startBar}~${child.endBar - 1}마디 — ${child.label} 따로(실측 ${child.memberCount}대, 표시 전용 — 편집은 M3+)`}
        >
          <small className="beat-grid-split-start-marker">여기서 갈라짐</small> {child.label}
        </span>
      </div>
    </div>
  );
}
