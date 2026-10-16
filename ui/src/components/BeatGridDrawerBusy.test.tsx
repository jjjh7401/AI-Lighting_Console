// 서랍·프리셋 계획 요청이 서버 `busy` 거절을 맞으면 「불러오는 중」/무반응으로 두지 않는다.
// (이 프로젝트는 jsdom 이 없다 — 상태 판정은 순수 함수로 뽑아 시험한다.)
import { describe, expect, it } from "vitest";

import { drawerLoadState, presetPlanRefusedBusy } from "./BeatGrid";
import { initialState, reduceServerEvent as reduce } from "../protocol";

describe("drawerLoadState", () => {
  it("요청 전·요청 뒤 답 대기는 loading", () => {
    expect(drawerLoadState(null, null, 0, false)).toBe("loading");
    expect(drawerLoadState(null, { busyAt: 0 }, 0, false)).toBe("loading");
  });
  it("요청 뒤 busy 가 오면 busy — 영원히 불러오는 중이 아니다", () => {
    expect(drawerLoadState(null, { busyAt: 0 }, 1, false)).toBe("busy");
  });
  it("요청 전에 있던 busy 는 이 요청의 거절이 아니다", () => {
    expect(drawerLoadState(null, { busyAt: 2 }, 2, false)).toBe("loading");
  });
  it("시간 초과면 timeout, 받았으면 항상 loaded", () => {
    expect(drawerLoadState(null, { busyAt: 0 }, 0, true)).toBe("timeout");
    expect(drawerLoadState([], { busyAt: 0 }, 5, true)).toBe("loaded");
  });
});

describe("presetPlanRefusedBusy", () => {
  it("요청 뒤 busy 가 왔고 계획표가 없으면 거절로 본다", () => {
    expect(presetPlanRefusedBusy({ busyAt: 0 }, false, 1)).toBe(true);
  });
  it("계획표가 떴거나 busy 가 없었거나 요청 전이면 아니다", () => {
    expect(presetPlanRefusedBusy({ busyAt: 0 }, true, 1)).toBe(false);
    expect(presetPlanRefusedBusy({ busyAt: 1 }, false, 1)).toBe(false);
    expect(presetPlanRefusedBusy(null, false, 3)).toBe(false);
  });
});

describe("reducer busyCount", () => {
  it("busy 이벤트마다 1씩 오른다", () => {
    const once = reduce(initialState, { v: 1, type: "busy", message: "처리 중" });
    expect(once.busyCount).toBe(1);
    expect(reduce(once, { v: 1, type: "busy", message: "처리 중" }).busyCount).toBe(2);
  });
});
