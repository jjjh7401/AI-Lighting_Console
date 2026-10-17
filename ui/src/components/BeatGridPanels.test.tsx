// 박자 격자 편집 칸·전환 화면·장면 전환·2D 무대 렌더 시험
// (SPEC-LDBEAT-001 M9 step 3·4·5, 카드 t561 — AC-LDBEAT-020·021(b)·022).
//
// 이 프로젝트는 jsdom 이 없다 — `renderToStaticMarkup`으로 부품 하나씩의
// 첫 화면을 HTML 문자열로 그려 확인하고, BeatGrid.tsx 안의 배치(같은 자리
// 교체·필드 순서)는 소스 구조로 확인한다.
import { readFileSync } from "node:fs";

import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { BeatGridCue, BeatGridMovementVocabulary, BeatGridTrack } from "../protocol";
import {
  BeatGridConsoleCommand,
  BeatGridMovementPicker,
  BeatGridMovementRow,
  movementChangesFromDraft,
  movementDraftFrom,
  BeatGridSideRow,
  focusFieldRowNames,
} from "./BeatGridCuePanelParts";
import { BeatGridStage, stageViewWidth } from "./BeatGridStage";
import { BeatGridJoint, BeatGridScenePanel, BeatGridSceneRow } from "./BeatGridTimelineParts";
import { BeatGridTransitionView } from "./BeatGridTransitionView";
import { sceneEntryEdits } from "./beatGridTransition";

const SOURCE = readFileSync(new URL("./BeatGrid.tsx", import.meta.url), "utf-8");
const PANEL_CSS = readFileSync(new URL("./beatGridPanels.css", import.meta.url), "utf-8");

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

function track(name: string, cues: BeatGridCue[], overrides: Partial<BeatGridTrack> = {}): BeatGridTrack {
  return { group_no: null, group_no_confirmed: false, group_name: name, layer_role: null, cues, ...overrides };
}

