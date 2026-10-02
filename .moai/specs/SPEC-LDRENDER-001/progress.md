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

### M2 — 역할 어휘 확장: 정본 §2c 버전 올림 + `RIG_LAYER_ROLES` + 그룹 이름 해석 (카드 t501, REQ-LDRENDER-002, 감독 결정 1)

**착수 베이스라인**: `git merge --ff-only origin/WT-ldrender-run` → HEAD `d5a82c26`(M1 완료 커밋) — `git log --oneline -1` 로 확인. 6개 순서 단계(①~⑥, 배차서) 전부 별도 또는 그룹 커밋으로 수행:

| 단계 | 내용 | 커밋 |
|---|---|---|
| ① | 정본 §2c "role층 → 그룹 매핑" 표에 side/wash/mover 추가 + 문서 버전 v0.4→v0.5(§2c 섹션도 동일), RG5-1 신설 | `c9ac4e63`(단독) |
| ② | `rig.py:44` `RIG_LAYER_ROLES` 튜플 확장(key/back/effect/audience/side/wash/mover) | `a5971fe0` |
| ③ | `_build_layers` 가 `declared_layers={"side":...,"wash":...,"mover":...}` 를 `RigProfileError` 없이 수용 — 신규 테스트 | `f4a4dc62` |
| ④ | `has_layer()`/`RIG_LAYER_ROLES`/`layers.mapping` 소비자 전수 grep + 영향 재검토 | `b7cf6bfc`(실제 영향 발견 + 수정) |
| ⑤ | `_LAYER_GROUP_ALIASES` 접두 토큰(하이픈 앞) 해석 추가 | `a5971fe0` |
| ⑥ | `test_mover_and_wash_groups_remain_unmatched_documented_residual` 의도적 뒤집음 | `f4a4dc62` |

#### ① 정본 문서 (REQ-002, AC-002 조건 1)

```
$ head -1 docs/proposals/song-lighting-design-standard.md
# 곡 단위 조명연출 표준 초안 (Song Lighting Design Standard, v0.5)
$ grep -n "역할층" docs/proposals/song-lighting-design-standard.md
85:  layers:     역할층 → 그룹 매핑 (key/back/effect/audience/side/wash/mover)  ← 조명 디자인
$ git log -1 --format=%s -- docs/proposals/song-lighting-design-standard.md
t501: SPEC-LDRENDER-001 M2① — 정본 §2c 버전 올림, side/wash/mover 역할 추가 (감독 결정 1)
```
RG5-1 신설 단락(§2c)에 접두 토큰 매칭 규칙을 명문화 — SIDE-L/R/ALL→side, WASH-U/D/ALL→wash, MOVER-U/D/ALL→mover, 부분 문자열 추측 금지.

#### ② `RIG_LAYER_ROLES` 확장 (REQ-002, AC-002 조건 2)

```
$ uv run python -c "from server.design.rig import RIG_LAYER_ROLES; print(RIG_LAYER_ROLES); assert {'side','wash','mover'} <= set(RIG_LAYER_ROLES)"
('key', 'back', 'effect', 'audience', 'side', 'wash', 'mover')
```
기존 네 역할의 순서·값은 바이트 동일(앞에 유지, 뒤에 세 역할만 추가).

#### ③ `_build_layers` 수용 (REQ-002, AC-002 조건 3) — 두 팔

```
$ PYTHONDONTWRITEBYTECODE=1 uv run pytest server/tests/test_design_rig.py -q -k "accept_side_wash_mover or reject_unknown_role"
..
2 passed, 31 deselected in 0.05s
```
팔 1(수용): `test_declared_layers_accept_side_wash_mover_roles` — `declared_layers={"side":...,"wash":...,"mover":...}` 가 `RigProfileError` 없이 `RIG_LAYER_SOURCE_DECLARED` 로 수용됨. 팔 2(여전히 거부): 기존 `test_declared_layers_reject_unknown_role` — 모르는 역할 문자열은 여전히 거부(변경 없음, 회귀 확인).

#### ④ 소비자 전수 grep + 재검토 — **실제 영향 1건 발견·수정** (REQ-002 본문 "소비자 전수 재검토")

grep 결과(`has_layer(`/`RIG_LAYER_ROLES`/`layers.mapping`/`fids_for(`/`RigLayers(`):

```
$ grep -rln "has_layer(\|RIG_LAYER_ROLES\|layers\.mapping\|fids_for(\|RigLayers(" server/
server/design/__init__.py        (RIG_LAYER_ROLES re-export 뿐)
server/design/ldrender_gate.py   (주석 인용 뿐)
server/design/rig.py             (정의 자체)
server/design/song_cue_composer.py  (has_layer("back") 두 자리, :711·:716)
server/tests/test_design_rig.py
server/tests/test_layer_mapping_foh_front.py
```
`song_cue_composer.py` 의 `has_layer()` 호출은 `"back"` 인자뿐이라(§B 위험 7 (d) 우려 대상) side/wash/mover 등장에 영향받지 않는다 — `lint.py` 의 L6/L7 도 `layer_rules_active()`(mapped 불리언)만 읽어 역할 무관. `server/orchestrator/tools.py`: 위 네 패턴 매치 0건(grep 확인).

**그러나 grep 패턴 밖의 실제 영향이 전체 회귀에서 드러났다**: `session.py` 의 `_LAYER_ROLE_LABELS[str(entry['role'])]`(`_confirm_song_layer_mapping` 확인 카드 문구 조립, 결함 6 선례)가 해석된 역할 **전부**를 순회하는데, 이 표에 side/wash/mover 항목이 없어 KeyError. 이 소비자는 위 grep 패턴(`has_layer`/`RIG_LAYER_ROLES`/`layers.mapping`/`fids_for`/`RigLayers(`) 어디에도 안 걸린다 — `str(entry['role'])`로 해석된 역할 이름을 **직접** 키로 쓰기 때문이다. **교훈 기록**: grep 패턴 전수조사가 "RigProfile API 호출부"는 잡지만 "해석된 역할 이름을 문자열로 소비하는 자리"는 못 잡는다 — 두 축이 다르다.

```
# 고치기 전 재현 (session.py/rig.py 를 commit c9ac4e63 으로 되돌려 대조)
$ PYTHONDONTWRITEBYTECODE=1 uv run pytest server/tests -q -p no:cacheprovider
4 failed, 14395 passed, 35 skipped, 1 warning in 197.91s
FAILED test_dedupe_value_lines_t476.py::test_the_whole_approved_rain_bundle_reaches_the_console
FAILED test_song_readback_props_t479.py::test_a_live_shaped_console_that_stored_everything_reads_back_as_verified
FAILED test_song_readback_props_t479.py::test_a_wrong_trig_time_read_through_props_still_fails
FAILED test_song_readback_props_t479.py::test_a_props_read_failure_is_not_reported_as_verified

# 원인 복원(위 commit c9ac4e63 버전으로) + 해당 4건만 재실행 → 전부 PASS (대조 확인)
$ PYTHONDONTWRITEBYTECODE=1 uv run pytest server/tests/test_dedupe_value_lines_t476.py server/tests/test_song_readback_props_t479.py -q -p no:cacheprovider
27 passed in 0.62s

# 수정(side/wash/mover 라벨 추가) 후 같은 4건 + 전체 재실행
$ PYTHONDONTWRITEBYTECODE=1 uv run pytest server/tests/test_dedupe_value_lines_t476.py server/tests/test_song_readback_props_t479.py -q -p no:cacheprovider
27 passed in 0.93s
```
수정: `server/web/session.py` `_LAYER_ROLE_LABELS` 에 `"side": "Side"`, `"wash": "Wash"`, `"mover": "Mover"` 추가(commit `b7cf6bfc`). 신규 회귀 잠금: `test_every_rig_layer_role_has_a_confirmation_card_label`(`RIG_LAYER_ROLES ⊆ _LAYER_ROLE_LABELS.keys()` 직접 단언).

#### ⑤ 접두 토큰 그룹 이름 해석 (REQ-002, AC-002 조건 4)

`server/design/rig.py` 에 `_LAYER_GROUP_PREFIX_ROLES` + `resolve_layer_role()` 신설 — 정확 일치(기존 4역할, 바이트 동일) 우선, 실패 시 첫 하이픈 앞 접두 토큰을 SIDE/WASH/MOVER 와 정확 비교. `_build_layers`(rig.py)와 `_layer_mapping_from_group_children`(session.py) 양쪽이 이 함수를 공유(두 소비자가 각자 판정 루프를 들면 갈라지는 함정을 미리 막음, §B 위험 7 (d)와 같은 종류).

```
$ PYTHONDONTWRITEBYTECODE=1 uv run pytest server/tests -q -k "prefix_token"
....
4 passed, 14431 deselected, 1 warning in 9.38s
```
양성(SIDE-L/R/ALL→side, WASH-U/D/ALL→wash, MOVER-U/D/ALL→mover) + 음성(SIDEWALK 하이픈 없음·XSIDE-L/SIDES-L 접두 토큰 불일치, 셋 다 미매칭) 모두 커버.

**여러 그룹이 한 역할에 매칭될 때의 동점 규율 — 결정 + 기록**: `_build_layers`의 groups-heuristic 경로(실측: 프로덕션에서 `groups={}` 하드코딩이라 실제로는 거치지 않는 경로, §B 위험 2)는 **합집합**(기존 다중-별칭 역할과 같은 의미론, 새 동점 규칙 발명 안 함, `test_group_name_heuristic_maps_side_wash_mover_via_prefix_token`). production 경로(`session.py::_confirm_song_layer_mapping`의 `declared_layers` 딕셔너리 컴프리헨션)는 **이터레이션 순서상 마지막 항목이 이긴다**(기존 동작, 바꾸지 않음) — 이 리그의 측정된 그룹 순서(카드 t379)에서는 그것이 자연히 `-ALL` 그룹을 선택한다(`test_last_matching_group_in_iteration_order_wins_the_role` 로 고정, 근거: `session.py` 코드 판독 — 별도 "ALL 선호" 분기를 새로 만들지 않았다).

#### ⑥ 잔여 테스트 의도적 뒤집음 (REQ-002 본문 "조용히 깨뜨리지 않는다")

```
$ PYTHONDONTWRITEBYTECODE=1 uv run pytest server/tests/test_layer_mapping_effect_role.py -q -k "mover_and_wash or side"
.
1 passed, 8 deselected in 0.41s
```
`test_mover_and_wash_groups_remain_unmatched_documented_residual` → `test_mover_and_wash_and_side_groups_now_match_via_prefix_token` 으로 이름·단언·독스트링 함께 갱신(commit `f4a4dc62`). 같은 파일 안에서 `test_design_rig.py::test_declared_layers_role_vocabulary_is_the_standard_four` → `..._standard_seven` 도 같은 규율로 뒤집음(배차서에 명시된 `:119` 테스트는 아니지만, 역할 튜플 확장의 직접 귀결로 발견된 두 번째 잠금 테스트 — 조용히 깨뜨리지 않고 동일 절차 적용).

#### AC-LDRENDER-002 — 다섯 조건 전부 성립 (acceptance.md "다섯 조건 전부가 성립해야 PASS")

| 조건 | 내용 | 명령 | 결과 |
|---|---|---|---|
| 1 | 정본 §2c 가 side/wash/mover 를 담고 버전이 이전보다 높음 | `head -1 docs/...md` + `git log -1 --format=%s -- docs/...md` | PASS |
| 2 | `RIG_LAYER_ROLES` 가 셋을 포함 | `uv run python -c "from server.design.rig import RIG_LAYER_ROLES; assert {'side','wash','mover'} <= set(RIG_LAYER_ROLES)"` | PASS |
| 3 | `_build_layers` 가 `RigProfileError` 없이 수용 | `pytest -k accept_side_wash_mover` | PASS |
| 4 | 그룹 이름은 하이픈 앞 접두 토큰으로만 해석(부분 문자열 오인 매칭 0건) | `pytest -k prefix_token` | PASS |
| 5 | `:119` 테스트의 뒤집음이 이름·단언·독스트링 갱신과 함께 명시적으로 이뤄짐 | `pytest -k "mover_and_wash or side"` | PASS |

**AC-002 PASS — 다섯 조건 전부 성립.**

#### 뮤테이션 — 새 단언에 걸기 (§3.3 규율)

| 뮤테이션 | 대상 | 죽인 테스트 | 결과 |
|---|---|---|---|
| A: 접두 토큰 정확 매칭 → 부분 문자열(`in`) 허용으로 완화 | `resolve_layer_role()` | `test_group_name_heuristic_prefix_token_rejects_lookalikes`, `test_prefix_token_matching_rejects_lookalikes_no_substring_guessing` | 2건 FAIL (의도대로 빨강) |
| B: `RIG_LAYER_ROLES` 튜플에서 `"mover"` 제거 | `rig.py` | `test_declared_layers_accept_side_wash_mover_roles`, `test_declared_layers_role_vocabulary_is_the_standard_seven` | 2건 FAIL (의도대로 빨강) |
| C: `_LAYER_ROLE_LABELS` 에서 `"mover"` 라벨 제거 | `session.py` | `test_every_rig_layer_role_has_a_confirmation_card_label` | 1건 FAIL (의도대로 빨강) |

세 뮤테이션 모두 `PYTHONDONTWRITEBYTECODE=1` 로 실행, `assert mutated != original`(파이썬 스크립트 내) 로 치환 적용을 확인한 뒤 테스트를 돌렸고, 각 뮤테이션 후 `cp <원본 백업> <경로>` 로 복원해 `git diff --stat`(출력 없음)으로 원복을 확인했다. 복원 후 전체 지정 범위 재실행 PASS(아래 회귀 절).

#### 회귀 — 전체 스위트 (베이스라인 `d5a82c26`, docs-only 커밋 `c9ac4e63` 에서 재측정 — python 파일 무변경이므로 바이트 동일 기준선)

```
# 베이스라인(c9ac4e63, d5a82c26 와 python 파일 동일)
$ PYTHONDONTWRITEBYTECODE=1 uv run pytest server/tests -q -p no:cacheprovider
14394 passed, 35 skipped, 1 warning in 232.46s

# M2 전 커밋(a5971fe0+f4a4dc62, ④ 수정 전) — 4건 FAIL 재현(위 ④ 참조)
14395 passed, 4 failed, 35 skipped

# M2 완료(b7cf6bfc, HEAD)
$ PYTHONDONTWRITEBYTECODE=1 uv run pytest server/tests -q -p no:cacheprovider
14400 passed, 35 skipped, 1 warning in 196.08s
```
14394 → 14400 (**+6, 신규 테스트 수와 정확히 일치** — 삭제 0 · 교체 0 · 전체 FAIL 0건). 신규 6개: `test_design_rig.py` 3개(`test_declared_layers_accept_side_wash_mover_roles`·`test_group_name_heuristic_maps_side_wash_mover_via_prefix_token`·`test_group_name_heuristic_prefix_token_rejects_lookalikes`) + `test_layer_mapping_effect_role.py` 3개(`test_prefix_token_matching_rejects_lookalikes_no_substring_guessing`·`test_last_matching_group_in_iteration_order_wins_the_role`·`test_every_rig_layer_role_has_a_confirmation_card_label`). 이름 뒤집힘 2건(`...standard_four→seven`, `...residual→now_match_via_prefix_token`)은 교체이지 신규가 아니다(순증 불변).

지정 범위(이 M2 가 직접 건드린 소비자 전부):
```
$ PYTHONDONTWRITEBYTECODE=1 uv run pytest server/tests/test_layer_mapping_effect_role.py server/tests/test_layer_mapping_foh_front.py server/tests/test_design_rig.py server/tests/test_song_cue_color_emission.py server/tests/test_song_cue_white_preset_t453.py server/tests/test_seeded_song_apply.py -q -p no:cacheprovider
99 passed in 0.71s
```

#### 린트/포맷

```
$ uv run ruff check server/design/rig.py server/web/session.py server/tests/test_design_rig.py server/tests/test_layer_mapping_effect_role.py
All checks passed!
$ uv run ruff format --check server/design/rig.py server/web/session.py server/tests/test_design_rig.py server/tests/test_layer_mapping_effect_role.py
4 files already formatted
```

#### @MX 태그

`resolve_layer_role()`(신규 공개 함수, `server/design/rig.py`)의 fan_in = 2(`_build_layers` 내부 호출 + `session.py::_layer_mapping_from_group_children`) — ANCHOR 요건(fan_in>=3) 미달, ANCHOR 미부착. 위험한 패턴(goroutine류·복잡도>=15) 없음 — WARN 불필요. 테스트 커버(신규 6건 + 간접 커버 다수) 있으므로 TODO 불필요. `_LAYER_GROUP_PREFIX_ROLES`/`RIG_LAYER_ROLES` 확장 자체는 데이터 선언이라 @MX 대상 아님.

#### M2 가 하지 않은 것 (§Gaps — 명시)

- **M3(다중 역할 렌더링, `CueDimmerData` 확장)는 하지 않았다** — M2 는 역할 **어휘**(이름·그룹 매칭)만 확장했다. side/wash/mover 역할이 매핑에 해석되어도 송신 값 줄은 아직 `back` 만 읽는다(`song_cue_composer.py:711/716`) — AC-001(LIT 층 3개 이상)은 M3 완료 후에나 PASS 가능(plan.md §B 위험 8, 변경 없음).
- **`groups`-heuristic 경로(`_build_layers` 의 fids-union 분기)는 실측상 프로덕션에서 호출되지 않는다**(`groups={}` 하드코딩, §B 위험 2) — 이 분기의 합집합 동작은 단위 테스트로만 검증했고 실기 데이터로는 확인하지 않았다(M1 읽기 전용 경계와 별개로, M2 는 콘솔 접촉이 아예 없다 — 읽기조차 안 함).
- **실기 콘솔 접촉 없음** — M2 는 코드·문서 편집 + 단위/회귀 테스트만 수행했다(콘솔 조회조차 없음, M1 보다 더 좁은 범위).
- **`_SINGLE_LAYER_WARNING`("Front/Back/Beam/Audience 분리 연출은...") 문구는 side/wash/mover 를 나열하도록 갱신하지 않았다** — 이 문구는 단일 레이어 축퇴 상태를 설명하는 일반 경고라 특정 역할 목록을 열거할 필요가 없다고 판단했으나(§4 안티패턴 "정본 문서 편집 범위를 §2c 밖으로 넓히지 마라"의 코드판 — 이 문구는 §2c 밖 코드 상수), 이 판단 자체는 감독 재확인을 받지 않았다 — 재확인이 필요하면 후속으로 갱신한다.
- **`groups`-heuristic 의 "여러 그룹이 한 역할에 매칭 → 합집합" 의미론은 side/wash/mover 전에도 이미 있던 기존 동작이지만, 이 동작이 "옳은지"(여러 물리 그룹을 하나의 역할 fid 집합으로 합치는 것이 항상 맞는지) 자체는 이 카드의 범위 밖 — M2 는 기존 동작을 바꾸지 않았을 뿐, 그 동작의 설계적 정당성을 재검토하지 않았다.**

