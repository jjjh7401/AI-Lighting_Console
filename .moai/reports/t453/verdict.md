# t453 판정서 — 흰색 큐는 콘솔 컬러 프리셋을 이름으로 불러 W 를 켠다

- 카드: t453 · SPEC-LDDESIGN-001 · 브랜치 `WT-white-preset-ref` · 기준 `fa8192d7` (origin/main)
- 감독 결정(2026-09-27, 리드 배차로 전달): 흰색은 앱이 RGBW 숫자를 박지 않고 콘솔 컬러 프리셋을 이름으로 참조한다(P3 차가운 흰색·P2 따뜻한 흰색, t232 포지션 방식).
- 콘솔 쓰기: **0**. 콘솔 읽기: **0**. 라벨은 기존 판독 기록에서 가져왔다.
- 범위: 감독 확정 곡 큐 경로(t430 의 E1, `_reviewed_song_commands`)만. E2~E7 은 건드리지 않았다.

## 1. 전제 — 라벨은 판독값이다

- 감독이 말한 P2·P3 은 **슬롯 번호가 아니라 정본 시트 ID**다. 콘솔 컬러 풀 슬롯 2 는 「핫 핑크 (=P4)」다.
- 콘솔 컬러 풀 4 판독(`.moai/reports/t469/run3_phaser_pools.txt` 9행, 2026-09-27 14:24 커밋): 슬롯 7 `웜 화이트 (=P2)` · 슬롯 8 `뉴트럴 화이트 (=P3)`.
- 2026-09-01 판독(`t225/evidence/console-pool-census.md`)에는 이 둘이 없었다. 그 뒤 콘솔에 올라갔다.
- 시트 이름은 「뉴트럴 화이트」, 감독이 t442 에서 쓴 말은 「차가운 흰색」이다. 표준 팔레트의 `Cool White` 에 이 라벨을 붙였다.

## 2. 무엇이 바뀌었나 (`server/web/session.py`)

| 자리 | 변화 |
|---|---|
| `_WHITE_PRESET_LABELS` | `Warm White` → `웜 화이트 (=P2)`, `Cool White` → `뉴트럴 화이트 (=P3)`. 슬롯 번호는 적지 않는다 |
| `_white_palette_name` | 구간 큐 주색이 표준 팔레트 흰색 둘 중 하나인지(RGB 로 대조) |
| `_white_preset_slots` (새 메서드) | 컬러 풀 번호를 이름 "Color" 로 해석하고(`_resolve_named_pool_no`), 풀을 한 번 판독해(`_paged_pool_children`) 라벨로 슬롯을 찾는다. `#n` 접미 무시. 없음·여러 슬롯·판독 실패는 사유 문자열 |
| `_song_color_value_lines` | 네 번째 인자 `white_presets`. 흰색 큐의 **W 기구에만** 오늘 줄(RGB + `W At 0`) 뒤에 `Fixture <W 기구> ; At Preset 4.<슬롯>` 한 줄을 붙인다. 사유가 오면 프리셋 줄 없이 오늘 줄 + 사유. `None` 이면 t430 동작 그대로 |
| `_reviewed_song_commands` | 흰색 큐가 있고 W 기구가 있을 때만 `_white_preset_slots` 를 부른다 |

설계 이유:

- **뒤에 붙인다.** 콘솔은 뒤에 온 값을 쓰므로 프리셋의 RGBW 가 이긴다. 프리셋에 값이 저장되지 않은 기구는 앞 줄의 RGB 흰색을 그대로 받는다. 프리셋만 보냈다면 그런 기구는 앞 큐의 색(예: 파랑)을 그대로 들고 있었을 것이다.
- **W 기구에만 부른다.** 다음 큐의 W 기구 줄은 t430 이후 늘 `W At 0` 을 적는다. 그래서 프리셋이 켠 W 가 다음 색으로 새지 않는다. W 판독이 안 된 기구(판별 불가)에는 프리셋을 부르지 않는다. 불렀다면 다음 큐에서 W 를 끌 줄이 없다.
- **흰색이 없는 곡은 판독 순서까지 같다.** 기존 골든 판독 순서 시험이 그대로 통과한다.

