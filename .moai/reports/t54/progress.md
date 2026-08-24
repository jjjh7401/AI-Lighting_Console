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

1. **상한 레버 = `0.0`. 그 자리에서 KILL 을 한 번이라도 볼 때까지 돌린다.**
   **KILL 1회를 보면 그 자리는 닫힌다.** 시행 수와 KILL 수는 기록하되 **비율을 판정
   근거로 쓰지 않는다.**
2. **KILL 을 한 번도 못 본 자리만 gap 이다.** 그때 비로소 「상한 부재」와 「경합」이
   구분해야 할 문제가 된다.

### 왜 「비율」이 아니라 「KILL≥1」인가 (규칙의 이유 — 지우지 말 것)

레버는 경합에 걸려 있다(§5.2: `recv_frame` 이 `worker.start()` 뒤 `join(timeout)`
을 하므로, 그 사이 pump 스레드가 선점하면 상한과 무관하게 프레임이 들어와 있다).
그래서 증거 구조가 **비대칭**이다:

- **KILL 1회 = 상한이 실재한다는 충분 증거.** 그 자리가 죽을 수 있다는 것을 봤으면
  상한은 있는 것이다.
- **SURVIVED N회 = 아무것도 증명하지 않는다.** 「상한 없음」과 「이번 창이 불리했음」
  을 못 가른다. **N 이 커져도 못 가른다** — 경합이 시간적으로 뭉치기 때문이다.

초판 규칙은 「SURVIVED 가 나오면 10회 반복해 **비율을 재라**」였다. 그 지시는
**재는 대상을 잘못 짚었다.** 표본이 상관돼 있으면 11/12 든 10/10 이든 그 값은
**스케줄러를 잰 값이지 코드를 잰 값이 아니다** — 다른 창에서 돌리면 다른 수가 나온다.

이 문서에 적힌 11/12·10/10 같은 수는 **전부 그런 성질의 값**이다. 품질 지표로 읽지
말 것. 12분의 12 를 목표로 삼는 것은 스케줄러를 목표로 삼는 것이다.
**판정 근거는 오직 KILL ≥ 1 이다.**

이 정정을 끌어낸 관측: `F3`(0/2 → 10회 10/10)와 `G7`(0/2 → 10회 10/10). 초판이
전제한 「SURVIVED 는 드물다」가 틀렸다 — **2회 연속 SURVIVED 가 드물지 않다.**
3. **분류 레버**를 자리마다 함께 쏜다. 갈리지 않는 자리는 §5.4 의 표기를 쓴다
   (「오늘의 경로로는 잴 수 없다」 — 「검사 없음」 아님).
4. 미판정 자리는 **옮기지 말고** 표에 남겨 회신한다.

### 숫자 위생 한 줄

`ruff` 범위(229)와 저장소 전역 `git ls-files '*.py'`(433, 리드 실측)는 **다른 것을
센 값**이다. §9 의 231/229 판정에 세 번째 숫자를 섞지 말 것.

같은 함정을 §12.2 에서 한 번 더 밟았다. 내 `_receive_until` 수는 **21(호출 자리)**
이고 리드의 `grep -c` 는 **22(매칭 줄 수)** 를 냈다. 차이 1은 `import` 줄이다 —
**둘 다 맞고 서로 다른 것을 센 것**이다. 그래서 이 문서의 모든 수는 **무엇을 세는지**
를 함께 적는다(자리 / 줄 / 파일 / 테스트).

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

---

## 12. 배치 t54-d — e2e 5곳 (두 헬퍼가 공존하는 첫 파일)

리드 경고: 「d 부터가 진짜다 — `drain_until` 이 이미 쓰이는 파일이라 두 의미가
한 파일에 공존한다. 전부 `recv_frame` 으로 끝나면 오히려 한 번 더 의심해 봐라.」

### 12.1 대상표

5곳 전부 같은 모양이다 — 접속 직후 **첫 프레임이 `status` 임을 단정**하는 자리.

| # | 파일:행(이관 전) | 소속 테스트 | 판정 |
|---|---|---|---|
| D1 | `:196` | `test_lock_yields_proposal_cards_and_zero_wire_sends` | `recv_frame` |
| D2 | `:215` | `test_panel_stop_is_also_demoted_to_a_proposal` | `recv_frame` |
| D3 | `:281` | `test_a_tile_press_reaches_the_console_wire_after_approval` | `recv_frame` |
| D4 | `:305` | `test_a_rejected_tile_press_reaches_nothing` | `recv_frame` |
| D5 | `:324` | `test_an_unknown_tile_never_reaches_the_wire` | `recv_frame` |

미판정: **0건**.

### 12.2 「전부 recv_frame」을 의심한 결과 — 오히려 근거가 세졌다

이 파일은 두 의미가 섞여 있는 게 맞다. 실측:

