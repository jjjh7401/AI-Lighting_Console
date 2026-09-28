// PLAN CUE 수정요청 생성기 (t460, SPEC-LDDESIGN-001 REQ-087~095, 100~101).
//
// 이것은 편집기가 아니라 **요청 문장 생성기**다(REQ-092) — 큐시트 타임라인
// 객체를 로컬에서 바꾸지 않고, `changes` 매핑도 만들지 않는다. 만드는 것은
// 사람이 읽는 한국어 문장뿐이고, 그 문장은 기존 채팅 경로(`sendChat`)를
// 그대로 타고 나가 서버 파서(`parse_cue_sheet_edit_request`)를 거친다.
// 값 범위·부분 적용 금지·거절 사유는 전부 서버가 단일 진실 지점이다 — 이
// 컴포넌트는 힌트만 보여주고 최종 판정은 서버 응답을 그대로 표시한다.
//
// 구조 — 이 프로젝트의 "훅 없는 컴포넌트를 함수로 직접 호출해 시험한다"
// 관례(jsdom 없음, protocol.ts 헤더 주석 참고)를 지키기 위해 상태와 뷰를
// 가른다:
//  - `usePlanCueRequestGenerator` 훅이 모든 useState/useEffect/useRef를 쥔다.
//  - `PlanCueRequestGeneratorView`는 훅이 전혀 없는 순수 함수다 — 시험은
//    이 함수를 직접 호출해 리액트 엘리먼트 트리를 훑는다(CueMonitor.test.tsx
//    와 같은 패턴).
//  - `PlanCueRequestGenerator`(트리에 실제로 마운트되는 것)는 훅을 불러
//    뷰에 넘기기만 한다.
import { useEffect, useRef, useState } from "react";
import type { ReactElement } from "react";

import type {
  SongTimelineConceptRow,
  SongTimelineDraftState,
  SongTimelineReserveItem,
  SongTimelineSection,
} from "../protocol";
import {
  fetchPresetPool,
  PresetPoolPopup,
  type PresetEntry,
  type PresetPopupState,
} from "./PresetPoolPopup";
import { sectionIntensityPercent } from "./CueSheetTimeline";
import {
  buildCueRequestSentences,
  cueRequestDiffLabel,
  mixedColorLabel,
  mixedIntensityLabel,
  type GeneratorChange,
  type GeneratorChangeItem,
  type MibChange,
  type TrackingChange,
} from "./cueRequestSentence";
import { deriveWarningsForChange, reserveLock } from "./cueRequestWarnings";
import { sectionPosition } from "./runbookM7";

/** REQ-LDDESIGN-089 — 콘솔 반영 값 패널이 여는 풀 번호(포지션 2·컬러 4·
 * 딤머 1·이펙트 21). 감독 확정 문언 그대로다 — 지어내지 않는다. */
const POOL_POSITION = 2;
const POOL_COLOR = 4;
const POOL_DIMMER = 1;
const POOL_EFFECT = 21;

/** `cue_sheet_edit.py` `_GROUP_COLOR_FIELD` — 컬러 칸을 가진 그룹은 이
 * 둘뿐이다. 새 그룹을 여기서 지어내지 않는다. */
export type LineState = "selected" | "requested" | "applied" | "rejected";

export interface StackEntry {
  id: string;
  change: GeneratorChange;
  warnings: string[];
  state: LineState;
  rejectionReason?: string;
}

// t470 — "position"이 포지션 행 전용 새 필드다(t460 이 임시로 쓰던
// "movement"는 그대로 둔다 — 다른 곳에서 참조하지 않지만 타입/시험 호환을
// 위해 지우지 않는다). "phaser"는 딤머 풀 1·컬러 풀 4 두 버튼이 공유한다.
export type PopupField = "movement" | "effect" | "palette_primary" | "dimmer" | "position" | "phaser";

