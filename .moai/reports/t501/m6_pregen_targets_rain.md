# t501 M6 — 5절 정지점: Rain 사전 생성 대상 목록 (WITHOUT SENDING)

🔴 **콘솔 쓰기 0건.** 이 문서는 `server/design/phaser_pregen.py` 순수 함수를
저장된 읽기 전용 풀 스냅샷에 돌려 "지금 보내면 나갈 명령"만 산출한다
(`.moai/reports/t501/m6_pregen_stop_point.py`). 실제 전송 전 **새 읽기 전용
재조회가 반드시 필요하다** — 아래 점유 목록은 스냅샷 시점의 것이고, 그
이후 다른 저장/삭제가 있었을 수 있다.

## 입력 — Rain 이 요청하는 5개 카탈로그 라벨

좌: 코디네이터 매핑 표(`_phaser_label_for_cue`, section 이름 매칭) · 우: 그
라벨이 대응하는 Rain 구간 역할(절정/후렴/벌스/브리지/피날레 다섯 역할
전부가 Rain 구조에 있다, `.moai/reports/t499/verdict.md` 8곡 구조표).

| 라벨 | Rain 구간 역할 | 저장 풀(카탈로그 고정) |
|---|---|---|
| Drop Slam | 절정/클라이맥스/피크 | All 1(21번) |
| Wave CM | 후렴 | Color(4번) |
| Breathe Warm | 벌스 | Color(4번) |
| Breathe Cool | 브리지/간주 | Color(4번) |
| Finale Slam | 피날레/아웃트로/엔딩 | Color(4번)* |

\* `_PHASER_LABEL_POOL_NAME` 재확인: `Finale Slam` 은 `COMBO_PHASER_SEQUENCE`
소속이라 실제로는 **All 1**(21번)이다 — 위 표의 "Color(4번)" 표기 오기를
여기서 바로잡는다. 아래 §결과 표가 정본(올바른 풀 번호로 산출됨).

## 공석(vacancy) 판정에 쓴 증거

| 풀 | 번호 | 점유 슬롯(캡처 당시) | 증거 파일 | 캡처 시점 |
|---|---|---|---|---|
| Color | 4 | 1,2,3,4,5,6,7,8,32 | `.moai/reports/t469/run3_phaser_pools.txt` | t469(이 SPEC 이전 카드) — `state` 조회, `truncated: false`, 완전 판독 |
| All 1 | 21 | 1,2,3,4,5,6 | `.moai/reports/t469/run3_phaser_pools.txt` | 〃 |

**이 스냅샷을 고른 이유**: 이 워크트리에 있는 t498 의 풀 판독
(`run0c_meta_pool2page.txt`)은 Position 풀(2번)만 담고 있어 Color/All 1
점유를 모른다 — t469 의 저장된 읽기가 Color·All 1 둘 다 완전 판독으로
커버하는 유일한 기존 레코드라 이것을 썼다. **이 스냅샷은 t501 M6 작업
시점(2026-10-01)보다 앞선 캡처**이므로 지금 이 순간의 점유를 보장하지
않는다 — 전송 전 재조회 필수(아래 §잔여 위험).

## 결과 — 번호·이름 전부 + 판정

| 라벨 | 풀.슬롯(제안) | 판정 | 사유(판정이 REFUSED 일 때) |
|---|---|---|---|
| Drop Slam | All 1(21).7 | **REFUSED** — 생성 자체가 안 됨 | `value_line_collision` — 두 스텝 모두 `Attribute 'ColorRGB_R' At 100` 을 내어 FXLIB `_guard_collision` 이 거부(Red→Red, 디머만 변함) |
| Wave CM | Color(4).9 | **WOULD_SEND** | — |
| Breathe Warm | Color(4).9 | **REFUSED** | `value_line_collision` — `Attribute 'ColorRGB_R' At 100` 중복(웜화이트·앰버 둘 다 R=100) |
| Breathe Cool | Color(4).9 | **REFUSED** | `value_line_collision` — `Attribute 'ColorRGB_B' At 100` 중복(쿨화이트·블루 둘 다 B=100) |
| Finale Slam | All 1(21).7 | **REFUSED** | `value_line_collision` — `Attribute 'ColorRGB_R' At 100` 중복(웜화이트·레드 둘 다 R=100) |

