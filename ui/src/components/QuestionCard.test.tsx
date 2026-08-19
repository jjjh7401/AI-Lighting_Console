import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

import { joinChosenLabels, QuestionCard, toggleChosenLabel } from "./QuestionCard";
import type { PendingQuestion } from "../protocol";

const QUESTION: PendingQuestion = {
  request_id: "q1",
  prompt: "콘솔에서 Patch 편집기를 열어 주세요 — Robin Esprite 20대.",
  why: "실행은 앱이 하니 편집기만 열어 두시면 됩니다.",
  steps: ["Patch 편집기를 엽니다."],
  commands: ["Plugin \"PatchEsprite\""],
  options: [],
  multi: false,
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

describe("QuestionCard multi-select", () => {
  const FAMILIES: PendingQuestion = {
    ...QUESTION,
    prompt: "어느 계열을 설정할까요?",
    commands: [],
    options: [
      { label: "기본 포지션 프리셋", description: "Position 풀" },
      { label: "기본 컬러 프리셋", description: "Color 풀" },
      { label: "콤보 페이저 프리셋", description: "All 1 풀" },
    ],
    multi: true,
  };

  it("renders checkboxes and a confirm button when multi", () => {
    const html = renderToStaticMarkup(
      <QuestionCard question={FAMILIES} onAnswer={vi.fn()} />,
    );
    expect(html).toContain('type="checkbox"');
    expect(html).toContain("question-option-check");
    expect(html).toContain("확인");
    // 단일 선택 버튼으로 되돌아가면 첫 클릭이 곧 답이 되어 나머지 계열이 사라진다.
    expect(html).not.toContain('class="question-option"');
    // 선택지가 하나도 빠지지 않는다.
    for (const option of FAMILIES.options) {
      expect(html).toContain(option.label);
    }
  });

  it("disables the confirm button until something is checked", () => {
    const html = renderToStaticMarkup(
      <QuestionCard question={FAMILIES} onAnswer={vi.fn()} />,
    );
    // 초기 상태 = 0개 선택. 빈 답이 서버로 나가면 계열을 하나도 못 고른 채 진행된다.
    expect(html).toMatch(/question-option-confirm[^>]*disabled/);
    // 컨트롤드 체크박스가 비어 있는 상태로 출발한다 — 미리 켜져 있으면 사용자가
    // 고르지도 않은 계열이 답에 실린다.
    expect(html).not.toContain("checked");
  });

  it("keeps the single-select buttons when not multi", () => {
    const html = renderToStaticMarkup(
      <QuestionCard question={{ ...FAMILIES, multi: false }} onAnswer={vi.fn()} />,
    );
    expect(html).toContain('class="question-option"');
    expect(html).not.toContain('type="checkbox"');
    expect(html).not.toContain("question-option-confirm");
  });

  it("keeps the freeform box on both shapes", () => {
    for (const multi of [true, false]) {
      const html = renderToStaticMarkup(
        <QuestionCard question={{ ...FAMILIES, multi }} onAnswer={vi.fn()} />,
      );
      expect(html).toContain("question-freeform");
    }
  });
});

describe("joinChosenLabels — 다중 선택 답 형식", () => {
  const OPTIONS = [
    { label: "기본 포지션 프리셋" },
    { label: "기본 컬러 프리셋" },
    { label: "콤보 페이저 프리셋" },
  ];

  it("joins the chosen labels with a comma + space", () => {
    expect(joinChosenLabels(OPTIONS, ["기본 포지션 프리셋", "콤보 페이저 프리셋"])).toBe(
      "기본 포지션 프리셋, 콤보 페이저 프리셋",
    );
  });

  it("uses the card's order, not the click order", () => {
    // 서버는 고른 계열을 이 순서로 처리한다 — 클릭 순서가 처리 순서를 흔들면 안 된다.
    expect(joinChosenLabels(OPTIONS, ["콤보 페이저 프리셋", "기본 포지션 프리셋"])).toBe(
      "기본 포지션 프리셋, 콤보 페이저 프리셋",
    );
  });

  it("returns an empty string when nothing is chosen", () => {
    // 확인 버튼이 비활성인 상태와 짝을 이룬다 — 빈 답은 서버로 나가지 않는다.
    expect(joinChosenLabels(OPTIONS, [])).toBe("");
  });

  it("ignores a label that is not on the card", () => {
    expect(joinChosenLabels(OPTIONS, ["없는 계열", "기본 컬러 프리셋"])).toBe(
      "기본 컬러 프리셋",
    );
  });
});

describe("toggleChosenLabel — 체크박스 하나가 바뀐 뒤", () => {
  it("adds a newly checked label", () => {
    expect(toggleChosenLabel(["기본 컬러 프리셋"], "기본 포지션 프리셋", true)).toEqual([
      "기본 컬러 프리셋",
      "기본 포지션 프리셋",
    ]);
  });

  it("removes an unchecked label and leaves the rest", () => {
    expect(
      toggleChosenLabel(["기본 컬러 프리셋", "기본 포지션 프리셋"], "기본 컬러 프리셋", false),
    ).toEqual(["기본 포지션 프리셋"]);
  });

  it("never stores the same label twice", () => {
    // 두 번 실리면 답에 같은 계열이 두 번 들어가고 서버가 그것을 두 번 실행한다.
    expect(toggleChosenLabel(["기본 컬러 프리셋"], "기본 컬러 프리셋", true)).toEqual([
      "기본 컬러 프리셋",
    ]);
  });

  it("is a no-op when unchecking something that was never chosen", () => {
    expect(toggleChosenLabel(["기본 컬러 프리셋"], "콤보 페이저 프리셋", false)).toEqual([
      "기본 컬러 프리셋",
    ]);
  });

  it("does not mutate the previous list", () => {
    const previous = ["기본 컬러 프리셋"];
    toggleChosenLabel(previous, "기본 포지션 프리셋", true);
    expect(previous).toEqual(["기본 컬러 프리셋"]);
  });
});
