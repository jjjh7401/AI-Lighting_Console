# SPEC-LDRENDER-001 — 구현 계획

> **개정 2026-10-01 (plan-auditor iteration 1 FAIL 0.74 대응)**: §B 위험 7 신설(`RIG_LAYER_ROLES` 닫힌 어휘), §C 에 결정 2 비용표 + M1 읽기 전용 경계 신설, M1/M2/M4 서술 정정(D6/D7/D3). spec.md HISTORY 의 같은 날짜 항목이 7건 전체(D1~D7, D9/D10)의 정본이다.
>
> **개정 2026-10-01 (2차) — 감독 결정 4건 반영, plan-auditor iteration 2 FAIL 0.68(점수 역행) D11·D12 해소.** 감독이 §5 의 열린 결정 3건을 전부 확정했다. 이 개정의 핵심 재구조화: ① **M2 신설**(역할 어휘 확장 — 정본 §2c 버전 올림 + `RIG_LAYER_ROLES` 확장) — R1(이전 M2, 이제 M3)이 이 신설 마일스톤에 **의존**하게 됐다(LIT-only 집계 규칙 하에서 key/back/effect 만으로는 "3층" 목표에 도달 불가 — spec.md §3.1 [HARD] 참조). ② 이전 M2~M6 을 M3~M7 로 밀어 번호를 다시 매겼다. ③ R4(이전 M5, 이제 M6)를 옵션 (a) 단일 경로로 확정하고 충돌 사전 검출을 추가했다. spec.md HISTORY 의 같은 날짜 2번째 항목이 이 개정 전체의 정본이다.

## §A 맥락

- **입력**: `.moai/specs/SPEC-LDRENDER-001/research-input-design-readout.md`(리드 요약) · `.moai/reports/t499/verdict.md`(8곡 오프라인 판독) · `.moai/reports/t498/verdict.md`(Rain 실기 파일럿) · 리드 경유 감독 결정 4건(2026-10-01).
- **전제 SPEC**: SPEC-LDDESIGN-001(completed — 층 매핑 카드·M2 색 배선·회차 에스컬레이션·헤드룸), SPEC-COPILOT-FXGEN-001/FXLIB-001(completed — 페이저 저작 도구, 충돌 거부 의미론 재사용 대상), SPEC-COPILOT-COLORMODE-001(completed — `color_usage` 곡별 스위치).
- **범위**: `server/design/song_cue_render.py`(송신기 본체) · `server/design/rig.py`(역할 매핑 어휘 — `RIG_LAYER_ROLES` 확장 포함) · `server/design/song_cue_composer.py`(디머 데이터 모델) · `server/design/section_palette.py`(색 산출 — 읽기만, 로직 무변경) · `server/web/session.py`(호출부 배선) · `server/orchestrator/tools.py`(LLM 툴 경로 배선) · `.moai/reports/t499/readout.py`(제품화 대상) · **`docs/proposals/song-lighting-design-standard.md`**(§2c 역할 어휘 확장 — run-phase manager-develop 의 편집 대상, 이 plan-phase 산출물은 편집하지 않는다).
- **진입 조건**: SPEC-LDDESIGN-001 이 `completed`(확인됨, 2026-09-28) — 층 매핑 확인 UX·회차 에스컬레이션·헤드룸 등 이 SPEC 이 재사용하는 하부 구조가 이미 존재한다.

## §B 알려진 위험 (manager-develop 착수 전 필독)