```
$ grep -c '_receive_until(' server/tests/test_web_e2e.py     → 21   (= drain_until)
$ grep -c 'recv_frame(ws)'  server/tests/test_web_e2e.py     →  5
$ grep -c 'websocket_connect' server/tests/test_web_e2e.py   → 11
```

11개의 접속 블록 중 **6개는 초기 status 를 아예 읽지 않고** 곧장
`_receive_until(ws, "chat_response")` 등으로 넘어간다(예: `:100-102`, `:122-124`,
`:149-151`, `:171-173`, `:181-183`). 즉 그 6개는 drain 이 초기 status 를 흡수한다.

**원저자가 이미 두 의미를 갈라 놓았다는 뜻이다.** 그리고 내가 옮긴 5곳은 그중
「첫 프레임이 status 임을 **명시적으로 단정**」하기로 선택한 자리들이다. 이 단정은
「언젠가 status 가 온다」보다 엄격하고, 그 엄격함이 바로 `recv_frame` 이 맡는 의미다.

따라서 「전부 `recv_frame`」은 판정을 안 한 결과가 아니라, **이 파일에서 직접 호출로
남아 있던 자리가 마침 전부 그 계열이었기 때문**이다. drain 계열 21곳은 애초에
직접 호출이 아니어서 이 카드의 대상이 아니었다.

### 12.3 전수 대조

```
$ grep -rn '\.receive_json(' server/tests --include='*.py' | wc -l
      41
$ grep -rc '\.receive_json(' server/tests --include='*.py' | grep -v ':0$' | sort -t: -k2 -rn
server/tests/test_web_cue_monitor.py:20
server/tests/test_web_app.py:20
server/tests/conftest.py:1
```

46 − 5 = 41. e2e 는 목록에서 사라졌다. 대상 잔여 **40곳 / 2파일**.

### 12.4 검증

```
$ .venv/bin/ruff check server/tests
All checks passed!
$ .venv/bin/python -m pytest server/tests/test_web_e2e.py -q
11 passed in 11.51s
```

이 파일은 실제 UDP 루프백 + 가짜 콘솔 서버를 띄우는 진짜 E2E 라 느리다(11.5s).

### 12.5 뮤테이션 — §10 규칙

**레버 A — 상한 0.0**: `D1..D5 전부 2/2 KILLED`. 경합 재확인이 필요한 자리 0건.

**레버 B — 분류**(`_receive_until(ws, "status")` 로 교체): `D1..D5 전부 SURVIVED`.

§5.4 표기 적용 — **「오늘의 경로로는 잴 수 없다 · `recv_frame` 이 더 엄격한 쪽 ·
엄격함은 미관측」**.

다만 이 파일에서는 그 「미관측」이 조금 다르게 읽힌다. 여기서는 **같은 파일 안에
두 선택이 공존하고 그 차이가 의도적**이므로, 구별 불가는 「둘 중 아무거나 써도
된다」가 아니라 「의도한 엄격함이 오늘 경로에서 발현되지 않는다」에 가깝다.
t57(기대 밖 프레임 경로)이 열리면 이 5곳이 가장 먼저 갈릴 후보다.

### 12.6 누적

| 배치 | 자리 | 상한 레버 | 분류 레버 |
|---|---|---|---|
| 1 | 7 | 전 자리 KILL | 1 KILLED / 6 구별 불가 |
| b | 8 | 전 자리 KILL (B3 11/12) | 0 / 8 구별 불가 |
| c | 6 | 전 자리 KILL (C2·C6 각 11/12) | 0 / 6 구별 불가 |
| d | 5 | 전 자리 KILL (재확인 불필요) | 0 / 5 구별 불가 |
| **누계** | **26** | **전 자리 KILL 확인** | **1 / 26** |

전수 67 → **41**. 대상 66 → **40**(cue_monitor 20 · app 20).
남은 둘은 리드 분할대로 e/f·g/h 네 배치로 쪼갠다.

---

## 13. 배치 t54-e — cue_monitor 앞 **9**곳 (10 아님 — 경계를 한 자리 당겼다)

### 13.1 배치 경계를 바꾼 이유

리드 분할표는 「cue_monitor 앞 10 / 뒤 10」이었다. 그런데 10번째 자리(`:619`)와
11번째(`:621`)가 **같은 테스트**(`test_a_tick_resolves_the_executors_and_reports_them`)
안에 있다. 10 에서 끊으면 그 테스트가 **반만 이관된 상태**로 배치 경계를 넘는다.

그래서 경계를 한 자리 당겨 **e = 9곳**(테스트 경계에서 절단)으로 잡았다.
남는 f 는 11곳이 되어 10 상한을 하나 넘는다 — 리드 판단이 필요하면 f 를 다시
쪼개면 되고, 그렇지 않으면 11 로 간다. **자리 수보다 테스트를 쪼개지 않는 쪽을
우선**했다.

### 13.2 대상표 — 9곳

