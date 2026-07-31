# SPEC-COPILOT-OVERLAP-001 — 설계 근거 (design)

status: draft (v0.1.0, 2026-07-30) · Tier M · 출처: PRECHK 독립 run-audit 후보 I-15(`.moai/specs/SPEC-COPILOT-PRECHK-001/progress.md:653`) · 본 문서는 **왜 이렇게 만드는가**를 답한다. 무엇을 만드는가는 `spec.md`가, 어떤 순서로 만드는가는 `plan.md`가 소유한다. 설계 슬롯은 **9건(A~I)이고 전부 닫혔다.** 열린 결정 **0건**.

> **참조 규약.** 본 SPEC의 정본 `research.md` · `spec.md` · `acceptance.md`와 오케스트레이터 소유 `CONTRACT.md`는 **줄번호로 인용하지 않고** `REQ-OVERLAP-001` · `AC-OVERLAP-001` · `ASSUMPTION-31` 같은 안정 토큰과 절 제목만 쓴다. `파일:줄`은 **코드 · 룰북 · 응답기 프로토콜 · 타 SPEC 아티팩트**에만 쓴다.
>
> **축약 금지.** 요구·인수 토큰은 슬러그 포함 완전형만 쓴다. 슬러그를 뺀 형태는 이 문서 전체에 **0건**이다. clarification 마커는 **0건**이다. 근거 등급은 `[코드]` · `[문서]` · `[실측]` · `[미확정]` · `[추론]`이다. **(run-audit 정정: 초안이 4종으로 적었다. plan-audit 1회차가 `[추론]`을 5번째 등급으로 추가했는데 그 정정 커밋이 나머지 4문서만 손댔다. 본 문서의 `[추론]` 사용은 0건이라 문서 내부적으로 거짓은 아니었으나 닫힌 등급 집합의 정의가 문서마다 달랐다.)**
>
> **본 SPEC은 라이브 세션 0회다.** 따라서 **본 문서가 자기 관측으로 주장하는 `[실측]`은 0건**이다. 실측 값은 전부 `.moai/specs/SPEC-COPILOT-PRECHK-001/`을 출처로 하는 인용이며 항목마다 그 사실을 밝힌다.
>
> **본 문서는 `CONTRACT.md` §2의 결정 8건(D-1~D-8)과 §5의 마일스톤 M0~M8을 재논의하지 않는다.** 근거를 인용하되 결론을 바꾸지 않으며, 계수(요구 18 · 인수 조건 21 · 미검증 전제 5 · 마일스톤 9)를 건드리지 않는다.

---

## §1. 설계가 서는 지반 — 상계 논증의 수학적 핵심

### §1.1 닫힌 끝 구간에서 유도한다

`server/prechk/patch.py:336`이 구간을 **닫힌 끝**으로 만든다 `[코드]`:

```python
intervals[universe].append((start, start + width - 1, item))
```

주소 `a`·폭 `w`의 픽스처는 채널 `[a, a+w-1]`을 점유한다. 같은 유니버스의 다음 픽스처가 `a+g`에서 시작할 때(`g ≥ 1`이 인접 간격) 두 구간이 겹칠 조건은 다음 픽스처의 시작이 앞 픽스처의 끝 이하인 것이다:

```
a + g ≤ a + w - 1
⟺  g ≤ w - 1
⟺  g < w
```

관측된 모드 집합의 폭 최대값을 `W`라 하자. **열거가 완전하면** 실제로 어느 모드를 쓰든 그 폭 `w`는 `w ≤ W`를 만족한다. 따라서:

```
g ≥ W   ⟹   g ≥ w   ⟹   ¬(g < w)   ⟹   겹치지 않는다
```

**이 함의 사슬 전체가 `w`의 값을 모르는 채로 성립한다.** 그것이 조인 없이 판정할 수 있는 이유이고, 본 SPEC이 `ASSUMPTION-27`(픽스처 → 점유폭 조인)을 뒤집지 않고도 성립하는 이유다. `research.md` §1이 적듯 C-9는 *"폭이 유일한가"*를 물어 부정으로 닫혔고 I-15는 *"폭에 상계가 있는가"*를 묻는다 — **더 약한 명제로 같은 결론에 도달한다.**

### §1.2 판정의 반대 방향은 유도되지 않는다

`w ≤ W`는 `w`의 **상한**만 준다. 하한을 주지 않으므로 `g < W`에서는 아무것도 나오지 않는다. 수치로 보이면 이렇다 — `W = 31`, 관측된 폭 집합이 `{29, 31}`인 리그에서 `a = 1`:

| 간격 `g` | 실제 폭이 29일 때 | 실제 폭이 31일 때 | 판정 |
|---|---|---|---|
| `g = 31 (= W)` | `[1,29]` vs `[32,60]` — 분리 | `[1,31]` vs `[32,62]` — 분리 | **겹침 없음이 증명된다** |
| `g = 30 (= W-1)` | `[1,29]` vs `[31,59]` — 분리 | `[1,31]` vs `[31,61]` — **31에서 겹침** | **갈린다 — 증명 불가** |
| `g = 28` | `[1,29]` vs `[29,57]` — **29에서 겹침** | 겹침 | 겹치지만 그것도 **증명되지 않는다**(아래) |

가운데 행이 핵심이다. 두 경우를 구별하려면 *"이 픽스처가 어느 모드를 쓰는가"*를 알아야 하고 그것이 정확히 `ASSUMPTION-27`이 부정한 조인이다. 그러므로 **`간격 < 상계`는 충돌이 아니다 — 미확정이다.**

마지막 행도 충돌이 아니다. `g = 28`이면 관측된 두 폭 어느 쪽이든 겹치지만, 그 결론은 *"관측된 집합이 실제 모드 집합의 전부"*를 요구하고 그것은 `ASSUMPTION-32`(`DMXChannels` 자식 수 = DMX 슬롯 수)와 `ASSUMPTION-31`(연속 블록 전제)에 걸린다. **상계 논증은 상한만 다루므로 "겹침 있음"을 어느 간격에서도 증명하지 못한다.** `research.md` §3.4가 같은 결론을 낸다.

### §1.3 `간격 == 상계`는 깨끗하다 — off-by-one이 잠복해 있다

위 표의 첫 행이 `AC-OVERLAP-008` ②가 잡는 경계다. 폭 31이 `1..31`을 점유하면 32는 자유이므로 `g == W`는 **증명 가능하게 깨끗하다.** 그래서 `REQ-OVERLAP-008`이 판정 술어를 **`간격 < 상계`**로 고정하고 *"이하"* · *"초과"* 같은 경계 표현을 금지한다. 선행 기록의 *"간격이 상계 이하라 미확정"*은 off-by-one이며 `research.md` §3.1이 코드로 정정했다.

**이 오류는 현재 쇼파일에서 무증상이다.** 실측 최소 간격 42, 상계 31이므로(`.moai/specs/SPEC-COPILOT-PRECHK-001/progress.md:308-326` · `:403`, 둘 다 선행 SPEC 인용 `[문서]`) `42 < 31`도 `42 ≤ 31`도 거짓이라 두 표현이 같은 답을 낸다. 오류는 **간격이 정확히 상계인 리그에서 처음 드러나고, 그때 깨끗한 리그를 미확정으로 보고한다.** 따라서 §4의 합성 리그 `bound_gap_equals`가 없으면 이 결함은 영구히 보이지 않는다.

### §1.4 오류는 한 방향뿐이며 그것이 인수 조건의 형상을 정한다

`research.md` §5.3이 확립했다 — 구간 겹침이 `intervals`를 유니버스로 키잉하고(`server/prechk/patch.py:330`) 클러스터링 루프가 유니버스별로 돌며(`:339`) `_flush_cluster`가 `universe`를 스칼라로 받으므로(`:355`), **유니버스를 넘는 점유는 구조적으로 비가시하다** `[코드]`. 유니버스 조인 경로가 형상 자체로 없다.

**따라서 오늘 가능한 오류는 거짓 충돌이 아니라 거짓 "겹침 없음 증명" 한 방향뿐이다.** 설계는 그 한 방향만 막으면 되고, 그 대신 그 방향은 **빠짐없이** 막아야 한다.

### §1.5 반대칭이 어휘 4값을 강제한다

§1.1~§1.4를 합치면 판정 결과가 **네 종류**로 갈리고, 그 넷은 서로 다른 것을 주장하며 서로 다른 사용자 조치를 부른다.

| 상황 | 무엇이 성립하는가 | 값 |
|---|---|---|
| 이 슬롯의 폭이 주어졌다 | 구간을 실제로 비교했다. 그 슬롯에 대해 결론이 **무한정**이다 | `exact_widths` |
| 폭은 모르나 상계가 있고 `간격 ≥ 상계` | *"관측된 모드 집합 안에서"* 겹침 없음이 **증명됐다** | `bound_proves_clear` |
| 상계가 있고 `간격 < 상계` | 비교했으나 **결론이 나오지 않았다.** 충돌이 아니다 | `bound_inconclusive` |
| 정확폭도 상계도 없다 | **비교 자체가 일어나지 않았다** | `not_performed` |

세 번째와 네 번째를 하나로 접으면 *"수행했으나 결론 못 냄"*이 *"수행하지 않음"*으로 읽힌다. 그것이 이 프로젝트가 **7건**을 낸 결함 계열 1 — *"판독 실패"와 "그런 것이 없음"의 혼동* — 이다(`CONTRACT.md` §6). 두 번째와 세 번째를 접으면 증명된 청결이 미확정으로 격하되고, 두 번째와 첫 번째를 접으면 한정된 주장이 무한정으로 승격된다. **네 값은 압축 불가능하며 그것이 신규 축이 필요한 근본 이유다.** 슬롯 E가 기존 두 축에 넣을 수 없는 이유를 거짓 문자열로 마저 닫는다.

---

## §2. 설계 슬롯 A~I

### §2.0 마일스톤 정렬 — `CONTRACT.md` §5와 1:1

| 슬롯 | 무엇을 결정하는가 | **집행 마일스톤** |
|---|---|---|
| **A** | 3단 순회의 자료 형상 | **M2** |
| **B** | 1·2단 vs 3단 절단 술어 분리 | **M2** |
| **C** | 예산 회계와 소진의 의미 | **M2**(순회 내부) · **M6**(툴 스레딩) |
| **D** | 간격 산수의 자리와 대상 집합 | **M3** |
| **E** | 닫힌 어휘 4값의 의미론 | **M1**(어휘·라벨표·가드·정본) · **M3**(`bound_inconclusive` 산출) · **M5**(라벨 도달) |
| **F** | 페이로드 스키마 델타 | **M4**(신규 최상위 키) · **M8**(툴 표면 4값 전량) |
| **G** | 상계 근거의 전달 경로 | **M4**(필드와 키를 함께) · **M5**(요약 도달) |
| **H** | PRESERVE 게이트의 형상 | **M7** |
| **I** | 툴 배선의 경로 수령과 섹션 가드 | **M6** |
| — | **M0**에는 설계 슬롯이 없다 | `ASSUMPTION-34` 전제 판정이며 **형상 결정이 아니다.** 인메모리 프로토타입 1개로 갈리고 결과가 슬롯 H의 서술만 바꾼다. 그 절차는 `plan.md`가 소유한다 |

**AC 배정은 `CONTRACT.md` §5가 소유하며 본 문서는 재배정하지 않는다.** 아래는 대조용 재기술이며 **배정 합 21 · 중복 0 · 누락 0**이다.

| 마일스톤 | cycle_type | 배정 AC | 수 |
|---|---|---|---|
| M0 | none | `AC-OVERLAP-020` | 1 |
| M1 | tdd | `AC-OVERLAP-014` | 1 |
| M2 | tdd | `AC-OVERLAP-001` · `AC-OVERLAP-002` · `AC-OVERLAP-003` · `AC-OVERLAP-004` · `AC-OVERLAP-005` · `AC-OVERLAP-006` | 6 |
| M3 | tdd | `AC-OVERLAP-008` · `AC-OVERLAP-009` · `AC-OVERLAP-010` · `AC-OVERLAP-011` · `AC-OVERLAP-012` | 5 |
| M4 | tdd | `AC-OVERLAP-007` · `AC-OVERLAP-013` · `AC-OVERLAP-016` | 3 |
| M5 | tdd | `AC-OVERLAP-015` · `AC-OVERLAP-017` | 2 |
| M6 | tdd | `AC-OVERLAP-018` | 1 |
| M7 | tdd | `AC-OVERLAP-019` | 1 |
| M8 | tdd | `AC-OVERLAP-021` | 1 |
| **합** | | | **21** |

각 슬롯의 *"달린 인수 조건"*은 **그 결정을 검사하는** 인수 조건이며, 집행 마일스톤과 다른 마일스톤에 배정된 항목이 섞일 수 있다. 그 경우 소유 마일스톤을 함께 적는다.

---

### 슬롯 A — 3단 순회의 자료 형상

**무엇을 결정하는가.** `server/prechk/footprint.py`의 순회 함수가 무엇을 반환하는가, 그리고 완전성 판정과 `max` 연산의 **제어 흐름상 순서**를 무엇이 강제하는가.

**후보.**

| # | 형상 |
|---|---|
| A-i | `(상계: 정수 또는 없음, 완전성: bool, 표기: dict)` — `max`를 항상 계산하고 불완전이면 플래그를 붙인다. `drill_into` 형상의 직역 |
| A-ii | `(완전성: bool, 폭 집합: tuple[int, ...])` — `max`는 완전성이 참인 분기 **안에서만** 계산된다 |
| A-iii | 불완전을 **예외**로 신호한다 — 부분 결과를 아예 돌려주지 않는다 |

**선택: A-ii.** 순회가 반환하는 것은 *"상계"*가 아니라 **`(완전성, 폭 집합)`**이다. 상계는 소비자가 완전성 참 분기에서 접는다. 불완전하면 **상계라는 값이 존재하지 않는다.**

