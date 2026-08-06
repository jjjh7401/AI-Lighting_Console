# SPEC-COPILOT-AUTOPATCH-001 — 진행 기록 (progress)

> **인용 규율**: 본 SPEC의 `spec.md`·`acceptance.md`는 행 번호로 인용하지 않는다 — 안정 토큰만 쓴다.
> `file:line`은 코드·룰북·`console/lua/PROTOCOL.md`·**다른** SPEC의 아티팩트에만.
> **증거 등급**: `[코드]` · `[문서]` · `[실측]` · `[미확정]`.

## §0 인수인계 — 여기서 시작한다 (2026-08-05)

**상태**: **plan-phase 아티팩트 6종 작성 완료 · plan-audit 대기.**
REQ **26건**(REQ-AUTOPATCH-001~026) · AC **27건** · ASSUMPTION 5건(71~75) · 마일스톤 9개(M0~M8) ·
라이브 세션 **2회 계획** · clarification 마커 0건 · 설계 슬롯 5건 전부 종결.

**이 SPEC이 1단계와 근본적으로 다른 점**: **콘솔에 쓴다.** 1단계는 읽고 비교만 했다.
패치는 픽스처를 **생성**하고, 이 앱에는 실행 취소·백업 복원 경로가 **없다**.
그래서 요구사항의 절반 이상이 기능이 아니라 **되돌릴 수 없는 쓰기를 사람이 통제하게 만드는 장치**다.

### 읽는 순서

| # | 무엇을 | 어디서 |
|---|---|---|
| 1 | 무엇을 만들기로 했나 | `spec.md` — REQ 26건 · §C `의존 범위 한정` · §C ASSUMPTION 71~75 · §C PRESERVE · §D Out of Scope 6건 |
| 2 | 왜 M0가 먼저인가 | `plan.md` §A.2 — 쓰기에 필요한 값 둘(FID · DMXMode 핸들)이 **읽히는지조차 미확정**이다 |
| 3 | 부정이면 어떻게 되나 | `plan.md` §A.3 — 가정 5건의 부정 처리표. 부정은 실패가 아니라 **기능 축소**다 |
| 4 | 무엇을 통과해야 하나 | `acceptance.md` — AC 27건 · §C.0 역추적표(REQ 26/26) · §C.0a 마일스톤 배정 · §F DoD |
| 5 | 어떻게 만들 것인가 | `design.md` — §3 흐름도 · §5 설계 슬롯 5건 · §6.3 비공허성 대조군 8건 · §7 안티패턴 10건 |
| 6 | 근거는 무엇인가 | `research.md` — 패치 기법 · FID 난제 · 타입 핸들 · 비가역성 · 1단계 상속 |

### 함정 6건 — 먼저 읽어라

1. **`ChangeDestination`/`CD`를 어디에서도 보내지 마라.** 플러그인 안에서도, `run_commands`로도.
   보내면 패치가 `nil`을 반환하고 **아무것도 생성되지 않는다**
   (`server/rulebook/assets/v2.4.2/30_plugin_patterns.md:20-29`).
2. **슬롯은 FID가 아니다.** `precheck_patch`는 FID를 읽지 못한다
   (`server/prechk/inventory.py:57`, REQ-PRECHK-005). 슬롯을 FID로 쓰면
   **MA3가 조용히 받아들이고 엉뚱한 픽스처를 덮는다**
   (`server/rulebook/assets/v2.4.2/31_choreography_patterns.md:203-209`).
3. **`FixtureType`·`Mode`는 표시 문자열이다.** 거기서 채널 수를 파싱하지 마라 —
   `ASSUMPTION-27`이 이미 반증했다(`server/prechk/patch.py:14-22`).
4. **플러그인이 오류 없이 끝난 것은 성공이 아니다.** `AddFixtures`는 실패 시 `nil`을 반환할 뿐이다.
   **검증 읽기가 성공의 유일한 근거다**(REQ-AUTOPATCH-023).
5. **`run_commands` 배열 길이는 1이다.** 플러그인 실행 호출에 다른 명령을 함께 넣지 마라.
   이름은 **작은따옴표**(큰따옴표는 거부됨).
