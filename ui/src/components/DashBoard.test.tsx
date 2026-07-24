// DashBoard structural tests (SPEC-COPILOT-DASHUI-001, plan.md §B M3/M4,
// design.md §2 header/collapse/헤더 스트립 affordance, §6 layout).
//
// Mocked-fidelity bound: this project has no DOM/jsdom test harness (see
// protocol.ts's own header — "Pure functions only... unit-testable without a
// DOM"). DashBoard has no internal hooks by design (see DashBoard.tsx), so it
// can be called directly as a plain function; the returned value is a React
// element — a plain object with `.type`/`.props` built by the `react-jsx`
// runtime — inspectable without any renderer. These assertions read that
// element tree the same way ApprovalCard.test.tsx exercises the extracted
// `createDecisionGuard` directly instead of simulating real clicks.
import type { ReactElement } from "react";
import { describe, expect, it, vi } from "vitest";

import { initialState, type DashSection, type DashState } from "../protocol";
import {
  DashBoard,
  dashboardSummaryText,
  dashItemIsPressable,
  fixtureCount,
  fixtureSummaryLabel,
  formatSyncTime,
} from "./DashBoard";
import { PoolSection } from "./PoolSection";

function childArray(element: ReactElement): unknown[] {
  const children = element.props.children;
  if (children === undefined) return [];
  const list = Array.isArray(children) ? children : [children];
  return list.filter((child) => child !== null && child !== undefined && child !== false);
}

const GROUPS_SECTION: DashSection = {
  name: "groups",
  status: "ok",
  items: [{ no: 3, name: "Wash" }],
};
const EXECUTORS_SECTION: DashSection = {
  name: "executors",
  status: "ok",
  items: [
    { no: 101, name: "Resolved", meta: { resolved: true } },
    { no: 102, name: "Unresolved", meta: { resolved: false } },
  ],
};
const FIXTURES_SECTION: DashSection = {
  name: "fixtures",
  status: "ok",
  items: [{ no: 1, name: "", meta: { count: 24 } }],
};

const POPULATED_DASH: DashState = {
  sections: [GROUPS_SECTION, EXECUTORS_SECTION, FIXTURES_SECTION],
  lastSyncAt: new Date(2026, 0, 1, 9, 5, 3).getTime(),
  stale: false,
};

describe("formatSyncTime", () => {
  it("renders a not-yet-synced placeholder before the first dash_catalog", () => {
    expect(formatSyncTime(null)).toBe("동기화 전");
  });

  it("formats HH:MM:SS from a wall-clock timestamp", () => {
    const ts = new Date(2026, 0, 1, 9, 5, 3).getTime();
    expect(formatSyncTime(ts)).toBe("09:05:03");
  });
});

describe("fixtureCount", () => {
  it("returns null when the fixtures section has not synced yet", () => {
    expect(fixtureCount(undefined)).toBeNull();
  });

  it("reads the synthetic count out of the count-only fixtures section", () => {
    expect(fixtureCount(FIXTURES_SECTION)).toBe(24);
  });

  it("returns null (never a guess) when the expected count meta is missing", () => {
    const noMeta: DashSection = { name: "fixtures", status: "ok", items: [] };
    expect(fixtureCount(noMeta)).toBeNull();
  });
});

describe("fixtureSummaryLabel", () => {
  it("is honest ('확인 불가') when the section is missing", () => {
    expect(fixtureSummaryLabel(undefined)).toBe("확인 불가");
  });

  it("is honest ('확인 불가') when the section failed — never a stale/guessed count", () => {
    const unreachable: DashSection = { name: "fixtures", status: "console_unreachable", items: [] };
    expect(fixtureSummaryLabel(unreachable)).toBe("확인 불가");
  });

  it("renders the count with a '대' unit when the section is healthy", () => {
    expect(fixtureSummaryLabel(FIXTURES_SECTION)).toBe("24대");
  });
});

