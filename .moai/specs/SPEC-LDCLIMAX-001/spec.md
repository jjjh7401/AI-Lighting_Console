---
id: SPEC-LDCLIMAX-001
title: "코러스 색 스냅 액센트 + 절정 지속시간 상한 — 정본 §6/§6.1 명문화"
version: "0.2.0"
status: in-progress
created: 2026-09-20
updated: 2026-09-20
author: jaihyun
priority: P2
phase: "Lighting Copilot v1.0 target"
module: "server/looks/songcue.py"
lifecycle: spec-anchored
tags: "songcue, accent-ladder, color-snap, climax-duration-cap, card-t425"
tier: L
related_specs: [SPEC-LDACCENT-001, SPEC-COPILOT-SONGCUE-001]
---

# SPEC-LDCLIMAX-001 — 코러스 색 스냅 액센트 + 절정 지속시간 상한

## HISTORY

| 일자 | 내용 |
|---|---|
| 2026-09-20 | 최초 작성. 큐 카드 t425 — 정본 `docs/proposals/song-structure-lighting-standard.md` §6.1 의 일곱 액센트 수단 중 **색 스냅**과, §6 의 **절정 지속시간 상한**(최강 효과 1~4박, 백색 플래시 1~2박, 그 뒤 통제된 룩 복귀) 둘 다 미구현임을 실측 확인하고 착수. 조사 상세는 `research.md`, 기술 설계는 `design.md`. |
| 2026-09-20 | **감독 결정 반영(같은 날 2차 개정)** — §5 의 미해결 질문 마커 해소. color_snap 은 기존 찍는 액센트 사다리의 정규 칸으로 편입된다(zoom_pinch/blinder_or_flash/iris_pinch/strobe_hit 와 같은 자격, 우선순위 없음, 별도 병행 메커니즘 아님) — `allow_color_snap` 기본값-거짓 스위치 모델은 폐기하고, 회전 후보에 무조건 포함하는 REQ-001 로 대체한다. 첫 실기 콘솔 검증 세션까지의 임시 안전판으로 `disable_color_snap`(REQ-012, §3.3)만 남긴다. 범위는 색 스냅 + 절정 지속시간 상한 둘 다 이 SPEC 하나에 유지(분리하지 않음). §1.1 이 인용한 songcue.py:109-110 배제 독스트링은 plan.md M2 에서 실제로 개정한다. 상세: plan.md §NC(해소 기록). |

## 1. 배경

### 1.1 실측 (2026-09-20, `origin/main` `2258048b` 기준 — SPEC-LDACCENT-001,
PR #472 병합 직후)

카드 t425 가 제기한 두 결함을 코드로 재확인했다(카드 요약이 아니라
`git show origin/main:` 로 직접 읽은 결과 — 상세 인용은 `research.md`):

