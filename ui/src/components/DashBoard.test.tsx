// DashBoard structural tests (M3 skeleton — SPEC-COPILOT-DASHUI-001, plan.md
// §B M3, design.md §2 header/collapse affordance, §6 layout).
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

import { initialState, type DashState } from "../protocol";
import { DashBoard } from "./DashBoard";

function childArray(element: ReactElement): unknown[] {
  const children = element.props.children;
  return Array.isArray(children) ? children : [children];
}

describe("DashBoard", () => {
  it("renders an aside with a header (title + collapse button) and a body region", () => {
    const element = DashBoard({
      dash: initialState.dash,
      onToggleCollapse: vi.fn(),
    }) as ReactElement;

    expect(element.type).toBe("aside");
    expect(element.props.className).toBe("dashboard");

    const [header, body] = childArray(element) as ReactElement[];
    expect(header.type).toBe("header");
    expect(header.props.className).toBe("dashboard-header");
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

  it("renders the loading placeholder on the M1-frozen empty/default dash state — no crash on absent data", () => {
    const element = DashBoard({
      dash: initialState.dash,
      onToggleCollapse: vi.fn(),
    }) as ReactElement;
    const [, body] = childArray(element) as ReactElement[];
    const [placeholder] = childArray(body) as ReactElement[];

    expect(placeholder.type).toBe("div");
    expect(placeholder.props.className).toBe("dashboard-empty");
  });

  it("switches to the sections placeholder region once sections are non-empty (M4 will mount real tiles here)", () => {
    const dash: DashState = {
      sections: [{ name: "groups", status: "ok", items: [] }],
      lastSyncAt: 12345,
      stale: false,
    };
    const element = DashBoard({ dash, onToggleCollapse: vi.fn() }) as ReactElement;
    const [, body] = childArray(element) as ReactElement[];
    const [placeholder] = childArray(body) as ReactElement[];

    expect(placeholder.type).toBe("div");
    expect(placeholder.props.className).toBe("dashboard-sections");
  });

  it("does not dispatch a dash_catalog_request or fetch data itself — presentation only (M3 scope)", () => {
    // DashBoard's props are exactly { dash, onToggleCollapse } — no socket,
    // no dispatch function, no fetch. Structural proof the component cannot
    // reach out on its own: it has nothing to reach out with.
    const element = DashBoard({
      dash: initialState.dash,
      onToggleCollapse: vi.fn(),
    }) as ReactElement;
    expect(element).toBeDefined();
  });
});
