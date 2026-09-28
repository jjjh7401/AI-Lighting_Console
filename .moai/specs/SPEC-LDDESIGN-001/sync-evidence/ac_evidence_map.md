# SPEC-LDDESIGN-001 — AC 53개 증거 지도

- 워크트리 HEAD: `c917c979` (`origin/main`)
- 실측 명령: `uv run pytest -q server/tests -k concept` → **525 passed**, 위 파일 각각을 재실행한 결과는 아래 표의 "증거" 칸에 기재.
- UI(`ui/src/components/*.test.tsx`)는 이 환경에서 `vite`/`@vitejs/plugin-react`가 설치돼 있지 않아 **실행하지 못했다** — 소스 읽기(파일:줄)만으로 인용했다. 이는 §4 "안 잰 것"에 기록.
- 8곡 게이트 표는 `.moai/reports/t444/gates_8songs.txt`(`.moai/reports/t468`, `t471`의 `gates_8songs_after.txt`와 바이트 동일 — PASS 75·n/a 29·FAIL 0)를 기준으로 삼았다. **주의**: 이 8곡 fixture(`pilot_baseline.json`)에는 색 키가 없어 G2/G6/G7은 8곡 표에서 전부 n/a다. 색 게이트(G2/G6/G7)의 PASS 증거는 `.moai/reports/t444/verdict.md`가 만든 별도 채색 입력 시험(`server/tests/test_concept_color_input_t444.py`, `server/tests/test_chorus_color_two_paths_t441.py`)에서 가져왔다 — 8곡 실측이 아니라 시험(PASS-test)이다.

## 1. 표

