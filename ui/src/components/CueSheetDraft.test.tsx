// t281 — 초안 편집이 화면에서 어떻게 결정되는지. 이 프로젝트에는 jsdom/RTL
// 하네스가 없으므로(CueSheetTimeline.test.tsx 와 같은 관례) 렌더가 아니라
// 렌더를 결정하는 순수 함수와 프레임 빌더를 잰다.
import { describe, expect, it } from "vitest";

import type { SongTimelineView } from "../protocol";
import { buildChat, buildTimelineDraftRedo, buildTimelineDraftUndo } from "../protocol";
import { CUE_SHEET_EXAMPLE } from "./cueSheetExample";
import { draftBadgeText, draftChangeReport } from "./CueSheetTimeline";

function withDraft(draft: SongTimelineView["draft"]): SongTimelineView {
  return { ...CUE_SHEET_EXAMPLE, draft };
}

describe("초안 배지", () => {
  it("표식이 없는 타임라인은 배지를 안 그린다 (기존 페이로드 호환)", () => {
    expect(draftBadgeText(CUE_SHEET_EXAMPLE)).toBeNull();
  });

  it("dirty=false 는 「수정됨」이 아니다 — 되돌려 원본으로 돌아온 상태", () => {
    expect(draftBadgeText(withDraft({ dirty: false, depth: 0, last_change: [] }))).toBeNull();
  });

  it("수정된 초안은 되돌리기 단계 수까지 적는다", () => {
    expect(draftBadgeText(withDraft({ dirty: true, depth: 2, last_change: [] }))).toBe(
      "수정됨 · 미저장 (되돌리기 2단계)",
    );
  });
});

describe("변경 보고", () => {
  it("직전 편집의 칸별 보고를 그대로 내보낸다 — 눈으로 diff 하지 않게", () => {
    expect(
      draftChangeReport(withDraft({ dirty: true, depth: 1, last_change: ["조도 40 → 60"] })),
    ).toEqual(["조도 40 → 60"]);
  });

  it("표식이 없으면 빈 배열이다 (undefined 를 그리지 않는다)", () => {
    expect(draftChangeReport(CUE_SHEET_EXAMPLE)).toEqual([]);
  });
});

describe("chat 프레임의 선택 전달", () => {
  it("선택이 있으면 selected_cue 를 싣는다", () => {
    expect(JSON.parse(buildChat("이 구간 더 밝게", 3))).toEqual({
      v: 1,
      type: "chat",
      text: "이 구간 더 밝게",
      selected_cue: 3,
    });
  });

  it("선택이 없으면 필드 자체가 없다 — 기존 서버와 호환된다", () => {
    expect(JSON.parse(buildChat("안녕"))).toEqual({ v: 1, type: "chat", text: "안녕" });
    expect(JSON.parse(buildChat("안녕", null))).toEqual({ v: 1, type: "chat", text: "안녕" });
  });

  it("0·음수·소수는 큐 번호가 아니므로 싣지 않는다", () => {
    for (const bad of [0, -1, 1.5]) {
      expect(JSON.parse(buildChat("x", bad))).not.toHaveProperty("selected_cue");
    }
  });
});

describe("초안 되돌리기/다시하기 프레임", () => {
  it("페이로드가 없다 — 무엇을 되돌릴지는 서버의 이력이 안다", () => {
    expect(JSON.parse(buildTimelineDraftUndo())).toEqual({ v: 1, type: "timeline_draft_undo" });
    expect(JSON.parse(buildTimelineDraftRedo())).toEqual({ v: 1, type: "timeline_draft_redo" });
  });

  it("어느 프레임에도 콘솔 명령이 실리지 않는다", () => {
    const frames = [buildTimelineDraftUndo(), buildTimelineDraftRedo(), buildChat("더 밝게", 1)];
    for (const frame of frames) {
      expect(frame).not.toMatch(/command|Store |Go\+|Preset /);
    }
  });
});
