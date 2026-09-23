// 카드 t387 — 감독이 「음악을 어떻게 분석했고 큐를 어떻게 만들었는지에 대한
// 분석 리포트가 없어」라고 지적했다. 이 파일은 그 요약을 만든다.
//
// 원칙: 서버가 이미 페이로드에 실어 보내는 값만 흘려보낸다. 값에 출처가
// 없으면 그 줄 자체를 안 낸다 — 그럴듯한 이유를 지어내지 않는다. 이 규율은
// 이 리포에서 이미 지키고 있는 것과 같다(팔레트에 이름이 없으면 이름을
// 지어내지 않는 것과 같은 원칙).
import type { SongTimelineView } from "../protocol";

export interface AnalysisSummaryLine {
  label: string;
  text: string;
}

function formatBpmForSummary(bpm: number): string {
  return String(Math.round(bpm * 100) / 100);
}

function tcMethodText(method: SongTimelineView["tc_method"]): string | null {
  if (method === "MEASURED") return "시각 측정됨";
  if (method === "DERIVED") return "시각 추정(마디 연산)";
  return null;
}

/** 음악을 어떻게 읽었는지 — bpm·박자·마디·시각 출처를 한 줄로. */
function buildMusicLine(timeline: SongTimelineView): AnalysisSummaryLine | null {
  const parts: string[] = [];
  if (timeline.bpm !== undefined) parts.push(`${formatBpmForSummary(timeline.bpm)} BPM`);
  if (timeline.time_signature) parts.push(timeline.time_signature);
  if (timeline.bar_count !== undefined) parts.push(`${timeline.bar_count}마디`);
  const methodText = tcMethodText(timeline.tc_method);
  if (methodText) parts.push(methodText);
  if (parts.length === 0) return null;
  return { label: "음악 판독", text: parts.join(" · ") };
}

/** DERIVED 일 때만 — 감독이 놓치면 안 되는 경고. */
function buildWarningLine(timeline: SongTimelineView): AnalysisSummaryLine | null {
  if (timeline.tc_method !== "DERIVED" || !timeline.tc_method_warning) return null;
  return { label: "주의", text: timeline.tc_method_warning };
}

// SPEC-COPILOT-COLORMODE-001 D4 — Q2B_COLOR_USAGE 값(modulate/single/
// per_chorus/split_swap)의 한국어 설명 문구. 값 자체는 서버가 이미 실어 보내는
// 것이므로 여기서는 표현만 맡는다 — 값을 지어내지 않는다는 이 파일의
// 원칙과 같다.
const COLOR_USAGE_LABELS: Record<string, string> = {
  modulate: "메인 컬러 중심으로 변조하다가 임팩트에서 터뜨림",
  single: "이 색 계열로만 유지",
  per_chorus: "후렴마다 다른 포인트 색",
  // 카드 t445 — 긴 후렴을 나눈 큐마다 주색·보조색을 맞바꾼다.
  split_swap: "후렴 안에서 주색·보조색 맞바꾸기",
};

/** 무엇이 색을 정했는지 — 감독의 PLAN 답변 + 구간 아크 역할 + 색 운용 방식. */
function buildColorLine(timeline: SongTimelineView): AnalysisSummaryLine | null {
  const parts: string[] = [];
  const paletteDecision = timeline.director_decisions.find((decision) => decision.axis === "palette");
  if (paletteDecision) {
    const value =
      typeof paletteDecision.value === "string"
        ? paletteDecision.value
        : Array.isArray(paletteDecision.value)
          ? paletteDecision.value.join("+")
          : String(paletteDecision.value);
    parts.push(`감독 지정(${paletteDecision.step}): ${value}`);
  }
  const colorUsageDecision = timeline.director_decisions.find((decision) => decision.axis === "color_usage");
  if (colorUsageDecision) {
    const rawValue =
      typeof colorUsageDecision.value === "string" ? colorUsageDecision.value : String(colorUsageDecision.value);
    const label = COLOR_USAGE_LABELS[rawValue] ?? rawValue;
    const defaultAcceptedMarker = colorUsageDecision.source === "default_accepted" ? " (기본값 수용)" : "";
    parts.push(`색 운용: ${label}${defaultAcceptedMarker}`);
  }
  const roles = Array.from(
    new Set(timeline.sections.map((section) => section.role).filter((role): role is string => Boolean(role))),
  );
  if (roles.length > 0) {
    parts.push(`구간 역할 ${roles.length}종(${roles.join("/")})이 팔레트를 갈랐다`);
  }
  if (parts.length === 0) return null;
  return { label: "색", text: parts.join(" · ") };
}

/** 어떤 이펙트가 쓰였는지 — 구간에 실제로 배정된 fx 값의 합집합. */
function buildFxLine(timeline: SongTimelineView): AnalysisSummaryLine | null {
  const fxSet = new Set(timeline.sections.flatMap((section) => section.fx));
  if (fxSet.size === 0) return null;
  return { label: "이펙트", text: `${fxSet.size}종 사용: ${Array.from(fxSet).join(", ")}` };
}

/** 무엇이 꺼져 있는지 — disabled[] 의 사유를 그대로. */
function buildDisabledLine(timeline: SongTimelineView): AnalysisSummaryLine | null {
  if (timeline.disabled.length === 0) return null;
  const reasons = Array.from(new Set(timeline.disabled.map((note) => note.reason)));
  return { label: "꺼진 축", text: reasons.join(" · ") };
}

/** 이 타임라인이 실제로 콘솔에 있는지 — 감독이 화면과 콘솔을 혼동하지 않게. */
function buildConsoleLine(timeline: SongTimelineView): AnalysisSummaryLine | null {
  if (timeline.console_stored === undefined) return null;
  return {
    label: "콘솔 상태",
    text: timeline.console_stored
      ? "이 타임라인은 콘솔에 저장되어 있다"
      : "이 타임라인은 아직 콘솔에 저장되지 않았다",
  };
}

export function buildAnalysisSummary(timeline: SongTimelineView): AnalysisSummaryLine[] {
  const builders = [
    buildMusicLine,
    buildWarningLine,
    buildColorLine,
    buildFxLine,
    buildDisabledLine,
    buildConsoleLine,
  ];
  const lines: AnalysisSummaryLine[] = [];
  for (const build of builders) {
    const line = build(timeline);
    if (line) lines.push(line);
  }
  return lines;
}
