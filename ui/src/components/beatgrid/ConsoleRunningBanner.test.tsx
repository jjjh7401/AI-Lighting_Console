// 콘솔 타임코드가 돌고 있을 수 있다는 큰 알림(N11) — 정적 렌더로 보이는 글과 끄기 버튼을 단언한다.
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { ConsoleRunningBanner } from "./ConsoleRunningBanner";

describe("ConsoleRunningBanner", () => {
  it("콘솔이 돌 수 있으면 타임코드 번호와 끄기 버튼을 크게 보인다", () => {
    const html = renderToStaticMarkup(
      <ConsoleRunningBanner visible timecodeNumber={5} approvalPending={false} onStop={() => {}} />,
    );
    expect(html).toContain('role="alert"');
    expect(html).toContain("콘솔 Timecode 5 가 아직 돌고 있을 수 있어요");
    expect(html).toContain("■ 콘솔 끄기");
  });

  it("정지 카드를 기다리는 중이면 카드에서 승인하라고 말하고 버튼은 숨긴다(카드를 겹쳐 띄우지 않음)", () => {
    const html = renderToStaticMarkup(
      <ConsoleRunningBanner visible timecodeNumber={5} approvalPending onStop={() => {}} />,
    );
    expect(html).toContain("정지 승인 카드를 기다리고 있어요");
    expect(html).not.toContain("■ 콘솔 끄기");
  });

  it("안 보일 때는 아무것도 그리지 않는다", () => {
    expect(renderToStaticMarkup(<ConsoleRunningBanner visible={false} timecodeNumber={5} approvalPending={false} />)).toBe("");
  });
});
