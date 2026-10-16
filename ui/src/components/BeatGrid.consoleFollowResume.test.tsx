// @vitest-environment jsdom
// 「콘솔 같이」 음원 이어 트기 시험 — 전체화면을 닫았다 다시 열어도 콘솔 재생 응답 뒤의 음원 시작이 이어지는가.
//
// 감독의 실제 순서: 「콘솔 같이」 + ▶ → 승인 카드 → 채팅에서 승인하려고 전체화면을 닫음(`BeatGrid` 가
// 사라진다) → 서버가 콘솔 재생 응답을 보냄 → 한참 뒤 전체화면을 다시 엶. 예전에는 응답을 받아 줄 화면이
// 없었고, 다시 열린 화면은 「눌렀다」는 사실을 몰라 음원이 0초에 멈춰 있었다.
//
// 이 시험은 `App` 의 배선을 `createApp` 으로 그대로 흉내 낸다 — 응답이 오면 ① 먼저 새 응답으로 화면을
// 그리고(자식 effect 가 부모 effect 보다 먼저 돈다) ② `observeConsoleFollowStatus` 로 기록한 뒤 ③ 순번을
// 올려 한 번 더 그린다. 중계 객체와 응답·순번은 `BeatGrid` 가 사라져도 `createApp` 에 남는다(`App` 상태와
// 같다). 시계는 가짜(`Date`·타이머)이고 `requestAnimationFrame` 은 손으로만 돌린다 — 시험은 동기이고
// 실제 시간이 끼어들지 않는다. 음원 재생(`play`/`pause`)은 jsdom 에 없어서 막아 두고 부른 횟수를 본다.
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { BeatGridSendStatus, BeatGridView } from "../protocol";
import { BeatGrid, type BeatGridProps } from "./BeatGrid";
import {
  CONSOLE_DELAY_MISSING_MESSAGE,
  CONSOLE_NO_SONG_AUDIO_MESSAGE,
  createConsoleFollowRelay,
  observeConsoleFollowStatus,
} from "./beatgrid/consoleFollowRelay";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

/** 실측 지연(초)을 정수로 둔다 — 시험이 타이머를 딱 맞춰 넘기려고(실제 값은 서버 데이터 파일 것이다). */
const DELAY_SECONDS = 3;

function gridWithDelay(delay: number | null): BeatGridView {
  return {
    song_title: "LOVE ATTACK",
    bar_range: { start: 0, end: 25 },
    tracks: [],
    scene_memos: [],
    probe_results: {},
    source: "empty",
    note: null,
    console_audio_offset_seconds: delay,
  };
}

let container: HTMLElement;
let root: Root;
let media: ReturnType<typeof stubMedia>;
let frames: Map<number, FrameRequestCallback>;

/** jsdom 은 `play`/`pause` 를 구현하지 않는다(호출하면 "not implemented"). 막고 부른 횟수만 본다. */
function stubMedia() {
  const play = vi.spyOn(HTMLMediaElement.prototype, "play").mockResolvedValue(undefined);
  const pause = vi.spyOn(HTMLMediaElement.prototype, "pause").mockImplementation(() => undefined);
  return { play, pause };
}

const urlApi = URL as unknown as { createObjectURL?: (blob: Blob) => string };

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date("2026-10-16T12:00:00Z"));
  media = stubMedia();
  // 재생 시계(RAF)는 손으로만 돌린다 — 시험 사이에 진짜 프레임이 끼어들지 않는다.
  frames = new Map();
  let frameId = 0;
  vi.stubGlobal("requestAnimationFrame", (callback: FrameRequestCallback) => {
    frameId += 1;
    frames.set(frameId, callback);
    return frameId;
  });
  vi.stubGlobal("cancelAnimationFrame", (id: number) => {
    frames.delete(id);
  });
  // 음원 파일을 붙이는 시험용 — jsdom 에는 `URL.createObjectURL` 이 없다.
  urlApi.createObjectURL = () => "blob:test";
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(() => {
  act(() => root.unmount());
  container.remove();
  delete urlApi.createObjectURL;
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  vi.useRealTimers();
});

/** 응답마다 새 객체 — 리듀서의 REPLACE 와 같다. */
function status(overrides: Partial<BeatGridSendStatus> = {}): BeatGridSendStatus {
  return {
    pending_apply_count: 0,
    last_action: "console_play",
    ok: true,
    reason: null,
    blocked_cells: [],
    approval_vs_sent: null,
    ...overrides,
  };
}

