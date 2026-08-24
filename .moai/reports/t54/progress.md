# t54 — 웹소켓 수신 직접 호출을 승격 헬퍼로 이관

- 카드: t54 (class B · plan 생략)
- 워크트리: `.claude/worktrees/t54` · 브랜치 `WT-recv-migrate`
- 기준 커밋: `fa08651` (= origin/main, 실측)
- 이 문서는 **배치 1** 의 증거다. 배치 2 이후는 하위 카드로 배차 예정.

---

## 1. 기준 (감독 확정)

`server/tests/**/*.py` 의 모든 `.receive_json(` 호출에서, conftest 승격 헬퍼
내부 1곳(`server/tests/conftest.py`, `recv_frame` 의 pump 함수)을 뺀 **66곳 /
11파일**. 대입형 22곳만 하는 안은 기각됨 — 나머지 44곳도 시간 상한이 없다.

착수 시점 전수 (기준 커밋 `fa08651`):

```
$ grep -rn '\.receive_json(' server/tests --include='*.py' | wc -l
      67
$ grep -rc '\.receive_json(' server/tests --include='*.py' | grep -v ':0$' | sort -t: -k2 -rn
server/tests/test_web_cue_monitor.py:20
server/tests/test_web_app.py:20
server/tests/test_web_handshake.py:6
server/tests/test_web_e2e.py:5
server/tests/test_web_layout_image.py:4
server/tests/test_web_dash.py:4
server/tests/test_web_session_progress.py:2
server/tests/test_web_review.py:2
server/tests/test_web_reply_discovery.py:1
server/tests/test_web_console_probe.py:1
server/tests/test_deploy_tauri_seams.py:1
server/tests/conftest.py:1
```

**배제 기준(명시)**: `conftest.py:1` 은 헬퍼 `recv_frame` 이 실제 수신을 수행하는
자리이므로 이관 대상이 아니다. 이 1곳을 빼서 **66곳 / 11파일**.

---

## 2. 헬퍼 둘의 대기 의미 — 자리마다 판정한다

| 헬퍼 | 위치 | 대기 의미 |
|---|---|---|
| `recv_frame(ws, timeout=10.0)` | `conftest.py:80` | **다음 프레임 하나** — 오지 않으면 실패 |
| `drain_until(ws, event_type, limit=30)` | `conftest.py:116` | **특정 타입이 나올 때까지** 버린다 (내부에서 `recv_frame` 사용) |

섞으면 조용히 통과하는 테스트가 생긴다. 배치 1 의 7자리는 **전부 `recv_frame`**
으로 판정했고, 미판정으로 남긴 자리는 **0건**이다. 판정 근거는 아래 표의
"판정 근거" 열에 자리마다 적었다.

---

## 3. 배치 1 대상표 — 7곳 / 5파일

| # | 파일:행(이관 전) | 원문 | 판정 | 판정 근거 |
|---|---|---|---|---|
| 1 | `test_web_review.py:297` | `ws.receive_json()  # initial status` | `recv_frame` | 첫 status 프레임 하나를 버리는 자리. 특정 타입까지 흘려보내는 게 아니라 **그 한 장**을 소비한다 |
| 2 | `test_web_review.py:299` | `event = ws.receive_json()` | `recv_frame` | 전송 직후 **바로 다음 한 장**이 error 임을 단정한다. `drain_until` 로 바꾸면 중간에 다른 프레임이 와도 통과해 단정이 약해진다 |
| 3 | `test_web_session_progress.py:124` | `assert ws.receive_json()["type"] == "status"` | `recv_frame` | 첫 프레임의 타입 자체를 단정 |
| 4 | `test_web_session_progress.py:128` | `frames.append(ws.receive_json())` | `recv_frame` | 루프가 **모든 중간 프레임을 모아** progress 계열을 검사한다. `drain_until` 은 중간 프레임을 버리므로 의미가 바뀐다 — 여기서 둘을 섞으면 progress 0건이어도 통과한다 |
| 5 | `test_web_reply_discovery.py:566` | `event = ws.receive_json()` | `recv_frame` | 접속 직후 첫 status 프레임 한 장 |
| 6 | `test_web_console_probe.py:375` | `event = ws.receive_json()` | `recv_frame` | 접속 직후 첫 status 프레임 한 장 |
| 7 | `test_deploy_tauri_seams.py:385` | `assert socket.receive_json()["type"]` | `recv_frame` | 접속 직후 첫 프레임 한 장 |

