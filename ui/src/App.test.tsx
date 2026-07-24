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

import { AppShell } from "./App";
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

describe("AppShell — split-pane layout (M3)", () => {
  it("collapsed: renders exactly the passed children, zero DashBoard nodes — matches today's single-column chat view (AC-DASHUI-009)", () => {
    const element = AppShell({
      dashCollapsed: true,
      dash: initialState.dash,
      onToggleDash: vi.fn(),
      children: CHAT_SENTINEL,
    }) as ReactElement;

    expect(element.type).toBe("div");
    expect(element.props.className).toBe("app-shell dash-collapsed");

    const children = childArray(element);
    const dashboardNodes = children.filter(
      (child) => (child as ReactElement | null)?.type === DashBoard,
    );
    expect(dashboardNodes).toHaveLength(0);
    expect(children).toContain(CHAT_SENTINEL);
  });

  it("split: mounts exactly one DashBoard node alongside the untouched chat children", () => {
    const element = AppShell({
      dashCollapsed: false,
      dash: initialState.dash,
      onToggleDash: vi.fn(),
      children: CHAT_SENTINEL,
    }) as ReactElement;

    expect(element.props.className).toBe("app-shell dash-split");

    const children = childArray(element);
    const dashboardNodes = children.filter(
      (child) => (child as ReactElement | null)?.type === DashBoard,
    ) as ReactElement[];
    expect(dashboardNodes).toHaveLength(1);
    expect(dashboardNodes[0].props.dash).toBe(initialState.dash);
    expect(children).toContain(CHAT_SENTINEL);
  });

  it("wires DashBoard's onToggleCollapse to the same onToggleDash callback the shell received", () => {
    const onToggleDash = vi.fn();
    const element = AppShell({
      dashCollapsed: false,
      dash: initialState.dash,
      onToggleDash,
      children: CHAT_SENTINEL,
    }) as ReactElement;
    const children = childArray(element) as ReactElement[];
    const dashboardNode = children.find((child) => child?.type === DashBoard) as ReactElement;

    dashboardNode.props.onToggleCollapse();
    expect(onToggleDash).toHaveBeenCalledTimes(1);
  });

  it("never mutates or wraps the passed children — same value passes through unchanged in both layout states", () => {
    const collapsed = AppShell({
      dashCollapsed: true,
      dash: initialState.dash,
      onToggleDash: vi.fn(),
      children: CHAT_SENTINEL,
    }) as ReactElement;
    const split = AppShell({
      dashCollapsed: false,
      dash: initialState.dash,
      onToggleDash: vi.fn(),
      children: CHAT_SENTINEL,
    }) as ReactElement;

    expect(childArray(collapsed)).toContain(CHAT_SENTINEL);
    expect(childArray(split)).toContain(CHAT_SENTINEL);
  });
});
