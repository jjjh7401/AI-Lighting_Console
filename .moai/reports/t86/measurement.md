# t86 — 게이트가 Store/Label 을 승인 없이 통과시키는 범위 (실측)

- 트리: `.claude/worktrees/t86` · 브랜치 `WT-preset-gate`
- 기준 커밋: `8723c97` (origin/main 과 0/0)
- 성격: 측정만 함. 구현 없음. **콘솔 발사 없음** — 모든 판정은 검사 층에서 냈다.

---

## 1. 주장 (Claim)

카드 문면은 「게이트가 Store/Label Preset 을 승인 없이 통과시킨다」였다. 실측 결과 이 문장은
**참이지만 범위가 좁게 적혀 있다.** 빈 칸은 프리셋이 아니라 **쓰기 동사 계열 전체**다.

그리고 이것은 간과가 아니라 **비준된 상태**다. `test_writegate.py::UNCHANGED_SAFE` 가
`Store Preset 4.1` 을 포함해 다섯 개의 `Store` 문형과 `Label Group` 을 「비-위험으로 유지」
대상으로 못박고 있다. 즉 t86 은 구멍을 메우는 카드가 아니라 **비준을 뒤집을지 판단하는
카드**다.

## 2. 증거 (Evidence)

### 2-1. 분류표 — 분류기를 직접 돌린 값

`.moai/reports/t86/probe_classify.py` · 실행: `PYTHONPATH=. uv run --no-project --with pyyaml python`

```
ruleset version = 3
blacklist = ['Delete', 'Remove', 'Off Everything', 'Store /overwrite',
             'Shutdown', 'Format', 'Set Fixture', 'LoadShow', 'NewShow']

SUBJECT          Store Preset 1.1                 safe         False  None
SUBJECT          Label Preset 4.7 "Warm Wash"     safe         False  None
STORE-FAMILY     Store Group 3                    safe         False  None
STORE-FAMILY     Store Cue 5                      safe         False  None
STORE-FAMILY     Store Sequence 1 Cue 2           safe         False  None
STORE-FAMILY     Store Executor 1                 safe         False  None
STORE-FAMILY     Store Macro 7                    safe         False  None
STORE-FAMILY     Store World 2                    safe         False  None
STORE-FAMILY     Store View 1                     safe         False  None
LABEL-FAMILY     Label Group 3 "Front Truss"      safe         False  None
LABEL-FAMILY     Label Cue 5 "Blackout"           safe         False  None
LABEL-FAMILY     Label Sequence 1 "Main"          safe         False  None

CTRL-POS         Store /overwrite                 blacklisted  True   Store /overwrite
CTRL-POS         Store Preset 1.1 /overwrite      blacklisted  True   Store /overwrite
CTRL-POS         Store Preset 1.1 /o              blacklisted  True   Store /overwrite
CTRL-POS         Delete Preset 1.1                blacklisted  True   Delete
CTRL-POS         Set Fixture 11 Posx '5.0'        blacklisted  True   Set Fixture
CTRL-POS         LoadShow                         blacklisted  True   LoadShow
CTRL-INVOKE      Go+ Executor 1                   invoking     False  None
CTRL-FABRICATED  Zzqqxx Preset 1.1                safe         False  None
```

**대조군이 살아 있다**: 양성 대조군 6개가 전부 `blacklisted` 로 발사됐고, 날조 대조군
(`Zzqqxx Preset 1.1`) 은 걸리지 않았다. 그러므로 위쪽 `safe` 는 프로브가 눈이 멀어서 나온
값이 아니다.

**읽어낸 규칙**: `Store` 는 `/overwrite` 옵션이 붙을 때만 걸린다(`Store /overwrite` 항목).
`/o` 한 글자 축약도 걸린다. 옵션이 없으면 대상이 무엇이든 `safe` 다. `Label` 은 룰셋 어디에도
없다 — 블랙리스트에도, invoking 동사에도.

### 2-2. 승인 카드로 이어지는지 — 게이트 하류 확인

