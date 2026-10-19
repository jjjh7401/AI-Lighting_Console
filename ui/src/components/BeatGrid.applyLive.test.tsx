// @vitest-environment jsdom
// 큐 편집 칸 「적용」 뒤 콘솔 반영(SPEC-LDRHYTHM-001) — 한 칸 편집이 앱에서 성공한 뒤에만, 그 칸 하나를 `onApplyCellsLive`
// 로 올린다. 실제 `<BeatGrid>` 를 그려 「적용」을 누르고, 서버 답(`lastServerReply`)을 다시 그려 넣는 방식이다.
// 거절·답 없음·옛 답·무대에서 여러 줄을 고른 편집에는 부르지 않고, 한 편집에 두 번 부르지도 않는다.
// 하네스는 `BeatGrid.stageSelect.test.tsx` 와 같다(jsdom + `act`).
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { BeatGridCue, BeatGridTrack, BeatGridView } from "../protocol";
import {
  BEAT_GRID_EDIT_OK_SUMMARY,
  BEAT_GRID_REJECTION_SUMMARY,
  BeatGrid,
  buildBrightnessValueChanges,
  type BeatGridFixturePoint,
  type BeatGridProps,
} from "./BeatGrid";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

function cue(bar: number): BeatGridCue {
  return {
    bar,
    label: `칸${bar}`,
    brightness: { mode: "value", value_percent: 100, preset_no: null },
    position_preset_no: null,
    color_preset_no: null,
    effect_preset_no: null,
    effect_kind: null,
    entry: { fade_bars: null, mib_mode: null },
    source_ref: null,
    app_movement: null,
    evidence: null,
  };
}

function track(name: string, bars: number[]): BeatGridTrack {
  return { group_no: null, group_no_confirmed: false, group_name: name, layer_role: null, cues: bars.map(cue) };
}

function gridOf(tracks: BeatGridTrack[]): BeatGridView {
  return {
    song_title: "LOVE ATTACK",
    bar_range: { start: 0, end: 12 },
    tracks,
    scene_memos: [],
    probe_results: {},
    source: "empty",
    note: null,
    console_audio_offset_seconds: 0,
  };
}

/** 줄마다 무대에 장비 한 대 — 좌표가 있어야 줄마다 눌리는 영역이 생긴다. */
function fixturesOf(names: string[]): BeatGridFixturePoint[] {
  return names.map((name, index) => ({
    fid: index + 1,
    name: `${name}-1`,
    x: index * 10,
    y: 0,
    z: 0,
    rotx: 0,
    roty: 0,
    rotz: 0,
    confirmedGroupName: name,
  }));
}

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

// 서버 `cells` 는 1마디부터라 반영 시험 칸은 모두 1마디 이상이다. 앞박(0마디) 칸은 따로 본다.
const ALIGNED = () => [track("AAA", [1, 5]), track("BBB", [1, 5]), track("CCC", [1, 5])];
const FROM_BAR_ZERO = () => [track("AAA", [0, 4]), track("BBB", [0, 4])];

const okReply = (seq: number) => ({ text: "박자 격자를 수정했습니다", seq, summary: BEAT_GRID_EDIT_OK_SUMMARY });
const rejectedReply = (seq: number) => ({
  text: "박자 격자를 수정하지 않았습니다",
  seq,
  summary: BEAT_GRID_REJECTION_SUMMARY,
});

function mount(tracks: BeatGridTrack[], initial: Partial<BeatGridProps> = {}) {
  const handlers = { onEditRequest: vi.fn(), onApplyCellsLive: vi.fn() };
  let current: Partial<BeatGridProps> = { ...initial };
  const render = (patch: Partial<BeatGridProps> = {}) => {
    current = { ...current, ...patch };
    act(() =>
      root.render(
        <BeatGrid
          grid={gridOf(tracks)}
          fixtures={fixturesOf(tracks.map((t) => t.group_name))}
          {...handlers}
          {...current}
        />,
      ),
    );
  };
  render();
  return { handlers, render };
}

function stageClick(name: string, shift = false) {
  const hit = container.querySelector(`rect.beat-grid-stage-hit[data-track="${name}"]`);
  if (!hit) throw new Error(`stage zone not found: ${name}`);
  act(() => {
    hit.dispatchEvent(new MouseEvent("click", { bubbles: true, shiftKey: shift }));
  });
}

/** 타임라인의 칸 막대를 순서(줄 우선)로 눌러 그 칸 하나를 고른다. */
function pickCue(index: number) {
  act(() => container.querySelectorAll<HTMLButtonElement>("button.beat-grid-cue")[index].click());
}

/** 밝기 「값 ▾」에서 값을 고르고 밝기 「적용」을 누른다. */
function applyBrightness(percent: number) {
  const select = container.querySelector<HTMLSelectElement>('select[aria-label="밝기 값(%)"]');
  if (!select) throw new Error("brightness value select not found");
  act(() => {
    select.value = String(percent);
    select.dispatchEvent(new Event("change", { bubbles: true }));
  });
  const apply = Array.from(container.querySelectorAll('.beat-grid-cue-field[data-field="밝기"] button')).find(
    (button) => button.textContent === "적용",
  );
  if (!apply) throw new Error("brightness apply button not found");
  act(() => (apply as HTMLButtonElement).click());
}