1. **"effect" 라벨 중의 — 두 개의 서로 다른 축이 같은 문자열을 쓴다.** `RigLayers.mapping["effect"]`(역할→그룹번호 주소록, `_LAYER_GROUP_ALIASES` 가 만듦, R1/R3 가 쓴다)와 `RigInventory.capability_fids["effect"]`(패치 레코드의 **명시 선언** 능력, `energy.py` 의 fx 예산이 쓴다, R4 가 다룬다)는 **구조적으로 다른 파이프라인**이다. M1 에서 이 둘을 혼동해 "역할 매핑이 있으니 능력도 있다"고 가정하면 안 된다 — 실측해야 한다(REQ-LDRENDER-009).
2. **`build_rig_profile(patch=..., groups={})`가 두 호출부(`session.py:7445`, `:7556`) 모두 `groups={}` 를 하드코딩한다.** 이것이 버그처럼 보이지만 `:7556` 인근 주석이 이미 이유를 설명한다 — 그룹 **멤버십**(어느 fid 가 그 그룹인가)은 이 통로로 읽을 수 없어(GROUPGEN SPEC 의 멤버십 판독 불가 확정과 동형), 대신 `declared_layers`(역할→그룹 **번호**, fid 아님)로 RG1(층 존재 여부)만 켠다. R1 의 다중 역할 렌더링은 **그룹 번호**만 있으면 되므로(`Group <n> ; Attribute ... At ...` 형태, fid 불요) 이 설계와 충돌하지 않는다 — fid 집합이 필요하다고 가정하지 마라.
3. **`CueDimmerData`는 현재 `key_pct`·`back_pct` 둘뿐이다**(`song_cue_composer.py:157-165`). R1 이 확장된 전 역할(key/back/effect/side/wash/mover) 값을 내려면 이 데이터클래스를 확장해야 한다 — M3 가 그 확장을 한다(결정 번복 비용이 두 번째로 큰 축).
4. **`_phaser_cue_value_lines`는 이미 호출되고 있다**(`song_cue_render.py:1051`). R4 의 결함은 "함수가 없다"가 아니라 "호출 전제(`fx.permitted`≠0 또는 `phaser_slots` 비어있지 않음)가 8곡 전부 성립하지 않는다"이다 — 새 함수를 만들지 말고 호출 전제의 원인(M1)부터 닫아라.
5. **효과 송신은 기계로 검증할 수 없다**(FXLIB/FXGEN 의 측정된 경계). 큐가 페이저 recall 줄을 담고 있는지는 송신 문자열 정적 검사로 확인 가능하지만, 그 효과가 실제로 보이는지는 **사람의 콘솔 GUI 관측뿐**이다. AC 는 두 증거를 분리한다(오프라인 송신 목록 검사 vs 실기 육안).
6. **`palette_mode`/`color_usage` 를 우회하지 마라.** R2 의 색 송신은 `_section_palette_choice` 가 이미 결정한 값을 그대로 옮기는 것이지, 새 색 선택 로직을 만드는 것이 아니다. `single` 모드에서 보조색 칸이 지배색과 같아지면(§D5) 그룹을 합쳐 한 줄만 내고 중복 줄을 내지 않는다(REQ-004).
7. **`RIG_LAYER_ROLES` 확장은 "조용히"가 아니라 "정본 문서 + 튜플 + 소비자 재검토"를 함께 한다.** `server/design/rig.py:44` `RIG_LAYER_ROLES` 는 지금까지 닫힌 어휘였다 — 감독 결정 1(옵션 a)로 `side`/`wash`/`mover` 를 더하기로 확정했지만, 이것은 **(a) 정본 문서(`docs/proposals/song-lighting-design-standard.md` §2c) 버전 올림, (b) 튜플 확장, (c) `_build_layers`(`rig.py:305-308`)가 새 역할을 `RigProfileError` 없이 수용하는지 확인, (d) `RigProfile` 를 소비하는 다른 모든 곳(특히 `song_cue_composer.py` 의 `has_layer()` 호출부)이 새 역할 등장에도 안전한지 재검토** — 네 가지를 **함께** 하는 작업이다. 하나라도 빠뜨리면(특히 (d)) 새 역할이 `has_layer()` 기반 규칙(I1~I3·L6/L7)에 의도치 않게 걸릴 수 있다. M2 가 이 작업 전부를 담당한다.
8. **REQ-001 의 "3+ LIT 층" 목표는 이제 M2(REQ-002)에 의존한다.** 감독 결정 2(LIT-only 집계)가 이전 버전의 "key/back/effect 만으로 이미 달성" 주장을 무효화했다 — `effect` 는 R3 에 의해 비액센트 큐에서 항상 꺼져 있어 LIT 버킷에 안 들어간다(key+back 뿐이면 버킷 2개). **M3(R1 렌더링)은 M2(역할 어휘 확장)가 먼저 끝나야 AC-001 을 PASS 시킬 수 있다** — 마일스톤 순서가 이것을 반영한다(아래 §E).

