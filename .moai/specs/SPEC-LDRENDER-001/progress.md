# SPEC-LDRENDER-001 — 진행 기록

## §E.1 Plan-phase Audit-Ready Signal

- plan_status: audit-ready
- plan_complete_at: 2026-10-01
- tier: M (spec.md + plan.md + acceptance.md 3종, research.md 추가 산출물)
- REQ 16개(M2 신설로 REQ-002/REQ-011 이 결정 반영 내용을 병합 — 새 REQ ID 추가 없음) · AC 16개(AC-015·016 은 전체 REQ 공통 비파괴/인간 판정) · 미해소 `[NEEDS CLARIFICATION]` 마커 **0건** — 리드 경유 감독 결정 4건(2026-10-01, 2차)이 §5 의 열린 결정 3건을 전부 해소했다: 결정 1(역할 어휘 옵션 a, REQ-002) · 결정 2(LIT-only 집계·큐 단위, REQ-001/013/014) · 결정 3(층→색 배정, REQ-004) · 결정 4(R4 옵션 a + 충돌 검출, REQ-011).
- plan-auditor iteration 1 FAIL(0.74) → D1~D7 + D9/D10 반영(1차 revision). plan-auditor iteration 2 FAIL(0.68, 점수 역행) → D11(AC-001 "과반" 무단 완화)·D12(key/back/effect 트리오 메트릭 게이밍, critical) → 감독 결정 2(LIT-only·큐 단위)가 양쪽을 동시에 해소(2차 revision, 본 기록). **마일스톤 재구조화**: M2(역할 어휘 확장 — 정본 §2c 버전 올림 + `RIG_LAYER_ROLES`)를 신설해 M3(구 M2, R1 렌더링)의 선행 조건으로 배치 — LIT-only 집계 하에서 R1 의 "3+ 층" 목표가 이 신설 마일스톤에 실질적으로 의존하기 때문(spec.md §3.1 [HARD], plan.md §B 위험 8). 구 M2~M6 은 M3~M7 로 전부 1단씩 밀렸다. 재감사(iteration 3) 대기.

## §E.2 Run-phase Evidence

### M1 — 측정: fx.permitted 원인 + 판독 하네스 제품화 (카드 t501)

**읽기 전용 경계 준수**: 콘솔 쓰기 0건. 코드 판독 + 오프라인(합성 패치 데이터)
측정만 수행했다 — 실기 콘솔 접촉 없음(§C "M1 읽기 전용 경계").

#### fx.permitted=0 원인 (REQ-LDRENDER-009, AC-LDRENDER-008)

- **등급: 코드 판독 + 잰 값 (확정, 추정 아님).**
- **코드 판독 경로**: `server/web/session.py:7444-7445`(`rig_read = self._try_rig_capabilities(); rig = build_rig_profile(patch=list(rig_read.patch), groups={}, coords=coords)`), `server/orchestrator/tools.py:3324`(동일 패턴) → `server/design/rig_capability_read.py:169-171`(`DesignRigRead.patch = patch_records(caps)`) → `server/design/capability_verdict.py:97-100`(`CAPABILITY_VOCABULARY = {POSITION_CAPABILITY: (Pan, Tilt), ZOOM_CAPABILITY: (Zoom,)}` — `"effect"` 키 자체가 없음) → `:119-134`(`patch_records()`가 `_capabilities_of()`로 이 표만 참조) → `server/design/rig.py:283-293`(`_build_inventory`가 `record.capabilities`에서만 `capability_fids`를 채움) → `server/design/energy.py:262-273`(`_fx_axes`가 `rig.has_capability("effect")` 거짓이면 0 반환).
- **확정된 원인(긍정도 부정도 아닌 세 번째 갈래 — AC-008 의 이분법을 정밀화)**: 능력 판독 경로는 **존재하고 실제로 프로덕션에 배선돼 있다**(`read_design_rig` 가 두 호출부 모두에서 호출됨 — "선언 경로 자체가 배선 안 됨"은 아니다). 그러나 그 경로가 참조하는 어휘 표(`CAPABILITY_VOCABULARY`)가 **"effect"라는 능력 이름 자체를 선언한 적이 없다** — `capability_verdict.py` 모듈 독스트링(:26-29)이 스스로 명시: `"effect"는 일부러 매핑하지 않는다. 어떤 속성이 있으면 이펙트 축이 열리는지는 이 저장소에서 측정된 바가 없다... 전체 어휘 표는 후속 카드다.` 즉 "능력 선언 경로가 존재하나 **그 어휘 자체가 미완성**"이다 — 리그별 개별 결함이 아니라 **구조적**(모든 리그, 모든 곡에서 동일하게 0).
- **잰 값(오프라인 측정, 읽기 전용)**: `.moai/reports/t501/measure_fx_permitted_zero.py` — Rain 실측 BLIND/STROBE/HAZE 그룹 fid 12대(`fid_names.json` 조인)에 Pan/Tilt **+ Strobe/Shutter**(효과성 속성 가정, 전수 판독 `gaps=()`)를 전부 선언하는 합성 `FixtureCapability`를 만들어 `patch_records()` → `build_rig_profile()` → `rig.inventory.has_capability("effect")`까지 통과시켰다.
  ```
  $ uv run python .moai/reports/t501/measure_fx_permitted_zero.py
  Rain 실측 BLIND/STROBE/HAZE fid 12대: [601, 602, 603, 604, 605, 606, 611, 612, 613, 614, 621, 622]
  patch_records() 결과 12건 중 처음 3건:
    {'fid': 601, 'type_name': 'SyntheticEffectFixture', 'capabilities': ['position']}
  이 레코드들에 실제로 실린 capabilities 전체 집합: ['position']
  "effect" 가 포함되는가: False
  rig.inventory.has_capability("effect") = False
  rig.inventory.capability_fids = {'position': frozenset({601..622 전부})}
  _fx_axes(budget=10, rig) = 0 (이 리그에 Strobe/Shutter 를 선언하는 기구가 있어도 0)
  ```
  **결론**: Strobe/Shutter 를 전수 선언해도 "effect" 는 끝내 나타나지 않는다 — `CAPABILITY_VOCABULARY`에 그 키가 없기 때문이다. **실기 패치 데이터를 넣어도 이 답은 바뀌지 않는다**(§D 질문 응답, 아래).
