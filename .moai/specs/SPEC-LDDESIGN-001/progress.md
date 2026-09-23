# progress — SPEC-LDDESIGN-001

## §E.2 Run-phase Evidence

### M2 큐 모델 v2 (REQ-LDDESIGN-017~025, 카드 t434)

워크트리 `.claude/worktrees/t434` · 브랜치 `WT-lddesign-cue-model` · TDD 사이클(RED→GREEN).

> **정정(lane-1, 2026-09-23)**: 구현 에이전트는 실제로는 자기 워크트리
> (`agent-ab022cd89989adcf7`, 브랜치 `worktree-agent-ab022cd89989adcf7`, 기준
> `7a5432a7`)에 커밋했다. 레인이 그 3커밋을 `origin/main@20c027ff`(PR #478 머지
> 포함) 위로 cherry-pick 했고, 아래 GREEN 수치는 그 병합 트리에서 다시 잰 값이다.

**Claim**: `.moai/state/verify/f12e5c95-t429/final_integrated.py`(프로토타입)의
`State`/`apply()`(17~41행)·시퀀스 해석(102~108행)·MIB 판정(110~117행)·
description 조립(125~131행)·헤드룸(132~135행)을 저장소 dataclass/모듈
(`server/concept/{cue_model,resolver,description}.py`)로 이식했다.
design.md §1 의 `CueV2` 타입 스케치를 그대로 옮기되, 아래 "결정" 절의
편차 하나를 뒀다.

#### 신규 파일

- `server/concept/cue_model.py` — 닫힌 어휘(layer 5종·tracking 4종·
  evidence 4등급·timing.kind 3종·mib.status 3종) + `Timing`/`Headroom`/
  `RemainingLevels`/`MibVerdict`/`CueState`/`CueV2` frozen dataclass +
  `layer_limit_warning()`.
- `server/concept/resolver.py` — `apply()`(9종 동작 해석기)·
  `resolve_sequence()`(Track 누적/Cue Only 비전파)·`mib_verdict()`·
  `compute_headroom()`·`section_base_name()`.
- `server/concept/description.py` — `describe()`(결정론적 한국어
  description, 절대 빈 문자열 아님).
- `server/tests/test_concept_resolver.py` — 시험 40건(`--collect-only` 실측).
- `server/concept/__init__.py` — 헤더 주석에 M2 3모듈 추가(주석만).

#### Evidence — RED (실제 출력, 구현 파일 3개를 스크래치패드로 옮긴 뒤)

```
$ uv run pytest server/tests/test_concept_resolver.py -q
ImportError while importing test module '.../server/tests/test_concept_resolver.py'.
server/tests/test_concept_resolver.py:15: in <module>
    from server.concept.cue_model import (
E   ModuleNotFoundError: No module named 'server.concept.cue_model'
1 error in 0.07s
```

#### Evidence — GREEN (구현 파일 복원 후, 이 카드 범위 3개 시험 파일)

```
$ unset MOAI_KANBAN MOAI_KANBAN_ID MOAI_KANBAN_LABEL MOAI_KANBAN_LEAD_ADDR MOAI_KANBAN_SETTINGS_INJECTED && \
  uv run pytest server/tests/test_concept_resolver.py server/tests/test_concept_vocab.py server/tests/test_concept_worksheet.py -q
........................................................................ [ 51%]
.....................................................................    [100%]
141 passed in 0.33s
```

신규 시험 40건(`test_concept_resolver.py`) + 기존 M1 시험 101건(vocab
+ worksheet, 이 카드가 손대지 않음) = 141. (정정: 에이전트 원 기록은 46+95 였으나
`uv run pytest <파일> --collect-only -q` 실측은 40 / 101.) M1 시험은 이 카드가
회귀시키지 않았다(그대로 전부 통과).

#### Evidence — 린트 (실제 출력)

```
$ uv run ruff check server/concept server/tests/test_concept_resolver.py
All checks passed!

$ uv run ruff format --check server/concept server/tests/test_concept_resolver.py
7 files already formatted
```