/** t470 — 트래킹 4택(`cue_sheet_edit.py` TRACKING_VALUES 그대로). */
const TRACKING_VALUES = ["Track", "Block", "Cue Only", "Release"] as const;

/** t470 — MIB 4택. 버튼 라벨은 서버 `_mib_label`과 같은 규칙("none"만
 * "없음"으로 보인다) — 값 자체는 `cue_sheet_edit.py` MIB_MODES 그대로다. */
const MIB_VALUES = ["none", "dark", "mark", "live"] as const;
const MIB_BUTTON_LABEL: Record<MibChange["value"], string> = {
  none: "없음",
  dark: "dark",
  mark: "mark",
  live: "live",
};

let stackIdSeq = 0;
function nextStackId(): string {
  stackIdSeq += 1;
  return `gen-${stackIdSeq}`;
}

/** 변경의 "서명" — 같은 필드·같은 그룹 조합을 다시 적용하면 새 줄을 더
 * 쌓지 않고 값만 갱신한다(감독이 값을 여러 번 조정해도 diff 줄이 늘지
 * 않는다). */
function changeSignature(change: GeneratorChange): string {
  const groups = "groups" in change && change.groups ? [...change.groups].sort().join(",") : "";
  return `${change.field}:${groups}`;
}

/** 페이드 변경 줄의 「이전 값」. 카드 t490 — 재질의 대기에서는 값이 `null`(미정)이라
 * 없는 키와 같이 「—」다(`null초` 로 찍지 않는다). */
export function fadeBeforeLabel(section: SongTimelineSection): string {
  return section.fade_seconds != null ? `${section.fade_seconds}초` : "—";
}

/** REQ-090 — BLIND 는 해제 구간(reserve 항목의 screen_position) 전까지 잠금.
 * `position` 은 `sectionPosition()` 값이다(t481 — released_q 는 컨셉 행 번호라
 * 구간 큐 번호와 비교하면 안 된다). 리저브 정보 자체가 없으면(구버전 페이로드)
 * 잠그지 않는다 — 정보 부재를 잠금 사유로 쓰지 않는다. */
export function isGroupLocked(
  groupName: string,
  reserve: SongTimelineReserveItem[] | undefined,
  position: number,
  sections: ReadonlyArray<Pick<SongTimelineSection, "cue_number">>,
): boolean {
  // t481 — 판정은 리저브 경고와 같은 한 곳(`reserveLock`)에서 한다.
  return reserveLock(groupName, reserve, position, sections) !== null;
}

/** REQ-095 — 수락의 증거는 서버가 편집 성공 때만 새로 찍어 보내는 초안
 * 표식(`_draft_badge`)이다. depth 증가만 보면 안 된다: 서버 되돌리기 기록은
 * `deque(maxlen=20)`(`server/web/timeline_draft.py`)이라 20단계에서는 편집이
 * 성공해도 depth 가 20 그대로다 — 수락을 거절로 읽는다. 그래서 「이 턴에 새
 * 표식이 왔고, depth 가 줄지 않았고(되돌리기가 아니다), 바뀐 내용 보고가
 * 있다」로 판정한다. 별도 검증 로직이 아니라 서버 표식의 비교뿐이다. 순수
 * 함수라 useEffect 타이밍과 분리해 검증할 수 있다. */
export function turnAccepted(
  before: SongTimelineDraftState | undefined,
  after: SongTimelineDraftState | undefined,
): boolean {
  if (after === undefined || after === before) return false;
  return after.depth >= (before?.depth ?? 0) && after.last_change.length > 0;
}

/** 한 줄 전송의 결과를 스택에 반영한다 — 수락 → applied, 거절 → rejected +
 * 사유(REQ-092). 순수 함수. */
export function applyTurnResult(
  stack: StackEntry[],
  sendingId: string,
  outcome: { accepted: true } | { accepted: false; rejectionReason: string },
): StackEntry[] {
  return stack.map((entry) =>
    entry.id === sendingId
      ? outcome.accepted
        ? { ...entry, state: "applied" as const }
        : { ...entry, state: "rejected" as const, rejectionReason: outcome.rejectionReason }
      : entry,
  );
}

