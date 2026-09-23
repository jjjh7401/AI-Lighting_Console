// t454 — SPEC-LDDESIGN-001 M7 2차(REQ-082·084·079/080/097/098·081).
// 원칙 하나: 원천이 있는 칸만 채우고, 없는 칸은 「데이터 없음」이다 —
// 지어낸 값이 화면에 한 칸이라도 나오면 이 파일이 잡아야 한다.
import { readFileSync } from "node:fs";

import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { SongTimelineConceptReport, SongTimelineSection } from "../protocol";
import { CUE_SHEET_EXAMPLE } from "./cueSheetExample";
import { ConceptPanel } from "./ConceptPanel";
import { RunbookGateBar } from "./RunbookGateBar";
import {
  NO_DATA,
  gateRows,
  gateTally,
  grammarRows,
  intensityTrend,
  mibCellText,
} from "./runbookM7";

const REPORT: SongTimelineConceptReport = {
  available: true,
  gates: {
    "G1 어휘 닫힘": { passed: true, detail: "구간·트리거·원샷 전부 문서 어휘" },
    "G7 후렴 주색 동일": { passed: false, detail: "위반 2건" },
    "G10 상대 감소 겹침 없음": { passed: null, detail: "절 밝기 [45, 38](2개 이하 — n/a)" },
  },
  mib: [null, { status: "dark" }],
  lint_finding_count: 27,
  lint_disabled_rule_count: 2,
  energy_report_count: 20,
};

describe("REQ-084 GATE — 원천은 concept_report.gates 뿐이다", () => {
  it("passed 세 값을 통과·실패·해당없음으로 센다", () => {
    expect(gateTally(REPORT)).toEqual({ pass: 1, fail: 1, na: 1 });
  });

  it("리포트가 없거나 available:false 면 개수를 지어내지 않는다", () => {
    expect(gateTally(undefined)).toBeNull();
    expect(gateTally({ available: false, reason: "BPM이 선언되지 않았다" })).toBeNull();
  });

  it("상세 행은 서버 detail 문자열을 그대로 싣는다", () => {
    expect(gateRows(REPORT)).toEqual([
      { name: "G1 어휘 닫힘", verdict: "pass", detail: "구간·트리거·원샷 전부 문서 어휘" },
      { name: "G7 후렴 주색 동일", verdict: "fail", detail: "위반 2건" },
      { name: "G10 상대 감소 겹침 없음", verdict: "na", detail: "절 밝기 [45, 38](2개 이하 — n/a)" },
    ]);
  });

  it("상태줄은 개수 3종을 보이고, 경고(WARN)는 원천이 없다고 적는다", () => {
    const html = renderToStaticMarkup(<RunbookGateBar report={REPORT} />);
    expect(html).toContain("통과 1");
    expect(html).toContain("실패 1");
    expect(html).toContain("해당없음 1");
    expect(html).toMatch(/경고[^<]*데이터 없음/);
    // 경고 개수를 숫자로 지어내지 않는다.
    expect(html).not.toMatch(/경고 \d/);
    expect(html).toContain("GATE 상세 보기");
    expect(html).toContain("위반 2건");
  });

  it("리포트를 못 만들었으면 서버 사유를 그대로 보인다", () => {
    const html = renderToStaticMarkup(
      <RunbookGateBar report={{ available: false, reason: "BPM이 선언되지 않았다" }} />,
    );
    expect(html).toContain("BPM이 선언되지 않았다");
    expect(html).not.toContain("통과 ");
  });

  it("리포트 키 자체가 없으면(예전 페이로드) 데이터 없음", () => {
    const html = renderToStaticMarkup(<RunbookGateBar report={undefined} />);
    expect(html).toContain(NO_DATA);
  });
});

describe("REQ-079/080/097/098 컨셉 패널", () => {
  const sections = CUE_SHEET_EXAMPLE.sections;
  const html = renderToStaticMarkup(<ConceptPanel sections={sections} />);

  it("기본 접힘이고 헤더는 「이 곡의 컨셉」이다", () => {
    expect(html).toMatch(/<details[^>]*class="concept-panel"/);
    expect(html).not.toMatch(/<details[^>]*\bopen\b/);
    expect(html).toContain("이 곡의 컨셉");
  });

  it("탭 라벨 3개는 REQ-098 고정 문자열이고, 영어는 보조 표기다", () => {
    expect(html).toContain("이 곡의 연출");
    expect(html).toContain("이 곡의 재료");
    expect(html).toContain("지키는 것·하지 않는 것·아껴 두는 것");
    expect(html).toContain("Master Concept");
    expect(html).toContain("Micro Concept");
    expect(html).toContain("Visual Grammar");
  });

  it("6칸 표 헤더는 REQ-080 고정 문자열이다", () => {
    for (const head of ["구간", "색", "기구·밝기", "움직임", "효과", "그래서 보이는 것"]) {
      expect(html).toContain(`<th>${head}</th>`);
    }
  });

  it("「한눈에」·인과 불릿·「그래서 보이는 것」은 원천이 없어 데이터 없음이다", () => {
    expect(html).toContain("한눈에");
    // 5단계 카드 단계명이 화면에 나오면 지어낸 것이다.
    for (const stage of ["쌓기", "강조", "예고"]) expect(html).not.toContain(stage);
    expect(html).not.toContain("원문 그대로");
    const noData = html.split(NO_DATA).length - 1;
    // 한눈에 1 + 인과 불릿 1 + 표 마지막 칸 × 행 수
    expect(noData).toBeGreaterThanOrEqual(2 + sections.length);
  });

  it("표의 다섯 칸은 구간 값을 그대로 쓴다", () => {
    const rows = grammarRows(sections);
    expect(rows).toHaveLength(sections.length);
    expect(rows[1]).toEqual({
      key: expect.any(String),
      section: "VERSE1",
      color: "P2 웜화이트 / P1 골드앰버",
      fixture: "KEY 70 / BACK 35 · KEY+BACK",
      motion: "STATIC",
      effect: "NONE",
    });
  });
});

