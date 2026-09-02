# t238 — 기종별 채널 목록 판독: 쏘지 않고 세 행을 갈랐다

베이스: `origin/main ded3d54` (착수 시점 실측) · 브랜치: `WT-fixture-channels`
워크트리: `.claude/worktrees/t238`
**콘솔 쓰기 0 · `run_commands` 0 · `Store` 0 · 프로그래머 접촉 0** — `state` 판독만 썼다.
응답기: 실기 `VERSION=1.6.2`, 9005 로만 응답, `Sequences childCount 6` (착수 시점 재측정)

## 1. 판정 세 줄

1. **`patch/FixtureTypes` 는 도달한다.** `patch` 별칭이 살아 있고 14자식, `FixtureTypes` 15자식.
   깊이는 `patch/FixtureTypes/<슬롯>/6(DMXModes)/<슬롯>/1(DMXChannels)` 다.
2. **카드가 물은 둘 다 「없다」로 답했다.** ETC S4 LED 에 `Frost` 채널이 **없고**(5개 모드 전부),
   Robe Spiider 에 `Gobo`·`Prism` 채널이 **없다**(Mode 1, 26채널 전수).
3. **덤으로 BM.03 이 갈렸다.** Robe MegaPointe 두 모드 어디에도 **`Prism` 채널이 없다.**
   t135 가 쏴서 받은 `Failed` 를, 이번에는 **쏘지 않고** 독립 경로로 같은 결론에 도달했다.

## 2. 무엇을 어떻게 읽었나

읽기 전용 기존 도구 둘만 썼다 — 새 도구를 안 만들었다.

- `server/tools/t131_paged_walk.py` — `childCount` 와 모은 자식 수를 대조해 **완전성**을 판정
- `server/tools/t95_state_dump.py --offset N` — 이름을 페이지 단위로 판독

### 계기 확인 (잘림은 실재했고, 페이징이 덮었다)

| 경로 | childCount | 모은 수 | 보낸 offset | 창 크기 | 판정 |
|---|---|---|---|---|---|
| `patch` | 14 | 14 | [0] | [14] | COMPLETE |
| `patch/FixtureTypes` | 15 | 15 | [0] | [15] | COMPLETE |
| `.../10/6/3/1` (S4 Direct) | 12 | 12 | [0] | [12] | COMPLETE |
| `.../4/6/1/1` (Spiider Mode 1) | 26 | 26 | [0, 15] | [15, 11] | COMPLETE |
| `.../11/6/1/1` (MegaPointe Mode 1) | 32 | 32 | [0, 15, 30] | [15, 15, 2] | COMPLETE |

🔴 **창은 24 가 아니라 15 였다.** 잘림은 실제로 났고(`truncated: true`), `offset` 에코가
돌아왔으며, 이어 붙인 수가 `childCount` 와 같아서 COMPLETE 로 판정했다. 위 표의 「모은 수 ==
childCount」가 이 문서의 모든 「없다」를 떠받친다 — 잘린 창만 봤다면 `Prism` 이 26번째 뒤에
있었을 수도 있다.

⚠️ 대조군 하나가 **실패로 나왔고 그것이 정상이다**: `Sequences` 를 9006 으로 물었더니
`no state reply within 5.0s`. 응답기가 9005 로만 답한다는 리드 전제의 재확인이지 결함이 아니다.

## 3. 측정 (1) — ETC S4 LED S3 Lustr X8 에 Frost 채널은 **없다**

콘솔 등록명 `Source 4 LED Series 3 Lustr X8` (`patch/FixtureTypes` 슬롯 10).
`Wheels` 는 **0개**다. 5개 모드 전량:

| 모드 | 채널 수 | 채널 |
|---|---|---|
| 1 Channel | 1 | Dimmer |
| 3 Ch RGB | **4** | ColorRGB_R·G·B, Dimmer |
| **Direct** (리그가 쓰는 모드) | **12** | Dimmer, DEEPRED, ColorRGB_R·RY·GY·G·C·B·BM, **Shutter1**, DimmerCurve, Fans |
| Expanded | 11 | Dimmer, COLORTEMPERATURE, Tint, ColorMixMode, COLORCROSSFADE, ColorRGB_R·G·B, Shutter1, DimmerCurve, Fans |
| Studio | 7 | Dimmer, COLORTEMPERATURE, Tint, ColorMixMode, Shutter1, DimmerCurve, Fans |

