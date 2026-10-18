// 줄 머리(줄 이름·장비 설명)는 설명 길이와 관계없이 한 폭이다. 마디 눈금 줄·장면 전환 줄·모든 줄의
// 타임라인이 같은 x 에서 시작해야 한다(감독 실측: 「G12 · 521~528 · 8대 · Robin Spiider」 대
// 「G4 · … · Mac Aura XB」처럼 설명 길이에 따라 줄마다 칸이 위아래로 어긋났다). 이 프로젝트는
// jsdom 이 없어 HTML 글과 CSS 글을 잰다(BeatGrid.manyRows.test.tsx 와 같은 방식). 실제 x 는
// 헤드리스 브라우저 측정으로 따로 확인한다.
import { readFileSync } from "node:fs";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { BeatGridCue, BeatGridView } from "../protocol";
import { BeatGrid } from "./BeatGrid";

function cue(bar: number): BeatGridCue {
  return {
    bar,
    label: `칸${bar}`,
    brightness: { mode: "value", value_percent: 100, preset_no: null },
    position_preset_no: null,
    color_preset_no: null,
    effect_preset_no: null,
    effect_kind: null,
    entry: { fade_bars: null, mib_mode: null },
    source_ref: null,
    app_movement: null,
    evidence: null,
  } as BeatGridCue;
}

const LONG_DESCRIPTION = "G11 · 401~412 · 12대 · Robin Spiider Pro Long Name Overflow Test Text";
const SHORT_DESCRIPTION = "G4 · 201~212 · 12대 · Mac Aura XB";

function grid(): BeatGridView {
  return {
    song_title: "ROW HEADER",
    bar_range: { start: 0, end: 16 },
    source: "custom",
    note: null,
    scene_memos: [],
    probe_results: {},
    unsent_cells: null,
    tracks: [
      {
        group_no: 11,
        group_no_confirmed: true,
        group_name: "MOVER-U",
        layer_role: "mover",
        cues: [cue(1)],
        sub_info: { text: LONG_DESCRIPTION },
      },
      {
        group_no: 4,
        group_no_confirmed: true,
        group_name: "BACK",
        layer_role: "back",
        cues: [cue(1)],
        sub_info: { text: SHORT_DESCRIPTION },
      },
    ],
  } as BeatGridView;
}

/** 주석을 뺀 CSS 에서 선택자가 정확히 같은 블록의 선언 글. */
function cssBody(file: string, selector: string): string {
  const css = readFileSync(new URL(file, import.meta.url), "utf8").replace(/\/\*[\s\S]*?\*\//g, "");
  const blocks = [...css.matchAll(/([^{}]+)\{([^{}]*)\}/g)].map((m) => ({
    selector: m[1].trim(),
    body: m[2],
  }));
  const block = blocks.find((b) => b.selector === selector);
  expect(block, selector).toBeDefined();
  return block!.body;
}

const STYLES = "../styles.css";
const PANELS = "./beatGridPanels.css";

describe("줄 머리 폭 — 설명 길이와 관계없이 한 폭 (감독 실측)", () => {
  it("긴 설명은 전체 글을 툴팁으로 싣고 칸 안에서는 말줄임으로 줄인다", () => {
    const html = renderToStaticMarkup(<BeatGrid grid={grid()} />);
    expect(html).toContain(`title="${LONG_DESCRIPTION}"`);
    expect(html).toContain(`title="${SHORT_DESCRIPTION}"`);
    const label = cssBody(STYLES, ".beat-grid-track-meta");
    expect(label).toMatch(/overflow:\s*hidden/);
    expect(label).toMatch(/text-overflow:\s*ellipsis/);
    expect(label).toMatch(/white-space:\s*nowrap/);
    const name = cssBody(STYLES, ".beat-grid-track-name");
    expect(name).toMatch(/text-overflow:\s*ellipsis/);
  });

  it("줄 머리 칸은 모든 줄·마디 눈금 머리가 같은 고정 폭을 쓴다(설명 길이로 늘지 않는다)", () => {
    const label = cssBody(STYLES, ".beat-grid-track-label");
    expect(label).toMatch(/box-sizing:\s*border-box/);
    expect(label).toMatch(/(?<![-\w])width:\s*200px/);
    expect(label).toMatch(/min-width:\s*200px/);
    expect(label).toMatch(/max-width:\s*200px/);
    expect(label).not.toMatch(/90px/);
  });

  it("행과 마디 눈금 줄에는 타임라인 앞을 밀어내는 여백·간격이 없다 — 시작 x 는 머리 폭뿐이다", () => {
    const row = cssBody(STYLES, ".beat-grid-track");
    expect(row).not.toMatch(/padding-left/);
    expect(row).not.toMatch(/gap:/);
    expect(cssBody(STYLES, ".beat-grid-ruler-row")).not.toMatch(/padding|gap:/);
    expect(cssBody(PANELS, ".beat-grid-scene-row")).not.toMatch(/padding|gap:/);
  });

  it("줄 이름 여백은 줄 안에서만 준다 — 마디 눈금 머리·장면 전환 머리의 글 자리는 그대로다", () => {
    expect(cssBody(STYLES, ".beat-grid-track > .beat-grid-track-label")).toMatch(
      /padding:\s*0 8px 0 14px/,
    );
    expect(cssBody(STYLES, ".beat-grid-track > .beat-grid-track-label.beat-grid-track-label-child")).toMatch(
      /padding-left:\s*30px/,
    );
  });

  it("마디 눈금 머리와 모든 줄 머리는 같은 머리 칸을 쓰고, 줄마다 타임라인 열이 머리 바로 뒤에 온다", () => {
    const html = renderToStaticMarkup(<BeatGrid grid={grid()} />);
    expect(html).toContain('class="beat-grid-track-label beat-grid-ruler-corner"');
    const headThenCues =
      html.match(/<span class="beat-grid-track-label"[^>]*>[\s\S]*?<\/span><div class="beat-grid-track-cues"/g) ??
      [];
    expect(headThenCues).toHaveLength(2);
  });
});
