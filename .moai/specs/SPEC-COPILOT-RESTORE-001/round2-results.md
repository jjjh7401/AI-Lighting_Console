# 실기 프로브 라운드 2 — 결과

> **콘솔 쓰기 0건.** 전부 `--skip-exec` / `props` 읽기 전용.
> 🔴 **어느 항목도 「확정」이 아니다.** 전부 **이 쇼파일의 이 객체**에 한정된 관측이다.

## A. 측정 조건 (이 라운드의 전제 — 다음 세션은 이것부터 재확인)

    응답기      version=1.6.1  plugin=CopilotResponder   (ping 실측)
    프로세스     app_gma3  pid 47006
    포트        송신 127.0.0.1:8000 · 수신 9005
                ※ 수신 9000 은 무응답(타임아웃). 9005 로만 왕복이 성립한다

| 대상 | `childCount` | 라운드 1 | 비고 |
|---|---|---|---|
| `Patch/Stages/1/Fixtures` | **0** | 86 | **바뀜** |
| `DataPool/Groups` | **0** | 0 | 그대로 |
| `DataPool/Pages` | 1 | — | |
| `DataPool/Pages/1` | **0** | — | 실행기 없음 |
| `DataPool/Sequences` | 1 | 1 | |
| `DataPool/Sequences/1` (`Default`) | 2 | 2 | OffCue · CueZero |
| `DataPool/PresetPools` | **14** | 0 | **바뀜** |

**쇼파일은 바뀌었다** — 다만 더 빈 쪽으로. 픽스처가 86→0 이 되었고 프리셋풀이 0→14 가
되었다. 이 두 방향이 왜 갈렸는지는 **이 라운드로 답할 수 없다**(기록만 한다).

## B. 어디까지 돌았나

| # | 대상 | 결과 |
|---|---|---|
| 0 | 왕복 + 양성 | **PASS** — ping ok(v1.6.1), `state DataPool/Sequences` ok |
| 1 | 측정 조건 | **완료** — 위 A 표 |
| 2 | 날조 대조군 | **PASS** — 아래 C |
| 3 | ② `Count()`+`Ptr(i)` | **미측정 — 재료 부재** (`Groups childCount 0`) |
| 4 | 개별 그룹 `introspect` | **미측정 — 재료 부재** (같음) |
| 5 | ④ Executor 우회 | **미측정 — 재료 부재** (`Pages/1 childCount 0`) |
| 6 | 값 형태 | **미측정** — 4 에 딸림 |

## C. 대조군 — 이 쇼파일에서 판별력이 있는가

날조 필드와 실제 필드가 **다른 모양으로** 답한다. 판별력 있음.

    날조   props DataPool/Sequences/1 · ZZFAKE_NO_SUCH_FIELD
           → ok:false  e:"property not readable: ZZFAKE_NO_SUCH_FIELD"
    양성   props DataPool/Sequences/1 · Name
           → ok:true   t:"string"  v:"Default"

## D. 부재의 모양 — 다음 세션을 위한 기준점

**없는 대상**에 물으면 판독 실패가 아니라 경로 해석 단계에서 별도 사유가 온다:

    state DataPool/Groups/1            → responder error: path segment not found: '1'
    state DataPool/Pages/1/Executor 201 → responder error: path segment not found: 'Executor 201'

그래서 3~6 의 `미측정`은 **「물었는데 못 읽었다」가 아니라 「물을 대상이 없다」**이다.
이 둘을 섞으면 ②④ 의 전제를 잘못 뒤집게 된다.

## E. 미검증 — 확정으로 적지 않은 것

- ② `Count()`+`Ptr(i)` 로 그룹 멤버를 읽을 수 있는가 — **모름.** 그룹이 0개다.
- ④ Executor 우회로 배정 시퀀스를 알 수 있는가 — **모름.** 실행기가 0개다.
- 개별 그룹 `introspect` 에 멤버 열거 필드가 있는가 — **모름.**
- 픽스처 86→0, 프리셋풀 0→14 로 갈린 이유 — **모름.** 관측만 했다.
- 수신 9000 무응답의 원인 — **모름.** 9005 로 우회했을 뿐이다.

## F. 다음 라운드가 필요로 하는 것

**그룹이 최소 1개, 실행기가 최소 1개 있는 쇼파일.** 그것이 없으면 3~6 은 이번과
똑같이 `path segment not found` 로 끝난다. `BLOCKED16-001/probe.md` §2 의 P-1·P-3 도
같은 재료를 기다리고 있다(P-6 은 추가로 **시퀀스 재생 상태**를 요구한다 — 별도 라운드).
