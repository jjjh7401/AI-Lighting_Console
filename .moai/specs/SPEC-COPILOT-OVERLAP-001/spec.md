---
id: SPEC-COPILOT-OVERLAP-001
title: "보수적 점유폭 상계로 구간 겹침 판정 재개 (Bounded-Footprint Range Overlap)"
version: "0.1.0"
status: draft
created: 2026-07-30
updated: 2026-07-30
author: manager-spec
priority: P2
phase: "Phase 3 이후 차별화 기능 — PRECHK 후속 1순위"
module: "server/prechk/ (신규 모듈 1개 + 기존 3파일), server/orchestrator/tools.py"
lifecycle: spec-anchored
tags: "patch, dmx-address, footprint, upper-bound, range-overlap, vocabulary, preserve-gate"
tier: M
related_specs: [SPEC-COPILOT-PRECHK-001, SPEC-COPILOT-SONGCUE-001, SPEC-COPILOT-BUSKWIZ-001, SPEC-COPILOT-LOOKLIB-001, SPEC-COPILOT-MVP-001]
---

# SPEC-COPILOT-OVERLAP-001 — 보수적 점유폭 상계로 구간 겹침 판정 재개

> **본 SPEC은 저장소에서 처음으로 제안서가 아닌 곳에서 나온다.** 출처는 PRECHK의 **독립 run-audit가 열거한 후보 I-15**이며 원문은 `.moai/specs/SPEC-COPILOT-PRECHK-001/progress.md:653`이다. 제안서에 `구간 겹침` · `점유폭` · `overlap` 문자열은 0건이다(`research.md` §1).
>
> **PRECHK는 이 축을 `ASSUMPTION-27` 부정으로 닫았고 본 SPEC은 그것을 뒤집지 않는다.** 조인은 여전히 없다. 본 SPEC은 조인이 없는 상태에서 무엇을 말할 수 있는지를 정확히 한다.
>
> **사용자 승인 1건 확보(2026-07-30)**: 닫힌 판정 어휘 확장 — 신규 축 `overlap_basis` 4값 + `SKIPPED_CHECK_KIND` 1값. PRECHK `progress.md` §0이 *"어휘 확장은 계약 변경이므로 SPEC 문서를 쓰기 전에 사용자 승인을 받는다"*고 규정했고 그 절차를 지켰다.

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 |
|---|---|---|---|
| 0.1.0 | 2026-07-30 | manager-spec | 최초 작성 (draft, Tier M). 출처는 PRECHK run-audit 후보 I-15. 조사 방법은 **병렬 read-only scout 4개 + 코디네이터 직접 검산**(산술 재계산 · 주소 파서 실행 · git 이력 조회). **라이브 프로브 0회** — 필요한 값이 전부 선행 SPEC에 실측 전재되어 있다. REQ **18건** · ASSUMPTION **5건**(31~35) · clarification 마커 **0건**. 조사가 선행 기록의 오류·누락 **5건**을 정정했다(`research.md` §12). **승인 대기 0건** — 어휘 확장은 착수 전 승인 완료. |

---

## A. 개요

**한 줄**: 픽스처를 자기 점유폭에 잇는 조인 키가 없어도, **열거 가능한 모드 전체의 폭 최대값**을 상계로 삼아 *"겹침 없음"*을 증명한다. 증명되지 않으면 **충돌이 아니라 미확정**으로 보고한다.

PRECHK는 구간 겹침 판정을 **수행하지 않고 수행하지 않았다고 보고**했다. 본 SPEC은 그 축을 **되살리되 판정의 비대칭을 계약으로 만든다.**

### 사전 확정 사실 (사용자 확정 — 재질의 금지)

