# SPEC-COPILOT-MUSICSYNC-001 — 구현 계획

> 정본은 `spec.md`. 이 문서는 **되돌리기 어려운 결정을 먼저** 놓고 기계적인 작업을 뒤로 미룬 실행 순서다.
> 기준 트리 `origin/main adae0ac` · 조사 근거 `research.md` · 설계 근거 `design.md` · 개발 방식 TDD.

## A. 맥락

세 마일스톤은 **같은 축(시간)** 을 다루지만 **되돌리는 비용이 크게 다르다.**

- **M1** 은 서버 안에서 끝난다. 파일 몇 개, 되돌리기 쉬움. 다만 `TrigTime` 이 승인 번들에 들어가는 순간 **콘솔 큐의 발사 시각이 바뀐다** — 되돌리려면 다시 승인이 든다.
- **M3-a(프로브)** 는 반나절이고 쓰기가 거의 없는데 **M3-b 의 형상을 통째로 정한다.** 늦게 하면 그때까지 지은 것이 근거 없는 가정 위에 서 있게 된다.
- **M2** 는 **가장 길고 가장 되돌리기 어렵다** — 의존성이 번들에 박히고, 새 와이어 프레임이 세 층을 지나며, 그 프레임의 형상은 배포된 뒤에 바꾸기 어렵다.
- **M3-b** 는 운영자·실기·LTC 가 있어야 서므로 마지막이다.

그래서 순서는 「쉬운 것부터」가 아니라 **「바뀔 가능성이 큰 결정부터, 다만 남을 것을 정하는 측정을 먼저」**다.

## B. 알려진 문제 (착수 전 재측정 대상)

| # | 항목 | 상태 |
|---|---|---|
| B1 | `research.md §1.4` 는 `cue_sheet_xlsx_base64` 블록을 `tools.py:5379-5428` 로 적었다. 2026-09-03 실측은 인자 취득 **`:5385`**, 행 루프 `:5404`, 열 인덱스 판독 `:5405-5412`, 홑따옴표 fail-closed `:5417-5426`, `cue_meta` 기록 `:5427` 이다. 6줄 이내 드리프트이며 본 계획이 정정한다 | 측정됨 (정정 완료) |
| B2 | **`TimestampedSection.start_ms` 는 `minimum=0`** 이다(`server/design/song_plan.py:143`, 실측). research.md 에 없는 사실이며 PRE-ROLL 음수 TC 와 직접 충돌한다 → REQ-MUSICSYNC-006 이 분리로 해소 | 측정됨 (본 계획이 추가) |
| B3 | `server/safety/` 전체에 `Timecode` 문자열이 **0건**이다 — `grep -rn 'Timecode' server/safety/` 를 17개 항목(`blacklist.yaml` 포함) 전수에 대해 잘림 없이 돌린 결과다. research.md §3.5 의 분류표는 **객체별 등재가 아니라 동사 규칙의 귀결**이다 — 즉 `Record Timecode` 가 `safe` 인 것은 누락이 아니라 설계상 결과다 | 측정됨 (해석 정정) |
| B4 | 재생 명령 후보 4종의 실제 문법. `Go Timecode 999` 만 기각이 실측돼 있다(`.moai/state/verify/songcue-m0/steps.jsonl:73`) | **미측정 → M3-a 산출물** |
| B5 | `TrackGroup` 아래 트랙·이벤트 판독 가능성 | **미측정 → M3-a 산출물** |
| B6 | `rig_paths["timecodes"]` 실값 — `DEFAULT_RIG_CONTEXT_PATHS`(`tools.py:340`)의 **유일한 미검증 경로**이며 코드 주석이 그렇게 못박는다(`tools.py:2820-2824`) | **미측정 → M3-a 산출물** |
| B7 | librosa 체인 실제 번들 증가분. 「+150~300MB」는 **추정**이며, 상한 300MB 는 §C 결정 1 이 정한 판정선이지 측정값이 아니다 | **미측정 → M2 완료 조건** |
| B8 | M3-a 스윕의 실제 `query_state` 호출 수가 상한 **12회** 안에 드는지. 예산은 **조회 수(`query_state` 12회)와 프로브 수(5건)를 각각의 단위로** 건다 — 0.1.1 까지 이 행이 「여섯 개 조회가 프로브 5건 안에 드는지」로 **단위를 섞어** 물어 판정선이 서지 않았다. 계상 기준은 `spec.md §A.4` M3-a 조회 칸의 12항목 내역이며, 착수 전에 프로브별 조회 수를 먼저 세어 노트에 숫자로 적는다(REQ-MUSICSYNC-025) | **미측정 → M3-a 착수 시 계상** |
| B9 | **음수 `TrigTime` 인자를 콘솔이 받아들이는지.** M0 가 실측한 것은 **양수뿐**이다 — `SPEC-COPILOT-SONGCUE-001/progress.md:377` `Set Cue 2 Sequence 101 Property 'TrigTime' 4` \| True \| OK(같은 파일 `:677` 감사 로그의 `'TrigTime' 40` 도 양수다). 같은 프로퍼티 계열이 값 하나로 `Illegal value` 를 답한 실측이 같은 표에 있고(`:375` `'TrigType' 'Zzz'`), 그래서 **음수라는 값 영역은 미측정**이다. 이 발화는 M1 의 **승인 번들에 실려 콘솔로 나가므로** 공백이 리허설이 아니라 본 공연에서 드러난다. 거절 시 거동은 AC-MUSICSYNC-006 둘째 Given 이 규정한다(그 큐만 강등, 나머지 번들 성립) | **미측정 → M1 apply 시 드러남** |

