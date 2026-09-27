// t458 — SPEC-LDDESIGN-001 M7 3차. 서버 #503(t455·t456)이 내보내는 데이터로
// t454 가 「데이터 없음」으로 둔 칸을 채운다. 데이터는 서버 실출력 사본
// (`runbookServerPayload.json` — `.moai/reports/t458/measure_payload.py`).
// 원칙: 짝짓기가 안 되면(row_pairing.available=false) t454 표기로 돌아간다.
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { SongTimelineConceptReport, SongTimelineView } from "../protocol";
import { CueSheetTimeline } from "./CueSheetTimeline";
import serverPayload from "./runbookServerPayload.json";
import {
  NO_DATA,
  NO_PUBLIC_EVIDENCE,
  conceptBySection,
  conceptCells,
  sectionHex,
  timelineDots,
} from "./runbookM7";

const TIMELINE = serverPayload as unknown as SongTimelineView;
const REPORT = TIMELINE.concept_report as SongTimelineConceptReport;
const SECTIONS = TIMELINE.sections;

function unpaired(report: SongTimelineConceptReport): SongTimelineConceptReport {
  return {
    ...report,
    row_pairing: { available: false, reason: "컨셉 구간 행 8개와 화면 구간 7개가 짝이 안 맞는다" },
    rows: report.rows?.map((row) => ({ ...row, screen_position: null })),
  };
}

describe("서버 실출력 전제 — 이 파일이 재는 데이터가 맞는가", () => {
  it("20행이 8구간에 짝지어져 있다", () => {
    expect(REPORT.row_pairing).toEqual({ available: true, reason: null });
    expect(REPORT.rows).toHaveLength(20);
    expect(SECTIONS).toHaveLength(8);
  });
});

describe("REQ-082 회차·Trigger·MIB·근거 등급 — rows 를 screen_position 으로 모은다", () => {
  const concept = conceptBySection(REPORT, SECTIONS.length);

  it("회차는 그 구간 section 행의 occurrence 다", () => {
    expect(concept?.map((c) => c.occurrence)).toEqual([1, 1, 1, 2, 2, 1, 1, 1]);
  });

  it("Trigger 는 구간 안 phrase 행에서 온다 — Pre-Chorus 는 앞 구간(Verse 1)에 모인다", () => {
    expect(conceptCells(concept![1], SECTIONS[1]).trigger).toBe("빌드업 시작");
    expect(conceptCells(concept![0], SECTIONS[0]).trigger).toBe("보컬 시작");
  });

  it("MIB 는 3상태 기호로 보인다 — 없는 구간은 「—」", () => {
    expect(conceptCells(concept![0], SECTIONS[0]).mib).toBe("◐ dark");
    expect(conceptCells(concept![6], SECTIONS[6]).mib).toBe("◇ mark");
    expect(conceptCells(concept![1], SECTIONS[1]).mib).toBe("—");
  });

  it("근거 등급이 null 이면 「[공개 근거 없음]」, 값이 있으면 그 등급(REQ-072)", () => {
    expect(conceptCells(concept![0], SECTIONS[0]).evidence).toBe(NO_PUBLIC_EVIDENCE);
    expect(conceptCells({ ...concept![0], evidence: "verified" }, SECTIONS[0]).evidence).toBe(
      "verified",
    );
  });

  it("짝짓기가 안 되면 t454 표기로 돌아간다 — 회차·Trigger·근거 등급은 데이터 없음, MIB 는 bool", () => {
    expect(conceptBySection(unpaired(REPORT), SECTIONS.length)).toBeNull();
    expect(conceptBySection({ available: false, reason: "x" }, 8)).toBeNull();
    expect(conceptBySection(undefined, 8)).toBeNull();
    const cells = conceptCells(null, { ...SECTIONS[0], mib: true });
    expect(cells).toEqual({
      occurrence: NO_DATA,
      trigger: NO_DATA,
      mib: "사전이동 있음",
      evidence: NO_DATA,
      nodata: true,
    });
  });
});

