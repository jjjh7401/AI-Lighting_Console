# t444 판정 — 컨셉 게이트의 색 판정은 입력 색으로만 (SPEC-LDDESIGN-001 REQ-026·027·029·030)

- 레인: 이 세션 · 워크트리 `.claude/worktrees/t444` · 브랜치 `WT-concept-two-colors`
- 기준: `origin/main@f5283ea4`, 도중에 `origin/main@f898d8a2` 합류(`b94aa28f`)
- 판정: **PASS** — 운영 경로의 G6은 실제로 내보내는 두 색으로 판정하고, 색이 없는 입력은 n/a로 둔다(리드 PASS 조건 그대로).

## 1. 정정: 구 기준선 90/6/8의 색 칸은 상수 팔레트 판정이었다

`server/tests/fixtures/pilot_baseline.json`의 곡에는 색이 없다. 최상위 키는 `song`·`bpm`·`bpm_confidence`·`duration_ms`·`n_sections`·`sections`이고, 구간 키에도 색이 없다. 이 사실은 시험 `test_fixture_songs_have_no_color_keys`가 고정한다. 그런데도 게이트는 `server/concept/gates.py`의 상수 4개(`PRIMARY_COLOR` 노랑, `SECONDARY_COLOR` 파랑, `CLIMAX_COLOR` 흰색, `UNDER_COLOR` 주황)로 색을 판정했다. 이 상수들은 프로토타입 `final_integrated.py:10`의 `PAL`을 그대로 옮긴 값이다.

그래서 **t439의 G6 FAIL 8칸, G2 PASS 7칸, G7 PASS 8칸은 모두 상수 팔레트로 낸 판정이었다.** 무대에 나갈 색에 대한 증거가 아니다.

## 2. 색 상수를 쓰는 게이트 전수

`grep -n "PRIMARY_COLOR\|SECONDARY_COLOR\|CLIMAX_COLOR\|UNDER_COLOR\|RESERVED_COLORS\|color" server/concept/gates.py`로 소비 지점을 찾은 뒤, 각 게이트가 부르는 모듈(`escalation.py`·`headroom.py`·`color_lint.py`)까지 읽어 확인했다.

| 게이트 | 색 의존 | 근거 | 입력에 색이 없을 때 |
|---|---|---|---|
| G2 후렴 정체성 | 전부 | `escalation.check_pairs`: `curr.color == prev.color` 또는 Final Chorus | n/a |
| G5 헤드룸 경고 | 조건 4개 중 1개 | `headroom.g5_warnings` (2) `chorus1_color == white_color` | 그 조건만 빼고 판정. 사유는 detail에 적는다 |
| G6 유보색·브리지 | 전부 | `check_reserved_color_release`(`RESERVED_COLORS`)와 `check_adjacent_bridge` | n/a |
| G7 후렴 주색 동일 | 전부 | `check_chorus_identity` | n/a |
| G1·G3·G4·G8~G13 | 없음 | G3/G4의 축은 groups·area·brightness·motion·direction·density로, 색이 없다(`escalation.new_axes`). G8은 빌드업 트리거 수만 센다 | 그대로 |

곡 앞 안전 큐의 `default_color=SECONDARY_COLOR`와 프레이즈 언더페인팅(`UNDER_COLOR`)은 큐 상태를 채울 뿐이다. 판정은 위 게이트에서만 일어난다.

## 3. 바꾼 것

