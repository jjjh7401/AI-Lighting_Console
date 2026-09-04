# SPEC-COPILOT-MUSICSYNC-001 — 설계 근거 (design)

status: draft (v0.1.0, 2026-09-03) · Tier L · 본 문서는 `spec.md` 요구의 **설계 근거**와 위험 검토를 담는다. 요구·인수 자체는 `spec.md`·`acceptance.md` 가 정본이며 여기서 재정의하지 않는다.

> **참조 규약.** 본 SPEC 의 형제 아티팩트(`spec.md`·`plan.md`·`acceptance.md`·`research.md`)는 **줄번호로 인용하지 않는다** — `REQ-MUSICSYNC-nnn` · `AC-MUSICSYNC-nnn` · 절 제목(`spec.md §A.2`)처럼 개정을 견디는 토큰만 쓴다. 반면 **코드·룰북·타 SPEC 의 완료된 기록은 `파일:줄`을 유지**한다 — 코드는 커밋 없이 움직이지 않고 다른 안정 식별자가 없다.
>
> **HOW 를 적지 않는다.** 이 문서는 **이미 코드에 존재하는 이름**(`_format_seconds` · `TimestampedSection` · `QuestionRequest` · `MusicProfile.bpm` · `SongCueTimingSkip` 등)만 부른다. 새 함수 시그니처·클래스 골격·API 스키마는 여기서 정하지 않으며 run 단계에 남긴다.

---

## §1. 설계 의도 — 시간축은 하나이고 층이 셋이다

이 SPEC 이 더하는 것은 **시간축 하나**다. 그런데 그 축은 세 개의 서로 다른 층에서 서로 다른 이름으로 나타나고, **각 층의 신뢰 등급과 쓰기 권한이 다르다.** 설계의 핵심 선택은 넷이다.

**첫째 — 시간의 출처를 값이 아니라 종류로 다룬다.** 「이 큐는 12.5초에 발사된다」는 문장은 그 12.5 가 **어디서 왔는지**에 따라 전혀 다른 무게를 갖는다. 조명감독이 음원을 듣고 찍었다면 `VERIFIED`, 마디 연산으로 도출했다면 `DERIVED`(실측 시트가 그렇다 — `TC_METHOD = DERIVED — 마디연산(1마디=2.000s) 도출. 음원 청취 미검증.`), DSP 가 측정했다면 또 다른 등급이다. 그래서 이 SPEC 의 데이터 모델은 **숫자 옆에 항상 출처와 방법을 데리고 다닌다.** 값만 나르면 「도출된 시각」과 「확인된 시각」이 코드 안에서 같은 float 가 되고, 그 순간 표준 §2.4 의 「파생 산출물 모두에 경고 표기」는 이행할 방법 자체가 사라진다.

**둘째 — 시트 시간과 측정 시간은 경쟁자가 아니라 서로 다른 등급의 같은 축이다.** M1 과 M2 는 「어느 쪽이 이기는가」로 설계하지 않는다. M1 은 사람이 이미 적어 둔 시각을 **잃지 않는** 일이고, M2 는 사람이 아직 안 적은 곡에서 시각을 **만들어 내는** 일이다. 둘 다 있는 경우에만 우선순위 질문이 생기고, 그것은 `plan.md §C` 의 명시적 결정이지 코드가 몰래 정할 일이 아니다.

