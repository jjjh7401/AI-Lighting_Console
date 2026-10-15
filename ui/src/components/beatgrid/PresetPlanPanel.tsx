// 「필요한 프리셋 만들기」 계획표 패널. 승인 카드를 가리지 않도록 모달이 아니라 격자 위 패널이다.
import { PRESET_PLAN_KIND_LABEL, type PresetPlan } from "./presetPlan";

/** 프리셋 서랍 머리의 「프리셋 계획 만들기」 — `beat_grid_apply` mode: preset_plan 을 보낸다. */
export function PresetPlanButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      className="tbtn"
      title="필요한 프리셋 만들기 — 격자 칸이 쓰는 값으로 만들 프리셋 계획표를 보이고, 승인 카드를 띄운다"
      onClick={onClick}
    >
      프리셋 계획 만들기
    </button>
  );
}

export const SUPERVISOR_FIX_MARK = "감독이 고칠 값";

export function PresetPlanPanel({ plan, onClose }: { plan: PresetPlan; onClose?: () => void }) {
  return (
    <section className="preset-plan-panel" role="region" aria-label="연출 프리셋 계획">
      <header className="preset-plan-head">
        <strong>연출 프리셋 계획</strong>
        <span className="preset-plan-note">승인 카드에서 「실행」을 눌러야 저장된다</span>
        {onClose && (
          <button type="button" className="tbtn" onClick={onClose}>
            닫기
          </button>
        )}
      </header>
      <table className="preset-plan-table">
        <thead>
          <tr>
            <th>종류</th>
            <th>번호</th>
            <th>이름</th>
            <th>값</th>
            <th>칸 수</th>
            <th>상태</th>
          </tr>
        </thead>
        <tbody>
          {plan.rows.map((row) => (
            <tr key={`${row.name}|${row.value}`} data-kind={row.kind}>
              <td>{PRESET_PLAN_KIND_LABEL[row.kind]}</td>
              <td>{row.slot}</td>
              <td>{row.name}</td>
              <td>
                {row.value}
                {row.needsSupervisor && (
                  <span className="preset-plan-mark" title="앱이 기본값·잠정값을 썼다. 아래 목록을 확인한다">
                    {SUPERVISOR_FIX_MARK}
                  </span>
                )}
              </td>
              <td>{row.cellCount}</td>
              <td>{row.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {plan.excluded.map((section) => (
        <div key={section.title} className="preset-plan-excluded">
          <strong>제외 · {section.title}</strong>
          <ul>
            {section.items.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      ))}
      {plan.supervisorFixes.length > 0 && (
        <div className="preset-plan-fixes">
          <strong>{SUPERVISOR_FIX_MARK}</strong>
          <ul>
            {plan.supervisorFixes.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
