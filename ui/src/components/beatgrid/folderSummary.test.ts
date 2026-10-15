// 접힌 폴더 요약 칸 시험 — 경계마다 한 칸을 두고, 켜진 줄 수를 칸 데이터에서만 센다.
import { describe, expect, it } from "vitest";

import type { BeatGridCue, BeatGridTrack } from "../../protocol";
import { folderSummarySpans } from "./folderSummary";

const cue = (bar: number, label: string) => ({ bar, label }) as BeatGridCue;
const track = (...cues: BeatGridCue[]) => ({ cues }) as BeatGridTrack;

describe("folderSummarySpans — 경계마다 n/m줄 켜짐 칸", () => {
  it("경계는 폴더 안 어느 줄이든 칸이 시작하는 마디이고, 칸마다 켜진 줄을 센다", () => {
    const a = track(cue(0, "앞박"), cue(4, "—"));
    const b = track(cue(0, "—"), cue(2, "킥"));
    expect(folderSummarySpans([a, b], 8)).toEqual([
      { startBar: 0, endBar: 2, lit: 1, total: 2 },
      { startBar: 2, endBar: 4, lit: 2, total: 2 },
      { startBar: 4, endBar: 8, lit: 1, total: 2 },
    ]);
  });

  it("칸이 하나도 없으면 빈 배열이다(지어내지 않는다)", () => {
    expect(folderSummarySpans([track()], 8)).toEqual([]);
  });

  it("축 끝을 넘는 경계는 버린다", () => {
    const a = track(cue(0, "앞박"), cue(9, "킥"));
    expect(folderSummarySpans([a], 8)).toEqual([{ startBar: 0, endBar: 8, lit: 1, total: 1 }]);
  });
});
