# t608 승인 목록 v3 — 박자 격자 송신 실기 확인 묶음 (⓪~⑫, t614 점 꼴 배정 + 단계별 정리)

- 작성 기준: origin/main `1973c481` (PR #656 · 카드 t614 병합 직후). v2 는 t612 어순 기준(`efb40e03` 계열)이었다.
- 콘솔 접촉 0. 이 문서의 줄은 전부 오프라인에서 현재 main 의 순수 함수를 불러 만들었다(소켓·OSC·UDP·TCP·`run_commands` 호출 없음, 러너는 `--dry-run` 만 돌렸다).
- 워크트리: `.claude/worktrees/t608-v3` (브랜치 `WT-t608-payload-v3`, 커밋 없음). 생성기: `gen_payload.py` (이 폴더). 다시 돌리는 법은 §9.

## 0. 결론 먼저

1. **타임코드 배정이 바뀌었다.** v2 의 맨 꼴 `Assign Sequence S At Timecode 70` 은 같은 타임코드의 둘째부터 `Illegal object` 였다(run-S1b: 702 는 OK, 703 에서 거절). 이제 에미터가 트랙 순번 k 로 점 꼴을 낸다: `Assign Sequence 702 At Timecode 70.1.1` · `Assign Sequence 703 At Timecode 70.1.2` · `Assign Sequence 701 At Timecode 70.1.3` · `Assign Sequence 700 At Timecode 70.1.4`. 설정 쪽에는 `Store Timecode 70.1` 한 줄이 더해졌다(S1a 끝).
2. **정리는 단계마다 따로 있다.** v2 정리는 만든 적 없는 `Sequence 701` 을 지우다 `Illegal object` 로 멈췄다. v3 의 `cleanup-after-<단계>.txt` 는 그 단계까지 **끝까지 갔을 때** 존재하는 객체만 지운다. 단계 중간에서 멈췄다면 파일을 고르지 말고 §4-2 의 도우미나 `--probe` 결과로 고른다.
3. 항목 ⓪~⑫ 와 번호(시퀀스 700~703 · 타임코드 70 · 프리셋 2.351/4.351/4.352/22.97/22.98/22.0)는 v2 와 같다. 합본 `payload-all.txt` **165줄** sha256 `77d670d7e537138e33e176ae4a409b470ee51baadfc8ec48a6199409df0596f1`. v2 합본은 164줄이었다.
4. 앱이 만든 줄의 변화는 타임코드 배정·설정 쪽뿐이다(§2). 큐·프리셋 줄은 v2 와 글자가 같다.
5. **실행 전 `--probe` 필수**: 지난 v2 실행의 정리가 중간에 멈췄으므로 콘솔에 잔재가 있을 수 있다(§8 위험 1).

## 1. 바뀐 근거

| 사실 | 값 | 출처 |
|---|---|---|
| 맨 꼴 배정의 둘째 거절 | `Assign Sequence 702 At Timecode 70` OK → `Assign Sequence 703 At Timecode 70` `Illegal object`, `stopped_at 6` | `.moai/reports/t608/v2/run-S1b.jsonl` (주 체크아웃, 이 세션에서 읽음) |
| 정리 중단 | index 8 `Delete Sequence 701 /NoConfirm` → `Illegal object`, 701 은 만든 적 없음 | `run-cleanup.jsonl` |
| 점 꼴 선례 | t553(8트랙)·t520(2트랙)·t506·t516 — 모두 `Store … .1` 앞에 `Set … Duration` 줄이 있었고 이번 줄에는 Duration 이 없다 | `.moai/reports/t614/progress.md` §1, §6 |
| S1a 의 객체 | Preset 2.351, Preset 4.351, Preset 22.98, Timecode 70 | 생성기가 Store 줄에서 뽑음 |
| S1b 의 객체 | Sequence 702, Sequence 703, Sequence 701, Sequence 700 | 같음 |

타임코드 설정 줄(S1a 중): `Store Timecode 70` · `Set Timecode 70 Property 'Name' 'LDBEAT Timecode 70'` · `Store Timecode 70.1`

## 2. v2 대비 항목별 차이

줄 집합(중복 포함) 비교이고 항목 배정은 v2 의 분할 규칙(가장 구체적인 항목 하나)과 같다. 합본 v2 164줄 → v3 165줄.

| 항목 | v2 줄 | v3 줄 | 제거 | 추가 |
|---|---|---|---|---|
| ⓪ | 3 | 3 | 0 | 0 |
| ① | 16 | 16 | 0 | 0 |
| ② | 15 | 15 | 0 | 0 |
| ③ | 11 | 11 | 0 | 0 |
| ④ | 13 | 13 | 0 | 0 |
| ⑤ | 8 | 8 | 0 | 0 |
| ⑥ | 31 | 32 | 4 | 5 |
| ⑦ | 5 | 5 | 0 | 0 |
| ⑧ | 16 | 16 | 0 | 0 |
| ⑨ | 22 | 22 | 0 | 0 |
| ⑩ | 10 | 10 | 0 | 0 |
| ⑪ | 10 | 10 | 0 | 0 |
| ⑫ | 4 | 4 | 0 | 0 |

- v2 에만 있는 줄 4개, v3 에만 있는 줄 5개. 나머지는 글자가 같다.

```text
⑥: 제거 4 · 추가 5
- Assign Sequence 700 At Timecode 70
- Assign Sequence 701 At Timecode 70
- Assign Sequence 702 At Timecode 70
- Assign Sequence 703 At Timecode 70
+ Assign Sequence 700 At Timecode 70.1.4
+ Assign Sequence 701 At Timecode 70.1.3
+ Assign Sequence 702 At Timecode 70.1.1
+ Assign Sequence 703 At Timecode 70.1.2
+ Store Timecode 70.1
```

## 3. 단계 파일과 합본

실행 순서이자 승인 단위다. 러너는 파일 하나를 번들 하나·승인 한 번으로 보내고 `ok` 가 아닌 첫 줄에서 멈춘다. 단계 sha256 은 `shasum -a 256 step-<단계>.txt` 와 같다.

| 순서 | 단계 | 줄 수 | 합본 줄 번호 | 승인카드/호출형/일반 | 만드는 객체 | sha256 | 파일 |
|---|---|---|---|---|---|---|---|
| 1 | S1a | 30 | 1-30 | 5/0/25 | Preset 2.351, Preset 4.351, Preset 22.98, Timecode 70 | `3276806f74a5711dd2807138874edfbf30bd5e496258e2406bcf07919fa62d02` | `step-S1a.txt` |
| 2 | S1b | 46 | 31-76 | 13/0/33 | Sequence 702, Sequence 703, Sequence 701, Sequence 700 | `fb11c5bd378ea23667a4c7a00c892a2e4e91916ca9f5683581ae8a8806f7a298` | `step-S1b.txt` |
| 3 | S2 | 2 | 77-78 | 0/1/1 | 없음 | `f7da225a9e7e528dfb13f2ce29095c77b24bd02c8b2ae09b13d4d996f606f9c2` | `step-S2.txt` |
| 4 | S2s | 1 | 79-79 | 0/1/0 | 없음 | `7b0f4fb3506c09af9a52eb8b5c54d8914ad28cc12376fc881a63fbba33280887` | `step-S2s.txt` |
| 5 | S3 | 8 | 80-87 | 0/8/0 | 없음 | `c1045c43ea43acb5a7c935f93a7c826df66fd9bc7ee8e4b700891efc4ee86d53` | `step-S3.txt` |
| 6 | S4 | 50 | 88-137 | 10/0/40 | 없음 | `8946e1e126ffe7418f6acee4ab8311d8643beaf3f85b4caf27c4a6cfef8e27e3` | `step-S4.txt` |
| 7 | S5 | 2 | 138-139 | 0/1/1 | 없음 | `f7da225a9e7e528dfb13f2ce29095c77b24bd02c8b2ae09b13d4d996f606f9c2` | `step-S5.txt` |
| 8 | S5s | 1 | 140-140 | 0/1/0 | 없음 | `7b0f4fb3506c09af9a52eb8b5c54d8914ad28cc12376fc881a63fbba33280887` | `step-S5s.txt` |
| 9 | S6 | 11 | 141-151 | 1/0/10 | Preset 22.97 | `3b80e093ea29eb0496073728227b9f7a3b1307039ba95af9ad685997316a48cd` | `step-S6.txt` |
| 10 | S7 | 4 | 152-155 | 1/0/3 | Preset 22.0 | `2afb6195bac8b4f883a823fc927400f2a1969fd5e88bf1a2e3e44da003c46401` | `step-S7.txt` |
| 11 | S8 | 10 | 156-165 | 2/0/8 | Preset 4.352 | `3df715705f34a9616cc860bf0e9dc2ab99cdb55675ebba68b047abc6fbfc392e` | `step-S8.txt` |

- **합본** `payload-all.txt` — 위 11개 단계를 표의 순서대로 이은 **165줄**. sha256 `77d670d7e537138e33e176ae4a409b470ee51baadfc8ec48a6199409df0596f1`
- 의존: S1b 는 S1a 위, S2·S3·S4 는 S1b 위, S5 는 S4 위(⓪이 H0/H2 이면 건너뜀), S6·S7·S8 은 서로 독립이다.
- 앱의 막힌 칸(생성 결과): 첫 반영 — MOVER-D 1마디(프리셋 번호가 있지만 evidence.approval이 없습니다 — REQ-LDBEAT-015(f) 위반); WASH-ALL 1마디(프리셋 번호가 있지만 evidence.approval이 없습니다 — REQ-LDBEAT-015(f) 위반); BACK 4마디(미확인 항목 1개(4) — REQ-LDBEAT-001 게이트). 다시 반영 — BACK 4마디(미확인 항목 1개(4) — REQ-LDBEAT-001 게이트).
- S1 승인 번들 sha256(앱 함수가 낸 값) `ed540b33abbd60d3d97e699b4fe42261e61ddcfb36cb2c1d1b989d24aa58883f` = S1a+S1b 를 이은 값(생성기가 단언). S4 `8946e1e126ffe7418f6acee4ab8311d8643beaf3f85b4caf27c4a6cfef8e27e3`.

## 4. 정리

### 4-1. 선택표 (끝까지 간 단계 기준)

보낼 파일은 **마지막으로 전부 `ok` 였던 단계**로 고른다. 객체를 만들지 않는 단계(S2·S2s·S3·S5·S5s)에서 멈췄다면 파일이 바로 앞 단계의 것과 같다(sha256 도 같다).

| 마지막으로 끝까지 `ok` 였던 단계 | 보낼 파일 | 비고 |
|---|---|---|
| 아무것도 안 보냄 | 없음 | 정리할 것 없음 |
| S1a | `cleanup-after-S1a.txt` | |
| S1b, S2, S2s, S3, S4, S5, S5s | `cleanup-after-S1b.txt` (= S2..S5s 파일과 동일) | 재생 중이면 먼저 `Off Timecode 70` 을 손으로(§4-3) |
| S6 (S7·S8 은 안 보냄) | `cleanup-after-S6.txt` | 22.97 포함 |
| S7 까지 | `cleanup-after-S7.txt` + 확인 뒤 `cleanup-22.0.txt` | 22.0 은 별도, §4-3 |
| S8 까지 | `cleanup-after-S8.txt` | 4.352 포함 (S6 을 건너뛰었다면 아래 `only` 파일) |
| S6 또는 S8 만 단독 실행 | `cleanup-only-S6.txt` / `cleanup-only-S8.txt` | S1 계열은 건드리지 않음 |
| **어느 단계든 중간에서 멈춤** | 파일 고르지 않음 → §4-2 | 만든 객체가 단계 안 어디까지인지 모른다 |

| 파일 | 줄 수 | 지우는 객체 | sha256 |
|---|---|---|---|
| `cleanup-after-S1a.txt` | 6 | Timecode 70, Preset 2.351, Preset 4.351, Preset 22.98 | `eb9b085e25dfc76cf4a8d4d094effa9c41a311d04d63ef33283efe88d5866873` |
| `cleanup-after-S1b.txt` | 10 | Timecode 70, Sequence 702, Sequence 703, Sequence 701, Sequence 700, Preset 2.351, Preset 4.351, Preset 22.98 | `e0e3c2fdcaa1ca07bafc38e5247cd114e623f944e9efc7a38f1013b3ba207ec5` |
| `cleanup-after-S2.txt` | 10 | Timecode 70, Sequence 702, Sequence 703, Sequence 701, Sequence 700, Preset 2.351, Preset 4.351, Preset 22.98 | `e0e3c2fdcaa1ca07bafc38e5247cd114e623f944e9efc7a38f1013b3ba207ec5` |
| `cleanup-after-S2s.txt` | 10 | Timecode 70, Sequence 702, Sequence 703, Sequence 701, Sequence 700, Preset 2.351, Preset 4.351, Preset 22.98 | `e0e3c2fdcaa1ca07bafc38e5247cd114e623f944e9efc7a38f1013b3ba207ec5` |
| `cleanup-after-S3.txt` | 10 | Timecode 70, Sequence 702, Sequence 703, Sequence 701, Sequence 700, Preset 2.351, Preset 4.351, Preset 22.98 | `e0e3c2fdcaa1ca07bafc38e5247cd114e623f944e9efc7a38f1013b3ba207ec5` |
| `cleanup-after-S4.txt` | 10 | Timecode 70, Sequence 702, Sequence 703, Sequence 701, Sequence 700, Preset 2.351, Preset 4.351, Preset 22.98 | `e0e3c2fdcaa1ca07bafc38e5247cd114e623f944e9efc7a38f1013b3ba207ec5` |
| `cleanup-after-S5.txt` | 10 | Timecode 70, Sequence 702, Sequence 703, Sequence 701, Sequence 700, Preset 2.351, Preset 4.351, Preset 22.98 | `e0e3c2fdcaa1ca07bafc38e5247cd114e623f944e9efc7a38f1013b3ba207ec5` |
| `cleanup-after-S5s.txt` | 10 | Timecode 70, Sequence 702, Sequence 703, Sequence 701, Sequence 700, Preset 2.351, Preset 4.351, Preset 22.98 | `e0e3c2fdcaa1ca07bafc38e5247cd114e623f944e9efc7a38f1013b3ba207ec5` |
| `cleanup-after-S6.txt` | 11 | Timecode 70, Sequence 702, Sequence 703, Sequence 701, Sequence 700, Preset 2.351, Preset 4.351, Preset 22.98, Preset 22.97 | `5e9a264e8e3dc12572f99eb409808a9ee44cf32f5631fdf759114275f36ad14c` |
| `cleanup-after-S7.txt` | 11 | Timecode 70, Sequence 702, Sequence 703, Sequence 701, Sequence 700, Preset 2.351, Preset 4.351, Preset 22.98, Preset 22.97 | `5e9a264e8e3dc12572f99eb409808a9ee44cf32f5631fdf759114275f36ad14c` |
| `cleanup-after-S8.txt` | 12 | Timecode 70, Sequence 702, Sequence 703, Sequence 701, Sequence 700, Preset 2.351, Preset 4.351, Preset 22.98, Preset 22.97, Preset 4.352 | `0ca31c7637d2602b38fa985fcb8c20533fa4c5f64071e6a4e35e022a81657bb2` |
| `cleanup-only-S6.txt` | 3 | Preset 22.97 | `03a5bc49979c0205625b74cc2f54481f710c9040716041fee3975c25bdeda224` |
| `cleanup-only-S8.txt` | 3 | Preset 4.352 | `aa36a0429fbb27ba522482374fc885c08f14aabef041178daf830589405bc58a` |
| `cleanup-22.0.txt` | 3 | Preset 22.0 | `01633bc0a2c0e341f4fe8c8ff398a8e575327ae3bcef3750a825a19ffb4408b9` |

### 4-2. 단계 도중에 멈췄을 때

러너 결과(`run-<단계>.jsonl`)에서 `status ok` 로 기록된 `Store …` 줄에 대응하는 객체만 지운다. 그 객체가 단계 안 어느 줄에서 만들어지는지는 아래 표다. 실패한 줄(`stopped_at`)과 그 뒤 줄은 보내지지 않았으므로 그 줄이 만드는 객체는 **없다**(`User Canceled Command` 처럼 효과 여부가 불분명한 응답은 `--probe` 로 확인).

| 단계 | 객체를 만드는 줄 (단계 안 번호 → 객체) |
|---|---|
| S1a | 09 → Preset 2.351 · 14 → Preset 4.351 · 25 → Preset 22.98 · 28 → Timecode 70 |
| S1b | 01 → Sequence 702 · 04 → Sequence 703 · 08 → Sequence 701 · 20 → Sequence 700 |
| S6 | 09 → Preset 22.97 |
| S7 | 03 → Preset 22.0 |
| S8 | 03 → Preset 4.352 |

- 도우미: `uv run python .moai/reports/t608/v3/cleanup_from_run.py --run <run-단계.jsonl> [--run …] --out <파일>` — `ok` 인 Store 줄에서 Timecode → Sequence → Preset 순의 Delete 목록을 만들고 sha256 을 찍는다(오프라인). `22.0` 은 `--include-22-0` 을 줘야 들어간다.
- 도우미를 못 쓰면: `--probe` (시퀀스 700~703 · 타임코드 70 · 프리셋 6개 읽기)로 `empty` 가 아닌 것만 손으로 `Delete … /NoConfirm` 한다. **없는 객체에 Delete 를 보내지 않는다**(v2 에서 `Illegal object` 로 러너가 멈췄다).
- 예: v2 의 S1b 는 index 6 에서 멈췄다. 그때 만들어진 건 S1a 의 4개 + 시퀀스 702·703 이고 701·700 은 없었다. 도우미를 `run-S1a.jsonl`·`run-S1b.jsonl` 에 돌리면 정확히 그 6개만 나온다(§9).

### 4-3. 공통 주의

- 정리 파일에 `Off Timecode/Sequence` 는 없다. 재생이 켜진 채 멈췄다면 `Off Timecode 70` 을 손으로 먼저 보낸다(타임코드가 있을 때만; 없는 객체에 `Off` 는 안 보낸다).
- `Delete Preset 22.0` 은 ⑫ 가 풀 22 슬롯 0 에 **실제로 들어간 것을 되읽기로 확인한 뒤에만** `cleanup-22.0.txt` 를 보낸다. 22.0 이 「현재 종류의 22번」으로 해석됐다면 쇼의 진짜 프리셋을 지울 수 있다.
- 순서는 cleanup-1012 에서 `ok` 였던 Timecode → Sequence → Preset 이다. 큐가 가리키는 프리셋을 시퀀스보다 먼저 지우는 것이 안전한지는 재지 않았으므로 이 순서를 유지한다.
- 정리가 끝나면 `--probe` 로 모두 `empty` 인지 읽는다. 읽기 전에는 「정리됨」이라고 쓰지 않는다. `SaveShow` 는 보내지 않는다.

## 5. 항목 요약 (선례·되읽기·위험의 전문은 v2 문서 §4 를 따른다)

v2 `approval-list.md` §4 의 항목별 선례/되읽기/위험은 이번에 다시 열지 않았고 그대로 유효하다(바뀐 건 ⑥ 의 배정 줄과 설정 줄뿐). v3 에서 새로 생기는 판정 대상은 아래 하나다.

- **⑥′ 점 꼴 배정**: S1a 끝 `Store Timecode 70.1` 이 받아들여지는지, 그 뒤 S1b 의 `Assign Sequence S At Timecode 70.1.k` 네 줄(MOVER-D .1 · WASH-ALL .2 · BACK .3 · FOH .4)이 모두 `OK` 인지. 되읽기: S1b 뒤 `state:…/Timecodes/70/1` 에 Marker + Track 4개(t520 의 되읽기 형식). 5개 이상이면 중복 배정이다.

## 6. 단계 줄 전문

줄 앞: `단계:번호 항목 [게이트분류]`. 항목은 ⓪~⑫(⑥ = 어느 항목에도 안 걸린 나머지).

**S1a — 30줄** `3276806f74a5711d…` (GENERATED (preset creation + timecode setup))

```text
S1a:01 ⑧ [일반] Fixture 521 ; Attribute 'Pan' At -65.6 ; Attribute 'Tilt' At 41.6
S1a:02 ⑧ [일반] Fixture 522 ; Attribute 'Pan' At -57.5 ; Attribute 'Tilt' At 34.4
S1a:03 ⑧ [일반] Fixture 523 ; Attribute 'Pan' At -43.3 ; Attribute 'Tilt' At 26.8
S1a:04 ⑧ [일반] Fixture 524 ; Attribute 'Pan' At -17.5 ; Attribute 'Tilt' At 21.1
S1a:05 ⑧ [일반] Fixture 525 ; Attribute 'Pan' At 17.5 ; Attribute 'Tilt' At 21.1
S1a:06 ⑧ [일반] Fixture 526 ; Attribute 'Pan' At 43.3 ; Attribute 'Tilt' At 26.8
S1a:07 ⑧ [일반] Fixture 527 ; Attribute 'Pan' At 57.5 ; Attribute 'Tilt' At 34.4
S1a:08 ⑧ [일반] Fixture 528 ; Attribute 'Pan' At 65.6 ; Attribute 'Tilt' At 41.6
S1a:09 ⑧ [승인카드] Store Preset 2.351
S1a:10 ⑧ [일반] Label Preset 2.351 'SCR POS'
S1a:11 ⑧ [일반] ClearAll
S1a:12 ⑩ [일반] ClearAll
S1a:13 ⑩ [일반] Group 10 ; Attribute 'ColorRGB_R' At 100 ; Attribute 'ColorRGB_G' At 0 ; Attribute 'ColorRGB_B' At 50
S1a:14 ⑩ [승인카드] Store Preset 4.351
S1a:15 ⑩ [일반] Label Preset 4.351 'SCR COLOR'
S1a:16 ⑩ [일반] ClearAll
S1a:17 ⑨ [일반] ChangeDestination Root
S1a:18 ⑨ [일반] ClearAll
S1a:19 ⑨ [일반] Group 4
S1a:20 ⑨ [일반] Attribute 'Dimmer' At 100
S1a:21 ⑨ [일반] Step 2
S1a:22 ⑨ [일반] Attribute 'Dimmer' At 0
S1a:23 ⑨ [일반] Attribute 'Dimmer' At Phase 0 Thru 360
S1a:24 ⑨ [일반] Attribute 'Dimmer' At Speed 60
S1a:25 ⑨ [승인카드] Store Preset 22.98 'SCR FX' /Universal
S1a:26 ⑨ [일반] Label Preset 22.98 'SCR FX'
S1a:27 ⑨ [일반] ClearAll
S1a:28 ⑥ [승인카드] Store Timecode 70
S1a:29 ⑥ [일반] Set Timecode 70 Property 'Name' 'LDBEAT Timecode 70'
S1a:30 ⑥ [승인카드] Store Timecode 70.1
```

**S1b — 46줄** `fb11c5bd378ea236…` (GENERATED (sequences + cues))

```text
S1b:01 ⑥ [승인카드] Store Sequence 702
S1b:02 ⑥ [일반] Set Sequence 702 Property 'Name' 'LDBEAT MOVER-D'
S1b:03 ⑥ [승인카드] Assign Sequence 702 At Timecode 70.1.1
S1b:04 ⑥ [승인카드] Store Sequence 703
S1b:05 ⑥ [일반] Set Sequence 703 Property 'Name' 'LDBEAT WASH-ALL'
S1b:06 ⑥ [승인카드] Assign Sequence 703 At Timecode 70.1.2
S1b:07 ⑥ [일반] Group 4 ; Attribute 'Dimmer' At 30
S1b:08 ⑥ [승인카드] Store Sequence 701 Cue 1
S1b:09 ⑥ [일반] Set Sequence 701 Property 'Name' 'LDBEAT BACK'
S1b:10 ⑥ [일반] ClearAll
S1b:11 ⑥ [일반] Set Cue 1 Sequence 701 Property 'TrigType' 'Time'
S1b:12 ⑥ [일반] Set Cue 1 Sequence 701 Property 'TrigTime' 2
S1b:13 ⑥ [일반] Group 4 ; Attribute 'Dimmer' At 50
S1b:14 ⑥ [승인카드] Store Sequence 701 Cue 2
S1b:15 ⑥ [일반] ClearAll
S1b:16 ⑥ [일반] Set Cue 2 Sequence 701 Property 'TrigType' 'Time'
S1b:17 ⑥ [일반] Set Cue 2 Sequence 701 Property 'TrigTime' 6
S1b:18 ⑥ [승인카드] Assign Sequence 701 At Timecode 70.1.3
S1b:19 ⑥ [일반] Group 3 ; Attribute 'Dimmer' At 20
S1b:20 ⑥ [승인카드] Store Sequence 700 Cue 1
S1b:21 ⑥ [일반] Set Sequence 700 Property 'Name' 'LDBEAT FOH'
S1b:22 ⑥ [일반] ClearAll
S1b:23 ⑥ [일반] Set Cue 1 Sequence 700 Property 'TrigType' 'Time'
S1b:24 ⑥ [일반] Set Cue 1 Sequence 700 Property 'TrigTime' 2
S1b:25 ② [일반] Group 3 ; Attribute 'Dimmer' At 40
S1b:26 ② [승인카드] Store Sequence 700 Cue 2 CueFade 1
S1b:27 ② [일반] ClearAll
S1b:28 ② [일반] Set Cue 2 Sequence 700 Property 'TrigType' 'Time'
S1b:29 ② [일반] Set Cue 2 Sequence 700 Property 'TrigTime' 4
S1b:30 ⑦ [일반] Group 3 ; Attribute 'Dimmer' At 60
S1b:31 ⑦ [승인카드] Store Sequence 700 Cue 3
S1b:32 ⑦ [일반] ClearAll
S1b:33 ⑦ [일반] Set Cue 3 Sequence 700 Property 'TrigType' 'Time'
S1b:34 ⑦ [일반] Set Cue 3 Sequence 700 Property 'TrigTime' 7
S1b:35 ③ [일반] Group 3 ; Attribute 'Dimmer' At 80
S1b:36 ③ [승인카드] Store Sequence 700 Cue 4
S1b:37 ③ [일반] ClearAll
S1b:38 ③ [일반] Set Cue 4 Sequence 700 Property 'TrigType' 'Time'
S1b:39 ③ [일반] Set Cue 4 Sequence 700 Property 'TrigTime' 8
S1b:40 ③ [일반] Block Sequence 700 Cue 4
S1b:41 ② [일반] Group 3 ; Attribute 'Dimmer' At 100
S1b:42 ② [승인카드] Store Sequence 700 Cue 5 CueFade 2 /CueOnly
S1b:43 ② [일반] ClearAll
S1b:44 ② [일반] Set Cue 5 Sequence 700 Property 'TrigType' 'Time'
S1b:45 ② [일반] Set Cue 5 Sequence 700 Property 'TrigTime' 10
S1b:46 ⑥ [승인카드] Assign Sequence 700 At Timecode 70.1.4
```

**S2 — 2줄** `f7da225a9e7e528d…` (READ (ChatSession._beat_grid_console_transport formula, not called))

```text
S2:01 ⓪ [일반] Top Timecode 70
S2:02 ⓪ [호출형] Go Timecode 70
```

**S2s — 1줄** `7b0f4fb3506c09af…` (READ (same))

```text
S2s:01 ⓪ [호출형] Off Timecode 70
```

**S3 — 8줄** `c1045c43ea43acb5…` (GENERATED (ChatSession._beat_grid_preview_commands, fake self))

```text
S3:01 ⑤ [호출형] Goto Cue 1 Sequence 701
S3:02 ⑤ [호출형] Goto Cue 2 Sequence 700
S3:03 ⑤ [호출형] Goto Cue 2 Sequence 701
S3:04 ⑤ [호출형] Goto Cue 4 Sequence 700
S3:05 ⑤ [호출형] Off Sequence 702
S3:06 ⑤ [호출형] Off Sequence 703
S3:07 ⑤ [호출형] Off Sequence 701
S3:08 ⑤ [호출형] Off Sequence 700
```

**S4 — 50줄** `8946e1e126ffe741…` (GENERATED (re-apply path))

```text
S4:01 ⑧ [일반] Group 12 ; At Preset 2.351
S4:02 ⑧ [승인카드] Store Sequence 702 Cue 1
S4:03 ⑥ [일반] Set Sequence 702 Property 'Name' 'LDBEAT MOVER-D'
S4:04 ⑧ [일반] ClearAll
S4:05 ⑧ [일반] Set Cue 1 Sequence 702 Property 'TrigType' 'Time'
S4:06 ⑧ [일반] Set Cue 1 Sequence 702 Property 'TrigTime' 2
S4:07 ⑩ [일반] Group 10 ; At Preset 4.351
S4:08 ⑩ [승인카드] Store Sequence 703 Cue 1
S4:09 ⑥ [일반] Set Sequence 703 Property 'Name' 'LDBEAT WASH-ALL'
S4:10 ⑩ [일반] ClearAll
S4:11 ⑩ [일반] Set Cue 1 Sequence 703 Property 'TrigType' 'Time'
S4:12 ⑩ [일반] Set Cue 1 Sequence 703 Property 'TrigTime' 2
S4:13 ① [일반] Group 4 ; Attribute 'Dimmer' At 30
S4:14 ① [승인카드] Store Sequence 701 Cue 1 /Overwrite
S4:15 ⑥ [일반] Set Sequence 701 Property 'Name' 'LDBEAT BACK'
S4:16 ① [일반] ClearAll
S4:17 ① [일반] Set Cue 1 Sequence 701 Property 'TrigType' 'Time'
S4:18 ① [일반] Set Cue 1 Sequence 701 Property 'TrigTime' 2
S4:19 ④ [일반] Group 4 ; Attribute 'Dimmer' At 40
S4:20 ④ [승인카드] Store Sequence 701 Cue 3
S4:21 ④ [일반] ClearAll
S4:22 ④ [일반] Set Cue 3 Sequence 701 Property 'TrigType' 'Time'
S4:23 ④ [일반] Set Cue 3 Sequence 701 Property 'TrigTime' 4
S4:24 ④ [일반] Group 4 ; Attribute 'Dimmer' At 50
S4:25 ④ [승인카드] Store Sequence 701 Cue 2 /Overwrite
S4:26 ④ [일반] ClearAll
S4:27 ④ [일반] Set Cue 2 Sequence 701 Property 'TrigType' 'Time'
S4:28 ④ [일반] Set Cue 2 Sequence 701 Property 'TrigTime' 6
S4:29 ① [일반] Group 3 ; Attribute 'Dimmer' At 20
S4:30 ① [승인카드] Store Sequence 700 Cue 1 /Overwrite
S4:31 ⑥ [일반] Set Sequence 700 Property 'Name' 'LDBEAT FOH'
S4:32 ① [일반] ClearAll
S4:33 ① [일반] Set Cue 1 Sequence 700 Property 'TrigType' 'Time'
S4:34 ① [일반] Set Cue 1 Sequence 700 Property 'TrigTime' 2
S4:35 ① [일반] Group 3 ; Attribute 'Dimmer' At 65
S4:36 ① [승인카드] Store Sequence 700 Cue 3 /Overwrite
S4:37 ① [일반] ClearAll
S4:38 ① [일반] Set Cue 3 Sequence 700 Property 'TrigType' 'Time'
S4:39 ① [일반] Set Cue 3 Sequence 700 Property 'TrigTime' 7
S4:40 ③ [일반] Group 3 ; Attribute 'Dimmer' At 80
S4:41 ③ [승인카드] Store Sequence 700 Cue 4 /Overwrite
S4:42 ③ [일반] ClearAll
S4:43 ③ [일반] Set Cue 4 Sequence 700 Property 'TrigType' 'Time'
S4:44 ③ [일반] Set Cue 4 Sequence 700 Property 'TrigTime' 8
S4:45 ② [일반] Group 3 ; Attribute 'Dimmer' At 100
S4:46 ② [승인카드] Store Sequence 700 Cue 5 CueFade 2 /CueOnly /Overwrite
S4:47 ② [일반] ClearAll
S4:48 ② [일반] Set Cue 5 Sequence 700 Property 'TrigType' 'Time'
S4:49 ② [일반] Set Cue 5 Sequence 700 Property 'TrigTime' 10
S4:50 ① [승인카드] Delete Cue 2 Sequence 700
```

**S5 — 2줄** `f7da225a9e7e528d…` (READ (same as S2))

```text
S5:01 ④ [일반] Top Timecode 70
S5:02 ④ [호출형] Go Timecode 70
```

**S5s — 1줄** `7b0f4fb3506c09af…` (READ (same as S2s))

```text
S5s:01 ④ [호출형] Off Timecode 70
```

**S6 — 11줄** `3b80e093ea29eb04…` (ASSEMBLED (build_fx_preset_bundle, Group 4 -> Group 4 + 3))

```text
S6:01 ⑨ [일반] ChangeDestination Root
S6:02 ⑨ [일반] ClearAll
S6:03 ⑨ [일반] Group 4 + 3
S6:04 ⑨ [일반] Attribute 'Dimmer' At 100
S6:05 ⑨ [일반] Step 2
S6:06 ⑨ [일반] Attribute 'Dimmer' At 0
S6:07 ⑨ [일반] Attribute 'Dimmer' At Phase 0 Thru 360
S6:08 ⑨ [일반] Attribute 'Dimmer' At Speed 60
S6:09 ⑨ [승인카드] Store Preset 22.97 'SCR FX MULTI' /Universal
S6:10 ⑨ [일반] Label Preset 22.97 'SCR FX MULTI'
S6:11 ⑨ [일반] ClearAll
```

**S7 — 4줄** `2afb6195bac8b4f8…` (ASSEMBLED (hand-made minimal programmer))

```text
S7:01 ⑫ [일반] ClearAll
S7:02 ⑫ [일반] Fixture 111 ; Attribute 'Dimmer' At 1
S7:03 ⑫ [승인카드] Store Preset 22.0
S7:04 ⑫ [일반] ClearAll
```

**S8 — 10줄** `3df715705f34a961…` (ASSEMBLED (color _build_bundle called twice, same number))

```text
S8:01 ⑪ [일반] ClearAll
S8:02 ⑪ [일반] Group 10 ; Attribute 'ColorRGB_R' At 100 ; Attribute 'ColorRGB_G' At 0 ; Attribute 'ColorRGB_B' At 50
S8:03 ⑪ [승인카드] Store Preset 4.352
S8:04 ⑪ [일반] Label Preset 4.352 'SCR DUP'
S8:05 ⑪ [일반] ClearAll
S8:06 ⑪ [일반] ClearAll
S8:07 ⑪ [일반] Group 10 ; Attribute 'ColorRGB_R' At 0 ; Attribute 'ColorRGB_G' At 100 ; Attribute 'ColorRGB_B' At 50
S8:08 ⑪ [승인카드] Store Preset 4.352
S8:09 ⑪ [일반] Label Preset 4.352 'SCR DUP'
S8:10 ⑪ [일반] ClearAll
```


대안 `alt-S7b.txt` (합본 제외, sha256 `09fe722b908227d59ced270aba7030ef9cdcbffbe01d29897b655be9c15c0e4b`):

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

## 7. 러너 `--dry-run`

모든 파일을 `uv run python -m server.tools.beatgrid_runner --dry-run --input <파일> --expect-sha256 <sha> --listen-port 9005` 로 검증했다(출력 전문은 `dry-run.txt`, `dry-run-<파일>`, 요약 `dry-run-summary.txt`).

| 파일 | 종료 코드 | 출력 첫 줄 | 출력 마지막 줄 | 파일 첫 줄 | 파일 마지막 줄 |
|---|---|---|---|---|---|
| `payload-all.txt` | 0 | `lines=165 sha256=77d670d7e537138e33e176ae4a409b470ee51baadfc8ec48a6199409df0596f1` | `165	ClearAll` | `Fixture 521 ; Attribute 'Pan' At -65.6 ; Attribute 'Tilt' At 41.6` | `ClearAll` |
| `cleanup-after-S1a.txt` | 0 | `lines=6 sha256=eb9b085e25dfc76cf4a8d4d094effa9c41a311d04d63ef33283efe88d5866873` | `6	ClearAll` | `ClearAll` | `ClearAll` |
| `cleanup-after-S1b.txt` | 0 | `lines=10 sha256=e0e3c2fdcaa1ca07bafc38e5247cd114e623f944e9efc7a38f1013b3ba207ec5` | `10	ClearAll` | `ClearAll` | `ClearAll` |
| `cleanup-after-S2.txt` | 0 | `lines=10 sha256=e0e3c2fdcaa1ca07bafc38e5247cd114e623f944e9efc7a38f1013b3ba207ec5` | `10	ClearAll` | `ClearAll` | `ClearAll` |
| `cleanup-after-S2s.txt` | 0 | `lines=10 sha256=e0e3c2fdcaa1ca07bafc38e5247cd114e623f944e9efc7a38f1013b3ba207ec5` | `10	ClearAll` | `ClearAll` | `ClearAll` |
| `cleanup-after-S3.txt` | 0 | `lines=10 sha256=e0e3c2fdcaa1ca07bafc38e5247cd114e623f944e9efc7a38f1013b3ba207ec5` | `10	ClearAll` | `ClearAll` | `ClearAll` |
| `cleanup-after-S4.txt` | 0 | `lines=10 sha256=e0e3c2fdcaa1ca07bafc38e5247cd114e623f944e9efc7a38f1013b3ba207ec5` | `10	ClearAll` | `ClearAll` | `ClearAll` |
| `cleanup-after-S5.txt` | 0 | `lines=10 sha256=e0e3c2fdcaa1ca07bafc38e5247cd114e623f944e9efc7a38f1013b3ba207ec5` | `10	ClearAll` | `ClearAll` | `ClearAll` |
| `cleanup-after-S5s.txt` | 0 | `lines=10 sha256=e0e3c2fdcaa1ca07bafc38e5247cd114e623f944e9efc7a38f1013b3ba207ec5` | `10	ClearAll` | `ClearAll` | `ClearAll` |
| `cleanup-after-S6.txt` | 0 | `lines=11 sha256=5e9a264e8e3dc12572f99eb409808a9ee44cf32f5631fdf759114275f36ad14c` | `11	ClearAll` | `ClearAll` | `ClearAll` |
| `cleanup-after-S7.txt` | 0 | `lines=11 sha256=5e9a264e8e3dc12572f99eb409808a9ee44cf32f5631fdf759114275f36ad14c` | `11	ClearAll` | `ClearAll` | `ClearAll` |
| `cleanup-after-S8.txt` | 0 | `lines=12 sha256=0ca31c7637d2602b38fa985fcb8c20533fa4c5f64071e6a4e35e022a81657bb2` | `12	ClearAll` | `ClearAll` | `ClearAll` |
| `cleanup-only-S6.txt` | 0 | `lines=3 sha256=03a5bc49979c0205625b74cc2f54481f710c9040716041fee3975c25bdeda224` | `3	ClearAll` | `ClearAll` | `ClearAll` |
| `cleanup-only-S8.txt` | 0 | `lines=3 sha256=aa36a0429fbb27ba522482374fc885c08f14aabef041178daf830589405bc58a` | `3	ClearAll` | `ClearAll` | `ClearAll` |
| `cleanup-22.0.txt` | 0 | `lines=3 sha256=01633bc0a2c0e341f4fe8c8ff398a8e575327ae3bcef3750a825a19ffb4408b9` | `3	ClearAll` | `ClearAll` | `ClearAll` |

## 8. 위험

1. **잔재**: v2 정리는 index 8 에서 멈췄고 그 앞(ClearAll, 프리셋 3, 타임코드 70, 시퀀스 702·703)은 `ok` 였다. 따라서 콘솔은 깨끗할 가능성이 높지만 읽어서 확인하지 않았다. 실행 전 `--probe` 로 700~703 · TC 70 · 프리셋 6개가 `empty` 인지 본다.
2. **점 꼴 배정은 이 구성에서 처음이다.** 선례 4건은 모두 `Set Timecode … Duration` 이 `Store … .1` 앞에 있었고 이번 줄에는 Duration 이 없다. 거절되면 S1b 는 첫 `Assign` 에서 멈추고 시퀀스는 일부만 만들어진 상태가 된다(§4-2).
3. **`Store Timecode 70.1` 이 S1a 에 들어갔다.** S1a 가 v2 와 달리 한 줄 길다. 이 줄이 거절되면 S1a 는 끝에서 멈추고 TC 70 은 있고 `.1` 은 없다. `cleanup-after-S1a` 로 정리된다.
4. 변하지 않은 위험: 새 어순 `Store Sequence S Cue N …`·`/Overwrite`·`CueFade`·`/CueOnly`·`Delete Cue` 는 실기 선례가 없다(v2 §0). `Go Timecode 70` 은 실제 재생이라 onPC 에 빛이 나간다. `Store Preset 22.0` 은 쇼의 진짜 프리셋에 닿을 수 있다.
5. **정리 파일은 「끝까지 간 단계」 가정**이다. 중간 정지에 파일을 그대로 보내면 v2 와 같은 `Illegal object` 로 멈춘다(§4-2).
6. S7 이후 S8 이 두 번째 `Store` 확인창을 띄우면 뒤 줄이 막힐 수 있어 S8 을 맨 끝에 뒀다(v2 와 동일).

## 9. 다시 만드는 법과 검증

```bash
cd <워크트리 루트>   # .claude/worktrees/t608-v3
uv run python <절대경로>/.moai/reports/t608/v3/gen_payload.py --repo . \
  --out <절대경로>/.moai/reports/t608/v3 --v2 <절대경로>/.moai/reports/t608/v2
uv run python <절대경로>/.moai/reports/t608/v3/cleanup_from_run.py \
  --run <절대경로>/.moai/reports/t608/v2/run-S1a.jsonl --run <절대경로>/.moai/reports/t608/v2/run-S1b.jsonl
```

## 10. Gaps — 측정하지 않았거나 생성하지 못한 것

- 콘솔 접촉 0: `ping`·`state`·`props`·`--probe` 도 보내지 않았다. 점유 번호, 응답기 버전, 그룹 소속, 장비 좌표·회전, 컬러 채널 이름(`ColorRGB_*` 가정), `Fixture 111` 의 존재를 모른다. 프리셋 풀 상태는 v2 와 같은 픽스처다.
- 점 꼴 배정·`Store Timecode 70.1` 의 실기 수용 여부는 미측정이다(선례는 Duration 포함 구성).
- 앱 세션을 돌리지 않았다: `ChatSession.beat_grid_apply` 를 호출하지 않고 같은 함수 사슬을 따라 호출했다. S1 sha256 은 `build_write_approval_batch` 가 낸 값이다.
- `Top`/`Go`/`Off Timecode` 는 코드를 읽고 적은 줄이다([읽음]). ⑨-b·⑪·⑫ 는 [조립]이다.
- v2 §4 의 선례 인용은 v2 에서 옮겼다. 이번에 그 파일들을 다시 열어 대조하지 않았다.
- 정리: 없는 객체에 대한 `Delete` 가 항상 `Illegal object` 인지는 v2 에서 한 번 관측했을 뿐이다. 큐가 참조하는 프리셋을 먼저 지우는 순서, `Delete Preset 22.0` 의 해석은 재지 않았다. `User Canceled Command` 처럼 효과가 불분명한 응답 뒤의 객체 존재는 파일로 판단할 수 없고 `--probe` 가 필요하다.
- 도우미 `cleanup_from_run.py` 는 v2 의 run 기록 두 개로만 돌려 봤다(콘솔 없이).
- `gen_payload.py` 와 이 폴더는 git 에 커밋하지 않았다.
