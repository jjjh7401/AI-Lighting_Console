// 카드 t534 — M1 프로브 실측 상수가 progress.md 표와 같은 모양인지 확인.
import { describe, expect, it } from "vitest";

import { buildProbeStatusTable, isWriteLocked } from "./BeatGrid";
import { M1_PROBE_RESULTS_T531 } from "./beatGridM1Probes";

describe("M1_PROBE_RESULTS_T531 — progress.md M1 표(커밋 46283183)", () => {
  it("9항목 모두 기록돼 있다", () => {
    expect(Object.keys(M1_PROBE_RESULTS_T531)).toHaveLength(9);
  });

  it("9항목 모두 같은 값 — 표가 전부 같은 모양이라서다(지어낸 차이 없음)", () => {
    const values = Object.values(M1_PROBE_RESULTS_T531);
    expect(new Set(values).size).toBe(1);
    expect(values[0]).toBe("리허설PASS·실기미실행");
  });

  it("buildProbeStatusTable 에 꽂아도 9행 모두 이 상태로 뜬다", () => {
    const probes = buildProbeStatusTable(M1_PROBE_RESULTS_T531);
    expect(probes).toHaveLength(9);
    expect(probes.every((p) => p.status === "리허설PASS·실기미실행")).toBe(true);
  });

  it("리허설만 통과했을 뿐 실기 실행은 미실행이므로 쓰기는 여전히 잠긴다", () => {
    const probes = buildProbeStatusTable(M1_PROBE_RESULTS_T531);
    expect(isWriteLocked(probes)).toBe(true);
  });
});
