// 「콘솔 같이」 재생 중계 — 전체화면(`BeatGrid`)을 닫았다 다시 열어도 이어지는 의도와 시작 시각.
//
// 문제: `BeatGrid` 는 전체화면에서만 그려진다. ▶ 를 누르면 승인 카드가 뜨고, 감독은 채팅에서 승인하려고
// 전체화면을 닫는다 — 그 순간 `BeatGrid` 가 사라진다. 서버의 콘솔 재생 응답(`console_play`)이 그 사이에
// 오면 받아 줄 화면이 없고, 나중에 다시 열린 `BeatGrid` 는 새 인스턴스라 「눌렀다」는 사실을 모른다.
// 그래서 의도(켬/끔·응답 대기)와 콘솔이 시작된 시각을 이 객체에 담아 `App` 이 쥔다. 이 파일에는 순수
// 함수만 있다 — React 도, 송신도, 승인 호출도 없다(승인 카드는 감독이 직접 누르고, ▶ 도 늘 사람이 누른다).
//
// 객체는 일부러 가변이다. `App` 이 `useState` 초기값으로 한 번 만들어 계속 같은 참조를 쓰고, `BeatGrid` 가
// 읽고 쓴다. React 상태가 아니라서 바꿔도 다시 그려지지 않는다 — 응답을 기록한 뒤 화면에 다시 알리는 일은
// `App` 의 순번(`consoleFollowSeq`)이 맡는다.
import type { BeatGridSendStatus } from "../../protocol";

export interface ConsoleFollowRelay {
  /** 「콘솔 같이」 가 켜져 있는가. */
  consoleFollow: boolean;
  /** ▶ 를 눌러 서버의 콘솔 재생 응답을 기다리는 중인가. */
  awaiting: boolean;
  /** ▶ 를 누를 때 화면에 있던 응답 객체. 이것과 **다른** 객체가 와야 이번 요청의 답이다(앞 응답을 새 답으로
   * 오인하지 않는다). 그때 화면에 응답이 없었으면 `null`. */
  pressedAgainst: BeatGridSendStatus | null;
  /** 콘솔이 돌기 시작한 시각(`Date.now()`) — 서버가 실은 시작 시각, 없으면 성공 응답을 본 시각.
   * `null` 이면 이어 갈 콘솔 실행이 없다. */
  responseAtMs: number | null;
  /** 지금 마운트된 `BeatGrid` 가 이미 음원을 시작했는가(마운트마다 한 번만 튼다). */
  audioStarted: boolean;
  /** 서버가 거절한 이유 — 다음에 마운트되는 화면도 보이게 둔다. */
  failure: string | null;
  /** 콘솔 타임코드가 돌고 있을 수 있는가 — 재생 성공 응답에서 켜지고 **정지 성공 응답에서만** 꺼진다.
   * 정지는 승인 카드(`Off Timecode N`)를 따로 거치므로, 카드가 거절·만료되면 앱은 멈춰도 콘솔은 돈다
   * (2차 전체 실행 N11). 화면은 이 값으로 크게 알린다. 콘솔을 읽은 값이 아니라 보낸 명령의 결과다. */
  consoleMayRun: boolean;
  /** 위 판정에 쓴 마지막 응답 객체 — 같은 응답을 두 번 세지 않는다. */
  runStatusSeen: BeatGridSendStatus | null;
  /** ▶ 를 누를 때의 `busy` 횟수 — 그 뒤 늘면 이번 재생 요청이 `busy` 로 거절된 것이다(4차 전체 실행 H-10). */
  awaitingBusyAt: number;
  /** ❚❚ 로 콘솔 정지를 보내고 서버 답을 기다리는 중인가. 이 사이에 보낸 재생은 `busy` 로 거절된다. */
  stopping: boolean;
  /** ❚❚ 를 누를 때 화면에 있던 응답 객체와 `busy` 횟수 — 이것과 다른 응답이나 `busy` 가 오면 정지 처리는 끝났다. */
  stopPressedAgainst: BeatGridSendStatus | null;
  stopBusyAt: number;
  /** 정지 처리 중에 ▶ 가 눌렸다 — 정지가 끝나면 그 재생을 보낸다. */
  playQueued: boolean;
  /** PR 1 — ❚❚ 로 콘솔 타임코드를 멈춘 뒤 아직 이어 가지 않았는가. 참이면 다음 ▶ 는 처음으로 되감지 않고
   * `Go Timecode`만 보내 멈춘 자리부터 잇는다. 콘솔 재생이 성공하면 거둔다. 처음부터 재생·■ 끄기·곡 끝·⏮ 처음에서도 거둔다. */
  timecodePaused: boolean;
  /** PR 1 — 지금 콘솔 재생이 시작한 곡 위치(초). 처음부터 재생은 0, 이어 가기는 멈춘 자리다. 음원은 이 자리에서
   * 콘솔→음원 지연만큼 늦춰 튼다(`resumeConsoleAudio`). */
  startSeconds: number;
}