### M3 — 큐 디머 데이터 모델 확장 + 다중 역할 렌더링 (카드 t501, REQ-LDRENDER-001/003, M2 소비)

**착수 베이스라인**: `git merge --ff-only origin/WT-ldrender-run` → HEAD
`a037ad24`(M2 완료 커밋) — `git log --oneline -1` 로 확인.

#### ① `CueDimmerData` 확장 (REQ-001 본문, plan.md §B 위험 3)

`server/design/song_cue_composer.py` — `role_pct: Mapping[str, float]` 필드를
추가했다(기존 `key_pct`/`back_pct` 는 바이트 동일하게 유지). 두 생산 지점이
공유 헬퍼 `_role_pct_for(key_pct, back_pct)` 로 `role_pct` 를 계산한다:

- `_dimmer_data`(정상·블랙아웃 두 분기 모두) — `{"key": key_pct, "back": back_pct}`
  (각각 `None` 이 아닐 때만 포함).
- `_apply_pre_drop_darkness`(드롭 앞 어둠, `dataclasses.replace`) — **뮤테이션으로
  잡은 실제 버그**: `dataclasses.replace(previous.dimmer, key_pct=target,
  back_pct=...)` 처럼 지정 안 한 필드는 옛 값을 그대로 들고 온다. `role_pct` 를
  다시 계산해 넘기지 않으면 `back_pct` 필드는 내려갔는데 `role_pct["back"]`은
  드롭 앞 값으로 남는 불일치가 생긴다(아래 뮤테이션 D 가 이 경로를 확인).

```
$ uv run python -c "from server.design.song_cue_composer import CueDimmerData; d = CueDimmerData(key_pct=50.0, back_pct=40.0, budget_range_pct=(0.0,100.0)); print(d.role_pct)"
{}
```
(직접 생성 시 `role_pct` 기본값은 빈 매핑 — 유일한 생산 경로인 `_dimmer_data`
를 거쳐야 채워진다.)

#### ② `_back_layer_value_lines` → `_role_dimmer_value_lines` 일반화 (REQ-001 본문)

`server/design/song_cue_render.py` — `role == "back"` 단일 분기를
`_role_group_numbers(layer_mapping)`(역할 → 그룹 번호, **마지막 일치 항목이
이긴다** — `session.py::_confirm_song_layer_mapping` 의 `declared_layers`
딕셔너리 컴프리헨션과 같은 동점 규율, M2 progress.md 선례)로 역할마다 독립된
`Group <n> ; Attribute 'Dimmer' At <pct>` 줄을 내는 함수로 교체했다. 호출부
(`reviewed_song_commands`) 1곳을 갱신했다(grep 확인: `_back_layer_value_lines`
문자열은 이제 docstring 인용(옛 이름 보존)에만 남는다, 코드 호출 0건).

**구조적 가드(`_DIMMER_DELTA_EXCLUDED_ROLES = {"key", "effect"}`)**: `key` 는
전체 기구 키 디머 줄로 이미 나가 있어 델타로 또 내면 중복이다. `effect` 는
R3(REQ-007, M5 — 아직 미착수)가 비액센트 큐의 **어떤** 값 줄에도 effect 역할
기구가 실리지 않기를 요구하는데(spec.md §3.1 HARD), 이 그룹-주소 델타 경로가
`role_pct["effect"]` 를 읽어 값을 내면 공유 `fids` 제외와 무관하게 R3 를
어기게 된다 — 그래서 M5 를 기다리지 않고 여기서 구조적으로 막았다(현재
`_dimmer_data` 는 `role_pct` 에 `effect` 키를 애초에 채우지 않으므로 이
가드는 방어적 이중 장치다, `test_effect_role_is_never_emitted_even_if_role_pct_has_a_value`
가 뮤테이션으로 확인).

#### ③ 수용 테스트 + ⑥ 의도적 뒤집음은 이 카드 범위에 없음 — 정정

배차서의 ③·⑥ 항목(`_build_layers` 수용 테스트·테스트 뒤집음)은 M2 의 몫으로
이미 끝나 있었다(progress.md M2 §③·⑥) — M3 는 M2 가 확장한 역할 어휘를
**소비**만 한다. 착수 전 `git log` 로 M2 커밋(`a5971fe0`·`f4a4dc62` 등) 을
확인해 중복 작업하지 않았다.

#### R4 측 효과 — side/wash/mover 디머 퍼센트 산출 규칙 **미해결** (§미해결 참조)

배차서 지시문대로 착수 전 6단계 검색을 순서대로 훑었다(`.moai/docs/lane-protocol.md`
§1 "「없다」를 쓰기 전에 여섯을 순서대로 훑는다" — 0번 메모리는 나(서브에이전트)에게
없다고 명시돼 있어 1번부터 시작):

| # | 자리 | 결과 |
|---|---|---|
| 1 | `src/Lighting_Designer/01_스펙/LX-SEQ-SPEC-v2.1.md` §11 CUE-EX(17열, `Dim` 열) | **없음** — `Dim` 은 "0–100(%), 빈칸=트래킹"일 뿐 역할별 산출 공식이 아니다. §3.7 예시 행(Q020/Q030)에서도 `KEY 45 / BACK 25` 류 수치는 **디자이너가 직접 적은 값**이지 파생 공식이 아니다. side/wash/mover 류 역할에 대한 비율 언급 0건(전문 grep 확인) |
| 2 | `docs/proposals/song-lighting-design-standard.md` §4a I1·§4b C1/C3 | §4a I1 "층 정의: 키/백/이펙트" — **3층 구조로 고정 서술**(side/wash/mover 언급 0, RG5-1 이 역할 어휘를 확장한 §2c 와 §4a 사이에 아직 정합이 안 맞은 상태로 보인다 — 이 역시 M3 범위 밖). I2 "백층 = 키층의 30~50%" — 코드가 실제로 쓰는 `0.8`(80%) 과 **다른 수치**다(기존 불일치, R5/디머 대역 영역 — 이 SPEC 의 Out of Scope, spec.md §4). §4b C1/C3 은 색 규칙뿐, 디머 퍼센트 언급 없음 |
| 3 | `docs/proposals/song-structure-lighting-standard.md` §6.1~6.3 | §6.2 "기구는 세 층으로 역할을 나눈다 — 앰비언트 워시/텍스처/에너지"는 **다른 어휘 체계**(key/back/effect/side/wash/mover 와 매핑되지 않는다)이고 퍼센트도 없다. §6.3 은 색 규칙 |
| 4 | `.moai/specs/` 기존 SPEC(특히 SPEC-LDDESIGN-001) | `grep -rn "side_pct\|wash_pct\|mover_pct\|side.*pct\|wash.*pct\|mover.*pct" server/ docs/ .moai/specs/` → SPEC-LDRENDER-001 자신의 문서 밖 매치 0건 |
| 5 | 코드(`song_cue_composer.py` `_dimmer_data`/`_D_LEVEL_ROWS`) | `back_pct = key_pct * 0.8 if plan.rig_profile.has_layer("back") else None`(`:735`) 가 **유일한** 역할별 파생 공식이다 — "back" 전용으로만 쓰여 왔다. `_D_LEVEL_ROWS`(R5, Out of Scope)는 구간 전체 디머 대역이지 역할별 분배가 아니다 |
| 6 | `.moai/reports/t499`·`t498` | t499 verdict.md: "KEY·FOH·SIDE·WASH·MOVER·STROBE 는 전 곡 전 큐에서 같은 값"(송신이 안 갈라졌다는 **결함 서술**일 뿐 목표 비율 서술 아님). t498: 같은 결함의 실기 재현. 둘 다 "어떻게 나눠야 하는가"에 답하지 않는다 |

**결론**: side/wash/mover 디머 퍼센트의 **정본 산출 규칙이 어디에도 없다**.
유일하게 존재하는 역할별 공식(`key_pct * 0.8`)은 "back" 전용으로만 쓰여
왔고, 이것을 side/wash/mover 에 그대로 복제하면 — **디머 값이 서로 같아져
AC-001 의 "서로 다른 값 버킷"에 전혀 기여하지 못한다**(`ldrender_gate.layer_diversity`
가 역할이 아니라 **직렬화된 상태 값**으로 버킷을 세기 때문 — `server/design/ldrender_gate.py:106-126`
코드 판독. side 가 back 과 같은 0.8×key 를 받으면 둘은 **같은 버킷**이다).
지시문의 "숫자를 지어내지 마라"는 이 지점에서 특히 날카롭다 — back 비율을
그대로 베끼는 것은 숫자를 안 지어내는 것처럼 보이지만, 그 숫자가 만드는
**효과**(새 버킷 생성)는 정확히 발명한 것과 같다.

**블로커 — 아래 § 블록 참조**: side/wash/mover 의 퍼센트는 구현하지 않았다
(결정 없이는 진행 불가). 대신 **결정과 무관한 ①·②(위)와 아래 측정·테스트만
완료**했다.

#### ④ `_SINGLE_LAYER_WARNING` 판정

M2 §Gaps 가 "재확인이 필요하면 후속으로 갱신" 으로 남겨 둔 결정을 이번에
내렸다. **판정: 이제 부정확하다 — 갱신한다.** 근거: 이 문구(와 같은 자리의
확인 카드 `why` 문구, `session.py:7723` 둘 다)는 "단일 레이어 축퇴 상태에서
검증되지 않는 분리 연출"의 **전수**를 나열하는 문장이다(기존 네 역할
key/back/effect/audience 를 **전부** 나열했었다 — "일부 대표"가 아니라
"전부" 였다). M2 가 역할을 일곱으로 넓혔고, `_role_dimmer_value_lines`(위 ②)는
층 매핑이 비면(단일 레이어) **어느 역할도** 줄을 못 낸다 — 즉 단일 레이어
축퇴에서 미검증인 역할은 이제 일곱 전부다. 넷만 적힌 문구는 "전수 나열"이라는
그 문장 자신의 전제를 어긴다(부분집합으로 전체를 사칭). 두 자리
(`_SINGLE_LAYER_WARNING`, `_confirm_song_layer_mapping` 의 `why`) 모두
"Front/Back/Beam/Audience" → "Front/Back/Beam/Audience/Side/Wash/Mover" 로
고치고, 전자를 단언하는 기존 잠금 테스트(`test_web_session.py:5604`)를 같은
문자열로 갱신했다(조용히 깨뜨리지 않음, 후자는 잠금 테스트가 없어 문구만 고침).

#### ⑤ AC-001 오프라인 판독 — t499 8곡 재현(실기 그룹), 결과: 전곡 LIT<3

**방법론(이 워크트리의 제약)**: 원곡 오디오(`src/sample music/*.mp3`)가 이
워크트리에 없다(`find . -iname "*.mp3" -o -iname "*.wav"` → scipy 테스트
픽스처 외 0건) — t499 의 `rehearse_song.py`/`run_all.py` 를 그대로 돌릴 수
없다. 대신 t499 가 이미 DSP 로 측정해 **커밋해 둔**
`.moai/reports/t499/runs/<곡>/analysis.json`(BPM·구간 D레벨 — 실측값)을
`ConfirmedSongAnalysis`/`BpmResolution` 으로 직접 재구성해 세션에 꽂았다
(`.moai/reports/t501/measure_ac001_8songs.py`, DSP 재실행 없음·확정값
재사용). 이 대체가 판정에 영향을 안 주는 이유: 디머 렌더링은 곡 내용(BPM·구간
D레벨)에 의존하지만 **역할 집합**(`role_pct` 가 key/back 만 채운다는 사실)에는
의존하지 않는다 — 그 스크립트 머리말에 코드 판독 근거를 적었다. 실기 그룹은
t498 run0 실측(`REAL_GROUPS`, 1~18번)을 그대로 썼다.

```
$ uv run python .moai/reports/t501/measure_ac001_8songs.py
Club Diver: 구간 큐 14개 · LIT≥3 0개 · LIT<3 14개 · 색 1종 · 효과줄 0 · 경고 YES
Cut and Run: 구간 큐 18개 · LIT≥3 0개 · LIT<3 18개 · 색 1종 · 효과줄 0 · 경고 YES
Ice cream: 구간 큐 8개 · LIT≥3 0개 · LIT<3 8개 · 색 1종 · 효과줄 0 · 경고 YES
Morning: 구간 큐 14개 · LIT≥3 0개 · LIT<3 14개 · 색 1종 · 효과줄 0 · 경고 YES
Rain: 구간 큐 13개 · LIT≥3 0개 · LIT<3 13개 · 색 1종 · 효과줄 0 · 경고 YES
Too Cool: 구간 큐 24개 · LIT≥3 0개 · LIT<3 24개 · 색 1종 · 효과줄 0 · 경고 YES
scott-buckley-neon: 구간 큐 18개 · LIT≥3 0개 · LIT<3 18개 · 색 1종 · 효과줄 0 · 경고 YES
걸그룹DinoDino_C_max최고품질: 구간 큐 11개 · LIT≥3 0개 · LIT<3 11개 · 색 2종 · 효과줄 0 · 경고 YES
```

8곡 전부 **모든** 구간 큐가 LIT<3(AC-001 FAIL, 전수) — t499 가 측정한 "최대
2버킷"(전체 값 + BACK) 과 일치한다. **예측과 일치**: ②의 구조적 가드로 side/
wash/mover 는 애초에 role_pct 값이 없어 렌더링되지 않으므로, M3 단독으로는
LIT 버킷이 늘지 않는다 — side/wash/mover 디머 퍼센트 결정(위 R4 블로커)이
풀려야 AC-001 이 PASS 할 길이 열린다. 산출물(`ac001_8songs.json`/`.txt`)을
`.moai/reports/t501/` 에 저장했다.

#### 뮤테이션 — 새 단언에 걸기 (§3.3 규율, 4건)

| 뮤테이션 | 대상 | 죽인 테스트 | 결과 |
|---|---|---|---|
| A: `_DIMMER_DELTA_EXCLUDED_ROLES` 에서 `"effect"` 제거 | `song_cue_render.py` | `test_effect_role_is_never_emitted_even_if_role_pct_has_a_value` | 1건 FAIL(의도대로 빨강) |
| B: `_role_group_numbers` 를 `numbers[role]=...`→`numbers.setdefault(role,...)`(first-wins 로 완화) | `song_cue_render.py` | `test_every_role_with_a_role_pct_value_gets_its_own_group_line`·`test_a_role_with_multiple_matching_groups_uses_the_last_one_iteration_order_wins`·`test_last_matching_entry_per_role_wins` | 3건 FAIL(의도대로 빨강) |
| C: `CueDimmerData.__post_init__` 에서 `role_pct` 값 검증 루프 제거 | `song_cue_composer.py` | `test_role_pct_is_validated_like_key_pct`·`test_role_pct_rejects_an_empty_string_role_key` | 2건 FAIL(의도대로 빨강) |
| D: `_apply_pre_drop_darkness` 의 `dataclasses.replace` 에서 `role_pct=_role_pct_for(...)` 인자 제거 | `song_cue_composer.py` | `test_complete_bundle_contains_section_axis_data_and_structured_timing`(신규 role_pct 단언) | 1건 FAIL(의도대로 빨강) |

4건 전부 `PYTHONDONTWRITEBYTECODE=1` 로 실행, 백업 파일과 `diff`(치환 적용
확인) 후 복원해 `git diff --stat` 으로 원복을 확인했다. 복원 후 전체 지정
범위 재실행 PASS(아래 회귀 절). 각 뮤테이션이 **의도한 테스트만** 빨갛게
만들었다(axis 분리 확인, §3.3 "자극은 재려는 축 하나만 건드려야 한다").

#### AC-LDRENDER-003 — 바이트 동일성 (단일 레이어 리그, 두 버전 직접 대조)

**직접 단위 테스트**(`TestSingleLayerIsByteIdentical`, 4개 role_pct 조합 ×
파라미터화): `layer_mapping=()` 이면 `role_pct` 에 무엇이 있어도 항상 빈
튜플 — `_role_group_numbers(())` 가 항상 `{}` 이므로 구성상 참인 속성.

**고치기 전/후 직접 대조**(`.moai/reports/t501/ac003_byte_diff.py` —
이 워크트리에 원곡 오디오가 없어 전체 세션 리허설로 두 "트리"를 비교할 수
없다는 §방법론 참조에 따라, `a037ad24`(M3 착수 베이스라인) 의
`_back_layer_value_lines` 소스를 `git show` 로 읽어 격리 네임스페이스에서
실행하고 지금 트리의 `_role_dimmer_value_lines` 와 같은 입력에 대조):

```
$ uv run python .moai/reports/t501/ac003_byte_diff.py
single_layer_no_mapping: OK  old=()  new=()
back_only_lit: OK  old=("Group 12 ; Attribute 'Dimmer' At 64",)  new=("Group 12 ; Attribute 'Dimmer' At 64",)
back_only_dark: OK  old=()  new=()
back_only_no_dimmer_role_pct_fallback: OK  old=("Group 12 ; Attribute 'Dimmer' At 40",)  new=("Group 12 ; Attribute 'Dimmer' At 40",)
mapping_with_only_side_no_role_pct_value: OK  old=()  new=()
mib_premove_untouched: OK  old=()  new=()

PASS — 6건 전부 바이트 동일.
```

**세션 레벨 회귀**(기존 통합 시험, 변경 없이 그대로 PASS — back-only 리그의
바이트 동일성을 end-to-end 로 증명): `test_confirmed_back_layer_adds_group_dimmer_lines_to_the_bundle`
(`test_web_session.py`) — back 역할 1개만 매핑된 리그에서 5개 LIT 큐 전부
`back_pct == key_pct*0.8` 을 확인하는 기존 시험, 수정 없이 PASS.

#### 테스트 — 신규 `server/tests/test_song_cue_role_dimmer_t501.py` (19개) + 기존 파일 보강

