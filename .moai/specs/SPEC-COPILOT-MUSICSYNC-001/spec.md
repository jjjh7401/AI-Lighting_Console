---
id: SPEC-COPILOT-MUSICSYNC-001
title: "음악에 맞춘 연출 — 시간축을 앱에 들여온다 (Music Sync)"
version: "0.1.3"
status: draft
created: 2026-09-03
updated: 2026-09-03
author: orchestrator (plan session 317272ed)
priority: P1
phase: "v1.8.0 target"
module: "server/lxseq/cue_parser.py, server/lxseq/cue_mapper.py, server/orchestrator/tools.py (import_lxseq_cues), server/audio/ (new), server/web/{messages,app,session,question}.py, server/looks/songcue.py, ui/src/"
lifecycle: spec-anchored
tags: "musicsync, timecode, bpm, audio-analysis, cue-timing, trigtime, dsp-measures-llm-proposes, console-write-budget, console-query-budget, probe-first, evidence-discipline"
tier: L
related_specs: [SPEC-COPILOT-LXSEQ-004, SPEC-COPILOT-SONGCUE-001, SPEC-COPILOT-SONGSTD-001, SPEC-COPILOT-CUETIME-001, SPEC-COPILOT-READBACK-001, SPEC-COPILOT-DEPLOY-001]
---

# SPEC-COPILOT-MUSICSYNC-001 — 시간축을 앱에 들여온다

> **이 SPEC 이 닫는 구멍**: 이 앱은 「음악에 맞춘 연출」을 표방하면서 **음악을 한 바이트도 받지 않는다.** 보고서 `reports/app-fresh-eyes-review-20260903.md` §3.1 이 셋을 나란히 적는다 — BPM 은 채팅 정규식이고 미지정이면 `120`(`server/design/profile.py:75` `DEFAULT_BPM = 120.0`), LX-SEQ 곡파일의 `TC In`·`TC Out`·`Section` 은 임포트에서 버려지며(`server/orchestrator/tools.py:5405-5412` 가 `Q#`·`Section`·`Mood`·`Fade` 네 열만 읽는다), 타임코드 오브젝트는 **빈 채로 생성된다**(`server/looks/songcue.py:490-498` 세 줄이 만들고 이름 붙이고 시퀀스를 매달 뿐이다).
>
> **세 마일스톤은 같은 축(시간)을 서로 다른 층에서 다룬다.** M1 은 시트가 **이미 가진** 시간을 잃지 않고 들여오고, M2 는 시간을 **측정해서** 만들어 내며, M3 는 그 시간을 콘솔이 **재생**하게 한다. 세 층의 **콘솔 예산이 서로 다르다는 것**이 이 SPEC 의 핵심 제약이다 — M1 은 기존 승인 경로 안, M2 는 **쓰기 0건**, M3 는 운영자 승인분만이고 **앱은 녹화를 무장시키지 않는다.** 조회 예산도 같은 자리에서 함께 묶인다(REQ-MUSICSYNC-025).
>
> **약속하지 않고 잰다.** M3 의 재생 명령 문법은 미확정이고(`Go Timecode 999` 는 `Illegal object` 를 답했다 — 실측 원본 `.moai/state/verify/songcue-m0/steps.jsonl:73`, `{"arg": "Go Timecode 999", "ok": false, "result": "Illegal object"}`), `TrackGroup` 아래 이벤트 판독은 **미측정**이다. 그래서 M3 는 **프로브(M3-a)가 본체(M3-b)보다 먼저** 서고, 프로브 결과가 본체의 검증 범위를 정한다. 열리지 않으면 **좁힌 범위로 닫되 좁혔다는 사실을 산출물이 스스로 말한다.**

## HISTORY

