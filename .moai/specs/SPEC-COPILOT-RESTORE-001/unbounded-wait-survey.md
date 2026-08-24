# 상한 없는 대기 — 조사 (t52, 조사 단계만)

> **설정을 고치지 않았다.** plan 레인이 t10 B 마무리로 전량 스위트를 곧 돌린다 —
> 지금 전역 pytest 설정을 건드리면 그 레인의 초록이 누구 것인지 갈리지 않는다.
> 🔴 **10곳 상한에 걸렸다가 풀렸다** — §4 에서 호출 지점으로 69 였는데, §4c 에서
> 저장소에 이미 있는 해답을 세니 **4곳**이 됐다. 신설이 아니라 승격이다.

## 1. 어떻게 쟀나 — grep 으로 시작해 AST 로 좁혔다

`while True` 만 세면 12건인데 사건 모양(*「응답이 영영 안 왔고 실패하지 않고 멈췄다」*)과
안 맞는다. **대기는 대개 루프가 아니라 호출에 숨어 있다.**

    1차  grep  `while True`                        server 전체 12
    2차  AST   대기성 호출 중 timeout 인자 없는 것    9   ← 판별기가 틀렸다
    3차  AST   이름별 규칙(위치 인자가 timeout 인가)  1154 ← 이번엔 너무 넓다
    4차  대상  진짜 블로킹 원시요소만                 아래 §2

**2차가 틀린 이유**: `recv(4096)` 의 위치 인자를 timeout 으로 세어 「상한 있음」으로
분류했다. 소켓이 바로 사건의 모양인데 그걸 걸러 냈다.
**3차가 넓은 이유**: `dict.get(key)` 1132건이 섞였다. `get` 은 큐일 때만 대기다.

## 2. 후보는 결함이 아니다 — 읽으니 8/9 가 상한을 갖고 있었다

| 자리 | 상한 | 근거 |
|---|---|---|
| `responder_roundtrip.py:96` | 있음 | `deadline` + `consumer.get(timeout=remaining)` |
| `reply_discovery.py:243,253` | 있음 | `deadline` + `select(..., remaining)` |
| `measurement/runner.py:133` | 있음 | `_max_attempts` |
| `orchestrator/runner.py:425` | 있음 | `_max_model_calls` |
| `test_web_console_probe.py:218` | 있음 | `:216` `setblocking(False)` — 두 줄 위 |
| `vwx/stagedpatch.py:126` | 대기 아님 | 유한 후보 공간 계산 |
| `watchdog_child.py:63,91` | 설계 | *"the watchdog is the only exit path"* — 상한이 밖에 있다 |
| `web/app.py:247,264` | 서비스 루프 | `await asyncio.sleep(interval)` — 응답 대기가 아니다 |
| **`web/app.py:428`** | **없음** | `await lane.acquire()` — 잠긴 레인이면 그 태스크가 멈춘다 |

**후보와 결함은 다르다.** 9곳 중 8곳은 스캐너가 물었을 뿐이고 읽으니 상한이 있었다.

## 3. 🔴 진짜 계열은 루프가 아니라 **수신 호출**이다

    server/tests  ws.receive_json()      69 곳 / 12 파일
                  ws.receive_text()       0
                  websocket_connect      100 곳
                  공용 수신 헬퍼           없음
                  conftest 안의 소켓 생성   없음

**`for _ in range(N)` 은 회수 상한이지 시간 상한이 아니다.** 루프를 N 번 돌기로 묶어도
`receive_json()` **한 번**이 영영 안 오면 거기서 멈춘다. 그래서 「루프에 상한이 있다」로
분류한 7곳도 실제로는 안 지켜진다.

근거(실행해 확인):

    starlette.testclient.WebSocketTestSession.receive
      return self.portal.call(self._send_rx.receive)     ← 인자 없음

즉 **이 스위트의 모든 웹소켓 수신은 상한이 없다.** 무한루프 1건
(`test_web_cue_monitor.py:585`)은 그중 **가장 걸리기 쉬운** 자리이지 유일한 자리가 아니다.

⚠️ `pytest-timeout` 은 **설치돼 있지 않다**(`ModuleNotFoundError`). `[tool.pytest.ini_options]`
에는 `testpaths` 한 줄뿐이라 지금 이 스위트에는 **어떤 시간 상한도 없다.**