1. **닫힌 어휘 확장이 승인됐다** — 신규 축 `overlap_basis` = {`exact_widths`, `bound_proves_clear`, `bound_inconclusive`, `not_performed`} + `SKIPPED_CHECK_KIND` += `range_overlap_bound_inconclusive`. **`COLLISION_KIND`와 `FIXTURE_VERDICT`는 건드리지 않는다** — 상계로 증명된 청결은 충돌도 미수행도 아닌 제3의 결과이므로 기존 축 어디에도 들어갈 수 없다(`research.md` §8.1).
2. **`ASSUMPTION-27`은 부정으로 유지된다.** 본 SPEC은 조인을 되살리지 않는다. PRECHK `progress.md`의 `DESCOPE: ASSUMPTION-27` 접두 행은 **원문 그대로 1건으로 보존**되며 `server/tests/test_prechk_patch.py:310-317`이 그것을 상시 단정한다.
3. **쓰기는 0건이다.** 본 SPEC은 읽고 판정하고 보고한다. 콘솔 발화가 없으므로 *"`Cmd` 접수 `OK`는 효과 증거가 아니다"* 계열은 적용 대상이 아니며 그 사실 자체가 범위 경계다.

### 조사가 확립한 제약 — 본 SPEC이 이 위에 선다

1. **판정 술어는 `간격 < 폭`이다.** 구간이 닫힌 끝(`start + width - 1`)이므로 `간격 == 상계`는 **증명 가능하게 깨끗하다**. `progress.md` §E.6 ④의 *"상계 이하라 미확정"*은 off-by-one이며 `research.md` §3.1이 코드로 정정했다. **이 쇼파일에서는 두 표현이 같은 답을 내므로 오류가 잠복한다.**
2. **상계는 열거 완전성 위에서만 성립한다.** 모드 집합이 불완전하면 `max`가 **부분집합의 최대값**이 되어 참 상계보다 작아지고, `bound_proves_clear`가 **거짓 양성**으로 발화한다(`research.md` §4.1의 구체 시나리오: 부분집합 상계 29 vs 참값 31, 간격 30인 리그에서 결론이 뒤집힌다).
3. **1·2단과 3단은 절단 술어가 다르다.** `DMXChannels` 열거는 `truncated=true`인데 `childCount`가 참값을 준다(`.moai/specs/SPEC-COPILOT-PRECHK-001/progress.md:408`). 1·2단은 **자식 집합**이 필요하므로 절단이 치명적이고, 3단은 **계수만** 필요하므로 절단이 무해하다.
4. **위험은 한 방향뿐이다.** 구간 겹침이 `intervals`를 유니버스로 키잉하고 `_flush_cluster`가 `universe`를 스칼라로 받으므로 유니버스를 넘는 점유는 **구조적으로 비가시**하다. 따라서 가능한 오류는 거짓 충돌이 아니라 **거짓 "겹침 없음 증명"** 뿐이다(`research.md` §5.3).
5. **주소 공간에 검증이 0건이다.** 파서가 `^(\d+)\.(\d+)$` 하나이며 하한도 상한도 없다 — `normalize_address("0.0")`이 `ok=True`를 낸다(`research.md` §4.4, 실행 확인). 오늘은 정확 일치 중복만 보므로 무해하고, **간격을 계산하는 순간 무의미한 주소가 무의미한 판정을 만든다.**
6. **최소 간격 42도 상계 31도 이 쇼파일의 산물이다.** 룰북 예제가 `addr = addr + 42`를 9회 돌린 결과가 실측 유니버스 1의 슬롯 2~10 주소와 **정확히 일치한다**(`research.md` §5.6). 두 수 중 어느 것도 하드코딩할 수 없다.

---

## B. 요구사항 (GEARS)

### B.1 상계 획득 — 런타임 3단 순회

