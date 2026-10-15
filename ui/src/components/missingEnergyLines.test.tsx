// 에너지(D 레벨)를 모르는 구간이 있어도 선이 NaN 으로 찍히지 않아야 한다.
//
// 콘솔의 `<polyline> attribute points: Expected number, "23.13,NaN 344.66,NaN …"`
// 은 CUE SHEET 의 「구간별 인텐시티」 선(CueSheetTimeline 의 intensityPolyline)에서
// 났다. 소수 둘째 자리 좌표가 그 함수의 형식이고, d_level 과 intensity 가 빠진
// 구간의 y 가 NaN 이었다. 곡 전체 지도(SongOverview)의 에너지선은 값을 모르는
// 구간에서 이미 끊기므로 NaN 은 없고 선이 안 그려질 뿐이다. 두 화면을 같이 본다.
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { SongTimelineView } from "../protocol";
import { CueSheetTimeline } from "./CueSheetTimeline";
import { SongOverview, type SongOverviewProps } from "./SongOverview";
import { buildSongOverview, type SongOverviewSectionInput } from "./songOverviewModel";
import REQUERY from "./__fixtures__/requeryTimeline.t490.json";

const SOURCE = REQUERY as unknown as SongTimelineView;

function dropKeys<T extends object>(value: T, keys: readonly string[]): T {
  const copy: Record<string, unknown> = { ...(value as Record<string, unknown>) };
  for (const key of keys) delete copy[key];
  return copy as T;
}

/** 에너지(d_level)와 그룹 값(intensity)이 빠진 구간 — NaN 을 낸 모양. */
const NO_ENERGY = SOURCE.sections.map((section) => dropKeys(section, ["d_level", "intensity"]));
/** 가운데 구간만 에너지를 모른다 — 선은 그 자리에서 끊겨야 한다. */
const GAP = [
  SOURCE.sections[0],
  dropKeys(SOURCE.sections[1], ["d_level", "intensity"]),
  SOURCE.sections[2],
];

describe("CUE SHEET 인텐시티 선 — 값을 모르는 구간", () => {
  it("NaN 을 찍지 않는다", () => {
    const html = renderToStaticMarkup(<CueSheetTimeline timeline={{ ...SOURCE, sections: NO_ENERGY }} />);
    expect(html).not.toContain("NaN");
  });

  it("값을 모르는 구간만 있으면 선을 그리지 않는다", () => {
    const html = renderToStaticMarkup(<CueSheetTimeline timeline={{ ...SOURCE, sections: NO_ENERGY }} />);
    expect(html).not.toContain("<polyline");
  });

  it("값을 모르는 구간에서 끊는다 — 앞뒤 값을 직선으로 잇지 않는다", () => {
    const html = renderToStaticMarkup(<CueSheetTimeline timeline={{ ...SOURCE, sections: GAP }} />);
    expect(html.match(/<polyline/g)).toHaveLength(2);
    expect(html).not.toContain("NaN");
  });

  it("값이 다 있으면 한 선으로 그대로 그린다(대조군)", () => {
    const html = renderToStaticMarkup(<CueSheetTimeline timeline={SOURCE} />);
    expect(html.match(/<polyline/g)).toHaveLength(1);
    expect(html).not.toContain("NaN");
  });
});

describe("곡 전체 지도 에너지선 — 값을 모르는 구간", () => {
  const props: Omit<SongOverviewProps, "model"> = {
    filledRange: { start: 0, end: 9 },
    visibleWindow: null,
    playheadBar: null,
    currentBar: 0,
    sceneMemos: [],
    zoom: "song",
    onZoomChange: () => {},
    onJump: () => {},
  };
  const build = (sections: SongOverviewSectionInput[]) =>
    buildSongOverview({ sections, barCount: 24, secondsPerBar: 2, fallbackRange: { start: 0, end: 9 } });

  it("에너지가 하나도 없으면 에너지선도 NaN 도 없다", () => {
    const model = build([
      { label: "A", start_ms: 0, bar_start: 0 },
      { label: "B", start_ms: 16000, bar_start: 8 },
    ]);
    const html = renderToStaticMarkup(<SongOverview {...props} model={model} />);
    expect(html).not.toContain("song-overview-energy");
    expect(html).not.toContain("NaN");
  });

  it("값을 모르는 구간에서 에너지선이 끊긴다", () => {
    const model = build([
      { label: "A", start_ms: 0, bar_start: 0, d_level: 3 },
      { label: "B", start_ms: 16000, bar_start: 8 },
      { label: "C", start_ms: 32000, bar_start: 16, d_level: 4 },
    ]);
    const html = renderToStaticMarkup(<SongOverview {...props} model={model} />);
    expect(html.match(/song-overview-energy/g)).toHaveLength(2);
    expect(html).not.toContain("NaN");
  });
});