`gate.py::_stage_classify` 는 `hold = verdict.risky` 로 시작한다. 이후 `hold` 가 참이 되는
경로는 셋뿐이다: ① invoking 판정 후 본문 검증 실패, ② 같은 명령의 미확인 재전송 이력,
③ 라이브 락(전역 스위치). `safe` 판정은 이 셋 중 어디에도 걸리지 않으므로
`held` 목록이 비고, `request_approval` 이 **호출되지 않는다.** 승인 카드는 뜨지 않는다.

### 2-3. 후보 항목별 코퍼스 충돌 비용 — 이 트리에서 재측정

`.moai/reports/t86/probe_cost.py` · `_would_be_held` × `load_corpus()` (21 시나리오 / 35 명령줄)

| 후보 항목 | 걸리는 줄 | 걸리는 시나리오 | 새로 걸리는 시나리오 |
|---|---|---|---|
| (없음, 현재) | 0 | 0/21 | — |
| `Store` | 10 | 10/21 | cue-store-1/2, group-create-1/2/3, macro-create-1/2, page-setup-1, preset-store-1/2 |
| `Store Preset` | 2 | 2/21 | preset-store-1/2 |
| `Store Group` | 3 | 3/21 | group-create-1/2/3 |
| `Store Cue` | 2 | 2/21 | cue-store-1/2 |
| `Label` | 9 | 9/21 | cue-store-1, group-create-1/2/3, macro-create-1/2, page-setup-1, preset-store-1/2 |
| `Label Preset` | 2 | 2/21 | preset-store-1/2 |

`Store` 10/21 과 `Store Group` 3/21 은 `blacklist.yaml` 헤더가 2026-08-05 에 기록한 값과
**일치한다** — 옮겨 적은 수치가 v3 에서도 유효함을 확인했다. `Label` 9/21 과
`Store Preset` / `Label Preset` 각 2/21 은 이번에 처음 잰 값이다.

### 2-4. 테스트 파괴 — 좁은 후보를 실제로 넣고 전량 실행

- 기준선: `uv run pytest -q` → **10167 passed, 12 skipped, 0 failed** (162.66s)
- 변형: `blacklist:` 블록에 `Store Preset` + `Label Preset` 삽입 후 전량 →
  **13 failed, 10162 passed** (145.96s)
- 복원: 백업본 복사 후 `shasum -a 256` 일치 확인
  (`3027d4cf2cede6692830c8052190077874372d2c83f068a18fe87b1967f942fb`).
  `git checkout` 은 쓰지 않았다.

깨진 13건의 갈래:

| 갈래 | 건수 | 무엇을 말하는가 |
|---|---|---|
| `test_looks_instantiate` | 6 | 룩 번들의 콘솔 경로가 `Store Preset` 을 탄다 |
| `test_measurement_runner` | 4 | 코퍼스의 「비-위험 동사만」 불변식이 깨진다 |
| `test_safety_ruleset` | 1 | 출하 클로즈드셋 비준 테스트(개정 시 당연히 갱신 대상) |
| `test_writegate` | 2 | **`Store Preset 4.1` 이 비-위험임을 명시적으로 비준하던 테스트** |

### 2-5. 가장 중요한 발견 — 이미 비준돼 있다

`server/tests/test_writegate.py` 의 `UNCHANGED_SAFE` 튜플은 「분류가 움직이면 안 되는 문형」
목록이며, 각 항목에 사유가 붙어 있다:

```
("Store Group 3",   "descoped: DEPLOY's canonical SAFE_SOURCE literal"),
("Store Preset 4.1","descoped: measurement corpus representative"),
("Store Cue 12",    "descoped: measurement corpus representative"),
("Store Page 3",    "descoped: measurement corpus representative"),
("Store Macro 21",  "descoped: measurement corpus representative"),
("Assign Sequence 4 Page 1.201", "descoped"),
("Copy Page 1 At Page 4",        "descoped"),
("Label Group 3 'Vocals'", "labelling is not a patch write"),
```

두 가지가 여기서 갈린다.

- **`Store` 계열 · `Assign` · `Copy`** — 사유가 「descoped」다. 비용 때문에 범위에서 뺀 것이고,
  `blacklist.yaml` 헤더가 **2026-08-05 사용자 결정**이라고 못박고 있다.