| 파일 | 내용 |
|---|---|
| `server/concept/cue_model.py` | `CueState.secondary`(기본값 `None`) |
| `server/concept/resolver.py` | `replace` 동작이 `secondary`를 나른다. `restore`는 기준 상태의 보조색까지 되살린다 |
| `server/concept/mib.py` | 프로브 상태가 보조색을 보존한다 |
| `server/concept/gates.py` | 원시 구간의 `palette` 입력(`_input_palettes`)을 읽고, 구간 큐마다 `restore` 뒤에 `replace`로 얹는다. `TableRow.colors`, `SongBuild.color_source`·`reserved`를 더했다. G2·G6·G7은 입력 색이 없으면 n/a(`NO_INPUT_COLOR_REASON` = 「입력에 색 없음 — 상수 팔레트 판정 안 함」). G5는 흰색 조건만 입력 색으로 판정한다. G6의 유보색 절은 입력이 `reserved`를 선언했을 때만 판정한다 |
| `server/concept/compile.py` | 린트 입력에 `row.colors`를 준다. 색 입력이 없으면 오늘과 같은 한 색이다 |
| `server/concept/session_bridge.py` | 경로 A는 `SectionDecision.palette.colors`(주색, 보조색)를 싣는다. 경로 B는 `palettes=` 인자로 받는다. 개수가 맞지 않으면 예외를 던지지 않고 `available: False`를 낸다 |
| `server/orchestrator/tools.py` | `_songcue_director_primaries`·`_songcue_concept_palettes`(파일 끝), 그리고 `prepare_songcue`의 컨셉 리포트 호출에 `palettes=` 한 줄 |
| `server/tests/test_concept_gates.py` | 8곡 행렬을 다시 고정했다. 기준선 대조를 「색 게이트 23칸만 n/a로 다름」으로, 집계를 75/29/0으로 바꿨다. G7 대조군은 입력 색이 있는 곡으로 잰다 |
| `server/tests/test_concept_color_input_t444.py` (신규) | 이 카드 시험 28개(`28 passed`) |
| `server/tests/test_songcue_bundle.py` | `tools.py` 헝크 재고 79 → 80 |

**경로별로 실제로 실리는 색.** 경로 A(`session.py`)의 콘솔 명령은 주색을 `_song_color_value_lines`로 내고, 보조색은 큐시트 반영 시 back 역할 그룹에 얹는다(`cue_sheet_apply.py:551`). 그래서 두 색을 모두 싣는다. 경로 B(`prepare_songcue`)는 감독 주색만 룩의 RGB에 덮고 보조색은 내지 않는다(`_override_songcue_main_color` 독스트링). 그래서 주색 하나만, 그것도 덮어쓰기가 실제로 적용된 구간에만 싣는다. 룩 고유색은 RGB 값뿐이라 색 이름으로 옮기지 않았다.

## 4. 레인이 직접 잰 것

1. **8곡 재측정.** `uv run python .moai/reports/t444/gen_gates_8songs.py` → `gates_8songs.txt`에 **PASS 75 · n/a 29 · FAIL 0**이 나왔다. 구 90/6/8과 비교하면 G2 7칸, G7 8칸이 PASS에서 n/a로, G6 8칸이 FAIL에서 n/a로 바뀌었고 나머지 81칸은 같다. 시험 `test_gate_matrix_diverges_from_prototype_baseline_only_in_color_gates`가 칸 단위로 고정한다.
2. **입력 색 판정의 양쪽 대조.** Cut and Run에 절 (blue, white), 후렴 (yellow, white)를 실으면 G6 PASS다(보조색이 공통이다). 보조색 없이 blue와 yellow만 실으면 G6 FAIL이다. 후렴 회차마다 red와 green을 실으면 `restore` 행도 자기 색을 띠고, G7과 G2가 FAIL이다. 유보색 white를 선언하고 해제 전에 쓰면 G6 FAIL이다. Chorus 1이 " White "이면 G5 FAIL이다.
3. **운영 진입점 배선.** `prepare_songcue`를 툴셋으로 직접 돌렸다(BPM 120 분석 기록, 16초 간격 6구간). 감독 기록이 있으면 G6가 판정되고 PASS다. 모든 구간이 감독 주색 하나이기 때문이다. 기록이 없으면 G6 = `{passed: None, detail: 「입력에 색 없음 — 상수 팔레트 판정 안 함」}`이다.
4. **교차 대조.** 컨셉에 실은 색 이름을 RGB로 풀면, 덮어쓴 룩의 RGB와 구간마다 같다(modulate와 per_chorus 모두).
5. **변이 시험 6건, 모두 잡힘.** `uv run python .moai/reports/t444/mutation/run_mutations.py` → `mutation/*.txt`.
   - m1 resolver가 보조색을 버린다 → 3 failed
   - m2 경로 A가 palette를 뺀다 → 2 failed
   - m3 `prepare_songcue` 호출에서 `palettes=`를 뺀다 → 1 failed
   - m4 입력 색을 `restore` 앞에 둔다 → 1 failed
   - m5 입력 없이 G6를 상수로 다시 판정한다 → 18 failed
   - m6 헬퍼가 주색 대신 보조색을 집는다 → 4 failed
   - 첫 m6 시도(회차를 1로 고정)는 살아남았다. 주색은 늘 `base[0]`이라 회차와 무관한 등가 변이였다(`m6_first_try_equivalent.txt`).
