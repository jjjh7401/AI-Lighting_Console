---
id: SPEC-COPILOT-LXSEQ-002
title: "LX-SEQ 연계 2단계 — RIG GROUP 시트와 001 FID 매핑표에서 onPC 그룹으로"
version: "0.1.0"
status: draft
created: 2026-08-24
updated: 2026-08-24
author: manager-spec
priority: P1
phase: "v0.2.0 target — LX-SEQ 연계 2단계(그룹); 3단계 프리셋/FX, 4단계 시퀀스/큐는 후속 SPEC"
module: "server/lxseq/ (신규 group_parser, group_mapper), server/orchestrator/tools.py (신규 툴 1종 등재), server/sheets/registry.py (group 행), server/web/session.py (행 계수기), server/tests/fixtures/lxseq/ (GROUP CSV 사본), server/groupgen 및 server/spatial (재사용, 무변경)"
lifecycle: spec-anchored
tags: "lxseq, rig-pack, group, csv, import, create_arrangement_groups, sheet-registry, unmeasured-membership, payload-budget, grandma3"
tier: M
related_specs: [SPEC-COPILOT-LXSEQ-001, SPEC-COPILOT-GROUPGEN-001, SPEC-COPILOT-RESTORE-001, SPEC-COPILOT-FILEARG-001, SPEC-COPILOT-TRUNCATE-001]
---

# SPEC-COPILOT-LXSEQ-002 — LX-SEQ 연계 2단계: RIG GROUP 시트에서 onPC 그룹으로

> **칸반 카드 t18, 4단계 중 2단계.** 조명감독 산출물(LX-SEQ v2.1 RIG 팩)의 **GROUP 시트**를 읽어, MA 코파일럿에 **이미 있는** `create_arrangement_groups` 툴로 grandMA3 onPC에 그룹을 만든다. 신규 코드는 **파서, 매퍼, 툴 등재 1종, 시트 종류 레지스트리 행 1개**뿐이다. 슬롯 측정, 점유 차단, 명령 조립, 승인 게이트, 발화, 재조회는 전부 기존 `server/groupgen/write.py` 에서 `create_arrangement_groups` 로 이어지는 경로를 그대로 쓴다.
>
> **1단계와 같은 다리 놓기다.** 001이 패치 CSV를 `patch_fixtures` 에 이었듯, 002는 그룹 CSV와 001의 FID 매핑표를 `create_arrangement_groups` 에 잇는다. 엔진 신설 0건.
>
> **감독 결정(2026-08-21, 001에서 확정 — 본 SPEC에도 구속력 있음)**: ① 신규 코드는 파서와 매퍼만. 콘솔 쓰기 경로를 새로 만들지 않는다. ② 4단계 분할, 각 단계 onPC 실기 검증. 본 SPEC은 2단계. ③ **점유 슬롯은 절대 쓰지 않는다.**

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 |
|---|---|---|---|
| 0.1.0 | 2026-08-24 | manager-spec | 최초 작성 (draft, Tier M). 아티팩트 3종(spec, plan, acceptance)과 progress. REQ **16건**, AC **16건**(실기 1건 포함), 마일스톤 **5개**(M0에서 M4까지), clarification 마커 **2건**(plan.md 의 A.4 — 슬롯 번호 권위, 입력 파일 수). 카드 t18이 「해소」로 적은 두 지뢰(12 대 18, 실기 질문)는 재확인했고, 그 밖에 **판독으로 새로 드러난 사실 4건**을 A.2에 등록한다. |

---

## A. 개요

**한 줄**: `LXSEQ_RIG_01_ShowBase_r3.group.csv`(18행, 열은 GroupNo, Name, Members, Purpose)를 읽어 그룹 레코드로 정규화하고, 001의 FID 매핑표(패치 CSV의 Group 라벨에서 FID 목록으로)와 **닫힌 파생 규칙 6종**으로 각 그룹의 멤버 FID를 확정한 뒤, 기존 `create_arrangement_groups` 툴이 받는 인자 묶음(`groups` 목록의 name과 fids 쌍)으로 번역해 배치 단위로 위임한다. 시트가 선언한 슬롯 번호와 콘솔이 답한 빈 슬롯이 어긋나면 **계획을 내지 않고 대조표를 보고한다.** 멤버십은 어느 채널로도 되읽히지 않으므로 「검증했다」고 말하지 않고 구조적 미검증 고지를 그대로 싣는다.

