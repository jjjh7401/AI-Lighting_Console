# SPEC-COPILOT-OVERLAP-001 — 진행 기록 (progress)

> **인용 규율.** 본 SPEC의 정본(`spec.md` · `acceptance.md`)은 **줄번호로 인용하지 않고** 안정 토큰만 쓴다. `파일:줄`은 **코드 · 룰북 · 응답기 프로토콜 · 타 SPEC 아티팩트**에만 쓴다. 요구·인수 토큰은 슬러그 포함 완전형만 쓴다(축약형 **0건**). 근거 등급은 `[코드]` · `[문서]` · `[실측]` · `[미확정]` · `[추론]`이며 **`[실측]`은 라이브 콘솔 직접 관측만**을 가리킨다.

## §0 인수인계 — 여기서 시작한다 (2026-07-30)

### 한 문단

**무엇**: 픽스처를 자기 DMX 점유폭에 잇는 조인 키가 없어도, **열거 가능한 모드 전체의 폭 최대값**을 상계로 삼아 *"겹침 없음"*을 증명한다. 증명되지 않으면 **충돌이 아니라 미확정**으로 보고한다. PRECHK가 수행하지 않고 수행하지 않았다고 보고한 축을 되살리되 **판정의 비대칭을 계약으로 만든다.**
**상태**: **plan-phase 완결 · 독립 plan-audit 1회차 완료(FAIL 0.806 → 지적 19건 전건 처리, §3).** 아티팩트 7종(`research` · `spec` · `acceptance` · `CONTRACT` · `design` · `plan` · 본 문서). REQ 18 · AC 21 · ASSUMPTION 31~35 · 마일스톤 M0~M8. **코드 변경 0건** — 아직 아무것도 구현하지 않았다.
**열린 사용자 접점**: **0건** — 어휘 확장 승인을 착수 전에 받았다(2026-07-30).
**라이브 세션**: **0회** — 필요한 값이 전부 PRECHK에 실측 전재되어 있다. run-phase도 **라이브를 요구하지 않는다.**

### 직전에 무슨 일이 있었나 — 같은 세션에서 PRECHK가 머지됐다

**본 SPEC의 BASE는 그 머지 이후다.** 이 SPEC만 읽으면 놓치는 사실이므로 여기 적는다.

| 사실 | 값 |
|---|---|
| PRECHK PR #7 | **squash 머지 (2026-07-30)** → `b406a7b2bde856f0ecfb445885e6fe60693c68a5` |
| 머지 직전 처리 | **독립 코드 리뷰 2건**(쓰기 경로 · 판독 경로 병렬)이 지적 14건을 냈고 **P1 4건을 머지 전에 고쳤다.** P1 넷 다 **2721개 스위트가 전건 통과하는 상태에서 살아 있었다** |
| 머지 후 처리 | P2·P3 **9건**을 계약 무변경으로 닫았다. 남은 2건은 어휘·스키마 확장을 요구해 **본 SPEC의 계약 결정과 묶인다** |
| 본 SPEC의 BASE | `85a4b2389003cb61b0ab72eb4aa8d6b2ff90b94a` — PRECHK §E.9를 기록한 문서 커밋이며 `b406a7b`의 자식이다 |
| 스위트 | 2721 → **2758** passed · 5 skipped · 0 failed |

**PRECHK가 남긴 규율 2건이 본 SPEC에 상속된다** — 규율 16(*"스위트가 통과한다"는 "결함이 없다"가 아니다*: 신규 테스트는 **수정 전 실패를 역방향으로 확인**하고 통과하는 테스트는 회귀 테스트가 아니라고 코드에 명시한다)과, 본 SPEC의 audit이 추가한 규율 17·18(§3 말미). **`CONTRACT.md` §6이 그 렌즈를 6건으로 정리해 배포한다.**

**PRECHK의 잔여 2건과 본 SPEC의 관계**: 부분 커버리지 고지의 슬롯 단위 정밀도와 *"어느 리포트 행이 보강에서 왔나"*가 그것이며 둘 다 **닫힌 어휘 또는 리포트 스키마 확장**을 요구한다. 본 SPEC이 그 확장을 승인받아 집행하므로 **M1 이후에 그 둘을 함께 처리할 여지가 생긴다** — 다만 본 SPEC의 요구가 아니므로 자동으로 닫히지는 않는다.

### 읽는 순서

| 순서 | 무엇을 알려주나 | 어디 |
|---|---|---|
| 1 | **왜 이 SPEC이 존재하나 / 무엇이 사실로 확립됐나** | `research.md` §1(출처) → §3(산술) → **§4(건전성 전제 3건 — 상계가 상계가 아닐 수 있는 경우)** |
| 2 | 무엇을 만들기로 했나 | `spec.md` — REQ 18 · §C PRESERVE와 ASSUMPTION 5건 · §D Out of Scope |
| 3 | 무엇을 통과해야 하나 | `acceptance.md` — AC 21 · 역추적표 · 계수 |
| 4 | **협상 불가 결정과 마일스톤 경계** | `CONTRACT.md` — §2 D-1~D-8 · §4 **BASE 세 개** · §5 M0~M8 · **§8 비준 기록 11건** |
| 5 | 왜 이 형상인가 | `design.md` — 슬롯 A~I · 후보 기록 25건(그중 기각 24) · 합성 리그 19 · 뮤테이션 35 |
| 6 | 어떤 순서로 만드나 | `plan.md` — §B M0~M8 · §C 게이트 · §G Phase 4 권고 |
| 7 | 조사 원문(가장 김) | `research.md` 전문 — 필요할 때만. **§F**(본 문서)는 첫 run-phase 스폰 전까지 비어 있음이 정상이다 |

### 인수인계 시 반드시 알아야 할 함정 5건

1. **`간격 == 상계`는 깨끗하다.** 술어는 `간격 < 상계`이며 `이하`가 아니다. PRECHK `progress.md` §E.6 ④가 *"상계 이하라 미확정"*으로 적었고 그것은 off-by-one이다. **이 쇼파일에서는 42 > 31이라 두 표현이 같은 답을 내므로 오류가 잠복한다** — 간격이 정확히 상계인 리그에서 처음 드러나고 그때 깨끗한 리그를 미확정으로 보고한다.
2. **열거가 짧으면 상계도 상계가 아니다.** 모드 집합이 불완전하면 `max`가 부분집합의 최대값이 되어 참 상계보다 **작아지고**, `bound_proves_clear`가 **거짓 양성**으로 발화한다. 구체 수치: 부분집합 상계 29 vs 참값 31, 간격 30인 리그에서 결론이 뒤집힌다. **완전성 판정이 `max` 앞에 와야 하며 표기만 붙이고 계산을 계속하는 형태는 그 자체가 결함이다.**
3. **BASE는 세 개이며 용도가 다르다.** 본 SPEC `85a4b23…` · PRECHK PRESERVE 기준점 `95687a0e…` · SONGCUE 런페이즈 기준점 `38a6e7e…`. 선례 상수를 복사하면 게이트가 **주석 한복판과 루프 앞 13행**을 지킨다.
4. **`tools.py`에 "삭제 0행" 규칙을 쓰면 즉시 실패한다.** 실측 삭제가 1행이다(import 1행이 12행 블록으로 대체). hunk 위치 봉쇄를 써야 한다. PRECHK §E.7 ⑤가 이것을 놓쳤다.
5. **어휘 가드 튜플 누락은 무증상이다.** 신규 축을 표현 계층의 import 시점 가드 루프에 넣지 않아도 **어떤 테스트도 실패하지 않는다.** 그래서 `CONTRACT.md` D-6이 그 루프를 레지스트리 순회로 바꾸도록 결정했다 — 튜플에 항목을 추가하는 것으로 끝내면 다음 축을 추가하는 사람이 같은 함정을 만난다.

### 인수인계가 온전한지 기계로 확인하는 법

```
git rev-parse --abbrev-ref HEAD              -> feature/SPEC-COPILOT-OVERLAP-001
git status --short                           -> 비어 있음
uv run pytest server/tests/ -q               -> 2758 passed · 5 skipped · 0 failed
git diff --stat 95687a0e0eba90b325daf76efbd0ac197e69e2fc..HEAD -- \
  server/looks/schema.py server/looks/loader.py server/looks/roles.py \
  server/looks/resolver.py server/looks/instantiate.py server/looks/matching.py \
  server/looks/library/ server/web/preview.py console/lua/ \
  server/rulebook/assets/v2.4.2/               -> 빈 출력 (PRESERVE 무변경)
git diff --stat 85a4b2389003cb61b0ab72eb4aa8d6b2ff90b94a..HEAD -- \
  .moai/specs/SPEC-COPILOT-PRECHK-001/          -> 빈 출력 (PRECHK 문서 무변경)
```

