// PresetPoolPopup — parser/title units (hook-free, no DOM; see protocol.ts).
import { describe, expect, it } from "vitest";

import {
  parsePresetPoolResponse,
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

  it("malformed JSON or a missing pool is null, never a fabricated shape", () => {
    expect(parsePresetPoolResponse("not-json")).toBeNull();
    expect(parsePresetPoolResponse(JSON.stringify({ presets: [] }))).toBeNull();
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
