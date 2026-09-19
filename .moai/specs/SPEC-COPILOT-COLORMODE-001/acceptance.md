# SPEC-COPILOT-COLORMODE-001 — 인수 기준

모든 AC는 pytest 또는 vitest로 기계 판정 가능하다. Given-When-Then 형식이며, 이 절은 검증 계층이다 — GEARS 요구사항(spec.md §3)을 다시 쓰지 않는다. 각 AC 헤딩은 이 AC가 검증하는 REQ ID를 명시한다(spec.md §3 말미 REQ→AC 추적 표와 상호 대응).

## AC-COLORMODE-001 — 정확히 3옵션, 기본이 첫 번째 (REQ-COLORMODE-001, 002)

- **Given** `Q2B_COLOR_USAGE` 스텝의 질문 카드를 `build_question`으로 생성했을 때
- **When** 카드의 `options` 튜플을 검사하면
- **Then** 길이가 정확히 3이고, `options[0].value == "modulate"`, `options[1].value == "single"`, `options[2].value == "per_chorus"`이며 `options[0].label`에 "기본"이 포함된다.
- 판정: `server/tests/test_design_interview.py::TestQ2bColorUsageOptions`

## AC-COLORMODE-002 — 공백 답변은 confirmed=True + SOURCE_DEFAULT_ACCEPTED (REQ-COLORMODE-003)

- **Given** `Q2B_COLOR_USAGE`가 현재 스텝인 `DirectorInterview`
- **When** `submit_answer(None)` 또는 `submit_answer("")`를 호출하면
- **Then** 반환된 `AnswerRecord`는 `value == "modulate"`, `confirmed is True`, `source == SOURCE_DEFAULT_ACCEPTED`다.
- 판정: `server/tests/test_design_interview.py` 신규 케이스

## AC-COLORMODE-003 — 기본값 수용이 재질의 카드를 만들지 않는다 (REQ-COLORMODE-010)

- **Given** Q2B가 default-accepted 경로로 답해진 `UnifiedSongLightingPlan.director_decisions` 항목
- **When** `song_cue_composer._requery_requirements(plan)`를 호출하면
- **Then** 반환된 요구사항 튜플에 `axis == "color_usage"`인 항목이 없다.
- 판정: `server/tests/test_web_session.py` 또는 `server/tests/test_song_cue_composer_requery.py`(존재하는 재질의 시험 파일)에 신규 케이스

## AC-COLORMODE-004 — 명시적 옵션·자유 텍스트가 세 값 모두로 매핑된다 (REQ-COLORMODE-002, 005)

- **Given** Q2B가 현재 스텝
- **When** 옵션 라벨을 그대로 답하거나, "단색으로"/"메인 컬러 변조"/"후렴마다 다른 색"류 자유 텍스트를 답하면
- **Then** 각각 `value`가 `"single"`/`"modulate"`/`"per_chorus"`로 해석되고 `confirmed is True`, `source`는 `SOURCE_OPTION` 또는 `SOURCE_FREE_TEXT`다.
- 판정: `server/tests/test_design_interview.py` 신규 파라미터화 케이스(3값 × 2경로)

## AC-COLORMODE-005 — 해석 불가 자유 텍스트는 재질의 (REQ-COLORMODE-006)

- **Given** Q2B가 현재 스텝
- **When** 세 키워드 그룹 어디에도 속하지 않는 자유 텍스트를 답하면
- **Then** `submit_answer`가 `UnresolvedAnswer`를 반환하고 `current_step`은 여전히 `Q2B_COLOR_USAGE`다(카드가 진행하지 않는다).
- 판정: `server/tests/test_design_interview.py::TestUnresolvedFreeTextReAsks` 패턴 확장

## AC-COLORMODE-006 — "Q3 다시"는 여전히 Q3_CLIMAX를 재시작한다 (REQ-COLORMODE-007)

- **Given** Q2B 삽입 이후의 `STEP_ORDER`(6단계)
- **When** `_song_run_interview` 루프 도중 답변으로 "Q3 다시"가 들어오면
- **Then** `interview.restart_from`이 `Q3_CLIMAX`로 호출되고, Q1/Q2/Q2B의 기존 답변은 보존된다.
- 판정: `server/tests/test_web_session.py::TestSongDesignInterviewSession` 신규 케이스(회귀 — Q2B 삽입 전과 동일한 라우팅)