| # | 행(이관 전) | 소속 | 판정 | 판정 근거 |
|---|---|---|---|---|
| E1 | `:476` | `test_cue_monitor_request_answers_with_a_cue_monitor_event` | `recv_frame` | 첫 status 한 장 소비 |
| E2 | `:478` | 〃 | `recv_frame` | 요청 직후 다음 한 장이 `cue_monitor` 임을 단정 |
| E3 | `:486` | `test_cue_monitor_request_does_not_fall_through_to_status` | `recv_frame` | 첫 status 한 장 소비 |
| E4 | `:488` | 〃 | `recv_frame` | 회귀 가드 — 다음 한 장이 status **가 아님**을 단정 |
| E5 | `:498` | `..._surfaces_audit_log_history_without_a_console` | `recv_frame` | 첫 status 한 장 소비 |
| E6 | `:500` | 〃 | `recv_frame` | 다음 한 장의 `history` 를 단정 |
| E7 | `:586` | 헬퍼 `_fresh_cue_monitor` 의 `while True:` 안 | `recv_frame` | **드레인 루프의 1회분**. 아래 13.5 참조 |
| E8 | `:607` | `test_a_tick_never_reads_the_five_discarded_dash_sections` | `recv_frame` | 첫 status 한 장 소비 |
| E9 | `:609` | 〃 | `recv_frame` | 다음 한 장이 `cue_monitor` 임을 단정 |

미판정: **0건**.

### 13.3 전수 대조

```
$ grep -rn '\.receive_json(' server/tests --include='*.py' | wc -l
      32
```

41 − 9 = 32. `test_web_cue_monitor.py` 는 20 → **11** 로 줄었다(부분 이관 — 이
파일은 배치가 둘로 쪼개지므로 의도된 중간 상태다). 대상 잔여 **31곳 / 2파일**.

### 13.4 검증 · 뮤테이션

```
$ .venv/bin/ruff check server/tests          → All checks passed!
$ pytest server/tests/test_web_cue_monitor.py → 49 passed in 0.44s
```

**레버 A — 상한 0.0**

```
E1 2/2  E2 2/2  E3 1/2 → +10회 10/10 (합계 11/12)  E4 2/2
E5 2/2  E6 2/2  E7 2/2  E8 2/2  E9 2/2
```

§10 규칙 1 이 또 한 번 작동했다(E3). 경합 재확인이 필요한 자리 누계 4건, **전부
반복에서 11/12 로 죽었다.** 결정적 KILL 불가로 남은 자리는 여전히 0건.

**레버 B — 분류**: `E1..E9 전부 SURVIVED`. §5.4 표기 적용.

### 13.5 🔴 E7 에서 나온 별도 발견 — 이 헬퍼는 **회수 상한이 없다**

`_fresh_cue_monitor` 는 이렇게 생겼다:

```python
while True:
    event = recv_frame(ws)
    if event["type"] == "cue_monitor" and not event.get("cached"):
        return event
```

이관으로 **시간 상한은 생겼다**(프레임 한 장당 10초). 그러나 **회수 상한이 없다** —
기대 밖 프레임이 계속 도착하면 이 루프는 계속 돈다.

⚠️ **정정(리드 반박 수용).** 초판에 「영원히 돈다 · 끝나지 않는 건 마찬가지다」라고
적었는데 **사실이 아니다.** 직접 확인했다:

```
$ sed -n '51,55p' pyproject.toml
# ... exit_on_timeout 은 프로세스를 통째로 끊으므로 임계값이
# 측정으로 선 뒤에만 켠다(t52 §5b 6단계).
faulthandler_timeout = 60
faulthandler_exit_on_timeout = true
```

`exit_on_timeout` 이 **true** 다. 60초 뒤 **프로세스가 통째로 끊긴다.** 무한이
아니고, 그물은 있고, 딱딱하다. 게다가 그 그물은 **내가 t52 에서 직접 넣은 것**이고
그 사실이 같은 파일 51-52행 주석에 이미 적혀 있었다.

정확한 문면은 이것이다:

> 무한 루프가 아니다. **「깨끗한 테스트 실패」 대신 「60초 뒤 런 전체가 죽는 것」**
> 이다. 고칠 값어치는 **그 대가**(나머지 스위트를 다 잃고 트레이스백 덤프만 남는다)
> 에 있지, 무한성에 있지 않다.

없는 결함의 크기를 키워 적으면 다음 사람이 **잘못된 급함**으로 온다. 발견 자체는
유효하지만 등급은 증거를 따라간다.

이것은 conftest 의 `drain_until` 이 `limit=30` 으로 막아 둔 바로 그 구멍이고,
`recv_frame` 독스트링이 명시한 「둘 다 필요하다」의 나머지 절반이다:

> 회수만 있으면 안 오는 프레임에 멈추고, **시간만 있으면 엉뚱한 프레임이 무한히
> 오는 경우를 못 끊는다.**

