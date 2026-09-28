// t485 — 컨셉 패널 탭 1 인과 불릿(SPEC-LDDESIGN-001 REQ-013·032·080, AC-018 잔여).
// 원문은 서버 `concept_bullet.text` 그대로다 — 줄바꿈으로 불릿을 나눌 뿐 글자는 바꾸지 않는다.
import { describe, expect, it } from "vitest";

import type { SongTimelineConceptBullet } from "../protocol";
import { VERBATIM_BADGE, conceptBulletView } from "./conceptBullet";
import { NO_DATA } from "./runbookM7";

const CAUSAL = "이 곡은 이별 노래다 → 그래서 주조색은 차가운 파랑\n\n  → 후렴에서만 흰색을 쓴다  ";

describe("conceptBulletView", () => {
  it("keeps every line byte-for-byte and only drops blank lines", () => {
    const bullet: SongTimelineConceptBullet = {
      available: true,
      text: CAUSAL,
      origin: "free_text",
      origin_label: "인터뷰 Q1 — 직접 입력",
    };
    const view = conceptBulletView(bullet);
    expect(view).toEqual({
      status: "ok",
      lines: ["이 곡은 이별 노래다 → 그래서 주조색은 차가운 파랑", "  → 후렴에서만 흰색을 쓴다  "],
      badge: VERBATIM_BADGE,
      origin: "인터뷰 Q1 — 직접 입력",
    });
    // 합치면 빈 줄만 빠진 원문이 된다 — 윤문·요약 0.
    if (view.status === "ok") {
      expect(view.lines.join("\n")).toBe(CAUSAL.split("\n").filter((line) => line.trim() !== "").join("\n"));
    }
  });

  it("badge text is fixed", () => {
    expect(VERBATIM_BADGE).toBe("원문 그대로");
  });

  it("shows the server reason when there is no source text", () => {
    expect(conceptBulletView({ available: false, reason: "인터뷰 Q1(컨셉) 기록이 없다" })).toEqual({
      status: "none",
      reason: "인터뷰 Q1(컨셉) 기록이 없다",
    });
  });

  it("an old payload without the key says the server did not send it", () => {
    expect(conceptBulletView(undefined)).toEqual({
      status: "none",
      reason: "서버가 인과 불릿 원문을 보내지 않았다(예전 페이로드)",
    });
  });

  it("an available flag with blank text is not rendered as a bullet", () => {
    expect(conceptBulletView({ available: true, text: " \n " }).status).toBe("none");
  });

  it("reasons never carry the no-data marker themselves (the panel adds it once)", () => {
    const view = conceptBulletView({ available: false, reason: "x" });
    expect(view.status === "none" && view.reason.includes(NO_DATA)).toBe(false);
  });
});