describe("한 칸 「적용」 뒤 콘솔 반영", () => {
  it("앱 편집이 성공한 답이 오면 그 칸 하나를 [줄 이름, 마디] 로 한 번 올린다", () => {
    const { handlers, render } = mount(ALIGNED());
    pickCue(2); // BBB 의 첫 칸(1마디)
    applyBrightness(60);
    expect(handlers.onEditRequest.mock.calls).toEqual([
      [{ bar: 1, target: "BBB", changes: buildBrightnessValueChanges(60) }],
    ]);
    expect(handlers.onApplyCellsLive).not.toHaveBeenCalled(); // 답이 오기 전에는 보내지 않는다
    render({ lastServerReply: okReply(1) });
    expect(handlers.onApplyCellsLive).toHaveBeenCalledTimes(1);
    expect(handlers.onApplyCellsLive).toHaveBeenCalledWith([["BBB", 1]]);
  });

  it("같은 답이 다시 그려지거나 다른 속성이 바뀌어도 한 편집에 두 번 부르지 않는다", () => {
    const { handlers, render } = mount(ALIGNED());
    pickCue(0);
    applyBrightness(60);
    render({ lastServerReply: okReply(1) });
    render({ lastServerReply: okReply(1) });
    render({ busyCount: 2 });
    expect(handlers.onApplyCellsLive).toHaveBeenCalledTimes(1);
  });

  it("거절된 답에는 부르지 않는다", () => {
    const { handlers, render } = mount(ALIGNED());
    pickCue(0);
    applyBrightness(60);
    render({ lastServerReply: rejectedReply(1) });
    render({ lastServerReply: rejectedReply(2) });
    expect(handlers.onApplyCellsLive).not.toHaveBeenCalled();
  });

  it("답이 오지 않으면 부르지 않는다", () => {
    const { handlers, render } = mount(ALIGNED());
    pickCue(0);
    applyBrightness(60);
    render({ busyCount: 1 });
    expect(handlers.onApplyCellsLive).not.toHaveBeenCalled();
  });

  it("누르기 전에 온 옛 성공 답으로는 부르지 않고, 누른 뒤의 새 답에만 부른다", () => {
    const { handlers, render } = mount(ALIGNED(), { lastServerReply: okReply(7) });
    pickCue(0);
    applyBrightness(60);
    render({ lastServerReply: okReply(7) });
    expect(handlers.onApplyCellsLive).not.toHaveBeenCalled();
    render({ lastServerReply: okReply(8) });
    expect(handlers.onApplyCellsLive).toHaveBeenCalledTimes(1);
    expect(handlers.onApplyCellsLive).toHaveBeenCalledWith([["AAA", 1]]);
  });

  it("무대에서 한 줄만 보통 클릭한 편집도 그 칸 하나다", () => {
    const { handlers, render } = mount(ALIGNED());
    pickCue(0); // 보는 마디를 1마디로 옮긴다 — 무대 줄은 보는 마디에 칸이 있어야 눌린다
    stageClick("CCC");
    applyBrightness(25);
    render({ lastServerReply: okReply(1) });
    expect(handlers.onApplyCellsLive).toHaveBeenCalledTimes(1);
    expect(handlers.onApplyCellsLive).toHaveBeenCalledWith([["CCC", 1]]);
  });

  it("무대에서 여러 줄을 골라 보낸 편집은 부르지 않는다 — 이 길은 아직 콘솔에 반영하지 않는다", () => {
    const { handlers, render } = mount(ALIGNED());
    pickCue(0);
    stageClick("BBB");
    stageClick("AAA", true);
    stageClick("CCC", true);
    applyBrightness(60);
    expect(handlers.onEditRequest).toHaveBeenCalledTimes(3);
    render({ lastServerReply: okReply(1) });
    expect(handlers.onApplyCellsLive).not.toHaveBeenCalled();
  });

  it("앞박(0마디) 칸은 서버 cells 로 보낼 수 없어 편집은 올리되 콘솔 반영은 부르지 않는다", () => {
    const { handlers, render } = mount(FROM_BAR_ZERO());
    pickCue(0);
    applyBrightness(60);
    expect(handlers.onEditRequest).toHaveBeenCalledTimes(1);
    expect(handlers.onEditRequest.mock.calls[0][0]).toMatchObject({ bar: 0, target: "AAA" });
    render({ lastServerReply: okReply(1) });
    expect(handlers.onApplyCellsLive).not.toHaveBeenCalled();
  });

  it("콜백이 없으면 예전과 같이 편집만 올리고 아무 일도 없다", () => {
    const { handlers, render } = mount(ALIGNED(), { onApplyCellsLive: undefined });
    pickCue(0);
    applyBrightness(60);
    render({ lastServerReply: okReply(1) });
    expect(handlers.onEditRequest).toHaveBeenCalledTimes(1);
    expect(handlers.onApplyCellsLive).not.toHaveBeenCalled();
  });
});
