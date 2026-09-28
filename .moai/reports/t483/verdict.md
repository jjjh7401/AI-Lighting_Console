# t483 판정서 — Q2 'edm 느낌' 주색이 수식어 '단색'으로 잡혀 색 줄 0

- 카드: t483 · SPEC-LDDESIGN-001 · 브랜치 `WT-edm-color-token`
- 기준 트리: `origin/main` = `4ecbf879` (`1e16bd8f` 포함 확인: `git merge-base --is-ancestor 1e16bd8f HEAD` → OK)
- 콘솔 쓰기: 0

## 판정: PASS (범위 안) · 같은 모양의 범위 밖 결함 2건 보고

## 원인 (재현으로 확인)

- Q2 후보 값은 표준 §7 행 문장 그대로다(`server/design/interview.py` `_q2_color_candidates`).
  edm 행 = `"단색 볼드, 퍼플/레드/화이트"`.
- `_palette_value_tokens` → `('단색','볼드','퍼플','레드','화이트')`. `_arc_palette` 는 반환 첫 칸을
  항상 `base[0]` 로 고정(t409 불변식) → 모든 구간 주색 = `'단색'` → `resolve_color_name` None.
- 원인 한 번 의심: `resolve_color_name` 은 옳다('단색'은 색이 아니다). 결함은 설명 문장의 단어를
  전부 색으로 취급하는 토큰 함수 쪽 — 고칠 자리는 토큰 함수.

## 수정 (`server/design/interview.py`, +19/−1)

`_promote_first_color`: 앞머리에서 **표준 표 어휘(`_KNOWN_COLOR_TOKENS`)이면서 RGB 로 안 풀리는**
토큰만 건너뛰고, 처음 풀리는 색 이름을 맨 앞으로 올린다. 토큰은 버리지 않고 순서만 바꾼다.
감독이 쓴 모르는 말(`민트`)을 만나면 멈춘다 — 그 자리를 뺏지 않는다.
`server/design` 의 다른 파일(t480 이 옮기는 중)은 건드리지 않았다.

## 증거

| 주장 | 명령 | 관측 |
|---|---|---|
| RED (수정 전) | `.venv/bin/python -m pytest -q server/tests/test_q2_modifier_token_primary_t483.py` | `5 failed, 3 passed` — 메탈·edm 주색 토큰, 곡 큐 경로 `director color '단색' is not in the standard 10-color palette` |
| GREEN | 같은 명령 | `8 passed` |
| 관련 시험 | `pytest -k "interview or palette or songcue or color or q2 or design_profile or concept" server/tests` | `1370 passed, 2 skipped` |
| 서버 전체 | `pytest -q server/tests` → `pytest_server_full.txt` | `1 failed, 14569 passed` — 실패 1 = `test_tree_identity` (주 체크아웃 venv 로 돌린 탓) |
| 그 1건 재확인 | `uv run python -m pytest -q server/tests/test_tree_identity.py …t483.py` | `12 passed` |
| 8곡 게이트 | `uv run python .moai/reports/t444/gen_gates_8songs.py` → `gates_8songs.txt` | `집계: PASS 75 · n/a 29 · FAIL 0` (기준선 유지) |
| 린트 | `uv run ruff check` / `ruff format --check` (변경 2파일) | `All checks passed!` / `2 files already formatted` |
| 장르 행 전수 | `uv run python .moai/reports/t483/probe_genre_tokens.py` → `genre_tokens_after.txt` | 메탈 첫 토큰 `스래시`→`레드`, edm `단색`→`퍼플`, 록·발라드 불변 |

## 장르 행 전수 (5행)

| 행 | 수정 전 주색 | 수정 후 주색 |
|---|---|---|
| 메탈 | 스래시 ✗ | 레드 ✓ (같은 모양 — 함께 고쳐짐) |
| 록 | 레드 ✓ | 레드 ✓ |
| edm | 단색 ✗ | 퍼플 ✓ |
| 발라드 | 블루 ✓ | 블루 ✓ |
| 팝 | 유사색 ✗ | 유사색 ✗ — 풀리는 색 토큰이 **하나도 없음**, 순서로 못 고침 |

## 범위 밖 (카드 후보, 이 PR 에서 안 고침)

1. **색 이름이 하나도 없는 Q2 후보가 9개** — 팝 행, 컨셉 `빈티지`(웜 CTO), 무드 `Center`·`Ring In`·
   `Cross`·`Fan Out`·`Wall`·`Home`, 기본 조합(`중립 화이트`). 이걸 고르면 edm 과 같은 경로로 주색이
   RGB 로 안 풀린다(추론 — 곡 큐 경로는 edm 만 실행으로 확인, 나머지는 토큰 표로만 확인).
2. **`화이트` 자체가 `resolve_color_name` 에서 None** — 표준 팔레트에 `Warm White` 만 있다.
   (`genre_tokens_after.txt` 의 `('화이트', False)`)
3. `server/concept/color_strip.py` `_split_interview_color_tokens` 는 독립 재구현이라 이 수정이 안
   닿는다 — 워크시트 팔레트가 빈 곡에서 edm 답을 받으면 주색이 여전히 `단색`(코드 판독, 미실행).

## 안 잰 것

- 실기 콘솔 반영(콘솔 쓰기 0). Ice cream·Rain 곡으로 재생성해 색 줄 수를 다시 세지 않았다 —
  곡 큐 경로는 시험의 5구간 픽스처로만 확인.
- t480(업로드 D4) 경로가 함께 고쳐지는지는 t480 브랜치에서 안 쟀다.
