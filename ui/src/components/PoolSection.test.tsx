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
import {
  clampPoolArea,
  clampPoolTileSize,
  POOL_AREA_DEFAULT,
  POOL_AREA_MAX_WIDTH,
  POOL_AREA_MIN_HEIGHT,
  POOL_TILE_DEFAULT_SIZE,
  POOL_TILE_MAX_SIZE,
  POOL_TILE_MIN_SIZE,
  POOL_TILE_SIZE_STEP,
  PoolSection,
  sectionHealthLabel,
} from "./PoolSection";

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

  // M5 (design.md §4, REQ-DASHUI-017) — running-state verb switch (Go+/Off).
  describe("running verb switch (M5)", () => {
    const EXECUTORS: DashSection = {
      name: "executors",
      status: "ok",
      items: [
        { no: 101, name: "Running", meta: { resolved: true } },
        { no: 102, name: "Idle", meta: { resolved: true } },
      ],
    };

    it("running item gets the runningVerb + running=true; idle item keeps the default verb + running=false", () => {
      const isRunning = (item: DashItem) => item.no === 101;
      const element = PoolSection({
        section: EXECUTORS,
        label: "익스큐터",
        isPressable: () => true,
        verb: "Go+",
        runningVerb: "Off",
        isRunning,
      }) as ReactElement;
      const [, grid] = childArray(element) as ReactElement[];
      const [runningTile, idleTile] = childArray(grid) as ReactElement[];
      expect(runningTile.props.verb).toBe("Off");
      expect(runningTile.props.running).toBe(true);
      expect(idleTile.props.verb).toBe("Go+");
      expect(idleTile.props.running).toBe(false);
    });

    it("omitting isRunning defaults every tile to not-running (backward compatible with M4 callers)", () => {
      const element = PoolSection({
        section: EXECUTORS,
        label: "익스큐터",
        isPressable: () => true,
        verb: "Go+",
      }) as ReactElement;
      const [, grid] = childArray(element) as ReactElement[];
      const tiles = childArray(grid) as ReactElement[];
      expect(tiles.every((tile) => tile.props.running === false)).toBe(true);
    });

    it("a one-shot section with no runningVerb (macros) never switches its verb even when isRunning reports true", () => {
      const macros: DashSection = {
        name: "macros",
        status: "ok",
        items: [{ no: 7, name: "Blackout" }],
      };
      const element = PoolSection({
        section: macros,
        label: "매크로",
        isPressable: () => true,
        verb: "Macro",
        isRunning: () => true,
      }) as ReactElement;
      const [, grid] = childArray(element) as ReactElement[];
      const [tile] = childArray(grid) as ReactElement[];
      expect(tile.props.verb).toBe("Macro");
    });

    it("running never applies to a non-pressable item, even if isRunning would report true", () => {
      const element = PoolSection({
        section: EXECUTORS,
        label: "익스큐터",
        isPressable: () => false,
        isRunning: () => true,
      }) as ReactElement;
      const [, grid] = childArray(element) as ReactElement[];
      const tiles = childArray(grid) as ReactElement[];
      expect(tiles.every((tile) => tile.props.running === false)).toBe(true);
    });
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

// M6-UX v3 — onPC pool-window model (user direction): SQUARE cells stepped
// by −/+, and the WINDOW's on-screen area resized by dragging its corner.
describe("PoolSection — square cells + window area", () => {
  function headerOf(element: ReactElement): ReactElement {
    return childArray(element)[0] as ReactElement;
  }
  function sizeButtons(element: ReactElement): ReactElement[] {
    const controls = childArray(headerOf(element)).find(
      (child) => (child as ReactElement)?.props?.className === "pool-size-control",
    ) as ReactElement | undefined;
    return controls ? (childArray(controls) as ReactElement[]) : [];
  }
  function cornerHandle(element: ReactElement): ReactElement | undefined {
    return childArray(element).find(
      (child) => (child as ReactElement)?.props?.className === "pool-area-resize",
    ) as ReactElement | undefined;
  }

  it("clamps cell size and window area into their legal ranges", () => {
    expect(clampPoolTileSize(1)).toBe(POOL_TILE_MIN_SIZE);
    expect(clampPoolTileSize(10_000)).toBe(POOL_TILE_MAX_SIZE);
    expect(clampPoolArea({ width: 10_000, height: 1 })).toEqual({
      width: POOL_AREA_MAX_WIDTH,
      height: POOL_AREA_MIN_HEIGHT,
    });
  });

  it("renders fixed SQUARE cell columns from tileSize and the window area from the area prop", () => {
    const element = PoolSection({
      section: OK_SECTION,
      label: "그룹",
      isPressable: () => false,
      tileSize: 120,
      area: { width: 600, height: 300 },
    }) as ReactElement;
    expect(element.props.style).toEqual({ width: "600px", height: "300px" });
    const grid = childArray(element)[1] as ReactElement;
    expect(grid.props.style.gridTemplateColumns).toBe("repeat(auto-fill, 120px)");
  });

  it("defaults tileSize/area when omitted", () => {
    const element = PoolSection({
      section: OK_SECTION,
      label: "그룹",
      isPressable: () => false,
    }) as ReactElement;
    expect(element.props.style).toEqual({
      width: `${POOL_AREA_DEFAULT.width}px`,
      height: `${POOL_AREA_DEFAULT.height}px`,
    });
    const grid = childArray(element)[1] as ReactElement;
    expect(grid.props.style.gridTemplateColumns).toBe(
      `repeat(auto-fill, ${POOL_TILE_DEFAULT_SIZE}px)`,
    );
  });

  it("−/+ step the cell size (clamped) ONLY when onTileSizeChange is provided", () => {
    const without = PoolSection({
      section: OK_SECTION,
      label: "그룹",
      isPressable: () => false,
    }) as ReactElement;
    expect(sizeButtons(without)).toHaveLength(0);

    const onTileSizeChange = vi.fn();
    const element = PoolSection({
      section: OK_SECTION,
      label: "그룹",
      isPressable: () => false,
      tileSize: POOL_TILE_MIN_SIZE,
      onTileSizeChange,
    }) as ReactElement;
    const [smaller, larger] = sizeButtons(element);
    expect(smaller.props["aria-label"]).toBe("셀 작게");
    smaller.props.onClick();
    expect(onTileSizeChange).toHaveBeenLastCalledWith(POOL_TILE_MIN_SIZE); // clamped floor
    larger.props.onClick();
    expect(onTileSizeChange).toHaveBeenLastCalledWith(
      POOL_TILE_MIN_SIZE + POOL_TILE_SIZE_STEP,
    );
  });

  it("the corner handle forwards its mouse-down ONLY when onAreaResizeStart is provided", () => {
    const without = PoolSection({
      section: OK_SECTION,
      label: "그룹",
      isPressable: () => false,
    }) as ReactElement;
    expect(cornerHandle(without)).toBeUndefined();

    const onAreaResizeStart = vi.fn();
    const element = PoolSection({
      section: OK_SECTION,
      label: "그룹",
      isPressable: () => false,
      onAreaResizeStart,
    }) as ReactElement;
    const handle = cornerHandle(element);
    expect(handle).toBeDefined();
    expect(handle!.props["aria-label"]).toBe("영역 크기 조절 — 모서리를 드래그");
    handle!.props.onMouseDown({ clientX: 700, clientY: 400 });
    expect(onAreaResizeStart).toHaveBeenCalledWith({ clientX: 700, clientY: 400 });
  });
});
