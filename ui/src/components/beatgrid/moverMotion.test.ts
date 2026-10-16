import { describe, expect, it } from "vitest";

import type { BeatGridCue } from "../../protocol";
import {
  PAN_SWING_DEG,
  basePoseOf,
  beamPolygonPoints,
  beamPoseAt,
  centrePanDegOf,
  moverMotionOf,
  parseEffectPresetName,
  phaseOffset,
  positionWordOf,
} from "./moverMotion";

function cue(extra: Partial<BeatGridCue>): BeatGridCue {
  return {
    bar: 0,
    label: "",
    brightness: { mode: null, value_percent: null, preset_no: null },
    position_preset_no: null,
    color_preset_no: null,
    effect_preset_no: null,
    effect_kind: null,
    entry: { fade_bars: null, mib_mode: null },
    source_ref: null,
    app_movement: null,
    evidence: null,
    ...extra,
  };
}

const wavePan2Beat = cue({
  app_movement: { shape: "wave", axes: ["Pan"], period_unit: "beat", period_value: 2, phase_spread: true },
});

describe("parseEffectPresetName", () => {
  it("서버 _effect_name 꼴을 읽는다", () => {
    expect(parseEffectPresetName("WAVE PAN 2 BEAT")).toEqual({ shape: "wave", pan: true, tilt: false, unit: "beat", value: 2 });
    expect(parseEffectPresetName("LA CIRCLE PAN+TILT 1 BAR")).toEqual({
      shape: "circle",
      pan: true,
      tilt: true,
      unit: "bar",
      value: 1,
    });
    expect(parseEffectPresetName("SWEEP TILT")).toMatchObject({ shape: "sweep", tilt: true, unit: null, value: null });
  });
  it("모르는 꼴은 null", () => {
    expect(parseEffectPresetName("Red Chase")).toBeNull();
    expect(parseEffectPresetName("PULSE PAN 1 BEAT")).toBeNull();
    expect(parseEffectPresetName(null)).toBeNull();
  });
});

describe("moverMotionOf", () => {
  it("app_movement 의 박 주기를 마디로 바꾼다", () => {
    expect(moverMotionOf(wavePan2Beat, 4)).toEqual({ shape: "wave", pan: true, tilt: false, periodBars: 0.5, phaseSpread: true });
  });
  it("박자표를 모르면 박 주기는 움직이지 않는다(지어내지 않음)", () => {
    expect(moverMotionOf(wavePan2Beat, null)).toBeNull();
  });
  it("app_movement 가 없으면 효과 프리셋 이름에서 읽는다", () => {
    expect(moverMotionOf(cue({ effect_preset_no: "21.2", effect_preset_name: "WAVE TILT 1 BAR" }), 4)).toMatchObject({
      shape: "wave",
      tilt: true,
      pan: false,
      periodBars: 1,
    });
  });
  it("주기가 없는 이름·움직임 없는 칸은 null", () => {
    expect(moverMotionOf(cue({ effect_preset_name: "WAVE PAN" }), 4)).toBeNull();
    expect(moverMotionOf(cue({}), 4)).toBeNull();
    expect(moverMotionOf(null, 4)).toBeNull();
  });
  it("app_movement 가 없으면 방향 값의 movement 를 읽는다(프리셋 기록보다 먼저)", () => {
    const direction = {
      brightness_percent: 100,
      color: null,
      position: { name: "Center" },
      effect_kind: "motion" as const,
      movement: { shape: "wave" as const, axes: ["Pan" as const], period_unit: "bar" as const, period_value: 2, phase_spread: null },
      entry: { trigger_beat: 1 },
    };
    // 효과 번호가 프리셋 기록의 다른 서명을 가리켜도 방향 값이 먼저다.
    const c = cue({ effect_preset_no: "21.10", direction });
    expect(moverMotionOf(c, 4, { movements: { "21.10": { group_no: 11, signature: ["circle", ["Tilt"], "bar", 4, false], bpm: 112 } } })).toEqual({
      shape: "wave",
      pan: true,
      tilt: false,
      periodBars: 2,
      phaseSpread: true,
    });
  });
  it("app_movement 가 있으면 방향 값보다 그것이 먼저다", () => {
    const direction = {
      brightness_percent: 100,
      color: null,
      position: null,
      effect_kind: "motion" as const,
      movement: { shape: "wave" as const, axes: ["Pan" as const], period_unit: "bar" as const, period_value: 2, phase_spread: null },
      entry: { trigger_beat: 1 },
    };
    const c = cue({ direction, app_movement: { shape: "sweep", axes: ["Tilt"], period_unit: "bar", period_value: 4, phase_spread: false } });
    expect(moverMotionOf(c, 4)).toMatchObject({ shape: "sweep", tilt: true, pan: false, periodBars: 4 });
  });
  it("방향 값에 움직임이 없으면(정지 칸) 움직이지 않는다", () => {
    const direction = {
      brightness_percent: 100,
      color: null,
      position: null,
      effect_kind: "hold" as const,
      movement: null,
      entry: { trigger_beat: 1 },
    };
    expect(moverMotionOf(cue({ direction }), 4)).toBeNull();
  });
  it("phase_spread false 면 위상을 펼치지 않는다", () => {
    const c = cue({ app_movement: { shape: "sweep", axes: ["Pan"], period_unit: "bar", period_value: 2, phase_spread: false } });
    expect(moverMotionOf(c, 4)?.phaseSpread).toBe(false);
  });
});