## C. 결정 기록 (Implementation Kickoff Approval 이전 해소 완료)

착수 전 열려 있던 결정 3건은 **2026-09-03 오케스트레이터 판정으로 확정**됐다. 표는 채택안과 기각안을 나란히 두어, 뒤집으려는 사람이 기각 사유를 먼저 읽게 한다.

| # | 주제 | 채택 | 기각 | 기각 사유 | 파급 파일 | 결정일 |
|---|---|---|---|---|---|---|
| 1 | 번들 크기 상한 | **`packaging/build.sh` 산출물 대비 델타 300MB.** 초과 시 폴백 R8(c) — 개발 모드에서만 분석을 열고, 패키징된 앱은 **같은 확인 카드**로 수동 BPM 입력을 받는다. `bpm_is_default` 고지 경로는 그대로 정직하게 산다 | (a) 상한 없이 「실측만 기록」 (b) 절대 크기 상한(예: 총 800MB) | (a) 는 임계가 없는 것과 같다 — 어떤 숫자가 나와도 「그럭저럭 괜찮다」로 읽힌다. (b) 는 오늘 번들 크기에 의존해 이 SPEC 밖의 변동을 판정선에 끌어들인다. **델타**여야 이 SPEC 이 더한 비용만 잰다. 300MB 인 이유는 이 앱이 조명감독의 공연장 노트북에 설치되는 데스크톱 배포물이고, 그만한 증가는 설치·서명·배포 시간 전부에 걸리기 때문이다 | `pyproject.toml` · `packaging/GrandMA3-Copilot.spec` · `packaging/build.sh`(측정만) · `server/audio/analyze.py`(폴백 분기) · `server/web/question.py` 소비 측(수동 입력 카드) | 2026-09-03 |
| 2 | `Record Timecode` 처리 | **(ii) 앱이 발화하지 않는다.** 명령은 `QuestionRequest.commands[]`(`question.py:85`)로 운영자에게 넘기고, 앱 발화 전수 grep 으로 0건을 기계 고정한다 | (i) `blacklist.yaml` 에 객체까지 2토큰으로 등재 (iii) (i)+(ii) 둘 다 | (i) 은 `_would_be_held` × `load_corpus()` **코퍼스 재측정 절차**(`server/safety/blacklist.yaml:81-84`, `server/tests/test_measurement_corpus.py`)를 요구해 이 SPEC 의 범위를 넘는다 — `Store Preset` 등재(`blacklist.yaml:172`)가 코퍼스 2/21 시나리오와 전체 스위트 13건을 움직인 선례가 그 비용을 보여 준다. 그리고 이 SPEC 이 실제로 필요로 하는 것은 「앱이 안 쏜다」 하나이며, (i) 없이도 REQ-MUSICSYNC-020 은 AC-MUSICSYNC-022 로 완전히 검증된다. **(i) 은 후속 카드로 분리한다** — 후속 카드명 `blacklist-record-timecode`(등재 + 코퍼스 재측정 + 전체 스위트 영향 계상). 이 SPEC 의 범위가 아니며, 큐 편입은 감독의 몫이다 | `server/orchestrator/tools.py`(인계 목록 조립) · `server/web/question.py` 소비 측 · `server/safety/**` **무변경** | 2026-09-03 |
| 3 | BPM 정본 우선순위 | **측정(사람이 확인 카드에서 확정한 값) > 시트 `HEAD.BPM` > 기본값 120.** 어긋남은 채택 여부와 무관하게 **항상** 사용자에게 보고한다. `FX-Rate` 는 **대조 전용** | (a) 시트 우선 (b) `FX-Rate` 역산을 3번째 판정원으로 채택 | (a) 는 시트가 스스로 「청취 미검증」을 자백하는 경우(`TC_METHOD: DERIVED`)에도 음원에서 온 값을 밀어낸다. (b) 는 `FX-Rate = SongBPM ÷ 사이클당 박수` 인데 **사이클당 박수가 사람의 의도**라 역산이 일의적이지 않다 — 하나의 `FX-Rate` 가 여러 BPM 과 양립한다. 그래서 대조는 하되 판정에는 안 쓴다 | `server/design/profile.py` 소비 측(`:74-75`, `:301-310`) · `server/orchestrator/tools.py`(시트 `HEAD.BPM` 문자열 파싱) · `server/web/question.py` 소비 측(불일치 고지) | 2026-09-03 |

