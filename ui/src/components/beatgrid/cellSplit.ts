// 칸 하나가 왼쪽(L)·오른쪽(R)을 따로 가질 때(서버 `cue.split`)의 순수 파생 — 타임라인 자식 줄·띠가 읽는다.
//
// `lrSplit.ts` 의 선언(`LRSplitDeclarations`)은 로컬 UI 상태라 구간 한 개의 틀(라벨+띠)만 그렸다.
// 이 모듈은 그 틀에 **칸 데이터**를 댄다: 서버가 칸마다 실어 준 `split.left/right` 의 색으로, 트랙의 L·R
// 두 줄에 쪽마다 칸을 낸다. 값은 전부 서버가 준 것이다 — 색 이름도 RGB도 여기서 짓지 않는다
// (이름이 없으면 `null`, 이름을 못 풀었으면 `color_rgb` 도 `null`).
//
// `BeatGrid.tsx` 를 import 하지 않는다(그쪽이 이 모듈을 import 한다) — 칸 구간 모양(`CueSegment`)은
// 구조만 같게 아래에 적는다. `lrSplit.ts` 가 모듈 순환을 피하려고 같은 방식을 쓴다.
import type { BeatGridCue } from "../../protocol";

/** `BeatGrid.tsx` 의 `CueSegment` 와 구조가 같다(칸 + 시작·끝 마디, 끝은 배타적). */
export interface CellSplitSegment {
  cue: BeatGridCue;
  startBar: number;
  endBar: number;
}

/** 한 쪽(L 또는 R) 줄의 칸 하나 — 나뉜 부모 칸 하나가 쪽마다 칸 하나를 낳는다. */
export interface CellSplitChildCell {
  startBar: number;
  /** 배타적 — `trackCueSegments` 의 `endBar` 와 같은 관례. */
  endBar: number;
  /** 이 쪽의 색 이름 — 정하지 않았으면 `null`. */
  color: string | null;
  /** 그 이름의 RGB(각 0~100%) — 서버가 못 풀었거나 이름이 없으면 `null`. */
  color_rgb: [number, number, number] | null;
}

/** 자식 줄 하나(L 또는 R). `lrSplit.ts` 의 `LRChildRow` 와 달리 대수(`memberCount`)가 없다 — 칸 데이터에는
 * 장비 수가 없고, 모르는 값을 지어내지 않는다. */
export interface CellSplitChildRow {
  side: "L" | "R";
  /** `"<group_name> L"` / `"<group_name> R"` — 접두·접미 치환 없이 그룹 이름을 그대로 잇는다. */
  label: string;
  /** 나뉜 칸마다 하나, 마디 순서대로. */
  cells: CellSplitChildCell[];
}

/** 나뉜 칸(`split` 이 `null` 이 아닌 칸)의 구간만. 받은 구간 객체를 그대로 돌려준다(복사하지 않는다) —
 * 호출부가 `includes` 로 숨길 구간을 가릴 수 있다. */
export function cellSplitSegments<T extends CellSplitSegment>(segments: readonly T[]): T[] {
  return segments.filter((segment) => segment.cue.split != null);
}

const SIDES = [
  { side: "L", key: "left" },
  { side: "R", key: "right" },
] as const;

/** 이 트랙의 자식 줄 둘(L·R) — 나뉜 칸이 하나도 없으면 빈 배열. 줄마다 나뉜 칸 수만큼 칸이 있다(어느 쪽의 색이
 * 비었어도 그 칸은 색 없이 남는다 — 줄 길이를 두 쪽이 맞춘다). */
export function cellSplitChildRows(
  track: { group_name: string },
  segments: readonly CellSplitSegment[],
): CellSplitChildRow[] {
  const split = cellSplitSegments(segments);
  if (split.length === 0) return [];
  return SIDES.map(({ side, key }) => ({
    side,
    label: `${track.group_name} ${side}`,
    cells: split.map((segment) => {
      const body = segment.cue.split?.[key];
      return {
        startBar: segment.startBar,
        endBar: segment.endBar,
        color: body?.color ?? null,
        color_rgb: body?.color_rgb ?? null,
      };
    }),
  }));
}
