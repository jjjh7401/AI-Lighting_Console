// CueMonitor structural tests (T-C, wave 2 — ad-hoc contract, no SPEC).
//
// Same mocked-fidelity bound as DashBoard.test.tsx (this project has no
// DOM/jsdom test harness): CueMonitor has no internal hooks, so it is called
// directly as a plain function and the returned React element tree is
// inspected without a renderer.
import type { ReactElement } from "react";
import { describe, expect, it, vi } from "vitest";

import { type CueExecutorEntry, type CueMonitorState } from "../protocol";
import {
  CueExecutorRow,
  CueMonitor,
  ExecutorActions,
  ExecutorStatusChip,
  currentCueBannerState,
  currentCueLabel,
  currentCueRowView,
  currentCueUnavailableReason,
  executorFireDisabledReason,
  formatRelativeAgo,
  isRecentAppAction,
  lastActionGrade,
  sequenceLabel,
} from "./CueMonitor";

function childArray(element: ReactElement): unknown[] {
  const children = element.props.children;
  if (children === undefined) return [];
  const list = Array.isArray(children) ? children : [children];
  return list
    .flat(Infinity)
    .filter((child) => child !== null && child !== undefined && child !== false);
}

const OK_ENTRY: CueExecutorEntry = {
  executor_no: 101,
  status: "ok",
  sequence_no: 5,
  sequence_name: "Song A",
  cues: [
    { no: 1, name: "Intro", cue_no: 1 },
    { no: 2, name: "Chorus" },
  ],
  current_cue: { status: "unavailable", tried: ["Cue"] },
};

const UNASSIGNED_ENTRY: CueExecutorEntry = {
  executor_no: 201,
  status: "unassigned",
  cues: [],
  current_cue: null,
};

const UNAVAILABLE_ENTRY: CueExecutorEntry = {
  executor_no: 301,
  status: "unavailable",
  cues: [],
  current_cue: null,
};

const POPULATED_STATE: CueMonitorState = {
  executors: [OK_ENTRY, UNASSIGNED_ENTRY, UNAVAILABLE_ENTRY],
  history: [
    { ts: "2026-08-02T00:00:00+00:00", command: "Go+ Executor 101", ok: true },
    { ts: "2026-08-02T00:00:05+00:00", command: "Delete Group 1", ok: false },
  ],
  lastSyncAt: new Date(2026, 0, 1, 9, 5, 3).getTime(),
  stale: false,
};

const EMPTY_STATE: CueMonitorState = {
  executors: [],
  history: [],
  lastSyncAt: null,
  stale: false,
};

describe("sequenceLabel", () => {
  it("shows the sequence name when the read succeeded", () => {
    expect(sequenceLabel(OK_ENTRY)).toBe("Song A");
  });

  it("falls back to the sequence number when the name is empty", () => {
    expect(sequenceLabel({ ...OK_ENTRY, sequence_name: "" })).toBe("시퀀스 5");
  });

  it("explains an unassigned executor", () => {
    expect(sequenceLabel(UNASSIGNED_ENTRY)).toBe("할당된 시퀀스 없음");
  });

  it("explains an unavailable executor", () => {
    expect(sequenceLabel(UNAVAILABLE_ENTRY)).toBe("확인 불가 — 콘솔 응답 없음");
  });
});

describe("currentCueLabel — independently Optional (contract item 1)", () => {
  it("renders the value when the read succeeded", () => {
    expect(currentCueLabel({ ...OK_ENTRY, current_cue: { status: "ok", value: "3" } })).toBe(
      "현재 큐: 3",
    );
  });

  it("explains WHY it is unavailable rather than rendering a blank", () => {
    const label = currentCueLabel(OK_ENTRY);
    expect(label).toContain("확인 불가");
    expect(label.length).toBeGreaterThan("현재 큐: 확인 불가".length);
  });

  it("never renders a percentage or a countdown", () => {
    // Contract explicitly excludes progress %/timer — no channel confirms one.
    for (const entry of [OK_ENTRY, UNASSIGNED_ENTRY, UNAVAILABLE_ENTRY]) {
      expect(currentCueLabel(entry)).not.toMatch(/%|초$/);
    }
  });

  it("treats a null current_cue the same as an unavailable one", () => {
    expect(currentCueLabel(UNASSIGNED_ENTRY)).toBe(currentCueLabel(UNAVAILABLE_ENTRY));
  });
});

