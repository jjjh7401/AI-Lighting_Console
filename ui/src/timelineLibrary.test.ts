// Pure-parser tests for the timeline library client (no DOM harness).
import { describe, expect, it, vi } from "vitest";

import type { SongTimelineView } from "./protocol";
import {
  confirmLoadIfUnsaved,
  parseTimelineListResponse,
  parseTimelineLoadBackupName,
  parseTimelineLoadBackupSkip,
  parseTimelineLoadError,
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

  // 2026-10-20 헤드리스 E2E 실측: 확인 창에서 백업을 약속했는데 백업 항목이 생기지 않았고(라이브러리
  // 106→106) 안내도 이유를 말하지 않았다. 서버가 백업을 건너뛴 이유를 그대로 전한다.
  it("says the draft is already saved under that name when the server skipped the backup", () => {
    const text = JSON.stringify({
      ok: true,
      timeline: { sections: [] },
      backup: null,
      backup_skipped: { reason: "same_as_saved", saved_as: "LOVE ATTACK (자동 v39)" },
    });
    const skip = parseTimelineLoadBackupSkip(text);
    expect(skip).toEqual({ reason: "same_as_saved", savedAs: "LOVE ATTACK (자동 v39)" });
    const notice = timelineLoadedNotice(parseTimelineLoadBackupName(text), skip, true);
    expect(notice).toContain("같은 내용이 이미 「LOVE ATTACK (자동 v39)」로 저장돼 있어");
    expect(notice).toContain("백업을 따로 만들지 않았어요");
    expect(notice).not.toContain("백업했습니다");
  });

  it("says there was nothing to back up when the director was asked but the server saw no edits", () => {
    const text = JSON.stringify({
      ok: true,
      timeline: { sections: [] },
      backup: null,
      backup_skipped: { reason: "no_unsaved_edits" },
    });
    const skip = parseTimelineLoadBackupSkip(text);
    expect(timelineLoadedNotice(null, skip, true)).toContain("백업을 따로 만들지 않았어요");
    // 묻지 않았으면(깨끗한 판) 굳이 백업 얘기를 꺼내지 않는다.
    expect(timelineLoadedNotice(null, skip, false)).toBe(
      "타임라인을 불러왔습니다 — 감독 타임라인에 표시됩니다.",
    );
  });

  it("reads no skip reason from older or malformed responses", () => {
    expect(parseTimelineLoadBackupSkip(JSON.stringify({ backup: null }))).toBeNull();
    expect(parseTimelineLoadBackupSkip("broken")).toBeNull();
    expect(parseTimelineLoadBackupSkip(JSON.stringify({ backup_skipped: { reason: 3 } }))).toBeNull();
  });
});

describe("UNSAVED_LOAD_CONFIRM", () => {
  // 확인 창이 「반드시 백업한다」고 단정하면, 같은 내용이 이미 저장돼 있어 서버가 건너뛸 때 거짓이 된다.
  it("does not promise a new backup when an identical saved copy may already exist", () => {
    expect(UNSAVED_LOAD_CONFIRM).toContain("같은 내용이 이미 저장돼 있으면");
  });
});

describe("parseTimelineLoadError", () => {
  it("surfaces the server's own reason (e.g. backup_failed) instead of a generic failure", () => {
    const text = JSON.stringify({
      detail: {
        error: "backup_failed",
        message: "저장하지 않은 지금 작업본을 백업하지 못해 불러오지 않았습니다(OSError).",
      },
    });
    expect(parseTimelineLoadError(text)).toBe(
      "저장하지 않은 지금 작업본을 백업하지 못해 불러오지 않았습니다(OSError).",
    );
  });

  it("falls back to null when the server gave no message", () => {
    expect(parseTimelineLoadError("Internal Server Error")).toBeNull();
    expect(parseTimelineLoadError(JSON.stringify({ detail: "x" }))).toBeNull();
  });
});

describe("timelineItemMeta", () => {
  it("joins saved time, sequence, and section count", () => {
    expect(timelineItemMeta(ITEM)).toBe("2026-08-14 12:00:00Z · Sequence 210 · 구간 5");
  });
});
