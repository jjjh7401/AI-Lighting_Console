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

import type { SongTimelineConceptRow, SongTimelineReserveItem, SongTimelineSection } from "../protocol";
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
} from "./cueRequestSentence";
import { deriveWarningsForChange } from "./cueRequestWarnings";

/** REQ-LDDESIGN-089 — 콘솔 반영 값 패널이 여는 풀 번호(포지션 2·컬러 4·
 * 딤머 1·이펙트 21). 감독 확정 문언 그대로다 — 지어내지 않는다. */
const POOL_POSITION = 2;
const POOL_COLOR = 4;
const POOL_DIMMER = 1;
const POOL_EFFECT = 21;

/** `cue_sheet_edit.py` `_GROUP_COLOR_FIELD` — 컬러 칸을 가진 그룹은 이
 * 둘뿐이다. 새 그룹을 여기서 지어내지 않는다. */
const COLOR_CAPABLE_GROUPS = new Set(["KEY", "BACK"]);

export type LineState = "selected" | "requested" | "applied" | "rejected";

export interface StackEntry {
  id: string;
  change: GeneratorChange;
  warnings: string[];
  state: LineState;
  rejectionReason?: string;
}

export type PopupField = "movement" | "effect" | "palette_primary" | "dimmer";

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

/** REQ-090 — BLIND 는 해제 큐(reserve 항목의 released_q) 전까지 잠금.
 * 리저브 정보 자체가 없으면(구버전 페이로드) 잠그지 않는다 — 정보 부재를
 * 잠금 사유로 쓰지 않는다. */
export function isGroupLocked(
  groupName: string,
  reserve: SongTimelineReserveItem[] | undefined,
  cueNumber: number,
): boolean {
  const item = reserve?.find((entry) => entry.name.toUpperCase() === groupName.toUpperCase());
  if (!item) return false;
  return item.released_q === null || cueNumber < item.released_q;
}

/** REQ-095 — depth 증가만이 수락의 증거다: 되돌리기 깊이의 진실 지점은
 * 서버(`TimelineDraftHistory.depth`)이고, 이 함수는 그 비교만 한다(별도
 * 판정 로직을 만들지 않는다). 순수 함수라 useEffect 타이밍과 분리해
 * 검증할 수 있다. */
export function turnAccepted(depthBefore: number, depthAfter: number): boolean {
  return depthAfter > depthBefore;
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
  /** REQ-095 — 되돌리기 깊이의 진실 지점(`TimelineDraftHistory.depth`).
   * 요청 수락 여부는 이 값이 전송 직전보다 늘었는지로만 판단한다. */
  draftDepth: number;
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
  positionLabel: string;
  colorLabel: string;
  colorButtonDisabled: boolean;
  dimLabel: string;
  effectLabel: string;
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
  draftDepth,
  onSend,
  responding,
  lastAssistantText,
}: PlanCueRequestGeneratorProps): PlanCueRequestGeneratorViewModel {
  const groups = (section.intensity ?? []).map((entry) => entry.group);
  const [selectedGroups, setSelectedGroups] = useState<string[]>([]);
  const [intensityInput, setIntensityInput] = useState("");
  const [movementName, setMovementName] = useState<string | null>(null);
  const [effectName, setEffectName] = useState<string | null>(null);
  const [colorName, setColorName] = useState<string | null>(null);
  const [dimName, setDimName] = useState<string | null>(null);
  const [fadeInput, setFadeInput] = useState("");
  const [transValue, setTransValue] = useState<"SNAP" | "XFADE" | "FADE">("SNAP");
  const [freeText, setFreeText] = useState("");
  const [stack, setStack] = useState<StackEntry[]>([]);
  const [popup, setPopup] = useState<{ field: PopupField; state: PresetPopupState } | null>(null);

  const [sendingId, setSendingId] = useState<string | null>(null);
  const baselineDepthRef = useRef(draftDepth);
  const queueRef = useRef<{ id: string; sentence: string }[]>([]);
  const prevResponding = useRef(responding);

  const cueNumber = section.cue_number;

  // 턴 종료(D1) 감시 — responding: true → false 전이에서만 판정한다.
  useEffect(() => {
    if (prevResponding.current && !responding && sendingId !== null) {
      const accepted = turnAccepted(baselineDepthRef.current, draftDepth);
      if (accepted) {
        setStack((prev) => applyTurnResult(prev, sendingId, { accepted: true }));
        const next = queueRef.current.shift();
        if (next) {
          baselineDepthRef.current = draftDepth;
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
  }, [responding, draftDepth, sendingId, lastAssistantText, onSend, cueNumber]);

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
    if (isGroupLocked(group, reserve, cueNumber)) return; // REQ-090 — 잠긴 그룹은 선택되지 않는다.
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
      before: section.fade_seconds !== undefined ? `${section.fade_seconds}초` : "—",
    });
  }

  function applyTrans(value: "SNAP" | "XFADE" | "FADE") {
    setTransValue(value);
    upsertChange({ field: "trans", value, before: section.trans ?? "—" });
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
    baselineDepthRef.current = draftDepth;
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
      setMovementName(entry.name);
      upsertChange({ field: "movement", value: entry.name, before: section.movement ?? "—" });
      return;
    }
    if (field === "effect") {
      setEffectName(entry.name);
      upsertChange({ field: "effect", value: entry.name, before: section.effect ?? "—" });
      return;
    }
    if (field === "palette_primary") {
      if (selectedGroups.length !== 1 || !COLOR_CAPABLE_GROUPS.has(selectedGroups[0])) return;
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

  const colorButtonDisabled =
    selectedGroups.length !== 1 || !COLOR_CAPABLE_GROUPS.has(selectedGroups[0]);

  return {
    cueNumber,
    statusLabel: stack.length === 0 ? "바뀐 항목 없음" : `바꾼 것 ${stack.length} — 코파일럿 확인 대기`,
    groups,
    selectedGroups,
    isGroupLocked: (group) => isGroupLocked(group, reserve, cueNumber),
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
    positionLabel: movementName ?? section.movement ?? "—",
    colorLabel: colorName ?? beforeColorLabel(),
    colorButtonDisabled,
    dimLabel: dimName ?? "—",
    effectLabel: effectName ?? section.effect ?? "—",
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
        </section>

        <section className="plan-cue-generator-console-values" aria-label="콘솔 반영 값">
          <div className="plan-cue-generator-row">
            <span>포지션</span>
            <span>{vm.positionLabel}</span>
            <button type="button" onClick={() => vm.onOpenPopup("movement", POOL_POSITION)}>
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
