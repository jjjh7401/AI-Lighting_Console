import { describe, expect, it } from "vitest";

import type { SongTimelineConceptRow, SongTimelineReserveItem, SongTimelineSection } from "../protocol";
import {
  chorusReversalWarning,
  deriveWarningsForChange,
  headroomWarning,
  mibLiveWarning,
  reserveViolationWarning,
} from "./cueRequestWarnings";

function section(overrides: Partial<SongTimelineSection>): SongTimelineSection {
  return {
    index: 0,
    label: "Chorus",
    start_ms: 0,
    cue_number: 1,
    d_level: 3,
    palette: [],
    position: "—",
    texture: "—",
    fx: [],
    accents: [],
    mib: false,
    trig_time_seconds: null,
    ...overrides,
  };
}

describe("chorusReversalWarning", () => {
  const c4 = section({ index: 3, cue_number: 4, role: "chorus", d_level: 4 }); // 80%
  const c5 = section({ index: 4, cue_number: 5, role: "chorus", d_level: 4 }); // 80%
  const all = [c4, c5];

  it("warns when the proposed value exceeds a later chorus", () => {
    expect(chorusReversalWarning(c4, all, 95)).toMatch(/뒤 후렴\(80%\)보다 밝아져/);
  });

  it("does not warn when the proposed value stays at or below later choruses", () => {
    expect(chorusReversalWarning(c4, all, 70)).toBeNull();
  });

  it("is n/a for a non-chorus section (role missing)", () => {
    const verse = section({ index: 0, cue_number: 1 });
    expect(chorusReversalWarning(verse, all, 100)).toBeNull();
  });

  it("is n/a when there is no later chorus", () => {
    expect(chorusReversalWarning(c5, all, 100)).toBeNull();
  });
});

describe("reserveViolationWarning", () => {
  const reserve: SongTimelineReserveItem[] = [
    { name: "BLIND", kind: "group", released_q: 23, screen_position: 5 },
    { name: "흰색", kind: "color", released_q: null, screen_position: null },
  ];

  it("warns when used before its release cue", () => {
    expect(reserveViolationWarning(10, reserve, "BLIND")).toMatch(/해제 큐\(Q23\) 이전/);
  });

  it("does not warn at or after the release cue", () => {
    expect(reserveViolationWarning(23, reserve, "BLIND")).toBeNull();
    expect(reserveViolationWarning(30, reserve, "BLIND")).toBeNull();
  });

  it("warns 미해제 when the colour has never been released", () => {
    expect(reserveViolationWarning(1, reserve, "흰색")).toMatch(/미해제/);
  });

  it("is silent for a name that is not a reserve item", () => {
    expect(reserveViolationWarning(1, reserve, "FOH")).toBeNull();
  });

  it("is silent when there is no reserve list at all", () => {
    expect(reserveViolationWarning(1, undefined, "BLIND")).toBeNull();
  });
});

describe("headroomWarning / mibLiveWarning — consume, never recompute (AC-040)", () => {
  const lowHeadroomRow: SongTimelineConceptRow = {
    q: 3,
    ts: 10,
    kind: "section",
    section: "chorus",
    occurrence: 1,
    trigger: null,
    tracking: "track",
    mib: "live",
    one_shot: null,
    evidence: null,
    screen_position: 0,
    unused_groups: 3,
  };

  it("warns when the server's own unused_groups is below the reused threshold", () => {
    expect(headroomWarning(lowHeadroomRow)).toMatch(/잔여 그룹 3개/);
  });

  it("does not warn at or above the threshold", () => {
    expect(headroomWarning({ ...lowHeadroomRow, unused_groups: 4 })).toBeNull();
  });

  it("is n/a when the field is absent (no fabricated defect)", () => {
    expect(headroomWarning({ ...lowHeadroomRow, unused_groups: undefined })).toBeNull();
  });

  it("warns MIB live straight from the server field", () => {
    expect(mibLiveWarning(lowHeadroomRow)).toMatch(/MIB live/);
  });

  it("is silent for dark/mark/null", () => {
    expect(mibLiveWarning({ ...lowHeadroomRow, mib: "dark" })).toBeNull();
    expect(mibLiveWarning({ ...lowHeadroomRow, mib: null })).toBeNull();
  });
});

describe("deriveWarningsForChange", () => {
  const cue = section({ index: 3, cue_number: 4, role: "chorus", d_level: 4 });
  const laterChorus = section({ index: 4, cue_number: 5, role: "chorus", d_level: 4 });
  const row: SongTimelineConceptRow = {
    q: 4,
    ts: 20,
    kind: "section",
    section: "chorus",
    occurrence: 1,
    trigger: null,
    tracking: "track",
    mib: "live",
    one_shot: null,
    evidence: null,
    screen_position: 3,
    unused_groups: 2,
  };
  const reserve: SongTimelineReserveItem[] = [
    { name: "BLIND", kind: "group", released_q: 23, screen_position: 5 },
  ];

  it("attaches reversal + headroom to an intensity change, not to a movement change", () => {
    const warnings = deriveWarningsForChange(
      { section: cue, allSections: [cue, laterChorus], conceptRow: row, reserve },
      { field: "intensity", groups: ["KEY"], value: 95, before: "80%" },
    );
    expect(warnings.some((w) => w.includes("후렴 상승 곡선"))).toBe(true);
    expect(warnings.some((w) => w.includes("헤드룸 부족"))).toBe(true);
  });

  it("attaches a reserve violation when the intensity change targets a locked group", () => {
    const warnings = deriveWarningsForChange(
      { section: cue, allSections: [cue, laterChorus], conceptRow: row, reserve },
      { field: "intensity", groups: ["BLIND"], value: 40, before: "0%" },
    );
    expect(warnings.some((w) => w.includes("리저브 대상"))).toBe(true);
  });

  it("attaches MIB-live only to a movement change (position-change field)", () => {
    const warnings = deriveWarningsForChange(
      { section: cue, allSections: [cue, laterChorus], conceptRow: row, reserve },
      { field: "movement", value: "Sweep L", before: "—" },
    );
    expect(warnings).toEqual(["⚠ MIB live — GATE 경고 예고"]);
  });

  it("t470 — attaches MIB-live to a position change too (the position row now emits `position`)", () => {
    const warnings = deriveWarningsForChange(
      { section: cue, allSections: [cue, laterChorus], conceptRow: row, reserve },
      { field: "position", value: "Sweep L", presetNo: "2.11", before: "—" },
    );
    expect(warnings).toEqual(["⚠ MIB live — GATE 경고 예고"]);
  });

  it("carries no warnings for a fade change (none of the 4 reused signals apply)", () => {
    const warnings = deriveWarningsForChange(
      { section: cue, allSections: [cue, laterChorus], conceptRow: row, reserve },
      { field: "fade_seconds", value: 5, before: "2초" },
    );
    expect(warnings).toEqual([]);
  });
});
