# t227 — FX 넷을 쐈다. 계획되는 큐가 **0 → 7**, 예측과 일치한다

base `origin/main` `61d48ff` · 브랜치 `WT-fx-fire` · 코드 변경 **0** · 콘솔 쓰기 **48커맨드**(FX 풀 21 한 곳)

## 한 줄

t225 가 「능력은 있는데 안 쐈다」로 남긴 `FX.01·FX.03·FX.05·FX.07` 을 발사했다.
넷 다 콘솔에 앉았고(21.3~21.6), 되읽기가 이름까지 확인했다. 그 결과
미해결 참조가 **11 → 7**, 전 행 해결되는 큐가 **5 → 7**, 그리고 새 시퀀스에
대고 재현한 계획 큐가 **7** 이다 — t225·t228 의 두 독립 예측과 **같은 수, 같은 신원**.

## 풀 인구조사 — 전/후

계기: `python -m server.tools.t95_state_dump --path <경로> --listen-port 9005`
(단발 `query_state`, 읽기 전용)

### 전 (`evidence/pool21_before.json`)

    DataPool/PresetPools/21  name "All 1"  childCount 2
      21.1  DIM-PULSE     (= FX.02)
      21.2  PT-CIRCLE     (= FX.08)

배차서가 「FX.02 / FX.08 둘이 이미 있다고 가정하지 말고 확인하라」 한 대목 —
**확인됐다.** 점유는 그 둘이고 슬롯은 1·2, 다음 빈자리가 3 이다.

### 후 (`evidence/pool21_after.json`)

    DataPool/PresetPools/21  name "All 1"  childCount 6
      21.1  DIM-PULSE
      21.2  PT-CIRCLE
      21.3  DIM-CHASE     <- 이번에 올림 (FX.01)
      21.4  DIM-BREATHE   <- 이번에 올림 (FX.03)
      21.5  TILT-SWEEP    <- 이번에 올림 (FX.05)
      21.6  DIM-TWINKLE   <- 이번에 올림 (FX.07)

**이름을 읽었다.** 개수만이 아니다 — 넷 다 시트 `Name` 열과 바이트 일치한다.

### 거짓 0 대조군 (형제 풀)

`childCount 0` 을 「비었다」로 읽기 전의 대조군. 같은 회차, 같은 채널:

| 경로 | childCount | 판정 |
|---|---|---|
| `DataPool/PresetPools/2` (Position) | **6** — POS01~POS06 이름까지 옴 | 채널이 0 을 남발하지 않는다 |
| `DataPool/ZZZNoSuchPoolXYZ` (날조) | `introspect failed: path segment not found` | 없는 것은 없다고 답한다 |
| `Patch/FixtureTypesZZZNotAThing/9999` (하네스 내장 날조) | `ok: false` | 〃 |
| `DataPool/Groups` | 18 — ALL~EVEN 이름까지 | 양성 팔 |

즉 이 회차의 어떤 숫자도 「못 읽어서 0」이 아니다. 하네스 자신도
`baseline.channel_trustworthy: true` 로 같은 판정을 냈다(날조 not-ok AND 실경로 ok).

## 자체 preview — t225 가 재현되나

먼저 **preview** 를 넷에만 돌렸다(콘솔 쓰기 0, `--approve` 없음):

    python -m server.tools.lxseq_fx_e2e \
      --fx-csv .../LXSEQ_RIG_01_ShowBase_r3.fx.csv \
      --action preview --group 13 \
      --only-ids FX.01,FX.03,FX.05,FX.07 --listen-port 9005 \
      --out .moai/reports/t227/evidence/fx_preview.json

    runnable_count 4 · skipped_count 0
    approval_requests: Store Preset 21.3 'DIM-CHASE'   /Universal
                       Store Preset 21.3 'DIM-BREATHE' /Universal
                       Store Preset 21.3 'TILT-SWEEP'  /Universal
                       Store Preset 21.3 'DIM-TWINKLE' /Universal