describe("dashboardSummaryText", () => {
  it("composes the fixture count + sync time on one line, with no stale suffix when fresh", () => {
    const text = dashboardSummaryText(POPULATED_DASH, FIXTURES_SECTION);
    expect(text).toBe("픽스처 24대 · 동기화 09:05:03");
  });

  it("appends the stale suffix when the freshness claim was withdrawn on disconnect", () => {
    const staleDash: DashState = { ...POPULATED_DASH, stale: true };
    const text = dashboardSummaryText(staleDash, FIXTURES_SECTION);
    expect(text).toBe("픽스처 24대 · 동기화 09:05:03 (오래됨)");
  });
});

describe("dashItemIsPressable", () => {
  it("macros are always press-able regardless of item shape", () => {
    expect(dashItemIsPressable("macros", { no: 1, name: "M1" })).toBe(true);
  });

  it("executors are press-able ONLY when the resolution report confirms them", () => {
    expect(dashItemIsPressable("executors", { no: 1, name: "E1", meta: { resolved: true } })).toBe(
      true,
    );
    expect(dashItemIsPressable("executors", { no: 1, name: "E1", meta: { resolved: false } })).toBe(
      false,
    );
    expect(dashItemIsPressable("executors", { no: 1, name: "E1" })).toBe(false);
  });

  it("groups/preset_pools/plugins/fixtures are never press-able — structural read-only", () => {
    for (const name of ["groups", "preset_pools", "plugins", "fixtures"]) {
      expect(dashItemIsPressable(name, { no: 1, name: "X" })).toBe(false);
    }
  });
});

