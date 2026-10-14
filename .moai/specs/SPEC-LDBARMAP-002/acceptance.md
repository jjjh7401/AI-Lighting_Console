# SPEC-LDBARMAP-002 — 수락 기준

모든 기준은 Given-When-Then 형식이며 이진 판정(PASS/FAIL)이 가능하도록 수치·단위·문턱을 명시한다. 각 AC는 검증하는 REQ-ID와 **작성할 시험 파일**을 적는다. 시험 파일 이름과 진입 메서드 이름(`analyse_bar_map`)은 가칭이며 run-phase가 확정한다. 이 문서는 plan-phase 산출물이라 어떤 시험도 아직 돌리지 않았다.

> **공통 전제(시험 도구)**: 세션 시험은 `server/tests/test_session_bar_map_store.py:28-76`의 시험 틀(`ChatSession` + `SongTimelineStore` + `FakeConsole` + 모델을 부르면 깨지는 제공자)을 같은 모양으로 쓴다. 와이어 시험은 `server/tests/test_web_song_audio.py:543-581`의 `TestClient` + `create_app` + `recv_frame` 형태를 쓴다. 오디오는 시험 안에서 합성한다(`test_audio_bar_map.py:220-253`의 클릭 트랙 생성기와 같은 방식) — 오디오 파일을 저장소에 두지 않는다(REQ-LDBARENTRY-016). 분석 라이브러리(librosa)가 없으면 합성 오디오를 쓰는 시험은 `test_audio_bar_map.py:64-67`과 같은 `skipif`로 건너뛴다.

## §A. 수치 상수 (한 번 정의, 전체에서 재사용)

| 상수 | 값 | 단위 | 근거 |
|---|---|---|---|
| 첫 박 오프셋 유효 범위 | 정수 0~3 | 박(beat-index) | REQ-LDBARENTRY-002·007, `bar_map.py:452-457`. 4/4 전용(D2) |
| 박자표 | `[4, 4]` | 분자/분모 | REQ-LDBARENTRY-015 |
| 응답 프레임 수 | 분석에 도달한 결과마다 `chat_response` 정확히 1, 도달하지 못한 요청(첨부 없음·busy·프레임 오류)은 0 | 개 | REQ-LDBARENTRY-012 |
| 되돌리기 깊이 증가 | 저장 성공 1회당 +1, 거절 0 | 단계 | REQ-LDBARENTRY-010 |
| 실제 곡 다운비트 적중 허용오차 | ±60 ms | ms | `SPEC-LDBARMAP-001` §A 상수표, AC-LDBARMAP-016 |
| 실제 곡 다운비트 적중 통과선 | 90 % 이상 | % | `SPEC-LDBARMAP-001` AC-LDBARMAP-016 |
| 실제 곡 사건 재현율 통과선 | 7개 중 5개 이상 | 사건 | `SPEC-LDBARMAP-001` AC-LDBARMAP-007 |
| 실제 곡 사건 정밀도 통과선 | 70 % 이상 | % | `SPEC-LDBARMAP-001` AC-LDBARMAP-007 |
| 합성 클릭 트랙 BPM 허용오차 | ±1 % | % | `test_audio_bar_map.py:256` 선례 |

## §B. Given-When-Then 시나리오

### AC-LDBARENTRY-001 (REQ-LDBARENTRY-003) — 첨부 오디오 없음

시험 파일: `server/tests/test_web_bar_map_entry.py`

**Given** 곡 오디오가 첨부되지 않은 세션이 WS에 연결돼 있고, 진입 메서드를 부르면 깨지는 대역(스텁)이 세션에 꽂혀 있고
**When** 유효한 `first_beat_offset`을 실은 마디 지도 분석 프레임이 오면
**Then** (1) `type == "error"`이고 `kind == "song_audio_missing"`인 프레임이 온다 — 종류를 단언하는 것이 이 시험의 전부다. 종류를 안 재면 허용 목록에 타입이 없는 상태의 `kind == "protocol"` 오류와 구별되지 않는다(`test_web_song_audio.py:607-612`가 같은 함정을 적었다). (2) `message`에 `첨부`가 들어 있다. (3) 스텁 호출 횟수가 0이다. (4) 이어서 보낸 `status_request`에 `status` 프레임이 답한다(연결이 살아 있다, `test_web_song_audio.py:627-637`과 같은 형태).