- **REQ-OVERLAP-001** `[Ubiquitous]` The 시스템 **shall** 점유폭 상계를 **런타임에 읽어** 얻는다 — `Patch/FixtureTypes` 열거 → 각 타입의 `DMXModes` 열거 → 각 모드의 `DMXChannels` `childCount`. 상계는 그 계수들의 **최대값**이다. **폭 값도 상계 값도 코드에 상수로 두지 않는다** — 실측 29·31과 최소 간격 42는 이 쇼파일 룰북 레시피의 산물이며 다른 리그에서 다르다(`research.md` §5.6).
- **REQ-OVERLAP-002** `[Ubiquitous]` The 순회 **shall** `state` 표면(`query_state`)만 사용하고 프로퍼티를 **0건** 읽는다. 따라서 `PROPERTY_WHITELIST`에 추가할 이름이 없고 `server/safety/**`에 신규 예외 지점이 **0건**이다 — PRECHK가 받은 조건부 예외는 `prop` 때문이었으며 본 SPEC은 그것을 재사용하지 않는다(`.moai/specs/SPEC-COPILOT-PRECHK-001/spec.md:121`).
- **REQ-OVERLAP-003** `[Event-driven]` **When** 1단 또는 2단 열거의 **읽은 개수가 `node.childCount`보다 작거나** 조회 예산이 소진되거나 조회가 예외를 냈으면, the 시스템 **shall** **상계 계산 자체를 수행하지 않는다.** 완전성 판정이 `max` 연산보다 **앞에** 온다. 부분 결과를 `max`에 넣고 사후에 플래그로 무효화하는 제어 흐름은 **금지**다 — 표기와 판정이 서로 다른 대상에 붙어 표기가 남아도 판정이 이미 오염된다(`research.md` §4.1).
- **REQ-OVERLAP-004** `[Ubiquitous]` The 시스템 **shall** 1·2단에는 **목록 완전성** 술어를, 3단에는 **계수 존재성** 술어를 적용한다. 두 술어를 하나로 뭉개지 않는다 — 3단은 `truncated=true`에도 `childCount`가 참값이므로(`.moai/specs/SPEC-COPILOT-PRECHK-001/progress.md:408`) 뭉개면 3단이 불필요하게 실패하거나 1·2단이 잘못 통과한다.
- **REQ-OVERLAP-005** `[Ubiquitous]` The 순회 **shall** 조회 예산 상한을 갖고, 그 상한과 대상 경로를 **인자로 받는다.** 순회 모듈은 `server.orchestrator.tools`를 import하지 않는다 — `tools.py`가 `server.prechk.*`를 import하므로 역방향은 하드 순환이다(`research.md` §6).
- **REQ-OVERLAP-006** `[Event-driven]` **When** 순회 조회가 실패하면, the 시스템 **shall** **설정·배선 결함**(경로가 이 쇼파일에 없다)과 **운영 조건**(콘솔이 응답하지 않는다)을 구분해 보고한다. 프로덕션 게이트 포트는 `ok=false`와 타임아웃을 **같은 예외 타입**으로 던지므로(`server/safety/console.py:387-388`) 구분은 예외 타입이 아닌 다른 근거로 해야 한다. 기존 분류 규칙(`REASON_UNRESOLVED` / `REASON_UNREACHABLE`, `server/orchestrator/tools.py:196-206`)을 **적용**하며 새 규칙을 만들지 않는다 — 순회는 픽스처 루트 조회가 이미 성공한 뒤에만 도달하므로 *"형제가 답했다"*가 참이다.
- **REQ-OVERLAP-007** `[Unwanted]` The 시스템 **shall not** 순회 실패를 *"겹침 없음"*으로 읽히게 하고, 순회 실패로 인해 **리포트의 나머지를 잃는다**. 인벤토리·주소 중복 판정은 순회 결과와 무관하게 산출된다.

### B.2 상계 논증 — 겹침 판정

