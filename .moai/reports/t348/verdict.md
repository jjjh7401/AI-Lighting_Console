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

---

# 2회차 — 경로 A 집행 (감독 승인 2026-09-11)

## 승인의 유래를 먼저 적는다

1회차에서 나는 네 경로를 **거부했다**: 게이트에 예외 추가 · `_PRESERVE_PATHS` 직접
수정 · 닫힌 SPEC 문서 사후 수정 · `SKIP_MOAI_PREPUSH=1` 우회. 넷 다 승인 없이 안전장치를
여는 일이었다. 그 거부가 이 결정이 존재하는 이유다 — 우회했다면 감독은 잠금이 있었다는
사실조차 몰랐을 것이고, 저장소는 아무도 승인하지 않은 동결 해제를 갖게 됐을 것이다.

## Claim (2회차)

1. **선언 층을 좁혔다.** `plan.md` §A.5 첫 행에서 `instantiate` 를 뺐다(여섯 → 다섯).
   행을 지우지 않았고 나머지 여섯 행은 손대지 않았다. 개정 절에 사유·승인·「범위 선언 ≠
   경계」 구별(게이트 독스트링을 인용)을 적었다.
2. **승인 기록을 남겼다.** `progress.md` §F.2 — SONGCUE §F 개정 절의 모양을 따랐다.
   이 저장소 **최초의 닫힌 SPEC PRESERVE 선언 사후 좁힘**임을 명시했고, 게이트가 판단을
   자기 밖에 두었다는 것(「그 판단은 이 게이트 밖이다」)과 감독이 그것을 메웠다는 것을
   적었다. `status` · AC 17건 · REQ 20건 · Out of Scope · 역사적 기록은 **하나도** 건드리지
   않았다.
3. **게이트를 따라갔다 — 5곳.** 아래 표. 남은 아홉에 대해 게이트는 살아 있다(실측).
4. 🔴 **푸시하지 않았다. PR 없다.** 같은 파일을 잠그는 **두 번째 선언**이 있고 이 승인이
   덮지 않는다.

## 게이트 따라가기 — 5곳 (배차서가 셋을 지목했고, 내가 다섯을 찾았다)

| # | 자리 | 조치 | 배차서가 지목? |
|---|---|---|---|
| 1 | `_PRESERVE_PATHS` 튜플 | `"server/looks/instantiate.py"` 제거 (10 → 9) | 예 |
| 2 | `test_the_list_has_ten_entries` | `== 10` → `== 9`, 이름도 `nine`, `files == 7` → `6` | 예(`files` 는 미지목) |
| 3 | 모듈 독스트링 인용 | 「여섯」 → 「다섯」, `plan.md:89` 줄번호 인용 삭제, 「아홉인 이유」 절 신설(t348·승인·두 번째 선언 고지) | 예 |
| 4 | `TestPreserveScopeCitations._DECLARATIONS` | `instantiate.py` 항목 제거 — `_PRESERVE_PATHS` 와 **집합 동일성** 단언이 있어서 필수 | **아니오** |
| 5 | `TestPredecessorSpecDocuments` | `plan.md` 를 granted 문서로 추가(선례와 같은 모양: 행 키 + sha256, **삭제 1행**만) + 비공허성 3건 | **아니오** |

## Evidence (2회차)

```
$ uv run pytest server/tests/test_overlap_preserve.py -q
65 passed in 0.99s
$ uv run ruff check server/tests/test_overlap_preserve.py
All checks passed!
$ make ci-local
CI_LOCAL_EXIT=0
$ uv run pytest -q
FAILED server/tests/test_songcue_bundle.py::test_preserve_look_files_are_unchanged_from_run_phase_base
1 failed, 12173 passed, 35 skipped, 1 warning in 161.87s (0:02:41)
```

### 뮤테이션 3회 추가 — 3/3 사망 (누적 8/8)

| # | 뮤테이션 | 결과 |
|---|---|---|
| M6 | 남은 아홉 중 하나(`server/looks/roles.py`)를 건드림 | **FAIL** `test_the_preserved_paths_are_unchanged` — 게이트는 여전히 살아 있다 |
| M7 | granted `plan.md` 에서 두 번째 행을 삭제 | **FAIL** `test_the_granted_plan_deleted_exactly_the_one_granted_row` + 선언 검사 2건 |
| M8 | 승인 기록에서 두 번째 잠금 고지(`REQ-SONGCUE-021`) 제거 | **FAIL** `test_the_amendment_records_its_approval_in_both_documents` |

각 회차는 throwaway 커밋 후 `git reset --hard 11ad3fe` 로 복원했고 `git status` 로 확인했다.

## Baseline-attribution (2회차)

- 트리 `.claude/worktrees/t348` · 브랜치 `WT-absent-axis-hold` · 베이스 `origin/main` = `bfaa560`
- 커밋: `63a8598`(코드) · `797ed1c`(1회차 판정문) · `a03c2c0`(선언 층) · `11ad3fe`(게이트 짝)
- 위 모든 명령을 이 트리에서 이 회차에 실행하고 출력을 관측했다.