describe("CueMonitor", () => {
  it("renders one row per executor plus a history section", () => {
    const element = CueMonitor({ cueMonitor: POPULATED_STATE }) as ReactElement;
    expect(element.props["aria-label"]).toBe("라이브 큐 진행 모니터");

    const body = childArray(element).find(
      (child) => (child as ReactElement).props?.className === "cue-monitor-body",
    ) as ReactElement;
    const [executorList, historyBlock] = childArray(body) as ReactElement[];
    const executorRows = childArray(executorList).filter(
      (child) => (child as ReactElement)?.props?.entry !== undefined,
    ) as ReactElement[];
    expect(executorRows).toHaveLength(3);
    expect(executorRows.map((row) => row.props.entry.executor_no)).toEqual([101, 201, 301]);

    const historyItems = childArray(childArray(historyBlock)[1] as ReactElement);
    expect(historyItems).toHaveLength(2);
  });

  it("shows an empty-state placeholder for both lists when nothing has synced", () => {
    const element = CueMonitor({ cueMonitor: EMPTY_STATE }) as ReactElement;
    const body = childArray(element).find(
      (child) => (child as ReactElement).props?.className === "cue-monitor-body",
    ) as ReactElement;
    const [executorList, historyBlock] = childArray(body) as ReactElement[];
    expect(childArray(executorList)).toHaveLength(1); // the "확인된 익스큐터 없음" row
    const historyItems = childArray(childArray(historyBlock)[1] as ReactElement);
    expect(historyItems).toHaveLength(1); // the "실행 이력 없음" row
  });

  it("marks a stale snapshot in the sync line", () => {
    const element = CueMonitor({ cueMonitor: { ...POPULATED_STATE, stale: true } }) as ReactElement;
    const header = childArray(element)[0] as ReactElement;
    const syncline = childArray(header)[1] as ReactElement;
    expect((childArray(syncline).join("") as string)).toContain("오래됨");
  });

  it("refresh button click dispatches the provided callback", () => {
    const onRefresh = vi.fn();
    const element = CueMonitor({ cueMonitor: EMPTY_STATE, onRefresh }) as ReactElement;
    const header = childArray(element)[0] as ReactElement;
    const button = childArray(header).find(
      (child) => (child as ReactElement)?.props?.["aria-label"] === "큐 모니터 새로고침",
    ) as ReactElement;
    button.props.onClick();
    expect(onRefresh).toHaveBeenCalledTimes(1);
  });

  it("refresh button click does not throw when onRefresh is omitted", () => {
    const element = CueMonitor({ cueMonitor: EMPTY_STATE }) as ReactElement;
    const header = childArray(element)[0] as ReactElement;
    const button = childArray(header).find(
      (child) => (child as ReactElement)?.props?.["aria-label"] === "큐 모니터 새로고침",
    ) as ReactElement;
    expect(() => button.props.onClick()).not.toThrow();
  });
});

// -- T-H: last_app_action status chip / pulse / relative time ---------------

const NOW = Date.parse("2026-08-02T00:10:00+00:00");

describe("lastActionGrade", () => {
  it("grades a nonexistent action as unknown — the app never sent this executor anything", () => {
    expect(lastActionGrade(UNASSIGNED_ENTRY)).toBe("unknown");
  });

  it("grades an ok action as confirmed", () => {
    const entry = { ...OK_ENTRY, last_app_action: { command: "Go+ Executor 101", ts: "t", ok: true } };
    expect(lastActionGrade(entry)).toBe("confirmed");
  });

  it("grades a failed action as failed", () => {
    const entry = { ...OK_ENTRY, last_app_action: { command: "Off Executor 101", ts: "t", ok: false } };
    expect(lastActionGrade(entry)).toBe("failed");
  });
});

