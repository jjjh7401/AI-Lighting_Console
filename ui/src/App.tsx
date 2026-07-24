// MA3 copilot Korean chat UI (M5 — REQ-MVP-020/021/022 UI halves;
// M7 — deploy review card, REQ-MVP-019/027).
// M3 (SPEC-COPILOT-DASHUI-001) — split-pane layout: left DashBoard (layout
// skeleton only; M4 renders pools, M5 wires the catalog request/response) +
// right chat (unchanged markup). Collapsed is the default so the pre-M3
// chat-first experience reproduces exactly until the operator opts into the
// split view (plan.md §E R5 mitigation — "접기 기본 제공").
import { type ReactNode, useEffect, useRef, useState } from "react";

import { ApprovalCard } from "./components/ApprovalCard";
import { ChatView } from "./components/ChatView";
import { DashBoard } from "./components/DashBoard";
import { LockToggle } from "./components/LockToggle";
import { OnboardingBanner } from "./components/OnboardingBanner";
import { ReviewCard } from "./components/ReviewCard";
import { SettingsPanel } from "./components/SettingsPanel";
import { StatusBanner } from "./components/StatusBanner";
import { panelItemId, type DashItem, type DashState, type PanelTargetKind } from "./protocol";
import { useCopilotSocket } from "./useCopilotSocket";

/**
 * The dash section names that carry live-fire semantics (M5, design.md §4)
 * mapped to the wire `target_kind` `panel_execute`/`panel_stop` expect. Every
 * other dash section (groups/preset_pools/plugins/fixtures) is structurally
 * read-only — `null` means "this section never presses".
 */
export function targetKindForDashSection(sectionName: string): PanelTargetKind | null {
  if (sectionName === "executors") return "executor";
  if (sectionName === "macros") return "macro";
  return null;
}

/**
 * The split-pane shell — deliberately hook-free so App.test.tsx can call it
 * directly (this project has no DOM/jsdom test harness; see protocol.ts's
 * own header). `dashCollapsed` decides whether `DashBoard` mounts at all: when
 * collapsed, the shell's own children ARE the entire output — exactly today's
 * pre-M3 single-column tree (AC-DASHUI-009). The shell never inspects or
 * rewrites `children`; it only wraps them.
 */
export function AppShell({
  dashCollapsed,
  dash,
  onToggleDash,
  onRefresh,
  isItemRunning,
  onItemPress,
  children,
}: {
  dashCollapsed: boolean;
  dash: DashState;
  onToggleDash: () => void;
  /** M5 — manual [새로고침] dispatch; see DashBoard.tsx. */
  onRefresh?: () => void;
  /** M5 — per-item running lookup; see DashBoard.tsx. */
  isItemRunning?: (sectionName: string, item: DashItem) => boolean;
  /** M5 — fires panel_execute/panel_stop; see DashBoard.tsx. */
  onItemPress?: (sectionName: string, item: DashItem) => void;
  children: ReactNode;
}) {
  return (
    <div className={`app-shell ${dashCollapsed ? "dash-collapsed" : "dash-split"}`}>
      {!dashCollapsed && (
        <DashBoard
          dash={dash}
          onToggleCollapse={onToggleDash}
          onRefresh={onRefresh}
          isItemRunning={isItemRunning}
          onItemPress={onItemPress}
        />
      )}
      {children}
    </div>
  );
}

export default function App() {
  const {
    state,
    connected,
    sendChat,
    sendDecision,
    sendReviewDecision,
    sendLock,
    sendPanelExecute,
    sendPanelStop,
    sendDashRefresh,
  } = useCopilotSocket();
  const [draft, setDraft] = useState("");
  const [settingsOpen, setSettingsOpen] = useState(false);
  // Bumped when the settings panel closes so the onboarding banner re-checks
  // whether a key was just added (and hides itself if so).
  const [settingsRefresh, setSettingsRefresh] = useState(0);
  // Session-volatile (design.md §6 / D5 — no client persistence); collapsed
  // by default so today's chat-first experience is unchanged until the
  // operator opts into the split view.
  const [dashCollapsed, setDashCollapsed] = useState(true);
  const bottomRef = useRef<HTMLDivElement>(null);

  const closeSettings = () => {
    setSettingsOpen(false);
    setSettingsRefresh((count) => count + 1);
  };

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [state.entries.length, state.pendingApprovals.length, state.pendingReviews.length]);

  const submit = () => {
    const text = draft.trim();
    if (!text) return;
    sendChat(text);
    setDraft("");
  };

  // M5 (design.md §4, REQ-DASHUI-017): the dash pool grid's fireable sections
  // (executors/macros) reuse the SAME panel_execute/panel_stop → gate.screen()
  // path the SHOWUI-inherited panel protocol already exposes — `state.panel`
  // (running/busy) already tracks it, this just cross-references it by
  // `panelItemId`. Non-fireable sections (groups/preset_pools/plugins) never
  // reach these — DashBoard's own `dashItemIsPressable` keeps them read-only.
  const isDashItemRunning = (sectionName: string, item: DashItem): boolean => {
    const targetKind = targetKindForDashSection(sectionName);
    if (targetKind === null) return false;
    return state.panel.running[panelItemId(targetKind, item.no)]?.running ?? false;
  };
  const pressDashItem = (sectionName: string, item: DashItem) => {
    const targetKind = targetKindForDashSection(sectionName);
    if (targetKind === null) return;
    if (isDashItemRunning(sectionName, item)) {
      sendPanelStop(targetKind, item.no);
    } else {
      sendPanelExecute(targetKind, item.no);
    }
  };

  return (
    <AppShell
      dashCollapsed={dashCollapsed}
      dash={state.dash}
      onToggleDash={() => setDashCollapsed((collapsed) => !collapsed)}
      onRefresh={sendDashRefresh}
      isItemRunning={isDashItemRunning}
      onItemPress={pressDashItem}
    >
      <div className="app">
        <header className="header">
          <h1>MA3 코파일럿</h1>
          <div className="header-actions">
            <button
              className="dash-toggle"
              onClick={() => setDashCollapsed((collapsed) => !collapsed)}
              aria-label={dashCollapsed ? "대시보드 펼치기" : "대시보드 접기"}
            >
              {dashCollapsed ? "▸ 대시보드" : "◂ 대시보드"}
            </button>
            <LockToggle status={state.status} onToggle={sendLock} />
            <button
              className="settings-open"
              onClick={() => setSettingsOpen(true)}
              aria-label="설정 열기"
            >
              ⚙ 설정
            </button>
          </div>
        </header>
        <StatusBanner status={state.status} connected={connected} />
        <OnboardingBanner
          onOpenSettings={() => setSettingsOpen(true)}
          refreshSignal={settingsRefresh}
        />
        {settingsOpen && <SettingsPanel onClose={closeSettings} />}
        <main className="main">
          <ChatView entries={state.entries} />
          {state.pendingApprovals.map((approval) => (
            <ApprovalCard
              key={approval.request_id}
              approval={approval}
              onDecision={sendDecision}
            />
          ))}
          {state.pendingReviews.map((review) => (
            <ReviewCard key={review.request_id} review={review} onDecision={sendReviewDecision} />
          ))}
          <div ref={bottomRef} />
        </main>
        <footer className="composer">
          <input
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.nativeEvent.isComposing) submit();
            }}
            placeholder="한국어로 지시를 입력하세요…"
            disabled={!connected}
          />
          <button onClick={submit} disabled={!connected || !draft.trim()}>
            전송
          </button>
        </footer>
      </div>
    </AppShell>
  );
}
