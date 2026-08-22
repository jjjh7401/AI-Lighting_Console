---
id: SPEC-COPILOT-PARITY-001
type: progress
version: "0.1.0"
created: 2026-08-22
updated: 2026-08-22
author: run 레인 (칸반 카드 t11)
---

# SPEC-COPILOT-PARITY-001 — progress

## §E.2 Run-phase Evidence — M1 (D2 정합)

측정자: run 레인 session 71f784af · 워크트리 `.claude/worktrees/t11-m1` · 브랜치 `WT-handle-to-name`

### M1-0 — 손대기 전 기준선

코드를 한 줄도 고치기 전에 잰 값이다. AC-002·AC-012 가 대조할 기준선은 이것뿐이며,
`progress.md` 에 기록된 옛 수치(`9691` · `9681`)는 기준선으로 쓰지 않았다.

손대지 않았음의 증거 (측정 직전):
```
$ git status --porcelain
(빈 출력 = 추적 파일 변경 0건)
$ git rev-parse HEAD
5c988bd9442a600d17afd9ee47cbe90beaec6780
```

| # | 명령 | 범위 | 출력 원문 |
|---|---|---|---|
| ① | `uv run pytest server/tests -q` | `server/tests` 전량 | `9691 passed, 8 skipped, 1 warning in 153.79s` |
| ② | `npm --prefix ui run test` | `ui/` 20개 파일 | `Test Files 20 passed (20)` · `Tests 496 passed (496)` |

둘 다 커밋 `5c988bd9442a600d17afd9ee47cbe90beaec6780`, 추적 변경 0건 상태.
**순서 정직하게**: ①은 툴체인 설치 전, ②는 후다(`npm --prefix ui ci` → `added 99 packages in 916ms`,
직후 `git status --porcelain` 빈 출력으로 lock 무변경 확인). ①은 python 스위트라 node 의존이 없다.

**기준선 수치의 성격.** ①의 `9691` 은 이 트리에서 직접 잰 값이며, 동시에 예상 회계와 일치한다 —
`9681`(t9 D1 수정 후) `+1`(F4 신규) `+9`(RV1·RV2 신규) `= 9691`. 독립 측정이 회계를 재현한 것이지,
기록된 숫자를 인용한 것이 아니다.

### M1-2 — 수정 전 RED (번역 코드가 존재하지 않는 상태)

```
handle_types=False (기본)  → Counter({'already_patched': 86})
handle_types=True  (D2)    → Counter({'fid_occupied': 86})
AC-003 같은 콘솔 객체:
  트리 열거   {'i': 1, 'name': 'ETC S4 LED S3 Lustr X8', 'class': 'FixtureType'}
  프로퍼티    {'ok': True, 'value': 'FixtureType 1'}
```
트리는 이름, 픽스처 프로퍼티만 핸들 — 실기 갈래와 같다(REQ-PARITY-003). 둘 다 핸들로 바꾸면
과하게 맞춘 것이 되어 재현이 실기와 어긋난다.

### M1-5 — 수정 후 GREEN

```
handle_types=True  → Counter({'already_patched': 86})
handle_types=False → Counter({'already_patched': 86})   (기본값 경로 불변)
occupant.fixture_type: 'FixtureType 1' → 'ETC S4 LED S3 Lustr X8'
```

**「정방향을 넣으면 초록이 된다」가 목표에서 관측으로 바뀌었다.** acceptance.md 앞머리가
「아무도 관측한 적이 없다(Gap 4)」로 못 박아 둔 항목이며, 이 실행이 그 관측을 만들었다.

### M1-5 — 뮤테이션 (D3), 최종 코드 기준 4종 전부 KILLED

설계가 (B) 로 바뀌었으므로 1차 뮤테이션 결과는 폐기하고 최종 코드로 다시 돌렸다.

| 뮤테이션 | 결과 | 죽인 테스트 |
|---|---|---|
| MUT-1 번역기를 항등으로 | KILLED | 통합 1 + 단위 5 |
| MUT-2 표 부재를 조용히 통과 | KILLED | **순서-의존 테스트 1 + AC-009 1** |
| MUT-3 lxseq 가 대응표를 안 넘김 | KILLED | **통합 1건만** |
| MUT-4 슬롯 부재를 조용히 통과 | KILLED | **AC-009 1건만** |

MUT-3·MUT-4 가 각각 **한 건만** 죽인 것이 판별력의 증거다 — 그 테스트가 그 성질의 유일한
판별자라는 뜻이고, 여러 건이 죽었으면 무엇이 무엇을 지키는지 모호했을 것이다.
MUT-1 이 단위 다수를 죽이고 MUT-3 이 통합만 죽인 것도 옳다: **단위는 번역기를, 통합은 배선을
지킨다.** 통과한 뮤테이션은 없다.

복구 증명(초록 아님): `shasum -a 256 -c` 3파일 `OK` (1차) · `grep -c "MUT-"` → `inventory.py:0`,
`tools.py:0` (2차).

### M1-6 — 전체 스위트

