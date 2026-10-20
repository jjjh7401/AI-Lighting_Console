// 마디 지도 진입 컨트롤의 순수 상태 리듀서 시험 (SPEC-LDBARMAP-003, 카드 t648).
//
// 이 프로젝트에는 DOM 시험대가 없다(spec.md §4 「시험 방식」). 그래서 상태 전이는
// 전부 순수 함수 `barMapEntryReducer` 로 모았고, 여기서는 이벤트를 차례로 먹여
// 결과 상태를 본다. 클릭과 실제 소켓은 자동 시험 대상이 아니다(plan.md §4).
//
// 기대 문구는 spec.md §4 「문구 고정표」의 글자 그대로다 — 상수를 import 해서
// 비교하지 않고 리터럴로 적는다(상수가 틀리면 시험도 같이 틀려 버리기 때문이다).
//
// 곡 파일명은 가짜 이름 `sample-track.wav` 만 쓴다.
import { describe, expect, it } from "vitest";

import {
  barMapEntryReducer,
  initialBarMapEntryState,
  isOffMeter,
  type BarMapEntryEvent,
  type BarMapEntryState,
} from "./barMapEntryState";

const SONG = "sample-track.wav";

const TEXT_SAVED_WITH_NAME = "곡 «sample-track.wav» 마디 지도를 초안에 저장했습니다.";
const TEXT_SAVED_NO_NAME = "마디 지도를 초안에 저장했습니다.";
const TEXT_AUDIO_MISSING = "곡 오디오를 먼저 첨부해 주세요.";
const TEXT_PROTOCOL = "분석 요청 형식이 맞지 않아 시작하지 못했습니다.";
const TEXT_NOT_CONNECTED = "연결되어 있지 않아 분석을 시작하지 못했습니다.";
const TEXT_SOCKET_CLOSED = "연결이 끊겨 분석 결과를 받지 못했을 수 있습니다.";
const TEXT_CANCELLED = "취소했습니다. 서버의 분석은 계속될 수 있으며, 끝나면 이 자리에 결과가 표시됩니다.";

/** 이벤트를 차례로 먹인다. 시작 상태를 안 주면 초기 상태에서 시작한다. */
function run(
  events: BarMapEntryEvent[],
  from: BarMapEntryState = initialBarMapEntryState,
): BarMapEntryState {
  return events.reduce(barMapEntryReducer, from);
}

const select = (offset: number | null): BarMapEntryEvent => ({ type: "offset-selected", offset });
const sent = (songName: string | null = SONG): BarMapEntryEvent => ({ type: "sent", songName });
const saved: BarMapEntryEvent = { type: "chat-response", summary: "마디 지도 저장", text: "서버 원문" };
const rejected = (summary: string, text = "시험용 사유 문장"): BarMapEntryEvent => ({
  type: "chat-response",
  summary,
  text,
});
const errorOf = (kind: string): BarMapEntryEvent => ({ type: "error", kind });

/** 오프셋 2를 골라 요청을 보낸 뒤의 대기 상태. */
function waiting(songName: string | null = SONG): BarMapEntryState {
  return run([select(2), sent(songName)]);
}

describe("AC-LDBARUI-002: initial state has no default offset", () => {
  it("AC-LDBARUI-002: starts idle with an empty selection, no notice, no song name", () => {
    expect(initialBarMapEntryState).toEqual({
      phase: "idle",
      offset: null,
      songName: null,
      notice: null,
    });
  });

  it("AC-LDBARUI-002: the selection is empty until the user picks, then holds the pick (0 included)", () => {
    expect(run([]).offset).toBeNull();
    expect(run([select(0)]).offset).toBe(0);
    expect(run([select(3)]).offset).toBe(3);
    expect(run([select(3), select(null)]).offset).toBeNull();
  });
});

