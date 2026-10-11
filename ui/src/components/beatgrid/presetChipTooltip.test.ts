// REQ-LDBEAT-023(c) — 프리셋 칩 툴팁 문자열(설명 텍스트 + 사용 큐 수)
// 순수 함수 시험. SPEC-LDBEAT-001 M9 step 6, 카드 t560.
//
// 데이터 경계(§Gaps, 카드 t560 보고): 콘솔이 실제로 돌려주는 프리셋
// "설명 텍스트"(시안 원문 예시 「펄스 30↔60 · 4박」 꼴)는 지금
// `BeatGridDrawerEntry`에 없다(`name`은 콘솔이 읽은 짧은 **이름**일 뿐,
// 효과 설명이 아니다 — server/design/beat_grid_presets.py:build_preset_
// drawer 확인). 아래 시험은 그 설명 텍스트가 "있다고 가정했을 때" 포맷이
// 옳은지만 검증한다 — 실제 와이어링은 설명 데이터가 생기기 전까지는
// usage-only 문자열로 떨어진다(지어내지 않음).
import { describe, expect, it } from "vitest";

import { formatPresetChipTooltip } from "./presetChipTooltip";

describe("formatPresetChipTooltip", () => {
  it("설명 텍스트가 있으면 설명과 사용 큐 수를 ' · '로 함께 보여준다", () => {
    expect(formatPresetChipTooltip("테스트용 설명 텍스트", 3)).toBe(
      "테스트용 설명 텍스트 · 이 곡에서 큐 3곳 사용",
    );
  });

  it("설명 텍스트가 없으면(null) 사용 큐 수만 보여준다 — 지어내지 않는다", () => {
    expect(formatPresetChipTooltip(null, 0)).toBe("이 곡에서 큐 0곳 사용");
  });

  it("설명 텍스트가 빈 문자열이면 없는 것으로 본다", () => {
    expect(formatPresetChipTooltip("   ", 1)).toBe("이 곡에서 큐 1곳 사용");
  });

  it("undefined도 null과 같게 처리한다", () => {
    expect(formatPresetChipTooltip(undefined, 2)).toBe("이 곡에서 큐 2곳 사용");
  });
});