**셋째 — 콘솔은 시간의 소비자이지 이 SPEC 의 생산자가 아니다.** M3 는 시각을 **만들지 않는다.** 앱이 만드는 것은 빈 그릇(타임코드 오브젝트 + 시퀀스 결합)이고, 그 안을 채우는 것은 **LTC 에 맞춰 사람이 하는 녹화**다. 이 선택은 취향이 아니라 측정의 귀결이다 — 정본 운영 절차 자체가 타임코드 단계를 **운영자가 Timecode 에디터에서 하는 일**로 적고 앱이 쏠 명령줄을 한 줄도 남기지 않으며(`src/Lighting_Designer/04_grandMA3/LXSEQ_SAMPLE_01_Sugar_r3.ma3-runbook.md:46-49` — 「LTC IN → TC Slot 1 → Timecode 에디터에 Cue 10~170 GO 이벤트 배치」 + 수동 GO 폴백), 재생 명령의 문법은 아직 아무도 모르고(`Go Timecode 999` → `Illegal object`, 실측 원본 `.moai/state/verify/songcue-m0/steps.jsonl:73`), `Record Timecode` 는 콘솔을 무장시킨다. 앱이 이 구간을 대신하려 들면 **되돌릴 수 없는 행위를 미측정 문법으로** 하게 된다.

**넷째 — 검증의 상한을 먼저 인정하고 그 안에서만 보고한다.** 실측된 되읽기 깊이는 `state DataPool/Timecodes/901` → `node{class:"Timecode", name, childCount:1}` + `children[{class:"TrackGroup", i:1}]` **한 층**이다(`SPEC-COPILOT-SONGCUE-001/progress.md:694`). 그 아래 트랙·이벤트는 미측정이다. 그러므로 M3-b 가 「타임코드가 맞게 녹화됐다」를 주장할 수 있는지는 **M3-a 가 정한다.** 못 주장하게 되면 설계가 할 정직한 일은 하나뿐이다 — 좁혀진 범위를 산출물이 스스로 말하게 하는 것.

---

## §2. 데이터 모델 — 시각에 출처를 붙인다

### §2.1 `SongTimeSource` — 시간의 출처 축

세 값을 갖는다. 이름은 예시이며 최종 명명은 run 단계 재량이다.

| 출처 | 의미 | 언제 |
|---|---|---|
| `sheet` | LX-SEQ 곡파일 `CUE` 탭의 `TC In`/`TC Out` | M1 |
| `measured` | 오디오 DSP 분석 + 사람 확인 | M2 |
| `default` | 아무 시각도 없음 — 오늘의 `manual_go` 상태 | CSV 만 있는 경우 |

이 축과 **직교**하는 두 번째 축이 방법이다.

| 방법 | 의미 | 근거 |
|---|---|---|
| `VERIFIED` | 음원 대조를 마친 시각 | 표준 §2.4 |
| `DERIVED` | 마디 연산 등으로 도출, 청취 미검증 | 표준 §2.4 — **경고 표기 의무 있음** |

두 축이 직교인 이유: `sheet` 출처의 시각이 `VERIFIED` 일 수도 `DERIVED` 일 수도 있고, `measured` 는 DSP 가 측정했으되 사람이 확인하기 전에는 `VERIFIED` 가 아니다. 한 축으로 접으면 「시트에서 왔으니 믿을 만하다」 같은 잘못된 함의가 코드에 들어간다.

### §2.2 `TC In` 판독 결과는 값이 아니라 종류다

`mm:ss.f` 파서가 돌려주는 것은 「초 또는 없음」이 아니라 **다섯 갈래**다.

```
정상 시각        →  타임라인·TrigTime 둘 다 사용
음수(PRE-ROLL)   →  TrigTime 사용, 타임라인 투사에서 제외
확인필요          →  둘 다 미사용, 미확정으로 표시
빈칸             →  둘 다 미사용, 미확정으로 표시 (사유 구별)
형식 불명         →  둘 다 미사용, 미확정으로 표시 (사유 구별)
```

`None` 하나로 뒤 세 개를 합치지 않는 이유는 실질적이다. 사용자가 봐야 할 행동이 다르다 — 「시트를 고쳐라」와 「아직 안 정했다」와 「이 열은 원래 비어 있다」는 같은 배너에 담을 수 없다. 그리고 `None` 을 도입하는 순간 어딘가에서 `or 0` 이 붙는다. 그것이 곧 **첫 박 발사**다.

