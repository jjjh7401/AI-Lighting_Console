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

## §E.3 Run-phase Audit-Ready Signal

_<run-phase 대기>_

## §E.4 Sync-phase Audit-Ready Signal

_<sync-phase 대기>_
