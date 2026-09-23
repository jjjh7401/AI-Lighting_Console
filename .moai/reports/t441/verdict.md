# t441 판정 — SPEC-LDDESIGN-001 REQ-003 부분 충족(색 결정만)

- 레인: lane-3 · 워크트리 `.claude/worktrees/t441` · 브랜치 `WT-single-composer`
- 기준: `origin/main@452d8aa7`, 도중에 origin/main 합류
- 판정: **PASS(범위 한정)** — REQ-003은 색 결정만 부분 충족했다. `build_songcue_bundle` 은퇴와 LDCLIMAX/LDACCENT/LDRETURN 이식은 카드 t448로 넘긴다.

## 범위 결정 (리드 승인 (c))

합격 조건 ①(경로 B를 composer 한 길로)과 ③(절정·액센트·되돌아옴 보존)이 충돌했다.

- composer에는 절정·어둠 로직이 0건이고, songcue에는 climax 91 · accent 142 · darkness 76건 있다(리드 재측정).
- ①을 글자 그대로 하면 기존 시험 40개는 `build_songcue_bundle`을 직접 불러서 계속 초록인데, 생산 경로에서는 세 기능이 사라진다. 시험이 가리는 퇴행이다.
- 그래서 이 카드는 **색 결정만** 두 경로가 공유하게 했다.

## 산출물

| 파일 | 내용 |
|---|---|
| `server/design/section_palette.py` (신규) | `_section_palette_choice`·`_arc_palette`·`_per_chorus_palette`·`_arc_accent_weight` 등을 `session.py`에서 옮겼다. `role_for_songcue_label` 추가 |
| `server/web/session.py` | 옮긴 이름을 다시 내보낸다(기존 import 유지). 인터뷰 완료 시 records를 보관하고 `_SongInterviewRecordsView`로 toolset에 공급한다 |
| `server/orchestrator/tools.py` | `InterviewRecordsPort`, `build_toolset(interview_records=)`, `_override_songcue_main_color` — `prepare_songcue`가 Look을 고른 뒤 `build_songcue_bundle`을 부르기 **전에** 주색 칩(ColorRGB_R/G/B)만 덮는다 |
| `server/tests/test_chorus_color_two_paths_t441.py` (신규) | 두 입구 교차 일치, 역할 매핑, 기록 없음 대조군, 날조 대조군, 실제 명령 색 단언 |
| `server/tests/test_songcue_bundle.py` | `tools.py` 헝크 재고 목록 갱신(94 → 79, 사유 주석) |

## 레인이 직접 잰 것

1. **두 입구 후렴 주색 표.** `.moai/reports/t441/chorus_color_two_paths.md` — modulate와 per_chorus 모두 경로 A 주색 "블루"와 경로 B RGB (5, 20, 100)이 모든 구간에서 같다(10/10 PASS). 기록이 없을 때 경로 B는 오늘처럼 Chorus가 crimson (100, 0, 15), Drop이 acid (72, 100, 0)를 낸다.
2. **실제 명령 diff.** `uv run python .moai/reports/t441/probe_command_diff.py` → 툴셋으로 `prepare_songcue`를 돌리면 52줄 중 **색 값 5줄만** 다르다(`probe_command_diff.txt`). 밝기·줌·Store·사다리 명령은 같다.
3. **변이 시험.** `prepare_songcue` 안의 덮어쓰기 호출을 빼는 변이를 넣자, 에이전트가 쓴 시험 24개는 **모두 통과**했다. 툴셋 시험이 "실패 메모 없음"만 봤기 때문이다. 그래서 명령 색을 직접 단언하는 시험 2개를 추가했고, 같은 변이에서 1 failed가 나왔다(`mutation/m1_no_override.txt`).
4. **헝크 재고 가드.** `test_songcue_bundle.py::test_tools_hunks_are_only_songcue_registration_and_not_dedupe_or_state`가 커밋 뒤에 실패했다. 에이전트의 "전체 통과" 보고는 커밋 전 측정이라 이 검사에는 공허했다. 가드 주석에 경고로 적혀 있는 함정이다. 커밋 뒤에 다시 재어 보호 구간 겹침 0을 확인하고, 사유와 함께 목록을 갱신했다. 형제 게이트 `test_overlap_preserve.py`는 72 passed다.
5. **시험.** 절정·액센트·팔레트·게이트 묶음 124 passed(`pytest_lane_verify.txt`). 합류 뒤 범위 시험 결과는 `pytest_scoped_after_merge.txt`에 있다. **전체** `uv run pytest server/tests -q` → 14226 passed, 35 skipped, exit 0이다(`pytest_full.txt`, 커밋 `038274c1` 위에서 커밋 뒤 측정).

