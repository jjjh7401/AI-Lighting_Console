# CONTRACT — SPEC-COPILOT-OVERLAP-001 (오케스트레이터 소유 · 협상 불가)

> **이 파일은 `design.md`와 `plan.md`를 병렬로 쓰는 두 작성자에게 배포되는 고정 계약이다.** 정본 3종(`research.md` · `spec.md` · `acceptance.md`)이 닫힌 뒤 오케스트레이터가 직접 작성했다. **워커는 이 값을 협상하거나 재해석하지 않는다** — 어긋나면 코디네이터가 전수 검증에서 잡는다.
>
> 병렬이 정당한 이유: 계약이 여기 고정됐다. PRECHK plan-phase가 *"`design.md` + `plan.md` 병렬 2는 정본 3종이 닫혀 계약이 고정된 뒤에만 정당하다"*고 규정했고 그 조건이 충족됐다.

## 1. 계수 — 기계로 확인됐다

| 항목 | 값 |
|---|---|
| BASE SHA | `85a4b2389003cb61b0ab72eb4aa8d6b2ff90b94a` |
| 착수 baseline | **2758 passed · 5 skipped · 0 failed** (직접 실측) |
| 요구 | **18** — `REQ-OVERLAP-001`~`REQ-OVERLAP-018` |
| 인수 조건 | **21** — `AC-OVERLAP-001`~`AC-OVERLAP-021` |
| 역추적표 행 | **18** — 커버 누락 0 |
| 역추적표 제외 AC | **3** — `AC-OVERLAP-019`(형상) · `AC-OVERLAP-020`(전제) · `AC-OVERLAP-021`(종단) |
| 미검증 전제 | **5** — `ASSUMPTION-31`~`ASSUMPTION-35` |
| 마일스톤 | **9** — M0~M8 (아래 §5) |
| 라이브 세션 | **0회** |
| clarification 마커 | **0** — 두 문서도 0을 유지한다 |

**두 문서는 이 계수를 바꾸지 않는다.** 새 요구·새 AC·새 전제를 만들지 마라. 필요하다고 판단되면 문서에 쓰지 말고 **코디네이터에게 보고**하라.

## 2. 오케스트레이터가 이미 결정한 설계 사항 — 재논의 금지

조사가 상반된 선례나 복수 후보를 낸 지점을 코디네이터가 닫았다. 근거까지 함께 적으니 두 문서는 이 근거를 인용하되 결론을 바꾸지 마라.

### D-1. 순회 모듈 배치 = `server/prechk/` **신규 모듈**

파일명 **`server/prechk/footprint.py`**. 대응 테스트 `server/tests/test_prechk_footprint.py`.

근거: 후보 4종 중 경계 위반 0건이 이것뿐이다(`research.md` §6). `inventory.py` 확장은 `server/tests/test_prechk_inventory.py:693-699`가 즉시 깨지고 `InventoryPolicy` 도크스트링이 명시적으로 금지한다. `query.py` 확장은 모듈 계약 위반이다. 핸들러 내부는 import 불가로 단위 검증을 잃으며 `bound_inconclusive`가 합성 리그로만 도달 가능한 본 SPEC에서 치명적이다.

**파일명 안전 확인**: `_FORBIDDEN_PROPERTY_NAMES`는 `"Footprint"`를 **정확 문자열**로 금지하지만 소문자 모듈명은 그 스캔의 대상이 아니다(문자열 상수 집합만 검사하며 정확 일치다). 그러나 **모듈 안에서 `"Footprint"` · `"Channels"` · `"ChannelCount"` · `"Universe"` · `"Address"` · `"No"` · `"Break"`를 문자열 리터럴로 쓰지 마라** — 그 순간 스캔이 죽인다.

**제약**: 이 모듈은 `server.orchestrator.tools`를 import하지 않는다(하드 순환). **경로와 예산 상한을 인자로 받는 순수 함수**로 만든다.

### D-2. 경로 수령 = `rig_paths` 경유 — 리터럴 고정하지 않는다

근거: `Patch/FixtureTypes`는 이미 `DEFAULT_RIG_CONTEXT_PATHS`에 있고 2026-07-22 라이브 검증 후 기본값으로 승격됐다. `get_rig_context`가 이미 `rig_paths`를 통해 그것을 조회한다. 상반된 선례인 `FIXTURE_ROOT` 리터럴 고정은 **폐기 경로 재주입 방지**라는 별개 사유(`REQ-PRECHK-002`가 `Patch/Fixtures`를 금지한다)에서 나왔고, `Patch/FixtureTypes`에는 그 위험이 없다.

