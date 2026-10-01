# SPEC-LDRENDER-001 — 인수 기준 (Given-When-Then)

표기: 각 AC 는 측정 명령을 함께 적는다. "오프라인 판독"은 M1 이 제품화하는 게이트 모듈(구 `.moai/reports/t499/readout.py`) 을 8곡(또는 해당 곡)에 돌린 결과를 가리키며, 콘솔 접촉 없이 송신 명령 문자열만 검사한다. "실기"는 grandMA3 onPC 또는 실 콘솔 접촉을 요구하며 사람 육안 확인이 필요함을 의미한다.

## AC-LDRENDER-001 — 구간 큐마다 3개 이상의 층이 다른 값을 받는다 [REQ-LDRENDER-001]

- **Given** 층 매핑이 `RIG_LAYER_ROLES` 닫힌 어휘 `key`/`back`/`effect` 중 2개 이상 역할을 해석한 곡의 송신 명령 목록(`audience` 는 이 리그에 매핑 그룹이 없어 제외)
- **When** 오프라인 판독 게이트로 각 구간 큐의 역할별 값(디머·색)을 펼쳐 세면 — t499 §1 의 트래킹 가정(값을 안 받은 기구는 직전 값을 잇는다)을 그대로 적용
- **Then** `key`(또는 전체 기본) 값·`back` 값·`effect`(비액센트 큐에서는 공유 `fids` 제외로 트래킹된 별개 상태) 값이 서로 다른 3개 버킷을 이루는 구간 큐가 전체 구간 큐 중 과반 이상이다(전 큐 ≤2 였던 t499 §2 §6.2 위반이 해소됨) — SIDE/WASH/MOVER 세분화(REQ-002, §5 결정 2 미확정) 없이도 이 AC 는 PASS 해야 한다
- **측정**: `uv run python -c "from server.design.ldrender_gate import layer_diversity; ..."`(M1 제품화 모듈) 또는 과도기엔 `uv run python .moai/reports/t499/readout.py` 재사용 — §3.2 참조 레이어 카운트 산출

## AC-LDRENDER-002 — SIDE/WASH/MOVER 그룹의 역할 해석 (§5 결정 2 확정 후에만 발동) [REQ-LDRENDER-002]

- **상태**: REQ-LDRENDER-002 는 §5 결정 2(옵션 a/b/c) 확정 전까지 **보류**다 — 이 AC 는 그 결정이 내려진 뒤에만 PASS/FAIL 판정 대상이며, M2 완료 조건(AC-001)에는 포함되지 않는다.
- **Given** `SIDE-L`/`SIDE-R`/`WASH-U`/`WASH-D`/`MOVER-U`/`MOVER-D` 이름의 콘솔 그룹을 포함한 층 매핑 입력, §5 결정 2 가 (a) 또는 (c)로 확정된 상태
- **When** 역할 해석 경로(결정에 따라 `_LAYER_GROUP_ALIASES` 확장 또는 원시 `layer_mapping` 리스트의 역할 없는 그룹-번호 주소)를 거치면
- **Then** (a)/(c) 각각의 형상대로 그룹이 식별되고, 부분 문자열 추측 없이 접두 토큰 정확 일치로만 성립한다(`SIDEWALK` 류 오인 매칭 0건). §5 결정 2 가 (b)로 확정되면 이 AC 는 "SIDE/WASH/MOVER 가 `back`/`effect` 와 동일 값을 받는다"로 재작성한다(별도 층 버킷을 만들지 않음, §5 결정 2 (b) 설명 참조)
- **측정**: `uv run pytest server/tests/test_layer_mapping_effect_role.py -q -k "mover_and_wash or side"` — 기존 `test_mover_and_wash_groups_remain_unmatched_documented_residual` 의 단언이 뒤집혀 PASS(결정이 (a)/(c)일 때만; (b)일 때는 해당 테스트의 "역할 미매칭" 단언이 "effect/back 으로 흡수됨" 단언으로 교체된다)

## AC-LDRENDER-003 — 단일 레이어 리그는 오늘과 바이트 동일 [REQ-LDRENDER-003]

- **Given** 층 매핑이 역할을 전혀 해석하지 못한(`_SINGLE_LAYER_WARNING`) 리그의 송신 입력
- **When** 송신기를 돌리면
- **Then** 출력 명령 목록이 이 SPEC 착수 전 커밋과 바이트 동일하다
- **측정**: `git stash` 없이 변경 전/후 두 트리에서 같은 입력으로 `reviewed_song_commands` 호출 → `diff`

## AC-LDRENDER-004 — 곡 전체 송신 색이 2~3종이고 구간 간 변화가 있으며, 한 큐의 동시 색은 최대 2개다 [REQ-LDRENDER-004, REQ-LDRENDER-005]

