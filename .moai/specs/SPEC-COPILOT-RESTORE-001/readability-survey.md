# 복원 가능성 조사 — 콘솔 판독 실측 전수표 (t5a)

> **이 문서는 설계가 아니라 조사다.** 복원 경로를 설계하려면 「이전 상태를 읽을 수
> 있는가」가 먼저인데, 그 실측이 22개 SPEC · 434곳에 흩어져 있었다. 여기 모은다.
>
> **실기 확인 0건** — 기존 실측 기록의 **재집계**이며 이 문서가 콘솔을 새로 재지
> 않았다. **콘솔 쓰기 0건.** 각 행의 근거는 파일:줄로 달았다.

## 1. 판정축이 「오브젝트 종류」가 아니라 **「계층 × 채널」** 이다

조사 전 통념은 *"그룹 멤버십은 읽을 수 없다"* 였다. 그 문장은 **참이지만 범위가 좁다.**
같은 `DataPool/Groups` 가 계층에 따라 다르게 답한다:

| 대상 | 채널 | 관측 | 근거 |
|---|---|---|---|
| `DataPool/Groups` (풀) | `state` childCount | **5 → 6 변화 관측** | GROUPGEN progress.md:267 |
| `DataPool/Groups` (풀) | `state` childCount | 6 유지(덮어쓰기 취소 후) | GROUPGEN progress.md:287 |
| `DataPool/Groups/13` (개별) | `state` childCount | **0** — 실사용 그룹인데도 | GROUPGEN research.md:45 |
| `DataPool/Groups/1` (개별) | `state` childCount | 0 | GROUPGEN research.md:46 |
| `DataPool/Groups/11` (개별) | `state` childCount | 0 | GROUPGEN research.md:47 |
| `DataPool/Groups/14` (개별) | **`prop` Name** | **`"GroupgenProbe"` 판독됨** | GROUPGEN acceptance.md:85 |

**세 가지가 갈린다:**

1. **풀 계층은 계수가 읽힌다** — 슬롯이 늘고 주는 것을 관측할 수 있다.
2. **개별 오브젝트의 자식(멤버십)은 안 읽힌다** — `childCount 0` 은 "비었다"가 아니라
   "이 채널로는 안 보인다"(GROUPGEN progress.md:44).
3. **개별 오브젝트의 속성은 읽힌다** — `prop … Name` 이 답한다.

## 2. 트리별 관측값 (기계 집계, 22개 SPEC · 434 기록)

| 트리 | 기록 | 관측된 childCount |
|---|---:|---|
| `Patch/Stages/…/Fixtures` | 18 | 0 · 3 · 19 · 39 · 86 |
| `DataPool/Sequences` | 15 | 0 · 1 · 6 · 17 · 19 · 24 |
| `DataPool/Groups` (풀) | 7 | 0 · 4 · 5 · 6 |
| `DataPool/Sequences/Sequence N` | 7 | 1 · 3 · 5 · 6 · 17 · 24 |
| `Patch/FixtureTypes` | 6 | 1 · 3 · 15 · 29 |
| **`Executor` / `Sequence` 노드** | 6 | **0 만** (4/4 샘플) |
| `DataPool/Pages` | 6 | 0 · 1 |
| `Patch/DMXUniverses` | 4 | 1024 |

**`Executor` 노드만 관측값이 0 한 종류다.** 다른 트리는 전부 0 이 아닌 값을 낸 적이 있다.

## 3. 🔴 「원리적 불가」와 「응답기 미구현」이 갈린다

이 구분이 복원 설계의 답을 바꾼다. 기존 기록이 사유를 다르게 적고 있다:

- **Executor 자식** — *"응답기가 범용 `handle:Children()` 만 호출"*. 이것은 **오브젝트의
  성질이 아니라 지금 응답기 구현의 한계**로 읽힌다.
- **Group 멤버십** — 후보 4종 전부 `ok:false`, `childCount 0`(BLOCKED16 probe.md,
  「정답 기지 표본 Group 14」에서도). 여러 채널을 시도해 전부 실패한 기록이라
  **원리적 불가에 가깝다.**

**둘을 같은 「판독 불가」로 묶으면 안 된다.** 전자는 응답기를 고치면 열릴 수 있고 후자는
안 열린다. 이 문서는 그 구분을 **표시만 하고 확정하지 않는다** — 확정하려면 응답기
소스와 MA3 API 를 대조해야 하고, 그건 이 조사의 범위 밖이다.