| # | 명령 | 범위 | 출력 원문 | 기준선 대비 |
|---|---|---|---|---|
| ① | `uv run pytest server/tests -q` | `server/tests` 전량 | `9703 passed, 8 skipped, 1 warning in 143.52s` | `9691 → 9703` = **+12** |
| ② | `npm --prefix ui run test` | `ui/` 20개 파일 | `Tests 496 passed (496)` | **불변** |

**+12 = 신규 테스트 수와 정확히 일치**(`test_prechk_handle_types.py` 10건 + `test_lxseq_tool.py` 2건).
실패 0. 파라미터화 케이스 수 변화 없음(acceptance.md §E 7번의 예외 경우에 해당하지 않는다).

### 설계 결정 — 판독 공유 (리드 승인)

`read_inventory` 는 타입 트리를 **스스로 읽지 않는다.** 호출자가 대응표를 넘긴다.

**중간 경로였던 「지연 판독」은 폐기했다.** 지연은 이름 경로에서 질의 0 증가라는 이점이 있었으나,
`prechk` 경로에서 **비준된 질의 예산 가드 5건**을 RED 로 만들었다. 저장소에는
「`did_not_grow` 류 테스트는 넓히지 마라는 비준이다 — 넓히지 않는 설계를 먼저 찾아라」는
교훈이 있고, 가드가 RED 인 것은 결함이 아니라 **가드가 자기 일을 한 것**이다. 단정을 넓히는 대신
설계를 바꿨다.

검증: 가드 5건이 **원래 수치 그대로** 초록이다(`test_prechk_tool.py` 77 passed). 넓혀서 통과한
것과 넓히지 않고 통과한 것은 다른 사건이다.

**한정 — (B)가 「모든 곳에서 순증 0」은 아니다.** 말할 수 있는 것은 *깨진 5건이 사는 자리에서
순증 0* 까지다. `read_inventory` 호출 7곳(`tools.py:2680 :2863 :3045 :3678 :4029 :4185 :4519`)
+ `paperwork/data.py:100` = 8곳 중, 트리 판독과 같은 핸들러에 있는 것은 `:2680`/`:2703` 과
`:4510`/`:4519` 둘이다. 나머지 5곳은 **미측정**이다(§E 잔여위험).

### 이 설계가 버리는 검출 능력 (명시)

번역은 **핸들 형식 인식**이 트리거다. 그래서 값이 「알려진 이름도 아니고 핸들도 아닌 제3의 형식」일 때,
이 설계는 그것을 **이름으로 오인해 표식 없이 통과시킨다.** 트리를 항상 읽는 설계라면 트리가 선언한
이름 집합과 대조해 그 경우를 **판별할 수 있었다.**

**결과는 같고 검출은 다르다** — 오늘 알려진 두 형식(이름 · `FixtureType <슬롯>`)에서는 두 설계의
결과가 같지만, 알려지지 않은 제3의 형식에서는 검출이 갈린다. 형식 드리프트를 어디서 잡을 것인가는
이 카드가 닫지 못하고 넘기는 질문이며, **t12(전수조사) 재료**다.

순서 의존도 같은 계열이라 명시했다: 트리를 읽지 않은 경로는 표가 없고, 그때 핸들은
`UNTRANSLATED_NO_TABLE` 로 표시된다 — 조용히 「번역됨」이 되지 않는다. 이 성질은
`test_without_a_table_a_handle_is_marked_not_quietly_accepted` 가 고정하며, MUT-2 가 그것을 죽였다.

### 발견 — 가짜 ↔ 가짜 괴리 (t12 재료)

t11 은 「가짜 ↔ 실물」 괴리를 찾는 카드였는데, M1-6 에서 실제로 잡힌 첫 사례는 **「가짜 ↔ 가짜」** 였다.

관측 원문 (`server/tests/test_prechk_tool.py:38-40`):
```python
1: {"Patch": "1.001", "FixtureType": "FixtureType 1", "Mode": "1 Mode 1", "Name": "MMX 1"},
```
계측 결과 (`read_inventory` 가 `GatedRig` 에서 본 값):
```
fixture_type: ['FixtureType 1', 'FixtureType 1', 'FixtureType 1']
핸들 형식으로 인식: 3/3
```

- **`prechk` 가짜**: `FixtureType <슬롯>` = **핸들** (실물 충실)
- **`lxseq` 가짜**: 타입 **이름** (D2 를 가림)

**두 가짜가 서로 다른 콘솔을 모델링하고 있다.** D2 가 lxseq 에서만 안 보인 이유가 이것이다 —
옆 모듈의 가짜는 진작 옳았다.

[HARD] **관측과 추론을 가른다.** 관측된 것은 위 원문과 계측값이다. 「`Mode`·`Name` 이 실기 캡처값
(MMX = Robe)이므로 **의도적** 모사로 보인다」는 **내 추론이지 관측이 아니다** — 작성자에게 확인하지
않았다.

**t12 재료**: 가짜끼리의 대조는 **실기 없이 오프라인으로 가능한 축**이며, 이번 카드가 그 축을
**한 건 실증했다.** t12 를 「실기 필요」로만 틀 지으면 이 축을 놓친다.

