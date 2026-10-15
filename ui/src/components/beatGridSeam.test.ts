// 이음매 끌기 순수 계산 시험 — 박 단위 스냅·마디 안 가두기·끌기/누르기 구분·
// 놓을 때만 커밋·끌기 뒤 클릭 무시(SPEC-LDBEAT-001 M9, 이음매 드래그).
// DOM 을 띄우지 않는다. 포인터 이벤트 대신 이벤트 값을 직접 넣어 상태 기계를 본다.
import { describe, expect, it } from "vitest";

import {
  reduceSeamDrag,
  SEAM_DRAG_THRESHOLD_PX,
  seamTriggerBeat,
  type SeamDragState,
} from "./beatGridSeam";

// 마디 400px, 박 4개 — 한 박은 100px.
const PX_PER_BAR = 400;
const BEATS = 4;

describe("seamTriggerBeat — 박 단위 스냅", () => {
  it("박 수를 모르면 끌 수 없어 null 이다", () => {
    expect(seamTriggerBeat({ startBeat: 1, deltaPx: 100, pxPerBar: PX_PER_BAR, beatsPerBar: null })).toBeNull();
  });

  it("마디 폭이 0 이하면 null 이다(0으로 나누지 않는다)", () => {
    expect(seamTriggerBeat({ startBeat: 1, deltaPx: 100, pxPerBar: 0, beatsPerBar: BEATS })).toBeNull();
  });

  it("움직이지 않으면 처음 박 그대로다", () => {
    expect(seamTriggerBeat({ startBeat: 3, deltaPx: 0, pxPerBar: PX_PER_BAR, beatsPerBar: BEATS })).toBe(3);
  });

  it("한 박 폭만큼 끌면 다음 박이다", () => {
    expect(seamTriggerBeat({ startBeat: 1, deltaPx: 100, pxPerBar: PX_PER_BAR, beatsPerBar: BEATS })).toBe(2);
    expect(seamTriggerBeat({ startBeat: 2, deltaPx: -100, pxPerBar: PX_PER_BAR, beatsPerBar: BEATS })).toBe(1);
  });

  it("가장 가까운 박에 붙는다(반 박 아래는 내려가고 위는 올라간다)", () => {
    expect(seamTriggerBeat({ startBeat: 1, deltaPx: 149, pxPerBar: PX_PER_BAR, beatsPerBar: BEATS })).toBe(2);
    expect(seamTriggerBeat({ startBeat: 1, deltaPx: 151, pxPerBar: PX_PER_BAR, beatsPerBar: BEATS })).toBe(3);
  });

  it("첫 박 밖으로 끌어도 첫 박에 머문다(마디 밖으로 나가지 않는다)", () => {
    expect(seamTriggerBeat({ startBeat: 1, deltaPx: -500, pxPerBar: PX_PER_BAR, beatsPerBar: BEATS })).toBe(1);
  });

  it("마지막 박 밖으로 끌어도 마지막 박에 머문다", () => {
    expect(seamTriggerBeat({ startBeat: 4, deltaPx: 500, pxPerBar: PX_PER_BAR, beatsPerBar: BEATS })).toBe(4);
  });

  it("마디 밖에서 시작한 잘못된 박도 마디 안으로 붙인다", () => {
    expect(seamTriggerBeat({ startBeat: 9, deltaPx: 0, pxPerBar: PX_PER_BAR, beatsPerBar: BEATS })).toBe(4);
  });
});

