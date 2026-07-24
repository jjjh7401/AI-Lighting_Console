// App split-pane layout tests — chat-first regression guard
// (SPEC-COPILOT-DASHUI-001 M3, AC-DASHUI-009).
//
// Mocked-fidelity bound: this project has no DOM/jsdom test harness (see
// protocol.ts's own header). `useCopilotSocket()` calls React hooks
// (useReducer/useState/useEffect/useRef) that need an active render
// dispatcher this test setup doesn't provide, so `App()` itself cannot be
// called directly here — the same bound useCopilotSocket.test.ts documents
// for the socket hook. `AppShell` is hook-free by design (see App.tsx)
// precisely so the split-pane layout decision stays testable without a
// renderer: it is called directly as a plain function and its returned
// React element tree is inspected, the same technique DashBoard.test.tsx
// applies to the sibling DashBoard component.
import type { ReactElement } from "react";
import { describe, expect, it, vi } from "vitest";

import { AppShell, dashPressTargetNo, targetKindForDashSection } from "./App";
import { DashBoard } from "./components/DashBoard";
import { initialState } from "./protocol";

function childArray(element: ReactElement): unknown[] {
  const children = element.props.children;
  return Array.isArray(children) ? children : [children];
}

// Stands in for the existing chat UI subtree (header/banner/main/composer —
// ChatView, ApprovalCard, ReviewCard, SettingsPanel, StatusBanner all live
// inside it). AppShell must never inspect or rewrite it — only wrap it.
const CHAT_SENTINEL = "chat-ui-sentinel";

// M5 (design.md §4) — the section-name-to-target_kind map that keys
// panel_execute/panel_stop dispatch and the panel.running lookup.
describe("targetKindForDashSection (M5)", () => {
  it("maps executors → 'executor' and macros → 'macro'", () => {
    expect(targetKindForDashSection("executors")).toBe("executor");
    expect(targetKindForDashSection("macros")).toBe("macro");
  });

  it("read-only dash sections (groups/preset_pools/plugins/fixtures) map to null — structurally never fire", () => {
    expect(targetKindForDashSection("groups")).toBeNull();
    expect(targetKindForDashSection("preset_pools")).toBeNull();
    expect(targetKindForDashSection("plugins")).toBeNull();
    expect(targetKindForDashSection("fixtures")).toBeNull();
  });
});

// AC-DASHUI-005 — the executor fire target is the server-VERIFIED console
// number, never the pool slot (live-measured: page 1 slot 1 = "Executor 101").
describe("dashPressTargetNo", () => {
  it("executors fire meta.console_no, not the pool-slot no", () => {
    const item = { no: 1, name: "Sequence 50", meta: { resolved: true, console_no: 101 } };
    expect(dashPressTargetNo("executors", item)).toBe(101);
  });

  it("an executor without a verified console number never fires (fail-closed)", () => {
    expect(dashPressTargetNo("executors", { no: 1, name: "Sequence 50" })).toBeNull();
    expect(
      dashPressTargetNo("executors", { no: 1, name: "Sequence 50", meta: { resolved: false } }),
    ).toBeNull();
  });

  it("macros fire their own pool number unchanged", () => {
    expect(dashPressTargetNo("macros", { no: 3, name: "Blackout FX" })).toBe(3);
  });

  it("read-only sections have no press target at all", () => {
    expect(dashPressTargetNo("groups", { no: 1, name: "Vocals" })).toBeNull();
  });
});