### §2.3 PRE-ROLL 분리는 두 계약이 모두 옳기 때문이다

표준은 음수 TC 를 허용하고(`-00:30.0`, §3.2), `TimestampedSection` 은 `start_ms` 에 `minimum=0` 을 강제한다(`server/design/song_plan.py:143`, 2026-09-03 실측). 셋 중 하나를 골라야 한다 — (a) 계약을 완화한다 (b) 좌표계를 옮겨 PRE-ROLL 을 0 으로 만든다 (c) 두 소비자를 분리한다.

**(c) 를 택한다.** (a) 는 타임라인 전 소비자의 불변식을 흔들고, (b) 는 **시트에 적힌 숫자와 화면의 숫자가 달라진다** — 표준 §3.6 규칙 4(숫자를 지어내지 않는다)의 정확한 위반이다. (c) 의 대가는 「PRE-ROLL 큐는 타임라인에 안 보인다」 하나이고, 그것은 제외 목록으로 **보이게** 만들 수 있다.

### §2.4 단조성 위반은 큐가 아니라 큐 **사이**의 사실이다

`CueHold` 어휘는 큐 하나에 붙는다. 「이 큐가 앞 큐보다 이르다」는 **두 큐의 관계**이므로 그 어휘에 자리가 없다. 억지로 넣으면 어느 쪽 큐에 붙일지가 자의적이 되고, 그 자의성이 그대로 사용자 혼란이 된다. 그래서 위반은 **번들과 나란한 별도 목록**이다. 그리고 재정렬하지 않는 이유: 재정렬은 시트를 고치는 행위인데, 이 앱은 시트의 주인이 아니다.

---

## §3. 시간축의 3층 흐름

```
 [층 1 — 시트 시간]                    [층 2 — 측정 시간]
  LX-SEQ .xlsx CUE 탭                   오디오 파일 (WAV/FLAC/MP3)
    TC In / TC Out / Section              │ base64 · 기존 로컬 WS · 8MiB(디코드 후 검사)
    HEAD: BPM · TC_SOURCE · TC_METHOD     ▼
         │                              song_audio_upload
         │ cue_sheet_xlsx_base64          messages.py  (검증)
         ▼   (기존 인자 · 새 프레임 없음)     app.py      (디스패치 분기 ← 사고 재발 지점)
   import_lxseq_cues                       session.py   (보관 · sha256 · 교체 고지)
         │                                  │
    mm:ss.f 파서 (순수)                      ▼
      5갈래 결과                        server/audio/analyze.py (순수 · 콘솔 무접촉)
         │                                bpm · bpm_confidence · boundaries_ms
         ├─ 정상 ─┐                        onsets_ms · rms_curve · d_candidates
         ├─ 음수 ─┤                          │
         └─ 미확정 ┘                          ▼
              │                          QuestionRequest (multi=True, 구간당 옵션)
              │                             │  ← 사람이 확정
              │                             ▼
              │                          MusicProfile.bpm  (bpm_is_default=False)
              ▼                             │
   ┌──────────┴─────────────────────────────┘
   ▼
 승인 번들 (하나)                          별도 얕은 투사
   Store Cue … CueFade … /Merge            TimestampedSection
   Set Cue … 'TrigType' 'Time'               start_ms (≥0) · end_ms(TC Out)
   Set Cue … 'TrigTime' <초>                 ※ PRE-ROLL 제외 목록
   ※ preview 는 쓰기 0                       ※ d_level/palette 지어내지 않음
   │
   ▼
 [층 3 — 콘솔 재생]  ← M3-a 프로브가 범위를 정한다
   앱: Store Timecode / Set … 'Name' / Assign Sequence … At Timecode   (M0 GO 실측)
   운영자: Record Timecode <n>  + (M3-a 가 효과를 증명한 재생 명령)     ← commands[] 인계
   앱: 되읽기 검증 — childCount · name · TrackGroup 존재/개수
        (M3-a 가 열어 준 경우에만) 이벤트 내용
        truncated:true → 무결론
```