6. **역산된 주소로 패치할 수 있다.** 1단계가 `absolute_back_calculated` 등급을 붙여 넘긴다.
   금지하지 않되 **승인 화면에 등급과 전제를 노출**해야 한다(design.md §5 슬롯 D).

### 기계 확인 커맨드

```bash
W=/Users/studiox/orca/workspaces/AI-Lighting_Console/spec-vwx-001
git -C "$W" rev-parse --abbrev-ref HEAD          # feature/SPEC-COPILOT-VWX-001 (1단계 위에 스택)
uv run pytest server/tests -q                    # 착수 기준선: 4898 passed / 7 skipped
uv run ruff check server/vwx server/tests/test_vwx_*.py
git -C "$W" diff --stat ca00bc5..HEAD -- console/lua server/safety server/prechk server/paperwork server/looks
```

### 다음 담당자가 먼저 결정할 것

- **M0 라이브 세션 일정**. 이것 없이 M2·M3·M6 설계가 확정되지 않는다.
- **테스트 쇼파일 확보**. M0·M8 둘 다 파괴적 측정을 포함하므로 **운영 쇼파일에서 하지 않는다.**
- `ASSUMPTION-71` 측정을 위해 **슬롯과 FID가 다른 픽스처**가 있는 쇼파일이 필요하다.
  없으면 판정이 INCONCLUSIVE로 끝나고 충돌 사전검사가 descope된다.

---

## Plan-phase log

### v0.1.0 — plan-phase 아티팩트 6종 작성 (2026-08-05)

착수 SHA **`ca00bc5c853bfe5d9391290f1b9db263610b4bfa`**(1단계 v0.1.7 완료 시점),
착수 baseline **4,898 passed · 7 skipped · 1 warning · 92.28s** — **직접 실측, 이월 인용 아님.**

작성 방식: **오케스트레이터 직접 작성.** 1단계 run-phase에서 dispatch 왕복이
코디네이터 재검증 → 지시문 번역 → 워커 해석 → 재검증의 **번역 왕복 2회**를 만들어 3라운드를
되돌려보낸 이력이 있다. 작성은 직접 하고 **감사만 분리**해 독립성을 올린다(작성자 ≠ 감사자).

| 아티팩트 | 내용 | 라인 수 |
|---|---|---|
| `spec.md` | REQ 26건 · ASSUMPTION 71~75 · Out of Scope 6개 H3 · PRESERVE 5경로 · `depends_on` | v0.1.1 |
| `plan.md` | 마일스톤 M0~M8 · 결정 A~G(미결 0) · 라이브 2회 · 테스트 골격 · §G Mode 권고 | 192 |
| `acceptance.md` | AC 27건 · §C.0 역추적표(REQ 26/26) · §C.0a 배정 합 27 · §F DoD | v0.1.1 |
| `design.md` | 변경 표면 · 흐름 · 위험 7건 · 설계 슬롯 5건(전부 종결) · 비공허성 8건 · 안티패턴 10건 | 216 |
| `research.md` | 증거 등급별 조사 8절 · 미확정 5건을 ASSUMPTION으로 승격 | 202 |
| `progress.md` | 본 문서 | 158 |

**합 1,476줄** — 커밋 시점 실측(`wc -l`).

---

## §E.1 Plan-phase Audit-Ready Signal

**상태: 작성 완료 · plan-audit 대기.** audit-ready 신호는 plan-auditor 통과 후 이 절에 기록한다.
감사 통과 전에 신호를 쓰지 않는 것은 **의도된 규율**이다 — 감사가 FAIL이면 신호가 거짓이 되기 때문이다.
(이 브랜치의 `.moai/specs/` 에는 같은 규율을 쓴 선행 SPEC이 없다. 유사 선례가 미머지 형제 브랜치에
존재하나 여기서 인용 가능한 자산이 아니므로 인용하지 않는다.)

기록 예정 값(감사 통과 시 확정):

