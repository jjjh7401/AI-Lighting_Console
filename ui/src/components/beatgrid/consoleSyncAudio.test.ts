// 「콘솔 같이」 음원 지연 순수 함수 시험 (SPEC-LDBEAT-001 M9 step 7, 카드
// t570, REQ-LDBEAT-024(a)).
//
// 코디네이터 정정(2026-10-11) — 콘솔 타임코드 뒤 음원 지연(t520 실측
// 3.002초)은 코드 상수가 아니라 서버 측 데이터 파일
// (`server/design/beat_grid_data/console_audio_offset.yaml`)에서 와야
// 한다. 이 모듈은 그 값을 받아만 쓰는 순수 함수다 — 숫자 리터럴 0건.
// 「콘솔 같이」 토글은 송신 경로(t563)가 아직 없어 늘 비활성이다(지연
// 데이터 유무와 무관) — 그 비활성 이유 문자열도 여기서 상수로 둔다.
import { describe, expect, it } from "vitest";

import { CONSOLE_FOLLOW_DISABLED_REASON, consoleSyncAudioStartOffsetSeconds } from "./consoleSyncAudio";

describe("consoleSyncAudioStartOffsetSeconds — 지연 데이터 정규화", () => {
  it("유효한 양수 지연은 그대로 돌려준다", () => {
    expect(consoleSyncAudioStartOffsetSeconds(3.002)).toBe(3.002);
  });

  it("0 은 유효한 지연이다(지연 없음 자체도 데이터일 수 있음)", () => {
    expect(consoleSyncAudioStartOffsetSeconds(0)).toBe(0);
  });

  it("출처가 없으면(null/undefined) null — 지어내지 않는다", () => {
    expect(consoleSyncAudioStartOffsetSeconds(null)).toBeNull();
    expect(consoleSyncAudioStartOffsetSeconds(undefined)).toBeNull();
  });

  it("음수·비정상 값은 null로 떨어진다", () => {
    expect(consoleSyncAudioStartOffsetSeconds(-1)).toBeNull();
    expect(consoleSyncAudioStartOffsetSeconds(Number.NaN)).toBeNull();
    expect(consoleSyncAudioStartOffsetSeconds(Number.POSITIVE_INFINITY)).toBeNull();
  });
});

describe("CONSOLE_FOLLOW_DISABLED_REASON — 토글 비활성 이유(코디네이터 재확인 2026-10-11)", () => {
  it("송신 경로 자체가 없다는 고정 문구다(t563 머지 후에도 그 경로는 없음)", () => {
    expect(CONSOLE_FOLLOW_DISABLED_REASON).toBe("타임코드 재생 송신 경로 없음");
  });
});
