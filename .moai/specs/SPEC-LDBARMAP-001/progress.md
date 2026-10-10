# SPEC-LDBARMAP-001 — 진행 기록

카드: t527(plan-phase) / t530(M1 run-phase). plan-phase 세션은 `server/` 코드 변경
0줄, 콘솔 접촉 0건이었다. M1 run-phase(이 세션)도 `server/` 코드 변경 0줄, 콘솔
접촉 0건이다(REQ-LDBARMAP-002/003) — 측정·채점 스크립트만 `tools/barmap/`에 신설했다.

## 작성된 파일

- `.moai/specs/SPEC-LDBARMAP-001/spec.md` — REQ 15개(R1~R5), Out of Scope 5개 H3 섹션, 열린 결정 4개
- `.moai/specs/SPEC-LDBARMAP-001/plan.md` — M1~M5 마일스톤(저장 인터페이스 열린 결정을 마일스톤보다 먼저 제시)
- `.moai/specs/SPEC-LDBARMAP-001/acceptance.md` — AC 15개(Given-When-Then + 수치·단위 + REQ-ID 인용), Definition of Done
- `.moai/specs/SPEC-LDBARMAP-001/research.md` — 이 plan-phase가 실행한 10개 실측(명령+출력)
- `.moai/specs/SPEC-LDBARMAP-001/progress.md` — 이 파일

## plan-audit 이력

- iteration 1: FAIL(0.60, 통과선 0.80). `.moai/reports/plan-audit/SPEC-LDBARMAP-001-review-1.md`. D1(critical, AC-006 분모 13≠8)·D3(critical, 1마디 밀림 음성 대조군·매칭 방법론 누락)·D2(major, REQ-010/012 이중 모달)·D4(major, AC→REQ 인용 희박 + REQ-001 무검증)·D5(minor, 224.70/224.69 불일치) — 모두 spec.md·acceptance.md에 교정 반영(REQ 14→15, AC 13→15). D6(minor, 선택)은 비용 대비 효과가 낮아 보류.
- iteration 2: FAIL(0.68, 통과선 0.80). `.moai/reports/plan-audit/SPEC-LDBARMAP-001-review-2.md`. D1~D6(iteration 1) 전부 RESOLVED 재확인. iteration 1의 AC-003 신설이 그 뒤 AC 번호를 전부 1씩 밀렸는데 `plan.md`가 반영 못 함 — **D-NEW-1(critical)**: M1(`plan.md:31` AC-001~005→001~006)·M2(`plan.md:38` AC-004/005→005/006)·M3(`plan.md:45-46` AC-006→007, M3 자신이 가리키려던 이벤트 재현율은 007)을 재매핑. **D-NEW-2(minor)**: `acceptance.md` AC-009가 무관한 REQ-008을 인용 — REQ-001(간접)로 재지정. 교정 뒤 spec.md/plan.md/research.md/progress.md 전수 grep 재확인(research.md·progress.md 0건, plan.md 4건 전부 교정). REQ/AC 총량 변경 없음(15/15). 재감사(iteration 3) 대기.

## §E.1 Plan-phase Audit-Ready Signal

plan_status: audit-ready (재감사 대기 — iteration 1 FAIL 교정 완료, iteration 2 결과 미수신)
plan_complete_at: 2026-10-10

5개 산출물이 모두 작성되었고, SPEC ID 사전 검사(Bash 정규식)가 PASS했으며, 프런트매터 12개 필수 필드가 모두 채워졌다. plan-audit iteration 1 FAIL의 D1~D5 교정이 이 세션에서 완료되었다 — iteration 2 재감사 대기 상태.

## §E.2 Run-phase Evidence

### M1 — 계기 보정(카드 t530, 2026-10-10)

산출물: `tools/barmap/{__init__,ground_truth,scorer,candidates,run_calibration,test_scorer}.py`
(신규, `server/` 아래 0줄 변경) + `.moai/reports/SPEC-LDBARMAP-001-probes/{m1-calibration.md,
m1-raw-stdout.txt,m1-pytest-output.txt,m1-ruff-output.txt}`(신규, gitignore 대상이라
`git add -f`로 올림). 전체 수치·근거·Gaps는 `m1-calibration.md`에 있다 — 여기서는
AC PASS/FAIL 요약만 반복한다.

| AC | 상태 | 근거 |
|---|---|---|
| AC-LDBARMAP-001 | **PASS** | 네 지표 전부 수치+단위 출력, `git diff --stat origin/main -- server/` 출력 0줄, 콘솔 쓰기 0건 |
| AC-LDBARMAP-002 | **PASS** | 1박 밀림 음성 대조군 0/82(0.0%) < 10% |
| AC-LDBARMAP-003 | **PASS** | 1마디 밀림 음성 대조군 0/82(0.0%) < 10%(엄격한 순서 대응으로 D3 함정 차단 확인) |
| AC-LDBARMAP-004 | **PASS**(후보 A/B/C 전부) | 후보 C가 두 배 BPM 함정(raw 224.69)을 실제로 겪고 격자 정합도 비교 후 112.35로 보정 + 근거 기록. A/B는 함정 미발동(공허 PASS) |
| AC-LDBARMAP-005 | **FAIL**(후보 A/B/C 전부, 자체 위상 선택 기준 0.0%) | 세 후보의 자체 위상 선택 규칙(온셋 악센트/화성 변화/저역 도약)이 모두 정답 위상(1)을 못 골랐다 — 위상 1로 강제하면 A 100%·B 97.6%(진단용, PASS로 세지 않음) |
| AC-LDBARMAP-006 | **FAIL**(동일 격자, AC-005와 같은 이유) | 4/4박자라 다운비트=마디 경계(spec.md §5 결정 3) |
| AC-LDBARMAP-007 | **FAIL**(A 0/7, B·C 1/7=14.3%, 통과선 5/7=70%) | M1 간이 이벤트 규칙 — M3가 실제 분류기 담당 |

**M1 통과 조건("AC-001~006 전부 PASS인 후보 최소 1개 존재") 미충족** — 세 후보
모두 AC-005/006에서 FAIL한다. plan.md M1이 명시한 원칙("채점 전 채택하지 않는다")
대로 정직하게 보고한다: 세 후보의 BPM·비트 격자 자체는 거의 완벽(오차율
0.003%, 올바른 위상으로 보면 다운비트 적중 100%/97.6%)하지만, **다운비트 위상
선택(1~4박 중 어느 것이 "하나"인가)이 M1에서 풀리지 않은 문제로 남았다** — 지도
보고서 자신도 이 위상을 [미확정(귀로)]로 표기했던 바로 그 지점이다. M2는 이
위상 문제를 우선 다뤄야 한다(단일 신호 대신 앙상블/투표, 또는 사람 확인 단계
유지).

Preserve 목록 확인: `SPEC-LDRHYTHM-001`·`SPEC-LDBEAT-001` 쪽 파일 미수정, 원곡
오디오 비커밋(`git status --porcelain`에 `*.mp3`/`*.wav` 없음), `server/audio/analyze.py`는
`_tempo_from_beats`만 읽기 전용 import로 호출 — 파일 자체는 안 고침.

## §E.3 Run-phase Audit-Ready Signal

_<pending run-phase>_

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_
