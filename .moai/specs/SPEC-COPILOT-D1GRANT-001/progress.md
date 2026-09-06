# SPEC-COPILOT-D1GRANT-001 — 진행 기록

> 카드 t282 후속 · Tier M · 기준 트리 `main` `a1e75e5` (2026-09-06)

## §E.1 Plan-phase Audit-Ready Signal

- 산출물: `spec.md` · `plan.md` · `acceptance.md` · `progress.md` (Tier M 4종)
- REQ: 21건 (REQ-D1GRANT-001..021), 전부 GEARS 마커 표기
- AC: 14건 (AC-D1GRANT-001..014), 전부 Given/When/Then
- 범위 제외: `### Out of Scope` H3 4개 (선택 로직 · 다른 장르/칸 · 게이트 구조 · 실기 발사와 색 보정)
- 미해결 clarification 마커: 없음
- 콘솔 예산: 읽기 전용, 쓰기 0

### plan 단계에서 실제로 잰 것 (이 트리, 이 회차)

| 잰 것 | 명령 | 관측 |
|---|---|---|
| D1 인구조사 | 워크트리 루트에서 `uv run python` 으로 `looks_for_genre` 순회 (프로브 스크립트는 실행 후 삭제) | `edm [('edm-ambient-hold', ('배경',))]` · `rock [('rock-empty-stage', ('배경',))]` · ballad·worship 은 각 2건 |
| 실기 18그룹 역할 결속 | 같은 회차 `resolve_roles` | `mapped: ['백라이트','사이드','스페셜','프론트']` · `unmapped: {'탑':'no_match','배경':'no_match'}` |
| 정렬 축 | `server/looks/busking.py:81-97` 판독 + `sorted()` 확인 | `looks_for_genre` = `sorted(key=(dynamics, look_id))`. `['edm-ambient-hold','edm-haze-shafts']` · `['rock-empty-stage','rock-wing-embers']` |
| 착수 초록 | `.venv/bin/python -m pytest server/tests/test_overlap_preserve.py server/tests/test_songcue_rig_aware_look.py -q -p no:cacheprovider` | `130 passed in 2.15s` |
| 인터프리터 귀속 | `server/tests` 하위에서 `../../.venv/bin/python -c "import server; print(server.__file__)"` | 이 워크트리의 `server/__init__.py` — 남의 트리 `.pth` 가 이기지 않았다 |
| 룩 디렉터리 승인 diff | `git diff --numstat 95687a0e..HEAD -- server/looks/library/` | `ballad 2/2` · `edm 1/1` · `worship 2/2` (rock 없음) |
| `edm.yaml` 훅 위치 | `git diff --unified=0 95687a0e..HEAD -- server/looks/library/edm.yaml \| grep '^@@'` | `@@ -74 +74 @@` — 훅 하나 |
| 기준 커밋 파일 길이 | `git show 95687a0e:server/looks/library/{edm,rock}.yaml \| wc -l` | `156` · `141` |
| 개수 의존 소비자 (부분) | `grep -rn 'len(looks_for_genre\|== 9' server/tests/` 외 | `test_busking_genre.py:30,45` · `test_looks_matching.py:676` · `edm.yaml:7` · `busking.py:13` · `test_looks_library.py:50` (`MAX_LOOKS_PER_GENRE = 10`) · `preshow/checks.py:111` (동적, 핀 아님) |
| SPEC ID 형식 | `[[ "SPEC-COPILOT-D1GRANT-001" =~ ^SPEC(-[A-Z][A-Z0-9]*)+-[0-9]{3}$ ]]` | `PASS` |

### plan 단계에서 **안** 잰 것

- 두 룩을 실제로 넣은 상태의 게이트 판정 — 이 SPEC 은 라이브러리를 한 바이트도 안 바꿨다(plan 단계). §1.3 에 인용한 실패 출력은 **PR #344 브랜치의 것**이며, run 단계가 이 트리에서 다시 만든다.
- 개수 의존 자리의 **전수** — 위 표는 부분 스윕이다. 전수는 REQ-020 이 run 단계에 요구한다.
- 실기 콘솔 발사 0건. 색·밝기 값은 이웃 룩에서 역산한 설계값이다.
- 실기 cyc 리그 지문에서의 무회귀 — 대조는 합성 리그 `_CYC_RIG` 로만 계획돼 있다.
- PR #344 의 머지 여부는 시점 의존이라 착수 시 다시 잰다(plan.md B-6).

