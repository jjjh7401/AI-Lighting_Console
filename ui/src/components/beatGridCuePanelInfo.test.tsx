// 큐 패널 정보 줄 시험(시안 `r.fix` + 타임코드) — 서버 sub_info.text 가 있으면 그것, 없으면 확인된 것만 쓴 문구.
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { BeatGridCue, BeatGridTrack } from "../protocol";
import { BeatGridCueHeadMeta } from "./BeatGridCuePanelParts";

function cue(bar: number): BeatGridCue {
  return { bar, label: "앞박" } as unknown as BeatGridCue;
}

function track(extra: Partial<BeatGridTrack> = {}): BeatGridTrack {
  const c = cue(0);
  return {
    group_no: 4,
    group_no_confirmed: true,
    group_name: "BACK",
    layer_role: "back",
    cues: [c],
    ...extra,
  } as BeatGridTrack;
}

// React SSR 은 이어 붙은 문자열 사이에 주석 표식을 넣으므로 시험 전에 걷어낸다.
function metaHtml(
  t: BeatGridTrack,
  options: { confirmedFixtureCount?: number; secondsPerBar?: number | null } = {},
): string {
  return renderToStaticMarkup(
    <BeatGridCueHeadMeta
      track={t}
      cue={t.cues[0]}
      endBar={4}
      secondsPerBar={options.secondsPerBar === undefined ? 2 : options.secondsPerBar}
      confirmedFixtureCount={options.confirmedFixtureCount ?? 0}
      confirmedFixtureRange={null}
    />,
  ).replace(/<!-- -->/g, "");
}

describe("BeatGridCueHeadMeta — 큐 패널 정보 줄(시안 r.fix + 타임코드)", () => {
  it("서버 sub_info.text 가 있으면 첫 줄에 그대로 쓴다(그룹·장비 범위·대수·기종)", () => {
    const html = metaHtml(track({ sub_info: { text: "G4 · 201~212 · 12대 · Aura XB" } }), { confirmedFixtureCount: 12 });
    expect(html).toContain("G4 · 201~212 · 12대 · Aura XB");
    expect(html).not.toContain("장비 소속 미확인");
  });

  it("sub_info 가 없으면 확인된 것만 쓴 예전 문구를 보인다(지어내지 않음)", () => {
    const html = metaHtml(track(), { confirmedFixtureCount: 0 });
    expect(html).toContain("장비 소속 미확인");
    expect(html).toContain("그룹 4");
  });

  it("둘째 줄은 마디 범위와 시각을 「타임코드」로 보인다", () => {
    const html = metaHtml(track(), { secondsPerBar: 2 });
    expect(html).toContain("Cue 1 · 0~3마디 · 4마디");
    expect(html).toContain("타임코드 0.00초");
  });
});
