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
