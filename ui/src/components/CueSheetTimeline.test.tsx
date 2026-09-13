// 이 프로젝트에는 jsdom/RTL 하네스가 없다(SongTimeline.test.tsx 와 같은 관례).
// 그래서 렌더가 아니라 렌더를 결정하는 순수 함수를 재고, 두 축의 연동은
// 「선택 인덱스 → 보이는 행 범위」와 「스크롤 위치 → 선택 인덱스」 두 방향을
// 각각 함수로 확인한다.
import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

import type { SongTimelineSection, SongTimelineView } from "../protocol";
import { SONG_TIMELINE_EXAMPLE } from "./songTimelineExample";
import { CUE_SHEET_EXAMPLE } from "./cueSheetExample";
import {
  EMPTY_CELL,
  VISIBLE_CUE_ROWS,
  shouldAdoptScroll,
  visibleRowRange,
  cell,
  cueIndexAtMs,
  cueLabel,
  derivedBannerText,
  formatBpm,
  formatDuration,
  formatTc,
  isSnapCue,
  paletteColorFor,
  sectionDurationMs,
  sectionEndMs,
  sectionIntensityPercent,
  sectionIntensityText,
  showDerivedBanner,
  songTotalMs,
} from "./CueSheetTimeline";

const SECTIONS = CUE_SHEET_EXAMPLE.sections;
const TOTAL = songTotalMs(CUE_SHEET_EXAMPLE);

describe("두 축의 연동 — 선택은 한 곳에서만 산다", () => {
  // 행 높이 28px 짜리 18행. 창은 다섯 줄(140px)만 보여 준다.
  const ROW_H = 28;
  const TOPS = SECTIONS.map((_, i) => i * ROW_H);
  const BAND = ROW_H * VISIBLE_CUE_ROWS;

  it("보이는 행 범위는 페이지 번호가 아니라 실제 스크롤 위치에서 나온다", () => {
    expect(visibleRowRange(TOPS, 0, BAND)).toEqual({ start: 0, end: 5 });
    expect(visibleRowRange(TOPS, ROW_H * 6, BAND)).toEqual({ start: 6, end: 11 });
  });

  it("반 줄만 걸쳐도 보이는 행으로 센다 — 창 높이가 범위를 정한다", () => {
    // 반 줄 걸친 6번은 시작으로, 아래로 반 줄 걸친 11번도 보이는 행으로 센다.
    expect(visibleRowRange(TOPS, ROW_H * 6 + 14, BAND)).toEqual({ start: 6, end: 12 });
  });

  it("끝까지 내리면 마지막 행에서 멈춘다", () => {
    const bottom = ROW_H * (SECTIONS.length - VISIBLE_CUE_ROWS);
    expect(visibleRowRange(TOPS, bottom, BAND)).toEqual({
      start: SECTIONS.length - VISIBLE_CUE_ROWS,
      end: SECTIONS.length,
    });
  });

  it("행이 창보다 적으면 있는 만큼만 센다", () => {
    expect(visibleRowRange([0, 28, 56], 0, BAND)).toEqual({ start: 0, end: 3 });
    expect(visibleRowRange([], 0, BAND)).toEqual({ start: 0, end: 0 });
  });

  it("타임라인을 가로로 스크롤하면 그 위치의 큐가 선택된다 (반대 방향)", () => {
    expect(cueIndexAtMs(SECTIONS, 0)).toBe(0);
    expect(cueIndexAtMs(SECTIONS, 57_000)).toBe(4); // CHORUS1 Q050 (56.0s~)
    expect(cueIndexAtMs(SECTIONS, 55_999)).toBe(3); // 아직 PRE1 Q040
    expect(cueIndexAtMs(SECTIONS, 999_000)).toBe(SECTIONS.length - 1);
  });

  it("t288 — 코드가 만든 스크롤은 클릭한 큐를 앞 큐로 되돌리지 못한다", () => {
    // 재현(2026-09-06, Chrome 실기 · .moai/state/verify/t287/probe-t288b.mjs):
    // 13번 칩(Q140)을 클릭하고 700ms 억제창이 끝난 뒤 레일에 scroll 이벤트가
    // 한 번 더 오면 선택이 Q130 으로 밀리고 창이 11–15 가 됐다. 스크롤 위치는
    // 그대로였다 — 원인은 타이밍이 아니라 「스크롤 위치 → 인덱스」 환산이
    // 클릭한 큐를 못 되돌린다는 것이다(칩을 창의 1/3 지점에 두므로 좌단은
    // 언제나 앞 큐다). 그래서 시간이 아니라 출처로 가른다.
    const clicked = 13;
    const settledMs = SECTIONS[clicked].start_ms - 1; // 정착 위치가 가리키는 지점
    expect(cueIndexAtMs(SECTIONS, settledMs)).toBe(clicked - 1); // 환산은 한 칸 앞이다

    let selected = clicked;
    if (shouldAdoptScroll("program")) selected = cueIndexAtMs(SECTIONS, settledMs);
    expect(selected).toBe(clicked);
  });

  it("사람이 굴린 스크롤만 선택을 옮긴다", () => {
    expect(shouldAdoptScroll("user")).toBe(true);
    expect(shouldAdoptScroll("program")).toBe(false);
  });

  it("스크롤로 고른 큐는 그 행이 보이는 범위 안에 든다 — 두 축이 어긋나지 않는다", () => {
    const index = cueIndexAtMs(SECTIONS, 150_000);
    const visible = visibleRowRange(TOPS, ROW_H * index, BAND);
    expect(index).toBeGreaterThanOrEqual(visible.start);
    expect(index).toBeLessThan(visible.end);
  });
});

