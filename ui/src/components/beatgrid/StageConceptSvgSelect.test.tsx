// @vitest-environment jsdom
// 무대 개념도(장비 좌표 없음)에서 자리와 이름표를 누르고 Shift 로 여럿 고르기. 실서버에서 감독이 보던 무대가 이 그림이었다.
// 자리마다 맡는 줄 하나: BACK · U(첫 무빙) · D(둘째 무빙) · SIDE-L. 이름표(BACK·U…)도 그 자리의 줄을 고른다.
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { BeatGridCue, BeatGridTrack } from "../../protocol";
import { StageConceptSvg } from "./StageConceptSvg";

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

/** 줄 순서가 자리를 정한다: 0 BACK(back), 1 MOVE-U(첫 무빙 → U), 2 MOVE-D(둘째 무빙 → D), 3 SIDE(측면 → SIDE-L). */
const TRACKS = (): BeatGridTrack[] => [
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

function render(
  props: {
    tracks?: BeatGridTrack[];
    selectedTrackName?: string | null;
    selectedRows?: number[];
    onSelectTrack?: (trackIndex: number, additive?: boolean) => void;
  } = {},
) {
  act(() =>
    root.render(
      <StageConceptSvg
        width={900}
        height={300}
        tracks={props.tracks ?? TRACKS()}
        viewBar={0}
        selectedTrackName={props.selectedTrackName ?? null}
        selectedRows={props.selectedRows}
        onSelectTrack={props.onSelectTrack}
      />,
    ),
  );
}

/** 자리의 이름표(자리 글자)로 그 자리 묶음을 찾는다. 이름표는 자리 묶음 안에 있다. */
function slotOf(label: string): SVGGElement {
  const group = Array.from(container.querySelectorAll<SVGGElement>("g.beat-grid-stage-slot")).find(
    (g) => g.querySelector("text")?.textContent === label,
  );
  if (!group) throw new Error(`slot not found: ${label}`);
  return group;
}

/** 노란 점선이 둘러진 자리들의 이름표(무대 그림 순서). */
function selectedSlots(): string[] {
  return Array.from(container.querySelectorAll<SVGGElement>("g.beat-grid-stage-slot.on")).map(
    (g) => g.querySelector("text")?.textContent ?? "?",
  );
}

/** 누른다 — `shift` 면 Shift+클릭. */
function press(target: Element, shift = false) {
  act(() => {
    target.dispatchEvent(new MouseEvent("click", { bubbles: true, shiftKey: shift }));
  });
}

describe("무대 개념도 — 이름표와 자리를 누르면 그 자리의 줄을 고른다", () => {
  it("이름표를 누르면 그 자리를 맡는 줄을 고른다(보통 클릭은 shiftKey 가 거짓)", () => {
    const onSelectTrack = vi.fn();
    render({ onSelectTrack });
    press(slotOf("BACK").querySelector("text") as Element);
    expect(onSelectTrack).toHaveBeenCalledWith(0, false);
  });

  it("장비 점을 눌러도 같은 줄을 고른다", () => {
    const onSelectTrack = vi.fn();
    render({ onSelectTrack });
    press(slotOf("BACK").querySelector("circle") as Element);
    expect(onSelectTrack).toHaveBeenCalledWith(0, false);
  });

  it("Shift+클릭은 같은 줄을 additive 참으로 넘긴다", () => {
    const onSelectTrack = vi.fn();
    render({ onSelectTrack });
    press(slotOf("U").querySelector("rect.beat-grid-stage-mover") as Element, true);
    expect(onSelectTrack).toHaveBeenCalledWith(1, true);
  });

  it("맡는 줄이 없는 자리는 눌러도 부르지 않는다", () => {
    const onSelectTrack = vi.fn();
    render({ onSelectTrack, tracks: [track("BACK", "back", [0])] });
    press(slotOf("SIDE-L").querySelector("text") as Element);
    expect(onSelectTrack).not.toHaveBeenCalled();
  });

  it("무대에서 고른 줄들의 자리는 모두 노란 점선이다", () => {
    render({ selectedRows: [0, 1] });
    expect(selectedSlots()).toEqual(["BACK", "U"]);
  });

  it("편집 칸의 줄(selectedTrackName)도 고른 줄에 더해 둘린다", () => {
    render({ selectedRows: [0], selectedTrackName: "MOVE-D" });
    expect(selectedSlots()).toEqual(["BACK", "D"]);
  });

  it("고른 줄이 없으면 점선도 없다", () => {
    render({});
    expect(selectedSlots()).toEqual([]);
  });

  it("자리 제목은 눌러서 편집이고, 이 마디에 칸이 없으면 그 사실을 말한다", () => {
    render({});
    expect(slotOf("BACK").querySelector("title")?.textContent).toBe("BACK — 눌러서 편집");
    render({ tracks: [track("BACK", "back", [4])] });
    expect(slotOf("BACK").querySelector("title")?.textContent).toBe("BACK — 이 마디에는 칸이 없어요");
  });
});
