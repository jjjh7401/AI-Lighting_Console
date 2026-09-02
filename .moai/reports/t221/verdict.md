> ⚠️ **만료 고지 (2026-09-01 22:2x, 재측정 회차).** 이 문서의 측정은 **콘솔 86대가
> 전부 `(0,0,0)` 이던 시점**의 것이다. 여기 적힌 §8 판정과 초과 각도(POS.03 +45.0°)는
> 그 상태의 기록으로 그대로 유효하고, 숫자는 하나도 고치지 않았다.
> 다만 **처방 1(좌표 투입)은 t224 가, 처방 2(퇴화 거절)는 t222 가 이미 이행했고
> 둘 다 `origin/main` 에 있다.** 그래서 「POS.02·03·04 불가」는 **현재 상태가 아니다** —
> 지금 같은 경로가 6/6 을 산출한다. 현재 상태와 큐 개폐 재측정은 **`verdict-recheck.md`** 를 봐라.

# t221 — POS 3행이 「불가」인 진짜 이유

기준: 브랜치 `WT-pos-reach` (base `origin/WT-pos-join` `7f16e6b`) · 2026-09-01 ·
콘솔 LIVE(onPC 2.4.2, PID 3669, 13:01 기동) · **콘솔 쓰기 0건**

## 0. 한 줄

(A) 물리적 도달 불가도 (B) 규칙이 잡은 점의 문제도 아니다.
**리그 좌표 86대가 전부 (0,0,0) 이다.** 규칙은 퇴화한 입력을 받았을 뿐이고,
그래서 세 행이 죽고 **나머지 세 행이 거짓 초록으로 살았다** — 이쪽이 더 위험하다.

## 1. 계기 확인부터 (「없다」를 쓰기 전에)

명령: `.venv/bin/python tools/console_probe.py --listen-port 9005 <step>`

| 팔 | 질의 | 답 |
|---|---|---|
| 양성 | `prop:Patch/Stages/1/Fixtures/1｜FID` | `ok=true value="101"` |
| 양성 | `prop:Patch/Stages/1/Fixtures/1｜Name` | `ok=true value="KEY 101"` |
| 음성 | `prop:Patch/Stages/1/Fixtures/1｜ZZZNotAProperty` | `ok=false property not readable` |
| 측정 | `prop:Patch/Stages/1/Fixtures/1｜Posx / Posy / Posz` | `ok=true value="0.0"` ×3 |

즉 **판독기가 눈먼 게 아니다.** 같은 경로·같은 노드에서 FID·Name 은 실값이 나오고
없는 프로퍼티는 거절된다. `Pos*` 만 `0.0` 이다.

표본을 넓혔다(같은 명령, 슬롯만 교체):

    Fixtures/15  BLIND 601   Posx 0.0  Posz 0.0
    Fixtures/50  BACK 208    Posx 0.0  Posz 0.0
    Fixtures/86  WASH-D 430  Posx 0.0  Posz 0.0

그리고 `get_spatial_context` 원문(`evidence/spatial_raw.json`)이 **스스로 말한다**:

    coverage : judged 86 · of 86 · complete true
    analysis : vertical_span 0.0 · row_count 1
               low_confidence true · confidence_reason "no_spatial_spread"

**86대 완독 · 전부 원점.** 「좌표 판독 86대 ✓」는 86대를 읽었다는 뜻이지
86대가 자기 자리에 있다는 뜻이 아니었다.

## 2. 리드 실측 재현

    .venv/bin/python server/tools/lxseq_pos_e2e.py \
      --pos-csv   src/Lighting_Designer/02_RIG팩/LXSEQ_RIG_01_ShowBase_r3.preset-pos.csv \
      --patch-csv src/Lighting_Designer/02_RIG팩/LXSEQ_RIG_01_ShowBase_r3.patch.csv \
      --group-csv src/Lighting_Designer/02_RIG팩/LXSEQ_RIG_01_ShowBase_r3.group.csv \
      --listen-port 9005 --action preview --limit 0 \
      --out .moai/reports/t221/evidence/preview.json

exit 0 · 좌표 86 · 채널 신뢰 true · 산출 3(POS.01·05·06) · 불가 3(POS.02·03·04).
리드 결과와 **행 단위로 일치**.

## 3. 행별 숫자

프로브 `evidence/t221_reach_probe.py` -> `evidence/reach.json`.

무대 기준틀 실측값: `cx=0.0 cy=0.0 min_x=0.0 max_x=0.0`,
`vocal_point=(0.0, -2.0, 1.6)`, 리그 x·y·z 범위 전부 `[0.0, 0.0]`, tilt 상한 `135.0°`.

