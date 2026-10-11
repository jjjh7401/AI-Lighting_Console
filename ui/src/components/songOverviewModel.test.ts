// 곡 전체 지도 데이터 모양 시험 (SPEC-LDBEAT-001 M9 step 1, 카드 t559,
// REQ-LDBEAT-018 / AC-LDBEAT-018).
//
// 이 프로젝트는 jsdom 시험대가 없다(BeatGrid.test.tsx 같은 메모) — 순수
// 함수만 직접 부른다. 두 곡 fixture 는 일부러 지어낸 값이다: 실제 곡의
// 마디 번호를 코드에 묶지 않는다는 것(AC-LDBEAT-018(a))을 "서로 다른 두
// 곡이 서로 다른 강조 마디를 보여 준다"로 확인한다.
import { describe, expect, it } from "vitest";

import {
  OVERVIEW_ZOOM_LEVELS,
  buildSongOverview,
  overviewBarAtFraction,
  overviewVisibleWindow,
  pxPerBarForZoom,
  type SongOverviewSectionInput,
} from "./songOverviewModel";

const SONG_A: SongOverviewSectionInput[] = [
  { label: "인트로", start_ms: 0, bar_start: 0, d_level: 1, accents: [] },
  { label: "벌스", start_ms: 8000, bar_start: 4, d_level: 2, accents: [] },
  { label: "후렴", start_ms: 24000, bar_start: 12, d_level: 5, accents: ["climax accent"] },
  { label: "끝", start_ms: 40000, bar_start: 20, d_level: 1, accents: [] },
];

const SONG_B: SongOverviewSectionInput[] = [
  { label: "A", start_ms: 0, d_level: 3, accents: ["section arc"] },
  { label: "B", start_ms: 6000, d_level: 4, accents: [] },
  { label: "C", start_ms: 12000, d_level: 5, accents: ["climax accent"] },
];

describe("buildSongOverview — 곡 데이터에서만 읽는다", () => {
  it("총 마디 수는 곡의 bar_count 를 그대로 쓴다", () => {
    const model = buildSongOverview({ sections: SONG_A, barCount: 30, secondsPerBar: 2, fallbackRange: { start: 0, end: 9 } });
    expect(model.totalBars).toBe(30);
  });

  it("bar_count 가 없으면 격자의 표시 범위로 떨어진다(지어내지 않음)", () => {
    const model = buildSongOverview({ sections: [], barCount: undefined, secondsPerBar: null, fallbackRange: { start: 0, end: 25 } });
    expect(model.totalBars).toBe(26);
    expect(model.sections).toEqual([]);
    expect(model.accentBars).toEqual([]);
  });

  it("구간 시작은 bar_start 가 있으면 그것을, 없으면 start_ms÷마디 길이를 쓴다", () => {
    const a = buildSongOverview({ sections: SONG_A, barCount: 24, secondsPerBar: 99, fallbackRange: { start: 0, end: 9 } });
    expect(a.sections.map((s) => [s.startBar, s.endBar])).toEqual([
      [0, 4],
      [4, 12],
      [12, 20],
      [20, 24],
    ]);
    const b = buildSongOverview({ sections: SONG_B, barCount: 9, secondsPerBar: 2, fallbackRange: { start: 0, end: 9 } });
    expect(b.sections.map((s) => [s.startBar, s.endBar])).toEqual([
      [0, 3],
      [3, 6],
      [6, 9],
    ]);
  });

  it("bar_start 도 마디 길이도 없는 구간은 위치를 지어내지 않고 뺀다", () => {
    const model = buildSongOverview({
      sections: [{ label: "X", start_ms: 1000, d_level: 2, accents: [] }],
      barCount: 10,
      secondsPerBar: null,
      fallbackRange: { start: 0, end: 9 },
    });
    expect(model.sections).toEqual([]);
  });

  it("에너지는 d_level(1~5)을 0~1로 옮기고, 값이 없으면 null", () => {
    const model = buildSongOverview({
      sections: [
        { label: "a", start_ms: 0, bar_start: 0, d_level: 5, accents: [] },
        { label: "b", start_ms: 0, bar_start: 2, accents: [] },
      ],
      barCount: 4,
      secondsPerBar: 2,
      fallbackRange: { start: 0, end: 3 },
    });
    expect(model.sections[0].energy).toBe(1);
    expect(model.sections[1].energy).toBeNull();
  });

  it("강조(★)는 accents 가 있는 구간의 시작 마디 — 두 곡이 서로 다른 번호를 낸다", () => {
    const a = buildSongOverview({ sections: SONG_A, barCount: 24, secondsPerBar: 2, fallbackRange: { start: 0, end: 9 } });
    const b = buildSongOverview({ sections: SONG_B, barCount: 9, secondsPerBar: 2, fallbackRange: { start: 0, end: 9 } });
    expect(a.accentBars).toEqual([12]);
    expect(b.accentBars).toEqual([0, 6]);
    expect(a.accentBars).not.toEqual(b.accentBars);
  });
});

describe("확대 3단계 — 곡 전체 / 16마디 / 8마디", () => {
  it("단계는 정확히 셋, 시안 순서 그대로", () => {
    expect(OVERVIEW_ZOOM_LEVELS.map((z) => z.label)).toEqual(["곡 전체", "16마디", "8마디"]);
  });

  it("세 단계가 서로 다른 가로 스케일을 낸다", () => {
    const widths = OVERVIEW_ZOOM_LEVELS.map((z) => pxPerBarForZoom(z.id, 960, 80));
    expect(widths).toEqual([12, 60, 120]);
    expect(new Set(widths).size).toBe(3);
  });

  it("곡 전체는 최소 폭 아래로 내려가지 않는다", () => {
    expect(pxPerBarForZoom("song", 300, 200)).toBe(6);
  });

  it("보이는 폭을 아직 모르면(0) 기존 고정값으로 떨어진다", () => {
    expect(pxPerBarForZoom("bars16", 0, 80, 42)).toBe(42);
  });
});

describe("지금 보는 범위 창 · 클릭 점프", () => {
  it("스크롤 위치와 보이는 폭으로 범위 창을 계산한다", () => {
    expect(overviewVisibleWindow({ scrollLeft: 120, visibleWidth: 480, pxPerBar: 60, rangeStart: 0, totalBars: 80 })).toEqual({
      startBar: 2,
      endBar: 10,
    });
  });

  it("범위 창은 곡 끝을 넘지 않는다", () => {
    expect(overviewVisibleWindow({ scrollLeft: 0, visibleWidth: 2000, pxPerBar: 10, rangeStart: 0, totalBars: 50 })).toEqual({
      startBar: 0,
      endBar: 50,
    });
  });

  it("지도 위 가로 비율 → 마디(0..총마디-1 로 클램프)", () => {
    expect(overviewBarAtFraction(0, 80)).toBe(0);
    expect(overviewBarAtFraction(0.5, 80)).toBe(40);
    expect(overviewBarAtFraction(1, 80)).toBe(79);
    expect(overviewBarAtFraction(-0.2, 80)).toBe(0);
  });
});
