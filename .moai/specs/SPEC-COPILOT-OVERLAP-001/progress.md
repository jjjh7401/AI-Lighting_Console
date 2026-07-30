# SPEC-COPILOT-OVERLAP-001 — 진행 기록 (progress)

> **인용 규율.** 본 SPEC의 정본(`spec.md` · `acceptance.md`)은 **줄번호로 인용하지 않고** 안정 토큰만 쓴다. `파일:줄`은 **코드 · 룰북 · 응답기 프로토콜 · 타 SPEC 아티팩트**에만 쓴다. 요구·인수 토큰은 슬러그 포함 완전형만 쓴다(축약형 **0건**). 근거 등급은 `[코드]` · `[문서]` · `[실측]` · `[미확정]`이며 **`[실측]`은 라이브 콘솔 직접 관측만**을 가리킨다.

## §0 인수인계 — 여기서 시작한다 (2026-07-30)

### 한 문단

**무엇**: 픽스처를 자기 DMX 점유폭에 잇는 조인 키가 없어도, **열거 가능한 모드 전체의 폭 최대값**을 상계로 삼아 *"겹침 없음"*을 증명한다. 증명되지 않으면 **충돌이 아니라 미확정**으로 보고한다. PRECHK가 수행하지 않고 수행하지 않았다고 보고한 축을 되살리되 **판정의 비대칭을 계약으로 만든다.**
**상태**: **plan-phase 완결 · audit 대기.** 아티팩트 7종(`research` · `spec` · `acceptance` · `CONTRACT` · `design` · `plan` · 본 문서). REQ 18 · AC 21 · ASSUMPTION 31~35 · 마일스톤 M0~M8.
**열린 사용자 접점**: **0건** — 어휘 확장 승인을 착수 전에 받았다.
**라이브 세션**: **0회** — 필요한 값이 전부 PRECHK에 실측 전재되어 있다.

### 읽는 순서

| 순서 | 무엇을 알려주나 | 어디 |
|---|---|---|
| 1 | **왜 이 SPEC이 존재하나 / 무엇이 사실로 확립됐나** | `research.md` §1(출처) → §3(산술) → **§4(건전성 전제 3건 — 상계가 상계가 아닐 수 있는 경우)** |
| 2 | 무엇을 만들기로 했나 | `spec.md` — REQ 18 · §C PRESERVE와 ASSUMPTION 5건 · §D Out of Scope |
| 3 | 무엇을 통과해야 하나 | `acceptance.md` — AC 21 · 역추적표 · 계수 |
| 4 | **협상 불가 결정과 마일스톤 경계** | `CONTRACT.md` — §2 D-1~D-8 · §4 **BASE 세 개** · §5 M0~M8 · **§8 비준 기록 11건** |
| 5 | 왜 이 형상인가 | `design.md` — 슬롯 A~I · 기각 25건 · 합성 리그 19 · 뮤테이션 35 |
| 6 | 어떤 순서로 만드나 | `plan.md` — §B M0~M8 · §C 게이트 · §G Phase 4 권고 |
| 7 | 조사 원문(가장 김) | `research.md` 전문 — 필요할 때만 |

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

### 다음 담당자가 먼저 할 일

**M0다.** `ASSUMPTION-34`(`state` 표면만으로 3단 순회가 도달하는가)를 인메모리 프로토타입으로 닫는다 — 라이브가 필요 없고 `cycle_type=none`이며 프로토타입은 커밋하지 않는다. `GO`면 `server/safety/**` 무변경이 확정되고, 부정이면 `spec.md` §C의 PRESERVE 서술을 개정한 뒤 M6·M7의 형상을 다시 본다. **M0 이전에 M1에 착수하지 않는다.**

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

**라이브 프로브를 돌리지 않은 근거**: PRECHK가 plan-phase에 사전 프로브를 돌린 것은 1차 산출물의 성립이 *"픽스처 주소를 읽을 프로퍼티명이 존재하는가"* 하나에 걸려 있었기 때문이다(`progress.md:85`). 본 SPEC의 성립은 **이미 실측된 값**에 걸려 있고 그 값은 전재되어 있다. 남은 라이브 항목은 전부 `ASSUMPTION`이며 **어느 것도 착수를 막지 않는다.**

**scout에게 이미 알려진 것을 재도출하지 말라고 명시했다** — §E.6 ④ · §E.7 · §E.8 · §E.9를 먼저 읽히고 그 위에 없는 것만 찾게 했다. 그 결과가 아래 정정 5건이다.