describe("AC-LDBEAT-020(d)(e) — 전환 화면", () => {
  const prev = cue(0, { position_preset_no: "2.1" });
  const cur = cue(4, { position_preset_no: "2.2", entry: { fade_bars: 1, mib_mode: "dark" } });
  const html = renderToStaticMarkup(
    <BeatGridTransitionView
      track={track("MOVER", [prev, cur])}
      cue={cur}
      prevCue={prev}
      secondsPerBar={2.14}
      beatsPerBar={4}
      sectionStartBars={null}
      onEditRequest={() => undefined}
    />,
  );

  it("페이드·트리거·딜레이·위치만 따로·MIB·트래킹 순서로 보인다", () => {
    const order = ["페이드", "트리거", "딜레이", "위치만 따로", "MIB", "트래킹"].map((label) =>
      html.indexOf(`<label>${label}`),
    );
    expect(order.every((index) => index >= 0)).toBe(true);
    expect([...order].sort((a, b) => a - b)).toEqual(order);
  });

  it("「들어올 때(페이드)」는 이 화면에 있다", () => {
    expect(html).toContain("들어올 때");
  });

  it("시간은 초 먼저, 마디는 괄호", () => {
    expect(html).toMatch(/\d+\.\d{2}초 \(1마디\)/);
  });

  it("딜레이는 [미확인], 위치만 따로는 ⚠미확인 표기를 유지한다", () => {
    expect(html).toContain("[미확인]");
    expect(html).toContain("⚠미확인");
  });

  // 카드 t574 — SPEC 0.5.0 이 저장 칸을 만들었으니 편집 경로가 있으면 켜진다.
  it("편집 경로가 있으면 트리거 박·딜레이·위치만 따로·트래킹이 켜진다", () => {
    for (const label of ["트리거 박", "딜레이(박)", "위치만 따로", "트래킹"]) {
      const control = new RegExp(`<(select|input)[^>]*aria-label="${label.replace(/[()]/g, "\\$&")}"[^>]*>`);
      const tag = html.match(control)?.[0] ?? "";
      expect(tag, label).not.toBe("");
      expect(tag, label).not.toContain('disabled=""');
    }
  });

  it("트리거 박 선택지는 그 곡 박자표만큼(3/4 → 1~3)", () => {
    const threeFour = renderToStaticMarkup(
      <BeatGridTransitionView
        track={track("MOVER", [prev, cur])}
        cue={cur}
        prevCue={prev}
        secondsPerBar={2.14}
        beatsPerBar={3}
        sectionStartBars={null}
        onEditRequest={() => undefined}
      />,
    );
    const select = threeFour.match(/<select[^>]*aria-label="트리거 박"[^>]*>([\s\S]*?)<\/select>/)?.[1] ?? "";
    expect((select.match(/<option/g) ?? []).length).toBe(3);
  });

  it("박자표를 모르면 트리거 박은 비활성(4를 지어내지 않음)", () => {
    const unknown = renderToStaticMarkup(
      <BeatGridTransitionView
        track={track("MOVER", [prev, cur])}
        cue={cur}
        prevCue={prev}
        secondsPerBar={2.14}
        beatsPerBar={null}
        sectionStartBars={null}
        onEditRequest={() => undefined}
      />,
    );
    expect(unknown.match(/<select[^>]*aria-label="트리거 박"[^>]*>/)?.[0]).toContain('disabled=""');
  });

  it("저장된 박 페이드·트리거 박·트래킹을 보여 준다", () => {
    const stored = cue(4, {
      entry: { fade_bars: null, mib_mode: null, fade_beats: 2, trigger_beat: 3, tracking: "Block" },
    });
    const shown = renderToStaticMarkup(
      <BeatGridTransitionView
        track={track("MOVER", [prev, stored])}
        cue={stored}
        prevCue={prev}
        secondsPerBar={2}
        beatsPerBar={4}
        sectionStartBars={null}
        onEditRequest={() => undefined}
      />,
    );
    expect(shown).toContain("1초 (2박)");
    expect(shown).toMatch(/<option value="3" selected="">3<\/option>/);
    expect(shown).toMatch(/<option value="Block" selected="">Block<\/option>/);
  });

  it("저장된 MIB 모드를 그대로 보여 준다", () => {
    expect(html).toContain("저장값 dark");
  });

  it("편집 경로가 없으면 페이드 입력이 없다(읽기 전용)", () => {
    const readOnly = renderToStaticMarkup(
      <BeatGridTransitionView
        track={track("MOVER", [prev, cur])}
        cue={cur}
        prevCue={prev}
        secondsPerBar={2.14}
        beatsPerBar={4}
        sectionStartBars={null}
      />,
    );
    expect(readOnly).not.toContain('aria-label="페이드 길이"');
    expect(readOnly.match(/<select[^>]*aria-label="트래킹"[^>]*>/)?.[0]).toContain('disabled=""');
  });

  it("경고 판정은 [제안] 표기", () => {
    const lit = cue(0, { position_preset_no: "2.1" });
    const snap = cue(4, { position_preset_no: "2.2", entry: { fade_bars: 0, mib_mode: null } });
    const warned = renderToStaticMarkup(
      <BeatGridTransitionView
        track={track("MOVER", [lit, snap])}
        cue={snap}
        prevCue={lit}
        secondsPerBar={2.14}
        beatsPerBar={4}
        sectionStartBars={null}
      />,
    );
    expect(warned).toContain("⚠ [제안] 켜진 채 위치가 끊어 바뀜");
  });
});