**세 층의 쓰기 권한이 다르다는 것이 이 그림의 요점이다.** 층 1 은 기존 승인 번들 안, 층 2 는 **0건**, 층 3 은 운영자 승인분만이며 그중 녹화 무장 명령은 앱이 아니라 사람이 실행한다.

---

## §4. 업로드 프레임과 확인 카드

### §4.1 왜 새 프레임인가 — 기존 첨부 경로로는 안 된다

첨부 라우터는 「파일 종류가 목적지를 고른다」이고 판별은 `registry.read_header` 가 **CSV 헤더를 읽어서** 한다(`server/sheets/registry.py:134-155`). 오디오 바이트에 그 판별기를 걸면 `unknown_sheet_kind` 로 떨어진다. 그러므로 목적지가 다른 별도 프레임이 필요하다. 다만 **전송 수단은 새로 만들지 않는다** — 오늘의 로컬 WebSocket 위 base64 그대로다. Tauri capability 가 「no http, no websocket, no upload」를 못박고 있고(AC-DEPLOY-027 Layer 3), 그 방어선을 뚫는 것은 오디오 한 개를 받자고 치를 값이 아니다.

### §4.2 `app.py` 분기는 설계 항목이다

이 저장소는 **정확히 같은 사고를 이미 겪었다** — `parse_client_message` 는 통과시키는데 `app.py` 에 분기가 없어 메시지가 조용히 버려졌고, 기존 테스트가 전부 session 메서드를 직접 불러서 그 층을 지나지 않았기 때문에 아무도 몰랐다(`server/web/app.py:505-513` 주석). 그러므로 이 SPEC 에서 「`app.py` 에 분기를 추가한다」는 구현 세부가 아니라 **설계상 명시 항목**이고, 그 분기가 없으면 실패하는 테스트가 AC 다.

### §4.3 확인 카드는 오늘 스키마로 세운다 — 그리고 서버가 세운다

`QuestionRequest`(`server/web/question.py:69-109`)는 평면 목록이라 「구간 N × (시각, 라벨, D)」 표 스키마가 없다. 갈래 셋 중 **`multi=True` + 구간당 옵션 1개**를 택한다. 근거: (i) 3층 변경(서버 스키마 · 와이어 · 렌더러) 없이 오늘 성립한다 (ii) `selected=True` 로 DSP 제안을 미리 켜 두면 사람이 **끄는 방식**으로 부분 수정할 수 있다 (iii) 세부 수정은 자유 입력(`ANSWER_FREEFORM`)이 받는다. 구조화 payload 는 필요가 실측된 뒤의 별도 카드다.

**그리고 이 카드는 모델이 아니라 서버 코드가 세운다.** `ask_user` 툴 스키마(`server/orchestrator/tools.py:9683-9737`)는 「EXACTLY ONE question」이고 `selected`·`multi`·`commands` 를 **모델에 노출하지 않는다.** 즉 모델에게 구간표 카드를 부탁하는 경로는 존재하지 않으며, 존재하는 것처럼 설계하면 런타임에 조용히 축소된 카드가 뜬다.

### §4.4 BPM 이 흐르는 자리

측정 BPM 의 종착지는 `MusicProfile.bpm` 하나다(`server/design/profile.py:74-75`, `:301-310`). 거기 닿으면 세 가지가 자동으로 따라온다 — `bpm_is_default` 가 `False` 가 되고, 린트 L11 이 켜지며(오늘은 기본값이면 안 돈다), 「BPM 미지정, 120 기본값」 사용자 문구가 사라진다. **별도 배선을 만들지 않는 이유가 이것이다** — 소비자가 이미 `bpm_is_default` 를 읽고 있으므로 그 한 자리만 정직해지면 하류 전부가 따라온다.