## D. 제약

- 콘솔 예산: M1 기존 승인 번들 안 / **M2 쓰기·조회 0건** / **M3-a 는 조회가 읽기 전용(`query_state` 12회 이하 · 프로브 5건 이하)이고 쓰기는 `spec.md §A.4` 가 열거한 8건 이하** — 슬롯 준비 3줄(`Store Timecode` · `Set … 'Name'` · `Assign Sequence … At Timecode`) + 재생 후보 **4건 이하** + 해제 1줄(`Off Timecode <n>`), 전부 **격리 슬롯 하나**에만이고 쇼 시퀀스에는 0건 / M3-b 운영자 승인분 + 검증 1회당 `query_state` 4회 이하. 앱은 `Record` 를 안 쏜다(REQ-MUSICSYNC-025).
  - 0.1.1 까지 이 줄은 M3-a 를 통째로 「읽기 전용」이라 적어 **재생 후보 발화라는 쓰기를 빠뜨렸다**. 읽기 전용인 것은 **조회**이고, 쓰기는 위 열거분이다 — 후보의 판정은 `ok:true` 가 아니라 **효과**이므로(REQ-MUSICSYNC-019) 후보를 쏘지 않고는 판정 자체가 성립하지 않는다.
- TDD. `mm:ss.f` 파서·분석 함수는 순수 함수 → 라이브 없이 RED.
- 17열·registry 무변경. `AC-LXSEQ4-002` 무변경.
- Tauri capability 무변경. 실제 곡 파일 저장소 반입 금지.
- 선행: SPEC-COPILOT-READBACK-001 — **조건부**다. M3-b 가 `TrackGroup` 자식을 테이블 값으로 만나는 경우에만 그 SPEC 의 R1 직렬화가 필요하다.

---

## E. 마일스톤

순서: **M1 → M3-a 프로브 → M2 → M3-b 본체** (근거 `research.md §Recommended 4`).

### M1 — 시트 시간열 수용 (되돌리기 어려운 결정 둘이 여기 있다)