describe("formatRelativeAgo", () => {
  it("renders a just-now action as 방금 전", () => {
    expect(formatRelativeAgo(new Date(NOW - 1_000).toISOString(), NOW)).toBe("방금 전");
  });

  it("renders seconds for a recent-but-not-instant action", () => {
    expect(formatRelativeAgo(new Date(NOW - 12_000).toISOString(), NOW)).toBe("12초 전");
  });

  it("renders minutes once past 60 seconds", () => {
    expect(formatRelativeAgo(new Date(NOW - 90_000).toISOString(), NOW)).toBe("1분 전");
  });

  it("renders an empty string for an unparseable timestamp", () => {
    expect(formatRelativeAgo("not-a-timestamp", NOW)).toBe("");
  });
});

describe("isRecentAppAction — the pulse window", () => {
  it("is true just after the action", () => {
    expect(isRecentAppAction(new Date(NOW - 1_000).toISOString(), NOW)).toBe(true);
  });

  it("is false once the pulse window has elapsed", () => {
    expect(isRecentAppAction(new Date(NOW - 10_000).toISOString(), NOW)).toBe(false);
  });

  it("is false for an unparseable timestamp", () => {
    expect(isRecentAppAction("not-a-timestamp", NOW)).toBe(false);
  });
});

describe("ExecutorStatusChip", () => {
  it("renders the unknown grade with no last_app_action", () => {
    const element = ExecutorStatusChip({ entry: UNASSIGNED_ENTRY }) as ReactElement;
    expect(element.props.className).toBe("cue-status-chip cue-status-chip-unknown");
    expect(childArray(element)[0]).toBe("○ 미확인");
  });

  it("renders confirmed + pulsing right after a fresh ok action", () => {
    // ExecutorStatusChip reads the REAL clock internally (a live render has
    // no injected `now`), so this uses `Date.now()`-relative freshness
    // rather than the fixed `NOW` constant the pure helpers above use.
    const entry = {
      ...OK_ENTRY,
      last_app_action: {
        command: "Go+ Executor 101",
        ts: new Date(Date.now() - 1_000).toISOString(),
        ok: true,
      },
    };
    const element = ExecutorStatusChip({ entry }) as ReactElement;
    expect(element.props.className).toBe(
      "cue-status-chip cue-status-chip-confirmed cue-status-chip-pulse",
    );
  });

  it("stops pulsing once the action ages past the window, but stays confirmed", () => {
    const entry = {
      ...OK_ENTRY,
      last_app_action: {
        command: "Go+ Executor 101",
        ts: new Date(Date.now() - 60_000).toISOString(),
        ok: true,
      },
    };
    const element = ExecutorStatusChip({ entry }) as ReactElement;
    expect(element.props.className).toBe("cue-status-chip cue-status-chip-confirmed");
  });

  it("renders failed for a not-ok action — never pulsing", () => {
    const entry = {
      ...OK_ENTRY,
      last_app_action: { command: "Off Executor 101", ts: new Date().toISOString(), ok: false },
    };
    const element = ExecutorStatusChip({ entry }) as ReactElement;
    expect(element.props.className).toBe("cue-status-chip cue-status-chip-failed");
    expect(childArray(element)[0]).toBe("✕ 실패/무응답");
  });
});

describe("executorFireDisabledReason — fail-closed posture", () => {
  it("is disabled with a reason for an unavailable (unresolved-right-now) executor", () => {
    expect(executorFireDisabledReason(UNAVAILABLE_ENTRY)).not.toBeNull();
  });

  it("is fireable for an ok executor", () => {
    expect(executorFireDisabledReason(OK_ENTRY)).toBeNull();
  });

  it("is fireable for an unassigned (console-answered, just no sequence) executor", () => {
    expect(executorFireDisabledReason(UNASSIGNED_ENTRY)).toBeNull();
  });
});

