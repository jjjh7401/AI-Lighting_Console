# t54 sync 리뷰 — PR #122 웹소켓 수신 헬퍼 이관

- **대상**: PR #122 · `WT-recv-migrate` · head **`727dcd68f8279d9ddd854924b5c625544c2de405`**
- **기준(base)**: `git merge-base FETCH_HEAD origin/main` → **`fa08651`**.
  모든 diff 수치는 `fa08651..727dcd6` 범위다. PR 미머지 상태라 머지베이스가 자기 자신으로 붕괴하지 않았다.
- **리뷰 트리**: `.claude/worktrees/t54r` / `WT-recv-review` (구현자 트리 `t54` 에는 들어가지 않았다)
- **렌즈**: 판정검수 · 테스트강도(예외 축 포함) · 스코프 (`--patch` 없음 — 결함은 보고만)

> **head 이동에 따른 재측정.** 이 리뷰는 처음 `1f37092` 에서 측정됐고, 심사 중 구현자가 문서 커밋을
> 푸시해 head 가 `727dcd6` 으로 옮겨졌다. **옛 head 의 측정을 옮겨 쓰지 않고 전부 새 head 에서 다시
> 쟀다.** 결과는 동일했다(§2.2). 두 head 의 diff 는 `progress.md` 단독(+56/−3)이다.

---

## 1. Claim (주장)

# 판정: **PASS**

CI 게이트가 **머지될 head 에서** 충족됐고(§2.1), 세 렌즈 모두 통과한다.

| 렌즈 | 주장 |
|---|---|
| 1 · 판정 검수 | 66자리 전부 `recv_frame` 이 옳은 선택이다 |
| 2 · 테스트 강도 | 약해진 자리 **0**. 예외 축까지 포함해 **0** |
| 3 · 스코프 | 테스트·문서 밖 변경 **0**. 산술이 스스로 검산된다 |

### 렌즈 1 — 판정 축은 「자리」가 아니라 「치환의 성질」이다

리드 지시는 "자리마다 옳은가"였고, 구현자도 "65자리는 검사가 못 지킨다"고 적었다.
그러나 원문을 읽으면 자리별 판단이 **불필요해진다.**

`recv_frame` 은 내부에서 그대로 `ws.receive_json()` 을 호출하고 같은 값을 반환한다(§2.3).
반환 프레임이 동일하므로 **어떤 단정도 약해질 수 없다.**

의미가 다른 쪽은 `drain_until`(특정 타입까지 폐기)인데, **이 PR 은 `drain_until` 을 0회 추가했다**(§2.2).
따라서 이관이 부정형 단정을 약화시킬 수 있는 **유일한 경로가 애초에 열리지 않았다.**

`recv_frame` 이 틀린 선택이 되는 경우는 「대상 프레임 앞에 다른 프레임이 실제로 끼어드는 자리」뿐이고,
그런 자리는 단일 호출로 바뀌지 않았다 — `_fresh_cue_monitor` 의 배수 루프가 루프 그대로 남았다(§2.5).

### ⚠️ 위 논증의 한 가지 예외 — 예외 전파는 보존되지 않는다

**이 리뷰의 초판은 이 치환을 「의미 보존」이라고만 적었다. 그 표현은 부정확했다.**
리드가 원문을 읽고 지적했고, 옳은 지적이다. 정확히는:

> **반환값 의미는 보존되지만, 예외 전파는 보존되지 않는다.**
> `pump()` 이 모든 예외를 잡아 `AssertionError` 로 바꾸고, 원래 예외는 메시지 안에 문자열로만 남는다.

이것은 실재하는 의미 변화다. 그래서 렌즈 2 의 축으로 따로 세워 66자리 전부를 훑었고,
**영향받는 자리는 0건이었다**(§2.8). 근거는 「CI 가 초록이다」가 아니라 자리별 위치 확인이다.

---

## 2. Evidence (증거 — 명령과 그 출력)

### 2.1 대상 고정 + CI 게이트

```
gh pr view 122 --json headRefOid,additions,deletions,changedFiles,state,mergeable
  {"additions":1333,"changedFiles":12,"deletions":66,
   "headRefOid":"727dcd68f8279d9ddd854924b5c625544c2de405",
   "mergeable":"MERGEABLE","state":"OPEN"}

git fetch origin pull/122/head ; git rev-parse FETCH_HEAD
  727dcd68f8279d9ddd854924b5c625544c2de405        (PR 보고 head 와 일치)

git merge-base FETCH_HEAD origin/main
  fa08651003a3dbe016b0dd724c8bdd52b9462c9f
```

