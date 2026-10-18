// 줄이 30개 넘는 무대에서도 격자가 모든 줄을 그린다(카드 WT-track-model PR2, 감독 2026-10-18
// 「무대마다 장비 종류가 수십 가지, 수량이 수백 대」). 줄 수에 화면 상한이 없는지 글자로 잰다
// (이 프로젝트는 jsdom 이 없다 — `renderToStaticMarkup`). 세로가 넘치면 `.beat-grid-lanes` 가
// 440px 안에서 스크롤한다(styles.css, 카드 t585) — 그 규칙도 함께 못박는다.
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

const ROLES = ["key", "back", "side", "wash", "mover", "effect", null] as const;

function grid(rows: number): BeatGridView {
  return {
    song_title: "MANY ROWS",
    bar_range: { start: 0, end: 16 },
    source: "custom",
    note: null,
    scene_memos: [],
    probe_results: {},
    unsent_cells: null,
    tracks: Array.from({ length: rows }, (_, index) => ({
      group_no: index + 1,
      group_no_confirmed: true,
      group_name: `RIG-${String(index + 1).padStart(2, "0")}`,
      layer_role: ROLES[index % ROLES.length],
      cues: [cue(1), cue(9)],
    })),
  } as BeatGridView;
}

describe("줄이 많은 무대", () => {
  it("30줄·48줄 격자가 줄 이름을 하나도 빠뜨리지 않고 그린다", () => {
    for (const rows of [30, 48]) {
      const html = renderToStaticMarkup(<BeatGrid grid={grid(rows)} />);
      for (let index = 1; index <= rows; index += 1) {
        expect(html).toContain(`RIG-${String(index).padStart(2, "0")}`);
      }
      expect(html).not.toContain("표시할 트랙이 없습니다");
    }
  });

  it("타임라인은 높이를 고정하고 그 안에서 세로로 스크롤한다", () => {
    const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
    const mid = /\.beat-grid-mid\s*\{[^}]*\}/.exec(css)?.[0] ?? "";
    const lanes = /\.beat-grid-lanes\s*\{[^}]*\}/.exec(css)?.[0] ?? "";
    expect(mid).toMatch(/height:\s*440px/);
    expect(lanes).toMatch(/overflow:\s*auto/);
  });
});
