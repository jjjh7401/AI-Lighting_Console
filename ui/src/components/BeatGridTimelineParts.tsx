// 박자 격자 — 타임라인의 이음매 표시·장면 전환 알약·장면 전환 표(SPEC-
// LDBEAT-001 M9 step 3, 카드 t561, REQ-LDBEAT-020(a)). 정본: design/
// ldbeat-runbook-ui-proposal-20261008.html `clipsHTML`(`.jt`·`.fw`)·
// `drawLanes`(`.trow`·`.tm`)·`drawTr`(장면 전환 표).
import type { BeatGridCue, BeatGridTrack } from "../protocol";
import { barToX, PX_PER_BAR } from "./BeatGrid";
import {
  entryFadeInBars,
  entryHasFade,
  formatEntryFade,
  jointMarker,
  sceneChangeRows,
  sceneEntryEdits,
  transitionMib,
  transitionWarnings,
  trimSeconds,
  type FullBeatGridEntry,
} from "./beatGridTransition";
import "./beatGridPanels.css";

/** 이음매 하나 + 다음 막대 왼쪽의 페이드 번짐(시안 `.jt` + `.fw`). */
export function BeatGridJoint({
  prev,
  cue,
  nextSegmentWidth,
  prevFill,
  sectionStartBars,
  secondsPerBar,
  isOn,
  onOpen,
  pxPerBar = PX_PER_BAR,
  beatsPerBar = null,
  accentBars = [],
}: {
  prev: BeatGridCue;
  cue: BeatGridCue;
  /** 다음 막대의 화면 폭(번짐이 막대를 넘지 않게). */
  nextSegmentWidth: number;
  /** 앞 막대의 채우기 색 — 모르면 `null`(켜짐/꺼짐 중립색으로 번진다). */
  prevFill: string | null;
  sectionStartBars: readonly number[] | null;
  secondsPerBar: number | null | undefined;
  isOn: boolean;
  onOpen: () => void;
  /** 곡 전체 지도 확대 단계별 마디 폭(카드 t559). */
  pxPerBar?: number;
  /** 카드 t574 — 박 페이드·트리거 박 위치 환산(곡 박자표, 모르면 null). */
  beatsPerBar?: number | null;
  /** 카드 t567 — 강조(★) 마디(곡 데이터). 위치 끊김 경고의 예외. */
  accentBars?: readonly number[];
}) {
  const marker = jointMarker(prev, cue, sectionStartBars, secondsPerBar ?? null, beatsPerBar, accentBars);
  const fadeBars = entryHasFade(cue.entry) ? (entryFadeInBars(cue.entry, beatsPerBar) ?? 0) : 0;
  // 시안 `.jt` 위치 = 마디 + (트리거 박 - 1) 칸 — 박자표를 모르면 마디 시작에 둔다.
  const triggerOffset =
    beatsPerBar !== null && cue.entry.trigger_beat ? ((cue.entry.trigger_beat - 1) / beatsPerBar) * pxPerBar : 0;
  const left = barToX(cue.bar, pxPerBar) + triggerOffset;
  const bleedFrom = prevFill ?? (prev.label.trim() === "—" ? "#25252c" : "#d8d8d8");
  return (
    <>
      {fadeBars > 0 && (
        <span
          className="beat-grid-fade-bleed"
          aria-hidden="true"
          style={{
            left,
            width: Math.min(nextSegmentWidth, fadeBars * pxPerBar),
            background: `linear-gradient(90deg, ${bleedFrom}, transparent)`,
          }}
        />
      )}
      <button
        type="button"
        className={["beat-grid-joint", ...marker.classes, isOn ? "is-on" : ""].filter(Boolean).join(" ")}
        style={{ left }}
        title={marker.title}
        onClick={onOpen}
      >
        {marker.glyph || "◆"}
      </button>
    </>
  );
}

