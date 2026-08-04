# SPEC 감사 보고서: SPEC-COPILOT-MCP-001

- Iteration: 1/3 · **Verdict: FAIL** · **Overall Score: 0.78** (Tier M 통과선 0.80)
- 대상: `.moai/specs/SPEC-COPILOT-MCP-001/` @ 608d144 (branch `feature/SPEC-COPILOT-MCP-001`, base 3176900)

## 요약

툴 분할표(§A)는 기계 확인 결과 **정확**하다(18종 전수 분할, 유령 이름 0, 누락 0). 그러나 이 SPEC의 존재 이유인 **"무변이 3중 방벽"이 실제로는 3중이 아니다** — 방벽 ①(allowlist)에 인자 하나로 콘솔을 쓰는 툴이 있고, 방벽 ③(도달성 테스트)은 명세대로면 공허 통과 가능하며, 부팅 경로의 `SaveShow`는 세 방벽 어디에도 걸리지 않는다.

## Must-Pass

MP-1 REQ 번호 정합 PASS · MP-2 GEARS PASS · MP-3 frontmatter PASS · MP-4 N/A · MP-5 교차 SPEC PASS · MP-6 N/A · MP-7 clarification 게이트 PASS(0건). **must-pass 실패 없음** — FAIL은 집계 점수 미달 + P0 3건의 성격에서 나온다.

## 차원 점수 (조화평균 = 0.78)

| 차원 | 점수 | 근거 |
|---|---|---|
| Clarity | 0.80 | 모호성이 아니라 사실 오류 감점 (spec.md:58, D-1) |
| Completeness | 0.75 | 부팅 경로·import 충돌·역방향 포트·부수효과 경계를 규율하는 REQ 부재 |
| Testability | 0.70 | 최대 하중 AC-MCP-004가 공허 통과 가능, 대조군 요구 없음 |
| Traceability | 0.92 | REQ 23 전수 커버·고아 0·마일스톤 합 16 확인. 감점은 AC-016 고아 1건 |

## 기계 확인된 SPEC 주장

`TOOL_NAMES` 18종 · 11+7 전수 분할 · `get_spatial_context` 부재 · `execution_port` 키워드 필수 인자 · `_ALLOWED_PREFIXES` 3종+예외 정확히 3건 · `launcher.py` FastAPI-free · 룰북 5종 · `mcp` 미설치 — **F-1~F-10 전건 참**. 무너지는 것은 실측하지 않고 단정한 두 곳: §A 분할표의 `precheck_patch` 행, D-1 (a)의 "가드 diff 0".

## 결함 11건

### D1 (P0) — `precheck_patch`는 읽기 전용이 아니다
`tools.py:1543` `create_macro` 인자 → `:1590` 매크로 저작 → `:1650` 내부에서 `run_commands` 호출. 툴 스키마 설명 자체가 "without touching the showfile"(=false일 때만)이라 명시. AC-MCP-004는 기본값으로 호출하므로 **ASSUMPTION-69가 거짓 GO를 받는다**.
→ 수정: MCP 노출 스키마에서 `create_macro` 제거 + 강제 False (REQ+AC 신설), 또는 정직한 축소로 allowlist 제외. §A:58 행 정정.

### D2 (P0) — 도달성 판정기가 공허 통과 가능
REQ-MCP-007이 `execution_port`에 RefusingExecutionPort를 주입하는데, AC-MCP-004 테스트가 같은 배선을 쓰면 도달성과 무관하게 전부 0건. `preshow_check`는 `ConsolePort`가 아니라 `preshow_liveness_port`를 타므로 명시된 계측기로는 보이지 않는다. SCENE-001 REQ-SCENE-021(c) 대조군 선행 원칙 위반.
→ 수정: (a) 허용형 기록 포트 사용, (b) 양성 대조 의무(기지의 변이 툴이 execute ≥1 기록 못하면 테스트 실패), (c) liveness port 별도 계측.

### D3 (P0) — 부팅 시 콘솔에 쓴다 (`SaveShow`)
`build_console_stack(attempt_session_backup=True)` → `gate.start_session()` → `make_showfile_backup_action()` = `SaveShow`. 게이트 링크를 타므로 `build_toolset` 경유가 아니며 세 방벽 밖. ASSUMPTION-70의 판정 기준이 "수명주기 충돌"이라 M1 판정관이 볼 이유가 없다.
→ 수정: `attempt_session_backup=False` REQ + 기동~tools/list 구간 콘솔 send 0건 AC. REQ-MCP-013 범위를 프로세스 전 생애로 확장.

