# t235 — 「구조적 한계」는 API 의 부재가 아니라 별칭의 부재였다

기준: `.claude/worktrees/t235` · 브랜치 `WT-programmer-readback` · base `origin/main bc7add2`
2026-09-01 · **콘솔 접촉 0건** (실기 프로브도, 배포도 안 했다)

## 0. 한 줄

세 레인이 「구조적 한계」로 읽은 `path segment not found: 'Programmer'` 는
**MA3 API 에 프로그래머가 없다는 뜻이 아니다.** 응답기의 `ROOT_ALIASES` 에 그
별칭이 없어서 1번 세그먼트가 `Root()` 자식 이름 대조로 떨어진 결과다.
MA Lighting 의 Object-Free API 는 `Programmer()` · `ProgrammerPart()` ·
`Selection()` 을 `Root()` · `DataPool()` 과 나란히 싣고 있다.

**다만 이 카드는 그 문을 열지 않았다** — 열 수 없어서가 아니라, 여는 행위가
감독 승인 대상이기 때문이다(§5). 설계 · 오프라인 증명 · 적용 절차까지 하고 멈췄다.

## 1. 배차 전제 셋 — 이 트리에서 다시 쟀다

| 전제 | 명령 | 결과 |
|---|---|---|
| base `bc7add2` | `git rev-parse --short origin/main` | **일치** |
| 응답기 `1.6.2` | `grep -n VERSION console/lua/copilot_responder.lua` | `:76 VERSION = "1.6.2"` — **일치** |
| `ROOT_ALIASES` 넷 | `grep -n -A 12 ROOT_ALIASES …` | `:503-508` datapool · root · showdata · patch — **일치** |

셋 다 리드가 「잰 값」이라 명시한 것이고, 셋 다 맞았다.

## 2. 「못 잰 것」과 「없는 것」을 갈랐다

세 레인의 실패 문면은 `path segment not found: 'Programmer'` 하나다. 그 문장이
가능한 원인은 셋인데, 코드를 읽어 둘을 **제거**했다.

| 가설 | 판정 | 근거 |
|---|---|---|
| (a) 자식 목록이 잘려서 안 보였다 | **제거** | 경로 해석은 `M.find_child` → `M.safe_children` 를 쓰고, 그 함수는 `handle:Children()` 을 **전량** 돌려준다(`:469-497`). 24-자식 캡은 **회신 스냅샷을 만들 때** 걸리지 응답기 내부 해석에는 안 걸린다 |
| (b) 이름 대조가 대소문자에 걸렸다 | **제거** | `find_child` 가 `segment:lower()` 와 `safe_name(obj):lower()` 를 비교한다(`:534-539`) |
| (c) `Root()` 의 자식에 그 이름이 없다 | **남음** | 위 둘이 제거되면 이것만 남는다 |

(c)는 참일 수 있고, **그래도 이 카드의 답을 바꾸지 않는다** — 아래 §3 이 그 이유다.

🔴 **이 절이 카드의 「0 옆의 메타데이터를 봐라」에 대한 답이다.** 잘림 가설을
제거한 것은 콘솔이 아니라 **응답기 소스**를 읽어서다. 잘림은 회신의 성질이고
해석의 성질이 아니다.

## 3. 별칭은 **전역 호출**이다 — 그래서 질문이 바뀐다

`ROOT_ALIASES` 의 네 항목은 전부 같은 모양이다:

    datapool = function() return DataPool and DataPool() or nil end,

즉 별칭은 `Root()` 트리를 걷지 않는다. **전역 함수를 부른다.** 그러므로
「별칭을 더할 수 있는가」는 `Root()` 자식 구성과 무관하고, 오직
**「그 전역이 있는가」**로 환원된다.

MA Lighting 문서(Object-Free API)와 커뮤니티 레퍼런스 **둘 다** 다음을 싣는다:

    Programmer()  ProgrammerPart()  Selection()
    SelectionFirst()  SelectionNext()  SelectionCount()

두 출처가 독립이고 같은 목록을 낸다. 따라서 「별칭으로는 못 연다」는 전제는
**문서 수준에서 반증된다.**

