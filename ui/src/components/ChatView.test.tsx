// "패널에 추가" affordance tests (SPEC-COPILOT-SHOWUI-001 M4 — REQ-SHOWUI-004).
//
// The pin frame is payload-free: the server seeds it from its own
// `_last_created` cross-turn memory, so the only thing the UI decides is WHICH
// chat entry may offer the button. That decision is this pure function; getting
// it wrong offers to pin a turn that created nothing.
import { describe, expect, it } from "vitest";

import { pinnableIndex } from "./ChatView";
import { type ChatEntry, type CommandView } from "../protocol";

function command(status: string): CommandView {
  return { command: "Store Sequence 71", status, label: status, detail: "" };
}

function assistant(...statuses: string[]): ChatEntry {
  return {
    kind: "assistant",
    status: "ok",
    summary: "연출을 만들었습니다",
    text: "",
    commands: statuses.map(command),
  };
}

describe("pinnableIndex", () => {
  it("offers the pin on a turn that created something", () => {
    expect(pinnableIndex([{ kind: "user", text: "룩 만들어줘" }, assistant("executed_ok")])).toBe(1);
  });

  it("offers nothing on an empty transcript", () => {
    expect(pinnableIndex([])).toBe(-1);
  });

  it("offers nothing when the assistant only talked", () => {
    expect(pinnableIndex([assistant()])).toBe(-1);
  });

  it("offers nothing when every command failed — there is no object to pin", () => {
    expect(pinnableIndex([assistant("blocked", "skipped_already_executed")])).toBe(-1);
  });

  it("offers the pin on an unconfirmed send — the object may well exist", () => {
    // The command left the gate; only the console's confirmation is missing.
    // Refusing to offer the pin here would hide the feature exactly when the
    // responder is degraded, and the server still answers explicitly if its
    // seed is absent.
    expect(pinnableIndex([assistant("unconfirmed")])).toBe(0);
  });

  it("tracks the LAST creating turn, not the last turn", () => {
    const entries: ChatEntry[] = [
      assistant("executed_ok"),
      { kind: "user", text: "고마워" },
      assistant(),
      { kind: "notice", message: "안내" },
    ];
    // The server's seed still points at what turn 0 created.
    expect(pinnableIndex(entries)).toBe(0);
  });

  it("moves the affordance forward when a later turn creates again", () => {
    const entries: ChatEntry[] = [assistant("executed_ok"), assistant("executed_ok")];
    expect(pinnableIndex(entries)).toBe(1);
  });

  it("ignores non-assistant entries entirely", () => {
    const entries: ChatEntry[] = [
      { kind: "proposal", commands: ["Go+ Executor 1"], reasons: [] },
      { kind: "error", message: "실패", errorKind: "panel" },
      { kind: "busy", message: "진행 중" },
    ];
    expect(pinnableIndex(entries)).toBe(-1);
  });
});