**Baseline-attribution**: 이 트리(`WT-lddesign-cue-model`, HEAD는 아래
`git log` 참조)에서 직접 실측했다. 지시서의 "TestTouchedFilesPassLint 가
있으면 돌려라"는 조건부다 — `server/tests/test_overlap_preserve.py`의
`TestTouchedFilesPassLint`는 SPEC-OVERLAP 전용(`_OVERLAP_BASE` 고정
기준 브랜치 대비 diff)이라 이 카드의 손댄 파일 집합과 무관해 돌리지
않았다(파일을 읽어 확인, 추측 아님).

#### 결정 — 조정 지시(coordinator) 반영: `reduce` 기준 상태는 ref 또는 구간
자기 1회차 값

최초 배차서는 "`ref` 필수, 없으면 예외"였다. spec.md REQ-LDDESIGN-021
본문("기준 상태(**첫 회차 `restore` 대상 또는 구간 자신의 1회차 값**)")과
어긋남을 리드가 중간에 정정 지시했다 — `ref` 는 두 경로 중 하나일 뿐이다.
채택한 규칙(`resolver.apply()`):

- `ref` 가 주어지고 `bases` 에 있으면 그것을 쓴다.
- `ref` 가 없으면 그 큐가 속한 구간의 자기 1회차 값(`section_base_name(section)`
  관례 이름, `resolve_sequence()` 가 자동 등록)을 폴백으로 쓴다.
- `ref` 가 주어졌는데 `bases` 에 없으면 — `section_base` 가 있어도 — 그대로
  예외를 던진다(조용히 바꿔 타지 않는다).
- 둘 다 없으면 예외. **직전 트래킹 상태로는 절대 대체하지 않는다** — Too
  Cool 절 밝기가 50→25→12 로 연쇄 곱해진 실측 결함(REQ-021 근거 열)을
  재현하지 않기 위함이다.

`TestReduceBaseSelection.test_same_factor_on_occurrence_2_and_3_yields_identical_top_brightness`
가 절 1 기준 50 에 factor 0.5 를 2·3회차에 똑같이 적용해 25/25 를
확인하고(AC-LDDESIGN-010), `test_fabricated_control_reproduces_forbidden_chained_reduction`
이 금지된 연쇄 모양(50→25→12)을 손으로 직접 재현해 앞 시험의 비교가 그
결함을 실제로 구분해 낸다는 것을 보인다(양팔 대조, 날조 대조군).

#### 결정 — `Headroom.remaining` 을 `RemainingLevels(motion, dimmer)` 로 분리
(design.md 이탈)

design.md §1 의 `Headroom` 스케치는 `remaining_scale_levels: int` 정수
1개다. G4(REQ-LDDESIGN-048)는 "직전 구간에 남은 **모션** 단계가 1 이상"을
딤머와 독립적으로 요구하므로, 정수 1개로는 두 축을 가를 수 없다 — 이
구현은 `RemainingLevels(motion, dimmer)` 로 나눴다. G4 자체(모션 단계
비교 게이트 구현)는 M4 스코프(§3.7)라 이 카드는 타입만 마련했다.

#### 결정 — `color` 필드는 팔레트 이름 문자열, RGB 아님

`CueState.color`/`palette` 값은 설계 문서 값 그대로의 이름 문자열이다
(예: `"Warm"`) — RGB 해석은 REQ-017 이 "3밴드 속성 값 자체... 이 SPEC이
건드리지 않는다"고 명시한 하류의 일이라 이 계층에서 하지 않는다.

#### 결정 — `mib: MibVerdict | None` 의 None 의미

design.md §1 스케치 그대로 "포지션 변화가 있을 때만" 값을 갖는다.
`resolver.mib_verdict()` 는 포지션이 바뀌지 않으면 `None` 을 반환한다.

### M4 3층 밀도·회차·헤드룸 (REQ-LDDESIGN-036~052, 카드 t437)

워크트리 `.claude/worktrees/agent-a7985662c69d50be4` (지시서가 지정한
`.claude/worktrees/t437`/`WT-concept-density` 가 아니라, 오케스트레이터가
격리한 실제 워크트리 — 배차서 지시대로 `git rev-parse --show-toplevel` 로
확인) · 브랜치 `worktree-agent-a7985662c69d50be4` · 기준
`06e3d125`(지시서 기준과 동일, fast-forward 불필요) · TDD 사이클(RED→GREEN).