| 일자 | 버전 | 변경 | 근거 |
|---|---|---|---|
| 2026-09-03 | 0.1.0 | 최초 초안. 보고서 `reports/app-fresh-eyes-review-20260903.md` §3.1·§4 P2 를 다섯 요구 모듈(R1 시트 시간열 · R2 분석 코어 · R3 업로드·카드·BPM · R4 콘솔 타임코드 · R5 횡단 규율)로 분해. 조사 근거는 동봉 `research.md`(기준 `origin/main adae0ac`, 읽기 전용, 콘솔 접촉 0). | 보고서 P2 · research.md |
| 2026-09-03 | 0.1.1 | plan-audit 전 자체 정정. (a) `plan.md §C` 미해결 결정 3건을 **결정 기록표**로 확정(번들 상한 300MB delta · `Record Timecode` 는 앱 미발화 + 운영자 인계 · BPM 정본 「측정 > 시트 > 기본값」) — 결정 대기 표식은 디렉터리 전역 0건. (b) `### Out of Scope —` 기존 8개를 산문에서 `-` 불릿으로 전환하고 blacklist 등재 제외를 1개 신설 — H3 9개, 각 3불릿. (c) 조회 예산 요구 **REQ-MUSICSYNC-025** 신설(REQ 24→25). (d) 프로세스 주어 REQ 5건을 컴포넌트 주어로, 구현 방식 문장 3건을 `plan.md` 로 이관. (e) 인용 행 앵커 11건을 `adae0ac` 에서 되읽어 정정. | 자체 감사 + `adae0ac` 실측 |
| 2026-09-03 | 0.1.2 | plan-audit 1회차(PASS 0.857) blocking 결함 D1~D7 해소 + optional D8·D9 정리. **REQ 25 · AC 25 는 불변**(Tier L 예산 정확 소진 — 신설 없이 기존 본문만 개정). (a) **D1·D2** §A.4 M3-a 쓰기 칸의 **미정의어**(원문은 감사 보고서 D1 참조)를 **열거**로 대체 — 슬롯 준비 3줄 + 재생 후보 4건 이하 + 해제 1줄 = **8건 이하**, 슬롯은 `_timecode_slot_verdict`(`tools.py:2792`) 3분 판정의 **free** 만; 같은 어휘를 REQ-019·025 · AC-021·030 · `plan.md §D`·M3-a · `design.md §3`·§5 에 전파. (b) **D3** REQ-014 괄호 안의 **축소 추정치 주석 삭제** — `messages.py:218` 이 8 MiB 를 **디코드된 원본**에 걸고 `:26` base64 상한(≈10.7 MiB)은 그로부터 파생되므로 실효 원본 상한은 8 MiB 하나다; `design.md:77` 정정 + `research.md` R6 에 만료 고지. (c) **D6** 음수 `TrigTime` 콘솔 수용 여부를 `plan.md §B` **B9(미측정)** 로 올리고 AC-006 에 거절 시 강등 절, AC-031 미검증 열거에 B9 추가. (d) **D4** GEARS 다섯 이름 밖 표식 2건(REQ-012·017)을 `[Event-driven]` 으로. (e) **D5** AC-007·008·024 를 **리터럴 부분문자열 판정**으로 전환(AC-024 는 부재 증명을 존재 판정으로 반전). (f) **D7** §A.4 M3-a 조회 칸을 프로브 수에서 **`query_state` 12회 이하**(12항목 내역)로 단위 정정, `plan.md` B8 동반 정정. (g) **D8·D9** REQ-015 의 필드 수준 지정을 `plan.md` M2 표로 이관, `plan.md:61` 에 `research.md §1.3` 헤더 실측 인용 추가. | plan-audit review-1 + `adae0ac` 실측 |

---
| 2026-09-04 | 0.1.3 | AC-MUSICSYNC-006 둘째 Given 을 계수 판정으로 교체(적용 목록 ∪ 거절 목록 = 시도 전수, 교집합 ∅, 되돌림 쓰기 없음). 근거: plan-audit review-2 D1. REQ/AC 25/25 불변. | review-2 |

## A. 배경

### A.1 지금 무엇이 이미 건강한가 (건드리지 않는다)

| 절 | 상태 | 근거 |
|---|---|---|
| CUE-EX 17열 정확 집합 | ✅ 건강 — **의도된 엄격함** | `cue_parser.py:43-61` + `AC-LXSEQ4-002`(`SPEC-COPILOT-LXSEQ-004/acceptance.md:79`). 「덧붙은 열을 조용히 무시하면 시트에는 적혀 있는데 콘솔에는 없는 값이 된다」 |
| xlsx `CUE` 탭을 읽는 다리 | ✅ **이미 있다** | `tools.py:5385-5427` — 선택 인자 `cue_sheet_xlsx_base64`(`:5385`), `min_row=5`(`:5404`), 홑따옴표 fail-closed(`:5417-5426`) |
| `TrigType`/`TrigTime` 발화 문법 | ✅ 실측된 GO | `songcue.py:501-512` + M0 실측(`SPEC-COPILOT-SONGCUE-001/progress.md:370-378`) — `'Time'`·`'Follow'` OK, `'Zzz'` Illegal value. **이 축은 `ok=True` 가 변별적이다** |
| 타임코드 준비 3줄 | ✅ 실측된 GO | `songcue.py:490-498` — `Store Timecode`(`:495`) / `Set … 'Name'`(`:496`) / `Assign Sequence … At Timecode`(`:497`) 전부 OK |
| 절단 고지·페이징 규율 | ✅ 건강 | `truncated` 플래그(`tools.py:930`) + `childCount` 대조 관례 |
| DSP 우위의 근거 | ✅ **이미 측정됨** | `SPEC-COPILOT-SONGSTD-001/feasibility.md:13` — BPM 오차 librosa 0.9% vs LLM 36% |
| 오디오 입력 경로 | ❌ **없다** | `server/audio/` 부재(실측), `uv.lock` 에 numpy·librosa·soundfile 항목 0건 |
| 재생 명령 문법 | ❌ **미확정** | `Go Timecode` 는 `Illegal object`(`.moai/state/verify/songcue-m0/steps.jsonl:73`). 후보는 프로브로 가른다 |
| `TrackGroup` 아래 판독 | ❌ **미측정** | 실측된 깊이는 `TrackGroup` **존재와 개수**까지 |

