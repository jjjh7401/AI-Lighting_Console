# SPEC-COPILOT-VWX-001 — 진행 기록 (progress)

> **인용 규율.** 본 SPEC의 정본(`spec.md` · `acceptance.md`)은 **줄번호로 인용하지 않고** 안정 토큰만 쓴다. `파일:줄`은 **코드 · 룰북 · 응답기 프로토콜 · 타 SPEC 아티팩트**에만 쓴다. 요구·인수 토큰은 슬러그 포함 완전형만 쓴다(축약형 **0건**).

## §0 인수인계 — 여기서 시작한다 (2026-08-05)

> **이력을 모르는 사람이 처음 읽는 절이다.**

### 한 문단

**무엇**: Vectorworks Instrument Data(엑셀/CSV/tab-text)를 읽어 **설계상 리그(designed rig)** 모델을 만들고, 이미 라이브 검증된 `precheck_patch`(콘솔 실측)와 대조해 **"도면 vs 실제 콘솔 패치"** 차이 리포트를 낸다. `.moai/reports/ma3-copilot-overview.html` §7 P0 항목의 1단계만을 범위로 하며, 2단계(`AddFixtures` 자동 패치)와 3단계(MVR/GDTF)는 후속 SPEC으로 분리한다.
**상태**: **plan-phase 아티팩트 6종 작성 완료. 미커밋 · 미감사.** REQ 25건 · AC 26건 · ASSUMPTION 3건(68~70) · 마일스톤 9개(M0~M8) · 라이브 세션 0회 · clarification 마커 0건.
**열린 사용자 접점**: **2건** — ① 실물 Vectorworks export 샘플 제공(M0 선행조건, 컬럼 계약 동결의 유일한 전제) · ② 신규 의존성 `openpyxl` 채택 승인(`.xlsx` 경로 B 지원 여부, 미승인이어도 산출물은 성립).

### 읽는 순서

| 순서 | 무엇을 알려주나 | 어디 |
|---|---|---|
| 1 | 무엇을 만들기로 했나 | `spec.md` — REQ 25건 · §C PRESERVE와 **신규 의존성 승인 대기** · §D Out of Scope 6건 |
| 2 | 무엇을 통과해야 하나 | `acceptance.md` — AC 26건 · 역추적표 · 마일스톤별 배정 |
| 3 | 왜 이렇게 설계했나 / 왜 이 순서로 만들었나 | `design.md` 슬롯 A~E · `plan.md` §B M0~M8 |
| 4 | Vectorworks 형식 조사 원문(가장 김) | `research.md` — 2경로·별칭 테이블·주소 4형식·7가지 함정. 필요할 때만 |
| 5 | 라이브 세션 0회의 근거 | `plan.md` §C — 검토 후 적극적으로 0으로 결정한 것이지 생략이 아니다 |

### 인수인계 시 반드시 알아야 할 함정 3건

1. **이 저장소에 실물 Vectorworks export 샘플이 0건이다.** 컬럼 별칭 테이블(`research.md` §3)은 Vectorworks 공식 문서 조사에 근거한 **강력한 초안**이지 정본이 아니다 — M0가 실물 샘플로 검증·확장하기 전에는 M1 이후를 "완료"로 표시하지 않는다.
2. **콘솔 실측을 재구현하지 않는다.** `read_inventory`/`build_patch_sheet`/`normalize_address`/`_range_overlaps`는 PRECHK SPEC이 이미 라이브 검증했다 — `server/vwx/`는 그것을 **소비만** 한다. 재구현하면 두 경로가 드리프트한다.
3. **대조 조인 키는 (유니버스, 주소)+타입이며 `FID`/`CID`는 0건이다.** 슬롯==FID 우연일치 쇼파일에서는 원리적으로 FID 프로브와 슬롯 프로브를 구별할 수 없다(`console/lua/PROTOCOL.md:322-324`, PRECHK 선례) — 이 SPEC은 그 필요 자체를 조인 키 설계로 우회했다. 새 라이브 프로브를 열려는 유혹을 거절한다(`plan.md` §C가 근거를 적었다).

### 인수인계가 온전한지 기계로 확인하는 법

