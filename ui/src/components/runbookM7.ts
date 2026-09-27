// t454 — SPEC-LDDESIGN-001 M7 2차의 순수 함수들. 렌더를 결정하는 값만
// 여기서 만들고, 컴포넌트는 그 값을 그리기만 한다(이 프로젝트에는 DOM 테스트
// 하네스가 없다 — CueSheetTimeline.test.tsx 머리 주석).
//
// 원칙: 원천이 있는 칸만 채운다. 서버가 내지 않는 값은 NO_DATA 로 둔다 —
// 비슷한 필드에서 끌어와 채우면 감독이 시트와 화면 중 어느 쪽을 믿을지 알 수
// 없게 된다(REQ-LDDESIGN-097 근거 문장).
import type {
  SongTimelineConceptReport,
  SongTimelineConceptRow,
  SongTimelinePaletteEntry,
  SongTimelineSection,
} from "../protocol";

/** 원천 없는 칸의 표기. 「—」(값이 비어 있음)와 다르다: 이건 서버가 이 칸을
 * 아직 내보내지 않는다는 뜻이다. */
export const NO_DATA = "데이터 없음";

export type GateVerdict = "pass" | "fail" | "na";

export interface GateTally {
  pass: number;
  fail: number;
  na: number;
}

export interface GateRow {
  name: string;
  verdict: GateVerdict;
  detail: string;
}

function verdictOf(passed: boolean | null): GateVerdict {
  if (passed === true) return "pass";
  if (passed === false) return "fail";
  return "na";
}

/** 게이트 판정 행. 리포트가 없거나 못 만들었으면 빈 목록. 서버의 게이트
 * 순서(G1..G13)를 그대로 쓴다. */
export function gateRows(report: SongTimelineConceptReport | undefined): GateRow[] {
  if (!report || !report.available || !report.gates) return [];
  return Object.entries(report.gates).map(([name, result]) => ({
    name,
    verdict: verdictOf(result.passed),
    detail: result.detail,
  }));
}

/** 상태줄 요약 개수. 원천이 없으면 null — 0 으로 두면 「전부 통과」처럼 읽힌다.
 * 경고(WARN) 개수는 없다: 서버 `passed` 는 세 값뿐이다. */
export function gateTally(report: SongTimelineConceptReport | undefined): GateTally | null {
  if (!report || !report.available || !report.gates) return null;
  const tally: GateTally = { pass: 0, fail: 0, na: 0 };
  for (const row of gateRows(report)) tally[row.verdict] += 1;
  return tally;
}

/** 밝기 칸 막대·증감에 쓰는 0..100. 그룹 값이 있으면 최댓값, 없으면 d_level×20
 * (CueSheetTimeline 의 sectionIntensityPercent 와 같은 규칙 — 값은 그쪽이 정본). */
function levelOf(section: SongTimelineSection): number {
  if (section.intensity && section.intensity.length > 0) {
    return Math.max(...section.intensity.map((entry) => entry.level));
  }
  return Math.min(100, Math.max(0, section.d_level * 20));
}

/** 직전 큐 대비 증감 기호. 첫 큐이거나 같으면 빈 문자열. */
export function intensityTrend(sections: SongTimelineSection[], index: number): "▲" | "▼" | "" {
  if (index <= 0 || index >= sections.length) return "";
  const now = levelOf(sections[index]);
  const before = levelOf(sections[index - 1]);
  if (now > before) return "▲";
  if (now < before) return "▼";
  return "";
}

/** MIB 칸. 원천은 `mib: boolean`(이 구간에 mib_premove 큐가 있는가) 하나뿐이다.
 * dark/mark/live 3상태는 서버가 구간 단위로 내지 않으므로 기호를 쓰지 않는다. */
export function mibCellText(section: SongTimelineSection): string {
  return section.mib ? "사전이동 있음" : "—";
}

function textOrDash(value: string | undefined | null): string {
  return value && value.trim() !== "" ? value : "—";
}

export interface GrammarRow {
  key: string;
  section: string;
  color: string;
  fixture: string;
  motion: string;
  effect: string;
}

/** 탭 1 여섯 칸 표의 앞 다섯 칸 — 구간 값 그대로. 「그래서 보이는 것」은
 * 원천이 없어 컴포넌트가 NO_DATA 로 그린다. */
export function grammarRows(sections: SongTimelineSection[]): GrammarRow[] {
  return sections.map((section) => {
    const primary = section.palette_primary ?? section.palette[0];
    const secondary = section.palette_primary ? section.palette_secondary : section.palette[1];
    const color = [primary, secondary].filter((c): c is string => Boolean(c)).join(" / ");
    const level =
      section.intensity && section.intensity.length > 0
        ? section.intensity.map((entry) => `${entry.group} ${entry.level}`).join(" / ")
        : `D${section.d_level}`;
    const groups = section.fixture_groups && section.fixture_groups.length > 0
      ? ` · ${section.fixture_groups.join("+")}`
      : "";
    return {
      key: `${section.index}-${section.cue_number}`,
      section: section.label,
      color: textOrDash(color),
      fixture: `${level}${groups}`,
      motion: textOrDash(section.movement ?? section.position),
      effect: textOrDash(section.effect ?? (section.fx.length ? section.fx.join(" · ") : null)),
    };
  });
}

// --- t458 — M7 3차: 서버 t455·t456 데이터로 채우는 칸 ------------------------

