// BeatGrid 순수 함수 시험 (SPEC-LDBEAT-001 M2, 카드 t532).
//
// 같은 바운드: 이 프로젝트는 DOM/jsdom 시험대가 없다(RunbookMode.test.tsx와
// 같은 메모) — 컴포넌트 자체를 렌더하지 않고, 내보낸 순수 함수만 직접
// 부른다.
import { describe, expect, it } from "vitest";

import type { BeatGridCue, BeatGridTrack, BeatGridView } from "../protocol";
import {
  BEAT_GRID_BAR_ROWS,
  PX_PER_BAR,
  barRowIndex,
  barToSeconds,
  barToX,
  buildProbeStatusTable,
  clampSkipSeconds,
  computeStageBounds,
  cueForBar,
  cueIsActive,
  fixtureDisplayColor,
  fixtureDisplayOpacity,
  groupTracksByLayerFolder,
  isFirstCueOfSong,
  isUnconfirmedShapeCue,
  isWriteLocked,
  layerFolderLabel,
  probeStatusClass,
  projectFixture,
  secondsToBar,
  trackCueSegments,
  type BeatGridFixturePoint,
} from "./BeatGrid";

function cue(bar: number, label: string): BeatGridCue {
  return { bar, label };
}

function track(
  group_name: string,
  layer_role: string | null,
  cues: BeatGridCue[],
  group_no_confirmed = true,
): BeatGridTrack {
  return { group_no: group_no_confirmed ? 1 : null, group_no_confirmed, group_name, layer_role, cues };
}

const LOVE_ATTACK_GRID: BeatGridView = {
  song_title: "LOVE ATTACK",
  bar_range: { start: 0, end: 25 },
  source: "love_attack_default",
  note: null,
  tracks: [
    track("BACK", "back", [cue(0, "앞박 1회"), cue(18, "킥 1·2·4박 100%")]),
    track("SIDE-ALL", "side", [cue(0, "—"), cue(11, "SIDE-L/R 2·4박 번갈이")]),
    track("MOVER-U", "mover", [cue(0, "바닥 쪽 좁은 빔, 정지")]),
    track("STROBE", "effect", [], false),
  ],
};

describe("barRowIndex", () => {
  it("places bar 0 in the first row", () => {
    expect(barRowIndex(0)).toBe(0);
  });

  it("places bar 25 in the last row", () => {
    expect(barRowIndex(25)).toBe(BEAT_GRID_BAR_ROWS.length - 1);
  });

  it("returns -1 for a bar outside the displayed range", () => {
    expect(barRowIndex(26)).toBe(-1);
  });

  it("places bar 11 in the fourth row (11~13)", () => {
    expect(barRowIndex(11)).toBe(3);
  });
});

describe("cueForBar", () => {
  const t = track("BACK", "back", [cue(0, "앞박"), cue(7, "킥"), cue(18, "100%")]);

  it("returns the most recent cue at or before the bar", () => {
    expect(cueForBar(t, 10)?.label).toBe("킥");
  });

  it("returns the exact cue when the bar matches exactly", () => {
    expect(cueForBar(t, 18)?.label).toBe("100%");
  });

  it("returns null before the first declared cue", () => {
    const later = track("X", null, [cue(5, "later")]);
    expect(cueForBar(later, 0)).toBeNull();
  });

  it("returns null for a track with no cues at all — never invents one", () => {
    expect(cueForBar(track("EMPTY", null, []), 10)).toBeNull();
  });
});

describe("barToSeconds / secondsToBar", () => {
  it("converts bar 0 to 0 seconds (앞박)", () => {
    expect(barToSeconds(0, 1.5)).toBe(0);
  });

  it("converts 1 bar to secondsPerBar seconds", () => {
    expect(barToSeconds(1, 1.5)).toBe(1.5);
  });

  it("is null when secondsPerBar is unavailable — never fabricates a tempo", () => {
    expect(barToSeconds(4, null)).toBeNull();
    expect(barToSeconds(4, undefined)).toBeNull();
    expect(barToSeconds(4, 0)).toBeNull();
  });

  it("round-trips bar -> seconds -> bar", () => {
    const seconds = barToSeconds(10, 2.0)!;
    expect(secondsToBar(seconds, 2.0, 25)).toBe(10);
  });

  it("clamps the inverse to the grid's max bar", () => {
    expect(secondsToBar(1000, 2.0, 25)).toBe(25);
  });

  it("clamps the inverse to zero, never negative", () => {
    expect(secondsToBar(-5, 2.0, 25)).toBe(0);
  });
});

