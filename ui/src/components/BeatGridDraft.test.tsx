// SPEC-LDARRANGE-001 — 자동 배치 초안 카드와 「자동 배치 제안」 버튼이 글로 보이는지 잰다.
// 이 프로젝트는 jsdom 이 없어 `renderToStaticMarkup` 으로 글자만 본다.
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { BeatGridDraft, BeatGridView } from "../protocol";
import { BeatGrid } from "./BeatGrid";

// 서버 렌더가 끼우는 `<!-- -->` 조각을 떼어 글자 그대로 본다.
const plain = (html: string) => html.replace(/<!-- -->/g, "");

// 칸이 없는 격자 — 초안 카드만 시험한다(격자 칸 모양은 다른 시험이 본다).
function emptyGrid(): BeatGridView {
  return {
    song_title: "LOVE ATTACK",
    bar_range: { start: 0, end: 25 },
    tracks: [],
    scene_memos: [],
    probe_results: [],
    source: "empty",
    note: null,
    console_audio_offset_seconds: 0,
  } as unknown as BeatGridView;
}

const DRAFT: BeatGridDraft = {
  draft_id: "d-1",
  bar_range: { start: 0, end: 25 },
  windows: [],
  tracks: [
    {
      group_name: "FOH",
      group_no: 3,
      group_no_confirmed: true,
      layer_role: "key",
      cells: [
        { bar: 3, label: "FOH 초안 1" },
        { bar: 7, label: "FOH 초안 2" },
      ],
    },
  ],
};

const EMPTY_DRAFT: BeatGridDraft = { ...DRAFT, tracks: [] };

describe("자동 배치 초안 카드", () => {
  it("보류 중이면 줄·칸 수와 적용·거절을 보인다", () => {
    const html = plain(
      renderToStaticMarkup(
        <BeatGrid grid={emptyGrid()} pendingDraft={DRAFT} onDraftApply={() => {}} onDraftReject={() => {}} />,
      ),
    );
    expect(html).toContain("자동 배치 초안");
    expect(html).toContain("줄 1개 · 칸 2개");
    expect(html).toContain("FOH · 2칸");
    expect(html).toContain(">적용</button>");
    expect(html).toContain(">거절</button>");
  });

  it("칸이 없는 초안은 적용을 막는다", () => {
    const html = plain(
      renderToStaticMarkup(<BeatGrid grid={emptyGrid()} pendingDraft={EMPTY_DRAFT} onDraftApply={() => {}} />),
    );
    expect(html).toMatch(/<button[^>]*disabled=""[^>]*>적용<\/button>/);
  });
});

describe("분석 직후 줄 없는 새 작업본(카드 WT-track-model)", () => {
  it("줄이 없으면 서버 안내 「자동 배치를 누르면 콘솔 그룹으로 줄을 만들어요」와 자동 배치 버튼을 보인다", () => {
    const grid = {
      ...emptyGrid(),
      source: "analysis",
      note: "자동 배치를 누르면 콘솔 그룹으로 줄을 만들어요.",
    } as unknown as BeatGridView;
    const html = plain(renderToStaticMarkup(<BeatGrid grid={grid} onDraftPropose={() => {}} />));
    expect(html).toContain("자동 배치를 누르면 콘솔 그룹으로 줄을 만들어요.");
    expect(html).toContain(">자동 배치<");
    expect(html).not.toContain("표시할 트랙이 없습니다.");
  });
});

describe("「자동 배치 제안」 버튼", () => {
  it("보류 초안이 없고 제안 핸들러가 있으면 버튼을 보인다", () => {
    const html = plain(renderToStaticMarkup(<BeatGrid grid={emptyGrid()} onDraftPropose={() => {}} />));
    expect(html).toContain(">자동 배치<");
  });

  it("보류 초안이 있으면 제안 버튼을 감춘다", () => {
    const html = plain(
      renderToStaticMarkup(<BeatGrid grid={emptyGrid()} pendingDraft={DRAFT} onDraftPropose={() => {}} />),
    );
    expect(html).not.toContain(">자동 배치<");
  });
});
