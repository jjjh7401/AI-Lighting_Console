// 칸 하나의 왼쪽·오른쪽 따로 색 — 왕복 시험: 데이터 → 서버 페이로드 → 화면 마크업.
//
// 데이터는 서버가 지금 내는 값의 사본(`cellSplitServerPayload.json`)이다. 사본이 서버 실출력과 어긋나면
// `server/tests/test_cell_split_payload_fixture.py` 가 실패하고 재생성 명령을 알려 준다:
//
//   uv run python -m server.tests.cell_split_payload_fixture
//
// 이 시험은 그 사본을 실제 `BeatGrid` 타임라인에 넣어, 나뉜 칸 하나가 띠·L/R 두 줄·쪽별 색으로 그려지고
// 나뉘지 않은 칸은 예전 그대로인지 마크업 문자열로 단언한다(jsdom 시험대가 없다 — `beatGridParity.test.tsx`
// 와 같은 방식).
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { BeatGridCue, BeatGridView } from "../../protocol";
import { BeatGrid, barToX } from "../BeatGrid";
import serverPayload from "./cellSplitServerPayload.json";
import { parsePresetPlan } from "./presetPlan";
import { PresetPlanPanel } from "./PresetPlanPanel";

const GRID = (serverPayload as unknown as { beat_grid: BeatGridView }).beat_grid;
const SIDE = GRID.tracks[0];
const OTHER = GRID.tracks[1];

// 사본 생성기(`server/tests/cell_split_payload_fixture.py`)가 정한 값 — 나뉜 칸과 그 다음 칸의 시작 마디,
// 나뉜 칸의 라벨. 사본이 이 약속과 다르면 첫 describe 가 먼저 실패한다.
const SPLIT_BAR = 7;
const NEXT_BAR = 14;
const SPLIT_LABEL = "왼쪽 오른쪽 따로";

const cueAt = (track: BeatGridView["tracks"][number], bar: number): BeatGridCue | undefined =>
  track.cues.find((cue) => cue.bar === bar);

/** 서버가 준 퍼센트 RGB → `#rrggbb` — 화면 코드(`cueRgbHex`)를 쓰지 않고 따로 계산해 대조한다. */
const hexOf = (rgb: readonly number[] | null | undefined): string => {
  if (!rgb) throw new Error("사본의 이 쪽에 RGB 가 없다");
  return `#${rgb.map((v) => Math.round((v / 100) * 255).toString(16).padStart(2, "0")).join("")}`;
};

/** 부모 막대(버튼)의 left 좌표(px) 전부 — 숨긴 칸은 여기에 없어야 한다. */
const buttonLefts = (html: string): string[] =>
  [...html.matchAll(/<button type="button" class="beat-grid-cue[^"]*" style="left:(\d+(?:px)?);/g)].map(
    (match) => match[1],
  );

const px = (bar: number): string => (bar === 0 ? "0" : `${barToX(bar)}px`);

function withoutSplit(grid: BeatGridView): BeatGridView {
  const copy = JSON.parse(JSON.stringify(grid)) as BeatGridView;
  for (const track of copy.tracks) for (const cue of track.cues) delete (cue as Partial<BeatGridCue>).split;
  return copy;
}

describe("서버 페이로드 — 사본이 나뉜 칸 하나를 담고 있다", () => {
  it("나뉜 칸은 마디 7 하나이고 두 쪽 모두 색 이름과 RGB 를 가진다", () => {
    expect(SIDE.cues.filter((cue) => cue.split != null).map((cue) => cue.bar)).toEqual([SPLIT_BAR]);
    expect(cueAt(SIDE, SPLIT_BAR)?.label).toBe(SPLIT_LABEL);
    expect(cueAt(SIDE, SPLIT_BAR)?.split).toEqual({
      left: { color: "Red", color_rgb: [100, 0, 0] },
      right: { color: "Blue", color_rgb: [5, 20, 100] },
    });
  });

  it("나뉘지 않은 칸에는 split 키가 아예 없다", () => {
    const plain = GRID.tracks.flatMap((track) => track.cues).filter((cue) => cue.label !== SPLIT_LABEL);
    expect(plain.length).toBeGreaterThan(0);
    expect(plain.every((cue) => !("split" in cue))).toBe(true);
  });
});

