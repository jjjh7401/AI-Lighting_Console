// App split-pane layout tests — chat-first regression guard
// (SPEC-COPILOT-DASHUI-001 M3, AC-DASHUI-009).
//
// Mocked-fidelity bound: this project has no DOM/jsdom test harness (see
// protocol.ts's own header). `useCopilotSocket()` calls React hooks
// (useReducer/useState/useEffect/useRef) that need an active render
// dispatcher this test setup doesn't provide, so `App()` itself cannot be
// called directly here — the same bound useCopilotSocket.test.ts documents
// for the socket hook. `AppShell` is hook-free by design (see App.tsx)
// precisely so the split-pane layout decision stays testable without a
// renderer: it is called directly as a plain function and its returned
// React element tree is inspected, the same technique DashBoard.test.tsx
// applies to the sibling DashBoard component.
import type { ReactElement } from "react";
import { describe, expect, it, vi } from "vitest";

import {
  AppShell,
  ATTACHMENT_BUSY_MESSAGE,
  attachmentControlState,
  attachmentInputDisabled,
  composerViewState,
  dashPressTargetNo,
  readRunbookModeFromStorage,
  targetKindForDashSection,
  writeRunbookModeToStorage,
} from "./App";
import { DashBoard } from "./components/DashBoard";
import { TimelineLibrary } from "./components/TimelineLibrary";
import { initialState } from "./protocol";

function childArray(element: ReactElement): unknown[] {
  const children = element.props.children;
  return Array.isArray(children) ? children : [children];
}

/** DashBoard now lives inside a .dashboard-wrap div — find it one level deeper. */
function findDashBoard(shellChildren: unknown[]): ReactElement | undefined {
  for (const child of shellChildren) {
    if ((child as ReactElement | null)?.type === DashBoard) return child as ReactElement;
    const el = child as ReactElement | null;
    if (el?.props?.className === "dashboard-wrap") {
      const inner = Array.isArray(el.props.children) ? el.props.children : [el.props.children];
      const found = inner.find((c: unknown) => (c as ReactElement | null)?.type === DashBoard);
      if (found) return found as ReactElement;
    }
  }
  return undefined;
}

// Stands in for the existing chat UI subtree (header/banner/main/composer —
// ChatView, ApprovalCard, ReviewCard, SettingsPanel, StatusBanner all live
// inside it). AppShell must never inspect or rewrite it — only wrap it.
const CHAT_SENTINEL = "chat-ui-sentinel";

// M5 (design.md §4) — the section-name-to-target_kind map that keys
// panel_execute/panel_stop dispatch and the panel.running lookup.
describe("targetKindForDashSection (M5)", () => {
  it("maps executors → 'executor' and macros → 'macro'", () => {
    expect(targetKindForDashSection("executors")).toBe("executor");
    expect(targetKindForDashSection("macros")).toBe("macro");
  });

  it("read-only dash sections (groups/preset_pools/plugins/fixtures) map to null — structurally never fire", () => {
    expect(targetKindForDashSection("groups")).toBeNull();
    expect(targetKindForDashSection("preset_pools")).toBeNull();
    expect(targetKindForDashSection("plugins")).toBeNull();
    expect(targetKindForDashSection("fixtures")).toBeNull();
  });
});

// AC-DASHUI-005 — the executor fire target is the server-VERIFIED console
// number, never the pool slot (live-measured: page 1 slot 1 = "Executor 101").
describe("dashPressTargetNo", () => {
  it("executors fire meta.console_no, not the pool-slot no", () => {
    const item = { no: 1, name: "Sequence 50", meta: { resolved: true, console_no: 101 } };
    expect(dashPressTargetNo("executors", item)).toBe(101);
  });

  it("an executor without a verified console number never fires (fail-closed)", () => {
    expect(dashPressTargetNo("executors", { no: 1, name: "Sequence 50" })).toBeNull();
    expect(
      dashPressTargetNo("executors", { no: 1, name: "Sequence 50", meta: { resolved: false } }),
    ).toBeNull();
  });

  it("macros fire their own pool number unchanged", () => {
    expect(dashPressTargetNo("macros", { no: 3, name: "Blackout FX" })).toBe(3);
  });

  it("read-only sections have no press target at all", () => {
    expect(dashPressTargetNo("groups", { no: 1, name: "Vocals" })).toBeNull();
  });
});