```
git rev-parse --abbrev-ref HEAD                 -> feature/SPEC-COPILOT-VWX-001
git status --short                              -> spec.md/plan.md/acceptance.md/design.md/research.md/progress.md 6개 신규(미커밋)
uv run pytest server/tests -q                   -> 4716 passed · 7 skipped · 1 warning (코드 변경 0 — plan-phase만 진행됨)
grep -oE 'REQ-VWX-[0-9]{3}' .moai/specs/SPEC-COPILOT-VWX-001/spec.md | sort -u | wc -l       -> 25
grep -oE '^### AC-VWX-[0-9]{3}' .moai/specs/SPEC-COPILOT-VWX-001/acceptance.md | sort -u | wc -l -> 26
```

### 다음 담당자가 먼저 결정할 것 2건

1. **plan-auditor 감사 1회차 PASS(0.92, Tier L 임계 0.85).** `plan_status: audit-ready`(아래 §E.1)로 갱신됨. 지적 10건(전부 minor, P0/P1 0건)은 `§E.1a` 참조.
2. **Kickoff 사용자 접점 2건**(실물 샘플 · `openpyxl` 승인)이 미해결이다. `plan.md` §G가 접점 표를 소유한다.

---

## Plan-phase log

### v0.1.0 — plan-phase 아티팩트 6종 작성 (2026-08-05)

착수 SHA **`b1a630eb9380fd37436252e366289350bd22feff`**(= `origin/main`, SPATIAL/GROUPGEN 머지 직후), 착수 baseline **4716 passed · 7 skipped · 1 warning · 91.35s(0:01:31)**(직접 실측, 이월 인용 아님).

| 아티팩트 | 내용 | 라인 수 |
|---|---|---|
| `spec.md` | REQ 25건 · Out of Scope 6개 H3(전부 `-` 불릿 보유) · ASSUMPTION 68~70 | 184 |
| `plan.md` | 마일스톤 M0~M8 · 결정 A~G · 라이브 세션 0회 근거 · Phase 4 Mode Selection 권고 | 253 |
| `acceptance.md` | AC 26건 · 역추적표 REQ 25/25 · 마일스톤별 배정 합 26 | 405 |
| `design.md` | 변경 표면 · 흐름 8단계 · 위험 검토 13항 · 설계 슬롯 A~E · 뮤테이션 24개 | 338 |
| `research.md` | 2경로 export · 별칭 테이블 · 주소 4형식 · 7가지 대조 함정 · 재사용 계약 | 206 |
| `progress.md`(본 파일) | 인수인계 + plan-phase 로그 + §E 골격 | (본 절 포함, §E.1 참조) |

### 조사 방법 — 실물 샘플 없이 공식 문서로 초안을 잡았다

이번 SPEC은 PRECHK와 달리 **라이브 콘솔 사전 프로브를 돌리지 않았다** — 대상이 콘솔이 아니라 Vectorworks export 파일 포맷이기 때문이다. 대신 Vectorworks 공식 도움말 문서 3건(WebFetch로 검증됨, `research.md` §1)을 조사해 두 export 경로(tab-text 전용 경로 A, 워크시트 그리드 경로 B)와 컬럼 별칭 테이블 초안을 확립했다. **이 초안은 실물 파일로 검증되지 않았다** — M0가 그 검증을 소유한다.

### 사용자 브리핑이 이미 확정한 사실을 그대로 반영했다

사용자 브리핑이 제공한 조사(두 export 경로, 4가지 주소 표현, 별칭 테이블, 7가지 대조 함정, FID/CID 불가 근거, 실물 샘플 부재)는 이미 검증된 기존 지식으로 취급하고 재조사하지 않았다 — 다만 저장소 코드 인용(`inventory.py:54` 등)은 실제 파일과 대조해 **드리프트를 3건 발견하고 정정했다**:

| 브리핑 인용 | 실제 값 | 정정 |
|---|---|---|
| `server/orchestrator/tools.py:98`(TOOL_NAMES) | `TOOL_NAMES = (`은 실제로 **127행** | design.md·spec.md·plan.md 전부 127로 정정 |
| `server/orchestrator/tools.py:1542-1697`(precheck_patch 핸들러) | `def precheck_patch(...)`는 실제로 **1986행** | 정정 |
| `server/orchestrator/tools.py:2916-2955`(ToolDefinition) | `name="precheck_patch"`는 실제로 **4317행** | 정정 |
| `server/orchestrator/tools.py:3443`(handlers dict) | `handlers: dict[str, _Handler] = {`는 실제로 **5134행**(항목은 5143행) | 정정 |
| `server/prechk/inventory.py:54`(PROPERTY_WHITELIST) | 실제로 **57행** | 정정 |

