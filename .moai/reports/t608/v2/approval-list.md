# t608 승인 목록 v2 — 박자 격자 송신 실기 확인 묶음 (⓪~⑫, t612 어순 반영)

- 작성 기준: main `9dbc2445` (카드 t612 · PR #655 병합 직후). v1 은 `efb40e03` 기준이었다.
- 콘솔 접촉 0. 이 문서의 줄은 전부 오프라인에서 현재 main 의 순수 함수를 불러 만들었다(소켓·OSC·`run_commands` 호출 없음, 러너는 `--dry-run` 만 돌렸다).
- 생성기: `gen_payload.py` (이 폴더). 다시 돌리는 법은 §9.

## 0. 결론 먼저

1. **어순이 바뀌었다.** 큐 저장은 `Store Sequence S Cue N` 이고, 큐가 하나라도 저장되는 트랙은 맨 `Store Sequence S` 줄을 내지 않는다(첫 큐 저장이 시퀀스를 만든다). `Set Sequence S Property 'Name'` 은 첫 큐 저장 바로 뒤에 온다. 저장되는 큐가 없는 트랙(R1 의 MOVER-D·WASH-ALL)만 옛 순서(`Store Sequence S` → Name)를 유지한다. `/Overwrite` 대상도 같은 어순이다. 근거: `.moai/reports/t612/progress.md` 의 수정 전후 diff.
2. **v1 의 실패 줄은 모두 사라졌다.** run-1012 가 index 33 에서 `User Canceled Command` 로 거절당한 줄은 옛 어순 `Store Cue 1 Sequence 700` 이다. v1 에는 이 꼴이 16줄 있었고 v2 에는 0줄이다(§8). 그 밖에 이전 실행이 실패로 증명한 줄은 없다(run-1012 는 32줄째까지 전부 `ok` 였다 — 단 `ok` 는 효과의 증거가 아니다).
3. **이 목록에서 가장 큰 모험은 S1b 8번째 줄** `Store Sequence 701 Cue 1` (합본 37번째 줄)이다. 라벨도 페이드도 없는 이 꼴은 저장소에 실기 선례가 없다(t612 Gaps 1). 이 줄이 거절되면 S1b 뒤는 의미가 없다. 그래서 순서를 §3 처럼 바꿨다.
4. **번호는 스크래치 픽스처다.** 시퀀스 700~703 · 타임코드 70 · 프리셋 2.351 / 4.351 / 4.352 / 22.97 / 22.98 / 22.0. 실행 직전에 §1 의 읽기 전용 점검으로 비어 있음을 다시 확인한다(러너 `--probe` 가 정확히 이 번호를 읽는다).
5. **`OK` 는 증거가 아니다.** `/Overwrite`·`CueFade`·`/CueOnly`·`Delete Cue` 는 되읽기 또는 onPC 캡처로만 판정한다. 큐의 `CUEFADE` 속성은 응답기로 읽히지 않는다.
6. **합본은 한 번에 보내는 묶음이 아니다.** 러너는 파일 하나를 승인 한 번·번들 하나로 보내고 첫 실패에서 멈춘다. 되읽기는 단계 사이에만 할 수 있으므로 **단계 파일(`step-*.txt`)을 따로 승인·송신**하라. 합본 sha256 은 「이 순서의 이 줄들」을 한 값으로 가리키는 용도다. 합본에는 정리 줄이 없다(`cleanup.txt` 로 따로 뺐다).
7. **정리는 `cleanup.txt` 와 `cleanup-22.0.txt` 둘이다.** `Delete Preset 22.0` 은 ⑫ 가 실제로 풀 22 슬롯 0 에 들어갔다고 되읽기로 확인한 뒤에만 보낸다(§6).

**한 줄 요약**: 합본 `payload-all.txt` 164줄 · sha256 `650635cfd553cb2824c86f0ad96470293d58dd96a596d71a52c59f55467fd6aa` · 정리 `cleanup.txt` 12줄 · sha256 `cf84b16eaca1ad6e6fe4f0f1f84cf9c484db1feed3bd894ca14593b8639b0a4f`.

### 요약표

| 항목 | 목적 | 줄 출처 | 단계 | 항목 줄 수 | 항목 줄 sha256 (앞 16자) |
|---|---|---|---|---|---|
| ⓪ | Top/Go Timecode 뒤 첫 큐가 서는 초를 재서 「콘솔 같이」 지연을 정한다 | [읽음]+[생성] | S1b→S2/S2s | 3 | `0f5d22909724228e` |
| ① | `Store Sequence S Cue N … /Overwrite` · `Delete Cue` 첫 실기 | [생성] | S4 | 16 | `e2fb2119c4d2e0e2` |
| ② | **새 어순** `Store Sequence S Cue N CueFade x` (+`/CueOnly`) 가 받아들여지는가 | [생성] | S1b, S4 | 15 | `e571354aececa326` |
| ③ | Block→Track 다시 반영 때 `/Overwrite` 가 Block 표시를 지우는지 | [생성] | S1b, S4 | 11 | `d0ea54c663859fee` |
| ④ | 번호 순서≠시간 순서 큐의 타임코드 재생 | [생성]+[읽음] | S4→S5/S5s | 13 | `5f27622862443a8a` |
| ⑤ | 미리보기 승인이 세션 1회로 지켜지는지 | [생성] | S3 | 8 | `c1045c43ea43acb5` |
| ⑥ | 반영→다시 반영 왕복 (타임코드·이름·배정·시퀀스 생성) | [생성] | S1a→S4 | 나머지 줄 31 | `fed3eb084eef8123` |
| ⑦ | `trigger_beat` 로 미룬 `TrigTime` | [생성] | S1b | 5 | `8168131937f10d06` |
| ⑧ | 위치 프리셋 만들기 줄을 반영 묶음에 섞기 | [생성] | S1a, S4 | 16 | `5016e4bd201c89e0` |
| ⑨ | 효과 프리셋 만들기(`/Universal`) 섞기 + 여러 그룹 선택 꼴 | [생성] / **[조립]**(⑨-b) | S1a, S6 | 22 | `952e477faa43f3af` |
| ⑩ | 색 프리셋 만들기 줄 섞기, 4.n 저장값·큐 참조 | [생성] | S1a, S4 | 10 | `3e0cd11bd328ab1c` |
| ⑪ | 같은 `Store` 가 한 묶음에 두 번 나갈 때 콘솔 반응 | **[조립]** | S8 | 10 | `3df715705f34a961` |
| ⑫ | `Store Preset 22.0` 이 받아들여지는지 | **[조립]** | S7 (대안 `alt-S7b.txt` [생성]) | 4 | `2afb6195bac8b4f8` |

표기: **[생성]** = 현재 main 의 앱 함수를 호출해 나온 문자열. **[읽음]** = 코드를 읽고 적었고 호출은 못 한 것(`Top`/`Go`/`Off Timecode`). **[조립]** = 앱에 생산 경로가 없어 앱 부품으로 손으로 이은 것. 항목 줄 수는 줄을 가장 구체적인 항목 하나에 배정한 분할이라 합이 합본 줄 수와 같다(⑥ 은 어느 항목에도 안 걸린 나머지: 타임코드 설정·이름·배정·빈 시퀀스·평범한 첫 큐). 줄 앞 꼬리표: `승인카드` = 오프라인 게이트 분류기(`classify_command`)가 `blacklisted` 로 가른 줄 · `호출형` = `invoking` · `일반` = `safe`.

## 1. 실행 전에 필요한 것

### 1-1. 연결과 러너

- 콘솔 연결(`console_host 127.0.0.1` · 송신 8000 · 수신 `receive_port 9005` · `osc_slot 2`)은 v1 §1-1 에서 옮긴 값이다 — 이번에 설정 파일을 다시 읽지 않았다.
- 러너: `uv run python -m server.tools.beatgrid_runner --input <파일> --expect-sha256 <sha> --listen-port 9005` (송신), `--dry-run` (송신 없음), `--probe` (읽기만). 모드·종료 코드는 `server/tools/beatgrid_runner.py` 머리 설명. 러너는 파일 전체를 번들 하나로 게이트에 올려 승인을 한 번 받고, 줄을 파일 순서대로 보내며 `ok` 가 아닌 첫 줄에서 멈춘다. 빈 줄·주석은 거절한다.
- 실행 전 첫 점검은 `--probe`. 러너가 정확히 이 번호를 읽는다: 시퀀스 700~703 · 타임코드 70 · 프리셋 2.351 / 4.351 / 4.352 / 22.97 / 22.98 / 22.0. 모두 `empty` 로 나와야 한다. (이 문서를 만드는 동안 `--probe` 도 돌리지 않았다.)

### 1-2. 점검이 못 보는 것 (손으로 읽는다)

- 풀 1~14 의 슬롯 22 (⑫ 전 기준선 — `22.0` 이 「풀 22 슬롯 0」이 아니라 「현재 종류의 22번」으로 읽힐 위험).
- MOVER-D(521~528)의 `POSX/Y/Z`·`ROTX/Y/Z` (⑧ 조준 값이 이 값으로 계산된다), WASH-ALL(401~410·421~430)의 `ColorRGB_R/G/B` (⑩), 그룹 3·4·10·12 의 소속, `Fixture 111` 의 존재 (⑫).
- 응답기 읽기 형식: `state:ShowData/DataPools/Default/Sequences/<s>` (자식 class·i·name·cueNo), `props:…/Sequences/<s>/<자식 번호>|NAME,TRIGTYPE,TRIGTIME,RELEASE`, `props:…/Sequences/<s>|CURRENTCUE`, `props:…/Timecodes/70|CURSOR`, `state:…/Timecodes/70/1` (Marker + Track 4개 기대), `state:…/PresetPools/<풀>`. (옮긴 값 — v1 §4 공통 되읽기. `CUEFADE` 는 읽히지 않는다.)

## 2. 이번에 확인한 실기 사실과 v1 에서 옮긴 값

| 사실 | 값 | 출처 |
|---|---|---|
| run-1012 의 중단 | index 33 `Store Cue 1 Sequence 700` → `failed`, `User Canceled Command` | `.moai/reports/t608/run-1012.jsonl` (측정, 이 트리에서 읽음) |
| 그 앞 32줄 | 전부 `status ok / detail OK` — 프리셋 3개·타임코드 70·`Store Sequence 700`·Name 이 `OK` | 같은 파일 |
| 정리 | `cleanup-1012.txt` 6줄(`Delete Timecode 70`, `Delete Sequence 700`, `Delete Preset 2.351/4.351/22.98` /NoConfirm) 전부 `ok` | `cleanup-1012.jsonl` |
| 정리 뒤 상태 | 시퀀스 700~703 · 타임코드 70 · 프리셋 2.351/4.351/4.352/22.97/22.98/22.0 모두 verdict `empty` (응답기 1.6.6, 발췌는 잘려 있다) | `probe-after-1012.jsonl` |
| M1 판독표 | 1번 통과(구조) · 2번 미확인 · 3번 부분 · 4번 미확인 · 5번 움직임 없음 · 6번 미확인 — 문법 불명 · 7번 부분(결과 기록) · 8번 통과 · 9번 wave 움직임 없음 · circle·발리후 미확인 | 이 트리의 `.moai/specs/SPEC-LDBEAT-001/progress.md` 를 `read_m1_probe_results_from_path` 로 읽음 |

그래서 `Delete Timecode N /NoConfirm`·`Delete Sequence N /NoConfirm`·`Delete Preset P.S /NoConfirm` 은 지난 실행에서 각각 응답 `OK` 와 사후 `empty` 가 관측됐다. `Delete Cue k Sequence s` 는 선례가 없다.

## 3. v1 에서 바꾼 것

1. **어순**: 위 §0-1. v1 의 `Store Cue N Sequence S …` 16줄과 맨 `Store Sequence 700`/`701` 2줄이 빠지고, `Store Sequence S Cue N …` 16줄이 들어왔다. `Set Sequence S Property 'Name'` 줄 수는 그대로이고 위치만 옮겨졌다(저장 큐가 있는 트랙은 첫 큐 저장 바로 뒤).
2. **트랙 순서**: v1 은 FOH·BACK·MOVER-D·WASH-ALL, v2 는 **MOVER-D·WASH-ALL·BACK·FOH**. 앱의 트랙 순서는 곡 격자가 정하므로 이 순서는 시험용 선택이다. 이유: 거절될 수 있는 모양이 앞에 몰려 있으면 한 번의 거절이 모든 항목을 막는다. 새 순서에서는 (가) 증명된 모양(빈 시퀀스 `Store Sequence 702`/`703`)이 먼저, (나) 평범한 첫 큐 저장(BACK, 합본 37번째 줄)이 다음, (다) 미측정 `CueFade`/`/CueOnly` 를 가진 FOH 가 마지막이다. S4 도 같은 순서라 MOVER-D·WASH-ALL 의 큐 참조(⑧⑩)가 `/Overwrite` 미측정 줄보다 먼저 나가고, `Delete Cue 2 Sequence 700`(되돌릴 수 없음)이 S4 의 마지막 줄이다. 시퀀스 번호는 그대로(FOH 700 · BACK 701 · MOVER-D 702 · WASH-ALL 703)이고 프리셋 만들기 줄 순서(위치→색→효과)와 타임코드 트랙 배정 순서가 트랙 순서를 따라 바뀐다.
3. **단계 분할**: v1 S1 을 S1a(프리셋 3개 + 타임코드 설정, 29줄 — 전부 run-1012 에서 `OK` 가 나온 꼴)와 S1b(시퀀스·큐, 46줄)로 쪼갰다. 합쳐서 앱이 만든 S1 묶음 한 개와 같다(§5 에서 단언). v1 의 S6b/S6/S7 은 위험이 큰 순서로 S6(⑨-b) → S7(⑫) → S8(⑪) 로 다시 줄 세웠다: ⑪ 은 두 번째 `Store` 가 확인창을 띄우면 뒤 줄을 삼킬 수 있어 맨 끝으로 보냈다.
4. **정리**: 합본에서 빼서 `cleanup.txt` 로 분리하고, 만든 객체를 합본에서 **기계적으로 뽑아** 줄을 세웠다(생성기가 「만든 객체 집합 == 지우는 객체 집합」을 단언한다). 순서는 만든 순서다: 첫 실패 뒤에는 앞서 만든 객체만 있으니 없는 객체의 `Delete` 는 항상 목록 끝에서 만난다. `Off Timecode/Sequence` 5줄은 정리에서 뺐다(없는 객체에 `Off` 를 보내면 첫 줄에서 막힐 수 있다 — 재생을 시작한 채 멈췄다면 `Off Timecode 70` 만 손으로 보낸다). `Delete Preset 22.0` 은 별도 파일이다(§6).
5. **⑫ 의 위험 문장 추가**: 정리 쪽에서 `Delete Preset 22.0` 이 쇼의 진짜 프리셋 22번을 지울 수 있다는 위험을 v1 은 적지 않았다.

## 4. 항목별 승인 목록

단계는 §5 에서 승인 단위다. 아래 줄 번호는 단계 안 번호(`S1b:08`)이고 합본 줄 번호는 §5 표.

### ⓪ Top/Go Timecode 뒤 첫 큐가 서는 초 → 「콘솔 같이」 음원 지연

- **줄 출처**: `Top`/`Go`/`Off Timecode N` 은 `ChatSession._beat_grid_console_transport("console_play", ("Top","Go"))` 의 식을 읽고 적었다 — **[읽음]**, 호출 못 함(송신과 한 몸). 번호 70 은 소유 기록의 타임코드 번호다. 시험 대상 큐 시각은 S1b 의 `TrigTime` 줄(생성): FOH 1·2·3·4·5번 큐 = 2·4·7·8·10초, BACK 1·2번 큐 = 2·6초.
- **선례/근거(v1 §4 ⓪ 에서 옮김, 이번에 다시 열지 않음)**: t520 verdict(3.002초는 타임코드 **이벤트 `Go+`** 쇼의 값, `Top Timecode N` → CURSOR 0.00, `Off` 는 되감지 않음), t474 verdict(타임코드를 돌려 큐가 시각대로 넘어가는지 보지 않았다), t498 verdict(이 저장소 방식은 이벤트 0개 + 큐별 `Time` 트리거 — 「판독」), t578 §5(`Go Timecode` 가 `Time` 큐를 부르는지 자체가 미확인).
- **보낼 줄**:

```text
S2:01 [일반] Top Timecode 70
S2:02 [호출형] Go Timecode 70

S2s:01 [호출형] Off Timecode 70
```

- **되읽기**: S1b 뒤 `Timecodes/70/1` 트랙 4개의 `TARGET` 을 읽는다. S2 와 같은 시각부터 `Timecodes/70|CURSOR`, `Sequences/700|CURRENTCUE`, `701|CURRENTCUE` 를 0.2~0.5초 간격으로 읽고 onPC 를 같이 캡처한다(`CURRENTCUE≠켜짐`). **H1** CURRENTCUE 가 CURSOR≈TrigTime 에서 넘어감 → 「콘솔 같이」 지연은 ≈0 이어야 한다(추론). **H2** 앞 큐 기준 누적(FOH 2·6·13·21·31초 꼴) → 에미터 TrigTime 의미가 틀렸다. **H0** 안 넘어감 → 이벤트 없는 타임코드는 큐를 안 부른다, 이벤트 생성 설계가 필요하다. 이 목록은 `console_audio_offset.yaml` 의 3.002초를 바꾸지 않는다.
- **정리**: S2s `Off Timecode 70`. 시퀀스는 S3 의 `Off Sequence` 줄이 끈다.
- **위험**: `Go Timecode 70` 은 시퀀스를 **실제로 재생**한다 — onPC 에 빛이 나간다(라이브 무대에 연결된 쇼면 안 됨). `Go Timecode` 는 `invoking` 이라 게이트가 대상 본문을 읽어 추가 확인할 수 있다. `Top Timecode N` 은 타임코드 24 에서 한 번 실측됐고 70 에서는 처음이다.

### ① `Store Sequence S Cue N … /Overwrite` · `Delete Cue k Sequence s`

- **줄 출처**: [생성] — `emit_beat_grid_write_bundle` → `apply_beat_grid_ownership_reuse` (`_overwrite_store_cue`, `Delete Cue`).
- **선례/근거**: t572 run-verdict(두 명령 모두 실기 선례 0건), t612 progress Gaps 4·5(`Store Sequence S Cue N … /Overwrite` 실기 미측정, `Delete Cue` 는 바꾸지 않은 옛 가설). `.moai/reports/t469/verdict.md:38` — 저장 옵션이 가짜여도 `OK` 이고 뒷글자를 큐 이름으로 먹는다. `/Overwrite` 철자가 틀리면 **큐 이름이 바뀔** 수 있다.
- **대상**: 시퀀스 700 큐 1·3 와 BACK 701 큐 1 이 `/Overwrite`, 700 의 큐 2 가 `Delete Cue`(S4 의 **마지막 줄**). 큐 5·4 와 701 큐 2 의 `/Overwrite` 는 ②③④ 쪽에 센다. 소유 기록(R1): FOH {'1': 1, '2': 2, '3': 3, '4': 4, '5': 5} · BACK {'1': 1, '3': 2} (마디→큐).
- **보낼 줄**:

```text
S4:13 [일반] Group 4 ; Attribute 'Dimmer' At 30
S4:14 [승인카드] Store Sequence 701 Cue 1 /Overwrite
S4:16 [일반] ClearAll
S4:17 [일반] Set Cue 1 Sequence 701 Property 'TrigType' 'Time'
S4:18 [일반] Set Cue 1 Sequence 701 Property 'TrigTime' 2
S4:29 [일반] Group 3 ; Attribute 'Dimmer' At 20
S4:30 [승인카드] Store Sequence 700 Cue 1 /Overwrite
S4:32 [일반] ClearAll
S4:33 [일반] Set Cue 1 Sequence 700 Property 'TrigType' 'Time'
S4:34 [일반] Set Cue 1 Sequence 700 Property 'TrigTime' 2
S4:35 [일반] Group 3 ; Attribute 'Dimmer' At 65
S4:36 [승인카드] Store Sequence 700 Cue 3 /Overwrite
S4:37 [일반] ClearAll
S4:38 [일반] Set Cue 3 Sequence 700 Property 'TrigType' 'Time'
S4:39 [일반] Set Cue 3 Sequence 700 Property 'TrigTime' 7
S4:50 [승인카드] Delete Cue 2 Sequence 700
```

- **되읽기**: S4 직후 `state:Sequences/700` 자식에 cueNo 2 가 **없고** 1·3·4·5 가 있는지(`Delete Cue` 판정). 큐 3 밝기 60→65 는 응답기로 못 읽는다 → onPC 큐 시트 캡처. 이름이 `/Overwrite` 로 오염되지 않았는지 `props NAME` 도 읽는다. `OK` 만으로 통과시키지 않는다.
- **정리**: `cleanup.txt` (시퀀스째 사라진다).
- **위험**: 문법 오류면 큐가 안 바뀌거나 이름이 바뀐다. 이미 있는 큐의 **내용을 덮는** 명령이라 스크래치 700·701 만 대상일 때만 안전하다. `Delete Cue 2 Sequence 700` 은 되돌릴 수 없다(쇼를 저장하지 않았다면 쇼 재열기로 복구). 이 줄은 S4 끝에 있어 거절돼도 뒤를 막지 않는다 — 단 S5(④)는 S4 가 끝까지 `ok` 여야 의미가 있다.

### ② 새 어순 `CueFade x`(+`/CueOnly`)

- **줄 출처**: [생성] — `_emit_cue` 의 `store_with_fade(f"Store Sequence {S} Cue {N}", 초)` + 옵션. 초 환산은 `_entry_plan`: 2박×60/120 = 1초, 1마디×4박×0.5 = 2초.
- **선례/근거**: t612 progress 3.4-1(라벨 붙은 `Store Sequence 309 Cue 1 'name'`(t531)과 `CueFade` 붙은 `Store Sequence S Cue N CueFade x /Merge`(cue_sheet_apply)만 선례, 라벨도 페이드도 없는 꼴과 `/Merge` 없는 `CueFade` 는 선례 없음). t469 verdict(`/CueOnly` 는 저장 옵션, 캡처로 확인 / 「`CueFade` 와 `/CueOnly` 를 함께 쓴 저장 줄은 쏘지 않았다」). `OK` 는 어순이 틀려도 나올 수 있다(t469:38).
- **대상**: 시퀀스 700 큐 2(`CueFade 1`)·큐 5(`CueFade 2 /CueOnly`). S4 에서 큐 5 는 `CueFade 2 /CueOnly /Overwrite`(옵션 순서는 `_overwrite_store_cue` 가 맨 끝에 붙인 결과).
- **보낼 줄**:

```text
S1b:25 [일반] Group 3 ; Attribute 'Dimmer' At 40
S1b:26 [승인카드] Store Sequence 700 Cue 2 CueFade 1
S1b:27 [일반] ClearAll
S1b:28 [일반] Set Cue 2 Sequence 700 Property 'TrigType' 'Time'
S1b:29 [일반] Set Cue 2 Sequence 700 Property 'TrigTime' 4
S1b:41 [일반] Group 3 ; Attribute 'Dimmer' At 100
S1b:42 [승인카드] Store Sequence 700 Cue 5 CueFade 2 /CueOnly
S1b:43 [일반] ClearAll
S1b:44 [일반] Set Cue 5 Sequence 700 Property 'TrigType' 'Time'
S1b:45 [일반] Set Cue 5 Sequence 700 Property 'TrigTime' 10

S4:45 [일반] Group 3 ; Attribute 'Dimmer' At 100
S4:46 [승인카드] Store Sequence 700 Cue 5 CueFade 2 /CueOnly /Overwrite
S4:47 [일반] ClearAll
S4:48 [일반] Set Cue 5 Sequence 700 Property 'TrigType' 'Time'
S4:49 [일반] Set Cue 5 Sequence 700 Property 'TrigTime' 10
```

- **되읽기**: **S1b 직후** `props NAME` 으로 이름이 `CueFade`·`1`·`/CueOnly` 같은 글자로 오염되지 않았는지(큐 2 는 S4 에서 삭제되므로 이때 확인). 페이드 값은 응답기로 못 읽는다 → onPC 큐 시트 Fade 열 캡처로 큐 2 = 1초, 큐 5 = 2초. `/CueOnly`: 큐 5 가 마지막 큐라 효과 관찰은 안 된다 — 트래킹 시트에서 큐 5 의 Cue Only 표시 여부만 본다.
- **정리**: `cleanup.txt`.
- **위험**: 어순이 틀려도 거절 대신 `OK` + 이름 오염일 수 있다. 이 줄이 거절되면 S1b 는 시퀀스 700 의 큐 1 까지만 만든 채 멈춘다(FOH 는 합본 트랙 순서 마지막이라 MOVER-D·WASH-ALL·BACK 은 이미 만들어져 있다). `/CueOnly` 는 되돌리는 명령이 없다 — 시퀀스를 지울 때까지 남는다.

### ③ Block → Track 다시 반영 때 `/Overwrite` 가 Block 표시를 지우는지

- **줄 출처**: [생성].
- **선례/근거**: t576 run-verdict(Track 이면 아무것도 보내지 않는다 — `Unblock` 안 보냄, `/Overwrite` 가 Block 표시를 지우는지 모름), t469 verdict(`Block Sequence S Cue N` 캡처 확인: 흰색 표시).
- **대상**: 시퀀스 700 큐 4: S1b 에서 `Block Sequence 700 Cue 4`, S4 에서 `Store Sequence 700 Cue 4 /Overwrite`(tracking=Track 이라 `Unblock` 줄이 **없다**).
- **보낼 줄**:

```text
S1b:35 [일반] Group 3 ; Attribute 'Dimmer' At 80
S1b:36 [승인카드] Store Sequence 700 Cue 4
S1b:37 [일반] ClearAll
S1b:38 [일반] Set Cue 4 Sequence 700 Property 'TrigType' 'Time'
S1b:39 [일반] Set Cue 4 Sequence 700 Property 'TrigTime' 8
S1b:40 [일반] Block Sequence 700 Cue 4

S4:40 [일반] Group 3 ; Attribute 'Dimmer' At 80
S4:41 [승인카드] Store Sequence 700 Cue 4 /Overwrite
S4:42 [일반] ClearAll
S4:43 [일반] Set Cue 4 Sequence 700 Property 'TrigType' 'Time'
S4:44 [일반] Set Cue 4 Sequence 700 Property 'TrigTime' 8
```

- **되읽기**: S1b 직후 onPC 트래킹 시트에서 큐 4 가 Block 표시(흰색)인지 캡처, S4 직후 같은 캡처. 표시가 남으면 에미터에 `Unblock` 줄이 필요하다(코드 변경 카드). 사라지면 `/Overwrite` 가 지운 것.
- **정리**: `cleanup.txt`. Block 이 남았을 때 임시 해제 `Unblock Sequence 700 Cue 4` 는 이 목록의 단계에 넣지 않았다(결과를 보기 전에 풀면 판정이 사라진다).
- **위험**: `Block Sequence 700 Cue 4` 는 `safe` 로 분류되지만 큐 표시를 바꾸는 쓰기다. 트래킹 시트를 응답기로 읽는 길은 확인되지 않았다 — 캡처에 의존한다.

### ④ 번호 순서 ≠ 시간 순서 큐의 타임코드 재생

- **줄 출처**: S4 의 큐 줄 [생성] (앱의 `beat_grid_reapply_summary` 가 `out_of_order = 1` 로 센다), S5/S5s 는 ⓪ 과 같은 [읽음].
- **선례/근거**: t572 run-verdict(순서 어긋난 큐의 타임코드 재생은 실기 확인 2번, 새 마디는 그 트랙 최대 번호 다음 정수). R1 기록 BACK {'1': 1, '3': 2} → R2 기록 BACK {'1': 1, '2': 3, '3': 2} (마디→큐): 마디 2 가 큐 3, 마디 3 이 큐 2.
- **대상**: 시퀀스 701: 큐 1(2초) · 큐 3(**4초**, 새 마디 2) · 큐 2(**6초**, 마디 3).
- **보낼 줄**:

```text
S4:19 [일반] Group 4 ; Attribute 'Dimmer' At 40
S4:20 [승인카드] Store Sequence 701 Cue 3
S4:21 [일반] ClearAll
S4:22 [일반] Set Cue 3 Sequence 701 Property 'TrigType' 'Time'
S4:23 [일반] Set Cue 3 Sequence 701 Property 'TrigTime' 4
S4:24 [일반] Group 4 ; Attribute 'Dimmer' At 50
S4:25 [승인카드] Store Sequence 701 Cue 2 /Overwrite
S4:26 [일반] ClearAll
S4:27 [일반] Set Cue 2 Sequence 701 Property 'TrigType' 'Time'
S4:28 [일반] Set Cue 2 Sequence 701 Property 'TrigTime' 6

S5:01 [일반] Top Timecode 70
S5:02 [호출형] Go Timecode 70

S5s:01 [호출형] Off Timecode 70
```

- **되읽기**: S4 직후 S5(`Top`→`Go`)를 보내고 `Sequences/701|CURRENTCUE` 를 0.2초 간격으로 읽는다. 기대(⓪이 H1 일 때): 2초에 1, 4초에 **3**, 6초에 **2**. 큐 번호 순서대로 갔다면 4초에 2. ⓪이 H0/H2 이면 의미가 없다 — ⓪ 결과를 먼저 본다.
- **정리**: S5s `Off Timecode 70`.
- **위험**: S5 는 S2 와 같은 줄이다. 러너는 호출마다 따로 승인·송신하므로 별도 호출이면 문제 없다. S4 이후 시퀀스 702·703 에 큐가 생겨 `Go Timecode 70` 이 네 시퀀스를 모두 돌린다(MOVER-D 팬/틸트가 움직일 수 있다).

### ⑤ 미리보기 승인이 세션 1회로 지켜지는지

- **줄 출처**: [생성] — `ChatSession._beat_grid_preview_commands(self, verb, bar)` 를 **실제로 호출**했다(`self` 자리에 `_beat_grid_applied` 만 가진 가짜 객체, 반영 상태 = S1 결과). 호출 순서: `goto` 2마디, `goto` 4마디, `off`. Goto 줄 순서는 트랙 순서(BACK→FOH)를 따른다.
- **선례/근거**: t563 run-verdict(REQ-012(b) 「세션 1회」가 실제 화면에서 지켜지는지는 실기에서 봐야 한다), `PreviewApprovalSession`, `_beat_grid_dispatch_preview`.
- **보낼 줄**:

```text
S3:01 [호출형] Goto Cue 1 Sequence 701
S3:02 [호출형] Goto Cue 2 Sequence 700
S3:03 [호출형] Goto Cue 2 Sequence 701
S3:04 [호출형] Goto Cue 4 Sequence 700
S3:05 [호출형] Off Sequence 702
S3:06 [호출형] Off Sequence 703
S3:07 [호출형] Off Sequence 701
S3:08 [호출형] Off Sequence 700
```

- **되읽기**: 승인 카드가 **첫 호출 한 번만** 뜨는지: `preview(2)` → 카드 1장, `preview(4)` → 0장, `preview_off` → 0장. 카드 수를 세는 쪽은 실행기(승인 요청 콜백)다.
- **정리**: `Off Sequence 700~703` 줄이 곧 정리다.
- **위험**: 게이트가 `Goto Cue … Sequence N` 의 대상 본문을 호출마다 읽으므로 카드가 두 번째에도 뜰 수 있다 — 그게 판정 대상이다. 세션 1회 승인 상태는 고정 승인 러너에는 없다(`PreviewApprovalSession` 은 앱 세션 상태) → **앱 세션 경유로만 시험할 수 있고, 줄 재생만으로는 판정할 수 없다.**

### ⑥ 반영 → 다시 반영 왕복

- **줄 출처**: [생성] — 호출 사슬 `pending_preset_approvals` → `split_empty_preset_holds` → `plan_cells` → `emit_beat_grid_write_bundle` → `ChatSession._beat_grid_apply_cells` → `build_write_approval_batch`; 두 번째는 `apply_pending_approval` → 에미터(소유 기록 번호표) → `apply_beat_grid_ownership_reuse` → `beat_grid_reapply_summary`. 이 사슬은 `ChatSession.beat_grid_apply` 의 호출을 오프라인에서 따라 한 것이다(콘솔 읽기 4곳만 §6 픽스처로 대체).
- **대상**: 시퀀스 700~703 · 타임코드 70. S1 의 줄(S1a+S1b 75줄)과 S4(50줄)는 §7 단계 전문. S1 승인 번들 sha256 `47499900f19118706ce5fdfbe1ca4f8822bd2b3edbbbe4796c8ba683a6a9e3c2` (S1a+S1b 를 이은 값과 같음을 생성기가 단언), S4 `8946e1e126ffe7418f6acee4ab8311d8643beaf3f85b4caf27c4a6cfef8e27e3`.
- **되읽기**: S4 직후 시퀀스 700~703 이 **새로 생기지 않았다**(704 이상 없음), 타임코드 70 트랙 **4개 그대로**(5개 이상이면 `Assign` 중복), 이름 그대로. S4 에 `Store Timecode`·`Assign` 줄과 맨 `Store Sequence S` 줄은 0줄이다 — 생성기가 단언한다.
- **정리**: `cleanup.txt`.
- **위험**: S4 에는 `Set Sequence S Property 'Name'` 줄이 남는다(이름 갱신은 해롭지 않다고 판단, 이름이 같으면 무변화). **저장 큐가 없던 트랙(702·703)의 첫 큐 저장이 S4 에서 처음 나가며, 그때도 Name 줄이 큐 저장 뒤에 따라붙는다** — 이미 있는 시퀀스에 `Store Sequence 702 Cue 1` 이 먹히는지는 이 목록이 처음 시험한다.

### ⑦ `trigger_beat` 로 미룬 `TrigTime`

- **줄 출처**: [생성].
- **선례/근거**: t576 run-verdict(`trigger_beat` → `TrigTime` = 마디 시작 + (박−1)×60/BPM). 3마디 시작 6.000초 + (3−1)×0.5 = 7.000 → `TrigTime 7`. 대조: 트리거 없는 2마디 `TrigTime 4`, 4마디 `TrigTime 8`.
- **대상**: 시퀀스 700 큐 3.
- **보낼 줄**:

```text
S1b:30 [일반] Group 3 ; Attribute 'Dimmer' At 60
S1b:31 [승인카드] Store Sequence 700 Cue 3
S1b:32 [일반] ClearAll
S1b:33 [일반] Set Cue 3 Sequence 700 Property 'TrigType' 'Time'
S1b:34 [일반] Set Cue 3 Sequence 700 Property 'TrigTime' 7
```

- **되읽기**: `props NAME,TRIGTYPE,TRIGTIME` 로 큐 3 = `Time`·`7`(t474 방식, 0.001초 안). ⓪이 H1 이면 재생 중 CURSOR 7.0 부근에서 큐 3 으로 넘어가는지도 본다.
- **정리**: `cleanup.txt`.
- **위험**: 읽기 일치는 「값이 저장됐다」까지다. 「그 시각에 실제로 선다」는 ⓪과 같은 미확인 위에 있다.

### ⑧ 새 위치 프리셋 만들기 줄을 반영 묶음 앞에 섞기

- **줄 출처**: [생성] — `position_preset_outcomes` → `plan_cells`(`aim_pan_tilt` · `aimed_commands` · `position_preset_store_commands`). 입력 좌표는 t516 측정값(POSX −5.5…5.5, POSY −2.5, POSZ 6.8), 회전 0 가정. 만들기 줄은 묶음 **맨 앞**(`cells = [*creations, *에미터 칸]`).
- **선례/근거**: t592 run-verdict(꼴 자체는 t474 run3 실기 10/10, **묶음 섞기는 선례 없음**).
- **대상**: 위치 프리셋 풀 2 슬롯 351, 장비 521~528, 목표 (0,0,0). 그 프리셋을 부르는 큐는 S4 의 시퀀스 702 큐 1.
- **보낼 줄**:

```text
S1a:01 [일반] Fixture 521 ; Attribute 'Pan' At -65.6 ; Attribute 'Tilt' At 41.6
S1a:02 [일반] Fixture 522 ; Attribute 'Pan' At -57.5 ; Attribute 'Tilt' At 34.4
S1a:03 [일반] Fixture 523 ; Attribute 'Pan' At -43.3 ; Attribute 'Tilt' At 26.8
S1a:04 [일반] Fixture 524 ; Attribute 'Pan' At -17.5 ; Attribute 'Tilt' At 21.1
S1a:05 [일반] Fixture 525 ; Attribute 'Pan' At 17.5 ; Attribute 'Tilt' At 21.1
S1a:06 [일반] Fixture 526 ; Attribute 'Pan' At 43.3 ; Attribute 'Tilt' At 26.8
S1a:07 [일반] Fixture 527 ; Attribute 'Pan' At 57.5 ; Attribute 'Tilt' At 34.4
S1a:08 [일반] Fixture 528 ; Attribute 'Pan' At 65.6 ; Attribute 'Tilt' At 41.6
S1a:09 [승인카드] Store Preset 2.351
S1a:10 [일반] Label Preset 2.351 'SCR POS'
S1a:11 [일반] ClearAll

S4:01 [일반] Group 12 ; At Preset 2.351
S4:02 [승인카드] Store Sequence 702 Cue 1
S4:04 [일반] ClearAll
S4:05 [일반] Set Cue 1 Sequence 702 Property 'TrigType' 'Time'
S4:06 [일반] Set Cue 1 Sequence 702 Property 'TrigTime' 2
```

- **되읽기**: `state:PresetPools/2` 에 i=351, 이름 `SCR POS`. 팬/틸트 값은 값 필드 읽기(위치 풀 선례 없음)나 육안: S4 후 시퀀스 702 를 `Goto Cue 1` 하면 MOVER-D 8대가 같은 점을 보는지 onPC 캡처.
- **정리**: `cleanup.txt` (`Delete Preset 2.351 /NoConfirm`).
- **위험**: 조준 값은 라이브 장비 좌표에서 계산된다. 좌표가 t516 시점과 다르거나 `ROTX/ROTY` 가 0 이 아니면 앱은 번호 전체를 보류한다 — 그러면 이 줄 자체가 나가지 않는다. `Store Preset 2.351` 은 승인카드이고 빈 슬롯이 아니면 덮어쓴다.

### ⑨ 효과 프리셋 만들기(`/Universal`)를 반영 묶음에 섞기 + 여러 그룹 선택

- **줄 출처**: ⑨-a [생성] — `effect_preset_outcomes` → `build_fx_preset_bundle`, 템플릿 `pulse-beat`(Dimmer) 2박 주기 → `At Speed 60`(= BPM 120 ÷ 2). ⑨-b **[조립]** — 같은 함수로 슬롯 97 번들을 만든 뒤 `Group 4` 줄만 `Group 4 + 3` 으로 바꿨다. 다중 그룹 선택 문형은 `server/design/cue_sheet_apply.py` 의 `Group a + b + …` 선례를 따랐다(효과 프리셋 저장과 함께 쓴 기록은 없다).
- **선례/근거**: t593 run-verdict(여러 그룹이 같은 효과 번호를 쓰면 앱이 보류 — 선례 없음), M1 ④ `미확인` → 에미터가 **효과 참조 큐(BACK 4마디)를 막는다**(§5 막힌 칸). 만들기 줄은 그 큐와 상관없이 나간다.
- **대상**: 풀 22 슬롯 98(⑨-a, 그룹 4), 슬롯 97(⑨-b, 그룹 4+3).
- **보낼 줄**:

```text
S1a:17 [일반] ChangeDestination Root
S1a:18 [일반] ClearAll
S1a:19 [일반] Group 4
S1a:20 [일반] Attribute 'Dimmer' At 100
S1a:21 [일반] Step 2
S1a:22 [일반] Attribute 'Dimmer' At 0
S1a:23 [일반] Attribute 'Dimmer' At Phase 0 Thru 360
S1a:24 [일반] Attribute 'Dimmer' At Speed 60
S1a:25 [승인카드] Store Preset 22.98 'SCR FX' /Universal
S1a:26 [일반] Label Preset 22.98 'SCR FX'
S1a:27 [일반] ClearAll

S6:01 [일반] ChangeDestination Root
S6:02 [일반] ClearAll
S6:03 [일반] Group 4 + 3
S6:04 [일반] Attribute 'Dimmer' At 100
S6:05 [일반] Step 2
S6:06 [일반] Attribute 'Dimmer' At 0
S6:07 [일반] Attribute 'Dimmer' At Phase 0 Thru 360
S6:08 [일반] Attribute 'Dimmer' At Speed 60
S6:09 [승인카드] Store Preset 22.97 'SCR FX MULTI' /Universal
S6:10 [일반] Label Preset 22.97 'SCR FX MULTI'
S6:11 [일반] ClearAll
```

- **되읽기**: `state:PresetPools/22` 에 i=98(`SCR FX`), 97(`SCR FX MULTI`). 효과 내용(스텝 2개·`At Speed 60`·`Phase`)은 응답기로 읽는 길이 기록에 없다 → onPC 프리셋 편집기 캡처. t601 이전에는 `Step 2` 가 중복 제거로 빠져 빈 효과가 저장됐으므로 스텝이 2개 들어갔는지가 판정 대상. ⑨-b: 그룹 4+3 장비 모두에 적용되는지.
- **정리**: `cleanup.txt` (`Delete Preset 22.98`, `22.97`).
- **위험**: 풀 22 의 이름이 쇼마다 다르다(t604: 풀 21='All 1', 풀 22='All 2'). ⑨-b 는 앱이 안 하는 짓이라 결과가 나빠도 앱 결함이 아니다. `Store Preset … /Universal` 도 승인카드다.

### ⑩ 색 프리셋 만들기 줄을 반영 묶음 앞에 섞기 · 4.n 저장값 · 큐 참조

- **줄 출처**: [생성] — `color_preset_outcomes` → `_build_bundle`. 컬러 채널 이름(`ColorRGB_R/G/B`)은 **가정**(t594 전제를 입력으로 넣음).
- **선례/근거**: t594 run-verdict(4.n 이 RGB 값으로 저장되고 큐가 그 번호를 참조하는지 되읽기). 선택+값을 한 줄로 묶어 송신 중복 제거 면제 꼴이다.
- **대상**: 색 프리셋 풀 4 슬롯 351, 그룹 10(WASH-ALL, 20대), 값 R100 G0 B50. 큐 참조: S4 의 시퀀스 703 큐 1 `Group 10 ; At Preset 4.351`.
- **보낼 줄**:

```text
S1a:12 [일반] ClearAll
S1a:13 [일반] Group 10 ; Attribute 'ColorRGB_R' At 100 ; Attribute 'ColorRGB_G' At 0 ; Attribute 'ColorRGB_B' At 50
S1a:14 [승인카드] Store Preset 4.351
S1a:15 [일반] Label Preset 4.351 'SCR COLOR'
S1a:16 [일반] ClearAll

S4:07 [일반] Group 10 ; At Preset 4.351
S4:08 [승인카드] Store Sequence 703 Cue 1
S4:10 [일반] ClearAll
S4:11 [일반] Set Cue 1 Sequence 703 Property 'TrigType' 'Time'
S4:12 [일반] Set Cue 1 Sequence 703 Property 'TrigTime' 2
```

- **되읽기**: `state:PresetPools/4` 에 i=351, 이름 `SCR COLOR`. 저장값은 `.moai/reports/t543/probe_color_values.py` 방식으로 R/G/B = 100·0·50. 큐 참조는 시퀀스 703 큐 1 을 `Goto` 한 뒤 WASH-ALL 색을 onPC 캡처.
- **정리**: `cleanup.txt` (`Delete Preset 4.351`).
- **위험**: WASH-ALL 20대에 컬러 채널이 모두 있다는 가정이 틀리면 앱이 번호를 보류한다(줄이 안 나간다). 프리셋 저장 직전 프로그래머에 Color 값이 20대 모두 들어 있어야 한다.

### ⑪ 같은 `Store` 가 한 묶음에 두 번 나갈 때 콘솔 반응 — **[조립]**

- **줄 출처**: **[조립]** — 어느 생산 경로도 같은 `Store` 줄을 한 묶음에 두 번 내지 않는다(t601 run-verdict:66). `_build_bundle` 을 같은 번호(4.352)로 두 번, 값만 다르게 불러 이었다.
- **확인용 설계**: 두 번째 색(0,100,50)이 남으면 덮어쓰기, 첫 색(100,0,50)이 남으면 두 번째 `Store` 가 무시/거절됨, 어느 쪽도 아니면 합치기.
- **대상**: 색 프리셋 풀 4 슬롯 352(그룹 10).
- **보낼 줄**:

```text
S8:01 [일반] ClearAll
S8:02 [일반] Group 10 ; Attribute 'ColorRGB_R' At 100 ; Attribute 'ColorRGB_G' At 0 ; Attribute 'ColorRGB_B' At 50
S8:03 [승인카드] Store Preset 4.352
S8:04 [일반] Label Preset 4.352 'SCR DUP'
S8:05 [일반] ClearAll
S8:06 [일반] ClearAll
S8:07 [일반] Group 10 ; Attribute 'ColorRGB_R' At 0 ; Attribute 'ColorRGB_G' At 100 ; Attribute 'ColorRGB_B' At 50
S8:08 [승인카드] Store Preset 4.352
S8:09 [일반] Label Preset 4.352 'SCR DUP'
S8:10 [일반] ClearAll
```

- **되읽기**: `state:PresetPools/4` i=352 값 읽기 → 어느 색이 남았는지. onPC 에 확인창(Overwrite/Merge 선택)이 떠 있는지 캡처. `OK` 는 판정 근거가 아니다.
- **정리**: `cleanup.txt` (`Delete Preset 4.352`).
- **위험**: 두 번째 `Store` 가 확인창을 띄우면 **그 창이 닫힐 때까지 뒤 명령이 막히거나 창에 먹힐** 수 있다(MA3 일반 동작, 이 콘솔에서 재지 않았다). **그래서 이 항목은 합본 맨 끝(S8)에 격리했다.** 리드/감독이 onPC 앞에서 창을 닫을 준비를 해야 한다. 가장 나쁜 경우 두 번째 `Store` 가 4.352 를 지우고 다시 만든다 — 스크래치 번호라 영향은 이 슬롯 안이다.

### ⑫ `Store Preset 22.0` → `PresetPools/22` 되읽기 — **[조립]**

- **줄 출처**: **[조립]** — t604 가 말한 「빈 테스트 프로그래머」를 가장 작은 값 1줄(`Fixture 111 ; Attribute 'Dimmer' At 1`)로 해석했다. 앱이 22.0 을 실제로 쓰는 꼴(`/Universal` 효과 번들)은 대안 `alt-S7b.txt` 에 [생성]으로 두었고 합본에는 넣지 않았다. `Fixture 111` 이 쇼에 있는지는 확인하지 않았다.
- **선례/근거**: t604 run-verdict(받아들여지면 그대로, 거절되거나 1 로 바뀌면 `preset_pools.yaml` `mixed_all.start` 를 `22.1` 로 — 슬롯 0 을 잰 기록 없음).
- **대상**: 프리셋 풀 22 슬롯 0.
- **보낼 줄**:

```text
S7:01 [일반] ClearAll
S7:02 [일반] Fixture 111 ; Attribute 'Dimmer' At 1
S7:03 [승인카드] Store Preset 22.0
S7:04 [일반] ClearAll
```

대안(합본 제외, `alt-S7b.txt`, sha256 `09fe722b908227d59ced270aba7030ef9cdcbffbe01d29897b655be9c15c0e4b`):

```text
ChangeDestination Root
ClearAll
Group 4
Attribute 'Dimmer' At 100
Step 2
Attribute 'Dimmer' At 0
Attribute 'Dimmer' At Phase 0 Thru 360
Attribute 'Dimmer' At Speed 60
Store Preset 22.0 'SCR FX0' /Universal
Label Preset 22.0 'SCR FX0'
ClearAll
```

- **되읽기**: `state:PresetPools/22` 에서 `i: 0` 자식이 생겼는지(성공), 아무것도 안 생겼는지(거절), `i: 1` 이 새로 생겼거나 기존 슬롯 1(`Piano Solo`)이 바뀌었는지(1 로 밀림/덮어쓰기). 이 단계 직전·직후에 풀 1~14 의 슬롯 22 도 읽어 비교한다.
- **정리**: **`cleanup-22.0.txt`** — 위 되읽기에서 풀 22 슬롯 0 이 생긴 것을 확인했을 때만(§6).
- **위험**: **`22.0` 이 「풀 22 슬롯 0」이 아니라 「현재 프리셋 종류의 22번」으로 해석될 수 있다**(MA3 표기 `종류.번호`, 이 콘솔에서 재지 않았다). 그러면 활성 종류의 22번 프리셋이 저장·덮어쓰기될 수 있고, 정리의 `Delete Preset 22.0` 은 **쇼의 진짜 프리셋을 지울 수 있다**. 직전 기준선과 직후 비교가 유일한 방어다.

## 5. 단계별 승인 목록과 합본

실행 순서이자 승인 단위다. 단계 sha256 은 `shasum -a 256 step-<단계>.txt` 와 같다(줄 끝 `\n`).

| 순서 | 단계 | v1 단계 | 항목 | 줄 수 | 합본 줄 번호 | 승인카드/호출형/일반 | sha256 | 파일 |
|---|---|---|---|---|---|---|---|---|
| 1 | S1a | S1 앞부분 | ⑧⑨⑩ ⑥(타임코드) | 29 | 1-29 | 4/0/25 | `c3e78ba1fd7d789ac8a9850b6817614acda163a8be0335fcaa03cb1abb71c2fa` | `step-S1a.txt` |
| 2 | S1b | S1 뒷부분 | ①~⑦ 첫 반영(②③⑦ 포함) | 46 | 30-75 | 13/0/33 | `06ff373ad1f900a7faa97faf1f0fee54466ee78696d5d54f8221f397cfec908b` | `step-S1b.txt` |
| 3 | S2 | S2 | ⓪ | 2 | 76-77 | 0/1/1 | `f7da225a9e7e528dfb13f2ce29095c77b24bd02c8b2ae09b13d4d996f606f9c2` | `step-S2.txt` |
| 4 | S2s | S2s | ⓪ | 1 | 78-78 | 0/1/0 | `7b0f4fb3506c09af9a52eb8b5c54d8914ad28cc12376fc881a63fbba33280887` | `step-S2s.txt` |
| 5 | S3 | S3 | ⑤ | 8 | 79-86 | 0/8/0 | `c1045c43ea43acb5a7c935f93a7c826df66fd9bc7ee8e4b700891efc4ee86d53` | `step-S3.txt` |
| 6 | S4 | S4 | ①②③④⑥ ⑧⑩ 큐 참조 | 50 | 87-136 | 10/0/40 | `8946e1e126ffe7418f6acee4ab8311d8643beaf3f85b4caf27c4a6cfef8e27e3` | `step-S4.txt` |
| 7 | S5 | S5 | ④ | 2 | 137-138 | 0/1/1 | `f7da225a9e7e528dfb13f2ce29095c77b24bd02c8b2ae09b13d4d996f606f9c2` | `step-S5.txt` |
| 8 | S5s | S5s | ④ | 1 | 139-139 | 0/1/0 | `7b0f4fb3506c09af9a52eb8b5c54d8914ad28cc12376fc881a63fbba33280887` | `step-S5s.txt` |
| 9 | S6 | S6b | ⑨-b | 11 | 140-150 | 1/0/10 | `3b80e093ea29eb0496073728227b9f7a3b1307039ba95af9ad685997316a48cd` | `step-S6.txt` |
| 10 | S7 | S7 | ⑫ | 4 | 151-154 | 1/0/3 | `2afb6195bac8b4f883a823fc927400f2a1969fd5e88bf1a2e3e44da003c46401` | `step-S7.txt` |
| 11 | S8 | S6 | ⑪ | 10 | 155-164 | 2/0/8 | `3df715705f34a9616cc860bf0e9dc2ab99cdb55675ebba68b047abc6fbfc392e` | `step-S8.txt` |

- **합본** `payload-all.txt` — 위 11개 단계를 표의 순서대로 이은 **164줄**. **sha256 `650635cfd553cb2824c86f0ad96470293d58dd96a596d71a52c59f55467fd6aa`**
- 정리: `cleanup.txt` 12줄 sha256 `cf84b16eaca1ad6e6fe4f0f1f84cf9c484db1feed3bd894ca14593b8639b0a4f` · `cleanup-22.0.txt` 3줄 sha256 `01633bc0a2c0e341f4fe8c8ff398a8e575327ae3bcef3750a825a19ffb4408b9`.
- 어느 단계든 앞 단계의 판정이 FAIL 이면 뒤를 보내지 않는다. 의존: S1b 는 S1a 위, S2·S3·S4 는 S1b 위, S5 는 S4 위(⓪이 H0/H2 이면 S5 는 건너뛴다), S6·S7·S8 은 서로 독립이다.
- **앱의 막힌 칸**(생성 결과): 첫 반영(S1) — MOVER-D 1마디(프리셋 번호가 있지만 evidence.approval이 없습니다 — REQ-LDBEAT-015(f) 위반); WASH-ALL 1마디(프리셋 번호가 있지만 evidence.approval이 없습니다 — REQ-LDBEAT-015(f) 위반); BACK 4마디(미확인 항목 1개(4) — REQ-LDBEAT-001 게이트). 다시 반영(S4) — BACK 4마디(미확인 항목 1개(4) — REQ-LDBEAT-001 게이트). MOVER-D·WASH-ALL 의 큐는 S1 에서 승인 기록이 없어 막히고(그래서 S1 에서는 빈 시퀀스만 생긴다), 승인 기록이 첫 반영 성공 뒤에 적히므로 S4 에서 나간다. BACK 4마디(효과 참조)는 M1 ④ 미확인이라 S4 에서도 막힌다.

### 단계 줄 전문

**S1a — 29줄** `c3e78ba1fd7d789a…` (GENERATED (preset creation + timecode setup))

```text
S1a:01 [일반] Fixture 521 ; Attribute 'Pan' At -65.6 ; Attribute 'Tilt' At 41.6
S1a:02 [일반] Fixture 522 ; Attribute 'Pan' At -57.5 ; Attribute 'Tilt' At 34.4
S1a:03 [일반] Fixture 523 ; Attribute 'Pan' At -43.3 ; Attribute 'Tilt' At 26.8
S1a:04 [일반] Fixture 524 ; Attribute 'Pan' At -17.5 ; Attribute 'Tilt' At 21.1
S1a:05 [일반] Fixture 525 ; Attribute 'Pan' At 17.5 ; Attribute 'Tilt' At 21.1
S1a:06 [일반] Fixture 526 ; Attribute 'Pan' At 43.3 ; Attribute 'Tilt' At 26.8
S1a:07 [일반] Fixture 527 ; Attribute 'Pan' At 57.5 ; Attribute 'Tilt' At 34.4
S1a:08 [일반] Fixture 528 ; Attribute 'Pan' At 65.6 ; Attribute 'Tilt' At 41.6
S1a:09 [승인카드] Store Preset 2.351
S1a:10 [일반] Label Preset 2.351 'SCR POS'
S1a:11 [일반] ClearAll
S1a:12 [일반] ClearAll
S1a:13 [일반] Group 10 ; Attribute 'ColorRGB_R' At 100 ; Attribute 'ColorRGB_G' At 0 ; Attribute 'ColorRGB_B' At 50
S1a:14 [승인카드] Store Preset 4.351
S1a:15 [일반] Label Preset 4.351 'SCR COLOR'
S1a:16 [일반] ClearAll
S1a:17 [일반] ChangeDestination Root
S1a:18 [일반] ClearAll
S1a:19 [일반] Group 4
S1a:20 [일반] Attribute 'Dimmer' At 100
S1a:21 [일반] Step 2
S1a:22 [일반] Attribute 'Dimmer' At 0
S1a:23 [일반] Attribute 'Dimmer' At Phase 0 Thru 360
S1a:24 [일반] Attribute 'Dimmer' At Speed 60
S1a:25 [승인카드] Store Preset 22.98 'SCR FX' /Universal
S1a:26 [일반] Label Preset 22.98 'SCR FX'
S1a:27 [일반] ClearAll
S1a:28 [승인카드] Store Timecode 70
S1a:29 [일반] Set Timecode 70 Property 'Name' 'LDBEAT Timecode 70'
```

**S1b — 46줄** `06ff373ad1f900a7…` (GENERATED (sequences + cues))

```text
S1b:01 [승인카드] Store Sequence 702
S1b:02 [일반] Set Sequence 702 Property 'Name' 'LDBEAT MOVER-D'
S1b:03 [승인카드] Assign Sequence 702 At Timecode 70
S1b:04 [승인카드] Store Sequence 703
S1b:05 [일반] Set Sequence 703 Property 'Name' 'LDBEAT WASH-ALL'
S1b:06 [승인카드] Assign Sequence 703 At Timecode 70
S1b:07 [일반] Group 4 ; Attribute 'Dimmer' At 30
S1b:08 [승인카드] Store Sequence 701 Cue 1
S1b:09 [일반] Set Sequence 701 Property 'Name' 'LDBEAT BACK'
S1b:10 [일반] ClearAll
S1b:11 [일반] Set Cue 1 Sequence 701 Property 'TrigType' 'Time'
S1b:12 [일반] Set Cue 1 Sequence 701 Property 'TrigTime' 2
S1b:13 [일반] Group 4 ; Attribute 'Dimmer' At 50
S1b:14 [승인카드] Store Sequence 701 Cue 2
S1b:15 [일반] ClearAll
S1b:16 [일반] Set Cue 2 Sequence 701 Property 'TrigType' 'Time'
S1b:17 [일반] Set Cue 2 Sequence 701 Property 'TrigTime' 6
S1b:18 [승인카드] Assign Sequence 701 At Timecode 70
S1b:19 [일반] Group 3 ; Attribute 'Dimmer' At 20
S1b:20 [승인카드] Store Sequence 700 Cue 1
S1b:21 [일반] Set Sequence 700 Property 'Name' 'LDBEAT FOH'
S1b:22 [일반] ClearAll
S1b:23 [일반] Set Cue 1 Sequence 700 Property 'TrigType' 'Time'
S1b:24 [일반] Set Cue 1 Sequence 700 Property 'TrigTime' 2
S1b:25 [일반] Group 3 ; Attribute 'Dimmer' At 40
S1b:26 [승인카드] Store Sequence 700 Cue 2 CueFade 1
S1b:27 [일반] ClearAll
S1b:28 [일반] Set Cue 2 Sequence 700 Property 'TrigType' 'Time'
S1b:29 [일반] Set Cue 2 Sequence 700 Property 'TrigTime' 4
S1b:30 [일반] Group 3 ; Attribute 'Dimmer' At 60
S1b:31 [승인카드] Store Sequence 700 Cue 3
S1b:32 [일반] ClearAll
S1b:33 [일반] Set Cue 3 Sequence 700 Property 'TrigType' 'Time'
S1b:34 [일반] Set Cue 3 Sequence 700 Property 'TrigTime' 7
S1b:35 [일반] Group 3 ; Attribute 'Dimmer' At 80
S1b:36 [승인카드] Store Sequence 700 Cue 4
S1b:37 [일반] ClearAll
S1b:38 [일반] Set Cue 4 Sequence 700 Property 'TrigType' 'Time'
S1b:39 [일반] Set Cue 4 Sequence 700 Property 'TrigTime' 8
S1b:40 [일반] Block Sequence 700 Cue 4
S1b:41 [일반] Group 3 ; Attribute 'Dimmer' At 100
S1b:42 [승인카드] Store Sequence 700 Cue 5 CueFade 2 /CueOnly
S1b:43 [일반] ClearAll
S1b:44 [일반] Set Cue 5 Sequence 700 Property 'TrigType' 'Time'
S1b:45 [일반] Set Cue 5 Sequence 700 Property 'TrigTime' 10
S1b:46 [승인카드] Assign Sequence 700 At Timecode 70
```

**S2 — 2줄** `f7da225a9e7e528d…` (READ (ChatSession._beat_grid_console_transport formula, not called))

```text
S2:01 [일반] Top Timecode 70
S2:02 [호출형] Go Timecode 70
```

**S2s — 1줄** `7b0f4fb3506c09af…` (READ (same))

```text
S2s:01 [호출형] Off Timecode 70
```

**S3 — 8줄** `c1045c43ea43acb5…` (GENERATED (ChatSession._beat_grid_preview_commands, fake self))

```text
S3:01 [호출형] Goto Cue 1 Sequence 701
S3:02 [호출형] Goto Cue 2 Sequence 700
S3:03 [호출형] Goto Cue 2 Sequence 701
S3:04 [호출형] Goto Cue 4 Sequence 700
S3:05 [호출형] Off Sequence 702
S3:06 [호출형] Off Sequence 703
S3:07 [호출형] Off Sequence 701
S3:08 [호출형] Off Sequence 700
```

**S4 — 50줄** `8946e1e126ffe741…` (GENERATED (re-apply path))

```text
S4:01 [일반] Group 12 ; At Preset 2.351
S4:02 [승인카드] Store Sequence 702 Cue 1
S4:03 [일반] Set Sequence 702 Property 'Name' 'LDBEAT MOVER-D'
S4:04 [일반] ClearAll
S4:05 [일반] Set Cue 1 Sequence 702 Property 'TrigType' 'Time'
S4:06 [일반] Set Cue 1 Sequence 702 Property 'TrigTime' 2
S4:07 [일반] Group 10 ; At Preset 4.351
S4:08 [승인카드] Store Sequence 703 Cue 1
S4:09 [일반] Set Sequence 703 Property 'Name' 'LDBEAT WASH-ALL'
S4:10 [일반] ClearAll
S4:11 [일반] Set Cue 1 Sequence 703 Property 'TrigType' 'Time'
S4:12 [일반] Set Cue 1 Sequence 703 Property 'TrigTime' 2
S4:13 [일반] Group 4 ; Attribute 'Dimmer' At 30
S4:14 [승인카드] Store Sequence 701 Cue 1 /Overwrite
S4:15 [일반] Set Sequence 701 Property 'Name' 'LDBEAT BACK'
S4:16 [일반] ClearAll
S4:17 [일반] Set Cue 1 Sequence 701 Property 'TrigType' 'Time'
S4:18 [일반] Set Cue 1 Sequence 701 Property 'TrigTime' 2
S4:19 [일반] Group 4 ; Attribute 'Dimmer' At 40
S4:20 [승인카드] Store Sequence 701 Cue 3
S4:21 [일반] ClearAll
S4:22 [일반] Set Cue 3 Sequence 701 Property 'TrigType' 'Time'
S4:23 [일반] Set Cue 3 Sequence 701 Property 'TrigTime' 4
S4:24 [일반] Group 4 ; Attribute 'Dimmer' At 50
S4:25 [승인카드] Store Sequence 701 Cue 2 /Overwrite
S4:26 [일반] ClearAll
S4:27 [일반] Set Cue 2 Sequence 701 Property 'TrigType' 'Time'
S4:28 [일반] Set Cue 2 Sequence 701 Property 'TrigTime' 6
S4:29 [일반] Group 3 ; Attribute 'Dimmer' At 20
S4:30 [승인카드] Store Sequence 700 Cue 1 /Overwrite
S4:31 [일반] Set Sequence 700 Property 'Name' 'LDBEAT FOH'
S4:32 [일반] ClearAll
S4:33 [일반] Set Cue 1 Sequence 700 Property 'TrigType' 'Time'
S4:34 [일반] Set Cue 1 Sequence 700 Property 'TrigTime' 2
S4:35 [일반] Group 3 ; Attribute 'Dimmer' At 65
S4:36 [승인카드] Store Sequence 700 Cue 3 /Overwrite
S4:37 [일반] ClearAll
S4:38 [일반] Set Cue 3 Sequence 700 Property 'TrigType' 'Time'
S4:39 [일반] Set Cue 3 Sequence 700 Property 'TrigTime' 7
S4:40 [일반] Group 3 ; Attribute 'Dimmer' At 80
S4:41 [승인카드] Store Sequence 700 Cue 4 /Overwrite
S4:42 [일반] ClearAll
S4:43 [일반] Set Cue 4 Sequence 700 Property 'TrigType' 'Time'
S4:44 [일반] Set Cue 4 Sequence 700 Property 'TrigTime' 8
S4:45 [일반] Group 3 ; Attribute 'Dimmer' At 100
S4:46 [승인카드] Store Sequence 700 Cue 5 CueFade 2 /CueOnly /Overwrite
S4:47 [일반] ClearAll
S4:48 [일반] Set Cue 5 Sequence 700 Property 'TrigType' 'Time'
S4:49 [일반] Set Cue 5 Sequence 700 Property 'TrigTime' 10
S4:50 [승인카드] Delete Cue 2 Sequence 700
```

**S5 — 2줄** `f7da225a9e7e528d…` (READ (same as S2))

```text
S5:01 [일반] Top Timecode 70
S5:02 [호출형] Go Timecode 70
```

**S5s — 1줄** `7b0f4fb3506c09af…` (READ (same as S2s))

```text
S5s:01 [호출형] Off Timecode 70
```

**S6 — 11줄** `3b80e093ea29eb04…` (ASSEMBLED (build_fx_preset_bundle, Group 4 -> Group 4 + 3))

```text
S6:01 [일반] ChangeDestination Root
S6:02 [일반] ClearAll
S6:03 [일반] Group 4 + 3
S6:04 [일반] Attribute 'Dimmer' At 100
S6:05 [일반] Step 2
S6:06 [일반] Attribute 'Dimmer' At 0
S6:07 [일반] Attribute 'Dimmer' At Phase 0 Thru 360
S6:08 [일반] Attribute 'Dimmer' At Speed 60
S6:09 [승인카드] Store Preset 22.97 'SCR FX MULTI' /Universal
S6:10 [일반] Label Preset 22.97 'SCR FX MULTI'
S6:11 [일반] ClearAll
```

**S7 — 4줄** `2afb6195bac8b4f8…` (ASSEMBLED (hand-made minimal programmer))

```text
S7:01 [일반] ClearAll
S7:02 [일반] Fixture 111 ; Attribute 'Dimmer' At 1
S7:03 [승인카드] Store Preset 22.0
S7:04 [일반] ClearAll
```

**S8 — 10줄** `3df715705f34a961…` (ASSEMBLED (color _build_bundle called twice, same number))

```text
S8:01 [일반] ClearAll
S8:02 [일반] Group 10 ; Attribute 'ColorRGB_R' At 100 ; Attribute 'ColorRGB_G' At 0 ; Attribute 'ColorRGB_B' At 50
S8:03 [승인카드] Store Preset 4.352
S8:04 [일반] Label Preset 4.352 'SCR DUP'
S8:05 [일반] ClearAll
S8:06 [일반] ClearAll
S8:07 [일반] Group 10 ; Attribute 'ColorRGB_R' At 0 ; Attribute 'ColorRGB_G' At 100 ; Attribute 'ColorRGB_B' At 50
S8:08 [승인카드] Store Preset 4.352
S8:09 [일반] Label Preset 4.352 'SCR DUP'
S8:10 [일반] ClearAll
```


## 6. 정리

`cleanup.txt` — 만든 객체를 **합본에서 기계적으로 뽑아** 만든 순서(만든 순서)로 지운다. 생성기가 「합본이 만든 객체 집합 == 정리가 지우는 객체 집합」을 단언한다(22.0 은 별도 파일).

```text
ClearAll
Delete Preset 2.351 /NoConfirm
Delete Preset 4.351 /NoConfirm
Delete Preset 22.98 /NoConfirm
Delete Timecode 70 /NoConfirm
Delete Sequence 702 /NoConfirm
Delete Sequence 703 /NoConfirm
Delete Sequence 701 /NoConfirm
Delete Sequence 700 /NoConfirm
Delete Preset 22.97 /NoConfirm
Delete Preset 4.352 /NoConfirm
ClearAll
```

`cleanup-22.0.txt` — ⑫ 가 풀 22 슬롯 0 을 **실제로 만든 것이 확인된 뒤에만**:

```text
ClearAll
Delete Preset 22.0 /NoConfirm
ClearAll
```

- 실행이 중간에서 멈췄을 때: `cleanup.txt` 를 그대로 보낸다. 만든 순서이므로 아직 안 만든 객체의 `Delete` 는 목록 끝쪽에서 만나고, 그것이 막히더라도 이미 있는 객체는 앞서 지워졌다. 없는 객체에 `Delete … /NoConfirm` 을 보내면 콘솔이 무엇을 하는지는 재지 않았다(오류로 러너가 멈출 수 있다 — 그 경우 남은 줄은 이미 없는 객체뿐이다).
- 재생 중이었다면 먼저 `Off Timecode 70` 을 손으로 보낸다(정리 파일에 `Off` 줄을 넣지 않은 이유는 §3-4).
- 순서의 가정(미측정): 프리셋을 시퀀스·타임코드보다 먼저 지운다 — 큐가 가리키는 프리셋을 지우는 것이 안전한지는 재지 않았다. 지난 정리(cleanup-1012)는 타임코드→시퀀스→프리셋 순이었고 `ok` 였다. 만든 순서를 택한 것은 「중간 정지에서 끝까지 도는 것」을 「의존 순서」보다 앞에 둔 선택이다.
- 정리가 끝나면 러너 `--probe` 로 700~703 · TC 70 · 프리셋 6개가 모두 `empty` 인지 읽어 확인한다. 읽기 전에는 「정리됨」이라고 쓰지 않는다. 어디서든 거절되면 대안: onPC 수동 삭제, 또는 쇼를 저장하지 않고 다시 열기. **`SaveShow` 는 보내지 않는다.**

## 7. 러너 `--dry-run` 결과

`uv run python -m server.tools.beatgrid_runner --dry-run --input payload-all.txt --expect-sha256 650635cfd553cb2824c86f0ad96470293d58dd96a596d71a52c59f55467fd6aa --listen-port 9005` → 종료 코드 0, 출력 전문은 `dry-run.txt`(165줄).

```text
lines=164 sha256=650635cfd553cb2824c86f0ad96470293d58dd96a596d71a52c59f55467fd6aa
1	Fixture 521 ; Attribute 'Pan' At -65.6 ; Attribute 'Tilt' At 41.6
2	Fixture 522 ; Attribute 'Pan' At -57.5 ; Attribute 'Tilt' At 34.4
3	Fixture 523 ; Attribute 'Pan' At -43.3 ; Attribute 'Tilt' At 26.8
4	Fixture 524 ; Attribute 'Pan' At -17.5 ; Attribute 'Tilt' At 21.1
5	Fixture 525 ; Attribute 'Pan' At 17.5 ; Attribute 'Tilt' At 21.1
...
161	Group 10 ; Attribute 'ColorRGB_R' At 0 ; Attribute 'ColorRGB_G' At 100 ; Attribute 'ColorRGB_B' At 50
162	Store Preset 4.352
163	Label Preset 4.352 'SCR DUP'
164	ClearAll
```

정리 파일도 같은 방식으로 검증했다(종료 코드 0, `dry-run-cleanup.txt`).

## 8. v1 대비 차이

v1 합본 184줄(sha256 `9ca962e47fab66e8e95dc7ce447c2fcec013a4f8e1161d711e53d6329c7faeea`) → v2 합본 164줄. 줄 배정은 §0 요약표와 같은 분할(가장 구체적인 항목 하나)이고, 줄 집합(중복 포함) 비교다 — 위치만 바뀐 줄은 세지 않는다.

| 항목 | v1 줄 | v2 줄 | 제거 | 추가 |
|---|---|---|---|---|
| ⓪ | 3 | 3 | 0 | 0 |
| ① | 16 | 16 | 3 | 3 |
| ② | 15 | 15 | 3 | 3 |
| ③ | 11 | 11 | 2 | 2 |
| ④ | 13 | 13 | 2 | 2 |
| ⑤ | 8 | 8 | 0 | 0 |
| ⑥ | 33 | 31 | 5 | 3 |
| ⑦ | 5 | 5 | 1 | 1 |
| ⑧ | 16 | 16 | 1 | 1 |
| ⑨ | 22 | 22 | 0 | 0 |
| ⑩ | 10 | 10 | 1 | 1 |
| ⑪ | 10 | 10 | 0 | 0 |
| ⑫ | 4 | 4 | 0 | 0 |
| 정리(합본 밖으로 이동) | 18 | 12 (+3) | — | — |

- v1 합본 안의 정리 S9(18줄: `Off` 5 · `ClearAll` 2 · `Delete` 11)는 합본 밖으로 나갔다. 정리 줄은 `cleanup.txt`(12줄: `Delete` 10 + 앞뒤 `ClearAll`)와 `cleanup-22.0.txt`(3줄)로 바뀌었다. `Off` 5줄은 빠졌고(§3-4), `Delete` 11줄은 같은 객체 11개를 가리킨다.
- 합본 안의 변화는 어순 하나에서 나온다: 제거 18줄 = 옛 어순 저장 줄 16 + 맨 `Store Sequence 700`/`701` 2, 추가 16줄 = 새 어순 저장 줄 16. 그 밖의 모든 줄은 v1 과 글자가 같고 위치만 다르다(트랙 순서·단계 재배치).

```text
①: 제거 3 · 추가 3
- Store Cue 1 Sequence 700 /Overwrite
- Store Cue 1 Sequence 701 /Overwrite
- Store Cue 3 Sequence 700 /Overwrite
+ Store Sequence 700 Cue 1 /Overwrite
+ Store Sequence 700 Cue 3 /Overwrite
+ Store Sequence 701 Cue 1 /Overwrite

②: 제거 3 · 추가 3
- Store Cue 2 Sequence 700 CueFade 1
- Store Cue 5 Sequence 700 CueFade 2 /CueOnly
- Store Cue 5 Sequence 700 CueFade 2 /CueOnly /Overwrite
+ Store Sequence 700 Cue 2 CueFade 1
+ Store Sequence 700 Cue 5 CueFade 2 /CueOnly
+ Store Sequence 700 Cue 5 CueFade 2 /CueOnly /Overwrite

③: 제거 2 · 추가 2
- Store Cue 4 Sequence 700
- Store Cue 4 Sequence 700 /Overwrite
+ Store Sequence 700 Cue 4
+ Store Sequence 700 Cue 4 /Overwrite

④: 제거 2 · 추가 2
- Store Cue 2 Sequence 701 /Overwrite
- Store Cue 3 Sequence 701
+ Store Sequence 701 Cue 2 /Overwrite
+ Store Sequence 701 Cue 3

⑥: 제거 5 · 추가 3
- Store Cue 1 Sequence 700
- Store Cue 1 Sequence 701
- Store Cue 2 Sequence 701
- Store Sequence 700
- Store Sequence 701
+ Store Sequence 700 Cue 1
+ Store Sequence 701 Cue 1
+ Store Sequence 701 Cue 2

⑦: 제거 1 · 추가 1
- Store Cue 3 Sequence 700
+ Store Sequence 700 Cue 3

⑧: 제거 1 · 추가 1
- Store Cue 1 Sequence 702
+ Store Sequence 702 Cue 1

⑩: 제거 1 · 추가 1
- Store Cue 1 Sequence 703
+ Store Sequence 703 Cue 1
```

## 9. 다시 만드는 법

```bash
cd <워크트리 루트>
uv run python <절대경로>/.moai/reports/t608/v2/gen_payload.py --repo .   --out <절대경로>/.moai/reports/t608/v2 --v1 <절대경로>/.moai/reports/t608
```

픽스처(번호·그룹·장비 좌표·곡 타이밍·트랙 순서)는 스크립트 머리의 상수다. 번호를 바꾸면 러너의 `--probe` 번호(`PROBE_SEQUENCES` 등)도 같이 바꿔야 한다. 생성기는 `server/` 의 현재 트리를 import 하므로 기준 커밋이 바뀌면 줄이 바뀔 수 있다 — 다시 돌려 sha256 을 갱신한다.

## 10. Gaps — 측정하지 않았거나 생성하지 못한 것

- **콘솔 접촉 0**: `ping`·`state`·`props`·`--probe` 도 보내지 않았다. 라이브 점유 번호, 응답기 버전, onPC 가동 여부, 그룹 소속, 장비 좌표·회전, 컬러 채널 이름, `Fixture 111` 의 존재를 모른다. 이 입력은 픽스처다(위치: v1 §3 에서 옮긴 값, `ColorRGB_*` 와 `Fixture 111` 은 **가정**). 프리셋 풀 상태는 R1 에서 「2·4 풀 비어 있음, 풀 22 는 슬롯 1 `Piano Solo` 만」(t543 읽은 값, 낡을 수 있음)으로 가정했다.
- **새 어순은 실기 선례가 없다**: 라벨도 페이드도 없는 `Store Sequence S Cue N`, `/Merge` 없는 `CueFade`, `CueFade` + `/CueOnly` 조합, `Store Sequence S Cue N … /Overwrite`, 이미 있는 빈 시퀀스에 대한 첫 큐 저장(702·703), `Delete Cue` — 전부 미측정이다. 이 문서의 줄이 거절되지 않는다는 보장은 없다.
- **앱 세션을 돌리지 않았다**: `ChatSession.beat_grid_apply` 를 호출하지 않고 같은 함수 사슬을 따라 호출했다. 콘솔 읽기 4곳(풀 슬롯·그룹 소속·장비 좌표·컬러 채널)을 픽스처로 대체한 부분은 `_plan_new_presets` 사본이다. 그래서 S1 sha256 은 「`build_write_approval_batch` 가 낸 값」이지 실제 세션이 낸 값과 대조한 것이 아니다.
- **트랙 순서는 시험용 선택이다**: 실제 앱은 곡 격자의 그룹 순서대로 낸다. 같은 줄이라도 트랙 순서가 다르면 합본 sha256 이 다르다.
- **[읽음] 줄**: `Top`/`Go`/`Off Timecode` 는 `_beat_grid_console_transport` 를 읽고 적었다(송신과 한 몸이라 호출 못 함).
- **⓪ 의 H0/H1/H2 는 판정하지 않았다.** 코드 판독으로는 `Go Timecode` 가 이벤트 없는 타임코드의 `Time` 트리거 큐를 부른다는 근거도 반대 근거도 없다.
- **⑤ 의 「세션 1회 승인」**은 줄 재생으로 시험할 수 없다(앱 세션 필요).
- **⑨ 의 효과 참조 큐**는 M1 ④ 미확인 때문에 앱이 막는다. 가설 확인용으로 ④를 통과로 가정한 줄은 만들지 않았다. ⑨-b·⑪·⑫ 는 [조립]이다.
- **정리의 `Delete` 문법**은 `Delete Sequence N` · `Delete Timecode N` · `Delete Preset P.S` 의 `/NoConfirm` 형이 지난 실행에서 `OK` + 사후 `empty` 였다는 것까지다(발췌가 잘려 있어 verdict 라벨을 믿었다). 없는 객체에 대한 `Delete` 반응, 큐가 참조하는 프리셋 삭제, `Delete Preset 22.0` 의 해석은 재지 않았다.
- **onPC 캡처는 수동이다.** 캡처에서 무엇을 PASS 로 볼지(Block 표시 색, Fade 열 값)의 판정 기준은 t469 설명 외에 새로 정하지 않았다.
- **v1 문서의 선례 인용**(t520·t474·t498·t572·t576·t593·t594·t601·t604 등)은 v1 에서 옮겼다. 이번에 그 파일들을 다시 열어 대조하지 않았다.
- **잔여 위험**: 단계는 서로 의존한다. 중간에 실패해 상태가 어긋나면 이후 줄의 `/Overwrite`·`Delete Cue` 가 존재하지 않는 큐를 대상으로 나갈 수 있다. 실패 지점에서 멈추고 `cleanup.txt` 로 정리한 뒤 처음부터 다시 하는 것이 안전하다. `gen_payload.py` 는 git 에 커밋하지 않았다(주 체크아웃의 추적 안 되는 파일).
