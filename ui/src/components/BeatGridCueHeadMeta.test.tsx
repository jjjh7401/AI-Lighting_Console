// 큐 패널 머리 둘째 줄 — 콘솔 시퀀스 번호(「Seq 282」)는 배정된 줄에만 붙는다(서버 PR #742).
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { BeatGridCue, BeatGridTrack } from "../protocol";
import { BeatGridCueHeadMeta } from "./BeatGridCuePanelParts";

function cue(overrides: Partial<BeatGridCue> = {}): BeatGridCue {
  return {
    bar: 0,
    label: "칸",
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

function renderHeadMeta(trackOverrides: Partial<BeatGridTrack>): string {
  const first = cue();
  const track: BeatGridTrack = {
    group_no: 10,
    group_no_confirmed: true,
    group_name: "WASH-ALL",
    layer_role: "wash",
    cues: [first],
    ...trackOverrides,
  };
  return renderToStaticMarkup(
    <BeatGridCueHeadMeta track={track} cue={first} endBar={4} secondsPerBar={null} confirmedFixtureCount={0} />,
  );
}

describe("BeatGridCueHeadMeta — 시퀀스 번호는 배정된 줄에만", () => {
  it("줄에 시퀀스 번호가 있으면 Cue 앞에 「Seq N」을 붙인다", () => {
    expect(renderHeadMeta({ sequence_number: 282 })).toContain("Seq 282 · Cue 1 · 0~3마디 · 4마디");
  });

  it("시퀀스 번호가 없으면(키 없음·null) 「Seq」를 빼고 Cue 줄만 쓴다", () => {
    const absent = renderHeadMeta({});
    expect(absent).not.toContain("Seq");
    expect(absent).toContain("Cue 1 · 0~3마디 · 4마디");
    expect(renderHeadMeta({ sequence_number: null })).not.toContain("Seq");
  });
});
