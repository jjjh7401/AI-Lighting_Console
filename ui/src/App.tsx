// MA3 copilot Korean chat UI (M5 — REQ-MVP-020/021/022 UI halves;
// M7 — deploy review card, REQ-MVP-019/027).
// M3 (SPEC-COPILOT-DASHUI-001) — split-pane layout. M6 live-feedback
// inversion (user direction, 2026-07-24): the CONSOLE INFO PANE is the
// primary, always-visible surface — the operator watches console state,
// picks targets, and fires at the moment of their choosing. Chat is the
// copilot SIDE column (right, fixed width) and is the collapsible half —
// collapsing it leaves a thin rail with a re-open affordance. The global
// header/status/settings live ABOVE the split so they stay reachable in
// both states.
import { type ReactNode, useEffect, useRef, useState } from "react";

import { ApprovalCard } from "./components/ApprovalCard";
import { ChatView } from "./components/ChatView";
import { DashBoard } from "./components/DashBoard";
import { LockToggle } from "./components/LockToggle";
import { OnboardingBanner } from "./components/OnboardingBanner";
import { ReviewCard } from "./components/ReviewCard";
import { SettingsPanel } from "./components/SettingsPanel";
import { StatusBanner } from "./components/StatusBanner";
import {
  clampPoolArea,
  POOL_AREA_DEFAULT,
  type PoolArea,
} from "./components/PoolSection";
import {
  panelItemId,
  type DashItem,
  type DashState,
  type PanelTargetKind,
  type StatusState,
} from "./protocol";
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
 * The number a press on this dash item may target, or null when it must not
 * fire. Executors fire ONLY the server-verified console number
 * (`meta.console_no`, AC-DASHUI-005) — the item's own `no` is the POOL SLOT
 * (live-measured on onPC 2.4.2: page 1 slot 1 is console "Executor 101"), so
 * targeting it would fire the wrong executor or nothing. An executor without
 * a verified console number never fires (fail-closed, EXECBODY AC-016).
 * Macros fire their own pool number unchanged.
 */
export function dashPressTargetNo(sectionName: string, item: DashItem): number | null {
  const targetKind = targetKindForDashSection(sectionName);
  if (targetKind === null) return null;
  if (targetKind === "executor") {
    const consoleNo = item.meta?.console_no;
    return typeof consoleNo === "number" ? consoleNo : null;
  }
  return item.no;
}

export interface ComposerViewState {
  inputDisabled: boolean;
  submitDisabled: boolean;
  placeholder: string;
  buttonLabel: string;
  helperText: string | null;
  canSubmit: boolean;
}

export function composerViewState({
  connected,
  status,
  draft,
}: {
  connected: boolean;
  status: StatusState | null;
  draft: string;
}): ComposerViewState {
  if (!connected) {
    return {
      inputDisabled: true,
      submitDisabled: true,
      placeholder: "서버 재연결 중입니다…",
      buttonLabel: "대기",
      helperText: "서버 연결이 끊겨 명령을 보낼 수 없습니다.",
      canSubmit: false,
    };
  }
  if (status === null) {
    return {
      inputDisabled: true,
      submitDisabled: true,
      placeholder: "상태 확인 중입니다…",
      buttonLabel: "대기",
      helperText: "서버 상태 확인 후 명령 입력이 열립니다.",
      canSubmit: false,
    };
  }
  if (status.executions_blocked) {
    return {
      inputDisabled: true,
      submitDisabled: true,
      placeholder: "콘솔 연결 후 명령을 입력하세요…",
      buttonLabel: "차단됨",
      helperText: "콘솔 연결이 필요합니다. 설정에서 onPC OSC와 responder를 확인하세요.",
      canSubmit: false,
    };
  }
  const hasDraft = draft.trim().length > 0;
  return {
    inputDisabled: false,
    submitDisabled: !hasDraft,
    placeholder: status.live_lock
      ? "라이브 잠금 중입니다 — 제안만 생성됩니다…"
      : "한국어로 지시를 입력하세요…",
    buttonLabel: "전송",
    helperText: status.live_lock
      ? "라이브 잠금 중입니다. 입력은 콘솔로 전송되지 않고 제안 카드로만 표시됩니다."
      : null,
    canSubmit: hasDraft,
  };
}

/**
 * The split-pane shell — deliberately hook-free so App.test.tsx can call it
 * directly (this project has no DOM/jsdom test harness; see protocol.ts's
 * own header). The console info pane (`DashBoard`) ALWAYS mounts — it is the
 * primary surface. `chatCollapsed` decides whether the chat column
 * (`children`) mounts: when collapsed, a thin rail with a re-open button
 * stands in for it. The shell never inspects or rewrites `children`; it only
 * wraps them.
 */
