---
id: SPEC-COPILOT-PRESETIDEM-001
title: "프리셋 임포트를 멱등으로 — 매퍼가 슬롯만 보고 이름을 안 봐서 같은 CSV 가 복제된다"
version: "0.1.0"
status: draft
created: 2026-08-25
updated: 2026-08-25
author: orchestrator
priority: P1
phase: "v0.3.0 — LX-SEQ 연계 후속 결함"
module: "server/lxseq/preset_mapper.py, server/orchestrator/tools.py, server/tests/"
lifecycle: spec-anchored
tier: S
related_specs: [SPEC-COPILOT-LXSEQ-003, SPEC-COPILOT-UNREQ-001, SPEC-COPILOT-PRESETGUARD-001]
---

# SPEC-COPILOT-PRESETIDEM-001 — 프리셋 임포트 멱등성

> **칸반 카드 t87.** `import_lxseq_presets` 는 멱등이 아니다. 매퍼가 콘솔 슬롯
> **점유**만 읽고 **이름**을 한 번도 안 봐서, 같은 CSV 를 두 번 돌리면 프리셋이
> 통째로 복제된다.
>
> LXSEQ-003 **밖**이다 — 그 SPEC 의 progress.md:494 가 이미 그렇게 정리했다.

## §A 무엇이 틀렸나

### A.1 코드 (실측, `preset_mapper.py:165-202` 직독)

`candidate=1` 부터 올라가며 `occupied` 집합에 없는 번호를 모으고
`zip(storable, empty)` 로 짝짓는다. `occupied` 는 `_occupied_slots` 가 만든
**정수 집합**이다 — 이름은 어디에도 안 들어온다.

점유 슬롯을 피하는 것은 **슬롯 보증**이지 **동일성 보증**이 아니다.
REQ-LXSEQ3-007 이 답하는 질문은 「이 자리에 이미 뭐가 있나」이고,
이 SPEC 이 답하는 질문은 「이 프리셋이 이미 있나」다. 서로 다른 질문이다.

### A.2 실기 재현 (2026-08-25, 읽기 전용)

`--action preview --limit 0`, 승인 통로 0, 명령 조립 0:

- `DataPool/PresetPools/1` 에 6건 점유 (슬롯 1..6), `truncated` 없음
- 매퍼 `planned` 슬롯 = 7, 8, 9, 10, 11, 12
- `held` = 빈 목록

정본 dim 시트를 다시 쏘면 6건이 복제된다. 되돌릴 수단은 없다 —
프리셋 값은 되읽히지 않고, Delete 계열이 게이트 블랙리스트인지도 미측정이다.

### A.3 이름은 이미 매퍼 손안에 있다

`rig_object`(`tools.py:858`)는 `no` 와 `name` 을 **둘 다** 낸다. 툴이 그것을
`pool_section` 의 `objects` 에 그대로 싣는다(`tools.py:4812-4818`).
`_occupied_slots`(`preset_mapper.py:109`)가 `no` 만 읽을 뿐이다.

**새 판독 채널도, 새 왕복도 필요 없다.** 이미 온 것을 안 볼 뿐이다.

### A.4 착수 게이트 — 이 SPEC 이 서는 전제 (통과)

축 (a) 「이름이 이미 있으면 보류」는 **콘솔이 CSV Name 을 바이트 그대로 저장한다**
에 걸려 있다. 이름이 한국어라 절단·정규화·트림 위험이 있어 착수 전에 실측했다.

- 날조 대조군 `Patch/FixtureTypesZZZNotAThing/9999` → `ok=false` (거절이 정답)
- 6/6 `byte_equal`. 공백을 품은 `쇼 하이` 가 `0x20` 을 유지했고 단음절 `풀` 도
  NFC 조합형(`ed9280`) 그대로다
- casefold / strip / NFC 변형 비교도 전부 참 — 「관대한 비교로만 맞는다」가 아니라
  **바이트가 같다**

증거: `.moai/reports/t87/gate-name-roundtrip.md` + `name-roundtrip.json`
(커밋 a93f51c). 리드가 원격에서 독립 재집계했다.

**미측정**: 이 6건만 쟀다. 길이 상한, col/bm 계열 이름 왕복은 안 쟀다.

### A.5 콘솔에 나가는 이름은 preset_id 가 아니다 — 그리고 양쪽이 트림된다

`preset_store_commands(pool_no, slot, label)`(`server/presets/store.py:14`)의
3번째 인자가 `placement.name` 이다. 콘솔에 붙는 것은 `record.name`(`풀`, `쇼 하이`)
이지 `preset_id`(`DIM.FULL`)가 아니다.
**이름 비교를 preset_id 로 구현하면 6건 전부 안 맞는다.**

그리고 **양쪽이 독립적으로 트림한다** — 실측:

- 파서 `preset_parser.py:274` 가 모든 셀에 `.strip()` 을 건다
- 명령 빌더 `store.py:31` 이 `label.strip()` 을 한 번 더 건다
- 확인: CSV `"  풀  "` → `record.name` 이 `풀`(`ed9280`) → `Label Preset 1.7 '풀'`.
  안쪽 공백은 보존된다(`쇼 하이`)

