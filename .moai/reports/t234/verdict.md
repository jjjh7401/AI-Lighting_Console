# t234 — 두 표는 만나지 않는다. 그리고 콘솔이 그 표가 옳다고 답했다

베이스: `origin/main dd967ea` (착수 시점 실측) · 브랜치: `WT-pool-family-split`
워크트리: `.claude/worktrees/t234` · **콘솔 쓰기 0 · 코드 변경 0** (판독과 판정이 산출물)
응답기: 실기 `1.6.2` · 9005 · `Sequences childCount 6`

## 0. 판정 세 줄

1. **런타임 모순이 아니다.** `ATTRIBUTE_POOL_FAMILY` 의 소비자는 `server/looks/` **안에만**
   있고, LXSEQ 프리셋 경로는 그것을 **한 번도 안 부른다.** bm 행의 풀은
   `_PRESET_POOL_FAMILY['preset-bm'] = 'Beam'` **혼자** 정한다.
2. **그래도 실질 질문은 남고, 이번엔 콘솔이 직접 답했다.** `Zoom` 은 `FeatureGroup 6 = Focus`,
   `Iris`·`Prism1`·`Frost1`·`Shutter1` 은 `5 = Beam`, 🔴 **`Gobo1` 은 `3 = Gobo`** —
   이 저장소가 **범위 밖으로 선언한 계열**이다. bm 시트 다섯 행은 **두 계열이 아니라 셋**에 걸친다.
3. **권고: (2) 기각**(콘솔 반증) · **(1)은 방향은 맞으나 지금 세우지 않는다** ·
   **(3)은 감독 질문 한 문장으로 올린다.** 그리고 **지금 고칠 코드가 없다.**

## 1. 지형이 바뀌었다 — 리드가 시킨 재측정

카드는 「BM 5행 중 **4행**이 Zoom 을 쓴다」로 서 있다. t238(main `a7028b7`)의 기종 채널
판독을 얹으면 그 4가 낡는다:

| 행 | 값 | 대상 | t238 판정 | 이 축에 걸리나 |
|---|---|---|---|---|
| BM.01 | `Zoom·Gobo·Prism` | MOVER-ALL | **Prism 이 두 기종 다 없음** → 적힌 대로는 영구 불가 | (죽은 행) |
| BM.02 | `Zoom·Gobo` | MOVER-ALL | Gobo 는 MegaPointe 8대만 → **절반** | **예** |
| BM.03 | `Zoom·Prism` | MOVER-U | **Prism 없음** → 영구 불가 | (죽은 행) |
| BM.04 | `Frost` | KEY | **Frost 없음** → 영구 불가 | 아니오(Zoom 없음) |
| BM.05 | `Gobo·Zoom·예비` | MOVER-U | 채널 전부 실재 → **생존** | **예** |

**「4행」이 아니라 「살아남을 수 있는 2행, 그리고 둘 다 Zoom 을 쓴다」다.** 축은 사라지지
않았고 **폭만 줄었다** — 그리고 남은 둘이 하필 이 축의 정중앙이다(둘 다 Zoom + Gobo).

## 2. 두 표는 만나지 않는다 (실측)

    grep -rn "pool_family\|payload_for_family" server/ --include=*.py
      server/looks/loader.py:105        pool_family(name) is None -> 거절
      server/looks/instantiate.py:332   payload_for_family(look, family)
      (그 밖의 프로덕션 소비자 0건)

    grep -rn "from server.looks" server/lxseq/ server/orchestrator/tools.py
      preset_parser.py:37  CONFIRMED_ATTRIBUTES, PROBE_GATED_ATTRIBUTES   <- **어휘만**
      tools.py:68          LookLibrary

즉 `ATTRIBUTE_POOL_FAMILY` 는 **룩(Look) 하위 시스템의 표**이고, 프리셋 임포트 경로는
그 표를 읽지 않는다. t233 의 관측 두 줄은 **둘 다 참**이지만 서로 다른 세계의 참이다 —
「bm 행은 Beam 풀에 저장된다」(프리셋 경로의 결정)와 「Zoom 은 Focus 계열이다」(룩 경로의
분류). **두 문장이 한 실행 경로에서 충돌하는 순간은 없다.**

