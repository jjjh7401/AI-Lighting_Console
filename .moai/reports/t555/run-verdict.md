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
- **SPEC 충돌**: REQ-LDBEAT-006(i-6)(숫자 없는 칸 채움 금지)·AC-LDBEAT-016(f)(26칸 value_percent null 기대)와
  어긋난다. 예외 조항 「감독 결정 2026-10-11 — 밝기 불명확 칸 기본 100%」 추가와 기대표 갱신은
  lane-1 t554 가 같은 spec.md/acceptance.md 를 고치고 main 에 들어간 뒤 그 위에 하고, plan-audit(델타)까지.
  그 전까지 PR 은 열지 않는다(리드 지시).
- 안 잰 것: 콘솔에서 100% 가 실제로 어떻게 보이는지(이 카드는 데이터만), 전체 테스트 스위트.
