# SPEC-COPILOT-SONGCONFIRM-001 — 진행 기록

> 단계별 증거를 적는 자리. plan 단계는 §E.1 만 채우고 §E.2~§E.4 는 각 단계의 소유자가 채운다.

## §E.1 Plan-phase Audit-Ready Signal

- SPEC 작성 완료 2026-09-06 — `spec.md` · `plan.md` · `acceptance.md` (Tier M) + 이 파일. 카드 t273.
- SPEC ID 정규식 검사(Bash 실행): `ID="SPEC-COPILOT-SONGCONFIRM-001"; [[ "$ID" =~ ^SPEC(-[A-Z][A-Z0-9]*)+-[0-9]{3}$ ]] && echo PASS || echo FAIL` → `PASS`.
- **기준 트리**: 워크트리 `.claude/worktrees/agent-ab693b5114839dea5`, `git rev-parse --short HEAD` → **`f727e11`**(= main, 실브라우저 보고서의 기준과 같은 커밋). 인용한 모든 행 번호는 이 HEAD 에서 되읽었다.
- **예산**: REQ **16건**(REQ-SONGCONFIRM-001~016) / AC **16건**(AC-SONGCONFIRM-001~016). 둘 다 Tier M 상한 16 을 정확히 소진. 하위 ID 없음.
- **결함 재실측(2026-09-06, `f727e11`)**: ① `grep 'proposals|selected|sections' server/web/question.py` → 카드 빌더(`:139-215`)에만 등장, 파서 0건 ② `grep -rn '\.song_bpm\b\|_song_bpm' server --include='*.py' | grep -v /tests/` → `session.py:3781 · :10277 · :10293` 3행(초기화·대입·반환), 생산 판독자 0 ③ `prepare_songcue`(`tools.py:2550`)는 `call.arguments` 만 읽고, 스키마 `required`(`:9721`)에 `sections` 포함 ④ `build_timecode_handoff_card` 생산 호출자 0건(`grep -rn … | grep -v /tests/` → 정의 `question.py:231` 1행) ⑤ `analyse_song_audio` 는 `app.py:585` 가 `to_thread` 인자로 넘긴다(괄호 없는 참조라 `analyse_song_audio(` grep 은 0 이지만 생산 배선은 있다 — MUSICSYNC-001 §E.2 「M2 후속」과 일치).
- **통로 실측**: 세션→모델 `session.py:10399-10440` `_session_context_note` → `:10037` `handle_instruction(session_context=…)` → `runner.py:331-359`(`:357-358` 합성 `UserMessage`) · 세션→도구 `session.py:3795-3826` `build_toolset(… uploaded_sheet=_UploadedSheetView(self))` + `tools.py:1949-1971` 시그니처 + `:527-541` `UploadedSheetPort` + `:6405-6406` `None` 분기 + `:3591-3602` 읽기 투과 뷰 선례 · UI 답 형식 `ui/src/components/QuestionCard.tsx:17-24` `joinChosenLabels`(`", "` 결합) · `:167-170` 자유 입력.
- **하위 호환 실측**: 스키마 `required` 단언 시험 0건 · `'sections' must be` 리터럴 단언 시험 0건 · `_session_context_note() is None` 단언 `test_web_session.py:1013` · 미응답 갈래 `song_bpm.source == "default"` 단언 `test_web_song_audio.py:479-484`(D2 의 근거).
- **결정 6건 확정**(`plan.md §C` D1~D6): 라벨 왕복 대조 문법 · 불변 기록 + `_song_bpm` 무변경 · 재업로드 무효화 · `_session_context_note` 통로 · 명시 인자 우선 + 불일치 보고 + 스키마 `sections` 선택화 · 중립 이름 `S<n>` · `SongAnalysisPort` 읽기 투과 뷰. 결정 대기 **0건**.
- **선행 SPEC 대조**: MUSICSYNC-001(`status: completed`) 의 REQ-015(카드 스키마 무변경)·016(BPM→`MusicProfile`)·017(우선순위)은 재명세하지 않고 읽기만 한다. 그 SPEC 의 부채 2건(`HEAD.BPM` 접합 · 인계 카드 호출자)은 §D 범위 밖으로 명시.
- **미검증**: B1(중복 라벨의 실제 발생) · B2(`start_ms` 문자열 왕복 손실 0) · B3(`S<n>` 이 라이브러리 어휘 밖) · B7(제공자의 `required` 강제 여부) · B8(채택 구간 수 상한) — 전부 `plan.md §B`, 착수 시 재측정. 실브라우저 관측은 보고서 것이며 이 계획 회차가 다시 띄우지 않았다(콘솔 접촉 0).

## §E.2 Run-phase Evidence

_<pending run-phase>_

## §E.3 Run-phase Audit-Ready Signal

_<pending run-phase>_

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_
