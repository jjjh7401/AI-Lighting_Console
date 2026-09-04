# SPEC-COPILOT-MUSICSYNC-001 — 인수 기준

> 각 항목은 **이진 판정 가능**해야 한다. 부정 대조군이 없는 항목은 통과해도 계기 고장과 구별되지 않는다.
> 오프라인 명령은 저장소 루트에서. 라이브 명령은 M3-a 프로브와 M3-b 리허설에서만, 운영자 승인 후.
>
> ⚠️ **AC 번호는 REQ 번호를 함의하지 않는다.** AC 는 절 단위로 묶여 `009`·`019`·`026`~`029` 가 비어 있고, REQ 는 `001`~`025` 연속이다. 두 체계가 우연히 겹치는 자리가 있어도 그것은 우연이며, **검증 대상은 각 AC 제목 끝의 `↔ REQ-…` 표시가 정본**이다. 역방향 전수는 §H 커버리지 표가 답한다.

## A. 실행 명령

```bash
# 오프라인 — M1 시트 시간열
uv run pytest server/tests/test_lxseq_cue_time.py server/tests/test_lxseq_cue_tool.py server/tests/test_lxseq_cue_mapper.py server/tests/test_lxseq_cue_parser.py -q

# 오프라인 — M1 회귀 (정본 CSV 전량 · 17열 정확 집합 무변경)
uv run pytest server/tests/test_lxseq_cue_harness.py server/tests/test_sheets_registry.py server/tests/test_sheet_kind_consumers.py -q

# 오프라인 — M2 분석 코어 + 경계
uv run pytest server/tests/test_audio_analyze.py server/tests/test_audio_boundary.py -q

# 오프라인 — M2 와이어 3층 (app.py 분기 포함)
uv run pytest server/tests/test_web_messages.py server/tests/test_web_app.py server/tests/test_web_session.py server/tests/test_web_question_channel.py -q

# 오프라인 — M2 BPM 정본
uv run pytest server/tests/test_design_profile.py server/tests/test_design_lint.py server/tests/test_design_energy.py -q

# 오프라인 — 아키텍처·패키징
uv run pytest server/tests/test_architecture.py server/tests/test_deploy_compile.py -q

# 프런트엔드
npx vitest run

# 패키징 크기 실측 (M2 완료 조건 — 전후 두 번)
du -sh dist/ 2>/dev/null; bash packaging/build.sh; du -sh dist/

# 라이브 — M3-a 프로브 (격리 슬롯 하나, 운영자 승인 후. 조회는 읽기 전용 query_state 12회 이하 · 프로브 5건 이하
#          · 쓰기는 spec.md §A.4 열거분 8건 이하 = 준비 3줄 + 재생 후보 4건 이하 + 해제 1줄)
# 아래 두 줄은 조회분이다. 재생 후보 발화와 해제(Off Timecode <n>)는 승인 게이트를 지나 별도로 나간다.
.venv/bin/python server/tools/responder_roundtrip.py --listen-port 9005 --skip-exec --path DataPool/Timecodes
.venv/bin/python server/tools/responder_roundtrip.py --listen-port 9005 --skip-exec --path "DataPool/Timecodes/<n>/TrackGroup 1"
```

> `test_audio_analyze.py`·`test_audio_boundary.py`·`test_lxseq_cue_time.py` 셋은 **`adae0ac` 에 아직 없다** — 본 SPEC 이 만든다. 나머지 15개 테스트 파일은 `adae0ac` 에 실재함을 확인했다.

---

## B. M1 — 시트 시간열 수용

**AC-MUSICSYNC-001** — 시트의 시각이 큐에 실린다 (↔ REQ-MUSICSYNC-001)
Given `LXSEQ_SAMPLE_01_Sugar_r3.xlsx` 의 `CUE` 탭이 `Q010 | INTRO | 00:00.0 | 00:08.0 | …` 을 담고 있고
When `import_lxseq_cues` 를 `cue_sheet_xlsx_base64` 와 함께 `action="preview"` 로 호출하면
Then 번들에 `Set Cue <n> Sequence <s> Property 'TrigType' 'Time'` 과 `Set Cue <n> Sequence <s> Property 'TrigTime' 0` 두 줄이 나란히 있고, `TrigTime` 값은 `TC In` 을 밀리초 정수로 환산한 뒤 `_format_seconds` 의미로 되돌린 값과 같다.

