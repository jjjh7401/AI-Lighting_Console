// BeatGrid 순수 함수 시험 (SPEC-LDBEAT-001 M2, 카드 t532).
//
// 같은 바운드: 이 프로젝트는 DOM/jsdom 시험대가 없다(RunbookMode.test.tsx와
// 같은 메모) — 컴포넌트 자체를 렌더하지 않고, 내보낸 순수 함수만 직접
// 부른다.
import { describe, expect, it } from "vitest";

import type { BeatGridCue, BeatGridSceneMemo, BeatGridTrack, BeatGridView } from "../protocol";
import {
  BEAT_GRID_BAR_ROWS,
  PX_PER_BAR,
  UNCONFIRMED_PROBE_STATUS,
  UNSET_FIELD_LABEL,
  barRowIndex,
  barToSeconds,
  barToX,
  buildProbeStatusTable,
  clampSkipSeconds,
  computeStageBounds,
  cueColorFill,
  cueForBar,
  cueIsActive,
  deriveFadeSeconds,
  fixtureDisplayColor,
  fixtureDisplayOpacity,
  formatBrightnessField,
  formatFadeBarsField,
  formatPresetField,
  formatSourceRefLabel,
  groupTracksByLayerFolder,
  isFirstCueOfSong,
  isUnconfirmedShapeCue,
  isWriteLocked,
  layerFolderLabel,
  probeStatusClass,
  projectFixture,
  sceneMemoForBar,
  secondsToBar,
  trackCueSegments,
  type BeatGridFixturePoint,
} from "./BeatGrid";

/** 구조화 필드를 전부 미정으로 둔 완전한 모양(레거시 테스트 픽스처용 —
 * `normalize_beat_grid_cue`가 서버에서 돌려주는 모양과 같다). */
function cue(bar: number, label: string): BeatGridCue {
  return {
    bar,
    label,
    brightness: { mode: null, value_percent: null, preset_no: null },
    position_preset_no: null,
    color_preset_no: null,
    effect_preset_no: null,
    effect_kind: null,
    entry: { fade_bars: null, mib_mode: null },
    source_ref: null,
  };
}

