---
id: SPEC-COPILOT-SONGCONFIRM-001
title: "곡 분석 확정의 도달 — 사람이 확인한 구간과 BPM 이 모델과 도구에 닿는다"
version: "0.1.2"
status: completed
created: 2026-09-06
updated: 2026-09-06
author: manager-spec (card t273)
priority: P1
phase: "v1.8.1 target"
module: "server/web/question.py, server/web/session.py, server/orchestrator/tools.py (prepare_songcue · build_toolset), server/tests/"
lifecycle: spec-anchored
tags: "song-confirm, sections, bpm, session-context, prepare-songcue, production-caller-discipline, zero-console-contact, backward-compat"
tier: M
depends_on: [SPEC-COPILOT-MUSICSYNC-001]
---

# SPEC-COPILOT-SONGCONFIRM-001 — 곡 분석 확정의 도달

> **이 SPEC 이 닫는 구멍**: SPEC-COPILOT-MUSICSYNC-001 은 곡을 재고, 확인 카드를 띄우고, 사람의 답에서 BPM 을 확정하는 데까지 배달했다. 그런데 **확정된 것이 아무 데도 닿지 않는다.** 2026-09-06 실브라우저 검증(`reports/musicsync-browser-check-20260906.md`, 기준 main `f727e11`)과 같은 날 같은 트리에서의 실측이 셋을 나란히 보여 준다.
>
> 1. **구간 확정은 버려진다.** `parse_confirmed_bpm`(`server/web/question.py:264-285`)은 답에서 BPM 토큰만 읽는다. 체크박스로 고른 구간을 읽는 코드는 저장소 어디에도 없다 — `question.py` 에서 `proposals`·`selected`·`sections` 는 카드 **빌더**(`:158-215`)에만 나온다.
> 2. **확정된 BPM 은 아무도 읽지 않는다.** `grep -rn '\.song_bpm\b\|_song_bpm' server --include='*.py' | grep -v /tests/` → `session.py:3781`(초기화) · `:10277`(대입) · `:10293`(프로퍼티 반환) **3행뿐**. 생산 호출자 0건. 「부품이 초록이어도 경로는 안 이어졌다」의 정확한 형태다.
> 3. **`prepare_songcue` 는 확정을 볼 수 없다.** 도구 스키마(`server/orchestrator/tools.py:9647-9723`)는 `sections` 를 **필수**로 요구하고(`:9721`), 핸들러(`:2550`)는 `call.arguments` 밖의 어떤 세션 사실에도 닿지 않는다. 카드가 끝난 뒤 모델은 채팅에서 구간을 **다시 지어내야** 한다.
>
> 그리고 확정 고지(`session.py:10279-10288`)는 BPM 만 말한다. 운영자는 체크한 구간이 어떻게 됐는지도, 다음에 무엇을 말해야 하는지도 듣지 못한다(보고서 발견 3).
>
> **고치는 것은 기계가 아니라 배관이다.** 분석기·카드·BPM 해소는 옳게 동작한다. 이 SPEC 은 (a) 답에서 구간 선택을 **읽고**, (b) 확정을 세션에 **불변 기록으로 남기고**, (c) 그 기록을 **이미 있는 두 통로**(세션 문맥 주입 · 도구 포트)로 모델과 `prepare_songcue` 에 **닿게** 한다. 새 통로·새 UI·새 카드는 만들지 않는다.
>
> **콘솔 접촉 0.** 어느 마일스톤도 콘솔에 아무것도 보내지 않는다. 전 인수 기준이 가짜 포트 위에서 판정된다(REQ-SONGCONFIRM-014).

## HISTORY

| 일자 | 버전 | 변경 | 근거 |
|---|---|---|---|
| 2026-09-06 | 0.1.0 | 최초 초안. 카드 t273. 실측 기준 HEAD `f727e11`(워크트리 `agent-ab693b5114839dea5`, main 과 동일 커밋). REQ 16 · AC 16(Tier M 상한 정확 소진). | `reports/musicsync-browser-check-20260906.md` 발견 3 + 같은 날 실측 3건(위 인용문) |
| 2026-09-06 | 0.1.1 | plan-audit 1차(FAIL 0.80) 반영 — D1 diff 기준을 `merge-base` 로·슬롯 술어를 밑줄 없는 이름으로(형제 POOLEMPTY-001 의 들어올리기와 공존) · D2 라벨 **완전 일치**(항목 단위) + AC-005 (d) 접두 충돌 대조군 · D3 AC-014 ④⑤ 주석 제외 grep · D4 REQ-001/006 ↔ AC-001/002 · D5 앵커 · D8 AC-007 리터럴 고정 · D10 `related_specs` 제거 | `.moai/reports/plan-audit/SPEC-COPILOT-SONGCONFIRM-001-review-1.md` |
| 2026-09-06 | 0.1.2 | plan-audit 2차 PASS 0.96 잔여 반영 — N1 diff 술어를 변경 행(`-U0`, `^[+-]`)으로 · N2 §E 보존 경계에 두 이름 병기 | `.moai/reports/plan-audit/SPEC-COPILOT-SONGCONFIRM-001-review-2.md` |

