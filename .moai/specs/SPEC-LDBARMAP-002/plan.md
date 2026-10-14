# SPEC-LDBARMAP-002 — 구현 계획

## §A. 개요 (Context)

서버에 마디 지도를 만드는 분석기, 저장하는 관문, 읽어 쓰는 소비자가 모두 있지만 셋을 잇는 입구가 없다(spec.md §1). 이 SPEC은 그 입구 하나를 낸다 — 프레임 한 종류, 세션 메서드 하나, 합성 단계 하나. 화면은 후속 카드다.

- 작업 위치: 워크트리 `.claude/worktrees/WT-barmap-entry-spec`, 베이스 `origin/main` `cca88d23`(2026-10-14 rebase, 처음 감사한 base는 `f5eada95`).
- 선행 SPEC: `SPEC-LDBARMAP-001` — frontmatter `status: completed`(`spec.md:5`)라 `depends_on` 사전 점검을 충족한다. 이 SPEC은 그 SPEC의 분석기·저장 스키마를 수정하지 않는다.
- 후속: 입구 버튼과 오프셋 입력(UI 카드, D4), 그리고 이 입구가 채운 `bar_map`을 읽는 `SPEC-LDARRANGE-001`의 run-phase.
- 읽은 전제와 줄 번호는 spec.md §3에 있다. 이 문서는 줄 번호를 되풀이하지 않고 P-번호로 부른다.

## §B. 결정 순서 — 되돌리기 어려운 것부터

바뀔 가능성이 가장 큰 결정을 앞에 둔다. 아래 여섯 결정(D1·D2·D3·E1·E2·E3)은 2026-10-14에 감독이 「전부 권고안대로」 결정해 반영했고, 미결 표지 6개는 모두 해소됐다. D4(화면 자리)는 후속 UI 카드의 결정이라 이 SPEC의 run-phase를 막지 않는다.

1. **프레임의 이름과 모양** — 프로토콜 동결 지점이라 한 번 정하면 클라이언트가 얹힌다. 확정(2026-10-14): D3 새 타입 `bar_map_analyse`이며 `song_audio_analyse` 확장이 아니다. D1 `first_beat_offset`은 기본값 없는 필수 요청 필드다.
2. **분석 범위** — 확정(2026-10-14): D2 4/4 전용이다. 분석기를 일반화하지 않으므로 이 SPEC은 분석기를 열지 않고 Tier M에 머문다.
3. **분석기 한계를 입구에서 어떻게 막는가** — 확정(2026-10-14): E1 두 배 BPM 채택은 저장을 거절한다(원래 BPM으로도 보정 BPM으로도 저장하지 않는다). E2 거절 응답의 `status`도 `ok`이고, 요약(`summary`)은 결과마다 고정된 라벨로 쓰며 사유 문장은 본문(`text`)에 싣는다(E5). E3 오디오와 타임라인의 곡 대응은 확인하지 않는다(알려진 한계, spec.md Gaps 8번). 저장 `bpm`의 출처(E4)도 (가) 검출기 값만 쓰는 것으로 확정됐다 — spec.md §5.
4. **합성을 어디에 두는가** — 세션 밖의 순수 단계로 둔다(REQ-LDBARENTRY-006). 대안은 세션 메서드 안에 모두 넣는 것인데, 그러면 오디오 분석 시험이 세션 틀(콘솔 대역, 승인 채널)을 끌고 와야 해서 느리고, 합성 순서의 오류와 세션 배선의 오류를 시험이 가르지 못한다. 이 결정은 되돌리기 쉽다(함수 위치 이동).
5. **기계적 단계** — 동결 스냅샷 한 줄, 시험 틀 복제, 린트. 뒤로 둔다.

## §C. 마일스톤 (의존 순서, 시간 추정 없음)

의존 순서는 M1 → M2 → M3 → M4다. 각 마일스톤은 이전 마일스톤의 시험이 통과한 뒤에 시작한다. 아래 파일 이름과 함수 이름은 **가칭**이다 — run-phase가 확정한다.

### 파일 요약 (Tier 판단의 근거 — 코드를 짜 본 값이 아니다)