**마지막 두 줄이 서로 다른 BASE를 쓰는 것은 오타가 아니다.** PRESERVE는 PRECHK 기준점으로만 유효하고(새 BASE면 항상 0행이라 무력) PRECHK 문서 무변경은 본 SPEC BASE로만 유효하다(PRECHK 기준점이면 그 문서들의 최초 작성 2887행이 실린다). `CONTRACT.md` §4가 정본이다.

### 다음 담당자가 먼저 할 일 — M0 착수 키트

**M0다.** `ASSUMPTION-34`(`state` 표면만으로 3단 순회가 도달하는가)를 닫는다. **라이브 불필요 · `cycle_type=none` · 프로토타입 비커밋.** `GO`면 `server/safety/**` 무변경이 확정되고, 부정이면 `spec.md` §C의 PRESERVE 서술을 개정한 뒤 M6·M7의 형상을 다시 본다. **M0 이전에 M1에 착수하지 않는다.**

#### 정확히 무엇을 해야 판정이 갈리나

`Patch/FixtureTypes/<t>/DMXModes/<m>/DMXChannels`의 `childCount`를 **`StateQueryPort.query_state`만으로** 읽는 인메모리 프로토타입 1개면 갈린다. **`query_property`가 한 번이라도 필요하면 부정**이고, 그 경우 PRECHK가 연 승인 4지점을 재사용해야 하며 `server/safety/**` PRESERVE 서술이 바뀐다.

판정 근거는 이미 조사에 있다 — 상계가 요구하는 읽기가 전부 `state` 표면이고 `state`는 이미 `StateQueryPort`로 프로덕션에 도달해 있다(`research.md` §9.6). **PRECHK가 받은 조건부 예외는 `prop`(프로퍼티) 때문이었다.** 즉 `GO` 방향이며 M0는 **확인만** 한다.

#### M0가 산출해야 하는 것 — 접두 행 5행

`AC-OVERLAP-020` ①이 네 접두어(`GO:` · `DESCOPE:` · `SKIP:` · `REOPEN:`)의 합이 **정확히 5행**임을 요구한다. 배정은 이미 정해져 있다:

| 전제 | 접두어 | 근거 |
|---|---|---|
| `ASSUMPTION-34` | M0가 판정 (`GO` 방향) | 프로토타입으로 갈린다 |
| `ASSUMPTION-31` · `ASSUMPTION-32` · `ASSUMPTION-33` · `ASSUMPTION-35` | **`SKIP:`** | 관측 없이 닫을 수 없다. **`GO`로 적으면 `AC-OVERLAP-020` ③이 실패로 판정한다** |

각 `SKIP:` 행은 **무엇을 측정하면 갈리는지**를 담아야 한다. 그 문안 재료는 `research.md` §11의 U-1~U-9에 전부 있다.

#### 착수 직전에 돌릴 것

```
git branch --show-current                    -> feature/SPEC-COPILOT-OVERLAP-001
git status --short                           -> 비어 있음
find server -name __pycache__ -type d -exec rm -rf {} + ; uv run pytest server/tests/ -q
                                             -> 2758 passed · 5 skipped · 0 failed
```

**baseline은 각 마일스톤이 착수 직전 직접 실측하며 이월 인용을 금지한다.** `plan.md` §A.2가 그 규율의 정본이다.

#### M0에서 절대 하지 말 것

1. **코드를 커밋하지 마라** — `cycle_type=none`이며 `plan.md` §B.0의 DoD가 `git status`로 그것을 판정한다. 프로토타입은 임시 산출물이고 삭제된다.
2. **`GO: ASSUMPTION-31`~`33`·`35`를 적지 마라** — 관측 없이 닫히지 않는다.
3. **M1에 손대지 마라** — 어휘가 M3·M4·M5의 선행물이지만 `ASSUMPTION-34` 부정이 M6·M7 형상을 바꾸므로 순서가 있다.

#### M1의 첫 함정을 미리 알아 둔다

M1(어휘 확장)은 **13편집점 + 배선 3**이고 그중 하나가 **누락해도 어떤 테스트도 실패하지 않는다**(표현 계층의 import 시점 가드 튜플). `CONTRACT.md` D-6이 그 루프를 레지스트리 순회로 **바꾸도록 강제**하므로 튜플에 항목을 추가하는 것으로 끝내면 **D-6 위반이며 `AC-OVERLAP-014` ⑦이 실패로 판정한다.** 그리고 **절차 순서가 있다** — 구조 변경을 신규 축 도입 **이전에** 해야 이후 누락이 무증상이 될 수 없다(`plan.md` §B.1).

## §1 Plan-phase log

### v0.1.0 — plan-phase 아티팩트 7종 작성 (2026-07-30)

착수 SHA **`85a4b2389003cb61b0ab72eb4aa8d6b2ff90b94a`**, 착수 baseline **2758 passed · 5 skipped · 0 failed**(직접 실측, 이월 인용 아님).

| 커밋 | 산출 |
|---|---|
| `f3092af` | `research.md` · `spec.md` · `acceptance.md` · `CONTRACT.md` — 정본 3종 + 계약 |
| (본 커밋) | `design.md` · `plan.md` — 병렬 산출 · `CONTRACT.md` §8 비준 기록 · `progress.md` |

### 이 SPEC은 제안서에서 오지 않았다 — 저장소 최초

선행 SPEC 6건은 전부 `docs/proposals/2026-07-26-lighting-direction-feature-proposal.md`의 항목이었다. 본 SPEC의 출처는 **PRECHK의 독립 run-audit가 열거한 후보 I-15**(`.moai/specs/SPEC-COPILOT-PRECHK-001/progress.md:653`)이며 제안서에 `구간 겹침` · `점유폭` · `overlap` 문자열은 **0건**이다 `[코드]`.

**절차적 귀결**: 감사가 만든 요구이므로 *"제안서가 무엇을 요구했나"*로 범위를 방어할 수 없다. 대신 **감사가 왜 이 후보를 열거했고 PRECHK가 왜 채택하지 않았는지**가 범위 근거다 — C-9는 *"폭이 유일한가"*를 물었고 I-15는 *"폭에 상계가 있는가"*를 묻는다. **더 약한 명제로 같은 결론에 도달하는 것이며 `ASSUMPTION-27` 부정을 뒤집지 않는다.**

### 조사 방법 — 2층이며 라이브를 돌리지 않았다

| 층 | 수단 | 산출 |
|---|---|---|
| 정적 | **병렬 read-only scout 4개** — 배선 · 어휘 · 유니버스 · 스키마·게이트 | 좌표 표 4건. 충돌 0 |
| 검산 | **코디네이터 직접 실행** | 간격 산술 재계산 · 주소 파서 실행 · git 이력 조회 · PRECHK 문서 참조 테스트 grep |

**라이브 프로브를 돌리지 않은 근거**: PRECHK가 plan-phase에 사전 프로브를 돌린 것은 1차 산출물의 성립이 *"픽스처 주소를 읽을 프로퍼티명이 존재하는가"* 하나에 걸려 있었기 때문이다(`.moai/specs/SPEC-COPILOT-PRECHK-001/progress.md:85`). 본 SPEC의 성립은 **이미 실측된 값**에 걸려 있고 그 값은 전재되어 있다. 남은 라이브 항목은 전부 `ASSUMPTION`이며 **어느 것도 착수를 막지 않는다.**

**scout에게 이미 알려진 것을 재도출하지 말라고 명시했다** — §E.6 ④ · §E.7 · §E.8 · §E.9를 먼저 읽히고 그 위에 없는 것만 찾게 했다. 그 결과가 아래 정정 5건이다.

### 조사가 정정한 선행 서술 5건

| # | 선행 서술 | 정정 |
|---|---|---|
| 1 | §E.6 ④ *"간격이 상계 **이하**라 미확정"* | **off-by-one.** 술어는 `간격 < 상계`다 |
| 2 | §E.7 *"어휘 확장은 **4곳**을 원자적으로"* | **파일 단위로는 맞고 편집점 단위로는 과소.** 기존 축 값 추가 **3편집점** / 새 축 **10편집점** + 배선 3 |
| 3 | §E.7 ⑤가 tools.py 보호구역 **①만** 기록 | **② dedupe 루프 BASE 범위 `(537, 582)`가 누락됐다.** 이번에 처음 실측 |
| 4 | §E.7 ⑤의 *"순수 추가 = 삭제 0"* 기계 규칙 | **`tools.py`도 삭제 1행이다.** 그 규칙을 적용하면 즉시 실패한다 |
| 5 | §E.9 *"다음 SPEC BASE = `b406a7b`"* | **실제 BASE는 1커밋 위 `85a4b23`.** 코드 무변경 문서 커밋이라 게이트 의미는 동일 |