## 4. 10곳 상한 판정 — **계층에 따라 갈린다**

| 계층 | 고칠 자리 | 무엇을 놓치나 |
|---|---:|---|
| 호출 지점 (`receive_json` 마다) | **69** ✋ | 새로 쓰는 테스트가 또 안 건다. 사람 규율에 의존 |
| 소켓 생성 지점 (`websocket_connect` 마다) | **100** ✋ | 위와 같음. 더 많다 |
| 공용 헬퍼 신설 + 호출부 이관 | **69** ✋ | 이관 자체가 69 곳 편집이다 |
| **conftest autouse 패치** (`WebSocketTestSession.receive` 에 기한) | **1** | 웹소켓 **밖의** 대기(파일·서브프로세스·잠금)는 못 잡는다 |
| **전역 pytest 시간 상한** (`pytest-timeout`) | **1** + 의존성 1 | 어디서 멈췄는지 메시지가 거칠다. 느린 테스트를 오탐할 수 있다 |

**호출 지점으로 세면 69 라 상한을 넘는다** — 그래서 여기서 멈추고 보고한다.
**계층을 올리면 1 곳**이고, 두 후보는 서로를 대체하지 않는다:

- conftest 패치는 **정확한 자리와 메시지**를 준다(어느 소켓이 무엇을 기다리다 죽었는지).
  대신 웹소켓만 덮는다.
- 전역 시간 상한은 **열거하지 못한 대기까지** 덮는다(§5 가 왜 열거가 하계인지 적는다).
  대신 원인을 안 알려 준다.

**둘 다 거는 것이 맞다고 본다** — 전역이 그물, conftest 가 진단이다. 다만 **결정과 실행은
t10 B 머지 뒤**다.

## 4b. 특정됐다 — 「후보 69」가 아니라 **「확인된 1건 + 같은 모양 68」**

멈춘 그 테스트는 `server/tests/test_web_app.py::test_vectorworks_upload_starts_a_guided_chat_turn`
이다. 근거는 `origin/WT-sheetpipe`(`02b5b56`) 의 픽스처 수정이고 **읽기만 했다**(plan 레인 것).

    옛 페이로드  content_base64="c2FmZQ=="        ("safe" 4바이트)
    SHEETPIPE M1 뒤  판별기가 unknown_sheet_kind 로 판정 → 서버는 notice 만 보낸다
    테스트        _receive_until(ws, "chat_response")   ← 영영 안 오는 것을 기다린다

그 브랜치의 수정 주석이 그대로 적는다 — *"예전의 `c2FmZQ==`는 unknown_sheet_kind로
떨어져 안내만 나가고 chat_response는 오지 않는다."*

### 🔴 상한도 실패 메시지도 **써 있는데 발화할 수 없다**

    def _receive_until(ws, event_type, *, limit=30):
        for _ in range(limit):
            event = ws.receive_json()          ← 1회차에서 막힌다
            ...
        raise AssertionError(f"no {event_type!r} event within {limit} frames: {seen}")

작성자는 실패 경우를 **생각했고** 메시지까지 썼다. 그런데 **회수 상한은 각 회가 돌아와야
센다** — 1 회차가 안 돌아오면 카운터가 안 올라가고 그 `raise` 는 영영 도달하지 못한다.
**검사가, 그것이 쓰인 바로 그 경우에 공허하다.**

이것이 §3 의 「`range` 는 회수 상한이지 시간 상한이 아니다」를 **구조 추론이 아니라 사건으로**
확정한다.

### 같은 모양 — 세 사본이 바이트 동일하다

    test_web_app.py:48   test_web_e2e.py:90   test_web_review.py:270
    sha256 앞 12자리  3dbfce1ce84c  — 셋 다 같다.  호출 36곳

## 4c. 🔴 저장소가 이미 답을 갖고 있다 — 신설이 아니라 승격이다

`server/tests/test_web_panel_execute.py` 는 **시간 상한을 가진 변형**을 이미 쓴다.
그 독스트링이 문제를 그대로 적어 뒀다:

> ``TestClient``'s websocket receive has no timeout, so a missing frame would
> block the whole suite forever.

    _recv(ws, timeout)   데몬 스레드로 pump → worker.join(timeout)
                         → 못 받으면 AssertionError("no websocket frame within Ns")
    _drain(ws, kind)     그 _recv 위에 회수 상한을 얹는다