⚠️ **범위 경계 — 이 반증이 덮는 것과 안 덮는 것.** 문서에 실렸다는 것은
**이 콘솔 버전이 노출한다**는 뜻도, **그 핸들이 `Children()`·프로퍼티 접근자에
응답한다**는 뜻도 아니다. 전자는 §6 의 `HelpLua` 로, 후자는 배포 후 실기로만
갈린다. 이 문서는 그 둘을 **미측정**으로 남긴다.

## 4. 오프라인 증명 — 별칭 기전이 작동하고, 없어도 안 깨진다

임베디드 Lua 5.4 하네스(`server/tests/lua_mock_env.py`)로 **실제 응답기 소스**를
돌려 두 팔을 다 쟀다. 증거: `evidence/alias_proof.txt` (6 passed).

| 팔 | 무엇을 재나 | 결과 |
|---|---|---|
| 전역 있음 | 목 환경에 `Programmer()`/`Selection()` 을 심고 `state Programmer` | `ok:true`, 자식 둘 판독 |
| 대소문자 | `state programmer` | `ok:true` — 기존 별칭과 같은 규율 |
| 🔴 **전역 없음** | 기본 목 환경(전역 없음)에서 `state Programmer` | `ok:false`, **오늘과 같은 사유** |
| 기존 별칭 | `DataPool` · `Root` · `ShowData` | 셋 다 `ok:true` |
| 🔴 **선례 대조군** | `state Patch` — 별칭은 1.6.2 부터 있는데 목에 전역이 없다 | `ok:false`, `Programmer` 와 **같은 모양** |

마지막 팔이 하중을 진다. 「전역 없는 별칭」은 이 변경이 **새로 만드는 상태가
아니다** — `Patch` 가 이미 그 상태로 돌고 있다. 그러므로 별칭 추가는 그 전역이
없는 콘솔에서 **아무것도 바꾸지 않는다.** 안전 근거가 「내 코드가 조심스럽다」가
아니라 **저장소가 이미 그 갈래를 돌리고 있다**는 관측에서 나온다.

## 5. 🔴 왜 코드를 안 싣고 멈췄나 — 감독 승인 게이트

변경을 만들고, 돌리고, **되돌렸다.** 트리에는 문서와 증거만 남는다.

`console/lua/` 는 바이트 잠금이고, 정당한 개정마다 `granted revision` 재핀이
필요하다(`server/tests/test_overlap_preserve.py`
`TestConsoleLuaReadmeGrantedException`). 그 게이트가 실제로 걸렸다:

    AssertionError: console/lua/copilot_responder.lua
    assert '75ab8248…' == '5555442b…'

그리고 기존 재핀 셋의 사유가 전부 **감독 지시**를 인용한다 — 「user-approved
2026-08-16 진행해줘」 · 「user-directed reland task」 · t104 의 감독 승인.
즉 재핀은 리드가 줄 수 있는 승인이 아니다. 리드도 **배포는 감독 행위**라고
범위에서 뺐는데, 재핀은 그 배포를 가능하게 하는 **같은 계열의 승인 행위**다.

그래서 응답기 소스를 원래 바이트로 되돌렸다. 제안은 그대로 적용 가능한 형태로
남긴다: `evidence/proposed.patch` (Lua 4줄 + 주석 + 검사 6건 + 버전 핀 둘).

## 6. 적용 절차 — 감독이 판단할 때 쓰는 순서

1. **이 콘솔 버전이 그 전역을 노출하는지 먼저 잰다.** 콘솔 커맨드라인에
   `HelpLua` 를 치면 `gma3_library` 폴더에 `grandMA3_lua_functions` 텍스트가
   떨어진다. 그 파일에서 `Programmer` · `Selection` 을 찾는다.
   **쇼파일을 안 건드리는 판독**이고, 배포 없이 §3 의 미측정 하나를 닫는다.
   없으면 여기서 멈춘다 — 답은 「이 버전에서는 별칭으로 못 연다」이고 §7 로 간다.