추가로 **선행 기록이 추정을 단정으로 적은 것 1건**을 잡았다 — `.moai/specs/SPEC-COPILOT-PRECHK-001/progress.md:1113`의 *"`childCount 1024`는 유니버스 개수"*는 근거가 병기되지 않았고 `DmxUniverses/1`의 자식 `'DMX 2'`와 정합하지 않는다. **`[실측]`으로 인용하면 안 된다.**

### 조사가 새로 확립한 것 — 요구를 낳은 4건

| # | 사실 | 등급 | 낳은 요구 |
|---|---|---|---|
| 1 | **건전성 전제 3건이 전부 현 표면에서 관측 불가다** — 연속 블록(브레이크 프로퍼티 판독 불가) · `DMXChannels` 자식 수 = DMX 슬롯 수(자식 이름 기록 0건) · 열거 완전성 | `[문서]`·`[코드]` | `ASSUMPTION-31`~`ASSUMPTION-33` · `REQ-OVERLAP-003` · `AC-OVERLAP-020` ④ |
| 2 | **주소 공간에 검증이 0건이다** — 파서가 `^(\d+)\.(\d+)$` 하나이며 `normalize_address("0.0")`이 `ok=True`를 낸다 | `[코드]` **실행 확인** | `REQ-OVERLAP-012` |
| 3 | **유니버스 서로소성에 살아 있는 뮤테이션 구멍이 있다** — 구간 겹침 축을 두 유니버스로 밟는 테스트가 **0건**이라 유니버스 키잉을 지워도 스위트가 통과한다 | `[코드]` | `REQ-OVERLAP-009` · `AC-OVERLAP-009` ③④ |
| 4 | **512는 필요하지 않다.** 논증이 요구하는 것은 `B ≥ 467`이라는 훨씬 약한 명제이며 판정이 갈리는 창은 `B ∈ [437, 466]` **30값**뿐이다 | `[문서]` 산술 | `ASSUMPTION-33` · §D Out of Scope |

그리고 **최소 간격 42는 일반 리그의 성질이 아니다** — 룰북의 `addr = addr + 42` 예제 결과가 실측 유니버스 1의 슬롯 2~10 주소와 **정확히 일치한다** `[문서]`. 42도 31도 하드코딩할 수 없는 근거이며(`REQ-OVERLAP-001`) 동시에 같은 룰북이 겹침 회피를 요구하므로 **기능의 문서적 정당화**가 된다.

### 512 근거 0건 — 살핀 범위를 남긴다

후속 SPEC이 같은 조사를 반복하지 않게 **범위 9곳**을 기록한다 `[코드]`·`[문서]`. 룰북 전수 5파일 · `console/lua/PROTOCOL.md`와 `console/lua/**` · `docs/**` · `server/**` 전역 · `.moai/specs/**` 전 12 SPEC · 루트 3파일 · 한국어 개념어 · 개념 정규식 4종.

**저장소에서 512를 유니버스 용량으로 쓰는 유일한 지점이 `.moai/specs/SPEC-COPILOT-PRECHK-001/progress.md:1113`이며 그 문장의 내용이 *"근거를 찾지 못했다"*다.** 자기참조 외 독립 근거는 없다.

### plan-phase 실행 형태 — 병렬은 계약이 닫힌 뒤에만

PRECHK의 판정을 그대로 계승했고 **실측으로 정당화됐다.**

| 국면 | 형태 | 결과 |
|---|---|---|
| 조사 | **병렬 scout 4개** | 충돌 0. **선행 기록 정정 5건 + 신규 확립 4건** |
| 정본 3종(`research`·`spec`·`acceptance`) | **코디네이터 단독 · 순차** | 6문서는 독립 슬라이스가 아니라 한 설계의 투영이다. SONGCUE가 감사 2회전에서 받은 지적 34건의 대부분이 문서 간 드리프트였고 뿌리면 그 드리프트를 **보장**한다 |
| `CONTRACT.md` | **코디네이터 단독** | 계약을 고정하는 것이 병렬의 전제다 |
| `design.md` + `plan.md` | **병렬 2** | **드리프트 0건**(아래) |
| `progress.md` | **코디네이터 단독** | 계수·신호가 6문서 실측에서 나온다 |

#### 병렬이 값을 냈다 — 두 워커가 계약의 빈틈 11건을 올렸다

계약을 고정했어도 빈틈이 있었고 **두 작성자가 각각 다른 각도에서 찾았다.** 전건은 `CONTRACT.md` §8에 있고 요지는 이렇다:

- **정본의 오류 3건**: PRESERVE 경로 분리가 4/6이 아니라 **3/7**(실행 확인) · `AC-OVERLAP-019` ⑧의 BASE 미지정(PRECHK 기준이면 **2887행**이 실린다) · BASE가 두 개가 아니라 **세 개**
- **워커 결정 8건**: 등급 순서 · 슬롯별 근거 수용처 · M0 프로토타입 비커밋 · 내부 7키 이름 · 슬롯 H·I 신설 · 테스트 파일명 · 트립와이어 편집의 소속 마일스톤 · 두 AC의 외견상 모순 해소

**세 번째 BASE와 트립와이어 소속 마일스톤은 코디네이터가 계약을 쓸 때 몰랐던 것이다.** 단독으로 6문서를 썼다면 그 둘이 run-phase까지 갔을 것이다.

#### 교차 대조 — 드리프트 0건

| 검사 | 결과 |
|---|---|
| 마일스톤 수 | `design` 9 · `plan` 9 · CONTRACT 9 |
| **마일스톤별 AC 배정** | **전 9행 프로그램 대조 일치** |
| AC 합집합 | 세 문서 **21** · 중복 0 · 누락 0 |
| 고정 문자열 7종 | 두 문서 동일 |
| 세 번째 BASE | 두 문서가 **독립적으로 찾아** 같은 프레이밍 |

`design.md` 작성자가 위험 1건을 **스스로** 고쳤다 — 초안의 경로 없는 좌표(`design.md:143`)가 저장소 루트의 동명 파일(204행 실재)로 오해석될 수 있었다. **PRECHK plan-audit가 P3로 낸 것과 같은 계열이며 이번에는 작성자가 먼저 잡았다.**

## §2 Plan-phase Audit-Ready Signal