describe("composerViewState", () => {
  it("keeps the composer closed while the server is disconnected", () => {
    const state = composerViewState({ connected: false, status: null, draft: "Group 1" });

    expect(state.inputDisabled).toBe(true);
    expect(state.submitDisabled).toBe(true);
    expect(state.canSubmit).toBe(false);
    expect(state.placeholder).toContain("서버");
  });

  it("keeps the composer closed until a gate status arrives", () => {
    const state = composerViewState({ connected: true, status: null, draft: "Group 1" });

    expect(state.inputDisabled).toBe(true);
    expect(state.submitDisabled).toBe(true);
    expect(state.canSubmit).toBe(false);
    expect(state.helperText).toContain("상태 확인");
  });

  it("blocks new chat input when the gate reports executions_blocked", () => {
    const state = composerViewState({
      connected: true,
      status: { health: "console_offline", live_lock: false, executions_blocked: true },
      draft: "보컬 그룹 만들어줘",
    });

    expect(state.inputDisabled).toBe(true);
    expect(state.submitDisabled).toBe(true);
    expect(state.buttonLabel).toBe("차단됨");
    expect(state.helperText).toContain("콘솔 연결");
  });

  it("allows text entry but not empty submission when the gate is healthy", () => {
    const empty = composerViewState({
      connected: true,
      status: { health: "online", live_lock: false, executions_blocked: false },
      draft: "   ",
    });
    const ready = composerViewState({
      connected: true,
      status: { health: "online", live_lock: false, executions_blocked: false },
      draft: "보컬 그룹 만들어줘",
    });

    expect(empty.inputDisabled).toBe(false);
    expect(empty.submitDisabled).toBe(true);
    expect(empty.canSubmit).toBe(false);
    expect(ready.submitDisabled).toBe(false);
    expect(ready.canSubmit).toBe(true);
  });

  it("keeps the composer open while responding: typing queues, empty cannot submit", () => {
    const empty = composerViewState({
      connected: true,
      status: { health: "online", live_lock: false, executions_blocked: false },
      draft: "",
      responding: true,
    });
    const drafted = composerViewState({
      connected: true,
      status: { health: "online", live_lock: false, executions_blocked: false },
      draft: "다음 요청",
      responding: true,
    });

    // The operator can DRAFT the next request during a running turn…
    expect(empty.inputDisabled).toBe(false);
    expect(empty.submitDisabled).toBe(true);
    expect(empty.canSubmit).toBe(false);
    // …and submitting queues it (serialized execution, never concurrent).
    expect(drafted.canSubmit).toBe(true);
    expect(drafted.buttonLabel).toBe("대기열 추가");
    expect(drafted.helperText).toBe("요청 응답이 완료될 때까지 잠시 기다려 주세요.");
  });

  it("keeps live-lock proposal mode available instead of treating it as offline", () => {
    const state = composerViewState({
      connected: true,
      status: { health: "online", live_lock: true, executions_blocked: false },
      draft: "코러스 웅장하게",
    });

    expect(state.inputDisabled).toBe(false);
    expect(state.canSubmit).toBe(true);
    expect(state.placeholder).toContain("제안");
    expect(state.helperText).toContain("제안 카드");
  });
});

// 리뷰 발견 #1 — 서버는 응답 처리 중(busy) 업로드를 busy_event로 버리고
// 저장하지 않으므로, UI가 먼저 첨부를 막아 낙관적 썸네일과 서버 상태의
// 불일치를 원천 차단해야 한다 (App.tsx attachmentControlState 참조).
describe("attachmentControlState", () => {
  it("disables attachment while responding and explains why in the title", () => {
    const state = attachmentControlState({
      inputDisabled: false,
      responding: true,
      queueLength: 0,
    });

    expect(state.disabled).toBe(true);
    expect(state.title).toBe(ATTACHMENT_BUSY_MESSAGE);
  });

  it("disables attachment while requests are queued (the next turn starts immediately)", () => {
    const state = attachmentControlState({
      inputDisabled: false,
      responding: false,
      queueLength: 2,
    });

    expect(state.disabled).toBe(true);
    expect(state.title).toBe(ATTACHMENT_BUSY_MESSAGE);
  });

  it("stays disabled when the composer itself is closed, without the busy message", () => {
    const state = attachmentControlState({
      inputDisabled: true,
      responding: false,
      queueLength: 0,
    });

    expect(state.disabled).toBe(true);
    expect(state.title).toContain("파일 첨부");
  });

  // t271 — 콘솔이 오프라인이면 명령 입력(composer)은 닫히지만, 첨부는 서버만
  // 있으면 된다(업로드·곡 분석은 콘솔에 닿지 않는 순수 서버 작업). 브라우저
  // 실측(reports/musicsync-browser-check-20260906.md 발견 1)에서 첨부 버튼이
  // 콘솔 상태에 잠겨 곡 분석 자체에 닿을 수 없었다.
  describe("attachmentInputDisabled (t271)", () => {
    it("stays closed while the server is disconnected or its status is unknown", () => {
      expect(attachmentInputDisabled({ connected: false, status: null })).toBe(true);
      expect(attachmentInputDisabled({ connected: true, status: null })).toBe(true);
    });

    it("opens when the console is offline — uploads never touch the console", () => {
      expect(
        attachmentInputDisabled({
          connected: true,
          status: { health: "console_offline", live_lock: false, executions_blocked: true },
        }),
      ).toBe(false);
    });

    it("is what the attach button reads, so console-offline no longer locks it", () => {
      const state = attachmentControlState({
        inputDisabled: attachmentInputDisabled({
          connected: true,
          status: { health: "console_offline", live_lock: false, executions_blocked: true },
        }),
        responding: false,
        queueLength: 0,
      });
      expect(state.disabled).toBe(false);
      expect(state.title).toContain("WAV");
    });
  });

  it("allows attachment when idle with the default file-format title", () => {
    const state = attachmentControlState({
      inputDisabled: false,
      responding: false,
      queueLength: 0,
    });

    expect(state.disabled).toBe(false);
    expect(state.title).toContain("VWX");
    expect(state.title).toContain("PNG");
  });
});