**CI — 초록이 머지될 head 에 귀속되는지 직접 확인했다** (「pass」 한 줄로 세지 않는다):

```
gh pr checks 122 --watch --fail-fast
  test  pending  0       .../runs/32715920533/job/97396995199
  test  pass     4m58s   .../runs/32715920533/job/97396995199

gh api repos/jjjh7401/AI-Lighting_Console/actions/runs/32715920533 \
       --jq '.head_sha, .conclusion, .status'
  727dcd68f8279d9ddd854924b5c625544c2de405
  success
  completed
```

**run 32715920533 의 `head_sha` 가 PR 의 현재 head 와 같다.** 앞선 실행(`32715319430`, 5m21s)은
옛 head `1f37092` 의 것이므로 이 판정의 근거로 쓰지 않았다.

**CodeRabbit 은 이 저장소에서 N/A** 다 — `statuses` 0건, `gh pr checks` 에 행 없음.
「적용 대상 아님」이지 미충족이 아니다. 이것으로 카드를 막지 않는다.
(이 문단은 리드가 t48 근거와 함께 준 **옮긴 값**이며 내가 재측정하지 않았다 — §4 참조.)

### 2.2 렌즈 3 — 스코프 (새 head 에서 독립 계수)

```
git diff --name-only fa08651 727dcd6 | grep -v -E '^server/tests/|^\.moai/'
  (없음 — 0건)
```

```
삭제행 총계 (server/tests)                  ->  66
  그중 receive_json 포함                    ->  66   (전부)
추가행 총계                                 ->  77
  그중 recv_frame(                          ->  66
  그중 drain_until(                         ->   0
  그중 import 행                            ->  11
```

**검산 두 갈래가 같은 0을 낸다.**

- 자체 검산: 추가 77 − `recv_frame` 66 − import 11 = **그 밖 0**
- 교차 검산: PR 전체 추가 1333 − `progress.md` 1256 = **77** (위 총계와 일치)

import 11건 = `from .conftest import recv_frame` 모듈 10 + 함수지역 1.
테스트 파일 11개에 정확히 하나씩. 함수지역 1건은 `test_web_reply_discovery.py` 의 기존 지역 import
스타일에 맞춘 것으로 스코프 위반이 아니다.

### 2.3 렌즈 1 — 헬퍼 원문 (`727dcd6:server/tests/conftest.py`)

```python
def recv_frame(ws, timeout: float = 10.0) -> dict:
    box = ...
    def pump() -> None:
        try:
            box["event"] = ws.receive_json()      # <- 동일 호출, 동일 반환
        except Exception as error:                # <- 여기서 예외가 바뀐다 (§2.8)
            box["error"] = error
    worker = threading.Thread(target=pump, daemon=True)   # <- 여기서 스레드가 바뀐다 (§2.9)
    worker.start()
    worker.join(timeout)
    if "event" not in box:
        raise AssertionError("no websocket frame within ...s ...")
    return box["event"]

def drain_until(ws, event_type, *, limit=30):
    for _ in range(limit):
        event = recv_frame(ws)
        if event["type"] == event_type:
            return event
    raise AssertionError(...)
```

→ `recv_frame` = 「다음 프레임 하나」 · `drain_until` = 「특정 타입까지 폐기」.
→ **이 PR 은 `drain_until` 을 0회 추가했다.**

### 2.4 렌즈 1 — 66자리 치환 형태 (전량 육안 확인)

`git diff -U0 fa08651 727dcd6 -- server/tests` 의 모든 `-`/`+` 쌍을 읽었다. 예외 없이 1:1이다:

```
-            assert ws.receive_json()["type"] == "status"
+            assert recv_frame(ws)["type"] == "status"
-            event = ws.receive_json()
+            event = recv_frame(ws)
-            ws.receive_json()  # initial status
+            recv_frame(ws)  # initial status
-            ws_a.receive_json()  # initial status
+            recv_frame(ws_a)  # initial status
-                ws_b.receive_json()  # initial status
+                recv_frame(ws_b)  # initial status
-            gated_event = ws.receive_json()
+            gated_event = recv_frame(ws)
-                frames.append(ws.receive_json())
+                frames.append(recv_frame(ws))
```

