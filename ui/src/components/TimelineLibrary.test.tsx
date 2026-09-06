// TimelineLibraryView 구조 테스트 (카드 t309).
//
// 이 프로젝트엔 jsdom 하네스가 없다(protocol.ts 머리말). TimelineLibraryView 는
// 그 한계 때문에 hook 없이 쪼개져 있으므로 평범한 함수로 직접 부르고, 돌아온
// React element tree 를 렌더러 없이 들여다본다 — RunbookMode.test.tsx 와 같은 수법.
import type { ReactElement } from "react";
import { describe, expect, it, vi } from "vitest";

import { TimelineLibraryView, type TimelineLibraryViewProps } from "./TimelineLibrary";

function flatten(node: unknown, out: unknown[] = []): unknown[] {
  if (node === null || node === undefined || node === false) return out;
  if (Array.isArray(node)) {
    for (const item of node) flatten(item, out);
    return out;
  }
  out.push(node);
  const children = (node as ReactElement | null)?.props?.children;
  if (children !== undefined) flatten(children, out);
  return out;
}

/** 접힌 토글 버튼이 실제로 화면에 내놓는 글자. */
function toggleLabel(props: Partial<TimelineLibraryViewProps>): string {
  const base: TimelineLibraryViewProps = {
    items: [],
    open: false,
    draftName: "",
    busy: false,
    notice: null,
    hasTimeline: false,
    onToggleOpen: vi.fn(),
    onDraftNameChange: vi.fn(),
    onSave: vi.fn(),
    onLoad: vi.fn(),
    onDelete: vi.fn(),
  };
  const tree = TimelineLibraryView({ ...base, ...props }) as ReactElement;
  const button = flatten(tree).find(
    (n) => (n as ReactElement | null)?.props?.className === "timeline-library-toggle",
  ) as ReactElement;
  return flatten(button.props.children)
    .filter((n) => typeof n === "string")
    .join("");
}

describe("TimelineLibraryView — 접힌 라벨이 스스로 상태를 말한다 (t309)", () => {
  it("저장본이 있으면 개수를 붙인다", () => {
    const items = [
      { id: "a", name: "Sugar", saved_at: null, song_title: null, sequence_number: null, lifecycle: null, section_count: 4 },
      { id: "b", name: "Sugar v2", saved_at: null, song_title: null, sequence_number: null, lifecycle: null, section_count: 4 },
    ] as unknown as TimelineLibraryViewProps["items"];
    expect(toggleLabel({ items })).toContain("(2)");
  });

  it("비었으면 빈 틀을 내지 않고 비었다고 말한다 — 타임라인이 있다는 인상을 주지 않는다", () => {
    const label = toggleLabel({ items: [], hasTimeline: false });
    expect(label).toContain("저장된 것 없음");
  });

  it("아직/못 읽었으면(items === null) 개수도 '없음'도 꾸며내지 않는다", () => {
    const label = toggleLabel({ items: null });
    expect(label).not.toContain("없음");
    expect(label).not.toMatch(/\(\d+\)/);
    expect(label).toContain("타임라인 라이브러리");
  });
});