다만 그 축은 **2갈래**뿐이라 「시트 값 · 측정 값 · 기본값」의 3원 상태를 표현하지 못한다. 그래서 우선순위와 불일치 보고는 `plan.md §C` 의 명시적 결정으로 남긴다.

---

## §5. M3 분기 다이어그램

```
                        ┌─────────────────────────┐
                        │  M3-a 프로브 (조회 읽기전용│
                        │   · 쓰기 8건 이하 열거분) │
                        │  ① TrackGroup 판독?      │
                        │  ② 재생 명령 효과?       │
                        │  ③ rig_paths 실값?       │
                        └───────────┬─────────────┘
                                    │
              ┌─────────────────────┴──────────────────────┐
              ▼                                            ▼
   [갈래 A — 열렸다]                            [갈래 B — 안 열렸다]
   TrackGroup 아래가 판독되고                    판독 불가 또는 재생 문법 미증명
   재생 명령의 효과가 증명됨
              │                                            │
              ▼                                            ▼
   앱 준비 3줄 (M0 GO)                          앱 준비 3줄 (M0 GO)  ← 동일
   운영자에게 Record + 재생 명령 인계             운영자에게 Record 만 인계
   운영자 녹화 (LTC)                             운영자 녹화 (LTC)
              │                                            │
              ▼                                            ▼
   되읽기 검증:                                  되읽기 검증 (좁힌 범위):
     childCount · name                            childCount · name
     TrackGroup 존재/개수                          TrackGroup 존재/개수
     + 이벤트 내용                                 ✗ 이벤트 내용 — 확인 불가
              │                                            │
              ▼                                            ▼
   「녹화된 이벤트가 계획과 일치」              「타임코드 오브젝트가 존재하고
     주장 가능                                    시퀀스가 매달려 있음」까지만 주장
                                                 unverified / SongCueTimingSkip 로
                                                 좁혀진 사실을 산출물이 말한다
              │                                            │
              └──────────────┬─────────────────────────────┘
                             ▼
              공통: Record Timecode 는 앱이 발화하지 않는다
                    truncated:true 는 무결론
                    M0 GO 목록 밖으로 프로브 없이 나가지 않는다
```

**M3-a 는 「읽기 전용 스윕」이 아니다 — 조회가 읽기 전용이고, 쓰기는 열거로 닫혀 있다.** 후보 재생 명령은 `ok:true` 가 아니라 **효과**로 갈리므로(§A.5) 쏘지 않고는 판정이 없다. 그래서 이 스윕의 콘솔 쓰기는 **격리 슬롯 하나**를 향한 **8건 이하**로 못박혀 있다 — 슬롯 준비 3줄(`Store Timecode <n>` · `Set Timecode <n> Property 'Name' '<ascii>'` · `Assign Sequence <s> At Timecode <n>`, M0 GO 실측) + 재생 후보 **4건 이하** + 해제 1줄(`Off Timecode <n>`). 슬롯은 `_timecode_slot_verdict`(`server/orchestrator/tools.py:2792`)가 **free** 로 답한 번호만 쓰고, **occupied**(남의 쇼를 덮는다) 또는 **unknown**(풀 무응답·절단·`childCount` 부재)이면 **쓰기 0건으로 무결론**이다. 조회는 `query_state` **12회 이하**. 정본 열거는 `spec.md §A.4` M3-a 행.

**두 갈래 모두 유효한 종점이다.** 갈래 B 가 실패가 아닌 이유: 이 SPEC 이 약속한 것은 「타임코드를 검증한다」가 아니라 「검증할 수 있는 만큼 검증하고 못 한 것을 말한다」이기 때문이다. 갈래 B 를 실패로 취급하면 M3 가 재시도 루프에 들어가고, 재시도로 열리지 않는 것을 재시도하게 된다.

---

## §6. 위험 검토 (오작동 노출면)

