# t477 — 반영 전 콘솔 풀 판독으로 포지션·페이저 이름 → 풀 번호 (lane-1)

- 브랜치 `WT-preset-name-resolve` · 기준 `origin/main@fa8192d7` · 구현 커밋 `01781a32`
- 근거 카드: t469 §6 후속 제안(`.moai/reports/t469/verdict.md`, 9587a41a)
- 리드 조건: **콘솔 접속 금지**(lane-2 t474 가 콘솔을 쓰는 중). 풀 판독은 t469 실기 캡처를 옮긴 가짜 콘솔로 시험. 실기 확인은 §5 「안 잰 것」
- 판정: 🟢 **코드 경로 PASS (가짜 콘솔)** · 실기 미확인

## 0. 무엇이 바뀌었나

| 경우 | 전 (t469) | 후 (t477) |
|---|---|---|
| 초안 포지션에 번호(`2.<n>`) 있음 | 보냄 | 그대로 보냄. **풀을 읽지 않는다** |
| 초안 포지션에 이름만 있음 (`POS05`) | 사유 달고 건너뜀 | 반영 직전 Position 풀(2)을 읽어 `2.5`를 채우고 `At Preset 2.5`로 보냄 |
| 초안 페이저에 이름만 있음 (`DIM-BREATHE`) | 사유 달고 건너뜀 | `All 1`·`Dimmer`·`Color` 풀을 **이름으로** 해석해 읽고, `21.4`를 채워 `At Preset 21.4`로 보냄 |
| 풀에 없는 이름 (`Breathe Soft`) | 건너뜀 | 건너뜀. 메모: 「콘솔 풀 1·4·21에서 그 이름의 프리셋을 찾지 못했습니다(번호를 지어내지 않습니다)」 |
| 같은 이름이 둘 이상 | — | 건너뜀. 후보 번호를 적고 「특정할 수 없습니다」 |
| 풀을 못 읽음 | — | 건너뜀. 사유는 「못 읽음」으로, 「없음」과 다른 문장 |
| 조도만 고친 반영 | 풀 판독 0 | 풀 판독 0 (시험으로 고정) |

찾은 경우에는 반영 메모에 **어떤 프리셋이 불렸는지** 콘솔 이름 그대로 적는다. 예: `· 큐 20 포지션 'POS05' → 콘솔 프리셋 2.5 'POS05 팬아웃 종점 (객석 상단) · 합성좌표' (이름 첫 낱말 일치, 풀 판독).`

### 매칭 규칙: 공용 함수는 한 곳

`server/design/preset_names.py`의 `match_preset_name` / `match_preset_name_across_pools`(순수 함수, 콘솔 없음)

1. **정확한 이름**: `#n` 접미를 뗀 베이스이름이 같다. t232 규칙 그대로다
2. **이름 첫 낱말**(`leading_token=True`일 때만): 정확한 이름이 하나도 없을 때 콘솔 이름의 첫 낱말이 같다(대소문자 무시). 실기 포지션 이름이 `POS05 팬아웃 종점 (객석 상단) · 합성좌표`처럼 길어서 필요하다(t469 run2 캡처). 이름 중간 낱말이나 부분 문자열로는 찾지 않는다(시험 `test_a_description_word_does_not_match`)
3. 여러 풀을 볼 때 한 풀이라도 못 읽으면, 다른 풀에서 찾았더라도 거부한다(모름 ≠ 없음)

`ChatSession._resolve_position_preset_labels`(t232)도 이 함수를 타게 바꿨다. 문면과 동작은 같고, t232 시험이 통과한다. **lane-3 t453**(컬러 프리셋 이름 참조)은 이 모듈을 가져다 쓰면 된다. 컬러 풀 이름이 `웜 화이트 (=P2)` 모양이라 첫 낱말 규칙이 맞는지는 t453이 판단한다.

## 1. 코드 변경

| 파일 | 변경 |
|---|---|
| `server/design/preset_names.py` (신규) | 매칭 순수 함수 2개, 이유 코드 `absent`·`ambiguous`·`pool_unread` |
| `server/web/session.py` | `_resolve_draft_preset_names`: 바뀐 큐 중 **이전과 다른 이름**이고 **번호 칸이 비어 있는** 포지션·페이저만 판독한다. 번호는 `target` 사본에만 채우고, 초안 자체는 감독이 적은 그대로 둔다. `_cue_sheet_draft_apply`에서 계획 직전에 부른다 · `_resolve_position_preset_labels`가 공용 함수를 탄다 |
| `server/design/cue_sheet_apply.py` | `_phaser_recall`: `phaser_preset_no`(`<풀>.<n>`)가 있으면 포지션 뒤에 `; <선택> ; At Preset <풀>.<n>`을 붙인다. 번호가 없으면 기존 `UNSOURCED_FIELD_REASONS["phaser"]` 사유(문구만 갱신) · 곡 전체 반영(`previous=None`)의 페이저 이름은 건드리지 않는다 · 포지션 무번호 사유 문구 갱신 · `CONSOLE_APPLIABLE_FIELDS`에 `phaser_preset_no` 추가 |
| `server/tests/fixtures/console/t469_preset_pools.json` (신규) | t469 run2·run3의 `<<<` 회신을 **값 그대로** 옮김(`extract_pools.py`로 재생성 가능) |
| `server/tests/test_preset_name_resolve_t477.py` (신규) | 29건: 순수 함수 13 · 계획기 7 · 세션(가짜 콘솔) 9 |

