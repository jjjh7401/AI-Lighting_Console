// 재생 시계 — ⏮·▶/❚❚·⏪10초/10초⏩·재생 중 자동 스크롤·화면 오류 흡수
// (SPEC-LDBEAT-001 M9 step 7, 카드 t570, REQ-LDBEAT-024(a)(b)(d)(f)).
//
// 이 모듈은 `<audio>` 엘리먼트나 `performance.now()`/`requestAnimationFrame`
// 자체를 호출하지 않는다 — 그 시계·DOM은 호출자(`BeatGrid.tsx`)가 쥐고,
// 이 모듈은 그 값들을 받아 계산만 하는 순수 함수다(jsdom 시험대가 없다,
// BeatGrid.test.tsx 와 같은 경계).

/** 재생 시작(또는 마지막 재배치) 때 고정한 기준(초 + 성능시계 ms)과 지금
 * 성능시계 ms로 지금 재생 위치(초)를 계산한다. 시계가 거꾸로 가는 입력
 * (중복 RAF 프레임 등)이 와도 앵커 밑으로는 떨어지지 않는다. */
export function elapsedPlaybackSeconds(
  anchorSeconds: number,
  anchorPerfMs: number,
  nowPerfMs: number,
): number {
  return anchorSeconds + Math.max(0, nowPerfMs - anchorPerfMs) / 1000;
}

/** ⏪10초/10초⏩(REQ-LDBEAT-024(d)) — 재생 위치를 `[0, maxSeconds]`로
 * 클램프한다. `BeatGrid.tsx`의 기존 `clampSkipSeconds`와 같은 식이다 —
 * 모듈 순환 참조를 피하려고 이 한 줄만 복제한다(`lrSplit.ts`의
 * `stageCentreX`와 같은 관행). */
export function clampPlaybackSeconds(current: number, delta: number, maxSeconds: number): number {
  return Math.max(0, Math.min(maxSeconds, current + delta));
}

/** 플레이 묶음 시계 — 시안 모양 「분:초.소수1자리」(mockup `fmtT`,
 * 초기값 「0:00.0」). 반올림으로 60.0초가 되는 경우는 다음 분으로 넘긴다. */
export function formatPlaybackClock(seconds: number): string {
  const tenths = Math.round(Math.max(0, seconds) * 10);
  const minutes = Math.floor(tenths / 600);
  const rest = (tenths - minutes * 600) / 10;
  return `${minutes}:${rest.toFixed(1).padStart(4, "0")}`;
}

/** 재생이 곡 끝에 도달했는가 — `maxSeconds`가 없으면(타임라인에 BPM/박자
 * 미확정) 끝에 도달할 수 없다(지어내지 않음, `null`을 false로 떨어뜨림). */
export function hasReachedPlaybackEnd(seconds: number, maxSeconds: number | null): boolean {
  if (maxSeconds === null) return false;
  return seconds >= maxSeconds;
}

/** 스페이스바로 재생/일시정지 토글(REQ-LDBEAT-024(a)) — 입력칸·선택칸·
 * contenteditable 안의 스페이스는 무시한다(`BeatGridTopBar.tsx`의
 * `barNavKeyDelta`와 같은 경계). */
export function isPlaybackSpaceToggleKey(event: {
  code?: string;
  key?: string;
  targetTag?: string;
  isContentEditable?: boolean;
}): boolean {
  const tag = (event.targetTag ?? "").toUpperCase();
  if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || event.isContentEditable) return false;
  return event.code === "Space" || event.key === " " || event.key === "Spacebar";
}

/** 음원 시계 입력 — `HTMLAudioElement` 에서 필요한 세 값만 받는다(시험에서 흉내 내기 쉽게).
 * `error` 는 `MediaError | null` 이다. */
export interface AudioClockSource {
  paused: boolean;
  currentTime: number;
  error: object | null;
}

/** 음원 시계 — 음원이 실제로 도는 동안은 그 `currentTime`(초)이 재생 위치다.
 * 음원이 없거나, 멈췄거나, 오류가 났으면 `null`: 호출자는 성능시계로 이어 간다
 * (음원 없이 시계만으로 가는 경로). */
