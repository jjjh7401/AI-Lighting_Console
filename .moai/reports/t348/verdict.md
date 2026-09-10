# t348 — 리그가 못 조정하는 축을 쓰려는 룩은 저장 전에 보류한다

- 워크트리: `.claude/worktrees/t348` (`git worktree add -b WT-absent-axis-hold`, `EnterWorktree` 미사용)
- 브랜치: `WT-absent-axis-hold` · 베이스 `origin/main` = `bfaa560`
- 커밋: `63a8598` (코드) + 이 파일의 커밋
- 🔴 **PR 없음 — 아래 「Blocker」 참조.** 푸시가 저장소의 PRESERVE 게이트에 막혔다.

## Claim

1. `server/looks/instantiate.py` `_plan_stores` 의 기존 보류 사다리에 rung 하나를
   더했다. 새 사유 상수 `AXIS_ABSENT = "axis_absent"` 는 `:65-68` 의 네 사유 옆에 있고,
   보류는 기존 `SkippedStore(family, reason, pool, slot, detail)` 로 나온다. 두 번째
   메커니즘은 만들지 않았다.
2. 판정 단위는 **속성**, 보류 단위는 **저장 하나(=family)**. `detail` 이 보류를 부른
   속성 이름을 싣는다.
3. 판독기는 **선택 인자** `axes=` 이고 기본은 없음. `Look` 은 리그 결속을 얻지 않았다.
4. 미판독은 부재가 아니다: 판독기 미제공 → 오늘과 동일, 판독기가 `unread` → 저장 진행,
   어댑터는 빈 판독 · 미판독 fid · 부분 판독 중 하나라도 있으면 부재를 단정하지 않는다.
5. 숫자 비교 0. `range_verdict` 호출 0. `AxisRange` 정렬 0. 콘솔 쓰기 0. 새 명령줄 0.

### 판정 단위: per-attribute (왜)

`ATTRIBUTE_POOL_FAMILY` 는 다-대-일이다 — `Color` family 는 `ColorRGB_R/G/B` 셋,
`Focus` 는 `Zoom`, `Beam` 은 `Iris` 를 나른다. family 단위로만 물으면 「이 리그에
`Zoom` 이 있는가」와 「`Focus` 계열 무언가가 있는가」가 한 질문으로 뭉쳐, 다른 축이
있다는 이유로 없는 축이 통과한다. 그래서 payload 의 속성을 하나씩 묻고(per-attribute),
그 중 하나라도 부재면 그 family 의 저장 하나를 보류하며 `detail` 에 그 속성 이름을 싣는다.

### rung 위치

pool 검사보다 **앞**. 장비가 그 축을 아예 못 움직인다는 것은 슬롯이 비었는지와 무관한
더 강한 사실이고, 뒤에 두면 같은 보류가 `no_free_slot` 으로 보고되어 고칠 곳(장비 vs
슬롯)을 잘못 가리킨다. `axes` 가 없으면 rung 자체가 통과하므로 **기존 순서 의미는
그대로**다 — `test_the_default_and_a_present_everything_lookup_agree_exactly` 가
`to_dict()` 동일까지 잰다.

### 철자 게이트

`FixtureCapability.has_attribute` 는 정확(대소문자 무관) 일치다. 룩 스키마 이름이 콘솔
철자와 다르면 **거짓 부재**가 나고, 거짓 부재는 되던 저장을 막는다. 그래서 어댑터는
이 저장소에서 콘솔 철자로 실측된 이름만 판정한다: `MEASURED_ATTRIBUTE_SPELLINGS =
("Dimmer", "Zoom")`. `Iris` · `ColorRGB_*` 는 철자 미측정이라 `unread` 로 답한다. 확장은
파라미터(`judged=`)이며 실측이 선행한다.

## Evidence

### 새 시험

```
$ uv run pytest server/tests/test_looks_axis_hold.py -q
........................                                                 [100%]
24 passed in 1.13s
```

