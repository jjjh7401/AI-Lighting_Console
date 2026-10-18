// 칸 단위 반영 — 화면이 정하는 것들의 순수 함수 시험(카드 WT-cell-apply): 보낼 칸 판정, 결과 요약, 칸별 표시.
import { describe, expect, it } from "vitest";

import type { BeatGridSubsetStatus } from "../../protocol";
import {
  CUE_SYNC_APP_ONLY_LABEL,
  CUE_SYNC_IN_SYNC_LABEL,
  PARTIAL_NOTHING_CHANGED_HINT,
  PARTIAL_NOTHING_PICKED_HINT,
  PARTIAL_NO_RECORD_HINT,
  PARTIAL_PICKED_NOTHING_CHANGED_HINT,
  PARTIAL_RECORD_WARNING,
  SUBSET_RECORD_BASELINE_NOTE,
  cueSyncMark,
  partialApplyPlan,
  subsetSummary,
  unsentKeySet,
} from "./cellApply";
import { CELL_WIRE_MAX, type CueCell } from "./cellSelection";

const cellOf = (group_name: string, bar: number): CueCell => ({ group_name, bar });

describe("partialApplyPlan — 「⇪ 콘솔에 반영」이 보낼 칸", () => {
  describe("기준이 없을 때(partial_baseline 이 null/undefined)", () => {
    it("막고 「전체 다시 반영」을 먼저 누르라고 말한다 — 이 안내는 이때만 나온다", () => {
      for (const baseline of [null, undefined]) {
        for (const unsent of [null, undefined, [], [cellOf("A", 1)]]) {
          const plan = partialApplyPlan(unsent, [cellOf("A", 1)], baseline);
          expect(plan).toEqual({ kind: "blocked", reason: PARTIAL_NO_RECORD_HINT, why: "no-record" });
        }
      }
      expect(PARTIAL_NO_RECORD_HINT).toBe("이 곡은 아직 반영 기록이 없어요 — 「전체 다시 반영」을 먼저 누르세요");
    });

    it("다른 기준의 막힘 이유는 그 안내를 담지 않는다", () => {
      const others = [
        partialApplyPlan([], [], "snapshot"),
        partialApplyPlan([cellOf("A", 1)], [cellOf("B", 2)], "snapshot"),
        partialApplyPlan(null, [], "record"),
      ];
      for (const plan of others) {
        expect(plan.kind === "blocked" && plan.reason).not.toContain("아직 반영 기록이 없어요");
      }
    });
  });

  describe("칸 기록 기준(snapshot) — 바뀐 칸만", () => {
    it("기준은 snapshot 인데 unsent 가 목록이 아니면(어긋난 응답) 기준 없음과 같이 막는다", () => {
      expect(partialApplyPlan(null, [], "snapshot")).toEqual({
        kind: "blocked",
        reason: PARTIAL_NO_RECORD_HINT,
        why: "no-record",
      });
      expect(partialApplyPlan(undefined, [cellOf("A", 1)], "snapshot").kind).toBe("blocked");
    });

    it("바뀐 칸이 없으면(빈 배열) 「바뀐 칸이 없어요」로 막는다", () => {
      const plan = partialApplyPlan([], [], "snapshot");
      expect(plan).toEqual({ kind: "blocked", reason: PARTIAL_NOTHING_CHANGED_HINT, why: "nothing-changed" });
      expect(PARTIAL_NOTHING_CHANGED_HINT).toBe("바뀐 칸이 없어요");
    });

    it("고른 칸이 없으면 바뀐 칸 전부를 unsent 순서대로 보낸다", () => {
      const plan = partialApplyPlan([cellOf("BACK", 3), cellOf("FOH", 1), cellOf("BACK", 7)], [], "snapshot");
      expect(plan).toEqual({
        kind: "ready",
        cells: [
          ["BACK", 3],
          ["FOH", 1],
          ["BACK", 7],
        ],
        note: "바뀐 3칸만 보내요",
      });
    });

    it("고른 칸이 있으면 그 가운데 바뀐 칸만 — 안 바뀐 칸과 고르지 않은 칸은 빠진다", () => {
      const unsent = [cellOf("A", 1), cellOf("C", 3), cellOf("D", 4)];
      const picks = [cellOf("C", 3), cellOf("B", 2), cellOf("A", 1)]; // B@2 는 안 바뀜, D@4 는 안 골랐다
      const plan = partialApplyPlan(unsent, picks, "snapshot");
      expect(plan).toEqual({
        kind: "ready",
        cells: [
          ["C", 3],
          ["A", 1],
        ],
        note: "고른 3칸 중 바뀐 2칸만 보내요",
      });
    });

    it("고른 칸 가운데 바뀐 칸이 하나도 없으면 막고, 그 사실을 고른 칸 기준으로 말한다", () => {
      const plan = partialApplyPlan([cellOf("A", 1)], [cellOf("B", 2)], "snapshot");
      expect(plan).toEqual({ kind: "blocked", reason: PARTIAL_PICKED_NOTHING_CHANGED_HINT, why: "nothing-changed" });
      // 「바뀐 칸이 없어요」를 그대로 품는다 — 어느 쪽이든 같은 말로 읽힌다.
      expect(PARTIAL_PICKED_NOTHING_CHANGED_HINT).toContain(PARTIAL_NOTHING_CHANGED_HINT);
    });

    it("같은 칸을 두 번 골라 둬도 한 번만 센다", () => {
      const plan = partialApplyPlan([cellOf("A", 1)], [cellOf("A", 1), cellOf("A", 1)], "snapshot");
      expect(plan.kind === "ready" && plan.cells).toEqual([["A", 1]]);
    });

    it("서버가 받지 못하는 0마디(앞박) 칸은 빼고 그 사실을 말한다", () => {
      const plan = partialApplyPlan([cellOf("A", 0), cellOf("A", 2)], [], "snapshot");
      expect(plan.kind).toBe("ready");
      if (plan.kind !== "ready") return;
      expect(plan.cells).toEqual([["A", 2]]);
      expect(plan.note).toBe("바뀐 1칸만 보내요 · 0마디(앞박) 칸 1개는 칸 단위로 보낼 수 없어요");
    });

    it("바뀐 칸이 전부 0마디면 막고 전체 반영으로 안내한다", () => {
      const plan = partialApplyPlan([cellOf("A", 0)], [], "snapshot");
      expect(plan).toMatchObject({ kind: "blocked", why: "bar-zero" });
      expect(plan.kind === "blocked" && plan.reason).toContain("「전체 다시 반영」");
    });

    it("한 번에 보낼 수 있는 상한(400)까지는 보내고, 넘으면 막는다", () => {
      const many = (count: number) => Array.from({ length: count }, (_, index) => cellOf("A", index + 1));
      expect(partialApplyPlan(many(CELL_WIRE_MAX), [], "snapshot").kind).toBe("ready");
      const over = partialApplyPlan(many(CELL_WIRE_MAX + 1), [], "snapshot");
      expect(over).toMatchObject({ kind: "blocked", why: "too-many" });
      expect(over.kind === "blocked" && over.reason).toContain(String(CELL_WIRE_MAX));
    });

    it("받은 목록은 고치지 않는다", () => {
      const unsent = [cellOf("A", 1)];
      const picks = [cellOf("A", 1)];
      partialApplyPlan(unsent, picks, "snapshot");
      expect(unsent).toEqual([cellOf("A", 1)]);
      expect(picks).toEqual([cellOf("A", 1)]);
    });
  });

  describe("기록 기준(record) — 고른 칸 모두", () => {
    it("고른 칸이 없으면 막고, 바뀐 칸을 알 수 없으니 먼저 고르라고 말한다", () => {
      for (const unsent of [null, undefined, [], [cellOf("A", 1)]]) {
        expect(partialApplyPlan(unsent, [], "record")).toEqual({
          kind: "blocked",
          reason: PARTIAL_NOTHING_PICKED_HINT,
          why: "nothing-picked",
        });
      }
      expect(PARTIAL_NOTHING_PICKED_HINT).toBe("고른 칸을 먼저 골라 주세요 — 기록 기준이라 바뀐 칸을 알 수 없어요");
    });

    it("고른 칸을 모두 보낸다 — unsent 로 거르지 않는다(unsent 는 null 이어도, 목록이어도 같다)", () => {
      const picks = [cellOf("BACK", 3), cellOf("FOH", 1), cellOf("SIDE", 9)];
      const expected = {
        kind: "ready",
        cells: [
          ["BACK", 3],
          ["FOH", 1],
          ["SIDE", 9],
        ],
        note: "고른 3칸을 보내요 (기록 기준) · 지운 값은 콘솔에 남을 수 있어요 — 지운 칸은 「전체 다시 반영」으로",
      };
      expect(partialApplyPlan(null, picks, "record")).toEqual(expected);
      expect(partialApplyPlan(undefined, picks, "record")).toEqual(expected);
      // 서버가 어긋나게 목록을 줘도 거르지 않는다(바뀐 칸에 없는 FOH·SIDE 칸도 간다).
      expect(partialApplyPlan([cellOf("BACK", 3)], picks, "record")).toEqual(expected);
    });

    it("안내는 지운 값이 콘솔에 남을 수 있다고 말한다", () => {
      const plan = partialApplyPlan(null, [cellOf("A", 1)], "record");
      expect(plan.kind === "ready" && plan.note).toContain(PARTIAL_RECORD_WARNING);
      expect(PARTIAL_RECORD_WARNING).toBe("지운 값은 콘솔에 남을 수 있어요 — 지운 칸은 「전체 다시 반영」으로");
    });

    it("같은 칸을 두 번 골라 둬도 한 번만 보낸다", () => {
      const plan = partialApplyPlan(null, [cellOf("A", 1), cellOf("A", 1)], "record");
      expect(plan.kind === "ready" && plan.cells).toEqual([["A", 1]]);
      expect(plan.kind === "ready" && plan.note).toContain("고른 1칸을 보내요 (기록 기준)");
    });

    it("0마디(앞박) 칸은 서버가 못 받아 빼고, 고른 칸 수와 보내는 칸 수를 둘 다 말한다", () => {
      const plan = partialApplyPlan(null, [cellOf("A", 0), cellOf("A", 2), cellOf("B", 3)], "record");
      expect(plan.kind).toBe("ready");
      if (plan.kind !== "ready") return;
      expect(plan.cells).toEqual([
        ["A", 2],
        ["B", 3],
      ]);
      expect(plan.note).toBe(
        "고른 3칸 중 2칸을 보내요 (기록 기준) · 지운 값은 콘솔에 남을 수 있어요 — 지운 칸은 「전체 다시 반영」으로 · 0마디(앞박) 칸 1개는 칸 단위로 보낼 수 없어요",
      );
    });

    it("고른 칸이 전부 0마디면 칸 목록이 비므로 막는다 — 빈 cells 가 전체 반영으로 새지 않는다", () => {
      const plan = partialApplyPlan(null, [cellOf("A", 0)], "record");
      expect(plan).toMatchObject({ kind: "blocked", why: "bar-zero" });
    });

    it("한 번에 보낼 수 있는 상한(400)까지는 보내고, 넘으면 막는다", () => {
      const many = (count: number) => Array.from({ length: count }, (_, index) => cellOf("A", index + 1));
      expect(partialApplyPlan(null, many(CELL_WIRE_MAX), "record").kind).toBe("ready");
      expect(partialApplyPlan(null, many(CELL_WIRE_MAX + 1), "record")).toMatchObject({
        kind: "blocked",
        why: "too-many",
      });
    });

    it("받은 목록은 고치지 않는다", () => {
      const picks = [cellOf("A", 1), cellOf("A", 1)];
      partialApplyPlan(null, picks, "record");
      expect(picks).toEqual([cellOf("A", 1), cellOf("A", 1)]);
    });
  });
});

