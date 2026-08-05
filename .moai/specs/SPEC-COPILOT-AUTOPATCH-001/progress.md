# SPEC-COPILOT-AUTOPATCH-001 — 진행 기록 (progress)

> **인용 규율**: 본 SPEC의 `spec.md`·`acceptance.md`는 행 번호로 인용하지 않는다 — 안정 토큰만 쓴다.
> `file:line`은 코드·룰북·`console/lua/PROTOCOL.md`·**다른** SPEC의 아티팩트에만.
> **증거 등급**: `[코드]` · `[문서]` · `[실측]` · `[미확정]`.

## §0 인수인계 — 여기서 시작한다 (2026-08-05)

**상태**: **plan-phase 아티팩트 6종 작성 완료 · plan-audit 대기.**
REQ 25건(REQ-AUTOPATCH-001~025) · AC 26건 · ASSUMPTION 5건(71~75) · 마일스톤 9개(M0~M8) ·
라이브 세션 **2회 계획** · clarification 마커 0건 · 설계 슬롯 5건 전부 종결.

**이 SPEC이 1단계와 근본적으로 다른 점**: **콘솔에 쓴다.** 1단계는 읽고 비교만 했다.
패치는 픽스처를 **생성**하고, 이 앱에는 실행 취소·백업 복원 경로가 **없다**.
그래서 요구사항의 절반 이상이 기능이 아니라 **되돌릴 수 없는 쓰기를 사람이 통제하게 만드는 장치**다.

### 읽는 순서

| # | 무엇을 | 어디서 |
|---|---|---|
| 1 | 무엇을 만들기로 했나 | `spec.md` — REQ 25건 · §C ASSUMPTION 71~75 · §C PRESERVE · §D Out of Scope 6건 |
| 2 | 왜 M0가 먼저인가 | `plan.md` §A.2 — 쓰기에 필요한 값 둘(FID · DMXMode 핸들)이 **읽히는지조차 미확정**이다 |
| 3 | 부정이면 어떻게 되나 | `plan.md` §A.3 — 가정 5건의 부정 처리표. 부정은 실패가 아니라 **기능 축소**다 |
| 4 | 무엇을 통과해야 하나 | `acceptance.md` — AC 26건 · §C.0 역추적표(REQ 25/25) · §C.0a 마일스톤 배정 · §F DoD |
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
| `spec.md` | REQ 25건 · ASSUMPTION 71~75 · Out of Scope 6개 H3 · PRESERVE 5경로 | 286 |
| `plan.md` | 마일스톤 M0~M8 · 결정 A~G(미결 0) · 라이브 2회 · 테스트 골격 · §G Mode 권고 | 192 |
| `acceptance.md` | AC 26건 · §C.0 역추적표(REQ 25/25) · §C.0a 배정 합 26 · §F DoD | 422 |
| `design.md` | 변경 표면 · 흐름 · 위험 7건 · 설계 슬롯 5건(전부 종결) · 비공허성 8건 · 안티패턴 10건 | 216 |
| `research.md` | 증거 등급별 조사 8절 · 미확정 5건을 ASSUMPTION으로 승격 | 202 |
| `progress.md` | 본 문서 | 158 |

**합 1,476줄** — 커밋 시점 실측(`wc -l`).

---

## §E.1 Plan-phase Audit-Ready Signal

**상태: 작성 완료 · plan-audit 대기.** audit-ready 신호는 plan-auditor 통과 후 이 절에 기록한다.
`SPEC-COPILOT-MCP-001`의 선례를 따라 감사 전에 신호를 쓰지 않는다.

기록 예정 값(감사 통과 시 확정):

```yaml
plan_status: (audit 대기)
plan_complete_at: (audit 통과일)
spec_version: "0.1.0"
base_sha: ca00bc5c853bfe5d9391290f1b9db263610b4bfa
baseline_measured: "uv run pytest server/tests -q → 4898 passed, 7 skipped, 1 warning in 92.28s"
artifacts: [spec.md, plan.md, acceptance.md, design.md, research.md, progress.md]
requirements: 25          # REQ-AUTOPATCH-001~025
acceptance_criteria: 26   # AC-AUTOPATCH-001~026
milestones: 9             # M0~M8. M0·M8만 cycle_type=none (라이브 측정)
assumptions_open: 5       # ASSUMPTION-71~75 — 전부 M0 라이브 판정 대상
live_sessions_planned: 2  # M0 전제 측정 · M8 종단 검증
decisions_closed: 7       # plan.md §A.4 결정 A~G
decisions_open: 0
design_slots_closed: 5    # design.md §5 슬롯 A~E
design_slots_open: 0
clarification_markers: 0
machine_gates:
  req_to_ac_coverage: "25/25 — acceptance.md 역추적표 REQ 행 25, 커버 누락 0"
  ac_milestone_assignment: "26 — M0 1 · M1 3 · M2 4 · M3 4 · M4 4 · M5 3 · M6 3 · M7 3 · M8 1. 중복 0 · 누락 0"
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

(plan-auditor 실행 후 라운드별 판정 · 축별 점수 · 지적표 · 수정 후 재측정을 기록한다.)

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