여기서 정해지는 되돌리기 어려운 것 둘: ① 미확정 시각의 **결과 종류 집합**(한번 페이로드 계약이 되면 소비자가 붙는다) ② PRE-ROLL 음수를 **타임라인에서 빼는 결정**(B2).

| 파일 | 델타 | 내용 |
|---|---|---|
| `server/lxseq/cue_time.py` | [NEW] | `mm:ss.f` 순수 파서. 결과 종류 5종(정상 · 음수 · `확인필요` · 빈칸 · 형식 불명)을 **명시적 값**으로. 음수·1분 초과·소수 자리 경계 포함 |
| `server/orchestrator/tools.py` | [MODIFY] | `cue_meta` 취득부(**Reference: `server/orchestrator/tools.py:5385-5427`**)에 `row[2]`(`TC In`)·`row[3]`(`TC Out`) 인덱스 판독을 `:5405-5412` 의 기존 인덱스 판독 옆에 추가 — **인덱스 근거는 `research.md §1.3` 헤더 실측**(openpyxl 로 읽은 `CUE` 탭 4행 헤더가 `Q#`·`Section`·`TC In`·`TC Out`·`Dur`·`Mood`… 순이며, 오늘 코드가 쓰는 `row[0]`·`row[1]`·`row[5]`·`row[12]` 와 정합한다). 인덱스를 재확인할 사람은 그 표부터 본다. `HEAD` 시트에서 `BPM`·`TC_SOURCE`·`TC_METHOD` 취득. 홑따옴표 fail-closed 검사(`:5417-5426`)는 **재사용**하고 다시 쓰지 않는다 |
| `server/lxseq/cue_mapper.py` | [MODIFY] | `CueRowPlan`(**Reference: `server/lxseq/cue_mapper.py:333-370`**)·`CueBucket`(`:373-378`)에 타이밍 어휘 추가. 단조성 위반은 **별도 목록**이며 `CueHold`(`:382`)에 섞지 않는다 |
| `server/orchestrator/tools.py` (번들 조립) | [MODIFY] | `Set Cue <n> Sequence <s> Property 'TrigType' 'Time'` + `'TrigTime' <초>` 두 줄을 **`Store Cue` 와 같은 승인 번들**에(**Reference: `server/orchestrator/tools.py:5984-5987`** — `Store Cue` 명령 조립 지점). 초 변환은 `_format_seconds` 의미(입력 ms 정수)를 그대로 따른다(**Reference: `server/looks/songcue.py:515-519`**) |
| `server/design/song_plan.py` 소비 측 | [EXISTING] | `TimestampedSection` **무변경**(`:143` `minimum=0` 유지). 임포트 큐 → 타임라인은 **별도 얕은 투사**로, `end_ms` 는 `TC Out` 에서 |
| `server/lxseq/cue_parser.py` · `server/sheets/registry.py` | [EXISTING] | **무변경** (§A.2 · `registry.py:364-366`) |
| `server/tests/test_lxseq_cue_time.py` | [NEW] | 파서 단위 — 경계 5종 + 부정 대조군 |
| `server/tests/test_lxseq_cue_tool.py` · `test_lxseq_cue_mapper.py` · `test_lxseq_cue_harness.py` | [MODIFY] | preview/apply 번들에 두 줄이 실리는지 · 미확정 큐에 안 실리는지 · 정본 CSV 전량 회귀 |

산출: 오프라인 전부 초록. **콘솔 쓰기는 기존 승인 경로 안에서만.**

### M3-a — 프로브 (M2 착수 전 · 격리 슬롯 하나 · 조회 12회 이하 읽기 전용 · 쓰기 8건 이하)

**M2 앞에 둔다.** 반나절이고, 결과가 M3-b 의 범위를 정하며, M2 를 먼저 하면 그동안 M3-b 는 가정 위에 서 있게 된다.

**이 스윕은 읽기 전용이 아니다 — 조회가 읽기 전용이고, 쓰기는 열거로 닫혀 있다.** 후보 재생 명령은 `ok:true` 가 아니라 **효과**로 갈리므로 쏘지 않고는 판정이 없다. 그래서 예산을 두 단위로 나눠 건다.