describe("clampSkipSeconds", () => {
  it("moves forward by the delta", () => {
    expect(clampSkipSeconds(10, 10, 100)).toBe(20);
  });

  it("never goes below zero", () => {
    expect(clampSkipSeconds(5, -10, 100)).toBe(0);
  });

  it("never exceeds the song's total length", () => {
    expect(clampSkipSeconds(95, 10, 100)).toBe(100);
  });
});

describe("groupTracksByLayerFolder", () => {
  it("groups by layer_role and preserves first-seen order", () => {
    const folders = groupTracksByLayerFolder(LOVE_ATTACK_GRID.tracks);

    expect(folders.map((f) => f.role)).toEqual(["back", "side", "mover", "effect"]);
    expect(folders[0].label).toBe("역광");
    expect(folders.find((f) => f.role === "effect")!.tracks).toHaveLength(1);
  });

  it("falls back to 미분류 for a null layer_role", () => {
    const tracks = [track("MYSTERY", null, [])];
    const folders = groupTracksByLayerFolder(tracks);

    expect(folders[0].label).toBe("미분류");
  });
});

describe("layerFolderLabel", () => {
  it("maps every RIG_LAYER_ROLES vocabulary token to a Korean label", () => {
    expect(layerFolderLabel("key")).toBe("앞빛");
    expect(layerFolderLabel("back")).toBe("역광");
    expect(layerFolderLabel("side")).toBe("옆빛");
    expect(layerFolderLabel("wash")).toBe("워시");
    expect(layerFolderLabel("mover")).toBe("무빙");
    expect(layerFolderLabel("effect")).toBe("효과");
    expect(layerFolderLabel("audience")).toBe("객석");
  });

  it("falls back to 미분류 for null/unknown roles", () => {
    expect(layerFolderLabel(null)).toBe("미분류");
    expect(layerFolderLabel("unknown-role")).toBe("미분류");
  });
});

describe("isUnconfirmedShapeCue — REQ-LDBEAT-010/AC-LDBEAT-004", () => {
  it("flags a circle shape", () => {
    expect(isUnconfirmedShapeCue("U·D 발리후 ⚠")).toBe(true);
  });

  it("flags the English spelling too", () => {
    expect(isUnconfirmedShapeCue("ballyhoo move")).toBe(true);
  });

  it("does not flag a confirmed-shape cue", () => {
    expect(isUnconfirmedShapeCue("틸트 웨이브, 한 바퀴 2마디")).toBe(false);
  });
});

describe("buildProbeStatusTable / isWriteLocked — REQ-LDBEAT-001~003", () => {
  it("defaults all 9 items to 미실행 when nothing is supplied", () => {
    const probes = buildProbeStatusTable();

    expect(probes).toHaveLength(9);
    expect(probes.every((p) => p.status === "미실행")).toBe(true);
    expect(isWriteLocked(probes)).toBe(true);
  });

  it("unlocks only when all 9 items are pass", () => {
    const allPass = Object.fromEntries(Array.from({ length: 9 }, (_, i) => [i + 1, "pass" as const]));
    const probes = buildProbeStatusTable(allPass);

    expect(isWriteLocked(probes)).toBe(false);
  });

  it("stays locked when even one item is not pass", () => {
    const allPass = Object.fromEntries(Array.from({ length: 9 }, (_, i) => [i + 1, "pass" as const]));
    const probes = buildProbeStatusTable({ ...allPass, 9: "fail" });

    expect(isWriteLocked(probes)).toBe(true);
  });
});

describe("probeStatusClass — 카드 t534 (네 상태가 각자 다른 자리)", () => {
  it("pass/fail/미실행은 그대로", () => {
    expect(probeStatusClass("pass")).toBe("pass");
    expect(probeStatusClass("fail")).toBe("fail");
    expect(probeStatusClass("미실행")).toBe("pending");
  });

  it("「리허설PASS·실기미실행」은 「미실행」과 다른 자리(rehearsal) — 섞여 보이면 리허설 통과 사실이 사라진다", () => {
    expect(probeStatusClass("리허설PASS·실기미실행")).toBe("rehearsal");
    expect(probeStatusClass("리허설PASS·실기미실행")).not.toBe(probeStatusClass("미실행"));
  });
});

describe("isFirstCueOfSong — REQ-LDBEAT-004(d)", () => {
  it("is true at the grid's first bar", () => {
    expect(isFirstCueOfSong(0, LOVE_ATTACK_GRID)).toBe(true);
  });

  it("is false after the first bar", () => {
    expect(isFirstCueOfSong(7, LOVE_ATTACK_GRID)).toBe(false);
  });
});

