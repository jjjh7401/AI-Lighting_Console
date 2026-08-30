# t135 — BM 빔 프리셋 5행이 안 들어가는 이유

카드: t135 · SPEC-COPILOT-LXSEQ-003 · 브랜치 `WT-beam-attrs` · 기준 `576e73f`
콘솔 쓰기 **0건**. 이 회차는 코드와 문서만 읽었다.

---

## 1. 주장

배차서가 준 전제 3건 중 **2건은 맞고 1건은 근거가 틀렸다.** 그리고 5행은
배차서가 나눈 2갈래가 아니라 **3갈래**로 갈린다 — 처방이 셋이다.

## 2. 증거

### 2.1 술어의 실제 주소 — schema.py 가 아니다

배차서는 두 사유를 `server/looks/schema.py` 에 귀속했다. **사유 문자열이 그
파일을 인용할 뿐, 판정하는 코드는 다른 곳에 있다.**

    server/lxseq/preset_parser.py:65   _PROBE_REJECTED = ("Focus","Frost","Prism","Shutter")
    server/lxseq/preset_parser.py:69   _OUT_OF_SCOPE   = ("Gobo","Position","Control","Shapers","Video")
    server/lxseq/preset_parser.py:187  classify_storability(...)

`schema.py` 는 이 두 튜플을 정의하지도, 내보내지도 않는다. 판정 지점을 고치려면
`preset_parser.py` 를 열어야 한다. (`schema.py` 는 `CONFIRMED_ATTRIBUTES` ·
`PROBE_GATED_ATTRIBUTES` 만 공급한다.)

### 2.2 M0 프로브의 원문 — 날짜·버전·조건

`.moai/specs/SPEC-COPILOT-LOOKLIB-001/progress.md:125-177`

| 항목 | 값 |
|---|---|
| 측정일 | 2026-07-26 |
| 응답기 | `CopilotResponder` **v1.4.1** |
| 선택 | `Group 13` (이름 `All`) |
| 발화 | `Attribute '<name>' At 50` |

결과: `Zoom` ok · `Iris` ok · `Focus` `Illegal object` · `Frost` `Illegal object`
· `Prism1` **`Failed`** · `Shutter` `Illegal object`.

### 2.3 원문이 스스로 적어 둔 한정 — 여기가 핵심이다

같은 절(progress.md:175)이 이렇게 적고 있다:

> 거부 4건은 **문법 무효가 증명된 것이 아니라 픽스처 의존적 결과**다. `Group 13`
> 은 이름이 `All` 이며, 그 그룹의 픽스처가 frost/prism/shutter 속성을 실제로
> 보유하는지는 확립되지 않았다. `Illegal object` 는 (i) MA3가 모르는 attribute
> 이름과 (ii) 선택된 픽스처가 그 속성을 갖지 않음 **양쪽과 모두 정합**한다.
> **픽스처가 더 풍부한 선택을 대상으로 후속 프로브를 돌리면 더 많은 문자열이
> 수용될 수 있다.**

즉 이 판정을 뒤집을 변수로 원문이 지목한 것은 **응답기 버전이 아니라 픽스처
보유 여부**다.

### 2.4 Gobo 제외의 근거

`.moai/specs/SPEC-COPILOT-LOOKLIB-001/plan.md:92`

> Gobo·Control·Shapers·Video는 **매핑되는 v1 룩 속성이 없다**.

기술적 한계가 아니라 선언이다. 다만 여는 비용이 딸려 있다 — `schema.py` 의
`@MX:NOTE` 가 필드 집합을 닫아 두었고, 속성 추가는 `schema_version` 변경이며
그 파장이 P1-1(곡구조 큐리스트) · P1-2(버스킹 위저드) 소비 계약까지 간다.

### 2.5 실행 결과 — 5행 + 대조군 7건

`.venv/bin/python` 으로 `classify_storability("preset-bm", …)` 를 직접 호출.