### 사전 확정 사실 (이 트리에서 실측, 근거를 각 항목에 인용한다)

#### A.1 카드가 「해소」로 적은 것 — 재확인됨

**12 대 18의 정체.** 실측으로 갈렸다.

| 출처 | 개수 | 내용 |
|---|---|---|
| `server/tests/fixtures/lxseq/LXSEQ_RIG_01_ShowBase_r3.patch.csv` 의 Group 열 | **12** | BACK 12, BLIND 6, FOH 8, HAZE 2, KEY 6, MOVER-D 8, MOVER-U 8, SIDE-L 6, SIDE-R 6, STROBE 4, WASH-D 10, WASH-U 10 = **86행** |
| `server/tests/fixtures/lxseq/LXSEQ_RIG_01_ShowBase_r3.group.csv` | **18** | 위 12에 파생 6 |

차이 6개는 전부 파생이고, 규칙은 Members 열이 산문으로 적고 있다.

| GroupNo | Name | 규칙 |
|---:|---|---|
| 1 | ALL | 전 픽스처 (FOLLOW 제외) — 패치 CSV 86행 전부 |
| 7 | SIDE-ALL | SIDE-L 과 SIDE-R 의 합집합 |
| 10 | WASH-ALL | WASH-U 와 WASH-D 의 합집합 |
| 13 | MOVER-ALL | MOVER-U 와 MOVER-D 의 합집합 |
| 17 | ODD | MOVER-ALL 중 FID 홀수 — 501, 503, 505, 507, 521, 523, 525, 527 |
| 18 | EVEN | MOVER-ALL 중 FID 짝수 — 502, 504, 506, 508, 522, 524, 526, 528 |

**FOLLOW-1은 패치 CSV에 없다.** `rig_data.py` 의 FIXTURES에는 있으나 Ch 가 0(수동, DMX 없음)이라 패치 대상이 아니고, 001의 파서가 이미 그 행을 제외행으로 분리한다. 그래서 ALL 의 "FOLLOW 제외"는 **추가 규칙이 아니라 패치 CSV 자체의 성질**이다 — 별도 제외 논리를 만들지 않는다.

**실기 질문은 GROUPGEN-001이 답해 뒀다. 새 프로브는 필요 없다.** 승계 사항 넷.

1. **그룹 풀 자체는 읽힌다.** `state DataPool/Groups` 의 childCount, 슬롯 출현, `prop Name` 재조회. AC-GROUPGEN-040 실측(풀 childCount 5에서 7로).
2. **멤버십은 이 프로젝트가 시도한 어느 채널로도 되읽히지 않았다.** 이 문장의 정확한 등급은 A.2 넷째 항이 정한다.
3. **점유 슬롯 덮어쓰기는 거부가 아니라 GUI 확인 다이얼로그다.** 무인 발화는 `User Canceled Command` 로 취소되지만 조작자가 OK를 누르면 덮인다. Delete는 블랙리스트이고 restore가 없어 복구 불가다. 그래서 REQ-GROUPGEN-022 정적 차단이 강제 제약이며, `select_group_slot`(`server/groupgen/write.py:182`)이 이미 그것을 구현한다.
4. **AC-GROUPGEN-040 패턴을 그대로 상속한다.** `unverified` 목록에 membership 을 담는 구조적 고지, `human_check_commands` 동봉, 슬롯 존재와 이름만 재조회. `build_group_write_plan` 이 반환값으로 이미 전부 싣는다(`server/groupgen/write.py:409-434`). 002가 다시 만들 것이 없다.

#### A.2 판독으로 새로 드러난 것 4건 (카드에 없다)

**첫째. Members 열은 멤버십 판정에 쓸 수 없다. 한 열에 문법이 넷이다.**

    KEY 6대                      라벨에 개수
    SIDE-L + SIDE-R              라벨 합집합
    전 픽스처 (FOLLOW 제외)      전체에서 제외
    MOVER-ALL 홀수 FID           다른 그룹에 대한 술어

네 문법을 한 파서로 받으면 규칙이 늘 때마다 파서가 늘고, 오해석이 **조용히** 잘못된 그룹을 만든다. 멤버십을 못 읽으므로 사후 적발도 안 된다. 그래서 **파싱하지 않는다.** 멤버십은 001의 FID 매핑표에서 오고, 파생 6종은 코드의 닫힌 규칙이며, Members 는 개수를 적은 행에 한해 **교차검증에만** 쓴다. 이것이 카드가 말한 "12는 옮기고 6은 규칙으로 만든다"의 정확한 형태다.

