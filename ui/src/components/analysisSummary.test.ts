// 카드 t387 — 감독이 「음악을 어떻게 분석했고 큐를 어떻게 만들었는지」 설명해
// 달라고 요청했다. 이 시험은 서버가 이미 페이로드에 실어 보내는 값들
// (bpm/tc_method/director_decisions/role/disabled/console_stored)만 요약으로
// 흘려보내는지 잰다 — 없는 값을 지어내면 안 된다.
import { describe, expect, it } from "vitest";

import { buildAnalysisSummary } from "./analysisSummary";
import type { SongTimelineView } from "../protocol";

const BASE: SongTimelineView = {
  song_title: "Sugar",
  sequence_name: "Sugar Seq",
  sequence_number: 110,
  timing_mode: "timecode",
  timecode_number: 1,
  lifecycle: "pending_approval",
  approval: "pending",
  director_decisions: [],
  sections: [],
  lint: [],
  unresolved: [],
  disabled: [],
  readback: { verified: null, message: null },
};

describe("buildAnalysisSummary", () => {
  it("음악 판독 줄을 bpm·박자·마디·tc_method 로부터 만든다", () => {
    const timeline: SongTimelineView = {
      ...BASE,
      bpm: 126.048,
      time_signature: "4/4",
      bar_count: 68,
      tc_method: "MEASURED",
    };
    const summary = buildAnalysisSummary(timeline);
    const musicLine = summary.find((line) => line.label === "음악 판독");
    expect(musicLine?.text).toContain("126.05 BPM");
    expect(musicLine?.text).toContain("4/4");
    expect(musicLine?.text).toContain("68마디");
    expect(musicLine?.text).toContain("측정");
  });

  it("tc_method 가 DERIVED 면 경고 문구를 별도 줄로 낸다", () => {
    const timeline: SongTimelineView = {
      ...BASE,
      tc_method: "DERIVED",
      tc_method_warning: "마디 연산으로 도출된 시각입니다 — 음원 미검증",
    };
    const summary = buildAnalysisSummary(timeline);
    const warnLine = summary.find((line) => line.label === "주의");
    expect(warnLine?.text).toBe("마디 연산으로 도출된 시각입니다 — 음원 미검증");
  });

  it("tc_method 가 없으면 음악 판독 줄도 경고 줄도 안 낸다 — 지어내지 않는다", () => {
    const summary = buildAnalysisSummary(BASE);
    expect(summary.find((line) => line.label === "음악 판독")).toBeUndefined();
    expect(summary.find((line) => line.label === "주의")).toBeUndefined();
  });

  it("director_decisions 의 palette 축 답변을 색 줄에 싣는다", () => {
    const timeline: SongTimelineView = {
      ...BASE,
      director_decisions: [
        { step: "Q2 PALETTE", axis: "palette", value: "블루/퍼플", confirmed: true, source: "director" },
      ],
    };
    const summary = buildAnalysisSummary(timeline);
    const colorLine = summary.find((line) => line.label === "색");
    expect(colorLine?.text).toContain("Q2 PALETTE");
    expect(colorLine?.text).toContain("블루/퍼플");
  });

  it("구간 role 이 여러 종류면 색 줄에 역할 갈래를 같이 낸다", () => {
    const timeline: SongTimelineView = {
      ...BASE,
      sections: [
        makeSection({ index: 1, role: "intro" }),
        makeSection({ index: 2, role: "chorus" }),
        makeSection({ index: 3, role: "finale" }),
      ],
    };
    const summary = buildAnalysisSummary(timeline);
    const colorLine = summary.find((line) => line.label === "색");
    expect(colorLine?.text).toContain("3종");
    expect(colorLine?.text).toContain("intro");
    expect(colorLine?.text).toContain("chorus");
    expect(colorLine?.text).toContain("finale");
  });

  it("director_decisions 도 role 도 없으면 색 줄을 안 낸다", () => {
    const summary = buildAnalysisSummary(BASE);
    expect(summary.find((line) => line.label === "색")).toBeUndefined();
  });

  it("구간의 fx 값을 모아 이펙트 줄을 만든다", () => {
    const timeline: SongTimelineView = {
      ...BASE,
      sections: [
        makeSection({ index: 1, fx: ["dimmer chase"] }),
        makeSection({ index: 2, fx: ["strobe hit"] }),
      ],
    };
    const summary = buildAnalysisSummary(timeline);
    const fxLine = summary.find((line) => line.label === "이펙트");
    expect(fxLine?.text).toContain("dimmer chase");
    expect(fxLine?.text).toContain("strobe hit");
    expect(fxLine?.text).toContain("2종");
  });

  it("disabled[] 의 사유를 꺼진 축 줄로 낸다", () => {
    const timeline: SongTimelineView = {
      ...BASE,
      disabled: [
        { axis: "position", section_index: null, reason: "좌표 없음" },
        { axis: "fx", section_index: 3, reason: "단일 레이어 계획" },
      ],
    };
    const summary = buildAnalysisSummary(timeline);
    const disabledLine = summary.find((line) => line.label === "꺼진 축");
    expect(disabledLine?.text).toContain("좌표 없음");
    expect(disabledLine?.text).toContain("단일 레이어 계획");
  });

  it("console_stored 를 정직하게 그대로 반영한다 — 지어내지 않는다", () => {
    const stored = buildAnalysisSummary({ ...BASE, console_stored: true });
    expect(stored.find((line) => line.label === "콘솔 상태")?.text).toContain("저장되어");

    const notStored = buildAnalysisSummary({ ...BASE, console_stored: false });
    expect(notStored.find((line) => line.label === "콘솔 상태")?.text).toContain("아직");

    const unknown = buildAnalysisSummary(BASE);
    expect(unknown.find((line) => line.label === "콘솔 상태")).toBeUndefined();
  });
});

function makeSection(
  overrides: Partial<SongTimelineView["sections"][number]>,
): SongTimelineView["sections"][number] {
  return {
    index: 1,
    label: "S1",
    start_ms: 0,
    cue_number: 1,
    d_level: 3,
    palette: [],
    position: "",
    texture: "",
    fx: [],
    accents: [],
    mib: false,
    trig_time_seconds: null,
    ...overrides,
  };
}
