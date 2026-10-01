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

## §E.4 Sync-phase Audit-Ready Signal

_<sync-phase 대기>_
