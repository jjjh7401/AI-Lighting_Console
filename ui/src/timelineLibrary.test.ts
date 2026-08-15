// Pure-parser tests for the timeline library client (no DOM harness).
import { describe, expect, it } from "vitest";

import {
  parseTimelineListResponse,
  parseTimelineLoadResponse,
  timelineItemMeta,
} from "./timelineLibrary";

const ITEM = {
  id: "abc123",
  name: "밝은 팝 무대 v1",
  saved_at: "2026-08-14T12:00:00+00:00",
  song_title: "Design Interview",
  sequence_number: 210,
  lifecycle: "verified",
  section_count: 5,
};

describe("parseTimelineListResponse", () => {
  it("parses a well-formed listing", () => {
    const items = parseTimelineListResponse(JSON.stringify({ items: [ITEM] }));
    expect(items).toHaveLength(1);
    expect(items?.[0].name).toBe("밝은 팝 무대 v1");
    expect(items?.[0].sequence_number).toBe(210);
  });

  it("returns null on any shape mismatch instead of fabricating an empty library", () => {
    expect(parseTimelineListResponse("not json")).toBeNull();
    expect(parseTimelineListResponse(JSON.stringify({}))).toBeNull();
    expect(parseTimelineListResponse(JSON.stringify({ items: [{ name: 1 }] }))).toBeNull();
  });
});

describe("parseTimelineLoadResponse", () => {
  it("returns the timeline payload when sections are present", () => {
    const timeline = { song_title: "t", sequence_number: 210, lifecycle: "verified", sections: [] };
    expect(parseTimelineLoadResponse(JSON.stringify({ ok: true, timeline }))?.sequence_number).toBe(
      210,
    );
  });

  it("rejects payloads without a sections array carrier", () => {
    expect(parseTimelineLoadResponse(JSON.stringify({ timeline: { a: 1 } }))).toBeNull();
    expect(parseTimelineLoadResponse("broken")).toBeNull();
  });
});

describe("timelineItemMeta", () => {
  it("joins saved time, sequence, and section count", () => {
    expect(timelineItemMeta(ITEM)).toBe("2026-08-14 12:00:00Z · Sequence 210 · 구간 5");
  });
});
