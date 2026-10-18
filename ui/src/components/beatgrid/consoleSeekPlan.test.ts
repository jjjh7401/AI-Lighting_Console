import { describe, expect, it } from "vitest";

import { buildBeatGridConsoleSeek } from "../../protocol";
import { consoleSeekPlan, consoleSeekStep } from "./consoleSeekPlan";

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

  it("pauses first when a bar is moved during playback", () => {
    expect(consoleSeekPlan({ ...paused, playing: true, timecodePaused: false })).toBe("pause_then_seek");
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

describe("buildBeatGridConsoleSeek", () => {
  it("carries the bar's seconds to the server", () => {
    expect(JSON.parse(buildBeatGridConsoleSeek(82.4))).toMatchObject({
      type: "beat_grid_console_seek",
      seconds: 82.4,
    });
  });
});
