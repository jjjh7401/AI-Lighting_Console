// 박자 격자 — 큐 편집 칸의 새 부품들(SPEC-LDBEAT-001 M9 step 3·4, 카드
// t561, REQ-LDBEAT-020(c)·021(a)(b)). 정본: design/ldbeat-runbook-ui-
// proposal-20261008.html `drawClipEd` — 머리(줄·Cue·마디·초·타임코드) →
// 밝기 → 위치 → 색 → 움직임 → 옆빛 L·R → 콘솔 명령. `BeatGrid.tsx`는
// 이 부품들을 마운트만 한다.
import { useEffect, useRef, useState, type ReactNode } from "react";

import type { BeatGridAppMovement, BeatGridCue, BeatGridMovementVocabulary, BeatGridTrack } from "../protocol";
import type { LRSplitToggleControl } from "./beatgrid/lrSplit";
import "./beatGridPanels.css";

/** 편집 칸이 초점을 둘 수 있는 항목(「이 마디 한눈에」 표 클릭 등에서 온다,
 * REQ-LDBEAT-021(a)). 값은 편집 칸 행의 `data-field` 와 짝지어진다. */
export type BeatGridFocusField = "밝기" | "위치" | "색" | "움직임" | "옆빛";

/** REQ-LDBEAT-010/AC-LDBEAT-004 — 「⚠ 실기 미확인」 배지 글자(타임라인 막대와
 * 「움직임」 행이 같이 쓴다). */
export const UNVERIFIED_SHAPE_BADGE = "⚠ 실기 미확인";

/** 카드 t579 — 배지 title: 무엇이 미확인인지와, 곡 기본값으로 넣지 않는다는 규칙. */
export function unverifiedShapeTitle(terms: readonly string[]): string {
  return `실기 미확인 — ${terms.join("·")} (M1 프로브 확인 전 · 곡 기본값으로 넣지 않음)`;
}

const FOCUS_FIELD_ROWS: Record<BeatGridFocusField, readonly string[]> = {
  밝기: ["밝기"],
  위치: ["위치 프리셋"],
  색: ["색 프리셋"],
  움직임: ["움직임", "효과 프리셋"],
  옆빛: ["옆빛 L·R"],
};

/** 초점 항목 → 편집 칸 행 이름(`data-field`) 후보. */
export function focusFieldRowNames(field: BeatGridFocusField): readonly string[] {
  return FOCUS_FIELD_ROWS[field];
}

/** 큐 편집 화면을 감싸 `focusField` 가 가리키는 행에 노란 테두리를 두고
 * 그 행으로 스크롤한다(시안 `FOCUS` — `el.focus(); outline 2px #ffd84d`).
 * 초점은 `focusField` 나 `focusKey`(지금 고른 칸)가 바뀔 때만 옮긴다 —
 * 다시 그릴 때마다 옮기면 입력 중인 칸에서 커서가 빠져나간다. */
export function BeatGridCueFocus({
  focusField,
  focusKey,
  children,
}: {
  focusField: BeatGridFocusField | null;
  focusKey?: string;
  children: ReactNode;
}) {
  const ref = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    const root = ref.current;
    if (!root) return;
    root.querySelectorAll(".is-focused").forEach((el) => el.classList.remove("is-focused"));
    if (!focusField) return;
    for (const name of focusFieldRowNames(focusField)) {
      const row = root.querySelector<HTMLElement>(`[data-field="${name}"]`);
      if (!row) continue;
      row.classList.add("is-focused");
      row.scrollIntoView?.({ block: "nearest" });
      row.querySelector<HTMLElement>("select, input, button, [tabindex]")?.focus();
      break;
    }
  }, [focusField, focusKey]);
  return (
    <div className="beat-grid-cue-view" ref={ref} data-focus-field={focusField ?? undefined}>
      {children}
    </div>
  );
}

/** 머리 둘째 줄 — Cue 번호·마디 범위·길이·초·곡 시각(시안 `drawClipEd`
 * 머리의 `fx` 줄). 초는 곡 BPM이 있을 때만 쓴다. */
