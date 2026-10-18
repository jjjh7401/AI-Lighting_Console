// 고른 칸 일괄 바꾸기 줄 (SPEC-LDRHYTHM-001, 카드 WT-cell-apply).
//
// 타임라인에서 칸을 여럿 골랐을 때만 큐 편집 칸 위에 보인다: 「N칸 고름」과 선택 해제, 디머(프리셋 또는 밝기 값)와
// 색 프리셋 고르기, 「적용」. 「적용」은 서버에 `beat_grid_edit` 를 `cells` 주소로 **한 번** 보낸다(칸마다 보내면 서버
// 바쁨 가드가 둘째부터 거절한다). 고르기 목록과 `changes` 모양은 한 칸 편집과 같은 것을 BeatGrid.tsx 가 넘겨 준다 —
// 이 부품은 지어내지 않고, 무엇을 골랐는지(`BulkChoice`)만 올린다. 프리셋 번호 목록은 이미 만든 `<option>` 들로 받는다.
import { useState, type ReactNode } from "react";

import "./cellSelection.css";

/** 한 번의 「적용」이 담는 선택. 디머는 값(%) · 프리셋 · 효과 중 하나이고, 색은 프리셋 번호다. */
export interface BulkChoice {
  dimmer:
    | { kind: "value"; percent: number }
    | { kind: "preset"; no: string }
    | { kind: "effect"; no: string }
    | null;
  color: { no: string } | null;
}

export interface BulkDrafts {
  /** 디머 프리셋·효과 번호(빈 글자 = 안 골랐다). */
  dimmerNo: string;
  /** 밝기 값(%) 글자(빈 글자 = 안 골랐다). */
  valueText: string;
  /** 색 프리셋 번호(빈 글자 = 안 골랐다). */
  colorNo: string;
}

/** 초안 → 선택. 아무것도 안 골랐으면 `null`. 디머 번호가 `dimmerEffectNos` 에 있으면 효과, 아니면 프리셋이다
 * (한 칸 편집의 「디머 프리셋」 고르기와 같은 가름). 디머는 번호가 값(%)보다 앞선다(화면은 둘을 함께 두지 않는다). */
export function bulkChoiceOf(drafts: BulkDrafts, dimmerEffectNos: readonly string[]): BulkChoice | null {
  const percent = drafts.valueText.trim() === "" ? Number.NaN : Number(drafts.valueText);
  let dimmer: BulkChoice["dimmer"] = null;
  if (drafts.dimmerNo !== "") {
    dimmer = { kind: dimmerEffectNos.includes(drafts.dimmerNo) ? "effect" : "preset", no: drafts.dimmerNo };
  } else if (Number.isFinite(percent)) {
    dimmer = { kind: "value", percent };
  }
  const color = drafts.colorNo !== "" ? { no: drafts.colorNo } : null;
  return dimmer === null && color === null ? null : { dimmer, color };
}

/** 프리셋 번호를 바꾼 칸은 승인 대기가 되어 칸 단위 반영이 받지 않는다(서버가 거절) — 전체 반영으로 보낸다. */
export const BULK_PRESET_NUMBER_HINT =
  "프리셋 번호를 바꾼 칸은 칸 단위 반영이 거절해요 — 「전체 다시 반영」으로 보내 주세요.";
export const BULK_NOTHING_CHOSEN_HINT = "디머나 색을 먼저 고르세요";
/** 아래 큐 편집 칸의 「적용」은 예전처럼 보이는 한 칸에만 간다 — 이 줄과 헷갈리지 않게 말해 둔다. */
export const BULK_SCOPE_HINT = "이 줄의 「적용」은 고른 칸 전부에, 아래 편집 칸의 「적용」은 한 칸에만 가요.";