---

## A. 배경

### A.1 지금 무엇이 이미 건강한가 (건드리지 않는다)

| 절 | 상태 | 근거 (HEAD `f727e11` 실측) |
|---|---|---|
| 업로드 → 분석 → 카드 → 답 → BPM 확정 사슬 | ✅ 실브라우저 끝까지 동작 | 보고서 §관측 표 6행 전부 OK · `app.py:556-590` 분석 디스패치 · `:614-632` 답 디스패치 |
| 확인 카드의 모양 | ✅ 오늘 스키마 그대로 | `question.py:158-215` — `multi=True`(`:214`), 구간당 옵션 1개, 라벨 `m:ss–m:ss · D<n>`(`:181-183`), `selected=True` 기본(`:150`) |
| 다중 선택 답의 와이어 형식 | ✅ 정의돼 있다 | `ui/src/components/QuestionCard.tsx:17-24` `joinChosenLabels` — 체크된 옵션의 **라벨을 `", "` 로 이어** 하나의 문자열로 보낸다(`question.py:92-93` 독스트링과 일치). 자유 입력은 `:167-170` 에서 타이핑한 글 그대로 |
| BPM 답 파서 | ✅ 옳다, 토큰 잠금 | `question.py:264-285` — `BPM <숫자>` 토큰만 읽고, 없으면 측정값 그대로 확정, 미응답·자유입력 표식은 `None` |
| BPM 정본 해소 | ✅ | `server/design/profile.py:389-450` `resolve_bpm` · `BpmResolution`(`:350-363`) |
| 세션 사실이 모델에 닿는 통로 | ✅ **이미 있다** | `session.py:10399-10440` `_session_context_note` → `:10037` `handle_instruction(session_context=…)` → `runner.py:357-358` 합성 `UserMessage` 로 지시문 **앞**에 삽입. 선례 3건(마지막 룩 대상 · 레이아웃 간격 · Vectorworks 첨부) |
| 세션 보관물이 도구에 닿는 통로 | ✅ **이미 있다** | `build_toolset(… uploaded_sheet=_UploadedSheetView(self))`(`session.py:3826`) — 읽기 투과 뷰(`_LayoutImageUploadView` `:3591-3602` 의 설명이 이유를 적는다) + 도구 쪽 `Protocol`(`tools.py:527-541` `UploadedSheetPort`) + 핸들러의 `None` 분기(`:6405-6406`) |
| 타임코드 슬롯 판정 | ✅ 남의 소유 | `tools.py` `_timecode_slot_verdict` — 카드 t270 = SPEC-COPILOT-POOLEMPTY-001 소유(그 SPEC 의 REQ-016 이 모듈 수준 `timecode_slot_verdict` 로 들어올린다). **이 SPEC 은 손대지 않는다**; 두 SPEC 은 독립이고 나중에 착지하는 쪽이 rebase 한다 |
| 구간 확정 판독 | ❌ **없다** | `question.py` 전수 — 파서 0건 |
| `song_bpm` 생산 판독자 | ❌ **0건** | 위 인용문 2 |
| `prepare_songcue` 의 세션 접근 | ❌ **없다** | `tools.py:2550-2567` — 인자만 읽는다 |

### A.2 답의 형식이 문법을 정한다 — 결정 사항

카드가 UI 로 나갈 때 `QuestionRequest.to_dict()`(`question.py:96-111`)가 라벨을 그대로 싣고, 사람이 「확인」을 누르면 **체크된 라벨들이 `", "` 로 이어져** 돌아온다(`QuestionCard.tsx:17-24`). 즉 서버가 만든 라벨 문자열이 **그대로 되돌아온다.** 그러므로 구간 선택 판독은 새 문법이 아니라 **라벨 왕복 대조**다 — 카드에 있던 라벨이 답에 있으면 채택, 없으면 제외. 자유 입력(`:167-170`)은 라벨을 담지 않으므로 「카드를 있는 그대로 받아들인 것」으로 읽는다. 이것은 `parse_confirmed_bpm` 의 셋째 규칙(「그 밖에는 측정값을 그대로 확정」, `:272-273`)과 **같은 원칙**이다.

