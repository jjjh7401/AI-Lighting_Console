# SPEC-LDRENDER-001 — 인수 기준 (Given-When-Then)

표기: 각 AC 는 측정 명령을 함께 적는다. "오프라인 판독"은 M1 이 제품화하는 게이트 모듈(구 `.moai/reports/t499/readout.py`) 을 8곡(또는 해당 곡)에 돌린 결과를 가리키며, 콘솔 접촉 없이 송신 명령 문자열만 검사한다. "실기"는 grandMA3 onPC 또는 실 콘솔 접촉을 요구하며 사람 육안 확인이 필요함을 의미한다.

## AC-LDRENDER-001 — 모든 구간 큐가 LIT(디머>0) 역할 3개 이상에서 서로 다른 값을 받는다 [REQ-LDRENDER-001]

> **감독 결정 2(2026-10-01) 전면 반영 — D11(과반 문구)·D12(key/back/effect 트리오 게이밍) 동시 해소.** 디머=0(꺼짐 — 비액센트 큐의 트래킹 상태 포함)인 역할은 "층"으로 세지 않는다. 판정은 구간 큐 단위다(전체의 과반·대다수가 아니다).

- **Given** 층 매핑이 확장된 `RIG_LAYER_ROLES`(`key`/`back`/`effect`/`audience`/`side`/`wash`/`mover`, REQ-002 적용 후) 중 `key`/`back` 을 포함해 2개 이상 역할을 해석한 곡의 송신 명령 목록
- **When** 오프라인 판독 게이트로 각 구간 큐의 역할별 값(디머·색)을 펼치고, 디머>0(LIT)인 역할만 골라 서로 다른 값 버킷을 세면(t499 §1 의 트래킹 가정은 "값을 안 받으면 직전 값을 잇는다"는 선택 집합 추적에만 쓰고, 꺼진 상태 자체는 버킷으로 세지 않는다)
- **Then** 구간 큐 **전부**(블랙아웃 큐 `cue.dimmer.blackout` 및 MIB 사전이동 큐 `cue.kind == "mib_premove"` 는 명시 예외 — 둘 다 정의상 정상 점등 상태가 아니다)가 LIT 역할 3개 이상에서 서로 다른 값을 받는다. "과반 이상"/"대다수" 등 완화된 기준은 **쓰지 않는다** — 단 1개 큐라도 미달이면 이 AC 는 FAIL 이다. **의존성 명시**: `effect` 는 R3(REQ-007)에 의해 비액센트 큐에서 항상 꺼져 있으므로 LIT 버킷에 들어가지 않는다 — 따라서 이 AC 는 `key`+`back` 만으로는 PASS 할 수 없고 `side`/`wash`/`mover`(REQ-002) 중 최소 1개가 그 큐에서 LIT 값을 받아야 한다
- **측정**: `uv run python -c "from server.design.ldrender_gate import layer_diversity; ..."`(M1 제품화 모듈, LIT-only 카운트 구현) 또는 과도기엔 `uv run python .moai/reports/t499/readout.py` 재사용 — §3.2 참조 레이어 카운트 산출(단 readout.py 자체가 LIT-only 를 이미 구현하는지 재확인 필요 — 안 하면 M1 제품화 단계에서 보강)

## AC-LDRENDER-002 — 역할 어휘 확장: 정본 버전 올림 + `RIG_LAYER_ROLES` + 그룹 이름 해석 [REQ-LDRENDER-002]