- **REQ-OVERLAP-008** `[Ubiquitous]` The 시스템 **shall** 겹침 판정 술어로 **`간격 < 상계`**를 쓴다. `간격 ≥ 상계`는 **겹침 없음이 증명된** 것이다. `이하`·`초과` 같은 경계 표현을 쓰지 않는다 — 구간이 닫힌 끝이므로 `간격 == 상계`는 깨끗하다.
- **REQ-OVERLAP-009** `[Ubiquitous]` The 시스템 **shall** 인접 간격을 **각 유니버스 내부에서만** 계산하고 전 유니버스에 대해 최소를 취한다. 각 유니버스의 마지막 픽스처는 오른쪽 이웃이 없어 간격을 기여하지 않는다. 유니버스를 넘는 감산은 **서로 다른 주소 공간의 감산이며 무의미**하다.
- **REQ-OVERLAP-010** `[Ubiquitous]` The 간격 계산의 대상 **shall** **서로 다른 주소의 집합**이다 — 같은 `(유니버스, 주소)`를 둘 이상이 점유하는 경우는 `REQ-PRECHK-007`의 주소 중복 축이 이미 판정하므로 여기서 이중 계상하지 않는다. 그리고 이 축은 픽스처타입·모드 확정을 **요구하지 않는다** — 상계 논증의 요점이 *"어느 픽스처가 어느 모드를 쓰는지 몰라도 성립"*이기 때문이다.
- **REQ-OVERLAP-011** `[Unwanted]` The 시스템 **shall not** 상계로 증명되지 않은 쌍을 **충돌로 보고**한다 — 충돌 목록에 넣지 않고 충돌 계수에 더하지 않으며 관여 픽스처에 충돌 판정을 붙이지 않는다. 상계 논증은 *"겹침 없음"*만 증명하며 *"겹침 있음"*은 증명하지 못한다. 증명되지 않은 것은 **미확정**이다.
- **REQ-OVERLAP-012** `[Ubiquitous]` The 시스템 **shall** 주소를 간격 계산에 쓰기 전에 **유효 범위를 검증**하고, 범위를 벗어난 값은 판독 실패로 분류해 간격 계산에서 제외하며 그 사실을 보고한다. 현재 파서는 하한도 상한도 없어 `0.0`과 `1.99999`가 통과한다(`research.md` §4.4). 무의미한 주소는 무의미한 간격을 만들고 그 간격이 판정을 낸다.
- **REQ-OVERLAP-013** `[Option]` **Where** 슬롯별 정확한 폭이 주어지면, the 시스템 **shall** 그 슬롯에 대해 **정확폭 비교**를 수행하고 상계 논증보다 우선한다. 정확폭이 없는 슬롯에만 상계를 적용한다 — 기존 `FootprintPolicy` 경로를 깨지 않는 것이 요건이다.

### B.3 판정 어휘와 보고

- **REQ-OVERLAP-014** `[Ubiquitous]` The 시스템 **shall** 겹침 판정의 **근거 등급**을 닫힌 어휘 `overlap_basis`로 표현한다 — `exact_widths`(슬롯별 정확폭으로 비교했다) · `bound_proves_clear`(열거 완전한 모드 집합의 상계로 겹침 없음이 증명됐다) · `bound_inconclusive`(최소 간격이 상계 미만이라 판정하지 못했다) · `not_performed`(정확폭도 상계도 없다). 어휘 밖 값은 **조용히 통과하지 않는다**.
- **REQ-OVERLAP-015** `[Ubiquitous]` The `bound_proves_clear` 판정 **shall** *"관측된 모드 집합에 한정해"*를 함께 말한다. 응답기는 프로퍼티명을 열거할 수 없고 어떤 프로브 집합도 부재 증명이 될 수 없다 — PRECHK가 *"후보 12건 전건 부정"*을 무한정으로 적어 감사 지적을 받은 것이 같은 계열의 두 번째 미끄러짐이었다(`.moai/specs/SPEC-COPILOT-PRECHK-001/progress.md:646`).
- **REQ-OVERLAP-016** `[Ubiquitous]` The 리포트 **shall** 상계의 **근거를 페이로드에 싣는다** — 상계 값과 그 출처(어느 경로의 어느 계수에서 왔는가). `FootprintPolicy.source`가 필드로 존재하면서 소비자 0건으로 죽어 있는 것이 선례이며(`research.md` §8.4) **근거를 받는 필드를 만들고 내보내는 키를 만들지 않으면 같은 결과가 된다.**
- **REQ-OVERLAP-017** `[Ubiquitous]` The 사용자 대면 한국어 요약 **shall** `overlap_basis` 라벨을 싣는다. 페이로드에만 넣고 요약에 넣지 않으면 **사용자에게 보이지 않는다** — 요약이 사용자가 실제로 읽는 유일한 문자열이다. 판정 어휘 라벨은 표현 계층에 두며 `REQ-PRECHK-017`의 형상을 계승한다.