| 입력 | storable | 읽힌 토큰 | 사유 클래스 |
|---|---|---|---|
| `Zoom 45° · Gobo OPEN · Prism OFF` (BM.01) | False | Zoom·Gobo·Prism | probe_rejected + family_out_of_scope |
| `Zoom 20° · Gobo OPEN` (BM.02) | False | Zoom·Gobo | family_out_of_scope |
| `Zoom 8° · Prism 3-facet ON` (BM.03) | False | Zoom·Prism | probe_rejected |
| `Frost 30%` (BM.04) | False | Frost | probe_rejected |
| `Gobo 슬롯2(브레이크업) · Zoom 25° · 예비` (BM.05) | False | Gobo·Zoom | family_out_of_scope |
| **[대조]** `Zoom 45°` | **True** | Zoom | — |
| **[핵심]** `Gobo OPEN` | False | Gobo | family_out_of_scope |
| **[핵심]** `Gobo 슬롯2` | False | Gobo | family_out_of_scope |
| **[핵심]** `Prism OFF` | False | Prism | probe_rejected |
| **[핵심]** `Prism 3-facet ON` | False | Prism | probe_rejected |
| **[미측정]** `Prism1 ON` | False | Prism | probe_rejected |
| **[날조대조]** `Blorptron 99°` | **True** | (없음) | — |

## 3. 기준 귀속

- 트리: `.claude/worktrees/t135` · 브랜치 `WT-beam-attrs` · HEAD `576e73f`
- 시트: `src/Lighting_Designer/02_RIG팩/LXSEQ_RIG_01_ShowBase_r3.preset-bm.csv` (5행, 전량 인용)
- 표 2.5 는 이 트리 이 커밋에서 **직접 실행**한 결과다. 옮겨 적은 값이 아니다.
- 표 2.2 의 M0 값은 progress.md 에서 **옮겨 적은 값**이다. 내가 재지 않았다.

## 4. 전제 판정

### 전제 1 — 「Gobo 는 지원 안 됨이 아니라 범위 밖」 → **맞다**

plan.md:92 가 근거다. 다만 배차서의 「여는 것은 코드가 아니라 결정」은 절반만
맞다 — 결정이 먼저인 것은 맞지만, 그 결정을 이행하려면 닫힌 스키마를 열어야
하고 그건 `schema_version` 변경이며 하류 SPEC 둘의 소비 계약을 건드린다.
**공짜 결정이 아니다.**

### 전제 2 — 「프로브 판정은 응답기 1.6.x 이전 조건」 → **사실은 맞고 근거는 틀렸다**

날짜(2026-07-26)와 버전(v1.4.1)은 확인된다. 그러나 **응답기 버전은 이 판정을
움직이는 변수가 아니다.** 응답기는 전송·조회 층이고, 콘솔이 attribute 이름을
받느냐는 **선택된 픽스처가 그 속성을 갖느냐**가 정한다 — 원문이 §2.3 에서
그렇게 적어 두었다.

재측정 가치는 있다. 근거가 다를 뿐이다:

- 원문이 지목한 변수는 **픽스처 보유 여부**다
- 프로브는 `Group 13` (`All`) 하나를 쐈다. 이 시트가 겨냥하는 대상은
  `MOVER-ALL` · `MOVER-U` · `KEY` 로 **다르다**
- 프리즘·프로스트를 실제로 가진 장비는 무버다. 무버를 선택해 쏜 적이 없다

⚠️ 배차서가 든 「쇼파일이 바뀌었다(픽스처 80→86, 타입 8→15)」는 **리드의 값이고
내가 재지 않았다.** 사실이면 §2.3 이 지목한 그 변수가 움직인 것이라 재측정
근거가 더 강해진다. 재측정 전에 내가 직접 확인하겠다.

### 전제 3 — 「BM.01 이 두 사유를 지는 건 한 행에 속성이 둘이라서」 → **맞다**

`Zoom 45° · Gobo OPEN · Prism OFF` — 한 행에 셋이고 그중 둘이 각각 다른 사유에
걸린다. 표 2.5 의 토큰 열이 그대로 보여 준다.

## 5. 카드가 몰랐던 것 — 5행은 2갈래가 아니라 3갈래다

판정기는 **속성 이름만 읽고 값은 해석하지 않는다**(`_attribute_tokens` 독스트링:
"값을 해석하지 않는다"). 표 2.5 의 `Gobo OPEN` 대 `Gobo 슬롯2`, `Prism OFF` 대
`Prism 3-facet ON` 이 **글자 하나 다르지 않게 같은 판정**을 받는 것이 그 증거다.

