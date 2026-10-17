// 박자 격자 — 전환(이음매)·장면 전환·콘솔 명령 미리보기·2D 무대 그룹 영역의
// 순수 계산(SPEC-LDBEAT-001 M9 step 3·4·5, 카드 t561, REQ-LDBEAT-020·021·022).
//
// 정본은 `.moai/specs/SPEC-LDBEAT-001/design/ldbeat-runbook-ui-proposal-
// 20261008.html`의 `mibOf`·`warnOf`·`fadeLbl`·`clipsHTML`(이음매)·`drawTr`
// (장면 전환)·`cueLines`(콘솔 명령) — 이 파일은 그 판단을 이 저장소의 실제
// 데이터 모양(`BeatGridCue`)으로 옮긴다. 카드 t574(SPEC 0.5.0)부터 트리거 박·
// 딜레이·위치만 따로·트래킹·박 페이드도 `entry` 에 저장된다(전부 박 단위). 시안의
// 「이유」는 여전히 저장 칸이 없어 지어내지 않는다.
import type { BeatGridCue, BeatGridEntry, BeatGridTrack } from "../protocol";
import type { BeatGridFixturePoint } from "./BeatGrid";
import { fixtureBelongsTo } from "./beatGridStageModel";

/** REQ-LDBEAT-020(a) 문면 「3줄 이상이 같은 마디에서 동시에 바뀌는 동안」. */
export const SCENE_CHANGE_MIN_ROWS = 3;

const UNSET = "미정";

/** 시안 `beatsToS`·`tc` 와 같은 표기 — 소수 둘째 자리로 맞춘 뒤 뒤의 0을 뗀다(2.00 → 2, 2.50 → 2.5). 표시 전용. */
export function trimSeconds(seconds: number): string {
  return seconds.toFixed(2).replace(/\.?0+$/, "");
}

/** REQ-LDBEAT-020(e) — 초를 먼저, 마디는 괄호. 저장값(`fade_bars`)은 바꾸지
 * 않는 표시 전용 변환이다. 곡 BPM(1마디 초)이 없으면 초를 지어내지 않는다. */
export function formatFadeSecondsFirst(fadeBars: number | null, secondsPerBar: number | null | undefined): string {
  if (fadeBars === null) return UNSET;
  if (fadeBars === 0) return "끊기 (0초)";
  if (secondsPerBar === null || secondsPerBar === undefined) return `— 초 (${fadeBars}마디)`;
  return `${trimSeconds(fadeBars * secondsPerBar)}초 (${fadeBars}마디)`;
}

/** 곡 박자표(`"4/4"`)에서 한 마디 박 수. 모르면 `null` — 4를 지어내지 않는다. */
export function parseBeatsPerBar(timeSignature: string | null | undefined): number | null {
  const match = /^\s*(\d+)\s*\/\s*\d+\s*$/.exec(timeSignature ?? "");
  if (!match) return null;
  const beats = Number(match[1]);
  return beats > 0 ? beats : null;
}

/** 카드 t574 — 서버는 `entry` 를 통째로 바꾸므로, 화면이 한 필드만 고쳐도 나머지
 * 필드를 함께 보내야 지워지지 않는다. 없는 필드는 `null`(미정)로 채운다. */
export type FullBeatGridEntry = Required<{ [K in keyof BeatGridEntry]: NonNullable<BeatGridEntry[K]> | null }>;

export function entryWith(entry: BeatGridEntry, patch: Partial<FullBeatGridEntry> = {}): FullBeatGridEntry {
  return {
    fade_bars: entry.fade_bars ?? null,
    mib_mode: entry.mib_mode ?? null,
    fade_beats: entry.fade_beats ?? null,
    trigger_beat: entry.trigger_beat ?? null,
    delay_beats: entry.delay_beats ?? null,
    position_late_beats: entry.position_late_beats ?? null,
    tracking: entry.tracking ?? null,
    ...patch,
  };
}

/** 페이드 입력(마디 또는 박) → 저장 필드. REQ-LDBEAT-020(e)(카드 t566 재교정):
 * 박 입력이 마디당 박 수의 정수배면 `fade_bars`, 아니면 `fade_beats` 로 —
 * 둘 중 하나만 채운다(REQ-LDBEAT-006(i-4a)). 초는 저장하지 않는다. */
