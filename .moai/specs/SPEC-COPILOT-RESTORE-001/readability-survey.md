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

---

# 부록 C — (b) 는 성립한다 · 응답기를 안 고쳐도 꼬리에 닿는다 (t46 1단계)

> 리드 지시: *"(b) 부터. 되면 응답기를 안 고칩니다."* — **됩니다.**
> 소스 판독 · 실기 0건 · 콘솔 쓰기 0건 · **응답기 변경 0줄.**

## C.1 두 동사가 **다른 접근자**를 쓴다

| 동사 | 이름을 얻는 방법 | 절단에 걸리나 |
|---|---|---|
| `introspect` | `handle:PropertyName(i)` — **인덱스 열거** (`:832`) | **예** — 꼬리부터 버림(`:903-904`) |
| `props` | `handle:Get(name)` → `handle[name]` — **이름 직접** (`:284-291`) | 요청한 이름만 담으므로 **열거 절단과 무관** |

`build_props_result` (`:761-808`) 는 **호출자가 준 이름 목록만** 돈다:

    for _, name in ipairs(names) do
        local value, perr, value_type = M.safe_property(handle, name)

**즉 이름을 알면 그 필드에 닿는다.** `introspect` 가 그 이름을 못 보여 줘도 상관없다 —
`props` 는 열거를 거치지 않는다.

