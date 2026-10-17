// @vitest-environment jsdom
// 반영 흐름 시험 — 서버가 단계 성공을 알리면(`beat_grid_send_status.completed`) 화면이 무엇을 하는가.
//
// 응답을 바꿔 가며 `<BeatGrid>` 를 다시 그려 본다(실제 앱에서 리듀서가 응답마다 새 객체를 만드는 것과
// 같다). 못박는 것: 초안 「적용」 뒤에는 **기존** 프리셋 계획 요청 하나만 가고, 그 밖의 단계는 화면
// 상태만 바꾼다 — 반영(`onApply`)·콘솔 재생(`onConsolePlay`)·정지(`onConsoleStop`)는 한 번도 안 불린다.
// DOM 이 필요해 `songAudioLinkRequest.test.tsx` 와 같은 방식(jsdom + `act`)이다.
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { BeatGridSendStatus, BeatGridView } from "../protocol";
import { BeatGrid, PRESET_PLAN_SLOW_MS, presetPlanWaiting, type BeatGridProps } from "./BeatGrid";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

// 칸이 없는 격자 — 상단 바와 띠만 본다(칸 모양은 다른 시험이 본다).
const GRID: BeatGridView = {
  song_title: "LOVE ATTACK",
  bar_range: { start: 0, end: 25 },
  tracks: [],
  scene_memos: [],
  probe_results: {},
  source: "empty",
  note: null,
  console_audio_offset_seconds: 0,
};

let container: HTMLElement;
let root: Root;

