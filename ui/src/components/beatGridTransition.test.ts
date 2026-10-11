// 박자 격자 전환·장면 전환·콘솔 명령 미리보기 순수 함수 시험
// (SPEC-LDBEAT-001 M9 step 3·4·5, 카드 t561, REQ-LDBEAT-020·021·022).
import { describe, expect, it } from "vitest";

import type { BeatGridCue, BeatGridTrack } from "../protocol";
import {
  SCENE_CHANGE_MIN_ROWS,
  cueConsoleCommandLines,
  cueIsLit,
  fadeDraftToBars,
  formatFadeSecondsFirst,
  jointMarker,
  parseBeatsPerBar,
  previousCue,
  sceneChangeBars,
  sceneChangeRows,
  stageGroupZones,
  transitionConsoleCommandLines,
  transitionMib,
  transitionWarnings,
} from "./beatGridTransition";

function cue(bar: number, overrides: Partial<BeatGridCue> = {}): BeatGridCue {
  return {
    bar,
    label: "켜짐",
    brightness: { mode: null, value_percent: null, preset_no: null },
    position_preset_no: null,
    color_preset_no: null,
    effect_preset_no: null,
    effect_kind: null,
    entry: { fade_bars: null, mib_mode: null },
    source_ref: null,
    app_movement: null,
    evidence: null,
    ...overrides,
  };
}

function track(name: string, cues: BeatGridCue[], overrides: Partial<BeatGridTrack> = {}): BeatGridTrack {
  return { group_no: null, group_no_confirmed: false, group_name: name, layer_role: null, cues, ...overrides };
}

describe("formatFadeSecondsFirst — 초 먼저, 마디는 괄호(REQ-LDBEAT-020(e))", () => {
  it("마디 수와 곡 1마디 초가 있으면 'N.NN초 (M마디)'", () => {
    expect(formatFadeSecondsFirst(1, 2.14)).toBe("2.14초 (1마디)");
    expect(formatFadeSecondsFirst(2, 2.14)).toMatch(/^\d+\.\d{2}초 \(2마디\)$/);
  });
  it("0마디는 끊기", () => {
    expect(formatFadeSecondsFirst(0, 2.14)).toBe("끊기 (0초)");
  });
  it("미정은 미정 그대로(지어내지 않음)", () => {
    expect(formatFadeSecondsFirst(null, 2.14)).toBe("미정");
  });
  it("곡 BPM이 없으면 초를 지어내지 않고 마디만", () => {
    expect(formatFadeSecondsFirst(2, null)).toBe("— 초 (2마디)");
  });
});

describe("parseBeatsPerBar / fadeDraftToBars — 박 입력은 허용하되 저장은 정수 마디", () => {
  it("박자표 분자를 읽는다", () => {
    expect(parseBeatsPerBar("4/4")).toBe(4);
    expect(parseBeatsPerBar("3/4")).toBe(3);
    expect(parseBeatsPerBar(undefined)).toBeNull();
    expect(parseBeatsPerBar("엉터리")).toBeNull();
  });
  it("마디 단위 입력은 그대로 정수 마디", () => {
    expect(fadeDraftToBars("2", "bar", null)).toEqual({ fadeBars: 2 });
  });
  it("박 입력은 한 마디 박 수로 나눠 정수일 때만 받는다", () => {
    expect(fadeDraftToBars("8", "beat", 4)).toEqual({ fadeBars: 2 });
    expect(fadeDraftToBars("2", "beat", 4).error).toMatch(/마디/);
  });
  it("박자표를 모르면 박 입력을 거절한다(4를 지어내지 않음)", () => {
    expect(fadeDraftToBars("4", "beat", null).error).toMatch(/박자표/);
  });
  it("음수·소수 마디·빈 값은 거절", () => {
    expect(fadeDraftToBars("-1", "bar", 4).error).toBeTruthy();
    expect(fadeDraftToBars("1.5", "bar", 4).error).toBeTruthy();
    expect(fadeDraftToBars("", "bar", 4).error).toBeTruthy();
  });
});

