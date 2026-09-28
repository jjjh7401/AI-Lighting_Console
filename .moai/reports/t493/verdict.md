# t493 판정서 — 런북 UI 시험·미리보기용 서버 출력 사본 재생성

- 카드: t493 (Class A 성격 — plan 생략, 배차서대로)
- 브랜치: `WT-payload-fixture-regen` · 워크트리 `.claude/worktrees/t493`
- base: 착수 시점 `origin/main` = `bffe308f` (`git rev-list --left-right --count origin/main...HEAD` → `0 0`)
- 선행 조건: t485(PR #540, merge `81bbb916`) · t489(PR #541) 둘 다 base 에 포함
- venv: 이 트리 자체 `uv sync --group dev`

## 판정: PASS

## 1. 재생성 명령

사본의 출처는 t458 스크립트다. 착수 시점 사본은 `.moai/reports/t458/payload.json` 과
**바이트 동일**했다(`cmp` → 동일, 14740바이트) — 즉 t458 이후 한 번도 다시 뜨지 않았다.

같은 스크립트를 **출력 경로만** t493 으로 바꿔 복사했다(docstring 첫 줄 제외 diff 는
경로 3줄뿐 — 서버 호출·입력 곡은 그대로):

    PYTHONDONTWRITEBYTECODE=1 .venv/bin/python .moai/reports/t493/measure_payload.py
    cp .moai/reports/t493/payload.json ui/src/components/runbookServerPayload.json

stdout (`regen_stdout.txt`):

    row_pairing: 'available': True, 'reason': None  rows: 21
    hex: ['#0D33FF', '#0D33FF', '#FFBF66', None, None, '#8C59FF', '#00E6FF', None]

- 결정성: 두 번 돌려 `cmp` 동일. docstring 수정 뒤 세 번째 실행도 사본과 `cmp` 동일.
- `grep -c "Rap/Solo/Dance Break"` : 전 1 → 후 **0**.

## 2. 전후 diff

- 텍스트 diff: `payload_diff.txt` (242줄)
- 구조 diff: `semantic_diff.txt` (80항목, 스크래치 스크립트로 키 단위 비교)

**t489 한 건만 낡은 게 아니었다.** 사본이 t458 시점에 멈춰 있어서 그 뒤 서버에 들어간
변경이 전부 빠져 있었다:

| 변화 | 개수 | 출처(추정 아님 — 키 이름으로 대조) |
|---|---|---|
| `concept_report.rows` 20 → 21 · `mib` 20 → 21 · `energy_report_count` 20 → 21 | 각 1 | t489 — Outro 가 제 칸으로 가며 눈 리셋 큐(148.0, 「드롭 직전의 정적」) 1행 추가 |
| q19 `Rap/Solo/Dance Break` → `Final Chorus`(phrase) · q20 `Outro` 섹션 · q21 safety | 3행 | t489 |
| 게이트 G9·G11·G13 detail 숫자 · `lint_finding_count` 13 → 14 | 4 | t489 의 1행 추가가 번진 것 |
| `rows[].description` 추가 | 20 | 큐 설명 필드(t486 이 밝기 수치 제거한 형태) |
| `rows[].unused_groups` · `concept_report.reserve` 추가 | 20 + 1 | t461 예비 그룹 |
| `rows[].evidence` null → 문자열 | 13 | 근거 문자열 |
| `concept_report.glance` · `concept_bullet` 추가 | 1 + 1 | 한눈 요약 · t485 인과 불릿(인터뷰 기록 없음 → available false) |
| `sections[1,3,5].intensity[].level` 70/56 → 25/20 · 20/16 | 6 | 밝기 예산 쪽 변경 |

마지막 행(intensity)과 evidence 는 **어느 카드인지 이 카드에서 짚지 않았다** — 키 이름만으로는
출처가 안 갈린다. 서버 실경로가 지금 내는 값이라는 것만 확정이다.

## 3. 잠금 20 → 21

`ui/src/components/runbookM7Third.test.tsx:36` `toHaveLength(20)` → `21`, 시험 이름도 21행.
머리 주석에 재생성 경로(t493) 한 줄 추가.

## 4. 검증 — 세 칸 + 대조군

| 사본 | 잠금 | 결과 | 증거 |
|---|---|---|---|
| 옛 사본 | 20 | `34 files · 741 passed` | `ui_before.txt` |
| 새 사본 | 20 | `1 failed | 740 passed` — 실패는 잠금 하나뿐 | (실행 로그, 본문) |
| 새 사본 | 21 | `34 files · 741 passed` | `ui_after.txt` |
| **대조군** 옛 사본 | 21 | `1 failed | 15 passed` (그 파일) | `control_old_fixture_lock21.txt` |

- 대조군 두 팔: 새 잠금은 옛 사본을 **잡고**(4행), 옛 잠금은 새 사본을 **못 통과시킨다**(2행).
- 회귀 계산: 시험 수 741 → 741, 순증 0 — 기존 검사의 숫자만 바꿨고 추가·삭제 없음. 맞다.
- 타입: `npx tsc --noEmit -p .` → exit 0.
- 린트: `uv run ruff check .moai/reports/t493/measure_payload.py` → All checks passed
  (첫 줄 E501 을 줄바꿈으로 감쌌다 — 출력은 cmp 동일 유지).
- 다른 두 소비처(`runbookMibWarning.test.tsx`, `runbookPreview.tsx`)는 사본을 바꿔도 시험이 안 움직였다.

## 5. 안 잰 것

- **미리보기 화면을 눈으로 안 봤다.** `runbookPreview.tsx` 가 이 사본을 그리는데, 새 키
  (`description`·`reserve`·`glance`·`concept_bullet`)가 화면에 어떻게 나오는지는 시험 밖이다.
- 서버 전체 스위트는 안 돌렸다 — 서버 코드 변경 0. CI 가 PR 헤드에서 돈다.
- 사본이 **다시 낡는 것**을 막는 장치는 없다. 이번에도 서버 변경 여러 건이 사본에 반영 안 된
  채 UI 시험이 초록이었다. 잠금 숫자 하나는 행 수만 문다 — 새 키 추가는 못 잡는다.
  (서버 쪽에 「사본 == 현재 실출력」 대조 시험을 두면 잡히지만, 범위를 넓히는 일이라 여기선
  안 했다 — 카드로 세울지는 리드 판단.)

## 6. 커밋 뒤 가드 (§3.1 순서)

커밋 `f9e2abc9` 뒤 `PYTHONDONTWRITEBYTECODE=1 uv run pytest server/tests/test_overlap_preserve.py server/tests/test_runbook_payload_t455_t456.py -q`
→ `86 passed` (`server_guard_after_commit.txt`). 서버 쪽 21행 잠금(t489)과 이 사본이 같은 행 수를 문다.