**세 사본은 이 해답을 놓친 복사본**이다. 처방은 「conftest 에 새 가드를 짓는다」가 아니라
**「이미 도는 `_recv`/`_drain` 을 conftest 로 올리고 세 사본이 그것을 쓰게 한다」**이다.

    고칠 자리  conftest 1 (이동) + 사본 3 (삭제·이관) = **4**   ← 10 아래다

앞서 「69 아니면 1」로 갈렸던 것은 **저장소에 이미 있는 것을 안 세었기 때문**이다.

### 내장 시간 상한 — 실재한다 (실측)

    $ uv run pytest --help | grep -i faulthandler
      faulthandler_timeout (string):          시간 초과 시 전 스레드 스택 덤프
      faulthandler_exit_on_timeout (bool):    시간 초과 시 테스트 프로세스 종료

**둘 다 내장이다** — 의존성 0. 덤프만 하는 게 아니라 `exit_on_timeout` 으로 끊을 수도
있다. `pytest-timeout` 을 사기 전에 이것으로 그물이 선다.

## 5. 🔴 이 조사도 하계다

t50 과 같은 이유다. `while True` 로 시작해 AST 로 좁혔지만, **대기는 어휘가 아니라
구조로 성립한다** — `portal.call(...)` 은 어느 어휘에도 안 걸렸고, 실제로 클래스 소스를
읽고서야 상한이 없다는 걸 알았다.

다음 사람이 쓸 기준: **「이 호출은 무엇이 오면 돌아오나」를 묻고, 그것이 안 오는 경우를
답할 수 없으면 상한이 없는 것이다.** 어휘 목록을 늘리는 것보다 빠르다.

## 5b. 🔴 실행 순서 — **재는 것 자체가 지금은 못 하는 일이다**

임계값은 재고 정한다. 그런데 **그 측정이 전량 스위트를 요구**하고, 전량은 지금 두 가지에
막혀 있다:

    lsof -nP -iUDP:9005 → app_gma3 pid 47006      콘솔이 잡고 있다
    gh pr list          → 빈 출력                  plan 레인 PR 아직 없음

콘솔이 9005 를 잡은 채 전량을 돌리면 빨간 것이 나오는데 **그건 코드 결함이 아니라 포트
점유**다. 그리고 지금 돌리면 plan 레인이 곧 돌릴 것과 겹쳐 초록의 귀속이 갈리지 않는다.

**이 문장을 여기 남기는 이유**: 안 적으면 다음 세션이 *"측정하라 했으니"* 하고 지금
돌린다. 지시는 「재라」였지 「지금 재라」가 아니었다.

실행 순서(전부 t10 B 머지 뒤):

    1  uv run pytest --durations=20        임계값의 근거
    2  conftest 승격 + 사본 3 이관          독스트링을 같이 옮긴다
    3  사본 소멸을 **바이트로** 확인         하나만 남아도 다음 사람이 그걸 복사한다
    4  뮤테이션 — 상한을 무한대로 되돌리면 빨개지는가
       (안 빨개지면 승격이 아무것도 안 지킨 것이다)
    5  faulthandler_timeout 을 1 의 측정값 **위로** 설정
    6  그 뒤에 faulthandler_exit_on_timeout

`exit_on_timeout` 은 pytest 프로세스를 통째로 끊는다 — 임계값이 낮으면 **느리기만 한
정상 테스트 하나가 전량 결과를 다 날린다.** 그래서 5 가 1 뒤에, 6 이 5 뒤에 온다.

## 6. 미검증

- **`app.py:428` `lane.acquire()` 가 실제로 걸린 적이 있는지는 모른다.** 구조만 봤다.
- ~~86% 에서 선 그 테스트 특정~~ → **닫혔다**(§4b). `origin/WT-sheetpipe` 대조.
- **그 테스트가 「두 번」 선 것이 같은 원인인지는 모른다.** 한 번의 기전만 확인했다.
- **`for _ in range(N)` 7곳이 실제로 멈춘 적이 있는지는 모른다.** 구조상 가능하다는 것뿐.
- **웹소켓 밖의 대기**(파일 읽기 18건 · 서브프로세스 · 잠금)는 이번에 **분류만 하고
  전수하지 않았다.**
