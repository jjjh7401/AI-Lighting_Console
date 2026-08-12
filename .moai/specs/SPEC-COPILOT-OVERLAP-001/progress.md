# SPEC-COPILOT-OVERLAP-001 — 진행 기록 (progress)

> **인용 규율.** 본 SPEC의 정본(`spec.md` · `acceptance.md`)은 **줄번호로 인용하지 않고** 안정 토큰만 쓴다. `파일:줄`은 **코드 · 룰북 · 응답기 프로토콜 · 타 SPEC 아티팩트**에만 쓴다. 요구·인수 토큰은 슬러그 포함 완전형만 쓴다(축약형 **0건**). 근거 등급은 `[코드]` · `[문서]` · `[실측]` · `[미확정]` · `[추론]`이며 **`[실측]`은 라이브 콘솔 직접 관측만**을 가리킨다.

## §0 인수인계 — 여기서 시작한다 (2026-07-30)

### 한 문단

**무엇**: 픽스처를 자기 DMX 점유폭에 잇는 조인 키가 없어도, **열거 가능한 모드 전체의 폭 최대값**을 상계로 삼아 *"겹침 없음"*을 증명한다. 증명되지 않으면 **충돌이 아니라 미확정**으로 보고한다. PRECHK가 수행하지 않고 수행하지 않았다고 보고한 축을 되살리되 **판정의 비대칭을 계약으로 만든다.**
**상태**: **run-phase 완결 → run-audit 1회차 FAIL 0.714 → P1 6건 폐쇄 완료 (2026-07-31).** 스위트 **2758 → 2933 passed · 5 skipped · 0 failed** · 라이브 세션 0회 · PRESERVE 위반 0건. 독립 감사가 뮤테이션 63건을 재주입해 **P1 6건**(출하 코드 2 · 게이트 4)을 냈고 **여섯 건 전부 2920 그린 아래에서 살아 있었다**. 전건 닫았고 오케스트레이터가 격리 트리에서 8종 재주입으로 방어를 확인했다(§7).
**→ 지금 할 일은 sync-phase다.** P1 **0건**. 남은 것은 `acceptance.md` 문언 4건과 P2·P3 잔여이며 **정본 상태 전이와 같은 커밋에 담는다**(§7 말미). 증거는 §4(마일스톤별) · 신호는 §5 · 감사와 폐쇄는 §7 · 팬아웃 근거는 §F.2. **아래 §0의 나머지는 plan-phase 시점의 인수인계 기록이며 그 시점의 판단으로 보존한다**(*"읽는 순서"*와 *"기계 확인"* 두 블록만 run-phase 값으로 개정했고, M0 착수 키트는 §6이 대체함을 표시했다). plan-audit 1회차는 §3이다.
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

### 읽는 순서 — **run-phase 완결 이후 개정 (2026-07-30)**

| 순서 | 무엇을 알려주나 | 어디 |
|---|---|---|
| **0** | **지금 무엇을 해야 하나** | **§6 다음 세션 착수 키트** — 재발견 비용을 0으로 만든다. 여기부터 읽는다 |
| **1** | **무엇이 만들어졌고 어떻게 증명됐나** | **§4 Run-phase Evidence** — M0~M8 각 절에 착수 baseline · 산출 · 뮤테이션 · DoD 표 |
| **2** | **감사가 먼저 볼 것 · 불일치 4건 · 정직한 잔여** | **§5 Run-phase Audit-Ready Signal** — `deviations` · `known_gaps` · `next` |
| 3 | 무엇을 통과해야 했나 | `acceptance.md` — AC 21 · 역추적표. **20건 충족 · 1건 부분**(§5) |
| 4 | **협상 불가 결정과 BASE 세 개** | `CONTRACT.md` — §2 D-1~D-8 · §4 BASE 3 · §5 M0~M8 · §8 비준 11건 |
| 5 | 왜 이 형상인가 | `design.md` — 슬롯 A~I · 후보 25(기각 24) · 합성 리그 19 · 뮤테이션 35 |
| 6 | 무엇을 만들기로 했나 | `spec.md` — REQ 18 · §C PRESERVE · §D Out of Scope. **`ASSUMPTION-34`가 `GO`였으므로 §C는 개정되지 않았다** |
| 7 | 왜 이 SPEC이 존재하나 | `research.md` §1(출처) → §3(산술) → §4(건전성 전제 3건) |
| 8 | 어떤 순서로 만들기로 했었나 | `plan.md` — §B M0~M8 · §C 게이트 · §G Phase 4 권고. **실측이 정정한 4건은 §5 `deviations`가 정본이다** |

> **plan-phase 산출물 6종은 사후 재작성하지 않는다** — 그 시점의 판단 기록이며 고치면 판단이 흐려진다. 계획과 실측이 어긋난 지점은 **§4의 해당 마일스톤 절과 §5 `deviations`**가 정본이고 어긋남 자체를 기록으로 남긴다.

### 인수인계 시 반드시 알아야 할 함정 5건 — **전건 run-phase에서 집행됐다**

> 아래 5건은 plan-phase가 예고한 함정이며 **전부 코드와 테스트로 닫혔다.** 어느 것을 어디가 닫았는지 병기했다 — 후속 편집이 그것을 되돌리려 할 때 무엇이 발화할지 알아야 한다.

1. **`간격 == 상계`는 깨끗하다.** 술어는 `간격 < 상계`이며 `이하`가 아니다. PRECHK `progress.md` §E.6 ④가 *"상계 이하라 미확정"*으로 적었고 그것은 off-by-one이다. **이 쇼파일에서는 42 > 31이라 두 표현이 같은 답을 내므로 오류가 잠복한다** — 간격이 정확히 상계인 리그에서 처음 드러나고 그때 깨끗한 리그를 미확정으로 보고한다.
2. **열거가 짧으면 상계도 상계가 아니다.** 모드 집합이 불완전하면 `max`가 부분집합의 최대값이 되어 참 상계보다 **작아지고**, `bound_proves_clear`가 **거짓 양성**으로 발화한다. 구체 수치: 부분집합 상계 29 vs 참값 31, 간격 30인 리그에서 결론이 뒤집힌다. **완전성 판정이 `max` 앞에 와야 하며 표기만 붙이고 계산을 계속하는 형태는 그 자체가 결함이다.**
3. **BASE는 세 개이며 용도가 다르다.** 본 SPEC `85a4b23…` · PRECHK PRESERVE 기준점 `95687a0e…` · SONGCUE 런페이즈 기준점 `38a6e7e…`. 선례 상수를 복사하면 게이트가 **주석 한복판과 루프 앞 13행**을 지킨다.
4. **`tools.py`에 "삭제 0행" 규칙을 쓰면 즉시 실패한다.** 실측 삭제가 1행이다(import 1행이 12행 블록으로 대체). hunk 위치 봉쇄를 써야 한다. PRECHK §E.7 ⑤가 이것을 놓쳤다.
5. **어휘 가드 튜플 누락은 무증상이다.** 신규 축을 표현 계층의 import 시점 가드 루프에 넣지 않아도 **어떤 테스트도 실패하지 않는다.** 그래서 `CONTRACT.md` D-6이 그 루프를 레지스트리 순회로 바꾸도록 결정했다 — 튜플에 항목을 추가하는 것으로 끝내면 다음 축을 추가하는 사람이 같은 함정을 만난다.

| # | 무엇이 닫았나 | 되돌리면 무엇이 발화하나 |
|---|---|---|
| 1 | `unsettled_gaps`의 `gap.size < bound` + 경계 테스트를 **순회 층과 판정 층 두 곳**에 | `<=`로 바꾸면 **6건 실패**(M3 뮤테이션 M-9) |
| 2 | `WalkOutcome`에 `bound` 필드가 **없고** 폴드가 완전성 참 분기 안에만 있다 + AST 판정 | 무조건 폴드로 바꾸면 **5건 실패**(M-1). 3단 예산 소진을 국소 표기로 강등하면 **1건 실패**(M-5 — 그 테스트는 뮤테이션이 1회차에 살아남아서 추가됐다) |
| 3 | `server/tests/test_overlap_preserve.py`가 PRECHK BASE를 **단독 소유**하고 두 상수가 정확히 13 어긋남을 단정 | 선례 상수를 복사하면 **1건 실패**(M-33). 선례 SHA를 이 파일에 재타이핑하면 **자기참조로 실패한다**(초안이 실제로 그랬다) |
| 4 | hunk **위치** 봉쇄 `(247, 251)` · `(537, 582)` + *"삭제 계수 규칙은 이 파일에 맞지 않다"*를 실측으로 단정 | 삭제 계수 규칙으로 바꾸면 착수 직후 실패한다 — 그 사실 자체를 테스트가 `added >= 1 and deleted >= 1`로 고정한다 |
| 5 | 가드 루프를 `CLOSED_VOCABULARIES` **순회**로 교체(양방향) + **형태 단정**(리터럴 시퀀스 루프 재발 금지) | 라벨표 항목 1개 제거 → **import 예외**(MUT-A) · 튜플로 되돌리면 **2건 실패**(MUT-A2) |

**그리고 run-phase가 함정 1건을 새로 발견했다** — `SKIPPED_CHECK_KIND_LABELS["range_overlap_descope"]`(*"구간 겹침 판정 미수행"*)이 `OVERLAP_BASIS_LABELS["not_performed"]`(*"겹침 판정 미수행"*)을 **부분문자열로 포함한다.** 따라서 `label(...) in summary` 형태의 단정은 `not_performed`에 대해 **등급이 한 번도 인쇄되지 않아도 통과한다.** 요약 단정은 반드시 **접두 포함형**(`겹침 판정 근거: <라벨>`)으로 쓴다(M5 절).

### 인수인계가 온전한지 기계로 확인하는 법

```
git rev-parse --abbrev-ref HEAD              -> feature/SPEC-COPILOT-OVERLAP-001
git status --short                           -> 비어 있음
uv run pytest server/tests/ -q               -> 2920 passed · 5 skipped · 0 failed
                                             #  (2758은 M0 착수 시점 값이며 run-phase 완결로 갱신됐다)
git diff --stat 95687a0e0eba90b325daf76efbd0ac197e69e2fc..HEAD -- \
  server/looks/schema.py server/looks/loader.py server/looks/roles.py \
  server/looks/resolver.py server/looks/instantiate.py server/looks/matching.py \
  server/looks/library/ server/web/preview.py console/lua/ \
  server/rulebook/assets/v2.4.2/               -> 빈 출력 (PRESERVE 무변경)
git diff --stat 85a4b2389003cb61b0ab72eb4aa8d6b2ff90b94a..HEAD -- \
  .moai/specs/SPEC-COPILOT-PRECHK-001/          -> 빈 출력 (PRECHK 문서 무변경)
git diff --stat 85a4b2389003cb61b0ab72eb4aa8d6b2ff90b94a..HEAD -- \
  server/safety/                               -> 빈 출력 (ASSUMPTION-34 GO의 귀결)
git diff --numstat 85a4b2389003cb61b0ab72eb4aa8d6b2ff90b94a..HEAD -- \
  server/tests/test_songcue_bundle.py          -> 빈 출력 (선례 게이트 파일 무변경)
grep -cE '^(GO|DESCOPE|SKIP|REOPEN):' \
  .moai/specs/SPEC-COPILOT-OVERLAP-001/progress.md   -> 5
uv run pytest server/tests/test_overlap_preserve.py -q  -> 23 passed  (PRESERVE 상시 게이트)
```

**마지막 두 줄이 서로 다른 BASE를 쓰는 것은 오타가 아니다.** PRESERVE는 PRECHK 기준점으로만 유효하고(새 BASE면 항상 0행이라 무력) PRECHK 문서 무변경은 본 SPEC BASE로만 유효하다(PRECHK 기준점이면 그 문서들의 최초 작성 2887행이 실린다). `CONTRACT.md` §4가 정본이다.

### ~~다음 담당자가 먼저 할 일~~ — M0 착수 키트 (**집행 완료 · §6이 대체한다**)

> **이 절은 §6이 대체한다(2026-07-30).** M0는 집행됐고 판정은 `GO: ASSUMPTION-34`이며 그 증거는 §4의 M0 절이다. **지금 할 일은 §6에 있다.**
>
> 남기는 이유는 절차적이다 — 이 절이 예고한 것(**`GO` 방향이며 M0는 확인만 한다** · `SKIP:` 4건의 배정 · 접두 행 정확히 5행 · *"M0에서 절대 하지 말 것"* 3건)이 **전건 그대로 성립했다.** 예고가 맞았다는 기록은 다음 SPEC이 plan-phase에 같은 형태의 키트를 쓸 근거이며, 지우면 그 근거가 사라진다.

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
  - "**절단 계수 비교의 4번째 사본을 만든다.** 기존 3건의 `childCount` 부재·0 정책이 서로 달라 단순 통합이 `.moai/specs/SPEC-COPILOT-PRECHK-001/acceptance.md:313`(§D 퇴화·경계 케이스)의 *'픽스처 0개는 거부가 아니라 정상'*과 충돌한다. `CONTRACT.md` D-8이 수렴을 명시적으로 금지했고 그것은 **별도 리팩터 SPEC의 일**이다. **(run-audit 정정: 초안이 이것을 `acceptance.md` §D로 적었으나 본 SPEC의 `acceptance.md`에 §D는 없다 — 타 SPEC 인용의 전체 경로 접두가 빠져 있었다.)**"
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

### M2 — 순회 모듈 (`AC-OVERLAP-001`~`AC-OVERLAP-006` · `cycle_type=tdd` · 2026-07-30)

#### 착수 전제 확인

| 항목 | 산출 |
|---|---|
| M1 DoD 11항 | 전건 충족(위) |
| `import server.prechk.report` | 종료 0 — 순회 모듈이 판정 어휘를 쓸 수 있다 |
| baseline | **2762 passed · 5 skipped · 0 failed** (M1 커밋 시점 실측) |

#### 산출

`server/prechk/footprint.py` **304행**(신규) · `server/tests/test_prechk_footprint.py` **35건**(신규). 기존 파일 갱신 **0건**.

형상은 설계 슬롯 그대로다 — **A-ii**(순회는 `(완전성, 폭 집합)`을 돌려주고 `WalkOutcome`에 `bound` 필드가 **없다**) · **B-iii**(1·2단은 `_listing_is_whole` 목록 완전성, 3단은 `_declared_child_count` 계수 존재성 — 3단은 `children`을 **한 번도 참조하지 않는다**) · **C**(예산은 파라미터이고 소진은 국소 표기가 아니라 **전역 무효**).

**사유 코드는 신설하지 않았다.** `server.orchestrator.tools`를 import하면 하드 순환이므로 `REASON_UNRESOLVED` · `REASON_UNREACHABLE` 두 값을 모듈에 재타이핑하고, **테스트가 원본과 등호로 고정한다** — 드리프트가 세 번째 어휘로 갈라지는 대신 실패한다. 이 저장소가 닫힌 어휘에 쓰는 재타이핑 정본과 같은 형태다.

#### 뮤테이션 6건 — 5건 즉사 · **1건이 살아남아 테스트를 고쳤다**

| # | 주입 | 결과 |
|---|---|---|
| **M-1** | `upper_bound`가 완전성과 무관하게 `max`를 접는다(**A-i 직역**) | **killed** — 5 failed. `AC-OVERLAP-003` ⑥의 부분집합 함정 테스트가 여기서 발화한다 |
| **M-2** | 3단에도 목록 완전성 술어를 적용(**B-i**) | **killed** — 8 failed. 실측 형태(3단 `truncated=true`)에서 기능이 통째로 죽는 것이 관측된다 |
| **M-3** | 자식을 풀 슬롯 `i` 대신 **열거 위치**로 주소 지정 | **killed** — 1 failed. 희소 풀(슬롯 4·9) 리그가 잡는다 |
| **M-4** | 분류를 형제 응답 여부 대신 **예외 타입**으로 | **killed** — 3 failed |
| **M-6** | 1·2단에서 `truncated` 플래그를 무시 | **killed** — 1 failed |
| **M-5** | 3단 예산 소진을 `_exhausted` 대신 **국소 표기 + `break`**로 강등 | **1회차에서 살아남았다** — 아래 |

**M-5가 살아남은 것이 이 마일스톤의 가장 값나가는 관측이다.** 코드는 옳았고 **테스트가 그 구멍을 재지 않았다.** 기존 예산 테스트 둘의 예산(2·3)이 **폭을 하나도 수집하기 전에** 소진되어 *"관측된 모드가 0개다"* 가드가 대신 통과시키고 있었다. 예산 **4**(3모드 중 2개를 읽고 세 번째에서 죽는다)로 재면 강등된 코드가 `complete=True` · `mode_widths=(5, 7)`을 내고 폴드가 **7**을 답한다 — 참 상계 11보다 **작은 상계**이며 정확히 거짓 안심이다. `test_exhaustion_after_some_widths_were_read_still_kills_the_bound`를 추가해 닫았고, 그 테스트가 **비공허성으로 `DMXChannels` 조회 2회가 실제로 발생했음**을 먼저 단정한다. 재주입하면 1 failed로 죽는다.

**이것이 규율 16의 이번 사례다** — 34건이 전부 통과하는 상태에서 A-i 계열 결함 하나가 3단에 살아 있었다. 뮤테이션을 돌리지 않았다면 발견되지 않았다.

#### DoD 15항 — 전건 기계 판정

