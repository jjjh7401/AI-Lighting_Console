# SPEC-LDACCENT-001 인수 기준

Given-When-Then 시나리오. 각 AC 는 이진 판정(PASS/FAIL)이 가능해야 한다.

## AC-LDACCENT-001 — 전량 무영향 조합에서 사다리가 셀 이름을 지어내지 않는다 (검증: REQ-LDACCENT-005, REQ-LDACCENT-006, REQ-LDACCENT-007)

**Given** 단일 축(`Dimmer`)만 가진 룩(`Zoom`/`Iris` 없음)을 FULL_RIG(블라인더
그룹 없음, `server/tests/busking_fixtures.py:31-41`) 위에서 시작값 20, 후렴
7회 반복으로 배치한다(`TestHeadroomCaseIsUntouched.test_seven_choruses_with_ample_headroom_are_byte_identical_before_and_after`
가 실제로 쓰는 `_build(7, dimmer=20.0)` 픽스처와 동일한 모양 — plan-auditor
D4 정정: 이전 초안은 시작값 95 로 잘못 적었다. `_build` 의 기본 인자값
95 는 다른 시험(`TestEveryRepeatOccurrenceCarriesOneAccent`)이 쓰는 값과
혼동한 것이었다).

**When** `build_songcue_bundle` 이 7개 반복 회차를 사다리로 오른다.

**Then**
- 저장된 7개 큐 중 어느 것의 `.ladder` 에도 `zoom_pinch`/`iris_pinch`/
  `blinder_or_flash` 가 등장하지 않는다(전부 `dimmer_hit`/`dimmer_yield`
  조합뿐이다).
- `Dimmer` 값 진행은 `20/25/30/35/40/45/50`(또는 이 SPEC 이전과 동일한
  기존 골든 진행값)으로 이 SPEC 이전과 바이트 동일하다.
- `instance >= 2` 인 회차 중 적어도 하나는 `accent_withheld`(섹션 단위)와
  번들 수준 `withheld_accents` 양쪽에 유보 기록을 남긴다 — 기록은
  section/cue_number/reason 을 채운 `SongCueWithheldAccent` 이고, 빈 값이
  아니다.

## AC-LDACCENT-002 — 회전이 무영향 칸을 건너뛰고 다음 유효 후보로 넘어간다 (검증: REQ-LDACCENT-004)

**Given** `Zoom`·`Iris` 둘 다 실제 축으로 가진 룩(`_look("chorus", dimmer=80,
zoom=18, iris=60)` 패턴, `server/tests/test_songcue_ladder.py:597`)을
FULL_RIG(블라인더 그룹 없음) 위에서 5회 반복 배치한다
(`test_the_fourth_occurrence_swaps_its_accent_instead_of_stacking` 과 같은
모양).

**When** 사다리가 깊이 3(4회차)에 닿아, 필터링 전이라면 소박하게
`blinder_or_flash` 를 골랐을 자리에 이른다.

**Then**
- 그 큐의 `.ladder` 는 `blinder_or_flash` 를 담지 않는다(FULL_RIG 에 블라인더
  그룹이 없어 무영향이므로).
- 그 큐의 `.ladder` 는 대신 남은 유효 후보(아이리스 또는 줌) 중 하나를
  정확히 하나만 담는다 — 액센트가 통째로 사라지지 않는다(유효 후보가
  실제로 남아 있는 시나리오이므로).
- `TestOneMarkingAccentPerCue` 가 세는 `_marking_count(ladder) <= 1`
  불변식이 이 큐에서도 유지된다.

## AC-LDACCENT-003 — 효과가 있는 블라인더는 여전히 회전에 오르고 무대에 나간다 (양성 대조군) (검증: REQ-LDACCENT-001, REQ-LDACCENT-003)

**Given** 블라인더 그룹을 실제로 가진 리그(`_RIG_WITH_BLINDER` 패턴 —
FULL_RIG + `(20, "BLIND")`, `server/tests/test_songcue_accent_ladder_t382.py:49`)
와, `intent_for_label` 이 유효한 §6 행을 돌려주는 섹션 라벨(예: `Chorus`)을
가진 반복 회차 배치.

**When** 사다리가 `blinder_or_flash` 를 고르는 깊이에 닿는다.