## 🔴 남은 블로커 — 같은 파일을 잠그는 두 번째 선언

```
$ uv run pytest server/tests/test_songcue_bundle.py -q
FAILED server/tests/test_songcue_bundle.py::test_preserve_look_files_are_unchanged_from_run_phase_base
```

`_PRESERVE_LOOK_FILES`(여섯 파일)에 `server/looks/instantiate.py` 가 있다. 출처는
`SPEC-COPILOT-SONGCUE-001/spec.md:182` `REQ-SONGCUE-021` — **또 다른 종료된 SPEC**. 대조
측정: 이 게이트도 `origin/main` 에서 초록, t348 head 에서 빨강. 낡은 잔여물이 아니라 살아
있는 잠금이다.

배차서의 [HARD] 는 「두 번째 잠긴 파일이 필요하면 아무것도 더 열지 말고 멈추고 보고하라 —
이 승인은 `instantiate.py` 하나만 덮는다」였다. 그래서 나는 `test_songcue_bundle.py` 와
SONGCUE `spec.md` 를 **건드리지 않았다.** 이번 승인이 좁힌 것은 PRECHK 의 선언 하나이고,
SONGCUE 의 `REQ` 를 좁히는 것은 plan-phase 표 한 행을 좁히는 것보다 무게가 다르다(요구
자체다). **별도 승인 사안이다.**

### ⚠️ 푸시가 통과할 수 있다 — 그것이 초록의 증거가 아니다 (실측)

`make ci-local` 은 exit 0 인데 전체 스위트는 빨갛다. 이유를 재서 확인했다:
`Makefile:63 FAST_TESTS` 는 12개 파일이고 `test_overlap_preserve.py` 는 **있지만**
`test_songcue_bundle.py` 는 **없다**. pre-push 훅은 `test-fast` 를 돌린다. 즉 **지금
푸시하면 통과할 것이고, 전체 스위트가 빨간 브랜치가 원격에 올라간다.** 그래서 우회가
아니라 통과 가능성 자체를 이유로 푸시하지 않았다 — 훅이 침묵하는 것은 부재의 증거가
아니다.

## `axes=` 프로덕션 배선 — 못 했다, 막는 것을 정확히 적는다

1회차 Gap 을 닫으라는 지시였다. 재서 답한다.

프로덕션 호출자는 **하나뿐**이다(`grep -rn --include='*.py' -e instantiate_look -e
build_instantiation`): `server/orchestrator/tools.py:2650` 의 `instantiate_look` 툴 핸들러
(`build_instantiation(look, resolution=…, pools=…, shape=…)`). `server/looks/busking.py:304`
도 `build_instantiation` 을 부르지만 그쪽은 별개 소비자(P1-2 버스킹)다.

배선이 막히는 이유는 **두 겹**이다.

1. **자료가 없다.** `tools.py:2620-2650` 을 읽었다. 핸들러는 `LOOK_RIG_SECTIONS`(groups ·
   preset_pools)만 읽고 `state_port` 를 갖는다. `RigAxisPresence` 는
   `RigCapabilities` 를 요구하고, 그것을 만들려면 `read_rig_capabilities(reader,
   properties, root=…, fixtures=[FixtureTypeRef(fid, type_raw, mode_raw)…])` 가 필요하다 —
   즉 **fid별 FixtureType·Mode 프로퍼티 판독 + `BulkPropertyReader` + 타입 이름 표**가
   새로 들어와야 한다. 프리셋 저장 핸들러 안에 **새 콘솔 판독 경로와 왕복**을 만드는
   일이고, 「사다리에 rung 하나」와 크기가 다르다.
2. **`tools.py` 가 그 자체로 잠긴 파일이다.** `test_songcue_bundle.py` 의 `_TOOLS_PATH`
   hunk 트립와이어가 SONGCUE 베이스 이후의 **모든 hunk 스냅샷**을 들고 있다(그 주석은
   「상수가 아니라 트립와이어이며, 정당하게 고치는 SPEC 은 의도적으로 갱신해야 한다」고
   적어 갱신을 허용한다). 그러나 그 트립와이어는 내가 건드리지 않기로 한 그 파일 안에
   있다. PRECHK §A.5 의 `tools.py` 금지 두 구간(`:247-250` · `:496-597`)은 `:2650` 을
   덮지 않으므로 **그쪽이 막는 것은 아니다** — 막는 것은 SONGCUE 쪽 트립와이어다.

**그래서 배선은 별도 카드다.** 그 카드의 내용은 「선택 인자를 넘긴다」가 아니라 「저장
핸들러에 능력 판독을 도입한다」이고, 왕복 예산·실패 모양(판독 실패 시 `unread` 로 열려야
한다)·`tools.py` 트립와이어 갱신을 함께 설계해야 한다. 지금 급히 끼우면 1회차가 지적받은
「부품은 초록인데 경로가 안 이어졌다」의 반대 실수 — **재지 않은 경로를 이어붙이는 것** —
이 된다.