| 파일 | 구분 | 마일스톤 | 대략 줄 수(추정) |
|---|---|---|---|
| `server/audio/bar_map_entry.py` (가칭) | 신규 운영 | M1 | 60~90 |
| `server/web/session.py` | 수정(메서드 1개 + import) | M2 | 70~110 |
| `server/web/messages.py` | 수정(허용 목록 + 파서 분기) | M3 | 25~40 |
| `server/web/app.py` | 수정(디스패치 분기) | M3 | 25~35 |
| `server/tests/test_prechk_tool.py` | 수정(튜플 1줄 + 주석) | M3 | 5~10 |
| `server/tests/test_audio_bar_map_entry.py` | 신규 시험 | M1, M4 | 120~180 |
| `server/tests/test_session_bar_map_entry.py` | 신규 시험 | M2 | 180~260 |
| `server/tests/test_messages_bar_map_entry.py` | 신규 시험 | M3 | 50~80 |
| `server/tests/test_web_bar_map_entry.py` | 신규 시험 | M3 | 100~150 |

합계 9개 파일(운영 4, 기존 시험 수정 1, 신규 시험 4), 대략 635~955줄. Tier M 범위(5~15개 파일, 300~1000줄) 안이지만 줄 수는 상한 근처다. 추정을 넘으면 Tier L 신호가 아니라 **분리 신호**로 읽는다(UI를 이 SPEC에 끌어들이지 않는다).

### M1 — 합성 단계: 오디오 + 오프셋 → 마디 지도 또는 사유 (우선순위 High)

**산출물**: 세션·콘솔·UI 없이 바이트와 오프셋만 받아 마디 지도 사전 또는 사유가 든 실패 객체를 돌려주는 순수 함수 하나. 기존 함수만 쓰고 검증을 다시 구현하지 않는다(REQ-LDBARENTRY-006).

**하는 일(순서)**: (1) 오프셋 타입·범위 점검 — 디코드 전 (2) `detect_beat_grid` (3) 두 배 BPM 채택이면 실패(E1 확정) (4) `derive_bars` (5) `extract_bar_features`에 `bar_boundaries_ms` 전달 (6) `classify_bar_events` (7) `build_bar_map_payload`에 비트 목록·오프셋·`bpm`·`time_signature=(4, 4)`·사건 목록 전달. 박자표 `(4, 4)`는 이름 붙은 상수 한 곳에만 둔다(REQ-LDBARENTRY-015).

**교체 가능성(시험 대역의 전제)**: 합성 함수는 분석 단계 셋(`detect_beat_grid`, `extract_bar_features`, `classify_bar_events`)을 주입 가능한 인자로 받거나, 시험이 바꿔 끼울 수 있는 모듈 수준 이름으로 두어야 한다. 그래야 AC-005(기록용 분류기 대역)와 AC-009(멈추는 대역)가 운영 호출 지점을 바꾸지 않고 대역을 쓸 수 있다.

**시험**: `test_audio_bar_map_entry.py` — AC-005, AC-007 (합성 단계 쪽).

**위험**:
- 같은 오디오를 `detect_beat_grid`와 `extract_bar_features`가 각각 디코드한다(spec.md Gaps 1번). 지연이 문제가 되면 디코드 결과를 공유하도록 분석기를 고쳐야 하는데, 분석기는 이 SPEC의 범위 밖이다 — 그때는 이 SPEC을 멈추고 분석기 변경을 별도 SPEC으로 올린다.
- 실패 객체가 셋(`BeatGridFailure`, `BarMapFailure`, `BarFeaturesFailure`)이고 빌더는 예외(`BarMapStoreError`)다. 합성 단계는 이 넷을 하나의 실패 형태로 통일하되 **각 사유 문자열을 바꾸지 않고** 넘긴다.
- 합성 단계가 예외를 밖으로 내보내면 `to_thread` 작업이 조용히 죽어 응답이 없다(REQ-LDBARENTRY-012 위반). 분석기의 "예외를 밖으로 내보내지 않는다" 계약(`bar_map.py:226-228`)을 합성 단계가 이어받는다.
- 마디 번호 공간 불일치(P7). `extract_bar_features`의 `bar`는 경계 목록 인덱스 + 1이고 빌더는 마디 0을 따로 둔다. AC-005 (3)과 (4)의 양성 대조군(분류 단계를 기록용 대역으로 바꿔 특징 번호를 가로채고 마디 하나에 사건을 주입하며, 사건 0개면 FAIL)이 CI에서 이를 재고, 실제 분류기가 실제 오디오에서 낸 사건의 번호는 로컬 전용 AC-016이 잰다.

