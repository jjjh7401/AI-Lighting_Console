# t501 M5b — 효과 기구 그룹 주소 영(0) 처리 (리드 결정 g) 구현 보고서

## 1. Claim (주장)

REQ-LDRENDER-007/008(M5, 카드 t501)을 리드 결정 (g)에 따라 구현했다 —
공유 `fids`에서 fid 를 빼는 대신(멤버십 판독 경로 부재, `M5.md` §블로커가
2차 반증한 사실), 비액센트 큐에서 effect 역할 그룹(BLIND/STROBE/HAZE)을
그룹 주소(`Group <n> ; Attribute 'Dimmer' At 0`)로 0 에 내리는
outcome-equivalent 구현이다. 액센트 큐에서는 그 액센트가 겨냥하는 그룹만
건너뛰어 `_accent_fixture_value_lines`가 상승 액센트 값을 낸다. t498
큐 11의 "100→80"(전체 디머 100 뒤에 액센트 80 이 덮어써 역방향 하강) 결함이
"0→80"(상승)으로 고쳐졌다.

## 2. Evidence (증거)

### 2.1 구현

`server/design/song_cue_render.py`:

- `_effect_group_numbers(layer_mapping)` — 역할 `"effect"`에 매칭되는 **모든**
  콘솔 그룹 번호를 정렬·중복 제거해 튜플로 모은다. `_role_group_numbers`의
  last-wins 단일값과 다른 축이다(BLIND 14/STROBE 15/HAZE 16 전부 서로 다른
  그룹이라 하나로 접으면 둘을 잃는다).
- `_effect_dimmer_zero_lines(cue, layer_mapping, previous_fixture=None)` —
  `cue.kind`가 `_ROLE_VALUE_LINE_KINDS`(`section`/`climax_return`)에 들고
  `key_pct > 0`일 때만, `_effect_group_numbers`가 모은 그룹마다
  `Group <n> ; Attribute 'Dimmer' At 0`을 낸다. 단, (a) 이 큐 자신의
  액센트가 겨냥하는 그룹(`cue.accent_fixture.group_no`), (b) 이 큐가
  복귀 큐이고(`cue.accent_fixture is None`) 앞 큐가 블라인더를 켜 둔
  그룹(`previous_fixture.group_no`)은 건너뛴다 — 각각 `_accent_fixture_value_lines`
  가 그 그룹에 독립적으로 상승/복귀 값을 내므로, 또 내면 문자열이
  중복된다(배차서 요구사항 1 "unique strings" 를 복귀 큐까지 일관 적용한
  추가 가드).
- `reviewed_song_commands`의 `extra_value_lines` 튜플에
  `*_role_dimmer_value_lines(...)` 직후 `*effect_zero_lines`를 삽입했다
  (배차서 요구사항 1 줄 순서: 전체 디머 → 역할 디머(effect=0 포함) →
  효과 recall → 액센트). `previous_fixture` 재할당(`previous_fixture =
  cue.accent_fixture`) **전**에 `effect_zero_lines`를 계산해, 복귀-그룹
  가드가 `accent_lines`와 같은 "이전 큐의 액센트"를 읽도록 맞췄다.

`_role_dimmer_value_lines`(M3, role_pct 경로) 자체는 손대지 않았다 — 기존
`test_effect_role_is_never_emitted_even_if_role_pct_has_a_value`가 바이트
동일 통과한다(§2.3).

### 2.2 줄 순서 + REQ-008 실측(Rain, 실기용 DSP 분석을 쓴 완전한 리허설)

`.moai/reports/t501/m5_rain_cue10_11_115_extract.txt`(verbatim 발췌,
실제 `reviewed_song_commands` 산출):

