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
231 files already formatted
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

- **전량 스위트 미실행**. 리드 상시 제약(plan 레인이 t18 로 돌고 있음)에 따라
  전량은 돌리지 않았다. 배치 1 의 5파일 + `test_ws_wait_guard.py` 만 돌렸다.
  다른 파일이 이 5파일의 헬퍼/픽스처를 재사용해 깨질 가능성은 **미검증**이다.
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
