// 「웨이브 프리셋 만들기」 — 고른 줄 하나에 디머·컬러 웨이브 다섯 개를 콘솔 효과 풀(풀 21)에 저장한다.
// 줄은 격자 트랙에서 고른다. 콘솔 그룹 번호가 확인되지 않은 줄은 고를 수 없고, 서버도 같은 판정을 한다.
import { useState } from "react";

import type { BeatGridTrack } from "../../protocol";

/** 고를 수 있는 줄 — 콘솔 그룹 번호가 확인된 트랙만. */
export function waveTrackChoices(tracks: readonly BeatGridTrack[]): BeatGridTrack[] {
  return tracks.filter((track) => track.group_no_confirmed && typeof track.group_no === "number");
}

export function WavePresetControls({
  tracks,
  onRequest,
}: {
  tracks: readonly BeatGridTrack[];
  onRequest: (groupName: string) => void;
}) {
  const choices = waveTrackChoices(tracks);
  const [picked, setPicked] = useState<string | null>(null);
  const current = choices.find((track) => track.group_name === picked) ?? choices[0] ?? null;
  return (
    <div className="wave-preset-controls" role="group" aria-label="웨이브 프리셋">
      <select
        aria-label="웨이브를 넣을 줄"
        value={current?.group_name ?? ""}
        disabled={choices.length === 0}
        onChange={(event) => setPicked(event.target.value)}
      >
        {choices.map((track) => (
          <option key={track.group_name} value={track.group_name}>
            {track.group_name}
          </option>
        ))}
      </select>
      <button
        type="button"
        className="tbtn"
        disabled={current === null}
        title="디머·컬러 웨이브 프리셋 다섯 개를 고른 줄에 맞춰 콘솔 효과 풀(풀 21)에 저장한다 — 승인 카드에서 「실행」을 눌러야 저장된다"
        onClick={() => {
          if (current) onRequest(current.group_name);
        }}
      >
        웨이브 프리셋 만들기
      </button>
      {choices.length === 0 && (
        <span className="wave-preset-note">콘솔 그룹 번호가 확인된 줄이 없습니다</span>
      )}
    </div>
  );
}