수신자(`ws`/`ws_a`/`ws_b`/`socket`), 표현식 위치, 대입 대상, 주석까지 보존.
**재구성 0 · 단정 삭제 0 · 호출 순서 변경 0.**

### 2.5 렌즈 2 — 지목된 부정형 단정 (이름과 내용으로 짚는다)

**(가) `test_a_connection_without_a_stored_timeline_gets_no_replay`** (`test_web_app.py`)

```python
assert recv_frame(ws)["type"] == "status"
_send(ws, type="status_request")
# The very next frame is the requested status — no timeline slipped in.
assert recv_frame(ws)["type"] == "status"
```

증명이 「다음 프레임 하나」에 걸려 있고 `recv_frame` 이 정확히 그 의미다. `drain_until(ws, "status")`
였다면 끼어든 `song_timeline` 을 버리고 통과시켰을 것이다. **그렇게 되지 않았다.**

**(나) `test_a_tick_arriving_while_a_build_is_in_flight_is_dropped`** (`test_web_cue_monitor.py`)

```python
_send(ws, type="cue_monitor_request")  # must be dropped, not queued
# The receive loop is sequential, so a status reply proves the
# second tick has already been dispatched (and dropped).
_send(ws, type="status_request")
assert recv_frame(ws)["type"] == "status"
console.release_hold.set()
assert recv_frame(ws)["type"] == "cue_monitor"
```

coalesce 가드 증명 전체가 「status 가 다음 프레임이다」에 의존한다. 폐기형이었다면 먼저 온
`cue_monitor` 를 버려 증명이 통째로 증발한다. **보존됐다.**

**(다) 지목받지 않았으나 같은 계열** — `test_cue_monitor_request_does_not_fall_through_to_status` 의
`assert event["type"] != "status"` 역시 「다음 프레임」 의미 위에서만 성립한다. 보존됐다.

### 2.6 이관 완결성

```
git grep -c receive_json 727dcd6 -- server/tests
  conftest.py:1            (recv_frame 내부 — 필수)
  test_ws_wait_guard.py:3  (가짜 소켓이 구현한 메서드 — 정상)
```

**호출부의 생 `receive_json` 은 0건.** 남은 2파일은 헬퍼 자신과 그 헬퍼를 재는 가드다.

### 2.7 헬퍼 계약을 지키는 가드가 이미 있다 (t52 산, 이 PR 무변경)

`server/tests/test_ws_wait_guard.py` 가 `recv_frame` 이 정지 대신 실패하는지를 바깥에서 재고,
공허성 방지 단정까지 달고 있다:

```python
assert ws.entered.is_set(), "수신을 시도하지도 않았다면 이 테스트는 공허하다"
assert "no websocket frame within 0.3s" in str(caught.value)
assert elapsed < 5.0, ...
```

### 2.8 렌즈 2 (예외 축) — 66자리 전부를 AST 로 훑었다

리드가 얹은 축이다. 토큰 근접 검색은 이 규모에서 못 믿는다(내 첫 스윕은 토큰 집합이 좁아
`test_web_e2e.py` 를 0건으로 잘못 냈다). **조상 노드를 보는 AST 스캔으로 다시 쟀다.**

판정 기준: `recv_frame` 호출의 조상에 `ast.Try` 또는 `with pytest.raises / pytest.warns /
contextlib.suppress` 가 있는가.

```
$ python3 scan_exc.py          (11개 변경 파일 전량, head 727dcd6 내용)
recv_frame 호출 발견: 66   (66 이어야 한다)     <- 비공허성 단정 통과
예외 포착 블록 안에 있는 자리: 0
```

**🔴 이 0 이 공허하지 않다는 대조군** — 스캐너가 발화할 수 있는지 먼저 쟀다.
날조 코퍼스(예외 블록 3형태 + 깨끗한 1건)를 만들어 쐈다:

```
대조군 호출 수: 4 (4 이어야)
걸린 자리: 3 (3 이어야 — clean 하나만 통과)
   (5, 'with')     <- with pytest.raises
   (9, 'try')      <- try/except
   (15, 'with')    <- contextlib.suppress
```