**t225 와 같다** — 넷 다 `Store Preset 21.3 '<name>' /Universal` 까지 조립된다.
어긋난 것이 없어 멈출 이유가 없었다.

네 결과 모두 `is_error: true` 였고, 그 사유를 문자열로 단언했다(규약 §3.2):
`gate_status: "rejected"` · `"bundle rejected by the approver — nothing was executed"`
· 커맨드별 `bundle rejected (all-or-nothing, REQ-MVP-015)`. 즉 **번역 실패가 아니라
설계된 승인 거절**이다. 두 거절 갈래를 사유로 갈랐다.

⚠️ 넷이 전부 `21.3` 을 겨눈 것은 preview 라 아무것도 안 써서 빈자리가 안 움직였기
때문이다. 발사 전에 이것이 **덮어쓰기 위험**인지 코드로 확인했다:
`tools.py::_fx_preset_destination` 이 매 `compose_fx` 디스패치마다 풀을
`query_state` + `paged_children` 로 **다시 재고** `select_preset_number` 로 빈자리를
고른다. 그래서 apply 에서는 3·4·5·6 으로 갈린다 — 그리고 실제로 그렇게 갈렸다.

## 발사 — 보낸 커맨드 (verbatim)

    python -m server.tools.lxseq_fx_e2e \
      --fx-csv .../LXSEQ_RIG_01_ShowBase_r3.fx.csv \
      --action apply --approve --group 13 \
      --only-ids FX.01,FX.03,FX.05,FX.07 --listen-port 9005 \
      --out .moai/reports/t227/evidence/fx_apply.json

그룹 13 은 이 쇼에서 `MOVER-ALL` 이다(같은 회차 `DataPool/Groups` 실측, childCount 18).
t225 의 처방 그대로다.

번들 넷, 커맨드 48개, **전부 `executed_ok`** (전문: `evidence/apply_commands.txt`):

    -- FX.01 DIM-CHASE
       ChangeDestination Root / ClearAll / Group 13
       Attribute 'Dimmer' At 100 / Step 2 / Attribute 'Dimmer' At 0
       Attribute 'Dimmer' At Phase 0 Thru 360
       Attribute 'Dimmer' At Width 50
       Attribute 'Dimmer' At Speed 240
       Store Preset 21.3 'DIM-CHASE' /Universal
       Label Preset 21.3 'DIM-CHASE'
       ClearAll
    -- FX.03 DIM-BREATHE   (같은 형태, Dimmer 100/40 · Speed 30 · Width 없음 · 21.4)
    -- FX.05 TILT-SWEEP    (같은 형태, Tilt -25/25 · Speed 30 · 21.5)
    -- FX.07 DIM-TWINKLE   (같은 형태, Dimmer 100/30 · Speed 30 · Phase 없음 · 21.6)

`Label` 이 별도 행인 이유는 저장소가 이미 알고 있다 — `Store Preset` 인라인
`'<label>'` 은 `ok` 를 받지만 풀 라벨로 안 붙는다(2026-08-16 실기).
이번 되읽기가 이름을 답한 것이 그 우회가 사는 증거다.

**`ok` 를 증거로 쓰지 않았다.** 판정은 위 되읽기(이름 4개)다.

### 범위

썼는 것은 `DataPool/PresetPools/21` 한 곳뿐이다. 검산:

| 경로 | 전 | 후 |
|---|---|---|
| `PresetPools/21` (FX, 대상) | 2 | **6** |
| `PresetPools/2` (POS, 범위 밖) | 6 | 6 |
| `DataPool/Sequences` | 6 | 6 |

`ClearAll` 은 프로그래머를 비우는 것이고 저장 데이터가 아니다.
큐 적용·시퀀스 생성은 하지 않았다.

## 결과 — 큐 몇 개가 계획되나

계기: `server/tools/lxseq_cues_e2e.py --action preview --limit 0`
(`--approve` 없음 → `approval_requests` 0건, 콘솔 쓰기 0)
정본 CUE-EX CSV + 정본 xlsx + DIM·COL·BM·FX 시트 전량.