// 실서버 격자 모양(2026-10-16 저장본에서 읽은 키) — #782 이후 웨이브 칸은 app_movement 가 비고
// effect_preset_no 만 남는다. 내용은 격자의 preset_movements·preset_labels 에 있다.
const book = {
  labels: {
    "21.10": "WAVE PAN 2 BAR",
    "21.11": "WAVE PAN 2 BEAT",
    "2.31": "FLOOR MOVER-U",
    "2.33": "CENTER MOVER-U",
    "2.34": "RING IN MOVER-U",
    "2.35": "AUDIENCE MOVER-U",
  },
  movements: { "21.10": { group_no: 11, signature: ["wave", ["Pan"], "bar", 2, false], bpm: 112 } },
};

describe("moverMotionOf — 격자 기록(서버 이름 없이)", () => {
  it("effect_preset_no 만 있는 칸은 preset_movements 서명에서 읽는다", () => {
    expect(moverMotionOf(cue({ effect_preset_no: "21.10", label: "팬 웨이브(한 바퀴 2마디)" }), 4, book)).toEqual({
      shape: "wave",
      pan: true,
      tilt: false,
      periodBars: 2,
      phaseSpread: false,
    });
  });
  it("서명이 없으면 preset_labels 이름에서 읽는다", () => {
    expect(moverMotionOf(cue({ effect_preset_no: "21.11" }), 4, book)).toMatchObject({ shape: "wave", periodBars: 0.5 });
  });
  it("기록도 이름도 없는 번호는 라벨 글이 웨이브라도 움직이지 않는다(라벨 파싱 금지)", () => {
    expect(moverMotionOf(cue({ effect_preset_no: "21.5", label: "팬 웨이브(한 바퀴 2마디)" }), 4, book)).toBeNull();
  });
  it("app_movement 가 있으면 그것이 먼저", () => {
    const c = cue({
      effect_preset_no: "21.10",
      app_movement: { shape: "wave", axes: ["Tilt"], period_unit: "bar", period_value: 1, phase_spread: true },
    });
    expect(moverMotionOf(c, 4, book)).toMatchObject({ tilt: true, pan: false, periodBars: 1 });
  });
});

describe("positionWordOf — 번호·이름·그룹 꼴", () => {
  it("낱말 단위로 기본 위치를 찾는다", () => {
    expect(positionWordOf("2.33 CENTER MOVER-U")).toBe("center");
    expect(positionWordOf("CENTER MOVER-U")).toBe("center");
    expect(positionWordOf("RING IN MOVER-D")).toBe("ring");
    expect(positionWordOf("LA Audience")).toBe("audience");
    expect(positionWordOf("FLOOR MOVER-U")).toBe("home");
    expect(positionWordOf("CENTERLINE")).toBeNull();
    expect(positionWordOf(null)).toBeNull();
  });
  it("칸에 이름이 없으면 위치 번호의 격자 이름으로 자세를 정한다", () => {
    expect(basePoseOf(cue({ position_preset_no: "2.33" }), 12, book)).toEqual({ panDeg: 12, reach: 0.5 });
    expect(basePoseOf(cue({ position_preset_no: "2.35" }), 12, book).reach).toBe(1);
    expect(basePoseOf(cue({ position_preset_no: "2.31" }), 12, book).reach).toBe(0.15);
    expect(basePoseOf(cue({ position_preset_name: "2.34 RING IN MOVER-U" }), 12).reach).toBe(0.25);
  });
});