`server/tests/test_song_cue_color_emission.py` 의 대역 람다 한 곳은 네 번째 인자를 받도록 고쳤다. t430 때 같은 이유로 세 번째 인자를 더한 자리다.

## 3. 증거

| 항목 | 명령 | 결과 | 파일 |
|---|---|---|---|
| RED | `uv run pytest -q server/tests/test_song_cue_white_preset_t453.py` (구현 전) | 12 failed, 2 passed | `red_before_fix.txt` |
| 새 시험 | 같은 파일 | 15 passed | — |
| 경계 | `TestRealReadPath` — 진짜 `_resolve_named_pool_no`·`_paged_pool_children`·`_white_preset_slots` 에 t469 응답 모양을 태움 | `{Warm White: (4,7), Cool White: (4,8)}`, 조회 2회(풀 목록 → 풀 4) | — |
| 범위 시험 | `uv run pytest -q server/tests -k "session or song or color or colour or preset or writegate or write_dispatch or cue_sheet or concept or gates"` | 3200 passed, 25 skipped | `pytest_scoped.txt` |
| 8곡 게이트 | `uv run python .moai/reports/t444/gen_gates_8songs.py` | PASS 75 · n/a 29 · FAIL 0 | `gates_after.txt` |
| 변이 ① 프리셋 줄 삭제 | `lines.append(_preset_recall_command(...))` 제거 | 3 failed | `mutation_no_recall.txt` |
| 변이 ② 라벨 변경 | `뉴트럴 화이트 (=P3)` → `뉴트럴 화이트` | 5 failed | `mutation_label.txt` |
| 린트 | `ruff check` / `ruff format --check` (바뀐 파일 3개) | exit 0 / exit 0 | `ruff_check.txt` · `ruff_format.txt` |

8곡 게이트는 컨셉 계층(`server/concept/`)만 보고, 이 변경은 세션의 명령 생성기에 있다. 게이트가 그대로인 것은 예상된 결과이며, 이 변경을 검증한 것은 아니다.

## 4. 안 잰 것

- **프리셋 내용.** P2·P3 에 어느 기구의 값이 저장돼 있는지, Rush Par 같은 다른 W 기종에도 값이 있는지 읽지 않았다(콘솔 읽기 0). 값이 없는 기구는 앞 줄의 RGB 흰색을 받는다는 것은 설계 의도일 뿐, 콘솔에서 확인하지는 않았다.
- **값이 없는 기구에 `At Preset` 을 걸었을 때 콘솔이 오류를 내는지.** 페이저 recall 이 같은 모양(`Fixture <전체> ; At Preset <풀>.<슬롯>`)으로 실기에서 쓰이고 있다는 점이 근거의 전부다.
- **저장된 큐가 프리셋 참조를 보존하는지, 값으로 평탄화하는지.** 페이저와 같은 잔여 가정이다(`_PHASER_REVIEW_ASSUMPTION_NOTE`).
- 실기 콘솔 발사, 화면 확인은 하지 않았다.
- **맨 「흰색/화이트/하양」(t409 경계)은 바꾸지 않았다.** 어느 흰색으로 풀지 결정이 배차에 없어서 리드에게 물었다. 답을 받기 전이라 지금처럼 미해소로 둔다.
- E2~E7(컬러 프리셋 번들·컬러 페이저·프리셋 저장·오버라이드 룩·큐시트 적용·룩 스키마)은 흰색을 여전히 RGB 로 낸다.
- 전체 시험 모음(11340개 선택 해제분)은 CI 에 맡긴다.

## 5. 남은 위험

- 콘솔에서 라벨을 바꾸면(예: `(=P3)` 를 지우면) 프리셋을 못 찾고 RGB 로 돌아간다. 이때 사유가 곡 반영 회신의 「색 미반영」 줄에 나온다.
- 곡을 반영할 때 흰색 큐가 있으면 콘솔 읽기가 2회 늘어난다.