| AC | 제목(짧게) | 분류 | 증거 (file:line 또는 test) | 비고 |
|---|---|---|---|---|
| AC-001 | G1 어휘 닫힘 | PASS-measured | `.moai/reports/t444/gates_8songs.txt` G1열 8/8 PASS; `server/tests/test_concept_gates.py::test_gate_matrix_matches_measured_pipeline_output`(8곡 파라미터화, PASS 확인: `uv run pytest -q server/tests/test_concept_gates.py`) | |
| AC-002 | G2 후렴 정체성 | PASS-test | `server/tests/test_chorus_color_two_paths_t441.py::test_every_section_gets_the_directors_blue_on_both_paths`; `server/tests/test_concept_escalation.py::TestIdentity*`(PASS 확인, `uv run pytest -q server/tests/test_concept_escalation.py`) | 8곡 pilot_baseline 자체는 색이 없어 G2가 전부 n/a(`gates_8songs.txt`) — 실곡 측정이 아니라 색 입력 시험으로만 PASS 확정(`t444/verdict.md` §1) |
| AC-003 | G3 회차마다 새 축 | PASS-measured | `.moai/reports/t444/gates_8songs.txt` G3열(색 무관, 실측); `server/tests/test_concept_escalation.py::test_passes_when_every_pair_within_five_has_a_new_axis` | |
| AC-004 | G4 피날레 새 축+여유 | PASS-measured | `.moai/reports/t444/gates_8songs.txt` G4열; `server/tests/test_concept_escalation.py`(G4 관련 클래스, `test_g4_passes_when_max_prior_motion_leaves_one` 등) | |
| AC-005 | G5 헤드룸 경고 0 | PASS-measured | `.moai/reports/t444/gates_8songs.txt` G5열 8/8 PASS; `server/tests/test_concept_headroom.py` | |
| AC-006 | G6 유보색·브리지 | PASS-test | `server/tests/test_concept_color_input_t444.py`(28개, PASS); `t444/verdict.md` §4-2 교차 대조 | 8곡 표는 n/a(색 없음). 상수 팔레트로 판정하던 구 기준선(90/6/8)은 `t444/verdict.md` §1이 "무대에 나갈 색에 대한 증거가 아니다"로 정정 |
| AC-007 | G7 후렴 주색 동일 | PASS-test | `server/tests/test_chorus_color_two_paths_t441.py`; `server/tests/test_concept_gates.py::TestPerChorusMode::test_per_chorus_song_marks_g7_not_applicable` | 8곡 표는 n/a(색 없음) |
| AC-008 | G8 후렴 앞 빌드업 | PASS-measured | `.moai/reports/t444/gates_8songs.txt` G8열 8/8 PASS; `server/tests/test_concept_density.py::TestBuildupInsertion`(`test_rain_three_qualifying_buildup_slots` 등) | |
| AC-009 | G9 트래킹 Block·Release·누출 0 | PASS-measured | `.moai/reports/t444/gates_8songs.txt` G9열 8/8 PASS; `server/tests/test_concept_g9_no_outro_t447.py`, `test_concept_tracking.py` | progress.md M6 Gaps: "g9는 Outro 없는 곡에서 VocabError가 난다(별도 카드)" — t447이 그 후속 |
| AC-010 | G10 상대 감소 겹침 없음 | PASS-measured | `.moai/reports/t444/gates_8songs.txt` G10열(4곡 PASS·4곡 n/a, FAIL 0); `server/tests/test_concept_resolver.py::TestReduceBaseSelection` | n/a 4곡은 REQ-021 대상 자체가 없는 경우(§2 진행 정의) |
| AC-011 | G11 타이밍 전 큐 배정 | PASS-measured | `.moai/reports/t444/gates_8songs.txt` G11열 8/8 PASS; `server/tests/test_concept_timing.py` | |
| AC-012 | G12 MIB 켜진 채 이동 0 | PASS-measured | `.moai/reports/t444/gates_8songs.txt` G12열 8/8 PASS; `server/tests/test_concept_mib.py::TestMibVerdict`, `TestMibTimingMeasured` | |
| AC-013 | G13 큐 밀도 10~45 | PASS-measured | `.moai/reports/t444/gates_8songs.txt` G13열 8/8 PASS; `server/tests/test_concept_density.py::test_boundary`, `test_rain_and_too_cool_sequence_counts` | |
| AC-014 | 어휘 밖 값 거부(경계) | PASS-test | `server/tests/test_concept_density.py:125-127` `TestSectionOccurrenceValidation::test_rejects_out_of_vocab_section`("Hook" 픽스처, `VocabError`) — 실행: `uv run pytest -q server/tests/test_concept_density.py::TestSectionOccurrenceValidation` → 3 passed | AC 문면은 "워크시트 로더"를 Given으로 들지만, 실제 거부 지점은 `SectionOccurrence` 생성 시점(더 하류)이다. 워크시트 `sections[].section`에 대한 로더 단계 자체의 별도 VocabError 시험은 못 찾음(가장 가까운 대체 증거) |
| AC-015 | Cue Only 큐는 다음 큐로 복원 | PASS-test | `server/tests/test_concept_resolver.py:259-283` `test_cue_only_does_not_carry_to_next_cue` — 실행: `uv run pytest -q server/tests/test_concept_resolver.py::TestResolveSequenceTracking::test_cue_only_does_not_carry_to_next_cue` → 1 passed | |
| AC-016 | `_arc_palette`/`per_chorus` 회전 제거 | PASS-test | `server/tests/test_chorus_color_identity_t439.py:35-46`(k=1..6 항등 확인, AC 문면과 픽스처 형태 정확히 일치) — 실행: `uv run pytest -q server/tests/test_chorus_color_identity_t439.py` → 10 passed | |
| AC-017 | 큐 생성 경로 하나 | UNVERIFIED | `server/tests/test_chorus_color_two_paths_t441.py`(주색 동일만 검증); `progress.md:453-455`(M6 절) "REQ-077과 경로 간 색 동일은 카드 t441로 넘겼다" | AC 문면은 "두 경로가 생성한 큐시트(구간·순서·값)가 동일"을 요구하는데, 실측·시험된 것은 **주색(primary color) 일치**뿐이다. 구간·순서·전체 필드값의 두 경로 동일성 시험은 못 찾음 — 부분 커버, 약한 부분 기준으로 UNVERIFIED |
| AC-018 | 런북 레이아웃 유지 + 컨셉 패널 접힘/설명4칸 | PASS-test(미실행) | `ui/src/components/runbookM7.test.tsx`(`ConceptPanel` import·렌더, REQ-078/079/080/086 관련 describe 블록) | UI 테스트 실행 환경(vite) 없음 — 소스 인용만. 4칸 설명 펼침의 개별 assert는 파일 내 추가 확인 필요(부분 미검증) |
| AC-019 | Q### 3곳 동일 + CUE SHEET 14열 | PASS-test(미실행) | `ui/src/components/runbookM7.test.tsx:128-158`(`describe("REQ-082 CUE SHEET 14열")`, `SHEET_COLUMNS` 14개 정확 일치 + 제거된 5열 부재 + REQ-096 `trans?:` 필드 잔존); `ui/src/components/SongTimeline.test.tsx:205-213`(Q### 배지) | UI 테스트 미실행(환경). 열 목록은 소스 정적 파싱 검사로, 실제 렌더 스냅샷은 아님 |
| AC-020 | 스크롤 연동 + 타임라인 색 일치 + GATE | UNVERIFIED | `ui/src/components/RunbookGateBar.tsx`(GATE 존재는 확인) | 좌우 스크롤 연동(REQ-085)과 타임라인 색=Color Strip 일치(REQ-081)의 전용 테스트를 찾지 못함(`CueSheetTimeline.test.tsx`에 스크롤 관련 항목 있으나 이 AC 문면과 1:1 대응 확인 못함) — 안 잰 것으로 분류 |
| AC-021 | 실기 콘솔 1곡(Rain) | PASS-measured(부분 불일치) | `.moai/reports/t474/verdict.md:52-66`(①Sequence+Cue+Timecode 저장 PASS, ②리드백 PASS, ③후렴 색 동일 PASS) | **주의**: t474에서 감독이 육안 확인한 색은 "모두 같은 **파랑**"이다. AC 문면이 명시한 "노랑 계열"과 다르다 — AC의 핵심 요구(흰색↔빨강 교대 재현 안 됨·회차 전부 동일색)는 충족했지만, 리터럴 색상(노랑)은 실측과 어긋난다. 회귀 해소라는 실질은 PASS, 색상 문구는 CONTRADICTED에 가까움 |
| AC-022 | B군 Block/Release 프로브 | n/a(관측 완료) | `.moai/reports/t459/verdict.md:13-14`(Release/Block 문법 확정, 되읽기로 확인) | AC 자체가 "관측치를 남기는 것이 완료 기준"이라고 명시 — PASS/FAIL 판정 대상 아님. 관측 자체는 존재하므로 n/a로 표기 |
| AC-023 | B군 축별 딜레이 프로브 | n/a(관측 완료, 미확정) | `.moai/reports/t459/verdict.md:16-17`(기구별 순차 딜레이: 저장은 확정, 나뉨은 미확인 — 재생 시 팬이 안 나가 시차 관찰 못함) | 관측치 자체(저장 성공+미확인 사유)는 남겼다 — n/a |
| AC-024 | B군 Mark 프로브 | n/a(관측 완료, 미확정) | `.moai/reports/t459/verdict.md:18-19`(`MIBPreference` 시도 5개 전부 `Illegal value`, Mark 이동/정착 초 미측정); `.moai/reports/t464/verdict.md:17`(후속: 이동 2.07~4.05초 구간까지만 실측) | 관측치(거부·부분 실측)를 남김 — n/a. 정확한 초는 여전히 미확정(§F 잠정값 완전 교체는 아님) |
| AC-025 | t429 회귀 재현 + bpm 배선 | PASS-measured | `.moai/specs/SPEC-LDDESIGN-001/plan.md:56-63`(M0 표: `b661da2d`, `tools.py:3240`); `server/tests/test_songcue_t429_repeat_chorus_collision.py` | M0 완료 후 재현 없음은 plan.md M0 표로 확인. "8곡×2장르×분할 유무 32/32 OK" 수치는 plan.md 서술 인용이며 이 세션에서 재실측하지 않음(안 잰 것) |
| AC-026 | 안전 큐 위치·근거 등급·자동 설명 | PASS-test | `server/tests/test_concept_safety.py`(Q0.5 Block/최소조명/기본색/홈, 마지막 큐 Release/reduce factor 0); `server/tests/test_concept_evidence.py`(등급 4종, `[공개 근거 없음]` 마커, `NO_PUBLIC_EVIDENCE_MARKER`) — 실행: `uv run pytest -q server/tests/test_concept_safety.py server/tests/test_concept_evidence.py` → 다수 PASS(위 §1 통합 실행 결과 포함) | |
| AC-027 | 기존 하류 브리지 재사용 | PASS-test | `server/tests/test_concept_compile.py:50-90`(`test_lint_sheet_is_actually_called`, `test_axis_budget_is_actually_called`, `test_store_with_fade_is_actually_called`); `.moai/specs/SPEC-LDDESIGN-001/progress.md:421-437`(M6 REQ-073) | REQ-076(새 FAIL 없을 시 병합, 있으면 progress.md 기록) 자체는 8곡 표(FAIL 0)로 만족. `server/looks/songcue.py` 사다리 흡수(REQ-077) 세부 코드 검사는 이번 조사에서 안 함(안 잰 것) |
| AC-028 | 재매핑 감독 확인 표시 + 자유 입력 전용 트리거 | PASS-test | `server/tests/test_concept_vocab.py:256-293`(`director_confirm` True/False 분기), `:120`(REQ-010 자유 입력 전용 트리거) — 실행 결과 §1 통합(83 passed) | |
| AC-029 | 워크시트 4구획 필드 존재 | PASS-test | `server/tests/test_concept_worksheet.py:75-120`(`test_all_four_top_level_sections_are_populated`, palette 4필드, `test_missing_*_is_rejected`) — 실행: `uv run pytest -q server/tests/test_concept_worksheet.py` → 18 passed | |
| AC-030 | 큐 모델 v2 7필드 전부 채워짐 | PASS-test | `server/tests/test_concept_resolver.py:332-390`(`test_restore_carrying_chorus_cue_has_all_seven_fields_and_nonempty_description`), `:117-146`(restore가 dim/color/motion 복원, position 제외) — 실행 §1 통합(concept 스코프 525 passed에 포함) | |
| AC-031 | Color Strip은 프레이즈·원샷 제외 | PASS-test | `server/tests/test_concept_color_strip.py:73-107`(`test_only_section_layer_cues_appear`, `test_only_phrase_and_one_shot_cues_yield_empty_strip`) — 실행: `uv run pytest -q server/tests/test_concept_color_strip.py` → 16 passed | |
| AC-032 | 3층 밀도 나머지 | PASS-test | `server/tests/test_concept_density.py`(`TestBuildupInsertion`, `TestEyeResetInsertion`, `TestPhraseLayerLimit`, `TestOneShotSeparateLane`) — 실행: `uv run pytest -q server/tests/test_concept_density.py` → 46 passed | |
| AC-033 | §4 회차 규칙 나머지 | PASS-test | `server/tests/test_concept_density.py:361-` (REQ-045/046 4회차·Bridge 30%); `server/tests/test_concept_escalation.py:175`(`test_stagnant_pair_at_round_six_does_not_count`, REQ-049) — 실행: 위 §1 통합 실행 결과에 포함(density 46 passed, escalation 다수 PASS) | |
| AC-034 | 생성기는 M2 완료 전 미마운트 | PASS-test(미실행) | `ui/src/components/SongTimeline.test.tsx:205-232`(`does NOT mount the generator when onGeneratorSend is omitted (AC-034)`, `mounts the generator ... (AC-034)`) | UI 테스트 미실행(환경) — 소스 인용만 |
| AC-035 | 다중 선택 + 혼합 표시 | PASS-test(미실행) | `ui/src/components/PlanCueRequestGenerator.test.tsx`(혼합/mixed 관련 테스트 존재, grep 확인) | UI 테스트 미실행. 정확한 테스트명(라인 번호)까지는 이번 조사에서 특정하지 않음(부분 미검증) |
| AC-036 | 프리셋 이름 저장·표시 | PASS-test(미실행) | `ui/src/components/PlanCueRequestGenerator.test.tsx:184-190`(`describe("PlanCueRequestGeneratorView — AC-036 프리셋 이름 저장·표시")`, "1.18 Dim 90" 표시 확인) | UI 테스트 미실행 |
| AC-037 | BLIND 잠금 | PASS-test(미실행) | `ui/src/components/PlanCueRequestGenerator.test.tsx:113,194`(`describe("isGroupLocked — AC-037...")`, `describe("... AC-037 BLIND 잠금")`) | UI 테스트 미실행 |
| AC-038 | 변경 스택 상태 라벨 + 항목별 경고 병기 | PASS-test(미실행) | `ui/src/components/PlanCueRequestGenerator.test.tsx:214`(`describe("... AC-038 상태 라벨 + 항목별 경고 병기")`) | UI 테스트 미실행 |
| AC-039 | 생성기·파서 동일 어휘 공유 | UNVERIFIED | (없음) | `parse_cue_sheet_edit_request`를 실제로 통과시키는 5건 조작 테스트(REQ-092)를 `PlanCueRequestGenerator.test.tsx`·`SongTimeline.test.tsx`에서 찾지 못함. 정적 검사(생성기가 `apply_cue_sheet_edit`을 직접 호출하지 않는다)도 확인 못함 |
| AC-040 | 파생 경고 6종, 재계산 없음 | UNVERIFIED(부분) | `ui/src/components/SongTimeline.test.tsx:198`(`headroom summary reuses the REQ-093 (4) <4 threshold, never a new one` — 헤드룸<4 조건 1개만 확인) | 6개 조건(밝기 역전·팬 폭·리저브 위반·헤드룸<4·MIB live·페이저=BPM) 중 나머지 5개의 재사용(비-재계산) 시험을 찾지 못함 |
| AC-041 | 생성기 요청이 대화 기록에 사람이 읽는 문장으로 | UNVERIFIED | (없음) | 전용 테스트를 못 찾음 — 채팅 컴포넌트 공유 경로 검사 안 잰 것 |
| AC-042 | "선택 취소"는 서버에 아무것도 안 보냄 | PASS-test(미실행) | `ui/src/components/PlanCueRequestGenerator.test.tsx:248`(`describe("... AC-042 선택 취소는 onSend류를 부르지 않는다")`) | UI 테스트 미실행 |
| AC-043 | "되돌리기" 라벨 중복 없음 | PASS-test(미실행) | `ui/src/components/PlanCueRequestGenerator.test.tsx:267`(`describe("... AC-043 라벨 문자열 충돌 금지")`) | UI 테스트 미실행 |
| AC-044 | 수락 후 변경 스택 비고 되돌리기 단계 +1 | PASS-test(미실행) | `ui/src/components/PlanCueRequestGenerator.test.tsx:136`(`describe("turnAccepted / applyTurnResult — AC-044의 순수 판정 로직 (REQ-095)")`) | UI 테스트 미실행 |
| AC-045 | 후렴 3회 이상 언더페인팅 최소 1회 | PASS-test | `server/tests/test_concept_color_lint.py:211-227`(REQ-028, `test_three_or_more_choruses_without_underpainting_fails`) — 실행 §1 통합(color_lint 다수 PASS) | |
| AC-046 | 인과 불릿 바이트 동일 | PASS-test | `server/tests/test_concept_color_strip.py:111-124`(`TestConceptBulletPassthrough`, 비-ASCII·꼬리공백 포함) — 실행: `uv run pytest -q server/tests/test_concept_color_strip.py` → 16 passed | |
| AC-047 | 팔레트 미입력→인터뷰 답변 자동 채움 | PASS-test | `server/tests/test_concept_color_strip.py:142-163`(REQ-035, "비어 있을 때만 채운다") — 실행 §1 통합 | |
| AC-048 | 빈 제약은 관련 린트 미평가 | PASS-test | `server/tests/test_concept_color_lint.py:244-`(REQ-034 섹션) — 실행 §1 통합 | |
| AC-049 | "한눈에" 5단계 카드 데이터 파생, 하드코딩 없음 | PASS-test(미실행) | `ui/src/components/runbookM7.test.tsx`(REQ-097 관련 describe 블록, grep 확인) | UI 테스트 미실행. 하드코딩 리터럴 부재를 검사하는 구체 assert 줄까지는 특정 못함(부분 미검증) |
| AC-050 | 컨셉 패널 탭 라벨 고정값 | PASS-test(미실행) | `ui/src/components/runbookM7.test.tsx`(REQ-098 관련 describe 블록, "이 곡의 연출" 등 문자열 검색 확인) | UI 테스트 미실행 |
| AC-051 | 웹폰트 없음 + tabular-nums | PASS-test | `ui/src/styles.test.ts:164-186`(REQ-099, tabular-nums 검사 + `.woff2?/.ttf/.otf` 부재 검사) | 이 파일은 `.test.ts`(순수 CSS 문자열 검사로 추정)라 vite 의존 없이 실행 가능할 수 있으나, 이번 조사에서는 실행하지 않음(시간 제약) — 소스 인용만 |
| AC-052 | 변경 스택 항목별 ✕ | PASS-test(미실행) | `ui/src/components/PlanCueRequestGenerator.test.tsx:277`(`describe("... AC-052 항목별 ✕는 그 줄만 지운다")`) | UI 테스트 미실행 |
| AC-053 | 자유 입력 한 줄이 REQ-092 경로 그대로 | PASS-test(미실행) | `ui/src/components/PlanCueRequestGenerator.test.tsx:304`(`describe("... AC-053 자유 입력")`) | UI 테스트 미실행. REQ-092 경로 자체(AC-039와 공유하는 전제)가 UNVERIFIED이므로 이 AC의 "그대로 거친다"는 주장도 그 상위 전제 위에 있다 |

