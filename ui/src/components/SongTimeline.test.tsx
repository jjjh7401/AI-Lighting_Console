import type { ReactElement } from "react";
import { describe, expect, it, vi } from "vitest";

import type { CueMonitorState, SongTimelineConceptReport, SongTimelineView } from "../protocol";
import { SONG_TIMELINE_EXAMPLE } from "./songTimelineExample";
import { PlanCueRequestGenerator } from "./PlanCueRequestGenerator";
import {
  conceptRowForSection,
  fadeTrackLine,
  headroomSummaryLine,
  isTimelineCurrentCue,
  linkedTimelineExecutor,
  liveExecutorForSection,
  mibHeadroomLine,
  SongTimeline,
  sectionCardTitle,
  sectionPlanStatus,
  timelineConsoleStored,
} from "./SongTimeline";

function childArray(element: ReactElement): unknown[] {
  const children = element.props.children;
  if (children === undefined) return [];
  const list = Array.isArray(children) ? children : [children];
  return list.flat(Infinity).filter((child) => child !== null && child !== undefined && child !== false);
}

/** SongTimeline → TimelineSectionCard 처럼, 훅이 없는 중첩 함수 컴포넌트는
 * 자동으로 펼쳐 훑는다(CueMonitor.test.tsx의 `render()` 관례를 재귀로
 * 일반화한 것). `PlanCueRequestGenerator`는 훅을 쥐고 있어 이 환경(jsdom
 * 없음)에서 직접 호출하면 던지므로, 존재 여부만 `type` 동일성으로 확인하고
 * **펼치지 않는다**(stopTypes). */
function deepElements(root: ReactElement, stopTypes: unknown[]): ReactElement[] {
  const results: ReactElement[] = [];
  for (const raw of childArray(root)) {
    const el = raw as ReactElement;
    if (typeof el?.type === "function" && !stopTypes.includes(el.type)) {
      const expanded = (el.type as (props: unknown) => ReactElement)(el.props);
      results.push(expanded, ...deepElements(expanded, stopTypes));
    } else if (el?.props) {
      results.push(el, ...deepElements(el, stopTypes));
    }
  }
  return results;
}

function findAllByClassIncludes(root: ReactElement, needle: string, stopTypes: unknown[] = []): ReactElement[] {
  return deepElements(root, stopTypes).filter(
    (el) => typeof el.props?.className === "string" && el.props.className.includes(needle),
  );
}

function findAllByType(root: ReactElement, type: unknown, stopTypes: unknown[] = []): ReactElement[] {
  return deepElements(root, stopTypes.length > 0 ? stopTypes : [type]).filter((el) => el.type === type);
}

function textOf(element: unknown): string {
  if (element === null || element === undefined || element === false) return "";
  if (typeof element === "string" || typeof element === "number") return String(element);
  const el = element as ReactElement;
  if (!el?.props) return "";
  return childArray(el).map(textOf).join("");
}

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