describe("transitionMib — 시안 mibOf 와 같은 세 갈래", () => {
  it("앞 칸이 없으면 곡 첫 큐", () => {
    expect(transitionMib(null, cue(0)).kind).toBe("first");
  });
  it("위치가 안 바뀌면 필요 없음", () => {
    const a = cue(0, { position_preset_no: "2.1" });
    expect(transitionMib(a, cue(4, { position_preset_no: "2.1" })).kind).toBe("none");
    expect(transitionMib(a, cue(4)).kind).toBe("none");
  });
  it("앞 칸이 꺼져 있고 위치가 바뀌면 자동(어둠 속 미리 이동)", () => {
    const off = cue(0, { label: "—", position_preset_no: "2.1" });
    expect(transitionMib(off, cue(4, { position_preset_no: "2.2" })).kind).toBe("auto");
  });
  it("앞 칸이 켜진 채 위치가 바뀌면 불가", () => {
    const lit = cue(0, { position_preset_no: "2.1" });
    expect(transitionMib(lit, cue(4, { position_preset_no: "2.2" })).kind).toBe("lit");
  });
  it("밝기 값 0%는 꺼짐으로 본다", () => {
    expect(cueIsLit(cue(0, { brightness: { mode: "value", value_percent: 0, preset_no: null } }))).toBe(false);
  });
});

describe("transitionWarnings — [제안] 경고(규칙서 §2.3 규칙 2)", () => {
  const lit = cue(0, { position_preset_no: "2.1", color_preset_no: "4.1" });
  it("켜진 채 위치가 끊어 바뀌면 경고", () => {
    const next = cue(4, { position_preset_no: "2.2", entry: { fade_bars: 0, mib_mode: null } });
    expect(transitionWarnings(lit, next, [])).toContain("켜진 채 위치가 끊어 바뀜");
  });
  it("페이드가 있으면 경고 없음", () => {
    const next = cue(4, { position_preset_no: "2.2", entry: { fade_bars: 1, mib_mode: null } });
    expect(transitionWarnings(lit, next, [])).toEqual([]);
  });
  it("페이드가 미정이면 판정하지 않는다(모르는 것을 경고로 지어내지 않음)", () => {
    const next = cue(4, { position_preset_no: "2.2" });
    expect(transitionWarnings(lit, next, [])).toEqual([]);
  });
  it("구간 경계가 아닌 곳에서 색이 끊어 바뀌면 경고, 경계면 없음", () => {
    const next = cue(4, { color_preset_no: "4.2", position_preset_no: "2.1", entry: { fade_bars: 0, mib_mode: null } });
    expect(transitionWarnings(lit, next, [0, 8])).toContain("구간 경계가 아닌데 색이 끊어 바뀜");
    expect(transitionWarnings(lit, next, [0, 4])).toEqual([]);
  });
  it("구간 경계 데이터가 없으면 색 경고를 판정하지 않는다", () => {
    const next = cue(4, { color_preset_no: "4.2", position_preset_no: "2.1", entry: { fade_bars: 0, mib_mode: null } });
    expect(transitionWarnings(lit, next, null)).toEqual([]);
  });
});

describe("jointMarker — 이음매 표시(M · ! · ◢)", () => {
  it("MIB 자동이면 M", () => {
    const off = cue(0, { label: "—", position_preset_no: "2.1" });
    const m = jointMarker(off, cue(4, { position_preset_no: "2.2" }), null);
    expect(m.glyph).toBe("M");
    expect(m.classes).toContain("is-mib");
  });
  it("경고가 있으면 !", () => {
    const lit = cue(0, { position_preset_no: "2.1" });
    const m = jointMarker(lit, cue(4, { position_preset_no: "2.2", entry: { fade_bars: 0, mib_mode: null } }), null);
    expect(m.glyph).toBe("!");
    expect(m.classes).toContain("is-warn");
    expect(m.title).toMatch(/\[제안\]/);
  });
  it("페이드만 있으면 ◢", () => {
    const m = jointMarker(cue(0), cue(4, { entry: { fade_bars: 1, mib_mode: null } }), null);
    expect(m.glyph).toBe("◢");
    expect(m.classes).toContain("is-fade");
  });
  it("아무것도 없으면 빈 이음매", () => {
    expect(jointMarker(cue(0), cue(4), null).glyph).toBe("");
  });
});

describe("previousCue", () => {
  it("그 마디 칸 바로 앞 칸, 첫 칸이면 null", () => {
    const t = track("A", [cue(0), cue(4), cue(8)]);
    expect(previousCue(t, 8)?.bar).toBe(4);
    expect(previousCue(t, 0)).toBeNull();
  });
});