| # | 조건 | 산출 |
|---|---|---|
| 1 | `python -c "import server.prechk.footprint"` 종료 0 | 충족 — 테스트가 `subprocess`로 판정한다(A-4 핸들러 클로저 배치 배제) |
| 2 | `server.orchestrator.tools` import 0건 + import 노드 ≥ 1 | 충족 |
| 3 | 포트 사용이 `query_state` 하나 · `query_property` 0건 + 호출 노드 ≥ 1 | 충족. 리그 대역이 `query_property`를 **정의하지 않으므로** 의존이 생기면 `AttributeError`로 드러난다 |
| 4 | `server/prechk/**` 상수에 `29`·`31`·`42`·`50` 0건 + 방문 파일 ≥ 1 + 정수 노드 ≥ 1 | 충족(실측 정수 집합은 `{0, 1, 2}`뿐) |
| 5 | 폭 `{17, 23}` 주입 → 상계 **23** | 충족. 그리고 `{11, 19, 47}` → **47**로 **두 번째 주입**을 단정한다 — 한 주입만 보면 값이 고정된 코드도 통과한다 |
| 6 | 조회 경로 3단 순서 기록 · 경로 수 ≥ 3 | 충족 |
| 7 | 3단에서 `children` 참조 0건 + 방문 함수 ≥ 1 | 충족 |
| 8 | `AC-OVERLAP-003` ①②③④ 네 경우 전부 상계 미산출 | 충족 |
| 9 | `max` 노드가 완전성 판정 분기 **내부** | 충족 — 발견된 `max` 노드 전량이 `complete`를 보는 `If` 내부임을 단정하고 노드 수 ≥ 1을 함께 본다 |
| 10 | `AC-OVERLAP-003` ⑥ 거짓 양성 재현 + 역방향 확인 | 충족 — M-1 재주입에서 그 테스트가 실패한다(killed) |
| 11 | `AC-OVERLAP-004` ①②를 한 테스트에서 · ③ 계수 비교 미사용 | 충족. **대조군**으로 1·2단 술어가 실제로 `len()`을 쓴다는 것도 단정한다 — 분리가 무의미해지지 않게 |
| 12 | `AC-OVERLAP-006` ①②③④ | 충족. ③은 두 시나리오를 **같은 `StateQueryError`**로 던져 재현한다 |
| 13 | `git diff --stat BASE..HEAD -- server/safety/` 빈 출력 · `server/prechk/`는 비어 있지 않음 | safety **빈 출력** · prechk **4 files +364 −16**(비공허성 확인) |
| 14 | `PROPERTY_WHITELIST` 바이트 동일 | `git show BASE:…`와 `cmp` → **IDENTICAL**(325바이트) |
| 15 | 스위트 계수가 baseline 이상 | **2797 passed · 5 skipped · 0 failed** = 2762 + 35 |

**갱신 0건이 유지됐다.** `server/tests/test_prechk_inventory.py`의 두 소비 테스트(`queried_paths`가 픽스처 루트 하위 · 금지 프로퍼티명 스캔)가 **무변경 통과**한다 — 순회가 자기 조회 기록을 `WalkOutcome.queried_paths`에 담고 `"DMXModes"`·`"DMXChannels"`는 금지 집합의 원소가 아니기 때문이다(금지 집합은 `"Channels"`·`"ChannelCount"`를 **정확 문자열**로 금지한다).

### M3 — 상계 판정 (`AC-OVERLAP-008`~`AC-OVERLAP-012` · `cycle_type=tdd` · 2026-07-30)

#### 착수 전제 확인

| 항목 | 산출 |
|---|---|
| M2 DoD 15항 | 전건 충족(위) |
| baseline | **2797 passed · 5 skipped · 0 failed** (M2 커밋 시점 실측) |

#### 산출

- `server/prechk/footprint.py` — `AddressGap` · `address_gaps`(유니버스 내부 인접차) · `unsettled_gaps`(술어 **`간격 < 상계`**). 저장소 전체에 `a[i+1]-a[i]`를 구하는 지점이 0건이었으므로 신규다.
- `server/prechk/patch.py` — `_address_groups`로 그룹핑을 **추출**해 두 축이 같은 집합을 보게 했다(D-7) · `normalize_address`에 **하한** 도입 · `_bound_basis` · `_unsettled_reason` · `evaluate_patch(…, walk=…)` 수령 · `PatchEvaluation.overlap_basis` 필드.
- 테스트 **+41건**(`test_prechk_footprint.py` 9 · `test_prechk_patch.py` 32).

**주소 하한만 넣고 상한은 넣지 않았다.** `_MINIMUM_INDEX = 1`이며 `0.0` · `1.0` · `0.1` · `12.0`이 판독 실패로 분류된다. 상한은 `ASSUMPTION-33`이 용량을 미확정으로 두므로 **없는 것이 옳다** — 그 사실을 `1.512` · `1.1024` · `1.65535`가 **통과함**을 단정해 기계로 고정했다(`AC-OVERLAP-012` ④). 어휘를 신설하지 않았고 기존 `address_parse_failed`로 흐른다.

**미확정은 `range_overlaps`에 들어가지 않는다.** `_bound_basis`가 `(등급, 미확정 인접쌍, 상계)`를 돌려주고 미확정은 `skipped_checks`의 `range_overlap_bound_inconclusive` 한 행으로만 나간다 — 침묵이 결함이므로 고지하고, 충돌로 세지 않으므로 `충돌 N건`이 발화하지 않는다. 그 한 행의 `reason`에 유니버스·슬롯·간격·상계를 열거한다(kind당 1행이므로 행을 늘릴 수 없다, D-4).

#### 뮤테이션 6건 — 전건 사망

| # | 주입 | 결과 |
|---|---|---|
| **M-7** | 정확폭 축의 유니버스 키잉 붕괴 | **killed** — 아래 별항 |
| **M-8** | 상계 축(`address_gaps`)의 유니버스 키잉 붕괴 | **killed** — 6 failed |
| **M-9** | 술어를 `간격 <= 상계`로 | **killed** — 6 failed. **`간격 == 상계` 경계 테스트가 두 계층(순회 · 판정)에서 각각 발화한다** |
| **M-10** | 미확정 인접쌍을 `range_overlaps`에 주입 | **killed** — 3 failed |
| **M-11** | 주소 하한 제거 | **killed** — 8 failed |
| **M-12** | 상계 축이 `type_mode_ok`를 요구 | **killed** — 3 failed. 기존 테스트 1건도 함께 죽는다 |

#### `AC-OVERLAP-009` ③의 *"착수 시점에 살아 있었다"*를 실측으로 확인했다

조사는 이것을 `[코드]` 추론으로 적었다. **직접 재현했다.** 첫 시도(`intervals[0]`)는 기존 테스트 1건을 죽였는데 그것은 붕괴 때문이 아니라 **보고되는 유니버스 라벨이 0이 되었기** 때문이다 — 즉 순수한 붕괴 뮤테이션이 아니다. 라벨을 클러스터 구성원에서 가져오도록 고쳐 **주소 공간만** 붕괴시키면:

| 대상 | 결과 |
|---|---|
| 신규 테스트를 제외한 `test_prechk_patch.py` | **74 passed** — 뮤테이션이 살아 있다 |
| 신규 `TestUniverseDisjointnessOnBothAxes` 포함 | **1 failed** — 닫혔다 |

**그리고 리그를 고쳐야 했다.** 초안은 `1.500`·`2.001`을 썼는데 그 쌍은 **붕괴해도 답이 바뀌지 않는다** — 폭 40에서 구간 `500..539`와 `1..40`이 한 공간에서도 만나지 않는다. 초안 주석이 그 사실을 스스로 적으면서도 리그를 바꾸지 않았고, 그것은 **공허한 뮤테이션 테스트**였다. `1.100`·`2.110`으로 바꿔 붕괴 시 `100..139`와 `110..149`가 겹치게 하고, **같은 두 주소를 한 유니버스에 놓으면 두 축이 실제로 발화함**을 별도 테스트로 단정해 비공허성을 산문이 아니라 코드로 옮겼다.

#### DoD 10항 — 전건 기계 판정

| # | 조건 | 산출 |
|---|---|---|
| 1 | 간격 `W-1` → `bound_inconclusive` · **정확히 `W`** → `bound_proves_clear` · `W+1` → `bound_proves_clear`, 같은 리그 형상에서 간격만 변화 | 충족. `TestBoundBasisGrades`가 `_pair(gap)` 하나로 세 경우를 돌리고 `below != at` · `at == above`를 단정한다 |
| 2 | 유니버스 경계 차분이 간격 집합에 없다 | 충족(`1.500`·`2.001` → 간격 0건) |
| 3 | 간격 총수가 `Σ(n_u − 1)`이며 **17을 상수로 박지 않는다** | 충족 — 리그 형상에서 계산해 대조하고 기대값 ≥ 1을 함께 단정한다 |
| 4 | 유니버스 키잉 제거 뮤테이션이 **양 축에서** 죽고, 착수 시점에 살아 있었음을 확인 | 충족 — 위 별항 |
| 5 | 같은 `(유니버스, 주소)`가 간격 집합에 한 번만 · 간격 0 미산출 · 주소 중복 축은 여전히 검출 | 충족 — 그룹핑 **키 집합**을 쓰므로 형상으로 성립한다 |
| 6 | 타입·모드 미확정 픽스처가 **간격에 포함**되고 **정확폭 축에서는 제외**됨을 한 테스트에서 | 충족. M-12가 그 술어 차이를 지키는 것을 확인 |
| 7 | `AC-OVERLAP-011` ⑤ 먼저, 그 다음 ①②③ | 충족 — `test_the_unsettled_grade_is_actually_produced`가 먼저 등급 산출을 단정한다 |
| 8 | 미확정이 침묵으로 처리되지 않는다 | 충족 — `skipped_checks` 행이 나가고 `report.summary_ko`가 그 라벨을 *"미수행 판정:"* 절에 싣는다. 라벨은 *"구간 겹침 상계 미확정 — 간격이 상계 이내라 판정 보류"*이며 *"이상 없음"*이 아니다. **요약 도달의 전량 판정은 M5 소유다** |
| 9 | `AC-OVERLAP-012` ①②③④ | 충족(위) |
| 10 | 스위트 계수가 baseline 이상 | **2838 passed · 5 skipped · 0 failed** = 2797 + 41 |

**갱신 0건이 유지됐다** — `server/tests/test_prechk_patch.py`의 기존 3단정(정확폭 GO 분기 · 주소 중복 축 서로소성 · `DESCOPE: ASSUMPTION-27` 접두 행 1건)이 **무변경 통과**한다. 추가만 했다.

#### 관측된 플레이크 1건 — 본 SPEC과 무관하다

`server/tests/test_web_launcher.py::TestSidecarSelfReap::test_orphaned_sidecar_reaps_the_group_without_a_pipe`가 전체 스위트 실행 3회 중 2회 실패하고 **단독 실행에서는 71건 전건 통과**했으며 이후 전체 실행에서도 통과했다. 원인은 `_await_status`의 **15초 벽시계 데드라인**이며 사이드카 서브프로세스가 그 안에 `status.json`을 내지 못하면 실패한다 — 머신 부하에 걸린다. 본 SPEC의 변경은 `server/prechk/**`와 `server/tests/test_prechk_*`뿐이고 런처 계층은 그것을 import하지 않는다. **고치지 않고 기록만 남긴다** — 본 SPEC의 범위가 아니며 타이밍 데드라인 조정은 별건이다.

### M4 — 정확폭 우선 · 근거 배선 (`AC-OVERLAP-007` · `AC-OVERLAP-013` · `AC-OVERLAP-016` · `cycle_type=tdd` · 2026-07-30)

#### 착수 전제 확인

| 항목 | 산출 |
|---|---|
| M3 DoD 10항 | 전건 충족(위) |
| baseline | **2838 passed · 5 skipped · 0 failed** (M3 커밋 시점 실측) |

#### 산출

- `server/prechk/footprint.py` — `ModeFootprint(path, width)`로 폭을 **출처 경로와 함께** 담고 `WalkOutcome.footprints`가 그것을 싣는다(`mode_widths`는 파생 프로퍼티로 남긴다). `bound_source(outcome)` 신설 — `"<경로> childCount"`.
- `server/prechk/patch.py` — `OverlapBasis` 7키(`basis` · `bound` · `bound_source` · `mode_widths` · `exact_width_slots` · `bound_slots` · `observation_note`, `CONTRACT.md` §8 R-8) · `_BASIS_ORDER`와 `_weakest` · `_exact_width_slots` · `_overlap_basis` · `_observation_note` · `PatchEvaluation.overlap` 필드와 `overlap_basis` 프로퍼티 · `to_dict`에 **신규 최상위 키 1개**.
- 테스트 **+21건**.

**등급 순서를 코드로 고정했다** — `not_performed ≺ bound_inconclusive ≺ bound_proves_clear ≺ exact_widths`(R-6). 리그 전역 스칼라는 **수행된 비교 전체의 최약 등급**이며 그것이 D-4 정직성 제약 1의 집행이다.

**정확폭 우선은 두 층에서 집행된다** — ① 정확폭이 있는 슬롯은 `bound_slots`에서 제외되고 ② **양 끝이 모두 정확폭인 간격은 상계 판정 대상에서 빠진다.** ②가 없으면 정확폭으로 이미 깨끗하다고 판정된 쌍에 상계가 `bound_inconclusive`를 덮어씌운다(뮤테이션 M-16이 그것을 잡는다).

**`bound_source`가 자유 산문이 아니다** — 가장 넓은 모드의 `DMXChannels` 경로에 읽은 필드명을 붙인다. 선례가 경고다: `FootprintPolicy.source`는 축이 출하된 이래 필드로 있었고 **페이로드에 도달한 적이 없어** 소비자가 0건이다. 값과 출처를 같은 블록에 넣는 것이 그 반복을 막는다.

#### 뮤테이션 6건 — 전건 사망

| # | 주입 | 결과 |
|---|---|---|
| **M-13** | 리그 전역 등급을 **최강**으로(등급 순서 역전) | **killed** — 4 failed |
| **M-14** | 근거 7키 중 `bound_source`를 페이로드에서 누락 | **killed** — 4 failed. **이것이 `AC-OVERLAP-016` ④가 존재하는 이유다** — 착수 시점의 최상위 단정은 부분집합이라 키를 얹거나 빼도 아무것도 깨지지 않았다 |
| **M-15** | 정확폭 우선 제거(상계를 전 슬롯에 적용) | **killed** — 3 failed |
| **M-16** | 양 끝이 정확폭인 간격도 상계가 판정 | **killed** — 1 failed |
| **M-17** | 순회 실패 사유를 `observation_note`에서 삭제 | **killed** — 1 failed |
| **M-18** | 미비교 슬롯을 등급 계산에서 무시 | **killed** — 2 failed |

#### DoD 12항 — 전건 기계 판정

| # | 조건 | 산출 |
|---|---|---|
| 1 | 신규 최상위 키에 **정확 키집합 단정 신설** · 기존 부분집합·포함 단정은 그대로 | 충족 — `set(payload["overlap_basis"]) == EVIDENCE_KEYS`를 **네 등급 전부**에서 단정한다(등급별로 키집합이 달라지는 것도 결함이므로). 기존 최상위 부분집합 단정도 별도 테스트로 계속 확인 |
| 2 | 상계 값 + 출처 문자열이 페이로드에 · 출처가 **경로와 계수**를 담는다 · 자료구조와 페이로드 키가 함께 | 충족. **출처가 최대 폭을 따라 움직인다는 것**을 두 리그로 단정한다 — 한 리그만 보면 경로가 고정된 코드도 통과한다 |
| 3 | 정확폭 슬롯은 `exact_widths` · 없는 슬롯에만 상계 · 혼재 리그에서 둘 다 수행되고 각각의 근거로 보고 | 충족 |
| 4 | 착수 시점 정확폭 테스트 전건 통과 | 충족 — 갱신 0건 |
| 5 | 부분 커버리지 고지가 여전히 발화 | 충족 |
| 6 | D-4 정직성 1 — 3슬롯 미비교 시 `bound_proves_clear`를 찍으면 **실패하는 테스트**가 존재 | 충족 — `test_the_rig_wide_grade_is_the_weakest_comparison_performed`. 유효 2슬롯은 간격이 정확히 상계라 **settled**이고 그 사실을 비공허성으로 먼저 단정하므로, 등급 하락이 미비교 3슬롯에서 왔음이 분리된다 |
| 7 | D-4 정직성 2 — kind당 1행 · `skipped_checks[]` 정확 3키 단정 무변경 통과 | 충족 |
| 8 | 순회 전면 실패 리그의 `observed_count`가 성공 시와 동일 | 충족 |
| 9 | 같은 리그에서 주소 중복이 **검출된다**(비공허) | 충족 — 3중 중복 1건·구성원 3개를 단정 |
| 10 | `overlap_basis`가 `not_performed` · `skipped_checks` 대응 행 · 요약이 *"충돌 0건"*을 한정 없이 말하지 않는다 | 충족 — 요약에 `충돌 0건`과 **미수행 판정 라벨이 함께** 있음을 단정한다 |
| 11 | `collisions` 딕셔너리 전체 동등 단정 무변경 통과 | 충족 — 미확정이 `range_overlaps`에 들어가지 않음의 기계 확인 |
| 12 | 스위트 계수가 baseline 이상 | **2859 passed · 5 skipped · 0 failed** = 2838 + 21 |

**갱신 1건과 그 정당화.** M3이 쓴 `test_an_out_of_range_address_never_enters_the_gap_set`이 `bound_proves_clear`를 기대했는데 M4의 최약 등급 규칙에서는 **`not_performed`가 옳은 답이다** — 그 리그의 슬롯 1은 주소가 무의미해 어느 축도 비교하지 않았다. 테스트를 고치면서 **비공허성을 추가했다**: 같은 리그에서 슬롯 1을 빼면 `bound_proves_clear`가 나오므로 등급 하락이 미비교 슬롯에서 온 것이며 판정 실패에서 온 것이 아니다. 그 밖의 기존 테스트는 갱신 0건이다.

### M5 — 리포트 (`AC-OVERLAP-015` · `AC-OVERLAP-017` · `cycle_type=tdd` · 2026-07-30)

#### 착수 전제 확인

| 항목 | 산출 |
|---|---|
| M4 DoD 12항 | 전건 충족(위) |
| baseline | **2859 passed · 5 skipped · 0 failed** (M4 커밋 시점 실측) |

#### 산출

`server/prechk/report.py`의 `summary_ko`에 **`겹침 판정 근거: <라벨>(<관측 범위 한정>)`** 절을 추가했다. 테스트 **+10건**. 신규 파일 0건 · 기존 테스트 갱신 0건.

