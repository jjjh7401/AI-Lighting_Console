# SPEC-COPILOT-D1GRANT-001 — 실행 계획

> 카드 t282 후속 · Tier M · 기준 트리 `main` `a1e75e5` (2026-09-06 `git fetch origin main` 으로 확인)
>
> 이 계획은 **되돌리기 어려운 순서**로 배열했다. M1(연출 자산)이 먼저이고 M4(기계적 정정)가 마지막이다. 감독이 읽어야 할 판단은 M1 과 M2 에 몰려 있다.

---

## §A 맥락 — 이 트리에서 직접 확인한 앵커

전부 `a1e75e5` 에서 열어 확인했다. 배차서나 앞선 카드의 인용을 옮기지 않았다.

| 앵커 | 값 | 무엇을 말하는가 |
|---|---|---|
| `server/looks/busking.py:81-97` | `looks_for_genre` = `sorted(key=(dynamics, look_id))` | 정렬 축이 **파일 위치가 아니다** — REQ-003 의 근거 |
| `server/looks/songcue.py:427-440` | `_select_bindable` = 「묶이는 첫 룩」 | t278 의 수정. 이 SPEC 은 안 건드린다 |
| `server/looks/songcue.py:223` | `map_sections_to_looks` 가 `looks_for_genre` 로 후보를 만든다 | 정렬 축이 선택으로 이어지는 경로 |
| `server/tests/test_overlap_preserve.py:96-107` | `_PRESERVE_PATHS` 10항목, 7번째가 `server/looks/library/` | 막힌 자리 |
| 같은 파일 `:310-338` | `_LOOKS_GRANTED_LINE_PAIRS` — 3파일 「파란」 미러 | 유일한 기존 룩 승인 |
| 같은 파일 `:1050-1099` | `TestLooksLibraryGrantedExtension` 4개 단언 | 고칠 클래스 |
| 같은 파일 `:1078-1080` | 파일 **집합** 단언 | 추가조차 막는 자리 |
| 같은 파일 `:981-1013` | `TestChoreographyObservedEffectGrantedAppend` | append-only 승인의 **선례 모양** |
| 같은 파일 `:130`·`:144`·`:298` | 다른 SPEC 이 발급한 승인 셋 | §1.4 의 「닫힌 SPEC 문제 없음」 근거 |
| `server/tests/test_songcue_rig_aware_look.py:237-261` | `TestWhatThisFixCannotReach` | 뒤집을 핀 ① |
| 같은 파일 `:263-277` | 행렬 `{"edm":"XOOOO","rock":"XOOOO"}` | 뒤집을 핀 ② |
| `server/tests/test_busking_genre.py:30` | `_EXPECTED_COUNTS = {..., "rock": 8, "edm": 9}` | 뒤집을 핀 ③ |
| 같은 파일 `:45-52` | `test_edm_nine_looks_survive`, `len(edm) == 9` | 뒤집을 핀 ④ |
| `server/tests/test_looks_matching.py:673-677` | `report["total"] == 9` | 뒤집을 핀 ⑤ |
| `server/looks/library/edm.yaml:7` | 「Nine looks」 | 뒤집을 핀 ⑥ (산문) |
| `server/looks/busking.py:13` | 「9룩이므로 … 정확히 1건이 조용히 사라진다」 | 뒤집을 핀 ⑦ (산문, 숫자만 고치면 틀린다) |
| `server/tests/test_looks_library.py:49-50` | `MIN 6` / `MAX_LOOKS_PER_GENRE = 10` | edm 이 10 이 되어 **상한에 닿는다** |
| `server/preshow/checks.py:111` | `count = len(library.looks)` 를 동적으로 보고 | 핀이 **아니다** |
| 기준 커밋 `95687a0e` 의 `edm.yaml` / `rock.yaml` | 156행 / 141행 | append 훅의 `old_start` 기대값 |
| 현재 룩 디렉터리 diff (`--numstat`, `95687a0e..HEAD`) | ballad 2/2 · edm 1/1 · worship 2/2 | 승인된 「파란」 쌍 넷이 전부 |
| `edm.yaml` 훅 (`--unified=0`) | `@@ -74 +74 @@` 하나 | 삽입(옛 156행)이 **뒤**에 온다 → diff 순서 결정론적 |