**근거.** `research.md` §4.1의 구제 시나리오가 A-i을 직접 반증한다. 2단(`DMXModes` 열거)에서 예산이 모드 3개 만에 소진되면 관측 부분집합은 `{29, 29, 29}`이고 계산된 *"상계"*는 **29**로, 참값 **31**보다 **작다**. 최소 간격이 30인 리그에서:

```
부분집합 상계 29 →  30 ≥ 29  →  bound_proves_clear (거짓)
참    상계 31 →  30 <  31  →  bound_inconclusive (옳음)
```

**부분 결과를 `max`에 넣는 순간 판정이 이미 뒤집혀 있다.** 나중에 붙는 플래그는 그것을 되돌리지 못한다 — **표기와 판정이 서로 다른 대상에 붙기 때문이다.** 플래그는 *순회*에 붙고 `bound_proves_clear`는 *주소 쌍*에 붙으며, 그 판정은 별도 자료구조를 타고 리포트와 요약까지 간다. 소비자가 플래그를 읽지 않는 경로가 하나라도 있으면 **거짓 안심이 사용자에게 도달한다.** A-ii는 그 경로를 형상으로 없앤다. 이것이 `REQ-OVERLAP-003`의 *"완전성 판정이 `max` 연산보다 앞에 온다"*가 문장이 아니라 **자료 형상**이어야 하는 이유다.

현재 쇼파일에서는 간격 42라 결론이 우연히 같아 이 결함이 보이지 않는다(`research.md` §4.1). **`AC-OVERLAP-003` ⑥이 그 시나리오를 그대로 코드로 옮긴 거짓 양성 재현 테스트를 요구하고, §4의 `subset_bound_trap` 리그가 그것이다.**

**기각한 후보와 사유.**

| # | 기각 사유 |
|---|---|
| A-i | 위 논증. 그리고 `AC-OVERLAP-003` ⑤가 AST로 순회 함수 본문을 읽어 `max` 노드가 완전성 판정 분기 **내부**에 있음을 확인하므로 A-i은 그 판정으로 죽는다. 선례 `drill_into`가 왜 A-i이어도 되는지는 슬롯 C가 분석한다 |
| A-iii | 불완전은 **정상 페이로드의 구조화된 부류**이지 예외가 아니다 — PRECHK `.moai/specs/SPEC-COPILOT-PRECHK-001/design.md:143`의 공통 처리 원칙(*"읽기 실패, 절단, 미수행, 부정 전제는 모두 정상 페이로드의 구조화된 부류이며 예외 산문으로만 흘리지 않는다"*)을 계승한다 `[문서]`. 그리고 `REQ-OVERLAP-007`이 순회 실패로 리포트의 나머지를 잃는 것을 금지하고 `AC-OVERLAP-021` ②가 착수 시점 `precheck_patch` 테스트 전건 통과를 요구한다 |

**집행 마일스톤: M2.**
**달린 인수 조건:** `AC-OVERLAP-001` ③④ · `AC-OVERLAP-003` ①②④⑤⑥ · `AC-OVERLAP-005` ④ (전부 M2 배정) · `AC-OVERLAP-007` ③ (M4 배정).

---

### 슬롯 B — 1·2단 vs 3단 절단 술어 분리

**무엇을 결정하는가.** 절단 판정 술어를 몇 개 두는가, 그리고 3단이 `childCount > len(children)` 비교를 쓰는가.

**후보.**

| # | 형상 |
|---|---|
| B-i | 단일 헬퍼 — 3단계 모두 `childCount > len(children)`이면 불완전 |
| B-ii | 단일 헬퍼 + 정책 파라미터 — `research.md` §6.5의 *"공용 헬퍼는 두 정책을 파라미터로 받아야 한다"* |
| B-iii | 술어 **2종**을 서로 다른 함수·분기로 분리 — 1·2단은 **목록 완전성**, 3단은 **계수 존재성** |

**선택: B-iii.**

**근거.** `.moai/specs/SPEC-COPILOT-PRECHK-001/progress.md:408`이 대칭을 깬다 `[문서]` — *"`DMXChannels` 열거는 `truncated=true`인데 `childCount`가 참값 29 또는 31을 준다"*. 세 단계가 필요로 하는 것이 다르기 때문이다:

| 단계 | 경로 | 필요한 것 | 절단이 치명적인가 | 술어 |
|---|---|---|---|---|
| 1단 | `Patch/FixtureTypes` | 자식 **집합** — 어느 타입이 있나 | **예** — 짧으면 타입 누락 | 목록 완전성 |
| 2단 | `…/<t>/DMXModes` | 자식 **집합** — 어느 모드가 있나 | **예** — 짧으면 상계가 부분집합의 최대값 | 목록 완전성 |
| 3단 | `…/<m>/DMXChannels` | **계수**만 — `childCount` | **아니다** — 계수는 정확하다 | 계수 존재성 |

B-i을 쓰면 **실측 형태(3단이 `truncated=true`)에서 상계가 영구히 산출되지 않는다** — 이 쇼파일에서 기능이 통째로 죽는다. 역으로 1·2단에 계수 존재성만 적용하면 부분집합 상계가 통과해 §1.2의 거짓 양성이 발화한다. **두 술어를 뭉개면 3단이 불필요하게 실패하거나 1·2단이 잘못 통과한다** — 그것이 `REQ-OVERLAP-004`의 전부다.

`AC-OVERLAP-004` ③이 *"3단 술어가 `childCount > len(children)` 비교를 쓰지 않는다"*를 기계로 요구하고, ④가 ①(3단 절단 → 판독 성공)과 ②(1단 절단 → 상계 미계산)를 **한 테스트에서 함께 돌려 결과가 다름**을 단정한다. B-i과 B-ii는 ④에서 죽는다.

**기각한 후보와 사유.**

| # | 기각 사유 |
|---|---|
| B-i | 위. `AC-OVERLAP-004` ①③④가 각각 죽인다 |
| B-ii | 파라미터화는 호출부에서 두 정책을 **선택 가능**하게 만들며, 선택 가능한 것은 잘못 선택될 수 있다 — 술어 분리는 형상으로 고정돼야 하고 인자로 고정되면 안 된다. 더 근본적으로 **`CONTRACT.md` §2 D-8이 수렴을 명시적으로 금지했다**: 저장소의 절단 계수 비교 3구현이 `childCount` 부재·0 정책에서 서로 다르다 — `server/prechk/inventory.py:389`(`root_was_short = child_count > len(children)`), `server/prechk/macro.py:249-251`(`countable`이 참일 때만 비교하는 관용), `server/orchestrator/tools.py:1296-1302`(정수 아니면 예외 + 짧으면 예외) `[코드]`. 파라미터 헬퍼는 그 셋을 통합하려는 시도의 첫 걸음이고, `acceptance.md` §D의 *"zero fixtures는 유효한 리그"*와 매크로 풀의 실측 근거를 충돌시킨다. **본 SPEC은 4번째 사본을 만들고 수렴하지 않으며, 수렴이 별도 리팩터 SPEC의 일임을 여기 적는다** |

**집행 마일스톤: M2.**
**달린 인수 조건:** `AC-OVERLAP-003` ①② · `AC-OVERLAP-004` ①②③④ (전부 M2 배정).

---

### 슬롯 C — 예산 회계와 소진의 의미

**무엇을 결정하는가.** 조회 예산을 어디에 두고, **소진이 무엇을 의미하는가.**

**선례의 형상 — `drill_into`(`server/orchestrator/tools.py:378-419`) `[코드]`.**

| 지점 | 원문 |
|---|---|
| `server/orchestrator/tools.py:406-408` | `if budget <= 0:` → `capped = True` → `break` |
| `server/orchestrator/tools.py:412-414` | 자식 조회 예외 → `obj["contents_unavailable"] = True` → `continue` |
| `server/orchestrator/tools.py:417-418` | `if capped:` → `entry["drilldown_capped"] = True` |

그리고 그 함수의 독스트링이 자기 설계 의도를 적는다: *"확인된 빈 컨테이너(`contents: []`)와 drill이 도달하지 못한 것(`contents_unavailable: True`)을 구분한다 — 둘을 합치면 순회 중 실패한 콘솔이 아무것도 설정되지 않은 쇼와 똑같아 보이며, 그것이 정확히 준비 점검이 없애려는 모호성이다"*(`server/orchestrator/tools.py:389-393`), *"예산이 떨어지면 부분 순회를 완전한 것으로 조용히 제시하는 대신 `drilldown_capped`로 표시한다"*(`server/orchestrator/tools.py:395-399`) `[코드]`.

**왜 그대로 복사하면 안 되는가.** `drill_into`에서 소진은 **그 자식에 국소적인 정보 부재**다. `contents_unavailable`이 붙은 객체 하나가 다른 객체의 `contents`를 거짓으로 만들지 않는다 — **표기와 그 표기가 수식하는 대상이 같다.** 상계 경로는 다르다. 예산이 2단 세 번째 모드에서 끊기면:

- **표기**는 *순회*에 붙는다 — *"모드 3개까지 읽었다"*.
- **판정**은 *주소 쌍*에 붙는다 — `bound_proves_clear`.

**표기가 남아 있어도 판정은 이미 오염돼 있고**, 그 판정은 페이로드와 요약을 타고 사용자에게 간다. 즉 `drilldown_capped` 형태를 복사하면 **거짓 안심이 정직한 표기와 나란히 출하된다.** 이것이 `research.md` §4.1이 *"부분 결과를 `max`에 넣고 나중에 플래그로 무효화하는 제어 흐름은 그 자체가 결함"*이라고 적은 것의 코드측 이유다.

**선택.** 예산은 순회 함수의 **파라미터**이고(`REQ-OVERLAP-005`), 소진은 **국소 표기가 아니라 전역 무효**다 — 1·2단 어느 지점에서든 소진되면 상계 계산 자체를 수행하지 않고 `not_performed`를 낸다. 슬롯 A의 자료 형상이 그것을 강제한다. 3단 소진도 같다: 폭 하나를 못 읽으면 관측 모드 집합이 불완전하다.

**기각한 후보와 사유.**

| # | 후보 | 기각 사유 |
|---|---|---|
| C-i | `drill_into` 직역 — `capped` 플래그 + 순회 계속 | 위 논증. `AC-OVERLAP-003` ③(예산 2로 낮춘 리그)과 ⑥(거짓 양성 재현)이 죽인다 |
| C-ii | 예산 없이 무제한 순회 | 조회 수가 `1 + T + Σ M_t`이고 `T`가 `ASSUMPTION-35`로 미확정이다. 조회 1건은 UDP 왕복 + 게이트 + 감사이며 `drill_into` 독스트링(`server/orchestrator/tools.py:395-399`)이 같은 사유로 예산을 둔다. `AC-OVERLAP-021` ③이 조회 계수가 예산 상한을 넘지 않을 것을 요구하고, `research.md` §6.1이 *"`state_calls`에 대한 등호 단정이 저장소 전체에 0건"*이라 조회 1건 추가가 아무 테스트도 깨뜨리지 않음을 확인했다 — **그래서 조회 비용을 지키는 인수 조건을 새로 쓴다** |
| C-iii | 예산을 순회 모듈의 상수로 | `REQ-OVERLAP-005`가 인자 수령을 요구하고 `AC-OVERLAP-005` ①이 시그니처를 기계로 본다. 그리고 모듈 상수는 `RIG_DRILLDOWN_QUERY_CAP`과 **서로 모르는 두 상한**이 되어, 한쪽을 조정한 배포가 다른 쪽을 조용히 초과한다 |

**소진과 예외의 사유 코드는 새로 만들지 않는다.** `REQ-OVERLAP-006`이 기존 분류 규칙 적용을 요구한다 — `REASON_UNRESOLVED = "path_not_resolved"` · `REASON_UNREACHABLE = "console_unreachable"`(`server/orchestrator/tools.py:196-197`)이고 그 메시지가 *"이 경로는 로드된 쇼파일에 없다 — 다른 섹션이 답했으므로 콘솔은 도달 가능하다"* / *"어느 섹션도 답하지 않았다"*로 분류 규칙을 문장으로 담는다(`:198-204`) `[코드]`. 상계 순회는 픽스처 루트 조회가 **이미 성공한 뒤에만** 도달하므로 *"형제가 답했다"*가 참이고 `REASON_UNRESOLVED`가 근거 있게 도출된다. **프로덕션 게이트 포트는 `ok=false`와 타임아웃을 같은 `StateQueryError`로 던지므로**(`server/safety/console.py:387-388`) 구분의 근거는 예외 타입이 아니다 — `AC-OVERLAP-006` ③이 그것을 기계로 고정한다.

**집행 마일스톤: M2**(순회 내부) · **M6**(툴에서의 예산 스레딩).
**달린 인수 조건:** `AC-OVERLAP-003` ③④ · `AC-OVERLAP-005` ① · `AC-OVERLAP-006` ①②③④ (M2 배정) · `AC-OVERLAP-018` (M6 배정) · `AC-OVERLAP-020` ⑤ (M0 배정) · `AC-OVERLAP-021` ③ (M8 배정).

---

### 슬롯 D — 간격 산수의 자리와 대상 집합

**무엇을 결정하는가.** 인접 간격을 **어떤 집합** 위에서 계산하는가, 그리고 그 집합을 **어느 기존 함수**에서 얻는가.

**후보.**

| # | 형상 |
|---|---|
| D-i | `_range_overlaps`의 정렬을 재사용한다 |
| D-ii | `_address_duplicates`의 `(유니버스, 주소)` 그룹핑의 **키 집합**을 쓴다 |
| D-iii | 신규 독립 그룹핑을 만든다 |

**선택: D-ii.** 대상 집합은 `_address_duplicates`의 키 집합이고, 인접차와 최소값은 신규다(`research.md` §6.5: 저장소 전체에 `a[i+1]-a[i]`를 구하는 지점 **0건**).

**근거 — D-i은 원리적으로 불가능하다.** `server/prechk/patch.py:330-336` `[코드]`:

```python
intervals: dict[int, list[tuple[int, int, _Assessed]]] = defaultdict(list)
for item in assessed:
    width = _footprint_width(policy, item.record.slot)
    if not item.parse.ok or not item.type_mode_ok or width is None:
        continue
    start = item.parse.address
    intervals[item.parse.universe].append((start, start + width - 1, item))
```