⚠️ 그래서 이것은 「지금 잘못 저장되고 있다」가 아니다. t233 이 「코드 판독 · 실기 미확인」
이라고 정직하게 한정한 그대로이고, 이 회차는 그 한정을 **한 단계 더 좁힌다** —
못 잰 것이 아니라 **그 경로에 그 표가 없다.**

## 3. 🔴 콘솔이 답했다 — 그리고 표가 옳다

이 카드 전체가 문서 한 줄(`10_object_model.md:38-40`)에 기대고 있었다. 콘솔에 직접 물었다.

    patch/AttributeDefinitions/3          FeatureGroups, childCount 9
      1 Dimmer · 2 Position · 3 Gobo · 4 Color · 5 Beam · 6 Focus · 7 Control · 8 Shapers · 9 Video
    patch/AttributeDefinitions/3/5 -> name Beam    (슬롯 주소로 교차 검증)
    patch/AttributeDefinitions/3/6 -> name Focus

각 속성의 `FEATURE` 핸들(`introspect --names FEATURE`):

| 속성 | 콘솔이 답한 것 | 계열 | 저장소 표 | 일치 |
|---|---|---|---|---|
| `Zoom` | `FeatureGroup 6.1` | **Focus** | `Focus` | ✅ |
| `Iris` | `FeatureGroup 5.1` | **Beam** | `Beam` | ✅ |
| `Frost1` | `FeatureGroup 5.1` | **Beam** | (표에 없음) | — |
| `Prism1` | `FeatureGroup 5.1` | **Beam** | (표에 없음) | — |
| `Shutter1` | `FeatureGroup 5.1` | **Beam** | (표에 없음) | — |
| `Focus1` | `FeatureGroup 6.1` | **Focus** | (표에 없음) | — |
| `Gobo1` | `FeatureGroup 3.1` | 🔴 **Gobo** | (표에 없음) | — |

**`ATTRIBUTE_POOL_FAMILY` 는 콘솔과 일치한다.** 룰북 문면도 일치한다. 그러므로 갈래 (2)는
「문면과 어긋나는」 변경이 아니라 **콘솔이 답한 사실과 어긋나는** 변경이다.

### 3.1 그리고 계열이 둘이 아니라 셋이다

bm 시트 다섯 행의 속성을 계열로 접으면:

    Zoom          -> Focus      (BM.01·02·03·05)
    Prism · Frost -> Beam       (BM.01·03·04)
    Gobo          -> **Gobo**   (BM.01·02·05)  <- IN_SCOPE_POOL_FAMILIES 에 없다

`IN_SCOPE_POOL_FAMILIES = ("Dimmer", "Color", "Beam", "Focus")` — **Gobo 는 범위 밖**이고,
`_OUT_OF_SCOPE` 가 그 계열을 이미 보류 사유로 들고 있다. 즉 「bm 시트를 두 풀로 나눈다」는
갈래 (1)의 서술 자체가 **개수를 하나 빠뜨렸다.**

## 4. 갈래 판정

### (2) `ATTRIBUTE_POOL_FAMILY['Zoom']` 을 `Beam` 으로 — **기각**

콘솔이 `Zoom -> FeatureGroup 6(Focus)` 라고 답했다(§3). 표를 고치면 저장소가 **콘솔과 다른
분류를 갖게** 되고, 그 표를 실제로 쓰는 곳은 룩 하위 시스템이므로 **이 카드와 무관한
경로(`payload_for_family` 의 계열 분할)가 틀어진다.** bm 문제를 고치려고 룩을 망가뜨리는
거래다. 비용이 이익보다 크고, 이익도 없다 — 프리셋 경로는 그 표를 안 읽는다(§2).

### (1) 시트를 계열별로 나눠 저장 — **방향은 맞다. 지금 세우지 않는다**

계열이 셋이고 그중 하나가 범위 밖이므로, 지금 세우면 **범위 결정을 코드가 먼저 해버린다.**
그리고 「한 시트 → 여러 풀」은 구조 변경이라 `_PRESET_POOL_FAMILY`(종류→풀 하나)와
`_preset_pool_number` 한 번 호출, 슬롯 배정 전체를 건드린다. 게다가 **소비자가 없다** —
살아남을 수 있는 두 행조차 어휘·대상 축으로 아직 막혀 있다(t236·t241·t243).