### B.4 경계 · PRESERVE

- **REQ-OVERLAP-018** `[Unwanted]` The 시스템 **shall not** 신규 REST 라우트 · 웹소켓 메시지 타입 · `execution_port` 직접 접근을 만들고, `server.bridge`를 직접 import하며, `server/tools/`의 운영 유틸 예외 목록에 파일을 추가한다 — 네 금지가 모두 적용된다. `REQ-MVP-029`와 `REQ-PRECHK-018`~`REQ-PRECHK-020`의 계승이다.

---

## C. 환경 및 전제

### 측정된 기준선

착수 SHA **`85a4b2389003cb61b0ab72eb4aa8d6b2ff90b94a`**에서 **직접 실측**한 값은 `uv run pytest server/tests/ -q` → **2758 passed · 5 skipped · 0 failed**다. 전체 스위트 수는 **각 마일스톤이 착수 직전 직접 실측**하며 **이월 인용을 금지**한다.

> **BASE 두 개를 혼동하지 않는다.** 본 SPEC의 BASE는 위 값이고, **PRECHK의 PRESERVE 기준점은 `95687a0e0eba90b325daf76efbd0ac197e69e2fc`로 영구 불변**이다. PRECHK의 PRESERVE를 새 BASE로 검사하면 착수 직후 항상 0행이라 게이트가 무력해진다 — `.moai/specs/SPEC-COPILOT-PRECHK-001/progress.md:558`이 같은 무력화를 실측으로 증명했다. `.moai/specs/SPEC-COPILOT-PRECHK-001/progress.md` §E.9가 다음 BASE를 `b406a7b…`로 적었으나 실제로는 그 위 1커밋이며, **코드 무변경 문서 커밋이라 게이트 의미는 동일하다**(`research.md` §9.1).

**라이브 세션은 착수에 필요하지 않다.** 상계와 간격이 모두 선행 SPEC에 실측 전재되어 있고(`.moai/specs/SPEC-COPILOT-PRECHK-001/progress.md:308-326` · `:403`) 본 SPEC이 요구하는 것은 그 값을 **런타임에 읽는 형상**이다. 라이브가 필요한 항목은 전부 `ASSUMPTION-31`~`ASSUMPTION-35`이며 **어느 것도 착수를 막지 않는다.**

### 미검증 전제 (ASSUMPTION)

번호는 선행 SPEC 이후를 이어받는다(PRECHK가 `ASSUMPTION-25~30`을 썼다).