### AC-LDBARENTRY-002 (REQ-LDBARENTRY-002) — 프레임 모양: 오프셋 필수, 기본값 없음

시험 파일: `server/tests/test_messages_bar_map_entry.py`

**Given** `parse_client_message`(`messages.py:378`)가 있고
**When** 다음 프레임을 차례로 넣으면: 오프셋 0·1·2·3·-1·4 정수 / 필드 없음 / `null` / `true` / `1.0` / `"1"` / `[1]`
**Then** (1) 정수 프레임 여섯(0·1·2·3·-1·4)은 전부 정확히 키 `{v, type, first_beat_offset}`만 가진 사전으로 통과하고 값은 입력과 같다 — 오디오 바이트나 다른 필드를 싣지 않는다. -1과 4처럼 범위 밖 정수도 파서는 통과시키고 범위 판정은 AC-003이 잰다. 파서는 박 수 상수를 따로 들지 않는다. (2) 나머지 여섯 프레임(필드 없음·`null`·`true`·`1.0`·`"1"`·`[1]`)은 전부 `ProtocolError`다 — 특히 "필드 없음"이 `first_beat_offset == 0`으로 통과하면 FAIL이다(기본값 금지). (3) 새 타입 문자열이 `CLIENT_MESSAGE_TYPES`(`messages.py:116`)에 들어 있다.

### AC-LDBARENTRY-003 (REQ-LDBARENTRY-007) — 싼 점검은 디코드 전에: 범위 밖 오프셋, 타임라인 없음

시험 파일: `server/tests/test_session_bar_map_entry.py`

**Given** 합성 오디오가 첨부되고 초안 타임라인이 있는 세션에서, 박 격자 검출 함수를 부르면 `AssertionError`를 내는 대역이 꽂혀 있고
**When** 진입 메서드를 오프셋 -1, 4, 99로 각각 부르면
**Then** 세 번 모두 (1) `chat_response` 1개가 전송되고 그 본문에 허용 범위 `0~3`이 들어 있다. (2) 검출 대역이 불리지 않았다. (3) `store.latest`가 호출 전 깊은 사본과 같고 되돌리기 깊이가 그대로다. (4) `song_timeline` 프레임이 0개다.

**And Given** 같은 세션에서 `store.latest`가 `None`일 때 **When** 유효한 오프셋으로 부르면 **Then** 같은 네 조건이 성립하고 본문이 타임라인 부재를 말한다.

### AC-LDBARENTRY-004 (REQ-LDBARENTRY-001, REQ-LDBARENTRY-010) — 정상 경로: 저장·읽기·이벤트·깊이

시험 파일: `server/tests/test_session_bar_map_entry.py`

**Given** 초안 타임라인(곡 열쇠 두 값 포함)이 있는 세션에 합성 클릭 트랙(30초, 알려진 BPM)이 `upload_song_audio`로 첨부돼 있고
**When** 오프셋 0으로 진입 메서드를 부르면
**Then** (1) `timeline_bar_map()`이 `None`이 아니고 `store.latest["bar_map"]`와 같다. (2) `validate_bar_map(그 값) is None`이다. (3) 저장된 `bpm`이 합성 BPM의 ±1 % 안이다. (4) 되돌리기 깊이가 호출 전보다 정확히 1 많다. (5) `bar_map`을 뺀 나머지 타임라인 키가 호출 전과 깊은 비교로 같다. (6) 전송된 프레임 중 `song_timeline`이 정확히 1개이고 그 `timeline`이 `bar_map`을 든다.

