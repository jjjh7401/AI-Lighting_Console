# t516 판정서 — 리듬 대본 실기 기술 확인 준비 (능력 프로브, 승인 요청 단계)

- 카드: t516 · 레인 lane-3 · 브랜치 `WT-rhythm-probe` (기준 `f89c31e7`)
- 범위: 프로브 설계 → 가짜 콘솔 리허설 → 실기 읽기 → 실기 전부-거절 → **승인 요청까지**.
- **실기 쓰기 0**: 감사 로그에서 명령 송신 0줄, 거절 20건이다. `server/` 수정 0, 덮어쓰기·삭제·쇼 저장 0.
- 판정: **승인 요청 준비 완료.** 이 파일 §4의 승인 파일을 리드·감독이 승인해야 실기 쓰기를 한다.
- 대상 콘솔: 이 Mac의 grandMA3 onPC다.
  - 프로브는 `127.0.0.1:8000`으로 보내고 `127.0.0.1:9005`로 받는다(`.moai/reports/t498/probe_readonly.py:55`, `rhythm_probe.py` `build_console_stack`).
  - 응답기 ping 회신은 `CopilotResponder` `1.6.5`다.
  - UDP 9005는 onPC(`app_gma3` PID 60211, `*:9005`)와 같이 열려 있지만 회신은 이 프로브로 왔다(`run0_readonly.txt` 첫 줄 pong, `live_denyall` preflight `responder_ok`).

## 1. 무엇을 재나 — 다섯 항목과 묶음

| 항목 | 묶음 | 기계로 읽는 것 | 사람이 보는 것 |
|---|---|---|---|
| ① 마스터 BPM 112.35 | `bpm`: `Master 3.15 At BPM 112.35` 한 줄 | `ShowData/Masters/3/15` `NORMEDVALUE`(지금 50)가 바뀌는지 | 스피드 마스터 15의 BPM 표시가 112.35(또는 반올림)인지. 🔴 읽을 수 있는 속성에 BPM 값이 없다(§3). 소수 자리는 사람만 확인할 수 있다 |
| ② SpeedMaster + Measure | `seq_beat`: 시퀀스 221에 BACK(그룹 4) 밝기 2스텝 페이저 큐 셋. Measure 1·2·0.5, 모두 `At SpeedMaster 15` | 시퀀스 221 이름·큐 저장 | `measure_1~3`에서 BACK이 1박(0.534초)·2박·반 박마다 한 번 깜빡이는지. 큐마다 8초 |
| ③ 신규 모양 3개 | `seq_shape`: 시퀀스 222에 무빙(그룹 13) Pan 페이저 큐 다섯. 팬 웨이브(위상 0~360, 2박) · 엇갈린 팬 웨이브(ODD 그룹 17 위상 0 / EVEN 그룹 18 위상 180, 1박) · 가속 스윕(위상 0, 4·2·1박) | 시퀀스 222 이름·큐 저장 | `shape_1~5`에서 모양과 빠르기 |
| ④ 타임코드 하나에 트랙 둘 | `tc_a`(타임코드 20 만들기, 이름, 시퀀스 220·221 배정) → 되읽기 → `tc_b`(CmdSubTrack 둘) → 되읽기 → `tc_c`(트랙마다 Go+ 이벤트 하나, 1초·2초) → `play` | 트랙이 2개인지, 각 트랙의 `NO`·`TARGET`, 서브트랙·이벤트 수, 재생 중 두 시퀀스 `CURRENTCUE`와 타임코드 `CURSOR`(6초 표본) | 1초에 장면, 2초에 박자가 들어오는지 |
| ⑤ BACK 겹침 | 시퀀스 220이 BACK 30%(`seq_scene`), 시퀀스 221 큐 1이 BACK 펄스. 둘 다 ④의 타임코드로 시작 | — | 2초부터 펄스가 보이는지. `beat_off` 뒤 4초 동안 BACK이 30%로 돌아오는지 |

이름(감독 규칙): 시퀀스 220·221·222와 타임코드 20 모두 `'RHYTHM PROBE - <항목>'`으로 붙인다.

- 실제 이름: `OVERLAP SCENE` · `SPEEDMASTER MEASURE` · `NEW SHAPES` · `TWO TRACKS`.
- 이름 줄 모양 `Set … Property 'Name' '…'`은 t513에서 실기로 확인한 것이다(`.moai/reports/t513/verdict.md` §7-2).

안전 장치:

- **빈 번호를 다시 읽는다.** 실행 시작에 220·221·222·TC20이 비었는지 다시 읽는다. 하나라도 있으면 아무것도 보내지 않고 멈춘다.
- **트랙 번호를 다시 읽는다.** `tc_a` 뒤 트랙을 되읽어 두 트랙의 `NO`로 `tc_b`·`tc_c` 주소를 만든다. 예상(1·2)과 다르면 문면이 승인 파일과 달라져 게이트가 거절하고 멈춘다.
- **이벤트는 확인 뒤에만 쓴다.** CmdSubTrack이 정확히 하나씩일 때만 이벤트를 쓴다. 이벤트가 하나씩일 때만 재생한다(t506 v3와 같은 방식).
- **묶음은 모두 승인 대상이다.** 모든 묶음을 위험(`BatchRisk kind=t516_probe`)으로 선언했다. 게이트가 안전하다고 본 줄도 승인 없이는 나가지 않는다.
- **쇼 저장은 보내지 않는다.** 실행 직전 백업(SaveShow)은 기록만 하고 보내지 않는다.

## 2. 가짜 콘솔 리허설

| 무엇 | 명령 | 관측 |
|---|---|---|
| 끝까지 진행 | `uv run python .moai/reports/t516/rhythm_probe.py .moai/reports/t516/rehearse --master 15 --master-props NAME,NORMEDVALUE,SPEEDSCALE --rehearse` | exit 0 · 묶음 20개 전부 진행 · 트랙 `NO 1→Sequence 220`·`NO 2→Sequence 221` · 서브트랙 각 1 · 이벤트 각 1 |
| 승인 = 송신 | `uv run python .moai/reports/t512/approval_vs_sent.py .moai/reports/t516/approval_rhythm_probe.txt .moai/reports/t516/rehearse/audit` | 송신 105줄 · sha256 같음 · 송신 안 됨 0 · 승인 안 됨 0 · **PASS** (`rehearse_approval_vs_sent.txt`) |
| 게이트 분류 | `rehearse/steps.jsonl` 집계 | `rehearse_screen_reasons.txt`. `Store Sequence`·`Store Timecode`·`Store Type`·`Assign Sequence`는 금지 목록에 걸린다. `Go/Goto/Off`는 참조 명령으로 분류된다. `Master 3.15 At BPM`·`Set … Property`·`Attribute …`·`cd`·`Store Property`는 사유 0개다. 사유와 무관하게 묶음 단위 승인이 필요하다 |

비교기의 양성 대조가 한 번 실제로 일어났다. 리허설을 같은 폴더에 두 번 돌리자 감사 로그에 210줄이 쌓였고, 비교기가 FAIL(송신 안 됨 105)을 냈다. 폴더를 지우고 다시 돌려서 위 PASS를 얻었다.

가짜 콘솔은 번호 존재와 트랙 `NO`만 흉내 낸다. 페이저·마스터·재생의 의미는 증거가 아니다.

## 3. 실기 읽기 (쓰기 0)

| 무엇 | 명령 | 관측 |
|---|---|---|
| 풀·번호 | `uv run python .moai/reports/t513/probe_steps.py .moai/reports/t516/steps_run0.txt` | 시퀀스 1~15·210·219(`LOVE ATTACK - OLD APP`). 2쪽(`@17`)은 1999·2000이다. 타임코드는 1·2·7·8·9·19다. `Sequences/220`·`221`·`222`·`Timecodes/20` 모두 `path segment not found`. 그룹 1~18 이름이 대본 리그와 같다(BACK 4 · MOVER-ALL 13 · ODD 17 · EVEN 18) — `run0_readonly.txt`, `run0b_masters.txt` |
| 스피드 마스터 | 같은 도구 `steps_run0b.txt` | `Masters/3/1~15` 이름 `Speed1~15`, `NORMEDVALUE 50`, `SPEEDSCALE 0`. `3/16` 이름 `BPM`, `NORMEDVALUE 51`. 속성 목록(`introspect`)에 BPM이나 속도 값 필드가 없다(`NORMEDVALUE` Int32만 있다) |
| 전부-거절 | `uv run python .moai/reports/t516/rhythm_probe.py .moai/reports/t516/live_denyall --master 15 --master-props NAME,NORMEDVALUE,SPEEDSCALE` | preflight `responder_ok` · 승인 요청 20건 105줄, 승인 0. 감사 로그 `executed/props_query 1` · `rejected/t516_probe 20` · `executed/command 0`. SaveShow 0. 요청 문면이 리허설과 같다(`live==rehearsal True`) |

## 4. 승인 요청