1. **색 스냅이 일곱 수단 중 유일하게 구현되지 않았다.** `server/looks/
   songcue.py` 의 찍는 액센트 사다리(`_MARKING_ACCENTS`, 180-184행)는
   `zoom_pinch`/`blinder_or_flash`/`iris_pinch`(+`allow_strobe` 로
   `strobe_hit`) 넷을 이미 낸다 — 색 스냅만 **명시적으로 배제**돼 있다
   (109-110행 독스트링: "색 스냅도 뺀다 — 정본 §7 이 「코러스 1의 색은
   되돌아와야 한다」고 못박으므로 지배색을 갈아치우는 것은 상승이 아니라
   위반이다"). 이 SPEC 은 그 배제 이유(§7 충돌)를 피하는 다른 정의로
   색 스냅을 구현하고, 그 배제 문면 자체도 이 정의로 갱신한다(§2,
   research.md §4, plan.md M2 — 프로즈만 바꾸는 것이 아니라 실제 코드
   주석을 고친다).
2. **절정 지속시간 상한이 어디에도 없다.** `blinder_or_flash`/`strobe_hit`
   가 큐 값을 바꾼 뒤 그 극단 상태를 몇 박 만에 통제된 룩으로 되돌리는
   메커니즘이 이 저장소 어디에도 없다(`grep -rn "박\|beat" server/looks`
   0건 — `server/design/energy.py` 의 `beats_to_seconds` 변환 함수 자체는
   있으나 소비하는 "복귀" 로직이 없다).
3. `AccentDecision.hits`(`server/design/song_plan.py:290`)는 실제로
   생산자가 없다(카드의 관찰이 정확함, research.md §2) — 다만 이 필드는
   경로 A(감독 인터뷰, 오늘도 표시 전용)의 것이고, 이 SPEC 의 대상인 경로 B
   (`server/looks/songcue.py`, 실제 값을 바꾸는 파이프라인)는 `AccentDecision`
   을 아예 쓰지 않는다 — research.md §2 가 두 파이프라인의 존재와 근거를
   전량 기록한다.

## 2. 범위 결정

- **대상 파이프라인은 경로 B(`server/looks/songcue.py`, `build_songcue_bundle`)
  뿐이다.** §6 이 규율하는 실제 무대 값이 나가는 유일한 경로이고,
  SPEC-LDACCENT-001 이 이미 이 파일의 찍는 액센트 사다리를 다듬었다. 경로
  A(`AccentDecision`/`server/web/session.py`)는 오늘 표시 전용이라 REQ 를
  걸 대상이 없다(§4 비목표).
- **색 스냅은 "§7 이 이미 돌아오라고 요구하는 색을 즉시 전환(페이드 0)으로
  낸다"로 정의한다** — songcue.py 자신이 명시 거부한 "지배색을 새로
  갈아치우는" 해석은 채택하지 않는다(근거: research.md §4).
- **감독 결정(2026-09-20) — color_snap 은 회전의 정규 칸이다.** color_snap
  은 기존 찍는 액센트 사다리의 **정규 칸**으로 편입된다 — `zoom_pinch`/
  `blinder_or_flash`/`iris_pinch`/`strobe_hit` 와 같은 자격이고, 이 넷보다
  **우선하지 않으며**, 별도 **병행** 메커니즘으로 돌지 않는다(단일
  회전, REQ-LDCLIMAX-005 의 큐당 액센트 하나 규율 그대로 적용). 회전 후보
  집합에는 **무조건** 포함되고(REQ-001), SPEC-LDACCENT-001 이 이미 만든
  무영향-칸 필터(`_accent_is_effective`)가 REQ-002(§7 색 집합 제한)·
  REQ-004(무영향 배제)로 그 자리를 대신한다 — 축 없는 `zoom_pinch` 가
  오늘 조용히 걸러지는 것과 정확히 같은 방식이고, 남는 유효 후보가
  없으면 SPEC-LDACCENT-001 의 유보 보고(`SongCueWithheldAccent`)가 그대로
  적용된다(새로 짓지 않는다). `_marking_accents`(`allow_strobe` 가
  `LADDER_STROBE_HIT` 를 붙이는 바로 그 함수)가 항상 맨 끝에
  `LADDER_COLOR_SNAP` 을 덧붙인다 — `_MARKING_ACCENTS` 상수 튜플 자체는
  손대지 않는다(strobe 와 같은 방식, §D). 이전 판(§3 NC-1, 이제 폐기)의
  `allow_color_snap`(기본값 거짓의 항상-꺼짐 스위치) 모델은 이 결정으로
  대체된다.
- **임시 안전판 — `disable_color_snap`.** 이 SPEC 의 판정 수단은 로컬
  pytest 뿐이고 실기 콘솔 관측은 범위 밖이다(§6). 첫 실기 콘솔 검증
  세션에서 예기치 못한 결함이 보이면 즉시 끌 수 있도록
  `disable_color_snap: bool = False`(기본값 = 끄지 않음, 즉 REQ-001 대로
  활성)만 남긴다(REQ-012, §3.3) — 이것은 영구 설계가 아니라 **그 세션까지의
  임시 킬스위치**다. 플립 주체는 그 콘솔 세션을 수행하는 사람이고, 플립
  시점은 그 세션에서 결함이 관측된 직후다(끌 때). 그 세션이 결함 없이
  통과하면, 또는 발견된 결함이 후속 수정으로 닫히면, 이 스위치는 후속
  커밋에서 **제거**한다 — 무기한 방치되는 죽은 기본값으로 남기지 않는다.
- **절정 지속시간 상한은 고정장비 그룹을 켜는 두 칸(`blinder_or_flash`
  → §6 "백색 플래시" 행 2박, `strobe_hit` → §6 "최강 효과" 일반 행 4박)에만
  적용한다.** 룩 자신의 값만 바꾸는 칸(줌·아이리스·색 스냅)은 §6 의
  밝기(D-레벨) 예산이 이미 규율하는 축이라 별도 지속시간 상한을 얹지
  않는다(design.md §4 대조표).
- **하나뿐인 액센트 규율은 안 바뀐다.** 감독 결정(2026-09-12) — 큐당 찍는
  액센트 정확히 하나, 밝기만 누적 — 은 색 스냅에도 그대로 적용된다.
- **삽입되는 복귀 큐는 조용히 끼우지 않는다.** 번들 보고에 명시적으로
  표식을 남긴다(SongCueWithheldMovement/Darkness/Accent 와 같은 "냈어야
  했는데/뭘 했는지 조용히 넘어가지 않는다" 보고 규율).

## 3. 요구사항

`SHALL` 은 필수다. `<subject>` 는 `server/looks/songcue.py` 의 큐 조립
계층을 가리킨다.

### 3.1 색 스냅 액센트 (REQ-LDCLIMAX-001~005)

| ID | 패턴·요구사항 | 규범 참조 |
|---|---|---|
| REQ-LDCLIMAX-001 | 찍는 액센트 회전 후보 집합은 **SHALL** `color_snap` 을 기존 칸(줌→블라인더→아이리스[→스트로브, `allow_strobe` 참일 때]) 뒤 **마지막** 후보로 항상 포함한다 — 기존 네 칸보다 우선하지 않는다(감독 결정 2026-09-20, §2). | `_marking_accents`(`songcue.py:260`), `allow_strobe` 가 `LADDER_STROBE_HIT` 를 붙이는 것과 같은 형상(`songcue.py:131-139`) |
| REQ-LDCLIMAX-002 | **When** `color_snap` 이 후보이고 그 회차가 §7 색 복귀 규율이 적용되는 반복 라벨(코러스 등)에 속하면, 회전은 **SHALL** 코러스 1 이 이미 쓴 팔레트 색 집합 밖의 색을 `color_snap` 의 대상으로 고르지 않는다 — §7 [HARD] "코러스 1의 색은 이후 코러스에서 되돌아와야 한다"를 어기지 않는다. | 정본 §7(HISTORY 인용), `songcue.py:109-110`(이 SPEC 이 갱신하는 배제 문면, §2) |
| REQ-LDCLIMAX-003 | **When** 사다리가 `color_snap` 을 이 큐의 찍는 액센트로 확정하면, 그 큐를 조립하는 코드는 **SHALL** 그 큐의 페이드 시간을 0 으로 강제한다(크로스페이드 없는 즉시 전환). | 정본 §6.1 "색 스냅"(진짜 fade-0 순간 색 변화) |
| REQ-LDCLIMAX-004 | **When** 사다리가 `color_snap` 을 이 큐의 찍는 액센트로 확정하면, 그 큐가 내는 색은 **SHALL** 직전에 저장된 큐의 색과 달라야 한다 — 이미 같은 색이면 이 칸은 무영향이라 회전 후보에서 제외된다(`_accent_is_effective` 와 같은 무영향-칸 판정 규율, SPEC-LDACCENT-001). | `_accent_is_effective`(`songcue.py:204-221`) |
| REQ-LDCLIMAX-005 | **While** 감독 결정(2026-09-12, §6.1 [HARD])의 "큐당 찍는 액센트 하나, 밝기만 누적" 규율이 유효한 동안, `color_snap` 이 선택된 큐는 **SHALL** 같은 큐에 다른 찍는 액센트 칸(`zoom_pinch`/`iris_pinch`/`blinder_or_flash`/`strobe_hit`)을 동시에 싣지 않는다. | `TestOneMarkingAccentPerCue`(`server/tests/test_songcue_ladder.py:470`), 감독 결정 2026-09-12 |

### 3.2 절정 지속시간 상한 (REQ-LDCLIMAX-006~011)

| ID | 패턴·요구사항 | 규범 참조 |
|---|---|---|
| REQ-LDCLIMAX-006 | **When** 사다리가 `blinder_or_flash` 또는 `strobe_hit` 를 이 큐의 찍는 액센트로 확정하고 이 곡의 BPM 이 선언되어 있으면, 절정 지속시간 상한 계산은 **SHALL** 그 큐 시작 시각으로부터 상한 박수(`blinder_or_flash`=2박, `strobe_hit`=4박) 뒤의 시각을 `beats_to_seconds` 로 구한다. | 정본 §6 "절정의 지속 시간에 상한이 있다"(최강 효과 1~4박, 백색 플래시 1~2박), `beats_to_seconds`(`server/design/energy.py:221-233`) |
| REQ-LDCLIMAX-007 | **When** REQ-006 이 계산한 복귀 시각이 그 큐가 속한 섹션의 다음 큐 시작 시각보다 이르면, 큐 조립은 **SHALL** 그 복귀 시각에 새 큐를 삽입해 그 회차에서 사다리를 오르지 않았을 때의 기준 값(통제된 룩)으로 되돌린다. | 정본 §6 "그 뒤 통제된 룩으로 복귀한다" |
| REQ-LDCLIMAX-008 | **When** REQ-006 이 계산한 복귀 시각이 다음 큐의 시작 시각과 같거나 그보다 늦으면, 큐 조립은 **SHALL** 새 큐를 삽입하지 않는다 — 다음 큐로의 자연 전환이 이미 상한을 지킨다. | `cue_density.py` "4마디짜리 꼬투리 큐는 연출이 아니라 잡음이다"(35행)와 같은 방향의 잡음-회피 규율 |
| REQ-LDCLIMAX-009 | **Where** 이 곡의 BPM 또는 박자표가 선언되지 않았으면, 절정 지속시간 상한 메커니즘은 **SHALL** 아무 큐도 삽입하지 않는다 — 이 SPEC 이전과 바이트 동일하다. | `cue_density.py:52-62`("안 재고는 안 쓴다") |
| REQ-LDCLIMAX-010 | **When** 절정 지속시간 상한이 복귀 큐를 삽입하면, 번들 보고는 **SHALL** 그 사실을 원래의 찍는 액센트 큐와 구분 가능한 명시적 필드(예: `SongCueBundle.climax_returns`)로 노출한다 — 조용히 끼워 넣어 큐 번호 체계만 밀리고 감독이 못 알아보게 하지 않는다. | `SongCueWithheldMovement`/`Darkness`/`Accent`(SPEC-LDACCENT-001)와 같은 "명시적이고 눈에 보이는" 보고 패턴 |
| REQ-LDCLIMAX-011 | **While** REQ-006~008 의 절정 지속시간 상한이 적용되는 동안, 기존 찍는 액센트 큐 자신의 값(`Dimmer`/`Zoom`/`Iris`/색 등)과 사다리 회전·유보 보고(SPEC-LDACCENT-001)는 **SHALL** 이 SPEC 이전과 동일하게 유지된다 — 상한 메커니즘은 완성된 번들 뒤에 큐를 더할 뿐, 기존 큐의 값 결정 경로를 바꾸지 않는다. | design.md §2 "조립 이후, 별도 함수" |

### 3.3 임시 안전판 (REQ-LDCLIMAX-012)

| ID | 패턴·요구사항 | 규범 참조 |
|---|---|---|
| REQ-LDCLIMAX-012 | **Where** 호출자가 `disable_color_snap=True` 로 색 스냅을 명시적으로 끈 곡 조립에서, 찍는 액센트 회전 후보 집합은 **SHALL** `color_snap` 을 후보에서 제외한다 — 기본값(`disable_color_snap=False`)에서는 REQ-001 이 그대로 적용된다. 이 스위치는 첫 실기 콘솔 검증 세션까지의 임시 킬스위치이며 영구 설계가 아니다(§2 임시 안전판). | §2 임시 안전판, `allow_strobe` 형상(호출자-불투명 플래그 패턴, `songcue.py:131-139`) |

> **GEARS 키워드 메모**: REQ-001 은 예외(REQ-012)가 없는 한 항상 성립하는
> 규율이므로 `Ubiquitous`(무조건)로 표기한다. REQ-009·REQ-012 는 호출자가
> 켠/끈 능력(BPM 선언 여부·안전판 플래그)을 전제 조건으로 걸므로
> `Where`(능력 게이트)다. REQ-002~004·006~008·010 은 특정 사건(사다리
> 확정, 시각 비교, 삽입)을 다루므로 `When`(이벤트-구동)이다. REQ-005·011
> 은 규율이 **계속 유효한 상태**를 전제하므로 `While`(상태-구동)이다.

## 4. 비목표

### Out of Scope — 감독 인터뷰 경로(`AccentDecision`, 경로 A)

- `server/design/song_plan.py` 의 `AccentDecision`/`server/web/session.py`
  의 `_accent_decision` 이 만드는 문자열 라벨(`"climax accent"`, `"white
  flash"` 등)은 이 SPEC 이 손대지 않는다 — research.md §2 확인대로 오늘
  화면 표시(`apply_cue_sheet_section`) 전용이고 무대 명령을 만들지 않는다.
  이 경로를 경로 B 와 같은 수준으로 끌어올리는 일은 이 SPEC 의 범위를
  넘는 별도 SPEC 이다.

### Out of Scope — `AccentDecision.hits` 필드 채우기

- 카드가 관찰한 `hits: tuple[Mapping[str, object], ...]` 필드는
  research.md §2 확인대로 생산자가 없다. 이 필드는 경로 A 소속이고, 이
  SPEC 은 경로 A 를 다루지 않으므로(위 항목) 이 필드를 채우는 작업도
  범위 밖이다.

### Out of Scope — 룩 자신의 값만 바꾸는 칸의 지속시간 상한

- `zoom_pinch`/`iris_pinch`/`color_snap` — 고정장비 그룹을 켜지 않고 룩
  자신의 값(D-레벨 예산 안)만 바꾸는 칸에는 절정 지속시간 상한을 얹지
  않는다(§2, design.md §4 대조표). §6 표의 밝기 상한이 이미 이 축을
  규율한다고 읽었다 — 이 해석이 틀렸다면 별도 카드다.

### Out of Scope — 정본 문서(§6/§6.1/§7) 개정

- `docs/proposals/song-structure-lighting-standard.md` 문면 변경은
  포함하지 않는다 — 이 SPEC 은 그 문면이 이미 요구하는 성질을 구현하는
  것이지 문면 자체를 바꾸는 것이 아니다.

### Out of Scope — 실기 콘솔 관측

- 이 SPEC 의 판정 수단은 로컬 `pytest` 뿐이다. 색 스냅·복귀 큐가 실제
  grandMA3 콘솔에서 육안으로 확인되는지는 이 SPEC 의 판정 범위 밖이다 —
  이 저장소의 다른 songcue 계열 SPEC 과 같은 잔여 위험이다.

## 5. 감독 결정 기록 (2026-09-20 해소)

카드 t425 본문의 미해결 질문 "어느 수단을 기본으로 쓸지"는 감독 확인으로
해소됐다. 세 축의 답:

1. **어느 곡/세트 위치에서 켜는가** — 조건부 판단이 아니다. color_snap 은
   `disable_color_snap=True` 로 명시적으로 끄지 않는 한 **항상** 활성이다
   (§2 임시 안전판, REQ-012). 전 곡 공통이며 장르·세트 위치별 분기는
   두지 않는다.
2. **`_MARKING_ACCENTS` 기존 칸 사이에서의 우선순위** — **맨 뒤**(줌→
   블라인더→아이리스[→스트로브] 뒤, 기존 네 칸보다 우선하지 않는다).
   design.md §1.1 의 잠정안이 그대로 확정됐다(REQ-001).
3. **대체하는지 병행하는지** — 대체도 병행도 아니다. 같은 회전 안의 한
   후보다 — 큐당 액센트 하나 규율(REQ-005)이 그대로 적용되고, 별도
   발생 조건이나 병렬 트랙을 두지 않는다.

이 해소는 plan.md §NC(해소 기록)와 같은 근거를 공유한다.
Implementation Kickoff Approval 은 이 해소를 전제로 통과한다.

## 6. 검증 수단의 한계 (착수 전 고지)

이 SPEC 은 순수 로컬 계산 계층(`server/looks/songcue.py`)만 건드린다 —
콘솔 왕복이 필요한 요구사항이 없다. 판정은 전부 `uv run pytest` +
`ruff check`/`ruff format --check` 로 닫힌다.

| 판정 | 수단 | 콘솔 필요 |
|---|---|---|
| REQ-001~005 (색 스냅) | pytest, 합성 룩/리그 조합 | 아니오 |
| REQ-006~009 (지속시간 상한 계산·삽입 조건) | pytest, BPM 유/무 두 갈래 | 아니오 |
| REQ-010 (삽입 보고) | pytest, `climax_returns` 필드 단언 | 아니오 |
| REQ-011 (기존 값 불변) | 기존 SPEC-LDACCENT-001 골든 시험 재실행 | 아니오 |
| REQ-012 (`disable_color_snap` 안전판) | pytest, `disable_color_snap=True` 픽스처 + 후보 제외 단언 | 아니오 |