### 회귀 (지정된 것 + 이 파일을 덮는 것들을 찾아 추가)

```
$ uv run pytest server/tests/test_capability_verdict.py server/tests/test_capability_join.py \
    server/tests/test_capability_read.py server/tests/test_looks_schema.py \
    server/tests/test_looks_instantiate.py server/tests/test_fx_instantiate.py \
    server/tests/test_looks_tool.py server/tests/test_songcue_rig_aware_look.py \
    server/tests/test_pool_lookup.py -q
531 passed in 4.59s
```

`instantiate.py` 를 덮는 기존 시험을 찾은 방법: `ls server/tests/ | grep -Ei 'look|instant|capab'`
→ `test_looks_instantiate.py`(_plan_stores 직접 소비) · `test_fx_instantiate.py` ·
`test_looks_tool.py` · `test_songcue_rig_aware_look.py` · `test_pool_lookup.py`.

### 전체 스위트

```
$ uv run pytest -q
12170 passed, 35 skipped, 1 warning in 195.65s (0:03:15)
[exited with code 0]
```

### make ci-local

```
$ make ci-local
CI_LOCAL_EXIT=0
```

(첫 실행은 `ruff format --check` 로 exit 2 였다: `Would reformat: server/looks/instantiate.py`,
`server/tests/test_looks_axis_hold.py`. `uv run ruff format` 후 0.)

### 뮤테이션 — 5회, 5/5 사망 (생존 0)

| # | 뮤테이션 | 결과 |
|---|---|---|
| M1 | 어댑터의 `has_attribute` 술어 반전 | **FAIL** 9 failed / 116 passed |
| M2 | 판독기 없을 때 기본이 보류 (`return values[0].name`) | **FAIL** 55 failed / 70 passed |
| M3 | unread 를 부재로 (`!= PRESENCE_PRESENT`) | **FAIL** 2 failed / 123 passed |
| M4 | 어댑터의 부분판독 가드 제거 | **FAIL** 1 failed / 124 passed |
| M5 | `detail` 에서 속성 이름 제거 | **FAIL** 4 failed / 121 passed |

각 회차 후 `diff -q` 로 원본 복원 확인(`restored-clean`).

## Baseline-attribution

- 트리: `/Users/studiox/Documents/Claude/Code/AI-Lighting_Console/.claude/worktrees/t348`
- 베이스: `origin/main` = `bfaa560316e6c14358e8f80b43060d91196b9042`
- 위 모든 명령은 이 트리에서, 이 회차에 실행하고 출력을 관측했다.

## Blocker — PRESERVE 게이트가 푸시를 막는다

```
$ git push -u origin WT-absent-axis-hold
FAILED server/tests/test_overlap_preserve.py::TestPreserveDiffIsEmpty::test_the_preserved_paths_are_unchanged
E       AssertionError: assert ' server/look...eletions(-)\n' == ''
[pre-push] FAILED: local CI mirror reported errors.
error: failed to push some refs
```

`server/looks/instantiate.py` 는 `_PRESERVE_PATHS`(10개) 중 하나다. 대조 측정:

```
$ git diff --stat 95687a0e..HEAD -- <_PRESERVE_PATHS 파일 7개>
 server/looks/instantiate.py | 83 +++...      ← 내 변경
$ git diff --stat 95687a0e..origin/main -- <같은 7개>
                                              ← 비어 있음 (main 에서 게이트는 초록)
```

즉 이 실패는 기존 결함이 아니라 **내 변경이 만든 것**이고, 카드가 지정한 편집 지점이
바로 잠긴 파일이다. 선언 출처는 `.moai/specs/SPEC-COPILOT-PRECHK-001/plan.md:89`
(「`server/looks/{schema,loader,roles,resolver,instantiate,matching}.py` … 변경 0건」).

