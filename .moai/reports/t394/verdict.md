# t394 판정 — bridge 구간 무빙·이펙트 정지

## 측정 요약 (before/after)

`/private/tmp/claude-501/t394_probe/probe.py` (9구간, 40-fixture 리그, 정본 예시
그대로) 를 고치기 전/후 각각 실행.

**before**
```
label     role       D   fade_s       tier                  fx_permitted density  speed_beats  accents
Intro     intro      2    1.905     narrow                            ()       0         None  ()
Verse 1   verse      3    1.429     medium                 ('slow pan',)       1          1.0  ()
Chorus 1  chorus     5    0.238        max ('dimmer chase', 'pan sweep')       2          2.0  ()
Verse 2   verse      3    1.429     medium                 ('slow pan',)       1          1.0  ()
Chorus 2  chorus     5    0.238        max ('dimmer chase', 'pan sweep')       2          2.0  ()
Bridge    bridge     2    1.905     narrow                ('slow tilt',)       1         0.25  ()
Breakdown bridge     1    3.810     narrow                            ()       1         None  ()
Chorus 3  chorus     5    0.238        max ('dimmer chase', 'pan sweep')       2          2.0  ('white flash',)
Finale    finale     5    3.810        max('dimmer chase', 'accent sweep')       2          2.0  ('white flash',)
```

**after**
```
Bridge    bridge     2    1.905     narrow                            ()       0         None  ()
Breakdown bridge     1    3.810     narrow                            ()       0         None  ()
```
(나머지 7행은 바이트 동일 — `diff` 로 확인.)

## 결함 위치

- `server/design/song_cue_composer.py:_section_cue` — fx/position width tier 를
  `axis_budget(decision.d.level, ...)` 로만 정하고, role 조건은 오직 fade
  (`_fade_seconds_for_role`, 카드 t386)에만 있었다.
- role "bridge" 구간(session.py `_infer_confirmed_role` 이 breakdown 도 여기로
  접는다) 이 D2/D3 에서 `fx.permitted != ()` 로 나와 §6 "무빙·이펙트 정지"를
  어겼다. D1 은 예산이 우연히 0이라 `permitted` 만 비어 있었고 `density` 는
  요청값(1)을 그대로 들고 있었다.

## 고침

`_fx_data_for_role` / `_position_width_for_role` 두 헬퍼를 `_fade_seconds_for_role`
과 같은 자리·같은 문체로 추가 — `decision.role == "bridge"` 면 D 레벨과 무관하게
fx 를 `permitted=() density=0 speed_beats=None` 으로, 포지션 폭 타이어를
`POSITION_WIDTH_TIERS[0]`("narrow")로 고정한다. 밝기(디머)·페이드는 건드리지
않는다(두 축 분리, t386 과 같은 원칙).

## RED → GREEN

RED(고치기 전, 6개 중 4개 실패):
```
FAILED test_bridge_at_d2_has_no_permitted_fx
FAILED test_bridge_at_d3_has_no_permitted_fx
FAILED test_bridge_position_width_tier_is_forced_to_the_lowest
FAILED test_bridge_at_d1_gets_the_same_stop_role_aware_fix_applies_uniformly
4 failed, 2 passed in 0.06s
```

GREEN(고친 후): `server/tests/test_song_cue_role_stop_t394.py` 7개 전부 PASS.

## AC 매핑

- AC-1: `test_song_cue_role_stop_t394.py::TestBridgeStopsMovementAndEffectRegardlessOfDLevel` (D2/D3/D1 세 케이스) — PASS.
- AC-2: 같은 파일 `TestCharacterizationOnlyBridgeRoleRowsChange` — 9행 중 bridge role
  두 행(Bridge/Breakdown)만 fx/movement 열이 바뀜을 확인. **주의**: Breakdown(D1)
  행의 `density` 필드는 1→0 으로도 바뀐다(고치기 전엔 `permitted` 만 비었고
  `density` 는 요청값을 그대로 들고 있었다 — §6 의도에는 오히려 더 가까워지는
  강화다. 카드 본문의 "D1 은 이미 만족" 서술은 `permitted`/`effect`(director 가
  보는 값) 기준이고, 내부 `density` int 까지 바이트 동일은 아니다 — 이 차이를
  숨기지 않고 테스트에 명시했다).
- AC-3: 가드 7개 파일(t386/composer/t393/t402/t403/timeline/web_session) 466개
  전부 PASS, 기대값 변경 없음. 전체 스위트 `uv run pytest -q` 13684 passed, 35
  skipped, exit 0.
- AC-4: `server/tests/test_song_timeline_cue_sheet_producer.py::TestEmittedSectionFields::
  test_effect_is_absent_for_a_bridge_role_cue_even_when_fx_was_requested` 추가 —
  director 가 보는 큐시트 타임라인 payload(`_song_timeline_payload` → `effect`
  키)에서 bridge 큐는 `fx.allowed` 요청이 있어도 `effect` 키가 안 뜬다는 것까지
  확인. `movement`(포지션 프리셋, MOVE 칸)는 이 카드가 건드리는 축이 아니다 —
  `cue.position.stored`(director 가 지정한 프리셋)는 그대로 두고, 스포셜 예산
  폭(`width_tier`)만 최저로 고정했다. 두 개념이 다르다는 점(§6 의 "무빙"은 이
  코드베이스에서 FX 이펙트 무빙(slow tilt 등)을 가리키고, `movement` payload
  필드는 director 가 명시한 포지션 프리셋을 가리킨다)을 보고서에 명시한다.

## 남겨둔 것 (안 잰 것)

- 실기 콘솔·시각 확인: 안 함(이 카드 범위는 서버 로직).
- §6.1 컬러 스냅 악센트, 클라이맥스 지속시간 상한(1-4박): 범위 밖 — 별도 카드로.
- `movement`(포지션 프리셋 MOVE 칸)가 bridge 에서 실제로 정지되어야 하는지는
  §6 표에 명시가 없다(표는 "무빙"을 이펙트 묶음으로만 나열) — 이번 고침은
  포지션 **폭**(spatial spread)만 최저로 고정했을 뿐, 프리셋 자체(예: "Center")는
  그대로 살아있다. 이 구분이 §6 의도와 맞는지는 감독 확인이 필요할 수 있다.