**Then**
- `.ladder` 는 `blinder_or_flash` 를 담는다.
- `accent_fixture` 필드는 `None` 이 아니고, `rung == LADDER_BLINDER_OR_FLASH`,
  `groups` 가 비어 있지 않다.
- 실제 콘솔 명령 목록(`bundle.commands`)에 그 그룹을 겨냥한 `Group <N>`
  선택 줄이 포함된다.
- 이 회차는 유보 기록을 남기지 않는다(`accent_withheld is None`).

## AC-LDACCENT-004 — AC-3 골든 대조군 바이트 동일성 (밝기 진행값) (검증: REQ-LDACCENT-001, REQ-LDACCENT-007)

**Given** `TestHeadroomCaseIsUntouched.test_seven_choruses_with_ample_headroom_are_byte_identical_before_and_after`
가 오늘 쓰는 정확히 같은 픽스처(단일 축 룩, FULL_RIG, 시작값 20, 후렴 7회).

**When** 이 SPEC 적용 전/후로 같은 픽스처를 두 번 돌린다.

**Then**
- 각 회차의 `Dimmer` 값(`_dimmer_from_values_line`)은 이 SPEC 전후로 완전히
  동일하다(20/25/30/35/40/45/50).
- `Dimmer` 이외의 속성 명령 바이트(`ColorRGB_*` 등)도 이 SPEC 전후로 완전히
  동일하다.
- 달라져도 되는 것은 오직 `.ladder` 튜플의 찍는 액센트 셀 이름 부분(무영향
  칸이 더는 등장하지 않음)과, 새로 생기는 유보 기록뿐이다.

## AC-LDACCENT-005 — 하나뿐인 액센트 불변식이 필터링과 무관하게 유지된다 (검증: REQ-LDACCENT-008)

**Given** `TestOneMarkingAccentPerCue`(`server/tests/test_songcue_ladder.py:470`)
의 기존 전 시나리오(3회차 EDM 실기 룩, 5회차 줌+아이리스 합성 룩, 축 없는
룩, 천장 룩).

**When** 이 SPEC 이 필터링 로직을 추가한 뒤 같은 시나리오를 재실행한다.

**Then**
- `test_every_ladder_rung_is_classified` — 분류 대상 칸 집합은 그대로
  `{dimmer_hit, zoom_pinch, iris_pinch, blinder_or_flash}` 다(새 칸을
  만들지 않았다).
- 저장된 모든 큐에서 `_marking_count(ladder) <= 1` 이 유지된다.
- 축이 없는 룩(`washonly`)에서 밝기만으로 값이 갈리는 기존 성질(§6.1 거울상
  대조군)은 그대로다 — `Zoom`/`Iris` 문자열이 어떤 명령 줄에도 안 나간다는
  기존 단언이 여전히 통과한다.

## AC-LDACCENT-006 — 라벨이 §6 행에 없으면 그룹이 있어도 후보에서 제외된다 (검증: REQ-LDACCENT-001, REQ-LDACCENT-003)

> plan-auditor 1차 판정(D1/MP-7) 뒤 감독 결정(2026-09-20)으로 범위에
> 들어온 세 번째 필터링 축 — 이전 초안은 이 경로를 §4 Out of Scope 로
> 미뤘다.

**Given** 블라인더 그룹을 실제로 가진 리그(`_RIG_WITH_BLINDER` 패턴 —
FULL_RIG + `(20, "BLIND")`, `server/tests/test_songcue_accent_ladder_t382.py:49`)
와, `intent_for_label` 이 `None` 을 돌려주는 섹션 라벨(§6 표에 없는 라벨)을
가진 반복 회차 배치.

**When** 사다리가 깊이가 정하는 순서상 `blinder_or_flash` 를 고르는
깊이에 닿는다.

**Then**
- `.ladder` 는 `blinder_or_flash` 를 담지 않는다(리그에 그룹이 있어도
  이 큐가 속한 섹션의 라벨이 §6 행을 못 찾으므로 무영향이다).
- `accent_fixture` 필드는 `None` 이다(`rung`/`groups`/`dimmer` 전부 빈 값 —
  `_accent_fixture_commands` 의 `intent is None` 갈래, `songcue.py:2069-2070`).