```
$ PYTHONDONTWRITEBYTECODE=1 uv run pytest server/tests/test_song_cue_role_dimmer_t501.py -q
...................
19 passed in 0.15s
```

`test_song_cue_composer.py` 의 기존 `test_complete_bundle_contains_section_axis_data_and_structured_timing`
에 `role_pct` 단언 1줄을 보강(새 테스트 함수 아님 — §3.5 "불변식 팔의 값어치는
뮤테이션에서 드러난다"에 따라 기존 드롭-앞-어둠 경로를 직접 겨눈다). `test_web_session.py`
의 기존 단일 레이어 경고 잠금 테스트 1건을 ④의 문구 변경에 맞춰 갱신.

#### 회귀 — 지정 범위 + 전체 스위트

```
$ PYTHONDONTWRITEBYTECODE=1 uv run pytest server/tests/test_layer_mapping_effect_role.py server/tests/test_layer_mapping_foh_front.py server/tests/test_design_rig.py server/tests/test_song_cue_color_emission.py server/tests/test_song_cue_white_preset_t453.py server/tests/test_seeded_song_apply.py server/tests/test_song_cue_composer.py server/tests/test_song_cue_arc_t462.py server/tests/test_song_cue_role_dimmer_t501.py server/tests/test_ldrender_gate.py server/tests/test_web_session.py server/tests/test_dedupe_value_lines_t476.py server/tests/test_song_readback_props_t479.py -q
609 passed in 4.73s
```

전체 스위트(베이스라인 `a037ad24`, M2 완료 시점 기록값 14400 passed/35 skipped):

```
$ PYTHONDONTWRITEBYTECODE=1 uv run pytest server/tests -q -p no:cacheprovider
14419 passed, 35 skipped in 200.80s
```

14400 → 14419(**+19, 신규 테스트 수와 정확히 일치** — 삭제 0 · 교체 0 ·
전체 FAIL 0건). **중간 1회차**(이 측정 전 별도 전체 스위트 실행)에서
`test_spatial_context.py::TestBulkPropertyReads::test_a_1_6_0_responder_falls_back_silently_to_the_single_reads`
1건이 FAIL 했다 — 벽시계 타임스탬프(`read_at`)가 두 호출 사이 초 경계를
넘어간 **플레이키**(해당 파일은 이 SPEC 이 건드리지 않는다, 코드 판독으로
확인). 그 1건만 격리 재실행해 PASS 확인(`1 passed in 0.38s`) 후 전체
스위트를 재실행한 것이 위 14419(FAIL 0) 결과다.

#### 린트/포맷

```
$ uv run ruff check server/design/song_cue_composer.py server/design/song_cue_render.py server/web/session.py server/tests/test_song_cue_role_dimmer_t501.py server/tests/test_song_cue_composer.py server/tests/test_web_session.py .moai/reports/t501/measure_ac001_8songs.py .moai/reports/t501/ac003_byte_diff.py
All checks passed!
$ uv run ruff format --check <동일 목록>
전부 이미 포맷됨
```

#### @MX 태그

`_role_dimmer_value_lines`(신규 공개 함수, `song_cue_render.py`)의 fan_in 은
1(`reviewed_song_commands` 호출 1곳) — ANCHOR 요건(fan_in>=3) 미달, ANCHOR
미부착. `_role_group_numbers`(fan_in 1, `_role_dimmer_value_lines` 내부
호출만)도 동일. `_role_pct_for`(`song_cue_composer.py`, fan_in 2 —
`_dimmer_data`·`_apply_pre_drop_darkness`)도 미달. 위험한 패턴(goroutine
류·복잡도>=15) 없음 — WARN 불필요. 전부 테스트 커버(신규 19건 + 간접 커버) 있어
TODO 불필요.

#### M3 이 하지 않은 것 (§Gaps — 명시)

- **side/wash/mover 디머 퍼센트는 구현하지 않았다** — 정본 산출 규칙이
  어디에도 없다(위 §R4 측 효과 6단계 검색 표). 블로커로 리드에 보고한다
  (아래 § 블록). M3 는 ①·②(데이터 모델+렌더 함수, 결정과 무관) 와 ④·⑤
  (경고 문구·측정, 결정과 무관)만 완료했다.
- **AC-001 은 여전히 FAIL 이다** — side/wash/mover 결정이 풀리지 않는 한
  M3 가 할 수 있는 한도 내에서는 이것이 구조적 상한이다(⑤ 측정 참조). M4
  (색 송신)도 side/wash/mover 그룹에 색을 보내려면 같은 그룹 번호 배선을
  재사용하지만, 디머가 0(또는 미점등)이면 `layer_diversity` 의 LIT 필터에
  애초에 안 걸려 색이 있어도 버킷에 안 들어간다 — **디머 % 결정은 M4 의
  선행 조건이기도 하다**(색만으로는 못 돌아간다).
- **M5(effect 기구 분리)는 하지 않았다** — `_DIMMER_DELTA_EXCLUDED_ROLES` 의
  `"effect"` 제외는 이 함수 하나의 방어적 가드일 뿐, 공유 `fids`(색·포지션·
  페이저)에서 effect 기구를 빼는 일(REQ-007 본 범위)은 손대지 않았다.
- **AC-001 8곡 측정은 원곡 오디오 없이 analysis.json 재구성으로 수행했다** —
  §⑤ 방법론 참조. 8곡 전부 코드 판독 예측(§R4 효과)과 일치하는 결과를 냈지만,
  이것은 "다른 경로로도 같은 결론에 도달했다"는 교차검증이지 "원곡 오디오로
  직접 재현했다"는 것과는 등급이 다르다(이 트리의 제약, §방법론).
- **`groups`-heuristic 경로**(실측상 프로덕션 미사용, M2 §Gaps 와 동일 — M3
  도 바꾸지 않았다)는 이번에도 건드리지 않았다.

## §블로커 — side/wash/mover 디머 퍼센트 산출 규칙 미정 (REQ-LDRENDER-001 잔여)

**상태(해소, 2026-10-01)**: 리드가 아래 옵션 (a)(back 비율 재사용)를 확정했다
— 권장안이었던 옵션 (b)(역할별 감독 결정 요청) 대신 (a)를 명시 선택했다.
리드 결정 전문: "side/wash/mover dimmer = key_pct × 0.8, i.e. the SAME
existing formula as back ... layer brightness contrast belongs to R5 (next
SPEC)". 아래 표가 이미 적어 둔 옵션 (a)의 "치명적 결함"(AC-001 기여 못함 —
side 가 back 과 같은 값을 받으면 같은 버킷)은 리드가 **알고도** 받아들인
것이다 — 층 간 구분은 디머가 아니라 M4(색)가 내기로 명시했다. 구현·측정은
아래 "M3 완료(결정 a)" + "M4" 절 참조. 이하 표는 블로커 당시 제시한 선택지
기록으로 보존한다(변경 없음, 결정 근거 추적용).

**상태(블로커 당시)**: 구현 불가(결정 없이는 숫자를 지어내지 않는다는 지시문의 명시 제약).
배차서 구속: "정본 어디에도 산출 규칙이 없으면 그 부분을 구현하기 전에 멈추고
2-3개 구체적 선택지를 제시하라."

**왜 블로커인가(①·②와 분리 가능함을 확인한 뒤의 결론)**: `_role_dimmer_value_lines`
(위 ②)는 `role_pct` 에 값이 있는 역할만 렌더링하므로, side/wash/mover 값을
비워 둔 채로도 ①·②·④·⑤ 는 결정과 **독립적으로** 완결됐다(회귀·뮤테이션·
AC-003 바이트 동일성 전부 PASS). 그러나 AC-001(REQ-001 의 핵심 완료 조건)은
side/wash/mover 퍼센트 없이는 구조적으로 도달 불가능하다(§⑤ 측정이 실측으로
확인) — 그래서 M3 는 "완료"가 아니라 "결정 대기로 블록"이다.

**선택지 (3개, 각각 출처·트레이드오프)**:

| | 옵션 (a) back 비율 재사용 | 옵션 (b) 역할별 감독 결정 요청(결정 5) | 옵션 (c) 설계 층 입력 계약으로 전가 |
|---|---|---|---|
| 내용 | `role_pct[role] = key_pct * 0.8` 을 side/wash/mover 에도 동일 적용(back 과 같은 공식 재사용) | R1/R2/R4 처럼 리드 경유로 "side/wash/mover 디머를 back 대비 몇 %로 할지" 새 감독 결정을 요청 | §11 CUE-EX 의 역할별 `Dim` 열처럼, 디자인 인터뷰/곡 설계 명세(`SectionDecision` 상위)에서 역할별 퍼센트를 **입력**으로 받는 축을 새로 연다 |
| 근거 | 코드에 이미 있는 유일한 역할별 공식 재사용(새 공식 발명 아님) | 이 SPEC 자신이 이미 4번 쓴 절차(spec.md §5 결정 1~4) — 선례와 동형 | §11 CUE-EX 의 기존 입력 계약을 그대로 일반화(새 모델 발명 아님) |
| 치명적 결함 | **AC-001 에 기여 못함** — side 가 back 과 같은 값(0.8×key)을 받으면 같은 버킷(`layer_diversity` 가 값으로 버킷을 센다, 코드 판독 위 §R4 참조). "back 전용으로만 검증된 공식을 다른 역할에 복제"는 숫자를 안 지어낸 것처럼 보이지만 효과는 발명과 같다 | 비용 — M4(색 송신) 착수 전 확인 라운드 1회 추가. 단, 이미 확립된 절차라 새 메커니즘 비용은 0 | 비용 최대 — 인터뷰 질문 추가(§2d DI1~DI6 재설계), `SectionDecision`/`song_plan.py` 확장, 사실상 이 SPEC 범위를 넘는 작은 SPEC 분량의 작업 |
| 구현 범위 | `_dimmer_data` 한 곳(`_role_pct_for` 확장) | `_dimmer_data` 한 곳 + 결정 수신 후 값 반영(구현 자체는 (a)와 같은 크기, 입력값만 감독 결정) | `song_plan.py`/인터뷰/`song_cue_composer.py` 다수 지점 |
| 권장 여부 | 비권장(치명적 결함으로 목표 미달) | **권장** — 이미 감독이 유사 결정을 4회 내린 선례(spec.md §5)와 같은 절차, 비용 최소, 발명 없음 | 비권장(이 카드 범위를 크게 벗어남 — 별도 SPEC 분량) |

**권장**: 옵션 (b) — R2(결정 3, 층→색 배정)와 **같은 모양의 질문**이다.
"back+mover=지배색, side+wash=보조색, key=중립"처럼 **디머에서도 지배/보조
구분을 둘지**(예: back+mover 를 80%, side+wash 를 50% 등)를 감독에게 물으면
된다 — 색 배정 결정이 이미 back/mover 를 "지배", side/wash 를 "보조"로
묶어 뒀으므로(spec.md §3.2 [HARD], 감독 결정 3), 디머 결정도 그 축을 따라
"지배 그룹 비율 vs 보조 그룹 비율" 둘만 물으면 충분할 가능성이 높다(발명
아님 — 이미 난 결정의 연장을 확인하는 질문).

### M3 완료(결정 a) — side/wash/mover 디머 = back 과 같은 식 (카드 t501, 리드 결정 2026-10-01)

**구현**: `song_cue_composer.py` `_role_pct_for(key_pct, back_pct, *, plan=None)` —
`plan` 이 주어지면 `plan.rig_profile.has_layer(role)` 이 참인
`side`/`wash`/`mover` 각각에 `key_pct * 0.8`(back 과 바이트 동일한 식, 새
상수 없음)을 채운다. `plan` 이 없으면(레거시 호출부 호환) side/wash/mover 는
이전처럼 비운다 — 발명 아니라 생략 규율은 그대로다. `_dimmer_data`(정상·
블랙아웃 두 분기)와 `_apply_pre_drop_darkness`(드롭 앞 어둠, `plan` 파라미터
신설 + 호출부 1곳 갱신) 양쪽이 `plan=plan` 을 넘긴다 — role_pct 가 두 자리
에서 갈라지지 않는다(M3 ①의 기존 공유 헬퍼 규율 유지).

코드 주석 인용(새 상수 미도입 표시): `_BACK_RATIO_ROLES`/`_role_pct_for`
독스트링에 "리드 결정 t501 M3 — 층 간 밝기 대비는 R5(후속 SPEC)로 이월한다"
를 명시했다(지시문 그대로, `song_cue_composer.py:720` 부근).

**테스트**: `server/tests/test_song_cue_role_dimmer_t501.py`
`TestRolePctForBackRatioReuse`(신규 6개) — side/wash/mover 가 back 과 같은
비율을 받는지, 리그에 없는 역할은 생략되는지(0 아님), `plan=None` 레거시
호환, 블랙아웃 0 전파, effect/audience 여전히 비움, `_role_dimmer_value_lines`
까지 닿는 종단 확인.

```
$ PYTHONDONTWRITEBYTECODE=1 uv run pytest server/tests/test_song_cue_role_dimmer_t501.py -q
.........................
25 passed in 0.17s
```

**뮤테이션(2건, §3.3 규율)**:

| 뮤테이션 | 대상 | 죽인 테스트 | 결과 |
|---|---|---|---|
| E: `for role in ("side","wash","mover")` → `("side","wash")`(mover 제거) | `_role_pct_for` | `test_side_wash_mover_get_the_same_ratio...`·`test_blackout_zero_key_pct_propagates...`·`test_end_to_end_role_dimmer_value_lines...` | 3건 FAIL(의도대로 빨강) |
| F: `key_pct * 0.8` → `key_pct * 0.5`(리드 결정 수치 변조) | `_role_pct_for` | `test_side_wash_mover_get_the_same_ratio...`·`test_a_role_absent_from_the_rig_is_omitted...`·`test_end_to_end_role_dimmer_value_lines...` | 3건 FAIL(의도대로 빨강) |

두 뮤테이션 모두 적용 후 대상 테스트만 빨갛게 만들고(axis 분리 확인)
`diff` 로 치환을 확인한 뒤 원본으로 복원, 복원 후 지정 범위 재실행 PASS.

**AC-001 효과(측정, 아래 M4 §AC-001 재측정 참조)**: 디머만으로는 버킷이
여전히 최대 2개다(`measure_dimmer_only_8songs.py` 8곡 전부 "디머전용 최대버킷
2") — 블로커 당시 예측·치명적 결함 분석과 정확히 일치한다. AC-001 의 실제
PASS 는 M4(색)가 만든다.

### M4 — 색 송신 확장 + 층→색 배정 (카드 t501, REQ-LDRENDER-004/005/006, 감독 결정 3)

#### 구현

`server/design/song_cue_render.py`:

- `_COLOR_ACCENT_ROLES = ("side", "wash")` — 보조색 델타 대상. `back`/`mover`
  는 베이스라인(전체 `fids`, 지배색)이 이미 그 값이라 델타를 내지 않는다
  (REQ-004 "네 그룹을 하나로 합친 선택에 동일 색 한 줄만" 의 구현 — 새 분기가
  아니라 "델타가 필요 없다"는 사실 자체가 병합이다).
- `_role_color_value_lines(cue, layer_mapping, palette, dominant_rgb)` —
  `_role_dimmer_value_lines`와 같은 그룹-주소 패턴(fid 불요, RG5). `len(palette)
  < 2`(단색)면 역할 배정 자체를 하지 않는다(REQ-004 본문 조건 그대로, 웜화이트
  배정도 안 함 — 발명 금지). `accent_rgb == dominant_rgb`(REQ-006, `color_usage
  =single`)면 side/wash 델타를 생략한다 — 값-비교 하나로 "별도 분기 불필요"를
  구현(REQ-006 본문 그대로 인용). `key` 도 지배색이 이미 웜화이트면 같은 이유로
  생략한다. `effect`/`audience` 는 배정 축(`_COLOR_ACCENT_ROLES`+`"key"`)에
  없어 구조적으로 제외된다(`_DIMMER_DELTA_EXCLUDED_ROLES`와 같은 이중 가드
  철학 — R3 HARD 불변식, M5 를 기다리지 않는다).
- `_group_color_apply_command(group_no, rgb)` — `_color_apply_command`의 그룹
  주소 쌍둥이(`Group <n> ; Attribute 'ColorRGB_R'...`).
- `_song_color_value_lines`에 `layer_mapping: Sequence[...] = ()` 5번째 인자
  추가(끝에 추가 — 기존 위치 인자 호출 전부 호환). 베이스라인/W채널/흰색
  프리셋 로직은 그대로 두고(단일 종료점으로 리팩터 — 4개였던 return 지점을
  1개로 합쳐 모든 경로가 역할 배정을 동일하게 거치게 했다), 함수 끝에서
  `_role_color_value_lines` 결과를 항상 추가한다(흰색 프리셋 실패 여부와
  무관 — 별개 축).

**§6.3 집계 플래그 코드 주석**(지시문 요구): `_role_color_value_lines`
독스트링에 "key 의 웜화이트는 이 SPEC 이 §6.3 '최대 2개(지배 1+액센트 1)'
집계 밖(중립 기준광)으로 읽는다... 이 읽음은 유일한 해석이 아니라고 spec.md
가 명시 플래그했다(재확인 여지)"를 그대로 인용해 남겼다(`song_cue_render.py`
`_role_color_value_lines` 함수 바로 위).

**웜화이트 RGB 사용처**: `_COLOR_NAMES.resolve_color_name("Warm White")` →
`(100, 75, 40)` — `color_names.py` `COLOR_PALETTE_SEQUENCE` 의 **기존** 첫
항목(새 RGB 미발명). 인용: `color_names.py:34` `("Warm White", (100, 75, 40))`.

호출부 1곳 갱신: `reviewed_song_commands`가
`_song_color_value_lines(cue, fids, w_fids, white_presets, layer_mapping)`
로 `layer_mapping`을 넘긴다.

#### 테스트 — 신규 `server/tests/test_song_cue_role_color_t501.py` (16개)

```
$ PYTHONDONTWRITEBYTECODE=1 uv run pytest server/tests/test_song_cue_role_color_t501.py -q
................
16 passed in 0.15s
```

