// 접힌 역할 폴더의 한 줄 요약(시안 「n/m줄 켜짐 · 바뀌는 경계」). 폴더 안 어느 줄이든
// 칸이 시작하는 마디가 경계이고, 경계마다 한 칸을 둔다. 그 칸의 글은 "켜진 줄 수/전체 줄 수
// 줄 켜짐"이다. 값은 칸 데이터에서만 세고, 칸이 없는 줄은 꺼진 것으로 본다(지어내지 않는다).
import type { BeatGridCue, BeatGridTrack } from "../../protocol";

export interface FolderSummarySpan {
  startBar: number;
  /** 배타적 — 다음 경계(또는 축 끝). */
  endBar: number;
  /** 그 마디에 켜진(글이 있고 「—」가 아닌) 칸이 있는 줄 수. */
  lit: number;
  /** 폴더의 전체 줄 수. */
  total: number;
}

/** 칸이 켜져 있는지 — `BeatGrid` 의 `cueIsActive` 와 같은 기준(빈 글·「—」는 꺼짐). */
function cueLit(cue: BeatGridCue | undefined): boolean {
  if (!cue) return false;
  const label = cue.label.trim();
  return label !== "" && label !== "—";
}

/** 그 마디에 걸린 칸 — 마디 이하에서 가장 늦게 시작한 칸(없으면 `undefined`). */
function cueAtBar(track: BeatGridTrack, bar: number): BeatGridCue | undefined {
  let found: BeatGridCue | undefined;
  for (const cue of track.cues) {
    if (cue.bar <= bar && (found === undefined || cue.bar >= found.bar)) found = cue;
  }
  return found;
}

/** 접힌 폴더의 요약 칸 자리. `endBar` 는 축 끝(배타). 칸이 하나도 없으면 빈 배열. */
export function folderSummarySpans(tracks: readonly BeatGridTrack[], endBar: number): FolderSummarySpan[] {
  const bounds = [...new Set(tracks.flatMap((track) => track.cues.map((cue) => cue.bar)))]
    .filter((bar) => bar < endBar)
    .sort((a, b) => a - b);
  return bounds.map((startBar, index) => ({
    startBar,
    endBar: bounds[index + 1] ?? endBar,
    lit: tracks.filter((track) => cueLit(cueAtBar(track, startBar))).length,
    total: tracks.length,
  }));
}
