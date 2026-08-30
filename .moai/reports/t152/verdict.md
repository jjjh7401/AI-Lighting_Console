# t152 — 요청 섹션 집합: 검사 선행 + 판정

- 카드: t152 (판정 + 검사 카드, SPEC 없음)
- 트리: `.claude/worktrees/t152` · 브랜치 `WT-section-request-set`
- 기준: `origin/main` **38e09b9**
- 콘솔: 안 씀(실기 0건)
- 산출: `server/tests/test_lxseq_group_section_request.py` (신규, 8검사)

## 요약 한 줄

카드가 든 차단 근거(「빼면 실패 분류가 바뀐다」)는 **수집기 층에서는 참**이지만,
**이 도구의 출력에서는 관측 불가**다 — 사유는 `map_groups` 가 불리언으로 접고,
두 사유 중 하나(`console_unreachable`)는 도달 전에 도구가 예외로 죽는다.
검사를 먼저 세웠고, 낭비 제거 자체는 **안전장치에 닿아 리드로 넘긴다.**

## 1. Claim — 무엇을 주장하는가

| # | 주장 |
|---|---|
| C1 | `import_lxseq_groups` 는 `groups`·`fixtures` 를 요청하고 `fixtures` 단면을 **안 읽는다** |
| C2 | 요청 집합을 `groups` 단독으로 줄이면 실패 사유가 `path_not_resolved` → `console_unreachable` 로 **바뀐다** |
| C3 | 그 변화를 잡는 검사가 저장소에 **한 자리도 없었다** |
| C4 | 🔴 그러나 두 사유 모두 이 도구의 **페이로드에 도달하지 않는다** — 관측 불가 |
| C5 | 🔴 `console_unreachable` 은 이 도구에서 **원리적으로 도달 불가** — 그 전에 예외로 죽는다 |
| C6 | 픽스처 경로는 **6회** 읽힌다(섹션 페이징 5 + `read_existing_fids` 1) |
| C7 | 문면이 똑같은 둘째 호출지(:7737)는 `fixtures` 를 **실제로 소비**한다 — 일괄 치환 함정 |

## 2. Evidence — 무엇을 돌렸고 무엇이 나왔나

### C1 — 소비 지점 (판독)
`server/orchestrator/tools.py:4734-4745` 구간에서 `sections[` 는 `sections["groups"]`
하나뿐(`:4744`, `map_groups(groups_section=...)`). `sections["fixtures"]` 는 어디에도 없다.

### C2 — 실패 분류가 형제에 달렸다 (실행)
`collect_rig_sections` 를 직접 태워 같은 실패(그룹 풀 미응답)에 두 요청 집합을 준 결과:

```
with fixtures  -> reason: path_not_resolved   | resolved: 1
groups alone   -> reason: console_unreachable | resolved: 0
```

검사로 고정: 신규 파일 2절 두 검사.

### C3 — 기존 검사는 못 잡는다 (뮤테이션, 두 팔)
뮤테이션 ①: `tools.py:4735` 에서 `"fixtures": fixtures_path` 제거(:7737 은 손대지 않음).

| 팔 | 명령 | 결과 |
|---|---|---|
| ② 기존이 못 잡는가 | `uv run pytest -q --ignore=server/tests/test_lxseq_group_section_request.py` | **10505 passed, 12 skipped** — 전량 초록 |
| ② 카드가 지목한 4파일 | `uv run pytest -q test_lxseq_group_tool.py test_lxseq_group_apply_path.py test_sheets_registry.py test_sheet_pipe_content_arg.py` | **122 passed** |
| ① 신규가 잡는가 | `uv run pytest -q server/tests/test_lxseq_group_section_request.py` | **2 failed, 6 passed** (1절 두 팔) |

카드의 「검사 4파일에 단언하는 자리가 없다」는 참이고, **저장소 전체로 넓혀도 참**이다.

### C4 — 사유가 페이로드에 안 실린다 (실행)
`groups` 경로만 죽인 가짜 콘솔로 도구를 preview 디스패치:

```
console_read_incomplete = true
console_read_reason     = null
batches                 = 0
```

경로: `map_groups` 가 `section_refusal(groups_section)` 의 `(코드, 사유)` 쌍을 받고
`console_read_incomplete=True` 불리언 하나만 돌려준다(`server/lxseq/group_mapper.py:362-368`).
페이로드의 `console_read_reason`(`tools.py:4763`)은 섹션이 아니라 `fid_read` 에서 온다.
→ `path_not_resolved` 든 `console_unreachable` 든 사용자에게 **바이트 동일**.