describe("reduceSeamDrag — 누르기·끌기·놓기", () => {
  const press = (startBeat = 1): SeamDragState =>
    reduceSeamDrag({ phase: "idle" }, { type: "down", pointerId: 7, x: 500, startBeat }).state;

  it("누르면 누르기 상태가 되고, 아직 커밋도 클릭 무시도 없다", () => {
    const outcome = reduceSeamDrag({ phase: "idle" }, { type: "down", pointerId: 7, x: 500, startBeat: 1 });
    expect(outcome.state).toEqual({ phase: "pressed", pointerId: 7, startX: 500, startBeat: 1 });
    expect(outcome.commitBeat).toBeNull();
    expect(outcome.suppressClick).toBe(false);
  });

  it("임계값보다 적게 움직이면 아직 끌기가 아니다", () => {
    const moved = reduceSeamDrag(press(), {
      type: "move",
      pointerId: 7,
      x: 500 + SEAM_DRAG_THRESHOLD_PX - 1,
      pxPerBar: PX_PER_BAR,
      beatsPerBar: BEATS,
    });
    expect(moved.state.phase).toBe("pressed");
  });

  it("임계값을 넘기면 끌기 상태가 되고 옮길 박을 보여 준다", () => {
    const moved = reduceSeamDrag(press(), {
      type: "move",
      pointerId: 7,
      x: 600,
      pxPerBar: PX_PER_BAR,
      beatsPerBar: BEATS,
    });
    expect(moved.state).toEqual({ phase: "dragging", pointerId: 7, startX: 500, startBeat: 1, beat: 2 });
    expect(moved.commitBeat).toBeNull();
  });

  it("끌다가 놓으면 옮겨진 박을 커밋하고 뒤따르는 클릭을 무시한다", () => {
    const dragging = reduceSeamDrag(press(), {
      type: "move",
      pointerId: 7,
      x: 600,
      pxPerBar: PX_PER_BAR,
      beatsPerBar: BEATS,
    }).state;
    const released = reduceSeamDrag(dragging, {
      type: "up",
      pointerId: 7,
      x: 600,
      pxPerBar: PX_PER_BAR,
      beatsPerBar: BEATS,
    });
    expect(released.commitBeat).toBe(2);
    expect(released.suppressClick).toBe(true);
    expect(released.state).toEqual({ phase: "idle" });
  });

  it("끌었다가 처음 박으로 되돌려 놓으면 커밋하지 않는다(그래도 클릭은 무시한다)", () => {
    const dragging = reduceSeamDrag(press(), {
      type: "move",
      pointerId: 7,
      x: 600,
      pxPerBar: PX_PER_BAR,
      beatsPerBar: BEATS,
    }).state;
    const released = reduceSeamDrag(dragging, {
      type: "up",
      pointerId: 7,
      x: 500,
      pxPerBar: PX_PER_BAR,
      beatsPerBar: BEATS,
    });
    expect(released.commitBeat).toBeNull();
    expect(released.suppressClick).toBe(true);
  });

  it("끌지 않고 그냥 누르고 놓으면 커밋도 없고 클릭은 살아 있다(편집 창 열기)", () => {
    const released = reduceSeamDrag(press(), {
      type: "up",
      pointerId: 7,
      x: 500,
      pxPerBar: PX_PER_BAR,
      beatsPerBar: BEATS,
    });
    expect(released.commitBeat).toBeNull();
    expect(released.suppressClick).toBe(false);
    expect(released.state).toEqual({ phase: "idle" });
  });

  it("다른 포인터의 이벤트는 무시한다", () => {
    const start = press();
    const moved = reduceSeamDrag(start, {
      type: "move",
      pointerId: 99,
      x: 800,
      pxPerBar: PX_PER_BAR,
      beatsPerBar: BEATS,
    });
    expect(moved.state).toBe(start);
  });

  it("박 수를 모르면 끌기가 시작되지 않는다(누르기에 머문다)", () => {
    const moved = reduceSeamDrag(press(), {
      type: "move",
      pointerId: 7,
      x: 800,
      pxPerBar: PX_PER_BAR,
      beatsPerBar: null,
    });
    expect(moved.state.phase).toBe("pressed");
  });

  it("끌다가 취소되면 커밋 없이 끝나고 클릭은 무시한다", () => {
    const dragging = reduceSeamDrag(press(), {
      type: "move",
      pointerId: 7,
      x: 600,
      pxPerBar: PX_PER_BAR,
      beatsPerBar: BEATS,
    }).state;
    const cancelled = reduceSeamDrag(dragging, { type: "cancel", pointerId: 7 });
    expect(cancelled.commitBeat).toBeNull();
    expect(cancelled.suppressClick).toBe(true);
    expect(cancelled.state).toEqual({ phase: "idle" });
  });

  it("누르기만 한 채 취소되면 클릭은 살아 있다", () => {
    const cancelled = reduceSeamDrag(press(), { type: "cancel", pointerId: 7 });
    expect(cancelled.suppressClick).toBe(false);
    expect(cancelled.state).toEqual({ phase: "idle" });
  });

  it("누른 적 없이 놓거나 취소해도 아무 일도 없다", () => {
    const idle: SeamDragState = { phase: "idle" };
    const released = reduceSeamDrag(idle, {
      type: "up",
      pointerId: 7,
      x: 500,
      pxPerBar: PX_PER_BAR,
      beatsPerBar: BEATS,
    });
    expect(released.state).toEqual({ phase: "idle" });
    expect(released.commitBeat).toBeNull();
    expect(released.suppressClick).toBe(false);
  });
});