| 축 | 상한 | 내역 |
|---|---|---|
| 콘솔 쓰기 | **8건 이하** | 슬롯 준비 3줄(`Store Timecode <n>` · `Set Timecode <n> Property 'Name' '<ascii>'` · `Assign Sequence <s> At Timecode <n>` — M0 GO 실측) + 재생 후보 **4건 이하** + 해제 1줄(`Off Timecode <n>`). 전부 **격리 슬롯 하나**에만 나가고 기존 운영자 승인 게이트를 지난다. **쇼 시퀀스를 향한 쓰기는 0건** |
| 프로브 | **5건 이하** | 본 프로브 3(①②③) + 대조군 2(④⑤) |
| 조회 `query_state` | **12회 이하** | 슬롯 판정 1 · 준비 전 베이스라인 1 · 준비 후 되읽기 1 · `TrackGroup 1` 판독 1 · 재생 후보 효과 되읽기 4 · `rig_paths` 실값 1 · 양성 대조군 1 · 음성 대조군 1 · 해제 뒤 되읽기 1 |

슬롯 번호는 **`_timecode_slot_verdict`(`server/orchestrator/tools.py:2792`)의 3분 판정**을 먼저 통과해야 한다 — **free** 면 진행, **occupied** 면 남의 쇼를 덮으므로 중단, **unknown**(풀 무응답 · 절단 · `childCount` 부재)이면 **프로브를 실행하지 않고 무결론으로 닫는다.** 즉 판정이 free 가 아니면 이 스윕의 콘솔 쓰기는 **0건**이다.

착수 전에 **조회 수를 먼저 센다**(B8 · REQ-MUSICSYNC-025). 각 프로브가 낸 `query_state` 호출 수와 발화한 쓰기 명령 전문을 노트에 그대로 적는다.

| 프로브 | 방법 | 판정 |
|---|---|---|
| ① `TrackGroup` 아래 판독 | 격리 슬롯에 `Store Timecode` → `Assign Sequence … At Timecode` → `state DataPool/Timecodes/<n>/TrackGroup 1` | 자식이 오는가 · `childCount` 대조 · `truncated` 판독. **오는 형태가 테이블 값이면** READBACK-001 R1 의존이 발생 |
| ② 재생 명령 후보 4종 | 후보를 격리 슬롯에 쏘고 **효과**(상태 변화)로 가른다. `ok:true` 는 증거가 아니다 | 효과가 증명된 것만 통과. `Go Timecode` 는 이미 `Illegal object` 로 기각됨(`.moai/state/verify/songcue-m0/steps.jsonl:73`) |
| ③ `rig_paths["timecodes"]` | 실값 조회 대 M0 문자열 대조 | 일치/불일치를 값으로 기록 |
| ④ 양성 대조군 | 이미 판독된다고 아는 경로(타임코드 풀 자체) | 값을 답해야 한다 — 안 답하면 계기 고장 |
| ⑤ 음성 대조군 | 존재하지 않는 슬롯 번호 | 부재를 부재로 답해야 한다 |

산출: 프로브 노트(경로는 `docs/research/ma3-effects/` 옆). 대조군 둘이 **같은 스윕 안에** 있어야 한다 — 없으면 모든 실패가 계기 고장과 구별되지 않는다.

### M2 — 오디오 업로드 → 분석 → 확인 카드 (가장 길고 가장 되돌리기 어렵다)

순서 안에서도 **순수 함수가 먼저**다. 와이어 프레임과 카드는 그 위에 붙는다. 이 마일스톤의 콘솔 접촉은 **쓰기·조회 모두 0건**이다.