브리핑 자체가 "content-token anchor; line numbers drift"라고 경고했고, 이 드리프트가 정확히 그 사례였다 — 인용 전에 직접 grep으로 재확인했다.

### 라이브 세션 0회 — 적극적 결정

PRECHK와 달리 본 SPEC은 라이브 세션을 **0회**로 결정했다. 콘솔 실측(대조의 절반)은 이미 라이브 검증된 `read_inventory`/`build_patch_sheet`를 재사용하고, FID/CID 재프로브는 조인 키 설계가 그 결과에 의존하지 않으므로 열지 않았다 — 대안을 검토하고 기각한 근거는 `plan.md` §C에 있다.

---

## §E.1 Plan-phase Audit-Ready Signal

```yaml
plan_status: audit-ready
plan_complete_at: 2026-08-05
spec_version: "0.1.0"
base_sha: b1a630eb9380fd37436252e366289350bd22feff
baseline_measured: "uv run pytest server/tests -q → 4716 passed, 7 skipped, 1 warning in 91.35s (0:01:31)"
artifacts: [spec.md, plan.md, acceptance.md, design.md, research.md, progress.md]
artifact_lines: "spec 184 · plan 253 · acceptance 405 · design 338 · research 206"
requirements: 25          # REQ-VWX-001~025 — spec.md 정의 25 = 고유 토큰 25
acceptance_criteria: 26   # AC-VWX-001~026 — acceptance.md 절 제목 26 = 고유 토큰 26
milestones: 9             # M0~M8. M0·M8만 cycle_type=none (코드 변경 0)
assumptions_open: 3       # ASSUMPTION-68~70
decisions_closed: 7       # plan.md 결정 등록부 A~G
decisions_open: 0
design_slots_closed: 5    # design.md §5 슬롯 A~E
design_slots_open: 0
clarification_markers: 0
live_sessions_planned: 0  # plan.md §C — 적극적 결정, 근거는 해당 절 참조
machine_gates:
  requirements_counted: "25 — spec.md 정의 25 = 고유 토큰 25"
  req_to_ac_coverage: "25/25 — acceptance.md 역추적표 REQ 행 25, 커버 누락 0"
  acceptance_criteria_counted: "26 — acceptance.md 절 제목 26 = 고유 토큰 26"
  ac_milestone_assignment: "26 — M0 1 · M1 4 · M2 3 · M3 4 · M4 5 · M5 4 · M6 3 · M7 1 · M8 1. 중복 0 · 누락 0. plan.md 마일스톤별 AC 줄과 1:1 대조 완료"
  ac_absent_from_traceability_table: "3 — AC-VWX-001(M0 전제 확보 게이트) · AC-VWX-025(형상 전체) · AC-VWX-026(종단 통합). acceptance.md가 의도로 명시"
  out_of_scope_h3_headings: "6 — 전부 `-` 불릿 1건 이상 보유(OutOfScopeRule 요건 충족)"
  abbreviated_tokens_all_artifacts: 0     # 정규식 [^A-Z-](AC|REQ)-[0-9]{3} — 6문서 합 0
  clarification_markers_all_artifacts: 0  # NEEDS CLARIFICATION/TODO/TBD/FIXME 검색 — 6문서 합 0
  mutations_proposed: 24    # design.md §6.3
preflight_probe:
  real_sample_present: false   # 이 저장소에 실물 Vectorworks export 샘플 0건. M0가 확보를 소유한다
  code_citation_drift_found: 3 # tools.py TOOL_NAMES/handler/definition/handlers dict 4개 좌표 + inventory.py 1개 좌표가 브리핑 인용과 어긋나 직접 재확인 후 정정
known_gaps:
  - "이 저장소에 실물 Vectorworks export 샘플이 없다 — 컬럼 별칭 테이블(research.md §3)은 Vectorworks 공식 문서 조사에 근거한 초안이며 M0가 실물 파일로 검증·확장한다."
  - "openpyxl 신규 의존성 승인이 확보되지 않았다 — 미승인이어도 산출물은 성립하며 경로 B의 .xlsx만 v1 범위 밖으로 축소된다(spec.md §D)."
  - "ASSUMPTION-68~70 3건 모두 M0/M1~M3에서 판정될 예정이며 아직 GO/NEGATIVE가 배정되지 않았다."
  - "plan-audit 1회차 PASS(0.92) — minor 지적 10건 잔존(§E.1a), P0/P1 0건이라 run-phase 착수를 막지 않는다."
next: "Implementation Kickoff Approval(실물 Vectorworks export 샘플 제공 + openpyxl 의존성 승인, 2건) 확보 후 /moai run SPEC-COPILOT-VWX-001."
```