## §C 사전 점검 (M1 착수 직전)

```bash
git branch --show-current
git rev-parse HEAD
uv run pytest server/tests/test_layer_mapping_effect_role.py server/tests/test_song_cue_color_emission.py server/tests/test_song_cue_white_preset_t453.py -q
grep -rn "RigInventory\|capability_fids" server/design/rig_capability_read.py server/design/capability_verdict.py | wc -l
uv run python .moai/reports/t499/readout.py --help 2>&1 | head -20
grep -n "role층\|key/back/effect/audience" docs/proposals/song-lighting-design-standard.md   # M2 착수 전 §2c 현재 표 확인(수정 대상 베이스라인)
```

### R4 방법 — 감독 결정 4로 확정 (옵션 a, 더 이상 선택지 아님)

| | (a) 사전 생성(`compose_fx`/`instantiate_fx`) — **확정** |
|---|---|
| 콘솔 쓰기 | 있음 — **기존** 승인 게이트 재사용(새 경로 아님, REQ-FXGEN-011 프리셋 저장 또는 FXLIB 시퀀스+큐) |
| 효과가 실제로 보이는가 | 예 — 풀에 없던 페이저가 생기면 recall 이 성립 |
| 구현 범위 | `song_cue_composer`/`song_cue_render` 호출부가 `compose_fx` 를 선행 호출하는 새 단계 추가 + 충돌 사전 검출(FXLIB `select_preset_number` 재사용) |
| 리스크 | 자동 생성이 감독이 모르는 사이 콘솔 풀을 채움 — **완화책**: 생성도 기존 승인 카드를 거치므로 감독이 매번 확인한다(새 무승인 경로 없음) |

(이전 버전에 있던 "(b) 고지만 강화" 선택지는 감독 결정 4로 **제거**됐다 — 더 이상 cost table 에 남기지 않는다.)

### 역할 어휘 확장 — 감독 결정 1로 확정 (옵션 a, 더 이상 선택지 아님)

| | (a) 정본·`RIG_LAYER_ROLES` 확장 — **확정** |
|---|---|
| `RigProfileError` 위험 | 없음(튜플 확장이 `declared_layers` 소비보다 먼저 이뤄짐, M2 가 순서를 보장) |
| 정본 문서 개정 | **필요하고 이 SPEC 의 범위 안이다**(run-phase manager-develop 이 `docs/proposals/song-lighting-design-standard.md` §2c 를 직접 편집 — 이 plan-phase 산출물은 편집하지 않는다) |
| `has_layer()` 류 규칙(I1~I3·L6/L7) 인식 | 예 — §B 위험 7 의 (d) 전수 재검토가 선행 조건 |
| AC-001 의 "3개 이상 LIT 층" 목표에 기여 | **필수**(감독 결정 2 의 LIT-only 집계 하에서, key/back 만으로는 버킷 2개뿐 — side/wash/mover 중 최소 1개가 있어야 3개) |
| 구현 비용 | 중간(튜플+정본+파급 검토, §B 위험 7) |

(이전 버전의 (b)/(c) 선택지는 감독 결정 1로 **제거**됐다 — cost table 에서 삭제. (b)/(c) 가 "RIG_LAYER_ROLES 확장 없이" 추가 LIT 버킷을 만들 수 없었던 이유 — 역사적 기록으로만 남긴다: (b)는 SIDE/WASH/MOVER 가 기존 역할과 같은 값을 받아 새 버킷이 안 생기고, (c)는 역할 이름 없는 원시 주소라 `has_layer()` 계열이 인식 못 함.)

