// 박자 격자 — 콘솔 그룹 트랙 × 마디 (SPEC-LDBEAT-001 M2, 카드 t532).
//
// `CueSheetTimeline`을 대체하지 않는다 — 그 컴포넌트는 큐 번호 단위(한 큐 =
// 한 행), 이 컴포넌트는 마디 단위(한 콘솔 그룹 트랙이 여러 큐·여러 타임코드
// 이벤트에 걸쳐 리듬을 탄다)다(plan.md §B 위험 2). `RunbookMode`의 기존
// 5블록 순서는 그대로이고, 이 컴포넌트는 `CueSheetTimeline`과 `SongTimeline`
// 사이에 **추가되는 새 블록**이다(REQ-LDBEAT-004).
//
// M2 범위 — 읽기 전용: 트랙·격자 데이터 모델과 레이아웃이 안정된 뒤에 M3가
// 실제 편집(세 경로 — 직접 고르기/문장/AI 제안)을 얹는다. 콘솔에는 이
// 컴포넌트 자신이 여전히 아무것도 쓰지 않는다 — 편집 콜백(`onEditRequest`/
// `onSentenceEditRequest`/`onSuggestionRequest`)이 서버의 새 편집 연산
// (`apply_beat_grid_edit`)으로 올라가고, 그 연산이 혼자 검증·적용한다
// (REQ-LDBEAT-007/008, 카드 t551/M3).
//
// 카드 t551 후속(리드 지시 2026-10-11, 근본 원인 정정) — 프리셋 카탈로그
// 읽기 경로는 이미 있었다(server/design/console_slots.py·preset_names.py,
// 콘솔 "읽기"는 쓰기 0 규칙과 충돌하지 않는다). 그래서 밝기 "값"(%) 외에도
// 프리셋 **서랍**(`drawerSections`/`onDrawerRequest`)과 AI 제안 점선 막대
// (`pendingSuggestion`/`onSuggestionAccept`/`onSuggestionReject`)가 추가로
// 가능해졌다 — mockup "프리셋 서랍"/"AI 제안" 절 그대로(아래 각 함수의
// 주석이 인용 절을 단다). 그 콜백들이 미제공이면 이 컴포넌트는 기존과
// 바이트 동일하게 동작한다(additive).
import { useMemo, useRef, useState } from "react";

import type {
  BeatGridAppMovement,
  BeatGridBrightness,
  BeatGridCue,
  BeatGridDrawerEntry,
  BeatGridDrawerSection,
  BeatGridEvidence,
  BeatGridPendingSuggestion,
  BeatGridSceneMemo,
  BeatGridTrack,
  BeatGridView,
} from "../protocol";

/** REQ-LDBEAT-005(a) — 초기 표시 범위를 4마디 단위 행 7개로 나눈다. 배치
 * 규칙서 §4의 표 그대로(첫 행은 못갖춘마디 포함 3마디, 넷째 행도 3마디 —
 * "4마디 단위"는 표의 경계를 그대로 옮긴 것이지 균등 분할이 아니다). */
export const BEAT_GRID_BAR_ROWS: readonly (readonly [number, number])[] = [
  [0, 2],
  [3, 6],
  [7, 10],
  [11, 13],
  [14, 17],
  [18, 21],
  [22, 25],
] as const;

/** `bar`가 속한 행의 인덱스. 범위 밖이면 `-1`. */
export function barRowIndex(bar: number): number {
  return BEAT_GRID_BAR_ROWS.findIndex(([start, end]) => bar >= start && bar <= end);
}

/** `bar` 시점에 그 트랙이 하는 일 — 그 마디 이전(또는 그 마디)에 선언된
 * 가장 최근 칸. 아직 칸이 없으면 `null`(지어내지 않는다). */
export function cueForBar(track: BeatGridTrack, bar: number): BeatGridCue | null {
  let found: BeatGridCue | null = null;
  for (const cue of track.cues) {
    if (cue.bar > bar) break;
    found = cue;
  }
  return found;
}

/** REQ-LDBEAT-005(b) — "음원 0초 = 앞박, 1마디 = 환산 초"(배치 규칙서 §4
 * 기준). `secondsPerBar`가 없으면(타임라인에 BPM/박자 미확정) 환산할 수
 * 없으므로 `null`. */
export function barToSeconds(bar: number, secondsPerBar: number | null | undefined): number | null {
  if (!secondsPerBar || !Number.isFinite(secondsPerBar)) return null;
  return bar * secondsPerBar;
}

/** `barToSeconds`의 역함수 — `maxBar`로 클램프하고 내림한다. */
export function secondsToBar(
  seconds: number,
  secondsPerBar: number | null | undefined,
  maxBar: number,
): number | null {
  if (!secondsPerBar || !Number.isFinite(secondsPerBar)) return null;
  const bar = Math.floor(seconds / secondsPerBar);
  return Math.max(0, Math.min(maxBar, bar));
}

/** ±10초 스킵 — 재생 위치를 `[0, maxSeconds]`로 클램프한다. */
export function clampSkipSeconds(current: number, delta: number, maxSeconds: number): number {
  return Math.max(0, Math.min(maxSeconds, current + delta));
}

/** 카드 t534 — 마디 하나의 가로 너비(px). 시안(`ldbeat-runbook-ui-proposal-
 * 20261008.html`)의 "줄이 많아질 때"·"큐 운영" 절이 보여주는 "칸 길이 =
 * 큐 길이"를 마디 시간축으로 그대로 옮긴 값이다 — 8마디 확대 수준에
 * 가깝게 고정했다(시안의 확대 단계는 M3 범위). */
export const PX_PER_BAR = 42;

/** `bar` → 가로 픽셀 좌표. 시간축 레이아웃 전용 순수 함수(상태 없음). */
export function barToX(bar: number, pxPerBar: number = PX_PER_BAR): number {
  return bar * pxPerBar;
}

export interface CueSegment {
  cue: BeatGridCue;
  /** 이 칸이 시작하는 마디 — `cue.bar`와 같다. */
  startBar: number;
  /** 이 칸이 끝나는 마디(배타적) — 다음 칸이 시작하는 마디, 없으면
   * `maxBar + 1`(격자 표시 범위 끝까지). */
  endBar: number;
}

/** 카드 t534 — 트랙의 칸을 "칸 길이 = 다음 칸까지의 마디 수"로 환산한다
 * (REQ-LDBEAT-004, 시안 §"큐 운영": "실제 값은 … 들어오는 큐에 저장"과
 * 같은 원리 — 길이는 다음 칸이 정한다). 지어내지 않음: 칸이 없으면 빈
 * 배열. */
export function trackCueSegments(track: BeatGridTrack, maxBar: number): CueSegment[] {
  return track.cues.map((cue, index) => {
    const next = track.cues[index + 1];
    const endBar = next ? next.bar : maxBar + 1;
    return { cue, startBar: cue.bar, endBar };
  });
}

/** 카드 t534 — 칸 내용이 "꺼짐/변화없음"(「—」, 배치 규칙서 관례)인지
 * 판단한다. 2D 무대 밝기(불/꺼짐)와 전환 판단의 공통 토대 — 수치 디머를
 * 지어내지 않고, 이미 있는 「—」 표기만 본다. */
export function cueIsActive(label: string): boolean {
  const trimmed = label.trim();
  return trimmed !== "" && trimmed !== "—";
}

/** 층 역할(`server.design.rig.RIG_LAYER_ROLES`)의 화면 이름표. 트랙 식별자가
 * 아니라 줄 옆의 폴더 이름일 뿐이다(REQ-LDBEAT-004, 카드 t526 교정). */
export const LAYER_ROLE_FOLDER_LABELS: Readonly<Record<string, string>> = {
  key: "앞빛",
  back: "역광",
  side: "옆빛",
  wash: "워시",
  mover: "무빙",
  effect: "효과",
  audience: "객석",
};

const UNASSIGNED_FOLDER = "미분류";

export function layerFolderLabel(role: string | null | undefined): string {
  if (!role) return UNASSIGNED_FOLDER;
  return LAYER_ROLE_FOLDER_LABELS[role] ?? UNASSIGNED_FOLDER;
}

export interface BeatGridFolder {
  role: string;
  label: string;
  tracks: BeatGridTrack[];
}

/** 트랙을 층 역할 폴더로 묶는다 — 처음 등장한 순서를 유지한다(REQ-LDBEAT-004(b)
 * 의 "층 역할 폴더" 접기/펴기 단위). */
export function groupTracksByLayerFolder(tracks: BeatGridTrack[]): BeatGridFolder[] {
  const order: string[] = [];
  const byRole = new Map<string, BeatGridTrack[]>();
  for (const track of tracks) {
    const role = track.layer_role ?? UNASSIGNED_FOLDER;
    if (!byRole.has(role)) {
      byRole.set(role, []);
      order.push(role);
    }
    byRole.get(role)!.push(track);
  }
  return order.map((role) => ({
    role,
    label: role === UNASSIGNED_FOLDER ? UNASSIGNED_FOLDER : layerFolderLabel(role),
    tracks: byRole.get(role)!,
  }));
}

/** REQ-LDBEAT-010/AC-LDBEAT-004 — 실기 미확인 모양(§6: circle·발리후·위상
 * 펼침). 배치 규칙서 §3이 "⚠"로 표기한 바로 그 모양들이다. */
const UNCONFIRMED_SHAPE_KEYWORDS = ["서클", "발리후", "위상 펼침", "circle", "ballyhoo"];

export function isUnconfirmedShapeCue(label: string): boolean {
  const lower = label.toLowerCase();
  return UNCONFIRMED_SHAPE_KEYWORDS.some((kw) => lower.includes(kw.toLowerCase()));
}

/** t537 — REQ-LDBEAT-003(b). M1 9항목 판정은 progress.md의 표 칸 텍스트를
 * **그대로** 옮긴 자유 문자열이다(예: `"통과(구조)"`·`"미확인"`·`"움직임
 * 없음"`·`"부분(결과 기록)"`) — 고정된 네 상태로 매핑하지 않는다. 손으로
 * 옮긴 TS 상수(`beatGridM1Probes.ts`, 카드 t534가 만든 것)는 카드 t537이
 * 폐기했다 — progress.md 자신이 "그 표가 갱신되면 바로 낡는다"고 적어
 * 두었던 그 위험이 실제로 일어났기 때문이다(lane-3의 실기 M1이 머지되며
 * 이 상수가 가리키던 "리허설PASS·실기미실행" 아홉 줄은 더 이상 사실이
 * 아니게 됐다). 이제 이 값은 `BeatGridView.probe_results`(서버가
 * progress.md를 그 자리에서 읽어 채운 값)에서만 온다. */
export type ProbeStatus = string;

/** 표가 없거나·파싱 실패하거나·그 항목 행이 없을 때의 정직한 기본값
 * (REQ-LDBEAT-003(b) 실패-경로, AC-LDBEAT-009(d)) — 지어낸 PASS는 0건. */
export const UNCONFIRMED_PROBE_STATUS = "미확인";

/** REQ-LDBEAT-001~003의 9항목 — progress.md가 쓰는 같은 순서·같은 9개.
 * `probeResults`에 없는 항목은 `UNCONFIRMED_PROBE_STATUS`가 기본이다. */
export const DEFAULT_PROBE_LABELS: readonly { id: number; label: string }[] = [
  { id: 1, label: "타임코드 트랙 ≥3" },
  { id: 2, label: "Goto 2번 이후·여러 시퀀스 동시" },
  { id: 3, label: "프리셋 수정 전파" },
  { id: 4, label: "효과 프리셋 SM15·Measure" },
  { id: 5, label: "위치 프리셋 위 상대값" },
  { id: 6, label: "타임코드 중간 재생" },
  { id: 7, label: "큐 하나 그룹 하나 + Step 2" },
  { id: 8, label: "같은 그룹 두 시퀀스 분담" },
  { id: 9, label: "circle·발리후" },
];

export interface ProbeRow {
  id: number;
  label: string;
  status: ProbeStatus;
}

export function buildProbeStatusTable(
  probeResults?: Readonly<Record<number, ProbeStatus>>,
): ProbeRow[] {
  return DEFAULT_PROBE_LABELS.map(({ id, label }) => ({
    id,
    label,
    status: probeResults?.[id] ?? UNCONFIRMED_PROBE_STATUS,
  }));
}