```yaml
plan_status: (audit 대기)
plan_complete_at: (audit 통과일)
spec_version: "0.1.0"
base_sha: ca00bc5c853bfe5d9391290f1b9db263610b4bfa
baseline_measured: "uv run pytest server/tests -q → 4898 passed, 7 skipped, 1 warning in 92.28s"
artifacts: [spec.md, plan.md, acceptance.md, design.md, research.md, progress.md]
requirements: 26          # REQ-AUTOPATCH-001~026 (v0.1.1에서 026 신설)
acceptance_criteria: 27   # AC-AUTOPATCH-001~027 (v0.1.1에서 027 신설)
milestones: 9             # M0~M8. M0·M8만 cycle_type=none (라이브 측정)
assumptions_open: 5       # ASSUMPTION-71~75 — 전부 M0 라이브 판정 대상
live_sessions_planned: 2  # M0 전제 측정 · M8 종단 검증
decisions_closed: 7       # plan.md §A.4 결정 A~G
decisions_open: 0
design_slots_closed: 5    # design.md §5 슬롯 A~E
design_slots_open: 0
clarification_markers: 0
machine_gates:
  req_to_ac_coverage: "26/26 — acceptance.md 역추적표 REQ 행 26, 커버 누락 0"
  ac_milestone_assignment: "27 — M0 1 · M1 3 · M2 5 · M3 4 · M4 4 · M5 3 · M6 3 · M7 3 · M8 1. 중복 0 · 누락 0"
  ac_absent_from_traceability_table: "5 — AC-AUTOPATCH-001(전제 게이트) · AC-AUTOPATCH-023(툴 등록) · AC-AUTOPATCH-024(PRESERVE) · AC-AUTOPATCH-025(1단계 회귀) · AC-AUTOPATCH-026(라이브 통합). acceptance.md가 의도로 명시"
  out_of_scope_h3_headings: "6"
  nonvacuity_controls_required: 8   # design.md §6.3
known_gaps:
  - "ASSUMPTION-71~75 5건 전부 미판정 — M0 라이브 세션 전에는 M2·M3·M6 설계가 확정되지 않는다."
  - "테스트 쇼파일이 아직 지정되지 않았다. M0·M8 둘 다 파괴적 측정을 포함한다."
  - "ASSUMPTION-71 판정에는 슬롯≠FID 픽스처가 있는 쇼파일이 필요하다. 없으면 INCONCLUSIVE."
  - "CID/다른 idtype 축(research.md §3.3 경로 c)은 조사 부족으로 이번 범위 밖이다."
next: "plan-auditor 감사 → PASS 후 이 절에 audit-ready 신호 기록 → M0 라이브 세션 일정과 테스트 쇼파일 확보 → Implementation Kickoff Approval."
```

---

## §E.1a Plan-audit 결과

### 1회차 (round1) — 2026-08-06 — plan-auditor 독립 감사

**판정: FAIL** — Overall Score **0.80**(조화평균) < Tier L 임계 **0.85**.
전문: `.moai/reports/plan-audit/SPEC-COPILOT-AUTOPATCH-001-round1.md`

**Must-Pass**: MP-1~MP-7 **전부 기계적 PASS/N/A**(MP-4 N/A: 단일 언어 프로젝트).
다만 MP-5(D7)는 좁은 검증구문(retired/superseded/archived만 검사) 상 기계적 PASS이나,
그 인접 위험을 **D1(critical)**로 별도 승격했다 — `SPEC-COPILOT-VWX-001`(직접 선행 SPEC, spec.md에
명시)이 `status: draft` · `run_status: partial-blocked`(M8 여전히 BLOCKED)인데도 본 SPEC이
`related_specs:`(게이트 미작동 필드)만 쓰고 `depends_on:`(게이트 작동 필드)을 선언하지 않아
Phase 1 Depends_on Pre-flight Check가 이 불일치를 전혀 잡지 못한다.

**축별 점수** (조화평균 산정):