- **§D 질문 — 실기 콘솔 패치 데이터가 답을 바꿀 수 있는가**: 아니다. 능력을 콘솔에서 읽는 경로(`capability_join.read_rig_capabilities`)는 실재하고 `axes`(Pan/Tilt/Zoom 등 실측 속성)를 충실히 나른다 — 그 경로 자체는 건재하다. 하지만 `capability_verdict._capabilities_of()`가 `axes`를 "capabilities" 이름으로 번역할 때 참조하는 표(`CAPABILITY_VOCABULARY`)가 `{position, zoom}` 두 키만 가지므로, **실기가 Strobe/Shutter/Gobo 등 무엇을 선언하든 "effect"로 번역될 길이 없다**. 고치려면 ①"effect 축을 여는 속성이 무엇인지"를 이 저장소에서 실측(모듈 독스트링이 스스로 "측정된 바 없다"고 명시)하고 ②`CAPABILITY_VOCABULARY`에 `"effect": (<측정된 속성들>,)` 항목을 추가해야 한다 — **이 추가 자체는 M1 의 범위 밖이다**(위 지시문 "R4 fix를 구현하지 마라" — M1 은 원인 확정만, 처방은 후속 카드/M6 트랙).
- **REQ-LDRENDER-010 연쇄 영향**: `fx.permitted`가 8곡 전부에서 항상 0 이므로, REQ-010의 전제조건("fx.permitted 이 0보다 크고...")이 **구조적으로 단 한 번도 성립하지 않는다** — t499 P5a/P5b(8곡 전부 페이저 제안 104큐 → 송신 0줄)가 관측한 현상과 이 코드 판독·잰 값이 정확히 들어맞는다.

#### 판독 하네스 제품화 (REQ-LDRENDER-013, AC-LDRENDER-012/013)