- **Given** `docs/proposals/song-lighting-design-standard.md` §2c 원본과, `SIDE-L`/`SIDE-R`/`SIDE-ALL`/`WASH-U`/`WASH-D`/`WASH-ALL`/`MOVER-U`/`MOVER-D`/`MOVER-ALL` 이름의 콘솔 그룹을 포함한 층 매핑 입력
- **When** REQ-002 구현(정본 §2c 편집+버전 올림, `rig.py:44` `RIG_LAYER_ROLES` 확장, `_LAYER_GROUP_ALIASES` 접두 토큰 추가)을 적용하고 `_build_layers` 에 `declared_layers={"side": ..., "wash": ..., "mover": ...}` 를 포함한 입력을 통과시키면
- **Then** (1) 정본 문서가 `side`/`wash`/`mover` 세 역할을 표에 담고 있고 문서 버전이 이전보다 높다, (2) `RIG_LAYER_ROLES` 가 그 셋을 포함한다, (3) `_build_layers` 는 `RigProfileError` 를 던지지 않고 수용한다, (4) 그룹 이름은 하이픈 앞 접두 토큰으로만 해석된다(`SIDE-L`→`side` 등, `SIDEWALK` 류 부분 문자열 오인 매칭 0건), (5) `test_layer_mapping_effect_role.py:119` `test_mover_and_wash_groups_remain_unmatched_documented_residual` 의 뒤집음이 테스트명·단언·docstring 갱신과 함께 명시적으로 이뤄졌다(조용히 깨지지 않았다). **다섯 조건 전부가 성립해야 AC-002 PASS 다 — 일부만 성립하면 FAIL 이다**(AC-013 의 쌍 판정 선례와 같은 규율, plan-auditor iter3 D13 반영)
- **측정**: `grep -c "side\|wash\|mover" docs/proposals/song-lighting-design-standard.md`(§2c 표 반영 확인) + `git log -1 --format=%s -- docs/proposals/song-lighting-design-standard.md`(버전 올림 커밋 확인) + `uv run python -c "from server.design.rig import RIG_LAYER_ROLES; assert {'side','wash','mover'} <= set(RIG_LAYER_ROLES)"` + `uv run pytest server/tests/test_layer_mapping_effect_role.py -q -k "mover_and_wash or side"`(뒤집힌 단언으로 PASS)

## AC-LDRENDER-003 — 단일 레이어 리그는 오늘과 바이트 동일 [REQ-LDRENDER-003]

- **Given** 층 매핑이 역할을 전혀 해석하지 못한(`_SINGLE_LAYER_WARNING`) 리그의 송신 입력
- **When** 송신기를 돌리면
- **Then** 출력 명령 목록이 이 SPEC 착수 전 커밋과 바이트 동일하다
- **측정**: `git stash` 없이 변경 전/후 두 트리에서 같은 입력으로 `reviewed_song_commands` 호출 → `diff`

## AC-LDRENDER-004 — 곡 전체 송신 색이 2~3종이고 구간 간 변화가 있으며, 감독 결정 3 의 층→색 배정이 지켜진다 [REQ-LDRENDER-004, REQ-LDRENDER-005]

- **Given** 설계 층 팔레트가 2개 이상 색을 담은 8곡(일부 팔레트는 3개 이상도 포함), 층 매핑이 `back`/`mover`/`side`/`wash`/`key` 를 해석한 상태
- **When** 오프라인 판독으로 (a) 곡당 고유 송신 RGB 집합, (b) 큐 1개가 동시에 내는 구별 **유채색**(웜화이트 제외) 수, (c) 역할별 수신 색을 각각 세면
- **Then** (a) 곡당 고유 송신 RGB 2~3개, 연속한 두 구간 큐 사이에 색이 바뀌는 지점이 1회 이상이다(8곡 전부 — 현재 7/8이 1색·0회 변화인 §6.3 위반이 해소됨). (b) 어느 큐도 동시에 3개 이상의 구별 유채색을 내지 않는다(`back`+`mover` = 지배색 1개, `side`+`wash` = 보조색 1개 — 이 둘만 §6.3 "최대 2개" 카운트 대상; `key` 의 웜화이트는 이 카운트에서 제외한다, 위 REQ-004 [HARD] 단락의 플래그 참조). (c) `back`/`mover` 역할 그룹은 지배색(`palette[0]`) 을, `side`/`wash` 역할 그룹은 보조색(`palette[1]`) 을, `key` 역할 그룹은 표준 팔레트의 웜화이트 색을 받는다 — 역할이 서로 다른데 같은 유채색을 받는 것은 FAIL
- **측정**: 제품화 게이트의 색 수·색 변화 횟수·큐당 동시 유채색 수·역할별 수신 색 산출 + `uv run pytest server/tests/test_song_cue_color_emission.py -q`

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
- **When** M1 측정 결과 + 감독 결정 4(옵션 a)를 구현한 송신기를 돌리면
- **Then** 오프라인 송신 목록에 `At Preset <pool>.<slot>` 류 페이저 recall 줄이 1줄 이상 존재한다(**기계 증거** — 줄의 존재, 풀에 없던 페이저는 REQ-011 의 사전 생성으로 메워졌다). 그 효과가 무대에서 실제로 보이는지는 **실기 육안 확인**(FXLIB/FXGEN 의 측정된 경계 — 사람 관측만 가능)으로 별도 기록한다
- **측정(기계)**: 제품화 게이트의 "송신 효과 줄 수" 산출 — `0` 이면 FAIL. **측정(사람)**: 실기 세션 체크리스트에 "페이저 육안 확인: PASS/FAIL" 항목 추가