| ID | 규칙 | 산출 목표점 | 대상 위치 | 필요 tilt | 초과 | 실제 사유 |
|---|---|---|---|---|---|---|
| POS.02 | `spread_floor` | (0, 0, 0) ×8 | (0,0,0) | 미정의 | — | **거리 0.0 m — 목표점이 장비 자신** |
| POS.03 | `silhouette_line` | (0, 0, 1.6) ×12 | (0,0,0) | **180.0°** | **+45.0°** | 수직 상방 — 천장 직사 |
| POS.04 | `floor_inside` | (0, 0, 0) ×8 | (0,0,0) | 미정의 | — | **거리 0.0 m — 목표점이 장비 자신** |
| POS.01 | `focus_vocal` | (0, −2, 1.6) ×6 | (0,0,0) | 128.66° | −6.34° | 통과(무의미) |
| POS.06 | `focus_vocal` | (0, −2, 1.6) ×18 | (0,0,0) | 128.66° | −6.34° | 통과(무의미) |
| POS.05 | `fan_out` | 좌표 미사용 | (0,0,0) | 45° 고정 | — | 통과(무의미) |

`file:line` — 목표점을 만드는 자리는 전부 `server/lxseq/position_derive.py` 의
`_aims_for` 안이다: `spread_floor` 396-409 · `focus_vocal` 410-411 ·
`silhouette_line` 412-415 · `floor_inside` 416-417.
무대 기준틀은 `position_derive.py:294-306`.
거절은 `server/spatial/pointing.py:103-134` — `length < 1e-9` 는 122행,
`tilt > 135` 은 124-127행. 상한 `POINTING_TILT_LIMIT_DEGREES = 135.0` 은 75행.

### 리드가 짚은 결정적 단서의 답

POS.03(BACK 12대)이 죽고 POS.06(KEY+BACK 18대)이 사는 이유는 **목표점 벡터 하나**다.
좌표가 전부 원점이라 두 규칙의 차이가 목표점으로만 남았다:

- POS.06 `focus_vocal` -> v = (0, −2, +1.6) -> tilt = acos(1.6/2.561) = **128.66°** -> 통과
- POS.03 `silhouette_line` -> v = (0, 0, +1.6) -> 순수 상방 -> tilt = **180.0°** -> 거절

같은 장비가 한 행에서 조준되고 다른 행에서 안 되는 것은 물리도 규칙 결함도 아니고,
**두 규칙이 퇴화한 입력에서 서로 다른 각도로 무너진 것**이다.

## 4. Pan/Tilt 가동범위의 출처 — 이것 자체가 발견이다

`POINTING_TILT_LIMIT_DEGREES = 135.0` 은 **패치의 픽스처 타입에서 오지 않는다.**
모듈 상수 하나이고, 주석이 근거를 「측정 리그의 헤드(Robe LEDBeam 350 / MMX)가
물리적으로 최대 ±135° 정도」라고 적는다(`pointing.py:69-75`).

- 이 쇼의 실제 기종은 MegaPointe · Spiider · MAC Aura XB · Atomic 3000 등이다
  (`rig_data.py` RIG_NOTES r2/r3). **다른 기종에 다른 리그의 상수를 쓰고 있다.**
- **Pan 범위는 아예 검사되지 않는다.** `aim_pan_tilt` 는 pan 을 (−180, 180] 로 접기만
  하고 상한 검사가 없다 — 물리 pan 한계를 넘는 값도 조용히 통과한다.
- 기종별 가동범위 표는 저장소에 없다.

**결론: 「조준 한계」는 실측이 아니라 가정이다.** 이 카드의 세 행이 죽은 원인은
아니지만(원인은 좌표), 좌표가 채워진 뒤 무엇이 「도달 불가」인지 판정할 때
이 상수가 그 판정의 유일한 근거가 된다.

## 5. 무대 의미 대조 (규칙 자체는 그럴듯하다)

좌표만 실값이라면 세 규칙의 목표점은 시트 문장과 어긋나지 않는다:

| 시트 문장 | 규칙이 잡는 점 | 판정 |
|---|---|---|
| POS.02 밴드 라인 포함 균일 커버 · 겹침 30% | 리그 x 폭을 등분한 착지점을 y=cy · z=0 에 **한 줄로** | 면이 아니라 **선**이다 — 잠재적 (C) |
| POS.03 실루엣 각 · 객석 눈부심 금지 | 각 장비 x · y=cy · z=1.6 (착지점이 무대 위) | 문장과 맞음 |
| POS.04 빔 무대 바닥 안쪽 · 상승 시작점 | 각 장비 x · y=cy · z=0 | 문장과 맞음 |