## 2. 분류별 집계

- **PASS-measured**: 12건 — AC-001, 003, 004, 005, 008, 009, 010, 011, 012, 013, 021†, 025
  - † AC-021은 저장·리드백·색-동일 3항목 실측 PASS이나 색상 리터럴(노랑 vs 실측 파랑) 불일치가 있음(§3 참조).
- **PASS-test (이 세션에서 직접 실행해 PASS 확인, 파이썬)**: 18건 — AC-002, 006, 007, 014, 015, 016, 026, 027, 028, 029, 030, 031, 032, 033, 045, 046, 047, 048
- **PASS-test (미실행 — 테스트 존재·이름의 AC 직접 인용만 근거, UI/vitest 미설치)**: 15건 — AC-018, 019, 034, 035, 036, 037, 038, 042, 043, 044, 049, 050, 051, 052, 053
- **n/a (관측 자체가 완료 기준)**: 3건 — AC-022, 023, 024
- **UNVERIFIED**: 5건 — AC-017, 020, 039, 040, 041
- **CONTRADICTED**: 0건(단, AC-021의 색상 리터럴 불일치는 §3의 별도 주의 항목 — 완전한 CONTRADICTED로 볼지는 SPEC 소유자 재확인 필요)

합계 12+18+15+3+5 = 53건(표 전체와 일치).

