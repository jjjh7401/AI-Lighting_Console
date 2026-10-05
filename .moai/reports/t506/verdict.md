# t506 판정서 — 타임코드 재생 실기 가능성 확인

카드 t506 · 레인 lane-3 · 워크트리 `.claude/worktrees/t506` · 브랜치 `WT-timecode-probe` (기준 `c11bc540`)
상태: **정지점 — 실기 쓰기 승인 대기** (2026-10-05). 콘솔 쓰기 0건, 쇼 저장 0건.

## 요약

| 미확인 | 지금 판정 | 근거 |
|---|---|---|
| (a) 타임코드 재생이 시퀀스 큐를 넘기는가 | **미측정** — 이번에는 잴 수단이 있다 | 9월 프로브는 효과를 잴 채널이 없었다. 이번에는 `Sequences/<n>` 의 `CURRENTCUE`(재생 중 `"Sequence 212.3"`, 꺼짐 `property not readable`)와 `Timecodes/<n>` 의 `CURSOR` 를 실기에서 읽을 수 있음을 확인했다 |
| (b) 이벤트를 앱 명령줄로 만들 수 있는가 | **명령줄로 가능하다고 본다(MA 자체 테스트 근거). 우리 콘솔에서는 미확인** | 설치본 grandMA3 2.4.2 의 MA 시스템 테스트 `#33162` 가 Lua 객체 API 없이 명령줄만으로 `CmdSubTrack` 과 `Go+` 이벤트 10개를 만들고 재생 결과를 검사한다. 앱 게이트도 이 줄들을 문법 단계에서 막지 않는다(리허설) |
| (c) 이벤트 수 상한·시간 정밀도 | **문서 근거 없음 · 미측정** | 공식 문서에는 상한·해상도가 없다. MA 테스트는 0.05초 간격 이벤트 10개를 1초 안에 넣고 마지막 큐 도달을 기대한다(정밀도 ≤ 0.05초를 시사하지만, 우리 실측이 아니다) |

## 1. 읽은 것

### 기존 프로브(저장소)

- `docs/research/ma3-effects/14-musicsync-m3a-timecode-probe-run2.md` — `Go`·`Go+`·`Pause`·`Toggle Timecode 999` 넷 다 `ok:true`. 하지만 되읽은 오브젝트 상태가 바이트까지 같았고, 그 채널은 재생 상태를 드러내지 않았다. 그래서 「효과 없음」이 아니라 「이 채널로는 잴 수 없음」이었다.
- `15-musicsync-m3b-rehearsal-verify.md` — 트랙 목록까지는 읽었지만, 이벤트 내용은 검증 범위 밖이었다.
- `.moai/reports/t498/verdict.md` — 타임코드 11·1 모두 `TimeRange` 아래 이벤트가 **0개**였다. 지금 앱 방식은 「타임코드가 시퀀스를 돌리고, 큐 전환은 각 큐의 Time 트리거가 맡는다」이다. 앱 코드 `server/looks/songcue.py:639-641` 은 `Store Timecode` · `Set … 'Name'` · `Assign Sequence … At Timecode` 세 줄만 낸다. 이벤트는 운영자의 `Record Timecode` 에 맡긴다(`server/orchestrator/songcue_timecode.py:46`).

### 공식 문서 · 설치본

- 타임코드 설정 「Playback and Record」 기본값은 **Manual Events** 다. 손으로 만든 큐 이벤트는 이 모드에서 Time 트리거 큐와 Follow 큐를 함께 돌린다. 그래서 대상 시퀀스에 Time 트리거 큐가 있으면 이벤트 효과와 섞인다. 이 프로브가 Go 트리거 시퀀스(9번)를 고른 이유다.
- `Timecode` 키워드 문서에는 하위 오브젝트(트랙·이벤트) 주소 문법이 없다.
- 설치본 `~/MALightingTechnology/gma3_2.4.2/shared/resource/lib_plugins/systemtests/db/system_test_timecode_record.lua`:
  - 녹화된 구조는 `Timecode > TrackGroup > Track(Target=시퀀스) > TimeRange > CmdSubTrack > 이벤트` 이다. 이벤트 속성은 `Token`(Goto/Go+ 등), `RawTime`/`Time`, `CueDestination` 이다.
  - **#33162**(명령줄 생성):
    `Store <TC>.1` → `Assign <seq> At <TC>.1.1` → `Store Type "CmdSubTrack" <TC>.1.1.1` → `cd <TC>.1.1.1.1` → `Store Property "Time" t "AbsTime" t "Token" "Go+"` ×10 → `cd root` → `Go <TC>` → 1초 뒤 `CurrentChild == Cue 10`
  - 「Check Playback at absolute time 0」 테스트는 `Go <TC>` 만으로 큐 1이 활성화된다고 기대한다. 원격 `Go Timecode` 가 재생을 시작한다는 MA 측 근거다.