산문으로 구간을 고치는 문법(「두 번째는 빼고 1:05 에서 나눠 줘」)은 이 SPEC 이 **만들지 않는다**(§D). 이유는 `plan.md §C` D1 에 있다.

### A.3 두 통로를 재사용하고 셋째를 만들지 않는다

모델에는 `_session_context_note` 한 줄이 추가되고, 도구에는 `build_toolset` 키워드 인자 하나와 `Protocol` 하나가 추가된다. 둘 다 오늘 형제들이 지나는 자리다. 기록이 없을 때 두 통로는 **오늘과 바이트 동일**하다 — 그것이 하위 호환의 정의다(REQ-SONGCONFIRM-015).

---

## B. 요구사항 (GEARS)

> 요구 번호는 `001`부터 `016`까지 연속이며 공백이 없다. Tier M 상한(16)을 정확히 소진한다.

### B.1 확정 기록과 답 판독 (M1)

- **REQ-SONGCONFIRM-001** [Ubiquitous] — the 세션 **shall** 확정된 곡 분석을 **불변 기록** 하나로 보관한다. 기록은 정체성(원본 오디오의 `sha256` · 파일명 · 확정 시각), 확정 BPM 해소 결과(`BpmResolution`), 구간 목록(구간마다 `index` · 카드 라벨 · `start_ms` · `end_ms` · `d_level` · `selected`)을 담으며, 채택 구간과 제외 개수를 파생값으로 내준다. 기록은 세션 안에 산다 — 프로세스를 넘어 저장하지 않는다.
- **REQ-SONGCONFIRM-002** [Event-driven] — **When** 사람이 확인 카드에 답하고 그 답이 미응답(`UNANSWERED`)도 자유입력 표식(`ANSWER_FREEFORM`)도 아니면, the 세션 **shall** 그 답과 카드의 제안 목록으로부터 기록을 만들어 보관한다. 미응답·자유입력 표식이면 기록을 만들지 않으며, 오늘의 BPM 대입(`session.py:10277`)은 어느 갈래에서도 변하지 않는다.
- **REQ-SONGCONFIRM-003** [Ubiquitous] — the 구간 답 파서 **shall** `parse_confirmed_bpm` 과 같은 자리(`server/web/question.py`)에 있는 순수 함수이며, 카드의 제안 목록과 답 문자열을 받아 규칙 셋으로 판정한다 — ① 답에 카드 라벨이 **하나 이상** 들어 있으면, 들어 있는 라벨의 구간은 채택하고 없는 라벨의 구간은 제외한다 ② 답에 카드 라벨이 **하나도** 없으면 모든 제안을 채택한다(카드를 있는 그대로 받아들인 것) ③ 미응답·자유입력 표식·문자열 아님이면 판정 없음. 라벨 대조는 답을 `", "` 로 나눈 **항목 각각과 라벨의 완전 일치**(양끝 공백 제거 뒤 `==`)로 하며, 부분문자열 포함은 대조가 아니다 — 라벨의 일부(시각 하나, `D` 등급 하나)도, 다른 라벨을 접두로 품은 긴 라벨(`1:00–1:15 · D1` ⊂ `11:00–11:15 · D1`)도 그 라벨을 채택하지 않는다.
- **REQ-SONGCONFIRM-004** [Unwanted] — the 구간 답 파서 **shall not** 카드에 없던 구간을 만들어 내거나, 산문(이름·시각·「빼 줘」류)을 구간 편집으로 읽는다. 산문은 BPM 토큰 판독(`parse_confirmed_bpm`)에만 영향을 주며 구간에는 규칙 ②가 적용된다.
- **REQ-SONGCONFIRM-005** [Event-driven] — **When** 새 곡 오디오가 업로드되면, the 세션 **shall** 보관 중인 확정 기록을 무효화하고(기록 없음 상태로), 기록이 **있었던 경우에만** 업로드 고지에 무효화 사실을 한 문장으로 덧붙인다. 기록이 없던 경우의 업로드 고지는 오늘 문자열과 바이트 동일하다.
- **REQ-SONGCONFIRM-006** [Ubiquitous] — the 세션 **shall** 확정 기록을 읽기 전용 프로퍼티로 내주며, 기록이 있을 때 그 기록의 BPM 해소 결과는 `song_bpm` 프로퍼티가 돌려주는 객체와 **같은 객체**다(두 정본이 생기지 않는다).