### 조사가 정정한 선행 서술 5건

| # | 선행 서술 | 정정 |
|---|---|---|
| 1 | §E.6 ④ *"간격이 상계 **이하**라 미확정"* | **off-by-one.** 술어는 `간격 < 상계`다 |
| 2 | §E.7 *"어휘 확장은 **4곳**을 원자적으로"* | **파일 단위로는 맞고 편집점 단위로는 과소.** 기존 축 값 추가 **3편집점** / 새 축 **10편집점** + 배선 3 |
| 3 | §E.7 ⑤가 tools.py 보호구역 **①만** 기록 | **② dedupe 루프 BASE 범위 `(537, 582)`가 누락됐다.** 이번에 처음 실측 |
| 4 | §E.7 ⑤의 *"순수 추가 = 삭제 0"* 기계 규칙 | **`tools.py`도 삭제 1행이다.** 그 규칙을 적용하면 즉시 실패한다 |
| 5 | §E.9 *"다음 SPEC BASE = `b406a7b`"* | **실제 BASE는 1커밋 위 `85a4b23`.** 코드 무변경 문서 커밋이라 게이트 의미는 동일 |

추가로 **선행 기록이 추정을 단정으로 적은 것 1건**을 잡았다 — `progress.md:1113`의 *"`childCount 1024`는 유니버스 개수"*는 근거가 병기되지 않았고 `DmxUniverses/1`의 자식 `'DMX 2'`와 정합하지 않는다. **`[실측]`으로 인용하면 안 된다.**

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

**저장소에서 512를 유니버스 용량으로 쓰는 유일한 지점이 `progress.md:1113`이며 그 문장의 내용이 *"근거를 찾지 못했다"*다.** 자기참조 외 독립 근거는 없다.

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
artifact_lines: "plan 827 · design 749 · research 565 · acceptance 225 · spec 171 · CONTRACT 168"
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
  cross_document_drift: "0 — 마일스톤 9행 AC 배정 · 고정 문자열 7종 · 세 BASE 전건 일치"
  design_slot_milestone_alignment: "9 슬롯 전부에 집행 마일스톤 명시. M0만 슬롯 없음(전제 판정이며 형상 결정 아님)"
  mutations_proposed: 35   # design.md §5 — 각 뮤테이션이 어느 AC를 죽이는지 명시
  synthetic_rigs: 19       # design.md §4 — 경계값 2건 포함(간격 == 상계, == 상계-1)
  rejected_designs_recorded: 25
  live_measurement_claims_by_this_spec: 0
gate_false_positives:      # 감사가 재검출할 수 있는 것 — 전부 의도다
  - "축약 토큰 정규식 `[^A-Z-](AC|REQ)-[0-9]{3}` 히트 1건 = CONTRACT.md의 **금지 형태를 명명하는 규칙 문구 자신**"
  - "`spec.md:121` 형태 히트 2건 = 전부 `.moai/specs/SPEC-COPILOT-PRECHK-001/` **전체 경로 접두**를 가진 타 SPEC 인용이며 규약이 허용한다"
  - "경로 없는 `design.md:143` 히트 1건 = CONTRACT.md §8의 **위험을 서술하는 비준 기록 자신**"
  - "`research.md`의 `· 101 · 143 …` = **주소값**이며 중점 뒤 3자리 축약 토큰이 아니다"