export function fadeDraftToEntry(
  draft: string,
  unit: "bar" | "beat",
  beatsPerBar: number | null,
): { fade?: { fade_bars: number | null; fade_beats: number | null }; error?: string } {
  const trimmed = draft.trim();
  if (trimmed === "") return { error: "값을 넣어 주세요." };
  const value = Number(trimmed);
  if (!Number.isFinite(value) || value < 0) return { error: "0 이상의 숫자여야 합니다." };
  if (!Number.isInteger(value)) return { error: unit === "beat" ? "박은 정수로 넣어 주세요." : "마디는 정수로 넣어 주세요." };
  if (unit === "bar") return { fade: { fade_bars: value, fade_beats: null } };
  if (beatsPerBar === null) return { error: "곡 박자표(한 마디 박 수)를 몰라 박을 쓸 수 없습니다." };
  return value % beatsPerBar === 0
    ? { fade: { fade_bars: value / beatsPerBar, fade_beats: null } }
    : { fade: { fade_bars: null, fade_beats: value } };
}

/** 페이드 표시 — 박 페이드면 「1.07초 (2박)」, 마디 페이드면 기존 표시. */
export function formatEntryFade(
  entry: BeatGridEntry,
  secondsPerBar: number | null | undefined,
  beatsPerBar: number | null,
): string {
  const beats = entry.fade_beats ?? null;
  if (beats === null) return formatFadeSecondsFirst(entry.fade_bars, secondsPerBar);
  if (beats === 0) return "끊기 (0초)";
  if (secondsPerBar === null || secondsPerBar === undefined || beatsPerBar === null) return `— 초 (${beats}박)`;
  return `${trimSeconds((beats * secondsPerBar) / beatsPerBar)}초 (${beats}박)`;
}

/** 끊어 바꿈(0) — 두 단위 중 정해진 쪽이 0일 때. 미정은 끊기가 아니다. */
export function entryFadeIsCut(entry: BeatGridEntry): boolean {
  return entry.fade_bars === 0 || entry.fade_beats === 0;
}

/** 페이드가 0보다 긴지(◢ 표시·번짐). */
export function entryHasFade(entry: BeatGridEntry): boolean {
  return (entry.fade_bars ?? 0) > 0 || (entry.fade_beats ?? 0) > 0;
}

/** 페이드 길이를 마디로(번짐 폭·CueFade 초 환산용). 박 페이드인데 박자표를
 * 모르면 `null`. */
export function entryFadeInBars(entry: BeatGridEntry, beatsPerBar: number | null): number | null {
  if (entry.fade_beats !== null && entry.fade_beats !== undefined) {
    return beatsPerBar === null ? null : entry.fade_beats / beatsPerBar;
  }
  return entry.fade_bars;
}

/** 트리거 시각(곡 0초 기준) — 마디 + (트리거 박 - 1) / 마디당 박 수. 박을 정했는데
 * 박자표를 모르면 지어내지 않고 `null`. */
export function triggerSeconds(
  cue: BeatGridCue,
  secondsPerBar: number | null | undefined,
  beatsPerBar: number | null,
  barOriginSeconds: number | null | undefined = 0,
): number | null {
  if (secondsPerBar === null || secondsPerBar === undefined) return null;
  // 0마디가 시작하는 곡 시각(서버 `bar_origin_seconds`, 콘솔 큐와 같은 기준) — 없으면 0초.
  const origin = typeof barOriginSeconds === "number" && Number.isFinite(barOriginSeconds) ? barOriginSeconds : 0;
  const beat = cue.entry.trigger_beat ?? null;
  if (beat === null) return Math.max(0, origin + cue.bar * secondsPerBar);
  if (beatsPerBar === null) return null;
  return Math.max(0, origin + (cue.bar + (beat - 1) / beatsPerBar) * secondsPerBar);
}

/** 칸이 켜져 있는지 — 배치 규칙서의 「—」 관례(`cueIsActive`와 같은 판단)에
 * 밝기 값 0%를 꺼짐으로 더한다(시안 `bright(s)===0`과 같은 뜻). */