/** REQ-LDBEAT-001 게이트 — 9항목 중 하나라도 "통과"로 시작하지 않으면 그
 * 항목에 의존하는 콘솔 **쓰기**는 잠긴다(미리보기는 이 게이트의 대상이
 * 아니다, 결정⑤). progress.md의 판정 갈래 중 "통과"만 쓰기를 열 근거이고
 * "부분"·"미확인"·"움직임 없음"은 전부 아직 아니다. */
export function isWriteLocked(probes: readonly { status: ProbeStatus }[]): boolean {
  return probes.some((probe) => !probe.status.startsWith("통과"));
}

/** t537 — 프로브 상태(progress.md 판정 칸의 자유 문자열) → CSS 클래스
 * 접미사. "통과"로 시작하면 pass, 정확히 "미확인"이면 pending(판정 근거
 * 없음), 그 밖(부분/움직임 없음/문법 불명 등 — 아직 쓰기를 열 수 없는
 * 모든 상태)은 fail로 눈에 띄게 보인다. */
export function probeStatusClass(status: ProbeStatus): "pass" | "fail" | "pending" {
  if (status.startsWith("통과")) return "pass";
  if (status === UNCONFIRMED_PROBE_STATUS) return "pending";
  return "fail";
}

/** 곡의 첫 칸인지 — "들어오는 전환" 토글이 비활성화되는 기준(REQ-LDBEAT-004(d)).
 * 곡 전체의 첫 칸(격자 표시 범위의 시작 마디)만 전환이 없다. */
export function isFirstCueOfSong(bar: number, grid: BeatGridView): boolean {
  return bar <= grid.bar_range.start;
}

export interface BeatGridFixturePoint {
  fid: number;
  name: string;
  x: number;
  y: number;
  z: number;
  rotx: number;
  roty: number;
  rotz: number;
  /** 콘솔 SELECTIONDATA로 **확인된** 소속 그룹 이름 — 이름 추정이 아니라
   * 읽은 값이어야 한다. 없으면(`null`/`undefined`) 미확인이고, 화면은
   * 반드시 회색이다(REQ-LDBEAT-004(f)). 이 값을 채우는 유일한 근거는
   * 콘솔 `SELECTIONDATA` 읽기다 — 장비 이름이 그룹 이름과 비슷해 보인다는
   * 것은 이 필드를 채울 근거가 **아니다**(레인 리뷰 05ad9ec4, 이름 접두
   * fallback 제거). 지금까지 확인된 그룹은 t525 §② 네 개뿐이고(그룹당
   * 앞 2대만) `.moai/reports/t525/verdict.md`의 "근거 2 — sf_index → fid
   * 대응" 표(파일 93~103행, 표 본문 100~103행)가 그 전체 목록이다 — MOVER-ALL(501·502) ·
   * BACK(201·202) · SIDE-L(301·302) · BLIND(601·602). */
  confirmedGroupName?: string | null;
}

interface StageBounds {
  minX: number;
  maxX: number;
  maxY: number;
  spanX: number;
  spanY: number;
}

/** 2D 무대 투영의 좌표 경계 — 실측 범위를 그대로 쓴다(상수를 지어내지
 * 않는다, t525 §③). 픽스처가 없으면 `null`. */
export function computeStageBounds(fixtures: readonly BeatGridFixturePoint[]): StageBounds | null {
  if (fixtures.length === 0) return null;
  const xs = fixtures.map((f) => f.x);
  const ys = fixtures.map((f) => f.y);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  return {
    minX,
    maxX,
    maxY,
    spanX: Math.max(1, maxX - minX),
    spanY: Math.max(1, maxY - minY),
  };
}

const STAGE_VIEW_W = 300;
const STAGE_VIEW_H = 220;
const STAGE_MARGIN = 20;

/** 픽스처 좌표 → SVG 화면 좌표. 위 = 무대 뒤(Y 값이 큰 쪽), 아래 = 객석
 * (t525 §③ "위에서 본 그림" 관례 그대로 — Y 방향 자체는 이름 추정이라
 * 미확인으로 남는다, spec.md §5 항목 5). */
export function projectFixture(
  point: { x: number; y: number },
  bounds: StageBounds,
): { cx: number; cy: number } {
  const usableW = STAGE_VIEW_W - STAGE_MARGIN * 2;
  const usableH = STAGE_VIEW_H - STAGE_MARGIN * 2;
  const cx = STAGE_MARGIN + ((point.x - bounds.minX) / bounds.spanX) * usableW;
  // Y가 클수록(무대 뒤) 화면 위쪽 — bounds.maxY를 0으로 둔다.
  const cy = STAGE_MARGIN + ((bounds.maxY - point.y) / bounds.spanY) * usableH;
  return { cx, cy };
}

/** REQ-LDBEAT-004(f) — 그룹 소속이 **확인된** 장비만 칠하고, 나머지는 회색
 * (t525 §③ 패턴 — "확인된 것만" 색, 전체 칠하기를 거짓으로 보여주지
 * 않는다). "확인"의 유일한 근거는 `fixture.confirmedGroupName`(콘솔
 * SELECTIONDATA에서 읽은 값)이고, 그것이 화면에 떠 있는 어느 트랙의
 * `group_name`과 **정확히** 일치할 때만 그 트랙 색을 쓴다 — 이름이 비슷해
 * 보인다는 추론(접두 매칭)은 fallback으로도 쓰지 않는다(레인 리뷰
 * 05ad9ec4). 이것은 트랙의 `group_no_confirmed`(그룹 **번호** 확인 여부,
 * 다른 축)와 무관하다 — 번호를 몰라도 SELECTIONDATA가 이름으로 소속을
 * 확인해 줬다면 그것으로 충분하다. */
const TRACK_COLOR_PALETTE = ["#4f8cff", "#f85149", "#3fb950", "#d29922", "#b388ff", "#00c2cc"];
const UNCONFIRMED_FIXTURE_COLOR = "#5a5f6b";

export function fixtureDisplayColor(
  fixture: BeatGridFixturePoint,
  tracks: readonly BeatGridTrack[],
): string {
  if (!fixture.confirmedGroupName) return UNCONFIRMED_FIXTURE_COLOR;
  const confirmedKey = fixture.confirmedGroupName.toUpperCase();
  const index = tracks.findIndex((track) => track.group_name.toUpperCase() === confirmedKey);
  if (index < 0) return UNCONFIRMED_FIXTURE_COLOR;
  return TRACK_COLOR_PALETTE[index % TRACK_COLOR_PALETTE.length];
}

/** 소속 미확인/칸 미선언/꺼진 칸일 때 공통으로 쓰는 흐림 값. 수치 디머를
 * 지어내지 않으므로 "밝기"는 이 한 단계(흐림/보통/최대)뿐이다. */
const UNCONFIRMED_FIXTURE_OPACITY = 0.45;
const INACTIVE_FIXTURE_OPACITY = 0.55;
const ACTIVE_FIXTURE_OPACITY = 1;

/** REQ-LDBEAT-004(f) 확장(카드 t534) — 2D 무대의 "밝기"는 콘솔 디머 수치가
 * 없으므로(M2/M3 전까지 칸은 문장 하나뿐) 지어내지 않는다. 대신 이미 있는
 * 실측 정보 두 가지만 흐림 단계로 옮긴다: (1) `fixtureDisplayColor`와 같은
 * "확인된 소속"인지, (2) `viewBar` 시점 그 트랙의 칸이 `cueIsActive`인지
 * (「—」=꺼짐, 배치 규칙서 관례 — 지어낸 수치가 아니라 이미 쓰는 표기).
 * 둘 다 사실일 때만 최대 밝기다. */
export function fixtureDisplayOpacity(
  fixture: BeatGridFixturePoint,
  tracks: readonly BeatGridTrack[],
  viewBar: number,
): number {
  if (!fixture.confirmedGroupName) return UNCONFIRMED_FIXTURE_OPACITY;
  const confirmedKey = fixture.confirmedGroupName.toUpperCase();
  const track = tracks.find((t) => t.group_name.toUpperCase() === confirmedKey);
  if (!track) return UNCONFIRMED_FIXTURE_OPACITY;
  const cue = cueForBar(track, viewBar);
  if (!cue) return INACTIVE_FIXTURE_OPACITY;
  return cueIsActive(cue.label) ? ACTIVE_FIXTURE_OPACITY : INACTIVE_FIXTURE_OPACITY;
}

export interface BeatGridProps {
  grid: BeatGridView | null | undefined;
  /** 2D 무대 좌표 — 콘솔 접촉 0인 M2는 이 값을 props로만 받는다(살아있는
   * 읽기 경로가 없으면 지어내지 않는다). 비어 있으면 무대 칸은 "무대 좌표
   * 미제공" 안내로 떨어진다. */
  fixtures?: BeatGridFixturePoint[];
  probeResults?: Readonly<Record<number, ProbeStatus>>;
  secondsPerBar?: number | null;
  /** t537 (3) — 색 프리셋 번호 → 실제 콘솔 색(hex). 이 카드는 콘솔 접촉
   * 0이라 아직 이 데이터의 살아있는 출처가 없다(M3+ 이후 프리셋 풀 읽기가
   * 채운다) — 넘기지 않으면(또는 번호가 이 표에 없으면) 그 칸은 항상
   * 중립(미정)으로 보인다. 임의 색으로 지어내 칠하지 않는다. */
  colorPresetHex?: Readonly<Record<string, string>>;
  /** t537 레이아웃 교정 — 곡 전체 지도의 구간 띠(REQ-LDBEAT-004(a)). 이미
   * 서버가 `timeline.sections`로 보내는 값이다 — 넘기지 않거나
   * `secondsPerBar`가 없으면 기존 7칸 숫자 띠로 조용히 떨어진다. */
  sections?: readonly BeatGridSectionLite[];
  /**
   * 카드 t551(M3) — 편집 경로 ①(직접 고르기). UI는 서버 페이로드를 직접
   * 구성하지 않는다(AC-LDBEAT-005) — 이 콜백은 사용자가 고른 필드·값을
   * 그대로 담아 올리고, 서버의 `apply_beat_grid_edit`가 검증·적용한다.
   * 카드 t551 계속(progress.md "M3 후속 — 직접 고르기 드롭다운") — 밝기
   * **값**(%) 평문 숫자 외에, 위치·색·밝기(디머 프리셋) 세 필드가
   * `drawerSections`에서 "이 곡 프리셋"/"쇼에 이미 있는 프리셋"/"+ 새
   * 프리셋" 목록 선택으로도 고쳐진다(앞선 `ldbeat-runbook-mockup-
   * 20261008.html` `opts()` 그대로). 카드 t551 계속(코디네이터 지시
   * 2026-10-11, 조건 1 — "lead 가 옵션 A를 골랐다") — 효과(움직임)
   * 프리셋과 디머 "효과" 서브모드도 이제 같은 패턴으로 고쳐진다. mockup
   * 자신이 같은 풀 안에서 번호대로 기본/효과를 가른다는 근거(`ldbeat-
   * runbook-mockup-20261008.md` 14-17/26-29행) — 서버가 `preset_pools.
   * yaml`(코드 상수 0건)로 각 항목의 `is_effect_band`를 판정해 보낸다
   * (`drawerSections`의 기존 세 풀 그대로, 네 번째 풀("All 1")은 여전히
   * 안 쓴다 — 조건1이 요구한 것만 더했다). 생략하면(미제공) 모든 칸이
   * 읽기 전용이다(기존 동작과 바이트 동일).
   */
  onEditRequest?: (request: {
    bar: number;
    target: string;
    changes: Record<string, unknown>;
  }) => void;
  /**
   * 카드 t551(M3) — 편집 경로 ②(문장). 명령창 "바로 적용(문장)" 버튼이
   * 입력 문자열을 그대로 올린다 — 해석(마디·역할·항목·값)은 전부 서버의
   * `beat_grid_sentence.parse_beat_grid_sentence`가 한다(REQ-LDBEAT-007).
   * 생략하면 버튼은 비활성이다(기존 동작과 바이트 동일, M3 배선 전 상태).
   */
  onSentenceEditRequest?: (sentence: string) => void;
  /**
   * 카드 t551(M3) — 편집 경로 ③(AI 제안) 1단계. "AI 제안" 버튼이 지금
   * 고른 칸(bar·그룹)을 서버의 `beat_grid_suggest`로 올린다 — 실제 AI
   * 백엔드는 이 카드 범위 밖이라(`NullSuggestionSource`) 오늘은 "제안
   * 없음" 응답이 채팅 로그에 그대로 뜬다(지어낸 제안 0건). 생략하면
   * 버튼은 비활성이다.
   */
  onSuggestionRequest?: (bar: number, target: string) => void;
  /**
   * 카드 t551 후속(지시 1항) — 보류 중인 AI 제안 하나. mockup의 점선
   * 막대 + 수락/거절 카드(`#bAi`→`aOk`/`aNo`)와 같은 모양. 생략·`null`이면
   * 아무 트랙에도 점선 막대가 뜨지 않는다(지금까지와 바이트 동일).
   */
  pendingSuggestion?: BeatGridPendingSuggestion | null;
  /** 카드 t551 후속 — mockup `aOk`(수락 → 같은 편집 요청을 보낸다). */
  onSuggestionAccept?: (suggestionId: string) => void;
  /** 카드 t551 후속 — mockup `aNo`(거절 → 격자·콘솔 diff 0). */
  onSuggestionReject?: (suggestionId: string) => void;
  /**
   * 카드 t551 후속(지시 1항) — 프리셋 서랍 섹션들(mockup "구조" 6,
   * `drawDrawer()`). `null`이면 아직 안 받음(서랍을 열어도 "불러오는
   * 중" 안내). 생략하면 서랍 버튼 자체가 없다(기존과 바이트 동일).
   */
  drawerSections?: BeatGridDrawerSection[] | null;
  /** 카드 t551 후속 — mockup `#bLib`(서랍 열기, 매번 최신 판독 요청). */
  onDrawerRequest?: () => void;
}

