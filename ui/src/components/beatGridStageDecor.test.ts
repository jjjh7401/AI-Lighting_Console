// 카드 t588 — 2D 무대 시안 장식(바닥·워시 면·무빙 빔)을 장비 좌표에서 만든다.
// 그룹 이름 상수 없이 줄의 층 역할(layer_role)과 확인된 소속만으로 그려지는지 본다.
import { describe, expect, it } from "vitest";

import type { BeatGridCue, BeatGridStageView, BeatGridTrack } from "../protocol";
import { fixtureIsBlind, fixtureIsMover, stageDecorations } from "./BeatGridStage";
import { stageFixturePoints } from "./beatGridStageModel";

const view: BeatGridStageView = {
  fixtures: [
    { fid: 11, name: "w1", x: -4, y: 2, z: 0 },
    { fid: 12, name: "w2", x: 4, y: 2, z: 0 },
    { fid: 21, name: "m1", x: -2, y: 6, z: 0 },
    { fid: 22, name: "m2", x: 2, y: 6, z: 0 },
    { fid: 99, name: "loose", x: 0, y: -2, z: 0 },
  ],
  groups: [
    { group_no: 1, group_name: "ZZZ", member_fids: [11, 12], complete: true },
    { group_no: 2, group_name: "QQQ", member_fids: [21, 22], complete: true },
  ],
  unread: [],
};
const points = stageFixturePoints(view);
const project = (p: { x: number; y: number }) => ({ cx: (p.x + 10) * 10, cy: (10 - p.y) * 10 });
const FRONT_Y = 150;

function cue(bar: number, label: string): BeatGridCue {
  return { bar, label } as unknown as BeatGridCue;
}

function track(name: string, role: string, label: string): BeatGridTrack {
  return { group_no: null, group_no_confirmed: false, group_name: name, layer_role: role, cues: [cue(0, label)] };
}

describe("stageDecorations — 시안 drawStage 장식 (카드 t588)", () => {
  it("바닥은 읽힌 장비 전체를 감싼다", () => {
    const decor = stageDecorations(points, [], project, 0, FRONT_Y, 0);
    expect(decor.floor).toEqual({ x: 60, y: 40, width: 80, height: 80 });
  });

  it("층 역할 wash 인 줄이 켜지면 그 소속 장비 영역에 워시 면 하나", () => {
    const decor = stageDecorations(points, [track("ZZZ", "wash", "워시 40%")], project, 0, FRONT_Y, 0);
    expect(decor.washes).toHaveLength(1);
    expect(decor.washes[0]).toMatchObject({ x: 60, y: 80, width: 80, height: 0 });
  });

  it("꺼진 칸(「—」)이면 워시 면도 빔도 없다", () => {
    const decor = stageDecorations(
      points,
      [track("ZZZ", "wash", "—"), track("QQQ", "mover", "—")],
      project,
      0,
      FRONT_Y,
      0,
    );
    expect(decor.washes).toEqual([]);
    expect(decor.beams).toEqual([]);
  });

  it("층 역할 mover 인 줄이 켜지면 소속 장비마다 무대 앞쪽으로 빔", () => {
    const decor = stageDecorations(points, [track("QQQ", "mover", "스윕")], project, 0, FRONT_Y, 0);
    expect(decor.beams.map((b) => b.key)).toEqual(["beam-0-21", "beam-0-22"]);
    // 장비(80,40)에서 앞 가장자리(150)까지의 절반 → 길이 55, 반폭 9.
    expect(decor.beams[0].points).toBe("80,40 71,95 89,95");
  });

  it("재생 시계가 있으면 움직임 칸의 빔이 시각마다 돌고, 장비마다 위상이 엇갈린다", () => {
    const moving: BeatGridTrack = {
      ...track("QQQ", "mover", "웨이브"),
      cues: [
        {
          ...cue(0, "웨이브"),
          app_movement: { shape: "wave", axes: ["Pan"], period_unit: "bar", period_value: 1, phase_spread: true },
        },
      ],
    };
    const at = (seconds: number) =>
      stageDecorations(points, [moving], project, 0, FRONT_Y, 0, { seconds, secondsPerBar: 2, beatsPerBar: 4 }).beams.map(
        (b) => b.points,
      );
    const still = "80,40 71,95 89,95";
    expect(at(0)[0]).toBe(still); // 위상 0 → 곧은 빔
    // 끝 두 점의 가운데 x 에서 장비 x 를 뺀 값 — + 면 화면 오른쪽으로 돈 빔.
    const swing = (pts: string) => {
      const [[x0], [x1], [x2]] = pts.split(" ").map((p) => p.split(",").map(Number));
      return (x1 + x2) / 2 - x0;
    };
    // 1/4 바퀴 뒤: 첫 장비는 오른쪽, 반 바퀴 엇갈린 둘째 장비는 왼쪽.
    expect(swing(at(0.5)[0])).toBeGreaterThan(10);
    expect(swing(at(0.5)[1])).toBeLessThan(-10);
    // 시계가 없으면 움직이지 않는다.
    expect(stageDecorations(points, [moving], project, 0, FRONT_Y, 0).beams[0].points).toBe(still);
  });

  it("실서버 재현: app_movement 없이 effect_preset_no 21.10 만 있는 칸도 격자 기록으로 움직인다", () => {
    // 리드 실측(47010, 12.9초 · 0.5초 간격 두 캡처가 바이트 동일)의 칸 모양 — 라벨은 읽지 않는다.
    const waveCell: BeatGridTrack = {
      ...track("QQQ", "mover", "팬 웨이브(한 바퀴 2마디)"),
      cues: [{ ...cue(4, "팬 웨이브(한 바퀴 2마디)"), effect_preset_no: "21.10", position_preset_no: "2.33" }],
    };
    const book = {
      labels: { "21.10": "WAVE PAN 2 BAR", "2.33": "CENTER MOVER-U" },
      movements: { "21.10": { group_no: 11, signature: ["wave", ["Pan"], "bar", 2, false] } },
    };
    const clock = (seconds: number) => ({ seconds, secondsPerBar: 60 / 112 * 4, beatsPerBar: 4 });
    const at = (seconds: number) =>
      stageDecorations(points, [waveCell], project, 5, FRONT_Y, 0, clock(seconds), book).beams.map((b) => b.points);
    expect(at(12.9)).toHaveLength(2);
    expect(at(13.4)[0]).not.toBe(at(12.9)[0]);
    expect(at(13.4)[1]).not.toBe(at(12.9)[1]);
  });

  it("역할이 다른 줄(그룹 이름과 무관)은 장식하지 않는다", () => {
    const decor = stageDecorations(points, [track("QQQ", "back", "켜짐")], project, 0, FRONT_Y, 0);
    expect(decor.washes).toEqual([]);
    expect(decor.beams).toEqual([]);
  });

  it("장비가 없으면 아무 것도 그리지 않는다", () => {
    expect(stageDecorations([], [track("ZZZ", "wash", "켜짐")], project, 0, FRONT_Y, 0)).toEqual({
      floor: null,
      washes: [],
      beams: [],
    });
  });
});