describe("REQ-081 원샷·Mark 점 줄", () => {
  it("원샷 3개 + Mark 1개, 구간 이름은 행 section 이 아니라 화면 구간 label", () => {
    const dots = timelineDots(REPORT, SECTIONS, 165_000) ?? [];
    expect(dots.map((d) => [d.kind, d.label])).toEqual([
      ["one_shot", "White hit"],
      ["one_shot", "White hit"],
      ["one_shot", "Blinder hit"],
      ["mark", "Mark"],
    ]);
    expect(dots[2].title).toContain("Chorus 3");
    expect(dots.some((d) => d.title.includes("Final Chorus"))).toBe(false);
  });

  it("점 위치는 행 ts(초)를 곡 길이에 대한 비율로 둔다", () => {
    const dots = timelineDots(REPORT, SECTIONS, 160_000) ?? [];
    expect(dots[0].leftPct).toBeCloseTo((40_000 / 160_000) * 100);
  });

  it("짝짓기가 안 되면 점을 그리지 않는다", () => {
    expect(timelineDots(unpaired(REPORT), SECTIONS, 160_000)).toBeNull();
  });
});

describe("REQ-081 블록 실색 — 서버 HEX 먼저, 없으면 범례, 그것도 없으면 중립색", () => {
  it("HEX 가 있으면 그 색, null 이면 null(호출자가 중립색)", () => {
    expect(SECTIONS.map((s) => sectionHex(s, []))).toEqual([
      "#0D33FF",
      "#0D33FF",
      "#FFBF66",
      null,
      null,
      "#8C59FF",
      "#00E6FF",
      null,
    ]);
  });

  it("HEX 가 없는 옛 페이로드는 범례로 찾는다", () => {
    const old = { ...SECTIONS[0], palette_primary_hex: undefined, palette_primary: "P4 핫핑크" };
    expect(sectionHex(old, [{ id: "P4", name: "핫핑크", color: "#FF3C9E" }])).toBe("#FF3C9E");
  });
});

describe("화면 — 서버 실출력으로 그린 CueSheetTimeline", () => {
  const html = renderToStaticMarkup(<CueSheetTimeline timeline={TIMELINE} />);

  it("블록에 서버 HEX 가 칠해지고, 해석 못 한 구간은 중립색이다", () => {
    expect(html).toContain("#0D33FF");
    expect(html).toContain("#8C59FF");
    expect(html).toContain("#4A5568");
  });

  it("MIB 기호·Trigger·근거 등급 마커가 시트에 보인다", () => {
    expect(html).toContain("◐ dark");
    expect(html).toContain("◇ mark");
    expect(html).toContain("빌드업 시작");
    expect(html).toContain(NO_PUBLIC_EVIDENCE);
  });

  it("점 줄이 그려지고, 범례의 「원샷·Mark 점 줄 · 데이터 없음」은 사라진다", () => {
    expect(html).toContain("cst-dot");
    expect(html).not.toContain(`원샷·Mark 점 줄 · ${NO_DATA}`);
  });

  it("Track 예외 칸만 아직 데이터 없음이다(이 카드 범위 밖)", () => {
    // 행 8개 × 1칸
    expect(html.match(new RegExp(`>${NO_DATA}<`, "g"))?.length).toBe(8);
  });

  it("짝짓기가 안 되면 t454 화면 그대로 — 4칸 데이터 없음, 점 줄 없음", () => {
    const fallback = renderToStaticMarkup(
      <CueSheetTimeline timeline={{ ...TIMELINE, concept_report: unpaired(REPORT) }} />,
    );
    expect(fallback.match(new RegExp(`>${NO_DATA}<`, "g"))?.length).toBe(8 * 4);
    expect(fallback).not.toContain("cst-dot");
    expect(fallback).toContain(`원샷·Mark 점 줄 · ${NO_DATA}`);
  });
});
