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
import { Fragment, useEffect, useMemo, useRef, useState } from "react";

import { PresetPlanButton, PresetPlanPanel } from "./beatgrid/PresetPlanPanel";
import { PRESET_PLAN_SUMMARY, parsePresetPlan } from "./beatgrid/presetPlan";
import { BeatGridTopBar } from "./BeatGridTopBar";
import { SongOverview } from "./SongOverview";
import {
  buildSongOverview,
  overviewVisibleWindow,
  pxPerBarForZoom,
  type OverviewZoom,
  type SongOverviewSectionInput,
} from "./songOverviewModel";

import type {
  BeatGridAppMovement,
  BeatGridBrightness,
  BeatGridCue,
  BeatGridDrawerEntry,
  BeatGridDrawerSection,
  BeatGridDraft,
  BeatGridEmptyPresetCell,
  BeatGridEvidence,
  BeatGridFxRecipe,
  BeatGridPendingSuggestion,
  BeatGridSceneMemo,
  BeatGridStageGroup,
  BeatGridTrack,
  BeatGridUnverifiedCell,
  BeatGridView,
  BeatGridSendStatus,
} from "../protocol";
// 카드 t561(M9 step 3·4·5) — 편집 칸·전환 화면·장면 전환·2D 무대는 새
// 부품 파일에 있다. 이 파일은 마운트만 한다(BeatGrid.tsx 를 여러 레인이
// 동시에 고치므로 새 영역을 여기 키우지 않는다).
import {
  BeatGridConsoleCommand,
  BeatGridCueFocus,
  BeatGridCueHeadMeta,
  BeatGridMovementRow,
  BeatGridSideRow,
  UNVERIFIED_SHAPE_BADGE,
  unverifiedShapeTitle,
  type BeatGridFocusField,
} from "./BeatGridCuePanelParts";
import { BeatGridStage } from "./BeatGridStage";
import { BeatGridJoint, BeatGridScenePanel, BeatGridSceneRow } from "./BeatGridTimelineParts";
import { BeatGridTransitionView } from "./BeatGridTransitionView";
import { confirmedFixtureRange, fixtureBelongsTo, trackFixtureSummary } from "./beatGridStageModel";
import {
  cueConsoleCommandLines,
  entryHasFade,
  parseBeatsPerBar,
  previousCue,
  sceneChangeBars,
  transitionConsoleCommandLines,
  transitionMib,
} from "./beatGridTransition";

// 카드 t560(SPEC-LDBEAT-001 M9 step 2·4(나)·6) — 타임라인 4종 상태·L·R
// 자식 줄·표→편집 연동·「이 마디 한눈에」 펼침/칩 툴팁/sticky. 로직은
// 전부 `beatgrid/` 하위 순수 모듈·표시 전용 컴포넌트에 있다 — 이 파일은
// 마운트·prop 전달만 한다(세 레인이 이 파일을 동시에 고치는 중이라 diff를
// 최소로 둔다).
import { GlanceCell } from "./beatgrid/GlanceCell";
import { cellBarsOf, gridAxisEnd } from "./beatgrid/gridAxis";
import {
  type FxPeriodUnit,
  NewPresetFxFields,
  type NewPresetFxFieldsProps,
  fxRecipeFromDraft,
  fxTemplatesForKind,
} from "./beatgrid/newPresetFx";
import {
  NewPresetColorFields,
  type NewPresetColorFieldsProps,
  isValidColorChannel,
} from "./beatgrid/newPresetColor";
import { GlanceRowDetailCells } from "./beatgrid/GlanceRowDetailCells";
import { LRSplitGlanceRow } from "./beatgrid/LRSplitGlanceRow";
import {
  LRSplitBanner,
  LRSplitCellRow,
  LRSplitRow,
  lrFollowSpans,
  lrParentCellsReplaced,
} from "./beatgrid/LRSplitRow";
import { cellSplitChildRows, cellSplitSegments } from "./beatgrid/cellSplit";
import {
  audioButtonLabel,
  audioButtonShortLabel,
  audioSourceId,
  formatAudioConnectFailureReason,
  resolvePlayIntentOnReady,
  shouldAutoConnectAudio,
  shouldDeferPlayPress,
  shouldMarkAudioLinkMissing,
  type AudioConnectStatus,
} from "./beatgrid/audioAutoConnect";
import {
  CueBarVisual,
  barNameText,
  cueBarVisualClass,
  cuePlannedClassName,
  cuePlannedTitleSuffix,
} from "./beatgrid/cueBarVisual";
import { cueRgbHex, presetColorHexMap } from "./beatgrid/presetColorHex";
import { folderSummarySpans } from "./beatgrid/folderSummary";
import { cueEditKey, deriveCueDisplayState, editedCueKeysFromUnsent } from "./beatgrid/cueDisplayState";
import { CONSOLE_FOLLOW_DISABLED_REASON, consoleSyncAudioStartOffsetSeconds } from "./beatgrid/consoleSyncAudio";
import {
  CONSOLE_DELAY_MISSING_MESSAGE,
  CONSOLE_NO_SONG_AUDIO_MESSAGE,
  consoleAudioPositionSeconds,
  createConsoleFollowRelay,
  type ConsoleFollowRelay,
} from "./beatgrid/consoleFollowRelay";
import { drawerPoolStatusText, shouldAutoRequestDrawer } from "./beatgrid/cuePanelDrawer";
import {
  brightnessCell,
  changedFieldsLabel,
  collapsedFolderSummary,
  colorCell,
  glanceBarLabel,
  movementCell,
  positionCell,
  transitionCell,
} from "./beatgrid/glanceCells";
import { buildGlanceRowDetail } from "./beatgrid/glanceRowDetail";
import {
  canDeclareLRSplit,
  clearLRSplit,
  declareLRSplit,
  lrChildRowsForTrack,
  lrSplitToggleControl,
  resolveLRSplitViewAfterBarChange,
  type LRChildRow,
  type LRSplitDeclarations,
  type LRSplitStage,
  type LRSplitViewedChild,
} from "./beatgrid/lrSplit";
import { applyProgressNote, failureNoteVisible } from "./beatgrid/applyProgress";
import { ConsoleRunningBanner } from "./beatgrid/ConsoleRunningBanner";
import { NO_FLOW_DONE, completedStepOf, type FlowDone } from "./beatgrid/flowChain";
import {
  audioClockSeconds,
  clampPlaybackSeconds,
  elapsedPlaybackSeconds,
  followPauseEnded,
  followScrollTarget,
  hasReachedPlaybackEnd,
  playheadPixelX,
  runPlaybackFrameUpdate,
} from "./beatgrid/playbackClock";
import { formatPresetChipTooltip } from "./beatgrid/presetChipTooltip";
import { roleFieldHints } from "./beatgrid/roleFields";
import { buildGlanceFocusTarget, glanceFocusAction, type GlanceFocusTarget } from "./beatgrid/tableFocus";

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

/** 카드 t579 — 서버 `unverified_cells`(M1 표 ⑨ + 실측 무빙 기록으로 가른 칸)를
 * `cueEditKey` → 미확인 어휘 목록으로 묶는다. 라벨 글자 맞추기(옛 상수 목록)는
 * 폐기했다 — 라벨은 사람이 쓴 설명이라 모양 필드와 다를 수 있고, 확인 여부는
 * 코드 상수가 아니라 M1 표가 정한다. 필드가 없으면 빈 지도(배지 없음). */