`widths={}`이면 `width`가 항상 `None`이라 `intervals`가 빈 딕셔너리로 남고 `server/prechk/patch.py:339`의 `for universe, entries in sorted(intervals.items())`가 **한 번도 돌지 않는다.** 상계 경로의 전제가 *"폭과 무관하게 주소만으로"*이므로 이 함수의 필터 첫 줄과 정면 충돌한다.

**근거 — D-ii가 맞는 것은 우연이 아니라 두 기존 함수의 설계 차이에서 나온다.** 필터 술어를 나란히 놓으면 드러난다 `[코드]`:

| 함수 | 필터 | 좌표 |
|---|---|---|
| `_address_duplicates` | `if item.parse.ok:` — **그것뿐이다** | `server/prechk/patch.py:269-271` |
| `_range_overlaps` | `if not item.parse.ok or not item.type_mode_ok or width is None: continue` | `server/prechk/patch.py:331-334` |

`_range_overlaps`가 `type_mode_ok`를 요구하는 이유를 그 함수의 독스트링이 적는다(`server/prechk/patch.py:327-328`): *"타입 또는 모드가 미해결인 픽스처는 제외된다 — 그 점유는 판정할 수 없고 `REQ-PRECHK-009`가 어느 쪽으로도 세는 것을 금지한다."* **그 요구는 폭을 알아야 하는 술어에만 필요하다.** 상계 논증은 정확히 그 반대다 — §1.1의 함의 사슬 전체가 `w`의 값을 모르는 채로 성립하므로, **모드를 모르는 픽스처의 폭도 `W` 이하다.**

**따라서 `type_mode_ok`를 요구하지 않는 것이 이 설계의 핵심이다.** 요구하면 그 자체가 논증의 오해이며, 오해를 기계로 잡는 것이 `AC-OVERLAP-010` ③(판독 실패 픽스처가 간격 계산에 **포함**된다)과 ④(같은 픽스처가 정확폭 축에서는 **제외**된다 — 두 축의 술어가 다름을 한 테스트에서 단정)다.

**근거 — 대상이 "키 집합"인 이유.** `_address_duplicates`는 같은 `(유니버스, 주소)`를 하나의 그룹으로 접는다(`server/prechk/patch.py:268-271`). 그 **키 집합**을 쓰면 중복 주소가 한 번만 들어가 **간격 0이 생기지 않는다.** 간격 0은 이미 주소 중복 축이 잡으므로(`REQ-PRECHK-007`) 여기서 다시 세면 이중 계상이다 — `REQ-OVERLAP-010`이 금지하고 `AC-OVERLAP-010` ①②가 *"이중 계상이 아니라 분업"*임을 확인한다.

**근거 — 유니버스 내부 한정이 공짜로 따라온다.** 키가 `(유니버스, 주소)` 튜플이므로 유니버스별 버킷이 그룹핑에서 자연히 나온다. 유니버스를 넘는 감산은 **서로 다른 주소 공간의 감산이며 무의미하다**(`REQ-OVERLAP-009`). 그리고 이것은 **착수 시점에 살아 있는 뮤테이션 구멍**이다 — `_range_overlaps`를 두 유니버스로 밟는 테스트가 0건이고(GO 분기 유일 테스트가 `overlap.universe == 1` 하나만 단정한다, `server/tests/test_prechk_patch.py:223`) 서로소성을 고정하는 테스트는 주소 중복 축의 1건뿐이다(`server/tests/test_prechk_patch.py:184-189`) `[코드]`. `AC-OVERLAP-009` ③④가 그 구멍을 닫는다.

**근거 — 주소 유효 범위 검증이 간격 계산의 전제조건이다.** 파서는 `server/prechk/patch.py:72`의 `^(\d+)\.(\d+)$` 하나이며 **하한도 상한도 없다** `[코드]`. `research.md` §4.4가 실행으로 확인했듯 `0.0` · `1.0` · `1.99999`가 전부 `ok=True`를 내고, 파싱 불가 목록(`server/tests/test_prechk_patch.py:105`)에 그 값들이 없어 고정하는 테스트도 0건이다. **오늘은 무해하고 상계 논증에서는 유해하다** — 정확 일치 중복만 볼 때 무의미한 주소는 자기와만 충돌하지만, 간격을 계산하면 무의미한 주소가 무의미한 간격을 만들고 그 간격이 판정을 낸다. 따라서 `REQ-OVERLAP-012`가 요구하는 검증은 **간격 계산 앞**에 오며, 범위를 벗어난 값은 **판독 실패로 분류**되어 *"그런 픽스처가 없다"*로 바뀌지 않는다(`AC-OVERLAP-012` ②). 상한은 `ASSUMPTION-33`이 미확정으로 두므로 검증은 **하한과 형식**에만 단정적이다(`AC-OVERLAP-012` ④).

**기각한 후보와 사유.**

| # | 기각 사유 |
|---|---|
| D-i | `widths={}`에서 정렬 자체가 일어나지 않는다(`server/prechk/patch.py:330-339`). 재사용 불가는 취향이 아니라 형상이다 |
| D-iii | 두 축의 그룹핑 규칙이 서로 모르게 갈라질 수 있다 — 한쪽이 주소 정규화를 고치면 다른 쪽이 조용히 다른 집합을 본다. `_address_duplicates`의 키 집합을 **추출**해 양쪽이 같은 것을 보게 한다. `AC-OVERLAP-010` ②가 두 축의 분업을 한 리그에서 확인하므로 갈라진 그룹핑은 거기서 드러난다 |

**집행 마일스톤: M3.**
**달린 인수 조건:** `AC-OVERLAP-008` ①②③④ · `AC-OVERLAP-009` ①②③④ · `AC-OVERLAP-010` ①②③④ · `AC-OVERLAP-012` ①②③④ (전부 M3 배정).

---

### 슬롯 E — 닫힌 어휘 4값의 의미론

**무엇을 결정하는가.** 각 값이 **정확히 무엇을 주장하고 무엇을 주장하지 않는가**, 그리고 왜 기존 축에 넣을 수 없는가.

**선택: `CONTRACT.md` §2 D-5의 어휘를 아래 의미론으로 고정한다.**

| 값 | **주장하는 것** | **주장하지 않는 것** |
|---|---|---|
| `exact_widths` | 이 슬롯의 폭이 주어졌고 실제 구간으로 비교했다. 결과가 무엇이든 **그 슬롯에 대해 무한정**이다 | 리그 전체가 정확폭으로 판정됐다는 것. **슬롯 단위 주장**이다 |
| `bound_proves_clear` | **관측된 모드 집합**의 최대 폭 `W`에 대해 `간격 ≥ W`이므로, 그 집합 안의 어느 모드를 쓰더라도 겹치지 않는다 | 겹침이 없다는 **무한정** 명제. 열거되지 않은 모드 · 다중 브레이크(`ASSUMPTION-31`) · `childCount ≠ 슬롯 수`(`ASSUMPTION-32`)는 이 주장 **밖**이다 |
| `bound_inconclusive` | 상계를 얻어 **비교했으나** `간격 < 상계`라 결론이 나오지 않았다 | 겹침이 **있다**는 것. 충돌이 아니다(`REQ-OVERLAP-011`) |
| `not_performed` | 정확폭도 상계도 없어 **비교 자체가 일어나지 않았다** | 겹침이 없다는 것. 그리고 *"그런 모드가 없다"*도 아니다 |

**왜 `COLLISION_KIND`에 넣을 수 없는가 — 거짓 문자열로.** `COLLISION_KIND = frozenset({"address_duplicate", "range_overlap"})`(`server/prechk/verdicts.py:25`) `[코드]`. 이 축의 값은 `Collision`에 붙고, `Collision`은 `collisions.range_overlaps` 목록의 항목이며, 그 목록에 든 슬롯은 `FIXTURE_VERDICT`의 `collision`을 받는다. 즉 `bound_inconclusive`를 `COLLISION_KIND`의 값으로 만들면 그 순간 **사용자가 읽는 문자열이 `충돌`이 된다** — `FIXTURE_VERDICT_LABELS["collision"] = "충돌"`(`server/prechk/report.py:67`) `[코드]`. §1.2가 보였듯 상계 논증은 **겹침 있음을 어느 간격에서도 증명하지 못하므로** 그 문자열은 거짓이다. 그리고 `collision_total`(`server/prechk/patch.py:232-233`)에 더해지는 순간 요약이 *"충돌 N건"*으로 발화한다.

**왜 `SKIPPED_CHECK_KIND`에 넣을 수 없는가 — 반대 방향의 거짓 문자열로.** 그 축의 라벨은 전부 **미수행**이다 — `SKIPPED_CHECK_KIND_LABELS["range_overlap_descope"] = "구간 겹침 판정 미수행"`(`server/prechk/report.py:90`) `[코드]`. `bound_proves_clear`를 여기 넣을 수 없는 것은 자명하고, **`bound_inconclusive`를 여기에만 넣으면 *"수행했으나 결론 못 냄"*이 *"수행하지 않음"*으로 읽힌다.** 그것이 이 프로젝트가 7건을 낸 결함 계열 1이며, `CONTRACT.md` §6이 *"코드가 방어 가능해도 사용자가 읽는 문자열이 거짓이면 결함"*이라고 못박은 그대로다.

**둘 다 넘어지는 경우가 신규 축을 강제한다.** `bound_inconclusive` 하나를 놓고 두 기존 축을 각각 시험하면 한쪽은 *"충돌"*을, 다른 쪽은 *"미수행"*을 사용자에게 출력한다 — **양쪽 다 거짓이다.** 그리고 `bound_proves_clear`와 `exact_widths`는 애초에 실릴 자리가 없다. 따라서 네 값은 **하나의 신규 축**이어야 한다.

**그럼에도 `SKIPPED_CHECK_KIND`에 1값이 추가되는 이유는 다르다.** `overlap_basis`는 **리그 전역 스칼라**이므로(`CONTRACT.md` §2 D-4) *"어느 유니버스의 어느 슬롯이 미확정인가"*를 나를 수 없다. 그 고지 채널이 `range_overlap_bound_inconclusive`다. **`skipped_checks`가 kind로 중복 제거하므로 kind당 1행만 리포트에 도달하고**(D-4) 한 행의 `reason`에 유니버스·슬롯을 열거한다 — `_judgeable_without_width`(`server/prechk/patch.py:305-321`)가 이미 그 형태이며, 그 독스트링이 왜 그 고지가 필요한지 적는다: *"비교되지 않은 픽스처를 조용히 제외하면 `observed_clear`가 주어지고 `충돌 0건`이 미수행 고지 없이 출력된다 — 한 번도 비교되지 않은 픽스처가 깨끗하다고 보고되는 것이다. '비교되지 않음'과 '겹침 없음'은 서로 다른 문자열이어야 한다"*(`:310-313`) `[코드]`.

**어휘 표기의 세 강제.** 전부 `CONTRACT.md` §2 D-5·D-6의 재게시다.

1. **라벨표 이름은 `OVERLAP_BASIS_LABELS`** — AST 스캔의 표 인식 규칙이 `_LABELS` 접미사다(`AC-OVERLAP-014` ⑤).
2. **레지스트리와 테스트 정본 리스트 양쪽에 맨 끝 append** — 순서를 보는 단정이 `server/tests/test_prechk_verdicts.py:55-61`의 하나뿐이고, 런타임 순서 의존이 0건이며, append는 기존 5줄을 바이트 동일하게 남겨 두 편집의 일치를 리뷰가 눈으로 확인할 수 있다(`research.md` §7.4).
3. **가드 루프를 `CLOSED_VOCABULARIES` 순회로 바꾼다** — 아래.

**가드 루프 구조 변경의 코드측 근거.** `server/prechk/report.py:111-117`이 **하드코딩 5-튜플**이고 `:118-119`가 검사다 `[코드]`:

```python
for _vocabulary, _codes in (
    ("completeness", COMPLETENESS),
    ("fixture_verdict", FIXTURE_VERDICT),
    ("collision_kind", COLLISION_KIND),
    ("read_failure_kind", READ_FAILURE_KIND),
    ("skipped_check_kind", SKIPPED_CHECK_KIND),
):
    if set(VOCABULARY_LABELS[_vocabulary]) != set(_codes):
        raise UnknownVerdict(...)
```

신규 축을 이 튜플에 넣지 않아도 **import는 성공하고**, 라벨 드리프트는 `server/tests/test_prechk_report.py:273-278`이 `CLOSED_VOCABULARIES`를 순회하므로 **여전히 잡히며**, 따라서 **실패 0건**이다 `[코드]`. 잃는 것은 신규 축의 import 시점 결속뿐이다. **이것이 스위트가 못 잡는 유일한 단계이며 규율 16의 직격 사례다**(`research.md` §7.2). `:111-117`을 `CLOSED_VOCABULARIES.items()` 순회로 바꾸면 **그 단계가 구조적으로 사라진다** — 등재할 튜플이 없으므로 *"빠뜨린다"*가 표현 불가능해진다. `AC-OVERLAP-014` ⑦이 그 형태를 인정하고 기계로 확인한다. **튜플에 항목을 추가하는 것으로 끝내지 않는 이유는 다음 축을 추가하는 사람이 같은 함정을 만나기 때문이다**(D-6).

**금지 토큰.** 스캐너 3종(`_VACUOUS_ASSERTION` · `_RESPONSE_ASSERTION_TOKENS` · `repr(payload)` 부분문자열 스캔)에 대해 제안 어휘 전량이 통과함이 확인됐다(`research.md` §7.6). `bound_proves_clear`는 `proves`이며 금지 토큰 `proven`이 아니다. `proven` · `verified` · `all_clear` · `_lit` 계열을 쓰지 않는 것이 강제되며 `AC-OVERLAP-014` ⑨가 그것을 판정한다.

