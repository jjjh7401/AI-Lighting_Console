# t225 — 미해결 프리셋 11종은 **전부 (a) 콘솔에 없다**

base `origin/main` `d4d6651` · 브랜치 `WT-preset-join` · 콘솔 쓰기 **0건**

## 한 줄

11종을 (a) 없다 / (b) 이름이 다르다 / (c) 조인이 그 종류를 안 본다 로 갈랐더니
**11/11 이 (a)** 였다. 조인 술어는 멀쩡하다 — **프리셋이 콘솔에 없다.**
그래서 여덟 큐 중 나가는 것은 **여전히 Q010 하나**이고, 툴이 계획하는 큐는
**0개**다(§11.1 부분집합 금지).

배차서가 준 유력한 단서 — 「Color 풀에 6종이 있으니 COL.02 는 (b) 나 (c) 다」 —
는 **반증됐다.** 풀에 있는 여섯은 COL.01·04·05·06·07·08 이고 COL.02 는 그
여섯에 없다.

## 참조별 판정 (11/11)

| ref | 갈래 | 증거 | 왜 없나 | 처분 |
|---|---|---|---|---|
| `COL.02` | **(a)** | `PresetPools/4` 6종에 「웜 화이트 (=P2)」 없음 | 값이 색온도 단독(`~3200K`) — `preset_parser.HOLD_NO_RGB_VALUE`, col 6/8 만 storable | 카드 |
| `BM.01` | **(a)** | `PresetPools/5` childCount **0** | bm **0/5** storable — `attribute_probe_rejected` / `family_out_of_scope` | 카드 |
| `BM.02` | **(a)** | 〃 | 〃 | 카드 |
| `BM.03` | **(a)** | 〃 | 〃 (`Prism` 부재 + `Gobo` 범위 밖, 사유 둘) | 카드 |
| `BM.04` | **(a)** | 〃 | 〃 (`Frost`) | 카드 |
| `FX.01` DIM-CHASE | **(a)** | `PresetPools/21` 에 DIM-PULSE·PT-CIRCLE 둘뿐 | **한 번도 안 쐈다.** 변환은 성립한다 | 카드(발사만 남음) |
| `FX.03` DIM-BREATHE | **(a)** | 〃 | 〃 | 카드(발사만 남음) |
| `FX.05` TILT-SWEEP | **(a)** | 〃 | 〃 | 카드(발사만 남음) |
| `FX.07` DIM-TWINKLE | **(a)** | 〃 | 〃 | 카드(발사만 남음) |
| `FX.04` COL-RAINBOW | **(a)** + 별건 | 〃 | `attribute 'Hue' 는 KNOWN_ATTRIBUTES 밖이다` | 카드(별건) |
| `FX.06` SHUTTER-STROBE | **(a)** + 별건 | 〃 | `attribute 'Shutter' 는 KNOWN_ATTRIBUTES 밖이다` | 카드(별건) |

**(b) 0건 · (c) 0건.** 조인 술어를 고칠 자리가 없다.

원인은 **셋**이지 하나가 아니다 — 처방이 서로 다르다:

1. **켈빈 모델 부재** (COL.02·COL.03) — 색온도를 RGB 로 옮기는 변환이 저장소에 없다.
2. **빔 어휘 거절** (BM 전 5행) — 라이브 프로브가 `Focus`·`Frost`·`Prism`·`Shutter`
   를 거절했고, `Gobo`·`Position` 등은 풀 계열 자체가 범위 밖이다.
   ⚠️ 여기에는 **지뢰**가 있다: bm 한 행이 저절로 storable 로 열리는 날
   `LXSEQ_PRESET_APPLY_ATTRIBUTE` 에 bm 칸이 없어 **그 bm 임포트가 통째로 0건**이
   된다(「4 보류 + 1 계획」이 아니라 0건). 소스 주석이 이미 그렇게 적어 뒀다.
3. **FX 미발사** (FX.01·03·05·07) — 능력은 있는데 **안 쐈다.**

### 3번 갈래는 「막혔다」가 아니라 「안 했다」 — 이것이 이 회차의 발견

`lxseq_fx_e2e --action preview` 를 **8종 전부**에 돌렸다(콘솔 쓰기 0):

    runnable 6 · skipped 2
    skipped: FX.04 (Hue), FX.06 (Shutter) — KNOWN_ATTRIBUTES 밖
    approval_requests: Store Preset 21.3 '<name>' /Universal  ← 6건 전부 조립됨
    baseline.channel_trustworthy: true (날조 경로 대조군 ok=false)

