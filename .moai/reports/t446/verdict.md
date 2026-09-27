# t446 판정서 — 절 무버 소등을 REQ-064 조건으로 배선

- 카드: t446 · SPEC-LDDESIGN-001 · 브랜치 `WT-movers-off` · 기준 `c4506a7c` (origin/main)
- 감독 결정(2026-09-27, 리드 배차로 전달): 끄지 않는 절에서는 무버를 그 절 밝기로 낮춘다. AC-LDDESIGN-010 Too Cool 절1 45% 잠금은 유지한다.
- 콘솔 쓰기: **0**. 순수 계산 계층(`server/concept/`)만 바꿨다.
- `server/orchestrator/tools.py`: 건드리지 않았다(lane-2 t476 영역).

## 무엇이 바뀌었나

1. **절 큐의 무버 동작** (`server/concept/density.py` Verse 분기, `_verse_mover_ops`)
   - 다음 후렴이 새 포지션을 요구하면 → 무버를 끈다(어두운 창에서 옮기도록, 지금까지와 같음).
   - 요구하지 않으면 → 무버를 절 밝기로 **낮춘다**. 1회차는 45, 2회차 이후는 `round(45×0.85)=38`이다. 포지션 값은 내지 않으므로 그대로 유지된다.
   - "낮춘다"이므로 `min(절 직전 밝기, 절 밝기)`를 쓴다. 절 직전에 꺼져 있던 무버(예: Intro 다음 첫 절)는 켜지 않는다.
   - 2회차 이후 절은 `restore Verse 1`이 1회차 무버 값을 다시 들여오므로, 회차마다 무버 동작을 따로 붙인다.
2. **예측 결함 수정** (`_chorus_section_position` 신설)
   - `_next_chorus_position`은 k=1 후렴(실제 `back`)과 Final Chorus(실제 `audience`)를 모두 `front`로 예측했다.
   - 그대로 배선했다면 Final Chorus 앞 절에서 "옮길 필요 없음"으로 판정해 무버를 켜 둔 채로 두고, Final Chorus에서 **켜진 채 포지션을 옮겼을** 것이다. REQ-064가 막으려는 바로 그 경우다.
   - 조립기의 후렴 분기와 예측이 같은 함수를 쓰게 합쳐서, 둘이 다시 갈라질 수 없게 했다.
3. **Bridge는 배선하지 않았다.** REQ-046이 "KEY·BACK 외 그룹을 무조건 끈다(SHALL)"고 정하고, 감독 결정도 절만 다룬다. 주석만 고쳤다.
4. **잠금 시험 한 줄 변경** (`test_verse_first_occurrence_clears_prior_mover_and_wash_state`)
   - 유지: 절1 최대 밝기 `== 45`(AC-010 잠금).
   - 변경: "무버가 꺼져 있다" → "무버가 켜져 있으면 45 이하이고 포지션은 직전과 같다". 이 부분이 바로 감독 결정이 뒤집은 내용이다.

## 증거

| 항목 | 명령 | 결과 | 파일 |
|---|---|---|---|
| RED(수정 전) | `uv run pytest -q server/tests/test_concept_density_verse_mover_wiring.py` | 3 failed, 2 passed | `red_before_fix.txt` |
| 8곡 게이트 전 | `uv run python .moai/reports/t444/gen_gates_8songs.py` @ `c4506a7c` | PASS 75 · n/a 29 · FAIL 0 | `gates_before.txt` |
| 8곡 게이트 후 | 같은 명령 @ 변경 후 | PASS 75 · n/a 29 · FAIL 0, 표 바이트 동일 | `gates_after.txt` |
| 무버·MIB 전 | `measure_movers.py before <c4506a7c 의 density.py>` | 절 31개 전부 무버 0 · MIB dark 15 / mark 8 / live 0 | `movers_before.txt` |
| 무버·MIB 후 | `measure_movers.py after` | 절 31개 중 11개 무버 유지(45×3, 38×8) · MIB dark 15 / mark 8 / live 0 | `movers_after.txt` |
| 범위 시험 | `uv run pytest -q -x server/tests -k "concept or density or mib or gates or song or timeline or design"` | 2074 passed, 14 skipped | `pytest_scoped.txt` |
| 변이 ① 예측을 옛 규칙으로 | `_chorus_section_position` → `_chorus_position` | 4 failed | `mutation_prediction.txt` |
| 변이 ② `min` 제거(무버를 올림) | `min(prev, top)` → `top` | 1 failed(`test_movers_off_before_verse_stay_off`) | `mutation_min.txt` |
| 린트 | `uv run ruff check` / `ruff format --check` (바뀐 파일) | exit 0 / exit 0 | `ruff_check.txt` · `ruff_format.txt` |

`gates_before.txt`의 앞 5줄은 venv를 처음 만들 때 나온 메시지다. 이 5줄을 빼면 `gates_after.txt`와 같다(`diff` 결과가 그 5줄뿐임).

곡별로 보면 무버를 유지하는 절이 있는 곡은 Club Diver(1), Cut and Run(5), Too Cool(4/6), neon(1/7)이다. Ice cream·Morning·Rain·DinoDino는 전과 같다.

## 안 잰 것

- **8곡 게이트는 이 변화를 보지 않는다.** 게이트 표가 바이트까지 같은 것은 "나빠지지 않았다"는 뜻일 뿐, 무버 유지를 검증했다는 뜻이 아니다. 무버 변화는 `measure_movers.py`로 따로 쟀다.
- 실기 콘솔 발사, 화면 확인은 하지 않았다.
- 절에서 무버를 38·45%로 켜 두는 것이 무대에서 괜찮아 보이는지는 감독이 눈으로 확인해야 한다.
- 무버 두 그룹의 절 직전 밝기가 서로 다르면 동작이 두 개로 나뉜다. 8곡에서는 이런 절이 0개였다(`movers_after.txt`의 `lvl` 집합이 모든 절에서 원소 하나). 그러니 그 갈래는 8곡 데이터로 검증되지 않았다.
- 전체 시험 모음(12417개 선택 해제분)은 돌리지 않았다. CI에 맡긴다.

## 남은 위험

- `_tracked_state`는 절마다 지금까지 만든 행 전체를 다시 해석한다(O(n²)). 곡당 큐 수가 10~45 범위(G13)라 문제는 없지만, 큐가 많아지면 느려질 수 있다.
- `mib.movers_off_ops`(구간 이름만 보는 함수)는 여전히 호출하는 곳이 없다. 지우지 않았다.
