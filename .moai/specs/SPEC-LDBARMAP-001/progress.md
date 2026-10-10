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
- iteration 2: FAIL(0.68, 통과선 0.80). `.moai/reports/plan-audit/SPEC-LDBARMAP-001-review-2.md`. D1~D6(iteration 1) 전부 RESOLVED 재확인. iteration 1의 AC-003 신설이 그 뒤 AC 번호를 전부 1씩 밀렸는데 `plan.md`가 반영 못 함 — **D-NEW-1(critical)**: M1(`plan.md:31` AC-001~005→001~006)·M2(`plan.md:38` AC-004/005→005/006)·M3(`plan.md:45-46` AC-006→007, M3 자신이 가리키려던 이벤트 재현율은 007)을 재매핑. **D-NEW-2(minor)**: `acceptance.md` AC-009가 무관한 REQ-008을 인용 — REQ-001(간접)로 재지정. 교정 뒤 spec.md/plan.md/research.md/progress.md 전수 grep 재확인(research.md·progress.md 0건, plan.md 4건 전부 교정). REQ/AC 총량 변경 없음(15/15).
- iteration 3: **PASS(0.86, 통과선 0.80)**. `.moai/reports/plan-audit/SPEC-LDBARMAP-001-review-3.md`(주 체크아웃, gitignore — 1~3행 `Verdict: PASS` / `Overall Score: 0.86`). must-pass 7개 PASS, D-NEW-1/D-NEW-2 RESOLVED 재확인. Implementation Kickoff Approval 가능 판정 — 감독 착수 승인 2026-10-10(M1~M3, 카드 t530).

## §E.1 Plan-phase Audit-Ready Signal

plan_status: audit-passed (iteration 3 PASS 0.86 — 2026-10-10, 정정: 카드 t530)
plan_complete_at: 2026-10-10

5개 산출물이 모두 작성되었고, SPEC ID 사전 검사(Bash 정규식)가 PASS했으며, 프런트매터 12개 필수 필드가 모두 채워졌다. plan-audit iteration 1·2 FAIL 교정을 거쳐 iteration 3에서 PASS(0.86)했다.

## 인터페이스 맞춤 (카드 t529, 2026-10-10)

- 바뀐 곳: `spec.md` frontmatter(version만), §5 열린 결정 0·항목 1(권고 모양 추가), HISTORY 1행, version 0.1.0→0.1.1. **REQ 표·`acceptance.md`·`plan.md`는 한 글자도 안 바꿨다.**
- plan-audit 재실행 안 함 — 사유: 추가한 것은 §5 열린 결정 안의 **권고**(확정 아님)뿐이고, 저장 형태 확정 금지(REQ-LDBARMAP-010)·마디 지도 없이는 생성 로직 미구현(REQ-LDARRANGE-001)·STROBE는 임팩트 마디에만(REQ-LDARRANGE-008) 같은 구속의 뜻은 그대로다. 권고 모양은 그 구속들이 이미 요구하는 것(마디 단위, REQ-LDBARMAP-007의 단위 명시, REQ-LDBARMAP-008의 사건 4종)에 이름을 붙인 것이다.
- 마디 번호 공간 실측(t529): 지도 보고서 §2 "마디 번호는 위상 1 기준이다. 1마디 = 1.50초. 0.96초의 첫 박은 못갖춘마디" · 같은 보고서 18마디 = "후렴 1 진입 — 큰 히트" · 배치 규칙서 §3 18~21행 = "코러스 1 앞", §4 첫 행 = "0~2" — 두 문서가 같은 번호 공간을 쓰고 0은 못갖춘마디다.
- ③ 저장 키 맞춤(t529 후속, 2026-10-10): §5 열린 결정에 세 SPEC 공통 권고 키 `timeline["beat_grid"]`/`["bar_map"]`/`["arrangement_draft"]` 추가. 권고뿐 — REQ·AC·plan.md·acceptance.md 변경 0, plan-audit 재실행 없음.

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
