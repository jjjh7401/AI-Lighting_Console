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
