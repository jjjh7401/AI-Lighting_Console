# t590 run 판정 — 빈 프리셋 송신 보류(가드 D) + SPEC 0.5.2

브랜치 `WT-new-preset-store` · 기준 origin/main `eb63ec17` · 콘솔 접촉 0건 · 곡 리터럴 0건

## 범위(리드 결정 2026-10-11)
- ① 가드 D: 새 번호를 가리키는데 만들 값이 없는 칸 → 반영 승인 카드에서 송신 보류 + 표시, 승인=송신 대조에서 빠지는지 시험.
- ② SPEC 개정(manager-spec): REQ-LDBEAT-015(i-1)~(i-8), AC-LDBEAT-016(w-1)~(w-5), plan M11~M14 — 커밋 `f4bb3609`.
- 구현 A(종류별 레시피)는 이 카드 밖: 위치 t592 → 효과 t593 → 색 t594. 디머는 범위 밖(i-6).

## 실측 — 고치기 전 동작 (가짜 콘솔, t577 하네스)
- 승인 대기 칸(`effect_preset_no` 4.21, 승인 없음)의 반영 묶음: `Store Timecode 20`·`Set Timecode …`·`Store Sequence 1`·`Set Sequence 1 Property 'Name' …`·`Assign Sequence 1 At Timecode 20` — **그 칸의 큐 줄은 0줄**(에미터 `_emit_cue` 가 `check_evidence_approval` 로 막음).
- 그런데 승인 카드는 그 번호를 「새로 만드는 프리셋 1개」로 열거하고, 승인 뒤 그 칸에 `evidence.approval` 을 적는다 → **다음** 반영에서 그 칸이 빈 번호를 가리킨 채 나간다. (두 번째 반영은 가짜 콘솔이 소유권 재확인에서 막혀 직접 재지 못했다 — 코드 판독 추론)

## 변경
- `server/design/beat_grid.py`: `split_empty_preset_holds(pending, pool_slots)` — 승인 대기 열거를 (승인 기록 대상, 보류)로 가른다. slot 없음 → 「빈 프리셋 — 아직 콘솔에 만들 길 없음」, 풀 못 읽음 → 「풀을 못 읽어 빈 프리셋인지 확인 못 함」, `pool.slot` 꼴 아님 → 보류. **칸 단위**(같은 칸의 다른 번호는 「같은 칸에 보류 번호가 있어 함께 보류」). 상수 `EMPTY_PRESET_HOLD`·`POOL_UNREAD_HOLD`·`CELL_HOLD`, `preset_pool_no`.
- `server/web/session.py` `beat_grid_apply`: `pending_preset_approvals` 직후 `_beat_grid_split_empty_presets` 로 풀 번호마다 한 번 `_paged_pool_children` 판독(콘솔 **읽기**만) → 보류 칸은 승인 기록 대상에서 빠지고, 승인 카드에 「빈 프리셋 — 아직 콘솔에 만들 길 없음(송신 보류) K개: …(사유)」를 따로 단다.
- `server/tests/test_apply_time_approval_t577.py` 픽스처: 가짜 콘솔에 `DataPool/PresetPools/4` (slot 21) 추가 — 4.21 이 「이미 있는 프리셋」이라는 t577 시험의 원래 뜻을 명시. 없으면 새 가드가 「못 읽음 → 보류」로 바꾼다.

## 검증
- RED: `pytest server/tests/test_empty_preset_hold_t590.py` → 수집 오류(`split_empty_preset_holds` 없음).
- GREEN: `pytest test_empty_preset_hold_t590.py test_apply_time_approval_t577.py` → `22 passed`.
- 뮤테이션(가드 끔: `held_presets = []`) → `4 failed, 9 passed` — (w-1) 표시·승인 미기록, (w-2), (w-4) 가 가드를 잡는다. 되돌린 뒤 `grep -c MUTATION session.py` → 0.
- 묶음: `pytest test_beat_grid_*.py test_web_beat_grid_*.py test_apply_time_approval_t577.py test_empty_preset_hold_t590.py test_approval_vs_sent_t549.py test_send_approval_t549.py test_session_beat_grid_edit_t551.py test_messages_beat_grid_t551.py test_app_movement_t548.py` → `521 passed`.
- `pytest test_prechk_tool.py test_write_dispatch_census.py` → `86 passed, 1 skipped`.
- `ruff check`(바뀐 4파일) → `All checks passed!` · `ruff format` 적용.

## 안 잰 것 / 남은 위험
- 「명령 0줄」(w-1)·「승인=송신 일치」(w-5) 시험은 **가드가 없어도 통과한다** — 승인 없는 칸은 원래 그 묶음에서 빠지기 때문. 가드의 실제 효과(승인 미기록 → 다음 반영에서도 안 나감)는 「승인 기록 없음·승인 대기 유지」 시험이 잡는다. 두 번째 반영까지 이어지는 시험은 가짜 콘솔이 소유권 재확인을 못 해 쓰지 않았다.
- 실기 콘솔에서 반영 시 풀 판독(`DataPool/PresetPools/<n>`)이 실제로 읽히는지 재지 않았다(콘솔 0). 못 읽으면 모든 승인 대기 칸이 보류된다 — 이미 있는 쇼 프리셋을 고른 칸도.
- 이미 **승인된** 칸이 빈 번호를 가리키는 경우는 이 가드 범위 밖(새 번호=승인 대기만).
- UI 쪽 표시는 승인 카드 문구(risk reason)뿐 — 격자 칸 자체에 「빈 프리셋」 표식은 넣지 않았다.
