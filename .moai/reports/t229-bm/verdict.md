# t229-BM — BM 적용 경로 설계: 「칸 채우기」가 아니라 **성분 목록**이다

베이스: `origin/main 46d3f84` · 브랜치: `WT-beam-apply`
환경: 자체 워크트리 · 자체 venv · **콘솔 접촉 0 · 제품 코드 변경 0** (설계가 산출물)
선행 재료: `origin/WT-kelvin-beam:.moai/reports/t229/verdict.md` §6 (앞 레인, **미머지**)

## 0. 판정 세 줄

1. **지뢰는 실재하고, 오늘 재현했다.** `Zoom 45°` 단독이 `classify_storability` 를 **통과**하는데(`storable=True`) `_lxseq_preset_apply_command` 는 **`None`** 을 낸다. 소비 루프가 그때 번들을 통째로 버린다(`apply_untranslatable`). 지금은 5행 전부가 다른 사유로 막혀 있어 **가려져 있을 뿐**이다.
2. **`LXSEQ_PRESET_APPLY_ATTRIBUTE` 에 bm 칸을 채우는 것으로는 안 된다.** 그 표는 `종류 → 속성 하나`이고 소비 지점은 `Attribute <name> At <level>` 한 줄을 만든다. bm 값은 **한 행에 속성이 여럿**이고 단위가 섞인다.
3. **처방은 COL 이 쓴 구조를 형태만 바꿔 그대로 쓰는 것** — 판정기와 판독기가 **같은 술어 하나**를 쓰게 만든다. 다만 반환형이 `RGB 3성분`이 아니라 **`(속성, 값)` 목록**이다.

## 1. 지뢰 재현 (오늘 실측)

    classify_storability("preset-bm", "Zoom 45°")   -> (True, ())        ← 열린다
    _lxseq_preset_apply_command(kind="preset-bm")   -> None              ← 못 옮긴다
    대조 dim: classify(...,"85%") -> (True, ())
              apply(...)          -> "Group 1 ; Attribute 'Dimmer' At 85"

`LXSEQ_PRESET_APPLY_ATTRIBUTE` 는 `{'preset-dim': 'Dimmer'}` 한 칸이고, bm 은 그 표에 없어 `attribute is None` 에서 `None` 으로 빠진다(`tools.py:1763-1765`).
소비 지점(`tools.py:5180-5190`)은 `untranslatable` 이 하나라도 있으면 `refusal="apply_untranslatable"` 로 **한 줄도 안 보낸다.**

**즉 「bm 한 행을 여는 것」과 「적용 경로를 만드는 것」의 순서가 뒤집히면 그 시트가 0건이 된다.** 앞 레인이 예고한 그대로이고, 이 회차가 **술어를 직접 호출해 확정**했다.

⚠️ 폭발 반경은 **그 시트 한 장**이다. `parse_preset_csv` 가 헤더에서 종류 하나를 정하고 한 번의 임포트 = 한 시트 = 한 종류이므로(t154 가 t141 의 「임포트 전체」 주장을 반증), dim·col 임포트는 안 죽는다.

## 2. 왜 「칸 하나」로 안 되는가 — 값의 형태

시트 정본(`src/Lighting_Designer/02_RIG팩/LXSEQ_RIG_01_ShowBase_r3.preset-bm.csv`) 5행 전량:

| 행 | 값 | 속성 수 | 값 형태 |
|---|---|---|---|
| BM.01 | `Zoom 45° · Gobo OPEN · Prism OFF` | **3** | 각도 · 열거(OPEN) · 불린(OFF) |
| BM.02 | `Zoom 20° · Gobo OPEN` | **2** | 각도 · 열거 |
| BM.03 | `Zoom 8° · Prism 3-facet ON` | **2** | 각도 · 열거+불린(`3-facet ON`) |
| BM.04 | `Frost 30%` | 1 | 퍼센트 |
| BM.05 | `Gobo 슬롯2(브레이크업) · Zoom 25° · 예비` | **2**(+주석) | 슬롯 번호+한글 라벨 · 각도 · **비-속성 토큰** |