### B.2 도달 — 모델 · 도구 · 운영자 (M2)

- **REQ-SONGCONFIRM-007** [State-driven] — **While** 확정 기록이 있으면, the 세션 **shall** 그 요약을 **기존** 세션 문맥 통로(`_session_context_note` → `handle_instruction(session_context=…)` → 합성 `UserMessage`)로 모델에 주입한다. 둘째 통로를 만들지 않는다. **While** 기록이 없으면 그 통로의 산출은 오늘과 바이트 동일하다.
- **REQ-SONGCONFIRM-008** [Ubiquitous] — the 주입 요약 **shall** 한 문단으로 파일명 · `sha256` 앞 8자 · BPM 과 채택 출처 · 채택 구간 전부(`index` · `m:ss–m:ss` · `D<n>`) · 제외 개수를 담고, 모델에게 두 가지를 지시한다 — 운영자가 이 곡의 큐 리스트를 요청하면 `prepare_songcue` 를 **`sections` 없이** 불러 확정 구간을 쓰라는 것, `timecode_number` 는 여전히 운영자에게 받으라는 것.
- **REQ-SONGCONFIRM-009** [Event-driven] — **When** `prepare_songcue` 가 `sections` 인자 **없이** 불리고 확정 기록이 있으면, the 도구 **shall** 채택 구간을 기본값으로 쓴다 — 구간 이름은 룩 라이브러리의 구간 어휘에 **속하지 않는** 중립 ASCII 이름, 시작은 `start_ms` 를 손실 없이 옮긴 값, dynamics 는 `d_level` — 그리고 도구 결과에 `sections_source: "confirmed_analysis"` 를 싣는다. 이후 경로(`parse_sections` · 룩 매핑 · 번들 · 슬롯 판정 · `run_commands`)는 오늘 그대로 지난다.
- **REQ-SONGCONFIRM-010** [Event-driven] — **When** `sections` 인자와 확정 기록이 **둘 다** 있으면, the 도구 **shall** 명시 인자를 채택하고 결과에 `sections_source: "explicit"` 와 **불일치 보고**(두 목록의 구간 수, 같은 `index` 의 시작 시각 쌍, 일치 여부)를 싣는다. 명시 인자를 조용히 버리거나 두 목록을 섞지 않는다.
- **REQ-SONGCONFIRM-011** [Event-driven] — **When** `sections` 인자가 없고 확정 기록도 없으면, the 도구 **shall** 오늘의 오류(`'sections' must be a non-empty array of song sections`)를 **바이트 동일**하게 돌려준다. 도구 스키마는 `sections` 를 선택 인자로 바꾸고 그 설명에 기본값 규칙을 적되, `song_title` · `genre` · `timecode_number` 는 필수로 남는다.
- **REQ-SONGCONFIRM-012** [Unwanted] — the 본 SPEC 의 구현 **shall not** `timecode_number` 의 호출자 공급 규칙, 슬롯 판정 함수(`_timecode_slot_verdict`, 또는 SPEC-COPILOT-POOLEMPTY-001 이 착지한 뒤의 `timecode_slot_verdict`)의 본문, 슬롯 판정의 호출 위치를 바꾼다. 타임코드 슬롯 판정은 SPEC-COPILOT-POOLEMPTY-001(카드 t270)의 소유다. 판정 술어는 이름의 밑줄 유무와 무관하게 `timecode_slot_verdict` 를 담은 diff 행 0 이다.
- **REQ-SONGCONFIRM-013** [Event-driven] — **When** 확정이 끝나 고지를 내면, the 확정 고지 **shall** BPM 문장에 더해 구간 결과(채택 N 건 · 제외 M 건)와 **운영자 말로 적은 다음 단계** 한 문장을 담는다. 기록이 만들어지지 않은 갈래(미응답 등)의 고지는 오늘 문자열과 바이트 동일하다.

### B.3 횡단 규율