즉 본 SPEC 은 *"파서가 틀렸다"* 를 고치는 것이 **아니다.** 파서의 엄격함은 옳고 유지된다. 고치는 것은 **시트가 이미 들고 있는 시간을 읽는 자리를 안 읽는 것**(R1)과, **음악을 아예 안 받는 것**(R2·R3) 둘이며, R4 는 고치는 것이 아니라 **재는 것**이다.

### A.2 왜 17열을 넓히지 않는가 — 결정 사항이지 열린 질문이 아니다

`TC In` 을 나르는 시트는 **`CUE` 하나뿐**이고 `CUE-EX` 에는 시간 열이 0개다(openpyxl 실측, research.md §1.3). 그러므로 시간을 들여오는 길은 둘이다 — (a) `CANONICAL_CUE_COLUMNS` 를 넓혀 CUE-EX 에 시간 열을 요구한다, (b) **이미 있는** `cue_sheet_xlsx_base64` 경로가 `CUE` 탭의 시간 열을 추가로 읽는다.

**(b) 를 택한다.** (a) 는 `AC-LXSEQ4-002`(모자람·남음 둘 다 거부)를 개정해야 하고, `registry.py:366` 의 `RequiredForbidden(required_columns=CANONICAL_CUE_COLUMNS)` 포함 검사와 파서의 정확 집합이 갈리는 자리를 넓히며, **오늘 CSV 만 가진 사용자 전원의 시트를 즉시 거절한다.** (b) 는 17열·registry 무변경이고 research.md 의 위험 R1·R5 를 **소멸**시킨다. 대가는 하나 — CSV 만 가진 사용자는 시간을 줄 수 없다. 그것은 숨기지 않고 **정직한 한계로 산출물에 적는다**(REQ-MUSICSYNC-007).

### A.3 PRE-ROLL 음수 TC 와 타임라인 계약이 충돌한다 (실측)

표준은 PRE-ROLL 에 **음수 TC 를 허용**한다(`LX-SEQ-SPEC-v2.1.md` §3.2, `-00:30.0`). 그런데 타임라인이 앉는 자리인 `TimestampedSection` 은 `_validate_int("start_ms", …, minimum=0)` 으로 **음수를 거절한다**(`server/design/song_plan.py:143`, 2026-09-03 실측 — research.md 에 없던 사실).

둘 다 옳다. 파서는 표준을 따라 음수를 **받아야** 하고, 타임라인 계약은 음수를 **받지 않아야** 한다. 그러므로 이 SPEC 은 둘을 **분리**한다 — 음수 TC 는 큐 페이로드와 `TrigTime` 발화에는 실리고, **타임라인 투사에서는 제외되며 제외 목록으로 보고된다**(REQ-MUSICSYNC-006). 좌표를 0 으로 접거나 계약을 완화하는 두 길은 모두 「지어낸 숫자」이며 표준 §3.6 규칙 4 가 금지한다.

### A.4 콘솔 예산은 마일스톤마다 다르다

