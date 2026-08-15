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
import { type ChangeEvent, type ReactNode, useEffect, useRef, useState } from "react";

import { ApprovalCard } from "./components/ApprovalCard";
import { ChatView } from "./components/ChatView";
import { CueMonitor } from "./components/CueMonitor";
import { DashBoard } from "./components/DashBoard";
import { LockToggle } from "./components/LockToggle";
import { OnboardingBanner } from "./components/OnboardingBanner";
import { PaperworkPanel } from "./components/PaperworkPanel";
import { QuestionCard } from "./components/QuestionCard";
import { ReviewCard } from "./components/ReviewCard";
import { RunbookMode } from "./components/RunbookMode";
import { SettingsPanel } from "./components/SettingsPanel";
import { StatusBanner } from "./components/StatusBanner";
import {
  clampPoolArea,
  POOL_AREA_DEFAULT,
  type PoolArea,
} from "./components/PoolSection";
import {
  panelItemId,
  type CueMonitorState,
  type DashItem,
  type DashState,
  type PanelTargetKind,
  type StatusState,
} from "./protocol";
import { useCopilotSocket } from "./useCopilotSocket";
import { apiUrl } from "./launchContext";
import { parseSettingsResponse, providerLabel, type SettingsResponse } from "./settings";

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

// Runbook-mode toggle (T-E) — the one piece of client persistence this
// component owns. localStorage (not session-volatile React state) so the
// mode survives a refresh, matching the task's explicit requirement; every
// other App.tsx view preference (chat-collapsed, tile sizes) stays
// session-volatile by design (design.md §6 / D5) and is left alone.
const RUNBOOK_MODE_STORAGE_KEY = "ma3-copilot.runbook-mode";
const MAX_VECTORWORKS_UPLOAD_BYTES = 8 * 1024 * 1024;
// SPEC-COPILOT-IMGLAYOUT-001 M1 — layout-sketch attachment channel, mirrored
// against server/web/messages.py's LAYOUT_IMAGE_MIME_TYPES / MAX_LAYOUT_IMAGE_BYTES.
const LAYOUT_IMAGE_MIME_TYPES = ["image/png", "image/jpeg", "image/webp"];
const MAX_LAYOUT_IMAGE_BYTES = 5 * 1024 * 1024;


export function readRunbookModeFromStorage(): boolean {
  try {
    return window.localStorage.getItem(RUNBOOK_MODE_STORAGE_KEY) === "1";
  } catch {
    return false;
  }
}

