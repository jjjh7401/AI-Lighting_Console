// 박자 격자 — 타임라인의 이음매 표시·장면 전환 알약·장면 전환 표(SPEC-
// LDBEAT-001 M9 step 3, 카드 t561, REQ-LDBEAT-020(a)). 정본: design/
// ldbeat-runbook-ui-proposal-20261008.html `clipsHTML`(`.jt`·`.fw`)·
// `drawLanes`(`.trow`·`.tm`)·`drawTr`(장면 전환 표).
import type { BeatGridCue, BeatGridTrack } from "../protocol";
import { barToX, PX_PER_BAR } from "./BeatGrid";
import {
  formatFadeSecondsFirst,
  jointMarker,
  sceneChangeRows,
  transitionMib,
  transitionWarnings,
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
}) {
  const marker = jointMarker(prev, cue, sectionStartBars, secondsPerBar ?? null);
  const fadeBars = cue.entry.fade_bars ?? 0;
  const left = barToX(cue.bar);
  const bleedFrom = prevFill ?? (prev.label.trim() === "—" ? "#25252c" : "#d8d8d8");
  return (
    <>
      {fadeBars > 0 && (
        <span
          className="beat-grid-fade-bleed"
          aria-hidden="true"
          style={{
            left,
            width: Math.min(nextSegmentWidth, fadeBars * PX_PER_BAR),
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
}: {
  bars: readonly { bar: number; count: number }[];
  activeBar: number | null;
  width: number;
  onSelect: (bar: number) => void;
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
            style={{ left: barToX(bar) }}
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
  onCutAll,
}: {
  bar: number;
  tracks: readonly BeatGridTrack[];
  secondsPerBar: number | null | undefined;
  sectionStartBars: readonly number[] | null;
  onClose: () => void;
  onSelectRow: (trackIndex: number) => void;
  /** 「모두 끊기」 — 편집 경로가 없으면 버튼은 비활성. */
  onCutAll?: (rows: { target: string; mibMode: string | null }[]) => void;
}) {
  const rows = sceneChangeRows(tracks, bar);
  return (
    <div className="beat-grid-scene-panel" aria-label="장면 전환">
      <header>
        <span>
          장면 전환 · {bar}마디
          {secondsPerBar !== null && secondsPerBar !== undefined ? ` (곡 ${(bar * secondsPerBar).toFixed(2)}초)` : ""}
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
            const warnings = transitionWarnings(row.prev, row.cue, sectionStartBars);
            return (
              <tr key={row.track.group_name} onClick={() => onSelectRow(row.trackIndex)}>
                <td className="rn">{row.track.group_name}</td>
                <td>
                  {row.cue.entry.fade_bars
                    ? `페이드 ${formatFadeSecondsFirst(row.cue.entry.fade_bars, secondsPerBar)}`
                    : formatFadeSecondsFirst(row.cue.entry.fade_bars, secondsPerBar)}
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
          disabled={!onCutAll}
          onClick={() =>
            onCutAll?.(rows.map((row) => ({ target: row.track.group_name, mibMode: row.cue.entry.mib_mode })))
          }
        >
          모두 끊기
        </button>
        <button
          type="button"
          className="tbtn"
          disabled
          title="1박 페이드는 마디보다 짧아 지금 저장 단위(정수 마디, entry.fade_bars)로 저장할 수 없습니다"
        >
          모두 1박 페이드
        </button>
      </div>
      <div className="beat-grid-tr-note">규칙: 히트(★)는 끊기, 장면 전환은 크로스페이드 — 규칙서 §2.3 규칙 2</div>
    </div>
  );
}