| 마일스톤 | 앱이 발화하는 콘솔 쓰기 | 앱이 내는 조회 | 근거 |
|---|---|---|---|
| M1 | **기존 승인 번들 안에서만.** 새 줄(`Set Cue … 'TrigType'`·`'TrigTime'`)도 `Store Cue` 와 **같은 승인 번들** | 오늘과 동일(증가 0) | `tools.py:6015` `group_approval.request_approval`; `preview` 는 쓰기 0 |
| M2 | **0건** | **0건** | 분석 모듈은 콘솔 무접촉(`SONGSTD-001` R6). `test_audio_boundary.py` 가 형제 4종과 같은 형태로 고정 |
| M3-a | **8건 이하 — 격리 슬롯 하나에만, 열거로 확정.** ① 슬롯 준비 3줄(`Store Timecode <n>` · `Set Timecode <n> Property 'Name' '<ascii>'` · `Assign Sequence <s> At Timecode <n>` — M0 GO 실측) ② 재생 명령 후보 **4건 이하** ③ 해제 1줄(`Off Timecode <n>`) + 슬롯 존재 기록. 전부 기존 운영자 승인 게이트를 지나며 **쇼 시퀀스에는 0건.** 슬롯 번호는 `_timecode_slot_verdict`(`tools.py:2792`)가 **free** 로 답한 번호만 쓰고, **occupied·unknown 이면 프로브를 실행하지 않는다**(쓰기 0건 · 무결론) | **스윕 전체 `query_state` 12회 이하.** 내역: 슬롯 판정 1 · 준비 전 베이스라인 1 · 준비 후 되읽기 1 · `TrackGroup 1` 판독 1 · 재생 후보 효과 되읽기 4 · `rig_paths` 실값 1 · 양성 대조군 1 · 음성 대조군 1 · 해제 뒤 되읽기 1 = **12**. 프로브 수는 **5건 이하**로 별도 상한 | REQ-MUSICSYNC-025 |
| M3-b | **운영자 승인분만.** 앱은 `Record Timecode` 를 **발화하지 않는다** | **검증 1회당 `query_state` 4회 이하** | `grep -rn 'Timecode' server/safety/` → **0건**(17개 항목 전수, `blacklist.yaml` 포함) → 동사 규칙상 `Record` 는 `safe` 로 분류되는데 **콘솔을 녹화 무장 상태로 만든다.** 해제는 `Off Timecode` 실측 1회뿐(`SONGCUE-001/progress.md:363, :414`) |

### A.5 M3 는 프로브가 본체보다 먼저 선다

재생 명령이 무엇인지 모르는 채로 본체를 설계하면 그 코드가 근거를 대신하게 된다. 그리고 M0 가 이미 규율을 적어 뒀다 — 「부정 프로브는 무력했다 … 판정을 가른 것은 생성 프로브다」(`SONGCUE-001/progress.md:354`). 따라서 M3-a 는 **효과로 판정**하며 `ok:true` 를 성공의 증거로 쓰지 않는다. 유일한 예외는 `TrigType` 축이다 — 그 축은 `'Zzz'` 에 Illegal value 를 답하므로 `ok=True` 가 변별적임이 **실측되어 있다**(`:370-378`).

---

## B. 요구사항 (GEARS)

> 요구 번호는 `001`부터 `025`까지 **연속**이며 공백이 없다. 절 구분은 번호가 아니라 §B.1~§B.5 표제가 한다.

### B.1 R1 — 시트 시간열 수용 (M1)

- **REQ-MUSICSYNC-001** [Event-driven] — **When** `import_lxseq_cues` 가 `cue_sheet_xlsx_base64` 를 받으면, the 임포터 **shall** `CUE` 탭에서 오늘 읽는 네 열(`Q#`·`Section`·`Mood`·`Fade`)에 더해 `TC In`·`TC Out` 을 읽고, `HEAD` 시트에서 `BPM`·`TC_SOURCE`·`TC_METHOD` 를 읽는다. `CANONICAL_CUE_COLUMNS`(`cue_parser.py:43-61`)와 `registry.py` 의 어느 행도 개정하지 않는다.
- **REQ-MUSICSYNC-002** [Ubiquitous] — the `mm:ss.f` 파서 **shall** 순수 함수이며, 입력마다 **명시적 결과 종류**를 돌려준다 — 정상 시각 · 음수(PRE-ROLL) · 문자열 `확인필요` · 빈칸 · 형식 불명. 다섯은 서로 구별 가능한 값이어야 한다.
- **REQ-MUSICSYNC-003** [Unwanted] — the 파서 **shall not** 미확인(`확인필요`)·빈칸·형식 불명을 `0` 또는 「0 처럼 쓰이는 `None`」으로 접는다. 접으면 그 큐는 **첫 박에 발사된다.**
- **REQ-MUSICSYNC-004** [Event-driven] — **When** 어떤 큐의 `TC In` 이 정상 시각이 아니면, the 임포터 **shall** 그 큐에 대해 `TrigType`/`TrigTime` 줄을 **한 줄도 내지 않고**, 그 큐를 시간 미확정으로 표시한 채 나머지 번들은 계속 만든다.
- **REQ-MUSICSYNC-005** [Event-driven] — **When** `TC In` 단조 증가 또는 `TC Out ≤ 다음 TC In`(표준 §3.6 규칙 2)이 깨지면, the 임포터 **shall** 위반을 **별도 목록**으로 페이로드에 싣는다. 순서를 조용히 재정렬하지 않으며, `CueHold` 어휘에 섞지 않는다.
- **REQ-MUSICSYNC-006** [State-driven] — **While** 어떤 큐의 `TC In` 이 음수(PRE-ROLL)이면, the 임포터 **shall** 그 값을 큐 페이로드와 `TrigTime` 발화에는 그대로 싣고 **타임라인 투사에서는 제외**하며, 제외된 큐를 목록으로 보고한다. `TimestampedSection.start_ms` 는 `minimum=0` 계약을 유지한다(`song_plan.py:143`).
- **REQ-MUSICSYNC-007** [Ubiquitous] — the 임포터 **shall** `TC_METHOD` 를 페이로드·타임라인·큐 라벨 세 곳에 전파하며, 값이 `DERIVED` 이면 **`리허설 LTC 대조 전까지 실행 확정본이 아님` 이라는 문면 그대로의 리터럴**을 세 곳의 경고 문자열에 포함시킨다. `cue_sheet_xlsx_base64` 를 주지 않은 호출(CSV 만)은 리터럴 `시간 정보 없음` 과 리터럴 `manual_go` 를 **둘 다 포함한 사유**를 정직한 한계로 같은 자리에 적는다.