- plan_status: audit-ready
- plan_complete_at: 2026-09-06

## §E.2 Run-phase Evidence

> 브랜치 `WT-d1-looks-land` (기준 `WT-spec-d1-grant` + `origin/main` 머지 `b6317b5`).
> 커밋 둘: `b656da7`(M1) · `9a93b8a`(M2~M4) + 이 기록 커밋.
> 검증 인터프리터 귀속: `uv run python -c "import sys, server; print(sys.executable); print(server.__file__)"`
> → `…/.claude/worktrees/agent-a0a465a4423810ee4/.venv/bin/python` · `…/agent-a0a465a4423810ee4/server/__init__.py`
> (이 워크트리의 인터프리터가 이 워크트리의 `server` 를 읽는다 — 남의 트리 `.pth` 가 이기지 않았다.)
> plan 이 적은 `.venv/bin/python` 은 이 워크트리에 없었다. `uv run` 이 `.venv` 를 만들고 그 안에서 돈다.

### 착수 기준선 (변경 전)

```
uv run python -m pytest server/tests -q -p no:cacheprovider
11757 passed, 22 skipped, 1 warning in 182.91s (0:03:02)
```

### M1 — 두 룩을 넣고, 게이트가 거절하는 것을 이 트리에서 다시 만들었다

`test_looks_library.py` 전량 초록(`29 passed in 0.37s`) 뒤 커밋 `b656da7`. 그 상태의 게이트 판정 —
plan.md B-7 이 요구한 「남의 트리 출력을 쓰지 않는다」의 이행:

```
uv run python -m pytest server/tests/test_overlap_preserve.py -q -p no:cacheprovider
E         Extra items in the left set:
E         'server/looks/library/rock.yaml'
...
FAILED server/tests/test_overlap_preserve.py::TestLooksLibraryGrantedExtension::test_exactly_the_three_granted_files_changed
FAILED server/tests/test_overlap_preserve.py::TestLooksLibraryGrantedExtension::test_every_change_is_a_granted_line_pair_and_every_pair_is_present
2 failed, 52 passed in 0.57s
```

### M2 — 승인 등록 후 게이트 초록

```
uv run python -m pytest server/tests/test_overlap_preserve.py -q -p no:cacheprovider
57 passed in 0.69s          (승인 전 54 → 새 단언 셋 추가)
```

### AC-D1GRANT-008 — 심은 변경 셋, 각각의 실패 출력 (전부 되돌림)

세 건 모두 **커밋해서** 쟀다(게이트는 `..HEAD` 를 읽으므로 워킹트리 편집은 안 보인다).
되돌림은 `git reset --soft HEAD~1` + `git restore --staged --worktree <파일>` 이며,
이력에 심은 커밋은 남아 있지 않다(`git log --oneline -3` 에 `PLANT` 없음).

**① 승인 밖 세 번째 파일 (`ballad.yaml` 에 한 줄 추가)**

```
E           AssertionError: server/looks/library/ballad.yaml
E           assert ['    aliases...-008 probe 1'] == ['    aliases...t", "night"]']
E             Left contains one more item: '# PLANTED — AC-D1GRANT-008 probe 1'
FAILED ...::test_every_change_is_a_granted_line_and_every_grant_is_present
1 failed, 56 passed in 0.72s
```

**② 승인 파일 안에 룩 하나 더 (`rock.yaml`)**

```
E           AssertionError: server/looks/library/rock.yaml
E           assert ['', '  # ---...2 의 차가운', ...] == ['', '  # ---...2 의 차가운', ...]
E             Left contains 13 more items, first extra item: ''
FAILED ...::test_every_change_is_a_granted_line_and_every_grant_is_present
1 failed, 56 passed in 0.64s
```

**③ 승인 파일에서 줄 하나 삭제 (`edm.yaml` 의 `    dynamics: 1`)**

