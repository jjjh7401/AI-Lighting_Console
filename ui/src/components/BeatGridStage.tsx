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
  cueForBar,
  cueIsActive,
  fixtureDisplayOpacity,
  fixtureStageColor,
  trackStageColor,
  type BeatGridFixturePoint,
} from "./BeatGrid";
import { fixtureBelongsTo } from "./beatGridStageModel";
import { stageGroupZones } from "./beatGridTransition";
import { StageConceptSvg } from "./beatgrid/StageConceptSvg";
import "./beatGridPanels.css";

/** 시안 `drawStage`의 그림 높이(`H=300`)와 최소 폭(`420`). */
const STAGE_H = 300;
const STAGE_MIN_W = 420;
const STAGE_MARGIN = 24;
const ZONE_PADDING = 8;

/** 카드 t588 — 시안 `drawStage` 장식의 그림 비율. 리그·곡 값이 아니라 그림
 * 모양 값이다: 빔 반폭 9(시안 `x-9`·`x+9`), 빔 불투명도 100/260(시안 `h/260`, 켜짐
 * 최대), 워시 면 불투명도 40/160(시안 `sh/160` — 앱은 디머 수치를 지어내지 않아
 * 켜짐 한 단계뿐이라 시안 표본 값 40%로 고정). 빔 길이는 장비에서 무대 앞
 * 가장자리까지의 거리 비율이다(시안은 틸트로 정하지만 앱은 틸트를 읽지 않는다). */
const BEAM_HALF_WIDTH = 9;
const BEAM_OPACITY = 100 / 260;
const BEAM_REACH = 0.5;
const WASH_OPACITY = 40 / 160;

export interface StageDecorations {
  /** 시안 `#1b1b22` 무대 바닥 — 읽힌 장비 전체를 감싸는 면. */
  floor: { x: number; y: number; width: number; height: number } | null;
  /** 시안 워시 면 — 층 역할이 wash 인 줄의 소속 장비 영역, 그 칸이 켜졌을 때만. */
  washes: { key: string; x: number; y: number; width: number; height: number; fill: string }[];
  /** 시안 무빙 빔 — 층 역할이 mover 인 줄의 소속 장비마다 무대 앞쪽으로, 켜졌을 때만. */
  beams: { key: string; points: string; fill: string }[];
}

/** 카드 t588 — 시안 `drawStage` 의 바닥·워시·빔 장식을 **장비 좌표에서** 만든다.
 * 어느 줄이 워시/무빙인지는 줄의 층 역할(`layer_role`, 앱 어휘)에서만 읽고,
 * 위치는 그 줄에 소속이 확인된 장비 좌표에서만 잡는다 — 그룹 이름·번호 상수 0.
 * 켜짐은 무대 점과 같은 판정(`cueIsActive`)이다. */
export function stageDecorations(
  fixtures: readonly BeatGridFixturePoint[],
  tracks: readonly BeatGridTrack[],
  project: (point: { x: number; y: number }) => { cx: number; cy: number },
  viewBar: number,
  frontY: number,
  padding: number,
): StageDecorations {
  if (fixtures.length === 0) return { floor: null, washes: [], beams: [] };
  const all = fixtures.map((f) => project(f));
  const minX = Math.min(...all.map((p) => p.cx)) - padding;
  const minY = Math.min(...all.map((p) => p.cy)) - padding;
  const floor = {
    x: minX,
    y: minY,
    width: Math.max(...all.map((p) => p.cx)) + padding - minX,
    height: Math.max(...all.map((p) => p.cy)) + padding - minY,
  };
  const lit = (track: BeatGridTrack) => {
    const cue = cueForBar(track, viewBar);
    return cue !== null && cueIsActive(cue.label);
  };
  const washes: StageDecorations["washes"] = [];
  const beams: StageDecorations["beams"] = [];
  const zones = stageGroupZones(fixtures, tracks, project, padding);
  for (const zone of zones) {
    const track = tracks[zone.trackIndex];
    if (track.layer_role !== "wash" || !lit(track)) continue;
    const member = fixtures.find((f) => fixtureBelongsTo(f, track.group_name));
    washes.push({
      key: `wash-${zone.trackIndex}`,
      x: zone.x,
      y: zone.y,
      width: zone.width,
      height: zone.height,
      fill: member ? fixtureStageColor(member, tracks, viewBar) : "#888",
    });
  }
  // 켜진 무빙만 빔(리드 결정): 무빙 여부는 장비 능력(`fixtureIsMover`), 켜짐은 소속 줄의 칸.
  for (const fixture of fixtures) {
    if (!fixtureIsMover(fixture, tracks)) continue;
    const trackIndex = tracks.findIndex((track) => fixtureBelongsTo(fixture, track.group_name));
    if (trackIndex < 0 || !lit(tracks[trackIndex])) continue;
    const { cx, cy } = project(fixture);
    const len = Math.max(0, (frontY - cy) * BEAM_REACH);
    if (len <= 0) continue;
    beams.push({
      key: `beam-${trackIndex}-${fixture.fid}`,
      points: `${cx},${cy} ${cx - BEAM_HALF_WIDTH},${cy + len} ${cx + BEAM_HALF_WIDTH},${cy + len}`,
      fill: trackStageColor(tracks[trackIndex], trackIndex, viewBar),
    });
  }
  return { floor, washes, beams };
}

