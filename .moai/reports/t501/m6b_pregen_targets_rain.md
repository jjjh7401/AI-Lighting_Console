# t501 M6b — 5절 정지점 재생성: Rain 사전 생성 대상 목록 (WITHOUT SENDING)

🔴 **콘솔 쓰기 0건.** 이 문서는 `.moai/reports/t501/m6b_pregen_stop_point.py`
(`m6_pregen_stop_point.py`와 같은 기계, 풀 점유 증거만 갱신)를 저장된 읽기
전용 풀 스냅샷에 돌려 "지금 보내면 나갈 명령"만 산출한다. 실제 전송 전
**새 읽기 전용 재조회가 반드시 필요하다** — 아래 점유 목록은 스냅샷
시점의 것이고, 그 이후 다른 저장·삭제가 있었을 수 있다.

## 배경 — 무엇이 바뀌었나 (M6 -> M6b)

M6 당시(§참고: `m6_pregen_targets_rain.md`, 본 보고서 바로 이전 판)
Rain 이 요청하는 5개 카탈로그 라벨 중 **Wave CM 하나만** FXLIB
`build_fx_preset_bundle`의 `_guard_collision`을 통과했다. 나머지 4개
(Drop Slam/Breathe Warm/Breathe Cool/Finale Slam)는 두 스텝 모두 같은
채널 값을 내어(예: Drop Slam 의 두 스텝 모두
`Attribute 'ColorRGB_R' At 100`) `value_line_collision`으로 거부됐다.

리드 결정(카드 t501 M6b, 2026-10-02 director decision ②)이 그 거부의
범위를 좁혔다: `run_commands`의 중복 제거가 `Step <n>` 경계에서 스코프를
리셋하도록 바꾸고(`server/orchestrator/tools.py` `_is_step_boundary`),
FXLIB `_guard_collision`을 그에 맞춰 완화했다(`server/fx/instantiate.py`).
**같은 값이 같은 스텝 안에서 두 번이면 여전히 거부되지만, 다른 스텝에서
반복되면 더 이상 충돌이 아니다** — 콘솔 스텝 칼럼이 두 순간을 가르기
때문이다. 이 변경으로 5개 필요 라벨 전부가 이 경로로 빌드된다.

## 입력 — Rain 이 요청하는 5개 카탈로그 라벨 (M6 과 동일)

| 라벨 | Rain 구간 역할 | 저장 풀(카탈로그 고정) |
|---|---|---|
| Drop Slam | 절정/클라이맥스/피크 | All 1(21번) |
| Wave CM | 후렴 | Color(4번) |
| Breathe Warm | 벌스 | Color(4번) |
| Breathe Cool | 브리지/간주 | Color(4번) |
| Finale Slam | 피날레/아웃트로/엔딩 | Color(4번)* -> 정본: All 1(21번, `_PHASER_LABEL_POOL_NAME` 재확인, M6 각주 그대로) |

## 공석(vacancy) 판정에 쓴 증거 — 갱신됨 (M6b)

| 풀 | 번호 | 점유 슬롯(캡처 당시) | 증거 파일 | 캡처 시점 |
|---|---|---|---|---|
| Color | 4 | 1,2,3,4,5,6,7,8,**9**,32 | `.moai/reports/t501/m6_postsend_reread_20261002.txt` | 2026-10-02 — **Wave CM 이 이미 실기 Preset 4.9 로 전송된 뒤**의 `state` 재조회(`truncated: false`, 완전 판독) |
| All 1 | 21 | 1,2,3,4,5,6 | `.moai/reports/t501/m6_pool_reread_readonly.txt` | 2026-10-02 — 읽기 전용 재조회(`truncated: false`, 완전 판독) |

**이 스냅샷으로 갈아탄 이유**: M6 의 원래 `m6_pregen_targets_rain.md`는
t469(이 SPEC 이전 카드)의 낡은 스냅샷을 썼다. M6 본편 작업 중 Wave CM 이
실제로 감독 승인을 받아 Preset 4.9 로 전송됐으므로(`.moai/reports/t501/
m6_send_wave_cm.py` 실행, 감독 승인 21줄), Color 풀의 점유 상태가
**실제로 바뀌었다** — 이 보고서는 그 변화를 반영한 **최신** 재조회
두 건(전송 직후 Color, 읽기 전용 All 1)을 쓴다.

## 결과 — 번호·이름 전부 + 판정 (M6b: 5개 전부 WOULD_SEND)

| 라벨 | 풀.슬롯(제안) | 판정 | 줄 수 | 스텝 완전성 |
|---|---|---|---|---|
| Drop Slam | All 1(21).7 | **WOULD_SEND** | 24 | Step 1·Step 2 모두 4개 채널(R/G/B/Dimmer) 값 전건 생존 |
| Wave CM | Color(4).10 | **WOULD_SEND** | 21 | Step 1·Step 2 모두 3개 채널(R/G/B) 값 전건 생존 |
| Breathe Warm | Color(4).10 | **WOULD_SEND** | 21 | Step 1·Step 2 모두 3개 채널(R/G/B) 값 전건 생존 |
| Breathe Cool | Color(4).10 | **WOULD_SEND** | 21 | Step 1·Step 2 모두 3개 채널(R/G/B) 값 전건 생존 |
| Finale Slam | All 1(21).7 | **WOULD_SEND** | 24 | Step 1·Step 2 모두 4개 채널(R/G/B/Dimmer) 값 전건 생존 |

