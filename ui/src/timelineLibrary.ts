// Director-timeline library client (save / list / load / delete named
// versions — 여러 곡을 미리 계획하고 버전별로 보관/불러오기, user request
// 2026-08-14). Pure parsers + thin fetch wrappers, so everything but
// fetch() is unit-testable without a DOM harness.
import { apiUrl } from "./launchContext";
import type { SongTimelineView } from "./protocol";

export interface TimelineLibraryItem {
  id: string;
  name: string;
  saved_at: string | null;
  song_title: string | null;
  sequence_number: number | null;
  lifecycle: string | null;
  section_count: number;
}

// -- pure parsers (no fetch, no DOM) ------------------------------------------

/** Parses GET /api/timelines. `null` on any shape mismatch — the caller
 * degrades to "could not load", never a fabricated empty library. */
export function parseTimelineListResponse(text: string): TimelineLibraryItem[] | null {
  let data: unknown;
  try {
    data = JSON.parse(text);
  } catch {
    return null;
  }
  if (typeof data !== "object" || data === null || !("items" in data)) return null;
  const items = data.items;
  if (!Array.isArray(items)) return null;
  const parsed: TimelineLibraryItem[] = [];
  for (const item of items) {
    if (typeof item !== "object" || item === null) return null;
    const id = "id" in item ? item.id : null;
    const name = "name" in item ? item.name : null;
    if (typeof id !== "string" || typeof name !== "string") return null;
    const savedAt = "saved_at" in item ? item.saved_at : null;
    const songTitle = "song_title" in item ? item.song_title : null;
    const sequenceNumber = "sequence_number" in item ? item.sequence_number : null;
    const lifecycle = "lifecycle" in item ? item.lifecycle : null;
    const sectionCount = "section_count" in item ? item.section_count : 0;
    parsed.push({
      id,
      name,
      saved_at: typeof savedAt === "string" ? savedAt : null,
      song_title: typeof songTitle === "string" ? songTitle : null,
      sequence_number: typeof sequenceNumber === "number" ? sequenceNumber : null,
      lifecycle: typeof lifecycle === "string" ? lifecycle : null,
      section_count: typeof sectionCount === "number" ? sectionCount : 0,
    });
  }
  return parsed;
}

/** Parses POST /api/timelines/{id}/load — the full timeline payload the UI
 * applies locally (the server store is already updated for replays). The
 * payload is server-authored (same producer as the `song_timeline` WS event),
 * so after the shape check it is adopted under the shared view type. */
export function parseTimelineLoadResponse(text: string): SongTimelineView | null {
  let data: unknown;
  try {
    data = JSON.parse(text);
  } catch {
    return null;
  }
  if (typeof data !== "object" || data === null || !("timeline" in data)) return null;
  const timeline = data.timeline;
  if (typeof timeline !== "object" || timeline === null || !("sections" in timeline)) return null;
  // Server-authored projection, structurally gated above — same trust level
  // as the song_timeline WebSocket frame the reducer already accepts.
  const view = timeline as SongTimelineView;
  return view;
}

/** POST /api/timelines/{id}/load 가 지금 작업본을 자동 백업했으면 그 이름. 아니면 `null`. */
export function parseTimelineLoadBackupName(text: string): string | null {
  try {
    const backup: unknown = (JSON.parse(text) as { backup?: unknown })?.backup;
    if (typeof backup !== "object" || backup === null || !("name" in backup)) return null;
    return typeof backup.name === "string" ? backup.name : null;
  } catch {
    return null;
  }
}

/** 서버가 불러오기 전에 지금 작업본을 백업하지 **않은** 이유(``backup_skipped``). */
export type TimelineLoadBackupSkip =
  | { reason: "same_as_saved"; savedAs: string | null }
  | { reason: "no_unsaved_edits" };

/** POST /api/timelines/{id}/load 의 ``backup_skipped``. 없거나 모양이 다르면 `null`. */
export function parseTimelineLoadBackupSkip(text: string): TimelineLoadBackupSkip | null {
  try {
    const skip: unknown = (JSON.parse(text) as { backup_skipped?: unknown })?.backup_skipped;
    if (typeof skip !== "object" || skip === null || !("reason" in skip)) return null;
    if (skip.reason === "no_unsaved_edits") return { reason: "no_unsaved_edits" };
    if (skip.reason !== "same_as_saved") return null;
    const savedAs = "saved_as" in skip && typeof skip.saved_as === "string" ? skip.saved_as : null;
    return { reason: "same_as_saved", savedAs };
  } catch {
    return null;
  }
}

/** 불러오기 실패 응답(``{detail: {message}}``)이 말한 이유. 없으면 `null`(화면은 일반 문구). */
export function parseTimelineLoadError(text: string): string | null {
  try {
    const detail: unknown = (JSON.parse(text) as { detail?: unknown })?.detail;
    if (typeof detail !== "object" || detail === null || !("message" in detail)) return null;
    return typeof detail.message === "string" && detail.message.trim() ? detail.message : null;
  } catch {
    return null;
  }
}

