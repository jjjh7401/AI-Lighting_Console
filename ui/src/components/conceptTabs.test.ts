// t492 — 컨셉 패널 탭 2·3 본문, 4칸 「바꾸려면」, 「그래서 보이는 것」 사유
// (SPEC-LDDESIGN-001 REQ-079·080·097·098, AC-018 잔여). 원칙: 다른 칸 값을
// 되풀이하지 않는다(탭 2 는 곡 단위 집계), 원천 없는 내용은 비우고 사유를 보인다.
import { describe, expect, it } from "vitest";

import type { SongTimelineConceptReport, SongTimelineSection } from "../protocol";
import { explanationCells } from "./conceptGlance";
import { changeGuideText, grammarView, materialSummary, OUTCOME_NO_SOURCE } from "./conceptTabs";
import { NO_DATA } from "./runbookM7";

function section(i: number, fields: Partial<SongTimelineSection> = {}): SongTimelineSection {
  return {
    index: i + 1,
    label: `S${i}`,
    start_ms: i * 10_000,
    cue_number: 101 + i,
    d_level: 3,
    palette: ["blue"],
    position: "Center",
    texture: "snap",
    fx: [],
    accents: [],
    mib: false,
    trig_time_seconds: null,
    ...fields,
  } as SongTimelineSection;
}

describe("changeGuideText — 4칸 「바꾸려면」은 실제 편집 위치를 가리킨다", () => {
  it("PLAN CUE(콘솔 저장 전)면 그 큐 번호의 수정요청 생성기를 가리킨다", () => {
    const text = changeGuideText(section(4), "draft");
    expect(text).toContain("Q105");
    expect(text).toContain("수정요청 생성기");
    expect(text.startsWith(NO_DATA)).toBe(false);
  });

  it("콘솔에 저장·검증된 큐는 생성기가 열리지 않으므로 데이터 없음 + 사유", () => {
    for (const status of ["stored", "verified"] as const) {
      const text = changeGuideText(section(0), status);
      expect(text.startsWith(NO_DATA)).toBe(true);
      expect(text).not.toContain("Q101");
    }
  });

  it("explanationCells 에 넘기면 「바꾸려면」 칸만 바뀌고 무슨 뜻·왜는 데이터 없음 그대로", () => {
    const cells = explanationCells(undefined, 0, changeGuideText(section(0), "approved"));
    expect(cells[3].text).toContain("Q101");
    expect(cells[0].text.startsWith(NO_DATA)).toBe(true);
    expect(cells[2].text.startsWith(NO_DATA)).toBe(true);
  });
});

describe("「그래서 보이는 것」 사유", () => {
  it("리드 결정 문구 — 구간별 원천 없음, 인터뷰가 곡 단위", () => {
    expect(OUTCOME_NO_SOURCE).toBe("구간별 원천 없음 — 인터뷰가 곡 단위");
  });
});