export interface PlanCueRequestGeneratorProps {
  section: SongTimelineSection;
  /** 후렴 밝기 역전 경고(REQ-093 (1))가 필요로 하는 곡 전체 구간. */
  allSections: SongTimelineSection[];
  conceptRow: SongTimelineConceptRow | undefined;
  reserve?: SongTimelineReserveItem[];
  /** REQ-095 — 서버 초안 표식(`timeline.draft`). 요청 수락 여부는 전송
   * 뒤 이 표식이 새로 왔는지로 판단한다(`turnAccepted`). */
  draft?: SongTimelineDraftState;
  /** 한 번 호출 = 한 줄 전송. 기존 `sendChat`과 같은 모양이라, 생성기가
   * 보낸 요청도 감독이 손으로 친 것과 같은 대화 경로를 탄다(REQ-094). */
  onSend: (text: string, cueNumber: number) => void;
  responding: boolean;
  /** REQ-092 — 거절 사유. 가장 최근 `assistant` 채팅 항목의 텍스트. */
  lastAssistantText: string | null;
}

export interface PlanCueRequestGeneratorViewModel {
  cueNumber: number;
  statusLabel: string;
  groups: string[];
  selectedGroups: string[];
  isGroupLocked: (group: string) => boolean;
  onToggleGroup: (group: string) => void;
  intensityInput: string;
  onIntensityInputChange: (value: string) => void;
  onApplyIntensity: () => void;
  beforeIntensityLabel: string;
  fadeInput: string;
  onFadeInputChange: (value: string) => void;
  onApplyFade: () => void;
  transValue: "SNAP" | "XFADE" | "FADE";
  onApplyTrans: (value: "SNAP" | "XFADE" | "FADE") => void;
  /** t470 — 트래킹 4택. */
  trackingValue: TrackingChange["value"];
  onApplyTracking: (value: TrackingChange["value"]) => void;
  /** t470 — MIB 4택. */
  mibValue: MibChange["value"];
  onApplyMib: (value: MibChange["value"]) => void;
  positionLabel: string;
  colorLabel: string;
  colorButtonDisabled: boolean;
  dimLabel: string;
  effectLabel: string;
  /** t470 — 페이저 프리셋 이름(딤머 풀 1 또는 컬러 풀 4에서 고른 것). */
  phaserLabel: string;
  onOpenPopup: (field: PopupField, poolNo: number) => void;
  stack: StackEntry[];
  onRemoveEntry: (id: string) => void;
  removeDisabledId: string | null;
  freeText: string;
  onFreeTextChange: (value: string) => void;
  onCancelSelection: () => void;
  cancelDisabled: boolean;
  onSendAll: () => void;
  sendDisabled: boolean;
  popup: { field: PopupField; state: PresetPopupState } | null;
  onClosePopup: () => void;
  onPopupRefresh: () => void;
  onPopupSelect: (entry: PresetEntry) => void;
}

/** 모든 상태(useState/useEffect/useRef)를 쥐는 훅 — 뷰는 여기서 나오는
 * 값·핸들러만 본다. */