미판정: **0건**.

이관 후 잔여: **60곳 / 6파일**(conftest 1 포함) = 대상 기준 **59곳 / 5파일**.

```
$ grep -rn '\.receive_json(' server/tests --include='*.py' | wc -l
      60
$ grep -rc '\.receive_json(' server/tests --include='*.py' | grep -v ':0$' | sort -t: -k2 -rn
server/tests/test_web_cue_monitor.py:20
server/tests/test_web_app.py:20
server/tests/test_web_handshake.py:6
server/tests/test_web_e2e.py:5
server/tests/test_web_layout_image.py:4
server/tests/test_web_dash.py:4
server/tests/conftest.py:1
```

67 − 7 = 60. 배치 1 의 5파일은 목록에서 **완전히 사라졌다**(부분 이관 아님).

---

## 4. 증거

### 4.1 검증 환경 — 어느 트리에서 났는가

t47 ④(워크트리마다 `.venv` 의 `.pth` 가 자기 트리를 가리킨다)를 피하려고
**이 트리 전용 venv 를 새로 만들었다**. 옆 트리(`../t52/.venv`)를 빌려 쓰면
`server` 가 t52 에서 해석되어 **다른 트리를 검증**하게 된다.

```
$ cat ../t52/.venv/lib/python3.11/site-packages/_editable_impl_*.pth
/Users/studiox/Documents/Claude/Code/AI-Lighting_Console/.claude/worktrees/t52   ← 빌려 쓰면 안 되는 이유

$ uv venv --python 3.11 .venv
$ uv pip install --python .venv/bin/python -e .
$ uv pip install --python .venv/bin/python --group dev
$ .venv/bin/python -c "import server; print(server.__file__)"
/Users/studiox/Documents/Claude/Code/AI-Lighting_Console/.claude/worktrees/t54/server/__init__.py   ← t54
```

### 4.2 린트 · 서식

```
$ .venv/bin/ruff check server/tests
All checks passed!
$ .venv/bin/ruff format --check server/tests
229 files already formatted   ← 정정, 아래 §9 참조
```

### 4.3 테스트 (카드 범위 — 전량 아님)

```
$ .venv/bin/python -m pytest \
    server/tests/test_web_review.py \
    server/tests/test_web_session_progress.py \
    server/tests/test_web_reply_discovery.py \
    server/tests/test_web_console_probe.py \
    server/tests/test_deploy_tauri_seams.py \
    server/tests/test_ws_wait_guard.py -q
124 passed in 4.71s
```

`test_ws_wait_guard.py`(t52)를 함께 돌린 것은 승격 헬퍼의 상한 자체가
살아 있는지를 같은 실행에서 확인하기 위해서다.

### 4.4 전량 스위트 (리드 1회 허가)

```
$ .venv/bin/python -m pytest server/tests -q -p no:cacheprovider
10023 passed, 12 skipped in 152.39s (0:02:32)
```

**어느 트리에서 났는지 대조**(t47 ⑤ 절차 — 수집 총수):

```
$ .venv/bin/python -m pytest server/tests --collect-only -q -p no:cacheprovider
10035 tests collected in 3.97s
```

10023 + 12 = 10035 — 자리 수까지 일치하므로 이 실행은 t54 트리에서 났다.
배치 1 이 건드린 공유 import 면이 다른 파일을 깨뜨리지 않았다.

---

## 5. 뮤테이션 검증 — 레버를 먼저 보정해야 했다

### 5.1 지시된 레버(0.001s)는 **판별력이 0** 이었다

자리마다 상한을 `0.001` 로 낮춘 1차 시행: **7/7 SURVIVED**.

