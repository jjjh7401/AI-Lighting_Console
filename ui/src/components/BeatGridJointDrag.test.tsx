// 이음매 끌기 — 조인트 부품의 정적 마크업 시험(SPEC-LDBEAT-001 M9, 이음매 드래그).
// 끌기 계산은 beatGridSeam.test.ts 가 본다. 여기서는 끌기 짝을 넘겨도 예전 모양이 그대로이고,
// 트리거 박이 조인트 위치를 박 단위로 옮기는지만 고정한다(jsdom 없이 정적 마크업으로).
import type { ComponentProps } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { BeatGridCue } from "../protocol";
import { BeatGridJoint } from "./BeatGridTimelineParts";

function cue(bar: number, overrides: Partial<BeatGridCue> = {}): BeatGridCue {
  return {
    bar,
    label: "켜짐",
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

// 마디 400px, 박 4개 — 한 박은 100px.
function joint(next: BeatGridCue, extra: Partial<ComponentProps<typeof BeatGridJoint>> = {}): string {
  return renderToStaticMarkup(
    <BeatGridJoint
      prev={cue(0)}
      cue={next}
      nextSegmentWidth={100}
      prevFill={null}
      sectionStartBars={null}
      secondsPerBar={2.14}
      isOn={false}
      onOpen={() => undefined}
      pxPerBar={400}
      beatsPerBar={4}
      {...extra}
    />,
  );
}

function leftOf(html: string): number {
  const match = /left:(-?[\d.]+)px/.exec(html);
  if (match === null) throw new Error(`left 값이 없다: ${html}`);
  return Number(match[1]);
}

describe("이음매 끌기 — 조인트 정적 모양", () => {
  it("끌기 짝이 없으면 예전 모양이다(끌고 있지 않으니 is-dragging 이 없다)", () => {
    const html = joint(cue(4));
    expect(html).toMatch(/class="beat-grid-joint"/);
    expect(html).not.toContain("is-dragging");
  });

  it("끌기 짝을 넘겨도 정적 모양과 위치는 그대로다", () => {
    const plain = joint(cue(4));
    const withDrag = joint(cue(4), { target: "FOH", onMoveTrigger: () => undefined });
    expect(withDrag).toMatch(/class="beat-grid-joint"/);
    expect(leftOf(withDrag)).toBe(leftOf(plain));
  });

  it("트리거 박이 2박 옮겨지면 조인트도 두 박 폭(200px)만큼 옮겨 간다", () => {
    const firstBeat = leftOf(joint(cue(4, { entry: { fade_bars: null, mib_mode: null, trigger_beat: 1 } })));
    const thirdBeat = leftOf(joint(cue(4, { entry: { fade_bars: null, mib_mode: null, trigger_beat: 3 } })));
    expect(thirdBeat - firstBeat).toBe(200);
  });

  it("트리거 박이 없으면 조인트는 마디 시작에 있다", () => {
    expect(leftOf(joint(cue(4)))).toBe(4 * 400);
  });

  it("박자표를 모르면 트리거 위치를 환산하지 않고 마디 시작에 둔다", () => {
    const html = joint(cue(4, { entry: { fade_bars: null, mib_mode: null, trigger_beat: 3 } }), { beatsPerBar: null });
    expect(leftOf(html)).toBe(4 * 400);
  });
});