그래서 `record.name` 과 콘솔 이름의 **정확 일치**가 옳은 비교다.
이것이 REQ-IDEM-002 가 서는 근거이고, 가정이 아니라 잰 값이다.

## §B 감독 결정 — 축 (a) per-record hold

이름이 이미 풀에 있는 레코드는 **그 레코드만** 보류하고, 나머지는 계획한다.

- **(b) 덮어쓰기 제외** — REQ-LXSEQ3-007 과 정면 충돌. 프리셋은 경고 없이
  덮어쓰고 값은 되읽을 수 없어 복구 수단이 없다.
- **(c) 호출자에게 위임 제외** — 점유를 보는 층은 매퍼뿐이다. 호출자마다
  다시 구현하면 한 벌은 틀린다.
- **전량 거절 제외** — REQ-LXSEQ3-008 의 부분 계획 금지는 **슬롯이 모자랄 때**를
  말한다. 이름 충돌은 그 반대다: 그 레코드의 목표 상태가 **이미 달성돼 있다.**
  보류는 부분 계획이 아니라 수렴이다.

## §C 요구사항

- **REQ-IDEM-001** `[Ubiquitous]` The 매퍼 **shall** 슬롯을 배정하기 **전에**
  콘솔이 답한 풀 이름과 대조해 이미 있는 레코드를 걸러낸다.
  배정 후 거르면 쓰지도 않을 슬롯을 예약해 없는 `shortfall` 이 생긴다.

- **REQ-IDEM-002** `[Ubiquitous]` The 이름 대조 **shall** **정확 일치**다 —
  casefold·NFC·추가 trim 어느 것도 쓰지 않는다. §A.4 가 바이트 일치를,
  §A.5 가 양쪽 트림을 실측했으므로 가장 엄격한 규칙이 성립한다.
  관대한 비교는 **미측정 변환**이라 사용자가 넣으려던 레코드를 조용히 떨어뜨린다.

- **REQ-IDEM-003** `[Unwanted]` The 매퍼 **shall not** 이름 충돌 보류를 기존
  `held`(파서 판정)에 섞는다. 섞으면 「19 중 6 계획 · 13 보류」 집계가
  **콘솔 상태 의존**이 되어 같은 CSV 가 날마다 다른 수를 보고한다.
  별도 필드 `already_present` 로 나른다.

- **REQ-IDEM-004** `[Ubiquitous]` The 산출물 **shall** `read` 를 보존한다 —
  `planned` + `held` + `already_present` 의 길이 합이 `read` 와 같다.
  세 번째 바구니를 안 읽는 소비자가 생기면 이 합이 깨지고, 그것이 신호다.

- **REQ-IDEM-005** `[Where]` **Where** 점유 슬롯 중 이름을 못 읽은 것이 있는 경우,
  the 매퍼 **shall** 거절이 아니라 `unverified` 에 한계를 싣는다.
  번호를 못 읽으면 **덮어쓰기**(복구 불가)라 fail-closed 가 옳지만, 이름을 모르면
  **중복**이다. 저장소가 이미 그 차이를 `refusal` 과 `unverified` 로 갈라 뒀다
  (REQ-LXSEQ3-014). 없는 상태를 근거로 도는 임포트를 통째로 막지 않는다.

- **REQ-IDEM-006** `[Ubiquitous]` The 매퍼 **shall** 한 CSV 안의 이름 중복도
  같은 규칙으로 막는다. 파서는 `duplicate_id` 만 막고 이름은 안 본다
  (`preset_parser.py:285` 직독) — 안 막으면 이 가드가 **첫 실행에서** 중복을 만든다.

- **REQ-IDEM-007** `[Ubiquitous]` The 툴 페이로드와 `guidance` **shall** 세 번째
  바구니를 싣는다. 「계획 + 보류」로만 보고하면 이미 있는 것이 어디로 갔는지
  아무도 모른다 — 매퍼 독스트링이 이미 경고하는 그 결함이다.

## §D 확인 한계 (그대로 안고 간다)

- **값 일치는 여전히 안 읽힌다.** 이 SPEC 은 *이름*만 답한다. 이름이 같아도
  값이 다를 수 있고, 그 레코드는 보류되어 값이 안 고쳐진 채 남는다.
  **「이미 있음」은 「맞게 있음」이 아니다.**
- **길이 상한 미측정.** 잰 6개는 전부 짧다.
- **col / bm 계열 이름 왕복 미측정** — 저장 가능 0건이라 콘솔에 이름이 없다.
- **범위 밖 인접 결함 1건 (안 고친다, 기록만).** 이름에 따옴표가 있으면
  `store.py:32` 가 `SpatialPointingError` 를 던진다 — 매퍼가 계획을 낸 **뒤에**
  터진다. 이 SPEC 은 그것을 안 건드린다.