interface AppOptions {
  grid?: BeatGridView;
  props?: Partial<BeatGridProps>;
}

/** `App` 흉내 — 중계 객체·응답·순번은 `BeatGrid` 가 사라져도 남는다. */
function createApp(options: AppOptions = {}) {
  const grid = options.grid ?? gridWithDelay(DELAY_SECONDS);
  const relay = createConsoleFollowRelay();
  const onConsolePlay = vi.fn();
  const onConsoleStop = vi.fn();
  let sendStatus: BeatGridSendStatus | null = null;
  let seq = 0;
  let shown = false;
  const draw = () => {
    act(() => {
      root.render(
        shown ? (
          <BeatGrid
            grid={grid}
            consoleFollowRelay={relay}
            consoleFollowSeq={seq}
            sendStatus={sendStatus}
            onConsolePlay={onConsolePlay}
            onConsoleStop={onConsoleStop}
            {...options.props}
          />
        ) : null,
      );
    });
  };
  return {
    relay,
    onConsolePlay,
    onConsoleStop,
    /** 전체화면을 연다 — 새 `BeatGrid` 인스턴스가 마운트된다. */
    open() {
      shown = true;
      draw();
    },
    /** 전체화면을 닫는다 — `BeatGrid` 가 사라진다. */
    close() {
      shown = false;
      draw();
    },
    /** 서버 응답 하나가 도착한다(화면이 열려 있든 닫혀 있든). */
    receive(next: BeatGridSendStatus) {
      sendStatus = next;
      draw();
      if (observeConsoleFollowStatus(relay, sendStatus, Date.now())) {
        seq += 1;
        draw();
      }
    },
  };
}

type TestApp = ReturnType<typeof createApp>;

function headerButton(textPart: string): HTMLButtonElement {
  const found = Array.from(container.querySelectorAll("header.beat-grid-topbar button")).find((button) =>
    (button.textContent ?? "").includes(textPart),
  );
  if (!found) throw new Error(`header button not found: ${textPart}`);
  return found as HTMLButtonElement;
}

const consoleFollowToggle = () => headerButton("콘솔 같이");
const playButton = () => {
  const found = container.querySelector<HTMLButtonElement>('header.beat-grid-topbar button[title^="재생 / 일시정지"]');
  if (!found) throw new Error("play button not found");
  return found;
};
const audioEl = () => {
  const found = container.querySelector("audio");
  if (!found) throw new Error("audio element not found");
  return found;
};

const click = (button: HTMLButtonElement) => act(() => button.click());
const advance = (ms: number) =>
  act(() => {
    vi.advanceTimersByTime(ms);
  });
/** 음원이 연결됐다(`canplay`) — `BeatGrid` 의 `onCanPlay` 가 `connected` 로 바꾼다. */
const connectAudio = () => act(() => void audioEl().dispatchEvent(new Event("canplay")));
/** 손으로 RAF 한 프레임을 돌린다. */
const runFrame = () => {
  const pending = Array.from(frames.values());
  frames.clear();
  act(() => {
    for (const callback of pending) callback(performance.now());
  });
};
/** 상단 바에 보이는 오류 문구들(콘솔 같이 오류·음원 실패 이유). */
const errorTexts = () =>
  Array.from(container.querySelectorAll(".beat-grid-audio-error")).map((el) => el.textContent ?? "");

/** 「콘솔 같이」를 켜고 ▶ 를 눌러 서버 요청을 한 번 보낸다. */
function pressPlayWithConsoleFollow(app: TestApp) {
  click(consoleFollowToggle());
  click(playButton());
  expect(app.relay.awaiting).toBe(true);
}

