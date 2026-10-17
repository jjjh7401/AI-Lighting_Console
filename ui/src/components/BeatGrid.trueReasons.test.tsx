// @vitest-environment jsdom
// 카드 WT-true-reasons — 서버가 거절·차단한 진짜 사유와 오래 걸리는 요청의 진행 표시가 전체화면에 보이는가.
//
// 새 곡 점검(2026-10-18) 사례 2: 「자동 배치」를 누른 뒤 초안이 오기까지(실측 58~100초) 화면이 조용했고,
// 거절되면 사유가 채팅(전체화면 뒤)에만 갔다. 서버는 이제 거절 사유를 상태 응답에도 싣는다
// (`server/tests/test_beat_grid_true_reasons.py`). 이 시험은 화면 쪽 — 기다리는 동안의 문구, 사유
// 문자열 그대로의 표시를 잰다.
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import type { BeatGridSendStatus, BeatGridView } from "../protocol";
import {
  BeatGrid,
  type BeatGridProps,
  DRAFT_PROPOSE_BUSY_MESSAGE,
  DRAFT_PROPOSE_WAITING_MESSAGE,
  applyFailureNote,
  draftProposeState,
} from "./BeatGrid";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

function emptyGrid(): BeatGridView {
  return {
    song_title: "LOVE ATTACK",
    bar_range: { start: 0, end: 25 },
    tracks: [],
    scene_memos: [],
    probe_results: {},
    source: "empty",
    note: null,
    console_audio_offset_seconds: 0,
  } as unknown as BeatGridView;
}

function failed(last_action: string, reason: string): BeatGridSendStatus {
  return { last_action, ok: false, reason, pending_apply_count: 0 } as unknown as BeatGridSendStatus;
}

const NO_BAR_MAP = "마디 지도가 없어 자동 배치를 만들 수 없습니다. 곡 오디오를 먼저 분석하세요.";

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

function render(props: Partial<BeatGridProps>) {
  act(() => root.render(<BeatGrid grid={emptyGrid()} {...props} />));
}

function draftButton(): HTMLButtonElement {
  const button = [...container.querySelectorAll("button")].find((b) => b.textContent?.startsWith("자동 배치"));
  if (!button) throw new Error("자동 배치 버튼이 없다");
  return button as HTMLButtonElement;
}

describe("자동 배치 요청 — 기다리는 동안과 거절", () => {
  it("누르면 만드는 중 문구가 뜨고 버튼이 잠긴다", () => {
    let asked = 0;
    render({ onDraftPropose: () => asked++, sendStatus: null, busyCount: 0 });

    act(() => draftButton().click());

    expect(asked).toBe(1);
    expect(container.textContent).toContain(DRAFT_PROPOSE_WAITING_MESSAGE);
    expect(draftButton().disabled).toBe(true);
    expect(draftButton().textContent).toBe("자동 배치 만드는 중…");
  });

  it("거절 상태가 오면 만드는 중을 풀고 서버 사유를 그대로 보인다", () => {
    const onDraftPropose = () => {};
    render({ onDraftPropose, sendStatus: null, busyCount: 0 });
    act(() => draftButton().click());

    render({ onDraftPropose, sendStatus: failed("edit", NO_BAR_MAP), busyCount: 0 });

    expect(container.textContent).not.toContain(DRAFT_PROPOSE_WAITING_MESSAGE);
    expect(container.textContent).toContain(`⚠ 격자에 적용 안 됨 — ${NO_BAR_MAP}`);
    expect(draftButton().disabled).toBe(false);
  });

  it("요청 뒤 busy 가 오면 거절 문구로 바꾼다", () => {
    const onDraftPropose = () => {};
    render({ onDraftPropose, sendStatus: null, busyCount: 2 });
    act(() => draftButton().click());

    render({ onDraftPropose, sendStatus: null, busyCount: 3 });

    expect(container.textContent).toContain(DRAFT_PROPOSE_BUSY_MESSAGE);
  });
});

describe("프리셋 계획 요청 — 거절되면 만드는 중을 푼다", () => {
  it("초안 적용 뒤 자동 계획 요청이 거절되면 「만드는 중」 대신 서버 사유가 보인다", () => {
    const onPresetPlanRequest = () => {};
    const reason = "수정할 박자 격자가 아직 없습니다.";
    render({ onPresetPlanRequest, sendStatus: null, lastServerReply: { text: "x", seq: 1 } });
    // 초안 적용 성공 응답 → 화면이 프리셋 계획을 자동으로 요청한다.
    render({
      onPresetPlanRequest,
      sendStatus: { last_action: "edit", ok: true, reason: null, completed: "draft_applied" } as never,
      lastServerReply: { text: "x", seq: 1 },
    });
    expect(container.textContent).toContain("프리셋 계획 요청을 이미 보냈어요");

    render({
      onPresetPlanRequest,
      sendStatus: failed("edit", reason),
      lastServerReply: { text: `박자 격자를 수정하지 않았습니다 — ${reason}`, seq: 2, summary: "박자 격자 수정 거절" },
    });

    expect(container.textContent).not.toContain("프리셋 계획 요청을 이미 보냈어요");
    expect(container.textContent).toContain(`⚠ 격자에 적용 안 됨 — ${reason}`);
  });
});

describe("draftProposeState", () => {
  const before = failed("apply", "앞 결과");
  it("요청 전이면 아무것도 없다", () => {
    expect(draftProposeState(null, false, before, 0)).toBeNull();
  });
  it("초안이 뜨면 끝난다", () => {
    expect(draftProposeState({ busyAt: 0, status: before }, true, before, 0)).toBeNull();
  });
  it("누를 때 있던 상태 응답은 이번 답이 아니다", () => {
    expect(draftProposeState({ busyAt: 0, status: before }, false, before, 0)).toBe("waiting");
  });
});

describe("applyFailureNote — 미리보기 실패도 사유를 보인다", () => {
  it("미리보기 거절 사유를 그대로 싣는다", () => {
    const reason =
      "미리보기 명령이 실행되지 않았습니다 — 승인 카드가 거절됐거나 시간 안에 승인되지 않아 아무것도 보내지 않았습니다.";
    expect(applyFailureNote(failed("preview", reason))).toBe(`⚠ 콘솔 미리보기 안 됨 — ${reason}`);
  });
});