즉 FX.01·03·05·07 은 **번역도 되고 명령도 조립된다.** 콘솔에 없는 이유는
앞 회차가 `--only-ids` 로 두 종만 점검 발사했기 때문이다(그 플래그의 도움말
예시 문자열이 `'FX.02,FX.08'` 이고, 풀에 있는 것이 정확히 그 둘이다).

## 여덟 큐 중 몇 개가 나가나 — **1개, 안 바뀐다**

`map_cues` 를 실측 슬롯표로 오프라인 재현했다
(`evidence/replay_join.py`, 콘솔 접촉 0):

| 상태 | 미해결 | 전 행 해결된 큐(18중) | 여덟 중 | 툴이 계획하는 큐 |
|---|---|---|---|---|
| 지금 | 11종 | 5 (Q010·Q030·Q060·Q170·Q180) | **1** (Q010) | **0** |
| FX 4종을 채웠다면 | 7종 | 7 (+Q100·Q120) | **1** (Q010) | **0** |
| FX+BM+COL.02 를 다 채웠다면 | 2종 | 16 | **8** | **0** |

세 열이 서로 다른 것을 말한다. **「전 행 해결」과 「나간다」는 같지 않다** —
한 행이라도 보류되면 `refusal=rows_held` 로 **배치 전체**가 0건이다(§11.1).
그래서 마지막 행조차 계획 큐가 0 이다: FX.04·FX.06 이 참조되는 Q140·Q150 이
남기 때문이다.

**이 회차의 변경으로 나가는 큐 수는 0 → 0, 여덟 중 전 행 해결은 1 → 1 이다.**
줄어든 것은 미해결이 아니라 **다음 사람의 왕복**이다(아래).

재현이 남의 측정과 맞는지: t224 커밋 문면이 「여덟 큐 중 전 행이 해결된 것은
Q010 하나이고 실제로 계획된 큐는 0개」라고 적었다. 내 재현이 같은 두 수를 냈다.

## 고친 것 — 툴이 이 분류를 스스로 말하게 했다

이 판정을 내려고 콘솔 풀 **다섯 개**를 손으로 떴다. 그럴 필요가 있었던 이유가
코드에 문면으로 적혀 있다 — `cue_mapper._HOLD_BLOCK_CLASS[UNRESOLVED_PRESET]`:

> 「시트에 정의가 없는 것인지, 정의는 있는데 콘솔 슬롯 조인이 안 선 것인지
> **이 층에서는 안 갈린다**」

맞는 말인데, **툴 층은 갈릴 수 있다.** 시트(정의)와 콘솔 되읽기(조인)를 둘 다
쥔 자리는 `import_lxseq_cues` 하나다. 그래서 산출물에 칸 하나를 더했다:

`unresolved_preset_refs` — 참조별로 `ref` · `kind` · `cause` · `expected_console_name`.

`cause` 는 닫힌 클래스 넷이고 **처방이 서로 다르다**:

| cause | 뜻 | 처방 |
|---|---|---|
| `sheet_not_supplied` | 그 종류 시트를 호출이 안 실었다 | 인자를 고친다 |
| `sheet_lacks_id` | 시트는 있는데 그 ID 가 없다 | 시트를 고친다 |
| `console_lacks_name` | 시트가 준 이름이 콘솔 풀에 없다 | **프리셋을 만든다** |
| `pool_unreadable` | 풀을 못 읽었다 | 못 읽은 것을 「없다」로 접지 않는다 |

`expected_console_name` 이 하중을 진다: 그 이름을 들고 풀을 보면 (a) 없다와
(b) 이름이 다르다가 **한 번에** 갈린다. 이번 회차가 손으로 한 일이다.

**계획을 바꾸지 않는다** — 보류·거절·명령 조립 전부 그대로다. 산출물 한 칸이다.

## 검증

### 회귀

| | 통과 | 스킵 |
|---|---|---|
| `d4d6651` (자체 venv, 이 트리) | 10,796 | 12 |
| 이 브랜치 | **10,805** | 12 |

**+9 = 새로 넣은 검사 9개.** 지운 검사 0, 교체 0. 전량 설명된다.
(`uv sync --group dev` 로 이 트리 자체 venv 를 세우고 쟀다 — 규약 §1)

