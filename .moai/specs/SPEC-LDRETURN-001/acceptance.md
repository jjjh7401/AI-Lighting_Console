# SPEC-LDRETURN-001 인수 기준

Given-When-Then 시나리오. 각 AC 는 이진 판정(PASS/FAIL)이 가능해야 한다.

## AC-LDRETURN-001 — 공개 진입점을 통한 반복 룩 삽입 성공 (F4 가 지목한 커버리지 공백을 직접 닫는 시험, 필수) (검증: REQ-LDRETURN-001, REQ-LDRETURN-002, REQ-LDRETURN-006)

**Given** 같은 `look_id` 를 가진 룩이 반복되는 코러스 구간(6회, `Dimmer` 축을
가진 룩)을 `blinder_or_flash` 사다리 칸에 도달하도록 배치하고, BPM 을
선언한다(`test_bpm_argument_reaches_the_duration_cap_pass` 가 쓰는 픽스처와
같은 모양, `server/tests/test_songcue_climax_001.py:503`).

**When** `songcue.build_songcue_bundle("Song", selections,
sequences_section=..., groups_section=..., bpm=120.0)` 을 **공개 진입점
그대로** 호출한다(`_apply_climax_duration_cap` 을 직접 부르지 않는다).

**Then**
- `SongCueBundleError` 가 던져지지 않는다(호출이 예외 없이 성공한다).
- 반환된 번들의 `climax_returns` 가 비어있지 않다(적어도 1건의 복귀 큐가
  실제로 삽입됐다).
- 삽입된 복귀 큐의 값 라인은 `_guard_bundle_collision` 을 통과한
  상태다(반환됐다는 사실 자체가 증거).

## AC-LDRETURN-002 — 넛지된 값은 원본 절정 큐의 기준 값과 다르다, 그러나 색은 유지된다 (검증: REQ-LDRETURN-001)

**Given** AC-001 과 같은 픽스처 — 1회차가 이미 이 룩의 기준 값 라인을 쥐고
있다.

**When** 3회차 이상이 사다리를 올라 `blinder_or_flash`/`strobe_hit` 에
도달해 복귀 큐 삽입이 시도된다.

**Then**
- 삽입된 복귀 큐의 `Dimmer` 값은 원본 룩의 `Dimmer` 값과 다르다(넛지가
  실제로 적용됐다).
- 삽입된 복귀 큐의 색 속성(`ColorRGB_R`/`G`/`B`)은 원본 룩의 색 값과
  **동일하다** — 넛지는 `Dimmer` 축에만 적용된다(§4 Out of Scope).
- 넛지된 값 라인은 이 번들 안 어디에도 이미 존재하지 않는다(새 충돌을
  만들지 않는다).
- 넛지 단계 수에는 `DARKNESS_FLOOR` 도달 외의 상한이 없다(감독 결정
  2026-09-21, 옵션 A) — 충돌이 몇 회 반복되든 탐색은 계속된다.

## AC-LDRETURN-003 — 넛지된 값도 여전히 `DARKNESS_FLOOR` 이상이다 (검증: REQ-LDRETURN-001)

**Given** AC-001 과 같은 픽스처.

**When** 넛지가 여러 단계 적용된다(반복 회차가 많아 여러 겹 충돌이
발생하는 경우).

**Then** 삽입된 복귀 큐의 `Dimmer` 값은 `DARKNESS_FLOOR`(20) 미만으로
내려가지 않는다 — 단계 수 자체에는 별도 상한이 없다(감독 결정
2026-09-21, 옵션 A). 오직 `DARKNESS_FLOOR` 도달 여부만 탐색을 멈춘다.

## AC-LDRETURN-004 — `Dimmer` 축이 없는 룩은 유보되고 원본 값은 무변경 (검증: REQ-LDRETURN-003, REQ-LDRETURN-004, REQ-LDRETURN-008)

**Given** `Dimmer` 축이 없는 룩(다른 축만 가진 룩)이 반복돼 `blinder_or_
flash` 사다리 칸에 도달하고, 그 값 라인이 이미 앞선 회차와 충돌하는
조합을 배치한다.

**When** `build_songcue_bundle(bpm=...)` 을 호출한다.

**Then**
- `SongCueBundleError` 가 던져지지 않는다(호출이 예외 없이 성공한다 —
  유보는 전체 조립 실패가 아니다).
- 그 절정 칸의 복귀 큐는 `climax_returns` 에 나타나지 않는다(삽입되지
  않았다).