**검증 명령**:
```
python -m pytest server/tests/test_audio_bar_map_entry.py -q
python -m pytest server/tests/test_audio_bar_map.py server/tests/test_audio_bar_map_store.py -q   # 분석기·저장소 회귀
ruff check server/audio/bar_map_entry.py server/tests/test_audio_bar_map_entry.py
ruff format --check server/audio/bar_map_entry.py server/tests/test_audio_bar_map_entry.py
```

### M2 — 세션 메서드: 점검 → 합성 → 곡 대조 → 저장 → 응답 (우선순위 High)

**산출물**: `ChatSession`에 진입 메서드 하나(가칭 `analyse_bar_map`). 순서는 다음과 같다.

1. 첨부 오디오 읽기 — 없으면 이 메서드까지 오지 않는다(WS 분기가 먼저 막는다, M3). 세션 시험은 직접 불러도 안전하도록 방어 점검을 하나 둔다.
2. 싼 점검: 오프셋 범위, `store.latest` 존재 → 실패면 **전송 후** 반환(REQ-LDBARENTRY-007, 012).
3. 곡 열쇠 `_beat_grid_song_key(timeline)`를 요청 시점에 잡아 둔다(P15).
4. 오디오 바이트를 base64에서 풀어 합성 단계에 넘긴다(M1).
5. 실패면 사유를 실어 전송 후 반환.
6. 저장 직전 곡 열쇠를 다시 읽어 달라졌거나 타임라인이 없으면 거절(REQ-LDBARENTRY-009).
7. `store_timeline_bar_map(payload)` 호출. 그 관문의 거절 경로는 반환만 하고 전송하지 않으므로(P2) 반환된 이벤트가 성공 이벤트가 아니면 진입 메서드가 그 이벤트를 `_send`한다. 성공 여부는 관문의 반환 이벤트 모양이 아니라, 호출 뒤 `timeline_bar_map()`이 방금 넘긴 페이로드와 깊은 비교로 같은지로 가른다 — 관문의 문구가 바뀌어도 판정이 흔들리지 않게 한다.

`_song_audio`만 읽는다(첨부 바이트). `_song_bpm`과 `_song_analysis`는 읽지도 쓰지도 않는다 — 저장되는 `bpm`은 검출기 값만 쓴다(E4 (가), REQ-LDBARENTRY-011).

**시험**: `test_session_bar_map_entry.py` — AC-003, 004, 006, 007(세션 쪽), 008, 012, 013, 014, 015.

**위험**:
- 7단계의 성공 판별. 관문이 성공하면 `song_timeline`과 `chat_response`를 이미 보냈으므로 진입 메서드가 한 번 더 `chat_response`를 보내면 응답이 2개가 된다(AC-015 위반). 성공이면 추가 전송 0, 거절이면 정확히 1이 되도록 판별을 시험이 잡는다.
- 6단계는 읽기-쓰기 사이를 잠그지 못한다(Gaps 4번). 이 SPEC은 창을 좁힐 뿐이다.
- 이 메서드가 `session.py`(거대한 파일)에 들어간다. 위치는 `timeline_bar_map`(`:9365`) 바로 아래가 자연스럽다. `session.py`에는 같은 맥락의 메서드가 모여 있어 충돌 가능성이 크므로, 편집 전 Pre-Edit Sync Check를 한다.
- 거절 문구에 분석기의 예외 문구가 섞일 수 있다(Gaps 7번). 정제하는 경우 **사유 문자열의 의미를 지우지 않는** 선에서 한다.
- 진입 메서드는 작업 스레드에서 돈다. `_send`를 스레드에서 부르는 선례는 `analyse_song_audio`가 이미 있다(P11).

**검증 명령**:
```
python -m pytest server/tests/test_session_bar_map_entry.py -q
python -m pytest server/tests/test_session_bar_map_store.py server/tests/test_session_beat_grid_edit_t551.py -q   # 같은 파일의 이웃 메서드 회귀
ruff check server/web/session.py server/tests/test_session_bar_map_entry.py
ruff format --check server/web/session.py server/tests/test_session_bar_map_entry.py
```

### M3 — WS 타입 + 파서 + 디스패치 분기 + 동결 스냅샷 한 줄 (우선순위 High)

**산출물**:
- `messages.py`: 허용 목록에 새 타입, 파서 분기. 정수·비bool 점검(REQ-LDBARENTRY-002). 출력은 `{v, type, first_beat_offset}`만.
- `app.py`: 디스패치 분기. 순서는 `song_audio_analyse`와 같다 — 첨부 없음 → busy → `create_task(to_thread(session.진입메서드, offset))` (P11). 첨부 없음이 busy보다 먼저다.
- `test_prechk_tool.py`: `_EXPECTED_CLIENT_MESSAGE_TYPES`에 한 줄 + 사유 주석(`:1249`의 `"approval_decision",` 바로 다음, t551 주석 블록 앞).