describe("(1)~(7) 전체화면을 닫았다 열어도 콘솔 재생 뒤 음원이 이어진다", () => {
  it("(1) 보통: 연결된 채 켜고 ▶ → 응답 → 지연 뒤 음원을 정확히 한 번 튼다", () => {
    const app = createApp();
    app.open();
    connectAudio();

    click(consoleFollowToggle());
    expect(consoleFollowToggle().getAttribute("aria-pressed")).toBe("true");
    click(playButton());
    expect(app.onConsolePlay).toHaveBeenCalledTimes(1);

    app.receive(status());
    expect(media.play).not.toHaveBeenCalled(); // 아직 지연 안이다
    advance(DELAY_SECONDS * 1000 - 1);
    expect(media.play).not.toHaveBeenCalled(); // 1ms 전
    advance(1);
    expect(media.play).toHaveBeenCalledTimes(1);
    expect(playButton().textContent).toBe("❚❚ 일시정지");
    expect(audioEl().currentTime).toBe(0);
    // 새 콘솔 요청도 정지도 자동으로 보내지 않는다.
    expect(app.onConsolePlay).toHaveBeenCalledTimes(1);
    expect(app.onConsoleStop).not.toHaveBeenCalled();
  });

  it("(2) 응답이 음원 연결보다 먼저: 지연 뒤에도 틀지 않다가 연결되는 순간 정확히 한 번 튼다", () => {
    const app = createApp();
    app.open(); // 음원은 아직 연결 전이다(canplay 없음)
    pressPlayWithConsoleFollow(app);

    app.receive(status());
    advance(DELAY_SECONDS * 1000);
    expect(media.play).not.toHaveBeenCalled();
    expect(playButton().textContent).toBe("▶ 재생"); // 소리 없이 재생 중인 척하지 않는다

    connectAudio();
    expect(media.play).toHaveBeenCalledTimes(1);
    expect(playButton().textContent).toBe("❚❚ 일시정지");
    expect(app.onConsolePlay).toHaveBeenCalledTimes(1);
  });

  it("(3) 지연을 기다리는 중에 화면을 닫았다 다시 열어도 지연이 끝나면 정확히 한 번 튼다", () => {
    const app = createApp();
    app.open();
    connectAudio();
    pressPlayWithConsoleFollow(app);
    app.receive(status());

    advance(1000); // 지연 3초 가운데 1초
    app.close();
    advance(500); // 닫힌 동안은 아무도 틀지 않는다
    expect(media.play).not.toHaveBeenCalled();

    app.open(); // 새 인스턴스 — 같은 중계 객체
    connectAudio(); // 이 시점에 지연은 1.5초 남았다
    expect(media.play).not.toHaveBeenCalled();
    advance(1499);
    expect(media.play).not.toHaveBeenCalled();
    advance(1);
    expect(media.play).toHaveBeenCalledTimes(1);
    expect(playButton().textContent).toBe("❚❚ 일시정지");
    // 새로 마운트된 화면은 콘솔 요청을 다시 보내지 않는다.
    expect(app.onConsolePlay).toHaveBeenCalledTimes(1);
  });

  it("(4) 음원이 시작된 뒤 닫았다 열면 지금 자리(응답 12초 뒤 = 12-지연)에서 정확히 한 번 튼다", () => {
    const app = createApp();
    app.open();
    connectAudio();
    pressPlayWithConsoleFollow(app);
    app.receive(status());
    advance(DELAY_SECONDS * 1000);
    expect(media.play).toHaveBeenCalledTimes(1); // 첫 인스턴스가 틀었다

    app.close(); // 닫으면 음원 엘리먼트도 사라져 멈춘다
    advance(12_000 - DELAY_SECONDS * 1000); // 응답 뒤 12초가 지난다
    const callsBeforeReopen = media.play.mock.calls.length;

    app.open();
    connectAudio();
    expect(media.play.mock.calls.length - callsBeforeReopen).toBe(1);
    expect(audioEl().currentTime).toBeGreaterThan(12 - DELAY_SECONDS - 0.1);
    expect(audioEl().currentTime).toBeLessThan(12 - DELAY_SECONDS + 0.1);
    expect(playButton().textContent).toBe("❚❚ 일시정지");
    expect(app.onConsolePlay).toHaveBeenCalledTimes(1);

    // 같은 마운트에서 다시 확인이 일어나도(다른 응답이 와서 화면이 다시 확인한다) 두 번 틀지 않는다.
    app.receive(status({ last_action: "preview" }));
    advance(5000);
    expect(media.play.mock.calls.length - callsBeforeReopen).toBe(1);
  });

  it("(5) 마운트 때 이미 있던 옛 콘솔 재생 응답으로는 틀지도 요청하지도 않는다", () => {
    const app = createApp();
    const old = status();
    app.receive(old); // 기다리는 중이 아니었다 — 기록되지 않는다
    expect(app.relay.responseAtMs).toBeNull();

    app.open();
    connectAudio();
    advance(30_000);
    expect(media.play).not.toHaveBeenCalled();
    expect(app.onConsolePlay).not.toHaveBeenCalled();
    expect(playButton().textContent).toBe("▶ 재생");

    // 대조군: 눌러서 온 새 응답은 같은 화면에서 튼다 — 위 단언이 효과가 죽어서 통과한 것이 아님을 보인다.
    pressPlayWithConsoleFollow(app);
    app.receive(status());
    advance(DELAY_SECONDS * 1000);
    expect(media.play).toHaveBeenCalledTimes(1);
  });

  it("(6) 서버가 거절하면 이유를 보이고 음원은 틀지 않는다", () => {
    const app = createApp();
    app.open();
    connectAudio();
    pressPlayWithConsoleFollow(app);

    app.receive(status({ ok: false, reason: "반영 기록 없음" }));
    expect(errorTexts()).toContain("반영 기록 없음");
    advance(60_000);
    expect(media.play).not.toHaveBeenCalled();
    expect(app.relay.responseAtMs).toBeNull();
    expect(playButton().textContent).toBe("▶ 재생");
  });

  it("(7) 일시정지(❚❚) 뒤에는 닫았다 열어도 아무것도 이어 틀지 않는다", () => {
    const app = createApp();
    app.open();
    connectAudio();
    pressPlayWithConsoleFollow(app);
    app.receive(status());
    advance(DELAY_SECONDS * 1000);
    expect(media.play).toHaveBeenCalledTimes(1);

    click(playButton()); // ❚❚
    expect(app.onConsoleStop).toHaveBeenCalledTimes(1);
    expect(media.pause).toHaveBeenCalled();
    expect(playButton().textContent).toBe("▶ 재생");
    expect(app.relay.responseAtMs).toBeNull();

    app.close();
    advance(20_000);
    app.open();
    connectAudio();
    advance(20_000);
    expect(media.play).toHaveBeenCalledTimes(1); // 처음 한 번뿐
    expect(playButton().textContent).toBe("▶ 재생");
    expect(app.onConsolePlay).toHaveBeenCalledTimes(1);
  });
});