describe("AC-LDBARUI-003: off-meter rule", () => {
  it("AC-LDBARUI-003: isOffMeter is true for a timeline meter other than 4/4", () => {
    expect(isOffMeter("3/4")).toBe(true);
    expect(isOffMeter("6/8")).toBe(true);
  });

  it("AC-LDBARUI-003: isOffMeter is false for 4/4 (whitespace ignored), null, undefined, and empty", () => {
    expect(isOffMeter("4/4")).toBe(false);
    expect(isOffMeter(" 4 / 4 ")).toBe(false);
    expect(isOffMeter(null)).toBe(false);
    expect(isOffMeter(undefined)).toBe(false);
    expect(isOffMeter("")).toBe(false);
    expect(isOffMeter("   ")).toBe(false);
  });
});

describe("AC-LDBARUI-004: entering the waiting state", () => {
  it("AC-LDBARUI-004: idle + sent becomes waiting and remembers the song name at request time", () => {
    const next = run([select(2), sent()]);
    expect(next.phase).toBe("waiting");
    expect(next.songName).toBe(SONG);
  });

  it("AC-LDBARUI-004: not-connected keeps the state idle and shows the not-connected line exactly", () => {
    const next = run([select(2), { type: "not-connected" }]);
    expect(next.phase).toBe("idle");
    expect(next.notice).toBe(TEXT_NOT_CONNECTED);
  });
});

describe("AC-LDBARUI-005: waiting ends only by result, error, socket close, or cancel", () => {
  it("AC-LDBARUI-005: cancel ends waiting with the exact cancel line", () => {
    const next = barMapEntryReducer(waiting(), { type: "cancel" });
    expect(next.phase).toBe("idle");
    expect(next.notice).toBe(TEXT_CANCELLED);
  });

  it("AC-LDBARUI-005: socket-closed ends waiting with the exact disconnect line", () => {
    const next = barMapEntryReducer(waiting(), { type: "socket-closed" });
    expect(next.phase).toBe("idle");
    expect(next.notice).toBe(TEXT_SOCKET_CLOSED);
  });

  it("AC-LDBARUI-005: busy does not end waiting", () => {
    const next = barMapEntryReducer(waiting(), { type: "busy", message: "처리 중" });
    expect(next.phase).toBe("waiting");
  });

  it("AC-LDBARUI-005: a result, an error kind of ours, socket close, and cancel each end waiting; busy and unrelated events do not", () => {
    const enders: BarMapEntryEvent[] = [
      saved,
      rejected("마디 지도 분석 거절"),
      errorOf("song_audio_missing"),
      { type: "socket-closed" },
      { type: "cancel" },
    ];
    for (const ender of enders) {
      expect(barMapEntryReducer(waiting(), ender).phase, JSON.stringify(ender)).toBe("idle");
    }
    const keepers: BarMapEntryEvent[] = [
      { type: "busy", message: "처리 중" },
      errorOf("connection"),
      rejected("일반 답변"),
    ];
    for (const keeper of keepers) {
      expect(barMapEntryReducer(waiting(), keeper).phase, JSON.stringify(keeper)).toBe("waiting");
    }
  });

  it("AC-LDBARUI-005: while idle, cancel and socket-closed change neither the state nor the notice (fresh state)", () => {
    expect(barMapEntryReducer(initialBarMapEntryState, { type: "cancel" })).toEqual(initialBarMapEntryState);
    expect(barMapEntryReducer(initialBarMapEntryState, { type: "socket-closed" })).toEqual(
      initialBarMapEntryState,
    );
  });

  it("AC-LDBARUI-005: while idle with an earlier notice on screen, cancel and socket-closed leave that notice alone", () => {
    const idleWithNotice = run([select(2), sent(), saved]);
    expect(idleWithNotice.phase).toBe("idle");
    expect(idleWithNotice.notice).toBe(TEXT_SAVED_WITH_NAME);
    expect(barMapEntryReducer(idleWithNotice, { type: "cancel" })).toEqual(idleWithNotice);
    expect(barMapEntryReducer(idleWithNotice, { type: "socket-closed" })).toEqual(idleWithNotice);
  });
});

