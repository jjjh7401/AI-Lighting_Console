// 상단 바 · 곡 전체 지도 시험 (SPEC-LDBEAT-001 M9 step 8·1, 카드 t559,
// REQ-LDBEAT-017·018 / AC-LDBEAT-017·018).
//
// jsdom 시험대가 없으므로(BeatGrid.test.tsx 같은 메모) 순수 함수는 직접
// 부르고, 마크업은 `renderToStaticMarkup`으로 문자열을 단언한다
// (runbookM7.test.tsx 와 같은 방식).
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

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

  it("BPM 옆에 「콘솔에서 직접 설정」이 보인다 — 자동 설정처럼 보이지 않게(REQ-LDBEAT-014, 카드 t579)", () => {
    const html = renderTopBar();
    expect(html).toContain("스피드 마스터 — 콘솔에서 직접 설정");
    expect(html).toContain("사람이 콘솔에서 직접 설정");
    expect(html).not.toMatch(/자동 설정됨|자동으로 맞춤/);
  });

  it("곡·버전·BPM 을 렌더한다", () => {
    const html = renderTopBar();
    expect(html).toContain("가짜 곡");
    expect(html).toContain("초안");
    expect(html).toContain("BPM 98.5");
    expect(html).toContain("3마디");
  });
});

describe("상단 바 — 마디 옆 구간 이름 (카드 t630)", () => {
  // BPM 알약에도 「 · 」 가 있어 마크업 전체로는 구분점 유무를 못 가린다 —
  // 마디 칸 하나의 글자만 뽑아 단언한다. 칸 안에 구간 이름 span 이 한 겹 들어
  // 있으므로 닫는 태그까지 통째로 잡은 뒤 안쪽 태그를 벗긴다.
  const barInner = (html: string) =>
    html.match(/<span class="beat-grid-topbar-bar"[^>]*>((?:[^<]|<span[^>]*>[^<]*<\/span>)*)<\/span>/)?.[1];
  const barText = (html: string) => barInner(html)?.replace(/<[^>]+>/g, "");

  it("구간 이름이 있으면 「12마디 · 벌스1」 이 보이고, 이름은 따로 감싼 span 이며 전체 라벨은 title 에 있다", () => {
    const html = renderTopBar({ currentBar: 12, barRange: { start: 0, end: 40 }, barSectionLabel: "벌스1" });
    expect(barText(html)).toBe("12마디 · 벌스1");
    expect(html).toContain('<span class="beat-grid-topbar-bar" title="12마디 · 벌스1">');
    expect(html).toContain('<span class="beat-grid-topbar-bar-section"> · 벌스1</span>');
  });

  it("구간 이름이 없으면(생략·null) 마디 번호만 보이고 구분점·구간 이름 span·title 이 없다", () => {
    for (const html of [renderTopBar(), renderTopBar({ barSectionLabel: null })]) {
      expect(barText(html)).toBe("3마디");
      expect(html).toContain('<span class="beat-grid-topbar-bar">3마디</span>');
      expect(html).not.toContain("beat-grid-topbar-bar-section");
    }
  });
});

/** styles.css 의 `@media (min-width: 1450px) { … }` 블록 본문(안쪽 규칙들). */
function wideMediaBlock(): string {
  const css = readFileSync(fileURLToPath(new URL("../styles.css", import.meta.url)), "utf-8");
  const start = css.indexOf("@media (min-width: 1450px) {");
  expect(start).toBeGreaterThanOrEqual(0);
  const end = css.indexOf("\n}\n", start);
  return css.slice(start, end);
}

describe("상단 바 — 1450px 이상 한 줄 (카드 t587, REQ-LDBEAT-017(b))", () => {
  it("BPM 알약은 긴 안내와 짧은 안내를 둘 다 갖는다 — 어느 폭에서도 「콘솔에서 설정」이 보인다(REQ-LDBEAT-014)", () => {
    const html = renderTopBar();
    expect(html).toMatch(
      /BPM 98\.5<span class="beat-grid-pill-note"> · 스피드 마스터 — 콘솔에서 직접 설정<\/span><span class="beat-grid-pill-note-short"> · 콘솔에서 설정<\/span>/,
    );
  });

  it("1450px 이상에서는 긴 안내 대신 짧은 안내를 보이고(긴 문장은 알약 title), 버튼은 줄임 문구를 쓴다", () => {
    const block = wideMediaBlock();
    expect(block).toMatch(/\.beat-grid-pill-note\s*\{\s*display:\s*none;?\s*\}/);
    expect(block).toMatch(/\.beat-grid-pill-note-short\s*\{\s*display:\s*inline;?\s*\}/);
    expect(block).toMatch(/\.lbl-short\s*\{\s*display:\s*inline;?\s*\}/);
  });

  it("넘쳐도 오른쪽 버튼을 잘라 버리지 않는다 — 시안 `.top{flex-wrap:wrap}` 처럼 줄바꿈 금지를 걸지 않는다", () => {
    expect(wideMediaBlock()).not.toMatch(/flex-wrap:\s*nowrap/);
  });
});

/** styles.css 전체 글. */
function readStylesCss(): string {
  return readFileSync(fileURLToPath(new URL("../styles.css", import.meta.url)), "utf-8");
}

