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

// t388 — 큐시트 표(14열)가 화면 오른쪽으로 잘려 마지막 열에 닿을 방법이 없다는
// 감독 신고. 이 컴포넌트는 useState/useRef/useCallback 을 쓰는 훅 컴포넌트라
// RunbookMode.test.tsx 처럼 함수를 직접 호출해 렌더 트리를 얻을 수 없다(훅은
// React 렌더 컨텍스트 밖에서 부르면 던진다) — 그래서 이 파일의 다른 모든
// 테스트처럼 컴포넌트를 렌더하지 않고 소스/스타일시트 텍스트를 구조적으로
// 검사한다. 스크린샷으로 시각 확인은 할 수 없다는 점을 그대로 남긴다(§ 검증
// 섹션 참고).
//
// 1차 수정(overflow: auto → overflow-x: auto; overflow-y: auto)은 조율자가
// 지적한 대로 **아무 동작도 안 바꾼 무효 수정**이었다 — 둘은 CSS 상 완전히
// 같다. 조상 사슬을 다시 훑어도(아래 CSS 주석 참고) 스크롤을 막는 요소는
// 없었다: 표는 이전에도 실제로 가로 스크롤이 됐다. 진짜 원인은 macOS 오버레이
// 스크롤바라 "더 있다"는 신호가 화면에 없었던 것 — 그래서 이번엔 "스크롤이
// 되는가"가 아니라 "스크롤할 수 있다는 게 보이는가"를 검사한다: (a) 실제로
// 자리를 차지하는 스크롤바 스타일이 새로 생겼는가, (b) 오른쪽 가장자리
// 그라디언트 신호가 새로 생겼는가, (c) 그 신호가 실제 스크롤 가능 여부(JS
// 로 잰 scrollWidth)에 따라 켜지고 꺼지는가.
describe("t388 재작업 — 스크롤 자체가 아니라 「더 있다」는 신호를 보이게 만든다", () => {
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

  // 무효였던 이전 단언(overflow-x: auto 문자열 존재)은 여기서 지운다 — 그
  // 단언은 「overflow: auto」였던 예전 CSS에서도 우연히는 안 통과했지만,
  // overflow-x/-y 로 쪼개기만 해도(동작 변화 없이) 통과해버려서 조율자가
  // 지적한 "동작을 바꾸지 않아도 통과하는 가드" 그 자체였다. 대신 실제로
  // 새로 생긴 스크롤바 스타일을 검사한다 — macOS 오버레이 스크롤바를 굵고
  // 항상 보이는 스크롤바로 바꾸는 것이 이번 수정의 실체다.
  it("스크롤바를 오버레이가 아니라 항상 자리를 차지하는 굵은 형태로 강제한다", () => {
    // .cst-sheet-scroll 은 두 곳에 나온다 — min-width:0 가드 목록의 한
    // 셀렉터로 한 번, 그리고 실제 스크롤 동작을 정의하는 자기 자신의 규칙
    // 으로 한 번. --cst-row-h 변수를 정의하는 쪽이 후자다.
    const scrollRule = [...stylesSource.matchAll(/\.cst-sheet-scroll\s*{([^}]*)}/g)].find((m) =>
      m[1].includes("--cst-row-h"),
    );
    expect(scrollRule).not.toBeUndefined();
    const body = (scrollRule as RegExpMatchArray)[1];
    // Firefox/최신 Chromium 공통 표준 축 — scrollbar-width: auto 는
    // "얇게도 아니고 숨기지도 않는다"는 뜻이라 오버레이보다 굵게 남는다.
    expect(body).toMatch(/scrollbar-width:\s*auto/);
    expect(body).toMatch(/scrollbar-color:\s*#[0-9a-f]{6}\s+#[0-9a-f]{6}/);
    // Chromium 계열(이 앱이 도는 웹뷰 포함) 전용 축 — 트랙과 손잡이가
    // 실제 색을 가진 사각 영역으로 항상 그려진다.
    expect(stylesSource).toMatch(/\.cst-sheet-scroll::-webkit-scrollbar\s*{[^}]*height:\s*\d+px/);
    expect(stylesSource).toMatch(/\.cst-sheet-scroll::-webkit-scrollbar-thumb\s*{[^}]*background:/);
  });

  it("오른쪽 가장자리에 '더 있다' 그라디언트(cst-sheet-edge-fade)가 창틀에 고정된 채 존재한다", () => {
    // 창틀(cst-sheet-scrollarea, position:relative)은 스크롤하지 않고,
    // 그 안에서 cst-sheet-scroll 만 옆으로 굴러간다 — 그래서 그라디언트가
    // absolute 로 창틀에 붙으면 표가 스크롤돼도 화면 위 같은 자리에 남는다.
    expect(componentSource).toMatch(/className="cst-sheet-scrollarea"/);
    expect(componentSource).toMatch(
      /sheetCanScrollRight\s*&&\s*<div className="cst-sheet-edge-fade"/,
    );
    const areaRule = stylesSource.match(/\.cst-sheet-scrollarea\s*{([^}]*)}/);
    expect(areaRule).not.toBeNull();
    expect((areaRule as RegExpMatchArray)[1]).toMatch(/position:\s*relative/);
    const fadeRule = stylesSource.match(/\.cst-sheet-edge-fade\s*{([^}]*)}/);
    expect(fadeRule).not.toBeNull();
    const fadeBody = (fadeRule as RegExpMatchArray)[1];
    expect(fadeBody).toMatch(/position:\s*absolute/);
    expect(fadeBody).toMatch(/pointer-events:\s*none/);
    expect(fadeBody).toMatch(/background:\s*linear-gradient/);
  });

  it("그라디언트는 '아직 스크롤할 게 남았을 때만' 켜진다 — 항상 켜진 장식이 아니다", () => {
    // sheetCanScrollRight 는 scrollWidth - clientWidth - scrollLeft 로
    // 실측한 잔여 스크롤 폭에서만 true 가 된다. 끝까지 스크롤한 사람에게
    // 거짓 "더 있다" 신호를 남기지 않는다는 게 이 계산의 요점이라, 그
    // 산식 자체를 소스에서 확인한다(렌더 없이 이 이상은 확인할 수 없다 —
    // 실제 scrollWidth 값은 브라우저에서만 나온다).
    expect(componentSource).toMatch(
      /box\.scrollWidth\s*-\s*box\.clientWidth\s*-\s*box\.scrollLeft/,
    );
    expect(componentSource).toMatch(/setSheetCanScrollRight\(remaining > 1\)/);
    // 스크롤할 때마다, 그리고 처음 그려질 때·창 크기가 바뀔 때도 다시 잰다 —
    // 한 번 계산하고 방치하면 리사이즈 후 신호가 낡는다.
    expect(componentSource).toMatch(/onSheetScroll[\s\S]*updateSheetScrollAffordance\(\)/);
    expect(componentSource).toMatch(/window\.addEventListener\("resize", updateSheetScrollAffordance\)/);
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

  it("조상 사슬 감사 — min-width:0 가드가 새 창틀(cst-sheet-scrollarea)까지 덮는다", () => {
    // 이 규칙 하나가 이번 재작업에서 실제로 바뀐 유일한 '가드' 성격 CSS다:
    // cst-sheet-scrollarea 가 cst-panel 의 새 직계 자식(flex 열의 자식)이
    // 됐으므로, 기존 min-width:0 리스트에 끼워 넣지 않으면 이 지점이 새
    // clipper 가 될 수 있었다.
    const guardRule = stylesSource.match(
      /\.cue-sheet-timeline,\s*\n\.cst-panel,\s*\n\.cst-rail,\s*\n\.cst-sheet-scrollarea,\s*\n\.cst-sheet-scroll\s*{([^}]*)}/,
    );
    expect(guardRule).not.toBeNull();
    expect((guardRule as RegExpMatchArray)[1]).toMatch(/min-width:\s*0/);
  });
});