describe("화면 마크업 — 나뉜 칸이 띠와 L·R 두 줄로 그려진다", () => {
  const html = renderToStaticMarkup(<BeatGrid grid={GRID} barCount={26} />);
  const left = barToX(SPLIT_BAR);
  const width = barToX(NEXT_BAR) - barToX(SPLIT_BAR) - 2;

  it("나뉜 칸의 구간 위에 줄무늬 띠가 정확히 하나 얹힌다", () => {
    const banners = html.match(/<span class="beat-grid-lr-banner" style="[^"]*"/g) ?? [];
    expect(banners).toEqual([`<span class="beat-grid-lr-banner" style="left:${left}px;width:${width}px"`]);
  });

  it("자식 줄이 「└ <그룹> L」「└ <그룹> R」 순서로 그 트랙 줄 바로 아래에 나온다", () => {
    const trackRow = html.indexOf(`class="beat-grid-track-name">${SIDE.group_name}<`);
    const leftRow = html.indexOf(`└ ${SIDE.group_name} L`);
    const rightRow = html.indexOf(`└ ${SIDE.group_name} R`);
    const nextTrack = html.indexOf(`class="beat-grid-track-name">${OTHER.group_name}<`);
    expect(trackRow).toBeGreaterThan(-1);
    expect(trackRow).toBeLessThan(leftRow);
    expect(leftRow).toBeLessThan(rightRow);
    expect(rightRow).toBeLessThan(nextTrack);
    expect(html.match(/└ /g)).toHaveLength(2); // 자식 줄은 이 둘뿐이다
  });

  it("자식 칸은 쪽마다 그 쪽의 color_rgb 로 칠하고 색 이름을 쓴다", () => {
    const children = [
      ...html.matchAll(/<span class="beat-grid-cue beat-grid-cue-split-child" style="([^"]*)"[^>]*>([^<]*)</g),
    ].map((match) => ({ style: match[1], text: match[2] }));
    const split = cueAt(SIDE, SPLIT_BAR)?.split;
    expect(children).toEqual([
      { style: `left:${left}px;width:${width}px;background-color:${hexOf(split?.left.color_rgb)}`, text: "Red" },
      { style: `left:${left}px;width:${width}px;background-color:${hexOf(split?.right.color_rgb)}`, text: "Blue" },
    ]);
  });

  it("나뉜 부모 칸은 그 구간 위에 .beat-grid-cue 버튼으로 그려지지 않는다", () => {
    expect(buttonLefts(html)).not.toContain(px(SPLIT_BAR));
    expect(html).not.toContain(SPLIT_LABEL);
  });

  it("나뉘지 않은 칸은 그대로 그려진다 — 같은 줄의 앞·뒤 칸과 다른 줄의 칸", () => {
    const lefts = buttonLefts(html);
    expect(lefts).toContain(px(0)); // 나뉜 칸 앞
    expect(lefts).toContain(px(NEXT_BAR)); // 나뉜 칸 뒤
    expect(lefts.filter((value) => value === px(0))).toHaveLength(2); // 다른 줄의 0마디 칸도
    for (const cue of [SIDE.cues[0], cueAt(SIDE, NEXT_BAR), OTHER.cues[0]]) {
      expect(html).toContain(`>${cue?.label}<`);
    }
  });

  it("나뉜 칸 쪽 가장자리에는 이음매를 그리지 않는다 — 숨긴 칸을 가리키는 이음매가 없다", () => {
    expect(html).not.toContain("beat-grid-joint");
  });
});

describe("split 이 없으면 예전과 똑같다", () => {
  const html = renderToStaticMarkup(<BeatGrid grid={withoutSplit(GRID)} barCount={26} />);

  it("띠도 자식 줄도 없고 나뉘었던 칸이 보통 막대로 돌아온다", () => {
    expect(html).not.toContain("beat-grid-lr-banner");
    expect(html).not.toContain("beat-grid-cue-split-child");
    expect(html).not.toContain("└ ");
    expect(buttonLefts(html)).toContain(px(SPLIT_BAR));
    expect(html).toContain(`>${SPLIT_LABEL}<`);
  });

  it("칸과 칸 사이 이음매는 예전처럼 그려진다 — 위 「이음매 없음」 단언이 헛돌지 않는다는 대조", () => {
    expect(html.match(/<button type="button" class="beat-grid-joint/g)).toHaveLength(2);
  });
});

describe("계획표 — 칸 색 후보 줄(이름이 줄표)", () => {
  // 서버 `plan_table_markdown` 이 칸 하나의 왼쪽·오른쪽 색 후보에 내는 표 모양(같은 모양을
  // `server/tests/test_beat_grid_cell_split.py` 가 서버 쪽에서 고정한다). 같은 색 둘은 이름·값이 같다.
  const TEXT = [
    "| 만들 프리셋 | 값 | 후보 번호 | 칸 수 | 상태 |",
    "|---|---|---|---|---|",
    "| — | RGB 100 0 0 | 4.11 | 1 | 이 카드 밖 |",
    "| — | RGB 100 0 0 | 4.12 | 1 | 이 카드 밖 |",
    "| — | RGB 미정 | 4.13 | 1 | 미정 |",
    "",
    "**이 카드 밖**",
    "- SIDE-ALL 7마디 왼쪽 칸 RGB 100 0 0(칸 1개, 후보 4.11): 콘솔 이름 미정 — 칸 색 이름은 감독이 정한다",
  ].join("\n");

  it("줄표 이름 줄도 색 줄로 읽는다", () => {
    const plan = parsePresetPlan(TEXT);
    expect(plan?.rows.map((row) => [row.kind, row.name, row.value, row.slot, row.status])).toEqual([
      ["color", "—", "RGB 100 0 0", "4.11", "이 카드 밖"],
      ["color", "—", "RGB 100 0 0", "4.12", "이 카드 밖"],
      ["color", "—", "RGB 미정", "4.13", "미정"],
    ]);
    expect(plan?.rows.some((row) => row.needsSupervisor)).toBe(false);
  });

  it("이름·값이 같은 두 줄이 모두 그려진다", () => {
    const plan = parsePresetPlan(TEXT)!;
    const html = renderToStaticMarkup(<PresetPlanPanel plan={plan} />);
    expect(html.match(/<tr data-kind="color">/g)).toHaveLength(3);
  });
});
