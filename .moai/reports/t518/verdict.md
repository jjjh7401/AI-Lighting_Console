# t518 판정서 — SPEC-LDRHYTHM-001 REQ-LDRHYTHM-012 shall 복원 + t516 요약

- 카드: t518 · 레인 lane-3 · 브랜치 `WT-req012-shall` (기준 `53a2bd9b`, PR #561 머지)
- 범위: plan 문서 2개(`spec.md`, `progress.md`)만 고쳤다. 코드 0 · 콘솔 0 · 다른 REQ/AC 0. 감사는 리드 지시로 생략했다(리드가 diff 를 읽는다).

## 바뀐 것

| 파일 | 변경 |
|---|---|
| `spec.md` REQ-LDRHYTHM-012 행(지금 108행) | 첫 절에 `**shall**` 한 단어만 넣었다: 「…**범위 후보**로만 **shall** 기록된다」 |
| `spec.md` 머리말 | `updated: 2026-10-06` → `2026-10-07` (버전·상태 그대로) |
| `spec.md` HISTORY | 2026-10-07 t518 행 하나 추가 (이 SPEC 은 수정마다 HISTORY 행을 남긴다 — 리드 지시 밖, 관례를 따랐다) |
| `progress.md` | 새 절 「M2 착수 전제 — t516 실기 능력 확인 (2026-10-07)」 + 「M1 감독 승인」의 낡은 「t516 진행 중·보고서 미작성」 줄 아래 갱신 메모 한 줄(원문은 그대로) |

## 증거 (이 트리, 이 세션에서 실행)

| 확인 | 명령 | 결과 |
|---|---|---|
| REQ-012 행에 shall 1개 | `sed -n '108p' spec.md \| grep -o shall \| wc -l` | `1` (전에는 0 — t517 plan-audit D1) |
| REQ-012 행의 변경이 shall 한 단어뿐 | HEAD 판 행과 새 행에서 ` **shall**` 을 뺀 것을 `cmp` | 같음 |
| spec lint | `moai spec lint .moai/specs/SPEC-LDRHYTHM-001/spec.md` | `✓ No findings`, exit 0 |
| 바뀐 규모 | `git diff --stat` | 2 files, +11 −2 |
| progress 인용 | `.moai/reports/t516/verdict.md` 요약 표(맨 위), 승인=송신 64·101행, ④ 104행 | 문면과 대조해 맞음 |

## 안 잰 것 / 남은 것

- `moai spec lint` 를 `progress.md` 에 돌리면 `ParseFailure`(머리말 없음)가 난다. 이 파일은 HEAD 에서도 머리말 없이 `# SPEC-LDRHYTHM-001 — 진행 기록` 으로 시작하므로 이번 변경 탓이 아니다. lint 가 progress.md 를 대상으로 하지 않는다는 건 추론이다.
- 줄 번호: 카드 본문의 「spec.md:107」은 수정 전 번호다. HISTORY 행이 하나 늘어 REQ-012 는 지금 108행이다.
- plan-auditor 재감사는 돌리지 않았다(리드 지시).