따라서 `server/prechk/footprint.py`에 `"Patch/FixtureTypes"`를 리터럴로 박지 않는다 — 핸들러가 `rig_paths["fixture_types"]`를 넘긴다. 그러면 `server/web/app.py` → `server/web/session.py` → `server/orchestrator/tools.py`의 오버라이드 이음새가 이 축에도 적용된다.

### D-3. 섹션 가드 = **별도 상수를 신설**하고 `create_macro` 분기 밖에서 검사한다

`PRECHK_RIG_SECTIONS`에 `"fixture_types"`를 **추가하지 않는다.** 그 가드는 `create_macro=True` 분기 안에만 있어 추가하면 같은 오버라이드 누락이 인자에 따라 다른 결과를 낸다. 그리고 `server/tests/test_prechk_tool.py:884-905`·`:907`이 누락 섹션 **집합**을 메시지로 단정하므로 추가하면 그 두 테스트가 깨진다.

**신설**: 상계 축이 요구하는 섹션만 담는 별도 튜플을 만들고, `create_macro`와 무관하게 항상 검사한다. 누락 시 메시지는 **어느 섹션이 빠졌는지 이름으로 말하고** 풀 판독 실패를 암시하지 않는다.

### D-4. `overlap_basis` 부착 = **신규 최상위 키 · 리그 전역 스칼라**

근거: 기존 페이로드 블록 6개가 전부 정확 키집합으로 잠겨 있고 무충돌 자리는 최상위 키 하나뿐이다(`research.md` §8.1). 최상위 키의 **내부 구조는 어떤 테스트도 단정하지 않으므로** 그 아래 중첩 구조는 자유다.

**정직성 제약 2건**:
- 리그 전역 스칼라는 **수행된 비교 전체의 최약 등급**이어야 한다. 3슬롯이 비교되지 않은 상태에서 `bound_proves_clear`를 리그 전역으로 찍는 것은 결함이다.
- `range_overlap_bound_inconclusive`는 `skipped_checks`가 kind로 중복 제거하므로 **kind당 1행**만 리포트에 도달한다. 유니버스별 다중 행 불가 — 한 행의 `reason`에 유니버스·슬롯을 열거한다(기존 부분 커버리지 고지와 같은 형태).

**그리고 `AC-OVERLAP-016` ④가 신규 최상위 키에 정확 키집합 단정을 새로 만들 것을 요구한다** — 얹기만 하면 아무것도 안 깨지지만 아무도 지키지 않는다.

### D-5. 어휘 = 신규 축 1개 + 기존 축 값 1개. 레지스트리 **맨 끝** append

```
overlap_basis = { exact_widths, bound_proves_clear, bound_inconclusive, not_performed }
SKIPPED_CHECK_KIND += range_overlap_bound_inconclusive
COLLISION_KIND     — 무변경
FIXTURE_VERDICT    — 무변경
```

라벨표 이름은 **`OVERLAP_BASIS_LABELS`** 로 강제한다(AST 스캔의 표 인식이 `_LABELS` 접미사다). 코드값 생산자 상수는 `server/prechk/patch.py`의 기존 `validate(...)` 상수 블록에 두고 표현 계층이 **이름으로 import**한다 — 표현 계층에서 코드값을 리터럴로 재타이핑하는 것은 라벨표 안에서만 허용된다.

레지스트리와 테스트 정본 리스트 양쪽에 **맨 끝 append**. 근거: 순서를 보는 단정이 하나뿐이고, 런타임 순서 의존이 0건이며(`validate()`의 오류 문자열이 `sorted()`를 쓴다), append는 기존 5줄을 바이트 동일하게 남겨 두 편집의 일치를 리뷰가 눈으로 확인할 수 있다.

### D-6. 가드 루프 = **레지스트리 순회로 바꾼다**

표현 계층의 import 시점 가드 루프가 하드코딩 5-튜플이며 **신규 축을 빠뜨려도 어떤 테스트도 실패하지 않는다**(`research.md` §7.2). 스위트가 못 잡는 유일한 단계다.

**결정: 루프를 `CLOSED_VOCABULARIES` 순회로 바꿔 이 단계를 구조적으로 없앤다.** `AC-OVERLAP-014` ⑦이 그 형태를 인정한다. 튜플에 항목을 추가하는 것으로 끝내지 마라 — 그러면 다음 축을 추가하는 사람이 같은 함정을 만난다.

