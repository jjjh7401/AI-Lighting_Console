# t593 run 판정 — 새 효과 프리셋을 반영 묶음에서 콘솔에 만든다 (SPEC-LDBEAT-001 REQ-015(i-4)(i-7)(i-8), plan M13)

- 카드: t593 · lane-2 · 브랜치 `WT-fx-preset-create` · 기준 origin/main `f8d7a8a9`, 뒤에 `1c8e4647`(t600 #637) 합침
- 콘솔 쓰기 0 · 콘솔 접촉 0(가짜 콘솔만) · 곡 리터럴·그룹 이름 규칙 0
- 범위(리드 회신 2026-10-12): 서버 + 시험만. 레시피를 채우는 입력 화면은 범위 밖.

## 무엇이 바뀌었나

- 새 모듈 `server/design/beat_grid_effect_presets.py`(순수 함수):
  - 저장 자리 `preset_fx_recipes{"22.n": {fx_id, period_unit, period_value}}` — `record_effect_preset_recipe`·`effect_preset_recipe`. 주기는 박·마디만 받는다(초 거절).
  - 이름은 t589·t592 와 같은 `preset_labels["22.n"]`(`app_preset_label`).
  - `effect_preset_outcomes(grid, numbers, library, policy, bpm, beats_per_bar)` — 번호마다 만들기 줄 또는 (None, 보류 사유).
    - 템플릿 = 출하 fx 라이브러리(`server/fx/library/*.yaml`)의 `fx_id`.
    - 속도 = 곡 BPM ÷ 한 주기 박 수(`server/design/app_movement.py` 선례). 템플릿의 `speed` 는 쓰지 않는다.
    - 줄 = `build_fx_preset_bundle(…, group, preset_pool, preset, label)`: `ChangeDestination Root` → `ClearAll` → `Group n` → 페이저 줄 → `Store Preset p.s '이름' /Universal` → `Label Preset p.s '이름'` → `ClearAll`(실기 선례 꼴 그대로, 새 문형 0).
  - `effect_grid_blocker` — 콘솔 없이 격자만으로 아는 걸림돌(빈 프리셋 표식이 씀).
- 공용 칸 판정 **`plan_cells(held, outcomes)`** — `server/design/beat_grid_position_presets.py` (리드 요청: 이름·자리 기록)
  - t592 `plan_position_preset_creation` 안에 있던 칸 판정을 빼냈다. 키는 (필드, 번호), 값은 만들기 줄 또는 사유.
  - 후보 = 「풀은 읽혔고 slot 이 없다」(`EMPTY_PRESET_HOLD`)로 보류된 항목 중 `outcomes` 에 있는 것뿐 — 이 입구가 덮어쓰기 0 의 근거다(@MX:ANCHOR 를 이 함수로 옮김).
  - 결과 `PositionPresetPlan`(별칭 `PresetCreationPlan`)에 `creation_fields{번호: 필드}` 추가 — 승인 카드가 위치·효과 문구를 가른다.
  - `plan_position_preset_creation` 은 위치 번호만 넣어 `plan_cells` 를 부르는 얇은 함수가 됐다(t592 시험 그대로 통과).
  - 같은 칸에 새 위치 번호 + 새 효과 번호가 같이 있으면 이제 **함께** 판정된다(전에는 효과 번호가 걸림돌이 되어 칸 통째로 보류).
- `server/web/session.py`
  - `_beat_grid_plan_position_presets` → **`_beat_grid_plan_new_presets(grid, held, timeline)`**: 위치 후보가 있을 때만 소속·장비 좌표를 읽고(t592 그대로), 효과는 격자 레시피·fx 라이브러리·`build_song_timing_from_bar_map`(에미터와 같은 BPM 출처)만 쓴다(콘솔 판독 0). 칸 판정은 `plan_cells` 한 번.
  - 승인 카드: 「새로 만드는 효과 프리셋 K개(콘솔 풀에서 빈 번호 확인): 22.1 'LA Wave' ← sweep-soft-wide · 2박 주기 · Group 7」.
  - 효과 만들기 줄이 같은 묶음의 큐 줄과 겹치면 반영 전체를 멈춘다(명령 0줄, 사유에 t601).
  - 만든 효과 번호도 t595 「있음」 추정에 들어간다(`_beat_grid_note_created_presets` 는 creations 전부를 받는다).
- `server/design/beat_grid.py` `empty_preset_cells` — 빈 효과 번호도 격자 조건이 다 있으면 `create_on_apply`(`EFFECT_CREATE_ON_APPLY`), 아니면 사유를 붙인다(t595 위치와 같은 방식, t600 이후라 승인 여부 무관).

## 보류 사유 (승인 카드·표식에 그대로 나간다)

| 상황 | 사유 |
|---|---|
| 레시피 없음 | `효과 프리셋 레시피(템플릿·주기)가 없음` |
| 템플릿 id 없음 | `효과 템플릿을 라이브러리에서 찾지 못함` |
| 어느 효과 번호대에도 없음 | `효과 번호대(preset_pools.yaml) 밖의 번호` |
| 디머 효과 대역(1.21~·1.31~) | `디머 효과 프리셋은 만들기 범위 밖(REQ-LDBEAT-015(i-6))` |
| 위치 효과 대역에 Pan/Tilt 아닌 템플릿, 색 효과 대역에 Color 아닌 템플릿 | `효과 템플릿 속성이 이 번호대 종류와 맞지 않음` (mixed 22 는 무엇이든) |
| 이름 없음 / 영문 규칙 위반 | `효과 프리셋 콘솔 이름(영문)이 없음` / `…영문·숫자 규칙에 맞지 않음` |
| 그 번호를 가리키는 트랙 중 그룹 미확인(i-8) | `트랙 그룹 번호 미확인 — 선택을 만들 수 없음`(t592 와 같은 글자) |
| 그룹 번호가 둘 이상 | `여러 그룹이 같은 효과 번호를 씀 — 여러 그룹 선택으로 만드는 꼴은 실기 선례 없음` → **t596 항목 요청** |
| 곡 BPM(마디 주기면 박자표)이 없음 | `곡 BPM·박자가 없어 주기를 속도로 바꿀 수 없음` |
| 같은 반영 묶음의 다른 효과와 줄이 겹침 | `… 다음 반영에서 만듦(송신 중복 제거, 카드 t601)` |

## 송신 중복 제거 — 재현 근거 (리드 요청, 결함 자체는 카드 t601, 이 PR 에서 안 고침)

- 건너뛰는 자리: `server/orchestrator/tools.py:2532` — `elif command in already_executed and not _is_programmer_state(command):` → `status="skipped_already_executed"`. `already_executed` 는 같은 지시 안에서 성공한 줄과 **같은 묶음 안 앞줄**까지 담는다(`:2521`, `:2549`).
- 면제 목록: `server/orchestrator/tools.py:1117` `_PROGRAMMER_STATE_COMMANDS`(`Clear`·`ClearAll`·선택 줄·선택+값 줄). 맨 `Step 2`, 맨 `Attribute 'Pan' At -30` 같은 선택 없는 값 줄은 **면제가 아니다**.
- 겹치는 줄을 내는 곳: `server/fx/instantiate.py:462` `_step_lines` 의 `lines.append(f"Step {index + 1}")` — 모든 효과 묶음이 `Step 2` 를 낸다. 저장소가 이미 적어 둔 사실: `server/fx/library/movement.yaml` 머리 주석 「every pattern emits the same step-transition line, so two instantiations in one instruction turn collide」, `server/fx/instantiate.py:802`.
- 결과: 효과 둘을 한 묶음에 실으면 두 번째 묶음의 `Step 2`(와 같은 값 줄)가 건너뛰어지고, `Store Preset` 은 그대로 ok — 빈(스텝 하나뿐인) 효과가 저장된다. 이 카드는 그래서 반영당 효과 1개로 막았다(`effect_preset_outcomes`, 시험 `TestOnlyOneEffectPerBatch`·`test_two_new_effects_send_only_one_store`).

## 검증

- RED: 시험 파일을 먼저 쓰고 `uv run pytest -q server/tests/test_effect_preset_create_t593.py` → 수집 오류(모듈 없음).
- GREEN: 같은 명령 → `40 passed`.
- 뮤테이션(합친 트리에서, 각각 되돌린 뒤 `grep -rc MUTATION server/design server/web` → 0줄):
  - A `plan_cells` 입구에서 `hold_reason == EMPTY_PRESET_HOLD` 검사 빼기 → `1 failed, 39 passed`. **처음엔 이 뮤테이션이 살아남았다**(38 passed) — 시험·세션 모두 넘기기 전에 이미 빈 slot 번호만 골라 넘겨서, 입구 검사가 빠져도 티가 안 났다. 입구를 직접 두드리는 시험 `test_plan_cells_own_entrance_refuses_a_non_empty_hold` 를 더해 잡았다.
  - B 반영당 1개(겹침 검사) 끄기 → `2 failed` · C 속도를 템플릿 값 그대로 → `2 failed` · D 표식의 효과 갈래 끄기 → `2 failed` · E 큐 줄 겹침 가드 끄기 → `1 failed` · F 디머 대역 보류 끄기 → `1 failed`.
- 관련 묶음(t577·t589·t590·t592·t593·t595·t600) → `164 passed`(합친 뒤, 승인된 칸 시험 추가 전).
- 서버 전체(합친 트리): `uv run pytest -q -p no:cacheprovider -rf server` → `15477 passed, 35 skipped, 1 warning in 222.03s`, `FAILED` 0(`server-pytest.log`). 합치기 전 첫 전체 실행에서 `test_new_preset_dialog_t589.py::…test_risk_reason_carries_label_description_and_the_console_creation_note` 1 failed — 원인은 이 카드: 아래 「바뀐 문구」.
- `uv run ruff check server .moai` → `All checks passed!` · `ruff format --check server` → `815 files already formatted`.

## 바뀐 문구 (기존 시험 2곳 기대값 수정)

- 빈 효과 번호의 항목 사유가 일반 문구 `빈 프리셋 — 아직 콘솔에 만들 길 없음` 에서 **못 만드는 까닭**(예: `효과 프리셋 레시피(템플릿·주기)가 없음`)으로 구체화됐다. 머리말 `빈 프리셋 — 아직 콘솔에 만들 길 없음(송신 보류) K개` 는 그대로다. t592 위치 번호가 이미 이렇게 동작한다.
  - `test_new_preset_dialog_t589.py`: `2.61 'LA Wave' — 따뜻한 흰색(효과 프리셋 레시피(템플릿·주기)가 없음)`.
  - `test_empty_preset_mark_t595.py`: 표식 사유 `빈 프리셋 — 아직 콘솔에 만들 길 없음(효과 프리셋 레시피(템플릿·주기)가 없음)`.

## t600 과 합친 자리 (늦게 합친 쪽이 풀기)

- 충돌 2곳: `beat_grid.py` `empty_preset_cells`(t600 이 「승인 대기 칸만」 제한을 없앰 → 효과 갈래도 승인 여부 무관으로 맞춤), `session.py` `beat_grid_apply` 앞부분(t600 의 `checked`·`approved` 구조 안에 `_beat_grid_plan_new_presets` 를 넣음).
- `plan_cells` 는 `released` 항목의 다른 키(`approved` 포함)를 그대로 두므로, 승인된 칸의 효과 번호는 만들어지되 승인 기록 대상에서는 빠진다. 시험 `test_approved_cell_empty_effect_is_created_too`.

## 안 잰 것 / 남은 위험

- **실기 콘솔 0회.** `/Universal` 효과 프리셋 꼴은 실기 선례가 있지만, 박자 격자 반영 묶음 안에서 큐 줄과 섞어 보내기, 주기→속도 환산이 무대에서 맞는 빠르기인지는 재지 않았다. t596 항목 후보: ① 섞어 보내기 ② 여러 그룹 선택(위 표).
- **입력 경로 없음**: `preset_fx_recipes` 를 채우는 화면이 없다. 지금은 저장된 곡 격자에 레시피가 들어 있어야 쓸 수 있다.
- **반영당 효과 하나**: 효과 번호가 여럿이면 반영을 여러 번 해야 다 만들어진다(t601 이 풀리면 넓힐 수 있음).
- 템플릿 속성과 그룹 장비의 실제 속성이 맞는지는 보지 않는다(번호대 종류와 템플릿 속성만 대조). 장비에 없는 속성이면 콘솔이 그 값을 담지 않을 수 있다.
- 판독~송신 시간차(덮어쓰기 창)는 t590·t592 와 같은 구멍이다.
- `preset_pools.yaml` 은 아직 `confirmed: false` — 번호대 종류 판정도 잠정 번호대 기준이다.