/** 불러오기 성공 안내. 서버가 지금 작업본을 백업했으면 어디에 남았는지, 건너뛰었으면 왜인지 말한다.
 * `asked` 는 이 불러오기 전에 미저장 확인 창을 띄웠는지 — 띄웠다면 백업 얘기를 빠뜨리지 않는다
 * (2026-10-20 실측: 확인 창은 백업을 약속했는데 항목이 생기지 않았고 안내도 이유를 말하지 않았다). */
export function timelineLoadedNotice(
  backupName: string | null,
  skip: TimelineLoadBackupSkip | null = null,
  asked = false,
): string {
  const loaded = "타임라인을 불러왔습니다 — 감독 타임라인에 표시됩니다.";
  if (backupName !== null) {
    return `${loaded} 저장하지 않았던 작업본은 「${backupName}」로 백업했습니다.`;
  }
  if (skip?.reason === "same_as_saved") {
    const where = skip.savedAs === null ? "라이브러리에" : `「${skip.savedAs}」로`;
    return `${loaded} 같은 내용이 이미 ${where} 저장돼 있어 백업을 따로 만들지 않았어요.`;
  }
  if (asked) {
    return `${loaded} 서버의 작업본에는 저장하지 않은 수정이 없어 백업을 따로 만들지 않았어요.`;
  }
  return loaded;
}

// WT-load-unsaved-guard — 「수정됨 · 미저장」 작업본 위에 불러오기를 누르면 먼저 묻는다
// (2026-10-20 실측: 확인 창 없이 덮여 수정이 사라졌다). 백업 자체는 서버가 하고, 같은 내용이 이미
// 저장돼 있으면 새로 남기지 않는다 — 확인 창도 그 경우를 거짓 없이 말한다.
export const UNSAVED_LOAD_CONFIRM =
  "저장하지 않은 수정이 있어요. 불러오기 전에 지금 작업본을 자동 백업으로 남겨요" +
  "(같은 내용이 이미 저장돼 있으면 새로 만들지 않아요). 불러올까요?";

/** 불러와도 되면 `true`. 미저장 작업본이면 `confirm` 으로 묻고, 취소하면 `false`(불러오지 않음).
 * `savedTimeline` 은 이 창에서 마지막으로 저장한 그 작업본 — 그대로면 다시 묻지 않는다. */
export function confirmLoadIfUnsaved(
  timeline: SongTimelineView | null,
  savedTimeline: SongTimelineView | null,
  confirm: (message: string) => boolean,
): boolean {
  if (timeline?.draft?.dirty !== true || timeline === savedTimeline) return true;
  return confirm(UNSAVED_LOAD_CONFIRM);
}

/** The one-line entry label: "저장시각 · Sequence N · 구간 5". */
export function timelineItemMeta(item: TimelineLibraryItem): string {
  const parts: string[] = [];
  if (item.saved_at) parts.push(item.saved_at.replace("T", " ").replace("+00:00", "Z"));
  if (item.sequence_number !== null) parts.push(`Sequence ${item.sequence_number}`);
  parts.push(`구간 ${item.section_count}`);
  return parts.join(" · ");
}

// -- fetch wrappers (thin — call + parse, no React) ---------------------------

export async function fetchTimelineList(): Promise<TimelineLibraryItem[] | null> {
  try {
    const response = await fetch(apiUrl("/api/timelines"));
    if (!response.ok) return null;
    return parseTimelineListResponse(await response.text());
  } catch {
    return null;
  }
}

export async function saveTimelineToLibrary(name: string): Promise<boolean> {
  try {
    const response = await fetch(apiUrl("/api/timelines"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });
    return response.ok;
  } catch {
    return false;
  }
}

export type TimelineLoadResult =
  | {
      ok: true;
      timeline: SongTimelineView;
      backupName: string | null;
      backupSkip: TimelineLoadBackupSkip | null;
    }
  | { ok: false; message: string | null };

/** 실패면 서버가 말한 이유(``backup_failed`` 등)를 `message` 에 싣는다 — 없으면 `null`. */
export async function loadTimelineFromLibrary(id: string): Promise<TimelineLoadResult> {
  try {
    const response = await fetch(apiUrl(`/api/timelines/${id}/load`), { method: "POST" });
    const text = await response.text();
    if (!response.ok) return { ok: false, message: parseTimelineLoadError(text) };
    const timeline = parseTimelineLoadResponse(text);
    if (timeline === null) return { ok: false, message: null };
    return {
      ok: true,
      timeline,
      backupName: parseTimelineLoadBackupName(text),
      backupSkip: parseTimelineLoadBackupSkip(text),
    };
  } catch {
    return { ok: false, message: null };
  }
}

export async function deleteTimelineFromLibrary(id: string): Promise<boolean> {
  try {
    const response = await fetch(apiUrl(`/api/timelines/${id}`), { method: "DELETE" });
    return response.ok;
  } catch {
    return false;
  }
}