describe("DERIVED 배너", () => {
  it("tc_method 가 DERIVED 이면 띄운다", () => {
    expect(showDerivedBanner(CUE_SHEET_EXAMPLE)).toBe(true);
    expect(derivedBannerText(CUE_SHEET_EXAMPLE)).toContain("LTC 대조");
  });

  it("MEASURED 이거나 값이 없으면 띄우지 않는다", () => {
    expect(showDerivedBanner({ ...CUE_SHEET_EXAMPLE, tc_method: "MEASURED" })).toBe(false);
    expect(showDerivedBanner({ ...CUE_SHEET_EXAMPLE, tc_method: null })).toBe(false);
    expect(showDerivedBanner(SONG_TIMELINE_EXAMPLE)).toBe(false);
  });

  it("서버 문구가 없어도 기본 고지 문구를 낸다 — 배너가 비어 보이지 않는다", () => {
    const text = derivedBannerText({ ...CUE_SHEET_EXAMPLE, tc_method_warning: undefined });
    expect(text).toContain("마디 연산");
    expect(text.length).toBeGreaterThan(20);
  });
});

describe("없는 필드는 조용히 떨어진다 — undefined 를 그리지 않는다", () => {
  // 오늘의 서버는 t279 확장 필드를 거의 채우지 않는다. 그 페이로드가 바로
  // SONG_TIMELINE_EXAMPLE 이고, 아래는 그 모양 그대로를 판다.
  const bare: SongTimelineView = SONG_TIMELINE_EXAMPLE;
  const bareSection: SongTimelineSection = bare.sections[0];

  it("헤더 메타가 전부 비어도 각 칸이 em-dash 로 나온다", () => {
    expect(cell(bare.bpm)).toBe(EMPTY_CELL);
    expect(cell(bare.time_signature)).toBe(EMPTY_CELL);
    expect(cell(bare.musical_key)).toBe(EMPTY_CELL);
    expect(cell(bare.tc_source)).toBe(EMPTY_CELL);
  });

  it("큐시트 확장 열이 전부 비어도 em-dash 로 나온다", () => {
    expect(cell(bareSection.mood)).toBe(EMPTY_CELL);
    expect(cell(bareSection.palette_primary)).toBe(EMPTY_CELL);
    expect(cell(bareSection.palette_secondary)).toBe(EMPTY_CELL);
    expect(cell(bareSection.movement)).toBe(EMPTY_CELL);
    expect(cell(bareSection.effect)).toBe(EMPTY_CELL);
    expect(cell(bareSection.trans)).toBe(EMPTY_CELL);
    expect(cell(bareSection.note)).toBe(EMPTY_CELL);
    expect(cell(bareSection.fixture_groups)).toBe(EMPTY_CELL);
  });

  it("빈 문자열과 빈 배열도 값 없음으로 본다", () => {
    expect(cell("")).toBe(EMPTY_CELL);
    expect(cell("  ")).toBe(EMPTY_CELL);
    expect(cell([])).toBe(EMPTY_CELL);
    expect(cell(0)).toBe("0");
    expect(cell(Number.NaN)).toBe(EMPTY_CELL);
  });

  it("end_ms 가 없으면 다음 구간 시작으로, 마지막은 곡 끝으로 메운다", () => {
    const total = songTotalMs(bare);
    expect(sectionEndMs(bare.sections[0], bare.sections[1], total)).toBe(24_000);
    const last = bare.sections[bare.sections.length - 1];
    expect(sectionEndMs(last, undefined, total)).toBe(total);
    expect(sectionDurationMs(bare.sections[0], bare.sections[1], total)).toBe(24_000);
  });

  it("끝을 못 구하면 Dur 은 추정하지 않고 em-dash 로 둔다", () => {
    const orphan: SongTimelineSection = { ...bareSection, start_ms: 500_000 };
    expect(sectionEndMs(orphan, undefined, 236_000)).toBeNull();
    expect(formatDuration(sectionDurationMs(orphan, undefined, 236_000))).toBe(EMPTY_CELL);
  });

  it("그룹별 인텐시티가 없으면 d_level 로 % 를 만든다 — 표는 비지 않는다", () => {
    expect(sectionIntensityPercent(bareSection)).toBe(bareSection.d_level * 20);
    expect(sectionIntensityText(bareSection)).toBe(String(bareSection.d_level * 20));
  });

  it("팔레트 범례가 없으면 중립색으로 떨어진다 — 색이 없어 깨지지 않는다", () => {
    expect(paletteColorFor(bareSection, undefined)).toMatch(/^#[0-9A-Fa-f]{6}$/);
    expect(paletteColorFor(bareSection, [])).toMatch(/^#[0-9A-Fa-f]{6}$/);
  });

  it("확장 필드가 하나도 없어도 창 계산이 그대로 돈다", () => {
    const tops = bare.sections.map((_, i) => i * 28);
    expect(visibleRowRange(tops, 0, 28 * VISIBLE_CUE_ROWS)).toEqual({
      start: 0,
      end: bare.sections.length,
    });
    expect(cueIndexAtMs(bare.sections, 50_000)).toBe(2);
  });
});

describe("정본 산출물의 표기를 따른다", () => {
  it("TC 는 MM:SS.d", () => {
    expect(formatTc(0)).toBe("00:00.0");
    expect(formatTc(236_000)).toBe("03:56.0");
    expect(formatTc(56_000)).toBe("00:56.0");
    expect(formatTc(undefined)).toBe(EMPTY_CELL);
  });

  // t392 — 감독 화면 신고: "126.04801829268435 BPM". 표시 전용 반올림이고,
  // 원본 값(마디 분할·큐 타이밍이 쓰는 값)은 이 함수를 거치지 않는다 —
  // formatBpm 은 화면에 찍을 문자열만 만들고 어떤 상태도 바꾸지 않는다.
  it("BPM 은 화면에서만 최대 소수점 2자리로 줄인다 — 원본 계산값은 건드리지 않는다", () => {
    const raw = 126.04801829268435;
    expect(formatBpm(raw)).toBe("126.05");
    expect(raw).toBe(126.04801829268435); // 원본은 그대로 살아 있다
    expect(formatBpm(120)).toBe("120"); // 정수 BPM 은 "120.00" 으로 안 부풀린다
    expect(formatBpm(undefined)).toBe(EMPTY_CELL);
    expect(formatBpm(null)).toBe(EMPTY_CELL);
  });

  it("Q# 는 세 자리", () => {
    expect(cueLabel(SECTIONS[0])).toBe("Q010");
    expect(cueLabel(SECTIONS[SECTIONS.length - 1])).toBe("Q180");
  });

  it("SNAP 인 큐만 흰 좌측선을 받는다", () => {
    const snaps = SECTIONS.filter(isSnapCue).map(cueLabel);
    expect(snaps).toEqual(["Q010", "Q050", "Q090", "Q130", "Q150"]);
  });

  it("팔레트 범례 id 로 큐 색을 찾는다", () => {
    expect(paletteColorFor(SECTIONS[4], CUE_SHEET_EXAMPLE.palette_legend)).toBe("#FF3C9E");
    expect(paletteColorFor(SECTIONS[0], CUE_SHEET_EXAMPLE.palette_legend)).toBe("#FFB43C");
  });

  it("그룹별 인텐시티는 그대로 적는다", () => {
    expect(sectionIntensityText(SECTIONS[1])).toBe("KEY 70 / BACK 35");
    expect(sectionIntensityPercent(SECTIONS[1])).toBe(70);
  });

  it("곡 길이는 헤더 메타를 그대로 쓴다", () => {
    expect(TOTAL).toBe(236_000);
  });
});

// t388 — 큐시트 표(13열)가 화면 오른쪽으로 잘려 마지막 열(Fade)에 닿을 방법이
// 없다는 감독 신고. 이 컴포넌트는 useState/useRef/useCallback 을 쓰는 훅
// 컴포넌트라 RunbookMode.test.tsx 처럼 함수를 직접 호출해 렌더 트리를 얻을
// 수 없다(훅은 React 렌더 컨텍스트 밖에서 부르면 던진다) — 그래서 이 파일의
// 다른 모든 테스트처럼 컴포넌트를 렌더하지 않고 소스/스타일시트 텍스트를
// 구조적으로 검사한다. 스크린샷으로 시각 확인은 할 수 없다는 점을 그대로
// 남긴다(§ 검증 섹션 참고).
describe("t388 — 큐시트 표가 TIMELINE 레일과 같은 방식으로 좌우 스크롤한다", () => {
  const componentSource = readFileSync(
    new URL("./CueSheetTimeline.tsx", import.meta.url),
    "utf-8",
  );
  const stylesSource = readFileSync(new URL("../styles.css", import.meta.url), "utf-8");

  it("표가 전용 가로 스크롤 컨테이너(cst-sheet-scroll) 안에 있다", () => {
    // cst-sheet-scroll 여는 태그와 <table className="cst-sheet"> 사이에
    // 다른 스크롤 컨테이너가 끼어들지 않는지 순서로 확인한다.
    const scrollWrapperIndex = componentSource.indexOf('className="cst-sheet-scroll"');
    const tableIndex = componentSource.indexOf('<table className="cst-sheet">');
    expect(scrollWrapperIndex).toBeGreaterThan(-1);
    expect(tableIndex).toBeGreaterThan(scrollWrapperIndex);
  });

  it("감독이 잘려 보인다고 신고한 Fade 열은 오른쪽 끝 근처에 실재한다 — 스크롤로 닿을 위치", () => {
    const columnsMatch = componentSource.match(/const SHEET_COLUMNS = \[([\s\S]*?)\];/);
    expect(columnsMatch).not.toBeNull();
    const columns = (columnsMatch as RegExpMatchArray)[1]
      .split(",")
      .map((s) => s.trim().replace(/^"|"$/g, ""))
      .filter(Boolean);
    expect(columns).toContain("Fade");
    // 첫 칸이 아니라 뒤쪽에 있어야 "잘려서 안 보인다"는 신고와 일치한다.
    expect(columns.indexOf("Fade")).toBeGreaterThan(columns.length / 2);
  });

  it("cst-sheet-scroll 은 가로 스크롤을 명시적으로 켜 두었다 — TIMELINE 레일(cst-rail)과 같은 원리", () => {
    const railRule = stylesSource.match(/\.cst-rail\s*{([^}]*)}/);
    const sheetScrollRules = [...stylesSource.matchAll(/\.cst-sheet-scroll\s*{([^}]*)}/g)];
    expect(railRule).not.toBeNull();
    expect((railRule as RegExpMatchArray)[1]).toMatch(/overflow-x:\s*auto/);
    expect(sheetScrollRules.length).toBeGreaterThan(0);
    const combined = sheetScrollRules.map((m) => m[1]).join("\n");
    // overflow: auto (양축) 또는 overflow-x: auto 둘 중 하나로 가로 스크롤이
    // 켜져 있어야 한다 — cst-rail 처럼 overflow-x 를 명시하는 쪽이 의도를
    // 더 분명히 하므로 이 값으로 고정한다.
    expect(combined).toMatch(/overflow-x:\s*auto/);
  });

  it("BPM 표시는 formatBpm 을 거친다 — 원본 부동소수점을 그대로 찍지 않는다", () => {
    expect(componentSource).toMatch(/\{formatBpm\(timeline\.bpm\)\}\s*BPM/);
  });

  it("Fade 표시는 소수점 2자리로 반올림한다", () => {
    expect(componentSource).toMatch(/section\.fade_seconds\.toFixed\(2\)/);
  });

  it("표 자체가 스크롤 컨테이너보다 넓게 강제된다(min-width) — 그래야 잘림이 아니라 스크롤이 생긴다", () => {
    const sheetWidthRules = [...stylesSource.matchAll(/\.cst-sheet\s*{([^}]*)}/g)].map((m) => m[1]);
    const minWidthLine = sheetWidthRules.find((rule) => /min-width/.test(rule));
    expect(minWidthLine).toBeDefined();
    const px = Number((minWidthLine as string).match(/min-width:\s*(\d+)px/)?.[1]);
    expect(px).toBeGreaterThanOrEqual(1100);
  });
});
