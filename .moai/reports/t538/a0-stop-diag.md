# t538 A0 「멈춰 있음」 — 읽기만으로 원인 좁히기

작성 2026-10-10. A0(시퀀스 311)은 진단용으로 켜 둔 상태다. 이 문서를 쓰는 동안 콘솔 쓰기는 0이고, 읽기는 `read_steps.py`·`group_members.py` 로만 했다.
조건: MegaPointe(MOVER-U 501~508)·Group 11·onPC 3D 를 감독이 눈으로 봤다.

## 잰 것

| # | 질문 | 읽은 값 | 근거 |
|---|---|---|---|
| 0 | A0 큐가 t516 A2 와 같게 저장됐나 | Part 크기 **311 = 3216B, t516 A2(236) = 3216B** — 같음. 🔴 처음에 큐 크기(3760)와 파트 크기를 섞어 「544B 차이」라고 적었는데, 그건 철회한다 | `r16_part_sizes.txt` · `t516/v4_live.stdout.txt:185` |
| 0b | 재생 경로가 같나 | t516 도 `Goto Cue 1 Sequence 236`(실행기 없음) — 같음 | `t516/approval_rhythm_probe_v4.txt:105` |
| 1 | 이동 속도 채널 | MegaPointe Mode 1 의 3번 채널이 `Main Module_PositionMSpeed`. 기본값 `<000000>` = 채널 세트 「Track 80%」(빠름). 1~255 는 Track 100%→1%, 끝값은 「min Track」 1.4% | `r10_megapointe_channels.txt` · `r12_mspeed_default.txt` · `r13_mspeed_sets.txt` |
| 1b | 지금 누가 MSpeed 를 쥐고 있나 | **못 읽는다.** 장비·실행기·시퀀스 객체에 실시간 출력값 필드가 없다(장비 필드 목록 `r7`, 실행기 `r17`) | — |
| 2 | 위치를 더 높은 우선순위로 쥔 시퀀스 | 시퀀스 45개 모두 `PRIORITY = LTP` | `r21_seq_priority.txt` |
| 2b | 실행 중 여부 | 못 가린다(CURRENTCUE 는 `Off` 뒤에도 남는다, t531). Page 1 실행기는 105~108(Dino 넷) 그대로 | `r14_now_state.txt` |
| 2c | 프로그래머 | 선택 0대(`Selection COUNTTOTALSELECTED 0`). 프로그래머 값 자체는 읽는 경로가 없다 | `r14_now_state.txt` |
| 2d | 마스터 | Grand Master 100 · Grand Rate 50 · Selected Rate 50 · Selected Speed 50 · ProgramTime 0 · ExecutorTime 50 · Speed15 69. 10-06 의 Rate 값은 기록에 없어 비교 불가 | `r19_master_values.txt` |
| 3 | 장비 측 설정 | 501: FixtureType 11(Robin MegaPointe) Mode 1 · 패치 2.001 · `MIB` true · `DMXINVERTTILT` false · `OFFSETTILT` 0 · `VISIBLE3D` true | `r8_fixture_props.txt` |
| 4 | ⑩ 과 A0 의 줄 차이 | ⑩ = `Group 11` / Dimmer 0 → `Step 2` → 100 / `Phase 0 Thru 180` — **Speed 줄 없음**(기본 속도). A0 = Fixture 목록 / Dimmer 70 · Tilt 45 · Tilt Relative 30 / `Phase 0 Thru 360` / **`At Speed 112`**. Speed 단위: t516 에서 `At Speed 56/224` 가 박 길이를 바꿨고(`t516/verdict.md` 4-12), 디머 페이저 + `At Speed 112`(v3 L1)는 돌았다 → Speed 줄 자체는 원인 후보가 약하다 | `t531/p10_dimmer_phase_spread.py:34-45` · `t516/verdict.md` 4-7 |

## 원인 후보

같은 문면이 같은 크기로 저장되고 같은 방식으로 재생됐다. 10-06 에는 움직였고 오늘은 멈췄다. 그래서 원인은 큐 밖, 그때와 지금 사이에 달라진 환경이다.

