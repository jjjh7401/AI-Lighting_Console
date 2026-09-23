# t434 판정 — SPEC-LDDESIGN-001 M2 큐 모델 v2 (REQ-017~025)

- 레인: lane-1 · 워크트리 `.claude/worktrees/t434` · 브랜치 `WT-lddesign-cue-model`
- 기준: `origin/main@20c027ff`(PR #478 머지 포함) 위 4커밋
- 판정: **PASS(범위 한정)** — 아래 「안 잰 것」 참조

## 산출물

| 파일 | 내용 |
|---|---|
| `server/concept/cue_model.py` | 7필드 타입(`CueV2` 외), 닫힌 어휘 검증, `layer_limit_warning` |
| `server/concept/resolver.py` | `apply()` 9동작, `resolve_sequence()`, `mib_verdict()`, `compute_headroom()` |
| `server/concept/description.py` | 큐 설명 자동 생성 `describe()` |
| `server/tests/test_concept_resolver.py` | 시험 40건 |
| `spec.md` | `status: draft → in-progress` |
| `progress.md` | Run-phase 증거(레인이 정정 4곳 반영) |

## 레인이 직접 잰 것

1. 병합 트리 시험 — `uv run pytest server/tests/test_concept_resolver.py server/tests/test_concept_vocab.py server/tests/test_concept_worksheet.py server/tests/test_song_cue_color_emission.py -q` → `161 passed`, exit 0 (`pytest_concept.txt`)
2. `ruff check` → All checks passed · `ruff format --check` → 7 files already formatted
3. **변이 시험 1 — 겹침 곱셈(REQ-021)**: `reduce` 가 기준 상태 대신 현재 상태를 곱하도록 한 줄 바꿈 → **3 failed**(AC-010 모양 시험 포함) → 복원
4. **변이 시험 2 — 색 없는 복원(REQ-020)**: `restore` 에서 색 복사를 지움 → **2 failed**(AC-030 종단 시험 포함) → 복원
5. 시험 개수 `--collect-only`: resolver 40 / M1 101 (에이전트 보고 46/95 는 틀림 — 정정함)

## reduce 기준 규칙 (리드 정정 반영)

`ref` 있으면 `bases[ref]`(없으면 거절) → `ref` 없으면 구간 자기 1회차 기준 → 둘 다 없으면 거절.
현재 누적 상태로 떨어지는 길은 없다. 대조군: Too Cool 50→25→25, 금지형 50→25→12 를 판별.

## 안 잰 것

- 해석기를 `session.py`/`tools.py` 에 배선하지 않았다 — M6 범위. 지금 무대에는 영향 0.
- 전체 시험은 로컬에서 돌리지 않았다 — CI 에 맡긴다(레인 규약).
- 실기 콘솔 0회 — 순수 데이터 계층.
- `cue_kind` 3종 식별자(`section`/`phrase`/`beat_accent`)는 구현이 고른 이름 — M4 에서 재확인.
- MIB 는 판정만. Mark 큐 삽입(REQ-063)은 M5.