## C.2 🔴 절단은 **전송 직전**에만 일어난다 — 열거는 콘솔 안에서 전량 끝난다

    :831   for i = 0, count - 1 do            ← 전량 열거. 절단 없음
    :837       fields[#fields + 1] = { n = name, t = tostring(value_type) }
    :903   while #M.encode_payload(payload) > CONFIG.max_payload and #fields > 0 do
    :904       table.remove(fields)            ← **전송 직전**에만 버린다

**응답기는 101개 이름을 전부 알고 있다.** 못 보낼 뿐이다. 예산은 `max_payload = 1900`
(`:41`, MA3 CLI 2048 제한 때문)이다.

그러므로 D-6 의 「73개」는 **응답기가 모르는 필드가 아니라 전송하지 못한 필드**다.
이것이 (a) 를 **순수 전송 문제**로 만든다 — 판독 능력의 문제가 아니다.

## C.3 순환은 남지만 **완전한 순환은 아니다**

`props` 는 이름을 알아야 부른다. 그 이름을 주는 것이 `introspect` 인데 절단된다 —
순환처럼 보인다. **그런데 세 가지가 순환을 깬다:**

1. **절단 전 구간의 이름은 이미 온다** — 28개 안팎(t12 실측 경계 `[1200, 1208)`).
   그 목록으로 **명명 규칙**을 읽을 수 있다.
2. **대조 이름 집합이 하드코딩돼 있다** — `:44` `introspect_contrast_names =
   { "INDEX", "NAME", "NO", "FADER", "CURRENTCUE" }`. 열거 없이 이름을 아는 선례다.
3. **후보 이름을 지어 쏘면 된다.** `props` 는 못 읽는 이름에 `ok:false` 를 준다
   (`:781-782`) — **부재와 존재가 갈린다.** 즉 `props` 로 **이름 추측을 검증**할 수 있다.

**3번이 (b) 의 실질이다.** 멤버 열거 필드의 후보 이름(예: `MEMBERS` · `FIXTURES` ·
`OBJECTS` · `CONTENT` 류)을 `props` 로 쏘면, **있으면 값이 오고 없으면 `ok:false`** 가
온다. 열거를 거치지 않으므로 절단과 무관하다.

## C.4 판정 — **(a) 는 지금 필요하지 않다**

리드 지시가 *"(b) 되면 응답기를 안 고친다"* 였다. **(b) 가 성립하므로 응답기 변경(a)
을 이 카드에서 하지 않는다.** 콘솔에 배포되는 코드를 고치지 않고 같은 물음에 답할 수
있으면 그 길이 먼저다.

**다만 (a) 가 무의미해진 것은 아니다** — 이름을 **모를 때** 열거가 필요하고, 추측이
빗나가면 (a) 가 유일한 길이다. 그때는 별도 카드다. C.2 가 그 카드의 근거를 강화한다:
응답기는 이미 이름을 갖고 있으므로 (a) 는 **전송 창을 옮기는 일**이지 새 판독 능력을
만드는 일이 아니다.

## C.5 이 확인이 답하지 않은 것

- **후보 이름이 맞는지는 모른다.** C.3-3 은 **검증 수단**을 확보한 것이지 답을 얻은
  것이 아니다. 어떤 이름이 실재하는지는 **실기 프로브**로만 안다.
- **`Get(name)` 이 멤버 목록을 값으로 주는지 모른다.** 이름이 있어도 값이
  `"table: 0x..."` 같은 핸들 문자열이면 멤버를 못 읽는다 — `:286` 이
  `tostring(value)` 를 쓴다. **이것이 (b) 의 가장 큰 미지수다.**
- 실기 0건. 위 전부 소스 판독이다.

## C.6 갱신된 프로브 목록 (쓰기 0건)

②가 여전히 먼저다(onPC 대기). ①은 **(b) 형태로 바뀐다**:

    ①' props 로 후보 이름을 쏜다 — MEMBERS · FIXTURES · OBJECTS · CONTENT · ITEMS …
        기대: 있으면 값 · 없으면 ok:false. **부재와 존재가 갈린다.**
        ⚠️ 값이 핸들 문자열로 오면 C.5 의 미지수가 확정된다 — 그것도 결과다.
    ②  Count() + Ptr(i)  — 변경 없음
    ③  프리셋 풀에 ①'·② 반복
    ④  Executor 우회 재확인 — 변경 없음

**넷 다 읽기 전용이고 쓰기 0건이다.**

---

# 부록 D — 실기 프로브 실측 (t46 라운드 1) — **두 채널이 갈린다**

> **콘솔 쓰기 0건.** 읽기 동사(`ping` · `state` · `prop` · `introspect`)만 사용.
> `--skip-exec` 로 명령 실행 경로를 제거했다.

## D.1 측정 조건 (재현용)

    콘솔        grandMA3 onPC 2.4.2 · pid 99116 (app_gma3)
    포트        송신 127.0.0.1:8000 · 수신 9005 (둘 다 app_gma3 점유)
    응답기      CopilotResponder v1.6.1 (ping 실측)
    도구        server.tools.responder_roundtrip --skip-exec
                server.tools.introspect_probe
    쇼파일      픽스처 86 (state 절단 19) · 시퀀스 1 · **그룹 0** · 프리셋 풀 14
    일시        2026-08-24

## D.2 ② 는 **대상이 없어 못 돌렸다**

    state DataPool/Groups → childCount 0 · children 0

리드 착수 조건 #2 그대로다 — *"비어 있으면 잴 대상이 없다. 없는 그룹에 `Ptr(i)` 를
물어 나온 실패는 판정이 아니다."*

**그런데 「비었다」와 「안 보인다」를 갈랐다:**

    DataPool/Sequences        childCount 1    ← 판독 채널은 살아 있다
    Patch/Stages/1/Fixtures   childCount 86   ← 리그는 있다
    DataPool/PresetPools      childCount 14
    DataPool/Groups           childCount 0    ← 이 쇼파일에 그룹이 **실제로 없다**

같은 채널이 다른 풀에 대해 0 이 아닌 값을 준다. 그러므로 이 0 은 **판독 실패가 아니라
쇼파일 상태**다. **②는 그룹이 있는 쇼파일에서 다시 재야 한다.**

## D.3 🔴 그런데 다른 자리에서 두 채널이 **갈렸다**

같은 오브젝트를 `state`(childCount)와 `prop COUNT` 로 각각 물었다:

| 오브젝트 | `state` childCount | `prop COUNT` | 일치? |
|---|---:|---:|---|
| `DataPool/Sequences/1` (`Default`) | **2** | **2** | 일치 |
| `DataPool/PresetPools/1` (`Dimmer`) | **0** | **1000** | **불일치** |
| `DataPool/PresetPools/2` (`Position`) | **0** | **1000** | **불일치** |
| `DataPool/PresetPools/3` (`Gobo`) | **0** | **0** | 일치 |
| `DataPool/PresetPools/4` (`Color`) | **0** | **1000** | **불일치** |

**`childCount 0` 이 「비었다」를 뜻하지 않는 실례를 이 세션에서 직접 관측했다.**
같은 오브젝트가 다른 채널로 1000 을 답한다.

⚠️ **`COUNT` 가 무엇을 세는지는 확정하지 않는다.** 1000 이라는 값과 `Gobo` 만 0 인
것을 보면 **저장된 프리셋 수가 아니라 풀 용량/할당**일 가능성이 크다. 이 프로브가
말할 수 있는 것은 **「두 채널이 다르게 답한다」**뿐이고, `COUNT` 의 의미는 미확정이다.

## D.4 `props` 경로가 산다 — 대조군 양쪽 성립

    ZZFAKE_NO_SUCH_FIELD  → ok=False "property not readable"   ← 날조 대조군
    Name                  → ok=True  value='Default'           ← 양성 대조군

**부재와 존재가 갈린다.** 부록 C 의 (b) 판정이 실기로 확인됐다 — `props` 는 이름만
알면 답하고, 없는 이름은 명확히 거부한다.

## D.5 후보 이름 — 무작정 지은 다섯은 전부 부재

    MEMBERS · FIXTURES · OBJECTS · CONTENT · ITEMS   → 전부 ok=False

리드 경고대로였다 — *"무작정 지으면 `ok:false` 만 쌓인다."* 그래서 **명명 규칙을
먼저 읽었다**(`introspect`, 28/65 수신, truncated):

    IGNORENETWORK STRUCTURELOCKED SYSTEMLOCKED LOCK INDEX COUNT NO NAME
    USEREXPANDED FADERENABLED OWNED HIDDEN DEPENDENCYEXPORT MEMORYFOOTPRINT
    GUID SCRIBBLE APPEARANCE NOTE TAGS PREVIEWCOPY CURRENTCUE LOADEDCUE TYPE
    CUENO CUENAME TRIGGER USER AUTOSTART

전부 **대문자 단일어/복합어**이고 복수형 컬렉션 이름이 없다. 그 목록에서 `COUNT` 를
골라 쏜 것이 D.3 의 발견이다.

## D.6 이 라운드가 답하지 않은 것

- **②는 미실행이다** — 그룹이 없는 쇼파일이었다. **재측정 필요.**
- **④ Executor 도 미실행** — `DataPool/Pages/1` `childCount 0`, 페이지가 비어 있다.
- **`COUNT` 의 의미 미확정** — D.3 ⚠️.
- **멤버 열거 필드는 여전히 미발견.** 절단된 37개 안에 있을 가능성은 **배제되지
  않았다**(D-6 문면 그대로). 이 라운드는 그것을 좁히지 못했다.
- **`Get(name)` 이 목록을 값으로 주는지도 미확정** — 부록 C.5 의 미지수가 그대로다.
  `COUNT` 는 스칼라라 그 물음에 답하지 않는다.

## D.7 다음 라운드에 필요한 것

    (1) **그룹이 있는 쇼파일** — ②를 돌리려면 필수다. 없으면 영원히 못 잰다
    (2) 익스큐터가 배정된 페이지 — ④ 용
    (3) 그룹 오브젝트에 introspect — 시퀀스와 이름 목록이 다를 수 있다

**(1) 이 감독께 부탁드릴 것이다** — 그룹 몇 개가 있는 쇼파일을 열어 주시면 ②가 바로 된다.

## D.8 추가 실측 — `COUNT` 는 **용량**이다 (D.3 ⚠️ 확정)

    state DataPool/Groups            → childCount 0    (이 쇼파일에 그룹 0개)
    prop  DataPool/Groups COUNT      → 1000

**그룹이 하나도 없는 풀도 `COUNT 1000` 을 답한다.** 그러므로 `COUNT` 는 **저장된
개수가 아니라 풀 용량/슬롯 수**다. D.3 의 「미확정」을 여기서 닫는다.

**그래서 D.3 의 「두 채널이 갈린다」의 해석이 바뀐다:**

- 갈린 것은 맞지만 **모순이 아니다** — 두 채널이 **다른 것**을 세고 있었다.
  `state` 는 **실재 자식**, `COUNT` 는 **용량**.
- 그러므로 `childCount 0` 은 이 쇼파일에서 **실제로 「비었다」가 맞다.**
- **`COUNT` 는 멤버십 판독에 쓸 수 없다.** 내용을 안 센다.

**자기 발견을 스스로 내린다**: D.3 을 「childCount 0 이 비었다를 뜻하지 않는 실례」로
읽으면 안 된다. 그 해석은 `COUNT` 를 내용 계수로 가정한 것이고, D.8 이 그 가정을
반증했다. **D.3 의 표는 유효하고 그 해석만 틀렸다.**

## D.9 🔴 그룹 풀 필드 전량 — **절단 없이 16개, 멤버 열거 필드 없음**

    introspect DataPool/Groups → 받은 16 / 총 16 · truncated **False**

    IGNORENETWORK STRUCTURELOCKED SYSTEMLOCKED LOCK INDEX COUNT NO NAME NOTE
    USEREXPANDED FADERENABLED OWNED HIDDEN DEPENDENCYEXPORT MEMORYFOOTPRINT
    DEFAULTSLOADED

**절단이 없다.** 시퀀스(65개, 28 수신, truncated)와 달리 그룹 풀은 **전량이 온다.**
그리고 **그 16개 안에 멤버/자식 열거 필드가 없다.**

**이것은 「도달 불가」가 아니라 「전량 봤는데 없다」이다.** D-6 이 「73개 미관측」을
근거로 *"배제되지 않았다"* 라 한 것은 **시퀀스 같은 절단 대상**에 대해 참이고,
**그룹 풀 노드에 대해서는 이 관측이 배제한다.**

⚠️ **다만 범위를 좁혀 읽어야 한다:**

- 이것은 **풀 노드**(`DataPool/Groups`)의 필드다. **개별 그룹 오브젝트**
  (`DataPool/Groups/13`)의 필드는 **이 쇼파일에 그룹이 없어 재지 못했다.**
- GROUPGEN 이 「멤버십을 못 읽는다」고 한 대상은 **개별 그룹**이다. 그러니 이
  관측은 그 판정을 **직접 반증하지도 확증하지도 않는다.**
- **개별 그룹에 `introspect` 를 쏘는 것이 다음 라운드의 1순위**다.