describe("감독의 실제 순서 — 닫은 사이에 응답이 온다", () => {
  it("▶ → 전체화면을 닫고 승인 → 응답(화면 없음) → 12초 뒤 다시 열면 12-지연 자리에서 튼다", () => {
    const app = createApp();
    app.open();
    connectAudio();
    pressPlayWithConsoleFollow(app);

    app.close(); // 채팅에서 승인하려고 닫는다
    app.receive(status()); // 받아 줄 `BeatGrid` 가 없다 — `App` 이 기록한다
    expect(app.relay.responseAtMs).not.toBeNull();
    expect(app.relay.awaiting).toBe(false);
    advance(12_000);
    expect(media.play).not.toHaveBeenCalled();

    app.open();
    expect(consoleFollowToggle().getAttribute("aria-pressed")).toBe("true"); // 켠 의도가 남아 있다
    connectAudio();
    expect(media.play).toHaveBeenCalledTimes(1);
    expect(audioEl().currentTime).toBeGreaterThan(12 - DELAY_SECONDS - 0.1);
    expect(audioEl().currentTime).toBeLessThan(12 - DELAY_SECONDS + 0.1);
    expect(app.onConsolePlay).toHaveBeenCalledTimes(1); // 새 요청은 없다
  });

  it("닫은 사이에 거절 응답이 오면 다시 열 때 그 이유가 보이고 음원은 틀지 않는다", () => {
    const app = createApp();
    app.open();
    connectAudio();
    pressPlayWithConsoleFollow(app);
    app.close();
    app.receive(status({ ok: false, reason: "감독이 미리보기 승인을 거절했습니다." }));

    app.open();
    connectAudio();
    advance(60_000);
    expect(errorTexts()).toContain("감독이 미리보기 승인을 거절했습니다.");
    expect(media.play).not.toHaveBeenCalled();

    // 다시 누르면 이전 거절 이유는 지워지고 새 요청이 나간다.
    click(playButton());
    expect(errorTexts()).not.toContain("감독이 미리보기 승인을 거절했습니다.");
    expect(app.onConsolePlay).toHaveBeenCalledTimes(2);
  });
});

