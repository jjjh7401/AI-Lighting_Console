// 앱 최상단 오류 경계 — 자식 한 부분이 던져도 화면이 검게 비지 않고 안내가 보여야
// 한다. 브라우저의 실제 경로(componentDidCatch 가 불리는 렌더)는 DOM 없는 이
// 하네스(node)에서 돌릴 수 없으므로, 경계가 쓰는 두 계약을 직접 확인한다:
// 오류 → 상태, 상태 → 안내 문구.
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { ErrorBoundary } from "./ErrorBoundary";

function Healthy() {
  return <p>정상 화면</p>;
}

describe("오류 경계 — 상태 계약", () => {
  it("오류가 없으면 자식을 그대로 낸다", () => {
    const boundary = new ErrorBoundary({ children: <Healthy /> });
    expect(renderToStaticMarkup(<>{boundary.render()}</>)).toBe("<p>정상 화면</p>");
  });

  it("오류가 나면 자식 대신 「이 부분을 그리지 못했어요」와 다시 그리기를 낸다", () => {
    const boundary = new ErrorBoundary({ children: <Healthy /> });
    boundary.state = ErrorBoundary.getDerivedStateFromError(new Error("reading 'length'"));
    const html = renderToStaticMarkup(<>{boundary.render()}</>);
    expect(html).toContain("이 부분을 그리지 못했어요");
    expect(html).toContain("다시 그리기");
    expect(html).not.toContain("정상 화면");
  });
});