**모듈 안 문자열 리터럴 금지.** `server/prechk/**`의 문자열 상수에 `"Footprint"` · `"Channels"` · `"ChannelCount"` · `"Universe"` · `"Address"` · `"No"` · `"Break"`를 쓰면 `_FORBIDDEN_PROPERTY_NAMES` 스캔이 죽인다(`server/tests/test_prechk_inventory.py:378-399`) `[코드]`. 소문자 모듈명 `footprint.py`는 그 스캔의 대상이 아니다 — 스캔은 **문자열 상수 집합만** 정확 일치로 검사한다(D-1).

**기각한 후보와 사유.**

| # | 후보 | 기각 사유 |
|---|---|---|
| E-i | 4값을 `COLLISION_KIND`에 흡수 | 위. 사용자 문자열이 `충돌`로 거짓이 된다. 그리고 `AC-OVERLAP-014` ③이 `COLLISION_KIND` 바이트 동일을 요구하고 `server/tests/test_prechk_verdicts.py:26-45`의 집합 단정이 즉시 깨진다 |
| E-ii | 4값을 `SKIPPED_CHECK_KIND`에 흡수 | 위. `bound_proves_clear`·`exact_widths`가 실릴 자리가 없고 `bound_inconclusive`가 *"미수행"*으로 거짓 표시된다 |
| E-iii | 자유 문자열 사유로 반환 | 닫힌 어휘가 아니면 `validate()`가 걸러낼 대상이 없다. `REQ-OVERLAP-014`가 *"어휘 밖 값은 조용히 통과하지 않는다"*를 요구한다 |
| E-iv | 신규 축을 만들고 `SKIPPED_CHECK_KIND` 1값은 생략 | 리그 전역 스칼라가 유니버스·슬롯을 나를 수 없다(D-4). 미확정이 **어디서** 났는지 사용자에게 도달하지 않는다 |
| E-v | 가드 루프 5-튜플에 항목만 추가 | 무증상 단계를 남긴다. 다음 축을 추가하는 사람이 같은 함정을 만난다(D-6). `AC-OVERLAP-014` ⑦이 구조적 대안을 요구한다 |
| E-vi | 레지스트리 중간 삽입(알파벳 순 등) | 두 리스트의 어긋남을 단정 하나에만 맡긴다. append는 기존 5줄을 바이트 동일하게 남긴다(`research.md` §7.4) |

**집행 마일스톤: M1**(어휘·라벨표·가드 구조 변경·정본 3단정 갱신) · **M3**(`bound_inconclusive` 산출) · **M5**(라벨 도달).
**달린 인수 조건:** `AC-OVERLAP-014` ①~⑨ (M1 배정) · `AC-OVERLAP-011` ①②③④⑤ (M3 배정) · `AC-OVERLAP-015` · `AC-OVERLAP-017` (M5 배정).

---

### 슬롯 F — 페이로드 스키마 델타

**무엇을 결정하는가.** 상속한 스키마 정본을 어디에 재게시하고, 신규 최상위 키의 이름과 **내부 구조**를 무엇으로 두며, 상속된 드리프트를 어떻게 다루는가.

**상속 원본은 좌표로 인용한다.** PRECHK `design.md` **§5.1 리포트 페이로드 스키마**는 `.moai/specs/SPEC-COPILOT-PRECHK-001/design.md:159-173`이고, 그 규범성 선언은 **`:161`** — *"구현은 dataclass와 `to_dict()`를 써도 되지만, **키와 닫힌 어휘는 이 표를 따른다**"* `[문서]`. 서술이 아니라 계약이다.

**PRECHK 문서를 고치는 것이 아니다.** `.moai/specs/SPEC-COPILOT-PRECHK-001/progress.md:805`가 *"갱신하지 않을 것"*에 `plan.md` · `design.md` · `research.md` 본문을 명시로 넣었다(소유권 매트릭스상 sync는 고치지 않는다) `[문서]`. 그 귀결로 `research.md` §8.3이 지시한 형태를 따른다 — **본 문서가 상속 정본을 재게시하고 델타만 명시한다.**

#### §F.1 상속한 7키 — PRECHK `.moai/specs/SPEC-COPILOT-PRECHK-001/design.md:165-171`의 재게시

| 키 | 값 | 필수성 | **본 SPEC의 델타** |
|---|---|---|---|
| `inventory` | `{path, child_count, observed_count, recovered_count, missing_count, completeness, recovery_boundary, index_domain_unknown}` | 항상 | **무변경.** 정확 8키가 `server/tests/test_prechk_inventory.py:890-901`로 잠겨 있다 |
| `fixtures` | 각 항목 `{slot, name, patch_raw, universe, address, fixture_type, mode, fid_note, verdict, reasons}` | 관측 픽스처 전량 | **무변경.** 정확 10키가 `server/tests/test_prechk_patch.py:453-464`로 잠겨 있다 — **슬롯별 근거를 여기 얹을 수 없다**(§F.3) |
| `collisions` | `{address_duplicates, range_overlaps}` | 항상, 비어 있어도 포함 | **무변경.** 정확 2키(`server/tests/test_prechk_patch.py:451`) + 딕셔너리 전체 동등(`server/tests/test_prechk_report.py:118`). **미확정은 여기 들어가지 않는다**(`REQ-OVERLAP-011`) |
| `read_failures` | `{slot, name, property, raw_value, kind, detail}` 목록 | 항상, 비어 있어도 포함 | **무변경.** 범위 밖 주소의 판독 실패는 기존 `kind` 어휘로 분류한다(`REQ-OVERLAP-012`, 새 사유 어휘 0건) |
| `skipped_checks` | `{kind, reason, assumption}` 목록 | 미수행 축이 있으면 포함 | **키 구조 무변경**(정확 3키, `server/tests/test_prechk_patch.py:245`). **값 어휘에 `range_overlap_bound_inconclusive` 1값 추가.** kind당 1행 |
| `macro` | `{created, target_kind, targets, commands, requires_human_visual_confirmation, reason}` | 매크로 요청 시 | **무변경.** 판정 계층에서 이중 잠금(`server/tests/test_prechk_macro.py:583-590` · `server/tests/test_prechk_report.py:397-406`). **툴 계층 드리프트는 §F.4** |
| `summary_ko` | 한국어 요약 문자열 | 항상 | **문자열 내용에 `overlap_basis` 라벨 추가**(`REQ-OVERLAP-017`) |

#### §F.2 신규 최상위 키 — `overlap_basis`

**자리 선택의 근거.** 기존 페이로드 블록 6개가 전부 정확 키집합으로 잠겨 있고 **무충돌 자리는 최상위 키 하나뿐이다**(`research.md` §8.1). 최상위는 부분집합·포함 단정만 있다 — `server/tests/test_prechk_patch.py:444-450`이 5키 부분집합(`<=`)이고 `server/tests/test_prechk_report.py:103-114`가 7키 각각의 `in` 검사다 `[코드]`. 그리고 저장소 선례가 있다: 핸들러가 `macro_execution`·`macro_requery`를 같은 방식으로 덧붙인다.

**내부 구조는 어떤 테스트도 단정하지 않으므로 자유이나**(D-4) **`AC-OVERLAP-016` ④가 정확 키집합 단정을 새로 만들 것을 요구한다** — 얹기만 하면 아무것도 안 깨지지만 아무도 지키지 않는다. `research.md` §8.2의 등가가 그것이다: ***"문서 무변경 가능한 자리 = 아무도 안 지키는 자리."*** 새 단정 없이 얹으면 **커버 침식**이다.

**결정 — 7키.**

| 키 | 값 | 왜 필요한가 |
|---|---|---|
| `basis` | `overlap_basis` 4값 중 하나. **리그 전역 스칼라** | `REQ-OVERLAP-014` · `AC-OVERLAP-017` ①. D-4가 최상위 스칼라를 강제한다 |
| `bound` | 상계 정수 또는 없음 | `REQ-OVERLAP-016`의 *"상계 값"* · `AC-OVERLAP-016` ① |
| `bound_source` | 상계가 온 **경로와 계수** | `AC-OVERLAP-016` ②가 *"자유 산문이 아니라 경로를 담는다"*를 요구한다 |
| `mode_widths` | 관측된 폭 집합. 열거 완전할 때만 비어 있지 않다 | `AC-OVERLAP-001` ②가 주입 폭 `{17, 23}` → 상계 23을 확인하려면 관측 집합이 페이로드에 있어야 한다 |
| `exact_width_slots` | 정확폭으로 비교된 슬롯 | `AC-OVERLAP-013` ③의 *"결과가 각각의 근거로 보고된다"* — §F.3 |
| `bound_slots` | 상계로 비교된 슬롯 | 같음 |
| `observation_note` | 관측 범위 한정 한국어 문구 | `REQ-OVERLAP-015` · `AC-OVERLAP-015` ①②④ |

**금지 토큰 대조.** 일곱 이름 중 `bound_source` · `mode_widths`는 `research.md` §7.6의 통과 목록에 직접 있다. 나머지 다섯(`basis` · `bound` · `exact_width_slots` · `bound_slots` · `observation_note`)은 `verified` · `all_clear` · `no_conflict` · `responded` · `fixture_ok` · `patch_ok` · `proven` · `respon` · `is_lit` · `_lit` · `lit_` 어디에도 부분문자열로 걸리지 않는다. **스캔이 `repr(payload)`의 값까지 훑으므로**(`research.md` §7.6) `observation_note`의 한국어 문구에 금지 ASCII 토큰이 섞이지 않아야 한다 — 한정 표현은 순한국어로 쓴다.

**정직성 제약 2건 — D-4의 재게시.**

1. **리그 전역 스칼라는 수행된 비교 전체의 최약 등급이다.** 3슬롯이 비교되지 않은 상태에서 `bound_proves_clear`를 리그 전역으로 찍는 것은 결함이다. 등급 순서는 §1.5의 주장 강도에서 따라온다: `not_performed` ≺ `bound_inconclusive` ≺ `bound_proves_clear` ≺ `exact_widths`. **비교가 0건이면 스칼라는 `not_performed`다**(`AC-OVERLAP-003` ① · `AC-OVERLAP-007` ③). 미비교 슬롯이 남아 있다는 사실 자체는 부분 커버리지 고지가 나른다(`AC-OVERLAP-013` ⑤).
2. **`range_overlap_bound_inconclusive`는 kind당 1행이다.** 유니버스별 다중 행 불가 — 한 행의 `reason`에 유니버스·슬롯을 열거한다.

#### §F.3 슬롯별 근거를 픽스처 행에 얹지 않는 이유

`REQ-OVERLAP-013`이 정확폭을 상계보다 우선시키므로 혼재 리그가 정상 입력이고, `AC-OVERLAP-013` ③이 그 리그에서 *"결과가 각각의 근거로 보고된다"*를 요구한다. **`fixtures[]` 행은 정확 10키로 잠겨 있어**(`server/tests/test_prechk_patch.py:453-464`) 슬롯별 `basis` 키를 얹으면 그 단정이 즉시 깨진다 `[코드]`. 따라서 슬롯별 귀속은 신규 최상위 키 **안의** `exact_width_slots` · `bound_slots` 두 목록이 나른다. 그 자리는 내부 구조가 자유이며(D-4) 새로 만드는 정확 키집합 단정이 지킨다(`AC-OVERLAP-016` ④). **이것은 새 요구가 아니라 잠긴 자리를 피하는 배치 결정이다.**

#### §F.4 상속된 스키마 드리프트 2건 — 명시하되 **정정하지 않는다**

**지금 정본이 실물보다 작다** `[코드]`.

| # | 드리프트 | 좌표 | 상태 |
|---|---|---|---|
| 1 | `PatchEvaluation.to_dict()`가 최상위에 `verdict_counts` · `read_failure_counts` · **`scope_qualified`** · **`scope_note`** 4키를 더 내는데 PRECHK 정본은 7키만 열거한다 | 정본 `.moai/specs/SPEC-COPILOT-PRECHK-001/design.md:165-171` vs 구현 `server/prechk/patch.py:245-248`(그 `to_dict()`는 `:235-249`이며 9키를 낸다). 앞 2개는 코드 주석이 의도를 적었고(`server/prechk/patch.py:207-214`) 뒤 2개는 정본에도 주석에도 근거가 없다 | **정정하지 않는다** |
| 2 | 툴 페이로드가 `macro`에 **`executed`를 7번째 키로 주입**한다 — `payload["macro"]["executed"] = not inner.result.is_error`(`server/orchestrator/tools.py:1491`). `server/tests/test_prechk_tool.py:585` · `:593` · `:600`이 그 키를 단정한다. **즉 정본 6키가 이미 거짓이다** | 정본 `.moai/specs/SPEC-COPILOT-PRECHK-001/design.md:170` | **정정하지 않는다** |

드리프트 2는 **층에 따라 참거짓이 갈린다** — 판정 계층에서는 6키가 참이고(이중 잠금이 지킨다) 툴 계층에서 7키가 된다. 즉 정본이 어느 층을 서술하는지가 정의되지 않았다.

**본 SPEC은 정정하지 않는다.** `spec.md` §D가 *"기존 스키마 드리프트 2건의 정정"*을 명시적으로 범위 밖에 뒀다 — 정정은 본 SPEC의 요구와 무관하며 **툴 층 스키마 계약을 별도로 정의해야 하는 작업**이다. 본 문서가 하는 일은 **재게시된 정본이 실물과 어긋난다는 사실을 좌표와 함께 남기는 것**이며, 그것이 없으면 후속 SPEC이 §F.1의 표를 실물로 믿는다.

**기각한 후보와 사유.**

