// 개념도 무대(좌표 미제공)의 무빙 빔도 재생 시각에 맞춰 돈다 — 실서버(47010)에서 무대가 개념도였고
// 빔이 고정 삼각형이라 0.5초 간격 캡처가 바이트 동일했다(리드 실측 2026-10-16).
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { BeatGridCue, BeatGridTrack } from "../../protocol";
import { StageConceptSvg } from "./StageConceptSvg";

const waveCue = {
  bar: 4,
  label: "팬 웨이브(한 바퀴 2마디)",
  effect_preset_no: "21.10",
  position_preset_no: "2.33",
  app_movement: null,
} as unknown as BeatGridCue;
const tracks = [
  { group_name: "MOVER-U", layer_role: "mover", cues: [waveCue] },
  { group_name: "MOVER-D", layer_role: "mover", cues: [{ bar: 4, label: "정지", app_movement: null } as unknown as BeatGridCue] },
] as unknown as BeatGridTrack[];
const book = {
  labels: { "21.10": "WAVE PAN 2 BAR", "2.33": "CENTER MOVER-U" },
  movements: { "21.10": { group_no: 11, signature: ["wave", ["Pan"], "bar", 2, false] } },
};

function beams(seconds: number | null): string[] {
  const html = renderToStaticMarkup(
    <StageConceptSvg
      width={700}
      height={300}
      tracks={tracks}
      viewBar={5}
      presetBook={book}
      motion={seconds === null ? undefined : { seconds, secondsPerBar: 2.1428, beatsPerBar: 4 }}
    />,
  );
  return [...html.matchAll(/<polygon class="beat-grid-stage-beam" points="([^"]+)"/g)].map((m) => m[1]);
}

describe("StageConceptSvg — 무빙 빔 움직임", () => {
  it("U·D 줄 무빙마다 빔이 있다(켜진 줄)", () => {
    expect(beams(12.8)).toHaveLength(16);
  });
  it("웨이브 칸(U)은 0.5초 뒤 빔이 달라지고, 정지 칸(D)은 그대로다", () => {
    const a = beams(12.8);
    const b = beams(13.3);
    expect(a.slice(0, 8)).not.toEqual(b.slice(0, 8));
    expect(a.slice(8)).toEqual(b.slice(8));
  });
  it("재생 시계가 없으면 움직이지 않는다", () => {
    expect(beams(null)).toEqual(beams(null));
  });
});
