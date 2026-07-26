// Chat transcript: user lines, assistant reports (gate-truth command statuses),
// proposal cards (REQ-MVP-016), Korean errors (REQ-MVP-044), busy/notice lines.
import { type ChatEntry, type CommandView } from "../protocol";

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

function Entry({ entry }: { entry: ChatEntry }) {
  switch (entry.kind) {
    case "user":
      return <div className="entry entry-user">{entry.text}</div>;
    case "assistant":
      return (
        <div className="entry entry-assistant">
          {entry.summary && <div className="summary">{entry.summary}</div>}
          {entry.text && <div className="assistant-text">{entry.text}</div>}
          {entry.commands.length > 0 && (
            <div className="commands">
              {entry.commands.map((command, index) => (
                <CommandRow key={`${command.command}-${index}`} command={command} />
              ))}
            </div>
          )}
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
    case "error":
      return <div className="entry entry-error">⛔ {entry.message}</div>;
    case "busy":
      return <div className="entry entry-busy">⏳ {entry.message}</div>;
    case "notice":
      return <div className="entry entry-notice">📢 {entry.message}</div>;
  }
}

export function ChatView({ entries }: { entries: ChatEntry[] }) {
  return (
    <div className="chat-view">
      {entries.length === 0 && (
        <div className="entry entry-hint">
          한국어로 지시를 입력해 보세요 — 예: "보컬 그룹 만들어줘"
        </div>
      )}
      {entries.map((entry, index) => (
        <Entry key={index} entry={entry} />
      ))}
    </div>
  );
}