/** 역할별 조건부 노출(REQ-LDBEAT-004(c)) — 무빙만 "움직임", KEY류는 "색"
 * 없음(기존 `cue_sheet_edit.py`의 `r.nocol` 관례와 같은 판단). */
function roleFieldHints(role: string | null): string[] {
  const hints: string[] = ["밝기"];
  if (role === "mover" || role === "back" || role === "side" || role === "wash") hints.push("위치");
  if (role !== "mover") hints.push("색");
  if (role === "mover") hints.push("움직임");
  return hints;
}

/** t537 — 구조화 필드가 미정(`null`)일 때 공통으로 쓰는 표시 문구. "0"이나
 * 빈 문자열이 아니라 명시적으로 "미정"이라고 말한다(REQ-LDBEAT-015(f)와
 * 같은 원칙을 화면 표시에도 적용 — 출처 없는 값을 지어내지 않는다). */
export const UNSET_FIELD_LABEL = "미정";

/** 밝기 칸 표시 — `mode`가 없으면 미정, `"value"`면 퍼센트, 프리셋
 * 모드면 그 프리셋 번호(없으면 역시 미정 — 둘 다 비면 지어내지 않는다). */
export function formatBrightnessField(brightness: BeatGridBrightness): string {
  if (brightness.mode === "value") {
    return brightness.value_percent === null ? UNSET_FIELD_LABEL : `${brightness.value_percent}%`;
  }
  if (brightness.mode === "dimmer_preset" || brightness.mode === "dimmer_effect") {
    return brightness.preset_no ?? UNSET_FIELD_LABEL;
  }
  return UNSET_FIELD_LABEL;
}

/** 위치/색/효과 프리셋 번호 칸 — 값이 없으면 미정(추측해 채우지 않음,
 * REQ-LDBEAT-015(f)). */
export function formatPresetField(presetNo: string | null): string {
  return presetNo ?? UNSET_FIELD_LABEL;
}

/** "들어올 때"의 마디 수 칸 — `null`이면 미정(REQ-LDBEAT-006(i-4)). */
export function formatFadeBarsField(fadeBars: number | null): string {
  return fadeBars === null ? UNSET_FIELD_LABEL : `${fadeBars}마디`;
}

/** 마디 수 → 초 환산(REQ-LDBEAT-006(i-4) — "저장은 마디, 초 환산은 화면
 * 표시 시점에 그 곡 BPM으로"). 둘 중 하나라도 없으면 `null`(지어내지
 * 않음) — 저장하지 않는 **파생값**이라는 것을 호출부가 "derived" 표기와
 * 함께 보여준다. */
export function deriveFadeSeconds(fadeBars: number | null, secondsPerBar: number | null): number | null {
  if (fadeBars === null || !secondsPerBar || !Number.isFinite(secondsPerBar)) return null;
  return fadeBars * secondsPerBar;
}

/** `source_ref` 표시 — 있으면 그 문자열을 그대로(링크 텍스트), 없으면
 * `null`(호출부가 행 자체를 생략하거나 "출처 없음"으로 보여준다). */
export function formatSourceRefLabel(sourceRef: string | null): string | null {
  return sourceRef;
}

/** t548 — REQ-LDBEAT-006(vi) 칸 표시. `null`이면 미정. 있으면
 * `"<shape> · <축(들)> · <주기>"` — 주기가 미정이면("지어내지 않음", 레이블이
 * 말하지 않은 칸) 그 자리도 `UNSET_FIELD_LABEL`이다. 축이 둘이면
 * `"Pan+Tilt"`로 합친다(고정 순서, 재배열하지 않는다). */
export function formatAppMovementField(movement: BeatGridAppMovement | null): string {
  if (!movement) return UNSET_FIELD_LABEL;
  const axesLabel = (["Pan", "Tilt"] as const)
    .filter((axis) => movement.axes.includes(axis))
    .join("+");
  const periodLabel =
    movement.period_unit === "beat"
      ? `${movement.period_value}박`
      : movement.period_unit === "bar"
        ? `${movement.period_value}마디`
        : UNSET_FIELD_LABEL;
  return `${movement.shape} · ${axesLabel} · ${periodLabel}`;
}

/** t548 — REQ-LDBEAT-006(vii) 근거 등급 표시. `grade`만 있으면 그 한국어
 * 이름, `approval`도 채워져 있으면 승인 날짜를 덧붙인다(REQ-LDBEAT-015
 * (g) 승인 예외가 성립한 칸을 화면에서도 구분할 수 있게). */
export function formatEvidenceField(evidence: BeatGridEvidence | null): string {
  if (!evidence || !evidence.grade) return UNSET_FIELD_LABEL;
  const gradeLabel: Record<NonNullable<BeatGridEvidence["grade"]>, string> = {
    measured: "측정",
    measured_other_group: "다른 그룹 실측",
    name_only: "이름만",
  };
  const base = gradeLabel[evidence.grade];
  if (evidence.approval?.date) return `${base} · 승인(${evidence.approval.date})`;
  return base;
}

/** t548 — AC-LDBEAT-016(t), REQ-LDBEAT-006(vi-7). 한 칸이 `app_movement`와
 * `effect_preset_no`를 **같은 축**에 동시에 쓰면 거절 플래그를 올린다.
 * `effect_kind`는 그 효과가 정확히 어느 축을 움직이는지 말하지 않으므로
 * `"position"`·`"mixed"`는 Pan·Tilt 어느 쪽과도 충돌로 **보수적으로**
 * 본다 — `"color"`·`"dimmer"`는 축을 움직이지 않아 충돌이 없다(server
 * `check_app_movement_axis_conflict`와 같은 판정). */
export function appMovementAxisConflictWarning(cue: BeatGridCue): string | null {
  const { app_movement: movement, effect_preset_no: effectPresetNo, effect_kind: effectKind } =
    cue;
  if (!movement || movement.axes.length === 0) return null;
  if (effectPresetNo === null) return null;
  if (effectKind !== "position" && effectKind !== "mixed") return null;
  return "⚠ 같은 축 충돌";
}

/** t548 — 감독 결정④(2026-10-10, 리드 경유). Pan 단독 `app_movement`가
 * `position_preset_no` 없이(기본 위치=수직 중심) 쓰이면 눈에 보이지 않을
 * 수 있다 — 경고일 뿐 거절은 아니다(server `pan_only_vertical_base_
 * warning`과 같은 판정, `position_preset_no`가 있는 경우의 "수직인가"
 * 판정은 이 SPEC의 범위 밖). */
export function panOnlyVerticalBaseWarning(cue: BeatGridCue): string | null {
  const movement = cue.app_movement;
  if (!movement) return null;
  if (movement.axes.length !== 1 || movement.axes[0] !== "Pan") return null;
  if (cue.position_preset_no !== null) return null;
  return "⚠ Pan 단독 움직임이 기본 위치(수직) 중심입니다 — 기울인 위치 프리셋 없이는 눈에 보이지 않을 수 있습니다";
}

/** 카드 t551(M3) — 밝기 "값"(%) 모드만 프리셋 카탈로그 없이 바로 고칠 수
 * 있다(mockup "밝기 값/디머 프리셋/디머 효과" 중 "값"만 평문 숫자). 칸이
 * 없거나(`null`) 디머 프리셋/디머 효과 참조 중이면 편집 불가 — 둘 다
 * "어느 프리셋으로 바꿀까"가 목록 선택을 요구해 이 카드 범위 밖이다. */
export function isBrightnessValueEditable(cue: BeatGridCue | null): boolean {
  if (!cue) return false;
  return cue.brightness.mode !== "dimmer_preset" && cue.brightness.mode !== "dimmer_effect";
}

/** 서버의 `apply_beat_grid_edit`가 받는 ``changes`` 모양 그대로 — UI는 이
 * 모양을 조립할 뿐 검증하지 않는다(검증은 서버 하나의 진실 지점,
 * REQ-LDBEAT-008). `percent`가 유한하지 않으면(빈 입력 등) `null`. */
export function buildBrightnessValueChanges(percent: number): Record<string, unknown> | null {
  if (!Number.isFinite(percent)) return null;
  return { brightness: { mode: "value", value_percent: percent, preset_no: null } };
}

/** 카드 t551 후속(지시 1항) — 이 칸이 `presetNo`를 쓰는가. 프리셋 서랍의
 * "누르면 쓰는 막대가 노랗게"(mockup `drawDrawer()` 안내 문구, `hlP`
 * 강조)를 타임라인 쪽에서 그대로 구현하는 술어다 — 서버의
 * `beat_grid_presets._usage_for_slot`과 같은 네 자리(위치·색·효과·
 * 디머 프리셋/디머 효과)를 본다. */
export function cueReferencesPreset(cue: BeatGridCue, presetNo: string): boolean {
  if (cue.position_preset_no === presetNo) return true;
  if (cue.color_preset_no === presetNo) return true;
  if (cue.effect_preset_no === presetNo) return true;
  const mode = cue.brightness.mode;
  if ((mode === "dimmer_preset" || mode === "dimmer_effect") && cue.brightness.preset_no === presetNo) {
    return true;
  }
  return false;
}

/** 카드 t551 후속(지시 2항) — `preset_pools.yaml`의 `confirmed`가
 * `false`일 때 보여줄 배지. mockup 자신에는 "번호대 자체가 미확인"이라는
 * 상태가 없다(그 데모는 번호대가 이미 정해져 있다는 전제) — 그래서 가장
 * 가까운 기존 관례인 "⚠ 실기 미확인"(모양 선택지 배지, `isUnconfirmedShapeCue`
 * 와 같은 글자)을 폭을 넓혀 재사용한다(이 카드가 그 자리를 정한 이유).
 * `confirmed`가 `true`(또는 알 수 없음)면 배지를 달지 않는다 — 번호대를
 * 사실로 내보이지 않을 뿐, 확정된 상태를 과장해 경고하지도 않는다. */
export function presetPoolBandBadge(section: BeatGridDrawerSection): string | null {
  return section.bands_confirmed ? null : "⚠ 번호대 미확인";
}

/** 카드 t551 계속 — 직접 고르기(①) 드롭다운의 "+ 새 프리셋" 선택지 값.
 * `ldbeat-runbook-mockup-20261008.html` `opts()`의 `"__new"` 리터럴
 * 그대로(값이 이 값이면 적용하지 않는다 — 그 모양 자체가 새 창을 여는
 * 자리라는 신호일 뿐, 번호가 아니다). */
export const NEW_PRESET_OPTION_VALUE = "__new";

/** 카드 t551 계속 — 직접 고르기 드롭다운 한 옵션의 표시 문구. mockup
 * `opts()`의 `${i} ${P[i].nm}`과 같은 모양("번호 이름"). */
export function formatDrawerEntryOptionLabel(entry: BeatGridDrawerEntry): string {
  return `${entry.preset_no} ${entry.name}`;
}