**AC-MUSICSYNC-002** — 두 줄이 같은 승인 번들 안에 있다 (↔ REQ-MUSICSYNC-025)
Given `action="apply"` 로 임포트하고
When 승인 요청에 실린 명령 목록을 확인하면
Then `Store Cue …` 와 `Set Cue … 'TrigType'`·`'TrigTime'` 이 **하나의 승인 번들**에 함께 있고, `preview` 호출에서는 콘솔 쓰기가 **0건**이며, M1 이 낸 `query_state` 호출 수가 변경 전과 **같다**(증가 0).

**AC-MUSICSYNC-003** [부정 대조군] — `확인필요` 는 발사되지 않는다 (↔ REQ-MUSICSYNC-002 · REQ-MUSICSYNC-004)
Given 어떤 행의 `TC In` 이 문자열 `확인필요` 이고
When 임포트하면
Then 그 큐에 대해 `TrigTime` 줄이 **한 줄도** 생성되지 않고, `TrigType` 줄도 생성되지 않으며, 그 큐가 시간 미확정으로 표시되어 페이로드에서 식별 가능하고, **다른 큐들의 번들은 그대로 만들어진다.**
그리고 Given 같은 행의 `TC In` 이 빈칸이거나 형식 불명(`abc`)이면 When 같은 호출을 하면 Then 결과는 같으며, 세 사유가 **서로 구별되는 값**으로 보고된다.

**AC-MUSICSYNC-004** [부정 대조군] — 어디에도 0 이 지어지지 않는다 (↔ REQ-MUSICSYNC-003)
Given 미확정 시각을 가진 시트를 임포트한 결과가 있고
When 그 결과의 큐별 타이밍 필드를 확인하면
Then 미확정 큐의 시각 필드는 **`0` 도 아니고 「0 처럼 쓰이는 `None`」도 아니며**, `TrigTime 0` 문자열이 번들 어디에도 나타나지 않는다(시각이 진짜 `00:00.0` 인 큐가 있다면 그 큐만 예외이고, 테스트는 두 경우를 갈라서 단언한다).

**AC-MUSICSYNC-005** [부정 대조군] — 단조성 위반이 목록으로 나오고 재정렬되지 않는다 (↔ REQ-MUSICSYNC-005)
Given `TC In` 이 `00:10.0 → 00:05.0` 으로 역행하는 두 행이 있고
When 임포트하면
Then 결과 페이로드에 **위반 목록**이 있고 그 항목이 두 행을 지목하며, 큐의 출력 순서는 **시트 순서 그대로**이고, `CueHold` 관련 필드에는 이 위반이 섞여 있지 않으며, **번들은 여전히 preview 가능하다.**
그리고 Given `TC Out` 이 다음 행의 `TC In` 보다 큰 경우도 When 같은 호출을 하면 Then 같은 목록에 별개 항목으로 실린다.

**AC-MUSICSYNC-006** [부정 대조군] — PRE-ROLL 음수가 받아들여지되 타임라인을 깨지 않는다 (↔ REQ-MUSICSYNC-006)
Given 어떤 행의 `TC In` 이 `-00:30.0` 이고
When 임포트하면
Then 그 큐의 `TrigTime` 은 음수 초로 발화되고, 그 큐는 **타임라인 투사에서 제외**되며 제외 목록에 이름이 오르고, `TimestampedSection` 생성 시 `SongPlanError` 가 **발생하지 않는다.**
그리고 Given 콘솔이 음수 `TrigTime` 인자를 **거절**하면(`plan.md §B` **B9 — 미측정 값 영역**. M0 는 양수만 실측했다: `SPEC-COPILOT-SONGCUE-001/progress.md:377`) When apply 경로가 그 거절 응답을 받으면 Then **그 큐 하나만** 시간 미확정으로 강등되어 AC-MUSICSYNC-003 과 같은 형태로 표시되고, 거절된 큐는 **별도 거절 목록**에 큐 번호와 콘솔 응답 문자열과 함께 오른다. 판정은 계수로 한다 — 페이로드에 **적용된 큐 목록**과 **거절된 큐 목록**이 둘 다 있고, 두 목록의 합집합이 이번 apply 가 시도한 큐 전수와 같으며 교집합은 비어 있다(되돌림 쓰기는 발화하지 않는다 — M1 의 쓰기는 기존 승인 번들 안의 명령뿐이다). 거절 사실은 완료 보고의 미검증 절에 B9 로 실린다.