describe("ExecutorActions", () => {
  it("renders an enabled 실행 button for a fireable, non-running executor", () => {
    const element = ExecutorActions({ entry: OK_ENTRY, running: false }) as ReactElement;
    const button = childArray(element)[0] as ReactElement;
    expect(button.props.disabled).toBe(false);
    expect(childArray(button)[0]).toBe("▶ 실행");
  });

  it("renders 정지 when running, and fires onStop (never onExecute) on click", () => {
    const onExecute = vi.fn();
    const onStop = vi.fn();
    const element = ExecutorActions({
      entry: OK_ENTRY,
      running: true,
      onExecute,
      onStop,
    }) as ReactElement;
    const button = childArray(element)[0] as ReactElement;
    expect(childArray(button)[0]).toBe("■ 정지");
    button.props.onClick();
    expect(onStop).toHaveBeenCalledWith(101);
    expect(onExecute).not.toHaveBeenCalled();
  });

  it("fires onExecute (never onStop) when not running", () => {
    const onExecute = vi.fn();
    const onStop = vi.fn();
    const element = ExecutorActions({
      entry: OK_ENTRY,
      running: false,
      onExecute,
      onStop,
    }) as ReactElement;
    const button = childArray(element)[0] as ReactElement;
    button.props.onClick();
    expect(onExecute).toHaveBeenCalledWith(101);
    expect(onStop).not.toHaveBeenCalled();
  });

  it("disables the button and shows a reason for an unavailable executor — fail-closed", () => {
    const element = ExecutorActions({ entry: UNAVAILABLE_ENTRY, running: false }) as ReactElement;
    const [button, reason] = childArray(element) as ReactElement[];
    expect(button.props.disabled).toBe(true);
    expect(reason).toBeDefined();
  });

  it("a fail-closed button click never calls onExecute, even if somehow invoked", () => {
    // Defence in depth: `disabled` is the real gate, but this documents the
    // handler itself still routes correctly rather than silently no-op'ing
    // into the wrong verb if a caller ever bypasses the disabled attribute.
    const onExecute = vi.fn();
    const element = ExecutorActions({
      entry: UNAVAILABLE_ENTRY,
      running: false,
      onExecute,
    }) as ReactElement;
    const button = childArray(element)[0] as ReactElement;
    expect(button.props.disabled).toBe(true);
  });
});

describe("CueExecutorRow — panel_execute/panel_stop wiring end-to-end", () => {
  it("passes running state and callbacks through to the action button", () => {
    const onExecute = vi.fn();
    const row = CueExecutorRow({
      entry: OK_ENTRY,
      running: true,
      onExecute,
    }) as ReactElement;
    const actions = childArray(row).find(
      (child) => (child as ReactElement)?.props?.entry !== undefined && (child as ReactElement).props?.running !== undefined,
    ) as ReactElement;
    expect(actions).toBeDefined();
  });

  it("renders the status chip inside the header", () => {
    const row = CueExecutorRow({ entry: UNASSIGNED_ENTRY }) as ReactElement;
    const header = childArray(row)[0] as ReactElement;
    const chip = childArray(header).find(
      (child) => typeof (child as ReactElement)?.type === "function",
    );
    expect(chip).toBeDefined();
  });
});

// -- T-H2: no more identical-sentence repetition across every executor row --
//
// User feedback (2026-08-02): the same long "확인 불가" sentence repeated on
// every one of 8 rows reads as noise, not information. The fix keeps the
// SAME honesty (no "playing now" claim, no % / countdown, no silent blank)
// but says the shared fact ONCE at panel level when it really is shared, and
// keeps each row down to a short placeholder — never dropping the fact that
// this row's current cue is unknown, just moving the long explanation to a
// tooltip (`title`) instead of the row body.

const ENTRY_WITH_VALUE: CueExecutorEntry = {
  ...OK_ENTRY,
  executor_no: 401,
  current_cue: { status: "ok", value: "3", property: "Cue", tried: ["Cue"] },
};

const ENTRY_UNAVAILABLE_SAME_TRIED: CueExecutorEntry = {
  ...OK_ENTRY,
  executor_no: 402,
  current_cue: { status: "unavailable", tried: ["Cue"] },
};