## 4. 복원 대상 분류 (잠정 — 3절이 확정되면 바뀔 수 있다)

| 대상 | 이전 상태를 읽을 수 있나 | 복원 가능성 |
|---|---|---|
| 그룹 **존재/개수** | 예 (풀 계수) | **가능** — 생성 전 계수를 기록하면 새 슬롯을 안다 |
| 그룹 **이름** | 예 (`prop Name`) | **가능** — 덮어쓰기 전 이름 백업 |
| 그룹 **멤버십** | **아니오** | **불가** — 되돌릴 대상을 모른다 |
| 시퀀스 존재/개수 | 예 | 가능 |
| 시퀀스 **큐 내용** | 부분(트리별로 갈림) | **미확정** |
| 프리셋 **내용** | **아니오** (`childCount 0`) | 불가 |
| 픽스처 패치 | 예 (86 등 실계수) | **가능** — LXSEQ·PRECHK 가 이미 재조회 대조를 한다 |
| Executor 배정 | **아니오** (0 만) | 미확정 — 3절 구분에 달림 |

**「복원 불가가 대부분」은 절반만 맞다.** 멤버십·프리셋 내용은 불가가 맞지만,
**존재·이름·계수·패치는 읽히므로 복원 경로가 있다.**

## 5. 이 조사가 답하지 않은 것

- **3절의 구분을 확정하지 않았다** — Executor 판독 실패가 응답기 한계인지 원리인지.
- **읽기 프로브를 돌리지 않았다.** 이 표는 전부 **기존 기록의 재집계**이고, 값이 지금도
  참인지는 재측정해야 한다. 그 프로브 목록은 이 표가 있어야 정해진다.
- **설계는 하지 않았다.** 대체 수단(덮어쓰기 전 경고 · 인계 패키지)은 다음 카드다.

---

# 부록 A — 응답기 소스 판독 (t5b · (ㄴ) 확정 시도)

> **1차 입력을 SPEC 기록이 아니라 `console/lua/copilot_responder.lua` 로 바꿔 다시 쟀다.**
> 리드 지적대로 **답이 저장소에 이미 있었는데 본문의 조사 입력에 없었다.** 본문 표의
> 판정 **세 개가 뒤집힌다.**
>
> 실기 확인 0건 · 콘솔 쓰기 0건 — 소스 판독이다.

## A.1 뒤집힘 ① — Executor 는 「미확정」이 아니라 **「다른 경로로 읽힘, 이미 구현됨」**

```
copilot_responder.lua:699-706
  Executor-only branch (REQ-EXECBODY-003, additive — AC-EXECBODY-004):
  expose the assigned sequence's pool number so a safety-gate caller can
  delegate body lookup to the already-trusted sequence path instead of
  Children() (which an executor never populates).
```

- `Children()` 을 executor 가 **절대 안 채운다** — 응답기 한계가 아니라 **MA3 오브젝트 모델**
- 응답기가 **이미 우회한다** — 할당 시퀀스의 풀 번호로 본문 조회를 위임
- `SPEC-COPILOT-EXECBODY-001` 이 그 작업이다

**본문 §3 에서 Executor 를 「응답기 미구현」 쪽에 놓은 것은 틀렸다.** 「never populates」라
적혀 있으니 원리 쪽이고, 그런데 **우회가 이미 있으므로 복원 관점에서는 읽히는 대상**이다.

## A.2 뒤집힘 ② — 멤버십 「원리적 불가」 판정의 **전제가 만료됐다**

`BLOCKED16-001/disposition.md:23` (D-6, 2026-08-18 리드 결정):

> GROUPGEN 게이트 A 의 반증은 유효하다 … **그러나 그 반증은 본 브랜치의 응답기 표면에
> 한정된다.** 미관측 73필드라는 수 자체가 `introspect` 가 프로퍼티명을 열거해 나온
> 값이고, **`introspect` 는 본 브랜치에 없다.** … **측정 조건: INTROSPECT-001 머지 +
> `introspect` offset 인자.**

**그 측정 조건이 지금 충족돼 있다:**

```
grep -c 'introspect' console/lua/copilot_responder.lua   → 19   (D-6 판정 시점: 0)
copilot_responder.lua:66-67
  1.6.1: additive props + introspect read-only discovery verbs
  (SPEC-COPILOT-INTROSPECT-001, PR #23 reland 2026-08-18)
```

