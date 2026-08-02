// Stylesheet-guard test (M4 — SPEC-COPILOT-DASHUI-001, plan.md §B M4,
// design.md §3, REQ-DASHUI-016/017). Recreated fresh on this branch — the
// SHOWUI-001 M4 stylesheet-guard pattern this follows lives at
// ui/src/styles.test.ts on commit 857e9ed, which is NOT an ancestor of this
// branch (plan.md §E R1, research.md §3) — it is a reference for the
// TECHNIQUE only, not a cherry-pick source.
//
// Pure string/regex parsing over the raw CSS text — this project has no
// DOM/jsdom test harness (see protocol.ts's own header), so this file reads
// styles.css with node:fs and walks flat `selector { body }` blocks with a
// regex rather than any CSSOM/browser API. styles.css has exactly one nested
// at-rule (T-H's `@media (prefers-reduced-motion: reduce)` carve-out) — the
// flat splitter still finds the INNER selector correctly (see the describe
// block below), so a single-level block split stays sufficient.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const CSS_PATH = fileURLToPath(new URL("./styles.css", import.meta.url));
const css = readFileSync(CSS_PATH, "utf-8");

interface CssBlock {
  selector: string;
  body: string;
}

/** Strip `/* ... *\/` comments so a comment's own text never leaks into the
 * following rule's parsed selector (comments contain no `{`/`}`, so the
 * naive block-splitter below would otherwise swallow them into `selector`). */