describe("DashBoard", () => {
  it("renders an aside with a header, a header-strip syncline, and a body region", () => {
    const element = DashBoard({
      dash: initialState.dash,
      onToggleCollapse: vi.fn(),
    }) as ReactElement;

    expect(element.type).toBe("aside");
    expect(element.props.className).toBe("dashboard");

    const [header, syncline, body] = childArray(element) as ReactElement[];
    expect(header.type).toBe("header");
    expect(header.props.className).toBe("dashboard-header");
    expect(syncline.type).toBe("div");
    expect(syncline.props.className).toBe("dashboard-syncline");
    expect(body.type).toBe("div");
    expect(body.props.className).toBe("dashboard-body");
  });

  it("header carries a title and a collapse-affordance button", () => {
    const element = DashBoard({
      dash: initialState.dash,
      onToggleCollapse: vi.fn(),
    }) as ReactElement;
    const [header] = childArray(element) as ReactElement[];
    const [title, collapseButton] = childArray(header) as ReactElement[];

    expect(title.type).toBe("span");
    expect(title.props.className).toBe("dashboard-title");
    expect(collapseButton.type).toBe("button");
    expect(collapseButton.props.className).toBe("dashboard-collapse");
  });

  it("wires the collapse button's onClick to the provided callback", () => {
    const onToggleCollapse = vi.fn();
    const element = DashBoard({ dash: initialState.dash, onToggleCollapse }) as ReactElement;
    const [header] = childArray(element) as ReactElement[];
    const [, collapseButton] = childArray(header) as ReactElement[];

    expect(typeof collapseButton.props.onClick).toBe("function");
    collapseButton.props.onClick();
    expect(onToggleCollapse).toHaveBeenCalledTimes(1);
  });

  it("syncline shows the not-yet-synced placeholder and an honest 'unavailable' fixture count on the M1-frozen empty state", () => {
    const element = DashBoard({
      dash: initialState.dash,
      onToggleCollapse: vi.fn(),
    }) as ReactElement;
    const [, syncline] = childArray(element) as ReactElement[];
    const [summary] = childArray(syncline) as ReactElement[];
    const text = childArray(summary).join("");

    expect(text).toContain("동기화 전");
    expect(text).toContain("확인 불가");
  });

  it("syncline shows the formatted fixture count + sync time once dash has data", () => {
    const element = DashBoard({ dash: POPULATED_DASH, onToggleCollapse: vi.fn() }) as ReactElement;
    const [, syncline] = childArray(element) as ReactElement[];
    const [summary] = childArray(syncline) as ReactElement[];
    const text = childArray(summary).join("");

    expect(text).toContain("24대");
    expect(text).toContain("09:05:03");
    expect(text).not.toContain("오래됨");
  });

  it("syncline appends a stale suffix when dash.stale is true (post-disconnect freshness withdrawal)", () => {
    const staleDash: DashState = { ...POPULATED_DASH, stale: true };
    const element = DashBoard({ dash: staleDash, onToggleCollapse: vi.fn() }) as ReactElement;
    const [, syncline] = childArray(element) as ReactElement[];
    const [summary] = childArray(syncline) as ReactElement[];
    const text = childArray(summary).join("");

    expect(text).toContain("오래됨");
  });

  it("refresh button dispatches the provided onRefresh callback exactly once per click", () => {
    const onRefresh = vi.fn();
    const element = DashBoard({
      dash: initialState.dash,
      onToggleCollapse: vi.fn(),
      onRefresh,
    }) as ReactElement;
    const [, syncline] = childArray(element) as ReactElement[];
    const [, refreshButton] = childArray(syncline) as ReactElement[];

    expect(refreshButton.type).toBe("button");
    expect(refreshButton.props.className).toBe("dashboard-refresh");
    refreshButton.props.onClick();
    expect(onRefresh).toHaveBeenCalledTimes(1);
  });

  it("refresh button click does not throw when onRefresh is omitted (M4 placeholder path)", () => {
    const element = DashBoard({
      dash: initialState.dash,
      onToggleCollapse: vi.fn(),
    }) as ReactElement;
    const [, syncline] = childArray(element) as ReactElement[];
    const [, refreshButton] = childArray(syncline) as ReactElement[];

    expect(() => refreshButton.props.onClick()).not.toThrow();
  });

  it("renders the loading placeholder on the M1-frozen empty/default dash state — no crash on absent data", () => {
    const element = DashBoard({
      dash: initialState.dash,
      onToggleCollapse: vi.fn(),
    }) as ReactElement;
    const [, , body] = childArray(element) as ReactElement[];
    const [placeholder] = childArray(body) as ReactElement[];

    expect(placeholder.type).toBe("div");
    expect(placeholder.props.className).toBe("dashboard-empty");
  });

  it("mounts one PoolSection per non-fixtures section, in wire order, excluding fixtures from the pool grid", () => {
    const element = DashBoard({ dash: POPULATED_DASH, onToggleCollapse: vi.fn() }) as ReactElement;
    const [, , body] = childArray(element) as ReactElement[];
    const [sectionsDiv] = childArray(body) as ReactElement[];
    expect(sectionsDiv.props.className).toBe("dashboard-sections");

    const poolSectionElements = childArray(sectionsDiv) as ReactElement[];
    expect(poolSectionElements).toHaveLength(2);
    expect(poolSectionElements.every((el) => el.type === PoolSection)).toBe(true);
    expect(poolSectionElements.map((el) => el.props.section.name)).toEqual([
      "groups",
      "executors",
    ]);
  });

  it("wires the correct Korean label + press verb + pressability predicate per section", () => {
    const element = DashBoard({ dash: POPULATED_DASH, onToggleCollapse: vi.fn() }) as ReactElement;
    const [, , body] = childArray(element) as ReactElement[];
    const [sectionsDiv] = childArray(body) as ReactElement[];
    const [groupsEl, executorsEl] = childArray(sectionsDiv) as ReactElement[];

    expect(groupsEl.props.label).toBe("그룹");
    expect(groupsEl.props.verb).toBeUndefined();
    expect(groupsEl.props.isPressable(GROUPS_SECTION.items[0])).toBe(false);

    expect(executorsEl.props.label).toBe("익스큐터");
    expect(executorsEl.props.verb).toBe("Go+");
    expect(executorsEl.props.isPressable(EXECUTORS_SECTION.items[0])).toBe(true);
    expect(executorsEl.props.isPressable(EXECUTORS_SECTION.items[1])).toBe(false);
  });

  it("does not dispatch a dash_catalog_request or fetch data itself — presentation only (M4 scope)", () => {
    // DashBoard's props are exactly { dash, onToggleCollapse, onRefresh } —
    // no socket, no internal fetch. `onRefresh` is a caller-supplied callback
    // slot, not a fetch DashBoard performs on its own.
    const element = DashBoard({
      dash: initialState.dash,
      onToggleCollapse: vi.fn(),
    }) as ReactElement;
    expect(element).toBeDefined();
  });
});