describe("basePoseOf", () => {
  it("기본 위치 이름 → 자세", () => {
    expect(basePoseOf(cue({ position_preset_name: "Home" }), 20)).toEqual({ panDeg: 0, reach: 0.15 });
    expect(basePoseOf(cue({ position_preset_name: "LA Center" }), 20)).toEqual({ panDeg: 20, reach: 0.5 });
    expect(basePoseOf(cue({ position_preset_name: "Ring In" }), 20).reach).toBe(0.25);
    expect(basePoseOf(cue({ planned_position_name: "Audience" }), 20).reach).toBe(1);
  });
  it("콘솔 이름이 계획 이름보다 먼저, 모르면 기본", () => {
    expect(basePoseOf(cue({ position_preset_name: "Home", planned_position_name: "Audience" }), 0).reach).toBe(0.15);
    expect(basePoseOf(cue({ position_preset_name: "SPOT 3" }), 0)).toEqual({ panDeg: 0, reach: 0.5 });
    expect(basePoseOf(null, 0)).toEqual({ panDeg: 0, reach: 0.5 });
  });
});

describe("beamPoseAt", () => {
  const motion = moverMotionOf(wavePan2Beat, 4)!; // 반 마디 한 바퀴
  const base = { panDeg: 0, reach: 0.5 };
  it("웨이브 팬은 한 바퀴의 1/4 에서 최대로 돈다", () => {
    // 마디 2초, 한 바퀴 1초 → 0.25초에 sin=1
    expect(beamPoseAt(base, motion, 0.25, 2, 0, 0).panDeg).toBeCloseTo(PAN_SWING_DEG);
    expect(beamPoseAt(base, motion, 0.75, 2, 0, 0).panDeg).toBeCloseTo(-PAN_SWING_DEG);
    expect(beamPoseAt(base, motion, 1, 2, 0, 0).panDeg).toBeCloseTo(0);
  });
  it("팬만 움직이면 길이는 그대로", () => {
    expect(beamPoseAt(base, motion, 0.25, 2, 0, 0).reach).toBe(0.5);
  });
  it("장비마다 위상이 엇갈린다", () => {
    const a = beamPoseAt(base, motion, 0.1, 2, phaseOffset(0, 4, true), 0).panDeg;
    const b = beamPoseAt(base, motion, 0.1, 2, phaseOffset(1, 4, true), 0).panDeg;
    expect(a).not.toBeCloseTo(b);
    expect(phaseOffset(1, 4, false)).toBe(0);
    expect(phaseOffset(0, 1, true)).toBe(0);
  });
  it("움직임·박 길이를 모르면 기본 자세", () => {
    expect(beamPoseAt(base, null, 3, 2, 0, 0)).toEqual(base);
    expect(beamPoseAt(base, motion, 3, null, 0, 0)).toEqual(base);
  });
  it("틸트 원은 길이를 바꾼다", () => {
    const circle = moverMotionOf(
      cue({ app_movement: { shape: "circle", axes: ["Pan", "Tilt"], period_unit: "bar", period_value: 1, phase_spread: true } }),
      4,
    )!;
    expect(beamPoseAt(base, circle, 0, 2, 0, 0).reach).toBeCloseTo(0.7);
    expect(beamPoseAt(base, circle, 1, 2, 0, 0).reach).toBeCloseTo(0.3);
  });
  it("flyout 은 무대 바깥쪽으로 벌어진다", () => {
    const fly = moverMotionOf(
      cue({ app_movement: { shape: "flyout", axes: ["Pan"], period_unit: "bar", period_value: 1, phase_spread: false } }),
      4,
    )!;
    expect(beamPoseAt(base, fly, 0.5, 2, 0, -1).panDeg).toBeLessThan(0);
    expect(beamPoseAt(base, fly, 0.5, 2, 0, 1).panDeg).toBeGreaterThan(0);
  });
});

describe("beamPolygonPoints", () => {
  it("팬 0 은 기존 고정 빔과 같은 모양", () => {
    expect(beamPolygonPoints(80, 40, 0, 55, 9)).toBe("80,40 71,95 89,95");
  });
  it("팬 90 은 화면 오른쪽으로 눕는다", () => {
    expect(beamPolygonPoints(0, 0, 90, 10, 2)).toBe("0,0 10,2 10,-2");
  });
});

describe("centrePanDegOf", () => {
  it("가운데 장비는 0, 왼쪽 장비는 오른쪽(+)으로", () => {
    expect(centrePanDegOf(100, 0, 100, 100)).toBe(0);
    expect(centrePanDegOf(0, 0, 100, 100)).toBeCloseTo(45);
  });
});
