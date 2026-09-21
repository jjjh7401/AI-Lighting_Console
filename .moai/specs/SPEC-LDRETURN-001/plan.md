# SPEC-LDRETURN-001 구현 계획

## §A. 컨텍스트

- **대상 파일**: `server/looks/songcue.py` (단일 파일). 보조로 손댈 시험
  파일: `server/tests/test_songcue_climax_001.py`(신규 테스트 클래스 추가
  + 기존 `TestClimaxDurationCapIsWiredThroughBuildSongcueBundle`/
  `TestClimaxReturnCueCollisionIsGuarded` 재검토 — 두 클래스가 지금
  단언하는 "실패"가 이 SPEC 이후엔 "성공"으로 뒤집히므로 그 자체가 이
  SPEC 의 회귀 대상이다).
- **⚠️ 착수 전 필수 동기화**: 이 SPEC 을 작성한 시점의 로컬 checkout 은
  `origin/main`(`42fbd1c8`, SPEC-LDCLIMAX-001 PR #473 병합 커밋)보다 **15
  커밋 뒤져 있다**(`git rev-list --count --left-right origin/main...HEAD`
  → `15 0` 실측). 로컬 디스크의 `.moai/specs/SPEC-LDCLIMAX-001/`·
  `server/tests/test_songcue_climax_001.py` 는 존재하지 않거나 옛 초안
  상태다 — 이 SPEC 의 모든 인용(`_apply_climax_duration_cap`·
  `_climax_return_bundle`·`_guard_bundle_collision`·`_yield_bundle`·
  `_rung_applied` 등 행 번호)은 전부 `git show origin/main:` 로 직접 읽은
  기준이다. run-phase 착수 전에 로컬 트리를 `origin/main` 과 동기화해야
  한다(`agent-common-protocol.md` § Pre-Spawn Sync Check 절차 그대로).
- **선행 완료 작업**: SPEC-LDCLIMAX-001(PR #473)이 절정 지속시간 상한
  메커니즘 자체(`_apply_climax_duration_cap`, 삽입 조건·재번호 매기기)와
  F1 수정(`_guard_bundle_collision` 재호출, `songcue.py:1132`)을 이미
  완결했다. 이 SPEC 은 그 위에서 F1 수정이 드러낸 값 충돌 실패 경로만
  고친다 — 상한 계산·삽입 조건·재번호 매기기는 건드리지 않는다.

## §B. 알려진 이슈

- **B1 — 넛지 대상은 항상 새로 끼우는 복귀 큐 자신이다, 기존 큐가 아니다.**
  `_yield_bundle` 은 **상대(rival)**, 즉 이미 저장된 실제 큐의 값을
  물러서게 한다(드롭에 자리를 비켜주는 문맥 — 드롭은 director 가 의도한
  큐이고 물러서는 쪽이 사다리 회차다). 이 SPEC 의 문맥은 반대다 — 물러서야
  하는 것은 **이 SPEC 이 새로 합성하는 복귀 큐**이고, 충돌 상대(1회차 등)는
  director 가 이미 확정한 실제 큐다. `_yield_bundle` 을 그대로 호출해
  상대를 물러서게 하면 이 SPEC 과 무관한 곡의 다른 큐 값이 조용히
  바뀐다 — REQ-LDCLIMAX-011("기존 큐 값 결정 경로를 안 건드린다")을
  정면으로 어긴다. 그래서 이 SPEC 은 `_yield_bundle` 을 **호출하지
  않는다** — 그 단계별 탐색(`_HIT_STEP`, `DARKNESS_FLOOR`) **알고리즘만**
  재사용하고, 적용 대상을 복귀 큐 자신으로 바꾼 새 헬퍼를 만든다(§F M2).
- **B2 — `_apply_climax_duration_cap` 은 조립 시점의 `emitted` 딕셔너리를
  갖고 있지 않다.** `emitted` 는 `_assembled`/`_rescue_value_line_collisions`
  가 조립 도중에만 쓰는 지역 상태이고, 완성된 `SongCueBundle` 로는 전달되지
  않는다(SPEC-LDCLIMAX-001 D3 결정 — "순수 함수로 이미 조립된 번들
  목록에서 매번 다시 읽는다"와 같은 방향). 따라서 충돌 판정에 쓸 "이미
  쓰인 값 라인 집합"은 `emitted` 를 재사용하지 않고, `sections` 리스트의
  현재 상태(이 패스 안에서 앞서 끼운 복귀 큐 포함)에서 매번 새로 읽는다
  — `_guard_bundle_collision` 자신이 쓰는 것과 같은 "non-programmer-state
  명령 집합" 판정을 재사용한다(`is_programmer_state`, `songcue.py:13`
  import 이미 있음).
- **B3 — 반복 삽입 시 재계산이 필요하다.** `_apply_climax_duration_cap`
  은 한 번의 훑기에서 여러 개의 복귀 큐를 끼울 수 있다(곡에 절정 칸이
  여럿이면). 두 번째 이후 삽입은 첫 번째 삽입이 만든 값도 충돌 후보에
  넣어야 한다 — `sections.insert(...)` 가 이미 리스트를 제자리에서
  수정하므로, 매 삽입 직전에 "지금 이 `sections` 상태"에서 다시 읽으면
  자동으로 반영된다(B2 와 같은 "재조립 순서와 무관하게 항상 지금 상태를
  되묻는다" 원칙 — SPEC-LDCLIMAX-001 D3 과 동일 근거).
- **B4 — `Dimmer` 축 부재/바닥 소진 판정은 `_yield_bundle` 의 종료 조건과
  같다.** `_stepped(attributes, _DIMMER, -_HIT_STEP, DARKNESS_FLOOR)` 가
  입력과 같은 값을 돌려주면(속성 부재 또는 이미 바닥) 더 내려갈 데가
  없다는 뜻이다 — `_yield_bundle` 이 `candidate == _values_line(attributes)`
  로 판정하는 것과 같은 조건을 재사용한다.
- **B5 — `Dimmer` 넛지 상한은 감독 결정(2026-09-21)으로 해소됐다 —
  상한 없음.** 옵션 A(권장안) 채택 — `DARKNESS_FLOOR`(20)까지 무제한
  탐색, 별도 단계 수 상한은 두지 않는다. 해소 기록: §F M1, spec.md §5.

## §C. 사전 점검

```bash
# 1. 로컬 트리가 origin/main 과 동기화됐는지 확인 (착수 필수)
git fetch origin main
git rev-list --count --left-right origin/main...HEAD   # "0 N" 이어야 진행 가능

# 2. 대상 함수가 실제로 그 자리에 있는지 확인
grep -n "^def _apply_climax_duration_cap\|^def _climax_return_bundle\|^def _guard_bundle_collision\|^def _yield_bundle\|^def build_songcue_bundle" server/looks/songcue.py

# 3. 이 SPEC 이 뒤집을 두 시험이 지금 "실패를 단언"하는 상태인지 재확인
#    (뒤집힌 뒤에는 반대로 "성공을 단언"해야 한다 — 이 SPEC 의 핵심 회귀 지점)
uv run pytest -q server/tests/test_songcue_climax_001.py -k "test_bpm_argument_reaches_the_duration_cap_pass or test_a_repeated_look_climax_return_collides_with_the_first_occurrence"

# 4. 전체 스위트 기준선
uv run pytest -q
```

## §D. 제약 (위반 금지)

- REQ-LDCLIMAX-006~011 (상한 계산·삽입 조건·재번호 매기기)은 이 SPEC 이
  절대 건드리지 않는다 — 오직 "끼우려는 복귀 큐의 값이 충돌할 때"의
  분기만 새로 만든다.
- `_yield_bundle` 자신의 시그니처·동작은 바꾸지 않는다(기존 드롭/반복
  회차 회수 경로는 이 SPEC 과 무관하게 그대로 동작해야 한다) — B1 의
  이유로 그 함수를 호출하지 않고 알고리즘만 병행 재사용한다.
- 원본 절정 큐 자신의 값·사다리·액센트 기록은 이 SPEC 전후로 바이트
  동일해야 한다(REQ-LDRETURN-004).
- `server/looks/songcue.py` 밖의 파일(리그 YAML, `resolver.py`,
  `section_intent.py`, `server/orchestrator/tools.py`)은 읽기만 하고
  수정하지 않는다 — `bpm` 프로덕션 배선은 이 SPEC 의 범위 밖이다(spec.md
  §4).
- 콘솔로 명령을 실제로 보내는 코드 경로(`server/safety/`, `server/bridge/`)
  는 건드리지 않는다 — 이 SPEC 은 순수 계산 계층이다.

## §E. 자기검증

- REQ-001~008 각각에 대해 판정 명령과 관측 출력을 PASS/FAIL 표로 제출한다
  (`verification-claim-integrity.md` §3 5-section 형식).
- `uv run pytest -q` 전체 스위트 통과 수를 착수 전 기준선과 나란히
  제출한다(증분만 보고하지 않는다).
- `ruff check server/looks/songcue.py server/tests/test_songcue_climax_001.py`
  / `ruff format --check` 둘 다 clean.
- **필수 — F4 가 지적한 커버리지 공백을 직접 닫는 시험**: 반복 룩(같은
  `look_id`) + `bpm` 지정 + `blinder_or_flash`/`strobe_hit` 도달 조합을
  `_apply_climax_duration_cap` 을 **직접 부르지 않고**
  `build_songcue_bundle(bpm=...)` 공개 진입점만으로 호출해 (a) 예외 없이
  성공하고 (b) `climax_returns` 가 비어있지 않음을 단언하는 시험이 최소
  1개 있어야 한다. 이 시험이 없으면 이 SPEC 은 미완료다(사용자 요구
  — spec.md §3.2 REQ-006). M5 가 이 항목을 담당한다.
- **필수 — AC-LDRETURN-008 전용 시험**: 절정 칸 2개 이상 + 둘 다 동일
  `look_id` 반복이라는 전용 픽스처로, 첫 번째로 삽입된 복귀 큐의
  `Dimmer` 값과 두 번째로 삽입된 복귀 큐의 `Dimmer` 값이 서로 다름을
  직접 단정하는 시험이 최소 1개 있어야 한다 — 다른 시험의 픽스처가
  우연히 이 조건을 만족하는 것으로 대신하지 않는다. 이 시험이 없으면
  이 SPEC 은 미완료다. M5a 가 이 항목을 담당한다.

## §F. 마일스톤 (결정 되돌리기 쉬운 순서 — 데이터 모델을 먼저)

### M1 — `Dimmer` 넛지 상한 감독 결정 기록 (2026-09-21 해소, 가장 되돌리기 비싼 결정)

착수 전 필요했던 director 확인은 완료됐다. spec.md §5 가 기록한 결정과
같은 근거를 공유한다. 해소 전 마커가 다루던 질문:

> 값 충돌 회피가 복귀 큐 자신의 `Dimmer` 를 넛지하면, 재방출되는 값은
> "사다리를 오르기 전 기준 값"과 바이트 동일하지 않게 된다(근처 값,
> ±`_HIT_STEP` 배수). 정본 §6 은 "통제된 룩으로 복귀한다"고만 말하고
> 바이트 동일성을 요구하지 않지만, 현재 REQ-LDCLIMAX-007 의 문면과 골든
> 시험은 정확한 재현을 전제로 쓰여 있다. **실제 충돌이 있을 때(무충돌
> 시나리오는 손대지 않는다) `Dimmer` 를 몇 단계까지 넛지하는 것이
> "통제된 룩"의 허용 범위인가?**
>
> - 옵션 A(권장) — `_yield_bundle` 과 동일하게 `DARKNESS_FLOOR`(20)까지
>   무제한 탐색. 장점: 유보(REQ-003) 발동 빈도가 최소화된다(§6 이 요구하는
>   "통제된 룩으로 복귀"가 대부분의 경우 실제로 지켜진다). 단점: 이론상
>   기준 값에서 멀리 떨어진 값까지 갈 수 있다(단, `Dimmer` 만 바뀌고
>   색·빔은 그대로이므로 시각적으로는 "더 차분해진 같은 색 룩"일 뿐이다).
> - 옵션 B — director 가 정하는 작은 상한(예: 2단계 = ±10)까지만 탐색,
>   그 이상은 유보로 접는다. 장점: 시각적 이탈 폭이 작다. 단점: 유보
>   빈도가 늘어 §6("통제된 룩으로 복귀")을 못 지키는 큐가 더 많아진다
>   — 유보는 원래 절정 큐의 극단적인 값이 상한 박수 이후에도 무대에
>   그대로 남는다는 뜻이다(§6 이 직접 금지하는 상태).
>
> 셋째 옵션(계속 `SongCueBundleError` 를 던지되 메시지만 개선)은 이미
> 기각됐다 — 사용자가 요구한 AC(공개 진입점을 통한 성공 삽입)를 원천
> 봉쇄하므로 이 SPEC 의 목적 자체를 달성할 수 없다.

**결정(2026-09-21) — 옵션 A 채택. 단계 수 상한 없음, `DARKNESS_FLOOR`
까지 무제한 탐색.** director 가 수용한 근거: 절정이 끝난 뒤에도 무대가
극단적인 절정 룩에 그대로 머무르는 상태(§6 이 직접 금지하는 상태)가,
사다리 회차와 정확히 같지 않은 값으로 복귀하는 것보다 나쁘다. 옵션 B
(작은 상한)를 뒀다면 유보 빈도가 늘어 오히려 그 금지 상태가 더 자주
남는다 — 옵션 A 는 유보를 최소화해 "통제된 룩으로 복귀"를 실제로
대부분의 경우 지킨다. 셋째 옵션(예외 메시지만 개선)은 §5 원문에서 이미
기각됐고, 이번 해소로도 바뀌지 않는다.

**이 결정이 REQ/AC 문면을 바꾸지 않는 이유**: spec.md 의
REQ-LDRETURN-001~008 과 acceptance.md 의 AC-LDRETURN-001~008 은 애초에
"`DARKNESS_FLOOR` 까지 무제한" 을 전제로 쓰여 있었다 — 별도 단계 상한
표현이 REQ/AC 어디에도 없었다. 이번 해소는 spec.md REQ-LDRETURN-001 에
"단계 수 제한 없이" 구절을 추가해 그 전제를 명시적인 문면으로 굳힌 것과,
acceptance.md AC-LDRETURN-002/003 에 같은 취지의 문장을 더한 것 외에는
REQ/AC 의 의미를 바꾸지 않는다. 탐색 알고리즘 자체(아래 M2)도 바뀌지
않는다 — M2 는 애초부터 이 전제(옵션 A)로 설계돼 있었다.

Implementation Kickoff Approval 은 이 해소를 전제로 통과한다 — M2 부터
착수 가능하다.

### M2 — 넛지 헬퍼 (새 함수 인터페이스 — M1 다음으로 되돌리기 비싼 결정)

`_yield_bundle`(`songcue.py:1950`)의 단계별 `Dimmer` 탐색 알고리즘을
병행 재사용하되, 적용 대상과 충돌 판정 방식을 바꾼 새 함수를 만든다
(이름은 구현 시 확정, 예: `_climax_return_bumped`):

- 입력: 후보 복귀 큐(`SongCueSectionBundle`, `_climax_return_bundle` 이
  만든 것), 현재 `sections` 리스트(충돌 판정용).
- 충돌 판정: `sections` 의 모든 `commands` 를 훑어
  `is_programmer_state` 면제 대상이 아닌 명령 집합을 만들고(B2), 후보의
  값 라인(`commands[2]`)이 그 집합에 있는지 확인한다.
- 충돌하면 `_stepped(look.attributes, _DIMMER, -_HIT_STEP, DARKNESS_FLOOR)`
  로 한 단계 내리고 다시 판정 — 단계 수 상한 없이(M1 결정, 옵션 A)
  `DARKNESS_FLOOR` 에 닿을 때까지 반복(B4 의 종료 조건).
- 비충돌 값을 찾으면 그 값으로 `commands[2]` 를 교체한 새
  `SongCueSectionBundle` 을 돌려준다(`_yield_bundle` 이 `rival.commands[0],
  rival.commands[1], candidate, *rival.commands[3:]` 로 재구성하는 것과
  같은 5-명령 튜플 모양 — `_climax_return_bundle` 의 출력도 같은 모양이다).
- 못 찾으면 `None` — 호출자가 REQ-003 유보 경로로 넘어간다.
- `_yield_bundle` 자신은 고치지 않는다(B1) — 이 함수는 별도 정의다. 두
  함수의 단계 탐색 로직이 겹치는 것을 "중복"으로 보고 억지로 합치려
  하지 않는다 — 시그니처가 근본적으로 다르다(하나는 `emitted` 딕셔너리를
  돌려주는 조립-시점 함수, 하나는 완성된 번들을 훑는 사후-패스 함수).

### M3 — 유보 기록의 데이터 모델

- `SongCueWithheldClimaxReturn`(신규 frozen dataclass, `songcue.py` —
  `SongCueClimaxReturn`(`songcue.py:748`) 옆) — 필드: `source_section:
  SongCueSection`, `source_cue_number: int`, `rung: str`, `cap_beats:
  float`, `reason: str`, `detail: str = ""`. `SongCueClimaxReturn` 과
  같은 필드 이름 규약을 따르되 "유보" 의미를 담는다
  (`SongCueWithheldMovement`/`Darkness`/`Accent` 와 같은 "명시적이고 눈에
  보이는" 패턴).
- `SongCueBundle` 에 `withheld_climax_returns: tuple[
  SongCueWithheldClimaxReturn, ...] = ()` 필드 추가(`withheld_movement`/
  `darkness`/`accents` 와 같은 자리, `songcue.py:770` 근처).

### M4 — `_apply_climax_duration_cap` 배선

M2 의 넛지 헬퍼와 M3 의 유보 기록을 `_apply_climax_duration_cap`
(`songcue.py:1331`)의 삽입 루프에 연결한다:

- 복귀 큐를 만든 뒤(`_climax_return_bundle` 호출 직후), `sections.insert`
  전에 M2 의 넛지 헬퍼로 충돌 여부를 확인한다.
- 비충돌(또는 넛지 성공) 값이면 지금처럼 `sections.insert` 로 끼운다.
- 유보면 `sections.insert` 를 건너뛰고(재번호 매기기도 건너뛴다 —
  이 큐는 삽입되지 않으므로), M3 의 레코드를 만들어 반환값의
  `withheld_climax_returns` 에 담는다. `returns`(`SongCueClimaxReturn`
  리스트, REQ-LDCLIMAX-010)에는 담지 않는다 — 삽입되지 않았으므로
  "삽입 보고"가 아니다.
- 함수 끝의 `if not returns: return bundle` 분기(`songcue.py:1381`)는
  `withheld_climax_returns` 도 함께 확인하도록 확장한다 — 유보만
  있고 성공 삽입이 0건이어도 `withheld_climax_returns` 는 비어있지
  않은 채로 돌려줘야 한다(`replace(bundle, ..., withheld_climax_returns=
  tuple(withheld))`).

### M5 — 공개 진입점 성공 삽입 시험 (F4 가 지목한 커버리지 공백 — 최우선 신규 시험)

- `build_songcue_bundle(bpm=...)` 를 반복 룩(같은 `look_id`) + 절정
  칸 도달 조합으로 직접 호출해 (a) 예외 없이 성공 (b) `climax_returns`
  비어있지 않음을 단언하는 시험을 새로 추가한다 — `_apply_climax_duration_
  cap` 을 직접 부르지 않는다(§E 필수 항목).
- 이 시험의 픽스처는 기존
  `TestClimaxDurationCapIsWiredThroughBuildSongcueBundle
  .test_bpm_argument_reaches_the_duration_cap_pass`(`test_songcue_
  climax_001.py:503`)가 쓰던 6회 반복 코러스와 같은 모양을 재사용해도
  된다 — 다만 단언을 "성공"으로 뒤집는다.
- **이 시험은 AC-LDRETURN-001 만 겨냥한다.** 절정 칸이 몇 개 만들어지는지,
  두 번째 삽입이 있는지는 이 시험의 관심사가 아니다 — 6회 반복 코러스가
  우연히 절정 칸을 2개 이상 만들더라도 그 사실에 기대 AC-LDRETURN-008
  을 대신 만족했다고 보지 않는다(AC-008 전용 시험은 M5a).

### M5a — AC-LDRETURN-008 전용 시험 (반복 삽입 상호 비충돌, 목적 시험 — 우연한 부산물이 아니다)

- **전용 픽스처를 새로 구성한다** — M5 의 6회 반복 코러스를 재사용하지
  않는다(M5 는 절정 칸 개수를 단언·보장하지 않으므로 우연에 기댈 수
  없다). 절정 칸(`blinder_or_flash` 또는 `strobe_hit` 확정)이 2개 이상
  있고, 둘 다 동일한 `look_id` 를 반복하는 룩으로 채워 두 복귀 큐 모두
  값 충돌이 발생하도록 배치한다.
- `build_songcue_bundle(bpm=...)` 공개 진입점으로 호출해 (a) 예외 없이
  성공하고 (b) 두 복귀 큐가 모두 `climax_returns` 에 삽입됐음을 확인한
  뒤, **첫 번째로 삽입된 복귀 큐의 `Dimmer` 값과 두 번째로 삽입된 복귀
  큐의 `Dimmer` 값이 서로 다름을 직접 단정한다**(AC-LDRETURN-008 문면
  그대로) — B3 이 설계한 "매번 현재 `sections` 상태를 다시 읽는다"는
  전제가 두 번째 삽입에 실제로 반영되는지가 이 시험의 목적이다.
- `_apply_climax_duration_cap` 을 직접 부르지 않는다 — F4 의 교훈(공개
  진입점을 안 거치는 시험이 결함을 숨겼다)이 AC-008 에도 그대로
  적용된다.

### M6 — 기존 두 시험 뒤집기 (F1 수정이 만든 "실패 단언"을 이 SPEC 의 "성공 단언"으로)

- `test_bpm_argument_reaches_the_duration_cap_pass`(`test_songcue_
  climax_001.py:503`) — `pytest.raises(SongCueBundleError, ...)` 단언을
  걷어내고, 성공 + `climax_returns` 비어있지 않음 단언으로 되돌린다(단,
  M5 가 이미 이 시험을 커버한다면 이 클래스 자체를 M5 로 통합해도 된다
  — 구현 시 판단).
- `TestClimaxReturnCueCollisionIsGuarded
  .test_a_repeated_look_climax_return_collides_with_the_first_occurrence`
  (`test_songcue_climax_001.py:553`) — 이 시험의 원본 3회 반복·`Dimmer`
  축 존재 픽스처는(M1 이 옵션 A 를 택하면) 이제 성공해야 한다 — 이것이
  정확히 AC-LDRETURN-007 이 요구하는 시나리오다(3회 반복, `Dimmer` 축
  O, 3회차 넛지 삽입 성공). **원본 성공 단언의 행선지를 명시한다 —
  새 메서드로 보존한다:**
  1. 이 메서드 자신을 성공 단언으로 뒤집고
     `test_a_repeated_look_climax_return_succeeds_via_nudge` 로 개명한다
     — AC-007 이 요구하는 "오늘 쓰는 같은 픽스처"(3회 반복, `Dimmer` 축
     존재, `bpm=120`)를 그대로 재호출해 성공 + 3회차 넛지 삽입을
     단정한다. 원본 픽스처는 삭제·변형하지 않는다.
  2. **같은 클래스에 신규 메서드**
     `test_a_repeated_look_climax_return_is_withheld_without_dimmer_axis`
     를 추가한다 — `Dimmer` 축이 없는 룩으로 같은 구조(3회 반복)의
     픽스처를 재구성한 음성 대조군이다. REQ-003 유보 경로가 실제로
     발동하는지(`withheld_climax_returns` 에 레코드가 나타나는지)를
     확인한다.
  원본 메서드를 지우거나 덮어써 AC-007 의 성공 단언이 사라지는 경로는
  선택지에서 제외한다 — 반드시 위 두 메서드가 공존해야 한다
  (`test_the_guard_still_passes_when_bpm_is_undeclared` 는 `bpm=None`
  대조군이므로 그대로 둔다 — REQ-007 의 회귀 대상, 이 두 메서드와는
  무관).

### M7 — 전량 회귀 + lint

- `uv run pytest -q` 전체 스위트. `ruff check`/`ruff format --check`
  대상 파일 전량.
- `@MX:ANCHOR`/`@MX:REASON` 주석을 M2/M4 가 바꾼 함수에 이 저장소 관행대로
  추가한다 — `_apply_climax_duration_cap` 은 이미 `@MX:ANCHOR` 가 있으므로
  (`songcue.py:1315` 근처) 그 `@MX:REASON` 을 이 SPEC 의 새 분기(넛지·유보)
  까지 포함하도록 갱신한다.

## §G. 안티패턴 (하지 말 것)

- `_yield_bundle` 을 그대로 호출해 **상대(rival)** 를 물러서게 하지 않는다
  (B1) — REQ-LDCLIMAX-011 위반.
- `emitted` 딕셔너리를 `_apply_climax_duration_cap` 까지 스레딩하지 않는다
  (B2) — SPEC-LDCLIMAX-001 D3 이 이미 기각한 "가변 상태 누적" 패턴을
  이 SPEC 에서 되살리지 않는다.
- 넛지 상한을 M1 결정(옵션 A, 단계 수 상한 없음)과 다르게 임의로 작은
  상한(예: "일단 2단계까지만")을 넣어 진행하지 않는다 — `DARKNESS_FLOOR`
  도달만이 유일한 탐색 종료 조건이다.
- `Dimmer` 외 다른 축(색·빔)으로 넛지를 확장하지 않는다(§4 Out of Scope).
- `bpm` 프로덕션 배선(`tools.py:3230`)을 이 SPEC 에서 같이 처리하지
  않는다 — 별도 후속 SPEC.

## §H. 교차 참조

- SPEC-LDCLIMAX-001 — 절정 지속시간 상한 메커니즘 원본, F1/F4 발단
- SPEC-LDACCENT-001 — `SongCueWithheld*` 보고 패턴 선례
- `docs/proposals/song-structure-lighting-standard.md` §6 — "절정의 지속
  시간에 상한이 있다... 그 뒤 통제된 룩으로 복귀한다"
- `.moai/reports/` 아래 SPEC-LDCLIMAX-001 sync-auditor F4 원본 보고(경로는
  run-phase 착수 시 `moai spec_audit`/기존 리포트 디렉터리에서 재확인)