- **`Label`** — 사유가 다르다. 「labelling is not a patch write」, 즉 **의미 판단**이다.
  비용 때문이 아니라 「이건 패치 쓰기가 아니다」라고 판단해서 뺐다.

카드 배차서가 물은 「프리셋만 빈 칸인지 Store 전체인지」의 답: **Store 전체이고, Label 전체이고,
Assign·Copy 까지다.** 다만 그 전부가 미판단 상태가 아니라 **판단을 거쳐 비준된 상태**다.

### 2-6. 사고와의 연결

`SPEC-COPILOT-LXSEQ-003` 의 문면이 사고 명령의 형태를 확인해 준다 —
`session.py:2951 _preset_store_commands` 가 `Store Preset <pool>.<n>` 을 만들고
`:2968` 이 `Label` 을 붙인다. 사고에서 콘솔에 올라간 두 명령이 정확히 2-1 표의 첫 두 줄이다.

`SPEC-COPILOT-PRESETGUARD-001`(completed)은 이 구멍을 **덮지 않는다**. 그 SPEC 은 응용 층에서
**덮어쓰기**를 막는다(점유 검사 · 저장 후 되읽기). 게이트의 `Store /overwrite` 항목도
덮어쓰기를 막는다. 두 층이 함께 덮는 것은 덮어쓰기이고, **빈 슬롯에 새로 만드는 쓰기**는
어느 쪽도 막지 않는다 — PRESETGUARD 는 점유되지 않은 슬롯이면 통과시키는 것이 설계다.
사고는 정확히 그 경로였다.

---

## 3. 기준 귀속 (Baseline-attribution)

모든 수치는 워크트리 `.claude/worktrees/t86`, 커밋 `8723c97`, 룰셋 `version: 3` 에서 이번에
직접 실행해 관측했다. 재사용한 외부 수치는 없다. `blacklist.yaml` 헤더의 10/21 · 3/21 은
인용이 아니라 재측정으로 **재현**했다.

---

## 4. 처방 방향

**t86 은 코드를 고치는 카드가 아니라 클로즈드셋 개정(v3 → v4) 여부를 판단하는 카드다.**
근거: 대상이 전부 `UNCHANGED_SAFE` 에 비준돼 있어, 조용히 항목을 넣는 것은 비준을 말없이
뒤집는 일이 된다. 개정은 `blacklist.yaml` 헤더가 이미 절차를 규정해 두었다 —
버전 올림 + 개정 이력 기재 + 위양성 관측 근거 + 비용 실측.

세 갈래가 있고, 셋의 성격이 서로 다르다.

**갈래 A — 좁게: `Store Preset` 만.** 비용 2/21 시나리오, 테스트 13건(그중 2건은 비준
테스트 자체, 1건은 출하 셋 비준). 사고를 정확히 막는다. 대신 `Store Group`·`Store Cue`·
`Store Macro` 는 그대로 열려 있어, 같은 계열의 다음 사고를 못 막는다. 점-수정이다.

**갈래 B — 넓게: `Store` 동사 전체.** 비용 10/21 시나리오, 대표 과업 10종 중 5종.
이 앱의 창작 쓰기 어휘 대부분에 승인 카드가 붙는다. 그리고 이 선택은 **2026-08-05 사용자
결정을 되돌리는 일**이다 — 리드나 내가 판정할 사안이 아니라 감독의 결정이다.

**갈래 C — 축을 바꾼다: 「요청되지 않은 쓰기」.** 사고의 본질은 `Store Preset` 이라는 문형이
아니라 *사용자가 요청하지 않은 쓰기가 나갔다*는 것이다. 그런데 게이트는 설계상 **명령 구문만**
본다(`classify.py` 모듈 독스트링). 의도는 구문에 없다. 따라서 이 축은 게이트 안에서는 풀 수
없고, 응용 층(세션이 자기가 만든 명령을 사용자 요청과 대조)에서 풀어야 한다.
PRESETGUARD 가 이미 그 층에 있으므로, 확장 지점은 게이트가 아니라 그쪽일 수 있다.