`TestRoleColorValueLines`(11개) — back/mover 델타 없음·side/wash 보조색·key
웜화이트, effect/audience 영구 제외, 단색 팔레트 전체 생략, 3번째 이후 색
미발화, single-모드 중복 생략(accent==dominant), 지배색이 이미 웜화이트인
경우 key 델타 생략, 보조색 미해석 시 생략(key 는 영향 없음), 매핑에 없는
역할 생략, 빈 매핑 전체 생략, non-section 전체 생략, 그룹 주소 문법,
유일 문자열(dedupe) 보존. `TestSongColorValueLinesIntegration`(3개) —
베이스라인+역할 배정 공존·순서, `layer_mapping=()` 레거시 바이트 동일,
미해석 지배색의 실패 보고(역할 배정 0건).

**기존 테스트 시그니처 변경(보고 의무)**: `test_song_cue_color_emission.py`
`TestTheFabricatedControl.test_silencing_the_colour_helper_brings_the_measured_defect_back`
의 monkeypatch 람다가 4개 위치 인자(`cue, fids, w_fids=, white_presets=`)만
받았는데, `_song_color_value_lines`가 5번째 인자(`layer_mapping`)를 추가로
받게 되면서 `reviewed_song_commands`의 호출(5개 위치 인자)과 불일치해
`TypeError`가 났다. 람다에 `layer_mapping=()` 키워드 매개변수를 추가해
고쳤다 — **단언(assert) 자체는 바뀌지 않았다**, 모킹 대상 함수의 시그니처가
늘어 대역도 같이 늘려야 했을 뿐이다(옛 동작 `((), None)` 반환은 동일).
`palette[0]`-only 동작 자체의 의도된 종료는 이 시그니처 변경과 무관하다 —
베이스라인 로직은 그대로 두고 역할 배정을 **추가**했을 뿐(REQ-004 본문
"오늘처럼 palette[0] 하나만 내고 나머지를 버리는 동작은 종료한다"는 이
추가로 충족된다 — 기존 단일-색 전용 송신을 "역할별 다색 송신"으로 대체).

#### 회귀 — 지정 범위 + 전체 스위트

```
$ PYTHONDONTWRITEBYTECODE=1 uv run pytest server/tests/test_layer_mapping_effect_role.py server/tests/test_layer_mapping_foh_front.py server/tests/test_design_rig.py server/tests/test_song_cue_color_emission.py server/tests/test_song_cue_white_preset_t453.py server/tests/test_seeded_song_apply.py server/tests/test_song_cue_composer.py server/tests/test_song_cue_arc_t462.py server/tests/test_song_cue_role_dimmer_t501.py server/tests/test_song_cue_role_color_t501.py server/tests/test_ldrender_gate.py server/tests/test_web_session.py server/tests/test_dedupe_value_lines_t476.py server/tests/test_song_readback_props_t479.py -q
631 passed in 6.28s
```

전체 스위트(베이스라인 `a5601e6e`, M3 완료 시점 기록값 14419 passed/35 skipped):

```
$ PYTHONDONTWRITEBYTECODE=1 uv run pytest server/tests -q -p no:cacheprovider
14441 passed, 35 skipped in 244.41s
```

14419 → 14441(**+22, 신규 테스트 수(6+16)와 정확히 일치** — 삭제 0 · 교체 0 ·
전체 FAIL 0건, skipped 35 불변).

`test_song_cue_white_preset_t453.py`·`test_song_cue_color_emission.py`
전량 PASS(지시문 요구 — 흰색 프리셋/W채널 로직·color_usage 분기 무변경 확인).

#### 린트/포맷

```
$ uv run ruff check server/design/song_cue_composer.py server/design/song_cue_render.py server/tests/test_song_cue_role_dimmer_t501.py server/tests/test_song_cue_role_color_t501.py server/tests/test_song_cue_color_emission.py .moai/reports/t501/measure_ac001_8songs.py .moai/reports/t501/measure_ac004_8songs.py .moai/reports/t501/measure_dimmer_only_8songs.py
All checks passed!
$ uv run ruff format --check <동일 목록>
전부 이미 포맷됨
```

#### @MX 태그

`_role_color_value_lines`(신규, `song_cue_render.py`)의 fan_in 은 1(`_song_
color_value_lines` 내부 호출 1곳) — ANCHOR 요건(fan_in>=3) 미달. `_group_
color_apply_command`(fan_in 1)도 동일. `_role_pct_for`는 M3 기존 fan_in 2
(`_dimmer_data`·`_apply_pre_drop_darkness`)에서 변동 없음(호출부 수는 그대로,
새 키워드 인자만 추가). 위험한 패턴(goroutine 류·복잡도>=15) 없음 — WARN
불필요. 전부 테스트 커버(신규 22건: M3 6 + M4 16) 있어 TODO 불필요.

#### AC-001 재측정 — 8곡 전부, M3+M4 반영 (`.moai/reports/t501/measure_ac001_8songs.py` 재실행)

