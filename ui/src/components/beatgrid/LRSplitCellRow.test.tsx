// 칸 데이터가 만든 자식 줄(└ L / └ R) 마크업 시험 — 선언 기반 `LRSplitRow` 와 같은 줄 모양을 쓰되,
// 칸마다 쪽의 색으로 칠하고 대수·선택·따름 칸은 없다. jsdom 시험대가 없어(`LRSplitRow.test.tsx`
// 와 같은 메모) `renderToStaticMarkup` 으로 문자열만 단언한다.
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { CellSplitChildRow } from "./cellSplit";
import { CELL_SPLIT_COLOR_UNSET, LRSplitCellRow } from "./LRSplitRow";

// 시험용 눈금: 1마디 = 100px.
const toX = (bar: number) => bar * 100;

const row: CellSplitChildRow = {
  side: "L",
  label: "FOOBAR L",
  cells: [{ startBar: 4, endBar: 8, color: "Red", color_rgb: [100, 0, 0] }],
};

describe("LRSplitCellRow — 줄 모양", () => {
  it("└ 라벨 줄이다 — 선언 기반 자식 줄과 같은 클래스를 쓴다", () => {
    const html = renderToStaticMarkup(<LRSplitCellRow row={row} toX={toX} />);
    expect(html).toContain("└ FOOBAR L");
    expect(html).toContain('class="beat-grid-track beat-grid-track-child"');
    expect(html).toContain("beat-grid-track-label beat-grid-track-label-child");
  });

  it("대수·갈라짐 표시·선택 클래스·따름 칸이 없다 — 표시 전용이다", () => {
    const html = renderToStaticMarkup(<LRSplitCellRow row={row} toX={toX} />);
    expect(html).not.toMatch(/\d+대/);
    expect(html).not.toContain("<small");
    expect(html).not.toContain("여기서 갈라짐");
    expect(html).not.toContain("beat-grid-track-child-selectable");
    expect(html).not.toContain("beat-grid-cue-follow");
  });
});

describe("LRSplitCellRow — 칸", () => {
  it("칸은 beat-grid-cue beat-grid-cue-split-child 이고 자리는 부모 막대와 같은 식이다", () => {
    const html = renderToStaticMarkup(<LRSplitCellRow row={row} toX={toX} />);
    expect(html).toContain('class="beat-grid-cue beat-grid-cue-split-child"');
    // 시작 4마디 → 400px, 너비 = 끝 8마디 - 시작 4마디 - 2 = 398px
    expect(html).toContain("left:400px;width:398px");
  });

  it("바탕은 그 쪽의 color_rgb 이고 글은 색 이름이다", () => {
    const html = renderToStaticMarkup(<LRSplitCellRow row={row} toX={toX} />);
    expect(html).toContain("background-color:#ff0000");
    expect(html).toMatch(/>Red<\/span>/);
  });

  it("색을 정하지 않았으면 「색 미정」이고 바탕을 칠하지 않는다", () => {
    const undecided: CellSplitChildRow = {
      ...row,
      cells: [{ startBar: 4, endBar: 8, color: null, color_rgb: null }],
    };
    const html = renderToStaticMarkup(<LRSplitCellRow row={undecided} toX={toX} />);
    expect(CELL_SPLIT_COLOR_UNSET).toBe("색 미정");
    expect(html).toContain(">색 미정</span>");
    expect(html).not.toContain("background-color");
  });

  it("이름은 있는데 RGB 를 못 풀었으면 이름만 쓰고 바탕은 기본 그대로다 — 색을 지어내지 않는다", () => {
    const unresolved: CellSplitChildRow = {
      ...row,
      cells: [{ startBar: 4, endBar: 8, color: "no-such-color", color_rgb: null }],
    };
    const html = renderToStaticMarkup(<LRSplitCellRow row={unresolved} toX={toX} />);
    expect(html).toContain(">no-such-color</span>");
    expect(html).not.toContain("background-color");
    expect(html).toContain("(RGB 미정)");
  });

  it("범위 밖 RGB 는 칠하지 않는다", () => {
    const outOfRange: CellSplitChildRow = {
      ...row,
      cells: [{ startBar: 4, endBar: 8, color: "Red", color_rgb: [101, 0, 0] }],
    };
    expect(renderToStaticMarkup(<LRSplitCellRow row={outOfRange} toX={toX} />)).not.toContain(
      "background-color",
    );
  });

  it("칸이 여럿이면 순서대로 줄 하나 안에 그린다", () => {
    const two: CellSplitChildRow = {
      ...row,
      cells: [
        { startBar: 0, endBar: 4, color: "Red", color_rgb: [100, 0, 0] },
        { startBar: 8, endBar: 12, color: "Blue", color_rgb: [5, 20, 100] },
      ],
    };
    const html = renderToStaticMarkup(<LRSplitCellRow row={two} toX={toX} />);
    expect(html.match(/beat-grid-cue-split-child/g)).toHaveLength(2);
    expect(html.indexOf("left:0px;width:398px")).toBeLessThan(html.indexOf("left:800px;width:398px"));
    expect(html).toContain("background-color:#0d33ff");
  });
});
