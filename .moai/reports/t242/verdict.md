# t242 — 별칭을 실었다. 배포는 싣지 않았다.

기준: 브랜치 `WT-programmer-alias` · base `origin/main 801fc65`
2026-09-02 · **콘솔 접촉 0건** (프로브도, 배포도 안 했다)

## 0. 한 줄

t235 가 만들어 두고 되돌린 제안을 **감독 승인 아래 실제로 실었다**.
응답기 `1.6.2 → 1.6.3`, `ROOT_ALIASES` 에 `programmer` · `programmerpart` ·
`selection` 셋. 배포는 이 승인에 들어 있지 않고, 이 브랜치에도 없다.

## 1. 승인 — 무엇이 열렸고 무엇이 안 열렸나

리드(`lx-seq-05`)가 감독 응답을 그대로 옮겨 왔다:

> 「승인한다 — 패치만, 배포는 별도」
> `console/lua/copilot_responder.lua` 를 `1.6.2 → 1.6.3` 으로 고치고 **PR 까지** 간다.
> 콘솔 배포는 **이 승인에 안 들어있다**.

| 열린 것 | 안 열린 것 |
|---|---|
| 소스 패치 · 재핀 · 검사 · PR | 콘솔 배포 · 실기 프로브 · 머지 |

🔴 **직접 관측하지 못한 것 하나 — 이 절의 승인 문면은 리드가 옮긴 값이다.**
감독 창을 내가 읽은 것이 아니다. t235 가 「승인의 출처를 확인할 수 없다」로
멈춰 세운 그 자리에, 이번에는 리드가 자기가 직접 물었다고 명시했다. 그 명시를
근거로 진행했고, 그것이 이 작업 전체가 서 있는 전제다.

## 2. 전제 재측정 — 착수 시점에 다시 쟀다

| 전제 | 명령 | 결과 |
|---|---|---|
| base 응답기 `1.6.2` | `grep -n 'VERSION = ' console/lua/copilot_responder.lua` | `:76 VERSION = "1.6.2"` — 일치 |
| base 바이트 `5555442b…` | `git hash-object console/lua/copilot_responder.lua` | `5555442b6754efb3add61587da4f8f0b3378e417` — 패치 전제와 일치 |
| `ROOT_ALIASES` 넷 | `grep -n -A 8 'local ROOT_ALIASES'` | `:503-508` datapool · root · showdata · patch — 일치 |
| t235 제안 적용 가능 | `git apply --check …/proposed.patch` | 종료 0 |

t235 의 PR #286 은 이미 머지됐다(`gh pr list --head WT-programmer-readback`
→ `MERGED`). 그래서 이 카드는 그 브랜치를 잇지 않고 `origin/main` 에서 새로 땄다.

## 3. 실은 것

| 파일 | 변경 |
|---|---|
| `console/lua/copilot_responder.lua` | `VERSION` `1.6.2→1.6.3` · `ROOT_ALIASES` 에 별칭 3 · 사유 주석 |
| `server/tests/test_overlap_preserve.py` | 재핀 `5555442b…→75ab8248…` + 사유 산문 |
| `server/tests/test_lua_responder.py` | 버전 핀 + `TestProgrammerAliases` 6건 |
| `server/tests/test_responder_deploy.py` | 버전 핀 |
| `server/tests/test_responder_roundtrip.py` | 버전 핀 3자리 |

마지막 줄은 t235 제안에 **없던 것**이다. 라운드트립 검사가 `1.6.2` 를 리터럴로
세 자리에 박고 있어 버전 범프만으로 떨어진다. 제안의 미측정이 아니라
제안이 못 본 자리다 — 전량 회귀가 잡았다.

## 4. 증거

| 주장 | 명령 | 관측 |
|---|---|---|
| 잠금 게이트 통과 | `pytest test_overlap_preserve.py -k ConsoleLua` | `4 passed` |
| 그 게이트가 공허하지 않다 | 재핀을 옛 해시로 되돌리고 재실행 | `1 failed` — `test_the_revised_assets_match_the_granted_digests_exactly` 가 정확히 떨어진다. 복원 후 다시 `4 passed` |
| 응답기 계열 | `pytest test_lua_responder.py test_responder_deploy.py` | `117 passed` |
| 전량 회귀 | `pytest -q -p no:cacheprovider` | **`10905 passed · 12 skipped`** |
| 린트 | `ruff check` · `ruff format --check` (변경 4파일) | `All checks passed` · `already formatted` |

