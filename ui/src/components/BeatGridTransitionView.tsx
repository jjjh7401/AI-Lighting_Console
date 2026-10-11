// 박자 격자 — 편집 칸의 전환 화면(SPEC-LDBEAT-001 M9 step 3, 카드 t561,
// REQ-LDBEAT-020(b)(d)(e)). 정본: design/ldbeat-runbook-ui-proposal-
// 20261008.html `drawClipEd`의 `trViewHTML` — 「전환」을 켜면 밝기·위치·색·
// 움직임이 있던 **같은 자리**가 이 화면으로 바뀐다(아래에 상자를 새로 만들지
// 않는다). 「들어올 때(페이드)」는 이 화면에만 있다.
// 카드 t574(SPEC 0.5.0) — 트리거 박·딜레이·위치만 따로·트래킹·박 페이드가 저장
// 칸을 얻어 켜진다. 저장은 늘 entry 전체(`entryWith`)로 보낸다 — 서버가 entry 를
// 통째로 바꾸므로 한 필드만 보내면 나머지가 지워진다.
import { useState } from "react";

import type { BeatGridCue, BeatGridTrack } from "../protocol";
import {
  entryWith,
  fadeDraftToEntry,
  formatEntryFade,
  transitionMib,
  transitionWarnings,
  triggerSeconds,
  type FullBeatGridEntry,
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
  /** 카드 t567 — 강조(★) 마디(곡 데이터). 위치 끊김 경고의 예외. */
  accentBars?: readonly number[];
  onEditRequest?: (request: { bar: number; target: string; changes: Record<string, unknown> }) => void;
}