## 합격 조건

| 조건 | 판정 | 근거 |
|---|---|---|
| ② 같은 곡, 두 입구, 후렴 회차별 주색 동일 | PASS | 표 10/10, 실제 명령 단언 |
| ④ per_chorus 예외 유지 | PASS | 경로 A 회전(t404·t439 시험)은 그대로다. 경로 B는 주색만 다루고 주색은 두 모드 모두 primary라 일치한다 |
| ③ LDCLIMAX/ACCENT/RETURN 시험 통과 | PASS | climax 18 · accent ladder 15 · accent fixture 7, 수정 0 |
| ⑤ 8곡 게이트 90/6/8 | PASS | `test_concept_gates.py` 통과, 파일 무변경 |
| ① 한 길로 | 부분 | 색 결정 함수만 공유한다. 방출은 여전히 두 갈래다 → t448 |

## 관찰

- **기록이 없으면 오늘 그대로다.** 대화만 쓰는 경우 records가 None이라 색을 지어내지 않는다. 대조군 시험으로 확인했다.
- **덮어쓰기 위치.** 덮어쓰기는 `build_songcue_bundle` 전에 한다. 그래서 색 스냅(`_color_snap_is_effective`)과 되돌아옴 팔레트(`_label_return_palette`)가 감독 색을 "그 구간의 색"으로 읽는다. `selection.look`뿐 아니라 `dynamics_matches` 후보까지 다시 칠해야 실제로 결합되는 룩에 적용됐다. 에이전트가 도중에 발견해서 고쳤다.
- **주색 외 그룹은 덮지 않는다.** Intro 룩의 두 번째 그룹(RGB 100/75/52)은 그대로다. 경로 A는 보조색을 BACK에 내지만, 경로 B는 보조색 개념이 없다.
- **역할 매핑.** `role_for_songcue_label`은 기존 `intent_for_label`을 다시 쓴다. Intro→intro, Verse→verse, Chorus·Drop→chorus, Breakdown·Bridge→bridge, Build·Post-Chorus·그 밖→other. finale은 만들지 않는다. 색 축에서 chorus와 finale은 같게 다뤄지기 때문이다.

## 범위 밖

- `build_songcue_bundle` 은퇴, 방출 경로 단일화, LDCLIMAX/LDACCENT/LDRETURN 이식 → 카드 t448
- 경로 B의 `palette_mode` "mixed"/"concept"(Q1 컨셉 색 충돌) 미배선 — 경로 A가 답이 없을 때 쓰는 기본값 "palette"와 같다

## 안 잰 것

- 실기 콘솔에는 쏘지 않았다(가짜 포트).
- 기록이 있는 세션에서 색 스냅 사다리 칸 선택이 바뀌는지는 한 곡(5구간)으로만 봤다. 명령 diff가 색 값뿐이었다. 다른 곡·다른 장르는 재지 않았다.
- `role_for_songcue_label`은 대표 라벨만 시험했다.
- ColorRGB_W: 이 경로의 룩 스키마에 W 채널이 없어서 다루지 않았다.