export function BeatGridCueHeadMeta({
  track,
  cue,
  endBar,
  secondsPerBar,
  barZeroStartSeconds = null,
  confirmedFixtureCount,
  confirmedFixtureRange = null,
}: {
  track: BeatGridTrack;
  cue: BeatGridCue;
  endBar: number;
  secondsPerBar: number | null | undefined;
  /** 0마디가 시작하는 곡 시각(초) — 「타임코드 X초」가 콘솔 큐 시각과 같게(3차 전체 실행 G-19). */
  barZeroStartSeconds?: number | null;
  confirmedFixtureCount: number;
  /** 카드 t586 — 소속이 확인된 장비 번호 범위(예: 「201~202」, 시안 머리
   * `Group 10 'WASH-ALL' · 401~410…`). 모르면 `null` — 범위를 빼고 쓴다. */
  confirmedFixtureRange?: string | null;
}) {
  const cueNo = track.cues.indexOf(cue) + 1;
  const lengthBars = endBar - cue.bar;
  const hasTiming = secondsPerBar !== null && secondsPerBar !== undefined;
  // 콘솔 시퀀스 번호(서버 PR #742)는 배정된 줄에만 있다 — 없으면 「Seq」 자체를 빼고, 지어내지 않는다.
  const seqText = typeof track.sequence_number === "number" ? `Seq ${track.sequence_number} · ` : "";
  return (
    <div className="beat-grid-cue-head-meta">
      {/* 정보 줄(시안 `r.fix`): 그룹·장비 범위·대수·기종 — 서버 `sub_info.text` 가 있으면 그것, 없으면 확인된 것만 쓴 예전 문구. */}
      {track.sub_info?.text ||
        `${confirmedFixtureCount > 0 ? `장비 ${confirmedFixtureRange ? `${confirmedFixtureRange} · ` : ""}${confirmedFixtureCount}대(소속 확인)` : "장비 소속 미확인"} · ${track.group_no_confirmed && track.group_no !== null ? `그룹 ${track.group_no}` : "그룹 번호 미확인"}`}
      <br />
      {seqText}Cue {cueNo} · {cue.bar}~{endBar - 1}마디 · {lengthBars}마디
      {hasTiming
        ? ` ≈ ${(lengthBars * secondsPerBar).toFixed(1)}초 · 타임코드 ${Math.max(0, (barZeroStartSeconds ?? 0) + cue.bar * secondsPerBar).toFixed(2)}초`
        : ""}
    </div>
  );
}

/** 카드 t584 — 고르기 목록의 축 선택지(서버 어휘 `axes`의 하나 또는 둘 다). */
function axesOptions(axes: readonly string[]): { key: string; axes: string[] }[] {
  const single = axes.map((axis) => ({ key: axis, axes: [axis] }));
  return axes.length > 1 ? [...single, { key: axes.join("+"), axes: [...axes] }] : single;
}

const PERIOD_UNIT_LABEL: Record<string, string> = { beat: "박", bar: "마디" };

/** 카드 t584 — 「움직임」 고르기 초안(편집을 열 때 지금 칸 값으로 채운다). */
export interface MovementDraft {
  shape: string;
  axesKey: string;
  periodUnit: string;
  periodValue: string;
  phaseSpread: boolean;
}

export function movementDraftFrom(current: BeatGridAppMovement | null): MovementDraft {
  return {
    shape: current?.shape ?? "",
    axesKey: current?.axes.length ? current.axes.join("+") : "",
    periodUnit: current?.period_unit ?? "",
    periodValue: current?.period_value != null ? String(current.period_value) : "",
    phaseSpread: current?.phase_spread === true,
  };
}

/** 초안 → 서버 `apply_beat_grid_edit`의 ``app_movement`` 값. 모양 「없음」이면 `null`
 * (움직임 지우기). 고를 것이 빠졌으면 `undefined`(적용 버튼을 막는다) — 축 없는
 * 모양, 단위만 있고 수가 없는(또는 1 미만·정수 아닌) 주기. 초 단위는 없다(음악
 * 단위만, REQ-LDBEAT-006(vi-4)). */
export function movementChangesFromDraft(draft: MovementDraft): BeatGridAppMovement | null | undefined {
  if (!draft.shape) return null;
  if (!draft.axesKey) return undefined;
  let periodValue: number | null = null;
  if (draft.periodUnit) {
    const parsed = Number(draft.periodValue);
    if (!Number.isInteger(parsed) || parsed < 1) return undefined;
    periodValue = parsed;
  }
  return {
    shape: draft.shape as BeatGridAppMovement["shape"],
    axes: draft.axesKey.split("+") as BeatGridAppMovement["axes"],
    period_unit: (draft.periodUnit || null) as BeatGridAppMovement["period_unit"],
    period_value: periodValue,
    phase_spread: draft.phaseSpread ? true : null,
  };
}