- **ASSUMPTION-31** — **연속 블록 전제.** 픽스처가 `Patch` 시작점에서 시작하는 **하나의 연속 블록**을 점유한다. `BreakAddress` · `Break` · `BreakCount`가 전부 `property not readable`이고 `Patch` 값이 `<유니버스>.<주소>` 한 쌍뿐이므로(`.moai/specs/SPEC-COPILOT-PRECHK-001/research.md:97-99`) 현 표면에서 확인 불가다. **거짓이면 `start + width - 1`이 첫 블록을 과대평가하고 둘째 블록을 완전히 놓친다 — 상계가 상계가 아니다.** 현 쇼파일은 픽스처타입 1종뿐이라 실험이 원리적으로 불가능하다. **차단 대상: 없음** — 부정이면 `bound_proves_clear`를 내지 않는 형상으로 축소된다.
- **ASSUMPTION-32** — **`DMXChannels` 자식 수 = DMX 슬롯 수.** `childCount` 29·31만 기록됐고 **자식 이름은 한 건도 기록되지 않았다**(열거가 `truncated=true`, `.moai/specs/SPEC-COPILOT-PRECHK-001/progress.md:408`). 자식이 어트리뷰트 논리 채널이고 16비트 어트리뷰트가 2슬롯을 쓰면 `childCount < 실제 슬롯 수`이며 **상계가 과소평가**된다. 저장소 내 유일한 방증은 룰북의 `addr + 42` 레시피가 겹침 회피를 요구하므로 `childCount ≤ 42`가 방증된다는 것뿐이고, **등식은 방증되지 않는다.** **차단 대상: 없음** — `ASSUMPTION-31`과 같은 축소.
- **ASSUMPTION-33** — **유니버스 용량과 주소 기준.** 유니버스당 채널 상한 `B`에 대해 **저장소 근거 0건 · 라이브 관측 0건**이다(`research.md` §5.1의 범위 9곳 전수 살핌). 실측 리그에서 **판정이 갈리는 창은 `B ∈ [437, 466]` 30값뿐**이며 `B ≥ 467`이면 몰라도 증명된다 — **따라서 전제는 512가 아니라 `B ≥ 467`이라는 훨씬 약한 명제다.** 주소 기준(1-기준 vs 0-기준)은 **간격 산수에 무관하고**(차분은 원점 이동에 불변) **꼬리 산수 하나에만** 걸리므로 같은 전제에 묶는다. **차단 대상: 꼬리 초과 판정 축 하나뿐**이며 그 축은 아래 §D가 범위 밖으로 둔다.
- **ASSUMPTION-34** — **`state` 표면만으로 3단 순회가 도달한다.** 상계가 요구하는 읽기가 전부 `state`이므로 `server/safety/**` 신규 예외가 0지점이라는 판정(`research.md` §9.6)은 **`[추론]`이다.** **차단 대상: `server/safety/**` PRESERVE의 유지 여부.** 부정이면 PRECHK가 연 4지점을 재사용해야 하고 그 경우 §E의 PRESERVE 서술을 개정한다. **첫 마일스톤이 이 전제를 닫는다** — 인메모리 프로토타입 1개로 갈리며 라이브가 필요 없다.
- **ASSUMPTION-35** — **`Patch/FixtureTypes` 열거의 완전성과 타입 수 `T`.** `T`의 실측 기록이 저장소에 **0건**이다. `1 + T + Σ M_t` 회 조회가 필요하므로 예산 상한 결정이 `T`에 걸린다. **차단 대상: 없음** — 예산을 보수적으로 잡고 소진 시 `not_performed`를 내면 `T`를 몰라도 안전하다(`REQ-OVERLAP-003`). 다만 **`node.childCount`와 `len(children)`을 함께 읽는 것**이 요건이며 `children` 길이만 보면 안 된다.

> **U-1 · ASSUMPTION-31 · ASSUMPTION-32는 전부 "다른 쇼파일이 필요하다"로 수렴한다.** 본 SPEC은 그것을 기다리지 않고 **셋 중 하나라도 거짓이면 `bound_proves_clear`를 내지 않는 형상**으로 출하한다 — PRECHK가 `FID`를 판정 근거에서 배제하고 출하한 것과 같은 형태다.

### PRESERVE — 무변경 대상