### (3) `Zoom` 행은 애초에 bm 이 아니라고 판정 — **감독 소유. 판정하지 않는다**

정본 시트 규약(`src/Lighting_Designer/01_스펙/LX-SEQ-SPEC-v2.1.md:253`)이
`BM(Beam: zoom·gobo·prism·frost·focus 통합)` 이라고 **명시적으로 통합을 선언**한다.
즉 지금 시트는 「한 ID 체계 안에 여러 계열을 담는다」가 **설계 의도**이고, 그것을 쪼개는
것은 감독의 규약 변경이다.

## 5. 🔴 감독께 물을 것 (리드에게 올리는 한 문장)

> BM 프리셋 시트가 콘솔 계열 기준으로 **세 계열**(Zoom→Focus · Prism/Frost→Beam ·
> Gobo→Gobo, 이 중 Gobo 는 현재 범위 밖)에 걸쳐 있는데, ① 한 시트를 계열별 여러 풀에
> 나눠 저장할지, ② Gobo 계열을 범위 안으로 들일지, ③ 시트 ID 체계를 계열별로 쪼갤지
> (`BM.xx` → `BM.xx`/`FOC.xx` 등, 규약 §253 의 「통합」 선언 변경) 중 무엇으로 갑니까.

이 질문 없이 (1)을 세우면 **코드가 규약을 먼저 정하게 된다.**

## 6. 안 잰 것 (Gaps)

- 🔴 **프리셋 풀이 계열로 필터링하는지 안 쟀다.** 이 카드 전체의 심각도가 여기 달려 있다 —
  `Store Preset <Beam풀>.<n>` 이 프로그래머의 Zoom 값을 **버리는지 담는지** 모른다.
  버리면 빈 프리셋이 조용히 저장되고(t108 C1 계열), 안 버리면 이 축은 **정리 문제**이지
  안전 문제가 아니다. 재려면 쏘고 되읽어야 하는데 **되읽기 채널이 없다**(t235).
- **어느 풀에 실제로 앉는지 안 쟀다.** t233 의 한정 그대로다 — bm 행이 전부 막혀 있어
  실기로 확인할 대상이 없다.
- **`_PRESET_POOL_FAMILY` 의 `Beam` 이 콘솔 풀 목록의 어느 번호인지 안 쟀다.**
  `_preset_pool_number` 가 이름으로 찾는데, 그 이름이 콘솔 `PresetPools` 에서 어떤 슬롯인지
  이 회차는 조회하지 않았다.
- **전역 사전 533개 중 7개만 물었다.** bm 시트에 나오는 것 위주다(t239 가 연 경로).
- **`Shutter1 -> Beam`** 이 나왔는데 이 저장소는 `Shutter` 를 danger 정책으로 배제해 뒀다.
  그 배제와 계열은 다른 축이라 안 팠다.

## 7. 잔여 위험

- **「표가 옳다」가 「문제가 없다」로 읽히는 것.** `ATTRIBUTE_POOL_FAMILY` 는 옳지만
  bm 시트가 세 계열에 걸친다는 사실은 그대로다. 옳은 표와 통합 시트가 **같이** 참이다.
- **두 표가 안 만난다는 것이 「영원히 안 만난다」는 뜻은 아니다.** (1)로 가면 프리셋
  경로가 속성→계열 지도를 **처음으로** 필요로 하게 되고, 그때 이 표가 그 자리에 온다.
  그 순간 `ATTRIBUTE_POOL_FAMILY` 가 여섯 항목뿐이라는 것이 문제가 된다 —
  `Prism1`·`Frost1`·`Gobo1`·`Focus1`·`Shutter1` 이 **표에 없다**(§3 표의 「표에 없음」).
- **이 문서의 계열 번호는 이 쇼 기준이다.** 슬롯 주소로 교차 검증했지만(§3),
  쇼가 바뀌면 이름으로 다시 찾아야 한다 — t238 이 남긴 경고를 그대로 물려받는다.