export function audioClockSeconds(audio: AudioClockSource | null): number | null {
  if (audio === null || audio.paused || audio.error !== null) return null;
  if (!Number.isFinite(audio.currentTime)) return null;
  return Math.max(0, audio.currentTime);
}

/** 재생 위치(초) → 가로 픽셀. 격자 칸과 같은 식(마디 = 초 ÷ 박 길이, 픽셀 = 마디 × pxPerBar)을
 * 쓰므로 칸 위에 정확히 놓인다. 마디 단위로 끊기지 않고 소수 픽셀로 흐른다.
 * 박 길이를 모르면 `null`(지어내지 않음). `barZeroStartSeconds` 는 0마디가 시작하는 곡 시각
 * (`barToSeconds` 와 같은 기준, 3차 전체 실행 G-19) — 없으면 0초. */
export function playheadPixelX(
  seconds: number,
  secondsPerBar: number | null | undefined,
  pxPerBar: number,
  barZeroStartSeconds: number | null | undefined = 0,
): number | null {
  if (!secondsPerBar || !Number.isFinite(secondsPerBar)) return null;
  const zeroStart = typeof barZeroStartSeconds === "number" && Number.isFinite(barZeroStartSeconds) ? barZeroStartSeconds : 0;
  return ((seconds - zeroStart) / secondsPerBar) * pxPerBar;
}

/** 재생선 따라가기의 새 `scrollLeft`(px) — mockup `keepVisible()`의 "1/3 지점" 규칙을
 * 연속으로 돌린다(AC-LDBEAT-024(h)). 재생선이 보이는 폭의 1/3 을 넘으면 그 자리에 머물도록
 * 스크롤 목표를 준다(매 프레임 호출하면 격자가 재생선을 따라 흐른다). 재생선이 1/3 안쪽이면
 * `null`(움직이지 않음). 보이는 칸 밖이면(크게 건너뛰었거나 뒤로 되감음) 1/3 자리로 바로 옮긴다.
 * 보이는 폭이 0 이하(아직 측정 전)면 `null`. 목표는 0 밑으로 내려가지 않는다. */
export function followScrollTarget(playheadX: number, scrollLeft: number, visibleWidth: number): number | null {
  if (!(visibleWidth > 0)) return null;
  const anchor = visibleWidth / 3;
  const offset = playheadX - scrollLeft;
  const outside = offset < 0 || offset > visibleWidth;
  if (!outside && offset < anchor) return null;
  return Math.max(0, playheadX - anchor);
}

/** 사용자가 재생 중 직접 스크롤하면 따라가기를 잠시 멈춘다. 마지막 직접 스크롤 뒤 이만큼(ms)
 * 조용하면 다시 따라간다. 멈춘 동안에도 ▶·⏮·지도 클릭은 곧바로 다시 따라가게 한다. */
export const FOLLOW_RESUME_QUIET_MS = 3000;

/** 멈춤이 끝났는가 — 직접 스크롤 기록이 없거나(`null`) 마지막 직접 스크롤 뒤 조용한 시간이
 * `FOLLOW_RESUME_QUIET_MS` 이상이면 참. */
export function followPauseEnded(lastManualScrollMs: number | null, nowMs: number): boolean {
  return lastManualScrollMs === null || nowMs - lastManualScrollMs >= FOLLOW_RESUME_QUIET_MS;
}

/** REQ-LDBEAT-024(f) — 재생 루프 한 프레임의 화면 갱신을 감싼다. `update`가
 * 던지면 재생을 멈추지 않고(다시 던지지 않음) `onError`로만 알린다 — 다음
 * 프레임의 오디오·시계는 그대로 이어간다(mockup `tick()`의
 * `try{...}catch(e){log(...)}` 과 같은 경계). */
export function runPlaybackFrameUpdate(update: () => void, onError: (message: string) => void): void {
  try {
    update();
  } catch (error) {
    onError(error instanceof Error ? error.message : String(error));
  }
}