- **Given** 설계 층 팔레트가 2개 이상 색을 담은 8곡(일부 팔레트는 3개 이상도 포함)
- **When** 오프라인 판독으로 (a) 곡당 고유 송신 RGB 집합과 (b) 큐 1개가 동시에 내는 구별 RGB 수를 각각 세면
- **Then** (a) 곡당 고유 송신 RGB 2~3개, 연속한 두 구간 큐 사이에 색이 바뀌는 지점이 1회 이상이다(8곡 전부 — 현재 7/8이 1색·0회 변화인 §6.3 위반이 해소됨). (b) **어느 큐도 동시에 3개 이상의 구별 RGB 를 내지 않는다**(§6.3 "최대 2개" 상한 — `len(palette) > 2`인 큐에서도 성립). 역할→색 배정(§5 결정 3)이 아직 미확정이어도 (a)/(b) 두 수치는 측정·PASS 가능하다(배정은 "어느 역할이 무엇을 받는가"이지 "몇 색이 나가는가"가 아니므로 독립적으로 검증된다)
- **측정**: 제품화 게이트의 색 수·색 변화 횟수·큐당 동시 색 수 산출 + `uv run pytest server/tests/test_song_cue_color_emission.py -q`

## AC-LDRENDER-005 — `color_usage` 비기본 모드는 회귀 없이 그대로 소비된다 [REQ-LDRENDER-006]

- **Given** `color_usage="modulate"`(기본)로 고정된 회귀 픽스처
- **When** 보조색 송신(REQ-004)을 적용한 새 송신기를 돌리면
- **Then** `modulate` 경로는 이 SPEC 적용 전후 바이트 동일하고(단, 보조색 줄이 **추가**되는 것은 의도된 변화이므로 "값 줄 추가분 제외하고 바이트 동일" 기준으로 비교), `single`/`per_chorus` 는 `_section_palette_choice` 가 낸 값을 그대로 옮긴 결과와 일치한다
- **측정**: `uv run pytest server/tests/test_song_cue_color_emission.py server/tests/test_song_cue_white_preset_t453.py -q`(SPEC-COPILOT-COLORMODE-001 회귀 스위트 포함)

## AC-LDRENDER-006 — 효과 기구가 비액센트 큐의 모든 값 줄(디머·색·포지션·페이저)에서 빠진다 [REQ-LDRENDER-007]

- **Given** BLIND/STROBE/HAZE 역할(`effect`)이 해석된 층 매핑
- **When** 비액센트 구간 큐가 공유하는 `fids` 선택과, 그 `fids` 로부터 파생되는 **4종 값 줄 전부**(전체 기구 디머, `_song_color_value_lines` 의 색 줄, `position_cue_bundle` 의 포지션 프리셋 줄, `_phaser_cue_value_lines` 의 페이저 recall 줄)를 각각 검사하면
- **Then** 4종 값 줄 전부에서 그 선택 집합에 `effect` 역할 그룹의 기구가 포함되지 않는다(8곡 전부 — 현재 86대 전체 묶음에 효과 기구가 끼어 있는 P3′ 위반이 해소됨; 디머 줄만 좁히고 색/포지션/페이저 줄이 여전히 effect 기구를 겨냥하는 상태는 FAIL)
- **측정**: 제품화 게이트의 "비액센트 큐 4종 값 줄의 `fids` ∩ effect 그룹 = ∅" 산출(각 값 줄 종류별로 개별 assert) + `uv run pytest server/tests/test_layer_mapping_effect_role.py server/tests/test_song_cue_color_emission.py -q`(새 테스트 케이스로 색/포지션/페이저 라인의 effect 제외를 추가 단언)

## AC-LDRENDER-007 — 블라인더 액센트는 상승이다, 하강이 아니다 [REQ-LDRENDER-008]

- **Given** 절정 큐가 블라인더 액센트를 켜는 송신 목록
- **When** 그 액센트 줄의 값을 직전(비점등) 상태와 비교하면
- **Then** 값이 **상승**(0 또는 낮은 값 → 높은 값)하며, REQ-007 적용 후 그 직전에 같은 그룹에 더 높은 값을 주는 경쟁 줄(전체 디머)이 존재하지 않는다(t498 큐 11 의 100→80 역방향 재현 0건)
- **측정**: Rain 송신 목록 재현(`.moai/reports/t498/`)에 패치 적용 후 재실행, 블라인더 그룹 값 시퀀스 assert

## AC-LDRENDER-008 — `fx.permitted=0` 원인이 측정값으로 확정된다 [REQ-LDRENDER-009]