### 규율 기록 — 세 번째 사례가 되지 않은 것

이 카드는 같은 함정을 두 번 겪었다: **B1**(리드가 「`_named_children` 가 쌍을 뽑으니 판독 불필요」로
전제를 건넸고, 추출 코드의 *존재*만 보고 그 출력이 호출자에게 *도달*하는지를 안 봤다) ·
**M-3**(같은 커밋이 다른 문단에서 「툴 경계엔 이미 트리 판독이 있다」로 같은 추론을 반복했다).
둘 다 **다른 사람이 잡았다.**

세 번째가 될 뻔한 것: run 레인이 (B) 를 권하며 「발자국 순회가 이미 같은 경로를 읽는다」고 적었는데,
그 근거는 **가짜 콘솔을 읽은 것**이었다. 보내기 전에 스스로 알아채고 제품 코드를 열어
`tools.py:2680`/`:2703` 과 `:4510`/`:4519` 의 겹침을 확인한 뒤 정정해 보냈다.
`reachability is not justification` — 규율이 사후가 아니라 **사전에** 작동한 사례로 남긴다.

### 변경 파일

| 파일 | 성격 |
|---|---|
| `server/prechk/mode_read.py` | `TypeNameRead` + `read_fixture_type_names` 신설 (질의 1회, 이름을 입력으로 받지 않음 → REQ-PARITY-007 역방향 금지와 충돌 없음) |
| `server/prechk/inventory.py` | `HANDLE_TEXT` · `translate_fixture_type` · `_name_handle_types` · `FixtureRecord.fixture_type_untranslated` · `read_inventory(type_names=…)` |
| `server/orchestrator/tools.py` | lxseq 핸들러가 대응표를 한 번 읽어 판독 경계에 넘긴다 |
| `server/tests/test_lxseq_tool.py` | `FakeConsole(handle_types=…)` + 테스트 2건 |
| `server/tests/test_prechk_handle_types.py` | 신규 · 테스트 10건 |

### 미검증 (이 마일스톤이 재지 않은 것)

1. **콘솔 라이브 0건.** onPC 무접촉. 실기 핸들 형식 재측정, 슬롯 12 판독 전부 안 했다.
2. **`read_inventory` 나머지 5곳**(`:2863 :3045 :3678 :4029 :4185`)의 질의 비용 — 미측정.
3. **제3의 형식 검출** — 위 「버리는 검출 능력」 참조. t12 로 넘긴다.
4. **C2~C13 열두 자리** — M2 의 몫. 이 마일스톤은 손대지 않았다.
5. **`prechk` 가짜의 핸들 값이 의도적인지** — 추론이며 미확인.
6. AC 12건이 전부 통과해도 **실기 D2 가 닫혔다는 증거는 아니다**(acceptance.md §C). 오프라인이
   보증하는 것은 「핸들이 들어오는 갈래에서 코드가 이름으로 번역한다」까지이며, 「실기 콘솔이 실제로
   그 형식의 핸들을 준다」는 가정으로 남는다.


---

## §E.2 (이어서) — M2 번짐 범위 실측 (분류만 · 수정 0건)

측정자: run 레인 · 트리 `t11-m1` · `WT-handle-to-name` · base `aabcdde` · 콘솔 무접촉

[HARD] **이 마일스톤은 아무것도 고치지 않았다.** 어긋남을 발견해도 적기만 했다
(plan.md M2 [HARD]). 제품 코드 변경 0건 — `git diff` 로 확인 가능.

### 판정 기준 — 「호출을 봤나, 결과를 봤나」

각 행마다 자문했다. **호출의 존재만 본 행은 「미측정」이다.** 이 카드에서 같은 함정이
네 번 나왔으므로(B1 · M-3 · run 레인의 (B) 근거 · 리드의 footprint 근거), 표를 채우는
일 자체가 그 함정에 걸리기 쉽다. **미측정이 많은 표는 부실한 표가 아니라 정직한 표다.**

### 선행 측정 — 대응표를 넘기는 호출 지점은 8곳 중 1곳

```
$ grep -rn "read_inventory(" server/ --include=*.py | grep -v /tests/ | grep -v "def read_inventory"
server/paperwork/data.py:100      read_inventory(port, policy)
server/orchestrator/tools.py:2680 read_inventory(_InventoryPort(...))
server/orchestrator/tools.py:2863 read_inventory(_InventoryPort(...))
server/orchestrator/tools.py:3045 read_inventory(inventory_port)
server/orchestrator/tools.py:3678 read_inventory(_InventoryPort(...))
server/orchestrator/tools.py:4029 read_inventory(_InventoryPort(...))
server/orchestrator/tools.py:4185 read_inventory(_InventoryPort(...))
server/orchestrator/tools.py:4524 read_inventory(inventory_port, type_names=type_names)   <- 유일
```
**`:4524`(lxseq 핸들러) 하나만 대응표를 넘긴다.** 나머지 7곳은 번역 없이 핸들을 그대로
하류에 보낸다. 이것이 「A-1 이 무엇을 닫았고 무엇이 열려 있는가」를 가르는 사실이며,
인자 목록이라 추론이 아니라 구문적 사실이다.

