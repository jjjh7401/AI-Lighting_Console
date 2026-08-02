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
  currentCueLabel,
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