### D4 (major) — D-1 (a) "가드 diff 0"이 성립 불가
`bootstrap.py:145`가 `ReceivePortInUseError`를 `server.web.launcher.PortInUseError`로 번역 → REQ-MCP-008 구현하려면 `server/mcp/`가 `server.web`을 import해야 하는데 plan §C가 금지. 대안(브리지 예외 직접 포착)은 아키텍처 가드 `_FORBIDDEN_MODULE_PREFIXES` 위반.
→ 수정: plan에서 선해소 — 예외 타입을 명명된 허용 예외로 재진술하거나 `server/safety`에서 재수출. 선택을 AC로 고정.

### D5 (major) — 판정 접두어 4종 중 3종이 정본과 다름
정본(SCENE-001 인라인 표): `GO:` / `DESCOPE:` / `SKIP:` / `REOPEN:`. 본 SPEC: `GO:` / `NO-GO:` / `CONDITION_NOT_MET:` / `INCONCLUSIVE:`. 코퍼스 실측 `NO-GO:` = **0건** → 기록해도 전역 grep에 안 잡힌다. 오염 표면 4곳(spec:111, acceptance:91·135, progress:61).
→ 수정: 5행 매핑 표 인라인 + 접두어 3종 정정.

### D6 (major) — `.mcp.json` 역방향 위험 미분석
프로젝트 스코프 `.mcp.json`은 세션마다 자동 기동 → 열린 Claude Code 세션이 포트 9000을 쥐어 **웹 앱이 기동 실패**하는 역방향이 REQ·AC·Out of Scope 어디에도 없다. D3와 결합 시 세션마다 `SaveShow`.
→ 수정: 기본 비활성 배포(`.mcp.json.example`) 또는 역방향 실패 UX REQ+AC.

### D7 (minor-major) — "읽기 전용"의 부수효과 경계 미정의
`build_*` 3종은 디스크에 HTML을 무조건 덮어쓴다(`paperwork/output.py:46-58`). 모든 state 판독이 감사 로그에 append(`gate.py:644-665`). AC-MCP-004는 둘 다 통과시킨다.
→ 수정: "읽기 전용"을 **"콘솔 무변이"**로 정의하고 허용 로컬 부수효과를 열거, 또는 `build_*` 제외.

### D8 (minor) — REQ-MCP-003 패턴 라벨 오류: `(Where)` → `(When)` (클라이언트 요청은 이벤트)

### D9 (minor) — AC-MCP-015 ④ "콘솔 변이 0건"의 관측 채널 미규정 → Command History 관측 + `audit_logs` kind 히스토그램 명시

### D10 (minor) — AC-MCP-016 고아(문서 자인) → 대응 REQ 신설 또는 "횡단 회귀 게이트" 표기

### D11 (minor) — ASSUMPTION-70이 한쪽은 과대(`HealthMonitor`는 스레드 아님 — grep 0건), 실제 위험 2건(D3·D4)은 미지명 → 판정 기준 재진술

## 검증하지 못한 것 (Gaps)

1. `mcp` SDK 실제 설치 가능성(ASSUMPTION-68) — 미설치, M1의 몫
2. `build_console_stack` 부수효과의 stdio **실행** 검증 — D3는 정적 판독 근거
3. `.mcp.json` 자동 기동 동작 — 이 저장소에서 미실측(파일 부재)
4. 전체 테스트 스위트 미실행 — AC-MCP-016 기준선 미측정
5. 나머지 읽기 후보 무변이는 dispatch 판독까지만(실행 검증 없음), `build_*`는 하위 호출 미전개
6. `preshow_check`의 MCP측 liveness port 배선은 SPEC에 미규정

## 잔여 위험

- **"통과했는데 안전하지 않은" 상태**가 최대 위험 — D1+D2 동시 생존 시 M2가 초록으로 끝나며 거짓 GO 기록
- D3는 방벽 밖이라 M6(실물 콘솔)에서야 드러남 → 라이브 회계 1회 계획이 깨짐
- D4는 run-phase 결정 월권 유발(4번째 가드 예외 신설 또는 PRESERVE 파일 수정)
- 형제 SPEC 머지 시 분할 테스트가 깨지는 것은 **설계**이지 결함 아님 — 재감사 시 회귀로 오독 금지

## 권고

차단 수정 6건(D1~D6) 후 iteration 2 재감사. 범위는 델타 한정 — 전면 재감사 불요. 토큰 계약(REQ/AC 개수)이 바뀌면 4개 표면(spec HISTORY · plan 머리말 · acceptance §A · progress §0)을 동시 갱신할 것(이 저장소 반복 결함 지점).