```
--- Cue 10 (Verse 4, 비액센트) ---
...
Group 14 ; Attribute 'Dimmer' At 0
Group 15 ; Attribute 'Dimmer' At 0
Group 16 ; Attribute 'Dimmer' At 0
Store Sequence 211 Cue 10 'Verse 4' CueFade 1.184
--- Cue 11 (Chorus 6, 액센트=BLIND/그룹14) ---
Fixture 20 + 26 ; Attribute 'Dimmer' At 100   <- 전체 디머(경쟁 값 100)
...
Group 4 ; Attribute 'Dimmer' At 80
Group 7 ; Attribute 'Dimmer' At 80
Group 10 ; Attribute 'Dimmer' At 80
Group 13 ; Attribute 'Dimmer' At 80
Group 15 ; Attribute 'Dimmer' At 0            <- STROBE 는 여전히 0
Group 16 ; Attribute 'Dimmer' At 0            <- HAZE 는 여전히 0
Group 14 ; Attribute 'Dimmer' At 80           <- 액센트(그룹 14 명시 줄은 이 하나뿐)
Store Sequence 211 Cue 11 'Chorus 6' CueFade 0.394667
--- Cue 11.5 (Chorus 6 Return, 복귀) ---
...
Group 15 ; Attribute 'Dimmer' At 0
Group 16 ; Attribute 'Dimmer' At 0
Group 14 ; Attribute 'Dimmer' At 0            <- 복귀(명시 줄 하나, 중복 없음)
Store Sequence 211 Cue 11.5 'Chorus 6 Return' CueFade 0
```

이전(t498 §0 큐 11, verdict.md): "Group 4 80 · Group 14(BLIND) 80" —
전체 디머 100 뒤에 액센트 80 이 와서 **100→80 하강**이었다. 고친 뒤:
직전 큐(10)에서 그룹 14 가 0 으로 내려가 있고, 이 큐(11)에서 그룹 14 를
명시적으로 겨냥하는 줄은 액센트 80 **하나뿐**(effect=0 줄은 액센트 자신의
그룹이라 건너뜀) — **0→80 상승**이다. STROBE(15)/HAZE(16)는 액센트 대상이
아니라서 이 큐에서도 0 을 유지한다.

**잔여 — 전체 디머(Fixture ... At 100) 자체는 여전히 그룹 14 소속 fid 에도
닿는다.** 그룹-주소 override(last-wins)가 최종 물리 상태를 80 으로
덮어쓰지만, 그 전체-디머 줄 자체는 사라지지 않는다 — REQ-007 fid 뺄셈이었다면
애초에 이 줄 자체가 그룹 14 fid 를 겨냥하지 않았을 것이다. 이것이
outcome-equivalent 해석의 구체적 비용이다(§4 Gaps 참조).

### 2.3 테스트 + 뮤테이션 + 전체 스위트

```
$ PYTHONDONTWRITEBYTECODE=1 uv run pytest server/tests/test_song_cue_effect_zero_t501_m5.py -q
....................
20 passed in 0.16s

$ PYTHONDONTWRITEBYTECODE=1 uv run pytest server/tests -q -p no:cacheprovider
14476 passed, 35 skipped, 1 warning in 215.34s
```

뮤테이션 6건(각 1축, diff 로 적용 확인 후 복원) 전부 대상 테스트만 죽임
(progress.md §M5 완료 표 참조) — 생존 뮤턴트 0건.

### 2.4 8곡 측정(a~c)

