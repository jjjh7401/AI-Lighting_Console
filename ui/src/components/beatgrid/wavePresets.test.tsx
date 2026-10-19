import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { type BeatGridTrack, buildBeatGridApply } from "../../protocol";
import { WavePresetControls, waveTrackChoices } from "./WavePresetControls";

function track(groupName: string, groupNo: number | null, confirmed: boolean): BeatGridTrack {
  return { group_name: groupName, group_no: groupNo, group_no_confirmed: confirmed } as BeatGridTrack;
}

describe("웨이브 프리셋 만들기", () => {
  it("보내는 프레임은 mode: wave_presets 와 고른 줄 이름이고, 기존 프레임은 바이트 그대로다", () => {
    expect(JSON.parse(buildBeatGridApply("wave_presets", { groupName: "BACK" }))).toEqual({
      v: 1,
      type: "beat_grid_apply",
      mode: "wave_presets",
      group_name: "BACK",
    });
    expect(buildBeatGridApply()).toBe('{"v":1,"type":"beat_grid_apply"}');
    expect(buildBeatGridApply("preset_plan")).toBe(
      '{"v":1,"type":"beat_grid_apply","mode":"preset_plan"}',
    );
  });

  it("고를 수 있는 줄은 콘솔 그룹 번호가 확인된 트랙뿐이다", () => {
    const choices = waveTrackChoices([
      track("BACK", 7, true),
      track("SIDE", null, false),
      track("FOH", 3, false),
    ]);

    expect(choices.map((item) => item.group_name)).toEqual(["BACK"]);
  });

  it("선택지에는 확인된 줄만 보이고, 고를 줄이 없으면 버튼이 비활성이다", () => {
    const html = renderToStaticMarkup(
      <WavePresetControls
        tracks={[track("BACK", 7, true), track("SIDE", null, false)]}
        onRequest={() => {}}
      />,
    );

    expect(html).toMatch(/<option value="BACK"[^>]*>BACK<\/option>/);
    expect(html).not.toContain('value="SIDE"');
    expect(html).toContain("웨이브 프리셋 만들기");

    const empty = renderToStaticMarkup(<WavePresetControls tracks={[]} onRequest={() => {}} />);

    expect(empty).toContain("콘솔 그룹 번호가 확인된 줄이 없습니다");
    expect(empty).toMatch(/<button[^>]*disabled/);
  });
});