**둘째. 18개는 한 호출로 못 쓴다. 상한이 16이다 (실측). 그리고 분할 지점은 12가 아니라 16이다.**

    server/groupgen/write.py:66        DEFAULT_GROUP_PLAN_CAP = 16
    server/groupgen/write.py:222       guard_plan_size 가 GROUP_PLAN_TOO_LARGE 를 던진다
    server/orchestrator/tools.py:7101  build_group_write_plan 호출에 max_plan_size 인자 없음

`create_arrangement_groups` 는 max_plan_size 를 노출하지 않으므로 18개를 한 번에 넘기면 GROUP_PLAN_TOO_LARGE 로 거부된다. 이는 결함이 아니라 설계된 슬롯 경제 가드다. `guard_plan_size` 독스트링이 부분 계획을 최악의 결과라고 적는다. 따라서 두 배치로 나눈다.

**분할은 GroupNo 1..16 과 17..18 이다.** plan-phase 는 「기본 12와 파생 6」으로 적었는데 **그것은 틀렸고 M2 구현에서 드러났다.** 엔진이 빈 슬롯을 준 순서대로 짝지으므로, 기본을 먼저 넘기면 KEY(GroupNo 2)가 슬롯 1을 받는 식으로 18개 전부 밀린다. 카드의 "12는 옮기고 6은 규칙으로 만든다"는 멤버십의 **출처**에 대한 말이지 배치 순서에 대한 말이 아니었는데, 내가 배치 규칙으로 과독했다.

각 호출이 풀을 다시 재므로 2차 호출은 1차가 만든 16개를 점유로 보고 17·18을 받는다. 올바른 동작이다.

**셋째. ALL 그룹의 선택 줄이 1201바이트다. 여백은 M2 에서 측정했고, 전송층은 이 경로를 검사하지 않는다.**

    server/spatial/choreography.py:341
        선택 줄은 Fixture N 을 플러스 기호로 이어 붙인다. 구간 압축 없음

패치 CSV 86 FID로 이 트리에서 직접 계산한 값이 **1201 bytes** 다. 상한 쪽 실측은 이렇다.

    server/bridge/protocol.py:33          MAX_PLUGIN_CALL_BYTES = 2048
    console/lua/copilot_responder.lua:34-35
        "Live-measured 2026-07-24 (onPC 2.4.2): the cmd_keyword transport rides
         the MA3 command line, which silently drops commands past ~2048 bytes"

**M2 에서 측정했다. 두 가지가 바뀌었다.**

**첫째, 예산은 번들이 아니라 줄 단위다.** `run_commands` 가 `for command in commands:` 로 **한 줄씩** 발화한다(`server/orchestrator/tools.py:1821`). 그러므로 5줄을 합친 길이가 아니라 **가장 긴 한 줄**이 상한에 걸린다.

**둘째, 이 리그의 최장 줄은 상한 안이다.**

    ALL 선택 줄                    1201 bytes
    build_exec_request 로 감싼 뒤    1243 bytes   (프레이밍 42 bytes)
    MAX_PLUGIN_CALL_BYTES           2048 bytes
    여백                             805 bytes

**그런데 게이트는 여전히 필요하고, 오히려 더 필요하다.** 전송층의 예산 검사기 `_validate_plugin_call_budget` 이 `introspect` 와 `props` 에만 걸려 있고 **`exec` 에는 안 걸려 있다**(`server/bridge/protocol.py:217·233`). 실측했다 — 5475바이트 명령을 `build_exec_request` 에 넣으니 예외 없이 5517바이트 줄이 나왔고, **같은 크기에서 `build_introspect_query` 는 ProtocolError 를 던졌다**(양성 대조군). 즉 그룹 쓰기가 타는 경로에는 **아무 검사도 없다.**

그러므로 이 리그는 오늘 안전하지만 **더 큰 리그는 조용히 깨진다.** 실패 형태가 조용한 누락이고 멤버십은 되읽히지 않으므로 사람도 기계도 적발하지 못한다. REQ-LXSEQ2-011 의 발화 전 측정이 **이 경로의 유일한 방어선**이다.

**넷째. 「원리적 불가」 판정은 미측정으로 하향됐다. 문면을 되살리지 않는다.**