그런데 시트를 보면 막고 있는 값의 성격이 다르다:

| 행 | 막는 속성 | 그 값 | 성격 | 처방 |
|---|---|---|---|---|
| BM.01 | Gobo, Prism | `OPEN`, `OFF` | **중립/해제** | 중립 상태 판정 |
| BM.02 | Gobo | `OPEN` | **중립/해제** | 중립 상태 판정 |
| BM.03 | Prism | `3-facet ON` | 활성 | 재측정 |
| BM.04 | Frost | `30%` | 활성 | 재측정 |
| BM.05 | Gobo | `슬롯2(브레이크업)` | 활성 | 범위 결정 |

**BM.01·BM.02 를 막는 것은 「고보를 넣어라」가 아니라 「고보를 빼라」다.** 두 행에서
중립 상태를 무시하면 남는 것은 `Zoom` 뿐이고, 표 2.5 의 대조군이 `Zoom 45°` →
storable=True 를 보여 준다.

🔴 **다만 이건 자유롭게 얻는 것이 아니라 의미 변경이다.** Zoom 만 저장한 프리셋을
불러오면 직전 룩이 넣어 둔 고보가 그대로 남는다. 「프리셋이 안 쓰는 속성을 명시적으로
꺼야 하는가」는 설계 결정이지 내가 고칠 결함이 아니다. **결정을 요청한다.**

따라서 재측정이 전부 성공해도 열리는 것은 **BM.03·BM.04 둘뿐**이다. 배차서가
암시한 「프로브를 다시 재면 5행이 풀린다」는 성립하지 않는다.

## 6. 범위 밖에서 튀어나온 결함 후보 — 별도 카드 감

날조 대조군 `Blorptron 99°` 가 **storable=True** 로 통과했다.

판정기는 **알려진 나쁜 이름**만 막는다. 모르는 속성 이름은 토큰이 0개라 사유가
붙지 않고 그대로 저장 가능으로 나간다 — fail-open 이다. 시트에 오타가 나거나
새 속성이 들어오면 조용히 콘솔로 향한다.

이 카드의 범위가 아니라 **고치지 않았다.** 별도 카드를 권한다.

## 7. 안 잰 것 (가장 값이 큰 절)

1. **오늘의 쇼파일을 안 봤다.** 픽스처 80→86 · 타입 8→15 는 리드의 값을 옮긴
   것이다. 재측정 순번을 받으면 내가 먼저 잰다.
2. **콘솔에 아무것도 안 쐈다.** `Prism` · `Frost` 가 지금 조건에서 수용되는지는
   여전히 미측정이다.
3. **`Prism` 이라는 문자열은 한 번도 측정된 적이 없다.** M0 가 쏜 것은 `Prism1`
   이다. `_PROBE_REJECTED` 의 `"Prism"` 은 다른 문자열의 측정에서 **외삽**한
   것이다. 재측정 때 두 철자를 **따로** 쏴야 한다.
4. **`Focus` 는 이름이 겹친다.** 속성 `Focus` 는 M0 가 거절했는데, 풀 계열
   `Focus` 는 `IN_SCOPE_POOL_FAMILIES` 에 들어 있다(Zoom 이 거기 산다).
   「Focus 가 범위 안이다」를 「Focus 속성이 된다」로 읽으면 안 된다. 이 축은
   이 카드에서 재지 않았다.
5. **`_attribute_tokens` 의 접두 매칭을 전수로 검사하지 않았다.**
   `token.lower().startswith(known.lower())` 라 다른 오탐이 있을 수 있다.
   시트 5행에서는 오탐이 없음만 확인했다(표 2.5).
6. **뮤테이션을 돌리지 않았다.** 이 회차는 코드를 고치지 않아 지킬 수정이 없다.
   재측정 후 술어를 고치면 그때 돌린다.

## 8. 잔여 위험

- §5 의 중립 상태 판정을 채택하면 **BM.01·BM.02 의 렌더링 의미가 바뀐다.**
  직전 상태가 남는 경로는 실기로 확인해야지 추론으로 닫으면 안 된다.
- 재측정이 `Prism`·`Frost` 를 수용해도, 그건 **그 쇼파일 그 선택**에서의 결과다.
  M0 가 겪은 것과 같은 한정이 그대로 붙는다.