beforeEach(() => {
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(() => {
  act(() => root.unmount());
  container.remove();
});

/** 응답마다 새 객체 — 리듀서의 REPLACE 와 같다. */
function status(overrides: Partial<BeatGridSendStatus> = {}): BeatGridSendStatus {
  return {
    pending_apply_count: 0,
    last_action: "apply",
    ok: true,
    reason: null,
    blocked_cells: [],
    approval_vs_sent: null,
    ...overrides,
  };
}

function setup() {
  const handlers = {
    onPresetPlanRequest: vi.fn(),
    onApply: vi.fn(),
    onTimecodeSubmit: vi.fn(),
    onConsolePlay: vi.fn(),
    onConsoleStop: vi.fn(),
  };
  /** `key` 를 바꾸면 같은 응답 객체로 새 인스턴스가 마운트된다(전체화면을 나갔다 다시 들어오는 경우). */
  const render = (props: Partial<BeatGridProps> = {}, key = "grid") =>
    act(() => root.render(<BeatGrid key={key} grid={GRID} {...handlers} {...props} />));
  return { handlers, render };
}

function strip(): HTMLElement {
  const el = container.querySelector<HTMLElement>(".beat-grid-flow-strip");
  if (!el) throw new Error("flow strip not found");
  return el;
}

/** 띠 안 단계 글자 셋(앞 세 칸 — 그 뒤는 안내 문장). */
function stepTexts(): string[] {
  return Array.from(strip().querySelectorAll("span"))
    .slice(0, 3)
    .map((span) => span.textContent ?? "");
}

function currentStep(): string | null {
  return strip().querySelector('[aria-current="step"]')?.textContent ?? null;
}

function headerButton(textPart: string): HTMLButtonElement {
  const found = Array.from(container.querySelectorAll("header.beat-grid-topbar button")).find((button) =>
    (button.textContent ?? "").includes(textPart),
  );
  if (!found) throw new Error(`header button not found: ${textPart}`);
  return found as HTMLButtonElement;
}

const consoleFollowToggle = () => headerButton("콘솔 같이");
const applyButton = () => headerButton("⇪");

describe("초안 「적용」 뒤 — 프리셋 계획 요청", () => {
  it("마운트 때 이미 있던 draft_applied 응답으로는 요청하지 않는다 — 같은 응답으로 다시 그려도, 다시 마운트해도", () => {
    const { handlers, render } = setup();
    const existing = status({ completed: "draft_applied" });

    render({ sendStatus: existing });
    expect(handlers.onPresetPlanRequest).not.toHaveBeenCalled();

    render({ sendStatus: existing }); // 부모가 같은 응답으로 다시 그린다
    expect(handlers.onPresetPlanRequest).not.toHaveBeenCalled();

    render({ sendStatus: existing }, "remounted"); // 나갔다 다시 들어와 새 인스턴스가 마운트된다
    expect(handlers.onPresetPlanRequest).not.toHaveBeenCalled();

    // 대조군: 새 응답이 오면 반응한다 — 위 세 단언이 효과 자체가 죽어서 통과한 것이 아님을 보인다.
    render({ sendStatus: status({ completed: "draft_applied" }) }, "remounted");
    expect(handlers.onPresetPlanRequest).toHaveBeenCalledTimes(1);
  });

  it("새 draft_applied 응답이 오면 프리셋 계획 요청을 정확히 한 번 보내고, 반영은 보내지 않는다", () => {
    const { handlers, render } = setup();
    render({ sendStatus: null });
    expect(handlers.onPresetPlanRequest).not.toHaveBeenCalled();

    const applied = status({ completed: "draft_applied" });
    render({ sendStatus: applied });
    expect(handlers.onPresetPlanRequest).toHaveBeenCalledTimes(1);

    render({ sendStatus: applied }); // 같은 사건으로 다시 그려도 되풀이하지 않는다
    expect(handlers.onPresetPlanRequest).toHaveBeenCalledTimes(1);

    expect(handlers.onApply).not.toHaveBeenCalled();
    expect(handlers.onConsolePlay).not.toHaveBeenCalled();
    expect(handlers.onConsoleStop).not.toHaveBeenCalled();
  });

  it("초안 「적용」이 또 성공하면(새 응답 객체) 그때마다 한 번씩 요청한다", () => {
    const { handlers, render } = setup();
    render({ sendStatus: null });
    render({ sendStatus: status({ completed: "draft_applied" }) });
    render({ sendStatus: status({ completed: "draft_applied" }) });
    expect(handlers.onPresetPlanRequest).toHaveBeenCalledTimes(2);
    expect(handlers.onApply).not.toHaveBeenCalled();
  });

  it("요청 콜백이 없으면 아무것도 보내지 않고 조용히 넘어간다", () => {
    const { handlers, render } = setup();
    render({ sendStatus: null, onPresetPlanRequest: undefined });
    render({ sendStatus: status({ completed: "draft_applied" }), onPresetPlanRequest: undefined });
    expect(handlers.onPresetPlanRequest).not.toHaveBeenCalled();
    expect(handlers.onApply).not.toHaveBeenCalled();
    expect(stepTexts()).toEqual(["1/3 프리셋 저장", "2/3 반영", "3/3 콘솔 재생"]);
  });

  it("실패했거나 단계가 아닌 응답(completed 없음)으로는 아무것도 하지 않는다", () => {
    const { handlers, render } = setup();
    render({ sendStatus: null });
    render({ sendStatus: status({ last_action: "apply", ok: false, reason: "거절" }) });
    render({ sendStatus: status({ last_action: "edit" }) });
    render({ sendStatus: status({ last_action: "preview" }) });
    expect(handlers.onPresetPlanRequest).not.toHaveBeenCalled();
    expect(stepTexts()).toEqual(["1/3 프리셋 저장", "2/3 반영", "3/3 콘솔 재생"]);
    expect(currentStep()).toBe("1/3 프리셋 저장");
  });
});

describe("프리셋이 저장된 뒤 — 띠와 다음 안내", () => {
  it("권유 번호 12 가 오면 2/3 이 지금 단계이고, 12 번 쓰기를 누르면 그 번호를 올린다", () => {
    const { handlers, render } = setup();
    render({ sendStatus: null, timecodeNumber: null });
    render({
      sendStatus: status({ completed: "preset_saved", timecode_suggestion: 12 }),
      timecodeNumber: null,
    });

    expect(stepTexts()).toEqual(["✓ 1/3 프리셋 저장", "2/3 반영", "3/3 콘솔 재생"]);
    expect(currentStep()).toBe("2/3 반영");
    expect(strip().textContent).toContain("타임코드 12 에 반영");
    expect(applyButton().classList.contains("is-next")).toBe(true);

    const button = strip().querySelector("button");
    expect(button?.textContent).toBe("12 번 쓰기");
    expect(handlers.onTimecodeSubmit).not.toHaveBeenCalled();
    act(() => button?.click());
    expect(handlers.onTimecodeSubmit).toHaveBeenCalledTimes(1);
    expect(handlers.onTimecodeSubmit).toHaveBeenCalledWith(12);
    // 번호를 초안에 적는 것까지다 — 반영은 감독이 따로 누른다.
    expect(handlers.onApply).not.toHaveBeenCalled();
  });

  it("초안에 번호가 이미 있으면 그 번호를 말하고 번호 쓰기 버튼은 없다", () => {
    const { render } = setup();
    render({ sendStatus: null, timecodeNumber: 20 });
    render({
      sendStatus: status({ completed: "preset_saved", timecode_suggestion: 12 }),
      timecodeNumber: 20,
    });
    expect(strip().textContent).toContain("타임코드 20 에 반영");
    expect(strip().textContent).not.toContain("타임코드 12");
    expect(strip().querySelector("button")).toBeNull();
  });

  it("권유 번호가 없으면(서버가 키를 싣지 않았다) 번호를 정하라고 말한다", () => {
    const { render } = setup();
    render({ sendStatus: null, timecodeNumber: null });
    render({ sendStatus: status({ completed: "preset_saved" }), timecodeNumber: null });
    expect(currentStep()).toBe("2/3 반영");
    expect(strip().textContent).toContain("다음: 타임코드 번호를 정한 뒤 반영");
    expect(strip().querySelector("button")).toBeNull();
  });
});

describe("반영이 끝난 뒤 — 「콘솔 같이」", () => {
  it("반영이 끝나면 3/3 이 지금 단계이고 「콘솔 같이」가 켜지지만 재생은 보내지 않는다", () => {
    const { handlers, render } = setup();
    render({ sendStatus: null });
    render({ sendStatus: status({ completed: "preset_saved" }) });
    expect(consoleFollowToggle().getAttribute("aria-pressed")).toBe("false");

    render({ sendStatus: status({ completed: "reflected" }) });
    expect(stepTexts()).toEqual(["✓ 1/3 프리셋 저장", "✓ 2/3 반영", "3/3 콘솔 재생"]);
    expect(currentStep()).toBe("3/3 콘솔 재생");
    expect(consoleFollowToggle().getAttribute("aria-pressed")).toBe("true");
    expect(applyButton().classList.contains("is-next")).toBe(false);

    // 켜 두기만 한다 — ▶ 는 감독이 누른다.
    expect(handlers.onConsolePlay).not.toHaveBeenCalled();
    expect(handlers.onConsoleStop).not.toHaveBeenCalled();
    expect(handlers.onApply).not.toHaveBeenCalled();
  });

  it("completed 없는 반영 응답(승인과 보낸 것이 어긋남)이면 「콘솔 같이」는 켜지지 않고 반영 ✓ 도 없다", () => {
    const { handlers, render } = setup();
    render({ sendStatus: null });
    render({
      sendStatus: status({
        last_action: "apply",
        ok: true,
        approval_vs_sent: {
          sha256: "abc",
          cell_count: 3,
          match: false,
          sent_not_approved: ["BACK 3마디"],
          approved_not_sent: [],
        },
      }),
    });
    expect(consoleFollowToggle().getAttribute("aria-pressed")).toBe("false");
    expect(stepTexts()[1]).toBe("2/3 반영");
    expect(handlers.onConsolePlay).not.toHaveBeenCalled();
  });

  it("콘솔 재생 콜백이 없으면 토글은 꺼진 채 비활성이고 아무 일도 없다", () => {
    const { handlers, render } = setup();
    render({ sendStatus: null, onConsolePlay: undefined, onConsoleStop: undefined });
    render({
      sendStatus: status({ completed: "reflected" }),
      onConsolePlay: undefined,
      onConsoleStop: undefined,
    });
    const toggle = consoleFollowToggle();
    expect(toggle.disabled).toBe(true);
    expect(toggle.getAttribute("aria-pressed")).toBeNull();
    expect(toggle.textContent).toBe("콘솔 같이 끔");
    expect(stepTexts()[1]).toBe("✓ 2/3 반영");
    expect(handlers.onConsolePlay).not.toHaveBeenCalled();
  });
});

describe("콘솔 재생이 성공한 뒤", () => {
  it("성공한 콘솔 재생 응답이면 3/3 에 ✓ 가 붙는다", () => {
    const { render } = setup();
    render({ sendStatus: null });
    render({ sendStatus: status({ last_action: "console_play", ok: true }) });
    expect(stepTexts()[2]).toBe("✓ 3/3 콘솔 재생");
  });

  it("거절된 콘솔 재생 응답이면 ✓ 가 없다", () => {
    const { render } = setup();
    render({ sendStatus: null });
    render({ sendStatus: status({ last_action: "console_play", ok: false, reason: "반영 기록 없음" }) });
    expect(stepTexts()[2]).toBe("3/3 콘솔 재생");
  });
});

describe("처음부터 끝까지", () => {
  it("초안 적용 → 프리셋 저장 → 반영 → 콘솔 재생: 계획 요청 한 번뿐, 반영·재생·정지·번호 쓰기는 한 번도 보내지 않는다", () => {
    const { handlers, render } = setup();
    render({ sendStatus: null });
    render({ sendStatus: status({ completed: "draft_applied" }) });
    render({ sendStatus: status({ completed: "preset_saved", timecode_suggestion: 12 }) });
    render({ sendStatus: status({ completed: "reflected" }) });
    render({ sendStatus: status({ last_action: "console_play", ok: true }) });

    expect(stepTexts()).toEqual(["✓ 1/3 프리셋 저장", "✓ 2/3 반영", "✓ 3/3 콘솔 재생"]);
    expect(strip().querySelector("[aria-current]")).toBeNull();
    expect(handlers.onPresetPlanRequest).toHaveBeenCalledTimes(1);
    expect(handlers.onApply).not.toHaveBeenCalled();
    expect(handlers.onConsolePlay).not.toHaveBeenCalled();
    expect(handlers.onConsoleStop).not.toHaveBeenCalled();
    expect(handlers.onTimecodeSubmit).not.toHaveBeenCalled();
  });

  it("새 초안을 적용하면 앞 흐름의 ✓ 와 번호 권유를 지우고 처음부터 다시 안내한다", () => {
    const { handlers, render } = setup();
    render({ sendStatus: null });
    render({ sendStatus: status({ completed: "preset_saved", timecode_suggestion: 12 }) });
    expect(stepTexts()[0]).toBe("✓ 1/3 프리셋 저장");
    expect(strip().querySelector("button")?.textContent).toBe("12 번 쓰기");

    render({ sendStatus: status({ completed: "draft_applied" }) });
    expect(stepTexts()).toEqual(["1/3 프리셋 저장", "2/3 반영", "3/3 콘솔 재생"]);
    expect(currentStep()).toBe("1/3 프리셋 저장");
    expect(strip().querySelector("button")).toBeNull();
    expect(handlers.onPresetPlanRequest).toHaveBeenCalledTimes(1);
  });
});

describe("초안 「적용」 뒤 — 프리셋 계획을 기다리는 동안 (1차 전체 실행 E-02)", () => {
  const waitLine = () => container.querySelector(".beat-grid-preset-plan-wait")?.textContent ?? null;
  const planButton = () =>
    Array.from(container.querySelectorAll("button")).find((button) =>
      (button.textContent ?? "").includes("프리셋 계획 만들기"),
    );

  it("자동 요청 뒤 계획표가 오기 전까지 「만드는 중」을 보이고, 서랍에서 다시 눌러도 두 번 보내지 않는다", () => {
    const { handlers, render } = setup();
    const onDrawerRequest = vi.fn(); // 서랍 단추는 이 콜백이 있을 때만 그려진다
    render({ sendStatus: null, onDrawerRequest });
    expect(waitLine()).toBeNull();
    render({ sendStatus: status({ completed: "draft_applied" }), onDrawerRequest });
    expect(handlers.onPresetPlanRequest).toHaveBeenCalledTimes(1);
    expect(waitLine()).toContain("요청을 이미 보냈어요");
    act(() => headerButton("▤").click());
    const button = planButton();
    expect(button).toBeDefined();
    act(() => button?.click());
    expect(handlers.onPresetPlanRequest).toHaveBeenCalledTimes(1);
  });

  it("서버가 busy 로 거절하면 「만드는 중」은 내린다", () => {
    const { render } = setup();
    render({ sendStatus: null, busyCount: 0 });
    const applied = status({ completed: "draft_applied" });
    render({ sendStatus: applied, busyCount: 0 });
    expect(waitLine()).toContain("요청을 이미 보냈어요");
    render({ sendStatus: applied, busyCount: 1 });
    expect(waitLine()).toBeNull();
  });
});

describe("presetPlanWaiting", () => {
  it("기다림 → 늦음 → (계획표·busy) 끝", () => {
    const pending = { busyAt: 0, at: 1_000 };
    expect(presetPlanWaiting(null, false, 0, 2_000)).toBeNull();
    expect(presetPlanWaiting(pending, false, 0, 2_000)).toBe("waiting");
    expect(presetPlanWaiting(pending, false, 0, 1_000 + PRESET_PLAN_SLOW_MS)).toBe("slow");
    expect(presetPlanWaiting(pending, true, 0, 2_000)).toBeNull();
    expect(presetPlanWaiting(pending, false, 1, 2_000)).toBeNull();
  });
});
