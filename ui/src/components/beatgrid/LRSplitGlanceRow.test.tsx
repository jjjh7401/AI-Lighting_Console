// 「이 마디 한눈에」 표 자식 줄 마크업 시험 — 선택 가능 여부(REQ-LDBEAT-024(e)).
// SPEC-LDBEAT-001 M9 step 7, 카드 t570. jsdom 시험대가 없으므로
// `renderToStaticMarkup`으로 문자열만 단언한다.
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { LRChildRow } from "./lrSplit";
import { LRSplitGlanceRow } from "./LRSplitGlanceRow";

const child: LRChildRow = {
  side: "R",
  label: "FOOBAR R",
  memberCount: 2,
  startBar: 10,
  endBar: 14,
};

describe("LRSplitGlanceRow — 선택 가능 여부(REQ-LDBEAT-024(e))", () => {
  it("onSelect 를 넘기면 선택 가능 클래스가 붙는다", () => {
    const html = renderToStaticMarkup(
      <table>
        <tbody>
          <LRSplitGlanceRow child={child} remainingColSpan={5} onSelect={() => {}} />
        </tbody>
      </table>,
    );
    expect(html).toContain("beat-grid-glance-child-row-selectable");
  });

  it("onSelect 가 없으면 기존과 바이트 동일하다", () => {
    const html = renderToStaticMarkup(
      <table>
        <tbody>
          <LRSplitGlanceRow child={child} remainingColSpan={5} />
        </tbody>
      </table>,
    );
    expect(html).not.toContain("beat-grid-glance-child-row-selectable");
    expect(html).toContain("FOOBAR R");
  });
});