export function cueIsLit(cue: BeatGridCue): boolean {
  if (cue.brightness.mode === "value" && cue.brightness.value_percent === 0) return false;
  const label = cue.label.trim();
  return label !== "" && label !== "—";
}

/** 그 마디 칸 바로 앞 칸(들어오는 전환의 "앞 큐"). 첫 칸이면 `null`. */
export function previousCue(track: BeatGridTrack, bar: number): BeatGridCue | null {
  const index = track.cues.findIndex((c) => c.bar === bar);
  return index > 0 ? track.cues[index - 1] : null;
}

export interface TransitionMib {
  kind: "first" | "none" | "auto" | "lit";
  text: string;
}

/** 시안 `mibOf` — 위치가 바뀌는 전환에서 MIB(어둠 속 미리 이동)가 되는지. */
export function transitionMib(prev: BeatGridCue | null, cur: BeatGridCue): TransitionMib {
  if (!prev) return { kind: "first", text: "곡 첫 큐" };
  if (cur.position_preset_no === null || prev.position_preset_no === cur.position_preset_no) {
    return { kind: "none", text: "위치 안 바뀜 — MIB 필요 없음" };
  }
  if (!cueIsLit(prev)) {
    return { kind: "auto", text: "앞 큐가 꺼져 있음 → 어둠 속에서 미리 이동(위치 전용 큐 삽입)" };
  }
  return { kind: "lit", text: "앞 큐가 켜져 있어 MIB 불가 — 켜진 채 이동(페이드로 보이게)" };
}

/** 시안 `warnOf` — [제안] 경고(규칙서 §2.3 규칙 2). 페이드가 미정이거나
 * 구간 경계를 모르면 그 판정은 하지 않는다(모르는 것을 경고로 만들지 않음).
 * 카드 t567 — 시안처럼 강조(★) 마디(곡 데이터 `accentBars`)에선 켜진 채 위치
 * 끊김을 경고하지 않는다(히트는 끊기). ★ 예외는 위치 경고에만 걸린다. */
export function transitionWarnings(
  prev: BeatGridCue | null,
  cur: BeatGridCue,
  sectionStartBars: readonly number[] | null,
  accentBars: readonly number[] = [],
): string[] {
  if (!prev || !entryFadeIsCut(cur.entry)) return [];
  const warnings: string[] = [];
  if (
    cur.position_preset_no !== null &&
    prev.position_preset_no !== cur.position_preset_no &&
    cueIsLit(prev) &&
    !accentBars.includes(cur.bar)
  ) {
    warnings.push("켜진 채 위치가 끊어 바뀜");
  }
  if (
    sectionStartBars !== null &&
    sectionStartBars.length > 0 &&
    cur.color_preset_no !== null &&
    prev.color_preset_no !== cur.color_preset_no &&
    !sectionStartBars.includes(cur.bar)
  ) {
    warnings.push("구간 경계가 아닌데 색이 끊어 바뀜");
  }
  return warnings;
}

export interface JointMarker {
  glyph: "M" | "!" | "◢" | "";
  classes: string[];
  title: string;
}

/** 시안 `clipsHTML`의 `.jt` — MIB 자동이면 M, 경고면 !, 페이드면 ◢.
 * 곡의 첫 칸이면 `prev` 는 null — 앞이 없으니 MIB·경고는 판정하지 않고 페이드만 본다. */
export function jointMarker(
  prev: BeatGridCue | null,
  cur: BeatGridCue,
  sectionStartBars: readonly number[] | null,
  secondsPerBar: number | null = null,
  beatsPerBar: number | null = null,
  accentBars: readonly number[] = [],
): JointMarker {
  const mib = transitionMib(prev, cur);
  const warnings = transitionWarnings(prev, cur, sectionStartBars, accentBars);
  const hasFade = entryHasFade(cur.entry);
  const classes: string[] = [];
  if (hasFade) classes.push("is-fade");
  if (mib.kind === "auto") classes.push("is-mib");
  if (warnings.length) classes.push("is-warn");
  const glyph = mib.kind === "auto" ? "M" : warnings.length ? "!" : hasFade ? "◢" : "";
  const title =
    `전환 ${cur.bar}마디 · 페이드 ${formatEntryFade(cur.entry, secondsPerBar, beatsPerBar)}` +
    (warnings.length ? ` · ⚠ [제안] ${warnings.join(" · ")}` : "") +
    " — 누르면 전환 편집";
  return { glyph, classes, title };
}

