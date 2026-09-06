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

> 브랜치 `WT-d1-grant-run`, 기준 `origin/main` `dc2ced3`(PR #344 머지 포함).
> 인터프리터 귀속: `server/tests` 하위에서 `../../.venv/bin/python -c "import server; print(server.__file__)"`
> → 이 워크트리의 `server/__init__.py`. 남의 트리 `.pth` 가 이기지 않았다.
> 착수 초록: `uv run python -m pytest server/tests -q -p no:cacheprovider` → `11757 passed, 22 skipped in 185.21s`.

### B-6 갈래 판정 (착수 시 재측정)

`gh pr view 344 --json state,mergedAt` → `{"state":"MERGED","mergedAt":"2026-09-06T12:26:25Z"}`.
머지됐으므로 **skip 게이트를 걷어내는** 갈래. 이 브랜치는 `a1e75e5` 에서 잘려 있어
`origin/main` 을 머지해 `test_songcue_d1_cycless.py` 를 받았다.

### AC PASS/FAIL 행렬

| AC | 판정 | 실행한 명령 | 관측 |
|---|---|---|---|
| AC-001 | PASS | `uv run python -c "…looks_for_genre…"` + `pytest server/tests/test_looks_library.py` | edm D1 = `['edm-ambient-hold','edm-haze-shafts']`, `edm-haze-shafts` roles `('백라이트',)` Dimmer 18 · RGB 0/40/78 · rock D1 = `['rock-empty-stage','rock-wing-embers']`, roles `('사이드',)` Dimmer 22 · RGB 65/10/22 — 명세와 일치. 라이브러리 인구조사 `29 passed` |
| AC-002 | PASS | `pytest server/tests/test_songcue_rig_aware_look.py` | `TestWhatThisFixCouldNotReachUntilTheLibraryGrew` 네 장르 전량 초록 — `ambient` 가 실기 리그에서 큐를 받는다. 음성 대조(`_UNBINDABLE_RIG`) 네 장르 전량 `[]` |
| AC-003 | PASS | `pytest server/tests/test_songcue_d1_cycless.py` | `test_the_incumbent_sorts_before_the_added_look_by_look_id` — `look_id` 사전순을 **직접** 단언. `TestDeterministicTotalOrder` 초록 |
| AC-004 | PASS | `pytest server/tests/test_songcue_rig_aware_look.py::TestCycRigIsUnchanged` | 4장르 × 다이내믹스 1~5 전량 `_naive_first_match` 와 일치. edm D1 = `edm-ambient-hold`, rock D1 = `rock-empty-stage` |
| AC-005 | PASS | `git diff --numstat 95687a0e..HEAD -- server/looks/library/` · `--unified=0 … \| grep '^@@'` | 바뀐 파일 넷: `ballad 2/2` · `edm 25/2` · `rock 21/0` · `worship 2/2`. rock 삭제 **0**. 훅: edm `@@ -7 +7 @@` · `@@ -74 +74 @@` · `@@ -156,0 +157,23 @@`, rock `@@ -141,0 +142,21 @@` — 삽입 훅 `old_count == 0`, `old_start` 156·141 = 기준 커밋 줄 수. 블록당 `- look_id:` 정확히 1회 |
| AC-006 | PASS | `git diff --stat origin/main..HEAD -- .moai/specs/SPEC-COPILOT-PRECHK-001/` | 빈 출력 |
| AC-007 | PASS | `pytest server/tests/test_overlap_preserve.py` · `grep -c 'SPEC-COPILOT-D1GRANT-001' …` | `56 passed`. grep `2`(≥1). 파일 집합 단언은 세 승인의 **합집합**, 줄 텍스트 단언은 `==` 유지 |
| AC-008 | PASS | 심은 변경 셋을 각각 커밋 → `pytest …::TestLooksLibraryGrantedExtension` → `git revert` | 셋 다 거절(출력은 §E.2 「심은 변경」 절). 되돌린 뒤 numstat 이 심기 전과 동일 |
| AC-009 | PASS | `pytest …::TestPreserveList` · `…::TestPreserveDiffIsEmpty` | 초록. `_PRESERVE_PATHS`(10항목)·`_PRECHK_BASE`·`_preserve_diff_command()` 본문 변경 hunk 0건 |
| AC-010 | PASS | `pytest server/tests/test_songcue_rig_aware_look.py` | `TestWhatThisFixCannotReach` → `TestWhatThisFixCouldNotReachUntilTheLibraryGrew` 로 **교체**. 독스트링이 전/후를 함께 기록. 새 단언 = 네 장르 전부 「역할이 `{탑,배경}` 부분집합 아닌 D1 룩 존재」 + 「`ambient` 가 큐를 받는다」 |
| AC-011 | PASS | `pytest …::test_the_matrix_is_recorded_for_the_report` | 실기 행렬 네 장르 `"OOOOO"`, **같은 함수 안** 음성 대조 네 장르 `"XXXXX"` |
| AC-012 | PASS | `pytest server/tests/test_songcue_d1_cycless.py -q -rs` · `grep -c 'pytest.skip\|_require_proposed\|TestTheSkipIsNotAPermanentPass' …` | `14 passed`, skip **0건**. grep `0` |
| AC-013 | **PASS-WITH-DEBT** | `pytest server/tests -q` · `grep -rn 'Nine looks' server/` · `grep -n '9룩' server/looks/busking.py` | 전량 초록. `_EXPECTED_COUNTS = {"worship":8,"rock":9,"ballad":7,"edm":10}`, `report["total"] == 10`, `9룩` 0행. **다만 `grep -rn 'Nine looks' server/` 는 0 이 아니라 2** — 상세는 아래 |
| AC-014 | PASS | `git diff origin/main..HEAD -- server/ \| grep -c 8000` · 전량 스위트 | `0`. UDP 전송 0건. conftest 의 `LIVE_CONSOLE_PORT = 8000` autouse 가드가 실패시킨 검사 0건 |

### AC-013 이 PASS-WITH-DEBT 인 이유 — AC 와 REQ 가 부딪힌다

AC-013 은 `grep -rn 'Nine looks' server/` 가 **0행**일 것을 요구한다. 실측은 **2행**이고
둘 다 `server/tests/test_overlap_preserve.py` 다:

```
server/tests/test_overlap_preserve.py:446:#: "Nine looks", because the append makes that sentence false. A comment is not
server/tests/test_overlap_preserve.py:469:            "# different room than the build did. Nine looks, weighted toward the top of the",
```

469 행은 **없앨 수 없다.** 같은 SPEC 의 REQ-007·009 가 승인을 「정확한 줄 텍스트」로
못박으라고 요구하고, 줄 텍스트 승인은 정의상 **옛 줄**을 문면에 담는다. 446 행은 그
쌍이 왜 존재하는지를 적은 설명이다.

AC 가 재려던 것 — **출하되는 자산이 자기 내용과 어긋나는 개수를 주장하지 않는다** — 은
충족됐다: `grep -rn 'Nine looks' server/looks/` 는 **0행**이고, `edm.yaml:7` 은 이제
`Ten looks` 다. 남은 2행은 그 정정이 **일어났다는 증거**이자 조용한 되돌림을 막는
핀이다.

이것은 이 SPEC 안에서 두 번째로 만난 같은 계열의 충돌이며(첫 번째는 REQ-004 의
기계적 프록시 대 REQ-019), 어느 쪽도 문서를 고쳐 해소하지 않고 **실측과 함께
기록**했다. 감독 판단이 필요한 자리다.

### 심은 변경 셋 — 게이트가 여전히 거절한다 (AC-008)

셋 다 커밋한 뒤 측정하고 `git revert` 로 되돌렸다. 게이트는 `_PRECHK_BASE..HEAD` 를
읽으므로 **워킹트리 편집만으로는 발화하지 않는다** — 이것 자체가 이 회차에서 배운
성질이고, 그래서 심은 변경은 반드시 커밋해야 측정된다.

**① `ballad.yaml` 에 승인 밖 한 줄** (`7d5fe32`)

```
>           assert added == [new for _old, new in pairs] + list(appended), path
E           AssertionError: server/looks/library/ballad.yaml
E           assert ['    aliases...이트가 거절해야 한다.'] == ['    aliases...t", "night"]']
E             Left contains 2 more items, first extra item: ''
```

**② 승인 파일에 룩 하나 더** (`rock.yaml`)

```
>           assert added == [new for _old, new in pairs] + list(appended), path
E           AssertionError: server/looks/library/rock.yaml
E           assert ['', '  # ---...서 침묵했다.', ...] == ['', '  # ---...서 침묵했다.', ...]
E             Left contains 13 more items, first extra item: ''
```

**③ 승인 파일에서 줄 하나 삭제** (`edm.yaml` 의 `aliases` 행)

```
>           assert deleted == [old for old, _new in pairs], path
E           AssertionError: server/looks/library/edm.yaml
E           At index 0 diff: '    aliases: ["앰비언트 홀드", "ambient hold", "대기"]' != '    mood_keywords: [...]'
E             Left contains one more item: '    mood_keywords: ["깊은", "푸른", "숨고르는", "브레이크다운", "deep", "breakdown"]'
```

되돌린 뒤 `git diff --numstat 95687a0e..HEAD -- server/looks/library/` 가 심기 전과
동일하고 `test_overlap_preserve.py` 가 다시 초록임을 확인했다.

**부수 기록**: 심은 변경 ①을 처음에 `worship.yaml` 로 잘못 심었다(acceptance.md 는
`ballad.yaml` 을 지정한다). `fc5b615` 와 그 revert 가 이력에 남아 있다.

### 개수 소비자 전수 스윕 (REQ-020) — plan 단계 목록은 전수가 아니었다

세 갈래로 쟀고, **전량 스위트가 기준**이 됐다.

| 갈래 | 명령 | 결과 |
|---|---|---|
| grep ① 리터럴 | `grep -rn "Nine looks\|9룩\|== 9\|len(edm)\|nine_looks\|MAX_LOOKS_PER_GENRE\|_EXPECTED_COUNTS" server/ docs/` | 대부분 무관(포트·픽스처 수). 룩 개수 자리 5건 |
| grep ② 계수식 | `grep -rn --include='*.py' … -e 'len(looks_for_genre' -e 'len(library.looks)' -e 'len(selection.looks)' -e 'len(d1)' -e '8룩' -e '10룩' server ui docs .moai` | ①이 못 본 `test_busking_bundle.py:95` 발견(worship 8룩 — **이 SPEC 의 영향 없음**) |
| ③ 기계 전수 | `uv run python -m pytest server/tests -q` | **17건 실패 / 6개 파일** — ①·②가 합쳐도 못 본 파일 넷 포함 |

**plan 단계가 예고한 자리(3건)**: `test_busking_genre.py` · `test_looks_matching.py` ·
산문 둘(`edm.yaml:7`, `busking.py:13`).

**plan 단계가 놓친 자리(4개 파일)**:

| 파일 | 무엇이 뒤집혔나 | 처리 |
|---|---|---|
| `test_looks_blue_alias.py` | 「`푸른` 을 쓰면 같은 슬롯에 `파란` 쌍둥이가 있어야 한다」 불변식. 새 룩 `edm-haze-shafts` 가 이를 어겼다 | **검사가 결함을 잡았다.** 룩에 `파란` 을 더하고 비공허 계수 5→6, 룩 수 3→4 |
| `test_scene_compile.py` | 라이브러리 전량 32→34 | 리터럴 갱신 + 사유 기록 |
| `test_busking_report.py` | `(룩,역할)` 쌍 rock·edm 26→27, 단일 역할 최대 기여 7→8 | 두 룩 모두 역할 하나뿐이라 +1씩 |
| `test_songcue_unmapped_notice.py` | **카드 t277 의 회귀 핀 자체** — 이 SPEC 이 닫은 손해를 고정하던 검사 | 아래 별도 절 |

`server/preshow/checks.py:111` 은 `len(library.looks)` 를 동적으로 세어 보고만 하므로
핀이 아니다(plan 단계 판정 재확인).

### t277 회귀 핀이 뒤집힌 것이 이 SPEC 의 가장 강한 증거다

`test_songcue_unmapped_notice.py` 는 카드 t277 이 실기 회차를 고정한 파일이다. 그
검사가 단언하던 것은 **이 SPEC 이 없애려던 바로 그 손해**다:

- 전: `generated_count == 3` · `unmapped_sections == ["Intro"]` · `reason_kind == "role_unaddressed"` · 감독 고지 「구간 4건 중 큐 3건」
- 후: 같은 실기 18그룹 리그, 같은 네 구간, `generated_count == 4` · `unmapped_sections == []` · 고지 **빈 문자열**

문자열 검색이 아니라 도구 → 게이트 → `run_commands` → 기록 포트까지 실제 경로를 탄
뒤의 보고다. 검사 이름을 `test_the_live_rig_now_stores_every_section` 으로 바꾸고
독스트링에 전/후를 남겼다.

고지 기계는 **죽지 않았다 — 울릴 일이 없어졌을 뿐이다.** 그 구별을 잃지 않으려고
`BACK` 을 뺀 리그(`_RIG_WITHOUT_BACKLIGHT`)를 새 시험대로 두고 고지 문면 검사를 그
위에서 돌린다. 그 리그에서는 edm D1 후보 둘이 요구하는 `백라이트`·`배경` 이 둘 다 안
묶여 첫 구간이 다시 건너뛰어지고, t277 이 본 「4건 중 3건」 형상이 그대로 재현된다.

### 게이트 재조정 — REQ-004 프록시와 REQ-019 의 충돌

`edm.yaml:7` 의 산문 수정(REQ-019)은 한 줄 삭제 + 한 줄 추가이므로 REQ-004 의
**기계적 프록시**(「「파란」 옛 줄 넷 외 삭제 0건」)를 건드린다. 그러나 REQ-004 의
첫 문장이 지키려는 것은 「**기존 룩의 어떤 필드도** 바꾸지 않는다」이고, 헤더 주석은
룩의 필드가 아니다 — **의도는 안 부딪히고 프록시가 자기 의도보다 넓게 잡은 것**이다.

느슨하게 푸는 대신 **핀으로** 해소했다: `_LOOKS_GRANTED_COUNT_PROSE_PAIRS` 에 옛/새
줄을 정확한 텍스트로 못박았다. 게이트의 강도는 그대로다(핀 안 된 것은 여전히 실패).
세 승인의 연결 **순서**(prose 7 → 파란 74 → append 156)도 가정하지 않고
`test_the_granted_hunks_appear_in_the_order_this_class_concatenates_them` 이 훅 위치로
잰다. 충돌 자체는 상수 주석에 그대로 남겼다.

### 콘솔 예산 (AC-014)

- UDP 전송 0건, `127.0.0.1:8000` 대상 실행 **0건**. 변경된 파일 diff 안에 `8000` 문자열 0개.
- `server/tests/conftest.py:41` 의 `LIVE_CONSOLE_PORT = 8000` autouse 가드가 실패시킨 검사 0건.
- 실기 콘솔에 발화한 명령 없음. 이 회차는 전량 오프라인이다.

### 검증 명령 꼬리

```
uv run python -m pytest server/tests -q -p no:cacheprovider
11775 passed, 12 skipped, 1 warning in 142.99s (0:02:22)

npm --prefix ui run test
Test Files  23 passed (23)
     Tests  544 passed (544)

npx --prefix ui tsc --noEmit -p ui/tsconfig.json
(출력 없음, exit 0)

uv run ruff check server/
All checks passed!
```

착수 `11757 passed, 22 skipped` → 종료 `11775 passed, 12 skipped`. skip 10건 감소는
`test_songcue_d1_cycless.py` 의 skip 게이트가 사라진 몫이다.

**관측된 플레이크 1건**: 전량 스위트 1회차에서
`test_responder_roundtrip.py::TestRoundtrip::test_expect_version_mismatch_fails_ping_with_clear_detail`
이 실패했으나 단독 재실행에서 통과했고, 2회차 전량 스위트도 통과했다. 룩 계층과
무관한 UDP 왕복 하네스이며 이 SPEC 의 변경이 닿지 않는다. **이 SPEC 이 만든 회귀로
보지 않지만, 안 잰 채로 넘기지 않고 여기 기록한다.**

### 안 잰 것 (이 SPEC 이 닫혀도 미검증으로 남는다)

- **실기 콘솔 발사 0건.** 두 룩의 색·밝기는 이웃 룩에서 역산한 **설계값**이며 무대에서 확인한 적이 없다. 연출 품질 위험이고 감독의 눈이 최종 심판이다.
- **실기 cyc 리그 지문에서의 무회귀.** 대조는 합성 리그 `_CYC_RIG` 로만 쟀다. 실기에 cyc 가 있는 리그를 물려 본 적이 없다.
- **색·밝기의 무대 적합성.** D2 와의 대비(밝기 3배·방향 추가·색온도 반전)는 숫자상 성립하지만 눈으로 본 적이 없다.
- **`edm` 이 `MAX_LOOKS_PER_GENRE = 10` 에 정확히 닿았다.** 통과하지만 여유가 **0**이다. 다음 edm 룩은 그 상수를 올리는 별도 결정을 요구한다.
- **개수 소비자 전수의 완전성.** 세 갈래로 쟀고 전량 스위트가 기준이지만, 「스위트가 안 재는 소비자」는 이 방법으로 못 본다(예: 문서·UI 문면). `ui/` 와 `docs/` 는 grep 으로만 훑었다.
- **`_RIG_WITHOUT_BACKLIGHT` 가 실기 지문이 아니다.** t277 의 「4건 중 3건」 형상을 재현하려고 실기 리그에서 `BACK` 을 뺀 **합성** 리그다.

## §E.3 Run-phase Audit-Ready Signal

```yaml
run_complete_at: 2026-09-06
run_commit_sha: pending-backfill-run
run_status: audit-ready
ac_pass_count: 13
ac_pass_with_debt_count: 1
ac_fail_count: 0
preserve_list_post_run_count: 10
new_warnings_or_lints_introduced: 0
console_writes: 0
total_run_phase_files: 12
m1_to_mN_commit_strategy: "M1 라이브러리 · M2 승인 등록 · M3 핀 갱신 · M4 전수 스윕, 각 마일스톤 1커밋 + 심은 변경 3쌍(커밋/revert) + lint 후속 1"
```

## §E.4 Sync-phase Audit-Ready Signal

_<pending sync-phase>_