즉 이 Gap 은 **닫지 못했고, 이유를 재서 좁혔다**: 막는 파일은 `server/orchestrator/tools.py`
하나이며, 그것을 막는 것은 PRECHK 의 선언이 아니라 SONGCUE 의 hunk 트립와이어다.

## 배차서 전제 중 내 측정이 반증한 것

1. **「`TestPreserveScopeCitations` 가 트립와이어니 먼저 빨개지게 두고 읽어라」 — 안
   빨개졌다.** `plan.md` 에서 `instantiate` 를 뺀 직후 그 클래스는 **초록**이었다(실측:
   `61 passed`, 해당 검사 실패 0). 원리적이다 — t177 이 좌표를 「구역 + 내용 동거」로
   바꿨고, 이 검사는 경로 조각 `server/looks/` 와 방침 문구가 같은 줄에 있는지만 본다.
   중괄호 묶음의 **멤버 하나가 빠지는 것**은 둘 다 그대로 남긴다. 실제로 잡은 것은
   `_PRESERVE_PATHS` ↔ `_DECLARATIONS` **집합 동일성** 단언이다. 이 한계를 게이트
   독스트링에 실측으로 적었다.
2. **「`plan.md:89` 의 줄번호가 밀릴 수 있다」 — 검사는 줄번호를 인용하지 않는다.**
   `TestPreserveScopeCitations` 는 내용 앵커(`### §A.5 PRESERVE 재확인`)를 쓴다(t177 이
   줄번호를 버렸다). 줄번호를 든 곳은 **모듈 독스트링 산문** 하나뿐이었고, 그마저 편집 후
   89행은 그대로였다(치환이라 행 수 불변). 산문의 줄번호 인용은 그래도 삭제했다 — 검사가
   버린 좌표를 산문이 계속 들고 있으면 다음 독자가 잘못된 규율을 배운다.
3. **「지목한 셋」이 전부가 아니었다.** 다섯이었다(위 표 #4 · #5).
4. **「선언 층을 고치면 푸시할 수 있다」(경로 A 의 암묵 전제) — 아니다.** 같은 파일을
   잠그는 선언이 둘이고, 게다가 pre-push 는 두 번째 게이트를 **돌지 않는다**(위 ⚠️).

## Gaps (2회차) — 재지 않은 것

- **PR · 원격 CI 여전히 미측정.** 푸시하지 않았으므로 `gh pr checks` 출력이 없다. 인용할
  head 도 없다.
- **SONGCUE 선언을 좁히면 무엇이 깨지는지 재지 않았다.** `_PRESERVE_LOOK_FILES` 를
  건드리지 않았으므로 그 게이트의 짝(비공허성 검사, 인용 트립와이어)이 어디에 있는지
  전수 세지 않았다.
- **`tools.py` hunk 트립와이어 갱신 비용 미측정.** 갱신이 몇 줄인지, 다른 검사가 그것에
  걸리는지 재지 않았다.
- 1회차 Gaps 는 그대로 유효하다 — 콘솔 실측 0, `Iris`·`ColorRGB_*` 철자 미측정,
  `Dimmer`·`Zoom` 철자도 이 회차에 직접 재지 않음.
- **내 git 사고 1건.** 비공허성 프로브 중 `git stash --keep-index` 를 써서 미커밋 작업이
  stash 로 빠지고 이어진 `git reset --hard HEAD~1` 이 커밋 `797ed1c` 를 떨어뜨렸다.
  reflog + `git stash pop` 으로 전량 복구했고(`git status` 로 확인) 이후 프로브는 커밋 후
  고정 SHA 로 되돌리는 방식으로 바꿨다. **잃은 것은 없지만 잃을 수 있었다** — 프로브는
  깨끗한 트리에서만 돌려야 한다.

## Residual-risk (2회차)

- **선례가 넓게 읽힐 위험.** §F.2 는 「닫힌 SPEC 선언도 감독 승인이면 좁힐 수 있다」로
  읽힐 수 있다. 완화: 그 절에 무엇이 승인되지 **않았는지**를 표로 적고, 잠금 전수 세기를
  다음 카드에 지시했다. 그래도 사후 좁힘의 첫 사례가 열렸다는 사실 자체는 남는다.
- **다이제스트 핀의 취약성.** `plan.md` 의 삭제 1행을 sha256 으로 못박았으므로, 이 문서를
  정당하게 고치는 다음 카드는 게이트에서 빨간불을 본다. 의도한 설계(재검토 강제)지만
  마찰이다.
- **아홉으로 줄어든 게이트.** 커버리지가 한 파일만큼 줄었고, 그 파일은 이제
  SONGCUE 게이트 하나에만 잠긴다. 그 선언이 나중에 좁혀지면 `instantiate.py` 는 잠금이
  0 이 된다 — 그때는 이 파일의 변경을 잡아줄 게이트가 없다.
