# SPEC-LDRHYTHM-001 — 진행 기록

## §E.1 Plan-phase Audit-Ready Signal

- plan_status: audit-ready
- plan_complete_at: 2026-10-05
- tier: M (spec.md + plan.md + acceptance.md 3종, progress.md 는 전 Tier 공통)
- REQ 12개(R1 대본 우선 게이트 3 · R2 첫 곡 범위 1 · R3 두 층 모델 3 · R4 비충돌 1 · R5 효과 속도 2 · R6 합격 기준+M4 후보 2) · AC 12개(AC-001~009, 011, 012 는 오프라인/시연 로그 검사, AC-010 만 실기 수동 판정 — AC-012 는 2026-10-06 M2 착수 전 게이트로 신설, REQ-LDRHYTHM-001 에 트레이스)
- 미해소 `[NEEDS CLARIFICATION]` 마커 **0건** — 감독 결정 4건(2026-10-03, 리드 경유) + 정정 결정 1건(2026-10-06, 첫 곡을 Club Diver 에서 LOVE ATTACK 으로 교체)이 입력 전체를 결정했다. §5 에 "열린 결정"이 아니라 "잔여 플래그" 5건을 기록(§10.3 인용 불일치 · G9 스피드 마스터 재생중 설정 방법 미확인 · G5 Rain BPM 오검출 가능성 · LOVE ATTACK 원곡 오디오 위치(저장소 밖, 측정 기록됨) · "기존 앱 연출"(AC-010 비교 대상) = t510 기준선, 가짜 콘솔에서만 생성·실기 미재생 — 전부 구현 전 재확인/선행 항목, 재결정 사항 아님).
- 이 SPEC 은 **대본·시연·규칙화(M1~M3)만** plan 하며, M4+(앱 구현)는 §3.6 REQ-LDRHYTHM-012 에 "범위 후보"로만 기록했다 — M3 종료 후 재확인을 거쳐야 M4+ REQ 가 확정된다.
- plan-auditor 이력: iteration 1 FAIL 0.75 → 2 PASS 0.92 → 3 FAIL 0.80(결함은 `a64fd66c` 로 해소, 리드 판독으로 확인) · t508 정정 감사 PASS 0.96(2026-10-06, `.moai/reports/plan-audit/SPEC-LDRHYTHM-001-review-4.md`).

## §E.2 Run-phase Evidence

- run_phase_start_sha: `cea25c04` (카드 t511, 감독 착수 승인 2026-10-06 — M1 만)
- 감독 귀 확인 2026-10-06: t509 다운비트 위상 1 · 63~66마디 비트 드롭 · 후렴 진입 18·46마디 첫 박 → 마디·시각은 `reports/loveattack-music-map-20261006.md` 그대로
- 참고(비채택): Club Diver 대본 초안 PR #553(t507, 미머지) — 형식만 참고, 내용은 옮기지 않음

### M1 — LOVE ATTACK 연출 대본 (2026-10-06, 감독 검토 대기)

- 산출물: `m1-love-attack-script.md`(이 폴더, 유일한 공식 산출물) · 감독 검토용 사본 `reports/loveattack-script-m1-20261006.html`
- 코드 diff 0줄 · 콘솔 명령 0건
- 대본 규모: 표 55행(박자 51 · 강조 4), 박자 층 이벤트 337개(펄스 173 · 체이스 한 칸 141 · 색/위치 한 단계 23), 강조 4곳(18·46·63마디, 67마디 4박)
- 기계 점검(사전 체일 뿐, 완료 아님 — REQ-011): `python .moai/reports/t511/count_script.py` → `problems 0`, `cite_10_4 5`, 오표기 0, 코드 블록 0, 이유 칸 인용 누락 0, 약점 ①②③ 통과. 첫 실행에서 이유 칸 인용 누락 21행과 강조 직전 비움 판정 창 문제 1건을 잡아 고쳤다
- 판정서: `.moai/reports/t511/verdict.md`
- 다음: 감독 M1 검토. 통과 전 M2 착수 금지(REQ-001·002). M2 첫 송신 전 AC-LDRHYTHM-012 측정 도구 필요(plan.md §D)

## §F Phase 4 Mode Selection

- Decision: direct — M1 은 문서 한 개(대본)이고 코드 0이라 서브에이전트를 띄우지 않고 레인이 직접 썼다
- 입력: tier M · 파일 1(대본) + 사본 1 + 판정서 · 도메인 1(연출 문서) · 코드 0

## §E.3 Run-phase Audit-Ready Signal

_<pending run-phase>_

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_