## AC-LDRENDER-010 — 풀에 없는 페이저는 기존 승인 게이트를 거쳐 사전 생성되고, 번호 충돌은 덮어쓰지 않고 보고된다 [REQ-LDRENDER-011]

- **Given** 제안된 페이저 라벨이 콘솔 풀 재조회에서 해석되지 않는 큐
- **When** REQ-011(감독 결정 4, 옵션 a 확정)을 실행하면
- **Then** 해당 라벨이 `compose_fx`/`instantiate_fx`(`build_fx_preset_bundle`/`select_preset_number`) 경유로 사전 생성되고, 그 생성 커맨드는 **기존** `run_commands` → `gate.screen()` 승인 게이트를 통과한다(새 무승인 경로가 생기지 않았음을 `grep` 으로 확인 가능해야 한다), 다음 재조회에서 그 라벨이 해석된다
- **Given (충돌 대조)** 생성하려는 프리셋 번호가 콘솔 풀 재조회 결과 이미 점유된 경우
- **When** 같은 생성 경로를 실행하면
- **Then** 기존 번호를 **덮어쓰지 않고**, FXLIB 의 기존 사유 코드(`PRESET_POOL_UNAVAILABLE`/`PRESET_POOL_TRUNCATED`/`PRESET_NUMBER_UNAVAILABLE`/`PRESET_OCCUPIED`) 중 해당하는 것으로 생성을 거부·보고한다(새 충돌 검사 로직을 발명하지 않고 `select_preset_number` 를 재사용했는지 코드로 확인 가능해야 한다)
- **측정**: `grep -rn "gate.screen\|run_commands" <페이저 생성 모듈>` (단일 관문 확인) + `uv run pytest server/tests/test_fx_instantiate.py -q -k "preset_occupied or collision"`(기존 FXLIB 충돌 테스트 재사용/확장) + 신규 단위 테스트(이 SPEC 의 페이저-생성 호출부가 점유 슬롯에서 거부를 받아 전파하는지)

## AC-LDRENDER-011 — 효과 보고가 요청/허용/송신 3계로 구분된다 [REQ-LDRENDER-012]

- **Given** 효과 관련 리뷰/보고 문면
- **When** 임의의 곡 1개를 송신하면
- **Then** 보고에 `fx.requested`·`fx.permitted`·송신 줄 수 3개 숫자가 각각 구분되어 나타난다(하나로 뭉뚱그려 "효과 처리됨"으로 적지 않는다)
- **측정**: 보고 페이로드/문자열에서 세 키(또는 세 레이블) 존재 여부 assert

## AC-LDRENDER-012 — 연출 판독 게이트가 임포트 가능한 모듈로 승격되고, AC-001 과 동일한 LIT-only·큐-단위 집계를 쓴다 [REQ-LDRENDER-013]