/** 자 바로 아래 「장면 전환」 줄 — 3줄 이상이 같이 바뀌는 마디에 알약. */
export function BeatGridSceneRow({
  bars,
  activeBar,
  width,
  onSelect,
  pxPerBar = PX_PER_BAR,
}: {
  bars: readonly { bar: number; count: number }[];
  activeBar: number | null;
  width: number;
  onSelect: (bar: number) => void;
  pxPerBar?: number;
}) {
  return (
    <div className="beat-grid-scene-row">
      <span className="beat-grid-track-label beat-grid-scene-row-label">장면 전환 ▼</span>
      <div className="beat-grid-scene-row-track" style={{ width }}>
        {bars.map(({ bar, count }) => (
          <button
            type="button"
            key={bar}
            className={`beat-grid-scene-pill${activeBar === bar ? " is-on" : ""}`}
            style={{ left: barToX(bar, pxPerBar) }}
            title={`${bar}마디에서 ${count}줄이 함께 바뀜 — 누르면 그 순간 전체`}
            onClick={() => onSelect(bar)}
          >
            {bar}마디 {count}줄
          </button>
        ))}
      </div>
    </div>
  );
}

/** 알약을 누르면 편집 칸에 열리는 「그 순간 전체 표」(시안 `drawTr` scene). */
export function BeatGridScenePanel({
  bar,
  tracks,
  secondsPerBar,
  sectionStartBars,
  onClose,
  onSelectRow,
  onBulkEntry,
  beatsPerBar = null,
  accentBars = [],
}: {
  bar: number;
  tracks: readonly BeatGridTrack[];
  secondsPerBar: number | null | undefined;
  sectionStartBars: readonly number[] | null;
  onClose: () => void;
  onSelectRow: (trackIndex: number) => void;
  /** 「모두 끊기」·「모두 1박 페이드」 — 줄마다 다른 entry 값은 그대로 둔 새 entry
   * 를 받는다(카드 t574). 편집 경로가 없으면 두 버튼 모두 비활성. */
  onBulkEntry?: (edits: { target: string; entry: FullBeatGridEntry }[]) => void;
  beatsPerBar?: number | null;
  /** 카드 t567 — 강조(★) 마디(곡 데이터). */
  accentBars?: readonly number[];
}) {
  const rows = sceneChangeRows(tracks, bar);
  return (
    <div className="beat-grid-scene-panel" aria-label="장면 전환">
      <header>
        <span>
          장면 전환 · {bar}마디
          {secondsPerBar !== null && secondsPerBar !== undefined ? ` (곡 ${trimSeconds(bar * secondsPerBar)}초)` : ""}
        </span>
        <button type="button" aria-label="닫기" onClick={onClose}>
          ✕
        </button>
      </header>
      <div className="beat-grid-tr-note">이 순간 {rows.length}줄이 함께 바뀜 — 한눈에 보고 줄별로 고치기</div>
      <table className="beat-grid-scene-table">
        <tbody>
          {rows.map((row) => {
            const mib = transitionMib(row.prev, row.cue);
            const warnings = transitionWarnings(row.prev, row.cue, sectionStartBars, accentBars);
            return (
              <tr key={row.track.group_name} onClick={() => onSelectRow(row.trackIndex)}>
                <td className="rn">{row.track.group_name}</td>
                <td>
                  {entryHasFade(row.cue.entry)
                    ? `페이드 ${formatEntryFade(row.cue.entry, secondsPerBar, beatsPerBar)}`
                    : formatEntryFade(row.cue.entry, secondsPerBar, beatsPerBar)}
                </td>
                <td>{mib.kind === "auto" ? "MIB 자동" : mib.kind === "lit" ? "켜진 채 이동" : "—"}</td>
                <td>{warnings.length ? <span className="u">⚠ [제안] {warnings.join(" · ")}</span> : null}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <div className="beat-grid-scene-actions">
        <button
          type="button"
          className="tbtn"
          disabled={!onBulkEntry}
          onClick={() => onBulkEntry?.(sceneEntryEdits(tracks, bar, { fade_bars: 0, fade_beats: null }))}
        >
          모두 끊기
        </button>
        {/* 카드 t574 — fade_beats 저장 칸(REQ-LDBEAT-006(i-4a))이 생겨 1박도 저장된다. */}
        <button
          type="button"
          className="tbtn"
          disabled={!onBulkEntry}
          onClick={() => onBulkEntry?.(sceneEntryEdits(tracks, bar, { fade_bars: null, fade_beats: 1 }))}
        >
          모두 1박 페이드
        </button>
      </div>
      <div className="beat-grid-tr-note">규칙: 히트(★)는 끊기, 장면 전환은 크로스페이드 — 규칙서 §2.3 규칙 2</div>
    </div>
  );
}