**AC-MUSICSYNC-007** — `TC_METHOD: DERIVED` 경고가 세 곳에 전파된다 (↔ REQ-MUSICSYNC-007)
Given `HEAD` 시트의 `TC_METHOD` 가 `DERIVED — 마디연산…` 이고
When 임포트하면
Then 세 곳 — (a) 결과 페이로드 (b) 타임라인 투사 결과 (c) 큐 라벨 계열 — 각각의 경고 문자열이 **리터럴 부분문자열 `리허설 LTC 대조 전까지 실행 확정본이 아님` 을 포함**한다. 판정은 의역 동등성이 아니라 **`in` 검사 3회**이며, 셋 중 하나라도 리터럴을 담지 않으면 FAIL 이다.

**AC-MUSICSYNC-008** — CSV 만 준 호출이 정직한 한계를 말한다 (↔ REQ-MUSICSYNC-001 · REQ-MUSICSYNC-007)
Given `cue_sheet_xlsx_base64` 없이 CSV 만으로 임포트하고
When 결과를 확인하면
Then `TrigTime` 줄이 0건이고, 결과의 사유 문자열이 **리터럴 `시간 정보 없음` 과 리터럴 `manual_go` 를 둘 다 포함**하며(**`in` 검사 2회** — 의역 동등성 판정이 아니다), `cue_parser.CANONICAL_CUE_COLUMNS` 와 `server/sheets/registry.py` 의 diff 가 **비어 있다.**

---

## C. M2 — 오디오 분석 · 업로드 · 확인 카드

**AC-MUSICSYNC-010** — 분석 모듈이 콘솔을 만지지 않는다 (↔ REQ-MUSICSYNC-010)
Given `server/tests/test_audio_boundary.py` 가 형제 4종과 같은 형태로 존재하고
When 그 테스트를 실행하면
Then `server/audio/**` 에서 콘솔 포트·`run_commands`·`exec` 경로로의 참조가 **0건**임이 통과하고, 형제 테스트 4종도 함께 초록이다.

**AC-MUSICSYNC-011** — 합성 트랙이 정답 폭 안에 들고, 실패는 실패로 돌아온다 (↔ REQ-MUSICSYNC-008 · REQ-MUSICSYNC-011 · REQ-MUSICSYNC-012)
Given 128 BPM, 경계 `0/16/32/36s` 로 **코드가 생성한** 합성 트랙이 주어지고
When `analyze` 를 호출하면
Then `bpm` 은 `124.0` 이상 `132.0` 이하이고, `boundaries_ms` 의 각 경계가 정답에서 ±1000ms 안이며, `d_candidates` 의 등급이 정답과 일치하고, 호출 동안 파일 시스템·네트워크·콘솔 접촉이 **0건**이다.
그리고 Given 오디오가 아닌 바이트(예: 잘린 헤더, 빈 바이트열)를 주면 When 같은 함수를 부르면 Then **사유 문자열을 담은 실패 결과**가 돌아오고, 예외가 호출자 밖으로 나가지 않으며, 부분 결과가 성공 형상으로 반환되지 **않는다**.

**AC-MUSICSYNC-012** [부정 대조군] — 저장소에 실제 곡이 없다 (↔ REQ-MUSICSYNC-011)
Given 본 SPEC 의 변경 집합이 있고
When `server/tests/fixtures/` 이하에서 오디오 확장자(`.wav`·`.flac`·`.mp3`·`.m4a`)를 가진 **커밋된 파일**을 열거하면
Then 개수가 **0** 이며, 픽스처는 생성 스크립트로만 존재한다.

**AC-MUSICSYNC-013** [부정 대조군] — `app.py` 분기가 없으면 테스트가 실패한다 (↔ REQ-MUSICSYNC-013)
Given `song_audio_upload` 프레임을 **WebSocket 층을 실제로 지나서** 보내는 테스트가 있고
When `server/web/app.py` 의 해당 디스패치 분기를 제거한 상태로 실행하면
Then 그 테스트는 **실패한다.** (session 메서드를 직접 부르는 테스트만으로는 이 층을 지나지 않으므로 통과해 버린다 — 그 사실을 테스트 주석이 명시한다.)

