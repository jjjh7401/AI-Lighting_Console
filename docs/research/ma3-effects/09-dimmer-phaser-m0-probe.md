# 09. 디머 프리셋(Dimmer 풀) M0 라이브 프로브 결과

`docs/handoff/2026-08-16-session-handoff.md` §2·§3와 `08-color-phaser-m0-probe.md`의
검증된 문법·포트 전쟁 절차를 상속해, Dimmer 풀(1) 대상 프리셋 저장의 미검증 조합을
실기(onPC 2.4.2)로 확인한 기록이다. `verification-claim-integrity` 원칙에 따라
**관측된 그대로**만 적고, 추정은 GAP으로 명시한다.

- 실기: onPC 2.4.2, CopilotResponder(ping 응답 OK, 버전 문자열은 별도 확인하지 않음 — GAP)
- 선택: `Group 11`
- 디머 풀: `1` (`DataPool/PresetPools/1`, `node.class='Presets'`, `node.name='Dimmer'`,
  프로브 전 baseline `childCount=7`)
- 임시 슬롯: `1.50`(정적 → 라벨), `1.51`(2스텝 페이저, 삭제됨), `1.52`(3스텝, 삭제됨)
  — **프로브 종료 후 전부 삭제 완료, 풀 childCount 7 → 9(피크) → 7로 정확히 원복 확인**

---

## 0. 포트 전쟁 (기록)

`08-...`이 예고한 대로 `~/Documents/Claude/Code/AI-Lighting_Console` 데몬이
`Documents` cwd로 8765/9005를 재탈환했다. 이번엔 두 단계로 재발했다:

1. 우리 앱(`server.web`, pid 47476)이 `SIGTERM`에 반응하지 않아 코디네이터에게
   `kill -9` 요청 → 실행됨, 9005 비워짐.
2. `console_probe.py`를 재기동하려는 순간 `~/Documents/...` 데몬(restart=on-failure,
   pid 2181)이 즉시 9005를 재점유(`OSError: Address already in use`) — PID kill만으로는
   그 데몬의 슈퍼바이저(persist) 재기동 속도를 이길 수 없었다.
3. 코디네이터가 "cwd가 Documents인 9005/8765 홀더만 0.5초 주기로 kill -9"하는
   베이비시터 루프를 띄운 뒤에야 `console_probe.py`가 안정적으로 바인드에 성공했다.
4. 프로브 종료 후 `/tmp/port_war.sh` 재실행으로 우리 앱이 정상 재기동/재선점됨
   (`WON pid=5642 attempt=1`).

**교훈 갱신**: 단발 kill로는 이 데몬의 재기동 경합을 못 이긴다 — 슈퍼바이저 정지 또는
반복 kill 루프가 필요하다. `08-...` §환경주의사항의 "kill 전 프로세스 → 즉시 우리 앱
기동" 단발 루프는 이번엔 통하지 않았고, 코디네이터의 지속형(0.5초 주기) kill 루프로
해결했다.

---

## 1. 기본(정적) 디머 — 실측

```
ClearAll
Group 11
Attribute 'Dimmer' At 50
Store Preset 1.50
```

전부 `{'ok': True, 'result': 'OK'}`. 되읽기:

```
DataPool/PresetPools/1/50 →
  node = {'name': 'Preset 50', 'class': 'Preset', 'childCount': 0}
```

**`'Dimmer'` 속성명이 그대로 수락된다** — 대체 속성명 실측은 불필요했다(거부 없음).
Dimmer 풀(1)의 입력 필터도 순수 디머 값을 거부 없이 수용했다.

---

## 2. 디머 페이저 2스텝 — 실측

```
ClearAll
Group 11
Attribute 'Dimmer' At 30       # Step 1 = 30%
Step 2
Attribute 'Dimmer' At 100      # Step 2 = 100%
Attribute 'Dimmer' At Accel -100
Attribute 'Dimmer' At Decel -100
Attribute 'Dimmer' At Phase 0
Attribute 'Dimmer' At Speed 60
Store Preset 1.51
```

전부 `{'ok': True, 'result': 'OK'}`(9개 명령, 실패 0). 되읽기:

```
DataPool/PresetPools/1/51 →
  node = {'name': 'Preset 51', 'class': 'Preset', 'childCount': 0}
```

**컬러 채널과 동일하게, `08-...`§3 문법(`Accel`/`Decel`/`Phase`/`Speed`)이 채널명만
`ColorRGB_R/G/B` → `Dimmer`로 바뀐 채 그대로 수락된다.** 함정①(Step 1 삭제 부작용)도
재현되지 않았다 — `Step 2` 진입 직후 곧바로 `Store Preset`을 호출해도 안전했다는 점은
`08-...`§3과 동일 패턴.

