# t141 선행 — 감독 시트 토큰 전수 (카드가 「만든 적 없다」고 적은 것)

- 카드: t141 · SPEC-COPILOT-LXSEQ-003 · 기준 `08edf8b`
- 트리 `.claude/worktrees/t141` · 브랜치 `WT-beam-vocab-canon`
- **콘솔 접촉 0.** 읽기와 세기뿐이다. 코드 변경 0.

## 0. 왜 이것이 선행인가

카드의 물음은 「두 어휘를 각각 어디에 정본으로 세우고 매핑을 어디에 두나」다.
매핑을 설계하려면 **한쪽 정의역**을 알아야 하는데, 감독 시트 쪽 정의역은
이 저장소에서 한 번도 열거된 적이 없다. 그래서 먼저 셌다.

## 1. 대상 — 시트 4개 전량

    src/Lighting_Designer/02_RIG팩/LXSEQ_RIG_01_ShowBase_r3.preset-bm.csv
    src/Lighting_Designer/02_RIG팩/LXSEQ_RIG_01_ShowBase_r3.preset-col.csv
    src/Lighting_Designer/02_RIG팩/LXSEQ_RIG_01_ShowBase_r3.preset-dim.csv
    src/Lighting_Designer/02_RIG팩/LXSEQ_RIG_01_ShowBase_r3.preset-pos.csv

「4개 전량」은 `ls src/Lighting_Designer/02_RIG팩/*preset*` 의 출력이 정확히 이 넷이라는
뜻이다. 표본이 아니라 전수다.

## 2. 결과 — 아는 이름 12개 중 시트에 나오는 것은 4개다

    grep -oihE "Focus|Frost|Prism|Shutter|Gobo|Position|Control|Shapers|Video|Zoom|Iris|Dimmer" <시트 4개> | sort | uniq -c | sort -rn

       4 Zoom
       3 Gobo
       2 Prism
       1 Frost

**0회인 것 8개**: `Focus` · `Shutter` · `Position` · `Control` · `Shapers` · `Video` ·
`Iris` · `Dimmer`.

행 단위로 보면 bm 시트 하나가 전부를 낸다:

| 행 | Value 원문 | 뽑히는 이름 |
|---|---|---|
| BM.01 | `Zoom 45° · Gobo OPEN · Prism OFF` | Zoom · Gobo · Prism |
| BM.02 | `Zoom 20° · Gobo OPEN` | Zoom · Gobo |
| BM.03 | `Zoom 8° · Prism 3-facet ON` | Zoom · Prism |
| BM.04 | `Frost 30%` | Frost |
| BM.05 | `Gobo 슬롯2(브레이크업) · Zoom 25° · 예비` | Gobo · Zoom |

col·dim 은 값이 RGB/퍼센트라 `classify_storability` 가 토큰 경로로 가지 않고,
pos 의 `RecordGuide` 는 한글 산문이라 `_WORD = [A-Za-z][A-Za-z0-9]*` 에 걸리는
속성 이름이 없다.

## 3. 그래서 목록 둘이 실제보다 넓다

    _PROBE_REJECTED = ("Focus", "Frost", "Prism", "Shutter")
                        ^^^^^            ^^^^^^^^^  <- 시트 등장 0회
    _OUT_OF_SCOPE   = ("Gobo", "Position", "Control", "Shapers", "Video")
                               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^  <- 전부 0회

지금 이 리그에서 **일을 하는 항목은 `Frost`·`Prism`·`Gobo` 셋뿐**이다.

⚠️ **이것은 「나머지를 지워라」가 아니다.** 시트는 감독이 쓰는 문서이고 다음 쇼에서
`Focus` 나 `Shutter` 가 등장할 수 있다. 지금 잰 것은 「현재 리그 기준 발동 범위」이지
「목록이 과하다」는 판정이 아니다. 판정하려면 시트가 장래에 어떤 토큰을 쓸지를 알아야
하는데 그건 이 카드가 못 재는 것이다(§5).

## 4. 🔴 매칭 방향 — 두 어휘가 구조적으로 분리될 수밖에 없는 이유

`server/lxseq/preset_parser.py:207-215`:

    def _attribute_tokens(value: str) -> list[str]:
        known_names = list(_ACCEPTED_ATTRIBUTES) + list(_PROBE_REJECTED) + list(_OUT_OF_SCOPE)
        ...
        if token.lower().startswith(known.lower()) and known not in found:

**시트 토큰이 목록 이름으로 시작해야** 걸린다 — 즉 시트 토큰이 목록 이름보다
길거나 같아야 한다. 방향이 이쪽이라는 것이 설계 제약을 만든다:

| 목록에 무엇을 두나 | 시트 `Prism 3-facet ON` 매치 | 콘솔 발사 |
|---|---|---|
| `Prism` (짧은 총칭) | **걸린다** — `prism`.startswith(`prism`) | 콘솔이 모르는 이름 |
| `Prism1` (콘솔 채널명) | **안 걸린다** — `prism`.startswith(`prism1`) 은 거짓 | 콘솔이 받는 이름 |

**한 목록이 두 일을 동시에 할 수 없다.** 시트를 걸려면 짧아야 하고, 콘솔에 쏘려면
길어야 한다. t135 가 BM.03 로 관측한 회귀는 이 비대칭의 결과이지 우연이 아니다.

이것이 카드의 물음(「통일이 아니라 매핑」)에 대한 **구조적 근거**다: 통일이 불가능한
것은 취향 문제가 아니라 술어의 방향 때문이다.

## 5. 안 잰 것

1. **시트가 장래에 쓸 토큰** — 이 리그의 현재 시트만 셌다. 다른 쇼의 RIG 팩은 안 봤고,
   이 저장소에 그것이 있는지도 확인하지 않았다. 그래서 §3 을 「목록이 과하다」로
   읽으면 안 된다.
2. **접두 매칭의 과다 매치 방향** — 시트에 `Prismatic` 같은 더 긴 토큰이 오면 `Prism`
   에 걸린다. 지금 시트엔 없지만 그것이 의도인지 사고인지는 안 쟀다(t139 축).
3. **목록에 없는 이름의 통과** — `_attribute_tokens` 가 모르는 이름은 토큰 0개라
   무조건 storable 로 통과한다(t137 축). 이 카드 범위 밖이다.
4. **`_ACCEPTED_ATTRIBUTES` 쪽 방향** — 이 census 는 hold 목록 둘에 초점을 뒀다.
   수용 목록(`Dimmer`/`ColorRGB_*`/`Zoom`/`Iris`)도 같은 술어를 타지만 col·dim 은
   토큰 경로로 안 가므로 실제 발동은 bm 의 `Zoom` 뿐이다 — 그 비대칭은 안 팠다.

## 6. 다음

이 정의역 위에 설계를 세운다: 두 어휘의 정본 자리와 매핑 자리, 그리고 그 매핑이
방향(§4)을 지키는지 재는 검사. 설계가 `server/looks/schema.py` 를 건드려야 하면
거기서 멈추고 보고한다 — 그 파일은 PRESERVE 게이트 둘이 잠그고 있고 t149 소유다.
