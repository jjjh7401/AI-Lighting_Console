# SPEC-COPILOT-MCP-001 — 진행 기록 (progress)

## §0 인수인계 — 여기서 시작한다 (2026-08-04 작성)

### 한 문단

앱을 MCP 서버로 여는 Stage 1 — **읽기 전용** stdio MCP 서버(`server/mcp/`, 신규)로 Claude 클라이언트가 grandMA3 콘솔을 판독한다. 기존 `build_toolset` 레지스트리의 읽기 전용 11종만 노출하고, 무변이 보증은 3중(allowlist 분할 테스트 · `execution_port` 거부 스텁 · 기록형 fake 도달성 테스트)이다. plan-phase 아티팩트 4종이 작성된 상태이며(v0.1.0, status: draft), 다음 단계는 plan-audit → Implementation Kickoff Approval → M1이다.

### 읽는 순서

1. `spec.md` §A(개요 + S1~S4 + 툴 분할표) → §B(REQ 23건) → §C(검증 천장 F-1~F-10 + ASSUMPTION-68~73) → §D(제외 10건)
2. `plan.md` §A.1(결정 우선순위) → §A.2(결정 등록부 D-1~D-6) → §B(M1~M6)
3. `acceptance.md` §C.0/§C.0a(역추적·배정) → AC 상세

### 함정 (다음 소유자가 알아야 할 것)

1. **`get_spatial_context`는 이 branch에 없다.** 임무 브리프가 "20 툴/후보 12종"이라 말해도 코드는 18/11이다(spec F-1·F-2). 브리프보다 branch 실측이 정본이다.
2. **분할 테스트는 깨지도록 설계된 감지기다.** 형제 SPEC(SPATIAL·GROUPGEN 등)이 머지되어 `TOOL_NAMES`가 늘어나는 순간 AC-MCP-003이 깨진다 — 버그가 아니라 "편입/제외를 결정하라"는 신호다(plan D-2).
3. **stdio 서버에서 stdout에 로그를 찍으면 프로토콜이 깨진다.** 로깅은 전부 stderr(plan §C). M1 에코 서버부터 테스트로 고정하라.
4. **`execution_port`는 `build_toolset`의 키워드 필수 인자다** — None 불가. 거부 스텁(RefusingExecutionPort)을 반드시 주입하라(REQ-MCP-007, spec F-3).
5. **아키텍처 가드 예외 목록은 테스트 2곳에 고정돼 있다** (`test_architecture.py` + `test_scene_boundary.py`의 "정확히 3건" 고정). D-1을 안 (b)로 판정하면 두 곳 다 의도적 diff다.
6. **전역 ASSUMPTION 카운터는 68부터.** 46~67은 미머지 형제 branch(INTROSPECT 46~52 · SPATIAL 53~60 · GROUPGEN 61~67)가 소비했다 — 이 tree를 grep하면 45까지만 보인다. grep 결과를 믿고 46부터 다시 쓰면 충돌한다.
7. **응답기 v1.6.0은 INTROSPECT-001 예약.** 본 SPEC은 응답기 무변경(D-6)이라 충돌이 없지만, 범위를 넓혀 응답기를 건드리는 순간 예약 충돌이 된다.

### 기계 확인 (인수인계 무결성)

```bash
# plan-phase 산출물 4종 (전부 존재해야 정상)
ls .moai/specs/SPEC-COPILOT-MCP-001/{spec,plan,acceptance,progress}.md

# 정본 토큰 계약: REQ 23 · AC 16 · ASSUMPTION 6
grep -c "^- \*\*REQ-MCP-" .moai/specs/SPEC-COPILOT-MCP-001/spec.md        # → 23
grep -c "^### AC-MCP-" .moai/specs/SPEC-COPILOT-MCP-001/acceptance.md     # → 16
grep -c "^- \*\*ASSUMPTION-" .moai/specs/SPEC-COPILOT-MCP-001/spec.md     # → 6

# branch 전제: spatial 툴 부재 · TOOL_NAMES 18종
grep -c "get_spatial_context" server/orchestrator/tools.py                 # → 0
python3 -c "import re;src=open('server/orchestrator/tools.py').read();print(len(re.findall(r'\"(\w+)\"',re.search(r'TOOL_NAMES = \((.*?)\)',src,re.S).group(1))))"  # → 18
```

### 다음 세션 킥오프 킷

- **다음 단계**: plan-audit(plan-auditor) → 감사 통과 시 Implementation Kickoff Approval(사람 게이트) → `/moai run SPEC-COPILOT-MCP-001` M1 착수.
- **M1의 판정 2건이 형상을 결정한다**: ASSUMPTION-68(SDK 공존) · ASSUMPTION-70(bootstrap 부수효과 → D-1 확정). 판정 전 M2 착수 금지(plan §B M1 게이트).
- **라이브 세션 회계**: 1회(M6)뿐. M1~M5는 콘솔 없이 fake로 완결된다.

## Plan-phase log

### v0.1.0 (최초 작성 — 2026-08-04)

- 아티팩트 4종(spec·plan·acceptance·progress) 동시 생성. status: draft.
- 임무 브리프 대비 실측 정정 2건: ① TOOL_NAMES 18종/후보 11종(브리프는 20/12 — 형제 branch 기준), ② ASSUMPTION 카운터 68 시작(브리프 무언급 — 에이전트 메모리 + 미머지 형제 SPEC 회계).
- 결정 등록부 6건(해소 4 · 조건부 2 — D-1은 M1 기계 판정, D-3은 M6 라이브 판정으로 닫힘). clarification 마커 0건.

## §E.1 Plan-phase Audit-Ready Signal

- 상태: 작성 완료 · **plan-audit 대기**. audit-ready 신호는 plan-auditor 통과 후 이 절에 기록된다.

## §E.2 Run-phase Evidence

_(run-phase 대기 — manager-develop 소유. ASSUMPTION-68~73 판정 접두 행(`GO:`/`NO-GO:`/`CONDITION_NOT_MET:`/`INCONCLUSIVE:`, 행두, 한 판정당 1행)은 이 절이 정본이다.)_

## §E.3 Run-phase Audit-Ready Signal

_(run-phase 대기 — manager-develop 소유.)_

## §E.4 Sync-phase Audit-Ready Signal

_(sync-phase 대기 — manager-docs 소유.)_
