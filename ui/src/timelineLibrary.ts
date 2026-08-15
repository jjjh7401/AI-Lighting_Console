// Director-timeline library client (save / list / load / delete named
// versions — 여러 곡을 미리 계획하고 버전별로 보관/불러오기, user request
// 2026-08-14). Pure parsers + thin fetch wrappers, matching the
// PaperworkPanel split so everything but fetch() is unit-testable without a
// DOM harness.
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

export async function loadTimelineFromLibrary(id: string): Promise<SongTimelineView | null> {
  try {
    const response = await fetch(apiUrl(`/api/timelines/${id}/load`), { method: "POST" });
    if (!response.ok) return null;
    return parseTimelineLoadResponse(await response.text());
  } catch {
    return null;
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
