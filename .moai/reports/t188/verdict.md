# t188 — read_existing_fids 의 나머지 포트 호출 둘: 도달 측정

- 브랜치 `WT-port-call-reach` · base `11f9d13` (= 착수 시점 `origin/main`)
- 콘솔 실기 **0회**. 가짜 포트 · 도구 dispatch · 정적 파싱으로 잰 값이다.
- 프로브 다섯: `.moai/reports/t188/probes/`

## 0. 카드 전제부터 다시 쟀다 — 1건 반증

카드의 줄번호는 base `0fc0439` 기준이고, t182 가 `patchplan.py` 에 24행을 넣어
**+22 밀렸다.** 현재 base `11f9d13` 기준:

| 카드 | 현재 | 무엇 | 방어 |
|---|---|---|---|
| :1461 | **:1483** | `query_state(FID_FIXTURE_ROOT)` 루트 | 호출부에서 t182 가 감쌈 |
| :1493 | **:1515** | `query_property` 열거 슬롯별 판독 | **없음** |
| :1529 | **:1551** | `query_property` 절단 복구 스윕 | **`except Exception` (round18)** |

🔴 카드는 「t182 가 1461 만 감쌌으니 나머지 둘에서 여전히 죽는다」고 했다.
`:1551` 은 **t182 이전부터** `patchplan.py:1550-1561` 의 `try/except Exception` 안에
있다. 「여전히 죽는다」는 `:1515` **한 자리에만** 참이다.

## 1. Claim

1. `:1515` 는 도달하고, 예외가 `read_existing_fids` 를 **그대로 탈출한다**.
2. `:1551` 은 도달하고, 예외가 **삼켜진다**(`probe_failures` 로 센다). 안 죽는다.
3. `:1515` 가 죽을 때 `import_lxseq_groups` 는 살아남지만 **거짓 사유**를 낸다 —
   루트는 읽혔는데 「콘솔의 픽스처 루트 상태를 읽지 못했다」가 나간다.
4. `read_inventory` 는 **FID 프로퍼티를 0회 읽는다.** 그래서 FID 프로퍼티만 죽는
   자극에서는 t181 의 거절이 **먼저 걸리지 않는다.**
5. `patch_fixtures`(`tools.py:4369`)는 그 자극에서 **예외가 도구를 탈출한다** —
   dispatch 로 확인했다.
6. 프로덕션 `query_property` 는 `ok=False` 를 **반환하지 않고** 예외를 던진다.
   그래서 `patchplan.py:1523-1525` 의 `unreadable_fids` 갈래는 **실기에서 죽은 코드**다.

## 2. Evidence

### 2.1 도달 (`_t188_reach.py`) — 양성 대조군 먼저

    A0 대조군(절단 없음, 안 죽음)   반환됨 complete=True fids=(101,102,103) · prop 3회
    A1 :1515 (열거 슬롯 2 예외)     🔴 예외 탈출 StateQueryError · prop 2회
    A2 대조군(절단 6>3, 안 죽음)    반환됨 enumerated=3 recovered=3 · prop 6회
    A3 :1551 (스윕 슬롯 5 예외)     반환됨 probe_failures=1 unseen=1 · prop 6회
                                    reason: 선언 6개 중 1개를 열거하지 못했다

A0 이 prop 3회를 세므로 계기는 살아 있다. A2 가 6회(열거 3 + 스윕 3)를 세므로
스윕도 실제로 발화한다 — A3 의 「안 죽는다」가 「자극이 안 닿았다」가 아니다.

### 2.2 사용자 문면 (`_t188_userfacing.py`)

    B0 안 죽음                       console_read_reason = None
    B1 루트 state 사망 (t182 자리)   console_read_reason = 콘솔의 픽스처 루트 상태를 읽지 못했다
    B2 슬롯 2 프로퍼티 사망 (:1515)  console_read_reason = 콘솔의 픽스처 루트 상태를 읽지 못했다

🔴 **B1 과 B2 가 바이트 동일하다.** B2 에서 루트는 정상 응답했고 슬롯 1의 프로퍼티도
성공했다(A1 이 prop 2회를 셌다 — 1은 통과, 2에서 죽었다). 그런데 사용자는 루트를
못 읽었다는 말을 듣는다.

t182 의 catch 는 `read_existing_fids` **호출 전체**를 감싸므로 세 자리 어디서 난
`StateQueryError` 든 다 잡아 `unreadable_root()` 로 접는다. 살린 것은 맞지만
**어느 판독이 실패했는지를 잃는다.**

