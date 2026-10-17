// SPEC-LDRHYTHM-001 재실행 2 N3 — 새 분석 작업본 구간에 큐 번호가 없을 때의 화면 표시.
import { describe, expect, it } from "vitest";

import type { SongTimelineSection } from "../protocol";
import { cueLabel, tcSourceText } from "./CueSheetTimeline";

function section(extra: Record<string, unknown>): SongTimelineSection {
  return { index: 1, label: "D1", start_ms: 0, d_level: 1, ...extra } as unknown as SongTimelineSection;
}

describe("N3 — 새 분석 작업본 구간에 큐 번호가 없을 때", () => {
  it("cueLabel 은 키가 없거나 null 이면 Qundefined·Qnull 대신 빈 칸을 쓴다", () => {
    expect(cueLabel(section({}))).toBe("Q—");
    expect(cueLabel(section({ cue_number: null }))).toBe("Q—");
    expect(cueLabel(section({ cue_number: 10 }))).toBe("Q010");
  });

  it("TC_SOURCE 는 출처가 없으면 반영할 타임코드 번호를, 둘 다 없으면 빈 칸을 보인다", () => {
    expect(tcSourceText({ tc_source: "LTC", timecode_number: 5 })).toBe("LTC");
    expect(tcSourceText({ timecode_number: 5 })).toBe("Timecode 5");
    expect(tcSourceText({ timecode_number: null })).toBe("—");
    expect(tcSourceText({} as never)).toBe("—");
  });
});
