# SPEC-LDRENDER-001 — 구현 계획

## §A 맥락

- **입력**: `.moai/specs/SPEC-LDRENDER-001/research-input-design-readout.md`(리드 요약) · `.moai/reports/t499/verdict.md`(8곡 오프라인 판독) · `.moai/reports/t498/verdict.md`(Rain 실기 파일럿).
- **전제 SPEC**: SPEC-LDDESIGN-001(completed — 층 매핑 카드·M2 색 배선·회차 에스컬레이션·헤드룸), SPEC-COPILOT-FXGEN-001/FXLIB-001(completed — 페이저 저작 도구), SPEC-COPILOT-COLORMODE-001(completed — `color_usage` 곡별 스위치).
- **범위**: `server/design/song_cue_render.py`(송신기 본체) · `server/design/rig.py`(역할 매핑 어휘) · `server/design/song_cue_composer.py`(디머 데이터 모델) · `server/design/section_palette.py`(색 산출 — 읽기만, 로직 무변경) · `server/web/session.py`(호출부 배선) · `server/orchestrator/tools.py`(LLM 툴 경로 배선, SPEC-LDDESIGN-001 M0 가 이미 단일 컴포저로 합침) · `.moai/reports/t499/readout.py`(제품화 대상).
- **진입 조건**: SPEC-LDDESIGN-001 이 `completed`(확인됨, 2026-09-28) — 층 매핑 확인 UX·회차 에스컬레이션·헤드룸 등 이 SPEC 이 재사용하는 하부 구조가 이미 존재한다.

## §B 알려진 위험 (manager-develop 착수 전 필독)

1. **"effect" 라벨 중의 — 두 개의 서로 다른 축이 같은 문자열을 쓴다.** `RigLayers.mapping["effect"]`(역할→그룹번호 주소록, `_LAYER_GROUP_ALIASES` 가 만듦, R1/R3 가 쓴다)와 `RigInventory.capability_fids["effect"]`(패치 레코드의 **명시 선언** 능력, `energy.py` 의 fx 예산이 쓴다, R4 가 다룬다)는 **구조적으로 다른 파이프라인**이다. M1 에서 이 둘을 혼동해 "역할 매핑이 있으니 능력도 있다"고 가정하면 안 된다 — 실측해야 한다(REQ-LDRENDER-009).
2. **`build_rig_profile(patch=..., groups={})`가 두 호출부(`session.py:7445`, `:7556`) 모두 `groups={}` 를 하드코딩한다.** 이것이 버그처럼 보이지만 `:7556` 인근 주석이 이미 이유를 설명한다 — 그룹 **멤버십**(어느 fid 가 그 그룹인가)은 이 통로로 읽을 수 없어(GROUPGEN SPEC 의 멤버십 판독 불가 확정과 동형), 대신 `declared_layers`(역할→그룹 **번호**, fid 아님)로 RG1(층 존재 여부)만 켠다. R1 의 다중 역할 렌더링은 **그룹 번호**만 있으면 되므로(`Group <n> ; Attribute ... At ...` 형태, fid 불요) 이 설계와 충돌하지 않는다 — fid 집합이 필요하다고 가정하지 마라.
3. **`CueDimmerData`는 현재 `key_pct`·`back_pct` 둘뿐이다**(`song_cue_composer.py:157-165`). R1 이 SIDE/WASH/MOVER 역할 값을 내려면 이 데이터클래스를 확장해야 한다 — M2 가 그 확장을 가장 먼저 한다(결정 번복 비용이 가장 큰 축이므로 1순위).
4. **`_phaser_cue_value_lines`는 이미 호출되고 있다**(`song_cue_render.py:1051`). R4 의 결함은 "함수가 없다"가 아니라 "호출 전제(`fx.permitted`≠0 또는 `phaser_slots` 비어있지 않음)가 8곡 전부 성립하지 않는다"이다 — 새 함수를 만들지 말고 호출 전제의 원인(M1)부터 닫아라.
5. **효과 송신은 기계로 검증할 수 없다**(FXLIB/FXGEN 의 측정된 경계). 큐가 페이저 recall 줄을 담고 있는지는 송신 문자열 정적 검사로 확인 가능하지만, 그 효과가 실제로 보이는지는 **사람의 콘솔 GUI 관측뿐**이다. AC 는 두 증거를 분리한다(오프라인 송신 목록 검사 vs 실기 육안).
6. **`palette_mode`/`color_usage` 를 우회하지 마라.** R2 의 보조색 송신은 `_section_palette_choice` 가 이미 결정한 값을 그대로 옮기는 것이지, 새 색 선택 로직을 만드는 것이 아니다. `single` 모드에서 보조색 칸이 베이스와 같아지는 경우(§D5) 중복 줄을 내지 않도록 주의.

