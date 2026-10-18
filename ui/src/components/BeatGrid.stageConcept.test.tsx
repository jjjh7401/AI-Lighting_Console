// @vitest-environment jsdom
// 무대 개념도(장비 좌표 없음)에서 줄 고르기와 「적용」 — 실제 `<BeatGrid>` 를 그린다. 이름표를 누르고 Shift 로 여럿 고르면
// 편집 칸이 그 줄을 펼치고, 「적용」은 고른 줄마다 요청 하나를 보낸다. 좌표가 있는 무대는 `BeatGrid.stageSelect.test.tsx` 가 본다.
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { BeatGridCue, BeatGridTrack, BeatGridView } from "../protocol";
import { BeatGrid } from "./BeatGrid";

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

function track(name: string, role: string, bars: number[]): BeatGridTrack {
  return { group_no: null, group_no_confirmed: false, group_name: name, layer_role: role, cues: bars.map(cue) };
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

/** 자리마다 줄 하나: BACK(back), MOVE-U(첫 무빙 → U), MOVE-D(둘째 무빙 → D), SIDE(측면 → SIDE-L). 모두 0마디에 칸이 있다. */
const CONCEPT = (): BeatGridTrack[] => [
  track("BACK", "back", [0]),
  track("MOVE-U", "mover", [0]),
  track("MOVE-D", "mover", [0]),
  track("SIDE", "side", [0]),
];

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

/** 장비 좌표를 넘기지 않으면 무대는 개념도다. */
function mountConcept(tracks: BeatGridTrack[]) {
  const onEditRequest = vi.fn();
  act(() =>
    root.render(<BeatGrid grid={gridOf(tracks)} fixtures={[]} onEditRequest={onEditRequest} />),
  );
  return { onEditRequest };
}

/** 개념도 자리의 이름표를 누른다 — `shift` 면 Shift+클릭. */
function conceptClick(label: string, shift = false) {
  const group = Array.from(container.querySelectorAll<SVGGElement>("g.beat-grid-stage-slot")).find(
    (g) => g.querySelector("text")?.textContent === label,
  );
  const text = group?.querySelector("text");
  if (!text) throw new Error(`concept slot not found: ${label}`);
  act(() => {
    text.dispatchEvent(new MouseEvent("click", { bubbles: true, shiftKey: shift }));
  });
}

/** 노란 점선이 둘러진 개념도 자리들의 이름표(무대 그림 순서). */
function conceptSelected(): string[] {
  return Array.from(container.querySelectorAll<SVGGElement>("g.beat-grid-stage-slot.on")).map(
    (g) => g.querySelector("text")?.textContent ?? "?",
  );
}

/** 큐 편집 칸 머리 글자 — 편집 칸이 펼쳐 보이는 줄을 가린다. */
function panelHeading(): string {
  return container.querySelector("aside.beat-grid-cue-panel header span")?.textContent ?? "";
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

describe("무대 개념도 — 이름표를 누르고 Shift 로 여럿 고른다", () => {
  it("이름표 클릭은 그 줄 하나로 고르고, Shift 클릭은 더하며, 편집 칸은 방금 누른 줄을 편다", () => {
    mountConcept(CONCEPT());
    conceptClick("BACK");
    expect(conceptSelected()).toEqual(["BACK"]);
    conceptClick("U", true);
    expect(conceptSelected()).toEqual(["BACK", "U"]);
    expect(panelHeading()).toContain("MOVE-U");
  });

  it("고른 여럿에 밝기 「적용」을 누르면 줄마다 요청 하나씩, 같은 마디·같은 값으로 간다", () => {
    const { onEditRequest } = mountConcept(CONCEPT());
    conceptClick("BACK");
    conceptClick("U", true);
    applyBrightness(50);
    expect(onEditRequest.mock.calls.map((call) => call[0].target)).toEqual(["BACK", "MOVE-U"]);
    expect(onEditRequest.mock.calls.every((call) => call[0].bar === 0)).toBe(true);
  });

  it("Shift 로 이미 고른 줄을 다시 누르면 뺀다 — 남은 줄이 편집 칸에 펼쳐진다", () => {
    mountConcept(CONCEPT());
    conceptClick("BACK");
    conceptClick("U", true);
    conceptClick("BACK", true);
    expect(conceptSelected()).toEqual(["U"]);
    expect(panelHeading()).toContain("MOVE-U");
  });
});
