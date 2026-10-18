// 큐 편집 칸 머리의 「⇪ 콘솔에 반영」 — 예전에는 상단 바에 있던 버튼이다.
// 동작은 그대로다: 콜백이 없으면 비활성이고 그 사실을 title 로 말하며, 대기 수 배지
// (숫자 → 배지, null → 「—」, undefined → 없음)와 진행 문구(승인 대기 중이면 눌러서 승인
// 카드로)가 따라붙고, 반영 흐름의 다음 단계가 「반영」이면 강조 테두리를 두른다.
// 상단 바의 `.lbl-full`/`.lbl-short` 짝은 `.beat-grid-topbar` 안에서만 규칙이 있어 여기서는
// 쓰지 않고 풀네임 글자만 그린다.
//
// 칸 단위 반영(`partial`)을 주면 이 버튼이 바뀐 칸만 보내는 칸 단위 반영이 되고, 곡 전체를 다시 보내는 길은
// 뒤따르는 작은 「전체 다시 반영」 버튼(`onApply`)이 맡는다. `partial` 이 없으면 예전 단일 버튼 그대로다.
import { ApplyProgressNote, badgeTitle, titleFor } from "../BeatGridTopBar";
import type { PartialApplyPlan } from "./cellApply";
import "./cellSelection.css";

export const CONSOLE_APPLY_LABEL = "⇪ 콘솔에 반영";
export const CONSOLE_APPLY_WHOLE_LABEL = "전체 다시 반영";
const CONSOLE_APPLY_WHOLE_TITLE = `${CONSOLE_APPLY_WHOLE_LABEL} — 곡 전체를 콘솔에 다시 반영해요`;

/** 칸 단위 반영 배선. `plan` 은 `partialApplyPlan` 의 판정(보낼 칸 또는 못 보내는 이유)이다. */
export interface ConsolePartialApply {
  plan: PartialApplyPlan;
  /** 판정이 `ready` 일 때만 불린다 — 서버로 보낼 `[줄 이름, 마디]` 목록을 넘긴다. */
  onApplyCells: (cells: [string, number][]) => void;
}

export interface ConsoleApplyButtonProps {
  /** 곡 전체 반영. `partial` 이 있으면 「전체 다시 반영」 버튼이 이것을 부른다. */
  onApply?: () => void;
  /** 콘솔에 아직 안 보낸 편집 수. `undefined`는 배선 전이라 배지를 생략하고,
   * `null`은 아직 반영 기록이 없다는 뜻이라 「—」를 보이며(0으로 지어내지
   * 않는다), 숫자는 그 개수다. */
  pendingApplyCount?: number | null;
  /** 격자 출처 안내(`BeatGridView.note`) — 배지 툴팁에 잇는다. 배지가 없는 배선 전 상태에서만 버튼 title 에 싣는다. */
  note?: string | null;
  /** 「⇪ 콘솔에 반영」 진행 문구 — 콘솔을 읽는 중·승인 카드를 기다리는 중. */
  applyProgress?: string | null;
  /** 진행 문구를 누르면 — 승인 대기 중일 때만 주어진다(전체화면 위 승인 카드로 옮긴다). */
  onApplyProgressClick?: () => void;
  /** 반영 흐름의 다음 단계가 「반영」이면 참 — 버튼에 강조 클래스(`is-next`)를 붙인다. 칸 단위 반영에서는
   * 흐름의 「반영」이 곡 전체 반영이라 「전체 다시 반영」 버튼이 받는다. */
  isNext?: boolean;
  /** 칸 단위 반영. 없으면 예전과 같은 단일 버튼이다. */
  partial?: ConsolePartialApply;
}

export function ConsoleApplyButton({
  onApply,
  pendingApplyCount,
  note = null,
  applyProgress,
  onApplyProgressClick,
  isNext = false,
  partial,
}: ConsoleApplyButtonProps) {
  const plan = partial?.plan;
  const title = plan
    ? plan.kind === "ready"
      ? `${CONSOLE_APPLY_LABEL} — ${plan.note}`
      : plan.reason
    : titleFor(CONSOLE_APPLY_LABEL, !!onApply);
  const disabled = plan ? plan.kind !== "ready" : !onApply;
  const onClick = () => {
    if (!partial) onApply?.();
    else if (partial.plan.kind === "ready") partial.onApplyCells(partial.plan.cells);
  };
  return (
    <div className="beat-grid-console-apply">
      <button
        type="button"
        className={isNext && !partial ? "tbtn is-next" : "tbtn"}
        title={pendingApplyCount === undefined ? badgeTitle(title, note) : title}
        disabled={disabled}
        onClick={onClick}
      >
        {CONSOLE_APPLY_LABEL}
        {typeof pendingApplyCount === "number" && (
          <span className="badge" title={badgeTitle(null, note)}>
            {pendingApplyCount}
          </span>
        )}
        {pendingApplyCount === null && (
          <span className="badge badge-dash" title={badgeTitle("반영 기록 없음 — 첫 반영 뒤에 숫자가 보인다", note)}>
            —
          </span>
        )}
      </button>
      {partial && (
        <button
          type="button"
          className={isNext ? "tbtn beat-grid-apply-whole is-next" : "tbtn beat-grid-apply-whole"}
          title={titleFor(CONSOLE_APPLY_WHOLE_TITLE, !!onApply)}
          disabled={!onApply}
          onClick={() => onApply?.()}
        >
          {CONSOLE_APPLY_WHOLE_LABEL}
        </button>
      )}
      {applyProgress && <ApplyProgressNote text={applyProgress} onClick={onApplyProgressClick} />}
      {plan && <small className="beat-grid-apply-scope">{plan.kind === "ready" ? plan.note : plan.reason}</small>}
    </div>
  );
}
