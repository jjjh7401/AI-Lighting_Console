// LOVE ATTACK 시드처럼 필드가 빠진 타임라인을 넣어도 런북 화면이 죽지 않아야
// 한다. 빠진 것은 구간의 팔레트·효과·강조·그룹 값과 최상위 마디·길이 값이다.
// 이전에는 `section.palette[0]` 과 `section.fx.length` 를 읽다가 TypeError 가
// 나서 #root 가 통째로 비었다(콘솔: reading '0' · reading 'length').
//
// 픽스처는 실제 재질의 대기 페이로드(requeryTimeline.t490.json)에서 그 필드만
// 걷어 낸 것이다. 나머지는 서버가 실제로 내는 모양 그대로다.
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { SongTimelineView } from "../protocol";
import { CueSheetTimeline, EMPTY_CELL } from "./CueSheetTimeline";
import { RunbookMode } from "./RunbookMode";
import { SongTimeline } from "./SongTimeline";
import { buildAnalysisSummary } from "./analysisSummary";
import { glanceView } from "./conceptGlance";
import { grammarRows, sectionHex } from "./runbookM7";
import REQUERY from "./__fixtures__/requeryTimeline.t490.json";

/** 구간에서 빠지는 값 — LOVE ATTACK 시드와 같은 모양. */
const SECTION_KEYS_MISSING = [
  "palette",
  "palette_primary",
  "palette_secondary",
  "palette_primary_hex",
  "palette_secondary_hex",
  "fx",
  "accents",
  "intensity",
  "fixture_groups",
];
/** 최상위에서 빠지는 값 — 마디 수·마디 길이·곡 길이. */
const HEADER_KEYS_MISSING = ["bar_count", "seconds_per_bar", "total_duration_ms"];
/** 배열·객체 값이 통째로 빠진 경우 — 가장 나쁜 모양. */
const COLLECTION_KEYS_MISSING = [
  "director_decisions",
  "lint",
  "unresolved",
  "disabled",
  "warnings",
  "readback",
  "palette_legend",
  "concept_report",
];

function dropKeys<T extends object>(value: T, keys: readonly string[]): T {
  const copy: Record<string, unknown> = { ...(value as Record<string, unknown>) };
  for (const key of keys) delete copy[key];
  return copy as T;
}

function loveAttackShaped(source: SongTimelineView): SongTimelineView {
  return {
    ...dropKeys(source, HEADER_KEYS_MISSING),
    sections: source.sections.map((section) => dropKeys(section, SECTION_KEYS_MISSING)),
  };
}

const SOURCE = REQUERY as unknown as SongTimelineView;
const LOVE_ATTACK_SHAPED = loveAttackShaped(SOURCE);
const EVERYTHING_MISSING = dropKeys(LOVE_ATTACK_SHAPED, COLLECTION_KEYS_MISSING);
const CUE_MONITOR = { executors: [], history: [], lastSyncAt: null, stale: false };

describe("LOVE ATTACK 모양 픽스처 — 전제", () => {
  it("구간의 색·효과·강조 값과 최상위 마디·길이 값이 실제로 없다", () => {
    const section = LOVE_ATTACK_SHAPED.sections[0];
    expect(section).not.toHaveProperty("palette");
    expect(section).not.toHaveProperty("fx");
    expect(section).not.toHaveProperty("accents");
    expect(LOVE_ATTACK_SHAPED).not.toHaveProperty("bar_count");
    expect(LOVE_ATTACK_SHAPED).not.toHaveProperty("total_duration_ms");
    expect(LOVE_ATTACK_SHAPED.sections.length).toBeGreaterThan(0);
  });
});

describe("빠진 값이 있어도 화면이 그려진다", () => {
  it("런북 화면 전체가 죽지 않고 구간 이름과 「—」를 낸다", () => {
    const html = renderToStaticMarkup(
      <RunbookMode cueMonitor={CUE_MONITOR} timeline={LOVE_ATTACK_SHAPED} />,
    );
    expect(html).toContain(LOVE_ATTACK_SHAPED.sections[0].label);
    expect(html).toContain(EMPTY_CELL);
    expect(html).not.toContain("undefined");
    expect(html).not.toContain("NaN");
  });

  it("CUE SHEET 가 죽지 않고 구간 이름을 낸다", () => {
    const html = renderToStaticMarkup(<CueSheetTimeline timeline={LOVE_ATTACK_SHAPED} />);
    expect(html).toContain(LOVE_ATTACK_SHAPED.sections[0].label);
  });

  it("곡 타임라인 카드가 죽지 않고, 효과가 없는 칸은 「정적」이 아니라 「—」다", () => {
    const html = renderToStaticMarkup(
      <SongTimeline timeline={LOVE_ATTACK_SHAPED} cueMonitor={CUE_MONITOR} />,
    );
    expect(html).toContain("<dt>FX</dt><dd>—</dd>");
  });

  it("배열·객체 값까지 통째로 빠져도 런북 화면이 그려진다", () => {
    const html = renderToStaticMarkup(
      <RunbookMode cueMonitor={CUE_MONITOR} timeline={EVERYTHING_MISSING} />,
    );
    expect(html).toContain(EVERYTHING_MISSING.sections[0].label);
  });
});

describe("빠진 값을 읽는 함수들도 죽지 않는다", () => {
  const section = LOVE_ATTACK_SHAPED.sections[0];

  it("수정 요청 표 한 줄은 색과 효과를 「—」로 낸다", () => {
    const row = grammarRows(LOVE_ATTACK_SHAPED.sections)[0];
    expect(row.color).toBe("—");
    expect(row.effect).toBe("—");
  });

  it("색 값이 없으면 범례가 있어도 색을 지어내지 않는다", () => {
    expect(sectionHex(section, [{ id: "P1", name: "red", color: "#f00" }])).toBeNull();
  });

  it("분석 요약은 효과 줄을 지어내지 않는다", () => {
    const labels = buildAnalysisSummary(LOVE_ATTACK_SHAPED).map((line) => line.label);
    expect(labels).not.toContain("이펙트");
  });

  it("구간 목록이 없으면 한눈에 구획은 사유와 함께 none 이다", () => {
    const withGlance = {
      ...SOURCE,
      concept_report: {
        ...SOURCE.concept_report,
        available: true,
        glance: {
          available: true,
          rule: "R",
          stages: [{ stage: "S", positions: [0], reason: null }],
        },
      },
    } as unknown as SongTimelineView;
    const view = glanceView({ ...withGlance, sections: undefined } as unknown as SongTimelineView);
    expect(view.status).toBe("none");
  });
});