describe("materialSummary — 탭 2 는 구간 행 나열이 아니라 곡 단위 집계다", () => {
  const sections = [
    section(0, { position: "Center", texture: "fade" }),
    section(1, { position: "Fan", texture: "fade" }),
    section(2, { position: "Center", texture: "snap" }),
    section(3, { position: "", texture: "snap" }),
  ];
  const byTitle = Object.fromEntries(materialSummary(sections).map((item) => [item.title, item]));

  it("다섯 재료를 이 순서로 낸다", () => {
    expect(materialSummary(sections).map((item) => item.title)).toEqual(["감정", "공간", "움직임", "질감", "시작–끝"]);
  });

  it("공간은 값별 구간 수(많은 순) + 빈 값 구간 수", () => {
    expect(byTitle["공간"].text).toBe("Center 2구간 · Fan 1구간 · 값 없음 1구간");
    expect(byTitle["공간"].nodata).toBe(false);
  });

  it("질감 집계", () => {
    expect(byTitle["질감"].text).toBe("fade 2구간 · snap 2구간");
  });

  it("시작–끝은 이웃 구간 사이에서 재료가 바뀐 횟수다(빈 값 경계는 세지 않는다)", () => {
    // 공간: Center→Fan(바뀜) Fan→Center(바뀜) Center→''(비교 안 함) = 2
    // 질감: fade→fade, fade→snap(바뀜), snap→snap = 1
    expect(byTitle["시작–끝"].text).toBe("구간 경계 3곳 중 공간 바뀜 2번 · 질감 바뀜 1번");
  });

  it("감정은 서버가 못 채우는 필드라 데이터 없음 + 사유", () => {
    expect(byTitle["감정"].nodata).toBe(true);
    expect(byTitle["감정"].text.startsWith(NO_DATA)).toBe(true);
  });

  it("움직임 값이 한 구간에도 없으면 데이터 없음 + 사유(0구간이라고 쓰지 않는다)", () => {
    expect(byTitle["움직임"].nodata).toBe(true);
    expect(byTitle["움직임"].text.startsWith(NO_DATA)).toBe(true);
  });

  it("움직임이 모든 구간에서 포지션과 같으면(서버 movement = 포지션 프리셋) 공간을 되풀이하지 않는다", () => {
    const same = [section(0, { position: "Center", movement: "Center" }), section(1, { position: "Fan", movement: "Fan" })];
    const item = materialSummary(same).find((entry) => entry.title === "움직임")!;
    expect(item.nodata).toBe(true);
    expect(item.text).toContain("공간에서 셌다");
  });

  it("포지션과 다른 움직임 값이 있으면 움직임을 따로 센다", () => {
    const diff = [section(0, { position: "Center", movement: "Center" }), section(1, { position: "Center", movement: "Fan" })];
    const item = materialSummary(diff).find((entry) => entry.title === "움직임")!;
    expect(item.nodata).toBe(false);
    expect(item.text).toBe("Center 1구간 · Fan 1구간");
  });

  it("구간 하나하나의 라벨을 늘어놓지 않는다(반복 금지)", () => {
    for (const item of materialSummary(sections)) {
      for (const s of sections) expect(item.text).not.toContain(s.label);
    }
  });
});

describe("grammarView — 탭 3 「아껴 두는 것」은 concept_report.reserve 를 그대로 읽는다", () => {
  // 구간 10개 — released_q(7)가 다른 구간을 가리킬 수 있어야 행 번호로 잘못 읽는 결함이 드러난다.
  const sections = Array.from({ length: 10 }, (_, i) => section(i));
  const report: SongTimelineConceptReport = {
    available: true,
    reserve: [
      { name: "BLIND", kind: "group", released_q: 7, screen_position: 2 },
      { name: "STROBE", kind: "group", released_q: null, screen_position: null },
      { name: "White", kind: "color", released_q: 4, screen_position: null },
    ],
  };

  it("해제 위치는 screen_position 의 구간 큐 번호다(released_q 행 번호가 아니다)", () => {
    const view = grammarView(report, sections);
    expect(view.status).toBe("ok");
    if (view.status !== "ok") return;
    expect(view.reserve[0]).toEqual({ name: "BLIND", kind: "그룹", release: "Q103 S2 에서 처음 푼다" });
    expect(view.reserve[0].release).not.toContain("Q007");
  });

  it("released_q 가 null 이면 이유를 지어내지 않고 미해제", () => {
    const view = grammarView(report, sections);
    if (view.status !== "ok") throw new Error("ok 여야 한다");
    expect(view.reserve[1].release).toBe("미해제 — 해제 큐를 찾지 못했다");
    expect(view.reserve[2]).toEqual({ name: "White", kind: "색", release: "해제됨 — 화면 구간 위치 불명" });
  });

  it("리포트가 없거나 못 만들었거나 reserve 가 비면 사유", () => {
    expect(grammarView(undefined, sections)).toEqual({ status: "none", reason: "컨셉 리포트가 없다" });
    expect(grammarView({ available: false, reason: "실패 X" }, sections)).toEqual({ status: "none", reason: "실패 X" });
    expect(grammarView({ available: true, reserve: [] }, sections).status).toBe("none");
  });
});