/** 카드 t584 — 「움직임」 고르기 칸. 모양·축·주기 이름은 서버 어휘에서만 온다.
 * 미확인 모양은 목록에 「⚠」를 달고(시안 `opts()`의 `${P[i].u?" ⚠":""}` 그대로),
 * 초안이 미확인 모양을 **먼저 고르는 일은 없다** — 지금 칸 값이나 「없음」에서
 * 출발하고, 사람이 직접 골라야 들어간다(REQ-LDBEAT-010). 저장은 `onApply` 하나
 * (= 서버 `apply_beat_grid_edit`). */
export function BeatGridMovementPicker({
  current,
  vocabulary,
  onApply,
  onCancel,
}: {
  current: BeatGridAppMovement | null;
  vocabulary: BeatGridMovementVocabulary;
  onApply: (movement: BeatGridAppMovement | null) => void;
  onCancel: () => void;
}) {
  const [draft, setDraft] = useState<MovementDraft>(() => movementDraftFrom(current));
  const set = (patch: Partial<MovementDraft>) => setDraft((prev) => ({ ...prev, ...patch }));
  const changes = movementChangesFromDraft(draft);
  const chosenShape = vocabulary.shapes.find((shape) => shape.name === draft.shape);
  const unverifiedChoice = [
    ...(chosenShape?.unverified ? [chosenShape.name] : []),
    ...(draft.shape && draft.phaseSpread && vocabulary.phase_spread_unverified ? ["위상 펼침"] : []),
  ];
  return (
    <span className="beat-grid-cue-field-edit">
      <select aria-label="움직임 모양" value={draft.shape} onChange={(event) => set({ shape: event.target.value })}>
        <option value="">— 없음 —</option>
        {vocabulary.shapes.map((shape) => (
          <option key={shape.name} value={shape.name}>
            {shape.name}
            {shape.unverified ? " ⚠" : ""}
          </option>
        ))}
      </select>
      {draft.shape && (
        <>
          <select aria-label="움직임 축" value={draft.axesKey} onChange={(event) => set({ axesKey: event.target.value })}>
            <option value="">축 고르기</option>
            {axesOptions(vocabulary.axes).map((option) => (
              <option key={option.key} value={option.key}>
                {option.key}
              </option>
            ))}
          </select>
          <select
            aria-label="움직임 주기 단위"
            value={draft.periodUnit}
            onChange={(event) => set({ periodUnit: event.target.value })}
          >
            <option value="">주기 미정</option>
            {vocabulary.period_units.map((unit) => (
              <option key={unit} value={unit}>
                {PERIOD_UNIT_LABEL[unit] ?? unit}
              </option>
            ))}
          </select>
          {draft.periodUnit && (
            <input
              aria-label="움직임 주기 수"
              type="number"
              min={1}
              step={1}
              value={draft.periodValue}
              onChange={(event) => set({ periodValue: event.target.value })}
            />
          )}
          <label>
            <input
              type="checkbox"
              checked={draft.phaseSpread}
              onChange={(event) => set({ phaseSpread: event.target.checked })}
            />
            위상 펼침{vocabulary.phase_spread_unverified ? " ⚠" : ""}
          </label>
        </>
      )}
      <button type="button" disabled={changes === undefined} onClick={() => changes !== undefined && onApply(changes)}>
        적용
      </button>
      {/* 카드 t588 — 고르기가 늘 열려 있어 「닫기」가 아니라 지금 값으로 「되돌리기」. */}
      <button type="button" onClick={onCancel}>
        되돌리기
      </button>
      {unverifiedChoice.length > 0 && (
        <p className="beat-grid-cue-field-note u">
          {UNVERIFIED_SHAPE_BADGE} — {unverifiedChoice.join("·")}: 직접 고른 칸에만 들어가요. 곡 기본값으로 쓰지 않고,
          콘솔 송신은 M1 확인 뒤에만 돼요.
        </p>
      )}
    </span>
  );
}