`SPEC-COPILOT-RESTORE-001/readability-survey.md` 의 A.2와 A.5가 판정 전제의 만료를 근거로 그룹 멤버십을 **「원리적 불가」에서 「미측정」으로 내렸다.** 같은 문서 D.9는 범위를 좁혀 읽으라고 못박는다. 전량 관측된 것은 **풀 노드**(`DataPool/Groups`, 필드 16개, 절단 없음, 멤버 열거 필드 없음)이고, **개별 그룹 오브젝트**(`DataPool/Groups/13`)는 그룹이 있는 쇼파일이 없어 재지 못했다.

    현재 등급   그룹 존재와 개수는 읽힘. 그룹 이름도 읽힘. 그룹 멤버십은 미측정
    미발사      Count 과 Ptr 을 쓰는 둘째 경로, Executor 우회 넷째 경로
    막힌 이유   그룹이 있는 쇼파일 부재 (카드 t22)

`server/groupgen/write.py:412-422` 는 이미 고친 문면을 달고 있다. **본 SPEC의 어느 문장도 「원리적 불가」나 「읽을 수 없다」로 단정하지 않는다.** 정확한 문장은 이것이다 — 이 프로젝트가 시도한 어느 채널로도 되읽히지 않았고, grandMA3가 노출하는지 여부는 미측정이다. 어느 쪽이든 오늘 백업도 복구도 없다.

---

## B. 배경과 문제

001이 86대를 패치했다. 그러나 그룹이 없으면 조명감독은 콘솔에서 한 대씩 골라야 하고, 곡 파일(`LXSEQ_SAMPLE_01_Sugar`)이 참조하는 그룹 번호 체계가 성립하지 않는다. RIG 팩은 그룹 18개를 **번호까지 정해** 선언하지만, 그 선언을 콘솔로 옮기는 경로가 없다.

동시에 이 도메인은 이 저장소에서 가장 위험한 축을 하나 갖고 있다. **쓴 것이 이 프로젝트가 시도한 어느 채널로도 되읽히지 않았다.** 잘못 만든 그룹은 오류를 내지 않고, 사후에 발견되지도 않으며, 삭제도 복구도 막혀 있다. 그래서 이 SPEC의 설계 자세는 「많이 만든다」가 아니라 **「어긋나면 아무것도 만들지 않는다」**이다.

---

## C. 범위

### C.1 In Scope

- `server/lxseq/group_parser.py` — GROUP CSV 바이트에서 그룹 레코드로 (순수 함수)
- `server/lxseq/group_mapper.py` — 레코드와 FID 매핑표에서 `create_arrangement_groups` 인자 배치로 (순수 함수, 콘솔 읽기는 주입 포트)
- `server/orchestrator/tools.py` — 툴 1종 `import_lxseq_groups` 등재, SHEET_KIND_ACTIONS 항목, 래퍼 스키마 동조
- `server/sheets/registry.py` — GROUP_ROW 1개 추가
- `server/web/session.py` — 행 계수기 항목 1개 추가
- `server/tests/fixtures/lxseq/LXSEQ_RIG_01_ShowBase_r3.group.csv` — 정본 사본 (plan-phase 커밋에 포함)
- 테스트 3종과 onPC 실기 1회

### C.2 Out of Scope

- **그룹 멤버십 판독 프로브.** 그룹이 있는 쇼파일이 있어야 한다(카드 t22). 본 SPEC은 판독을 시도하지 않고 미검증 고지를 싣는다.
- **`create_arrangement_groups` 핸들러 본문 변경.** 001의 「신규 툴 밖 0-diff」를 계승한다. max_plan_size 인자 신설도 하지 않는다(배치 분할로 푼다).
- **`server/groupgen/write.py` 변경.** 엔진은 이미 필요한 것을 전부 한다.
- **프리셋, FX, 시퀀스.** 3단계와 4단계 후속 SPEC.
- **UI 파일 선택기 배선.** 카드 t10 소유. 본 SPEC은 툴 인자 계약까지만 책임진다.
- **소비자 표 2와 3의 A 레지스트리 이관.** 카드 t53 소유. 본 SPEC은 group 행을 **현재 모양 그대로** 등재하고 모양을 바꾸지 않는다.

### C.3 제외 근거 하나

`create_arrangement_groups` 에 max_plan_size 를 노출하는 편이 배치 분할보다 짧아 보인다. 채택하지 않는 이유는 그 인자가 슬롯 경제 가드의 상한을 **호출자가 넓히는 문**이고, 한 번 열면 다음 호출자는 이유 없이 넓히기 때문이다. 배치 분할은 가드를 그대로 두고 같은 결과를 낸다.

