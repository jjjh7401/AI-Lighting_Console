# t222 — 퇴화한 리그를 거절한다 (거짓 초록 3행 제거)

브랜치 `WT-degenerate-guard` · base `origin/WT-pos-reach` `674d984`
(그 위는 `origin/WT-pos-join` `7f16e6b` / PR #270 — **둘 다 아직 main 이 아니다**)
2026-09-01 · 콘솔 LIVE(onPC 2.4.2, `--listen-port 9005`) · **콘솔 쓰기 0건**

## 0. 한 줄

t221 이 진단한 「살아남은 세 행이 거짓 초록」을 껐다. **정직한 거절이 거짓 초록보다 낫다.**
이 카드는 큐를 하나도 열지 않는다 — 사고를 막을 뿐이고 병목은 여전히 좌표 데이터다.

## 1. 재현 (구현 전, base 소스)

`evidence/t222_before.py` — 순수 함수에 t221 실측 상태(전 대상 좌표 0.0)를 그대로 넣는다.
콘솔 접촉 0.

    좌표 대수: 86
    derived : ['POS.01', 'POS.05', 'POS.06']
       POS.01 n=6  pan [180.0] tilt [128.7]
       POS.05 n=16 pan [-178.0 … 178.0] tilt [45.0]
       POS.06 n=18 pan [180.0] tilt [128.7]
    skipped : [('POS.02','unaimable'), ('POS.03','unaimable'), ('POS.04','unaimable')]

t221 의 판정과 행 단위로 일치한다(독립 재현). 저장본 `evidence/before.txt` 는
구현 뒤 base 소스를 되돌려 다시 돌린 것과 **바이트 동일**했다.

그리고 접힌 사유도 그 자리에서 쟀다(`evidence/before_reasons.txt`):

    POS.02: ('unaimable', '대상 8대 전부 조준 한계 밖 또는 계산 불가')
    POS.04: ('unaimable', '대상 8대 전부 조준 한계 밖 또는 계산 불가')
    바이트 동일: True

## 2. 술어 — 두 후보를 코퍼스에 대고 재서 골랐다

취향이 아니라 실측이다. `evidence/t222_predicate_probe.py` -> `evidence/predicate.txt`.
코퍼스 8종(live 콘솔 리그 + 합성 7). live 리그는 t221 이 저장한 응답 원문을 읽는다.

| rig | A(span=0) | A(span<=0.05) | **C(수평면<=0.05)** | B(low_confidence) | B 사유 | C~B |
|---|---|---|---|---|---|---|
| live_86_console | True | True | **True** | True | no_spatial_spread | agree |
| synthetic_12 | False | False | **False** | False | — | agree |
| weak_gaps_20 | False | False | **False** | False | — | agree |
| vertical_only_8 | False | False | **True** | True | vertical_spread_only | agree |
| even_depth_9 | False | False | **False** | True | weak_gap_separation | **DISAGREE** |
| single_bar_9 | False | False | **False** | False | — | agree |
| single_fixture_1 | True | True | **True** | True | no_spatial_spread | agree |
| tiny_spread_6 | False | True | **True** | True | no_spatial_spread | agree |

**두 후보의 경계는 겹치지 않는다.**

- **후보 B(도구의 `low_confidence` 를 그대로 신뢰) 는 과잉 거절한다.** `even_depth_9`
  는 x 폭 4m · y 폭 8m 의 **멀쩡한 리그**다 — 등분도 조준도 성립한다. B 가 참인 이유는
  y 가 등간격이라 열 분할이 모호해서일 뿐이다. `low_confidence` 가 답하는 질문은
  「열 분할이 모호한가」이고, 이 카드의 질문은 「조준할 폭이 있는가」다. 다른 질문이다.
- **후보 A 를 span 정확히 0 으로 잡으면 과소 거절한다.** `vertical_only_8`(x·y 는 한 점,
  z 만 벌어짐)과 `tiny_spread_6`(노이즈 폭 아래 편차)을 놓친다. 둘 다 목표점이 한 점으로
  접혀 산출이 무의미하다.

**채택: C — 수평면(x·y) span 이 `SPATIAL_ROW_NOISE_SPAN`(0.05m) 이하.**
코퍼스 8종에서 C 는 `low_confidence and confidence_reason in
(no_spatial_spread, vertical_spread_only)` 와 **전부 일치**했다 — 즉 B 의 부분집합을
순수 함수 안에서 재현한다. 라이브 도구 응답을 순수 모듈로 끌고 들어오지 않아도 같은
판정이 선다.

두 가지를 일부러 했다:

- **z 는 뺐다.** 한 트러스에 매단 리그는 z span 이 0 이고 그것이 정상이다. 세 축을 다
  요구하면 가장 흔한 리그를 거절한다(`single_bar_9`). 뮤턴트 M3 이 이 축을 지킨다.
- **임계는 빌려 쓴다.** `server.spatial.rows.SPATIAL_ROW_NOISE_SPAN` 을 그대로 든다 —
  숫자를 다시 적으면 한쪽만 바뀌는 날 두 판정이 조용히 갈린다.

## 3. 세 행이 지금 무엇을 하나

`server/lxseq/position_derive.py` `rig_is_degenerate` 가 참이면 **전 행**을
`degenerate_rig` 사유로 거절한다.

| 행 | 전 | 후 |
|---|---|---|
| POS.01 | 초록 · KEY 6대 `Pan 180 / Tilt 128.7` | `degenerate_rig` |
| POS.05 | 초록 · MOVER-ALL 16대 부채꼴 (좌표 미사용) | `degenerate_rig` |
| POS.06 | 초록 · KEY+BACK 18대 `Pan 180 / Tilt 128.7` | `degenerate_rig` |
| POS.02·03·04 | `unaimable`(접힌 사유) | `degenerate_rig` |

거절문은 **무엇이 없는지**를 말한다:

    좌표 86대를 읽었지만 수평 폭이 없다 (x span 0.000m · y span 0.000m <= 0.05m)
    — 목표점이 한 점으로 접혀 산출값이 무의미하다. 리그 좌표를 콘솔에 넣어야 풀린다

`degenerate_rig` 는 `no_coordinates` 를 삼키지 않는다 — 「아예 못 읽었다」와
「읽었는데 한 점에 접혀 있다」는 다른 상태이고, 검사가 그 구별을 고정한다.

## 4. 사유 가르기

t221 §7 의 부수 결함. 서로 다른 두 원인이 바이트 동일한 사유를 냈고, 그것이
「물리적 도달 불가인가」라는 오진을 만들어 레인 하나를 픽스처 기하 측정에 보냈다.

**원인은 예외 종류로 읽는다, 문면 매칭이 아니다.** `pointing.py` 에 `SpatialPointingError`
의 하위 둘을 세웠다 — `PointingTargetCoincidesError`(거리 0) ·
`PointingTiltLimitError`(상한 초과). 하위 클래스라 기존 `except SpatialPointingError`
는 전부 그대로 잡는다.

실측(`evidence/reason_split.txt`, 수평 폭이 실값인 합성 리그):

    POS.03 | unaimable
        대상 12대 전부 조준 상한 135° 를 넘는다. ⚠️ 이 상한은 실측이 아니라 다른
        리그 기종(Robe LEDBeam 350 / MMX)에서 온 모듈 상수다 — 이 쇼의 기종
        가동범위로 다시 재야 한다
    POS.04 | target_coincides
        대상 8대 전부 목표점이 장비 자신과 같은 자리다 (거리 0) — 빔 방향이
        정의되지 않는다. 조준 한계와는 무관하다

사유도 상세도 바이트 동일이 아니고, 검사가 둘 다 단언한다. 한 행 안에서 두 원인이
섞이면 `unaimable_mixed` 로 **양쪽을 다 말한다** — 접지 않는다.

135° 상한 자체는 이 카드 범위 밖(가정이고 별도 카드)이지만, **그 상한을 근거로 든
사유는 그것이 가정임을 같이 말한다.** 뮤턴트 M6 이 이 고지를 지킨다.

## 5. 뮤테이션 — 6/6 죽었다

`evidence/t222_mutants.py` -> `evidence/mutants.txt`. 하위 프로세스를
`PYTHONDONTWRITEBYTECODE=1` 로 돌리고, 회차마다 `assert mutated != original` 로
「적용 안 됨」 갈래를 기계화했다. `if False and …` 형태는 린트 축을 오염시키므로 쓰지 않았다.

    기준 (뮤턴트 없음): 0 32 passed
    M1 가드 자체를 없앤다              -> 죽었다 | 6 failed
    M2 임계를 정확히 0 으로            -> 죽었다 | 2 failed
    M3 z 축까지 요구한다               -> 죽었다 | 1 failed
    M4 두 원인을 다시 한 사유로 접는다  -> 죽었다 | 1 failed
    M5 원인 분류를 없앤다              -> 죽었다 | 3 failed
    M6 「상한은 가정」 고지를 뺀다       -> 죽었다 | 1 failed
    생존/미적용: 0 / 6

대조군 두 팔: 1) 새 검사가 잡는가 — M1 이 6건을 빨갛게 만든다. 2) 기존 상태에서는
못 잡는가 — `test_a_rig_with_real_spread_is_untouched_by_the_guard` 가 실값 리그에서
가드가 아무것도 안 잡는 것을 단언한다.

