# 카드 t563 — run 판정 (SPEC-LDBEAT-001, 상단 바 콘솔 버튼 → M4 송신 경로)

- 범위: REQ-LDBEAT-011~013·017. 상단 바 「▶ 이 마디 콘솔에서 보기」「■ 끄기」「⇪ 콘솔에 반영(대기 수)」 배선
- 트리: `.claude/worktrees/t563`, 브랜치 `WT-console-send-wire`, 기준 `origin/main` `1d1aa813`
- 리드 결정 2건 반영: (1) A안 — 배선 + 번호는 이미 있는 길로(곡 파일에 번호 필드 금지), (2) `unsent_cells` 계약(t568과 합의)
- 실기 콘솔 쓰기: 0 (모든 시험은 가짜 콘솔·가짜 게이트)

## 1. 입력 넷 — 전부 기존 함수 재사용

| 입력 | 출처 | 못 읽으면 |
|---|---|---|
| 트랙별 시퀀스 번호 | `songcue.select_sequence_number` — 다시 읽은 시퀀스 풀에서, 트랙마다 앞에서 고른 번호를 점유로 더해 차례로 | 묶음 전체 거절(풀 미응답·잘림·번호 없는 자식) |
| 타임코드 번호 | 감독 입력 `timeline["timecode_number"]` + `tools.timecode_slot_verdict` | 없음·점유·모름이면 거절 |
| 디머 속성 | `read_design_rig` + `dimmer_attribute_names` | 아래 규칙 |
| 곡 타이밍 | `timeline["bar_map"]` → bpm·박자·1마디 `start_ms`·0마디 박 수 | 에미터가 묶음 전체 거절 |

**디머 속성 규칙(판단)**: 서버에는 그룹 소속을 읽는 함수가 없다(t525 — 콘솔 `SELECTIONDATA`에는 있으나 서버 판독 함수 0). 그래서 리그 판독이 완전하고 패치된 모든 기종의 디머 속성이 똑같을 때만 그 값을 모든 트랙에 쓴다. 그룹은 패치의 부분집합이라, 이 조건에서는 어떤 그룹에도 맞다. 기종마다 다르거나 판독이 불완전하면 빈 값을 넘긴다 → 에미터가 **밝기 "값" 칸만** 자체 사유로 막는다(프리셋 칸은 그대로 나감).

## 2. 동작

- **반영**: 입력 넷 → 에미터 → 막히면 콘솔 0줄 + 사유·막힌 칸 표시 → `build_write_approval_batch`로 승인 묶음 **1개** → 기존 `run_commands` → 안전 게이트(감독 승인 카드) → `verify_approval_vs_sent`로 승인=송신 대조 → **대조가 맞을 때만** 곡별 칸 스냅숏 갱신.
- **미리보기/끄기**: 마지막 성공 반영 기록(트랙별 시퀀스 번호·마디별 큐 번호)으로 `Goto Cue <k> Sequence <s>` / `Off Sequence <s>`. 반영 기록이 없으면 거절. `PreviewApprovalSession`이 세션 1회 승인을 맡고, 쓰기 승인과는 섞이지 않는다.
- **대기 수**: `BeatGridView.unsent_cells: [{group_name, bar}] | null` — 스냅숏과 다른 칸(추가·변경·삭제). 스냅숏이 없으면 `null`(빈 목록 아님). 상단 바 숫자 = `len(unsent_cells)`, `null`이면 숫자 없음. 이름 체계는 `apply_beat_grid_edit`의 `target`·`bar`와 같다. 「고침=초록」은 lane-2(t568) 몫이라 손대지 않았다.
- **WS**: 보내기 `beat_grid_apply`·`beat_grid_preview {bar}`·`beat_grid_preview_off` / 받기 `beat_grid_send_status`. `test_prechk_tool.py` 고정 목록과 `test_write_dispatch_census.py` 쓰기 진입점 표에 등재.
- **찾아서 고친 결함**: 이 진입점들은 `run_instruction` 체인 밖이라, 세션 키를 직접 묶지 않으면(`bind_session_key`) 승인 카드가 0장인 채로 조용히 거절됐다. 세션 메서드를 직접 부르는 시험은 이걸 못 잡았고, WS 왕복 시험이 잡았다.

## 3. 증거 (이 트리에서 직접 다시 잼)