### M1 읽기 전용 경계 (D7, 여전히 유효)

[HARD] M1(REQ-LDRENDER-009)의 실기 측정은 **읽기 전용**이다 — 응답기 `state`/`prop` 류 조회만 쓰고, `exec`/`Store`/`Label` 등 콘솔을 변경하는 어떤 커맨드도 발화하지 않는다. 이 측정은 §C 사전 점검의 `grep` 코드 판독과, (가능하면) 실기 또는 실기와 동형의 패치 데이터를 읽기만 하는 1회 왕복으로 완료된다 — 콘솔 쓰기가 필요한 조치(페이저 사전 생성, M6)는 M1 의 범위 밖이다.

## §D 제약 (위반 금지)

- **PRESERVE**: `server/safety/**`(byte-diff 0) · `server/looks/{schema,loader,roles,resolver,instantiate,matching}.py`(FXLIB/LOOKLIB 잠금 계승) · `server/rulebook/assets/v2.4.2/**`(PRESERVE — FXGEN 이 이미 연 경로만 재사용한다, 신규 자산 추가 없음) · `console/lua/copilot_responder.lua`.
- 단일 관문(`run_commands` → `gate.screen()`) 무변경 — 송신기가 명령 문자열을 더 많이 만들 뿐 제2 실행 표면을 만들지 않는다. **M6 의 페이저 생성도 이 단일 관문을 통과한다 — 새 무승인 실행 표면 금지.**
- `_PROGRAMMER_STATE_COMMANDS`/dedupe 면제 집합 무변경(값 라인 충돌 가드는 그대로 둔다 — 역할별 줄이 늘어나도 각 줄은 여전히 유일 문자열이어야 한다, REQ-FXLIB-011 계승 구조).
- 표준 팔레트 10색 밖의 RGB 발명 금지(§A.2 색 범위 불변) — `key` 웜화이트도 표준 팔레트 기존 항목 재사용, 새 RGB 금지.
- `palette_mode`/`color_usage` 분기 로직(`_section_palette_choice`) 수정 금지 — 읽기만.
- **FXLIB 의 충돌 거부 의미론(`select_preset_number`/`PRESET_OCCUPIED` 등)을 새로 구현하지 마라 — 재사용만 한다**(M6).
- **정본 문서(`docs/proposals/song-lighting-design-standard.md`) 편집은 M2 의 명시된 범위(§2c 역할 표 + 버전 올림)로 한정한다** — 다른 절 수정 금지.

## §E 마일스톤 (결정 번복 비용 순 — 데이터 모델·신규 해석 축이 먼저, 기계적 배선은 뒤로. 감독 결정 반영으로 M2 신설 + 전체 1단씩 밀림)

### M1 — 측정: fx.permitted 원인 + 판독 하네스 제품화

REQ-LDRENDER-009, REQ-LDRENDER-013. **착수 전 확인**: R4 방법은 이미 확정(옵션 a) — 더 이상 감독 확인 라운드가 필요 없다. **이 마일스톤은 읽기 전용이다 — 콘솔 쓰기 0건**(위 "M1 읽기 전용 경계" 참조).

- `server/design/rig_capability_read.py`/`capability_verdict.py` 를 코드 판독해 "effect" 능력 선언 경로를 정확히 지목.
- 실기(또는 실기와 동형의 패치 데이터)를 **재조회로만** 읽어 BLIND/STROBE/HAZE 그룹 소속 기구가 실제로 `capabilities={"effect",...}` 선언을 받는지 1곡 왕복으로 측정(쓰기 커맨드 발화 금지).
- `.moai/reports/t499/readout.py` 의 판정 함수(색 수·층 수·효과 줄 수 판정 로직)를 `server/design/` 아래 임포트 가능한 모듈로 옮긴다(스크립트 복사가 아니라 함수 추출 — 기존 CLI 는 그 모듈을 호출하는 얇은 래퍼로 남긴다). **이 시점에 LIT-only 집계(감독 결정 2)를 함께 구현한다** — readout.py 원본이 그 집계를 이미 하는지 코드 판독으로 확인하고, 안 하면 이 추출 단계에서 보강한다(AC-012 가 이 동치성을 검증).