known_gaps:
  - "**건전성 전제 3건이 다른 쇼파일을 요구한다** — 연속 블록(`ASSUMPTION-31`) · `DMXChannels` 자식 수 = 슬롯 수(`ASSUMPTION-32`) · 유니버스 용량(`ASSUMPTION-33`). 현 쇼파일은 픽스처타입 1종뿐이라 앞 둘의 실험이 원리적으로 불가능하다. 본 SPEC은 **셋 중 하나라도 거짓이면 `bound_proves_clear`를 내지 않는 형상**으로 출하한다 — PRECHK가 FID를 배제하고 출하한 것과 같은 형태다."
  - "**`bound_inconclusive` 분기는 라이브로 증명할 수 없다.** 현재 쇼파일 17 인접쌍 전부가 상계를 통과해 발동 입력이 **0건**이며 합성 인메모리 리그만이 덮는다. **라이브 증거를 요구하는 인수 조건은 원리적으로 충족 불가능하므로 쓰지 않았다** — 감사가 *'GO 분기만 실측됐다'*를 지적으로 올릴 수 있고 그 지적은 부당하다. 근거는 `research.md` §3.3."
  - "**타입 수 `T`의 실측 기록이 0건이다**(`ASSUMPTION-35`). 예산 상한 결정이 `T`에 걸리지만 보수적으로 잡고 소진 시 `not_performed`를 내면 `T`를 몰라도 안전하다."
  - "**절단 계수 비교의 4번째 사본을 만든다.** 기존 3건의 `childCount` 부재·0 정책이 서로 달라 단순 통합이 `acceptance.md` §D의 *'zero fixtures는 유효한 리그'*와 충돌한다. `CONTRACT.md` D-8이 수렴을 명시적으로 금지했고 그것은 **별도 리팩터 SPEC의 일**이다."
  - "**상속되는 스키마 드리프트 2건을 정정하지 않는다** — 판정 계층이 정본에 없는 4키를 내고 툴 계층이 `macro`에 7번째 키를 주입해 정본 6키가 이미 거짓이다. `spec.md` §D가 명시적 Out of Scope로 뒀다. 본 SPEC의 스키마 정본은 그것을 **명시하되 고치지 않는다.**"
  - "**`plan.md`에 REQ 토큰이 5건만 등장한다**(`design.md`는 18건 전건). plan은 마일스톤·절차 문서이고 요구 추적이 **AC를 경유**하며 AC 21건은 전건 등장한다. 역추적표가 REQ 18/18을 커버하므로 사슬은 끊기지 않으나, **감사가 이것을 요구 추적 약화로 지적할 수 있다.** 지적되면 `plan.md` 마일스톤 표에 REQ 열을 추가하는 것이 최소 수정이다."
  - "**plan-audit 미실시.** 본 신호를 낸 직후 독립 감사 1회를 돈다. PRECHK가 1회차 FAIL 0.76에서 지적 11건을 받았고 그중 P1 4건이 전부 기계검증성·문서 정합 층이었다 — 같은 층에서 지적이 나올 것을 예상한다."
next: "**독립 plan-audit 1회차.** 작성자가 아닌 주체가 7문서를 채점한다. 그 뒤 사용자 Kickoff 접점(현재 열린 접점 0건이므로 형식적)을 거쳐 **run-phase 착수 — M0 전제 판정부터.** M0는 `cycle_type=none`이며 인메모리 프로토타입으로 `ASSUMPTION-34`를 닫고 프로토타입은 커밋하지 않는다. **M0 이전에 M1에 착수하지 않는다** — `ASSUMPTION-34` 부정이면 PRESERVE 서술이 바뀌고 그것이 M6·M7의 형상을 바꾼다."
```

## §3 Phase 4 Mode Selection — 미도래 (오케스트레이터 소유)

> 본 절은 **오케스트레이터가 첫 run-phase 스폰 전에 작성**하는 구속력 있는 기록이다. `plan.md` §G의 대응 절은 **권고**이며 오케스트레이터가 확정하거나 기각한다. 어긋나면 **본 절이 이긴다.**
>
> 이 헤딩은 plan-phase 완결 시점에 **선제 생성**되었다 — 선행 SPEC에서 `plan.md`가 존재하지 않는 `progress.md` 절을 구속력 있는 기록으로 지목해 끊어진 참조를 만든 사례가 있었고, BUSKWIZ가 선제 생성으로 그것을 고쳤으며 PRECHK가 계승했다. **본문이 채워지기 전까지 이 절은 비어 있음이 정상이며, 비어 있다는 사실 자체가 "아직 스폰하지 않았다"의 기록이다.**

`plan.md` §G의 권고는 **sub-agent 순차 · 초기 폭 1**이며 근거 셋은 어휘 사슬(M1이 단독 선행물이고 그것 없이는 M3·M4·M5가 **import조차 실패**한다) · 파일 교집합(교집합 0인 쌍이 M7 하나뿐이고 그것도 M6 커밋에 걸려 있다) · M0가 새 도메인을 만들지 않는다는 것이다.

**오케스트레이터는 M0 실측 후에 이 권고를 확정하거나 개정한다.** PRECHK가 폭 1로 확정한 뒤 M0 실측이 미지를 닫아 M4가 자립 슬라이스가 되자 **§F.1로 폭 2로 개정한 선례**가 있다(`.moai/specs/SPEC-COPILOT-PRECHK-001/progress.md` §F.1). **폭을 미리 약속하지 않는다.**

**읽기 전용 scout 병렬은 폭 권고와 무관하게 계속 유효하다** — 본 SPEC plan-phase가 scout 4개를 동시에 돌려 충돌 0건이었고 선행 기록 정정 5건을 냈다.
