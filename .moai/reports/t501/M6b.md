# t501 M6b — Step 경계 dedupe: FXLIB value_line_collision 처방

SPEC-LDRENDER-001 M6 연속(director decision ②, 2026-10-02). 읽기 전용
경계를 지켰다 — 콘솔 쓰기 0건, 실기 접촉 없음(배차서 지시 그대로 승계).

## 주장 (Claim)

1. M6 가 측정한 4개 필요 라벨(Drop Slam/Breathe Warm/Breathe Cool/
   Finale Slam)의 `value_line_collision` 거부 원인은 FXLIB `_guard_
   collision`이 "스텝 경계와 무관하게 같은 값 줄이 두 번이면 전부
   충돌"로 판정했기 때문이다 — 실제로는 두 스텝 모두 같은 채널 값이
   우연히 겹치는 것일 뿐, 콘솔 쪽에서는 서로 다른 스텝의 값이라 둘 다
   필요하다.
2. `run_commands`의 중복 제거 스코프를 `Step <n>` 표준형 줄에서 리셋하고
   FXLIB `_guard_collision`을 같은 규칙으로 완화했다 — **같은 스텝 안의
   반복은 여전히 거부, 스텝 경계를 건넌 반복은 더 이상 충돌이 아니다.**
3. 이 변경 전후로 t476/t475 가족(선택 붙은 값 줄 면제, 크로스콜 fold)의
   기존 동작은 **0건 회귀** — 전용 테스트 212건 + 전체 스위트 +10건
   (제거 0, skip 변화 0) 모두 통과.
4. 처방 적용 결과 5개 필요 라벨 전부가 이 경로로 빌드된다. Rain 5절
   정지점 산출물을 재생성해 5개 전부의 전송 명령 전문 + 풀.슬롯 제안을
   콘솔 접촉 없이 다시 산출했다.
5. 뮤테이션 3건 전부 대상만 사망, 린트/포맷 전부 통과.
6. **이 카드가 실제로 뒤집는 것은 plan.md §D 만이 아니다** — 이 FXLIB
   코드를 원래 정의한 `SPEC-COPILOT-FXLIB-001`의 **결정 E**가 "스텝 값
   라인의 유일성은 저작 제약"(= 같은 attribute 가 다른 스텝에서
   반복되는 것은 거부해야 할 저작 결함)이라고 명시했었다 — M6b는 그
   전제를 스텝 경계 한정으로 뒤집는다. 교차 호출 fold(REQ-FXLIB-011
   (b))는 그대로 보존했으므로 되돌릴 필요는 없다고 판단했지만, 이
   선례의 존재는 director decision ②를 승인한 리드가 알아야 할 사실
   이라 §Residual-risk 에 명시한다.

## 증거 (Evidence)

### 1. 전제 변경 (plan.md §D 덮어씀, 명시)

plan.md §D: "`_PROGRAMMER_STATE_COMMANDS`/dedupe 면제 집합 무변경(값
라인 충돌 가드는 그대로 둔다)". 리드가 director decision ②(2026-10-02)
로 이 제약을 **Step 경계 한정**으로 덮어썼다 — `_PROGRAMMER_STATE_
COMMANDS` 튜플 자체는 바이트 동일로 남았고(아래 §2 확인), 덮어쓴 건
"값 라인 충돌 가드는 그대로 둔다"는 범위뿐이다.

### 2. 원인 지점 읽기 (코드 판독, 추측 아님)

- `server/orchestrator/tools.py:2513-2571` `run_commands` 중복 제거
  루프 — `already_executed = set(context.executed_ok)`가 호출 전체에
  걸쳐 단조 누적되고, 리셋 지점이 없었다.
- `server/orchestrator/tools.py:1108-1113` `_PROGRAMMER_STATE_COMMANDS`
  — "저장물을 만드는가"만 판별, 스텝 위치는 무관.
