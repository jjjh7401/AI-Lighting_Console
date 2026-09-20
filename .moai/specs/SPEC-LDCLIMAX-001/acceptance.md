# SPEC-LDCLIMAX-001 인수 기준

Given-When-Then 시나리오. 각 AC 는 이진 판정(PASS/FAIL)이 가능해야 한다.
`disable_color_snap`/`bpm`/`meter` 등 구체 인자 이름은 M1~M2 구현 시
확정된 실제 시그니처를 따른다 — 여기서는 §NC(plan.md, 2026-09-20 해소)
반영 이후의 설계(design.md/plan.md) 기준의 잠정 이름을 쓴다.

## AC-LDCLIMAX-001 — `color_snap` 은 무조건 후보이고, 색 변화 없는 골든 픽스처는 바이트 동일 (검증: REQ-LDCLIMAX-001, REQ-LDCLIMAX-004)

**Given** (a) SPEC-LDACCENT-001 골든 대조군(`TestHeadroomCaseIsUntouched`
와 같은 단일 축 룩 + FULL_RIG + 후렴 7 회 반복 픽스처, 회차 간
`ColorRGB_*` 값이 항상 동일)을, `disable_color_snap` 인자를 아예 넘기지
않고(기본값) 조립한다. (b) 색이 실제로 바뀌는 룩(코러스 1과 코러스 2가
서로 다른 `ColorRGB_*` 값을 쓰는 픽스처)도 같은 방식으로 조립한다.

**When** `build_songcue_bundle` 이 이 두 곡을 조립한다.

**Then**
- (a) 색 변화 없는 픽스처에서는, `_marking_accents` 가 `color_snap` 을
  후보에 무조건 포함시키지만(REQ-001), 직전 저장 큐와 색이 항상 같으므로
  `_accent_is_effective` 확장 분기가 매 회차 `False` 를 돌려주고
  (REQ-004), 결과적으로 저장된 큐들의 `.ladder` 중 어디에도 `color_snap`
  이 등장하지 않는다. `Dimmer` 값 진행과 그 외 속성 명령 바이트가 이
  SPEC 이전과 완전히 동일하다(`TestHeadroomCaseIsUntouched` 를 그대로
  재실행해 대조 — 스위치가 꺼져서가 아니라 이 필터 때문이다).
- (b) 색이 실제로 바뀌는 픽스처에서는, 다른 유효 후보(줌·블라인더·
  아이리스[·스트로브])가 모두 무영향이고 §7 색 집합 안의 복귀 색이
  존재하면 `color_snap` 이 그 큐의 찍는 액센트로 확정될 수 있다 — 이
  SPEC 이전에는 나오지 않던 결과이며, 이것은 결함이 아니라 REQ-001 이
  요구하는 의도된 동작이다.
- `test_every_ladder_rung_is_classified`(`test_songcue_ladder.py:470`)
  는 `LADDER_RUNGS` 에 `LADDER_COLOR_SNAP` 이 추가된 뒤의 `_MARKING`
  튜플 갱신과 함께 재실행하면 PASS 다 — 갱신 없이 두면 이 시험은
  의도적으로 RED 다(이 시험 자신의 설계 목적).

## AC-LDCLIMAX-002 — 색 스냅이 §7 색 집합 안에서만 색을 낸다 (검증: REQ-LDCLIMAX-002)

**Given** 코러스가 3회 이상 반복되고 코러스 1이 이미 팔레트 색 집합(예:
`["빨강", "주황"]`)을 쓴 곡을, `disable_color_snap` 을 넘기지 않고
(기본값 활성) 조립한다.

**When** 사다리가 어느 회차에서 `color_snap` 을 후보로 평가한다.

**Then**
- `color_snap` 이 낼 수 있는 색은 코러스 1의 팔레트 색 집합
  (`["빨강", "주황"]`) 안으로 제한된다 — 그 집합 밖의 새 색(예: "청록")을
  대상으로 `color_snap` 이 선택되지 않는다.
- 코러스 1의 팔레트 밖 색을 강제로 주입한 음성 픽스처에서는 `color_snap`
  이 무영향 칸으로 판정돼 회전 후보에서 제외된다(`_accent_is_effective`
  확장 분기가 `False` 를 돌려준다).

## AC-LDCLIMAX-003 — 색 스냅 확정 시 페이드가 0으로 강제된다 (검증: REQ-LDCLIMAX-003)

**Given** `color_snap` 이 유효 후보이고 사다리 깊이가 그 칸을 가리키는
회차 배치.

**When** 사다리가 `color_snap` 을 그 큐의 찍는 액센트로 확정한다.

**Then**
- 그 큐의 페이드 시간(§B2 확정 필드)은 정확히 `0`(또는 `0.0`)이다 — D-레벨
  예산이 유도했을 다른 값으로 남지 않는다.
- 같은 큐의 `Dimmer`/`Zoom`/`Iris` 등 다른 속성 값은 색 스냅이 없었을
  때와 동일하다(색 스냅은 색과 페이드만 바꾼다).

## AC-LDCLIMAX-004 — 색이 안 바뀌면 색 스냅은 무영향 칸으로 제외된다 (검증: REQ-LDCLIMAX-004)

**Given** 직전 저장 큐와 팔레트 색이 이미 같은 룩 배치(예: 같은 회차가
반복돼 색 전환이 없는 구성).

**When** 사다리가 `color_snap` 을 후보로 평가한다.

**Then**
- `_accent_is_effective` 가 `color_snap` 에 대해 `False` 를 돌려준다 —
  직전 큐와 값이 같으면 "스냅"이 관측되지 않으므로 무영향으로 판정된다.