- **Given** M1 완료
- **When** `server/design/` 아래에서 그 게이트 함수를 임포트하면
- **Then** 별도 CLI 프로세스 기동 없이 함수 호출만으로 판정 결과(색 수·LIT 층 수·효과 줄 수 + 위반 여부)를 얻는다. **집계 동치성**: 같은 송신 목록에 대해 이 게이트의 "층 수"와 AC-001 이 직접 센 "LIT 층 수"가 일치한다 — 게이트가 디머=0 상태를 층으로 세거나 과반/평균으로 판정을 완화하면 FAIL
- **측정**: `uv run python -c "from server.design import ldrender_gate; print(ldrender_gate.evaluate(...))"` (모듈명은 구현 시 확정) + 같은 입력에 대해 게이트 결과와 AC-001 수동 집계 결과를 비교하는 교차검증 테스트

## AC-LDRENDER-013 — 게이트 양성·음성 대조 — Rain 전/통과 합성 모두 (LIT-only·큐-단위) [REQ-LDRENDER-016]

- **Given (음성 대조)** t498 가 기록한 Rain 고치기 전 송신 목록(색 1·LIT 층 2·효과 0 — 전 구간 큐 공통)
- **When** REQ-013 게이트(LIT-only, 큐-단위 — 과반 아님)에 통과시키면
- **Then** 경고가 발동한다(색 2~3 미만, LIT 층 3 미만인 구간 큐가 하나라도 존재, 효과 요청 대비 송신 0 중 최소 하나를 사유로 기록)
- **Given (양성 대조)** 색 3종·**모든** 구간 큐가 LIT 층 3개 이상·효과 요청 곡에 효과 줄 1개 이상인 합성(날조) 송신 목록
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

- **2-역할 잔여 리그(발명하지 않고 플래그, spec.md §3.1 [HARD] 단락과 동일)** — 층 매핑이 `key`+`back` 둘만 해석하고 그 리그에 `side`/`wash`/`mover`/`audience` 그룹 자체가 없는 경우, REQ-002 구현 후에도 그 곡은 구조적으로 LIT 층 3개에 도달할 수 없다 — AC-001 은 이 경우 FAIL 하며, 이 SPEC 은 이를 새 REQ 로 메우지 않는다(감독의 4건 결정 범위 밖, 후속 카드 후보로 기록).
- **블랙아웃/MIB 사전이동 큐** — AC-001 의 "구간 큐 전부" 요구에서 명시 예외(위 AC-001 본문).
- DinoDino 의 "우연한 2색"(구간 분할 큐 팔레트 회전, 추정) — 이 SPEC 의 AC-004 는 송신 색 수만 재므로 DinoDino 는 이미 통과 측에 있을 수 있다. 의도된 변화로 재분류되는지는 이 SPEC 의 범위 밖(§4 색 정밀 매칭 제외 참조).
- **key 웜화이트의 §6.3 집계 포함 여부** — spec.md §3.2 [HARD] 단락에 플래그된 해석 긴장. AC-004(b)는 이 SPEC 의 읽음(웜화이트 제외)을 전제로 측정한다 — 그 읽음이 틀렸다고 판명되면 AC-004(b)도 재확인이 필요하다.

## Definition of Done

- [ ] REQ-001~016 전부 구현 + 위 AC 전부 PASS(사람 판정 AC-016 은 실기 세션 일정에 따름 — plan-phase 종료 조건이 아니라 run-phase 종료 조건).
- [ ] `golangci-lint`/해당 없음(Python 프로젝트) 대신 `ruff check`·`pytest --cov`(85% 이상, 변경 모듈 한정) 통과.
- [ ] t498 회귀 스위트(AC-015) PASS.
- [ ] progress.md §E 에 M1 측정 결과(코드 판독/잰 값 등급 명시)와 감독 결정 1~4(역할 어휘·LIT 집계·층→색 배정·R4 방법) 의 구현 결과가 기록됨 — §5 열린 결정은 0건이므로 더 이상 "결정 확정 결과"가 아니라 "구현 결과"만 남는다.
