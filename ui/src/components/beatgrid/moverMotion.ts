// 2D 무대 무빙 빔 움직임 — 재생 시계(#755 `playbackClock`)의 지금 시각에서 무빙 칸을 읽어
// 빔 각도를 계산한다. 이 모듈은 DOM·`requestAnimationFrame` 을 만지지 않는 순수 함수다
// (`playbackClock.ts` 와 같은 경계) — 매 프레임 다시 그리는 것은 `BeatGrid.tsx` 의 재생 루프가
// `playbackSeconds` 를 갱신하는 것으로 이미 된다.
//
// 움직임은 구조화 값에서만 읽는다: 앱 2단계 무빙(`app_movement`)이 먼저, 다음은 칸의 방향 값
// (`direction.movement`), 없으면 효과 번호의
// 격자 기록(`preset_movements`)·앱 이름(`preset_labels`)·콘솔 이름(`effect_preset_name`) 순서
// (이름은 서버 `_effect_name` 꼴 「WAVE PAN 2 BEAT」).
// 라벨 글자는 파싱하지 않는다(REQ-LDBEAT-006(ii-2)). 주기를 모르면 움직이지 않는다(지어내지 않음).
import type { BeatGridAppMovement, BeatGridCue, BeatGridPresetMovement } from "../../protocol";

export type MoverShape = NonNullable<BeatGridAppMovement["shape"]>;

export interface MoverMotion {
  shape: MoverShape;
  pan: boolean;
  tilt: boolean;
  /** 한 바퀴의 마디 수. */
  periodBars: number;
  /** 장비마다 위상을 엇갈리게 하는가 — 칸이 `false` 라고 할 때만 끈다. */
  phaseSpread: boolean;
}

/** 빔 자세 — `panDeg` 는 무대 앞쪽(화면 아래)에서 돌아간 각도(+ 는 화면 오른쪽),
 * `reach` 는 장비에서 무대 앞 가장자리까지 거리의 비율(틸트를 평면에 눕힌 값). */
export interface BeamPose {
  panDeg: number;
  reach: number;
}

/** 위치를 모를 때의 빔 길이 — 기존 고정 빔(`BEAM_REACH`)과 같다. */
export const DEFAULT_REACH = 0.5;
/** 팬 움직임 폭(도)과 틸트 움직임 폭(reach 의 비율). 그림 값이다(콘솔 값이 아니다). */
export const PAN_SWING_DEG = 30;
export const TILT_SWING = 0.4;

const SHAPES: readonly MoverShape[] = ["sweep", "flyout", "circle", "ballyhoo", "wave"];

function periodBarsOf(unit: "beat" | "bar" | null, value: number | null, beatsPerBar: number | null): number | null {
  if (value === null || !Number.isFinite(value) || value <= 0) return null;
  if (unit === "bar") return value;
  if (unit === "beat") return beatsPerBar && beatsPerBar > 0 ? value / beatsPerBar : null;
  return null;
}

/** 효과 프리셋 콘솔 이름(「WAVE PAN 2 BEAT」·「CIRCLE PAN+TILT 1 BAR」) → 모양·축·주기.
 * 서버 `preset_plan._effect_name` 이 만드는 꼴만 읽는다. 맞지 않으면 `null`. */
export function parseEffectPresetName(
  name: string | null | undefined,
): { shape: MoverShape; pan: boolean; tilt: boolean; unit: "beat" | "bar" | null; value: number | null } | null {
  if (!name) return null;
  const match = /^\s*(?:LA\s+)?([A-Z]+)\s+((?:PAN|TILT)(?:\+(?:PAN|TILT))?)(?:\s+(\d+(?:\.\d+)?)\s+(BEAT|BAR)S?)?\s*$/i.exec(
    name,
  );
  if (!match) return null;
  const shape = match[1].toLowerCase() as MoverShape;
  if (!SHAPES.includes(shape)) return null;
  const axes = match[2].toUpperCase().split("+");
  return {
    shape,
    pan: axes.includes("PAN"),
    tilt: axes.includes("TILT"),
    unit: match[4] ? (match[4].toLowerCase() as "beat" | "bar") : null,
    value: match[3] ? Number(match[3]) : null,
  };
}

/** 곡 격자의 프리셋 기록 — 칸에 이름이 안 실려도(서버가 풀을 못 읽었어도) 앱이 만든 프리셋의
 * 이름·내용은 격자에 남아 있다(`preset_labels`·`preset_movements`). */
export interface StagePresetBook {
  labels?: Readonly<Record<string, string | null | undefined>> | null;
  movements?: Readonly<Record<string, BeatGridPresetMovement | null | undefined>> | null;
}

