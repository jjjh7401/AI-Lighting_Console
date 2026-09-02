# t228 — 전부 아니면 아무것도의 **입도를 배치에서 큐로** 내렸다

base `origin/main` `83661d8` · 브랜치 `WT-cue-granularity` · 콘솔 쓰기 **0건**(응답기 사망)

## 한 줄

아침 판정(큐 안 원자성)은 그대로 두고, t207 이 그것을 **배치** 층에 놓은 것만
되돌렸다. 정본 CSV 재현으로 계획되는 큐가 **0 → 5** 가 됐고, 프리셋을 다 채운
반사실에서는 **0 → 16** 이다.

## 정본 `:272` 읽기 — 배차서가 요구한 검증

`src/Lighting_Designer/01_스펙/LX-SEQ-SPEC-v2.1.md:272` 는 §11.1 「열 규격(17열)」
표의 **1행**이고 문면은 이렇다:

    | 1 | `Q#` | CUE 시트 Q#와 일치 (부분집합 금지 — 모든 큐에 최소 1행) |

주어가 **입력 CUE-EX 시트의 `Q#` 열**이고, 규정하는 것은 그 시트가 CUE 시트의
부분집합이면 안 된다 — 즉 **입력의 완전성**이다. 콘솔에 무엇이 닿는지는 이
조항의 정의역이 아니다. 저장소는 이미 그 읽기대로 구현돼 있다:
`cue_mapper.CUE_COVERAGE_GAP` 이 「선언된 큐 중 행이 없는 것이 있으면 배치 거절」
을 하고, 그 거절 사유 문자열이 `§11.1` 을 인용한다.

같은 조항을 **출하 층에 한 번 더** 적용한 것이 t207 이었다. 리드의 읽기가 맞고,
배치 층 적용은 과잉 적용이다.

🔴 **그렇다고 큐 안의 원자성이 근거를 잃지는 않는다.** 그쪽은 `:272` 가 아니라
아침 판정의 **트래킹 논거**에 서 있다 — 한 그룹이 빠진 큐는 MA3 가 트래킹하므로
큐 리스트에서 정상으로 보이고 발사할 때에야 어긋나고, 되읽기 채널이 큐 내용을
안 주므로(`AC-LXSEQ4-013`) 사후 탐지 수단이 없다. 근거가 서로 다른 두 규율이
한 조항에 묶여 있었던 것이 이 오적용의 기전이다.

## 무엇이 나가나 — 정본 CSV 오프라인 재현

t225 의 `replay_join.py` 를 그대로 복사해(`evidence/replay_join_t228.py`,
콘솔 접촉 0) 이 브랜치에서 다시 돌렸다. 슬롯표는 t225 가 실측한 값 그대로다.

| 프리셋 상태 | 전 행 해결된 큐 | 계획되는 큐 **전** | 계획되는 큐 **후** | 빠지는 큐 |
|---|---|---|---|---|
| 지금 | 5 | **0** (`rows_held`) | **5** — Q010·Q030·Q060·Q170·Q180 | 13 |
| FX 4종을 채웠다면 | 7 | **0** | **7** (+Q100·Q120) | 11 |
| FX+BM+COL.02 를 다 채웠다면 | 16 | **0** | **16** | 2 — Q140·Q150 |

「계획되는 큐 후」가 t225 의 「전 행 해결된 큐」 열과 세 값 다 일치한다 — 즉 이
변경이 여는 것은 **정확히 t225 가 잰 그만큼**이고 더도 덜도 아니다.
마지막 행의 잔여 둘(Q140·Q150)이 `FX.04`(Hue)·`FX.06`(Shutter)이며, 이 카드에서
고치지 않았다(별건).

- 전: `.moai/reports/t225/evidence/replay_join.json`
- 후: `.moai/reports/t228/evidence/replay_join_after.json`

## 부분 출하의 대가를 어떻게 갚았나

콘솔이 시트의 **일부**를 든 상태가 새로 생겼고, 되읽기 채널은 큐 내용을 안 준다
(`AC-LXSEQ4-013`). 그래서 **툴 산출물이 유일한 기록**이다. 산출물에 실린 것:

| 칸 | 내용 |
|---|---|
| `planned_cues` | 나간 큐 (기존) |
| `cues_held` | 빠진 큐 — `cue_no` · `held_rows` · `withheld_rows` · `classes` · `preset_refs` |
| `cues_held_count` · `partial_ship` | 상태의 이름 |
| `notice_partial_ship` | 「콘솔이 일부만 든다」 + 재실행 안내 |
| `ApprovalRequest.risk_reasons` | 승인 화면이 부분 출하임을 말한다 |

