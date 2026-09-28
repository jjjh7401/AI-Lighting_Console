// t482 — 컨셉 패널 "한눈에" 5단계 카드와 항목 4칸 설명(SPEC-LDDESIGN-001 REQ-079/097,
// AC-018 일부·AC-049). 카드의 수치는 CUE SHEET 와 같은 구간 데이터에서만 나오고,
// 서버는 "어느 구간이 어느 단계인가"(glance.stages)만 준다.
import { describe, expect, it } from "vitest";

import type { SongTimelineConceptReport, SongTimelineSection, SongTimelineView } from "../protocol";
import { DESCRIPTION_SOURCE, explanationCells, glanceView } from "./conceptGlance";
import { NO_DATA } from "./runbookM7";

const LABELS = ["Intro", "Verse 1", "Pre-Chorus 1", "Chorus 1", "Verse 2", "Chorus 2", "Bridge", "Chorus 3", "Outro"];
const HEX = ["#0D33FF", "#FF0000", "#FF8C0D", "#00FF1A", "#FF00B2", "#00E6FF", "#0D33FF", "#FF0000", "#FF8C0D"];

function section(i: number): SongTimelineSection {
  return {
    index: i + 1,
    label: LABELS[i],
    start_ms: i * 10_000,
    cue_number: 101 + i,
    d_level: 3,
    palette: ["blue"],
    position: "Center",
    palette_primary_hex: HEX[i],
    intensity: [
      { group: "KEY", level: 40 + i * 5 },
      { group: "BACK", level: 30 + i * 5 },
    ],
  } as SongTimelineSection;
}

const REPORT: SongTimelineConceptReport = {
  available: true,
  rows: LABELS.map((label, i) => ({
    q: i + 2,
    ts: i * 10,
    kind: "section" as const,
    section: label,
    occurrence: 1,
    trigger: null,
    tracking: "track",
    mib: null,
    one_shot: null,
    evidence: null,
    screen_position: i,
    unused_groups: 5,
    description: `설명 ${i}`,
  })),
  glance: {
    available: true,
    rule: "director-confirmed-2026-09-28",
    reason: null,
    stages: [
      { stage: "시작", positions: [0], reason: null },
      { stage: "쌓기", positions: [1, 2], reason: null },
      { stage: "강조", positions: [3, 4, 5], reason: null },
      { stage: "예고", positions: [], reason: "마지막 후렴 바로 앞도 후렴이다" },
      { stage: "정점→마무리", positions: [7, 8], reason: null },
    ],
  },
};

const TIMELINE = {
  song_title: "Glance Test",
  sections: LABELS.map((_, i) => section(i)),
  total_duration_ms: 90_000,
  concept_report: REPORT,
} as unknown as SongTimelineView;