- **승인 파일**: `.moai/reports/t516/approval_rhythm_probe.txt` — 105줄, 주석·빈 줄 0, sha256 `aa0157dded9013aa7ebc36ba52849342366ba1d2965bac512d5f693300af795e`. 묶음 20개를 순서대로 이은 것이다.
- **실행 명령** (승인 뒤): `uv run python .moai/reports/t516/rhythm_probe.py .moai/reports/t516/live_write --master 15 --master-props NAME,NORMEDVALUE,SPEEDSCALE --approve .moai/reports/t516/live_denyall`
- **송신 뒤 대조**: `uv run python .moai/reports/t512/approval_vs_sent.py .moai/reports/t516/approval_rhythm_probe.txt .moai/reports/t516/live_write/audit`
- 사람이 콘솔 앞에 있어야 한다. 실행은 약 1분 30초다. 재생 6초, 박자 끄기 뒤 4초, Measure 3 × 8초, 모양 5 × 8초.

승인 전에 정할 것(리드·감독):

1. **스피드 마스터 15의 BPM을 바꾸는 것.** 1~15가 모두 기본값(50)이라 어느 것이 쓰이는지 응답기로 가릴 수 없었다. 마지막 번호 15를 골랐다. 실행 뒤 112.35에 그대로 남는다. 되돌리는 줄은 넣지 않았다 — 원래 BPM 값을 읽을 수 없어서다.
2. **쓰고 남는 것.** 시퀀스 220·221·222, 타임코드 20, 마스터 15의 BPM이 남는다. 지우지 않는다. 쇼 저장은 하지 않으므로 감독이 저장하지 않으면 다시 열 때 사라진다.
3. **엇갈린 팬 웨이브의 그룹.** ODD 17·EVEN 18이 무빙만 담는지는 확인하지 않았다. 무빙이 아닌 기구는 Pan이 없어 영향이 없을 것으로 본다(추정).

## 4-1. 실기 실행 (감독 승인 2026-10-06, 리드 경유) — 1회

- 실행: `uv run python .moai/reports/t516/rhythm_probe.py .moai/reports/t516/live_write --master 15 --master-props NAME,NORMEDVALUE,SPEEDSCALE --approve .moai/reports/t516/live_denyall`
  - exit 0, 12:53:53~12:55:16 KST(감사 로그 첫·끝 송신 시각).
  - 승인 직전 확인: 승인 파일 sha256 `aa0157dd…` 그대로, 헤드 `982f63ed`.
- 🔴 **실행 시점이 리드의 "감독 준비 완료" 신호보다 앞섰다.** 승인 메시지의 "감독이 지금 콘솔 앞에서 본다"를 준비 완료로 읽고, 볼 화면 안내를 보낸 직후 실행했다. 승인이 1회라 다시 돌리지 않았다. 감독이 화면을 봤는지는 리드에게 물었다.

| 항목 | 기계 측정 | 결과 |
|---|---|---|
| 승인 = 송신 (AC-LDRHYTHM-012 방식) | `approval_vs_sent.py approval_rhythm_probe.txt live_write/audit` → 송신 105줄, sha256 같음, 송신 안 됨 0, 승인 안 됨 0, not-ok 0 (`live_write_approval_vs_sent.txt`) | **PASS** |
| 승인 · 쇼 저장 | 승인 20/20 · SaveShow 송신 0(기록만 20) | 통과 |
| ① 마스터 BPM | `Masters/3/15` `NORMEDVALUE` 50 → 69, 이름 `Speed15` 그대로. 응답기 속성에 BPM 값이 없다. **감독 관찰(2026-10-06, 리드 경유)**: 감독이 Speed15를 실행기에 걸어 확인했다. 표시는 「Speed15 / 112 *B」, 그 아래 「MST 112 B」 | 명령은 받아들여졌다. **표시 112(반올림 또는 절삭), 내부 값 미판별.** 소수 .35가 내부에 남아 있는지는 기계로도 화면으로도 가릴 수 없다 |
| ④ 트랙 둘 | TC20/1 아래 Track 두 개: `NO 1 → Sequence 220`, `NO 2 → Sequence 221`. 두 번째 `Assign … At Timecode 20.1.2`가 새 트랙을 만들었다. CmdSubTrack 각 1, 이벤트 각 1 | **PASS** |
| ④ 재생 | 0.4초 간격 표본: 220은 커서 1.00~1.40 사이, 221은 1.80~2.20 사이에 큐 1로 들어갔다(이벤트 1초·2초). `CURRENTCUE`는 `Sequence 220.1` / `221.1`로 읽혔다 | **PASS** (정밀도는 표본 간격 0.4초 한계) |
| 되읽기 (`run1_after_readonly.txt`) | 추가: 시퀀스 220·221·222(이름 `RHYTHM PROBE - …`), 타임코드 20 `RHYTHM PROBE - TWO TRACKS`. 기존 시퀀스·타임코드 목록은 그대로(제거·이름 변경 0). 시퀀스 221 큐 `Measure 1`·`Measure 2`·**`Measure 05`**, 시퀀스 222 큐 5개 | 쓰기 범위 = 승인 범위 |
| ②③⑤ | 기계 측정 없음 | **감독 관찰 대기** |

