// 카드 t598 — 「⇪ 콘솔에 반영」이 실패한 사유(서버 `beat_grid_send_status.reason`)를
// 격자 화면 상단 바 바로 아래에 보인다. 승인 창 사이 콘솔에서 번호가 채워져 송신을
// 통째로 멈춘 경우, 감독이 「다시 반영」해야 한다는 걸 전체화면에서 바로 본다.
// (이 프로젝트는 jsdom 이 없다 — `renderToStaticMarkup`.)
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

import { BeatGrid, applyFailureNote } from "./BeatGrid";
import type { BeatGridSendStatus, BeatGridView } from "../protocol";

const FILLED =
  "승인 창이 떠 있는 사이 콘솔에서 2.71이(가) 채워져, 덮어쓰지 않으려고 아무것도 보내지 않았습니다 — 다시 반영하세요";

function status(overrides: Partial<BeatGridSendStatus> = {}): BeatGridSendStatus {
  return {
    pending_apply_count: 1,
    last_action: "apply",
    ok: false,
    reason: FILLED,
    blocked_cells: [],
    approval_vs_sent: null,
    ...overrides,
  };
}

const GRID: BeatGridView = {
  song_title: "T598",
  bar_range: { start: 0, end: 8 },
  source: "custom",
  note: null,
  scene_memos: [],
  probe_results: {},
  unsent_cells: null,
  tracks: [],
} as unknown as BeatGridView;

describe("applyFailureNote", () => {
  it("반영 실패면 서버 사유를 그대로 싣는다", () => {
    expect(applyFailureNote(status())).toBe(`⚠ 콘솔에 반영 안 됨 — ${FILLED}`);
  });

  it("성공·다른 동작·사유 없음은 null", () => {
    expect(applyFailureNote(status({ ok: true }))).toBeNull();
    expect(applyFailureNote(status({ last_action: "preview" }))).toBeNull();
    expect(applyFailureNote(status({ reason: null }))).toBeNull();
    expect(applyFailureNote(null)).toBeNull();
  });

  it("서버 문구(session.py)에 「다시 반영하세요」가 실제로 있다", () => {
    const source = readFileSync(resolve(__dirname, "../../../server/web/session.py"), "utf8");
    expect(source).toContain("채워져, 덮어쓰지");
    expect(source).toContain("아무것도 보내지 않았습니다 — 다시 반영하세요");
  });
});

describe("BeatGrid — 반영 실패 사유 줄", () => {
  it("실패 상태면 상단 바 아래에 사유가 보인다", () => {
    const html = renderToStaticMarkup(<BeatGrid grid={GRID} sendStatus={status()} />);
    expect(html).toContain("beat-grid-apply-fail");
    expect(html).toContain("2.71");
    expect(html).toContain("다시 반영하세요");
  });

  it("성공 상태면 줄이 없다", () => {
    const html = renderToStaticMarkup(<BeatGrid grid={GRID} sendStatus={status({ ok: true })} />);
    expect(html).not.toContain("beat-grid-apply-fail");
  });
});
