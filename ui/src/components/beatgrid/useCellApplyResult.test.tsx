// @vitest-environment jsdom
// 칸 단위 반영 결과 훅 시험(카드 WT-cell-apply) — 새 응답이 올 때만 반응하는가, 어떤 응답이 요약을 바꾸고 어떤 응답이
// 그대로 두는가, 재생 중이면 콘솔을 그 마디로 옮기지 않는가. BeatGrid 전체를 그리지 않고 훅만 얇은 틀로 마운트한다.
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { BeatGridSendStatus, BeatGridSubsetStatus } from "../../protocol";
import { useCellApplyResult, type CellApplyResultOptions } from "./useCellApplyResult";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const SUBSET: BeatGridSubsetStatus = {
  requested: 2,
  applied: [
    ["FOH", 4],
    ["BACK", 2],
  ],
  not_applied: [],
};

function status(overrides: Partial<BeatGridSendStatus> = {}): BeatGridSendStatus {
  return {
    pending_apply_count: 0,
    last_action: "apply",
    ok: true,
    reason: null,
    blocked_cells: [],
    approval_vs_sent: null,
    ...overrides,
  };
}

let container: HTMLElement;
let root: Root;
let latest: ReturnType<typeof useCellApplyResult>;

function Harness(options: CellApplyResultOptions) {
  latest = useCellApplyResult(options);
  return <p>{latest.result?.text ?? "없음"}</p>;
}

beforeEach(() => {
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(() => {
  act(() => root.unmount());
  container.remove();
});

const render = (options: CellApplyResultOptions) => act(() => root.render(<Harness {...options} />));

describe("useCellApplyResult", () => {
  it("칸 단위 반영이 성공하면 요약을 쥐고 보낸 첫 칸의 마디를 보러 간다", () => {
    const onPreviewBar = vi.fn();
    render({ sendStatus: null, onPreviewBar });
    render({ sendStatus: status({ subset: SUBSET }), onPreviewBar });
    expect(latest.result?.text).toBe("2칸 반영 · 못 보낸 칸 0개");
    expect(onPreviewBar).toHaveBeenCalledTimes(1);
    expect(onPreviewBar).toHaveBeenCalledWith(4);
  });

  it("재생 중이거나 콘솔이 돌고 있을 수 있으면(previewBlocked) 요약은 쥐되 콘솔을 그 마디로 옮기지 않는다", () => {
    const onPreviewBar = vi.fn();
    render({ sendStatus: null, onPreviewBar, previewBlocked: true });
    render({ sendStatus: status({ subset: SUBSET }), onPreviewBar, previewBlocked: true });
    expect(latest.result?.text).toBe("2칸 반영 · 못 보낸 칸 0개");
    expect(onPreviewBar).not.toHaveBeenCalled();
  });

  it("막힘 여부는 응답이 오는 순간의 값을 쓴다 — 그 뒤에 풀려도 지난 응답으로 뒤늦게 옮기지 않는다", () => {
    const onPreviewBar = vi.fn();
    const done = status({ subset: SUBSET });
    render({ sendStatus: null, onPreviewBar, previewBlocked: true });
    render({ sendStatus: done, onPreviewBar, previewBlocked: true });
    render({ sendStatus: done, onPreviewBar, previewBlocked: false });
    expect(onPreviewBar).not.toHaveBeenCalled();
  });

  it("콜백이 없어도 요약은 쥔다", () => {
    render({ sendStatus: null });
    render({ sendStatus: status({ subset: SUBSET }) });
    expect(latest.result?.firstBar).toBe(4);
  });

  it("마운트 때 이미 있던 응답에는 반응하지 않는다", () => {
    const onPreviewBar = vi.fn();
    render({ sendStatus: status({ subset: SUBSET }), onPreviewBar });
    expect(latest.result).toBeNull();
    expect(onPreviewBar).not.toHaveBeenCalled();
  });

  it("같은 응답 객체로 다시 그려도 되풀이하지 않는다", () => {
    const onPreviewBar = vi.fn();
    const done = status({ subset: SUBSET });
    render({ sendStatus: null, onPreviewBar });
    render({ sendStatus: done, onPreviewBar });
    render({ sendStatus: done, onPreviewBar });
    expect(onPreviewBar).toHaveBeenCalledTimes(1);
  });

  it("미리보기·편집 응답은 요약을 그대로 둔다", () => {
    render({ sendStatus: null });
    render({ sendStatus: status({ subset: SUBSET }) });
    render({ sendStatus: status({ last_action: "preview" }) });
    expect(latest.result).not.toBeNull();
    render({ sendStatus: status({ last_action: "edit" }) });
    expect(latest.result).not.toBeNull();
  });

  it("다음 반영 응답이 오면 요약을 바꾼다 — 전체 반영이나 실패면 지운다", () => {
    const onPreviewBar = vi.fn();
    render({ sendStatus: null, onPreviewBar });
    render({ sendStatus: status({ subset: SUBSET }), onPreviewBar });
    render({ sendStatus: status({ completed: "reflected" }), onPreviewBar });
    expect(latest.result).toBeNull();
    render({ sendStatus: status({ subset: SUBSET }), onPreviewBar });
    render({ sendStatus: status({ ok: false, reason: "거절" }), onPreviewBar });
    expect(latest.result).toBeNull();
    expect(onPreviewBar).toHaveBeenCalledTimes(2);
  });

  it("보낸 칸이 하나도 없는 응답은 요약도 마디 이동도 없다", () => {
    const onPreviewBar = vi.fn();
    render({ sendStatus: null, onPreviewBar });
    render({ sendStatus: status({ subset: { ...SUBSET, applied: [] } }), onPreviewBar });
    expect(latest.result).toBeNull();
    expect(onPreviewBar).not.toHaveBeenCalled();
  });

  it("dismiss 는 요약을 지운다", () => {
    render({ sendStatus: null });
    render({ sendStatus: status({ subset: SUBSET }) });
    act(() => latest.dismiss());
    expect(latest.result).toBeNull();
  });
});
