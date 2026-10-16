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
  /** 성공한 콘솔 재생 응답을 본 시각(`Date.now()`). `null` 이면 이어 갈 콘솔 실행이 없다. */
  responseAtMs: number | null;
  /** 지금 마운트된 `BeatGrid` 가 이미 음원을 시작했는가(마운트마다 한 번만 튼다). */
  audioStarted: boolean;
  /** 서버가 거절한 이유 — 다음에 마운트되는 화면도 보이게 둔다. */
  failure: string | null;
}

/** 서버가 거절하면서 이유를 싣지 않았을 때 쓰는 문구. */
const CONSOLE_PLAY_REJECTED_FALLBACK = "콘솔 타임코드 재생이 거절됐습니다.";

/** 지연 측정값이 없으면 지연을 지어내지 않고 멈춘다(`resolveConsolePlayResponse` 의 같은 문구). */
export const CONSOLE_DELAY_MISSING_MESSAGE = "콘솔→음원 지연 측정값이 없어 음원을 맞춰 시작할 수 없습니다.";

/** 음원을 틀 때가 됐는데 이 곡에 연결된 음원이 아예 없을 때. 콘솔 타임코드는 이미 돌고 있다. */
export const CONSOLE_NO_SONG_AUDIO_MESSAGE = "이 곡에 연결된 음원이 없어 콘솔 타임코드만 재생 중입니다.";

export function createConsoleFollowRelay(): ConsoleFollowRelay {
  return {
    consoleFollow: false,
    awaiting: false,
    pressedAgainst: null,
    responseAtMs: null,
    audioStarted: false,
    failure: null,
  };
}

/** 서버 응답 하나를 중계 객체에 반영한다. 이번 요청의 답으로 받아들였으면 `true`(호출자는 화면에 다시
 * 알려야 한다), 아니면 `false` 이고 아무것도 바꾸지 않는다.
 *
 * - 기다리는 중이 아니거나, 응답이 없거나, ▶ 를 누를 때 이미 있던 객체이거나, 콘솔 재생 응답이 아니면
 *   답이 아니다.
 * - 거절이면 이유를 남긴다(음원은 틀지 않는다).
 * - 성공이면 지금 시각을 콘솔 시작 시각으로 기록한다 — 이 시각에서 음원 위치를 계산한다. */
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
  relay.responseAtMs = nowMs;
  return true;
}

/** 콘솔 응답을 본 뒤 지금 음원이 있어야 할 자리(초). 지난 시간에서 콘솔→음원 지연을 뺀 값이다.
 * 음수면 아직 음원을 틀 때가 아니다 — 그만큼 기다렸다 0초부터 튼다. 0 이상이면 그 자리부터 튼다. */
export function consoleAudioPositionSeconds(responseAtMs: number, delaySeconds: number, nowMs: number): number {
  return (nowMs - responseAtMs) / 1000 - delaySeconds;
}