### B.2 R2 — 오디오 분석 코어 (M2)

- **REQ-MUSICSYNC-008** [Ubiquitous] — the 분석 함수 **shall** 오디오 바이트를 받아 `bpm` · `bpm_confidence` · `boundaries_ms` · `onsets_ms` · `rms_curve` · `d_candidates` 를 돌려주는 **순수 함수**이며, 파일 시스템·네트워크·콘솔 어느 것에도 접촉하지 않는다.
- **REQ-MUSICSYNC-009** [Unwanted] — the 분석 파이프라인 **shall not** BPM·박자를 LLM 이 결정하게 한다. 측정은 DSP 가, 제안은 LLM 이, 확정은 사람이 한다(`SONGSTD-001` R6; 근거는 `feasibility.md:13` — librosa 오차 0.9% vs LLM 36%).
- **REQ-MUSICSYNC-010** [Ubiquitous] — the 분석 모듈 **shall** 콘솔 포트·`run_commands`·`exec` 어느 경로도 참조하지 않으며, 그 사실이 형제 경계 테스트 4종(`test_paperwork_boundary.py`·`test_scene_boundary.py`·`test_looks_boundary.py`·`test_fx_boundary.py`)과 **같은 형태**의 테스트로 기계 고정된다.
- **REQ-MUSICSYNC-011** [Ubiquitous] — the 픽스처 생성 스크립트 **shall** 정답이 알려진 합성 트랙을 코드로 만들며(BPM 128 · 경계 `0/16/32/36s`), 실제 곡 파일을 저장소에 커밋하지 않는다. 판정 폭은 BPM ≤3%, 구간 경계 ±1s, D 등급 일치다.
- **REQ-MUSICSYNC-012** [Event-driven] — **When** 분석이 실패하거나 형식을 못 읽으면, the 분석 함수 **shall** 사유를 담은 실패 결과를 돌려주며 예외로 세션을 죽이지 않는다. 부분 결과를 성공으로 위장하지 않는다.

### B.3 R3 — 업로드 프레임 · 확인 카드 · BPM 정본 (M2)