| 파일 | 델타 | 내용 |
|---|---|---|
| `server/audio/analyze.py` | [NEW] | bytes → `bpm`·`bpm_confidence`·`boundaries_ms`·`onsets_ms`·`rms_curve`·`d_candidates`. **librosa 는 함수 안에서 import** 한다(기동 시간 대책 — 크기 대책이 아니다). 실패 경로는 예외가 아니라 사유를 담은 실패 결과 |
| `server/tests/test_audio_boundary.py` | [NEW] | 형제 4종(`test_paperwork_boundary.py`·`test_scene_boundary.py`·`test_looks_boundary.py`·`test_fx_boundary.py`)과 **같은 형태**로 콘솔 접촉 0건 고정 |
| `server/tests/fixtures/audio/` | [NEW] | **합성 트랙 생성 스크립트**(파형을 코드로 만든다). 실제 곡 파일 없음. 정답: BPM 128, 경계 0/16/32/36s |
| `server/web/messages.py` | [MODIFY] | `song_audio_upload` 프레임 검증 — 확장자·MIME·8 MiB 이중 검사. **Reference: `server/web/messages.py:24-26`(기존 상한 상수)·`:227-262`(layout_image validate-before-store 선례)** |
| `server/web/app.py` | [MODIFY] | **디스패치 분기 추가.** **Reference: `server/web/app.py:505-513`** — 분기 누락으로 메시지가 조용히 버려진 사고가 주석으로 남아 있다. 같은 busy-guard·스레드 패턴 |
| `server/web/session.py` | [MODIFY] | 보관 + sha256 + 바이트 수 고지. 교체 시 반드시 말한다. **Reference: `server/web/session.py:10004-10091`**(`upload_vectorworks_export` 전문) |
| `ui/src/App.tsx` · `useCopilotSocket.ts` · `protocol.ts` | [MODIFY] | `accept` 에 오디오 확장자 추가(**Reference: `ui/src/App.tsx:830`**), 클라이언트 검증(`:549-557`), 프레임 타입. 「UI 는 분류하지 않는다」 규율 유지 |
| `server/web/question.py` 소비 측 | [MODIFY] | 확인 카드를 **서버 코드가** 세운다 — `multi=True`, 구간당 옵션 1개, DSP 제안에 `selected=True`, 자유 입력(`ANSWER_FREEFORM`) 수정 허용. **이 행이 REQ-MUSICSYNC-015 의 필드 수준 정본**이며 근거는 `design.md §4.3`. **Reference: `server/web/question.py:69-109`**(`commands`:85, `multi`:92) |
| `server/design/profile.py` 소비 측 | [MODIFY] | 확정 BPM → `MusicProfile.bpm`. **Reference: `server/design/profile.py:74-75`, `:301-310`**. 시트 `HEAD.BPM` 문자열 파싱(`120 (고정)`). 우선순위는 §C 결정 3 |
| `pyproject.toml` · `packaging/GrandMA3-Copilot.spec` | [MODIFY] | 의존성 + PyInstaller 훅. **완료 조건: 빌드 전후 크기 실측 기록, 델타 300MB 초과 시 폴백**(§C 결정 1) |
| `src-tauri/capabilities/default.json` | [EXISTING] | **무변경** |

산출: 오프라인 전부 초록 + **콘솔 접촉 0** + 번들 크기 전후 숫자.

### M3-b — 콘솔 타임코드 리허설 본체 (M3-a 결과로 두 갈래)

여기서만 운영자 승인 콘솔 쓰기가 일어난다. 검증 조회는 **1회당 `query_state` 4회 이하**다.

1. 앱이 **준비**한다 — 기존 3줄(`Store Timecode` / `Set … 'Name'` / `Assign Sequence … At Timecode`, **Reference: `server/looks/songcue.py:490-498`**, M0 에서 GO 실측).
2. 앱이 `Record Timecode <n>` (와 M3-a 가 증명한 재생 명령)을 **`QuestionRequest.commands[]` 로 운영자에게 인계**한다. 앱은 발화하지 않는다(§C 결정 2).
3. 운영자가 LTC 에 맞춰 녹화한다.
4. 앱이 **되읽어 검증**한다 — 풀 `childCount` · 이름 · `TrackGroup` 존재/개수 · (M3-a 가 열어 준 경우에만) 이벤트 내용. 네 축을 합쳐 조회 4회 안에 끝낸다.
5. 열리지 않았으면 검증 범위를 좁히고 **`unverified` / `SongCueTimingSkip` 관례로 산출물이 스스로 말한다.**