### M2 — 역할 어휘 확장: 정본 §2c 버전 올림 + `RIG_LAYER_ROLES` + 그룹 이름 해석 (R1 기반, 신설, 감독 결정 1)

REQ-LDRENDER-002. **가장 되돌리기 비싼 축으로 승격** — R1(M3)의 완료 조건이 이 마일스톤에 의존한다(§B 위험 8). 순서: ① `docs/proposals/song-lighting-design-standard.md` §2c 의 "role층 → 그룹 매핑" 표에 `side`/`wash`/`mover` 추가 + 문서 버전 올림(단독 커밋 권장 — 문서 변경과 코드 변경을 분리하면 리뷰가 쉽다). ② `server/design/rig.py:44` `RIG_LAYER_ROLES` 튜플에 세 역할 추가. ③ `rig.py:305-308` `_build_layers` 가 `declared_layers={"side":...}` 류 입력을 `RigProfileError` 없이 수용하는지 단위 테스트로 확인(신규 테스트, 아직 없음). ④ `song_cue_composer.py` 의 `has_layer()` 호출부 전수 grep 하여 새 역할 등장 시 안전한지 확인(§B 위험 7 (d)). ⑤ `_LAYER_GROUP_ALIASES` 에 접두 토큰 해석 추가(`SIDE-L/R/ALL`→`side`, `WASH-U/D/ALL`→`wash`, `MOVER-U/D/ALL`→`mover`, 부분 문자열 추측 없음). ⑥ `test_layer_mapping_effect_role.py:119` `test_mover_and_wash_groups_remain_unmatched_documented_residual` 를 **의도적으로 뒤집는다** — 테스트명·단언·docstring 을 함께 갱신(조용히 깨뜨리지 않는다, REQ-002 본문 참조).

- PRESERVE 확인: 기존 4역할(`key`/`back`/`effect`/`audience`)의 `_LAYER_GROUP_ALIASES` 정확 일치 동작은 바이트 동일.
- 회귀: `test_layer_mapping_effect_role.py` 의 기존 통과 케이스 전부 유지(단, `:119` 는 의도적으로 뒤집음 — 위 ⑥).
- 산출물: 정본 문서 diff(§2c 만) + `rig.py` diff + 신규 `_build_layers` 수용 테스트 + 뒤집힌 테스트.

### M3 — 큐 디머 데이터 모델 확장 + 다중 역할 렌더링 (R1, M2 소비)

REQ-LDRENDER-001, REQ-LDRENDER-003. `CueDimmerData`(`song_cue_composer.py:157`)에 역할별 퍼센트를 담을 구조(기존 `key_pct`/`back_pct` 명명 필드 패턴을 유지하는 매핑형 확장 — 예: `role_pct: Mapping[str, float]`, 키는 M2 가 확장한 `RIG_LAYER_ROLES` 전체)를 더한다. `_back_layer_value_lines` 를 매핑된 모든 역할을 순회하는 다중 역할 함수로 일반화한다(함수명 변경 포함 — 호출부 전수 갱신).

- 전제: M2 완료(`side`/`wash`/`mover` 가 `RIG_LAYER_ROLES`·`_LAYER_GROUP_ALIASES` 양쪽에 존재).
- 회귀: `test_layer_mapping_effect_role.py` 전량 PASS(M2 가 이미 뒤집은 테스트 포함).
- AC-001 PASS 전제조건: 층 매핑이 `key`+`back`+ (`side`/`wash`/`mover` 중 1개 이상)을 해석한 곡으로 측정(2-역할 잔여 리그는 §B/acceptance.md 경계 사례 참조 — 이 마일스톤이 메우지 않는다).

