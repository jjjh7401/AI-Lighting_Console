import type { ReactElement } from "react";
import { describe, expect, it } from "vitest";

import { type ExecutionPreview } from "../protocol";
import { ExecutionPreviewCard, previewCommandMeta } from "./ExecutionPreviewCard";

function childArray(element: ReactElement): unknown[] {
  const children = element.props.children;
  if (children === undefined) return [];
  const list = Array.isArray(children) ? children : [children];
  return list.filter((child) => child !== null && child !== undefined && child !== false);
}

const PREVIEW: ExecutionPreview = {
  preview_id: "preview-1",
  summary: "실행 전 미리보기 — 2개 명령",
  risk_level: "danger",
  commands: [
    {
      command: "Store /Overwrite Cue 4",
      action: "store_overwrite",
      target_kind: "cue",
      target: "4",
      label: "Cue 4 덮어쓰기",
    },
    {
      command: "Group Blinder At Full",
      action: "modify",
      target_kind: "group",
      target: "Blinder",
      label: "Group Blinder 수정",
    },
  ],
  warnings: [
    {
      severity: "caution",
      label: "덮어쓰기",
      detail: "기존 cue를 바꿀 수 있습니다.",
      command: "Store /Overwrite Cue 4",
    },
    {
      severity: "danger",
      label: "객석 블라인더",
      detail: "관객 방향 고광량 출력 가능성이 있습니다.",
      command: "Group Blinder At Full",
    },
  ],
};

describe("previewCommandMeta", () => {
  it("combines target and action for dense command rows", () => {
    expect(previewCommandMeta(PREVIEW.commands[0])).toBe("cue 4 · 덮어쓰기");
  });
});

describe("ExecutionPreviewCard", () => {
  it("renders risk, commands, warnings, and scope caveat", () => {
    const element = ExecutionPreviewCard({ preview: PREVIEW }) as ReactElement;
    const [header, summary, commandList, warningList, scope] = childArray(element) as ReactElement[];
    const [title, risk] = childArray(header) as ReactElement[];
    const commandRows = childArray(commandList) as ReactElement[];
    const warnings = childArray(warningList) as ReactElement[];

    expect(element.props.className).toContain("preview-risk-danger");
    expect(title.props.children).toBe("실행 전 미리보기");
    expect(risk.props.children).toBe("위험");
    expect(summary.props.children).toBe("실행 전 미리보기 — 2개 명령");
    expect(commandRows).toHaveLength(2);
    expect(warnings).toHaveLength(2);
    expect(scope.props.children).toContain("실제 Cue diff/tracking 영향");
  });
});