function motionFrom(
  shape: unknown,
  axes: readonly unknown[],
  unit: unknown,
  value: unknown,
  spread: unknown,
  beatsPerBar: number | null,
): MoverMotion | null {
  if (typeof shape !== "string" || !SHAPES.includes(shape as MoverShape)) return null;
  const upper = axes.map((axis) => String(axis).toUpperCase());
  const pan = upper.includes("PAN");
  const tilt = upper.includes("TILT");
  const periodBars = periodBarsOf(
    unit === "beat" || unit === "bar" ? unit : null,
    typeof value === "number" ? value : null,
    beatsPerBar,
  );
  if (periodBars === null || (!pan && !tilt)) return null;
  return { shape: shape as MoverShape, pan, tilt, periodBars, phaseSpread: spread !== false };
}

/** 칸의 움직임. 근거 순서: ① 칸의 `app_movement` ② 칸의 방향 값 `direction.movement` ③ 효과 번호의
 * 격자 기록(`preset_movements` 서명) ④ 효과 번호의 앱 이름(`preset_labels`) ⑤ 콘솔이 준 이름
 * (`effect_preset_name`).
 * 라벨 글자는 읽지 않는다. 근거가 없거나 주기·축을 모르면 `null`(빔은 위치 자세로 멈춰 있다). */
export function moverMotionOf(
  cue: BeatGridCue | null,
  beatsPerBar: number | null,
  book: StagePresetBook = {},
): MoverMotion | null {
  if (!cue) return null;
  const app = cue.app_movement;
  if (app && app.shape) {
    return motionFrom(app.shape, app.axes, app.period_unit, app.period_value, app.phase_spread, beatsPerBar);
  }
  // 칸의 방향 값(자동 배치가 칸마다 낸 결정)이 움직임을 말하면 프리셋 기록보다 먼저 읽는다.
  const moving = cue.direction?.movement;
  if (moving && moving.shape) {
    return motionFrom(moving.shape, moving.axes, moving.period_unit, moving.period_value, moving.phase_spread, beatsPerBar);
  }
  const no = cue.effect_preset_no;
  if (!no) return null;
  const signature = book.movements?.[no]?.signature;
  if (Array.isArray(signature) && signature.length >= 4) {
    const [shape, axes, unit, value, spread] = signature;
    const motion = motionFrom(shape, Array.isArray(axes) ? axes : [], unit, value, spread, beatsPerBar);
    if (motion) return motion;
  }
  for (const name of [book.labels?.[no], cue.effect_preset_name]) {
    const parsed = parseEffectPresetName(name);
    if (!parsed) continue;
    const periodBars = periodBarsOf(parsed.unit, parsed.value, beatsPerBar);
    if (periodBars !== null) return { shape: parsed.shape, pan: parsed.pan, tilt: parsed.tilt, periodBars, phaseSpread: true };
  }
  return null;
}

/** 위치 이름 안의 기본 위치 낱말. 이름은 「CENTER MOVER-U」·「2.33 CENTER MOVER-U」·「LA Home」처럼
 * 번호·그룹이 붙어 오므로 낱말 단위로 찾는다. FLOOR 는 서버 기본 위치 Home(「바닥 쪽」)과 같다. */
const POSITION_WORDS: readonly [RegExp, "home" | "center" | "ring" | "audience"][] = [
  [/\bRING\s*IN\b/, "ring"],
  [/\bAUDIENCE\b/, "audience"],
  [/\bCENT(?:ER|RE)\b/, "center"],
  [/\b(?:HOME|FLOOR)\b/, "home"],
];

export function positionWordOf(name: string | null | undefined): "home" | "center" | "ring" | "audience" | null {
  if (!name) return null;
  const upper = name.toUpperCase();
  for (const [pattern, word] of POSITION_WORDS) if (pattern.test(upper)) return word;
  return null;
}

/** 위치 이름 → 기본 자세. 앱 기본 위치 어휘(서버 `preset_plan` 의 Home·Center·Ring In·Audience)만
 * 안다. 이름 근거 순서: 콘솔 이름(`position_preset_name`) → 위치 번호의 앱 이름(`preset_labels`) →
 * 계획 위치(`planned_position_name`). `centrePanDeg` 는 무대 가운데를 보는 팬 각도(Center 에만). */
export function basePoseOf(cue: BeatGridCue | null, centrePanDeg: number, book: StagePresetBook = {}): BeamPose {
  const names = [
    cue?.position_preset_name,
    cue?.position_preset_no ? book.labels?.[cue.position_preset_no] : null,
    cue?.planned_position_name,
  ];
  const word = names.map(positionWordOf).find((w) => w !== null) ?? null;
  if (word === "home") return { panDeg: 0, reach: 0.15 };
  if (word === "center") return { panDeg: centrePanDeg, reach: DEFAULT_REACH };
  if (word === "ring") return { panDeg: 0, reach: 0.25 };
  if (word === "audience") return { panDeg: 0, reach: 1 };
  return { panDeg: 0, reach: DEFAULT_REACH };
}

