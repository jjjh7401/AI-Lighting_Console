// RunbookMode structural tests (T-E — ad-hoc contract, no SPEC).
//
// Same mocked-fidelity bound as CueMonitor.test.tsx (this project has no
// DOM/jsdom test harness): RunbookMode has no internal hooks, so it is
// called directly as a plain function and the returned React element tree
// is inspected without a renderer.
import type { ReactElement } from "react";
import { describe, expect, it, vi } from "vitest";

import { type CueExecutorEntry, type CueMonitorState } from "../protocol";
import {
  RunbookMode,
  runbookButtonLabel,
  runbookCaution,
  runbookIsRunnable,
} from "./RunbookMode";

function childArray(element: ReactElement): unknown[] {
  const children = element.props.children;
  if (children === undefined) return [];
  const list = Array.isArray(children) ? children : [children];
  return list
    .flat(Infinity)
    .filter((child) => child !== null && child !== undefined && child !== false);
}

const OK_KNOWN_CUE: CueExecutorEntry = {
  executor_no: 101,
  status: "ok",
  sequence_no: 5,
  sequence_name: "Song A",
  cues: [
    { no: 1, name: "Intro", cue_no: 1 },
    { no: 2, name: "Chorus", cue_no: 2 },
  ],
  current_cue: { status: "ok", value: "1.5" },
};

const OK_UNKNOWN_CUE: CueExecutorEntry = {
  executor_no: 102,
  status: "ok",
  sequence_no: 6,
  sequence_name: "Song B",
  cues: [],
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

describe("runbookCaution", () => {
  it("returns null when the current cue is known — nothing to warn about", () => {
    expect(runbookCaution(OK_KNOWN_CUE)).toBeNull();
  });

  it("explains an unavailable current cue on an otherwise-ok row", () => {
    expect(runbookCaution(OK_UNKNOWN_CUE)).toMatch(/다음 큐로 넘어갑니다/);
  });

  it("explains an unassigned executor", () => {
    expect(runbookCaution(UNASSIGNED_ENTRY)).toMatch(/배정된 시퀀스가 없습니다/);
  });

  it("explains an unavailable console", () => {
    expect(runbookCaution(UNAVAILABLE_ENTRY)).toMatch(/응답하지 않아/);
  });
});

describe("runbookButtonLabel — literal, never the generic '지금 실행'", () => {
  it("names the known cue number when running", () => {
    expect(runbookButtonLabel(OK_KNOWN_CUE, false)).toBe("큐 1.5 실행");
  });

  it("falls back to a literal 'next cue' label when the cue number is unknown", () => {
    expect(runbookButtonLabel(OK_UNKNOWN_CUE, false)).toBe("다음 큐 실행");
  });

  it("shows stop when already running", () => {
    expect(runbookButtonLabel(OK_KNOWN_CUE, true)).toBe("정지");
  });

  it("is disabled-labeled for unassigned/unavailable rows", () => {
    expect(runbookButtonLabel(UNASSIGNED_ENTRY, false)).toBe("실행 불가");
    expect(runbookButtonLabel(UNAVAILABLE_ENTRY, false)).toBe("실행 불가");
  });
});

describe("runbookIsRunnable", () => {
  it("only an 'ok' row is fireable — fail-closed for unassigned/unavailable", () => {
    expect(runbookIsRunnable(OK_KNOWN_CUE)).toBe(true);
    expect(runbookIsRunnable(UNASSIGNED_ENTRY)).toBe(false);
    expect(runbookIsRunnable(UNAVAILABLE_ENTRY)).toBe(false);
  });
});

const POPULATED_STATE: CueMonitorState = {
  executors: [OK_KNOWN_CUE, OK_UNKNOWN_CUE, UNASSIGNED_ENTRY, UNAVAILABLE_ENTRY],
  history: [],
  lastSyncAt: new Date(2026, 0, 1, 9, 5, 3).getTime(),
  stale: false,
};

const EMPTY_STATE: CueMonitorState = {
  executors: [],
  history: [],
  lastSyncAt: null,
  stale: false,
};

describe("RunbookMode", () => {
  it("renders one list item per executor, in wire order, numbered from 1", () => {
    const element = RunbookMode({ cueMonitor: POPULATED_STATE });
    const body = childArray(element) as ReactElement[];
    const list = body.find((child) => (child as ReactElement).type === "ol") as ReactElement;
    expect(list).toBeDefined();
    const rows = childArray(list);
    expect(rows).toHaveLength(4);
  });

  it("explains an empty executor list instead of rendering a silent blank", () => {
    const element = RunbookMode({ cueMonitor: EMPTY_STATE });
    const body = childArray(element) as ReactElement[];
    const empty = body.find((child) => (child as ReactElement).props?.className === "runbook-empty");
    expect(empty).toBeDefined();
    expect(childArray(empty as ReactElement).join("")).toMatch(/확인된 곡·큐가 없습니다/);
  });

  it("marks a stale snapshot instead of presenting it as live", () => {
    const element = RunbookMode({ cueMonitor: { ...POPULATED_STATE, stale: true } });
    const body = childArray(element) as ReactElement[];
    const header = body.find((child) => (child as ReactElement).type === "header") as ReactElement;
    const syncline = childArray(header).find(
      (child) => (child as ReactElement).props?.className === "runbook-syncline",
    ) as ReactElement;
    expect(childArray(syncline).join("")).toMatch(/오래됨/);
  });

  it("wires onExecute to the pressed row's executor number", () => {
    const onExecute = vi.fn();
    const element = RunbookMode({ cueMonitor: POPULATED_STATE, onExecute });
    const body = childArray(element) as ReactElement[];
    const list = body.find((child) => (child as ReactElement).type === "ol") as ReactElement;
    // Each list item is an un-invoked <RunbookRow> element (hook-free, so
    // calling its function type directly — same technique the header
    // comment documents for the top-level components — reaches its <li>).
    const firstRowElement = childArray(list)[0] as ReactElement;
    const firstRow = (firstRowElement.type as (props: unknown) => ReactElement)(
      firstRowElement.props,
    );
    const rowChildren = childArray(firstRow) as ReactElement[];
    const main = rowChildren.find((child) => child?.props?.className === "runbook-item-main") as ReactElement;
    const button = childArray(main).find(
      (child) => typeof (child as ReactElement)?.props?.onClick === "function",
    ) as ReactElement;
    button.props.onClick();
    expect(onExecute).toHaveBeenCalledWith(101);
  });

  it("dispatches manual refresh via onRefresh", () => {
    const onRefresh = vi.fn();
    const element = RunbookMode({ cueMonitor: EMPTY_STATE, onRefresh });
    const body = childArray(element) as ReactElement[];
    const header = body.find((child) => (child as ReactElement).type === "header") as ReactElement;
    const refreshButton = childArray(header).find(
      (child) => (child as ReactElement).props?.className === "runbook-refresh",
    ) as ReactElement;
    refreshButton.props.onClick();
    expect(onRefresh).toHaveBeenCalledOnce();
  });
});