**대조군 두 팔이 제안 안에 들어 있다** — 전역이 있으면 열리는 팔과,
없으면 오늘과 같은 사유로 실패하는 팔. 뒤엣것이 안전 근거다. 그리고 `patch`
별칭이 목 환경에서 이미 그 상태(전역 없는 별칭)로 돌고 있다는 세 번째 팔이
「전역 없는 별칭」이 이 변경이 만든 새 상태가 아님을 고정한다.

🔴 안 잰 것: **base 트리의 전량 회귀 수를 이 브랜치에서 따로 재지 않았다.**
「10905」는 패치 후 값이고, 증가분이 새 검사 6건인지 다른 이유인지는
이 회차가 답하지 않는다.

### 함정 하나 — 바이트코드 캐시가 낡은 상수를 물고 있었다

공허성 대조군을 돌린 직후 전량 회귀에서 잠금 게이트가 **떨어졌다**. 소스에는
새 해시가 있는데 검사는 옛 해시를 읽었다. 원인은 `.pyc` 캐시다: 두 해시가
40자로 **길이가 같아** 파일 크기가 안 변했고, 복원 `cp` 가 같은 초 안에
들어가 mtime 도 캐시를 무효화하지 못했다.

🔴 **일반형: 같은 길이의 리터럴을 되돌리는 뮤테이션은 파이썬 캐시를 못 깬다.**
뮤테이션 실험 뒤에는 `__pycache__` 를 지우거나 `-p no:cacheprovider` 로 돌려라.
안 그러면 통과·실패가 소스가 아니라 캐시를 재는 것이 된다.

## 5. 안 잰 것 (배포 없이는 못 재는 것)

| 미측정 | 왜 못 쟀나 | 어떻게 닫나 |
|---|---|---|
| 이 콘솔이 `Programmer()` 전역을 노출하는가 | 콘솔 접촉 0 (리드는 `HelpLua` 로 확인했다고 전했으나 **내가 본 출력이 아니다**) | 콘솔에 `HelpLua` → `gma3_library/grandMA3_lua_functions` 에서 `Programmer`·`Selection` 검색. 쇼파일 무접촉 |
| 돌아온 핸들이 `Children()` 에 답하는가 | 배포가 필요하다 (감독 행위) | 배포 후 `state Programmer` |
| 배포가 실제로 먹었는가 | 〃 | 🔴 `ping` 이 **`1.6.3`** 을 답해야 한다 |

**`1.6.2` 를 답하면 main 이 무엇을 담고 있든 그 리그에는 별칭이 없다.**
이 저장소에 실기 1.6.1 / main 1.6.2 였던 전례가 있다. 버전을 올린 이유가
그것이고, 올리지 않으면 배포 여부를 원리적으로 구별할 수 없다.

## 6. 배포 절차 — 문서로만 남긴다 (실행은 별도 승인)

1. 이 PR 머지
2. `console/lua/copilot_responder.lua` 를 콘솔 플러그인 자리에 배포 (**감독 행위**)
3. `ping` 이 `1.6.3` 을 답하는지 확인 — 아니면 2번이 안 먹은 것이고 여기서 멈춘다
4. `state Programmer` 를 쏜다. 이것이 §5 의 둘째 미측정을 닫는다

## 7. 4번이 안 열릴 때 — 갈래를 미리 세운다

리드 지시대로 세워 둔다. 별칭이 열려도 핸들이 `Children()` 에 안 답할 수 있고,
그때는 **별칭 축이 끝난다**.

| 갈래 | 조건 | 무엇을 해야 하나 |
|---|---|---|
| A — 열린다 | `state Programmer` 가 자식을 답한다 | 끝. 프로그래머 점유가 이 채널로 읽힌다 |
| B — 노출은 있는데 핸들이 안 읽힌다 | `ok:false`, 또는 자식 0인데 실제로는 차 있다 | 🔴 **`SelectionCount()` / `SelectionFirst()` 새 동사가 유일한 경로다.** 별칭이 아니라 응답기 확장이고, 값 반환이라 `state` 로는 못 싣는다 — 회신 형태부터 정해야 한다. 별칭보다 큰 작업 |
| C — 전역 자체가 없다 | `HelpLua` 목록에 `Programmer` 부재 | 이 버전에서는 별칭으로 못 연다. t235 verdict §7 의 간접 관측 셋으로 간다 |

B 와 C 는 **다른 카드**다. 이 카드는 A 를 가능하게 하는 데까지다.

## 8. 이 카드가 안 한 것

- 콘솔에 아무것도 안 썼다 (프로브도, 배포도)
- 머지 안 했다 — 리드가 확인하고 한다
- `PROTOCOL.md` 를 안 건드렸다. 새 동사도, 새 토큰도, 새 회신 필드도 없어서
  **회선 규약이 안 바뀐다**. 주소로 부를 수 있는 1번 세그먼트 집합만 늘었다
