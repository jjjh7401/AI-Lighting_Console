// PresetPoolPopup — parser/title units (hook-free, no DOM; see protocol.ts).
import { describe, expect, it } from "vitest";

import {
  parsePresetPoolResponse,
  phaserGradient,
  presetPoolErrorMessage,
  presetPopupTitle,
} from "./PresetPoolPopup";

describe("parsePresetPoolResponse — GET /api/presets/{no}의 와이어 형태", () => {
  it("parses the pool, its presets and the completeness flags", () => {
    const parsed = parsePresetPoolResponse(
      JSON.stringify({
        pool: { no: 21, name: "All 1" },
        presets: [
          { no: 1, name: "Breath FX" },
          { no: 2, name: "Snap Pulse" },
        ],
        truncated: false,
        total: 2,
      }),
    );
    expect(parsed).not.toBeNull();
    expect(parsed?.pool).toEqual({ no: 21, name: "All 1" });
    expect(parsed?.presets.map((p) => p.no)).toEqual([1, 2]);
    expect(parsed?.truncated).toBe(false);
    expect(parsed?.total).toBe(2);
  });

  it("drops a name-only slot — a tile without a REAL console number invites position addressing", () => {
    const parsed = parsePresetPoolResponse(
      JSON.stringify({ pool: { no: 21, name: "All 1" }, presets: [{ name: "ghost" }], truncated: true }),
    );
    expect(parsed?.presets).toEqual([]);
    expect(parsed?.truncated).toBe(true);
    expect(parsed?.total).toBeNull();
  });

  it("carries a well-formed palette colour and drops anything else — never a CSS injection channel", () => {
    const parsed = parsePresetPoolResponse(
      JSON.stringify({
        pool: { no: 4, name: "Color" },
        presets: [
          { no: 21, name: "Warm White", color: "#ff8c0d" },
          { no: 1, name: "FrontWarm" }, // 수동 프리셋 — 색 없음이 정직한 상태
          { no: 2, name: "evil", color: "red;background:url(x)" },
        ],
        truncated: false,
        total: 3,
      }),
    );
    expect(parsed?.presets[0].color).toBe("#ff8c0d");
    expect(parsed?.presets[1].color).toBeUndefined();
    expect(parsed?.presets[2].color).toBeUndefined();
  });

  it("carries a phaser's step colours only when every hex is well-formed and there are 2+", () => {
    const parsed = parsePresetPoolResponse(
      JSON.stringify({
        pool: { no: 4, name: "Color" },
        presets: [
          { no: 33, name: "Chase RB", colors: ["#ff0000", "#0000ff"] },
          { no: 37, name: "Rainbow", colors: ["#ff0000", "#00ff00", "#0000ff"] },
          { no: 90, name: "evil", colors: ["#ff0000", "url(x)"] }, // 한 항목만 나빠도 통째로 탈락
          { no: 91, name: "solo", colors: ["#ff0000"] }, // 1스텝은 페이저가 아니다
        ],
        truncated: false,
        total: 4,
      }),
    );
    expect(parsed?.presets[0].colors).toEqual(["#ff0000", "#0000ff"]);
    expect(parsed?.presets[1].colors).toHaveLength(3);
    expect(parsed?.presets[2].colors).toBeUndefined();
    expect(parsed?.presets[3].colors).toBeUndefined();
  });

  it("malformed JSON or a missing pool is null, never a fabricated shape", () => {
    expect(parsePresetPoolResponse("not-json")).toBeNull();
    expect(parsePresetPoolResponse(JSON.stringify({ presets: [] }))).toBeNull();
  });
});

describe("phaserGradient — 콘솔의 ⋯ 분할 원", () => {
  it("splits 2 steps into horizontal halves and 3 into thirds", () => {
    expect(phaserGradient(["#ff0000", "#0000ff"])).toBe(
      "conic-gradient(from 270deg, #ff0000 0% 50%, #0000ff 50% 100%)",
    );
    expect(phaserGradient(["#ff0000", "#00ff00", "#0000ff"])).toContain("#00ff00");
  });
});

describe("presetPoolErrorMessage — API detail 우선, 상태줄 폴백", () => {
  it("uses the API's own detail when present", () => {
    expect(presetPoolErrorMessage(404, JSON.stringify({ detail: "풀 99 없음" }))).toBe("풀 99 없음");
  });

  it("falls back to the HTTP status line", () => {
    expect(presetPoolErrorMessage(502, "gateway")).toBe("프리셋 풀을 읽지 못했습니다 (HTTP 502)");
  });
});

describe("presetPopupTitle — 개수는 아는 만큼만", () => {
  it("ready shows the pool and an honest count", () => {
    expect(
      presetPopupTitle({
        phase: "ready",
        contents: {
          pool: { no: 21, name: "All 1" },
          presets: [{ no: 1, name: "Breath FX" }],
          truncated: false,
          total: 9,
        },
      }),
    ).toBe("프리셋 풀 21 · All 1 — 9개");
  });

  it("loading/error show the pool identity only", () => {
    expect(presetPopupTitle({ phase: "loading", pool: { no: 25, name: "" } })).toBe("프리셋 풀 25");
  });
});