- **REQ-MUSICSYNC-013** [Event-driven] — **When** 클라이언트가 `song_audio_upload` 프레임을 보내면, the 서버 **shall** 검증 층(`messages.py`) → **디스패치 분기 층(`app.py`)** → 보관 층(`session.py`, sha256 + 바이트 수 고지, 교체 시 반드시 말함) 셋을 모두 통과시킨다. `app.py:505-513` 이 기록한 **분기 누락으로 메시지가 조용히 버려진 사고**가 재발하지 않음을 테스트가 고정한다.
- **REQ-MUSICSYNC-014** [Ubiquitous] — the 업로드 경로 **shall** 오늘의 로컬 WebSocket 위 base64 프레임만 쓰며, Tauri capability(`src-tauri/capabilities/default.json`: no http, no websocket, no upload)를 **개정하지 않는다.** 상한은 **디코드된 원본 8 MiB** 이며(`server/web/messages.py:218` 의 기존 검사와 같은 형태 — 같은 파일 `:26` 의 base64 **문자열 길이** 상한 `((8MiB+2)//3)*4` ≈ 10.7 MiB 는 그 8 MiB 에서 **파생된 값**이지 별도 상한이 아니다), 초과하는 WAV/FLAC 은 **상한 수치를 명시한 한국어 사유**로 거절한다.
- **REQ-MUSICSYNC-015** [Ubiquitous] — the 서버 코드 **shall** 확인 카드를 **오늘의 `QuestionRequest` 스키마(`server/web/question.py:69-109`) 변경 없이** 세우며, 사람이 구간별로 제안을 **끄고** 자유 입력으로 고칠 수 있게 한다. 필드 수준 지정(`multi` · 구간당 옵션 · `selected`)은 `plan.md §E` M2 표의 `question.py` 행이 정본이며 근거는 `design.md §4.3` 이다. 구조화 payload 신설은 이 SPEC 밖이다. `ask_user` 툴 스키마는 「EXACTLY ONE question」이고 `selected`·`multi`·`commands` 를 모델에 노출하지 않으므로 **모델이 세우는 카드가 아니다.**
- **REQ-MUSICSYNC-016** [Event-driven] — **When** 사람이 확인 카드에서 BPM 을 확정하면, the 서버 **shall** 그 값을 `MusicProfile.bpm` 으로 실어 `bpm_is_default`(`profile.py:307`)가 `False` 가 되게 하며, 그 결과 린트 L11 이 켜지고 「BPM 미지정, 120 기본값」 문구가 사라진다.
- **REQ-MUSICSYNC-017** [Event-driven] — **When** 시트 `HEAD.BPM`(예: `120 (고정)` 같은 주석 붙은 문자열) · 측정 BPM · `FX-Rate` 역산값이 서로 어긋나면, the 서버 **shall** 어긋남을 사용자에게 보고하고 어느 쪽도 조용히 채택하지 않는다. 채택 우선순위는 **측정(사람이 확인 카드에서 확정한 값) > 시트 `HEAD.BPM` > 기본값 120** 이며, `FX-Rate` 는 대조에만 쓰고 판정에는 쓰지 않는다.
- **REQ-MUSICSYNC-018** [Event-driven] — **When** M2 완료를 보고하면, the 완료 보고 **shall** `packaging/build.sh` 의 전후 번들 크기 두 숫자와 그 차이를 명령 출력 그대로 싣는다. 차이가 **300MB** 를 넘으면 폴백(개발 모드 전용 분석 + 수동 BPM 입력)이 선택되었음을 같은 보고에 적는다.

### B.4 R4 — 콘솔 타임코드 프로브와 리허설 (M3)

- **REQ-MUSICSYNC-019** [Ubiquitous] — the M3-a 프로브 스윕 **shall** M2 착수 **전에** 세 가지를 잰다 — ① `state DataPool/Timecodes/<n>/TrackGroup 1` 로 트랙·이벤트가 판독되는가 ② 재생 명령 후보 4종 ③ `rig_paths["timecodes"]` 실값 대 M0 문자열. 판정은 **효과**로 하며 `ok:true` 를 성공의 증거로 쓰지 않는다(예외: `TrigType` 축은 변별적임이 실측됨). ②의 후보 발화는 §A.4 M3-a 행이 **열거한 쓰기 예산(8건 이하) 안에서만** 이뤄지고, 그 열거 밖의 쓰기는 0건이며, 슬롯이 **free** 로 판정되지 않으면 스윕은 발화 없이 무결론으로 닫힌다.
- **REQ-MUSICSYNC-020** [Unwanted] — the 앱 **shall not** `Record Timecode` 를 어떤 번들에서도 발화한다. 그 명령은 콘솔을 **녹화 무장 상태**로 만들고 해제 경로는 `Off Timecode` 실측 1회뿐이다. 앱은 `QuestionRequest.commands[]`(`question.py:85`)로 **운영자에게 넘긴다.**
- **REQ-MUSICSYNC-021** [Event-driven] — **When** 운영자가 LTC 에 맞춰 녹화를 마쳤다고 알리면, the 앱 **shall** 되읽기로 검증한다 — 풀 `childCount` 증가 · 이름 일치 · `TrackGroup` 존재/개수, 그리고 **M3-a 가 열어 준 경우에만** 이벤트 내용. `truncated:true` 는 무결론이며 성공으로 읽지 않는다.
- **REQ-MUSICSYNC-022** [State-driven] — **While** `TrackGroup` 아래가 판독되지 않으면, the 검증 산출물 **shall** 좁혀진 검증 범위를 기존 `unverified` / `SongCueTimingSkip` 어휘로 명시한다. 좁힌 것을 성공처럼 보고하지 않는다.
- **REQ-MUSICSYNC-023** [Where] — **Where** M3-a 가 어떤 재생 명령의 **효과**를 증명한 경우에만, the 앱 **shall** 그 명령을 운영자 인계 목록에 올린다. M0 의 GO 목록(`songcue.py:490-498` 3줄) 밖으로 프로브 없이 나가지 않는다.

### B.5 R5 — 횡단 규율 (전 마일스톤)

