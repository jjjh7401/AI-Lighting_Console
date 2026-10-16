// 반영 흐름 단계 판정 시험 — 순수 함수만 부른다(화면은 TopBar·BeatGrid 시험이 본다).
import { describe, expect, it } from "vitest";

import {
  FLOW_STEPS,
  FLOW_STEP_LABEL,
  NO_FLOW_DONE,
  completedStepOf,
  flowNextText,
  nextFlowStep,
  type FlowDone,
  type FlowStep,
} from "./flowChain";

describe("단계 이름", () => {
  it("세 단계는 프리셋 저장 → 반영 → 콘솔 재생 순서이고 글자는 한 자도 다르지 않다", () => {
    expect(FLOW_STEPS).toEqual(["preset", "reflect", "console"]);
    expect(FLOW_STEP_LABEL).toEqual({
      preset: "1/3 프리셋 저장",
      reflect: "2/3 반영",
      console: "3/3 콘솔 재생",
    });
  });

  it("처음에는 아무 단계도 끝나지 않았다", () => {
    expect(NO_FLOW_DONE).toEqual({ preset: false, reflect: false, console: false });
  });
});

describe("nextFlowStep — 끝나지 않은 첫 단계", () => {
  // [프리셋, 반영, 콘솔] 끝남 여부 8가지 전부와 기대 값을 손으로 적었다.
  const cases: [FlowDone, FlowStep | null][] = [
    [{ preset: false, reflect: false, console: false }, "preset"],
    [{ preset: true, reflect: false, console: false }, "reflect"],
    [{ preset: false, reflect: true, console: false }, "preset"],
    [{ preset: true, reflect: true, console: false }, "console"],
    [{ preset: false, reflect: false, console: true }, "preset"],
    [{ preset: true, reflect: false, console: true }, "reflect"],
    [{ preset: false, reflect: true, console: true }, "preset"],
    [{ preset: true, reflect: true, console: true }, null],
  ];

  it.each(cases)("%j → %s", (done, expected) => {
    expect(nextFlowStep(done)).toBe(expected);
  });
});

describe("completedStepOf — 이 응답이 어느 단계의 성공인가", () => {
  const base = { last_action: "apply", ok: true } as const;

  it("completed 가 단계를 가리킨다", () => {
    expect(completedStepOf({ ...base, completed: "draft_applied" })).toBe("draft_applied");
    expect(completedStepOf({ ...base, completed: "preset_saved" })).toBe("preset");
    expect(completedStepOf({ ...base, completed: "reflected" })).toBe("reflect");
  });

  it("성공한 콘솔 재생(console_play + ok)은 3단계다", () => {
    expect(completedStepOf({ last_action: "console_play", ok: true })).toBe("console");
  });

  it("거절된 콘솔 재생은 단계가 아니다", () => {
    expect(completedStepOf({ last_action: "console_play", ok: false })).toBeNull();
  });

  it("completed 가 없는 성공 응답(편집·반영 불일치 등)은 단계가 아니다", () => {
    expect(completedStepOf({ last_action: "edit", ok: true })).toBeNull();
    expect(completedStepOf({ last_action: "apply", ok: true })).toBeNull();
    expect(completedStepOf({ last_action: "apply", ok: true, completed: null })).toBeNull();
  });

  it("알 수 없는 completed 값은 단계로 읽지 않는다", () => {
    expect(completedStepOf({ ...base, completed: "something_else" })).toBeNull();
  });

  it("응답이 없으면 null", () => {
    expect(completedStepOf(null)).toBeNull();
    expect(completedStepOf(undefined)).toBeNull();
  });
});

describe("flowNextText — 다음이 반영일 때만 말한다", () => {
  it("초안에 적힌 타임코드 번호가 있으면 그 번호", () => {
    expect(flowNextText("reflect", 20, null)).toBe("다음: 타임코드 20 에 반영");
    // 초안 번호가 권유 번호보다 먼저다.
    expect(flowNextText("reflect", 20, 12)).toBe("다음: 타임코드 20 에 반영");
  });

  it("초안 번호가 없고 서버가 번호를 권했으면 그 번호", () => {
    expect(flowNextText("reflect", null, 12)).toBe("다음: 타임코드 12 에 반영");
  });

  it("둘 다 없으면 번호를 정하라는 말", () => {
    expect(flowNextText("reflect", null, null)).toBe("다음: 타임코드 번호를 정한 뒤 반영");
  });

  it("다른 단계 앞에서는 말이 없다", () => {
    expect(flowNextText("preset", 20, 12)).toBeNull();
    expect(flowNextText("console", 20, 12)).toBeNull();
    expect(flowNextText(null, 20, 12)).toBeNull();
  });
});
