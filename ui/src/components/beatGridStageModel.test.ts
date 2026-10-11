// 2D 무대 판독 결과 → BeatGrid 장비 점 (카드 t565, SPEC-LDBEAT-001 REQ-022).
import { describe, expect, it } from "vitest";

import type { BeatGridStageView, BeatGridTrack } from "../protocol";
import { fixtureDisplayColor } from "./BeatGrid";
import { stageGroupZones } from "./beatGridTransition";
import {
  fixtureBelongsTo,
  fixtureConfirmedGroupNames,
  stageFixturePoints,
  trackFixtureSummary,
} from "./beatGridStageModel";

const view: BeatGridStageView = {
  fixtures: [
    { fid: 301, name: "Side L 1", x: -6, y: 1, z: 1.2 },
    { fid: 311, name: "Side R 1", x: 6, y: 1, z: 1.2 },
    { fid: 900, name: "Haze", x: 0, y: -9, z: 0 },
  ],
  groups: [
    { group_no: 5, group_name: "SIDE-L", member_fids: [301], complete: true },
    { group_no: 6, group_name: "SIDE-ALL", member_fids: [301, 311], complete: true },
  ],
  unread: [],
};

function track(name: string): BeatGridTrack {
  return { group_no: null, group_no_confirmed: false, group_name: name, layer_role: null, cues: [] };
}

describe("stageFixturePoints", () => {
  it("좌표는 그대로, 소속은 판독된 그룹 전부", () => {
    const points = stageFixturePoints(view);
    expect(points.map((p) => p.fid)).toEqual([301, 311, 900]);
    expect(points[0]).toMatchObject({ x: -6, y: 1, z: 1.2, name: "Side L 1" });
    expect(fixtureConfirmedGroupNames(points[0])).toEqual(["SIDE-L", "SIDE-ALL"]);
    expect(fixtureConfirmedGroupNames(points[1])).toEqual(["SIDE-ALL"]);
  });
  it("어느 그룹에도 없는 장비는 소속 미확인(회색)", () => {
    const points = stageFixturePoints(view);
    expect(fixtureConfirmedGroupNames(points[2])).toEqual([]);
    expect(fixtureDisplayColor(points[2], [track("SIDE-ALL")])).toBe(fixtureDisplayColor(points[2], []));
  });
  it("판독이 없으면 빈 목록(지어내지 않음)", () => {
    expect(stageFixturePoints(null)).toEqual([]);
  });
});

describe("fixtureBelongsTo — 여러 그룹 소속(부모·자식)", () => {
  it("대소문자만 무시하고 정확히 같은 이름", () => {
    const [sideL1] = stageFixturePoints(view);
    expect(fixtureBelongsTo(sideL1, "side-all")).toBe(true);
    expect(fixtureBelongsTo(sideL1, "SIDE")).toBe(false);
  });
  it("예전 한 개짜리 필드도 그대로 인정", () => {
    const legacy = { fid: 1, name: "a", x: 0, y: 0, z: 0, rotx: 0, roty: 0, rotz: 0, confirmedGroupName: "BACK" };
    expect(fixtureBelongsTo(legacy, "BACK")).toBe(true);
    expect(fixtureConfirmedGroupNames(legacy)).toEqual(["BACK"]);
  });
  it("부모 그룹 트랙만 있어도 그 트랙 색으로 칠해진다", () => {
    const [, sideR1] = stageFixturePoints(view);
    expect(fixtureDisplayColor(sideR1, [track("WASH"), track("SIDE-ALL")])).not.toBe(
      fixtureDisplayColor(sideR1, []),
    );
  });
  it("무대 그룹 영역은 부모·자식 줄 각각 생긴다", () => {
    const points = stageFixturePoints(view);
    const zones = stageGroupZones(points, [track("SIDE-L"), track("SIDE-ALL")], (p) => ({ cx: p.x, cy: p.y }), 0);
    expect(zones.map((z) => [z.label, z.fixtureCount])).toEqual([
      ["SIDE-L", 1],
      ["SIDE-ALL", 2],
    ]);
  });
});

describe("trackFixtureSummary — 줄 이름 둘째 줄 (카드 t586, 시안 .lhead small)", () => {
  const points = stageFixturePoints(view);

  it("그룹 번호 · 확인된 장비 번호 범위 · 대수", () => {
    expect(trackFixtureSummary(6, "SIDE-ALL", points)).toBe("G6 · 301~311 · 2대");
  });

  it("장비가 한 대면 범위 대신 번호 하나", () => {
    expect(trackFixtureSummary(5, "SIDE-L", points)).toBe("G5 · 301 · 1대");
  });

  it("소속이 확인된 장비가 없으면 범위·대수를 지어내지 않는다", () => {
    expect(trackFixtureSummary(9, "BLIND", points)).toBe("G9");
  });

  it("그룹 번호도 장비도 모르면 둘째 줄이 없다", () => {
    expect(trackFixtureSummary(null, "BLIND", points)).toBeNull();
  });
});
