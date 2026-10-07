# t523 판정서 — SPEC-LDRHYTHM-001 M3 기록 + 박자 배치 규칙 보고서 반입

- 카드: t523 · 브랜치 `WT-rhythm-m3` · 기준 `origin/main` `5ccd1d1c` · 2026-10-07
- 성격: 문서만. 코드 0 · 콘솔 0

## 1. 결과 요약

| 카드 지시 | 결과 | 증거 |
|---|---|---|
| ① 미추적 보고서 넷을 그대로 싣기 | 완료 | 아래 §2 sha256 — 주 체크아웃 원본과 네 파일 모두 동일 |
| ② progress.md·HISTORY 에 M3 확정·방향 전환 기록, 감독 원문은 §5 그대로 | 완료 | spec.md HISTORY 2026-10-07 t523 행 · progress.md §E.2 「M3 — 규칙 확정」. 원문 두 건 `grep -F` 로 보고서 §5 와 일치 확인(감사 review-5 (a)) |
| ③ plan.md M2 「0~25마디」 정정 메모만, 원문 보존 | 완료 | plan.md M2 아래 블록쿼트. 커밋 diff 에 삭제 줄 0(감사 review-5 (c)) |
| ④ 표준 문서 교정은 plan.md §D 범위만 | **변경 0** — 고칠 인용 조항이 없었다 | M1 대본의 §2.1/§2.3 인용은 벤치마크 보고서를 가리킨다(대본 9행 인용 규칙). 표준 문서 인용은 「§10 금지목록 4번」 하나이고 이미 바르게 적혀 있다. 대본 안 `§10.3` 0건 |
| ⑤ plan-auditor 1회 | **PASS 0.91** (Tier M 기준 0.80) | `.moai/reports/t523/plan-audit-review-5.md` |

REQ/AC 수 12/12 그대로, 새 ID 0, `status: in-progress` 그대로.

## 2. 보고서 반입 — 바이트 동일

`shasum -a 256` (저장소 사본 = 주 체크아웃 원본, 네 파일 모두 같은 값):

| 파일 | sha256 |
|---|---|
| `reports/effect-arrangement-rules-20261007.md` | `61850937499cee6fc5a3303bea2838df29f9d0844e30fd8eee5833f4d1bd485b` |
| `reports/effect-arrangement-rules-20261007.html` | `0d4b551755c4041793622aa81f626fec7fc6d0774c5ebbf4a63238eac45f54f7` |
| `reports/effect-arrangement-research-pro-20261007.md` | `86b199ad7979700d351a9a50928b8b140574f0cab3d7017e1c785efdd74587c2` |
| `reports/effect-arrangement-research-kpop-20261007.md` | `0c82ae115434b2cceb6d3c824af977cd1926c05d376066bc499f3b25670700f7` |

## 3. 레인이 잡아 고친 것

- **manager-spec 초안의 거짓 사실 1건**: progress.md 에 「t520 판정서는 PR #561 머지 `53a2bd9b` 로 이미 main 에 실렸다」고 적었다. 재보니 `git ls-tree -r --name-only origin/main -- .moai/reports/t520/` → **0건**이고, t520 판정서는 `origin/WT-m2-batch1` 에만 있다. PR #561 은 t516 이다. 「아직 main 에 없다, 반입은 보고서 §7 3번 몫」으로 고쳤다. 그 뒤 푸시 직전 재측정에서 t520 이 PR #565(`af3298ff`)로 main 에 머지된 것을 확인해, origin/main 을 이 브랜치에 병합하고 문장을 「PR #565 로 main 에 실렸다」로 다시 고쳤다.
- **감사 D1(major)**: plan.md M3 첫 문단은 「M2 에서 감독이 줄마다 어울림 표시한 증거」에서 규칙을 뽑는다고 적혀 있는데, 실제 규칙은 조사 두 편 + t520 §20 + M1 대본에서 리드가 정리하고 감독이 확정했다. M3 아래에 정정 메모를 달았다 — **감독 승인 규칙이지 실기 줄 단위로 검증된 규칙은 아니다**, 실기 확인은 t522 몫. 원문 보존.

## 4. 안 잰 것 · 남은 위험

- D1 정정 메모는 감사 뒤에 추가했다 — 그 메모 자체는 재감사하지 않았다(카드 지시가 감사 1회).
- t520 머지 반영 문장은 병합 뒤 다시 쓴 것이라 감사 대상이 아니었다.
- `server/`·`ui/`·`docs/` 무변경: `git diff --quiet 5ccd1d1c -- server/ ui/ docs/` → exit 0.
