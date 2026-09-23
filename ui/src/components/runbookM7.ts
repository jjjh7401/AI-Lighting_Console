// t454 — SPEC-LDDESIGN-001 M7 2차의 순수 함수들. 렌더를 결정하는 값만
// 여기서 만들고, 컴포넌트는 그 값을 그리기만 한다(이 프로젝트에는 DOM 테스트
// 하네스가 없다 — CueSheetTimeline.test.tsx 머리 주석).
//
// 원칙: 원천이 있는 칸만 채운다. 서버가 내지 않는 값은 NO_DATA 로 둔다 —
// 비슷한 필드에서 끌어와 채우면 감독이 시트와 화면 중 어느 쪽을 믿을지 알 수
// 없게 된다(REQ-LDDESIGN-097 근거 문장).
import type { SongTimelineConceptReport, SongTimelineSection } from "../protocol";

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