원인은 이관이 부실해서가 아니라 **레버가 너무 관대해서**다. 이 자리들의 프레임은
이미 버퍼에 있어 1ms 안에 도착한다. 한 자리(#1)로 상한을 계단식으로 내려 실측:

```
timeout=0.001   -> SURVIVED
timeout=0.0001  -> SURVIVED
timeout=0.00001 -> KILLED
timeout=0.0     -> KILLED
```

즉 도착 지연이 **10µs ~ 100µs** 대역이고, 0.001s 는 그 위 100배 지점이라
아무것도 가르지 못한다. 「통과했으니 이관이 헛것」이 아니라 **자가 먼저 틀렸다**.

### 5.2 경계 부근에서는 결과가 뒤집힌다 (관측됨)

`0.00001` 로 7자리를 돌린 시행에서 #1·#2 가 SURVIVED 로 나왔는데, **같은 값·같은
자리**를 단독으로 6회 반복하니 6/6 KILLED 였다. 같은 뮤테이션이 실행마다 갈린다.

기전(가설 아님, 코드로 확인): `recv_frame` 은 `worker.start()` 뒤에
`worker.join(timeout)` 을 한다. `start()` 와 `join()` 사이에 pump 스레드가 먼저
스케줄되어 수신을 끝내면 **상한 값과 무관하게** 프레임이 들어와 있다. 그래서
도착 지연 대역 근처의 어떤 상한도 결정적 레버가 못 된다.

### 5.3 확정 시행 — 상한 0.0, 자리마다 2회

```
M1 2/2 KILLED | test_web_review.py            | test_stale_review_decision_yields_a_korean_error
M2 2/2 KILLED | test_web_review.py            | test_stale_review_decision_yields_a_korean_error
M3 2/2 KILLED | test_web_session_progress.py  | test_a_chat_turn_streams_progress_frames_then_the_response
M4 2/2 KILLED | test_web_session_progress.py  | test_a_chat_turn_streams_progress_frames_then_the_response
M5 2/2 KILLED | test_web_reply_discovery.py   | test_the_websocket_status_frame_carries_the_mismatch
M6 2/2 KILLED | test_web_console_probe.py     | test_the_websocket_status_frame_carries_the_verdict
M7 2/2 KILLED | test_deploy_tauri_seams.py    | test_the_stage2_window_still_needs_the_token_for_ws
---
sites: 7  runs: 14  survived: 0
```

죽는 자리의 실패 메시지는 전부 `recv_frame` 의 단정(`no websocket frame within …s`)
이었다 — 즉 그 자리의 대기가 **정말 헬퍼의 상한을 통과한다**.

복원은 `git checkout` 이 아니라 **원문 보관 + SHA-256 대조**로 했다(미커밋분 보호).
7자리 × 모든 시행에서 복원 후 해시 일치를 확인했고, 최종 `git diff --stat` 은
아래와 같이 의도한 변경만 남았다.

```
$ git diff --stat
 server/tests/test_deploy_tauri_seams.py   | 3 ++-
 server/tests/test_web_console_probe.py    | 3 ++-
 server/tests/test_web_reply_discovery.py  | 3 ++-
 server/tests/test_web_review.py           | 5 +++--
 server/tests/test_web_session_progress.py | 5 +++--
 5 files changed, 12 insertions(+), 7 deletions(-)
```

(+12 = 새 import 5행 + 수정된 호출 7행, −7 = 수정 전 호출 7행)

### 5.4 분류 뮤테이션 — 헬퍼를 **옳게** 골랐는가 (리드 지적으로 소급)

5.3 까지의 상한 뮤테이션이 죽이는 것은 「이 자리에 상한이 걸렸다」뿐이다.
「헬퍼를 옳게 골랐다」는 아무것도 안 지킨다. 그래서 자리마다 판정한 헬퍼를
**다른 헬퍼 의미로 바꿔** 빨개지는지 실측했다.

| # | 자리 | 바꾼 의미 | 결과 |
|---|---|---|---|
| 1 | `test_web_review` 첫 status 버리기 | `drain_until(ws, "status")` | **SURVIVED** |
| 2 | `test_web_review` error 단정 | `drain_until(ws, "error")` | **SURVIVED** |
| 3 | `test_web_session_progress` 첫 status | `drain_until(ws, "status")` | **SURVIVED** |
| 4 | `test_web_session_progress` 모으는 루프 | `drain_until(ws, "chat_response", limit=40)` | **KILLED** |
| 5 | `test_web_reply_discovery` 첫 status | `drain_until(ws, "status")` | **SURVIVED** |
| 6 | `test_web_console_probe` 첫 status | `drain_until(ws, "status")` | **SURVIVED** |
| 7 | `test_deploy_tauri_seams` 첫 프레임 | `drain_until(socket, "status")` | **SURVIVED** |

#4 의 실패 메시지:

```
E  AssertionError: 소켓에 진행 프레임이 0건이다: ['chat_response']
E  assert []
```

§3 표에서 산문으로만 적었던 「모으는 루프를 drain_until 로 바꾸면 progress
0건이어도 통과한다」가 **이제 검사로 확인됐다** — 정확히 그 모양으로 빨개진다.

**나머지 6자리는 두 헬퍼가 현재 경로상 구별 불가하다.** 전부 프레임 한 장을
읽는 자리라, 기대 타입을 그대로 넣은 `drain_until` 은 정상 경로에서 첫 프레임이
곧 그 타입이므로 **행동이 정말로 동일**하다. 그래서 뮤테이션이 죽지 않는다.

⚠️ 이것을 **「검사 실패」로 읽지 말 것.** 이관이 틀린 것도, 검사를 빠뜨린 것도
아니다. 이 자리에서 `recv_frame` 은 **더 엄격한 쪽**이고(`drain_until` 은 중간에
엉뚱한 프레임이 끼어도 조용히 넘어가 단정을 약화시킨다), 그 엄격함은 **기대 밖
프레임이 실제로 먼저 올 때만 관측된다.** 오늘의 경로에는 그런 프레임이 없다.

그러므로 6자리의 표기는 「검사가 없다」가 아니라 **「오늘의 경로로는 잴 수 없다 —
`recv_frame` 이 더 엄격한 쪽이며 그 엄격함은 미관측」** 이다. 없는 결함을 고치러
오지 말 것. 기대 밖 프레임 경로를 만드는 일은 **t57** 로 별건 등재됐다.

복원은 전 시행 SHA-256 대조로 확인했다(7/7 restore ok).

---

## 6. 남은 59곳 — 분할표 제안 (리드 회신용)

20곳짜리 둘은 단독으로도 카드 10 상한을 넘으므로 반씩 쪼갠다.

| 하위 카드 | 대상 | 자리 수 | 비고 |
|---|---|---|---|
| t54-b | `test_web_dash.py` 4 + `test_web_layout_image.py` 4 | 8 | 소형 둘. 배치 1 패턴 그대로 |
| t54-c | `test_web_handshake.py` 6 | 6 | 단일 파일 |
| t54-d | `test_web_e2e.py` 5 | 5 | 이미 `drain_until as _receive_until` 을 쓰는 파일 — 두 헬퍼가 한 파일에 공존하므로 판정을 자리마다 적을 것 |
| t54-e | `test_web_cue_monitor.py` 앞 10 | 10 | 파일 내 상단 절반 |
| t54-f | `test_web_cue_monitor.py` 뒤 10 | 10 | 파일 내 하단 절반 |
| t54-g | `test_web_app.py` 앞 10 | 10 | 이미 `drain_until as _receive_until` 사용 파일 |
| t54-h | `test_web_app.py` 뒤 10 | 10 | 〃 |

합계 59곳. 한 파일을 둘로 쪼개는 t54-e/f·g/h 는 **같은 브랜치에서 순차**로 해야
충돌이 없다(같은 파일을 두 카드가 동시에 건드리면 안 된다).

⚠️ t54-d·g·h 는 `drain_until` 이 이미 쓰이는 파일이라 **두 의미가 한 파일에
섞여 있다**. 배치 1 처럼 「전부 recv_frame」으로 끝나지 않을 가능성이 높고,
미판정 자리가 나올 수 있다.

---

## 7. 미검증 · 잔여 위험

- ~~전량 스위트 미실행~~ → **해소**. 리드가 1회 허가해 돌렸고 초록이다(§4.4).
  수집 총수 대조로 이 트리에서 난 실행임도 확인했다. 다음 전량은 **카드 닫을 때
  한 번만** 돌린다 — 배치마다 돌리면 코드가 아니라 기계를 재는 꼴이 된다.
- **분류가 뮤테이션으로 갈리는 자리는 15곳 중 1곳뿐**(§5.4 · §8.4). 나머지 14곳은
  두 헬퍼가 **현재 경로상 구별 불가**해서지, 검사를 빠뜨려서가 아니다. 가르려면
  「기대 밖 프레임이 먼저 오는」 경로가 있어야 하고 그건 테스트를 고치는 일이다 —
  **t57** 로 별건 등재됐다. 이 항목을 결함 목록으로 읽지 말 것.
- **푸시 성공은 게이트 통과가 아니다**. pre-push 훅의 `ci-local` 갈래는 저장소
  루트에 `Makefile` 이 없어 조용히 건너뛴다(t55). 이 카드의 초록은 위 4·5절의
  명령이 근거이고, 푸시 결과는 근거가 아니다.
- **뮤테이션 레버의 한계**. 5.2 에서 확인했듯 상한 낮추기는 도착 지연 대역 부근에서
  결정적이지 않다. 상한 `0.0` 은 14/14 를 죽였지만 이는 확률적으로 강한 것이지
  구조적으로 보장된 것이 아니다. **결정적인 그물이 필요하다면** 직접 호출을
  금지하는 기계적 검사(허용목록이 줄어드는 tripwire)가 별도로 있어야 한다 —
  이 카드 범위 밖이라 제안만 남긴다.
- **콘솔 쓰기 0** — 이 카드에서 콘솔에 보낸 명령은 없다(테스트 전부 FakeConsole
  / TestClient 기반).

---

## 8. 배치 t54-b — dash 4 + layout_image 4 = 8곳

리드 배차: b → c → d → e → f → g → h 순, 같은 브랜치에서 순차.

### 8.1 대상표

| # | 파일:행(이관 전) | 원문 | 판정 | 판정 근거 |
|---|---|---|---|---|
| B1 | `test_web_dash.py:576` | `ws.receive_json()  # initial status` | `recv_frame` | 첫 status 한 장 소비 |
| B2 | `test_web_dash.py:578` | `event = ws.receive_json()` | `recv_frame` | 요청 직후 **다음 한 장**이 `dash_catalog` 임을 단정 |
| B3 | `test_web_dash.py:588` | `ws.receive_json()  # initial status` | `recv_frame` | 첫 status 한 장 소비 |
| B4 | `test_web_dash.py:590` | `event = ws.receive_json()` | `recv_frame` | 회귀 가드 — 다음 한 장이 status **가 아님**을 단정. 중간 프레임을 버리는 의미로 바꾸면 단정 대상 자체가 사라진다 |
| B5 | `test_web_layout_image.py:166` | `ws.receive_json()  # initial status` | `recv_frame` | 첫 status 한 장 소비 |
| B6 | `test_web_layout_image.py:174` | `event = ws.receive_json()` | `recv_frame` | 업로드 거부 직후 다음 한 장이 `error` 임을 단정 |
| B7 | `test_web_layout_image.py:188` | `ws.receive_json()  # initial status` | `recv_frame` | 첫 status 한 장 소비 |
| B8 | `test_web_layout_image.py:190` | `event = ws.receive_json()` | `recv_frame` | 〃 |

미판정: **0건**. 8곳 전부 `recv_frame`.

### 8.2 전수 대조

```
$ grep -rn '\.receive_json(' server/tests --include='*.py' | wc -l
      52
$ grep -rc '\.receive_json(' server/tests --include='*.py' | grep -v ':0$' | sort -t: -k2 -rn
server/tests/test_web_cue_monitor.py:20
server/tests/test_web_app.py:20
server/tests/test_web_handshake.py:6
server/tests/test_web_e2e.py:5
server/tests/conftest.py:1
```

60 − 8 = 52. dash·layout_image 두 파일은 목록에서 완전히 사라졌다.
대상 잔여 **51곳 / 4파일**.

### 8.3 검증

```
$ .venv/bin/ruff check server/tests
All checks passed!
$ .venv/bin/ruff format --check server/tests
229 files already formatted
$ .venv/bin/python -m pytest server/tests/test_web_dash.py server/tests/test_web_layout_image.py -q
68 passed in 1.05s
```

### 8.4 뮤테이션 — 두 레버 (리드 규칙 1·2)

**레버 A — 상한 0.0, 자리마다 2회**

```
B1 2/2 KILLED   B2 2/2 KILLED   B3 1/2 KILLED   B4 2/2 KILLED
B5 2/2 KILLED   B6 2/2 KILLED   B7 2/2 KILLED   B8 2/2 KILLED
```

🔴 **B3 가 1/2 로 갈렸다.** §5.2 에서 기전으로 적은 뒤집힘이 상한 `0.0` 에서도
실제로 나타난 것이다. 지어내지 않고 같은 자리를 10회 더 반복해 비율을 쟀다:

```
B3 x10: KKKKKKKKKK  → 10/10 KILLED
```

합계 B3 는 12회 중 11회 KILLED. 즉 레버 `0.0` 은 **확률적으로 강하지만 결정적이
아니다** — `recv_frame` 이 `worker.start()` 와 `worker.join(timeout)` 사이에
pump 스레드에게 선점당하면 상한과 무관하게 프레임이 들어와 있다. 1회 시행으로
SURVIVED 가 나오면 **결함이 아니라 경합일 수 있으므로 반복해서 확인할 것.**

**레버 B — 분류 (판정한 헬퍼를 다른 의미로 교체)**

```
B1..B8  전부 SURVIVED
```

배치 1 §5.4 와 같은 결과다. 8곳 전부 프레임 한 장을 읽는 자리라 기대 타입을 그대로
넣은 `drain_until` 은 정상 경로에서 행동이 동일하다. 8곳 모두 §5.4 와 같은 표기를
쓴다 — **「오늘의 경로로는 잴 수 없다 · `recv_frame` 이 더 엄격한 쪽 · 엄격함은
미관측」**. 「검사 없음」이 아니다.

특히 B4 는 판정 근거가 가장 센 자리인데도(중간 프레임을 버리면 「status 가 아님」을
잴 대상이 사라진다) 뮤테이션으로는 갈리지 않는다 — **판정이 옳은 것과 판정이
검사로 지켜지는 것은 별개**라는 것을 이 자리가 잘 보여준다.

---

## 9. 자체 정정 — §4.2 의 `231`

배치 1 §4.2 에 `ruff format --check server/tests` 결과를 **231 files** 로 적었으나
**재현되지 않는다.** 같은 명령이 지금은 일관되게 229 를 낸다.

대조:

```
$ find server/tests -name '*.py' -not -path '*/__pycache__/*' | wc -l
     229
$ git ls-files server/tests | grep -c '\.py$'
229
$ git ls-files --others --exclude-standard server/tests | grep '\.py$' | wc -l
       0
$ .venv/bin/ruff format --check server/tests --no-respect-gitignore
229 files already formatted
```

`git show --stat 68a57f1` 에 삭제 파일이 없으므로 트리에서 .py 파일이 사라진 것도
아니다. 기준 커밋 이래 줄곧 229 다. **231 이 어디서 나왔는지는 규명하지 못했다** —
그럴듯한 이야기를 지어 붙이지 않는다. 확인된 것은 「정확한 수는 229 이고, 231 은
내 보고의 오기」 하나뿐이다.

이 정정이 바꾸는 판정은 없다(`ruff format --check` 는 두 경우 모두 변경 0건).

---

## 10. 뮤테이션 레버 규칙 (리드 확정 · 이 카드의 남은 배치에 적용)

1. **상한 레버 = `0.0`, 자리마다 2회.** SURVIVED 가 1회라도 나오면 결함으로 단정하지
   말고 **10회 반복해 비율을 잰다.** 레버가 경합(§5.2 의 start/join 선점)에 걸려
   있으므로 1회 SURVIVED 는 「지켜지지 않음」과 「이번엔 pump 가 먼저 뛰었음」을
   가르지 못한다. B3(11/12)가 후자였고, 1회만 보고 결함이라 적었으면 **없는 결함을
   보고한 것**이 된다.
2. 10회 반복에서도 SURVIVED 가 남는 자리는 **「경합으로 결정적 KILL 불가 — 상한
   존재는 리뷰로 보증」** 으로 표에 적는다. **비율을 적되 그 비율을 「통과」로 세지
   말 것.**
3. **분류 레버**를 자리마다 함께 쏜다. 갈리지 않는 자리는 §5.4 의 표기를 쓴다
   (「오늘의 경로로는 잴 수 없다」 — 「검사 없음」 아님).
4. 미판정 자리는 **옮기지 말고** 표에 남겨 회신한다.

### 숫자 위생 한 줄

`ruff` 범위(229)와 저장소 전역 `git ls-files '*.py'`(433, 리드 실측)는 **다른 것을
센 값**이다. §9 의 231/229 판정에 세 번째 숫자를 섞지 말 것.

---

## 11. 배치 t54-c — handshake 6곳

### 11.1 대상표

| # | 파일:행(이관 전) | 원문 | 판정 | 판정 근거 |
|---|---|---|---|---|
| C1 | `test_web_handshake.py:213` | `event = ws.receive_json()` | `recv_frame` | 접속 직후 첫 프레임의 `v`·`type` 을 단정 |
| C2 | `:221` | `event = ws.receive_json()` | `recv_frame` | Stage-1 회귀 가드 — 첫 프레임 한 장 |
| C3 | `:229` | `event = ws.receive_json()` | `recv_frame` | 정책 미설정 경로 — 첫 프레임 한 장 |
| C4 | `:257` | `gated_event = ws.receive_json()` | `recv_frame` | 게이트된 접속의 **첫 프레임**을 비교 대상으로 잡는다 |
| C5 | `:259` | `open_event = ws.receive_json()` | `recv_frame` | 열린 접속의 첫 프레임. C4 와 **바이트 동일**을 단정하므로 둘 다 「첫 한 장」이어야 비교가 성립한다 |
| C6 | `:291` | `ws.receive_json()` | `recv_frame` | 토큰 유출 스캔 전 접속 수명주기를 한 바퀴 돌리는 자리 — 프레임 한 장 소비 |

미판정: **0건**. 6곳 전부 `recv_frame`.

### 11.2 전수 대조

```
$ grep -rn '\.receive_json(' server/tests --include='*.py' | wc -l
      46
$ grep -rc '\.receive_json(' server/tests --include='*.py' | grep -v ':0$' | sort -t: -k2 -rn
server/tests/test_web_cue_monitor.py:20
server/tests/test_web_app.py:20
server/tests/test_web_e2e.py:5
server/tests/conftest.py:1
```

52 − 6 = 46. handshake 는 목록에서 완전히 사라졌다. 대상 잔여 **45곳 / 3파일**.

### 11.3 검증

```
$ .venv/bin/ruff check server/tests
All checks passed!
$ .venv/bin/python -m pytest server/tests/test_web_handshake.py -q
29 passed in 1.46s
```

### 11.4 뮤테이션 — §10 규칙 적용

**레버 A — 상한 0.0**

```
C1 2/2 KILLED   C2 1/2 → +10회 10/10 KILLED (합계 11/12)
C3 2/2 KILLED   C4 2/2 KILLED
C5 2/2 KILLED   C6 1/2 → +10회 10/10 KILLED (합계 11/12)
```

🟢 **§10 규칙 1 이 곧바로 값을 했다.** C2·C6 이 1/2 로 나왔는데, 보정 전 규칙(2회
시행으로 판정)이었다면 **없는 결함 2건을 보고**할 뻔했다. 10회 반복이 둘 다
10/10 KILLED 로 갈랐다 — B3(11/12)와 같은 비율이고 같은 기전(§5.2 선점)이다.

경합으로 결정적 KILL 이 불가한 자리는 **0건**(모든 자리가 반복에서 전부 죽었다).

**레버 B — 분류**

```
C1..C6  전부 SURVIVED
```

6곳 모두 프레임 한 장을 읽는 자리다. §5.4 표기를 쓴다 — **「오늘의 경로로는 잴 수
없다 · `recv_frame` 이 더 엄격한 쪽 · 엄격함은 미관측」**. 「검사 없음」이 아니다.

C4·C5 는 한 가지를 덧붙일 만하다: 두 자리가 **바이트 동일**을 단정하므로, 둘 중
하나만 다른 의미로 바뀌면 비교의 전제가 깨진다. 그런데도 정상 경로에서는
`drain_until(ws, "status")` 가 첫 프레임을 그대로 돌려주므로 갈리지 않는다 —
구별 불가의 전형적인 모양이다.

### 11.5 누적

| 배치 | 자리 | 상한 레버 | 분류 레버 |
|---|---|---|---|
| 1 | 7 | 14/14 KILLED | 1 KILLED / 6 구별 불가 |
| b | 8 | 15/16 + B3 10/10 재확인 | 0 KILLED / 8 구별 불가 |
| c | 6 | 10/12 + C2·C6 각 10/10 재확인 | 0 KILLED / 6 구별 불가 |
| **누계** | **21** | 전 자리 KILL 확인 | **1 / 21** 만 분류가 갈린다 |

전수 67 → **46**. 대상 기준 66 → **45**.
