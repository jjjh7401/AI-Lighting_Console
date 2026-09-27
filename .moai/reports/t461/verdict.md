# t461 판정서 — PLAN CUE 수정요청 생성기의 서버 선행 (SPEC-LDDESIGN-001 M7)

- 카드: t461 (클래스 C, t460에서 분리)
- 브랜치: `WT-parser-group-scope` · 기준 `origin/main` `6f89e9eb`
- 콘솔 쓰기: 0건 (가짜 콘솔과 계획 함수만 사용). 새 콘솔 쓰기 경로는 만들지 않았다.
- 커밋: `30bb0949`(① 문법) · `cfaf35c3`(⚠1 반영 분할, 별도 커밋) · `c2f6aec3`(② 리저브·잔여 그룹)

> **진행 상태 (2026-09-27, 세션 컨텍스트 한도로 인계):** ①·⚠1·②는 구현·시험·커밋을 마쳤고 브랜치를 푸시했다. ③은 하지 않기로 판단했다(아래 절). **남은 일:** (1) `origin/main` 합류 — 인계 시점에 main이 5커밋 앞서 있다(`git rev-list --left-right origin/main...HEAD` → `5 3`). (2) 합류 뒤 범위 시험 재실행(`scoped_dimmer.txt`·`scoped_step2.txt` 목록 + `test_concept_reserve_t461.py` + overlap 가드). (3) PR 생성 → CI 초록까지. PR은 아직 열지 않았다.

## ① 그룹 스코프 문법 (리드 승인)

`server/design/cue_sheet_edit.py`

- 문법: 큐 지시어 + 그룹 목록(라틴 이름, `· , + /` 와 `와 과 랑 하고`로 잇기) + (의/그룹) + 항목 + 값.
- 받는 그룹은 그 큐의 `intensity[].group`뿐이다(대소문자 무시). 이 경로에서는 KEY·BACK이다(`session.py`의 구간 필드가 이 둘만 만든다).
- 받는 예(시험으로 고정):
  1. `큐 3 BACK 밝기 70%로 바꿔줘` → BACK만 70, KEY는 그대로
  2. `KEY·BACK 95%` → 큐 전체 지정과 결과·보고가 같다
  3. `BACK 더 밝게` → BACK만 +20
  4. `BACK 컬러 앰버` → `palette_secondary`
  5. `KEY 컬러 레드` → `palette_primary`
  6. 큐를 고른 상태의 `BACK 밝기 50%` → 선택한 큐
- 거절(사유 문장):
  - a. 모르는 그룹 → 「큐 3에는 'FOH' 그룹이 없습니다 — 이 큐의 그룹: KEY, BACK. 그룹 이름을 지어내지 않습니다.」
  - b. 컬러를 여러 그룹에 지정
  - c. 큐 전체 값(페이드·무브먼트 등)에 그룹 지정
  - d. 그룹별 조도가 없는 큐에 그룹 지정
  - 거절은 쓰기 전에 난다(부분 적용 없음).
- **기존 문장 바이트 동일**: `server/tests/*.py`의 한국어 문자열 6,832개를 수정 전(`6f89e9eb`)에 `parse_cue_sheet_edit_request`(cue_selected 참·거짓)에 넣어 스냅샷을 떴다(`parse_corpus_base.json`). 수정 후 결과가 달라진 문장은 0개다(`parse_corpus_after_parser.json` 대조 → `changed 0`). 이 대조는 시험으로 고정했다(`test_existing_sentences_parse_exactly_as_before`).

## ⚠1 콘솔 반영의 그룹별 Dimmer (리드 판정 A)

`server/design/cue_sheet_apply.py` `_group_dimmer_overrides`. 기존 경로 `plan_cue_console_apply` 안에서만 바꿨다.

- 그룹 값이 서로 다르면, 최댓값 한 줄(기존과 같음) 뒤에 **낮은 그룹만** `Group n ; Attribute 'Dimmer' At v`로 덮는다(last-wins — `session._back_layer_value_lines`와 같은 방식).
- 모든 그룹 값이 같으면 아무것도 붙지 않는다 → 명령이 바이트 동일하다.
- 그룹 → 콘솔 번호는 기존 주소록(`layer_mapping`의 group_name·role, 정확 일치)으로만 푼다. 못 풀면 덮지 않고(한 값) 사유를 단다: 「그룹별 조도를 나눠 보내지 못했습니다 — 콘솔 그룹 번호를 모르는 그룹: …」. 이미 이 큐의 대상에서 빠진 그룹은 기존 사유가 말하므로 새 사유를 달지 않는다.

**전후 명령 diff** (`apply_commands.py` → `apply_commands.diff`, 시나리오 5개):

```
equal_levels / equal_levels_with_secondary / back_lower_unmapped_back : 변화 없음
back_lower (KEY 90, BACK 70):
- … 'Dimmer' At 90 ; <블루>
+ … 'Dimmer' At 90 ; <블루> ; Group 12 ; Attribute 'Dimmer' At 70
key_lower_with_secondary (KEY 50, BACK 90, 보조 앰버):
- … 'Dimmer' At 90 ; <블루> ; Group 12 ; <앰버>
+ … 'Dimmer' At 90 ; <블루> ; Group 12 ; <앰버> ; Group 11 ; Attribute 'Dimmer' At 50
```

**기존 곡에 미치는 영향(리드 판정 A로 수용).** 실제 곡 타임라인은 원래 KEY와 BACK의 값이 다르다(설계가 back = key × 0.8을 만든다). 그래서 편집하지 않은 큐도 다시 반영하면 BACK이 초안 값으로 따로 나간다. 수정 전 반영 경로가 back 비율을 잃던 결함을 고친 것이다. 명령 문자열을 고정하던 시험 5개(`test_cue_sheet_apply` ×4, `test_seeded_song_apply` ×1)를 새 명령으로 갱신했고, 파일마다 사유 주석을 달았다.

