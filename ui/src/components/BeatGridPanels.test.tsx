// 박자 격자 편집 칸·전환 화면·장면 전환·2D 무대 렌더 시험
// (SPEC-LDBEAT-001 M9 step 3·4·5, 카드 t561 — AC-LDBEAT-020·021(b)·022).
//
// 이 프로젝트는 jsdom 이 없다 — `renderToStaticMarkup`으로 부품 하나씩의
// 첫 화면을 HTML 문자열로 그려 확인하고, BeatGrid.tsx 안의 배치(같은 자리
// 교체·필드 순서)는 소스 구조로 확인한다.
import { readFileSync } from "node:fs";

import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { BeatGridCue, BeatGridTrack } from "../protocol";
import {
  BeatGridConsoleCommand,
  BeatGridMovementRow,
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
    expect(shown).toContain("1.00초 (2박)");
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
