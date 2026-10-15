// 반영 준비 — 타임코드 번호 입력 메시지 모양 시험. 이 메시지는 번호 하나만 싣는다
// (서버가 곡 초안과 보관함에만 적고, 콘솔에는 쓰지 않는다).
import { describe, expect, it } from "vitest";

import { PROTOCOL_VERSION, buildBeatGridTimecodeSet } from "./protocol";

describe("buildBeatGridTimecodeSet", () => {
  it("carries only the director's timecode number", () => {
    const frame = JSON.parse(buildBeatGridTimecodeSet(7));

    expect(frame).toEqual({
      v: PROTOCOL_VERSION,
      type: "beat_grid_timecode_set",
      timecode_number: 7,
    });
  });
});