/** 카드 t551 계속 — 서랍 섹션 하나를 "이 곡 프리셋"(이 격자가 실제로
 * 쓰는 것, `usage_count > 0`)과 "쇼에 이미 있는 프리셋"(콘솔에서 읽혔지만
 * 이 곡은 아직 안 쓰는 것, `usage_count === 0`)으로 가른다 — mockup
 * `opts()`의 두 `<optgroup>`("이 곡 프리셋"/"쇼에 이미 있는 프리셋")과
 * 같은 그룹·같은 이름이다. 섹션이 없거나(아직 서랍을 안 열었거나) 그
 * 풀을 콘솔에서 못 읽었으면(POOL_UNREAD, `section.unread`) 둘 다 빈
 * 배열이다 — 목록을 지어내지 않는다. */
function splitEntriesByUsage(
  entries: BeatGridDrawerEntry[],
): { thisSong: BeatGridDrawerEntry[]; showExisting: BeatGridDrawerEntry[] } {
  return {
    thisSong: entries.filter((entry) => entry.usage_count > 0),
    showExisting: entries.filter((entry) => entry.usage_count === 0),
  };
}

export function splitDrawerSectionEntries(
  section: BeatGridDrawerSection | null,
): { thisSong: BeatGridDrawerEntry[]; showExisting: BeatGridDrawerEntry[] } {
  if (!section || section.unread) return { thisSong: [], showExisting: [] };
  return splitEntriesByUsage(section.entries);
}

/** 카드 t551 계속(코디네이터 지시 2026-10-11, 조건 1 — "lead 가 옵션 A를
 * 골랐다") — 효과(움직임)·디머 "효과" 드롭다운은 같은 풀 섹션에서
 * `is_effect_band`(서버가 `preset_pools.yaml` 번호대로 이미 판정한 값,
 * 번호대 리터럴은 이 함수에도 없다)인 항목만 골라낸 뒤, 그 안에서 다시
 * `splitDrawerSectionEntries`와 같은 "이 곡 프리셋"/"쇼에 이미 있는
 * 프리셋" 그룹으로 가른다. */
export function splitDrawerSectionEffectEntries(
  section: BeatGridDrawerSection | null,
): { thisSong: BeatGridDrawerEntry[]; showExisting: BeatGridDrawerEntry[] } {
  if (!section || section.unread) return { thisSong: [], showExisting: [] };
  return splitEntriesByUsage(section.entries.filter((entry) => entry.is_effect_band));
}

/** 카드 t551 계속 — `drawerSections`에서 풀 이름("Position"/"Color"/
 * "Dimmer")으로 섹션 하나를 찾는다. 배열 자체가 `null`이면(서랍을 아직
 * 한 번도 안 열어 못 받은 상태) `null` — `section.unread`(읽긴 했지만
 * POOL_UNREAD)와는 다른 "아직 안 옴" 상태라 호출자가 구분해 보일 수
 * 있다. */
export function findDrawerSection(
  sections: BeatGridDrawerSection[] | null,
  poolName: string,
): BeatGridDrawerSection | null {
  if (!sections) return null;
  return sections.find((section) => section.pool_name === poolName) ?? null;
}

/** 서버 `apply_beat_grid_edit`의 ``changes`` 모양 — 위치 프리셋 직접
 * 고르기(드로워에서 고른 번호를 그대로 담는다, 검증은 서버 몫). */
export function buildPositionPresetChanges(presetNo: string): Record<string, unknown> {
  return { position_preset_no: presetNo };
}

/** 서버 `apply_beat_grid_edit`의 ``changes`` 모양 — 색 프리셋 직접
 * 고르기. */
export function buildColorPresetChanges(presetNo: string): Record<string, unknown> {
  return { color_preset_no: presetNo };
}

/** 서버 `apply_beat_grid_edit`의 ``changes`` 모양 — 밝기 단일모드 중
 * "디머 프리셋" 직접 고르기(REQ-LDBEAT-015(c), `buildBrightnessValueChanges`
 * 의 "값" 모드와 같은 자리, 세 모드 중 정확히 하나). */
export function buildBrightnessPresetChanges(presetNo: string): Record<string, unknown> {
  return { brightness: { mode: "dimmer_preset", value_percent: null, preset_no: presetNo } };
}

/** 서버 `apply_beat_grid_edit`의 ``changes`` 모양 — 효과(움직임) 프리셋
 * 직접 고르기. 이 드롭다운은 무빙(`hints.includes("움직임")`, 위치 풀의
 * 효과 번호대) 전용이라 `effect_kind`는 "position"으로 고정한다 — 이
 * 값은 번호대 리터럴이 아니라 REQ-LDBEAT-006(i-3)의 닫힌 종류 어휘다. */
export function buildEffectPresetChanges(presetNo: string): Record<string, unknown> {
  return { effect_preset_no: presetNo, effect_kind: "position" };
}

/** 서버 `apply_beat_grid_edit`의 ``changes`` 모양 — 밝기 단일모드 중
 * "디머 효과" 직접 고르기(REQ-LDBEAT-015(c), `buildBrightnessPresetChanges`
 * 의 "디머 프리셋" 모드와 짝). */
export function buildBrightnessDimmerEffectChanges(presetNo: string): Record<string, unknown> {
  return { brightness: { mode: "dimmer_effect", value_percent: null, preset_no: presetNo } };
}

/** 카드 t551 후속(지시 1항) — `pendingSuggestion`이 이 트랙(그룹 이름)을
 * 겨냥하는가. mockup의 점선 막대(`GHOST=[{r:"movd",...}]`)가 그 트랙
 * 줄에만 겹쳐 그려지는 것과 같은 판정이다. */
export function isPendingSuggestionForTrack(
  suggestion: BeatGridPendingSuggestion | null | undefined,
  groupName: string,
): boolean {
  return !!suggestion && suggestion.target === groupName;
}

export interface BeatGridCueColorFill {
  /** CSS 배경색 문자열 — 있을 때만 inline style로 쓴다. */
  background?: string;
  /** `color_preset_no`가 없거나, 있어도 그 색을 아는 자리(`colorPresetHex`)가
   * 없을 때 참 — 둘 다 "지어내지 않는다"는 같은 규칙의 다른 경로다
   * (REQ-LDBEAT-015(f)와 같은 원칙을 렌더링에도 적용, plan.md M7 (3)). */
  isColorUnset: boolean;
}

/** 막대 채우기 색 — `color_preset_no`가 있고 그 번호의 실제 색(`colorPresetHex`,
 * 콘솔에서 읽은 프리셋 색 — 이 카드 범위에서는 콘솔 접촉 0이라 아직 아무
 * 데이터도 없다)을 알 때만 그 색을 쓴다. 번호가 없거나, 번호는 있지만
 * 색을 모르면(아직 `colorPresetHex`가 없다) **중립**이다 — 임의 색을
 * 지어내 칠하지 않는다(plan.md M7 (3), REQ-LDBEAT-015(f)와 같은 원칙). */
export function cueColorFill(
  cue: BeatGridCue,
  colorPresetHex?: Readonly<Record<string, string>>,
): BeatGridCueColorFill {
  if (!cue.color_preset_no) return { isColorUnset: true };
  const hex = colorPresetHex?.[cue.color_preset_no];
  if (!hex) return { isColorUnset: true };
  return { background: hex, isColorUnset: false };
}

/** t537 ② — `bar`가 속한 4마디 행에 걸린 SCENE 메모(있으면). 메모는 그
 * 행의 시작 마디에 매달려 있다(`default_beat_grid`의 YAML 데이터, 행
 * 안의 어느 마디를 봐도 같은 메모가 보인다) — 없으면 `null`. */
export function sceneMemoForBar(
  memos: readonly BeatGridSceneMemo[],
  bar: number,
): BeatGridSceneMemo | null {
  const rowIndex = barRowIndex(bar);
  if (rowIndex === -1) return null;
  const [rowStart] = BEAT_GRID_BAR_ROWS[rowIndex];
  return memos.find((memo) => memo.bar === rowStart) ?? null;
}

/** t537 ② plan-audit iteration 3 D1 — "이 마디 한눈에" 패널이 실제로
 * 그리는 것(미정 배지 + §4 원문 텍스트 + `source_ref`, REQ-LDBEAT-006
 * (iv-3))을 DOM 없이 단언할 수 있게 뽑은 순수 파생. `visibleBarRange`에
 * 걸린 4마디 행마다 그 행에 메모가 있으면 하나씩 돌려준다(없는 행은
 * 결과에서 빠진다 — 추측 0건). `label`은 항상 `UNSET_FIELD_LABEL`("미정")
 * 이다 — 실제 화면은 이 자리에 "⚠" 배지로 보여주지만, 그 배지가 가리키는
 * 의미는 "이 칸은 트랙으로 못 옮겨 미정으로 남았다"는 것이고, `text` 자신도
 * §4 원문 그대로 "배정 미정 — ..."로 시작한다(`beat_grid_data/love_attack.yaml`
 * 참조) — 두 표기가 서로 다른 말이 아니다. */
export interface SceneMemoMarker {
  bar: number;
  label: string;
  text: string;
  sourceRef: string;
}

export function sceneMemoMarkers(
  memos: readonly BeatGridSceneMemo[],
  visibleBarRange: readonly [number, number],
): SceneMemoMarker[] {
  const [rangeStart, rangeEnd] = visibleBarRange;
  const rowStarts: number[] = [];
  for (const [rowStart, rowEnd] of BEAT_GRID_BAR_ROWS) {
    if (rowEnd < rangeStart || rowStart > rangeEnd) continue;
    rowStarts.push(rowStart);
  }
  const markers: SceneMemoMarker[] = [];
  for (const rowStart of rowStarts) {
    const memo = memos.find((candidate) => candidate.bar === rowStart);
    if (!memo) continue;
    markers.push({ bar: rowStart, label: UNSET_FIELD_LABEL, text: memo.text, sourceRef: memo.source_ref });
  }
  return markers;
}

/** t537 레이아웃 교정 — 곡 전체 지도의 구간 띠를 derive하는 데 필요한
 * 최소 필드. `ui/src/protocol.ts`의 `SongTimelineSection`은 상위집합이라
 * 그대로 넘겨도 된다(구조적 타이핑). */
export interface BeatGridSectionLite {
  label: string;
  start_ms: number;
  palette_primary_hex?: string | null;
}

export interface BeatGridSectionBlock {
  label: string;
  startBar: number;
  /** 배타적 — 다음 구간이 시작하는 마디(또는 표시 범위 끝+1). */
  endBar: number;
  hex: string | null;
}

/** 구간 레이블(`sections[].label`, 이미 서버가 보내는 값)을 `start_ms`
 * → 그 곡 BPM(`secondsPerBar`, `barToSeconds`의 역수 관계 — REQ-LDBEAT-
 * 005(b)와 같은 환산)으로 마디 위치로 옮긴다. 추측·보간 없음: 둘 중
 * 하나라도 없으면(구간 데이터 없음, BPM 미확정) 빈 배열 — 호출부가 숫자
 * 띠로 조용히 떨어진다(지어내지 않음). 표시 범위(`rangeStart`~`rangeEnd`)
 * 밖으로 완전히 벗어난 구간은 뺀다. */
export function deriveSectionBlocks(
  sections: readonly BeatGridSectionLite[] | undefined,
  secondsPerBar: number | null | undefined,
  rangeStart: number,
  rangeEnd: number,
): BeatGridSectionBlock[] {
  if (!sections || sections.length === 0) return [];
  if (!secondsPerBar || !Number.isFinite(secondsPerBar) || secondsPerBar <= 0) return [];
  const withBars = sections
    .map((section) => ({
      label: section.label,
      startBar: Math.max(0, Math.round(section.start_ms / 1000 / secondsPerBar)),
      hex: section.palette_primary_hex ?? null,
    }))
    .sort((a, b) => a.startBar - b.startBar);
  const blocks: BeatGridSectionBlock[] = [];
  for (let i = 0; i < withBars.length; i++) {
    const current = withBars[i];
    const next = withBars[i + 1];
    const blockEnd = next ? next.startBar : rangeEnd + 1;
    const clippedStart = Math.max(current.startBar, rangeStart);
    const clippedEnd = Math.min(blockEnd, rangeEnd + 1);
    if (clippedStart > rangeEnd || clippedEnd <= clippedStart) continue;
    blocks.push({ label: current.label, startBar: clippedStart, endBar: clippedEnd, hex: current.hex });
  }
  return blocks;
}

/** 곡 전체 지도 위 SCENE 메모 배지의 가로 위치(%) — 표시 범위 안에서
 * `bar`의 상대 위치다. flexbox 기반 구간 띠는 정확한 픽셀 경계를 미리
 * 알 수 없어서(브라우저가 레이아웃한다), 오버레이는 퍼센트로 둔다. */
