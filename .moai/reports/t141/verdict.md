# t141 — 두 어휘의 연결을 데이터로 두고, 파생 대신 트립와이어를 놓았다

- 카드: t141 · SPEC-COPILOT-LXSEQ-003 · 기준 `08edf8b` · 브랜치 `WT-beam-vocab-canon`
- 선행: `.moai/reports/t141/sheet-token-census.md`(`1af9a08`) · `design.md`(`b58cd7d`)
- **콘솔 접촉 0.**

## 0. 카드가 물은 것과 답

물음은 「어느 쪽으로 통일하나」가 **아니었다**. 두 어휘가 서로 다른 것이므로
「각각 어디에 정본으로 세우고 매핑을 어디에 두나」였다.

**답: 정본은 이미 갈려 있었다. 없던 것은 정본이 아니라 연결이다.**

| 어휘 | 정본 | 상태 |
|---|---|---|
| 콘솔에 **쏘는** 문자열 | `server/looks/schema.py` | 있음. PRESERVE 게이트 둘이 잠금(t149) |
| 감독 **시트에 적힌** 토큰 | `server/lxseq/preset_parser.py` | 있음 |
| **둘 사이 매핑** | — | **없었다.** 산문과 검사 하나가 관계를 *서술*할 뿐이었다 |

`Frost` 의 콘솔 이름이 `Frost1` 이라는 사실은 코드 어디에도 데이터로 없었다.

## 1. 통일이 불가능한 기계적 이유

`preset_parser.py:213` 은 목록 항목을 시트 토큰의 **접두사**로 쓴다:

    목록 `Prism`  · 시트 `Prism`   ->  "prism".startswith("prism")    참
    목록 `Prism1` · 시트 `Prism`   ->  "prism".startswith("prism1")   거짓
    목록 `Prism`  · 시트 `Prism1`  ->  "prism1".startswith("prism")   참

**짧은 항목이 엄격히 더 관대한데, 콘솔이 받는 이름은 시트 토큰보다 길다** — 정확히
반대 방향이다. 한 목록이 두 일을 동시에 못 한다. 취향 문제가 아니다.

## 2. 선행 측정 — 시트 토큰 전수 (아무도 센 적 없던 것)

시트 4개 전량: `Zoom` 4 · `Gobo` 3 · `Prism` 2 · `Frost` 1.
아는 이름 12개 중 **0회가 8개**(`Focus`·`Shutter`·`Position`·`Control`·`Shapers`·
`Video`·`Iris`·`Dimmer`). 상세와 한정은 `sheet-token-census.md`.

⚠️ **「목록이 과하다」로 읽지 마라.** 다음 쇼 시트가 무엇을 쓸지 안 쟀다.

## 3. 낸 것

    _SHEET_TO_CONSOLE_ATTRIBUTE = Focus->Focus1 · Frost->Frost1
                                  Prism->Prism1 · Shutter->Shutter1
    _PROBE_REJECTED = tuple(_SHEET_TO_CONSOLE_ATTRIBUTE)

**매칭 정의역은 키 쪽이다.** 여기 둔 이유 셋: 소비자가 이 파서다 · 콘솔 쪽 정본은
PRESERVE 잠금이라 못 쓴다 · 매핑은 콘솔 어휘의 성질이 아니라 **이 리그 시트와 콘솔
사이**의 성질이다(다른 시트가 오면 매핑이 바뀌지 콘솔 어휘가 안 바뀐다).

값의 **출처 등급이 갈린다**는 것도 주석에 적었다: `Focus1`·`Frost1`·`Shutter1` 은
DMX 채널 목록에서 **읽은** 이름, `Prism1` 은 **쏴서 `Failed` 를 받은** 이름이다.
「콘솔이 받는 이름」이 아니라 「콘솔에 쏘는/쏜 이름」이다.

## 4. 🔴 파생시키지 않은 이유 — SPEC 보다 폭발 반경이 크다

SPEC §A.4-2b 는 「열면 bm 임포트가 통째로 0건」이라 적었다. 코드를 읽으니 더 크다:

    tools.py:5001  for placement in result.planned:     <- 종류를 안 가린다
    tools.py:5018  if untranslatable:
    tools.py:5023  "…값을 명령으로 옮길 수 없는 것이 있어 **한 줄도** 보내지 않았다"
    tools.py:5029  return                                <- bundles 를 버린다

`LXSEQ_PRESET_APPLY_ATTRIBUTE`(`:1692`)에 bm 이 없고, `planned` 는 보류를 뺀 저장
가능분만 담는다(`preset_mapper.py:357`). 그러므로 **bm 한 행이 열리면 같은 계획의
dim·col 배정까지 전부 안 나간다** — 「bm 이 0건」이 아니라 프리셋 임포트 전체가 0건이다.

「값이 수용되면 보류를 자동으로 푼다」로 만들면 t149 가 오는 날 bm 행이 저절로 열리고
그날 임포트가 죽는다. **파생은 지뢰를 심는 것**이라 안 했다.

대신 **트립와이어**: 값이 수용 목록에 들어갔는데 키가 아직 보류에 있으면 보류 사유
문면이 거짓이 되고, 그 자리에서 검사가 빨개지며 실패 메시지가 적용 경로를 지목한다.
**미래의 조용한 실패를 현재의 시끄러운 실패로 바꾼 것**이다.

(SPEC 문면 정정은 리드가 **t154** 로 세웠다 — 이 카드 범위 밖이라 안 건드렸다.)

