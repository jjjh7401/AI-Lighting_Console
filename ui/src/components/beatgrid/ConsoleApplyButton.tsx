// 큐 편집 칸 머리의 「⇪ 콘솔에 반영」 — 예전에는 상단 바에 있던 버튼이다.
// 동작은 그대로다: 콜백이 없으면 비활성이고 그 사실을 title 로 말하며, 대기 수 배지
// (숫자 → 배지, null → 「—」, undefined → 없음)와 진행 문구(승인 대기 중이면 눌러서 승인
// 카드로)가 따라붙고, 반영 흐름의 다음 단계가 「반영」이면 강조 테두리를 두른다.
// 상단 바의 `.lbl-full`/`.lbl-short` 짝은 `.beat-grid-topbar` 안에서만 규칙이 있어 여기서는
// 쓰지 않고 풀네임 글자만 그린다.
import { ApplyProgressNote, badgeTitle, titleFor } from "../BeatGridTopBar";

export const CONSOLE_APPLY_LABEL = "⇪ 콘솔에 반영";

export interface ConsoleApplyButtonProps {
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
  /** 반영 흐름의 다음 단계가 「반영」이면 참 — 버튼에 강조 클래스(`is-next`)를 붙인다. */
  isNext?: boolean;
}

export function ConsoleApplyButton({
  onApply,
  pendingApplyCount,
  note = null,
  applyProgress,
  onApplyProgressClick,
  isNext = false,
}: ConsoleApplyButtonProps) {
  const title = titleFor(CONSOLE_APPLY_LABEL, !!onApply);
  return (
    <div className="beat-grid-console-apply">
      <button
        type="button"
        className={isNext ? "tbtn is-next" : "tbtn"}
        title={pendingApplyCount === undefined ? badgeTitle(title, note) : title}
        disabled={!onApply}
        onClick={() => onApply?.()}
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
      {applyProgress && <ApplyProgressNote text={applyProgress} onClick={onApplyProgressClick} />}
    </div>
  );
}