describe("AC-LDBARUI-006: save result", () => {
  it("AC-LDBARUI-006: with a file name the notice is the exact fixed line and waiting ends", () => {
    const next = barMapEntryReducer(waiting(SONG), saved);
    expect(next.notice).toBe(TEXT_SAVED_WITH_NAME);
    expect(next.phase).toBe("idle");
  });

  it("AC-LDBARUI-006: without a file name the notice is the nameless fixed line", () => {
    const next = barMapEntryReducer(waiting(null), saved);
    expect(next.notice).toBe(TEXT_SAVED_NO_NAME);
    expect(next.phase).toBe("idle");
  });

  it("AC-LDBARUI-006: the shown line is the fixed copy, not the server text", () => {
    const next = barMapEntryReducer(waiting(SONG), {
      type: "chat-response",
      summary: "마디 지도 저장",
      text: "서버가 보낸 다른 문장",
    });
    expect(next.notice).toBe(TEXT_SAVED_WITH_NAME);
  });

  it("AC-LDBARUI-006: a late result after cancel is still shown with the same line, and stays idle", () => {
    const cancelled = run([select(2), sent(), { type: "cancel" }]);
    expect(cancelled.phase).toBe("idle");
    expect(cancelled.notice).toBe(TEXT_CANCELLED);
    const late = barMapEntryReducer(cancelled, saved);
    expect(late.notice).toBe(TEXT_SAVED_WITH_NAME);
    expect(late.phase).toBe("idle");
  });

  it("AC-LDBARUI-006: the result line never carries the offset", () => {
    for (const offset of [0, 1, 2, 3]) {
      const next = run([select(offset), sent(), saved]);
      expect(next.notice).toBe(TEXT_SAVED_WITH_NAME);
      expect(next.notice).not.toContain("오프셋");
    }
  });

  it("AC-LDBARUI-006: a result replaces an earlier busy notice", () => {
    const busy = barMapEntryReducer(waiting(), { type: "busy", message: "처리 중" });
    expect(busy.notice).toBe("처리 중");
    expect(barMapEntryReducer(busy, saved).notice).toBe(TEXT_SAVED_WITH_NAME);
  });
});

describe("AC-LDBARUI-007: rejection labels show the server text verbatim", () => {
  const LABELS = ["마디 지도 분석 거절", "마디 지도 저장 거절", "마디 지도 저장 불가"];

  it.each(LABELS)("AC-LDBARUI-007: while waiting, %s shows the server text and ends waiting", (label) => {
    const next = barMapEntryReducer(waiting(), rejected(label));
    expect(next.notice).toBe("시험용 사유 문장");
    expect(next.phase).toBe("idle");
  });

  it.each(LABELS)("AC-LDBARUI-007: after cancel, a late %s is shown the same way and stays idle", (label) => {
    const cancelled = run([select(2), sent(), { type: "cancel" }]);
    const late = barMapEntryReducer(cancelled, rejected(label));
    expect(late.notice).toBe("시험용 사유 문장");
    expect(late.phase).toBe("idle");
  });

  it("AC-LDBARUI-007: the server text is shown as sent — the client invents no reason", () => {
    const next = barMapEntryReducer(waiting(), rejected("마디 지도 분석 거절", "범위 밖 오프셋: 7"));
    expect(next.notice).toBe("범위 밖 오프셋: 7");
  });

  it("AC-LDBARUI-007: an unrelated summary leaves state and notice unchanged (waiting and idle)", () => {
    const w = waiting();
    expect(barMapEntryReducer(w, rejected("일반 답변"))).toEqual(w);
    expect(barMapEntryReducer(initialBarMapEntryState, rejected("일반 답변"))).toEqual(
      initialBarMapEntryState,
    );
  });
});

