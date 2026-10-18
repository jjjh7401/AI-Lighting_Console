import { describe, expect, it } from "vitest";

import { buildBeatGridConsoleSeek } from "../../protocol";
import { consoleResyncDue, consoleSeekPlan, consoleSeekStep, consoleTimecodeSeconds } from "./consoleSeekPlan";

const paused = { consoleFollow: true, consoleFollowAvailable: true, playing: false, timecodePaused: true };
const quiet = { stopping: false, awaiting: false };

describe("consoleSeekPlan", () => {
  it("does nothing when 콘솔 같이 is off or cannot be used", () => {
    expect(consoleSeekPlan({ ...paused, consoleFollow: false })).toBe("none");
    expect(consoleSeekPlan({ ...paused, consoleFollowAvailable: false })).toBe("none");
  });

  it("moves only the console cursor while paused after ❚❚", () => {
    expect(consoleSeekPlan(paused)).toBe("seek");
  });

  it("moves the console live while playing, without pausing", () => {
    expect(consoleSeekPlan({ ...paused, playing: true, timecodePaused: false })).toBe("live");
  });

  it("leaves a fresh stop alone, because the next ▶ rewinds to the top", () => {
    expect(consoleSeekPlan({ ...paused, timecodePaused: false })).toBe("none");
  });
});

describe("consoleSeekStep", () => {
  it("is idle with nothing pending", () => {
    expect(consoleSeekStep({ pendingSeconds: null, inFlight: false }, quiet)).toBe("idle");
  });

  it("sends the pending move when the console is quiet", () => {
    expect(consoleSeekStep({ pendingSeconds: 82.4, inFlight: false }, quiet)).toBe("send");
  });

  it("waits while a move is in flight", () => {
    expect(consoleSeekStep({ pendingSeconds: 82.4, inFlight: true }, quiet)).toBe("wait");
  });

  it("waits while a stop is pending, so the server does not answer busy", () => {
    expect(consoleSeekStep({ pendingSeconds: 82.4, inFlight: false }, { stopping: true, awaiting: false })).toBe(
      "wait",
    );
  });

  it("waits while a play request is awaiting its answer", () => {
    expect(consoleSeekStep({ pendingSeconds: 82.4, inFlight: false }, { stopping: false, awaiting: true })).toBe(
      "wait",
    );
  });
});

describe("consoleTimecodeSeconds", () => {
  it("adds the measured console-to-audio delay, because the console runs ahead of the audio", () => {
    expect(consoleTimecodeSeconds(82.4, 3)).toBeCloseTo(85.4);
  });

  it("refuses to invent a timecode when the delay is not measured", () => {
    expect(consoleTimecodeSeconds(82.4, null)).toBeNull();
    expect(consoleTimecodeSeconds(82.4, Number.NaN)).toBeNull();
  });

  it("never goes below the top of the timeline", () => {
    expect(consoleTimecodeSeconds(0, -5)).toBe(0);
  });
});

describe("consoleResyncDue", () => {
  const playingFollow = {
    playing: true,
    consoleFollow: true,
    consoleFollowAvailable: true,
    inFlight: false,
    pending: false,
    awaiting: false,
    stopping: false,
  };

  it("is due while playing with 콘솔 같이 on and nothing else in progress", () => {
    expect(consoleResyncDue(playingFollow)).toBe(true);
  });

  it("is not due when stopped, when 콘솔 같이 is off, or when a move is pending or in flight", () => {
    expect(consoleResyncDue({ ...playingFollow, playing: false })).toBe(false);
    expect(consoleResyncDue({ ...playingFollow, consoleFollow: false })).toBe(false);
    expect(consoleResyncDue({ ...playingFollow, pending: true })).toBe(false);
    expect(consoleResyncDue({ ...playingFollow, inFlight: true })).toBe(false);
    expect(consoleResyncDue({ ...playingFollow, stopping: true })).toBe(false);
  });
});

describe("buildBeatGridConsoleSeek", () => {
  it("carries the bar's seconds to the server", () => {
    expect(JSON.parse(buildBeatGridConsoleSeek(82.4))).toMatchObject({
      type: "beat_grid_console_seek",
      seconds: 82.4,
    });
  });
});