- `withheld_rows` 는 **해석은 됐는데 그 큐가 빠져서 함께 안 나간** 행 수다. 이
  칸이 없으면 「Q020 이 안 갔다」는 알아도 「그래서 성한 KEY 행도 안 갔다」는
  모른다 — 콘솔 상태가 다르다. 뮤턴트 M4 가 이 칸을 지키는 검사를 확인했다.
- `preset_refs` 는 **병렬 어휘를 만들지 않았다.** t225 의
  `unresolved_preset_refs`(`ref`/`kind`/`cause`/`expected_console_name`) 표에
  `ref` 로 조인되어 원인과 기대 콘솔 이름까지 간다. 검사
  `test_the_held_refs_join_to_the_cause_table` 이 그 조인이 실제로 서는 것을 잰다.

**하네스 산출물**(`server/tools/lxseq_cues_e2e.py --out`, 부분 출하의 durable
기록): `cues_readback` 의 기대치가 이제 **둘**이다. 시트 기준
(`expected`/`matches_expected`, 원래 값 보존)과 계획 기준
(`expected_planned`/`expected_after`/`matches_after`)에 `partial_ship`·`cues_held`
를 함께 적는다. 시트 기준만 두면 정상적인 부분 출하가 「불일치」로 읽히고,
계획 기준만 두면 「시트의 몇 개가 안 갔나」가 사라진다.

**멱등성**: 부분 출하 뒤 재실행은 시퀀스 층(`already_present`)과 큐 층
(`cues_already_present`) 그대로다 — 이미 올라간 큐는 다시 계획하지 않고, 보류된
큐는 여전히 보류다. 매퍼·툴 양쪽에 검사를 뒀다.

## `refusal` 의 소비자 — 전수

`rows_held` 를 저장소 전체에서 세면 14곳이고, **검사·문서를 뺀 생산/소비 지점은
셋뿐**이다.

| 소비자 | 전 | 후 |
|---|---|---|
| `cue_mapper.map_cues` (생산) | 보류 1행 → `rows_held` | **성한 큐가 하나도 없을 때만** `rows_held` |
| `tools.py:6013` apply 게이트 (`if result.refusal is not None or not cue_bundles`) | 보류가 있으면 항상 여기서 멈춤 | 부분 출하면 `refusal=None` 이라 통과 → 성한 큐만 승인 요청·전송 |
| `cue_mapper.block_report` (AC-014 3분류) | `ROWS_HELD` 는 건너뛰고 보류 사유별로 (A)/(B)/(C) | **바뀌지 않음** — `result.held` 를 보므로 거절 여부와 무관하다 |
| 모델(LLM)이 읽는 payload | `refusal=rows_held` 하나 | `refusal=None` + `partial_ship=true` + `notice_partial_ship` |

`server/lxseq/preset_mapper.py`·`group_mapper.py`·`web/session.py` 의 `refusal` 은
**다른 타입의 같은 이름 필드**다(형제 매퍼·세션 응답) — 이 변경과 무관하다.
UI·문서에는 `rows_held` 소비 지점이 없다(`grep -rn rows_held .` 전수, 위 표 밖은
전부 `server/tests/` 와 `.moai/specs/`).

## 검증

### 회귀

| | 통과 | 스킵 |
|---|---|---|
| `83661d8` (자체 venv, 이 트리) | 10,805 | 12 |
| 이 브랜치 | **10,819** | 12 |

**+14 = 새로 넣은 검사 14개**(매퍼 6 + 툴 8). 지운 검사 0.
검사 **2개는 이름/입력이 바뀌었지 수는 안 바뀌었다**:
`test_the_refusal_names_which_cue_which_row_and_why`(입력을 전량 보류로 옮김 —
배치 거절 사유 문면 계약을 살리려고) ·
`test_a_cue_emptied_by_hold_still_refuses_everything` →
`..._ships_nothing_for_that_cue`(이름 세 번째 세대). 전량 설명된다.
(`uv sync --group dev` 로 이 트리 자체 venv 를 세우고 쟀다 — 규약 §1)

### 재현 우선

`test_a_held_row_holds_its_cue_and_only_its_cue` 가 이 카드의 빨강이다. 고치기
전 실행: `AssertionError: assert [] == ['Q010']` — Q020 의 한 행이 안 풀려 성한
Q010 까지 안 나갔다. 새 검사 6개가 전부 빨갛게 뜬 것을 먼저 확인하고 고쳤다
(`evidence/red-before-fix.txt`).