describe("2D stage projection", () => {
  const fixtures: BeatGridFixturePoint[] = [
    { fid: 201, name: "BACK 201", x: -6, y: 4.5, z: 6.2, rotx: 0, roty: 0, rotz: 0 },
    { fid: 202, name: "BACK 202", x: 6, y: 4.5, z: 6.2, rotx: 0, roty: 0, rotz: 0 },
    { fid: 301, name: "SIDE-L 301", x: -7, y: 0.5, z: 1.2, rotx: 0, roty: 0, rotz: 0 },
  ];

  it("returns null bounds for an empty fixture list — never fabricates a stage", () => {
    expect(computeStageBounds([])).toBeNull();
  });

  it("computes bounds from the measured fixture range", () => {
    const bounds = computeStageBounds(fixtures)!;

    expect(bounds.minX).toBe(-7);
    expect(bounds.maxX).toBe(6);
    expect(bounds.maxY).toBe(4.5);
  });

  it("projects within the SVG viewBox", () => {
    const bounds = computeStageBounds(fixtures)!;
    const { cx, cy } = projectFixture(fixtures[0], bounds);

    expect(cx).toBeGreaterThanOrEqual(0);
    expect(cy).toBeGreaterThanOrEqual(0);
  });

  // 레인 리뷰(05ad9ec4) — 이름 접두 일치는 소속 확인이 아니다. 색은
  // `confirmedGroupName`(콘솔 SELECTIONDATA에서 읽은 값)이 화면의 트랙
  // `group_name`과 **정확히** 일치할 때만 나온다 — 이름이 비슷해 보인다는
  // 추론은 fallback으로도 쓰지 않는다. 아래 "BACK 201" 두 시험은 **같은
  // 장비, 다른 필드**로 대조한다 — 수정 전 구현에서는 첫 시험(이름만
  // 일치, confirmedGroupName 없음)이 색칠돼 **실패했다**(RED, 레인 리뷰
  // 코멘트가 지적한 바로 그 결함).
  it("stays grey for a name-matching fixture with NO confirmed SELECTIONDATA membership — no name fallback", () => {
    const nameMatchesButUnconfirmed = fixtures[0]; // "BACK 201" — BACK 트랙과 이름만 같다, confirmedGroupName 없음
    expect(fixtureDisplayColor(nameMatchesButUnconfirmed, LOVE_ATTACK_GRID.tracks)).toBe("#5a5f6b");
  });

  it("colors a fixture whose confirmedGroupName EXACTLY matches a track's group_name", () => {
    // t525 §② "근거 2 — sf_index → fid 대응"(verdict.md:101) — fid 201은
    // 콘솔 SELECTIONDATA로 BACK 그룹 소속이 확인됐다.
    const confirmed: BeatGridFixturePoint = { ...fixtures[0], confirmedGroupName: "BACK" };
    expect(fixtureDisplayColor(confirmed, LOVE_ATTACK_GRID.tracks)).not.toBe("#5a5f6b");
  });

  it("greys out a confirmed membership whose group name has no matching track on screen", () => {
    // t525 §②(verdict.md:100)가 확인한 그룹은 "MOVER-ALL"이지 "MOVER-U"가
    // 아니다 — LOVE ATTACK 기본 격자에는 MOVER-ALL 트랙이 없으므로(트랙은
    // MOVER-U/MOVER-D), 이 확인은 화면의 어느 트랙과도 일치하지 않는다.
    // 이름이 "MOVER-U 501"이라고 해서 MOVER-U 트랙 색을 받지 않는다.
    const moverAllMember: BeatGridFixturePoint = {
      fid: 501,
      name: "MOVER-U 501",
      x: -1.5,
      y: 2.5,
      z: 6.8,
      rotx: 0,
      roty: 0,
      rotz: 0,
      confirmedGroupName: "MOVER-ALL",
    };
    expect(fixtureDisplayColor(moverAllMember, LOVE_ATTACK_GRID.tracks)).toBe("#5a5f6b");
  });

  it("greys out a fixture with no confirmedGroupName at all", () => {
    const strobeFixture: BeatGridFixturePoint = {
      fid: 611,
      name: "STROBE 611",
      x: 0,
      y: 0,
      z: 0,
      rotx: 0,
      roty: 0,
      rotz: 0,
    };
    expect(fixtureDisplayColor(strobeFixture, LOVE_ATTACK_GRID.tracks)).toBe("#5a5f6b");
  });

  it("greys out a fixture matching no track at all", () => {
    const unmatched: BeatGridFixturePoint = {
      fid: 999,
      name: "HAZE 621",
      x: 0,
      y: 0,
      z: 0,
      rotx: 0,
      roty: 0,
      rotz: 0,
    };
    expect(fixtureDisplayColor(unmatched, LOVE_ATTACK_GRID.tracks)).toBe("#5a5f6b");
  });
});