dim 은 `한 속성 · 한 퍼센트`라 표 한 칸으로 들어간다. bm 은 **셋 다 다르다**: 속성이 여럿이고, 값 단위가 넷(도·퍼센트·열거·슬롯번호)이며, **속성이 아닌 토큰**(`예비`)이 섞인다.

## 3. 설계 — 세 조각

### 3.1 술어 하나: `_bm_components(value_raw) -> tuple[tuple[str,str], ...] | None`

`_col_components()` 와 **같은 자리·같은 계약**이다(`preset_parser.py:453`). 다른 것은 반환형뿐:

    col:  value_raw -> (R, G, B)                        3성분 고정
    bm:   value_raw -> (("Zoom","45°"), ("Iris","50%")) 가변 길이 (속성, 원문값) 목록

- **판정기**(`classify_storability` 의 bm 갈래)와 **판독기**(툴 층)가 이 함수를 **같이 부른다.** 갈라질 수 없다 — 그것이 계약이고, `_col_components` 독스트링이 그 계약을 이미 문장으로 갖고 있다.
- `None` 은 「이 값을 성분으로 못 가른다」이고, 그때 판정기는 `HOLD_VALUE_NOT_MACHINE_READABLE` 로 보류한다.
- 🔴 **비-속성 토큰을 버리지 않는다.** BM.05 의 `예비` 는 속성이 아니다. 지금 `_attribute_tokens` 는 그것을 **조용히 무시**한다(알려진 이름 접두사만 모은다). 성분 목록은 **남은 토큰이 있으면 그것을 보고**해야 한다 — 안 그러면 시트가 뜻한 것의 일부가 조용히 사라진다.

### 3.2 명령 빌더: `preset_apply_beam_command(group_no, components)`

`preset_apply_command`(dim) · `preset_apply_color_command`(col) 의 **셋째 형제**다. 형제가 나뉜 이유는 「값의 타입이 다르면 검사가 느슨해진다」이고(store.py:112 독스트링), bm 은 **개수가 가변**이라 세 번째 이유가 하나 더 붙는다.

    Group <n> ; Attribute 'Zoom' At <v> ; Attribute 'Iris' At <v>

- **한 줄인 것이 계약이다.** 세 줄로 나누면 `run_commands` 의 접힘이 뒤를 지우고 앞 성분만 실린 프로그래머가 저장될 수 있다 — col 이 같은 이유로 한 줄을 쓴다(t108 C1 과 같은 자리).
- 성분이 **0개면 `None`** 을 낸다(빈 `Group <n> ;` 를 만들지 않는다).

### 3.3 표는 남기되 역할을 바꾼다

`LXSEQ_PRESET_APPLY_ATTRIBUTE` 에 `preset-bm` 칸을 **넣지 않는다.** 그 표는 「한 종류 → 한 속성」의 정의역을 갖고 있고 bm 은 그 정의역에 안 든다. 대신 `_lxseq_preset_apply_command` 가 col 과 같은 모양으로 **종류별 분기**를 하나 더 갖는다:

    if placement.kind == "preset-col":  ... (기존)
    if placement.kind == "preset-bm":   components = bm_components(...)
                                        if components is None: return None
                                        return preset_apply_beam_command(GROUP_NO, components)
    attribute = LXSEQ_PRESET_APPLY_ATTRIBUTE.get(...)   ... (기존, dim)

**표에 칸을 넣는 형태를 명시적으로 거절한다** — 넣으면 `dim_level_percent` 가 bm 값을 읽으려다 `None` 을 내고, 그건 §1 의 지뢰를 **다른 모양으로 다시 심는 것**이다.

## 4. 순서 — 이것이 이 설계의 핵심

    ① 술어 + 빌더 + 분기를 먼저 넣는다        (이 시점에 bm 행은 여전히 0건 storable)
    ② 트립와이어로 ①이 실제로 붙었는지 잰다
    ③ 그 다음에야 어휘를 연다 (Zoom·Iris 외 확장)

