import { describe, expect, it } from "vitest";

import { drawerPoolStatusText, shouldAutoRequestDrawer } from "./cuePanelDrawer";

// 큐 패널이 열리면 프리셋 서랍을 한 번 자동으로 받는다(새 WS 타입 없이 기존 서랍 요청).
describe("큐 패널이 열리면 서랍을 자동으로 받는다", () => {
  const opened = { panelOpen: true, drawerSections: null, drawerAsk: null, canRequest: true };

  it("패널이 열렸고 서랍이 아직 없고 아직 묻지 않았으면 묻는다", () => {
    expect(shouldAutoRequestDrawer(opened)).toBe(true);
  });

  it("패널이 닫혀 있으면 묻지 않는다", () => {
    expect(shouldAutoRequestDrawer({ ...opened, panelOpen: false })).toBe(false);
  });

  it("서랍이 이미 왔으면 다시 묻지 않는다", () => {
    expect(shouldAutoRequestDrawer({ ...opened, drawerSections: [] })).toBe(false);
  });

  it("이미 물었으면(답 대기·거절·시간 초과) 자동으로 또 묻지 않는다", () => {
    expect(shouldAutoRequestDrawer({ ...opened, drawerAsk: { busyAt: 0 } })).toBe(false);
  });

  it("요청 수단이 없으면(서랍 배선이 없는 화면) 묻지 않는다", () => {
    expect(shouldAutoRequestDrawer({ ...opened, canRequest: false })).toBe(false);
  });
});

// 드롭다운 안내는 「먼저 열어야」라고 잠그지 않고, 받는 상태를 그대로 말한다.
describe("드롭다운 안내 문구는 받는 상태를 말한다", () => {
  it("받는 중에는 기다리라고 말하고, 「먼저 열어야」라고 잠그지 않는다", () => {
    const text = drawerPoolStatusText("loading");
    expect(text).toContain("받는 중");
    expect(text).not.toContain("먼저 열어야");
  });

  it("콘솔이 바빠 거절됐으면 서랍의 「다시 시도」를 안내한다", () => {
    expect(drawerPoolStatusText("busy")).toContain("다시 시도");
  });

  it("답이 늦으면 서랍의 「다시 시도」를 안내한다", () => {
    expect(drawerPoolStatusText("timeout")).toContain("다시 시도");
  });

  it("서랍은 왔는데 이 풀이 없으면 그렇게 말한다", () => {
    expect(drawerPoolStatusText("loaded")).toContain("없어요");
  });
});
