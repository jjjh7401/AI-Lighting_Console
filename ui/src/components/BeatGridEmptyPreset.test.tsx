// 카드 t595(REQ-LDBEAT-015(i-1) 「그 칸에 표시」) — 서버 `empty_preset_cells`를
// 격자 칸 배지와 편집 칸 안내로 그대로 옮기는지. 판정은 서버 몫이라 여기서는
// 목록 → 글자만 잰다(이 프로젝트는 jsdom 이 없다 — `renderToStaticMarkup`).
import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

import {
  BeatGrid,
  emptyPresetBadge,
  emptyPresetCellIndex,
  emptyPresetFieldNote,
  emptyPresetTitle,
} from "./BeatGrid";
import type { BeatGridCue, BeatGridEmptyPresetCell, BeatGridView } from "../protocol";

const HOLD = "빈 프리셋 — 아직 콘솔에 만들 길 없음";
const UNREAD = "풀을 못 읽어 빈 프리셋인지 확인 못 함";

function cue(bar: number, overrides: Partial<BeatGridCue> = {}): BeatGridCue {
  return {
    bar,
    label: `칸${bar}`,
    brightness: { mode: "value", value_percent: 100, preset_no: null },
    position_preset_no: null,
    color_preset_no: null,
    effect_preset_no: null,
    effect_kind: null,
    entry: { fade_bars: null, mib_mode: null },
    source_ref: null,
    app_movement: null,
    evidence: null,
    ...overrides,
  } as BeatGridCue;
}

const HELD: BeatGridEmptyPresetCell = {
  group_name: "BACK",
  bar: 1,
  held: true,
  fields: [
    { field: "effect_preset_no", field_label: "효과 프리셋", value: "4.99", kind: "empty", reason: HOLD },
  ],
};

const APPROVED: BeatGridEmptyPresetCell = {
  group_name: "BACK",
  bar: 2,
  held: false,
  fields: [
    { field: "color_preset_no", field_label: "색 프리셋", value: "4.98", kind: "empty", reason: HOLD },
    { field: "position_preset_no", field_label: "위치 프리셋", value: "2.7", kind: "pool_unread", reason: UNREAD },
  ],
};

describe("emptyPresetBadge / emptyPresetTitle", () => {
  it("빈 번호를 배지에 담고, 못 읽은 풀의 번호엔 ? 를 붙인다", () => {
    expect(emptyPresetBadge(HELD)).toBe("⚠ 빈 프리셋(4.99)");
    expect(emptyPresetBadge(APPROVED)).toBe("⚠ 빈 프리셋(4.98, 2.7?)");
  });

  it("보류 칸과 이미 승인된 칸의 결과를 가른다", () => {
    expect(emptyPresetTitle(HELD)).toContain("송신 보류");
    expect(emptyPresetTitle(APPROVED)).toContain("그대로 나갑니다");
    expect(emptyPresetTitle(APPROVED)).toContain(UNREAD);
  });
});

describe("emptyPresetFieldNote — 편집 칸 행", () => {
  it("그 행의 필드만 안내한다", () => {
    expect(emptyPresetFieldNote(APPROVED, "색 프리셋")).toContain("4.98");
    expect(emptyPresetFieldNote(APPROVED, "위치 프리셋")).toContain(UNREAD);
    expect(emptyPresetFieldNote(APPROVED, "효과 프리셋")).toBeNull();
    expect(emptyPresetFieldNote(APPROVED, "밝기")).toBeNull();
  });

  it("칸 표식이 없으면 안내 없음", () => {
    expect(emptyPresetFieldNote(undefined, "색 프리셋")).toBeNull();
  });
});

describe("emptyPresetCellIndex", () => {
  it("옛 서버 응답(필드 없음)은 빈 지도", () => {
    expect(emptyPresetCellIndex(undefined).size).toBe(0);
  });
});

describe("BeatGrid 격자 칸 — 서버 목록 그대로 배지", () => {
  function grid(cells: BeatGridEmptyPresetCell[] | undefined): BeatGridView {
    return {
      song_title: "T595",
      bar_range: { start: 0, end: 8 },
      source: "custom",
      note: null,
      scene_memos: [],
      probe_results: {},
      unsent_cells: null,
      tracks: [
        {
          group_no: 7,
          group_no_confirmed: true,
          group_name: "BACK",
          layer_role: "back",
          cues: [
            cue(1, { effect_preset_no: "4.99" }),
            cue(2, { color_preset_no: "4.98" }),
            cue(3, { effect_preset_no: "4.21" }),
          ],
        },
      ],
      empty_preset_cells: cells,
    };
  }

  it("목록에 있는 칸에만 배지가 붙는다", () => {
    const html = renderToStaticMarkup(<BeatGrid grid={grid([HELD, APPROVED])} />);
    expect(html).toContain("⚠ 빈 프리셋(4.99)");
    expect(html).toContain("⚠ 빈 프리셋(4.98, 2.7?)");
    expect(html.match(/beat-grid-empty-preset-warn/g)?.length).toBe(2);
  });

  it("목록이 없으면(옛 서버) 번호만 보고 배지를 지어내지 않는다", () => {
    const html = renderToStaticMarkup(<BeatGrid grid={grid(undefined)} />);
    expect(html).not.toContain("빈 프리셋");
  });
});
