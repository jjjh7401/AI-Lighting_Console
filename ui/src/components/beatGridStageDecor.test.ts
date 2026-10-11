// 카드 t588 — 2D 무대 시안 장식(바닥·워시 면·무빙 빔)을 장비 좌표에서 만든다.
// 그룹 이름 상수 없이 줄의 층 역할(layer_role)과 확인된 소속만으로 그려지는지 본다.
import { describe, expect, it } from "vitest";

import type { BeatGridCue, BeatGridStageView, BeatGridTrack } from "../protocol";
import { fixtureIsMover, stageDecorations } from "./BeatGridStage";
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
