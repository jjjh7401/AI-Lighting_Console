# SPEC-LDBARMAP-001 — 진행 기록

카드: t527. 이 세션은 plan-phase만 수행했다 — `server/` 코드 변경 0줄, 콘솔 접촉 0건.

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

## 인터페이스 맞춤 (카드 t529, 2026-10-10)

- 바뀐 곳: `spec.md` frontmatter(version만), §5 열린 결정 0·항목 1(권고 모양 추가), HISTORY 1행, version 0.1.0→0.1.1. **REQ 표·`acceptance.md`·`plan.md`는 한 글자도 안 바꿨다.**
- plan-audit 재실행 안 함 — 사유: 추가한 것은 §5 열린 결정 안의 **권고**(확정 아님)뿐이고, 저장 형태 확정 금지(REQ-LDBARMAP-010)·마디 지도 없이는 생성 로직 미구현(REQ-LDARRANGE-001)·STROBE는 임팩트 마디에만(REQ-LDARRANGE-008) 같은 구속의 뜻은 그대로다. 권고 모양은 그 구속들이 이미 요구하는 것(마디 단위, REQ-LDBARMAP-007의 단위 명시, REQ-LDBARMAP-008의 사건 4종)에 이름을 붙인 것이다.
- 마디 번호 공간 실측(t529): 지도 보고서 §2 "마디 번호는 위상 1 기준이다. 1마디 = 1.50초. 0.96초의 첫 박은 못갖춘마디" · 같은 보고서 18마디 = "후렴 1 진입 — 큰 히트" · 배치 규칙서 §3 18~21행 = "코러스 1 앞", §4 첫 행 = "0~2" — 두 문서가 같은 번호 공간을 쓰고 0은 못갖춘마디다.
- 남은 일(같은 카드): LDBEAT 저장 키(REQ-LDBEAT-006) 맞춤 — t526 머지 뒤.

## §E.2 Run-phase Evidence

_<pending run-phase>_

## §E.3 Run-phase Audit-Ready Signal

_<pending run-phase>_

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_