6. **헝크 재고 가드.** 커밋 뒤 `measure_hunks.out.txt`: 79 → 80, 새 시작점 1233, 사라진 시작점 0, 보호 구간(234..238 / 524..569)과 형제 구간(247..251 / 537..582) 겹침 0. 합류 뒤 `measure_hunks_after_merge.out.txt`: 80 → 80, 겹침 0.
   - 🔴 처음엔 헬퍼를 `_override_songcue_main_color` 곁에 두고 그 본문을 헬퍼 호출로 바꿨다. 그러자 내용이 한 줄도 안 바뀐 `run_commands`가 diff 정렬상 삭제·재삽입으로 보여 79 → 112가 됐고, 보호 구간과 겹침 1(483,99)이 생겼다. 커밋 전 범위 시험으로는 이것이 보이지 않았다. 그래서 덮어쓰기 본문은 원래대로 두고 헬퍼를 파일 끝으로 옮겼다. 주색 결정이 두 곳에 남은 대가는 교차 대조 시험(4번)이 막는다.
7. **시험.** 합류 트리에서 `uv run pytest` 범위 시험(concept·songcue·chorus_color·song_timeline·tools·web·overlap_preserve·t451) → **2515 passed, 2 skipped**, exit 0(`pytest_scoped_after_merge.txt`). ruff check → All checks passed(`ruff_check.txt`). 시작 전 기준선은 456 passed(`pytest_before.txt`)다.

## 5. 합격 조건

| 조건 | 판정 | 근거 |
|---|---|---|
| 운영 경로 G6가 실제 두 색으로 판정됨 | PASS | 경로 A 원시 구간 palette = `SectionDecision.palette.colors`(시험), 보조색이 공통일 때만 통과하는 입력으로 PASS, m1·m2 변이 잡힘 |
| 색 없는 입력은 n/a | PASS | 8곡 G2·G6·G7 n/a와 사유 문자열 고정, m5 변이 18 failed |
| 색 상수를 쓰는 게이트 전수 표 | PASS | §2 |
| 8곡 기준선 재측정·고정 + 정정 명시 | PASS | 75/29/0, §1 |
| 경로 A·B 후렴 주색 동일(t441) · per_chorus 예외 유지 | PASS | `test_chorus_color_two_paths_t441.py` 통과, per_chorus G7 n/a 시험 통과 |
| 색을 지어내지 않음 · 시트 값 불가침 | PASS | 입력 palette가 없으면 싣지 않는다. 경로 B는 적용된 주색만 싣는다. fixture는 바꾸지 않았다 |

## 6. 안 잰 것

- **실기 콘솔.** 이 카드는 콘솔 명령을 바꾸지 않는다. 컨셉 리포트는 덧붙이는 정보다.
- **전체 시험.** 레인에서는 범위 시험만 돌렸다. 전체는 CI가 PR head에서 돈다.
- **경로 A 운영 곡의 실제 G6 결과.** 시험 plan(모든 구간 blue)으로만 쟀다. 실제 감독 곡에서 절과 후렴의 `_arc_palette` 보조색이 겹치는지는 곡마다 다르다. 실곡 리포트는 재지 않았다.
- **4초 간격 5구간 곡의 컨셉 파이프라인 실패**(`reduce: ref 'song_release_reference' 가 bases 에 없음`)는 이 브랜치에서 감독 기록 유무와 상관없이 똑같이 났다. 색 경로와 무관하다. main에서도 같은지는 재지 않았다.

## 7. 남은 위험

- 경로 A의 보조색은 back 역할 그룹이 매핑돼 있을 때만 콘솔로 나간다. 매핑이 없으면 `ROLE_UNADDRESSED`로 건너뛴다. 이때 컨셉 게이트는 두 색으로 판정하지만 무대에는 주색만 나간다.
- 색 이름 비교는 대소문자와 공백만 접는다. 한 곡 안에서 "블루"와 "blue"가 섞이면 다른 색으로 센다. 오늘 두 경로는 각각 한 가지 표기만 쓴다.
- 안전 큐(곡 앞)는 입력의 첫 색을 받는다. 운영 경로에는 없는 큐라서 첫 전환의 브리지는 항상 통과한다.