export interface SceneChangeRow {
  track: BeatGridTrack;
  trackIndex: number;
  cue: BeatGridCue;
  prev: BeatGridCue | null;
}

/** 그 마디에서 새 칸이 시작하는(=바뀌는) 줄들. */
export function sceneChangeRows(tracks: readonly BeatGridTrack[], bar: number): SceneChangeRow[] {
  const rows: SceneChangeRow[] = [];
  tracks.forEach((track, trackIndex) => {
    const cue = track.cues.find((c) => c.bar === bar);
    if (cue) rows.push({ track, trackIndex, cue, prev: previousCue(track, bar) });
  });
  return rows;
}

/** REQ-LDBEAT-020(a) — 3줄 이상이 동시에 바뀌는 마디(곡 첫 마디 제외). */
export function sceneChangeBars(
  tracks: readonly BeatGridTrack[],
  firstBar: number,
): { bar: number; count: number }[] {
  const counts = new Map<number, number>();
  for (const track of tracks) {
    for (const cue of track.cues) {
      if (cue.bar <= firstBar) continue;
      counts.set(cue.bar, (counts.get(cue.bar) ?? 0) + 1);
    }
  }
  return [...counts.entries()]
    .filter(([, count]) => count >= SCENE_CHANGE_MIN_ROWS)
    .sort(([a], [b]) => a - b)
    .map(([bar, count]) => ({ bar, count }));
}

function groupSelection(track: BeatGridTrack): string {
  return track.group_no_confirmed && track.group_no !== null
    ? `Group ${track.group_no}`
    : `Group <번호 미확인 '${track.group_name}'>`;
}

/** 큐 편집 화면의 「콘솔 명령」 미리보기 — `server/design/beat_grid_emit.py`
 * `_cue_attribute_commands`와 같은 줄 꼴(`Group <번호> ; At Preset <번호>`).
 * 디머 속성 목록·앱 무빙 줄은 송신 때 서버가 정하므로 그 자리만 표시한다.
 * 실제 송신은 「⇪ 콘솔에 반영」 경로이고, 이 미리보기는 아무것도 보내지
 * 않는다. */
export function cueConsoleCommandLines(track: BeatGridTrack, cue: BeatGridCue): string[] {
  const sel = groupSelection(track);
  const lines: string[] = [];
  if (cue.app_movement?.shape) {
    lines.push(`(앱 무빙 ${cue.app_movement.shape} — 줄은 송신 때 서버가 곡 BPM으로 만듦)`);
  } else if (cue.position_preset_no !== null) {
    lines.push(`${sel} ; At Preset ${cue.position_preset_no}`);
  }
  if (cue.color_preset_no !== null) lines.push(`${sel} ; At Preset ${cue.color_preset_no}`);
  if (cue.effect_preset_no !== null) lines.push(`${sel} ; At Preset ${cue.effect_preset_no}`);
  const { mode, value_percent, preset_no } = cue.brightness;
  if (mode === "value" && value_percent !== null) {
    lines.push(`${sel} ; Attribute <디머 속성마다 한 줄> At ${value_percent}`);
  } else if ((mode === "dimmer_preset" || mode === "dimmer_effect") && preset_no !== null) {
    lines.push(`${sel} ; At Preset ${preset_no}`);
  }
  if (lines.length === 0) return ["(이 칸에 낼 명령 없음 — 값이 전부 미정)"];
  return lines;
}

/** 전환 화면의 「콘솔 명령」 미리보기 — 실측된 페이드 꼴은 `Store … Cue <n>
 * '<이름>' CueFade <초>` 하나뿐이다(`server/design/cue_fade.py`). 시퀀스·큐
 * 번호는 송신 때 정해지므로 자리만 둔다. 카드 t574 — 박 페이드·트리거 박을
 * 반영하고, 송신 꼴이 정해지지 않은 딜레이([미확인])·위치만 따로(⚠미확인)·
 * 트래킹(콘솔 송신 없음)은 명령이 아니라 괄호 안 안내로만 적는다. */