### 실기 읽기 전용 판독 (2026-10-05, 응답기 1.6.5)

| 무엇 | 명령 | 관측 | 파일 |
|---|---|---|---|
| 타임코드 풀 | `state Timecodes` | 1·2·7·8·9·11·12·13 (8개). **14 비어 있음** | `r1_readonly.txt` |
| 슬롯 14 음성 대조군 | `state Timecodes/14` | `path segment not found: '14'` | `live_denyall/steps.jsonl` |
| TC12 TimeRange | `state …/12/1/2/1` | 자식 0 — 이벤트 없음 | `r1_readonly.txt` |
| TimeRange 속성 | `introspect …/12/1/2/1` | `TRACKGROUP`·`TRACK`·`START`·`DURATION`·`OFFSET` … | `r1_readonly.txt` |
| 재생 상태 채널 | `props Sequences/212 CURRENTCUE,CUENO` | `"Sequence 212.3"`, `"3"` | `r1_readonly.txt` |
| 대상 시퀀스 9 | `state Sequences/9` + 큐 `TRIGTYPE` | 「T215 SCRATCH DELETABLE」, 큐 1~5, 큐 1~4 전부 `Go`, 꺼짐(`CURRENTCUE` 읽기 불가) | `r3_seq_candidates.txt`, `r4_seq9_triggers.txt` |
| 시퀀스 목록 | `state Sequences`(+@15) | 21개. 2000 까지 있음 | `r2_sequences.txt` |

## 2. 최소 실기 프로브 설계

- 빈 타임코드 슬롯 **14**를 만들고, 트랙 1개에 시퀀스 **9**를 연결한다. `Go+` 이벤트는 1·2·3초에 하나씩 둔다.
- 기존 번호는 덮지도 지우지도 않는다. 시퀀스 9의 큐 내용도 바꾸지 않는다(재생만 한다).
- 판정 신호:
  - 재생 전: 시퀀스 9 `CURRENTCUE` 읽기 불가(꺼짐). 이것이 대조군이다.
  - `Go Timecode 14` 후 약 4.5초 동안 0.15초 간격으로 `CURRENTCUE` 와 TC14 `CURSOR` 를 쌍으로 읽는다.
  - **PASS(a)**: `9.1 → 9.2 → 9.3` 이 각각 약 1·2·3초에 나타나고, `CURSOR` 가 증가한다.
  - **PASS(b)**: 준비 직후 되읽기에서 `CmdSubTrack` 아래 이벤트 3개의 `TIME`·`TOKEN` 이 계획과 같다.
  - **(c)**: 전환이 처음 관측된 시각에서 이벤트 시각을 뺀 값. 조회 왕복 지연(샘플마다 `t_from_go` 의 앞뒤 값으로 기록)만큼은 불확실하다.
- 묶음 셋, 총 14줄 — `commands_for_approval.txt`:
  1. 준비 11줄 (`Store Timecode 14` … `cd root`)
  2. 재생 1줄 (`Go Timecode 14`)
  3. 해제 2줄 (`Off Timecode 14`, `Off Sequence 9`)
