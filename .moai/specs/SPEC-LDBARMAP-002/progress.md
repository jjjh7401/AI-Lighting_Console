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

### M3 — WS 프레임 `bar_map_analyse` (카드 t647, 재개 뒤)

- 커밋: `a8482122` (첫 박 오프셋 거절 문구에서 입력값 빼기), `508b372c` (허용 목록·파서·디스패치), `6db71ada` (와이어·파서·동결 시험). M3 끝 트리 `6db71ada`.
- 기준 갱신: `origin/main` `3f67e525`(12커밋, `server/web/session.py` 포함)을 `3a0fef43` 으로 합침. `git merge-tree` 로 충돌 0을 먼저 확인했다. 합친 뒤 기준선은 `uv run pytest server/tests/test_audio_bar_map_entry.py server/tests/test_session_bar_map_entry.py server/tests/test_web_song_audio.py server/tests/test_session_bar_map_store.py -q -rs` → `187 passed, 1 warning in 8.00s`.
- 구현 요점
  - 파서(`server/web/messages.py`): 정수만 받는다. `bool`·실수·문자열·null·필드 없음은 `ProtocolError`다. 범위(0~3)는 세션이 판정한다. 출력은 `v`·`type`·`first_beat_offset` 세 키뿐이다.
  - 디스패치(`server/web/app.py`): 첨부 없음 → `error` 종류 `song_audio_missing`. 처리 중 → `busy`. 그 밖 → `create_task(run_bar_map_analysis(...))`로 띄우고 `await` 하지 않는다(AC-LDBARENTRY-010).
  - 래퍼 `run_bar_map_analysis`: 세션 메서드가 예외를 내면 WARNING 로그(`server.web.app`, 트레이스백 포함)를 남긴다. 이 요청에 대해 `chat_response` 가 하나도 나가지 않았을 때만 일반 문구 응답을 하나 보낸다. 판단은 연결 단위 `chat_response` 카운터의 증가분으로 한다.
  - 거절 문구(`server/audio/bar_map_entry.py`): 정수가 아닌 값의 문구에서 입력값(`repr`)을 뺐다. 객체 주소가 화면에 새지 않게 하기 위해서다.
- 래퍼 대체 응답의 모양: `status` `ok`, 요약 `마디 지도 분석 거절`, 본문 `_BAR_MAP_ENTRY_FAILED_TEXT`. 지시문의 「non-success」는 SPEC E2(거절은 새 상태값이 아니라 요약으로 가른다)에 맞춰 이렇게 읽었다. 리드 확인이 필요하다.
- 동결 목록(`server/tests/test_prechk_tool.py`): `_EXPECTED_CLIENT_MESSAGE_TYPES` 에 `"bar_map_analyse",` 한 줄을 `"approval_decision",` 다음에 넣었다. 다른 튜플은 건드리지 않았다.
- 관찰한 검증 (트리 `6db71ada`, `uv run`)
  - M3 묶음: `uv run pytest server/tests/test_audio_bar_map_entry.py server/tests/test_session_bar_map_entry.py server/tests/test_messages_bar_map_entry.py server/tests/test_web_bar_map_entry.py server/tests/test_prechk_tool.py -q -rs` → `217 passed, 1 warning in 5.85s`.
  - 회귀: `uv run pytest server/tests/test_web_song_audio.py server/tests/test_session_bar_map_store.py server/tests/test_audio_bar_map.py server/tests/test_audio_bar_map_store.py server/tests/test_web_messages.py server/tests/test_messages_beat_grid_t551.py -q -rs` → `476 passed, 1 warning in 16.66s`.
  - 린트: `uv run ruff check` 7개 파일 → `All checks passed!`. `uv run ruff format --check` → `7 files already formatted`.
  - 구현 레인의 보고(직접 재실행은 §D 단계에서 한다): AC-010 비공허 확인으로 디스패치를 `await` 형태로 바꾸면 `AssertionError: no websocket frame within 5.0s` 로 실패했다. AC-011 역방향 실행으로 `"bar_map_analyse",` 한 줄을 지우면 `assert surface.client_message_types == _EXPECTED_CLIENT_MESSAGE_TYPES` 가 실패했다(`At index 1 diff: 'bar_map_analyse' != 'beat_grid_apply'`). 두 변형 모두 되돌린 뒤 트리는 깨끗했다.
  - 변이 확인(구현 레인 보고): 파서 bool 가드 제거 → `[true]`·`[false]` 시험이 잡음. 누락 오프셋을 0으로 채움 → 세 시험이 잡음. 래퍼가 「이미 보냈나」를 무시 → 응답 뒤 예외 시험이 잡음. `str(exc)` 를 프레임에 실음 → 예외 시험이 잡음. 첨부 확인 제거 → AC-001·AC-015(a)가 잡음. busy 확인 제거 → AC-009·AC-015(b)가 잡음. 트레이스백 없는 로그 → 래퍼 두 시험이 잡음. 카운터 증가 제거 → 응답 뒤 예외 시험이 잡음.
  - 넓은 범위(구현 레인 보고): 웹 계열 시험 파일 40개 → `1328 passed in 63.33s`. 와이어 시험 파일은 25회 연속과 16회 동시 실행에서 모두 통과했다(불안정 없음).
