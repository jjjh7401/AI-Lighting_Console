// Stylesheet colour-contract guard (SPEC-COPILOT-SHOWUI-001 M4 —
// REQ-SHOWUI-018, AC-SHOWUI-011 "running일 때만 live-amber 토큰 적용").
//
// The component tests assert which CLASS a tile wears; they cannot see what
// that class is actually painted. Live-amber's whole value is that it means one
// thing — an operator scanning a dark FOH panel for "what is playing right now"
// finds it in one glance — and that value is destroyed by a single decorative
// use anywhere in the sheet. The rule is therefore enforced against the
// stylesheet itself rather than against class names.
//
// Reading the file with node:fs keeps this DOM-free and adds no dependency
// (design.md §7 / no-new-deps): the assertions are over text, not over a
// rendered document.
import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

const CSS = readFileSync(new URL("./styles.css", import.meta.url), "utf8");

/** The live-amber token, plus the literal forms of the same colour. */
const LIVE_TOKEN = /--live\b|#ffb02e|rgba\(\s*255\s*,\s*176\s*,\s*46/i;

/**
 * The ONLY selectors permitted to spend live-amber (design.md §3).
 *
 * Each one renders a state in which the console is actually playing something:
 * `:root` defines the token, `is-running`/`is-run`/`-live`/`-sweep` are the
 * running renders, and `.panel-tile-cue` only exists while running (`tileView`
 * nulls the cue the moment a tile stops). Adding a selector here is a design
 * decision, not a formatting one — anything that is not playback must use
 * another colour.
 */
const RUNNING_SELECTORS = new Set([
  ":root",
  ".panel-tile.is-running",
  ".panel-state-badge.is-run",
  ".panel-tile-cue",
  ".panel-rail-live",
  ".panel-rail-sweep",
]);

interface Block {
  selector: string;
  body: string;
}

/**
 * Innermost `selector { body }` pairs.
 *
 * Comments are stripped first: a rule's captured selector otherwise starts at
 * the previous rule's closing brace and swallows the comment above it, which
 * would make every lookup below miss.
 *
 * `[^{}]` on both sides means a nested block (an `@keyframes` wrapper) never
 * matches as one unit — its inner steps surface individually as `from`/`to`, so
 * a keyframe that painted live-amber would be caught rather than skipped.
 */
function blocks(css: string): Block[] {
  const withoutComments = css.replace(/\/\*[\s\S]*?\*\//g, "");
  const found: Block[] = [];
  const pattern = /([^{}]+)\{([^{}]*)\}/g;
  for (const match of withoutComments.matchAll(pattern)) {
    found.push({ selector: match[1].trim().replace(/\s+/g, " "), body: match[2] });
  }
  return found;
}

function fontSizePx(selector: string): number | null {
  const block = blocks(CSS).find((candidate) => candidate.selector === selector);
  if (block === undefined) return null;
  const size = /font-size:\s*(\d+(?:\.\d+)?)px/.exec(block.body);
  return size === null ? null : Number(size[1]);
}

describe("live-amber is spent on running and nothing else (REQ-SHOWUI-018)", () => {
  it("parses the stylesheet into blocks at all", () => {
    // Guards the guard: a parser that silently matched nothing would make every
    // assertion below vacuously true.
    const parsed = blocks(CSS);
    expect(parsed.length).toBeGreaterThan(50);
    expect(parsed.some((block) => block.selector === ":root")).toBe(true);
  });

  it("finds live-amber in the sheet — the token is actually in use", () => {
    const users = blocks(CSS).filter((block) => LIVE_TOKEN.test(block.body));
    expect(users.length).toBeGreaterThan(1);
  });

  it("spends it in running-state selectors only", () => {
    const offenders = blocks(CSS)
      .filter((block) => LIVE_TOKEN.test(block.body))
      .map((block) => block.selector)
      .filter((selector) => !RUNNING_SELECTORS.has(selector));

    // A non-empty list here names exactly which rule broke the contract.
    expect(offenders).toEqual([]);
  });

  it("declares the token once, in :root", () => {
    const declarations = blocks(CSS).filter((block) => /--live:\s*#/.test(block.body));

    expect(declarations).toHaveLength(1);
    expect(declarations[0].selector).toBe(":root");
  });

  it("never paints the arm-progress rail with it — arming is not running", () => {
    // All Off is a destructive FIRE control wearing Stop red (design.md §3/§6).
    // Painting its arm progress amber would put the "something is playing"
    // signal on a control that is about to stop everything.
    const arming = blocks(CSS).find((block) => block.selector === ".panel-rail-arming");

    expect(arming).toBeDefined();
    expect(LIVE_TOKEN.test(arming!.body)).toBe(false);
    expect(arming!.body).toMatch(/--bad/);
  });

  it("never paints a blocked, busy, proposal or hint state with it", () => {
    const nonRunning = [
      ".panel-block-banner",
      ".panel-proposal-banner",
      ".panel-tile-note",
      ".panel-tile.is-proposal",
      ".panel-section-hint.level-error",
      ".panel-section-hint.level-warn",
      ".panel-alloff-button",
    ];

    for (const selector of nonRunning) {
      const block = blocks(CSS).find((candidate) => candidate.selector === selector);
      expect(block, `${selector} should exist`).toBeDefined();
      expect(LIVE_TOKEN.test(block!.body), `${selector} must not use live-amber`).toBe(false);
    }
  });
});

describe("panel text is legible at arm's length (design.md §3, REQ-SHOWUI-018)", () => {
  it("sets the state badge at the 15px floor — it is the text half of the state", () => {
    // Colour alone never carries state, so RUN/OFF must be as readable as the
    // colour it accompanies. Below the floor the redundancy is nominal only.
    expect(fontSizePx(".panel-state-badge")).toBeGreaterThanOrEqual(15);
  });

  it("keeps the tile's own name and status line at the floor too", () => {
    expect(fontSizePx(".panel-tile-name")).toBeGreaterThanOrEqual(15);
    expect(fontSizePx(".panel-tile-meta")).toBeGreaterThanOrEqual(15);
  });

  it("keeps both press targets big enough for a gloved hand", () => {
    const actions = blocks(CSS).find(
      (block) => block.selector === ".panel-tile-actions button",
    );

    expect(actions).toBeDefined();
    expect(/min-height:\s*44px/.test(actions!.body)).toBe(true);
    expect(fontSizePx(".panel-tile-actions button")).toBeGreaterThanOrEqual(15);
  });
});

describe("the theme is dark, fixed (REQ-SHOWUI-020, design.md §7)", () => {
  it("pins color-scheme to dark with no light or auto anywhere", () => {
    expect(/color-scheme:\s*dark\s*;/.test(CSS)).toBe(true);
    expect(/color-scheme:\s*(light|auto|normal)/.test(CSS)).toBe(false);
    expect(/prefers-color-scheme/.test(CSS)).toBe(false);
  });

  it("keeps the pre-M4 base tokens untouched — M4 extends, never replaces", () => {
    for (const token of [
      "--bg: #14161a",
      "--panel: #1e2128",
      "--accent: #4f8cff",
      "--ok: #3fb950",
      "--warn: #d29922",
      "--bad: #f85149",
    ]) {
      expect(CSS).toContain(token);
    }
  });
});