### C5 — `console_unreachable` 은 도달 불가 (실행)
두 경로를 다 죽이면 도구가 거절이 아니라 **예외로 종료**한다:

```
LookupError: dead: Patch/Stages/1/Fixtures
  tools.py:4737  fid_read = read_existing_fids(...)
  patchplan.py:1461  state = fid_property_port.query_state(FID_FIXTURE_ROOT)
```

`collect_rig_sections` 는 예외를 잡아 분류하지만(`tools.py:1009-1013`),
`_existing_fids_from_console` 은 `ok is not True` 만 보고 **예외는 안 잡는다**.
프로덕션 포트는 실패 시 예외를 던진다 — `server/safety/console.py:670` 독스트링
"raises on failure/timeout". 즉 가짜가 아니라 실제 실패 형태다.

### C6 — 왕복 비용 (실행)
실기 실측 형태(childCount 86, 창 19)로 가짜 콘솔을 만들고 preview 1회 디스패치:

```
query_state by path:  DataPool/Groups -> 1
                      Patch/Stages/1/Fixtures -> 6
total query_state: 7 | query_property: 86
fixtures offsets: [0, 19, 38, 57, 76, 0]
```

앞의 다섯(0·19·38·57·76)이 섹션 페이징, 마지막 0이 `read_existing_fids`.
**7회 중 5회가 안 읽히는 단면 때문**이다. 카드의 「1→5회」와 일치하고, 같은 경로가
6번째로 또 읽힌다는 것이 카드가 안 적은 부분이다.
덧붙여 `FID_FIXTURE_ROOT == DEFAULT_RIG_CONTEXT_PATHS["fixtures"]` 는 **현재** True 지만,
앞은 상수(`patchplan.py:44`)이고 뒤는 `rig_paths` 로 덮어쓸 수 있다 — 덮어쓰면 갈린다.

### C7 — 쌍둥이 호출지 (판독)
`grep -n 'state_port, {"groups": groups_path, "fixtures": fixtures_path}'` → **:4735 와 :7737**.
:7737(`create_arrangement_groups`)은 바로 다음 줄에서 `fixtures_section = sections["fixtures"]`
를 꺼내 부분판독 **쓰기 거절**에 쓴다 — `@MX:ANCHOR`, SPEC-COPILOT-TRUNCATE-001
REQ-TRUNCATE-008 / AC-TRUNCATE-008, mutation-required.
**문면이 같고 의미가 반대다. 일괄 치환하면 안전장치가 날아간다.**

## 3. Baseline-attribution

모든 실행은 이 워크트리, `origin/main` **38e09b9** 위에서 났다.
`git status --short` 는 신규 검사 파일 하나만 보고했다(뮤테이션은 전부
`git checkout --` 로 되돌렸고, 프로브 2개는 지웠다).

## 4. 뮤테이션 — 4/4 예고대로

| # | 심은 것 | 예고 | 실측 |
|---|---|---|---|
| ① | `:4735` 요청 집합에서 `fixtures` 제거 | 1절 2검사 죽음 | 🟢 2 failed (스파이 팔 + 관측 팔 둘 다) |
| ② | 분류 삼항 뒤집기 | 2절 2검사 죽음 | 🟢 3 failed (2절 2 + 3절 대조팔 1) |
| ③ | 섹션 사유를 페이로드에 실음 | 3절 특성화 죽음 | 🟢 1 failed — `assert 'path_not_resolved' is None` |
| ④ | `read_existing_fids` 예외 포획 | 4절 특성화 죽음 | 🟢 1 failed — `DID NOT RAISE LookupError` |

②가 3절 대조팔까지 죽인 것은 설계대로다 — 그 팔이 같은 분류를 단언한다.

## 5. 카드 물음에 대한 답

### (a) `groups` 단독에서 `console_unreachable` 이 맞는 사유인가

**수집기 층에서는 맞다.** 형제가 없으면 「이 경로가 틀렸다」와 「콘솔이 죽었다」를
가를 신호가 원리적으로 없고, 그때 경로를 탓하면 사람이 시트를 고치러 가서 안 낫는다.

**그러나 이 도구에서는 물음이 성립하지 않는다.** C4·C5 가 실측으로 답한다 —
두 사유 다 페이로드에 안 실리고, `console_unreachable` 은 그 앞에서 도구가 죽어
**낼 수 있는 경로 자체가 없다**. 지금 상태에서 요청 집합을 줄이는 것은
**관측 가능한 변화를 0건 만든다.**

