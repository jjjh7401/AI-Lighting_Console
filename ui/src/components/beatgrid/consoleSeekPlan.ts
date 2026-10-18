// 「콘솔 같이」 마디 이동 — 콘솔 타임코드 커서 맞추기 계획 (순수 함수, React·송신 없음).
//
// 마디를 옮기면 콘솔 커서도 그 마디의 시각으로 옮긴다. 멈춘 뒤(❚❚)에는 커서만 옮긴다 — 정지 중 실측으로
// `Set Timecode N Property 'Cursor' <초>` 는 재생을 켜지 않았다. 재생 중에는 멈추지 않고, 연타가 멈춘 뒤 마지막
// 자리만 보내며 주기적으로 다시 맞춘다(실측: 재생 중 Set 이 바로 먹고 재생은 이어진다). 서버는 콘솔 명령을 한 번에 하나만
// 처리하므로, 언제 보낼지는 `consoleSeekStep` 이 정한다.

/** 마디 이동을 짧게 모으는 시간(ms) — 방향키를 연달아 누르면 마지막 마디만 보낸다. */
export const CONSOLE_SEEK_DEBOUNCE_MS = 250;

/** 재생 중 콘솔 커서를 다시 맞춰 보는 주기(ms)와, 그때 허용하는 어긋남(초). 서버도 같은 허용 오차로 읽어 맞춘다. */
export const CONSOLE_RESYNC_INTERVAL_MS = 2000;
export const CONSOLE_RESYNC_TOLERANCE_SECONDS = 0.3;

/** 곡 시각(음원 자리)을 콘솔 타임코드 시각으로. 콘솔은 음원보다 실측 지연만큼 앞서 있다(음원은 그 뒤에 튼다).
 * 지연 측정값이 없으면 `null` — 시각을 지어내지 않는다. */
export function consoleTimecodeSeconds(songSeconds: number, delaySeconds: number | null): number | null {
  if (delaySeconds === null || !Number.isFinite(delaySeconds) || !Number.isFinite(songSeconds)) return null;
  return Math.max(0, songSeconds + delaySeconds);
}

/** 재생 중 주기 확인을 지금 보낼지. 「콘솔 같이」가 켜진 재생 중이고, 보낼 이동이 없고 답을 기다리는 중이 아닐 때만. */
export function consoleResyncDue(input: {
  playing: boolean;
  consoleFollow: boolean;
  consoleFollowAvailable: boolean;
  inFlight: boolean;
  pending: boolean;
  awaiting: boolean;
  stopping: boolean;
}): boolean {
  return (
    input.playing &&
    input.consoleFollow &&
    input.consoleFollowAvailable &&
    !input.inFlight &&
    !input.pending &&
    !input.awaiting &&
    !input.stopping
  );
}

export type ConsoleSeekPlan = "none" | "seek" | "live";

/** 마디를 옮긴 뒤 무엇을 할지. 「콘솔 같이」가 꺼져 있거나 쓸 수 없으면 아무것도 하지 않는다.
 * 멈춘 적 없는 정지는 옮길 필요가 없다 — 처음부터 ▶ 는 `Top` 으로 되감아 시작한다. */
export function consoleSeekPlan(input: {
  consoleFollow: boolean;
  consoleFollowAvailable: boolean;
  playing: boolean;
  timecodePaused: boolean;
}): ConsoleSeekPlan {
  if (!input.consoleFollow || !input.consoleFollowAvailable) return "none";
  // 재생 중에는 멈추지 않는다 — 콘솔 커서는 연타가 멈춘 뒤 마지막 자리로 재생을 이어 간 채 옮긴다.
  if (input.playing) return "live";
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