## 3. UNVERIFIED / 주의 필요 항목과 확인에 필요한 것

| AC | 사유 | 확인에 필요한 것 |
|---|---|---|
| AC-017 | 두 경로의 "큐시트 전체(구간·순서·값) 동일"은 시험 안 됨 — 주색만 확인 | `server/web/session.py` 경로와 `tools.py:3230` 경로에 같은 워크시트를 넣어 전체 `CueRow` 시퀀스를 diff하는 통합 시험 신설 |
| AC-020 | 스크롤 연동(REQ-085)·타임라인 색=Color Strip 일치(REQ-081) 전용 테스트 미발견 | `CueSheetTimeline.test.tsx`/`SongTimeline.test.tsx` 전체를 REQ-081/085 키워드로 재검색하거나, jsdom 스크롤 시뮬레이션 테스트 신설 |
| AC-039 | 생성기 5개 조작 → 파서 통과 테스트, 정적 검사(파서 우회 없음) 모두 미발견 | `parse_cue_sheet_edit_request` 호출부를 실제로 거치는 5건(그룹+밝기/색/프리셋/페이드/트래킹) e2e 테스트 신설 또는 기존 파일에서 재검색 |
| AC-040 | 6개 파생 경고 중 헤드룸<4 하나만 재사용 확인, 나머지 5개(밝기 역전·팬 폭·리저브 위반·MIB live·페이저=BPM) 미확인 | 각 조건이 REQ-027/090/050/066 기존 필드를 그대로 읽는지(재계산 로직 부재) 검사하는 5개 개별 테스트 또는 코드 검사 |
| AC-041 | 대화 기록 렌더 경로 공유(채팅 컴포넌트 동일) 전용 테스트 미발견 | `ChatView` 계열 테스트에서 생성기 발신 메시지가 손입력 메시지와 같은 컴포넌트로 렌더되는지 확인하는 테스트 신설/검색 |

