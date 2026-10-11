// 박자 격자 — 편집 칸의 전환 화면(SPEC-LDBEAT-001 M9 step 3, 카드 t561,
// REQ-LDBEAT-020(b)(d)(e)). 정본: design/ldbeat-runbook-ui-proposal-
// 20261008.html `drawClipEd`의 `trViewHTML` — 「전환」을 켜면 밝기·위치·색·
// 움직임이 있던 **같은 자리**가 이 화면으로 바뀐다(아래에 상자를 새로 만들지
// 않는다). 「들어올 때(페이드)」는 이 화면에만 있다.
import { useState } from "react";

import type { BeatGridCue, BeatGridTrack } from "../protocol";
import {
  fadeDraftToBars,
  formatFadeSecondsFirst,
  transitionMib,
  transitionWarnings,
} from "./beatGridTransition";
import "./beatGridPanels.css";

/** 시안 `TRK` — 트래킹 어휘(REQ-LDDESIGN-053). 콘솔 송신 없음. */
const TRACKING_VOCABULARY = ["Track", "Cue Only", "Block", "Release"] as const;

export interface BeatGridTransitionViewProps {
  track: BeatGridTrack;
  cue: BeatGridCue;
  prevCue: BeatGridCue | null;
  secondsPerBar: number | null | undefined;
  beatsPerBar: number | null;
  sectionStartBars: readonly number[] | null;
  onEditRequest?: (request: { bar: number; target: string; changes: Record<string, unknown> }) => void;
}

export function BeatGridTransitionView({
  track,
  cue,
  prevCue,
  secondsPerBar,
  beatsPerBar,
  sectionStartBars,
  onEditRequest,
}: BeatGridTransitionViewProps) {
  const [fadeDraft, setFadeDraft] = useState<string>(
    cue.entry.fade_bars === null ? "" : String(cue.entry.fade_bars),
  );
  const [fadeUnit, setFadeUnit] = useState<"bar" | "beat">("bar");
  const [fadeError, setFadeError] = useState<string | null>(null);
  const mib = transitionMib(prevCue, cue);
  const warnings = transitionWarnings(prevCue, cue, sectionStartBars);
  const triggerSeconds =
    secondsPerBar === null || secondsPerBar === undefined ? null : (cue.bar * secondsPerBar).toFixed(2);

  const applyFade = () => {
    const result = fadeDraftToBars(fadeDraft, fadeUnit, beatsPerBar);
    if (result.error !== undefined || result.fadeBars === undefined) {
      setFadeError(result.error ?? "값을 확인해 주세요.");
      return;
    }
    setFadeError(null);
    // 서버의 `entry`는 통째로 바뀌므로 MIB 모드도 그대로 함께 보낸다.
    onEditRequest?.({
      bar: cue.bar,
      target: track.group_name,
      changes: { entry: { fade_bars: result.fadeBars, mib_mode: cue.entry.mib_mode } },
    });
  };

  return (
    <div className="beat-grid-transition-view" aria-label="전환 화면">
      <div className="beat-grid-tr-title">
        전환 — {prevCue ? `'${prevCue.label}' (${prevCue.bar}마디)` : "곡 첫 큐"} → '{cue.label}' ({cue.bar}마디)
      </div>
      <div className="beat-grid-tr-note">값은 들어오는 큐({cue.bar}마디)에 저장돼요(MA3 방식)</div>
      <div className="beat-grid-ed">
        <label>
          페이드
          <small>들어올 때</small>
        </label>
        <div className="beat-grid-dimrow beat-grid-tr-fade">
          <b className="beat-grid-tr-fade-value">{formatFadeSecondsFirst(cue.entry.fade_bars, secondsPerBar)}</b>
          {onEditRequest && (
            <>
              <input
                type="number"
                min={0}
                step={1}
                value={fadeDraft}
                aria-label="페이드 길이"
                onChange={(event) => setFadeDraft(event.target.value)}
              />
              <select
                value={fadeUnit}
                aria-label="페이드 단위"
                onChange={(event) => setFadeUnit(event.target.value as "bar" | "beat")}
              >
                <option value="bar">마디</option>
                <option value="beat" disabled={beatsPerBar === null}>
                  박
                </option>
              </select>
              <button type="button" onClick={applyFade}>
                적용
              </button>
            </>
          )}
        </div>
        {fadeError && <p className="beat-grid-cue-field-note">{fadeError}</p>}

        <label>트리거</label>
        <div>
          {cue.bar}마디{" "}
          <select disabled aria-label="트리거 박" title="박 위치 저장 칸이 없어 1박(마디 시작)으로 고정">
            <option>1</option>
          </select>{" "}
          박{triggerSeconds !== null ? ` = 곡 ${triggerSeconds}초` : ""}
        </div>

        <label>딜레이</label>
        <div className="beat-grid-dimrow">
          <b>—</b>
          <input type="number" disabled aria-label="딜레이(박)" />
          <span className="beat-grid-tr-unknown">박 [미확인] — 속성별 늦은 적용은 실기 미확인</span>
        </div>

        <label>위치만 따로</label>
        <select disabled aria-label="위치만 따로">
          <option>같이(기본)</option>
          <option>1박 늦게 ⚠미확인</option>
        </select>

        <label>MIB</label>
        <div className={`beat-grid-tr-mib is-${mib.kind}`}>
          {mib.kind === "auto" ? "● 자동 " : mib.kind === "lit" ? "● 불가 " : "— "}
          {mib.text}
          {cue.entry.mib_mode !== null && <span className="beat-grid-tr-stored"> · 저장값 {cue.entry.mib_mode}</span>}
        </div>

        <label>트래킹</label>
        <div className="beat-grid-dimrow">
          <select disabled aria-label="트래킹" defaultValue={TRACKING_VOCABULARY[0]}>
            {TRACKING_VOCABULARY.map((word) => (
              <option key={word}>{word}</option>
            ))}
          </select>
          <span className="beat-grid-tr-unknown">콘솔 송신 없음 · 저장 칸 없음</span>
        </div>
      </div>
      {warnings.length > 0 && (
        <div className="beat-grid-tr-warn">⚠ [제안] {warnings.join(" · ")}</div>
      )}
    </div>
  );
}