describe("subsetSummary — 칸 단위 반영 결과 한 줄", () => {
  const subset = (overrides: Partial<BeatGridSubsetStatus> = {}): BeatGridSubsetStatus => ({
    requested: 3,
    applied: [
      ["BACK", 1],
      ["FOH", 3],
    ],
    not_applied: [{ group_name: "BACK", bar: 2, reason: "콘솔과 같음" }],
    ...overrides,
  });

  it("보낸 칸이 없거나 subset 이 없으면 요약하지 않는다", () => {
    expect(subsetSummary(undefined)).toBeNull();
    expect(subsetSummary(null)).toBeNull();
    expect(subsetSummary(subset({ applied: [] }))).toBeNull();
  });

  it("「N칸 반영 · 못 보낸 칸 M개」에 사유를 잇는다", () => {
    const summary = subsetSummary(subset());
    expect(summary?.text).toBe("2칸 반영 · 못 보낸 칸 1개 — 콘솔과 같음");
  });

  it("못 보낸 칸이 없으면 사유 없이 0개라고 말한다", () => {
    expect(subsetSummary(subset({ not_applied: [] }))?.text).toBe("2칸 반영 · 못 보낸 칸 0개");
  });

  it("사유는 처음 셋까지 — 같은 말은 한 번만 보이고, 더 있으면 …", () => {
    const skipped = ["콘솔과 같음", "콘솔과 같음", "승인 대기 프리셋", "지운 항목", "막힌 칸"].map((reason, index) => ({
      group_name: "BACK",
      bar: index + 10,
      reason,
    }));
    const summary = subsetSummary(subset({ not_applied: skipped }));
    expect(summary?.text).toBe("2칸 반영 · 못 보낸 칸 5개 — 콘솔과 같음 · 승인 대기 프리셋 · 지운 항목 …");
    // 사유가 셋 이하면 …이 없다.
    const few = subsetSummary(subset({ not_applied: skipped.slice(0, 3) }));
    expect(few?.text).toBe("2칸 반영 · 못 보낸 칸 3개 — 콘솔과 같음 · 승인 대기 프리셋");
  });

  it("title 에는 반영한 칸과 못 보낸 칸이 칸마다 전부 있다", () => {
    const skipped = [
      { group_name: "BACK", bar: 2, reason: "콘솔과 같음" },
      { group_name: "SIDE", bar: 5, reason: "막힌 칸" },
    ];
    const summary = subsetSummary(subset({ not_applied: skipped }));
    expect(summary?.title.split("\n")).toEqual([
      "고른 3칸 중 2칸 반영",
      "반영한 칸: BACK 1마디, FOH 3마디",
      "못 보낸 칸: BACK 2마디 — 콘솔과 같음",
      "못 보낸 칸: SIDE 5마디 — 막힌 칸",
    ]);
  });

  it("기록 기준(baseline record)으로 보냈으면 요약 끝에 그 사실을 붙인다 — 지운 값은 확인 못 했다", () => {
    const withSkips = subsetSummary(subset({ baseline: "record" }));
    expect(withSkips?.text).toBe(
      "2칸 반영 · 못 보낸 칸 1개 — 콘솔과 같음 · 기록 기준으로 보냄(지운 값은 확인 못 함)",
    );
    const noSkips = subsetSummary(subset({ baseline: "record", not_applied: [] }));
    expect(noSkips?.text).toBe("2칸 반영 · 못 보낸 칸 0개 · 기록 기준으로 보냄(지운 값은 확인 못 함)");
    expect(SUBSET_RECORD_BASELINE_NOTE).toBe("기록 기준으로 보냄(지운 값은 확인 못 함)");
  });

  it("칸 기록 기준(snapshot)이나 기준을 안 실은 옛 응답에는 그 말이 없다", () => {
    expect(subsetSummary(subset({ baseline: "snapshot" }))?.text).toBe("2칸 반영 · 못 보낸 칸 1개 — 콘솔과 같음");
    expect(subsetSummary(subset())?.text).toBe("2칸 반영 · 못 보낸 칸 1개 — 콘솔과 같음");
  });

  it("기록 기준이어도 title 의 칸 목록은 그대로다", () => {
    const plain = subsetSummary(subset())?.title;
    expect(subsetSummary(subset({ baseline: "record" }))?.title).toBe(plain);
  });

  it("보낸 첫 칸의 마디를 알려 준다 — 콘솔에서 그 마디를 보러 간다", () => {
    expect(subsetSummary(subset())?.firstBar).toBe(1);
    expect(subsetSummary(subset({ applied: [["FOH", 9], ["BACK", 2]] }))?.firstBar).toBe(9);
  });
});