리그 `patch.csv` 가 KEY 6대·FOH 8대를 `Direct 12ch` 로 적었고 콘솔의 `Direct` 가 **정확히 12채널**이다 —
모드 식별이 우연이 아니다.

**결론: BM.04(`Frost 30%`, 대상 KEY)는 어휘 문제가 아니라 기종 문제다.** 철자를 고쳐도,
프로브를 다시 돌려도 열리지 않는다. 그 기종에 그 채널이 없다.

(덧: `3 Ch RGB` 모드는 이름이 3인데 채널이 4다. 이 카드의 질문은 아니라 안 팠다.)

## 4. 측정 (2) — Robe Spiider 에 Gobo·Prism 채널은 **없다**

🔴 **`patch/FixtureTypes` 에 `Robin Spiider` 가 슬롯 4 와 슬롯 12, 두 번 등록돼 있다.**
둘 다 열어 Mode 1 채널 26개를 전수 판독했고 **이름 목록이 서로 같다** — 그래서 「리그가 둘 중
어느 것을 쓰는가」가 이 질문의 답을 바꾸지 않는다. (어느 쪽인지는 여전히 미확정 — 6절.)

Mode 1, 26채널 전량:

    RGBW Cluster_ColorRGB_R·G·B·W, RGBW Cluster_Dimmer,
    Yoke_Main Module_Pan, Tilt, PositionMSpeed, FixtureGlobalReset,
    COLORMIXER, COLORTEMPERATURE, COLOURPRIORITY,
    PIXELMASK, PIXELMASKINDEXROTATE, PIXELMASKSTEPTIME,
    EFFECTWHEEL, ColorRGB_R·G·B·W, COLORMIXER2,
    Shutter1, Dimmer, **Zoom**, Shutter2, Dimmer2

`Gobo` 0건 · `Prism` 0건 · `Frost` 0건 · `Focus` 0건. `Zoom` 은 **있다**. `Wheels` 는 `E` 하나뿐이다.

## 5. 덤으로 갈린 것 — Robe MegaPointe 에 Prism 채널이 **없다**

카드가 시킨 둘은 아니지만 같은 경로에서 한 번에 나왔고, BM 두 행이 여기 걸려 있다.
Mode 1·Mode 2 **둘 다 32채널이고 이름이 같다**:

    Pan, Tilt, PositionMSpeed, LampControl, ColorRGB_R·G·B, Color1,
    COLORMIXER, ColorMixMSpeed, ColorMixMSPeed2, ZoomMSpeed,
    AnimationWheel1, ANIMATIONINDEXROTATE, EFFECTMACROS,
    **Gobo1, Gobo2, Gobo2Pos**, EFFECTWHEEL, EFFECTINDEXROTATE,
    EFFECTWHEEL2, EFFECTINDEXROTATE2, EFFECTMACROS2, EFFECTMACRORATE,
    EFFECTWHEEL3, EFFECTINDEXROTATE3, **Frost1**, **Zoom**, **Focus1**,
    ReflectorAdjust, Shutter1, Dimmer

`Prism` 0건. `Wheels` 는 `C1 · AnimationWheel · G1 · G2 · E · E2 · E3` 일곱이고 이름에 prism 은 없다.

🔴 **`_PROBE_REJECTED` 넷의 출처 등급이 이 판독으로 갈라진다.** MegaPointe 에는
`Frost1`·`Focus1`·`Shutter1` 채널이 **있고** `Prism` 만 없다 — t135 가 적은 등급
(「Focus1·Frost1·Shutter1 은 **읽은** 이름, Prism1 은 **쏴서 Failed 를 받은** 이름」)과
정확히 일치한다. 다른 경로로 같은 결론에 닿았다.

## 6. 이 판독이 BM 5행을 어떻게 갈랐나

대상 그룹은 `group.csv` 에서 확인했다 — `MOVER-ALL` = `MOVER-U`(MegaPointe 8대) + `MOVER-D`(Spiider 8대).

| 행 | 대상 | 필요 속성 | 이 판독의 답 |
|---|---|---|---|
| BM.01 | MOVER-ALL | Zoom · Gobo · Prism | **Prism 은 두 기종 다 없다**(기종 확정). Gobo 는 MegaPointe 만 있다 → 혼합 |
| BM.02 | MOVER-ALL | Zoom · Gobo | Gobo 가 **Spiider 에 없다** → 8대는 되고 8대는 안 된다 |
| BM.03 | MOVER-U | Zoom · Prism | 🔴 **기종 문제 확정** — MegaPointe 에 Prism 채널 없음 |
| BM.04 | KEY | Frost | 🔴 **기종 문제 확정** — S4 LED 5개 모드 전부에 Frost 없음 |
| BM.05 | MOVER-U | Gobo · Zoom · (예비) | **기종은 갖췄다** — Gobo1·Gobo2 있음. 지금 막는 건 범위 판단과 `예비` 조각(t236) |