- 대신 `withheld_climax_returns` 에 `SongCueWithheldClimaxReturn` 레코드가
  1건 이상 나타난다 — `source_cue_number`/`rung`/`cap_beats`/`reason` 이
  채워진 빈 값이 아닌 레코드다.
- 원본 절정 큐 자신의 값 라인·사다리(`ladder`)·`accent_fixture` 는 이
  SPEC 전후로 바이트 동일하다.

## AC-LDRETURN-005 — 무충돌 시나리오는 바이트 동일(골든 대조군 무회귀) (검증: REQ-LDRETURN-005)

**Given** 기존 `TestClimaxReturnIsInsertedForALongClimax
.test_a_return_cue_lands_at_the_two_beat_cap` 가 오늘 쓰는 정확히 같은
픽스처(`server/tests/test_songcue_climax_001.py:375` — 단일 절정 큐 +
충돌 없는 다음 큐).

**When** 이 SPEC 적용 전/후로 같은 픽스처를 두 번 돌린다.

**Then** 삽입된 복귀 큐의 `Dimmer` 값(`Attribute 'Dimmer' At 60`)은 이
SPEC 전후로 바이트 동일하다 — 충돌이 없으므로 넛지가 전혀 개입하지
않는다.

## AC-LDRETURN-006 — `bpm=None` 은 이 SPEC 이전과 바이트 동일(무영향) (검증: REQ-LDRETURN-007)

**Given** 기존 `TestUndeclaredBpmIsANoOp.test_bpm_none_returns_the_input_
untouched` 가 쓰는 픽스처(`bpm=None`).

**When** `_apply_climax_duration_cap(bundle, bpm=None)` 을 호출한다.

**Then** `result is bundle`(항등 — 입력 그대로 반환), `climax_returns ==
()`, `withheld_climax_returns == ()` — 이 SPEC 의 넛지/유보 로직이 전혀
평가되지 않는다.

## AC-LDRETURN-007 — 기존 sync-audit 재현 픽스처는 더는 예외를 던지지 않는다 (F1→F4 폐쇄 확인) (검증: REQ-LDRETURN-002, REQ-LDRETURN-006)

**Given** `TestClimaxReturnCueCollisionIsGuarded
.test_a_repeated_look_climax_return_collides_with_the_first_occurrence`
가 오늘(이 SPEC 이전) 쓰는 3회 반복 코러스 + `bpm=120` 픽스처
(`server/tests/test_songcue_climax_001.py:553`) — 이 SPEC 이전에는
`SongCueBundleError` 를 던지는 결함 재현 사례였다.

**When** 이 SPEC 적용 후 같은 픽스처로 `build_songcue_bundle(bpm=120.0)`
을 호출한다.

**Then** 예외 없이 성공하고, 3회차의 복귀 큐가 넛지된 `Dimmer` 값으로
삽입된다(`climax_returns` 에 해당 레코드가 나타난다) — 결함 재현 픽스처가
이제 정상 경로로 전환됐다.

## AC-LDRETURN-008 — 반복 삽입이 서로 충돌하지 않는다 (검증: REQ-LDRETURN-001)

**Given** 절정 칸에 도달하는 저장 큐가 2개 이상이고, 둘 다 같은 룩(같은
`look_id`)을 반복해 두 복귀 큐가 같은 기준 값을 재방출하려는 조합을
배치한다.

**When** `_apply_climax_duration_cap` 이 두 복귀 큐를 순서대로 끼운다.

**Then** 첫 번째 복귀 큐가 넛지된 값과 두 번째 복귀 큐가 넛지된 값은
서로 다르다 — 두 번째 삽입의 충돌 판정이 첫 번째 삽입이 만든 값도
포함해서 다시 읽는다(§B3).

## Definition of Done

- REQ-LDRETURN-001~008 전량 PASS(§E 자기검증 표).
- AC-LDRETURN-001~008 전량 PASS, 특히 AC-001(공개 진입점 성공 삽입)은
  사용자가 명시적으로 요구한 필수 항목 — 이 AC 없이는 이 SPEC 은
  완료로 간주되지 않는다.
- `uv run pytest -q` 전체 스위트 통과, 착수 전 기준선 대비 델타가
  이 SPEC 이 더한 신규 시험 수와 정확히 일치.
- `ruff check` / `ruff format --check` clean.
- plan.md M1 의 `Dimmer` 넛지 상한 결정은 2026-09-21 감독 확인으로
  이미 해소됨(옵션 A — 상한 없음, `DARKNESS_FLOOR` 까지 무제한) — 해소
  기록은 spec.md §5 및 plan.md §F M1 에 있다.