- AC-LDBARENTRY-013 (4) 근거: 운영 파일 diff에서 지워진 줄은 `server/web/app.py` 의 `from server.web.session import ChatSession, PendingSongPlanStore, SongTimelineStore` 한 줄뿐이고, 그 자리에 새 이름이 든 여러 줄 import 가 들어갔다. `song_audio_analyse` 파서·디스패치 본문 변경 0줄. `_song_bpm`·`_song_analysis` 는 손대지 않았다.
- AC-LDBARENTRY-015 세션 쪽 여섯 경우: `test_session_bar_map_entry.py` 의 `test_ac015_every_outcome_that_reaches_analysis_sends_exactly_one_chat_response` 가 M2에서 이미 덮는다.
- 열린 항목 (M3 기준)
  - 계약 문서 누락: `server/web/PROTOCOL.md` 의 클라이언트 프레임 표에 `bar_map_analyse` 행이 없다. plan.md 파일 목록에도 없고 이를 강제하는 시험도 없다. 레인 범위를 넓히지 않고 리드 판단으로 남긴다. UI 쪽 `ui/src/protocol.ts` 도 UI 카드의 몫이다.
  - 래퍼 판정의 한계: 「이미 보냈나」는 연결 단위 카운터의 증가분이다. 같은 연결의 다른 경로가 같은 시간에 `chat_response` 를 내면, 드문 이중 실패에서 대체 응답이 빠질 수 있다. 측정하지 않았다.
  - 로그 파일 여부: 서버 코드에는 파일 로그 설정이 없다(`basicConfig`·`FileHandler` 없음). `server/web/launcher.py` 는 `sys.stderr` 로만 내보낸다. 파일로 남는지는 실행 방식에 달려 있어 저장소만으로는 확정하지 못했다.

### M4 — 실제 곡 로컬 게이트 AC-016 (카드 t647, 재개 뒤)

- 커밋: `5b2c53fc` (`test(SPEC-LDBARMAP-002): M4 실제 곡 로컬 게이트 AC-016`). 바뀐 파일은 `server/tests/test_audio_bar_map_entry.py` 하나(+155줄, 모듈 독스트링 두 줄 포함)이다. 운영 코드는 건드리지 않았다.
- 기록 정정(히스토리): 앞선 M3 증거 커밋 `8c2d0705` 에는 M4 테스트 파일이 잘못 섞여 있었다. 원격에 올리기 전에 로컬에서 `reset --soft` 로 되돌려 `503b3f22`(M3 증거 기록, `progress.md` 만)와 `5b2c53fc`(M4 테스트)로 나눴다. 원격 브랜치는 `6db71ada` → `5b2c53fc` 로 빨리 감기 되었다. 그 전에 원격에 올라 있던 것은 병합 커밋 `3a0fef43` 까지였다.
- 시험: `test_ac016_real_song_entry_gate`. `-k ac016` 과 `-k real_song` 둘 다 고른다. 로컬 전용이다. 원곡이 없으면 `skipif` 로, librosa 가 없으면 `requires_analysis` 로 건너뛴다. 건너뜀은 통과가 아니다.
- 경로와 고정물: 저장소 밖 `/Users/studiox/Music/AI-Lighting_Console-listen/t505/LOVE ATTACK.mp3`(4,733,524 바이트)를 복사하지 않고 제자리에서 읽는다. 세션에 첨부(`upload_song_audio`)하고, 곡 열쇠 `TEST SONG` / 1 인 초안 타임라인을 둔 뒤 진입 메서드 `analyse_bar_map(1)` 을 부른다. 첫 박 오프셋 1은 이 시험의 고정물이며 운영 상수가 아니다.
- 판정(AC-LDBARENTRY-016)
  - (1) `bar >= 1` 마디가 정확히 82개이고 번호가 1..82로 이어진다. `bar == 0` 은 1개이며 박 1개다.
  - (2) 엄격한 순서 대응(`strict_index_hit_rate`, 허용오차 `DOWNBEAT_TOLERANCE_SEC` = 0.060 s, 즉 ±60 ms)으로 다운비트 적중이 90 % 이상이다. 분모는 82다.
  - (3) 저장된 사건이 `detect_beat_grid → derive_bars → extract_bar_features → classify_bar_events` 를 직접 부른 결과와 같다. 직접 쪽이 비면 실패한다.
  - (4) 재현율은 `event_recall`(전체 사건 대 `parse_events()`)로 7개 중 5개 이상이다. 정밀도는 `event_precision` 으로 70 % 이상이다. 분모는 `break`·`kick_entry` 사건만이며, 기존 AC-007(`test_audio_bar_map.py` 862–865행)과 같은 규칙이다. 분모가 0이면 실패다.
  - (5) 벽시계 시간은 진입 메서드 호출 한 번만 잰다. 문턱은 없고, 출력 한 줄로 남긴다.
