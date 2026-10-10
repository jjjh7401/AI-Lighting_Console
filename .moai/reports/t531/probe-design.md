# t531 M1 — 콘솔에서 아직 안 잰 아홉 항목 설계

2026-10-10, 카드 t531, SPEC-LDBEAT-001 M1. 실기 응답기 1.6.5, HEAD `fef93ed6`.
전부 새 번호(시퀀스 300~319·타임코드 30~34·프리셋 풀마다 301번부터)만 쓴다 —
기존 228~233 등은 참조만 하고 Store/수정하지 않는다. 덮어쓰기·삭제·SaveShow 없음.

이 세션은 **`--rehearse`(가짜 콘솔 + 실제 SafetyGate·ruleset) 까지만** 실행했다.
실기 전송은 리드의 「실행」 신호 없이는 하지 않는다(지시사항 + feedback-run-only-on-explicit-execute-signal).

> **2026-10-10 리드 리뷰 수정판.** ④⑥⑦ 세 항목을 리드 리뷰 지시로 다시 설계했다
> (아래 각 행과 「안 잰 것」에 수정 내용 반영). 다른 여섯 항목은 변경 없음.

## 빈 슬롯 재확인 (r1_free_slots.txt, 실기 1.6.5 상대, 읽기 전용)

시퀀스 300~308, 타임코드 30~31, 프리셋 4.301·21.301 — **13개 전부 `ok:false /
path segment not found`** 로 비어 있음을 실측으로 재확인했다(2026-10-10,
`.moai/reports/t531/r1_free_slots.txt`). 21.301 은 리뷰 수정판 ④가 추가로
쓰는 번호 — 같은 읽기 전용 질의로 추가 확인했다.

## 표