새로 안 것:

- **큐 이름에서 점이 빠진다.** `Store Sequence 221 Cue 3 'Measure 0.5'`가 `Measure 05`로 저장됐다. 점이 들어가는 이름은 피해야 한다(M2 대본 큐 이름 규칙에 반영할 것). `At Measure 0.5` 값 자체가 들어갔는지는 읽을 수 없다. Measure 구간 ③이 반 박에 한 번이었는지 감독 관찰로 판정한다.
- `Off Sequence` 뒤에도 `CURRENTCUE`는 마지막 큐(221.3, 222.5)로 읽힌다. 꺼짐 여부의 계기로 쓸 수 없다.
- 남은 것(감독이 알고 승인): 시퀀스 220~222, 타임코드 20, 마스터 15 BPM. 쇼는 저장하지 않았다.

## 4-2. 다시 보기 재생 — 쓰기 없음 (리드 지시 2026-10-06, 실행 신호 대기)

1회차 실행 시간에 감독이 화면을 보지 못했다(리드 확인). 리드 지시로 재생만 하는 판을 만들었다. 실행 신호는 리드가 "실행"이라고 쓴 메시지 하나뿐이다. 그 전에는 실기 승인 모드로 돌리지 않는다.

- 스크립트: `replay_probe.py`. 1회차와 같은 순서·구간 길이에 구간 사이 2초를 둔다. 전체 약 1분 35초.
- 1회차와 다른 점: 겹침 구간(⑤)을 타임코드 대신 `Goto Cue 1 Sequence 220/221`로 1초·2초에 연다.
  - 1회차 뒤 타임코드 20의 커서가 10.00(끝)으로 읽혀서, `Go Timecode 20`이 0초부터 다시 도는지 확인되지 않았다.
  - 트랙 둘(④)은 1회차에서 기계로 PASS했다.
- 사전 판독: 220·221·222 이름이 `RHYTHM PROBE - …`가 아니면 아무것도 보내지 않고 멈춘다.

| 단계 | 명령 | 관측 |
|---|---|---|
| 가짜 콘솔 | `uv run python .moai/reports/t516/replay_probe.py .moai/reports/t516/replay_rehearse --rehearse` → `replay_summary.py` | 묶음 15, 15줄 전부 진행. 금지 동사(Store·Set·Assign·Delete·ClearAll·Save·Copy·Move·Label·Edit) 0. 동사는 `Goto Cue`·`Master 3.15`·`Off Sequence`뿐 |
| 실기 전부-거절 | `uv run python .moai/reports/t516/replay_probe.py .moai/reports/t516/replay_denyall` | 사전 판독 이름 셋 일치. 승인 요청 15건 15줄, 승인 0. 감사 로그 `kind: command` 0행, `rejected` 15. SaveShow 0 |
| 승인 파일 | `write_replay_approval.py` | `approval_replay.txt` 15줄, 주석 0, sha256 `c694286e19c2b6619a3087a72e8f486e7e495a362f1d1fb4c49c47b557fc8a03`. 문면이 리허설과 같다 |

- 실행(리드 "실행" 뒤에만): `uv run python .moai/reports/t516/replay_probe.py .moai/reports/t516/replay_live --approve .moai/reports/t516/replay_denyall`
- 송신 뒤 대조: `uv run python .moai/reports/t512/approval_vs_sent.py .moai/reports/t516/approval_replay.txt .moai/reports/t516/replay_live/audit`

## 4-3. 다시 보기 결과 — 🔴 조명이 하나도 안 켜졌다 (감독 관찰, 리드 경유)

- 다시 보기는 리드의 「실행」 뒤 1회 돌았다: 13:34:40~13:36:17 KST.
  - 승인 = 송신 15줄 PASS, SaveShow 송신 0.
- 그런데 감독이 본 무대에는 내내 조명이 하나도 켜지지 않았다.
- 원인을 읽기만으로 좁혔다. 새 송신 0, 기록은 `diag1~5.txt`이고 요약 도구는 `show_reads.py`다.

**잰 것**