**①과 ③을 한 커밋에 넣어도 순서는 지켜야 한다.** 「한 커밋에 넣는다」는 약속이고 **구조가 아니다** — 앞 레인이 그렇게 적었고 맞다. 구조로 막는 것이 §3.1 의 단일 술어다.

## 5. 어휘를 열 때 무엇이 열리는가 (예측, 미측정)

지금 5행을 막는 것은 어휘이지 적용 경로가 아니다. 적용 경로가 생겨도 **5행은 그대로 0건**이다:

| 막는 축 | 행 | 이 설계가 여는가 |
|---|---|---|
| `Gobo`(범위 밖) | BM.01·02·05 | **아니다** — 풀 계열 확장은 별도 판단 |
| `Prism`·`Frost`(프로브 거절) | BM.01·03·04 | **아니다** — 라이브 프로브 재측정이 선행 |

**즉 이 설계는 「지금 열리는 행 수」를 0에서 0으로 둔다.** 값은 다른 데 있다 — **어휘를 여는 날 그 시트가 0건이 되는 것을 막는다.** 순서를 바로잡는 일이지 행을 여는 일이 아니다.

## 6. 안 잰 것 (Gap)

- **콘솔이 `Attribute 'Zoom' At 45` 를 받는지 안 쐈다.** 이 회차는 쓰기 0이고, `Zoom` 이 수용 어휘라는 것은 `PROBE_GATED_ATTRIBUTES` 선언이지 이 회차의 관측이 아니다. **`At <각도>` 의 단위가 콘솔에서 도인지 퍼센트인지 미측정** — dim 은 퍼센트, col 은 16비트 선형이 실측으로 확정됐지만 Zoom 은 그 자리가 비어 있다.
- **`3-facet ON` · `슬롯2` 를 어떤 값 문면으로 옮길지 안 정했다.** §3.1 은 `(속성, 원문값)` 을 나르기만 하고 빌더가 그것을 어떻게 쓰는지는 **어휘를 여는 회차의 몫**이다. 지금 정하면 미측정 문법을 코드에 박는 것이다.
- **`Iris` 는 시트에 안 나온다.** 수용 어휘라 §1 재현에 썼을 뿐이고, 실제 시트 5행에 `Iris` 행이 **없다.**
- **트립와이어의 형태를 안 정했다.** §4 ②가 무엇을 단언해야 하는지(예: `bm 이 storable 이면 apply 가 None 이 아니다`)는 적었으나, 그것을 어느 파일에 어떤 술어로 쓰는지는 구현 회차의 몫이다.
- **`_attribute_tokens` 가 비-속성 토큰을 무시한다는 것**은 소스 판독이고, `예비` 가 실제로 무시되는지 호출로 확인하지 않았다.

## 7. 잔여 위험

- **§3.1 의 반환형이 커지면 계약이 약해진다.** col 은 `(R,G,B)` 3성분 고정이라 판정기와 판독기가 같은 것을 본다는 것이 자명하다. bm 은 가변 길이라 **「같은 술어를 부른다」만으로는 부족하고**, 빌더가 성분을 **하나도 안 버리는지**를 검사가 따로 지켜야 한다. 버리면 판정은 통과인데 콘솔에 일부만 간다 — `apply_untranslatable` 보다 **조용한** 실패다.
- **`예비` 같은 토큰이 늘어나면 §3.1 의 「남은 토큰 보고」가 소음이 된다.** 시트 작성 규약(정본 `LX-SEQ-SPEC-v2.1.md`)이 주석 토큰을 규정하는지 안 읽었다 — 규정돼 있으면 그 어휘를 알고 무시해야 하고, 아니면 보고가 맞다.
- **이 설계는 `Zoom` 이 콘솔에서 실제로 받는다는 것에 기대고 있다.** §6 첫 항목이 미측정이므로, 어휘를 여는 회차는 **빌더를 쓰기 전에 그 한 줄을 실기로 쏴야** 한다.