| 항목 | 새 번호 | 명령 줄(핵심) | 되읽기 | PASS/FAIL | 감독 관찰 | 문법 출처 / 미측정 | 위험 |
|---|---|---|---|---|---|---|---|
| ① TC 트랙≥3(목표6) | TC 30 | `Store Timecode 30` → `Store Timecode 30.1` → `Assign Sequence 228..233 At Timecode 30.1.<1..6>` | `state Timecodes/30/1` 자식 수=7, 각 Track `TARGET` | 자식 7개 + TARGET 순서 228..233 | 불필요 | t516 rhythm_probe.py `tc_a`(트랙 2개) 그대로, 6개로 확장 | 낮음 — 새 TC 1개, 기존 시퀀스 참조만 |
| ② 2번째 넘는 Goto + 복수 시퀀스 | 없음(기존만) | `Goto Cue 3 Sequence 228` / `Goto Cue 1 Sequence 11` / `Goto Cue 1 Sequence 12` → `Off ×3` | 각 `CURRENTCUE` | 셋 다 요청 큐로 읽힘 | 필수 — 세 시퀀스 동시 혼선/우선순위 | t516 control_probe.py `Goto Cue N Sequence S` 그대로 | 매우 낮음 — 쓰기 0 |
| ③ 프리셋 수정→큐 전파 | Color 4.301(새) · Seq 300(새) | 4.9 베이스 recall→Store Preset 4.301 → Seq 300 Cue1 이 4.301 참조 → **edit_preset**(4.5 로 교체 후 `/Merge`) | edit 전/후 Seq300 Cue1 `PRESETDATA`/`MEMORYFOOTPRINT` 대조 | 값이 달라지면 전파 확인 | 필수 — 큐 활성 중 즉시 반영되는지 | 🔴 edit_preset 의 `/Merge` 줄 미측정(일반 추정) | 중간 — Store Preset 1개, 기존 프리셋 미변경 |
| ④ 이펙트 프리셋+SpeedMaster15+Measure **(수정판)** | Preset 21.301(새) · Seq 301(새, recall 전용) | `Group 4`→`At 0`/`Step 2`/`At 100`/`At Measure 1`/`At SpeedMaster 15`→`Store Preset 21.301 '…' /Universal`→`Label Preset 21.301 '…'` → `Group 4`→`At Preset 21.301`→`Store Sequence 301 Cue 1` | introspect+props(PresetPools/21/301, 후보명 NAME/SPEED/MEASURE/SPEEDMASTER/NORMEDVALUE/PRESETDATA — 실제 존재 속성은 live 가 답함), `Goto Cue 1 Sequence 301` | 어떤 속성명이 실존하는지 기록(부재도 결과) + 감독이 112.35BPM 대비 점멸 속도 판단 | 필수(속도 숫자만으론 부족) | **t513 `run6_A1/rebuilt_sent.txt:20-34`**(`Store Preset 21.7 'Finale Slam' /Universal` 두-단계 페이저) 의 타이밍 줄만 t516 `phaser_cue` 형태(Measure+SpeedMaster)로 교체. 🔴 recall(`Group 4`→`At Preset 21.301`)은 t513 이 실측한 Fixture-선택 recall(`<fids> ; At Preset 4.9`)을 Group 선택으로 대체 — 미측정 | 낮음 — **Master 3.15 는 읽기만, 쓰지 않음**(재생 전 NORMEDVALUE≠69 면 전부 중단) |
| ⑤ 포지션 프리셋+relative | Seq 302(새) | `Group 13` → `Attribute 'Position' At Preset 2.1` → relative 페이저(Pan±12/Tilt±8,Phase0/90,Speed60) → Store | `PAN`/`TILT` 읽기(중심값) | 중심값=베이스와 같은 방향 | 필수(중심-추종 여부는 관찰) | position_fx.py `_relative_phaser_lines`(circle) 상수 재사용. 🔴 Fixture 선택 대신 Group 선택(픽스처ID 미확보) | 낮음 |
| ⑥ 타임코드 중간 시작 **(수정판 — 예상 문구만 교체)** | TC 31(새) | TC 설정+이벤트 1개(5초) → **`Goto Time 5 Timecode 31`**(🔴) → `Go Timecode 31` | play 직후 0.1초 내 `CURSOR` | CURSOR≈5.0 이면 중간시작 확인, ≈0.0 이면 미확인 | 불필요 | 🔴 **미확인 — 문법 불명**(전례 0건, 아래 그렙 근거). 거절은 「미확인 — 문법 불명」으로 기록 — 「중간 시작 기능 없음」금지 | 낮음 — 거절 시 그냥 멈춤 |
| ⑦ 단일선택 vs 복수선택 Step2 **(대조 추가)** | Seq 303(새, Cue1·Cue2) | Cue1: `Group 4`→`At 0`/`Step 2`/`At 100`→Store. Cue2: `Group 4`(디머0/Step2/100)→**선택을 `Group 11`로 바꿔** Pan Relative±10/Step2 →Store(같은 시퀀스) | introspect/props 로 Cue1·Cue2 각각 MEMORYFOOTPRINT + 디머/Pan 페이저 흔적 대조 | Cue1 디머 유지 **AND** Cue2 디머 소실+Pan 유지 ⇒ t520 가설(verdict.md:46) 확인. 다른 결과는 그대로 기록 | 필수 — Cue1 깜빡임, Cue2 에서 BACK 이 여전히 깜빡이는지 | t516 `phaser_cue` 그대로, Cue2 는 t520 `verdict.md:167`의 "선택 바꾼 뒤 Step2" 모양을 그룹 1개씩으로 축소 | 낮음 |
| ⑧ 그룹 공유(디머/팬틸트 분담) | Seq 304·305(새) | 304: `Group 13` 디머100 → Store. 305: `Group 13` Pan/Tilt Relative10 → Store. 둘 다 Goto | `Group 13` 의 DIMMER/PAN/TILT 동시 읽기 | 셋 다 의도값 | 필수 — HTP/LTP 혼선 여부 | 새 조합, 속성 문법은 기존 측정 재사용 | 낮음 |
| ⑨ circle/ballyhoo/wave | Seq 306·307·308(새) | `Group 13` → `At Preset 2.1` → 축별 relative+phase+speed(세 모양 각각 다른 크기/페이즈) → Store ×3 | introspect 로 Pan/Tilt 페이저 저장 확인 | 셋 다 페이저 저장 | 필수 — 세 모양이 다르게 보이는지 | position_fx.py 상수 재사용. 🔴 `position_fx_commands()` 함수 자체(스켈레톤 프리셋+Fixture 선택) 미호출 | 낮음 |

