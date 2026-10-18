/** 무대 개념도 — 시안 `drawStage` 의 자리 배치를 그대로 옮긴다.
 *
 * 패치 좌표를 못 읽으면 이 그림을 대신 그린다. 장비 위치는 지어내지 않는다.
 * 자리는 줄의 층 역할로 정한다(BACK 원 줄 · BLIND 사각 · U/D 무빙 두 줄 · SIDE-L/R 원 세로줄 ·
 * WASH 점 · FOH 점). 무빙은 첫 줄이 위(U), 둘째 줄이 아래(D) — 이름 규칙은 쓰지 않는다(리드 결정).
 * 색은 지금 마디의 그 줄 색(켜짐 = 칸 색, 꺼짐 = #333), 빔은 켜진 무빙만, 고른 줄은 노란 점선 테두리.
 * 자리나 이름표를 누르면 그 자리를 맡는 줄을 고른다(줄 편집). Shift 를 누르면 고른 줄에 더하거나 뺀다.
 */
import type { MouseEvent as ReactMouseEvent, ReactNode } from "react";

import type { BeatGridTrack } from "../../protocol";
import { OFF_FIXTURE_COLOR, cueForBar, trackIsLitAt, trackStageColor } from "../BeatGrid";
import { moverBeamPoints, type StagePresetBook } from "./moverMotion";

/** 개념도 무빙 빔이 위치 이름을 모를 때(reach 0.5) 시안 길이 98.5 가 되도록 잡은 앞 가장자리 거리. */
const CONCEPT_BEAM_DISTANCE = 197;
const CONCEPT_MOVERS_PER_ROW = 8;

export type ConceptSlot = "back" | "blind" | "u" | "d" | "side-l" | "side-r" | "wash" | "foh";

export interface ConceptSlotState {
  slot: ConceptSlot;
  /** 그 자리를 맡는 줄의 순번(`tracks` 안). 맡는 줄이 없으면 `null`. */
  trackIndex: number | null;
  lit: boolean;
  color: string;
}

function indexesOfRole(tracks: readonly BeatGridTrack[], role: string): number[] {
  return tracks.flatMap((track, index) => (track.layer_role === role ? [index] : []));
}

/** 개념도 자리마다 맡는 줄과 지금 마디의 상태(리드 결정).
 * - U/D: 무빙 줄의 첫째가 위(U), 둘째가 아래(D).
 * - BACK·WASH·FOH: 그 층 역할의 첫 줄.
 * - SIDE-L/R: 측면 줄의 첫째·둘째. 측면 줄이 하나면 양쪽이 그 줄을 따른다.
 * - BLIND: 무빙이 아닌 효과(effect) 줄의 첫째. */
export function conceptSlots(tracks: readonly BeatGridTrack[], viewBar: number): ConceptSlotState[] {
  const movers = indexesOfRole(tracks, "mover");
  const sides = indexesOfRole(tracks, "side");
  const picks: Record<ConceptSlot, number | undefined> = {
    back: indexesOfRole(tracks, "back")[0],
    blind: indexesOfRole(tracks, "effect")[0],
    u: movers[0],
    d: movers[1],
    "side-l": sides[0],
    "side-r": sides[1] ?? sides[0],
    wash: indexesOfRole(tracks, "wash")[0],
    foh: indexesOfRole(tracks, "key")[0],
  };
  return (Object.keys(picks) as ConceptSlot[]).map((slot) => {
    const trackIndex = picks[slot] ?? null;
    if (trackIndex === null) return { slot, trackIndex, lit: false, color: OFF_FIXTURE_COLOR };
    const track = tracks[trackIndex];
    return {
      slot,
      trackIndex,
      lit: trackIsLitAt(track, viewBar),
      color: trackStageColor(track, trackIndex, viewBar),
    };
  });
}