- 판정기를 고치면 `test_lxseq_preset_parser.py:196-197` 의 고정값
  (`probe_rejected` 3 · `family_out_of_scope` 3)이 깨진다. 그 테스트가
  **현재 판정의 비준**이라 갱신 시 무엇을 가렸는지 함께 보고해야 한다.

## 9. 리드에게 요청하는 결정 3건

1. **중립 상태 판정** — `Gobo OPEN` · `Prism OFF` 를 무시할 것인가?
   채택하면 BM.01·BM.02 가 Zoom 만으로 열린다. 의미 변경을 동반한다.
2. **재측정 순번** — 콘솔은 단일 자원이다. `MOVER-U` 선택으로 `Prism` ·
   `Prism1` · `Frost` 를 쏘는 프로브(읽기 아님, `Attribute … At` 발화)의
   순번을 요청한다.
3. **Gobo 범위** — BM.05 를 여는 것은 `schema_version` 변경이다. 하류 SPEC
   둘의 계약을 건드린다. 이 카드에서 다룰 일이 아니라고 본다.

---

# 2회차 — 리드 숙제 둘을 쟀다 (콘솔 쓰기 여전히 0건)

리드가 §5(안 잰 것 살려라) · §6(조상 검사)을 남겼다. 둘 다 쟀고, 그 과정에서
**§7-5 「접두 매칭 전수 미검사」가 열린 gap 에서 확인된 결함으로 바뀌었다.**

## 10. §6 — 기준 커밋 조상 검사

    git merge-base --is-ancestor 570e241 576e73f   ->  exit 0

