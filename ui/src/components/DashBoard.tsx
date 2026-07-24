// Left dashboard pane — M3 layout skeleton (SPEC-COPILOT-DASHUI-001, plan.md
// §B M3, design.md §2 IA / §6 layout). Presentation-only: header + collapse
// affordance + an empty/placeholder body region. M4 mounts PoolSection /
// PoolTile inside the body; M5 wires the dash_catalog_request/response
// through useCopilotSocket.ts (both out of scope here).
//
// No internal hooks by design: this project has no DOM/jsdom test harness
// (see protocol.ts's own header — "Pure functions only... unit-testable
// without a DOM"). A hook-free component can be called directly as a plain
// function in tests, returning an inspectable React element tree with no
// renderer — see DashBoard.test.tsx and the sibling AppShell in App.tsx.
import { type DashState } from "../protocol";

export interface DashBoardProps {
  dash: DashState;
  onToggleCollapse: () => void;
}

export function DashBoard({ dash, onToggleCollapse }: DashBoardProps) {
  const hasSections = dash.sections.length > 0;
  return (
    <aside className="dashboard" aria-label="리그 대시보드">
      <header className="dashboard-header">
        <span className="dashboard-title">리그 요약</span>
        <button
          className="dashboard-collapse"
          onClick={onToggleCollapse}
          aria-label="대시보드 접기"
        >
          ◂ 접기
        </button>
      </header>
      <div className="dashboard-body">
        {hasSections ? (
          // M4 mounts PoolSection/PoolTile per section here.
          <div className="dashboard-sections" />
        ) : (
          <div className="dashboard-empty">로딩 중…</div>
        )}
      </div>
    </aside>
  );
}
