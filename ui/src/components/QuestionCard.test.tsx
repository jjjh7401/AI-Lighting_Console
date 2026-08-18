import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

import { QuestionCard } from "./QuestionCard";
import type { PendingQuestion } from "../protocol";

const QUESTION: PendingQuestion = {
  request_id: "q1",
  prompt: "콘솔에서 패치를 실행해 주세요 — Robin Esprite 20대.",
  why: "서버가 대신 실행하면 만들어지지 않습니다.",
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
    // 사용자가 앱에 실행을 다시 시키지 않도록 직접 실행을 명시한다.
    expect(html).toContain("콘솔 명령줄에 직접");
  });

  it("renders no command block when there is nothing to hand over", () => {
    const html = renderToStaticMarkup(
      <QuestionCard question={{ ...QUESTION, commands: [] }} onAnswer={vi.fn()} />,
    );
    expect(html).not.toContain("question-commands");
  });
});