/** 장비 순번(같은 줄 무빙 안 0..count-1)의 위상 엇갈림 — 한 바퀴의 비율. */
export function phaseOffset(index: number, count: number, spread: boolean): number {
  if (!spread || count <= 1) return 0;
  return index / count;
}

function triangle(phase: number): number {
  const p = phase - Math.floor(phase);
  return p < 0.5 ? 4 * p - 1 : 3 - 4 * p;
}

/** 지금 시각(초)의 빔 자세. `motion` 이 없으면 기본 자세 그대로. `side` 는 장비가 무대 가운데
 * 왼쪽(-1)·오른쪽(+1)·가운데(0) 중 어디인가(flyout 이 바깥으로 벌어지는 방향). */
export function beamPoseAt(
  base: BeamPose,
  motion: MoverMotion | null,
  seconds: number,
  secondsPerBar: number | null | undefined,
  offset: number,
  side: number,
): BeamPose {
  if (!motion || !secondsPerBar || !Number.isFinite(secondsPerBar) || secondsPerBar <= 0) return base;
  const phase = seconds / secondsPerBar / motion.periodBars + offset;
  const turn = 2 * Math.PI * phase;
  let pan = 0;
  let tilt = 0;
  switch (motion.shape) {
    case "wave":
      pan = Math.sin(turn);
      tilt = Math.sin(turn);
      break;
    case "sweep":
      pan = triangle(phase);
      tilt = triangle(phase);
      break;
    case "circle":
      pan = Math.sin(turn);
      tilt = Math.cos(turn);
      break;
    case "ballyhoo":
      pan = Math.sin(turn);
      tilt = Math.sin(2 * turn);
      break;
    case "flyout":
      pan = (side === 0 ? 1 : side) * (0.5 + 0.5 * Math.sin(turn));
      tilt = 0.5 + 0.5 * Math.sin(turn);
      break;
  }
  return {
    panDeg: base.panDeg + (motion.pan ? pan * PAN_SWING_DEG : 0),
    reach: Math.max(0.05, base.reach * (1 + (motion.tilt ? tilt * TILT_SWING : 0))),
  };
}

/** 빔 삼각형 — 장비 점에서 팬 각도로 `length` 만큼 뻗고 끝의 반폭이 `halfWidth`. SVG `points` 글. */
export function beamPolygonPoints(cx: number, cy: number, panDeg: number, length: number, halfWidth: number): string {
  const rad = (panDeg * Math.PI) / 180;
  const dx = Math.sin(rad);
  const dy = Math.cos(rad);
  const ex = cx + dx * length;
  const ey = cy + dy * length;
  const round = (v: number) => Math.round(v * 100) / 100;
  return `${round(cx)},${round(cy)} ${round(ex - dy * halfWidth)},${round(ey + dx * halfWidth)} ${round(ex + dy * halfWidth)},${round(ey - dx * halfWidth)}`;
}

/** 무빙 한 대의 빔 삼각형 — 칸의 위치·움직임과 재생 시각에서(장비 좌표 무대·개념도 무대가 같이 쓴다).
 * `distance` 는 장비에서 무대 앞 가장자리까지(reach 1), `index`/`count` 는 같은 줄 안의 순번(위상 엇갈림). */
export function moverBeamPoints(args: {
  cue: BeatGridCue | null;
  x: number;
  y: number;
  distance: number;
  centreX: number;
  index: number;
  count: number;
  halfWidth: number;
  clock?: { seconds: number; secondsPerBar: number | null | undefined; beatsPerBar: number | null };
  book?: StagePresetBook;
}): string {
  const { cue, x, y, distance, centreX, index, count, halfWidth, clock, book = {} } = args;
  const motion = clock ? moverMotionOf(cue, clock.beatsPerBar, book) : null;
  const pose = beamPoseAt(
    basePoseOf(cue, centrePanDegOf(x, y, centreX, y + distance), book),
    motion,
    clock?.seconds ?? 0,
    clock?.secondsPerBar,
    phaseOffset(index, count, motion?.phaseSpread ?? true),
    Math.sign(Math.round(x - centreX)),
  );
  return beamPolygonPoints(x, y, pose.panDeg, distance * pose.reach, halfWidth);
}

/** 장비에서 무대 가운데(`centreX`, 앞 가장자리 `frontY` 쪽)를 보는 팬 각도. */
export function centrePanDegOf(cx: number, cy: number, centreX: number, frontY: number): number {
  const down = Math.max(1, frontY - cy);
  return (Math.atan2(centreX - cx, down) * 180) / Math.PI;
}