## 2. 증거

| 확인 | 명령 | 결과 |
|---|---|---|
| RED | `uv run pytest server/tests/test_preset_name_resolve_t477.py -q` (순수 모듈만 있고 세션·계획기 변경 전) | `7 failed, 22 passed` — `pytest_red.txt`. 통과한 22건은 순수 함수 13건 + 변경 전에도 참인 「안 보낸다」 쪽 |
| GREEN | 같은 명령 (`01781a32`) | `29 passed` — `pytest_green.txt` |
| 관련 묶음 | `uv run pytest -q -p no:randomly server/tests -k "cue_sheet or preflight or draft or apply or web_session or session or preset or t469 or t466 or t232 or writegate or dispatch_census"` | `2116 passed, 23 skipped` — `pytest_affected.txt` |
| 린트 | `ruff check` · `ruff format --check` (고친 파일 전부) | 통과 |
| 뮤테이션 | 아래 4종, 각각 되돌림 | 전부 FAIL로 잡힘 |

| 뮤테이션 | 결과 |
|---|---|
| M1 세션에서 판독 호출 제거 | 5 failed |
| M2 포지션 판독의 첫 낱말 규칙 끔 | 2 failed |
| M3 계획기가 페이저 줄을 붙이지 않음 | 3 failed |
| M4 여러 풀 판독에서 「못 읽은 풀」 무시 | 1 failed |

## 3. 콘솔 쓰기

**0건.** 이 카드는 콘솔에 접속하지 않았다(리드 조건). 가짜 콘솔 시험 `test_the_lookup_reads_but_never_writes_the_pool`은 판독 경로가 `Store/Label/Delete Preset`을 한 줄도 내지 않는다는 것만 잰다. 다만 이 시험은 변경 전에도 통과한다. 판독은 `query_state`(읽기)만 쓰는 구조라서 시험보다 코드 구조가 더 강한 보증이다.

## 4. 판정 근거로 쓴 실측 (재측정 아님)

- 풀 번호 = 회신 `i`: t469 run5·run7·run11 캡처에서 `At Preset 2.5` → `POS05`, `At Preset 21.4` → `DIM-B…`. 이 카드의 매칭 결과(`POS05`→5, `DIM-BREATHE`→4)가 같은 번호를 낸다
- 풀 21 = `All 1`, 풀 1 = `Dimmer`, 풀 4 = `Color`: t469 run2 풀 목록 회신

## 5. 안 잰 것 (Gaps)

- **실기 콘솔 판독**: 이 코드가 실제 onPC 응답기에 `query_state`를 보내 같은 결과를 받는지는 쏘지 않았다(콘솔 접속 금지). 가짜 콘솔은 t469 캡처 회신을 그대로 돌려줄 뿐, 응답기의 페이징(`offset`)은 흉내 내지 않는다. 캡처 풀은 전부 24개 미만이라 페이징이 일어나지 않는다
- **포지션+페이저를 한 값 줄에 같이 싣기**: `… ; At Preset 2.5 ; Group 11 ; At Preset 21.4` 한 줄을 실기에서 쏜 적이 없다. t469는 둘을 각각 따로만 쐈다
- **페이저 recall이 현재 선택 기구에 값을 싣는가**: t469 run5는 Q4에서 `21.4`가 실린 것을 캡처했다. 다른 그룹(초안의 `fixture_groups`)에도 값이 있는지는 프리셋마다 다르다. 값이 없으면 콘솔은 OK를 주고 아무것도 싣지 않는다(t469 §1 「조용히 넘어가는 두 가지」 2번). 반영 메모에 번호와 이름을 적어 감독이 확인하게 했다
- **실제 `run_commands` 승인 경로**: 가짜 콘솔 + 실제 `SafetyGate`·`ApprovalChannel`로 쐈다(자동 승인). 실기 LiveLock은 시험하지 않았다
- **첫 낱말 규칙의 오탐**: 감독이 풀의 다른 프리셋 이름 첫 낱말과 우연히 같은 말을 적으면, 그 프리셋 하나가 불린다. 메모에 콘솔 이름을 보이는 것 말고는 막지 않는다
- **Dimmer·Color 풀의 정적 프리셋**: 페이저 칸에 `미드` 같은 정적 조도 프리셋 이름을 적으면 그대로 불린다. 페이저인지 판별하지 않는다
- **UI**: 채운 번호는 초안(`store.latest`)에 쓰지 않는다. 타임라인 화면에는 이름만 보이고, 번호는 반영 메모에서만 보인다

## 6. 후속 제안

- t474(실기 1곡) 뒤에 1회 실기 판독: `POS05` → `2.5`, `DIM-BREATHE` → `21.4` 반영을 가짜 시퀀스에서 되읽기로 확인하면 §5 첫 두 줄이 닫힌다
- t453은 `server/design/preset_names.py`를 재사용한다. 새 매칭 규칙을 만들지 않는다

실제 문면: `show_messages.txt` (`uv run python .moai/reports/t477/show_messages.py`)