**PRECHK의 PRESERVE를 전량 계승한다** — `server/looks/{schema,loader,roles,resolver,instantiate,matching}.py` · `server/looks/library/` · `server/web/preview.py` · **`console/lua/**`** · `server/rulebook/assets/v2.4.2/**` · `server/orchestrator/tools.py`의 `_PROGRAMMER_STATE_COMMANDS`와 dedupe 실행 루프.

**그리고 본 SPEC은 `server/safety/**`를 무변경으로 둔다.** PRECHK가 받은 조건부 예외는 `prop`(프로퍼티 조회)이 프로덕션 경로로 도달 불가했기 때문이며, 본 SPEC의 순회는 프로퍼티를 **0건** 읽고 `state`만 쓴다(`REQ-OVERLAP-002`). `state`는 이미 `StateQueryPort`로 프로덕션에 도달해 있다. **신규 예외 지점은 0건이다** — 다만 이 판정은 `ASSUMPTION-34`이며 첫 마일스톤이 닫는다.

> **`console/lua/**`를 다시 PRESERVE로 두는 근거를 명시한다.** BUSKWIZ가 잠갔고 SONGCUE가 `plan.md`와 정본의 모순 때문에 풀었으며 PRECHK가 다시 잠갔다. **본 SPEC에도 그 강제 사유가 없다** — 상계가 요구하는 읽기 전량이 현재 `state` 표면으로 달성된다. 이 문장을 남기는 이유는 절차적이다: SONGCUE에서 오케스트레이터가 `plan.md`의 좁은 목록만 보고 정본 절을 읽지 않아 응답기 변경을 지시한 실수가 있었고, **잠금·해제의 근거가 문서에 없으면 그 실수가 반복된다.**

#### 갱신이 강제되는 트립와이어 2건 — PRESERVE 위반이 아니다

| 대상 | 왜 갱신인가 |
|---|---|
| `server/tests/test_songcue_bundle.py`의 `_TOOLS_EXPECTED_HUNK_OLD_STARTS` | 주석이 스스로 *"tools.py를 정당하게 고치는 후속 SPEC은 이것을 의도적으로 갱신해야 하며 그것이 요점이다"*라고 선언한다. PRECHK가 이미 한 번 갱신했다. **보호구역 교차 단정은 계속 성립해야 한다** |
| `server/tests/test_prechk_verdicts.py`의 재타이핑 정본 3단정 | 어휘 확장이 승인 사항이므로 이 정본을 갱신하는 것이 집행이다. **단 형태를 약화시키지 않는다** — 집합 동일성 · 레지스트리 키 동일성 · 레지스트리 **순서** 동일성 셋을 모두 유지한다 |

**PRECHK의 `progress.md`는 손대지 않는다.** `server/tests/test_prechk_patch.py:310-317` · `test_prechk_macro.py:49` · `test_prechk_inventory.py:196`이 그 문서를 읽으며, 특히 `DESCOPE: ASSUMPTION-27` 접두 행이 **정확히 1건**이어야 한다. 본 SPEC의 게이트 행은 자기 `progress.md`에 쓴다.

---

## D. 제외 범위 (Out of Scope)

### Out of Scope — 꼬리 초과 판정

유니버스 마지막 픽스처의 점유가 용량을 넘어 다음 유니버스로 걸치는지는 **판정하지 않는다.** 근거 셋:

1. **용량 `B`에 대한 저장소 근거가 0건**이다(`research.md` §5.1). 512를 코드에 박는 것은 미검증 관례의 하드코딩이다.
2. **현재 코드는 유니버스를 넘는 점유를 클러스터에 넣지 못한다** — 구조적으로 비가시하므로 오늘 이 축을 켜는 것은 새 자료구조를 요구한다.
3. **용량을 런타임에 읽으려면 `DEFAULT_RIG_CONTEXT_PATHS`에 11번째 키가 필요하고 그 순간 `server/tests/test_tools.py:511-522`의 정확 10키 단정이 깨진다.** 폭 상계 축은 신규 경로 키 **0건**으로 성립하므로(`fixture_types`가 이미 있다) **꼬리 축만이 계약 변경을 요구한다.**

