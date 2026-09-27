import { describe, expect, it } from "vitest";

import {
  buildCueRequestSentences,
  cueRequestDiffLabel,
  cueRequestSentence,
  mixedColorLabel,
  mixedIntensityLabel,
  type GeneratorChange,
  type GeneratorChangeItem,
} from "./cueRequestSentence";
import vocabularyFixture from "./__fixtures__/cueRequestSentences.json";

describe("cueRequestSentence", () => {
  it("builds a group-multi intensity sentence the parser accepts", () => {
    expect(
      cueRequestSentence(3, { field: "intensity", groups: ["KEY", "BACK"], value: 95, before: "70%" }),
    ).toBe("큐 3 KEY·BACK 밝기 95%로 바꿔줘");
  });

  it("builds a cue-wide intensity sentence with no group prefix", () => {
    expect(
      cueRequestSentence(3, { field: "intensity", groups: null, value: 80, before: "60%" }),
    ).toBe("큐 3 밝기 80%로 바꿔줘");
  });

  it("builds a single-group colour sentence", () => {
    expect(
      cueRequestSentence(3, { field: "palette_primary", groups: ["BACK"], value: "앰버", before: "—" }),
    ).toBe("큐 3 BACK 컬러 앰버로 바꿔줘");
  });

  it("builds a cue-wide effect/preset-name sentence", () => {
    expect(
      cueRequestSentence(3, { field: "effect", value: "CHASE", before: "—" }),
    ).toBe("큐 3 이펙트 CHASE로 바꿔줘");
  });

  it("builds a cue-wide movement/preset-name sentence", () => {
    expect(
      cueRequestSentence(3, { field: "movement", value: "Sweep L", before: "—" }),
    ).toBe("큐 3 무브먼트 Sweep L로 바꿔줘");
  });

  it("builds a fade sentence", () => {
    expect(cueRequestSentence(3, { field: "fade_seconds", value: 5, before: "2초" })).toBe(
      "큐 3 페이드 5초로 바꿔줘",
    );
  });

  it("builds a trans sentence", () => {
    expect(cueRequestSentence(3, { field: "trans", value: "XFADE", before: "SNAP" })).toBe(
      "큐 3 전환을 XFADE로 바꿔줘",
    );
  });

  it("builds a tracking sentence with the 으로 particle (t466/t470)", () => {
    expect(
      cueRequestSentence(3, { field: "tracking", value: "Block", before: "Track" }),
    ).toBe("큐 3 트래킹 Block으로 바꿔줘");
  });

  it("builds a tracking sentence with the 로 particle for a no-batchim value", () => {
    expect(
      cueRequestSentence(3, { field: "tracking", value: "Release", before: "Track" }),
    ).toBe("큐 3 트래킹 Release로 바꿔줘");
  });

  it("builds a MIB sentence, using the 없음 label for none", () => {
    expect(cueRequestSentence(3, { field: "mib_mode", value: "dark", before: "없음" })).toBe(
      "큐 3 MIB dark로 설정",
    );
    expect(cueRequestSentence(3, { field: "mib_mode", value: "none", before: "dark" })).toBe(
      "큐 3 MIB 없음으로 설정",
    );
  });

  it("builds a phaser preset-name sentence", () => {
    expect(
      cueRequestSentence(3, { field: "phaser", value: "Breathe Soft", before: "—" }),
    ).toBe("큐 3 페이저 Breathe Soft로 바꿔줘");
  });

  it("builds a position preset sentence with its pool-2 number", () => {
    expect(
      cueRequestSentence(3, {
        field: "position",
        value: "Sweep L",
        presetNo: "2.11",
        before: "—",
      }),
    ).toBe("큐 3 포지션 2.11 Sweep L로 바꿔줘");
  });

  it("renders the REQ-091 diff-line label format", () => {
    expect(
      cueRequestDiffLabel({ field: "intensity", groups: ["BACK"], value: 95, before: "70%" }),
    ).toBe("~ BACK 밝기 70% → 95%");
    expect(cueRequestDiffLabel({ field: "fade_seconds", value: 5, before: "2초" })).toBe(
      "~ 페이드 2초 → 5초",
    );
  });

  it("renders diff labels for the t466/t470 fields", () => {
    expect(
      cueRequestDiffLabel({ field: "tracking", value: "Block", before: "Track" }),
    ).toBe("~ 트래킹 Track → Block");
    expect(cueRequestDiffLabel({ field: "mib_mode", value: "dark", before: "없음" })).toBe(
      "~ MIB 없음 → dark",
    );
    expect(
      cueRequestDiffLabel({ field: "phaser", value: "Breathe Soft", before: "—" }),
    ).toBe("~ 페이저 — → Breathe Soft");
    expect(
      cueRequestDiffLabel({
        field: "position",
        value: "Sweep L",
        presetNo: "2.11",
        before: "—",
      }),
    ).toBe("~ 포지션 — → 2.11 Sweep L");
  });
});