### AC-LDBARENTRY-005 (REQ-LDBARENTRY-006, REQ-LDBARENTRY-015, REQ-LDBARENTRY-016) — 합성은 순수하고 번호 공간이 맞다

시험 파일: `server/tests/test_audio_bar_map_entry.py`

**Given** 합성 클릭 트랙 바이트와 오프셋 k ∈ {0, 1, 2, 3}이 있고
**When** 합성 단계를 세션·콘솔·UI 객체 없이 바이트와 오프셋만으로 부르면
**Then** (1) 실패 객체가 아니라 마디 지도 사전이 나오고 `validate_bar_map(그 사전) is None`이다. (2) `bars[]`의 `beats_ms`를 순서대로 이어 붙이면 같은 오디오에 대한 `detect_beat_grid(...).beat_times_ms`와 같다. (3) k > 0이면 첫 마디 번호가 0이고 그 `beats_ms` 길이가 k이며, k = 0이면 첫 마디 번호가 1이다. 마디 번호는 연속한다. (4) **양성 대조군(번호 공간)**: 분류 단계를 대역으로 바꾼다 — 대역은 합성 단계가 넘긴 마디별 특징 목록을 기록하고, 그 목록의 **마지막 특징 마디**에 `kick_entry` 사건 하나를 돌려준다. 합성 클릭 트랙은 실제 분류기로는 사건을 거의 내지 않으므로 이 대역이 사건 유무에 기대지 않고 번호 공간을 재는 장치다. 전제 단언: 기록된 특징이 1개 이상이고 저장된 `events`가 1개 이상이다 — **0개면 FAIL**이다(사건이 없어 (4a)~(4c)가 공허하게 참이 되는 것을 막는다). (4a) 기록된 특징의 `bar`가 순서대로 1, 2, …, n이고 n이 저장된 `bar >= 1` 마디 수와 같다. (4b) 저장된 `events`에 주입한 사건이 정확히 1개이고 그 `start_bar == end_bar`가 저장된 `bars[].bar`의 최댓값과 같다(마디 0은 세지 않는 같은 1-base 번호 공간). (4c) 이 (4a)~(4b)를 k = 0·1·2·3 각각에서 되풀이한다 — 오프셋이 달라져도 특징 번호와 저장 마디 번호의 대응이 유지된다. (5) `time_signature == [4, 4]`이고 `first_beat_offset == k`다. (6) **고유값 정적 스캔(닫힌 목록)**: 아래 다섯 정규식이 0건이다 — `\bLOVE ATTACK\b`, `\b112(\.\d+)?\b`, `\b210\b`, `\bGroup\b`, `\bfid\b`. 단어 경계를 써서 `bpm_confidence`·`confidence`가 `fid`에 걸리지 않는다. 목록은 닫혀 있고, 넓히려면 SPEC을 개정한다. 이 시험(pytest)이 훑는 파일은 **신규 5개 중 이 시험 파일을 뺀 넷**이다 — 합성 모듈(가칭 `server/audio/bar_map_entry.py`), `test_session_bar_map_entry.py`, `test_messages_bar_map_entry.py`, `test_web_bar_map_entry.py`. 이 시험 파일 자신은 정규식 목록과 AC-016 실제 곡 고정물이 있어 제외한다. 신규 시험 틀은 중립 제목과 번호(곡 열쇠 예: `"TEST SONG"`, `1`)를 쓴다. 수정한 운영 파일 `server/web/messages.py`·`app.py`·`session.py`는 파일 전체가 아니라 **base 대비 추가된 줄**만 같은 다섯 정규식으로 훑는다 — 이 훑기는 base 커밋이 필요해 pytest가 아니라 §D 8번 명령이 맡는다.

### AC-LDBARENTRY-006 (REQ-LDBARENTRY-007) — 분석 실패는 타임라인을 건드리지 않는다

시험 파일: `server/tests/test_session_bar_map_entry.py`