describe("AppShell — console-primary split layout (M6 inversion)", () => {
  it("chat open: mounts exactly one DashBoard node alongside the untouched chat children", () => {
    const element = AppShell({
      chatCollapsed: false,
      dash: initialState.dash,
      cueMonitor: initialState.cueMonitor,
      onToggleChat: vi.fn(),
      children: CHAT_SENTINEL,
    }) as ReactElement;

    expect(element.type).toBe("div");
    expect(element.props.className).toBe("app-shell chat-split");

    const children = childArray(element);
    const db = findDashBoard(children);
    expect(db).toBeDefined();
    expect(db!.props.dash).toBe(initialState.dash);
    expect(children).toContain(CHAT_SENTINEL);
  });

  it("chat collapsed: DashBoard STILL mounts (console pane is permanent) and a chat-rail re-open button replaces the chat children", () => {
    const onToggleChat = vi.fn();
    const element = AppShell({
      chatCollapsed: true,
      dash: initialState.dash,
      cueMonitor: initialState.cueMonitor,
      onToggleChat,
      children: CHAT_SENTINEL,
    }) as ReactElement;

    expect(element.props.className).toBe("app-shell chat-collapsed");

    const children = childArray(element);
    const db = findDashBoard(children);
    expect(db).toBeDefined();
    expect(children).not.toContain(CHAT_SENTINEL);

    const rail = children.find(
      (child) => (child as ReactElement | null)?.props?.className === "chat-rail",
    ) as ReactElement;
    expect(rail).toBeDefined();
    const railButton = (
      Array.isArray(rail.props.children) ? rail.props.children[0] : rail.props.children
    ) as ReactElement;
    expect(railButton.props["aria-label"]).toBe("채팅 펼치기");
    railButton.props.onClick();
    expect(onToggleChat).toHaveBeenCalledTimes(1);
  });

  it("does not offer a dashboard collapse affordance — DashBoard's onToggleCollapse slot stays undefined", () => {
    const element = AppShell({
      chatCollapsed: false,
      dash: initialState.dash,
      cueMonitor: initialState.cueMonitor,
      onToggleChat: vi.fn(),
      children: CHAT_SENTINEL,
    }) as ReactElement;
    const db = findDashBoard(childArray(element));

    expect(db!.props.onToggleCollapse).toBeUndefined();
  });

  // M5 (design.md §4, REQ-DASHUI-017) — press/refresh/running wiring passthrough.
  it("threads onRefresh/isItemRunning/onItemPress through to DashBoard unchanged", () => {
    const onRefresh = vi.fn();
    const isItemRunning = vi.fn();
    const onItemPress = vi.fn();
    const element = AppShell({
      chatCollapsed: false,
      dash: initialState.dash,
      cueMonitor: initialState.cueMonitor,
      onToggleChat: vi.fn(),
      onRefresh,
      isItemRunning,
      onItemPress,
      children: CHAT_SENTINEL,
    }) as ReactElement;
    const db = findDashBoard(childArray(element));

    expect(db!.props.onRefresh).toBe(onRefresh);
    expect(db!.props.isItemRunning).toBe(isItemRunning);
    expect(db!.props.onItemPress).toBe(onItemPress);
  });

  it("omitting onRefresh/isItemRunning/onItemPress leaves DashBoard's slots undefined — no forced stub", () => {
    const element = AppShell({
      chatCollapsed: false,
      dash: initialState.dash,
      cueMonitor: initialState.cueMonitor,
      onToggleChat: vi.fn(),
      children: CHAT_SENTINEL,
    }) as ReactElement;
    const db = findDashBoard(childArray(element));

    expect(db!.props.onRefresh).toBeUndefined();
    expect(db!.props.isItemRunning).toBeUndefined();
    expect(db!.props.onItemPress).toBeUndefined();
  });

  it("never mutates or wraps the passed children — same value passes through unchanged when chat is open", () => {
    const split = AppShell({
      chatCollapsed: false,
      dash: initialState.dash,
      cueMonitor: initialState.cueMonitor,
      onToggleChat: vi.fn(),
      children: CHAT_SENTINEL,
    }) as ReactElement;

    expect(childArray(split)).toContain(CHAT_SENTINEL);
  });
});