POS.02 의 (C) 는 **지금 잴 수 없다.** 좌표가 전부 0 이라 등분 결과가 한 점으로
접히는데, 그 접힘의 원인이 규칙인지 입력인지 이 데이터로는 안 갈린다.
좌표가 채워진 뒤 다시 재야 한다. (t220 이 이미 「겹침 30% 는 Zoom 없이 못 푼다」로
gap 을 적어 뒀다.)

## 6. 🔴 더 위험한 쪽 — 살아남은 세 행이 거짓 초록이다

`--action apply --approve` 였다면 콘솔에 이 명령이 나갔다
(`evidence/preview.json` 의 `bundles`, 쓰기는 안 했다):

    Fixture 101 ; Attribute 'Pan' At 180 ; Attribute 'Tilt' At 128.7
    Fixture 102 ; Attribute 'Pan' At 180 ; Attribute 'Tilt' At 128.7
    …(101~106 전원 동일)
    Store Preset 2.1
    Label Preset 2.1 'POS.01 보컬 센터 페이스 · 산출값'

**전원이 한 값이다.** POS.06(18대)도 같다. POS.05 의 부채꼴(150°·154°·158°…)은
좌표를 안 쓰는 `fan_pan_tilt` 가 만든 것이고, 체인 순서는
`fan_chain`(`pointing.py:495-514`)이 span 0 에서 x축·FID 타이브레이크로 떨어뜨린
**FID 순서**다 — 배치가 아니라 번호다.

세 프리셋이 콘솔에 올라가고 라벨은 「· 산출값」을 달아 **사람에게 출발점으로 읽힌다.**
저장소 규범(「날조보다 결손이 낫다」)에 정면으로 어긋난다.

퇴화 신호는 이미 응답에 있는데 아무도 안 읽는다:

    grep -c "low_confidence\|no_spatial_spread\|coverage" server/lxseq/position_derive.py   -> 0
    grep -n  "low_confidence\|analysis"                   server/tools/lxseq_pos_e2e.py     -> (출력 없음)
    (계기 대조) grep -c "get_spatial_context" server/tools/lxseq_pos_e2e.py                 -> 3

셋째 줄이 양성 대조군이다 — grep 이 이 파일에서 실제로 무언가를 찾는다는 증거.

## 7. 사유 문자열이 두 원인을 접는다 (부수 결함)

세 행 모두 `unaimable` · 「대상 N대 전부 조준 한계 밖 **또는 계산 불가**」로 나온다
(`position_derive.py:352-361`). 실제 원인은 둘로 갈린다:

- POS.03 = tilt 180° > 135° (한계 밖)
- POS.02 · POS.04 = 목표점이 장비 자신 (거리 0 — 계산 불가)

서로 다른 원인이 **바이트 동일한 사유**를 낸다. 리드가 이 문자열만 보고
「물리적 도달 불가인가」를 물은 것이 그 증거다 — 사유가 판정을 못 도왔다.

## 8. 판정

| 행 | 판정 | 숫자 |
|---|---|---|
| POS.02 | **판독 불가 — 전제 미충족(퇴화 입력)** | 목표점 = 장비 자신, 거리 0.0 m. tilt 미정의 |
| POS.03 | **판독 불가 — 전제 미충족(퇴화 입력)** | tilt 180.0° vs 상한 135.0° -> **+45.0°**. 단 이 값은 좌표 0 이 만든 것 |
| POS.04 | **판독 불가 — 전제 미충족(퇴화 입력)** | 목표점 = 장비 자신, 거리 0.0 m. tilt 미정의 |

(A) 도 (B) 도 (C) 도 아니다. 세 행 다 같은 뿌리이고, 좌표가 채워지기 전에는
(A)/(B)/(C) 어느 것도 **원리적으로 판정할 수 없다.**

## 9. 고칠 수 있나 · 어떤 큐가 열리나

큐 대조(`evidence/cue_map.py`, 정본 `LXSEQ_SAMPLE_01_Sugar_r3.cue-ex.csv` 89행):

    Q010 BACK    POS.03        Q020 KEY     POS.01
    Q040 MOVER-U POS.04        Q110 KEY     POS.06 · BACK POS.06
    Q050 MOVER-U POS.05 · MOVER-D POS.02
    Q080 MOVER-U POS.04
    Q090 MOVER-U POS.05 · MOVER-D POS.02
    Q130 MOVER-U POS.05 · MOVER-D POS.02

실패 POS 를 무는 큐 **6개**(Q010 Q040 Q050 Q080 Q090 Q130) / 시트 전체 18큐.
리드가 말한 「여섯 큐」와 일치한다.