## 5. 검증

### 5.1 전체 스위트 — 구현 직전/직후를 둘 다 쟀다

    직전 (HEAD~1 파일 상태)  10483 passed, 12 skipped, 1 warning   exit 0
    직후 (커밋된 HEAD)       10489 passed, 12 skipped, 1 warning   exit 0

**정확히 +6**(추가한 검사 수와 일치) · 스킵 불변 · 실패 0. 「회귀 없음」을 추론이
아니라 **측정**으로 적는다. `suite-before.txt` · `suite-after.txt`(트리 로컬).

### 5.2 동작 변경 0의 기계적 증거

    _PROBE_REJECTED == ("Focus", "Frost", "Prism", "Shutter")   -> 참

dict 가 삽입 순서를 지키므로 파생 튜플이 이전 손-작성 튜플과 **바이트 동일**하다.
검사가 그 동일성을 단언하므로 다음 사람이 검산할 수 있다.

### 5.3 뮤테이션 — 3/3 KILLED, **트립와이어 자체를 포함**

| # | 뒤집은 것 | 결과 |
|---|---|---|
| M1 | `_ACCEPTED_ATTRIBUTES` 에 `Frost1` 추가 (= t149 가 오는 날) | **KILLED** — `test_no_hold_reason_is_stale_today` 가 `Frost` 를 지목 |
| M2 | 매핑 값을 시트 토큰보다 짧게(`Frost1` -> `Fro`) | **KILLED** — 3개 검사 |
| M3 | `_stale_holds` 술어를 항상 빈 튜플로 (검사를 공허하게) | **KILLED** — 비공허성 검사 |

M1 의 실패 메시지 원문:

    콘솔 어휘가 넓어져 이 토큰들의 보류 사유가 거짓이 됐다: Frost — 목록에서 빼기
    전에 **적용 경로부터 열어라**. bm 에 적용 줄이 없는 채로 열면 프리셋 임포트가
    통째로 0건이 된다 (server/orchestrator/tools.py 의 apply_untranslatable fail-closed).

M3 이 중요하다: 그것 없이는 **「오늘 조용하다」와 「검사가 공허하다」가 구별되지 않는다.**
복원은 전부 체크섬 대조(`git status` 빈 출력 + 두 파일 해시 일치).

### 5.4 lint

    ruff check server/                   -> All checks passed!   exit 0
    ruff format --check (편집 2파일)      -> 2 files already formatted

작성 중 `SIM300` 하나가 걸려 `--fix` 로 고쳤고, 고친 뒤 재검사했다.

## 6. 덤 — 기존 검사가 조용히 약해질 뻔했다

`test_the_parser_comment_does_not_claim_the_syntax_is_invalid` 는
`source.split("_PROBE_REJECTED = (")[0]` 로 주석 블록을 잘라 한정 문구를 찾는다.
선언이 `= tuple(...)` 이 되면 그 앵커가 **아무것도 못 자르고 파일 전체**를 훑는다 —
검사가 「주석 블록에 있다」가 아니라 「파일 어딘가에 있다」를 재게 된다. 통과는 계속
하므로 **아무도 못 본다.**

앵커를 옮기고, 앵커 자체가 없으면 실패하도록 단언을 붙였다.

그리고 그 검사가 고정하던 한정 문구 둘(「전수 확정으로도」·「관측되지 않았다」)을
초안에서 지웠다가 검사에 잡혀 되살렸다 — **그 한정은 아직 참이다**(`Prism1` 의
`Failed` 차이 원인은 여전히 미관측).

## 7. 안 잰 것

1. **적용 경로를 여는 방법** — 이 카드가 안 한다. §4 는 그 축이 존재한다는 것을 잰
   것이지 여는 방법이 아니다.
2. **`_OUT_OF_SCOPE` 쪽 매핑** — 안 만들었다. 풀 계열 이름은 어트리뷰트가 아니라
   **풀 이름**이라 콘솔 쪽 대응의 종류가 다르다. 같은 표에 넣으면 t135 가 반증한
   그 형태(두 종류를 한 목록에)의 재발이다.
3. **다른 RIG 팩의 시트 어휘** — 이 리그 시트만 셌다(census §5-1).
4. **`_ACCEPTED_ATTRIBUTES` 쪽 비대칭** — `Zoom` 은 시트에도 콘솔에도 `Zoom` 이라
   지금은 안 갈린다. 콘솔에 `Zoom1` 류가 있는지 안 쟀다.
5. **`server/looks/schema.py`** — 안 건드렸다. PRESERVE 게이트 둘이 잠금, t149.
   이 카드 설계는 그 파일을 요구하지 않았다(파생이 읽는 상수는 이미 import 돼 있다).

## 8. 잔여 위험

- 트립와이어는 **테스트 시점**에만 운다. 누가 테스트를 안 돌리고 머지하면 안 잡힌다.
  CI 가 스위트를 돌리므로 PR 경로에서는 잡히지만, 로컬 직접 푸시는 그 밖이다.
- 매핑 값 넷 중 `Shutter1` 은 **값을 쏜 적이 없다**. 채널명이 존재한다는 것까지만
  실측이고 그 이름으로 콘솔이 값을 받는지는 미측정이다 — 주석에 그대로 적었다.
- 이 보고서의 스위트 수치는 이 트리·이 커밋 기준이며 CI 초록이 아니다.