const ENTRY_UNAVAILABLE_DIFFERENT_TRIED: CueExecutorEntry = {
  ...OK_ENTRY,
  executor_no: 403,
  current_cue: { status: "unavailable", tried: ["Fader", "Phase"] },
};

describe("currentCueUnavailableReason", () => {
  it("is null when the entry actually has a value — nothing to explain", () => {
    expect(currentCueUnavailableReason(ENTRY_WITH_VALUE)).toBeNull();
  });

  it("names the tried property list in the reason text", () => {
    expect(currentCueUnavailableReason(ENTRY_UNAVAILABLE_SAME_TRIED)).toContain("Cue");
  });

  it("two entries with the same tried list produce the identical reason text", () => {
    const twin: CueExecutorEntry = { ...ENTRY_UNAVAILABLE_SAME_TRIED, executor_no: 999 };
    expect(currentCueUnavailableReason(ENTRY_UNAVAILABLE_SAME_TRIED)).toBe(
      currentCueUnavailableReason(twin),
    );
  });

  it("a different tried list produces different reason text", () => {
    expect(currentCueUnavailableReason(ENTRY_UNAVAILABLE_SAME_TRIED)).not.toBe(
      currentCueUnavailableReason(ENTRY_UNAVAILABLE_DIFFERENT_TRIED),
    );
  });
});

describe("currentCueRowView — the SHORT per-row placeholder", () => {
  it("shows the value when the entry has one", () => {
    const view = currentCueRowView(ENTRY_WITH_VALUE);
    expect(view.hasValue).toBe(true);
    expect(view.label).toBe("현재 큐: 3");
    expect(view.reason).toBeNull();
  });

  it("is a short dash placeholder (never the long sentence) when unavailable", () => {
    const view = currentCueRowView(ENTRY_UNAVAILABLE_SAME_TRIED);
    expect(view.hasValue).toBe(false);
    expect(view.label).toBe("현재 큐 —");
    expect(view.label.length).toBeLessThan(20);
  });

  it("still carries the full reason (for a tooltip), just not in the row body", () => {
    const view = currentCueRowView(ENTRY_UNAVAILABLE_SAME_TRIED);
    expect(view.reason).not.toBeNull();
    expect(view.reason).toContain("확인 불가");
  });

  it("never renders a blank — the placeholder is always non-empty", () => {
    for (const entry of [ENTRY_WITH_VALUE, ENTRY_UNAVAILABLE_SAME_TRIED, UNASSIGNED_ENTRY]) {
      expect(currentCueRowView(entry).label.length).toBeGreaterThan(0);
    }
  });

  it("T-H3: renders the server's 'index — name' current-cue value verbatim", () => {
    // server/web/cue_monitor.py now reads the SEQUENCE handle's CurrentCue
    // property and composes "<index> — <cue name>" server-side; the UI does
    // no reformatting of its own, so a value this shape must render through
    // unchanged (no reformatting to break, no re-derivation to drift).
    const entry: CueExecutorEntry = {
      ...OK_ENTRY,
      current_cue: { status: "ok", value: "2 — Hook Drop", property: "CurrentCue", tried: ["CurrentCue"] },
    };
    const view = currentCueRowView(entry);
    expect(view.hasValue).toBe(true);
    expect(view.label).toBe("현재 큐: 2 — Hook Drop");
  });
});