describe("cueSyncMark — 칸마다 콘솔과 같은지", () => {
  it("unsent_cells 가 null 이거나 없으면 표시가 없다", () => {
    expect(unsentKeySet(null)).toBeNull();
    expect(unsentKeySet(undefined)).toBeNull();
    expect(cueSyncMark(unsentKeySet(null), cellOf("BACK", 3))).toBeNull();
    expect(cueSyncMark(unsentKeySet(undefined), cellOf("BACK", 3))).toBeNull();
  });

  it("배열에 있는 칸은 「앱에서만 바뀜」이다", () => {
    const keys = unsentKeySet([cellOf("BACK", 3), cellOf("FOH", 1)]);
    expect(cueSyncMark(keys, cellOf("BACK", 3))).toEqual({
      kind: "app-only",
      glyph: "✎",
      label: "앱에서만 바뀜",
    });
    expect(CUE_SYNC_APP_ONLY_LABEL).toBe("앱에서만 바뀜");
  });

  it("배열은 있는데 그 칸이 없으면 「콘솔과 같음」이다 — 줄과 마디가 둘 다 맞아야 든 칸이다", () => {
    const keys = unsentKeySet([cellOf("BACK", 3)]);
    expect(cueSyncMark(keys, cellOf("BACK", 4))).toEqual({ kind: "in-sync", glyph: "✓", label: "콘솔과 같음" });
    expect(cueSyncMark(keys, cellOf("FOH", 3))?.kind).toBe("in-sync");
    expect(CUE_SYNC_IN_SYNC_LABEL).toBe("콘솔과 같음");
  });

  it("빈 배열(기록은 있고 바뀐 칸이 없음)이면 모든 칸이 콘솔과 같다", () => {
    expect(cueSyncMark(unsentKeySet([]), cellOf("BACK", 3))?.kind).toBe("in-sync");
  });

  it("글자와 기호가 늘 함께 있어 색에만 기대지 않는다", () => {
    const keys = unsentKeySet([cellOf("BACK", 3)]);
    for (const cell of [cellOf("BACK", 3), cellOf("BACK", 4)]) {
      const mark = cueSyncMark(keys, cell);
      expect(mark?.glyph.length).toBeGreaterThan(0);
      expect(mark?.label.length).toBeGreaterThan(0);
    }
  });
});