### M4 — 색 송신 확장 + 층→색 배정 (R2, M2/M3 배선 재사용, 감독 결정 3)

REQ-LDRENDER-004, REQ-LDRENDER-005, REQ-LDRENDER-006. `_song_color_value_lines` 가 감독 결정 3 의 구체 배정대로 값을 낸다: `back`+`mover` = 지배색(`palette[0]`), `side`+`wash` = 보조색(`palette[1]`), `key` = 표준 팔레트의 웜화이트(새 RGB 금지). `color_usage=single` 일 때 네 그룹(`back`/`mover`/`side`/`wash`)이 같은 값을 받으면 선택을 합쳐 한 줄만 낸다(중복 줄 금지).

- 전제: M2/M3 완료(`mover`/`side`/`wash` 그룹 주소 확보).
- 회귀: `test_song_cue_color_emission.py`·`test_song_cue_white_preset_t453.py` 전량 PASS(흰색 프리셋 W 채널 로직 무변경 확인).
- **플래그(구현 시 재확인)**: `key` 웜화이트가 §6.3 "최대 2개" 집계에 포함되지 않는다는 이 SPEC 의 읽음(spec.md §3.2 [HARD])을 코드 주석에도 남긴다 — 다음 읽는 사람이 "왜 3색인데 §6.3 위반이 아닌가"를 바로 알 수 있게.

### M5 — 효과 기구 분리 (R3, M2 의 effect 역할 재사용)

REQ-LDRENDER-007, REQ-LDRENDER-008. `reviewed_song_commands` 가 비액센트 큐마다 `position_cue_bundle(sequence_no, plan, fids, extra_value_lines=(*color_lines, *_back_layer_value_lines(...), *_phaser_cue_value_lines(cue, fids, ...), *accent_lines))` 를 호출할 때 쓰는 **공유 `fids` 자체**에서 `effect` 역할 그룹 기구를 제외한다 — 별도의 "디머 전용 좁은 선택"을 만드는 것이 아니다(D3). 이렇게 하면 색·포지션·페이저 줄도 자동으로 effect 기구를 겨냥하지 않게 된다. 액센트 상승 방향 정정(REQ-008)은 이 제외가 선행된 뒤에만 의미가 있다.

- 회귀: t498 가 지정한 A1~A7·C 항목(기계 동작 PASS)이 깨지지 않는지 재확인 — 되읽기·트래킹·기존 쇼 보존 전부. (t497 은 spec.md §4 에서 **이 SPEC 의 범위 밖으로 판정**됐다 — 여기서는 t498/t497 두 리포트가 공유하는 Rain 기계-동작 회귀 스위트의 출처로만 인용하며, t497 자신의 결함 — 승인 밖 `ClearAll` — 은 이 마일스톤이 다루지 않는다.)

### M6 — 효과 송신 통로: 페이저 사전 생성 + 충돌 검출 (R4, 감독 결정 4, M1 측정 결과 소비)

REQ-LDRENDER-010, REQ-LDRENDER-011, REQ-LDRENDER-012. §C "R4 방법 — 감독 결정 4로 확정" 표의 옵션 (a)를 구현한다.