**`ASSUMPTION-33`으로 명시하고 실측 리그에서 발생하지 않음을 산술로 기록한다**(유니버스 1 최악 종단 467, 유니버스 2는 431). 후속 SPEC이 용량을 실측하면 그때 연다.

### Out of Scope — 픽스처 → 점유폭 조인 복원

`ASSUMPTION-27`은 후보 12건 전건 부정으로 닫혔고 본 SPEC은 그것을 **뒤집지 않는다.** 조인을 되살리려면 응답기 확장(`console/lua/**` PRESERVE 위반)이나 다른 쇼파일이 필요하다. 상계 논증은 조인 없이 성립하는 **더 약한 명제**이며 그것이 본 SPEC의 전부다.

### Out of Scope — 겹침 발견 후 주소 재배치

PRECHK와 동일하게 **판정하고 보고한다.** 패치 변경은 리그의 물리 배선과 결합된 결정이고 되돌리기 비용이 크다.

### Out of Scope — 다중 브레이크 픽스처 지원

`ASSUMPTION-31`이 연속 블록을 전제하며, 브레이크를 프로퍼티로 얻는 경로가 **0건**이다. 브레이크가 둘인 픽스처를 정확히 다루는 것은 관측 경로가 생긴 뒤의 일이다.

### Out of Scope — 기존 스키마 드리프트 2건의 정정

`PatchEvaluation.to_dict()`가 `design.md` §5.1에 없는 4키를 내고 툴 페이로드가 `macro`에 7번째 키를 주입하는 드리프트가 **이미 존재한다**(`research.md` §8.4). 본 SPEC의 스키마 정본은 그것을 **명시하되 정정하지 않는다** — 정정은 본 SPEC의 요구와 무관하며 툴 층 스키마 계약을 별도로 정의해야 하는 작업이다.

---

## E. 참조 구현

| 참조 | 좌표 | 무엇을 계승하는가 |
|---|---|---|
| 주소 그룹핑 | `server/prechk/patch.py`의 `_address_duplicates` | 폭과 무관하고 `type_mode_ok`도 요구하지 않는 `(유니버스, 주소)` 정렬. **상계 경로가 재사용할 유일한 지점** — `_range_overlaps`는 `widths={}`이면 정렬 자체가 일어나지 않아 재사용 불가 |
| 조회 예산 상한 | `server/orchestrator/tools.py`의 `RIG_DRILLDOWN_QUERY_CAP`과 `drill_into` | 자식당 예산 소모와 소진 표기 형상. **다만 소진 처리는 반대로 해야 한다** — 거기서 소진은 그 자식에 국소적이지만 여기서는 상계를 오염시킨다(`research.md` §4.1) |
| 순회 실패 분류 | `server/orchestrator/tools.py`의 `REASON_UNRESOLVED` / `REASON_UNREACHABLE` | 설정 결함과 운영 조건의 분류 규칙. 새 규칙이 아니라 기존 규칙의 적용 |
| 부분 커버리지 고지 | `server/prechk/patch.py`의 `_judgeable_without_width` | 한 행의 `reason`에 슬롯을 열거하는 형상. `skipped_checks`가 kind로 중복 제거하므로 kind당 1행만 도달한다 |
| PRESERVE 상시 테스트 | `server/tests/test_songcue_bundle.py` | BASE 40자 SHA 고정 · 범위 고정 테스트 · hunk 봉쇄 machinery. **단 상수를 복사하면 게이트가 엉뚱한 곳을 지킨다**(`research.md` §9.3의 수치 증명) |
| 닫힌 어휘 | `server/prechk/verdicts.py` | 레지스트리 + 발생시키는 validator + 재타이핑 정본. **확장 선례는 0건이므로 본 SPEC이 선례를 만든다**(`research.md` §7.5) |