- 신규 모듈: `server/design/ldrender_gate.py` — `.moai/reports/t499/readout.py`의 판정 로직(색 수·구간-큐당 LIT 층 수·효과 줄 수·구간 큐 간 색 변화·effect 그룹의 값-줄 관여 플래그)을 순수 함수로 추출. API: `SectionCue`(dataclass 입력), `GateResult`(dataclass 출력), `evaluate(cues, *, sent_lines, fx_requested, fx_hinted, palette_mode) -> GateResult`, 보조 함수 `layer_diversity`·`color_count`·`color_change_count`·`effect_line_count`·`effect_group_in_value_lines`·`is_exempt_cue`.
- **readout.py 는 건드리지 않았다** — 이유: readout.py는 `.moai/reports/`의 히스토리 기록(과거 실행의 재현성이 가치)이고, readout.py 의 `distinct_layers`/`stage_rig_layers` 집계는 **LIT-only 가 아니다**(코드 판독 확인 — `rig_view`/`violations`가 디머 값과 무관하게 상태 비어있지 않음만 본다). 이 차이를 readout.py 에 넣으면 그 파일이 과거에 낸 `readout_8songs.txt`/`summary.json`(이미 기록된 산출물)이 바뀐다 — 그래서 readout.py 를 그대로 두고 **새 모듈이 독립적으로 LIT-only 규칙을 구현**했다(감독 결정 2). 차이점은 `ldrender_gate.py` 모듈 독스트링에 명시했다.
- **LIT-only 집계가 readout.py 와 실제로 다른 결과를 내는지**: Rain 실측 입력(모든 그룹이 디머>0) 자체로는 차이가 **드러나지 않는다**(두 셈법 모두 2버킷) — 이 입력이 전부 디머>0 인 우연 때문이다. 차이가 실제로 작동함은 `test_layer_diversity_excludes_zero_dimmer_roles`의 뮤테이션 대조로 별도 확인했다(아래 §뮤테이션).
- **집계 동치성(AC-012)**: `test_layer_diversity_matches_manual_lit_only_count`가 손으로 센 LIT-only 집합과 `layer_diversity()`의 결과가 일치함을 1개 큐에서 교차검증한다 — **모든 큐 형태에 대한 일반 증명은 아니다**(§Gaps 참조).
- **버킷 단위 단순화(의도된 단순화, 모듈 독스트링에 명시)**: readout.py 의 `distinct_layers`는 그룹 하나의 상태 목록 전체를 한 단위로 비교하지만, `layer_diversity()`는 상태 하나하나를 독립적으로 버킷에 넣는다 — 지금까지 측정된 입력(그룹 내부가 항상 균일, 목록 길이 1)에서는 두 셈법이 일치하지만, 그룹 내부가 갈라진 입력으로는 실측하지 않았다.

#### 테스트 — `server/tests/test_ldrender_gate.py` (신규 7개)

| 테스트 | 성격 | 결과 |
|---|---|---|
| `test_rain_before_fix_warns_on_all_three_axes` | AC-013 음성 대조(Rain 고치기 전 — 4개 대표 큐, 실측 데이터 전사) | PASS |
| `test_passing_synthetic_does_not_warn` | AC-013 양성 대조(합성 — 3색·LIT≥3·효과 1줄) | PASS |
| `test_palette_mode_na_skips_color_count_check` | AC-014(REQ-015) — `single` 모드 색 수 n/a | PASS |
| `test_layer_diversity_matches_manual_lit_only_count` | AC-012 집계 동치성(1개 큐 교차검증) | PASS |
| `test_layer_diversity_excludes_zero_dimmer_roles` | 뮤테이션 대조 — effect 를 디머>0 으로 켜면 버킷+1 | PASS (뮤테이션 적용 시 FAIL 확인, 아래) |
| `test_color_count_excludes_exempt_cues` | AC-001 경계 사례(블랙아웃/MIB 예외) | PASS |
| `test_effect_line_count_excludes_position_preset_pool` | readout.py 규칙 재사용(포지션 풀 2 제외) | PASS |

```
$ PYTHONDONTWRITEBYTECODE=1 uv run pytest server/tests/test_ldrender_gate.py -q
.......
7 passed in 0.05s
```

**뮤테이션(§3.3 요구 — 새 단언에 걸어라)**: `layer_diversity()`의 LIT 필터(`if float(dim) <= 0: continue`)를 제거하고(디머 값 무관하게 전부 버킷에 넣도록) 재실행:
```
$ PYTHONDONTWRITEBYTECODE=1 uv run pytest server/tests/test_ldrender_gate.py -q
....F..
1 failed, 6 passed in 0.07s
FAILED test_layer_diversity_excludes_zero_dimmer_roles
  AssertionError: effect 를 디머>0 으로 켰는데 버킷 수가 그대로다(before=4, after=4)
```
뮤테이션이 의도한 단 하나의 테스트만 빨갛게 만들었다(다른 6개는 Rain 실측 입력이 전부 디머>0이라 영향받지 않음 — §3.3 "자극은 재려는 축 하나만 건드려야 한다"와 일치). 복원 후 7개 전부 재확인 PASS.

#### 회귀 — 지정 범위 + 전체 스위트