---

## D. 요구 (GEARS)

### D.1 파싱 (M1)

- **REQ-LXSEQ2-001** [Ubiquitous] — 파서는 **shall** BOM을 흡수하고, 헤더를 **이름으로** 매칭하며(위치 매칭 금지), 4열 GroupNo, Name, Members, Purpose 가 전부 있어야 한다. 하나라도 없으면 **shall** 파일 단위로 실패한다.
- **REQ-LXSEQ2-002** [Event] — **When** 한 행이 검증에 실패하면, 파서는 **shall** 예외를 던지지 않고 닫힌 어휘 5종 중 하나로 거부 부류를 붙여 낸다: `groupno_not_int`, `groupno_out_of_range`, `groupno_duplicate`, `name_empty`, `name_has_quote`.
- **REQ-LXSEQ2-003** [Unwanted] — 파서는 **shall not** Members 열을 멤버십 판정에 쓴다. 원문 그대로 보존만 한다.

### D.2 매핑 (M2)

- **REQ-LXSEQ2-004** [Ubiquitous] — 기본 12종의 멤버 FID는 **shall** 001 FID 매핑표(패치 레코드의 Group 라벨에서 FID 목록으로)에서 온다.
- **REQ-LXSEQ2-005** [Ubiquitous] — 파생 6종(ALL, SIDE-ALL, WASH-ALL, MOVER-ALL, ODD, EVEN)의 멤버 FID는 **shall** 코드의 **닫힌 규칙**에서 온다. 규칙 표는 `group_mapper.py` 가 소유하며 데이터에서 유추하지 않는다.
- **REQ-LXSEQ2-006** [Event] — **When** 한 행의 Name 이 패치 라벨도 파생 6종도 아니면, 매퍼는 **shall** `unknown_group_name` 으로 건너뛰고 목록에 적는다. 추측하지 않는다.
- **REQ-LXSEQ2-007** [State] — **While** Members 가 라벨 뒤에 개수를 적은 행을 다루는 동안, 매퍼는 **shall** 그 개수를 실제 FID 수와 대조하고 다르면 `member_count_mismatch` 로 건너뛴다. 이 대조는 **교차검증**이며 멤버십의 근거가 아니다.
- **REQ-LXSEQ2-008** [Unwanted] — 매퍼는 **shall not** 콘솔 실측에 없는 FID를 그룹에 넣는다. FID 실측이 전수가 아니면(`console_read_incomplete`) **shall** 0배치를 낸다.
- **REQ-LXSEQ2-009** [State] — **While** 측정된 빈 슬롯 순열이 시트의 GroupNo 순열과 다른 동안, 매퍼는 **shall** 계획을 내지 않고 `slot_number_divergence` 대조표를 보고한다.
- **REQ-LXSEQ2-010** [Ubiquitous] — 계획은 **shall** **GroupNo 오름차순**으로 정렬된 뒤 DEFAULT_GROUP_PLAN_CAP(16) 이하 배치로 나뉜다. 이 시트에서는 **16과 2**다. 순서가 GroupNo 여야 하는 이유는 `build_group_write_plan` 이 `measure_empty_slots` 가 낸 빈 슬롯을 **준 순서대로** 짝짓기 때문이다 — 다른 순서로 넘기면 18개 전부 번호가 밀리고, 곡 파일이 그룹 번호를 참조하므로 그것은 쇼의 의미를 조용히 깨는 변경이다. REQ-LXSEQ2-009(슬롯을 시트대로)와 양립하는 순서는 GroupNo 하나뿐이다.
- **REQ-LXSEQ2-011** [Unwanted] — 매퍼와 툴은 **shall not** 조립된 명령 **한 줄**의 인코딩 바이트 길이가 선언된 예산을 넘는 상태로 발화한다. 단위가 줄인 이유는 `run_commands` 가 한 줄씩 발화하기 때문이다. 넘으면 `line_over_budget` 으로 그 그룹을 건너뛰고 목록에 최장 줄의 바이트 수를 적는다.

### D.3 툴과 배선 (M3)