```
Club Diver: 비액센트 큐 13개 중 effect>0 위반 {'BLIND': 0, 'STROBE': 0, 'HAZE': 0} (합 0) · 액센트 큐 1개 중 상승 1/1 · LIT>=3 14/14 · 색 4종
Cut and Run: 비액센트 큐 17개 중 effect>0 위반 {'BLIND': 0, 'STROBE': 0, 'HAZE': 0} (합 0) · 액센트 큐 1개 중 상승 1/1 · LIT>=3 18/18 · 색 3종
Ice cream: 비액센트 큐 7개 중 effect>0 위반 {'BLIND': 0, 'STROBE': 0, 'HAZE': 0} (합 0) · 액센트 큐 1개 중 상승 1/1 · LIT>=3 8/8 · 색 4종
Morning: 비액센트 큐 13개 중 effect>0 위반 {'BLIND': 0, 'STROBE': 0, 'HAZE': 0} (합 0) · 액센트 큐 1개 중 상승 1/1 · LIT>=3 14/14 · 색 3종
Rain: 비액센트 큐 12개 중 effect>0 위반 {'BLIND': 0, 'STROBE': 0, 'HAZE': 0} (합 0) · 액센트 큐 1개 중 상승 1/1 · LIT>=3 13/13 · 색 3종
Too Cool: 비액센트 큐 23개 중 effect>0 위반 {'BLIND': 0, 'STROBE': 0, 'HAZE': 0} (합 0) · 액센트 큐 1개 중 상승 1/1 · LIT>=3 24/24 · 색 4종
scott-buckley-neon: 비액센트 큐 17개 중 effect>0 위반 {'BLIND': 0, 'STROBE': 0, 'HAZE': 0} (합 0) · 액센트 큐 1개 중 상승 1/1 · LIT>=3 18/18 · 색 4종
걸그룹DinoDino_C_max최고품질: 비액센트 큐 10개 중 effect>0 위반 {'BLIND': 0, 'STROBE': 0, 'HAZE': 0} (합 0) · 액센트 큐 1개 중 상승 1/1 · LIT>=3 11/11 · 색 4종

합계: 비액센트 큐 effect>0 위반 0건(목표 0) · 액센트 상승 8/8 · AC-001 LIT>=3 120/120
```

AC-001 LIT>=3 120/120 은 M3 후속(climax_return, M4 §AC-001 재측정)과
바이트 동일 — M5 는 공유 `fids`를 바꾸지 않았으므로(그룹-주소 override
축만 추가) 디머/색 LIT 집계 자체는 구조적으로 불변, 예측대로 확인됐다.
`.moai/reports/t501/measure_m5_8songs.py`(신설, `measure_ac001_8songs.rehearse`
재사용) + 3개 JSON 산출물(`measure_m5_{a,b,c}_*.json`).

### 2.5 AC-LDRENDER-015(t498 오프라인 스위트) — d. 재실행 결과

실제 Rain 오디오(`src/sample music/Rain.mp3`, 주 체크아웃, 읽기 전용)로
`rehearse_rain.py`를 이 트리(M5 적용 후)에서 2회 실행:

```
$ uv run python .moai/reports/t498/judge_a1_a5.py run1_m5 run2_m5
A1 run1_m5: bpm=76.01351351351367 source=measured sections=12 selected=12
A1 run2_m5: bpm=76.01351351351367 source=measured sections=12 selected=12
A2 gates=13 passed=13 not_passed=[]  (x3)
A3 console_commands_approved.txt: run1==run2 bytes True (224 lines)
A3 console_commands_sent.txt: run1==run2 bytes True (224 lines)
A4 approved=224 sent=224 diff=0
A5 sent-not-approved=0 []
   approved-not-sent=0 []
order equal: True
```

`$ uv run python .moai/reports/t498/judge_a7.py run1_m5/console_commands_approved.txt
  run8_cue_props.txt run7_after_write.txt`(**t498 M5 이전 실기 캡처**, 읽기
전용 대조 — 새 콘솔 접촉 0):

```
A7 match 13 / 13 (console cues read: 13)
```

PASS: A1(분석 재현)·A2(게이트 13/13)·A3(결정성)·A4(승인=송신)·A5(승인 밖
명령 0)·A7(되읽기, M5 이전 실기 큐 이름/트리거 시각과 13/13 일치 — M3/M4/M5
누구도 큐 식별/타이밍을 바꾸지 않았음을 실기 데이터로 확인).

**classify_diff(참고용, AC-015 필수 항목 아님)** —
`.moai/reports/t498/classify_diff.py`를 M5 트리의 신선한 리허설과
**t498 M5 이전** 실기 전부-거절 목록(`run3_rain_real_denyall`)에 돌리면:

