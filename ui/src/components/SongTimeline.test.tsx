import { describe, expect, it } from "vitest";

import type { CueMonitorState } from "../protocol";
import { SONG_TIMELINE_EXAMPLE } from "./songTimelineExample";
import {
  isTimelineCurrentCue,
  linkedTimelineExecutor,
  liveExecutorForSection,
  sectionCardTitle,
  sectionPlanStatus,
  timelineConsoleStored,
} from "./SongTimeline";

const LINKED_MONITOR: CueMonitorState = {
  executors: [{
    executor_no: 120,
    status: "ok",
    sequence_no: 120,
    sequence_name: "Sequence 120",
    cues: [{ no: 3, name: "Chorus", cue_no: 3 }],
    current_cue: { status: "ok", value: "3" },
  }],
  history: [],
  lastSyncAt: 0,
  stale: false,
};

describe("linkedTimelineExecutor", () => {
  it("links a plan only to an executor with the same console sequence number", () => {
    expect(linkedTimelineExecutor(SONG_TIMELINE_EXAMPLE, LINKED_MONITOR)?.executor_no).toBe(120);
  });

  it("does not infer a match from an unrelated executor name or cue", () => {
    expect(linkedTimelineExecutor(SONG_TIMELINE_EXAMPLE, {
      ...LINKED_MONITOR,
      executors: [{ ...LINKED_MONITOR.executors[0], sequence_no: 50, sequence_name: "NEON RUN" }],
    })).toBeNull();
  });

  it("marks only the matching planned cue as live", () => {
    expect(isTimelineCurrentCue(LINKED_MONITOR.executors[0], 3)).toBe(true);
    expect(isTimelineCurrentCue(LINKED_MONITOR.executors[0], 2)).toBe(false);
  });

  it("matches a console value carrying the cue name ('5 — Section 5', live onPC format)", () => {
    const entry = {
      ...LINKED_MONITOR.executors[0],
      current_cue: { status: "ok" as const, value: "5 — Section 5" },
    };
    expect(isTimelineCurrentCue(entry, 5)).toBe(true);
    expect(isTimelineCurrentCue(entry, 1)).toBe(false);
  });
});

const SECTION = SONG_TIMELINE_EXAMPLE.sections[0];

describe("plan vs console cue separation", () => {
  it("titles design-only sections as PLAN CUE and console cues as CUE", () => {
    expect(sectionCardTitle(SECTION, "draft")).toBe(
      `PLAN CUE ${SECTION.cue_number} · ${SECTION.label}`,
    );
    expect(sectionCardTitle(SECTION, "requires_requery")).toContain("PLAN CUE");
    expect(sectionCardTitle(SECTION, "approved")).toContain("PLAN CUE");
    expect(sectionCardTitle(SECTION, "stored")).toBe(
      `CUE ${SECTION.cue_number} · ${SECTION.label}`,
    );
    expect(sectionCardTitle(SECTION, "verified")).toBe(`CUE ${SECTION.cue_number}`);
  });

  it("never links a live executor to a PLAN cue, even with a matching sequence", () => {
    const executor = LINKED_MONITOR.executors[0];
    expect(liveExecutorForSection("draft", executor)).toBeNull();
    expect(liveExecutorForSection("requires_requery", executor)).toBeNull();
    expect(liveExecutorForSection("approved", executor)).toBeNull();
    expect(liveExecutorForSection("stored", executor)).toBe(executor);
    expect(liveExecutorForSection("verified", executor)).toBe(executor);
  });

  it("uses the server plan_status when present and derives it from lifecycle otherwise", () => {
    expect(sectionPlanStatus({ ...SECTION, plan_status: "requires_requery" }, "verified")).toBe(
      "requires_requery",
    );
    expect(sectionPlanStatus(SECTION, "requires_requery")).toBe("draft");
    expect(sectionPlanStatus(SECTION, "pending_approval")).toBe("draft");
    expect(sectionPlanStatus(SECTION, "approved")).toBe("approved");
    expect(sectionPlanStatus(SECTION, "readback_failed")).toBe("stored");
    expect(sectionPlanStatus(SECTION, "verified")).toBe("verified");
  });

  it("treats the console as holding cues only after a write", () => {
    expect(timelineConsoleStored({ ...SONG_TIMELINE_EXAMPLE, console_stored: true })).toBe(true);
    expect(timelineConsoleStored({ ...SONG_TIMELINE_EXAMPLE, console_stored: false })).toBe(false);
    expect(
      timelineConsoleStored({ ...SONG_TIMELINE_EXAMPLE, lifecycle: "pending_approval" }),
    ).toBe(false);
    expect(timelineConsoleStored({ ...SONG_TIMELINE_EXAMPLE, lifecycle: "verified" })).toBe(true);
    expect(
      timelineConsoleStored({ ...SONG_TIMELINE_EXAMPLE, lifecycle: "readback_failed" }),
    ).toBe(true);
  });
});