**AC-MUSICSYNC-014** [부정 대조군] — 상한 초과가 한국어 사유로 거절된다 (↔ REQ-MUSICSYNC-013 · REQ-MUSICSYNC-014)
Given 8 MiB 를 넘는 WAV 를 base64 로 실은 프레임을 보내고
When 서버가 처리하면
Then 거절되고, 사유 문자열이 한국어이며 **상한 수치를 명시**하고, 세션에는 아무것도 보관되지 않으며, `src-tauri/capabilities/default.json` 의 diff 가 **비어 있다.**
그리고 Given 상한 이하의 정상 파일이면 When 같은 경로로 보내면 Then 보관되고 sha256 과 바이트 수가 고지되며, 기존 첨부를 교체한 경우 그 사실이 별도로 말해진다.

**AC-MUSICSYNC-015** — 확인 카드가 오늘 스키마로 서고, 숫자는 사람이 정한다 (↔ REQ-MUSICSYNC-009 · REQ-MUSICSYNC-015)
Given 분석 결과가 구간 N 개를 담고 있고
When 확인 카드를 세우면
Then `QuestionRequest.multi` 가 `True` 이고, `options` 개수가 N 이며, DSP 가 제안한 구간의 `selected` 가 `True` 이고, 카드를 세운 주체가 **서버 코드**임이 호출 경로로 확인되며, `ask_user` 툴 스키마는 변경되지 않았고, BPM 값이 **LLM 응답에서 파생된 경로가 0건**임이 호출 그래프로 확인된다.

**AC-MUSICSYNC-016** — 측정 BPM 이 기본값 표식을 끈다 (↔ REQ-MUSICSYNC-016)
Given 사람이 확인 카드에서 BPM `128` 을 확정하고
When 그 값으로 `MusicProfile` 을 만들면
Then `bpm_is_default` 가 `False` 이고, `effective_bpm` 이 `128.0` 이며, 린트 L11 이 실행되고, 「BPM 미지정, 120 기본값」 문구가 사용자 출력에 **나타나지 않는다.**
그리고 Given 아무도 BPM 을 주지 않으면 When 같은 경로를 지나면 Then 오늘과 같이 `120.0` · `bpm_is_default=True` 이며 문구가 그대로 나온다(회귀 없음).

**AC-MUSICSYNC-017** — 번들 크기가 숫자로 기록되고 300MB 가 판정선이다 (↔ REQ-MUSICSYNC-018)
Given `packaging/build.sh` 를 변경 전후로 실행하고
When 두 결과를 비교하면
Then 완료 보고에 **두 숫자와 그 차이**가 명령 출력 그대로 실려 있고, 차이가 **300MB** 를 넘으면 폴백(개발 모드 전용 분석 + 수동 BPM 입력)이 선택되었음이 같은 보고에 적혀 있으며, 폴백을 택한 경우에도 확인 카드 경로와 `bpm_is_default` 고지가 살아 있음이 테스트로 확인된다.

**AC-MUSICSYNC-018** [부정 대조군] — BPM 3원 불일치가 숨지 않는다 (↔ REQ-MUSICSYNC-009 · REQ-MUSICSYNC-017)
Given 시트 `HEAD.BPM` 이 `120 (고정)` 이고 측정 BPM 이 `128` 이며 둘이 어긋나고
When 임포트·분석을 모두 거치면
Then 불일치가 사용자에게 보고되고, 채택된 값이 **`128`(측정)** 이며 그 근거가 「측정 > 시트 > 기본값」으로 명시되고, 어느 쪽도 **조용히** 채택되지 않는다.
그리고 Given `FX-Rate` 역산값이 셋과 또 어긋나면 When 같은 경로를 지나면 Then 그 값은 **대조 항목으로만** 보고되고 채택 후보에 오르지 않는다.

---

## D. M3 — 콘솔 타임코드 (프로브 선행 · 리허설)

**AC-MUSICSYNC-020** — M3-a 세 프로브가 기록된다 (↔ REQ-MUSICSYNC-019)
Given 격리 슬롯에서 프로브 세 건을 실행하고
When 프로브 노트를 확인하면
Then ① `TrackGroup` 아래 판독 결과(자식 유무 · `childCount` · `truncated` 판독값) ② 재생 명령 후보별 **효과** 판정 ③ `rig_paths["timecodes"]` 실값 대 M0 문자열 대조 — 셋이 모두 실행 일자와 함께 기록되어 있다.

