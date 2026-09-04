# SPEC-COPILOT-MUSICSYNC-001 — 음악 연동 3단계 · 사전 조사

조사 시점 2026-09-03 · 기준 `origin/main adae0ac` · 읽기 전용(쓰기 0건, 콘솔 접촉 0건)
출처: 보고서 `reports/app-fresh-eyes-review-20260903.md` §3.1·§4 P2, Explore 심층 조사

세 마일스톤은 **같은 축(시간)** 을 서로 다른 층에서 다룬다: M1은 시트가 이미 가진 시간을 잃지 않고 들여오는 일, M2는 시간을 **측정**해 만들어 내는 일, M3는 그 시간을 콘솔이 **재생**하게 하는 일이다. 세 층의 콘솔 쓰기 권한이 서로 다르다는 점이 이 SPEC의 핵심 제약이다.

---

## M1. cue-ex import 가 시간 열을 받는다

### 1.1 오늘의 파서 — 17열 정확 집합, 시간 열 0개

`server/lxseq/cue_parser.py:43-61` `CANONICAL_CUE_COLUMNS` = `Q#, Group, Dim, COL, POS, BM, FX, FX-Rate, FX-Phase, FX-Width, I-Fade, I-Delay, P-Fade, C-Fade, B-Fade, Snap, Note`. 시간 열 없음. 그리고 **정확 집합**이다 — `cue_parser.py:157-162` 가 `unexpected` 열이면 `UnexpectedCueColumnsError`. 독스트링(`:85-92`): 「덧붙은 열을 조용히 무시하면 시트에는 적혀 있는데 콘솔에는 없는 값이 된다」. `AC-LXSEQ4-002` 가 「모자람·남음 둘 다 거부」를 고정(`cue_parser.py:3`).

`LxseqCueRecord`(`:99-120`)·`CueRowPlan`(`server/lxseq/cue_mapper.py:334-371`)에도 시간 필드 없음. 매퍼가 나르는 시간은 페이드/딜레이뿐(`i_fade`·`i_delay`·`p_fade`·`c_fade`·`b_fade`) — 「얼마나 걸리는가」이지 「언제 시작하는가」가 아니다.

### 1.2 표준이 정한 시간 열 — `src/Lighting_Designer/01_스펙/LX-SEQ-SPEC-v2.1.md`

HEAD §2.1 (44-53행): `RUNTIME` 필수 **`mm:ss.f`** · `BPM` 선택(가변 `72→96`) · `TIME_SIG` · `TC_SOURCE` `LTC|MTC|MANUAL` 필수 · `TC_ORIGIN` 필수(TC 0점 정의) · `TC_METHOD` `VERIFIED|DERIVED` 필수(§2.4).

CUE 시트 §3.1 (14열): 3 `TC In` ● **`mm:ss.f`**(예 `01:12.5`), 미확인 시 문자열 `확인필요` · 4 `TC Out` ○ · 5 `Dur` ○ 자동 산출.

🔴 형식은 SMPTE `hh:mm:ss:ff` 가 아니라 **`mm:ss.f`**. 프레임 개념 없음. PRE-ROLL 은 **음수 TC 허용**(§3.2, 234행: `-00:30.0`). §3.6 규칙 2 (HARD): `TC In` 단조 증가, `TC Out` ≤ 다음 `TC In`. 규칙 4 (HARD): 숫자를 지어내지 않는다. §2.4: `DERIVED` 시트는 큐시트 상단과 **파생 산출물 모두에 경고 표기**, 리허설 LTC 대조 전까지 실행 확정본 아님.

### 1.3 🔴 결정적 사실 — CUE-EX 시트에는 TC 열이 없다 (openpyxl 실측)

`src/Lighting_Designer/03_곡파일_Sugar/LXSEQ_SAMPLE_01_Sugar_r3.xlsx` 6시트:

| 시트 | 헤더 행 | 헤더 |
|---|---|---|
| `HEAD` | 키-값 세로 | `SONG_TITLE`…`RUNTIME`·`BPM`·`TIME_SIG`…`TC_SOURCE`·`TC_ORIGIN`…`TC_METHOD` |
| **`CUE`** | 4행 | `Q#`, `Section`, **`TC In`**, **`TC Out`**, `Dur`, `Mood`, `Color(주/보조)`, `Intensity`, `Fixture Group`, `Movement`, `Effect`, `Transition`, `Fade`, `Note` |
| `NOTE` · `PATCH` · `PRESET` | 3행 | — |
| **`CUE-EX`** | 4행 | 17열 (파서와 동일) — **TC 열 0개** |

**`TC In` 을 나르는 시트는 `CUE` 하나뿐.** CSV(90행, BOM)도 17열. 실측 데이터 행: `Q010 | INTRO | 00:00.0 | 00:08.0 | 08.0 | 화사, 등장 | … | SNAP | 0.0`. HEAD 실측: `RUNTIME = 03:56.0`, `BPM = 120 (고정)` (⚠️ 한글 주석 붙은 문자열), `TC_SOURCE = LTC`, `TC_METHOD = DERIVED — 마디연산(1마디=2.000s) 도출. 음원 청취 미검증. 리허설 LTC 대조 필수.`

### 1.4 이미 있는 다리 — `cue_sheet_xlsx_base64`