1. **PositionMSpeed 를 느리게 쥔 출처가 있다** (가장 유력, 미측정)
   - 근거: 채널이 실재한다(`r10` 3번). 느린 값이면 정적 이동(⑧ 「틸트가 조금 기울어짐」)은 결국 도착하지만, 112 BPM ±30 의 빠른 왕복은 모터가 못 따라가 멈춘 것처럼 보일 수 있다. 「디머 페이저는 돌고 위치 페이저만 멈춤」과도 맞는다 — 디머는 MSpeed 영향을 안 받는다.
   - 약점: 누가 쥐는지는 읽을 수 없다. 기본값은 빠른 쪽이다. 0 이 정말 빠른지는 t464 에서 한 번 본 것뿐이다(`t464/verdict.md:77,110`).
2. **다른 출처가 501~508 의 Tilt 를 A0 보다 나중에 잡았다** (가능, 미측정)
   - 근거: 모두 LTP 라서 나중에 켜진 쪽이 이긴다. 오늘 lane-1·lane-2 가 busy 였다. 같은 콘솔에 다른 레인이 보내는지는 이 레인에서 못 본다.
   - 약점: 그렇다면 정적 위치 값도 함께 덮였어야 한다.
3. **실행기 없는 재생에서 위치 출력이 막힌다** (약함)
   - 근거: t464 에서 Spiider 의 Pan 이 미배정 `Goto Sequence` 로는 안 나가고, 실행기 재생에서는 나갔다(`t464/verdict.md` §0 ①).
   - 약점: t516 A2 는 미배정 재생으로 움직였고, ⑧ 도 미배정 재생으로 기울었다.

빠진 후보:
- Group 선택: A0 는 Fixture 목록이다. Group 11 = 501~508 은 `r3_group11_fid.txt` 로 확인했다.
- 큐 저장 차이: 파트 크기가 같다.
- 시퀀스 우선순위: 전부 LTP 다.
- Speed 줄 자체: 디머에서는 돌았다.

## 가를 수 있는 최소 시험 (실행 X — 리드가 감독 승인을 다시 받는다)

- **T1 (후보 1)**: A0(311) 을 켜 둔 채 프로그래머에 2줄을 보낸다.
  - `Fixture 501 + 502 + 503 + 504 + 505 + 506 + 507 + 508 ; Attribute 'PositionMSpeed' At 0`
  - 감독이 본 뒤 `ClearAll` 한다.
  - 판정: 움직이기 시작하면 → 어딘가 MSpeed 를 느리게 쥐고 있다. 그대로 멈춰 있으면 → MSpeed 는 원인이 아니다.
  - 새 객체 0, 쇼 저장 0. 문법 근거는 `t464/run21_mspeed_ab.txt`(Spiider 에서 `OK`, 감독 「움직임은 빠른데」).
  - 🔴 위험: 프로그래머 값은 재생보다 우선한다. MSpeed 하나만 넣고 `ClearAll` 로 끝낸다.
- **T2 (후보 2·3)**: T1 이 멈춤이면 같은 콘솔을 지금 쓰는 다른 레인이 없는지 리드가 확인한다(쓰기 0).
  - 그 뒤 `Assign Sequence 311 At Executor 201` → `Goto Executor 201 Cue 1` 로 실행기 재생과 비교한다.
  - t464 문법이다. 새 실행기 배정 1건이 생긴다.

## 장비 속성으로 남길 것 (리드 원칙)

`PositionMSpeed` 는 MegaPointe 에서 DMX 채널 3 이고, 기본 「Track 80%」 다. 이 채널이 있는지와 기본값은 패치의 FixtureType → DMXMode → DMXChannels 에서 읽힌다(`r10`·`r12`·`r13` 경로).
앱이 위치 페이저를 낼 때는 장비에 MSpeed 류 채널이 있으면 빠른 값을 함께 내야 할 수 있다. 그 필요 여부는 T1 결과에 달렸다.