**AC-MUSICSYNC-021** [대조군] — 프로브가 계기 생존과 부재 판별을 모두 보이고 예산 안에 있다 (↔ REQ-MUSICSYNC-019 · REQ-MUSICSYNC-025)
Given 같은 스윕에 **양성 대조군**(이미 판독된다고 알려진 경로, 예: 타임코드 풀 자체)과 **음성 대조군**(존재하지 않는 슬롯 번호)을 넣고
When 스윕을 실행하면
Then 양성 대조군은 값을 답하고, 음성 대조군은 부재를 부재로 답하며, 두 사유 문자열이 노트에 **그대로** 기록된다. 이 두 대조군이 없으면 다른 모든 결과는 결론의 근거가 되지 못한다.
그리고 When 스윕 전체의 프로브 수 · `query_state` 호출 수 · 콘솔 쓰기 명령을 **가짜 콘솔(또는 감사 로그 `executed` 이벤트)에서 세면** Then 프로브는 **5건 이하**, 조회는 **`query_state` 12회 이하**이며 각 프로브의 조회 수가 노트에 **숫자로** 적혀 있고, 발화된 쓰기는 `spec.md §A.4` M3-a 행이 열거한 것과 **정확히 일치**한다 — ① 슬롯 준비 3줄(`Store Timecode <n>` · `Set Timecode <n> Property 'Name' '<ascii>'` · `Assign Sequence <s> At Timecode <n>`) ② 재생 명령 후보 **4건 이하** ③ 해제 1줄(`Off Timecode <n>`), **합계 8건 이하**. 그 열거 밖 명령은 **0건**이고, 격리 슬롯이 아닌 대상(쇼 시퀀스·다른 타임코드 슬롯)을 향한 쓰기도 **0건**이다.
그리고 Given `_timecode_slot_verdict`(`server/orchestrator/tools.py:2792`)가 대상 슬롯에 **occupied** 또는 **unknown** 을 답했으면 When 스윕을 실행하면 Then 콘솔 쓰기가 **0건**이고, 스윕은 성공도 실패도 아닌 **무결론**으로 노트에 기록되며 그 사유 문자열이 함께 적힌다.

**AC-MUSICSYNC-022** [부정 대조군] — 앱은 `Record Timecode` 를 쏘지 않는다 (↔ REQ-MUSICSYNC-020)
Given 본 SPEC 의 전 작업이 끝났고
When 앱이 발화한 명령 전수(감사 로그 `executed` 이벤트 + 승인 번들 목록)에 대해 `grep -c 'Record Timecode'` 를 **잘림 없이** 실행하면
Then 결과는 **0** 이다.
그리고 Given 리허설이 실제로 수행되었으면 When 운영자 인계 경로를 확인하면 Then 그 명령은 `QuestionRequest.commands[]` 에만 문자열로 존재하고, `server/safety/blacklist.yaml` 의 diff 는 **비어 있다**(등재는 후속 카드 — `plan.md §C` 결정 2).

**AC-MUSICSYNC-023** — 준비 3줄이 그대로 통과한다 (↔ REQ-MUSICSYNC-023)
Given M3-b 준비 단계를 실행하고
When 발화된 명령을 확인하면
Then `Store Timecode <n>` · `Set Timecode <n> Property 'Name' '<ascii>'` · `Assign Sequence <s> At Timecode <n>` 세 줄뿐이며, M0 GO 목록 밖의 명령이 **0건**이다.
그리고 Given M3-a 가 어떤 재생 명령의 효과를 증명하지 못했으면 When 인계 목록을 확인하면 Then 그 명령은 목록에도 코드에도 **없다.**

**AC-MUSICSYNC-024** [부정 대조군] — 판독 불가가 성공으로 위장되지 않는다 (↔ REQ-MUSICSYNC-022)
Given M3-a 가 `TrackGroup` 아래를 판독하지 못했다고 기록했고
When M3-b 검증 산출물을 확인하면
Then 판정은 **존재 검사 셋으로만** 내려진다 — (a) 산출물에 5절 표제 다섯(`주장` · `증거` · `기준 귀속` · `미검증` · `잔여 위험`)이 `grep -c` 로 각각 **1 이상** (b) 그 `미검증` 절이 리터럴 `unverified` 또는 리터럴 `SongCueTimingSkip` 중 **적어도 하나를 포함** (c) 산출물의 판정 필드 값이 `unverified` 또는 `SongCueTimingSkip` 이고 **`verified` 가 아니다**. 셋 다 참이어야 PASS 다.
의역의 **부재**를 증명하라고 요구하지 않는다 — 「검증 완료 취지의 문구가 없다」는 기계 판정이 원리적으로 불가하므로, 같은 목적을 **존재 판정으로 뒤집어** 건다.

