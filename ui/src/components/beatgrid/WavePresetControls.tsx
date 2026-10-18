// 「웨이브 프리셋 만들기」 — 고른 줄 하나에 웨이브를 콘솔 효과 풀(풀 21)에 저장한다.
// 다섯 기본 프리셋 버튼과, 감독이 모양·박 수·이름을 골라 한 개를 저장하는 「직접 만들기」가 있다.
// 줄은 격자 트랙에서 고른다. 콘솔 그룹 번호가 확인되지 않은 줄은 고를 수 없고, 서버도 같은 판정을 한다.
import { useState } from "react";

import type { BeatGridTrack, WaveCustomPreset } from "../../protocol";
import { skippedBarNote } from "./cellSelection";

/** 고를 수 있는 줄 — 콘솔 그룹 번호가 확인된 트랙만. */
export function waveTrackChoices(tracks: readonly BeatGridTrack[]): BeatGridTrack[] {
  return tracks.filter((track) => track.group_no_confirmed && typeof track.group_no === "number");
}

/** 직접 만들기 — 고를 수 있는 웨이브 모양(서버 `wave_custom` 과 같은 목록). */
export const WAVE_SHAPE_CHOICES = [
  { id: "sine", label: "디머 웨이브 · 사인" },
  { id: "rainbow", label: "컬러 웨이브 · 무지개" },
  { id: "warmcool", label: "컬러 웨이브 · 웜쿨" },
] as const;

/** 직접 만들기 — 고를 수 있는 한 주기 박 수. */
export const WAVE_BEAT_CHOICES: readonly number[] = [1, 2, 4];

const CONSOLE_LABEL = /^[A-Za-z0-9](?:[A-Za-z0-9 ]*[A-Za-z0-9])?$/;

/** 직접 만들기 값 검사 — 서버(`wave_custom`)와 같은 규칙을 화면에서 먼저 본다. 사유 또는 null. */
export function waveCustomProblem(form: WaveCustomPreset): string | null {
  if (!WAVE_SHAPE_CHOICES.some((shape) => shape.id === form.shape)) {
    return "웨이브 모양을 고르세요.";
  }
  if (!WAVE_BEAT_CHOICES.includes(form.beats)) return "박 수를 고르세요.";
  if (form.label.length > 20 || !CONSOLE_LABEL.test(form.label)) {
    return "콘솔 이름은 영문·숫자·가운데 공백만 쓰고 20자 이하로 적어 주세요.";
  }
  const name = form.displayName.trim();
  if (name === "" || name.length > 40) return "화면 이름은 1~40자로 적어 주세요.";
  return null;
}

export function WavePresetControls({
  tracks,
  onRequest,
  onCustomRequest,
  selectedCells = [],
  skippedCellCount = 0,
}: {
  tracks: readonly BeatGridTrack[];
  onRequest: (groupName: string) => void;
  onCustomRequest?: (
    groupName: string,
    preset: WaveCustomPreset,
    cells: ReadonlyArray<readonly [string, number]>,
  ) => void;
  /** 지금 고른 칸(줄·마디 쌍) — 「선택한 칸에도 적용」을 켜면 저장이 끝난 뒤 이 칸들에 번호를 적는다. */
  selectedCells?: ReadonlyArray<readonly [string, number]>;
  /** 고른 칸 가운데 0마디(앞박)라 칸 적용으로 보낼 수 없는 칸 수 — 빠진 이유를 서랍에 말한다. */
  skippedCellCount?: number;
}) {
  const choices = waveTrackChoices(tracks);
  const [picked, setPicked] = useState<string | null>(null);
  const current = choices.find((track) => track.group_name === picked) ?? choices[0] ?? null;
  const [form, setForm] = useState<WaveCustomPreset>({
    shape: "sine",
    beats: 2,
    label: "",
    displayName: "",
  });
  const [applyToCells, setApplyToCells] = useState(false);
  const problem = waveCustomProblem(form);
  const canSave = current !== null && problem === null && onCustomRequest !== undefined;
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
      <div className="wave-custom-form" role="group" aria-label="웨이브 직접 만들기">
        <select
          aria-label="웨이브 모양"
          value={form.shape}
          onChange={(event) => setForm({ ...form, shape: event.target.value })}
        >
          {WAVE_SHAPE_CHOICES.map((shape) => (
            <option key={shape.id} value={shape.id}>
              {shape.label}
            </option>
          ))}
        </select>
        <select
          aria-label="박 수"
          value={form.beats}
          onChange={(event) => setForm({ ...form, beats: Number(event.target.value) })}
        >
          {WAVE_BEAT_CHOICES.map((beats) => (
            <option key={beats} value={beats}>
              {`${beats}박`}
            </option>
          ))}
        </select>
        <input
          aria-label="콘솔 이름"
          placeholder="MY SINE 2B"
          maxLength={20}
          value={form.label}
          onChange={(event) => setForm({ ...form, label: event.target.value })}
        />
        <input
          aria-label="화면 이름"
          placeholder="내 사인 2박"
          maxLength={40}
          value={form.displayName}
          onChange={(event) => setForm({ ...form, displayName: event.target.value })}
        />
        {selectedCells.length > 0 && (
          <label className="wave-custom-cells">
            <input
              type="checkbox"
              checked={applyToCells}
              onChange={(event) => setApplyToCells(event.target.checked)}
            />
            {`선택한 칸 ${selectedCells.length}개에도 적용`}
          </label>
        )}
        {skippedCellCount > 0 && (
          <span className="wave-custom-cells-note">
            {skippedBarNote(skippedCellCount, "edit")}
            {selectedCells.length > 0 ? " — 나머지 칸에만 적용돼요" : ""}
          </span>
        )}
        <button
          type="button"
          className="tbtn"
          disabled={!canSave}
          title="고른 모양·박 수·이름으로 웨이브 프리셋 하나를 콘솔 효과 풀(풀 21)에 저장한다 — 승인 카드에서 「실행」을 눌러야 저장된다"
          onClick={() => {
            if (current && onCustomRequest && problem === null) {
              onCustomRequest(current.group_name, form, applyToCells ? selectedCells : []);
            }
          }}
        >
          이름 붙여 저장
        </button>
        {problem !== null && (form.label !== "" || form.displayName !== "") && (
          <span className="wave-custom-problem" role="alert">
            {problem}
          </span>
        )}
      </div>
    </div>
  );
}