## AC-COLORMODE-007 — "Q2B 다시"가 색 운용 스텝을 재시작한다 (REQ-COLORMODE-008)

- **Given** Q2B가 이미 답해진 상태에서 이후 스텝까지 진행된 인터뷰
- **When** 답변으로 "Q2B 다시" 또는 "색 운용 다시"가 들어오면
- **Then** `current_step`이 `Q2B_COLOR_USAGE`로 되돌아가고, Q1/Q2 답변은 보존되며 Q2B 이후 답변은 폐기된다.
- 판정: `server/tests/test_web_session.py` 신규 케이스

## AC-COLORMODE-008 — 페이로드 `director_decisions`에 color_usage 항목이 실린다 (REQ-COLORMODE-009, 015)

- **Given** Q2B에 답한 완주된 인터뷰로 만들어진 타임라인 페이로드
- **When** `director_decisions` 리스트를 검사하면
- **Then** `{step: "Q2B_COLOR_USAGE", axis: "color_usage", value: <응답값>, confirmed: <bool>, source: <str>}` 모양의 항목이 정확히 하나 존재한다. (이 검사가 통과하려면 `DirectorDecision.__post_init__`의 `_validate_axis`가 `"color_usage"`를 유효한 축으로 인정해야 하므로, REQ-015의 `DecisionAxis`/`_AXES` 확장도 암묵적으로 함께 검증된다.)
- 판정: `server/tests/test_song_timeline_decision_sources.py` 신규 케이스

## AC-COLORMODE-009 — 분석 요약이 세 모드 각각을 설명한다 (REQ-COLORMODE-011)

- **Given** `color_usage` 축이 `"modulate"`/`"single"`/`"per_chorus"` 각각으로 설정된 `SongTimelineView` fixture 세 개
- **When** `buildColorLine(timeline)`을 호출하면
- **Then** 반환된 `text`에 각 모드에 대응하는 한국어 설명 절이 포함되고, 기존 팔레트 문장(`감독 지정(...)`)은 그대로 유지된다.
- 판정: `ui/src/components/analysisSummary.test.ts` 신규 케이스 3개

## AC-COLORMODE-010 — 기본값 수용 마커가 표시된다 (REQ-COLORMODE-011)

- **Given** `color_usage` 결정의 `source`가 default-accepted인 fixture
- **When** `buildColorLine(timeline)`을 호출하면
- **Then** 반환된 `text`에 "(기본값 수용)" 문자열이 포함된다.
- 판정: `ui/src/components/analysisSummary.test.ts` 신규 케이스

## AC-COLORMODE-011 — modulate는 기존 fixture와 바이트 동일 (REQ-COLORMODE-012)

- **Given** `color_usage == "modulate"`(기본)로 설정된, t402 특성화 시험이 이미 쓰는 것과 동일한 구간 fixture
- **When** `_section_palette_choice`를 새 시그니처(color_usage 파라미터 포함)로 호출하면
- **Then** 반환되는 팔레트 튜플·출처·웨이트 라벨이 이 SPEC 이전 동작과 바이트 단위로 동일하다.
- 판정: `server/tests/test_song_color_usage_t404.py::test_modulate_is_byte_identical_to_pre_spec`

## AC-COLORMODE-012 — single은 palette_mode 해소 결과를 모든 회차에서 그대로 반환 (REQ-COLORMODE-013)

- **Given** `color_usage == "single"`, `palette_mode`가 기본(profile 팔레트 사용)인 여러 회차(occurrence 1~4)의 chorus 역할 구간들
- **When** `_section_palette_choice`를 각 회차에 대해 호출하면
- **Then** 매 호출의 반환 팔레트가 Q2 base 팔레트(`profile.palette or color_tendency`)와 동일하고(`_arc_palette` 미적용), 출처 라벨이 `"section_single"`류로 구분된다.
- **Given** (추가 케이스, plan-audit D4) `color_usage == "single"`, `palette_mode == "concept"`이고 `concept_colors`가 비어 있지 않은 chorus 역할 구간
- **When** `_section_palette_choice`를 호출하면
- **Then** 반환 팔레트가 Q2 base가 아니라 `concept_colors`(그 구간에서 `palette_mode` 충돌 해소가 실제로 만들어낸 base)와 동일하다 — `single`이 `palette_mode` 해소를 우회하지 않고 그 결과를 그대로 통과시킴을 증명한다.
- 판정: `server/tests/test_song_color_usage_t404.py::test_single_returns_base_everywhere` + `test_single_returns_concept_base_when_palette_mode_is_concept`