- **Given** M1 착수
- **When** `RigInventory.capability_fids["effect"]` 채움 경로를 코드 판독 + 실기(또는 동형 패치 데이터)로 대조하면
- **Then** progress.md 에 원인이 "코드 판독"/"잰 값" 등급으로 명시되고 "추정"으로 남지 않는다 — 긍정(능력 선언 경로가 실제로 존재하나 호출되지 않음) 또는 부정(선언 경로 자체가 프로덕션에 배선되지 않음) 중 하나로 확정
- **측정**: progress.md §E.2 M1 절의 등급 표기 확인(코드 판독 파일:줄 + 실측 결과 인용 여부)

## AC-LDRENDER-009 — 효과를 요청한 곡은 송신 효과 줄 1줄 이상 [REQ-LDRENDER-010, REQ-LDRENDER-011]

- **Given** 설계 층 `fx.requested` > 0 인 곡
- **When** M1 확정 방법(§5 결정 1)을 구현한 송신기를 돌리면
- **Then** 오프라인 송신 목록에 `At Preset <pool>.<slot>` 류 페이저 recall 줄이 1줄 이상 존재한다(**기계 증거** — 줄의 존재). 그 효과가 무대에서 실제로 보이는지는 **실기 육안 확인**(FXLIB/FXGEN 의 측정된 경계 — 사람 관측만 가능)으로 별도 기록한다
- **측정(기계)**: 제품화 게이트의 "송신 효과 줄 수" 산출 — `0` 이면 FAIL. **측정(사람)**: 실기 세션 체크리스트에 "페이저 육안 확인: PASS/FAIL" 항목 추가

## AC-LDRENDER-010 — 풀에 없는 페이저의 처리가 결정된 방법과 일치한다 [REQ-LDRENDER-011]

- **Given** 제안된 페이저 라벨이 콘솔 풀 재조회에서 해석되지 않는 큐
- **When** §5 결정 1 이 (a) 라면
- **Then** 해당 라벨이 `compose_fx`/`instantiate_fx` 경유로 사전 생성되고 승인 카드가 발급된 뒤 재조회에서 해석된다
- **When** §5 결정 1 이 (b) 라면
- **Then** 콘솔 쓰기 없이, 그 사유가 감독이 보는 리뷰 표면(변경 스택 또는 분석 요약)에 노출된다(회신에만 묻히지 않는다)
- **측정**: 선택된 분기에 해당하는 단위 테스트 1종 + 수동 리뷰 표면 스크린샷 또는 페이로드 검사

## AC-LDRENDER-011 — 효과 보고가 요청/허용/송신 3계로 구분된다 [REQ-LDRENDER-012]

- **Given** 효과 관련 리뷰/보고 문면
- **When** 임의의 곡 1개를 송신하면
- **Then** 보고에 `fx.requested`·`fx.permitted`·송신 줄 수 3개 숫자가 각각 구분되어 나타난다(하나로 뭉뚱그려 "효과 처리됨"으로 적지 않는다)
- **측정**: 보고 페이로드/문자열에서 세 키(또는 세 레이블) 존재 여부 assert

## AC-LDRENDER-012 — 연출 판독 게이트가 임포트 가능한 모듈로 승격된다 [REQ-LDRENDER-013]

- **Given** M1 완료
- **When** `server/design/` 아래에서 그 게이트 함수를 임포트하면
- **Then** 별도 CLI 프로세스 기동 없이 함수 호출만으로 판정 결과(색 수·층 수·효과 줄 수 + 위반 여부)를 얻는다
- **측정**: `uv run python -c "from server.design import ldrender_gate; print(ldrender_gate.evaluate(...))"` (모듈명은 구현 시 확정)

## AC-LDRENDER-013 — 게이트 양성·음성 대조 — Rain 전/통과 합성 모두 [REQ-LDRENDER-016]

- **Given (음성 대조)** t498 가 기록한 Rain 고치기 전 송신 목록(색 1·층 2·효과 0)
- **When** REQ-013 게이트에 통과시키면
- **Then** 경고가 발동한다(색 2~3 미만, 층 3 미만 구간 큐 존재, 효과 요청 대비 송신 0 중 최소 하나를 사유로 기록)
- **Given (양성 대조)** 색 3종·구간 큐마다 층 3개 이상·효과 요청 곡에 효과 줄 1개 이상인 합성(날조) 송신 목록
- **When** 같은 게이트에 통과시키면
- **Then** 경고가 발동하지 않는다 — 두 대조군이 한 쌍으로 PASS 해야 게이트가 "쏘면 걸리는" 장치임이 증명된다(어느 한쪽만 PASS 하면 공허한 검사)
- **측정**: `uv run pytest server/tests/test_ldrender_gate.py -q -k "rain_before_fix or passing_synthetic"`(신규 작성, 두 대조군을 같은 파일에 쌍으로 둔다)