### 분류표 — C1~C13

| # | 자리 | 판정 | 측정 | 근거 |
|---|---|---|---|---|
| C1 | `lxseq/mapper.py:325` | 어긋났다 → **닫힘** | **측정됨** | M1 통합 테스트. 번역 전 `Counter({'fid_occupied': 86})` → 후 `Counter({'already_patched': 86})` |
| C2 | `vwx/apply.py:503` | **어긋나지 않는다** | **측정됨** | `_resolve_library_type("FixtureType 4", lib)` → `Robin Spiider` — 이름 입력과 **같은 결과**. 이 함수는 `_TYPE_DISPLAY_INDEX = ^FixtureType (\d+)$`(`apply.py:444`)로 **핸들 형태를 이미 처리한다** |
| C3 | `vwx/diff.py:113` | **어긋난다** | **측정됨** | `fuzzy_type_equal("Source 4 LED", "FixtureType 10")` → `False` (이름이면 `True`). `diff.py:179` 가 이 대조로 `console_count` 를 정하므로 **전 타입이 `console_count=0` → 거짓 QuantityMismatch** |
| C4 | `paperwork/data.py:108` | **어긋난다(운반)** | **측정됨** | `build_patch_sheet` 를 실제 포트로 실행 → 행에 `fixture_type='FixtureType 10'` 그대로 |
| C5 | `paperwork/render.py:87` | **어긋난다(인쇄)** | **측정됨** | `render_patch_sheet` 실행 → `<td>` 셀 `['1','KEY 101','1','1','FixtureType 10','Mode 1']`. **사람이 읽는 서류에 핸들이 인쇄된다** |
| C6 | `tools.py:3734` | 표시 통과로 보인다 | **미측정** | 운반자 C11 은 측정됐다(핸들 그대로). 그러나 **이 줄은 핸들러를 실행해 페이로드를 관측하지 않았다** — 딕셔너리 리터럴을 읽었을 뿐이다 |
| C7 | `prechk/patch.py:236` | 표시 통과로 보인다 | **미측정** | 같은 형태. `to_dict()` 를 실행하지 않았다 |
| C8 | `prechk/patch.py:714` | **무관** | **측정됨** | 널 검사뿐 — 핸들·이름 모두 `type_mode_ok=True`, `None` 만 `False` |
| C9 | `lxseq/mapper.py:317` | 어긋났다 → **닫힘** | **측정됨** | M1 테스트가 `occupant["fixture_type"]` 이 이름임을 단언. 번역 전 실측값은 `'FixtureType 1'` |
| C10 | `vwx/apply.py:510` | 표시는 핸들, **판정은 정상** | **측정됨** | `read_console_fixtures` 실행 → `type_display='FixtureType 10'` 이나 `type_name='Source 4 LED'`(C2 가 해석) |
| C11 | `tools.py:3683` | **무관(판정)** | **측정됨** | 핸들 점유와 이름 점유의 `evaluate` 판정이 동일(`ok=False, hits=1`). `fixture_type` 은 충돌 판정에 참여하지 않는다 |
| C12 | `tools.py:4034` | **무관(판정)** | **측정됨** | 같은 `evaluate` 경로. 페이로드는 `f"{universe}.{address}"` 만 낸다 |
| C13 | `tools.py:4193` | **무관(버려짐)** | **측정됨** | `seats` 가 `(universe, address)` 만 추출 — `fixture_type` 은 **소비 지점에서 버려진다** |

**집계**: 측정됨 11 · 미측정 2(C6 · C7). 어긋남 3(C3 · C4 · C5) · 닫힘 2(C1 · C9) ·
무관 **6**(C2 · C8 · C10판정 · C11 · C12 · C13) · 표시상 핸들 노출 3(C6 · C7 · C10).
검산: 어긋남 3 + 닫힘 2 + 무관 6 = 11 = 측정됨. **정정(감사 D-3)** — 첫 판은 이름
여섯을 들면서 「5」로 적었다. 바로 다음 절 A-1 표도 여섯을 들며, 여섯이 옳다.

### A-1 이 닫은 것과 열어 둔 것 — 측정으로 가른다

| | 자리 | 근거 |
|---|---|---|
| **닫혔다** | C1 · C9 | lxseq 경로(`:4524`)가 유일하게 대응표를 넘긴다. M1 테스트가 관측 |
| **열려 있다** | C3 · C4 · C5 | 각각의 `read_inventory` 가 대응표를 안 넘기고(위 grep), 핸들을 받으면 어긋남을 측정했다 |
| **닫을 필요가 없다** | C2 · C8 · C10 · C11 · C12 · C13 | 핸들이 와도 결과가 갈리지 않음을 측정했다 |

**리드의 C11~C13 관측은 참으로 확인됐다** — 「양쪽이 다 핸들이면 성립할 수도 있다」는
가설이었고, 측정 결과 **더 강한 이유로 성립한다**: 그 경로들은 애초에 `fixture_type` 을
판정에 쓰지 않는다(C13 은 아예 버린다). 「양쪽이 핸들이라 우연히 맞는」 것이 아니라
**그 축을 보지 않는다.**

