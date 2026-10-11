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

/** 재생 중 플레이헤드가 보이는 범위를 벗어나면 스크롤할 새 `scrollLeft`
 * (px). 이미 보이면 `null`(스크롤 안 함) — mockup `keepVisible()`의
 * "범위 밖이면 1/3 지점으로" 재구현(AC-LDBEAT-024(h)). `visibleWidth`가
 * 아직 측정 전(0 이하)이면 `null`. */
export function autoScrollTargetForPlayhead(
  playheadBar: number,
  pxPerBar: number,
  rangeStart: number,
  scrollLeft: number,
  visibleWidth: number,
): number | null {
  if (visibleWidth <= 0) return null;
  const x = (playheadBar - rangeStart) * pxPerBar;
  if (x < scrollLeft || x > scrollLeft + visibleWidth - pxPerBar * 2) {
    return Math.max(0, x - visibleWidth / 3);
  }
  return null;
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
