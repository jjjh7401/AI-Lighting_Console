// Chat transcript: user lines, assistant reports (gate-truth command statuses),
// proposal cards (REQ-MVP-016), Korean errors (REQ-MVP-044), busy/notice lines.
import { useState } from "react";

import { type ChatEntry, type CommandView, type ProgressState } from "../protocol";
import { ExecutionPreviewCard } from "./ExecutionPreviewCard";

// Command lists start COLLAPSED regardless of length (operator decision): the
// collapsed line already carries the count + per-status roll-up, so nothing
// load-bearing is hidden, and the transcript stays scannable.
export const COMMANDS_COLLAPSE_THRESHOLD = 0;

/** Korean per-status roll-up for the collapsed summary line, insertion-ordered. */
export function commandStatusSummary(commands: CommandView[]): string {
  const counts = new Map<string, number>();
  for (const command of commands) {
    counts.set(command.label, (counts.get(command.label) ?? 0) + 1);
  }
  return [...counts.entries()].map(([label, count]) => `${label} ${count}`).join(" · ");
}

function statusClass(status: string): string {
  switch (status) {
    case "executed_ok":
      return "cmd-ok";
    case "unconfirmed":
      return "cmd-unconfirmed";
    case "proposal":
    case "held":
      return "cmd-held";
    case "skipped_already_executed":
      return "cmd-skip";
    default:
      return "cmd-bad";
  }
}

export function commandDetailText(command: CommandView): string | null {
  const detail = command.detail.trim();
  return detail ? detail : null;
}

function copyCommand(command: string) {
  if (typeof navigator === "undefined" || navigator.clipboard === undefined) return;
  void navigator.clipboard.writeText(command);
}

export function CommandRow({ command }: { command: CommandView }) {
  const detail = commandDetailText(command);
  return (
    <div className={`command-row ${statusClass(command.status)}`}>
      <div className="command-main">
        <code className="command-text">{command.command}</code>
        {detail && <span className="command-detail">{detail}</span>}
      </div>
      <div className="command-meta">
        <span className="command-label">{command.label || command.status}</span>
        <button
          type="button"
          className="command-copy"
          onClick={() => copyCommand(command.command)}
          aria-label="명령 복사"
        >
          복사
        </button>
      </div>
    </div>
  );
}

export function CollapsibleCommands({ commands }: { commands: CommandView[] }) {
  const collapsible = commands.length > COMMANDS_COLLAPSE_THRESHOLD;
  const [open, setOpen] = useState(!collapsible);
  return (
    <div className="commands">
      {collapsible && (
        <button
          type="button"
          className="commands-toggle"
          aria-expanded={open}
          onClick={() => setOpen((value) => !value)}
        >
          <span className="commands-toggle-arrow">{open ? "▾" : "▸"}</span> 명령{" "}
          {commands.length}개 — {commandStatusSummary(commands)}
          <span className="commands-toggle-hint">{open ? " 접기" : " 펼치기"}</span>
        </button>
      )}
      {open &&
        commands.map((command, index) => (
          <CommandRow key={`${command.command}-${index}`} command={command} />
        ))}
    </div>
  );
}

/** The first sentence of a reply — what the collapsed body shows. Falls back
 *  to the first line when the line carries no sentence-ending period. */
export function firstSentence(text: string): string {
  const firstLine = text.split("\n", 1)[0].trim();
  const match = firstLine.match(/^[^.!?]*[.!?]/);
  return (match ? match[0] : firstLine).trim();
}

export function CollapsibleAssistantText({ text }: { text: string }) {
  const preview = firstSentence(text);
  const truncated = preview.length < text.trim().length;
  const [open, setOpen] = useState(false);
  if (!truncated) return <div className="assistant-text">{text}</div>;
  return (
    <div className="assistant-text">
      {open ? text : preview}
      <button
        type="button"
        className="assistant-text-toggle"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
      >
        {open ? "접기" : "…펼치기"}
      </button>
    </div>
  );
}

function Entry({ entry }: { entry: ChatEntry }) {
  switch (entry.kind) {
    case "user":
      return <div className="entry entry-user">{entry.text}</div>;
    case "assistant":
      return (
        <div className="entry entry-assistant">
          {entry.summary && <div className="summary">{entry.summary}</div>}
          {entry.text && <CollapsibleAssistantText text={entry.text} />}
          {entry.commands.length > 0 && <CollapsibleCommands commands={entry.commands} />}
        </div>
      );
    case "proposal":
      return (
        <div className="entry entry-proposal">
          <div className="proposal-title">제안 카드 — 라이브 잠금 중 (전송되지 않음)</div>
          {entry.commands.map((command) => (
            <code key={command} className="proposal-command">
              {command}
            </code>
          ))}
          {entry.reasons.map((reason) => (
            <div key={reason} className="proposal-reason">
              {reason}
            </div>
          ))}
        </div>
      );
    case "preview":
      return (
        <div className="entry entry-preview">
          <ExecutionPreviewCard preview={entry.preview} />
        </div>
      );
    case "error":
      return <div className="entry entry-error">⛔ {entry.message}</div>;
    case "busy":
      return <div className="entry entry-busy">⏳ {entry.message}</div>;
    case "notice":
      return <div className="entry entry-notice">📢 {entry.message}</div>;
  }
}

export function ChatView({
  entries,
  progress = null,
  streamingAnswer = null,
}: {
  entries: ChatEntry[];
  /**
   * 진행 중인 턴의 마지막 한 줄. 대화록 **밖**에 붙는 소멸성 표시이므로
   * `entries`에 섞지 않고 항상 맨 아래 한 줄로만 산다 — 턴이 끝나면 상위가
   * `null`을 내려 사라진다(protocol.ts `reduceServerEvent`).
   */
  progress?: ProgressState | null;
  /**
   * 도착하는 중인 답 본문 (SPEC-COPILOT-STREAM-001). 같은 이유로 `entries`
   * 밖에 산다 — 턴이 끝나면 확정본이 `entries`로 들어오고 이쪽은 사라진다.
   * 접기 없이 통째로 보여 준다: 아직 자라는 중인 글에 "…펼치기"를 붙이면
   * 다 읽기도 전에 버튼이 움직인다.
   */
  streamingAnswer?: string | null;
}) {
  return (
    <div className="chat-view">
      {entries.length === 0 && (
        <div className="entry entry-hint">
          어려운 용어 없이 말하듯 적어 보세요 — 예: "처음은 차분하게, 후렴은 크게 터지게 해줘"
        </div>
      )}
      {entries.map((entry, index) => (
        <Entry key={index} entry={entry} />
      ))}
      {streamingAnswer && (
        <div className="entry entry-assistant entry-streaming" aria-live="polite">
          <div className="assistant-text">{streamingAnswer}</div>
        </div>
      )}
      {progress !== null && (
        <div className="entry entry-progress" data-phase={progress.phase} role="status">
          ⏳ {progress.detail}
        </div>
      )}
    </div>
  );
}