- `compose_fx`/`instantiate_fx` 선행 호출(`build_fx_preset_bundle`/`select_preset_number` 재사용) + **기존** 승인 카드 노출(새 경로 아님 — §D 제약).
- **충돌 사전 검출**: 콘솔 풀 재조회 후 지정 번호가 점유돼 있으면 FXLIB 의 기존 사유 코드(`PRESET_OCCUPIED` 등)로 거부·보고한다 — 새 충돌 검사 로직을 작성하지 않는다(`select_preset_number` 호출 재사용 여부를 코드 리뷰로 확인).
- **2스텝 페이저 생성**: 멀티스텝 번들 형상(`<값>` → `Step 2` → `<값>`)은 FXLIB/FXGEN 이 이미 구현했다 — 이 마일스톤은 그 호출만 한다, 새 저작 문법 금지.
- 콘솔 쓰기가 실제로 발생하는 유일한 마일스톤이므로, Implementation Kickoff Approval 과 별개로 이 마일스톤 착수 직전 감독에게 "지금부터 콘솔 풀에 프리셋이 생성된다"는 사실을 재확인시킨다(승인 카드 자체가 그 확인 수단이지만, 착수 시점에 다시 구두 확인 권장).

### M7 — 연출 판독 게이트 배선 (R7, M1 하네스 + M4 색 소비, LIT-only 집계 동치성)

REQ-LDRENDER-014, REQ-LDRENDER-015, REQ-LDRENDER-016. M1 이 제품화한 게이트 모듈을 송신 직전 호출 지점(`reviewed_song_commands` 호출부 또는 그 직후)에 배선하고, 경고를 기존 비차단 경고 채널(헤드룸 경고와 같은 표면)에 노출한다. **집계 규칙은 AC-001 과 바이트 동일해야 한다**(LIT-only, 큐-단위 — 과반/평균 금지, AC-012 가 교차검증). 두 대조군(Rain 고치기 전/통과 합성) 테스트를 작성한다.

## §F 안티패턴

- **R4 를 "FXLIB/FXGEN 재구현"으로 착수하지 마라** — `_phaser_cue_value_lines`(M3/M6 가 이미 가진 recall 메커니즘)를 먼저 호출 가능하게 만드는 것이 R4 다. 페이저 생성(M6)도 FXGEN 의 기존 `compose_fx`/충돌 거부 의미론을 재사용한다 — 새 저작 어휘·새 충돌 검사를 만들지 않는다.
- **"effect" 두 축을 하나로 합치려 들지 마라** — §B 위험 1. `RigLayers` 와 `RigInventory` 를 한 곳에서 선언하려는 리팩터는 이 SPEC 의 범위가 아니다(옳을 수도 있지만 별도 SPEC — 지금은 R3/R4 가 각자의 축만 쓴다).
- **R5/R6 디머 대역·회차 상승 로직에 손대지 마라** — `song_cue_composer.py` 의 `_dimmer_data`/후렴 비교 로직은 PRESERVE.
- **M2 를 건너뛰고 M3 부터 착수하지 마라** — REQ-001/AC-001 의 "3+ LIT 층" 목표는 M2 가 끝나야 달성 가능하다(§B 위험 8). M2 없이 M3 를 구현하면 AC-001 이 구조적으로 FAIL 한다.
- **정본 문서 편집 범위를 §2c 밖으로 넓히지 마라** — M2 는 역할 표만 고친다.

## §G 교차 참조

- `docs/proposals/song-structure-lighting-standard.md` §6.1~§6.3·§11.2(색·층·분위기 그룹 규율).
- `docs/proposals/song-lighting-design-standard.md` §2c(`RigProfile`/`RIG_LAYER_ROLES` 정본 — M2 가 편집 대상)·§4a I1(키/백/이펙트 3층 정의)·§4b C1/C3(팔레트 3~5색, 프런트 중립 유지) — D2/D6/감독 결정 1·3 의 정본 근거.
- `src/Lighting_Designer/01_스펙/LX-SEQ-SPEC-v2.1.md` §11.2 규칙 6(분위기 그룹 Intensity 정합 제외).
- `.moai/specs/SPEC-LDDESIGN-001/spec.md` §3.9(트래킹 모드)·§3.7(회차 에스컬레이션) — 이 SPEC 이 건드리지 않는 인접 축.
- `.moai/specs/SPEC-COPILOT-FXLIB-001/spec.md` REQ-FXLIB-012 (c)(프리셋 충돌 거부 의미론 — M6 재사용 대상).