describe("REQ-082 CUE SHEET 14열", () => {
  const source = readFileSync(new URL("./CueSheetTimeline.tsx", import.meta.url), "utf-8");
  const columns = (source.match(/const SHEET_COLUMNS = \[([\s\S]*?)\];/) as RegExpMatchArray)[1]
    .split(",")
    .map((s) => s.trim().replace(/^"|"$/g, ""))
    .filter(Boolean);

  it("정확히 14열이고 순서는 src/DESIGN.md §4.4 그대로다", () => {
    expect(columns).toEqual([
      "Q#",
      "구간",
      "회차",
      "Trigger",
      "시각",
      "색",
      "밝기",
      "기구 그룹",
      "움직임",
      "효과",
      "Fade",
      "MIB",
      "Track 예외",
      "근거 등급",
    ]);
  });

  it("제거된 5열(TC Out·Dur·Mood·Trans·Note)은 화면 헤더에 없다", () => {
    for (const gone of ["TC Out", "Dur", "Mood", "Trans", "Note"]) {
      expect(columns).not.toContain(gone);
    }
  });

  it("Trans 값은 데이터 모델에 남는다 — 타입 필드를 지우지 않았다(REQ-096)", () => {
    const protocol = readFileSync(new URL("../protocol.ts", import.meta.url), "utf-8");
    expect(protocol).toMatch(/\btrans\?:/);
  });

  it("MIB 는 bool 원천뿐이라 기호 3종(◐◇◑)을 쓰지 않는다", () => {
    const base = CUE_SHEET_EXAMPLE.sections[0];
    expect(mibCellText({ ...base, mib: true })).toBe("사전이동 있음");
    expect(mibCellText({ ...base, mib: false })).toBe("—");
    expect(source).not.toMatch(/[◐◇◑]/);
  });

  it("밝기 증감 기호는 직전 큐와의 비교에서만 나온다", () => {
    const s = (level: number): SongTimelineSection => ({
      ...CUE_SHEET_EXAMPLE.sections[0],
      intensity: [{ group: "ALL", level }],
    });
    const seq = [s(40), s(60), s(60), s(20)];
    expect(intensityTrend(seq, 0)).toBe("");
    expect(intensityTrend(seq, 1)).toBe("▲");
    expect(intensityTrend(seq, 2)).toBe("");
    expect(intensityTrend(seq, 3)).toBe("▼");
  });

  it("원천 없는 4열은 행마다 데이터 없음 칸으로 그린다", () => {
    const noDataCells = source.match(/className="nodata"/g) ?? [];
    expect(noDataCells.length).toBe(4);
  });
});

describe("배치 — 메인 화면 컴포넌트 불가침", () => {
  const runbook = readFileSync(new URL("./RunbookMode.tsx", import.meta.url), "utf-8");

  it("컨셉 패널은 블록 1(오늘의 곡)과 타임라인 사이, GATE 는 그 뒤다", () => {
    const header = runbook.indexOf('className="runbook-header"');
    const concept = runbook.indexOf("<ConceptPanel");
    const sheet = runbook.indexOf("<CueSheetTimeline");
    const gate = runbook.indexOf("<RunbookGateBar");
    expect(header).toBeGreaterThan(-1);
    expect(concept).toBeGreaterThan(header);
    expect(sheet).toBeGreaterThan(concept);
    expect(gate).toBeGreaterThan(sheet);
  });

  it("GATE 는 앱 셸의 StatusBanner 를 가져다 쓰지 않는다", () => {
    expect(runbook).not.toMatch(/import[^;]*StatusBanner/);
    const gate = readFileSync(new URL("./RunbookGateBar.tsx", import.meta.url), "utf-8");
    expect(gate).not.toMatch(/import[^;]*StatusBanner/);
  });
});