| # | 위험 | 왜 조용한가 | 방어 |
|---|---|---|---|
| W1 | 미확정 시각이 `0` 으로 접혀 큐가 첫 박에 발사 | 예외도 경고도 없다. **콘솔은 성공으로 답한다** | 파서가 5갈래를 값으로 돌려준다 → 접을 자리가 없다 (REQ-MUSICSYNC-002·003) |
| W2 | 새 프레임이 `app.py` 에서 버려짐 | ack 도 에러도 없다. session 직접 호출 테스트는 통과한다 | 층을 실제로 지나는 테스트 (AC-MUSICSYNC-013) |
| W3 | 단조성 위반을 재정렬해 시트와 콘솔이 갈림 | 결과가 「깔끔해 보인다」 | 목록으로 보고 · 재정렬 금지 (REQ-MUSICSYNC-005) |
| W4 | PRE-ROLL 음수가 `SongPlanError` 로 터짐 | 예외는 시끄럽지만 **원인이 표준 준수**라 오진하기 쉽다 | §2.3 분리 (REQ-MUSICSYNC-006) |
| W5 | 번들이 배로 커진 채 배포 | 빌드는 성공한다. 서명도 통과한다 | 크기 실측을 완료 조건으로 (REQ-MUSICSYNC-018) |
| W6 | `Record Timecode` 가 번들에 섞여 콘솔 무장 | 분류가 `safe` 라 게이트를 통과한다. 해제는 `Off Timecode` 실측 1회뿐 | 앱 미발화 + grep AC (REQ-MUSICSYNC-020, AC-MUSICSYNC-022) |
| W7 | `truncated:true` 를 검증 성공으로 읽음 | 응답은 도착했고 파싱된다 | 무결론 규정 (REQ-MUSICSYNC-021, AC-MUSICSYNC-025) |
| W8 | 미증명 재생 명령이 코드·문면에 남아 근거로 읽힘 | 다음 사람이 그것을 실측으로 착각한다 | Out of Scope 명시 + REQ-MUSICSYNC-023 |
| W9 | DSP 결과가 확인 없이 콘솔로 흐름 | 숫자가 그럴듯하다 | 확인 카드가 경로상 필수 (REQ-MUSICSYNC-015) |
| W11 | 음수 `TrigTime` 을 콘솔이 거절해 M1 승인 번들이 부분 적용으로 남는다 | M0 는 **양수만** 실측했고(`SONGCUE-001/progress.md:377`) 같은 계열이 `Illegal value` 를 답한 전례가 있다. 오프라인 테스트는 전부 초록이라 **본 공연에서 처음 드러난다** | `plan.md §B` **B9(미측정)** 로 명시 + AC-MUSICSYNC-006 둘째 Given — 거절 시 그 큐만 강등, 나머지 번들 성립, 거절 목록에 응답 문자열 기록 |
| W10 | 합성 트랙에서만 맞는 분석기를 출하 | 픽스처가 초록이다 | 판정 폭을 명시(±3%/±1s)하고, 실제 곡 검증은 **저장소 밖 운영자 확인**으로 남긴다 (그 한계를 완료 보고 미검증 절에) |

---

## §7. 테스트 설계 방향