한정 표현은 **등급과 같은 문장에** 붙는다. 별 문장으로 두면 한 문장만 읽는 독자가 무한정 절반만 가져간다 — 그것이 선행 SPEC이 *"후보 12건 전건 부정"*을 무한정으로 적어 지적받은 것과 같은 계열이다.

#### 뮤테이션 6건 — 4건 즉사 · **2건이 살아남아 테스트를 고쳤다**

| # | 주입 | 결과 |
|---|---|---|
| **M-19** | 등급 절을 요약에서 제거 | **killed** — 5 failed |
| **M-20** | 관측 범위 한정을 요약에서 제거 | **killed** — 2 failed |
| **M-23** | 판정 계층이 한국어 라벨을 직접 만든다 | **killed** — 1 failed |
| **M-24** | 등급 채널을 미수행 채널 라벨로 대체 | **killed** — 4 failed(기존 재타이핑 스캔까지 함께 발화) |
| **M-21** | 상계 한정을 `exact_widths`에도 붙인다 | **1회차 생존** — 아래 |
| **M-22** | 한정 표현의 모드 수를 상수 `2`로 | **1회차 생존** — 아래 |

**M-21이 살아남은 이유: 대조 테스트에 순회가 없었다.** `AC-OVERLAP-015` ③의 대조는 *"정확폭 슬롯에는 상계 한정이 붙지 않는다"*인데 초안은 **`walk`를 넘기지 않은 리그**로 그것을 확인했다. 상계가 애초에 존재하지 않으면 한정의 부재는 우선순위 규칙을 아무것도 증명하지 않는다. `walk=_walk()`를 함께 넘겨 **상계가 존재하는데도 정확폭이 이기는 리그**로 바꿨고, `overlap.bound`가 실제로 실려 있음을 비공허성으로 먼저 단정한다.

**M-22가 살아남은 이유: 모드 수가 하나뿐이었다.** 테스트 리그의 열거 모드가 항상 2개라 상수 `2`로 바꿔도 통과했다. `_walk_of(modes)`를 만들어 **모드 수 2와 3을 둘 다** 재고, `열거된 모드 3개`가 2모드 요약에 **없음**까지 단정한다.

**그리고 라벨 부분문자열 충돌 1건을 잡았다.** `SKIPPED_CHECK_KIND_LABELS["range_overlap_descope"]`(*"구간 겹침 판정 미수행"*)이 `OVERLAP_BASIS_LABELS["not_performed"]`(*"겹침 판정 미수행"*)을 **부분문자열로 포함한다.** 따라서 `label(...) in summary` 형태의 단정은 `not_performed`에 대해 **미수행 채널 라벨만으로도 통과한다** — 등급이 한 번도 인쇄되지 않아도 초록이다. 단정을 **접두 포함형**(`겹침 판정 근거: <라벨>`)으로 바꿔 채널까지 고정했고 M-24가 그 형태를 지킨다.

#### DoD 6항 — 전건 기계 판정

| # | 조건 | 산출 |
|---|---|---|
| 1 | 4값 각각의 라벨이 요약에 도달 + **4값 전부가 실제로 산출**(비공허) | 충족 — `_every_grade()`가 리그 4개를 만들고 **각 리그가 자기 등급을 냈는지**를 값별로 단정한다(*"어떤 등급이든 나왔다"*가 아니다). 산출 집합이 닫힌 어휘와 정확히 일치 → 죽은 어휘 0건 |
| 2 | 라벨이 표현 계층 표에서 오고 판정 계층이 한국어를 만들지 않는다(AST) | 충족 — 판정 계층 문자열 집합과 라벨 집합의 교집합 0건 + **역방향 비공허성**(라벨이 리포트 소스에 실재) |
| 3 | 라벨 집합 = 어휘 집합(양방향) | 충족 — M1의 구조 변경 위에서 자동 성립하며 M5가 확인한다 |
| 4 | `bound_proves_clear`에 관측 범위 한정 · 어느 모드 집합에서 왔는지 · 비어 있지 않고 한국어 | 충족 |
| 5 | **대조**: 정확폭 슬롯에는 한정이 붙지 않는다 | 충족 — 상계가 존재하는 리그로 재측정(M-21 수정) |
| 6 | 스위트 계수가 baseline 이상 | **2869 passed · 5 skipped · 0 failed** = 2859 + 10 |

### M6 — 툴 배선 (`AC-OVERLAP-018` · `cycle_type=tdd` · 2026-07-30)

#### 착수 전제 확인

| 항목 | 산출 |
|---|---|
| M5 DoD 6항 | 전건 충족(위) |
| baseline | **2869 passed · 5 skipped · 0 failed** (M5 커밋 시점 실측) |
| 트립와이어 착수 기준선 | `git diff --unified=0 38a6e7e2…..HEAD -- server/orchestrator/tools.py`의 old-start 목록 = `(33, 49, 125, 463, 475, 479, 951, 1222, 1231)` — `_TOOLS_EXPECTED_HUNK_OLD_STARTS`와 일치 |

#### 산출

`server/orchestrator/tools.py`(갱신) · `server/prechk/footprint.py`(`sibling_answered` 추가) · `server/tests/test_prechk_tool.py` **+14건** · `server/tests/test_prechk_footprint.py` **+4건**. 신규 파일 0건. **(run-audit 정정: 초안이 툴 테스트를 `+22건`으로 적었다. 실측은 `+14`이며 `git show e780a38 -- server/tests/test_prechk_tool.py | grep -cE '^\+[[:space:]]*def test_'`와 커밋별 계수 `fa46113=52 → e780a38=66`이 일치한다. 그 오기가 §5의 마일스톤 분해로 전파됐었다.)**

#### 계획을 개정한 것 2건 — 둘 다 기계 증거가 강제했다

**① 섹션 누락은 호출을 거부하지 않는다.** D-3은 *"별도 상수를 신설하고 `create_macro` 분기 밖에서 항상 검사"*를 요구했고 그것은 그대로 집행했다. 그러나 **누락을 오류로 만들 수 없다** — `server/tests/test_prechk_tool.py:895-905`가 `{"fixtures": FIXTURE_ROOT}` 오버라이드(즉 `fixture_types`도 없다)로 매크로 가드 메시지를 단정하므로, 먼저 발화하는 오류가 그 메시지를 대체한다. 그리고 그래야 **옳다**: 거부는 이 툴의 존재 이유인 픽스처 재고를 버리는 것이며 같은 파일의 zero-target 매크로 분기가 이미 그 계열을 한 번 고쳤다. 따라서 가드는 **항상 검사하되 결과를 리포트에 담는다** — 섹션 이름을 말하고 *"조회를 시도하지 않았으므로 판독 실패가 아니다"*를 붙이며 등급은 `not_performed`다. D-3의 세 요건(별도 상수 · 분기 밖 · 이름으로 말하고 풀 판독 실패를 암시하지 않음)은 전건 충족된다.

**② 순회에 `sibling_answered`를 추가했다.** 설계 슬롯 C는 *"상계 순회는 픽스처 루트 조회가 이미 성공한 뒤에만 도달하므로 형제가 답했다가 참이고 `REASON_UNRESOLVED`가 근거 있게 도출된다"*고 적었다. 그런데 **순회는 그것을 안에서 알 수 없다** — 첫 조회가 실패하면 자기 기록이 비어 있고, 프로덕션은 *"경로 없음"*과 *"무응답"*을 같은 예외로 던진다. 그래서 호출자만 아는 사실을 파라미터로 받는다. 기본값은 `False`(보수적)이고 핸들러가 `True`를 넘긴다. 이 추가 없이는 툴 경로의 분류가 **항상 `console_unreachable`**이 되어 설정 결함을 운영 조건으로 보고했다 — 결함 계열 1의 재생산이다.

#### 트립와이어는 갱신이 필요하지 않았다 — 실측이 계획을 정정한다

`plan.md` §B.6이 *"tools.py를 고치므로 선례 트립와이어를 같은 커밋에서 갱신한다"*고 못박았다. **실측하니 갱신할 것이 없었다.**

| 대상 | 산출 |
|---|---|
| M6 이전 old-side hunk 헤더 | `-33` · `-49,0` · `-125,0` · `-463,0` · `-475,0` · `-479,0` · `-951,0` · `-1222,0` · `-1231,0` |
| M6 이후(워킹트리) old-side | **동일 9개** — `diff`로 대조해 `IDENTICAL_OLD_SIDE` |
| `git diff --numstat -- server/tests/test_songcue_bundle.py` | **빈 출력**(0행 변경) |
| 커밋 후 `test_songcue_bundle.py` | **20 passed** |

**이유는 기계적이다** — M6의 편집 전량이 PRECHK가 **이미 연 hunk 영역 안**에 떨어졌고(`--unified=0`에서 인접 삽입은 기존 hunk에 병합된다) old-side 경계는 새 삽입의 크기에 무관하다. 새 side는 커졌지만(`+150,25` → `+151,51` 등) 트립와이어는 old-side만 본다.

**귀결은 `AC-OVERLAP-019` ⑥에 유리하다** — 그 항이 *"변경이 트립와이어 값 1행에 한정"*을 요구하는데 실제 변경은 **0행**이다. ⑦의 *"갱신되고"*는 전제가 성립하지 않으나 그 항의 실질 불변식(**보호구역 교차 단정이 계속 성립**)은 유지되며 M7이 그것을 판정한다. **갱신하지 않은 것을 갱신했다고 적지 않는다.**

#### 뮤테이션 6건 — 전건 사망

| # | 주입 | 결과 |
|---|---|---|
| **M-25** | `PRECHK_RIG_SECTIONS`에 `"fixture_types"` 추가(기각 후보 X-9) | **killed** — 3 failed. **기존 테스트 `test_a_complete_override_still_builds_the_macro`까지 함께 죽는다** — 설계가 예측한 그대로다 |
| **M-26** | 순회 모듈에 `"Patch/FixtureTypes"`를 리터럴로(기각 후보 I-i) | **killed** — 1 failed |
| **M-27** | 섹션 가드를 `create_macro` 분기 안으로 | **killed** — 2 failed |
| **M-28** | `sibling_answered=False` | **killed** — 1 failed. 설정 결함이 운영 조건으로 보고되는 것을 잡는다 |
| **M-29** | 예산 상한을 40에서 2로 | **killed** — 3 failed |
| **M-30** | 순회 모듈에 `"Footprint"`·`"Channels"`·`"Universe"` 문자열 상수 | **killed** — 2 failed(**기존** 금지 프로퍼티명 스캔 + 신규 모듈 스캔) |

#### DoD 8항 — 전건 기계 판정

| # | 조건 | 산출 |
|---|---|---|
| 1 | `AC-OVERLAP-018` ①②③④⑤ 전건 | 충족. ①은 `server/web/**` 전수에 `footprint`·`walk_mode_widths`·`overlap_basis` 0건 + **역방향 비공허성**(툴 이름이 `TOOL_NAMES`에 있고 `walk_mode_widths`가 `tools.py`에 있다) · ②③은 `server/prechk/**` AST 스캔 + 방문 노드/모듈 하한 · ④는 예외 목록 재타이핑 대조 · ⑤는 상계 축을 켠 리그에서 실행 포트 기록이 **빈 목록**이고 **같은 대역이 매크로 경로에서는 비어 있지 않음**을 함께 단정 |
| 2 | D-2 — 순회 모듈에 경로 리터럴 0건 · 핸들러가 `rig_paths["fixture_types"]`를 넘긴다 · 신규 경로 상수 0건 | 충족. **오버라이드가 순회를 실제로 이동시킴**을 단정한다(`Patch/OtherTypes`로 바꾸면 그 경로만 조회되고 `bound_source`도 그 경로를 가리킨다) |
| 3 | D-3 — `PRECHK_RIG_SECTIONS` 바이트 동일 · 신설 튜플이 `create_macro`와 무관하게 검사 · 메시지가 섹션 이름을 말하고 풀 판독 실패를 암시하지 않음 | 충족. `create_macro` **False·True 양쪽**에서 같은 결과임을 한 테스트가 순회한다 |
| 4 | `test_prechk_tool.py:895-905`·`:907` 무변경 통과 | 충족 |
| 5 | `test_tools.py:511-522` 정확 10키 무변경 통과 | 충족 — 신규 경로 키 0건 |
| 6 | `_dispatch` **41지점** 전건 통과 = 순회 예외 포착의 기계 판정 | 충족. 기본 `RigPort`는 `Patch/FixtureTypes`에 `RuntimeError`를 던지며 순회가 그것을 분류로 흡수한다 |
| 7 | 트립와이어 갱신 · 보호구역 상수 바이트 동일 · 교차 단정 성립 | **갱신 불필요**(위 별항). 상수 바이트 동일 · 교차 단정 성립 |
| 8 | 스위트 계수가 baseline 이상 | **2887 passed · 5 skipped · 0 failed** = 2869 + 18 |

### M7 — PRESERVE 상시 테스트 · 게이트 (`AC-OVERLAP-019` · `cycle_type=tdd` · 2026-07-30)

#### 착수 전제 확인

| 항목 | 산출 |
|---|---|
| M6 DoD 8항 | 전건 충족(위) — 특히 tools.py 커밋이 이미 있어 hunk 봉쇄가 최종값을 갖는다 |
| baseline | **2887 passed · 5 skipped · 0 failed** (M6 커밋 시점 실측) |

#### 산출

**`server/tests/test_overlap_preserve.py` 23건**(신규). 구현 0건 · 기존 파일 갱신 0건. **선례 파일을 확장하지 않았다** — 그 파일의 변경은 `git diff --numstat` 기준 **0행**이다.

#### 착수 시점 실측값 — 게이트가 고정하는 수치