**`test_rig_preflight`의 「일부만 나가는 큐 1건」이 사라진 원인(리드 조건 ②, 먼저 잼).** `probe_preflight.py` → `probe_preflight_after.txt`:

```
· 큐 18개 중 반영 가능 18건(그중 일부만 나가는 큐 2건), 건너뜀 0건.
  skip q30 [role_unaddressed] 그룹별 조도를 나눠 보내지 못했습니다 — 콘솔 그룹 번호를 모르는 그룹: SIDE. 큐 전체 70% 한 값으로 보냈습니다.
q30 intensity: [KEY 70, SIDE 40]  fixture_groups: [KEY, BACK, SIDE-L, SIDE-R]
```

큐 30의 SIDE(40)는 주소록에 `SIDE`라는 이름이나 역할이 없다(콘솔에는 `SIDE-L`·`SIDE-R`만 있다). 그래서 따로 보내지 못하고 한 값(70)만 나간다. 수정 전에도 70이 나갔지만 말하지 않았고, 이제는 사유가 붙어 「일부만 나가는 큐」로 드러났다. 이 수정이 의도한 결과이므로 문구를 「2건」으로 갱신하고 새 사유 문장을 단언했다. `SIDE`를 `SIDE-L`·`SIDE-R`로 추측해 풀지 않는다(RG5 — 정확 일치만).

## ② 리저브 해제 큐와 잔여 그룹 수 (추가만)

`server/concept/session_bridge.py` — `concept_report.reserve`, `rows[].unused_groups`

- `reserve`: BLIND·STROBE가 해석된 큐 상태에서 처음 켜지는 행(`released_q`, `screen_position`). 한 번도 안 켜지면 null이다. 유보색은 입력(`raw_song["reserved"]`)이 선언할 때만 나오고, 해제 큐는 입력 색으로 판정한 곡에서만 찾는다. 상수 팔레트의 흰색은 쓰지 않는다(카드 t444 원칙).
- `unused_groups`: `headroom.compute_cue_headroom(state).unused_groups`를 그대로 썼다(새 계산 없음). 컨셉 그룹 로스터 11개 기준이다(REQ-093 (4)).
- 실측(`measure_reserve.out.txt`, 8구간 곡): BLIND는 q15(Final Chorus, 화면 구간 6)에서 처음 켜지고 STROBE는 한 번도 안 켜진다. 잔여 그룹은 10 → … → 1이다.
- t455가 고정한 키 목록 시험(`test_runbook_payload_t455_t456.py`)에 새 키 두 개를 더했다(추가만).

## ③ 요청 id — 하지 않음 (카드상 선택 항목)

편집 응답은 채팅 텍스트 한 줄(`_pointing_refusal`)이라, id를 싣려면 채팅 응답 프로토콜을 바꿔야 한다. 이 카드의 범위(파서·반영·payload 추가)를 넘는다. t460은 한 번에 한 요청만 보내고 다음 응답으로 상태를 넘기면 id 없이도 성립한다. 필요하면 별도 카드로 뺀다.

## 검증

| 주장 | 명령 | 관측 |
|---|---|---|
| ① RED→GREEN | `pytest test_cue_sheet_edit_group_scope_t461.py` | `10 failed, 4 passed` → `14 passed` |
| ① 기존 문장 | 코퍼스 스냅샷 대조 | `changed 0` / 6,832 |
| ⚠1 RED→GREEN | `pytest test_cue_sheet_apply_group_dimmer_t461.py` | `3 failed, 2 passed` → `5 passed` |
| ⚠1 영향 범위 | Dimmer·반영 명령을 고정한 시험 파일 33개 | `1810 passed, 22 skipped` (`pytest_scoped_dimmer.txt`) |
| ⚠1 반영 관련 | 반영·편집·세션 파일 15개 | `776 passed, 23 skipped` (`pytest_scoped_step2.txt`) |
| ② | `pytest test_concept_reserve_t461.py` + 컨셉 리포트 배선 4파일 | `36 passed` (`pytest_reserve.txt`) |
| 린트 | `ruff check` / `ruff format --check` (변경 파일 + 증거 스크립트) | 통과 |

## 안 잰 것 (Gaps)

- **실기 콘솔에 보내지 않았다.** 그룹별 Dimmer 덮어쓰기가 `/Merge` 저장에서 기대대로 남는지는 콘솔 실측이 없다. 다만 같은 last-wins 형태가 `session._back_layer_value_lines`에서 이미 쓰이고 있다.
- 한국어 그룹 이름('백')과 콘솔 그룹 이름(MOVER-U 등)은 받지 않는다(리드 승인 ⚠2). 이런 이름으로 말하면 파서가 그룹으로 읽지 않고 큐 전체 편집으로 처리한다 — 예: 「큐 3 백 밝기 70%」는 큐 전체 70이 된다.
- STROBE 해제는 실출력에서 한 번도 관측되지 않았다(이 곡에서는 켜지지 않는다).
- 전체 시험 묶음은 로컬에서 돌리지 않았다. CI에 맡긴다.

## 잔여 위험

- 편집하지 않은 기존 곡을 다시 반영하면 콘솔 명령이 한 줄 늘어난다(BACK 덮어쓰기). 리드가 감독에게 알렸다.
- 그룹 목록 정규식은 라틴 토큰 바로 뒤에 항목 낱말이 올 때만 그룹으로 읽는다. 기존 시험 문장에서는 오탐이 0건이지만, 라틴 약어를 쓰는 새 문장(예: 「큐 3 LED 밝기」)은 그룹 지정으로 읽혀 LED가 없으면 거절된다.
