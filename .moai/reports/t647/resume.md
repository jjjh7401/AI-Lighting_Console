✂──── 여기부터 복사 ────✂

ultrathink. SPEC-LDBARMAP-002 run 재개 (카드 t647). M3 부터 이어 간다.
applied lessons: lesson-moai-session-list-destroys-worktrees, lesson-enterworktree-bases-on-a-stale-origin, lesson-a-subagent-may-land-in-its-own-worktree, feedback-spawn-subagents-with-sonnet, feedback-kanban-lane-asks-lead-not-operator, feedback-report-lane-clear-readiness-on-card-close, feedback-summarize-in-plain-words-not-lane-chatter.

전제 검증 (순서대로):
1) 위치 확인: `pwd; git branch --show-current; git rev-parse --short HEAD; git status --short`. 경로는 `.claude/worktrees/t647`, 브랜치는 `WT-barmap-entry-impl`, 작업 트리는 깨끗해야 한다. HEAD 는 「중간 인계」 커밋이다.
2) 진입 직후 `uv sync --group dev` 를 묻지 말고 돌린다.
3) `git ls-remote --heads origin WT-barmap-entry-impl` 의 SHA 가 로컬 HEAD 와 같아야 한다.
4) 금지: `moai session list`(워크트리를 지운다). `moai todo`(레인은 집지 않는다). 세션 확인은 ListAgents.
5) 먼저 읽을 것: `.moai/specs/SPEC-LDBARMAP-002/progress.md` 의 §E.2 「중간 인계」 블록, `.moai/specs/SPEC-LDBARMAP-002/acceptance.md`, `.moai/docs/lane-protocol.md`.

끝난 것 (커밋):
- M1 합성 단계 6a54dc13 · 수정 ad671c5d, 637934e4
- M2 세션 진입 메서드 cd0dc342 · 후속 fb941a3d · 실패 표시 정책 faf915b9
- SPEC E5 5fc9319c, 4ca0585e (라벨은 성공 대 그 밖, 사유는 본문)
- 검증 (faf915b9 기준): 시험 4개 파일 137개 통과, ruff 통과, 추가된 줄 금지어 0건

남은 일 (이 순서):
1. M3: WS 프레임 bar_map_analyse. 허용 목록과 파서는 정수만 받고, bool·실수·문자열·null·없음은 거절한다. app 디스패치는 첨부 없음이면 error song_audio_missing, busy 면 busy, 그 밖엔 create_task + to_thread. 래퍼는 예외가 나면 non-success chat_response 를 한 개 보낸다(이미 보냈으면 보내지 않는다). 프로토콜 동결 목록 한 줄(test_prechk_tool.py, :1249 다음 줄, t551 주석 앞)과 AC-011 역방향 실행. 시험 AC-001·002·009·010·011·015(와이어 3경우). AC-005 스캔 목록에 두 파일을 더한다. 첫 커밋 후보: 첫 박 오프셋 거절 문구에서 repr(offset) 을 뺀다.
2. M4: AC-016 실제 곡 로컬 게이트. 원곡 /Users/studiox/Music/AI-Lighting_Console-listen/t505/LOVE ATTACK.mp3 는 존재한다. 저장소 밖 경로, skipif, 오프셋 1. 벽시계 시간을 기록한다(기준값 없음).
3. 검증: SPEC §D 1–8 (targeted·regression pytest, ruff, 오디오 파일 비커밋, console 0건, AC-016 로컬 출력, 변경 파일 목록 대조, 추가된 줄 고유값 훑기).
4. PR·CI·머지: WT-barmap-entry-impl → main, 머지 방식 merge. 허용 목록 확장(D3)은 감독 결정이므로 머지 판단은 리드에게 넘긴다. mergeable 을 먼저 읽고, CI 는 헤드 SHA 와 같이 읽는다.
5. sync: /moai sync SPEC-LDBARMAP-002. manager-docs 가 status completed 와 §E.4 를 한 커밋으로 올리고, sync-auditor 가 독립 판정한다. SPEC 정정 세 가지는 manager-spec 로 한꺼번에 반영하고 보고서에 목록으로 남긴다.

방침 (확정, 바꾸지 말 것):
- 객체 주소: 분석 실패의 화면 문구는 일반 문구 하나(_BAR_MAP_ENTRY_FAILED_TEXT). 원문 사유는 WARNING 로그(server.web.session). 거절 문구는 설계 문구다. 시험은 화면 사유에 0x 와 object at 이 없다는 것으로 단언한다.
- D1 (디스패치의 「D1」, SPEC 에서는 E5): 거절 사유 문장은 본문(text)에 싣고, summary 는 성공(「마디 지도 저장」)과 그 밖(「마디 지도 분석 거절」)을 가르는 고정 라벨이다. 근거: session.py 의 기존 응답 모양(저장 관문 거절 :9378-9385, 박자 격자 수정 거절 :9428 등 고정 라벨 13곳).
- 콘솔: 쓰기 0건(SPEC 접촉 0). 실기가 생기면 멈추고 리드에게 범위를 보고한 뒤, 「실행」 신호를 받은 뒤에만 한다.

SPEC 정정 세 가지 (sync 에서 한꺼번에, 보고서에 목록으로):
(a) REQ-LDBARENTRY-010, AC-LDBARENTRY-004 (5): 「bar_map 키 외 바이트 동일」 → 「bar_map 과 draft 표식 외 바이트 동일」.
(b) AC-LDBARENTRY-006 (다): 패치 대상은 analyze.py:229 가 아니라 bar_map.py 가 가져다 쓰는 이름(bar_map.py:36, :179).
(c) 전제 P13: 업로드가 지우는 것은 _song_analysis 뿐, _song_bpm 은 유지.

열린 항목: 로그가 파일에 남는지 앱 실행 설정을 확인한다. 콜드 스타트 첫 실행 약 41초(시험 한 개 60초 제한에 가깝다). plan-audit 3차 PASS(0.91) 해시는 본문 수정으로 달라졌다 — 재감사 여부는 리드 판단.

규칙: 구현은 서브에이전트(model sonnet, general-purpose, 워크트리 cwd 상속)에 맡기고, 디스크의 diff 와 시험 출력은 직접 확인한다. 워크트리에서는 상대경로만 쓴다. 커밋 메시지 끝줄은 🗿 MoAI. git add -A 금지. 증거는 .moai/reports/t647/ 에 쓰며, .gitignore 예외(t[0-9]*)로 그냥 add 된다.

✂──── 여기까지 복사 ────✂