**Given** 초안 타임라인이 있는 세션에서 다음 실패 입력을 각각 만들고: (가) 오디오가 아닌 바이트 (나) 2000 ms보다 짧은 오디오(`bar_map.py:215`) (다) `analysis_available()`이 거짓인 환경(`analyze.py:229` 대역) (라) 박은 3개뿐이라 마디 경계가 2개 미만이 되는 검출 결과 대역(`bar_map.py:622`)
**When** 오프셋 유효값으로 진입 메서드를 부르면
**Then** 네 경우 모두 (1) `chat_response` 1개가 전송되고 본문에 실패한 단계의 `reason` 문자열이 들어 있다 — (다)는 `MANUAL_BPM_FALLBACK_REASON`(`analyze.py:188`)이다. (2) `store.latest`가 호출 전과 깊은 비교로 같다. (3) 되돌리기 깊이가 그대로다. (4) `song_timeline` 프레임이 0개다.

### AC-LDBARENTRY-007 (REQ-LDBARENTRY-008) — 두 배 BPM 채택은 저장하지 않는다

시험 파일: `server/tests/test_audio_bar_map_entry.py`(합성 단계), `server/tests/test_session_bar_map_entry.py`(세션 응답)

**Given** 박 격자 검출 대역이 `bpm_check.outcome == "adopt_double"`, `bpm == 2 × raw_bpm`인 결과를 돌려주고
**When** 합성 단계를 부르면 **Then** 마디 지도가 아니라 실패 객체가 나오고 그 `reason`에 `두 배`가 들어 있다. **And When** 같은 대역으로 진입 메서드를 부르면 **Then** AC-006의 네 조건이 성립한다. 이 AC의 근거 판단(E1)이 감독 확인에서 바뀌면 이 AC가 바뀐다 — 확인 전까지는 권고(저장 거절)가 기준이다.

### AC-LDBARENTRY-008 (REQ-LDBARENTRY-009) — 분석 중 타임라인이 바뀌면 저장하지 않는다

시험 파일: `server/tests/test_session_bar_map_entry.py`

**Given** 곡 열쇠 `(제목 A, 번호 a)`의 초안 타임라인이 있는 세션에서, 합성 단계 대역이 실행 도중 `store.latest`를 `(제목 B, 번호 b)`의 다른 타임라인으로 바꾸고 유효한 마디 지도를 돌려주고
**When** 진입 메서드가 끝나면
**Then** (1) `chat_response` 1개가 전송되고 본문이 곡이 바뀌었음을 말한다. (2) `store.latest`가 바뀐 타임라인(B)과 깊은 비교로 같고 `bar_map` 키가 없다. (3) 되돌리기 깊이가 그대로다. **And Given** 대역이 `store.latest`를 `None`으로 바꿀 때도 **Then** 같은 (1)·(3)이 성립한다.

### AC-LDBARENTRY-009 (REQ-LDBARENTRY-004) — 처리 중이면 busy

시험 파일: `server/tests/test_web_bar_map_entry.py`

**Given** 세션에 첨부 오디오가 있고, 진입 메서드 대역이 이벤트를 기다리며 멈추도록(명시적 시간 상한이 있다) 꽂혀 있고, 첫 마디 지도 분석 프레임이 이미 처리 중일 때
**When** 대역이 **풀리기 전에** 두 번째 마디 지도 분석 프레임이 오면
**Then** (1) `type == "busy"`이고 `message`가 `app.py:89`의 문구와 같은 프레임이 온다. 풀리기 전에 받은 프레임 중 `chat_response`는 0개다. (2) 대역 호출 횟수가 1이다. (3) 그 뒤 대역을 푼다(이 시점이 풀림 시점이다). 대역은 풀리면 `chat_response` 프레임을 하나 보내고 끝나도록 만든다. 시험은 대역을 푼 뒤 **첫 요청의 `chat_response` 수신을 기다리고**, 이어 `status_request`를 보내 `status` 답을 받은 다음에야 세 번째 프레임을 보낸다 — 그러지 않으면 첫 작업이 아직 끝나지 않아(`current_task.done()` 거짓) 세 번째 프레임에 또 busy가 올 수 있다. 그 뒤 세 번째 프레임은 busy 없이 받아들여지고 호출 횟수가 2가 된다.