## AC-LDRENDER-014 — 비기본 `palette_mode` 는 색 경고에서 n/a [REQ-LDRENDER-015]

- **Given** `palette_mode="single"`(또는 `per_chorus`)로 확정된 곡
- **When** 그 곡의 색 수가 2~3 범위 밖이어도
- **Then** 게이트는 그 축을 n/a 로 표기하고 FAIL 로 세지 않는다
- **측정**: `uv run pytest server/tests/test_ldrender_gate.py -q -k palette_mode_na`(같은 신규 파일)

## AC-LDRENDER-015 — 회귀: t498 A1~A7·C 항목이 그대로 유지된다 [전체 REQ 공통 비파괴 조건]

- **Given** 이 SPEC 적용 후의 송신기
- **When** t498 의 기계 동작 판정 스위트(곡 분석 재현·게이트·결정성·승인=송신·승인 밖 명령·실기 쓰기 성공·되읽기·기존 쇼 보존·백업·번호 충돌)를 재실행하면
- **Then** 전부 이전과 동일하게 PASS 한다(새 역할별 값 줄이 추가되어도 승인=송신 일치, 트래킹 규율, 번호 충돌 회피는 깨지지 않는다)
- **측정**: `.moai/reports/t498/` 의 재현 스크립트(`rehearse_rain.py` 류)를 이 SPEC 적용 후 트리에서 재실행

## AC-LDRENDER-016 — 실기 감독 판정 ≥3점 (판독을 통과한 곡만, 사람 판정) [인간 판정 AC]

- **Given** AC-001~015 오프라인 판독을 통과한 곡
- **When** 실 콘솔에 올려 감독이 육안으로 판정하면
- **Then** 곡 점수가 5점 만점 중 3점 이상이다 — **이 AC 는 사람이 판정하며 기계로 대체 불가**
- **측정**: 실기 세션 체크리스트에 감독 점수 기록(t498 §1 B3~B12 선례 형식)

## 검증 요약 — REQ → AC 추적표

| REQ | 검증 AC |
|---|---|
| REQ-LDRENDER-001 | AC-001 |
| REQ-LDRENDER-002 | AC-002 |
| REQ-LDRENDER-003 | AC-003 |
| REQ-LDRENDER-004 | AC-004 |
| REQ-LDRENDER-005 | AC-004 |
| REQ-LDRENDER-006 | AC-005 |
| REQ-LDRENDER-007 | AC-006 |
| REQ-LDRENDER-008 | AC-007 |
| REQ-LDRENDER-009 | AC-008 |
| REQ-LDRENDER-010 | AC-009 |
| REQ-LDRENDER-011 | AC-009, AC-010 |
| REQ-LDRENDER-012 | AC-011 |
| REQ-LDRENDER-013 | AC-012 |
| REQ-LDRENDER-014 | AC-013 |
| REQ-LDRENDER-015 | AC-014 |
| REQ-LDRENDER-016 | AC-013 |

모든 REQ 가 최소 1개 AC 로 검증되며(orphan 없음), AC-015·AC-016 은 전체 REQ 공통 비파괴/인간 판정 조건으로 특정 REQ 에 1:1 대응하지 않는다.

## 경계 사례

- 층 매핑이 부분적으로만 해석된 리그(예: KEY·BACK 만 해석되고 SIDE/WASH/MOVER 는 미해석) — REQ-001 은 "2개 이상"을 요구하므로 이 경우도 다중 역할 렌더링이 발동해야 한다(AC-001 의 "3개 이상" 목표는 미달일 수 있으나 경고로만 기록, §6.2 식 FAIL 이 아니라 부분 매핑으로 분류).
- DinoDino 의 "우연한 2색"(구간 분할 큐 팔레트 회전, 추정) — 이 SPEC 의 AC-004 는 송신 색 수만 재므로 DinoDino 는 이미 통과 측에 있을 수 있다. 의도된 변화로 재분류되는지는 이 SPEC 의 범위 밖(§4 색 정밀 매칭 제외 참조).

## Definition of Done

- [ ] REQ-001~016 전부 구현 + 위 AC 전부 PASS(사람 판정 AC-016 은 실기 세션 일정에 따름 — plan-phase 종료 조건이 아니라 run-phase 종료 조건).
- [ ] `golangci-lint`/해당 없음(Python 프로젝트) 대신 `ruff check`·`pytest --cov`(85% 이상, 변경 모듈 한정) 통과.
- [ ] t498 회귀 스위트(AC-015) PASS.
- [ ] progress.md §E 에 M1 측정 결과(코드 판독/잰 값 등급 명시)와 §5 결정 1·2 의 확정 결과가 기록됨.