스캐너는 세 형태 모두 잡고 깨끗한 자리만 통과시킨다. **따라서 실측의 0 은 진짜 0이다.**

**직접 후보 1건도 원문으로 확인했다** — `test_deploy_tauri_seams.py`
`test_the_stage2_window_still_needs_the_token_for_ws`:

```python
with (
    pytest.raises(WebSocketDisconnect),
    client.websocket_connect("/ws", headers=...),
):
    pass  # pragma: no cover
with client.websocket_connect("/ws", ..., subprotocols=[...]) as socket:
    assert recv_frame(socket)["type"]
```

`pytest.raises` 블록은 **토큰 없는 접속**을 감싸는 별개 `with` 이고 `pass` 로 끝난다.
이관된 호출은 그 아래 **성공한 접속** 안이다. **두 블록은 겹치지 않는다.**

**결론: 예외 타입이 `AssertionError` 로 바뀌는 것이 66자리 중 어느 자리의 단정도 바꾸지 못한다.**
근거는 「CI 가 초록이다」가 아니라 자리별 구조 확인이다.

### 2.9 리드의 세 번째 갈래(닫힌 소켓 → 10초 대기)는 **성립하지 않는다** — 측정했다

`Thread.join(timeout)` 은 **스레드가 끝나면 즉시 반환**한다. `pump()` 이 예외를 곧바로 잡고
종료하므로 join 도 곧바로 돌아온다. 추론이 아니라 재서 확인했다 — `recv_frame` 이 의존하는
기전(threading + join(timeout))만 stdlib 로 재현해 쐈다:

```
A) 즉시 예외:  경과 0.000s  ::  no frame within 10.0s (socket closed)
B) 무응답:     경과 1.010s  ::  no frame within 1.0s (None)
```

**즉시 실패는 여전히 0초다. 속도 회귀는 없다.** (B 는 상한이 실제로 작동함을 보이는 양성 대조군.)

다만 A 의 메시지가 **0초 만에 실패해 놓고 「within 10.0s」를 주장한다** — 잔여 위험 §5 에 적는다.

### 2.10 스레드 변경 축 — 이 11개 파일에는 스레드 정체 의존이 없다

리드/구현자가 찾은 두 번째 구조 변화(호출 스레드 → daemon 스레드)를 봤다.

```
git grep -nE 'threading|contextvar|current_thread|threading.local|ThreadPool' 727dcd6 -- <변경 11파일>
  test_web_app.py:13         import threading
  test_web_app.py:256            release = threading.Event()
  test_web_cue_monitor.py:12  import threading
  test_web_cue_monitor.py:525    self.entered_hold = threading.Event()
  test_web_cue_monitor.py:526    self.release_hold = threading.Event()
```

**전부 `threading.Event` 다.** Event 는 어느 스레드가 대기하든 동작이 같고, 스레드 정체·
스레드로컬·`contextvars` 에 기대는 자리는 **0건**이다. `TestClient` 의 수신은 anyio
`BlockingPortal` 을 경유하는데, 포털은 이벤트 루프 스레드 **바깥**의 임의 스레드에서 호출되도록
설계된 물건이다.

⚠️ 다만 이것은 **변경된 11개 파일 범위**에서만 잰 값이다 — §4 참조.

---

## 3. Baseline-attribution (기준 귀속)

| 무엇 | 어디서 · 어떻게 |
|---|---|
| PR 메타(+1333/−66, 12파일, MERGEABLE) | `gh pr view 122`, 이 리뷰 세션 |
| 모든 diff 계수 | `fa08651..727dcd6`, 리뷰 트리 `t54r` |
| 헬퍼·테스트 원문 | `git show 727dcd6:<path>` 블롭 직독 |
| 예외 축 판정 | AST 스캔 + 날조 대조군, head 727dcd6 내용 |
| join 의미 | stdlib 재현 프로브 (§2.9) |
| CI 초록 | `gh api .../runs/32715920533` → `head_sha == 727dcd6`, `conclusion: success` |

**옮긴 값과 잰 값의 구분** — 아래는 내가 재지 않았고 근거로 쓰지 않았다:

- 구현자의 형태별 표(66/66/11/0) — §2.2 는 그 표를 보기 전과 같은 방식으로 내가 다시 센 값이며 일치했을 뿐이다
- run 레인의 로컬 전량 `10023 passed / 12 skipped / 144.71s` — 옮긴 값
- CodeRabbit N/A 근거(t48, 머지된 PR #117·116·110·104) — 리드가 준 옮긴 값
- 리드가 제공한 「예외 토큰을 품은 헬퍼 14개」 목록 — 나는 그 목록을 **걸러내는 대신 대체했다**.
  AST 스캔이 헬퍼 경유 여부와 무관하게 호출 자리의 조상을 직접 보므로, 목록의 정오와 무관하게 판정된다

---

## 4. Gaps (안 본 것)

**이 절이 이 판정에서 가장 중요하다.** 아래는 내가 관측하지 않은 것들이다.

### 4.1 예외/스레드 축의 사각지대 4종 (리드 제시 — 그대로 옮긴다)

내 AST 스캔은 1·2 를 해소하지만 3·4 는 해소하지 못한다. 구분해 적는다.

1. **헬퍼 함수 경유** — 테스트가 부르는 non-test `def` 안의 예외 처리.
   **→ 해소됨.** AST 스캔은 호출 자리의 조상을 직접 보므로 경유 여부와 무관하다. 더해 헬퍼 어디에도
   `receive_json` 이 없다(§2.6: 호출부 생 호출 0건)
2. **픽스처·컨텍스트 매니저의 기대** — 함수 밖이라 토큰 검색이 못 봄.
   **→ 부분 해소.** `with` 형태는 스캔이 조상으로 잡는다. 픽스처 **정의부**에 있는 기대는 못 본다
3. **주석·독스트링 안의 토큰 오탐** — **→ 무관해짐.** AST 는 주석을 노드로 만들지 않는다
4. 🔴 **표현되지 않은 의존** — 「예외가 그대로 올라오길 기대」하는데 코드에 아무 토큰도 안 나오는 자리.
   **→ 해소 안 됨. 원리적으로 정적 스캔으로 못 찾는다.** 내 판정은 이 종류의 자리가 없다고
   **증명하지 않는다.** 다만 그런 자리가 있었다면 예외 타입이 바뀌었을 때 대개 시끄럽게 깨지고,
   CI·로컬 전량이 초록이다 — 이는 정황이지 증명이 아니다

### 4.2 스레드 축의 측정 범위

§2.10 은 **변경된 11개 파일 안에서만** 스레드 정체 의존을 쟀다. 이 테스트들이 부르는
`server/` 프로덕션 코드나 `conftest.py` 의 다른 픽스처가 스레드 정체에 기대는지는 **재지 않았다.**

### 4.3 전량 스위트를 내가 돌리지 않았다

리드 지시(중복 실행 금지 · plan 레인이 창 사용 중)에 따른 것이다. 실행 근거는 CI(§2.1)이며,
그 CI 는 머지될 head 에 귀속됨을 확인했다.

### 4.4 자리별 뮤테이션을 하지 않았다

구현자 말대로 65자리는 정상 경로에서 두 선택지의 행동이 같아 뮤테이션이 안 갈린다.
나는 그 한계를 **우회**했지 **해소**하지 않았다 — 자리별 검증 대신 치환의 성질(§1)로 판정했다.
**그 논증이 틀리면 판정도 틀린다.**

### 4.5 「검사가 지키는 1자리」를 독립 확정하지 못했다

내 추정은 `_fresh_cue_monitor` 의 `cached: True` 재도색 건너뛰기 루프다 — 정상 경로에서 대상 아닌
프레임이 실제로 도착하는 유일한 자리라서다. **추정이며 측정이 아니다.**

### 4.6 로컬 ↔ CI skip 배분 10 차이 (별건 t59 — 판정 근거로 쓰지 않았다)

| | passed | skipped | 합 |
|---|---|---|---|
| 로컬(t54 트리) | 10023 | 12 | **10035** |
| CI | 10013 | 22 | **10035** |

합계는 자리 수까지 같고 수집 총수와도 일치하며, **배분만 10 어긋난다.** 저장소에 환경 조건부
`skipif` 가 실재하나(POSIX `killpg` 유무 · root 여부 · `SRC_TAURI_DIR` 존재 등) **그 10개가 정확히
어느 것인지는 아무도 안 쟀다.** 이 카드와 무관하다는 근거는 있다 — 테스트 추가·삭제 0, 수집 총수 동일.
**별건 t59 로 등재됨.**

### 4.7 런타임 동작 확인 0

콘솔·네트워크에 아무것도 쓰지 않았고 웹소켓을 실제로 열지 않았다. §2.9 의 프로브는 `recv_frame` 이
아니라 그것이 의존하는 **stdlib 기전**을 잰 것이다.

### 4.8 `progress.md` 본문 1256줄은 읽지 않았다

문서이고 렌즈 밖이다. 스코프 판정에서 「테스트 아님」으로만 분류했고, §17.7 만 갱신했다.

---

## 5. Residual-risk (잔여 위험)

### 🟡 이관이 비준되지 않았다 — 회귀를 막는 트립와이어가 없다

**이 카드의 결함은 아니다**(카드 범위는 66자리 이관이고 완결됐다). 리뷰어로서 보고한다.

`test_ws_wait_guard.py` 는 **헬퍼가 상한을 거는지**를 지킨다. 그러나 **호출부가 헬퍼를 쓰는지**를
지키는 것은 아무것도 없다. 지금 호출부의 생 `receive_json` 은 0건이지만, 내일 누가
`ws.receive_json()` 을 새로 쓰면 무한대기가 조용히 되돌아온다 — 그리고 그 실패는 실패가 아니라
**정지**로 나타나 평범한 테스트로는 안 잡힌다. `test_ws_wait_guard.py` 의 독스트링이 스스로 그렇게
말한다.

지금이 이 트립와이어를 놓기에 가장 싼 시점이다 — 0건이 **비준된 0건**이 되기 때문이다.
(`--patch` 가 없으므로 초안은 붙이지 않는다.)

### 🟡 `_fresh_cue_monitor` 의 무한 루프는 시간 상한만으로 안 끊긴다

```python
while True:
    event = recv_frame(ws)
    if event["type"] == "cue_monitor" and not event.get("cached"):
        return event
```

프레임이 **안 오면** 이제 끊긴다(개선). 그러나 대상 아닌 프레임이 **계속 오면** 회수 상한이 없어
영영 돈다. `drain_until` 의 독스트링이 정확히 이 경우를 지적한다.
**이 PR 이 만든 위험은 아니고**(이관 전에도 같은 루프였다), 조건이 `cached` 까지 보므로
`drain_until` 로 그대로 대체할 수도 없다. 후속 카드감.

### 🟡 실패 메시지가 일어나지 않은 상한을 주장한다

§2.9 A: 소켓이 즉시 예외를 던져 **0.000초**에 실패했는데 메시지는
`no websocket frame within 10.0s (socket closed)` 다. 원 예외가 괄호 안에 보존되는 것은 좋으나,
**「10초를 기다렸다」는 서술은 사실이 아니다.** 다음에 이 메시지를 보는 사람이 없는 타임아웃을
쫓을 수 있다. 진단 문구 결함이며 정확성 결함은 아니다.

### 🟢 위험 아님 — 기록용

- `test_deploy_tauri_seams.py` 의 `assert recv_frame(socket)["type"]` 은 **참인지만** 본다(어떤
  프레임이든 만족). 다만 이관 전 `assert socket.receive_json()["type"]` 도 똑같이 약했다 —
  **t54 가 약화시킨 것이 아니다.** 테스트 강도 목록화 시 적어 둘 값은 있다
- `recv_frame` 의 10초 상한이 느린 러너에서 거짓 실패를 낼 수 있으나, 기존에는 그 경우가
  **영구 정지**였다. 교환은 명백히 이득이다
- 타임아웃 후 daemon 워커가 남을 수 있으나 프로세스 종료를 막지 않는다

---

## 부기 — 이 리뷰가 스스로 고친 것

1. 초판은 이 치환을 「의미 보존」이라고만 적었다. **반환값 의미는 보존되지만 예외 전파는 보존되지
   않는다** — 리드 지적이 옳았고 §1·§2.8 에 반영했다.
2. 초판의 예외 스윕은 토큰 집합이 좁아 `test_web_e2e.py` 를 0건으로 잘못 냈다. 리드가 준 헬퍼
   목록과 어긋나는 것을 보고 알아챘고, 근접 검색을 **AST 스캔 + 날조 대조군**으로 대체했다.
3. 초판은 `1f37092` 에서 측정됐다. head 이동 후 **옮기지 않고 전부 다시 쟀다.**