- **순수 함수 우선.** `mm:ss.f` 파서와 `analyze` 는 라이브 없이 RED 를 만들 수 있다. 이 두 개가 먼저 초록이 되면 나머지는 배선 문제로 축소된다.
- **실패 모드는 개별 테스트.** `확인필요` · 빈칸 · 형식 불명을 한 테스트에 묶지 않는다 — 묶으면 셋 중 하나가 다른 하나를 가린다(t109 의 「신호가 서로를 가림」 사례).
- **부정 대조군이 결론의 조건.** 프로브에서 양성·음성 대조군이 없으면 모든 `not readable` 은 계기 고장과 구별되지 않는다. 오프라인에서도 같다 — 「0 이 아님」을 단언하려면 「0 이 되는 경우」를 같은 테스트 파일에서 보여야 한다.
- **경계 테스트는 형제 형태를 그대로.** `test_audio_boundary.py` 는 `test_paperwork_boundary.py`·`test_scene_boundary.py`·`test_looks_boundary.py`·`test_fx_boundary.py` 와 같은 형태여야 한다 — 형태가 다르면 다음에 경계를 추가하는 사람이 어느 쪽을 베낄지 모른다.
- **회귀 방어선.** `test_lxseq_cue_harness.py`(정본 CSV 전량) · `test_sheets_registry.py` · `test_sheet_kind_consumers.py` 가 17열 무변경을 지킨다. `test_design_profile.py` 의 기존 기본값 케이스가 「BPM 안 주면 오늘과 같다」를 지킨다.
- **페이크 콘솔.** `server/tests/test_safety_gate.py:30-57` 의 `FakeConsole` 이 정본이다(`executed`·`fail_on`·`unconfirmed_on`·`ping_ok`·`state_tree`, 미등록 경로는 `RuntimeError`). ⚠️ `test_groupgen_tools.py:49` 에 **동명 별개 클래스**가 있으므로 import 경로를 확인한다.

---

## §8. 반-패턴 (이 SPEC 근처의 유혹)

- **「어차피 대부분 0초부터 시작하니 미확정은 0 으로 두자.」** — W1 이 정확히 이것이다. 그리고 이 실패는 리허설이 아니라 **본 공연에서** 드러난다.
- **「17열을 넓히면 CSV 사용자도 시간을 줄 수 있다.」** — 넓히는 순간 오늘 동작하는 모든 CSV 가 거절된다. 얻는 것보다 부수는 것이 크다(`spec.md §A.2`).
- **「LLM 에게 BPM 을 물어보고 DSP 로 검증하자.」** — 순서가 뒤집혔다. 측정이 있는데 추측을 1차로 두는 설계는 추측을 정본으로 만든다. 그리고 이미 측정된 오차가 36% 다.
- **「`Record Timecode` 는 `safe` 로 분류되니 앱이 쏴도 된다.」** — 분류는 동사 규칙의 귀결이지 안전 판정이 아니다(`server/safety/` 전체에 `Timecode` 문자열 0건 — 실측). 무장 상태를 만드는 명령이 `safe` 로 읽히는 것이 W6 의 실체다.
- **「프로브는 M2 끝나고 하자, 어차피 M3 는 마지막이다.」** — 프로브는 M3-b 의 **형상**을 정한다. 늦추면 그동안 M3-b 설계가 가정 위에 서고, 그 가정이 틀리면 M2 도 아닌 곳까지 되돌린다.
- **「`ok:true` 가 왔으니 됐다.」** — `ReloadAllPlugins` 는 아무것도 리로드하지 않고 `ok:true` 를 답했다. 예외는 `TrigType` 축 하나이며, 그 예외는 **실측 근거를 함께 인용할 때만** 유효하다.
- **「타임라인에 d_level 이 비어 보이니 임포트 값으로 채우자.」** — 임포트 경로는 팔레트·D 레벨을 모른다. 채우면 지어낸 숫자가 화면에 뜬다. 얕은 투사는 **얕은 채로** 둔다.

---

## §9. 교차 참조

`spec.md` · `plan.md` · `acceptance.md` · `research.md` · `reports/app-fresh-eyes-review-20260903.md` §3.1 · `src/Lighting_Designer/01_스펙/LX-SEQ-SPEC-v2.1.md` §2.1·§2.4·§3.1·§3.2·§3.6 · `SPEC-COPILOT-SONGSTD-001/feasibility.md` · `SPEC-COPILOT-SONGCUE-001/progress.md`(M0 실측 · 응답기 되읽기 깊이) · `SPEC-COPILOT-READBACK-001`(조건부 선행) · `SPEC-COPILOT-DEPLOY-001`(Tauri capability 방어선) · `.claude/rules/moai/core/verification-claim-integrity.md`
