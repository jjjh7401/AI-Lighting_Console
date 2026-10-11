# 카드 t555 — 박자 격자 밝기 기본값 100% run-verdict

기준 `6402ae03`(origin/main, PR #602 포함). 브랜치 `WT-beatgrid-bright-default`. 콘솔 접촉 0건.
감독 결정 2026-10-11(리드 경유): 「밝기 값이 명확하지 않으면 우선 100% 진행해」.
리드 판단 2026-10-11: 아래 분류 (A)/(B) 확정, 근거 기록 방식 확정, SPEC 개정은 t554 머지 뒤.

## 바꾼 칸 전수 (16칸 — `server/design/beat_grid_data/love_attack.yaml`)

전부 `brightness: {mode: value, value_percent: 100}`. 100 은 데이터에만 있고 코드 상수는 0건
(`grep -rn '\b100\b' server/design/beat_grid*.py server/design/app_movement.py` → 주석 밖 0건).

| 트랙 | 마디 | 라벨(§4 원문) | 근거 기록 |
|---|---|---|---|
| SIDE-ALL | 11 | SIDE-L/R 2·4박 번갈이 | 기존 2026-10-10 승인 유지(proposal-table #14) + YAML 주석 |
| SIDE-ALL | 14 | 가속(마디마다 두 배) | 기존 2026-10-10 승인 유지(#15) + YAML 주석 |
| MOVER-U | 0 | 바닥 쪽 좁은 빔, 정지 | evidence.approval {supervisor, 2026-10-11, 카드 t555} |
| MOVER-U | 3 | 5마디 1박 위치 한 칸 올림 | 같음 |
| MOVER-U | 7 | 정지 | 같음 |
| MOVER-U | 11 | 기울인 자리에서 느린 팬 흔들기 | 같음 |
| MOVER-U | 14 | 가속 스윕 4박→2박→1박→반 박 | 기존 2026-10-10 승인 유지(#22) + YAML 주석 |
| MOVER-U | 18 | 18마디 위로 열고 19마디부터 팬 웨이브 | 기존 2026-10-10 승인 유지(#23) + YAML 주석 |
| MOVER-U | 22 | 22마디 1박에 멈춰 섬 | evidence.approval {supervisor, 2026-10-11, 카드 t555} |
| MOVER-D | 0 | 바닥 쪽, 정지 | 같음 |
| MOVER-D | 3 | 5마디 1박 위치 한 칸 올림 | 같음 |
| MOVER-D | 7 | 틸트 웨이브, 한 바퀴 2마디, 위상 펼침 | 같음 |
| MOVER-D | 11 | 11마디 1박 새 자리, 정지 | 같음 |
| MOVER-D | 14 | U 와 같은 스윕 | 기존 2026-10-10 승인 유지(#29) + YAML 주석 |
| MOVER-D | 18 | 위로 연 자리, 정지 | 기존 2026-10-10 승인 유지(#30) + YAML 주석 |
| MOVER-D | 22 | 22마디부터 틸트 웨이브(한 바퀴 2박) | evidence.approval {supervisor, 2026-10-11, 카드 t555} |

새 승인 10칸은 `evidence.grade: null`(증거 강도는 해당 없음 — 감독 결정이지 측정이 아니다).
`source_ref` 는 16칸 모두 비어 있다(§4 인용 전용 필드 — 이 값은 §4 출처가 아니다).

t553 발견 해소: MOVER-D 트랙에 brightness 가 0칸이라 열린 7·22 무빙이 디머를 안 냈다 →
이제 7칸 전부 값이 있어 `brightness_value_commands` 가 Dimmer(+Dimmer2, 호출자가 넘기면)를 낸다.

## 채우지 않은 칸 (9칸 — 값이 명확)

| 트랙 | 마디 | 이유 |
|---|---|---|
| BACK | 11, 14 | §4 「—」 — §4:100 「「—」는 그 시퀀스가 쉰다는 뜻」 |
| SIDE-ALL | 0, 3, 7, 18, 22 | 같음(쉼) |
| BACK | 0, 3 | **감독 결정 대기** — §4 SCENE 열 「BACK 차가운 실루엣 30%」(0~2)·「그대로」(3~6). 값 30 이 있는데 `scene_memos` 로만 남아 칸에는 안 옮겨졌다. 30 을 칸에 옮길지 리드가 감독에게 올린다. |

§4 숫자가 있던 칸(BACK 7·18·22, WASH-ALL 7·14, BLIND 18)과 디머 프리셋 칸(FOH 7, BLIND 17)은
그대로다(`test_no_other_brightness_changed`).

## 시험

- RED(데이터 고치기 전): `uv run --quiet pytest server/tests/test_beat_grid_bright_default_t555.py -q`
  → `2 failed, 2 passed`(실패: `test_sixteen_unclear_cells_get_value_100`,
  `test_new_approvals_name_this_card_and_prior_approvals_are_untouched` — 통과 둘은 「안 바뀔 칸」 확인).
- GREEN 뒤 기존 시험 하나가 옛 기대로 실패: `test_beat_grid_t537.py::test_every_other_cue_has_no_value_percent_and_no_source_ref`
  (`assert 100 is None`) — 날짜 붙은 대체 고지 주석과 함께 16칸은 100, 나머지는 None 으로 고쳤다(삭제 아님).
- 최종: `uv run --quiet pytest server/tests/test_beat_grid_bright_default_t555.py server/tests/test_beat_grid_t532.py server/tests/test_beat_grid_t537.py server/tests/test_beat_grid_t548.py server/tests/test_beat_grid_probes_t537.py server/tests/test_beat_grid_emit_t549.py server/tests/test_beat_grid_measured_t553.py server/tests/test_beat_grid_timecode_cap_t553.py server/tests/test_app_movement_t548.py server/tests/test_position_fx.py -q`
  → `222 passed`. `ruff check`/`format --check` 통과.
- UI 시험(`ui/src/components/BeatGrid.test.tsx`)은 자체 손 픽스처를 써서 YAML 과 무관(읽음, 실행 안 함).

## 갭 · 남은 일

- **기계 필드 없음**: 2026-10-10 승인이 있던 6칸은 칸당 승인 필드가 하나라 밝기 100 의 근거가
  YAML 주석과 이 표에만 있다(리드 판단 — 스키마 확장 안 함).
- **SPEC 충돌 → 해소(2026-10-11)**: t554 브랜치(`origin/WT-ldbeat-ui-design` 9cfc1783)를 합친 위에
  REQ-LDBEAT-006(i-6a) 예외 조항 + (i-7)에 「(i-6a) 우선」 + AC-LDBEAT-016(f) 기대표(33칸: §4 전사 6 /
  기본 100 16 — 새 승인 10·기존 승인 6 / null 11 — 휴지 7·디머 프리셋 2·BACK 0·3 2) + §5 열린 결정 10항.
  델타 plan-audit PASS 0.92(`.moai/reports/plan-audit/SPEC-LDBEAT-001-t555-delta.md`) — D1·D2 반영, D3(선택,
  (vii-1) 목적 문구 일반화) 미반영.
- **PR #604** — CI 초록. 머지는 리드가 t554 먼저 합친 뒤 한다(레인은 머지 안 함). 워크트리
  `.claude/worktrees/t555` 는 머지 전까지 지우지 않는다.

### 넘기는 남은 일

1. **BACK 0·3 의 30%** — §4 SCENE 열 값 30 을 칸에 옮길지: 감독 질문으로 넘어감(SPEC §5 열린 결정 10항). 지금은 비어 있다.
2. **기계 필드 없음 6칸** — 위 갭. 고치려면 밝기 전용 근거 필드(스키마 확장)가 필요 — 리드 판단으로 하지 않음.
3. **AC-016(e)/REQ-015(f) 「프리셋 번호 필드 전부 null」 낡은 문구** — t543/t548 이후 실제와 다름(FOH 1.1·BLIND 1.6·BACK 21.1 등). 새 카드 t556(이 카드에서 손대지 않음).
4. **델타 감사 D3(선택)** — (vii-1) `evidence` 목적 문구를 밝기 근거까지 일반화.
- 안 잰 것: 콘솔에서 100% 가 실제로 어떻게 보이는지(이 카드는 데이터만), 전체 테스트 스위트(CI 가 돌림).

## 재개 (2026-10-11) — 합친 CI 빨강: 칸 승인이 새 프리셋 번호를 통과시킨 구멍

리드 배차: 합친 head `edc14dfc`(main `aa327785` + 이 브랜치) CI run 38112994889 에서 1건 실패.

### 원인 (잰 것)

- 실패: `server/tests/test_beat_grid_edit_t551.py:586`
  `test_new_effect_preset_number_without_approval_is_rejected` — 기대 사유 REQ-LDBEAT-015, 실제 사유
  「app_movement 축 ['Pan']과 effect_preset_no … (REQ-LDBEAT-006(vi-7))」.
- 로컬 재현: `.venv/bin/python -m pytest -q server/tests/test_beat_grid_edit_t551.py` → `1 failed, 43 passed`(같은 시험).
- 그 칸(MOVER-U 11마디)의 현재 값을 읽음: t555 가 붙인 `evidence.approval {supervisor, 2026-10-11, 카드 t555 …}` 가
  있다. `apply_beat_grid_edit` 는 기존 칸과 changes 를 합친 `merged` 로 `check_evidence_approval` 을 불렀기 때문에,
  **밝기 100% 승인이 새 효과 번호의 승인으로 재사용**돼 REQ-015 검사를 통과하고, 그다음 축 겹침에서 걸렸다.
  t555 이전에는 그 칸에 승인이 없어 REQ-015 에서 먼저 걸렸다 — 두 브랜치 각각은 초록, 합치면 빨강.
- 원인 확인(증상 아님): 축 겹침과 무관한 칸(MOVER-U 3·MOVER-D 3 — t555 승인 있음, app_movement 없음)에서
  새 효과 번호 2.65 / 디머 프리셋 1.22 를 승인 없이 넣으면 **거절 없이 들어갔다** — 아래 재현 시험 2건이
  `DID NOT RAISE` 로 실패(`2 failed, 5 passed`). 축 겹침이 가리고 있던 실제 구멍이다.

### 고친 것 (감독 선택 2026-10-11: 이번 changes 의 승인만 인정)

- `server/design/beat_grid_edit.py` — 새 `effect_preset_no` / 디머 `preset_no` 의 REQ-015 검사를
  `merged` 대신 `fresh_approval_cue` 로 한다: changes 에 `evidence` 가 있으면 그대로, 없으면 `evidence=None`.
  칸에 이미 있던 승인은 쓰지 않는다. 데이터·승인 스키마 변경 0.
- 재현 시험 3건 추가 — `server/tests/test_beat_grid_bright_default_t555.py`:
  칸 밝기 승인으로 새 효과 번호 거절 / 새 디머 번호 거절 / changes 에 승인을 함께 보내면 통과.
- 옛 동작을 기대하던 시험 1건 정정 — `server/tests/test_session_beat_grid_edit_t551.py`
  `test_effect_name_resolves_and_derives_effect_kind_from_the_matched_pool`: MOVER-U 14 의 기존 승인(t543, 번호 21.5)으로
  새 번호 2.61 을 문장 경로에서 쓰던 것을 기대했다. 이름→번호 해석은 해석기를 직접 불러 그대로 확인하고
  (2.61·position), 쓰기는 REQ-015 거절 + 격자 무변경을 기대하도록 고쳤다.

### 결과

- `.venv/bin/python -m pytest -q server/tests/test_beat_grid_bright_default_t555.py server/tests/test_beat_grid_edit_t551.py`
  → `51 passed`.
- 전체: `.venv/bin/python -m pytest -q -rs` → exit 0, `15075 passed, 35 skipped`(로그는 gitignore 된
  `.moai/reports/t555/pytest-full-fix.log`, 로컬에만).
- `ruff check` / `ruff format --check`(바꾼 파일 3개) 통과.

### 알릴 결과 (리드 판단 필요)

- **문장 경로는 이제 효과·디머 프리셋 번호를 쓸 수 없다.** 문장 파서는 `evidence` 를 싣지 못하므로
  (`server/web/session.py` `beat_grid_edit`), 「14마디 MOVER-U 효과를 LA Sweep 2로」 같은 문장은 이름 해석은 되지만
  REQ-015 로 거절된다. 감독 선택의 직접 결과이며, 문장으로 새 번호를 넣으려면 승인을 싣는 길이 따로 있어야 한다.
- 안 잰 것: UI 직접 고르기 경로가 changes 에 `evidence.approval` 을 실제로 함께 보내는지(서버 쪽만 고침),
  vitest(서버 변경이라 CI 가 돌림).
