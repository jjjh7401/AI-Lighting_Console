// 카드 t654 — 수정 요청 생성기의 「이전 값」 라벨이 페이드 원시 실수를 그대로 찍는다
// (`3.1573333333333267초`). 시안 tc 표기(소수 둘째, 뒤 0 제거)로 맞춘다.
// 표시 전용이다 — 저장값(`fade_seconds`)과 송신 값(`value`)은 바꾸지 않는다.
import { describe, expect, it } from "vitest";

import type { SongTimelineSection, SongTimelineView } from "../protocol";
import { fadeBeforeLabel } from "./PlanCueRequestGenerator";
import REQUERY from "./__fixtures__/requeryTimeline.t490.json";

const SECTION = (REQUERY as unknown as SongTimelineView).sections[0] as SongTimelineSection;

describe("수정 요청 생성기 이전 값 — 페이드 표시 (카드 t654)", () => {
  it("원시 실수는 소수 둘째 자리로 맞춘다", () => {
    expect(fadeBeforeLabel({ ...SECTION, fade_seconds: 3.1573333333333267 })).toBe("3.16초");
  });

  it("뒤의 0 은 뗀다", () => {
    expect(fadeBeforeLabel({ ...SECTION, fade_seconds: 2 })).toBe("2초");
    expect(fadeBeforeLabel({ ...SECTION, fade_seconds: 2.5 })).toBe("2.5초");
    expect(fadeBeforeLabel({ ...SECTION, fade_seconds: 10 })).toBe("10초");
  });

  it("값이 없으면 대시다", () => {
    expect(fadeBeforeLabel({ ...SECTION, fade_seconds: null })).toBe("—");
  });
});
