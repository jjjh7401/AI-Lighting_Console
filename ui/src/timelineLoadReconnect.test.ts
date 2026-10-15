// 불러오기 성공 뒤 연결을 한 번 다시 맺는 규칙 — 성공이면 재연결 1회, 실패면 0회.
// 서버는 연결할 때 세션 값(줄 머리 sub_info 등)을 다시 보내므로, 이 재연결이 곧 상태 재수신이다.
import { describe, expect, it, vi } from "vitest";

import { reconnectAfterTimelineLoad } from "./timelineLoadReconnect";

describe("reconnectAfterTimelineLoad — 불러오기 성공 → 재연결 1회, 실패 → 0회", () => {
  it("불러오기에 성공하면 재연결을 정확히 한 번 부른다", () => {
    const reconnect = vi.fn();

    expect(reconnectAfterTimelineLoad({ song_title: "LOVE ATTACK" }, reconnect)).toBe(true);
    expect(reconnect).toHaveBeenCalledTimes(1);
  });

  it("불러오기에 실패하면(결과가 없으면) 재연결을 부르지 않는다", () => {
    const reconnect = vi.fn();

    expect(reconnectAfterTimelineLoad(null, reconnect)).toBe(false);
    expect(reconnect).not.toHaveBeenCalled();
  });
});
