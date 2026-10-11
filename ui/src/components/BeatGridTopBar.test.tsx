// 상단 바 · 곡 전체 지도 시험 (SPEC-LDBEAT-001 M9 step 8·1, 카드 t559,
// REQ-LDBEAT-017·018 / AC-LDBEAT-017·018).
//
// jsdom 시험대가 없으므로(BeatGrid.test.tsx 같은 메모) 순수 함수는 직접
// 부르고, 마크업은 `renderToStaticMarkup`으로 문자열을 단언한다
// (runbookM7.test.tsx 와 같은 방식).
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import {
  BeatGridTopBar,
  TOP_BAR_SHORTENED_ACTIONS,
  barNavKeyDelta,
  formatTopBarBpm,
  stepBar,
} from "./BeatGridTopBar";
import { SongOverview } from "./SongOverview";
import { buildSongOverview } from "./songOverviewModel";

const noop = () => {};

function renderTopBar(overrides: Partial<Parameters<typeof BeatGridTopBar>[0]> = {}) {
  return renderToStaticMarkup(
    <BeatGridTopBar
      songTitle="가짜 곡"
      versionLabel="초안"
      bpm={98.5}
      currentBar={3}
      barRange={{ start: 0, end: 9 }}
      onBarChange={noop}
      onDrawerToggle={noop}
      {...overrides}
    />,
  );
}

describe("상단 바 — 마디 이동", () => {
  it("◀ ▶ 는 표시 범위 안으로 클램프한다", () => {
    expect(stepBar(3, -1, { start: 0, end: 9 })).toBe(2);
    expect(stepBar(0, -1, { start: 0, end: 9 })).toBe(0);
    expect(stepBar(9, 1, { start: 0, end: 9 })).toBe(9);
  });

  it("← → 키만 이동이고, 입력칸 안이나 수정키 조합은 무시한다", () => {
    expect(barNavKeyDelta({ key: "ArrowLeft" })).toBe(-1);
    expect(barNavKeyDelta({ key: "ArrowRight" })).toBe(1);
    expect(barNavKeyDelta({ key: "ArrowUp" })).toBe(0);
    expect(barNavKeyDelta({ key: "ArrowLeft", targetTag: "INPUT" })).toBe(0);
    expect(barNavKeyDelta({ key: "ArrowRight", targetTag: "TEXTAREA" })).toBe(0);
    expect(barNavKeyDelta({ key: "ArrowRight", targetTag: "SELECT" })).toBe(0);
    expect(barNavKeyDelta({ key: "ArrowRight", isContentEditable: true })).toBe(0);
    expect(barNavKeyDelta({ key: "ArrowRight", altKey: true })).toBe(0);
  });
});

describe("상단 바 — 곡·버전·BPM", () => {
  it("BPM 은 곡 데이터 값, 없으면 지어내지 않고 '—'", () => {
    expect(formatTopBarBpm(112.35)).toBe("BPM 112.35");
    expect(formatTopBarBpm(120)).toBe("BPM 120");
    expect(formatTopBarBpm(undefined)).toBe("BPM —");
  });

  it("곡·버전·BPM 을 렌더한다", () => {
    const html = renderTopBar();
    expect(html).toContain("가짜 곡");
    expect(html).toContain("초안");
    expect(html).toContain("BPM 98.5");
    expect(html).toContain("3마디");
  });
});