### 처방 1 — 진짜 수리 (이 카드 범위 밖, 감독 결정)

콘솔에 실제 리그 좌표를 넣어야 한다. **저장소에는 그 값이 없다.**
패치 시트의 `Position` 열은 「FOH 브리지」 같은 산문이고 미터값이 아니다
(열: FID,Group,FixtureType,Mode,Ch,Universe,Address,AddrRange,Position).
쓰기 수단은 이미 있다 — `arrange_fixtures` 가 `Posx/Posy/Posz` 를 쓴다
(`tools.py:1455` `ARRANGE_AXES`). **막힌 것은 능력이 아니라 데이터다.**
`rig_data.py` RIG_NOTES 의 「POS.01~08 포지션 프리셋 전부 현장 레코드 필요 · 미해결」이
여전히 이 카드의 답이다.

### 처방 2 — 지금 당장의 안전 수리 (작지만 **미구현**)

`derive_position_presets` 가 퇴화한 리그를 거절해야 한다. 현재는 3행을 거짓 초록으로
내보낸다. 최소 형태:

- 기준틀 계산 직후 x·y·z 전 축의 span 이 0 이면(또는 응답의 `analysis.low_confidence` /
  `confidence_reason` 이 `no_spatial_spread`) **전 행을 `degenerate_rig` 사유로
  건너뛴다.** 하네스는 `_coordinates`(`lxseq_pos_e2e.py:96-134`)에서 절단만 보고
  퇴화는 안 본다.
- 겸사겸사 `unaimable` 을 `unaimable` / `target_coincides` 두 사유로 가른다(§7).

**이 카드에서 구현하지 않았다.** 이유 둘: ① 지금 초록인 3행이 빨강으로 바뀌므로
범위를 넓히는 변경이고 규약 §6 상 리드에게 먼저 알려야 한다. ② 퇴화 판정 술어를
「span 0」로 잡을지 「도구의 low_confidence」로 잡을지가 선택지이고, 후자는
`get_spatial_context` 의 응답 계약에 새로 의존한다.

처방 2 는 **큐를 열지 않는다** — 여섯 큐를 여는 것은 처방 1 뿐이다.
처방 2 가 여는 것은 「모르는 것을 모른다고 말하는 능력」이다.

## 10. 안 잰 것 (Gaps)

- **실제 리그 좌표가 무엇이어야 하는지.** 저장소에 없고, 이 카드가 만들지 않았다.
- **콘솔 쓰기·되읽기 0건.** preview 만 돌렸다. 산출값이 어디 떨어지는지 여전히 미측정
  (t220 의 gap 이 그대로 살아 있다).
- **기종별 Pan/Tilt 물리 가동범위.** §4 대로 저장소에 표가 없다. 135° 가 이 리그에
  맞는지 안 쟀고, MegaPointe·Spiider 규격을 조회하지 않았다.
- **Pan 상한 미검사의 폭발 반경.** `aim_pan_tilt` 에 pan 검사가 없다는 것만 읽었고,
  실기에서 범위 밖 pan 이 어떻게 처리되는지(클램프·거절·랩)는 안 쐈다.
- **POS.02 의 (C) 여부.** 좌표가 0 이라 원리적으로 판정 불가(§5).
- **좌표가 0 인 이유.** 쇼 파일이 원래 그런지, 누가 지웠는지, 임포트가 안 실었는지 —
  상태만 쟀고 내력은 안 쟀다.
- **처방 2 의 뮤테이션·회귀.** 구현하지 않았으므로 검사도 안 짰다.
- **회귀 스위트.** 제품 코드를 안 건드려서 안 돌렸다. base `origin/WT-pos-join` 의
  리드 기준값 `10745 passed, 12 skipped` 는 **이 회차에서 재측정하지 않았다.**
- **CI.** 저장소 전체 결제정지로 죽어 있음(리드 고지). 로컬 자체 venv 로만 쟀다.

## 11. 증거 파일

    .moai/reports/t221/evidence/preview.json         리드 실행 재현 (harness --action preview --limit 0)
    .moai/reports/t221/evidence/spatial_raw.json     get_spatial_context 원문 (86대 · low_confidence)
    .moai/reports/t221/evidence/reach.json           행별 목표점·필요 tilt·초과분
    .moai/reports/t221/evidence/t221_reach_probe.py  위 파일을 만든 프로브 (읽기 전용)
    .moai/reports/t221/evidence/t221_raw_spatial.py  원문 덤프 프로브 (읽기 전용)
    .moai/reports/t221/evidence/cue_map.py           POS 참조 -> 큐 번호 대조