### 뮤테이션 — 6/6 사망

`diff` 로 「적용 안 됨」을 기계 확인했고(스크립트가 `mutated != original` 을
단언한다) 여섯 번 다 적용됐다.

| # | 치환 | 죽은 검사 |
|---|---|---|
| **M1** | 배치 거절로 되돌린다 (`if held:`) | 8개 — `test_a_cue_emptied_by_hold_ships_nothing_for_that_cue` 외 |
| **M2** | 보류된 큐를 부분 출하시킨다 (planned 필터에서 `held_cue_names` 제거) | 2개 — `test_a_held_cue_ships_zero_rows_not_the_healthy_ones` 포함 |
| M3 | 보류로 빈 큐를 `video_only_cues` 로 오분류 | `test_a_held_cue_is_not_reported_as_video_only` |
| M4 | `withheld_rows` 를 항상 0 으로 | `test_the_held_cue_record_names_the_cause_and_the_rows_it_took_down` |
| M5 | `partial_ship` 을 항상 False 로 | `test_a_held_cue_does_not_stop_the_healthy_one` |
| M6 | 보류 큐의 `preset_refs` 를 비운다 | `test_the_output_names_the_held_cue_its_rows_and_its_refs` |

**M1·M2 가 배차서가 지정한 두 뮤턴트다** — 배치 거절로 되돌리는 것과 부분 큐를
통과시키는 것. 둘 다 죽었고, M2 를 죽인 검사에 아침 판정을 지키는
`..._ships_zero_rows_not_the_healthy_ones` 가 들어 있다.

M3 이 하중을 진다: 입도가 내려온 뒤로 「보류로 비어 버린 큐」와 「영상만 있는 큐」가
`rows_by_cue` 가 비었다는 **같은 술어**에 걸린다. 전에는 `assert not held` 가
그 갈래를 원천 차단했고, 그 assert 를 지우면서 새로 열린 구멍이다.

### 대조군 두 팔

- **팔 1 — 새 검사가 잡는가**: 위 뮤테이션 6/6.
- **팔 2 — 기존 상태에서는 못 잡는가**:
  `test_every_cue_held_still_refuses_the_whole_batch`(배치 거절이 아직 사는가) ·
  `test_every_cue_healthy_is_not_a_partial_ship`(성한 시트를 부분 출하로 안 부르는가) ·
  `test_every_cue_held_is_a_batch_refusal_not_a_partial_ship`(전량 보류에서 콘솔
  전송 0건). 그리고 6개 새 검사는 `cues_held` 필드 자체가 없던 기존 소스에서는
  `AttributeError` 로 수집조차 안 된다.

## 안 잰 것 (Gaps)

- **콘솔에 아무것도 안 썼다.** 배차서대로 응답기는 죽어 있고 onPC 를 재시작하지
  않았다. 부분 출하가 **실기에서** 나가는 것은 못 봤다 — 오프라인 재현과 가짜
  상태 포트까지다.
- **감사로그(`server/safety/audit.py`, JSONL 90일)가 부분 출하의 두 번째 durable
  기록**이지만, 실제 apply 를 안 돌려 그 로그에 `Store Cue` 가 어떻게 남는지는
  **이 회차에서 안 쟀다.** 소스상 게이트 이벤트 단위로 명령 문자열이 남으므로
  「어느 큐가 실제로 나갔나」는 그쪽에서도 답이 나올 것으로 읽히나, **읽은 것이지
  잰 것이 아니다.**
- **`cue_manual_notes`·`per_row_timing` 은 안 건드렸다** — 부분 출하와 직교하지만
  대조를 안 돌렸다.
- **`FX.04`/`FX.06` 도 프리셋 생성도 안 했다**(별건, 배차서 지시).
- **여러 큐가 서로 다른 사유로 보류될 때의 산출물 크기**는 안 쟀다. 정본 재현에서
  `cues_held` 13개까지 나오는데, 그 payload 가 모델 컨텍스트에서 얼마나 무거운지는
  측정하지 않았다.
- **`matches_expected`(시트 기준)를 그대로 둔 것이 옳은지**는 판단이지 측정이
  아니다. 부분 출하가 정상인 세상에서 그 값이 상시 False 가 되어 「경보 피로」를
  만들 수 있다. 지금은 `matches_after` 를 나란히 두는 쪽을 택했다.

## 컨텍스트

`.moai/state/context-usage.json` 은 이 트리에서 다른 세션 값을 들고 있을 수 있어
읽지 않았다(규약 §9). **카드 수 축**: 이 세션 **1장째**.