describe("상단 바 — 버튼 전부 + 1450px 줄임 (AC-LDBEAT-017(a)(b))", () => {
  it("줄이는 버튼은 셋이고 시안 문구 그대로", () => {
    expect(TOP_BAR_SHORTENED_ACTIONS.map((a) => [a.full, a.short])).toEqual([
      ["▶ 이 마디 콘솔에서 보기", "▶ 콘솔"],
      ["⇪ 콘솔에 반영", "⇪ 반영"],
      ["▤ 프리셋 서랍", "▤"],
    ]);
  });

  it("◀ ▶ · 콘솔에서 보기 · 끄기 · 반영 · 서랍이 모두 렌더되고, 줄임 버튼의 title 에 풀네임이 있다", () => {
    const html = renderTopBar({ onPreviewBar: noop, onPreviewOff: noop, onApply: noop, pendingApplyCount: 2 });
    expect(html).toContain('title="이전 마디 (←)"');
    expect(html).toContain('title="다음 마디 (→)"');
    expect(html).toContain("■ 끄기");
    for (const action of TOP_BAR_SHORTENED_ACTIONS) {
      expect(html).toContain(`<span class="lbl-full">${action.full}</span>`);
      expect(html).toContain(`<span class="lbl-short">${action.short}</span>`);
      expect(html).toMatch(new RegExp(`title="${action.full.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}[^"]*"`));
    }
    expect(html).toContain('<span class="badge">2</span>');
  });

  it("콘솔 경로가 배선되지 않은 버튼은 비활성이고 그 사실을 title 로 말한다", () => {
    const html = renderTopBar();
    expect(html).toMatch(/title="▶ 이 마디 콘솔에서 보기 — 아직 배선 안 됨[^"]*" disabled/);
    expect(html).toMatch(/title="■ 끄기 — 아직 배선 안 됨[^"]*" disabled/);
    expect(html).not.toContain('class="badge"');
  });
});

describe("곡 전체 지도 마크업 (AC-LDBEAT-018)", () => {
  const props = {
    filledRange: { start: 0, end: 9 },
    visibleWindow: { startBar: 2, endBar: 6 },
    playheadBar: 1,
    currentBar: 2,
    sceneMemos: [],
    zoom: "bars16" as const,
    onZoomChange: noop,
    onJump: noop,
  };

  it("두 곡이 서로 다른 강조 마디를 그린다", () => {
    const songA = buildSongOverview({
      sections: [
        { label: "a", start_ms: 0, bar_start: 0, d_level: 2, accents: [] },
        { label: "b", start_ms: 0, bar_start: 5, d_level: 5, accents: ["climax accent"] },
      ],
      barCount: 20,
      secondsPerBar: 2,
      fallbackRange: { start: 0, end: 9 },
    });
    const songB = buildSongOverview({
      sections: [
        { label: "x", start_ms: 0, bar_start: 0, d_level: 4, accents: ["section arc"] },
        { label: "y", start_ms: 0, bar_start: 11, d_level: 1, accents: [] },
      ],
      barCount: 20,
      secondsPerBar: 2,
      fallbackRange: { start: 0, end: 9 },
    });
    const htmlA = renderToStaticMarkup(<SongOverview model={songA} {...props} />);
    const htmlB = renderToStaticMarkup(<SongOverview model={songB} {...props} />);
    expect(htmlA.match(/data-bar="(\d+)"/g)).toEqual(['data-bar="5"']);
    expect(htmlB.match(/data-bar="(\d+)"/g)).toEqual(['data-bar="0"']);
  });

  it("에너지선 · 범위 창 · 재생 위치 · 확대 3버튼(16마디 눌림)을 그린다", () => {
    const model = buildSongOverview({
      sections: [{ label: "a", start_ms: 0, bar_start: 0, d_level: 3, accents: [] }],
      barCount: 20,
      secondsPerBar: 2,
      fallbackRange: { start: 0, end: 9 },
    });
    const html = renderToStaticMarkup(<SongOverview model={model} {...props} />);
    expect(html).toContain('class="song-overview-energy"');
    expect(html).toContain('class="song-overview-window"');
    expect(html).toContain('class="song-overview-playhead"');
    expect(html).toContain("곡 전체</button>");
    expect(html).toContain('class="on" aria-pressed="true">16마디</button>');
    expect(html).toContain("8마디</button>");
    expect(html).toContain("채운 범위(0~9)");
  });
});
