// 「콘솔 같이」 음원 지연 (SPEC-LDBEAT-001 M9 step 7, 카드 t570,
// REQ-LDBEAT-024(a)).
//
// 코디네이터 정정(2026-10-11, 카드 t570 중간 지시) — 켬이면 콘솔에
// `Top Timecode`→`Go Timecode`를 보내고 음원은 TC 뒤 지연(t520 실측
// 3.002초)에 맞춰 시작하는 동작이지만, 그 지연 숫자는 **코드 상수가
// 아니다** — `server/design/beat_grid_data/console_audio_offset.yaml`
// (t520 출처가 같이 적힌 데이터 파일)에서 `BeatGridView.
// console_audio_offset_seconds`로 실려 온다. 이 모듈은 그 값을 **받아서
// 검증만** 한다 — 숫자 리터럴 0건(§consoleSyncAudioStartOffsetSeconds).
//
// 토글 자체(「콘솔 같이」 버튼)는 타임코드 재생 송신 경로(REQ-LDBEAT-024(a)의
// `Top Timecode`→`Go Timecode` 커맨드)가 없어 늘 비활성이다 — 코디네이터
// 재확인(2026-10-11, 카드 t570 후속 지시): 카드 t563 가 main(3e118327)에
// 머지됐지만 그 송신 경로(`beat_grid_apply`/`beat_grid_preview`/
// `beat_grid_preview_off`/`beat_grid_send_status`)는 Top/Go Timecode를
// 내지 않고, 게이트를 통과한 앱 경로도 어디에도 없다(`server/tools/
// musicsync_m3a_probe.py`는 앱 경로가 아니라 수동 프로브 스크립트다) —
// 그래서 더 이상 "t563 전"이 아니라 "그 경로 자체가 없음"이 정확한
// 이유다. 지연 데이터 유무와 무관하게 늘 비활성 — 그 이유 문구만 이
// 모듈이 상수로 든다. 새 송신 경로를 이 카드가 추가하지 않는다(코디네이터
// 지시 "Do NOT add any write path").
export const CONSOLE_FOLLOW_DISABLED_REASON = "타임코드 재생 송신 경로 없음";

/** 서버가 보낸 지연(초, `console_audio_offset_seconds`)을 정규화한다 —
 * 음수·NaN·무한대·출처 없음(`null`/`undefined`)은 전부 `null`로
 * 떨어진다(지어내지 않음). `0`은 유효한 지연(지연 없음 자체도 측정
 * 데이터일 수 있다)이라 그대로 통과한다. */
export function consoleSyncAudioStartOffsetSeconds(
  delaySeconds: number | null | undefined,
): number | null {
  if (typeof delaySeconds !== "number" || !Number.isFinite(delaySeconds) || delaySeconds < 0) {
    return null;
  }
  return delaySeconds;
}

/** 카드 t578(REQ-LDBEAT-024(a)) — 「콘솔 같이」 켬 + ▶ 를 누른 뒤 서버 응답
 * (`beat_grid_send_status`)이 오면 무엇을 할지.
 *
 * - 기다리는 중이 아니거나 콘솔 재생 응답이 아니면 `none`.
 * - 서버가 거절했으면(반영 기록 없음·남의 타임코드·승인 거절) `fail` + 그 이유 —
 *   음원만 따로 틀지 않는다(콘솔과 어긋난 재생을 만들지 않음).
 * - 성공했는데 지연 측정값이 없으면 `fail` — 지연을 지어내지 않는다.
 * - 성공 + 측정값이 있으면 `start` — 그만큼 기다렸다 음원을 0초부터 시작한다
 *   (`Top Timecode`가 콘솔을 처음으로 되감았으므로 음원도 처음부터). */
export type ConsolePlayDecision =
  | { kind: "none" }
  | { kind: "start"; delaySeconds: number }
  | { kind: "fail"; reason: string };

export function resolveConsolePlayResponse(
  awaiting: boolean,
  status: { last_action: string; ok: boolean; reason: string | null } | null,
  delaySeconds: number | null | undefined,
): ConsolePlayDecision {
  if (!awaiting || !status || status.last_action !== "console_play") return { kind: "none" };
  if (!status.ok) {
    return { kind: "fail", reason: status.reason ?? "콘솔 타임코드 재생이 거절됐습니다." };
  }
  const delay = consoleSyncAudioStartOffsetSeconds(delaySeconds);
  if (delay === null) {
    return { kind: "fail", reason: "콘솔→음원 지연 측정값이 없어 음원을 맞춰 시작할 수 없습니다." };
  }
  return { kind: "start", delaySeconds: delay };
}