### D-7. 재사용 = `_address_duplicates`의 그룹핑. `_range_overlaps`는 재사용 불가

`_range_overlaps`는 폭이 없으면 `intervals`가 비어 **정렬 자체가 일어나지 않는다.** 상계 경로는 *"폭과 무관하게 주소만으로"* 성립해야 하므로 그 함수를 탈 수 없다.

`_address_duplicates`는 폭과 무관하고 `type_mode_ok`도 요구하지 않는다 — **상계 논증의 요점이 "어느 모드를 쓰는지 몰라도 성립"이므로 이쪽 술어가 맞다.** 그 함수의 `(유니버스, 주소)` 그룹핑을 추출해 **키 집합**을 상계 경로가 쓴다. 인접차와 최소값은 신규(저장소에 그 연산이 0건).

### D-8. 절단 계수 비교 헬퍼 = 수렴시키지 않는다

구현 3건의 `childCount` 부재·0 정책이 **서로 다르다**(예외 / 관용 / 예외+0거부). 단순 통합은 `acceptance.md` §D의 *"zero fixtures는 유효한 리그"*와 매크로 풀의 실측 근거를 충돌시킨다.

**결정: 본 SPEC은 4번째 사본을 만들지만 수렴을 시도하지 않는다.** 순회는 **자기 정책**을 갖는다 — 1·2단은 목록 완전성(짧으면 상계 미계산), 3단은 계수 존재성(`childCount`가 정수면 성공). 수렴은 별도 리팩터 SPEC의 일이며 그 사실을 문서에 적는다.

## 3. PRESERVE — 두 문서가 같은 목록을 인용한다

PRECHK 목록 전량 계승 + **`server/safety/**` 추가**(본 SPEC은 프로퍼티를 0건 읽으므로 신규 예외 0지점 — 단 `ASSUMPTION-34`이며 M0가 닫는다).

**갱신이 강제되는 트립와이어 2건은 PRESERVE 위반이 아니다** — songcue hunk 트립와이어, 어휘 정본 3단정. 형태를 약화시키지 않는 것이 조건이다.

**PRECHK의 `progress.md`는 무변경**이며 `DESCOPE: ASSUMPTION-27` 접두 행이 정확히 1건으로 유지된다.

## 4. BASE 두 개 — 절대 섞지 않는다

| 용도 | SHA |
|---|---|
| 본 SPEC의 BASE(스위트·회귀 기준) | `85a4b2389003cb61b0ab72eb4aa8d6b2ff90b94a` |
| **PRECHK PRESERVE 게이트 기준점 — 영구 불변** | `95687a0e0eba90b325daf76efbd0ac197e69e2fc` |

BASE 상대 좌표(실측 완료): tools.py 보호구역 `(247, 251)`과 `(537, 582)`. safety 심볼: `console.py` 96·372, `gate.py` 114·120·598.

**`tools.py`에 "삭제 0행" 규칙을 쓰지 마라** — 실측 삭제가 1행이며 즉시 실패한다. hunk 위치 봉쇄를 쓴다.

## 5. 마일스톤 M0~M8 — 오케스트레이터가 확정했다

두 문서는 이 경계를 그대로 쓴다. `plan.md`가 각 마일스톤의 절차·산출·게이트를 상세화하고, `design.md`가 설계 슬롯을 이 경계에 정렬한다.

