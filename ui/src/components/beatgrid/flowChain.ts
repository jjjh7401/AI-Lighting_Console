// 반영 흐름 — 초안 「적용」 → 프리셋 저장 → 「⇪ 콘솔에 반영」 → 콘솔 재생의 단계 판정.
//
// 서버는 단계가 성공으로 끝났을 때만 `beat_grid_send_status.completed` 를 싣는다. 이 모듈은 그 값을
// 화면의 세 단계(프리셋 저장 · 반영 · 콘솔 재생)로 옮기고 다음 단계를 가리킨다. 순수 함수만 있다 —
// 승인 호출도, 콘솔 명령도, 송신도 없다(승인 카드는 감독이 직접 누르고, ▶ 도 늘 사람이 누른다).

export type FlowStep = "preset" | "reflect" | "console";

export const FLOW_STEPS: readonly FlowStep[] = ["preset", "reflect", "console"];

export const FLOW_STEP_LABEL: Record<FlowStep, string> = {
  preset: "1/3 프리셋 저장",
  reflect: "2/3 반영",
  console: "3/3 콘솔 재생",
};

/** 단계별 완료 여부. 상태를 바꿀 때는 새 객체로 만든다(아래 상수를 고치지 않는다). */
export type FlowDone = Record<FlowStep, boolean>;

export const NO_FLOW_DONE: FlowDone = Object.freeze({ preset: false, reflect: false, console: false });

/** 아직 끝나지 않은 첫 단계(`FLOW_STEPS` 순서). 셋 다 끝났으면 `null`. */
export function nextFlowStep(done: FlowDone): FlowStep | null {
  return FLOW_STEPS.find((step) => !done[step]) ?? null;
}

/** 이 응답이 어느 단계의 성공인가. `completed` 가 우선이고, 그게 없을 때만 성공한 콘솔 재생
 * (`last_action: "console_play"` + `ok`)을 3단계로 읽는다. 나머지는 `null`이다 — 거절·실패·미리보기·
 * 편집은 단계가 아니다. `"draft_applied"` 는 세 단계 앞의 출발점이라 `FlowStep` 이 아니다. */
export function completedStepOf(
  status: { completed?: string | null; last_action: string; ok: boolean } | null | undefined,
): "draft_applied" | FlowStep | null {
  if (!status) return null;
  switch (status.completed) {
    case "draft_applied":
      return "draft_applied";
    case "preset_saved":
      return "preset";
    case "reflected":
      return "reflect";
  }
  return status.last_action === "console_play" && status.ok ? "console" : null;
}

/** 다음이 「반영」일 때만 붙는 안내 한 줄 — 어느 타임코드 번호에 반영하는지. 초안에 적힌 번호가 먼저고,
 * 없으면 서버 권유 번호, 둘 다 없으면 번호를 정하라는 말이다. 다른 단계 앞에서는 `null`(말이 없다). */
export function flowNextText(
  next: FlowStep | null,
  timecodeNumber: number | null,
  suggestion: number | null,
): string | null {
  if (next !== "reflect") return null;
  if (timecodeNumber !== null) return `다음: 타임코드 ${timecodeNumber} 에 반영`;
  if (suggestion !== null) return `다음: 타임코드 ${suggestion} 에 반영`;
  return "다음: 타임코드 번호를 정한 뒤 반영";
}