### 판독 1 — 정본 시퀀스 `Sugar r3` 에 대고

    preset_slots_resolved  24   (t225 재현표의 20 에서 +4 — 이번에 올린 넷)
    unresolved_preset_refs  7   (11 에서 -4)
    cues_held_count        11   -> 전 행 해결되는 큐 18-11 = 7
    planned_cues           []   · already_present true

미해결 잔여 **7건, FX 넷은 사라졌다**:

| ref | cause | 기대 콘솔 이름 |
|---|---|---|
| `BM.01` | `console_lacks_name` | 와이드 워시 |
| `BM.02` | 〃 | 미드 빔 |
| `BM.03` | 〃 | 좁은 빔 + 프리즘 |
| `BM.04` | 〃 | 소프트 프로스트 |
| `COL.02` | 〃 | 웜 화이트 (=P2) |
| `FX.04` | 〃 | COL-RAINBOW |
| `FX.06` | 〃 | SHUTTER-STROBE |

`FX.01·03·05·07` 이 이 표에서 **빠졌다** — 조인이 실제로 섰다.
정확히 t225 가 남긴 잔여(BM 4 + COL.02 + Hue/Shutter 별건 2)다.

🔴 이 판독의 `planned_cues` 가 `[]` 인 것은 조인 때문이 **아니다**.
`already_present: true` — 18큐가 이미 `Sugar r3` 에 다 들어 있어(t209) 멱등층이
먼저 끊었다. 이 값을 「아직 0개다」로 읽으면 오독이다.

### 판독 2 — 멱등층을 비켜서 (계획 수를 직접 잰다)

같은 명령, `--sequence-name` 만 콘솔에 없는 이름으로:

    --sequence-name 'T227 PREVIEW ONLY NOT WRITTEN'

    already_present        false
    cue_bundles_planned    7
    planned_cues           Q010(3행) Q030(2) Q060(3) Q100(3) Q120(4) Q170(6) Q180(1)
    planned_row_count      22
    cues_held_count        11
    partial_ship           true
    refusal                null
    approval_requests      0건   <- 콘솔에 아무것도 안 갔다

발사 후 `DataPool/Sequences` 를 다시 읽어 childCount 6 · 같은 여섯 이름을
확인했다. 산출물의 `sequence_no: 5` 는 **쓰였다면 갈 자리**이고, 안 쓰였다.

### 예측 대조 — **맞다, 7 이다**

| 출처 | 예측 | 근거 |
|---|---|---|
| t225 (오프라인 재현, 반사실 A) | 전 행 해결 큐 **7** (+Q100·Q120) | `evidence/replay_join.json` |
| t228 (같은 재현, 입도 변경 후) | 계획되는 큐 **7** | `evidence/replay_join_after.json` |
| **t227 (실기, 콘솔 슬롯 실측 조인)** | **7** — Q010·Q030·Q060·Q100·Q120·Q170·Q180 | 위 판독 2 |

**수도 신원도 같다.** 두 예측이 하드코딩 슬롯표(`FX.01→3 · FX.03→4 · FX.05→5 ·
FX.07→6`)를 전제로 했고, 발사 결과가 **그 전제와 바이트 일치**했다 — 예측이
맞은 것은 우연이 아니라 슬롯 배정까지 같았기 때문이다.

t225 와 어긋난 것은 **없다.** 어긋날 뻔한 자리 하나는 위의 `planned_cues: []`
인데, 그것은 t225 의 예측이 아니라 t228 이 새로 넣은 멱등층 신호다.

## 코드 변경 0 — 그래서 회귀도 안 돌렸다

`git status --short` 가 빈 출력이다(추적 파일 변경 0). 이 카드는 실행 카드고,
남는 것은 보고서와 증거뿐이다. **회귀 회계를 적지 않는다** — 이 트리에서 기준을
재지 않았고, 남의 값을 옮겨 오지도 않는다.

하네스도 고치지 않았다. 즉 위 숫자는 정본 도구가 낸 값이다.

## 안 잰 것 (Gaps)