describe("AC-LDBEAT-020(d) — 같은 자리에서 바뀐다(별도 상자 0건)", () => {
  it("전환 화면과 큐 편집 화면은 한 삼항의 두 갈래다", () => {
    expect(SOURCE).toMatch(
      /transitionView && selectedCue && selectedPrevCue \? \([\s\S]*?<BeatGridTransitionView[\s\S]*?\) : \(\s*<BeatGridCueFocus/,
    );
  });
  it("예전 자리표시자 상자는 남아 있지 않다", () => {
    expect(SOURCE).not.toContain("M3 배선 전까지 읽기 전용");
  });
});

describe("AC-LDBEAT-020(b) — 전환 토글", () => {
  it("켜지면 노란색", () => {
    expect(PANEL_CSS).toMatch(
      /\.beat-grid-cue-panel \.beat-grid-transition-toggle\.is-on,[\s\S]*?\{[^}]*background: #ffd84d/,
    );
  });
  it("곡 첫 큐(들어오는 전환 없음)에서는 비활성", () => {
    expect(SOURCE).toContain("disabled={firstCue || !selectedPrevCue}");
  });
});

describe("AC-LDBEAT-020(c) — 콘솔 명령 버튼", () => {
  it("편집 칸 맨 아래 버튼, 처음엔 닫혀 있다", () => {
    const html = renderToStaticMarkup(<BeatGridConsoleCommand lines={["Group 1 ; At Preset 2.1"]} />);
    expect(html).toContain('class="beat-grid-tg"');
    expect(html).toContain("콘솔 명령");
    expect(html).not.toContain("beat-grid-cmdbox");
  });
  it("지금 보는 화면에 맞는 줄을 고른다(전환이면 전환 줄)", () => {
    expect(SOURCE).toMatch(
      /transitionView && selectedPrevCue\s*\?\s*transitionConsoleCommandLines\([\s\S]*?:\s*cueConsoleCommandLines\(/,
    );
  });
  it("켜지면 노란색(.beat-grid-tg.is-on)", () => {
    expect(PANEL_CSS).toMatch(/\.beat-grid-tg\.is-on \{[^}]*background: #ffd84d/);
  });
});

describe("재생 — 음원 시계·재생선 연속 이동·따라가기 배선(BeatGrid.tsx)", () => {
  it("재생 틱은 음원 시계를 먼저 읽고, 음원이 없으면 성능시계로 이어 간다", () => {
    expect(SOURCE).toMatch(/const audioSeconds = audioClockSeconds\(audioRef\.current\)/);
    expect(SOURCE).toMatch(/const next = audioSeconds \?\? elapsedPlaybackSeconds\(/);
  });
  it("재생선은 마디가 아니라 초에서 구한 소수 픽셀로 놓이고 한 마디 폭을 덮는다", () => {
    // 3차 전체 실행 G-19 — 재생선·마디 번호·빔 위상은 마디 지도 0마디 시작 시각을 기준으로 한다.
    expect(SOURCE).toMatch(
      /const playheadX = playheadPixelX\(playbackSeconds, secondsPerBar, pxPerBar, barOriginSeconds\)/,
    );
    expect(SOURCE).toMatch(/secondsToBar\(playbackSeconds, secondsPerBar, maxBar, barOriginSeconds\)/);
    expect(SOURCE).toMatch(/secondsToBar\(next, secondsPerBar, axisEnd, barOriginSeconds\)/);
    expect(SOURCE).toMatch(/seconds: playbackSeconds - originOf\(barOriginSeconds\)/);
    expect(SOURCE).toMatch(/style=\{\{ left: playheadX, width: pxPerBar \}\}/);
  });
  it("따라가기는 매 프레임 연속 목표로 가고, 직접 스크롤 신호(휠·터치·스크롤바)에 멈춘다", () => {
    expect(SOURCE).toMatch(/const target = followScrollTarget\(x, el\.scrollLeft, ctx\.visibleWidth\)/);
    expect(SOURCE).toMatch(/onWheel=\{pauseFollowForManualScroll\}/);
    expect(SOURCE).toMatch(/onTouchMove=\{pauseFollowForManualScroll\}/);
    expect(SOURCE).toMatch(/if \(event\.target === event\.currentTarget\) pauseFollowForManualScroll\(\)/);
  });
  it("▶·⏮·지도 클릭은 따라가기를 곧바로 다시 켠다", () => {
    expect(SOURCE).toMatch(/setPlaying\(true\);\s*resumeFollow\(\);/);
    expect(SOURCE).toMatch(/const rewindToStart = \(\) => \{\s*setPlaybackSeconds\(0\);\s*resumeFollow\(\);/);
    expect(SOURCE).toMatch(/const jumpToBar = \(bar: number\) => \{[\s\S]*?resumeFollow\(\);/);
  });
});

describe("곡 첫 칸 페이드 들어옴 이음매 — 앞 칸 없는 조인트(LOVE ATTACK 7마디 워시 2마디 번짐 꼴)", () => {
  const joint = (next: BeatGridCue, prev: BeatGridCue | null = null) =>
    renderToStaticMarkup(
      <BeatGridJoint
        prev={prev}
        cue={next}
        nextSegmentWidth={600}
        prevFill={null}
        sectionStartBars={null}
        secondsPerBar={2.14}
        isOn={false}
        onOpen={() => undefined}
        pxPerBar={300}
        beatsPerBar={4}
      />,
    );
  it("첫 칸 페이드는 ◢ 와 어둠에서 시작하는 번짐(2마디 = 600px)으로 그려진다", () => {
    const html = joint(cue(7, { label: "라벤더 워시 40%", entry: { fade_bars: 2, mib_mode: null } }));
    expect(html).toMatch(/class="beat-grid-joint is-fade"[^>]*>◢</);
    expect(html).toMatch(/beat-grid-fade-bleed[^>]*width:600px/);
    expect(html).toContain("linear-gradient(90deg, #25252c, transparent)");
  });
  it("MIB 칸(어둠 칸 뒤에서 위치가 바뀜)은 보라 M 이음매다", () => {
    const dark = cue(4, { label: "—", position_preset_no: "2.1" });
    const html = joint(cue(8, { position_preset_no: "2.2" }), dark);
    expect(html).toMatch(/class="beat-grid-joint is-mib"[^>]*>M</);
  });
  it("BeatGrid 는 첫 칸에 페이드가 있을 때만 앞 칸 없는 이음매를 그린다", () => {
    expect(SOURCE).toMatch(/<BeatGridJoint\s+prev=\{null\}\s+pxPerBar=/);
    expect(SOURCE).toMatch(/visibleSegments\[0\] === segments\[0\] &&\s*entryHasFade\(segments\[0\]\.cue\.entry\)/);
  });
});

describe("AC-LDBEAT-020(a) — 이음매와 장면 전환 알약", () => {
  it("페이드가 있는 이음매는 ◢ 와 번짐", () => {
    const html = renderToStaticMarkup(
      <BeatGridJoint
        prev={cue(0)}
        cue={cue(4, { entry: { fade_bars: 1, mib_mode: null } })}
        nextSegmentWidth={100}
        prevFill={null}
        sectionStartBars={null}
        secondsPerBar={2.14}
        isOn={false}
        onOpen={() => undefined}
      />,
    );
    expect(html).toContain("beat-grid-fade-bleed");
    expect(html).toMatch(/class="beat-grid-joint is-fade"[^>]*>◢</);
  });
  it("1마디 페이드 이음매는 앞 칸 색이 1마디 폭으로 번진다(앞 칸 색 → 투명)", () => {
    const html = renderToStaticMarkup(
      <BeatGridJoint
        prev={cue(0)}
        cue={cue(4, { entry: { fade_bars: 1, mib_mode: null } })}
        nextSegmentWidth={900}
        prevFill="#f0b4c8"
        sectionStartBars={null}
        secondsPerBar={2.14}
        isOn={false}
        onOpen={() => undefined}
        pxPerBar={300}
        beatsPerBar={4}
      />,
    );
    expect(html).toMatch(/beat-grid-fade-bleed[^>]*width:300px/);
    expect(html).toContain("linear-gradient(90deg, #f0b4c8, transparent)");
    expect(html).toMatch(/class="beat-grid-joint is-fade"[^>]*>◢</);
  });
  it("3줄 이상 바뀌는 마디에 알약", () => {
    const html = renderToStaticMarkup(
      <BeatGridSceneRow bars={[{ bar: 8, count: 3 }]} activeBar={null} width={500} onSelect={() => undefined} />,
    );
    expect(html).toContain("장면 전환 ▼");
    expect(html).toContain("8마디 3줄");
  });
  it("알약 → 그 순간 전체 표 + 「모두 끊기/모두 1박 페이드」", () => {
    const tracks = ["A", "B", "C"].map((name) => track(name, [cue(0), cue(8)]));
    const html = renderToStaticMarkup(
      <BeatGridScenePanel
        bar={8}
        tracks={tracks}
        secondsPerBar={2.14}
        sectionStartBars={null}
        onClose={() => undefined}
        onSelectRow={() => undefined}
        onBulkEntry={() => undefined}
      />,
    );
    expect(html).toContain("이 순간 3줄이 함께 바뀜");
    expect(html).toContain("모두 끊기");
    expect(html).toContain("모두 1박 페이드");
    expect((html.match(/<tr>/g) ?? []).length).toBe(3);
  });

  // 카드 t574 — fade_beats 저장 칸이 생겨 「모두 1박 페이드」가 켜진다(AC-020(j)).
  it("편집 경로가 있으면 「모두 끊기」「모두 1박 페이드」 둘 다 켜진다", () => {
    const tracks = ["A", "B", "C"].map((name) => track(name, [cue(0), cue(8)]));
    const html = renderToStaticMarkup(
      <BeatGridScenePanel
        bar={8}
        tracks={tracks}
        secondsPerBar={2.14}
        beatsPerBar={4}
        sectionStartBars={null}
        onClose={() => undefined}
        onSelectRow={() => undefined}
        onBulkEntry={() => undefined}
      />,
    );
    expect(html).not.toMatch(/<button[^>]*disabled=""[^>]*>모두 1박 페이드/);
    expect(html).not.toMatch(/<button[^>]*disabled=""[^>]*>모두 끊기/);
  });

  it("일괄 전환은 각 줄의 다른 entry 값을 보존한다", () => {
    const keep = cue(8, { entry: { fade_bars: 2, mib_mode: "dark", trigger_beat: 2, tracking: "Block" } });
    const tracks = [track("A", [cue(0), keep]), track("B", [cue(0), cue(8)]), track("C", [cue(0), cue(8)])];
    const edits = sceneEntryEdits(tracks, 8, { fade_bars: null, fade_beats: 1 });
    expect(edits[0]).toEqual({
      target: "A",
      entry: {
        fade_bars: null,
        mib_mode: "dark",
        fade_beats: 1,
        trigger_beat: 2,
        delay_beats: null,
        position_late_beats: null,
        tracking: "Block",
      },
    });
    expect(edits.map((e) => e.target)).toEqual(["A", "B", "C"]);
  });
});

describe("카드 t653 — 초 표기 뒤의 0 떼기 (시안 tc·beatsToS 와 같은 표기)", () => {
  it("전환 화면 「박 = 곡 N초」는 8.00 대신 8로 쓴다", () => {
    const prev = cue(0);
    const cur = cue(4, { entry: { fade_bars: 1, mib_mode: null, trigger_beat: 1 } });
    const html = renderToStaticMarkup(
      <BeatGridTransitionView
        track={track("MOVER", [prev, cur])}
        cue={cur}
        prevCue={prev}
        secondsPerBar={2}
        beatsPerBar={4}
        sectionStartBars={null}
        onEditRequest={() => undefined}
      />,
    );
    expect(html).toContain("박 = 곡 8초");
    expect(html).not.toContain("8.00초");
  });
  it("장면 전환 머리글 「(곡 N초)」는 120.00 대신 120으로 쓴다", () => {
    const tracks = ["A", "B", "C"].map((name) => track(name, [cue(0), cue(60)]));
    const html = renderToStaticMarkup(
      <BeatGridScenePanel
        bar={60}
        tracks={tracks}
        secondsPerBar={2}
        sectionStartBars={null}
        onClose={() => undefined}
        onSelectRow={() => undefined}
        onBulkEntry={() => undefined}
      />,
    );
    expect(html).toContain("(곡 120초)");
    expect(html).not.toContain("120.00초");
  });
});

describe("AC-LDBEAT-021(b) — 편집 칸 필드 순서", () => {
  it("밝기 → 위치 → 색 → 움직임 → 옆빛 L·R → 콘솔 명령", () => {
    const order = [
      'field: "밝기"',
      'field: "위치 프리셋"',
      'field: "색 프리셋"',
      "<BeatGridMovementRow",
      "<BeatGridSideRow",
      "<BeatGridConsoleCommand",
    ].map((needle) => SOURCE.indexOf(needle));
    expect(order.every((index) => index >= 0)).toBe(true);
    expect([...order].sort((a, b) => a - b)).toEqual(order);
  });
  it("「들어올 때」 필드는 큐 편집 화면에 없다", () => {
    expect(SOURCE).not.toContain("beat-grid-cue-field-entry");
    expect(SOURCE).not.toContain('rows.push({ field: "들어올 때"');
  });
  it("움직임·옆빛 행이 보인다", () => {
    expect(renderToStaticMarkup(<BeatGridMovementRow value="미정" isUnset />)).toContain('data-field="움직임"');
    expect(renderToStaticMarkup(<BeatGridSideRow />)).toContain('data-field="옆빛 L·R"');
  });
  it("옆빛 L·R 토글이 없으면 「이 구간 왼쪽·오른쪽 따로」는 비활성이다", () => {
    const html = renderToStaticMarkup(<BeatGridSideRow />);
    expect(html).toContain("같이(갈라지지 않음)");
    expect(html).toMatch(/<button[^>]*disabled[^>]*>이 구간 왼쪽·오른쪽 따로<\/button>/);
  });
  it("옆빛 L·R 토글이 있고 아직 안 갈랐으면 「따로」를 누를 수 있다", () => {
    const html = renderToStaticMarkup(
      <BeatGridSideRow lrSplit={{ isSplit: false, onToggle: () => undefined }} />,
    );
    expect(html).toContain("같이(갈라지지 않음)");
    expect(html).toContain(">이 구간 왼쪽·오른쪽 따로</button>");
    expect(html).not.toContain("disabled");
  });
  it("갈라진 상태면 「L·R 다시 합치기」가 보이고 누를 수 있다", () => {
    const html = renderToStaticMarkup(
      <BeatGridSideRow lrSplit={{ isSplit: true, onToggle: () => undefined }} />,
    );
    expect(html).toContain("따로(왼쪽·오른쪽 갈라짐)");
    expect(html).toContain(">L·R 다시 합치기</button>");
    expect(html).not.toContain("disabled");
  });
  it("움직임 행 — 서버가 미확인으로 가른 칸에만 「⚠ 실기 미확인」(카드 t579, REQ-LDBEAT-010)", () => {
    const flagged = renderToStaticMarkup(
      <BeatGridMovementRow value="circle · Pan+Tilt · 4박" isUnset={false} unverifiedTerms={["circle"]} />,
    );
    expect(flagged).toContain("⚠ 실기 미확인");
    expect(flagged).toContain("곡 기본값으로 넣지 않음");
    const plain = renderToStaticMarkup(<BeatGridMovementRow value="wave · Tilt · 2마디" isUnset={false} />);
    expect(plain).not.toContain("실기 미확인");
    const empty = renderToStaticMarkup(
      <BeatGridMovementRow value="wave · Tilt · 2마디" isUnset={false} unverifiedTerms={[]} />,
    );
    expect(empty).not.toContain("실기 미확인");
  });
  it("타임라인 배지는 서버 목록만 읽는다 — 라벨 글자 맞추기 없음(카드 t579)", () => {
    expect(SOURCE).toContain("unverifiedCells.get(cueEditKey(track.group_name, segment.cue.bar))");
    expect(SOURCE).not.toContain("UNCONFIRMED_SHAPE_KEYWORDS");
    expect(SOURCE).not.toContain("isUnconfirmedShapeCue(");
  });
  it("초점 항목은 편집 칸 행 이름과 짝지어진다(카드 t560 연동용)", () => {
    expect(focusFieldRowNames("색")).toEqual(["색 프리셋"]);
    expect(focusFieldRowNames("옆빛")).toEqual(["옆빛 L·R"]);
  });
});

describe("AC-LDBEAT-022 — 2D 무대", () => {
  const tracks = [track("WASH", [cue(0)]), track("BACK", [cue(0)])];
  const fixtures = [
    { fid: 1, name: "w1", x: 0, y: 0, z: 0, rotx: 0, roty: 0, rotz: 0, confirmedGroupName: "WASH" },
    { fid: 2, name: "w2", x: 10, y: 0, z: 0, rotx: 0, roty: 0, rotz: 0, confirmedGroupName: "WASH" },
    { fid: 3, name: "b1", x: 5, y: 10, z: 0, rotx: 0, roty: 0, rotz: 0, confirmedGroupName: "BACK" },
  ];

  it("(a) 상태판·3D 캡처·평면도 전환 UI가 없다", () => {
    for (const word of ["상태판", "3D 캡처", "평면도"]) {
      expect(SOURCE).not.toContain(word);
    }
  });

  it("(b) 고른 줄의 장비에 노란 점선, 그룹 이름표, 클릭 영역", () => {
    const html = renderToStaticMarkup(
      <BeatGridStage
        fixtures={fixtures}
        tracks={tracks}
        viewBar={0}
        selectedTrackName="WASH"
        onSelectTrack={() => undefined}
      />,
    );
    expect(html).toMatch(/class="beat-grid-stage-selected"[^>]*stroke="#ffd84d"[^>]*stroke-dasharray="5 3"/);
    expect((html.match(/beat-grid-stage-selected/g) ?? []).length).toBe(1);
    expect(html).toContain(">WASH</text>");
    expect(html).toContain(">BACK</text>");
    expect(html).toContain('data-track="WASH"');
    expect(html).toContain('data-track="BACK"');
  });

  it("(c) 높이 320px, 폭 비율 1.2", () => {
    expect(PANEL_CSS).toMatch(
      /\.beat-grid \.beat-grid-insp \.beat-grid-stage-pane \{[^}]*flex: 1\.2 1 0;[^}]*height: 320px;/,
    );
  });

  it("(c) 칸 비율에 맞춰 가로를 채운다(창 크기에 따라 다시 계산)", () => {
    expect(stageViewWidth(1200, 300)).toBe(1200);
    expect(stageViewWidth(600, 300)).toBe(600);
    expect(stageViewWidth(100, 300)).toBe(420);
  });

  it("좌표가 없으면 지어내지 않고 안내", () => {
    const html = renderToStaticMarkup(
      <BeatGridStage fixtures={[]} tracks={tracks} viewBar={0} selectedTrackName={null} onSelectTrack={() => undefined} />,
    );
    expect(html).toContain("무대 좌표 미제공");
  });
});

// 카드 t584 — 「움직임」 고르기 목록(REQ-LDBEAT-006(vi)·010·021(b)).
const VOCAB: BeatGridMovementVocabulary = {
  shapes: [
    { name: "sweep", unverified: false },
    { name: "circle", unverified: true },
    { name: "wave", unverified: false },
  ],
  axes: ["Pan", "Tilt"],
  period_units: ["bar", "beat"],
  phase_spread_unverified: true,
};
const noop = () => {};

describe("카드 t584 — 움직임 고르기 초안", () => {
  it("빈 칸은 「없음」에서 출발한다 — 미확인 모양을 먼저 고르지 않는다", () => {
    expect(movementDraftFrom(null)).toEqual({
      shape: "",
      axesKey: "",
      periodUnit: "",
      periodValue: "",
      phaseSpread: false,
    });
  });
  it("지금 칸 값으로 채운다", () => {
    const draft = movementDraftFrom({
      shape: "wave",
      axes: ["Pan", "Tilt"],
      period_unit: "bar",
      period_value: 2,
      phase_spread: true,
    });
    expect(draft).toEqual({ shape: "wave", axesKey: "Pan+Tilt", periodUnit: "bar", periodValue: "2", phaseSpread: true });
  });
  it("「없음」은 움직임 지우기(null)", () => {
    expect(movementChangesFromDraft(movementDraftFrom(null))).toBeNull();
  });
  it("축이 없거나 주기 수가 틀리면 적용할 수 없다(undefined)", () => {
    const base = { shape: "wave", axesKey: "Tilt", periodUnit: "", periodValue: "", phaseSpread: false };
    expect(movementChangesFromDraft({ ...base, axesKey: "" })).toBeUndefined();
    expect(movementChangesFromDraft({ ...base, periodUnit: "beat", periodValue: "" })).toBeUndefined();
    expect(movementChangesFromDraft({ ...base, periodUnit: "beat", periodValue: "0" })).toBeUndefined();
    expect(movementChangesFromDraft({ ...base, periodUnit: "beat", periodValue: "1.5" })).toBeUndefined();
  });
  it("서버 apply_beat_grid_edit 의 app_movement 모양 그대로 — 음악 단위만", () => {
    expect(
      movementChangesFromDraft({ shape: "circle", axesKey: "Pan+Tilt", periodUnit: "beat", periodValue: "4", phaseSpread: false }),
    ).toEqual({ shape: "circle", axes: ["Pan", "Tilt"], period_unit: "beat", period_value: 4, phase_spread: null });
    expect(
      movementChangesFromDraft({ shape: "wave", axesKey: "Tilt", periodUnit: "", periodValue: "", phaseSpread: true }),
    ).toEqual({ shape: "wave", axes: ["Tilt"], period_unit: null, period_value: null, phase_spread: true });
  });
});

describe("카드 t584 — 움직임 고르기 칸 렌더", () => {
  it("모양 목록은 서버 어휘 그대로, 미확인 모양엔 ⚠", () => {
    const html = renderToStaticMarkup(
      <BeatGridMovementPicker current={null} vocabulary={VOCAB} onApply={noop} onCancel={noop} />,
    );
    // 빈 칸이면 「없음」이 선택돼 있고, 미확인 모양은 선택돼 있지 않다.
    expect(html).toContain('<option value="" selected="">— 없음 —</option>');
    expect(html).toContain('<option value="circle">circle ⚠</option>');
    expect(html).toContain('<option value="sweep">sweep</option>');
    expect(html).not.toContain("ballyhoo");
    // 빈 칸에서 열면 미확인 안내가 없다(아무것도 고르지 않았다).
    expect(html).not.toContain("직접 고른 칸에만");
  });
  it("미확인 모양이 들어 있는 칸을 열면 축·주기·위상 칸과 안내가 보인다", () => {
    const html = renderToStaticMarkup(
      <BeatGridMovementPicker
        current={{ shape: "circle", axes: ["Pan", "Tilt"], period_unit: "beat", period_value: 4, phase_spread: null }}
        vocabulary={VOCAB}
        onApply={noop}
        onCancel={noop}
      />,
    );
    expect(html).toContain('aria-label="움직임 축"');
    expect(html).toContain('<option value="Pan+Tilt" selected="">Pan+Tilt</option>');
    expect(html).toContain('<option value="beat" selected="">박</option>');
    expect(html).toContain("위상 펼침 ⚠");
    expect(html).toContain("⚠ 실기 미확인 — circle: 직접 고른 칸에만 들어가요");
  });
  it("행은 편집 가능할 때만 ✎, 편집 중이면 고르기 칸", () => {
    const edit = { current: null, vocabulary: VOCAB, editing: false, onOpen: noop, onApply: noop, onCancel: noop };
    expect(renderToStaticMarkup(<BeatGridMovementRow value="미정" isUnset edit={edit} />)).toContain("✎");
    expect(renderToStaticMarkup(<BeatGridMovementRow value="미정" isUnset />)).not.toContain("✎");
    expect(
      renderToStaticMarkup(<BeatGridMovementRow value="미정" isUnset edit={{ ...edit, editing: true }} />),
    ).toContain('aria-label="움직임 모양"');
  });
  it("저장은 onEditRequest(app_movement) 한 길, 어휘는 grid.movement_vocabulary 에서만", () => {
    expect(SOURCE).toContain("changes: { app_movement: movement }");
    expect(SOURCE).toContain("vocabulary: grid.movement_vocabulary");
  });
});