export function writeRunbookModeToStorage(active: boolean): void {
  try {
    if (active) {
      window.localStorage.setItem(RUNBOOK_MODE_STORAGE_KEY, "1");
    } else {
      window.localStorage.removeItem(RUNBOOK_MODE_STORAGE_KEY);
    }
  } catch {
    // Storage unavailable (private mode, disabled) — the toggle still works
    // for the current session, it just won't survive a refresh.
  }
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
  responding = false,
}: {
  connected: boolean;
  status: StatusState | null;
  draft: string;
  responding?: boolean;
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
  if (responding) {
    // The turn runs on the server; the composer stays OPEN so the operator can
    // draft the next request. Submitting now QUEUES it (App serializes the
    // queue — one instruction at a time, never concurrent).
    const hasDraft = draft.trim().length > 0;
    return {
      inputDisabled: false,
      submitDisabled: !hasDraft,
      placeholder: "처리 중에도 다음 요청을 미리 작성할 수 있습니다…",
      buttonLabel: "대기열 추가",
      helperText: "요청 응답이 완료될 때까지 잠시 기다려 주세요.",
      canSubmit: hasDraft,
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
  cueMonitor,
  onToggleChat,
  onRefresh,
  onCueMonitorRefresh,
  isItemRunning,
  onItemPress,
  isExecutorRunning,
  onExecutorExecute,
  onExecutorBack,
  onExecutorStop,
  onExecutorGoto,
  openCueExecutorNo,
  onToggleCueExecutor,
  sectionTileSize,
  onSectionTileSizeChange,
  sectionArea,
  onSectionAreaResizeStart,
  dashWidth,
  onDashDividerDown,
  children,
}: {
  chatCollapsed: boolean;
  dash: DashState;
  cueMonitor: CueMonitorState;
  onToggleChat: () => void;
  onRefresh?: () => void;
  onCueMonitorRefresh?: () => void;
  isItemRunning?: (sectionName: string, item: DashItem) => boolean;
  onItemPress?: (sectionName: string, item: DashItem) => void;
  isExecutorRunning?: (executorNo: number) => boolean;
  onExecutorExecute?: (executorNo: number) => void;
  onExecutorBack?: (executorNo: number) => void;
  onExecutorStop?: (executorNo: number) => void;
  onExecutorGoto?: (executorNo: number, cue: number) => void;
  openCueExecutorNo?: number | null;
  onToggleCueExecutor?: (executorNo: number) => void;
  sectionTileSize?: (sectionName: string) => number | undefined;
  onSectionTileSizeChange?: (sectionName: string, next: number) => void;
  sectionArea?: (sectionName: string) => PoolArea | undefined;
  onSectionAreaResizeStart?: (
    sectionName: string,
    event: { clientX: number; clientY: number },
  ) => void;
  /** Pixel width of the dashboard pane; undefined = flex default. */
  dashWidth?: number;
  /** Start a divider drag between dashboard and cue monitor. */
  onDashDividerDown?: (startX: number) => void;
  children: ReactNode;
}) {
  const dashStyle = dashWidth !== undefined ? { width: dashWidth, flexShrink: 0 } : undefined;
  return (
    <div className={`app-shell ${chatCollapsed ? "chat-collapsed" : "chat-split"}`}>
      <div className="dashboard-wrap" style={dashStyle}>
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
      </div>
      {onDashDividerDown && (
        <div
          className="pane-divider"
          onMouseDown={(e) => { e.preventDefault(); onDashDividerDown(e.clientX); }}
        />
      )}
      <CueMonitor
        cueMonitor={cueMonitor}
        onRefresh={onCueMonitorRefresh}
        isExecutorRunning={isExecutorRunning}
        onExecute={onExecutorExecute}
        onBack={onExecutorBack}
        onStop={onExecutorStop}
        onGoto={onExecutorGoto}
        openExecutorNo={openCueExecutorNo}
        onToggleExecutor={onToggleCueExecutor}
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
    responding,
    sendChat,
    sendDecision,
    sendReviewDecision,
    sendQuestionAnswer,
    sendLock,
    sendPanelExecute,
    sendPanelStop,
    sendPanelBack,
    sendPanelGoto,
    sendDashRefresh,
    sendCueMonitorRefresh,
    sendVectorworksExportUpload,
    sendLayoutImageUpload,
    clearChat,
  } = useCopilotSocket();
  const [draft, setDraft] = useState("");
  // Requests typed while a turn is running. Drained ONE at a time — the next
  // is sent only after the current turn's terminal response arrives, so
  // queued instructions execute strictly in order, never concurrently (the
  // server rejects a second in-flight chat with a busy event anyway).
  const [queue, setQueue] = useState<string[]>([]);
  const vectorworksInputRef = useRef<HTMLInputElement>(null);
  const [vectorworksUploadError, setVectorworksUploadError] = useState<string | null>(null);
  // SPEC-COPILOT-IMGLAYOUT-001 M1 — the attached layout-sketch thumbnail
  // (client-side display only; the server holds the authoritative copy).
  const [layoutImageUploadError, setLayoutImageUploadError] = useState<string | null>(null);
  const [layoutImage, setLayoutImage] = useState<{ fileName: string; dataUrl: string } | null>(
    null,
  );
  const [settingsOpen, setSettingsOpen] = useState(false);
  // T-E — volunteer runbook mode. localStorage-backed (see
  // readRunbookModeFromStorage above) so it survives a refresh; the lazy
  // initializer reads it once on mount.
  const [runbookMode, setRunbookMode] = useState(readRunbookModeFromStorage);
  const toggleRunbookMode = () => {
    setRunbookMode((active) => {
      const next = !active;
      writeRunbookModeToStorage(next);
      return next;
    });
  };
  // W3 — paperwork panel toggle. Session-volatile (no localStorage), same
  // default every other App.tsx view preference besides runbookMode uses
  // (design.md §6 / D5) — runbookMode's persistence is an explicit,
  // deliberate exception this toggle does not need to repeat.
  const [paperworkMode, setPaperworkMode] = useState(false);
  // Bumped when the settings panel closes so the onboarding banner re-checks
  // whether a key was just added (and hides itself if so).
  const [settingsRefresh, setSettingsRefresh] = useState(0);
  const [activeModel, setActiveModel] = useState<SettingsResponse | null>(null);
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
  // Dashboard-CueMonitor divider drag: adjusts the dashboard pane width.
  // Session-volatile, same pattern as sectionAreas above.
  const [dashWidth, setDashWidth] = useState<number | undefined>(undefined);
  const startDashDividerDrag = (startX: number) => {
    // On first drag, snapshot the dashboard's current rendered width.
    const dashEl = document.querySelector(".dashboard-wrap") as HTMLElement | null;
    const baseWidth = dashWidth ?? dashEl?.offsetWidth ?? 400;
    const onMove = (e: MouseEvent) => {
      const next = Math.max(200, baseWidth + (e.clientX - startX));
      setDashWidth(next);
    };
    const onUp = () => {
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
    };
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
  };
  // T-H4 — CueMonitor's cue sheet opens ONE executor at a time (MA3 console
  // convention); this is the SAME name toggling off as re-closing (see
  // CueMonitor.tsx's own module header on why this is controlled here
  // rather than internal component state).
  const [openCueExecutorNo, setOpenCueExecutorNo] = useState<number | null>(null);
  const toggleCueExecutor = (executorNo: number) => {
    setOpenCueExecutorNo((current) => (current === executorNo ? null : executorNo));
  };
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

  useEffect(() => {
    let cancelled = false;
    const loadActiveModel = async () => {
      try {
        const response = await fetch(apiUrl("/api/settings"));
        const settings = parseSettingsResponse(await response.text());
        if (!cancelled) setActiveModel(settings);
      } catch {
        if (!cancelled) setActiveModel(null);
      }
    };
    void loadActiveModel();
    return () => {
      cancelled = true;
    };
  }, [settingsRefresh]);
  const composer = composerViewState({ connected, status: state.status, draft, responding });

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [
    state.entries.length,
    state.pendingApprovals.length,
    state.pendingReviews.length,
    state.pendingQuestions.length,
  ]);

  const submit = () => {
    if (!composer.canSubmit) return;
    const text = draft.trim();
    if (responding || queue.length > 0) {
      setQueue((pending) => [...pending, text]);
    } else {
      sendChat(text);
    }
    setDraft("");
  };

  useEffect(() => {
    if (responding || queue.length === 0) return;
    if (!connected || state.status === null || state.status.executions_blocked) return;
    const [next, ...rest] = queue;
    setQueue(rest);
    sendChat(next);
  }, [responding, queue, connected, state.status, sendChat]);

  const uploadVectorworksExport = (file: File) => {
    if (![".csv", ".txt", ".xlsx", ".mvr"].some((extension) => file.name.toLowerCase().endsWith(extension))) {
      setVectorworksUploadError("Vectorworks export는 CSV, TXT, XLSX 또는 MVR 파일만 올릴 수 있습니다.");
      return;
    }
    if (file.size === 0 || file.size > MAX_VECTORWORKS_UPLOAD_BYTES) {
      setVectorworksUploadError("Vectorworks export는 비어 있지 않은 8 MiB 이하 파일이어야 합니다.");
      return;
    }
    const reader = new FileReader();
    reader.onerror = () => setVectorworksUploadError("Vectorworks 파일을 읽지 못했습니다.");
    reader.onload = () => {
      const result = reader.result;
      if (typeof result !== "string") {
        setVectorworksUploadError("파일을 텍스트 프레임으로 변환하지 못했습니다.");
        return;
      }
      const separator = result.indexOf(",");
      if (separator < 0) {
        setVectorworksUploadError("파일을 텍스트 프레임으로 변환하지 못했습니다.");
        return;
      }
      if (!sendVectorworksExportUpload(file.name, result.slice(separator + 1))) {
        setVectorworksUploadError("서버 연결이 끊겨 파일을 올릴 수 없습니다.");
        return;
      }
      setVectorworksUploadError(null);
    };
    reader.readAsDataURL(file);
  };

  const uploadLayoutImage = (file: File) => {
    if (!LAYOUT_IMAGE_MIME_TYPES.includes(file.type)) {
      setLayoutImageUploadError("이미지는 PNG, JPEG 또는 WEBP 파일만 첨부할 수 있습니다.");
      return;
    }
    if (file.size === 0 || file.size > MAX_LAYOUT_IMAGE_BYTES) {
      setLayoutImageUploadError("이미지는 비어 있지 않은 5 MiB 이하 파일이어야 합니다.");
      return;
    }
    const reader = new FileReader();
    reader.onerror = () => setLayoutImageUploadError("이미지 파일을 읽지 못했습니다.");
    reader.onload = () => {
      const result = reader.result;
      if (typeof result !== "string") {
        setLayoutImageUploadError("파일을 이미지 프레임으로 변환하지 못했습니다.");
        return;
      }
      const separator = result.indexOf(",");
      if (separator < 0) {
        setLayoutImageUploadError("파일을 이미지 프레임으로 변환하지 못했습니다.");
        return;
      }
      if (!sendLayoutImageUpload(file.name, file.type, result.slice(separator + 1))) {
        setLayoutImageUploadError("서버 연결이 끊겨 이미지를 올릴 수 없습니다.");
        return;
      }
      setLayoutImageUploadError(null);
      setLayoutImage({ fileName: file.name, dataUrl: result });
    };
    reader.readAsDataURL(file);
  };

  // 사용자 결정 (2026-08-15): 첨부 버튼은 하나 — 파일 종류가 목적지를 고른다.
  // 이미지 MIME(계약 §1)은 layout_image_upload로, 나머지는 기존 Vectorworks
  // 경로로 보낸다. 각 경로의 검증·오류 문구는 그대로다: 여기는 라우터일 뿐
  // 두 번째 검증 계층이 아니다.
  const uploadAttachment = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.currentTarget.files?.[0];
    event.currentTarget.value = "";
    if (file === undefined) return;
    if (LAYOUT_IMAGE_MIME_TYPES.includes(file.type)) {
      uploadLayoutImage(file);
    } else {
      uploadVectorworksExport(file);
    }
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

  // T-E — RunbookMode fires the SAME panel_execute/panel_stop wire path as
  // the dashboard's executor tiles above, just keyed directly on the
  // console-verified executor number cue_monitor already reports (no
  // DashItem/meta.console_no lookup needed here — see cue_monitor.py's own
  // note that it shares dash.py's resolved_executor_nos).
  const isExecutorRunning = (executorNo: number): boolean =>
    state.panel.running[panelItemId("executor", executorNo)]?.running ?? false;
  const pressExecutor = (executorNo: number) => {
    if (isExecutorRunning(executorNo)) {
      sendPanelStop("executor", executorNo);
    } else {
      sendPanelExecute("executor", executorNo);
    }
  };

  return (
    <div className="app-frame">
      <header className="header">
        <h1>MA3 코파일럿</h1>
        <div className="header-actions">
          <button
            className={`runbook-toggle${runbookMode ? " runbook-toggle-active" : ""}`}
            onClick={toggleRunbookMode}
            aria-label={runbookMode ? "런북 모드 끄기" : "런북 모드 켜기"}
            aria-pressed={runbookMode}
          >
            {runbookMode ? "✓ 런북 모드" : "런북 모드"}
          </button>
          <button
            className={`paperwork-toggle${paperworkMode ? " paperwork-toggle-active" : ""}`}
            onClick={() => setPaperworkMode((active) => !active)}
            aria-label={paperworkMode ? "페이퍼워크 닫기" : "페이퍼워크 열기"}
            aria-pressed={paperworkMode}
          >
            {paperworkMode ? "✓ 페이퍼워크" : "페이퍼워크"}
          </button>
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
      {runbookMode ? (
        <div className="runbook-mode-frame">
          <RunbookMode
            cueMonitor={state.cueMonitor}
            isExecutorRunning={isExecutorRunning}
            onExecute={pressExecutor}
            onRefresh={sendCueMonitorRefresh}
          />
          {/* Approvals/reviews still surface here — RunbookMode's run button
              rides the same gated panel_execute path, so a required
              approval never gets bypassed just because the rest of the UI
              is hidden (contract item 4). */}
          {state.pendingApprovals.map((approval) => (
            <ApprovalCard key={approval.request_id} approval={approval} onDecision={sendDecision} />
          ))}
          {state.pendingQuestions.map((question) => (
            <QuestionCard
              key={question.request_id}
              question={question}
              onAnswer={sendQuestionAnswer}
            />
          ))}
          {state.pendingReviews.map((review) => (
            <ReviewCard key={review.request_id} review={review} onDecision={sendReviewDecision} />
          ))}
        </div>
      ) : paperworkMode ? (
        <div className="paperwork-mode-frame">
          <PaperworkPanel onClose={() => setPaperworkMode(false)} />
        </div>
      ) : (
        <>
          <StatusBanner status={state.status} connected={connected} />
          <OnboardingBanner
            onOpenSettings={() => setSettingsOpen(true)}
            refreshSignal={settingsRefresh}
          />
          {settingsOpen && <SettingsPanel onClose={closeSettings} />}
          <AppShell
            chatCollapsed={chatCollapsed}
            dash={state.dash}
            cueMonitor={state.cueMonitor}
            onToggleChat={() => setChatCollapsed((collapsed) => !collapsed)}
            onRefresh={sendDashRefresh}
            onCueMonitorRefresh={sendCueMonitorRefresh}
            isItemRunning={isDashItemRunning}
            onItemPress={pressDashItem}
            isExecutorRunning={isExecutorRunning}
            onExecutorExecute={(executorNo) => sendPanelExecute("executor", executorNo)}
            onExecutorBack={(executorNo) => sendPanelBack("executor", executorNo)}
            onExecutorStop={(executorNo) => sendPanelStop("executor", executorNo)}
            onExecutorGoto={(executorNo, cue) => sendPanelGoto("executor", executorNo, cue)}
            openCueExecutorNo={openCueExecutorNo}
            onToggleCueExecutor={toggleCueExecutor}
            sectionTileSize={(sectionName) => sectionTileSizes[sectionName]}
            onSectionTileSizeChange={(sectionName, next) =>
              setSectionTileSizes((sizes) => ({ ...sizes, [sectionName]: next }))
            }
            sectionArea={(sectionName) => sectionAreas[sectionName]}
            onSectionAreaResizeStart={startSectionAreaResize}
            dashWidth={dashWidth}
            onDashDividerDown={startDashDividerDrag}
          >
            <div className="app">
              <main className="main">
                {state.entries.length > 0 && (
                  <div className="chat-tools">
                    <button
                      type="button"
                      className="chat-clear"
                      onClick={() => {
                        if (window.confirm("대화 내용을 모두 지울까요?")) clearChat();
                      }}
                    >
                      대화 지우기
                    </button>
                  </div>
                )}
                <ChatView entries={state.entries} />
                {state.pendingApprovals.map((approval) => (
                  <ApprovalCard
                    key={approval.request_id}
                    approval={approval}
                    onDecision={sendDecision}
                  />
                ))}
                {state.pendingQuestions.map((question) => (
                  <QuestionCard
                    key={question.request_id}
                    question={question}
                    onAnswer={sendQuestionAnswer}
                  />
                ))}
                {state.pendingReviews.map((review) => (
                  <ReviewCard key={review.request_id} review={review} onDecision={sendReviewDecision} />
                ))}
                <div ref={bottomRef} />
              </main>
              <footer className="composer">
                {composer.helperText && <div className="composer-status">{composer.helperText}</div>}
                {vectorworksUploadError && (
                  <div className="composer-status composer-upload-error">{vectorworksUploadError}</div>
                )}
                {layoutImageUploadError && (
                  <div className="composer-status composer-upload-error">{layoutImageUploadError}</div>
                )}
                {queue.length > 0 && (
                  <div className="composer-queue" aria-label="대기 중 요청">
                    {queue.map((text, index) => (
                      <div className="composer-queue-item" key={`${index}-${text.slice(0, 24)}`}>
                        <span className="composer-queue-order">{index + 1}</span>
                        <span className="composer-queue-text">{text}</span>
                        <button
                          type="button"
                          className="composer-queue-remove"
                          aria-label="대기 요청 삭제"
                          onClick={() =>
                            setQueue((pending) => pending.filter((_, at) => at !== index))
                          }
                        >
                          ✕
                        </button>
                      </div>
                    ))}
                  </div>
                )}
                <textarea
                  className="composer-input"
                  rows={2}
                  value={draft}
                  onChange={(event) => setDraft(event.target.value)}
                  onKeyDown={(event) => {
                    if (
                      event.key === "Enter" &&
                      !event.shiftKey &&
                      !event.nativeEvent.isComposing
                    ) {
                      event.preventDefault();
                      submit();
                    }
                  }}
                  placeholder={composer.placeholder}
                  disabled={composer.inputDisabled}
                />
                <div className="composer-bar">
                  <input
                    ref={vectorworksInputRef}
                    className="composer-file-input"
                    type="file"
                    accept=".csv,.txt,.xlsx,.mvr,image/png,image/jpeg,image/webp"
                    onChange={uploadAttachment}
                    disabled={composer.inputDisabled}
                  />
                  <button
                    type="button"
                    className="composer-upload"
                    onClick={() => vectorworksInputRef.current?.click()}
                    disabled={composer.inputDisabled}
                    title="파일 첨부 — VWX(CSV·TXT·XLSX·MVR) 또는 배치 이미지(PNG·JPEG·WEBP)"
                    aria-label="파일 첨부"
                  >
                    ＋
                  </button>
                  {layoutImage && (
                    <div className="composer-image-thumb" title={layoutImage.fileName}>
                      <img src={layoutImage.dataUrl} alt={layoutImage.fileName} />
                    </div>
                  )}
                  <div className="composer-model" aria-live="polite">
                    {activeModel === null
                      ? "모델 확인 중…"
                      : `${
                          activeModel.settings.active_provider === "claude_code"
                            ? "Claude 구독"
                            : providerLabel(activeModel.settings.active_provider)
                        }${activeModel.active_model ? ` · ${activeModel.active_model}` : ""}`}
                  </div>
                  <button
                    className="composer-send"
                    onClick={submit}
                    disabled={composer.submitDisabled}
                  >
                    {composer.buttonLabel}
                  </button>
                </div>
              </footer>
            </div>
          </AppShell>
        </>
      )}
    </div>
  );
}