- **REQ-MUSICSYNC-024** [Ubiquitous] — the 완료 보고 **shall** 5절 형식을 갖춘다 — 주장 · 증거(명령과 그 출력) · 기준 귀속 · **미검증** · 잔여 위험(`.claude/rules/moai/core/verification-claim-integrity.md` §3). 「재지 못함」을 「비었음」으로 적지 않으며, 페이징 판독은 `childCount` 대조와 `truncated` 판독값을 함께 싣는다.
- **REQ-MUSICSYNC-025** [Ubiquitous] — the 앱 **shall** 콘솔 접촉을 §A.4 표의 마일스톤별 예산 안에서만 한다. 쓰기는 그 표대로이며 **M3-a 의 쓰기는 §A.4 가 열거한 8건 이하**(슬롯 준비 3줄 + 재생 후보 4건 이하 + 해제 1줄)로 닫혀 있고, 조회는 **M3-a 스윕 전체에서 `query_state` 12회 이하**(프로브 수는 본 프로브 3 + 양성·음성 대조군 2 = **5건 이하**로 별도 상한이며, 12회의 내역은 §A.4 M3-a 행의 열거를 따른다)·**M3-b 검증 1회당 `query_state` 4회 이하**이며, 모든 조회는 격리 슬롯을 향한 **읽기 전용**이다. 예산을 넘겨야 답이 나오는 판독은 답이 아니라 **무결론**으로 보고되고, 프로브별 실제 조회 수는 노트에 숫자로 적힌다.

---

## C. 성공 기준

| # | 기준 | 판정 |
|---|---|---|
| S1 | 곡파일 한 장으로 임포트하면 큐마다 `TrigTime` 이 **시트에 적힌 시각**으로 실린다 | AC-MUSICSYNC-001 |
| S2 | 시간을 못 믿는 큐는 **발사되지 않고** 그 사실이 보인다 | AC-MUSICSYNC-003·004 |
| S3 | 단조성 위반이 조용한 재정렬 대신 **목록**으로 나온다 | AC-MUSICSYNC-005 |
| S4 | 오디오 한 곡을 올리면 BPM·구간 경계·악센트 후보가 **확인 카드**로 돌아온다 | AC-MUSICSYNC-011·013·014·015 |
| S5 | 분석 모듈이 콘솔을 **한 번도** 만지지 않음이 기계로 고정된다 | AC-MUSICSYNC-010 |
| S6 | 측정 BPM 이 `bpm_is_default` 를 끈다 | AC-MUSICSYNC-016 |
| S7 | 번들 크기 증가가 **숫자로** 기록되고 300MB 초과 시 폴백이 선택된다 | AC-MUSICSYNC-017 |
| S8 | M3-a 세 프로브의 결과가 기록되고 M3-b 범위가 그로부터 정해진다 | AC-MUSICSYNC-020·021 |
| S9 | `Record Timecode` 가 앱 발화 목록에 **0건**임이 grep 으로 증명된다 | AC-MUSICSYNC-022 |
| S10 | 판독되지 않은 것이 판독된 것처럼 보고되지 않는다 | AC-MUSICSYNC-024·025 |
| S11 | 콘솔 접촉이 **쓰기·조회 양쪽에서** 예산 안에 있음이 숫자로 확인된다 | AC-MUSICSYNC-002·030 |

---

## D. 범위 밖 (Out of Scope)

### Out of Scope — 앱 쪽 타임코드 트랜스포트·마스터 클록

- 앱이 스스로 타임코드를 굴리는 축을 열지 않는다.
- 앱이 마스터 클록이 되는 축을 열지 않는다.
- 시간의 주인은 콘솔과 LTC 이며, 앱은 **준비하고 되읽는 역할**에 머문다.

### Out of Scope — 실시간 오디오 반응 자율 조명

- 들리는 소리에 조명이 스스로 반응하는 축은 **설계 비목표**다.
- 이 SPEC 의 산물은 사람이 확인한 뒤 콘솔에 저장되는 **정적 계획**이다.
- 실행 중 자율 판단은 어느 요구에도 없다.

### Out of Scope — LLM 을 BPM·박자의 권위로 삼는 것

- `SONGSTD-001/feasibility.md:13` 이 이미 기각했다(LLM BPM 오차 36%).
- LLM 은 라벨·무드·제안에만 쓰인다.
- LLM 은 숫자를 정하지 않는다(REQ-MUSICSYNC-009).

### Out of Scope — LLM 오디오 교차 검증의 필수화

- 1차에서 제외한다(research.md R10).
- 하고 싶다면 **선택 경로**로 뒤에 붙일 수 있다.
- 이 SPEC 의 어떤 판정도 그 결과에 의존하지 않는다.

### Out of Scope — CUE-EX 17열 정확 집합의 확장