```yaml
plan_status: audit-ready
plan_complete_at: 2026-07-30
spec_version: "0.1.0"
base_sha: 85a4b2389003cb61b0ab72eb4aa8d6b2ff90b94a
baseline_measured: "2758 passed · 5 skipped · 0 failed (착수 SHA에서 직접 실측, 이월 인용 아님)"
source: "PRECHK 독립 run-audit 후보 I-15 — 제안서 아님. 저장소 최초"
artifacts: [research.md, spec.md, acceptance.md, CONTRACT.md, design.md, plan.md, progress.md]
artifact_lines: "plan 827 · design 749 · research 565 · acceptance 225 · CONTRACT 207 · progress 205 · spec 171 (wc -l)"
requirements: 18           # REQ-OVERLAP-001~018 — 정의 18 = 고유 토큰 18
acceptance_criteria: 21    # AC-OVERLAP-001~021 — 절 제목 21 = 고유 토큰 21
milestones: 9              # M0~M8. M0만 cycle_type=none
assumptions_open: 5        # ASSUMPTION-31~35
live_sessions_planned: 0   # 필요한 값이 전부 PRECHK에 실측 전재
decisions_closed: 16       # CONTRACT D-1~D-8 + design.md D-9~D-16
decisions_open: 0
design_slots_closed: 9     # design.md 슬롯 A~I
design_slots_open: 0
clarification_markers: 0
user_touchpoints_open: 0   # 어휘 확장 승인은 착수 전 확보
machine_gates:
  requirements_counted: "18 — spec.md 정의 18 = 고유 토큰 18"
  req_to_ac_coverage: "18/18 — acceptance.md 역추적표 REQ 행 18, 커버 누락 0"
  acceptance_criteria_counted: "21 — acceptance.md 절 제목 21 = 고유 토큰 21"
  ac_milestone_assignment: "21 — M0 1 · M1 1 · M2 6 · M3 5 · M4 3 · M5 2 · M6 1 · M7 1 · M8 1. 중복 0 · 누락 0. CONTRACT §5 · design.md · plan.md 삼자 프로그램 대조 일치"
  ac_absent_from_traceability_table: "3 — AC-OVERLAP-019(형상 전체) · AC-OVERLAP-020(전제 판정) · AC-OVERLAP-021(종단 통합). acceptance.md가 의도로 명시하며 PRECHK가 AC-PRECHK-015~017에 같은 구조를 썼다"
  cross_document_drift: "0 — 대조한 축을 열거한다: (a) 마일스톤 9행 AC 배정 (b) 고정 문자열 7종 = `server/prechk/footprint.py` · `server/tests/test_prechk_footprint.py` · `server/tests/test_overlap_preserve.py` · `OVERLAP_BASIS_LABELS` · 세 BASE 40자 SHA (c) 상계 판정 술어 `간격 < 상계`(`이하`·`초과` 잔존 0건) (d) **계수 문구**(경로 분류 · 편집점 수 · 후보 기록 수) — (d)는 audit 1회차가 P1-1로 지적한 뒤 추가됐다. **초안의 대조 집합에 (d)가 없어 `design.md`의 4/6 오류를 놓쳤다.**"
  design_slot_milestone_alignment: "9 슬롯 전부에 집행 마일스톤 명시. M0만 슬롯 없음(전제 판정이며 형상 결정 아님)"
  mutations_proposed: 35   # design.md §5 — 각 뮤테이션이 어느 AC를 죽이는지 명시
  synthetic_rigs: 19       # design.md §4 — 경계값 2건 포함(간격 == 상계, == 상계-1)
  design_candidates_recorded: 25   # design.md §3 — A-1~A-4(4) + R-1~R-21(21). 그중 A-3은 **채택**(D-1)이므로 기각은 24
  rejected_designs: 24
  live_measurement_claims_by_this_spec: 0
gate_false_positives:      # 감사가 재검출할 수 있는 것. **audit 1회차가 ①②④를 오탐으로 확인하고 ③의 계수를 정정했다**
  - "축약 토큰 정규식 `[^A-Z-](AC|REQ)-[0-9]{3}` 히트 1건 = CONTRACT.md의 **금지 형태를 명명하는 규칙 문구 자신** — audit 확인"
  - "`spec.md:121` 형태 히트 2건 = 전부 `.moai/specs/SPEC-COPILOT-PRECHK-001/` **전체 경로 접두**를 가진 타 SPEC 인용이며 규약이 허용한다 — audit 확인"
  - "경로 없는 `design.md:143` 히트 **2건**(`CONTRACT.md:207` · `progress.md:143`) = 둘 다 **위험을 서술하는 기록 자신.** 초안이 1건으로 적었고 audit이 2건으로 정정했다"
  - "`research.md`의 `· 101 · 143 …` = **주소값**이며 중점 뒤 3자리 축약 토큰이 아니다 — audit 확인"
known_gaps:
  - "**건전성 전제 3건이 다른 쇼파일을 요구한다** — 연속 블록(`ASSUMPTION-31`) · `DMXChannels` 자식 수 = 슬롯 수(`ASSUMPTION-32`) · 유니버스 용량(`ASSUMPTION-33`). 현 쇼파일은 픽스처타입 1종뿐이라 앞 둘의 실험이 원리적으로 불가능하다. 본 SPEC은 **셋 중 하나라도 거짓이면 `bound_proves_clear`를 내지 않는 형상**으로 출하한다 — PRECHK가 FID를 배제하고 출하한 것과 같은 형태다."
  - "**`bound_inconclusive` 분기는 라이브로 증명할 수 없다.** 현재 쇼파일 17 인접쌍 전부가 상계를 통과해 발동 입력이 **0건**이며 합성 인메모리 리그만이 덮는다. **라이브 증거를 요구하는 인수 조건은 원리적으로 충족 불가능하므로 쓰지 않았다** — 감사가 *'GO 분기만 실측됐다'*를 지적으로 올릴 수 있고 그 지적은 부당하다. 근거는 `research.md` §3.3."
  - "**타입 수 `T`의 실측 기록이 0건이다**(`ASSUMPTION-35`). 예산 상한 결정이 `T`에 걸리지만 보수적으로 잡고 소진 시 `not_performed`를 내면 `T`를 몰라도 안전하다."
  - "**절단 계수 비교의 4번째 사본을 만든다.** 기존 3건의 `childCount` 부재·0 정책이 서로 달라 단순 통합이 `acceptance.md` §D의 *'zero fixtures는 유효한 리그'*와 충돌한다. `CONTRACT.md` D-8이 수렴을 명시적으로 금지했고 그것은 **별도 리팩터 SPEC의 일**이다."
  - "**상속되는 스키마 드리프트 2건을 정정하지 않는다** — 판정 계층이 정본에 없는 4키를 내고 툴 계층이 `macro`에 7번째 키를 주입해 정본 6키가 이미 거짓이다. `spec.md` §D가 명시적 Out of Scope로 뒀다. 본 SPEC의 스키마 정본은 그것을 **명시하되 고치지 않는다.**"
  - "**보호구역 `(247, 251)`이 `_SELECTION_OPERAND`(PRECHK BASE **246**)를 덮지 않는다.** BASE 250행이 `re.compile(rf\"(?:Fixture|Group)\\s+{_SELECTION_OPERAND}\", …)`로 그 상수를 보간하므로 **246만 바꾸는 편집은 봉쇄와 교차하지 않고 게이트를 통과하면서 dedupe 예외 대상 커맨드 집합을 실질적으로 바꿀 수 있다.** `research.md` U-9가 폭 후보 문제로 적었으나 246 자체를 담지 않았고 plan-audit 1회차가 P2로 잡았다. **본 SPEC은 봉쇄 범위를 넓히지 않고 이 구멍을 명시해 후속 SPEC에 넘긴다** — 범위 확장은 선례 트립와이어의 SONGCUE 상대 상수와 대칭이 깨지고, 이 SPEC은 `tools.py` 보호구역을 소유하지 않는다. `CONTRACT.md` §6 결함 계열 4(*\"게이트가 결함을 비껴가는 형태를 의심한다\"*)에 해당한다."
  - "**`plan.md`에 REQ 토큰이 5건만 등장한다** — plan-audit 1회차가 이것을 지적으로 올리지 않았다(요구 추적이 AC를 경유하고 AC 21건이 전건 등장하며 역추적표가 REQ 18/18을 커버하므로 사슬이 끊기지 않는다). 그러나 자백을 남긴다 — 지적되면 `plan.md` 마일스톤 표에 REQ 열을 추가하는 것이 최소 수정이다."
  - "**plan-audit 1회차 FAIL 0.806 → 지적 19건 전건 처리**(§3). 계수는 불변이다. **다만 감사가 재검증하지 않았다** — 1회차 정정이 새 불일치를 만들지 않았다는 증명은 없고 run-phase 각 마일스톤의 착수 직전 실측이 덮는다."
next: "**plan-audit 1회차 완료 — FAIL 0.806 → 지적 19건 전건 처리(§3).** 2회차를 열지 않는 근거는 §3 말미에 있다. 다음은 **run-phase 착수 — M0 전제 판정부터.** M0는 `cycle_type=none`이며 인메모리 프로토타입으로 `ASSUMPTION-34`를 닫고 프로토타입은 커밋하지 않는다. **M0 이전에 M1에 착수하지 않는다** — `ASSUMPTION-34` 부정이면 PRESERVE 서술이 바뀌고 그것이 M6·M7의 형상을 바꾼다. 열린 사용자 접점 0건이므로 Kickoff는 형식적이다."
```

## §3 Plan-audit 결과 — FAIL 0.806 → 지적 19건 전건 처리 (2026-07-30)

독립 감사자(작성자가 아닌 주체)가 7문서를 채점했다. **Verdict: FAIL · 가중합 0.806 / 기준선 0.85.** 지적 19건(P1 3 · P2 9 · P3 7).

| 축 | 가중치 | 감사 요지 |
|---|---:|---|
| 인용 정확성 | 20% | 범위 밖 좌표 0건이나 **경로 없는 좌표**가 정본과 인수 조건에 남았고, `research.md`의 COLLISION 사슬 좌표 3건이 무관한 생성문을 가리켰다 |
| **교차 정합** | **30%** | **FAIL을 몰고 온 축이다.** P1 3건이 전부 여기다 |
| 요구-AC 정합 | 15% | 역추적 18/18은 정확하나 `AC-OVERLAP-020` ④가 집행 마일스톤 없이 떠 있었다 |
| AC 기계검증성 | 15% | `AC-OVERLAP-018` ②③⑤ 비공허성 누락 · ⑤ 판정 대상 무지정 · `AC-OVERLAP-014` ⑥이 계약과 모순 |
| 증거 등급 규율 | 10% | **`[실측]` 15건 전수가 등급 정의·"0건" 선언·금지 문장이며 자기 관측 주장 0건** — 신호가 사실로 확인됐다. 닫힌 4등급 밖의 `[추론]` 사용이 지적 |
| 범위 경계 | 5% | 일관되나 `AC-OVERLAP-018` ⑤가 판정 대상 없이 경계를 고정한다고 주장했다 |
| 미결 은닉 | 5% | `_SELECTION_OPERAND`(BASE 246) 보호 공백이 `known_gaps`에 없었다 |

**감사가 재현해 정확하다고 확인한 계수**: REQ 18 · AC 21 · 역추적 18/18 커버 누락 0 · 마일스톤별 AC 배정 21(삼자 프로그램 대조) · 슬롯 9 · 뮤테이션 35 · 합성 리그 19 · BASE 상대 보호구역 `(247,251)`·`(537,582)`와 SONGCUE `(234,238)`·`(524,569)`의 **끝점 원문과 +13 오프셋** · safety 2파일 삭제 0/1(독스트링 원문) · `tools.py` 삭제 1행 원문 · PRESERVE 10경로 빈 출력 · PRECHK 기준 2887 insertions vs 본 SPEC 기준 빈 출력 · `DESCOPE:` 행 1건 · 41 디스패치 지점 · 인접쌍 17 · 상계 31 · 창 `[437,466]` 30값. **그리고 상계 술어가 7문서에서 `간격 < 상계`로 일관되며 `이하`·`초과` 드리프트 0건임을 확인했다.**

### P1 3건 — 전부 교차 정합 축이며 전건 닫았다

| # | 지적 | 처리 |
|---|---|---|
| **P1-1** | **`design.md`에 정정 전 PRESERVE 경로 분류 4/6이 남았다.** `acceptance.md`를 7/3으로 정정한 **바로 그 커밋에서** `design.md`가 4/6을 신규로 썼다. 귀결이 무겁다 — `cross_document_drift: 0`과 §8 교차 대조 표가 **반증된다** | **닫힘** — `design.md`를 7/3 + *"분류를 목록에서 기계로 도출"*로 고쳤다. 그리고 **원인을 고쳤다**: `cross_document_drift`의 대조 축에 **(d) 계수 문구**를 추가하고 초안의 대조 집합에 그것이 없어 놓쳤다는 사실을 신호에 적었다. 대조 축 4종을 이제 열거한다 |
| **P1-2** | **`AC-OVERLAP-020` ④를 집행하는 마일스톤 DoD가 0건이다.** 배정된 M0는 `cycle_type=none`·코드 0·테스트 0이며 `plan.md` 전문에 ④ 언급이 0건이다. 더욱이 ④가 **기계 충족 불가**다 — `ASSUMPTION-31`·`ASSUMPTION-32`는 관측 불가이므로 코드가 그 거짓을 감지해 발화를 억제할 수 없다 | **닫힘 — 지적이 옳다.** ④를 **코드가 관측할 수 있는 전제 위반**(열거 불완전 · 예산 소진 · 순회 예외)으로 좁히고 집행을 **M2**로 명시했다. **관측 불가 전제에 대한 정직한 형상은 발화 억제가 아니라 한정 표현**이며 `AC-OVERLAP-015`가 그것을 소유하고 **M5**가 집행한다. 본 항이 **항 단위로 셋 마일스톤에 걸치는 유일한 인수 조건**임을 명시했다 |
| **P1-3** | **`plan.md`가 5지점에서 존재하지 않는 `progress.md` §F를 구속력 있는 기록으로 지목한다.** 실제 헤딩은 §3이었고 `plan.md`의 *"본 SPEC의 progress.md도 §F 헤딩을 선제 생성하며"*는 **거짓 사실 주장**이었다. **`plan.md` §G가 스스로 LOOKLIB 선례를 인용해 막겠다고 선언한 바로 그 끊어진 참조를 재생산했다** | **닫힘** — `progress.md`의 해당 헤딩을 **§F로 개명**했다. PRECHK 관례가 §F이고 `plan.md`의 5지점 인용이 그것을 전제하므로 문서 5곳을 고치는 것보다 정확하다. §0 읽는 순서도 맞췄다 |

### P2 9건 · P3 7건 — 전건 닫았다

| # | 등급 | 지적 | 처리 |
|---|---|---|---|
| P2-4 | P2 | `research.md`의 COLLISION 사슬 좌표가 무관한 생성문을 가리킨다 | **닫힘** — 감사가 준 실제 좌표로 교정. 주장 자체는 참이었고 근거만 틀렸다 |
| P2-5 | P2 | **`"state_calls 등호 단정이 저장소 전체에 0건"`은 거짓이다** — `server/tests/test_prechk_inventory.py:990`에 있고 **가장 강한 형태**다 | **닫힘 — 이번 감사의 가장 아픈 지적이다.** 그 테스트는 **내가 이 세션의 P1 수정에서 직접 쓴 것**이며 그것을 잊고 *"0건"*을 단정했다. `CONTRACT.md` §6 결함 계열 5의 자기 위반이다. *"조회 **계수**에 대한 등호 단정은 0건"*으로 좁히고 그 테스트를 좌표와 함께 명시했다 |
| P2-6 | P2 | **`ASSUMPTION-35`의 접두어를 어느 문서도 지정하지 않아 관측 없는 `GO:`가 통과한다.** 계수 표도 5건 중 4건만 처분했다 | **닫힘** — `AC-OVERLAP-020` ③에 추가해 접두어를 `SKIP:`으로 고정하고 계수 표에 5번째 행을 넣었다. **PRECHK plan-audit P1-2와 같은 형태**(조건부 미지를 판정 확정으로 셈)다 |
| P2-7 | P2 | `AC-OVERLAP-018` ②③⑤에 비공허성 단정이 없고 ⑤는 **판정 대상이 무지정**이다 — 문서가 스스로 금지한 형태다 | **닫힘** — ②③에 방문 수 하한을 달고 ⑤에 판정 대상(실행 포트 대역 기록 + 매크로 경로 대조)을 명시했다 |
| P2-8 | P2 | `AC-OVERLAP-014` ⑥의 표제가 D-6과 **모순**이다 — D-6이 가드 튜플을 없애도록 강제하므로 *등재*할 튜플이 남지 않는다 | **닫힘** — 표제에서 *등재*를 빼고 **관측 가능한 결과**만 요구하도록 고쳤다. 가드에 항목을 추가해 ⑥을 충족시키는 것을 **실패로 판정**한다고 명시했다 |
| P2-9 | P2 | 어휘 확장 편집점 계수가 **10이 아니라 13 + 배선 3**이다. `plan.md`는 목표 문장과 자기 절차가 직접 모순했다 | **닫힘** — `AC-OVERLAP-014` 표제와 `plan.md` M1 목표를 고쳤다 |
| P2-10 | P2 | 보호구역 `(247, 251)`이 그것이 보간하는 `_SELECTION_OPERAND`(BASE **246**)를 덮지 않아 **246만 바꾸는 편집이 게이트를 통과한다** | **닫힘 — 범위를 넓히지 않고 명시해 넘긴다.** `known_gaps`에 신설했다. 범위 확장은 선례 트립와이어의 SONGCUE 상대 상수와 대칭이 깨지고 본 SPEC은 그 보호구역을 소유하지 않는다 |
| P2-11 | P2 | 뮤테이션 표 마일스톤 배정 4건 모순 — **M-35가 코드 변경 0건인 M0에 물린다** | **닫힘** — M-35를 `주입 M2 · 판정 M7`로, M-30·M-31도 주입·판정 분리로 고치고 **열 관례를 §5 서두에 명문화**했다. M-4 행은 D-6 이후 *등재 누락*이 주입 불가가 되므로 유증상 형태(**구조를 되돌리는 것**)로 재기술했다 |
| P2-12 | P2 | 경로 없는 좌표가 205행 형제 문서로 오해석된다 — **인수 조건이 그중 하나를 인용한다** | **닫힘** — 27건을 `.moai/specs/SPEC-COPILOT-PRECHK-001/` 전체 경로로 교정했다(프로그램 처리). 남은 1건은 `gate_false_positives`가 선언한 **의도된 자기참조**다 |
| P3-13 | P3 | `tools.py` 총 행수가 실측과 1행 어긋난다 | **닫힘** — `wc -l` 기준으로 교정하고 관례를 병기했다. +330 차이와 보호구역 오프셋은 정확했다 |
| P3-14 | P3 | *"기각 25건"*이 1건 과다 — A-3은 **채택**(D-1)이므로 기각은 24 | **닫힘** — `design_candidates_recorded: 25` + `rejected_designs: 24`로 갈랐다 |
| P3-15 | P3 | `gate_false_positives` ③ 계수가 1→2로 틀리고 `artifact_lines`의 CONTRACT 행수가 틀리다 | **닫힘** — 둘 다 교정하고 `progress` 행수를 목록에 추가했다. **오탐 선언 자체의 계수가 틀리면 그 선언의 신뢰가 깨진다**는 지적이 정확하다 |
| P3-16 | P3 | 닫힌 4등급 밖의 `[추론]`을 쓴다 — **닫힌 어휘를 주제로 삼는 SPEC이 자기 메타레벨에서 그 규율을 어긴다** | **닫힘** — `[추론]`을 5번째 등급으로 **명시 추가**했다(정의 병기). PRECHK도 쓴 상속 관례이므로 제거가 아니라 명시가 맞다 |
| P3-17 | P3 | `R-n`이 `CONTRACT.md` §8(비준)과 `design.md` §3.2(기각) 사이에서 네임스페이스 충돌 | **닫힘** — `design.md` §3.2를 `X-1`~`X-21`로 재지정했다(21행). 잔존 `R-n` 0건 |
| P3-18 | P3 | 같은 단정을 가리키는 테스트 좌표 범위가 문서마다 3군으로 다르다 | **닫힘** — 세 좌표로 단일화했다(11지점) |
| P3-19 | P3 | `cross_document_drift`의 근거 *"고정 문자열 7종"*이 어느 문서에도 열거되지 않아 **재현 불가능**하다 | **닫힘** — 대조 축 4종과 문자열을 전부 열거했다. **P1-1과 짝을 이루는 지적이다** — 대조 집합이 열거되지 않았기 때문에 무엇이 대조되지 **않았는가**를 독자가 알 수 없었다 |

### 2회차를 열지 않는 근거

19건을 닫으면서 **새 요구·AC·마일스톤·`ASSUMPTION`을 만들지 않았고 계수가 불변이다**(REQ 18 · AC 21 · M0~M8 · `ASSUMPTION-31`~`ASSUMPTION-35`). P1 3건은 전부 **교차 정합·기계검증성** 층이며 코드 설계를 바꾸지 않았다 — 유일한 예외가 P1-2이고 그것은 **인수 조건을 좁힌 것**이지 요구를 바꾼 것이 아니다.

**다만 감사가 재검증하지 않은 상태를 기록한다** — 1회차 정정이 새 불일치를 만들지 않았다는 증명은 없으며 run-phase 각 마일스톤의 착수 직전 실측이 그것을 덮는다. PRECHK가 같은 판단을 했고 그 기록이 선례다.

### 감사가 값을 낸 지점 — 규율 2건을 남긴다

17. **작성자의 교차 대조는 자기가 대조한 축에서만 유효하다.** 나는 마일스톤 AC 배정·고정 문자열·BASE 세 축을 프로그램으로 대조하고 *"드리프트 0건"*을 신호했다. **감사가 네 번째 축(계수 문구)에서 P1을 찾았다** — 내가 `acceptance.md`를 7/3으로 고친 그 커밋에 `design.md`의 4/6이 들어 있었다. **대조 집합을 열거하지 않으면 무엇이 대조되지 않았는지 아무도 알 수 없다**(P3-19가 P1-1과 짝인 이유). 이제 `cross_document_drift`가 대조 축을 열거한다.
18. **자기가 방금 쓴 테스트도 잊는다.** P2-5에서 *"`state_calls` 등호 단정 0건"*을 `[코드]` 등급으로 단정했는데 **그 단정을 깨는 테스트를 같은 세션에서 내가 직접 썼다.** 전수 주장의 근거는 그것을 만든 사람의 기억이 아니라 **방금 돌린 명령의 출력**이어야 한다.

## §4 Run-phase Evidence

### M0 — 전제 판정: `state`만으로 도달하는가 (`AC-OVERLAP-020` · `cycle_type=none` · 2026-07-30)

> **본 절이 M0의 추적되는 정본이다.** 프로토타입은 저장소 밖(`/tmp`)에서 돌렸고 판정 직후 삭제했으므로 실행 원문을 여기 요약 없이 전재한다(`plan.md` §F.3).

#### 착수 전제 확인 — 직접 실측이며 이월 인용이 아니다

| 명령 | 산출 | 판정 |
|---|---|---|
| `git branch --show-current` | `feature/SPEC-COPILOT-OVERLAP-001` | 일치 |
| `git status --short` | 빈 출력 | 일치 |
| `git merge-base --is-ancestor 85a4b2389003cb61b0ab72eb4aa8d6b2ff90b94a HEAD` | 종료 코드 **0** (HEAD = `8a5fa77f7e57be23df887019c1f258dfdb06371a`) | 진입 조건 1 충족 |
| `find server -name __pycache__ -type d -exec rm -rf {} + ; uv run pytest server/tests/ -q` | **2758 passed · 5 skipped · 0 failed** (89.12s) | 진입 조건 2 충족 · baseline 확정 |

#### 프로토타입 — arm 5개이며 arm B가 없으면 arm A의 통과는 공허하다

`StateOnlyPort`는 **`query_state` 하나만 정의하고 `query_property`를 정의하지 않는다** — 프로퍼티를 한 번이라도 요구하면 `AttributeError`로 즉시 드러난다. 그것이 판정 장치이며 arm B가 그 장치가 살아 있음을 대조군으로 고정한다. 페이로드 형태는 `console/lua/PROTOCOL.md` 제4절과 `console/lua/copilot_responder.lua:600-640`에서, 리그 수치(모드 폭 29·29·29·31, `DMXChannels` 열거 절단과 `childCount` 참값의 비대칭)는 `.moai/specs/SPEC-COPILOT-PRECHK-001/progress.md:403`·`:408`에서 왔다 `[문서]`.

| arm | 무엇을 갈랐나 | 산출 |
|---|---|---|
| **A** | 3단 순회가 state 전용 포트로 완주하는가 | 조회 **6회** = `1 + T(1) + ΣM(4)` · 호출된 포트 메서드 **`['query_state']`** · 관측 폭 `[29, 29, 29, 31]` → 상계 **31** · 열거 완전 `True` |
| **B** | 판정 장치가 공허하지 않은가 (대조군) | `walk_needing_property`가 `AttributeError: 'StateOnlyPort' object has no attribute 'query_property'` — **부정 판정의 모습이 관측 가능하다** |
| **C** | arm A가 쓴 표면이 프로덕션에 이미 있는가 | `StateQueryPort` 선언 메서드 = `['query_state']`이고 순회 호출 집합이 그 부분집합 · 초크포인트 3층 `ConsolePort` · `ConsoleLink` · `_GateStatePort` 전부 `query_state` 보유 · `server/prechk/inventory.py`의 `server.bridge` import **없음** |
| **D** | 열거가 짧을 때 상계가 상계가 아님을 state 표면만으로 판별할 수 있는가 | 2단 예산을 3으로 줄이면 상계 후보 **29** · 완전성 **`False`** · 사유 `2단 열거 부분: 3/4 (타입 1)` — `childCount`와 `len(children)`이 **같은 스냅샷에** 있으므로 판별에 프로퍼티가 필요 없다 |
| **E** | 예산 소진이 state 표면에서 관측되는가 | 예산 3에서 `BudgetExhausted: Patch/FixtureTypes/1/DMXModes/2/DMXChannels` |

**부수 확립 1건 — 순회는 이름도 `FID`도 요구하지 않는다.** 경로 세그먼트에 스냅샷이 스스로 보고하는 **풀 슬롯 `i`**를 쓴다. `console/lua/copilot_responder.lua:426-449`가 숫자 세그먼트를 풀 슬롯으로 해석하고 그것이 `PROTOCOL.md`의 `i`와 같은 번호임을 주석으로 명시한다 `[코드]`. 즉 **식별자 해석 단계가 0단계**이며, 선행 SPEC이 `FID`를 판정 근거에서 배제해야 했던 종류의 미결이 이 축에는 발생하지 않는다.

**arm C가 `ASSUMPTION-34`를 `server/safety/**`에 연결하는 방식.** PRECHK가 조건부 예외를 받은 사유는 `prop`이 **프로덕션 경로로 도달 불가**였다는 것이다 — `build_prop_query`에 프로덕션 소비자가 0건이었고 OSC 송신 표면 import이 `server/bridge/` · `server/safety/` · `server/tests/` 셋으로 강제된다(`server/tests/test_architecture.py:27-31`) `[코드]`. 본 SPEC의 순회는 `query_state`만 쓰고 그 메서드는 초크포인트 3층에 **이미** 있으므로 신규 예외 지점이 **0건**이다. `server/safety/gate.py:601-610`의 `_query_state`는 경로 화이트리스트를 갖지 않고 조회 1건을 감사 1건으로 기록하므로 순회가 그 계약을 바꾸지도 않는다 `[코드]`.

#### 접두 행 5행 — 정본

```
GO: ASSUMPTION-34 ports=query_state effect=3단 순회(Patch/FixtureTypes 열거 -> Patch/FixtureTypes/1/DMXModes 열거 -> 각 모드 DMXChannels 계수)가 query_property를 정의하지 않은 인메모리 포트에서 조회 6회로 완주해 상계 31을 냈고 호출된 포트 메서드 집합이 정확히 {query_state}이며 그 집합이 StateQueryPort 선언 집합의 부분집합이고 ConsolePort·ConsoleLink·_GateStatePort 3층이 전부 그 메서드를 이미 보유한다. 대조군은 프로퍼티 요구가 AttributeError로 즉시 드러남을 확인했다. 귀결: server/safety/** 무변경이 확정되고 신규 예외 지점은 0건이다
SKIP: ASSUMPTION-31 연속 블록 전제. 브레이크가 둘 이상인 픽스처타입을 패치한 쇼파일에서 그 픽스처의 Patch 값과 해당 모드 DMXChannels childCount를 비교하면 갈린다 — 하나의 연속 블록이면 start + width - 1이 점유 끝과 일치하고 두 블록이면 어긋난다. 현 쇼파일은 픽스처타입 1종뿐이라 실험이 원리적으로 불가능하며 라이브 세션을 열어도 갈리지 않는다. 거짓이면 상계가 첫 블록을 과대평가하고 둘째 블록을 완전히 놓친다
SKIP: ASSUMPTION-32 DMXChannels 자식이 DMX 슬롯인가 논리 채널인가. 자식 이름을 확보하면 갈린다 — 열거가 절단되므로 DMXChannels/<n>을 개별 경로로 조회하거나 예산을 늘려 이름을 받고 16비트 어트리뷰트가 2슬롯을 차지하는 사례를 찾는다. 자식이 논리 채널이면 childCount < 실제 슬롯 수이고 상계가 과소평가되어 bound_proves_clear가 거짓 안심이 된다. 현재 저장소에 자식 이름 기록이 0건이다
SKIP: ASSUMPTION-33 유니버스 용량 B. 판정이 갈리는 창은 B 구간 437 이상 466 이하의 30값뿐이고 B가 467 이상이면 몰라도 증명된다. state Patch/DmxAddresses의 childCount가 512의 배수인가를 조회하면 간접적으로 갈리며 직접 경계 실험은 상계 폭 픽스처를 주소 490 근처에 패치 시도하는 쓰기이므로 본 SPEC 범위 밖이다. 걸리는 축은 꼬리 초과 판정 하나이며 spec.md의 Out of Scope가 그것을 범위 밖으로 뒀다
SKIP: ASSUMPTION-35 Patch/FixtureTypes의 childCount 즉 타입 수 T. state Patch/FixtureTypes 1회로 갈리며 node.childCount와 len(children)을 함께 읽어야 한다 — children 길이만 보면 절단된 풀에서 T를 과소평가한다. 본 SPEC은 T를 몰라도 안전하다: 예산 상한을 보수적으로 잡고 소진 시 not_performed를 내는 형상이며 M0 arm E가 그 소진이 state 표면에서 관측됨을 확인했다. 라이브 조회 1회로 닫히지만 본 SPEC은 라이브 세션 0회이므로 닫지 않는다
```

**접두어 계수: `GO:` 1행 · `SKIP:` 4행 · `DESCOPE:` 0행 · `REOPEN:` 0행 = 합 정확히 5행.** 한 전제가 두 행을 갖지 않는다. `REOPEN:` 0건이므로 범위 재개정 접점은 발생하지 않았고 `plan.md` §B.0의 부정 분기 3항은 **집행되지 않는다.**

#### DoD 6항 — 전건 기계 판정

| # | 조건 | 산출 | 판정 |
|---|---|---|---|
| 1 | 접두 행 합이 정확히 5행 | `grep -cE '^(GO\|DESCOPE\|SKIP\|REOPEN):'` → **5** (착수 시점 0) | 충족 |
| 2 | `ASSUMPTION-34` 행에 포트 메서드 이름 목록이 병기되고 비공허 | `ports=query_state` — 원소 1개, 공집합 아님 | 충족 |
| 3 | `ASSUMPTION-31`·`ASSUMPTION-32`·`ASSUMPTION-33` 접두어가 `SKIP:`이고 측정 방법을 담는다 | 3행 전부 `SKIP:` · 각 행이 "무엇을 조회하면 갈리는가"를 담는다. `ASSUMPTION-35`도 같은 형태(`AC-OVERLAP-020` ③) | 충족 |
| 4 | `git status --porcelain -- server/ console/` 빈 출력 | 빈 출력 | 충족 |
| 5 | `git status --porcelain` 빈 출력 (기록 커밋 이후) | 아래 §4의 커밋 직후 빈 출력 | 충족 |
| 6 | 스위트 계수가 baseline과 동일 | **2758 passed · 5 skipped · 0 failed** — 진입 시와 동일 | 충족 |

**`AC-OVERLAP-020` 중 M0가 판정하는 것은 ①②③이며 ④⑤는 M2·M5가 집행한다**(`acceptance.md` `AC-OVERLAP-020` 말미). M0는 ④⑤에 대해 아무것도 주장하지 않는다 — arm D·E가 그 형상이 state 표면에서 **표현 가능함**을 보였을 뿐이고 코드로 고정하는 것은 M2다.

#### 프로토타입은 버려졌다

`/tmp/overlap-m0-proto/proto.py`(7879바이트)를 판정 직후 `rm -rf`했다. 저장소 트리 안에 만들지 않았으므로 DoD 4·5는 삭제 여부와 무관하게 성립하며, 그것이 `/tmp`를 고른 이유다 — `server/`나 `server/tests/`에 두면 삭제를 잊는 순간 `cycle_type=none` 위반이 된다(`CONTRACT.md` §8 R-9).

### M1 — 어휘 확장 (`AC-OVERLAP-014` · `cycle_type=tdd` · 2026-07-30)

#### 착수 전제 확인 — 직접 실측

| 항목 | 산출 |
|---|---|
| M0 DoD 6항 | 전건 충족(위) |
| `ASSUMPTION-34` 접두 행 | 존재 · `GO:` — 부정 분기 미발동이므로 `plan.md` §B.0의 3항 개정 없음 |
| baseline | `uv run pytest server/tests/ -q` → **2758 passed · 5 skipped · 0 failed** (M0 기록 커밋 시점 재측정) |

#### 절차 순서를 지켰다 — 구조 변경이 신규 축보다 먼저다

| 단 | 무엇을 했나 | 관측 |
|---|---|---|
| 1 | `server/prechk/report.py`의 import 시점 가드를 하드코딩 5-튜플에서 **`CLOSED_VOCABULARIES` 순회**로 교체(D-6). 어휘 5종 시점이므로 결과 동일. 양방향으로 만들었다 — *어휘에 표 없음*과 *표에 어휘 없음* 둘 다 예외 | `2758 passed · 5 skipped · 0 failed` — **구조 변경 단독으로 무회귀** |
| 2 | 1의 성질을 테스트로 고정 — `TestImportTimeLabelGuard` 4건 | 39 passed (신규 4건 포함). **신규 축 없이 `AC-OVERLAP-014` ⑦의 판정이 이미 성립** |
| 3 | `OVERLAP_BASIS` 신설 + 레지스트리 **맨 끝** append | `uv run python -c "import server.prechk.report"` → `UnknownVerdict: label tables and closed vocabularies disagree` — **즉시 적발** |
| 4 | `OVERLAP_BASIS_LABELS` + `VOCABULARY_LABELS` 항목 | import 복구. **3과 4 사이에 무증상 창이 0** |
| 5 | `SKIPPED_CHECK_KIND` += `range_overlap_bound_inconclusive` + 대응 라벨 | — |
| 6 | `server/tests/test_prechk_verdicts.py` 정본 3단정 갱신(집합 · 키 · **순서**) | 어느 것도 삭제·약화하지 않았다. 순서 단정은 `OVERLAP_BASIS`를 6번째 원소로 받는다 |
| 배선 | `server/prechk/patch.py`의 `validate(...)` 상수 블록에 생산자 상수 **5개**(`RANGE_OVERLAP_BOUND_INCONCLUSIVE` + `overlap_basis` 4값) | D-5 — 표현 계층은 코드값을 라벨표 안에서만 철자한다 |

**1을 마지막에 하면 3과 4 사이에 무증상 창이 열린다** — 그 창을 열지 않은 것이 이 마일스톤의 산출물이며, 단 3의 관측(`UnknownVerdict` 즉시 발화)이 그 창이 실재했음을 역방향으로 보여 준다.

#### 뮤테이션 4건 — 전건 사망

| # | 주입 | 죽인 것 | 결과 |
|---|---|---|---|
| **MUT-A** | `OVERLAP_BASIS_LABELS`에서 `not_performed` 행 삭제 | `import server.prechk.report` | **killed** — `UnknownVerdict: label table for overlap_basis does not match its vocabulary` (`AC-OVERLAP-014` ⑥) |
| **MUT-A2** | 가드의 iterable을 하드코딩 튜플로 되돌림 | `TestImportTimeLabelGuard` | **killed** — 2 failed. **형태 단정이 하는 일이 이것이다**: 효과만 보는 단정은 튜플에 항목을 추가하는 조작으로 충족되고 그것이 D-6 위반이다(`AC-OVERLAP-014` ⑦) |
| **MUT-B** | 레지스트리에서 `"overlap_basis": OVERLAP_BASIS` 행 삭제 | `test_prechk_verdicts.py` | **killed** — 2 failed (집합 단정 + 키 단정) |
| **MUT-C** | append 위치를 **맨 끝에서 맨 앞으로** 이동 | `test_prechk_verdicts.py` | **killed** — 1 failed(순서 단정만). **집합 단정 단독이면 통과한다** — 순서 단정을 유지한 값이 여기서 관측된다(`AC-OVERLAP-014` ④) |

**신규 테스트 4건은 회귀 테스트가 아니다** — 그 사실을 `TestImportTimeLabelGuard`의 도크스트링에 코드로 명시했다. 하드코딩 튜플이 어휘를 빠뜨려도 import은 성공했고 라벨 드리프트 테스트는 레지스트리를 순회하므로 아무것도 보지 못했다. **그 단계가 무증상이었기 때문에 이 테스트들이 존재하며 그것들이 증상이다**(규율 16).

#### DoD 11항 — 전건 기계 판정

| # | 조건 | 산출 |
|---|---|---|
| 1 | `python -c "import server.prechk.report"` 종료 0 | 충족 |
| 2 | `test_prechk_verdicts.py` · `test_prechk_report.py` 전건 통과 | 8 + 39 passed |
| 3 | 뮤테이션 A | **killed**(위) |
| 4 | 뮤테이션 B | **killed**(위) |
| 5 | `CLOSED_VOCABULARIES` 기존 5줄 바이트 동일 | `git diff BASE..HEAD -- server/prechk/verdicts.py`가 그 블록에 **`+` 1행만** 낸다(순수 삽입) |
| 6 | `COLLISION_KIND` · `FIXTURE_VERDICT` 바이트 동일 | 같은 diff에서 두 상수를 건드리는 `+`/`-` 행 **0건**(`grep -cE '^[-+](COLLISION_KIND\|FIXTURE_VERDICT)'` → 0) |
| 7 | 신규 축 값 집합 · `SKIPPED_CHECK_KIND` 그 밖 값 동일 | `overlap_basis = ['bound_inconclusive', 'bound_proves_clear', 'exact_widths', 'not_performed']` · `skipped_check_kind = ['gate_unapproved', 'macro_descope', 'macro_no_groups', 'range_overlap_bound_inconclusive', 'range_overlap_descope']` — 기존 4값 보존 |
| 8 | 라벨표 이름이 `_LABELS`로 끝난다 | `OVERLAP_BASIS_LABELS` |
| 9 | 표현 계층의 코드 리터럴이 라벨표 대입 안에만 · 스캔 비공허 | 착수 시점부터 있던 `test_no_vocabulary_code_is_spelled_as_a_literal_outside_the_tables`가 신규 4값을 자동 포함해 통과 |
| 10 | 금지 토큰 스캐너 3종 통과 | 통과. **`bound_proves_clear`는 `proves`이며 금지 토큰 `proven`이 아니다.** 주석 산문에 있던 `proven` 1건도 `settled`로 바꿨다 — 스캐너 대상이 아니지만 규율을 메타레벨에서 어기지 않는다 |
| 11 | 스위트 계수가 baseline 이상 | **2762 passed · 5 skipped · 0 failed** = 2758 + 신규 4 |

#### 정정 1건 · 이월 1건

- **정정**: `server/prechk/report.py`와 `server/tests/test_prechk_report.py`의 도크스트링이 판정을 *"five closed sets의 원소"*로 적었다. 어휘가 6종이 되어 거짓이 되므로 **계수를 지웠다**(*"one of the closed sets"*). 계수를 손으로 적으면 다시 틀린다 — `CONTRACT.md` §8 R-1이 같은 이유로 분류를 기계 도출로 바꿨다.
- **이월(본 SPEC이 고치지 않는다)**: `uv run ruff check server/`가 **착수 시점에 이미 3건 실패**한다 — `server/safety/console.py:292`·`:346`과 `server/tests/test_web_dash.py:523`의 E501. BASE 원본을 꺼내 같은 3건임을 확인했다. 앞의 두 파일은 **PRESERVE**이므로 고치는 것이 위반이다. `AC-OVERLAP-019` ⑨의 판정 범위는 *"본 SPEC이 손댄 전 파일"*이며 그 5파일은 `ruff check`·`ruff format --check` 전건 통과다.

## §F Phase 4 Mode Selection — 확정 (오케스트레이터 소유 · 2026-07-30)

> 본 절은 **오케스트레이터가 첫 run-phase 스폰 전에 작성**하는 구속력 있는 기록이다. `plan.md` §G의 대응 절은 **권고**이며 오케스트레이터가 확정하거나 기각한다. 어긋나면 **본 절이 이긴다.**
>
> 이 헤딩은 plan-phase 완결 시점에 **선제 생성**되었다 — 선행 SPEC에서 `plan.md`가 존재하지 않는 `progress.md` 절을 구속력 있는 기록으로 지목해 끊어진 참조를 만든 사례가 있었고, BUSKWIZ가 선제 생성으로 그것을 고쳤으며 PRECHK가 계승했다. **본문이 채워지기 전까지 이 절은 비어 있음이 정상이며, 비어 있다는 사실 자체가 "아직 스폰하지 않았다"의 기록이다.**

`plan.md` §G의 권고는 **sub-agent 순차 · 초기 폭 1**이며 근거 셋은 어휘 사슬(M1이 단독 선행물이고 그것 없이는 M3·M4·M5가 **import조차 실패**한다) · 파일 교집합(교집합 0인 쌍이 M7 하나뿐이고 그것도 M6 커밋에 걸려 있다) · M0가 새 도메인을 만들지 않는다는 것이다.

**오케스트레이터는 M0 실측 후에 이 권고를 확정하거나 개정한다.** PRECHK가 폭 1로 확정한 뒤 M0 실측이 미지를 닫아 M4가 자립 슬라이스가 되자 **§F.1로 폭 2로 개정한 선례**가 있다(`.moai/specs/SPEC-COPILOT-PRECHK-001/progress.md` §F.1). **폭을 미리 약속하지 않는다.**

**읽기 전용 scout 병렬은 폭 권고와 무관하게 계속 유효하다** — 본 SPEC plan-phase가 scout 4개를 동시에 돌려 충돌 0건이었고 선행 기록 정정 5건을 냈다.

### §F.1 확정 — 오케스트레이터 직접 집행 · 폭 1 (M0 실측 후)

**`plan.md` §G의 권고를 방향에서 확정하고 수단에서 개정한다.** 권고는 *"sub-agent 순차 · 초기 폭 1"*이었다. **폭 1은 확정하고, 그 폭 1의 주체를 sub-agent가 아니라 오케스트레이터 직접으로 정한다.**

| 축 | 확정 | 근거 |
|---|---|---|
| 폭 | **1** | `plan.md` §G의 근거 셋이 M0 실측으로도 약해지지 않았다 — M1은 여전히 M3·M4·M5의 import 선행물이고, 파일 교집합 0인 쌍은 M7 하나뿐이며 그것도 M6 커밋에 걸려 있다(`CONTRACT.md` §8 R-5) |
| 주체 | **오케스트레이터 직접** (sub-agent 스폰 0건) | 폭 1에서 sub-agent는 병렬 이득이 0인데 **핸드오프 손실만 남긴다.** 본 SPEC의 P1 3건이 전부 교차 정합 축이었고(§3) 그 층은 전 아티팩트를 한 머리에 들고 있는 주체에게만 보인다 |
| 읽기 전용 scout | **계속 유효** | plan-phase가 scout 4개로 충돌 0건 · 선행 기록 정정 5건을 냈다. 좌표 재발견이 필요해지면 쓴다 |

**M0 실측이 폭을 넓히지 않은 이유 — PRECHK 선례와 갈리는 지점.** PRECHK는 M0 실측이 미지를 닫아 M4가 **자립 슬라이스**가 되면서 폭 2로 개정했다(`.moai/specs/SPEC-COPILOT-PRECHK-001/progress.md` §F.1). 본 SPEC의 M0가 닫은 것은 `ASSUMPTION-34`이며 그것이 푼 것은 **`server/safety/**` 무변경 확정**뿐이다 — 즉 M6·M7의 *형상*을 고정했을 뿐 **어떤 마일스톤도 선행물에서 떼어내지 않았다.** 어휘 사슬은 그대로다. 폭을 넓힐 근거가 M0에서 나오지 않았다.

**첫 스폰 시점의 기록.** 본 절 작성 시점의 sub-agent 스폰은 **0건**이며, 이후 폭을 넓히면 §F.2를 신설해 그 시점과 근거를 남긴다. **비어 있는 §F.2가 "넓히지 않았다"의 기록이다.**
