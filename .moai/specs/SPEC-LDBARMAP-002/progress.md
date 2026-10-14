# SPEC-LDBARMAP-002 — Progress

## §E.1 Plan-phase Audit-Ready Signal

- plan_status: audit-ready
- plan_complete_at: 2026-10-14
- 작성 카드: t638. 입력과 읽은 줄은 `spec.md` §3 전제표에 있다.
- Tier: M (`spec.md` §0 근거) — REQ 16개·AC 16개, Tier M 상한(각 16개)에 정확히 닿는다.
- 자체 점검(plan-audit 전):
  - SPEC ID 정규식: Bash 실행 `ID="SPEC-LDBARMAP-002"; [[ "$ID" =~ ^SPEC(-[A-Z][A-Z0-9]*)+-[0-9]{3}$ ]] && echo PASS || echo FAIL` → `PASS`.
  - ID 유일성: `git grep -c "SPEC-LDBARMAP-002"` 를 `origin/main` 과 원격 브랜치 `WT-barmap-plan`·`WT-barmap-store`·`WT-barmap-run`·`WT-barmap-precision`·`WT-barmap-halfdouble`·`worktree-WT-ldbarmap-close` 에 실행 → 출력 없음(0건). REQ/AC 접두사 `LDBARENTRY` 도 `origin/main` 0건.
  - `depends_on: SPEC-LDBARMAP-001` → 그 SPEC `status: completed`(`SPEC-LDBARMAP-001/spec.md:5`)라 충족.
  - 프런트매터 12필드와 `tier` 선택 필드를 `spec-frontmatter-schema.md` 와 대조.
  - 시험·코드 실행 0회 — 이 plan-phase 는 문서만 쓴다.
- **감독 결정 반영(2026-10-14, 「전부 권고안대로」)**: `plan.md` §B의 미결 표지 6개를 해소했다 — D1 오프셋은 필수 요청 필드, D2 4/4 전용, D3 새 타입 `bar_map_analyse`, E1 두 배 BPM 채택은 저장 거절, E2 거절도 `status` `ok` + 요약, E3 곡 대응은 확인하지 않음(알려진 한계). E4(저장 `bpm`은 검출기 값만)도 확정을 확인했다. D4(화면 자리)는 후속 UI 카드의 결정이라 run-phase 를 막지 않는다.
- plan-audit 1차: FAIL(MP-7) — `.moai/reports/plan-audit/SPEC-LDBARMAP-002-review-1.md`(0.84, 문턱 0.80 위, 게이트 사유 MP-7 표지 6개). 결함 반영(2026-10-14, version 0.1.1): D2~D11, D13, D14 반영. D12(REQ 본문의 식별자)는 문체 문제이고 변경이 크다고 보아 반영하지 않았다. 표지 6개(D1·D2·D3·E1·E2·E3)는 감독 결정 대기로 유지. 2차 대기. (그 일자의 기록 — 같은 날 감독 결정으로 해소, 위 항목 참조.)
- plan-audit 2차: FAIL(MP-7만, 0.94) — review-2. 감독 결정 후 3차 감사.
- base 갱신(2026-10-14): `origin/main` `f5eada95` → `cca88d23` rebase. `server/web/app.py`·`session.py`의 줄 번호 인용을 새 base 기준으로 고쳤다(spec.md 54곳, plan.md 3곳, acceptance.md 3곳, 합 60곳). 처음 감사한 base는 `f5eada95`이고 `.moai/reports/plan-audit/`의 감사 보고서는 그 base의 줄 번호를 유지한다. 전제 P1~P18은 줄 번호만 이동, 서술이 바뀐 것은 Gaps 5번뿐.

## §E.2 Run-phase Evidence

### 중간 인계 (카드 t647, 재개 전 기록)
- 기준: origin/main `7cfc80c2`. 워크트리 `.claude/worktrees/t647`, 브랜치 `WT-barmap-entry-impl`. 배차서의 `WT-barmap-run` 은 SPEC-LDBARMAP-001 때 머지된 옛 브랜치라 쓰지 않았다(지우지 않았다).
- 끝난 단계:
  - M1 합성 단계 `6a54dc13` (`server/audio/bar_map_entry.py`, 시험 `test_audio_bar_map_entry.py`).
  - 수정 `ad671c5d` (M1 시험의 객체 주소 흔들림 제거), `637934e4` (첫 박 오프셋 점검을 base64 디코드 앞으로).
  - M2 세션 진입 메서드 `cd0dc342` (`ChatSession.analyse_bar_map`, 시험 `test_session_bar_map_entry.py`), 후속 `fb941a3d`.
  - 실패 표시 정책 `faf915b9` (분석 실패는 일반 문구 화면, 원문은 로그. 거절은 설계 문구).
  - SPEC 결정 E5 `5fc9319c`, `4ca0585e` (라벨은 성공과 그 밖을 가르고, 사유 문장은 본문).
