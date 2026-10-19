import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { type BeatGridTrack, buildBeatGridApply, type WaveCustomPreset } from "../../protocol";
import { WavePresetControls, waveCustomProblem } from "./WavePresetControls";

const SINE_2B: WaveCustomPreset = {
  shape: "sine",
  beats: 2,
  label: "MY SINE 2B",
  displayName: "내 사인 2박",
};

function track(groupName: string, groupNo: number | null, confirmed: boolean): BeatGridTrack {
  return {
    group_name: groupName,
    group_no: groupNo,
    group_no_confirmed: confirmed,
  } as BeatGridTrack;
}

describe("웨이브 직접 만들기 — 화면 검사", () => {
  it("좋은 값은 통과한다", () => {
    expect(waveCustomProblem(SINE_2B)).toBeNull();
  });

  it("모양·박 수·콘솔 이름·화면 이름을 각각 거른다", () => {
    expect(waveCustomProblem({ ...SINE_2B, shape: "square" })).not.toBeNull();
    expect(waveCustomProblem({ ...SINE_2B, beats: 3 })).not.toBeNull();
    expect(waveCustomProblem({ ...SINE_2B, label: "내 사인" })).not.toBeNull();
    expect(waveCustomProblem({ ...SINE_2B, label: "X".repeat(21) })).not.toBeNull();
    expect(waveCustomProblem({ ...SINE_2B, displayName: "   " })).not.toBeNull();
  });
});

describe("웨이브 직접 만들기 — 보내는 프레임", () => {
  it("줄 이름과 값 묶음을 싣고, 고른 칸이 없으면 cells 키가 없다", () => {
    expect(
      JSON.parse(buildBeatGridApply("wave_custom", { groupName: "BACK", preset: SINE_2B })),
    ).toEqual({
      v: 1,
      type: "beat_grid_apply",
      mode: "wave_custom",
      group_name: "BACK",
      preset: { shape: "sine", beats: 2, label: "MY SINE 2B", display_name: "내 사인 2박" },
    });
  });

  it("고른 칸이 있으면 cells 를 덧붙이고, 비어 있으면 키를 싣지 않는다", () => {
    const withCells = JSON.parse(
      buildBeatGridApply("wave_custom", {
        groupName: "BACK",
        preset: SINE_2B,
        cells: [["BACK", 1]],
      }),
    );
    expect(withCells.cells).toEqual([["BACK", 1]]);

    const noCells = JSON.parse(
      buildBeatGridApply("wave_custom", { groupName: "BACK", preset: SINE_2B, cells: [] }),
    );
    expect("cells" in noCells).toBe(false);
  });
});

describe("웨이브 직접 만들기 — 화면", () => {
  it("모양·박 수·이름 칸과 저장 버튼, 고른 칸 적용 체크를 보여준다", () => {
    const html = renderToStaticMarkup(
      <WavePresetControls
        tracks={[track("BACK", 7, true)]}
        onRequest={() => {}}
        onCustomRequest={() => {}}
        selectedCells={[["BACK", 1]]}
      />,
    );

    expect(html).toContain('aria-label="웨이브 모양"');
    expect(html).toContain("디머 웨이브 · 사인");
    expect(html).toContain('aria-label="콘솔 이름"');
    expect(html).toContain("이름 붙여 저장");
    expect(html).toContain("선택한 칸 1개에도 적용");
  });

  it("고른 칸이 없으면 칸 적용 체크가 없다", () => {
    const html = renderToStaticMarkup(
      <WavePresetControls
        tracks={[track("BACK", 7, true)]}
        onRequest={() => {}}
        onCustomRequest={() => {}}
      />,
    );

    expect(html).not.toContain("선택한 칸");
  });

  it("고를 줄이 없으면 저장 버튼이 비활성이다", () => {
    const html = renderToStaticMarkup(
      <WavePresetControls tracks={[]} onRequest={() => {}} onCustomRequest={() => {}} />,
    );

    expect(html).toMatch(/<button[^>]*disabled[^>]*>이름 붙여 저장/);
  });
});