**측정됨(날조 아님) — 5개 중 1개만 이 경로로 생성 가능하다.** `server/tests/
test_phaser_pregen.py::TestPregenerateBundle` 가 이 결과를 독립적으로
재확인한다(`test_wave_cm_is_the_one_needed_label_that_builds_cleanly` +
`test_the_other_four_needed_labels_collide_and_are_refused_not_guessed`).
이것은 "같은 의도, 다른 문면" 수준의 스타일 차이가 아니라 — FXLIB 의
`_guard_collision`(REQ-FXLIB-011 (a))이 실제로 번들 조립을 **거부**하는
빌드 실패다(`server/design/phaser_pregen.py` 모듈 독스트링 [ASSUMPTION ->
측정 확정] 참조). 거부는 FXLIB 기존 사유 코드(`value_line_collision`) 그대로
전파되며, 이 모듈이나 그 호출부(`server/web/session.py
_pregenerate_missing_phasers`)가 색 값을 바꿔 충돌을 피하려 하지 않는다
(새 RGB 발명 금지, §D 제약).

## 보낼 명령 전문 (Wave CM 만 — 나머지 넷은 REFUSED라 명령 자체가 없음)

전문은 `.moai/reports/t501/m6_pregen_commands_rain.txt` 에 저장했다(REFUSED
4건의 정확한 사유 문구도 그 파일에 주석으로 함께 있다). 요약:

```
# Wave CM -> Preset 4.9
ChangeDestination Root
ClearAll
Group 1
Attribute 'ColorRGB_R' At 0
Attribute 'ColorRGB_G' At 90
Attribute 'ColorRGB_B' At 100
Step 2
Attribute 'ColorRGB_R' At 100
Attribute 'ColorRGB_G' At 0
Attribute 'ColorRGB_B' At 70
Step 1 At Accel -100
Step 1 At Decel -100
Step 2 At Accel -100
Step 2 At Decel -100
Attribute 'ColorRGB_R' At Phase 0
Attribute 'ColorRGB_G' At Phase 120
Attribute 'ColorRGB_B' At Phase 240
Attribute 'ColorRGB_R' At Speed 30 ; Attribute 'ColorRGB_G' At Speed 30 ; Attribute 'ColorRGB_B' At Speed 30
Store Preset 4.9 'Wave CM' /Universal
Label Preset 4.9 'Wave CM'
ClearAll
```

`Group 1`(=All, `server/orchestrator/tools.py:2037` `LXSEQ_PRESET_APPLY_GROUP_NO`
과 같은 전제)은 저작 시점 스크래치 선택일 뿐이다 — `Store Preset ...
/Universal` 로 저장되므로 recall 대상 기구를 제한하지 않는다.

## 잔여 위험 — 전송 전 재확인 필요 (명시)

- **풀 점유 스냅샷이 낡았다.** t469 캡처 이후 Color(4)/All 1(21) 풀에
  다른 저장·삭제가 있었을 수 있다 — 전송 직전 `select_preset_number` 의
  재조회(§D "콘솔 풀 재조회로 프리셋 번호 충돌을 사전 검출" 요구) 없이
  이 문서의 슬롯 번호(4.9, 21.7)를 그대로 쓰면 안 된다.
- **phase/curve 문법 괴리(Wave CM 에도 적용됨).** `build_fx_preset_bundle`
  이 쓰는 FXLIB 표준 문법(`Step <k> At Accel <v>`, 속성별 Phase 체이스)은
  `server/web/session.py` 손수 작성 경로(채널 하나에만 Phase/Accel/Decel)와
  다르다 — "같은 스텝 값·같은 색·같은 속도"를 재현하되 정확한 명령 문면은
  다르다. Wave CM 자체는 FXLIB 쪽에서 빌드는 되지만, **그 문법으로도 같은
  시각 효과가 나는지는 이 저장소가 실기로 측정한 바가 없다**(server/fx/
  library/color.yaml 의 chase-* 항목들이 이 경로를 쓰지만, "Wave CM"
  이라는 이름의 **카탈로그** 효과와 동일하다는 교차 확인은 없음).
- **4개 라벨은 이 경로로 영구히 생성 불가능하다(처방 미정).** 카탈로그
  색을 바꾸거나(§D 가 금지하는 새 RGB 발명과 충돌 — 리드 결정 필요),
  FXLIB 쪽에 "레이어 전체를 한 줄로 묶는" 새 빌더를 추가하거나(이 SPEC
  범위 밖), 또는 손수 작성 경로(`_combo_phaser_form_commands` 등)를 이
  송신 흐름에 직접 연결하는 제3의 길 — 셋 다 이 카드가 결정하지 않는다.
- **R7 게이트(fx.permitted) 와는 독립된 축.** 이 문서의 5개 라벨은 전부
  "제안됐다"고 가정한 것이지, 실제 Rain 송신이 그 순간 `cue.fx.permitted`
  를 비우지 않았는지는 별도로 확인해야 한다(REQ-010, M6 본편 참조) — 예산이
  0이면 Wave CM 조차 pregen 시도가 아예 발동하지 않는다.