- **REQ-LXSEQ2-012** [Ubiquitous] — 툴은 **shall** 1종 `import_lxseq_groups` 이며 action 으로 preview 또는 apply 를 받는다. 기본은 preview 다.
- **REQ-LXSEQ2-013** [Ubiquitous] — 쓰기는 **shall** `create_arrangement_groups` 내부 ToolCall 위임뿐이다. `server/lxseq/` 에 쓰기 수단(모듈, 식별자, 명령 문자열) 0건이며 AST 스캔으로 단언한다.
- **REQ-LXSEQ2-014** [Ubiquitous] — 시트 종류 레지스트리는 **shall** group 행을 갖고, 동반 4지점(SHEET_KIND_ACTIONS, 행 계수기, 래퍼 스키마 passthrough 인자, 래퍼 action enum)이 전부 채워진다.
- **REQ-LXSEQ2-015** [Unwanted] — 바이트는 **shall not** 채팅 본문 텍스트에서 만들어진다(001 REQ-LXSEQ-016 계승). 파일에서 읽은 바이트만이며, 툴 설명문과 guidance 에 명시하고 페이로드에 `source.sha256` 과 `byte_length` 를 싣는다.
- **REQ-LXSEQ2-016** [Ubiquitous] — 미검증 고지 문면은 **shall** 멤버십을 **미측정**으로 적는다. 「원리적 불가」나 「읽을 수 없다」류 단정은 **shall not** 어느 산출물에도 나타난다.

---

## E. 가정 (ASSUMPTION)

| 번호 | 가정 | 부정 시 |
|---|---|---|
| **ASSUMPTION-80** | onPC의 그룹 풀이 비어 있다(실측 2026-08-22와 08-24, `DataPool/Groups` childCount 0). 그래서 측정된 빈 슬롯이 1부터 18까지로 나와 시트의 GroupNo 와 일치한다 | REQ-LXSEQ2-009가 발동해 0배치와 대조표. 코드 변경 없음 |
| **ASSUMPTION-81** | ~~조립된 그룹 번들이 전송 상한 안에 들어간다. 미측정~~ → **M2 에서 측정해 참으로 판정**(A.2 셋째). 이 리그의 최장 줄은 exec 로 감싸 1243 bytes, 상한 2048. 단위는 번들이 아니라 **줄**이다 | 판정 완료. 더 큰 리그에서는 다시 참이 아닐 수 있고, 전송층이 exec 을 검사하지 않으므로 REQ-LXSEQ2-011 이 유일한 방어선이다 |
| **ASSUMPTION-82** | 001의 name_prefix_mode 가 group 이었던 결과로 콘솔 픽스처 이름이 「그룹 라벨에 FID」 꼴이다. 사람이 `human_check_commands` 로 눈으로 대조할 때의 유일한 단서다 | 대조가 어려워질 뿐 계획은 성립한다. 코드 변경 없음 |

---

## F. 성공 판정

`acceptance.md` 가 소유한다. 요약하면 오프라인 15건에 onPC 실기 1건, 합 **16건**이다.

---

## G. 위험

| 위험 | 성질 | 완화 |
|---|---|---|
| 잘못된 멤버십이 조용히 영속 | **탐지 불가**. 되읽기 없음, Delete 블랙리스트, restore 부재 | 멤버십을 데이터에서 유추하지 않고 닫힌 규칙과 실측 FID로만 만든다(REQ-004, 005, 008). 개수 교차검증(REQ-007). 미검증 고지 상속 |
| 명령 줄이 상한을 넘어 조용히 누락 | **탐지 불가**. 전송층이 exec 을 검사하지 않는다(실측) | 발화 전 줄 단위 바이트 게이트(REQ-011) — 이 경로의 유일한 방어선 |
| 슬롯 번호가 어긋나 곡 파일 참조가 깨짐 | 조용함 | 어긋나면 0배치와 대조표(REQ-009) |
| 점유 슬롯 덮어쓰기 | 조작자가 OK를 누르면 성립, 복구 불가 | 기존 `select_group_slot` 정적 차단을 그대로 탄다. 002는 우회로를 만들지 않는다 |
| 시트 종류를 늘리며 동반 지점을 빠뜨림 | 조용함 | t51의 함께 자라는 검사가 기계적으로 4지점을 요구한다(REQ-014) |

### G.1 본 SPEC이 다루지 않는 위험

- 그룹이 있는 쇼파일에서 멤버십이 실제로 읽히는가. 카드 t22와 t46 소유.
- 픽스처 열거 절단(86에서 19로)의 해소. 카드 t46 소유. 002는 멤버십을 **콘솔 열거가 아니라 CSV**에서 만들어 이 절단을 우회한다.