⚠️ **이 카드에서 고치지 않았다.** 이 카드는 「직접 호출을 승격 헬퍼로 이관」이고,
헬퍼에 회수 상한을 새로 다는 것은 테스트의 대기 의미를 바꾸는 일이라 이관 원칙에
정면으로 걸린다. 리드가 **t58** 로 별건 등재했다.

처방 후보(둘 다 이 카드 밖):
- (a) `_fresh_cue_monitor(ws, *, limit=30)` 로 회수 상한을 추가 — 싸다
- (b) `drain_until` 에 술어(predicate) 인자를 열어 이 헬퍼를 흡수 — 근본적이지만
  conftest 공용 헬퍼의 시그니처를 바꾼다

🔴 t58 착수 조건(리드): **같은 형태의 `while True` + 수신 루프를 전수할 것.**
한 자리만 고치면 계열이 안 마른다.

### 13.6 누적

| 배치 | 자리 | 상한 레버 | 분류 레버 |
|---|---|---|---|
| 1 | 7 | 전 자리 KILL | 1 KILLED / 6 |
| b | 8 | 전 자리 KILL (B3 11/12) | 0 / 8 |
| c | 6 | 전 자리 KILL (C2·C6 11/12) | 0 / 6 |
| d | 5 | 전 자리 KILL | 0 / 5 |
| e | 9 | 전 자리 KILL (E3 11/12) | 0 / 9 |
| **누계** | **35** | **전 자리 KILL 확인** | **1 / 35** |

전수 67 → **32**. 대상 66 → **31**(cue_monitor 11 · app 20).

---

## 14. 배치 t54-f — cue_monitor 뒤 11곳 (파일 완결)

리드 승인: 「11곳 그대로. 쪼개지 마라. **10 은 작업 단위 눈금이지 불변식이 아니다** —
자리 수와 의미 단위가 충돌하면 의미 단위를 우선하고 보고만 하라.」

### 14.1 대상표 — 11곳 (단위: **자리**)

| # | 행(이관 전) | 소속 테스트 | 판정 | 판정 근거 |
|---|---|---|---|---|
| F1 | `:620` | `test_a_tick_resolves_the_executors_and_reports_them` | `recv_frame` | 첫 status 한 장 소비 |
| F2 | `:622` | 〃 | `recv_frame` | 요청 직후 다음 한 장의 `executors` 를 단정 |
| F3 | `:638` | `test_a_second_tick_inside_the_ttl_re_resolves_nothing` | `recv_frame` | 첫 status 한 장 소비 |
| F4 | `:654` | `test_an_expired_ttl_re_reads_the_executor_section` | `recv_frame` | 〃 |
| F5 | `:670` | `test_a_dash_refresh_updates_the_cache_without_waiting_out_the_ttl` | `recv_frame` | 〃 |
| F6 | `:672` | 〃 | `recv_frame` | 다음 한 장이 `dash_catalog` 임을 단정 |
| F7 | `:675` | 〃 | `recv_frame` | 틱 응답 한 장을 소비해 **동기를 맞추는** 자리. 아래 14.2 참조 |
| F8 | `:693` | `test_a_tick_arriving_while_a_build_is_in_flight_is_dropped` | `recv_frame` | 첫 status 한 장 소비 |
| F9 | `:700` | 〃 | `recv_frame` | 🔴 **이 배치에서 판정 근거가 가장 센 자리.** 아래 14.2 |
| F10 | `:702` | 〃 | `recv_frame` | hold 해제 후 다음 한 장이 `cue_monitor` 임을 단정 |
| F11 | `:715` | `test_the_guard_is_not_a_latch_and_releases_on_completion` | `recv_frame` | 첫 status 한 장 소비 |

미판정: **0건**.

### 14.2 리드가 지목한 두 후보 — 판정 근거

**`:700` (F9)** — 코드 옆 주석이 판정을 대신 말해 준다:

```python
_send(ws, type="cue_monitor_request")   # 버려져야 한다(큐에 쌓이면 안 됨)
_send(ws, type="status_request")
# The receive loop is sequential, so a status reply proves the
# second tick has already been dispatched (and dropped).
assert recv_frame(ws)["type"] == "status"
```

이 단정의 힘은 **「수신 루프가 순차이므로 status 응답이 곧 두 번째 틱이 이미
처리(그리고 폐기)되었다는 증명」** 이라는 데 있다. `drain_until` 로 바꾸면 중간
프레임을 버리므로 **그 증명 자체가 사라진다** — 「언젠가 status 가 왔다」는
「status 가 다음 차례였다」를 대신하지 못한다. `recv_frame` 이 아니면 안 되는 자리다.