**AC-MUSICSYNC-025** [부정 대조군] — 되읽기 네 축이 값으로 남고 `truncated` 는 결론이 되지 않는다 (↔ REQ-MUSICSYNC-021)
Given 되읽기 응답이 `truncated: true` 를 실었고
When 검증 판정을 내리면
Then 판정은 성공도 실패도 아닌 **무결론**으로 기록되고, `childCount` 대조 없이 「전부 읽었다」는 문장이 산출물에 **없다.**
그리고 Given 되읽기가 정상 응답이면 When 검증을 수행하면 Then 풀 `childCount` 증가 · 이름 일치 · `TrackGroup` 존재/개수 세 축이 각각 **값과 함께** 기록되고, 이벤트 내용은 **M3-a 가 열어 준 경우에만** 넷째 축으로 추가되며, 검증 1회가 낸 `query_state` 호출 수가 **4회 이하**다.

---

## E. 횡단

**AC-MUSICSYNC-030** — 마일스톤별 콘솔 예산이 쓰기·조회 양쪽에서 지켜진다 (↔ REQ-MUSICSYNC-025)
Given 본 SPEC 의 전 작업 로그가 있고
When 마일스톤별로 앱이 발화한 콘솔 **쓰기**를 세면
Then M1 은 기존 `group_approval` 경로 밖 쓰기가 0건, **M2 는 총 0건**, M3-a 는 `spec.md §A.4` 가 열거한 **8건 이하**(슬롯 준비 3줄 + 재생 후보 4건 이하 + 해제 1줄, 전부 **격리 슬롯 하나**를 향한다)뿐, M3-b 는 §D 준비 3줄과 운영자가 실행한 명령뿐이다.
그리고 When 같은 로그에서 앱이 낸 **조회**(`query_state`)를 세면 Then **M1 은 변경 전과 같고(증가 0)**, **M2 는 총 0건**, M3-a 는 **`query_state` 12회 이하**(프로브는 5건 이하 — 두 축이 각각의 단위로 판정된다)이며 프로브별 조회 수가 노트에 숫자로 적혀 있고, M3-b 는 검증 1회당 4회 이하이며, 상한을 넘겨 얻은 판독이 있다면 그것은 결론이 아니라 **무결론**으로 보고돼 있다.

**AC-MUSICSYNC-031** — 완료 보고가 5절 형식을 갖춘다 (↔ REQ-MUSICSYNC-024)
Given 본 SPEC 의 완료 보고가 작성됐고
When 그 보고를 확인하면
Then 주장 · 증거(명령과 그 출력) · 기준 귀속 · **미검증** · 잔여 위험 다섯 절이 모두 있고, 미검증 절에 최소한 B4(재생 명령 문법) · B5(`TrackGroup` 아래 판독) · B7(번들 증가 실측 전 추정치) · B8(M3-a `query_state` 계상) · **B9(음수 `TrigTime` 인자의 콘솔 수용 여부)** 의 잔여분이 명시돼 있다.

---

## F. 완료 정의 (Definition of Done)

- [ ] §A 오프라인 명령 6줄 + `npx vitest run` 전부 초록, 출력 그대로 인용.
- [ ] AC-MUSICSYNC-001~008 통과 (부정 대조군 4종 포함), `cue_parser.py`·`registry.py` diff 비어 있음.
- [ ] AC-MUSICSYNC-010~018 통과 (부정 대조군 4종 포함), **콘솔 접촉 0** 이 기계로 고정됨.
- [ ] 번들 크기 전후 두 숫자가 보고에 실림 (AC-MUSICSYNC-017). 델타 300MB 초과 시 폴백 선택이 기록됨.
- [ ] M3-a 프로브 노트 존재, 양성·음성 대조군 포함, **프로브 5건 이하 · `query_state` 12회 이하 · 콘솔 쓰기 8건 이하(§A.4 열거분)** + 프로브별 조회 수 기록 (AC-MUSICSYNC-020·021).
- [ ] `grep -c 'Record Timecode'` 가 앱 발화 전수에서 **0** (AC-MUSICSYNC-022). `blacklist.yaml` diff 비어 있음.
- [ ] M3-b 가 두 갈래 중 하나로 명시적으로 닫힘 — 「나중에」는 종점이 아니다 (AC-MUSICSYNC-024).
- [ ] 콘솔 예산이 쓰기·조회 양쪽에서 숫자로 확인됨 (AC-MUSICSYNC-002·030).
- [ ] 완료 보고 5절, 미검증 절 비어 있지 않음 (AC-MUSICSYNC-031).
- [ ] §H 커버리지 표의 25개 REQ 행이 전부 최소 1개 AC 를 갖고, 그 AC 가 실제로 통과함.