- 남은 유효 후보(다른 룩 축)가 있으면 그것으로 대체되고, 없으면
  `accent_withheld`(섹션 단위)와 `withheld_accents`(번들 단위)에 유보
  기록이 남는다 — 빈 칸으로 조용히 넘어가지 않는다.

## 엣지 케이스

- **줌만 있고 아이리스는 없는 룩** — `zoom_pinch` 만 유효 후보, `iris_pinch`
  는 필터링 대상. 회전이 `iris_pinch` 자리에서 `zoom_pinch` 로 넘어가거나
  건너뛰는지 신규 시험으로 확인한다.
- **블라인더 그룹은 있고 스트로브 그룹은 없는 리그** — 두 무대-그룹 칸이
  서로 독립적으로 필터링되는지 확인한다(`allow_strobe=True` 경로에서).
- **네 후보 전부 무영향** — AC-LDACCENT-001 이 이 경우다. 유보 기록이
  정확히 필요한 자리에서만 생기고, 남는 값 갈림은 여전히 `Dimmer`/
  `dimmer_yield` 만으로 이뤄진다.
- **`intent_for_label` 이 None 인 라벨 + 블라인더 그룹은 있는 리그** — 이제
  범위 안이다. AC-LDACCENT-006 이 이 조합을 직접 커버한다(더는 회귀
  확인만이 아니다).
- **`intent_for_label` 이 None 인 라벨 + 블라인더 그룹도 없는 리그** — 두
  무영향 조건이 겹치는 경우. REQ-003 의 두 OR 조건 중 어느 쪽이 먼저
  걸리는지는 무관하다 — 결과(그 칸 제외)는 같다. AC-LDACCENT-001 의
  전량-무영향 시나리오와 같은 층위의 회귀 확인으로 충분하다.
- **§6 행은 있지만 그 밝기 구간이 다른 큐로 이미 소진된 경우(D2)** —
  spec.md §4 Out of Scope 로 명시적으로 미룬 잔여 갈래다(REQ-LDACCENT-007
  의 명시적 예외). 이 SPEC 의 AC 는 이 조합을 커버하지 않는다 — 회귀
  확인만(이 SPEC 적용 전후로 이 조합의 동작이 달라지지 않아야 한다).

## 품질 게이트 기준

- `uv run pytest -q` 전체 스위트 — 0 FAIL. 기준선(착수 전, `origin/main`
  동기화 직후 측정치)과 나란히 보고.
- `ruff check server/looks/songcue.py <변경된 시험 파일들>` — clean.
- `ruff format --check` 동일 대상 — clean.
- `test_songcue_sections.py` 의 `{}` 매핑 리터럴 금지 AST 가드(`ast.Dict`)
  — 계속 통과(`dict()` 함수 호출은 가드 대상이 아니다).
- subagent-boundary grep(`AskUserQuestion`) — `server/looks/` 전체 0건(기존
  불변식, 이 SPEC 이 위반할 이유 없음 — 회귀 확인 차원).

## Definition of Done

- [ ] REQ-LDACCENT-001~008 전부 PASS — 판정 명령 + 관측 출력 인용.
- [ ] AC-LDACCENT-001~006 전부 PASS.
- [ ] `TestHeadroomCaseIsUntouched`/`test_the_fourth_occurrence_swaps_its_accent_instead_of_stacking`
      픽스처 갱신이 §D 제약(밝기 값 바이트 동일성)을 지킨 채 반영됨.
- [ ] 신규 양성 대조군(AC-LDACCENT-003, 블라인더 있는 리그) 추가·통과.
- [ ] 신규 음성 대조군(AC-LDACCENT-006, 블라인더 있는 리그 + 라벨 미매치)
      추가·통과.
- [x] `[NEEDS CLARIFICATION: intent_for_label 축 포함 여부]`(plan.md 옛 M2)
      해소됨 — 감독 결정(2026-09-20)으로 범위를 넓혀 REQ-001/003 세 번째
      효과 조건으로 편입, AC-LDACCENT-006 으로 검증한다. plan.md/spec.md
      에서 마커 자체는 제거됨.
- [ ] 전체 pytest 스위트 회귀 없음, ruff clean.