| 축 | 점수 | 근거 |
|---|---|---|
| Clarity | 0.75 | D1(1단계 완료 여부 모순) · D7(REQ-AUTOPATCH-022 멱등 매칭 기준 미정) · D8(AC-AUTOPATCH-001 Where/When 오용) |
| Completeness | 0.75 | D1(`depends_on:` 부재) · D3(design.md §5 슬롯 D "근거 등급 노출" 미보증) · D5(AC-AUTOPATCH-025 "계약 스냅샷" 메커니즘 미정의 — `test_vwx_report.py` grep 확인, 현재 그런 스냅샷 테스트 없음) |
| Testability | 0.75 | D4(AC-AUTOPATCH-014③ "구조적으로 보인다"가 ①②와 같은 검증법 재서술 — AC-AUTOPATCH-007①의 진짜 AST 구조 검사와 대비됨) · D5(AC-AUTOPATCH-025① "의미가 그대로다" 준-위즐워드) |
| Traceability | 1.0 | §C.0 25행 전량 재대조 PASS. 공유-AC REQ쌍 **4건**(디스패치 힌트의 "3건"보다 1건 더 발견) 전부 독립 검증 가능 확인 — 은폐 없음 |

**지적표 요약**(전문 참조): D1 critical(1) · D2·D3·D4·D5 major(4) · D6·D7·D8·D9·D10 minor(5).
P0/P1 상당 지적 5건(D1~D5)이 이번 회차의 핵심 — 전부 "design.md가 약속한 안전장치가 REQ/AC로
집행되지 않음" 또는 "1단계 상태 주장이 1단계 자신의 progress.md와 불일치" 패턴이다.

**권고 수정 순서**: D1(`depends_on:` 추가 + 1단계 상태 조정) → D3(근거 등급 컬럼 추가) →
D5(계약 스냅샷 구체화) → D4(AC-AUTOPATCH-014③ AST 구조 검사로 교체) → D2(FID 부정 분기 완화책 강화) →
D6~D10 일괄. 구조적 결함이 아니라 열거 가능한 구체적 gap이므로, 2회차에서 PASS 도달이 현실적이다
(scope-reduction 불필요 — LEAN Workflow STOP 에스컬레이션 조건 미해당, 1회차뿐이라 회귀 비교 대상 없음).

### 1회차 지적 반영 — v0.1.1 (2026-08-06, 작성자=오케스트레이터)

**10건 전량 반영. 미반영 0건.**