### O-6 — D2 의 잔여로 오분류하지 않는다

`lxseq/mapper.py` 는 라이브러리 해석이 present 가 아니면 `console_types[csv_type] = None`
로 둔다(원문 확인: `console_types[csv_type] = resolution.get("resolved") or csv_type` /
`console_types[csv_type] = None` 두 갈래). 그러면 `:325` 의 비교는 **번역 후에도**
「이름 == None」이라 거짓이다. 이것은 **D2 와 다른 원인**이며 이 카드가 결함으로 단정하지
않는다. C1 에서 「번역했는데도 안 뒤집힌다」가 관측되면 **먼저 이 갈래인지 확인할 것.**

### 부수 관측 — 같은 정규식이 두 곳에 따로 있다 (고치지 않았다)

```
server/vwx/apply.py:444        _TYPE_DISPLAY_INDEX = re.compile(r"^FixtureType (\d+)$")
server/prechk/inventory.py     HANDLE_TEXT         = re.compile(r"^FixtureType (\d+)$")
```
**바이트 동일하다.** vwx 는 이 형태를 진작 알고 있었고, prechk/lxseq 는 몰랐다 —
§E.2 의 「가짜↔가짜」 발견과 같은 계열의 **모듈 간 지식 불균형**이다. 형식이 드리프트하면
두 곳을 따로 고쳐야 하며 한쪽만 고치면 조용히 갈린다. **M2 는 분류 마일스톤이므로 고치지
않았다** — 후속 재료로 남긴다.

### M2 가 재지 않은 것

1. **C6 · C7** — 핸들러/`to_dict()` 를 실행하지 않았다. 운반자는 측정됐으나 출력은 아니다.
   **정정(감사)**: 이 둘을 「옳은 미측정」으로 수식하지 않는다. `acceptance.md` AC-011 의
   허용은 「**오프라인으로 결론이 안 나는 자리**」라는 조건부인데, C6 · C7 은 오프라인
   측정이 **가능하고** 이 문서 자신이 「실행하지 않았다」고 적었다. **「안 잰 것」이다.**
2. **콘솔 라이브 0건.** 위 전부 오프라인 측정이다.
3. **C3 의 실제 사용자 영향** — 거짓 QuantityMismatch 가 나는 것은 측정했으나, 그 리포트를
   조명감독이 어떻게 읽고 무엇을 하는지는 재지 않았다.
4. **어긋남 3건(C3·C4·C5)의 수정** — 범위 밖(plan.md M2 [HARD]). 후속 카드 재료다.
5. **`read_inventory` 나머지 5곳 순증** — M1 에서 남긴 미검증 그대로.
6. **AC 12건이 전부 통과해도 실기 D2 가 닫혔다는 증거는 아니다**(acceptance §C).
   오프라인이 보증하는 것은 「핸들 갈래에서 코드가 이름으로 번역한다」까지이며,
   「실기 콘솔이 실제로 그 형식의 핸들을 준다」는 가정으로 남는다. **sync 가 이 문장을
   지우면 「AC 전건 통과」가 「실기 결함 해소」로 읽힌다.**


---

## §E.4 Sync-phase Audit-Ready Signal

sync_commit_sha: d6b1c49
측정자: run 레인 (sync 단계) · 트리 `t11-m1` · `WT-handle-to-name` · base `581a1fb`

**M1·M2 의 증거는 §E.2 에 있다 — 여기 옮겨 적지 않고 가리킨다.** 이 절은 sync 가
**자기 손으로 잰 것만** 담는다.

### sync 가 직접 잰 것

| # | 명령 | 범위 | 출력 원문 | 판정 |
|---|---|---|---|---|
| S1 | `uv run pytest server/tests -q` | `server/tests` 전량 | `9703 passed, 8 skipped, 1 warning in 144.64s` | 실패 0 |
| S2 | `git diff --stat 5c988bd..581a1fb -- console/lua server/safety server/vwx server/paperwork server/rulebook/assets ui` | 봉쇄 구역 | **빈 출력** | 0-diff |
| S3 | `git diff --stat 5c988bd..581a1fb -- server/` | 변경 범위 | 5파일 · `+450 / -5` | 아래 표 |
| S4 | `uv run pytest server/tests --cov=server.prechk` | `server/prechk` | `inventory.py 215 2 99%` · `mode_read.py 97 16 84%` · `TOTAL 1120 39 97%` | 아래 단서 |
| S5 | `grep -c "SPEC-COPILOT-PARITY-001" CHANGELOG.md` (기입 전) | 중복 방지 | `0` | 중복 없음 |

**기준선은 `9703`**(M1-6, §E.2). `9691` 은 M1-0 손대기 전 기준선이고 `9681`·`9682` 는
다른 카드의 값이다 — 이 절에서 인용하지 않는다.

### S3 변경 범위 — plan.md D4 대조

