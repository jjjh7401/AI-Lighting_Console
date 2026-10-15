// 서버가 붙이는 구간 색·에너지·강조(★) 값(#726)을 개요 모델이 우선 쓰는지 시험한다.
// 순수 함수만 직접 부른다(songOverviewModel.test.ts 와 같은 방식).
import { describe, expect, it } from "vitest";

import { buildSongOverview, type SongOverviewSectionInput } from "./songOverviewModel";

const BASE: SongOverviewSectionInput[] = [
  { label: "인트로", start_ms: 0, bar_start: 0, d_level: 1, accents: [], palette_primary_hex: "#111111" },
  { label: "벌스", start_ms: 8000, bar_start: 4, d_level: 2, accents: [] },
];

const FALLBACK = { start: 0, end: 7 };

describe("구간 색 — 서버 color 가 palette_primary_hex 보다 우선", () => {
  it("color 가 있으면 그 색을 쓴다", () => {
    const model = buildSongOverview({
      sections: [{ ...BASE[0], color: "#5b6b8a" }, BASE[1]],
      barCount: 8,
      secondsPerBar: 2,
      fallbackRange: FALLBACK,
    });
    expect(model.sections[0].hex).toBe("#5b6b8a");
  });

  it("color 가 없으면 palette_primary_hex, 둘 다 없으면 null(기본색은 화면이 정한다)", () => {
    const model = buildSongOverview({ sections: BASE, barCount: 8, secondsPerBar: 2, fallbackRange: FALLBACK });
    expect(model.sections[0].hex).toBe("#111111");
    expect(model.sections[1].hex).toBeNull();
  });
});

describe("에너지 — 서버 energy(0~1)를 쓰고, 없으면 d_level 환산, 둘 다 없으면 null", () => {
  it("energy 가 있으면 그 값을 0~1 안에서 쓴다", () => {
    const model = buildSongOverview({
      sections: [
        { ...BASE[0], energy: 0.75 },
        { ...BASE[1], energy: 1.5 },
      ],
      barCount: 8,
      secondsPerBar: 2,
      fallbackRange: FALLBACK,
    });
    expect(model.sections[0].energy).toBe(0.75);
    expect(model.sections[1].energy).toBe(1);
  });

  it("energy 가 없으면 d_level 로 환산한다(기존 동작)", () => {
    const model = buildSongOverview({ sections: BASE, barCount: 8, secondsPerBar: 2, fallbackRange: FALLBACK });
    expect(model.sections[0].energy).toBeCloseTo(1 / 5);
    expect(model.sections[1].energy).toBeCloseTo(2 / 5);
  });

  it("둘 다 없으면 선을 지어내지 않는다(null)", () => {
    const bare: SongOverviewSectionInput[] = [{ label: "A", start_ms: 0, bar_start: 0 }];
    const model = buildSongOverview({ sections: bare, barCount: 4, secondsPerBar: 2, fallbackRange: { start: 0, end: 3 } });
    expect(model.sections[0].energy).toBeNull();
  });
});

describe("강조(★) — 서버 accent_bars 가 있으면 그 마디들, 곡 밖 마디는 버린다", () => {
  it("accent_bars 의 마디를 쓴다", () => {
    const model = buildSongOverview({
      sections: BASE,
      barCount: 8,
      secondsPerBar: 2,
      fallbackRange: FALLBACK,
      accentBars: [{ bar: 4 }, { bar: 1 }, { bar: 99 }],
    });
    expect(model.accentBars).toEqual([1, 4]);
  });

  it("accent_bars 가 없으면 구간 문구(accents)의 시작 마디를 쓴다(기존 동작)", () => {
    const withAccent: SongOverviewSectionInput[] = [{ ...BASE[0], accents: ["climax accent"] }, BASE[1]];
    const model = buildSongOverview({ sections: withAccent, barCount: 8, secondsPerBar: 2, fallbackRange: FALLBACK });
    expect(model.accentBars).toEqual([0]);
  });
});