- 유효 후보가 남아 있으면(예: `zoom_pinch`) 회전은 그 후보로 넘어간다
  (SPEC-LDACCENT-001 의 "무영향 칸 건너뛰기" 규율 재확인).

## AC-LDCLIMAX-005 — 색 스냅도 큐당 액센트 하나 규율을 지킨다 (검증: REQ-LDCLIMAX-005)

**Given** `color_snap` 이 확정된 큐.

**When** `TestOneMarkingAccentPerCue` 와 같은 형태의 불변식 검사를 그
큐에 대해 돈다.

**Then**
- 그 큐의 `.ladder` 에는 찍는 액센트 칸이 정확히 하나만 실린다
  (`color_snap` 과 `zoom_pinch`/`iris_pinch`/`blinder_or_flash`/
  `strobe_hit` 중 어느 것도 동시에 실리지 않는다).

## AC-LDCLIMAX-006 — 긴 절정 구간에 복귀 큐가 삽입된다 (검증: REQ-LDCLIMAX-006, REQ-LDCLIMAX-007)

**Given** BPM 120, `blinder_or_flash` 가 확정된 절정 큐가 있고, 다음
저장 큐가 그 절정 큐 시작으로부터 2박(`beats_to_seconds(2.0, 120)` =
1.0 초)보다 한참 뒤(예: 8초 뒤)에 오는 곡 배치.

**When** `_apply_climax_duration_cap` 이 완성된 번들을 훑는다.

**Then**
- 절정 큐 시작 + 1.0 초 시각에 새 복귀 큐가 삽입된다.
- 그 복귀 큐의 값은 절정 큐가 사다리를 오르기 전의 기준 값과 동일하다
  (블라인더 그룹 명령이 없고, `Dimmer`/`Zoom`/`Iris` 가 기준 룩 값).
- 삽입 이후 큐들의 `cue_number` 가 1씩 밀려 순서가 유지된다.

## AC-LDCLIMAX-007 — 자연 전환이 상한을 지키면 복귀 큐를 생략한다 (검증: REQ-LDCLIMAX-008)

**Given** BPM 120, `strobe_hit` 가 확정된 절정 큐(4박 상한 =
`beats_to_seconds(4.0, 120)` = 2.0 초)가 있고, 다음 저장 큐가 그로부터
1.5 초 뒤(상한 이전)에 오는 곡 배치.

**When** `_apply_climax_duration_cap` 이 완성된 번들을 훑는다.

**Then**
- 새 복귀 큐가 삽입되지 않는다 — `SongCueBundle.climax_returns` 가
  이 절정 큐에 대해 빈 채로 남는다.
- 기존 큐 번호·값이 전혀 바뀌지 않는다(이 패스가 no-op 이다).

## AC-LDCLIMAX-008 — BPM 미선언이면 상한이 아예 적용되지 않는다 (검증: REQ-LDCLIMAX-009)

**Given** `blinder_or_flash` 가 확정된 절정 큐가 있지만 이 곡의 BPM 이
`None`(미선언)인 배치.

**When** `_apply_climax_duration_cap(bundle, bpm=None, ...)` 이 호출된다.

**Then**
- 반환된 번들이 입력과 완전히 동일하다(큐 개수·번호·값 전부 바이트
  동일) — 어떤 복귀 큐도 삽입되지 않는다.

## AC-LDCLIMAX-009 — 삽입은 명시적으로 보고되고 기존 값은 불변이다 (검증: REQ-LDCLIMAX-010, REQ-LDCLIMAX-011)

**Given** AC-LDCLIMAX-006 과 같은 복귀 큐 삽입이 일어나는 배치.

**When** `build_songcue_bundle` 이 최종 번들을 반환한다.

**Then**
- `SongCueBundle.climax_returns` 튜플에 정확히 하나의 `SongCueClimaxReturn`
  레코드가 있고, `source_cue_number`/`rung`/`cap_beats`/
  `inserted_cue_number`/`inserted_start_ms` 가 전부 채워져 있다(빈 값이
  아니다).
- 삽입 이전에 이미 확정돼 있던 다른 큐들(절정 큐 자신 포함)의 `Dimmer`/
  `Zoom`/`Iris`/색/`accent_fixture`/`.ladder` 값은 이 SPEC 이전과
  동일하다 — 이 패스는 새 큐를 뒤에 더할 뿐 기존 큐를 고치지 않는다.

## AC-LDCLIMAX-010 — `disable_color_snap=True` 는 임시 안전판으로 후보를 완전히 제거한다 (검증: REQ-LDCLIMAX-012)

**Given** AC-LDCLIMAX-001(b)와 같이 색이 실제로 바뀌어 `color_snap` 이
정상적으로는 유효 후보가 될 픽스처를, 이번에는 `disable_color_snap=True`
를 명시적으로 넘겨 조립한다.

**When** `build_songcue_bundle` 이 이 곡을 조립한다.

**Then**
- `_marking_accents` 가 돌려주는 후보 튜플 어디에도 `LADDER_COLOR_SNAP`
  이 없다 — 다른 후보(줌·블라인더·아이리스[·스트로브])의 효과 판정은
  이 스위치의 영향을 받지 않는다(이 스위치는 `color_snap` 한 칸만
  제거한다).
- 같은 픽스처를 `disable_color_snap` 을 넘기지 않고(기본값) 조립하면
  `color_snap` 이 다시 후보로 나타난다 — 이 스위치는 기본값이 아니라
  호출자가 명시적으로 켜야만 효과가 있는 opt-out이다(REQ-012).