**`:675` (F7)** — 판정이 가장 약한 자리라 근거를 명시한다. 이 자리는 결과를 쓰지
않고 프레임 한 장을 버려 **동기만 맞춘다**. 기능만 보면 두 헬퍼가 다 동작한다.
그래서 이관 원칙의 원문으로 판정했다 — **「헬퍼가 그 자리의 대기 의미를 바꾸면
안 된다」**. 현재 의미는 「한 장 받는다」이고 `recv_frame` 이 그것을 **정확히**
보존한다. 「동작이 같다」는 이관 사유가 아니다.

`:670`·`:672`·`:675` 의 dash_catalog 혼재는 실제로는 함정이 아니었다. 셋은
**서로 다른 프레임을 한 장씩** 소비할 뿐이고(status → dash_catalog → cue_monitor),
같은 대기를 두 의미로 쓰는 자리가 아니다.

### 14.3 전수 대조 (단위: **자리**)

```
$ grep -c '\.receive_json(' server/tests/test_web_cue_monitor.py
0
$ grep -rn '\.receive_json(' server/tests --include='*.py' | wc -l
      21
$ grep -rc '\.receive_json(' server/tests --include='*.py' | grep -v ':0$'
server/tests/test_web_app.py:20
server/tests/conftest.py:1
```

32 − 11 = 21. **`test_web_cue_monitor.py` 완결**(20/20 이관). 대상 잔여 **20곳 /
1파일** — `test_web_app.py` 만 남았다.

### 14.4 검증 · 뮤테이션

```
$ .venv/bin/ruff check server/tests          → All checks passed!
$ pytest server/tests/test_web_cue_monitor.py → 49 passed in 0.45s
```

**레버 A — 상한 0.0**

```
F1 2/2   F2 2/2   F3 0/2 → +10회 10/10   F4 2/2   F5 2/2   F6 2/2
F7 2/2   F8 1/2 → +10회 10/10   F9 2/2   F10 2/2  F11 2/2
```

🔴 **F3 는 2회 시행이 둘 다 SURVIVED 였다**(0/2). 이전 사례(B3·C2·C6·E3)는 전부
1/2 였는데 F3 는 처음으로 **연속 2회** 살아남았다. 그런데 10회 반복은 10/10 KILLED.

이것이 §10 규칙 1 의 값어치를 가장 크게 보여주는 자리다. 「2회 다 통과했으니
결함」이라는 판정은 **가장 그럴듯한 오판**이고, 실제로는 12회 중 10회가 죽는 자리다.
경합이 **독립적이지 않고 시간적으로 뭉쳐서** 일어난다는 뜻이기도 하다 — 연속 2회
SURVIVED 가 확률적으로 드물지 않다. 규칙을 「2회 중 1회라도」가 아니라
**「SURVIVED 가 1회라도 나오면」** 으로 쓴 것이 정확했다.

경합 재확인 누계 **6건**(B3·C2·C6·E3·F3·F8), **전부 반복에서 죽었다.** 결정적 KILL
불가로 남은 자리는 여전히 **0건**.

**레버 B — 분류**: `F1..F11 전부 SURVIVED`. §5.4 표기 적용.
F9 는 판정 근거가 가장 센 자리인데도 갈리지 않는다 — 배치 b 의 B4 와 같은 모양이고,
**판정이 옳은 것과 판정이 검사로 지켜지는 것은 별개**라는 것을 다시 보여준다.

### 14.5 누적 (단위: **자리**)

| 배치 | 자리 | 상한 레버 | 분류 레버 |
|---|---|---|---|
| 1 | 7 | 전 자리 KILL | 1 KILLED / 6 |
| b | 8 | 전 자리 KILL (B3) | 0 / 8 |
| c | 6 | 전 자리 KILL (C2·C6) | 0 / 6 |
| d | 5 | 전 자리 KILL | 0 / 5 |
| e | 9 | 전 자리 KILL (E3) | 0 / 9 |
| f | 11 | 전 자리 KILL (F3·F8) | 0 / 11 |
| **누계** | **46** | **전 자리 KILL 확인** | **1 / 46** |

전수 67 → **21**. 대상 66 → **20**(`test_web_app.py` 20곳, 1파일).
미판정 누계 **0건**. 완결된 파일 **9개** / 대상 11파일.

---

## 15. 배치 t54-g — app 앞 10곳

리드가 경계를 독립 검산했다: app 20자리는
`53 69 70 78 81 107 127 145 160 162 | 170 172 177 189 191 213 221 245 273 321` —
**`162/170` 에서 정확히 10/10** 이고 테스트를 쪼개지 않는다.

### 15.1 접속 블록 훑기 (리드 조언 — 판정 전 형태 파악)

`test_web_app.py` 도 `drain_until as _receive_until` 을 이미 쓴다. e2e 에서 얻은
방식대로 「접속 블록마다 초기 status 를 읽는지」부터 훑었다:

- 읽는 블록 — 이 배치의 10자리가 전부 여기 속한다
- **안 읽는 블록** — `test_chat_round_trip`(`:87`)은 접속 직후 곧장
  `_receive_until(ws, "chat_response")` 로 간다. drain 이 초기 status 를 흡수한다

e2e 와 같은 그림이다. **원저자가 두 의미를 이미 갈라 놓았고**, 직접 호출로 남은
자리는 「첫 프레임(또는 다음 한 장)을 명시적으로 단정/소비」하기로 고른 쪽이다.

### 15.2 대상표 — 10자리

| # | 행(이관 전) | 소속 테스트 | 판정 | 판정 근거 |
|---|---|---|---|---|
| G1 | `:53` | `test_connect_receives_an_initial_status_event` | `recv_frame` | 첫 프레임의 `type`·`health`·`live_lock` 을 단정 |
| G2 | `:69` | `test_a_new_connection_is_replayed_the_last_song_timeline` | `recv_frame` | 첫 한 장이 status |
| G3 | `:70` | 〃 | `recv_frame` | 🔴 **그 다음 한 장이 `song_timeline`** — 재생(replay)이 status **바로 뒤에** 온다는 순서 주장이다 |
| G4 | `:78` | `test_a_connection_without_a_stored_timeline_gets_no_replay` | `recv_frame` | 첫 한 장이 status |
| G5 | `:81` | 〃 | `recv_frame` | 🔴 **이 배치에서 근거가 가장 세다.** 아래 15.3 |
| G6 | `:107` | `test_vectorworks_upload_starts_a_guided_chat_turn` | `recv_frame` | 첫 status 한 장 소비 |
| G7 | `:127` | `test_unrecognised_upload_is_named_not_silently_routed` | `recv_frame` | 〃 |
| G8 | `:145` | `test_layout_image_upload_is_stored_and_acked_over_the_wire` | `recv_frame` | 〃 |
| G9 | `:160` | `test_malformed_message_yields_a_korean_protocol_error` | `recv_frame` | 〃 |
| G10 | `:162` | 〃 | `recv_frame` | 깨진 입력 직후 **다음 한 장**이 `error` 임을 단정 |

미판정: **0건**. 판정을 밀어붙인 자리 없음 — 10자리 모두 「한 장」 의미가 명시적이다.

### 15.3 G5 — 부정형 순서 단정

```python
assert recv_frame(ws)["type"] == "status"
_send(ws, type="status_request")
# The very next frame is the requested status — no timeline slipped in.
assert recv_frame(ws)["type"] == "status"
```

이 테스트의 이름 자체가 `..._gets_no_replay` 이고, 주석이 단정의 내용을 말한다 —
**「바로 다음 프레임이 요청한 status 다. 타임라인이 끼어들지 않았다.」**

`drain_until(ws, "status")` 로 바꾸면 중간에 `song_timeline` 이 끼어들어도 그것을
버리고 status 를 찾아내므로 **테스트가 막으려던 회귀를 정확히 통과시킨다.**
F9(`:700`)와 같은 계열의 부정형 단정이고, `recv_frame` 이 아니면 안 되는 자리다.

G3 도 같은 축의 긍정형이다 — 「status **다음**이 song_timeline」이라는 순서 주장.

### 15.4 전수 대조 (단위: 자리)

```
$ grep -c '\.receive_json(' server/tests/test_web_app.py
10
$ grep -rn '\.receive_json(' server/tests --include='*.py' | wc -l
      11
```

21 − 10 = 11. 대상 잔여 **10자리 / 1파일**(`test_web_app.py` 뒤 10 = 배치 h).

### 15.5 검증 · 뮤테이션

```
$ .venv/bin/ruff check server/tests   → All checks passed!
$ pytest server/tests/test_web_app.py → 21 passed in 0.95s
```

**레버 A — 상한 0.0 (§10 개정 규칙: KILL ≥ 1 이면 닫힘)**

| 자리 | 결과 | 판정 |
|---|---|---|
| G1·G2·G3·G4·G5·G10 | 2/2 KILLED | 닫힘 |
| G6 | 1/2 → +10회 10/10 | 닫힘 |
| G7 | **0/2** → +10회 10/10 | 닫힘 |
| G8 | 1/2 → +10회 10/10 | 닫힘 |
| G9 | 1/2 → +10회 10/10 | 닫힘 |

**KILL 을 한 번도 못 본 자리(= gap): 0건.**

🔴 이 배치는 **10자리 중 4자리**가 재시행을 요구했다(누적 중 가장 높은 밀도).
그리고 `G7` 이 `F3` 에 이어 **두 번째 0/2** 다. 초판 규칙이 전제한 「SURVIVED 는
드물다」가 틀렸다는 증거가 하나 더 쌓였다 — §10 개정의 직접 근거다.

여기 적은 `10/10`·`11/12` 같은 수는 **스케줄러 측정치**다. 품질 지표가 아니다(§10).