- 안전 장치(스크립트 `tc_probe.py`):
  - 시작 전에 슬롯 14 부재와 시퀀스 9 꺼짐을 다시 읽는다. 둘 중 하나라도 어긋나면 쓰지 않고 멈춘다.
  - `cd Timecode 14.1.1.1.1` 이 실패하면 뒤따르는 `Store Property` 3줄은 보내지 않는다. 루트 문맥에서 무엇을 만들지 모르기 때문이다. `cd root` 는 언제나 보낸다.
  - 묶음 전체를 위험으로 선언해(`BatchRisk`), 「안전」으로 분류된 줄이 승인 없이 혼자 나가지 않게 한다.
  - 승인 실행은 전부-거절 실행이 남긴 `approvals.json` 의 세 묶음과 **글자까지 같을 때만** 승인한다.
  - 게이트의 실행 직전 백업(SaveShow)은 t498·t501 과 같이 「보내지 않고 기록만」으로 바꿔 끼운다.
- 잔여물(승인 후): 타임코드 14 「T506 TCPROBE」가 남는다. 삭제는 하지 않는다(카드 금지). 시퀀스 9는 `Off` 로 돌려 놓는다.

## 3. 리허설과 전부-거절 실기

| 단계 | 명령 | 관측 |
|---|---|---|
| 가짜 콘솔 리허설 | `tc_probe.py rehearse --rehearse` | 게이트 문법 단계 통과 14/14. 세 묶음 실행 경로 끝까지. 가짜 모형 기준 전환 1.10·2.04·3.14초. 백업은 「기록만」 3회(`rehearse.stdout.txt`, `rehearse/`) |
| 실기 전부-거절 | `tc_probe.py live_denyall` | preflight `responder_ok`. 승인 요청 3묶음(11·1·2줄) 모두 거절. 감사 로그 기준 콘솔 명령 실행 **0건**, 거절 3, 읽기 4(state 3 + props 1), SaveShow 0 |

리허설은 스크립트 경로와 게이트 판정만 확인한다. 가짜 콘솔의 전환 시각은 콘솔 의미론의 증거가 아니다.

## 4. 게이트에서 발견한 것 (제품 쪽, 이 카드 범위 밖 — 기록만)

1. **`cd` 문맥의 `Store Property` 는 분류 사유가 0개다.** 리허설 게이트 판정에서 `cd Timecode 14.1.1.1.1` 과 `Store Property "Time" … "Token" "Go+"` 3줄은 사유가 비어 있었다. 반면 `Store Timecode` 와 `Assign Sequence` 는 블랙리스트에 걸렸다. 묶음 선언이 없는 평소 경로라면 이 줄들이 승인 없이 오브젝트를 만든다. 분류기가 `cd` 로 바뀐 위치를 보지 못하기 때문이다. 리듬 SPEC(t504)이 이 경로를 제품에 넣는다면 다뤄야 한다.
2. **실행 직전 백업이 SaveShow 다.** `server/safety/gate.py:497-500` 의 백업 규칙 ③ 은 승인된 위험 묶음마다 `SaveShow` 를 보낸다. 「쇼 저장 안 함」 조건 아래에서는 t498·t501 처럼 바꿔 끼워야 한다(이 프로브도 그렇게 했다).

## 5. 안 잰 것

- (a)·(b)·(c) 셋 모두 실기 쓰기 없이는 답이 나오지 않는다. 위 판정은 문서와 MA 테스트 코드를 읽은 결과이고, 우리 콘솔에서 잰 값이 아니다.
- 실기 콘솔의 grandMA3 버전은 재지 않았다. 응답기 1.6.5 만 확인했다. MA 테스트는 설치본 2.4.2 기준이다.
- `Store Timecode 14.1` 이 트랙 그룹 안에 Marker 트랙을 자동으로 만드는지(그러면 `.1.1` 이 Marker 를 가리킬 수 있다)는 MA 테스트 형태를 그대로 따랐을 뿐 확인하지 않았다. 준비 직후 되읽기가 이것을 드러낸다. Track 대상이 시퀀스 9가 아니면 재생 묶음을 보내기 전에 판정으로 적는다.
- 이벤트 수 상한은 이번 프로브(3개)로는 답할 수 없다. 리듬 층(곡당 수백 개)을 위해서는 승인 후 별도 단계가 필요하다.