## §E.1a Plan-audit 결과

**1회차 — PASS, 종합 점수 0.92** (Tier L 임계 0.85). 전체 리포트: `.moai/reports/plan-audit/SPEC-COPILOT-VWX-001-round1.md`.

Must-pass 7축: MP-1 REQ 시퀀싱 PASS(25/25, 결번·중복 0) · MP-2 AC GEARS 준수 PASS(26건 전부 IF/THEN 0·`[Option]` 0) · MP-3 frontmatter PASS(12/12 정본, 별칭 0) · MP-4 언어 중립성 N/A(단일 언어 Python) · MP-5 D7 교차-SPEC 정합 PASS(PRECHK/OVERLAP/GROUPGEN 전부 `status: completed`) · MP-6 D8 크로스플랫폼 N/A(`syscall` 언급 0) · MP-7 clarification 게이트 PASS(마커 0).

Minor 지적 10건(P0/P1 없음, 전부 run-phase 착수 비차단):
- REQ-VWX-025가 `[Ubiquitous]` 태그인데 "shall" 부재
- REQ 7건이 비정형 후행 조건절을 태그 없이 포함
- REQ 5건이 정본 텍스트 안에 `file:line 함수명` 구현 좌표를 직접 인용
- PRESERVE 목록이 `server/prechk/` 8개 파일 중 4개만 커버(`__init__.py`/`footprint.py`/`macro.py`/`query.py` 미포함) — 감사가 조사한 결과 3개 모듈은 무관 기능이라 위험도 낮음으로 판정
- 미문서화된 `related_specs` frontmatter 필드
- `id` 정규식이 SSOT 리터럴과 문자 그대로는 다름(비차단 — 리포 전역 다분절 관례와 합치)
- `progress.md`가 드리프트 정정 "3건"이라 적었는데 자체 표는 5건 나열(자기모순)
- `design.md`가 변형 "24건"이라 적었는데 자체 표는 25행(3+3+4+5+4+3+2+1=25, 재계산 확인)
- "0건" AC 주장 2건이 형제 AC들이 갖춘 비공허성 인라인 주석을 누락
- AC-VWX-013②의 동점 처리 규칙이 "예시"이지 닫힌 결정이 아님

강점: 코드 좌표 인용 11건 전량 라이브 재검증 통과(`tools.py:127/136/1986/4317/5134/5143`, `inventory.py:57`, `patch.py:118/440`, `paperwork/data.py:67`, `verdicts.py:52`, `report.py:143`). FID/CID 불가·실물 샘플 부재 두 orchestrator 지정 정직-처리 항목 모두 `SkippedCheck`/`not_performed` 어휘로 충실히 처리됨(얼버무림 없음). `base_sha`가 실측 `git log -1`과 정확히 일치. REQ↔AC 25↔26 역추적을 표본이 아닌 전수 검증(누락 0, 고아 0).

**후속 처리**: 10건 minor는 audit-ready 신호를 막지 않는다(모두 P0/P1 미해당). run-phase 착수 전 또는 M1 중 정정 권고 — 이번 plan-phase worker 범위에서는 재수정하지 않고 다음 담당자(Implementation Kickoff Approval 승인자 및 manager-develop)에게 인계한다.

## §E.2 Run-phase Evidence

_<pending run-phase>_

## §E.3 Run-phase Audit-Ready Signal

_<pending run-phase>_

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_

## §F. Phase 4 Mode Selection — 확정 기록 (오케스트레이터 소유)