### 2.3 방어 범위 (`_t188_coverage.py`, ast)

    read_existing_fids 호출 자리: [4369, 4750, 5457]
    tools.py:4369  덮는 try 없음
    tools.py:4750  try@4749 가 잡는 것: ['StateQueryError']
    tools.py:5457  덮는 try 없음

양성 대조군은 `4750`(t182 가 감싼 자리)이다. 계기가 그것을 「덮임」으로 답했으므로
나머지 둘의 「없음」은 계기의 눈멂이 아니다.

`4369`·`5457` 에도 `except StateQueryError` 가 있지만(`:4296`·`:5443`) 그것들은
`read_inventory` 를 감싸는 t181 의 자리이고, 문제의 호출은 그 try **본문 밖**이다 —
들여쓰기가 아니라 ast 의 본문 범위로 쟀다.

⚠️ **이 절은 「덮임 여부」만 답한다. 도달은 안 답한다** — 그건 2.4·2.5 가 답한다.

### 2.4 t182 의 반대 실측을 다시 쟀다 (`_t188_precede.py`)

t182 커밋 본문은 「4368·5447 은 t181 이 고친 `read_inventory` 에서 먼저 거절된다」고
적었다. 그 자극은 픽스처 **경로 전체**를 죽였다. 내 자극은 **FID 프로퍼티 하나**만
죽인다. 자극이 다르므로 그 값을 옮겨 쓸 수 없어 다시 쟀다.

    read_inventory 반환됨: Inventory
    state 호출 1회 · prop 호출 12회
      슬롯마다 Patch · FixtureType · Mode · Name — 슬롯 3개 × 4
    그중 FID 프로퍼티 판독: 0회

`read_inventory` 는 FID 를 **한 번도 안 읽는다**(patchplan 독스트링의 「화이트리스트
밖」이라는 문면이 실제로 그렇다). 그러므로 FID 프로퍼티만 죽는 자극에서 t181 의
거절은 발화하지 않고, 제어가 `read_existing_fids` 까지 내려간다.

### 2.5 실제 도구 dispatch (`_t188_blast.py`)

`patch_fixtures` 를 기존 검사 하네스(`test_vwx_stagedpatch.py::_patch`)로 태웠다.

    C0 대조군: 아무것도 안 죽음        status = created
    C1 측정: FID 프로퍼티만 죽음       🔴 예외가 도구를 탈출:
                                       StateQueryError: no prop reply for
                                       Patch/Stages/1/Fixtures/1 FID
    C2 대비군: Patch 프로퍼티가 죽음   status = unverified

**C1 이 이 카드의 핵심 실측이다** — ast 의 「덮는 try 없음」이 실제 크래시로 확인됐다.

⚠️ **C2 는 내 예측이 틀렸다.** 「t181 이 먼저 거절한다」를 보이려고 둔 대비군인데
거절이 아니라 `status=unverified` 로 통과했다. 즉 이 하네스에서는 `Patch` 프로퍼티
사망도 t181 의 catch 를 안 태운다. t182 의 「먼저 거절된다」는 **또 다른 자극**
(경로 전체 사망)에서만 재현되는 값으로 보이며, 나는 그 자극을 안 만들었다.
예측이 어긋난 것을 고쳐 적지 않고 그대로 둔다.

### 2.6 프로덕션 포트의 실패 형태 (`server/safety/console.py:696-722`)

`query_property` 는 타임아웃이면 `:713`, `ok=false` 응답이면 `:718` 에서 각각
`StateQueryError` 를 올린다. **`ok=False` 를 반환하는 경로가 없다.**

카드가 열어둔 물음 「여덟 raise 중 어느 것이 query_property 경로인가」의 답:
**`:713` 과 `:718`, 둘.** 나머지 여섯은 `query_state`(689·693) ·
`enumerate_fields`(748·752) · `query_properties`(772·777) 소속이다.

두 형태 다 현실적이다. `:713` 은 **한 번의 왕복 타임아웃**이라 어느 호출에도
붙을 수 있고(그래서 read_inventory 12회가 통과한 뒤 FID 판독에서만 나는 조합이
가능하다), `:718` 은 응답기가 **그 프로퍼티에 대해** ok=false 를 답한 것이라
프로퍼티 특정적이다.

## 3. Baseline-attribution