## 6. 회귀 회계

자체 venv(`uv sync --group dev`), 같은 트리, `-p no:randomly`.

| 상태 | 결과 |
|---|---|
| base(`origin/WT-pos-reach` 소스로 되돌림) | **10745 passed, 12 skipped** |
| 이 브랜치 | **10759 passed, 12 skipped** |

차이 **+14**, 추가한 검사 수 **14**(`TestDegenerateRig` 9 + `TestUnaimableReasonSplit` 5).
**기존 검사는 하나도 안 고쳤고 하나도 안 지웠다.** 리드가 준 10745 를 옮겨 쓰지 않고
이 트리에서 직접 재서 같은 값을 얻었다.

## 7. 실기 확인 (읽기 전용)

    .venv/bin/python server/tools/lxseq_pos_e2e.py … --action preview --limit 0

exit 0 · `coordinates_read {count: 86, reason: null}` · `derived []` ·
`bundles 0` · 6행 전부 `degenerate_rig` · `stopped preview`.
**콘솔 쓰기 0건** (`--approve` 없음, 번들 0). 전에는 같은 명령이 3행·3번들을 냈다.
`evidence/preview_after.json`.

하네스(`lxseq_pos_e2e.py`)는 **한 줄도 안 고쳤다** — 술어를 순수 함수 안에 두었으므로
거절이 `result.skipped` 를 타고 그대로 나온다.

