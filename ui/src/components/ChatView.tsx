// Chat transcript: user lines, assistant reports (gate-truth command statuses),
// proposal cards (REQ-MVP-016), Korean errors (REQ-MVP-044), busy/notice lines.
// SHOWUI M4 adds the "패널에 추가" affordance (REQ-SHOWUI-004).
import { type ChatEntry, type CommandView } from "../protocol";

// A turn created something if at least one of its commands reached the console.
// `unconfirmed` counts: the command left the gate and only the console's
// acknowledgement is missing, so refusing the pin there would hide the feature
// exactly when the responder is degraded. The server answers explicitly when
// its own `_last_created` seed turns out to be absent, so a wrong guess here
// surfaces as a message rather than as silence.
const CREATED_STATUSES = new Set(["executed_ok", "unconfirmed"]);

/**
 * Which entry may offer "패널에 추가", or -1 for none.
 *
 * The pin frame is payload-free — the server seeds it from its own cross-turn
 * memory of what the chat just created (REQ-SHOWUI-004) — so the UI's only job
 * is to put the button on the turn that memory refers to: the LAST turn that
 * created something, which is not necessarily the last turn.
 */
export function pinnableIndex(entries: ChatEntry[]): number {
  for (let index = entries.length - 1; index >= 0; index -= 1) {
    const entry = entries[index];
    if (entry.kind !== "assistant") continue;
    if (entry.commands.some((command) => CREATED_STATUSES.has(command.status))) return index;
  }
  return -1;
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

function CommandRow({ command }: { command: CommandView }) {
  return (
    <div className={`command-row ${statusClass(command.status)}`}>
      <code>{command.command}</code>
      <span className="command-label">{command.label}</span>
    </div>
  );
}

function Entry({ entry, onPin }: { entry: ChatEntry; onPin?: () => void }) {
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
          {onPin !== undefined && (
            <button className="entry-pin" onClick={onPin}>
              패널에 추가
            </button>
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

export function ChatView({ entries, onPin }: { entries: ChatEntry[]; onPin?: () => void }) {
  const pinnable = onPin === undefined ? -1 : pinnableIndex(entries);
  return (
    <div className="chat-view">
      {entries.length === 0 && (
        <div className="entry entry-hint">
          한국어로 지시를 입력해 보세요 — 예: "보컬 그룹 만들어줘"
        </div>
      )}
      {entries.map((entry, index) => (
        <Entry key={index} entry={entry} onPin={index === pinnable ? onPin : undefined} />
      ))}
    </div>
  );
}
