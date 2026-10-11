# t592 run 판정 — 새 위치 프리셋을 반영 묶음에서 콘솔에 만든다 (SPEC-LDBEAT-001 REQ-015(i-3)(i-7)(i-8), M12)

- 카드: t592 · lane-1 · 브랜치 `WT-console-pos-presets` · 기준 origin/main `56b994b4`
- 콘솔 쓰기 0 · 콘솔 접촉 0(가짜 콘솔만) · 곡 리터럴·그룹 이름 규칙 0
- 범위(리드 회신 2026-10-11): 서버 + 시험만. 「＋ 새 프리셋 만들기」 창의 위치 종류(목표 X·Y·Z 입력, 번호대 막힘 해제)는 t589 머지 뒤 후속.

## 무엇이 바뀌었나

- 새 모듈 `server/design/beat_grid_position_presets.py`(순수 함수):
  - 저장 자리 `preset_targets{"2.n": {x,y,z}}` — `record_position_preset_target`·`position_preset_target`. 위치 풀(2) 번호와 유한한 수 셋만 받는다.
  - 이름은 t589 와 같은 `preset_labels{"2.n": 이름}` 을 읽는다(같은 키·모양).
  - `plan_position_preset_creation(grid, held, members, frames)` — t590 이 보류한 항목 중 **「풀은 읽혔고 slot 이 없다」(`EMPTY_PRESET_HOLD`)인 위치 번호만** 후보로 본다. 좌표·이름·그룹 번호 확인·소속 전수·장비 좌표 전수·전 장비 조준 가능이 모두 있으면 만들기 줄을 짠다. 하나라도 빠지면 사유를 단 채 보류한다.
  - 만들기 줄은 t474 run3 실기 선례와 같은 꼴: `Fixture n ; Attribute 'Pan' At p ; Attribute 'Tilt' At t` → `Store Preset 2.n` → `Label Preset 2.n '이름'` → `ClearAll`. 조준 값은 `server/spatial/pointing.py`(실측 모델)의 `aim_pan_tilt`, 줄은 `aimed_commands`·`position_preset_store_commands` 를 그대로 쓴다(새 문형 0).
  - 칸 단위(t590 과 같다): 다른 종류의 빈 번호나 못 읽은 풀이 섞인 칸은 통째로 보류하고, 그 칸의 위치 번호는 만들지 않는다. 같은 번호를 여러 트랙이 가리키면 그 소속 전부를 한 프리셋에 담고, 그중 하나라도 빠지면 그 번호를 가리키는 칸 전부를 보류한다.
- `server/web/session.py` `beat_grid_apply`: t590 분류 바로 뒤에 계획을 세운다(후보가 있을 때만 그룹 소속·장비 좌표를 **읽는다**). 만들 수 있는 칸은 승인 기록 대상으로 돌아가고, 만들기 줄은 묶음 **맨 앞**에 붙는다(끝의 `ClearAll` 뒤에 에미터 큐 줄). 승인 카드에 「새로 만드는 위치 프리셋 K개(콘솔 풀에서 빈 번호 확인): 2.n '이름' → (x, y, z) 장비 N대 조준」.

## 보류 사유 (승인 카드에 그대로 나간다)

| 상황 | 사유 |
|---|---|
| 풀 못 읽음 | `풀을 못 읽어 빈 프리셋인지 확인 못 함` (t590 그대로, 만들기 0) |
| 목표 좌표 없음 | `위치 프리셋 목표 좌표가 없음` |
| 이름 없음 / 영문 규칙 위반 | `위치 프리셋 콘솔 이름(영문)이 없음` / `…영문·숫자 규칙에 맞지 않음` |
| 그룹 번호 미확인(i-8) | `트랙 그룹 번호 미확인 — 선택을 만들 수 없음` |
| 소속·좌표 일부만 읽힘 | `트랙 그룹 소속을 다 읽지 못함` / `장비 좌표를 다 읽지 못함` |
| 틸트 한계·겹침·Rotx/Roty | `목표를 조준할 수 없는 장비가 있음(FID …)` — 일부 장비만 담은 프리셋을 만들지 않는다 |

## 검증