export function usePlanCueRequestGenerator({
  section,
  allSections,
  conceptRow,
  reserve,
  draft,
  onSend,
  responding,
  lastAssistantText,
}: PlanCueRequestGeneratorProps): PlanCueRequestGeneratorViewModel {
  const groups = (section.intensity ?? []).map((entry) => entry.group);
  const [selectedGroups, setSelectedGroups] = useState<string[]>([]);
  const [intensityInput, setIntensityInput] = useState("");
  const [effectName, setEffectName] = useState<string | null>(null);
  const [colorName, setColorName] = useState<string | null>(null);
  const [dimName, setDimName] = useState<string | null>(null);
  // t470 — 포지션 행은 이제 "position" 문장을 만든다(무브먼트가 아니다).
  // 번호("2.<no>")는 선택 시점에 합성해 upsertChange 로 바로 넘긴다 — 화면
  // 표시(positionLabel)는 이름만 보이므로 따로 상태에 들고 있지 않는다.
  const [positionName, setPositionName] = useState<string | null>(null);
  const [phaserName, setPhaserName] = useState<string | null>(null);
  const [fadeInput, setFadeInput] = useState("");
  const [transValue, setTransValue] = useState<"SNAP" | "XFADE" | "FADE">("SNAP");
  // t470 — trans 와 같은 방식: 로컬 버튼 상태는 이전에 고른 값을 기억할
  // 뿐(첫 기본값), 실제 이전값은 적용 시점에 section 에서 읽는다.
  const [trackingValue, setTrackingValue] = useState<TrackingChange["value"]>("Track");
  const [mibValue, setMibValue] = useState<MibChange["value"]>("none");
  const [freeText, setFreeText] = useState("");
  const [stack, setStack] = useState<StackEntry[]>([]);
  const [popup, setPopup] = useState<{ field: PopupField; state: PresetPopupState } | null>(null);

  const [sendingId, setSendingId] = useState<string | null>(null);
  const baselineDraftRef = useRef(draft);
  const queueRef = useRef<{ id: string; sentence: string }[]>([]);
  const prevResponding = useRef(responding);

  const cueNumber = section.cue_number;
  const position = sectionPosition(section, allSections);

  // 턴 종료(D1) 감시 — responding: true → false 전이에서만 판정한다.
  useEffect(() => {
    if (prevResponding.current && !responding && sendingId !== null) {
      const accepted = turnAccepted(baselineDraftRef.current, draft);
      if (accepted) {
        setStack((prev) => applyTurnResult(prev, sendingId, { accepted: true }));
        const next = queueRef.current.shift();
        if (next) {
          baselineDraftRef.current = draft;
          setSendingId(next.id);
          setStack((prev) => prev.map((e) => (e.id === next.id ? { ...e, state: "requested" } : e)));
          onSend(next.sentence, cueNumber);
        } else {
          // REQ-044 — 스택의 전 항목이 수락되면 스택을 비운다.
          setStack([]);
          setFreeText("");
          setSendingId(null);
        }
      } else {
        setStack((prev) =>
          applyTurnResult(prev, sendingId, {
            accepted: false,
            rejectionReason: lastAssistantText ?? "코파일럿이 응답하지 않았습니다.",
          }),
        );
        queueRef.current = [];
        setSendingId(null);
      }
    }
    prevResponding.current = responding;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [responding, draft, sendingId, lastAssistantText, onSend, cueNumber]);

  function upsertChange(change: GeneratorChange) {
    const warnings = deriveWarningsForChange({ section, allSections, conceptRow, reserve }, change);
    const signature = changeSignature(change);
    setStack((prev) => {
      const existingIndex = prev.findIndex(
        (entry) => entry.state === "selected" && changeSignature(entry.change) === signature,
      );
      const entry: StackEntry = { id: nextStackId(), change, warnings, state: "selected" };
      if (existingIndex === -1) return [...prev, entry];
      const next = [...prev];
      next[existingIndex] = { ...entry, id: prev[existingIndex].id };
      return next;
    });
  }

  function toggleGroup(group: string) {
    if (isGroupLocked(group, reserve, position, allSections)) return; // REQ-090 — 잠긴 그룹은 선택되지 않는다.
    setSelectedGroups((prev) =>
      prev.includes(group) ? prev.filter((g) => g !== group) : [...prev, group],
    );
  }

  function beforeIntensityLabel(): string {
    if (selectedGroups.length === 0) return `${sectionIntensityPercent(section)}%`;
    const levels = selectedGroups.map(
      (g) => section.intensity?.find((entry) => entry.group === g)?.level ?? 0,
    );
    return mixedIntensityLabel(levels);
  }

  function beforeColorLabel(): string {
    if (selectedGroups.length !== 1) {
      return mixedColorLabel([section.palette_primary, section.palette_secondary]);
    }
    return selectedGroups[0] === "BACK"
      ? section.palette_secondary ?? "—"
      : section.palette_primary ?? "—";
  }

  function applyIntensity() {
    const value = Number(intensityInput);
    if (!Number.isFinite(value)) return;
    upsertChange({
      field: "intensity",
      groups: selectedGroups.length > 0 ? [...selectedGroups] : null,
      value,
      before: beforeIntensityLabel(),
    });
  }

  function applyFade() {
    const value = Number(fadeInput);
    if (!Number.isFinite(value)) return;
    upsertChange({
      field: "fade_seconds",
      value,
      before: fadeBeforeLabel(section),
    });
  }

  function applyTrans(value: "SNAP" | "XFADE" | "FADE") {
    setTransValue(value);
    upsertChange({ field: "trans", value, before: section.trans ?? "—" });
  }

  // t466/t470 — 이전값 없으면 "Track"으로 본다(서버 `_set_default` 규칙과 동일).
  function applyTracking(value: TrackingChange["value"]) {
    setTrackingValue(value);
    upsertChange({ field: "tracking", value, before: section.tracking ?? "Track" });
  }

  // t466/t470 — `mib_mode`는 조립기가 계산한 기존 `mib`(참/거짓)와는 다른
  // 칸이다(건드리지 않는다). 이전값은 `section.mib_mode`만 읽고, 없으면
  // "없음"으로 보인다(서버 `_mib_label` 규칙과 동일).
  function applyMib(value: MibChange["value"]) {
    setMibValue(value);
    const before = section.mib_mode;
    const beforeLabel = before ? MIB_BUTTON_LABEL[before as MibChange["value"]] ?? before : "없음";
    upsertChange({ field: "mib_mode", value, before: beforeLabel });
  }

  function removeEntry(id: string) {
    if (sendingId === id) return; // 전송 중인 줄은 항목별 제거로 지우지 않는다.
    setStack((prev) => prev.filter((entry) => entry.id !== id));
  }

  function cancelSelection() {
    if (sendingId !== null) return; // 전송 중에는 되돌릴 게 없다 — 서버 상태와 어긋나는 취소를 막는다.
    setStack([]);
    setFreeText("");
  }

  function sendAll() {
    if (stack.length === 0 || sendingId !== null) return;
    const items: GeneratorChangeItem[] = stack.map((entry) => ({ id: entry.id, change: entry.change }));
    const sentences = buildCueRequestSentences(cueNumber, items, freeText);
    if (sentences.length === 0) return;
    const queue = stack.map((entry, index) => ({ id: entry.id, sentence: sentences[index] }));
    queueRef.current = queue.slice(1);
    const first = queue[0];
    baselineDraftRef.current = draft;
    setStack((prev) => prev.map((entry) => (entry.id === first.id ? { ...entry, state: "requested" } : entry)));
    setSendingId(first.id);
    onSend(first.sentence, cueNumber);
  }

  function openPopup(field: PopupField, poolNo: number) {
    setPopup({ field, state: { phase: "loading", pool: { no: poolNo, name: "" } } });
    void fetchPresetPool(poolNo).then((next) => setPopup({ field, state: next }));
  }

  function handlePopupSelect(entry: PresetEntry) {
    if (!popup) return;
    const field = popup.field;
    setPopup(null);
    if (field === "movement") {
      // t470 — 포지션 행이 이제 이 필드 대신 "position"을 쓴다(아래). 이
      // 분기는 다른 곳에서 field: "movement" 팝업을 열지 않아 지금은 UI에서
      // 도달하지 않지만, `MovementChange` 타입·PopupField 값을 지우지 않고
      // 그대로 둔다(범위 밖 변경 금지).
      upsertChange({ field: "movement", value: entry.name, before: section.movement ?? "—" });
      return;
    }
    if (field === "position") {
      // t470 — 포지션 프리셋은 풀 2에서만 온다(`_POSITION_POOL`). 번호는
      // "2.<point>" 형태로 합성한다 — entry.no 는 그 풀 안의 진짜 번호다.
      const presetNo = `${POOL_POSITION}.${entry.no}`;
      setPositionName(entry.name);
      upsertChange({
        field: "position",
        value: entry.name,
        presetNo,
        before: section.position ?? "—",
      });
      return;
    }
    if (field === "phaser") {
      // t470 — 딤머 풀 1·컬러 풀 4 어느 쪽에서 골라도 값은 이름 문자열
      // 하나뿐이다(REQ-089 P4).
      setPhaserName(entry.name);
      upsertChange({ field: "phaser", value: entry.name, before: section.phaser ?? "—" });
      return;
    }
    if (field === "effect") {
      setEffectName(entry.name);
      upsertChange({ field: "effect", value: entry.name, before: section.effect ?? "—" });
      return;
    }
    if (field === "palette_primary") {
      // 컬러는 그룹 하나에만 싣는다(문장 문법). 어느 그룹이 컬러 칸을 갖는지는
      // 서버(`_GROUP_COLOR_FIELD`)가 판정하고 거절 사유를 그 줄에 돌려준다
      // — UI 가 같은 표를 복제하지 않는다(REQ-092).
      if (selectedGroups.length !== 1) return;
      setColorName(entry.name);
      upsertChange({
        field: "palette_primary",
        groups: [selectedGroups[0]] as [string],
        value: entry.name,
        before: beforeColorLabel(),
      });
      return;
    }
    // dimmer — REQ-089 "이름을 저장하라"의 표시 전용 참조다. PresetEntry 에는
    // 숫자 % 값이 없어(딤머 프리셋의 조도는 콘솔만 안다) 이 선택 하나로는
    // 보낼 문장을 만들 수 없다 — 위 조도 입력이 실제 전송 경로다. 이 값은
    // "무엇을 눌렀는지" 표시용으로만 남는다(t460 plan.md Gap).
    setDimName(entry.name);
  }

  const colorButtonDisabled = selectedGroups.length !== 1;

  return {
    cueNumber,
    statusLabel: stack.length === 0 ? "바뀐 항목 없음" : `바꾼 것 ${stack.length} — 코파일럿 확인 대기`,
    groups,
    selectedGroups,
    isGroupLocked: (group) => isGroupLocked(group, reserve, position, allSections),
    onToggleGroup: toggleGroup,
    intensityInput,
    onIntensityInputChange: setIntensityInput,
    onApplyIntensity: applyIntensity,
    beforeIntensityLabel: beforeIntensityLabel(),
    fadeInput,
    onFadeInputChange: setFadeInput,
    onApplyFade: applyFade,
    transValue,
    onApplyTrans: applyTrans,
    trackingValue,
    onApplyTracking: applyTracking,
    mibValue,
    onApplyMib: applyMib,
    positionLabel: positionName ?? section.position ?? "—",
    colorLabel: colorName ?? beforeColorLabel(),
    colorButtonDisabled,
    dimLabel: dimName ?? "—",
    effectLabel: effectName ?? section.effect ?? "—",
    phaserLabel: phaserName ?? section.phaser ?? "—",
    onOpenPopup: openPopup,
    stack,
    onRemoveEntry: removeEntry,
    removeDisabledId: sendingId,
    freeText,
    onFreeTextChange: setFreeText,
    onCancelSelection: cancelSelection,
    cancelDisabled: sendingId !== null || (stack.length === 0 && freeText === ""),
    onSendAll: sendAll,
    sendDisabled: stack.length === 0 || sendingId !== null,
    popup,
    onClosePopup: () => setPopup(null),
    onPopupRefresh: () => {
      if (!popup) return;
      const no = popup.state.phase === "ready" ? popup.state.contents.pool.no : popup.state.pool.no;
      openPopup(popup.field, no);
    },
    onPopupSelect: handlePopupSelect,
  };
}

/** 훅이 전혀 없는 순수 뷰 — 시험은 이 함수를 직접 호출한다(jsdom 없이). */
export function PlanCueRequestGeneratorView(vm: PlanCueRequestGeneratorViewModel): ReactElement {
  return (
    <div className="plan-cue-generator" aria-label="PLAN CUE 수정요청 생성기">
      <header className="plan-cue-generator-status">{vm.statusLabel}</header>

      <div className="plan-cue-generator-body">
        <section className="plan-cue-generator-editor" aria-label="그룹 다중 선택 편집기">
          <div className="plan-cue-generator-chips" role="group" aria-label="기구 그룹">
            {vm.groups.map((group) => {
              const locked = vm.isGroupLocked(group);
              const selected = vm.selectedGroups.includes(group);
              return (
                <button
                  key={group}
                  type="button"
                  className={`plan-cue-chip${selected ? " is-selected" : ""}${locked ? " is-locked" : ""}`}
                  disabled={locked}
                  aria-pressed={selected}
                  onClick={() => vm.onToggleGroup(group)}
                >
                  {group}
                  {locked && " 🔒"}
                </button>
              );
            })}
          </div>

          <div className="plan-cue-generator-field">
            <label>
              밝기 (0-100)
              <input
                type="number"
                min={0}
                max={100}
                value={vm.intensityInput}
                onChange={(event) => vm.onIntensityInputChange(event.target.value)}
              />
            </label>
            <span className="plan-cue-generator-before">현재 {vm.beforeIntensityLabel}</span>
            <button type="button" onClick={vm.onApplyIntensity} disabled={vm.intensityInput === ""}>
              적용
            </button>
          </div>

          <div className="plan-cue-generator-field">
            <label>
              페이드 (초, ≤60)
              <input
                type="number"
                min={0}
                max={60}
                value={vm.fadeInput}
                onChange={(event) => vm.onFadeInputChange(event.target.value)}
              />
            </label>
            <button type="button" onClick={vm.onApplyFade} disabled={vm.fadeInput === ""}>
              적용
            </button>
          </div>

          <div className="plan-cue-generator-field" role="group" aria-label="전환">
            {(["SNAP", "XFADE", "FADE"] as const).map((value) => (
              <button
                key={value}
                type="button"
                className={`plan-cue-generator-trans${vm.transValue === value ? " is-selected" : ""}`}
                onClick={() => vm.onApplyTrans(value)}
              >
                {value}
              </button>
            ))}
          </div>

          <div className="plan-cue-generator-field" role="group" aria-label="트래킹">
            {TRACKING_VALUES.map((value) => (
              <button
                key={value}
                type="button"
                className={`plan-cue-generator-trans${vm.trackingValue === value ? " is-selected" : ""}`}
                onClick={() => vm.onApplyTracking(value)}
              >
                {value}
              </button>
            ))}
          </div>

          <div className="plan-cue-generator-field" role="group" aria-label="MIB">
            {MIB_VALUES.map((value) => (
              <button
                key={value}
                type="button"
                className={`plan-cue-generator-trans${vm.mibValue === value ? " is-selected" : ""}`}
                onClick={() => vm.onApplyMib(value)}
              >
                {MIB_BUTTON_LABEL[value]}
              </button>
            ))}
          </div>
        </section>

        <section className="plan-cue-generator-console-values" aria-label="콘솔 반영 값">
          <div className="plan-cue-generator-row">
            <span>포지션</span>
            <span>{vm.positionLabel}</span>
            <button type="button" onClick={() => vm.onOpenPopup("position", POOL_POSITION)}>
              바꾸기
            </button>
          </div>
          <div className="plan-cue-generator-row">
            <span>컬러</span>
            <span>{vm.colorLabel}</span>
            <button
              type="button"
              disabled={vm.colorButtonDisabled}
              onClick={() => vm.onOpenPopup("palette_primary", POOL_COLOR)}
            >
              바꾸기
            </button>
          </div>
          <div className="plan-cue-generator-row">
            <span>딤머</span>
            <span>{vm.dimLabel}</span>
            <button type="button" onClick={() => vm.onOpenPopup("dimmer", POOL_DIMMER)}>
              바꾸기
            </button>
          </div>
          <div className="plan-cue-generator-row">
            <span>이펙트</span>
            <span>{vm.effectLabel}</span>
            <button type="button" onClick={() => vm.onOpenPopup("effect", POOL_EFFECT)}>
              바꾸기
            </button>
          </div>
          <div className="plan-cue-generator-row">
            <span>페이저</span>
            <span>{vm.phaserLabel}</span>
            {/* t470 P4 — 페이저 프리셋은 딤머 풀 1·컬러 풀 4 둘 다에 있다.
                고른 이름 하나로 같은 "phaser" 문장을 만든다. */}
            <button type="button" onClick={() => vm.onOpenPopup("phaser", POOL_DIMMER)}>
              딤머 풀 바꾸기
            </button>
            <button type="button" onClick={() => vm.onOpenPopup("phaser", POOL_COLOR)}>
              컬러 풀 바꾸기
            </button>
          </div>
        </section>
      </div>

      <div className="plan-cue-generator-stack" aria-label="변경 스택">
        {vm.stack.length === 0 ? (
          <p className="plan-cue-generator-empty">바뀐 항목이 없습니다.</p>
        ) : (
          <ul>
            {vm.stack.map((entry) => (
              <li key={entry.id} className={`plan-cue-generator-diff is-${entry.state}`}>
                <span>{cueRequestDiffLabel(entry.change)}</span>
                {entry.warnings.map((warning) => (
                  <span className="plan-cue-generator-warning" key={warning}>
                    {warning}
                  </span>
                ))}
                {entry.state === "rejected" && (
                  <span className="plan-cue-generator-rejection">거절: {entry.rejectionReason}</span>
                )}
                <button
                  type="button"
                  className="plan-cue-generator-remove"
                  aria-label="이 줄 제거"
                  disabled={vm.removeDisabledId === entry.id}
                  onClick={() => vm.onRemoveEntry(entry.id)}
                >
                  ✕
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="plan-cue-generator-free-text">
        <input
          type="text"
          placeholder="자유 입력 한 줄 (예: 그리고 이 구간 전체를 반 박자 당겨줘)"
          value={vm.freeText}
          onChange={(event) => vm.onFreeTextChange(event.target.value)}
        />
      </div>

      <div className="plan-cue-generator-actions">
        <button type="button" onClick={vm.onCancelSelection} disabled={vm.cancelDisabled}>
          선택 취소
        </button>
        <button
          type="button"
          className="plan-cue-generator-submit"
          disabled={vm.sendDisabled}
          onClick={vm.onSendAll}
        >
          코파일럿에게 반영 요청
        </button>
      </div>

      {vm.popup && (
        <PresetPoolPopup
          state={vm.popup.state}
          onClose={vm.onClosePopup}
          onRefresh={vm.onPopupRefresh}
          onSelect={vm.onPopupSelect}
        />
      )}
    </div>
  );
}

/** 실제로 트리에 마운트되는 컴포넌트 — 훅은 여기(그리고 위 훅 안)에서만
 * 산다. `PlanCueRequestGeneratorView`를 함수로 그대로 호출한다(JSX가
 * 아니다 — 새 컴포넌트 레이어를 하나 더 얹지 않는다). */
export function PlanCueRequestGenerator(props: PlanCueRequestGeneratorProps): ReactElement {
  return PlanCueRequestGeneratorView(usePlanCueRequestGenerator(props));
}