즉 「멤버십은 원리적으로 못 읽는다」는 **`introspect` 없는 표면에서 내린 판정**이고,
그 표면은 더 이상 현재 상태가 아니다. **본문 §3 의 「원리적 불가에 가깝다」를 철회한다** —
지금은 **미측정**이다. 원리적 불가일 수도 있으나 **이 브랜치에서 다시 재기 전에는 모른다.**

## A.3 뒤집힘 ③ — 판독 경로가 하나가 아니라 **셋**이다

`M.safe_children` (`:461-489`; `Children()` `:462` · `Count()` `:475` · `Ptr(i)` `:479`) 이 순서대로 시도한다:

| # | 경로 | 성질 |
|---|---|---|
| 1 | `handle:Children()` | 목록. **간극을 압축한다**(`:324` COMPACTS gaps away) — 위치 ≠ 슬롯 |
| 2 | `handle:Count()` + `handle:Ptr(i)` | **주소 지정**. 슬롯 i 를 물어 객체를 받으므로 i 가 그 객체의 슬롯 |
| 3 | (실패) | 빈 배열 |

본문 표는 `childCount` **한 채널만** 집계했다. `childCount 0` 은 경로 1의 실패이지
**경로 2의 실패가 아니다.** 두 경로를 갈라 재지 않았다.

`:317-320` 이 이 계약을 못 박는다:

> a child's slot is reported ONLY when it was positively established; an
> unestablished slot is reported as **nothing**, never as the child's position

**그래서 `0` 은 「없음」이 아니라 「확립하지 못함」의 표현일 수 있다** — 본문이 인용한
GROUPGEN 의 *"이 채널로는 안 보인다"* 와 같은 말이고, 소스가 그것을 **설계 의도로** 적고 있다.

## A.4 이 소스 판독의 천장 — 넘지 않은 선

리드가 정해 준 경계 그대로다.

**소스로 알 수 있었던 것** — 응답기가 무엇을 부르는가(`Children` / `Count`+`Ptr` /
`Property*`) · 왜 그 경로인가 · 우회가 있는가(있다).

**소스로 알 수 없는 것 — 확정하지 않았다** — MA3 API 가 멤버십을 주는 더 나은 accessor 를
제공하는가. 「응답기가 X 를 안 부른다」와 「MA3 에 X 가 없다」는 다른 문장이고 소스는
앞엣것만 답한다. `:342-344` 가 스스로 그렇게 적는다:

> Which (if any) exists on 2.4.2 is **unverified** — PROTOCOL.md §6 ASSUMPTION-7

## A.5 갱신된 판정 (본문 §4 를 대체한다)

| 대상 | 판정 | 근거 |
|---|---|---|
| 그룹 존재/개수 | **읽힘** | 풀 계수 변화 관측 (본문 §1) |
| 그룹 이름 | **읽힘** | `prop Name` (본문 §1) |
| 그룹 **멤버십** | **미측정** ← 「원리적 불가」에서 하향 | A.2 — 판정 전제가 만료 |
| 프리셋 내용 | 미측정 | 같은 사유일 가능성 — 재측정 대상 |
| 픽스처 패치 | 읽힘 | 실계수 86 등 |
| Executor 배정 | **읽힘(우회)** ← 「미확정」에서 상향 | A.1 — 이미 구현됨 |

**「복원 불가」로 확정된 항목이 하나도 남지 않았다.** 전부 읽히거나 **미측정**이다.
이것이 이 부록의 결론이며, 본문이 「불가」라 적은 두 항목의 근거가 각각 만료·미분리였다.

## A.6 다음 — 읽기 프로브 목록 (쓰기 0건)

A.2·A.3 이 프로브 목록을 정한다. 전부 **읽기 전용**이다:

1. `introspect` 로 `DataPool/Groups/13` 의 프로퍼티명을 열거 — 멤버십 접근자가 있는가
2. 같은 그룹에 `Count()` + `Ptr(i)` 경로 — `childCount 0` 과 다르게 답하는가
3. 프리셋 풀에 1·2 반복 — 같은 기전인가
4. Executor 우회 경로 재확인 — 할당 시퀀스 번호가 실제로 나오는가

**쓰기가 필요한 항목은 없다.** 넷 다 판독뿐이다.

---