`server/orchestrator/tools.py:5379-5428`: `import_lxseq_cues` 가 선택 인자 `cue_sheet_xlsx_base64` 로 `CUE` 탭을 읽는다(`min_row=5`), 인덱스 `0`(Q#)·`1`(Section)·`5`(Mood)·`12`(Fade) — **`2`(TC In)·`3`(TC Out)·`4`(Dur)를 건너뛴다.** 홑따옴표 fail-closed 검사(`:5417-5426`) 재사용 가능. 스키마 `tools.py:11234-11243`. **M1 은 새 시트 종류·새 업로드 프레임 없이 성립한다.**

### 1.5 TrigType/TrigTime 발화 자리 — 두 곳

(a) `server/looks/songcue.py:501-514` `_auto_advance_commands`: `Set Cue {n} Sequence {s} Property 'TrigType' 'Time'` + `'TrigTime' {_format_seconds(start_ms)}`; `_format_seconds`(`:517-521`) 입력 **밀리초 정수**. 타임코드 3줄 `:490-499`. 축 플래그 `SongCueTimingAxes`(`:97-99`), `build_songcue_timing`(`:309-340`), `skipped_axes`.

(b) `server/design/song_cue_composer.py:283-321` `CueTimingData` (`mode`, `trigger`, `start_ms`, `trig_time_seconds`, `timecode_number`, `follows_cue_number`); `follow_previous` 는 절대 시간 없음(`:298-301`). 계약 `server/design/song_plan.py:531-575` `CueTimingPayload`.

**구멍**: `cue_mapper.map_cues` 는 타이밍 어휘를 모른다. `CueBucket`(`cue_mapper.py:373-378`)에 시간 없음. `import_lxseq_cues` apply 번들(`tools.py:5985-5988`)은 `Store Cue … CueFade … /Merge /NoConfirm` 만 낸다 — `Set Cue … Property 'TrigType'` 0줄.

### 1.6 registry 판별자

`server/sheets/registry.py:362-369` `CUE_ROW` = `RequiredForbidden(required_columns=CANONICAL_CUE_COLUMNS)` (**포함** 검사, `:205-213`) vs 파서 정확 집합. 열을 덧붙여도 판별자는 맞히고 파서가 거절한다. 정규 목록에 시간 열을 **필수**로 넣으면 기존 CSV 가 `unknown_sheet_kind` 로 거절된다(`session.py:10025-10027`). 장래 `cue`(14열) 행 등재 시 `ambiguous_sheet_kind` 위험 → `forbidden_columns`(오늘 전 행에서 빈 튜플)로 갈라야 한다.

### 1.7 타임라인에 앉는 길

UI `SongTimelineSection`(`ui/src/protocol.ts:301-315`): `start_ms`, `cue_number`, `d_level`, `palette`, `position`, `texture`, `fx`, `accents`, `mib`, `trig_time_seconds`, `plan_status`. 서버 `server/web/session.py:1486-1508` 가 `TimestampedSection`(`server/design/song_plan.py:131-161`: `index`·`label`·`start_ms`·`end_ms`(선택)·`source`)에서 채움. `SongTimeline.tsx:24-32` 폭 = 다음 `start_ms` 차이, 마지막은 15초 가정 — `end_ms` 는 payload 에 안 실린다. `_timeline_store.latest`(`session.py:7416-7419`) process-wide.

**M1 종착지**: `CueBucket` → `TimestampedSection` 변환. `_song_timeline_payload`(`session.py:1429-1440`)는 `UnifiedSongLightingPlan` + `SongCueCompositionResult` 를 요구 → 임포트 경로는 **별도 얕은 투사** 필요.

### 1.8 M1 콘솔 쓰기 경계

`action="apply"` → `tools.py:6003-6068` `group_approval.request_approval` → 승인 시 `run_commands`. `preview` 는 쓰기 0(`:5320-5323`). 새 `Set Cue … Property` 줄도 **같은 승인 번들** 안. 분류: `Set Cue … Property …` 는 `classify_command`(`server/safety/classify.py:173-239`)에서 `safe`.

### 1.9 M1 테스트 자산

`test_lxseq_cue_parser.py`(17열·BOM) · `test_lxseq_cue_mapper.py` · `test_lxseq_cue_tool.py`(preview/apply, xlsx 경로) · `test_lxseq_cue_partial_ship.py`(AC-LXSEQ4-007) · `test_lxseq_cue_unresolved_refs.py` · `test_lxseq_cue_harness.py`(정본 CSV 전량) · `test_sheets_registry.py`·`test_sheet_kind_consumers.py`·`test_sheet_pipe.py` · `test_song_plan.py`·`test_song_cue_composer.py` · `test_songcue_timing.py` · `test_ma3_cue_part_timing.py`. 픽스처: `server/tests/fixtures/lxseq/` (cue-ex 사본 없음, 정본 직접 읽음).

---

## M2. 오디오 업로드 → BPM / 구간 경계 / 악센트 후보 → 확인 카드

### 2.1 이미 재어 둔 것 — `.moai/specs/SPEC-COPILOT-SONGSTD-001/feasibility.md` (2026-08-14)

합성 트랙(64s, 128 BPM, 경계 0/16/32/36s):

| 측정 | DSP (librosa 1.0.0) | LLM (gemini-2.5-flash) |
|---|---|---|
| BPM | **129.2 (오차 0.9%)** | 82 (오차 36%) — 실패 |
| 구간 경계 | 정답 일치 | 정답 일치 (±0.5s) |
| 에너지 등급 | 전부 정확 | 후렴 과소평가 |
| 온셋 | 257개 100% 격자 정렬 | 미측정 |

판정: 「**DSP가 측정, LLM이 제안, 사람이 확정**」. LLM 박자 결정은 기각. 64s WAV 2.7MB 인라인 성공. 「librosa 없음(**numpy도 없음**)」. `plan.md:59-70` M4 계획: 지연 import · `song_audio_upload` 프레임 · 합성 트랙 픽스처(BPM ≤3%, 경계 ±1s) · 실제 곡 1개. `spec.md:130-141` R6: LLM 은 BPM·박자를 결정하지 않는다; 분석 모듈은 **콘솔 무접촉**. **`server/audio/` 는 아직 없다.**

### 2.2 업로드 경로 종단

① `ui/src/App.tsx:830` accept 에 오디오 없음; `MAX_VECTORWORKS_UPLOAD_BYTES = 8 MiB`(`:94`) · ② 라우터 `App.tsx:632-641` 「첨부 버튼은 하나 — 파일 종류가 목적지를 고른다」, 「UI는 분류하지 않는다」(`:629-634`) · ③ 클라이언트 검증 `:549-578` · ④ `useCopilotSocket.ts:332-341` → `protocol.ts:506` · ⑤ 서버 `server/web/messages.py:194-225`, `VECTORWORKS_UPLOAD_EXTENSIONS`(`:24`), 8MiB 이중 검사 · ⑥ 디스패치 `server/web/app.py:494-504`; ⚠️ `:505-513` 주석이 **분기 누락으로 메시지가 조용히 버려진 사고**를 기록 — 새 프레임의 함정 · ⑦ `server/web/session.py:10019-10093` 판별·보관·sha256·notice(교체 시 반드시 말함 `:10073-10077`) · ⑧ `src-tauri/capabilities/default.json`: 「no http, no websocket, **no upload**」(AC-DEPLOY-027 Layer 3) → base64 프레임 재사용이 유일한 값싼 길 · ⑨ `registry.py:134-155` `read_header` 는 CSV 헤더를 읽으므로 오디오는 `unknown_sheet_kind` → **별도 프레임 `song_audio_upload`** 필요.

### 2.3 확인 카드 구조 — `server/web/question.py`

`QuestionRequest`(`:67-109`): `prompt`·`why`·`steps`·`commands`(복사 실행)·`options`(`label`·`description`·`selected`)·`multi`. `UNANSWERED`(`:38`), 타임아웃 600s(`:35`), `ANSWER_FREEFORM`(`:41`). 와이어 `protocol.ts:377-395`. 렌더러 `QuestionCard.tsx`.

**한계**: 평면 목록이라 「구간 N × (시각, 라벨, D)」 표 스키마 없음. 갈래: (i) `steps[]` 텍스트 표 + 확정/수정 · (ii) `multi=True` 구간당 옵션 1개 · (iii) 구조화 payload 추가(3층 변경). ⚠️ `ask_user` 툴 스키마(`tools.py:9683-9737`)는 「EXACTLY ONE question」이고 `selected`·`multi`·`commands` 는 모델에 미노출 → 구간표 카드는 **서버 코드가 세우는** 카드.

### 2.4 의존성 · 패키징

`pyproject.toml:7-22` 런타임: anthropic, fastapi, google-genai, keyring, lupa, openpyxl, python-osc, pyyaml, uvicorn, websockets. **`uv.lock` 실측: numpy · librosa · soundfile 없음.** `requires-python >=3.11`.

PyInstaller `packaging/GrandMA3-Copilot.spec`: librosa 체인 = numpy + scipy + numba + llvmlite + soundfile(libsndfile 네이티브) + audioread + pooch + joblib. numba/llvmlite 훅 까다로움, `.dylib` 서명(`packaging/sign.sh`) 전부에 걸림. **+150~300MB 예상.** 지연 import 는 기동만 줄이고 번들 크기는 못 줄인다. 대안(조사만): numpy+scipy 만으로 온셋·자기상관 BPM 직접 구현 → numba 체인 제거, 정확도 재측정 필요.

### 2.5 BPM 기본값 120 — 소비자 전량

`server/design/profile.py:74-75` `DEFAULT_BPM = 120.0`; `effective_bpm`·`bpm_is_default`(`:301-310`). 소비자: `interview.py:166, 223, 350`(「BPM 미지정, 120 기본값」 사용자 문구), `460`; `lint.py:27, 658, 693`(기본값이면 린트 안 돎); 테스트 `test_design_profile.py:11,42-48`, `test_design_interview.py:219`, `test_design_energy.py:158-160`. **계약**: DSP BPM 은 `MusicProfile.bpm` 으로 → `bpm_is_default=False` → 린트 켜짐·문구 사라짐. §11.3 `FX-Rate = SongBPM ÷ 사이클당 박수` 와도 연결. xlsx `BPM = "120 (고정)"` 문자열 파싱 필요.

### 2.6 M2 콘솔 쓰기 경계 — **0건**

`test_audio_boundary.py` 를 형제(`test_paperwork_boundary.py`·`test_scene_boundary.py`·`test_looks_boundary.py`·`test_fx_boundary.py`)와 같은 형태로.

### 2.7 M2 테스트 자산

`test_web_messages.py` · **`test_web_app.py`**(디스패치 분기) · `test_web_session.py` · `test_web_layout_image.py`(가장 가까운 선례) · `test_sheets_registry.py` · `test_web_question_channel.py` · `QuestionCard.test.tsx`·`protocol.test.ts`·`App.test.tsx` · `test_design_profile.py`·`test_design_energy.py`·`test_design_lint.py` · `test_architecture.py` · `packaging/verify_packaged_e2e.py`·`test_deploy_compile.py`.

---

## M3. 콘솔 타임코드 리허설

### 3.1 오늘 발화하는 3줄 — `server/looks/songcue.py:490-499`

`Store Timecode {n}` · `Set Timecode {n} Property 'Name' '{ascii}'` · `Assign Sequence {s} At Timecode {n}`. 이름 ASCII 강제. **`Record`·`Go`·`Off Timecode` 는 서버 코드에 0줄.**

### 3.2 슬롯 점유 판정 — `tools.py:2699-2712` 호출, `:2792-2845` 정의

free / occupied(거절, 슬롯 대체 안 함) / unknown(`timecode_go=False`). `:2823-2827`: `rig_paths["timecodes"]` 는 **`DEFAULT_RIG_CONTEXT_PATHS` 의 유일한 미검증 경로**. 「Degrading a feature beats overwriting an operator's show.」

### 3.3 M0 실측 — `SPEC-COPILOT-SONGCUE-001/progress.md:326, 354-378`

| 커맨드 | 결과 |
|---|---|
| `Store Timecode <n>` | OK (childCount 0→1) |
| `Set Timecode <n> Property 'Name' …` | OK |
| `Assign Sequence <s> At Timecode <n>` | OK (`TrackGroup 1` 생성) |
| `Record Timecode <n>` | OK (무장; `Off Timecode <n>` 로 해제 확인) |
| `Store Timecode <n> Sequence <s>` | **거부** `User Canceled Command` |
| `Stop Timecode <n>` | **거부** `Not implemented` |
| `Go Timecode 999` | **`Illegal object`** (`.moai/state/verify/songcue-m0/steps.jsonl:73`) — **재생 명령은 `Go` 가 아니다** |

「부정 프로브는 무력했다 … 판정을 가른 것은 생성 프로브다」(`:354`). TrigType 축(`:370-378`): `'Time'`·`'Follow'` OK, `'Zzz'` Illegal value, 없는 큐 Illegal object — 이 축은 `ok=True` 가 변별적. `:414`: 파괴 명령의 확인 대화상자 기본값은 「취소」.

### 3.4 응답기 되읽기 — 한 층 깊이만 실측

`progress.md:694` (M7 라이브): `state DataPool/Timecodes/901` → `node{class:"Timecode", name, childCount:1}`, `children[{class:"TrackGroup", i:1}]`. 풀 층 `:467, :512, :761`. **확인 가능**: 존재·`i`(풀 층 `i` 는 실번호, `:401`)·이름·TrackGroup 존재/개수. **미측정**: TrackGroup 아래 트랙·이벤트. F-1 함정(`:401`): 큐 자식 `i` 는 나열 위치. `No` property 1000배 스케일(`:458`).

### 3.5 안전 분류 — `server/safety/blacklist.yaml` v4 · `classify.py:173-239`

| 명령 | 분류 |
|---|---|
| `Store Timecode` · `Set Timecode … Property` · `Assign … At Timecode` | safe |
| **`Record Timecode <n>`** | **safe** — 블랙리스트에도 invoking 에도 없음 |
| `Go Timecode` · `Off Timecode` | invoking |
| `Delete Timecode` | blacklisted |

🔴 **`Record Timecode` 가 `safe`** 인데 콘솔을 녹화 무장 상태로 만들고, 해제는 `Off Timecode`(실측 1회)뿐. 선택지: (i) `blacklist.yaml` 등재(객체까지 2토큰, `:170-171` 선례; 코퍼스 재측정 절차 `:83-94, 130-147`) · (ii) 앱이 발화하지 않고 `commands[]`(`question.py:82-85`)로 운영자 복사 실행 · (iii) 둘 다.

### 3.6 운영자 절차 정본

`04_grandMA3/…ma3-runbook.md:46-47` 7단계: LTC IN → TC Slot 1 → Timecode 에디터에 GO 이벤트 배치. `ma3.txt:700` `[MANUAL]`. **정본 파이프라인 자체가 타임코드 이벤트 배치를 수작업으로 남긴다.**

### 3.7 녹화 뒤 앱이 확인할 수 있는 것

가능: 풀 childCount 증가 · 이름 일치 · TrackGroup 존재/개수 · 시퀀스 생존 · 큐 `TrigType`/`TrigTime` property(유망, 미측정). 불가/미측정: TrackGroup 아래 이벤트 · 음악과 맞는가(사람이 듣는다) · `truncated:true` 는 무결론 · 빈 풀 vs 죽은 풀.

### 3.8 M3 콘솔 쓰기 경계

앱 자체 발화: 없음. 운영자 승인 필요: `Record`/`Off`/재생(문법 미확정). 이미 게이트 통과: `Store Timecode` 3줄(`tools.py:2744-2747`). `_LOCKED` 는 보류(`:2750-2752`).

### 3.9 M3 테스트 자산

`test_songcue_timing.py` · `test_songcue_tool.py`(세 갈래) · `test_songcue_{bundle,map,report,sections}.py` · `test_safety_classify.py`·`test_safety_corpus.py`·`test_writegate.py` · **`test_safety_gate.py:30-57` `FakeConsole` 정본** · `test_safety_ruleset.py` · `test_measurement_corpus.py` · 응답기 4종 · `test_state_paging_callsite.py`·`test_truncate_disclosure.py` · `test_web_cue_monitor.py`·`SongTimeline.test.tsx`.

## 부록 A. 페이크 콘솔

`server/tests/test_safety_gate.py:30-57` `FakeConsole`: `executed`, `fail_on`, `unconfirmed_on`, `ping_ok`, `state_tree`; `query_state` 미등록 경로는 `RuntimeError`. 상속 `DeployableFakeConsole`(`test_deploy_transport.py:119-137`). ⚠️ `test_groupgen_tools.py:49` 동명 별개 클래스.

---

## Risks and open questions

- **R1 (M1, 상)** 17열 정확 집합 확장 방식 — AC-LXSEQ4-002 개정 vs `cue_sheet_xlsx_base64` 확장(CSV 만 가진 사용자는 시간 못 줌).
- **R2 (M1, 중)** `mm:ss.f` 경계값: 음수, `확인필요`, 1분 초과, 소수 자리. `확인필요` 를 0 으로 접으면 첫 박에 발사된다.
- **R3 (M1, 중)** TC 단조성 위반은 큐-간 관계 — `CueHold` 어휘에 자리 없음.
- **R4 (M1, 중)** 임포트 큐 → 타임라인 투사 함수 부재; `end_ms` 미전달.
- **R5 (M1, 하)** registry 모호성 — `forbidden_columns` 첫 사용.
- **R6 (M2, 상)** Tauri 「no upload」 방어선; base64 8MiB = 실효 6MiB, WAV/FLAC 초과.
  - ⚠️ **2026-09-03 만료 고지 (plan-audit D3 반증)** — 이 줄의 「실효 6MiB」는 **틀렸다.** `server/web/messages.py:218` 이 8 MiB 를 **디코드된 원본 바이트**(`len(payload)`)에 걸고, `:26` 의 base64 **문자열 길이** 상한(`((8MiB+2)//3)*4` ≈ 10.7 MiB, `:208` 에서 검사)은 그 8 MiB 에서 **파생**된 값이다. 즉 실효 원본 상한은 **8 MiB** 다. 6 MiB 는 8 MiB 를 base64 문자열 길이 쪽에 걸었을 때만 나오는 숫자이고 코드는 그 반대다. WebSocket 프레임 상한으로 6 MiB 를 뒷받침할 근거도 없다(`grep -rn 'max_size\|max_message' server/web/*.py` → 0건, rc=1). 이 줄은 **기록으로 남기고**, 처방은 `spec.md` REQ-MUSICSYNC-014 · `design.md §3` 이 정본이다.
- **R7 (M2, 상)** 번들 +150~300MB; 지연 import 는 크기 대책 아님.
- **R8 (M2, 상)** 배포 형태에서 DSP: (a) 인라인 (b) 둘째 사이드카(capability 확장) (c) 개발 모드 전용 + 수동 BPM 폴백.
- **R9 (M2, 중)** 구간표 카드 스키마 — 평면 목록으로는 부분 수정 불가.
- **R10 (M2, 하)** LLM 교차 검증은 1차 제외 권장.
- **R11 (M3, 상)** 재생 명령 문법 미확정 — 착수 전 프로브 필수.
- **R12 (M3, 상)** TrackGroup 아래 판독 미측정 — 못 읽으면 검증 범위 축소를 문면에.
- **R13 (M3, 상)** `Record Timecode` 가 `safe`.
- **R14 (M3, 중)** `rig_paths["timecodes"]` 유일 미검증 경로.
- **R15 (M3, 중)** 자식 `i` 함정 재발 가능.
- **R16 (전체, 중)** BPM 3원(측정·시트 문자열·FX-Rate) 정본 규칙 필요; `bpm_is_default` 는 2갈래만.
- **R17 (전체, 중)** `TC_METHOD: DERIVED` 경고가 파생 산출물 전부에 — `SongTimelineView` 에 칸 없음.

## Recommended approach

**0. 착수 전 프로브 3줄 (M3, 읽기/격리 슬롯)** — `state DataPool/Timecodes/<n>/TrackGroup 1` · 재생 명령 후보 4종(생성/효과 프로브로 가른다) · `rig_paths["timecodes"]` 실값 대조. 결과가 M3 범위를 정한다.

**1. M1 — `cue_sheet_xlsx_base64` 확장(권장)**: `tools.py:5411-5428` 에 `row[2]`·`row[3]` 추가 → 17열·registry 무변경(R1·R5 소멸). CSV 만인 사용자는 정직한 한계로 적는다. 순서: `mm:ss.f` 순수 파서(음수·`확인필요`·빈칸을 명시적 결과 타입으로, `None` 으로 접지 않는다) → `cue_meta` dataclass 승격 → 단조성 위반은 별도 목록 → `Set Cue … 'TrigType' 'Time'` + `'TrigTime'` 두 줄을 **같은 승인 번들**에(`_format_seconds` 를 순수 함수로 분리) → `TC_METHOD` 딱지 전파 → 별도 얕은 타임라인 투사.

**2. M2 — 순수 함수부터**: `server/audio/analyze.py`(bytes → `bpm`·`bpm_confidence`·`boundaries_ms`·`onsets_ms`·`rms_curve`·`d_candidates`, librosa 함수 내 import) → `test_audio_boundary.py` → 합성 트랙 픽스처(BPM ≤3%, 경계 ±1s) → `song_audio_upload` 프레임(`messages.py` → **`app.py` 분기** → `session.py`) → 카드는 오늘 스키마(`multi=True`, 구간당 옵션, `selected`)로 시작 → 측정 BPM 은 `MusicProfile.bpm` 으로 → **패키징 실측(빌드 전후 크기)을 완료 조건에**, 300MB 초과면 R8(c) 폴백 결정.

**3. M3 — 프로브 결과로 두 갈래**: 재생 문법 + TrackGroup 판독이 열리면 「준비(3줄) → 운영자에게 `Record` 를 `commands[]` 로 인계 → 사람이 녹화 → 앱이 되읽어 검증 → 타임라인 표시」; 안 열리면 검증을 존재·이름·TrackGroup 개수로 좁히고 `unverified`/`SongCueTimingSkip` 관례로 산출물이 스스로 말하게. 공통: `Record Timecode` 는 앱이 발화하지 않는다(R13 갈래 ii). `truncated` 는 무결론. M0 GO 3줄 밖으로 나가지 않는다.

**4. 순서**: **M1 → M3 프로브 → M2 → M3 본체**. M3 프로브는 반나절이고 M2 는 가장 길고 되돌리기 어렵다.

**5. 공통 검증 사이클**: 구현 → 스코프 pytest + ruff → 서버 재시작 → 앱 UI 라이브 → 커밋·푸시. M2 만 콘솔 단계 없음.