- `server/fx/instantiate.py:588-612` `_guard_collision` — "이 번들 전체"
  스코프로 `seen` 집합을 유지, docstring 이 스스로 "두 번째 줄이
  `run_commands` dedupe 에 drop 된다"고 명시(즉 `_guard_collision`은
  `run_commands`의 실제 동작을 선제 모사한 것이지 독립 규칙이 아니다 —
  둘을 같은 규칙으로 바꿔야 하는 이유).
- REQ-FXLIB-011 원본(`.moai/specs/SPEC-COPILOT-FXGEN-001/spec.md`
  검색) — "이 스토어는 ONE 스토어"라는 전제만 있고 스텝별 스코프는
  명시돼 있지 않다 — M6b 가 그 공백을 메운다.

### 3. 처방 — 코드

```python
# server/orchestrator/tools.py
_STEP_BOUNDARY = re.compile(r"Step\s+\d+", re.IGNORECASE)

def _is_step_boundary(command: str) -> bool:
    return _STEP_BOUNDARY.fullmatch(command.strip()) is not None

# run_commands 루프, 명령 처리 직후:
if not failed and _is_step_boundary(command):
    already_executed = set()
```

```python
# server/fx/instantiate.py — _guard_collision
seen: set[str] = set()
for command in commands:
    if _STEP_BOUNDARY.fullmatch(command.strip()) is not None:
        seen = set()
        continue
    if is_programmer_state(command):
        continue
    if command in seen:
        raise FxInstantiationError(VALUE_LINE_COLLISION, ...)
    seen.add(command)
```

마커 자신의 skip/execute 판정은 **리셋 전** 이력으로 내린다 — 이 턴
안에서 이미 발사된 `Step <n>` 줄의 크로스콜 fold(REQ-FXLIB-011 (b))는
유지된다(아래 §RED→GREEN, `test_a_step_marker_already_executed_in_a_
prior_call_still_folds` 참조).

### 4. RED→GREEN

```
$ PYTHONDONTWRITEBYTECODE=1 uv run pytest server/tests/test_fx_instantiate.py::test_a_value_repeated_ACROSS_a_step_boundary_is_no_longer_a_collision -q
1 passed
```

처방 적용 전(되돌린 사본으로 재확인, 아래 §뮤테이션 2) 이 테스트는
`FxInstantiationError(VALUE_LINE_COLLISION)`를 올려 RED, 적용 후
GREEN. 기존 `test_a_pattern_repeating_a_step_value_is_refused_before_
the_bundle_exists`는 `test_a_value_repeated_WITHIN_one_step_is_still_
refused_before_the_bundle_exists`로 이름을 바꿔 "같은 스텝 반복은
여전히 거부"로 보존했다(RED 없음 — 기존 동작 유지 확인).

### 5. 5개 라벨 전부 빌드 확인

```
$ PYTHONDONTWRITEBYTECODE=1 uv run pytest server/tests/test_phaser_pregen.py -q
25 passed
$ PYTHONDONTWRITEBYTECODE=1 uv run pytest server/tests/test_phaser_pregen_wiring.py -q
7 passed
```

`test_the_other_four_needed_labels_now_build_cleanly_too`(4개
파라미터화 — Drop Slam/Breathe Cool/Finale Slam/Breathe Warm 전부 빌드
+ `Step 2` 마커 생존 확인) + `test_a_genuine_same_step_collision_is_
still_refused`(합성 Fx로 같은 스텝 반복을 몽키패치 재현, 여전히
`VALUE_LINE_COLLISION`). 배선 쪽은 `test_drop_slam_now_builds_and_
dispatches_through_the_gate`(Drop Slam이 이제 기존 `run_commands`
게이트로 디스패치됨) + `test_a_genuine_same_step_collision_is_still_
reported_not_overwritten`(합성 충돌은 여전히 콘솔 접촉 0건으로 거부).

### 6. 크로스콜 fold 보존 확인