| # | 이름 | cycle_type | 무엇을 닫나 | 배정 AC |
|---|---|---|---|---|
| **M0** | 전제 판정 — `state`만으로 도달하는가 | **none**(코드 변경 0) | `ASSUMPTION-34`. 인메모리 프로토타입으로 갈리며 **라이브 불필요**. `GO`면 `server/safety/**` 무변경 확정, 부정이면 범위 재개정 | `AC-OVERLAP-020` |
| **M1** | 어휘 확장 | tdd | 신규 축 + 기존 축 값 + 라벨표 + 가드 루프 구조 변경 + 정본 3단정 갱신. **교차 슬라이스 선행물** | `AC-OVERLAP-014` |
| **M2** | 순회 모듈 | tdd | `server/prechk/footprint.py` 신설 — 3단 순회 · 완전성 술어 2종 · 예산 · 실패 분류 | `AC-OVERLAP-001` · `AC-OVERLAP-002` · `AC-OVERLAP-003` · `AC-OVERLAP-004` · `AC-OVERLAP-005` · `AC-OVERLAP-006` |
| **M3** | 상계 판정 | tdd | 간격 산수 · 술어 `간격 < 상계` · 유니버스 내부 · 주소 유효 범위 · 미확정을 충돌로 안 냄 | `AC-OVERLAP-008` · `AC-OVERLAP-009` · `AC-OVERLAP-010` · `AC-OVERLAP-011` · `AC-OVERLAP-012` |
| **M4** | 정확폭 우선 · 근거 배선 | tdd | 정확폭 우선순위 · `overlap_basis` 최상위 키 · 상계 근거 페이로드 도달 · 순회 실패 시 리포트 나머지 생존 | `AC-OVERLAP-007` · `AC-OVERLAP-013` · `AC-OVERLAP-016` |
| **M5** | 리포트 | tdd | 라벨 · 요약 도달 · `bound_proves_clear`의 관측 범위 한정 | `AC-OVERLAP-015` · `AC-OVERLAP-017` |
| **M6** | 툴 배선 | tdd | `rig_paths` 수령(D-2) · 별도 섹션 가드(D-3) · 예산 스레딩 | `AC-OVERLAP-018` |
| **M7** | PRESERVE 상시 테스트 · 게이트 | tdd | 이월 항목 집행 — 신규 테스트 파일 · BASE `95687a0e…` 고정 · hunk 봉쇄 · 트립와이어 갱신 | `AC-OVERLAP-019` |
| **M8** | 종단 통합 | tdd | 툴 표면 4값 전량 산출 · 역방향 FAIL 검증 · 스위트 | `AC-OVERLAP-021` |

**배정 합 = 21. 중복 0 · 누락 0.** 두 문서가 이 배정을 재기술할 때 합이 21임을 유지하라.

**M0 이전에 M1에 착수하지 않는다** — `ASSUMPTION-34`가 부정이면 PRESERVE 서술이 바뀌고 그것이 M6·M7의 형상을 바꾼다.

**M1은 교차 슬라이스 선행물이다** — 어휘가 없으면 M3·M4·M5가 값을 낼 수 없다. 오케스트레이터가 M1을 순차로 집행한 뒤 이후 폭을 판단한다.

## 6. 이 프로젝트의 결함 계열 — 두 문서가 공유하는 판단 렌즈

1. **"판독 실패"와 "그런 것이 없음"을 섞으면 결함이다.** 선행 SPEC이 이 계열로 **7건**을 냈다. 코드가 방어 가능해도 **사용자가 읽는 문자열이 거짓**이면 결함이다.
2. **`node.childCount`와 `len(children)`을 함께 본다.** 열거가 짧으면 **상계도 상계가 아니다.**
3. **"스위트가 통과한다"는 "결함이 없다"가 아니다**(규율 16). P1 4건이 2721개 전부 통과하는 상태에서 살아 있었다. **신규 테스트는 수정 전 코드에서 실패함을 역방향으로 확인하고, 통과하는 테스트는 회귀 테스트가 아니라고 코드에 명시한다.**
4. **게이트가 결함을 비껴가는 형태를 의심한다**(규율 13). 대조 전에 페이로드를 지우는 정규화, 한 페이즈만 보는 필터, 명시적 `continue`.
5. **불완전한 집합에 판정을 단정하지 않는다.** PRECHK가 같은 항목에서 **두 번** 미끄러졌다.
6. **추측한 코드값·경로를 쓰지 않는다.** 실측 기록이 없으면 `[미확정]`으로 남기고 무엇을 측정하면 갈리는지 적는다.

## 7. 인용·등급 규율

- 정본(`spec.md` · `acceptance.md`)은 **줄번호로 인용하지 않고 안정 토큰만** 쓴다. `파일:줄`은 코드 · 룰북 · 응답기 프로토콜 · **타 SPEC 아티팩트**에만.
- 요구·인수 토큰은 **완전형만**. 축약형(`REQ-001`, 중점 뒤 3자리 숫자만) **0건**.
- 등급: `[코드]`(저장소 정적 조사) · `[문서]` · `[실측]`(**라이브 콘솔 직접 관측만**) · `[미확정]`.
- **본 SPEC은 라이브 세션 0회다. 따라서 두 문서가 자기 관측으로 `[실측]`을 주장하는 것은 0건이어야 한다** — 실측 값은 전부 `.moai/specs/SPEC-COPILOT-PRECHK-001/` 인용이며 그 사실을 밝힌다.
- clarification 마커 **0건**을 유지한다. 미결이 있으면 `[미확정]`으로 쓰고 무엇을 측정하면 갈리는지 적는다.
