// MA3 copilot Korean chat UI (M5 — REQ-MVP-020/021/022 UI halves;
// M7 — deploy review card, REQ-MVP-019/027).
import { useEffect, useRef, useState } from "react";

import { ApprovalCard } from "./components/ApprovalCard";
import { ChatView } from "./components/ChatView";
import { LockToggle } from "./components/LockToggle";
import { OnboardingBanner } from "./components/OnboardingBanner";
import { ReviewCard } from "./components/ReviewCard";
import { SettingsPanel } from "./components/SettingsPanel";
import { StatusBanner } from "./components/StatusBanner";
import { useCopilotSocket } from "./useCopilotSocket";

export default function App() {
  const { state, connected, sendChat, sendDecision, sendReviewDecision, sendLock } =
    useCopilotSocket();
  const [draft, setDraft] = useState("");
  const [settingsOpen, setSettingsOpen] = useState(false);
  // Bumped when the settings panel closes so the onboarding banner re-checks
  // whether a key was just added (and hides itself if so).
  const [settingsRefresh, setSettingsRefresh] = useState(0);
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

  return (
    <div className="app">
      <header className="header">
        <h1>MA3 코파일럿</h1>
        <div className="header-actions">
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
  );
}