```
E           AssertionError: server/looks/library/edm.yaml
E           assert 2 == 1
E            +  where 2 = len(['    dynamics: 1', '    mood_keywords: ["깊은", "푸른", "숨고르는", "브레이크다운", "deep", "breakdown"]'])
FAILED ...::test_every_change_is_a_granted_line_and_every_grant_is_present
FAILED ...::test_the_d1_appends_delete_nothing
2 failed, 55 passed in 0.63s
```

되돌린 뒤 `git status --short` 는 비었고, `git diff --numstat 95687a0e..HEAD -- server/looks/library/` 는
`ballad 2/2 · edm 20/1 · rock 20/0 · worship 2/2` 로 심기 전과 같다.

**관측된 한계**: ②를 잡은 것은 줄 텍스트 `==` 단언이지
`test_each_d1_append_carries_exactly_one_look` 가 아니다. 후자는 **상수**를 읽으므로
승인 선언의 폭만 재고, 트리에 실제로 들어온 룩 수는 안 본다. 폭을 지키는 것은 줄
텍스트 정확 일치이며, 그것을 부분집합으로 바꾸면 이 방어가 통째로 사라진다(plan.md B-2).

### 룩 **개수** 소비자 전수 스윕 (REQ-D1GRANT-020)

plan 단계 표는 부분 스윕이었다. 아래는 run 단계가 실행한 것이며, **grep 만으로는 부족했다** —
전량 스위트가 다섯 건을 더 잡았다.

명령:

```
grep -rn 'Nine looks' server/ docs/
grep -rn '9룩\|8룩\|9 룩' server/ docs/
grep -rn '_EXPECTED_COUNTS\|MAX_LOOKS_PER_GENRE\|MIN_LOOKS_PER_GENRE\|report\[.total.\]' server/
grep -rn 'len(library.looks)\|len(looks_for_genre\|len(selection.looks)\|len(bundle.looks)\|len(edm)\|len(rock)' server/
uv run python -m pytest server/tests -q -p no:cacheprovider      # ← 실제 전수 계측기
```

| 자리 | 어떻게 찾았나 | 처리 |
|---|---|---|
| `test_busking_genre.py:30` `_EXPECTED_COUNTS` | grep | edm 9→10, rock 8→9. 갱신 사유를 주석에 남김 |
| `test_busking_genre.py:45` `test_edm_nine_looks_survive` | grep | `test_edm_ten_looks_survive` 로 이름·리터럴 갱신. 비공허 근거 `len(edm) > MAX_TOOL_MATCHES` 유지 |
| `test_looks_matching.py:676` `report["total"]` | grep | 9→10, 같은 함수의 `min(...)`·`MAX_TOOL_MATCHES < ...` 리터럴 동반 갱신 |
| `server/looks/busking.py:13` 산문 | grep | 숫자만 갈지 않고 다시 씀 — 세 수(장르 룩 수 / 상한 8 / 사라지는 건수)를 명시적으로 갈랐다 |
| `server/looks/library/edm.yaml:7` 「Nine looks」 | grep | **안 고침** — 아래 미검증 항목 참조 |
| `test_scene_compile.py:798` `len(REAL_LOOKS) == 32` | **전량 스위트** | 32→34, 헤더 산문 2곳 동반 |
| `test_busking_report.py:41` `_PAIR_COUNTS` | **전량 스위트** | rock·edm 26→27 (새 룩이 역할을 하나씩 선언) |
| `test_busking_report.py:105` rock `사이드` 7 | **전량 스위트** | 7→8 |
| `test_looks_blue_alias.py:84` 푸른/파란 쌍 5건·3룩 | **전량 스위트** | 6건·4룩. 새 룩이 `푸른` 을 쓰므로 불변식대로 `파란` 쌍을 같은 슬롯에 실었다 |
| `test_songcue_unmapped_notice.py:95,108,145` | **전량 스위트** | 이 SPEC 이 관측한 손해를 못박고 있던 자리 — 아래 참조 |
| `server/preshow/checks.py:111` | grep | 개수를 동적으로 세어 보고만 하므로 핀이 아니다(재확인) |
| `test_looks_library.py:388,394` · `test_busking_bundle.py:95,521` · `test_looks_schema.py:226` | grep | 부등식이거나 worship/합성 라이브러리 대상 — 영향 없음(전량 스위트로 확인) |