```
$ PYTHONDONTWRITEBYTECODE=1 uv run pytest server/tests/test_tools.py -q -k StepBoundary
5 passed
```

`test_a_step_marker_already_executed_in_a_prior_call_still_folds` —
이전 호출에서 이미 발사된 `Step 2`는 이 번들에서도 여전히
`skipped_already_executed`(REQ-FXLIB-011 (b) 크로스콜 감지 유지), 단
그 **뒤**의 값 줄은 리셋된 스코프 덕에 실행된다. `test_fx_tool.py
::TestACrossCallFoldIsAnExplicitFailure` + `test_scene_tool.py
::TestACrossCallFoldIsAnError`(둘 다 기존 크로스콜 fold 통합 시험,
`context.executed_ok` 시딩) 전부 그대로 통과.

### 7. t476/t475 가족 + 미러 동치 + 전체 스위트

```
$ PYTHONDONTWRITEBYTECODE=1 uv run pytest server/tests/test_dedupe_value_lines_t476.py server/tests/test_fx_boundary.py server/tests/test_groupgen_write.py server/tests/test_overlap_preserve.py server/tests/test_song_readback_props_t479.py server/tests/test_songcue_bundle.py -q
212 passed
```

```
$ unset MOAI_KANBAN MOAI_KANBAN_ID MOAI_KANBAN_LABEL MOAI_KANBAN_LEAD_ADDR MOAI_KANBAN_SETTINGS_INJECTED && PYTHONDONTWRITEBYTECODE=1 uv run pytest server/tests -q -p no:cacheprovider
14525 passed, 35 skipped, 1 warning in 253.77s
```

베이스라인(M6, HEAD `947ddba8`) `14515 passed, 35 skipped` 대비 **+10
passed, 0 removed, skip 변화 0** — 신설/치환 테스트 수(`test_fx_
boundary.py` +2, `test_fx_instantiate.py` 순증 +1, `test_phaser_
pregen.py` 순증 +1, `test_phaser_pregen_wiring.py` 순증 +1,
`test_tools.py` 신설 5 = 10)와 정확히 일치.

### 8. 뮤테이션(3건, 각 1축, diff 확인 후 복원, `diff -q`로 원본 바이트
동일 재확인)

| 뮤테이션 | 대상 | 죽은 테스트 |
|---|---|---|
| `run_commands`의 Step 경계 리셋 블록 삭제 | `tools.py` | 2건 |
| `_guard_collision`의 Step 경계 리셋 분기 삭제 | `instantiate.py` | 5건 |
| `_STEP_BOUNDARY`에서 `IGNORECASE` 제거(fx 측만, 미러 불일치 재현) | `instantiate.py` | 2건 |

생존 뮤턴트 0건.

```
$ uv run ruff check server/fx/instantiate.py server/orchestrator/tools.py server/tests/test_fx_boundary.py server/tests/test_fx_instantiate.py server/tests/test_phaser_pregen.py server/tests/test_phaser_pregen_wiring.py server/tests/test_tools.py .moai/reports/t501/m6b_pregen_stop_point.py
All checks passed!
$ uv run ruff format --check <동일 8개>
8 files already formatted
```

### 9. 5절 정지점 재생성 (WITHOUT SENDING)

```
$ uv run python .moai/reports/t501/m6b_pregen_stop_point.py
```

산출: `.moai/reports/t501/m6b_pregen_commands_rain.txt`(5개 전부 명령
전문), `.moai/reports/t501/m6b_pregen_targets_rain.md`(풀.슬롯·판정·줄
수·스텝 완전성 표 + "전송 전 재조회 필수" 명시), `.moai/reports/t501/
m6b_pregen_stop_point_output.json`.

## 기준선 (Baseline-attribution)