| 주장 | 명령 | 관측 |
|---|---|---|
| 새 시험이 먼저 실패 | 구현 에이전트의 첫 실행(보고 인용) | `11 failed, 15 passed` |
| 관련 시험 | `uv run pytest -q test_beat_grid_send_t563.py test_web_beat_grid_send_t563.py test_prechk_tool.py test_write_dispatch_census.py test_beat_grid_emit_t549.py` | `156 passed, 1 skipped` |
| 서버 전량(CI와 같은 명령) | `npm --prefix ui run build` 뒤 `uv run pytest -q -rs` | 1회차 `1 failed`(제가 고친 줄이 100자 초과 — `TestTouchedFilesPassLint`) → 줄 나눔·포맷 뒤 2회차 `15116 passed, 33 skipped` exit 0 |
| UI 전량 | `npm --prefix ui run test` | `Test Files 37 passed` · `Tests 906 passed` |
| 빌드 | `npm --prefix ui run build` | `✓ built in 388ms` |
| 린트 | `uv run ruff check` / `ruff format --check` (바뀐 서버 파일) | `All checks passed!` / `already formatted` |
| 콘솔 번호 하드코딩 0 | `grep -nE '\b(300\|30\|31)\b' server/design/beat_grid_send.py` | 매치 0(exit 1) |

증거 원문: `.moai/state/verify/t563/{pytest.txt,pytest2.txt,vitest.txt,build.txt}`(gitignore 대상이라 숫자를 여기 옮겨 적음).

## 4. 안 잰 것 (Gaps)

- **실기 콘솔 왕복 0회**: 전부 가짜 콘솔이다.
- **타임코드 번호 판정 갈래(없음·점유·모름)의 전용 시험이 없다**: `_resolve_beat_grid_timecode_number`는 `timecode_slot_verdict`를 그대로 부르지만, 세 갈래를 각각 쏘는 시험은 이번에 추가되지 않았다.
- **뮤테이션 확인은 하지 않았다**: "거절이면 0줄" 시험을 일부러 깨뜨려 실패하는지까지는 보지 않았다.
- **같은 줄이 여러 큐에 반복되는 묶음**(예: `ClearAll`): 기존 `run_commands`의 중복 실행 방지가 두 번째부터를 `skipped_already_executed`로 처리할 수 있다. 공용 인프라의 기존 동작이고, 시험 fixture는 큐 하나짜리라 이 경우를 쏘지 않았다. 이 경우 승인=송신 대조가 "승인했는데 안 보낸 줄"로 잡을 것으로 보지만 재보지 않았다.

## 5. 남은 위험 · 리드에게

1. **미리보기 승인**: `Goto Cue … Sequence N`/`Off Sequence N`은 시퀀스 참조라, 게이트 자체가 호출마다 시퀀스 내용을 다시 확인한다(`classify.py`·`expand.py`, 기존 panel Goto와 같은 길). 그래서 `PreviewApprovalSession`이 다스리는 건 "이 세션이 1회 승인 사유를 붙이느냐"까지이고, 게이트가 매번 다시 물을 수는 있다. REQ-012(b) "세션 1회"가 실제 화면에서 지켜지는지는 실기에서 봐야 한다.
2. **반영할 때마다 새 시퀀스 번호**: 매번 빈 번호를 새로 고르므로, 다시 반영하면 이전 시퀀스는 남고 새 시퀀스가 생긴다. 타임코드는 이미 쓰인 번호면 거절된다 — 즉 두 번째 반영은 지금 구조로는 타임코드 단계에서 막힌다. 곡 큐 경로도 같은 성질이다. "다시 반영 = 덮어쓰기"를 어떻게 할지는 별도 결정이 필요하다.
3. `unsent_cells`·반영 기록·미리보기 승인은 세션 메모리에만 있다. 다시 연결하면 `null`로 돌아간다(저장 안 함).
4. 파이썬 `BeatGridView` TypedDict(`beat_grid.py`)에는 `unsent_cells`를 넣지 않고 세션 층에서 붙인다(`draft` 키와 같은 방식). 그 모듈은 콘솔·세션을 모르게 둔다는 기존 원칙 때문이다.
5. 반영 실패 문구는 "승인 거절·게이트 차단·콘솔 무응답 중 하나" + 결과 내용으로 바꿨다. 원래 문구는 모든 실패를 "감독이 거절"로 단정했다.
