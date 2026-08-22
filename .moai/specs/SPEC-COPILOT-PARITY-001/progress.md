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


---

## §E.4 (이어서) — X-1 병합과 3-phase close

3차 감사 **PASS 0.92**(0.86 → 0.90 → 0.92). 차단 1건(X-1)만 남아 있었고 그것을 닫았다.

### X-1 — 같은 카드가 두 브랜치로 갈려 있었다

`completed` 스탬프가 찍히는 `spec.md` 가 **plan 브랜치에만** 정정돼 있었다. 그대로 찍었으면
감사 O-3 지적 문면(「C1~C13 동시 해결」)을 **안은 채** 닫혔다 — 고쳤는데 닫는 파일에는
없는 상태다. 배차 조율에서 열린 자리이며, **코드가 아니라 순서에서 열렸다**는 점이
앞의 두 건(M-3 · 절단)과 다르다.

`cherry-pick` 이 아니라 `merge --no-ff` 로 가져왔다 — 두 갈래의 이력이 남아야 나중에
「왜 두 브랜치였나」가 읽힌다.

**frontmatter 충돌은 섞어서 해소**: `version: "0.1.4"`(plan 쪽 — 정정이 더 뒤다) +
`status`(run 쪽 — 구현이 끝났다).

### 병합이 내용을 잃지 않았음의 증명

「충돌 없이 됐다」는 증거가 아니므로 넷을 확인했다:

| 확인 | 결과 |
|---|---|
| `git diff origin/WT-fake-real-parity -- spec.md` | **`status` 한 줄만** 다르다 |
| `git diff origin/WT-fake-real-parity -- plan.md acceptance.md` | **빈 출력** (plan 판본 그대로) |
| O-3 정정 본문 · HISTORY 0.1.3 / 0.1.4 | `:129` `[정정 v0.1.4]` 실재 · HISTORY 2행 실재 |
| 충돌 표식 잔재 | SPEC 4파일 모두 `0` |
| 전체 스위트 | `9709 passed, 8 skipped` — **불변**. 문서 병합이라 불변이 정상이고, **불변인 것도 관측이다** |

### 감사가 결함으로 올리지 않은 관찰 둘 (기록만)

1. **`slot_unseen_truncated_listing` 의 이름이 실제 집합보다 좁다.** `node` 없음 ·
   `children` 없음 · `childCount` 가 문자열인 경우도 이 사유로 온다. 실제 뜻은 「절단」보다
   **「전수임을 확인할 수 없음」**에 가깝다. **행동은 전부 옳다** — 어느 경우도 리그 편집으로
   보내지 않는다. D-1 · N-1 계열과 **반대 방향의 안전한 부정확**이다. 근거인
   `_listing_is_whole` 이 공유 술어라 이름을 바꾸면 이용자 전부를 건드리므로 **바꾸지 않는다.**
2. `shape_invalid` 와 `truncated` 는 동시에 참일 수 없어(형태 불량은 절단 계산 전에 반환)
   우선순위 분기가 도달 불가다. **결함 아니며 우선순위 선택도 옳다.**

### 감사가 남긴 정직한 한 줄 (지우지 않는다)

> **이번엔 이 계열의 네 번째가 안 나왔다 — 다만 그게 「없다」의 증거는 아니다.
> 내가 돌린 게 7형태라는 뜻이다.**

### 3-phase close

`status: implemented → completed`. 전이 트리거는 **리드가 읽은 3차 감사 판정**이며,
run 레인이 자기 문서를 자기 판정으로 닫지 않았다.

**닫히지 않은 채 출하되는 것**(sync 가 지우면 안 되는 것):
AC 전건 통과 ≠ 실기 D2 해소 · 번짐 3건(C3 diff 거짓 경보 · C4 · C5 서류 인쇄) ·
C6 · C7 미측정 · N-1 실기 도달성 미측정 · `read_inventory` 나머지 5곳 순증 미측정.


---

## §E.2 (이어서) — `/code-review` 지적 처분 · `completed` 되돌림

**`completed` 를 되돌렸다**(`completed → in-progress`, 감독 결정). 감사 5회가 통과시킨
뒤 코드 리뷰가 HIGH 1건을 잡았고, 그 결함은 **감사가 비준한 테스트가 지키고 있었다.**

### 🔴 #1 — 빈 목록을 「전수 답했다」로 읽던 자리 (형제 모듈 원문 대조)

**인용을 받지 않고 원문을 읽었다.** `server/prechk/footprint.py:317-331` 13줄 주석:

> A listing that reports zero children is INDISTINGUISHABLE from one whose
> children could not be read: the responder's ``safe_children`` returns an empty
> table when both ``Children()`` and ``Count()`` fail, and then ``childCount``
> is derived from that same empty read — so ``childCount == len(children) == 0``
> and ``truncated`` is unset. ``_listing_is_whole`` therefore says "whole".

`console/lua/copilot_responder.lua:461-475` 에서 그 기제도 확인했다(`Children()` 실패 시
`Count()` 폴백, 둘 다 실패하면 빈 표).

**형제 순회는 이 경우 `whole = False` 를 강제하는데 내 판독은 안 했다.** 결과:
콘솔이 타입 트리 판독에 실패하면 `attempted=True · 전수 · 형태 정상` → **`slot_absent`**
→ 계약이 「answered IN FULL … a rig fact — retrying changes nothing」이다.
**86대 전부가 「리그 사실」로 나가고 감독은 리그를 손보러 간다.**

**비준된 테스트를 뒤집었다.** `test_an_empty_library_is_still_a_rig_fact` 는 내가 MUT-F
판별력의 증거로 든 대조군이고 `sync` 가 독립 확인한 것이다. 뒤집는 근거는 취향이 아니라
**형제 모듈이 같은 페이로드에 정반대 판정을 내리고 그 이유를 주석에 적어 뒀다**는 사실이다.
두 모듈이 같은 페이로드에 다른 답을 내면 그것이 다음 결함이므로 **맞췄다.**

### 🟡 #2 — 자식 하나가 나쁘면 리그 전체 번역이 꺼지던 자리

**PROTOCOL.md 원문을 읽었다**(리드가 인용만 옮기고 재현하지 않았다고 밝혔다).
`console/lua/PROTOCOL.md:52-58`(응답기 1.2.0 개정 노트):

> the snapshot child `i` is now the **real pool slot** and is **omitted** when
> that slot could not be established … `i` becomes optional — the server already
> degrades an `i`-less child to a name-only rig-context entry

