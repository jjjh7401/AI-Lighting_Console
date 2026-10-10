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

## 추가 2026-10-10 — T1·T3 결과와 1단계 원인

- T1(PositionMSpeed 0): 감독 「여전히 멈춰 있음」 → 후보 ① 기각. `ClearAll` 로 정리했다(`live/T1_clear/`).
- T3(311 끄고 프로그래머에만 A0 몸통): 감독 「위치는 바뀌었는데 무빙은 안 됨」. Fixture Sheet 의 501 Tilt 숫자도 멈춰 있었다.
  - 시각화와 시퀀스 경로는 원인이 아니다. 콘솔이 페이저 값을 계산하지 않는다. `ClearAll` 로 정리했다(`live/T3_clear/`).
- **원인(근거 셋이 같은 쪽을 가리킨다): A0 은 1단계라 페이저가 아니다.**
  - 앱 룰북: 「Steps CREATE the phaser (two or more) … `Phase` / `Speed` / every other layer only MODIFIES one that exists」(`server/rulebook/assets/v2.4.2/33_effect_editors.md:21-22`).
  - 앱 코드: `MIN_STEPS = 2`(`server/fx/schema.py:67`). 1단계면 「every line ok:true, no `Step` line, no phaser」(`server/fx/instantiate.py:405-416`, REQ-FXLIB-009).
  - MA 공식 문서: 「Phasers change the output for attributes using a set of information in two or more steps」(Phasers 2.0). 위치 프리셋 둘레 원 절차도 「Two steps /points are the basis for the circle」(Create a Circle Phaser Around a Position Preset 2.2).
- **t516 A2(236) 「움직임」은 감독 원문이 아니다.**
  - 원문은 「235 … 확인 못했어 … 242~244 켜진 거 없어」와 「나머지는 모두 확인했어」뿐이다.
  - 「236·237 Tilt 움직임」은 리드 정리로 붙은 해석이다(`t516/verdict.md:385`). 236 은 단독 재생이었다(`replay_v4.py:48-49`).
  - 그래서 A0 의 「알려진 성공」 전제가 처음부터 서지 않았다. 2단계 움직임은 감독 원문이 있다: t516 v5 E2 247 「좌우로 흔들렸어」(`t516/verdict.md` 4-14).
  - 🔴 **리드 실수로 기록(리드 요청, 2026-10-10)**: A0 의 「알려진 성공」 전제는 감독 원문 없이 리드 정리(t516 `verdict.md:385` 「236·237 Tilt 움직임」)에 기대 섰다. 카드 t538 본문과 t531 설계안이 이 정리를 「감독 『움직임』」으로 옮겼고, 이 레인도 원문을 대조하지 않고 받아 썼다.
- 영향:
  - 카드의 A1~A5 는 모두 A0 꼴(1단계)이라 그대로면 전부 「정지」로 나온다. 2단계로 다시 설계해야 한다.
  - A6(쇼 효과 프리셋)·B1~B3(위치 큐, 페이저 없음)은 이 원인과 무관하다.
  - `server/spatial/position_fx.py` 의 circle·wave·ballyhoo 도 1단계 상대값이다. ⑤⑨ 정지의 원인이 같다(앱 결함 후보 — 고치기는 별도 카드).

## T4·T5 문면 (실행 X — 리드가 감독 승인을 받는다)

- 파일: `t4_t5_two_steps.py`, 승인 목록 `approval_t45.txt`(24줄, sha256 `b9d5bbb0b1ec36c2e9374f3b403fe685273fa8f61e14720a758bf38b53500514`).
- 검증: 리허설 OK. 실기 전부-거절은 거절 4 / 실행 0 이고, 문면이 리허설과 같다.
- T4 양성 대조: t516 v4 A3(237) 몸통 그대로(`approval_rhythm_probe_v4.txt:28-36`), Store 없음.
  - 줄: Dimmer 70 · Tilt 45 · Tilt Relative -30 · `Step 2` · Tilt Relative 30 · Phase 0 Thru 360 · Speed 112.
- T5: T4 에 `Step 1/2 At Accel -100`·`At Decel -100` 을 더한다(앱 실측 사인 곡선, `instantiate.py:470-485`). 줄 순서는 단계 → 곡선 → 위상 → 속도(`instantiate.py:646`).
  - 「1단계 + Form」은 명령줄 근거가 없어 만들지 않았다. 공식 문서의 Form 은 페이저 편집기 버튼으로만 나오고, 룰북은 1단계에 곡선 줄을 넣으면 「accepted and do nothing」이라고 적는다(`33_effect_editors.md:23-24`).
- 감독 볼 것: Fixture Sheet 501 Tilt 숫자가 계속 바뀌나 + 무대에서 틸트 물결. T5 는 그 움직임이 T4 보다 부드러운가.

## 추가 2 — T4 판정과 v2 묶음 (2026-10-10)

- T4 감독 판정(리드 경유): 「물결처럼 움직임」.
  - 원인 확정: 1단계 상대값은 페이저가 아니다. 2단계 상대 Tilt + `Phase 0 Thru 360` + `Speed 112` 는 움직인다.
  - 조건: MegaPointe, Fixture 501~508 선택, 프로그래머(Store 없음).
- 정리: `ClearAll` OK(`live/T4_clear/`). T5(사인 곡선)는 켜 둔 채 판정 대기(`live/T5_on/`).
- v2 묶음: `mover_probe_v2.py`, 시퀀스 312~322, 승인 목록 `approval_t538_v2.txt`(169줄, sha256 `d57d76f725b88b0a613d6ba1f3e7eadc3bd509bb48b16c7725e0f62570ffb90f`).

| 항목 | A0′ 에서 바꾼 한 가지 | 번호 | 감독 볼 것 |
|---|---|---|---|
| A0′ 양성 대조 | 없음 — T4 몸통을 시퀀스로 저장 | 312 | T4 처럼 물결로 움직이나. 안 움직이면 저장·재생 경로가 원인이니 중단 |
| A1 | 선택 → Group 11 | 313 | 같게 움직이나 |
| A2 | 크기 30 → 12 | 314 | 움직임이 더 작나 |
| A3 | 기준 Tilt 45 → `At Preset 2.1` | 315 | 프리셋 자리를 중심으로 움직이나 |
| A4 | 기준 줄 없음 | 316 | 움직이나(기준 자세는 직전 상태) |
| A5 | Pan 축 추가, Pan Phase 0 / Tilt Phase 90 | 317 | 원(또는 마름모)을 그리나 |
| A6a/A6b | 쇼 효과 프리셋 21.2 / 21.5 (v1 그대로) | 318/319 | 원 / 쓸기 |
| B1·B2·B3 | 위치 큐·Follow 반복·MIB (v1 그대로) | 320/321/322 | v1 표와 같음 |

- 대조(`check_v2.py`):
  - A0′ 몸통 9줄 = T4(`t4_prog`) True.
  - A6·B 21묶음 = v1 과 번호만 다름, 전부 True.
- 리허설 OK. 실기 전부-거절: 빈 번호 312~322 모두 비어 있음 · 거절 38 / 실행 0 · 문면 = 리허설 · SaveShow·Delete·Remove·Master 0줄.
- 🔴 A5 에는 곡선 줄이 없어 모서리가 있는 원(마름모)으로 보일 수 있다. T5 가 「더 부드럽다」로 나오면 곡선 4줄을 더한 A5b 를 붙일지 리드가 정한다.
