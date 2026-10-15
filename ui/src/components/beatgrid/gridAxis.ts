// 격자 축의 끝 마디 — 기본 격자 범위(0~25)에 고정하지 않고, 칸이 있는 마지막 마디나
// 곡의 마디 수(timeline bar_count)까지 축을 넓힌다. 축을 줄이지는 않는다.
// 16·8마디 보기 버튼은 축의 길이와 상관없이 그대로 쓴다.

export interface GridAxisRange {
  start: number;
  end: number;
}

/** 모든 줄의 칸 마디 번호. 줄마다 칸 목록(`cues`)의 `bar`만 본다. */
export function cellBarsOf(tracks: ReadonlyArray<{ cues: ReadonlyArray<{ bar: number }> }>): number[] {
  const bars: number[] = [];
  for (const track of tracks) {
    for (const cue of track.cues) bars.push(cue.bar);
  }
  return bars;
}

/** 격자 축의 끝 마디 — 기본 범위 끝, 칸이 있는 마지막 마디, 곡 마디 수 중 가장 큰 값.
 * 유한하지 않은 값(NaN·Infinity)은 무시한다. */
export function gridAxisEnd(
  range: GridAxisRange,
  cellBars: readonly number[],
  barCount: number | null | undefined,
): number {
  let end = range.end;
  for (const bar of cellBars) {
    if (Number.isFinite(bar) && bar > end) end = bar;
  }
  if (typeof barCount === "number" && Number.isFinite(barCount)) {
    const count = Math.round(barCount);
    if (count > end) end = count;
  }
  return end;
}