**전수라는 주장의 근거는 grep 이 아니라 전량 스위트다.** grep 이 5건을 놓쳤고 스위트가 잡았다.

### 뒤집힌 핀 — 관측 손해가 닫혔다

`test_songcue_unmapped_notice.py` 는 이 SPEC 의 §1.1 이 인용한 실기 회차(4건 확정, 3건 저장)를
**회귀로 고정**하고 있었다. 룩이 들어오면서 그 픽스처가 뒤집혔다:

```
E       assert report["summary"]["generated_count"] == 3
E       assert 4 == 3
E       AssertionError: 건너뛴 구간이 있는데 감독용 고지가 비어 있다
E       assert ''
```

교체 방식: `test_live_rig_now_covers_every_section` 이 4/4 를 단언하고 독스트링에 전/후를 남긴다.
고지 기제는 지우지 않고 **안 묶이는 리그**(`_UNBINDABLE_RIG_GROUPS`)로 옮겨 계속 잰다 — 실기
리그의 고지가 이제 빈 문자열이라 그것으로는 「고지가 만들어지는가」를 확인할 수 없다(계측기 공허).

### 최종 검증 (변경 후, 이 트리, 이 회차)

```
uv run python -m pytest server/tests -q -p no:cacheprovider
11776 passed, 12 skipped, 1 warning in 145.07s (0:02:25)
```

```
uv run python -m pytest server/tests/test_songcue_d1_cycless.py -q -rs -p no:cacheprovider
16 passed in 0.22s                                   # 건너뜀 0건
grep -c 'pytest.skip\|_require_proposed\|TestTheSkipIsNotAPermanentPass' server/tests/test_songcue_d1_cycless.py
0
```

```
uv run ruff check server/          → All checks passed!
uv run ruff format --check server/ → 523 files already formatted
npm --prefix ui run test           → Test Files 23 passed (23) · Tests 544 passed (544)
npx --prefix ui tsc --noEmit -p ui/tsconfig.json → exit 0, 출력 없음
```

건너뜀이 22→12 로 준 것은 이 파일의 10건이 사라졌기 때문이다(부재 트립와이어가 목적을 다했다).

### diff 형상 (AC-D1GRANT-005)

```
git diff --numstat 95687a0e..HEAD -- server/looks/library/
2	2	server/looks/library/ballad.yaml
20	1	server/looks/library/edm.yaml
20	0	server/looks/library/rock.yaml
2	2	server/looks/library/worship.yaml

git diff --unified=0 95687a0e..HEAD -- server/looks/library/edm.yaml | grep '^@@'
@@ -74 +74 @@ looks:
@@ -156,0 +157,19 @@ looks:

git diff --unified=0 95687a0e..HEAD -- server/looks/library/rock.yaml | grep '^@@'
@@ -141,0 +142,20 @@ looks:

git show 95687a0e:server/looks/library/edm.yaml | wc -l   → 156
git show 95687a0e:server/looks/library/rock.yaml | wc -l  → 141
```

삽입 훅은 각 파일에 하나씩, `old_count == 0`, `old_start` 가 기준 커밋 줄 수와 일치(156 / 141).
`rock.yaml` 의 삭제는 0. `edm.yaml` 의 삭제는 승인된 「파란」 옛 줄 하나뿐.

### 선언 층·게이트 골격 불변 (AC-006 / AC-009)

```
git diff --stat origin/main..HEAD -- .moai/specs/SPEC-COPILOT-PRECHK-001/
(빈 출력)

git diff origin/main..HEAD -- server/tests/test_overlap_preserve.py | grep -E '^[+-]' \
  | grep -E '_PRESERVE_PATHS|_PRECHK_BASE = |def _preserve_diff_command'
(빈 출력 — 셋 다 안 건드렸다)
```

변경 hunk 넷은 전부 새 상수(`@@ -337,6 +337,69 @@`)와 `TestLooksLibraryGrantedExtension` 안이다.

### 콘솔 예산 (AC-D1GRANT-014)