### AC-LDBARENTRY-010 (REQ-LDBARENTRY-005) — 분석 중에도 수신 루프가 산다

시험 파일: `server/tests/test_web_bar_map_entry.py`

**Given** AC-009와 같은 멈추는 대역이 꽂혀 있고 마디 지도 분석 프레임이 처리 중일 때
**When** 대역이 풀리기 **전에** `status_request` 프레임을 보내면
**Then** `status` 프레임이 대역이 풀리기 전에 도착한다(시간 상한 안에). 도착하지 않으면 FAIL이다. **비공허 조건**: 이 시험은 디스패치 분기를 `await asyncio.to_thread(...)`로 바꾸면 상태 응답이 막혀 시간 상한에서 **실패해야** 한다 — run-phase는 그 변형을 한 번 실행해 실패를 `progress.md` §E.2에 증거로 남긴다(`test_web_song_audio.py:550-555`가 같은 판정 방식을 적었다). 대역의 대기에는 명시적 시간 상한을 둔다 — `pyproject.toml:75-76`의 `faulthandler_timeout = 60`(`exit_on_timeout`)이 멈춘 시험을 프로세스째 끊기 때문이다.

### AC-LDBARENTRY-011 (REQ-LDBARENTRY-013) — 프로토콜 동결 스냅샷

시험 파일: `server/tests/test_prechk_tool.py`(기존 파일의 손 편집 1건)

**Given** 새 타입이 `messages.py`의 허용 목록에 들어 있고
**When** `TestBoundaryProhibitions.test_the_axis_adds_no_web_surface`(`test_prechk_tool.py:1484`)를 돌리면
**Then** (1) PASS다. (2) `_EXPECTED_CLIENT_MESSAGE_TYPES`의 base 대비 diff가 새 문자열 원소 정확히 1개와 그 사유 주석뿐이다. 그 원소와 주석은 `"approval_decision",`(base `:1249`) **바로 다음 줄**에서 시작하고 t551 주석 블록(base `:1250-1261`) **앞**에서 끝난다 — 리터럴 튜플이 정렬된 순서여야 `==` 비교(`:1499`)가 통과하므로 이 자리가 정본이다. (3) `_EXPECTED_SERVER_MESSAGE_TYPES`(`:1335`)와 `_EXPECTED_WEB_ROUTES`의 diff가 0줄이다. **역방향 실행**: 새 원소 줄만 지우고 같은 시험을 돌리면 FAIL이어야 한다 — 그 출력을 `progress.md` §E.2에 남긴다. 이 FAIL이 없으면 이 AC는 공허하다.

### AC-LDBARENTRY-012 (REQ-LDBARENTRY-014) — 소비자 왕복

시험 파일: `server/tests/test_session_bar_map_entry.py`

**Given** AC-004의 정상 경로가 끝난 세션이고
**When** `timeline_bar_map()`의 결과를 `build_song_timing_from_bar_map`에 넣으면
**Then** (1) 결과가 `None`이 아니다. (2) `downbeat_bar1_seconds`가 저장된 1마디 `start_ms / 1000`과 같다. (3) `beats_per_bar == 4`이고 `bpm`이 저장된 `bpm`과 같다. (4) 오프셋이 0보다 크면 `pickup_beats`가 0마디 `beats_ms` 길이이고, 0이면 `None`이다. **참고 측정(문턱 없음)**: 1~5마디에 대해 `SongTiming.bar_start_seconds(n)`과 저장된 `bars[n].start_ms / 1000`의 차이를 ms로 잰 값을 `progress.md` §E.2에 기록한다 — 소비자는 `bpm`으로 마디 시작을 계산하고(P9) 저장된 `start_ms`를 쓰지 않으므로, 두 값이 얼마나 어긋나는지는 이 경로가 확인해 둘 가치가 있다.