export function StageConceptSvg({
  width,
  height,
  tracks = [],
  viewBar = 0,
  selectedTrackName = null,
  selectedRows = [],
  onSelectTrack,
  motion,
  presetBook,
}: {
  /** 재생 시계 — 있으면 무빙 빔이 칸의 움직임대로 돈다(장비 좌표 무대와 같은 계산). */
  motion?: { seconds: number; secondsPerBar: number | null | undefined; beatsPerBar: number | null };
  /** 곡 격자의 프리셋 기록(이름·효과 내용). */
  presetBook?: StagePresetBook;
  width: number;
  height: number;
  /** 줄 목록 — 자리를 맡는 줄의 층 역할·상태·색을 정한다. 없으면 모든 자리가 꺼진 회색이다. */
  tracks?: readonly BeatGridTrack[];
  viewBar?: number;
  selectedTrackName?: string | null;
  /** 무대에서 고른 줄들(트랙 번호) — 여기 든 자리는 모두 노란 점선으로 둘린다. */
  selectedRows?: readonly number[];
  /** 자리나 이름표를 누르면 그 자리를 맡는 줄을 고른다(줄 편집). `additive` 는 Shift 를 누른 채 눌렀을 때 참 — 고른 줄에 더하거나 뺀다. */
  onSelectTrack?: (trackIndex: number, additive?: boolean) => void;
}) {
  const W = width;
  const H = height;
  const L0 = 60;
  const R0 = W - 60;
  const SW = R0 - L0;
  const slots = conceptSlots(tracks, viewBar);
  const stateOf = (slot: ConceptSlot): ConceptSlotState =>
    slots.find((s) => s.slot === slot) ?? { slot, trackIndex: null, lit: false, color: OFF_FIXTURE_COLOR };
  const selectedIndex = selectedTrackName === null ? -1 : tracks.findIndex((t) => t.group_name === selectedTrackName);
  // 시안 `row(n, a, b)` — n개를 a~b 사이에 고르게.
  const row = (n: number, a: number, b: number) =>
    Array.from({ length: n }, (_, i) => a + (b - a) * (n === 1 ? 0.5 : i / (n - 1)));
  const lamp = (x: number, y: number, r: number, key: string, fill: string) => (
    <circle key={key} cx={x} cy={y} r={r} fill={fill} />
  );
  // 무빙 한 대: 켜진 무빙만 빔 삼각형(시안 `mv`). 헤드 사각형은 줄 색(꺼짐 = #333).
  // 빔 각도·길이는 그 줄 지금 칸의 위치·움직임과 재생 시각에서(`moverBeamPoints`).
  const movingHead = (slot: "u" | "d", x: number, y: number, index: number) => {
    const state = stateOf(slot);
    const track = state.trackIndex === null ? null : tracks[state.trackIndex];
    const points = moverBeamPoints({
      cue: track ? cueForBar(track, viewBar) : null,
      x,
      y,
      distance: CONCEPT_BEAM_DISTANCE,
      centreX: W / 2,
      index,
      count: CONCEPT_MOVERS_PER_ROW,
      halfWidth: 9,
      clock: motion,
      book: presetBook,
    });
    return (
      <g key={`m${slot}${index}`}>
        {state.lit && <polygon className="beat-grid-stage-beam" points={points} fill={state.color} opacity={0.4} />}
        <rect className="beat-grid-stage-mover" x={x - 5} y={y - 5} width={10} height={10} fill={state.color} />
      </g>
    );
  };
  const label = (x: number, y: number, text: string, anchor: "start" | "middle" | "end" = "start") => (
    <text key={`${text}-${x}-${y}`} x={x} y={y} fontSize={10} fill="#8a889a" textAnchor={anchor}>
      {text}
    </text>
  );
  // 자리 하나의 묶음 — 맡는 줄이 있으면 누를 수 있고(이름표도), 고른 줄이면 노란 점선 테두리를 두른다.
  // 고른 줄 = 편집 칸의 줄(`selectedIndex`)이거나 무대에서 고른 줄(`selectedRows`).
  const slotGroup = (
    slot: ConceptSlot,
    box: { x: number; y: number; width: number; height: number },
    children: ReactNode,
  ) => {
    const state = stateOf(slot);
    const index = state.trackIndex;
    const track = index === null ? null : tracks[index];
    const selected = index !== null && (index === selectedIndex || selectedRows.includes(index));
    const onClick =
      index !== null && onSelectTrack
        ? (event: ReactMouseEvent<SVGGElement>) => onSelectTrack(index, event.shiftKey)
        : undefined;
    // 맡는 줄이 이 마디에 칸이 없으면 눌러도 아무 일이 없다 — 그 사실을 이름표 대신 말한다.
    const hint = track && cueForBar(track, viewBar) ? "눌러서 편집" : "이 마디에는 칸이 없어요";
    return (
      <g
        key={`slot-${slot}`}
        className={`beat-grid-stage-slot${selected ? " on" : ""}`}
        onClick={onClick}
        style={onClick ? { cursor: "pointer" } : undefined}
      >
        {track && <title>{`${track.group_name} — ${hint}`}</title>}
        {children}
        {selected && (
          <rect
            x={box.x}
            y={box.y}
            width={box.width}
            height={box.height}
            rx={4}
            fill="none"
            stroke="#ffd84d"
            strokeWidth={2}
            strokeDasharray="5 3"
          />
        )}
      </g>
    );
  };
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="beat-grid-stage beat-grid-stage-concept" role="img" aria-label="무대 개념도">
      <rect width={W} height={H} fill="#101014" />
      {/* 워시 면 — 시안 `ZB.wash` 자리 */}
      <rect x={L0} y={70} width={SW} height={170} fill="#1b1b22" stroke="#333" />
      {slotGroup("wash", { x: L0 - 4, y: 66, width: SW + 8, height: 178 }, [
        ...row(10, L0 + 22, R0 - 22).map((x, i) => lamp(x, 226, 5, `wf${i}`, stateOf("wash").color)),
        ...row(10, L0 + 22, R0 - 22).map((x, i) => lamp(x, 86, 5, `wb${i}`, stateOf("wash").color)),
        label(L0 + 6, 250, "WASH"),
      ])}
      {slotGroup("foh", { x: L0 + 30, y: 252, width: SW - 60, height: 24 }, [
        ...row(8, L0 + 60, R0 - 60).map((x, i) => lamp(x, 264, 5, `fo${i}`, stateOf("foh").color)),
        label(L0 + 44, 284, "FOH"),
      ])}
      {slotGroup("back", { x: L0 - 10, y: 18, width: SW + 20, height: 24 }, [
        ...row(12, L0 + 10, R0 - 10).map((x, i) => lamp(x, 30, 6, `ba${i}`, stateOf("back").color)),
        label(L0, 16, "BACK"),
      ])}
      {slotGroup("side-l", { x: 14, y: 84, width: 28, height: 136 }, [
        ...row(6, 92, 212).map((y, i) => lamp(28, y, 6, `sl${i}`, stateOf("side-l").color)),
        label(14, 76, "SIDE-L"),
      ])}
      {slotGroup("side-r", { x: W - 42, y: 84, width: 28, height: 136 }, [
        ...row(6, 92, 212).map((y, i) => lamp(W - 28, y, 6, `sr${i}`, stateOf("side-r").color)),
        label(W - 14, 76, "SIDE-R", "end"),
      ])}
      {slotGroup("u", { x: L0 + 18, y: 44, width: SW - 36, height: 22 }, [
        ...row(CONCEPT_MOVERS_PER_ROW, L0 + 30, R0 - 30).map((x, i) => movingHead("u", x, 54, i)),
        label(L0 - 14, 58, "U", "end"),
      ])}
      {slotGroup("d", { x: L0 + 18, y: 110, width: SW - 36, height: 22 }, [
        ...row(CONCEPT_MOVERS_PER_ROW, L0 + 30, R0 - 30).map((x, i) => movingHead("d", x, 120, i)),
        label(L0 - 14, 124, "D", "end"),
      ])}
      {slotGroup("blind", { x: W / 2 - 120, y: 33, width: 240, height: 16 }, [
        ...row(6, W / 2 - 110, W / 2 + 110).map((x, i) => (
          <rect key={`bl${i}`} x={x - 9} y={41} width={18} height={8} fill={stateOf("blind").color} />
        )),
        label(W / 2, 36, "BLIND", "middle"),
      ])}
    </svg>
  );
}
