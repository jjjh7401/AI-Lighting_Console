# t504 판정서 — SPEC-LDRHYTHM-001 plan

- 카드: t504 · 브랜치: `WT-rhythm-plan` · 기준: `origin/main` `c11bc540`
- 범위: plan 만. 콘솔 접촉 0, 앱 코드 0(`git diff --stat origin/main..HEAD -- server/` → 빈 출력)
- 산출물: `.moai/specs/SPEC-LDRHYTHM-001/{spec,plan,acceptance,progress}.md` — Tier M, REQ 12 · AC 11

## 1. 리드 필수 조건

| 조건 | 상태 | 근거 |
|---|---|---|
| 감독 결정 4건 원문 | 충족 | `spec.md` 「감독 결정 (원문)」 인용 블록(카드 본문 그대로). 감사 1~3차 모두 원문 일치 확인 |
| M1 대본 → M2 손 시연 → M3 규칙화가 앱 코드보다 먼저 | 충족 | REQ-LDRHYTHM-001·002(M1~M3 통과 전 앱 코드 금지) |
| 합격 = Club Diver 실기 감독 3점 이상, 기계 점검은 사전 체 | 충족 | REQ-011 · AC-009(사전 체) · AC-010(감독 ≥3/5) |
| 벤치마크 보고서 반입 | 충족 | 커밋 `2d96f54c`. sha256 원본=사본 — md `887be62d…`, html `b4dca357…`. 원본은 주 체크아웃에 그대로 둠 |

## 2. plan 감사 이력

| 회차 | 판정 | 점수 | 결함 → 처리 |
|---|---|---|---|
| 1 | FAIL | 0.75 | D1(critical): AC-006 이 SPEC 폴더 전체에서 `§10.3` 0건을 요구 — 감독 원문 인용 때문에 영원히 통과 불가. D2(minor): REQ-012 주어 둘 → `b1fdc72b` |
| 2 | PASS | 0.92 | D-NEW-1(major): AC-006 측정이 문자열 2건뿐, "큰 히트에만" 배치를 안 잼 → `a708541a`(M1 6칸 표 + 닫힌 어휘 + 배치 오프라인 검사) |
| 3 | FAIL | 0.80 | D-NEW-2(major): REQ-003·AC-003 이 옛 4칸 이름을 유지 — 2차 수정의 회귀 → `a64fd66c` |

- 보고서: `.moai/reports/plan-audit/SPEC-LDRHYTHM-001-review-{1,2,3}.md` (gitignore 대상 — 레인 트리에만 있음)
- **3차가 허용 최종 회차라 4차 감사는 돌리지 않았다.** D-NEW-2 해소는 감사관이 아니라 이 레인이 기계로 확인했다:
  - `grep -n "음악 순간\|놓는 연출\|네 칸" .moai/specs/SPEC-LDRHYTHM-001/*.md` → 3건. 감독 원문 인용(spec.md:35), HISTORY(spec.md:27), 정정 메모(acceptance.md:21)뿐이고, 요구 문장에는 남지 않음
  - 6칸 이름(시각/층/모멘트유형/연출/잇는 방식/이유)은 plan.md:47 · spec.md:64(REQ-003) · acceptance.md:25(AC-003)에서 같음
  - `moai spec lint spec.md` → `✓ No findings` (manager-spec 실행 보고)

## 3. 이 SPEC 이 사실로 다루지 않는 것(전제)

- 타임코드 이벤트가 실기에서 큐를 진행시키는지 — 미측정
- 곡 중간에 `Master 3.n At BPM` 을 큐 명령·매크로로 내는 방법 — 미측정(At SpeedMaster 결합 자체는 FXGEN spec.md:43 V3 실기 관측)
- Rain 76.01 BPM 반/두 배 오검출 위험 — 미측정
- M4+ 앱 후보 4종의 필요성 — M3 에서 다시 확인(AC-011)
- 감독 결정 (3)의 「표준 §10.3」 — 표준 문서에 그런 제목이 없다. 실제 조항은 「## 10.」 목록 4번(326~327행). 원문은 그대로 두고 REQ-006·AC-006 에서 위치를 바로잡았다

## 4. 판정

plan 산출물 완성. 감사 점수는 3차 0.80 FAIL(D-NEW-2 한 건) — 그 결함은 `a64fd66c` 로 고쳤고, 고친 뒤의 확인은 레인 기계 검사뿐이다(감사관 재확인 없음). 4차 감사·PASS-with-debt·그대로 머지 중 선택은 리드 몫. run 은 감독 착수 승인 뒤.