워크트리 `.claude/worktrees/t188`, HEAD `11f9d13`. 다른 트리의 venv 를 빌려 썼으므로
트리 동일성 가드를 먼저 돌렸다 — `server.vwx.patchplan` 이
`.../worktrees/t188/server/vwx/patchplan.py` 로 해석되는 것을 확인한 뒤 프로브를
돌렸다. 전부 `PYTHONDONTWRITEBYTECODE=1`.

## 4. Gaps — 안 잰 것

- 🔴 **실기 콘솔 0회.** 실물에서 FID 프로퍼티만 실패하는 형태를 아무도 안 만들어
  봤고, 그 조합이 실기에서 얼마나 흔한지도 모른다. 2.6 의 「둘 다 현실적이다」는
  `console.py` 소스를 읽은 근거이지 실기 관측이 아니다.
- **`import_lxseq_patch`(`:5457`)를 dispatch 하지 않았다.** ast 로 덮임 없음만 쟀고
  도달은 `4369` 와 같은 구조라는 **추론**이다. `4369` 는 실측했고 이쪽은 안 했다.
- **C2 가 왜 거절이 아니었는지 안 쫓았다.** t182 의 「먼저 거절된다」를 재현하는
  자극을 못 만들었고, 만들려고 더 시도하지도 않았다.
- **스윕의 `except Exception` 이 얼마나 넓은지 안 쟀다.** `StateQueryError` 말고
  무엇이 삼켜지는지, 삼켜서 안 되는 것이 있는지 안 봤다.
- **`unreadable_fids` 갈래가 실기에서 죽은 코드**라고 적었지만 `console.py` 하나만
  읽었다. 다른 포트 구현이 `ok=False` 를 내는지 전수하지 않았다.
- **뮤테이션 0회.** 코드를 아직 안 고쳤으므로 걸 단언이 없다.

## 5. Residual-risk

- 전부 가짜 포트다. 실기 응답기가 이 형태로 실패한다는 것은 소스가 근거다.
- `:1551` 이 「이미 방어됨」이라는 판정은 그 자리에 `except Exception` 이 있다는
  실측이다. 그 catch 가 **의도보다 넓어서** 생기는 별개 위험은 이 카드 밖으로 남긴다.
- 프로브 다섯 중 넷이 서로 다른 가짜를 쓴다(t182 회차가 만난 것과 같은 형태다).
  같은 계기로 잰 값이 아니므로 팔끼리의 수치 비교는 하지 않았다.

## 6. 판정 요청 — 조이는 방향이라 리드 몫

`:1515` 를 고치면 지금 죽는 도구가 거절로 바뀐다. 형태가 셋이다.

- **(A) 세 호출부에 각각 `except StateQueryError`** — t182 선례 그대로.
  같은 블록이 세 번 반복되고, **셋 다 `unreadable_root()` 라는 거짓 사유를 낸다.**
  지금 `4750` 이 내는 거짓말을 셋으로 늘리는 형태다.
- **(B) `patchplan.py:1515` 를 `try/except StateQueryError` 로 감싸고
  `unreadable_fids += 1`** — 그 갈래는 **이미 존재한다**(`:1523-1525`). 프로덕션이
  내지 않는 `ok=False` 로만 도달할 수 있어 죽어 있었다. 새 개념을 만드는 게 아니라
  **있는 처리기에 실기 형태를 연결**하는 것이다. `complete=False` 가 서고 사유가
  슬롯 단위로 정직해진다.
  ⚠️ 걸리는 것: t182 가 「`server/vwx` 는 `server.safety` 임포트 선례 0건」을 근거로
  안쪽 catch 를 피했다. (B)는 그 경계를 넘는다 — t182 가 안 낸 값을 내가 내게 된다.
- **(C) 예외를 `patchplan` 안에서 잡되 `server.safety` 를 임포트하지 않는 형태** —
  `except Exception` 을 쓰는 `:1551` 선례가 이미 그 파일에 있다. 다만 넓히기라
  t182 검사가 지키는 「안 넓혔다」와 부딪힌다.

내 판단은 **(B)** 이고, 근거는 처방의 싸구려가 아니라 **개념의 주인**이다 —
「슬롯 프로퍼티를 못 읽었다」는 `ExistingFidRead` 가 이미 세는 축이고 호출부는 그
축을 모른다. (A)는 거짓 사유를 복제한다.

⚠️ 다만 임포트 경계는 t182 가 명시적으로 **안 넘기로 한** 값이다. 그 결정을 뒤집는
것이므로 판정은 리드가 한다. 나는 구현하지 않고 여기서 멈춘다.