// 확정 분석이 있으면 서버는 마디 지도를 옛 작업본에 붙이지 않고 새 작업본을 연다
// (`session.py` `_start_analysis_timeline`, 리드 지시 2026-10-16). 그 길의 끝 응답 두 개도
// 대기를 끝내야 한다 — 2026-10-20 실측에서 「새 분석으로 새 작업본」이 25초 만에 왔는데도
// 화면은 300초 넘게 「분석 중」에 머물렀다.
describe("새 작업본 길의 끝 응답도 대기를 끝낸다", () => {
  const LABELS = ["새 분석으로 새 작업본", "새 분석 작업본 만들기 실패"];

  it.each(LABELS)("대기 중에 %s 가 오면 서버 문장을 보이고 대기를 끝낸다", (label) => {
    const next = barMapEntryReducer(waiting(), rejected(label, "서버가 보낸 결과 문장"));
    expect(next.phase).toBe("idle");
    expect(next.notice).toBe("서버가 보낸 결과 문장");
  });

  it.each(LABELS)("「취소」 뒤에 늦게 온 %s 도 같은 모양으로 보이고 idle 에 머문다", (label) => {
    const cancelled = run([select(2), sent(), { type: "cancel" }]);
    const late = barMapEntryReducer(cancelled, rejected(label, "서버가 보낸 결과 문장"));
    expect(late.phase).toBe("idle");
    expect(late.notice).toBe("서버가 보낸 결과 문장");
  });
});

describe("AC-LDBARUI-008: error kinds", () => {
  it("AC-LDBARUI-008: song_audio_missing while waiting shows the attach-audio line and ends waiting", () => {
    const next = barMapEntryReducer(waiting(), errorOf("song_audio_missing"));
    expect(next.notice).toBe(TEXT_AUDIO_MISSING);
    expect(next.phase).toBe("idle");
  });

  it("AC-LDBARUI-008: protocol while waiting shows the bad-format line and ends waiting", () => {
    const next = barMapEntryReducer(waiting(), errorOf("protocol"));
    expect(next.notice).toBe(TEXT_PROTOCOL);
    expect(next.phase).toBe("idle");
  });

  it("AC-LDBARUI-008: any other error kind is ignored while waiting", () => {
    const w = waiting();
    for (const kind of ["connection", "internal", "rate_limit", ""]) {
      expect(barMapEntryReducer(w, errorOf(kind)), kind).toEqual(w);
    }
  });

  it("AC-LDBARUI-008: while idle, even our two kinds change neither state nor notice", () => {
    expect(barMapEntryReducer(initialBarMapEntryState, errorOf("song_audio_missing"))).toEqual(
      initialBarMapEntryState,
    );
    expect(barMapEntryReducer(initialBarMapEntryState, errorOf("protocol"))).toEqual(
      initialBarMapEntryState,
    );
    const idleWithNotice = run([select(2), sent(), saved]);
    expect(barMapEntryReducer(idleWithNotice, errorOf("song_audio_missing"))).toEqual(idleWithNotice);
    expect(barMapEntryReducer(idleWithNotice, errorOf("protocol"))).toEqual(idleWithNotice);
  });
});

describe("AC-LDBARUI-009: busy", () => {
  it("AC-LDBARUI-009: while waiting, busy shows the message as the notice and keeps waiting", () => {
    const next = barMapEntryReducer(waiting(), { type: "busy", message: "처리 중" });
    expect(next.notice).toBe("처리 중");
    expect(next.phase).toBe("waiting");
  });

  it("AC-LDBARUI-009: while idle, busy changes neither state nor notice (fresh state and with an earlier notice)", () => {
    const busy: BarMapEntryEvent = { type: "busy", message: "처리 중" };
    expect(barMapEntryReducer(initialBarMapEntryState, busy)).toEqual(initialBarMapEntryState);
    const idleWithNotice = run([select(2), sent(), saved]);
    expect(barMapEntryReducer(idleWithNotice, busy)).toEqual(idleWithNotice);
  });
});