export function barPercentInRange(bar: number, rangeStart: number, rangeEnd: number): number {
  const span = rangeEnd - rangeStart + 1;
  if (span <= 0) return 0;
  return ((bar - rangeStart) / span) * 100;
}

/** 카드 t551 계속 — 직접 고르기(①) 드롭다운 옵션 JSX. mockup `opts()`의
 * 세 부분을 그대로 옮긴다: "— 없음 —"는 여기서는 쓰지 않고(세 필드 다
 * 항상 값을 고른다, mockup의 `allowNone`은 위치·색이 "없음"을 허용하는
 * 자리였지만 이 카드는 적용/취소 버튼이 그 "되돌리기" 역할을 대신한다)
 * "이 곡 프리셋"(`usage_count > 0`) → "쇼에 이미 있는 프리셋"
 * (`usage_count === 0`) → "+ 새 프리셋 만들기…" 순서로 쌓는다. 비표준
 * JSX 헬퍼라 이 파일의 "DOM 없는 단위시험" 관례 밖에 있다 — 데이터
 * 가름(`splitDrawerSectionEntries`/`splitDrawerSectionEffectEntries`,
 * 둘 다 순수·시험됨)은 호출자가 끝내고, 이 함수는 그 결과를 그대로
 * JSX로만 옮긴다(카드 t551 계속 — 효과 드롭다운과 공유하려고 섹션이
 * 아니라 이미 가른 쌍을 받는다). */
function renderPresetOptions({
  thisSong,
  showExisting,
}: {
  thisSong: BeatGridDrawerEntry[];
  showExisting: BeatGridDrawerEntry[];
}) {
  return (
    <>
      {thisSong.length > 0 && (
        <optgroup label="이 곡 프리셋">
          {thisSong.map((entry) => (
            <option key={entry.preset_no} value={entry.preset_no}>
              {formatDrawerEntryOptionLabel(entry)}
            </option>
          ))}
        </optgroup>
      )}
      {showExisting.length > 0 && (
        <optgroup label="쇼에 이미 있는 프리셋">
          {showExisting.map((entry) => (
            <option key={entry.preset_no} value={entry.preset_no}>
              {formatDrawerEntryOptionLabel(entry)}
            </option>
          ))}
        </optgroup>
      )}
      <option value={NEW_PRESET_OPTION_VALUE}>＋ 새 프리셋 만들기…</option>
    </>
  );
}