describe("buildCueRequestSentences", () => {
  const items: GeneratorChangeItem[] = [
    { id: "a", change: { field: "intensity", groups: ["KEY", "BACK"], value: 95, before: "70%" } },
    { id: "b", change: { field: "fade_seconds", value: 5, before: "2초" } },
  ];

  it("emits one sentence per diff line, in order", () => {
    expect(buildCueRequestSentences(3, items, "")).toEqual([
      "큐 3 KEY·BACK 밝기 95%로 바꿔줘",
      "큐 3 페이드 5초로 바꿔줘",
    ]);
  });

  it("appends free text to the LAST sentence only (REQ-101)", () => {
    const sentences = buildCueRequestSentences(3, items, "그리고 이 구간 전체를 반 박자 당겨줘");
    expect(sentences).toHaveLength(2);
    expect(sentences[0]).toBe("큐 3 KEY·BACK 밝기 95%로 바꿔줘");
    expect(sentences[1]).toBe("큐 3 페이드 5초로 바꿔줘 그리고 이 구간 전체를 반 박자 당겨줘");
  });

  it("sends nothing when there are no diff lines, even with free text", () => {
    expect(buildCueRequestSentences(3, [], "그리고 반 박자 당겨줘")).toEqual([]);
  });

  it("ignores whitespace-only free text", () => {
    expect(buildCueRequestSentences(3, items, "   ")).toEqual([
      "큐 3 KEY·BACK 밝기 95%로 바꿔줘",
      "큐 3 페이드 5초로 바꿔줘",
    ]);
  });
});

describe("mixedIntensityLabel", () => {
  it("returns the shared value when all selected groups agree", () => {
    expect(mixedIntensityLabel([70, 70, 70])).toBe("70%");
  });

  it("returns 혼합 when selected groups disagree", () => {
    expect(mixedIntensityLabel([70, 90])).toBe("혼합");
  });

  it("returns the empty placeholder when nothing is selected", () => {
    expect(mixedIntensityLabel([])).toBe("—");
  });
});

describe("AC-LDDESIGN-039 — 어휘 공유 고정(fixture) — TS 빌더 쪽", () => {
  // 이 fixture(cueRequestSentences.json)는 pytest
  // (server/tests/test_plan_cue_generator_vocabulary_t460.py)와 공유한다 —
  // 여기서는 TS 빌더가 만드는 문장이 fixture 문장과 바이트 동일한지만
  // 검증한다; 그 문장이 파서 기대 changes 로 풀리는지는 pytest 쪽이 잰다.
  it("produces exactly the fixture sentence for every representative operation", () => {
    for (const item of vocabularyFixture as {
      name: string;
      cue: number;
      change: GeneratorChange;
      sentence: string;
    }[]) {
      expect(cueRequestSentence(item.cue, item.change)).toBe(item.sentence);
    }
  });
});

describe("mixedColorLabel", () => {
  it("returns the shared colour when all selected groups agree", () => {
    expect(mixedColorLabel(["앰버", "앰버"])).toBe("앰버");
  });

  it("returns 혼합 2색 when two colours differ (REQ-088)", () => {
    expect(mixedColorLabel(["앰버", "블루"])).toBe("혼합 2색");
  });

  it("ignores groups with no colour on record", () => {
    expect(mixedColorLabel([undefined, "앰버"])).toBe("앰버");
  });

  it("returns the empty placeholder when nothing is known", () => {
    expect(mixedColorLabel([undefined, undefined])).toBe("—");
  });
});