| # | 반영 내용 | 반영 위치 |
|---|---|---|
| D1 critical | frontmatter `depends_on: [SPEC-COPILOT-VWX-001]` 추가로 run-phase 진입에 Phase 1 의존성 게이트를 물린다. **동시에** "1단계 완료" 주장을 좁혀 §C `의존 범위 한정` 신설 — 무엇에 의존하고(리포트 스키마·멀티셀/액세서리 분류·`address_basis`·`diffs.performed` 불변식, 전부 M1~M7 구현·검증 완료) 무엇에 의존하지 않는지(`ASSUMPTION-70`·1단계 M8·`status: draft`) 표로 분리 | `spec.md` frontmatter · 도입 blockquote · §C |
| D2 major | **REQ-AUTOPATCH-026 신설** — `ASSUMPTION-71` 부정/INCONCLUSIVE 시 "FID 범위가 콘솔에서 비어 있음을 눈으로 확인했다"를 일반 승인과 구분되는 **별도 페이로드 필드**로 요구하고 없으면 실행 거부. 산문 경고에서 **건별 감사 가능한 구조 데이터**로 승격. AC-AUTOPATCH-027이 GO/부정 대조로 비공허하게 검증 | `spec.md` §B.2 · `acceptance.md` · `plan.md` §A.3 |
| D3 major | REQ-AUTOPATCH-003의 드라이런 표 필수 열에 **`address_basis` 추가**. AC-AUTOPATCH-004③이 역산 전제 문구 노출을 검증하고, 전 항목 직접값인 입력에서는 그 문구가 **안 나오는지**까지 대조 | `spec.md` REQ-AUTOPATCH-003 · `acceptance.md` AC-AUTOPATCH-004 · `design.md` §4 R5 |
| D4 major | AC-AUTOPATCH-014를 **두 기법 분리**로 재작성 — ①② 산출물 문자열 스캔, ③ `server/vwx/luagen.py` **소스 AST 스캔**(금지 리터럴 0건 + 자유 문자열이 명령 배열/Lua 본문에 도달하는 경로 0건). AC-AUTOPATCH-007① AST 패턴 계승 | `acceptance.md` AC-AUTOPATCH-014 |
| D5 major | AC-AUTOPATCH-025에 **골든 스냅샷 기법 정의** — 최상위 키 집합 + 키별 타입 시그니처를 JSON 픽스처로 고정(값은 고정하지 않음), 키 내부 의미는 1단계 기존 구조 assert에 위임. 파일명·픽스처 경로 명시, `plan.md` §E 테스트 표에 등재 | `acceptance.md` AC-AUTOPATCH-025 · `plan.md` §E |
| D6 minor | M0에 **진입 전제** 신설 — 테스트 쇼파일 확보는 권고가 아니라 차단 전제. 끝내 미확보 시 `ASSUMPTION-73`·`-74`는 INCONCLUSIVE로 판정하고 M8은 BLOCKED로 남는다(운영 쇼파일 대체 금지) | `plan.md` §B M0 |
| D7 minor | REQ-AUTOPATCH-022에 멱등 일치 튜플 **(유니버스, 주소, FixtureType, DMXMode 이름)** 명시. **주소 일치 + 타입/모드 불일치는 멱등이 아니라 충돌**로 보고 | `spec.md` REQ-AUTOPATCH-022 · `acceptance.md` AC-AUTOPATCH-020 |
| D8 minor | AC-AUTOPATCH-001 `**Where**` → `**When**`(이벤트 트리거이지 capability gate가 아니다) | `acceptance.md` AC-AUTOPATCH-001 |
| D9 minor | 존재하지 않는 선례 인용 삭제. 감사 전 신호 보류가 **의도된 규율**임을 직접 서술하고, 유사 선례가 미머지 형제 브랜치에 있어 인용 불가함을 명시 | `progress.md` §E.1 |
| D10 minor | `design.md` §4에 **R8 신설** — 미리보기와 실행이 툴 호출 수준에서 결속되지 않는 잔여 위험을 **수용된 위험으로 명시**. 승인은 오케스트레이터/사람 대화 계층에서 강제되며 이는 저장소의 다른 쓰기 툴과 동일 패턴. plan-hash/preview-token 결속은 도입하지 않는다(이 SPEC만 다른 규약을 쓰면 일관성이 깨진다) | `design.md` §4 |

**반영 후 기계 재검증**(작성자 실측): REQ 26 · AC 27 · 역추적 26/26 누락 0 · 표 밖 AC 5(의도) ·
§C.0a 합 27 · `plan.md` 마일스톤 AC 줄과 **1:1 전수 일치** · 약어 토큰 0 · 명료화 마커 0 ·
`IF/THEN` 0 · `[Option]` 0 · `depends_on` 1건.

**2회차 감사 필요.** 이 절의 반영 주장은 작성자 자신의 것이므로 독립 확인 대상이다.

---

## §E.2 Run-phase Evidence

(마일스톤별 증거를 기록한다. M0는 `GO:` / `NEGATIVE:` / `INCONCLUSIVE:` 접두 행으로
`ASSUMPTION-71`~`-75` 판정을 남긴다.)

---

## §E.3 Run-phase Audit-Ready Signal

(run-phase 완료 시 기록한다.)

---

## §E.4 Sync-phase Audit-Ready Signal

(sync-phase 완료 시 기록한다.)

---

## §F. Phase 4 Mode Selection — 확정 기록 (오케스트레이터 소유)

본 절은 **오케스트레이터가 첫 run-phase `Agent()` 스폰 전에 작성**하는 구속력 있는 기록이다.
`plan.md` §G의 대응 절은 **권고**이며 오케스트레이터가 확정하거나 기각한다.
어긋나면 **본 절이 이긴다.** 본문이 채워지기 전까지 이 절은 **비어 있음이 정상**이다.