---

## H. 커버리지 (REQ → AC 역방향 전수)

REQ 는 `001`~`025` 연속 25개, AC 는 25개(번호는 절 단위 블록이라 `009`·`019`·`026`~`029` 가 빈다). 아래 표가 **정본**이며, 표에 없는 대응은 대응이 아니다.

| REQ | 절 | AC | 비고 |
|---|---|---|---|
| REQ-MUSICSYNC-001 | R1 | AC-001 · AC-008 | 시간 열 판독(있는 경우) + 없는 경우의 정직한 한계 |
| REQ-MUSICSYNC-002 | R1 | AC-003 | 결과 종류 5종이 구별 가능한가 |
| REQ-MUSICSYNC-003 | R1 | AC-004 | 0 으로 접지 않음 — 부정 대조군 |
| REQ-MUSICSYNC-004 | R1 | AC-003 | 미확정 큐에 두 줄 미생성 |
| REQ-MUSICSYNC-005 | R1 | AC-005 | 단조성 위반 별도 목록 |
| REQ-MUSICSYNC-006 | R1 | AC-006 | PRE-ROLL 음수 분리 |
| REQ-MUSICSYNC-007 | R1 | AC-007 · AC-008 | `TC_METHOD` 3곳 전파 + CSV 한계 |
| REQ-MUSICSYNC-008 | R2 | AC-011 | 분석 함수 순수성 + 반환 6필드 |
| REQ-MUSICSYNC-009 | R2 | AC-015 · AC-018 | LLM 이 숫자를 정하지 않음 — 호출 그래프 + 불일치 보고 |
| REQ-MUSICSYNC-010 | R2 | AC-010 | 콘솔 접촉 0건 기계 고정 |
| REQ-MUSICSYNC-011 | R2 | AC-011 · AC-012 | 합성 트랙 정답 폭 + 실제 곡 0건 |
| REQ-MUSICSYNC-012 | R2 | AC-011 | 실패 결과 반환 · 예외 미전파 (AC-011 둘째 Given) |
| REQ-MUSICSYNC-013 | R3 | AC-013 · AC-014 | 세 층 통과 + `app.py` 분기 부정 대조군 |
| REQ-MUSICSYNC-014 | R3 | AC-014 | 8 MiB 상한 · 한국어 사유 · Tauri capability diff 0 |
| REQ-MUSICSYNC-015 | R3 | AC-015 | 확인 카드를 서버 코드가 세움 |
| REQ-MUSICSYNC-016 | R3 | AC-016 | `bpm_is_default` 를 끔 + 회귀 없음 |
| REQ-MUSICSYNC-017 | R3 | AC-018 | 3원 불일치 보고 + 우선순위 · `FX-Rate` 대조 전용 |
| REQ-MUSICSYNC-018 | R3 | AC-017 | 번들 전후 숫자 + 300MB 판정선 |
| REQ-MUSICSYNC-019 | R4 | AC-020 · AC-021 | 세 프로브 기록 + 대조군 |
| REQ-MUSICSYNC-020 | R4 | AC-022 | `Record Timecode` grep 0 |
| REQ-MUSICSYNC-021 | R4 | AC-025 | 되읽기 네 축 + `truncated` 무결론 |
| REQ-MUSICSYNC-022 | R4 | AC-024 | 좁힌 범위를 산출물이 스스로 말함 |
| REQ-MUSICSYNC-023 | R4 | AC-023 | 효과 증명된 명령만 인계 |
| REQ-MUSICSYNC-024 | R5 | AC-031 | 5절 보고 |
| REQ-MUSICSYNC-025 | R5 | AC-002 · AC-021 · AC-030 | 콘솔 예산 — M1 승인 번들 · M3-a 프로브 5건 · M3-b 검증 4회 |

**미대응 0건**: 25개 REQ 가 모두 최소 1개 AC 를 갖는다. 역으로 25개 AC 가 모두 최소 1개 REQ 를 지목한다.