function stripComments(source: string): string {
  return source.replace(/\/\*[\s\S]*?\*\//g, "");
}

/** Split the (flat, @media-free) stylesheet into `{ selector, body }` blocks. */
function parseBlocks(source: string): CssBlock[] {
  const blocks: CssBlock[] = [];
  const re = /([^{}]+)\{([^{}]*)\}/g;
  let match: RegExpExecArray | null;
  while ((match = re.exec(source)) !== null) {
    blocks.push({ selector: match[1].trim(), body: match[2] });
  }
  return blocks;
}

const blocks = parseBlocks(stripComments(css));

/** The declared font-size (px, numeric) for a selector's own block, or null. */
function declaredFontSizePx(selector: string): number | null {
  const block = blocks.find((b) => b.selector === selector);
  if (!block) return null;
  const found = block.body.match(/font-size:\s*(\d+)px/);
  return found ? Number(found[1]) : null;
}

describe("styles.css — @media is restricted to the T-H prefers-reduced-motion carve-out", () => {
  // T-H (coordinator directive, 2026-08-02) adds exactly ONE nested at-rule:
  // the reduced-motion fallback for the cue-status acknowledgement pulse
  // (CueMonitor.tsx). The flat block-splitter still parses the INNER
  // selector correctly (the @media wrapper text is simply not captured as
  // its own block), so this stays additive rather than requiring a real
  // CSS parser — every @media in the file must be this one carve-out.
  it("every @media block is the prefers-reduced-motion carve-out", () => {
    const mediaBlocks = css.match(/@media[^{]*\{/g) ?? [];
    expect(mediaBlocks.length).toBeGreaterThan(0);
    for (const block of mediaBlocks) {
      expect(block).toMatch(/prefers-reduced-motion:\s*reduce/);
    }
  });

  it("parsed at least one block (sanity check the regex actually matched)", () => {
    expect(blocks.length).toBeGreaterThan(10);
  });
});

describe("--live-amber token exclusivity (REQ-DASHUI-017)", () => {
  it("is defined exactly once, inside :root", () => {
    const rootBlock = blocks.find((b) => b.selector === ":root");
    expect(rootBlock).toBeDefined();
    const definitions = css.match(/--live-amber:\s*#[0-9a-fA-F]{3,8};/g) ?? [];
    expect(definitions).toHaveLength(1);
    expect(rootBlock!.body).toMatch(/--live-amber:/);
  });

  it("is referenced (var(--live-amber)) ONLY inside a .pool-tile-running-scoped selector — never for any other, non-running state", () => {
    const usages = blocks.filter((b) => b.body.includes("var(--live-amber)"));
    expect(usages.length).toBeGreaterThan(0);
    for (const usage of usages) {
      expect(usage.selector).toMatch(/\.pool-tile-running/);
    }
  });

  it("is never referenced by an 'occupied slot' or generic tile selector (.pool-tile alone, .pool-tile-press, .pool-tile-info)", () => {
    const forbiddenSelectors = [".pool-tile", ".pool-tile-press", ".pool-tile-info"];
    for (const selector of forbiddenSelectors) {
      const block = blocks.find((b) => b.selector === selector);
      if (block) {
        expect(block.body).not.toMatch(/var\(--live-amber\)/);
      }
    }
  });
});

describe("15px label floor for M4 primary labels (design.md §3 '라벨 최소 15px')", () => {
  const primaryLabelSelectors = [
    ".pool-tile-no",
    ".pool-tile-name",
    ".pool-tile-verb",
    ".pool-section-label",
    ".dashboard-summary",
  ];

  it.each(primaryLabelSelectors)("%s declares font-size >= 15px", (selector) => {
    const size = declaredFontSizePx(selector);
    expect(size).not.toBeNull();
    expect(size!).toBeGreaterThanOrEqual(15);
  });
});

describe("existing :root tokens are additive-only (REQ-DASHUI-016 — extend, never replace)", () => {
  const preExistingTokens = ["--bg", "--panel", "--text", "--muted", "--accent", "--ok", "--warn", "--bad"];

  it.each(preExistingTokens)("%s is still defined in :root", (token) => {
    const rootBlock = blocks.find((b) => b.selector === ":root");
    expect(rootBlock).toBeDefined();
    expect(rootBlock!.body).toMatch(new RegExp(`${token}:\\s*#`));
  });
});

describe("--live-amber stays exclusive to .pool-tile-running even after T-H5's action-button colours", () => {
  // T-H5 adds .cue-monitor-action-btn-back/-stop colour variants; this
  // re-asserts the pre-existing REQ-DASHUI-017 exclusivity guard still holds
  // (a regression a careless copy-paste of --live-amber into a new button
  // variant would otherwise slip past unnoticed).
  it("no cue-monitor-action-btn selector references var(--live-amber)", () => {
    const actionButtonBlocks = blocks.filter((b) => b.selector.startsWith(".cue-monitor-action-btn"));
    expect(actionButtonBlocks.length).toBeGreaterThan(0);
    for (const block of actionButtonBlocks) {
      expect(block.body).not.toMatch(/var\(--live-amber\)/);
    }
  });
});

describe("T-H5 tile density — the grid fits multiple tiles side by side (task #8/#9)", () => {
  // A regression guard on the MINMAX value driving column count
  // (`repeat(auto-fill, minmax(<px>, 1fr))`): T-H4 shipped at 150px, which
  // left the pane at ONE column — the exact "MA3 executor-bar 느낌이 안
  // 난다" complaint T-H5 fixes. This pins the value low enough that at least
  // two ~104px tiles plus their gap fit inside a typical cue-monitor pane
  // width (documented assumption: >= 260px content width, this app's
  // right-side panel is comfortably wider than that in practice).
  it("cue-monitor-grid's tile minmax is narrow enough for 2+ columns at typical pane width", () => {
    const block = blocks.find((b) => b.selector === ".cue-monitor-grid");
    expect(block).toBeDefined();
    const match = block!.body.match(/minmax\((\d+)px/);
    expect(match).not.toBeNull();
    const minmaxPx = Number(match![1]);
    const gapMatch = block!.body.match(/gap:\s*(\d+)px/);
    const gapPx = gapMatch ? Number(gapMatch[1]) : 0;
    const ASSUMED_PANE_CONTENT_WIDTH_PX = 260;
    expect(minmaxPx * 2 + gapPx).toBeLessThanOrEqual(ASSUMED_PANE_CONTENT_WIDTH_PX);
  });
});