- 관찰한 결과
  - 레인이 같은 트리에서 다시 돌린 출력(`uv run pytest server/tests/test_audio_bar_map_entry.py -q -rs -s -k ac016`):
    `AC-016 wall-clock: 12.60 s` / `AC-016 measured: bars(bar>=1)=82 bars(bar==0)=1 downbeat_hit=82/82 (100.0%, 허용오차 ±60ms) events=8 direct_events=8 recall=7/7 precision=5/6 (83.3%)` / `1 passed, 78 deselected in 23.57s`.
  - 구현 레인의 실행(같은 값, 보고 기준): 벽시계 12.47 s. 파일 전체 `79 passed in 24.53s`. M3 묶음 `139 passed, 1 warning in 4.54s`.
  - 린트(레인 확인): `uv run ruff check server/tests/test_audio_bar_map_entry.py` → `All checks passed!`. `uv run ruff format --check` → `1 file already formatted`.
- 벽시계 시간(AC-016 (5), 기준값 없음): 12.47 s(구현 레인), 12.60 s(레인). 시험 항목 전체는 약 23.6 s다. `pyproject.toml` 의 `faulthandler_timeout = 60` 과 비교하면 여유가 있다. 콜드 스타트(첫 실행) 시간은 이번에 따로 재지 않았다.
- 구현 레인의 변이 확인(저장소 밖에서 인라인 실행, 파일은 바꾸지 않음. 레인은 재실행하지 않았다)
  - 사건을 하나 빼면 `assert stored == direct` 에서 실패한다. 재현율은 6/7, 정밀도는 4/5가 되어 (4)만으로는 잡히지 않는다.
  - 사건을 하나 더하면 같은 단언에서 실패한다. 정밀도는 5/7(71.4 %)로 70 % 를 넘으므로 (4)만으로는 통과한다.
  - 저장 시각을 +100 ms 밀면 적중률 단언에서 실패한다(0/82).
- 열린 항목(M4 기준)
  - 정밀도 분모가 점 사건 6개뿐이다. 사건 하나가 바뀌면 83.3 %가 71.4 %로 움직인다. 이 값은 있는 그대로 적는다. 문턱 70 %는 SPEC-LDBARMAP-001 이 정했다.
  - 실곡 게이트는 한 곡, 한 장비에서 한 번 잰 값이다. CI 에는 원곡이 없어 건너뛴다. 건너뜀은 통과로 치지 않으므로 이 AC 는 로컬 실행 출력으로만 검증된다.
  - plan.md M4 의 가칭 `-k real_song` 은 `test_ac016_real_song_entry_gate` 로 맞게 선택된다.
  - §D 1–8 검증, PR, 머지 판단, sync 는 이번 세션에서 하지 않았다. 다음 세션으로 넘긴다(`.moai/reports/t647/resume.md`).

## §E.3 Run-phase Audit-Ready Signal

_<pending run-phase>_

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_