| 파일 | D4 예상 | 실제 | 사유 |
|---|---|---|---|
| `server/prechk/inventory.py` | ✅ 예상됨 | 변경 | A-1 판독 경계 |
| `server/tests/*` | ✅ 예상됨 | 변경 2 | 테스트 |
| `server/prechk/mode_read.py` | D4 문면엔 없음 | 변경 | plan.md M1-3 이 「신설 판독」을 지시했고 §A.4 근거 4 가 `_named_children` 소재를 근거로 들었다 — **계획 의도 안, D4 문면 밖** |
| `server/orchestrator/tools.py` | D4 문면엔 없음 | 변경 (+9/-2) | (B) 판독 공유 결정의 귀결 — 호출자가 대응표를 넘겨야 한다 |

**D4 를 문면 그대로 읽으면 2파일 초과다.** 숨기지 않고 적는다: 두 파일 모두 계획·결정이
지시한 것이나 **D4 문장 자체는 갱신되지 않았다.** sync 가 임의로 D4 를 고치지 않는다
(`acceptance.md` 는 manager-spec 소유).

### S4 커버리지 — 내 신설 코드에 미검사 갈래 2건

`mode_read.py` 84% 는 모듈 전체 값이고 미검사 줄 대부분은 **기존** `read_type_mode_widths`
(157~205)다. 그러나 **`127` · `130` 은 이번에 내가 추가한 `read_fixture_type_names` 안이다**:

- `:127` — 트리 판독이 `ok: false` 로 답한 갈래
- `:130` — 자식에 슬롯/이름이 없는(형태 불량) 갈래

당시 내 테스트는 예외 발생 갈래(`:124-125`)와 정상·절단 갈래만 덮었고 **두 갈래가
미검사였다.** sync 배차가 「제품 코드 수정 0건」이라 그 자리에서 추가하지 않고 보고했다.
`inventory.py` 는 99%(미검사 `264` · `486` 은 이번 변경과 무관).

#### 정정 — 두 갈래는 닫혔다 (sync 후속 · 리드 예외 승인)

리드가 「이번 카드가 새로 쓴 코드이므로 지금 닫아라, 단 테스트 파일만」으로 예외를 줬다.
`mode_read.py` **본문은 건드리지 않았다**(복구 대조: `shasum -a 256` 이 뮤테이션 전후
`8fac1096…7871` 동일 · `git diff --stat -- server/prechk server/orchestrator ui` 빈 출력).

| 갈래 | 신규 테스트 | 뮤테이션 | 결과 |
|---|---|---|---|
| `:127` 트리가 `ok:false` 로 거절 | `test_a_refusing_tree_is_attempted_false_and_names_nothing` | `attempted=False` → `True` | **KILLED**(해당 1건만) |
| `:130` 자식 형태 불량 | `test_a_malformed_child_is_attempted_true_and_still_names_nothing` | `attempted=True` → `False` | **KILLED**(해당 1건만) |

두 테스트는 결과(이름 0건)가 같은 두 갈래를 **`attempted` 로 가른다** — 「응답이 없다」와
「응답이 이상하다」는 다른 사건이고, 전자는 재시도할 자리이고 후자는 아니다. 뮤테이션이
각각 자기 테스트 **한 건만** 죽인 것이 그 구분의 판별력을 보인다.

커버리지: `mode_read.py 97 13 87%` — 남은 미검사 `68` · `157-205` 는 **전부 기존
`_named_children` · `read_type_mode_widths`** 이며 이번 카드가 추가한 줄은 **0건 미검사**다.
전체 스위트 `9705 passed, 8 skipped` — 기준선 `9703` 대비 **+2 = 신규 테스트 수 일치**.

### 문서 정합

| 산출물 | 상태 |
|---|---|
| `CHANGELOG.md` | `[Unreleased] > Added` 에 1건 추가. 리드가 [HARD] 로 지목한 3건 전부 포함 — 「AC 전건 통과 ≠ 실기 D2 해소」 · 어긋남 3건(특히 diff 거짓 경보를 「콘솔에 아무것도 없다로 읽힌다」까지) · 「테스트 CI 없음」 |
| `README.md` | D2 를 「known gap remains」 → 「**offline** 로 닫힘, **콘솔 재검증 안 됨**」으로 정정하고, 아직 미번역인 두 소비자(diff 수량 대조 · 패치 시트 인쇄)를 명시 |
| `progress.md` | §E.2(M1·M2) + 이 절 |

### sync 가 재지 않은 것

1. **콘솔 라이브 0건.** sync 도 onPC 에 접속하지 않았다.
2. ~~`mode_read.py:127 · :130`~~ — **닫혔다**(위 「정정」 참조). 남은 미검사 줄은 전부
   이번 카드 밖의 기존 코드다.
3. **어긋남 3건이 「표를 넘기면 함께 닫히는가」** — 원인이 하나로 보이나 **측정 안 했다**.
4. **C6 · C7 출력** — M2 미측정 그대로.
5. **`read_inventory` 나머지 5곳 질의 순증** — M1 미검증 그대로.
6. **신설 판독이 정말 「얇은」지** — 감사가 남긴 항목, 재지 않았다.
7. [HARD] **AC 전건 통과가 실기 D2 해소의 증거가 아니다**(`acceptance.md` §C).
   오프라인이 보증하는 것은 「핸들이 들어오는 갈래에서 코드가 이름으로 번역한다」까지이며,
   「실기 콘솔이 실제로 그 형식의 핸들을 준다」는 **가정**으로 남는다.