## 8. 안 잰 것 (Gaps)

- **135° 상한이 이 쇼 기종(MegaPointe · Spiider · MAC Aura XB)에서 맞는지 안 쟀다.**
  범위 밖(별도 카드). 사유 문면이 이것을 가정으로 고지할 뿐이다. pan 은 여전히
  범위 검사가 **없다** — 그것도 안 건드렸다.
- **좌표가 채워진 뒤 여섯 행이 어떻게 나오는지 안 쟀다.** 잴 데이터가 없다.
  POS.02 의 「면이 아니라 선」(t221 §5) 은 여전히 미판정이다.
- **`degenerate_rig` 상태에서 큐 조인(`import_lxseq_cues`)이 어떻게 거절하는지
  안 쟀다.** 전에도 6행 중 3행이 보류라 배치가 거절됐고 지금은 6행이 보류다 —
  방향은 같지만 문면을 확인하지 않았다.
- **검사 RED 를 행위 수준으로 못 보였다.** base 소스에 새 검사 파일을 얹으면
  `ImportError` 로 수집 단계에서 끊긴다(새 심볼을 임포트하므로). 행위 수준 재현은
  검사가 아니라 `evidence/t222_before.py` 프로브가 나른다. 가드가 실제로 무엇을
  지키는지는 뮤턴트 M1(6 failed)이 답한다.
- **코퍼스 8종 중 7종이 합성이다.** 실제 리그는 live 하나뿐 — 다른 쇼파일의 실값
  좌표로는 못 쟀다(저장소에 없다).
- **큐는 0개 열렸다.** 의도된 것이다.

## 8.5 배차서 전제 하나를 반증한다 — CI 는 죽어 있지 않다

배차서: 「CI is dead repo-wide (billing): a ~3s job with `steps: 0` is that, not you.」
실측(2026-09-01, PR #271 head `230693f`):

    gh run watch 33472430407 --exit-status
      ✓ Python tests   ✓ UI tests   ✓ Complete job
    gh pr checks 271 -> test  pass  5m10s
    gh pr view 271 --json headRefOid -> 230693f (내 HEAD 와 동일)

`steps: 0` 도 3초도 아니었다 — **5분 10초를 돌고 실제 단계가 전부 초록**이다.
`mergeable MERGEABLE` · `mergeStateStatus CLEAN`.
결제가 언제 풀렸는지는 안 쟀다. 다만 「죽어 있다」를 전제로 CI 를 건너뛰는 배차는
지금 시점에 성립하지 않는다.

## 9. 컨텍스트

`.moai/state/context-usage.json` 이 **이 워크트리에 없다**(`cat` -> `No such file`).
그래서 `raw_pct` 축은 이 회차에서 못 쓴다 — 규약 §9 의 **대체 경로인 카드 수 축**으로
간다: **이 세션 1장째**(t222 단독). 다섯 장 임계에서 멀다.