```
lines rehearsal=224 real=119
after fixture-set normalisation: only_rehearsal=117 only_real=12
...
real-only lines: W-channel=12 other=0
VERDICT all diff lines explained by fixture-set + W-channel: False
```

`only_rehearsal=117`은 전부 설명 가능: 116줄이 Group 3/4/7/10/13/14/15/16
패턴(M3 역할 디머·M4 역할 색·M5 effect=0, `grep -c "^  UNEXPLAINED
rehearsal-only: Group "` → 116)이고, 나머지 1줄은 가짜 콘솔 좌표 대역
(fid 20/26) 색 줄 — 이 측정 하네스 자체가 쓰는 2기구 대역(`_Spatial`
클래스)의 이미 문서화된 인공물이지 M5 결함이 아니다. `only_real=12`는
전부 기존 W 채널 축(t430, M5 이전부터 있던 것). **VERDICT False 는 M5
결함이 아니라, 이 비교의 기준선(real 목록)이 M3/M4 보다도 더 이전(M5 이전
뿐 아니라 M3/M4 이전)의 캡처이기 때문** — classify_diff 는 원래 t498
자신의 단일 목적(W 채널 축 분류) 도구이고, AC-015 의 "A1~A7·C 항목" 목록에
들지 않는다. 참고용으로 `.moai/reports/t501/m5_classify_diff.txt`에
전문을 보존한다.

**C1~C3(기존 쇼 보존·백업·번호 충돌)** — 이번 카드는 가짜 콘솔만 썼다
(콘솔 쓰기 0건, 배차서 제약). 직접 측정하지 않았다 — §4 Gaps 참조(간접
근거만 있음).

## 3. Baseline-attribution (baseline 귀속)

- **커밋**: `git fetch origin WT-ldrender-run && git merge --ff-only
  origin/WT-ldrender-run` 직후 `git rev-parse --short HEAD` → `edb19c44`
  (배차서가 지정한 canonical HEAD, M3 후속 climax_return 완료 커밋 이후
  리드 블로커 보고서 커밋). 이 보고서의 모든 측정은 이 HEAD 위에서
  M5 구현(`server/design/song_cue_render.py` 수정)을 적용한 **이** 워크트리
  에서 직접 실행한 결과다.
- **전체 스위트 before/after**: before(M5 코드 변경 0, M5.md §2.5)
  `14456 passed, 35 skipped` — 이번 카드가 이 워크트리에서 직접 관측.
  after(M5 구현 적용) `14476 passed, 35 skipped` — 이번 카드가 이 워크트리
  에서 직접 실행해 관측한 verbatim 출력. 차이 +20/0/0 은 신설 테스트
  수(20)와 바이트 단위로 일치.
- **8곡 측정**: `.moai/reports/t501/measure_m5_8songs.py`를 이 워크트리에서
  직접 실행해 관측 — `measure_ac001_8songs.py`(M3/M4 가 이미 검증한 재현
  인프라, DSP 재실행 없이 t499 `analysis.json` 재사용)를 import 해
  재사용했다. `t499/runs/*/analysis.json` 8개는 t499 가 커밋한 실측값
  (DSP 재실행 아님, 재사용).
- **AC-015 오프라인 스위트**: `rehearse_rain.py`를 이 워크트리에서 실제
  오디오(`/Users/studiox/Documents/Claude/Code/AI-Lighting_Console/src/sample
  music/Rain.mp3`, 주 체크아웃 경로, 읽기 전용)로 2회 직접 실행해 관측.
  `judge_a7.py`/`classify_diff.py`의 **대조 대상**(run8_cue_props.txt·
  run7_after_write.txt·run3_rain_real_denyall/approval_request_1.txt)은
  이 카드가 만든 것이 아니라 t498 이 2026-09-28 당시 실기에서 캡처해
  커밋해 둔 기존 파일을 그대로 읽기만 했다(새 콘솔 접촉 0, 배차서 제약
  준수).

## 4. Gaps (미검증)