/** 카드 t591 — 시안 `drawStage` 는 무빙 장비를 10×10 네모(`rect x-5 y-5`)로,
 * 나머지를 동그라미로 그린다. 무빙인지는 층 역할이 mover 인 줄에 **소속이
 * 확인된**(무대 판독 `member_fids`) 장비인가로만 정한다 — 그룹 이름 규칙 0. */
export function fixtureIsMover(fixture: BeatGridFixturePoint, tracks: readonly BeatGridTrack[]): boolean {
  // 서버가 팬·틸트 능력(`pan_tilt`)을 알면 그것이 기준이다(리드 결정). 키가 없으면(모름) 임시로 층 역할이
  // mover 인 줄에 소속이 확인된 장비만 무빙으로 본다.
  if (fixture.pan_tilt !== undefined) return fixture.pan_tilt;
  return tracks.some((track) => track.layer_role === "mover" && fixtureBelongsTo(fixture, track.group_name));
}

/** 리드 결정(모양은 장비 능력으로, 어휘는 늘리지 않음) — 무빙이 아닌 효과(effect) 줄의 장비는 사각(BLIND 류)으로
 * 그린다. 무빙 판정(팬·틸트 능력 필드)은 서버가 필드를 줄 때 바꾼다. */
export function fixtureIsBlind(fixture: BeatGridFixturePoint, tracks: readonly BeatGridTrack[]): boolean {
  return (
    !fixtureIsMover(fixture, tracks) &&
    tracks.some((track) => track.layer_role === "effect" && fixtureBelongsTo(fixture, track.group_name))
  );
}

const BLIND_HALF_W = 7;
const BLIND_HALF_H = 4;
const MOVER_HALF = 5;

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
    // 패치 좌표를 못 읽으면 시안 개념도 배치를 같은 자리에 그린다(좌표는 지어내지 않는다).
    return (
      <div className="beat-grid-stage-box" ref={boxRef}>
        <StageConceptSvg
          width={viewW}
          height={STAGE_H}
          tracks={tracks}
          viewBar={viewBar}
          selectedTrackName={selectedTrackName}
          onSelectTrack={onSelectTrack}
        />
        {/* 기존 안내(AC-LDBEAT-022)는 그대로 남기고, 그림이 개념도임을 덧붙인다. */}
        <p className="beat-grid-stage-note">
          {notes && notes.length > 0
            ? "무대 좌표를 못 읽음 — 아래 그림은 시안의 개념도 배치예요(장비 위치는 지어내지 않음)."
            : "무대 좌표 미제공 — 박자 격자를 열면 콘솔 패치에서 읽어 옵니다. 아래 그림은 시안의 개념도 배치예요(장비 위치는 지어내지 않음)."}
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
  // 카드 t588 — 시안 장식은 점 아래에 깐다(바닥 → 워시 면 → 빔 → 장비 점).
  const decor = stageDecorations(fixtures, tracks, project, viewBar, STAGE_H - STAGE_MARGIN, ZONE_PADDING);

  return (
    <div className="beat-grid-stage-box" ref={boxRef}>
      <svg viewBox={`0 0 ${viewW} ${STAGE_H}`} className="beat-grid-stage">
        {decor.floor && (
          <rect
            className="beat-grid-stage-floor"
            x={decor.floor.x}
            y={decor.floor.y}
            width={decor.floor.width}
            height={decor.floor.height}
            fill="#1b1b22"
            stroke="#333"
          />
        )}
        {decor.washes.map((wash) => (
          <rect
            key={wash.key}
            className="beat-grid-stage-wash"
            x={wash.x}
            y={wash.y}
            width={wash.width}
            height={wash.height}
            fill={wash.fill}
            opacity={WASH_OPACITY}
          />
        ))}
        {decor.beams.map((beam) => (
          <polygon
            key={beam.key}
            className="beat-grid-stage-beam"
            points={beam.points}
            fill={beam.fill}
            opacity={BEAM_OPACITY}
          />
        ))}
        {fixtures.map((fixture) => {
          const { cx, cy } = project(fixture);
          const fill = fixtureStageColor(fixture, tracks, viewBar);
          const opacity = fixtureDisplayOpacity(fixture, tracks, viewBar);
          const title = <title>{`${fixture.name} (fid ${fixture.fid})`}</title>;
          return fixtureIsMover(fixture, tracks) ? (
            <rect
              key={fixture.fid}
              className="beat-grid-stage-mover"
              x={cx - MOVER_HALF}
              y={cy - MOVER_HALF}
              width={MOVER_HALF * 2}
              height={MOVER_HALF * 2}
              fill={fill}
              opacity={opacity}
            >
              {title}
            </rect>
          ) : fixtureIsBlind(fixture, tracks) ? (
            <rect
              key={fixture.fid}
              className="beat-grid-stage-blind"
              x={cx - BLIND_HALF_W}
              y={cy - BLIND_HALF_H}
              width={BLIND_HALF_W * 2}
              height={BLIND_HALF_H * 2}
              fill={fill}
              opacity={opacity}
            >
              {title}
            </rect>
          ) : (
            <circle key={fixture.fid} cx={cx} cy={cy} r={5} fill={fill} opacity={opacity}>
              {title}
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
