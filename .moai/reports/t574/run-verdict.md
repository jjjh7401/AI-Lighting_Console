# t574 run 판정서 — 전환 entry 확장 필드 저장·검증·편집 배선

- 카드: t574 (t566 후속)
- 범위: SPEC-LDBEAT-001 0.5.0 — REQ-LDBEAT-006(i-4a)~(i-4f) · REQ-LDBEAT-020(e) · AC-LDBEAT-020 (f)~(k)
- 브랜치: `WT-entry-fields-run` (작업 트리 `.claude/worktrees/t574`), 기준 `d15ee0f5` (= origin/main, 착수 시 확인)
- 콘솔 접촉 0건. 새 WS 메시지 0건(기존 `beat_grid_edit` 의 `entry` 변경만).

## 1. 바뀐 것

| 파일 | 내용 |
|---|---|
| `server/design/beat_grid.py` | `BeatGridEntry` 에 `fade_beats`·`trigger_beat`·`delay_beats`·`position_late_beats`·`tracking` 추가, 정규화에서 없으면 `None`(미정) |
| `server/design/beat_grid_edit.py` | `_validate_entry` 확장 — 페이드 두 단위 배타(i-4a), 박 수 필드는 0 이상 정수, `trigger_beat` 는 1~마디당 박 수(i-4b), `tracking` 은 기존 `cue_sheet_edit.TRACKING_VALUES` 재사용(i-4e). `beats_per_bar_from_timeline` 신설(i-4f) — `timeline.time_signature`(`"3/4"`) 먼저, 없으면 `bar_map.time_signature`(`[n, d]`), 못 읽으면 `None`(4 하드코딩 없음). `apply_beat_grid_edit`·`apply_beat_grid_edit_range` 에 `beats_per_bar` 키워드 — 검증은 이 한 함수에서 |
| `server/web/session.py` | 편집 두 경로 모두 곡 박자표를 읽어 넘김 |
| `server/tests/test_beat_grid_t537.py` | 레거시 읽기 시험 2건의 기대 `entry` 모양을 0.5.0 으로(새 다섯 필드 `None`) — t548 이 필드를 더할 때와 같은 갱신 |
| `ui/src/protocol.ts` | `BeatGridEntry` 에 다섯 선택 필드 |
| `ui/src/components/beatGridTransition.ts` | `entryWith`(entry 전체 보존), `fadeDraftToEntry`(정수 마디면 `fade_bars`, 아니면 `fade_beats` — REQ-020(e)), `formatEntryFade`(「1.07초 (2박)」), `entryFadeIsCut`/`entryHasFade`/`entryFadeInBars`, `triggerSeconds`, `sceneEntryEdits`. 경고·이음매·콘솔 명령 미리보기가 박 페이드·트리거 박을 반영. 예전 `fadeDraftToBars`(정수 마디만) 는 SPEC 0.5.0 으로 대체돼 없앰 |
| `ui/src/components/BeatGridTransitionView.tsx` | t561 이 꺼 둔 트리거 박(1~박자표)·딜레이(박)·위치만 따로·트래킹을 켬. 선택은 바꾸는 즉시, 숫자 입력은 칸을 떠날 때/Enter 에 저장. 저장은 늘 entry 전체. [미확인]·⚠미확인 표기 유지 |
| `ui/src/components/BeatGridTimelineParts.tsx` | 이음매 위치가 트리거 박만큼 이동(시안 `.jt` 와 같은 식), 박 페이드 번짐·◢. 장면 전환 「모두 1박 페이드」 켬, 「모두 끊기」와 함께 `onBulkEntry`(줄마다 다른 entry 값 보존) |
| `ui/src/components/BeatGrid.tsx` | 마운트 세 곳에 `beatsPerBar`·`onBulkEntry` 전달 |

### 함께 고친 잠복 결함

서버는 `entry` 를 통째로 바꾼다(`{**base, **changes}`). 그런데 화면은 `{fade_bars, mib_mode}` 두 개만 보내고 있었다(t561 의 페이드 「적용」과 「모두 끊기」). 새 필드가 생기면 페이드 하나만 고쳐도 트리거 박·딜레이·트래킹이 **지워졌을** 것이다. 이제 모든 쓰기가 `entryWith` 로 entry 전체를 보낸다(시험: 「일괄 전환은 각 줄의 다른 entry 값을 보존한다」, 「entryWith 는 바꾼 필드 말고는 그대로」).

## 2. AC 대조

