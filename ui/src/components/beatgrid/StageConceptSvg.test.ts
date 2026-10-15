// 무대 개념도 자리 배정 시험 — 리드 결정: 무빙 첫 줄 = 위(U), 둘째 줄 = 아래(D), 이름 규칙 없음.
import { describe, expect, it } from "vitest";

import type { BeatGridCue, BeatGridTrack } from "../../protocol";
import { type ConceptSlot, type ConceptSlotState, conceptSlots } from "./StageConceptSvg";

function cueAt(bar: number, label: string, colorRgb?: [number, number, number]): BeatGridCue {
  return { bar, label, ...(colorRgb ? { color_rgb: colorRgb } : {}) } as unknown as BeatGridCue;
}

function track(groupName: string, layerRole: string, label: string, colorRgb?: [number, number, number]): BeatGridTrack {
  return { group_name: groupName, layer_role: layerRole, cues: [cueAt(0, label, colorRgb)] } as unknown as BeatGridTrack;
}

function slot(slots: readonly ConceptSlotState[], name: ConceptSlot): ConceptSlotState {
  return slots.find((s) => s.slot === name)!;
}

describe("conceptSlots — 무대 개념도 자리마다 맡는 줄(리드 결정)", () => {
  it("무빙 줄의 첫째는 위(U), 둘째는 아래(D)다 — 이름과 무관", () => {
    const slots = conceptSlots([track("MOVER-B", "mover", "앞박 1회"), track("MOVER-A", "mover", "—")], 0);
    expect(slot(slots, "u")).toMatchObject({ trackIndex: 0, lit: true });
    expect(slot(slots, "d")).toMatchObject({ trackIndex: 1, lit: false });
  });

  it("측면 줄이 하나면 SIDE-L·SIDE-R 양쪽이 그 줄을 따른다", () => {
    const slots = conceptSlots([track("SIDE-ALL", "side", "앞박 1회")], 0);
    expect(slot(slots, "side-l").trackIndex).toBe(0);
    expect(slot(slots, "side-r").trackIndex).toBe(0);
  });

  it("무빙이 아닌 효과(effect) 줄의 첫째는 블라인드(사각) 자리다", () => {
    const slots = conceptSlots([track("STROBE", "effect", "앞박 1회")], 0);
    expect(slot(slots, "blind").trackIndex).toBe(0);
  });

  it("켜진 줄은 칸 색을 쓰고, 칸 색이 없으면 줄 기본색(팔레트)을 쓴다", () => {
    const slots = conceptSlots([track("BACK", "back", "앞박 1회", [100, 0, 50])], 0);
    expect(slot(slots, "back").color).toBe("rgb(255, 0, 128)");
    const plain = conceptSlots([track("FOH", "key", "앞박 1회")], 0);
    expect(slot(plain, "foh").color).toBe("#4f8cff");
  });

  it("꺼진 줄은 어두운 회색(#333)이다", () => {
    const slots = conceptSlots([track("WASH", "wash", "—", [100, 0, 0])], 0);
    expect(slot(slots, "wash")).toMatchObject({ lit: false, color: "#333" });
  });

  it("줄이 하나도 없으면 모든 자리가 맡는 줄 없음·꺼진 회색이다", () => {
    const slots = conceptSlots([], 0);
    expect(slots.every((s) => s.trackIndex === null && !s.lit && s.color === "#333")).toBe(true);
  });
});