- **효과가 맞게 도는지 안 봤다.** 되읽기는 프리셋의 **이름**까지만 답한다.
  chase·sweep 패턴은 실기 초행이고, 파형·속도·폭이 무대에서 의도대로 도는지는
  기계로 확인할 수단이 이 채널에 없다 — 하네스 docstring 이 스스로 그렇게 적어 뒀다.
  `Width 50` 이 FX.01 에만 붙고 `Phase` 가 FX.07 에 안 붙은 것도 문면대로 보냈을
  뿐 콘솔이 어떻게 해석했는지는 안 잰다. **GUI 확인은 감독 몫으로 남는다.**
- **`Patch/Stages/1/Fixtures` 를 안 밟지는 못했다.** 정본 하네스가 신뢰성 기준으로
  그 경로를 **컨테이너 단발 `query_state` 로 한 번** 읽는다(`child_count: 86`,
  `children_in_reply: 19`, `truncated: true` — 자식을 걷지는 않는다).
  카드가 금한 「walk」는 아니라고 판단해 하네스를 고치지 않고 그대로 돌렸다.
  응답기는 전 과정에서 한 번도 침묵하지 않았다 — 발사 전 preview 1회, 발사 1회,
  발사 후 판독 5회. **t220·t225 의 상관에 대한 반례 1건이지만 대조군이 아니다**
  (그 두 회차와 하네스·경로·순서가 같지 않다). 원인은 여전히 미확정.
- **`--group 13` 이 연출상 맞는 그룹인지 안 따졌다.** t225 의 처방을 그대로 썼다.
  `MOVER-ALL` 에 Dimmer 체이스를 올리는 것이 시트 의도인지는 시트가 말하지 않는다.
- **판독 2 의 7 이 `apply` 에서도 7 인지는 안 봤다.** preview 층과 apply 층은
  페이로드 조립이 한 자리지만, 실기 확인은 감독이 큐 적용을 결정한 뒤다.
  큐 적용은 이 카드의 범위 밖이다(리드 판정).
- **`already_present` 경로의 재실행 의미를 안 캤다.** `Sugar r3` 는 18큐가 이미
  들어 있어 이 회차의 FX 넷이 **기존 큐 내용을 바꾸지는 않는다.** 이미 들어간
  큐들이 FX 참조를 들고 있는지, 아니면 그때 held 로 빠진 채 들어갔는지는
  되읽기 채널이 큐 **내용**을 안 주므로(`AC-LXSEQ4-013`) 잴 수 없다.
  🔴 **이것이 다음 사람이 가장 먼저 물어야 할 것이다** — 「7개가 계획된다」는
  새 시퀀스에 대한 값이고, 정본 시퀀스는 이미 뭔가를 들고 있다.
- **`--timeout-seconds` 가 여전히 안 먹는다**(t225 관측). 고치지 않았다.
- **컨텍스트**: `.moai/state/context-usage.json` 의 `session_id`
  `39e0308c-…`(writer_pid 80905, 15:09 캡처)가 **내 세션이 아니다** — 규약 §9 대로
  `raw_pct` 를 버리고 카드 수 축으로 답한다: **이 세션의 첫 카드**다.

## 다음 카드 후보 (t225 목록의 잔여)

1. **BM 5행 어휘** — 지뢰(`LXSEQ_PRESET_APPLY_ATTRIBUTE` 의 bm 칸 부재) 때문에
   어휘와 같은 카드에서 다뤄야 한다. 별건 카드 t229 로 이미 나갔다.
2. **켈빈 → RGB** — COL.02. 잔여 7건 중 1건.
3. **`FX.04`(Hue) · `FX.06`(Shutter)** — `KNOWN_ATTRIBUTES` 확장. 이 둘이 열리면
   Q140·Q150 이 풀리고 전 행 해결이 16 이 된다.
4. **정본 시퀀스 `Sugar r3` 의 기존 18큐가 무엇을 들고 있나** — 위 Gap.
5. **응답기 침묵** — 이 회차가 반례 1건을 냈다. 대조군을 붙이면 갈릴 수 있다.