### 후속 카드 재료 (제안만 — 큐는 건드리지 않았다)

1. **어긋남 3건 수정** — `vwx/diff.py` 수량 대조 · `paperwork` 서류 2자리. 원인이 하나
   (대응표 미공급 경로)일 가능성이 있으나 **측정되지 않았다.** 특히 diff 거짓 경보는
   감독이 읽는 화면이라 우선순위가 높다.
2. **정규식 이중화 통합** — `vwx/apply.py:444` 와 `prechk/inventory.py` 의
   `^FixtureType (\d+)$` 가 바이트 동일. 형식이 드리프트하면 두 곳을 따로 고쳐야 하고
   한쪽만 고치면 조용히 갈린다.
3. **C6 · C7 출력 관측**. (`mode_read.py` 미검사 갈래 2건은 sync 후속에서 닫혔다.)
4. **실기 핸들 형식 재측정** — 오프라인 AC 로는 닫을 수 없는 유일한 축.


---

## §E.4 (이어서) — sync-audit 지적 처분

감사: `origin/WT-parity-sync-audit` `0c49c39` · PASS-WITH-DEBT 0.86. 아래 넷을 닫았다.

### D-1 (주요) — 판독 실패가 리그 사실로 보고되던 자리

감사가 거절 리더로 재현했고 **나도 재현했다**:
```
read_fixture_type_names(ok:false 리더)  →  attempted=False · by_slot()={} · is None: False
수정 전 translate(그 표)                →  ('FixtureType 4', 'slot_absent')      ← 틀림
```

원인은 **`by_slot()` 이 `attempted` 를 버리는 한 걸음**이다. 트리가 답하지 않아 빈 표가
된 것과 트리가 답했는데 그 슬롯이 없는 것이 **똑같은 빈 dict** 로 도착하므로, 표만 받은
호출자는 이미 구분을 잃은 뒤다. `TypeNameRead` 주석이 이 상태를 예고했다 —
*"a caller that conflates them would report a read failure as slot absent."*

**고친 방식**: 판독 경계가 **표가 아니라 판독 결과(`TypeNameRead`)를 받는다.** 구분을
잃는 것을 **표현할 수 없게** 만든 것이지, 잃지 않도록 주의하게 만든 것이 아니다.

사유는 셋으로 갈랐다 — `no_type_table`(호출자가 안 읽었다 · 순서 결함) ·
`type_tree_unreadable`(읽었으나 답이 없다 · 재조회할 자리) · `slot_absent`(리그 사실).

**뮤테이션 MUT-C**(`attempted` 가드 무력화) → `test_an_unreadable_tree_is_not_reported_as_a_rig_fact`
**1건만** RED. 복구 `shasum` 대조.

### D-1 자체 점검에서 찾은 넷째 갈래 — 절단

리드가 「네 수정이 새 자리를 열지 않는지 스스로 보고 커밋해라」(v0.1.2 M-3 전례)라고 했다.
보니 **열려 있었다**: 셋으로 가른 판에서도 **절단된 목록**에서 안 보인 슬롯이
`slot_absent` 로 나갔다. 그것은 **부정 결론**이고, 이 저장소는 이미
「절단이 무효화하는 것은 부정 결론뿐이다」를 규약으로 갖고 있다(결함 D1 계열).

```
절단 판독 → attempted=True · pairs=((10, 'Source 4 LED'),) · truncated=True
수정 전  → slot_absent            ← 「없다」로 단정
수정 후  → slot_unseen_truncated_listing
```
`TypeNameRead.truncated` 를 노출하고 사유를 넷째로 갈랐다.
**뮤테이션 MUT-D**(절단 가드 무력화) → `test_a_slot_missing_from_a_truncated_listing_is_unseen_not_absent`
**1건만** RED. 복구 `shasum` 대조(`4209be1c…731d`).

**이 건은 감사가 지적한 것이 아니라 감사 지적을 고치다 내가 찾은 것**이며, 리드의
「새 자리를 여는지 보라」가 실제로 한 건 잡았다.

### D-2 (경미) — CHANGELOG 수치

출하 HEAD 기준으로 다시 재서 갱신했다. `9703 / +12` → **`9707 / +16`**
(M1 12 + 오류 갈래 2 + D-1 회귀 1 + 절단 회귀 1). 커버리지도 `1130 36 97%` 로 갱신.
**출하 직전 실측값이며, 앞선 커밋의 수치를 이월하지 않았다.**

### D-3 (경미) — M2 집계

「무관 5」인데 이름이 여섯이었다. **6 이 옳다**(검산 3+2+6=11=측정됨). 정정하고 검산식을
본문에 실었다.

### AC-011 수식 — 「옳은 결과」를 뗐다

`acceptance.md` 의 허용은 「**오프라인으로 결론이 안 나는 자리**」라는 조건부인데
C6 · C7 은 오프라인 측정이 가능하다. **「옳은 미측정」이 아니라 「안 잰 것」**으로 고쳤다.