describe("fixtureIsMover — 시안 무빙 네모 (카드 t591)", () => {
  const byFid = (fid: number) => points.find((p) => p.fid === fid)!;

  it("층 역할 mover 줄에 소속이 확인된 장비만 무빙이다(그룹 이름 무관)", () => {
    const tracks = [track("QQQ", "mover", "켜짐"), track("ZZZ", "wash", "켜짐")];
    expect(fixtureIsMover(byFid(21), tracks)).toBe(true);
    expect(fixtureIsMover(byFid(22), tracks)).toBe(true);
    expect(fixtureIsMover(byFid(11), tracks)).toBe(false);
    expect(fixtureIsMover(byFid(99), tracks)).toBe(false);
  });

  it("이름이 MOVER 처럼 보여도 소속 확인이 없으면 무빙이 아니다", () => {
    const loose = { ...byFid(99), name: "MOVER-U 501" };
    expect(fixtureIsMover(loose, [track("MOVER-U", "mover", "켜짐")])).toBe(false);
  });
});

describe("fixtureIsBlind — 무빙이 아닌 효과(effect) 줄 = 사각(리드 결정)", () => {
  const byFid = (fid: number) => points.find((p) => p.fid === fid)!;

  it("효과 역할 줄에 소속이 확인된 장비는 사각(BLIND 류)이다", () => {
    const tracks = [track("ZZZ", "effect", "켜짐")];
    expect(fixtureIsBlind(byFid(11), tracks)).toBe(true);
    expect(fixtureIsBlind(byFid(12), tracks)).toBe(true);
  });

  it("무빙 줄의 장비는 사각이 아니라 무빙이다", () => {
    const tracks = [track("QQQ", "mover", "켜짐")];
    expect(fixtureIsBlind(byFid(21), tracks)).toBe(false);
    expect(fixtureIsMover(byFid(21), tracks)).toBe(true);
  });

  it("소속이 없으면 사각이 아니다", () => {
    expect(fixtureIsBlind(byFid(99), [track("ZZZ", "effect", "켜짐")])).toBe(false);
  });
});

describe("pan_tilt — 서버 능력 필드가 있으면 무빙 판정의 기준(리드 결정)", () => {
  const byFid = (fid: number) => points.find((p) => p.fid === fid)!;

  it("pan_tilt 가 true 면 층 역할과 무관하게 무빙이다", () => {
    expect(fixtureIsMover({ ...byFid(11), pan_tilt: true }, [track("ZZZ", "wash", "켜짐")])).toBe(true);
  });

  it("pan_tilt 가 false 면 무빙 줄 소속이어도 무빙이 아니다", () => {
    expect(fixtureIsMover({ ...byFid(21), pan_tilt: false }, [track("QQQ", "mover", "켜짐")])).toBe(false);
  });

  it("pan_tilt 키가 없으면(모름) 임시로 층 역할을 따른다", () => {
    expect(fixtureIsMover(byFid(21), [track("QQQ", "mover", "켜짐")])).toBe(true);
  });
});

describe("빔 — 켜진 무빙만(리드 결정)", () => {
  it("무빙 줄이 켜져 있으면 그 소속 장비마다 빔이 있다", () => {
    const decor = stageDecorations(points, [track("QQQ", "mover", "스윕")], project, 0, FRONT_Y, 0);
    expect(decor.beams.map((beam) => beam.key).sort()).toEqual(["beam-0-21", "beam-0-22"]);
  });

  it("무빙 줄이 꺼져 있으면 빔이 없다", () => {
    const decor = stageDecorations(points, [track("QQQ", "mover", "—")], project, 0, FRONT_Y, 0);
    expect(decor.beams).toEqual([]);
  });
});