## 안 잰 것

- **④ 프리셋 레벨 SpeedMaster/Measure 속성명**은 추측(`CANDIDATE_PRESET_PROPS` —
  NAME/SPEED/MEASURE/SPEEDMASTER/NORMEDVALUE/PRESETDATA)일 뿐, 이 프리셋 풀
  클래스의 introspect 결과를 이 리포에서 잰 전례가 없다. live 실행의 introspect
  결과가 실제 속성명 목록이다 — 부재도 발견으로 기록한다(FAIL 로 적지 않는다).
- **④의 recall 문법**(Group 선택 뒤 바로 `At Preset 21.301`)은 t513 이 실측한
  Fixture-선택 recall(`<fixture 목록> ; At Preset 4.9`, `rebuilt_sent.txt` 전역)을
  Group 선택으로 대체한 것 — 이 형태 자체는 미측정. recall 이 거절돼도 ④의 핵심
  질문(프리셋이 SpeedMaster+Measure 를 갖는가)은 store_preset 단계에서 이미 답이
  난다(recall 과는 독립).
- **③의 프리셋 수정 문법**(`/Merge` 로 기존 프리셋 내용을 바꾸는 줄)은 grandMA3 일반
  추정이며 이 리포에 송신 전례가 없다.
- **⑥의 "중간 시작" 명령**(`Goto Time <n> Timecode <n>`)은 전례가 전혀 없음을
  그렙으로 확인했다 — ``tc_probe.py`` 독스트링이 이름 댄
  ``shared/resource/lib_plugins/systemtests/db/system_test_timecode_record.lua``
  는 로컬 설치본(`~/MALightingTechnology/gma3_2.4.2/...`)에 실제로 존재하지만
  콘솔 명령줄 문자열을 전혀 담지 않는다(Lua 내부 객체 API만 테스트,
  `grep -n "Cmd(|GotoTime|'Goto "` 0건). 같은 폴더의 다른 두 파일, 그리고
  `docs/research/ma3-*` 전체도 0건. 그래서 거절은 **「미확인 — 문법 불명」**
  으로 기록한다 — "그런 기능이 없다"는 더 강한 주장이라 쓰지 않는다.
- **⑤⑨의 Fixture-ID 기반 position_fx.py 그대로의 recall**은 이 세션이 실측 픽스처
  ID 목록을 갖고 있지 않아 Group 선택으로 대체했다 — "Group 선택도 Fixture 선택과
  같은 결과를 내는가"는 이 설계가 추가로 떠안는 변수.
- **props 1.6.6 offset 페이징**은 실기 응답기가 1.6.5 라 이번 세션엔 1회 거부만
  확인했다(`group_members_refusal.txt`) — 실제 페이징 동작은 응답기가 1.6.6 으로
  올라온 뒤에야 잴 수 있다.
- **그룹 SELECTIONDATA 자체 내용**(그룹 1~18 의 실제 멤버 목록)은 1.6.6 전엔 잴 수
  없다 — docs/runbooks/console-channel-facts.md 가 이미 "안 풀린 축"으로 적어 둔 것과
  같은 이유.
- live 실행 전 재확인 필요: ②의 `Sequence 228` 큐 3 이 실제로 존재하는지(큐 개수
  미확인) — r0b_pools.txt 엔 시퀀스 이름만 있고 큐 수는 없다.

## 리허설 결과 요약 (deliverable 3)