# 부록 B — 프로브 ① 선행 확인: `introspect` 에 offset 페이징이 **없다** (t5c)

> 리드 지시: *"D-6 이 「introspect offset 인자」를 조건으로 적었으니 offset 페이징이
> 있는지 먼저 소스에서 확인하십시오. 없으면 ①은 지금 못 합니다."*
>
> **없습니다. ①은 지금 못 합니다.** 소스 판독 · 실기 0건 · 콘솔 쓰기 0건.

## B.1 offset 은 있는데 `state` 전용이다

`offset` 자체는 응답기 1.6.0 에 실려 있다:

    :226-231  Paged snapshot requests (responder 1.6.0, PROTOCOL.md §4.2):
              the **state** rest-of-line may end in one whitespace-separated
              "offset=<n>" token
    :233      function M.parse_state_args(rest)
    :661-662  Paging window (1.6.0): `offset` is the 0-based start; the window
              is at most CONFIG.max_children wide

**그러나 그 파서는 한 곳에서만 불린다:**

    grep -n 'parse_state_args' → :233 (정의) · :1136 (호출, state 분기)

## B.2 `introspect` 는 offset 을 받지 않는다

    :863   function M.build_introspect_result(id, path)      ← offset 인자 없음
    :1173-1184  elseif parsed.kind == "introspect" then
                  … payload = M.build_introspect_result(parsed.id, parsed.rest)

`parsed.rest` 를 **경로로 통째로** 넘긴다. 사용자가 `offset=` 을 붙이면 그것은 경로의
일부로 해석된다 — 페이징이 아니라 **경로 오류**가 된다.

## B.3 절단이 꼬리를 버린다 — 그래서 뒤쪽 필드는 도달 불가다

    :903-908  while #M.encode_payload(payload) > CONFIG.max_payload and #fields > 0 do
                  table.remove(fields)      ← 배열 끝에서 제거
                  payload.truncated = true

`table.remove(fields)` 는 **마지막 원소**를 지운다. 즉 페이로드가 예산을 넘으면 **뒤쪽
필드부터 사라지고**, 페이징이 없으니 **어떤 호출로도 그 뒤쪽에 도달할 수 없다.**

이것이 D-6 의 「73개 미관측」이 지금도 유효한 이유다 — 응답기가 필드를 **가지고 있어도**
전송 예산 밖이면 호출자에게 도달하지 않고, 그 창을 옮길 수단이 없다.

## B.4 ⚠️ 「N개가 돌아온다」로 못박지 않는다

리드 경고 그대로다. 절단은 개수가 아니라 **페이로드 예산**이다(t12 실측: Root 22→18/1200B ·
Fixtures 86→19/1158B · DataPool 16→16/1013B, 경계 `[1200, 1208)`). 위 B.3 의 while 루프가
그 기전이다 — **인코딩된 바이트 길이**를 보고 자른다. 필드 개수 기준이 아니다.

**그러므로 ①의 검사는 「N개가 보인다」가 아니라 「멤버 열거 필드가 절단 전 구간에
있는가」여야 한다.** 그리고 그것은 페이징 없이는 **운이다.**

## B.5 판정과 다음

**①은 지금 못 한다.** 두 갈래 중 하나가 선행해야 한다:

- **(a) `introspect` 에 offset 을 붙인다** — `parse_state_args` 를 재사용하면 되고
  `build_introspect_result` 에 인자 하나가 는다. 응답기 변경이므로 **별도 카드**다.
- **(b) 대조 필드명을 좁혀 요청한다** — 지금 응답기가 그 형태를 지원하는지 미확인.

**②는 영향받지 않는다.** `Count()` + `Ptr(i)` 경로는 `introspect` 와 무관하고, 리드가
「②부터」로 순서를 정한 것이 이 확인으로 더 옳아졌다 — **①이 막힌 지금 ②가 유일하게
바로 잴 수 있는 프로브다.**

## B.6 이 확인이 답하지 않은 것

- **멤버 열거 필드가 실재하는지는 여전히 모른다.** B.3 은 「보이지 않는 이유」를 설명할
  뿐 「없다」를 뜻하지 않는다. D-6 의 *"그 안에 멤버 열거 필드가 있을 가능성은
  배제되지 않았다"* 가 그대로 유효하다.
- **(b) 가 가능한지 재지 않았다** — 필드명 지정 조회의 지원 여부는 미확인이다.
