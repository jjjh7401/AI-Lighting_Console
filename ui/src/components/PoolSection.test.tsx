// PoolSection structural tests (M4 — SPEC-COPILOT-DASHUI-001, plan.md §B M4,
// design.md §2/§3, REQ-DASHUI-004/008/010/018).
//
// Mocked-fidelity bound: this project has no DOM/jsdom test harness (see
// protocol.ts's own header). PoolSection is hook-free by design, so it is
// called directly as a plain function and the returned React element tree
// is inspected.
import type { ReactElement } from "react";
import { describe, expect, it, vi } from "vitest";

import { type DashItem, type DashSection } from "../protocol";
import { PoolSection, sectionHealthLabel } from "./PoolSection";

function childArray(element: ReactElement): unknown[] {
  const children = element.props.children;
  if (children === undefined) return [];
  const list = Array.isArray(children) ? children : [children];
  // Conditional JSX children (`{cond ? <X/> : null}`) leave a real `null`
  // entry in the children array when the condition is false — filter those
  // out so positional assertions reflect only the elements actually shown.
  return list.filter((child) => child !== null && child !== undefined && child !== false);
}

const OK_SECTION: DashSection = {
  name: "groups",
  status: "ok",
  items: [
    { no: 3, name: "Wash" },
    { no: 12, name: "Cyc" },
  ],
};

describe("sectionHealthLabel", () => {
  it("returns null for a fully-healthy section with no flags", () => {
    expect(sectionHealthLabel(OK_SECTION)).toBeNull();
  });

  it("distinguishes path_not_resolved from console_unreachable — never a generic 'error'", () => {
    const notResolved: DashSection = { name: "macros", status: "path_not_resolved", items: [] };
    const unreachable: DashSection = { name: "macros", status: "console_unreachable", items: [] };
    const resolvedLabel = sectionHealthLabel(notResolved);
    const unreachableLabel = sectionHealthLabel(unreachable);
    expect(resolvedLabel).not.toBeNull();
    expect(unreachableLabel).not.toBeNull();
    expect(resolvedLabel).not.toBe(unreachableLabel);
  });

  it("surfaces truncated/drilldown_capped/contents_unavailable honestly instead of silent capping", () => {
    const truncated: DashSection = { name: "groups", status: "ok", items: [], truncated: true };
    const capped: DashSection = { name: "preset_pools", status: "ok", items: [], drilldown_capped: true };
    const unavailable: DashSection = {
      name: "preset_pools",
      status: "ok",
      items: [],
      contents_unavailable: true,
    };
    expect(sectionHealthLabel(truncated)).not.toBeNull();
    expect(sectionHealthLabel(capped)).not.toBeNull();
    expect(sectionHealthLabel(unavailable)).not.toBeNull();
  });
});

describe("PoolSection", () => {
  it("renders a header with the label and no health badge when healthy", () => {
    const element = PoolSection({
      section: OK_SECTION,
      label: "그룹",
      isPressable: () => false,
    }) as ReactElement;

    expect(element.type).toBe("section");
    const [header] = childArray(element) as ReactElement[];
    expect(header.type).toBe("header");
    const headerChildren = childArray(header) as ReactElement[];
    expect(headerChildren[0].props.children).toBe("그룹");
    expect(headerChildren.length).toBe(1);
  });

  it("renders items in WIRE order — no sort/reflow (AC-DASHUI-010)", () => {
    const element = PoolSection({
      section: OK_SECTION,
      label: "그룹",
      isPressable: () => false,
    }) as ReactElement;
    const [, grid] = childArray(element) as ReactElement[];
    const tiles = childArray(grid) as ReactElement[];
    expect(tiles.map((tile) => tile.props.item.no)).toEqual([3, 12]);
  });

  it("renders an empty-state placeholder for a section with zero items — not an error", () => {
    const empty: DashSection = { name: "macros", status: "ok", items: [] };
    const element = PoolSection({ section: empty, label: "매크로", isPressable: () => true }) as ReactElement;
    const [, body] = childArray(element) as ReactElement[];
    expect(body.props.className).toBe("pool-section-empty");
  });

  it("delegates per-item pressability to the caller predicate — never decides it itself", () => {
    const executors: DashSection = {
      name: "executors",
      status: "ok",
      items: [
        { no: 101, name: "Resolved", meta: { resolved: true } },
        { no: 102, name: "Unresolved", meta: { resolved: false } },
      ],
    };
    const isPressable = (item: DashItem) => item.meta?.resolved === true;
    const element = PoolSection({
      section: executors,
      label: "익스큐터",
      isPressable,
      verb: "Go+",
    }) as ReactElement;
    const [, grid] = childArray(element) as ReactElement[];
    const tiles = childArray(grid) as ReactElement[];
    expect(tiles[0].props.pressable).toBe(true);
    expect(tiles[1].props.pressable).toBe(false);
  });

  it("passes onPress through to every tile unchanged", () => {
    const onPress = vi.fn();
    const element = PoolSection({
      section: OK_SECTION,
      label: "그룹",
      isPressable: () => false,
      onPress,
    }) as ReactElement;
    const [, grid] = childArray(element) as ReactElement[];
    const tiles = childArray(grid) as ReactElement[];
    expect(tiles.every((tile) => tile.props.onPress === onPress)).toBe(true);
  });

  it("shows the health badge text inside the header when the section is not fully healthy", () => {
    const capped: DashSection = { name: "preset_pools", status: "ok", items: [], drilldown_capped: true };
    const element = PoolSection({
      section: capped,
      label: "프리셋",
      isPressable: () => false,
    }) as ReactElement;
    const [header] = childArray(element) as ReactElement[];
    const headerChildren = childArray(header) as ReactElement[];
    expect(headerChildren.length).toBe(2);
    expect(headerChildren[1].props.className).toBe("pool-section-health");
  });
});