**자동 이름 신호 — 컬러와의 차이(신규 관측)**: 컬러 풀은 팔레트 참조(`At Preset 4.x`)로
스텝을 채우면 자동 이름에 `[Warm White#2/Lavender#2]`처럼 스텝 내용이 노출됐다(`08-...`§2).
이번 디머 프로브는 **직접 값**(`At 30`/`At 100`)만 사용했으므로 — 이는 `08-...`§1-B
"직접 RGB 방식"과 같은 조건이다 — 자동 이름은 `Preset 51`(기본형)로, 스텝 내용이
이름에 나타나지 않았다. **디머 풀에 팔레트 참조 방식(`At Preset`)이 있는지는 이번
프로브에서 시도하지 않았다(GAP)** — 이 카탈로그는 디머를 직접 값으로만 다루면
되므로(0~100 스칼라, 참조할 "디머 팔레트"라는 개념 자체가 카탈로그 설계에 없음)
범위 밖으로 남긴다.

---

## 3. 3스텝(30→60→100) — 실측

```
ClearAll
Group 11
Attribute 'Dimmer' At 30       # Step 1 = 30%
Step 2
Attribute 'Dimmer' At 60       # Step 2 = 60%
Step 3
Attribute 'Dimmer' At 100      # Step 3 = 100%
Store Preset 1.52
```

전부 `{'ok': True, 'result': 'OK'}`. 되읽기: `node.name == 'Preset 52'`(직접 값이라
자동 이름에 스텝 내용 없음 — §2와 동일 이유). `Step 3`으로 진입 후 바로 `Store`를
호출했음에도 스텝 삭제 부작용 없음 — `08-...`§6.2(3스텝, 컬러)의 무재현 결론이 디머에서도
동일하게 성립.

---

## 4. 라벨 — 실측

```
Label Preset 1.50 'Dim 50'
```

`{'ok': True, 'result': 'OK'}`. 되읽기: `node.name == 'Dim 50'` — 공백+숫자를 포함한
라벨이 그대로 반영됨. (숫자만 단독인 라벨은 이번엔 시도하지 않음 — GAP, 다만 `08-...`가
이미 이 명령 형태를 확립한 채널-무관 문법이므로 위험도는 낮게 본다.)

---

## 5. 정리(cleanup) 검증

```
DataPool/PresetPools/1  childCount: 7(baseline) → 9(1.50+1.52 저장 후, 1.51은 §2에서
                                                    이미 삭제) → 7(전부 삭제 후)
```

`Delete Preset 1.5x` 3회(1.50, 1.51, 1.52) 전부 `{'ok': True}` + 즉시 `state` 재조회로
`path segment not found` 확인 — 부작용 없이 정확히 원복됨. `08-...`§2와 동일 패턴.

---

## 6. GAP — 이번 프로브가 채우지 못한 것

1. **디머 풀의 팔레트 참조 방식**(`At Preset 1.x`로 다른 디머 프리셋을 스텝에 싣는
   문법)은 시도하지 않았다 — 카탈로그가 직접 값(0~100)만 쓸 계획이라 범위 밖으로 판단.
2. **숫자만 단독인 라벨**(예: `'50'`)은 시도하지 않았다 — 공백+숫자 조합(`'Dim 50'`)만
   확인.
3. **저장된 프리셋의 실제 스텝 개수/Accel-Decel-Phase-Speed 반영 여부를 기계로 셀
   방법** — `08-...`§2/§4/§6.4와 동일한 구조적 한계(`state` childCount:0,
   `prop StepCount/Steps` 모두 미탐색). 이번엔 `prop` 재탐색도 하지 않았다(범위 밖).
4. **Rectangle Form 근사**(`Transition 0`)는 디머에서 시도하지 않았다 — 카탈로그에
   Rectangle 디머 항목이 없다면 불필요, 필요해지면 `08-...`§6.1 패턴을 채널명만 바꿔
   재사용 가능할 것(ASSUMPTION, 미검증).

---

## 7. 다음 세션(카탈로그 구현)에 대한 시사점

- **`'Dimmer'` 속성명 + `08-...`의 스텝/Form/Phase/Speed 문법이 채널명 치환만으로
  디머에 그대로 이식된다** — 별도의 디머 전용 문법 조사는 불필요해 보인다.
- 함정①(Step N 진입 직후 Store 안전) — 2스텝·3스텝 둘 다 디머에서도 무재현 확인,
  기존 `_preset_store_commands` 몸통을 그대로 재사용 가능.
- 자동 이름 신호는 디머에서 항상 기본형(`Preset NN`)이다 — 컬러처럼 저장 직후 사람
  검증용 신호로 쓸 수 없으므로, 디머 카탈로그는 저장 즉시 `Label Preset`을 붙이는
  흐름에 더 의존하게 될 것(설계 시사점, 구현 아님).
- **포트 전쟁 대응 갱신**: 이번 세션처럼 데몬 재기동이 PID kill보다 빠른 경우가
  재발하면, 단발 kill 대신 곧바로 "지속형 kill 루프(0.5초 주기)"를 요청하는 편이
  왕복 지연을 줄인다.
