// 막대 영역을 시안(reports/ldbeat-runbook-ui-proposal-20261008.html)과 맞춘다.
// ① 막대 색 = 색 프리셋의 목표 RGB. 꺼진 칸은 「꺼짐」이고 빗금이다.
// ① 배치 범위 밖은 「N마디~ 아직 배치 안 함」 빗금 영역이다.
// 데이터는 서버가 준다. 여기서는 그 모양을 넣고, 그려진 결과만 본다.
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { BeatGridCue, BeatGridTrack, BeatGridView } from "../protocol";
import { BeatGrid } from "./BeatGrid";

function cue(bar: number, label: string, overrides: Partial<BeatGridCue> = {}): BeatGridCue {
  return {
    bar,
    label,
    brightness: { mode: null, value_percent: null, preset_no: null },
    position_preset_no: null,
    color_preset_no: null,
    effect_preset_no: null,
    effect_kind: null,
    entry: { fade_bars: null, mib_mode: null },
    source_ref: null,
    app_movement: null,
    evidence: null,
    ...overrides,
  };
}

function track(groupName: string, layerRole: string | null, cues: BeatGridCue[]): BeatGridTrack {
  return { group_no: 1, group_no_confirmed: true, group_name: groupName, layer_role: layerRole, cues };
}

function gridWith(tracks: BeatGridTrack[], presetColors?: BeatGridView["preset_colors"]): BeatGridView {
  return {
    song_title: "LOVE ATTACK",
    bar_range: { start: 0, end: 25 },
    source: "love_attack_default",
    note: null,
    scene_memos: [],
    probe_results: {},
    unsent_cells: null,
    tracks,
    preset_colors: presetColors,
  } as BeatGridView;
}

describe("막대 색 — 색 프리셋의 목표 RGB", () => {
  it("색 번호의 RGB 가 있으면 그 색으로 칠한다", () => {
    const grid = gridWith(
      [track("WASH-ALL", "wash", [cue(0, "라벤더 워시", { color_preset_no: "4.22" })])],
      { "4.22": { r: 60, g: 30, b: 100 } },
    );
    const html = renderToStaticMarkup(<BeatGrid grid={grid} barCount={26} />);
    expect(html).toContain("background-color:#994dff");
  });

  it("RGB 를 모르는 켜진 칸은 시안 기본색(#d8d8d8)으로 칠한다 — 색을 지어내지 않는다", () => {
    const grid = gridWith([track("WASH-ALL", "wash", [cue(0, "라벤더 워시", { color_preset_no: "4.22" })])]);
    const html = renderToStaticMarkup(<BeatGrid grid={grid} barCount={26} />);
    expect(html).toContain("background-color:#d8d8d8");
    expect(html).toContain("is-color-unset");
  });

  it("꺼진 칸은 색 프리셋이 있어도 칠하지 않는다(빗금 유지)", () => {
    const grid = gridWith(
      [track("WASH-ALL", "wash", [cue(0, "—", { color_preset_no: "4.22" })])],
      { "4.22": { r: 60, g: 30, b: 100 } },
    );
    const html = renderToStaticMarkup(<BeatGrid grid={grid} barCount={26} />);
    expect(html).toMatch(/is-off[^>]*>꺼짐/);
    expect(html).not.toContain("background-color:#");
  });
});

describe("꺼진 칸과 배치 안 된 마디 — 시안 .clip.off · .clip.empty", () => {
  it("꺼진 칸의 막대 글자는 「꺼짐」이다(「—」가 아니다)", () => {
    const grid = gridWith([track("FOH", "key", [cue(0, "—")])]);
    const html = renderToStaticMarkup(<BeatGrid grid={grid} barCount={26} />);
    expect(html).toMatch(/is-off[^>]*>꺼짐/);
    expect(html).not.toMatch(/is-off[^>]*>—</);
  });

  it("첫 칸 앞의 구간은 빗금 「꺼짐」이다(시안의 꺼진 첫 구간)", () => {
    const grid = gridWith([track("FOH", "key", [cue(7, "Pace 60")])]);
    const html = renderToStaticMarkup(<BeatGrid grid={grid} barCount={26} />);
    expect(html).toMatch(/beat-grid-cue-gap is-off[^>]*>꺼짐/);
  });

  it("배치 범위 밖은 「26마디~ 아직 배치 안 함」 빗금 영역이다", () => {
    const grid = gridWith([track("FOH", "key", [cue(0, "앞빛")])]);
    const html = renderToStaticMarkup(<BeatGrid grid={grid} barCount={83} />);
    expect(html).toContain("26마디~ 아직 배치 안 함");
  });

  it("배치 범위가 축 끝까지면 그 영역은 없다", () => {
    // gridAxisEnd 는 barCount 를 축 끝 마디로 쓴다(barCount 26 이면 26마디까지 축이 있다).
    const grid = gridWith([track("FOH", "key", [cue(0, "앞빛")])]);
    const html = renderToStaticMarkup(<BeatGrid grid={grid} barCount={25} />);
    expect(html).not.toContain("아직 배치 안 함");
  });
});

describe("개요 — 채운 범위 표시 (시안 「← 채운 범위(0~25)」)", () => {
  it("채운 범위는 격자 데이터 범위(bar_range)다 — 축 끝이 아니다", () => {
    const grid = gridWith([track("FOH", "key", [cue(0, "앞빛")])]);
    const html = renderToStaticMarkup(<BeatGrid grid={grid} barCount={83} />);
    expect(html).toContain("← 채운 범위(0~25)");
    expect(html).not.toContain("← 채운 범위(0~82)");
  });
});

describe("줄 머리 둘째 줄 — 서버 sub_info.text (#726)", () => {
  it("sub_info.text 가 있으면 둘째 줄에 그대로 쓴다", () => {
    const withInfo = { ...track("BACK", "back", [cue(0, "앞박")]), sub_info: { text: "G4 · 201~212 · 12대 · Aura XB" } };
    const html = renderToStaticMarkup(<BeatGrid grid={gridWith([withInfo])} barCount={26} />);
    expect(html).toContain("G4 · 201~212 · 12대 · Aura XB");
  });

  it("sub_info 가 없으면 콘솔 판독 문구를 지어내지 않는다", () => {
    const html = renderToStaticMarkup(<BeatGrid grid={gridWith([track("BACK", "back", [cue(0, "앞박")])])} barCount={26} />);
    expect(html).not.toContain("Aura XB");
  });
});
