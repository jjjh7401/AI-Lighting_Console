# 검증 보고 — LOVE ATTACK 프리셋 계획 미정 6건 채우기

- 브랜치: `WT-preset-plan-fill` (기반 `origin/WT-preset-plan` = `4be82172`, PR #747 헤드와 같음)
- 코드 커밋: `ebe1c04f` — `feat(beatgrid): LOVE ATTACK 프리셋 계획의 미정 6건을 기본값과 「감독이 고칠 값」으로 채운다`
- 카드 id 없음 — 리드 확인: 이름 `WT-preset-plan-fill`, 증거 위치 `.moai/reports/preset-plan-fill/`

## 1. 주장 (Claim)

1. 미정 6건을 모두 처리했다. 각 항목은 값이나 사유를 가지며, 앱이 기본값을 쓴 것은 「감독이 고칠 값」으로 승인 카드에 표시된다. 빈칸은 없다.
2. 저장은 가짜 콘솔과 픽스처만 썼다. 실콘솔에 접속하거나 쓰지 않았다.
3. 지정 선택 `pytest -k "beat_grid or prechk or timeline or preset"` 통과, `ruff` 통과.
4. 기준선 대비 통과 수 차이는 신규 테스트 수(12)와 일치한다. 기존 테스트를 지우지 않았다.

## 2. 증거 (Evidence) — 명령과 관측 출력 원문

```
$ uv run pytest -k "beat_grid or prechk or timeline or preset" -q      # 커밋 ebe1c04f 위에서
2533 passed, 4 skipped, 13588 deselected, 1 warning in 17.07s          (exit 0) — pytest-after.log

$ uv run pytest server/tests/test_love_attack_presets_fill.py server/tests/test_love_attack_presets.py -q
34 passed in 0.91s                                                      (exit 0) — after-restore.log

$ uv run ruff check server
All checks passed!                                                      (exit 0) — ruff-check-server.log

$ uv run ruff format --check server
873 files already formatted                                             (exit 0) — ruff-format-server.log
```

## 3. 기준선 (Baseline attribution)

- 기준 `4be82172`(변경 전), 같은 명령:
  `2521 passed, 4 skipped, 13588 deselected, 1 warning in 67.87s (0:01:07)` (exit 0).
- 차이: `2533 - 2521 = +12`. 신규 파일 `server/tests/test_love_attack_presets_fill.py`의 테스트 12개와 같다. 제거된 테스트 0개.
- 기존 파일 `test_love_attack_presets.py`는 기대값이 바뀐 테스트 몇 개를 고쳤다(예: DIM-100 이 이제 준비된 프리셋, 라벤더 RGB 가 정해짐). 테스트 수는 그대로다.

## 4. 뮤테이션 (protocol §3.3) — 새 단언이 실제로 막는지 확인

| 뮤테이션 (커밋 뒤에 걸고 되돌림) | 관측 | 로그 |
|---|---|---|
| A. 색 표 `「라벤더」` 를 존재하지 않는 슬롯으로 (`color_names.py`) | `3 failed, 31 passed` — 라벤더 단언 3개 빨강 | mutation-A-lavender.log |
| B. 다중 그룹 선택 구분자 `+` → `-` (`love_attack_presets.py`) | `4 failed, 30 passed` — DIM-100 저장 줄 단언 + 저장 전체 순서 단언 빨강 | mutation-B-separator.log |

- 두 뮤테이션 모두 Edit 이 성공했다(치환 문자열이 실제로 맞았다 — 「적용 안 됨」 갈래 아님).
- `git checkout --` 로 되돌린 뒤 `git status --short` 는 비었고, 같은 두 테스트 파일은 `34 passed in 0.91s` 다.

## 5. 안 잰 것 (Gaps — 미검증)

- **실콘솔 접속·쓰기 없음.** 다중 그룹 선택 저장 `Group 4 + 7 + 11 + 12 + 14 ; Attribute 'Dimmer' At 100` 이 실기 grandMA3 에서 받아들여지는지는 확인하지 않았다. 문법은 cue_sheet 가 이미 내는 꼴(t461·t476 테스트)을 따랐을 뿐이다.
- **쇼 지문 재측정 안 함** (`PresetPools/1`·`Groups` 개수). 리드가 콘솔 재측정 금지를 지시했다. 계획은 저장된 판독본 픽스처 기준이다.
- **기본 디머 속성 `Dimmer` 의 실기 확인 안 함.** 판독 경로(`_love_attack_dimmer_attributes`)가 실제 픽스처 타입에서 빈 결과를 낼 때의 동작은 테스트만 봤다.
- **라벤더 RGB `(55,35,100)` 실기 대조 안 함.** 표준 팔레트 슬롯을 그대로 쓴 기본값이다.
- **바닥 쪽 대략값을 pan/tilt 로 바꾸지 않음.** 목표는 보고서 t221 POS.04 의 말로 적었고, 위치 저장 경로(t592)는 이 카드 밖이다.
- **번호대 `confirmed: false` 해소 안 함.** 후보 번호는 여전히 잠정이다.
- CI 전체 테스트는 돌리지 않았다. 지정 선택과 `ruff` 만 돌렸다.

## 6. 잔여 위험 (Residual risk)

- DIM-100 한 선택 저장이 실기에서 다섯 그룹에 같은 값을 주고 번호 1.11 에 한 번에 담기는지는 감독이 확인해야 한다. 그룹마다 따로 저장하는 쪽으로 바꾸려면 저장 줄을 나누면 된다(감독이 고칠 값으로 표시됨).
- 승인 뒤 칸 참조 갱신은 실제 비동기 승인 경로 테스트(`TestApprovalCardRealAsyncChannel`)가 통과했지만, 가짜 승인이다.
- 공유 편집 경로(`apply_beat_grid_edit`)가 디머 프리셋 번호 변경을 승인으로 세지 않는 문제는 손대지 않았다. 리드가 정할 사항이다.
- 기반 브랜치 `WT-preset-plan` 은 `origin/main` 과 3:3 으로 갈라져 있다. #747 을 머지한 뒤 이 PR 을 `main` 기준으로 옮겨야 한다(리드가 옮기겠다고 함). `main` 세 커밋이 PR diff 에 섞이지 않도록 `WT-preset-plan` 을 기반으로 두었다.

## 7. 프로토콜 예외 (공개)

- 워크트리는 `git worktree add -b WT-preset-plan-fill … origin/WT-preset-plan` 으로 만들었다. `EnterWorktree(name)` 이 「이미 워크트리 세션」이라 거절했다. 리드 허용을 받았다. 정리는 리드가 머지 뒤에 한다.
- 구현은 서브에이전트 없이 직접 했다. 워크트리에서 띄운 에이전트가 주 체크아웃 기준 트리에 떨어지는 기록(메모리 lesson-agent-spawn-from-worktree-lands-on-main)이 있어, 쓰기 작업을 맡기지 않았다.
