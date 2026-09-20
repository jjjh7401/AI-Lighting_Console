---
id: SPEC-LDACCENT-001
title: "찍는 액센트 사다리 — 무영향 칸을 후보에서 거르고, 못 채운 자리는 유보로 남긴다"
version: "0.1.0"
status: completed
created: 2026-09-20
updated: 2026-09-20
author: jaihyun
priority: P1
phase: "Lighting Copilot v1.0 target"
module: "server/looks/songcue.py"
lifecycle: spec-anchored
tags: "songcue, accent-ladder, blinder, strobe, zoom-pinch, iris-pinch, reporting-integrity, card-t424"
tier: M
related_specs: [SPEC-COPILOT-SONGCUE-001]
---

# SPEC-LDACCENT-001 — 찍는 액센트 사다리 무영향 칸 필터 + 유보 보고

## HISTORY

| 일자 | 내용 |
|---|---|
| 2026-09-20 | 최초 작성. 큐 카드 t424 — t382(`fix(t382)`, PR #468, `origin/main` 병합 완료)가 이미 남긴 follow-up("effective-accent filter") 을 닫는다. t382 자신의 판정 보고(`.moai/reports/t382/verdict.md` "범위 밖으로 남긴 것")가 이 결함을 정확히 이름까지 붙여 예고했다: "사다리 회전이 그 룩에 없는 축이나 리그에 없는 그룹을 그대로 고르는 기존 동작은 손대지 않았다... 후속 카드 후보: 회전이 후보를 고르기 전에 이 룩·이 리그에서 실제로 효과가 있는 액센트만 후보로 거르는 'effective-accent filter'." |
| 2026-09-20 | plan-auditor 1차 판정(FAIL, 0.625, MP-7 자동 실패) 반영. 감독 결정 — `intent_for_label` 라벨 미매치 경로(§4 옛 비목표)를 범위 안으로 들여 REQ-001~003 세 번째 효과 조건으로 편입, `[NEEDS CLARIFICATION]` 마커 해소. D1(REQ-007 절대 불변식 모순)·D3(호출자 수 오기재)·D4(AC-1 시작값 95≠골든 시험 20) 정정, D2(`_unique_floor_climb` 소진 경로) 는 범위 밖으로 명시하고 REQ-007 에 예외로 이름 붙임, D5(AC↔REQ 인용 추가)·D6(REQ-004/008 GEARS 키워드 정정)·D7(`dict()` 금지 문면 정정) 반영. |

## 1. 배경과 근본 원인

### 1.1 실측 (카드 t424, 2026-09-20, t382 calibration 중)

`server/looks/songcue.py`의 찍는 액센트 회전(`_MARKING_ACCENTS` = `zoom_pinch`·
`blinder_or_flash`·`iris_pinch`, `LADDER_STROBE_HIT` 별도)은 반복 회차마다 값
라인을 가르기 위해 사다리 칸 하나를 고른다. 그러나 이 회전은 **그 칸이 실제로
무엇이든 바꾸는지**를 보지 않고 순전히 깊이(반복 회차)로만 고른다
(`_climb_rungs`, `songcue.py:2333`). 그 결과 두 갈래에서 칸 이름이 사다리
보고(`SongCueSectionBundle.ladder`, `songcue.py:407`)에 실려도 무대에는
아무것도 안 나간다:

1. **`zoom_pinch`/`iris_pinch`** — 룩이 `Zoom`/`Iris` 축을 안 실었으면
   `_rung_applied`(`songcue.py:2447`)가 부르는 `_stepped`(`songcue.py:2462`)는
   그 속성을 찾지 못해 값을 그대로 돌려준다(무영향 무입력, "없는 축엔 값을
   만들어 보내지 않는다"는 이 파일 자신의 기존 규율).
2. **`blinder_or_flash`/`strobe_hit`** — 이 두 칸은 애초에 이 룩 자신의 값을
   절대 안 바꾼다(`_rung_applied` 의 세 번째 분기, `songcue.py:2447` — 다른
   그룹이기 때문). 실제 무대 명령은 `_accent_fixture_commands`
   (`songcue.py:2040`)가 사다리와 별도로 만드는데, 이 함수는 리그에 그 역할로
   묶인 그룹이 없으면(`RoleResolution.groups_for(role)`,
   `server/looks/resolver.py:125`, 빈 튜플) 빈 명령을 돌려준다
   (`songcue.py:2040` 독스트링이 이미 이 갈래를 "이 카드 이전부터 있던 모양"
   으로 문서화한다).

실측 재현(2026-09-20, FULL_RIG — 블라인더 그룹 없음
[`server/tests/busking_fixtures.py:31-41`] + 단일 축(`Dimmer`뿐) 룩, 시작값
20, 후렴 7회): `AttributeValue("Dimmer", 20.0)` 만 가진 룩으로 7회차를
돌리면, 블라인더 그룹이 존재하지 않는 FULL_RIG 위에서도 `.ladder` 에
`blinder_or_flash` 가 2회 등장한다(`server/tests/test_songcue_accent_ladder_t382.py`
`TestHeadroomCaseIsUntouched.test_seven_choruses_with_ample_headroom_are_byte_identical_before_and_after`
의 `expected_ladders` 3·6회차 — 이 시험 자신이 AC-3 골든 대조군으로 이미
그 값을 굳히고 있다). 이 룩+리그 조합에서 `zoom_pinch`·`iris_pinch`·
`blinder_or_flash` 셋 다 무대 효과가 0인데도 셋 다 어떤 회차에서는 사다리에
실린다.

### 1.2 이미 예고된 후속 — t382 verdict.md

이 SPEC 은 새 결함을 발견한 것이 아니라, t382 자신의 판정 보고가 "범위 밖으로
남긴 것"으로 명시적으로 예고해 둔 후속을 닫는다(`.moai/reports/t382/verdict.md`
마지막 절):

> "사다리 회전이 그 룩에 없는 축(줌만 있는 룩에 아이리스를 고르는 경우 등)이나
> 리그에 없는 그룹(블라인더 없는 리그에 blinder_or_flash 를 고르는 경우)을
> 그대로 고르는 기존 동작은 손대지 않았다. 그 경우 ladder 에는 칸 이름이
> 실리지만 무대 효과는 전혀 없다... 후속 카드 후보: 회전이 후보를 고르기
> **전에** 이 룩·이 리그에서 실제로 효과가 있는 액센트만 후보로 거르는
> 'effective-accent filter' — 그러면 무영향 액센트가 애초에 사다리에 오르지
> 않는다."

`SongCueSectionBundle.accent_fixture` 필드(`songcue.py:407` 근방 독스트링)는
이미 "`ladder` 가 blinder_or_flash/strobe_hit 를 실어도 이 필드가 `None` 일
수 있다"는 갈래를 문서화하고 있다 — 즉 **그 사실은 안에서 관측 가능하다**.
문제는 그 관측이 `ladder` 튜플 자체의 셀 이름 정직성으로 전파되지 않는다는
것이다: 보고를 읽는 감독은 `accent_fixture` 필드까지 따로 대조하지 않는 한
"이 칸이 실렸다"를 "이 칸이 무대에 나갔다"로 오독한다.

## 2. 범위 결정

- **필터링 축은 세 가지 — 룩의 축 보유, 리그의 그룹 보유, 그 큐가 속한
  섹션 라벨의 §6 행 보유.** 카드가 명시한 두 갈래(줌/아이리스 축 부재,
  블라인더/스트로브 그룹 부재)에 더해, `intent_for_label(section.label)`
  가 `None` 을 돌려주는 세 번째 무영향 경로(`songcue.py:2040` — 리그에
  그룹이 있어도 §6 표 행을 못 찾으면 역시 무대 명령이 안 나간다,
  `server/looks/section_intent.py:156`)도 이 SPEC 이 다룬다(감독 결정
  2026-09-20, plan-audit 1차 판정 이후 — 이전 초안은 이 경로를 §4 비목표로
  미뤘으나, 구조는 다르되(룩+리그 조합이 아니라 **그 큐가 속한 섹션의
  라벨**마다 달라진다) 회귀 위험이 낮다고 판단해 범위를 넓혔다).
  `blinder_or_flash`/`strobe_hit` 두 칸은 이제 **리그 그룹 보유와 라벨의
  §6 행 보유 둘 다**를 만족해야 유효 후보다 — REQ-LDACCENT-003 참고.
- **필터는 회전 전, 회차별 값 결정 전에 적용된다.** `_marking_accents`
  (`songcue.py:187`)가 오늘 `allow_strobe: bool` 하나만 받는 자리에, 이
  큐의 룩(`look.attributes`)과 리그 해석(`resolution: RoleResolution`),
  그리고 이 큐가 속한 섹션의 라벨(`section.label`)을 더 받아 무영향 칸을
  회전 후보에서 미리 뺀다 — 사후에 걸러내지 않는다.
- **밝기 구간이 이미 소진된 경로(§6 행은 있지만 `_unique_floor_climb` 가
  `None` 을 돌려주는 경우)는 이 SPEC 이 다루지 않는다.** §4 비목표로
  명시적으로 미룬다 — REQ-LDACCENT-007 이 이 잔여 갈래를 예외로 이름
  붙인다.
- **하나뿐인 액센트 규율은 안 바뀐다.** 감독 결정(2026-09-12) — 큐당 찍는
  액센트는 정확히 하나, 밝기만 누적한다 — 은 그대로다. 이 SPEC 은 "어느
  후보가 자격이 있는가"만 바꾼다.
- **콘솔로 나가는 명령 바이트는 안 바뀐다(값 결정 축에서).** 무영향 칸이
  값 라인 자체를 못 바꾼다는 사실(`_stepped`/`_rung_applied`)은 이 SPEC
  이전에도 참이었다 — 그래서 밝기(`Dimmer`)만으로 유일해지는 기존 골든
  대조군(TestHeadroomCaseIsUntouched, AC-3)의 `Dimmer` 진행값과 그 외
  속성 명령 바이트는 이 SPEC 이후에도 동일해야 한다. 달라지는 것은 `.ladder`
  튜플의 **셀 이름 보고**와, 채울 후보가 없을 때 새로 생기는 **유보 기록**
  뿐이다.
- **회전이 무영향 칸을 건너뛸 때는 남은 유효 후보를 마저 시도한다.** 깊이가
  가리키는 소박한 칸이 무영향이라고 그 회차의 액센트 자체를 포기하지 않는다
  — 같은 회전 목록 안에서 다음 유효 후보로 넘어간다(§6.1 "하나만"의 취지 —
  가능하면 뭔가는 찍는다).
- **유효 후보가 하나도 없으면 셀 이름을 지어내지 않고, 눈에 보이는 유보
  기록을 남긴다.** 빈 칸도 아니고 허위 셀 이름도 아니다 — 기존
  `SongCueWithheldMovement`(`songcue.py:472`)·`SongCueWithheldDarkness`
  (`songcue.py:361`) 가 이미 쓰는 "냈어야 했는데 못 냈다"보고 패턴을
  따른다.

## 3. 요구사항

`SHALL` 은 필수다. `<subject>` 는 이 파일이 다루는 계층(사다리 회전/보고)을
가리킨다.

| ID | 패턴·요구사항 | 규범 참조 |
|---|---|---|
| REQ-LDACCENT-001 | 찍는 액센트 회전 후보 집합은 **SHALL** 이 큐의 룩과 리그 해석, 그리고 이 큐가 속한 섹션의 라벨에 대해 실제로 관측 가능한 효과를 내는 칸으로만 한정된다 — (a) 그 룩 자신의 값 라인에서 대상 속성을 바꾸거나(zoom_pinch 는 `Zoom`, iris_pinch 는 `Iris`), (b) 별도 무대 명령(고정장비 그룹 선택 + 값)이 실제로 생성되는(blinder_or_flash, strobe_hit) 칸이어야 한다 — (b)의 생성 조건은 리그가 대응 그룹을 갖는 것과, 이 큐가 속한 섹션의 라벨이 §6 행(`intent_for_label`)을 가진 것 **둘 다**를 요구한다. | `_marking_accents`(`songcue.py:187`), `_rung_applied`/`_stepped`(`songcue.py:2447,2462`), `_accent_fixture_commands`(`songcue.py:2040`), `intent_for_label`(`server/looks/section_intent.py:156`) |
| REQ-LDACCENT-002 | **When** 이 큐가 선택한 룩의 `attributes` 에 `zoom_pinch`/`iris_pinch` 가 겨냥하는 속성(`Zoom`/`Iris`)이 없으면, 회전 후보 집합은 **SHALL** 그 회차·그 룩+리그 조합에서 해당 칸을 제외한다. | `_stepped`(`songcue.py:2462`) — 속성 부재 시 무영향 확인; `LADDER_ZOOM_PINCH`/`LADDER_IRIS_PINCH`(`songcue.py:115-116`) |
| REQ-LDACCENT-003 | **When** 리그 해석(`RoleResolution`)이 `blinder_or_flash`/`strobe_hit` 에 대응하는 역할(`_ACCENT_FIXTURE_ROLE`, `songcue.py:275`)로 묶인 고정장비 그룹을 하나도 갖지 않거나, **OR When** 이 큐가 속한 섹션의 라벨에 대해 `intent_for_label` 이 `None` 을 돌려주면(§6 행 부재), 회전 후보 집합은 **SHALL** 그 회차·그 룩+리그+라벨 조합에서 해당 칸을 제외한다. | `RoleResolution.groups_for`(`server/looks/resolver.py:125`), `_accent_fixture_commands`(`songcue.py:2040`, 빈 튜플 갈래), `intent_for_label`(`server/looks/section_intent.py:156`) |
| REQ-LDACCENT-004 | **When** 깊이가 정하는 소박한 회전 순서(`_marking_accents`/`_climb_rungs`)가 가리키는 칸이 REQ-002/003 에 의해 제외된 칸이면, 회전은 **SHALL** 같은 큐 안에서 같은 회전 순서를 유지한 채 다음으로 유효한 후보를 시도한다 — 유효 후보가 남아 있는 한 그 회차의 찍는 액센트 자체를 포기하지 않는다. | `_climb_rungs`(`songcue.py:2333`), `_marking_accents`(`songcue.py:187`) |
| REQ-LDACCENT-005 | **When** REQ-004 의 탐색을 다 거쳐도 그 회차·그 룩+리그+라벨 조합에서 유효한 찍는 액센트 후보가 하나도 남지 않으면, 사다리 구성 과정은 **SHALL** 그 자리에 무영향 칸 이름을 쓰지 않고, 그 대신 어느 섹션·어느 큐에서·어떤 이유로 못 채웠는지를 담은 명시적이고 눈에 보이는 유보 기록을 만든다 — 빈 칸으로 조용히 넘어가지 않는다. | `SongCueWithheldMovement`(`songcue.py:472`), `SongCueWithheldDarkness`(`songcue.py:361`) — 동형의 기존 유보 보고 패턴 |
| REQ-LDACCENT-006 | 번들 수준 보고는 **SHALL** REQ-005 가 만든 유보 기록 전량을, 개별 섹션 번들과 번들 전체 집계 양쪽에서, 기존 `withheld_movement`/`withheld_darkness`(`SongCueBundle`, `songcue.py:487`)와 같은 층위의 필드로 노출한다. | `SongCueBundle`(`songcue.py:487`), `build_songcue_bundle`(`songcue.py:752`) |
| REQ-LDACCENT-007 | 사다리 튜플(`SongCueSectionBundle.ladder`)에 실리는 찍는 액센트 셀 이름은 **SHALL NOT** 그 이름이 REQ-001의 세 조건(축 보유·그룹 보유·라벨의 §6 행 보유)을 만족한다고 확인되지 않은 채로 보고에 남는다 — 즉 `zoom_pinch`/`iris_pinch`/`blinder_or_flash`/`strobe_hit` 중 하나가 `.ladder` 에 나타나면 이 SPEC 이 필터링하는 세 조건은 전부 충족되었다는 뜻이어야 한다. **명시적 예외(§4 Out of Scope)**: `blinder_or_flash`/`strobe_hit` 가 §6 행(라벨 조건)을 만족하고 리그에 그룹도 있지만, 그 큐의 밝기 구간을 다른 큐가 이미 전부 소진해 `_unique_floor_climb` 가 `None` 을 돌려주는 네 번째 무영향 경로(`songcue.py:2072-2074`)는 이 SPEC 의 필터가 다루지 않는다 — 이 경로가 걸리면 위 세 조건을 모두 만족했음에도 `.ladder` 에 실린 이름이 무대 명령을 못 낼 수 있다. 이 하나의 명시적 예외를 벗어난 무영향 칸은 이 요구가 여전히 절대적으로 금지한다. | `.ladder` 필드 독스트링(`songcue.py:407` 근방); `_unique_floor_climb`(`songcue.py:1976`) 소진 갈래; 이 요구가 이 SPEC 의 핵심 불변식이다 |
| REQ-LDACCENT-008 | **While** 감독 결정(2026-09-12, §6.1 [HARD])이 정한 "큐당 찍는 액센트 하나, 밝기만 누적" 규율이 여전히 유효한 동안, REQ-002~005 의 필터링은 **SHALL** 그 규율을 어기지 않는다 — 필터가 후보를 줄이거나 유보로 접더라도 한 큐에 두 개 이상의 찍는 액센트 셀 이름이 동시에 `.ladder` 에 실리는 일은 없다. | `TestOneMarkingAccentPerCue`(`server/tests/test_songcue_ladder.py:470`), 감독 결정 2026-09-12 |

> **GEARS 키워드 메모(REQ-004/008)**: REQ-004 는 "회전이 제외된 칸을 가리킨다"는
> 관측 가능한 사건을 다루므로 `When`(이벤트-구동)으로 표기한다. REQ-008 은
> 감독 결정이라는 규율이 **계속 유효한 상태**를 전제하므로 `While`(상태-구동)로
> 표기한다 — 둘 다 능력 게이트(`Where`)가 아니라, GEARS 패턴표
> (`.claude/skills/moai-workflow-spec/SKILL.md` § GEARS Format)의 이벤트/상태
> 패턴에 더 정확히 대응한다(plan-auditor D6 정정).

## 4. 비목표

### Out of Scope — `_unique_floor_climb` 밝기 구간 소진 경로

- §6 행이 있고(라벨 조건 충족) 리그에 대응 그룹도 있지만, 그 밝기 구간
  (`intent.brightness` 의 floor~ceiling)을 **같은 곡의 다른 큐가 이미 전부
  소진**해 `_unique_floor_climb(floor, ceiling, (), emitted)`
  (`songcue.py:1976`, 호출은 `songcue.py:2072`)가 `None` 을 돌려주는 네 번째
  무영향 경로는 이 SPEC 이 다루지 않는다. **이유**: 이 경로를 사전에
  판별하려면 회전 후보를 고르는 시점에 그 시점까지의 `emitted` 누적 상태로
  `_unique_floor_climb` 를 미리 시뮬레이션해야 하는데, 그 시뮬레이션은
  `_accent_fixture_commands` 자신이 실행할 부작용(값을 실제로 `emitted` 에
  기입하는 것)과 같은 계산을 후보 선택 단계에서 한 번, 명령 생성 단계에서
  또 한 번 — 중복 실행해야 한다. 이는 이 SPEC 의 범위(§2 "필터는 회전 전,
  회차별 값 결정 전에 적용된다")를 넘어서는 아키텍처 변경이고, 실측상으로도
  드문 경로다(한 곡 안에서 같은 밝기 구간을 여러 큐가 동시에 소진할
  정도로 밀집한 입력이 필요하다). REQ-LDACCENT-007 이 이 예외를 이름 붙여
  명시한다 — 이 경로가 남아 있다는 사실이 REQ-007 의 절대 금지를 무효화하지
  않는다.

### Out of Scope — 회전 순서 자체의 재설계

- 무영향 칸이 아닌, 유효한 후보가 여럿일 때 **어느 것을 고르는가**의 기존
  순서(`_MARKING_ACCENTS` = 줌→블라인더→아이리스, `songcue.py:180`)는 이
  SPEC 이 바꾸지 않는다. REQ-004 는 그 순서 안에서 무영향 항목만 건너뛴다 —
  순서 자체의 우선순위 재배열은 별도 논의다.

### Out of Scope — 실기 콘솔 관측

- 이 SPEC 의 판정 수단은 로컬 `pytest` 뿐이다. 필터링이 실제 grandMA3
  콘솔에서 육안으로 확인되는지는 이 SPEC 의 판정 범위 밖이다 — 이 저장소의
  다른 songcue 계열 SPEC(SPEC-COPILOT-SONGCUE-001 등)과 같은 잔여 위험이다.

### Out of Scope — 정본 문서(§6/§7.1) 개정

- `docs/proposals/song-structure-lighting-standard.md` 의 §6/§7.1 문면
  변경은 포함하지 않는다 — 이 SPEC 은 그 문면이 요구하는 성질(큐당 액센트
  하나, 회차가 깊어지면 다른 요소를 더한다)을 **정직하게** 구현하는 것이지
  문면 자체를 바꾸는 것이 아니다.

### Out of Scope — 남은 t382 워크트리 정리

- `.claude/worktrees/t382`(및 `t394`/`t417`/`t423`의 동명 잔존 시험 파일)를
  치우는 것은 이 SPEC 의 일이 아니다 — 별개의 하우스키핑 카드다.

## 5. 검증 수단의 한계 (착수 전 고지)

이 SPEC 은 순수 로컬 계산 계층(`server/looks/songcue.py`)만 건드린다 — 콘솔
왕복이 필요한 요구사항이 없다. 판정은 전부 `uv run pytest` + `ruff check`/
`ruff format --check` 로 닫힌다.

| 판정 | 수단 | 콘솔 필요 |
|---|---|---|
| REQ-001~004 (필터·대체 탐색) | pytest, 합성 룩/리그 조합 | 아니오 |
| REQ-005~007 (유보 기록·보고 정직성) | pytest, 유보 필드 단언 | 아니오 |
| REQ-008 (하나만 규율 불변) | 기존 `TestOneMarkingAccentPerCue` + 신규 시험 | 아니오 |
| AC-3 골든 대조군 바이트 동일성 | `TestHeadroomCaseIsUntouched` 픽스처 갱신 후 재실행 | 아니오 |
