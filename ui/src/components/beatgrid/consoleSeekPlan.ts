// 「콘솔 같이」 마디 이동 — 콘솔 타임코드 커서 맞추기 계획 (순수 함수, React·송신 없음).
//
// 마디를 옮기면 콘솔 커서도 그 마디의 시각으로 옮긴다. 멈춘 뒤(❚❚)에는 커서만 옮긴다 — 정지 중 실측으로
// `Set Timecode N Property 'Cursor' <초>` 는 재생을 켜지 않았다. 재생 중이면 먼저 ❚❚ 로 멈춘 뒤 옮기고,
// 이어 가기(▶)는 옮긴 자리에서 잇는다(결정: 잠깐 멈춤 후 이어 가기). 서버는 콘솔 명령을 한 번에 하나만
// 처리하므로, 언제 보낼지는 `consoleSeekStep` 이 정한다.

/** 마디 이동을 짧게 모으는 시간(ms) — 방향키를 연달아 누르면 마지막 마디만 보낸다. */
export const CONSOLE_SEEK_DEBOUNCE_MS = 250;

export type ConsoleSeekPlan = "none" | "seek" | "pause_then_seek";

/** 마디를 옮긴 뒤 무엇을 할지. 「콘솔 같이」가 꺼져 있거나 쓸 수 없으면 아무것도 하지 않는다.
 * 멈춘 적 없는 정지는 옮길 필요가 없다 — 처음부터 ▶ 는 `Top` 으로 되감아 시작한다. */
export function consoleSeekPlan(input: {
  consoleFollow: boolean;
  consoleFollowAvailable: boolean;
  playing: boolean;
  timecodePaused: boolean;
}): ConsoleSeekPlan {
  if (!input.consoleFollow || !input.consoleFollowAvailable) return "none";
  if (input.playing) return "pause_then_seek";
  if (input.timecodePaused) return "seek";
  return "none";
}

export interface ConsoleSeekState {
  /** 보낼 대기 중인 시각(초). 없으면 `null`. */
  pendingSeconds: number | null;
  /** 보낸 이동의 답을 아직 기다리는가. */
  inFlight: boolean;
}

export type ConsoleSeekStep = "idle" | "wait" | "send";

/** 대기 중인 이동을 지금 보낼지. 멈춤(❚❚)이나 다른 재생 요청의 답을 기다리는 중이면 서버가 `busy` 로
 * 거절하므로, 그 답이 올 때까지 기다린다. */
export function consoleSeekStep(
  state: ConsoleSeekState,
  busy: { stopping: boolean; awaiting: boolean },
): ConsoleSeekStep {
  if (state.pendingSeconds === null) return "idle";
  if (state.inFlight || busy.stopping || busy.awaiting) return "wait";
  return "send";
}