⚠️ 그것이 「그러니 줄여도 된다」는 뜻은 아니다. C4·C5 는 둘 다 **고쳐야 할 결함**이고,
고쳐지는 순간 요청 집합 축소는 fail-open 변경이 된다. 그래서 1절 검사를 먼저 세웠다.

### (b) 요청 집합 축소 말고 다른 길

| 안 | 절감(실측) | 분류 축 영향 | 평 |
|---|---|---|---|
| A. 요청 집합을 `groups` 단독으로 | 7→2 (5회) | 🔴 바뀐다 | 가장 싸지만 낭비 제거와 오류 분류 변경을 한 커밋에 묶는다 |
| **B. 소비 안 하는 섹션은 페이징 생략**(카드 제안) | 7→3 (4회) | 🟢 없음 | **권고** — 형제 신호를 그대로 두고 낭비의 80%를 없앤다 |
| C. `read_existing_fids` 의 읽기를 재사용 | 7→2 | 🟢 없음 | 경로 결합이 는다(C6 의 상수 vs 설정 갈림) |

**권고: B.** 근거는 절감이 아니라 **분류 축을 안 건드린다**는 것이다. A 는 오늘은
무해하지만(C4·C5) 그 무해함이 결함에 기대고 있어, C4·C5 를 고치는 사람이
A 를 되돌려야 한다.

### (c) 검사를 먼저 세워야 하나

**그렇다 — 실측으로 확정됐다.** 뮤테이션 ① 아래에서 **10,505개 검사가 전부 초록**이었다.
「검사가 없으니 깨끗」이 아니라 「검사가 없으니 조용히 바뀐다」가 맞다.
이 카드에서 리드가 조건을 반대로 썼다가 정정한 지점이 바로 여기이고, 그 정정이 옳았다.

## 6. Gaps — 안 잰 것

- **실기 0건.** 콘솔 불필요 카드라 가짜 콘솔로만 쟀다. 실기에서 `read_existing_fids`
  가 어떤 형태로 실패하는지(예외인지 `ok=False` 인지)는 `console.py:670` **독스트링을
  읽은 것**이지 실기 관측이 아니다.
- **C5 의 폭발 반경 미측.** 예외가 웹 층에서 어떻게 보이는지(500 인지, 사용자에게
  뭐라 보이는지) 안 쟀다. 「도구가 거절을 못 낸다」까지만 확정.
- **C4 를 다른 도구로 넓히지 않았다.** `collect_rig_sections` 소비자는 9자리인데
  그중 사유를 실제로 사용자에게 전하는 자리가 몇인지 전수 안 했다.
- **B 안의 구현 형태 미설계.** 절감치 7→3 은 현재 코드에서 산술로 뺀 값이지
  구현해서 잰 값이 아니다.
- **`rig_paths["fixtures"]` 덮어쓰기를 실제로 안 해 봤다.** C6 의 갈림 위험은
  두 상수를 읽어 비교한 것이지 실행으로 갈라 본 것이 아니다.

## 7. Residual-risk

- 3절·4절은 **특성화**다 — 현재 결함 상태를 고정한다. 고치는 사람이 이 검사를
  「지켜야 할 계약」으로 오독하면 결함이 굳는다. 그래서 각 클래스 독스트링과
  실패 메시지에 「t152 를 다시 열어라」를 박아 뒀다.
- 1절 (a)는 `monkeypatch` 로 모듈 전역을 가로챈다. 수집기를 함수 안으로 인라인하면
  이 팔은 조용히 공허해진다 — 그래서 (b) 관측 팔을 함께 뒀다. 둘 다 죽으면
  검사가 아니라 검사 대상이 사라진 것이다.
- `_LIVE_WINDOW = 19` 는 t151 의 실기 실측에서 왔다. 응답기가 바뀌어 창이 커지면
  절단이 안 나 1절 (b)가 공허해진다 — 그 자리에 이유를 주석으로 남겼다.

## 8. 리드에게 넘기는 것

낭비 제거(B 안)는 **결정이 안전장치에 닿는다**:

1. `collect_rig_sections` 는 소비자가 9자리다. 페이징 생략 옵션은 그 전부에 노출된다.
2. 그중 :7737 은 `@MX:ANCHOR` 부분판독 **쓰기 거절**이고 mutation-required 로 표시돼 있다.
3. C4·C5 는 별도 결함이라 별도 카드가 맞다고 본다 — 이 카드에서 고치면
   「판정 카드」가 세 결함의 수리 카드가 된다.

그래서 이 카드는 **검사 + 판정까지**만 닫고, 수리는 배차 따로를 권한다.