/** REQ-LDBEAT-021(b) 「움직임」 전용 행 — 앱 2단계 무빙(REQ-LDBEAT-006(vi)).
 * 값 표시는 기존 `formatAppMovementField` 결과를 그대로 받는다. 카드 t579
 * (REQ-LDBEAT-010) — `unverifiedTerms`가 있으면(서버가 M1 표로 가른 미확인
 * 칸) 타임라인 막대와 같은 「⚠ 실기 미확인」 배지를 값 옆에 단다. 카드 t584 —
 * `edit`를 넘기면 다른 행과 같은 「값 ✎ 누르기 → 그 자리 고르기 → 적용」. */
export function BeatGridMovementRow({
  value,
  isUnset,
  unverifiedTerms = null,
  edit = null,
}: {
  value: string;
  isUnset: boolean;
  unverifiedTerms?: readonly string[] | null;
  edit?: {
    current: BeatGridAppMovement | null;
    vocabulary: BeatGridMovementVocabulary;
    editing: boolean;
    onOpen: () => void;
    onApply: (movement: BeatGridAppMovement | null) => void;
    onCancel: () => void;
  } | null;
}) {
  return (
    <div className="beat-grid-cue-field" data-field="움직임">
      <span className="beat-grid-cue-field-label">움직임</span>
      {edit?.editing ? (
        <BeatGridMovementPicker
          current={edit.current}
          vocabulary={edit.vocabulary}
          onApply={edit.onApply}
          onCancel={edit.onCancel}
        />
      ) : (
        <span
          className={`beat-grid-cue-field-value${isUnset ? " is-unset" : ""}${edit ? " is-editable" : ""}`}
          onClick={edit ? edit.onOpen : undefined}
        >
          {value}
          {unverifiedTerms && unverifiedTerms.length > 0 && (
            <span className="beat-grid-shape-warn" title={unverifiedShapeTitle(unverifiedTerms)}>
              {UNVERIFIED_SHAPE_BADGE}
            </span>
          )}
          {edit && " ✎"}
        </span>
      )}
    </div>
  );
}

/** REQ-LDBEAT-021(b) 「옆빛 L·R」 행 — 옆빛(side) 줄에서만. 「이 구간 왼쪽·오른쪽
 * 따로」는 펼침 줄과 같은 L·R 토글이다(REQ-LDBEAT-019(c)). `lrSplit` 이 `null` 이면
 * (좌우에 나눌 장비가 없거나 구간이 없으면) 버튼은 비활성이고, 있으면 누를 수 있다. */
export function BeatGridSideRow({
  lrSplit = null,
}: {
  lrSplit?: LRSplitToggleControl | null;
} = {}) {
  return (
    <div className="beat-grid-cue-field" data-field="옆빛 L·R">
      <span className="beat-grid-cue-field-label">옆빛 L·R</span>
      <span className="beat-grid-cue-field-value">
        {lrSplit?.isSplit ? "따로(왼쪽·오른쪽 갈라짐)" : "같이(갈라지지 않음)"}{" "}
        {lrSplit ? (
          <button
            type="button"
            className="beat-grid-tg"
            onClick={(event) => {
              event.stopPropagation();
              lrSplit.onToggle();
            }}
          >
            {lrSplit.isSplit ? "L·R 다시 합치기" : "이 구간 왼쪽·오른쪽 따로"}
          </button>
        ) : (
          <button
            type="button"
            className="beat-grid-tg"
            disabled
            title="이 칸에서는 좌우로 나눌 수 없습니다(좌우에 나눌 장비가 없거나 구간이 없습니다)"
          >
            이 구간 왼쪽·오른쪽 따로
          </button>
        )}
      </span>
    </div>
  );
}

/** REQ-LDBEAT-020(c) — 편집 칸 맨 아래 「콘솔 명령」. 켜면 노란색, 지금 보는
 * 화면(큐 편집/전환)에 맞는 명령 미리보기를 보여 준다. 아무것도 보내지
 * 않는다. */
export function BeatGridConsoleCommand({ lines }: { lines: readonly string[] }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="beat-grid-cmd-section">
      <button
        type="button"
        className={`beat-grid-tg${open ? " is-on" : ""}`}
        aria-pressed={open}
        onClick={() => setOpen((v) => !v)}
      >
        콘솔 명령
      </button>
      {open && (
        <pre className="beat-grid-cmdbox" aria-label="콘솔 명령 미리보기">
          {lines.join("\n")}
          {"\n"}(미리보기 — 송신은 「⇪ 콘솔에 반영」)
        </pre>
      )}
    </div>
  );
}