readout.py 자신의 머리말이 예고한 경계("SIDE-ALL·WASH-ALL·MOVER-ALL... 은
이번 송신에 안 나와서 펼침 규칙을 안 만들었다, 나오면 멈춘다")가 M4 에서
처음 발생했다 — `_role_group_numbers`의 "마지막 항목이 이긴다" 규율로 역할별
디머/색 델타가 SIDE-ALL(7)/WASH-ALL(10)/MOVER-ALL(13) 그룹을 겨냥하기
시작했기 때문(M2 progress.md 선례와 동형). readout.py 자신은 건드리지
않고(M1 PRESERVE 경계), **측정 스크립트 전용 패치**(`measure_ac001_8songs.py`
`_members_with_all_group_expansion`)로 -ALL 그룹을 서브그룹 합집합(SIDE-ALL
= SIDE-L ∪ SIDE-R 등 — 콘솔 명명 관행, 지어낸 값 아님)으로 펼쳤다.

```
$ uv run python .moai/reports/t501/measure_ac001_8songs.py
Club Diver: 구간 큐 14개 · LIT≥3 13개 · LIT<3 1개 · 색 4종 · 효과줄 0 · 경고 YES
  위반: 색 수 4개(기준 2~3)
  위반: LIT 층 3 미만인 구간 큐 1개: 12.5
  위반: 효과 요청 12건 · 페이저 제안 0큐 → 송신 효과 줄 0
Cut and Run: 구간 큐 18개 · LIT≥3 17개 · LIT<3 1개 · 색 3종 · 효과줄 0 · 경고 YES
  위반: LIT 층 3 미만인 구간 큐 1개: 16.5
  위반: 효과 요청 16건 · 페이저 제안 0큐 → 송신 효과 줄 0
Ice cream: 구간 큐 8개 · LIT≥3 7개 · LIT<3 1개 · 색 4종 · 효과줄 0 · 경고 YES
  위반: 색 수 4개(기준 2~3)
  위반: LIT 층 3 미만인 구간 큐 1개: 6.5
  위반: 효과 요청 6건 · 페이저 제안 0큐 → 송신 효과 줄 0
Morning: 구간 큐 14개 · LIT≥3 13개 · LIT<3 1개 · 색 3종 · 효과줄 0 · 경고 YES
  위반: LIT 층 3 미만인 구간 큐 1개: 12.5
  위반: 효과 요청 12건 · 페이저 제안 0큐 → 송신 효과 줄 0
Rain: 구간 큐 13개 · LIT≥3 12개 · LIT<3 1개 · 색 3종 · 효과줄 0 · 경고 YES
  위반: LIT 층 3 미만인 구간 큐 1개: 11.5
Too Cool: 구간 큐 24개 · LIT≥3 23개 · LIT<3 1개 · 색 4종 · 효과줄 0 · 경고 YES
  위반: 색 수 4개(기준 2~3)
  위반: LIT 층 3 미만인 구간 큐 1개: 18.5
  위반: 효과 요청 36건 · 페이저 제안 0큐 → 송신 효과 줄 0
scott-buckley-neon: 구간 큐 18개 · LIT≥3 17개 · LIT<3 1개 · 색 4종 · 효과줄 0 · 경고 YES
  위반: 색 수 4개(기준 2~3)
  위반: LIT 층 3 미만인 구간 큐 1개: 16.5
  위반: 효과 요청 16건 · 페이저 제안 0큐 → 송신 효과 줄 0
걸그룹DinoDino_C_max최고품질: 구간 큐 11개 · LIT≥3 10개 · LIT<3 1개 · 색 4종 · 효과줄 0 · 경고 YES
  위반: 색 수 4개(기준 2~3)
  위반: LIT 층 3 미만인 구간 큐 1개: 3.5
  위반: 효과 요청 9건 · 페이저 제안 0큐 → 송신 효과 줄 0
```

**집계**: 전체 구간 큐 120개(14+18+8+14+13+24+18+11) 중 112개(93.3%)가
LIT≥3 로 PASS(M3 착수 전 0/120 에서 상승). **실패 8개는 전부 같은 모양** —
곡마다 정확히 1개, 전부 `.5` 큐 번호(클라이맥스 복귀 큐,
`_climax_return`)이고 전부 LIT=2. 원인은 §Gaps 참조(아래, 이 카드 범위 밖
잔여로 보고).

#### Part C 항목 2 — 디머-전용 버킷 수 (리드 예측 "밝기 대비 0" 검증)

```
$ uv run python .moai/reports/t501/measure_dimmer_only_8songs.py
Club Diver: 구간/큐 14개 · 전체상태(색+디머) 최소버킷 2 · 디머전용 최대버킷 2 · 디머전용>=3 인 큐 0개
Cut and Run: 구간/큐 18개 · 전체상태(색+디머) 최소버킷 2 · 디머전용 최대버킷 2 · 디머전용>=3 인 큐 0개
Ice cream: 구간/큐 8개 · 전체상태(색+디머) 최소버킷 2 · 디머전용 최대버킷 2 · 디머전용>=3 인 큐 0개
Morning: 구간/큐 14개 · 전체상태(색+디머) 최소버킷 2 · 디머전용 최대버킷 2 · 디머전용>=3 인 큐 0개
Rain: 구간/큐 13개 · 전체상태(색+디머) 최소버킷 2 · 디머전용 최대버킷 2 · 디머전용>=3 인 큐 0개
Too Cool: 구간/큐 24개 · 전체상태(색+디머) 최소버킷 2 · 디머전용 최대버킷 2 · 디머전용>=3 인 큐 0개
scott-buckley-neon: 구간/큐 18개 · 전체상태(색+디머) 최소버킷 2 · 디머전용 최대버킷 2 · 디머전용>=3 인 큐 0개
걸그룹DinoDino_C_max최고품질: 구간/큐 11개 · 전체상태(색+디머) 최소버킷 2 · 디머전용 최대버킷 2 · 디머전용>=3 인 큐 0개
```

**판정(측정 지지 — 리드 예측과 일치)**: 디머 값만으로는 8곡 전부 LIT 버킷이
**단 한 번도** 3개에 도달하지 못한다(디머전용>=3 인 큐 0개, 전 곡). 값은
항상 둘뿐이다(`key_pct`·`key_pct*0.8`) — back/mover/side/wash/effect(값
있으면)가 전부 같은 두 번째 값으로 뭉친다. **결론 문장(측정이 지지하는
한에서만)**: 「층 대비는 색, 밝기 대비는 최대 2버킷(0 이 아니라 "추가
기여 0") — R5 이월」. 원문 지시의 "밝기 대비 0"은 "back 대비 추가되는
대비가 0"이라는 뜻으로 읽을 때만 정확하다 — key 자체와 나머지의 2-버킷
구분은 M2 이전부터 있던 것(back 전용 공식의 유산)이라 "0"을 "버킷이 1개"로
읽으면 과장이다. 이 구분을 명시하는 것이 "측정이 지지하는 것만 쓴다" 규율이다.

#### 상태 키 실측 증거 (Part C 항목 3 — pos·dim·rgb 전체가 키)

Club Diver 큐 12(절정)와 12.5(절정 복귀) 의 `role_view` 를 직접 찍었다
(`uv run python` 1회성 조회, `.moai/reports/t501/`에 스크립트로 남기지
않음 — 디버그 1회성 조회이지 재사용 하네스가 아니다):

```
cue 12 (section):
  back  : {'pos': '2.30', 'dim': 80.0,  'rgb': (5.0, 20.0, 100.0)}    (Blue, 지배색)
  mover : {'pos': '2.30', 'dim': 80.0,  'rgb': (5.0, 20.0, 100.0)}    (Blue, 지배색 — back 과 동일 dim·rgb, 같은 버킷)
  side  : {'pos': '2.30', 'dim': 80.0,  'rgb': (100.0, 75.0, 40.0)}   (Warm White, 보조색 — dim 은 back 과 같은 80 인데 rgb 가 달라 **다른 버킷**)
  wash  : {'pos': '2.30', 'dim': 80.0,  'rgb': (100.0, 75.0, 40.0)}   (side 와 동일 dim·rgb, 같은 버킷)
  key   : {'pos': '2.30', 'dim': 100.0, 'rgb': (5.0, 20.0, 100.0)} 외 (6/14기구) + {..., 'rgb': (100.0,75.0,40.0)} (8/14기구)
  effect: {'pos': '2.30', 'dim': 80.0,  'rgb': (5.0, 20.0, 100.0)} (블라인더 점등 — BLIND 그룹, LIT)
```

**직접 증거**: `side`(dim=80, rgb=웜화이트)와 `back`(dim=80, rgb=블루)은
**디머 값이 완전히 같은데**(`_role_dimmer_value_lines` 의 §M3 결정대로)
`layer_diversity`(`json.dumps(state, sort_keys=True)` 직렬화 비교)가 이
둘을 **서로 다른 버킷**으로 센다 — 상태 키가 `dim` 단독이 아니라
`{pos, dim, rgb}` 전체 딕셔너리이기 때문이다(`ldrender_gate.py:106-126`
코드 판독, M3.md §R4 측 효과가 이미 지목한 바로 그 메커니즘 — M4 가 이것을
실제로 가동시켰다).

#### M4 이 하지 않은 것 (§Gaps — 명시)

- **클라이맥스 복귀 큐(`climax_return`)의 디머/색 역할 배정 미적용** — AC-001
  이 곡당 1개씩(전 8곡, 총 8/120 구간 큐) FAIL 하는 유일한 원인. 근본 원인
  (코드 판독): `_climax_return()`(`song_cue_composer.py:1024`)가 "포지션·색·
  효과는 다시 싣지 않는다 — 콘솔이 앞 큐 값을 그대로 이어 간다"는 docstring
  대로 `dimmer`/`color` 필드를 **그대로 들고 온다**(climax 큐와 동일 객체).
  그런데 `_song_color_value_lines`/`_role_dimmer_value_lines` 는 둘 다
  `cue.kind != "section"` 이면 **아무 줄도 안 낸다**(역할 배정은 물론
  베이스라인도) — 반면 `position_cue_bundle` 의 **전체 기구 디머 줄**은
  `cue.kind` 와 무관하게 `plan.dimmer`(=`cue.dimmer.key_pct`)가 있으면 항상
  나간다. 그 결과 climax_return 큐에서: 디머는 **전체 기구가 key_pct 로
  재동기화**(back/mover/side/wash 도 80→100 처럼 역할 구분이 사라진 값으로
  되돌아간다)되고, 색은 **역할 배정이 재발화하지 않아** 직전 상태를 그대로
  들고 가는데, 우연히 key 역할이 물리적으로 두 콘솔 그룹(KEY+FOH)에
  걸쳐 있고 그중 하나(FOH)는 M4 의 key 델타 대상이 아니라서(마지막 매칭
  그룹만 델타를 받는다, `_role_group_numbers` 동점 규율) 베이스라인 색(지배
  색)을 그대로 들고 있다 — 그 결과 back+mover+effect(블루) 대 side+wash+key
  일부(웜화이트) 로 색이 딱 2그룹으로만 갈리고, 디머가 전부 100 으로
  재동기화돼 추가 구분을 못 만든다 → LIT 버킷 2개(AC-001 미달). **이 카드
  범위 밖**: 배차서 Part A/B 는 각각 "back 비율 재사용"과 "REQ-004 색 배정"
  만 지시했다 — climax_return 자체의 재발화 로직 확장(M3/M4 의 역할 함수를
  `cue.kind in ("section", "climax_return")` 으로 넓히거나, `_climax_return()`
  이 `role_pct`/`color`를 재계산해 넣는 등)은 새 구조 변경이라 배차서가
  지시하지 않은 범위다 — 리드에게 후속 카드로 보고한다(8/120, 6.7%, 곡마다
  정확히 1개).
- **AC-004(a) "곡당 고유 송신 RGB 2~3개" 미달(측정값 3~4개, 8곡 중 4곡이
  4개)** — 원인(측정): `ldrender_gate.color_count`(및 AC-004(a) 본문의
  문자 그대로 읽기)는 큐 전체에 걸쳐 송신된 **모든** RGB 를 센다 — 웜화이트도
  포함한다. 반면 §6.3 "동시 최대 2개"(AC-004(b))는 spec.md §3.2 [HARD] 가
  웜화이트를 **그 집계 밖**으로 읽기로 명시했다(§6.3 플래그). 이 SPEC 의
  REQ-004 가 `key` 에 웜화이트를 새로 배정하면서, **곡 전체 고유 RGB 카운트
  (AC-004a)에는 그 제외가 적용되지 않는다** — 그래서 웜화이트 1종이 항상
  "고유 RGB" 집합에 추가되어, 챔음 2~3종이던 값이 3~4종으로 밀렸다(§6.3 의
  "동시 2개" 자체는 8곡 전부 PASS — 아래 AC-004 측정 참조, 웜화이트 제외
  기준으로는 전부 2 이하). 이것은 REQ-004(웜화이트 신설)와 AC-004(a)의 문자
  그대로의 수치(2~3) 사이의 **긴장**이다 — 발명으로 해소하지 않는다(AC-004a
  기준을 "웜화이트 제외 2~3" 으로 조용히 재해석하거나, 반대로 REQ-004 의
  웜화이트 배정을 되돌리는 것 둘 다 이 카드의 권한 밖). 리드에게 플래그로
  보고한다 — AC-004(a)의 "2~3"이 웜화이트 포함인지 제외인지 명문화가
  필요하다.
- **실제 곡 오디오로 직접 재현하지 않았다** — M3 와 동일한 이 워크트리의
  제약(§방법론, mp3/wav 0건)을 이어받는다. t499 analysis.json 재구성 교차
  검증이고, 원곡 오디오 직접 재현과는 등급이 다르다.
- **AC-005(REQ-006, `color_usage=single`/`per_chorus`)는 단위 함수 수준으로만
  확인했다** — `_role_color_value_lines` 직접 호출 테스트(단일 모드 중복 생략
  확인)는 있지만, `compose_song_cue_bundle`→`reviewed_song_commands` 전체
  경로로 `color_usage=single` 인 합성 곡을 끝까지 돌리는 새 종단 테스트는
  추가하지 않았다(기존 `test_song_cue_white_preset_t453.py`/`test_song_cue_
  color_emission.py` 회귀는 전량 PASS — 무회귀 확인은 됐지만 새 종단 확인은
  아니다).
- **M5(effect 기구 분리)는 이 카드 범위 밖** — 공유 `fids`(베이스라인 색·
  디머·포지션·페이저가 모두 겨냥하는 선택)에서 effect 기구를 빼는 일은 아직
  하지 않았다. M4 는 **역할별 델타** 경로에서만 effect 를 구조적으로
  제외했을 뿐(`_COLOR_ACCENT_ROLES`에 "effect" 없음, M3 의 `_DIMMER_DELTA_
  EXCLUDED_ROLES`와 같은 이중 가드) — 베이스라인 자체(효과 기구 포함 여부)는
  M5 의 몫 그대로다.
- **`groups`-heuristic 경로**(실측상 프로덕션 미사용, M2/M3 §Gaps 와 동일) —
  이번에도 건드리지 않았다.

### M3 후속 — climax_return (카드 t501, M4 §Gaps 1 해소, REQ-LDRENDER-001/004)

**착수 베이스라인**: `git fetch origin WT-ldrender-run` → `git merge --ff-only`
→ HEAD `61b1695b`(M4 완료 커밋) — `git log --oneline -1` 로 확인.

#### 결정 — kind 허용 집합을 명시 열거로 확장(`!= "section"` 반전 금지)

`server/design/song_cue_render.py` 에 공유 상수
`_ROLE_VALUE_LINE_KINDS: frozenset[str] = frozenset({"section", "climax_return"})`
를 새로 선언하고, 아래 네 함수의 `cue.kind != "section"` 가드를
`cue.kind not in _ROLE_VALUE_LINE_KINDS` 로 바꿨다 — 지시문이 요구한 "명시
허용집합 우선(`!=` 반전 지양)" 그대로다. `mib_premove`/블랙아웃
(`cue.dimmer.blackout`, kind 자체는 여전히 `"section"`)은 이 집합 밖에
머물러 AC-001 명시 예외(acceptance.md AC-001: "블랙아웃 큐... 및 MIB
사전이동 큐... 는 명시 예외")와 바이트 동일하게 보존된다:

| 함수 | 줄 | 바꾼 것 |
|---|---|---|
| `_white_palette_name` | 594 | `!= "section"` → `not in _ROLE_VALUE_LINE_KINDS` |
| `_role_color_value_lines` | 643 | 〃 |
| `_song_color_value_lines` | 725 | 〃 |
| `_role_dimmer_value_lines` | 815 | 〃 |

**이 네 kind(함수 범위를 왜 `_role_color_value_lines`·`_white_palette_name`
까지 넓혔나)**: 배차서 결함 서술은 `_song_color_value_lines`와
`_role_dimmer_value_lines` 둘만 명명했지만, `_song_color_value_lines` 는
내부에서 `_role_color_value_lines`를 호출해 역할 델타를 내므로(`song_cue_
render.py:694` 부근) 그 함수의 kind 가드를 같이 넓히지 않으면
`_song_color_value_lines`쪽 가드만 열어도 역할 델타가 여전히 안 나간다.
`_white_palette_name`은 W 채널(`w_fids`)이 비어 있지 않은 리그에서만 실제로
호출되므로(이 카드의 8곡 측정에선 `w_fids` 가 항상 비어 호출 자체가 없다 —
`server/web/session.py:7604-7613` 코드 판독, `_color_rig_fixture_pairs`가
합성 리그에서 W 능력을 선언받지 못한다) 측정 결과에는 영향이 없지만, 고치지
않으면 W 채널이 있는 리그에서 climax_return 의 흰색 프리셋 recall 줄만
조용히 비선택되는 **잠재 비대칭**이 남는다 — 같은 상수로 네 함수를 함께
닫아 그 비대칭을 없앴다(`server/tests/test_song_cue_climax_return_t501.py`
`TestStubLevelWhitePaletteName` 이 이 결정을 직접 겨눈다).

**`_climax_return()`이 climax 큐 자신의 값을 바이트 동일하게 들고 온다는
근거(인용)**: `song_cue_composer.py:1024-1049` `_climax_return(climax, ...)`
가 `dataclasses.replace(climax, kind="climax_return", cue_number=..., cue_
name=..., fade_seconds=0.0, position=dataclasses.replace(climax.position,
stored=None), fx=CueFxData(...), accents=(), accent_fixture=None, pre_drop_
from=None, mib=CueMibData(), timing=...)` 를 호출한다 — 교체 인자 목록에
`dimmer`도 `color`도 없다. `dataclasses.replace`의미론상 교체하지 않은
필드는 원본 **참조** 그대로 남는다(값 복사조차 아니다) — 이 카드의
`TestComposerIntegration.test_climax_return_dimmer_and_color_are_the_same_
object_as_the_climax_cue`가 `ret.dimmer is climax.dimmer`/`ret.color is
climax.color`(`is`, `==` 아님)로 이 사실을 직접 확인한다. `position`은
`stored=None`으로 **바뀐다**(재송신 안 함, 변경 없음), `fx`는 **명시적으로
빈 값**으로 교체된다(복사가 아니다 — 블라인더가 꺼지는 것 외 새 효과
없음). 그래서 이 함수들이 climax_return 에도 역할별 줄을 내는 것은 새 값을
발명하는 게 아니라 climax 큐 자신이 이미 가진 값을 재사용하는 것이다.
`_climax_return()`의 독스트링도 이 구분(조립 층의 "다시 계산 안 함" vs
송신 층의 "다시 내는가")을 명시하도록 갱신했다(song_cue_composer.py).

#### 진단 — 실패 원인 실측(M4 §Gaps 1 의 가설을 코드 실행으로 대조)

M4 §Gaps 1 은 "FOH 그룹이 key 델타 대상이 아니라서 베이스라인 색을 그대로
들고 있다"는 **코드 판독 가설**을 적어 뒀다. 착수 전 Club Diver 큐 12(절정)
/12.5(절정 복귀) 의 실제 `role_view` 를 1회성 진단 스크립트로 직접 찍어
대조했다(스크립트는 쓰고 지웠다 — 아래 수치는 그 출력의 인용):

```
cue 12 (section):     layer_diversity = 4
  back/mover : dim=80  rgb=Blue(5,20,100)        → 버킷 A
  side/wash  : dim=80  rgb=WarmWhite(100,75,40)  → 버킷 B
  key        : dim=100 rgb=Blue 외 rgb=WarmWhite (물리적으로 KEY+FOH 혼재) → 버킷 C·D
  effect     : dim=80(점등) rgb=Blue              → 버킷 A 와 겹침(기존 동작)

cue 12.5 (climax_return, 고치기 전): layer_diversity = 2
  back/mover : dim=100(전체 기구 재동기화) rgb=Blue        → 버킷 A′
  side/wash  : dim=100(전체 기구 재동기화) rgb=WarmWhite   → 버킷 B′
  key        : dim=100 rgb=Blue 외 rgb=WarmWhite            → A′/B′ 와 **병합**(dim 도 100 으로 같아졌으므로)
  effect     : dim=0(블라인더 꺼짐, LIT 아님 — 집계 제외)
```

**정정(측정이 가설을 대체)**: 진짜 원인은 "FOH 가 베이스라인을 들고
있어서"가 아니라 — **색은 트래킹으로 멀쩡히 2그룹(Blue/WarmWhite)으로 남아
있는데, 역할 델타 줄이 재발화하지 않아 디머가 전체 `key_pct`(100)로
재동기화되면서 `key` 역할의 상태(dim=100, rgb=Blue 또는 WarmWhite)가
back/mover·side/wash 의 재동기화된 상태(마찬가지로 dim=100)와 **우연히
같아져 버킷이 병합**된 것이다. `{pos,dim,rgb}` 전체가 상태 키이므로(M4 §Part
C 항목 3 의 상태 키 실측과 같은 메커니즘), dim 이 유일한 분기였던 자리가
사라지면 rgb 만 같아도 바로 병합된다. 고친 뒤(아래 §검증)에는 역할 델타가
back/mover=80, side/wash=80 으로 다시 갈라지며 cue 12 와 바이트 동일한
`layer_diversity=4` 가 나온다 — 측정으로 직접 확인(§검증 1).

#### 테스트 — 신규 `server/tests/test_song_cue_climax_return_t501.py` (15개)

두 축으로 나눴다: 대역(stub) 수준 11개(`_role_dimmer_value_lines`·
`_role_color_value_lines`·`_song_color_value_lines`·`_white_palette_name`
각각 "climax_return 이 section 과 같은 줄을 낸다" + "mib_premove 는 여전히
아무 줄도 안 낸다"의 두 팔, 블랙아웃 key_pct<=0 가드 보존 1건 추가) +
`compose_song_cue_bundle` 실조립 통합 4개(climax_return 큐가 정확히 1개
생성됨, `dimmer`/`color` 가 climax 큐와 같은 객체 참조(`is`), 역할 디머/색
줄이 climax 큐와 바이트 동일, 일반 section 큐(Finale)는 이 변경과 무관함을
대조로 확인).

```
$ PYTHONDONTWRITEBYTECODE=1 uv run pytest server/tests/test_song_cue_climax_return_t501.py -q
...............
15 passed in 0.19s
```

#### 뮤테이션 — 새 단언에 걸기 (§3.3 규율, 5건 — 축 분리 확인)

| # | 변조 | 대상 | 죽은 테스트 수 | 확인 |
|---|---|---|---|---|
| A | `_ROLE_VALUE_LINE_KINDS` 를 `{"section"}` 으로 축소(climax_return 제거, 네 함수 동시 영향) | `song_cue_render.py:588` | 7(stub 5 + 통합 2) | `diff`로 치환 확인 → 복원 → `diff` 로 원복 확인(무차이) → 지정 범위 재실행 PASS |
| B | `_role_dimmer_value_lines` 가드만 `!= "section"` 으로 되돌림(다른 셋은 그대로) | `:815` | 정확히 2(디머 축 stub+통합만) | 상동, 색 관련 테스트 13개는 전부 그대로 초록 — 축 분리 확인 |
| C | `_song_color_value_lines` 가드만 되돌림 | `:725` | 정확히 3(song_color stub 2 + 통합 1) | 상동, 다른 12개 초록 |
| D | `_white_palette_name` 가드만 되돌림 | `:594` | 정확히 1 | 상동, 다른 14개 초록 |
| E | `_role_color_value_lines` 가드만 되돌림 | `:643` | 정확히 3(role_color stub 1 + song_color 가 그 함수를 내부 호출하므로 song_color stub 1 + 통합 1) | 상동, 다른 12개 초록 |

5건 전부 `PYTHONDONTWRITEBYTECODE=1`로 실행, 매 회차 `diff /tmp/song_cue_
render.py.orig server/design/song_cue_render.py` 로 (1) 변조 적용 확인
(2) 복원 후 무차이 확인 두 번씩 거쳤다. 각 뮤테이션이 **정확히 그 축의
테스트만** 죽여(3.3 "자극은 재려는 축 하나만 건드려야 한다") 공유 상수 하나
뒤에 네 개의 독립된 가드가 각자 자기 몫을 지키고 있음을 확인했다 — A(상수
자체)가 7개를 죽이고 B+C+D+E(개별 가드)가 합쳐 2+3+1+3=9인데 7과 안 맞는
이유는 겹침이다: `_song_color_value_lines`가 `_role_color_value_lines`를
내부 호출하므로 C·E 뮤테이션은 서로 다른 지점이지만 둘 다
`test_climax_return_emits_the_same_lines_as_section`(song_color stub) 를
함께 죽인다 — 축이 "함수 하나"가 아니라 "그 함수가 실제로 거치는 호출
경로"이므로 당연한 중복이고, 공허 단언이 아니라는 것은 B/D 가 각자
독립적으로 정확한 카디널리티(2·1)를 낸 것으로 교차 확인된다.

#### 검증 1 — AC-001 재측정, 8곡 전부 120/120 (기존 측정 스크립트 재사용)

배차서가 지정한 세 스크립트(`measure_ac001_8songs.py`·`measure_dimmer_
only_8songs.py`·`measure_ac004_8songs.py`)를 한 글자도 안 고치고 그대로
재사용했다 — 출력 파일명에만 `_climaxfix` 접미사를 끼워 넣는 드라이버
(`.moai/reports/t501/run_climaxfix_measurements.py`, `pathlib.Path.
write_text` 를 실행 중에만 가로챈다)를 새로 써서 M4 가 이미 저장해 둔
`ac001_8songs.json`/`.txt`·`dimmer_only_8songs.json`·`ac004_8songs.json`
(고치기 전 값)을 덮어쓰지 않았다.

```
$ uv run python .moai/reports/t501/run_climaxfix_measurements.py
Club Diver: 구간 큐 14개 · LIT≥3 14개 · LIT<3 0개 · 색 4종 · 효과줄 0 · 경고 YES
Cut and Run: 구간 큐 18개 · LIT≥3 18개 · LIT<3 0개 · 색 3종 · 효과줄 0 · 경고 YES
Ice cream: 구간 큐 8개 · LIT≥3 8개 · LIT<3 0개 · 색 4종 · 효과줄 0 · 경고 YES
Morning: 구간 큐 14개 · LIT≥3 14개 · LIT<3 0개 · 색 3종 · 효과줄 0 · 경고 YES
Rain: 구간 큐 13개 · LIT≥3 13개 · LIT<3 0개 · 색 3종 · 효과줄 0 · 경고 no
Too Cool: 구간 큐 24개 · LIT≥3 24개 · LIT<3 0개 · 색 4종 · 효과줄 0 · 경고 YES
scott-buckley-neon: 구간 큐 18개 · LIT≥3 18개 · LIT<3 0개 · 색 4종 · 효과줄 0 · 경고 YES
걸그룹DinoDino_C_max최고품질: 구간 큐 11개 · LIT≥3 11개 · LIT<3 0개 · 색 4종 · 효과줄 0 · 경고 YES
```

**AC-001 — 8곡 전체 before→after**

| 곡 | before(M4) LIT≥3/전체 | after(이 카드) LIT≥3/전체 |
|---|---|---|
| Club Diver | 13/14 | **14/14** |
| Cut and Run | 17/18 | **18/18** |
| Ice cream | 7/8 | **8/8** |
| Morning | 13/14 | **14/14** |
| Rain | 12/13 | **13/13** |
| Too Cool | 23/24 | **24/24** |
| scott-buckley-neon | 17/18 | **18/18** |
| 걸그룹DinoDino | 10/11 | **11/11** |
| **합계** | **112/120(93.3%)** | **120/120(100%)** |

남은 경고(색 수 4개·효과 송신 0줄)는 이 카드 범위 밖(AC-004(a) 웜화이트
집계 플래그·M6 효과 송신 — M4 §Gaps 2 와 동일, 손대지 않았다)이고 AC-001
자체(LIT 층 3 미만 경고)는 8곡 전부 자취를 감췄다.

**디머-전용 대조(리드 예측 "밝기 대비는 R5 이월" 재확인 — 변화 없음을
기대하고 쟀다)**:

```
$ (run_climaxfix_measurements.py 의 두 번째 구간, 위 §검증 1 명령과 같은 1회 실행)
Club Diver: 구간/큐 14개 · 전체상태(색+디머) 최소버킷 4 · 디머전용 최대버킷 2 · 디머전용>=3 인 큐 0개
(8곡 전부 디머전용 최대버킷 2, >=3 인 큐 0개 — M4 측정값과 바이트 동일)
```

전체상태(색+디머) 최소버킷이 2(M4, climax_return 이 끌어내린 전곡 최솟값)
→ 4(이 카드, climax 큐와 동일하게 복원)로 올랐지만, 디머-전용 축은
**건드리지 않았다**(여전히 최대 2, >=3 인 큐 0개) — 리드 예측("층 대비는
색, 밝기 대비는 R5 이월")이 이 카드 이후에도 그대로 지켜짐을 재확인한다.

**AC-004 대조(변화 없음을 기대하고 쟀다 — color_count/색변화/역할 확인
전부 M4 값과 바이트 동일)**: 8곡 전부 고유 RGB 수·색변화 횟수·역할별 수신
색 확인(`back==dominant`·`side==accent`·`key==warmwhite` 전부 `True`)이
M4 측정값과 일치 — climax_return 이 색은 이미 트래킹으로 멀쩡했으므로
(§진단 참조) 색 집계 축은 이 카드로 달라질 이유가 없었고, 측정도 그것을
확인했다.

산출물(수정 없이 재사용한 세 스크립트의 climaxfix 출력): `.moai/reports/
t501/ac001_8songs_climaxfix.json`·`.txt`, `dimmer_only_8songs_climaxfix.json`,
`ac004_8songs_climaxfix.json` — M4 가 저장한 동일 이름의 원본은 변경하지
않았다(`git status` 로 확인, `M` 표시 없음).

#### 회귀 — 지정 범위 + 전체 스위트

```
$ PYTHONDONTWRITEBYTECODE=1 uv run pytest server/tests/test_layer_mapping_effect_role.py server/tests/test_layer_mapping_foh_front.py server/tests/test_design_rig.py server/tests/test_song_cue_color_emission.py server/tests/test_song_cue_white_preset_t453.py server/tests/test_seeded_song_apply.py server/tests/test_song_cue_composer.py server/tests/test_song_cue_arc_t462.py server/tests/test_song_cue_role_dimmer_t501.py server/tests/test_song_cue_role_color_t501.py server/tests/test_ldrender_gate.py server/tests/test_web_session.py server/tests/test_dedupe_value_lines_t476.py server/tests/test_song_readback_props_t479.py server/tests/test_song_cue_climax_return_t501.py -q
646 passed in 5.98s
```

M4 기록값(지정 범위) 631 → 646(**+15, 이 카드 신규 테스트 수와 정확히
일치** — 삭제 0 · 교체 0 · 전체 FAIL 0건).

전체 스위트(베이스라인 `61b1695b`, M4 완료 시점 기록값 14441 passed/35
skipped):

```
$ PYTHONDONTWRITEBYTECODE=1 uv run pytest server/tests -q -p no:cacheprovider
14456 passed, 35 skipped in 233.67s
```

14441 → 14456(**+15, 신규 테스트 수와 정확히 일치** — 삭제 0 · 교체 0 ·
전체 FAIL 0건, skipped 35 불변).

#### 린트/포맷

```
$ uv run ruff check server/design/song_cue_render.py server/design/song_cue_composer.py server/tests/test_song_cue_climax_return_t501.py .moai/reports/t501/run_climaxfix_measurements.py
All checks passed!
$ uv run ruff format --check <동일 목록>
4 files already formatted
```

#### @MX 태그

`_ROLE_VALUE_LINE_KINDS`(신규 모듈 상수, `song_cue_render.py`)의 fan_in 은
4(`_white_palette_name`·`_role_color_value_lines`·`_song_color_value_lines`·
`_role_dimmer_value_lines`) — ANCHOR 요건(fan_in>=3) 충족, 독스트링에 이미
`@MX:ANCHOR` 수준 서술(결함 인용·설계 근거·REASON)을 담았으나 명시 태그
문법(`// @MX:ANCHOR: ...` 류)은 Python 모듈 주석 관행과 맞춰 생략했다(이
저장소의 기존 `_COLOR_ACCENT_ROLES`/`_DIMMER_DELTA_EXCLUDED_ROLES` 도 같은
형태의 서술형 주석만 쓰고 명시 `@MX` 태그 문법을 달지 않는다 — 일관성
유지). 위험한 패턴(goroutine 류·복잡도>=15) 없음. 전부 테스트 커버(신규
15건) 있어 TODO 불필요.

#### 이 카드가 하지 않은 것 (§Gaps — 명시)

- **AC-004(a) 웜화이트 집계 플래그(M4 §Gaps 2)는 그대로 미해소** — 이 카드
  범위 밖(배차서가 climax_return 결함만 지시).
- **M6(효과 송신)·M5(effect 기구 분리)는 여전히 미착수** — 8곡 전부 효과
  요청 대비 송신 0줄(Rain 제외)이 그대로 남아 있다(배차서 범위 밖).
- **진단 스크립트는 저장하지 않았다** — 착수 전 Club Diver 큐 12/12.5 상태를
  직접 찍어 본 1회성 조회이고(위 §진단), 재사용 하네스로 남기지 않았다(M4
  의 "상태 키 실측 증거"와 같은 1회성 조회 선례).
- **원곡 오디오 직접 재현 없음** — M3/M4 와 동일한 이 워크트리 제약(mp3/wav
  0건) 계승.
- **W 채널(`w_fids`)이 있는 리그에서의 climax_return 흰색 프리셋 recall 은
  실측 대상이 아니었다** — 이 8곡 측정에서 `w_fids` 가 항상 비어 있어
  `_white_palette_name`의 climax_return 분기가 실제로 호출되지 않는다(위
  "함수 범위" 절 참조). `TestStubLevelWhitePaletteName` 단위 테스트로만
  확인했고, `compose_song_cue_bundle`→`reviewed_song_commands` 종단 경로로
  W 채널이 있는 합성 리그를 돌리는 새 테스트는 추가하지 않았다.

### M5 — 효과 기구 분리 (카드 t501, REQ-LDRENDER-007/008, M2 의 effect 역할 재사용) — 블로커 보고(아래) → **리드 결정 (g) 로 해소, §M5 완료 절 참조**

**착수 베이스라인**: `git merge --ff-only origin/WT-ldrender-run` → HEAD `4d93e1dc`
(M3 후속 climax_return 완료 커밋) — `git rev-parse --short HEAD`로 확인.

#### 배차서 지시 6단계 검색 — 결론: 효과 역할 그룹의 fid 멤버십을 읽는 production 경로가 어디에도 없다

| # | 자리 | 결과 |
|---|---|---|
| 1 | `.moai/specs/` 기존 SPEC(특히 SPEC-LDDESIGN-001·SPEC-COPILOT-GROUPGEN-001) | GROUPGEN SPEC §A.4 M0 게이트(실측, 2026-09)가 **그룹 멤버십 판독 채널 자체가 없음**을 확정했다: "`Group 13 'All'`은 `exec`이 `OK`인 실사용 그룹인데 `query_state`는 `childCount: 0`을 준다... **그룹 멤버십은 오브젝트 트리 경로로 노출되지 않는다**"(`SPEC-COPILOT-GROUPGEN-001/spec.md:104-105`, `progress.md:43-44`·`:248`·`:255` 재확인 — `state …/13` → `childCount: 0`, `state …/14` → `childCount: 0`). LDDESIGN REQ-053/054(HAZE 안전 큐)도 그룹 **번호**(Block/Release) 주소만 쓰고 fid 멤버십을 요구하지 않는다 |
| 2 | `server/design/rig.py` `RigLayers`/`fids_for` | `RigLayers.mapping`(역할→fid)은 **존재**하지만(`:251-262`), 채우는 유일한 두 경로(`RIG_LAYER_SOURCE_DECLARED`/`RIG_LAYER_SOURCE_GROUP_HEURISTIC`, `_build_layers`, `:359-393`) 중 `declared_layers`는 그룹 **번호**만 나르고(`session.py:7580-7584`, `str(entry["role"]): (int(entry["group_no"]),)`), `groups`(그룹이름→fid)는 모든 production 호출부에서 **하드코딩 빈 딕셔너리**다(아래 #3). 즉 `fids_for("effect")`는 오늘 프로덕션 어디서도 비지 않는 값을 낸 적이 없다 |
| 3 | `server/web/session.py`(`_reviewed_song_commands`·`_confirm_song_layer_mapping`) | `grep -rn "build_rig_profile(" server/` → 4개 production 호출부(`session.py:7475`·`:7586`, `concept/compile.py:190`, `orchestrator/tools.py:3324`) **전부** `groups={}`. `state.fids = [fid for fid, _position in fixtures]`(`session.py:7620`)는 `_try_pointing_coordinates`가 돌려주는 **좌표 있는 기구 전부**(effect 기구 제외 없음) — plan.md §B 위험 2가 이미 경고한 바로 그 지점 |
| 4 | `server/orchestrator/tools.py` | `:3324` 동일 패턴(`groups={}`) — 2곳 다 같은 제약 |
| 5 | `.moai/reports/t499/fid_names.json`·`readout.py members()` | `members(group_no)`는 **이름 첫 단어** 매칭으로 fid를 모은다(`readout.py:54-61`). 원본 생성 스크립트(`fid_names.py`) 자신의 머리말이 명시: "콘솔 그룹 풀의 **실제 구성원은 응답기로 못 읽는다**(t498 §6) — 이 표는 **이름 기반 추정**이며, 판독 도구는 그 사실을 **INFERRED**로 표기한다." 즉 이 테이블 자체가 "검증된 멤버십"이 아니라 "이름 규약이 지켜진다는 가정 위의 추정"이라고 스스로 밝힌다 |
| 6 | `server/design/ldrender_gate.py`(M1 이 미리 만든 `effect_group_in_value_lines`) | 이 함수는 **이미 조립된 `Group <n> ; ...` 송신 문자열**에서 그룹 이름이 들어있는 줄을 찾아 플래그하는 **문자열 검사**다(`ldrender_gate.py:168-179`). `position_cue_bundle`/`_preset_recall_command`/`_color_apply_command`가 요구하는 `Fixture <f1> + <f2> + ...`(`mib.py:167`, `song_cue_render.py:1166`·`:1177`)에 들어갈 **fid 목록**을 만들어 주지 못한다 — 역할이 다르다(M1 progress.md 자신이 "선행 유틸, 아직 아무 데도 배선 안 함"으로 명시) |

**production 코드 자신의 결론(2026-10-01 작성, M2 가 이미 적어 둔 것)**:
`_layer_mapping_from_group_children`(`session.py:766-780`) 독스트링 — "Group
**MEMBERSHIP** is not readable from the console (the drilldown wall), so
this records which group carries a role — it **never claims to know the
member fixtures**." 이 SPEC 자신이 M2 단계에서 이미 같은 결론에 도달해
문서화해 두었다 — M5 가 이번에 독립적으로 재확인한 것은 "그 결론이 REQ-007
구현에 실제로 길을 막는다"는 점이다.

#### 왜 "Group 번호"로는 부족한가 — REQ-007 이 요구하는 것은 fid 수준 뺄셈

`_role_dimmer_value_lines`(M3)·`_role_color_value_lines`(M4)는 역할마다
`Group <n> ; Attribute ... At ...` 줄을 **따로** 내는 방식으로 그룹 번호만
있으면 충분했다(RG5, plan.md §B 위험 2가 이미 지적). 그러나 REQ-007은 이와
다른 종류의 요구다 — "비액센트 큐가 공유하는 **`fids` 선택 자체**"
(`reviewed_song_commands`의 `fids` 매개변수, `song_cue_render.py:1189`)에서
effect 역할 기구를 **빼라**는 것이고, 이 `fids`는 `position_cue_bundle`
(`mib.py:167`, `selection = " + ".join(str(fid) for fid in fids)`)·
`_preset_recall_command`(`:1166`)·`_color_apply_command`(`:1177`)가 전부
**개별 fid를 나열한 `Fixture <f1> + <f2> + ...` 문자열**을 만드는 데 직접
쓰인다 — 그룹 번호로 대체할 길이 코드 어디에도 없다(`"Group <n> Except
Group <m>"`류 뺄셈 문법은 이 저장소 어디서도 쓰지 않는다, 전수 grep 확인).
`_DIMMER_DELTA_EXCLUDED_ROLES`(M3)·`_COLOR_ACCENT_ROLES`류 구조적 가드는
**그룹-주소 델타 줄**(`Group <n>` 경로)에서만 effect를 막을 뿐, 공유 `fids`
자체는 오늘도 86대 전체를 그대로 들고 있다 — REQ-007 본 범위(공유 `fids`
자체에서 제외)는 아직 손대지 않았다.

#### 블로커 — effect 역할(BLIND/STROBE/HAZE) 그룹의 fid 멤버십을 얻을 production-safe 경로가 없다

**상태**: 구현 불가(결정 없이는 멤버십을 지어내지 않는다는 배차서의 명시
제약 — "Do not invent a membership source. If membership is genuinely
unavailable in production, STOP and return a blocker report"). M5(REQ-007/
REQ-008) 전체가 이 결정에 막힌다 — REQ-008조차 spec.md 본문이 "REQ-007 적용
후 기준(이전 비점등 상태, 통상 0)"을 요구해 REQ-007 선행 없이는 AC-007의
"경쟁 줄이 존재하지 않는다" 조건을 검증할 수 없다(아래 §AC-007 절 참조).

**선택지 (3개 + 기각 1개, 각각 출처·트레이드오프)**:

| | 옵션 (a) 패치명 기반(fixture `Name` 접두 매칭) | 옵션 (b) 운용자 명시 선언(`groups`/`declared_layers` 확장) | 옵션 (c) 콘솔 그룹 멤버십 직접 판독 | 옵션 (d, 기각) 기구-타입/능력 축 재사용 |
|---|---|---|---|---|
| 내용 | 패치된 기구마다 `Name` 속성을 1회 재조회(읽기 전용)하고, `resolve_layer_role`(`rig.py:146`, 정확 일치+RG5-1 접두 토큰)과 같은 규율로 이름 첫 토큰을 역할에 매칭 — t499 `fid_names.py`가 쓴 바로 그 기법을 production 경로로 승격 | `_build_layers`가 이미 받는 `groups: Mapping[str, Sequence[int]]`(그룹이름→fid) 매개변수를(지금은 production 전부에서 `{}`) 운용자가 레이어 매핑 확인 카드에서 role→fid를 **직접 확인/입력**하도록 확장 — `_confirm_song_layer_mapping`의 role→group_no 확인 패턴과 같은 UX 축 | `query_state`로 그룹의 자식(member fid)을 직접 읽는다 | `RigInventory.capability_fids["effect"]`(패치 선언 능력 축)를 역할 축 대용으로 쓴다 |
| 근거 | 코드에 이미 있는 유일한 기법(새 발명 아님), `resolve_layer_role` 재사용 | 새 멤버십 판독 채널을 발명하지 않는다 — 콘솔이 못 주는 정보를 사람이 확정해 주는, 이 코드베이스가 이미 쓰는 패턴(RG5 우선순위 1위 "operator declaration") | 가장 직접적 — 새 UX 비용 없음 | 이미 측정 배선된 축 재사용 시도 |
| 치명적 결함 | **이름 규약 의존** — 효과 기구 이름이 "BLIND"/"STROBE"/"HAZE"(또는 매칭 접두)로 시작하지 않는 리그에서는 **조용히 제외 실패**(R3 HARD 위반이 FAIL 신호 없이 발생 — t499 자신이 이 테이블을 "INFERRED"로 낮춰 부른 이유와 같다). 또한 이 M5 배차서 자체가 "no console contact"를 명시해 이번 카드 범위에서 새 재조회를 추가할 수 없다 | 비용 — `_confirm_song_layer_mapping` 확인 카드 UX 확장(새 질문/새 입력 형식) 필요, M5 "fids 자체에서 제외"보다 범위가 커진다(레이어-매핑 확인 플로우 자체를 건드림 — plan.md §D 제약이 다루지 않은 새 표면) | **실측으로 확정 불가** — GROUPGEN SPEC M0(실사용 그룹에서도 `childCount: 0`), `_layer_mapping_from_group_children` 독스트링(이 SPEC 자신의 M2 결론)이 **동일 결론**을 두 번 확정했다. 이번 M5는 "no console contact" 제약이라 재확인 시도조차 불가 | **축이 다르다**(plan.md §B 위험 1, HARD 경고) — M1 실측이 이미 확인: 이 저장소의 `CAPABILITY_VOCABULARY`에는 `"effect"` 키 자체가 없어 `capability_fids["effect"]`는 오늘 **항상 빈 집합**이다(M1 progress.md). 설령 채워도 "Strobe/Shutter 속성 선언"과 "BLIND/STROBE/HAZE 그룹 소속"은 다른 사실이라 오분류 위험 |
| 권장 여부 | 비권장(조용한 R3 위반 위험, 이번 카드에서 재조회 불가) | 결정 필요 시 **차선** — 비용은 있으나 발명이 아니다 | 기각(실측 2회 확정) | 기각(축 자체가 다름, HARD 경고 재확인) |

**이 보고서는 권장안을 하나로 좁히지 않는다** — 배차서의 명시 지시("do not
guess")를 따라, (a)와 (b) 둘 다 각자의 비용(은닉 결함 위험 vs UX 확장 범위)을
그대로 리드에게 넘긴다. (c)는 두 차례(GROUPGEN M0 + 이 SPEC 자신의 M2
결론) 독립적으로 반증됐으므로 선택지에서 사실상 제외됐고, (d)는 축
혼동이라는 구조적 결함(plan.md HARD 위험 1)으로 기각한다.

#### AC-LDRENDER-007(블라인더 액센트 상승) — REQ-007 선행 조건 미충족으로 측정 불가

`_accent_fixture_value_lines`(`song_cue_render.py:832-844`)의 현재 "80"
근원은 코드 판독으로 확인했다: `CueAccentFixtureData.dimmer_pct =
float(intent.brightness[0])`(`song_cue_composer.py:982`), `intent =
intent_for_label(labels[cue.section_index])`가 돌려주는
`SectionIntent.brightness`는 §6 표의 **구간 밝기 구간의 하한**이다 — chorus
행은 `(80, 100)`(`section_intent.py:124-126`), `[0]`이 80을 고른다. t498
큐 11(`verdict.md:22` — "Group 4 80 · Group 14(BLIND) 80")에서 관측된
"100→80"은 같은 큐 안에서 전체 기구 디머 줄(100, effect 기구 포함)이 먼저
나가고 액센트 줄(80)이 콘솔 last-wins로 그 뒤를 덮어써 **하강**하는 것이다
— spec.md 본문이 "REQ-007 적용 후 기준(이전 비점등 상태, 통상 0)"을
요구하는 이유가 바로 이것이다: REQ-007이 먼저 effect 기구를 공유 `fids`에서
빼야, 그 기준이 100(전체 기구 값)에서 0(effect 기구가 애초에 값을 안
받음)으로 바뀌고, 그제서야 액센트 줄의 80이 **상승**이 된다. REQ-007이
블록된 채로는 "경쟁 줄(전체 디머)이 존재하지 않는다"(AC-007 측정 조건)를
검증할 방법이 없다 — 억지로 `_accent_fixture_value_lines`만 고치면
독립적으로는 녹색이어도 AC-007이 실제로 요구하는 불변식(공유 `fids` 제외가
선행된 뒤의 상승)을 증명하지 못하는 거짓 PASS가 된다. 그래서 이 카드는
`_accent_fixture_value_lines`를 **건드리지 않았다**.

#### 측정 항목 1-3(8곡 디머/색/포지션/페이저 줄 + 액센트 방향) — 수행하지 않음, 이유

배차서 측정 항목 1("비액센트 큐 중 effect 기구가 점등값을 받는 큐 수")은
현재 트리에서 **코드 판독만으로 자명**하다 — `fids`에 제외 로직이 전혀
없으므로(위 §왜 Group 번호로는 부족한가), 8곡·모든 비액센트 큐에서 효과
기구는 예외 없이 전체 기구 묶음에 포함된 채 디머·색·포지션·페이저 네 값
줄 전부를 받는다(t499 P3′·t498 큐 전체와 바이트 동일한 구조 — 새 리허설로
다시 재도 같은 "0% 제외"가 나올 뿐, 새 정보가 없다). 8곡 표를 만드는 대신
이 코드-구조적 사실을 명시한다 — 억지로 숫자를 지어내지 않는다. 항목 2(액센트
방향)는 위 §AC-007 절 참조. 항목 3(AC-001/AC-004 재측정)은 M5가 `fids`를
바꾸지 않았으므로 M4 측정과 바이트 동일할 것이 코드-구조적으로 보장된다(새
측정이 정보를 안 준다) — 재실행하지 않았다.

#### AC-LDRENDER-015 — t498 오프라인 스위트 재실행하지 않음, 이유

t498의 `judge_a1_a5.py`/`judge_a7.py`/`classify_diff.py`는 `run1_fake_rain_1`/
`run1_fake_rain_2`류 **고정 폴더**를 인자로 받아 읽기만 한다(`judge_a1_a5.py:11`
`R1, R2 = Path(sys.argv[1]), Path(sys.argv[2])`) — 새 리허설 없이 그 스크립트를
돌려도 M5 "적용 후" 증거가 아니라 **M5 이전에 이미 저장된 과거 데이터의
재판정**일 뿐이다(결과는 이전 실행과 바이트 동일할 수밖에 없다). 이 워크트리에
원곡 오디오가 없어(M3/M4가 이미 기록한 제약, find 재확인 0건) 새 리허설로
"이 SPEC 적용 후" 송신 목록을 만들 방법도 없다. 거짓 증거(과거 데이터를 새
증거처럼 제시)를 만들지 않기 위해 재실행을 스킵했다 — M5 구현 자체가
블록됐으므로 "적용 후" 상태가 아직 존재하지 않는다는 사실을 그대로 보고한다.

#### 회귀 — 베이스라인 안정성만 재확인(M5 코드 변경 0)

```
$ unset MOAI_KANBAN MOAI_KANBAN_ID MOAI_KANBAN_LABEL MOAI_KANBAN_LEAD_ADDR MOAI_KANBAN_SETTINGS_INJECTED && PYTHONDONTWRITEBYTECODE=1 uv run pytest server/tests -q -p no:cacheprovider
14456 passed, 35 skipped, 1 warning in 295.80s
```

배차서가 명시한 베이스라인(HEAD `4d93e1dc`, 14456 passed/35 skipped)과
바이트 동일 — M5가 코드를 건드리지 않았으므로 **변경 없음을 재확인**한
것이지, M5 "적용 후" 테스트 결과가 아니다. 뮤테이션은 해당 없음(새 단언
0건, 구현 코드 변경 0건). 린트/포맷도 해당 없음(변경 파일 0건).

#### @MX 태그 — 해당 없음(코드 변경 0)

#### M5 이 하지 않은 것 (§Gaps — 명시)

- **REQ-LDRENDER-007(공유 `fids`에서 effect 기구 제외)은 구현하지 않았다**
  — fid 멤버십 판독 경로 부재(위 §블로커)로 결정 없이는 숫자(fid 목록)를
  지어낼 수 없다.
- **REQ-LDRENDER-008(블라인더 액센트 상승 방향)도 구현하지 않았다** —
  REQ-007 선행 조건 미충족(spec.md 본문 명시), 독립 수정은 거짓 PASS
  위험(위 §AC-007).
- **AC-LDRENDER-006/007 모두 미검증**(FAIL 아님 — 검증 자체가 불가능한
  상태, PASS/FAIL 판정을 내리지 않는다).
- **측정 항목 1-3(8곡 테이블)·AC-015 오프라인 스위트는 수행하지 않았다** —
  각각 "코드-구조적으로 이미 자명"·"거짓 증거 위험" 사유, 위 해당 절 참조.
- **뮤테이션·@MX·린트 다이프는 해당 없음** — 구현 코드 변경이 0건이기
  때문이다.
- **이 블로커는 멤버십 "확보 방법"의 선택이지 멤버십 "읽기 시도"가 아니다**
  — 이번 M5는 "no console contact"가 명시돼 옵션 (a)/(c)의 실측 재시도
  자체도 이 카드 범위 밖이다(결정이 난 뒤 후속 카드가 수행).

### M5 완료(결정 g) — 효과 기구 그룹 주소 영(0) 처리, fid 뺄셈 대신 outcome-equivalent (카드 t501, 리드 결정 2026-10-01)

**전제(위 블로커 절 참조)**: REQ-007 본문이 요구하는 공유 `fids` 자체에서의
fid 뺄셈은 멤버십 판독 경로 부재로 구현 불가(2차 반증). 리드 결정 (g)는
fid 뺄셈을 **하지 않고**, 그룹 주소로 같은 결과(비액센트 큐에서 효과 기구가
어둡다)를 낸다 — `.moai/reports/t501/M5b.md` §해석 노트에 outcome-equivalent
해석을 명시 플래그.

**구현**: `server/design/song_cue_render.py`에 `_effect_group_numbers`(역할
`"effect"` 에 매칭되는 **모든** 콘솔 그룹 번호를 정렬·중복 제거해 모음 —
`_role_group_numbers`의 last-wins 단일값과 다른 축)와
`_effect_dimmer_zero_lines`(비액센트 큐에서 그 그룹들을 전체 기구 디머 줄
**뒤**에 `Group <n> ; Attribute 'Dimmer' At 0`으로 내림, 액센트 큐에서는 그
액센트가 겨냥하는 그룹만 건너뜀, 복귀 큐에서는 `_accent_fixture_value_lines`
가 이미 내는 복귀-0 줄과 겹치지 않도록 그 그룹도 건너뜀)을 신설했다.
`reviewed_song_commands`의 `extra_value_lines` 튜플에 `_role_dimmer_value_lines`
직후(배차서 요구사항 1의 줄 순서: 전체 디머 → 역할 디머(effect=0 포함) →
효과 recall → 액센트) 배선했다. `_role_dimmer_value_lines` 자체(role_pct
경로)는 손대지 않았다 — `test_effect_role_is_never_emitted_even_if_role_pct_has_a_value`
(기존 M3 테스트)가 여전히 통과한다(바이트 동일 가드, 아래 회귀 확인).

**줄 순서 실측**(Rain 큐 11, `.moai/reports/t501/m5_rain_cue10_11_115_extract.txt`):
전체 기구 디머(100) → 역할 디머(Group 4/7/10/13=80) → effect=0(Group 15/16,
Group 14 는 이 큐의 액센트라 건너뜀) → 액센트(Group 14=80, 맨 끝).

**HAZE 캡션(해소, 충돌 없음)**: spec.md REQ-007 본문은 HAZE 도 제외 대상이나
"곡 시작/종료 안전 큐(Block/Release, SPEC-LDDESIGN-001 REQ-053/054)에서는
명시적으로 관리된다"고 적는다. 그 Block/Release 트래킹 필드는 이 송신
경로(`reviewed_song_commands`)가 전혀 쓰지 않는 **별도 시스템**(큐-시트
메타데이터, `server/design/cue_sheet_edit.py` `TRACKING_VALUES`)이다 —
grep 재확인(`grep -rn "Block\|Release" server/design/song_cue_render.py
server/design/song_cue_composer.py` → 0건). 두 축이 겹치지 않아 충돌이
없다. 추가로 실측(`.moai/reports/t241/verdict.md` §2, 기종 표):
헤이저(Look Unique 2.1, Mode 0 2ch)는 애초에 `Dimmer` 애트리뷰트가 **없다**
(채널은 Haze1·Blower1 뿐, `Dimmer ✗`로 표에 명시) — `Group <n> ; Attribute
'Dimmer' At 0`은 그 기구에 아무 애트리뷰트도 겨누지 못하는 무해한 명령이다.
오늘도 이미 전체 기구 디머 줄이 같은 방식으로 HAZE 에 가닿아 왔다(같은
무해성의 선례, 사고 보고 0건). BLIND(✓)/STROBE(✓)는 Dimmer 가 있어 실제로
꺼진다. **결론**: 충돌 없음 → BLIND/STROBE/HAZE 전부 포함했다(배차서
요구사항 3 "If no conflict, include HAZE").

**해석 노트(명시 플래그)**: REQ-007 문면("공유 `fids` 선택 자체에서 effect
기구를 제외")의 **직역이 아니다** — 공유 `fids`(색·포지션·페이저 줄이
겨냥하는 선택)는 여전히 86대 전체를 들고 있다. (g)가 달성하는 것은
**outcome-equivalent**: 비액센트 큐에서 effect 기구가 어둡다(디머=0)는
결과는 동일하되, 그 경로가 fid 뺄셈이 아니라 그룹 주소 override(last-wins)
다. AC-LDRENDER-006의 문면("4종 값 줄 전부에서 effect 기구가 빠진다")은
**디머 축만** 충족하고 색·포지션·페이저 축은 여전히 공유 `fids`를 거친다
— 이 AC 를 "전면 PASS"로 보고하지 않는다(아래 §AC 매핑). spec.md 문구
쪽 정정이 필요하면 sync 단계에서 manager-spec 이 처리한다 — 이 카드는
spec.md 본문을 고치지 않았다.

**테스트**: `server/tests/test_song_cue_effect_zero_t501_m5.py`(신규 20개) —
`_effect_group_numbers`(집계·정렬·중복 제거·bool 가드, 6개),
`_effect_dimmer_zero_lines`(비액센트/액센트/복귀/연속-액센트/kind 가드/
byte-identical fallback, 9개), `reviewed_song_commands` 통합(줄 순서,
t498 큐 11 재현 고침 확인, 복귀 큐 중복 없음, effect 미매핑 바이트 동일,
4개) + 보조 1개. RED→GREEN 확인: 구현 전 손으로 호출해 `AttributeError`
(함수 미존재)로 RED, 구현 후 전부 GREEN.

```
$ PYTHONDONTWRITEBYTECODE=1 uv run pytest server/tests/test_song_cue_effect_zero_t501_m5.py -q
....................
20 passed in 0.16s
```

**뮤테이션(6건, §3.3 규율 — 각 1축만 건드림, diff 로 적용 확인 후 복원)**:

| 뮤테이션 | 대상 | 죽인 테스트(수) | 결과 |
|---|---|---|---|
| A: 액센트/복귀 그룹 제외 분기 제거(`pass`로 치환) | `_effect_dimmer_zero_lines` | 5건 | FAIL(의도대로) |
| B: `cue.kind not in _ROLE_VALUE_LINE_KINDS` 가드 제거 | 〃 | 2건(mib_premove·blackout kind) | FAIL |
| C: `key_pct <= 0` 가드 제거 | 〃 | 2건(blackout·None key_pct) | FAIL |
| D: `sorted(numbers)` → `tuple(numbers)`(정렬 제거) | `_effect_group_numbers` | 7건(순서 의존 단언 전부) | FAIL |
| E: `set` → `list`(중복 제거 제거) | 〃 | 1건(중복 입력 전용) | FAIL |
| F: `reviewed_song_commands`에서 배선 비활성화(`effect_zero_lines = ()`) | `reviewed_song_commands` | 2건(통합 테스트) | FAIL |

6건 전부 적용 후 대상 테스트만 빨갛게 만들고(axis 분리 확인), 원본과 `diff`
로 적용을 재확인한 뒤 복원, 복원 후 `test_song_cue_effect_zero_t501_m5.py`
20/20 재통과 확인. 생존 뮤턴트 0건.

**회귀 — 전체 스위트**:

```
$ PYTHONDONTWRITEBYTECODE=1 uv run pytest server/tests -q -p no:cacheprovider
14476 passed, 35 skipped, 1 warning in 215.34s
```

베이스라인(M3 후속, HEAD `4d93e1dc`) 14456 passed/35 skipped 대비 **+20
passed, 0 removed, skip 변화 0** — 신설 테스트 20개와 정확히 일치(순증
20, 지운 검사 0). `server/design/song_cue_render.py`·기존 M3/M4/climax_return
테스트 파일(`test_song_cue_role_dimmer_t501.py`·`test_layer_mapping_effect_role.py`
·`test_song_cue_role_color_t501.py`·`test_song_cue_climax_return_t501.py`
·`test_ldrender_gate.py`·`test_songcue_accent_ladder_t382.py`·
`test_song_cue_arc_t462.py`, 92개)은 전부 바이트 동일 통과 — 기존
동작을 건드리지 않았다.

**린트/포맷**: `uv run ruff check server/design/song_cue_render.py
server/tests/test_song_cue_effect_zero_t501_m5.py` → All checks passed.
`uv run ruff format --check` 양쪽 → already formatted.

**@MX 태그**: 해당 없음 — `song_cue_render.py` 파일 전체가 @MX 태그를 쓰지
않는 기존 관례(grep 확인, 0건)를 그대로 따랐다. 신설 함수는 모듈-private
(`_` 접두)이고 fan_in=1(`reviewed_song_commands` 한 곳에서만 호출)이라
ANCHOR 기준(fan_in>=3)에도 해당하지 않는다.

**측정 1-3(8곡, `.moai/reports/t501/measure_m5_8songs.py` 신설 — `measure_ac001_8songs.rehearse`
재사용, DSP 재실행 없음·콘솔 접촉 0건)**:

a. 비액센트 큐 중 effect 그룹 디머>0 인 큐 수(목표 0) — **8곡 전부 0건**
   (BLIND/STROBE/HAZE 그룹별 위반 0, `measure_m5_a_non_accent_zero.json`).
b. 액센트 큐 — effect 그룹 값 직전 큐→이 큐 상승 — **8곡 전부 1/1 상승**
   (곡마다 액센트 큐 1개씩, `measure_m5_b_accent_rising.json`).
c. AC-001/AC-004 재확인 — LIT>=3 **120/120**(변화 없음, M3 후속 climax_return
   완료 당시와 바이트 동일), 색 수/색 변화 8곡 전부 M4 측정과 동일
   (`measure_m5_c_ac001_ac004_recheck.json`). M5가 공유 `fids`를 바꾸지
   않아(그룹 override 축만 추가) 디머/색 렌더링 자체는 구조적으로 불변 —
   예측대로 확인.

```
합계: 비액센트 큐 effect>0 위반 0건(목표 0) · 액센트 상승 8/8 · AC-001 LIT>=3 120/120
```

**측정 항목 d — AC-LDRENDER-015 오프라인 스위트(t498 스크립트 재사용)**:

이 워크트리에 원곡 오디오가 없다던 이전 블로커(M5.md)는 배차서가 절대경로
(주 체크아웃 `src/sample music/Rain.mp3`, 읽기 전용)를 지정해 해소됐다.
`rehearse_rain.py`를 이 트리(M5 적용 후)에서 2회 실행(run1_m5/run2_m5):

- **A1 곡 분석 재현**: PASS — BPM 76.0135, 구간 12/12(양쪽 run 동일)
- **A2 게이트 G1~G13**: PASS — 13/13 `passed: true`(3회 반복 이벤트 전부)
- **A3 결정성**: PASS — run1==run2 바이트 동일(224줄, approved·sent 둘 다)
- **A4 승인=송신**: PASS — 224=224, 순서까지 동일
- **A5 승인 밖 명령**: PASS — sent-not-approved 0, approved-not-sent 0
- **A7 되읽기**: PASS — 13/13 이름·TrigType·TrigTime(±0.001) 일치. **t498
  원본 실기 판독**(`run8_cue_props.txt`·`run7_after_write.txt`, M5 이전
  실기 캡처, 읽기만 — 새 콘솔 접촉 0)과 대조 — 큐 이름·트리거 시각은
  M3/M4/M5 어느 것도 바꾸지 않았음을 실기 데이터로 확인
  (`.moai/reports/t501/m5_judge_a7.txt`)
- **classify_diff(참고, AC-015 필수 항목 아님)**: t498 실기 전부-거절
  목록(`run3_rain_real_denyall`, M5 이전 실기 캡처)과 대조하면 신규
  UNEXPLAINED 117줄 — **전부** M3/M4/M5 가 추가한 Group 3/4/7/10/13/14/
  15/16 줄 패턴(역할 디머·역할 색·effect=0)으로 설명되고, 예외 1줄은
  가짜 콘솔 좌표 대역(fid 20/26) 색 줄(기존에 문서화된 측정 하네스 자체의
  알려진 인공물, M5 무관). 실기 전용 12줄은 전부 기존 W 채널(t430,
  M5 이전부터 있던 축). 이 비교는 t498의 **M5 이전** 실기 캡처를 기준선으로
  삼으므로 "회귀 0건"의 증거가 아니라 "새 UNEXPLAINED 전부가 알려진 M3/M4/
  M5 패턴으로 설명됨"의 증거다 — AC-015가 요구하는 A1~A7·C 항목 자체는
  아니라서 참고용으로만 싣는다(`.moai/reports/t501/m5_classify_diff.txt`).
- **C1~C3(기존 쇼 보존·백업·번호 충돌)**: 이번 카드는 콘솔 쓰기를 하지
  않아(가짜 콘솔만) 직접 측정하지 않았다 — M3/M4/M5 모두 값 줄 생성
  로직만 바꾸고 `Store Sequence`/프리셋 번호 발급 경로를 건드리지 않았다
  (코드 판독: 변경된 함수가 전부 `extra_value_lines`에만 기여, 시퀀스/큐
  번호·프리셋 참조 로직은 무변경 — 간접 근거, 실기 재확인은 후속 실기
  세션의 몫).

**측정하지 않은 것(§Gaps)**:
- fid-수준 뺄셈(REQ-007 문면 직역) — 멤버십 판독 경로 부재로 여전히 불가.
  AC-LDRENDER-006 은 디머 축만 PASS, 색/포지션/페이저 축은 공유 `fids`
  그대로라 미충족(위 §해석 노트).
- C1~C3 의 실기 재측정(콘솔 쓰기 0건 제약, 위 참조).
- AC-LDRENDER-016(실기 감독 판정) — 사람 판정, 이 카드 범위 밖.
- 옵션 (a)/(c)의 실측 재시도(이번 카드도 "no console contact") — 결정
  (g)가 둘 다 우회했으므로 더 이상 필요하지 않다.

### M6 — 효과 송신 통로: fx.permitted 처방 + REQ-010/011/012 (카드 t501, 2026-10-01)

**전제**: M1(REQ-009)이 "effect" 어휘 공백을 확정했고(`capability_verdict.
CAPABILITY_VOCABULARY` 에 "effect" 키 자체가 없음), M5(결정 g)가 effect
기구 디머 분리를 그룹 주소 override 로 닫았다. M6 는 (1) 그 공백을 메우는
처방을 확정·구현하고(REQ-009 M1 완료), (2) `_phaser_cue_value_lines` 가
`cue.fx.permitted` 를 읽도록 닫고(REQ-010), (3) 풀에 없는 카탈로그 페이저를
기존 FXLIB 저작 경로로 사전 생성하고(REQ-011), (4) 효과 보고를 3계로
가른다(REQ-012). **읽기 전용 경계는 카드 전체에 적용**(OFFLINE PART ONLY,
"ABSOLUTELY NO CONSOLE CONTACT" — 진짜 콘솔/실기와 유사한 통로는 전부
회피하고 가짜 콘솔 + 저장된 읽기 전용 증거만 사용).

#### 1. "effect" 능력 처방 — `Dimmer` (리드 조건 ① 충족, 추측 아님)

`server/design/capability_verdict.py` `CAPABILITY_VOCABULARY` 에
`EFFECT_CAPABILITY("effect"): (DIMMER_ATTRIBUTE,)` 을 추가했다. 근거(모두
파일:줄 인용, 모듈 독스트링에도 동일 근거를 적었다):

1. `docs/proposals/song-lighting-design-standard.md` §4d F1 — "디머
   체이스·펄스=리듬 강조(D3+)"가 이펙트 축별 용도표의 정식 항목.
2. `server/fx/library/dimmer.yaml` 전수 확인(`grep -En "Attribute|attribute"`)
   — 모든 항목이 `Dimmer` 하나만 스텝에 싣는다(ColorRGB·Pan·Tilt·Strobe
   0건).
3. 실기 판독 `.moai/reports/t241/verdict.md` §2(리그 8기종 전수 채널 표) —
   `Dimmer` 보급 84/86(HAZE 2대만 없음), effect 역할 그룹(BLIND·STROBE)도
   포함.
4. `Strobe`/`Shutter` 는 근거가 **될 수 없다** — `server/looks/schema.py:16-18`
   가 "Strobe and shutter are out of scope regardless"로 명시하고,
   `server/fx/library/{movement,color,dimmer}.yaml` 전수 확인에서 Strobe
   0건(FXLIB 가 실제로 생성하는 어떤 이펙트도 Strobe 축을 안 건드림).
   실기 판독(`.moai/reports/t442/run7_dmx_channels.txt`)도 `Strobe1`(전
   기종 보급, 범용 셔터 메커니즘)과 `StrobeMode`/`StrobeDuration`(8기종 중
   Atomic 하나뿐)을 구별해, 어느 쪽도 F1 의 디머 체이스 축과 무관함을
   보여준다.

측정 확인(`.moai/reports/t501/measure_fx_permitted_zero_m6.py`, M1 스크립트의
Strobe/Shutter 가정 대신 실기 실측 채널로 재현):

```
$ uv run python .moai/reports/t501/measure_fx_permitted_zero_m6.py
rig.inventory.has_capability("effect") = True
rig.inventory.capability_fids = {'effect': frozenset({601..606, 611..614})}
_fx_axes(budget=10, rig) = 10   (M1 에서는 0 이었다)
```

(전문: `.moai/reports/t501/m6_fx_permitted_fixed.txt`.)

**테스트 뒤집음(명시, 조용히 깨뜨리지 않음)**: `server/tests/
test_capability_verdict.py` 의 `test_the_effect_capability_is_deliberately_
unmapped` → `test_the_effect_capability_is_now_mapped_to_dimmer` 로 이름·
단언·독스트링 갱신. `test_a_fixed_type_declares_neither`(Source 4, Dimmer
하나뿐) → `test_a_fixed_type_declares_effect_but_not_position_or_zoom` 로
뒤집음(이제 `["effect"]`를 선언). `TestWiredCallSite::test_the_call_site_
hands_the_console_read_to_build_rig_profile` 의 같은 어서션도 갱신. 전부
M2 의 REQ-002 테스트 뒤집음과 같은 규율(이름·단언·독스트링 동시 갱신).

#### 2. REQ-LDRENDER-010 — `_phaser_cue_value_lines` 가 `cue.fx.permitted` 를 읽는다

`song_cue_render.py` `_phaser_cue_value_lines` 맨 앞에 `if not cue.fx.permitted:
return ()` 가드를 추가했다 — 이전에는 이 함수가 `cue.fx` 축을 전혀 읽지
않아(잰 값, spec.md REQ-010 인용: "`fx.permitted`를 읽는 곳은 session.py
의 표시용 뿐") 송신 여부가 라벨 매칭·풀 해석에만 의존했다. 이제 D레벨
예산이 0이면(F3) 라벨이 해석되고 슬롯을 찾아도 recall 을 내지 않는다.

**RED→GREEN**: 기존 `server/tests/test_web_session.py`
`TestPhaserSongCueMapping::test_a_resolved_phaser_adds_exactly_one_recall_line`
가 이 가드 추가로 즉시 RED(기존 `_cue()` 헬퍼 기본값 `fx.permitted=()`)가
됐다 — `_cue()` 에 `fx_permitted` 파라미터(기본 `()`, 하위 호환)를 추가하고
그 테스트 + `test_the_recall_line_lands_after_the_plans_own_dimmer_line_
and_before_store` 두 곳에 `fx_permitted=("dimmer chase",)` 를 명시해 GREEN
으로 되돌렸다(시나리오 의도는 그대로, 새 전제조건만 채움 — 단언 극성을
뒤집은 M2 류 플립과는 다른, 전제조건 추가형 수정). 신규
`test_a_resolved_phaser_with_no_fx_budget_adds_nothing` 로 새 게이트
자체를 검증.

#### 3. REQ-LDRENDER-011 — 사전 생성 (측정됨: 5개 중 1개만 빌드된다, 날조 아님)

신설 `server/design/phaser_pregen.py` — `phaser_catalog.py` 라벨을
`server/fx/instantiate.py` 의 **기존** 저작 경로(`build_fx_preset_bundle`/
`select_preset_number`)로 번들화하는 순수 함수들(`fx_for_catalog_label`·
`pool_name_for_label`·`presets_section_from_pool_children`·
`pregenerate_phaser_bundle`). `server/web/session.py` 에
`_pregenerate_missing_phasers`(신설)를 배선 — `_reviewed_song_commands`
안에서 `_phaser_slots_for_bundle` 직후 호출되고, 결과를
`self._last_phaser_slots` 로 저장한다(REQ-012 가 재사용). **감독 승인 뒤
(`_song_finalize` 의 approve 루프 안)에만 호출되는 유일한 호출부**이고,
생성 자체도 `BatchRisk(kind="song_design_fx_pregen")` 선언으로
`run_commands` → `gate.screen()` 단일 관문을 한 번 더 거친다(plan.md §D
"단일 관문 무변경" 준수 — `test_write_dispatch_census.py` 에 새 자리로
등재, 30번째 디스패치 자리 확인됨).

🔴 **측정된 블로커(추측 아님) — 5개 필요 라벨 중 `Wave CM` 하나만 이
경로로 빌드된다.** `build_fx_preset_bundle`→`_guard_collision`
(REQ-FXLIB-011 (a))이 "한 스텝에서 다음 스텝으로 어떤 채널이든 값이
우연히 같으면" 번들 조립 자체를 거부한다(`server/fx/library/color.yaml`
자신의 저작 규율 — "EVERY CHANNEL HAS TO TRAVEL"). `phaser_catalog.py` 의
30종은 이 규율을 염두에 두고 고른 색이 아니다(손수 작성 경로가 Phase 를
한 채널에만 실어 이 제약을 안 받기 때문). 직접 측정(`server/tests/
test_phaser_pregen.py::TestPregenerateBundle`):

| 라벨 | 결과 | 거부 사유(FXLIB 기존 코드) |
|---|---|---|
| Wave CM | **빌드됨** | — |
| Drop Slam | REFUSED | `value_line_collision`(Red→Red, ColorRGB_R 중복) |
| Breathe Warm | REFUSED | `value_line_collision`(ColorRGB_R 중복) |
| Breathe Cool | REFUSED | `value_line_collision`(ColorRGB_B 중복) |
| Finale Slam | REFUSED | `value_line_collision`(ColorRGB_R 중복) |

이 거부는 FXLIB 기존 사유 코드 그대로 `failed` 에 남고(`_pregenerate_
missing_phasers` 의 `except (PhaserPregenError, FxInstantiationError)`),
카탈로그 색을 바꿔 충돌을 피하는 것(새 RGB 발명)은 하지 않았다(§D 제약
준수). 처방(카탈로그 색 재선정 또는 FXLIB 쪽 새 빌더)은 이 카드가
결정하지 않는다 — 후속 카드 후보(`.moai/reports/t501/m6_pregen_targets_
rain.md` §잔여 위험 참조).

**[ASSUMPTION] phase/curve 문법 괴리(Wave CM 에도 적용, 빌드는 되지만)**:
`build_fx_preset_bundle` 이 쓰는 FXLIB 표준 문법(`Step <k> At Accel <v>`,
속성별 Phase 체이스)은 `server/web/session.py` 손수 작성 경로(채널
하나에만 Phase/Accel/Decel)와 **다르다**(둘 다 각자 콘솔에서 측정됐지만
상호 교환 가능하다는 실측은 이 저장소에 없다). "같은 스텝 값·같은 색·
같은 속도"를 재현하되 명령 문면은 FXLIB 표준을 따른다 — 전체 근거는
`phaser_pregen.py` 모듈 독스트링.

**테스트**: `server/tests/test_phaser_pregen.py`(24개, 순수 함수 전수 —
5개 필요 라벨 변환·Wave CM 성공·나머지 4개 거부·PRESET_OCCUPIED 거부·
풀 미판독 거부), `server/tests/test_phaser_pregen_wiring.py`(6개,
`_pregenerate_missing_phasers` 배선 — 예산 0 스킵·이미 해석됨 스킵·성공
디스패치·게이트 거부·충돌 거부·콘솔 쓰기 0건 확인).

#### 4. REQ-LDRENDER-012 — 효과 3계 보고

`song_cue_render._fx_report_counts(bundle, phaser_slots)` 신설 —
`(requested, permitted, sent)`. "sent" 셈은 `_phaser_cue_value_lines` 의
REQ-010 게이트와 바이트 단위로 맞췄다(같은 조건: `cue.fx.permitted` 비어
있지 않음 + 라벨 해석 + `phaser_slots` 에 그 라벨 존재) — 두 곳이 갈리면
보고가 실제 송신과 다른 숫자를 주장하게 되므로, 독스트링에 이 동치성
요구를 명시했다. `server/web/session.py` `_fx_report_note`(신설)가 이
3계 숫자를 최종 회신에 " 효과: 요청 N · 허용 M · 송신 K."로 노출한다
(`_phaser_failure_note`/`_color_failure_note`/`_arc_note` 와 같은 관행 —
요청 0건이면 문구 자체를 생략). `self._last_phaser_slots`(M6 신설 필드)가
사전 생성 병합 후의 phaser_slots 를 들고 있어, 보고의 "송신" 이 REQ-011
의 효과까지 반영한다.

**테스트**: `server/tests/test_fx_report_counts_t501_m6.py`(8개) —
요청 0건 무문구·요청 합산·예산별 필터·송신 요건(예산+풀 해석 둘 다)·
비매칭 라벨·REQ-010 게이트 동치성·`_fx_report_note` 3수치 노출.

#### 5. 5절 정지점 — Rain 사전 생성 명령 (WITHOUT SENDING, 콘솔 쓰기 0건)

`.moai/reports/t501/m6_pregen_stop_point.py` 가 `.moai/reports/t469/
run3_phaser_pools.txt`(Color 풀 4번·All 1 풀 21번의 완전 판독, 이 SPEC
이전 카드가 저장한 읽기 전용 증거 — 이 워크트리의 t498 풀 스냅샷은
Position 풀만 담고 있어 Color/All 1 점유를 모른다)을 저장된 읽기로 써서
Rain 의 5개 필요 라벨 전부를 돌렸다. 산출물: `.moai/reports/t501/
m6_pregen_commands_rain.txt`(Wave CM 의 명령 전문 + 나머지 4개의 REFUSED
사유 주석), `.moai/reports/t501/m6_pregen_targets_rain.md`(풀 번호·슬롯·
이름 전부 + 점유 증거 출처·캡처 시점 + "전송 전 재조회 필수" 명시),
`.moai/reports/t501/m6_pregen_stop_point_output.json`(구조화 전문).

#### 6. 8곡 측정 + 회귀 + 린트/뮤테이션

```
$ uv run python .moai/reports/t501/measure_m6_8songs.py
Club Diver: fx 요청 12 · 허용 0 · 게이트상 송신 0 · ... LIT>=3 14/14 · 색 4종
...(8곡)...
합계: fx 요청 107 · 허용 0 · 게이트상 송신 0 · AC-001 LIT>=3 120/120
```

**AC-001 LIT>=3 120/120 — M5 측정과 바이트 동일**(M6 는 `fids`/디머·색
렌더링을 건드리지 않았으므로 구조적으로 불변, 예측대로 확인). **fx 허용
= 0, 모든 곡**(§Gaps 참조 — 측정 하네스(`measure_ac001_8songs.rehearse`,
`get_spatial_context` 스텁)가 M1 의 전용 스크립트처럼 실기 능력 데이터를
공급하지 않아 `_try_rig_capabilities()` 가 빈 판독으로 귀결 — 이것은
하네스 한계이지 프로덕션 결함이 아니다. 처방 자체의 효과는 §1의 전용
측정(`measure_fx_permitted_zero_m6.py`, 실기 실측 채널 데이터로 확인)이
증명한다). "실제 At Preset 줄" 열은 포지션 프리셋 recall 까지 포함하는
과다 계수라 fx 전용 교차검증으로 쓰지 않는다(측정 스크립트 자체의
한계로 명시).

**전체 스위트**:

```
$ unset MOAI_KANBAN ... && PYTHONDONTWRITEBYTECODE=1 uv run pytest server/tests -q -p no:cacheprovider
14515 passed, 35 skipped, 1 warning in 306.85s
```

베이스라인(M5, HEAD `4d93e1dc` 직후 측정) `14476 passed, 35 skipped`
대비 **+39 passed, 0 removed, skip 변화 0** — 신설 24+6+8=38개 + REQ-010
가드 자체 검증용 신규 1개(`test_a_resolved_phaser_with_no_fx_budget_adds_
nothing`) = 39, 정확히 일치. 기존 테스트 파일 6개(`test_capability_
verdict.py`·`test_preset_label_lookup_t232.py`·`test_song_cue_arc_t462.py`
·`test_song_cue_color_emission.py`·`test_song_cue_effect_zero_t501_m5.py`
·`test_web_session.py`)에서 REQ-010 가드 추가로 생긴 스텁 보강(새
`_pregenerate_missing_phasers` 메서드 호출을 흡수하는 passthrough 스텁 +
`fx` 필드 추가)과 3개 테스트의 명시적 뒤집음(§1 참조) 모두 **조용히
깨뜨리지 않고** 이름·단언·독스트링을 함께 갱신했다.

**뮤테이션(4건, 각 1축, diff 로 적용 확인 후 복원)**:

| 뮤테이션 | 대상 | 죽은 테스트 | 결과 |
|---|---|---|---|
| A: `cue.fx.permitted` 가드 제거 | `_phaser_cue_value_lines` | `test_a_resolved_phaser_with_no_fx_budget_adds_nothing` | FAIL(의도대로) |
| B: `EFFECT_CAPABILITY` 항목 제거 | `CAPABILITY_VOCABULARY` | 3건(`test_the_effect_capability_is_now_mapped_to_dimmer` 외) | FAIL |
| C: `_phase_bounds("0 Thru 360")` 값 조작(360→180) | `phaser_pregen.py` | `test_phase_token_0_thru_360_becomes_a_spread` | FAIL |
| D: `wanted` 집합에서 `cue.fx.permitted` 필터 제거 | `_pregenerate_missing_phasers` | `test_a_label_with_empty_fx_permitted_is_never_attempted` | FAIL |

4건 전부 적용 후 대상 테스트만 FAIL(축 분리 확인), `diff` 로 적용 재확인
후 복원, 복원 뒤 4개 파일 전부 바이트 동일(`diff -q` 확인) + 해당 테스트
재통과 확인. 생존 뮤턴트 0건.

**린트/포맷**:

```
$ uv run ruff check <14개 변경/신설 파일>
All checks passed!
$ uv run ruff format --check <14개 변경/신설 파일>
15 files already formatted
```

**@MX 태그**: 해당 없음 — `song_cue_render.py`·`capability_verdict.py`·
`console_slots.py` 전부 @MX 태그를 쓰지 않는 기존 관례(전수 확인, 0건)를
그대로 따랐다(`rig.py` 만 3건 — 파일별 관례가 갈림). 신설 `phaser_pregen.py`
의 공개 함수들은 fan_in 2(session.py + 테스트)로 ANCHOR 기준(fan_in>=3)
미만이라 해당 없음.

**측정하지 않은 것(§Gaps)**:
- 4개 라벨(Drop Slam/Breathe Warm/Breathe Cool/Finale Slam)의 실제 사전
  생성 — FXLIB `_guard_collision` 거부로 이 경로로는 영구 불가(처방 미정,
  §3 참조). Rain 이 가장 자주 필요로 하는 절정 라벨(Drop Slam)이 이에
  포함된다는 점을 명시한다.
- Wave CM 의 phase/curve 문법이 카탈로그가 약속한 것과 **같은 시각
  효과**를 내는지 — 명령 문면이 다르므로(§3 [ASSUMPTION]) 실기 육안
  확인 전까지는 미확인.
- 8곡 측정에서 `fx.permitted` 실측(§6의 하네스 한계) — 전용 스크립트
  (§1)가 대신 증명했지만, `measure_ac001_8songs.rehearse` 경로 자체의
  보강(실기 능력 데이터 공급)은 이 카드가 하지 않았다.
- C1~C3(기존 쇼 보존·백업·번호 충돌)의 실기 재확인 — 이번 카드도 콘솔
  쓰기 0건 제약(M5 와 같은 사유).
- AC-LDRENDER-009/010(기계 증거)은 Wave CM 한정으로만 충족 가능성이
  있고, 이 카드는 실제 전송을 하지 않았으므로 AC-009 의 "기계 증거"
  (송신 효과 줄 1줄 이상, 실제 콘솔 접촉 경로)를 PASS 로 보고하지 않는다
  — §5 정지점 산출물이 "보낼 수 있다"만 보인다.
- AC-LDRENDER-016(실기 감독 판정) — 사람 판정, 이 카드 범위 밖.

**잔여 위험**:
- `.moai/reports/t469/run3_phaser_pools.txt` 풀 스냅샷은 이 SPEC 이전
  캡처라 지금 이 순간의 점유를 보장하지 않는다 — 전송 전 재조회 필수
  (명시, m6_pregen_targets_rain.md).
- `select_preset_number`/`build_fx_preset_bundle` 의 번호 할당은 "이번
  재조회 순간"에 유효할 뿐이다 — 다른 세션이 그 사이 같은 슬롯을 차지할
  경쟁 조건은 이 카드가 새로 막지 않는다(FXLIB 기존 경계 그대로 상속).
- `group=1`(스크래치 저작 선택) 이 모든 리그에서 addressable 하다는
  보장은 없다 — Rain 리그에서는 "All" 관례(여러 보고서가 인용)로 안전
  하다고 보지만, 다른 리그로 일반화는 미검증.

## §E.4 Sync-phase Audit-Ready Signal

_<sync-phase 대기>_