### sync-audit 후 재측정

| 명령 | 출력 |
|---|---|
| `uv run pytest server/tests -q` | `9707 passed, 8 skipped, 1 warning in 143.06s` |

기준선 `9691`(M1-0) 대비 **+16 = 신규 테스트 수 일치**. 실패 0.

### 이 정정이 재지 않은 것

- **감사의 완화 가설**(`:4510` 이 같은 트리를 먼저 읽어 D-1 이 실기에서 가려질 가능성) —
  **감사도 재지 않았고 나도 재지 않았다.** 등급 근거로 쓰이지 않았다.
- `spec.md` §A.4 의 「A-1 이 C1~C13 을 동시 해결한다」 표제 — **손대지 않았다**(소유 경계,
  `plan` 레인 배차).


---

## §E.4 (이어서) — 재감사 지적 처분 (N-1 · N-2)

재감사: `origin/WT-parity-sync-audit` **`8c8aaba`** · PASS-WITH-DEBT **0.90**(1차 0.86).

### N-1 (주요) — 형태 불량이 리그 사실로 나가던 자리

**재현 먼저 했다**(Rule 4). 테스트를 세우고 RED 를 관측한 뒤 고쳤다:
```
형태 불량 응답 {"ok": True, "children": [{"i": 1, "name": 123}]}
  판독기  → attempted=True · truncated=False · pairs=()
  수정 전 → slot_absent              ← RED 관측
  수정 후 → listing_shape_invalid
```

`slot_absent` 의 계약은 「**전수** 답했고 그 슬롯을 선언하지 않는다 — 리그 사실이며
재조회해도 같다」다. 형태 불량은 **「전수 답했다」를 만족하지 않는다.** 지시되는 행동이
틀리고, 고칠 곳은 리그가 아니라 **판독 쪽**이다.

**같은 계열의 세 번째다** — D-1(판독 실패→리그 사실) · 절단(못 봄→리그 사실) ·
N-1(형태 불량→리그 사실). 셋 다 「목록을 믿을 수 없다」를 「리그 사실」로 뭉갠 것이다.

**판독기 분류는 건드리지 않았다.** 「응답이 없다」와 「응답이 이상하다」를 가른 것은 이
카드가 세운 doctrine 이고 `fc37abc` 테스트가 고정하고 있다 — `TypeNameRead.shape_invalid`
를 노출해 **하류 사유만** 늘렸다.

**뮤테이션 양방향**:

| 뮤테이션 | 죽인 것 |
|---|---|
| MUT-E 형태-불량 가드 제거 | `test_a_malformed_listing_is_not_reported_as_a_rig_fact` **1건만** |
| MUT-F 다섯째 사유를 모든 경우에 적용(과잉) | **3건** — 그중 `test_an_empty_library_is_still_a_rig_fact` |

**MUT-F 를 대조군이 잡은 것이 핵심이다.** 대조군이 없으면 다섯째가 넷째를 잡아먹어도
초록이다. 복구: `shasum -a 256` `ee028bee…b522` 대조 · `grep -c "MUT-"` → `0`.

### [HARD] 정지 조건 — 여섯째는 만들지 않는다

현재 열거는 **감사가 배선 7갈래를 실측한 것**에 근거한다. 「있을 것 같다」로 늘리지
않는다. 새로 **측정된** 갈래가 나오면 그때 새 카드다. 이 문장을 코드 주석에도 남겼다.

### N-2 (경미) — 수치가 한 층 옮겨갔다

CHANGELOG 항목 **제목**이 「세 갈래」인데 **본문**은 「넷」이었다. 감사 표현 그대로 —
**「이 커밋의 임무 하나가 낡은 수치 정정(D-2)이었는데, 그 작업을 서술하는 바로 그 문단이
새 낡은 수치를 남겼다.」** 제목 · 본문 · 상수 개수를 **다섯**으로 한 번에 맞췄고,
`grep -o … | sort | uniq -c` 로 다섯 상수가 각각 실재함을 확인했다.

### 재측정 (출하 HEAD 실측 · 이월 없음)

| 명령 | 출력 |
|---|---|
| `uv run pytest server/tests -q` | `9709 passed, 8 skipped, 1 warning in 143.25s` |
| `--cov=server.prechk` | `TOTAL 1141 36 97%` |

기준선 `9691`(M1-0) 대비 **+18 = 신규 테스트 수 일치**(M1 12 + 오류 갈래 2 + D-1 1 +
절단 1 + N-1 1 + 대조군 1). 실패 0.

### 이 정정이 재지 않은 것

- **N-1 의 실기 도달성** — 실기 콘솔이 형태 불량 응답을 실제로 내는지 **감사도 나도 재지
  않았다.** 오프라인에서 도달 가능한 갈래임은 측정됐다.
- **감사의 완화 가설**(`:4510` 선행 판독) — 여전히 미측정.
- **`spec.md`** — `plan` 레인이 v0.1.4(`f816973`)로 닫았다. 손대지 않았다.
