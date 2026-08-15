import type { SongTimelineView } from "../protocol";

/** Visual-only rehearsal fixture. It never crosses the WebSocket boundary and
 * must always be rendered with `isExample` so it cannot be mistaken for a
 * console-backed plan. */
export const SONG_TIMELINE_EXAMPLE: SongTimelineView = {
  song_title: "NEON RUN · SAMPLE",
  sequence_name: "Sequence 120",
  sequence_number: 120,
  timing_mode: "timecode",
  timecode_number: 901,
  lifecycle: "pending_approval",
  approval: "pending_review",
  director_decisions: [
    { step: "Q1 CONCEPT", axis: "texture", value: "neon", confirmed: true, source: "example" },
    { step: "Q2 PALETTE", axis: "palette", value: ["cyan", "magenta"], confirmed: true, source: "example" },
    { step: "Q3 CLIMAX", axis: "accent", value: "final chorus", confirmed: true, source: "example" },
    { step: "Q4 SPACE", axis: "position", value: "narrow to wide", confirmed: true, source: "example" },
    { step: "Q5 TEXTURE", axis: "fx", value: "soft build", confirmed: true, source: "example" },
  ],
  sections: [
    { index: 1, label: "INTRO", start_ms: 0, cue_number: 1, d_level: 2, palette: ["blue", "white"], position: "Center", texture: "long fade", fx: [], accents: [], mib: false, trig_time_seconds: 0 },
    { index: 2, label: "VERSE", start_ms: 24_000, cue_number: 2, d_level: 3, palette: ["cyan", "white"], position: "Vocal DSC", texture: "build", fx: ["dimmer chase"], accents: [], mib: true, trig_time_seconds: 24 },
    { index: 3, label: "CHORUS", start_ms: 48_000, cue_number: 3, d_level: 4, palette: ["cyan", "magenta"], position: "Fan Out", texture: "snap", fx: ["dimmer chase"], accents: ["chorus hit"], mib: true, trig_time_seconds: 48 },
    { index: 4, label: "FINAL", start_ms: 72_000, cue_number: 4, d_level: 5, palette: ["magenta", "white"], position: "Ring In", texture: "snap", fx: ["dimmer chase", "pan sweep"], accents: ["final accent"], mib: true, trig_time_seconds: 72 },
  ],
  lint: [],
  unresolved: [],
  disabled: [{ axis: "fx", section_index: null, reason: "strobe capability not available" }],
  readback: { verified: null, message: "샘플은 콘솔에 적용하거나 검증하지 않습니다." },
};