게이트 모듈 독스트링이 처방을 명시한다: 게이트에 예외를 다는 것은 **마지막 수단**이고,
먼저 가는 곳은 선언 층(그 SPEC 문서)이며 — 그리고

> ⚠️ 그때는 그 SPEC 이 **살아 있었다.** 닫힌 SPEC 의 선언을 사후에 고치는 경우는 이
> 선례가 덮지 않는다 — 그 판단은 이 게이트 밖이다.

그래서 내가 하지 않은 것: 게이트에 예외 추가, `_PRESERVE_PATHS` 수정, 닫힌 SPEC 문서
사후 수정, `SKIP_MOAI_PREPUSH=1` 우회. 넷 다 승인 없이 안전장치를 여는 일이다.
**결정 필요:** 이 rung 을 위해 `server/looks/instantiate.py` 의 PRESERVE 를 어떤 경로로
해제할지.

## Gaps — 재지 않은 것

- **PR · 원격 CI 미측정.** 푸시가 막혀 PR 을 만들지 못했다. `gh pr checks` 출력 없음.
  원격 CI 가 로컬과 같은 판정을 낼지 모른다.
- **콘솔 실측 0.** 이 회차에 콘솔을 부르지 않았다. `RigAxisPresence` 는 in-memory
  `RigCapabilities` 로만 시험했다. 실제 리그에서 `read_rig_capabilities` 가 채운 값으로
  이 어댑터가 어떤 답을 내는지는 **관측하지 않았다**.
- **`Iris` · `ColorRGB_*` 의 콘솔 철자 미측정.** 그래서 판정 대상이 아니다. 실기에서
  이 축들은 영원히 `unread` 이고, 부재여도 보류되지 않는다. 이 카드는 그 철자를 재지
  않았다.
- **`Dimmer` · `Zoom` 철자도 이 회차에 직접 재지 않았다.** 근거는 기존 시험
  (`test_capability_read.py` 등)에 나타나는 철자 빈도(`Zoom` 21회, `Dimmer` 5회, `Pan`
  10, `Tilt` 8, `Prism` 2)뿐이다 — 실기 판독 원본을 다시 열지는 않았다.
- **`_plan_stores` 의 새 소비자 배선 0.** `server/web/session.py` 등 실제 호출자에
  `axes=` 를 넘기는 배선은 이 카드가 하지 않았다(범위 밖). 즉 이 rung 은 오늘 프로덕션
  경로에서 **발사되지 않는다** — t344 A 가 지적받은 「읽는데 아무도 안 부르는」 모양과
  같은 종류의 잔여물이다.
- 성능 · 왕복 수 영향 미측정.

## Residual-risk

- **거짓 부재가 되던 저장을 멈추는 위험.** 철자 게이트로 좁혔지만, 콘솔이 `Zoom` 을
  다른 철자로 답하는 모드가 있으면 그 리그의 Focus 저장이 전부 보류된다. 완화: 보류는
  파괴가 아니라 미실행이고, `detail` 이 이유를 이름 대어 말한다.
- **과잉 보류.** `Color` family 는 세 속성 중 하나만 부재여도 저장 전체가 보류된다.
  의도한 선택이지만(부분만 담은 색 프리셋을 만들지 않는다), 감독이 「일부라도 저장」을
  원하면 정책 변경이 필요하다. 오늘은 `ColorRGB_*` 가 판정 대상이 아니라 발현되지 않는다.
- **rung 순서 변경의 파급.** 축 부재가 `no_free_slot`·`conflict` 를 가린다. `axes` 없이
  부르는 기존 호출자에는 영향 0(시험으로 고정), 새 호출자에는 보이는 변화다.
- **부분 판독 시 fail-open.** 판독이 조금이라도 불완전하면 보류하지 않으므로, 리그가
  못 하는 일을 그대로 저장할 수 있다. 반대 방향(조용히 막힘)보다 낫다고 판단했다.
