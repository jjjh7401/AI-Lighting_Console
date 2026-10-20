// Pure-parser tests for the timeline library client (no DOM harness).
import { describe, expect, it, vi } from "vitest";

import type { SongTimelineView } from "./protocol";
import {
  confirmLoadIfUnsaved,
  parseTimelineListResponse,
  parseTimelineLoadBackupName,
  parseTimelineLoadResponse,
  timelineItemMeta,
  timelineLoadedNotice,
  UNSAVED_LOAD_CONFIRM,
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

// WT-load-unsaved-guard — 「수정됨 · 미저장」 작업본 위에 불러오기를 누르면 먼저 묻는다
// (2026-10-20 실측: 확인 창 없이 덮여 수정이 사라졌다). 취소하면 불러오지 않는다.
describe("confirmLoadIfUnsaved", () => {
  const base = { song_title: "t", sequence_number: 210, lifecycle: "verified", sections: [] };
  const dirty = {
    ...base,
    draft: { dirty: true, depth: 3, last_change: [] },
  } as unknown as SongTimelineView;
  const clean = {
    ...base,
    draft: { dirty: false, depth: 0, last_change: [] },
  } as unknown as SongTimelineView;

  it("asks before replacing an unsaved draft, and cancel means no load", () => {
    const confirm = vi.fn(() => false);
    expect(confirmLoadIfUnsaved(dirty, null, confirm)).toBe(false);
    expect(confirm).toHaveBeenCalledWith(UNSAVED_LOAD_CONFIRM);
    expect(UNSAVED_LOAD_CONFIRM).toContain("저장하지 않은 수정");
    expect(UNSAVED_LOAD_CONFIRM).toContain("자동 백업");
  });

  it("loads when the director agrees", () => {
    expect(confirmLoadIfUnsaved(dirty, null, () => true)).toBe(true);
  });

  it("does not ask for a clean draft, no draft, or a draft just saved as-is", () => {
    const confirm = vi.fn(() => false);
    expect(confirmLoadIfUnsaved(clean, null, confirm)).toBe(true);
    expect(confirmLoadIfUnsaved(null, null, confirm)).toBe(true);
    expect(confirmLoadIfUnsaved(dirty, dirty, confirm)).toBe(true);
    expect(confirm).not.toHaveBeenCalled();
  });
});

describe("timelineLoadedNotice", () => {
  it("names the auto backup the server left", () => {
    const text = JSON.stringify({
      ok: true,
      timeline: { sections: [] },
      backup: { id: "b1", name: "Aside v5 불러오기 전 백업 (자동 v1)" },
    });
    expect(timelineLoadedNotice(parseTimelineLoadBackupName(text))).toContain(
      "「Aside v5 불러오기 전 백업 (자동 v1)」",
    );
  });

  it("stays the plain notice when nothing was backed up", () => {
    const text = JSON.stringify({ ok: true, timeline: { sections: [] }, backup: null });
    expect(parseTimelineLoadBackupName(text)).toBeNull();
    expect(timelineLoadedNotice(null)).toBe("타임라인을 불러왔습니다 — 감독 타임라인에 표시됩니다.");
  });
});

describe("timelineItemMeta", () => {
  it("joins saved time, sequence, and section count", () => {
    expect(timelineItemMeta(ITEM)).toBe("2026-08-14 12:00:00Z · Sequence 210 · 구간 5");
  });
});