- **REQ-SONGCONFIRM-014** [Ubiquitous] — the 본 SPEC 의 모든 마일스톤 **shall** 콘솔 접촉 0건이다 — 쓰기 0 · 조회 0. 전 인수 기준은 가짜 포트로 판정되며, `server/safety/**` · `server/audio/**` · `server/looks/**` · `server/design/**` · `ui/src/**` · `src-tauri/**` 는 무변경이다.
- **REQ-SONGCONFIRM-015** [Ubiquitous] — the 본 SPEC 의 구현 **shall** 확정 기록이 없을 때 모든 경로를 오늘과 **바이트 동일**하게 유지한다. 기존 시험 파일 `test_song_confirm_card.py` · `test_web_song_audio.py` · `test_songcue_tool.py` · `test_web_session.py` · `test_runner_self_correction.py` 는 **수정 없이** 초록이며, 새 시험은 새 파일에 산다.
- **REQ-SONGCONFIRM-016** [Ubiquitous] — the 본 SPEC 이 만드는 모든 새 진입점(구간 파서 · 기록 생성 · 읽기 투과 뷰 · 도구 기본값 분기) **shall** 시험이 아닌 **생산 호출자를 하나 이상** 갖고, `song_bpm` 프로퍼티는 생산 판독자를 하나 이상 얻으며, 그 사실은 grep 으로 판정된다. 완료 보고는 5절 형식(주장 · 증거 · 기준 귀속 · 미검증 · 잔여 위험)을 갖춘다.

---

## C. 성공 기준

| # | 기준 | 판정 |
|---|---|---|
| S1 | 체크를 푼 구간은 제외되고 남긴 구간은 채택된다 — 라벨 왕복 대조로 | AC-SONGCONFIRM-001 · 002 · 005 |
| S2 | 자유 입력으로 BPM 만 고쳐도 구간은 카드대로 채택된다 | AC-SONGCONFIRM-003 |
| S3 | 답이 없으면 기록도 없고, 오늘의 BPM 거동은 그대로다 | AC-SONGCONFIRM-004 |
| S4 | 다른 곡을 올리면 이전 확정은 무효가 되고 그 사실이 들린다 | AC-SONGCONFIRM-006 |
| S5 | 운영자가 확정 뒤에 구간 결과와 다음 할 말을 듣는다 | AC-SONGCONFIRM-007 |
| S6 | 모델이 확정을 **기존 통로로** 받는다 | AC-SONGCONFIRM-008 · 009 |
| S7 | `prepare_songcue` 가 `sections` 없이 확정 구간으로 번들을 만든다 | AC-SONGCONFIRM-010 |
| S8 | 명시 인자가 이기고 불일치가 보고된다 | AC-SONGCONFIRM-011 |
| S9 | 기록이 없으면 오늘과 바이트 동일하다 | AC-SONGCONFIRM-012 · 016 |
| S10 | 새 진입점마다 생산 호출자가 있고 `song_bpm` 이 읽힌다 | AC-SONGCONFIRM-014 |
| S11 | 콘솔 접촉 0 · 보존 경계 무변경 · 슬롯 판정 무변경 | AC-SONGCONFIRM-013 · 015 |

---

## D. 범위 밖 (Out of Scope)

### Out of Scope — 산문 구간 편집 문법

- 「두 번째 구간은 빼 줘」·「1:05 에서 나눠」 같은 자유 문장을 구간 편집으로 읽는 문법은 만들지 않는다.
- 카드에 없던 구간(경계 이동 · 분할 · 병합)은 어떤 답으로도 생기지 않는다(REQ-SONGCONFIRM-004).
- 고치고 싶으면 「분석」을 다시 누르거나, 큐 리스트 요청 때 `sections` 를 명시한다(REQ-SONGCONFIRM-010). 근거는 `plan.md §C` D1.

### Out of Scope — 새 UI 버튼·새 카드·와이어 변경

- 「이 구간으로 큐 만들기」 버튼, 확정 후 요약 카드, 새 메시지 타입은 만들지 않는다. `ui/src/**` 는 무변경이다.
- 다음 단계는 **고지 문장**으로 안내한다(REQ-SONGCONFIRM-013). 버튼이 필요하다고 판단되면 별도 카드이며, `plan.md §G` 에 선택 항목으로만 적는다.
- `QuestionRequest` 스키마(`question.py:70-111`)는 한 글자도 바뀌지 않는다.

### Out of Scope — 시트 `HEAD.BPM` 과 분석의 접합

- MUSICSYNC-001 이 부채로 기록한 「M1 임포터가 읽은 `HEAD.BPM` 을 `analyse_song_audio(sheet_bpm=…)` 로 넘기는 호출자」(`SPEC-COPILOT-MUSICSYNC-001/progress.md:289-293`)는 이 SPEC 이 배선하지 않는다.
- 이 SPEC 은 이미 해소된 `BpmResolution` 을 **읽기만** 한다.
- 별도 카드다.