이 회차에 콘솔로 나간 명령은 **0건**이다. UDP 전송 0, `127.0.0.1:8000` 대상 실행 0.
변경 파일 16개 중 `console/lua/`·`server/safety/` 는 하나도 없고, 검증은 전량 오프라인
pytest·ruff·vitest·tsc 였다. 라이브 포트를 여는 명령을 한 번도 실행하지 않았다.

## §E.3 Run-phase Audit-Ready Signal

- run_status: audit-ready
- run_complete_at: 2026-09-06
- 커밋: `b656da7` (M1) · `9a93b8a` (M2~M4) · 이 기록 커밋
- AC 판정: 13 PASS · **1 PARTIAL** (AC-D1GRANT-013 — 아래)

### AC-D1GRANT-013 이 PARTIAL 인 이유 — 두 수용 기준이 서로 부딪힌다

AC-013 은 `grep -rn 'Nine looks' server/` 가 **0행**일 것을 요구한다. 그 문자열은
`server/looks/library/edm.yaml:7` 헤더 주석에 있다. 그런데 AC-005 는 같은 회차에
`edm.yaml` 의 **삭제 줄이 승인된 「파란」 옛 줄 하나뿐**일 것을 요구하고, 배차 제약은
`server/looks/library/` 를 **추가 전용**으로 못박는다. 7행을 고치면 삭제가 하나 늘어
AC-005 와 그 제약이 동시에 깨진다.

두 기준을 다 만족시키는 방법은 없다. 고르지 않고 **안 고쳤다** — 잘못된 것보다 없는 것이 낫고,
게이트를 넓히는 쪽(헤더 줄을 승인 목록에 더하기)은 이 SPEC 이 §G 에서 스스로 금지한 방향이다.

- 현재 상태: `grep -rn 'Nine looks' server/` → **1행** (`edm.yaml:7`)
- 같은 AC 의 나머지는 전부 PASS: `grep -n '9룩' server/looks/busking.py` → **0행**,
  `_EXPECTED_COUNTS` = `{"worship": 8, "rock": 9, "ballad": 7, "edm": 10}`,
  `report["total"]` = 10, `len(edm) > MAX_TOOL_MATCHES` 유지, 전수 스윕 기록 위에 있음
- 처리 제안: 헤더 산문 정정은 **후속 카드**로 올린다. 승인 목록에 헤더 줄 쌍 하나를
  명시적으로 추가하는 형태여야 하며, 그것은 감독이 따로 읽어야 할 결정이다

### 이 SPEC 이 닫혀도 **미검증**으로 남는 것

1. **실기 콘솔 발사 0건.** 두 룩은 한 번도 발사되지 않았다. 색·밝기는 이웃 룩에서 역산한
   설계값이며(`edm-ambient-hold`·`edm-groove-cyan`·`rock-empty-stage`·`rock-verse-side`),
   숫자가 맞아도 무대에서 눈에 틀릴 수 있다.
2. **실기 cyc 리그 지문에서의 무회귀.** 무회귀 대조는 합성 리그 `_CYC_RIG` 로만 쟀다.
   cyc 가 있는 **실제** 리그의 그룹 이름으로는 한 번도 재지 않았다.
3. **색·밝기의 무대 적합성.** D2 와의 대비(밝기 3배·방향 추가·색온도 반전)는 설계 의도이며
   관측이 아니다.
4. **`edm.yaml:7` 산문.** 위 PARTIAL — 라이브러리는 10룩인데 헤더는 여전히 「Nine looks」다.
5. **CI 초록.** 이 기록을 쓰는 시점에 PR 은 방금 열렸고 CI 결과는 아직 안 봤다.
   위 숫자는 전부 이 워크트리의 로컬 실행이다.
6. **`_PAIR_COUNTS`·`REAL_LOOKS` 등 갱신한 기대값의 의미 재검토.** 값을 자산에서 다시 재어
   맞췄을 뿐, 각 검사가 원래 재려던 성질이 여전히 유효한지는 검사별로 따로 읽지 않았다
   (비공허 근거가 리터럴이 아닌 것들 — `len(edm) > MAX_TOOL_MATCHES`, 전량 스윕 —
   은 유지했음을 확인했다).

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_