- RED: `uv run pytest -q server/tests/test_position_preset_create_t592.py` → `ModuleNotFoundError: No module named 'server.design.beat_grid_position_presets'`(수집 오류).
- GREEN: 같은 명령 → `33 passed in 0.41s`.
- 덮어쓰기 0 잠금 뮤테이션: 후보 술어를 `hold_reason != "MUTATION"`(못 읽은 풀·같은 칸 보류도 후보로)으로 바꾸면 → `2 failed, 31 passed`(`test_unreadable_pool_never_creates`, `test_cell_hold_entry_alone_never_creates`). 되돌린 뒤 `grep -c MUTATION` → `0`. 세션 쪽 시험은 이 뮤테이션에서도 통과했다 — 세션이 후보를 한 번 더 거르기 때문(이중 방어).
- 관련 묶음: `pytest test_position_preset_create_t592.py test_empty_preset_hold_t590.py test_apply_time_approval_t577.py` → `55 passed`.
- 서버 전체: `uv run pytest -q -p no:cacheprovider server` → `15367 passed, 35 skipped, 1 warning in 273.54s`.
- `uv run ruff check`(바뀐 3파일) → `All checks passed!` · `ruff format --check` → `3 files already formatted`.

## 실기 선례 (리드 요청 「선례 없으면 t582 에」)

- 꼴 자체는 선례가 있다: t474 run3(`.moai/reports/t474/run3_presets_write/approval_request_1.txt`) — 조준 줄 → `Store Preset 2.21` → `Label Preset 2.21 'Home'` → `ClearAll`, 실제 콘솔에서 10/10 실행.
- 선례가 없는 것: **박자 격자 반영 묶음 안에서 큐 줄과 섞어 보내기**. 리드가 t582 에 항목으로 넣기로 했다(2026-10-11 회신 ①).
- 한 묶음 안 같은 글자 건너뛰기(dedupe): 조준 줄·`ClearAll` 은 프로그래머 상태 줄로 면제(`server/fx/instantiate.py` `_PROGRAMMER_STATE_COMMANDS`), `Store`·`Label` 은 번호마다 글자가 달라 프리셋 여러 개가 한 묶음에 있어도 겹치지 않는다(코드 판독, 실측 아님).

## 합칠 때 정리할 자리 (리드 회신 ②)

- 이름 읽기 함수가 둘이다: 이 카드의 `beat_grid_position_presets._preset_label` 과 t589 의 `beat_grid_presets.app_preset_label`(같은 `preset_labels` 키·모양). 늦게 합치는 쪽이 하나로 합친다 — 자리에 `TODO(t589 머지 뒤)` 주석을 달아 두었다.
- t589 브랜치를 main(t590 포함)과 합쳐 보니 `session.py` 승인 카드 문구 한 곳이 충돌하고, t589 시험 2개(`TestApprovalCardShowsLabelAndDescription`)가 t590 보류 규칙 때문에 떨어졌다 — t589 레인이 main 을 합칠 때 풀 몫이라 이 브랜치는 t589 를 합치지 않았다.

## 안 잰 것 / 남은 위험

- **실기 콘솔 0회**. 섞어 보내기, 만든 프리셋을 다음 반영에서 큐가 부르는 왕복은 가짜 콘솔에서도 두 번째 반영까지는 재지 않았다(t590 과 같은 이유 — 소유권 재확인).
- **입력 경로 없음**: `preset_targets` 를 채우는 화면이 아직 없다(리드 결정 — t589 창 후속). 지금 이 기능을 실제로 쓰려면 저장된 곡 격자에 좌표·이름이 들어 있어야 한다.
- 판독과 송신 사이 시간차: 풀은 반영 버튼을 누른 순간 읽고, Store 는 감독 승인 뒤 나간다. 승인 창이 떠 있는 동안 누가 콘솔에서 그 번호를 채우면 덮어쓴다(t590 판독과 같은 창).
- 그룹 소속은 무대 판독(`read_beat_grid_stage`)에서 `complete` 인 그룹만 쓴다 — 응답기 길이 상한으로 잘린 그룹은 「소속을 다 읽지 못함」으로 보류된다(안전 쪽).
- 같은 번호를 여러 트랙이 쓰고 그중 일부 칸만 이번에 승인 대기인 경우, 이미 승인된 칸의 트랙 소속은 프리셋에 담기지 않는다(후보 칸의 트랙만 모은다).
