# progress — SPEC-LDDESIGN-001

## §E.2 Run-phase Evidence

### M2 큐 모델 v2 (REQ-LDDESIGN-017~025, 카드 t434)

워크트리 `.claude/worktrees/agent-ab022cd89989adcf7` · 브랜치
`WT-lddesign-cue-model` · TDD 사이클(RED→GREEN).

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
- `server/tests/test_concept_resolver.py` — 시험 46건(아래 집계).
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

신규 시험 46건(`test_concept_resolver.py`) + 기존 M1 시험 95건(vocab
54건 + worksheet 41건, 이 카드가 손대지 않음) = 141. M1 시험은 이 카드가
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

- 🔴 **이 워크트리의 기준선은 착수 시점에 `origin/main` 보다 7커밋
  뒤졌다.** 착수 중 `git fetch origin main && git rev-list --count
  --left-right origin/main...HEAD` → `7 0`(origin 이 7 앞섬, 이 트리의
  로컬 전용 커밋은 0 — diverge 아니라 순수 지연). `git diff --name-only
  HEAD origin/main`으로 겹치는 파일을 직접 대조: `server/concept/` 전체
  0건 겹침, 유일한 겹침은 `.moai/specs/SPEC-LDDESIGN-001/spec.md`이고
  그 diff(§4 "색 표현 방식 확장" 절 신설 + §5 흰색 판정 보류 기록)는
  이 카드가 건드린 frontmatter 두 줄(`status`/`updated`)과 라인이 겹치지
  않는다(직접 `git diff` 로 읽어 확인). **이 카드는 지시대로 push·PR·
  다른 워크트리 접근을 하지 않았으므로 `origin/main` 을 이 브랜치에
  병합하지 않았다** — 병합하면 이 카드가 검증하지 않은 변경(색 경로
  M2 하위 스레드)까지 이 카드의 커밋 범위로 끌어들이게 된다. 이 지연은
  머지 전 리드/오케스트레이터가 판단할 잔여 위험으로 남긴다.
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
