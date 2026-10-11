// BeatGrid 순수 함수 시험 (SPEC-LDBEAT-001 M2, 카드 t532).
//
// 같은 바운드: 이 프로젝트는 DOM/jsdom 시험대가 없다(RunbookMode.test.tsx와
// 같은 메모) — 컴포넌트 자체를 렌더하지 않고, 내보낸 순수 함수만 직접
// 부른다.
import { readFileSync } from "node:fs";

import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type {
  BeatGridCue,
  BeatGridDrawerEntry,
  BeatGridDrawerSection,
  BeatGridPendingSuggestion,
  BeatGridSceneMemo,
  BeatGridTrack,
  BeatGridView,
} from "../protocol";
import { cueEditKey } from "./beatgrid/cueDisplayState";
import {
  BEAT_GRID_BAR_ROWS,
  NEW_PRESET_OPTION_VALUE,
  PX_PER_BAR,
  UNCONFIRMED_PROBE_STATUS,
  UNSET_FIELD_LABEL,
  appMovementAxisConflictWarning,
  barRowIndex,
  barToSeconds,
  barToX,
  buildBrightnessDimmerEffectChanges,
  buildBrightnessPresetChanges,
  buildColorPresetChanges,
  buildEffectPresetChanges,
  buildPositionPresetChanges,
  buildProbeStatusTable,
  clampSkipSeconds,
  computeStageBounds,
  barPercentInRange,
  cueColorFill,
  cueForBar,
  cueIsActive,
  deriveFadeSeconds,
  deriveSectionBlocks,
  findDrawerSection,
  fixtureDisplayColor,
  fixtureDisplayOpacity,
  formatAppMovementField,
  formatBrightnessField,
  formatDrawerEntryOptionLabel,
  presetPickChanges,
  formatEvidenceField,
  formatFadeBarsField,
  formatPresetField,
  formatSourceRefLabel,
  groupTracksByLayerFolder,
  isFirstCueOfSong,
  isValidConsoleLabel,
  NewPresetDialog,
  unverifiedCellIndex,
  isWriteLocked,
  layerFolderLabel,
  buildBrightnessValueChanges,
  cueReferencesPreset,
  isBrightnessValueEditable,
  isPendingSuggestionForTrack,
  pendingApprovalBadge,
  presetPoolBandBadge,
  panOnlyVerticalBaseWarning,
  probeStatusClass,
  projectFixture,
  sceneMemoForBar,
  sceneMemoMarkers,
  secondsToBar,
  splitDrawerSectionEffectEntries,
  splitDrawerSectionEntries,
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
    app_movement: null,
    evidence: null,
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
  unsent_cells: null,
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

describe("unverifiedCellIndex — REQ-LDBEAT-010/AC-LDBEAT-004, 카드 t579", () => {
  it("indexes the server list by track name and bar", () => {
    const index = unverifiedCellIndex([{ group_name: "MOVER-U", bar: 14, terms: ["circle"] }]);
    expect(index.get(cueEditKey("MOVER-U", 14))).toEqual(["circle"]);
    expect(index.get(cueEditKey("MOVER-U", 13))).toBeUndefined();
    expect(index.get(cueEditKey("MOVER-D", 14))).toBeUndefined();
  });

  it("an old server without the field yields no badge", () => {
    expect(unverifiedCellIndex(undefined).size).toBe(0);
    expect(unverifiedCellIndex(null).size).toBe(0);
  });

  it("a label that merely mentions a shape is not a badge source any more", () => {
    // 옛 상수 목록은 라벨 글자 「위상 펼침」 만으로 배지를 달았다 — 실측으로 열린
    // MOVER-D 7마디(t548 D1)도 그래서 미확인으로 보였다. 이제 서버 목록에 없으면 없다.
    const index = unverifiedCellIndex([]);
    expect(index.get(cueEditKey("MOVER-D", 7))).toBeUndefined();
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

describe("sceneMemoMarkers — t537 ② plan-audit iteration 3 D1 (렌더 파생 — 미정 배지+§4 원문+source_ref)", () => {
  // REQ-LDBEAT-006(iv-3) — glance 패널이 실제로 렌더하는 세 요소(⚠ 배지,
  // §4 원문 텍스트, source_ref)를 DOM 없이도 단언한다(이 프로젝트는
  // jsdom이 없다). 여섯 값 전부는 `beat_grid_data/love_attack.yaml`의
  // 실제 SCENE 메모 텍스트·source_ref와 바이트 동일하다.
  const LOVE_ATTACK_MEMOS: BeatGridSceneMemo[] = [
    {
      bar: 0,
      text: "배정 미정 — SCENE 원값 「BACK 차가운 실루엣 30%」",
      source_ref: "reports/effect-arrangement-rules-20261007.md:104",
    },
    {
      bar: 7,
      text: "배정 미정 — SCENE 원값 「라벤더 워시 40%(2마디 번짐) · FOH 켬」",
      source_ref: "reports/effect-arrangement-rules-20261007.md:106",
    },
    {
      bar: 11,
      text: "배정 미정 — SCENE 원값 「틴트 한 단계」",
      source_ref: "reports/effect-arrangement-rules-20261007.md:107",
    },
    {
      bar: 14,
      text: "배정 미정 — SCENE 원값 「워시 25% 덜어냄」",
      source_ref: "reports/effect-arrangement-rules-20261007.md:108",
    },
    {
      bar: 18,
      text: "배정 미정 — SCENE 원값 「핑크 70% 끊어 바꿈 · 밝기 올림」",
      source_ref: "reports/effect-arrangement-rules-20261007.md:109",
    },
    {
      bar: 22,
      text: "배정 미정 — SCENE 원값 「22마디 핑크→피치 1마디 번짐」",
      source_ref: "reports/effect-arrangement-rules-20261007.md:110",
    },
  ];

  it("표시 범위 전체(0~25)에서 여섯 메모 전부가 배지+원문+source_ref로 뽑힌다", () => {
    const markers = sceneMemoMarkers(LOVE_ATTACK_MEMOS, [0, 25]);

    expect(markers.map((marker) => marker.bar)).toEqual([0, 7, 11, 14, 18, 22]);
    for (const marker of markers) {
      expect(marker.label).toBe(UNSET_FIELD_LABEL);
    }
    expect(markers[0].text).toBe(LOVE_ATTACK_MEMOS[0].text);
    expect(markers[0].sourceRef).toBe(LOVE_ATTACK_MEMOS[0].source_ref);
    expect(markers[4].text).toBe(LOVE_ATTACK_MEMOS[4].text);
    expect(markers[4].sourceRef).toBe(LOVE_ATTACK_MEMOS[4].source_ref);
  });

  it("단일 마디로 좁힌 범위는 그 마디가 속한 행의 메모 하나만 돌려준다(glance 패널과 같은 호출 모양)", () => {
    // 9마디는 7~10행에 속한다 — sceneMemoForBar(memos, 9)와 같은 행 규칙.
    const markers = sceneMemoMarkers(LOVE_ATTACK_MEMOS, [9, 9]);

    expect(markers).toHaveLength(1);
    expect(markers[0]).toEqual({
      bar: 7,
      label: UNSET_FIELD_LABEL,
      text: LOVE_ATTACK_MEMOS[1].text,
      sourceRef: LOVE_ATTACK_MEMOS[1].source_ref,
    });
  });

  it("표시 범위 밖에 걸린 메모는 결과에서 빠진다(추측 0건)", () => {
    const markers = sceneMemoMarkers(LOVE_ATTACK_MEMOS, [0, 6]);

    expect(markers).toEqual([
      {
        bar: 0,
        label: UNSET_FIELD_LABEL,
        text: LOVE_ATTACK_MEMOS[0].text,
        sourceRef: LOVE_ATTACK_MEMOS[0].source_ref,
      },
    ]);
  });

  it("메모가 하나도 없는 곡은 빈 배열이다 — 지어내지 않는다", () => {
    const noMemoSong: BeatGridSceneMemo[] = [];

    expect(sceneMemoMarkers(noMemoSong, [0, 25])).toEqual([]);
  });

  it("리그·곡이 전혀 다른 가짜 곡의 메모도 같은 규칙으로 뽑힌다(REQ-LDBEAT-006(v-1)(v-2) — 로더 일반화와 같은 원칙)", () => {
    const differentFakeSongMemos: BeatGridSceneMemo[] = [
      {
        bar: 3,
        text: "배정 미정 — 다른 곡 SCENE 원값 「테스트 전용 자리」",
        source_ref: "fake-song-report.md:1",
      },
    ];

    const markers = sceneMemoMarkers(differentFakeSongMemos, [0, 10]);

    expect(markers).toEqual([
      {
        bar: 3,
        label: UNSET_FIELD_LABEL,
        text: "배정 미정 — 다른 곡 SCENE 원값 「테스트 전용 자리」",
        sourceRef: "fake-song-report.md:1",
      },
    ]);
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

describe("deriveSectionBlocks — t537 레이아웃 교정 (곡 전체 지도 구간 띠, REQ-LDBEAT-004(a))", () => {
  it("secondsPerBar가 없으면 빈 배열 — 숫자 띠 폴백으로 떨어진다(지어내지 않음)", () => {
    const sections = [{ label: "INTRO", start_ms: 0 }];
    expect(deriveSectionBlocks(sections, null, 0, 25)).toEqual([]);
    expect(deriveSectionBlocks(sections, undefined, 0, 25)).toEqual([]);
    expect(deriveSectionBlocks(sections, 0, 0, 25)).toEqual([]);
  });

  it("구간 데이터가 없으면 빈 배열", () => {
    expect(deriveSectionBlocks([], 1.5, 0, 25)).toEqual([]);
    expect(deriveSectionBlocks(undefined, 1.5, 0, 25)).toEqual([]);
  });

  it("start_ms를 secondsPerBar로 마디 위치로 환산하고, 다음 구간 시작까지를 블록으로 묶는다", () => {
    const sections = [
      { label: "INTRO", start_ms: 0 },
      { label: "VERSE", start_ms: 10500 }, // 10.5s / 1.5s = 7마디
    ];
    const blocks = deriveSectionBlocks(sections, 1.5, 0, 25);

    expect(blocks).toEqual([
      { label: "INTRO", startBar: 0, endBar: 7, hex: null },
      { label: "VERSE", startBar: 7, endBar: 26, hex: null },
    ]);
  });

  it("마지막 구간은 표시 범위 끝(rangeEnd+1)까지 이어진다", () => {
    const sections = [{ label: "INTRO", start_ms: 0 }];
    const blocks = deriveSectionBlocks(sections, 1.5, 0, 25);

    expect(blocks[0].endBar).toBe(26);
  });

  it("palette_primary_hex가 있으면 그대로 옮긴다(지어낸 색 없음)", () => {
    const sections = [{ label: "코러스", start_ms: 0, palette_primary_hex: "#ff69b4" }];
    const blocks = deriveSectionBlocks(sections, 1.5, 0, 25);

    expect(blocks[0].hex).toBe("#ff69b4");
  });

  it("palette_primary_hex가 없으면 null(중립) — 임의 색을 지어내지 않는다", () => {
    const sections = [{ label: "코러스", start_ms: 0 }];
    const blocks = deriveSectionBlocks(sections, 1.5, 0, 25);

    expect(blocks[0].hex).toBeNull();
  });

  it("구간 순서가 start_ms 기준으로 뒤섞여 와도 정렬해서 묶는다", () => {
    const sections = [
      { label: "VERSE", start_ms: 10500 },
      { label: "INTRO", start_ms: 0 },
    ];
    const blocks = deriveSectionBlocks(sections, 1.5, 0, 25);

    expect(blocks.map((b) => b.label)).toEqual(["INTRO", "VERSE"]);
  });

  it("표시 범위를 완전히 벗어난 구간은 뺀다", () => {
    const sections = [
      { label: "INTRO", start_ms: 0 },
      { label: "OUTRO", start_ms: 1_000_000 }, // 범위 훨씬 밖
    ];
    const blocks = deriveSectionBlocks(sections, 1.5, 0, 5);

    expect(blocks.map((b) => b.label)).toEqual(["INTRO"]);
  });
});

describe("barPercentInRange — t537 레이아웃 교정 (SCENE 메모 오버레이 위치)", () => {
  it("범위 시작은 0%, 범위를 벗어난 마디는 비례해서 계속 커진다", () => {
    expect(barPercentInRange(0, 0, 25)).toBe(0);
  });

  it("범위 중간 마디는 비례 위치", () => {
    // span = 26 (0~25 포함), bar=13 → 13/26 = 50%
    expect(barPercentInRange(13, 0, 25)).toBeCloseTo(50, 5);
  });

  it("빈 범위(rangeEnd < rangeStart)는 0 — 나눗셈 오류 없음", () => {
    expect(barPercentInRange(5, 10, 5)).toBe(0);
  });
});

describe("formatAppMovementField — t548 REQ-LDBEAT-006(vi)", () => {
  it("app_movement가 없으면 미정", () => {
    expect(formatAppMovementField(null)).toBe(UNSET_FIELD_LABEL);
  });

  it("음악 단위 주기가 있으면 shape·축·주기를 보여준다", () => {
    expect(
      formatAppMovementField({
        shape: "wave",
        axes: ["Pan"],
        period_unit: "beat",
        period_value: 2,
        phase_spread: null,
      }),
    ).toBe("wave · Pan · 2박");
  });

  it("마디 단위 주기도 같은 꼴로 보여준다", () => {
    expect(
      formatAppMovementField({
        shape: "wave",
        axes: ["Tilt"],
        period_unit: "bar",
        period_value: 2,
        phase_spread: true,
      }),
    ).toBe("wave · Tilt · 2마디");
  });

  it("축이 둘이면 Pan+Tilt로 합쳐 보여준다", () => {
    expect(
      formatAppMovementField({
        shape: "circle",
        axes: ["Pan", "Tilt"],
        period_unit: "beat",
        period_value: 4,
        phase_spread: null,
      }),
    ).toBe("circle · Pan+Tilt · 4박");
  });

  it("주기가 미정이면 shape·축만 보여준다(지어내지 않음)", () => {
    expect(
      formatAppMovementField({
        shape: "wave",
        axes: ["Pan"],
        period_unit: null,
        period_value: null,
        phase_spread: null,
      }),
    ).toBe("wave · Pan · 미정");
  });
});

describe("formatEvidenceField — t548 REQ-LDBEAT-006(vii)", () => {
  it("evidence가 없으면 미정", () => {
    expect(formatEvidenceField(null)).toBe(UNSET_FIELD_LABEL);
  });

  it("grade만 있고 approval이 없으면 grade만 보여준다", () => {
    expect(formatEvidenceField({ grade: "name_only", approval: null })).toBe("이름만");
  });

  it("approval이 채워지면 승인 표시를 덧붙인다", () => {
    expect(
      formatEvidenceField({
        grade: "measured",
        approval: { by: "supervisor", date: "2026-10-10", source: "x#1" },
      }),
    ).toBe("측정 · 승인(2026-10-10)");
  });

  it("measured_other_group은 '다른 그룹 실측'으로 보여준다", () => {
    expect(formatEvidenceField({ grade: "measured_other_group", approval: null })).toBe(
      "다른 그룹 실측",
    );
  });
});

describe("appMovementAxisConflictWarning — t548 AC-LDBEAT-016(t)", () => {
  function cueWith(overrides: Partial<BeatGridCue>): BeatGridCue {
    return {
      bar: 0,
      label: "x",
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

  it("app_movement 없으면 충돌 없음", () => {
    expect(appMovementAxisConflictWarning(cueWith({}))).toBeNull();
  });

  it("같은 축(Tilt)을 movement와 effect가 함께 움직이면 충돌", () => {
    const cue = cueWith({
      app_movement: {
        shape: "wave",
        axes: ["Tilt"],
        period_unit: "beat",
        period_value: 2,
        phase_spread: null,
      },
      effect_preset_no: "21.9",
      effect_kind: "position",
    });
    expect(appMovementAxisConflictWarning(cue)).not.toBeNull();
  });

  it("축이 겹치지 않으면(Pan + dimmer 효과) 충돌 없음", () => {
    const cue = cueWith({
      app_movement: {
        shape: "wave",
        axes: ["Pan"],
        period_unit: "beat",
        period_value: 2,
        phase_spread: null,
      },
      effect_preset_no: "21.1",
      effect_kind: "dimmer",
    });
    expect(appMovementAxisConflictWarning(cue)).toBeNull();
  });
});

describe("panOnlyVerticalBaseWarning — t548 감독 결정④", () => {
  function cueWith(overrides: Partial<BeatGridCue>): BeatGridCue {
    return {
      bar: 0,
      label: "x",
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

  it("Pan 단독 + 기준 위치 없음 → 경고", () => {
    const cue = cueWith({
      app_movement: {
        shape: "wave",
        axes: ["Pan"],
        period_unit: null,
        period_value: null,
        phase_spread: null,
      },
    });
    expect(panOnlyVerticalBaseWarning(cue)).not.toBeNull();
  });

  it("Pan 단독 + 기준 위치 있음 → 경고 없음", () => {
    const cue = cueWith({
      app_movement: {
        shape: "wave",
        axes: ["Pan"],
        period_unit: "beat",
        period_value: 2,
        phase_spread: null,
      },
      position_preset_no: "2.1",
    });
    expect(panOnlyVerticalBaseWarning(cue)).toBeNull();
  });

  it("Tilt 단독은 기준 위치가 없어도 경고 없음", () => {
    const cue = cueWith({
      app_movement: {
        shape: "wave",
        axes: ["Tilt"],
        period_unit: "bar",
        period_value: 2,
        phase_spread: true,
      },
    });
    expect(panOnlyVerticalBaseWarning(cue)).toBeNull();
  });

  it("app_movement 없으면 경고 없음", () => {
    expect(panOnlyVerticalBaseWarning(cueWith({}))).toBeNull();
  });
});

describe("isBrightnessValueEditable — 카드 t551(M3), mockup 밝기 값 전용 편집", () => {
  it("칸이 없으면(선택 안 됨) 편집 불가", () => {
    expect(isBrightnessValueEditable(null)).toBe(false);
  });

  it("brightness.mode 가 null(미정)이면 편집 가능 — 처음 값을 넣는 경우", () => {
    const cue = structuredCue(7, {
      brightness: { mode: null, value_percent: null, preset_no: null },
    });
    expect(isBrightnessValueEditable(cue)).toBe(true);
  });

  it("brightness.mode 가 value 면 편집 가능", () => {
    const cue = structuredCue(7, {
      brightness: { mode: "value", value_percent: 40, preset_no: null },
    });
    expect(isBrightnessValueEditable(cue)).toBe(true);
  });

  it("brightness.mode 가 dimmer_preset 이면 편집 불가(목록 선택 필요 — 카탈로그 없음)", () => {
    const cue = structuredCue(7, {
      brightness: { mode: "dimmer_preset", value_percent: null, preset_no: "1.1" },
    });
    expect(isBrightnessValueEditable(cue)).toBe(false);
  });

  it("brightness.mode 가 dimmer_effect 면 편집 불가(목록 선택 필요 — 카탈로그 없음)", () => {
    const cue = structuredCue(7, {
      brightness: { mode: "dimmer_effect", value_percent: null, preset_no: "1.21" },
    });
    expect(isBrightnessValueEditable(cue)).toBe(false);
  });
});

describe("buildBrightnessValueChanges — 카드 t551(M3), apply_beat_grid_edit 와 바이트 동일 모양", () => {
  it("유효한 숫자는 value 모드 changes 를 돌려준다", () => {
    expect(buildBrightnessValueChanges(55)).toEqual({
      brightness: { mode: "value", value_percent: 55, preset_no: null },
    });
  });

  it("0 은 유효한 값이다(꺼짐)", () => {
    expect(buildBrightnessValueChanges(0)).toEqual({
      brightness: { mode: "value", value_percent: 0, preset_no: null },
    });
  });

  it("NaN(빈 입력 등)은 null — 지어내지 않는다", () => {
    expect(buildBrightnessValueChanges(Number.NaN)).toBeNull();
  });

  it("무한값도 null", () => {
    expect(buildBrightnessValueChanges(Number.POSITIVE_INFINITY)).toBeNull();
  });
});

describe("cueReferencesPreset — 카드 t551 후속(지시 1항), 프리셋 서랍 강조", () => {
  it("position_preset_no 일치", () => {
    const cue = structuredCue(11, { position_preset_no: "2.41" });
    expect(cueReferencesPreset(cue, "2.41")).toBe(true);
  });

  it("color_preset_no 일치", () => {
    const cue = structuredCue(7, { color_preset_no: "4.21" });
    expect(cueReferencesPreset(cue, "4.21")).toBe(true);
  });

  it("effect_preset_no 일치", () => {
    const cue = structuredCue(14, { effect_preset_no: "2.61", effect_kind: "position" });
    expect(cueReferencesPreset(cue, "2.61")).toBe(true);
  });

  it("dimmer_preset 모드의 brightness.preset_no 일치", () => {
    const cue = structuredCue(7, {
      brightness: { mode: "dimmer_preset", value_percent: null, preset_no: "1.1" },
    });
    expect(cueReferencesPreset(cue, "1.1")).toBe(true);
  });

  it("dimmer_effect 모드의 brightness.preset_no 일치", () => {
    const cue = structuredCue(7, {
      brightness: { mode: "dimmer_effect", value_percent: null, preset_no: "1.21" },
    });
    expect(cueReferencesPreset(cue, "1.21")).toBe(true);
  });

  it("value 모드의 brightness.preset_no 는 무시한다(값 모드엔 의미 없는 자리)", () => {
    const cue = structuredCue(7, {
      brightness: { mode: "value", value_percent: 50, preset_no: "1.1" },
    });
    expect(cueReferencesPreset(cue, "1.1")).toBe(false);
  });

  it("아무 필드도 일치하지 않으면 false", () => {
    const cue = structuredCue(0, {});
    expect(cueReferencesPreset(cue, "2.41")).toBe(false);
  });
});

describe("presetPoolBandBadge — 카드 t551 후속(지시 2항), 번호대 미확인", () => {
  function section(overrides: Partial<BeatGridDrawerSection> = {}): BeatGridDrawerSection {
    return {
      pool_name: "Position",
      title: "위치 풀 2 — 위치·움직임(상대값)",
      pool_no: 2,
      entries: [],
      unread: false,
      bands_confirmed: true,
      ...overrides,
    };
  }

  it("bands_confirmed 가 false 면 배지를 단다", () => {
    expect(presetPoolBandBadge(section({ bands_confirmed: false }))).toBe("⚠ 번호대 미확인");
  });

  it("bands_confirmed 가 true 면 배지 없음", () => {
    expect(presetPoolBandBadge(section({ bands_confirmed: true }))).toBeNull();
  });
});

describe("pendingApprovalBadge — 카드 t577, REQ-LDBEAT-015(h-1), 승인 대기", () => {
  it("pending_preset_fields 가 비어 있으면 배지 없음", () => {
    expect(pendingApprovalBadge(structuredCue(3, { pending_preset_fields: [] }))).toBeNull();
  });

  it("pending_preset_fields 가 없는(옛 격자) 칸도 배지 없음", () => {
    expect(pendingApprovalBadge(structuredCue(3))).toBeNull();
  });

  it("pending_preset_fields 가 있으면 그 필드 이름을 담아 배지를 단다", () => {
    const badge = pendingApprovalBadge(
      structuredCue(3, { pending_preset_fields: ["효과 프리셋"] }),
    );
    expect(badge).toContain("승인 대기");
    expect(badge).toContain("효과 프리셋");
  });

  it("여러 필드가 승인 대기면 전부 담는다", () => {
    const badge = pendingApprovalBadge(
      structuredCue(3, { pending_preset_fields: ["효과 프리셋", "위치 프리셋"] }),
    );
    expect(badge).toContain("효과 프리셋");
    expect(badge).toContain("위치 프리셋");
  });
});

describe("isPendingSuggestionForTrack — 카드 t551 후속(지시 1항), AI 제안 점선 막대", () => {
  function suggestion(overrides: Partial<BeatGridPendingSuggestion> = {}): BeatGridPendingSuggestion {
    return {
      suggestion_id: "s-1",
      bar: 18,
      target: "MOVER-D",
      changes: {},
      rationale: "테스트",
      ...overrides,
    };
  }

  it("제안이 없으면 어느 트랙도 false", () => {
    expect(isPendingSuggestionForTrack(null, "MOVER-D")).toBe(false);
    expect(isPendingSuggestionForTrack(undefined, "MOVER-D")).toBe(false);
  });

  it("target 과 그룹 이름이 같으면 true", () => {
    expect(isPendingSuggestionForTrack(suggestion(), "MOVER-D")).toBe(true);
  });

  it("target 과 그룹 이름이 다르면 false", () => {
    expect(isPendingSuggestionForTrack(suggestion(), "MOVER-U")).toBe(false);
  });
});

/** 카드 t551 계속 — 직접 고르기(①) 드롭다운. mockup `ldbeat-runbook-
 * mockup-20261008.html` `opts()`의 그룹·값 그대로("이 곡 프리셋"/
 * "쇼에 이미 있는 프리셋"/"+ 새 프리셋"), `drawerSections`가 출처다. */
function drawerEntry(overrides: Partial<BeatGridDrawerEntry> = {}): BeatGridDrawerEntry {
  return {
    preset_no: "2.41",
    name: "LA Center",
    usage_count: 0,
    used_by: [],
    is_effect_band: false,
    ...overrides,
  };
}

function drawerSection(overrides: Partial<BeatGridDrawerSection> = {}): BeatGridDrawerSection {
  return {
    pool_name: "Position",
    title: "위치 풀 2 — 위치·움직임(상대값)",
    pool_no: 2,
    entries: [],
    unread: false,
    bands_confirmed: true,
    ...overrides,
  };
}

describe("formatDrawerEntryOptionLabel — 카드 t551 계속, mockup opts() 옵션 표시", () => {
  it("번호와 이름을 공백으로 잇는다", () => {
    expect(formatDrawerEntryOptionLabel(drawerEntry({ preset_no: "4.24", name: "LA Pink" }))).toBe(
      "4.24 LA Pink",
    );
  });
});

describe("splitDrawerSectionEntries — 카드 t551 계속, mockup 두 optgroup(이 곡/쇼 기존)", () => {
  it("섹션이 null 이면 둘 다 빈 배열(지어내지 않는다)", () => {
    expect(splitDrawerSectionEntries(null)).toEqual({ thisSong: [], showExisting: [] });
  });

  it("POOL_UNREAD(section.unread)면 둘 다 빈 배열", () => {
    expect(
      splitDrawerSectionEntries(drawerSection({ unread: true, entries: [drawerEntry()] })),
    ).toEqual({ thisSong: [], showExisting: [] });
  });

  it("usage_count > 0 은 이 곡 프리셋, 0 은 쇼에 이미 있는 프리셋", () => {
    const used = drawerEntry({ preset_no: "2.41", usage_count: 2 });
    const unused = drawerEntry({ preset_no: "2.42", usage_count: 0 });
    expect(splitDrawerSectionEntries(drawerSection({ entries: [used, unused] }))).toEqual({
      thisSong: [used],
      showExisting: [unused],
    });
  });

  it("entries 가 비어 있으면 둘 다 빈 배열", () => {
    expect(splitDrawerSectionEntries(drawerSection({ entries: [] }))).toEqual({
      thisSong: [],
      showExisting: [],
    });
  });
});

describe("findDrawerSection — 카드 t551 계속", () => {
  it("배열이 null 이면 null(아직 서랍을 안 받음)", () => {
    expect(findDrawerSection(null, "Position")).toBeNull();
  });

  it("풀 이름이 일치하는 섹션을 찾는다", () => {
    const position = drawerSection({ pool_name: "Position" });
    const color = drawerSection({ pool_name: "Color", title: "색 풀 4" });
    expect(findDrawerSection([position, color], "Color")).toBe(color);
  });

  it("일치하는 섹션이 없으면 null", () => {
    expect(findDrawerSection([drawerSection({ pool_name: "Position" })], "Dimmer")).toBeNull();
  });
});

describe("buildPositionPresetChanges/buildColorPresetChanges/buildBrightnessPresetChanges — 카드 t551 계속, apply_beat_grid_edit 와 바이트 동일 모양", () => {
  it("위치 프리셋 changes", () => {
    expect(buildPositionPresetChanges("2.41")).toEqual({ position_preset_no: "2.41" });
  });

  it("색 프리셋 changes", () => {
    expect(buildColorPresetChanges("4.24")).toEqual({ color_preset_no: "4.24" });
  });

  it("디머 프리셋 changes — 밝기 단일모드(REQ-LDBEAT-015(c))", () => {
    expect(buildBrightnessPresetChanges("1.1")).toEqual({
      brightness: { mode: "dimmer_preset", value_percent: null, preset_no: "1.1" },
    });
  });
});

describe("NEW_PRESET_OPTION_VALUE — 카드 t551 계속, mockup opts() \"__new\" 리터럴", () => {
  it("mockup 과 같은 리터럴 값", () => {
    expect(NEW_PRESET_OPTION_VALUE).toBe("__new");
  });
});

// 카드 t589 — 「＋ 새 프리셋 만들기」 창. 콘솔 이름 검증 helper + 순수
// 표시 부품(`NewPresetDialog`)을 renderToStaticMarkup으로 본다(jsdom
// 없음 — 클릭 이벤트는 시뮬레이션하지 않는다, 위 파일 바운드 그대로).
describe("isValidConsoleLabel — 카드 t589, 서버 영문 규칙의 화면 쪽 즉시 확인", () => {
  it("영문·숫자·공백은 통과", () => {
    expect(isValidConsoleLabel("LA Wave 2")).toBe(true);
  });

  it("빈 문자열/공백만은 거절", () => {
    expect(isValidConsoleLabel("")).toBe(false);
    expect(isValidConsoleLabel("   ")).toBe(false);
  });

  it("한글이 섞이면 거절", () => {
    expect(isValidConsoleLabel("라이트 Wave")).toBe(false);
  });
});

describe("NewPresetDialog — 카드 t589, 「＋ 새 프리셋 만들기」 순수 표시", () => {
  it("onNewPresetRequest 가 없으면(enabled=false) 안내문만 뜨고 입력·버튼이 없다", () => {
    const html = renderToStaticMarkup(
      <NewPresetDialog
        enabled={false}
        label=""
        description=""
        onLabelChange={() => {}}
        onDescriptionChange={() => {}}
        onCreate={() => {}}
        onCancel={() => {}}
      />,
    );
    expect(html).toContain("아직 배선되지 않았습니다");
    expect(html).not.toContain("beat-grid-new-preset-dialog");
  });

  it("enabled=true 면 두 입력과 만들기/취소 버튼이 뜬다", () => {
    const html = renderToStaticMarkup(
      <NewPresetDialog
        enabled
        label=""
        description=""
        onLabelChange={() => {}}
        onDescriptionChange={() => {}}
        onCreate={() => {}}
        onCancel={() => {}}
      />,
    );
    expect(html).toContain("beat-grid-new-preset-dialog");
    expect(html).toContain("콘솔 이름(영문·숫자)");
    expect(html).toContain("설명(한국어)");
    expect(html).toContain("만들기");
    expect(html).toContain("취소");
  });

  it("라벨·설명이 둘 다 유효하지 않으면 만들기가 disabled", () => {
    const html = renderToStaticMarkup(
      <NewPresetDialog
        enabled
        label=""
        description=""
        onLabelChange={() => {}}
        onDescriptionChange={() => {}}
        onCreate={() => {}}
        onCancel={() => {}}
      />,
    );
    expect(html).toMatch(/<button[^>]*disabled[^>]*>\s*만들기/);
  });

  it("라벨·설명이 둘 다 유효하면 만들기가 활성", () => {
    const html = renderToStaticMarkup(
      <NewPresetDialog
        enabled
        label="LA Wave"
        description="따뜻한 흰색"
        onLabelChange={() => {}}
        onDescriptionChange={() => {}}
        onCreate={() => {}}
        onCancel={() => {}}
      />,
    );
    expect(html).not.toMatch(/<button[^>]*disabled[^>]*>\s*만들기/);
  });

  it("비-ASCII 라벨이면 즉시 경고 문구가 뜨고 만들기는 여전히 disabled", () => {
    const html = renderToStaticMarkup(
      <NewPresetDialog
        enabled
        label="라이트"
        description="설명"
        onLabelChange={() => {}}
        onDescriptionChange={() => {}}
        onCreate={() => {}}
        onCancel={() => {}}
      />,
    );
    expect(html).toContain("한글/비-ASCII 문자는 받지 않습니다");
    expect(html).toMatch(/<button[^>]*disabled[^>]*>\s*만들기/);
  });
});

/** 카드 t551 계속(코디네이터 지시 2026-10-11, 조건 1 — "lead 가 옵션 A를
 * 골랐다") — 효과(움직임)·디머 "효과" 드롭다운은 같은 drawerSections 풀
 * 안에서 `is_effect_band`(서버가 `preset_pools.yaml` 번호대로 판정)로만
 * 골라낸다. 번호대 리터럴은 이 시험에도 없다 — fixture가 `is_effect_band`
 * 를 직접 지정한다(서버가 이미 판정을 끝낸 값을 그대로 받는다는 전제). */
describe("splitDrawerSectionEffectEntries — 카드 t551 계속, is_effect_band 로 효과만 골라내기", () => {
  it("섹션이 null 이면 둘 다 빈 배열", () => {
    expect(splitDrawerSectionEffectEntries(null)).toEqual({ thisSong: [], showExisting: [] });
  });

  it("POOL_UNREAD 면 둘 다 빈 배열", () => {
    expect(
      splitDrawerSectionEffectEntries(
        drawerSection({ unread: true, entries: [drawerEntry({ is_effect_band: true })] }),
      ),
    ).toEqual({ thisSong: [], showExisting: [] });
  });

  it("is_effect_band=false 인 항목(기본 프리셋)은 제외한다", () => {
    const base = drawerEntry({ preset_no: "2.41", is_effect_band: false, usage_count: 3 });
    expect(splitDrawerSectionEffectEntries(drawerSection({ entries: [base] }))).toEqual({
      thisSong: [],
      showExisting: [],
    });
  });

  it("is_effect_band=true 인 항목만 골라, 그 안에서 다시 이 곡/쇼 기존으로 가른다", () => {
    const effectUsed = drawerEntry({ preset_no: "2.61", is_effect_band: true, usage_count: 1 });
    const effectUnused = drawerEntry({ preset_no: "2.62", is_effect_band: true, usage_count: 0 });
    const base = drawerEntry({ preset_no: "2.41", is_effect_band: false, usage_count: 5 });
    expect(
      splitDrawerSectionEffectEntries(drawerSection({ entries: [effectUsed, effectUnused, base] })),
    ).toEqual({ thisSong: [effectUsed], showExisting: [effectUnused] });
  });
});

describe("buildEffectPresetChanges/buildBrightnessDimmerEffectChanges — 카드 t551 계속, apply_beat_grid_edit 와 바이트 동일 모양", () => {
  it("효과(움직임) changes — 무빙 전용 effect_kind=\"position\"", () => {
    expect(buildEffectPresetChanges("2.61")).toEqual({
      effect_preset_no: "2.61",
      effect_kind: "position",
    });
  });

  it("디머 효과 changes — 밝기 단일모드(REQ-LDBEAT-015(c))", () => {
    expect(buildBrightnessDimmerEffectChanges("1.21")).toEqual({
      brightness: { mode: "dimmer_effect", value_percent: null, preset_no: "1.21" },
    });
  });
});

// 카드 t557 — 효과 드롭다운이 무빙(위치 효과) 전용이던 것을 필드별로 나눈다.
// 정본 시안: 색 효과는 색 드롭다운(「(쇼·효과)」), 움직임 효과는 무빙의
// 「움직임 효과」 드롭다운, 디머 효과는 밝기 「디머 효과」 모드.
describe("presetPickChanges — 고른 항목의 풀·효과 번호대로 저장 필드를 정한다(카드 t557)", () => {
  const color = drawerSection({
    pool_name: "Color",
    pool_no: 4,
    entries: [
      drawerEntry({ preset_no: "4.24", name: "LA Pink", is_effect_band: false }),
      drawerEntry({ preset_no: "4.41", name: "LA Wave CM", is_effect_band: true }),
    ],
  });
  const position = drawerSection({
    pool_name: "Position",
    entries: [
      drawerEntry({ preset_no: "2.41", name: "LA Floor", is_effect_band: false }),
      drawerEntry({ preset_no: "2.63", name: "LA Sweep 4", is_effect_band: true }),
    ],
  });

  it("재현: 색 풀의 효과 번호대 항목은 색 효과(effect_kind color)로 — 예전에는 color_preset_no 로 나갔다", () => {
    expect(presetPickChanges(color, "Color", "4.41")).toEqual({ effect_preset_no: "4.41", effect_kind: "color" });
  });
  it("색 풀의 기본 항목은 그대로 color_preset_no", () => {
    expect(presetPickChanges(color, "Color", "4.24")).toEqual({ color_preset_no: "4.24" });
  });
  it("위치 풀의 효과 항목은 위치 효과, 기본 항목은 position_preset_no", () => {
    expect(presetPickChanges(position, "Position", "2.63")).toEqual({ effect_preset_no: "2.63", effect_kind: "position" });
    expect(presetPickChanges(position, "Position", "2.41")).toEqual({ position_preset_no: "2.41" });
  });
  it("서랍에 없는 번호·서랍을 아직 못 받음은 기본 필드(효과로 지어내지 않음)", () => {
    expect(presetPickChanges(color, "Color", "4.99")).toEqual({ color_preset_no: "4.99" });
    expect(presetPickChanges(null, "Color", "4.41")).toEqual({ color_preset_no: "4.41" });
  });
  it("buildEffectPresetChanges 는 종류를 받는다(기본값은 예전과 같은 position)", () => {
    expect(buildEffectPresetChanges("4.41", "color")).toEqual({ effect_preset_no: "4.41", effect_kind: "color" });
    expect(buildEffectPresetChanges("2.61")).toEqual({ effect_preset_no: "2.61", effect_kind: "position" });
  });
  it("위치·색 드롭다운에서는 효과 항목에 「· 효과」를 붙인다(시안 「(쇼·효과)」)", () => {
    const fx = drawerEntry({ preset_no: "4.41", name: "LA Wave CM", is_effect_band: true });
    expect(formatDrawerEntryOptionLabel(fx, { markEffect: true })).toBe("4.41 LA Wave CM · 효과");
    expect(formatDrawerEntryOptionLabel(fx)).toBe("4.41 LA Wave CM");
  });
  it("편집 칸의 위치·색·효과 「적용」이 모두 presetPickChanges 를 거친다", () => {
    const source = readFileSync(new URL("./BeatGrid.tsx", import.meta.url), "utf-8");
    expect(source).not.toMatch(/changes: buildColorPresetChanges\(/);
    expect(source).not.toMatch(/changes: buildPositionPresetChanges\(/);
    expect(source).not.toMatch(/changes: buildEffectPresetChanges\(effectPresetDraft\)/);
    expect((source.match(/changes: presetPickChanges\(/g) ?? []).length).toBe(3);
  });
});