| # | 후보 | 기각 사유 |
|---|---|---|
| F-i | `overlap_basis`를 `collisions` 안에 넣는다 | `server/tests/test_prechk_patch.py:451`의 정확 2키와 `server/tests/test_prechk_report.py:118`의 딕셔너리 전체 동등이 즉시 깨진다 |
| F-ii | `inventory` 블록에 넣는다 | 정확 8키(`server/tests/test_prechk_inventory.py:890-901`)가 깨진다. 그리고 상계는 인벤토리의 성질이 아니라 판정의 근거다 |
| F-iii | 슬롯별 `basis`를 `fixtures[]` 행에 얹는다 | 정확 10키가 깨진다(§F.3) |
| F-iv | 최상위 키를 얹고 정확 키집합 단정을 만들지 않는다 | `AC-OVERLAP-016` ④가 금지한다. *"문서 무변경 가능한 자리 = 아무도 안 지키는 자리"*(`research.md` §8.2) |
| F-v | PRECHK `design.md` §5.1을 직접 고쳐 델타를 반영한다 | `.moai/specs/SPEC-COPILOT-PRECHK-001/progress.md:805`가 금지한다. plan-phase 산출물은 그 시점의 판단 기록이며 사후 재작성은 흐린다 |
| F-vi | 드리프트 2건을 이 SPEC에서 정정한다 | `spec.md` §D가 범위 밖으로 뒀다. 툴 층 스키마 계약 정의라는 별도 작업을 끌어들인다 |

**집행 마일스톤: M4**(신규 최상위 키·정확 키집합 단정) · **M8**(툴 표면에서 4값 전량 산출).
**달린 인수 조건:** `AC-OVERLAP-013` ①②③⑤ · `AC-OVERLAP-016` ①②④ (M4 배정) · `AC-OVERLAP-021` ① (M8 배정).

---

### 슬롯 G — 상계 근거의 전달 경로

**무엇을 결정하는가.** 상계의 출처가 어떤 필드에 담기고 **어떤 키로 나가는가**, 그리고 그 둘을 언제 만드는가.

**선례 — 필드는 있는데 소비자가 0건이다.** `FootprintPolicy.source: str = ""`가 `server/prechk/patch.py:170`에 **필드로 존재한다** `[코드]`. 그런데 그 값을 **읽는 지점이 저장소에 0건**이다 — 전수 확인 결과 등장 지점은 선언 1건(`server/prechk/patch.py:170`)과 테스트의 **대입** 3건(`server/tests/test_prechk_patch.py:74` · `:286` · `server/tests/test_prechk_report.py:444`)뿐이고, 어떤 `to_dict()`도 그것을 내보내지 않는다. 즉 **근거를 받는 필드는 만들어졌고 내보내는 키는 만들어지지 않았다.**

그리고 결정적으로 — **본 SPEC이 필요로 하는 바로 그 문자열이 이미 저장소에 있고 아무 데도 도달하지 않는다** `[코드]`:

```
server/tests/test_prechk_inventory.py:372
FOOTPRINT_SOURCE = "Patch/FixtureTypes/1/DMXModes/1/DMXChannels childCount"
```

**결정.** 근거 필드와 페이로드 키를 **같은 마일스톤에서 함께** 만든다. `AC-OVERLAP-016` ③이 그것을 회귀 방지 단정으로 요구한다 — *"근거 필드를 담는 자료구조와 페이로드 키가 함께 존재한다."* 세 지점(순회의 `bound_source` 산출 → `overlap_basis.bound_source` 키 → 요약 라벨)이 M4~M5 사슬에서 닫힌다.

**기각한 후보와 사유.**

| # | 후보 | 기각 사유 |
|---|---|---|
| G-i | 기존 `FootprintPolicy.source`를 상계 출처로 재사용 | 그 필드는 **주입된 정확폭**의 출처다 — 독스트링이 *"injected, never derived"*라고 못박는다(`server/prechk/patch.py:160`) `[코드]`. 상계는 **런타임 파생**이다. 같은 필드에 두 의미를 겹치면 `exact_widths`와 `bound_proves_clear`의 출처를 구별할 수 없고, `AC-OVERLAP-016` ②가 *"어느 경로의 어느 계수에서 왔는가"*를 요구하므로 두 출처는 분리돼야 한다 |
| G-ii | 근거를 `summary_ko` 산문에만 싣는다 | 산문은 기계 판정 불가이고 `AC-OVERLAP-016` ②가 *"자유 산문이 아니라 경로를 담는다"*를 명시한다 |
| G-iii | 근거 필드만 만들고 페이로드 키는 후속 SPEC으로 | **그것이 정확히 `FootprintPolicy.source`가 된 경로다.** `REQ-OVERLAP-016`이 *"근거를 받는 필드를 만들고 내보내는 키를 만들지 않으면 같은 결과가 된다"*고 적은 것의 대상이 이 후보다 |
| G-iv | 페이로드 키만 만들고 판정 계층은 문자열을 그때그때 조립 | 표현 계층이 판정 근거를 만들게 되어 `AC-OVERLAP-017` ②(*"판정 계층이 한국어를 만들지 않는다"*)의 반대편 오류가 된다. 출처는 순회가 산출하고 라벨만 표현 계층이 붙인다 |

**요약 도달이 별개 지점인 이유.** `REQ-OVERLAP-017`이 적듯 **요약이 사용자가 실제로 읽는 유일한 문자열**이다. 페이로드에만 넣으면 사용자에게 보이지 않는다 — 그것은 `FootprintPolicy.source`가 죽은 방식의 한 칸 뒤 버전이다. `AC-OVERLAP-017` ①이 4값 각각에 대해 요약 문자열에 대응 라벨이 포함됨을 요구하고 ④가 4값 전부가 실제로 산출됨을 비공허성으로 확인한다.

**집행 마일스톤: M4**(필드와 키를 함께) · **M5**(요약 도달).
**달린 인수 조건:** `AC-OVERLAP-016` ①②③ (M4 배정) · `AC-OVERLAP-015` ①②③④ · `AC-OVERLAP-017` ①②③④ (M5 배정).

---

### 슬롯 H — PRESERVE 게이트의 형상

**무엇을 결정하는가.** 이월된 PRESERVE 상시 테스트를 **어디에** 두고, 보호구역을 **어떤 형태로** 봉쇄하며, **어느 BASE**를 쓰는가.

**선택.**

| 항목 | 결정 |
|---|---|
| 파일 | **신규 파일 `server/tests/test_overlap_preserve.py`.** 선례 파일을 확장하지 않는다 |
| PRESERVE diff 기준점 | **`95687a0e0eba90b325daf76efbd0ac197e69e2fc`**(PRECHK PRESERVE 기준점, 영구 불변). 본 SPEC의 BASE가 **아니다** |
| `tools.py` 보호구역 | **hunk 위치 봉쇄.** BASE `95687a0e…` 상대 범위 `(247, 251)`과 `(537, 582)`. **"삭제 0행" 규칙을 쓰지 않는다** |
| `server/safety/**` | 파일집합 봉쇄 + 삭제 행 봉쇄 — 변경 파일 정확히 2개, 한쪽 삭제 0행, 다른 쪽 삭제 ≤ 1행이며 **그 1행이 독스트링임**을 함께 단정 |

**근거 — BASE는 셋이고 섞으면 게이트가 엉뚱한 곳을 지킨다.** `CONTRACT.md` §4가 둘을 고정했고, 여기에 선례 파일이 쓰는 세 번째가 더해진다 `[코드]`·`[문서]`:

| 기준점 | 쓰이는 곳 | 보호구역 범위 |
|---|---|---|
| SONGCUE BASE `38a6e7e…` | `server/tests/test_songcue_bundle.py:65` — `_TOOLS_PROTECTED_OLD_RANGES = ((234, 238), (524, 569))` | `(234, 238)` · `(524, 569)` |
| **PRECHK BASE `95687a0e…`** | **신규 `server/tests/test_overlap_preserve.py`** | **`(247, 251)` · `(537, 582)`** |
| 본 SPEC BASE `85a4b2389003cb61b0ab72eb4aa8d6b2ff90b94a` | 스위트·회귀 기준, `AC-OVERLAP-002` ③의 `server/safety/` diff | 해당 없음 |

`research.md` §9.3이 수치로 증명했다 — PRECHK BASE에서 `tools.py`가 SONGCUE BASE보다 330행 길고 두 보호구역이 각각 **+13행** 밀렸다. **선례 상수를 복사하면 `234-238`은 dedupe 예외를 설명하는 주석 한복판을 지키고, `524-569`는 실행 루프보다 13행 앞에서 시작해 `failed = True`(BASE 582)를 보호하지 못한다.** 그것이 `AC-OVERLAP-019` ⑥의 *"신규 파일에 둔다"*가 취향이 아닌 이유다.

**근거 — "삭제 0행" 규칙은 `tools.py`에서 즉시 실패한다.** `research.md` §9.4가 파일별 삭제 행 수를 실측했고 `tools.py`가 **삭제 1행**이다 — 원문은 `-from server.orchestrator.ports import BundleGate, CommandExecutionPort, StateQueryPort`로, import 1행이 12행 블록으로 대체된 것이다. `CONTRACT.md` §4가 같은 지시를 반복한다. 따라서 hunk 위치 봉쇄를 유지한다(`AC-OVERLAP-019` ④).

**근거 — 비공허성이 선례보다 강해야 한다.** 존재하지 않는 경로는 `--stat`에 조용히 0행을 기여하므로 **오타 한 글자로 게이트가 영구 통과한다.** `AC-OVERLAP-019` ③이 10경로 목록의 **각 경로 실재**를 요구하고 **파일 7개와 디렉터리 3개**의 판정 형태가 다름을 반영할 것을 요구하며 **그 분류를 목록 자체에서 기계로 도출**하도록 못박는다(손으로 적으면 다시 틀린다 — 초안이 4/6으로 적었고 plan-audit 1회차가 P1로 잡았다). 그리고 ②가 argv 범위 인자를 `<PRECHK_BASE>..HEAD` 형태로 고정한다 — 인자 없는 `git diff`로의 *"단순화"*가 게이트를 무력화함이 실측으로 증명되어 있다(`.moai/specs/SPEC-COPILOT-PRECHK-001/progress.md:558`, 선행 SPEC 인용 `[문서]`).

**갱신이 강제되는 트립와이어 2건은 PRESERVE 위반이 아니다**(`CONTRACT.md` §3).

| 대상 | 왜 갱신인가 |
|---|---|
| `server/tests/test_songcue_bundle.py:64`의 `_TOOLS_EXPECTED_HUNK_OLD_STARTS` | 주석이 스스로 선언한다 — *"tools.py를 정당하게 고치는 후속 SPEC은 이것을 의도적으로 갱신해야 하며, 그것이 요점이다"*(`server/tests/test_songcue_bundle.py:56-59`) `[코드]`. PRECHK가 이미 한 번 갱신했다(`:60-63`). **`:65`의 보호구역 교차 단정은 계속 성립해야 한다** |
| `server/tests/test_prechk_verdicts.py`의 재타이핑 정본 3단정 | 어휘 확장이 승인 사항이므로 갱신이 집행이다. **형태를 약화시키지 않는다** — 집합 동일성(`server/tests/test_prechk_verdicts.py:26-45`) · 레지스트리 키 동일성(`server/tests/test_prechk_verdicts.py:47-54`) · 레지스트리 **순서** 동일성(`server/tests/test_prechk_verdicts.py:55-61`) 셋을 모두 유지한다 |

**PRECHK의 `progress.md`는 무변경이다.** `server/tests/test_prechk_patch.py:310-317`이 `DESCOPE: ASSUMPTION-27` 접두 행이 **정확히 1건**임을 상시 단정한다 `[코드]`. 본 SPEC의 게이트 행은 자기 `progress.md`에 쓴다.

**두 BASE의 `server/safety/**` 판정이 모순되지 않는다는 확인.** 본 SPEC이 `server/safety/**`를 무변경으로 둘 수 있는 근거는 `REQ-OVERLAP-002` — 순회가 `state` 표면만 쓰고 프로퍼티를 **0건** 읽으므로 신규 예외 지점이 0건이다(단 그 판정은 `ASSUMPTION-34`이며 M0가 닫는다). 그 위에서 `AC-OVERLAP-002` ③은 **본 SPEC BASE** 기준으로 `server/safety/`가 **빈 출력**이어야 한다고 하고, `AC-OVERLAP-019` ⑤는 **PRECHK BASE** 기준으로 변경 파일이 **정확히 2개**라고 한다. 둘은 서로 다른 기준점을 보므로 동시에 참이다 — PRECHK가 연 2파일은 PRECHK BASE 이후의 변경이고 본 SPEC은 그 위에 0건을 더한다. **이 둘을 같은 BASE로 읽는 것이 이 슬롯의 유일한 함정이며 여기 적어 둔다.**

**기각한 후보와 사유.**

| # | 후보 | 기각 사유 |
|---|---|---|
| H-i | `server/tests/test_songcue_bundle.py`를 확장한다 | 한 모듈에 두 BASE가 섞인다. `research.md` §9.3의 수치가 게이트가 엉뚱한 곳을 지키게 됨을 증명했다. `AC-OVERLAP-019` ⑥이 금지한다 |
| H-ii | 보호구역을 "삭제 0행" 규칙으로 대체한다 | `tools.py` 실측 삭제 1행이라 즉시 실패한다(`research.md` §9.4). `AC-OVERLAP-019` ④가 금지한다 |
| H-iii | PRESERVE diff를 본 SPEC BASE로 검사한다 | 착수 직후 항상 0행이라 게이트가 통째로 무력해진다. `AC-OVERLAP-019` ① |
| H-iv | 인자 없는 `git diff --stat -- <목록>` | 위반이 커밋돼 있어도 0행을 낸다 — `.moai/specs/SPEC-COPILOT-PRECHK-001/progress.md:558`이 뮤테이션 실증으로 확인했다 |
| H-v | 보호구역 ①을 넓게 `(247, 257)`로 | `CONTRACT.md` §4가 `(247, 251)`로 확정했다. 두 후보가 현재 diff에서 구별되지 않는다는 잔여는 §6의 `[미확정]`으로 남긴다 |

**집행 마일스톤: M7.**
**달린 인수 조건:** `AC-OVERLAP-019` ①~⑨ (M7 배정) · `AC-OVERLAP-002` ②③④ (M2 배정).

---

### 슬롯 I — 툴 배선의 경로 수령과 섹션 가드