export function BeatGrid({
  grid,
  fixtures = [],
  probeResults,
  secondsPerBar = null,
  colorPresetHex,
  sections,
  onEditRequest,
  onSentenceEditRequest,
  onSuggestionRequest,
  pendingSuggestion = null,
  onSuggestionAccept,
  onSuggestionReject,
  drawerSections = null,
  onDrawerRequest,
}: BeatGridProps) {
  const [openFolders, setOpenFolders] = useState<Set<string>>(() => new Set());
  const [allOpen, setAllOpen] = useState(true);
  const [selected, setSelected] = useState<{ trackIndex: number; bar: number } | null>(null);
  const [transitionView, setTransitionView] = useState(false);
  const [playbackSeconds, setPlaybackSeconds] = useState(0);
  const [audioName, setAudioName] = useState<string | null>(null);
  const [commandText, setCommandText] = useState("");
  // 카드 t551(M3) — 밝기 "값"(%) 인라인 편집(mockup "구조" 4). 선택이
  // 바뀌면(다른 칸을 클릭) 편집 중이던 입력을 닫는다 — 이전 칸의 입력값이
  // 새 칸에 실수로 적용되는 것을 막는다.
  // 카드 t551 계속 — 직접 고르기(①) 드롭다운(밝기/위치/색). mockup
  // "같은 자리에서" 그대로 한 번에 한 필드만 연다 — `activeEditField`가
  // 그 "자리"다.
  const [activeEditField, setActiveEditField] = useState<
    "밝기" | "위치 프리셋" | "색 프리셋" | "효과 프리셋" | null
  >(null);
  const [brightnessModeDraft, setBrightnessModeDraft] = useState<
    "value" | "dimmer_preset" | "dimmer_effect"
  >("value");
  const [brightnessDraft, setBrightnessDraft] = useState("");
  const [brightnessPresetDraft, setBrightnessPresetDraft] = useState("");
  // 카드 t551 계속(코디네이터 지시 2026-10-11, 조건 3) — 디머 "효과" 드롭다운
  // (brightnessModeDraft==="dimmer_effect")의 선택 초안.
  const [brightnessEffectDraft, setBrightnessEffectDraft] = useState("");
  const [positionPresetDraft, setPositionPresetDraft] = useState("");
  const [colorPresetDraft, setColorPresetDraft] = useState("");
  // 카드 t551 계속 — 효과(움직임) 프리셋 직접 고르기(무빙 전용, "효과 프리셋" 행).
  const [effectPresetDraft, setEffectPresetDraft] = useState("");
  // mockup `newPreset()` — "+ 새 프리셋" 선택지는 적용하지 않고 안내만
  // 띄운다(새 프리셋 생성은 이 카드 범위 밖, M4/별도 카드).
  const [newPresetNote, setNewPresetNote] = useState<string | null>(null);
  // 카드 t551 후속(지시 1항) — 프리셋 서랍 열림/강조 상태(mockup `.drawer.open`/
  // `hlP`). 강조는 서랍을 닫아도 유지하지 않는다 — 다시 열면 깨끗한 상태.
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [highlightedPresetNo, setHighlightedPresetNo] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const folders = useMemo(() => groupTracksByLayerFolder(grid?.tracks ?? []), [grid]);
  // t537 — M1 상태의 살아있는 소스는 `grid.probe_results`(서버가 progress.md를
  // 그 자리에서 읽어 채운 값)다. `probeResults` prop은 명시적으로 다른 값을
  // 넘기고 싶을 때만 쓰는 override다(시험·예외 상황) — 둘 다 없으면
  // `buildProbeStatusTable`이 9항목 전부 "미확인"으로 떨어진다.
  const probes = useMemo(
    () => buildProbeStatusTable(probeResults ?? grid?.probe_results),
    [probeResults, grid],
  );
  const writeLocked = isWriteLocked(probes);
  const stageBounds = useMemo(() => computeStageBounds(fixtures), [fixtures]);

  if (!grid) {
    return (
      <section className="beat-grid" aria-label="박자 격자">
        <p className="beat-grid-empty">박자 격자 데이터가 아직 없습니다.</p>
      </section>
    );
  }

  const maxBar = grid.bar_range.end;
  const isFolderOpen = (role: string) => allOpen || openFolders.has(role);
  const toggleFolder = (role: string) => {
    setOpenFolders((prev) => {
      const next = new Set(prev);
      if (isFolderOpen(role)) {
        // 전역이 열림이면 이 폴더만 닫는 것이므로, 전역 "모두 펴기" 상태를
        // 끈 채 나머지만 열린 집합으로 바꾼다.
        setAllOpen(false);
        next.clear();
        for (const f of folders) if (f.role !== role) next.add(f.role);
      } else {
        next.add(role);
      }
      return next;
    });
  };
  const toggleAll = () => {
    if (allOpen || openFolders.size > 0) {
      setAllOpen(false);
      setOpenFolders(new Set());
    } else {
      setAllOpen(true);
    }
  };

  const selectedTrack = selected ? grid.tracks[selected.trackIndex] : null;
  const selectedCue = selectedTrack && selected ? cueForBar(selectedTrack, selected.bar) : null;
  const firstCue = selected ? isFirstCueOfSong(selected.bar, grid) : false;
  const viewBar = selected?.bar ?? grid.bar_range.start;
  // t537 ② plan-audit iteration 3 D1 — 실제로 렌더하는 배지+원문+source_ref
  // 묶음은 `sceneMemoMarkers`가 반환하는 모양 그대로다(DOM 없이 단언 가능).
  const viewBarSceneMemo = sceneMemoMarkers(grid.scene_memos, [viewBar, viewBar])[0] ?? null;
  // t537 레이아웃 교정 — 곡 전체 지도 구간 띠(데이터 없으면 빈 배열, 호출부가
  // 숫자 띠로 떨어진다) + SCENE 메모 오버레이의 퍼센트 위치 헬퍼.
  const sectionBlocks = useMemo(
    () => deriveSectionBlocks(sections, secondsPerBar, grid.bar_range.start, grid.bar_range.end),
    [sections, secondsPerBar, grid.bar_range.start, grid.bar_range.end],
  );
  const barPercent = (bar: number) => barPercentInRange(bar, grid.bar_range.start, grid.bar_range.end);
  // 카드 t534 — 재생 위치를 마디로 환산(음원 동기가 없으면 null, 지어내지
  // 않음). 플레이헤드 선·"이 마디 한눈에" 둘 다 이 값이 있을 때만 재생
  // 위치를 반영한다 — 없으면 선택된 칸(or 시작 마디)이 기준이다.
  const playheadBar = secondsToBar(playbackSeconds, secondsPerBar, maxBar);
  const laneContentWidth = barToX(maxBar + 1);

  const onSelectAudio = (file: File | null) => {
    if (!file) return;
    setAudioName(file.name);
    if (audioRef.current) {
      audioRef.current.src = URL.createObjectURL(file);
    }
  };

  const seek = (delta: number) => {
    const totalSeconds = barToSeconds(maxBar, secondsPerBar) ?? playbackSeconds;
    const next = clampSkipSeconds(playbackSeconds, delta, totalSeconds);
    setPlaybackSeconds(next);
    if (audioRef.current) audioRef.current.currentTime = next;
  };

  return (
    <section className="beat-grid" aria-label="박자 격자">
      <header className="beat-grid-head">
        <span className="beat-grid-title">박자 격자</span>
        <span className="beat-grid-song">{grid.song_title || "(곡 미지정)"}</span>
        {grid.note && <span className="beat-grid-note">{grid.note}</span>}
        <span className="beat-grid-range">
          {grid.bar_range.start}~{grid.bar_range.end}마디
        </span>
      </header>

      {/* ① 곡 전체 지도 — 시안처럼 구간(인트로/벌스/코러스…) 블록 띠(REQ-
          LDBEAT-004(a)). 구간 레이블은 `timeline.sections`(서버가 이미
          보내는 값)에서, 블록 경계는 `start_ms`를 그 곡 BPM(`secondsPerBar`)
          으로 마디 환산해 derive한다(지어내지 않음 — REQ-LDBEAT-005(b)와
          같은 환산) — 그 데이터가 없으면(secondsPerBar 미확정 등) 기존
          7칸 숫자 띠로 조용히 떨어진다(추측 대신 "아는 만큼만"). SCENE
          메모가 걸린 마디는 그 위에 퍼센트 위치로 겹쳐 그린 「미정」
          배지로 보여준다(t537 ②, 리드 지시). 시안처럼 "전체 곡 중 지금
          보는 범위를 강조"는 전체 곡 길이(마디 수) 데이터가 아직 없어
          못 했다 — 지도 자체가 그 표시 범위(0~25마디)다(§Gaps). */}
      <div className="beat-grid-overview" role="img" aria-label="곡 전체 지도">
        <div className="beat-grid-overview-track">
          {sectionBlocks.length > 0
            ? sectionBlocks.map((block) => (
                <span
                  key={`${block.label}-${block.startBar}`}
                  className={`beat-grid-overview-section${
                    viewBar >= block.startBar && viewBar < block.endBar ? " is-current" : ""
                  }`}
                  style={{ flexGrow: block.endBar - block.startBar, background: block.hex ?? undefined }}
                  title={`${block.label} · ${block.startBar}~${block.endBar - 1}마디`}
                >
                  {block.label}
                </span>
              ))
            : BEAT_GRID_BAR_ROWS.map(([start, end]) => (
                <span
                  key={start}
                  className={`beat-grid-overview-section${barRowIndex(viewBar) === barRowIndex(start) ? " is-current" : ""}`}
                  style={{ flexGrow: end - start + 1 }}
                  title={`${start}~${end}마디`}
                >
                  {start}
                </span>
              ))}
        </div>
        <div className="beat-grid-overview-memos">
          {grid.scene_memos.map((memo) => (
            <span
              key={memo.bar}
              className="beat-grid-overview-memo-marker"
              style={{ left: `${barPercent(memo.bar)}%` }}
              title={memo.text}
            >
              ⚠ 미정
            </span>
          ))}
        </div>
      </div>

      <div className="beat-grid-toolbar">
        <button type="button" className="beat-grid-fold-all" onClick={toggleAll}>
          [모두 접기/펴기]
        </button>
        <span className="beat-grid-transport">
          <button type="button" onClick={() => seek(-10)}>
            ⏪ 10초
          </button>
          <button type="button" onClick={() => seek(10)}>
            10초 ⏩
          </button>
          <span className="beat-grid-clock">{playbackSeconds.toFixed(1)}초</span>
          <label className="beat-grid-audio-label">
            ♪ {audioName ?? "음원"}
            <input
              type="file"
              accept="audio/*"
              hidden
              onChange={(event) => onSelectAudio(event.target.files?.[0] ?? null)}
            />
          </label>
          <audio ref={audioRef} hidden />
        </span>
        {writeLocked && (
          <span className="beat-grid-locked" title="M1 프로브 9항목 중 미확인 항목이 있어 쓰기가 잠겨 있습니다">
            ⚠ 쓰기 잠김
          </span>
        )}
      </div>

      {/* ② 그룹-트랙 타임라인 — 마디 시간축 위 칸 막대(카드 t534, REQ-LDBEAT-004).
          곡 전체 지도·자(마디 눈금)는 `.beat-grid-lanes` 스크롤 안에서
          `position:sticky`로 위에 고정되고, 폴더는 좌우 스크롤 + 한 화면
          고정 높이(REQ-LDBEAT-004(b)). t537 레이아웃 교정 — 타임라인과
          큐 편집 칸을 한 줄(`.beat-grid-mid`)에 나란히(시안 `.mid` =
          `.lanes`+`.sidepane`), 무대·한눈에는 그 아래 별도 띠(아래
          `.beat-grid-insp`)로 뺐다. */}
      <div className="beat-grid-mid">
        <div className="beat-grid-lanes" role="table" aria-label="콘솔 그룹 트랙 타임라인">
          {/* 자(마디 눈금) — 세로 스크롤 중에도 위에 고정(시안 `.ruler`). */}
          <div className="beat-grid-ruler-row">
            <span className="beat-grid-track-label beat-grid-ruler-corner">마디</span>
            <div className="beat-grid-ruler" style={{ width: laneContentWidth }}>
              {Array.from({ length: maxBar - grid.bar_range.start + 1 }, (_, i) => grid.bar_range.start + i).map(
                (bar) => (
                  <span
                    key={bar}
                    className={`beat-grid-ruler-tick${playheadBar === bar ? " is-playhead" : ""}${
                      viewBar === bar ? " is-view" : ""
                    }`}
                    style={{ left: barToX(bar), width: PX_PER_BAR }}
                  >
                    {bar}
                  </span>
                ),
              )}
            </div>
          </div>

          {folders.map((folder) => {
            const open = isFolderOpen(folder.role);
            return (
              <div className="beat-grid-folder" key={folder.role}>
                <button
                  type="button"
                  className="beat-grid-folder-head"
                  onClick={() => toggleFolder(folder.role)}
                >
                  {open ? "▾" : "▸"} {folder.label} ({folder.tracks.length}줄)
                </button>
                {open &&
                  folder.tracks.map((track) => {
                    const trackIndex = grid.tracks.indexOf(track);
                    const segments = trackCueSegments(track, maxBar);
                    const leadGapEnd = segments[0]?.startBar ?? maxBar + 1;
                    return (
                      <div className="beat-grid-track" role="row" key={`${track.group_name}-${trackIndex}`}>
                        <span className="beat-grid-track-label">
                          {track.group_name}
                          {!track.group_no_confirmed && (
                            <span className="beat-grid-unconfirmed-badge" title="콘솔 그룹 번호 미확인">
                              ⚠
                            </span>
                          )}
                        </span>
                        <div className="beat-grid-track-cues" style={{ width: laneContentWidth }}>
                          {segments.length === 0 && (
                            <span className="beat-grid-cue-empty">이 구간에 칸 없음</span>
                          )}
                          {/* 첫 칸 앞의 빈 구간 — "아직 선언 안 됨"을 지어내지 않고 그대로
                              빈 칸으로 보인다(시안 `.clip.empty`). */}
                          {leadGapEnd > grid.bar_range.start && (
                            <span
                              className="beat-grid-cue beat-grid-cue-gap"
                              style={{ left: barToX(grid.bar_range.start), width: barToX(leadGapEnd) - barToX(grid.bar_range.start) - 2 }}
                            >
                              —
                            </span>
                          )}
                          {segments.map((segment, segIndex) => {
                            const isSelected = selected?.trackIndex === trackIndex && selected.bar === segment.cue.bar;
                            const active = cueIsActive(segment.cue.label);
                            const hasNext = segIndex < segments.length - 1;
                            // t537 (3) — 막대 채우기 색은 color_preset_no가 실제 색을
                            // 아는 자리일 때만 쓴다. 지금 LOVE ATTACK 기본값은 §4에
                            // 프리셋 번호가 없어(REQ-LDBEAT-015(f)) 전부 미정이고,
                            // 그 경우 임의 색을 지어내지 않고 중립(해칭)으로 보인다.
                            const colorFill = cueColorFill(segment.cue, colorPresetHex);
                            // 카드 t551 후속(지시 1항) — 프리셋 서랍에서 고른 항목을
                            // "누르면 쓰는 막대가 노랗게"(mockup `drawDrawer()` 안내).
                            const isHighlighted =
                              highlightedPresetNo !== null &&
                              cueReferencesPreset(segment.cue, highlightedPresetNo);
                            return (
                              <span key={segment.cue.bar} className="beat-grid-cue-slot">
                                <button
                                  type="button"
                                  className={`beat-grid-cue${isSelected ? " is-selected" : ""}${active ? "" : " is-off"}${
                                    active && colorFill.isColorUnset ? " is-color-unset" : ""
                                  }${isHighlighted ? " is-preset-highlighted" : ""}`}
                                  style={{
                                    left: barToX(segment.startBar),
                                    width: barToX(segment.endBar) - barToX(segment.startBar) - 2,
                                    ...(colorFill.background ? { backgroundColor: colorFill.background } : {}),
                                  }}
                                  title={`${segment.startBar}~${segment.endBar - 1}마디${
                                    colorFill.isColorUnset && active ? " · 색 미정" : ""
                                  }`}
                                  onClick={() => {
                                    setSelected({ trackIndex, bar: segment.cue.bar });
                                    setTransitionView(false);
                                    setActiveEditField(null);
                                    setNewPresetNote(null);
                                  }}
                                >
                                  {segment.cue.label}
                                  {isUnconfirmedShapeCue(segment.cue.label) && (
                                    <span className="beat-grid-shape-warn" title="실기 미확인 모양">
                                      ⚠ 실기 미확인
                                    </span>
                                  )}
                                </button>
                                {hasNext && (
                                  <button
                                    type="button"
                                    className="beat-grid-joint"
                                    style={{ left: barToX(segment.endBar) }}
                                    title={`${segment.endBar}마디 이음매 — 전환 편집 열기`}
                                    onClick={() => {
                                      const nextCue = segments[segIndex + 1].cue;
                                      setSelected({ trackIndex, bar: nextCue.bar });
                                      setTransitionView(true);
                                      setActiveEditField(null);
                                      setNewPresetNote(null);
                                    }}
                                  >
                                    ◆
                                  </button>
                                )}
                              </span>
                            );
                          })}
                          {playheadBar !== null && (
                            <span
                              className="beat-grid-playhead"
                              style={{ left: barToX(playheadBar) }}
                              title={`재생 위치 — ${playheadBar}마디`}
                            />
                          )}
                          {/* mockup "AI 제안은 타임라인에 점선 막대로 미리 보임"
                              (카드 t551 후속, 지시 1항 — "AI-suggestion dashed-bar
                              render"). 「적용」·「거절」 전까지 격자는 바뀌지
                              않는다 — 이 막대는 그 보류 상태의 시각 표시일
                              뿐이다(결정④, 상태 diff 0). */}
                          {isPendingSuggestionForTrack(pendingSuggestion, track.group_name) && (
                            <span
                              className="beat-grid-cue beat-grid-cue-ghost"
                              style={{ left: barToX(pendingSuggestion!.bar), width: PX_PER_BAR - 2 }}
                              title={`AI 제안(보류) — ${pendingSuggestion!.rationale}`}
                            >
                              AI 제안(보류)
                            </span>
                          )}
                        </div>
                      </div>
                    );
                  })}
              </div>
            );
          })}
          {folders.length === 0 && (
            <p className="beat-grid-empty">{grid.note ?? "표시할 트랙이 없습니다."}</p>
          )}
        </div>

        {/* 큐 편집 칸 — 시안처럼 "타임라인 바로 오른쪽에 늘 있음"(선택 전엔
            빈 안내, t537 레이아웃 교정 — `.beat-grid-mid`의 두 번째 칸).
            밝기/위치/색/들어올 때 네 필드를 보여 준다(REQ-LDBEAT-004(c)(d)).
            카드 t551(M3) — 밝기 "값"(%)만 `onEditRequest`가 있으면 그
            자리에서 고칠 수 있다(mockup "표의 ... 칸을 누르면 그 자리에서
            바로 고쳐지고"); 위치/색/효과/디머 프리셋은 프리셋 카탈로그가
            없어 여전히 읽기 전용이다(progress.md "## Missing Inputs"). */}
        <aside className="beat-grid-cue-panel" aria-label="큐 편집 칸">
          {pendingSuggestion ? (
            // mockup `#bAi` 핸들러(지시 1항) — AI 제안이 보류 중인 동안은
            // 이 칸이 "AI 제안" 카드로 바뀐다(평소 큐 편집 대신). 「적용」·
            // 「거절」 전까지 격자·콘솔은 바뀌지 않는다(결정④).
            <div className="beat-grid-ai-suggestion" aria-label="AI 제안">
              <header>
                <span>AI 제안</span>
                <span>
                  {pendingSuggestion.target} {pendingSuggestion.bar}마디
                </span>
              </header>
              <p>{pendingSuggestion.rationale}</p>
              <p className="fx">타임라인의 점선 막대가 제안이에요.</p>
              <div className="beat-grid-ai-suggestion-actions">
                <button
                  type="button"
                  className="tbtn pri"
                  onClick={() => onSuggestionAccept?.(pendingSuggestion.suggestion_id)}
                >
                  수락
                </button>
                <button
                  type="button"
                  onClick={() => onSuggestionReject?.(pendingSuggestion.suggestion_id)}
                >
                  거절
                </button>
              </div>
            </div>
          ) : selected && selectedTrack ? (
            <>
              <header>
                <span>
                  {selectedTrack.group_name} · {selected.bar}마디
                </span>
                <span className="beat-grid-cue-panel-actions">
                  <button
                    type="button"
                    className={`beat-grid-transition-toggle${transitionView ? " is-on" : ""}`}
                    disabled={firstCue}
                    title={firstCue ? "곡 첫 큐 — 들어오는 전환 없음" : undefined}
                    onClick={() => setTransitionView((v) => !v)}
                  >
                    전환
                  </button>
                  <button type="button" aria-label="닫기" onClick={() => setSelected(null)}>
                    ✕
                  </button>
                </span>
              </header>
              {transitionView ? (
                <div className="beat-grid-transition-view">
                  <p>들어오는 전환 — 페이드 · 트리거 박 · 딜레이 · 트래킹(M3 배선 전까지 읽기 전용)</p>
                </div>
              ) : (
                <div className="beat-grid-cue-view">
                  {/* t537 — 속성별 값을 각각 독립된 자리에(REQ-LDBEAT-004(c),
                      감독 결정 「전체 화면 + 속성별 값」). 같은 문장을 네 번
                      반복하던 M2후속 임시 동작을 걷어냈다 — `label`은 아래
                      "설명(원문)" 한 줄로만 남아 구조화 필드와 혼동되지 않는다. */}
                  {(() => {
                    const hints = roleFieldHints(selectedTrack.layer_role);
                    const rows: { field: string; value: string; sourceRef?: string | null }[] = [];
                    if (selectedCue) {
                      rows.push({ field: "밝기", value: formatBrightnessField(selectedCue.brightness) });
                      if (hints.includes("위치")) {
                        rows.push({ field: "위치 프리셋", value: formatPresetField(selectedCue.position_preset_no) });
                      }
                      if (hints.includes("색")) {
                        rows.push({ field: "색 프리셋", value: formatPresetField(selectedCue.color_preset_no) });
                      }
                      if (hints.includes("움직임")) {
                        const effectValue = formatPresetField(selectedCue.effect_preset_no);
                        rows.push({
                          field: "효과 프리셋",
                          value: selectedCue.effect_kind ? `${effectValue} (${selectedCue.effect_kind})` : effectValue,
                        });
                      }
                      // t548 — 앱 2단계 무빙(REQ-LDBEAT-006(vi))과 근거 등급(vii)은
                      // 값이 있는 칸에서만 보인다. 경고 둘은 거절이 아니라 표시다.
                      if (selectedCue.app_movement) {
                        rows.push({ field: "앱 무빙", value: formatAppMovementField(selectedCue.app_movement) });
                      }
                      if (selectedCue.evidence) {
                        rows.push({ field: "근거", value: formatEvidenceField(selectedCue.evidence) });
                      }
                      const axisConflict = appMovementAxisConflictWarning(selectedCue);
                      if (axisConflict) rows.push({ field: "같은 축", value: axisConflict });
                      const panOnly = panOnlyVerticalBaseWarning(selectedCue);
                      if (panOnly) rows.push({ field: "기준 위치", value: panOnly });
                    }
                    // 카드 t551 계속 — 직접 고르기(①) 드롭다운(mockup "구조" 4 +
                    // "막대 → 오른쪽 큐 편집": 위치·색·밝기(디머 프리셋)는
                    // `drawerSections`에서 "이 곡 프리셋"/"쇼에 이미 있는
                    // 프리셋"/"+ 새 프리셋"으로 고른다). 효과(움직임)·디머
                    // "효과"는 아직 읽기 전용(아래 Missing Inputs 참조).
                    const positionSection = findDrawerSection(drawerSections, "Position");
                    const colorSection = findDrawerSection(drawerSections, "Color");
                    const dimmerSection = findDrawerSection(drawerSections, "Dimmer");
                    const closeEdit = () => {
                      setActiveEditField(null);
                      setNewPresetNote(null);
                    };
                    const poolStatusNote = (section: BeatGridDrawerSection | null): string | null => {
                      if (!section) return "프리셋 서랍을 먼저 열어야 선택할 수 있습니다.";
                      if (section.unread) return "이 풀을 콘솔에서 읽지 못했습니다.";
                      return null;
                    };
                    return rows.map((row) => {
                      const isBrightnessRow = row.field === "밝기";
                      const isPositionRow = row.field === "위치 프리셋";
                      const isColorRow = row.field === "색 프리셋";
                      // 카드 t551 계속(코디네이터 지시 2026-10-11, 조건 1/3) —
                      // 효과(움직임) 프리셋 직접 고르기(무빙 전용 행).
                      const isEffectRow = row.field === "효과 프리셋";
                      const editable =
                        !!onEditRequest &&
                        (isBrightnessRow || isPositionRow || isColorRow || isEffectRow);
                      const editing = editable && activeEditField === row.field;
                      return (
                        <div className="beat-grid-cue-field" key={row.field}>
                          <span className="beat-grid-cue-field-label">{row.field}</span>
                          {editing && isBrightnessRow ? (
                            // 카드 t551 계속 — 밝기 단일모드(값/디머 프리셋/디머
                            // 효과, REQ-LDBEAT-015(c)) — mockup `#eM`/`eDimMode`
                            // 3항 선택 그대로. "디머 효과"는 아직 목록이 없어
                            // 읽기 전용 안내만(Missing Inputs).
                            <span className="beat-grid-cue-field-edit">
                              <select
                                value={brightnessModeDraft}
                                aria-label="밝기 모드"
                                onChange={(event) => {
                                  const mode = event.target.value as typeof brightnessModeDraft;
                                  setBrightnessModeDraft(mode);
                                  setNewPresetNote(null);
                                }}
                              >
                                <option value="value">값</option>
                                <option value="dimmer_preset">디머 프리셋</option>
                                <option value="dimmer_effect">디머 효과</option>
                              </select>
                              {brightnessModeDraft === "value" && (
                                <input
                                  type="number"
                                  min={0}
                                  max={100}
                                  value={brightnessDraft}
                                  onChange={(event) => setBrightnessDraft(event.target.value)}
                                  aria-label="밝기 값(%)"
                                />
                              )}
                              {brightnessModeDraft === "dimmer_preset" && (
                                <select
                                  value={brightnessPresetDraft}
                                  disabled={!dimmerSection || dimmerSection.unread}
                                  aria-label="디머 프리셋"
                                  onChange={(event) => {
                                    const value = event.target.value;
                                    setBrightnessPresetDraft(value);
                                    setNewPresetNote(
                                      value === NEW_PRESET_OPTION_VALUE
                                        ? "＋ 새 프리셋 만들기 — 이름·값을 정하는 창은 아직 배선되지 않았습니다(M4/별도 카드)."
                                        : null,
                                    );
                                  }}
                                >
                                  {renderPresetOptions(splitDrawerSectionEntries(dimmerSection))}
                                </select>
                              )}
                              {brightnessModeDraft === "dimmer_effect" && (
                                <select
                                  value={brightnessEffectDraft}
                                  disabled={!dimmerSection || dimmerSection.unread}
                                  aria-label="디머 효과"
                                  onChange={(event) => {
                                    const value = event.target.value;
                                    setBrightnessEffectDraft(value);
                                    setNewPresetNote(
                                      value === NEW_PRESET_OPTION_VALUE
                                        ? "＋ 새 프리셋 만들기 — 이름·값을 정하는 창은 아직 배선되지 않았습니다(M4/별도 카드)."
                                        : null,
                                    );
                                  }}
                                >
                                  {renderPresetOptions(splitDrawerSectionEffectEntries(dimmerSection))}
                                </select>
                              )}
                              <button
                                type="button"
                                onClick={() => {
                                  if (brightnessModeDraft === "value") {
                                    const changes = buildBrightnessValueChanges(Number(brightnessDraft));
                                    if (changes && selected && selectedTrack) {
                                      onEditRequest!({ bar: selected.bar, target: selectedTrack.group_name, changes });
                                    }
                                  } else if (
                                    brightnessModeDraft === "dimmer_preset" &&
                                    brightnessPresetDraft &&
                                    brightnessPresetDraft !== NEW_PRESET_OPTION_VALUE &&
                                    selected &&
                                    selectedTrack
                                  ) {
                                    onEditRequest!({
                                      bar: selected.bar,
                                      target: selectedTrack.group_name,
                                      changes: buildBrightnessPresetChanges(brightnessPresetDraft),
                                    });
                                  } else if (
                                    brightnessModeDraft === "dimmer_effect" &&
                                    brightnessEffectDraft &&
                                    brightnessEffectDraft !== NEW_PRESET_OPTION_VALUE &&
                                    selected &&
                                    selectedTrack
                                  ) {
                                    onEditRequest!({
                                      bar: selected.bar,
                                      target: selectedTrack.group_name,
                                      changes: buildBrightnessDimmerEffectChanges(brightnessEffectDraft),
                                    });
                                  }
                                  closeEdit();
                                }}
                              >
                                적용
                              </button>
                              <button type="button" onClick={closeEdit}>
                                취소
                              </button>
                              {(brightnessModeDraft === "dimmer_preset" ||
                                brightnessModeDraft === "dimmer_effect") &&
                                poolStatusNote(dimmerSection) && (
                                  <p className="beat-grid-cue-field-note">{poolStatusNote(dimmerSection)}</p>
                                )}
                              {/* 카드 t551 계속(코디네이터 지시 2026-10-11, 조건 2) —
                                  confirmed:false 인 동안 디머 효과 드롭다운 옆에도
                                  "번호대 미확인" 배지(서랍과 같은 배지, `presetPoolBandBadge`). */}
                              {brightnessModeDraft === "dimmer_effect" &&
                                dimmerSection &&
                                presetPoolBandBadge(dimmerSection) && (
                                  <p className="beat-grid-cue-field-note u">
                                    {presetPoolBandBadge(dimmerSection)}
                                  </p>
                                )}
                              {newPresetNote && <p className="beat-grid-cue-field-note">{newPresetNote}</p>}
                            </span>
                          ) : editing && isPositionRow ? (
                            // 카드 t551 계속 — 위치 프리셋 직접 고르기(mockup
                            // "이 곡 프리셋"/"쇼에 이미 있는 프리셋"/"+ 새
                            // 프리셋", 앞선 `ldbeat-runbook-mockup-20261008.html`
                            // `opts()` 그대로).
                            <span className="beat-grid-cue-field-edit">
                              <select
                                value={positionPresetDraft}
                                disabled={!positionSection || positionSection.unread}
                                aria-label="위치 프리셋"
                                onChange={(event) => {
                                  const value = event.target.value;
                                  setPositionPresetDraft(value);
                                  setNewPresetNote(
                                    value === NEW_PRESET_OPTION_VALUE
                                      ? "＋ 새 프리셋 만들기 — 이름·값을 정하는 창은 아직 배선되지 않았습니다(M4/별도 카드)."
                                      : null,
                                  );
                                }}
                              >
                                {renderPresetOptions(splitDrawerSectionEntries(positionSection))}
                              </select>
                              <button
                                type="button"
                                onClick={() => {
                                  if (
                                    positionPresetDraft &&
                                    positionPresetDraft !== NEW_PRESET_OPTION_VALUE &&
                                    selected &&
                                    selectedTrack
                                  ) {
                                    onEditRequest!({
                                      bar: selected.bar,
                                      target: selectedTrack.group_name,
                                      changes: buildPositionPresetChanges(positionPresetDraft),
                                    });
                                  }
                                  closeEdit();
                                }}
                              >
                                적용
                              </button>
                              <button type="button" onClick={closeEdit}>
                                취소
                              </button>
                              {poolStatusNote(positionSection) && (
                                <p className="beat-grid-cue-field-note">{poolStatusNote(positionSection)}</p>
                              )}
                              {newPresetNote && <p className="beat-grid-cue-field-note">{newPresetNote}</p>}
                            </span>
                          ) : editing && isColorRow ? (
                            // 카드 t551 계속 — 색 프리셋 직접 고르기(위치와 같은
                            // 패턴, `colorSection` 출처만 다르다).
                            <span className="beat-grid-cue-field-edit">
                              <select
                                value={colorPresetDraft}
                                disabled={!colorSection || colorSection.unread}
                                aria-label="색 프리셋"
                                onChange={(event) => {
                                  const value = event.target.value;
                                  setColorPresetDraft(value);
                                  setNewPresetNote(
                                    value === NEW_PRESET_OPTION_VALUE
                                      ? "＋ 새 프리셋 만들기 — 이름·값을 정하는 창은 아직 배선되지 않았습니다(M4/별도 카드)."
                                      : null,
                                  );
                                }}
                              >
                                {renderPresetOptions(splitDrawerSectionEntries(colorSection))}
                              </select>
                              <button
                                type="button"
                                onClick={() => {
                                  if (
                                    colorPresetDraft &&
                                    colorPresetDraft !== NEW_PRESET_OPTION_VALUE &&
                                    selected &&
                                    selectedTrack
                                  ) {
                                    onEditRequest!({
                                      bar: selected.bar,
                                      target: selectedTrack.group_name,
                                      changes: buildColorPresetChanges(colorPresetDraft),
                                    });
                                  }
                                  closeEdit();
                                }}
                              >
                                적용
                              </button>
                              <button type="button" onClick={closeEdit}>
                                취소
                              </button>
                              {poolStatusNote(colorSection) && (
                                <p className="beat-grid-cue-field-note">{poolStatusNote(colorSection)}</p>
                              )}
                              {newPresetNote && <p className="beat-grid-cue-field-note">{newPresetNote}</p>}
                            </span>
                          ) : editing && isEffectRow ? (
                            // 카드 t551 계속(코디네이터 지시 2026-10-11, 조건 1·2) —
                            // 효과(움직임) 프리셋 직접 고르기. `positionSection`에서
                            // `is_effect_band`인 항목만(위치 효과 풀, mockup
                            // 14-17/26-29행 — "위치 효과 → 위치 풀 2") 고른다.
                            <span className="beat-grid-cue-field-edit">
                              <select
                                value={effectPresetDraft}
                                disabled={!positionSection || positionSection.unread}
                                aria-label="효과(움직임) 프리셋"
                                onChange={(event) => {
                                  const value = event.target.value;
                                  setEffectPresetDraft(value);
                                  setNewPresetNote(
                                    value === NEW_PRESET_OPTION_VALUE
                                      ? "＋ 새 프리셋 만들기 — 이름·값을 정하는 창은 아직 배선되지 않았습니다(M4/별도 카드)."
                                      : null,
                                  );
                                }}
                              >
                                {renderPresetOptions(splitDrawerSectionEffectEntries(positionSection))}
                              </select>
                              <button
                                type="button"
                                onClick={() => {
                                  if (
                                    effectPresetDraft &&
                                    effectPresetDraft !== NEW_PRESET_OPTION_VALUE &&
                                    selected &&
                                    selectedTrack
                                  ) {
                                    onEditRequest!({
                                      bar: selected.bar,
                                      target: selectedTrack.group_name,
                                      changes: buildEffectPresetChanges(effectPresetDraft),
                                    });
                                  }
                                  closeEdit();
                                }}
                              >
                                적용
                              </button>
                              <button type="button" onClick={closeEdit}>
                                취소
                              </button>
                              {poolStatusNote(positionSection) && (
                                <p className="beat-grid-cue-field-note">{poolStatusNote(positionSection)}</p>
                              )}
                              {/* 조건2 — confirmed:false 인 동안 서랍과 같은 배지. */}
                              {positionSection && presetPoolBandBadge(positionSection) && (
                                <p className="beat-grid-cue-field-note u">
                                  {presetPoolBandBadge(positionSection)}
                                </p>
                              )}
                              {newPresetNote && <p className="beat-grid-cue-field-note">{newPresetNote}</p>}
                            </span>
                          ) : (
                            <span
                              className={`beat-grid-cue-field-value${row.value === UNSET_FIELD_LABEL ? " is-unset" : ""}${
                                editable ? " is-editable" : ""
                              }`}
                              onClick={
                                editable
                                  ? () => {
                                      if (isBrightnessRow) {
                                        const mode = selectedCue?.brightness.mode ?? "value";
                                        setBrightnessModeDraft(
                                          mode === "dimmer_preset" || mode === "dimmer_effect" ? mode : "value",
                                        );
                                        const currentValue = selectedCue?.brightness.value_percent;
                                        setBrightnessDraft(currentValue != null ? String(currentValue) : "");
                                        setBrightnessPresetDraft(
                                          mode === "dimmer_preset" ? selectedCue?.brightness.preset_no ?? "" : "",
                                        );
                                        setBrightnessEffectDraft(
                                          mode === "dimmer_effect" ? selectedCue?.brightness.preset_no ?? "" : "",
                                        );
                                      } else if (isPositionRow) {
                                        setPositionPresetDraft(selectedCue?.position_preset_no ?? "");
                                      } else if (isColorRow) {
                                        setColorPresetDraft(selectedCue?.color_preset_no ?? "");
                                      } else if (isEffectRow) {
                                        setEffectPresetDraft(selectedCue?.effect_preset_no ?? "");
                                      }
                                      setNewPresetNote(null);
                                      setActiveEditField(
                                        row.field as "밝기" | "위치 프리셋" | "색 프리셋" | "효과 프리셋",
                                      );
                                    }
                                  : undefined
                              }
                            >
                              {row.value}
                              {editable && " ✎"}
                            </span>
                          )}
                        </div>
                      );
                    });
                  })()}
                  <div className="beat-grid-cue-field beat-grid-cue-field-entry">
                    <span className="beat-grid-cue-field-label">들어올 때</span>
                    <span className="beat-grid-cue-field-value">
                      {selectedCue ? formatFadeBarsField(selectedCue.entry.fade_bars) : UNSET_FIELD_LABEL}
                      {selectedCue &&
                        (() => {
                          const derivedSeconds = deriveFadeSeconds(selectedCue.entry.fade_bars, secondsPerBar);
                          return derivedSeconds !== null ? (
                            <span className="beat-grid-cue-field-derived"> (≈{derivedSeconds.toFixed(1)}초, derived)</span>
                          ) : null;
                        })()}
                    </span>
                    <button
                      type="button"
                      className="beat-grid-cue-field-entry-btn"
                      disabled={firstCue}
                      onClick={() => setTransitionView(true)}
                    >
                      {firstCue ? "곡 첫 큐 — 전환 없음" : "전환 보기 열기 ›"}
                    </button>
                  </div>
                  {selectedCue?.source_ref && (
                    <div className="beat-grid-cue-field beat-grid-cue-field-source">
                      <span className="beat-grid-cue-field-label">출처</span>
                      <span className="beat-grid-cue-field-value">
                        {formatSourceRefLabel(selectedCue.source_ref)}
                      </span>
                    </div>
                  )}
                  <div className="beat-grid-cue-field beat-grid-cue-field-label-row">
                    <span className="beat-grid-cue-field-label">설명(원문)</span>
                    <span className="beat-grid-cue-field-value">{selectedCue?.label ?? "—"}</span>
                  </div>
                </div>
              )}
            </>
          ) : (
            <p className="beat-grid-empty beat-grid-cue-panel-empty">
              막대(큐)를 누르면 밝기·위치·색·들어올 때를 여기서 확인합니다.
            </p>
          )}
        </aside>
      </div>

      {/* ③ 하단 띠 — 2D 무대(왼쪽) + 이 마디 한눈에(오른쪽), 시안 `.insp`와
          같은 자리(타임라인 아래, 고정 높이, t537 레이아웃 교정). */}
      <div className="beat-grid-insp">
        <div className="beat-grid-stage-pane">
          <h5>무대 (2D)</h5>
          {stageBounds ? (
            <svg viewBox={`0 0 ${STAGE_VIEW_W} ${STAGE_VIEW_H}`} className="beat-grid-stage">
              {fixtures.map((fixture) => {
                const { cx, cy } = projectFixture(fixture, stageBounds);
                return (
                  <circle
                    key={fixture.fid}
                    cx={cx}
                    cy={cy}
                    r={3}
                    fill={fixtureDisplayColor(fixture, grid.tracks)}
                    opacity={fixtureDisplayOpacity(fixture, grid.tracks, viewBar)}
                  >
                    <title>{`${fixture.name} (fid ${fixture.fid})`}</title>
                  </circle>
                );
              })}
            </svg>
          ) : (
            <p className="beat-grid-empty">무대 좌표 미제공 — 콘솔 패치 읽기 경로가 아직 안 배선됨(M2).</p>
          )}
          <p className="beat-grid-stage-note">
            위 = 무대 뒤 · 색 = 소속 확인된 그룹만, 나머지 회색 · 밝기 = {viewBar}마디 그 칸이 켜져 있는지
            (수치 디머는 지어내지 않음, M3 전까지는 켜짐/꺼짐 두 단계)
          </p>
        </div>

        <div className="beat-grid-glance-pane">
          <h5>이 마디 한눈에 — {viewBar}마디</h5>
          {/* t537 ② — 이 행에 걸린 SCENE 메모(§4 역할·효과 혼성 값, 트랙에
              못 옮긴 자리)를 표 위에 그대로 보여준다 — 추측해 채우지 않고
              「미정」으로 남긴 이유를 그 자리에서 읽을 수 있게 한다. */}
          {viewBarSceneMemo && (
            <p className="beat-grid-scene-memo-note">
              ⚠ {viewBarSceneMemo.text}
              <span className="beat-grid-scene-memo-source"> ({viewBarSceneMemo.sourceRef})</span>
            </p>
          )}
          <table className="beat-grid-glance-table">
            <tbody>
              {grid.tracks.map((track) => {
                const cue = cueForBar(track, viewBar);
                return (
                  <tr key={track.group_name}>
                    <td>{track.group_name}</td>
                    <td>{cue ? cue.label : "—"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* 하단 명령 입력 — mockup "구조" 5 + 조작 방법(ldbeat-runbook-ui-
          proposal-20261008.md "22~25마디 MOVER-D 효과를 Sweep 2박으로" →
          바로 적용 · AI 제안). 카드 t551 후속(근본 원인 정정) — "효과"
          항목과 위치/색의 이름 값은 이제 서버가 콘솔 프리셋 카탈로그로
          해석한다(console_slots/preset_names 재사용) — 번호 꼴 값은
          여전히 카탈로그 조회 없이 그대로 받는다. 플레이스홀더는 mockup
          원문 그대로다. */}
      <div className="beat-grid-cmd">
        <input
          className="beat-grid-cmd-input"
          value={commandText}
          onChange={(event) => setCommandText(event.target.value)}
          placeholder="예: 22~25마디 MOVER-D 효과를 Sweep 2박으로"
        />
        <button
          type="button"
          disabled={!onSentenceEditRequest || !commandText.trim()}
          title={onSentenceEditRequest ? "REQ-LDBEAT-007 문장 경로 — 밝기/위치/색/효과" : "M3에서 배선"}
          onClick={() => onSentenceEditRequest?.(commandText)}
        >
          바로 적용(문장)
        </button>
        <button
          type="button"
          disabled={!onSuggestionRequest || !selected || !selectedTrack}
          title={
            !onSuggestionRequest
              ? "M3에서 배선"
              : !selected || !selectedTrack
                ? "먼저 타임라인에서 칸을 선택하세요"
                : "실제 AI 백엔드는 이 카드 범위 밖 — 제안 소스가 비어 있으면 " +
                  "'제안 없음'이 그대로 뜹니다(지어낸 제안 0건)"
          }
          onClick={() => {
            if (selected && selectedTrack) onSuggestionRequest?.(selected.bar, selectedTrack.group_name);
          }}
        >
          AI 제안
        </button>
        {/* mockup "구조" 1·6 `#bLib` — 프리셋 서랍(카드 t551 후속, 지시 1항). */}
        <button
          type="button"
          disabled={!onDrawerRequest}
          title={onDrawerRequest ? "풀별(디머 1·위치 2·색 4) 목록 — 실제 콘솔 판독" : "M3에서 배선"}
          onClick={() => {
            const next = !drawerOpen;
            setDrawerOpen(next);
            if (next) onDrawerRequest?.();
          }}
        >
          📁 프리셋
        </button>
      </div>

      {/* 프리셋 서랍 — mockup `drawDrawer()` 그대로(지시 1항):
          "풀별(디머 1 · 위치 2 · 색 4) 목록, 쓰는 큐 수, 누르면 쓰는
          막대가 노랗게 · 콘솔 이름(영문) 표시". 데모 ``P`` 객체가 아니라
          서버의 실제 콘솔 판독(`beat_grid_preset_drawer`)에서 온다 — 못
          읽은 풀은 빈 목록(지어내지 않는다). */}
      {drawerOpen && (
        <div className="drawer open" role="complementary" aria-label="프리셋 서랍">
          <h4>
            프리셋
            <span
              style={{ float: "right", cursor: "pointer" }}
              onClick={() => setDrawerOpen(false)}
              aria-label="닫기"
            >
              ✕
            </span>
          </h4>
          <div className="fx">누르면 쓰는 막대가 노랗게 · 콘솔 이름(영문) 표시</div>
          {drawerSections === null ? (
            <p className="beat-grid-drawer-loading">불러오는 중…</p>
          ) : (
            drawerSections.map((section) => (
              <div key={section.pool_name} className="beat-grid-drawer-section">
                <h6>
                  {section.title}
                  {presetPoolBandBadge(section) && (
                    <span className="u beat-grid-drawer-band-badge">
                      {" "}
                      {presetPoolBandBadge(section)}
                    </span>
                  )}
                </h6>
                {section.unread && <p className="beat-grid-drawer-unread">이 풀을 콘솔에서 읽지 못했습니다.</p>}
                {section.entries.map((entry) => (
                  <div
                    key={entry.preset_no}
                    className={`pr${highlightedPresetNo === entry.preset_no ? " on" : ""}`}
                    onClick={() =>
                      setHighlightedPresetNo((current) =>
                        current === entry.preset_no ? null : entry.preset_no,
                      )
                    }
                    title={
                      entry.used_by.length
                        ? `쓰는 곳: 큐 ${entry.usage_count}개 — ` +
                          entry.used_by.map((u) => `${u.group_name ?? "?"} ${u.bar ?? "?"}마디`).join(", ")
                        : "쓰는 곳: 큐 0개"
                    }
                  >
                    <span>
                      <b>{entry.preset_no}</b> {entry.name}
                    </span>
                    <span className="c">큐 {entry.usage_count}</span>
                  </div>
                ))}
              </div>
            ))
          )}
        </div>
      )}

      <div className="beat-grid-probe-pane" aria-label="M1 프로브 9항목 상태">
        <h5>M1 콘솔 확인 프로브</h5>
        <ul className="beat-grid-probe-list">
          {probes.map((probe) => (
            <li key={probe.id} className={`beat-grid-probe-${probeStatusClass(probe.status)}`}>
              {probe.id}. {probe.label} — {probe.status}
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