**측정됨(날조 아님, `.moai/reports/t501/m6b_pregen_stop_point.py` 실행
결과 verbatim, `.moai/reports/t501/m6b_pregen_stop_point_output.json`
참조) — 5개 전부 이 경로로 생성 가능하다.** `server/tests/
test_phaser_pregen.py::TestPregenerateBundle::
test_the_other_four_needed_labels_now_build_cleanly_too`가 이 4개를
개별로 재확인하고, `test_wave_cm_is_the_one_needed_label_that_builds_cleanly`가
Wave CM 을 재확인한다. "스텝 완전성" 열은 각 라벨의 Step 1/Step 2 가 모두
자기 채널 값을 **전건** 담고 있는지(드롭되지 않았는지) 명령 리스트를
직접 센 결과다 — 예: Drop Slam 은 Step 1 에 R/G/B/Dimmer 4줄, Step 2 에도
R/G/B/Dimmer 4줄(총 8줄), 둘 다 생존한다.

**Color 풀 주의(.10 중복 제안)**: Wave CM/Breathe Warm/Breathe Cool 셋
다 같은 다음 빈 번호(.10)를 제안한다 — 이 스크립트가 5개 라벨을 **서로
독립**으로 같은 스냅샷에 대해 시뮬레이션하기 때문이다(M6 의 원본
스크립트와 동일한 계산 모델). 실제로 셋을 순서대로 보내면 먼저 성공한
라벨이 .10 을 차지하고, 다음 라벨은 그다음 빈 번호(.11)로 밀린다 — 그래서
아래 §잔여 위험의 "전송 전 재조회"가 이 세 라벨에는 특히 더 중요하다.

## 보낼 명령 전문 (5개 전부)

전문은 `.moai/reports/t501/m6b_pregen_commands_rain.txt` 에 저장했다. 예시
(Drop Slam — M6 당시 거부됐던 바로 그 라벨, 이제 두 스텝 모두 생존):

```
# Drop Slam -> Preset 21.7
ChangeDestination Root
ClearAll
Group 1
Attribute 'ColorRGB_R' At 100
Attribute 'ColorRGB_G' At 0
Attribute 'ColorRGB_B' At 0
Attribute 'Dimmer' At 100
Step 2
Attribute 'ColorRGB_R' At 100
Attribute 'ColorRGB_G' At 0
Attribute 'ColorRGB_B' At 0
Attribute 'Dimmer' At 0
Step 1 At Accel 0
Step 1 At Decel 0
Step 2 At Accel 0
Step 2 At Decel 0
Attribute 'ColorRGB_R' At Phase 0
Attribute 'ColorRGB_G' At Phase 0
Attribute 'ColorRGB_B' At Phase 0
Attribute 'Dimmer' At Phase 0
Attribute 'ColorRGB_R' At Speed 30 ; Attribute 'ColorRGB_G' At Speed 30 ; Attribute 'ColorRGB_B' At Speed 30 ; Attribute 'Dimmer' At Speed 30
Store Preset 21.7 'Drop Slam' /Universal
Label Preset 21.7 'Drop Slam'
ClearAll
```

주목: Step 1 과 Step 2 모두 `Attribute 'ColorRGB_R' At 100` 을 낸다
(M6 에서 `value_line_collision`으로 거부됐던 바로 그 반복) — 이제
`run_commands` 가 `Step 2` 경계에서 중복 제거 스코프를 리셋하므로 둘 다
실제로 실행된다(`skipped_already_executed` 로 떨어지지 않는다).

`Group 1`(=All, `server/orchestrator/tools.py:2037`
`LXSEQ_PRESET_APPLY_GROUP_NO`와 같은 전제)은 저작 시점 스크래치 선택일
뿐이다 — `Store Preset ... /Universal` 로 저장되므로 recall 대상 기구를
제한하지 않는다.

## 잔여 위험 — 전송 전 재확인 필요 (명시)

- **풀 점유 스냅샷이 이 보고서 작성 시점의 것이다.** 이 문서의 두 재조회
  (Color 2026-10-02 전송 직후, All 1 2026-10-02 읽기 전용)는 M6 의 t469
  스냅샷보다는 훨씬 최신이지만, 여전히 **스냅샷**이다 — 전송 직전
  `select_preset_number` 의 재조회(§D "콘솔 풀 재조회로 프리셋 번호
  충돌을 사전 검출" 요구) 없이 이 문서의 슬롯 번호(21.7, 4.10)를 그대로
  쓰면 안 된다.
- **Color 풀의 .10 삼중 제안.** 위 §결과 표에 적은 대로, Wave CM(이미
  전송됨, 재전송 의미 없음)을 빼면 Breathe Warm/Breathe Cool 둘이 같은
  .10 을 다툰다 — 순서대로 보낼 경우 두 번째 라벨은 재조회 후 .11 로
  다시 계산해야 한다.
- **phase/curve 문법 괴리(M6 잔여 위험 그대로 승계).** `build_fx_preset_
  bundle`이 쓰는 FXLIB 표준 문법은 `server/web/session.py` 손수 작성
  경로와 다르다 — Wave CM 자체는 이미 실기로 전송됐고(Preset 4.9, 감독
  승인), **그 문법으로 같은 시각 효과가 나는지는 이 저장소가 실기로
  측정한 바가 없다**(이 레포 범위 — 육안 확인은 운용 쪽 몫).
- **R7 게이트(fx.permitted)와는 독립된 축.** 이 문서의 5개 라벨은 전부
  "제안됐다"고 가정한 것이지, 실제 Rain 송신이 그 순간 `cue.fx.permitted`
  를 비우지 않았는지는 별도로 확인해야 한다(REQ-010, M6 본편 참조).
- **번호 할당(`select_preset_number`)의 경쟁 조건은 FXLIB 기존 경계
  그대로(새로 막지 않음)** — M6 잔여 위험과 동일.