**착수 시 초록 확인**(같은 회차):

```
.venv/bin/python -m pytest server/tests/test_overlap_preserve.py server/tests/test_songcue_rig_aware_look.py -q -p no:cacheprovider
130 passed in 2.15s
```

**인터프리터 귀속**(`server/tests` 하위에서):

```
../../.venv/bin/python -c "import server; print(server.__file__)"
→ …/.claude/worktrees/agent-aee2cc5604c4db64c/server/__init__.py
```

---

## §B 알려진 함정

### B-1 「파일 뒤에 놓으면 안전하다」는 제안서의 전제가 틀렸다

PR #344 §2 는 무회귀 근거를 「파일에서 기존 D1 룩 **뒤에** 놓는다」로 적었다. `looks_for_genre` 는 `(dynamics, look_id)` 로 정렬하므로 **파일 순서를 읽지 않는다**. 결과는 우연히 같지만 근거가 다르고, 근거가 틀린 채로 굳으면 나중에 `look_id` 를 바꾸는 순간 조용히 깨진다. REQ-003 이 이것을 검사로 바꾼다.

### B-2 승인 줄 텍스트 단언을 느슨하게 만들면 게이트가 죽는다

`test_every_change_is_a_granted_line_pair_and_every_pair_is_present`(`:1082-1086`)는 추가 줄 목록의 **정확한 일치**를 요구한다. 추가분을 통과시키는 가장 쉬운 방법은 `==` 를 `>=`(부분집합)로 바꾸는 것이고, 그렇게 하면 승인 밖의 임의 편집이 전부 통과한다. **금지**한다 — 두 승인의 줄 목록을 순서대로 이어붙인 값과의 `==` 를 유지한다(REQ-009).

### B-3 산문 인용은 숫자만 바꾸면 틀린다

`server/looks/busking.py:13` 은 「EDM은 9룩이므로 그 경로를 타는 순간 **정확히 1건이 조용히 사라진다** — 8룩이 돌아오고」라고 적는다. 10룩이면 사라지는 것은 **2건**이고 「8룩이 돌아온다」는 여전히 참이다. 세 숫자가 서로 다른 것을 세고 있으므로 문장을 다시 써야 한다.

### B-4 자산 스캔이 산문까지 본다

`test_looks_library.py` 의 `FORBIDDEN_ATTRIBUTE_TOKENS`(`:75`)와 `PER_SHOW_PATTERN`(`:82`)은 YAML **텍스트 전체**(주석 포함)를 스캔한다. 새 블록의 한국어 주석에 `Focus`·`Frost`·`Prism`·`Shutter`·`Pan`·`Tilt` 가 부분 문자열로 들어가거나, 「그룹 3」·「프리셋 12」 같은 키워드+숫자가 들어가면 실패한다.

### B-5 edm 이 상한에 정확히 닿는다

`MAX_LOOKS_PER_GENRE = 10`. 이 추가로 edm 은 10 이 된다 — 통과하지만 **여유가 0**이다. 다음 edm 룩은 상수를 올리는 별도 결정을 요구한다. 이 사실을 progress 에 기록한다.

### B-6 PR #344 의 머지 순서

