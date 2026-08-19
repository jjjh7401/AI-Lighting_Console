import type { ReactElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { type ChatEntry, type CommandView } from "../protocol";
import {
  ChatView,
  COMMANDS_COLLAPSE_THRESHOLD,
  CommandRow,
  commandDetailText,
  commandStatusSummary,
  firstSentence,
} from "./ChatView";

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

describe("collapsed command summary", () => {
  it("rolls statuses up per Korean label, insertion-ordered", () => {
    const commands: CommandView[] = [
      { ...COMMAND, label: "실행 완료", status: "executed_ok" },
      { ...COMMAND, label: "실행 완료", status: "executed_ok" },
      { ...COMMAND, label: "건너뜀 (중복 실행 방지)", status: "skipped_already_executed" },
    ];
    expect(commandStatusSummary(commands)).toBe("실행 완료 2 · 건너뜀 (중복 실행 방지) 1");
  });

  it("every command list collapses by default (operator decision)", () => {
    // Threshold 0: even a 1-command result starts collapsed — the collapsed
    // line carries count + status roll-up, and expanding is one click.
    expect(COMMANDS_COLLAPSE_THRESHOLD).toBe(0);
  });
});

describe("firstSentence — collapsed assistant body", () => {
  it("cuts at the first sentence end", () => {
    expect(firstSentence("요청한 명령을 모두 실행했습니다. 모든 장비(Group 13)를 선택하여…")).toBe(
      "요청한 명령을 모두 실행했습니다.",
    );
  });

  it("falls back to the first line when no period ends it", () => {
    expect(firstSentence("## 완료 — 전체 40대 반영\n상세 내용…")).toBe("## 완료 — 전체 40대 반영");
  });

  it("a single short sentence needs no toggle (preview equals text)", () => {
    expect(firstSentence("완료했습니다.")).toBe("완료했습니다.");
  });
});

describe("ChatView — 진행 스트리밍 한 줄", () => {
  const ENTRIES: ChatEntry[] = [{ kind: "user", text: "무대 좌표 읽고 그대로 걸어줘" }];

  it("renders the in-flight progress line under the transcript", () => {
    const html = renderToStaticMarkup(
      <ChatView
        entries={ENTRIES}
        progress={{ phase: "tool_start", detail: "무대 좌표 읽기…", seq: 2 }}
      />,
    );
    expect(html).toContain("무대 좌표 읽기…");
    expect(html).toContain('class="entry entry-progress"');
    // phase는 스타일/진단용으로 DOM에 남는다 — 문구는 서버가 정한다.
    expect(html).toContain('data-phase="tool_start"');
    // 대화록 항목보다 뒤에 온다: 진행은 항상 맨 아래 한 줄이다.
    expect(html.indexOf("무대 좌표 읽고")).toBeLessThan(html.indexOf("무대 좌표 읽기…"));
  });

  it("shows nothing when the turn is over (progress null) — 종료 시 사라진다", () => {
    const html = renderToStaticMarkup(<ChatView entries={ENTRIES} progress={null} />);
    expect(html).not.toContain("entry-progress");
  });

  it("omitting the prop behaves like a finished turn (구버전 서버 호환)", () => {
    const html = renderToStaticMarkup(<ChatView entries={ENTRIES} />);
    expect(html).not.toContain("entry-progress");
  });

  it("keeps exactly ONE progress line — 대화록에 쌓이지 않는다", () => {
    const html = renderToStaticMarkup(
      <ChatView entries={ENTRIES} progress={{ phase: "model_call", detail: "마무리 정리 중…", seq: 9 }} />,
    );
    expect(html.split("entry-progress").length - 1).toBe(1);
  });
});