### 뮤테이션 — 6/6 사망

매 회차 `assert mutated != original` 대신 `diff -q` 로 「적용 안 됨」을 기계로
확인했고, 여섯 번 다 `differ` 를 받았다.

| # | 치환 | 죽은 검사 |
|---|---|---|
| M1 | `sheet_not_supplied` → `sheet_lacks_id` | `test_a_kind_with_no_sheet_supplied_says_so` |
| M2 | `expected` 를 항상 `None` 으로 | `test_a_defined_id_the_console_lacks_names_the_expected_label` |
| M3 | `text in preset_slots` 가드 제거 | `test_a_resolved_ref_is_absent_from_the_table` |
| M4 | `pool_unreadable` 조건 반전 | POS 두 검사 |
| M5 | 참조 문법 가드(`found is None`) 제거 | 8개 전부 |
| M6 | `is_video_call` 스킵 제거 | `test_a_video_call_rows_preset_ref_is_not_counted` |

M6 은 **검사를 먼저 만들고 나서** 걸었다. 그 팔이 없었을 때 이 가드는 코퍼스에
안 걸려 지워도 아무도 몰랐다(규약 §3.5).

### 대조군 두 팔

- **팔 1 — 새 검사가 잡는가**: 위 뮤테이션 6/6.
- **팔 2 — 기존 상태에서는 못 잡는가**: 검사 파일을 그대로 두고 소스 둘만
  `git checkout` 으로 되돌려 돌렸다 →
  `ImportError: cannot import name 'UNRESOLVED_CONSOLE_LACKS_NAME'`, 수집 단계 실패.
  이 브랜치 없이는 이 계약이 **존재하지 않는다.**

## 안 잰 것 (Gaps)

- **콘솔에 아무것도 안 썼다.** FX.01·03·05·07 을 쏘려던 참에 **응답기가 죽었다.**
  판독 7건 + preview 1건까지 정상이었고, 그 직후부터 네 번 연속 무회신이다.
  onPC 는 재시작하지 않았다(배차서 [HARD]). 그래서 이 넷은 **여전히 콘솔에 없다.**
- **침묵의 원인은 안 쟀다.** 직전에 돈 것이 `Patch/Stages/1/Fixtures` 를 밟는
  하네스라 배차서가 경고한 상관과 같은 형태이지만, **대조군이 없다** — 그 경로만
  단독으로 쏘는 대조를 돌리려면 응답기가 살아 있어야 한다. 상관이고, 원인이 아니다.
  (같은 상관의 **두 번째** 관측이라는 사실만 기록한다.)
- **`console_lacks_name` 이 (a) 와 (b) 를 코드로는 안 가른다.** `expected_console_name`
  을 실어 사람이 한 번에 가르게 할 뿐이다. 기계로 가르려면 풀 이름 전량을
  산출물에 실어야 하는데, 그건 이 칸의 목적이 아니다.
- **COL.03 은 이 큐시트가 참조하지 않아** 표에 없다. 원인은 COL.02 와 같다.
- **`--timeout-seconds` 플래그가 안 먹는다**(선언 6.0, 실제 5.0). 고치지 않았다 —
  콘솔이 죽어 고쳐도 검증할 수 없다.
- **새 칸이 `apply` 경로에서 실기로 나오는 것은 못 봤다.** 자동 검사 9개는
  `preview` 를 돈다. `apply` 경로는 이 칸을 안 건드리지만(페이로드 조립은 한 자리),
  실기 확인은 응답기가 돌아온 뒤다.

## 다음 카드 후보

1. **FX 4종 발사** — FX.01·03·05·07. 능력은 확인됐고 발사만 남았다.
   `lxseq_fx_e2e --action apply --approve --only-ids FX.01,FX.03,FX.05,FX.07 --group 13`.
   chase·sweep 패턴은 **실기 초행**이다.
2. **BM 5행 어휘** — 지뢰(위 2번) 때문에 「한 행만 열기」가 위험하다. 어휘와
   `LXSEQ_PRESET_APPLY_ATTRIBUTE` 의 bm 칸을 **같은 카드에서** 다뤄야 한다.
3. **켈빈 → RGB** — COL.02·COL.03.
4. **FX.04(Hue)·FX.06(Shutter)** — `KNOWN_ATTRIBUTES` 확장. Q140·Q150 이 여기 걸린다.
5. **응답기 침묵** — Fixtures 상관에 대조군을 붙인다.