## §C 사전 점검 (M1 착수 직전)

```bash
git branch --show-current
git rev-parse HEAD
uv run pytest server/tests/test_layer_mapping_effect_role.py server/tests/test_song_cue_color_emission.py server/tests/test_song_cue_white_preset_t453.py -q
grep -rn "RigInventory\|capability_fids" server/design/rig_capability_read.py server/design/capability_verdict.py | wc -l
uv run python .moai/reports/t499/readout.py --help 2>&1 | head -20
```

### R4 방법 선택 — 두 선택지의 비용 (§5 열린 결정 1 상세)

| | (a) 사전 생성(`compose_fx`/`instantiate_fx`) | (b) 고지만 강화 |
|---|---|---|
| 콘솔 쓰기 | 있음 — 새 승인 경로 필요(REQ-FXGEN-011 프리셋 저장 또는 FXLIB 시퀀스+큐) | 없음 |
| 효과가 실제로 보이는가 | 예 — 풀에 없던 페이저가 생기면 recall 이 성립 | 아니오 — 8곡 모두 송신 효과 0줄은 그대로(R4 의 AC 미충족 위험) |
| 구현 범위 | `song_cue_composer`/`song_cue_render` 호출부가 `compose_fx` 를 선행 호출하는 새 단계 추가 | `song_cue_render.py` 의 고지 문자열만 변경 + 리뷰 표면 노출 경로 추가 |
| 리스크 | 자동 생성이 감독이 모르는 사이 콘솔 풀을 채움(승인 UX 설계 필요) | AC 의 "효과를 요청한 곡은 송신 효과 줄 1줄 이상" 을 구조적으로 만족 못 시킬 수 있음(풀에 없는 페이저가 많으면) |

manager-develop 은 M1 측정 결과와 함께 이 표를 감독에게 다시 제시하고, 착수 전 AskUserQuestion 으로 확정한다(스펙 §5 결정 1 — 아직 미확정).

## §D 제약 (위반 금지)

- **PRESERVE**: `server/safety/**`(byte-diff 0) · `server/looks/{schema,loader,roles,resolver,instantiate,matching}.py`(FXLIB/LOOKLIB 잠금 계승) · `server/rulebook/assets/v2.4.2/**`(PRESERVE, R4 가 (a) 를 택해도 FXGEN 이 이미 연 경로만 재사용한다 — 신규 자산 추가 없음) · `console/lua/copilot_responder.lua`.
- 단일 관문(`run_commands` → `gate.screen()`) 무변경 — 송신기가 명령 문자열을 더 많이 만들 뿐 제2 실행 표면을 만들지 않는다.
- `_PROGRAMMER_STATE_COMMANDS`/dedupe 면제 집합 무변경(값 라인 충돌 가드는 그대로 둔다 — 역할별 줄이 늘어나도 각 줄은 여전히 유일 문자열이어야 한다, REQ-FXLIB-011 계승 구조).
- 표준 팔레트 10색 밖의 RGB 발명 금지(§A.2 색 범위 불변).
- `palette_mode`/`color_usage` 분기 로직(`_section_palette_choice`) 수정 금지 — 읽기만.

## §E 마일스톤 (결정 번복 비용 순 — 데이터 모델·신규 해석 축이 먼저, 기계적 배선은 뒤로)

### M1 — 측정: fx.permitted 원인 + 판독 하네스 제품화

REQ-LDRENDER-009, REQ-LDRENDER-013. **착수 전 결정**: §C 의 R4 방법 선택 표를 감독에게 제시하고 확정받는다 — 이 결정이 M4 의 설계를 바꾼다.

- `server/design/rig_capability_read.py`/`capability_verdict.py` 를 코드 판독해 "effect" 능력 선언 경로를 정확히 지목.
- 실기(또는 실기와 동형의 패치 데이터)로 BLIND/STROBE/HAZE 그룹 소속 기구가 실제로 `capabilities={"effect",...}` 선언을 받는지 1곡 왕복으로 측정.
- `.moai/reports/t499/readout.py` 의 판정 함수(색 수·층 수·효과 줄 수 판정 로직)를 `server/design/` 아래 임포트 가능한 모듈로 옮긴다(스크립트 복사가 아니라 함수 추출 — 기존 CLI 는 그 모듈을 호출하는 얇은 래퍼로 남긴다).

### M2 — 큐 디머 데이터 모델 확장 (R1 기반)