export function transitionConsoleCommandLines(
  cue: BeatGridCue,
  secondsPerBar: number | null | undefined,
  mib: TransitionMib | null,
  beatsPerBar: number | null = null,
  barOriginSeconds: number | null | undefined = 0,
): string[] {
  const lines: string[] = [];
  const entry = cue.entry;
  const fadeLabel = entry.fade_beats !== null && entry.fade_beats !== undefined ? `${entry.fade_beats}박` : `${entry.fade_bars}마디`;
  const fadeBars = entryFadeInBars(entry, beatsPerBar);
  if (entry.fade_bars === null && (entry.fade_beats === null || entry.fade_beats === undefined)) {
    lines.push("(페이드 미정 — CueFade 줄 없음)");
  } else if (secondsPerBar === null || secondsPerBar === undefined || fadeBars === null) {
    lines.push(`(페이드 ${fadeLabel} — 곡 BPM·박자표가 없어 초로 못 바꿈)`);
  } else {
    lines.push(`Store Sequence <시퀀스> Cue <큐> CueFade ${trimSeconds(fadeBars * secondsPerBar)}`);
  }
  const beat = entry.trigger_beat ?? 1;
  const at = triggerSeconds(cue, secondsPerBar, beatsPerBar, barOriginSeconds);
  lines.push(`(트리거: ${cue.bar}마디 ${beat}박${at === null ? "" : ` = 곡 ${trimSeconds(at)}초`} · 타임코드 이벤트)`);
  if (mib?.kind === "auto") lines.push("(MIB) 앞 큐 사이에 위치 전용 큐 — 밝기 0 유지");
  if (entry.delay_beats) lines.push(`(딜레이 ${entry.delay_beats}박 — 속성별 송신 줄 꼴 [미확인])`);
  if (entry.position_late_beats) lines.push(`(위치만 ${entry.position_late_beats}박 늦게 — ⚠미확인)`);
  if (entry.tracking) lines.push(`(트래킹 ${entry.tracking} — 콘솔 송신 없음)`);
  return lines;
}

/** 「장면 전환」 일괄 바꾸기(모두 끊기·모두 1박 페이드) — 그 마디에서 바뀌는
 * 줄마다 **다른 entry 값은 그대로 둔** 새 entry 를 만든다. */
export function sceneEntryEdits(
  tracks: readonly BeatGridTrack[],
  bar: number,
  patch: Partial<FullBeatGridEntry>,
): { target: string; entry: FullBeatGridEntry }[] {
  return sceneChangeRows(tracks, bar).map((row) => ({
    target: row.track.group_name,
    entry: entryWith(row.cue.entry, patch),
  }));
}

export interface StageGroupZone {
  trackIndex: number;
  label: string;
  x: number;
  y: number;
  width: number;
  height: number;
  fixtureCount: number;
}

/** REQ-LDBEAT-022(b) — 그룹 이름표·선택 테두리·클릭 영역. 콘솔에서 **확인된**
 * 소속(`fixtureBelongsTo` — 카드 t565부터 여러 그룹 소속)이 트랙 이름과 정확히 같은 장비만 묶는다 —
 * 이름이 비슷하다는 추론은 쓰지 않는다(`fixtureDisplayColor`와 같은 원칙). */
export function stageGroupZones(
  fixtures: readonly BeatGridFixturePoint[],
  tracks: readonly BeatGridTrack[],
  project: (point: { x: number; y: number }) => { cx: number; cy: number },
  padding: number,
): StageGroupZone[] {
  const zones: StageGroupZone[] = [];
  tracks.forEach((track, trackIndex) => {
    const key = track.group_name.toUpperCase();
    const points = fixtures
      .filter((f) => fixtureBelongsTo(f, key))
      .map((f) => project(f));
    if (points.length === 0) return;
    const xs = points.map((p) => p.cx);
    const ys = points.map((p) => p.cy);
    const minX = Math.min(...xs) - padding;
    const minY = Math.min(...ys) - padding;
    zones.push({
      trackIndex,
      label: track.group_name,
      x: minX,
      y: minY,
      width: Math.max(...xs) + padding - minX,
      height: Math.max(...ys) + padding - minY,
      fixtureCount: points.length,
    });
  });
  return zones;
}
