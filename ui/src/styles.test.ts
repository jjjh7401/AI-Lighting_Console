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
// regex rather than any CSSOM/browser API. styles.css has no @media or
// nested at-rules, so a single-level block split is sufficient.
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

describe("styles.css — no @media (single-level block parsing is valid)", () => {
  it("has no nested at-rule blocks that would break the flat parser", () => {
    expect(css).not.toMatch(/@media/);
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

// ---------------------------------------------------------------------------
// SHOWUI-inherited guard suite below — a SEPARATE stylesheet-guard contract for
// the show-control panel's own tile family (.panel-tile*), independent of the
// pool-tile guard suite above. Its own `panelBlocks()` parser is renamed from
// the original `blocks()` (SPEC-COPILOT-SHOWUI-001 source) solely to avoid a
// top-level name collision with this file's `blocks` array above — no behavior
// change.
// ---------------------------------------------------------------------------

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

/**
 * The show-panel's own --live token, plus the literal forms of the same
 * colour. The negative lookahead excludes `--live-amber` — a SEPARATE,
 * same-value token DASHUI's pool-tile family owns (guarded by its own
 * "--live-amber token exclusivity" describe block above) — so this guard
 * stays scoped to the panel-tile family it was written for and does not
 * false-positive on `var(--live-amber)` merely for sharing the `--live`
 * prefix.
 */
const LIVE_TOKEN = /--live(?!-amber)\b|#ffb02e|rgba\(\s*255\s*,\s*176\s*,\s*46/i;

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
function panelBlocks(css: string): Block[] {
  const withoutComments = css.replace(/\/\*[\s\S]*?\*\//g, "");
  const found: Block[] = [];
  const pattern = /([^{}]+)\{([^{}]*)\}/g;
  for (const match of withoutComments.matchAll(pattern)) {
    found.push({ selector: match[1].trim().replace(/\s+/g, " "), body: match[2] });
  }
  return found;
}

function fontSizePx(selector: string): number | null {
  const block = panelBlocks(CSS).find((candidate) => candidate.selector === selector);
  if (block === undefined) return null;
  const size = /font-size:\s*(\d+(?:\.\d+)?)px/.exec(block.body);
  return size === null ? null : Number(size[1]);
}

describe("live-amber is spent on running and nothing else (REQ-SHOWUI-018)", () => {
  it("parses the stylesheet into blocks at all", () => {
    // Guards the guard: a parser that silently matched nothing would make every
    // assertion below vacuously true.
    const parsed = panelBlocks(CSS);
    expect(parsed.length).toBeGreaterThan(50);
    expect(parsed.some((block) => block.selector === ":root")).toBe(true);
  });

  it("finds live-amber in the sheet — the token is actually in use", () => {
    const users = panelBlocks(CSS).filter((block) => LIVE_TOKEN.test(block.body));
    expect(users.length).toBeGreaterThan(1);
  });

  it("spends it in running-state selectors only", () => {
    const offenders = panelBlocks(CSS)
      .filter((block) => LIVE_TOKEN.test(block.body))
      .map((block) => block.selector)
      .filter((selector) => !RUNNING_SELECTORS.has(selector));

    // A non-empty list here names exactly which rule broke the contract.
    expect(offenders).toEqual([]);
  });

  it("declares the token once, in :root", () => {
    const declarations = panelBlocks(CSS).filter((block) => /--live:\s*#/.test(block.body));

    expect(declarations).toHaveLength(1);
    expect(declarations[0].selector).toBe(":root");
  });

  it("never paints the arm-progress rail with it — arming is not running", () => {
    // All Off is a destructive FIRE control wearing Stop red (design.md §3/§6).
    // Painting its arm progress amber would put the "something is playing"
    // signal on a control that is about to stop everything.
    const arming = panelBlocks(CSS).find((block) => block.selector === ".panel-rail-arming");

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
      const block = panelBlocks(CSS).find((candidate) => candidate.selector === selector);
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
    const actions = panelBlocks(CSS).find(
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