**무엇을 결정하는가.** 순회가 대상 경로를 어떻게 받고, 경로 누락을 어떤 가드가 잡는가. 이 슬롯의 모든 선택은 `REQ-OVERLAP-018`의 경계 4금지(신규 REST 라우트 · 웹소켓 메시지 타입 · `execution_port` 직접 접근 · `server.bridge` 직접 import, 그리고 `server/tools/` 예외 증설) 안에서 이루어진다.

**선택 — `CONTRACT.md` §2 D-2·D-3의 재게시.**

| 축 | 결정 |
|---|---|
| 경로 수령 | **`rig_paths` 경유.** `server/prechk/footprint.py`에 `"Patch/FixtureTypes"`를 리터럴로 박지 않고 핸들러가 `rig_paths["fixture_types"]`를 넘긴다 |
| 섹션 가드 | **별도 상수를 신설**하고 `create_macro` 분기 **밖에서** 항상 검사한다. `PRECHK_RIG_SECTIONS`에 `"fixture_types"`를 추가하지 않는다 |

**근거 — 경로.** `Patch/FixtureTypes`는 이미 `DEFAULT_RIG_CONTEXT_PATHS`에 있다 — `"fixture_types": "Patch/FixtureTypes",`(`server/orchestrator/tools.py:117`) `[코드]`. 즉 **새 경로 상수가 필요 없다.** 리터럴로 박으면 4층 오버라이드 이음새를 우회한다: `server/web/app.py:83`(`rig_paths` 파라미터) → `server/web/session.py:182`·`:215` → `server/orchestrator/tools.py:508`(`build_toolset`의 `rig_paths`) · `:534`(`rig_paths = dict(rig_paths or DEFAULT_RIG_CONTEXT_PATHS)`) `[코드]`.

상반된 선례인 `FIXTURE_ROOT` 리터럴 고정(`server/prechk/inventory.py:50`)은 **폐기 경로 재주입 방지**라는 별개 사유에서 나왔고 `InventoryPolicy` 독스트링이 그것을 의도로 선언한다 — *"루트 경로와 프로퍼티 화이트리스트는 **일부러** 여기 없다"*(`server/prechk/inventory.py:206-209`) `[코드]`. `Patch/FixtureTypes`에는 그 위험이 없다(`REQ-PRECHK-002`가 금지한 것은 `Patch/Fixtures`다). 그리고 `AC-OVERLAP-005` ①이 대상 경로를 **파라미터로** 받을 것을 기계로 요구한다.

**근거 — 섹션 가드.** `PRECHK_RIG_SECTIONS = ("groups", "macros")`(`server/orchestrator/tools.py:157`)의 가드는 **`create_macro=True` 분기 안에만** 있다 `[코드]`. `"fixture_types"`를 그냥 추가하면 **같은 오버라이드 누락이 `create_macro` 값에 따라 다른 결과를 낸다**(참 → 오류, 거짓 → 조용히 통과). 상계 순회는 `create_macro`와 무관하다.

그리고 추가하면 깨지는 테스트 좌표가 확정돼 있다 — `server/tests/test_prechk_tool.py:895-905`가 누락 섹션 **집합**을 메시지로 단정하고(`assert "groups" in content and "macros" in content`) `:907`이 매크로 풀만 누락된 경우를 단정한다 `[코드]`. 2섹션이 3섹션이 되면 둘 다 깨진다.

**누락 시 메시지의 형상.** *"어느 섹션이 빠졌는지 이름으로 말하고 풀 판독 실패를 암시하지 않는다"*(D-3). 선례가 그 형태를 이미 갖는다 — `server/tests/test_prechk_tool.py:900-903`이 `"no path configured"`를 요구하고 **`"unreadable"`이 없을 것**을 단정하며 주석이 이유를 적는다: *"실패한 읽기가 아니다 — 아무것도 조회되지 않았으므로 아무것도 판독 불가라 불릴 수 없다"* `[코드]`. **이것이 결함 계열 1의 예방 형태이며 신규 가드가 그대로 계승한다.**

**기각한 후보와 사유.**

| # | 후보 | 기각 사유 |
|---|---|---|
| I-i | `server/prechk/footprint.py`에 경로를 리터럴로 | 4층 오버라이드 이음새를 우회한다. `AC-OVERLAP-005` ①이 죽는다 |
| I-ii | `PRECHK_RIG_SECTIONS`에 `"fixture_types"` 추가 | `create_macro`에 따라 다른 결과. `server/tests/test_prechk_tool.py:895-905`·`:907`이 깨져 `AC-OVERLAP-021` ②가 죽는다 |
| I-iii | 기존 가드를 `create_macro` 분기 밖으로 끌어낸다 | 매크로 축의 계약을 바꾼다 — `create_macro=False`에서 그룹·매크로 경로 누락이 새로 오류가 되고, 같은 두 테스트가 깨진다 |
| I-iv | 가드 없이 경로 누락을 순회 실패로 처리 | 설정 결함이 운영 조건과 섞인다. `AC-OVERLAP-006` ①이 죽고 결함 계열 1을 재생산한다 |
| I-v | 신규 경로 키를 `DEFAULT_RIG_CONTEXT_PATHS`에 추가 | 11번째 키가 되어 `server/tests/test_tools.py:511-522`의 정확 10키 단정이 깨진다. **폭 상계 축은 신규 경로 키 0건으로 성립한다** — `fixture_types`가 이미 있다 |

**집행 마일스톤: M6.**
**달린 인수 조건:** `AC-OVERLAP-018` ①~⑤ (M6 배정) · `AC-OVERLAP-005` ① · `AC-OVERLAP-006` ① (M2 배정) · `AC-OVERLAP-021` ② (M8 배정).

---

## §3. 거부한 설계 — 전수 기각 기록

**목적은 후속 SPEC이 무엇을 이미 시도했는지 아는 것이다.** `.moai/specs/SPEC-COPILOT-PRECHK-001/progress.md:406`이 같은 이유를 적었다 — *"후보 0건이 아니라 후보 12건 전건 부정이다. 이 구별이 중요하다 — 후속 SPEC이 다른 쇼파일에서 재측정할 때 무엇을 이미 시도했는지 알 수 있다"* `[문서]`.

### §3.1 배치 후보 4종 — `research.md` §6의 전수 판정

| 후보 | 판정 | 기각 사유 | **깨지는 테스트 · 좌표** |
|---|---|---|---|
| **A-1** `server/prechk/inventory.py` 확장 | **기각. 출구 없음** | 순회 경로를 `Inventory.state_paths`에 기록하면 픽스처 루트 경계가 깨진다 — `Patch/FixtureTypes`는 그 하위가 아니다. 기록을 생략하면 `generated_queries()`의 *"이 읽기가 생성한 모든 요청"* 계약이 거짓이 된다. 그리고 `InventoryPolicy` 독스트링이 주입 가능화를 **의도로 금지**한다 | `server/tests/test_prechk_inventory.py:693-699`(`test_every_queried_path_stays_under_the_fixture_root`) 즉시 실패. 독스트링은 `server/prechk/inventory.py:206-209` |
| **A-2** `server/prechk/query.py` 확장 | **기각. 기존 테스트 0건 실패, 모듈 계약 위반** | 그 모듈은 `PropertyQueryPort`만 import하고(`server/prechk/query.py:19`) 자기를 *"프로퍼티 읽기"*로 정의한다. 3단 순회는 프로퍼티를 **0건** 읽고 `query_state`만 쓴다 | 깨지는 테스트 0건 — **그래서 더 위험하다.** `AC-OVERLAP-002` ①이 순회 모듈의 포트 사용을 `query_state` 하나로 고정해 이 후보를 기계로 배제한다 |
| **A-3** `server/prechk/` **신규 모듈** | **채택(D-1)** | 자기 조회 기록을 별도 자료구조에 담으면 `Inventory.queried_paths`에 섞이지 않는다 | 깨지는 테스트 **0건** |
| **A-4** `server/orchestrator/tools.py` 핸들러 내부 | **기각. 위반 0건이나 검증 가능성 손실** | `_free_macro_slot`이 `build_toolset` 클로저라 import 불가하고 `_dispatch` 경유로만 테스트되는 **선례가 이미 있다**. `bound_inconclusive`가 합성 리그로만 도달 가능한 본 SPEC에서 그 손실은 치명적이다 | `AC-OVERLAP-005` ③(*"순회 모듈을 단독으로 import할 수 있다"*)이 이 배치를 배제하는 기계 판정이다. ④가 툴을 거치지 않는 직접 호출 테스트를 요구한다 |

### §3.2 다른 지점에서 기각한 설계 — 식별자는 `X-n`이다

| # | 후보 | 기각 사유 | **깨지는 테스트 · 좌표** |
|---|---|---|---|
| X-1 | `_range_overlaps`의 정렬 재사용 | `widths={}`이면 `intervals`가 비어 정렬 자체가 일어나지 않는다 | 형상 자체로 불가 — `server/prechk/patch.py:330-339` |
| X-2 | 간격 대상에 `type_mode_ok`를 요구 | 상계 논증은 모드를 몰라도 성립한다(§1.1). 요구하면 논증의 오해다 | `AC-OVERLAP-010` ③④ |
| X-3 | 중복 주소를 간격 집합에 그대로 넣어 간격 0을 낸다 | 주소 중복 축과 이중 계상 | `AC-OVERLAP-010` ①②. 대상은 `_address_duplicates`의 **키 집합**이다(`server/prechk/patch.py:268-271`) |
| X-4 | 술어를 `간격 ≤ 상계`로 | off-by-one. 닫힌 끝 구간에서 `간격 == 상계`는 깨끗하다 | `AC-OVERLAP-008` ②. 실측 리그로는 안 잡힌다 — §4의 `bound_gap_equals`만이 잡는다 |
| X-5 | 미확정을 `collisions.range_overlaps`에 넣는다 | 그 목록의 슬롯은 `collision` verdict를 받아 사용자가 *"충돌"*을 읽는다. 상계 논증은 겹침 있음을 증명하지 못한다 | `AC-OVERLAP-011` ①②③. 라벨은 `server/prechk/report.py:67` |
| X-6 | 정확폭 축과 상계 축을 한 축으로 흡수 | 두 축의 필터 술어가 다르다(`type_mode_ok`). 그리고 기존 `FootprintPolicy` 경로가 깨진다 | `AC-OVERLAP-013` ④(착수 시점 정확폭 테스트 전건 통과) · `AC-OVERLAP-010` ④ |
| X-7 | `truncated` 플래그만 신뢰 | 3단은 `truncated=true`인데 `childCount`가 참값이다 | `AC-OVERLAP-004` ①. 근거는 `.moai/specs/SPEC-COPILOT-PRECHK-001/progress.md:408` |
| X-8 | 상계 31 · 폭 29 · 간격 42를 상수로 | 셋 다 이 쇼파일 룰북 레시피의 산물이다 — `addr = addr + 42`를 9회 돌린 결과가 실측 유니버스 1의 슬롯 2~10 주소와 정확히 일치한다(`server/rulebook/assets/v2.4.2/30_plugin_patterns.md:45-50`) | `AC-OVERLAP-001` ①② |
| X-9 | `PRECHK_RIG_SECTIONS`에 `"fixture_types"` 추가 | `create_macro`에 따라 다른 결과 | `server/tests/test_prechk_tool.py:895-905`·`:907` |
| X-10 | `DEFAULT_RIG_CONTEXT_PATHS`에 11번째 키 추가 | 폭 상계 축은 신규 경로 키 0건으로 성립한다. 꼬리 초과 축만이 이 계약 변경을 요구하며 그 축은 범위 밖이다 | `server/tests/test_tools.py:511-522` 정확 10키 |
| X-11 | 어휘 레지스트리에 중간 삽입 | 두 리스트의 어긋남을 단정 하나에만 맡긴다 | `server/tests/test_prechk_verdicts.py:55-61` 순서 있는 리스트 동일성 |
| X-12 | 가드 튜플에 항목만 추가 | 무증상 단계를 남겨 다음 축이 같은 함정을 만난다 | `AC-OVERLAP-014` ⑦. 튜플은 `server/prechk/report.py:111-117` |
| X-13 | `COLLISION_KIND` 또는 `FIXTURE_VERDICT`에 값 추가 | §2 슬롯 E의 거짓 문자열. 그리고 어휘 파생 단정 3건이 무변경으로 통과해야 한다 | `AC-OVERLAP-014` ③. `server/tests/test_prechk_verdicts.py:26-45` |
| X-14 | 꼬리 초과 판정 축을 켠다 | 용량 `B`에 저장소 근거 0건이고, 현재 코드는 유니버스를 넘는 점유를 클러스터에 넣지 못하며, 런타임 조회는 11번째 경로 키를 요구한다 | `spec.md` §D가 범위 밖으로 뒀다. R-10과 같은 좌표 |
| X-15 | 선례 테스트 파일(`test_songcue_bundle.py`) 확장 | 한 모듈에 두 BASE. 선례 값을 복사하면 주석 한복판과 루프 앞 13행을 지킨다(`research.md` §9.3) | `AC-OVERLAP-019` ⑥ |
| X-16 | `tools.py`에 "삭제 0행" 규칙 | 실측 삭제 1행 | `AC-OVERLAP-019` ④ |
| X-17 | 근거 필드만 만들고 페이로드 키를 생략 | `FootprintPolicy.source`(`server/prechk/patch.py:170`)가 소비자 0건으로 죽은 경로의 재생산 | `AC-OVERLAP-016` ③ |
| X-18 | 신규 최상위 키를 얹고 정확 키집합 단정 생략 | 아무것도 안 깨지지만 아무도 안 지킨다 | `AC-OVERLAP-016` ④ |
| X-19 | 절단 계수 비교 3구현을 수렴시킨다 | 세 정책이 서로 다르고 단순 통합이 *"zero fixtures는 유효한 리그"*와 충돌한다(D-8) | `server/prechk/inventory.py:389` · `server/prechk/macro.py:249-251` · `server/orchestrator/tools.py:1296-1302` |
| X-20 | 순회 실패를 예외로 전파 | 리포트의 나머지를 잃는다. 41개 디스패치가 깨진다 | `AC-OVERLAP-007` ① · `AC-OVERLAP-021` ② |
| X-21 | `ASSUMPTION-27`을 되살려 조인을 복원 | 응답기 확장(`console/lua/**` PRESERVE 위반)이나 다른 쇼파일이 필요하다. 상계 논증은 조인 없이 성립하는 더 약한 명제다 | `spec.md` §D. `DESCOPE: ASSUMPTION-27` 1건 보존은 `server/tests/test_prechk_patch.py:310-317` |