2. `git apply .moai/reports/t235/evidence/proposed.patch`
3. `test_overlap_preserve.py` 의 `_CONSOLE_LUA_GRANTED_REVISION_DIGESTS` 를
   새 `git hash-object console/lua/copilot_responder.lua` 값으로 재핀하고,
   기존 셋과 같은 형식으로 **사유를 산문으로** 남긴다.
4. 플러그인을 콘솔에 배포한다(감독 행위).
5. 🔴 **배포 확인은 버전으로 한다.** `ping` 이 `1.6.3` 을 답해야 한다.
   `1.6.2` 를 답하면 main 이 무엇을 담고 있든 **그 리그에는 별칭이 없다** —
   실기 1.6.1 / main 1.6.2 였던 전례가 이 저장소에 있다. 그래서 이 제안은
   버전을 올린다: 올리지 않으면 배포 여부를 **원리적으로 구별할 수 없다.**
6. 그 다음에야 `state Programmer` 가 무엇을 답하는지 잰다 — 그것이 §3 의 남은
   미측정(핸들이 `Children()` 에 응답하는가)을 닫는다.

## 7. 대안 경로 — 별칭이 안 열릴 때 무엇을 대신 읽나

리드 지시대로 세워 둔다. 노출이 없거나 핸들이 안 읽히면, 프로그래머 **점유 자체**는
못 읽어도 그 **효과**를 간접 관측할 수 있는 자리가 남는다.

| 경로 | 무엇을 답하나 | 한계 |
|---|---|---|
| `SelectionCount()` / `SelectionFirst()` (같은 Object-Free 목록) | 선택 **개수**와 첫 픽스처 핸들 | 별칭이 아니라 응답기에 **새 동사**가 필요하다. 트리 경로가 아니라 값 반환이라 `state` 로는 못 싣는다 |
| 어트리뷰트 값 되읽기 | 「원래대로 돌아왔다」를 프로그래머가 아니라 **대상 픽스처 쪽에서** 확인 | 이 채널의 프리셋 값 판독이 이미 막혀 있다(t105) — 이 경로가 열려 있다는 증거가 없다 |
| `ClearAll` 후 불변식 | 쏘기 전 비어 있음을 **확인**하는 대신 **강제**한다 | 확인이 아니라 행위다. 안전 조건은 만족시키지만 판정 조건은 못 만든다 |

세 번째가 t135 가 적은 교착의 정확한 형태다 — **안전 조건과 판정 조건이 동시에
만족되지 않는다.** 첫째 경로(새 동사)가 그 교착을 푸는 유일한 후보이고,
별칭보다 큰 작업이다(반환값을 실을 회신 형태부터 정해야 한다).

## 8. 안 잰 것

- **이 콘솔 버전이 `Programmer()` 를 노출하는지** — §6-1 의 `HelpLua` 로만 닫힌다.
  문서 두 출처는 「API 에 있다」까지만 말하고 「이 빌드에 있다」는 안 말한다.
- **핸들이 `Children()`·프로퍼티 접근자에 응답하는지** — 배포 후에만 갈린다.
- **실기 프로브 0건.** 이 회차는 콘솔에 접촉하지 않았다. §2 의 가설 제거는
  전부 **소스 판독**이지 실기 관측이 아니다.
- **`Root()` 의 실제 자식 구성** — (c) 가설이 참인지 안 쟀다. §3 때문에 답을
  바꾸지 않아 재지 않았고, 재려면 콘솔 조회가 필요하다.
- **`SelectionCount()` 계열의 반환 형태** — §7 의 첫 경로를 설계하려면 필요하고,
  이 카드에서 열지 않았다.

## 9. 증거 파일

    .moai/reports/t235/evidence/alias_proof.txt   별칭 검사 6건 통과 (임베디드 Lua)
    .moai/reports/t235/evidence/proposed.patch    적용 가능한 제안 (되돌린 변경의 원본)

Sources (§3 의 API 목록):

- MA Lighting 공식 — Lua Functions, Object-Free API: https://help.malighting.com/grandMA3/2.3/HTML/lua_objectfree.html
- 커뮤니티 레퍼런스 (독립 2차 출처): https://grandma3.bambinito.net/reference/v23/api/
