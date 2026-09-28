// t482 — 컨셉 패널 "한눈에" 5단계 카드(REQ-097)와 항목 클릭 4칸 설명(REQ-079).
//
// 원천 원칙(REQ-097 "시트와 어긋나는 값이 있으면 감독이 어느 쪽을 믿을지 알 수
// 없다"): 서버는 어느 구간이 어느 단계인가(`concept_report.glance`)만 준다. 카드의
// 수치(Q 범위·구간·시간·색 HEX·밝기 범위)는 CUE SHEET 와 같은 `sections` 에서 같은
// 도우미(cueLabel·formatTc·sectionEndMs·sectionHex)로 계산한다. 한 줄 설명도 그
// 수치로만 조립한다 — 형용 문장을 두지 않는다.
import type { SongTimelineConceptReport, SongTimelineSection, SongTimelineView } from "../protocol";
import { cueLabel, formatTc, sectionEndMs, songTotalMs } from "./CueSheetTimeline";
import { NO_DATA, sectionHex } from "./runbookM7";

export interface GlanceCard {
  stage: string;
  /** 구간이 없는 단계면 서버 사유, 있으면 null. */
  empty: string | null;
  qRange: string | null;
  sections: string[];
  time: string | null;
  hexes: string[];
  colorBar: string | null;
  brightness: string | null;
  line: string | null;
}

export type GlanceView =
  | { status: "none"; reason: string }
  | { status: "ok"; rule: string; analysis: string; cards: GlanceCard[] };

function sectionLevels(section: SongTimelineSection): number[] {
  if (section.intensity && section.intensity.length > 0) {
    return section.intensity.map((entry) => entry.level);
  }
  // CUE SHEET 밝기 칸과 같은 대체값(sectionIntensityPercent 의 D 레벨 환산).
  return [Math.min(100, Math.max(0, section.d_level * 20))];
}

function card(
  stage: string,
  positions: number[],
  reason: string | null,
  timeline: SongTimelineView,
): GlanceCard {
  const all = timeline.sections;
  if (positions.length === 0) {
    return {
      stage,
      empty: reason ?? "이 단계에 드는 구간이 없다",
      qRange: null,
      sections: [],
      time: null,
      hexes: [],
      colorBar: null,
      brightness: null,
      line: null,
    };
  }
  const picked = positions.map((position) => all[position]);
  const first = picked[0];
  const lastPosition = positions[positions.length - 1];
  const end = sectionEndMs(all[lastPosition], all[lastPosition + 1], songTotalMs(timeline));
  const hexes: string[] = [];
  for (const section of picked) {
    const hex = sectionHex(section, timeline.palette_legend);
    if (hex && !hexes.includes(hex)) hexes.push(hex);
  }
  const levels = picked.flatMap(sectionLevels);
  const brightness = `${Math.min(...levels)}–${Math.max(...levels)}%`;
  const seconds = end === null ? null : ((end - first.start_ms) / 1000).toFixed(1);
  const qFirst = cueLabel(first);
  const qLast = cueLabel(picked[picked.length - 1]);
  return {
    stage,
    empty: null,
    qRange: qFirst === qLast ? qFirst : `${qFirst}–${qLast}`,
    sections: picked.map((section) => section.label),
    time: `${formatTc(first.start_ms)}–${formatTc(end)}`,
    hexes,
    colorBar: hexes[0] ?? null,
    brightness,
    line: `구간 ${picked.length}개 · ${seconds === null ? "길이 —" : `${seconds}초`} · 밝기 ${brightness}`,
  };
}

/** "한눈에" 구획의 뷰 모델. 서버 배정이 없거나 믿을 수 없으면 사유와 함께 none. */
export function glanceView(timeline: SongTimelineView): GlanceView {
  const glance = timeline.concept_report?.glance;
  if (!glance) {
    return { status: "none", reason: "단계 배정 원천이 서버에 없다(컨셉 리포트에 glance 없음)" };
  }
  if (!glance.available) {
    return { status: "none", reason: glance.reason ?? "단계 배정 원천이 없다" };
  }
  const count = timeline.sections.length;
  const outOfRange = glance.stages.some((stage) =>
    stage.positions.some((position) => !Number.isInteger(position) || position < 0 || position >= count),
  );
  if (outOfRange) {
    return { status: "none", reason: `단계 배정 위치가 화면 구간 ${count}개 범위를 벗어난다` };
  }
  const cards = glance.stages.map((stage) => card(stage.stage, stage.positions, stage.reason, timeline));
  const filled = cards.filter((entry) => entry.empty === null).length;
  return {
    status: "ok",
    rule: glance.rule,
    analysis: `구간 ${count}개 · ${cards.length}단계 중 ${filled}단계에 구간 배정 · 규칙 ${glance.rule}(감독 확인 전)`,
    cards,
  };
}

export interface ExplanationCell {
  title: string;
  text: string;
  /** 값의 출처가 CUE SHEET 와 다를 때 함께 보이는 표식. */
  source?: string;
}

/** 큐 설명은 컨셉 파이프라인의 해석 상태에서 나온다. 그 밝기는 D 레벨을 읽지 않아
 * CUE SHEET(조립기)와 10구간 중 1구간만 맞았다(.moai/reports/t486) — 카드 t486 이
 * 서버에서 「최대 N%」 수치를 뺐다. 설명은 변화 서술만 싣고, 밝기는 시트가 기준이다.
 * 출처를 숨기지 않는다. */
export const DESCRIPTION_SOURCE = "컨셉 파이프라인 계산 — 밝기 수치는 CUE SHEET 기준(큐 생성 경로 미통합, REQ-003)";

/** REQ-079 항목 클릭 4칸 설명. 「무대에서」만 원천이 있다 — 그 구간 section
 * 행의 서버 큐 설명(`description`, REQ-070). 나머지 셋은 원천이 없어 사유와 함께
 * 데이터 없음이다(지어내지 않는다). `position` 은 `sectionPosition()` 값이다. */
export function explanationCells(
  report: SongTimelineConceptReport | undefined,
  position: number,
): ExplanationCell[] {
  const row = report?.rows?.find((entry) => entry.kind === "section" && entry.screen_position === position);
  return [
    { title: "무슨 뜻", text: `${NO_DATA} — 항목 뜻풀이 원천이 서버에 없다` },
    row?.description
      ? { title: "무대에서", text: row.description, source: DESCRIPTION_SOURCE }
      : { title: "무대에서", text: `${NO_DATA} — 이 구간과 짝지어진 컨셉 행 설명이 없다` },
    { title: "왜 이렇게 제안했나", text: `${NO_DATA} — 제안 사유 문장 원천이 서버에 없다` },
    { title: "바꾸려면", text: `${NO_DATA} — 변경 안내 원천이 서버에 없다` },
  ];
}