- **fid-수준 뺄셈(REQ-007 문면 직역)** — 구현하지 않았다(멤버십 판독 경로
  부재, M5.md §블로커가 2차 확정). AC-LDRENDER-006 은 디머 축만 effect
  기구를 제외하고, 색·포지션·페이저 축(공유 `fids`가 겨냥)은 여전히
  effect 기구를 포함한다 — **AC-006 을 PASS 로 보고하지 않는다.**
  디머 축만 떼어 보면 효과는 어둡지만(outcome 동치), AC-006 본문의
  "4종 값 줄 전부" 조건은 문자 그대로는 FAIL 이다.
- **C1(기존 쇼 보존)·C2(백업)·C3(번호 충돌)** — 이번 카드가 콘솔에 실제로
  쓰지 않아(가짜 콘솔만, "no console contact" 배차서 제약) 직접 측정하지
  않았다. 코드 판독(M3/M4/M5 가 전부 `extra_value_lines`에만 기여하고
  `Store Sequence`/프리셋 번호 발급 경로는 무변경)은 간접 근거일 뿐
  실기 확인이 아니다.
- **AC-LDRENDER-016(실기 감독 판정)** — 사람 판정, 이 카드 범위 밖.
- **옵션 (a)/(c)의 실측 재시도** — 결정 (g)가 둘 다 우회했으므로 더 이상
  필요하지 않다(이번 카드도 "no console contact").
- **전체 디머 줄이 여전히 effect fid 를 겨냥하는지의 실기 확인** — 코드
  판독(§2.2 "잔여")으로는 확인했으나, 실제 grandMA3 에서 Fixture-레벨
  줄과 Group-레벨 줄의 last-wins 순서가 **문서 그대로**인지는 이번 카드가
  실기로 재확인하지 않았다(M3/M4 가 이미 같은 가정을 쓰고 있었고, 이
  카드는 그 가정 위에 M5 를 쌓았을 뿐 새로 검증하지 않았다).

## 5. Residual-risk (잔여 위험)

- last-wins 는 실기 미확인 — 최종 실기 판정에서 확인(M3·M4·M5 공통 가정).
- **옵션 (a)(이름 접두 기반 fid 뺄셈)로 추후 전환할 경우**: 효과 기구
  이름이 "BLIND"/"STROBE"/"HAZE"(또는 RG5-1 접두 토큰 규약)로 시작하지
  않는 리그에서는 그룹-주소 override 가 여전히 동작한다(이름에 의존하지
  않으므로) — 이 점에서 (g)는 (a)보다 리그 일반화에 더 안전하다. 다만
  색·포지션·페이저 축은 계속 공유 `fids`를 거치므로, 그 세 축의 완전한
  제외가 필요해지면 결국 fid 뺄셈(옵션 a/b)으로 전환해야 한다.
- **전체 디머 줄이 여전히 effect fid 를 겨냥**하는 한, 콘솔이 `Fixture`
  레벨과 `Group` 레벨 선택을 **다른 우선순위**로 처리하는 예외적 설정
  (프로그래머 레이어링이 단순 last-wins가 아닌 경우)이 있다면 이 구현의
  가정이 깨질 수 있다 — M3/M4 가 이미 같은 가정에 기대어 있으므로 이것은
  M5 고유의 새 위험이 아니라 기존 위험의 연장이다.
- **HAZE 의 "무해한 명령" 결론**은 t241/verdict.md 실측(채널 표)에 근거하나,
  그 실측 자체가 "Dimmer ✗"를 **채널 모드 판독**(Mode 0 2ch)으로 확인한
  것이지, 콘솔이 존재하지 않는 애트리뷰트에 대한 `Attribute 'Dimmer' At 0`
  명령을 받았을 때 **에러 없이** 무시하는지까지 실기로 확인한 것은 아니다
  (오늘의 전체 디머 줄이 이미 같은 패턴으로 HAZE 에 가닿아 왔다는 선례가
  이 위험을 낮추지만, 완전한 배제는 아니다).

last-wins 는 실기 미확인 — 최종 실기 판정에서 확인(M3·M4·M5 공통 가정).
