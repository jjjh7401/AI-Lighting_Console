import type { ReactElement } from "react";
import { describe, expect, it } from "vitest";

import { type CommandView } from "../protocol";
import { CommandRow, commandDetailText } from "./ChatView";

function childArray(element: ReactElement): unknown[] {
  const children = element.props.children;
  if (children === undefined) return [];
  const list = Array.isArray(children) ? children : [children];
  return list.filter((child) => child !== null && child !== undefined && child !== false);
}

const COMMAND: CommandView = {
  command: "Store /Overwrite Cue 4",
  status: "unconfirmed",
  label: "실행 미확인 (자동 재전송 안 함)",
  detail: "execution unconfirmed: no responder feedback before timeout",
};

describe("commandDetailText", () => {
  it("returns trimmed detail when the server provided one", () => {
    expect(commandDetailText({ ...COMMAND, detail: "  blocked: console offline  " })).toBe(
      "blocked: console offline",
    );
  });

  it("returns null for empty detail", () => {
    expect(commandDetailText({ ...COMMAND, detail: "   " })).toBeNull();
  });
});

describe("CommandRow", () => {
  it("renders command, Korean status label, raw detail, and a copy affordance", () => {
    const element = CommandRow({ command: COMMAND }) as ReactElement;
    const [main, meta] = childArray(element) as ReactElement[];
    const [commandText, detail] = childArray(main) as ReactElement[];
    const [label, copy] = childArray(meta) as ReactElement[];

    expect(element.props.className).toContain("cmd-unconfirmed");
    expect(commandText.props.children).toBe("Store /Overwrite Cue 4");
    expect(detail.props.children).toContain("execution unconfirmed");
    expect(label.props.children).toBe("실행 미확인 (자동 재전송 안 함)");
    expect(copy.props["aria-label"]).toBe("명령 복사");
  });
});
