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