---

## §4. 합성 리그 카탈로그

**`bound_inconclusive` 분기는 현재 쇼파일에서 발동 입력이 0건이다.** `research.md` §3.2가 산술로 닫았다 — 17 인접쌍 전부가 `간격 ≥ 31`이라 미확정 쌍이 **0건**이다. 따라서 그 분기를 덮을 수 있는 것은 **합성 인메모리 리그뿐**이며, 미확정 분기에 라이브 증거를 요구하는 인수 조건은 원리적으로 충족 불가능하다(`acceptance.md` 서두가 그것을 명시한다).

**합성 리그를 라이브 미러로 묶지 않는다.** 선례가 둘이다 `[코드]`·`[문서]`:

- 기존 프로닝된 폭이 *"INJECTED, never derived"*다 — `server/tests/test_prechk_inventory.py:369-371`의 주석 원문: *"The value 29 is the measured `DMXChannels` child count of mode 1; it is INJECTED, never derived."*
- **결정 원문**: *"합성 픽스처이며 라이브 미러가 아니다. 확장하지 않는다. 인메모리 픽스처를 현장 쇼파일에 묶으면 리그가 바뀔 때마다 테스트가 깨지고 결정성이 사라진다"*(`.moai/specs/SPEC-COPILOT-PRECHK-001/progress.md:419`).

**경계 3형은 같은 리그 형상에서 간격만 바꿔 돌린다** — `AC-OVERLAP-008` ④가 그것을 요구한다. 폭 집합 `{17, 23}`(상계 **23**), 유니버스 1에 픽스처 2개, 첫 주소 `1.001` 고정, 둘째 주소만 이동.

| # | 리그 이름 | 주소·폭 구성 | 덮는 인수 조건 | **죽이는 뮤테이션** |
|---|---|---|---|---|
| 1 | `bound_widths_injected` | 모드 폭 `{17, 23}` 주입 → 상계가 **23으로 산출**된다 | `AC-OVERLAP-001` ② | M-9 |
| 2 | **`bound_gap_below`** | `{17, 23}` · `1.001` · `1.023` → **간격 22 = 상계 − 1** | `AC-OVERLAP-008` ①④ · `AC-OVERLAP-011` ⑤ | **M-2**(역방향) · M-5 |
| 3 | **`bound_gap_equals`** | `{17, 23}` · `1.001` · `1.024` → **간격 23 = 상계** | `AC-OVERLAP-008` ②④ | **M-2**(off-by-one 정면) |
| 4 | `bound_gap_above` | `{17, 23}` · `1.001` · `1.025` → 간격 24 = 상계 + 1 | `AC-OVERLAP-008` ③④ | M-2 |
| 5 | `tier1_short` | 1단 `childCount = 5`, 자식 3 | `AC-OVERLAP-003` ① · `AC-OVERLAP-004` ② | M-3 · M-8 |
| 6 | `tier2_short` | 2단 `childCount = 4`, 자식 2 | `AC-OVERLAP-003` ② | M-3 |
| 7 | `tier3_truncated_countable` | 3단 `truncated = true` · `childCount = 31` · `children = []` | `AC-OVERLAP-004` ①③④ | **M-8** |
| 8 | `budget_two` | 예산 2, 타입 1 + 모드 2 이상 | `AC-OVERLAP-003` ③ · `AC-OVERLAP-020` ⑤ | M-3 · M-10 |
| 9 | `walk_raises` | 2단 조회가 예외를 던진다 | `AC-OVERLAP-003` ④ | M-3 · M-11 |
| 10 | **`subset_bound_trap`** | 모드 폭 `{29, 29, 29, 31}` · 2단 예산 **3** · 최소 간격 **30**. `research.md` §4.1 시나리오의 코드 이식 | `AC-OVERLAP-003` ⑤⑥ | **M-3** — 부분집합 상계 29로 `bound_proves_clear` 거짓 양성 |
| 11 | `two_universe_adjacent` | `1.500` · `2.001` — 인접해 보이나 다른 유니버스 | `AC-OVERLAP-009` ①③ | **M-1**(착수 시점 생존) |
| 12 | `two_universe_counts` | 유니버스 1에 10, 유니버스 2에 9 → 간격 총수 **17** | `AC-OVERLAP-009` ②④ | **M-1** |
| 13 | `shared_start_point` | 서로 다른 슬롯 2개가 `1.001`, 그리고 `1.043` | `AC-OVERLAP-010` ①② | M-12 |
| 14 | `type_mode_unresolved_pair` | 타입·모드 판독 실패 픽스처 2개 + 유효 주소 | `AC-OVERLAP-010` ③④ | M-13 |
| 15 | `out_of_range_addresses` | `0.0` · `1.0` · `0.1` + 유효 `1.001` · `2.401` | `AC-OVERLAP-012` ①②③④ | M-14 |
| 16 | `exact_and_bound_mixed` | 슬롯 1·2는 정확폭 주입, 슬롯 3·4는 폭 없음 | `AC-OVERLAP-013` ①②③⑤ | M-15 |
| 17 | `walk_fails_rest_survives` | 순회 전면 실패 + **심은 주소 중복 1건** | `AC-OVERLAP-007` ①②③④ | M-11 · M-16 |
| 18 | `path_absent_vs_unreachable` | 대상 경로 부재 / 콘솔 무응답 — **같은 예외 타입**으로 도착 | `AC-OVERLAP-006` ①②③④ | M-17 |
| 19 | `four_basis_values` | 4값 각각을 산출하는 리그 4형 | `AC-OVERLAP-017` ①④ · `AC-OVERLAP-021` ① | M-18 |

**합성 리그 19건.** 리그 2·3·4는 **같은 형상에서 간격만 바뀐다** — 그것이 `AC-OVERLAP-008` ④가 요구하는 대조다. 리그 17의 *"심은 주소 중복"*은 비공허성이다: 중복이 0건이면 `AC-OVERLAP-007` ②가 공허하다.

**리그 이름 규약.** 이름은 `server/tests/test_prechk_footprint.py`의 헬퍼 함수명이며 `server/prechk/**`의 문자열 상수가 아니다 — `_FORBIDDEN_PROPERTY_NAMES` 스캔의 대상 범위는 `server/prechk/`이고 `server/tests/`가 아니다(`AC-OVERLAP-001` ①). 그럼에도 이름에 `Universe` · `Address` · `Channels` · `Footprint` · `Break` · `No`를 대문자 정확형으로 쓰지 않는다.

---

## §5. 뮤테이션 제안

각 항목은 **주입 / 죽어야 하는 인수 조건 / 마일스톤**을 갖는다. **주입 지점과 판정 지점이 다른 행은 `주입 Mx · 판정 My`로 적는다** — plan-audit 1회차가 이 관례 불일치를 P2로 지적했고 M-30 · M-31 · M-35를 그 형태로 고쳤다. 특히 M-35는 초안이 `M0`로 적었으나 M0는 `cycle_type=none`(코드 변경 0)이므로 `server/safety/**`에 hunk를 만드는 뮤테이션을 소유할 수 없다. `CONTRACT.md` §6 규율 3의 집행이다 — *"신규 테스트는 수정 전 코드에서 실패함을 역방향으로 확인하고, 통과하는 테스트는 회귀 테스트가 아니라고 코드에 명시한다."*

| # | 주입할 결함 | **죽어야 하는 인수 조건** | 마일스톤 |
|---|---|---|---|
| **M-1** | **구간 겹침 축에서 유니버스 키잉을 제거해 단일 주소 공간으로 붕괴시킨다** | `AC-OVERLAP-009` ①②③④ | M3 |
| **M-2** | 술어를 `간격 ≤ 상계`로 바꾼다(off-by-one) | `AC-OVERLAP-008` ②④ | M3 |
| **M-3** | 완전성 판정을 `max` **뒤로** 옮긴다 — 부분 결과를 `max`에 넣고 사후에 플래그로 무효화 | `AC-OVERLAP-003` ⑤⑥ | M2 |
| **M-4** | **어휘 가드를 하드코딩 튜플로 되돌린 뒤 신규 축을 등재하지 않는다** — D-6이 루프를 레지스트리 순회로 바꾸므로 *등재 누락* 자체는 주입 불가가 된다. 유증상 형태는 **구조를 되돌리는 것**이다 | `AC-OVERLAP-014` ⑥⑦ | M1 |
| **M-5** | 미확정을 `collisions.range_overlaps` 목록에 넣는다 | `AC-OVERLAP-011` ①③⑤ | M3 |
| M-6 | 미확정을 목록에는 안 넣고 `collision_total`에만 더한다 | `AC-OVERLAP-011` ②⑤ | M3 |
| M-7 | `bound_proves_clear`를 관측 범위 한정 없이 무한정으로 발화 | `AC-OVERLAP-015` ①② | M5 |
| M-8 | 1·2단과 3단 절단 술어를 하나로 뭉갠다 | `AC-OVERLAP-004` ①③④ | M2 |
| M-9 | 상계·폭·간격을 코드 상수로 박는다(31 · 29 · 42) | `AC-OVERLAP-001` ①② | M2 |
| M-10 | 예산을 제거하고 무제한 순회 | `AC-OVERLAP-005` ① · `AC-OVERLAP-021` ③ | M2 · M8 |
| M-11 | 순회 예외를 포착하지 않는다 | `AC-OVERLAP-007` ① · `AC-OVERLAP-021` ② | M4 · M8 |
| M-12 | 중복 주소를 간격 집합에 두 번 넣어 간격 0을 만든다 | `AC-OVERLAP-010` ①② | M3 |
| M-13 | 간격 대상에 `type_mode_ok`를 요구한다 | `AC-OVERLAP-010` ③④ | M3 |
| M-14 | 주소 유효 범위 검증을 생략한다 | `AC-OVERLAP-012` ①② | M3 |
| M-15 | 정확폭이 있는 슬롯에도 상계를 우선 적용한다 | `AC-OVERLAP-013` ①④ | M4 |
| M-16 | 순회 실패를 `bound_proves_clear`로 낸다 | `AC-OVERLAP-007` ③④ | M4 |
| M-17 | 경로 부재와 콘솔 무응답을 한 사유 코드로 낸다 | `AC-OVERLAP-006` ①④ | M2 |
| M-18 | 4값 중 하나를 산출 경로 없이 둔다(죽은 어휘) | `AC-OVERLAP-017` ④ · `AC-OVERLAP-021` ① | M5 · M8 |
| M-19 | 신규 최상위 키를 얹고 정확 키집합 단정을 만들지 않는다 | `AC-OVERLAP-016` ④ | M4 |
| M-20 | 근거 필드만 만들고 페이로드 키를 만들지 않는다 | `AC-OVERLAP-016` ③ | M4 |
| M-21 | 레지스트리 신규 축을 맨 끝이 아니라 중간에 삽입한다 | `AC-OVERLAP-014` ④ | M1 |
| M-22 | 라벨표 이름을 `_LABELS`로 끝내지 않는다 | `AC-OVERLAP-014` ⑤ | M1 |
| M-23 | 어휘 코드를 표현 계층의 라벨표 **밖에서** 리터럴로 재타이핑한다 | `AC-OVERLAP-014` ⑧ | M1 |
| M-24 | `COLLISION_KIND` 또는 `FIXTURE_VERDICT`를 함께 고친다 | `AC-OVERLAP-014` ③ | M1 |
| M-25 | 신규 어휘에 `proven` · `verified` · `all_clear` · `_lit` 계열 이름을 쓴다 | `AC-OVERLAP-014` ⑨ | M1 |
| M-26 | 순회에서 `query_property`를 호출한다 | `AC-OVERLAP-002` ① | M2 |
| M-27 | 3단에서 `children` 목록을 읽어 폭을 센다 | `AC-OVERLAP-001` ④ | M2 |
| M-28 | 순회 모듈이 `server.orchestrator.tools`를 import한다 | `AC-OVERLAP-005` ②③ | M2 |
| M-29 | `Patch/FixtureTypes`를 `server/prechk/`에 리터럴로 박는다 | `AC-OVERLAP-005` ① | M2 · M6 |
| M-30 | 순회 모듈에 `"Footprint"` · `"Channels"` · `"Universe"`를 문자열 리터럴로 쓴다 | `AC-OVERLAP-021` ②⑤ | 주입 M2 · 판정 M8 |
| M-31 | `PRECHK_RIG_SECTIONS`에 `"fixture_types"`를 추가해 신규 가드를 대신한다 | `AC-OVERLAP-021` ② | 주입 M6 · 판정 M8 |
| M-32 | PRESERVE diff를 **본 SPEC의 BASE**로 검사한다 | `AC-OVERLAP-019` ①② | M7 |
| M-33 | `tools.py` 보호구역 hunk 봉쇄를 "삭제 0행" 규칙으로 대체한다 | `AC-OVERLAP-019` ④ | M7 |
| M-34 | PRESERVE 10경로 목록에 오타를 한 글자 넣는다 | `AC-OVERLAP-019` ③ | M7 |
| M-35 | `server/safety/**`에 hunk를 1건 만든다 / PRECHK `progress.md`의 `DESCOPE:` 행을 편집한다 | `AC-OVERLAP-002` ③④ · `AC-OVERLAP-019` ⑧ | 주입 M2 · 판정 M7 |

**제안 뮤테이션은 총 35개다.**

### §5.1 M-1 — 착수 시점에 이미 살아 있는 구멍

**이 뮤테이션은 지금 주입하면 스위트가 통과한다.** `research.md` §5.5가 확정했다 `[코드]`:

- `_range_overlaps`를 **두 유니버스로 밟는 테스트가 0건**이다.
- GO 분기 유일 테스트가 `overlap.universe == 1` 하나만 단정한다(`server/tests/test_prechk_patch.py:223`)이고 `range_overlap_go()`는 유니버스 1 전용이다.
- 유니버스 서로소성을 고정하는 테스트는 **주소 중복 축의 1건뿐**이다(`server/tests/test_prechk_patch.py:184-189`).

**결과: `patch.py`의 `intervals` dict를 단일 리스트로 붕괴시켜도 스위트가 통과한다.** 서로소성이 코드에만 있고 계약으로 고정돼 있지 않다. `AC-OVERLAP-009` ③이 그 사실을 명시로 담고 ④가 대응 테스트를 **정확폭 축과 상계 축 양쪽에** 요구한다 — 착수 시점에는 주소 중복 축만 덮여 있었다. **본 SPEC이 그 구멍을 닫는다.**

### §5.2 M-4 — 수정 전 무증상이며 D-6이 주입 지점을 없앤다

**M-4는 수정 전 코드에서 아무 테스트도 실패시키지 않는다.** `research.md` §7.2와 `server/prechk/report.py:111-119`의 형상이 그 이유다: 신규 축을 하드코딩 5-튜플에 넣지 않아도 (i) import가 성공하고 (ii) 라벨 드리프트는 `server/tests/test_prechk_report.py:273-278`이 `CLOSED_VOCABULARIES`를 순회하므로 여전히 잡히므로 (iii) **실패 0건**이다.

**D-6의 구조 변경이 이 뮤테이션을 어떻게 잡는가 — 죽이는 것이 아니라 주입 불가로 만든다.** 가드 루프를 `CLOSED_VOCABULARIES.items()` 순회로 바꾸면 **등재할 튜플이 존재하지 않으므로 *"빠뜨린다"*라는 조작 자체가 표현 불가능해진다.** 축을 레지스트리에 추가하는 순간 가드가 자동으로 그것을 본다.

그 상태를 확인하는 것이 `AC-OVERLAP-014` ⑦이다 — **신규 축을 등재하지 않고도** 라벨표에서 한 항목을 제거하면 import 시점 예외가 발생함을 확인한다. 그리고 **뮤테이션은 사라지지 않고 형태를 바꾼다**: 순회를 다시 하드코딩 튜플로 되돌리는 조작이 새 주입 지점이며, 그때 `AC-OVERLAP-014` ⑦이 죽는다. **즉 구조 변경은 무증상 단계를 유증상 단계로 옮긴 것이다.**

⑥은 그 사이의 하한을 지킨다 — 라벨표에서 신규 축의 한 항목을 제거한 상태로 모듈을 import하면 예외가 발생해야 한다. 예외가 없으면 가드에 등재되지 않은 것이다.

---

## §6. 결정 등록부

**열린 결정은 0건이다.** 문자 식별자 `D-1`~`D-8`은 `CONTRACT.md` §2의 것을 **왜곡 없이 재게시**한 것이며 본 문서가 결론을 바꾸지 않는다. `D-9`~`D-16`은 위 설계 과정에서 닫은 결정이다.

### §6.1 `CONTRACT.md` §2 재게시 — 재논의 금지

| 결정 | 확정 내용 | 반영 위치 |
|---|---|---|
| **D-1** | 순회 모듈 배치 = `server/prechk/` **신규 모듈**. 파일명 `server/prechk/footprint.py`, 대응 테스트 `server/tests/test_prechk_footprint.py`. 후보 4종 중 경계 위반 0건은 이것뿐. `server.orchestrator.tools`를 import하지 않고 **경로·예산 상한을 인자로 받는 순수 함수**. 모듈 안에서 `"Footprint"` · `"Channels"` · `"ChannelCount"` · `"Universe"` · `"Address"` · `"No"` · `"Break"`를 문자열 리터럴로 쓰지 않는다 | §2 슬롯 A · §3.1 |
| **D-2** | 경로 수령 = `rig_paths` 경유. `"Patch/FixtureTypes"`를 리터럴로 박지 않는다 | §2 슬롯 I |
| **D-3** | 섹션 가드 = **별도 상수 신설**, `create_macro` 분기 **밖에서** 항상 검사. `PRECHK_RIG_SECTIONS`에 추가하지 않는다. 누락 메시지는 섹션 이름을 말하고 **풀 판독 실패를 암시하지 않는다** | §2 슬롯 I |
| **D-4** | `overlap_basis` 부착 = **신규 최상위 키 · 리그 전역 스칼라**. 정직성 제약 2건(최약 등급 · kind당 1행). `AC-OVERLAP-016` ④가 정확 키집합 단정 신설을 요구한다 | §2 슬롯 F |
| **D-5** | 어휘 = 신규 축 1개 + 기존 축 값 1개. 라벨표 이름 **`OVERLAP_BASIS_LABELS`**. 코드값 생산자 상수는 `server/prechk/patch.py`의 `validate(...)` 상수 블록. 레지스트리·정본 리스트 **맨 끝 append** | §2 슬롯 E |
| **D-6** | 가드 루프 = **`CLOSED_VOCABULARIES` 순회로 바꾼다.** 튜플에 항목을 추가하는 것으로 끝내지 않는다 | §2 슬롯 E · §5.2 |
| **D-7** | 재사용 = `_address_duplicates`의 그룹핑. `_range_overlaps`는 **재사용 불가**. `type_mode_ok`를 요구하지 않는 쪽이 상계 논증에 맞는 술어다. 인접차·최소값은 신규 | §2 슬롯 D |
| **D-8** | 절단 계수 비교 헬퍼 = **수렴시키지 않는다.** 4번째 사본을 만들고 순회는 자기 정책을 갖는다. 수렴은 별도 리팩터 SPEC의 일 | §2 슬롯 B |

### §6.2 본 설계가 닫은 결정 8건

| 결정 | 확정 내용 | 근거 | 반영 위치 |
|---|---|---|---|
| **D-9** | **순회의 반환은 `(완전성, 폭 집합)`이다.** `max`는 완전성 참 분기 안에서만 계산된다. 불완전하면 상계라는 값이 존재하지 않는다 | 부분 결과를 `max`에 넣으면 표기와 판정이 서로 다른 대상에 붙어 판정이 먼저 오염된다(`research.md` §4.1) | §2 슬롯 A |
| **D-10** | **예산 소진은 국소 표기가 아니라 전역 무효다.** `drill_into`의 `capped` 형상을 복사하지 않는다 | 선례에서는 표기 대상과 판정 대상이 같고 여기서는 다르다(`server/orchestrator/tools.py:389-399` vs 슬롯 C) | §2 슬롯 C |
| **D-11** | **불완전·실패는 예외가 아니라 정상 페이로드의 구조화된 부류다** | PRECHK `.moai/specs/SPEC-COPILOT-PRECHK-001/design.md:143`의 공통 처리 원칙 계승. `REQ-OVERLAP-007` · `AC-OVERLAP-021` ② | §2 슬롯 A |
| **D-12** | **`overlap_basis` 내부는 7키다** — `basis` · `bound` · `bound_source` · `mode_widths` · `exact_width_slots` · `bound_slots` · `observation_note`. 이 집합에 **정확 키집합 단정을 새로 만든다** | 잠긴 블록 6개에 자리가 없고 최상위만 무충돌(`research.md` §8.1). 새 단정이 없으면 커버 침식(§8.2) | §2 슬롯 F |
| **D-13** | **리그 전역 스칼라의 등급 순서는 `not_performed` ≺ `bound_inconclusive` ≺ `bound_proves_clear` ≺ `exact_widths`이며 스칼라는 수행된 비교의 최약 등급이다. 비교가 0건이면 `not_performed`다** | D-4의 정직성 제약 1을 §1.5의 주장 강도로 정렬한 것. `AC-OVERLAP-003` ① · `AC-OVERLAP-007` ③ | §2 슬롯 F |
| **D-14** | **슬롯별 근거는 `fixtures[]` 행이 아니라 `overlap_basis` 내부의 두 슬롯 목록이 나른다** | `fixtures[]`가 정확 10키로 잠겨 있다(`server/tests/test_prechk_patch.py:453-464`). `AC-OVERLAP-013` ③을 잠긴 자리 밖에서 충족한다 | §2 슬롯 F.3 |
| **D-15** | **근거 필드와 페이로드 키를 같은 마일스톤에서 함께 만든다.** 기존 `FootprintPolicy.source`를 재사용하지 않는다 | 그 필드는 주입된 정확폭의 출처이며 상계는 런타임 파생이다. 소비자 0건 선례의 재생산을 막는다(`AC-OVERLAP-016` ③) | §2 슬롯 G |
| **D-16** | **PRESERVE 상시 테스트는 신규 파일 `server/tests/test_overlap_preserve.py`이고 기준점은 PRECHK BASE `95687a0e…`다. BASE 셋을 섞지 않는다** | 선례 상수 복사 시 주석 한복판과 루프 앞 13행을 지킨다는 수치 증명(`research.md` §9.3). `AC-OVERLAP-019` ⑥ | §2 슬롯 H |

### §6.3 상속된 스키마 드리프트 — 결정은 "정정하지 않는다"

| 드리프트 | 결정 |
|---|---|
| `PatchEvaluation.to_dict()`의 최상위 4키(`verdict_counts` · `read_failure_counts` · `scope_qualified` · `scope_note`)가 PRECHK 정본 7키에 없다 | **명시하되 정정하지 않는다.** `spec.md` §D가 범위 밖으로 뒀다 |
| 툴 페이로드가 `macro`에 `executed`를 7번째 키로 주입해(`server/orchestrator/tools.py:1491`) 정본 6키가 이미 거짓이다 | **명시하되 정정하지 않는다.** 정정은 툴 층 스키마 계약을 별도로 정의해야 하는 작업이다 |

### §6.4 열린 결정이 아닌 것 — `[미확정]` 6건과 갈리는 측정

**아래는 결정의 빈칸이 아니라 관측이 열어 둔 외부 접점이다.** 각 항목에 **무엇을 측정·조회하면 갈리는지**를 병기한다. 본 SPEC은 라이브 세션 0회이므로 어느 것도 본 문서의 관측으로 닫히지 않는다.

| # | `[미확정]` | 무엇을 측정·조회하면 갈리는가 | 갈리면 무엇이 바뀌는가 |
|---|---|---|---|
| 1 | `ASSUMPTION-34` — `state` 표면만으로 3단 순회가 도달하는가 | **M0의 인메모리 프로토타입 1개.** `DMXChannels`를 `StateQueryPort.query_state`만으로 읽는다. `prop` 호출이 한 번이라도 필요하면 PRECHK 예외를 재사용해야 한다. 라이브 불필요 | 부정이면 `spec.md` §C의 PRESERVE 서술을 개정하고 슬롯 H의 `server/safety/**` 봉쇄 형태가 바뀐다 |
| 2 | `ASSUMPTION-35` — `Patch/FixtureTypes`의 `childCount`(타입 수 `T`) | `state Patch/FixtureTypes` **1회**. `node.childCount`와 `len(children)`을 **함께** 읽는다 | 예산 상한의 정확한 값. 보수적으로 잡고 소진 시 `not_performed`를 내면 `T`를 몰라도 안전하다(`AC-OVERLAP-020` ⑤) |
| 3 | `ASSUMPTION-32` — `DMXChannels` 자식 = DMX 슬롯인가 | 자식 **이름**을 확보한다 — 열거가 절단되므로 `/<n>` 개별 조회 또는 예산 조정. 16비트 어트리뷰트가 2슬롯을 쓰면 `childCount < 실제 슬롯 수` | 거짓이면 상계가 **과소평가**되어 `bound_proves_clear`가 거짓이 된다. 본 SPEC은 셋 중 하나라도 거짓이면 그 값을 내지 않는 형상으로 출하한다(`AC-OVERLAP-020` ④) |
| 4 | `ASSUMPTION-31` — 연속 블록 전제 | **브레이크 2개 이상인 픽스처타입을 패치한 쇼파일**에서 `Patch` 값과 `DMXChannels` `childCount`를 비교한다. 현 쇼파일은 픽스처타입 1종뿐이라 실험이 원리적으로 불가능하다 | 거짓이면 `start + width - 1`이 첫 블록을 과대평가하고 둘째 블록을 완전히 놓친다 — 상계가 상계가 아니다 |
| 5 | `ASSUMPTION-33` — 유니버스 용량 `B`. 판정이 갈리는 창은 `B ∈ [437, 466]` 30값 | `DmxAddresses`의 `childCount`가 **512의 배수인가**를 조회하면 간접적으로 갈린다. 직접 경계 실험은 상계 폭 픽스처를 주소 490 근처에 패치 시도하는 **쓰기**이므로 본 SPEC 범위 밖 | 꼬리 초과 판정 축 하나에만 걸리며 그 축은 `spec.md` §D가 범위 밖으로 뒀다. `B ≥ 467`이면 512를 몰라도 증명된다 |
| 6 | `tools.py` 보호구역 ①의 폭 — 좁게 `(247, 251)` vs 넓게 `(247, 257)`. **현재 diff에서 둘 다 교차 0건이라 구별되지 않는다** | `_is_programmer_state` **본문만** 바꾸는 뮤테이션을 넣고 두 범위로 각각 게이트를 돌린다. 좁은 범위는 통과시키고 넓은 범위는 적발한다 | `CONTRACT.md` §4가 `(247, 251)`로 확정했으므로 **결정은 닫혀 있고** 잔여는 그 선택의 강도뿐이다. 넓은 쪽이 옳다고 판명되면 후속 SPEC이 범위를 넓힌다 |

**M0 이전에 M1에 착수하지 않는다**(`CONTRACT.md` §5) — `ASSUMPTION-34`가 부정이면 PRESERVE 서술이 바뀌고 그것이 슬롯 H·I의 형상을 바꾼다.

---

**열린 설계 슬롯 0건 · 열린 결정 0건 · clarification 마커 0건 · 본 문서 자기 관측 `[실측]` 0건.**