- 커밋: 이 작업은 `git merge --ff-only origin/WT-ldrender-run` 직후
  `git rev-parse --short HEAD` → `947ddba8`(배차서가 지정한 canonical
  HEAD, M6 완료 커밋) 위에서 수행했다. 이 보고서의 모든 측정은 이
  워크트리에서 M6b 구현을 적용해 직접 실행한 결과다.
- 전체 스위트 베이스라인(M6, 14515/35)은 M6.md §Evidence 6 에 이미
  기록된 값(이 카드가 재측정한 것이 아니라 직전 보고서 값을 그대로
  인용) — 이번 M6b 애프터(14525/35)는 이 워크트리에서 직접 실행해
  관측한 verbatim 출력이다.
- Color(4)/All 1(21) 풀 점유 증거: `.moai/reports/t501/
  m6_postsend_reread_20261002.txt`·`m6_pool_reread_readonly.txt` — 이
  카드가 만든 것이 아니라 M6 본편이 이미 저장해 둔 읽기 전용 레코드를
  그대로 읽기만 했다(새 콘솔 접촉 0, 카드 제약 준수).

## 미검증 (Gaps)

- 4개 라벨의 실제 콘솔 전송 — 이 카드도 콘솔 쓰기 0건 제약. §5 정지점
  산출물은 "보낼 수 있다"만 보인다.
- Step 경계를 건넌 반복이 실기 콘솔에서 M0 anchor 와 **같은 phaser
  효과**를 내는지 — 명령 문면은 FXLIB 표준형 그대로이지만, "두 스텝
  사이 한 채널만 다른" 조합의 육안 확인은 이 카드 범위 밖(콘솔 접촉
  0건 제약).
- AC-LDRENDER-009/010/016 — M6 §Gaps 와 동일 사유로 승계(기계 증거는
  Wave CM 한정 가능성, 전송 자체를 하지 않음, 사람 판정은 범위 밖).

## 잔여 위험 (Residual-risk)

- **선례 재검토 미확인(§Claim 6 참조)** — `SPEC-COPILOT-FXLIB-001`
  결정 E("스텝 값 라인의 유일성은 저작 제약 — 다른 스텝 반복도 거부
  대상")를 이 카드가 스텝 경계 한정으로 뒤집었다. director decision
  ②(plan.md §D 로컬 제약 덮어쓰기)가 이 더 깊은 선례의 존재를 알고
  내린 결정인지는 배차서에 명시돼 있지 않다 — 교차 호출 fold(REQ-
  FXLIB-011 (b))는 보존했으므로 작업을 되돌리지는 않았지만, 리드가
  이 선례를 인지하고 있는지 재확인이 필요하다.
- Color 풀의 `.10` 삼중 제안(Wave CM/Breathe Warm/Breathe Cool, Wave
  CM 은 이미 전송됐으므로 재전송 의미 없음 — 실질적으로는 Breathe
  Warm/Breathe Cool 둘이 경합) — 순서대로 전송 시 두 번째부터 재조회
  필수, `m6b_pregen_targets_rain.md`에 명시.
- 이 완화는 **값 라인에만** 적용된다 — `Store`/`Label`/`Assign`/
  `Delete` 등 저장물을 만드는 줄은 Step 경계와 무관하게 기존 dedupe
  그대로(문자 그대로 중복이면 여전히 1회만 발사); 이 카드가 바꾼 것은
  비면제·비마커 값 줄에 적용되는 스코프뿐이다.
- `select_preset_number`의 번호 할당 경쟁 조건은 FXLIB 기존 경계
  그대로(M6 과 동일, 새로 막지 않음).
- `group=1` 스크래치 저작 선택이 모든 리그에서 addressable 하다는
  보장은 없다(M6 과 동일, Rain 리그 한정 확인).
- Wave CM phase/curve 문법 괴리(M6 §잔여 위험 그대로 승계) — 실기로
  "같은 효과"가 검증되기 전까지는 모든 사전 생성 페이저에 남는 위험.

---

🗿 MoAI