| 대상 | 실측 |
|---|---|
| PRESERVE 10경로 diff (PRECHK BASE) | **빈 출력**. 같은 명령을 `server/prechk/`에 돌리면 비어 있지 않다(비공허성) |
| 경로 분류 | **파일 7 · 디렉터리 3** — 목록에서 `is_file()`/`is_dir()`로 기계 도출 |
| `tools.py` (PRECHK BASE) | **+412 · −1** · hunk old-start 9개 = `44, 61, 139, 476, 488, 492, 1203, 1551, 1561`. 보호구역 `(247, 251)` · `(537, 582)` 교차 **0건** |
| `server/safety/` (PRECHK BASE) | **정확히 2파일** — `console.py` +30/**−0** · `gate.py` +16/**−1** |
| 그 삭제 1행의 원문 | `    """StateQueryPort implementation riding the gate-audited console link."""` |
| `server/safety/` (본 SPEC BASE) | **빈 출력** — 본 SPEC은 초크포인트를 건드리지 않았다 |
| PRECHK SPEC 문서 (본 SPEC BASE) | **빈 출력**. PRECHK BASE로 돌리면 비어 있지 않다 — 그 대조를 테스트가 같은 자리에서 실행한다 |
| `DESCOPE: ASSUMPTION-27` 접두 행 | **정확히 1건** |
| 본 SPEC이 손댄 `.py` | **11파일** — `git diff --name-only`에서 도출해 ruff에 넘긴다. **(run-audit 정정: 초안이 10으로 적었다. 게이트는 목록을 기계 도출하므로 코드에 10이 박히지는 않았다.)** |

**선례 SHA를 재타이핑하지 않는다.** 초안은 `test_this_file_owns_the_predecessor_base_alone`에서 SONGCUE BASE를 리터럴로 적었고 **그 순간 자기가 금지하는 문자열을 자기 파일에 넣어** 테스트가 자기 자신에서 실패했다. 선례 파일 소스에서 `_RUN_PHASE_BASE`를 정규식으로 읽어 오도록 고쳤다 — 드리프트도 자기참조도 없앤다. **두 상수가 정확히 13 어긋남**(`234 + 13` · `524 + 13`)을 단정으로 고정해 선례 복사를 기계로 막는다.

#### 뮤테이션 6건 — 5건 사망 · 1건은 주입 불가여서 형상을 강화했다

| # | 주입 | 결과 |
|---|---|---|
| **M-32** | PRESERVE diff를 **본 SPEC BASE**로 | **killed** — 범위 형태 단정이 잡는다. 이 뮤테이션이 살아 있으면 게이트가 커밋 직후 영구 통과한다 |
| **M-33** | 보호구역을 선례 상수 `(234, 238)`·`(524, 569)`로 복사 | **killed** |
| **M-34** | PRESERVE 경로에 오타 한 글자(`preview` → `previews`) | **killed** — 2 failed(존재 검사 + 분류 합) |
| **M-36** | 삭제 허용 행 원문을 다른 문장으로 | **killed** |
| **M-37** | 파일/디렉터리 분류를 손으로 3/7 → 4/6 | **killed** — plan-audit가 P1으로 낸 오류와 같은 형태다 |
| **M-35** | safety 삭제 행 **텍스트 단정을 계수만으로 약화** | **주입만으로는 효과가 없다** — 아래 |

**M-35는 뮤테이션 설계가 불완전했다.** 텍스트 단정을 `len(deleted) <= 1`로 약화해도 **현재 삭제가 실제로 그 독스트링 한 줄**이므로 아무것도 실패하지 않는다. 효과를 보려면 `server/safety/gate.py`에서 의미 있는 한 줄을 **함께 삭제해 커밋**해야 하는데 그것은 PRESERVE 위반이며 `git diff BASE..HEAD`가 커밋만 보므로 워킹트리 편집으로는 재현되지 않는다. **그래서 뮤테이션을 억지로 만들지 않고 형상을 강화했다** — 삭제 행이 **구조적으로 독스트링인지**(`"""`로 시작·종료) 함께 단정하고, 그 규칙이 항상 참이 아님을 심은 세 줄(`failed = True` 등)로 보였다. 이제 텍스트 기대치를 약화시켜도 **원문을 모르는 의미 있는 삭제가 여전히 잡힌다.**

#### DoD 10항 — 전건 기계 판정

| # | 조건 | 산출 |
|---|---|---|
| 1 | PRESERVE 10경로 diff가 PRECHK BASE 기준 빈 출력 | 충족 |
| 2 | 범위 인자가 정확히 `95687a0e…..HEAD` 형태이며 본 SPEC BASE가 아니다 | 충족 — argv를 조립해 요소별로 단정하고 본 SPEC BASE 문자열의 부재까지 본다 |
| 3 | 비공허성 — 원소 10 · 각 경로 실재 · 분류를 기계 도출 · 디렉터리 원소가 `/`로 끝난다 | 충족 |
| 4 | hunk 위치 봉쇄 · PRECHK BASE 상대 | 충족 + 교차 술어의 비공허성(경계 두 끝과 그 밖 1행) |
| 5 | safety 파일집합 정확 2 · 삭제 0/≤1 · 그 1행이 독스트링 | 충족 — 원문 대조와 **구조 판정 둘 다** |
| 6 | 선례 파일에 신규 게이트 상수가 들어가지 않았다 | 충족 — 변경 **0행**(트립와이어 갱신이 불필요했으므로 1행보다 강하다) |
| 7 | 트립와이어 판정 — 보호구역 교차 단정이 계속 성립 | 충족 — 선례 파일 20건이 커밋 후 통과 |
| 8 | PRECHK 문서 무변경(본 SPEC BASE) + `DESCOPE:` 1건 | 충족. **왜 이 한 항목만 다른 BASE인지**를 같은 클래스의 다른 테스트가 실측으로 보인다 |
| 9 | ruff check · format --check가 손댄 전 파일에서 통과 | 충족 — 대상 목록을 `git diff --name-only`에서 도출하므로 목록이 낡지 않는다 |
| 10 | 스위트 계수가 baseline 이상 | **2910 passed · 5 skipped · 0 failed** = 2887 + 23 |

### M8 — 종단 통합 (`AC-OVERLAP-021` · `cycle_type=tdd` · 2026-07-30)

#### 착수 전제 확인

| 항목 | 산출 |
|---|---|
| M7 DoD 10항 | 전건 충족(위) |
| `git status --porcelain` | **빈 출력** — 역방향 절차가 워킹트리를 건드리므로 시작 상태가 깨끗해야 한다 |
| baseline | **2910 passed · 5 skipped · 0 failed** (M7 커밋 시점 실측) |

#### 산출

`server/tests/test_prechk_tool.py` **+10건**. 구현 0건 · 기존 테스트 갱신 0건. **라이브 세션 0회** — `AC-OVERLAP-021`이 명문화한 대로 인메모리 리그와 툴 디스패치로 닫았다.

**감사 1:1을 프로덕션 초크포인트로 관통시켰다.** 대역을 손으로 만들지 않고 실제 `SafetyGate`를 세워(`console=` 인메모리 리그 · `audit=AuditLog(tmp_path)`) `gate.state_port`를 툴에 넘겼다. 그 결과 **감사 `state_query` 행 수 = 리그의 `state_calls` 수**이고 순회 경로가 그 집합의 부분집합임을 단정한다. 실패 조회도 1행을 남긴다는 것을 별도로 확인했다 — 타임아웃도 OSC 송신 1건이므로 회계가 새면 안 된다.

**조회 계수를 등호로 고정했다.** 착수 시점에 조회 계수를 고정하는 단정이 저장소 전체에 0건이었으므로(연구 §6.1) `1 + T + ΣM` 등호와 예산 상한 부등호를 **둘 다** 신설했다. 부등호만 두면 조회 1건이 영구히 조용히 늘어난다.

#### `AC-OVERLAP-021` ① 불일치 1건 — 오케스트레이터 접점으로 올린다

**`exact_widths`는 툴 표면에서 산출 불가능하다.** ①은 *"툴을 통해 4개 값 각각이 산출되는 리그가 존재"*를 요구하지만 **출하된 핸들러는 `FootprintPolicy`를 만들지 않는다** — `ASSUMPTION-27`이 부정이라 정확폭 축이 꺼진 채 출하됐고, **본 SPEC의 상계 축이 존재하는 이유가 바로 그것**이다. 그 등급을 툴에서 내려면 기각된 축을 다시 켜는 코드 경로를 신설해야 하며 그것은 `spec.md` §D 범위 밖이다.

| 항목 | 산출 |
|---|---|
| 툴 표면에서 도달 가능한 등급 | **3** — `bound_proves_clear` · `bound_inconclusive` · `not_performed`. 각각 리그를 만들어 디스패치로 확인하고 **세 등급이 서로 다름**을 단정한다 |
| 도달 불가 등급 | **1** — `exact_widths`. 기계 증거: `server/orchestrator/tools.py`의 AST에 `FootprintPolicy(` 호출이 **0건** |
| 그 등급이 죽은 어휘인가 | **아니다** — 판정·리포트 계층에서 산출되며 `AC-OVERLAP-017` ④의 4값 비공허성이 M5에서 충족됐다 |

**이 불일치를 덮지 않고 기록한다.** 형태는 `AC-OVERLAP-021` ③에 대해 `plan.md` §E.2가 정한 접점 3번(*"M8 산출이 산술과 어긋나면 불일치 자체를 기록하고 오케스트레이터에게 후속 판단을 요청한다"*)과 같다. 그리고 이것은 **`bound_inconclusive`를 라이브로 증명할 수 없다**는 기록과 같은 계열이다 — 인수 조건의 전제가 출하 형상과 어긋나는 경우이며, 조건을 충족시키려 형상을 바꾸는 것이 결함이다.

#### 역방향 검증 — 3등급을 섞지 않는다

`plan.md` §B.8의 명령 순서를 그대로 실행했다. 5단계 복원 후 `git status --porcelain`이 빈 출력이다.

**A 등급 — 모듈 부재(약한 증거이며 그렇게 적는다).**

```
ERROR server/tests/test_prechk_footprint.py
ERROR server/tests/test_prechk_patch.py
ERROR server/tests/test_prechk_report.py
ERROR server/tests/test_prechk_verdicts.py
```

원문 2건: `ModuleNotFoundError: No module named 'server.prechk.footprint'` · `ImportError: cannot import name 'OVERLAP_BASIS' from 'server.prechk.verdicts'`. **무엇을 막는지는 말해 주지 않는다.**

**B 등급 — 수집 오류를 넘기고 전량 실행: 19 failed · 80 passed · 4 errors.** `server/tests/test_prechk_tool.py` 단독으로 **19 failed · 57 passed**이며 그 57은 **착수 시점 52건 + C등급 신규 5건**이다. 즉 **그 파일의 신규 24건 중 19건이 수정 전 코드에서 실패하고 5건은 회귀 테스트가 아니다.** **(run-audit 정정: 초안이 *"57은 착수 시점부터 있던 테스트"*로 적었으나 BASE 계수는 52다 — 포함 관계를 등호로 읽은 것이며 M5에서 잡은 부분문자열 함정과 같은 계열이다.)** 클래스별 계수:

| 클래스 | 수정 전 결과 |
|---|---|
| `TestFootprintWalkIsWiredThroughRigPaths` | 7 failed · 1 passed |
| `TestTheOverlapAxisFiresNoCommand` | 1 failed · 1 passed |
| `TestBoundaryProhibitions` | 1 failed · 3 passed |
| `TestEveryGradeThroughTheTool` | **6 failed** |
| `TestAuditAndBudgetEndToEnd` | **4 failed** |

그리고 마일스톤별 뮤테이션이 **무엇을** 막는지 증명한다 — 고정 목록 4건이 전건 killed다: `AC-OVERLAP-003` ⑥(부분집합 상계 거짓 양성, M-1) · `AC-OVERLAP-008` ②(간격 == 상계, M-9) · `AC-OVERLAP-009` ③(유니버스 키잉 붕괴, M-7·M-8) · `AC-OVERLAP-014` ⑥⑦(라벨표 항목 제거 시 import 실패, MUT-A·MUT-A2).

**C 등급 — 수정 전에도 통과하는 것 5건 + PRESERVE 게이트 전량. 회귀 테스트가 아니라고 코드에 라벨했다.**

| 테스트 | 라벨 |
|---|---|
| `TestFootprintWalkIsWiredThroughRigPaths::test_a_missing_section_does_not_discard_the_report` | **INVARIANT GUARD** — 가드를 추가한 것이 호출을 거부하기 시작하지 않게 지킨다 |
| `TestTheOverlapAxisFiresNoCommand::test_the_same_port_is_not_simply_inert` | **NON-VACUITY CONTROL** |
| `TestBoundaryProhibitions::test_the_walk_never_touches_the_execution_port` | **INVARIANT GUARD** |
| `TestBoundaryProhibitions::test_the_prechk_package_never_imports_the_send_surface` | **INVARIANT GUARD** |
| `TestBoundaryProhibitions::test_the_operator_tool_exemption_list_is_unchanged` | **INVARIANT GUARD** |
| `server/tests/test_overlap_preserve.py` **23건 전량** | **INVARIANT GATE** — 모듈 도크스트링에 명시. 수정을 잡는 것은 뮤테이션의 일이고, 이 파일이 잡는 것은 **아무도 재검사하지 않는 경계를 넘는 미래의 편집**이다 |

**A 등급만으로 규율 16을 충족했다고 적지 않는다.** 선행 SPEC의 P1 4건은 2721개가 전부 통과하는 상태에서 살아 있었고 그것을 잡은 것은 존재 확인이 아니라 뮤테이션이었다. 본 run-phase의 뮤테이션 총계는 **36건 주입 · 33건 즉사 · 3건이 1회차 생존해 테스트를 고쳤다**(M-5 · M-21 · M-22) · **1건은 주입이 PRESERVE 위반을 요구해 형상 강화로 대체했다**(M-35).

#### DoD 6항 — 전건 기계 판정

| # | 조건 | 산출 |
|---|---|---|
| 1 | 툴을 통해 4값 각각 산출 · 페이로드가 스키마 정본과 일치 | **3값 충족 · 1값은 출하 형상에서 도달 불가**(위 별항). 도달 가능한 세 등급 전부에서 신규 최상위 키의 **정확 키집합**이 유지됨을 단정한다 |
| 2 | 착수 시점 `precheck_patch` 테스트 전건 통과(=순회 예외 포착) | 충족 — 역방향 실행이 그 57건을 분리해 보여 준다 |
| 3 | 조회 계수가 예산 상한을 넘지 않는다 | 충족 — **등호와 부등호 둘 다** 신설 |
| 4 | 감사 로그에 순회 조회 전건 기록 — 조회 1건 = 감사 1건 | 충족 — 실제 `SafetyGate`를 관통시켜 등호로 단정. 실패 조회도 1행 |
| 5 | 스위트 전체 통과 · 계수가 baseline 이상 | **2920 passed · 5 skipped · 0 failed** = 2910 + 10 |
| 6 | 역방향 절차 실행·기록 · 통과하는 테스트를 회귀 테스트가 아니라고 코드에 명시 | 충족(위) |

## §5 Run-phase Audit-Ready Signal

```yaml
run_status: audit-ready
run_complete_at: 2026-07-30
base_sha: 85a4b2389003cb61b0ab72eb4aa8d6b2ff90b94a
baseline_at_entry: "2758 passed · 5 skipped · 0 failed (M0 착수 직전 직접 실측)"
suite_at_exit: "2920 passed · 5 skipped · 0 failed"
tests_added: 162            # 2920 − 2758. 마일스톤별: M1 4 · M2 35 · M3 41 · M4 21 · M5 10 · M6 18 · M7 23 · M8 10 — 합이 정확히 162이며 보정항이 필요 없다. (run-audit 정정: 초안이 M6를 26으로 적어 합이 170이 되자 그 초과 8을 "M4·M5가 갱신·재배치한 것"으로 설명했다. M4·M5는 실측과 정확히 일치하고 재배치는 0건이며, 초과분 전량이 M6 한 행의 오기였다 — 재측정 대신 서사로 봉합한 것이 이 SPEC 자신의 규율 위반이다.)
milestones_complete: 9      # M0~M8
live_sessions: 0            # 계획대로. AC-OVERLAP-021이 라이브 불요를 명문화했다
code_files_new: 1           # server/prechk/footprint.py (395행)
test_files_new: 2           # server/tests/test_prechk_footprint.py · server/tests/test_overlap_preserve.py
code_files_changed: 4       # tools.py · prechk/{patch,report,verdicts}.py
preserve_violations: 0      # PRESERVE 10경로 diff(PRECHK BASE) 빈 출력 · server/safety/ diff(본 SPEC BASE) 빈 출력
precedent_file_changes: 0   # server/tests/test_songcue_bundle.py — 트립와이어 갱신이 불필요했다(M6 별항)
prechk_docs_changes: 0      # .moai/specs/SPEC-COPILOT-PRECHK-001/ diff(본 SPEC BASE) 빈 출력
assumptions_closed: 1       # ASSUMPTION-34 (GO) — M0
assumptions_skipped: 4      # ASSUMPTION-31 · 32 · 33 · 35 (관측 없이 닫히지 않는다)
prefix_lines: 5             # GO: 1 · SKIP: 4 · DESCOPE: 0 · REOPEN: 0
mutations_injected: 39      # §4 표 40행 = 주입 39 + 주입 불가 1. M-31은 결번이며 MUT-A·A2·B·C를 포함해 고유 ID 40
mutations_killed: 36        # 마일스톤 헤더 합 4+5+6+6+4+6+5. 36 killed + 3 생존 = 39 주입
mutations_survived_first_pass: 3   # M-5 · M-21 · M-22 — 전건 테스트를 고쳐 닫았다
mutations_not_injectable: 1        # M-35 — 주입이 PRESERVE 위반을 요구해 형상 강화로 대체
reverse_verification: "실행 완료 — A등급 수집 오류 4파일 · B등급 19 failed(신규 툴 테스트 전량) · C등급 5 + PRESERVE 게이트 23건을 코드에 라벨"
ac_satisfied: 20            # AC-OVERLAP-001~021 중 20건
ac_partially_satisfied: 1   # AC-OVERLAP-021 ① — 툴 표면에서 3/4 등급만 도달 가능(아래)
deviations:
  - "**`AC-OVERLAP-021` ① — `exact_widths`는 툴 표면에서 도달 불가능하다.** 출하된 핸들러가 `FootprintPolicy`를 만들지 않으며(AST로 `FootprintPolicy(` 호출 0건 확인) 그 이유는 `ASSUMPTION-27` 부정으로 정확폭 축이 꺼진 채 출하됐다는 것이다 — **본 SPEC의 상계 축이 존재하는 이유가 바로 그것**이다. 그 등급을 툴에서 내려면 기각된 축을 다시 켜는 경로를 신설해야 하고 그것은 `spec.md` §D 범위 밖이다. **죽은 어휘는 아니다** — 판정·리포트 계층에서 산출되며 `AC-OVERLAP-017` ④의 4값 비공허성이 M5에서 충족됐다. 오케스트레이터 접점으로 올린다."
  - "**`AC-OVERLAP-019` ⑦의 *'트립와이어가 갱신되고'*는 전제가 성립하지 않았다.** M6의 tools.py 편집 전량이 선행 SPEC이 이미 연 hunk 영역 안에 떨어져 old-side 경계가 움직이지 않았다(실측 대조). 그 항의 실질 불변식(보호구역 교차 단정 계속 성립)은 유지되며 선례 파일은 **0행 변경**이라 ⑥의 *'1행에 한정'*보다 강하다. **갱신하지 않은 것을 갱신했다고 적지 않는다.**"
  - "**D-3의 섹션 가드가 오류를 내지 않는다.** 별도 상수·분기 밖·이름으로 말함은 전건 집행됐으나 누락을 **호출 거부**로 만들 수 없었다 — 매크로 가드 메시지를 고정한 두 기존 테스트가 그 오버라이드를 쓰며, 거부는 이 툴의 존재 이유인 픽스처 재고를 버린다. 리포트에 담고 등급을 `not_performed`로 낸다(M6 별항)."
  - "**순회에 `sibling_answered` 파라미터를 추가했다.** 설계 슬롯 C가 전제한 *'형제가 답했다'*를 순회는 자기 안에서 알 수 없고 프로덕션이 두 실패를 같은 예외로 던지므로 호출자가 넘긴다. 없으면 툴 경로의 분류가 항상 `console_unreachable`이 되어 설정 결함을 운영 조건으로 보고한다(결함 계열 1)."
corrections_to_own_tests: 4
  # M2 M-5(예산 소진 후 부분 폭) · M3 유니버스 리그가 붕괴해도 답이 안 바뀜 · M4 최약 등급 규칙에 맞춘 1건 · M5 M-21·M-22(대조에 순회 없음 · 모드 수 단일)
known_gaps:
  - "**`ruff check server/`가 착수 시점부터 3건 실패한다** — `server/safety/console.py:292`·`:346`(PRESERVE이므로 고치면 위반) · `server/tests/test_web_dash.py:523`. BASE 원본을 꺼내 같은 3건임을 확인했다. `AC-OVERLAP-019` ⑨의 판정 범위는 손댄 파일이며 그 **11파일**은 `check`·`format --check` 전건 통과한다."
  - "**`server/tests/test_web_launcher.py`의 `TestSidecarSelfReap` **클래스 전체**가 간헐 실패한다** — 사이드카 서브프로세스가 벽시계 데드라인 안에 `status.json`을 내지 못하면 실패하며 머신 부하에 걸린다. 단독 실행 71건 전건 통과. 본 SPEC은 런처 계층을 **0파일** 건드린다. **(run-audit 폐쇄 정정: 초안이 `test_orphaned_sidecar_reaps_the_group_without_a_pipe` 1건으로 좁혔으나, P1 폐쇄 검증 중 같은 클래스의 `test_pipe_eof_reaps_the_group_and_frees_the_ports`가 같은 사유로 실패했다 — 단일 테스트가 아니라 클래스 단위 성질이다.)**"
  - "**`ASSUMPTION-31` · `ASSUMPTION-32` · `ASSUMPTION-33`이 여전히 열려 있고 셋 다 다른 쇼파일을 요구한다.** 본 SPEC은 셋 중 하나라도 거짓이면 상계가 과대·과소평가되는 형상을 **한정 표현으로** 출하했다 — `bound_proves_clear`는 항상 *'열거된 모드 N개에 한정한 판정'*을 함께 말한다. 발화 억제가 아니라 한정이 정직한 형상인 이유는 `AC-OVERLAP-020` ④의 주석에 있다."
  - "**`_SELECTION_OPERAND`(PRECHK BASE 246) 보호 공백은 그대로 남는다.** plan-phase가 `known_gaps`에 신설한 그대로이며 본 SPEC은 `tools.py` 보호구역을 소유하지 않으므로 범위를 넓히지 않았다."
  - "**절단 계수 비교의 4번째 사본을 만들었고 수렴하지 않았다**(D-8). `_listing_is_whole`과 `_declared_child_count`가 그 사본이며 **의도적으로 서로 다른 정책**이다. 수렴은 별도 리팩터 SPEC의 일이다."
  - "**상속된 스키마 드리프트 2건을 정정하지 않았다** — `spec.md` §D가 명시적 Out of Scope로 뒀다."
next: "**run-audit 1회차 완료 — FAIL 0.714 / 기준선 0.85 · 지적 32건(P1 6 · P2 14 · P3 12). 전문은 §7.** 권고했던 감사가 실제로 값을 냈다: **P1 6건 전부가 2920개 스위트가 전건 통과하는 상태에서 살아 있었고**, 그중 5건은 코드가 옳고 테스트가 못 재는 형태이며 2건(P1-1 · P1-6)은 출하 코드 결함이다. 특히 **P1-1은 미관측 픽스처가 등급에 기여하지 않아 불완전 판독 리그를 `bound_proves_clear`로 찍는다** — `CONTRACT.md` D-4가 결함으로 명명한 형상이자 `spec.md` §A 제약 4가 *유일하게 가능한 오류*라고 적은 **거짓 '겹침 없음 증명'** 그 자체다. 불일치 4건은 §7에서 전건 처분했다(①은 근거를 교체해 인수 조건을 좁힘 · ②는 표제 정정 · ③은 애초에 불일치가 아님 · ④는 슬롯 C 안이며 기본값만 조건부). **다음은 sync-phase가 아니라 P1 6건의 폐쇄다** — §7 말미가 2회차 조건을 적는다."
```

## §6 다음 세션 착수 키트 (2026-07-30)

> **§5가 무엇을 할지를 적었다. 이 절은 바로 착수할 수 있게 재발견 비용을 0으로 만든다** — 검증 커맨드와 기대 출력, 산출물 인벤토리, 감사 브리프, 그리고 하지 말아야 할 것.
>
> **`.moai/state/`는 `.gitignore` 대상이므로 커밋되지 않는다.** `.moai/state/handoff/pending.json`에 같은 내용의 기계 판독용 사본이 있으나 **클론에서 살아남는 것은 본 절이며 충돌 시 본 절이 이긴다**(`CLAUDE.md` §5 "Resuming Work").

### §6.1 한 문단

**run-audit(FAIL 0.714)가 낸 P1 6건을 전건 닫았고 방어를 재주입으로 확인했다(§7).** 스위트 **2933 passed · 5 skipped · 0 failed** · 손댄 파일 ruff clean · PRESERVE 게이트 23 passed. **다음은 sync-phase다** — `acceptance.md` 문언 4건과 P2·P3 잔여를 정본 상태 전이와 같은 커밋에 담는다. 사용자 승인이 필요한 열린 접점은 **0건**이고, 라이브 콘솔 접근은 **필요하지 않다**.

### §6.2 착수 즉시 돌릴 것 — 기대 출력을 병기한다

```sh
git branch --show-current                    # feature/SPEC-COPILOT-OVERLAP-001
git status --porcelain                       # 빈 출력
git log --oneline -3                         # 최신 커밋이 docs(overlap) 계열이면 run-phase 완결 지점이다.
                                             #  SHA를 여기 적지 않는다 — 이 절을 쓰는 커밋이 그 값을
                                             #  바꾸므로 적는 순간 거짓이 된다. 판정은 아래 스위트 계수로 한다.
find server -name __pycache__ -type d -exec rm -rf {} + ; uv run pytest server/tests/ -q
                                             # 2920 passed · 5 skipped · 0 failed
uv run pytest server/tests/test_overlap_preserve.py -q          # 23 passed
uv run pytest server/tests/test_prechk_footprint.py -q          # 52 passed
uv run pytest server/tests/test_prechk_patch.py -q              # 94 passed
uv run pytest server/tests/test_prechk_report.py -q             # 49 passed
uv run pytest server/tests/test_prechk_tool.py -q               # 76 passed
uv run pytest server/tests/test_prechk_verdicts.py -q           #  8 passed
```

**스위트가 2933이 아니면 먼저 그 차이를 설명하라.** 단 `server/tests/test_web_launcher.py`의 **`TestSidecarSelfReap` 클래스는 간헐 실패한다** — 사이드카가 벽시계 데드라인 안에 `status.json`을 내지 못하는 부하 의존 실패이며, 그 파일 단독 실행에서 71건 전건 통과하고 본 SPEC은 런처 계층을 0파일 건드렸다(§4 M3 절의 별항 · §5 `known_gaps`). **그 클래스 밖의 다른 실패는 조사 대상이다.**

**게이트 6종은 `test_overlap_preserve.py` 23건이 상시 판정하므로 손으로 돌릴 필요가 없다.** 손으로 확인하고 싶으면 §0의 *"인수인계가 온전한지 기계로 확인하는 법"* 블록이 그 6종을 그대로 담고 있다.

### §6.3 산출물 인벤토리 — 무엇이 어디에 있나

| 파일 | 성격 | 행수(±) |
|---|---|---|
| `server/prechk/footprint.py` | **신규** — 3단 순회 · 완전성 술어 2종 · 예산 · 실패 분류 · 간격 산수 · 술어 `간격 < 상계` | +395 |
| `server/tests/test_overlap_preserve.py` | **신규** — PRESERVE 상시 게이트 23건. **PRECHK BASE를 단독 소유한다** | +369 |
| `server/tests/test_prechk_footprint.py` | **신규** — 순회·간격·상계 52건 | +719 |
| `server/prechk/patch.py` | 갱신 — `OverlapBasis` 7키 · `_overlap_basis` · 주소 하한 · 그룹핑 추출 | +275 −9 |
| `server/prechk/report.py` | 갱신 — 가드 루프 구조 변경 · `OVERLAP_BASIS_LABELS` · 요약 배선 | +47 −15 |
| `server/prechk/verdicts.py` | 갱신 — `OVERLAP_BASIS` · 레지스트리 맨 끝 append | +19 −1 |
| `server/orchestrator/tools.py` | 갱신 — 섹션 가드 신설 · 예산 상한 · 순회 배선 | +58 −3 |
| `server/tests/test_prechk_{patch,report,tool,verdicts}.py` | 갱신 — 추가만 | +1263 −2 |

**커밋 수와 증감은 값으로 적지 않는다** — `git rev-list --count 85a4b23..HEAD`와 `git diff --shortstat 85a4b23..HEAD`로 산출한다. **§6.2가 HEAD SHA에 대해 고른 처방과 같다**: 이 절을 쓰는 커밋이 그 값을 바꾸므로 적는 순간 거짓이 된다. **(run-audit 정정: 초안이 `커밋 16개 · 20파일 · +6697 −30`을 적었고 그 세 값은 3커밋 전 `807119f`에서 **동시에** 정확했다 — 즉 측정 시점과 기록 시점이 갈렸다. 파일 수 20만 살아남아 스팟 체크로는 드러나지 않았다.)**

### §6.4 run-audit 브리프 — 감사에게 그대로 넘길 것

**감사 대상**: 오케스트레이터가 고정한 SHA 시점의 run-phase이며 그 값은 §F.2가 기록한다. **SHA를 여기 적지 않는다** — §6.2와 같은 이유다. 정본은 `progress.md` §4(마일스톤별 증거) · §5(신호) · **§7(감사 결과)**.

**감사가 먼저 볼 4건** — 전부 §5 `deviations`에 원문이 있다:

| # | 불일치 | 물어야 할 것 |
|---|---|---|
| 1 | `AC-OVERLAP-021` ① — `exact_widths`가 **툴 표면에서 도달 불가능**(핸들러가 `FootprintPolicy`를 만들지 않으며 AST로 0건 확인) | 인수 조건을 좁히는 것이 옳은가, 아니면 기각된 축을 다시 켜는 것이 옳은가. **후자는 `spec.md` §D 범위 밖이다** |
| 2 | `AC-OVERLAP-019` ⑦ — *"트립와이어가 갱신되고"*의 **전제가 성립하지 않았다**(old-side 경계 9개 바이트 동일 · 선례 파일 0행 변경) | 그 항의 실질 불변식만 남기고 표제를 고치는 것이 옳은가 |
| 3 | D-3 섹션 가드가 **오류를 내지 않는다**(리포트에 담고 등급을 `not_performed`로) | D-3의 세 요건은 충족됐다. 거부가 아닌 형태를 수용하는가 |
| 4 | 순회에 **`sibling_answered` 파라미터 추가** | 설계 슬롯 C를 벗어나는가, 아니면 슬롯 C가 전제한 사실을 명시적으로 만든 것인가 |

**감사가 재현할 수 있는 계수**(전부 §4에 실측 원문이 있다): 스위트 2758 → 2920 · 마일스톤별 순증 · 뮤테이션 36 주입/33 killed/3 생존/1 주입 불가 · 역방향 검증 A·B·C 3등급 · PRESERVE 게이트 6종 · 접두 행 5 · 어휘 6축.

**감사가 오탐으로 낼 수 있는 것 — 미리 선언한다:**

1. *"`bound_inconclusive`가 라이브로 검증되지 않았다"* — **원리적으로 불가능하다.** 현 쇼파일 17 인접쌍 전부가 상계를 통과해 발동 입력이 0건이며 합성 인메모리 리그만이 덮는다(`research.md` §3.3).
2. *"`ASSUMPTION-31`·`32`·`33`이 열려 있는데 `bound_proves_clear`를 낸다"* — **의도된 형상이다.** 관측 불가 전제에 대한 정직한 형상은 발화 억제가 아니라 **한정 표현**이며(`AC-OVERLAP-020` ④의 주석) 그 등급은 항상 *"열거된 모드 N개에 한정한 판정"*을 함께 말한다.
3. *"`ruff check server/`가 실패한다"* — **착수 시점부터 3건 실패하며 그중 둘이 PRESERVE 파일이다.** BASE 원본을 꺼내 같은 3건임을 확인했고 판정 범위는 손댄 11파일이다.
4. *"절단 계수 비교가 4번째 사본이다"* — **D-8이 수렴을 명시적으로 금지했다.** 세 기존 구현의 `childCount` 부재·0 정책이 서로 달라 통합이 `.moai/specs/SPEC-COPILOT-PRECHK-001/acceptance.md:313`(§D)와 충돌한다. 수렴은 별도 리팩터 SPEC의 일이다.

### §6.5 그다음 — sync-phase에서 할 일

감사와 불일치 처분이 끝난 뒤다. **먼저 하지 마라.**

1. `CHANGELOG.md` `[Unreleased]`의 OVERLAP 항목은 **이미 run-phase 완결로 갱신돼 있다** — sync는 감사 결과를 덧붙인다.
2. `spec.md`의 `status`는 현재 **`in-progress`**다. `completed`는 머지 시점의 값이다(선행 SPEC 9건의 관례).
3. **plan-phase 산출물 6종을 고치지 마라** — 그 시점의 판단 기록이다. 어긋남은 §4·§5가 정본이다.
4. PR을 올리면 **`gh pr checks`가 0건인 저장소**임을 기억하라 — 머지 전 유일한 관문이 사람 리뷰이며, PRECHK는 그 자리에서 독립 코드 리뷰 2건을 병렬로 붙여 **P1 4건을 머지 전에 잡았다.** 그 P1 넷 다 **2721개 스위트가 전건 통과하는 상태에서 살아 있었다.**

### §6.6 절대 하지 말 것

1. **`server/safety/**`를 건드리지 마라.** `ASSUMPTION-34`가 `GO`이므로 본 SPEC은 신규 예외 0지점으로 성립했고, `test_overlap_preserve.py`가 본 SPEC BASE 기준 빈 출력을 상시 단정한다.
2. **`server/tests/test_songcue_bundle.py`를 확장하지 마라.** 그 파일은 SONGCUE BASE 상대이고 신규 게이트는 PRECHK BASE 상대다 — 한 모듈에 두 BASE를 섞으면 게이트가 **엉뚱한 곳을 지키면서 통과한다**(두 상수가 정확히 13 어긋난다).
3. **PRESERVE diff를 본 SPEC BASE로 "단순화"하지 마라.** 커밋 직후 항상 빈 출력이라 게이트가 통째로 무력해진다. 그 뮤테이션(M-32)이 실제로 killed된다.
4. **`PRECHK_RIG_SECTIONS`에 `"fixture_types"`를 추가하지 마라.** `create_macro` 값에 따라 다른 결과가 되고 기존 테스트 3건이 죽는다(M-25).
5. **요약 라벨 단정을 단순 포함형으로 쓰지 마라.** §0 함정 표 아래의 부분문자열 충돌 때문에 등급이 인쇄되지 않아도 통과한다.
6. **뮤테이션 없이 "검증됐다"고 적지 마라.** 이번 run-phase에서 뮤테이션 3건이 1회차에 살아남았고 **셋 다 코드가 옳고 테스트가 못 재고 있었다.**

## §7 Run-audit 1회차 — FAIL 0.714 → 지적 32건 (2026-07-31)

독립 감사자(작성자가 아닌 주체·plan/run 세션과 다른 세션)가 **`a61cf11efc56d6736d5eccac97416f26ea85e3a9`** 시점의 run-phase를 채점했다. 집행 형태는 **폭 7 팬아웃**이며 근거·격리 실측은 §F.2다.

**Verdict: FAIL · 가중합 0.714 / 기준선 0.85 · 지적 32건(P1 6 · P2 14 · P3 12).**

| 축 | 가중치 | 점수 | 감사 요지 |
|---|---:|---:|---|
| 인용 정확성 | 20% | 0.72 | **좌표는 13/13 무드리프트**(선례는 17/18 드리프트)인데 **계수에 P2가 6건** 몰렸다. 병인이 하나다 — *측정 시점 ≠ 기록 시점* |
| **교차 정합** | **30%** | **0.68** | **P1 2건이 여기다.** 그중 하나는 출하 코드가 `CONTRACT.md` D-4를 어기고 **거짓 "겹침 없음 증명"**을 낸다 — 본 SPEC이 막으려던 **유일한 오류 방향**(`spec.md` §A 제약 4) |
| 요구-AC 정합 | 15% | 0.76 | 계수 전건 재현(18·21·18·삼자 21). 감점은 인수 조건 3건이 **집행 불가·공허·형태 불일치**인 것 |
| AC 기계검증성 | 15% | 0.62 | **뮤테이션 63건 재주입 → 9건 생존 · 고유 결함 지점 8곳 · P1 4건.** 게이트가 목표 결함을 못 잡는 지점이 5곳 |
| 증거 등급 규율 | 10% | 0.78 | **자기 관측 `[실측]` 0건 — 이 축의 핵심 실패모드는 청결하다**(16건 전수 분류). 감점은 run-phase에서 등급 태그가 소멸한 것 |
| 범위 경계 | 5% | 0.92 | **모범적.** PRESERVE 6게이트 · 두 BASE 비교환성 양방향 수치 · 7/3 기계 도출 · 독스트링 단정 5중 |
| 미결 은닉 | 5% | 0.70 | 자백 10건은 강한 긍정. 감점은 **자백 자신의 계수가 틀린 것**과 M6 불일치를 재측정 없이 **서사로 봉합**한 것 |

**감사가 재현해 정확하다고 확인한 것**: 스위트 2920·5·0(89.85s, 플레이크 미발생) · 파일별 6/6(23·52·94·49·76·8) · `tests_added` 162와 **실측 마일스톤 합 162의 일치** · REQ 18 · AC 21 · 역추적 18/18 · 마일스톤별 AC 배정 21(삼자 프로그램 대조) · 접두 행 5(GO 1·SKIP 4) · BASE 3종과 보호구역 **+13 오프셋이 시작·종점 4/4** · PRESERVE 10경로 빈 출력 · PRECHK 기준 2887 vs 본 SPEC 기준 빈 출력 · safety 삭제 1행이 **정말로 독스트링** · `_dispatch` 41지점 · 파일별 행 델타 8/8 · `ruff` 3건이 BASE와 바이트 동일.

### P1 6건 — 전부 "스위트가 그린인 채로 살아 있다"

| # | 지적 | 근거 |
|---|---|---|
| **P1-1** | **불완전 판독 리그가 `bound_proves_clear`로 찍힌다.** `_overlap_basis`의 `NOT_PERFORMED` 절이 `assessed`(=**관측된** 픽스처)만 훑어 미관측 개체가 등급에 기여하지 않는다 | `childCount=40` 선언·18개 열거 리그 실측 → `missing_count=22` · `not_assessed=22`인데 `basis=bound_proves_clear`. 한정 문구는 **모드 집합만** 말하고 못 본 22건은 언급하지 않는다. D-4 정직성 제약 1이 이 형상을 **결함으로 명명**한다. `tools.py:1467`이 `completeness` 게이트 없이 호출하므로 **프로덕션 도달 가능**. 계측 census: `bound_AND_incomplete_inventory = 0` — **테스트 0건** |
| **P1-2** | **`AC-OVERLAP-010` ①②의 게이트가 대상 결함을 못 잡는다** | 명명된 테스트가 `address_gaps`에 **파이썬 집합 리터럴**을 먹여 공유 시작점이 원리적으로 들어갈 수 없다 → 항진명제. 상계 축이 키 집합 대신 픽스처별 주소 목록을 걷게 하는 뮤테이션이 **271 passed 전건 통과**. 뮤턴트는 사용자 문자열에 **간격 0**을 인쇄하고 같은 중복을 두 축이 이중 보고한다 — ①②가 금지하는 바로 그것 |
| **P1-3** | **D-6 가드가 1줄 우회에 무방비 — `AC-OVERLAP-014` ⑦ 무효화** | 레지스트리 순회는 **그대로 둔 채** 루프 첫 줄에 허용목록 + `continue`를 넣으면 **1081 passed 전건 통과**. 형태 단정이 `For.iter`만 보므로 `frozenset`을 이름에 대입하면 빠져나간다. **대조 실증**: 뮤턴트에서 라벨 없는 5번째 코드 추가 → import **성공**(HEAD에서는 `UnknownVerdict`). D-6이 없애려던 무증상 상태가 그대로 복원된다 |
| **P1-4** | **열거 불완전 무효화 3지점이 무단정** — `footprint.py:212`(슬롯 `i` 부재) · `:305`(모드단) · `:318`(`childCount` 판독 실패) | 셋 다 **0 failed**(302·광역 1081). 셋 다 `research.md` §4.1 함정을 정확히 재현한다 — 참 상계 31, 산출 29, 간격 30 → **`bound_proves_clear`**. `_listing_is_whole` 계열 2지점만 게이트가 있다 |
| **P1-5** | **예산 상한 단정이 자기참조** | `assert len(walk_calls) <= tools_module.PRECHK_FOOTPRINT_QUERY_CAP` ×2 — 측정값을 **상수 자신과** 비교한다. `40 → 1000000000`으로 바꿔도 **1081 passed**. §4 M8 DoD 3의 *"등호와 부등호 둘 다"* 중 부등호 절반이 **실패 불가능**하다 |
| **P1-6** | **픽스처 0개 리그의 폴백이 무단정** | `_weakest`의 빈집합 폴백을 `NOT_PERFORMED → EXACT_WIDTHS`로 뒤집어도 **1081 passed**. 뒤집힌 상태에서 비교를 0건 수행한 리그에 *"실제 점유폭으로 판정 · 한정이 없다"*를 인쇄한다 — 결함 계열 1 |

**P1 6건 중 2건(P1-1·P1-6)은 출하 코드 결함이고 4건은 게이트 결함이다.** P1-1을 제외한 5건은 코드가 옳고 **테스트가 못 재고 있다** — §6.6 6항이 예고한 바로 그 형태이며, 이번에는 감사가 그것을 5곳에서 찾았다.

### P2 14건 — 요지

계수 6건이 한 병인을 공유한다: **§6.3의 `커밋 16개 · +6697`이 3커밋 전(`807119f`)에서 측정됐고**(두 값이 그 커밋과 **동시에** 정확 일치), §6.3의 footprint `48건`이 M4 시점 값이며(참값 52 · **12행 위 §6.2가 52라고 적는다**), §4 M6 산출 `+22건`이 실측 **+14**이고 그 오기가 §5의 `M6 26`으로 흘러 *"170 중 8건은 M4·M5가 갱신·재배치"*라는 **재측정 없는 서사**로 봉합됐으며(M4·M5는 실측과 정확히 일치해 떼어낼 8건이 없다 · **DoD 8의 인쇄된 등식 `2887 = 2869 + 26`이 산술적으로 거짓**), *"손댄 10파일"*이 3곳에서 실측 **11**이고, *"57은 착수 시점부터 있던 테스트"*가 실측 **52**이며, **뮤테이션 총계 `36/33`이 §4 자신의 열거 `40/36`과 어긋나고 어떤 셈법으로도 도달하지 않는다**(§6.4가 감사에게 재현을 권한 계수다).

**가장 값나가는 관측**: `a61cf11`은 자기참조 위험을 **정확히 진단하고 §6.2의 HEAD SHA를 지운 커밋**인데, 12행 아래 §6.3의 동일 취약 필드 셋과 §6.4의 SHA를 그대로 뒀다. **규칙 부재가 아니라 규칙의 국소 적용**이 병인이다.

나머지 P2 8건: `AC-OVERLAP-014` ⑨가 **공허하다**(금지 토큰 스캐너 3종이 어휘의 **값**을 한 번도 보지 않는다 — 주장 자체는 13토큰 수동 대조로 **참**이나 측정된 적이 없다) · `AC-OVERLAP-018` ①이 명시한 *"AST 식별자 스캔"*이 실제로는 **3-needle 부분문자열 스캔**이며 라우트를 세지 않는다(심은 라우트가 통과함을 실증) · `AC-OVERLAP-017` ②의 *"판정 계층이 한국어를 만들지 않는다"*가 `CONTRACT.md` R-8(*"`observation_note`는 순한국어로 쓴다"*)과 **같은 정본 묶음 안에서 충족 불가능**하다 · `"한정" in summary` 단정이 한정과 **한정의 명시적 부정**을 구별하지 못한다 · `bound_slots`가 비어 있지 않은데 *"겹침 비교를 수행하지 않았다"*를 인쇄한다 · `AC-OVERLAP-009` ②·`design.md` 리그 12의 **10+9→17 형상이 미구현**(4+3 대역) · `CONTRACT.md` D-3이 *"깨진다"*고 명명한 두 테스트가 **실제로는 깨지지 않는다**(부분문자열 단정) · **`acceptance.md` §D가 실재하지 않는데 4곳이 인용한다**(아래).

#### 감사가 새로 찾은 끊어진 앵커 — `acceptance.md` §D

`CONTRACT.md` D-8 · `plan.md` §E · `progress.md` §5 `known_gaps` ⑤ · §6.4 오탐 선언 ④가 *"`acceptance.md` §D의 **zero fixtures는 유효한 리그**"*를 인용한다. **본 SPEC의 `acceptance.md`에 §D는 없다** — 절은 `AC-OVERLAP-001`~`021` · 역추적표 · 계수뿐이다. 실제 출처는 **`.moai/specs/SPEC-COPILOT-PRECHK-001/acceptance.md:313`**(§D 퇴화·경계 케이스, *"픽스처 **0개** | 거부가 아니라 **정상**이다"*)이며, **타 SPEC 인용에 요구되는 전체 경로 접두가 빠졌다.** 내용은 실재하므로 D-8의 결론은 유효하고 오탐 선언 ④도 유지된다 — **앵커만 끊어졌다.** plan-audit P1-3(*"`plan.md`가 존재하지 않는 `progress.md` §F를 지목한다"*)와 같은 계열이 **다른 문서 쌍에서 재발**했고, 이번에는 동명 파일이 같은 SPEC 안에 실재해 더 조용히 오해석된다.

### 오탐 선언 4건 — 전건 유지되며 그중 3건은 반증을 시도한 뒤 유지됐다

| # | 선언 | 감사 판정 |
|---|---|---|
| 1 | `bound_inconclusive` 라이브 미검증 | **유지.** 합성 리그로 실제 산출됨을 확인했고 그 등급을 툴 표면까지 미는 테스트가 실재한다. 뮤테이션 4건이 그 경로로 죽었다 |
| 2 | 열린 전제 위의 `bound_proves_clear` | **유지.** 한정 표현이 **기계로 강제**된다 — note 비우기 7건 · 정확폭에 번지게 하기 1건 · 모드 수 삭제 2건 실패 |
| 3 | `ruff check server/` 실패 | **유지, 바이트 동일로 확인.** HEAD와 BASE 트리 각각 `Found 3 errors` 동일 3좌표 · 둘이 PRESERVE. **손댄 11파일은 `check`·`format --check` 전건 통과** |
| 4 | 절단 계수 비교 4번째 사본 | **유지.** 3구현의 정책 상이를 원문 확인, 두 술어 분리를 뮤테이션으로 확증(3단에 계수 비교 주입 → 18건 실패). **단 인용 앵커가 끊어졌다**(위) |

**선언을 무비판 수용하지 않았다** — ①은 실제 산출로, ②는 뮤테이션 3종으로, ③은 BASE 트리 대조로, ④는 원문과 뮤테이션으로 각각 검증한 뒤 유지했다.

### 불일치 4건의 처분 — 오케스트레이터가 판단한다

> §6.4가 감사에게 넘긴 4건이다. 슬라이스는 **전제만 측정**했고 처분은 여기서 한다. **네 건 모두에서 작성자의 서술이 한 대목씩 부정확했고, 그 부정확이 처분 방향을 바꾼 것은 1건이다.**

**① `AC-OVERLAP-021` ① — 인수 조건을 좁힌다. 단 작성자가 댄 근거로는 아니다.**
작성자는 *"기각된 축을 켜는 것은 `spec.md` §D 범위 밖"*을 근거로 삼았다. **그 근거는 §D 원문이 뒷받침하지 않는다** — §D가 범위 밖으로 둔 것은 *"픽스처 → 점유폭 **조인** 복원"*이지 *"정확폭 축 재활성화"*가 아니고, `FootprintPolicy` 독스트링은 슬롯 키가 **기각된 조인을 요구하지 않는다**고 적는다. 근거를 **`REQ-OVERLAP-013`이 `[Option]`이라는 사실**로 교체한다 — *"**Where** 슬롯별 정확한 폭이 **주어지면**"*이므로 어떤 요구도 툴이 폭을 **공급**할 의무를 지우지 않는다. `AC-OVERLAP-021` ①이 4값 전부의 툴 도달을 요구한 것은 **지배 요구보다 강한 과잉 명세**이며, 그것이 인수 조건 쪽의 결함이다(`[교훈] 인수 조건의 전제가 출하 형상과 모순될 수 있다`). **처분**: ①을 *"툴을 통해 3값이 산출되고, `exact_widths`는 호출자가 폭을 공급할 때만 도달하며 프로덕션 호출자는 공급하지 않는다"*로 좁힌다. **축을 켜지 않는다**(신규 범위). 두 가지를 함께 고친다 — (a) 불일치 문장의 *"핸들러가 `FootprintPolicy`를 만들지 않으며"*는 **`tools.py` 소스 한정 명제**다. 핸들러 **경로**는 `patch.py:637`에서 기본 정책(`enabled=False`)을 실제로 만든다. 정확한 사실은 *"핸들러가 폭을 **주입하지 않는다**"*이다. (b) 도달 불가는 툴 표면이 아니라 **프로덕션 전역**이다(`evaluate_patch`의 프로덕션 호출자가 `tools.py:1467` 하나뿐이고 정책을 넘기지 않는다) — 작성자 주장보다 **강하다**. 그리고 *"슬롯 키 폭을 조인 없이 얻는 경로가 실재하는가"*를 **`[미확정]`으로 등재**한다.

**② `AC-OVERLAP-019` ⑦ — 표제를 고치고 실질 불변식만 남긴다.**
전제는 **전건 성립**한다(선례 파일 0행·0커밋 · SONGCUE 좌표계 old-side 9개 시작·길이 **바이트 동일** · 교차 단정 통과). 그리고 실측이 작성자보다 **강한 사실**을 준다 — 트립와이어 상수가 실측 hunk와 정확히 일치하므로 **갱신이 불필요했던 것이 아니라 갱신하면 그 단정이 깨진다**(뮤테이션 A-4: 선례 상수로 바꾸면 1건 실패). **처분**: ⑦을 *"트립와이어 상수가 실측 hunk와 일치하고 보호구역 교차 단정이 계속 성립한다"*로 고쳐 *"갱신되고"*를 뺀다. `CONTRACT.md` R-5(값 편집의 소속 마일스톤)는 **편집 0건이므로 공허 충족**임을 병기한다. **함께 고칠 것**: 선례 파일 `server/tests/test_songcue_bundle.py:56-63`의 주석이 PRECHK의 기여만 서술하고 **OVERLAP이 `tools.py`를 `+58 −3` 편집한 사실에 침묵한다** — 다음 SPEC이 그 주석을 읽고 오판한다.

**③ D-3 — 출하 형상을 수용한다. 다만 이것은 불일치가 아니다.**
**D-3은 호출 거부를 요구한 적이 없다.** 세 요건은 별도 상수 · `create_macro` 분기 밖 상시 검사 · **메시지가 섹션을 이름으로 말할 것**이며 **전건 충족**됐다(실측: 양쪽 `create_macro`에서 동일, 메시지가 `['fixture_types']`를 이름으로 말하고 *"조회를 시도하지 않았으므로 판독 실패가 아니다"*를 **명시적으로 부정**한다 — 결함 계열 1 위반 없음). **처분**: §5의 *"거부로 만들 수 없었다"*를 *"D-3은 거부를 요구하지 않았고 세 요건이 전건 충족됐다"*로 고친다 — 미충족을 자백하는 형태가 **사실과 다르다**. 부수 정정 3건: (a) *"거부로 만들 수 없었다"*는 **불가능성으로 성립하지 않는다** — 측정된 것은 *"출하 위치에 거부를 두면 5건이 깨진다"*이고 `create_macro` 분기 **뒤** 위치는 측정되지 않았다(`[추론]`). (b) `CONTRACT.md` D-3이 *"깨진다"*고 명명한 `:895-905`·`:907` 두 테스트는 **실제로는 통과한다**(부분문자열 단정) — 깨지는 것은 다른 3건이다. (c) **누락 섹션 전용 `skipped_checks` 행이 없다** — 유일한 행은 착수 시점부터 있던 `range_overlap_descope`이고 누락 사실은 `observation_note` 한 곳에만 실린다. `skipped_checks`만 기계 소비하는 소비자는 이 사실을 **볼 수 없다**. 그리고 사용자 문자열에 파이썬 리스트 repr `['fixture_types']`가 그대로 노출된다.

**④ `sibling_answered` — 슬롯 C 안이다. 수용한다.**
슬롯 C 본문이 이미 *"상계 순회는 픽스처 루트 조회가 **이미 성공한 뒤에만** 도달하므로 '형제가 답했다'가 참이고 `REASON_UNRESOLVED`가 근거 있게 도출된다"*를 적고, 구분 근거가 예외 타입이 **아님**을 못박으며, `AC-OVERLAP-006` ①②③④를 이미 소유한다. 파라미터는 그 문장이 전제한 사실을 **호출자→피호출자 인터페이스로 이동**시킨 것이고 **신규 사유 어휘 0건**이다. 이탈이 아니다. **정정 1건**: §5의 *"없으면 툴 경로의 분류가 **항상** `console_unreachable`이 된다"*는 **거짓**이다 — 붕괴는 **첫(루트) 조회가 실패할 때에만** 일어나고 이후 실패는 플래그와 무관하게 `path_not_resolved`다(실측). **코드 독스트링은 이미 옳게 적고 있으며**(*"when the very first read fails"*) `progress.md` 문장만 무조건형이다. **그리고 감사가 이 처분에 조건을 하나 붙인다** — 기본값이 `sibling_answered: bool = False`다. 슬롯 C가 그 사실을 **구조적으로 보장된다**고 선언했는데 기본값은 반대쪽이므로, **호출자가 이 인자를 빠뜨리면 설정 결함이 운영 조건으로 조용히 오분류된다.** 이것이 정확히 함정 5(*"어휘 가드 튜플 누락은 무증상이다"*)의 계열이고 D-6이 *"누락을 구조적으로 불가능하게 만들라"*로 닫은 것과 같은 형태다. **키워드 필수로 바꿔 누락을 `TypeError`로 만든다** — 1토큰 편집이며 무증상 누락을 요란한 누락으로 바꾼다.

### 처분 요약 — 무엇을 고치고 무엇을 고치지 않나

| 대상 | 처분 |
|---|---|
| P1 6건 | **닫아야 한다.** 2건은 출하 코드(P1-1 미관측 개체의 등급 기여 · P1-6 빈집합 폴백), 4건은 게이트 |
| P2 계수 6건 | **정정.** 그리고 §6.2의 처방(값 대신 **측정 명령**)을 §6.3·§6.4에 확장 적용한다 |
| `acceptance.md` §D 인용 4곳 | **전체 경로 접두 부여** — `.moai/specs/SPEC-COPILOT-PRECHK-001/acceptance.md` §D |
| 인수 조건 문언 4건 | `AC-OVERLAP-021` ① 좁힘 · `AC-OVERLAP-019` ⑦ 표제 · `AC-OVERLAP-017` ② 좁힘 · `AC-OVERLAP-018` ① 판정 방식 |
| plan-phase 산출물 6종 | **재작성하지 않는다.** 어긋남은 §4·§5·본 절이 정본이다. 단 `CONTRACT.md` D-3·D-8의 **근거 문장** 정정은 계약 결정의 변경이 아니라 오기 정정이므로 예외로 허용한다 |
| 정확폭 축 재활성화 | **하지 않는다** — 신규 범위이며 `ASSUMPTION-27`을 뒤집지 않는다는 `spec.md` 사전 확정 사실 2와 충돌한다 |

### 2회차를 여는 조건

**P1 6건을 닫은 뒤 뮤테이션 재주입으로 방어를 확인하기 전까지 sync-phase로 가지 않는다.** 특히 P1-4의 3지점은 수정 테스트가 **공허해지기 쉽다** — `footprint.py:324`의 *"관측된 모드가 0개다"* 가드가 대신 통과시키므로, 각 테스트가 **폭이 1개 이상 실제로 수집됐음을 먼저 단정**해야 한다(이것이 `:288` 뮤테이션이 무해했던 이유이며 같은 함정이다). P1-1은 코드 수정이므로 **역방향 확인**(수정 전 실패)이 필수다.

### P1 6건 폐쇄 — 완료 (2026-07-31)

**스위트 2920 → 2933 passed · 5 skipped · 0 failed.** 손댄 파일 `ruff check`·`ruff format --check` 전건 통과. PRESERVE 상시 게이트 23 passed. 커밋 `8c1a826` 외 본 절의 폐쇄 커밋.

집행 형태는 **선행물 인라인 → 게이트 폭 4 팬아웃**이다. 출하 코드 수정이 거동을 바꾸므로 오케스트레이터가 먼저 처리하고, 게이트 4건은 서로 다른 테스트 파일을 소유하므로 병렬로 돌렸다. **뮤테이션은 전 슬라이스가 런타임 주입(monkeypatch · `/tmp` pytest 플러그인 · 인메모리 소스 변환)으로만 확인했다** — 공유 트리의 소스를 쓰면 동시 슬라이스가 오염된다(§F.2가 실측한 위험).

| P1 | 무엇을 했나 |
|---|---|
| **P1-1** | `_overlap_basis`가 `missing_count`를 받아 **미관측 개체가 등급에 기여**한다. 역방향 확인: 같은 리그가 수정 전 `bound_proves_clear` · 수정 후 `not_performed`. **그리고 그 수정이 도달 가능하게 만든 거짓 문자열을 함께 고쳤다**(감사 P2) — `not_performed`는 *"일부만 비교된"* 리그의 올바른 최약 등급이기도 하므로 무조건 *"겹침 비교를 수행하지 않았다"*를 인쇄하면 `bound_slots`가 비어 있지 않을 때 거짓이다 |
| **P1-2** | 공유 시작점을 **실제로 갖는** 리그로 `AC-OVERLAP-010` ①②를 덮는다. 기존 단정은 집합 리터럴을 먹여 항진명제였다 |
| **P1-3** | 형태 단정에 **본문 절**을 더하고(루프 변수 직접 비교·비-`raise` 분기·`continue`·레지스트리 키 상수), 그와 별개로 **레지스트리 파라미터화 행태 게이트**를 신설했다 — 후자는 형태와 무관하므로 어떤 우회 형태도 피해 갈 수 없다 |
| **P1-4** | 열거 불완전 무효화 3지점에 게이트. **타입별 모드표를 갖는 `PerTypeRig`**를 신설해 결함 타입이 있어도 정상 타입이 폭을 접게 만들었다 — 폭이 0개면 *"관측된 모드가 0개다"* 가드가 대신 통과시켜 테스트가 공허해진다(`:288` 뮤테이션이 무해했던 이유). 각 테스트가 폭 수집을 **먼저** 단정한다 |
| **P1-5** | 예산 상한을 리터럴로 고정. 워커가 함께 시도한 `CAP > 1 + 1 + len(MODE_WIDTHS)`는 등호가 선행해 **그림자가 져 실패 불가능**함을 발견하고 **출하하지 않고 삭제**했다 — 이 지적과 같은 공허성이다 |
| **P1-6** | 픽스처 0개 리그를 단정. 대조 실측이 결정적이다 — 폴백을 뒤집으면 **기존 94건이 전건 통과**하고 신규 1건만 죽는다 |

**처분 ④도 함께 집행했다** — `walk_mode_widths`의 `sibling_answered`에서 기본값을 없앴다. 누락이 이제 `TypeError`다.

#### 재주입 검증 — 감사자가 아니라 오케스트레이터가 독립 격리 트리에서 돌렸다

`/tmp/ovl-verify`(폐쇄 커밋 detached · 전용 venv)에서 소스를 실제로 변형해 8종을 재주입했다. 슬라이스 보고를 승계하지 않는다.

| 뮤테이션 | 결과 |
|---|---|
| P1-1 `missing_count` 절 제거 · 노트를 무조건 blanket 문구로 | killed 1 · killed 1 |
| P1-4 `_child_slots` 거절 → 건너뛰기 | killed 2 |
| P1-5 상한 `40 → 1e9` · P1-6 빈집합 폴백 뒤집기 | killed 1 · killed 1 |
| P1-3 D-6 우회 **2변형**(허용목록+`continue` / 조건에 접기) | killed 2 · killed 2 |
| ④ `sibling_answered` 기본값 복원 | killed 1 |

**1회차에서 2건이 살아남았고 둘 다 오케스트레이터 자신의 작업이었다.** P1-1은 **코드를 고치고 게이트를 달지 않아** 되돌려도 아무것도 실패하지 않았고, 기본값 제거는 **모든 호출자가 인자를 넘기므로 행태 테스트에 보이지 않았다**. 둘 다 이 감사가 남에게서 찾아낸 것과 **정확히 같은 결함 계열**이다 — *결함을 고치는 것과 그 수정을 지키는 것은 별개의 작업이다*. 각각 `test_an_unread_population_drags_the_rig_wide_grade_down`과 시그니처 단정 `test_the_flag_has_no_default_so_a_caller_cannot_omit_it`을 추가해 닫았고, 위 표는 **닫은 뒤의 결과**다.

#### 남은 것 — sync-phase로 간다

P1 0건. 감사 P2 중 계수·인용 정정은 집행했다(§4 M6·M7·M8 · §5 · §6.3 · §6.4 · `CONTRACT.md` D-8 · `plan.md` §E). **`acceptance.md` 문언 4건**(`AC-OVERLAP-021` ① 좁힘 · `AC-OVERLAP-019` ⑦ 표제 · `AC-OVERLAP-017` ② 좁힘 · `AC-OVERLAP-018` ① 판정 방식)과 나머지 P2·P3는 **sync-phase에서 정본과 함께 처리한다** — 인수 조건 개정은 상태 전이와 같은 커밋에 있는 편이 추적된다. 선행 SPEC이 `acceptance.md`·`design.md`를 sync에서 감사 지적으로 정정한 선례를 따른다.

### §7.1 sync-phase 완료 · PR #8 (2026-07-31)

**스위트 2758 → 2946 passed · 5 skipped · 0 failed** · 손댄 11파일 `ruff check`·`ruff format --check` clean · PRESERVE 상시 게이트 24 passed. 커밋 4개(`8c1a826` P1 폐쇄 · `29ddbbd` 재주입 검증 · `862ea3a` sync · `48d6c8c` 앵커 1건).

> **스위트 계수 환산을 밝혀 둔다.** 워크트리 실측은 **2944 passed · 7 skipped**이며 차이 2건은 `server/tests/test_deploy_tauri_shell.py`가 `.app` 번들 미빌드 체크아웃에서 skip하는 것이다(`-rs`로 확인). 번들이 있는 트리에서는 2946 · 5다. CHANGELOG가 PRECHK에 대해 기록한 `2756+2=2758`과 같은 환산이며, **추정하지 않고 skip 목록을 열어 확인했다.**

#### 집행한 것

| 대상 | 처분 |
|---|---|
| `spec.md` `status` | `in-progress` → **`completed`**. 선행 9 SPEC이 전부 `completed`이고 PRECHK는 **sync 시점에 브랜치에서** 설정한 뒤 PR을 올렸다 — **§6.5의 *"`completed`는 머지 시점의 값"*은 그 선례와 어긋난다.** 머지는 별도 관문으로 남는다 |
| 인수 조건 문언 3건 | `AC-OVERLAP-021` ①(툴 표면 3값으로 좁힘 · **근거를 `[Option]`으로 교체**) · `AC-OVERLAP-019` ⑦(표제에서 *갱신* 제거) · `AC-OVERLAP-017` ②(*한국어 금지* → *라벨 소유권*) |
| `AC-OVERLAP-018` ① | **문언을 고치지 않고 게이트를 요구 수준으로 올렸다** — 라우트 8 · 클라이언트 메시지 타입 11 · 서버 이벤트 타입 15를 AST로 열거해 절대 튜플로 고정한다. 저장소 최초의 라우트 계수 게이트다 |
| 게이트 강화 4건 | `AC-OVERLAP-014` ⑨(어휘 **값**에 금지 토큰 스캔) · `AC-OVERLAP-015` ①(`"한정"`이 **한정의 부정**과 구별되지 않았다) · `AC-OVERLAP-009` ②(10+9→17 리그 신설) · `AC-OVERLAP-002` ④(비공허성 대조군) |
| 오기 정정 | `CONTRACT.md` D-3(*"깨진다"*고 명명한 두 테스트가 실제로는 깨지지 않는다 — 부분문자열 단정) · D-8(술어 문언이 코드보다 넓었다) · `design.md` 등급 4종→5종 · 끊어진 앵커 **5곳**(4곳이 아니었다 — 아래) |
| `CHANGELOG.md` | 기존 OVERLAP 항목에 감사·폐쇄·처분을 덧붙였다 |

#### 이 국면에서 내가 두 번 틀렸고 두 번 다 재측정이 잡았다

1. **`CHANGELOG`에 OVERLAP 항목이 없다고 단정했다** — **FXLIB 트리(`85a4b23`)에서 쟀기 때문이다.** 우리 브랜치에는 있었고 **§6.5가 옳았다.** 중복 항목을 넣기 직전에 되돌려 기존 항목에 병합했다.
2. **끊어진 앵커를 *"4곳 전부 처리"*로 닫았는데 5번째가 남아 있었다**(`design.md` B-ii). 첫 확인에서 정규식이 틀려 **0건으로 잘못 읽었다.**

**둘 다 이 감사가 남에게서 반복해서 찾아낸 형태다** — *잘못된 대상을 재고, 재측정 없이 통과시키는 것*(§7 P2의 공통 병인). 앞선 라운드에서 재주입이 내 수정 2건을 잡은 것과 같은 계열이며, **자기 감사의 한계는 이 세션에서 세 번 실증됐다.**

#### 중간에 저장소가 움직였다 — 유실 0건

sync 도중 외부에서 브랜치가 `feature/SPEC-COPILOT-FXLIB-001`로 전환되고 작업분이 stash됐다. **커밋은 브랜치 ref에 온전했고 유실은 0건이다.** 슬라이스 5개를 즉시 park시키고 산출물을 **파일이 아니라 텍스트로** 회수한 뒤, 사용자 결정에 따라 **전용 워크트리**에서 마무리했다(메인 트리와 FXLIB는 무변경). 기록해 두는 이유는 절차적이다 — **한 슬라이스가 `git stash pop`을 하지 않고 먼저 신고했고**, 4방향 동시 pop이었으면 복구가 어려웠다. 공유 트리에서 병렬로 일할 때 **git 상태 변경은 오케스트레이터만 한다**가 그 교훈이다.

#### PR #8 — 머지 전 관문은 사람 리뷰 하나뿐이다

`https://github.com/jjjh7401/AI-Lighting_Console/pull/8` · `base: main` · **`MERGEABLE` · `CLEAN`** · 20파일 `+7875 −30` · **`gh pr checks` 0건**.

`origin/main`은 `85a4b23`으로 본 SPEC BASE와 같아 **리베이스가 불필요**했고, 원격 브랜치가 plan-phase 시점 `8a5fa77`에 있어 **fast-forward** 푸시였다.

**§6.5의 지시대로 그 자리에 독립 코드 리뷰 2건을 병렬로 붙였다** — run-audit는 **프로세스 축**(요구-AC 정합 · 증거 · 경계)을 채점했고 **코드 품질·보안 축은 아직 아무도 보지 않았다.** 분할은 PRECHK의 *쓰기 경로 / 판독 경로*를 그대로 쓸 수 없다(본 SPEC은 쓰기 0건) — 대신 **판정·순회 층**(`footprint.py`·`patch.py`, 질문: *참 상계보다 작은 상계로 `bound_proves_clear`를 내는 입력이 있는가*)과 **배선·표현 층**(`tools.py`·`report.py`·`verdicts.py`, 질문: *사용자에게 거짓을 말하는 도달 가능한 상태가 있는가*)으로 갈랐다.

### §7.2 PR 독립 코드 리뷰 — P1 2건, 둘 다 거짓 "겹침 없음 증명" (2026-07-31)

**리뷰를 붙인 판단이 값을 냈다.** 두 리뷰어가 **각자 다른 층에서, 같은 오류 방향으로** P1을 하나씩 냈고 **둘 다 2944개 스위트가 전건 통과하는 상태에서 살아 있었다.** run-audit가 32건을 내고 그 P1 6건을 닫은 **뒤에도** 남아 있던 것이다.

| # | 결함 | 왜 감사가 놓쳤나 |
|---|---|---|
| **R-1** | **`DMXModes`가 `childCount 0`으로 답하면 "모드 0개를 완전히 열거함"으로 읽는다.** 응답기의 `safe_children`는 `Children()`과 `Count()`가 **둘 다** 실패하면 빈 테이블을 돌려주고 `childCount`가 그 같은 빈 판독에서 파생되므로 **계수와 자식 수가 일치하고 `truncated`도 서지 않는다** — `_listing_is_whole`이 "완전"이라 답한다. 타입 2개 리그에서 폭 8만 접히고 참 상계 31이 사라지는데 **note·failure·`skipped_checks` 어느 것도 남지 않아 정상 완주와 바이트 동일하다** | 감사는 **인수 조건에서 추론**했고 그 조항들은 *짧은 목록*과 *`truncated` 플래그*만 열거한다. **계수 0은 어디에도 이름이 없다** — `design.md` §6의 리그 목록도 `tier1_short`·`tier2_short`·`tier3_truncated_countable` 셋뿐이다. 리뷰는 **응답기가 실제로 무엇을 내보내는지**(`copilot_responder.lua`·`PROTOCOL.md` §4.2)에서 출발해 찾았다 |
| **R-2** | **같은 `(유니버스, 주소)`를 점유한 두 픽스처가 `bound_proves_clear`를 받는다.** 공유 시작점은 그룹 키 하나로 접혀 **간격이 아예 계산되지 않는데**, `bound_slots`가 *적격성*(`parse.ok` ∧ 정확폭 없음)으로 만들어져 그 슬롯들을 **비교한 것으로 계상**한다. 사용자는 동일 채널을 쓰는 두 픽스처에 대해 *"간격이 커서 겹침이 불가능"*을 읽는다 | 감사는 `AC-OVERLAP-010` ①②의 게이트가 **없다**는 것까지 찾았지만, 그 자리에 넣은 테스트가 **`bound_proves_clear`를 단정했다** — 즉 **결함을 정답으로 고정했다.** 리뷰는 조항이 아니라 **사용자가 읽는 문자열**에서 출발해 그것이 거짓임을 봤다 |

**R-2가 이 세션에서 가장 값나가는 관측이다.** 감사가 만든 게이트가 틀린 답을 잠갔고, 그 게이트는 **양방향 검증까지 통과했다**(HEAD 통과 · 뮤테이션 시 실패) — *비공허한 게이트도 틀린 불변식을 지킬 수 있다.* 뮤테이션 테스팅은 *"이 테스트가 무언가를 재는가"*를 답하지 *"재는 그것이 옳은가"*를 답하지 않는다. 그 질문은 **판정 결과가 아니라 사용자가 읽는 문장**을 보는 주체만 답할 수 있었다.

#### 처분

- **R-1**: 모드 목록이 비면 `whole = False` + 경로를 담은 note. 역방향 확인 — 같은 리그가 수정 전 `complete=True bound=8`, 수정 후 `complete=False bound=None`. 게이트는 `PerTypeRig(unlisted=...)`를 신설해 **정상 타입이 폭을 접은 상태에서** 재며(빈 폭 가드가 대신 통과시키는 것을 배제), 접힌 폭 8 ≤ 간격 30 < 참 상계 31을 함께 단정한다.
- **R-2**: `bound_slots`를 **참여**로 만든다 — 그룹 멤버가 1인 슬롯만. 잘못 고정된 게이트를 정정하고 **왜 틀렸는지를 그 테스트 안에 적었다.** 퇴화 방지 대조 2건을 함께 넣었다: 자기 주소를 가진 세 번째 픽스처는 **여전히 참여**하고(`bound_slots == (3,)`), 시작점이 전부 다른 리그는 **여전히 `bound_proves_clear`**다.
- 리뷰 P2·P3 5건(정확폭이 상계를 초과할 때의 문턱 · `walk.notes` 소비자 0건 · 불완전 시 `mode_widths` 노출 · `except Exception` 과대 포착 · 콘솔 중간 사망 오분류)은 **닫지 않았다.** 전부 `FootprintPolicy.enabled=True`(출하 호출자 0건)를 요구하거나 진단 정밀도 계열이며, **거짓 청결을 만들지 않는다.** 리뷰 원문에 재현과 최소 수정이 있고 후속 SPEC이 집는다.

**스위트 2947 passed · 5 skipped · 0 failed**(워크트리 실측 2945/7 + tauri 번들 2). 손댄 파일 ruff clean.

### §7.3 수렴 점검 4회차 — 계열은 소진되지 않았다. 그리고 뿌리는 이 SPEC 밖이다 (2026-07-31)

**질문은 하나였다**: *거짓 "겹침 없음 증명" 계열이 소진됐는가.* 3회차까지 매번 새 P1이 나왔고 마지막(코드 리뷰)도 0이 아니었으므로, 머지 전에 **수렴 여부만** 재기로 했다. 두 축으로 갈랐다 — **응답기 페이로드 형상 전수**(R-1이 그 각도에서 우연히 나왔으므로 이번엔 열거로) · **게이트가 고정한 불변식이 옳은가**(R-2가 틀린 답을 잠갔으므로).

**답: 소진되지 않았다.** 4회차도 P1을 냈다. 다만 **두 결함의 성격이 완전히 달라 처분도 갈린다.**

#### C-1 — 고쳤다: 한 축이 겹침을 증명한 뒤에도 다른 축이 청결을 주장했다

`_BASIS_ORDER`가 `exact_widths`를 `bound_proves_clear` 위에 두는데 **둘은 같은 종류의 진술이 아니다** — 앞은 *어떻게 비교했나*(결과가 충돌일 수도 있다)이고 뒤는 *결과*다. 최약 규칙이 method를 result로 끌어내려, 정확폭 축이 **실제로 겹침을 찾은** 리그에 *"간격이 커서 겹침이 불가능"*을 붙였다. 실측: 슬롯 1·2가 `1.100`에 동시 점유(정확폭 4, 채널 100~103 동일) + 슬롯 3 별도 → `range_overlaps=1` · `충돌 2건`인데 `basis=bound_proves_clear`. **최상위 키만 읽는 기계 소비자에게는 "증명된 청결"이다.**

**R-2가 닫은 것과 다른 문**이다 — R-2는 `bound_slots`의 참여 검사를 세웠는데 이 경로는 `exact_set`으로 들어와 그 검사를 우회한다. *같은 결함 계열이 두 번째 문으로 재입장했다.* 수정은 `bound_slots and not exact_overlaps`이며 기존 단정 **0건**을 바꾼다(리뷰어가 32개 단정에 대해 시뮬레이션했고 실측으로 확인됐다). 게이트를 함께 넣었고 비공허성은 *"정확폭 축이 실제로 겹침을 찾았고 상계 축도 실제로 돌았다"* 두 단정이 진다.

**출하 도달 불가**다(`FootprintPolicy(enabled=True)`를 만드는 프로덕션 호출자 0건). 그럼에도 고친 이유는 어휘가 공개 API이고 스위트가 상시 발화시키기 때문이다. **그리고 리뷰어가 출하 구성(`enabled=False`)에 대해 리그 약 306,000개 · 청결 등급 1,244건을 전수 훑어 거짓 증명 0건**을 냈다 — 이 축의 **live 위험은 그 실측이 경계 짓는다.**

#### C-2 — 고치지 않았다. 고칠 수 없다: 완전성 술어가 짧은 판독을 원리적으로 탐지하지 못한다

**이것이 이 SPEC의 안전 논증에서 가장 중요한 한계이며, 여기 정확히 적는다.**

`_listing_is_whole`은 `len(children) == node.childCount ∧ ¬truncated`로 완전성을 증명한다. **그 두 수는 서로 독립이 아니다.** 응답기 원문(직접 확인):

- `safe_children`의 `Count()`/`Ptr()` 폴백(`console/lua/copilot_responder.lua:398-411`)은 `for i = 1, count` 를 돌며 **성공한 `Ptr(i)`만** `out`에 넣는다 — 실패한 자식은 조용히 빠진다.
- `build_snapshot`(`:579-580` · `:607`)은 `local total = #children` 즉 **그 짧아진 배열**에서 계수를 파생해 `childCount = total`로 내보내고, `truncated = cap < total`이므로 서지 않는다.

**즉 짧은 판독이 스스로를 "완전"이라 선언한다.** 계수와 목록이 항상 일치하므로 술어가 발화할 수 없다. R-1의 수정은 `count == 0` 한 지점만 닫았고 **같은 파생은 어떤 계수에서도 성립한다.**

실측(리뷰어가 저장소의 lupa 하네스로 출하 응답기에 대해 재현): 픽스처타입 **1종** · 31채널 모드 1개 · 그 `DMXChannels`에서 `Children()` 불가 · 채널 슬롯 7 판독 실패 · 픽스처 `1.100`/`1.130`(간격 30) → 정상이면 `childCount=31` → 상계 31 → `30 < 31` → `bound_inconclusive`(옳다). 짧은 판독이면 `childCount=30` → `complete=True` · `notes=[]` → 상계 30 → `30 >= 30` → **`bound_proves_clear`**. 한정 문구는 *"열거된 모드 1개에 한정한 판정"*이라 **참이고 경보가 되지 않는다.**

**왜 이 SPEC이 고치지 않는가 — 세 가지가 겹친다.**

1. **뿌리가 `console/lua/**`이고 그것은 PRESERVE다.** 고치려면 응답기가 `Count()` 선언값을 `#out` 대신 실어 **짧은 판독이 자기 목록과 모순되게** 해야 한다. 그것은 프로토콜 계약 변경이며 `spec.md` §C가 잠근 경로다. 서버 쪽에는 **와이어 상 판별자가 존재하지 않는다** — 계수와 목록이 일치하는 두 상태를 구분할 정보가 페이로드에 없다.
2. **이 SPEC이 도입한 결함이 아니다.** 완전성 술어 `childCount` 대 읽은 개수는 `REQ-PRECHK-004`가 세운 것이고 **인벤토리 계층 전체가 같은 술어를 쓴다** — PRECHK의 완전성 판정도 똑같이 이 한계를 갖는다. 상속한 것이지 신설한 것이 아니다.
3. **전제가 미측정이다.** `Children()`이 그 핸들에서 실패해야 폴백이 도는데, `PROTOCOL.md` §6 `ASSUMPTION-4`가 폴백을 계약에 넣었을 뿐 **픽스처타입 트리에서 실제로 실패하는지에 대한 측정이 저장소에 0건**이다. `[미확정]`이며 관측 없이 닫히지 않는다.

**그래서 형상이 아니라 지식의 한계다.** 본 SPEC은 *"열거가 완전하면 상계가 참 상계"*라는 명제 위에 서는데, **완전성을 판정하는 유일한 수단이 이 경우 거짓 양성을 낼 수 있다.** 한정 표현(`AC-OVERLAP-015`)이 *"열거된 모드 N개에 한정"*을 항상 말하므로 주장 자체는 무한정이 아니지만, **그 N이 참값보다 작을 수 있다는 것까지는 말하지 않는다.**

> **※ 2026-08-07 — 후속 SPEC 순위 1과 같은 결함이다.** 위 「후속 SPEC이 집을 것」 표의 순위 1(응답기가 선언 계수를 판독 배열에서 파생하지 않게)이 정확히 이 C-2를 닫는다. **두 항목을 하나의 후속 SPEC으로 묶어야 하며**, 그 SPEC의 선행은 `console/lua/**` 개정(절차 — 이미 2회 선례)과 **라이브 측정 1건**(그 핸들에서 `Children()`이 실제로 실패하는가)이다.

#### 후속 SPEC이 집을 것 — 우선순위 순

| 순위 | 항목 | 선행 조건 |
|---|---|---|
| **1** | **응답기가 선언 계수를 판독 배열에서 파생하지 않게 한다** — `Count()` 원값을 실어 짧은 판독이 자기 목록과 모순되게. 인벤토리·매크로·상계 **세 축의 완전성 판정이 동시에 실질을 얻는다**. **※ 이 항목과 아래 C-2는 같은 결함의 두 얼굴이다 — 하나의 후속 SPEC으로 묶어야 한다** | `console/lua/**` PRESERVE 해제 + 라이브 측정(그 핸들에서 `Children()`이 실제로 실패하는가). **※ 2026-08-07 정정 — PRESERVE 해제는 blocker가 아니라 절차다**: 응답기 개정이 이미 2회 집행됐다(`.moai/specs/SPEC-COPILOT-SONGCUE-001/progress.md` Track B가 v1.4.1→v1.5.0, `.moai/specs/SPEC-COPILOT-DASHUI-001/progress.md:213`이 v1.4.0→v1.4.1). 남은 진짜 선행은 **라이브 측정 1건**이다 |
| 2 | 픽스처타입 **2종 이상** 쇼파일에서 상계 축 종단 검증 | ~~사용자 GUI 작업 — 현 쇼파일은 1종이라 R-1 계열이 원리적으로 발동하지 않는다~~ → **2026-08-07 정정: 선행 조건 충족(2026-08-04). 즉시 착수 가능.** 라이브 리그가 2타입이 됐다 — `.moai/specs/SPEC-COPILOT-GROUPGEN-001/progress.md:427`(`Patch/FixtureTypes` 3슬롯) · `:649-650`(Robin MMX Spot 19대 / Robin LEDBeam 350 20대). "1종"은 2026-07-31 시점 사실이며 2026-08-04에 뒤집혔다. **순위 1↔2 재검토 대상** — 이쪽은 라이브 측정도 응답기 개정도 필요 없다 |
| 3-i | **벽에 걸려 도달 불가** (2026-08-07 분리): 정확폭이 상계를 초과할 때의 문턱 · 불완전 시 `mode_widths` 노출 | **재개 조건 없음.** 둘 다 `FootprintPolicy(enabled=True)` + **정확폭 조인**을 요구하는데 조인 후보 12경로가 전건 부정됐고(`.moai/specs/SPEC-COPILOT-PRECHK-001/progress.md:296`) 출하 호출자도 0건이다. **유일한 외부 공급원은 Vectorworks `DMX Footprint` 컬럼**이며 그것은 "설계상 폭"이지 콘솔 실측 폭이 아니다 — 제3의 근거값으로만 실을 수 있다 |
| 3-ii | **벽 무관 — 지금 고칠 수 있다** (2026-08-07 분리): `walk.notes` 소비자 0건 · `except Exception` 과대 포착 · 콘솔 중간 사망 오분류 · 1·2단 동일 메커니즘 | 없음. **한 행에 3-i과 섞여 있던 탓에 후속이 전부를 도달 불가로 읽을 위험이 있었다** |

#### 이 회차가 머지 판단에 주는 것

**결함 발견 곡선은 꺾이지 않았다**(P1: 3 → 6 → 2 → 1+1). 그러나 4회차가 **처음으로 경계를 그었다** — 출하 구성 전수 훑기가 리그 위상 축에서 **거짓 증명 0건**을 냈고, 남은 live 도달 가능 결함은 **하나이며 그 뿌리가 이 SPEC 밖에 있고 상속된 것**이다. 즉 *"더 찾으면 더 나온다"*에서 *"남은 것이 무엇이고 왜 여기서 못 고치는지 안다"*로 옮겼다. **머지 판단은 그 위에서 내린다.**

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

### §F.2 개정 — run-audit는 폭 7로 넓힌다 (2026-07-31)

> **§F.1이 "이후 폭을 넓히면 §F.2를 신설해 그 시점과 근거를 남긴다"고 규정했다. 이 절이 그 기록이다.** 넓히는 국면은 **run-audit이며 run-phase 구현이 아니다.**

**감사 대상 시점**: `a61cf11efc56d6736d5eccac97416f26ea85e3a9` (본 SPEC BASE 이후 커밋 20개). 본 절을 쓰는 커밋이 `HEAD`를 옮기지만 **채점 대상은 그 SHA로 고정된다** — PRECHK가 `b355469` 시점을 채점한 것과 같은 형태다(§E.2a).

**착수 전제 3건 재실측** (이월 인용 아님): 브랜치 `feature/SPEC-COPILOT-OVERLAP-001` · `git status --porcelain` 빈 출력 · 스위트 **2920 passed · 5 skipped · 0 failed**(89.85s, `test_web_launcher` 플레이크 미발생).

#### §F.1의 폭 1 근거 셋이 이 국면에 어떻게 적용되나

| §F.1의 근거 | run-audit에 적용되나 | 왜 |
|---|---|---|
| 어휘 사슬 — M1이 M3·M4·M5의 **import 선행물** | **아니다** | 선행물 관계는 *만드는* 순서의 제약이다. 이미 출하된 형상을 **읽는** 데는 순서가 없다 |
| 파일 교집합 — 교집합 0인 쌍이 M7 하나뿐 | **아니다** | 교집합이 위험한 것은 **동시 쓰기**다. 채점은 읽기이며 같은 파일을 7주체가 동시에 읽어도 충돌이 0이다 |
| 교차 정합은 **전 아티팩트를 한 머리에 들고 있는 주체에게만 보인다** | **그대로 적용된다** | 그래서 **채점·합성·처분을 위임하지 않는다**(아래) |

**그리고 §F 본문이 이 국면을 이미 허가했다** — *"읽기 전용 scout 병렬은 폭 권고와 무관하게 계속 유효하다."* 선례도 같은 방향이다: PRECHK가 머지 직전 **독립 코드 리뷰 2건을 쓰기 경로·판독 경로로 병렬**로 붙여 P1 4건을 잡았고, §E.5가 *"리뷰는 읽기 전용이라 충돌이 없다"*를 명문화했다.

#### 오케스트레이터가 위임하지 않는 것 — 폭을 넓혀도 남는다

1. **7축 가중 채점과 최종 verdict.** 슬라이스는 **측정된 사실**만 올린다.
2. **불일치 4건의 처분**(§5 `deviations`). 인수 조건을 좁히는가·기각된 축을 켜는가는 범위 판단이며 `spec.md` §D를 읽는 주체의 일이다.
3. **교차 정합 축의 합성.** P1은 두 선례 모두 이 축에서만 나왔고(plan-audit 3/3 · PRECHK run-audit 4/4) 그 층은 §F.1이 말한 대로 한 머리에서만 보인다. 슬라이스 둘을 **다른 각도**(판정·순회 층 / 표현·배선 층)로 세워 각자 사실을 올리게 하고 **합성은 오케스트레이터가 한다** — plan-phase의 병렬 2가 계약 빈틈 11건을 낸 것과 같은 형태다.

#### 폭 7 — 슬라이스와 축 배정

| # | 슬라이스 | 축(가중치) | 쓰기 |
|---|---|---|---|
| 1 | 좌표·계수 재현 | 인용 정확성 (20%) | 없음 |
| 2 | 판정·순회 층 대조 | 교차 정합 (30%) | 없음 |
| 3 | 표현·배선 층 대조 | 교차 정합 (30%) | 없음 |
| 4 | REQ·AC 역추적 + AC→테스트 사상 | 요구-AC 정합 (15%) | 없음 |
| 5 | **뮤테이션 재주입** | AC 기계검증성 (15%) | **격리 워크트리** |
| 6 | 등급·경계·미결 은닉 | 증거 등급 (10%) · 범위 경계 (5%) · 미결 은닉 (5%) | 없음 |
| 7 | 불일치 4건 전제 실측 | 처분 근거 (오케스트레이터가 판단) | 없음 |

#### 병렬의 유일한 실제 위험과 그 폐쇄 — 실측으로 닫았다

**뮤테이션 축은 공유 워크트리의 소스를 쓴다.** 그 슬라이스가 다른 슬라이스와 동시에 돌면 (a) 읽기 슬라이스의 `pytest`가 **뮤테이션된 소스**를 보고 (b) 규율 14(`__pycache__` mtime 1초 해상도)가 **뮤테이션 생존을 오판**시킨다. 폐쇄를 실측했다:

| 실측 | 결과 |
|---|---|
| `git worktree add /tmp/ovl-mut-probe HEAD --detach` 후 그 트리에서만 `verdicts.py` 뮤테이션 | 워크트리 pytest **collection error**(뮤테이션 관측) · **같은 순간** 본 트리 pytest **8 passed** |
| 공유 `.venv`를 `UV_PROJECT_ENVIRONMENT`로 빌려 쓰기 | **금지.** `uv run`이 editable 설치 대상을 **매 호출마다 자기 트리로 재지정**한다(`Uninstalled 1 / Installed 1`). 해석은 rootdir sys.path 우선이라 무해했으나 두 트리가 같은 dist-info를 동시에 쓰는 경합이 남는다 |
| 워크트리 전용 venv `uv sync` | **0.151s**(uv 캐시 하드링크). 경합 0. 이것을 채택한다 |

**나머지 6슬라이스는 소스를 쓰지 않으며 `pytest`에 `-p no:cacheprovider`를 붙여 `.pytest_cache` 경합까지 없앤다.** 전체 스위트는 **오케스트레이터가 단독으로 소유**한다 — 슬라이스가 각자 2920을 재실행하는 것은 값이 0이고 소요만 7배다.

**폭 7이 오탐을 늘리지 않게 하는 장치**: §6.4의 **오탐 선언 4건을 전 슬라이스에 배포**하고, 그것을 지적으로 올리려면 **선언된 근거를 증거로 반증**할 것을 요구한다. 선언을 무비판 수용하는 것도 금지한다 — 반증 가능성을 열어 둔 것이 선언의 조건이다.

---

## §8 sync 마무리 — CHANGELOG 따라잡기 (2026-08-01)

**sync 커밋(`862ea3a`) 이후 프로덕션 코드가 두 번 더 바뀌었는데 CHANGELOG는 sync 시점 상태로 멈춰 있었다.** 이 SPEC이 스스로 세운 규율(*"거짓 청결 주장을 형상으로 막는다"*)에 비추면, 가장 중요한 발견이 사용자 대면 문서에서 빠져 있던 셈이다.

| sync 이후 커밋 | 무엇이 바뀌었나 | CHANGELOG 반영 |
|---|---|---|
| `48d6c8c` | `design.md` B-ii 끊어진 앵커 1건 — 전체 경로 접두 부여 | 문서 정정, 별도 항목 불요 |
| `f383833` | **프로덕션 코드** `footprint.py` · `patch.py` — PR 코드 리뷰 P1 2건, 둘 다 거짓 "겹침 없음 증명" | **누락 → 이번에 추가** |
| `929a6c3` | **프로덕션 코드** `patch.py` — 수렴 점검 4회차: C-1 수정 + C-2를 **고칠 수 없는 한계**로 명시 | **누락 → 이번에 추가** |

### 추가한 것 — 하위 불릿 2건

1. **수렴 점검 4회차의 두 결과.** C-1(고침): 한 축이 겹침을 증명한 뒤에도 다른 축이 청결을 주장했다 — 앞 라운드가 세운 참여 검사를 `exact_set` 경로가 **우회**했고, *같은 결함 계열이 두 번째 문으로 재입장*했다. C-2(못 고침): **완전성 술어가 짧은 판독을 원리적으로 탐지하지 못한다** — 응답기가 선언 계수를 판독 배열 자체에서 파생하므로 짧은 판독이 스스로를 "완전"이라 선언한다. 뿌리가 `console/lua/**`(PRESERVE)라 **형상이 아니라 지식의 한계**다.
2. **머지 판단의 근거를 "결함 0"이 아니라 "경계를 알았다"로 적었다.** 결함 곡선은 꺾이지 않았고(P1 3 → 6 → 2 → 1+1), 4회차가 처음으로 경계를 그었다 — 출하 구성 전수 훑기가 리그 약 306,000개·청결 등급 1,244건에서 **거짓 증명 0건**을 냈다.

**C-2를 CHANGELOG에 적은 것이 이번 마무리의 핵심이다.** 고칠 수 없는 한계를 릴리스 노트에서 빼면, 이 SPEC이 남에게서 반복해 찾아낸 바로 그 형태(*측정하지 않은 청결을 청결로 보고하기*)를 자기 문서가 저지르게 된다.

### 검증

- 전체 스위트 **2948 passed · 5 skipped · 0 failed** (직접 실측, 이월 아님)
- `spec.md` `status: completed` (sync 시점 `862ea3a`에 설정, 불변)
- PR **#8** OPEN — 본 커밋 push로 갱신된다

### 부수 — 낡은 stash 폐기

FXLIB 브랜치 생성 전 보관했던 `stash@{0}`("OVERLAP-001 sync-pending WIP")를 폐기했다. **브랜치가 앞서 있어 전량 대체됐음을 확인한 뒤** 버렸다 — `CONTRACT.md`·`acceptance.md`·`test_overlap_preserve.py`는 브랜치와 바이트 동일했고, `design.md`(1줄)·`test_prechk_footprint.py`(3줄)의 stash 고유 내용은 전부 **이후 커밋이 더 나은 형태로 교체한 자리**였다(특히 `BOUND_PROVES_CLEAR` 단언은 `f383833`이 거짓 증명을 고치며 바꾼 바로 그 줄). 손실 0건.