describe("경계 — 지연 값·음원 없음·끝난 곡", () => {
  it("지연 측정값이 없으면 안내를 보이고 기록을 지운다 — 음원은 틀지 않는다", () => {
    const app = createApp({ grid: gridWithDelay(null) });
    app.open();
    connectAudio();
    pressPlayWithConsoleFollow(app);

    app.receive(status());
    expect(errorTexts()).toContain(CONSOLE_DELAY_MISSING_MESSAGE);
    expect(app.relay.responseAtMs).toBeNull();
    advance(60_000);
    expect(media.play).not.toHaveBeenCalled();
  });

  it("틀 때가 됐는데 이 곡에 연결된 음원이 아예 없으면 그렇게 말하고, 불러오는 중에는 말하지 않는다", () => {
    // 음원이 하나도 안 붙은 곡 — 말한다.
    const bare = createApp();
    bare.open();
    pressPlayWithConsoleFollow(bare);
    bare.receive(status());
    expect(errorTexts()).not.toContain(CONSOLE_NO_SONG_AUDIO_MESSAGE); // 아직 지연 안이다
    advance(DELAY_SECONDS * 1000);
    expect(errorTexts()).toContain(CONSOLE_NO_SONG_AUDIO_MESSAGE);
    expect(media.play).not.toHaveBeenCalled();
    expect(bare.relay.responseAtMs).not.toBeNull(); // 음원이 뒤늦게 붙으면 이어 틀 수 있게 남겨 둔다
    bare.close();

    // 음원 파일이 붙어 불러오는 중 — 곧 올 음원이라 말하지 않고, 연결되면 튼다.
    const withFile = createApp({ props: { attachedSongAudioFile: new File(["x"], "song.mp3") } });
    withFile.open(); // 자동 연결이 시작돼 `loading` 이다
    pressPlayWithConsoleFollow(withFile);
    withFile.receive(status());
    advance(DELAY_SECONDS * 1000);
    expect(errorTexts()).not.toContain(CONSOLE_NO_SONG_AUDIO_MESSAGE);
    expect(media.play).not.toHaveBeenCalled();
    connectAudio();
    expect(media.play).toHaveBeenCalledTimes(1);
  });

  it("서버가 이 곡엔 저장된 음원 링크가 없다고 답한 곡(missing)에서도 음원이 없다고 말한다", () => {
    const app = createApp({ props: { songAudioLinkMissing: true } });
    app.open(); // 화면이 상태를 `missing`(음원 없음)으로 정한다
    expect(container.querySelector(".beat-grid-audio-label")?.textContent).toContain("음원 없음");
    pressPlayWithConsoleFollow(app);
    app.receive(status());
    advance(DELAY_SECONDS * 1000);
    expect(errorTexts()).toContain(CONSOLE_NO_SONG_AUDIO_MESSAGE);
    expect(media.play).not.toHaveBeenCalled();
  });

  it("음원이 없다던 안내는 음원이 나중에 연결돼 틀게 되면 사라진다", () => {
    const app = createApp();
    app.open();
    pressPlayWithConsoleFollow(app);
    app.receive(status());
    advance(DELAY_SECONDS * 1000);
    expect(errorTexts()).toContain(CONSOLE_NO_SONG_AUDIO_MESSAGE);

    connectAudio(); // 감독이 ♪ 음원으로 파일을 골랐다고 치자
    expect(media.play).toHaveBeenCalledTimes(1);
    expect(errorTexts()).not.toContain(CONSOLE_NO_SONG_AUDIO_MESSAGE);
  });

  it("다시 열었을 때 곡이 이미 끝났으면(자리 ≥ 음원 길이) 틀지 않고 기록을 거둔다", () => {
    const app = createApp();
    app.open();
    connectAudio();
    pressPlayWithConsoleFollow(app);
    app.receive(status());
    advance(DELAY_SECONDS * 1000);
    expect(media.play).toHaveBeenCalledTimes(1);

    app.close();
    advance(20_000); // 응답 뒤 23초 → 자리 20초
    app.open();
    expect(errorTexts()).toContain(CONSOLE_NO_SONG_AUDIO_MESSAGE); // 아직 연결 전이라 음원이 없다고 말하는 중이다
    Object.defineProperty(audioEl(), "duration", { configurable: true, get: () => 10 });
    connectAudio();
    expect(media.play).toHaveBeenCalledTimes(1); // 새로 틀지 않았다
    expect(app.relay.responseAtMs).toBeNull();
    expect(playButton().textContent).toBe("▶ 재생");
    expect(errorTexts()).not.toContain(CONSOLE_NO_SONG_AUDIO_MESSAGE); // 끝난 곡이라 그 안내도 거둔다
  });

  it("곡 끝에 닿으면 기록을 거두고, 다시 열어도 이어 틀지 않는다", () => {
    const app = createApp({ props: { secondsPerBar: 2 } }); // 25마디 × 2초 = 50초
    app.open();
    connectAudio();
    pressPlayWithConsoleFollow(app);
    app.receive(status());
    advance(DELAY_SECONDS * 1000);
    app.close();
    advance(60_000); // 응답 뒤 63초 → 자리 60초(곡 끝 50초를 넘었다)

    app.open();
    connectAudio();
    expect(media.play).toHaveBeenCalledTimes(2); // 새 마운트가 그 자리에서 튼다
    runFrame(); // 첫 프레임이 곡 끝을 알아챈다
    expect(playButton().textContent).toBe("▶ 재생");
    expect(media.pause).toHaveBeenCalled();
    expect(app.relay.responseAtMs).toBeNull();

    app.close();
    app.open();
    connectAudio();
    advance(10_000);
    expect(media.play).toHaveBeenCalledTimes(2); // 더 틀지 않았다
  });
});

