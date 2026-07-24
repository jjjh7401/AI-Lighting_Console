// PoolTile structural tests (M4 — SPEC-COPILOT-DASHUI-001, plan.md §B M4,
// design.md §3 "풀 셀(슬롯)" / §7 rule 7, REQ-DASHUI-010/011/016/017).
//
// Mocked-fidelity bound: this project has no DOM/jsdom test harness (see
// protocol.ts's own header). PoolTile is hook-free by design, so it is
// called directly as a plain function and the returned React element tree
// is inspected — the same technique DashBoard.test.tsx and
// ApprovalCard.test.tsx already apply.
import type { ReactElement } from "react";
import { describe, expect, it, vi } from "vitest";

import { type DashItem } from "../protocol";
import { PoolTile } from "./PoolTile";

function childArray(element: ReactElement): unknown[] {
  const children = element.props.children;
  if (children === undefined) return [];
  const list = Array.isArray(children) ? children : [children];
  // Conditional JSX children (`{cond ? <X/> : null}`) leave a real `null`
  // entry in the children array when the condition is false — filter those
  // out so positional assertions reflect only the elements actually shown.
  return list.filter((child) => child !== null && child !== undefined && child !== false);
}

const OCCUPIED_ITEM: DashItem = { no: 5, name: "Cyc Wash", appearance: "#ffcc00" };
const UNRESOLVED_EXECUTOR: DashItem = { no: 41, name: "Look 41", meta: { resolved: false } };
const RESOLVED_EXECUTOR: DashItem = { no: 41, name: "Look 41", meta: { resolved: true } };

describe("PoolTile", () => {
  it("renders a slot cell with the REAL no as a first-class element and the name", () => {
    const element = PoolTile({ item: OCCUPIED_ITEM, pressable: false }) as ReactElement;
    expect(element.type).toBe("div");
    expect(element.props.className).toContain("pool-tile");

    const [no, name] = childArray(element) as ReactElement[];
    expect(no.type).toBe("span");
    expect(no.props.className).toBe("pool-tile-no");
    expect(no.props.children).toBe(5);
    expect(name.type).toBe("span");
    expect(name.props.className).toBe("pool-tile-name");
    expect(name.props.children).toBe("Cyc Wash");
  });

  it("renders an appearance chip when the item carries one, and omits it otherwise", () => {
    const withAppearance = PoolTile({ item: OCCUPIED_ITEM, pressable: false }) as ReactElement;
    const children = childArray(withAppearance) as ReactElement[];
    const chip = children.find((child) => child.props?.className === "pool-tile-appearance");
    expect(chip).toBeDefined();
    expect(chip!.props.style).toEqual({ background: "#ffcc00" });

    const noAppearance: DashItem = { no: 6, name: "No Chip" };
    const withoutAppearance = PoolTile({ item: noAppearance, pressable: false }) as ReactElement;
    const noChip = (childArray(withoutAppearance) as ReactElement[]).find(
      (child) => child.props?.className === "pool-tile-appearance",
    );
    expect(noChip).toBeUndefined();
  });

  it("read-only tile (pressable=false) carries NO verb button — design.md §7 rule 7", () => {
    const element = PoolTile({ item: OCCUPIED_ITEM, pressable: false }) as ReactElement;
    const button = (childArray(element) as ReactElement[]).find((child) => child.type === "button");
    expect(button).toBeUndefined();
    expect(element.props.className).toBe("pool-tile pool-tile-info");
  });

  it("press-able tile renders a verb button with press-affordance class + onClick wired", () => {
    const onPress = vi.fn();
    const element = PoolTile({
      item: OCCUPIED_ITEM,
      pressable: true,
      verb: "Go+",
      onPress,
    }) as ReactElement;

    expect(element.props.className).toBe("pool-tile pool-tile-press");
    const button = (childArray(element) as ReactElement[]).find(
      (child) => child.type === "button",
    ) as ReactElement;
    expect(button).toBeDefined();
    expect(button.props.children).toBe("Go+");
    expect(typeof button.props.onClick).toBe("function");
    button.props.onClick();
    expect(onPress).toHaveBeenCalledWith(OCCUPIED_ITEM);
  });

  it("press-able tile with no onPress still renders the button but its onClick is a no-op (undefined)", () => {
    const element = PoolTile({ item: OCCUPIED_ITEM, pressable: true, verb: "Macro" }) as ReactElement;
    const button = (childArray(element) as ReactElement[]).find(
      (child) => child.type === "button",
    ) as ReactElement;
    expect(button.props.onClick).toBeUndefined();
  });

  it("unresolved executor (pressable=false, meta.resolved=false) renders an info-only badge, no click affordance", () => {
    const element = PoolTile({ item: UNRESOLVED_EXECUTOR, pressable: false }) as ReactElement;
    expect(element.props.className).toBe("pool-tile pool-tile-info");
    const badge = (childArray(element) as ReactElement[]).find(
      (child) => child.props?.className === "pool-tile-unresolved",
    );
    expect(badge).toBeDefined();
    expect(badge!.props.children).toBe("정보만");
    const button = (childArray(element) as ReactElement[]).find((child) => child.type === "button");
    expect(button).toBeUndefined();
  });

  it("resolved executor rendered as pressable carries no info-only badge", () => {
    const element = PoolTile({
      item: RESOLVED_EXECUTOR,
      pressable: true,
      verb: "Go+",
    }) as ReactElement;
    const badge = (childArray(element) as ReactElement[]).find(
      (child) => child.props?.className === "pool-tile-unresolved",
    );
    expect(badge).toBeUndefined();
  });

  it("empty name falls back to an em-dash placeholder rather than rendering blank", () => {
    const blank: DashItem = { no: 1, name: "" };
    const element = PoolTile({ item: blank, pressable: false }) as ReactElement;
    const [, name] = childArray(element) as ReactElement[];
    expect(name.props.children).toBe("—");
  });
});