/** 재생 요청이 `busy` 로 거절됐을 때 보이는 문구. */
export const CONSOLE_PLAY_BUSY_MESSAGE = "앞 명령을 처리 중이라 콘솔 재생이 거절됐습니다 — ▶ 를 다시 눌러 주세요.";

/** 서버가 거절하면서 이유를 싣지 않았을 때 쓰는 문구. */
const CONSOLE_PLAY_REJECTED_FALLBACK = "콘솔 타임코드 재생이 거절됐습니다.";

/** 지연 측정값이 없으면 지연을 지어내지 않고 멈춘다(`resolveConsolePlayResponse` 의 같은 문구). */
export const CONSOLE_DELAY_MISSING_MESSAGE = "콘솔→음원 지연 측정값이 없어 음원을 맞춰 시작할 수 없습니다.";

/** 음원을 틀 때가 됐는데 이 곡에 연결된 음원이 아예 없을 때. 콘솔 타임코드는 이미 돌고 있다. */
export const CONSOLE_NO_SONG_AUDIO_MESSAGE = "이 곡에 연결된 음원이 없어 콘솔 타임코드만 재생 중입니다.";

/** 감독 실기(WT-director-play) — 새 탭은 「콘솔 같이 끔」으로 시작해 ▶ 가 음원만 튼다. 그걸 모르고 콘솔을
 *  기다리지 않게 알린다. */
export const CONSOLE_PLAY_WAITING_MESSAGE = "콘솔 타임코드 재생 요청을 보냈어요 — 콘솔 응답을 기다리는 중(음원은 콘솔이 출발한 뒤 시작합니다).";

export const CONSOLE_FOLLOW_OFF_MESSAGE =
  "「콘솔 같이」가 꺼져 있어 음원만 재생 중입니다 — 콘솔도 함께 돌리려면 ❚❚ 후 「콘솔 같이」를 켜고 ▶ 를 누르세요.";

export function createConsoleFollowRelay(): ConsoleFollowRelay {
  return {
    consoleFollow: false,
    awaiting: false,
    pressedAgainst: null,
    responseAtMs: null,
    audioStarted: false,
    failure: null,
    consoleMayRun: false,
    runStatusSeen: null,
    awaitingBusyAt: 0,
    stopping: false,
    stopPressedAgainst: null,
    stopBusyAt: 0,
    playQueued: false,
    timecodePaused: false,
    startSeconds: 0,
  };
}

/** 재생 요청 뒤 `busy` 가 왔으면 대기를 풀고 이유를 남긴다. 풀었으면 `true`(호출자는 이유를 보인다).
 * 풀지 않으면 「응답 대기」가 영영 남아 그 뒤 ▶ 가 전부 무시된다(4차 전체 실행 H-10). */
export function releaseBusyRefusedPlay(relay: ConsoleFollowRelay, busyCount: number): boolean {
  if (!relay.awaiting || busyCount <= relay.awaitingBusyAt) return false;
  relay.awaiting = false;
  relay.failure = CONSOLE_PLAY_BUSY_MESSAGE;
  return true;
}

/** 콘솔 정지 처리가 끝났는지 본다 — ❚❚ 뒤 새 응답이나 `busy` 가 오면 끝났다. 끝났고 그 사이 ▶ 가 눌려
 * 있었으면 `true`(호출자는 그 재생을 지금 보낸다). */