export function AppShell({
  chatCollapsed,
  dash,
  onToggleChat,
  onRefresh,
  isItemRunning,
  onItemPress,
  sectionTileSize,
  onSectionTileSizeChange,
  sectionArea,
  onSectionAreaResizeStart,
  children,
}: {
  chatCollapsed: boolean;
  dash: DashState;
  onToggleChat: () => void;
  /** M5 — manual [새로고침] dispatch; see DashBoard.tsx. */
  onRefresh?: () => void;
  /** M5 — per-item running lookup; see DashBoard.tsx. */
  isItemRunning?: (sectionName: string, item: DashItem) => boolean;
  /** M5 — fires panel_execute/panel_stop; see DashBoard.tsx. */
  onItemPress?: (sectionName: string, item: DashItem) => void;
  /** M6-UX v3 — square cells (−/+) + pool-window area corner drag. */
  sectionTileSize?: (sectionName: string) => number | undefined;
  onSectionTileSizeChange?: (sectionName: string, next: number) => void;
  sectionArea?: (sectionName: string) => PoolArea | undefined;
  onSectionAreaResizeStart?: (
    sectionName: string,
    event: { clientX: number; clientY: number },
  ) => void;
  children: ReactNode;
}) {
  return (
    <div className={`app-shell ${chatCollapsed ? "chat-collapsed" : "chat-split"}`}>
      <DashBoard
        dash={dash}
        onRefresh={onRefresh}
        isItemRunning={isItemRunning}
        onItemPress={onItemPress}
        sectionTileSize={sectionTileSize}
        onSectionTileSizeChange={onSectionTileSizeChange}
        sectionArea={sectionArea}
        onSectionAreaResizeStart={onSectionAreaResizeStart}
      />
      {chatCollapsed ? (
        <aside className="chat-rail">
          <button className="chat-rail-open" onClick={onToggleChat} aria-label="채팅 펼치기">
            ◂ 채팅
          </button>
        </aside>
      ) : (
        children
      )}
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
  // Session-volatile (design.md §6 / D5 — no client persistence). The chat
  // column starts OPEN alongside the always-visible console pane; the
  // operator may collapse it to give the console pane the full width.
  const [chatCollapsed, setChatCollapsed] = useState(false);
  // M6-UX v3 — per-section view preferences, session-volatile: the SQUARE
  // cell size (stepped by each section's −/+ header buttons) and the pool
  // WINDOW's on-screen area (dragged from its onPC-style bottom-right
  // corner). The drag session lives here (document-level move/up listeners)
  // because the pool components are hook-free by design.
  const [sectionTileSizes, setSectionTileSizes] = useState<Record<string, number>>({});
  const [sectionAreas, setSectionAreas] = useState<Record<string, PoolArea>>({});
  const startSectionAreaResize = (
    sectionName: string,
    start: { clientX: number; clientY: number },
  ) => {
    const base = sectionAreas[sectionName] ?? POOL_AREA_DEFAULT;
    const onMove = (move: MouseEvent) => {
      const next = clampPoolArea({
        width: base.width + (move.clientX - start.clientX),
        height: base.height + (move.clientY - start.clientY),
      });
      setSectionAreas((areas) => ({ ...areas, [sectionName]: next }));
    };
    const onUp = () => {
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
    };
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
  };
  const bottomRef = useRef<HTMLDivElement>(null);

  const closeSettings = () => {
    setSettingsOpen(false);
    setSettingsRefresh((count) => count + 1);
  };
  const composer = composerViewState({ connected, status: state.status, draft });

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [state.entries.length, state.pendingApprovals.length, state.pendingReviews.length]);

  const submit = () => {
    if (!composer.canSubmit) return;
    const text = draft.trim();
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
    const targetNo = dashPressTargetNo(sectionName, item);
    if (targetNo === null) return false;
    return state.panel.running[panelItemId(targetKind, targetNo)]?.running ?? false;
  };
  const pressDashItem = (sectionName: string, item: DashItem) => {
    const targetKind = targetKindForDashSection(sectionName);
    if (targetKind === null) return;
    const targetNo = dashPressTargetNo(sectionName, item);
    if (targetNo === null) return; // unresolved executor: never fire (fail-closed)
    if (isDashItemRunning(sectionName, item)) {
      sendPanelStop(targetKind, targetNo);
    } else {
      sendPanelExecute(targetKind, targetNo);
    }
  };

  return (
    <div className="app-frame">
      <header className="header">
        <h1>MA3 코파일럿</h1>
        <div className="header-actions">
          <button
            className="chat-toggle"
            onClick={() => setChatCollapsed((collapsed) => !collapsed)}
            aria-label={chatCollapsed ? "채팅 펼치기" : "채팅 접기"}
          >
            {chatCollapsed ? "◂ 채팅" : "▸ 채팅"}
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
      <AppShell
        chatCollapsed={chatCollapsed}
        dash={state.dash}
        onToggleChat={() => setChatCollapsed((collapsed) => !collapsed)}
        onRefresh={sendDashRefresh}
        isItemRunning={isDashItemRunning}
        onItemPress={pressDashItem}
        sectionTileSize={(sectionName) => sectionTileSizes[sectionName]}
        onSectionTileSizeChange={(sectionName, next) =>
          setSectionTileSizes((sizes) => ({ ...sizes, [sectionName]: next }))
        }
        sectionArea={(sectionName) => sectionAreas[sectionName]}
        onSectionAreaResizeStart={startSectionAreaResize}
      >
        <div className="app">
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
            {composer.helperText && <div className="composer-status">{composer.helperText}</div>}
            <input
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.nativeEvent.isComposing) submit();
              }}
              placeholder={composer.placeholder}
              disabled={composer.inputDisabled}
            />
            <button onClick={submit} disabled={composer.submitDisabled}>
              {composer.buttonLabel}
            </button>
          </footer>
        </div>
      </AppShell>
    </div>
  );
}