## AC-COLORMODE-013 — per_chorus는 연속 후렴에서 서로 다른 악센트를 낸다 (REQ-COLORMODE-014)

- **Given** `color_usage == "per_chorus"`, chorus 역할의 연속 회차 3개 이상(occurrence 1,2,3,...)
- **When** 각 회차에 대해 `_section_palette_choice`를 호출하면
- **Then** 인접한 두 회차(occurrence N, N+1)의 악센트 색이 서로 다르며, 매 회차 반환 팔레트의 첫 칸(`[0]`)은 항상 primary(`base[0]`)와 같다.
- **Given** (경계 케이스, plan-audit D6) `color_usage == "per_chorus"`, chorus 역할의 회차가 정확히 1개뿐인 곡
- **When** 그 유일한 회차에 대해 `_section_palette_choice`를 호출하면
- **Then** 반환값이 같은 fixture·같은 occurrence에서 `color_usage == "modulate"`로 호출했을 때의 반환값과 동일하다(비교할 이전 회차가 없으므로 사다리가 개입하지 않는다).
- 판정: `server/tests/test_song_color_usage_t404.py::test_per_chorus_consecutive_accents_differ` + `test_per_chorus_single_occurrence_matches_modulate`

## AC-COLORMODE-014 — 전곡 인터뷰 e2e가 7장 카드를 낸다 (REQ-COLORMODE-001)

- **Given** `test_full_choice_flow_previews_before_any_write_and_asks_for_approval`과 동일한 픽스처 브리프
- **When** 6개 문항(Q1~Q5 + Q2B)에 모두 답하면
- **Then** `channel.asked`의 길이가 7이고(6문항 + 리뷰 카드), 세 번째 카드(`asked[2]`)의 `prompt`가 Q2B 색 운용 문항이다.
- 판정: `server/tests/test_web_session.py::TestSongDesignInterviewSession` 갱신된 케이스

## AC-COLORMODE-015 — "Q2 다시"가 Q2B 답변도 함께 폐기한다 (REQ-COLORMODE-016)

- **Given** Q1~Q2B까지 답변을 마친 `DirectorInterview`(Q2B는 명시적 옵션 답변, default-accepted 아님)
- **When** `interview.restart_from(Q2_PALETTE)`를 호출하면
- **Then** `interview.answers`에 `Q2B_COLOR_USAGE` 키가 더 이상 존재하지 않고, `interview.current_step == Q2_PALETTE`다.
- **Given** 위 상태에서 Q2를 다시 답변하면
- **When** 다음 카드를 요청하면(`build_current_card` 또는 동등 호출)
- **Then** 그 카드가 다시 `Q2B_COLOR_USAGE`의 질문 카드다(감독이 Q2B를 다시 확인받는다).
- 판정: `server/tests/test_design_interview.py::TestPartialRestart` 확장 케이스 (신규: Q2 재시작이 Q2B를 폐기함을 증명)

## AC-COLORMODE-016 — Q2B 이외 스텝의 공백-답변 회귀 (REQ-COLORMODE-004)

- **Given** `Q1_CONCEPT`(또는 `Q2_PALETTE`/`Q3_CLIMAX`/`Q4_SPATIAL_STORY`/`Q5_TEXTURE`)가 현재 스텝인 `DirectorInterview`
- **When** `submit_answer(None)`을 호출하면
- **Then** 반환된 `AnswerRecord`는 `confirmed is False`, `source == SOURCE_AUTO_DRAFT`다 — Q2B_COLOR_USAGE 삽입 이전과 바이트 동일한 동작이며, `SOURCE_DEFAULT_ACCEPTED`는 어떤 값으로도 나타나지 않는다.
- 판정: `server/tests/test_design_interview.py::TestNoAnswerAutoDraft` 확장 케이스(Q1/Q3/Q4/Q5 파라미터화, Q2B 삽입 후 회귀 확인)

## 정의역 밖 시나리오 (참고, 신규 AC 아님)

- 기존 t402/t403/t405/t406 시험은 `color_usage` 파라미터를 명시하지 않는 호출부에서 기본값 `"modulate"`로 그대로 초록이어야 한다 — AC-COLORMODE-011의 재확인이며 회귀 게이트로 취급한다.
