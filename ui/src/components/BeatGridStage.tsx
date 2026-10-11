// 박자 격자 — 2D 무대(SPEC-LDBEAT-001 M9 step 5, 카드 t561, REQ-LDBEAT-022).
// 정본: design/ldbeat-runbook-ui-proposal-20261008.html `drawStage` — 칸
// 비율에 맞춰 가로를 채우고(창 크기가 바뀌면 다시 그림), 고른 줄의 장비에
// 노란 점선 테두리, 그룹 이름표, 장비 영역을 누르면 그 줄 편집이 열린다.
// 좌표는 콘솔 패치(Posx·Posy)에서 온 값만 쓴다(손그림이 아니다). 시안의
// 고정 그룹 이름(FOH·WASH…)은 예시일 뿐이고, 이름표는 곡의 트랙 이름에서
// 온다.
import { useEffect, useRef, useState } from "react";

import type { BeatGridTrack } from "../protocol";
import {
  computeStageBounds,
  fixtureDisplayColor,
  fixtureDisplayOpacity,
  type BeatGridFixturePoint,
} from "./BeatGrid";
import { stageGroupZones } from "./beatGridTransition";
import "./beatGridPanels.css";

/** 시안 `drawStage`의 그림 높이(`H=300`)와 최소 폭(`420`). */
const STAGE_H = 300;
const STAGE_MIN_W = 420;
const STAGE_MARGIN = 24;
const ZONE_PADDING = 8;

/** 칸 비율에 맞춘 그림 폭 — 시안 `Math.max(420, round(H * clientW/clientH))`. */
export function stageViewWidth(clientWidth: number, clientHeight: number): number {
  if (clientWidth <= 0 || clientHeight <= 0) return STAGE_MIN_W;
  return Math.max(STAGE_MIN_W, Math.round(STAGE_H * (clientWidth / clientHeight)));
}

export function BeatGridStage({
  fixtures,
  tracks,
  viewBar,
  selectedTrackName,
  onSelectTrack,
  notes,
}: {
  fixtures: readonly BeatGridFixturePoint[];
  tracks: readonly BeatGridTrack[];
  viewBar: number;
  selectedTrackName: string | null;
  onSelectTrack: (trackIndex: number) => void;
  /** 카드 t565 — 서버 무대 판독이 못 읽은 이유(그대로 보인다). */
  notes?: readonly string[];
}) {
  const boxRef = useRef<HTMLDivElement | null>(null);
  const [viewW, setViewW] = useState(STAGE_MIN_W);
  useEffect(() => {
    const box = boxRef.current;
    if (!box || typeof ResizeObserver === "undefined") return;
    const measure = () => setViewW(stageViewWidth(box.clientWidth, box.clientHeight));
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(box);
    return () => observer.disconnect();
  }, []);

  const bounds = computeStageBounds(fixtures);
  if (!bounds) {
    return (
      <div className="beat-grid-stage-box" ref={boxRef}>
        <p className="beat-grid-empty">
          {notes && notes.length > 0 ? "무대 좌표를 못 읽음" : "무대 좌표 미제공 — 박자 격자를 열면 콘솔 패치에서 읽어 옵니다."}
        </p>
        <StageNotes notes={notes} />
      </div>
    );
  }
  // 장비 줄이 칸 폭 전체에 고르게 퍼지도록 가로·세로를 따로 늘린다.
  const project = (point: { x: number; y: number }) => ({
    cx: STAGE_MARGIN + ((point.x - bounds.minX) / bounds.spanX) * (viewW - STAGE_MARGIN * 2),
    // Y가 클수록(무대 뒤) 위쪽.
    cy: STAGE_MARGIN + ((bounds.maxY - point.y) / bounds.spanY) * (STAGE_H - STAGE_MARGIN * 2),
  });
  const zones = stageGroupZones(fixtures, tracks, project, ZONE_PADDING);
  const selectedKey = selectedTrackName?.toUpperCase() ?? null;

  return (
    <div className="beat-grid-stage-box" ref={boxRef}>
      <svg viewBox={`0 0 ${viewW} ${STAGE_H}`} className="beat-grid-stage">
        {fixtures.map((fixture) => {
          const { cx, cy } = project(fixture);
          return (
            <circle
              key={fixture.fid}
              cx={cx}
              cy={cy}
              r={5}
              fill={fixtureDisplayColor(fixture, tracks)}
              opacity={fixtureDisplayOpacity(fixture, tracks, viewBar)}
            >
              <title>{`${fixture.name} (fid ${fixture.fid})`}</title>
            </circle>
          );
        })}
        {zones.map((zone) => (
          <text key={`label-${zone.trackIndex}`} className="beat-grid-stage-label" x={zone.x} y={zone.y - 3}>
            {zone.label}
          </text>
        ))}
        {zones
          .filter((zone) => zone.label.toUpperCase() === selectedKey)
          .map((zone) => (
            <rect
              key={`sel-${zone.trackIndex}`}
              className="beat-grid-stage-selected"
              x={zone.x}
              y={zone.y}
              width={zone.width}
              height={zone.height}
              rx={4}
              fill="none"
              stroke="#ffd84d"
              strokeWidth={2}
              strokeDasharray="5 3"
            />
          ))}
        {zones.map((zone) => (
          <rect
            key={`hit-${zone.trackIndex}`}
            className="beat-grid-stage-hit"
            data-track={zone.label}
            x={zone.x}
            y={zone.y}
            width={zone.width}
            height={zone.height}
            fill="transparent"
            onClick={() => onSelectTrack(zone.trackIndex)}
          >
            <title>{`${zone.label} — 눌러서 편집`}</title>
          </rect>
        ))}
      </svg>
      <StageNotes notes={notes} />
    </div>
  );
}

/** 판독이 못 읽은 것 — 지어내지 않고 이유를 그대로 보인다. */
function StageNotes({ notes }: { notes?: readonly string[] }) {
  if (!notes || notes.length === 0) return null;
  return (
    <ul className="beat-grid-stage-notes" aria-label="무대 판독 안내">
      {notes.map((note) => (
        <li key={note}>⚠ {note}</li>
      ))}
    </ul>
  );
}
