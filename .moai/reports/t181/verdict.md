# t181 — console_unreachable 이 도구 층에서 도달 불가: 1단계 측정

기준: `WT-refusal-reachability` @ `413b7a5` (origin/main 과 0/0)
측정일: 2026-08-30 · 레인 세션 · 실기 콘솔 0회 (전부 가짜 콘솔)
프로브: `.moai/reports/t181/probes/` 4개. 워크트리 루트에서 재현한다 —
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.moai/reports/t181/probes uv run python .moai/reports/t181/probes/<name>.py`
(`_t181_frames` 와 `_t181_secondorder` 가 `_t181_probe` 를 임포트하므로 PYTHONPATH 가 필요하다.
ruff format 을 걸고 넷 다 다시 돌려 출력이 바뀌지 않음을 확인했다 — 커밋된 파일이 이 결과를 낸 파일이다.)

리드 지시 순서대로 1단계(「오늘 사용자가 실제로 무엇을 보는가」)를 재고,
그 위에서 (1)/(2)를 답한다. 2단계 답은 §4.

---

## 1. 카드 전제 하나가 반증됐다 — 세 자리는 같지 않다

리드가 전수를 지시하며 「셋이 실제로 같은 성질인지는 내가 안 쟀다」고 명시했다. 쟀다.

측정: 픽스처 경로 **하나만** 죽인다(`Patch/Stages/1/Fixtures`). 나머지는 살아 있다.
프로덕션 포트의 실패 형태가 예외이므로 예외를 던지는 가짜를 쓴다
(`server/safety/console.py` `query_state`: "raises on failure/timeout").

| 카드가 지목한 자리 | 도구 | 결과 | **실제로 터진 줄** |
|---|---|---|---|
| `tools.py:4358` | `patch_fixtures` | RAISED `LookupError` | `tools.py:4293` — 4358 에 **안 닿는다** |
| `tools.py:4738` | `import_lxseq_groups` | RAISED `LookupError` | `patchplan.py:1461` — `read_existing_fids` **안** |
| `tools.py:5428` | `import_lxseq_patch` | RAISED `LookupError` | `tools.py:5422` — 5428 에 **안 닿는다** |

대조군(팔 A, 살아있는 콘솔): 세 도구 모두 `RETURNED`, `is_error=false`.
이 팔이 없으면 팔 B 의 빨강이 「이 형태가 죽는다」인지 「프로브가 그 코드에 못 닿는다」인지
안 갈린다.

**따라서 `read_existing_fids` 만 고치면 세 도구 중 하나만 낫는다.**
`read_existing_fids` 호출자가 셋인 것은 맞지만, 이 실패 형태에서 **그 함수에 도달하는
호출자는 하나뿐**이다. 「호출자 수」와 「이 결함이 걸리는 자리 수」가 다른 수다.

증거: `probes/_t181_probe.py` (결과) · `probes/_t181_frames.py` (터진 줄)

## 2. 4293·5422 에는 방어가 **있다** — 다만 이 형태에 공허하다

두 자리 모두 이미 감싸여 있다:

    try:
        before = read_inventory(_InventoryPort(state_port, property_port))
    except InventoryReadError as error:
        return _error_result(call, f"fixture inventory unreadable: {error}")

포트가 던지는 것은 `LookupError` 이고 `InventoryReadError` 가 아니라서 **안 잡힌다.**

이 except 가 아예 쓸모없다는 뜻은 아니다 — 대조군으로 확인했다.
`InventoryReadError` 는 `server/prechk/inventory.py:407·415·670` 에서 실제로 던져진다.
다만 그 셋은 전부 **`ok=False` 형태**이고, 예외 형태는 아무도 안 던진다.
즉 이 방어는 **한 실패 형태만 덮고 자매 형태를 놓친다** — 「방어가 한 입력 계열만
덮는다」 계열의 새 자리다.

## 3. 사용자가 실제로 보는 것 — 잰 값

예외는 어디서도 안 잡히다가 세션 최외곽에서 잡힌다:

    runner.py:488     registry.dispatch(...)          try 없음
    session.py:9906   except Exception as exc:        # raw detail NEVER reaches the surface
    session.py:10190  _report_error -> classify_exception -> error_event

`classify_exception` 에 그 예외를 그대로 넣어 잰 값:

| 입력 | kind | 사용자 문면 |
|---|---|---|
| `LookupError("console did not answer: Patch/Stages/1/Fixtures")` | `unexpected` | 서버 내부 문제가 발생했습니다. 다시 시도해도 반복되면 진단 로그를 확인해 주세요. |
| `LookupError("unknown object path: …")` | `unexpected` | (동일) |
| `ValueError("boom")` | `unexpected` | (동일) |
| `TimeoutError(…)` | `unexpected` | (동일) |
| **비공허성** `ValueError("No API key configured")` | `auth` | AI 서비스 인증에 실패했습니다. API 키 설정을 확인해 주세요. |
| **비공허성** `ProviderError(kind="rate_limit")` | `rate_limit` | AI 서비스 요청 한도를 초과했습니다. 잠시 후 다시 시도해 주세요. |

비공허성 두 줄이 없으면 위 결과가 「이 예외가 접힌다」인지 「이 분류기는 상수다」인지
안 갈린다. 갈렸으므로 **접힌다**가 측정값이다.

**답:** 사용자는 매달리지도(무응답) 스택트레이스를 보지도 않는다.
**「서버 내부 문제」라는 일반 오류 카드**를 받고 **진단 로그를 보라**는 안내를 받는다.
콘솔도, 경로도, 거절 사유도 문면에 없다. 원문(`raw_detail`)은 감사 로그로만 간다.

증거: `probes/_t181_surface.py`

## 4. (1)/(2) 답

### (2) 「도구 층 계약이 원래 예외를 올리는 것이 맞다」 — **반증한다**

근거 셋, 전부 잰 것:

1. **이 자리에 이미 거절 의도가 코드로 있다.** 4293·5422 의 `try/except` 는 바로 이
   상황을 위해 `"fixture inventory unreadable: …"` 를 준비해 두고 있다. 계약이 예외를
   올리는 것이었다면 이 except 가 있을 이유가 없다. 예외 종류를 잘못 적었을 뿐이다.
2. **사용자 문면이 거짓 귀속을 한다.** 콘솔이 안 답한 것을 「서버 내부 문제」라 하고
   **진단 로그**를 보라 한다. 감독은 서버를 뒤지지만 고장난 곳은 콘솔이다.
3. **저장소가 이 상황의 어휘를 이미 갖고 있다.** `path_not_resolved` ·
   `console_unreachable` · `console_read_incomplete` 는 전부 「콘솔이 안 답함」을 위해
   만든 값이다. 그 분류를 계산해 놓고 `unexpected` 로 접는 것은 설계가 아니라 누락이다.

### (1) 「read_existing_fids 호출부에서 잡는다」 — **범위가 모자라다**

§1 대로 세 도구 중 하나만 덮는다.

### 처방은 **두 자리**다 — 셋도 하나도 아니다

`read_inventory` 만 이 형태를 잡게 하면 어떻게 되는지 흉내 내서 쟀다
(소스 미변경, 모듈 속성만 감싸고 `assert` 로 적용 확인):

| 도구 | 결과 | 사용자에게 가는 것 |
|---|---|---|
| `patch_fixtures` | REFUSED CLEANLY | `fixture inventory unreadable: console did not answer: Patch/Stages/1/Fixtures` |
| `import_lxseq_patch` | REFUSED CLEANLY | (동일) |

둘 다 사유를 달고 거절하며 `read_existing_fids` 에 **닿지도 않는다.**
남는 자리는 `import_lxseq_groups`(4738) 하나 — 여기만 `read_existing_fids` 가 직접 죽는다.

    자리 A: read_inventory 의 catch 가 포트 예외도 잡게   -> patch_fixtures + import_lxseq_patch
    자리 B: read_existing_fids 경로                        -> import_lxseq_groups

증거: `probes/_t181_secondorder.py`

🔴 **판정은 리드 몫이다.** 둘 다 조이는 방향이고, 특히 자리 A 는 지금 죽는 두 도구를
거절로 바꾸므로 t166 과 같은 축이다. 구현까지 갈지도 리드가 정한다.

## 5. 안 잰 것

- **실기 콘솔 0회.** 전부 가짜다. 실물에서 픽스처 경로만 죽는 형태는 여전히 아무도
  안 만들어 봤다 — 카드가 적은 그대로다.
- **감사 로그에 실제로 무엇이 적히는지 안 쟀다.** `_report_error` 가 `raw_detail` 을
  기록하는 코드를 읽었을 뿐 실행해서 로그를 열어보지 않았다.
- **이 셋 말고 다른 도구도 같은 형태인지 안 쟀다.** 범위를 카드가 지목한 세 자리로 뒀다.
- **`console_unreachable` 자체가 이 경로에서 계산되는지 안 쟀다.** §1 이 보인 것은
  「예외가 먼저 터진다」이지 「분류가 계산됐는데 안 나간다」가 아니다. 매퍼 층 분류가
  이 도구에서 계산되는 지점까지는 안 따라갔다.
- **뮤테이션 안 함.** 이번 회차는 측정만이고 새 단언을 안 만들었다. 검사를 쓰면 그때 건다.

## 6. 잔여 위험

- §4 의 「두 자리」는 **오늘의 코드 형상**이다. `read_inventory` 를 안 부르게 바뀌면
  `patch_fixtures`·`import_lxseq_patch` 도 4358·5428 에서 죽기 시작한다 — 자리 A 의
  수리가 그 두 도구를 덮는 것은 호출 순서에 의존한다.
- §3 의 문면은 `korean_errors.py` 의 현재 사전이다. 사전이 바뀌면 문면도 바뀐다.
- 프로브가 쓰는 가짜 둘(`_Console`·`FakeConsole`)은 서로 인터페이스가 다르다
  (`FakeConsole.query_state` 에 `offset` 이 없다). 한 가짜로 세 도구를 다 태우지 못해
  자리마다 맞는 가짜를 썼다 — 세 결과가 **같은 계기로 잰 값이 아니다.**

---

# 2단계 — 자리 A 구현 (리드 승인 후)

커밋 `fa67250`. 승인 범위는 **도달을 잰 둘**(4293 `patch_fixtures` · 5422 `import_lxseq_patch`).

## 7. 조건 1 을 재다가 전제가 또 하나 틀렸다

리드가 「포트가 던지는 종류를 이름으로 대라」고 걸어서 쟀는데, **1단계 프로브가 쓴
`LookupError` 는 내 가짜가 고른 종류였다.** 진짜는 다르다:

    server/safety/console.py:89   class StateQueryError(Exception)
    raise 자리 8곳: 689 · 693 · 713 · 718 · 748 · 752 · 772 · 777

형태(예외)는 맞았고 **종류가 틀렸다.** 조건 1 이 없었으면 그대로 구현에 들어가
`except LookupError` 를 넣었을 것이고, 실기에서는 아무것도 안 잡혔을 것이다.
**가짜가 정한 값을 실물의 성질로 읽을 뻔한 자리**로 기록한다.

⚠️ 리드가 넘겨준 raise 자리 수는 **다섯**(689·693·713·718·748)이었는데 재니 **여덟**이다
(752·772·777 이 빠져 있었다). 「입력 계열을 셀 때는 다섯」이라는 주의가 오히려 강해진다 —
검사에 「타임아웃과 ok=False 둘만 온다」를 안 심었다.

## 8. 단위가 정한 것과 안 정한 것 (리드가 남기라고 한 구별)

`read_inventory` 를 직접 재서 팔 셋을 얻었다(`probes/_t181_unit.py`):

    A  포트가 StateQueryError  -> StateQueryError 그대로 빠져나감   **안 잡힌다**
    B  포트가 ok=False         -> InventoryReadError                잡힌다
    C  살아있는 포트           -> 정상 반환

**이 측정이 정한 것**: 그 `except InventoryReadError` 가 이 예외를 안 잡는다.
`read_inventory` 를 감싼 **일곱 자리 전부**에 대해 정해진다.

**이 측정이 안 정한 것**: 죽은 경로가 그 자리에 **도달하는지**. 그건 도구마다 따로다.
나는 둘만 도달까지 쟀다. 나머지 여섯은 **도달 미측정**이고 손대지 않았다 → t183.

「존재는 도달의 증거가 아니다」 — 자리를 세는 것과 도달을 재는 것은 다른 측정이다.

## 9. 무엇을 고쳤나

두 자리에 `except StateQueryError` 를 **따로** 두고 콘솔을 먼저 가리키는 문면을 낸다:

    console did not answer — fixture inventory unread: {error}

기존 `except InventoryReadError` 갈래는 문면까지 그대로 뒀다.

**안 고른 처방**: `read_inventory` 안에서 `StateQueryError → InventoryReadError` 로 옮기면
한 줄로 일곱 자리가 낫는다. 안 골랐다 — 그러면 「콘솔이 침묵」과 「인벤토리가 읽을 수 없는
모양」이 한 사유로 합쳐지고, **그 구별을 살리는 것이 이 카드의 목적**이라 가장 싼 처방이
목적을 지운다. 리드가 이 판단을 승인했다.

## 10. 검사 — 한 가짜로 두 도구 (조건 4)

`FakeConsole` 하나로 두 도구를 다 태운다. 1단계에서 「자리마다 다른 가짜라 세 결과가 같은
계기로 잰 값이 아니다」라고 적은 그 주의를 구현 검사에 걸었다. `import_lxseq_groups` 는
페이징이 필요해 같은 가짜를 못 쓰는데, 그 도구는 자리 B(t182)라 이 범위 밖이다.

    37 -> 49  (순증 12, 교체 없음 — 지운 검사 0, 넣은 검사 12)

| 검사 | 무엇을 지키나 |
|---|---|
| `test_a_silent_console_is_refused_and_the_refusal_names_the_console` (문면 3종 × 도구 2) | 안 죽는다 + 사유 문자열이 콘솔을 가리킨다 + 포트 사유가 보존된다 |
| `test_a_not_ok_console_still_takes_the_inventory_branch` (×2) | 팔 B — 기존 갈래 미파손 (조건 5) |
| `test_a_live_console_carries_neither_refusal` (×2) | 대조군 — 문면이 상수가 아니다 |
| `test_an_unrelated_bug_is_not_swallowed_as_a_console_refusal` (×2) | 넓히기 방지 — `except Exception` 이면 빨강 (조건 1) |

마지막 줄은 검사를 쓰다 찾은 구멍이다. 조건 1 은 「넓히지 마라」인데 앞의 검사들로는
**누가 넓혀도 안 걸렸다.** 넓히면 무관한 버그가 「콘솔이 안 답했다」로 보고되고, 이번엔
감독이 콘솔을 뒤지는데 고장난 곳은 코드다 — **방향만 뒤집힌 같은 오진**이라 검사를 더했다.

## 11. 뮤테이션 6/6 KILL (`probes/_t181_mutate.py`)

축을 하나씩만 건드렸고, 회차마다 `assert mutated != original` 을 들고 갔다.

| # | 축 | 예측 | 결과 |
|---|---|---|---|
| M1 | 자리 1 catch | patch_fixtures 침묵 3건 | KILL 3 |
| M2 | 자리 2 catch | import_lxseq_patch 침묵 3건 | KILL 3 |
| M3 | 문면이 콘솔을 가리킴 | 이름 단언 6건 | KILL 6 |
| M4 | 예외 종류 명시 | 넓히기 방지 2건 | KILL **4** ⚠️ |
| M5 | 포트 사유 보존 | detail 단언 6건 | KILL 6 |
| M6 | 두 사유 분리 | 팔 B 2건 | KILL 2 |

⚠️ **M4 는 예측이 어긋났다 — 2건을 예측했는데 4건이 죽었다.** 억지로 맞추지 않고 왜인지
적는다: `except StateQueryError` 를 `except Exception` 으로 넓히면 그 except 가 `try` 의
**첫 번째**이므로 `InventoryReadError`(Exception 의 자식)까지 먼저 삼킨다. 그래서 팔 B 의
문면도 콘솔 쪽으로 바뀌어 분리 단언이 같이 죽는다. 예측이 좁았던 것이고 결과는 옳다.

## 12. 대조군 팔 2 — 직전 커밋에서 못 잡는가

`git checkout 408127d -- server/orchestrator/tools.py` (catch 0개) 상태에서:

    6 failed, 43 passed
    실패 6건 전부 StateQueryError 로 죽음 = 결함 그대로

팔 B(2)와 넓히기 방지(2)는 **직전 상태에서도 초록**이다. 그게 맞다 — 그 넷은 원래 결함이
아니라 **내 변경**을 지키는 팔이다. 「기존 상태에서도 초록인 팔은 쓸모없다」로 읽어 지우면
안 되는 자리다(규약 §3, t167 에서 나온 그 항목).

## 13. 2단계에서 안 잰 것

- **실기 콘솔 0회.** 여전히 전부 가짜다. `StateQueryError` 를 던지는 실물 상황을 만들지 않았다.
- **나머지 여섯 자리의 도달.** 측정 안 했고 손대지 않았다 → t183.
- **여덟째 자리(6506, `build_patch_sheet_query`)** 는 다른 함수를 감싸서 §8 의 단위 측정이
  적용되지 않는다. 따로 재야 한다 → t183.
- **`session.py` 쪽은 안 건드렸다.** 무관한 버그가 「서버 내부 문제」로 접히는 것은 그대로다 —
  무관한 버그에는 그게 맞는 문면이라 판단했고, 그 판단은 재서 나온 게 아니라 내 판단이다.
- **감사 로그 실측은 여전히 없다.**

## 14. 규약 후보 (문면만, 반영은 리드)

> **`try/except` 가 있다는 것은 그 실패 형태를 잡는다는 뜻이 아니다 — 예외 *종류*를 읽어라.**
> 자매 형태(`ok=False` ↔ 예외)가 다른 종류로 오면 방어는 한쪽만 덮는다. t181 실측:
> `except InventoryReadError` 가 거절 문면까지 준비해 두고도 포트의 `StateQueryError` 를
> 놓쳐, 도구가 죽고 사용자는 「서버 내부 문제」를 받았다. 판별은 **던지는 쪽의 `raise` 를
> 세는 것** — 잡는 쪽만 읽으면 안 보인다.
>
> 짝 규칙: **넓혀서 고치지 마라.** `except Exception` 은 무관한 버그를 같은 사유로 보고해
> **방향만 뒤집힌 같은 오진**을 만든다. 종류를 이름으로 대고, 그 밖은 올려보내라.