export function BeatGridTransitionView({
  track,
  cue,
  prevCue,
  secondsPerBar,
  beatsPerBar,
  sectionStartBars,
  accentBars = [],
  onEditRequest,
}: BeatGridTransitionViewProps) {
  const storedBeats = cue.entry.fade_beats ?? null;
  const [fadeDraft, setFadeDraft] = useState<string>(
    storedBeats !== null ? String(storedBeats) : cue.entry.fade_bars === null ? "" : String(cue.entry.fade_bars),
  );
  const [fadeUnit, setFadeUnit] = useState<"bar" | "beat">(storedBeats !== null ? "beat" : "bar");
  const [fadeError, setFadeError] = useState<string | null>(null);
  const mib = transitionMib(prevCue, cue);
  const warnings = transitionWarnings(prevCue, cue, sectionStartBars, accentBars);
  const triggerAt = triggerSeconds(cue, secondsPerBar, beatsPerBar);
  const editable = !!onEditRequest;

  const save = (patch: Partial<FullBeatGridEntry>) =>
    onEditRequest?.({ bar: cue.bar, target: track.group_name, changes: { entry: entryWith(cue.entry, patch) } });

  const applyFade = () => {
    const result = fadeDraftToEntry(fadeDraft, fadeUnit, beatsPerBar);
    if (result.error !== undefined || result.fade === undefined) {
      setFadeError(result.error ?? "값을 확인해 주세요.");
      return;
    }
    setFadeError(null);
    save(result.fade);
  };

  /** 박 수 입력(딜레이) — 비우면 미정, 아니면 0 이상의 정수. */
  const commitBeats = (field: "delay_beats", raw: string) => {
    const trimmed = raw.trim();
    if (trimmed === "") {
      if ((cue.entry[field] ?? null) !== null) save({ [field]: null });
      return;
    }
    const value = Number(trimmed);
    if (!Number.isInteger(value) || value < 0) {
      setFadeError("딜레이는 0 이상의 정수 박으로 넣어 주세요.");
      return;
    }
    setFadeError(null);
    if (value !== (cue.entry[field] ?? null)) save({ [field]: value });
  };
  const beatOptions = beatsPerBar === null ? [] : Array.from({ length: beatsPerBar }, (_, i) => i + 1);
  const positionLate = cue.entry.position_late_beats ?? null;

  return (
    <div className="beat-grid-transition-view" aria-label="전환 화면">
      {/* 카드 t586 — 시안 `drawJx` 머리: 「전환 · FOH · Cue 1 → Cue 2」 한 줄 +
          「'FOH Off' → 'Face 60' · 값은 들어오는 큐(Cue 2)에 저장돼요」 한 줄. Cue 번호는
          그 줄 안 순서(편집 칸 머리 `BeatGridCueHeadMeta`와 같은 셈). */}
      <div className="beat-grid-tr-title">
        전환 · {track.group_name} · {prevCue ? `Cue ${track.cues.indexOf(prevCue) + 1}` : "곡 첫 큐"} → Cue{" "}
        {track.cues.indexOf(cue) + 1}
      </div>
      <div className="beat-grid-tr-note">
        {prevCue ? `'${prevCue.label}' (${prevCue.bar}마디) → ` : ""}'{cue.label}' ({cue.bar}마디) · 값은 들어오는
        큐(Cue {track.cues.indexOf(cue) + 1})에 저장돼요(MA3 방식)
      </div>
      <div className="beat-grid-ed">
        <label>
          페이드
          <small>들어올 때</small>
        </label>
        <div className="beat-grid-dimrow beat-grid-tr-fade">
          <b className="beat-grid-tr-fade-value">{formatEntryFade(cue.entry, secondsPerBar, beatsPerBar)}</b>
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
          <select
            aria-label="트리거 박"
            disabled={!editable || beatsPerBar === null}
            title={beatsPerBar === null ? "곡 박자표(마디당 박 수)를 몰라 박을 고를 수 없습니다" : undefined}
            value={String(cue.entry.trigger_beat ?? 1)}
            onChange={(event) => save({ trigger_beat: Number(event.target.value) })}
          >
            {(beatOptions.length > 0 ? beatOptions : [cue.entry.trigger_beat ?? 1]).map((beat) => (
              <option key={beat} value={String(beat)}>
                {beat}
              </option>
            ))}
          </select>{" "}
          박{triggerAt !== null ? ` = 곡 ${triggerAt.toFixed(2)}초` : ""}
        </div>

        <label>딜레이</label>
        <div className="beat-grid-dimrow">
          <input
            type="number"
            min={0}
            step={1}
            aria-label="딜레이(박)"
            disabled={!editable}
            key={`delay-${cue.entry.delay_beats ?? ""}`}
            defaultValue={cue.entry.delay_beats ?? ""}
            onBlur={(event) => commitBeats("delay_beats", event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") commitBeats("delay_beats", event.currentTarget.value);
            }}
          />
          <span className="beat-grid-tr-unknown">박 [미확인] — 속성별 늦은 적용은 실기 미확인</span>
        </div>

        <label>위치만 따로</label>
        <select
          aria-label="위치만 따로"
          disabled={!editable}
          value={positionLate === null ? "" : String(positionLate)}
          onChange={(event) => save({ position_late_beats: event.target.value === "" ? null : Number(event.target.value) })}
        >
          <option value="">같이(기본)</option>
          <option value="1">1박 늦게 ⚠미확인</option>
          {positionLate !== null && positionLate > 1 && (
            <option value={String(positionLate)}>{positionLate}박 늦게 ⚠미확인</option>
          )}
        </select>

        <label>MIB</label>
        <div className={`beat-grid-tr-mib is-${mib.kind}`}>
          {mib.kind === "auto" ? "● 자동 " : mib.kind === "lit" ? "● 불가 " : "— "}
          {mib.text}
          {cue.entry.mib_mode !== null && <span className="beat-grid-tr-stored"> · 저장값 {cue.entry.mib_mode}</span>}
        </div>

        <label>트래킹</label>
        <div className="beat-grid-dimrow">
          <select
            aria-label="트래킹"
            disabled={!editable}
            value={cue.entry.tracking ?? ""}
            onChange={(event) => save({ tracking: event.target.value === "" ? null : event.target.value })}
          >
            <option value="">— 미정</option>
            {TRACKING_VOCABULARY.map((word) => (
              <option key={word} value={word}>
                {word}
              </option>
            ))}
          </select>
          <span className="beat-grid-tr-unknown">콘솔 송신 없음</span>
        </div>
      </div>
      {warnings.length > 0 && (
        <div className="beat-grid-tr-warn">⚠ [제안] {warnings.join(" · ")}</div>
      )}
    </div>
  );
}