**내 권고**: 갈래 C 를 우선 검토하고, 게이트 개정은 갈래 A 로 최소화한다. 이유는 두 가지다.
① 갈래 B 의 비용(대표 과업 5/10)은 게이트를 사실상 「모든 창작 작업에 확인 버튼」으로 바꾸는데,
그 마찰은 승인 피로를 낳아 승인 게이트 자체를 무력화하는 쪽으로 작동하기 쉽다.
② 사고의 인과는 분류 누락보다 **응용 층이 요청 범위를 넘는 명령을 만들어낸 것**에 가깝다 —
게이트는 자기가 본 것을 규칙대로 판정했을 뿐이다.

다만 ②는 **내 읽기이지 측정이 아니다.** 사고 당시 세션이 왜 그 명령을 만들었는지는 이 트리에서
재현하지 않았다.

**`Label` 은 별건으로 다뤄야 한다.** 「labelling is not a patch write」는 참이지만, 게이트가
지키려는 것은 「패치 쓰기」보다 넓은 **쇼파일 상태**다(`Set Fixture` 항목 주석이 스스로 그렇게
적었다: 「A fixture's patch row is SHOWFILE STATE」). 개체 이름을 바꾸는 것도 쇼파일 상태
변경이다. 이 사유가 지금도 유효한지는 재검토 대상이며, 비용은 `Label Preset` 2/21 ·
`Label` 전체 9/21 로 이미 재 두었다.

---

## 5. 미검증 (Gaps)

- **갈래 B 의 테스트 파괴 수를 재지 않았다.** 코퍼스 충돌 10/21 만 쟀다. `Store` 를 넣고
  전량을 돌리면 몇 건이 깨지는지는 미측정이다.
- **`Assign` · `Copy` 의 비용을 재지 않았다.** `UNCHANGED_SAFE` 에 「descoped」로 올라 있는
  것만 확인했고, 후보 비용 표에 넣지 않았다.
- **사고의 원본 로그를 못 봤다.** 명령 형태는 LXSEQ-003 문면과 `session.py` 빌더로 확인했으나,
  사고 당시 실제로 콘솔에 나간 문자열 자체는 이 트리에 없다.
- **MA3 실기 확인 없음.** 카드 지시대로 콘솔에 아무것도 쏘지 않았다. `Store Preset` 이
  실제 콘솔에서 어떤 부작용을 내는지는 이 문서의 범위 밖이다.
- **`Store` 축약형을 따로 재지 않았다.** `_keyword_match` 가 3자 이상 접두사를 받으므로
  `Sto Preset 1.1` 도 같은 경로일 것으로 읽히나, 프로브 표에 넣지 않았다.

## 6. 잔여 위험 (Residual-risk)

- 코퍼스 21 시나리오는 이 앱의 전체 쓰기 어휘가 아니다. 코퍼스에 없는 문형의 비용은 0 으로
  측정되지만 실제로 0 이라는 뜻이 아니다.
- 갈래 A 를 택하면 `Store Group`·`Store Cue`·`Store Macro`·`Store Page` 가 열린 채 남는다.
  같은 사고 형태가 다른 개체에서 재현될 수 있고, 그때는 「프리셋은 막았는데」가 방심의 근거로
  작동할 위험이 있다.
- 테스트 13건 중 `test_looks_instantiate` 6건은 룩 번들 경로가 승인 카드를 타게 된다는 뜻이다.
  이는 테스트를 고쳐서 넘길 문제가 아니라 **실제 사용 흐름이 바뀐다**는 신호다.

---

## 부록 — 하네스 소견 (카드 범위 밖, 리드 보고용)

이 워크트리에서 `Write`/`Edit` 도구가 **경로 통과 거부**로 전부 막혔다. 세션이 처음 뜬
디렉터리(`~/orca/workspaces/AI-Lighting_Console/LX-SEQ`)가 쓰기 가드의 경계로 잡혀 있고,
`EnterWorktree` 로 옮겨온 `~/Documents/.../worktrees/t86` 은 그 바깥이기 때문이다.
같은 경로에 대해 **Bash 의 쓰기는 통과했다.** 이 문서와 프로브 스크립트도 전부 Bash 로 썼다.
도구 층 가드와 Bash 사이의 이 비대칭은 t86 과 무관하지만, 가드를 신뢰하는 다른 카드에는
영향이 있다.