### AC-LDBARENTRY-013 (REQ-LDBARENTRY-011) — 접촉 경계

시험 파일: `server/tests/test_session_bar_map_entry.py`

**Given** AC-004와 같은 세션이고, 콘솔 대역이 있고, 라이브러리 경로(`tmp_path / "library.json"`)가 호출 전에 존재하지 않고, `_song_bpm`과 `_song_analysis`에 서로 다른 표식 객체를 넣어 두었고
**When** 정상 경로를 한 번 돌리면
**Then** (1) 콘솔 대역이 받은 호출이 0건이다. (2) 라이브러리 파일이 여전히 없다. (3) `_song_bpm`과 `_song_analysis`가 표식 객체 그대로다(`is` 비교). (4) `test_web_song_audio.py`와 `test_session_bar_map_store.py`가 수정 없이 통과한다 — `song_audio_analyse` 프레임의 파서·분기·카드 흐름이 바이트 단위로 바뀌지 않았다는 간접 증거다(`git diff`가 `song_audio_analyse`의 파서 분기와 디스패치 분기 본문에 변경 0줄이라는 직접 증거를 `progress.md` §E.2에 함께 남긴다. 줄 번호는 새 분기가 들어가면 밀리므로 번호가 아니라 분기 본문으로 가른다).

### AC-LDBARENTRY-014 (REQ-LDBARENTRY-010) — 재실행은 교체하고, 되돌리기는 직전 값을 복원한다

시험 파일: `server/tests/test_session_bar_map_entry.py`

**Given** AC-004가 끝나 `bar_map` V1(오프셋 0)이 저장돼 있고
**When** 같은 오디오로 오프셋 1로 다시 부르면
**Then** (1) `store.latest["bar_map"]["first_beat_offset"] == 1`이고 V1과 다르다. (2) 되돌리기 깊이가 V1 직후보다 정확히 1 많다. (3) `undo_timeline_draft()` 한 번이 V1을 깊은 비교로 복원한다. (4) 한 번 더 되돌리면 `bar_map` 키가 없는 처음 타임라인으로 돌아간다.

### AC-LDBARENTRY-015 (REQ-LDBARENTRY-012) — 어떤 결과든 응답은 연결로 나간다

시험 파일: `server/tests/test_session_bar_map_entry.py`(분석에 도달한 여섯 경우), `server/tests/test_web_bar_map_entry.py`(도달하지 못한 세 경우)

**측정 지점은 반환값이 아니라 연결의 송신 지점이다.** 세션 시험은 연결이 주입한 `send_event` 콜백(`session.py:4046`)이 받은 프레임을 세고, 와이어 시험은 클라이언트가 받은 프레임을 센다. 저장 관문의 거절 경로는 반환만 하고 보내지 않기 때문이다(`session.py:9330-9345`).

**Given** `send_event` 콜백을 리스트에 모으는 세션이고
**When** 다음 결과를 각각 만들면: 성공 / 타임라인 없음 / 범위 밖 오프셋 / 분석 실패(AC-006 (가)) / 두 배 BPM 채택 / 곡 바뀜(AC-008)
**Then** 여섯 경우 모두 모인 프레임 중 `type == "chat_response"`가 정확히 1개다. **성공에서 그 1개는 저장 관문이 보낸 것이다** — 진입 경로가 성공에서 반환 이벤트를 다시 `_send`하면 2개가 되어 FAIL이다. 거절 다섯에서는 진입 경로가 보낸 것이 그 1개다. 성공에서는 `song_timeline`이 정확히 1개, 나머지 다섯에서는 0개다. 성공의 `summary`가 다섯 거절의 `summary`와 모두 다르다.