**레버 B — 분류**: `G1..G10 전부 SURVIVED`. §5.4 표기 적용.
G5 는 근거가 가장 센 자리인데도 갈리지 않는다 — 이 테스트에는 **애초에 타임라인이
없어서**(`..._without_a_stored_timeline_...`) 끼어들 프레임 자체가 존재하지 않기
때문이다. 「오늘의 경로로는 잴 수 없다」의 교과서적 사례다: 막으려는 회귀가
**아직 일어나지 않았으므로** 두 헬퍼가 구별되지 않는다.

### 15.6 누적 (단위: 자리)

| 배치 | 자리 | 상한 레버(gap) | 분류 레버 |
|---|---|---|---|
| 1 · b · c · d · e · f | 46 | 0 | 1 KILLED / 45 |
| g | 10 | 0 | 0 / 10 |
| **누계** | **56** | **0** | **1 / 56** |

전수 67 → **11**. 대상 66 → **10**. 미판정 누계 **0건**. 완결 파일 **9 / 11**.

---

## 16. 배치 t54-h — app 뒤 10곳 (대상 완결)

### 16.1 대상표 — 10자리

| # | 행(이관 전) | 소속 테스트 | 판정 | 판정 근거 |
|---|---|---|---|---|
| H1 | `:171` | `test_status_request_returns_a_status_event` | `recv_frame` | 첫 status 한 장 소비 |
| H2 | `:173` | 〃 | `recv_frame` | 요청 직후 다음 한 장이 status |
| H3 | `:178` | `test_lock_toggle_round_trip` | `recv_frame` | 첫 status 한 장 소비 (이후 대기는 `_receive_until`) |
| H4 | `:190` | `test_stale_approval_decision_is_reported` | `recv_frame` | 첫 status 한 장 소비 |
| H5 | `:192` | 〃 | `recv_frame` | 만료된 결정 직후 다음 한 장이 `error` |
| H6 | `:214` | `test_disconnect_does_not_deny_another_sessions_pending_approval` | `recv_frame(ws_a)` | 세션 A 의 첫 status |
| H7 | `:222` | 〃 | `recv_frame(ws_b)` | 세션 B 의 첫 status. **두 소켓이 한 테스트에 있다** — 변수만 다르고 의미는 같다 |
| H8 | `:246` | `test_own_disconnect_still_denies_own_pending_approval` | `recv_frame` | 첫 status 한 장 소비 |
| H9 | `:274` | `test_second_chat_while_busy_gets_a_busy_event` | `recv_frame` | 첫 status 한 장 소비 |
| H10 | `:322` | `test_heartbeat_loop_pushes_status_changes` | `recv_frame` | 첫 프레임이 status 임을 단정하고, **그 뒤 드레인 루프는 이미 `_receive_until`(limit=30)** 이다 — 원저자가 두 의미를 한 블록 안에서 갈라 쓴 자리 |

미판정: **0건**.

### 16.2 전수 대조 — 대상 **완결**

```
$ grep -rn '\.receive_json(' server/tests --include='*.py'
server/tests/conftest.py:104:            box["event"] = ws.receive_json()
$ grep -rn '\.receive_json(' server/tests --include='*.py' | wc -l
       1
```

11 − 10 = 1. 남은 **1자리는 승격 헬퍼 `recv_frame` 자신의 수신 호출**이며 §1 에서
처음부터 배제 기준으로 명시한 자리다.

**대상 66자리 → 0. 11파일 전부 완결.**

### 16.3 검증

```
$ .venv/bin/ruff check server/tests          → All checks passed!
$ .venv/bin/ruff format --check server/tests → 229 files already formatted
$ pytest server/tests/test_web_app.py        → 21 passed in 0.95s
```

### 16.4 뮤테이션 — 개정 규칙(KILL ≥ 1)으로 처음 돌린 배치

| 자리 | 결과 |
|---|---|
| H1·H2·H3·H5·H6·H7·H8 | 닫힘 (시행 1회에 KILL) |
| H4·H10 | 닫힘 (시행 2회) |
| H9 | 닫힘 (시행 3회) |

**gap(KILL 을 한 번도 못 본 자리): 0건.**

개정 규칙은 **판정이 더 정확할 뿐 아니라 훨씬 싸다.** 초판대로면 SURVIVED 가 난
자리마다 10회를 더 돌려 이 배치에서만 30회 이상을 태웠을 텐데, 개정 규칙에서는
총 시행이 **14회**로 끝났다. 「비율을 재려는 것」이 비용의 원인이었고, 그 비율은
애초에 코드가 아니라 스케줄러를 재던 값이다(§10).

**레버 B — 분류**: `H1..H10 전부 SURVIVED`. §5.4 표기 적용.

---

## 17. 카드 종합 — t54 대상 완결

### 17.1 최종 수치 (단위를 함께 적는다)