`server/tests/test_songcue_d1_cycless.py` 와 제안서 문서는 아직 머지되지 않은 브랜치 `WT-d1-looks`(PR #344, OPEN)에 있다. run 단계는 착수 시점에 그 PR 의 상태를 **재서** 갈래를 정한다: 머지됐으면 skip 게이트를 걷어내고, 아니면 REQ-016 의 최종 형태로 새로 만든다. 어느 쪽이든 **최종 상태는 같다** — 그것이 AC 가 재는 값이다.

### B-7 t282 의 실측 인용은 다른 트리에서 나왔다

§1.3 에 옮긴 게이트 실패 출력은 PR #344 브랜치에서 나온 것이다. run 단계는 그 출력을 **다시 만든다**(REQ-012 의 심은 변경 ①과 같은 형태). 남의 트리 출력을 이 SPEC 의 증거로 쓰지 않는다.

---

## §C 결정 — 가장 되돌리기 어려운 것부터

### C-1 두 룩의 역할 — 이 SPEC 의 유일한 연출 판단 (되돌리기 가장 어려움)

역할은 무대에서 실제로 보이는 것을 정하고, 한번 출하되면 감독의 쇼에 들어간다. 후보와 배제 사유:

| 장르 | 채택 | 배제한 후보와 사유 |
|---|---|---|
| edm | `백라이트` | `프론트` — 헤더 규칙이 배제(관객은 부스를 본다). `탑` — 실기 리그 `no_match`. `사이드` — D2 `edm-groove-cyan` 이 이미 쓰며, D1 에서 쓰면 D2 진입의 「방향이 하나 늘어남」이 사라진다. `스페셜` — EDM 에 독주자 개념이 없다 |
| rock | `사이드` | `프론트`·`스페셜` — 헤더 규칙이 「얼굴은 어둡고 형태만」이라 장르를 깬다. `백라이트` — D2 `rock-verse-side` 가 이미 쓰며, 선점하면 벌스 진입이 밋밋해진다. `탑` — 실기 리그 `no_match` |

두 채택 모두 **실기 리그에서 묶이는 역할**(§A 실측: 백라이트·프론트·사이드·스페셜)이며, 이것이 이 SPEC 이 존재하는 이유다.

### C-2 값 — 역산이지 측정이 아니다

| 룩 | Dimmer | RGB | 역산 기준 |
|---|---|---|---|
| `edm-haze-shafts` | 18 | 0/40/78 | `edm-ambient-hold`(20, 0/55/70)보다 어둡고 더 파랗게 — 「아직 시작 안 했다」. D2 `edm-groove-cyan`(55)의 3분의 1 |
| `rock-wing-embers` | 22 | 65/10/22 | `rock-empty-stage`(25, 60/8/30)와 같은 계열, 조금 더 어둡고 붉게. D2 `rock-verse-side`(48, 차가운 청)와 색온도 반전 |

**이 표의 어떤 값도 실기에서 발사되지 않았다.** 값 수정은 되돌리기 쉬우므로(YAML 한 줄) 실기 회차의 결과에 따라 후속 카드에서 조정한다 — 그러나 **역할은 되돌리기 어렵다**(선택 동작이 바뀐다). 그래서 C-1 이 먼저다.

### C-3 승인 상수의 모양 — 정확한 텍스트 튜플

세 후보를 비교했다:

| 후보 | 장점 | 채택 안 한 이유 |
|---|---|---|
| **정확한 줄 텍스트 튜플** (채택) | 같은 클래스의 형제 승인(`_LOOKS_GRANTED_LINE_PAIRS`)과 같은 규율. 사람이 읽어 무엇이 승인됐는지 안다 | — |
| 블록 sha256 다이제스트 | 짧다. `_CONSOLE_LUA_GRANTED_REVISION_DIGESTS` 선례 있음 | 읽어서 알 수 없다. 룩 정의는 사람이 감사해야 할 **내용**이지 불투명한 개정이 아니다 |
| 경로 이름만 (`_RULEBOOK_GRANTED_ADDITIONS` 형) | 가장 짧다 | 승인 파일 안에서 **무엇이든** 추가 가능해진다 — 파일당 룩 하나라는 폭이 안 잡힌다 |

상수 안에 들어갈 **정확한 줄 텍스트는 run 단계가 커밋한 블록에서 나온다.** 이 SPEC 은 그 블록의 **의미**(look_id·역할·값·룩 하나)를 못박고, 게이트 상수는 그 바이트를 못박는다.

### C-4 append 위치 — 옛 EOF

기능적으로는 아무 데나 놓아도 된다(C-1 의 정렬 축). 옛 EOF 를 고르는 이유는 게이트 쪽이다: 순수 삽입 훅 하나(`old_count == 0`)가 되어 위쪽이 한 줄도 안 밀리고, 「파란」 훅(옛 74행)이 삽입 훅(옛 156행)보다 **앞**에 오므로 추가 줄의 diff 순서가 `[쌍의 새 줄] + [블록]` 으로 결정된다. 그 결정론이 REQ-009 의 정확 일치를 가능하게 한다.

가독성 비용은 있다 — dynamics 오름차순으로 읽히던 파일 끝에 D1 룩이 하나 붙는다. 블록 앞에 구간 주석을 달아 상쇄한다.

### C-5 뒤집히는 핀을 어떻게 다룰 것인가

`TestWhatThisFixCannotReach` 는 **삭제하지 않는다.** 그 클래스는 「고칠 수 없는 것」의 기록이었고, 그것이 고쳐졌다는 사실 자체가 기록될 값이다. 교체하되 독스트링에 전/후를 남긴다(REQ-014).

행렬이 전량 O 가 되면 계측기가 공허해도 초록이다. 그래서 같은 자리에 `_UNBINDABLE_RIG` 음성 대조 행렬(전량 X)을 둔다(REQ-015). `TestInstrumentIsNotVacuous` 가 이미 개별 단언으로 같은 일을 하지만, **행렬을 읽는 사람**이 그 대조를 함께 봐야 한다.

---

## §D 제약

- `SPEC-COPILOT-PRECHK-001/plan.md` 바이트 불변 (REQ-006).
- `_PRESERVE_PATHS`·`_PRECHK_BASE`·`_preserve_diff_command()` 불변 (REQ-013).
- 기존 네 자산 파일의 삭제 줄은 승인된 「파란」 옛 줄 넷 외 0건 (REQ-004).
- 콘솔 쓰기 0, 포트 8000 미접촉 (REQ-021).
- 무브먼트 속성 0, 빔 계열 0 — v1 라이브러리 규율.
- 검증은 워크트리 안의 `.venv` 인터프리터로 실행하고, 그 귀속을 progress 에 남긴다.

---

## §E 마일스톤

### M1 — 두 룩을 라이브러리에 넣는다 (우선순위 High, 되돌리기 가장 어려움)

- `edm.yaml` 옛 EOF 뒤에 `edm-haze-shafts` 블록 하나, `rock.yaml` 옛 EOF 뒤에 `rock-wing-embers` 블록 하나. 각 블록 앞에 구간 주석.
- 기존 줄 0 수정. 무브먼트·빔 속성 0.
- 이 시점에서 `test_overlap_preserve.py` 는 **빨강이어야 한다** — 그 출력을 인용해 두면 M2 의 대조군이 된다(B-7).
- 검증: `test_looks_library.py` 전량 초록(스키마·색·강도·역할·한국어·금지 토큰·per-show 패턴), `test_songcue_rig_aware_look.py` 의 cyc 리그 무회귀 검사 초록.

### M2 — 승인을 게이트에 등록하고, 게이트가 여전히 거절하는지 재본다 (우선순위 High)

- `_LOOKS_GRANTED_D1_APPENDS` 추가 + 승인 주석(이 SPEC ID, 날짜, 발급 근거).
- `TestLooksLibraryGrantedExtension` 의 네 단언 갱신 + 새 단언 셋(EOF 삽입 훅 / 블록당 룩 하나 / 비공허성).
- **심은 변경 셋으로 거절을 실측하고 되돌린다**(REQ-012): ① `ballad.yaml` 에 한 줄 추가 ② `rock.yaml` 에 룩 하나 더 추가 ③ `edm.yaml` 에서 줄 하나 삭제. 각 실패 출력의 꼬리를 progress 에 인용한다.
- 검증: `test_overlap_preserve.py` 초록(심은 변경 되돌린 상태), 심은 상태에서 빨강.

### M3 — 뒤집히는 핀을 의도적으로 갱신한다 (우선순위 Medium)

- `TestWhatThisFixCannotReach` 교체 + 독스트링의 전/후 기록.
- 행렬 갱신 + 음성 대조 행렬 추가.
- `test_songcue_d1_cycless.py` 를 최종 형태로 (skip 게이트 0, `TestTheSkipIsNotAPermanentPass` 없음). PR #344 상태를 먼저 재고 갈래를 정한다(B-6).
- 검증: 세 파일 초록, skip 0건(`-rs` 로 확인).

### M4 — 개수를 세는 자리를 전수로 훑고 산문을 정정한다 (우선순위 Medium)

- `_EXPECTED_COUNTS`, `test_edm_nine_looks_survive`, `report["total"] == 9`.
- `edm.yaml:7` 「Nine looks」, `busking.py:13` 「9룩 … 1건」 (B-3 — 숫자만 바꾸지 않는다).
- **전수 스윕**: 룩 개수에 의존하는 자리를 grep 으로 훑고 결과 표를 progress 에 남긴다(REQ-020). plan 단계 실측 세 건이 전부라는 주장이 아니다.
- 검증: `server/tests` 전량 초록, 새 회귀 0.

---

## §F 위험

| 위험 | 등급 | 왜 | 완화 |
|---|---|---|---|
| **색·밝기가 무대에서 안 맞는다** | 중 | 값이 역산이고 실기 발사 0건. 조명은 숫자가 맞아도 눈에 틀릴 수 있다 | 값 수정은 YAML 한 줄이라 되돌리기 쉽다. 실기 확인을 sync 단계 후속 카드로 올린다(§4). SPEC 본문이 이 상태를 명시한다 |
| **역할 선택이 장르를 깬다** | 중 | 역할은 선택 동작을 바꾸므로 값보다 되돌리기 어렵다 | C-1 의 배제표를 감독이 읽고 결정한다. D2 와의 대비를 §5 에 수치로 적어 검토 가능하게 했다 |
| 게이트가 조용히 넓어진다 | 중 | 승인을 더하는 편집은 「통과시키는」 방향의 압력을 받는다 | REQ-012 의 심은 변경 셋을 **실측**으로 요구한다. B-2 가 느슨한 술어를 명시적으로 금지한다 |
| 핀이 조용히 뒤집힌다 | 중 | 일곱 자리가 반드시 실패하고, 숫자만 고치면 초록이 된다 | REQ-014·015·019 가 **왜 바뀌었는지**를 같은 자리에 요구한다. B-3 이 숫자만 고치면 틀리는 문장을 지목한다 |
| 개수 의존 자리를 놓친다 | 중 | plan 단계 grep 이 전수라는 보장이 없다 | REQ-020 이 run 단계 전수 스윕과 그 명령을 요구한다. 놓친 자리는 전량 스위트가 빨강으로 잡는다 |
| edm 이 상한에 닿는다 | 낮 | `MAX_LOOKS_PER_GENRE = 10` 에 정확히 도달 | 이번엔 통과. progress 에 기록해 다음 카드가 알게 한다(B-5) |
| PR #344 와의 충돌 | 낮 | 같은 파일을 다른 브랜치가 만든다 | B-6 의 갈래. 최종 상태를 AC 가 재므로 어느 순서든 같은 곳에 도달 |

---

## §G 반패턴 — 이 SPEC 에서 하지 말 것

- 승인 단언을 `==` 에서 부분집합으로 바꿔 통과시키기 (B-2).
- `_PRESERVE_PATHS` 에서 `server/looks/library/` 를 빼서 통과시키기 — 그것은 승인이 아니라 경계 삭제다.
- `SPEC-COPILOT-PRECHK-001/plan.md` 를 고쳐 「이제 룩 라이브러리도 바뀔 수 있다」로 만들기 — 역사적 사실의 사후 개정(§1.4).
- 뒤집히는 핀에서 숫자만 갈아끼우고 이유를 안 적기.
- 실기 발사 없이 색 값을 「검증됨」으로 보고하기.
- 룩을 두 개 이상 넣으면서 승인은 하나로 적기.

---

## §H 교차 참조

- `server/tests/test_overlap_preserve.py` 모듈 독스트링 (`:28-61`) — 선언 층 우선 원칙과 「닫힌 SPEC」 경고의 원문
- `.moai/specs/SPEC-COPILOT-PRECHK-001/plan.md:89` §A.5 — 원 선언 (불변)
- `.moai/specs/SPEC-COPILOT-SONGCUE-001/spec.md:182` — 선례 게이트의 다른 기준
- PR #344 (브랜치 `WT-d1-looks`) — 설계 제안서와 부재 트립와이어 검사의 출처
- 카드 t277 (실기 관측) · t278 (선택기 수정과 잔여 핀) · t282 (게이트 실측)