**And Given** WS에 연결된 세션이고 **When** 다음 세 요청을 각각 보내면: (가) 첨부 오디오가 없는 상태의 유효한 분석 프레임 (나) **곡 오디오가 첨부된 상태에서**, 첫 분석 요청이 멈추는 대역 안에서 처리 중일 때 — 대역이 **풀리기 전에** 오는 두 번째 분석 프레임(오디오가 붙어 있으므로 첨부 없음 경로와 섞이지 않고 busy 경로만 탄다) (다) `first_beat_offset`이 없는 프레임 **Then** 클라이언트가 받는 응답은 (가) `error` + kind `song_audio_missing`, (나) `busy`, (다) `error` + kind `protocol`이고, `chat_response`는 0개다. **(나)의 0개는 대역을 풀기 전까지 받은 프레임만 센다** — 대역은 풀리면 `chat_response` 1개를 보내므로(AC-009 (3)) 푼 뒤에 세면 1이 되어 0과 맞지 않는다. 진입 메서드 대역의 호출 횟수는 (가)·(다)에서 0, (나)에서 첫 요청 몫의 1이다.

### AC-LDBARENTRY-016 (REQ-LDBARENTRY-001, 006, 016) — 실제 곡 로컬 전용 게이트

시험 파일: `server/tests/test_audio_bar_map_entry.py`(`skipif`: 원곡 부재 시 건너뜀 — `test_audio_bar_map.py:554-557`과 같은 방식)

이 AC는 **로컬 전용**이다. 곡 파일은 저장소에 없다(REQ-LDBARENTRY-016). 고정물: `/Users/studiox/Music/AI-Lighting_Console-listen/t505/LOVE ATTACK.mp3`(`test_audio_bar_map.py:72`가 같은 경로를 쓴다), 정답지는 `tools/barmap/ground_truth.py`의 `parse_downbeats`·`parse_bar_features`·`parse_precision_evidence`(`test_audio_bar_map.py:55-61`), 첫 박 오프셋은 감독 귀 확정값 1(`SPEC-LDBARMAP-001` HISTORY 카드 t530 행, `test_audio_bar_map.py:78`의 `CONFIRMED_FIRST_BEAT_OFFSET`과 같은 값 — **이 오프셋은 이 시험의 고정물이지 운영 코드 상수가 아니다**).

**Given** 위 파일을 첨부한 세션과 곡 열쇠가 있는 초안 타임라인이 있고
**When** 오프셋 1로 진입 메서드를 부르면
**Then** (1) 저장된 `bars[]` 중 `bar >= 1`이 정확히 82개이고 `bar == 0`이 1개(박 1개)다. (2) 그 `bars[].start_ms`가 정답지 다운비트와 **엄격한 순서 대응**(검출 n번째는 정답 n번째와만 비교, 최근접 매칭 금지 — `SPEC-LDBARMAP-001` REQ-LDBARMAP-005)으로 ±60 ms에서 90 % 이상 적중한다. (3) 저장된 `events`가 같은 오디오에 대해 `classify_bar_events(extract_bar_features(...))`를 직접 부른 결과와 같다 — 진입 경로가 분석기의 출력에 아무것도 더하거나 빼지 않는다. (4) 그 사건으로 계산한 재현율이 7개 중 5개 이상, 정밀도가 70 % 이상이다(`tools/barmap/scorer.py`의 `event_recall`·`event_precision`, 분모 0이면 FAIL — `test_audio_bar_map.py:865`가 같은 규칙을 단언한다). (5) **측정만 하고 문턱은 없다**: 진입 메서드 호출 전체의 벽시계 시간(초)을 `progress.md` §E.2에 기록한다. 이 값이 spec.md Gaps 1번의 첫 실측이다.

## §C. 가장자리 사례