아홉 스크립트 전부 `--rehearse` 로 돌렸다. 가짜 콘솔은 존재 여부·cd 맥락만
얕게 흉내 내고(콘솔 의미론의 증거가 아님), 목적은 **실제 SafetyGate·ruleset**이
각 줄을 어떻게 심사하는지 보는 것이다.

| 프로브 | exit | 줄 수 | 번들 결과 | 게이트가 플래그한 패턴 | 막힌 줄 |
|---|---|---|---|---|---|
| P1 | 0 | 16 | 4/4 clear+exec | `blacklisted command`(Store Timecode/Assign Sequence), `reference-invoking`(Go/Off) | 없음 |
| P2 | 0 | 6 | 2/2 | `reference-invoking`(Goto/Off, 기존 시퀀스 참조) | 없음 |
| P3 | 0 | 15 | 4/4 | `blacklisted command`(Store Preset/Sequence) | 없음 |
| P4 **(수정판)** | 0 | store_preset 10 + store_cue 7 + play 1 + release 1 | `store_preset`/`store_cue`/`play`/`release` 4/4 | `blacklisted command`(Store Preset/Sequence), `reference-invoking`. 사전 Master 3.15 NORMEDVALUE 읽기=69(가짜 콘솔이 t520 기준값으로 고정 응답) → 통과 | 없음 |
| P5 | 0 | 10 | 3/3 | 〃 | 없음 |
| P6 **(문구만 수정)** | 0 | 12 | 4/4 | 〃 + TC 관련(`goto_mid` 포함) | 없음(리허설은 가짜 콘솔이라 거절 안 됨 — live 거절 시 기록 문구가 「미확인 — 문법 불명」으로 바뀐 것이 이번 수정) |
| P7 **(대조 추가)** | 0 | store_cue1 8 + store_cue2 11 + play/off/play/release 4 | `store_cue1_single`/`store_cue2_two_selections`/`play_cue1`/`off_cue1`/`play_cue2`/`release` 6/6 | `blacklisted command`(Store Sequence ×2), `reference-invoking` | 없음 |
| P8 | 0 | 13 | 4/4 | 〃(×2 Store) | 없음 |
| P9 | 0 | 20 | 5/5 | 〃(×3 Store) | 없음 |

아홉 전부 **exit 0, 모든 번들 clear+executed** — 게이트는 `Store
Sequence/Timecode/Preset` 와 `Assign Sequence` 를 "closed-set 일치" 로,
`Goto/Off/Go` 를 "reference-invoking / 본문 미확인 참조" 로 **플래그만 하고
허용**했다(전부-거절 실행에선 이 플래그가 승인 요청 문면에 그대로 실린다 —
live 실행 시 사람이 보는 승인 텍스트가 이 표와 같다는 뜻). 묶음이 **막힌** 줄은
0건이다 — 리허설에서 심사가 끝까지 간 전부 로그는 각 `.moai/reports/t531/
rehearse/p<n>/steps.jsonl` 과 `result.json` 에 있다.

P4 는 다른 여덟과 달리 `main_cli` 범용 러너가 아니라 전용 `run()`(마스터 사전
검사를 넣기 위해)을 쓴다 — `result.json` 에 `master_normedvalue_observed:
"69"`, `master_normedvalue_expected: "69"` 가 남아, 리허설에서도 중단 분기를
실제로 통과했음을 확인할 수 있다.

## 라이브 실행 전 사람이 재확인할 것 (설계 산출물, 이 세션은 실행하지 않음)

1. ②의 `Sequence 228` 큐 3 존재 여부를 `state Sequences/228` 로 먼저 잰다.
2. ③⑥의 🔴 미측정 문법 줄은 단독으로 더 작게 쪼개 먼저 쏴 본다(거절되면 그 항목은
   "그런 명령이 없다"로 답하고 범위 밖 처리).
3. r1_free_slots.txt 를 **다시** 읽어 12개 번호가 여전히 비어 있는지 재확인한다
   (이 설계와 live 실행 사이에 다른 세션이 번호를 썼을 수 있다).