REQ-LDRENDER-001, REQ-LDRENDER-002, REQ-LDRENDER-003. **가장 되돌리기 비싼 축** — `CueDimmerData`(`song_cue_composer.py:157`)에 역할별 퍼센트를 담을 구조(기존 `key_pct`/`back_pct` 명명 필드 패턴을 유지하는 매핑형 확장 — 예: `role_pct: Mapping[str, float]`)를 더하고, `rig.py` 의 `_LAYER_GROUP_ALIASES` 에 `side`/`wash`/`mover` 접두 토큰 해석을 추가한다. `_back_layer_value_lines` 를 다중 역할 함수로 일반화한다(함수명 변경 포함 — 호출부 전수 갱신).

- PRESERVE 확인: `rig.py` 의 기존 4역할(`key`/`back`/`effect`/`audience`) 정확 일치 동작은 바이트 동일.
- 회귀: `test_layer_mapping_effect_role.py` 의 기존 통과 케이스 전부 유지, `test_mover_and_wash_groups_remain_unmatched_documented_residual` 는 이 마일스톤에서 **의도적으로 뒤집는다**(이제 매칭됨) — 테스트명·단언을 함께 갱신.

### M3 — 색 송신 확장 (R2, M2 배선 재사용)

REQ-LDRENDER-004, REQ-LDRENDER-005, REQ-LDRENDER-006. `_song_color_value_lines` 가 `palette[1:]` 을 M2 가 만든 역할 그룹에 낸다. `color_usage`/`palette_mode` 분기는 읽기 전용 소비.

- 회귀: `test_song_cue_color_emission.py`·`test_song_cue_white_preset_t453.py` 전량 PASS(흰색 프리셋 W 채널 로직 무변경 확인).

### M4 — 효과 기구 분리 (R3, M2 의 effect 역할 재사용)

REQ-LDRENDER-007, REQ-LDRENDER-008. 전체 기구 선택에서 `effect` 역할 그룹 제외, 액센트 상승 방향 정정.

- 회귀: t498/t497 가 지정한 A1~A7·C 항목(기계 동작 PASS)이 깨지지 않는지 재확인 — 되읽기·트래킹·기존 쇼 보존 전부.

### M5 — 효과 송신 통로 (R4, M1 결정 + M2 배선 소비)

REQ-LDRENDER-010, REQ-LDRENDER-011, REQ-LDRENDER-012. §C 표의 확정된 방법(a 또는 b)을 구현.

- (a) 선택 시: `compose_fx`/`instantiate_fx` 선행 호출 + 승인 카드 노출. 콘솔 쓰기 신규 경로이므로 Implementation Kickoff Approval 과 별개로 이 마일스톤 자체 착수 전 감독 재확인.
- (b) 선택 시: 리뷰 표면(변경 스택 또는 분석 요약)에 페이저 미배정 고지 노출 위치 변경.

### M6 — 연출 판독 게이트 배선 (R7, M1 하네스 + M3 색 소비)

REQ-LDRENDER-014, REQ-LDRENDER-015, REQ-LDRENDER-016. M1 이 제품화한 게이트 모듈을 송신 직전 호출 지점(`reviewed_song_commands` 호출부 또는 그 직후)에 배선하고, 경고를 기존 비차단 경고 채널(헤드룸 경고와 같은 표면)에 노출한다. 두 대조군(Rain 고치기 전/후 송신 목록) 테스트를 작성한다.

## §F 안티패턴

- **R4 를 "FXLIB/FXGEN 재구현"으로 착수하지 마라** — `_phaser_cue_value_lines`(M2/M5 가 이미 가진 recall 메커니즘)를 먼저 호출 가능하게 만드는 것이 R4 다. 새 페이저 생성 경로는 §5 결정 1 에서 (a) 가 확정된 경우에만, 그것도 FXGEN 의 기존 `compose_fx` 를 재사용한다 — 새 저작 어휘를 만들지 않는다.
- **"effect" 두 축을 하나로 합치려 들지 마라** — §B 위험 1. `RigLayers` 와 `RigInventory` 를 한 곳에서 선언하려는 리팩터는 이 SPEC 의 범위가 아니다(옳을 수도 있지만 별도 SPEC — 지금은 R3/R4 가 각자의 축만 쓴다).
- **R5/R6 디머 대역·회차 상승 로직에 손대지 마라** — `song_cue_composer.py` 의 `_dimmer_data`/후렴 비교 로직은 PRESERVE.

## §G 교차 참조

- `docs/proposals/song-structure-lighting-standard.md` §6.1~§6.3·§11.2(색·층·분위기 그룹 규율).
- `src/Lighting_Designer/01_스펙/LX-SEQ-SPEC-v2.1.md` §11.2 규칙 6(분위기 그룹 Intensity 정합 제외).
- `.moai/specs/SPEC-LDDESIGN-001/spec.md` §3.9(트래킹 모드)·§3.7(회차 에스컬레이션) — 이 SPEC 이 건드리지 않는 인접 축.