**자식별 격하가 established 관례**이며 `:199-204` 가 서버 측 처리를 다시 명시한다.
`_named_children` 의 전부-아니면-전무는 그 관례와 어긋났고, 슬롯 미확정 타입이 **하나만**
있어도 리그 전체 번역이 꺼져 **D2 가 조용히 재발**한다(#3 때문에 경고도 없이).

고친 방식: 쓸 수 있는 쌍은 살리고, **버린 자식이 있으면 목록을 부분집합으로 표시**한다 —
긍정 증거(도착한 쌍)는 번역하고 부정 결론(그 슬롯은 없다)만 보류한다.

### 세 갈래를 한 플래그로 합쳤다 — 이름도 고쳤다

`truncated` → **`whole_unconfirmed`**, `slot_unseen_truncated_listing` →
**`slot_unseen_listing_unconfirmed`**. 절단 · 빈 목록 · 부분집합 셋 다 **「전수임을 확인할
수 없음」**이고 **결과가 같다**(부정 결론 보류).

리드가 앞서 「이름이 실제 집합보다 좁다 — 다만 `_listing_is_whole` 이 공유 술어라
바꾸지 마라」고 했었다. **바꾼 것은 공유 술어가 아니라 이번 카드가 만든 내 상수·필드뿐**이며,
집합이 실제로 더 커졌으므로(빈 목록 · 부분집합이 합류) 옛 이름은 이제 **틀린 라벨**이다.
공유 술어 `_listing_is_whole` 은 **손대지 않았다.**

**사유는 여전히 다섯이다** — 여섯째를 만들지 않았다(리드 [HARD] 정지 조건).

### 🟡 #3 — 다섯 사유가 감독에게 도달하지 않던 자리

```
$ git grep -n fixture_type_untranslated -- server/ | grep -v /tests/
inventory.py:291  정의
inventory.py:499  기록
                  ← 읽는 곳 0
```
사유를 다섯으로 가르는 데 감사 세 라운드를 썼는데 **화면에 안 나왔다.** 판독이 실패하면
툴은 수정 전과 **똑같이** 86행 `fid_occupied` 를 내보내고 신호가 없다 — 그 침묵이 이
카드가 고치려는 결함과 같은 모양이다.

페이로드 `console_read.type_translation` 에 실었다: `attempted` · `named` ·
`whole_unconfirmed` · **`untranslated`(사유별 건수)** · `detail`. 상위 키 집합
(AC-LXSEQ-014 닫힌 페이로드)은 **불변** — `console_read` 하위에 넣었다.

### LOW 3건

| # | 처분 |
|---|---|
| #4 `rig_paths["fixture_types"]` 무조건 인덱싱 | **고침** — 형제 툴(`:2689` · `:2723` · `:4757`)과 같은 `in` 가드. 경로가 없으면 번역만 포기하고 계획은 낸다(전엔 `KeyError` 가 툴 밖으로 나갔다) |
| #6 `FIXTURE_TYPES_ROOT` 미사용 | **제거** — 배선된 것처럼 읽힌다. 경로는 호출자가 `rig_paths` 로 준다 |
| #5 핸들 형태 우선 번역 · 정규식 이중화 | **기록만.** `vwx/apply.py:520-535` 는 「이름이면서 핸들 형태」인 모호성을 **거부**하는데 내 번역기는 핸들 해석을 우선한다. 오늘 관측된 형식에서는 결과가 같으나 **판단이 다르다.** 정규식 바이트 동일 중복도 그대로 — 둘 다 후속 재료 |

### 뮤테이션 (비준 테스트를 뒤집었으므로 특히)

| 뮤테이션 | 죽인 것 |
|---|---|
| MUT-G 빈 목록을 다시 「전수」로 | `test_an_empty_listing_is_not_a_rig_fact` **1건만** |
| MUT-H 자식 전부-아니면-전무로 되돌림 | **2건** (형태 불량 · 슬롯 미확정 격하) |
| MUT-J 사유를 페이로드에서 다시 감춤 | `test_the_payload_says_why_a_type_stayed_untranslated` **1건만** |

복구: `shasum -a 256` `0e9b57e6…` / `fee4bdcf…` 대조 · `grep -c "MUT-"` 두 파일 `0`.

### 측정

| 명령 | 출력 |
|---|---|
| `uv run pytest server/tests -q` | `9712 passed, 8 skipped, 1 warning in 143.06s` |

직전 기준선 `9709` 대비 **+3 = 신규 테스트 수 일치**(전수-목록 대조군 · 슬롯 미확정 격하 ·
페이로드 도달). `test_an_empty_library_is_still_a_rig_fact` 는 **개명·판정 반전**이라
개수에 안 잡힌다. 봉쇄 구역 `5c988bd..HEAD` 빈 출력.

### 리뷰가 통과시킨 것 (지우지 않는다)

순환 import 없음 · `replace()` 안전 · **절단 처리는 옳다**(절단 창 안의 쌍은 긍정 증거라
번역이 맞고 부정 결론만 보류) · `by_slot()` 중복 슬롯 first-wins 와 그 전용 테스트는
공허하지 않음.

### 같은 원인 하나 더 (범위 밖 · 기록)

리뷰가 짚었다 — **M2 가 찾은 `vwx/diff.py` 거짓 경보와 서류 핸들 인쇄는 각 호출부에
`type_names=` 한 줄씩이면 닫힌다.** #3 과 **같은 배선 간극**이다(대응표를 안 넘기는 경로).
이번 범위에 넣지 않았고, **원인이 하나라는 사실을 여기 적는다** — 후속 카드가 셋을 따로
다루지 않도록.

### 이 라운드가 재지 않은 것

- **#5 의 실기 영향** — 「이름이면서 핸들 형태」인 타입이 실제로 있는지 안 쟀다.
- **콘솔 라이브 0건** · **N-1 · #1 의 실기 도달성** 미측정.
- 리뷰가 **7형태 이상을 돌렸는지** — 리뷰 범위 자체는 내가 재지 않았다.


---

## §E.2 (이어서) — M3 생산 지점 전수표

**처방 변경.** 점-수정이 네 회차 연속으로 같은 계열을 열었다(D-1 → 절단 → N-1 → Y-1·Y-2).
매번 성공했고 근거도 매번 사실이었는데 **계열이 마르지 않았다.** M2 가 소비 지점
(C1~C13)에 한 일을 **생산 지점**에 한다.

각 행: **(a)** 그 라벨이 지시하는 행동이 그 입력에 맞는가 · **(b)** 형제가 같은 입력을
이미 다르게 분류하는가 · 「측정됨/미측정」과 근거. M2 규율 그대로 —
**미측정이 많은 표는 정직한 표다.**

### 열거 — 판독 조건이 사유·라벨·플래그로 바뀌는 자리

| # | 자리 | 산출 | (a) 행동이 맞는가 | (b) 형제 분기 | 측정 |
|---|---|---|---|---|---|
| **P1** | `mode_read.read_fixture_type_names` → `attempted` | 판독 도달 여부 | **맞다** — False 는 재조회를 지시하고 실제로 응답이 없었다 | 형제 `walk_mode_widths` 도 같은 축을 쓴다 | **측정됨** — 거절/예외 갈래 테스트 2건 |
| **P2** | 같은 함수 → `whole_unconfirmed` | 전수 확인 불가 | **맞다** — 부정 결론만 보류, 도착한 쌍은 번역 | **맞췄다.** `footprint.py:317-331` 이 빈 목록에 `whole=False` 를 강제하며 이유를 주석에 적었고, 이번에 같은 판정으로 정렬 | **측정됨** — MUT-G 가 되돌리면 RED |
| **P3** | 같은 함수 → `shape_invalid` | 쓸 자식 0건 | **맞다** — 「판독 쪽을 고쳐라」 | 없음 | **측정됨** — N-1 테스트 + MUT |
| **P4** | `mode_read._named_children` → 하나라도 나쁘면 `None` | 표 전체 폐기 | **P1~P3 경로에서는 더 이상 안 쓴다**(자식별 격하로 대체) | `PROTOCOL.md:52-58` 이 `i` optional + 이름-only 격하를 established 로 규정 | **측정됨** — #2 테스트 |
| **P5** | `mode_read.read_type_mode_widths` → `type_found` / `detail` | 모드 폭 판독 | **틀린다(Y-1)** — 여전히 전부-아니면-전무다. `i` 없는 자식 **하나**가 그 타입 판독을 죽여 `mode_unresolved` → **픽스처가 안 패치된다.** 파장이 라벨보다 크다 | 같은 `PROTOCOL.md` 가 이 분기를 규탄. **P4 는 고쳤고 P5 는 안 고쳤다 — 형제 불일치가 내 코드 안에 있다** | **측정됨**(원문) · **영향 미측정** |
| **P6** | `footprint._listing_is_whole` | 전수 술어 | 이용자 다수의 **공유 술어** | — | **손대지 않음** |
| **P7** | `footprint.walk_mode_widths` → `whole=False` 강제 | 빈 목록 | **기준선** — 이번에 P2 가 여기로 정렬 | — | **측정됨**(원문 13줄) |
| **P8** | `inventory.translate_fixture_type` → 사유 5 | 미번역 사유 | **맞다** — 다섯이 각각 다른 행동을 지시 | `vwx/apply.py:520-535` 는 「이름이면서 핸들 형태」 모호성을 **거부**하는데 내 번역기는 **핸들 해석을 우선**한다 → **판단이 다르다(리뷰 #5)** | **측정됨**(원문) · **실기 영향 미측정** |
| **P9** | `inventory._name_handle_types` → 사유 선택 | 우선순위 | **맞다** — shape_invalid > unconfirmed > absent | — | **측정됨** — MUT-D·E·F |
| **P10** | `inventory.read_inventory` → `completeness` · `index_domain_unknown` | 판독 완전성 | **이 카드가 안 건드림** | — | **미측정** |
| **P11** | `tools` 의 `TypeNameRead` 생성(배선) | 경로 부재 시 산출 | **틀렸다(Y-2) → 고쳤다.** 아무것도 안 물었는데 `type_tree_unreadable`(재조회하라)을 냈다 | **인용한 형제가 금지한다** — `tools.py:2696` *"nothing was queried, so nothing may be called unreadable."* 이제 `None`(→`no_type_table`) | **측정됨**(원문 대조) |
| **P12** | `vwx/apply.console_read_caveat` → caveat kind | 미판독 vs 절단 | **이 카드가 안 건드림** | `missing_count == 0` + 절단은 **막지 않는다**(수량 비교는 정확) — P2 는 같은 절단에서 **부정 결론을 보류**한다. **질문이 다르다**(픽스처 부재 vs 슬롯 부재)지만 **같은 절단 신호에 다른 판정**이다 | **미측정** — 두 판정이 실제로 충돌하는 입력이 있는지 안 쟀다 |
| **P13** | `lxseq/mapper._judge_console_read` | 계획 진행 여부 | **틀린다(리뷰 #3)** — **번역 상태를 안 본다**(`git grep` 0건). 판독 실패해도 계획이 서고 86행이 `fid_occupied` 로 나가며 그 라벨은 「다른 FID 로 다시 패치하라」다. **실행 취소가 없다** | 같은 함수가 판독 완전성은 이미 게이트한다 — **번역만 빠졌다** | **측정됨**(grep + 원문) |
| **P14** | `lxseq/mapper._occupancy_skip` → 3 라벨 | 건너뛰기 사유 | **맞다**(D2 수정 후) | — | **측정됨** — M1 통합 테스트 |

**집계**: 14행 · 측정됨 11 · 미측정 3(P6 는 손대지 않음, P10 · P12) ·
**틀린 채 남은 것 2**(P5 Y-1 · P13 리뷰 #3) · **이번에 고친 것 3**(P2 · P4 · P11).

### 표가 드러낸 것 — 이 카드 안에 형제 불일치가 있다

**P4 는 자식별 격하로 고쳤는데 P5 는 전부-아니면-전무 그대로다.** 같은 `PROTOCOL.md`
규약이 두 자리에 걸리는데 한쪽만 정렬했다. **이것이 표 없이는 안 보였다** — 점-수정은
「발견된 자리」만 보므로 형제를 안 본다.

### 고칠 것 / 기록만 할 것 — 제안 (리드 확정 대상)

| 항목 | 제안 | 근거 |
|---|---|---|
| **P5 (Y-1)** | **고치자** | 파장이 라벨이 아니라 **패치 누락**이다. 수정은 P4 와 같은 모양(자식별 격하)이라 설계 위험이 낮다. 다만 `read_type_mode_widths` 는 이 카드 밖 이용자가 있어 **M1 범위를 넘는다 — 리드 확정 필요** |
| **P13 (리뷰 #3)** | **고치자** | 「실행 취소 없음」과 결합해 이 표에서 **가장 위험한 행**이다. 번역이 실패했는데 계획이 서는 것 자체가 잘못이다. **범위 초과 — 확정 필요** |
| **P8 (리뷰 #5)** | **기록만** | 오늘 관측된 두 형식에서는 결과가 같고, 「이름이면서 핸들 형태」인 타입이 실재하는지 **안 쟀다.** 재기 전에 고치면 근거 없는 변경이다 |
| **P12** | **기록만** | 두 판정이 실제로 충돌하는 입력이 있는지 안 쟀다. 측정이 선행이다 |
| **P10** | **기록만** | 이 카드 범위 밖 |
| **리뷰 #7** | **문면 수정 제안** | 「질의 순증 0」이 툴 수준에서 거짓이다 — `read_type_mode_widths` 가 **같은 루트를 확정 타입 수만큼 읽고 `_named_children` 으로 쌍까지 만든 뒤 버린다**(`mode_read.py:234` 확인). 진짜 공유는 P5 수정과 함께라야 자연스럽다 |

### 이번 회차에 닫은 것

| # | 처분 |
|---|---|
| **Y-2 / 리뷰 #1**(수렴) | `None` 을 넘긴다 → `no_type_table`. 형제 규칙(`:2696`) 원문 확인 |
| **리뷰 #2** | 가드를 **두 판독보다 앞**으로 올렸다. 이전 가드는 모드 판독이 먼저 인덱싱해 **무력이었다** |
| **Y-3** | 주석 행번호 정정 — 자기 편집 **이전** 행번호를 편집 **이후** 파일에 적었다 |
| **Y-4** | `console/lua/PROTOCOL.md` 로 경로 명시(같은 이름 둘) |
| **리뷰 #6** | CHANGELOG 가 **개명 전 상수**를 적고 있었다(옛 이름 1 · 새 이름 0). **개명한 그 커밋이 사용자 문서를 안 고쳤다** — 낡은 라벨 계열 여섯 번째 |

### 정지 조건

**표의 모든 행이 (a)(b) 두 칸을 갖췄다**(14/14). 이 뒤에 새로 발견되는 자리는
**「표가 놓친 축」**이므로 표를 넓히지 않고 그 사실만 기록한다 — 다음 카드 재료다.

### 두 검사 대조 (리드 판단, 기록)

- **수렴 1건**: 리뷰 #1 == 감사 Y-2. **서로 못 보는 두 방법이 같은 자리를 짚었다.**
- **분기**: 리뷰만 #2·#3·#6·#7 / 감사만 Y-1·Y-3·Y-4. **각각 다른 절반을 잡았다.**

감사의 자기 진단(인용): 3차에서 첫 행에 스스로 **「A 진짜 빈 라이브러리」**라고 이름
붙였고 **그 이름이 곧 가정이었다.** 그 오분류를 비준한 테스트를 독립 확인해 주면서
**「작동하는가」만 묻고 「무엇을 지키는가」는 안 물었다.**

그리고 감사가 남긴 정직한 한 줄 — **「⑧·⑨도 내가 생각해 낸 질문이 아니라 리뷰에게 배운
질문이다. 다음 축이 무엇인지는 여전히 모른다.」** 이 표도 같은 한계를 갖는다:
**열거의 근거는 오늘까지 발견된 축이지, 축의 전수가 아니다.**
