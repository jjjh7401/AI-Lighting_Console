import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

import { QuestionCard } from "./QuestionCard";
import type { PendingQuestion } from "../protocol";

const QUESTION: PendingQuestion = {
  request_id: "q1",
  prompt: "콘솔에서 Patch 편집기를 열어 주세요 — Robin Esprite 20대.",
  why: "실행은 앱이 하니 편집기만 열어 두시면 됩니다.",
  steps: ["Patch 편집기를 엽니다."],
  commands: ["Plugin \"PatchEsprite\""],
  options: [],
};

describe("QuestionCard handover commands", () => {
  it("renders each command verbatim with a copy button", () => {
    const html = renderToStaticMarkup(
      <QuestionCard question={QUESTION} onAnswer={vi.fn()} />,
    );
    expect(html).toContain("Plugin &quot;PatchEsprite&quot;");
    expect(html).toContain("명령 복사");
    // 서버-실행 모델: 명령은 자동 실행 실패 시의 대비책이다. 구모델 문구
    // («앱이 대신 실행하면 동작하지 않습니다»)로 되돌아가지 않게 고정한다.
    expect(html).toContain("대신 실행");
    expect(html).toContain("자동 실행이 또 실패할 때만");
    expect(html).not.toContain("앱이 대신 실행하면 동작하지 않습니다");
  });

  it("renders no command block when there is nothing to hand over", () => {
    const html = renderToStaticMarkup(
      <QuestionCard question={{ ...QUESTION, commands: [] }} onAnswer={vi.fn()} />,
    );
    expect(html).not.toContain("question-commands");
  });
});