/** 화면 구간 하나에 짝지어진 컨셉 행 묶음(서버 `screen_position` 기준). */
export interface SectionConcept {
  /** 그 구간 section 행의 회차. section 행이 없으면 null. */
  occurrence: number | null;
  /** 구간 안 행들의 trigger(나온 순서, 중복 제거). */
  triggers: string[];
  /** 구간 안 행들의 MIB 상태(나온 순서, 중복 제거). */
  mib: ("dark" | "mark" | "live")[];
  /** 그 구간 section 행의 근거 등급(REQ-022 4등급). 없으면 null. */
  evidence: string | null;
}

/** REQ-LDDESIGN-072 — 근거 등급이 없는 항목 표시(서버 `server/concept/evidence.py`
 * `NO_PUBLIC_EVIDENCE_MARKER` 와 같은 문자열). */
export const NO_PUBLIC_EVIDENCE = "[공개 근거 없음]";

/** 짝짓기가 된 리포트면 화면 구간마다 묶음을 낸다. 리포트가 없거나,
 * `row_pairing.available` 이 false 거나, 행이 없으면 null — 그때는 t454 처럼
 * 「데이터 없음」을 그린다. 구간 이름은 행 `section` 을 쓰지 않는다. */
export function conceptBySection(
  report: SongTimelineConceptReport | undefined,
  sectionCount: number,
): SectionConcept[] | null {
  if (!report || !report.available || !report.rows || !report.row_pairing?.available) {
    return null;
  }
  const out: SectionConcept[] = Array.from({ length: sectionCount }, () => ({
    occurrence: null,
    triggers: [],
    mib: [],
    evidence: null,
  }));
  for (const row of report.rows) {
    const at = row.screen_position;
    if (at === null || at < 0 || at >= sectionCount) continue;
    const slot = out[at];
    if (row.kind === "section" && slot.occurrence === null) {
      slot.occurrence = row.occurrence;
      slot.evidence = row.evidence;
    }
    if (row.trigger && !slot.triggers.includes(row.trigger)) slot.triggers.push(row.trigger);
    if (row.mib && !slot.mib.includes(row.mib)) slot.mib.push(row.mib);
  }
  return out;
}

const MIB_SYMBOL: Record<"dark" | "mark" | "live", string> = {
  dark: "◐ dark",
  mark: "◇ mark",
  live: "◑ live",
};

/** CUE SHEET 회차·Trigger·MIB·근거 등급 칸. `concept` 가 null(짝 없음)이면
 * 회차·Trigger·근거 등급은 NO_DATA, MIB 는 t454 의 bool 표기로 돌아간다. 원천은
 * 있는데 값이 비었으면 「—」, 근거 등급이 null 이면 「[공개 근거 없음]」. */
export function conceptCells(
  concept: SectionConcept | null,
  section: SongTimelineSection,
): { occurrence: string; trigger: string; mib: string; evidence: string; nodata: boolean } {
  if (concept === null) {
    return {
      occurrence: NO_DATA,
      trigger: NO_DATA,
      mib: mibCellText(section),
      evidence: NO_DATA,
      nodata: true,
    };
  }
  return {
    occurrence: concept.occurrence === null ? "—" : String(concept.occurrence),
    trigger: concept.triggers.length ? concept.triggers.join(" · ") : "—",
    mib: concept.mib.length ? concept.mib.map((status) => MIB_SYMBOL[status]).join(" ") : "—",
    evidence: concept.evidence ?? NO_PUBLIC_EVIDENCE,
    nodata: false,
  };
}

export interface TimelineDot {
  key: string;
  /** 타임라인 왼쪽 기준 %(0..100). */
  leftPct: number;
  kind: "one_shot" | "mark";
  /** 점 옆 글자(원샷 이름 또는 「Mark」). */
  label: string;
  /** 마우스를 올리면 보일 설명 — 구간 이름은 화면 구간 label 이다. */
  title: string;
}

/** 원샷·Mark 점 줄(REQ-081). 짝지어진 행만 그린다 — 짝짓기가 안 됐으면 null.
 * 위치는 행 `ts`(초). */
export function timelineDots(
  report: SongTimelineConceptReport | undefined,
  sections: SongTimelineSection[],
  totalMs: number,
): TimelineDot[] | null {
  if (conceptBySection(report, sections.length) === null || totalMs <= 0) return null;
  const place = (row: SongTimelineConceptRow) =>
    Math.min(100, Math.max(0, ((row.ts * 1000) / totalMs) * 100));
  const dots: TimelineDot[] = [];
  for (const row of report?.rows ?? []) {
    if (row.screen_position === null) continue;
    const label = sections[row.screen_position]?.label ?? "";
    if (row.one_shot) {
      dots.push({
        key: `shot-${row.q}`,
        leftPct: place(row),
        kind: "one_shot",
        label: row.one_shot.shot,
        title: `${label} · ${row.one_shot.shot} → ${row.one_shot.target}`,
      });
    }
    if (row.mib === "mark") {
      dots.push({
        key: `mark-${row.q}`,
        leftPct: place(row),
        kind: "mark",
        label: "Mark",
        title: `${label} · MIB mark`,
      });
    }
  }
  return dots;
}

/** 블록·색 레일 색. 서버 HEX(t456)가 먼저, 없으면 범례, 그것도 없으면 null
 * (호출자가 중립색으로 떨어진다). UI 는 색 이름 → 색값 표를 들고 있지 않다. */
export function sectionHex(
  section: SongTimelineSection,
  legend: SongTimelinePaletteEntry[] | undefined,
): string | null {
  if (section.palette_primary_hex) return section.palette_primary_hex;
  if (!legend || legend.length === 0) return null;
  const token = (section.palette_primary ?? section.palette[0] ?? "").trim().split(/\s+/)[0];
  if (!token) return null;
  return legend.find((entry) => entry.id === token || entry.name === token)?.color ?? null;
}