| 항목 | 착수 시 | 종료 시 |
|---|---|---|
| `.receive_json(` **자리** (server/tests 전체) | 67 | **1** |
| 그중 **이관 대상 자리** (conftest 헬퍼 1 제외) | 66 | **0** |
| 대상 **파일** | 11 | **0** |
| **미판정 자리** | — | **0** |

### 17.2 배치별

| 배치 | 파일 | 자리 | 상한 레버 gap | 분류 레버 KILL |
|---|---|---|---|---|
| 1 | review · session_progress · reply_discovery · console_probe · tauri_seams | 7 | 0 | **1** |
| b | dash · layout_image | 8 | 0 | 0 |
| c | handshake | 6 | 0 | 0 |
| d | e2e | 5 | 0 | 0 |
| e | cue_monitor (앞) | 9 | 0 | 0 |
| f | cue_monitor (뒤) | 11 | 0 | 0 |
| g | app (앞) | 10 | 0 | 0 |
| h | app (뒤) | 10 | 0 | 0 |
| **합계** | **11파일** | **66** | **0** | **1 / 66** |

### 17.3 이 카드가 실제로 산 것 — 과장 없이

**샀다**: 66자리의 웹소켓 수신이 이제 **시간 상한 아래**에 있다. 오지 않는 프레임
하나가 스위트를 세우는 일은 이 자리들에서 일어나지 않는다. 66자리 전부에서
「상한이 실재한다」를 KILL 로 관측했다(gap 0).

**안 샀다**: 「헬퍼를 옳게 골랐다」는 66자리 중 **1자리**에서만 검사가 지킨다.
나머지 65자리는 두 헬퍼가 **오늘의 경로로는 구별 불가**하다(§5.4). 이것은 결함이
아니라 관측 가능성의 한계이고, **t57**(기대 밖 프레임 경로)이 열려야 갈린다.

**남겼다**: `_fresh_cue_monitor` 의 회수 상한 부재 → **t58**. 무한 루프가 아니라
「깨끗한 테스트 실패 대신 60초 뒤 런 전체가 죽는 것」이다(§13.5).

### 17.4 이 카드에서 규칙이 두 번 고쳐졌다 — 둘 다 오판을 막았다

1. **초판(0.001s)**: 판별력 0. 7/7 통과 → 「이관이 헛것」이라 적을 뻔했다.
   실측으로 프레임 도착이 10µs~100µs 임을 확인하고 레버를 내렸다(§5.1).
2. **2판(0.0, 2회 → 비율)**: 재는 대상이 틀렸다. `F3`·`G7` 의 **0/2 → 10/10** 이
   드러냈다 — 경합이 시간적으로 뭉치므로 비율은 스케줄러 측정치다.
   **3판: KILL ≥ 1 이면 닫힘**(§10).

두 번 다 **「자를 먼저 의심한 것」** 이 오판을 막았다. 통과가 나왔을 때 결론을
내리기 전에 레버를 검산한 것, 그것이 이 카드에서 가장 값어치 있는 절차였다.

**누가 무엇을 했는지는 정확히 적는다**(리드가 이 사실을 남기라 했고, 리드가 준
문면은 run 레인 몫을 과장한다):

| 정정 | 관측 | 규칙 재작성 |
|---|---|---|
| 1판 → 2판 (`0.001s` 는 판별력 0) | run 레인 (계단 실측 §5.1) | run 레인이 제안, 리드 채택 |
| 2판 → 3판 (비율은 스케줄러 측정치) | run 레인 (`F3` 0/2 → 10/10, §14.4) | **리드** — 「증거 구조가 비대칭이다」라는 논증은 리드가 세웠다 |

즉 **두 자 모두 리드가 준 것이고, 두 번 다 run 레인의 실측이 그것을 깨뜨렸으며,
세 번째 자의 핵심 논증은 리드가 세웠다.** 「둘 다 run 레인이 고쳤다」는 부정확하다.

일반화할 것은 사람이 아니라 절차다 — **자를 준 쪽과 자를 쓰는 쪽이 다르면, 자가
틀렸을 때 그것을 처음 보는 것은 쓰는 쪽이다.** 그래서 쓰는 쪽은 「통과」가 나왔을
때 결론 대신 자를 의심하고, 준 쪽은 그 보고를 받으면 **규칙을 방어하지 말고 다시
논증**해야 한다. 이 카드에서 그 왕복이 두 번 돌았다.

### 17.5 아직 안 한 것

- **전량 스위트 재실행**: 배치 1 시점에 1회 초록(10023 passed / 12 skipped, §4.4)을
  받았고, 그 뒤 b~h 8배치가 더 들어갔다. **카드 닫기 전 전량 1회가 남았다** —
  창(window)이 plan 레인에 있어 리드 허가를 기다린다.
- 배치별로는 대상 파일 테스트를 매번 돌려 초록을 확인했다(각 §).