function structuredCue(bar: number, overrides: Partial<BeatGridCue> = {}): BeatGridCue {
  return { ...cue(bar, overrides.label ?? ""), ...overrides };
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
  scene_memos: [],
  probe_results: {},
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

describe("buildProbeStatusTable / isWriteLocked — REQ-LDBEAT-001~003(b), 카드 t537", () => {
  it("defaults all 9 items to 미확인 when nothing is supplied — 지어낸 PASS 0건", () => {
    const probes = buildProbeStatusTable();

    expect(probes).toHaveLength(9);
    expect(probes.every((p) => p.status === UNCONFIRMED_PROBE_STATUS)).toBe(true);
    expect(isWriteLocked(probes)).toBe(true);
  });

  it("falls back to 미확인 for any item missing from the supplied record", () => {
    const partial = { 1: "통과(구조)" };
    const probes = buildProbeStatusTable(partial);

    expect(probes[0].status).toBe("통과(구조)");
    expect(probes[1].status).toBe(UNCONFIRMED_PROBE_STATUS);
  });

  it("unlocks only when all 9 items start with 통과 — progress.md의 실제 판정 문구 그대로", () => {
    const allPass = Object.fromEntries(Array.from({ length: 9 }, (_, i) => [i + 1, "통과(구조)"]));
    const probes = buildProbeStatusTable(allPass);

    expect(isWriteLocked(probes)).toBe(false);
  });

  it("stays locked when even one item is 부분/미확인/움직임 없음 — progress.md의 실제 M1 결과", () => {
    const mixed = {
      1: "통과(구조)",
      2: "미확인",
      3: "부분",
      4: "미확인",
      5: "움직임 없음",
      6: "미확인 — 문법 불명",
      7: "부분(결과 기록)",
      8: "통과",
      9: "wave 움직임 없음 · circle·발리후 미확인",
    };
    const probes = buildProbeStatusTable(mixed);

    expect(isWriteLocked(probes)).toBe(true);
  });
});

describe("probeStatusClass — 카드 t537 (progress.md 판정 칸의 자유 문자열)", () => {
  it("통과로 시작하면 pass — 괄호 설명이 붙어도 마찬가지", () => {
    expect(probeStatusClass("통과")).toBe("pass");
    expect(probeStatusClass("통과(구조)")).toBe("pass");
    expect(probeStatusClass("통과(가설 반증)")).toBe("pass");
  });

  it("정확히 미확인이면 pending", () => {
    expect(probeStatusClass(UNCONFIRMED_PROBE_STATUS)).toBe("pending");
  });

  it("그 밖의 모든 상태(부분/움직임 없음/문법 불명 등)는 fail — 아직 쓰기를 열 근거가 아니다", () => {
    expect(probeStatusClass("부분")).toBe("fail");
    expect(probeStatusClass("움직임 없음")).toBe("fail");
    expect(probeStatusClass("미확인 — 문법 불명")).toBe("fail");
    expect(probeStatusClass("wave 움직임 없음 · circle·발리후 미확인")).toBe("fail");
  });
});

describe("구조화 필드 표시 헬퍼 — 카드 t537 (REQ-LDBEAT-006, 미정은 지어내지 않는다)", () => {
  it("formatBrightnessField — value 모드는 퍼센트", () => {
    expect(formatBrightnessField({ mode: "value", value_percent: 60, preset_no: null })).toBe("60%");
  });

  it("formatBrightnessField — mode가 null이면 미정", () => {
    expect(formatBrightnessField({ mode: null, value_percent: null, preset_no: null })).toBe(
      UNSET_FIELD_LABEL,
    );
  });

  it("formatBrightnessField — 디머 프리셋 모드는 프리셋 번호", () => {
    expect(
      formatBrightnessField({ mode: "dimmer_preset", value_percent: null, preset_no: "1.31" }),
    ).toBe("1.31");
  });

  it("formatPresetField — null이면 미정, 값이 있으면 그대로", () => {
    expect(formatPresetField(null)).toBe(UNSET_FIELD_LABEL);
    expect(formatPresetField("4.21")).toBe("4.21");
  });

  it("formatFadeBarsField — null이면 미정, 값이 있으면 마디 단위", () => {
    expect(formatFadeBarsField(null)).toBe(UNSET_FIELD_LABEL);
    expect(formatFadeBarsField(2)).toBe("2마디");
    expect(formatFadeBarsField(0)).toBe("0마디"); // 끊어 바꿈(0마디)도 미정과 다르다
  });

  it("deriveFadeSeconds — 마디 수 × 마디당 초(BPM 파생값, 저장하지 않음)", () => {
    expect(deriveFadeSeconds(2, 1.5)).toBe(3);
  });

  it("deriveFadeSeconds — fadeBars나 secondsPerBar가 없으면 null(지어내지 않음)", () => {
    expect(deriveFadeSeconds(null, 1.5)).toBeNull();
    expect(deriveFadeSeconds(2, null)).toBeNull();
    expect(deriveFadeSeconds(2, 0)).toBeNull();
  });

  it("formatSourceRefLabel — 있으면 그대로, 없으면 null", () => {
    expect(formatSourceRefLabel("reports/effect-arrangement-rules-20261007.md:106")).toBe(
      "reports/effect-arrangement-rules-20261007.md:106",
    );
    expect(formatSourceRefLabel(null)).toBeNull();
  });
});

describe("cueColorFill — plan.md M7 (3) (미정은 중립, 임의 색을 지어내지 않는다)", () => {
  it("color_preset_no가 없으면 중립(미정)", () => {
    const result = cueColorFill(structuredCue(0, { color_preset_no: null }));
    expect(result.isColorUnset).toBe(true);
    expect(result.background).toBeUndefined();
  });

  it("color_preset_no는 있지만 아는 색이 없으면 — 역시 중립(지어내지 않음)", () => {
    const result = cueColorFill(structuredCue(0, { color_preset_no: "4.21" }), {});
    expect(result.isColorUnset).toBe(true);
  });

  it("color_preset_no가 실제 색 표에 있으면 그 색을 쓴다", () => {
    const result = cueColorFill(structuredCue(0, { color_preset_no: "4.21" }), { "4.21": "#ff69b4" });
    expect(result.isColorUnset).toBe(false);
    expect(result.background).toBe("#ff69b4");
  });
});

describe("sceneMemoForBar — t537 ② 리드 추가 지시 (SCENE 열 값은 메모로만)", () => {
  const memos: BeatGridSceneMemo[] = [
    { bar: 0, text: "배정 미정 — SCENE 원값 「BACK 차가운 실루엣 30%」", source_ref: "x:104" },
    { bar: 7, text: "배정 미정 — SCENE 원값 「라벤더 워시 40%(2마디 번짐) · FOH 켬」", source_ref: "x:106" },
  ];

  it("그 행(4마디 단위)의 시작 마디에 매달린 메모를 찾는다", () => {
    expect(sceneMemoForBar(memos, 0)?.bar).toBe(0);
  });

  it("같은 행의 다른 마디에서도 같은 메모가 보인다", () => {
    // 7~10 행의 어느 마디(8·9·10)를 봐도 bar=7 메모가 보인다.
    expect(sceneMemoForBar(memos, 9)?.bar).toBe(7);
  });

  it("메모가 없는 행은 null — 지어내지 않는다", () => {
    expect(sceneMemoForBar(memos, 11)).toBeNull();
  });

  it("표시 범위 밖의 마디는 null", () => {
    expect(sceneMemoForBar(memos, 99)).toBeNull();
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