describe("REQ-LDDESIGN-083 — 하단 3줄이 읽는 컨셉 행 짝짓기 (t460)", () => {
  const report: SongTimelineConceptReport = {
    available: true,
    rows: [
      {
        q: 3,
        ts: 12,
        kind: "section",
        section: "chorus",
        occurrence: 1,
        trigger: null,
        tracking: "cue_only",
        mib: "live",
        one_shot: null,
        evidence: null,
        screen_position: 0,
        unused_groups: 2,
      },
    ],
  };

  it("matches the section-kind row whose screen_position equals this section's index", () => {
    expect(conceptRowForSection(report, 0)?.q).toBe(3);
    expect(conceptRowForSection(report, 1)).toBeUndefined();
  });

  it("is honestly absent when row_pairing failed (no report, or no matching row)", () => {
    expect(conceptRowForSection(undefined, 0)).toBeUndefined();
    expect(conceptRowForSection({ available: false }, 0)).toBeUndefined();
  });

  it("Fade/Track line reads fade_seconds and the tracking exception (blank when default)", () => {
    expect(fadeTrackLine({ ...SECTION, fade_seconds: 2 }, report.rows![0])).toBe("Fade 2s · Track cue_only");
    expect(fadeTrackLine({ ...SECTION, fade_seconds: 2 }, undefined)).toBe("Fade 2s · Track —");
    expect(
      fadeTrackLine({ ...SECTION, fade_seconds: 2 }, { ...report.rows![0], tracking: "track" }),
    ).toBe("Fade 2s · Track —");
  });

  it("MIB/남김 line reads both fields straight from the row — never recomputed", () => {
    expect(mibHeadroomLine(report.rows![0])).toBe("MIB live · 남김 2");
    expect(mibHeadroomLine(undefined)).toBe("MIB — · 남김 —");
  });

  it("headroom summary reuses the REQ-093 (4) <4 threshold, never a new one", () => {
    expect(headroomSummaryLine({ ...report.rows![0], unused_groups: 2 })).toContain("부족");
    expect(headroomSummaryLine({ ...report.rows![0], unused_groups: 4 })).toContain("여유");
    expect(headroomSummaryLine(undefined)).toBe("헤드룸 —");
  });
});

describe("SongTimeline render — REQ-083 Q### 배지 + 하단 3줄, AC-034 마운트 게이트", () => {
  const planTimeline: SongTimelineView = {
    ...SONG_TIMELINE_EXAMPLE,
    lifecycle: "draft",
    sections: [{ ...SONG_TIMELINE_EXAMPLE.sections[0], plan_status: "draft", index: 0, cue_number: 7 }],
  };
  const cueMonitor: CueMonitorState = { executors: [], history: [], lastSyncAt: 0, stale: false };

  it("renders the Q### badge on the PLAN CUE card using the shared cueLabel rule", () => {
    const el = SongTimeline({ timeline: planTimeline, cueMonitor });
    const badges = findAllByClassIncludes(el, "song-timeline-q-badge");
    expect(badges).toHaveLength(1);
    expect(textOf(badges[0])).toBe("Q007");
  });

  it("renders the 3 REQ-083 detail lines on a PLAN CUE card", () => {
    const el = SongTimeline({ timeline: planTimeline, cueMonitor });
    const detail = findAllByClassIncludes(el, "song-timeline-plan-detail")[0];
    expect(detail).toBeTruthy();
    expect(childArray(detail)).toHaveLength(3);
  });

  it("does NOT mount the generator when onGeneratorSend is omitted (AC-034)", () => {
    const el = SongTimeline({ timeline: planTimeline, cueMonitor });
    expect(findAllByType(el, PlanCueRequestGenerator)).toHaveLength(0);
  });

  it("mounts the generator under the PLAN CUE card once onGeneratorSend is wired (AC-034)", () => {
    const onGeneratorSend = vi.fn();
    const el = SongTimeline({
      timeline: planTimeline,
      cueMonitor,
      onGeneratorSend,
      generatorResponding: false,
      generatorLastAssistantText: null,
    });
    const mounted = findAllByType(el, PlanCueRequestGenerator);
    expect(mounted).toHaveLength(1);
    expect(mounted[0].props.onSend).toBe(onGeneratorSend);
    expect(mounted[0].props.section.cue_number).toBe(7);
  });

  it("does not mount the generator on a console-stored (non-PLAN) cue", () => {
    const storedTimeline: SongTimelineView = {
      ...planTimeline,
      sections: [{ ...planTimeline.sections[0], plan_status: "verified" }],
    };
    const el = SongTimeline({
      timeline: storedTimeline,
      cueMonitor,
      onGeneratorSend: vi.fn(),
    });
    expect(findAllByType(el, PlanCueRequestGenerator)).toHaveLength(0);
    expect(findAllByClassIncludes(el, "song-timeline-plan-detail")).toHaveLength(0);
  });
});