`570e241` 은 `576e73f` 의 **조상이다.** 갈라지지 않았고, 사이 커밋은 하나다
(`576e73f` PR #188). 재fetch 후에도 `origin/main` 은 여전히 `576e73f` 다 —
「오늘 main 이 여섯 번 움직였다」가 사실이어도 내 기준보다 앞선 것은 없다.

## 11. §5 — 접두 매칭 전수 조사

### 11.1 코퍼스는 짓지 않고 저장소에서 긁었다

    grep -rhoE "(Gobo|Prism|Frost|Shutter|Focus|Zoom|Iris)[A-Za-z0-9]+"

    Prism1 15 · Prisma 7 · Focused 7 · Gobo1 5 · Focuses 1

`Prisma` 는 ORM 이름이고 `Focused`·`Focuses` 는 하네스 문서의 영어 산문이다 —
**셋 다 프리셋 시트 값 칸에는 없다.** 실재하는 오탐이 아니라 술어의 성질을
드러내는 표본이다.

### 11.2 결과 — 같은 술어가 두 목록에서 **방향이 반대다**

`_attribute_tokens` 의 `token.lower().startswith(known.lower())` 를 세 코퍼스
26건에 쏜 결과:

**막는 목록(`_PROBE_REJECTED` · `_OUT_OF_SCOPE`) 쪽 — 과다 차단 = fail-closed**

| 입력 | 읽힌 토큰 | 결과 |
|---|---|---|
| `Prism1` · `Prism1Pos` | Prism | 막힘 — 의도대로 |
| `Prismatic` · `Prisma` | Prism | 막힘 — **과다 차단** |
| `Frost2` · `Frosty` | Frost | 막힘 — `Frosty` 는 과다 차단 |
| `Focused` · `Focuses` · `Focus1` | Focus | 막힘 — 앞 둘은 과다 차단 |
| `Shutter1` · `Shuttered` | Shutter | 막힘 |
| `Gobo1` · `Gobo2` · `Gobo1Pos` | Gobo | 막힘 — 의도대로 |

리드의 주장 「`Prism` 이 `Prismatic` 도 잡는다」는 **확인됐다.** 방향은 안전한
쪽이다 — 넣을 수 있는 행이 보류로 남을 뿐이고, 보류는 사유와 함께 눈에 보인다.

**받는 목록(`_ACCEPTED_ATTRIBUTES`) 쪽 — 과다 수용 = fail-OPEN**

| 입력 | 읽힌 토큰 | storable |
|---|---|---|
| `Iris` | Iris | True — 의도대로 |
| `IrisPulseOpen` | Iris | **True** — 측정된 적 없는 속성 |
| `Zoom` | Zoom | True — 의도대로 |
| `ZoomModeBeam` | Zoom | **True** — 측정된 적 없는 속성 |
| `Zoomed` | Zoom | **True** — 영어 과거분사가 통과한다 |
| `Dimmer` | Dimmer | True — 의도대로 |
| `DimmerCurve` | Dimmer | **True** — 측정된 적 없는 속성 |

🔴 **같은 한 줄의 술어가, 어느 목록에 걸리느냐에 따라 fail-closed 가 되기도 하고
fail-open 이 되기도 한다.** 그리고 안전한 쪽이 뒤집혀 있다 — 과다 차단은 보류
행 하나를 남기고(눈에 보이고 되돌릴 수 있다), 과다 수용은 **측정된 적 없는
속성을 계획에 싣는다**(발화 전까지 안 보인다).

### 11.3 도달 경로 — 어디까지 가는지만 적는다

`storable=True` 는 `server/lxseq/preset_mapper.py:263-268` 에서 storable 목록에
들어가고 `:305` 가 순회한다. **계획에는 들어간다.**

⚠️ 그 계획이 실제로 콘솔에 발화되는지, 안전 게이트가 미측정 속성을 거르는지는
**이 회차에서 재지 않았다.** 「콘솔로 나간다」고 쓰지 않는 이유다.

### 11.4 지금 실재하는가

**아니다.** 정본 bm 시트 5행의 값 칸에 위 문자열은 하나도 없다(§2.5 토큰 열).
**잠재 결함이지 발동 중인 결함이 아니다.** t137(`Blorptron` 미지 속성 통과)과
기전이 다르다 — 저건 토큰 0개, 이건 토큰이 **잘못 매칭돼서** 통과다. 같은
fail-open 계열인지 묶을지는 리드 판단이다.

## 12. §5 — `Focus` 이름 겹침의 구체 사례

`Focus1` 은 실재하는 MA3 속성인데 `_PROBE_REJECTED` 의 `"Focus"` 에 걸려 막힌다.
동시에 풀 계열 `Focus` 는 `IN_SCOPE_POOL_FAMILIES` 에 있다 — `Zoom` 이 거기 산다.

**같은 문자열이 속성 층에서는 거절이고 풀 층에서는 범위 안이다.** 「Focus 는
막힌다」로도 「Focus 는 열려 있다」로도 뭉갤 수 있는 자리다. 두 층을 가르지 않고
쓴 문장은 전부 의심 대상이다. 이 축은 이 카드에서 더 재지 않았다.

## 13. 2회차가 안 잰 것

1. **콘솔 0발** — 1회차와 동일. 리드가 「답 올 때까지 콘솔 잡지 마라」고 했다
2. **안전 게이트가 미측정 속성을 거르는지** — §11.3. 계획 진입까지만 봤다
3. **`_ACCEPTED_ATTRIBUTES` 쪽 과다 수용의 실제 도달 가능성** — bm 시트에 그런
   값을 넣을 사람이 있는지는 조사하지 않았다. 술어의 성질만 쟀다
4. **`ColorRGB_*` 축** — `_WORD` 가 밑줄을 안 먹어 `ColorRGB_R` 이 `ColorRGB`+`R`
   로 쪼개진다. col 시트는 앞단에서 갈라져 이 경로에 안 오지만, **그 사실을
   실행으로 확인하지는 않았다**
5. **뮤테이션 0회** — 여전히 코드를 안 고쳤다. 지킬 수정이 없다

---

# 3회차 — 재측정 승인 이행 (콘솔 발사, 승인 범위 내)

리드 승인 범위: 무버 한 대 선택 + `Attribute` 발화 + 즉시 해제 · `Prism`·`Prism1` 두 철자 따로 · `Frost`. 금지: `Store`·프리셋 풀 접촉·두 대 이상·범위 밖 속성·`ClearAll`.

## 14. 대상 선택 — 콘솔에서 직접 읽었다 (리드 문서 무시)

리드 문서의 픽스처 번호는 만료됐다는 경고를 따라, `query_state`를 offset 페이징으로 돌려 **86개 전량**을 읽었다. `Patch/Stages/1/Fixtures` 인덱스 27 = `MOVER-U 501`.

`query_properties`로 `FIXTURETYPE` 핸들을 해석: **`FixtureType 11` = `Robin MegaPointe`.**

⚠️ 이것은 t98(`fixture-type-shortfall.md`)이 「콘솔에 없는 6종」에 넣었던 그 기종이다 — 오늘 사이에 타입이 들어왔다는 뜻이다. 리드가 경고한 「오늘 콘솔이 바뀌었다」가 이 지점에서 확인된다.

`Patch/FixtureTypes` 전량(15종, `truncated=false`)도 같이 읽었다:

    1 Robin Esprite · 2 Robin Forte HP · 3 Robin LEDBeam 350 · 4 Robin Spiider
    5 Xtylos · 6 Sharpy Plus · 7 Robin MMX Spot · 8 Mac Aura XB
    9 Rush Par 2 RGBW Zoom · 10 Source 4 LED Series 3 Lustr X8
    11 **Robin MegaPointe** · 12 Robin Spiider · 13 CuePix Blinder WW2
    14 Atomic 3000 LED · 15 Unique 2 1

## 15. 0단계 — baseline (구조적 한계를 먼저 적는다)

`server/web/session.py:4942`가 이미 적어 둔 것을 확인했다: **이 저장소의 응답기 경로엔 `Programmer`/`Selection` 판독 별칭이 없다.** DMX 어트리뷰트 값의 「원래대로 돌아왔다」는 이 채널로 **원리적으로 관측 불가**다.

그래서 0단계는 리드가 요구한 그대로 채우지 못했다 — 대신 **가능한 baseline**(픽스처 오브젝트의 `NAME`·`FIXTURETYPE`·`MODE`)을 발사 전/후로 읽어 구조가 안 변했는지만 확인했다. `id` 필드(요청 일련번호)만 다르고 나머지 값은 동일했다.

## 16. 발사 — 원문 그대로, 순서대로

승인 범위대로 정확히 쐈다: 선택 → 발화 → **`Off Fixture 501` 해제**(리드 지시 문형, `ClearAll` 안 씀). `Store`·풀 접촉 없음. 대상 항상 501 하나.

| 단계 | 명령 | 원문 결과 |
|---|---|---|
| select | `Fixture 501` | ok=True, `OK` |
| **prism** | `Attribute 'Prism' At 50` | **ok=False, `Illegal object`** |
| release | `Off Fixture 501` | ok=True, `OK` |
| select | `Fixture 501` | ok=True, `OK` |
| **prism1** | `Attribute 'Prism1' At 50` | **ok=False, `Failed`** |
| release | `Off Fixture 501` | ok=True, `OK` |
| select | `Fixture 501` | ok=True, `OK` |
| **frost** | `Attribute 'Frost' At 50` | **ok=False, `Illegal object`** |
| release | `Off Fixture 501` | ok=True, `OK` |

게이트 심사(`screen`)를 먼저 통과시켰다 — `Off Fixture 501`에 `unverifiable reference` 경고가 붙었지만 **cleared** 로 나왔다(빈 목적지가 아니라 그냥 참조 불확실 표기). 9줄 전부 콘솔까지 갔다 — t66 이 지적한 「게이트 공허」가 아니다.

**M0(2026-07-26, v1.4.1, Group 13 전체 선택)와 판정이 정확히 재현된다** — `Prism1`만 다른 오류 문자열(`Failed`)을 낸다는 것까지 동일하다. **응답기가 v1.6.2로 바뀌었어도, 프리즘을 물리적으로 가진 진짜 무버(Robin MegaPointe)를 단독 선택해서 쏴도 결과가 안 바뀐다.**

## 17. 🔴 원인이 밝혀졌다 — 픽스처 보유 여부가 아니라 철자 불일치다

발사와 별개로, `Patch/FixtureTypes/11`(Robin MegaPointe)의 실제 DMX 채널 정의를 **읽기 전용으로** 끝까지 열었다(승인·발사 아님, 트리 조회):

    Patch/FixtureTypes/11/DMXModes/1/DMXChannels  (Mode 1, 32채널 전량)

관련 채널만 추리면:

    Main Module_ZoomMSpeed
    Main Module_Frost1        <<< "Frost" 가 아니라 "Frost1" 이다
    Main Module_Zoom
    Main Module_Focus1        <<< "Focus" 가 아니라 "Focus1" 이다
    Main Module_Shutter1      <<< "Shutter" 가 아니라 "Shutter1" 이다
    Main Module_Dimmer

**`Prism` 이라는 채널이 이 기종 이 모드에 아예 없다.** 32채널 전량에 프리즘류는 `EFFECTWHEEL`·`EFFECTWHEEL2`·`EFFECTWHEEL3`(로베 명명 관례 — 이펙트 휠이 프리즘을 담을 수도 아닐 수도 있다, 미확인) 뿐이다.

**progress.md:175 의 가설(「픽스처가 그 속성을 안 가져서 거절됐을 수 있다」)은 이 기종에 대해 절반만 맞다** — `Prism`은 실제로 없는 개념이라 거절이 맞다. 그런데 `Frost` 는 있다, **다만 이름이 `Frost1` 이다.** `_PROBE_REJECTED`의 문자열 자체가 실제 MA3 채널명과 어긋난다.

⚠️ **승인 범위 밖이라 `Frost1` 은 안 쐈다.** 리드가 승인한 철자는 `Prism`·`Prism1`·`Frost` 셋뿐이다. 새 철자는 별도 승인이 필요하다고 판단해 여기서 멈췄다.

## 18. 판정 갱신

전제 2(프로브가 낡았다)의 근거를 다시 정정한다. 1·2회차에서 "픽스처 의존적 결과"(progress.md:175)를 근거로 재측정 가치를 주장했는데, **이번 재측정이 그 가설을 반증했다.** 프리즘을 실제로 가진(것으로 기대한) 무버를 단독으로 쐈는데도 같은 판정이 나왔다 — 변수는 픽스처 선택이 아니라 **어트리뷰트 이름 철자**였다.

**Frost는 이제 열 수 있다** — 정확한 철자(`Frost1`)로 재승인 요청. **Prism은 이 기종에 없다** — 다른 기종(Robin MMX Spot 등, 프리즘 보유 여부 미확인)을 찾아야 하거나, BM.03(`좁은 빔+프리즘`, target `MOVER-U`)이 애초에 이 리그의 어떤 기종도 만족 못 시킬 수 있다.

## 19. 안 잰 것 (3회차)

1. **`Frost1` 로 재발사하지 않았다** — 승인 범위 밖. 다음 승인 대상으로 남긴다
2. **Robin MMX Spot(FixtureType 7) 이 프리즘을 갖는지** — DMX 채널을 안 열어봤다. 이 리그 패치에 MMX Spot 이 실제로 물려 있는지도 확인 안 함(patch.csv 고유 기종 목록엔 없었다 — 즉 콘솔의 15종 중 다수는 이 프로젝트 패치가 쓰지 않는 라이브러리 잔존일 수 있다)
3. **EFFECTWHEEL 이 프리즘 등가물인지** — 로베 명명 관례를 확인하지 않았다. 확인하면 BM.03·BM.05 의 처방이 통째로 바뀔 수 있다
4. **다른 무버(MOVER-D 521 = Robin Spiider)** 는 애초에 빔 워시라 프리즘/프로스트 후보가 아니라고 판단해 안 쐈다 — 그 판단 자체를 검증하지 않았다(Spiider 실제 채널 미확인)
5. **여전히 원래 값 복귀를 관측할 채널이 없다** — §15. 이건 이 카드가 못 여는 구조적 한계다

## 20. 잔여 위험

- 3회차 발사 3건은 전부 `Off Fixture 501` 로 해제했지만, **복귀를 확인할 채널이 없어 "정확히 원상태"라고는 단언 못 한다.** 구조 판독(NAME·FIXTURETYPE·MODE)만 불변을 확인했다.
- `Frost1` 로 다시 쏘면 열릴 가능성이 높지만 **아직 실측 아니다** — 채널명이 존재한다는 것과 그 값이 이 모드·이 픽스처에서 받아들여진다는 것은 다른 명제다.
- Patch/FixtureTypes 의 15종 중 이 프로젝트 패치(patch.csv 8종)와 안 겹치는 7종은 **이전 쇼파일의 잔존일 수 있다** — 이 카드에서 그 출처를 확인하지 않았다.