**두 행(BM.03·BM.04)은 기종 능력 부재로 확정**됐다. 어휘를 고치든 프로브를 다시 돌리든
열리지 않는다. **한 행(BM.05)은 반대 방향으로 갈렸다** — 기종은 능력을 갖고 있으므로
그 행이 막힌 것은 순수하게 범위·값 판단 문제다.

🔴 **새로 드러난 축: `MOVER-ALL` 은 혼합 기종 그룹이다.** 한 bm 행이 두 기종을 겨누는데
속성이 한쪽에만 있으면 「열림/막힘」이 아니라 **절반**이다. 지금 `classify_storability` 는
대상 그룹을 **아예 보지 않는다** — 이 축은 파서 모델에 없다. 카드감이라 판단해 리드에 올린다.

## 7. 안 잰 것 (Gaps) — 「없다」와 「못 봤다」를 가른다

**「없다」로 적은 것** (창 완전성 확인 + 전수 판독):
- S4 LED 5개 모드의 채널 목록에 `Frost` 없음
- Spiider Mode 1 26채널에 `Gobo`·`Prism`·`Frost`·`Focus` 없음
- MegaPointe Mode 1·2 32채널에 `Prism` 없음

**「못 봤다」로 남는 것**:
- **Spiider 는 Mode 1 만 봤다.** 나머지 9개 모드(Mode 2~10)는 안 열었다. 리그가 Mode 1 을
  쓰므로 이 카드의 질문에는 충분하지만, 「Spiider 라는 기종에 Gobo 가 없다」로 넓히면 안 된다.
- **리그 시트의 채널 수와 콘솔의 채널 수가 다르다.** 시트 `Mode 1 49ch` ↔ 콘솔 26채널,
  시트 `Mode 1 39ch` ↔ 콘솔 32채널. 「콘솔 DMXChannels 는 논리 채널이고 시트 숫자는
  16비트 fine 을 포함한 바이트 자국」이면 둘 다 설명되지만 **그것을 재지 않았다.** 가설이다.
- **슬롯 4 와 슬롯 12 중 리그가 어느 Spiider 를 쓰는지 안 쟀다.** 채널 이름이 같아 이 답은
  안 바뀌지만, 다른 질문에서는 갈릴 수 있다.
- **`Wheels` 의 한 글자 이름이 무엇인지 안 쟀다.** Spiider 의 `E`, MegaPointe 의 `E·E2·E3` 가
  효과 휠인지 프리즘인지 이 판독으로는 모른다. 채널 목록에 prism 이 없다는 것과 별개다.
- **채널이 있다는 것이 「그 속성을 쏘면 받는다」는 것은 아니다.** 이 카드는 쓰기 0 이다.
  Gobo1 이 있다고 `Attribute 'Gobo1' At <값>` 이 통한다는 뜻이 아니다.
- **값 단위는 여전히 미측정이다.** Zoom 채널이 있는 것과 `At 45` 가 도인지 퍼센트인지는
  다른 질문이고, 그것은 t235 가 연 문(감독 승인 대기)에 걸려 있다.

## 8. 잔여 위험

- **판독 시점의 쇼가 다르면 패치도 다르다.** 이 문서의 모든 숫자는 `Sequences childCount 6`
  인 쇼에서 잰 것이다. 쇼가 바뀌면 `patch/FixtureTypes` 의 슬롯 번호부터 달라진다 —
  **슬롯 번호를 기억해 다음 회차에 그대로 쓰지 마라. 이름으로 다시 찾아라.**
- **창 크기 15 는 관측이지 계약이 아니다.** 응답기가 창을 바꾸면 offset 순서가 달라진다.
  판정은 언제나 「모은 수 == childCount」로 해야 하고, 창 크기를 상수로 박으면 안 된다.
- **이름에 `Prism` 이 없다는 것과 프리즘 기능이 없다는 것은 엄밀히 다르다.** 이 리그의
  MegaPointe GDTF 가 프리즘을 `EFFECTWHEEL` 계열로 모델링했을 가능성을 이 판독은 배제하지
  못한다. 다만 t135 가 **쏴서 받은 `Failed`** 와 방향이 같아, 둘이 서로를 보강한다.
