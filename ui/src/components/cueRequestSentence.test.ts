import { describe, expect, it } from "vitest";

import {
  buildCueRequestSentences,
  cueRequestDiffLabel,
  cueRequestSentence,
  mixedColorLabel,
  mixedIntensityLabel,
  type GeneratorChangeItem,
} from "./cueRequestSentence";

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

  it("renders the REQ-091 diff-line label format", () => {
    expect(
      cueRequestDiffLabel({ field: "intensity", groups: ["BACK"], value: 95, before: "70%" }),
    ).toBe("~ BACK 밝기 70% → 95%");
    expect(cueRequestDiffLabel({ field: "fade_seconds", value: 5, before: "2초" })).toBe(
      "~ 페이드 2초 → 5초",
    );
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