| 사례 | 기대 | 다루는 AC |
|---|---|---|
| 박이 오프셋보다 적은 오디오 | 마디 경계 2개 미만 → 특징 추출 실패 → 거절(`bar_map.py:622`) | AC-006 (라) |
| 마지막 마디가 4박 미만 | 저장 스키마가 마지막 마디의 부분 채움을 허용한다(`bar_map_store.py:259-262`) — 거절하지 않는다 | AC-004 (2) |
| 같은 오디오 재실행 | 교체 + 되돌리기 가능 | AC-014 |
| 분석 중 HTTP 불러오기 | 곡 열쇠가 달라지면 저장하지 않음. 같은 곡을 다시 불러온 경우(열쇠가 같음)는 막지 못한다 | AC-008, Gaps 4번 |
| 분석 중 WS 연결이 끊김 | 끊긴 뒤 `_send`의 거동을 읽지 못했다 — 이 SPEC은 시험으로 판정하지 않고 Gaps로 둔다 | spec.md Gaps 5번 |
| 오프셋 `true` | 파서가 거절(`bool`은 `int`의 하위형이라 명시적으로 뺀다) | AC-002 |
| 프레임에 `time_signature`나 오디오 필드를 얹어 보냄 | 파서 출력에 남지 않는다(알려진 필드만 돌려준다 — `song_audio_analyse` 파서와 같은 관행, `messages.py:755-760`) | AC-002 (1) |

## §D. 완료 정의 (Definition of Done)

아래는 run-phase가 실행하고 **출력 원문**을 `progress.md` §E.2에 붙이는 명령이다. 이 plan-phase는 어느 것도 실행하지 않았다. 실행기(`python -m pytest`인지 `uv run`인지)는 run-phase가 저장소 관례로 확인한다.

1. 신규 시험 네 파일 전부 통과(AC-001~016 중 AC-011은 `test_prechk_tool.py`).
   `python -m pytest server/tests/test_audio_bar_map_entry.py server/tests/test_session_bar_map_entry.py server/tests/test_messages_bar_map_entry.py server/tests/test_web_bar_map_entry.py server/tests/test_prechk_tool.py -q`
2. 회귀 — 건드리지 않은 기존 계약:
   `python -m pytest server/tests/test_web_song_audio.py server/tests/test_session_bar_map_store.py server/tests/test_audio_bar_map.py server/tests/test_audio_bar_map_store.py server/tests/test_web_messages.py server/tests/test_messages_beat_grid_t551.py -q`
3. 린트·포맷(`pyproject.toml:78-125`): 바뀐 파일에 `ruff check`와 `ruff format --check`. 새 파일은 첫날부터 전량 린트를 받는다(`pyproject.toml:98-101`).
4. 오디오 파일 비커밋(REQ-LDBARENTRY-016): `git diff --name-only origin/main...HEAD`의 출력에 `.mp3 .wav .flac .m4a .aac .ogg` 확장자가 0건.
5. 콘솔 접촉 0건: `git diff --name-only origin/main...HEAD`에 `console/` 아래 파일이 0건이고, AC-013이 통과한다.
6. AC-016은 감독의 로컬 환경에서 한 번 돌려 결과를 기록한다(CI에서는 건너뜀 — 건너뜀 자체를 PASS로 읽지 않는다. 로컬 실행 출력이 없으면 AC-016은 미검증이다).
7. 변경 파일 목록이 plan.md §C의 파일 목록과 다르면 그 차이를 `progress.md`에 사유와 함께 적는다.
8. 고유값 훑기 — 수정한 운영 파일의 추가된 줄(AC-005 (6)의 pytest가 못 맡는 부분): `git diff -U0 origin/main...HEAD -- server/web/messages.py server/web/app.py server/web/session.py`의 `+` 줄(헤더 `+++` 제외)을 정규식을 지원하는 도구(예: `rg`)로 `\bLOVE ATTACK\b|\b112(\.[0-9]+)?\b|\b210\b|\bGroup\b|\bfid\b`에 대어 0건이어야 한다. 출력 원문을 `progress.md` §E.2에 붙인다.
