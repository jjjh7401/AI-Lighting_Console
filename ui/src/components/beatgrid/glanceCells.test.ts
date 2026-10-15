// REQ-LDBEAT-023(a)(c)(d) — 「이 마디 한눈에」 표 칼럼(밝기·위치·색·
// 움직임·전환) 칸 값 + 「바뀐 것」 표시 순수 함수 시험. SPEC-LDBEAT-001
// M9 step 2·4(나)·6, 카드 t560 후속.
import { describe, expect, it } from "vitest";

import type { BeatGridCue, BeatGridDrawerSection } from "../../protocol";
import {
  brightnessCell,
  changedFieldsLabel,
  colorCell,
  movementCell,
  positionCell,
  transitionCell,
} from "./glanceCells";

function cue(overrides: Partial<BeatGridCue> = {}): BeatGridCue {
  return {
    bar: 0,
    label: "테스트 칸",
    brightness: { mode: "value", value_percent: 60, preset_no: null },
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

const SECTIONS: BeatGridDrawerSection[] = [
  {
    pool_name: "Dimmer",
    title: "밝기",
    pool_no: 1,
    unread: false,
    bands_confirmed: true,
    entries: [{ preset_no: "1.31", name: "LA Dim 30", usage_count: 2, used_by: [], is_effect_band: false }],
  },
];

describe("brightnessCell", () => {
  it("칸이 없으면(아직 선언 안 됨) 대시다", () => {
    expect(brightnessCell(null, null)).toEqual({ kind: "text", text: "—" });
  });

  it("값 모드면 퍼센트 텍스트다", () => {
    expect(brightnessCell(cue({ brightness: { mode: "value", value_percent: 60, preset_no: null } }), null)).toEqual({
      kind: "text",
      text: "60%",
    });
  });

  it("값 모드인데 값이 미정이면 '미정'이다(지어내지 않음)", () => {
    expect(brightnessCell(cue({ brightness: { mode: "value", value_percent: null, preset_no: null } }), null)).toEqual({
      kind: "text",
      text: "미정",
    });
  });

  it("디머 프리셋 모드면 칩이다(서랍에서 설명·사용 수를 찾는다)", () => {
    const result = brightnessCell(
      cue({ brightness: { mode: "dimmer_preset", value_percent: null, preset_no: "1.31" } }),
      SECTIONS,
    );
    expect(result).toEqual({
      kind: "chip",
      presetNo: "1.31",
      name: "Dim 30",
      label: "1.31 Dim 30",
      tooltip: "이 곡에서 큐 2곳 사용",
    });
  });

  it("디머 프리셋 모드인데 번호가 없으면(비정상 상태) '미정'이다", () => {
    expect(
      brightnessCell(cue({ brightness: { mode: "dimmer_preset", value_percent: null, preset_no: null } }), null),
    ).toEqual({ kind: "text", text: "미정" });
  });
});

describe("positionCell", () => {
  it("역할이 위치를 안 쓰면(예: key) 칸이 있어도 대시다", () => {
    expect(positionCell(cue({ position_preset_no: "2.41" }), "key", null)).toEqual({ kind: "text", text: "—" });
  });

  it("역할이 위치를 쓰면(mover) 번호가 있으면 칩이다", () => {
    expect(positionCell(cue({ position_preset_no: "2.41" }), "mover", null)).toEqual({
      kind: "chip",
      presetNo: "2.41",
      name: null,
      label: "2.41",
      tooltip: "이 곡에서 큐 0곳 사용",
    });
  });

  it("역할이 위치를 쓰는데 번호가 없으면 '미정'이다", () => {
    expect(positionCell(cue({ position_preset_no: null }), "mover", null)).toEqual({ kind: "text", text: "미정" });
  });

  it("칸 자체가 없으면 대시다(역할 적용 여부와 무관)", () => {
    expect(positionCell(null, "mover", null)).toEqual({ kind: "text", text: "—" });
  });
});

describe("colorCell", () => {
  it("무빙 역할은 색을 안 쓴다 — 대시", () => {
    expect(colorCell(cue({ color_preset_no: "4.21" }), "mover", null)).toEqual({ kind: "text", text: "—" });
  });

  it("무빙이 아니면 번호가 있으면 칩이다", () => {
    expect(colorCell(cue({ color_preset_no: "4.21" }), "side", null)).toEqual({
      kind: "chip",
      presetNo: "4.21",
      name: null,
      label: "4.21",
      tooltip: "이 곡에서 큐 0곳 사용",
    });
  });
});

describe("movementCell", () => {
  it("무빙이 아니면 대시다", () => {
    expect(movementCell(cue({ effect_preset_no: "2.61" }), "back", null)).toEqual({ kind: "text", text: "—" });
  });

  it("무빙이면 효과 번호가 있으면 칩이다", () => {
    expect(movementCell(cue({ effect_preset_no: "2.61" }), "mover", null)).toEqual({
      kind: "chip",
      presetNo: "2.61",
      name: null,
      label: "2.61",
      tooltip: "이 곡에서 큐 0곳 사용",
    });
  });

  it("무빙인데 효과 번호가 없으면 '+ 없음'이다", () => {
    expect(movementCell(cue({ effect_preset_no: null }), "mover", null)).toEqual({ kind: "text", text: "+ 없음" });
  });
});

describe("transitionCell", () => {
  it("칸이 없으면 대시다", () => {
    expect(transitionCell(null, false)).toEqual({ kind: "text", text: "—" });
  });

  it("전환 마디가 아니면(칸 중간) '유지'다", () => {
    expect(transitionCell(cue({ entry: { fade_bars: 2, mib_mode: null } }), false)).toEqual({
      kind: "text",
      text: "유지",
      dim: true,
    });
  });

  it("전환 마디면 들어올 때 마디 수를 보여준다", () => {
    expect(transitionCell(cue({ entry: { fade_bars: 2, mib_mode: null } }), true)).toEqual({
      kind: "text",
      text: "2마디",
    });
  });

  it("전환 마디인데 들어올 때가 미정이면 '미정'이다", () => {
    expect(transitionCell(cue({ entry: { fade_bars: null, mib_mode: null } }), true)).toEqual({
      kind: "text",
      text: "미정",
    });
  });
});

describe("changedFieldsLabel — mockup changedTxt와 같은 「바뀐 것」 표시(derivable한 것만)", () => {
  it("곡 표시 범위 첫 마디에서는 항상 빈 문자열이다(비교할 '이전'이 없음)", () => {
    const current = cue();
    expect(changedFieldsLabel(null, current, true)).toBe("");
  });

  it("칸이 아예 없으면 빈 문자열이다", () => {
    expect(changedFieldsLabel(null, null, false)).toBe("");
  });

  it("이전 칸이 없고(트랙이 여기서 처음 시작) 칸이 있으면 '여기서 시작'이다", () => {
    expect(changedFieldsLabel(null, cue(), false)).toBe("● 여기서 시작");
  });

  it("같은 칸이 이어지면(칸 중간) 빈 문자열이다", () => {
    const same = cue();
    expect(changedFieldsLabel(same, same, false)).toBe("");
  });

  it("칸이 바뀌면 바뀐 필드 이름을 나열한다", () => {
    const previous = cue({ brightness: { mode: "value", value_percent: 30, preset_no: null } });
    const current = cue({ brightness: { mode: "value", value_percent: 70, preset_no: null }, color_preset_no: "4.24" });
    expect(changedFieldsLabel(previous, current, false)).toBe("● 밝기·색 바뀜");
  });

  it("비교해도 구조화 필드 전부 같으면(label만 다름 등) '큐 바뀜'으로 떨어진다", () => {
    const previous = cue({ label: "이전" });
    const current = cue({ label: "다음" });
    expect(changedFieldsLabel(previous, current, false)).toBe("● 큐 바뀜");
  });
});