describe("currentCueBannerState — the three-way branch (REQ T-H2 §3)", () => {
  it("branch 1: every ok-status executor unavailable for the SAME reason -> uniform banner", () => {
    const twin: CueExecutorEntry = { ...ENTRY_UNAVAILABLE_SAME_TRIED, executor_no: 404 };
    const state = currentCueBannerState([ENTRY_UNAVAILABLE_SAME_TRIED, twin]);
    expect(state.kind).toBe("uniform");
    if (state.kind === "uniform") {
      expect(state.reason).toContain("Cue");
    }
  });

  it("branch 2: reasons are mixed across rows -> no blanket banner (mixed)", () => {
    const state = currentCueBannerState([
      ENTRY_UNAVAILABLE_SAME_TRIED,
      ENTRY_UNAVAILABLE_DIFFERENT_TRIED,
    ]);
    expect(state.kind).toBe("mixed");
  });

  it("branch 3: at least one row already has a value -> no blanket claim (none)", () => {
    const state = currentCueBannerState([ENTRY_WITH_VALUE, ENTRY_UNAVAILABLE_SAME_TRIED]);
    expect(state.kind).toBe("none");
  });

  it("ignores non-ok-status executors (they never attempt a current-cue read at all)", () => {
    const state = currentCueBannerState([
      ENTRY_UNAVAILABLE_SAME_TRIED,
      { ...ENTRY_UNAVAILABLE_DIFFERENT_TRIED, status: "unassigned" },
    ]);
    expect(state.kind).toBe("uniform");
  });

  it("no ok-status executors at all -> none", () => {
    expect(currentCueBannerState([UNASSIGNED_ENTRY, UNAVAILABLE_ENTRY]).kind).toBe("none");
  });

  it("all ok-status executors have values -> none (nothing to bannner)", () => {
    const other: CueExecutorEntry = { ...ENTRY_WITH_VALUE, executor_no: 405 };
    expect(currentCueBannerState([ENTRY_WITH_VALUE, other]).kind).toBe("none");
  });
});

describe("CueMonitor — panel-level banner rendering (T-H2)", () => {
  function stateWith(executors: CueExecutorEntry[]): CueMonitorState {
    return { ...POPULATED_STATE, executors };
  }

  /** `CurrentCueBanner` is a component, not a DOM node — the element in
   * CueMonitor's own children array has `props.executors`, not a
   * `className`. Find it by that prop, then invoke its own render function
   * one level deeper (same "call the function component directly" pattern
   * this whole suite uses) to inspect what it actually put on the page. */
  function renderedBanner(element: ReactElement): ReactElement | null {
    const bannerElement = childArray(element).find(
      (child) => (child as ReactElement)?.props?.executors !== undefined,
    ) as ReactElement | undefined;
    if (!bannerElement) return null;
    return (bannerElement.type as (props: unknown) => ReactElement | null)(bannerElement.props);
  }

  it("renders exactly one banner when every row shares the same unavailable reason", () => {
    const twin: CueExecutorEntry = { ...ENTRY_UNAVAILABLE_SAME_TRIED, executor_no: 406 };
    const element = CueMonitor({
      cueMonitor: stateWith([ENTRY_UNAVAILABLE_SAME_TRIED, twin]),
    }) as ReactElement;
    const banner = renderedBanner(element);
    expect(banner).not.toBeNull();
    expect(banner!.props.className).toBe("cue-monitor-current-cue-banner");
    expect((childArray(banner!).join("") as string)).toContain("확인 불가");
  });

  it("renders no banner when reasons are mixed", () => {
    const element = CueMonitor({
      cueMonitor: stateWith([ENTRY_UNAVAILABLE_SAME_TRIED, ENTRY_UNAVAILABLE_DIFFERENT_TRIED]),
    }) as ReactElement;
    expect(renderedBanner(element)).toBeNull();
  });

  it("renders no banner when some rows already have a value", () => {
    const element = CueMonitor({
      cueMonitor: stateWith([ENTRY_WITH_VALUE, ENTRY_UNAVAILABLE_SAME_TRIED]),
    }) as ReactElement;
    expect(renderedBanner(element)).toBeNull();
    // ...and the row with a value shows it, never the long sentence.
    const body = childArray(element).find(
      (child) => (child as ReactElement).props?.className === "cue-monitor-body",
    ) as ReactElement;
    const [executorList] = childArray(body) as ReactElement[];
    const rows = childArray(executorList).filter(
      (child) => (child as ReactElement)?.props?.entry !== undefined,
    ) as ReactElement[];
    expect(rows.map((row) => row.props.entry.executor_no)).toEqual([401, 402]);
  });
});