describe("sceneChangeBars — 3줄 이상이 같은 마디에서 동시에 바뀌면 장면 전환 알약", () => {
  const tracks = [
    track("A", [cue(0), cue(4), cue(8)]),
    track("B", [cue(0), cue(4)]),
    track("C", [cue(0), cue(4), cue(8)]),
    track("D", [cue(0), cue(8)]),
  ];
  it("기준은 SPEC 문면의 3줄", () => {
    expect(SCENE_CHANGE_MIN_ROWS).toBe(3);
  });
  it("곡 첫 마디는 빼고 3줄 이상 바뀌는 마디만", () => {
    expect(sceneChangeBars(tracks, 0)).toEqual([
      { bar: 4, count: 3 },
      { bar: 8, count: 3 },
    ]);
  });
  it("그 마디에서 바뀌는 줄 목록", () => {
    expect(sceneChangeRows(tracks, 8).map((r) => r.track.group_name)).toEqual(["A", "C", "D"]);
  });
});

describe("콘솔 명령 미리보기 — 서버 에미터와 같은 줄 꼴", () => {
  it("번호가 확인된 그룹은 Group <번호> ; At Preset <번호>", () => {
    const t = track("WASH", [], { group_no: 12, group_no_confirmed: true });
    const lines = cueConsoleCommandLines(t, cue(0, { position_preset_no: "2.1", color_preset_no: "4.3" }));
    expect(lines).toContain("Group 12 ; At Preset 2.1");
    expect(lines).toContain("Group 12 ; At Preset 4.3");
  });
  it("번호 미확인 그룹은 번호를 지어내지 않는다", () => {
    const lines = cueConsoleCommandLines(track("WASH", []), cue(0, { color_preset_no: "4.3" }));
    expect(lines.some((l) => /Group \d/.test(l))).toBe(false);
    expect(lines.join("\n")).toMatch(/번호 미확인/);
  });
  it("값이 전부 미정이면 낼 명령 없음", () => {
    expect(cueConsoleCommandLines(track("A", []), cue(0)).join("\n")).toMatch(/낼 명령 없음/);
  });
  it("전환 화면은 CueFade 초와 트리거 시각", () => {
    const lines = transitionConsoleCommandLines(cue(4, { entry: { fade_bars: 1, mib_mode: null } }), 2.14, null);
    expect(lines.join("\n")).toMatch(/CueFade 2\.14/);
    expect(lines.join("\n")).toMatch(/4마디/);
  });
  it("페이드 미정이면 CueFade 를 지어내지 않는다", () => {
    expect(transitionConsoleCommandLines(cue(4), 2.14, null).join("\n")).not.toMatch(/CueFade \d/);
  });
});

describe("stageGroupZones — 2D 무대 그룹 영역(REQ-LDBEAT-022(b))", () => {
  const tracks = [track("WASH", []), track("BACK", [])];
  const fixtures = [
    { fid: 1, name: "w1", x: 0, y: 0, z: 0, rotx: 0, roty: 0, rotz: 0, confirmedGroupName: "WASH" },
    { fid: 2, name: "w2", x: 10, y: 0, z: 0, rotx: 0, roty: 0, rotz: 0, confirmedGroupName: "wash" },
    { fid: 3, name: "b1", x: 5, y: 10, z: 0, rotx: 0, roty: 0, rotz: 0, confirmedGroupName: "BACK" },
    { fid: 4, name: "u1", x: 5, y: 5, z: 0, rotx: 0, roty: 0, rotz: 0, confirmedGroupName: null },
  ];
  const project = (p: { x: number; y: number }) => ({ cx: p.x * 10, cy: p.y * 10 });
  it("확인된 소속 장비만 묶어 트랙마다 영역 하나", () => {
    const zones = stageGroupZones(fixtures, tracks, project, 4);
    expect(zones.map((z) => z.trackIndex)).toEqual([0, 1]);
    expect(zones[0]).toMatchObject({ label: "WASH", x: -4, y: -4, width: 108, height: 8, fixtureCount: 2 });
  });
  it("소속 미확인 장비는 어느 영역에도 안 들어간다", () => {
    const zones = stageGroupZones(fixtures, tracks, project, 4);
    expect(zones.reduce((n, z) => n + z.fixtureCount, 0)).toBe(3);
  });
});