// T-E — runbook-mode toggle persistence. This vitest run has no jsdom/DOM
// harness (see the file header), so `window` is not a real global here;
// these tests stand a minimal fake in for it, matching the fail-open
// contract the functions themselves already promise (storage unavailable →
// behave as if the mode were off, never throw).
describe("runbook-mode localStorage persistence (T-E)", () => {
  function withFakeLocalStorage<T>(run: (store: Map<string, string>) => T): T {
    const store = new Map<string, string>();
    const fakeWindow = {
      localStorage: {
        getItem: (key: string) => store.get(key) ?? null,
        setItem: (key: string, value: string) => {
          store.set(key, value);
        },
        removeItem: (key: string) => {
          store.delete(key);
        },
      },
    };
    (globalThis as { window?: unknown }).window = fakeWindow;
    try {
      return run(store);
    } finally {
      delete (globalThis as { window?: unknown }).window;
    }
  }

  it("defaults to off when nothing was ever stored", () => {
    withFakeLocalStorage(() => {
      expect(readRunbookModeFromStorage()).toBe(false);
    });
  });

  it("round-trips on → off through write/read", () => {
    withFakeLocalStorage(() => {
      writeRunbookModeToStorage(true);
      expect(readRunbookModeFromStorage()).toBe(true);
      writeRunbookModeToStorage(false);
      expect(readRunbookModeFromStorage()).toBe(false);
    });
  });

  it("never throws when storage is unavailable — degrades to off", () => {
    expect(() => writeRunbookModeToStorage(true)).not.toThrow();
    expect(readRunbookModeFromStorage()).toBe(false);
  });
});

// 카드 t309 — 저장된 타임라인에 손잡이가 없던 결함.
//
// 억누르던 줄은 App.tsx 의 `{runbookMode ? (` 하나다: 라이브러리는
// RunbookMode 안에만 있었고, 런북 모드는 fresh 세션에서 꺼져 있다
// (readRunbookModeFromStorage 는 저장된 키가 없으면 false). 그래서 앱을
// 처음 연 감독의 화면에는 라이브러리가 아예 mount 되지 않았다 — API 는
// 저장본을 내주고 있는데도.
//
// jsdom 이 없어(파일 머리말) App() 자체는 못 부른다. 대신 기본 화면의
// 컨테이너인 AppShell 이 슬롯을 실제로 tree 에 싣는지를 잰다. 브라우저
// 끝단 측정은 .moai/state/verify/t309/ 에 따로 있다.
describe("AppShell — 타임라인 라이브러리 도달 가능성 (t309)", () => {
  function libraryIn(children: unknown[]): ReactElement | undefined {
    for (const child of children) {
      const el = child as ReactElement | null;
      if (el?.type === TimelineLibrary) return el;
      if (el?.props?.className === "dashboard-wrap") {
        const inner = Array.isArray(el.props.children) ? el.props.children : [el.props.children];
        const found = inner.find(
          (c: unknown) => (c as ReactElement | null)?.type === TimelineLibrary,
        );
        if (found) return found as ReactElement;
      }
    }
    return undefined;
  }

  it("타임라인이 없어도(hasTimeline=false) 기본 화면에 라이브러리가 mount 된다", () => {
    const element = AppShell({
      chatCollapsed: false,
      dash: initialState.dash,
      cueMonitor: initialState.cueMonitor,
      onToggleChat: vi.fn(),
      librarySlot: <TimelineLibrary hasTimeline={false} onLoaded={vi.fn()} />,
      children: CHAT_SENTINEL,
    }) as ReactElement;

    const lib = libraryIn(childArray(element));
    expect(lib).toBeDefined();
    expect(lib!.props.hasTimeline).toBe(false);
  });

  it("슬롯을 안 주면 라이브러리 노드도 없다 — 슬롯이 실제 렌더 경로다", () => {
    const element = AppShell({
      chatCollapsed: false,
      dash: initialState.dash,
      cueMonitor: initialState.cueMonitor,
      onToggleChat: vi.fn(),
      children: CHAT_SENTINEL,
    }) as ReactElement;

    expect(libraryIn(childArray(element))).toBeUndefined();
  });
});
