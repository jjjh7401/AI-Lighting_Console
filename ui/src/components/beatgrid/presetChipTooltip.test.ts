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

import type { BeatGridDrawerSection } from "../../protocol";
import { findDrawerEntryByPresetNo, formatPresetChipTooltip } from "./presetChipTooltip";

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

// 카드 t560 후속(REQ-LDBEAT-023(c), plan.md M9 step 6) — 「이 마디 한눈에」
// 표 칸의 프리셋 칩은 어느 풀(위치·색·디머)에 속하는지 미리 모르고
// preset_no 하나만 가진다(예: 칸의 `effect_preset_no`는 위치 풀의 효과
// 번호대다) — 그래서 풀 이름을 몰라도 번호 하나로 모든 섹션을 가로질러
// 찾는 조회가 필요하다.
const SECTIONS: BeatGridDrawerSection[] = [
  {
    pool_name: "Position",
    title: "위치",
    pool_no: 2,
    unread: false,
    bands_confirmed: true,
    entries: [
      { preset_no: "2.41", name: "LA Floor", usage_count: 2, used_by: [], is_effect_band: false },
      { preset_no: "2.61", name: "LA Tilt Wave 8", usage_count: 1, used_by: [], is_effect_band: true, description: "틸트 웨이브 · 8박" },
    ],
  },
  {
    pool_name: "Dimmer",
    title: "밝기",
    pool_no: 1,
    unread: false,
    bands_confirmed: true,
    entries: [{ preset_no: "1.31", name: "LA Dim 30", usage_count: 0, used_by: [], is_effect_band: false }],
  },
];

describe("findDrawerEntryByPresetNo", () => {
  it("어느 풀에 있든 번호로 항목을 찾는다", () => {
    expect(findDrawerEntryByPresetNo(SECTIONS, "1.31")?.name).toBe("LA Dim 30");
    expect(findDrawerEntryByPresetNo(SECTIONS, "2.61")?.description).toBe("틸트 웨이브 · 8박");
  });

  it("없는 번호면 null(지어내지 않음)", () => {
    expect(findDrawerEntryByPresetNo(SECTIONS, "9.99")).toBeNull();
  });

  it("sections 자체가 null(서랍 미수신)이면 null", () => {
    expect(findDrawerEntryByPresetNo(null, "1.31")).toBeNull();
  });
});
