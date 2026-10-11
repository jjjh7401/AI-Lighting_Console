// 자식 줄(L/R) 마크업 시험 — "여기서 갈라짐" 표시(REQ-LDBEAT-024(e),
// AC-LDBEAT-024(e)) + 선택 가능 여부. SPEC-LDBEAT-001 M9 step 7, 카드
// t570. jsdom 시험대가 없으므로(BeatGrid.test.tsx 같은 메모)
// `renderToStaticMarkup`으로 문자열만 단언한다(BeatGridTopBar.test.tsx
// 와 같은 방식).
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { LRChildRow } from "./lrSplit";
import { LRSplitRow } from "./LRSplitRow";

const child: LRChildRow = {
  side: "L",
  label: "FOOBAR L",
  memberCount: 3,
  startBar: 10,
  endBar: 14,
};

describe("LRSplitRow — 「여기서 갈라짐」 표시(REQ-LDBEAT-024(e))", () => {
  it("자식 줄에 '여기서 갈라짐' 표시가 있다", () => {
    const html = renderToStaticMarkup(<LRSplitRow child={child} left={100} width={50} />);
    expect(html).toContain("여기서 갈라짐");
  });

  it("기존 라벨·대수 표시는 그대로다(회귀 방지)", () => {
    const html = renderToStaticMarkup(<LRSplitRow child={child} left={100} width={50} />);
    expect(html).toContain("FOOBAR L");
    expect(html).toContain("3대");
  });

  it("onSelect 를 넘기면 선택 가능 클래스가 붙는다", () => {
    const html = renderToStaticMarkup(<LRSplitRow child={child} left={100} width={50} onSelect={() => {}} />);
    expect(html).toContain("beat-grid-track-child-selectable");
  });

  it("onSelect 가 없으면 선택 가능 클래스가 없다", () => {
    const html = renderToStaticMarkup(<LRSplitRow child={child} left={100} width={50} />);
    expect(html).not.toContain("beat-grid-track-child-selectable");
  });
});
