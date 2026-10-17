// SPEC-LDARRANGE-001 — 자동 배치 초안 보류 상태: 받기와 소비(화면 상태 전이).
import { describe, expect, it } from "vitest";

import { type BeatGridDraft, initialState, reduceServerEvent } from "./protocol";

const DRAFT: BeatGridDraft = {
  draft_id: "d-1",
  bar_range: { start: 0, end: 25 },
  windows: [],
  tracks: [
    {
      group_name: "FOH",
      group_no: 3,
      group_no_confirmed: true,
      layer_role: "key",
      cells: [
        { bar: 3, label: "FOH 초안 1" },
        { bar: 7, label: "FOH 초안 2" },
      ],
    },
  ],
};

describe("자동 배치 초안 보류 상태", () => {
  it("beat_grid_draft 를 받으면 보류 초안이 생긴다", () => {
    const next = reduceServerEvent(initialState, { v: 1, type: "beat_grid_draft", ...DRAFT });
    expect(next.pendingBeatGridDraft).toEqual(DRAFT);
  });

  it("콘솔 장비 대조(console_coverage)를 그대로 싣는다 — 빠진 장비 안내가 사라지지 않게(WT-all-fixtures)", () => {
    const console_coverage = {
      added: ["KEY"],
      uncovered: [{ fid: 621, group_names: ["HAZE"], reason: "일부러 뺌: 연기 장비(연출 대상 아님)", intentional: true }],
      unread: [],
    };
    const next = reduceServerEvent(initialState, { v: 1, type: "beat_grid_draft", ...DRAFT, console_coverage });
    expect(next.pendingBeatGridDraft?.console_coverage).toEqual(console_coverage);
  });

  it("같은 id 의 consumed 를 받으면 보류 초안을 지운다", () => {
    const held = reduceServerEvent(initialState, { v: 1, type: "beat_grid_draft", ...DRAFT });
    const next = reduceServerEvent(held, { v: 1, type: "beat_grid_draft_consumed", draft_id: "d-1" });
    expect(next.pendingBeatGridDraft).toBeNull();
  });

  it("다른 id 의 consumed 는 보류 초안을 건드리지 않는다", () => {
    const held = reduceServerEvent(initialState, { v: 1, type: "beat_grid_draft", ...DRAFT });
    const next = reduceServerEvent(held, { v: 1, type: "beat_grid_draft_consumed", draft_id: "other" });
    expect(next).toBe(held);
  });
});