- 검증 현황 (faf915b9 기준): 시험 4개 파일 137개 통과(M1·M2 파일과 이웃 2개), ruff 통과, 추가된 줄 금지어 0건. 변이 시험으로 시험의 힘을 확인함(M2 네 종, 실패 표시 두 종).
- 남은 일 (이 순서):
  1. M3: WS 프레임 `bar_map_analyse`(허용 목록·파서: 정수만, bool·실수·문자열·null·없음은 거절), app 디스패치(첨부 없음 → error song_audio_missing, busy, create_task + to_thread, 래퍼는 예외 시 non-success chat_response 1개), 프로토콜 동결 목록 한 줄(`test_prechk_tool.py`, `:1249` 다음 줄, t551 주석 앞)과 AC-011 역방향 실행, 시험 AC-001·002·009·010·011·015(와이어 3경우), AC-005 스캔 목록에 두 파일 추가. 첫 커밋 후보: 첫 박 오프셋 거절 문구가 직접 호출 때 `repr(offset)` 을 싣는 것을 뺀다.
  2. M4: AC-016 실제 곡 로컬 게이트. 원곡 `/Users/studiox/Music/AI-Lighting_Console-listen/t505/LOVE ATTACK.mp3` 는 이 머신에 있다(4.7MB). 저장소 밖 경로, skipif, 오프셋 1, 벽시계 시간 기록.
  3. 검증: SPEC §D 1–8.
  4. PR·CI·머지: `WT-barmap-entry-impl` → main, 머지 방식 merge(spec-workflow 기본값). 허용 목록 확장(D3)은 감독 결정이라 머지 판단은 리드에게 넘긴다. mergeable 을 먼저 읽고, CI 는 헤드 SHA 와 같이 읽는다.
  5. sync: `/moai sync SPEC-LDBARMAP-002` — manager-docs 가 status completed 와 §E.4 를 한 커밋으로, sync-auditor 가 독립 판정. SPEC 정정 세 가지는 manager-spec 로 한꺼번에.
- 객체 주소 처리 방침 (확정): 분석 실패의 화면 문구는 일반 문구 하나(`_BAR_MAP_ENTRY_FAILED_TEXT`). 원문 사유는 WARNING 로그(`server.web.session`). 거절 문구는 설계 문구. 시험은 화면 사유에 `0x` 와 `object at` 이 없다는 것으로 단언한다.
- D1 에서 고른 쪽 (디스패치의 「D1」, SPEC 에서는 E5): 거절 사유 문장은 본문(`text`)에 싣고, `summary` 는 성공(「마디 지도 저장」)과 그 밖(「마디 지도 분석 거절」)을 가르는 고정 라벨이다. 근거: `server/web/session.py` 의 기존 응답 모양(저장 관문 거절 `:9378-9385`, 박자 격자 수정 거절 `:9428` 등 고정 라벨 13곳).
- SPEC 정정 세 가지 (sync 에서 한꺼번에 반영하고, 보고서에 목록으로 남긴다):
  (a) REQ-LDBARENTRY-010 과 AC-LDBARENTRY-004 (5): 저장 관문이 `draft` 표식을 얹으므로, 「bar_map 키 외 바이트 동일」을 「bar_map 과 draft 표식 외 바이트 동일」로 고친다.
  (b) AC-LDBARENTRY-006 (다): 패치 대상은 `analyze.py:229` 의 정의가 아니라 `server/audio/bar_map.py` 가 가져다 쓰는 이름(`bar_map.py:36`, `:179`).
  (c) 전제 P13: 업로드가 지우는 것은 `_song_analysis` 뿐이고 `_song_bpm` 은 유지한다(`session.py` 업로드 함수, 주석 「_song_bpm 은 손대지 않는다」).
- 열린 항목: 로그가 파일에 남는지 앱 실행 설정을 확인한다(지금은 파이썬 기본 로깅, stderr 의 WARNING 이상). 성공 판정 경쟁(Gaps 4·15·16)은 SPEC 이 받아들인 한계다. 콜드 스타트 첫 실행 약 41초는 시험 한 개 60초 시간 제한에 가깝다(실제 곡 시험은 한 번만). plan-audit 3차 PASS(0.91) 의 산출물 해시는 본문 수정으로 달라졌다. 재감사 여부는 리드가 정한다.

## §E.3 Run-phase Audit-Ready Signal

_<pending run-phase>_

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_