산출: 라이브 증거 + 검증 범위가 명시된 5절 보고.

---

## F. 위험과 완화

| 위험 | 완화 |
|---|---|
| 미확정 시각을 0 으로 접어 큐가 첫 박에 발사된다 | REQ-MUSICSYNC-003 + AC 부정 대조군. 파서가 **명시적 결과 종류**를 돌려주므로 접을 자리가 없다 |
| 단조성 위반을 조용히 재정렬해 시트와 콘솔이 갈린다 | REQ-MUSICSYNC-005 — 별도 목록, 재정렬 금지. 번들은 여전히 preview 가능 |
| PRE-ROLL 음수가 `TimestampedSection` 에서 예외로 터진다 | B2 를 REQ-MUSICSYNC-006 으로 분리 해소. 타임라인 계약 무변경 |
| 새 프레임이 `app.py` 분기 누락으로 조용히 버려진다 | 저장소가 이미 같은 사고를 겪었다(`app.py:505-513`). **그 층을 지나는 테스트**로 고정 — session 메서드 직접 호출은 이 층을 지나지 않는다 |
| 번들이 배로 커진 채 배포된다 | 크기 실측을 **완료 조건**으로. 델타 300MB 초과 시 폴백(§C 결정 1) |
| DSP 결과를 사람이 확인하지 않고 콘솔에 흘린다 | 확인 카드가 경로상 필수. DSP 는 `selected=True` 제안일 뿐 |
| 프로브 없이 재생 명령을 코드에 남긴다 | REQ-MUSICSYNC-023 + Out of Scope 항목. 「후보」를 코드·문면 어디에도 안 남긴다 |
| `Record Timecode` 가 앱 번들에 섞여 콘솔이 무장된다 | REQ-MUSICSYNC-020 + **grep AC**(감사·실행 목록 전수). 기계 차단(blacklist 등재)은 후속 카드 `blacklist-record-timecode` |
| `truncated:true` 를 검증 성공으로 읽는다 | REQ-MUSICSYNC-021 — 무결론. `childCount` 대조 없는 「전부 읽었다」 금지 |
| 프로브가 늘어나 조회가 콘솔 예산을 넘는다 | REQ-MUSICSYNC-025 — 프로브 5건·검증당 4회 상한, 초과분은 무결론. 착수 전 B8 로 계상 |

## G. 안티패턴

- `exec: ok` 를 효과의 증거로 인용하는 것 (예외: `TrigType` 축, 그리고 그 예외는 실측 근거를 함께 적는다).
- 「재지 못함」을 「비었음」으로 적는 것 — 빈 응답은 부재의 증거가 아니다.
- 잘린 출력의 0 을 0 으로 읽는 것 — B3 의 `grep` 은 잘림 없이 전수로 돌려야 0 이 0 이다.
- LLM 에 BPM 을 물어 그 답을 숫자로 채택하는 것.
- 저장소에 실제 곡 파일을 커밋하는 것.
- CSV 만 가진 사용자를 위해 17열을 넓혀 **오늘 동작하는 시트를 전부 거절**하는 것.
- 확인 카드를 `ask_user` 툴로 세우려는 것 — 그 스키마는 `multi`·`selected`·`commands` 를 모델에 노출하지 않는다.
- M3-b 를 M3-a 없이 착수하는 것.
- 답이 안 나온다고 프로브를 늘려 조회 예산 밖에서 판정하는 것 — 그 판정은 결론이 아니라 무결론이다.

## H. 교차 참조

`spec.md` · `acceptance.md` · `design.md` · `research.md` · `reports/app-fresh-eyes-review-20260903.md` · `src/Lighting_Designer/01_스펙/LX-SEQ-SPEC-v2.1.md` · `SPEC-COPILOT-SONGSTD-001/feasibility.md` · `SPEC-COPILOT-SONGCUE-001/progress.md` · `.moai/state/verify/songcue-m0/steps.jsonl` · `SPEC-COPILOT-READBACK-001` · `.claude/rules/moai/core/verification-claim-integrity.md`