describe("AppShell — console-primary split layout (M6 inversion)", () => {
  it("chat open: mounts exactly one DashBoard node alongside the untouched chat children", () => {
    const element = AppShell({
      chatCollapsed: false,
      dash: initialState.dash,
      onToggleChat: vi.fn(),
      children: CHAT_SENTINEL,
    }) as ReactElement;

    expect(element.type).toBe("div");
    expect(element.props.className).toBe("app-shell chat-split");

    const children = childArray(element);
    const dashboardNodes = children.filter(
      (child) => (child as ReactElement | null)?.type === DashBoard,
    ) as ReactElement[];
    expect(dashboardNodes).toHaveLength(1);
    expect(dashboardNodes[0].props.dash).toBe(initialState.dash);
    expect(children).toContain(CHAT_SENTINEL);
  });

  it("chat collapsed: DashBoard STILL mounts (console pane is permanent) and a chat-rail re-open button replaces the chat children", () => {
    const onToggleChat = vi.fn();
    const element = AppShell({
      chatCollapsed: true,
      dash: initialState.dash,
      onToggleChat,
      children: CHAT_SENTINEL,
    }) as ReactElement;

    expect(element.props.className).toBe("app-shell chat-collapsed");

    const children = childArray(element);
    const dashboardNodes = children.filter(
      (child) => (child as ReactElement | null)?.type === DashBoard,
    );
    expect(dashboardNodes).toHaveLength(1);
    expect(children).not.toContain(CHAT_SENTINEL);

    const rail = children.find(
      (child) => (child as ReactElement | null)?.props?.className === "chat-rail",
    ) as ReactElement;
    expect(rail).toBeDefined();
    const railButton = (
      Array.isArray(rail.props.children) ? rail.props.children[0] : rail.props.children
    ) as ReactElement;
    expect(railButton.props["aria-label"]).toBe("채팅 펼치기");
    railButton.props.onClick();
    expect(onToggleChat).toHaveBeenCalledTimes(1);
  });

  it("does not offer a dashboard collapse affordance — DashBoard's onToggleCollapse slot stays undefined", () => {
    const element = AppShell({
      chatCollapsed: false,
      dash: initialState.dash,
      onToggleChat: vi.fn(),
      children: CHAT_SENTINEL,
    }) as ReactElement;
    const children = childArray(element) as ReactElement[];
    const dashboardNode = children.find((child) => child?.type === DashBoard) as ReactElement;

    expect(dashboardNode.props.onToggleCollapse).toBeUndefined();
  });

  // M5 (design.md §4, REQ-DASHUI-017) — press/refresh/running wiring passthrough.
  it("threads onRefresh/isItemRunning/onItemPress through to DashBoard unchanged", () => {
    const onRefresh = vi.fn();
    const isItemRunning = vi.fn();
    const onItemPress = vi.fn();
    const element = AppShell({
      chatCollapsed: false,
      dash: initialState.dash,
      onToggleChat: vi.fn(),
      onRefresh,
      isItemRunning,
      onItemPress,
      children: CHAT_SENTINEL,
    }) as ReactElement;
    const children = childArray(element) as ReactElement[];
    const dashboardNode = children.find((child) => child?.type === DashBoard) as ReactElement;

    expect(dashboardNode.props.onRefresh).toBe(onRefresh);
    expect(dashboardNode.props.isItemRunning).toBe(isItemRunning);
    expect(dashboardNode.props.onItemPress).toBe(onItemPress);
  });

  it("omitting onRefresh/isItemRunning/onItemPress leaves DashBoard's slots undefined — no forced stub", () => {
    const element = AppShell({
      chatCollapsed: false,
      dash: initialState.dash,
      onToggleChat: vi.fn(),
      children: CHAT_SENTINEL,
    }) as ReactElement;
    const children = childArray(element) as ReactElement[];
    const dashboardNode = children.find((child) => child?.type === DashBoard) as ReactElement;

    expect(dashboardNode.props.onRefresh).toBeUndefined();
    expect(dashboardNode.props.isItemRunning).toBeUndefined();
    expect(dashboardNode.props.onItemPress).toBeUndefined();
  });

  it("never mutates or wraps the passed children — same value passes through unchanged when chat is open", () => {
    const split = AppShell({
      chatCollapsed: false,
      dash: initialState.dash,
      onToggleChat: vi.fn(),
      children: CHAT_SENTINEL,
    }) as ReactElement;

    expect(childArray(split)).toContain(CHAT_SENTINEL);
  });
});