### Out of Scope — 타임코드 인계 카드의 생산 호출자

- `build_timecode_handoff_card`(`question.py:231`)의 생산 호출자는 HEAD `f727e11` 에서도 0건이며(같은 날 grep), 이 SPEC 은 그 자리를 배선하지 않는다.
- `prepare_songcue` 결과의 `timing.operator_handoff` 페이로드(`tools.py:2788-2795`)는 무변경이다.
- 별도 카드다.

### Out of Scope — 타임코드 슬롯 판정과 `timecode_number` 자동 선택

- 슬롯 판정 함수(`_timecode_slot_verdict` → POOLEMPTY-001 착지 뒤 `timecode_slot_verdict`)의 `childCount 0 → unknown` 규칙은 SPEC-COPILOT-POOLEMPTY-001(카드 t270)이 소유한다.
- `timecode_number` 를 확정 기록이나 모델이 대신 고르는 일은 없다(REQ-SONGCONFIRM-012).
- 도구 스키마에서 `timecode_number` 는 필수로 남는다.

### Out of Scope — 곡 설계 인터뷰의 BPM 정규식 대체

- `_song_design_interview` 가 채팅 정규식(`session.py:387` `_SONG_BPM`, `:7243-7248`)으로 BPM 을 읽는 자리를 확정 기록으로 바꾸지 않는다.
- 그 경로는 콘솔 쓰기를 동반하는 별도 흐름이며, 기본값을 바꾸면 이 SPEC 의 콘솔 접촉 0 규율 밖으로 나간다.
- 후속 카드 후보로 `plan.md §G` 에 적는다.

### Out of Scope — 확정 기록의 세션 밖 보존

- 앱 재시작·새 연결을 넘어 기록을 파일이나 콘솔에 남기지 않는다.
- `history_restore`(`app.py:591-596`)는 기록을 되살리지 않는다.
- 세션이 끝나면 기록도 끝난다 — 오디오 첨부(`SongAudioUpload`)와 같은 수명이다.

---

## E. 제약

- **개발 방식**: TDD(`.moai/config/sections/quality.yaml` `constitution.development_mode`). 구간 파서는 순수 함수라 RED 를 라이브 없이 만든다.
- **콘솔 접촉**: 0건. 전 마일스톤(REQ-SONGCONFIRM-014). 시험은 `_AnsweringChannel`(`test_web_song_audio.py:420-440`)과 `test_songcue_tool.py` 의 가짜 포트 형태를 그대로 쓴다.
- **하위 호환**: 기록이 없을 때 바이트 동일(REQ-SONGCONFIRM-015). 기존 다섯 시험 파일 무수정.
- **보존 경계**: `server/safety/**` · `server/audio/**` · `server/looks/**` · `server/design/**` · `ui/src/**` · `src-tauri/**` 무변경. `tools.py` 안에서는 슬롯 판정 함수(`_timecode_slot_verdict` / POOLEMPTY-001 착지 뒤 `timecode_slot_verdict`) 본문 무변경.
- **층 경계**: `server/orchestrator/tools.py` 는 `server.web` 을 import 하지 않는다 — 형제 포트들(`VectorworksUploadPort` · `LayoutImageUploadPort` · `UploadedSheetPort`, `tools.py:507-541`)처럼 구조적 `Protocol` 로 받는다.
- **BPM 정본**: 이 SPEC 은 `resolve_bpm` 의 결과를 읽을 뿐 우선순위를 다시 정하지 않는다(MUSICSYNC-001 `plan.md §C` 결정 3 유지).
- **생산 호출자 규율**: 새 진입점마다 grep 으로 생산 호출자 1건 이상(REQ-SONGCONFIRM-016). 시험만 부르는 경로는 배달이 아니다.
- **선행 SPEC**: SPEC-COPILOT-MUSICSYNC-001(`status: completed`, 네 마일스톤 main 머지 완료). 본 SPEC 은 그 산출물을 전제로 하며 재명세하지 않는다.

---

## F. 교차 참조

`plan.md` · `acceptance.md` · `progress.md` · `reports/musicsync-browser-check-20260906.md`(주 체크아웃) · `SPEC-COPILOT-MUSICSYNC-001/{spec,acceptance,progress}.md` · `SPEC-COPILOT-SONGCUE-001` · `.claude/rules/moai/core/verification-claim-integrity.md` · 메모리 교훈 「부품이 초록이어도 경로는 안 이어졌다」