```
$ PYTHONDONTWRITEBYTECODE=1 uv run pytest server/tests/test_layer_mapping_effect_role.py server/tests/test_song_cue_color_emission.py server/tests/test_song_cue_white_preset_t453.py -q
.........................................
41 passed in 0.64s
```
```
$ PYTHONDONTWRITEBYTECODE=1 uv run pytest server/tests/test_layer_mapping_effect_role.py server/tests/test_song_cue_color_emission.py server/tests/test_song_cue_white_preset_t453.py server/tests/test_ldrender_gate.py -q
................................................
48 passed in 1.61s
```
지정 범위: 41 → 48 (+7, 신규 테스트 수와 정확히 일치 — 삭제 0 · 교체 0).

전체 스위트(`server/tests/`, 신규 2개 파일을 스크래치패드로 치워 측정한 `before`와 복원 후 `after` 둘 다 실제로 재실행):
```
# before (server/design/ldrender_gate.py · server/tests/test_ldrender_gate.py 제외)
$ PYTHONDONTWRITEBYTECODE=1 uv run pytest server/tests -q -p no:cacheprovider
14387 passed, 35 skipped in 205.61s

# after (복원)
$ PYTHONDONTWRITEBYTECODE=1 uv run pytest server/tests -q -x -p no:cacheprovider
14394 passed, 35 skipped in 237.27s
```
14387 → 14394 (+7, 신규 테스트 수와 정확히 일치 · skip 수 불변 · 전체 스위트 FAIL 0건).

#### 린트/포맷

```
$ uv run ruff check server/design/ldrender_gate.py server/tests/test_ldrender_gate.py .moai/reports/t501/measure_fx_permitted_zero.py
All checks passed!
$ uv run ruff format --check server/design/ldrender_gate.py server/tests/test_ldrender_gate.py .moai/reports/t501/measure_fx_permitted_zero.py
3 files already formatted
```

#### @MX 태그

`server/design/ldrender_gate.py`의 `evaluate()`는 신규 공개 함수지만 M1 시점의 fan_in 은 0(아직 아무 생산 코드도 이 모듈을 호출하지 않음 — M7 이 배선한다). ANCHOR 요건(fan_in>=3)에 못 미치므로 ANCHOR 는 달지 않았다. 테스트 없는 공개 함수가 아니므로(`test_ldrender_gate.py`가 전부 커버) TODO 도 불필요. 위험한 패턴(goroutine 류, 복잡도>=15) 없음 — WARN 불필요.

#### M1 이 하지 않은 것 (§Gaps — 명시)

- **AC-001 자체는 검증하지 않았다** — M1 은 게이트 모듈만 만들었다. AC-001(실제 송신 목록이 LIT 층 3개 이상을 내는가)은 M2(역할 어휘 확장)·M3(다중 역할 렌더링)가 구현된 뒤에야 PASS 가능하다(§B 위험 8 — 현재 key/back 뿐이면 구조적으로 2버킷).
- **REQ-014(게이트를 송신 직전 호출 지점에 배선)는 하지 않았다** — M7 의 몫. `evaluate()`는 아직 `reviewed_song_commands` 어디에서도 호출되지 않는다(grep 확인 0건).
- **`effect_group_in_value_lines()`는 아직 아무 판정에도 안 쓰인다** — REQ-007/M5 의 선행 유틸로만 만들어 뒀다.
- **집계 동치성은 1개 큐에서만 교차검증했다** — 모든 큐 형태(그룹 내부가 갈라진 경우 등)에 대한 일반 증명이 아니다.
- **실기 콘솔 접촉 없음** — §C 의 "M1 읽기 전용 경계"를 지키기 위해 의도적으로 생략했다. 합성 패치 데이터로 수행한 측정(위)이 실기 접촉 없이도 결론이 구조적으로 불변함을 보여주므로, 이 Gap 은 결론의 신뢰도를 낮추지 않는다(위 §D 질문 응답).
- **이 워크트리는 `WT-ldrender-run`(t501) 의 canonical 1커밋 뒤처져 있다** — `git branch --show-current` 결과가 `worktree-agent-af2ef34f7d94f8ec7`이고 `HEAD`는 `5220ca4e`(canonical `c11ee839` 보다 1커밋 뒤). 차이 커밋(`c11ee839`)을 `git show`로 대조한 결과 AC-002(M2 범위, acceptance.md 문면 1줄 — "다섯 조건 전부 성립해야 PASS") 뿐이었고 M1 범위(REQ-009/013)에 영향 없음을 확인했다.

## §E.3 Run-phase Audit-Ready Signal

_<run-phase 대기>_

## §E.4 Sync-phase Audit-Ready Signal

_<sync-phase 대기>_
