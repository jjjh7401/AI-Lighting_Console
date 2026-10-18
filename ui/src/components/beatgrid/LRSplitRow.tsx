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
import type { CellSplitChildRow } from "./cellSplit";
import type { LRChildRow } from "./lrSplit";
import { cueRgbHex } from "./presetColorHex";

/** 「SIDE-ALL 따름」 점선 칸 — 자식 줄 밖(선언 구간 앞·뒤)에서 부모를 따른다는 표시(시안 `.clip.follow`). */
export interface LRFollowCells {
  label: string;
  spans: readonly { left: number; width: number }[];
}

export interface LRSplitRowProps {
  child: LRChildRow;
  /** 부모 트랙의 `barToX(child.startBar)`와 같은 가로 좌표(px). */
  left: number;
  /** `barToX(child.endBar) - barToX(child.startBar) - 2`와 같은 너비(px). */
  width: number;
  /** 카드 t570 — 이 자식 줄을 "보는 중"으로 선택. 없으면(기존과 동일)
   * 표시 전용이다. */
  onSelect?: () => void;
  /** 자식 줄 밖의 따름 칸. 없으면(기존과 동일) 따름 칸을 그리지 않는다. */
  follow?: LRFollowCells;
}

export function LRSplitRow({ child, left, width, onSelect, follow }: LRSplitRowProps) {
  const followLabel = follow?.label;
  return (
    <div
      className={`beat-grid-track beat-grid-track-child${onSelect ? " beat-grid-track-child-selectable" : ""}`}
      role="row"
      onClick={onSelect}
    >
      <span className="beat-grid-track-label beat-grid-track-label-child">
        <span className="beat-grid-track-name" title={`${child.label} · ${child.memberCount}대`}>
          └ {child.label} <small>· {child.memberCount}대</small>
        </span>
      </span>
      <div className="beat-grid-track-cues">
        {follow?.spans.map((span, index) => (
          <span
            key={index}
            className="beat-grid-cue beat-grid-cue-follow"
            style={{ left: span.left, width: span.width }}
          >
            {followLabel}
          </span>
        ))}
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

/** 칸 색을 아직 정하지 않은 쪽의 칸 글. */
export const CELL_SPLIT_COLOR_UNSET = "색 미정";

export interface LRSplitCellRowProps {
  row: CellSplitChildRow;
  /** 마디 → 가로 좌표(px). 부모 줄과 같은 눈금(`BeatGrid.tsx` 의 `barToX`). */
  toX: (bar: number) => number;
}

/** 칸 데이터(서버 `cue.split`)가 만든 자식 줄 하나(└ L / └ R). 선언 기반 `LRSplitRow` 와 같은 줄 모양·
 * 클래스를 쓰지만 칸이 하나가 아니라 나뉜 칸마다 하나씩이다. 표시 전용이다 — 누를 수 없고(`onSelect` 없음),
 * 선언 구간 밖의 「따름」 칸도 없다(칸 데이터가 이 줄의 전부다). 칸 바탕은 그 쪽의 `color_rgb`, 글은 색 이름
 * (정하지 않았으면 「색 미정」)이다. 색을 못 풀었으면 바탕은 자식 칸 기본색 그대로다 — 색을 지어내지 않는다.
 * 대수(`memberCount`)는 칸 데이터에 없으므로 쓰지 않는다. */
export function LRSplitCellRow({ row, toX }: LRSplitCellRowProps) {
  return (
    <div className="beat-grid-track beat-grid-track-child" role="row">
      <span className="beat-grid-track-label beat-grid-track-label-child">
        <span className="beat-grid-track-name" title={row.label}>
          └ {row.label}
        </span>
      </span>
      <div className="beat-grid-track-cues">
        {row.cells.map((cell) => {
          const name = cell.color?.trim() ? cell.color : CELL_SPLIT_COLOR_UNSET;
          const fill = cueRgbHex(cell.color_rgb);
          return (
            <span
              key={cell.startBar}
              className="beat-grid-cue beat-grid-cue-split-child"
              style={{
                left: toX(cell.startBar),
                width: toX(cell.endBar) - toX(cell.startBar) - 2,
                ...(fill ? { backgroundColor: fill } : {}),
              }}
              title={`${cell.startBar}~${cell.endBar - 1}마디 — ${row.label} · ${name}${
                cell.color && !fill ? " (RGB 미정)" : ""
              }`}
            >
              {name}
            </span>
          );
        })}
      </div>
    </div>
  );
}

/** 자식 칸 데이터가 한 줄이라도 있으면 부모 칸을 띠로 대신하고, 없으면 부모 칸을 그대로 둔다(리드 결정). */
export function lrParentCellsReplaced(childRows: readonly LRChildRow[]): boolean {
  return childRows.some((child) => (child.cues?.length ?? 0) > 0);
}

/** 시안 `.clip.split` — 갈라진 구간 띠(줄무늬). 글은 시안과 같은 기준으로 넓을 때만 쓴다(40px·70px). */
export function LRSplitBanner({ left, width }: { left: number; width: number }) {
  return (
    <span className="beat-grid-lr-banner" style={{ left, width }} aria-hidden="true">
      {width > 40 && <span className="beat-grid-lr-banner-t">↓ L·R 로 갈라짐</span>}
      {width > 70 && <span className="beat-grid-lr-banner-s">아래 두 줄 보기</span>}
    </span>
  );
}

/** 선언 구간 앞·뒤의 따름 칸 자리(px). 앞은 축 시작부터, 뒤는 축 끝까지. 너비가 0 이하면 만들지 않는다. */
export function lrFollowSpans(
  child: { startBar: number; endBar: number },
  axis: { start: number; end: number },
  toX: (bar: number) => number,
): { left: number; width: number }[] {
  const spans: { left: number; width: number }[] = [];
  if (child.startBar > axis.start) {
    spans.push({ left: toX(axis.start), width: toX(child.startBar) - toX(axis.start) - 2 });
  }
  if (child.endBar < axis.end) {
    spans.push({ left: toX(child.endBar), width: toX(axis.end) - toX(child.endBar) - 2 });
  }
  return spans.filter((span) => span.width > 0);
}