export interface CellSelectionBarProps {
  /** 고른 칸 수. */
  count: number;
  onClear: () => void;
  /** 「디머 프리셋」 고르기 목록(`<option>`·`<optgroup>`) — 한 칸 편집과 같은 목록. */
  dimmerOptions: ReactNode;
  /** 「색 프리셋」 고르기 목록 — 한 칸 편집과 같은 목록. */
  colorOptions: ReactNode;
  /** 디머 목록 가운데 「디머 효과」인 번호. */
  dimmerEffectNos: readonly string[];
  /** 「밝기 값(%)」 고르기 선택지. */
  valueChoices: readonly number[];
  /** 그 풀을 콘솔에서 아직 못 읽었으면 고르기를 끈다. */
  dimmerDisabled?: boolean;
  colorDisabled?: boolean;
  /** 프리셋 목록 상태 안내(받는 중·못 읽음 등). */
  poolNote?: string | null;
  /** 「적용」을 못 하는 이유(칸 수 초과 등). 있으면 「적용」은 꺼진다. */
  blockedReason?: string | null;
  /** 서버 `cells` 로 못 보내 뺀 칸 안내(0마디). */
  skippedNote?: string | null;
  /** 서버 거절 사유·바쁨 안내 — 방금 누른 「적용」의 답. */
  replyNote?: string | null;
  onApply: (choice: BulkChoice) => void;
}

export function CellSelectionBar({
  count,
  onClear,
  dimmerOptions,
  colorOptions,
  dimmerEffectNos,
  valueChoices,
  dimmerDisabled = false,
  colorDisabled = false,
  poolNote = null,
  blockedReason = null,
  skippedNote = null,
  replyNote = null,
  onApply,
}: CellSelectionBarProps) {
  const [drafts, setDrafts] = useState<BulkDrafts>({ dimmerNo: "", valueText: "", colorNo: "" });
  const choice = bulkChoiceOf(drafts, dimmerEffectNos);
  const disabledReason = blockedReason ?? (choice === null ? BULK_NOTHING_CHOSEN_HINT : null);
  return (
    <section className="beat-grid-cell-bar" aria-label="고른 칸 일괄 바꾸기">
      <div className="beat-grid-cell-bar-head">
        <b className="beat-grid-cell-bar-count">{count}칸 고름</b>
        <button type="button" className="beat-grid-cell-bar-clear" title="고른 칸을 모두 풉니다" onClick={onClear}>
          선택 해제
        </button>
      </div>
      <div className="beat-grid-cell-bar-row">
        <span className="beat-grid-cell-bar-label">디머</span>
        <select
          aria-label="일괄 디머 프리셋"
          value={drafts.dimmerNo}
          disabled={dimmerDisabled}
          onChange={(event) => setDrafts({ ...drafts, dimmerNo: event.target.value, valueText: "" })}
        >
          {dimmerOptions}
        </select>
        <select
          aria-label="일괄 밝기 값(%)"
          value={drafts.valueText}
          onChange={(event) => setDrafts({ ...drafts, valueText: event.target.value, dimmerNo: "" })}
        >
          <option value="" disabled>
            — 값 —
          </option>
          {valueChoices.map((choiceValue) => (
            <option key={choiceValue} value={String(choiceValue)}>
              {choiceValue}%
            </option>
          ))}
        </select>
      </div>
      <div className="beat-grid-cell-bar-row">
        <span className="beat-grid-cell-bar-label">색</span>
        <select
          aria-label="일괄 색 프리셋"
          value={drafts.colorNo}
          disabled={colorDisabled}
          onChange={(event) => setDrafts({ ...drafts, colorNo: event.target.value })}
        >
          {colorOptions}
        </select>
        <button
          type="button"
          className="beat-grid-cell-bar-apply"
          disabled={disabledReason !== null}
          title={disabledReason ?? `고른 ${count}칸에 한 번에 적용해요`}
          onClick={() => choice && onApply(choice)}
        >
          적용
        </button>
      </div>
      <p className="beat-grid-cell-bar-hint">{BULK_SCOPE_HINT}</p>
      <p className="beat-grid-cell-bar-hint">{BULK_PRESET_NUMBER_HINT}</p>
      {poolNote && <p className="beat-grid-cell-bar-hint">{poolNote}</p>}
      {skippedNote && <p className="beat-grid-cell-bar-hint">{skippedNote}</p>}
      {blockedReason && <p className="beat-grid-cell-bar-hint is-warn">{blockedReason}</p>}
      {replyNote && (
        <p className="beat-grid-cell-bar-hint is-warn" role="status">
          {replyNote}
        </p>
      )}
    </section>
  );
}
