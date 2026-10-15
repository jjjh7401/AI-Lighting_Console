// 갈라짐 표시 시험(시안 `.clip.split`·`.clip.follow`) — 띠 글 기준, 따름 칸 자리(px)를 확인한다.
// 자식 줄 데이터가 아직 없어서 화면 전체 대신 작은 컴포넌트를 직접 그려 본다.
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { LRSplitBanner, LRSplitRow, lrFollowSpans } from "./LRSplitRow";

// 시험용 눈금: 1마디 = 100px.
const toX = (bar: number) => bar * 100;

describe("lrFollowSpans — 자식 줄 밖의 따름 칸 자리", () => {
  it("선언 구간이 가운데면 앞·뒤 두 칸이다", () => {
    const spans = lrFollowSpans({ startBar: 4, endBar: 8 }, { start: 0, end: 12 }, toX);
    expect(spans).toEqual([
      { left: 0, width: 398 },
      { left: 800, width: 398 },
    ]);
  });

  it("선언 구간이 축 시작부터면 뒤쪽 한 칸만 있다", () => {
    const spans = lrFollowSpans({ startBar: 0, endBar: 4 }, { start: 0, end: 12 }, toX);
    expect(spans).toEqual([{ left: 400, width: 798 }]);
  });

  it("선언 구간이 축 끝까지면 앞쪽 한 칸만 있다", () => {
    const spans = lrFollowSpans({ startBar: 8, endBar: 12 }, { start: 0, end: 12 }, toX);
    expect(spans).toEqual([{ left: 0, width: 798 }]);
  });
});

describe("LRSplitBanner — 시안 .clip.split 띠의 글", () => {
  it("넓으면 「↓ L·R 로 갈라짐」과 「아래 두 줄 보기」를 모두 쓴다", () => {
    const html = renderToStaticMarkup(<LRSplitBanner left={0} width={200} />);
    expect(html).toContain("↓ L·R 로 갈라짐");
    expect(html).toContain("아래 두 줄 보기");
  });

  it("좁으면 글을 쓰지 않고, 중간 너비면 첫 줄만 쓴다", () => {
    expect(renderToStaticMarkup(<LRSplitBanner left={0} width={30} />)).not.toContain("L·R 로 갈라짐");
    const mid = renderToStaticMarkup(<LRSplitBanner left={0} width={50} />);
    expect(mid).toContain("↓ L·R 로 갈라짐");
    expect(mid).not.toContain("아래 두 줄 보기");
  });
});

describe("LRSplitRow — 따름 칸", () => {
  const child = { side: "L" as const, label: "SIDE-ALL L", memberCount: 3, startBar: 4, endBar: 8 };

  it("따름 칸은 「SIDE-ALL 따름」 점선 칸으로 그린다", () => {
    const html = renderToStaticMarkup(
      <LRSplitRow
        child={child}
        left={400}
        width={398}
        follow={{ label: "SIDE-ALL 따름", spans: [{ left: 0, width: 398 }] }}
      />,
    );
    expect(html).toContain("beat-grid-cue-follow");
    expect(html).toContain("SIDE-ALL 따름");
  });

  it("따름 칸이 없으면 예전 자식 줄 그대로다", () => {
    const html = renderToStaticMarkup(<LRSplitRow child={child} left={400} width={398} />);
    expect(html).not.toContain("beat-grid-cue-follow");
  });
});
