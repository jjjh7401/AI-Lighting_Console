# SPEC-LDRHYTHM-001 — 진행 기록

## §E.1 Plan-phase Audit-Ready Signal

- plan_status: audit-ready
- plan_complete_at: 2026-10-05
- tier: M (spec.md + plan.md + acceptance.md 3종, progress.md 는 전 Tier 공통)
- REQ 12개(R1 대본 우선 게이트 3 · R2 첫 곡 범위 1 · R3 두 층 모델 3 · R4 비충돌 1 · R5 효과 속도 2 · R6 합격 기준+M4 후보 2) · AC 11개(AC-001~009, 011 은 오프라인/시연 로그 검사, AC-010 만 실기 수동 판정)
- 미해소 `[NEEDS CLARIFICATION]` 마커 **0건** — 감독 결정 4건(2026-10-03, 리드 경유)이 입력 전체를 결정했다. §5 에 "열린 결정"이 아니라 "잔여 플래그" 3건을 기록(§10.3 인용 불일치 · G9 스피드 마스터 재생중 설정 방법 미확인 · G5 Rain BPM 오검출 가능성 — 전부 구현 전 재확인 항목, 재결정 사항 아님).
- 이 SPEC 은 **대본·시연·규칙화(M1~M3)만** plan 하며, M4+(앱 구현)는 §3.6 REQ-LDRHYTHM-012 에 "범위 후보"로만 기록했다 — M3 종료 후 재확인을 거쳐야 M4+ REQ 가 확정된다.
- plan-auditor 재감사 대기(최초 작성, iteration 1 아직 미실행).

## §E.2 Run-phase Evidence

- run_phase_start_sha: `e7eaf690` (카드 t507, 감독 착수 승인 2026-10-06 — Implementation Kickoff Approval PASS, M1 만)
- 다운비트 위상 0: 감독이 2026-10-06 t505 클릭 파일로 확인 → 마디 번호·시각은 `reports/clubdiver-music-map-20261005.md` 그대로

### M1 — Club Diver 연출 대본 (2026-10-06, 감독 검토 대기)

- 산출물: `m1-club-diver-script.md`(이 폴더, 유일한 공식 산출물) · 감독 검토용 사본 `reports/clubdiver-script-m1-20261006.html`
- 코드 diff 0줄 · 콘솔 명령 0건
- 대본 규모: 표 32행(박자 28 · 강조 4), 박자 층 이벤트 650개(펄스 293 · 체이스 한 칸 316 · 색/위치 한 단계 41), 강조 4곳(19·35·51·67마디)
- 기계 점검(사전 체일 뿐, 완료 아님 — REQ-011): `python .moai/reports/t507/check_script.py` → `problems 0`, `cite_10_4 5`, 오표기 0, 코드 블록 0. 첫 실행에서 강조 행 굵은 글씨 8건과 21마디 시각 오기 1건을 잡아 고쳤다
- 판정서: `.moai/reports/t507/verdict.md`
- 다음: 감독 M1 검토. 통과 전 M2 착수 금지(REQ-001·002)

## §F Phase 4 Mode Selection

- Decision: direct — M1 은 문서 한 개(대본)이고 코드 0이라 서브에이전트를 띄우지 않고 레인이 직접 썼다
- 입력: tier M · 파일 1(대본) + 사본 1 + 판정서 · 도메인 1(연출 문서) · 코드 0

## §E.3 Run-phase Audit-Ready Signal

_<pending run-phase>_

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_