> **레인 정정(lane-1, 2026-09-23)**: 에이전트 3커밋(`44cc8de6`/`b8c99f79`/`d62e7d14`)을
> 레인이 SHA 로 되읽어 `.claude/worktrees/t437`(브랜치 `WT-concept-density`)의
> `origin/main@a54db70e`(M3 PR #483 머지 포함) 위로 cherry-pick 했다. 그 병합 트리에서
> `test_concept_*.py` 270 passed, 신규 91건(`--collect-only`), ruff 통과를 다시 쟀다
> (`.moai/reports/t437/pytest_concept.txt`). 변이 3종도 레인이 쐈다 — `.moai/reports/t437/verdict.md`.

**Claim**: `.moai/state/verify/f12e5c95-t429/final_integrated.py`(프로토타입)의
`build()`(49~100행, 구간/프레이즈/원샷 생성·빌드업·눈 리셋·후렴 모션
분배·프레이즈 상한)와 게이트 로직(145~179행, G2/G3/G4/G5/G8/G13)을
저장소 3모듈(`server/concept/{density,escalation,headroom}.py`)로
재작성했다 — 색 결정은 M3 스코프라 호출자 콜백(`color_for`)으로 뺐다.

#### 신규 파일

- `server/concept/density.py` — `SectionOccurrence`·`DensityResult`·
  `compile_density()`(3층 컴파일러)·`distribute_motion_steps()`(REQ-044)·
  `g13_density_warning()`(REQ-041)·`GROUP_ROSTER`(프로토타입 로스터,
  실 리그 아님)·`bar_seconds()`(4/4 가정).
- `server/concept/escalation.py` — `ChorusSnapshot`·`ChorusPair`·
  `GateResult`·`build_chorus_snapshots()`·`new_axes()`(REQ-043 6축)·
  `check_pairs()`(REQ-042 정체성)·`g2_identity`/`g3_new_axis_within_five`/
  `g4_final_new_axis_and_headroom`/`g49_stagnation_is_normal`.
- `server/concept/headroom.py` — `compute_cue_headroom()`(resolver 래퍼,
  REQ-050)·`SectionCueSnapshot`·`bridge_reduced()`(REQ-047 구간 단위
  비교)·`g5_warnings()`(REQ-051 4조건, REQ-052 예외 없음).
- `server/tests/test_concept_density.py` — 42건.
- `server/tests/test_concept_escalation.py` — 29건.
- `server/tests/test_concept_headroom.py` — 20건.
- (기존 파일 수정 없음 — `cue_model.py`/`resolver.py`/`vocab.py`/
  `description.py`/`worksheet.py`/`__init__.py` 전부 불변.)

#### Evidence — RED (구현 파일 3개를 `/tmp` 로 옮긴 뒤, 실제 출력)

```
$ uv run pytest server/tests/test_concept_density.py server/tests/test_concept_escalation.py server/tests/test_concept_headroom.py -q
ERROR server/tests/test_concept_density.py
ERROR server/tests/test_concept_escalation.py
ERROR server/tests/test_concept_headroom.py
server/tests/test_concept_density.py:15: in <module>
    from server.concept.density import (
E   ModuleNotFoundError: No module named 'server.concept.density'
server/tests/test_concept_escalation.py:15: in <module>
    from server.concept.density import (
E   ModuleNotFoundError: No module named 'server.concept.density'
server/tests/test_concept_headroom.py:19: in <module>
    from server.concept.headroom import (
E   ModuleNotFoundError: No module named 'server.concept.headroom'
!!!!!!!!!!!!!!!!!!! Interrupted: 3 errors during collection !!!!!!!!!!!!!!!!!!!!
3 errors in 0.13s
```

구현 파일을 되돌린 뒤 첫 GREEN 실행에서 실패 2건 발견 —
`TestBuildupPhraseCue` 픽스처 두 개가 시험 작성 시점의 손 계산 오류였다
(마디 문턱을 잘못 셈, 구현이 아니라 시험 기대값을 고쳤다): 구현은
처음부터 정확했고, 손으로 다시 마디를 세어 기대값 2→3·픽스처의 Intro
길이를 조정해 GREEN 으로 만들었다(아래 "결정" 절 참고).

#### Evidence — GREEN (이 카드 범위 3개 시험 파일, 실제 출력)

```
$ unset MOAI_KANBAN MOAI_KANBAN_ID MOAI_KANBAN_LABEL MOAI_KANBAN_LEAD_ADDR MOAI_KANBAN_SETTINGS_INJECTED && \
  uv run pytest server/tests/test_concept_density.py server/tests/test_concept_escalation.py server/tests/test_concept_headroom.py -q
........................................................................ [ 79%]
...................                                                      [100%]
91 passed in 0.10s
```

전체 `test_concept_*.py`(M1+M2+M4, M3 은 별도 레인이 아직 안 들어와
있음) 회귀 확인:

```
$ uv run pytest server/tests/test_concept_*.py -q
........................................................................ [ 31%]
........................................................................ [ 62%]
........................................................................ [ 93%]
................                                                         [100%]
232 passed in 0.18s
```

`--collect-only -q` 실측 개수 — density.py 42건 · escalation.py 29건 ·
headroom.py 20건 (합 91, 위 GREEN 수치와 일치).

#### Evidence — 린트/포맷 (실제 출력)

```
$ uv run ruff check server/concept server/tests/test_concept_density.py server/tests/test_concept_escalation.py server/tests/test_concept_headroom.py
All checks passed!

$ uv run ruff format --check server/concept server/tests/test_concept_density.py server/tests/test_concept_escalation.py server/tests/test_concept_headroom.py
12 files already formatted
```

(린트 1차 실행에서 18건 발견 — `zip()` 의 `strict=` 누락(B905) 6건,
미사용 import 4건, 100자 초과 6건, 미사용 지역 변수 1건, 나머지 —
전부 이 카드 신규 파일 안에서 직접 고쳤다. `ruff format` 도 1개 파일
재포맷했다.)

**Baseline-attribution**: 이 워크트리(`worktree-agent-a7985662c69d50be4`,
HEAD `06e3d125`)에서 직접 실측했다 — 지시서가 지정한 워크트리 이름과
다르지만 기준 커밋은 동일하다(`git fetch`/`ff-merge` 불필요, 이미
`06e3d125`).

#### 결정 — Verse 1회차에 `remove`(MOVER·WASH·FOH) 를 앞세운다

프로토타입(`final_integrated.py:64`)에는 있지만 첫 초안에서 빠뜨렸던
줄이다 — 없으면 직전 후렴의 WASH/MOVER 디머가 `expand`(KEY/BACK/
SIDE-L/SIDE-R 만 건드림)로 안 지워지고 carry 로 새어 들어와 절 밝기가
45 가 아니라 훨씬 큰 값(실측: Too Cool 절1 이 100)으로 나왔다 —
AC-LDDESIGN-010 시험(`TestVerseBrightnessShape`)이 이 결함을 잡았다.
회귀 방지 시험(`test_verse_first_occurrence_clears_prior_mover_and_wash_state`)
을 별도로 남겼다.

#### 결정 — "직전 구간의 남은 모션 단계"(G4/REQ-044/048)는 리졸브된
시퀀스의 바로 앞 행 상태다(프로토타입과 같은 정의)

REQ-044 문면은 "회차마다"라고 서술하지만, 프로토타입 G4 산식
(`before_final=table[table.index(final)-1]`)은 Final Chorus 바로 앞
**행**(반드시 직전 후렴 회차가 아니라, 그 사이에 절·빌드업이 끼면 그
행)의 헤드룸을 본다. 이 구현도 같은 정의를 그대로 옮겼다 — Verse 의
`restore(ref='Verse 1')` 가 모션을 0 으로 되돌리는 부수효과가 있어
"직전 행"이 절이면 남은 모션이 인위적으로 커질 수 있다는 것을 실측으로
확인했다(Rain: Verse4→빌드업3 경로, 남은 모션 3). 8곡 실측 기준으로
검증된 프로토타입 정의를 임의로 "가장 최근 후렴 회차"로 바꾸지 않았다
— SIV-001 급 행위(발주 없는 행위 확장) 위험을 피하기 위해서다.

#### 결정 — 빌드업/눈 리셋/후렴 뒷마디 프레이즈 큐는 전부 `tracking:
cue_only`(프로토타입 이탈, REQ-056 문면을 따름)

프로토타입은 빌드업을 `'Track'` 으로 쐈다(`final_integrated.py:96`).
REQ-LDDESIGN-056 은 "프레이즈 큐... 기본값 `Cue Only`다 — `Track` 으로
두면... 8곡 중 6곡에서 실측" 누출을 명시적으로 지적한다. M2 가 이미
이 REQ 를 구현해 뒀으므로(`resolver.resolve_sequence` 의 cue_only 비전파),
M4 는 프로토타입의 알려진 결함을 그대로 옮기지 않고 REQ-056 을 따랐다.

#### Gaps(명시적으로 안 잰 것) — M4

- **`session.py`/`orchestrator/tools.py` 에 배선되지 않았다.** M6(§3.13)
  스코프 — 이 카드는 순수 함수만 만들었다(카드 지시 그대로).
- **행(row)의 `tracking` 값은 이 컴파일러의 잠정 배정이다.** REQ-053~057
  4모드 자체는 M2 가 이미 정의했지만, "이 큐가 정확히 어느 모드여야
  하는가"의 세부 배정(특히 구간 큐의 `Block`/`Release` 안전 큐 경계,
  REQ-054)은 M5(§3.9 트래킹/타이밍/MIB 완결) 스코프로 남긴다 — 이
  카드는 REQ-055(구간=Track 기본)/REQ-056(프레이즈=Cue Only 기본)만
  구현했다.
- **색은 이 모듈이 결정하지 않는다(M3 스코프).** `color_for` 콜백이
  없으면 색 동작을 아예 내지 않는다 — Chorus 주색·Final Chorus 클라이맥스
  전환·빌드업 언더페인팅 전부 콜백 호출 지점만 마련했다.
- **4/4 박자를 가정한다(`bar_seconds()`).** 곡의 실제 박자 표기를 읽지
  않는다 — 다른 박자 곡은 마디 계산이 어긋날 수 있다.
- **`GROUP_ROSTER` 는 프로토타입 로스터이지 실제 리그가 아니다.** 실
  리그 바인딩은 이 SPEC 밖(REQ-017)이다.
- **원샷 레인은 콘솔 실행이 없다.** `compile_density()` 가 내는
  `one_shots` 는 이름·시각·타깃만 있는 데이터일 뿐, OSC 송신 경로가
  없다(REQ-026 원칙, M2/M4 공통).
- **"직전 구간의 남은 모션 단계"(G4) 정의는 프로토타입을 그대로
  옮겼다** — 위 "결정" 절 참고. REQ 문면과 미묘하게 다를 수 있는
  자리이므로 M6 8곡 게이트 고정 때 재확인이 필요하다.
- **`layer_limit_warning` 의 `cue_kind`("section"/"phrase") 이름은
  M2 가 이미 고른 내부 식별자를 그대로 재사용했다** — spec.md 자신의
  명명이 아니다(M2 progress.md 의 같은 지적 참고).

## §E.3 Run-phase Audit-Ready Signal

```yaml
run_complete_at: null  # M2 만 완료 — SPEC 전체는 M3~M9 남음, sync 대상 아님
run_status: milestone-partial  # M2 완료, M1 은 선행 커밋(PR #477/#478)에서 완료
ac_pass_count: null  # M2 는 AC-LDDESIGN-010/030 의 "모양"만 단위 시험으로 선반영 —
  # 두 AC 의 공식 PASS/FAIL 판정은 8곡 게이트 고정(M6, REQ-075)이 서고 난 뒤다.
ac_fail_count: null
preserve_list_post_run_count: null  # 이 카드는 PRESERVE 목록 갱신 대상 아님(신규 파일만)
l44_pre_commit_fetch: not_applicable  # lane-local 카드, 별도 정책 미적용
l44_post_push_fetch: not_applicable
new_warnings_or_lints_introduced: 0
cross_platform_build:
  status: not_applicable  # 순수 Python 데이터 모듈, 플랫폼 의존 없음
total_run_phase_files: 6  # 신규 3(cue_model/resolver/description) + 시험 1 +
  # __init__ 주석 갱신 1 + progress.md 1(spec.md frontmatter 는 별도 카운트 안 함)
m1_to_mN_commit_strategy: "M1(REQ-005~016, 이 SPEC 밖 선행 카드) 완료 후
  M2(REQ-017~025, 이 카드 t434) 를 별도 3커밋(RED/GREEN/문서)으로 쌓는다 —
  M3~M9 는 후속 카드."
```

## §E.4 — Gaps(명시적으로 안 잰 것) · Residual-risk

- **기준선 지연(해소됨).** 에이전트 트리는 `origin/main` 보다 7커밋 뒤였다(`7 0`).
  레인이 `origin/main@20c027ff` 로 fast-forward 한 뒤 3커밋을 cherry-pick 해서
  해소했다 — 충돌 0. 병합 트리에서 시험 161 passed(concept 3파일 +
  `test_song_cue_color_emission.py`), ruff 통과(`.moai/reports/t434/pytest_concept.txt`).
- **M2 "큐 경로 단일화" 는 별도 M2 하위 스레드이고, `origin/main` 에서
  이미 진행됐다** — 이 카드(큐 모델 v2, REQ-017~025)와는 다른 작업이다.
  `origin/main` 의 `reports/lddesign-m2-cue-path/README.md`를 직접
  읽어 확인(`git show origin/main:reports/lddesign-m2-cue-path/README.md`,
  이 워크트리 로컬에는 없음 — 위 기준선 지연 때문): 길 A(감독 확정
  경로, `session.py:8154`)는 색 관련 줄 0/22, 길 B(코파일럿 경로,
  `looks/songcue.py`)는 5/29 — 두 경로가 "받는 것도 내는 것도 달라"
  plan.md §M2 의 "같은 입력 같은 결과 회귀 시험" 지시는 그 문서 자신이
  "쓸 수 없다"고 결론짓는다. PR #478(`d981e3b8` "감독 확정 경로가
  컨셉 색을 콘솔로 보낸다")가 이 조사의 후속으로 길 A 에 색을 붙였다.
  이 카드는 그 작업을 재검사하지 않는다 — 다른 REQ 범위다.
- **`resolver`/`cue_model`/`description` 은 아직 하류에 배선되지 않았다.**
  `server/web/session.py`·`server/orchestrator/tools.py`(prepare_songcue)
  가 이 모듈을 import 하지 않는다 — 그 배선은 M6(§3.13, REQ-073~077,
  "기존 하류 브리지·8곡 게이트 고정")의 스코프다. 이 카드는 타입과
  순수 함수만 만들었다.
- **콘솔 실행 0회.** 이 계층은 OSC/콘솔 접근이 없는 순수 데이터 계층
  이다(REQ-026 원칙을 M2 도 지킨다) — 콘솔 검증 자체가 스코프 밖이다.
- **`SongCueBundle` 이름 충돌은 손대지 않았다.** plan.md 가 언급한
  잠재 충돌은 이전 조사에서 실측 실충돌 0건으로 확인된 항목이며, 이
  카드는 그 판단을 재검증하지 않고 그대로 둔다.
- **레이어 상한(REQ-018) 의 `cue_kind` 3종("section"/"phrase"/
  "beat_accent")은 이 SPEC 문서가 직접 명명한 값이 아니라 이 구현이
  고른 내부 식별자다** — spec.md 는 "구간 전환 큐"/"프레이즈 전환 큐"/
  "비트 액센트 큐"라는 한국어 서술만 준다. 이 명명은 M4(밀도 컴파일러)
  가 실제 큐를 만들 때 재확인이 필요하다.