export function unverifiedCellIndex(
  cells: readonly BeatGridUnverifiedCell[] | null | undefined,
): Map<string, readonly string[]> {
  const index = new Map<string, readonly string[]>();
  for (const cell of cells ?? []) index.set(cueEditKey(cell.group_name, cell.bar), cell.terms);
  return index;
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

/** 카드 apply-safety(D16) — 「쓰기 잠김」은 반영 전체를 막는 뜻이 아니다. 반영은 진행하고
 * 미통과 프로브에 기대는 칸만 보내지 않는다. 배지는 그 뜻 그대로 보인다. 미통과가 없으면 `null`. */
export function writeHoldLabel(
  probes: readonly { status: ProbeStatus }[],
  heldCellCount: number | null | undefined,
): string | null {
  const failing = probes.filter((probe) => !probe.status.startsWith("통과")).length;
  if (failing === 0) return null;
  return `일부 칸 보류 (프로브 ${failing}개 미통과, 칸 ${heldCellCount ?? 0}개)`;
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
  /** 팬·틸트 능력(서버 판독) — 있으면 무빙 모양을 따른다. 없으면(`undefined`) 임시로 층 역할을 쓴다. */
  pan_tilt?: boolean;
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
  /** 카드 t565 — 콘솔 SELECTIONDATA 판독(`beat_grid_stage`)으로 확인된 소속
   * 그룹 이름 **전부**. 한 장비가 부모·자식 그룹(SIDE-ALL ⊇ SIDE-L)에 함께 들
   * 수 있어 목록이다. 판정은 `fixtureBelongsTo`(`beatGridStageModel.ts`) 한
   * 곳이 이 필드와 위 한 개짜리 필드를 함께 본다. */
  confirmedGroupNames?: readonly string[];
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
  // 카드 t565 — 여러 그룹 소속이면 트랙 순서상 첫 일치 트랙의 색.
  const index = tracks.findIndex((track) => fixtureBelongsTo(fixture, track.group_name));
  if (index < 0) return UNCONFIRMED_FIXTURE_COLOR;
  return TRACK_COLOR_PALETTE[index % TRACK_COLOR_PALETTE.length];
}

/** 소속 미확인/칸 미선언/꺼진 칸일 때 공통으로 쓰는 흐림 값. 수치 디머를
 * 지어내지 않으므로 "밝기"는 이 한 단계(흐림/보통/최대)뿐이다. */
const UNCONFIRMED_FIXTURE_OPACITY = 0.45;
const ACTIVE_FIXTURE_OPACITY = 1;

/** 시안 `꺼짐` — 이 마디에 켜진 칸이 없는 확인된 줄의 장비 색(어두운 회색). */
export const OFF_FIXTURE_COLOR = "#333";

/** [r,g,b] 각 0~100% → CSS `rgb(...)`(0~255 로 환산). */
function rgbPercentToCss(rgb: [number, number, number]): string {
  const toByte = (percent: number) => Math.min(255, Math.max(0, Math.round((percent * 255) / 100)));
  return `rgb(${toByte(rgb[0])}, ${toByte(rgb[1])}, ${toByte(rgb[2])})`;
}

/** 2D 무대 장비 색(리드 결정) — 소속이 확인된 줄이 지금 마디에서 켜져 있으면 그 칸의 색(`color_rgb`,
 * 없으면 줄 기본색), 꺼져 있으면 어두운 회색. 소속 미확인은 기존 회색. */
export function fixtureStageColor(
  fixture: BeatGridFixturePoint,
  tracks: readonly BeatGridTrack[],
  viewBar: number,
): string {
  const index = tracks.findIndex((track) => fixtureBelongsTo(fixture, track.group_name));
  if (index < 0) return UNCONFIRMED_FIXTURE_COLOR;
  return trackStageColor(tracks[index], index, viewBar);
}

/** 줄이 지금 마디에서 켜져 있는가 — 칸이 있고 `cueIsActive`. */
export function trackIsLitAt(track: BeatGridTrack, viewBar: number): boolean {
  const cue = cueForBar(track, viewBar);
  return cue !== null && cueIsActive(cue.label);
}

/** 줄이 지금 마디에서 내는 장비 색 — 켜져 있으면 칸 색(`color_rgb`, 없으면 줄 기본색), 꺼져 있으면 #333. */
export function trackStageColor(track: BeatGridTrack, trackIndex: number, viewBar: number): string {
  if (!trackIsLitAt(track, viewBar)) return OFF_FIXTURE_COLOR;
  const rgb = cueForBar(track, viewBar)?.color_rgb;
  return rgb ? rgbPercentToCss(rgb) : TRACK_COLOR_PALETTE[trackIndex % TRACK_COLOR_PALETTE.length];
}

/** REQ-LDBEAT-004(f) 확장(카드 t534, 리드 결정으로 갱신) — 확인된 장비의 불투명은 늘 최대다. 켜짐/꺼짐은
 * 불투명이 아니라 색으로 보인다(`fixtureStageColor`: 켜진 줄 = 칸 색, 꺼진 줄 = #333). 소속 미확인만 흐린다. */
export function fixtureDisplayOpacity(
  fixture: BeatGridFixturePoint,
  tracks: readonly BeatGridTrack[],
  _viewBar: number,
): number {
  const confirmed = tracks.some((t) => fixtureBelongsTo(fixture, t.group_name));
  return confirmed ? ACTIVE_FIXTURE_OPACITY : UNCONFIRMED_FIXTURE_OPACITY;
}

/** 밝기 「값 ▾」 칸의 선택지(시안 `#eM` 값 목록). */
const BRIGHTNESS_VALUE_CHOICES = [0, 25, 40, 60, 70, 100] as const;

export interface BeatGridProps {
  grid: BeatGridView | null | undefined;
  /** 빈 화면(격자 없음·트랙 없음)의 「돌아가기」 버튼. 런북 화면으로 나간다. 없으면 버튼을 그리지 않는다. */
  onExit?: () => void;
  /** 곡 타임라인이 열려 있는지. 격자가 없을 때 「타임라인이 없다」와 「타임라인은 있는데 격자가 없다」를 다른 안내로 가른다. */
  hasTimeline?: boolean;
  /** 2D 무대 좌표 — 콘솔 접촉 0인 M2는 이 값을 props로만 받는다(살아있는
   * 읽기 경로가 없으면 지어내지 않는다). 비어 있으면 무대 칸은 "무대 좌표
   * 미제공" 안내로 떨어진다. */
  fixtures?: BeatGridFixturePoint[];
  /** 카드 t565 — 무대 판독이 못 읽은 이유(`beat_grid_stage.unread`) 그대로.
   * 무대 칸 아래에 보인다 — 비어 있는 무대를 「장비 없음」으로 읽지 않게. */
  stageNotes?: readonly string[];
  /** 카드 t568(REQ-LDBEAT-019(c)) — `beat_grid_stage` 응답의 콘솔 그룹
   * 목록(그룹별 `member_fids`+`complete`, 카드 t565) 그대로. L·R 자식 줄
   * 분리 가능 판정(`lrSplit.ts`)이 이 값과 `fixtures`를 함께 쓴다 —
   * 트랙 이름과 정확히 같은 그룹을 여기서 찾아 그 멤버를 무대 x로 좌우로
   * 나눈다(부모 그룹도 자기 member_fids를 직접 들고 있어 더 이상 장비
   * 하나당 확인된 소속 이름의 정확 일치에 기대지 않는다). 없으면(`[]`)
   * 모든 트랙이 분리 불가다. */
  stageGroups?: readonly BeatGridStageGroup[];
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
  sections?: readonly SongOverviewSectionInput[];
  /** #726 — 서버 `timeline.accent_bars[]`({bar, kind}). 있으면 ★ 는 이 마디들이다. */
  accentBars?: readonly { bar: number; kind: string }[] | null;
  /** 카드 t559(M9 step 1·8) — 곡 전체 지도·상단 바가 읽는 곡 메타
   * (`timeline.bpm`·`timeline.bar_count`, 버전 = 초안 상태 라벨). 없으면
   * 지어내지 않고 "—"/표시 범위로 떨어진다. */
  bpm?: number | null;
  barCount?: number | null;
  versionLabel?: string | null;
  /** 카드 t559 — 상단 바 콘솔 버튼(이 마디 콘솔에서 보기·끄기·반영). 콘솔
   * 송신 경로가 아직 없어 생략하면 버튼이 비활성으로 남는다. */
  onPreviewBar?: (bar: number) => void;
  onPreviewOff?: () => void;
  onApply?: () => void;
  /** 승인 카드가 떠 있는가 — 진행 문구와 거절 알림 숨김에 쓴다(카드 apply-latency). */
  approvalPending?: boolean;
  /** 「승인 카드를 기다리는 중」 문구를 눌렀을 때 — 전체화면 위 승인 카드로 옮긴다. */
  onApprovalNoteClick?: () => void;
  /** 「필요한 프리셋 만들기」 — 서버가 계획표(chat_response)를 먼저 보내고 승인 카드를 띄운다. */
  onPresetPlanRequest?: () => void;
  /** 반영 준비 — 상단 바 타임코드 번호(초안에 적힌 값, 없으면 null)와 입력 콜백. */
  timecodeNumber?: number | null;
  onTimecodeSubmit?: (timecodeNumber: number) => void;
  pendingApplyCount?: number | null;
  /** 카드 t578(REQ-LDBEAT-024(a)) — 「콘솔 같이」 타임코드 재생·정지 송신과 그
   * 응답(`beat_grid_send_status`). 둘 다 넘겨야 토글이 켜진다 — 생략하면 기존처럼
   * 늘 비활성이다. */
  onConsolePlay?: () => void;
  onConsoleStop?: () => void;
  sendStatus?: BeatGridSendStatus | null;
  /** 「콘솔 같이」 의도와 콘솔 재생 시작 시각을 이 화면 밖(`App`)에서 쥐는 중계 객체. 전체화면을 닫으면 이
   * 화면이 사라지므로, 닫은 사이에 온 콘솔 재생 응답과 켜 둔 토글이 여기에 남아 다시 열 때 이어진다.
   * 생략하면 이 화면이 자기 것을 만들어 쓴다(그 경우 응답을 기록해 줄 쪽이 없다). */
  consoleFollowRelay?: ConsoleFollowRelay;
  /** `App` 이 응답을 중계 객체에 기록한 뒤 올리는 순번. 자식의 effect 가 부모의 effect 보다 먼저 돌아서,
   * 응답이 도착한 그 렌더에서는 아직 기록 전이다 — 기록 뒤 이 값이 바뀌어야 이 화면이 다시 확인한다. */
  consoleFollowSeq?: number;
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
   * 카드 t589(REQ-LDBEAT-015(h)) — 「＋ 새 프리셋 만들기」 창. `onEditRequest`
   * 와 같은 이유로 UI는 콘솔 번호를 짓지 않는다 — 어느 칸(`bar`/`target`)·
   * 어느 필드(`field`, 다섯 셀렉트 중 하나)에 영문 이름·한국어 설명을
   * 올리면, 서버가 `preset_pools.yaml` 번호대에서 빈 번호를 골라
   * `apply_beat_grid_edit`로 적용한다. 생략하면(미제공) 이 선택지를
   * 골라도 "아직 배선되지 않았습니다" 안내만 뜨고 만들기는 비활성이다
   * (기존 `newPresetNote` 동작과 바이트 동일).
   */
  onNewPresetRequest?: (request: {
    bar: number;
    target: string;
    field: NewPresetField;
    label: string;
    description: string;
    /** 카드 t599(REQ-LDBEAT-015(i-3)) — "position" 필드만 싣는다. */
    aim?: { x: number; y: number; z: number };
    /** 카드 t603 — "effect" 필드만 싣는다(효과 틀·주기 박/마디, 서버 필수). */
    fx?: BeatGridFxRecipe;
    /** 카드 t594(REQ-LDBEAT-015(i-5)) — "color" 필드만 싣는다(R·G·B 0~100%, 서버 필수). */
    rgb?: { r: number; g: number; b: number };
  }) => void;
  /** 카드 t589 — 서버의 가장 최근 답. 「만들기」 뒤 배정 결과·거절 사유를
   * 그 칸 아래에 보이는 데 쓴다(`newPresetReplyFor`). 생략하면 안 보인다. */
  lastServerReply?: BeatGridServerReply | null;
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
  /** SPEC-LDARRANGE-001 — 보류 중인 자동 배치 초안. 있으면 큐 편집 칸이 초안 카드로 바뀐다. */
  pendingDraft?: BeatGridDraft | null;
  /** 「자동 배치 제안」 — 서버에 초안을 한 번 요청한다(보류만 만든다). */
  onDraftPropose?: () => void;
  /** 초안 「적용」 — draft_id 하나를 되돌려 보내면 서버가 한 단위 전체를 적용한다. */
  onDraftApply?: (draftId: string) => void;
  /** 초안 「거절」 — draft_id 하나를 되돌려 보내면 서버가 보류를 버린다(격자·콘솔은 그대로). */
  onDraftReject?: (draftId: string) => void;
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
  /** 서버가 「다른 일 처리 중」으로 거절한(`busy`) 누적 횟수 — 서랍·프리셋 계획 요청이
   * 거절됐는지 알아채 「불러오는 중」/무반응으로 두지 않는다. */
  busyCount?: number;
  /** 카드 t560(REQ-LDBEAT-019(a)) — 이번 세션에 고친 칸의 키 집합
   * (`cueEditKey(groupName, bar)` 꼴). 이 컴포넌트는 이 Set을 만들지
   * 않는다 — 실제 편집 적용 지점(`onEditRequest` 호출부, 편집 칸 소관)이
   * 채워 넘겨야 "고친 막대는 초록"이 켜진다. 생략하면 그 상태는 늘
   * 꺼져 있다(기존과 바이트 동일, additive). */
  editedCueKeys?: ReadonlySet<string>;
  /** 카드 t560(REQ-LDBEAT-021(a), plan.md M9 step 4(나)) — 「이 마디
   * 한눈에」 표 칸·줄을 클릭했을 때 그 자리에서 값을 바꾸지 않고(서버
   * 요청 0건) 초점 식별자만 올려 보내는 얇은 콜백. 내부적으로는 이미
   * 같은 클릭이 `selected`를 설정해 오른쪽 칸을 그 항목에 초점을 두고
   * 연다 — 이 콜백은 그 사실을 부모에게도 알리는 추가 통지일 뿐이다. */
  onGlanceFocusRequest?: (target: GlanceFocusTarget) => void;
  /** 카드 t561 — 곡 박자표(`"4/4"`). 전환 화면의 박 입력을 정수 마디로
   * 바꿀 때만 쓴다 — 없으면 박 입력이 비활성이다(한 마디 박 수를 지어내지
   * 않음). */
  timeSignature?: string;
  /** 카드 t570(REQ-LDBEAT-024(c)) — 이 세션에서 이미 첨부된 곡 음원(기존
   * 업로드 경로 — `App.tsx` `uploadSongAudio`가 읽는 그 File). 런북
   * 전체화면 뷰를 열 때(이 컴포넌트가 처음 마운트될 때) 자동으로
   * 연결한다. 없으면(`null`/생략) 자동 연결하지 않고 ♪ 버튼으로 직접
   * 고르는 기존 경로만 남는다(기존과 바이트 동일). */
  attachedSongAudioFile?: File | null;
  /** 카드 t571(REQ-LDBEAT-024(c) 후속) — 서버에 저장된 이 곡의 오디오
   * 링크(`App.tsx`가 `song_audio_link_request` 응답을 `File`로 되돌린
   * 것). `attachedSongAudioFile`이 있으면 **그것이 항상 이긴다** — 이
   * 값은 세션 첨부가 없을 때만 쓰인다. */
  linkedSongAudioFile?: File | null;
  /** 카드 t571 — 서버에 이 곡의 저장된 링크가 없다고 확인됐다(세션
   * 첨부도 서버 링크도 없을 때만 "음원 없음"으로 보일 신호). */
  songAudioLinkMissing?: boolean;
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
 * 가까운 기존 관례인 "⚠ 실기 미확인"(모양 배지, `UNVERIFIED_SHAPE_BADGE`
 * 와 같은 글자)을 폭을 넓혀 재사용한다(이 카드가 그 자리를 정한 이유).
 * `confirmed`가 `true`(또는 알 수 없음)면 배지를 달지 않는다 — 번호대를
 * 사실로 내보이지 않을 뿐, 확정된 상태를 과장해 경고하지도 않는다. */
export function presetPoolBandBadge(section: BeatGridDrawerSection): string | null {
  return section.bands_confirmed ? null : "⚠ 번호대 미확인";
}

/** 카드 t577, REQ-LDBEAT-015(h-1). 서버가 칸마다 뷰 전용으로 붙인
 * `pending_preset_fields`(`attach_beat_grid_runtime_extras`)를 그대로
 * 읽어 "⚠ 승인 대기" 배지를 만든다 — 기존 "⚠ 번호대 미확인"/"⚠ 실기
 * 미확인"과 같은 접두 관례를 재사용한다. UI는 이 판정을 다시 유추하지
 * 않는다(서버 단일 진실 지점) — 그 리스트가 비어 있거나(또는 옛 격자라
 * 필드 자체가 없으면) 배지를 달지 않는다. */
export function pendingApprovalBadge(cue: BeatGridCue): string | null {
  const fields = cue.pending_preset_fields;
  if (!fields || fields.length === 0) return null;
  return `⚠ 승인 대기(${fields.join(", ")})`;
}

/** 카드 t595(REQ-LDBEAT-015(i-1) 「그 칸에 표시」) — 서버 `empty_preset_cells`를
 * `cueEditKey` → 칸으로 묶는다. 빈 번호 판정은 서버가 이미 읽은 풀로만 했고,
 * 화면은 그 목록을 그대로 쓴다(서랍 항목과 대조해 다시 추측하지 않는다). */
export function emptyPresetCellIndex(
  cells: readonly BeatGridEmptyPresetCell[] | null | undefined,
): Map<string, BeatGridEmptyPresetCell> {
  const index = new Map<string, BeatGridEmptyPresetCell>();
  for (const cell of cells ?? []) index.set(cueEditKey(cell.group_name, cell.bar), cell);
  return index;
}

/** 격자 칸 배지 — `⚠ 빈 프리셋(4.99)`. 풀을 못 읽은 번호는 `?`를 붙여 「비었는지
 * 모름」을 「빈 것 확인」과 가른다. 반영 때 만들어질 칸(`state: "create"`)은
 * `⚠ 새로 만들 프리셋(2.71)`. */
/** 카드 t598 — 「⇪ 콘솔에 반영」이 실패했을 때 그 사유(서버 `beat_grid_send_status`).
 * 반영이 아니거나 성공이면 `null`. 승인 창 사이 콘솔에서 번호가 채워져 송신을 통째로
 * 멈춘 경우처럼, 감독이 「다시 반영」해야 하는지를 격자 화면에서 바로 본다. */
export function applyFailureNote(status: BeatGridSendStatus | null | undefined): string | null {
  if (!status || status.ok || !status.reason) return null;
  if (status.last_action === "apply") return `⚠ 콘솔에 반영 안 됨 — ${status.reason}`;
  // 격자 편집 실패(자동 배치 적용이 바꾼 칸 0개 등) — 채팅에만 두면 전체화면에서 성공처럼 보인다.
  if (status.last_action === "edit") return `⚠ 격자에 적용 안 됨 — ${status.reason}`;
  return null;
}

export function emptyPresetBadge(cell: BeatGridEmptyPresetCell): string {
  const values = cell.fields.map((f) => (f.kind === "pool_unread" ? `${f.value}?` : f.value));
  const title = cell.state === "create" ? "새로 만들 프리셋" : "빈 프리셋";
  return `⚠ ${title}(${values.join(", ")})`;
}

/** 배지·편집 칸에 붙는 뒷말 — 반영에서 무슨 일이 생기는지(`state`). */
function emptyPresetConsequence(cell: BeatGridEmptyPresetCell): string {
  if (cell.state === "create") return "「⇪ 콘솔에 반영」 승인 때 콘솔에 만들어 함께 보냅니다";
  return "「⇪ 콘솔에 반영」에서 이 칸은 송신 보류됩니다";
}

export function emptyPresetTitle(cell: BeatGridEmptyPresetCell): string {
  const reasons = cell.fields.map((f) => `${f.field_label} ${f.value}: ${f.reason}`);
  return `${reasons.join(" · ")} — ${emptyPresetConsequence(cell)}`;
}

/** 편집 칸 행 이름 → 서버 필드 키. 행 이름과 키를 잇는 구조 대응일 뿐이다. */
const EMPTY_PRESET_ROW_FIELDS: Readonly<Record<string, string>> = {
  밝기: "brightness.preset_no",
  "위치 프리셋": "position_preset_no",
  "색 프리셋": "color_preset_no",
  "효과 프리셋": "effect_preset_no",
};

/** 편집 칸의 그 행이 빈 번호를 가리키면 한 줄 안내, 아니면 `null`. */
export function emptyPresetFieldNote(
  cell: BeatGridEmptyPresetCell | undefined,
  rowField: string,
): string | null {
  const key = EMPTY_PRESET_ROW_FIELDS[rowField];
  const field = cell && key ? cell.fields.find((f) => f.field === key) : undefined;
  if (!cell || !field) return null;
  return `⚠ ${field.value} — ${field.reason} · ${emptyPresetConsequence(cell)}`;
}

/** 카드 t551 계속 — 직접 고르기(①) 드롭다운의 "+ 새 프리셋" 선택지 값.
 * `ldbeat-runbook-mockup-20261008.html` `opts()`의 `"__new"` 리터럴
 * 그대로(값이 이 값이면 적용하지 않는다 — 그 모양 자체가 새 창을 여는
 * 자리라는 신호일 뿐, 번호가 아니다). */
export const NEW_PRESET_OPTION_VALUE = "__new";

/** 카드 t589 — 「＋ 새 프리셋 만들기」를 고를 수 있는 다섯 드롭다운. */
export type NewPresetField = "dimmer_preset" | "dimmer_effect" | "position" | "color" | "effect";

/** 카드 t589 — 「＋ 새 프리셋 만들기」 창의 콘솔 이름(영문) 칸 검증. 서버의
 * `_assert_ascii_preset_label`(REQ-LDBEAT-015(d))과 같은 뜻의 화면 쪽
 * 즉시 확인 — 최종 판정은 항상 서버가 한다(이 함수가 통과시켜도 서버가
 * 거절할 수 있다, 예: 허용 문자 집합이 서버가 더 좁다). 빈 문자열(또는
 * 공백만)은 통과하지 않는다. */
export function isValidConsoleLabel(label: string): boolean {
  return /^[\x20-\x7E]+$/.test(label.trim());
}

/** 카드 t599(REQ-LDBEAT-015(i-3)) — 「＋ 새 프리셋 만들기」 위치 다이얼로그의
 * 좌표 입력(x·y·z, 미터) 즉시 확인. 빈 문자열·수가 아님·무한대/NaN 은
 * 모두 거절 — 서버의 `_validate_new_preset_aim`(세션)과 같은 뜻의 화면
 * 쪽 즉시 확인이다(최종 판정은 항상 서버가 한다). */
export function isValidAimCoordinate(value: string): boolean {
  if (value.trim() === "") return false;
  const parsed = Number(value);
  return Number.isFinite(parsed);
}

/** 카드 t589 — 「만들기」를 누른 칸의 지금 값(서버가 번호를 씌웠는지 보는 열쇠).
 * 밝기 두 칸은 모드까지 묶는다 — 모드가 바뀌어도 다시 채워야 한다. */
export function newPresetFieldValue(cue: BeatGridCue | null, field: NewPresetField): string | null {
  if (!cue) return null;
  switch (field) {
    case "dimmer_preset":
    case "dimmer_effect":
      return `${cue.brightness.mode}:${cue.brightness.preset_no ?? ""}`;
    case "position":
      return cue.position_preset_no ?? null;
    case "color":
      return cue.color_preset_no ?? null;
    case "effect":
      return cue.effect_preset_no ?? null;
  }
}

/** 카드 t589 — 다섯 칸이 `seedEditDrafts`에서 쓰는 행 이름. */
const NEW_PRESET_SEED_ROW: Record<NewPresetField, "밝기" | "위치 프리셋" | "색 프리셋" | "효과 프리셋"> = {
  dimmer_preset: "밝기",
  dimmer_effect: "밝기",
  position: "위치 프리셋",
  color: "색 프리셋",
  effect: "효과 프리셋",
};

/** 카드 t589 — 서버의 가장 최근 답(대화 기록의 마지막 assistant 글과 그 순번). */
export interface BeatGridServerReply {
  text: string;
  seq: number;
  /** 카드 t597 — 서버 답의 요약 줄(거절 여부를 가르는 데 쓴다). */
  summary?: string;
}

/** 카드 t597 — 일반 편집(`beat_grid_edit`)이 거절될 때 서버가 붙이는 요약.
 * `server/web/session.py` `_beat_grid_rejection`과 같은 글자여야 한다. */
export const BEAT_GRID_REJECTION_SUMMARY = "박자 격자 수정 거절";

/** 카드 t597 — 일반 편집을 보내는 여섯 칸. */
export type EditReplyField = "brightness" | "position" | "color" | "effect" | "movement" | "transition";

/** 카드 t597 — 「적용」을 누른 칸(`pending.field`)에, 누른 뒤에 온 **거절**
 * 답만 돌려준다(`newPresetReplyFor`와 같은 순번 규칙). 성공은 칸 값이 바뀌는
 * 것으로 보이므로 따로 적지 않는다. */
export function editRejectionFor(
  field: EditReplyField,
  pending: { field: EditReplyField; sinceSeq: number } | null,
  reply: BeatGridServerReply | null,
): string | null {
  if (!pending || !reply || pending.field !== field) return null;
  if (reply.summary !== BEAT_GRID_REJECTION_SUMMARY) return null;
  return reply.seq > pending.sinceSeq ? reply.text : null;
}

/** 카드 t589 — 「만들기」를 누른 칸(`pending.field`)에, 누른 뒤(`seq >
 * sinceSeq`)에 온 서버 답만 돌려준다. 배정 결과(「승인 대기」)와 거절 사유가
 * 전체화면에서도 보이게 하려는 것 — 글자가 같아도 순번으로 앞뒤를 가른다. */
export function newPresetReplyFor(
  field: NewPresetField,
  pending: { field: NewPresetField; sinceSeq: number } | null,
  reply: BeatGridServerReply | null,
): string | null {
  if (!pending || !reply || pending.field !== field) return null;
  return reply.seq > pending.sinceSeq ? reply.text : null;
}

/** 카드 t589 — 「＋ 새 프리셋 만들기」 창의 순수 표시 부품(이 프로젝트는
 * jsdom 이 없다 — `BeatGridCuePanelParts.tsx`와 같은 이유로, 내부 상태를
 * props 로 끌어내 `renderToStaticMarkup`만으로 검증 가능하게 한다).
 * `enabled`가 거짓이면(= `onNewPresetRequest` 미제공) 기존 "아직 배선
 * 안 됨" 안내만 보여준다(바이트 동일, M4/별도 카드 참조는 그대로). */
export interface NewPresetDialogProps {
  enabled: boolean;
  label: string;
  description: string;
  onLabelChange: (value: string) => void;
  onDescriptionChange: (value: string) => void;
  onCreate: () => void;
  onCancel: () => void;
  /**
   * 카드 t599(REQ-LDBEAT-015(i-3)) — "위치" 필드만 목표 좌표(x·y·z,
   * 미터) 세 입력을 추가로 받는다. 라벨은 `server/spatial/pointing.py`
   * 모듈 설명(실측)이 정한 그 틀 그대로다 — Pan0/Tilt0 은 무대 -Z(바로
   * 아래)를 보고, +Z 가 위, +Tilt 가 무대 +Y(뒤)로 기울인다. 다른 네
   * 필드는 이 props를 넘기지 않는다(생략 — `showAim` 기본값 거짓).
   */
  showAim?: boolean;
  x?: string;
  y?: string;
  z?: string;
  onXChange?: (value: string) => void;
  onYChange?: (value: string) => void;
  onZChange?: (value: string) => void;
  /** 카드 t603 — "효과" 필드만 효과 틀·주기 칸을 넘긴다(생략하면 그 칸이 없다).
   * 넘기면 레시피가 다 차야 「만들기」가 켜진다. */
  fx?: NewPresetFxFieldsProps;
  /** 카드 t594 — "색" 필드만 R·G·B(0~100%) 칸을 넘긴다(생략하면 그 칸이 없다).
   * 넘기면 셋이 다 차야 「만들기」가 켜진다. */
  color?: NewPresetColorFieldsProps;
}

export function NewPresetDialog({
  enabled,
  label,
  description,
  onLabelChange,
  onDescriptionChange,
  onCreate,
  onCancel,
  showAim = false,
  x = "",
  y = "",
  z = "",
  onXChange,
  onYChange,
  onZChange,
  fx,
  color,
}: NewPresetDialogProps) {
  if (!enabled) {
    return (
      <p className="beat-grid-cue-field-note">
        ＋ 새 프리셋 만들기 — 이름·값을 정하는 창은 아직 배선되지 않았습니다(M4/별도 카드).
      </p>
    );
  }
  const labelValid = isValidConsoleLabel(label);
  const descriptionValid = description.trim().length > 0;
  const aimValid = !showAim || (isValidAimCoordinate(x) && isValidAimCoordinate(y) && isValidAimCoordinate(z));
  const fxValid =
    !fx ||
    (fxTemplatesForKind(fx.templates, fx.kind).some((t) => t.fx_id === fx.fxId) &&
      fxRecipeFromDraft({ fxId: fx.fxId, period: fx.period, unit: fx.unit }) !== null);
  const colorValid =
    !color ||
    (isValidColorChannel(color.r) && isValidColorChannel(color.g) && isValidColorChannel(color.b));
  const canCreate = labelValid && descriptionValid && aimValid && fxValid && colorValid;
  return (
    <span className="beat-grid-new-preset-dialog" data-testid="beat-grid-new-preset-dialog">
      <label className="beat-grid-new-preset-field">
        콘솔 이름(영문·숫자)
        <input
          type="text"
          placeholder="LA Wave"
          value={label}
          aria-label="콘솔 이름(영문·숫자)"
          onChange={(event) => onLabelChange(event.target.value)}
        />
      </label>
      <label className="beat-grid-new-preset-field">
        설명(한국어)
        <input
          type="text"
          value={description}
          aria-label="설명(한국어)"
          onChange={(event) => onDescriptionChange(event.target.value)}
        />
      </label>
      {label && !labelValid && (
        <p className="beat-grid-cue-field-note u">
          콘솔 이름은 영문·숫자만 허용됩니다 — 한글/비-ASCII 문자는 받지 않습니다.
        </p>
      )}
      {showAim && (
        <>
          <label className="beat-grid-new-preset-field">
            X (m)
            <input
              type="number"
              step="0.1"
              value={x}
              aria-label="X (m)"
              onChange={(event) => onXChange?.(event.target.value)}
            />
          </label>
          <label className="beat-grid-new-preset-field">
            Y (m, + = 무대 뒤)
            <input
              type="number"
              step="0.1"
              value={y}
              aria-label="Y (m, + = 무대 뒤)"
              onChange={(event) => onYChange?.(event.target.value)}
            />
          </label>
          <label className="beat-grid-new-preset-field">
            Z (m, + = 위)
            <input
              type="number"
              step="0.1"
              value={z}
              aria-label="Z (m, + = 위)"
              onChange={(event) => onZChange?.(event.target.value)}
            />
          </label>
        </>
      )}
      {fx && <NewPresetFxFields {...fx} />}
      {color && <NewPresetColorFields {...color} />}
      <button type="button" disabled={!canCreate} onClick={onCreate}>
        만들기
      </button>
      <button type="button" onClick={onCancel}>
        취소
      </button>
    </span>
  );
}

/** 카드 t551 계속 — 직접 고르기 드롭다운 한 옵션의 표시 문구. mockup
 * `opts()`의 `${i} ${P[i].nm}`과 같은 모양("번호 이름"). */
export function formatDrawerEntryOptionLabel(
  entry: BeatGridDrawerEntry,
  options: { markEffect?: boolean } = {},
): string {
  // 카드 t557 — 위치·색 드롭다운에는 기본·효과 항목이 함께 있어, 효과 번호대
  // 항목에 「· 효과」를 붙여 가른다(시안 opts() 의 「(쇼·효과)」 표기).
  const suffix = options.markEffect && entry.is_effect_band ? " · 효과" : "";
  return `${entry.preset_no} ${entry.name}${suffix}`;
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

/** 서버 `apply_beat_grid_edit`의 ``changes`` 모양 — 효과 프리셋 직접
 * 고르기. `effect_kind` 는 REQ-LDBEAT-006(i-3)의 닫힌 종류 어휘이고(번호대
 * 리터럴 아님), 카드 t557 부터 고른 항목이 나온 풀이 정한다
 * (`presetPickChanges`). 기본값 "position" 은 예전 호출과 같다. */
export function buildEffectPresetChanges(
  presetNo: string,
  kind: "position" | "color" | "dimmer" | "mixed" = "position",
): Record<string, unknown> {
  return { effect_preset_no: presetNo, effect_kind: kind };
}

/** 카드 t557 — 서랍 풀 이름 → 효과 종류·기본 저장 필드. 디머 풀은 밝기
 * 단일모드(값·디머 프리셋·디머 효과)가 따로 맡는다(REQ-LDBEAT-015(c)). */
const PICK_POOLS: Record<string, { kind: "position" | "color"; baseField: "position_preset_no" | "color_preset_no" }> = {
  Position: { kind: "position", baseField: "position_preset_no" },
  Color: { kind: "color", baseField: "color_preset_no" },
};

/** 카드 t557 — 위치·색·효과 드롭다운에서 고른 번호를 어느 필드에 담을지 정한다.
 * 그 풀의 **효과 번호대** 항목(`is_effect_band`, 서버가 `preset_pools.yaml` 로
 * 판정 — 번호대 리터럴은 여기 없다)이면 그 풀 종류의 효과(`effect_preset_no` +
 * `effect_kind`), 아니면 그 풀의 기본 필드다. 서랍에 없는 번호나 서랍을 아직
 * 못 받았으면 효과로 지어내지 않고 기본 필드로 둔다(서버 검사는 그대로 받는다). */
export function presetPickChanges(
  section: BeatGridDrawerSection | null,
  poolName: "Position" | "Color",
  presetNo: string,
): Record<string, unknown> {
  const pool = PICK_POOLS[poolName];
  const entry = section?.entries.find((candidate) => candidate.preset_no === presetNo);
  if (entry?.is_effect_band) return buildEffectPresetChanges(presetNo, pool.kind);
  return { [pool.baseField]: presetNo };
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
   * 없을 때 참 — 이때 `background`는 시안 기본색(`CUE_DEFAULT_FILL`)이다.
   * 프리셋 색을 지어내지 않는다는 원칙은 그대로다(고정 기본색만 쓴다). */
  isColorUnset: boolean;
}

/** 막대 채우기 색 — 칸에 실린 RGB(`cue.color_rgb`, 서버 #731)가 있으면 그 색이 이긴다.
 * 없으면 `color_preset_no` 의 실제 색(`colorPresetHex`)을 쓴다. 둘 다 모르면
 * **시안 기본색**(`CUE_DEFAULT_FILL`)이다 — 색을 지어내지 않는다(`isColorUnset` 참).
 * 꺼진 칸에는 부르지 않는다. */
export const CUE_DEFAULT_FILL = "#d8d8d8";

export function cueColorFill(
  cue: BeatGridCue,
  colorPresetHex?: Readonly<Record<string, string>>,
): BeatGridCueColorFill {
  const rgbHex = cueRgbHex(cue.color_rgb);
  if (rgbHex !== undefined) return { background: rgbHex, isColorUnset: false };
  if (!cue.color_preset_no) return { background: CUE_DEFAULT_FILL, isColorUnset: true };
  const hex = colorPresetHex?.[cue.color_preset_no];
  if (!hex) return { background: CUE_DEFAULT_FILL, isColorUnset: true };
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
function renderPresetOptions(
  {
    thisSong,
    showExisting,
  }: {
    thisSong: BeatGridDrawerEntry[];
    showExisting: BeatGridDrawerEntry[];
  },
  markEffect = false,
  current = "",
) {
  // 카드 t588 — 고르기가 처음부터 열려 있으므로, 값이 없는 칸이 첫 선택지(「새
  // 프리셋 만들기」)를 고른 것처럼 보이면 안 된다 → 「— 미정 —」. 지금 값이 아직
  // 읽은 목록에 없으면(서랍을 안 열었음) 그 값을 그대로 한 줄 보인다(시안은 칸을
  // 열자마자 지금 값을 보인다).
  const listed = [...thisSong, ...showExisting].some((entry) => entry.preset_no === current);
  return (
    <>
      <option value="" disabled>
        — 미정 —
      </option>
      {current !== "" && current !== NEW_PRESET_OPTION_VALUE && !listed && (
        <option value={current}>{current} (지금 값)</option>
      )}
      {thisSong.length > 0 && (
        <optgroup label="이 곡 프리셋">
          {thisSong.map((entry) => (
            <option key={entry.preset_no} value={entry.preset_no}>
              {formatDrawerEntryOptionLabel(entry, { markEffect })}
            </option>
          ))}
        </optgroup>
      )}
      {showExisting.length > 0 && (
        <optgroup label="쇼에 이미 있는 프리셋">
          {showExisting.map((entry) => (
            <option key={entry.preset_no} value={entry.preset_no}>
              {formatDrawerEntryOptionLabel(entry, { markEffect })}
            </option>
          ))}
        </optgroup>
      )}
      <option value={NEW_PRESET_OPTION_VALUE}>＋ 새 프리셋 만들기…</option>
    </>
  );
}

/** 카드 t559 — 컴포넌트 안의 확대 반영 `barToX`가 가리는 모듈 함수의 별칭. */
const barToXAt = barToX;

/** SPEC-LDARRANGE-001 — 초안이 바꿀 칸 수(트랙별 칸의 합). 0이면 「적용」을 막는다. */
function draftCellCount(draft: BeatGridDraft): number {
  return draft.tracks.reduce((total, track) => total + track.cells.length, 0);
}

/** 서랍 요청에 이 시간 안에 답이 없으면 「불러오는 중」 대신 재시도를 보인다. */
const DRAWER_REPLY_TIMEOUT_MS = 15000;

/** 서랍 읽기 상태 — 받았으면 loaded, 요청 뒤 `busy` 거절이 오면 busy, 시간 초과면 timeout. */
export type DrawerLoadState = "loaded" | "loading" | "busy" | "timeout";

export function drawerLoadState(
  sections: BeatGridDrawerSection[] | null,
  ask: { busyAt: number } | null,
  busyCount: number,
  timedOut: boolean,
): DrawerLoadState {
  if (sections !== null) return "loaded";
  if (ask !== null && busyCount > ask.busyAt) return "busy";
  return timedOut ? "timeout" : "loading";
}

/** 「프리셋 계획 만들기」 요청 뒤 계획표 없이 `busy` 거절만 왔는가 — 무반응으로 두지 않는다. */
export function presetPlanRefusedBusy(
  pending: { busyAt: number } | null,
  planShown: boolean,
  busyCount: number,
): boolean {
  return pending !== null && !planShown && busyCount > pending.busyAt;
}

/** 프리셋 계획 요청 뒤 이만큼 답이 없으면 「늦어요」로 바꾸고 다시 누를 수 있게 한다. 계획은 콘솔 풀을
 * 읽어 만들어 실측 38초 걸렸다(1차 전체 실행 E-02). */
export const PRESET_PLAN_SLOW_MS = 90_000;

/** 프리셋 계획 요청이 아직 답을 기다리는가 — 「만드는 중」 안내를 띄우고 손 재요청을 막는다.
 * 1차 전체 실행 E-02: 자동 요청은 나갔는데 화면이 조용해 서랍에서 다시 눌렀고, 그 두 번째 요청이
 * `busy` 로 거절돼 「처리되지 않았습니다」가 떴다. */
export function presetPlanWaiting(
  pending: { busyAt: number; at: number } | null,
  planShown: boolean,
  busyCount: number,
  now: number,
): "waiting" | "slow" | null {
  if (pending === null || planShown || busyCount > pending.busyAt) return null;
  return now - pending.at < PRESET_PLAN_SLOW_MS ? "waiting" : "slow";
}

export function BeatGrid({
  grid,
  onExit,
  hasTimeline = false,
  fixtures = [],
  stageNotes,
  stageGroups = [],
  probeResults,
  secondsPerBar = null,
  colorPresetHex,
  sections,
  accentBars,
  bpm,
  barCount,
  versionLabel = null,
  onPreviewBar,
  onPreviewOff,
  onApply,
  approvalPending = false,
  onApprovalNoteClick,
  onPresetPlanRequest,
  timecodeNumber,
  onTimecodeSubmit,
  pendingApplyCount,
  onConsolePlay,
  onConsoleStop,
  sendStatus = null,
  consoleFollowRelay,
  consoleFollowSeq = 0,
  onEditRequest,
  onNewPresetRequest,
  lastServerReply = null,
  onSentenceEditRequest,
  onSuggestionRequest,
  pendingSuggestion = null,
  pendingDraft = null,
  onDraftPropose,
  onDraftApply,
  onDraftReject,
  onSuggestionAccept,
  onSuggestionReject,
  drawerSections = null,
  onDrawerRequest,
  busyCount = 0,
  editedCueKeys,
  onGlanceFocusRequest,
  timeSignature,
  attachedSongAudioFile = null,
  linkedSongAudioFile = null,
  songAudioLinkMissing = false,
}: BeatGridProps) {
  // 격자 축 끝 마디 — 칸이 있는 마지막 마디나 곡의 마디 수까지 넓힌다(기본 범위에 고정하지 않는다).
  // 재생 계산이 맨 위 훅에서 쓰므로 여기서 먼저 구한다. 격자가 없으면 0(아래 빈 화면이 먼저 돌아간다).
  const axisEnd = grid ? gridAxisEnd(grid.bar_range, cellBarsOf(grid.tracks), barCount) : 0;
  const [openFolders, setOpenFolders] = useState<Set<string>>(() => new Set());
  const [allOpen, setAllOpen] = useState(true);
  const [selected, setSelected] = useState<{ trackIndex: number; bar: number } | null>(null);
  // 「필요한 프리셋 만들기」 — 누른 뒤(seq > sinceSeq)에 온 「연출 프리셋 계획」 답만 계획표로 보인다.
  const [presetPlanPending, setPresetPlanPending] = useState<
    { sinceSeq: number; busyAt: number; at: number } | null
  >(null);
  const requestPresetPlan = () => {
    setPresetPlanPending({ sinceSeq: lastServerReply?.seq ?? -1, busyAt: busyCount, at: Date.now() });
    onPresetPlanRequest?.();
  };
  const presetPlan =
    presetPlanPending !== null &&
    lastServerReply !== null &&
    lastServerReply.summary === PRESET_PLAN_SUMMARY &&
    lastServerReply.seq > presetPlanPending.sinceSeq
      ? parsePresetPlan(lastServerReply.text)
      : null;
  // 서랍 요청이 거절(busy)되거나 시간 안에 답이 없으면 「불러오는 중」을 풀고 재시도를 보인다.
  const [drawerAsk, setDrawerAsk] = useState<{ busyAt: number } | null>(null);
  const [drawerTimedOut, setDrawerTimedOut] = useState(false);
  const requestDrawer = () => {
    setDrawerAsk({ busyAt: busyCount });
    setDrawerTimedOut(false);
    onDrawerRequest?.();
  };
  const drawerState = drawerLoadState(drawerSections, drawerAsk, busyCount, drawerTimedOut);
  const drawerBusyRefused = drawerState === "busy";
  const drawerFailed = drawerState === "busy" || drawerState === "timeout";
  useEffect(() => {
    if (drawerSections !== null || drawerAsk === null) return;
    const timer = window.setTimeout(() => setDrawerTimedOut(true), DRAWER_REPLY_TIMEOUT_MS);
    return () => window.clearTimeout(timer);
  }, [drawerSections, drawerAsk]);
  // 큐 패널이 열리면 서랍을 한 번 자동으로 받는다 — 드롭다운을 바로 고를 수 있게(새 WS 타입 없음).
  // 거절·시간 초과 뒤에는 다시 묻지 않는다(판정은 `shouldAutoRequestDrawer`). 다시 받기는 서랍의 「다시 시도」.
  useEffect(() => {
    if (
      shouldAutoRequestDrawer({
        panelOpen: selected !== null,
        drawerSections,
        drawerAsk,
        canRequest: onDrawerRequest !== undefined,
      })
    ) {
      requestDrawer();
    }
  }, [selected, drawerSections, drawerAsk, onDrawerRequest]);
  const presetPlanBusyRefused = presetPlanRefusedBusy(presetPlanPending, presetPlan !== null, busyCount);
  // 「만드는 중」이 「늦어요」로 바뀌는 순간에 다시 그린다(그 사이 다른 렌더가 없어도).
  const [presetPlanClock, setPresetPlanClock] = useState(() => Date.now());
  useEffect(() => {
    if (presetPlanPending === null) return;
    const left = presetPlanPending.at + PRESET_PLAN_SLOW_MS - Date.now();
    const timer = setTimeout(() => setPresetPlanClock(Date.now()), Math.max(0, left) + 50);
    return () => clearTimeout(timer);
  }, [presetPlanPending]);
  const presetPlanWait = presetPlanWaiting(
    presetPlanPending,
    presetPlan !== null,
    busyCount,
    Math.max(presetPlanClock, Date.now()),
  );
  /** 서랍의 손 요청 — 앞 요청이 아직 만드는 중이면 다시 보내지 않는다(같은 계획표가 뜬다). */
  const requestPresetPlanByHand = () => {
    if (presetPlanWait === "waiting") return;
    requestPresetPlan();
  };
  const [transitionView, setTransitionView] = useState(false);
  // 카드 t560(REQ-LDBEAT-019(c)) — "이 구간 L·R 따로" 선언(트랙별 콘솔
  // 그룹 이름 키 하나, mockup `SPLIT` 전역과 같은 단순함). 로컬 UI 상태일
  // 뿐이다(§Gaps — lrSplit.ts 모듈 주석).
  const [lrSplits, setLrSplits] = useState<LRSplitDeclarations>(() => new Map());
  // 카드 t568(REQ-LDBEAT-019(c)) — `lrSplit.ts`가 쓰는 무대 판독 묶음.
  // `fixtures`(장비 점, fid·x 포함)와 `stageGroups`(그룹별 member_fids·
  // complete, 카드 t565 `beat_grid_stage` 응답)를 한 객체로 묶는다 —
  // 부모 그룹(SIDE-ALL 등) 소속은 그 그룹 자체의 member_fids로 판정하고,
  // 더 이상 장비 하나당 확인된 소속 이름(`confirmedGroupName`) 정확
  // 일치에 기대지 않는다(t560 §Gaps — 부모 그룹은 그 필드가 영원히 못
  // 맞았다, lrSplit.ts 모듈 주석).
  const lrStage = useMemo<LRSplitStage>(
    () => ({ fixtures, groups: stageGroups }),
    [fixtures, stageGroups],
  );
  // 카드 t568 ② — 「고침=초록」: 부모가 넘긴 키가 없으면 서버 `unsent_cells`
  // (마지막 반영 뒤 바뀐 칸, t563 공급)에서 만든다.
  const effectiveEditedCueKeys = useMemo(
    () => editedCueKeys ?? editedCueKeysFromUnsent(grid?.unsent_cells),
    [editedCueKeys, grid?.unsent_cells],
  );
  // 카드 t579(REQ-LDBEAT-010) — 「⚠ 실기 미확인」 칸(서버가 M1 표로 가른 목록).
  const unverifiedCells = useMemo(
    () => unverifiedCellIndex(grid?.unverified_cells),
    [grid?.unverified_cells],
  );
  // 카드 t595 — 「⚠ 빈 프리셋」 칸(서버가 이미 읽은 풀로 가른 목록).
  const emptyPresetCells = useMemo(
    () => emptyPresetCellIndex(grid?.empty_preset_cells),
    [grid?.empty_preset_cells],
  );
  // 카드 t560(REQ-LDBEAT-023(b)) — 「이 마디 한눈에」 줄 이름 ▸ 로 펼친
  // 트랙(콘솔 그룹 이름 키 — 이 표는 트랙당 한 줄뿐이라 마디는 필요 없다).
  const [expandedGlanceRows, setExpandedGlanceRows] = useState<Set<string>>(() => new Set());
  const [playbackSeconds, setPlaybackSeconds] = useState(0);
  const [audioName, setAudioName] = useState<string | null>(null);
  const [commandText, setCommandText] = useState("");
  // 카드 t551(M3) — 밝기 "값"(%) 인라인 편집(mockup "구조" 4). 선택이
  // 바뀌면(다른 칸을 클릭) 편집 중이던 입력을 닫는다 — 이전 칸의 입력값이
  // 새 칸에 실수로 적용되는 것을 막는다.
  // 카드 t551 계속 — 직접 고르기(①) 드롭다운(밝기/위치/색). 카드 t588 부터
  // 한 필드씩 여는 대신 전부 처음부터 열려 있다(아래).
  // 카드 t588 — 시안처럼 편집 칸의 고르기는 **처음부터 열려 있다**(전에는 값을
  // 누르면 한 칸만 열렸다, `activeEditField`). 칸마다 초안을 따로 두고, 고른 막대가
  // 바뀔 때 현재 값으로 다시 채운다(아래 `seedEditDrafts` 효과). 움직임 칸은
  // 자기 초안을 마운트 때 채우므로, 되돌리면 이 번호를 올려 다시 마운트한다.
  const [movementResetNonce, setMovementResetNonce] = useState(0);
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
  // 카드 t589 — 「＋ 새 프리셋 만들기」 창의 두 입력. 카드 t588 부터 다섯
  // 드롭다운이 동시에 열려 있어 창도 여럿 뜰 수 있다 — 입력은 칸마다 따로 둔다.
  // 카드 t589 — 「만들기」를 누른 칸과 그때의 서버 답 순번(그 뒤 답만 보인다).
  const [newPresetPending, setNewPresetPending] = useState<{
    field: NewPresetField;
    sinceSeq: number;
  } | null>(null);
  // 카드 t597 — 일반 편집 「적용」을 누른 칸과 그때의 서버 답 순번.
  const [editPending, setEditPending] = useState<{ field: EditReplyField; sinceSeq: number } | null>(null);
  const [newPresetDrafts, setNewPresetDrafts] = useState<
    Partial<
      Record<
        NewPresetField,
        // 카드 t599(REQ-LDBEAT-015(i-3)) — "position" 칸만 x·y·z 를 쓴다
        // (다른 네 필드는 항상 빈 문자열로 둔다 — `NewPresetDialog`가 그
        // 기본값으로 `showAim`을 끈다).
        // 카드 t603 — "effect" 칸만 fxId·period·unit 을 쓴다(나머지는 기본값 그대로).
        // 카드 t594(REQ-LDBEAT-015(i-5)) — "color" 칸만 r·g·b 를 쓴다
        // (다른 네 필드는 항상 빈 문자열로 둔다).
        {
          label: string;
          description: string;
          x: string;
          y: string;
          z: string;
          fxId?: string;
          period?: string;
          unit?: FxPeriodUnit;
          r?: string;
          g?: string;
          b?: string;
        }
      >
    >
  >({});
  // 카드 t551 후속(지시 1항) — 프리셋 서랍 열림/강조 상태(mockup `.drawer.open`/
  // `hlP`). 강조는 서랍을 닫아도 유지하지 않는다 — 다시 열면 깨끗한 상태.
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [highlightedPresetNo, setHighlightedPresetNo] = useState<string | null>(null);
  // 카드 t561 — 「장면 전환」 알약으로 연 마디(편집 칸이 그 순간 전체 표로
  // 바뀐다, REQ-LDBEAT-020(a)). 막대·이음매를 누르면 닫힌다.
  const [sceneBar, setSceneBar] = useState<number | null>(null);
  // 카드 t561 — 편집 칸이 초점을 둘 항목(REQ-LDBEAT-021(a)). 「이 마디
  // 한눈에」 표 클릭(카드 t560)이 이 값을 정한다 — 막대를 누르면 지운다.
  const [focusField, setFocusField] = useState<BeatGridFocusField | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  // 카드 t570(REQ-LDBEAT-024) — 재생 묶음. `playing`은 지금 재생 중인가,
  // `audioStatus`/`audioFailureReason`/`connectedAudioSourceId`는 음원
  // 연결 상태(`beatgrid/audioAutoConnect.ts`), `pendingPlayIntent`는
  // "불러오는 중에 ▶ 를 눌렀다"(AC-LDBEAT-024(b)). `lastPlaybackError`는
  // 화면 쪽 오류를 흡수한 뒤 보일 로그(REQ-LDBEAT-024(f)) — 재생 자체는
  // 이 값과 무관하게 계속된다.
  const [playing, setPlaying] = useState(false);
  const [audioStatus, setAudioStatus] = useState<AudioConnectStatus>("idle");
  const [audioFailureReason, setAudioFailureReason] = useState<string | null>(null);
  const [connectedAudioSourceId, setConnectedAudioSourceId] = useState<string | null>(null);
  const [pendingPlayIntent, setPendingPlayIntent] = useState(false);
  const [lastPlaybackError, setLastPlaybackError] = useState<string | null>(null);
  // 카드 t578(REQ-LDBEAT-024(a)) — 「콘솔 같이」. 켜져 있으면 ▶ 가 먼저 서버에
  // 타임코드 재생을 요청하고, 성공 응답이 오면 실측 지연 뒤 음원을 튼다.
  // 켬/끔·응답 대기·응답 시각은 이 화면 밖의 중계 객체(`relay`, `App` 이 쥔다)에 있다 — 전체화면을
  // 닫아 이 화면이 사라져도 의도가 남고, 닫은 사이에 온 응답도 기록된다. 이전 응답을 새 응답으로
  // 오인하지 않는 일은 `relay.pressedAgainst`(▶ 를 누를 때 화면에 있던 응답 객체)가 맡는다.
  const [ownRelay] = useState(createConsoleFollowRelay);
  const relay = consoleFollowRelay ?? ownRelay;
  const [consoleFollow, setConsoleFollowState] = useState(relay.consoleFollow);
  const setConsoleFollow = (on: boolean) => {
    relay.consoleFollow = on;
    setConsoleFollowState(on);
  };
  const [consoleFollowError, setConsoleFollowError] = useState<string | null>(null);
  // 「⇪ 콘솔에 반영」 진행 표시(카드 apply-latency): 누른 시각, 승인 카드가 뜬 시각, 그리고
  // 누르기 전이나 카드가 뜰 때 화면에 있던 결과(이번 반영의 결과가 아니다). 시계는 진행 문구가
  // 보일 때만 돈다.
  const [applyRunStartMs, setApplyRunStartMs] = useState<number | null>(null);
  const [approvalSinceMs, setApprovalSinceMs] = useState<number | null>(null);
  const [staleSendStatus, setStaleSendStatus] = useState<BeatGridSendStatus | null>(null);
  const [applyNowMs, setApplyNowMs] = useState(() => Date.now());
  useEffect(() => {
    if (approvalPending) {
      setApprovalSinceMs((since) => since ?? Date.now());
      setStaleSendStatus(sendStatus);
    } else {
      // 결정이 났거나 새 결과가 왔다 — 진행 문구를 거두고, 이후 결과는 이번 반영의 결과로 본다.
      setApprovalSinceMs(null);
      setApplyRunStartMs(null);
    }
  }, [approvalPending, sendStatus]);
  useEffect(() => {
    if (applyRunStartMs === null && approvalSinceMs === null) return;
    const timer = window.setInterval(() => setApplyNowMs(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [applyRunStartMs, approvalSinceMs]);
  const requestApply = onApply
    ? () => {
        const now = Date.now();
        setApplyNowMs(now);
        setApplyRunStartMs(now);
        // 누르기 전에 화면에 있던 결과는 이번 반영의 결과가 아니다 — 새 결과가 올 때까지 숨긴다.
        setStaleSendStatus(sendStatus);
        onApply();
      }
    : undefined;
  const applyProgressText = applyProgressNote(
    approvalPending ? approvalSinceMs : applyRunStartMs,
    applyNowMs,
    approvalPending,
  );
  const applyFailure = failureNoteVisible(approvalPending, sendStatus, staleSendStatus)
    ? applyFailureNote(sendStatus)
    : null;
  const consoleAudioTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const consoleFollowAvailable = !!onConsolePlay && !!onConsoleStop;
  // 카드 t570(REQ-LDBEAT-024(e)) — 편집 칸이 보고 있는 L·R 자식 줄(없으면
  // 부모 그룹 줄). `resolveLRSplitViewAfterBarChange`가 마디 변화에 따라
  // 매 렌더 다시 계산한다 — 별도 clear 코드 없이 구간을 벗어나면 저절로
  // 부모로 떨어진다.
  const [lrSplitViewedSide, setLrSplitViewedSide] = useState<LRSplitViewedChild | null>(null);
  const rafRef = useRef<number | null>(null);
  const playbackAnchorRef = useRef<{ anchorSeconds: number; anchorPerfMs: number } | null>(null);
  // 재생선 따라가기 — 재생 중 사용자가 직접 스크롤하면 잠시 멈춘다(`followPauseEnded`: 조용한 시간이
  // 지나면 다시 따라감). ▶·⏮·지도 클릭은 `resumeFollow`로 곧바로 다시 따라간다.
  const followPausedRef = useRef(false);
  const lastManualScrollMsRef = useRef<number | null>(null);
  const pauseFollowForManualScroll = () => {
    followPausedRef.current = true;
    lastManualScrollMsRef.current = performance.now();
  };
  const resumeFollow = () => {
    followPausedRef.current = false;
    lastManualScrollMsRef.current = null;
  };
  // 카드 t570 — RAF 틱(아래 effect)이 매 프레임 읽는 "지금 최신 값" 묶음.
  // 그 틱은 effect 의존 배열에 없는 렌더 중 계산값(`pxPerBar`·
  // `laneView.visibleWidth`·지금 고른 칸)을 훅 순서 규칙을 어기지 않고
  // 읽으려고 ref 하나로 미러링한다(렌더 바디가 매번 `.current`를 최신화,
  // 아래 `pxPerBar` 계산 직후) — React의 흔한 "latest ref" 패턴.
  const livePlaybackContextRef = useRef<{
    pxPerBar: number;
    visibleWidth: number;
    rangeStart: number;
    selected: { trackIndex: number; bar: number } | null;
  }>({ pxPerBar: PX_PER_BAR, visibleWidth: 0, rangeStart: 0, selected: null });

  // 카드 t570(REQ-LDBEAT-024(c)) — 음원 연결(자동·수동 공통 경로). DOM
  // 쪽(objectURL·`<audio>` 이벤트)만 여기서 걸고, 상태 전이 판정은
  // `beatgrid/audioAutoConnect.ts` 순수 함수가 한다.
  const connectAudioFile = (file: File) => {
    setAudioStatus("loading");
    setAudioFailureReason(null);
    setAudioName(file.name);
    setConnectedAudioSourceId(audioSourceId(file));
    const audio = audioRef.current;
    if (!audio) return;
    audio.src = URL.createObjectURL(file);
  };

  // REQ-LDBEAT-024(a) — ▶ 재생/❚❚ 일시정지. 불러오는 중이면(AC-LDBEAT-
  // 024(b)) 지금 시작하지 않고 큐잉만 한다 — 아래 "연결 완료" effect가
  // 큐잉을 풀어 즉시 시작한다. 일시정지는 `playbackSeconds`를 그대로 둔다
  // (멈춘 자리부터 이어 재생 — AC-LDBEAT-024(d)).
  const togglePlay = () => {
    // 카드 t578 — 「콘솔 같이」 켬: ❚❚ 는 음원을 멈추고 콘솔 타임코드도 끈다. 멈춘 뒤에는 아무것도
    // 다시 시작하지 않는다 — 걸어 둔 음원 시작 타이머와 콘솔 시작 시각을 지운다.
    // ▶ 는 여기서 음원을 틀지 않는다 — 서버 응답(아래 `resumeConsoleAudio`)이 지연 뒤 튼다.
    if (consoleFollow && consoleFollowAvailable) {
      if (playing) {
        setPlaying(false);
        audioRef.current?.pause();
        if (consoleAudioTimerRef.current !== null) clearTimeout(consoleAudioTimerRef.current);
        consoleAudioTimerRef.current = null;
        relay.responseAtMs = null;
        relay.audioStarted = false;
        onConsoleStop?.();
        return;
      }
      if (relay.awaiting) return;
      // 새로 누른 ▶ 는 콘솔 타임코드를 처음부터 다시 돌린다 — 앞 실행에 걸어 둔 음원 시작 예약은 거두고
      // 이번 응답만 따른다(옛 시작 시각으로 음원이 먼저 트는 일이 없게).
      if (consoleAudioTimerRef.current !== null) clearTimeout(consoleAudioTimerRef.current);
      consoleAudioTimerRef.current = null;
      relay.responseAtMs = null;
      relay.audioStarted = false;
      setConsoleFollowError(null);
      relay.failure = null;
      relay.awaiting = true;
      relay.pressedAgainst = sendStatus;
      onConsolePlay?.();
      return;
    }
    if (playing) {
      setPlaying(false);
      audioRef.current?.pause();
      // 콘솔 같이를 끈 채 멈춰도 멈춘 뒤에는 이어 트는 것이 없어야 한다 — 남은 콘솔 시작 시각을 지운다.
      relay.responseAtMs = null;
      relay.audioStarted = false;
      return;
    }
    if (shouldDeferPlayPress(audioStatus)) {
      setPendingPlayIntent(true);
      return;
    }
    playbackAnchorRef.current = { anchorSeconds: playbackSeconds, anchorPerfMs: performance.now() };
    setPlaying(true);
    resumeFollow();
    if (audioStatus === "connected" && audioRef.current) {
      try {
        audioRef.current.currentTime = playbackSeconds;
      } catch {
        // 일부 브라우저는 메타데이터가 아직 없으면 던진다 — 무시하고
        // BPM 시계만으로 재생을 이어간다(mockup `audioGo`의 try/catch와
        // 같은 경계).
      }
      void audioRef.current.play().catch((error: unknown) => {
        const message = error instanceof Error ? error.message : String(error);
        setLastPlaybackError(`[음원 재생 실패] ${message}`);
      });
    }
  };

  // REQ-LDBEAT-024(a) — ⏮ 처음. 재생 중이면 0초로 다시 앵커를 두고 계속
  // 재생한다(mockup `bTop`의 "재생 중이면 멈췄다 다시 시작" 과 같은
  // 결과 — 끊김 없이 0초부터). 멈춰 있으면 ▶ 가 그 자리(0초)부터 잇는다.
  const rewindToStart = () => {
    setPlaybackSeconds(0);
    resumeFollow();
    if (playing) {
      playbackAnchorRef.current = { anchorSeconds: 0, anchorPerfMs: performance.now() };
      if (audioRef.current) {
        try {
          audioRef.current.currentTime = 0;
        } catch {
          // 위 togglePlay 와 같은 경계.
        }
      }
    } else if (audioRef.current) {
      try {
        audioRef.current.currentTime = 0;
      } catch {
        // 위와 같은 경계.
      }
    }
  };

  // 카드 t570(REQ-LDBEAT-024(c)) — 런북 전체화면 뷰를 열 때(이 컴포넌트가
  // 처음 그려질 때) 이미 첨부된 곡 음원을 자동으로 연결한다. 첨부된 음원이
  // 없으면 서버에 저장된 링크로 대신 연결한다(카드 t571, `App.tsx`가
  // `song_audio_link_request` 응답을 `File`로 되돌려 넘긴 값) — 세션
  // 첨부가 늘 이긴다(`??`가 그 우선순위다). 둘 다 없으면, 서버가 "이 곡엔
  // 링크도 없다"고 이미 답했다면(`songAudioLinkMissing`) "음원 없음"으로
  // 솔직하게 보인다. `shouldAutoConnectAudio`가 "같은 음원에 이미 연결됨"
  // 반복을 막는다(무한 재연결 루프 방지).
  useEffect(() => {
    if (!grid) return;
    const effectiveFile = attachedSongAudioFile ?? linkedSongAudioFile;
    const sourceId = audioSourceId(effectiveFile);
    if (!shouldAutoConnectAudio({ status: audioStatus, connectedSourceId: connectedAudioSourceId }, sourceId)) {
      if (!effectiveFile && songAudioLinkMissing && shouldMarkAudioLinkMissing(audioStatus)) {
        setAudioStatus("missing");
      }
      return;
    }
    if (effectiveFile) connectAudioFile(effectiveFile);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    grid,
    attachedSongAudioFile,
    linkedSongAudioFile,
    songAudioLinkMissing,
    audioStatus,
    connectedAudioSourceId,
  ]);

  // 카드 t570(REQ-LDBEAT-024(b)) — 큐잉된 재생(불러오는 중에 ▶ 를 눌렀던
  // 의도)이 연결 상태가 바뀔 때마다 풀리는지 확인한다. `connected`가
  // 되면 즉시 시작(대기 없이), `failed`가 되면 큐잉만 지운다.
  useEffect(() => {
    const { shouldStart, nextPending } = resolvePlayIntentOnReady(pendingPlayIntent, audioStatus);
    if (nextPending !== pendingPlayIntent) setPendingPlayIntent(nextPending);
    if (shouldStart) togglePlay();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [audioStatus]);

  // 카드 t578(REQ-LDBEAT-024(a)) — 「콘솔 같이」 음원 시작. 서버가 콘솔 재생을 받아들인 시각
  // (`relay.responseAtMs`, 응답이 올 때 `App` 이 기록한다)에서 지금 음원이 있어야 할 자리를 매번 새로
  // 계산한다 — 타이머·음원 연결·화면 재진입 어느 쪽이 불러도 같은 답이 나온다. 그래서 응답이 이 화면이
  // 닫힌 사이에 왔어도, 음원이 늦게 연결돼도 맞는 자리에서 튼다. 콘솔은 Top 으로 처음에 되감겼고 음원은
  // 실측 지연(`console_audio_offset_seconds`) 뒤에 시작해야 맞는다.
  //   - 아직 지연 안(자리 < 0): 시계를 0초에 두고 그만큼 기다렸다 0초부터 튼다.
  //   - 지났으면: 그 자리로 옮겨 한 번 튼다(이 화면이 마운트된 동안 한 번만 — `relay.audioStarted`).
  //   - 음원이 아직 연결되지 않았으면 기다린다 — 아래 연결 effect 가 다시 부른다.
  // 여기서는 새 콘솔 요청도 승인 호출도 하지 않는다(▶ 는 늘 사람이 누른다).
  // 타이머와 effect 는 렌더 때 굳은 값이 아니라 아래 ref 로 늘 최신 값을 읽는다 — 옛 렌더의 음원 상태로
  // 판단하면 이미 연결돼 있어도 재생을 건너뛴다.
  const audioStatusRef = useRef(audioStatus);
  audioStatusRef.current = audioStatus;
  const consoleDelayRef = useRef<number | null>(null);
  consoleDelayRef.current = consoleSyncAudioStartOffsetSeconds(grid?.console_audio_offset_seconds);
  const resumeRef = useRef<() => void>(() => {});
  const resumeConsoleAudio = () => {
    const responseAt = relay.responseAtMs;
    if (responseAt === null) return;
    // 격자가 아직 없으면 지연을 모를 뿐이다 — 기록을 지우지 않고 격자가 올 때를 기다린다.
    if (!grid) return;
    const delay = consoleDelayRef.current;
    if (delay === null) {
      relay.responseAtMs = null;
      setConsoleFollowError(CONSOLE_DELAY_MISSING_MESSAGE);
      return;
    }
    const position = consoleAudioPositionSeconds(responseAt, delay, Date.now());
    if (position < 0) {
      setPlaybackSeconds(0);
      if (consoleAudioTimerRef.current !== null) clearTimeout(consoleAudioTimerRef.current);
      consoleAudioTimerRef.current = setTimeout(() => {
        consoleAudioTimerRef.current = null;
        resumeRef.current();
      }, -position * 1000);
      return;
    }
    if (relay.audioStarted) return;
    const audio = audioRef.current;
    if (!audio) return;
    // 「연결된 음원이 없다」는 안내(아래)는 음원이 연결돼 틀게 되거나 이미 끝난 곡이라 접는 순간 낡은 말이다.
    const dropNoAudioNote = () =>
      setConsoleFollowError((message) => (message === CONSOLE_NO_SONG_AUDIO_MESSAGE ? null : message));
    // 이미 끝난 곡이면 틀지 않고 기록을 거둔다. 길이는 메타데이터가 와야 알 수 있다(그 전엔 NaN).
    if (Number.isFinite(audio.duration) && position >= audio.duration) {
      relay.responseAtMs = null;
      dropNoAudioNote();
      return;
    }
    if (audioStatusRef.current !== "connected") {
      // 불러오는 중이면 곧 올 음원이다. 연결할 음원이 아예 없을 때만 그렇게 말한다.
      if (!attachedSongAudioFile && !linkedSongAudioFile && audioStatusRef.current !== "loading") {
        setConsoleFollowError(CONSOLE_NO_SONG_AUDIO_MESSAGE);
      }
      return;
    }
    relay.audioStarted = true;
    dropNoAudioNote();
    try {
      audio.currentTime = position;
    } catch {
      // togglePlay 와 같은 경계(메타데이터 전이면 던진다).
    }
    playbackAnchorRef.current = { anchorSeconds: position, anchorPerfMs: performance.now() };
    setPlaybackSeconds(position);
    setPlaying(true);
    resumeFollow();
    void audio.play().catch((error: unknown) => {
      const message = error instanceof Error ? error.message : String(error);
      setLastPlaybackError(`[음원 재생 실패] ${message}`);
    });
  };
  resumeRef.current = resumeConsoleAudio;

  // 응답이 오거나(`sendStatus`) `App` 이 그 응답을 기록한 뒤(`consoleFollowSeq`) 다시 확인한다. 자식의
  // effect 가 부모의 effect 보다 먼저 돌아서, 응답이 도착한 그 렌더에서는 아직 기록 전이다 — 순번이
  // 바뀌는 다음 렌더가 기록된 응답을 본다. 서버가 거절했으면 그 이유를 보인다(음원은 틀지 않는다).
  useEffect(() => {
    if (relay.failure) setConsoleFollowError(relay.failure);
    resumeRef.current();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sendStatus, consoleFollowSeq]);

  // 음원이 연결되면(`canplay`) 기다리던 시작을 그 자리에서 이어 간다.
  useEffect(() => {
    if (audioStatus === "connected") resumeRef.current();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [audioStatus]);

  // 반영 흐름 — 서버가 단계 성공을 알리면(`beat_grid_send_status.completed`) 화면이 다음 단계를
  // 안내한다. 초안 「적용」 뒤에는 기존 「프리셋 계획 만들기」 요청을 한 번 보낸다(승인 카드는 감독이
  // 직접 누른다). 그 밖의 단계는 화면 상태만 바꾼다 — 승인 호출도, 반영·콘솔 재생 송신도 여기서
  // 하지 않는다(▶ 는 늘 사람이 누른다). `seenStatusRef` 는 마운트 전에 이미 있던 응답이 다시 그려질
  // 때 요청이 되풀이되지 않게 막는다 — 새 응답 객체가 올 때만 한 번 반응한다.
  const [flowDone, setFlowDone] = useState<FlowDone>(NO_FLOW_DONE);
  const [timecodeSuggestion, setTimecodeSuggestion] = useState<number | null>(null);
  const seenStatusRef = useRef(sendStatus);
  useEffect(() => {
    if (sendStatus === seenStatusRef.current) return;
    seenStatusRef.current = sendStatus;
    if (sendStatus === null) return;
    const step = completedStepOf(sendStatus);
    if (step === "draft_applied") {
      // 새 흐름이 시작된다 — 앞 흐름의 ✓ 와 번호 권유를 지운다.
      setFlowDone(NO_FLOW_DONE);
      setTimecodeSuggestion(null);
      if (onPresetPlanRequest) requestPresetPlan();
    } else if (step === "preset") {
      setFlowDone((done) => ({ ...done, preset: true }));
      setTimecodeSuggestion(sendStatus.timecode_suggestion ?? null);
    } else if (step === "reflect") {
      setFlowDone((done) => ({ ...done, reflect: true }));
      if (consoleFollowAvailable) setConsoleFollow(true);
    } else if (step === "console") {
      setFlowDone((done) => ({ ...done, console: true }));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sendStatus]);

  // 화면이 처음 그려질 때 — 닫혀 있던 사이에 콘솔 재생 응답이 왔다면 이어 간다(전체화면을 닫고 승인한 뒤
  // 다시 연 경우). 화면을 떠날 때는 걸려 있는 음원 시작 타이머를 지우고 이 마운트의 「시작했다」 표시를
  // 내린다. 콘솔 시작 시각(`relay.responseAtMs`)은 지우지 않는다 — 다음에 열리는 화면이 이어 받는다.
  useEffect(() => {
    resumeRef.current();
    return () => {
      if (consoleAudioTimerRef.current !== null) clearTimeout(consoleAudioTimerRef.current);
      consoleAudioTimerRef.current = null;
      relay.audioStarted = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 카드 t570(REQ-LDBEAT-024(b)(d)(f)(h)) — 재생 시계 자체. `playing`일
  // 때만 돈다. 매 프레임: 화면 쪽 갱신(갱신 "이번 마디로 바뀌었는지"
  // 판정 + 보이는 칸·자동 스크롤)을 `runPlaybackFrameUpdate`로 감싸
  // 예외가 나도 재생(오디오·시계)은 멈추지 않는다(REQ-LDBEAT-024(f)).
  useEffect(() => {
    if (!playing || typeof window === "undefined") return;
    const totalSeconds = grid ? barToSeconds(axisEnd, secondsPerBar) : null;
    let previousBar: number | null = null;
    const tick = () => {
      const anchor = playbackAnchorRef.current;
      if (!anchor) return;
      const nowMs = performance.now();
      // 음원이 실제로 도는 동안은 음원 시간이 시계다(음원과 재생선이 어긋나지 않는다). 음원이 없거나
      // 멈췄으면 성능시계로 이어 가고, 그때 앵커를 지금 위치로 옮겨 두어 위치가 튀지 않게 한다.
      const audioSeconds = audioClockSeconds(audioRef.current);
      const next = audioSeconds ?? elapsedPlaybackSeconds(anchor.anchorSeconds, anchor.anchorPerfMs, nowMs);
      if (audioSeconds !== null) playbackAnchorRef.current = { anchorSeconds: audioSeconds, anchorPerfMs: nowMs };
      setPlaybackSeconds(next);
      runPlaybackFrameUpdate(
        () => {
          if (!grid) return;
          const ctx = livePlaybackContextRef.current;
          const bar = secondsToBar(next, secondsPerBar, axisEnd);
          if (bar !== null && bar !== previousBar) {
            previousBar = bar;
            setBarCursor((prev) => ({ bar, anchor: ctx.selected ?? prev?.anchor ?? null }));
            if (ctx.selected) setSelected({ trackIndex: ctx.selected.trackIndex, bar });
          }
          // 재생선 따라가기는 매 프레임 — 마디 칸이 아니라 초에서 픽셀을 바로 구해 연속으로 흘린다.
          if (followPausedRef.current && followPauseEnded(lastManualScrollMsRef.current, nowMs)) resumeFollow();
          const el = lanesRef.current;
          const x = playheadPixelX(next, secondsPerBar, ctx.pxPerBar);
          if (el && x !== null && !followPausedRef.current) {
            const target = followScrollTarget(x, el.scrollLeft, ctx.visibleWidth);
            if (target !== null) el.scrollLeft = target;
          }
        },
        (message) => {
          // eslint-disable-next-line no-console
          console.error(`[재생 — 화면 오류, 재생은 계속] ${message}`);
          setLastPlaybackError(message);
        },
      );
      if (totalSeconds !== null && hasReachedPlaybackEnd(next, totalSeconds)) {
        setPlaying(false);
        audioRef.current?.pause();
        // 곡이 끝났다 — 다시 열어도 이어 트는 것이 없게 콘솔 시작 시각을 지운다.
        relay.responseAtMs = null;
        relay.audioStarted = false;
        return;
      }
      rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);
    return () => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    };
  }, [playing, grid, secondsPerBar]);

  const folders = useMemo(() => groupTracksByLayerFolder(grid?.tracks ?? []), [grid]);
  // t537 — M1 상태의 살아있는 소스는 `grid.probe_results`(서버가 progress.md를
  // 그 자리에서 읽어 채운 값)다. `probeResults` prop은 명시적으로 다른 값을
  // 넘기고 싶을 때만 쓰는 override다(시험·예외 상황) — 둘 다 없으면
  // `buildProbeStatusTable`이 9항목 전부 "미확인"으로 떨어진다.
  const probes = useMemo(
    () => buildProbeStatusTable(probeResults ?? grid?.probe_results),
    [probeResults, grid],
  );
  const writeHoldText = writeHoldLabel(probes, grid?.m1_held_cell_count);
  // 카드 t559(M9 step 1·8) — 곡 전체 지도 확대 단계 + 상단 바 마디 이동.
  // `barCursor`는 ◀▶·지도 클릭으로 고른 마디다 — 그 뒤 칸을 새로 누르면
  // (`selected`가 바뀌면) 저절로 무효가 되어 칸 선택이 다시 기준이 된다.
  const [overviewZoom, setOverviewZoom] = useState<OverviewZoom>("bars16");
  const [barCursor, setBarCursor] = useState<{ bar: number; anchor: typeof selected } | null>(null);
  const lanesRef = useRef<HTMLDivElement | null>(null);
  const [laneView, setLaneView] = useState({ scrollLeft: 0, visibleWidth: 0 });
  const measureLanes = () => {
    const el = lanesRef.current;
    if (!el) return;
    const corner = el.querySelector<HTMLElement>(".beat-grid-ruler-corner");
    const visibleWidth = Math.max(0, el.clientWidth - (corner?.offsetWidth ?? 0));
    setLaneView((prev) =>
      prev.scrollLeft === el.scrollLeft && prev.visibleWidth === visibleWidth
        ? prev
        : { scrollLeft: el.scrollLeft, visibleWidth },
    );
  };
  useEffect(() => {
    measureLanes();
    if (typeof window === "undefined") return;
    window.addEventListener("resize", measureLanes);
    return () => window.removeEventListener("resize", measureLanes);
  }, [grid]);

  // 카드 t588 — 한 칸(또는 전부)의 초안을 그 막대의 현재 값으로 채운다. 전에는
  // 값을 눌러 칸을 열 때 하던 일이다.
  const seedEditDrafts = (
    cue: BeatGridCue | null,
    field: "밝기" | "위치 프리셋" | "색 프리셋" | "효과 프리셋" | null = null,
  ) => {
    if (field === null || field === "밝기") {
      const mode = cue?.brightness.mode ?? "value";
      setBrightnessModeDraft(mode === "dimmer_preset" || mode === "dimmer_effect" ? mode : "value");
      const currentValue = cue?.brightness.value_percent;
      setBrightnessDraft(currentValue != null ? String(currentValue) : "");
      setBrightnessPresetDraft(mode === "dimmer_preset" ? (cue?.brightness.preset_no ?? "") : "");
      setBrightnessEffectDraft(mode === "dimmer_effect" ? (cue?.brightness.preset_no ?? "") : "");
    }
    if (field === null || field === "위치 프리셋") setPositionPresetDraft(cue?.position_preset_no ?? "");
    if (field === null || field === "색 프리셋") setColorPresetDraft(cue?.color_preset_no ?? "");
    if (field === null || field === "효과 프리셋") setEffectPresetDraft(cue?.effect_preset_no ?? "");
  };
  // 고른 막대(줄 + 그 칸의 시작 마디)가 바뀔 때만 다시 채운다 — 한 칸을 적용해
  // 격자가 새로 와도 다른 칸에 고치던 초안은 지우지 않는다.
  const seedTrack = grid && selected ? (grid.tracks[selected.trackIndex] ?? null) : null;
  const seedCue = seedTrack && selected ? cueForBar(seedTrack, selected.bar) : null;
  const seedKey = seedTrack ? `${seedTrack.group_name}:${seedCue?.bar ?? "none"}` : null;
  useEffect(() => {
    // seedCue 는 seedKey 가 바뀔 때의 값만 쓴다 — deps 에서 일부러 뺐다.
    seedEditDrafts(seedCue);
  }, [seedKey]); // eslint-disable-line react-hooks/exhaustive-deps
  // 카드 t589 — 「만들기」 뒤 서버가 그 칸에 번호를 씌우면(값이 바뀌면) 그
  // 드롭다운만 새 값으로 다시 채운다 — 창을 닫을 때는 아직 옛 값이었다.
  const pendingSeedValue = newPresetPending ? newPresetFieldValue(seedCue, newPresetPending.field) : null;
  useEffect(() => {
    if (newPresetPending) seedEditDrafts(seedCue, NEW_PRESET_SEED_ROW[newPresetPending.field]);
  }, [pendingSeedValue]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!grid) {
    // 빈 화면은 안내와 돌아가는 길을 함께 보인다 — 격자가 없을 때 갈 곳이 없으면 막다른 화면이 된다.
    return (
      <section className="beat-grid" aria-label="박자 격자">
        <div className="beat-grid-empty-guide">
          {hasTimeline ? (
            <>
              <p className="beat-grid-empty-title">이 곡에는 아직 박자 격자가 없습니다.</p>
              <p className="beat-grid-empty">곡 파일을 첨부하고 「마디 지도 분석」을 하면 격자가 만들어집니다.</p>
            </>
          ) : (
            <>
              <p className="beat-grid-empty-title">박자 격자가 아직 없습니다.</p>
              <p className="beat-grid-empty">
                박자 격자는 곡 타임라인이 있어야 생깁니다. 라이브러리에서 곡을 불러온 뒤 다시 여세요.
              </p>
            </>
          )}
          {onExit && (
            <button type="button" className="beat-grid-empty-back" onClick={onExit}>
              런북 화면으로 돌아가기
            </button>
          )}
        </div>
      </section>
    );
  }

  const maxBar = axisEnd;
  // 색 프리셋의 목표 RGB(시안 P 의 rgb, 곡 격자 preset_colors) → 화면 색.
  // 명시한 colorPresetHex 가 있으면 그것이 이긴다.
  const presetHex = colorPresetHex ?? presetColorHexMap(grid?.preset_colors);
  // 카드 t559 — 곡 전체 지도 모델(곡 데이터에서만 읽음)과 확대 단계별 마디 폭.
  // 아래 `barToX`는 모듈의 같은 이름 함수를 확대 폭으로 감싼 것이다 — 타임라인
  // 그리기 코드는 손대지 않고 가로 스케일만 바뀐다.
  const overviewModel = buildSongOverview({
    sections,
    barCount,
    secondsPerBar,
    fallbackRange: grid.bar_range,
    accentBars,
  });
  const pxPerBar = pxPerBarForZoom(overviewZoom, laneView.visibleWidth, overviewModel.totalBars, PX_PER_BAR);
  // 카드 t586 — 눈금(자)에 구간 이름을 다는 데 쓴다: 구간 시작 마디 → 이름.
  const sectionLabelAtBar = new Map(overviewModel.sections.map((section) => [section.startBar, section.label]));
  const barToX = (bar: number) => barToXAt(bar, pxPerBar);
  // 카드 t570 — RAF 틱이 읽는 "지금 최신 값" 미러(위 `livePlaybackContextRef`
  // 선언 주석 참조). 렌더마다 갱신해 틱이 항상 이번 렌더의 레이아웃·선택을
  // 본다.
  livePlaybackContextRef.current = {
    pxPerBar,
    visibleWidth: laneView.visibleWidth,
    rangeStart: grid.bar_range.start,
    selected,
  };
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
  // 카드 t570(REQ-LDBEAT-024(e)) — 지금 보고 있는 L·R 자식 줄. 선택한 뒤
  // 마디가 그 선언 구간을 벗어나면 매 렌더 다시 계산해 저절로 부모로
  // 떨어진다(별도 clear 코드 없음).
  const effectiveLRSplitSide =
    selected && selectedTrack
      ? resolveLRSplitViewAfterBarChange(lrSplitViewedSide, lrSplits, selected.bar)
      : null;
  const selectedLRSplitRange = selectedTrack ? lrSplits.get(selectedTrack.group_name) : undefined;
  const selectedIsLRSplitStartBar =
    selected !== null && selectedLRSplitRange !== undefined && selectedLRSplitRange.startBar === selected.bar;
  const viewBar = barCursor && barCursor.anchor === selected ? barCursor.bar : (selected?.bar ?? grid.bar_range.start);
  // 카드 t586 — 지금 보는 마디가 속한 구간 이름(한눈에 표 머리말).
  const viewBarSectionLabel =
    overviewModel.sections.find((section) => viewBar >= section.startBar && viewBar < section.endBar)?.label ??
    null;
  // t537 ② plan-audit iteration 3 D1 — 실제로 렌더하는 배지+원문+source_ref
  // 묶음은 `sceneMemoMarkers`가 반환하는 모양 그대로다(DOM 없이 단언 가능).
  const viewBarSceneMemo = sceneMemoMarkers(grid.scene_memos, [viewBar, viewBar])[0] ?? null;
  // 카드 t534 — 재생 위치를 마디로 환산(음원 동기가 없으면 null, 지어내지
  // 않음). 플레이헤드 선·"이 마디 한눈에" 둘 다 이 값이 있을 때만 재생
  // 위치를 반영한다 — 없으면 선택된 칸(or 시작 마디)이 기준이다.
  const playheadBar = secondsToBar(playbackSeconds, secondsPerBar, maxBar);
  // 재생선 가로 위치 — 마디 단위가 아니라 초에서 바로 구한 소수 픽셀(칸과 같은 식).
  const playheadX = playheadPixelX(playbackSeconds, secondsPerBar, pxPerBar);
  const laneContentWidth = barToX(maxBar + 1);
  // 카드 t561 — 전환·장면 전환·편집 칸 머리에 쓰는 값. 구간 경계는 곡 전체
  // 지도와 같은 `overviewModel.sections`(카드 t559)에서 온다(없으면 `null` —
  // 색 경고를 판정하지 않는다).
  const beatsPerBar = parseBeatsPerBar(timeSignature);
  const sectionStartBars =
    overviewModel.sections.length > 0 ? overviewModel.sections.map((section) => section.startBar) : null;
  const sceneBars = sceneChangeBars(grid.tracks, grid.bar_range.start);
  const selectedPrevCue = selectedTrack && selectedCue ? previousCue(selectedTrack, selectedCue.bar) : null;
  const selectedSegmentEnd =
    selectedTrack && selectedCue
      ? (trackCueSegments(selectedTrack, maxBar).find((s) => s.cue === selectedCue)?.endBar ?? maxBar + 1)
      : maxBar + 1;
  const selectedConfirmedFixtures = selectedTrack
    ? fixtures.filter((f) => fixtureBelongsTo(f, selectedTrack.group_name)).length
    : 0;
  // 카드 t597 — 일반 편집을 보내고, 그 칸에 뒤따라 올 거절 사유를 기다린다.
  const requestEdit = (
    field: EditReplyField,
    request: Parameters<NonNullable<BeatGridProps["onEditRequest"]>>[0],
  ) => {
    if (!onEditRequest) return;
    onEditRequest(request);
    setEditPending({ field, sinceSeq: lastServerReply?.seq ?? -1 });
  };
  const renderEditReply = (field: EditReplyField) => {
    const reply = editRejectionFor(field, editPending, lastServerReply);
    return reply ? (
      <p className="beat-grid-cue-field-note beat-grid-edit-reject" role="status">
        {reply}
      </p>
    ) : null;
  };
  const selectCue = (trackIndex: number, bar: number, transition: boolean) => {
    setSelected({ trackIndex, bar });
    setTransitionView(transition);
    setSceneBar(null);
    setFocusField(null);
    setNewPresetDrafts({});
    setNewPresetPending(null);
    setEditPending(null);
    // 카드 t570(REQ-LDBEAT-024(e)) — 다른 칸·막대를 고르면 부모 그룹
    // 줄로 돌아간다. L·R 자식 줄을 "보는 중"으로 두는 선택은
    // `selectLRSplitChild`가 이 함수 뒤에 다시 설정한다.
    setLrSplitViewedSide(null);
  };

  // 카드 t570(REQ-LDBEAT-024(e)) — L·R 자식 줄(`LRSplitRow`/
  // `LRSplitGlanceRow`)을 눌러 "보는 중"으로 선택. 실제 편집 데이터는
  // 여전히 부모 트랙 것뿐이다(§Gaps) — 그 구간 시작 마디의 부모 큐를
  // 연다.
  const selectLRSplitChild = (trackIndex: number, groupName: string, side: "L" | "R", startBar: number) => {
    selectCue(trackIndex, startBar, false);
    setLrSplitViewedSide({ groupName, side });
  };

  const onSelectAudio = (file: File | null) => {
    if (!file) return;
    connectAudioFile(file);
  };

  const seek = (delta: number) => {
    const totalSeconds = barToSeconds(maxBar, secondsPerBar) ?? playbackSeconds;
    const next = clampPlaybackSeconds(playbackSeconds, delta, totalSeconds);
    setPlaybackSeconds(next);
    // AC-LDBEAT-024(d) — 재생 중이면 음원·앵커를 같이 옮겨 끊김 없이
    // 이어가고, 멈춰 있으면 ▶ 가 나중에 이 자리에서 잇는다(앵커는 다시
    // 재생을 시작할 때 setPlaybackSeconds 로 이미 읽는다).
    if (playing) playbackAnchorRef.current = { anchorSeconds: next, anchorPerfMs: performance.now() };
    if (audioRef.current) audioRef.current.currentTime = next;
  };

  // 카드 t559 — ◀▶·←→·지도 클릭 공통: 그 마디를 보고, 타임라인을 그 마디가
  // 보이도록 옮긴다. 격자 칸 데이터가 있는 범위 밖으로는 가지 않는다.
  // 카드 t570(REQ-LDBEAT-024(b)(h)) — 재생 중이면 그 자리부터 이어 재생한다
  // (처음으로 되돌아가지 않는다) — `secondsPerBar`가 없으면(환산 불가)
  // 보기만 옮기고 재생 위치는 그대로 둔다(지어내지 않음).
  const jumpToBar = (bar: number) => {
    const target = Math.max(grid.bar_range.start, Math.min(maxBar, bar));
    resumeFollow();
    setBarCursor({ bar: target, anchor: selected });
    if (playing) {
      const targetSeconds = barToSeconds(target, secondsPerBar);
      if (targetSeconds !== null) {
        setPlaybackSeconds(targetSeconds);
        playbackAnchorRef.current = { anchorSeconds: targetSeconds, anchorPerfMs: performance.now() };
        if (audioRef.current) {
          try {
            audioRef.current.currentTime = targetSeconds;
          } catch {
            // togglePlay 와 같은 경계.
          }
        }
      }
    }
    const el = lanesRef.current;
    if (el && laneView.visibleWidth > 0) {
      const left = (target - grid.bar_range.start) * pxPerBar;
      if (left < el.scrollLeft || left + pxPerBar > el.scrollLeft + laneView.visibleWidth) {
        el.scrollLeft = Math.max(0, left - laneView.visibleWidth / 3);
        measureLanes();
      }
    }
  };
  // mockup `#bLib` — 아래 명령창 줄의 「📁 프리셋」 버튼과 같은 동작.
  const toggleDrawer = () => {
    const next = !drawerOpen;
    setDrawerOpen(next);
    if (next) requestDrawer();
  };

  // 「이 마디 한눈에」 접힌 폴더의 「이 마디 N줄 바뀜」 — 이 마디에서 칸이 새로 시작하는 줄 수.
  // 곡 표시 범위의 첫 마디는 비교할 앞 칸이 없어 0이다(「바뀐 것」 표시와 같은 기준).
  const changedRowsAtBar = (tracks: BeatGridTrack[]) =>
    viewBar === grid.bar_range.start
      ? 0
      : tracks.filter((track) => trackCueSegments(track, maxBar).some((segment) => segment.startBar === viewBar)).length;

  return (
    <section className="beat-grid" aria-label="박자 격자">
      {/* 2차 전체 실행 N11 — 앱은 멈췄는데 콘솔 정지가 확인되지 않았으면 크게 알린다. */}
      <ConsoleRunningBanner
        visible={relay.consoleMayRun && !playing}
        timecodeNumber={timecodeNumber ?? null}
        approvalPending={approvalPending}
        onStop={onConsoleStop}
      />
      {/* 카드 t559(M9 step 8) — 상단 바, REQ-LDBEAT-017. */}
      <BeatGridTopBar
        songTitle={grid.song_title}
        note={grid.note}
        versionLabel={versionLabel}
        bpm={bpm}
        currentBar={viewBar}
        barSectionLabel={viewBarSectionLabel}
        barRange={{ start: grid.bar_range.start, end: maxBar }}
        onBarChange={jumpToBar}
        onPreviewBar={onPreviewBar}
        onPreviewOff={onPreviewOff}
        onApply={requestApply}
        applyProgress={applyProgressText}
        onApplyProgressClick={approvalPending ? onApprovalNoteClick : undefined}
        timecodeNumber={timecodeNumber}
        onTimecodeSubmit={onTimecodeSubmit}
        pendingApplyCount={pendingApplyCount}
        onDrawerToggle={onDrawerRequest ? toggleDrawer : undefined}
        onDraftPropose={pendingDraft ? undefined : onDraftPropose}
        flow={{ done: flowDone, timecodeSuggestion }}
        playback={{
          playing,
          positionSeconds: playbackSeconds,
          onTogglePlay: togglePlay,
          onRewindToStart: rewindToStart,
          onSeek: seek,
          audioButtonLabel: audioButtonLabel(audioStatus, audioName),
          audioButtonShortLabel: audioButtonShortLabel(audioStatus, audioName),
          onSelectAudioFile: onSelectAudio,
          audioFailureReason,
          consoleFollowDisabledReason: CONSOLE_FOLLOW_DISABLED_REASON,
          consoleFollowOn: consoleFollow,
          onToggleConsoleFollow: consoleFollowAvailable
            ? () => setConsoleFollow(!relay.consoleFollow)
            : undefined,
          consoleFollowError,
        }}
      />
      {presetPlan && <PresetPlanPanel plan={presetPlan} onClose={() => setPresetPlanPending(null)} />}
      {presetPlanWait !== null && (
        <p className="beat-grid-preset-plan-wait" role="status">
          {presetPlanWait === "waiting"
            ? "프리셋 계획을 만드는 중이에요 — 콘솔 풀을 읽느라 30초 넘게 걸릴 수 있어요. 다시 누르지 않아도 계획표가 뜹니다."
            : "프리셋 계획 답이 늦어요 — ▤ 서랍의 「프리셋 계획 만들기」로 다시 요청할 수 있어요."}
        </p>
      )}
      {/* 카드 t598 — 반영 실패 사유(전체화면에서도 이 격자 화면이 그대로 보인다). */}
      {applyFailure && (
        <p className="beat-grid-apply-fail" role="status">
          {applyFailure}
        </p>
      )}

      {/* 카드 t559(M9 step 1) — 곡 전체 지도, REQ-LDBEAT-018. */}
      <SongOverview
        model={overviewModel}
        filledRange={{ start: grid.bar_range.start, end: grid.bar_range.end }}
        visibleWindow={
          laneView.visibleWidth > 0
            ? overviewVisibleWindow({
                scrollLeft: laneView.scrollLeft,
                visibleWidth: laneView.visibleWidth,
                pxPerBar,
                rangeStart: grid.bar_range.start,
                totalBars: overviewModel.totalBars,
              })
            : null
        }
        playheadBar={playheadBar}
        currentBar={viewBar}
        sceneMemos={grid.scene_memos}
        zoom={overviewZoom}
        onZoomChange={setOverviewZoom}
        onJump={jumpToBar}
      />

      <div className="beat-grid-toolbar">
        <button type="button" className="beat-grid-fold-all" onClick={toggleAll}>
          [모두 접기/펴기]
        </button>
        <span className="beat-grid-transport">
          {/* 카드 t570 — ⏪ 10초 / 10초 ⏩ 는 시안대로 상단 바 플레이 묶음 안으로 옮겼다. */}
          {/* 카드 t570(REQ-LDBEAT-024(a)) — 시계·♪ 음원·콘솔 같이는
              상단 바 가운데 플레이 묶음으로 옮겼다(위 `<BeatGridTopBar
              playback={...}>`). 이 엘리먼트는 그대로 여기 남는다 — 실제
              재생 엔진(`connectAudioFile`/`togglePlay`/RAF 틱)이 거는
              DOM 핸들이라, 화면에 보이는 자리와 분리해도 된다. */}
          <audio
            ref={audioRef}
            hidden
            onCanPlay={() => {
              setAudioStatus("connected");
              setAudioFailureReason(null);
            }}
            onError={() => {
              setAudioStatus("failed");
              setAudioFailureReason(formatAudioConnectFailureReason(audioName ?? "음원"));
            }}
          />
          {/* REQ-LDBEAT-024(f) — 화면 쪽 오류가 나도 재생은 계속되고,
              그 사실을 로그(console.error)뿐 아니라 여기에도 보인다. */}
          {lastPlaybackError && (
            <span className="beat-grid-playback-error" title={lastPlaybackError}>
              ⚠ 재생 로그: {lastPlaybackError}
            </span>
          )}
        </span>
        {writeHoldText && (
          <span
            className="beat-grid-locked"
            title="M1 프로브 9항목 중 통과하지 않은 항목에 기대는 칸만 콘솔에 보내지 않습니다. 나머지 칸은 반영됩니다"
          >
            ⚠ {writeHoldText}
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
        <div
          className="beat-grid-lanes"
          role="table"
          aria-label="콘솔 그룹 트랙 타임라인"
          ref={lanesRef}
          onScroll={measureLanes}
          onWheel={pauseFollowForManualScroll}
          onTouchMove={pauseFollowForManualScroll}
          onPointerDown={(event) => {
            // 스크롤바를 잡는 누름만 직접 스크롤로 본다 — 칸을 누르는 것은 따라가기를 멈추지 않는다.
            if (event.target === event.currentTarget) pauseFollowForManualScroll();
          }}
        >
          {/* 자(마디 눈금) — 세로 스크롤 중에도 위에 고정(시안 `.ruler`). */}
          <div className="beat-grid-ruler-row">
            <span className="beat-grid-track-label beat-grid-ruler-corner">마디</span>
            <div className="beat-grid-ruler" style={{ width: laneContentWidth }}>
              {Array.from({ length: maxBar - grid.bar_range.start + 1 }, (_, i) => grid.bar_range.start + i).map(
                (bar) => {
                  // 카드 t586 — 시안 `.rb.sec`/`.sl`: 구간이 시작하는 마디에 구간
                  // 이름과 왼쪽 경계선. 구간은 곡 지도와 같은 `overviewModel`
                  // (곡 데이터)에서만 온다 — 없으면 번호만(지어내지 않음).
                  const sectionLabel = sectionLabelAtBar.get(bar);
                  return (
                    <span
                      key={bar}
                      className={`beat-grid-ruler-tick${playheadBar === bar ? " is-playhead" : ""}${
                        viewBar === bar ? " is-view" : ""
                      }${sectionLabel ? " is-section-start" : ""}`}
                      style={{ left: barToX(bar), width: pxPerBar }}
                    >
                      {bar}
                      {sectionLabel && <em className="beat-grid-ruler-section">{sectionLabel}</em>}
                    </span>
                  );
                },
              )}
            </div>
          </div>
          <BeatGridSceneRow
            bars={sceneBars}
            pxPerBar={pxPerBar}
            activeBar={sceneBar}
            width={laneContentWidth}
            onSelect={(bar) => {
              setSceneBar(bar);
              setFocusField(null);
            }}
          />

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
                {!open && (
                  <div className="beat-grid-track beat-grid-folder-summary" role="row">
                    <span className="beat-grid-track-label" />
                    <div className="beat-grid-track-cues" style={{ width: laneContentWidth }}>
                      {folderSummarySpans(folder.tracks, maxBar + 1).map((span) => (
                        <span
                          key={span.startBar}
                          className={`beat-grid-cue beat-grid-cue-sum${span.lit > 0 ? "" : " is-off"}`}
                          style={{
                            left: barToX(span.startBar),
                            width: barToX(span.endBar) - barToX(span.startBar) - 2,
                            ...(span.lit > 0 ? { backgroundColor: CUE_DEFAULT_FILL } : {}),
                          }}
                        >
                          {span.lit}/{span.total}줄 켜짐
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {open &&
                  folder.tracks.map((track) => {
                    const trackIndex = grid.tracks.indexOf(track);
                    const segments = trackCueSegments(track, maxBar);
                    const leadGapEnd = segments[0]?.startBar ?? maxBar + 1;
                    // 배치 범위 밖(범위 끝 다음 마디부터 축 끝까지) — 시안 .clip.empty 의 빗금 영역.
                    const tailStart = grid.bar_range.end + 1;
                    // 카드 t560 후속(REQ-LDBEAT-019(c)) — "이 구간 왼쪽·오른쪽
                    // 따로"/"L·R 다시 합치기" 토글은 더 이상 이 자리(타임라인
                    // 줄 이름 칸)에서 그리지 않는다 — 아래 「이 마디 한눈에」
                    // 펼침 상세 줄로 옮겼다. 자식 줄(└ L/R) 자체는 선언된
                    // 구간 전체에 걸쳐 그대로 타임라인에 보인다.
                    // 칸 하나가 왼쪽·오른쪽을 따로 가질 때(서버 `cue.split`)는 그 칸 데이터가 이긴다 —
                    // 같은 트랙에 선언(`lrSplits`)도 있으면 선언 기반 자식 줄·띠는 그리지 않는다
                    // (칸 데이터가 사실이고 선언은 화면에서 임시로 켠 틀이다). `split` 이 없는 트랙은
                    // 아래 선언 경로가 예전 그대로다.
                    const cellSplits = cellSplitSegments(segments);
                    const cellChildRows = cellSplitChildRows(track, cellSplits);
                    const childRows: LRChildRow[] =
                      cellSplits.length > 0 ? [] : lrChildRowsForTrack(track, lrSplits, lrStage);
                    // 시안 `.clip.split` 띠 — 자식 줄이 있을 때만(선언 + 분리 가능 트랙).
                    const splitRange = childRows.length > 0 ? (lrSplits.get(track.group_name) ?? null) : null;
                    // 자식 칸 데이터가 생긴 구간에서만 부모 칸을 띠로 대신한다(없으면 부모 칸 유지 — 리드 결정).
                    const declaredVisibleSegments =
                      lrParentCellsReplaced(childRows) && splitRange
                        ? segments.filter(
                            (segment) => !(segment.startBar >= splitRange.startBar && segment.endBar <= splitRange.endBar),
                          )
                        : segments;
                    // 칸 데이터로 나뉜 칸은 부모 막대를 숨기고, 아래에서 그 구간에 띠를 얹는다.
                    const visibleSegments =
                      cellSplits.length > 0
                        ? declaredVisibleSegments.filter((segment) => !cellSplits.includes(segment))
                        : declaredVisibleSegments;
                    return (
                      <Fragment key={`${track.group_name}-${trackIndex}`}>
                      <div className="beat-grid-track" role="row">
                        <span className="beat-grid-track-label">
                          <span className="beat-grid-track-name">
                            {track.group_name}
                            {!track.group_no_confirmed && (
                              <span className="beat-grid-unconfirmed-badge" title="콘솔 그룹 번호 미확인">
                                ⚠
                              </span>
                            )}
                          </span>
                          {/* 카드 t586 — 시안 `.lhead small`: 그룹·장비 범위·대수. */}
                          {(() => {
                            // #726 — 둘째 줄은 서버가 준 `sub_info.text`(콘솔 판독)가 있으면 그것, 없으면 기존 요약.
                            const summary =
                              track.sub_info?.text || trackFixtureSummary(track.group_no, track.group_name, fixtures);
                            return summary ? <small className="beat-grid-track-meta">{summary}</small> : null;
                          })()}
                        </span>
                        <div className="beat-grid-track-cues" style={{ width: laneContentWidth }}>
                          {segments.length === 0 && (
                            <span className="beat-grid-cue-empty">이 구간에 칸 없음</span>
                          )}
                          {/* 첫 칸 앞의 구간 — 칸이 없으니 꺼진 칸과 같다. 시안의 첫 구간처럼
                              빗금 + 「꺼짐」으로 보인다(「아직 선언 안 됨」이라는 글은 지어내지 않는다). */}
                          {leadGapEnd > grid.bar_range.start && (
                            <span
                              className="beat-grid-cue beat-grid-cue-gap is-off"
                              style={{ left: barToX(grid.bar_range.start), width: barToX(leadGapEnd) - barToX(grid.bar_range.start) - 2 }}
                            >
                              꺼짐
                            </span>
                          )}
                          {tailStart <= maxBar && (
                            <span
                              className="beat-grid-cue beat-grid-cue-gap beat-grid-cue-unplaced"
                              style={{ left: barToX(tailStart), width: barToX(maxBar + 1) - barToX(tailStart) - 2 }}
                            >
                              {`${tailStart}마디~ 아직 배치 안 함`}
                            </span>
                          )}
                          {/* 곡의 첫 칸이 페이드로 들어오면 — 앞 칸이 없어 이음매가 그려지지 않던 자리(꺼짐 칸에서 들어옴).
                              앞은 어둠이라 번짐도 어둠에서 시작한다. 앞 칸 사이 이음매와 달리 MIB·경고는 판정하지 않는다. */}
                          {visibleSegments.length > 0 &&
                            visibleSegments[0] === segments[0] &&
                            entryHasFade(segments[0].cue.entry) && (
                              <BeatGridJoint
                                prev={null}
                                pxPerBar={pxPerBar}
                                beatsPerBar={beatsPerBar}
                                target={track.group_name}
                                onMoveTrigger={onEditRequest ? (request) => requestEdit("transition", request) : undefined}
                                cue={visibleSegments[0].cue}
                                nextSegmentWidth={barToX(visibleSegments[0].endBar) - barToX(visibleSegments[0].startBar) - 2}
                                prevFill={null}
                                sectionStartBars={sectionStartBars}
                                accentBars={overviewModel.accentBars}
                                secondsPerBar={secondsPerBar}
                                isOn={
                                  transitionView &&
                                  selected?.trackIndex === trackIndex &&
                                  selected.bar === visibleSegments[0].cue.bar
                                }
                                onOpen={() => selectCue(trackIndex, visibleSegments[0].cue.bar, true)}
                              />
                            )}
                          {visibleSegments.map((segment) => {
                            const isSelected = selected?.trackIndex === trackIndex && selected.bar === segment.cue.bar;
                            const active = cueIsActive(segment.cue.label);
                            // 칸 목록(`segments`) 안의 자리 — `visibleSegments` 는 숨긴 칸(칸 데이터로 나뉜 칸 등)이
                            // 있으면 부분집합이라 거기서의 순번으로 다음 칸을 고르면 어긋난다. 다음 칸이 숨겨져
                            // 있으면 이음매를 그리지 않는다. 숨긴 칸이 없으면 예전 계산과 같다.
                            const segIndex = segments.indexOf(segment);
                            const hasNext = segIndex < segments.length - 1 && visibleSegments.includes(segments[segIndex + 1]);
                            // t537 (3) — 켜진 칸의 채우기 색은 color_preset_no가 실제 색을
                            // 아는 자리면 그 색, 모르면 시안 기본색(#d8d8d8)이다(프리셋 색을
                            // 지어내지 않는다). 꺼진 칸은 색을 칠하지 않고 빗금(.is-off)으로 둔다.
                            const colorFill = active ? cueColorFill(segment.cue, presetHex) : { isColorUnset: false };
                            // 계획 색(리드 결정, 콘솔에 아직 없음) — 점선 테두리 클래스와 제목 글.
                            const plannedClass = cuePlannedClassName(segment.cue, active);
                            const plannedTitle = cuePlannedTitleSuffix(segment.cue, active);
                            // 카드 t551 후속(지시 1항) — 프리셋 서랍에서 고른 항목을
                            // "누르면 쓰는 막대가 노랗게"(mockup `drawDrawer()` 안내).
                            const isHighlighted =
                              highlightedPresetNo !== null &&
                              cueReferencesPreset(segment.cue, highlightedPresetNo);
                            // 카드 t560(REQ-LDBEAT-019(a)) — 네 상태(고침=초록·
                            // 같은프리셋=노랑·AI제안=점선·기본) 판정은 순수 함수
                            // (beatgrid/cueDisplayState.ts)가 하고, 여기서는 그 결과를
                            // 클래스로만 옮긴다. `isHighlighted`(기존 `is-preset-
                            // highlighted`)는 그대로 두고(회귀 방지), 새 두 상태만
                            // 추가 클래스로 얹는다.
                            const displayState = deriveCueDisplayState({
                              isActive: active,
                              isEdited: effectiveEditedCueKeys.has(cueEditKey(track.group_name, segment.cue.bar)),
                              hasPendingSuggestion:
                                isPendingSuggestionForTrack(pendingSuggestion, track.group_name) &&
                                pendingSuggestion?.bar === segment.cue.bar,
                              referencesHighlightedPreset: isHighlighted,
                            });
                            return (
                              <span key={segment.cue.bar} className="beat-grid-cue-slot">
                                <button
                                  type="button"
                                  className={`beat-grid-cue${isSelected ? " is-selected" : ""}${active ? "" : " is-off"}${
                                    active && colorFill.isColorUnset ? " is-color-unset" : ""
                                  }${isHighlighted ? " is-preset-highlighted" : ""}${
                                    displayState === "edited" ? " is-edited" : ""
                                  }${displayState === "ai-suggestion" ? " is-ai-suggestion" : ""}${plannedClass}${cueBarVisualClass(segment.cue)}`}
                                  style={{
                                    left: barToX(segment.startBar),
                                    width: barToX(segment.endBar) - barToX(segment.startBar) - 2,
                                    ...(colorFill.background ? { backgroundColor: colorFill.background } : {}),
                                  }}
                                  title={`${segment.startBar}~${segment.endBar - 1}마디${
                                    colorFill.isColorUnset && active ? " · 색 미정" : ""
                                  }${plannedTitle}`}
                                  onClick={() => selectCue(trackIndex, segment.cue.bar, false)}
                                >
                                  {active ? barNameText(segment.cue) : "꺼짐"}
                                  <CueBarVisual cue={segment.cue} />
                                  {(() => {
                                    const terms = unverifiedCells.get(cueEditKey(track.group_name, segment.cue.bar));
                                    return terms ? (
                                      <span className="beat-grid-shape-warn" title={unverifiedShapeTitle(terms)}>
                                        {UNVERIFIED_SHAPE_BADGE}
                                      </span>
                                    ) : null;
                                  })()}
                                  {pendingApprovalBadge(segment.cue) && (
                                    <span
                                      className="beat-grid-pending-approval-warn"
                                      title="「⇪ 콘솔에 반영」 승인 카드에서 승인해야 콘솔로 나갑니다"
                                    >
                                      {pendingApprovalBadge(segment.cue)}
                                    </span>
                                  )}
                                  {(() => {
                                    const empty = emptyPresetCells.get(cueEditKey(track.group_name, segment.cue.bar));
                                    return empty ? (
                                      <span className="beat-grid-empty-preset-warn" title={emptyPresetTitle(empty)}>
                                        {emptyPresetBadge(empty)}
                                      </span>
                                    ) : null;
                                  })()}
                                </button>
                                {hasNext && (
                                  // 카드 t561 — 이음매 표시(M·!·◢)와 페이드 번짐(REQ-LDBEAT-020(a)).
                                  <BeatGridJoint
                                    prev={segment.cue}
                                    pxPerBar={pxPerBar}
                                    beatsPerBar={beatsPerBar}
                                    target={track.group_name}
                                    onMoveTrigger={onEditRequest ? (request) => requestEdit("transition", request) : undefined}
                                    cue={segments[segIndex + 1].cue}
                                    nextSegmentWidth={
                                      barToX(segments[segIndex + 1].endBar) - barToX(segments[segIndex + 1].startBar) - 2
                                    }
                                    prevFill={active ? colorFill.background ?? null : null}
                                    sectionStartBars={sectionStartBars}
                                    accentBars={overviewModel.accentBars}
                                    secondsPerBar={secondsPerBar}
                                    isOn={
                                      transitionView &&
                                      selected?.trackIndex === trackIndex &&
                                      selected.bar === segments[segIndex + 1].cue.bar
                                    }
                                    onOpen={() => selectCue(trackIndex, segments[segIndex + 1].cue.bar, true)}
                                  />
                                )}
                              </span>
                            );
                          })}
                          {playheadBar !== null && playheadX !== null && (
                            <span
                              className="beat-grid-playhead"
                              style={{ left: playheadX, width: pxPerBar }}
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
                          {splitRange && (
                            <LRSplitBanner
                              left={barToX(splitRange.startBar)}
                              width={barToX(splitRange.endBar) - barToX(splitRange.startBar) - 2}
                            />
                          )}
                          {/* 칸 데이터로 나뉜 칸마다 그 칸의 구간에 띠 — 숨긴 부모 막대 자리를 대신한다. */}
                          {cellSplits.map((segment) => (
                            <LRSplitBanner
                              key={segment.cue.bar}
                              left={barToX(segment.startBar)}
                              width={barToX(segment.endBar) - barToX(segment.startBar) - 2}
                            />
                          ))}
                        </div>
                      </div>
                      {/* 카드 t560(REQ-LDBEAT-019(c)) — "이 구간 L·R 따로" 선언이
                          만든 자식 줄. 선언 전에는 `childRows`가 늘 빈 배열이라
                          아무것도 안 그려진다(AC-LDBEAT-019(c) "0개"). */}
                      {childRows.map((child) => (
                        <LRSplitRow
                          key={child.side}
                          child={child}
                          left={barToX(child.startBar)}
                          width={barToX(child.endBar) - barToX(child.startBar) - 2}
                          follow={{
                            label: `${track.group_name} 따름`,
                            spans: lrFollowSpans(child, { start: grid.bar_range.start, end: maxBar + 1 }, barToX),
                          }}
                          onSelect={() =>
                            selectLRSplitChild(trackIndex, track.group_name, child.side, child.startBar)
                          }
                        />
                      ))}
                      {/* 칸 데이터(`cue.split`)가 만든 자식 줄 — 표시 전용(누를 수 없고 따름 칸도 없다).
                          칸 데이터가 있으면 위 선언 기반 자식 줄(`childRows`)은 비어 있다. */}
                      {cellChildRows.map((row) => (
                        <LRSplitCellRow key={row.side} row={row} toX={barToX} />
                      ))}
                      </Fragment>
                    );
                  })}
              </div>
            );
          })}
          {folders.length === 0 && (
            <div className="beat-grid-empty-guide">
              <p className="beat-grid-empty">{grid.note ?? "표시할 트랙이 없습니다."}</p>
              {onExit && (
                <button type="button" className="beat-grid-empty-back" onClick={onExit}>
                  런북 화면으로 돌아가기
                </button>
              )}
            </div>
          )}
        </div>

        {/* 큐 편집 칸 — 시안처럼 "타임라인 바로 오른쪽에 늘 있음"(선택 전엔
            빈 안내, t537 레이아웃 교정 — `.beat-grid-mid`의 두 번째 칸).
            밝기/위치/색/들어올 때 네 필드를 보여 준다(REQ-LDBEAT-004(c)(d)).
            `onEditRequest`가 있으면 밝기(값·디머 프리셋·디머 효과)·위치·
            색·효과·움직임 칸이 늘 열린 고르기로 그 자리에서 고쳐진다(t588,
            시안 `.sidepane .ed`) — 프리셋 목록은 서랍이 읽은 카탈로그에서
            온다. */}
        <aside className="beat-grid-cue-panel" aria-label="큐 편집 칸">
          {pendingDraft ? (
            // SPEC-LDARRANGE-001 — 자동 배치 초안이 보류 중인 동안은 이 칸이 초안 카드가 된다.
            // 「적용」·「거절」 전까지 격자·콘솔은 바뀌지 않는다. 적용은 칸 라벨만 바꾸고 되돌리기 기록을 남긴다.
            <div className="beat-grid-ai-suggestion beat-grid-draft" aria-label="자동 배치 초안">
              <header>
                <span>자동 배치 초안</span>
                <span>
                  {pendingDraft.bar_range.start}~{pendingDraft.bar_range.end}마디
                </span>
              </header>
              <p>
                줄 {pendingDraft.tracks.length}개 · 칸 {draftCellCount(pendingDraft)}개. 「적용」하면 같은 칸의 라벨이
                초안 값으로 바뀌고 되돌리기 기록이 남습니다. 콘솔에는 쓰지 않습니다.
              </p>
              <ul className="beat-grid-draft-tracks">
                {pendingDraft.tracks.map((track, index) => (
                  <li key={`${track.group_name}-${index}`}>
                    {track.group_name} · {track.cells.length}칸
                  </li>
                ))}
              </ul>
              <div className="beat-grid-ai-suggestion-actions">
                <button
                  type="button"
                  className="tbtn pri"
                  disabled={draftCellCount(pendingDraft) === 0}
                  onClick={() => onDraftApply?.(pendingDraft.draft_id)}
                >
                  적용
                </button>
                <button type="button" onClick={() => onDraftReject?.(pendingDraft.draft_id)}>
                  거절
                </button>
              </div>
            </div>
          ) : pendingSuggestion ? (
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
          ) : sceneBar !== null ? (
            // 카드 t561 — 「장면 전환」 알약 → 그 순간 전체 표(REQ-LDBEAT-020(a)).
            <BeatGridScenePanel
              bar={sceneBar}
              tracks={grid.tracks}
              secondsPerBar={secondsPerBar}
              sectionStartBars={sectionStartBars}
              accentBars={overviewModel.accentBars}
              onClose={() => setSceneBar(null)}
              onSelectRow={(trackIndex) => selectCue(trackIndex, sceneBar, true)}
              beatsPerBar={beatsPerBar}
              onBulkEntry={
                onEditRequest
                  ? (edits) =>
                      edits.forEach(({ target, entry }) =>
                        onEditRequest({ bar: sceneBar, target, changes: { entry } }),
                      )
                  : undefined
              }
            />
          ) : selected && selectedTrack ? (
            <>
              <header>
                <span>
                  {selectedTrack.group_name}
                  {effectiveLRSplitSide ? ` ${effectiveLRSplitSide.side}` : ""}
                  {/* 시안 머리 「BACK · Cue 5 'Back Hold'」 — 번호와 이름은 곡 데이터에서. */}
                  {selectedCue
                    ? ` · Cue ${selectedTrack.cues.indexOf(selectedCue) + 1} '${selectedCue.label}'`
                    : ` · ${selected.bar}마디`}
                  {/* 카드 t570(REQ-LDBEAT-024(e)) — 갈라지는 시작 마디
                      표시. 선언 구간의 시작 마디를 보고 있을 때만(부모
                      줄 기준 — 자식 줄 쪽에서도 같은 시작 마디다). */}
                  {selectedIsLRSplitStartBar && (
                    <small className="beat-grid-split-start-marker"> · 여기서 갈라짐</small>
                  )}
                </span>
                <span className="beat-grid-cue-panel-actions">
                  <button
                    type="button"
                    className={`beat-grid-transition-toggle${transitionView ? " is-on" : ""}`}
                    disabled={firstCue || !selectedPrevCue}
                    title={firstCue || !selectedPrevCue ? "곡 첫 큐 — 들어오는 전환 없음" : undefined}
                    onClick={() => setTransitionView((v) => !v)}
                  >
                    전환
                  </button>
                  <button type="button" aria-label="닫기" onClick={() => setSelected(null)}>
                    ✕
                  </button>
                </span>
              </header>
              {selectedCue && (
                <BeatGridCueHeadMeta
                  track={selectedTrack}
                  cue={selectedCue}
                  endBar={selectedSegmentEnd}
                  secondsPerBar={secondsPerBar}
                  confirmedFixtureCount={selectedConfirmedFixtures}
                  confirmedFixtureRange={confirmedFixtureRange(selectedTrack.group_name, fixtures)}
                />
              )}
              {transitionView && selectedCue && selectedPrevCue ? (
                // 카드 t561 — 같은 자리에서 전환 화면으로 바뀐다(REQ-LDBEAT-020(d)).
                <>
                  <BeatGridTransitionView
                    key={`${selectedTrack.group_name}-${selectedCue.bar}`}
                    track={selectedTrack}
                    cue={selectedCue}
                    prevCue={selectedPrevCue}
                    secondsPerBar={secondsPerBar}
                    beatsPerBar={beatsPerBar}
                    sectionStartBars={sectionStartBars}
                    accentBars={overviewModel.accentBars}
                    onEditRequest={onEditRequest ? (request) => requestEdit("transition", request) : undefined}
                  />
                  {/* 카드 t597 — 전환 편집의 거절 사유. */}
                  {renderEditReply("transition")}
                </>
              ) : (
                <BeatGridCueFocus focusField={focusField} focusKey={`${selected.trackIndex}-${selected.bar}`}>
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
                      // 카드 t557 — 무빙이 아닌 줄에 색 효과처럼 다른 종류의 효과가
                      // 저장돼 있어도 보이게 한다(고치기는 아래에서 무빙만).
                      if (hints.includes("움직임") || selectedCue.effect_preset_no !== null) {
                        const effectValue = formatPresetField(selectedCue.effect_preset_no);
                        rows.push({
                          field: "효과 프리셋",
                          value: selectedCue.effect_kind ? `${effectValue} (${selectedCue.effect_kind})` : effectValue,
                        });
                      }
                      // t548 — 근거 등급(REQ-LDBEAT-006(vii))은 값이 있는 칸에서만
                      // 보인다. 경고 둘은 거절이 아니라 표시다. 앱 2단계 무빙(vi)은
                      // 카드 t561부터 아래 「움직임」 전용 행이 보인다(REQ-LDBEAT-021(b)).
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
                    // 프리셋"/"+ 새 프리셋"으로 고른다).
                    const positionSection = findDrawerSection(drawerSections, "Position");
                    const colorSection = findDrawerSection(drawerSections, "Color");
                    const dimmerSection = findDrawerSection(drawerSections, "Dimmer");
                    const closeEdit = () => {
                      setNewPresetDrafts({});
                    };
                    // 카드 t589 — 「＋ 새 프리셋 만들기」 창. 실제 표시는
                    // `NewPresetDialog`(순수 부품, renderToStaticMarkup으로
                    // 검증)에 맡기고, 여기서는 이 칸이 아는 콜백(선택된
                    // 바·트랙·그 칸의 draft)만 엮는다. `resetSelectDraft`는 그
                    // 드롭다운을 막대의 현재 값으로 되돌린다 — 만들기·취소 뒤
                    // 「＋ 새 프리셋」에 머물러 창이 남지 않게.
                    const renderNewPresetDialog = (field: NewPresetField, resetSelectDraft: () => void) => {
                      const draft =
                        newPresetDrafts[field] ?? { label: "", description: "", x: "", y: "", z: "" };
                      const setDraft = (
                        next: Partial<{
                          label: string;
                          description: string;
                          x: string;
                          y: string;
                          z: string;
                          fxId: string;
                          period: string;
                          unit: FxPeriodUnit;
                          r: string;
                          g: string;
                          b: string;
                        }>,
                      ) => setNewPresetDrafts((prev) => ({ ...prev, [field]: { ...draft, ...next } }));
                      const finish = () => {
                        resetSelectDraft();
                        setNewPresetDrafts((prev) => ({ ...prev, [field]: undefined }));
                      };
                      // 카드 t599 — "position"만 목표 좌표를 받는다.
                      const showAim = field === "position";
                      // 카드 t603 — "effect"만 효과 틀·주기를 받는다(서버 필수). 고를 수 있는
                      // 틀은 그 칸의 효과 종류에 맞는 것뿐이다(서버 `kinds`).
                      const fxDraft = {
                        fxId: draft.fxId ?? "",
                        period: draft.period ?? "",
                        unit: draft.unit ?? ("beat" as FxPeriodUnit),
                      };
                      const fxKind = selectedCue?.effect_kind ?? null;
                      const fxProps: NewPresetFxFieldsProps | undefined =
                        field === "effect"
                          ? {
                              templates: grid?.fx_templates,
                              kind: fxKind,
                              ...fxDraft,
                              onFxIdChange: (fxId) => setDraft({ fxId }),
                              onPeriodChange: (period) => setDraft({ period }),
                              onUnitChange: (unit) => setDraft({ unit }),
                            }
                          : undefined;
                      const fxRecipe =
                        fxProps &&
                        fxTemplatesForKind(fxProps.templates, fxKind).some((t) => t.fx_id === fxDraft.fxId)
                          ? fxRecipeFromDraft(fxDraft)
                          : null;
                      // 카드 t594 — "color"만 R·G·B(0~100%)를 받는다(서버 필수).
                      const colorDraft = { r: draft.r ?? "", g: draft.g ?? "", b: draft.b ?? "" };
                      const colorProps: NewPresetColorFieldsProps | undefined =
                        field === "color"
                          ? {
                              ...colorDraft,
                              onRChange: (r) => setDraft({ r }),
                              onGChange: (g) => setDraft({ g }),
                              onBChange: (b) => setDraft({ b }),
                            }
                          : undefined;
                      const colorValid =
                        colorProps !== undefined &&
                        isValidColorChannel(colorDraft.r) &&
                        isValidColorChannel(colorDraft.g) &&
                        isValidColorChannel(colorDraft.b);
                      return (
                        <NewPresetDialog
                          enabled={!!onNewPresetRequest}
                          label={draft.label}
                          description={draft.description}
                          onLabelChange={(label) => setDraft({ label })}
                          onDescriptionChange={(description) => setDraft({ description })}
                          showAim={showAim}
                          x={draft.x}
                          y={draft.y}
                          z={draft.z}
                          onXChange={(x) => setDraft({ x })}
                          onYChange={(y) => setDraft({ y })}
                          onZChange={(z) => setDraft({ z })}
                          fx={fxProps}
                          color={colorProps}
                          onCreate={() => {
                            const labelValid = isValidConsoleLabel(draft.label);
                            const descriptionValid = draft.description.trim().length > 0;
                            const aimValid =
                              !showAim ||
                              (isValidAimCoordinate(draft.x) &&
                                isValidAimCoordinate(draft.y) &&
                                isValidAimCoordinate(draft.z));
                            if (
                              !onNewPresetRequest ||
                              !labelValid ||
                              !descriptionValid ||
                              !aimValid ||
                              (fxProps !== undefined && fxRecipe === null) ||
                              (colorProps !== undefined && !colorValid) ||
                              !selected ||
                              !selectedTrack
                            ) {
                              return;
                            }
                            onNewPresetRequest({
                              bar: selected.bar,
                              target: selectedTrack.group_name,
                              field,
                              label: draft.label.trim(),
                              description: draft.description.trim(),
                              ...(showAim
                                ? {
                                    aim: {
                                      x: Number(draft.x),
                                      y: Number(draft.y),
                                      z: Number(draft.z),
                                    },
                                  }
                                : {}),
                              ...(fxRecipe ? { fx: fxRecipe } : {}),
                              ...(colorValid
                                ? {
                                    rgb: {
                                      r: Number(colorDraft.r),
                                      g: Number(colorDraft.g),
                                      b: Number(colorDraft.b),
                                    },
                                  }
                                : {}),
                            });
                            setNewPresetPending({ field, sinceSeq: lastServerReply?.seq ?? -1 });
                            finish();
                          }}
                          onCancel={finish}
                        />
                      );
                    };
                    // 카드 t589 — 「만들기」 뒤 서버 답(배정 「승인 대기」 또는 거절
                    // 사유)을 그 칸 아래에 보인다. 창은 닫혀도 답은 남는다.
                    const renderNewPresetReply = (field: NewPresetField) => {
                      const reply = newPresetReplyFor(field, newPresetPending, lastServerReply);
                      return reply ? (
                        <p className="beat-grid-cue-field-note" role="status">
                          {reply}
                        </p>
                      ) : null;
                    };
                    const poolStatusNote = (section: BeatGridDrawerSection | null): string | null => {
                      // 서랍을 기다리는 중이면 받는 상태를 말하고, 「먼저 열어야」로 잠그지 않는다.
                      if (!section) return drawerPoolStatusText(drawerState);
                      if (section.unread) return "이 풀을 콘솔에서 읽지 못했습니다.";
                      return null;
                    };
                    // 밝기 두 칸(리드 결정) — 디머 섹션을 프리셋과 효과로 나눈다. 효과는 첫 칸(디머 프리셋)의
                    // 「디머 효과」 그룹에만 보인다(두 번 나오지 않게 프리셋 목록에서 뺀다).
                    const dimmerEffects =
                      dimmerSection && !dimmerSection.unread
                        ? dimmerSection.entries.filter((entry) => entry.is_effect_band)
                        : [];
                    const dimmerPresetSection: BeatGridDrawerSection | null =
                      dimmerSection && !dimmerSection.unread
                        ? { ...dimmerSection, entries: dimmerSection.entries.filter((entry) => !entry.is_effect_band) }
                        : dimmerSection;
                    return rows.map((row) => {
                      const isBrightnessRow = row.field === "밝기";
                      const isPositionRow = row.field === "위치 프리셋";
                      const isColorRow = row.field === "색 프리셋";
                      // 카드 t551 계속(코디네이터 지시 2026-10-11, 조건 1/3) —
                      // 효과(움직임) 프리셋 직접 고르기(무빙 전용 행).
                      // 이 행의 드롭다운은 위치 풀 효과(움직임) 목록이라 무빙 줄에서만 고친다.
                      const isEffectRow = row.field === "효과 프리셋" && hints.includes("움직임");
                      const editable =
                        !!onEditRequest &&
                        (isBrightnessRow || isPositionRow || isColorRow || isEffectRow);
                      // 카드 t588 — 편집할 수 있는 칸은 늘 고르기 칸이다(시안).
                      const editing = editable;
                      return (
                        <div
                          className={`beat-grid-cue-field${editing ? " is-editing" : ""}`}
                          key={row.field}
                          data-field={row.field}
                        >
                          <span className="beat-grid-cue-field-label">{row.field}</span>
                          {editing && isBrightnessRow ? (
                            // 카드 t551 계속 — 밝기 단일모드(값/디머 프리셋/디머
                            // 효과, REQ-LDBEAT-015(c)) — mockup `#eM`/`eDimMode`
                            // 3항 선택 그대로. 디머 프리셋·디머 효과 목록은
                            // 서랍의 디머 섹션에서 온다(못 읽었으면 고르기가 꺼진다).
                            <span className="beat-grid-cue-field-edit">
                              {/* 밝기 두 칸(리드 결정): 「디머 프리셋 ▾」 과 「값 ▾」. 고른 칸이 밝기 방식을 정한다.
                                  프리셋 목록은 「이 곡 프리셋」·「쇼에 이미 있는 프리셋」 묶음과 「+ 새 프리셋」을 그대로 쓴다. */}
                              <select
                                value={
                                  brightnessModeDraft === "dimmer_preset"
                                    ? brightnessPresetDraft
                                    : brightnessModeDraft === "dimmer_effect"
                                      ? brightnessEffectDraft
                                      : ""
                                }
                                disabled={!dimmerSection || dimmerSection.unread}
                                aria-label="디머 프리셋"
                                onChange={(event) => {
                                  const no = event.target.value;
                                  if (no === "") return;
                                  if (dimmerEffects.some((entry) => entry.preset_no === no)) {
                                    setBrightnessModeDraft("dimmer_effect");
                                    setBrightnessEffectDraft(no);
                                  } else {
                                    setBrightnessModeDraft("dimmer_preset");
                                    setBrightnessPresetDraft(no);
                                  }
                                }}
                              >
                                {renderPresetOptions(splitDrawerSectionEntries(dimmerPresetSection), false, brightnessPresetDraft)}
                                {dimmerEffects.length > 0 && (
                                  <optgroup label="디머 효과">
                                    {dimmerEffects.map((entry) => (
                                      <option key={`fx-${entry.preset_no}`} value={entry.preset_no}>
                                        {entry.preset_no} {entry.name}
                                      </option>
                                    ))}
                                  </optgroup>
                                )}
                              </select>
                              <select
                                value={brightnessModeDraft === "value" ? brightnessDraft : ""}
                                aria-label="밝기 값(%)"
                                onChange={(event) => {
                                  setBrightnessModeDraft("value");
                                  setBrightnessDraft(event.target.value);
                                }}
                              >
                                <option value="" disabled>
                                  — 값 —
                                </option>
                                {brightnessModeDraft === "value" &&
                                  !BRIGHTNESS_VALUE_CHOICES.some((choice) => String(choice) === brightnessDraft) && (
                                    <option value={brightnessDraft}>{brightnessDraft}%</option>
                                  )}
                                {BRIGHTNESS_VALUE_CHOICES.map((choice) => (
                                  <option key={choice} value={String(choice)}>
                                    {choice}%
                                  </option>
                                ))}
                              </select>
                              <button
                                type="button"
                                onClick={() => {
                                  if (brightnessModeDraft === "value") {
                                    const changes = buildBrightnessValueChanges(Number(brightnessDraft));
                                    if (changes && selected && selectedTrack) {
                                      requestEdit("brightness", { bar: selected.bar, target: selectedTrack.group_name, changes });
                                    }
                                  } else if (
                                    brightnessModeDraft === "dimmer_preset" &&
                                    brightnessPresetDraft &&
                                    brightnessPresetDraft !== NEW_PRESET_OPTION_VALUE &&
                                    selected &&
                                    selectedTrack
                                  ) {
                                    requestEdit("brightness", {
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
                                    requestEdit("brightness", {
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
                              <button
                                type="button"
                                onClick={() =>
                                  seedEditDrafts(
                                    selectedCue,
                                    row.field as "밝기" | "위치 프리셋" | "색 프리셋" | "효과 프리셋",
                                  )
                                }
                              >
                                되돌리기
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
                              {brightnessModeDraft === "dimmer_preset" &&
                                brightnessPresetDraft === NEW_PRESET_OPTION_VALUE &&
                                renderNewPresetDialog("dimmer_preset", () => seedEditDrafts(selectedCue, "밝기"))}
                              {brightnessModeDraft === "dimmer_effect" &&
                                brightnessEffectDraft === NEW_PRESET_OPTION_VALUE &&
                                renderNewPresetDialog("dimmer_effect", () => seedEditDrafts(selectedCue, "밝기"))}
                              {renderNewPresetReply("dimmer_preset")}
                              {renderNewPresetReply("dimmer_effect")}
                              {renderEditReply("brightness")}
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
                                onChange={(event) => setPositionPresetDraft(event.target.value)}
                              >
                                {renderPresetOptions(splitDrawerSectionEntries(positionSection), true, positionPresetDraft)}
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
                                    requestEdit("position", {
                                      bar: selected.bar,
                                      target: selectedTrack.group_name,
                                      // 카드 t557 — 효과 번호대 항목이면 위치 효과로.
                                      changes: presetPickChanges(positionSection, "Position", positionPresetDraft),
                                    });
                                  }
                                  closeEdit();
                                }}
                              >
                                적용
                              </button>
                              <button
                                type="button"
                                onClick={() =>
                                  seedEditDrafts(
                                    selectedCue,
                                    row.field as "밝기" | "위치 프리셋" | "색 프리셋" | "효과 프리셋",
                                  )
                                }
                              >
                                되돌리기
                              </button>
                              {poolStatusNote(positionSection) && (
                                <p className="beat-grid-cue-field-note">{poolStatusNote(positionSection)}</p>
                              )}
                              {positionPresetDraft === NEW_PRESET_OPTION_VALUE &&
                                renderNewPresetDialog("position", () => seedEditDrafts(selectedCue, "위치 프리셋"))}
                              {renderNewPresetReply("position")}
                              {renderEditReply("position")}
                            </span>
                          ) : editing && isColorRow ? (
                            // 카드 t551 계속 — 색 프리셋 직접 고르기(위치와 같은
                            // 패턴, `colorSection` 출처만 다르다).
                            <span className="beat-grid-cue-field-edit">
                              <select
                                value={colorPresetDraft}
                                disabled={!colorSection || colorSection.unread}
                                aria-label="색 프리셋"
                                onChange={(event) => setColorPresetDraft(event.target.value)}
                              >
                                {renderPresetOptions(splitDrawerSectionEntries(colorSection), true, colorPresetDraft)}
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
                                    requestEdit("color", {
                                      bar: selected.bar,
                                      target: selectedTrack.group_name,
                                      // 카드 t557 — 효과 번호대 항목이면 색 효과(effect_kind color)로.
                                      changes: presetPickChanges(colorSection, "Color", colorPresetDraft),
                                    });
                                  }
                                  closeEdit();
                                }}
                              >
                                적용
                              </button>
                              <button
                                type="button"
                                onClick={() =>
                                  seedEditDrafts(
                                    selectedCue,
                                    row.field as "밝기" | "위치 프리셋" | "색 프리셋" | "효과 프리셋",
                                  )
                                }
                              >
                                되돌리기
                              </button>
                              {poolStatusNote(colorSection) && (
                                <p className="beat-grid-cue-field-note">{poolStatusNote(colorSection)}</p>
                              )}
                              {colorPresetDraft === NEW_PRESET_OPTION_VALUE &&
                                renderNewPresetDialog("color", () => seedEditDrafts(selectedCue, "색 프리셋"))}
                              {renderNewPresetReply("color")}
                              {renderEditReply("color")}
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
                                onChange={(event) => setEffectPresetDraft(event.target.value)}
                              >
                                {renderPresetOptions(splitDrawerSectionEffectEntries(positionSection), false, effectPresetDraft)}
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
                                    requestEdit("effect", {
                                      bar: selected.bar,
                                      target: selectedTrack.group_name,
                                      // 카드 t557 — 종류는 고른 항목의 풀이 정한다(이 목록은 위치 풀 효과).
                                      changes: presetPickChanges(positionSection, "Position", effectPresetDraft),
                                    });
                                  }
                                  closeEdit();
                                }}
                              >
                                적용
                              </button>
                              <button
                                type="button"
                                onClick={() =>
                                  seedEditDrafts(
                                    selectedCue,
                                    row.field as "밝기" | "위치 프리셋" | "색 프리셋" | "효과 프리셋",
                                  )
                                }
                              >
                                되돌리기
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
                              {effectPresetDraft === NEW_PRESET_OPTION_VALUE &&
                                renderNewPresetDialog("effect", () => seedEditDrafts(selectedCue, "효과 프리셋"))}
                              {renderNewPresetReply("effect")}
                              {renderEditReply("effect")}
                            </span>
                          ) : (
                            <span
                              className={`beat-grid-cue-field-value${row.value === UNSET_FIELD_LABEL ? " is-unset" : ""}${
                                editable ? " is-editable" : ""
                              }`}
                            >
                              {row.value}
                            </span>
                          )}
                          {/* 카드 t595 — 이 행이 빈 프리셋 번호를 가리키면(서버 판정) 한 줄. */}
                          {(() => {
                            const note = selectedCue
                              ? emptyPresetFieldNote(
                                  emptyPresetCells.get(cueEditKey(selectedTrack.group_name, selectedCue.bar)),
                                  row.field,
                                )
                              : null;
                            return note ? (
                              <p className="beat-grid-cue-field-note beat-grid-empty-preset-warn">{note}</p>
                            ) : null;
                          })()}
                        </div>
                      );
                    });
                  })()}
                  {/* 카드 t561 — 시안 순서: 밝기 → 위치 → 색 → 움직임 → 옆빛 L·R
                      (REQ-LDBEAT-021(b)). 「들어올 때」는 전환 화면으로 옮겼다
                      (REQ-LDBEAT-020(d)). */}
                  {selectedCue && roleFieldHints(selectedTrack.layer_role).includes("움직임") && (
                    <BeatGridMovementRow
                      // 카드 t588 — 막대가 바뀌거나 되돌리기를 누르면 새로 마운트해
                      // 고르기 초안을 그 칸의 현재 값으로 다시 채운다.
                      key={`${selectedTrack.group_name}:${selectedCue.bar}:${movementResetNonce}`}
                      value={
                        selectedCue.app_movement
                          ? formatAppMovementField(selectedCue.app_movement)
                          : UNSET_FIELD_LABEL
                      }
                      isUnset={!selectedCue.app_movement}
                      unverifiedTerms={unverifiedCells.get(cueEditKey(selectedTrack.group_name, selectedCue.bar)) ?? null}
                      // 카드 t584 — 다른 행과 같은 직접 고르기(①). 어휘는 서버에서만.
                      edit={
                        onEditRequest && grid.movement_vocabulary && selected
                          ? {
                              current: selectedCue.app_movement,
                              vocabulary: grid.movement_vocabulary,
                              // 카드 t588 — 늘 열려 있다(시안). 되돌리기는 다시 마운트로.
                              editing: true,
                              onOpen: () => undefined,
                              onApply: (movement) => {
                                requestEdit("movement", {
                                  bar: selected.bar,
                                  target: selectedTrack.group_name,
                                  changes: { app_movement: movement },
                                });
                              },
                              onCancel: () => setMovementResetNonce((n) => n + 1),
                            }
                          : null
                      }
                    />
                  )}
                  {renderEditReply("movement")}
                  {selectedTrack.layer_role === "side" && <BeatGridSideRow lrSplit={lrSplitToggleControl({ track: selectedTrack, stage: lrStage, segment: trackCueSegments(selectedTrack, maxBar).find((segment) => segment.cue === selectedCue), declarations: lrSplits, update: setLrSplits })} />}
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
                </BeatGridCueFocus>
              )}
              {selectedCue && (
                // 카드 t561 — 편집 칸 맨 아래, 지금 보는 화면에 맞는 명령(REQ-LDBEAT-020(c)).
                <BeatGridConsoleCommand
                  lines={
                    transitionView && selectedPrevCue
                      ? transitionConsoleCommandLines(
                          selectedCue,
                          secondsPerBar,
                          transitionMib(selectedPrevCue, selectedCue),
                          beatsPerBar,
                        )
                      : cueConsoleCommandLines(selectedTrack, selectedCue)
                  }
                />
              )}
            </>
          ) : (
            // 시안 `drawEd` 의 빈 안내문 그대로.
            <p className="beat-grid-empty beat-grid-cue-panel-empty">
              타임라인의 막대(큐)나 무대 그림의 장비를 누르면 여기서 고쳐요
              <br />
              <br />
              밝기 · 위치 · 색 · 움직임 · 들어올 때
              <br />
              <br />
              이음매 ◆ 를 누르면 전환, 「장면 전환」 알약을 누르면 그 순간 전체
            </p>
          )}
        </aside>
      </div>

      {/* ③ 하단 띠 — 2D 무대(왼쪽) + 이 마디 한눈에(오른쪽), 시안 `.insp`와
          같은 자리(타임라인 아래, 고정 높이, t537 레이아웃 교정). */}
      <div className="beat-grid-insp">
        <div className="beat-grid-stage-pane">
          {/* 카드 t586 — 시안 `#stT` 「12마디 · 25.1초」: 지금 보는 마디와 그 시각
              (곡 BPM 환산 — 모르면 마디만). */}
          <h5 className="beat-grid-stage-title">
            <span>무대</span>
            <span>
              {viewBar === 0 ? "앞박" : `${viewBar}마디`}
              {(() => {
                const seconds = barToSeconds(viewBar, secondsPerBar);
                return seconds === null ? "" : ` · ${seconds.toFixed(1)}초`;
              })()}
            </span>
          </h5>
          {/* 카드 t561 — 선택 테두리·그룹 이름표·장비 영역 클릭(REQ-LDBEAT-022). */}
          <BeatGridStage
            notes={stageNotes}
            motion={{ seconds: playbackSeconds, secondsPerBar, beatsPerBar }}
            presetBook={{ labels: grid.preset_labels, movements: grid.preset_movements }}
            fixtures={fixtures}
            tracks={grid.tracks}
            viewBar={viewBar}
            selectedTrackName={selectedTrack?.group_name ?? null}
            onSelectTrack={(trackIndex) => {
              const cue = cueForBar(grid.tracks[trackIndex], viewBar);
              if (cue) selectCue(trackIndex, cue.bar, false);
            }}
          />
          <p className="beat-grid-stage-note">
            2D 개념도 · 위 = 무대 뒤 · 노란 테두리 = 고른 줄 · 장비를 누르면 그 줄 편집 · 앱에서는 패치 좌표(Posx·Posy)로 실제 위치에 그림
          </p>
        </div>

        <div className="beat-grid-glance-pane">
          {/* 카드 t560(REQ-LDBEAT-023(d)) — 제목 줄은 스크롤 영역(아래
              `.beat-grid-glance-scroll`) 밖에 둔다 — 그래야 표 본문이
              아무리 길어져도 이 제목이 스크롤에 밀려 사라지지 않는다. */}
          {/* 카드 t586 — 시안 `#bsT` 「12마디 한눈에 — 벌스1」 + 오른쪽 안내. 구간
              이름은 곡 데이터(overviewModel)에서만 — 없으면 마디만. */}
          <h5 className="beat-grid-glance-title">
            <span>
              {glanceBarLabel(viewBar)} 한눈에
              {viewBarSectionLabel ? ` — ${viewBarSectionLabel}` : ""}
            </span>
            <span className="beat-grid-glance-hint">훑어보기 · 누르면 오른쪽에서 고치기</span>
          </h5>
          {/* t537 ② — 이 행에 걸린 SCENE 메모(§4 역할·효과 혼성 값, 트랙에
              못 옮긴 자리)를 표 위에 그대로 보여준다 — 추측해 채우지 않고
              「미정」으로 남긴 이유를 그 자리에서 읽을 수 있게 한다. */}
          {viewBarSceneMemo && (
            <p className="beat-grid-scene-memo-note">
              ⚠ {viewBarSceneMemo.text}
              <span className="beat-grid-scene-memo-source"> ({viewBarSceneMemo.sourceRef})</span>
            </p>
          )}
          <div className="beat-grid-glance-scroll">
            <table className="beat-grid-glance-table">
              {/* 카드 t560 후속(REQ-LDBEAT-023(a)(c)(d)) — 시안 `rowHTML`/
                  `cellHTML` 그대로 6칼럼(줄·밝기·위치·색·움직임·전환). 표
                  머리는 스크롤 중에도 고정된다(`styles.css`의
                  `position:sticky`). */}
              <thead>
                <tr>
                  <th>줄</th>
                  <th>밝기</th>
                  <th>위치</th>
                  <th>색</th>
                  <th>움직임</th>
                  <th>전환</th>
                </tr>
              </thead>
              <tbody>
                {/* 카드 t586 — 시안 `#bt tr.gh`: 줄을 타임라인과 같은 층 역할
                    폴더로 묶어 「▾ 앞빛 · key」 머리 줄을 단다. 접기/펴기는
                    타임라인 폴더와 같은 상태를 쓴다(시안 `OPEN` 공유). */}
                {folders.map((folder) => (
                  <Fragment key={folder.role}>
                    <tr className="beat-grid-glance-folder" onClick={() => toggleFolder(folder.role)}>
                      <td colSpan={6}>
                        {isFolderOpen(folder.role) ? "▾" : "▸"} {folder.label}
                        {folder.label !== folder.role && ` · ${folder.role}`}
                        {!isFolderOpen(folder.role) &&
                          collapsedFolderSummary(folder.tracks.length, changedRowsAtBar(folder.tracks))}
                      </td>
                    </tr>
                    {isFolderOpen(folder.role) &&
                      folder.tracks.map((track) => {
                  const trackIndex = grid.tracks.indexOf(track);
                  const cue = cueForBar(track, viewBar);
                  const isExpanded = expandedGlanceRows.has(track.group_name);
                  // 카드 t560(REQ-LDBEAT-023(b)) — 펼침 상세는 지금 보고 있는
                  // 마디(viewBar)가 걸친 칸 하나를 기준으로 계산한다.
                  const viewSegment = trackCueSegments(track, maxBar).find(
                    (segment) => viewBar >= segment.startBar && viewBar < segment.endBar,
                  );
                  const detail = viewSegment
                    ? buildGlanceRowDetail({
                        track,
                        startBar: viewSegment.startBar,
                        endBar: viewSegment.endBar,
                        secondsPerBar,
                        fixtures,
                      })
                    : null;
                  // 카드 t560 후속(mockup `changedTxt`) — derivable한 「바뀐
                  // 것」만 이름 칸 아래 작게 보인다. 곡 표시 범위의 첫 마디는
                  // 비교할 "이전"이 없어 늘 빈 문자열이다.
                  const isFirstBarOfRange = viewBar === grid.bar_range.start;
                  const previousCue = isFirstBarOfRange ? null : cueForBar(track, viewBar - 1);
                  const changed = changedFieldsLabel(previousCue, cue, isFirstBarOfRange);
                  // 전환 칸은 "지금 보는 마디가 그 칸의 시작 마디이고, 그
                  // 칸이 이 트랙의 첫 칸이 아닐 때"만 들어오는 전환을 보인다
                  // (mockup `rowHTML` 여섯째 칸과 같은 판정).
                  const isTransitionBar = cue !== null && cue.bar === viewBar && track.cues.indexOf(cue) > 0;
                  // 카드 t560 후속(REQ-LDBEAT-019(c)) — "이 구간 왼쪽·오른쪽
                  // 따로"/"L·R 다시 합치기" 토글이 이제 이 자리(펼침 상세
                  // 줄)에서만 뜬다. 분리 가능 데이터(실측 좌우 장비)가 없는
                  // 트랙이면 `lrSplitControl`이 `null`이라 링크 자체가 없다.
                  const hasLrSplit = lrSplits.has(track.group_name);
                  const lrSplitControl =
                    canDeclareLRSplit(track, lrStage) && viewSegment
                      ? {
                          isSplit: hasLrSplit,
                          onToggle: () =>
                            setLrSplits((prev) =>
                              hasLrSplit
                                ? clearLRSplit(prev, track.group_name)
                                : declareLRSplit(prev, track.group_name, {
                                    startBar: viewSegment.startBar,
                                    endBar: viewSegment.endBar,
                                  }),
                            ),
                        }
                      : null;
                  // 카드 t560 후속 — 자식 줄(└ L/R)은 분리 선언이 있고 지금
                  // 보는 마디가 그 선언 구간 안일 때만(mockup `drawBar`의
                  // `b>=SPLIT.a&&b<=SPLIT.b` 분기와 같은 판정).
                  const glanceChildRows = lrChildRowsForTrack(track, lrSplits, lrStage).filter(
                    (row) => viewBar >= row.startBar && viewBar < row.endBar,
                  );
                  const focus = (field: GlanceFocusTarget["field"]) => {
                    // t561 편집 칸 초점 배선 — 막대 클릭과 같은 selectCue 뒤에
                    // 그 칼럼의 필드로 초점을 둔다(selectCue 가 초점을 지우므로 뒤에).
                    const action = glanceFocusAction(field);
                    // 곡 첫 큐는 전환 토글이 비활성이므로(REQ-LDBEAT-020(b)) 큐 편집으로 연다.
                    selectCue(trackIndex, viewBar, action.transition && !isFirstCueOfSong(viewBar, grid));
                    setFocusField(action.focusField);
                    onGlanceFocusRequest?.(buildGlanceFocusTarget(track.group_name, viewBar, field));
                  };
                  return (
                    <Fragment key={track.group_name}>
                      {/* 카드 t560(REQ-LDBEAT-021(a), plan.md M9 step 4(나)) —
                          줄·칸을 누르면 그 자리에서 값을 바꾸지 않고(서버
                          요청 0건) 기존 `selected`를 그대로 설정해 오른쪽
                          편집 칸이 그 항목에 초점을 두고 연다 — 타임라인
                          막대를 눌렀을 때와 같은 메커니즘이다. 칼럼별 칸을
                          누르면 그 칼럼 이름을 초점으로 함께 올린다. */}
                      <tr
                        className={selected?.trackIndex === trackIndex ? "beat-grid-glance-row on" : "beat-grid-glance-row"}
                        onClick={() => focus(null)}
                      >
                        <td>
                          <button
                            type="button"
                            className="beat-grid-glance-expand-toggle"
                            title={isExpanded ? "상세 접기" : "상세 펼치기"}
                            onClick={(event) => {
                              event.stopPropagation();
                              setExpandedGlanceRows((prev) => {
                                const next = new Set(prev);
                                if (next.has(track.group_name)) next.delete(track.group_name);
                                else next.add(track.group_name);
                                return next;
                              });
                            }}
                          >
                            {isExpanded ? "▾" : "▸"}
                          </button>
                          {track.group_name}
                          {changed && <br />}
                          {changed && <small className="beat-grid-glance-changed">{changed}</small>}
                        </td>
                        <td onClick={(event) => { event.stopPropagation(); focus("밝기"); }}>
                          <GlanceCell value={brightnessCell(cue, drawerSections)} />
                        </td>
                        <td onClick={(event) => { event.stopPropagation(); focus("위치"); }}>
                          <GlanceCell value={positionCell(cue, track.layer_role, drawerSections)} />
                        </td>
                        <td onClick={(event) => { event.stopPropagation(); focus("색"); }}>
                          <GlanceCell value={colorCell(cue, track.layer_role, drawerSections)} />
                        </td>
                        <td onClick={(event) => { event.stopPropagation(); focus("움직임"); }}>
                          <GlanceCell value={movementCell(cue, track.layer_role, drawerSections)} />
                        </td>
                        <td onClick={(event) => { event.stopPropagation(); focus("전환"); }}>
                          <GlanceCell value={transitionCell(cue, isTransitionBar)} />
                        </td>
                      </tr>
                      {isExpanded && detail && (
                        <GlanceRowDetailCells detail={detail} colSpan={6} lrSplit={lrSplitControl} />
                      )}
                      {glanceChildRows.map((childRow) => (
                        <LRSplitGlanceRow
                          key={childRow.side}
                          child={childRow}
                          remainingColSpan={5}
                          onSelect={() =>
                            selectLRSplitChild(trackIndex, track.group_name, childRow.side, childRow.startBar)
                          }
                        />
                      ))}
                    </Fragment>
                  );
                      })}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
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
        {/* 카드 t586 — 시안 `.cmd` 의 「명령」 레이블. */}
        <span className="beat-grid-cmd-label">명령</span>
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
            if (next) requestDrawer();
          }}
        >
          📁 프리셋
        </button>
      </div>
      {/* 시안 명령창 아래 단축키 안내 줄(문구 그대로). */}
      <div className="beat-grid-hint-line">
        ← → 마디 이동 · 막대 = 큐 편집 · 이음매 ◆ = 전환 편집(◢ 페이드) · M = MIB · ! = 경고 · 「장면 전환」 알약 = 그 순간 전체 · 칩 = 같은 프리셋 강조
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
          {onPresetPlanRequest && <PresetPlanButton onClick={requestPresetPlanByHand} />}
          {presetPlanBusyRefused && (
            <p className="beat-grid-drawer-unread" role="alert">
              지금 서버가 다른 일을 처리하는 중이라 프리셋 계획 요청이 처리되지 않았습니다 — 끝난 뒤 다시 눌러 주세요.
            </p>
          )}
          {drawerSections === null && drawerFailed ? (
            <p className="beat-grid-drawer-unread" role="alert">
              {drawerBusyRefused
                ? "서버가 다른 일을 처리하는 중이라 서랍을 못 읽었습니다."
                : "서랍을 읽는 데 시간이 걸리고 있습니다."}{" "}
              <button type="button" onClick={requestDrawer}>
                다시 시도
              </button>
            </p>
          ) : drawerSections === null ? (
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
                    // 카드 t560(REQ-LDBEAT-023(c)) — 「설명 텍스트 · 이 곡에서 큐
                    // N곳 사용」 꼴을 앞에 두고(필수 모양), 기존 사용처 목록(카드
                    // t551)은 뒤에 보조로 남긴다(정보 손실 없음). 카드 t569 —
                    // 설명은 앱이 저장한 것만, 쇼 프리셋은 출처만 붙인다
                    // (presetChipTooltip.ts 모듈 주석).
                    title={
                      formatPresetChipTooltip(entry.description, entry.usage_count, entry.description_source) +
                      (entry.used_by.length
                        ? " — " + entry.used_by.map((u) => `${u.group_name ?? "?"} ${u.bar ?? "?"}마디`).join(", ")
                        : "")
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
