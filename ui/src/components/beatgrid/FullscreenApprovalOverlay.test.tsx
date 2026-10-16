// 전체화면 + 대기 승인 → 승인 카드가 전체화면 위에 보인다(감독 실화면: 카드가 채팅 열 뒤에 묻혔다).
// DOM 시험대가 없어 정적 렌더(`renderToStaticMarkup`)로 그려진 글을 단언한다.
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { PendingApproval } from "../../protocol";
import { ApplyProgressNote } from "../BeatGridTopBar";
import { FullscreenApprovalOverlay } from "./FullscreenApprovalOverlay";

const approval: PendingApproval = {
  request_id: "req-1",
  items: [{ command: "Store Preset 21.2", risk_reasons: ["프리셋 저장"], warnings: ["덮어쓰기"] }],
};

describe("FullscreenApprovalOverlay", () => {
  it("대기 승인이 있으면 승인 카드(승인·거부·명령 펼치기)를 겹쳐 보인다", () => {
    const html = renderToStaticMarkup(<FullscreenApprovalOverlay approvals={[approval]} onDecision={() => {}} />);
    expect(html).toContain('class="beat-grid-approval-overlay"');
    expect(html).toContain('role="dialog"');
    expect(html).toContain("승인 대기 — 위험 명령");
    expect(html).toContain("프리셋 저장");
    expect(html).toContain("⚠ 덮어쓰기");
    expect(html).toMatch(/commands-toggle[^>]*>.*명령.*1.*개.*펼치기/);
    expect(html).toContain(">승인</button>");
    expect(html).toContain(">거부</button>");
  });

  it("승인이 여러 개면 전부 보인다", () => {
    const second = { ...approval, request_id: "req-2" };
    const html = renderToStaticMarkup(
      <FullscreenApprovalOverlay approvals={[approval, second]} onDecision={() => {}} />,
    );
    expect(html.match(/class="approval-card"/g)).toHaveLength(2);
  });

  it("대기 승인이 없으면 아무것도 그리지 않는다", () => {
    expect(renderToStaticMarkup(<FullscreenApprovalOverlay approvals={[]} onDecision={() => {}} />)).toBe("");
  });
});

describe("ApplyProgressNote 진행 문구", () => {
  const text = "승인 카드를 기다리는 중 · 106초";
  it("승인 대기 중이면 문구가 카드로 가는 버튼이 된다", () => {
    const html = renderToStaticMarkup(<ApplyProgressNote text={text} onClick={() => {}} />);
    expect(html).toMatch(/^<button[^>]*beat-grid-apply-progress-link[^>]*>승인 카드를 기다리는 중 · 106초 — 승인 카드 보기<\/button>$/);
  });
  it("누를 곳이 없으면 기존처럼 글만", () => {
    expect(renderToStaticMarkup(<ApplyProgressNote text={text} />)).toBe(
      '<span class="beat-grid-apply-progress" role="status">승인 카드를 기다리는 중 · 106초</span>',
    );
  });
});