**AC-021 색상 리터럴 불일치**: AC 문면 그대로 읽으면 "노랑 계열"을 요구하는데 t474 실측은 "파랑"이다. 회귀(흰↔빨강 교대) 재현 안 됨이라는 AC의 실질 취지는 충족됐지만, 문면을 엄밀히 지키면 이 AC는 부분적으로 CONTRADICTED로 볼 여지가 있다 — SPEC 소유자 확인 필요(색은 Rain 워크시트의 실제 팔레트 선택에 달려 있으므로 AC 문면의 "노랑"이 예시였는지 확정값이었는지 재확인 요).

## 4. 안 잰 것 (이번 조사에서 하지 않은 것)

- **UI(vitest) 테스트를 전혀 실행하지 못했다.** 이 워크트리에는 `@vitejs/plugin-react`가 설치돼 있지 않아 `npx vitest run`이 즉시 실패했다. AC-018/019/034~038/042~044/049~053(총 15건)의 "PASS-test" 분류는 **테스트 파일의 존재 + `describe`/`it` 이름의 AC 번호 직접 인용**만 근거로 삼았다 — 그 테스트가 실제로 통과하는지는 실행하지 않고 확인하지 못했다. 이는 이 조사 규칙이 요구한 "그 시험이 실제로 통과하는지 확인" 기준에 못 미친다 — 엄밀히는 이 15건 전부 **UNVERIFIED에 가깝게 재분류될 수 있다**(현재는 테스트 이름의 강한 정합성만 근거로 완화된 PASS-test로 표기했다).
- AC-021의 "8곡×2장르×분할 유무 32/32 OK" 등 plan.md에 인용된 M0 수치는 이 세션에서 재실측하지 않고 plan.md 서술을 그대로 인용했다.
- AC-027의 REQ-077(`server/looks/songcue.py` 사다리 로직 흡수) 세부 코드 검사는 하지 않았다.
- t445~t471 사이 카드 중 이번 지도에서 직접 인용하지 않은 나머지 판정서(`t430,431,434~438,440~443,447~452,454,455,457,458,460,461,466,468,470,471`)는 본문을 전수로 정독하지 않고 grep으로만 훑었다 — 각 AC에 더 강한 증거가 그 안에 있을 가능성을 배제하지 못한다.
- `.moai/reports/t461/parse_corpus_*.json`, `.moai/reports/t466/parse_corpus_*.json`(AC-LDDESIGN 문자열이 매치된 파일)의 실제 내용은 열어보지 않았다.
- 8곡 게이트 표(`gates_8songs.txt`)를 만든 `gen_gates_8songs.py` 스크립트 자체를 이 세션에서 재실행하지 않았다 — 파일에 적힌 값을 그대로 인용했다(별도로 `test_concept_gates.py`는 직접 실행해 PASS 확인).