- `CANONICAL_CUE_COLUMNS`(`cue_parser.py:43-61`)는 무변경이다.
- `server/sheets/registry.py:364-366` 의 `CUE_ROW` 도 무변경이다.
- `AC-LXSEQ4-002` 개정은 이 SPEC 이 하지 않는다 — 이유는 §A.2 에 있고, 이 결정을 뒤집는 것은 별도 카드다.

### Out of Scope — 새 Tauri 네트워크·업로드 플러그인

- `src-tauri/capabilities/default.json` 의 「no http, no websocket, no upload」 방어선(AC-DEPLOY-027 Layer 3)은 개정하지 않는다.
- 오디오는 **기존 로컬 WebSocket 위 base64** 로만 들어온다.
- 새 Tauri 플러그인을 추가하지 않는다.

### Out of Scope — SMPTE 프레임 형식

- 정본은 `hh:mm:ss:ff` 가 아니라 **`mm:ss.f`** 다(`LX-SEQ-SPEC-v2.1.md` §3.1).
- 프레임 개념·드롭프레임을 다루지 않는다.
- 프레임레이트 협상을 다루지 않는다.

### Out of Scope — M3-a 로 효과가 증명되지 않은 재생 명령

- 후보 4종 중 **효과가 증명된 것만** 인계 목록에 오른다.
- 나머지는 문면에도 코드에도 남기지 않는다 — 남기면 다음 사람이 그것을 근거로 읽는다.
- `Go Timecode` 는 이미 `Illegal object` 로 기각됐다(`.moai/state/verify/songcue-m0/steps.jsonl:73`).

### Out of Scope — `Record Timecode` 의 `blacklist.yaml` 등재

- 객체까지 2토큰으로 등재해 기계가 막는 길(`blacklist.yaml:172` `- "Store Preset"` 선례)은 이 SPEC 이 하지 않는다.
- 등재는 `_would_be_held` × `load_corpus()` 코퍼스 재측정 절차(`server/safety/blacklist.yaml:81-84`, `server/tests/test_measurement_corpus.py`)를 요구해 이 SPEC 의 범위를 넘는다.
- 후속 카드로 분리한다(`plan.md §C` 결정 2 의 후속 항목).

---

## E. 제약

- **개발 방식**: TDD(`.moai/config/sections/quality.yaml` `constitution.development_mode`) — RED-GREEN-REFACTOR. `mm:ss.f` 파서와 분석 함수는 순수 함수이므로 라이브 없이 RED 를 만들 수 있다.
- **콘솔 예산**: §A.4 표대로 마일스톤마다 다르며, 쓰기와 조회 양쪽을 REQ-MUSICSYNC-025 가 묶는다. M2 는 쓰기·조회 모두 0건이며 기계로 고정된다.
- **증거 규율**: `exec: ok` 는 효과의 증거가 아니다. 예외는 `TrigType` 축 하나이며 그 예외는 실측에 근거한다. 페이징 판독은 `childCount` + `truncated` 를 함께 읽는다.
- **번들 상한**: `packaging/build.sh` 전후 델타 **300MB**. 초과 시 폴백은 개발 모드 전용 분석 + 수동 BPM 입력이며, `bpm_is_default` 고지 경로는 그대로 정직하게 산다(`plan.md §C` 결정 1).
- **BPM 정본**: 측정(사람 확정) > 시트 `HEAD.BPM` > 기본값 120. 어긋남은 항상 보고한다. `FX-Rate` 는 대조 전용이다(`plan.md §C` 결정 3).
- **저장소 자산**: 실제 곡 파일을 저장소에 두지 않는다. 시험은 합성 트랙으로 한다.
- **선행 SPEC**: SPEC-COPILOT-READBACK-001(값 되읽기, `status: draft`). M3-b 의 검증은 `TrackGroup` 자식이 **테이블 값으로 밝혀진 경우에만** 그 SPEC 의 R1 직렬화에 의존한다. 밝혀지지 않으면 의존 없이 성립한다.
- **`_format_seconds` 계약**: 입력은 **밀리초 정수**다(`songcue.py:515-519`). 새 호출자도 같은 단위를 쓴다.

---

## F. 교차 참조

`plan.md` · `acceptance.md` · `design.md` · `research.md` · `reports/app-fresh-eyes-review-20260903.md` §3.1·§4 P2 · `src/Lighting_Designer/01_스펙/LX-SEQ-SPEC-v2.1.md` · `SPEC-COPILOT-SONGSTD-001/feasibility.md` · `SPEC-COPILOT-SONGCUE-001/progress.md`(M0 실측) · `.moai/state/verify/songcue-m0/steps.jsonl`(M0 원본 로그) · `SPEC-COPILOT-READBACK-001` · `.claude/rules/moai/core/verification-claim-integrity.md`