/** styles.css 의 `@media (min-width: <px>px) { … }` 블록 본문 — `wideMediaBlock` 과 같은 방식. */
function minWidthMediaBlock(px: number): string {
  const css = readStylesCss();
  const start = css.indexOf(`@media (min-width: ${px}px) {`);
  expect(start).toBeGreaterThanOrEqual(0);
  const end = css.indexOf("\n}\n", start);
  return css.slice(start, end);
}

/** styles.css 의 기본(미디어 블록 밖) 규칙 하나 — 최상위 규칙은 줄 맨 앞에서 시작하고 미디어 블록 안
 * 규칙은 들여쓴다. 없으면 빈 글. 실패 메시지에 스타일시트 전체가 찍히지 않게 그 규칙만 돌려준다. */
function baseRule(selector: string): string {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return readStylesCss().match(new RegExp(`\\n${escaped}\\s*\\{[^}]*\\}`))?.[0].trim() ?? "";
}

describe("상단 바 — 좁은 폭에서 줄이 꺾이지 않게 (카드 t630)", () => {
  it("구간 이름은 1490px 이상에서만 보인다", () => {
    expect(minWidthMediaBlock(1490)).toMatch(/\.beat-grid-topbar-bar-section\s*\{\s*display:\s*inline;?\s*\}/);
  });

  it("반영 기록 없음 「—」 배지는 1520px 이상에서만 보인다", () => {
    expect(minWidthMediaBlock(1520)).toMatch(/\.beat-grid-topbar \.badge-dash\s*\{\s*display:\s*inline;?\s*\}/);
  });

  it("기본 규칙은 둘 다 숨긴다 — 그보다 좁은 폭에서는 마크업에만 남는다", () => {
    expect(baseRule(".beat-grid-topbar-bar-section")).toMatch(/display:\s*none/);
    expect(baseRule(".beat-grid-topbar .badge-dash")).toMatch(/display:\s*none/);
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

  it("카드 t630 — 반영 기록이 아직 없으면(null) 숫자 대신 「—」 배지와 이유 title 을 보인다", () => {
    const html = renderTopBar({ onApply: noop, pendingApplyCount: null });
    expect(html).toContain(
      '<span class="badge badge-dash" title="반영 기록 없음 — 첫 반영 뒤에 숫자가 보인다">—</span>',
    );
  });
});

describe("상단 바 — 플레이 묶음 (REQ-LDBEAT-024(a), 카드 t570)", () => {
  const playback = {
    playing: false,
    positionSeconds: 12.3,
    onTogglePlay: noop,
    onRewindToStart: noop,
    onSeek: noop,
    audioButtonLabel: "✓ LOVE ATTACK.mp3",
    onSelectAudioFile: noop,
    consoleFollowDisabledReason: "타임코드 재생 송신 경로 없음",
  };

  it("playback 을 안 넘기면 기존과 바이트 동일(플레이 묶음 없음)", () => {
    const html = renderTopBar();
    expect(html).not.toContain("beat-grid-play-cluster");
    expect(html).not.toContain("⏮");
  });

  it("시안 순서대로 플레이·⏮·⏪ 10초·▶ 재생·10초 ⏩·시계·♪·콘솔 같이 끔이 렌더된다", () => {
    const html = renderTopBar({ playback });
    const order = ["플레이", "⏮", "⏪ 10초", "▶ 재생", "10초 ⏩", "0:12.3", "✓ LOVE ATTACK.mp3", "콘솔 같이 끔"];
    const positions = order.map((label) => html.indexOf(label));
    expect(positions.every((p) => p >= 0)).toBe(true);
    expect([...positions].sort((a, b) => a - b)).toEqual(positions);
  });

  it("재생 중이면 ▶ 대신 ❚❚ 일시정지를 보인다", () => {
    const html = renderTopBar({ playback: { ...playback, playing: true } });
    expect(html).toContain("❚❚ 일시정지");
    expect(html).not.toContain("▶ 재생");
  });

  it("콘솔 같이 토글은 송신 경로를 안 넘기면 비활성이고 이유를 title 로 말한다", () => {
    const html = renderTopBar({ playback });
    expect(html).toMatch(/title="타임코드 재생 송신 경로 없음"[^>]*disabled/);
  });

  it("카드 t578 — 송신 경로를 넘기면 토글이 켜지고, 켬/끔과 거절 이유를 보인다", () => {
    const off = renderTopBar({ playback: { ...playback, onToggleConsoleFollow: noop, consoleFollowOn: false } });
    const toggleTag = off.match(/<button[^>]*>콘솔 같이 끔</)?.[0] ?? "";
    expect(toggleTag).toContain('aria-pressed="false"');
    expect(toggleTag).not.toContain("disabled");
    expect(off).not.toContain("타임코드 재생 송신 경로 없음");
    const on = renderTopBar({
      playback: {
        ...playback,
        onToggleConsoleFollow: noop,
        consoleFollowOn: true,
        consoleFollowError: "이 곡을 콘솔에 반영한 기록이 없어",
      },
    });
    expect(on).toMatch(/aria-pressed="true">콘솔 같이 켬</);
    expect(on).toContain("이 곡을 콘솔에 반영한 기록이 없어");
  });

  it("연결 실패 이유가 있으면 보인다", () => {
    const html = renderTopBar({ playback: { ...playback, audioFailureReason: "x.mp3 을 읽지 못했어요" } });
    expect(html).toContain("x.mp3 을 읽지 못했어요");
  });

  it("실패 이유가 없으면 그 칸 자체가 없다", () => {
    const html = renderTopBar({ playback });
    expect(html).not.toContain("beat-grid-audio-error");
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
