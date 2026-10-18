// 승인 카드 머리 (WT-approval-card-text) — 앱 소유 묶음은 감독 말로 머리를 쓰고, 영어 게이트 사유는
// 「자세히」 접기 안에만 둔다. 경고는 접지 않는다(안전 신호). 승인·거부 판정은 그대로다.
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { ApprovalCard } from "./ApprovalCard";

describe("ApprovalCard — 앱 소유 묶음 머리", () => {
  it("머리는 감독 말이고, 영어 게이트 사유는 「자세히」 접기 안에만 있다", () => {
    const html = renderToStaticMarkup(
      <ApprovalCard
        approval={{
          request_id: "req-1",
          title: "러브어택 재생 시작 — 쇼 백업 1 · 이 곡 시퀀스 11개 끄기 · TC5 처음으로·재생",
          items: [
            { command: "SaveShow", risk_reasons: ["showfile backup (REQ-MVP-017 rule 3)"], warnings: [] },
            { command: "Top Timecode 5", risk_reasons: ["reference-invoking command"], warnings: [] },
          ],
        }}
        onDecision={() => {}}
      />,
    );

    expect(html).toContain('<div class="approval-title">러브어택 재생 시작 — 쇼 백업 1');
    const foldStart = html.indexOf("<details");
    expect(foldStart).toBeGreaterThan(-1);
    const fold = html.slice(foldStart, html.indexOf("</details>"));
    expect(fold).toContain("<summary>자세히</summary>");
    expect(fold).toContain("reference-invoking command");
    expect(html.slice(0, foldStart)).not.toContain("reference-invoking command");
  });
});