export function settleConsoleStop(
  relay: ConsoleFollowRelay,
  status: BeatGridSendStatus | null,
  busyCount: number,
): boolean {
  if (!relay.stopping) return false;
  if (status === relay.stopPressedAgainst && busyCount <= relay.stopBusyAt) return false;
  relay.stopping = false;
  const queued = relay.playQueued;
  relay.playQueued = false;
  return queued;
}

/** 콘솔 타임코드가 돌고 있을 수 있는지를 응답 하나로 갱신한다. 바뀌었으면 `true`(호출자는 화면에 알린다).
 * - 콘솔 재생 성공(`console_play` + ok) → 돌 수 있음.
 * - 콘솔 정지 성공(`console_stop` + ok) → 멈춤.
 * - 정지 거절·실패(승인 거절·카드 만료·게이트 차단)는 바꾸지 않는다 — 콘솔은 그대로 돈다. */
export function observeConsoleRunStatus(relay: ConsoleFollowRelay, status: BeatGridSendStatus | null): boolean {
  if (status === null || status === relay.runStatusSeen) return false;
  relay.runStatusSeen = status;
  let next = relay.consoleMayRun;
  if (status.last_action === "console_play" && status.ok) {
    next = true;
    // PR 1 — 처음부터든 이어 가기(`Go`)든 콘솔이 돌기 시작했으면 일시정지는 끝났다.
    relay.timecodePaused = false;
  }
  if (status.last_action === "console_stop" && status.ok) next = false;
  if (next === relay.consoleMayRun) return false;
  relay.consoleMayRun = next;
  return true;
}

/** 서버 응답 하나를 중계 객체에 반영한다. 이번 요청의 답으로 받아들였으면 `true`(호출자는 화면에 다시
 * 알려야 한다), 아니면 `false` 이고 아무것도 바꾸지 않는다.
 *
 * - 기다리는 중이 아니거나, 응답이 없거나, ▶ 를 누를 때 이미 있던 객체이거나, 콘솔 재생 응답이 아니면
 *   답이 아니다.
 * - 거절이면 이유를 남긴다(음원은 틀지 않는다).
 * - 성공이면 콘솔 시작 시각을 기록한다 — 서버가 실었으면 그 시각, 없으면 지금. 이 시각에서 음원 위치를 계산한다. */
export function observeConsoleFollowStatus(
  relay: ConsoleFollowRelay,
  status: BeatGridSendStatus | null,
  nowMs: number,
): boolean {
  if (!relay.awaiting) return false;
  if (status === null || status === relay.pressedAgainst) return false;
  if (status.last_action !== "console_play") return false;
  relay.awaiting = false;
  if (!status.ok) {
    relay.failure = status.reason ?? CONSOLE_PLAY_REJECTED_FALLBACK;
    return true;
  }
  relay.failure = null;
  // 서버가 콘솔이 돌기 시작한 시각을 실었으면 그 시각으로 잰다. 응답이 늦게 와도 음원은 콘솔과 같은 자리에서 튼다.
  relay.responseAtMs = status.console_started_at_ms ?? nowMs;
  return true;
}

/** 콘솔 응답을 본 뒤 지금 음원이 있어야 할 자리(초). 지난 시간에서 콘솔→음원 지연을 뺀 값이다.
 * 음수면 아직 음원을 틀 때가 아니다 — 그만큼 기다렸다 0초부터 튼다. 0 이상이면 그 자리부터 튼다. */
export function consoleAudioPositionSeconds(responseAtMs: number, delaySeconds: number, nowMs: number): number {
  return (nowMs - responseAtMs) / 1000 - delaySeconds;
}

/** 전체 실행 G-22 — 곡 끝에서 콘솔 타임코드도 끌지. 「콘솔 같이」가 켜져 있고 콘솔이 돌고 있을 수
 * 있을 때만 끈다(❚❚ 와 같은 `Off Timecode N`). 콘솔 쪽 자동 정지(AutoStop)는 실측된 적이 없어
 * 기대지 않는다(t498: 타임코드에 AUTOSTOP 필드 없음). */
export function shouldStopConsoleAtSongEnd(relay: ConsoleFollowRelay): boolean {
  return relay.consoleFollow && relay.consoleMayRun;
}
