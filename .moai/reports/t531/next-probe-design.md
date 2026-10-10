# t531 M1 다음 프로브 설계안 — 위치 상대값이 왜 멈춰 있나 (설계만, 실행은 재승인)

작성 2026-10-10. 콘솔 접촉 0. 이 문서의 줄은 리허설·전부-거절 전이다.

## 무엇을 가르나

⑤(위치 프리셋 + 상대값 원)와 ⑨ wave(위치 프리셋 + Tilt 상대값 + 위상 펼침)는 감독 눈에 둘 다 「멈춰 있음」이었다.
t516 A2(시퀀스 236)는 상대값 한 단계였는데 Tilt 가 움직였다(`t516/verdict.md:385`).

| | ⑨ wave (멈춤) | t516 A2 (움직임) |
|---|---|---|
| 선택 | `Group 11` | `Fixture 501 + … + 508 ; …` |
| 기준 | `At Preset 2.1` (위치 프리셋 호출) | 같은 큐에 `Attribute 'Tilt' At 45` (단, 큐에는 안 남았다 — `t516/verdict.md:390`) |
| 크기 | `Attribute 'Tilt' At Relative 12` | `Attribute 'Tilt' At Relative 30` |
| 위상 | `Attribute 'Tilt' At Phase 0 Thru 360` | 같음 |
| 속도 | `Attribute 'Tilt' At Speed 60` | `Attribute 'Tilt' At Speed 112` |
| 디머 | 없음(다른 큐가 켜 둔 상태에 기댐) | `Attribute 'Dimmer' At 70` 같은 큐 |

⑩에서 `Group 11` 선택으로 디머 페이저 + 위상 펼침이 먹었으므로(감독 「물결처럼 차례로」), 「Group 선택이면 페이저가 안 먹는다」는 약하다. 남은 후보: **크기 · 기준 프리셋 호출 · 속도 · 디머 유무**.

🔴 디머 유무가 실제 후보일 수 있다: ⑤⑨ 큐에는 디머 줄이 없다. 장비가 꺼져 있었다면 「멈춰 있음」과 「안 보임」이 섞였을 수 있다 — 감독이 「프리셋 자리에 서 있다」고 했으니 빛은 보였을 것(추정). 다음 묶음에는 디머를 넣어 이 갈래를 닫는다.

## 묶음 — wave 를 기준으로 한 번에 하나만 바꾼다

모두 새 시퀀스, 실행 직전 빈 번호 확인. 공통 앞줄 `ChangeDestination Root` / `ClearAll`, 공통 끝줄 `Store Sequence <n> Cue 1 '<이름>'` / `Set Sequence <n> Property 'Name' '<이름>'` / `ClearAll`. 재생 묶음은 **시퀀스마다 따로**(⑨의 「한 번에 켜고 끄기」 한계를 반복하지 않는다): `Goto Cue 1 Sequence <n>` → 감독 눈 → `Off Sequence <n>`.

| 번호 | 시퀀스 | wave 에서 바꾼 것 | 몸통 줄 |
|---|---|---|---|
| ⑫-0 기준 | 311 | 디머만 더함(나머지 wave 그대로) | `Group 11` / `Attribute 'Dimmer' At 70` / `At Preset 2.1` / `Attribute 'Tilt' At Relative 12` / `Attribute 'Tilt' At Phase 0 Thru 360` / `Attribute 'Tilt' At Speed 60` |
| ⑫-a 크기 | 312 | ⑫-0 에서 Relative 12 → **30** | ⑫-0 과 같고 `Attribute 'Tilt' At Relative 30` |
| ⑫-b 속도 | 313 | ⑫-0 에서 Speed 60 → **112** | ⑫-0 과 같고 `Attribute 'Tilt' At Speed 112` |
| ⑫-c 기준 | 314 | ⑫-0 에서 `At Preset 2.1` → **`Attribute 'Tilt' At 45`** | ⑫-0 과 같고 기준 줄만 교체 |
| ⑫-d 대조 | 315 | **t516 A2 그대로** (`Fixture 501 + … + 508`, Tilt 45, Relative 30, Phase 0 Thru 360, Speed 112, Dimmer 70) | `t516/approval_rhythm_probe_v4.txt:19-25` 을 시퀀스 번호만 바꿔 |

⑫-d 는 양성 대조다. 지금 쇼·장비 상태에서 A2 가 다시 움직이는지 먼저 확인해야 ⑫-0~c 의 「멈춤」을 해석할 수 있다. ⑫-d 도 멈추면 원인은 이 묶음의 변수가 아니라 환경(장비 상태·마스터·다른 시퀀스 우선) 쪽이다.

## 판정 읽기

- ⑫-d 움직임 + ⑫-0 멈춤 + ⑫-a/b/c 중 하나만 움직임 → 그 변수가 원인.
- ⑫-0 이 움직임 → 원인은 디머 유무(⑤⑨ 에 디머가 없었다).
- 둘 이상 움직임 → 변수가 하나가 아니다. 본 그대로 적는다.
- ⑫-d 멈춤 → 묶음 해석 보류, 환경부터 본다.

## 안 잰 것 · 위험

- `Group 11` 의 구성원이 `Fixture 501 … 508` 과 같은지는 안 쟀다(그룹 COUNT 는 0 으로 읽힌다, t95). 응답기 1.6.6 나눠 읽기로 `group_members.py` 를 돌리면 잴 수 있다 — 이 묶음 전에 읽기 전용으로 먼저 하는 것을 권한다(쓰기 0).
- 상대값 크기 단위(도)는 장비마다 Pan/Tilt 범위가 달라 눈에 보이는 크기가 다르다 — 12 가 「작아서 안 보인」 것인지는 ⑫-a 로만 가린다.
- 끄기는 시퀀스마다 하나씩. 쇼 저장 0.