// 카드 t534 — 트랙 칸을 마디 시간축 위 막대로 배치하기 위한 순수 함수.
describe("barToX / PX_PER_BAR — 카드 t534", () => {
  it("places bar 0 at x=0", () => {
    expect(barToX(0)).toBe(0);
  });

  it("scales linearly by PX_PER_BAR", () => {
    expect(barToX(3)).toBe(3 * PX_PER_BAR);
  });

  it("accepts a custom pixel-per-bar override", () => {
    expect(barToX(2, 10)).toBe(20);
  });
});

describe("trackCueSegments — 카드 t534 (칸 길이 = 다음 칸까지)", () => {
  const t = track("BACK", "back", [cue(0, "앞박"), cue(3, "4박마다"), cue(18, "100%")]);

  it("각 칸의 길이는 다음 칸이 시작하는 마디까지", () => {
    const segments = trackCueSegments(t, 25);
    expect(segments).toEqual([
      { cue: t.cues[0], startBar: 0, endBar: 3 },
      { cue: t.cues[1], startBar: 3, endBar: 18 },
      { cue: t.cues[2], startBar: 18, endBar: 26 },
    ]);
  });

  it("마지막 칸은 maxBar+1까지 이어진다(격자 끝까지)", () => {
    const segments = trackCueSegments(t, 25);
    expect(segments[segments.length - 1].endBar).toBe(26);
  });

  it("칸이 없는 트랙은 빈 배열(지어내지 않음)", () => {
    expect(trackCueSegments(track("EMPTY", null, []), 25)).toEqual([]);
  });
});

describe("cueIsActive — 카드 t534 (「—」는 꺼짐/변화없음)", () => {
  it("「—」는 꺼짐", () => {
    expect(cueIsActive("—")).toBe(false);
  });

  it("빈 문자열·공백도 꺼짐", () => {
    expect(cueIsActive("")).toBe(false);
    expect(cueIsActive("   ")).toBe(false);
  });

  it("내용이 있는 문장은 켜짐", () => {
    expect(cueIsActive("앞박 1회")).toBe(true);
  });
});

describe("fixtureDisplayOpacity — 카드 t534 (2D 무대 밝기: 실측 on/off 칸만, 수치 디머 지어내지 않음)", () => {
  const fixture: BeatGridFixturePoint = {
    fid: 201,
    name: "BACK 201",
    x: -6,
    y: 4.5,
    z: 6.2,
    rotx: 0,
    roty: 0,
    rotz: 0,
    confirmedGroupName: "BACK",
  };

  it("확인된 소속 + 켜진 칸 = 1(최대)", () => {
    // LOVE_ATTACK_GRID 의 BACK 트랙은 bar 0 에 "앞박 1회"(켜짐)가 있다.
    expect(fixtureDisplayOpacity(fixture, LOVE_ATTACK_GRID.tracks, 0)).toBe(1);
  });

  it("확인된 소속이지만 이 마디는 꺼진 칸(「—」) = 흐리게", () => {
    const grid: BeatGridView = {
      ...LOVE_ATTACK_GRID,
      tracks: [track("BACK", "back", [cue(0, "앞박 1회"), cue(11, "—")])],
    };
    expect(fixtureDisplayOpacity(fixture, grid.tracks, 11)).toBeLessThan(1);
  });

  it("소속 미확인은 흐리게(회색과 같은 방향)", () => {
    const unconfirmed: BeatGridFixturePoint = { ...fixture, confirmedGroupName: null };
    expect(fixtureDisplayOpacity(unconfirmed, LOVE_ATTACK_GRID.tracks, 0)).toBeLessThan(1);
  });

  it("이 마디에 아직 칸이 선언 안 됐으면 흐리게(지어내지 않음)", () => {
    const grid: BeatGridView = {
      ...LOVE_ATTACK_GRID,
      tracks: [track("BACK", "back", [cue(5, "5마디부터")])],
    };
    expect(fixtureDisplayOpacity(fixture, grid.tracks, 0)).toBeLessThan(1);
  });
});