**시험**: `test_messages_bar_map_entry.py` — AC-002. `test_web_bar_map_entry.py` — AC-001, 009, 010. `test_prechk_tool.py` — AC-011(역방향 실행 포함).

**위험**:
- 멈춘 시험이 프로세스째 끊긴다(`pyproject.toml:75-76`). AC-009·010의 멈추는 대역은 반드시 명시적 시간 상한을 둔다.
- 허용 목록에만 더하고 동결 튜플을 빠뜨리면 `test_prechk_tool.py:1499`에서 실패한다. 반대로 튜플을 먼저 더하고 목록을 빠뜨려도 같은 단언에서 실패한다. 두 줄은 한 변경에 있어야 한다.
- 정렬 위치. 동결 시험은 정렬한 수집 결과(`test_prechk_tool.py:1463`)를 리터럴 튜플과 `==`로 비교하므로(`:1499`) **리터럴 튜플도 정렬 순서여야 하고, 어긋나면 `:1499`에서 실패한다.** 새 원소와 사유 주석은 `:1249`의 `"approval_decision",` 바로 다음 줄, t551 주석 블록(`:1250-1261`) 앞에 둔다 — 그래야 t551 주석이 계속 `beat_grid_apply`에 붙어 있다.
- `ui/src/protocol.ts`를 건드리지 않는다(UI 범위 밖). 서버에만 있는 타입은 호출하는 클라이언트가 없다(Gaps 9번).
- `app.py`에는 `song_audio_analyse` 분기가 사람 응답 대기 때문에 `create_task`를 쓴다는 긴 주석이 있다. 새 분기를 이 분기 옆에 두면 읽는 사람이 이유를 혼동한다 — 새 분기의 주석은 "이유가 다르다: 분석 시간"을 적는다(REQ-LDBARENTRY-005).

**검증 명령**:
```
python -m pytest server/tests/test_messages_bar_map_entry.py server/tests/test_web_bar_map_entry.py server/tests/test_prechk_tool.py -q
python -m pytest server/tests/test_web_song_audio.py server/tests/test_web_messages.py server/tests/test_messages_beat_grid_t551.py -q   # 기존 프레임·분기 회귀
ruff check server/web/messages.py server/web/app.py server/tests/test_messages_bar_map_entry.py server/tests/test_web_bar_map_entry.py server/tests/test_prechk_tool.py
ruff format --check server/web/messages.py server/web/app.py server/tests/test_messages_bar_map_entry.py server/tests/test_web_bar_map_entry.py server/tests/test_prechk_tool.py
```
AC-011 역방향 실행: 튜플의 새 줄만 주석 처리하고 `python -m pytest server/tests/test_prechk_tool.py -q -k test_the_axis_adds_no_web_surface`를 돌려 FAIL을 확인한 뒤 되돌린다. 그 출력을 기록한다.

### M4 — 실제 곡 로컬 게이트 (우선순위 Medium)

**산출물**: `test_audio_bar_map_entry.py`에 AC-016 시험 하나. 원곡이 없으면 건너뛴다. 감독의 로컬 환경에서 한 번 돌리고 결과(적중률, 재현율, 정밀도, 벽시계 시간)를 `progress.md` §E.2에 기록한다.

**위험**:
- 원곡 경로는 저장소 밖이다(REQ-LDBARENTRY-016). 경로와 오프셋 1은 이 시험의 고정물로만 있고 운영 코드에는 들어가지 않는다.
- 건너뛴 시험은 통과가 아니다(acceptance.md §D 6). 로컬 실행 출력이 없으면 AC-016은 미검증으로 남는다.
- 지연이 길게 나오면(spec.md Gaps 1번) 그 값이 REQ-LDBARENTRY-005의 구조를 다시 따지게 만들 수 있다 — 구조는 이미 비차단이므로 바뀌는 것은 UI의 진행 표시 요구뿐이다.
- 사건 재현율·정밀도는 `SPEC-LDBARMAP-001`이 정한 문턱을 그대로 쓴다. 이 경로가 새 문턱을 만들지 않는다.

**검증 명령** (감독의 로컬 환경):
```
python -m pytest server/tests/test_audio_bar_map_entry.py -q -k real_song -s
```
시험 이름은 가칭이다.