| 질문 | 읽은 것 | 관측 |
|---|---|---|
| ① 재생됐나 | `replay_live/steps.jsonl`, 시퀀스 `CURRENTCUE` | 송신 15줄 모두 detail `OK`. 재생 상태 표본은 없다. 지금 `CURRENTCUE` 220.1·221.3·222.5 — 1회차 끝과 같은 값이라 다시 보기의 Goto 효과는 이 값으로 못 가린다. 1회차에서는 221이 재생 중 `221.1` → 끝난 뒤 `221.3`, 222가 `222.5`로 바뀌었다. **Goto는 큐 포인터를 옮긴다**(1회차 기준) |
| ② 큐에 값이 들어갔나 | 큐·Part의 자식과 속성(필드 3쪽), `MEMORYFOOTPRINT` | Part 자식은 0개다(219도 같다). 값을 세는 속성은 없다. `MEMORYFOOTPRINT` 비교는 아래와 같다 |
| | | 빈 Part(OffCue·CueZero, 시퀀스 9·219·220 공통): **2,521B** |
| | | 우리 큐 Part: **3,132~3,284B**(빈 것보다 611~763B 많다) |
| | | 219 큐 Part: **14,092~20,384B** · 9번 T215 큐 Part: 6,316B |
| ③ 그룹 | `Groups/4·13·17·18` | 이름은 BACK·MOVER-ALL·ODD·EVEN으로 맞다. 고정구 수는 응답기로 읽을 수 없다(`COUNT` 0 — 그룹은 늘 0) |
| ④ 222 밝기 | 승인 파일 222 묶음 | Pan 줄 22, Dimmer 줄 **0** — 시퀀스 222는 밝기를 주지 않는다 |
| ⑤ 출력 0 요인 | Masters, 시퀀스 설정 | Grand Master 100 · World 100 · Blind 100 · Selected Master 100. 220/221/222와 219의 PRIORITY(LTP)·PLAYBACKMASTER/SPEEDMASTER/RATEMASTER(None)·AUTOSTART/AUTOSTOP(true)·TRACKING·SOFTLTP·OFFWHENOVERRIDDEN은 모두 같다. 큐 TRIGTYPE만 다르다(우리 Go, 219 Time) |

**추정**

- 우리 큐에는 무언가 아주 조금 저장됐다. 내용은 읽을 수 없다.
  - 값 줄은 「Group 4」와 「Attribute 'Dimmer' At 30」을 따로 보냈다. 룰북 `31_choreography_patterns.md:46-52`의 모양이다.
  - 219(앱)와 t498은 「Fixture … ; Attribute …」 한 줄 모양이었다.
  - 이 차이가 원인인지는 재지 않았다.
- 222의 무빙은 밝기 0인 채 움직였을 가능성이 크다(리드 가설과 같다). 밝기 값 자체는 읽을 수 없다.
- 무대 화면이나 onPC 출력 쪽 문제일 수도 있다. 219가 지금 켜지는지가 갈림길이다.

**다음 프로브 제안(설계만, 리드에게 보냄)**

- P1: 대조군 `Goto Cue 3 Sequence 219` 8초 → `Off Sequence 219`
- P2: `Goto Cue 1 Sequence 220` 8초 → `Off Sequence 220`
- P3: `Goto Cue 1 Sequence 221` 8초 → `Off Sequence 221`
- 모두 쓰기 0이고, 리드의 「실행」 뒤에만 돌린다.

## 5. 안 잰 것

- ①의 소수 BPM은 기계로 확인할 수 없다. `NORMEDVALUE`가 정수라서다. 사람이 마스터 표시를 본다.
- ②·③·⑤는 사람 눈으로만 판정한다. 영상이 있으면 더 좋다.
- `Goto Cue <k> Sequence <n>`은 룰북 문법표(`server/rulebook/assets/v2.4.2/00_grammar.md:48`)에 있지만, 이 저장소의 송신 기록에는 없다.
- `Store Timecode 20.1`(트랙 그룹 만들기)은 t506 1회차 PREP 모양이다. v3는 잔여물을 썼으므로 두 번째 실기 사용이다.
- 상대(`At Relative`) Pan 페이저의 기준 위치는 지금 무빙이 가리키는 곳이다. 기준 프리셋을 따로 부르지 않는다.

## 6. 잔여 위험

- 트랙 번호가 1·2가 아니면(예: 둘째 `Assign`이 새 트랙이 아니라 첫 트랙을 바꾸면) `tc_b`가 거절되고 멈춘다. 이것 자체가 ④의 답(트랙 둘이 안 됨)이 된다. 이미 만든 220~222·TC20은 남는다.
- `Master 3.15 At BPM 112.35`가 실패해도 다음 묶음은 계속 간다. 그때 ②·③은 마스터 15의 지금 속도로 돈다.