| AC | 판정 | 확인 방법 |
|---|---|---|
| AC-020(f) 페이드 두 단위 배타 | PASS | `test_one_fade_unit_is_accepted` · `test_both_fade_units_are_rejected`(사유에 `i-4a`) · `test_rejection_leaves_the_grid_untouched` |
| AC-020(g) `_seconds` 0건 | PASS | `test_no_seconds_field_in_entry_storage` — `BeatGridEntry` 키에 second 0, `_validate_entry` 소스에 `_seconds` 0 |
| AC-020(h) 트래킹 닫힌 집합 재사용 | PASS | `beat_grid_edit.TRACKING_VALUES is cue_sheet_edit.TRACKING_VALUES` + 집합 밖 거절 |
| AC-020(i) 트리거 박 범위 = 곡 박자표 | PASS | 4/4 에서 5 거절·4 수락, 3/4 에서 4 거절·3 수락 + 박자표 모르면 거절(지어내지 않음) + 범위 편집 경로 + 세션 경로(3/4 곡에서 4 거절, 3 저장) |
| AC-020(j) `fade_beats=1` 저장 | PASS | `test_one_beat_fade_is_storable` + UI 「모두 1박 페이드」 켜짐 렌더 시험 |
| AC-020(k) WASH-ALL@7 바이트 불변 | PASS | `git diff -- server/design/beat_grid_data/love_attack.yaml \| wc -l` → `0` (데이터 파일 무변경) + `test_missing_new_fields_normalize_to_none`(`fade_bars: 2` 그대로, 새 필드 `None`) |
| AC-020(e) 표시는 초 먼저 + 두 저장 필드 | PASS | `fadeDraftToEntry` 시험(8박→2마디, 2박→`fade_beats`, 3/4 에서 6박→2마디), `formatEntryFade` 시험 |

## 3. 증거 (이 트리)

| 명령 | 결과 | 파일 |
|---|---|---|
| `uv run pytest -q server/tests/test_beat_grid_entry_t574.py` (구현 전) | collection error(함수 없음) — RED | `red-1.txt` |
| 같은 명령 (구현 후) | `36 passed` | — |
| `npx vitest run src/components/beatGridTransition.test.ts src/components/BeatGridPanels.test.tsx` (구현 전) | `Tests 16 failed \| 57 passed` — RED | `red-2.txt` |
| `uv run pytest -q -k "beat_grid or ldbeat or prechk_tool" server/tests` | `457 passed` | `pytest-beatgrid.txt` |
| `npx tsc --noEmit -p ui` | exit 0 | `tsc.txt` |
| `npx vitest run --root ui` | `Tests 1075 passed (1075)` | `vitest.txt` |
| `ruff check` · `ruff format --check` (바꾼 파이썬 파일) | 통과 | — |
| 전체 pytest | 아래 §5 | `pytest-full.txt` |

## 4. 안 잰 것 · 남은 것

- **앱 화면 0회.** 컨트롤이 켜지고 저장 요청 모양이 맞는 것은 렌더 시험·순수 함수 시험으로만 봤다. 브라우저에서 고르고 서버 왕복 뒤 다시 그려지는 것은 안 봤다.
- **콘솔 송신은 그대로 없음.** 에미터(`beat_grid_emit.py`)는 지금도 `entry` 를 읽지 않는다 — 페이드·트리거 박·딜레이·트래킹 어느 것도 콘솔로 가지 않는다(이 카드 이전과 같음). 트래킹은 SPEC 대로 송신하지 않고, 딜레이·위치만 따로는 [미확인]/⚠미확인 그대로다. 페이드(CueFade)·트리거 박의 송신 배선은 별도 카드 감.
- 곡 타임라인에 박자표(`time_signature`·`bar_map.time_signature`)가 없으면 트리거 박은 화면에서 비활성이고 서버도 거절한다 — 의도한 동작(4를 지어내지 않음). 실제 곡(LOVE ATTACK 포함) 타임라인에 박자표가 실리는지는 이 카드에서 안 쟀다.
- 「위치만 따로」 화면 선택지는 시안 그대로 「같이 / 1박 늦게」 둘뿐이다(저장은 임의의 박 수를 받는다 — 그런 값이 오면 그 값도 선택지로 보인다).

## 5. 전체 pytest

`uv run pytest -q` → `15168 passed, 35 skipped` (실패 0, `pytest-full.txt`). 이 실행 뒤에 바뀐 것은 새 시험 파일의 `ruff format`(줄바꿈만, 내용 같음) 하나다 — 그 파일은 포맷 뒤 따로 다시 돌렸다(`36 passed`).