describe("glanceView — 5단계 카드는 구간 데이터에서만 파생한다 (REQ-097)", () => {
  const view = glanceView(TIMELINE);

  it("서버 배정이 있으면 5장을 규칙 표식과 함께 낸다", () => {
    expect(view.status).toBe("ok");
    if (view.status !== "ok") return;
    expect(view.rule).toBe("director-confirmed-2026-09-28");
    expect(view.cards.map((card) => card.stage)).toEqual(["시작", "쌓기", "강조", "예고", "정점→마무리"]);
  });

  it("쌓기 카드의 Q 범위·구간·시간·색 HEX·밝기 범위는 구간 1~2 값 그대로다", () => {
    if (view.status !== "ok") throw new Error("glance unavailable");
    const card = view.cards[1];
    expect(card.empty).toBeNull();
    expect(card.qRange).toBe("Q102–Q103");
    expect(card.sections).toEqual(["Verse 1", "Pre-Chorus 1"]);
    expect(card.time).toBe("00:10.0–00:30.0");
    expect(card.hexes).toEqual(["#FF0000", "#FF8C0D"]);
    expect(card.colorBar).toBe("#FF0000");
    expect(card.brightness).toBe("35–50%");
  });

  it("한 줄 설명은 수치로만 조립한다 — 형용 문장이 없다", () => {
    if (view.status !== "ok") throw new Error("glance unavailable");
    expect(view.cards[1].line).toBe("구간 2개 · 20.0초 · 밝기 35–50%");
    expect(view.analysis).toBe("구간 9개 · 5단계 중 4단계에 구간 배정 · 규칙 director-confirmed-2026-09-28");
  });

  it("마지막 카드의 끝 시각은 곡 길이에서 온다 — 끝을 지어내지 않는다", () => {
    if (view.status !== "ok") throw new Error("glance unavailable");
    expect(view.cards[4].time).toBe("01:10.0–01:30.0");
  });

  it("구간이 없는 단계는 빈 카드에 서버 사유를 그대로 싣는다", () => {
    if (view.status !== "ok") throw new Error("glance unavailable");
    const preview = view.cards[3];
    expect(preview.empty).toBe("마지막 후렴 바로 앞도 후렴이다");
    expect(preview.qRange).toBeNull();
  });

  it("값을 바꾸면 카드도 바뀐다 — 하드코딩이 아니다", () => {
    const changed = {
      ...TIMELINE,
      sections: TIMELINE.sections.map((s, i) => (i === 1 ? { ...s, cue_number: 555, palette_primary_hex: "#123456" } : s)),
    } as SongTimelineView;
    const card = glanceView(changed);
    if (card.status !== "ok") throw new Error("glance unavailable");
    expect(card.cards[1].qRange).toBe("Q555–Q103");
    expect(card.cards[1].colorBar).toBe("#123456");
  });

  it("서버 배정이 없으면 이유를 그대로 보인다 — 단계 이름을 지어내지 않는다", () => {
    const none = glanceView({ ...TIMELINE, concept_report: { ...REPORT, glance: undefined } } as SongTimelineView);
    expect(none.status).toBe("none");
    const unavailable = glanceView({
      ...TIMELINE,
      concept_report: { ...REPORT, glance: { available: false, rule: "director-confirmed-2026-09-28", reason: "역할 없음", stages: [] } },
    } as SongTimelineView);
    expect(unavailable).toEqual({ status: "none", reason: "역할 없음" });
  });

  it("배정 위치가 구간 목록 밖이면 배정 전체를 믿지 않는다", () => {
    const broken = {
      ...TIMELINE,
      concept_report: {
        ...REPORT,
        glance: { ...REPORT.glance!, stages: [{ stage: "시작", positions: [99], reason: null }] },
      },
    } as SongTimelineView;
    expect(glanceView(broken).status).toBe("none");
  });
});

describe("explanationCells — 항목 클릭 4칸 설명 (REQ-079)", () => {
  it("「무대에서」는 그 구간 컨셉 행의 description, 나머지 셋은 데이터 없음 + 사유", () => {
    const cells = explanationCells(REPORT, 3);
    expect(cells.map((cell) => cell.title)).toEqual(["무슨 뜻", "무대에서", "왜 이렇게 제안했나", "바꾸려면"]);
    expect(cells[1].text).toBe("설명 3");
    // 설명은 컨셉 파이프라인 값이라 CUE SHEET 와 다를 수 있다 — 출처 표식이 붙는다.
    expect(cells[1].source).toBe(DESCRIPTION_SOURCE);
    for (const i of [0, 2, 3]) {
      expect(cells[i].text.startsWith(NO_DATA)).toBe(true);
    }
  });

  it("짝이 되는 행이 없으면 「무대에서」도 데이터 없음이다", () => {
    expect(explanationCells(REPORT, 42)[1].text.startsWith(NO_DATA)).toBe(true);
    expect(explanationCells(REPORT, 42)[1].source).toBeUndefined();
    expect(explanationCells(undefined, 0)[1].text.startsWith(NO_DATA)).toBe(true);
  });
});