## §D. 제약 (위반 금지)

- **PRESERVE(수정 금지)**: `server/audio/bar_map.py`, `server/audio/bar_map_store.py`, `server/audio/analyze.py`, `song_audio_analyse`의 파서 분기와 디스패치 분기와 `ChatSession.analyse_song_audio`, `ui/`, `console/`, `server/web/preview.py`(포매터 핀), 다른 SPEC 디렉터리.
- 콘솔 쓰기·읽기 0건. 라이브러리 저장 0건.
- 곡·장비 고유값을 운영 코드나 시험 상수로 박지 않는다(REQ-LDBARENTRY-016). 시험의 실제 곡 고정물은 AC-016 한 곳에만 둔다.
- 오디오 파일 비커밋.
- 공유 체크아웃에서는 `git add -A`·`git add .`·`git commit -a`를 쓰지 않고 경로를 명시해 올린다. 편집 전 병렬 세션 점검(`agent-common-protocol.md` Pre-Edit Sync Check)을 한다.
- 시간 추정을 쓰지 않는다. 우선순위와 순서만 쓴다.

## §E. 위험표

| 위험 | 영향 | 완화 |
|---|---|---|
| 전곡 분석이 길다(미측정) | 응답이 늦어 사용자가 멈춘 줄 안다 | 수신 루프 비차단(REQ-005), M4에서 첫 실측. 진행 표시는 UI 카드 |
| 두 배 BPM 채택 시 BPM·격자 불일치(P8, P9) | 소비자 마디 시작이 전부 어긋남 | E1 (가) 저장 거절(2026-10-14 확정) |
| 다른 곡 오디오를 현재 타임라인에 저장(E3, Gaps 8번) | 어긋난 지도가 조용히 저장됨 | 알려진 한계로 확정(E3, 2026-10-14) — 이 SPEC은 막지 못함. 후속 UI가 파일명을 보여 줘야 함 — 후속 카드로 넘길 항목 |
| 저장 관문 거절 경로가 전송하지 않음(P2) | 응답 없는 요청 | REQ-012, AC-015가 전송된 프레임을 센다 |
| 허용 목록과 동결 튜플의 불일치 | 동결 시험 실패 | 한 변경에 두 줄, AC-011 역방향 실행 |
| 시험이 멈춰 프로세스째 끊김 | CI 전체 실패 | 대역 대기에 명시적 시간 상한(`pyproject.toml:75-76`) |
| 분석 중 HTTP 불러오기가 타임라인 교체 | 엉뚱한 곡에 저장 | REQ-009의 곡 열쇠 대조. 같은 곡 재불러오기와 읽기-쓰기 사이는 못 막음(Gaps 4번) |
| 박이 적은 짧은 곡 | 특징 추출 실패 | 실패는 사유와 함께 거절(AC-006 (라)) |
| 실패 사유에 예외 원문 섞임(P17) | 화면에 기술 문구 노출 | Gaps 7번 — 정제 정책 확인 필요 |
| `session.py` 병렬 편집 충돌 | 병합 충돌, 남의 변경 손실 | 편집 전 점검, 경로 명시 스테이징 |

## §F. 안티패턴

- 입구를 `song_audio_analyse`에 얹어 BPM 확정 카드 흐름에 섞는 것(D3 (나)).
- 오프셋에 기본값 0을 두는 것(D1 (나)) — 어긋난 지도가 구조 검사를 통과해 저장된다.
- `validate_bar_map`의 규칙을 합성 단계에 복제하는 것(REQ-006).
- 반환된 이벤트만 믿고 전송하지 않는 것(P2).
- 시험이 대역 호출만 세고 와이어 위 프레임을 세지 않는 것 — `test_web_song_audio.py:550-555`가 적은 공허한 시험의 모양이다.
- "건너뜀"을 통과로 읽는 것(AC-016).

## §G. 교차 참조

- `SPEC-LDBARMAP-001` — 분석기(M2·M3)와 저장 관문(M4). 이 SPEC의 전제 전부.
- `SPEC-LDARRANGE-001` §5 항목 1 — 소비자 입력 모양. spec.md §6.1이 줄 단위로 대조했다.
- `server/web/app.py:760-794` — 따라 할 디스패치 틀. `server/web/session.py:9317-9372` — 저장 관문과 읽기. `server/design/beat_grid_send.py:232-284` — 소비자.
- `.claude/rules/moai/workflow/spec-workflow.md` § SPEC Complexity Tier — Tier M 상한.