describe("▶ 를 다시 누를 때와 켬/끔", () => {
  it("응답을 기다리는 중에 ▶ 를 또 눌러도 요청은 한 번뿐이다", () => {
    const app = createApp();
    app.open();
    connectAudio();
    pressPlayWithConsoleFollow(app);
    click(playButton());
    click(playButton());
    expect(app.onConsolePlay).toHaveBeenCalledTimes(1);
  });

  it("▶ 를 누를 때 화면에 있던 옛 응답이 같은 객체로 다시 와도 이번 요청의 답으로 치지 않는다", () => {
    const app = createApp();
    const old = status();
    app.receive(old); // 옛 응답 — 기다리는 중이 아니었다
    app.open();
    connectAudio();
    pressPlayWithConsoleFollow(app); // 누르는 순간 화면에 `old` 가 있다

    app.receive(old); // 같은 객체가 다시 보인다 — 새 응답이 아니다
    advance(60_000);
    expect(app.relay.awaiting).toBe(true);
    expect(app.relay.responseAtMs).toBeNull();
    expect(media.play).not.toHaveBeenCalled();

    app.receive(status()); // 새 객체가 와야 이번 요청의 답이다
    advance(DELAY_SECONDS * 1000);
    expect(media.play).toHaveBeenCalledTimes(1);
  });

  it("지연을 기다리는 중에 ▶ 를 다시 누르면 앞 시작 예약을 거두고 새 응답만 따른다", () => {
    const app = createApp();
    app.open();
    connectAudio();
    pressPlayWithConsoleFollow(app);
    app.receive(status());
    advance(1000);

    click(playButton()); // 다시 누름 — 콘솔 타임코드를 처음부터 다시 돌린다
    expect(app.onConsolePlay).toHaveBeenCalledTimes(2);
    expect(app.relay.responseAtMs).toBeNull();
    advance(10_000); // 옛 예약이 살아 있었다면 여기서 틀었을 것이다
    expect(media.play).not.toHaveBeenCalled();

    app.receive(status());
    advance(DELAY_SECONDS * 1000);
    expect(media.play).toHaveBeenCalledTimes(1);
  });

  it("「콘솔 같이」를 끄고 멈춰도 남은 콘솔 시작 시각이 지워져 다시 열어도 이어 틀지 않는다", () => {
    const app = createApp();
    app.open();
    connectAudio();
    pressPlayWithConsoleFollow(app);
    app.receive(status());
    advance(DELAY_SECONDS * 1000);
    expect(media.play).toHaveBeenCalledTimes(1);

    click(consoleFollowToggle()); // 끈다
    expect(consoleFollowToggle().getAttribute("aria-pressed")).toBe("false");
    click(playButton()); // 콘솔 같이를 끈 채 ❚❚ — 콘솔 정지는 보내지 않는다
    expect(app.onConsoleStop).not.toHaveBeenCalled();
    expect(app.relay.responseAtMs).toBeNull();

    app.close();
    app.open();
    connectAudio();
    advance(20_000);
    expect(media.play).toHaveBeenCalledTimes(1);
  });
});
