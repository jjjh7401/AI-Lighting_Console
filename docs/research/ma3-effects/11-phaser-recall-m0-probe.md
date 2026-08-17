# 11. 페이저 recall M0 라이브 프로브 — ①즉시 recall ②시퀀스+Exec ③곡 큐 전제 문법

`docs/research/ma3-effects/{08,09,10}-*-m0-probe.md`가 확립한 **저장** 문법(스텝 생성·
Form·Phase)은 재검증하지 않고, 이미 저장된 페이저 프리셋을 **소비**하는 recall·해제·
큐-저장 문법만 실측한다. `docs/handoff/2026-08-16-session-handoff.md` §3 포트 전쟁
절차를 그대로 상속했다. `verification-claim-integrity` 원칙에 따라 **관측된 그대로**만
적고, 추정은 GAP으로 명시한다.

- 실기: onPC 2.4.2, `console_probe.py` 직결(응답기 버전 문자열 별도 미확인 — GAP, `Ping`
  exec는 응답기가 `{"error": "Illegal object"}`로 거부해 미채택; 다른 명령들은 전부
  `ok:true`로 정상 응답해 연결 자체는 확인됨)
- 선택: `Group 11`, 보조 픽스처 셀렉터 `Fixture 2`(존재 확인됨)
- 재료(사전 저장된 실물): Color 4.31 `Breathe Warm`(2스텝), Dimmer 1.21 `Breathe Soft`
  (2스텝), All 1 21.21 `Drop Slam`(2스텝) — 셋 다 `state` 직접 조회로 라벨 실재 확인
- 임시 슬롯: `4.99`/`1.99`/`21.99`(프리셋), `Sequence 999`(시퀀스) — **프로브 종료 후
  전부 삭제 완료, 풀 childCount 원복 확인**(§7)

## 0. 포트 전쟁 (기록)

프로브 시작 시 우리 앱(`server.web`, pid 78858, cwd=orca 워크트리)이 이미 9005/8765를
쥐고 있었다 — 남의 데몬이 아니라 우리 자신의 이전 인스턴스였다. `SIGTERM`에 무반응
(기존 교훈과 동일 패턴)이라 Bash `kill -9`를 시도했으나 정책에 막혀 `ask`로 코디네이터에게
승인 요청 → `kill -9 78858` 실행됨 + 30분 베이비시터 루프(Documents 홀더 자동 사살)
가동 확인. 프로브 종료 후 `/tmp/port_war.sh`로 즉시 재선점 성공(`WON pid=39080
attempt=1`).

---

## 1. [최우선] recall이 페이저를 통째로 싣는가 — **판독 불가(구조적 한계), 대안 신호도 중립**

### 1.1 직접 판독 시도 — 전부 거부됨

```
ClearAll
Group 11
At Preset 4.31          # Breathe Warm 리콜
state Programmer         → {"ok": false, "error": "path segment not found: 'Programmer' ..."}
state ProgrammerPart     → {"ok": false, "error": "path segment not found: 'ProgrammerPart' ..."}
state Selection          → {"ok": false, "error": "path segment not found: 'Selection' ..."}
state SelectedFixtures   → {"ok": false, "error": "path segment not found: 'SelectedFixtures' ..."}
prop Programmer|Dimmer   → {"ok": false, "error": "path segment not found: 'Programmer' ..."}
prop 'Group 11'|Dimmer   → {"ok": false, "error": "path segment not found: 'Group 11' ..."}
```

`console/lua/copilot_responder.lua`의 `resolve_path`/`ROOT_ALIASES`를 코드로도 확인했다
— 이 응답기가 인식하는 루트는 `datapool`/`root`/`showdata`/`patch`(+ `Executor <n>` 특수
케이스)뿐이고, 프로그래머·선택(Selection) 핸들을 노출하는 별칭이 아예 없다. 즉 이번
프로브 범위의 실패가 아니라 **이 프로토콜 경로 자체가 구조적으로 프로그래머를 읽을 수
없다**(08~10번 문서의 `state childCount:0`/`prop not readable` GAP과 같은 계열의 한계이되,
이번엔 저장된 프리셋이 아니라 프로그래머 자체가 대상이라 더 근본적이다).

### 1.2 대안 증거 시도 — recall 직후 재저장한 자동 이름 (중립, 확정적이지 않음)

```
(위 recall 상태에서) Store Preset 4.99
state DataPool/PresetPools/4/99 → node.name == "Preset 99"   (기본형, 스텝 라벨 없음)
Delete Preset 4.99
```

Dimmer(1.21→1.99)·All 1(21.21→21.99)도 동일 패턴으로 반복 — **셋 다 `Preset 99`류
기본 이름**으로만 되읽혔다.

**대조군(08번 문서 기존 결과)과 비교**: 08번 문서는 프로그래머에서 **스텝을 처음부터
직접 만들 때**(`At Preset 4.21` → `Step 2` → `At Preset 4.30` → `Store`) 자동 이름에
`[Warm White#2/Lavender#2]`처럼 두 스텝 라벨이 노출된다고 기록했다. 이번 프로브는 그
대조군과 달리 **이미 저장된 2스텝 프리셋을 `At Preset 4.31` 한 줄로 recall한 뒤 바로
재저장**했는데, 자동 이름이 스텝 내용을 전혀 반영하지 않았다.

**정직한 해석**: 이 차이는 "recall이 첫 스텝만 실었다"는 증거가 **아니다** — 자동 이름
로직은 08번 문서 관찰상 "스텝을 `At Preset x.y`로 순차 조립하는 과정" 자체에 붙는 이름
생성 규칙으로 보이며, 이미 완성된 프리셋을 단일 recall로 불러온 경우엔 애초에 그 조립
경로를 타지 않아 이름이 기본형으로 남는 것으로도 설명된다. 즉 이 신호는 **recall이
몇 스텝을 실었는지에 대해 중립적**이며, 확정도 반증도 아니다.

**결론: "recall이 페이저를 통째로 싣는가"는 이번 프로토콜 경로(OSC/Lua state/prop)로는
판독 불가로 정직하게 남긴다.** 확정하려면 라이브에서 픽스처가 실제로 두 색/두 레벨
사이를 오가는지 눈으로 관찰하는 절차가 필요하며(08번 문서 §3 Rectangle 절과 동일한
구조적 이유), 이 저장소는 OSC/Lua만 쓰는 시각 확인 채널이 없다 — 이번 세션 범위 밖.

---

## 2. recall 커맨드 문법 — Color/Dimmer/All 3풀 전부 수락

`pointing.py:351`(`preset_recall_command`)의 `Fixture <fids> ; At Preset <pool>.<slot>`
문법을 풀만 바꿔 실측:

| 풀 | 커맨드 | 결과 |
|---|---|---|
| Color(4) | `Fixture 2 ; At Preset 4.31` | `{'ok': True, 'result': 'OK'}` |
| Dimmer(1) | `Fixture 2 ; At Preset 1.21` | `{'ok': True, 'result': 'OK'}` |
| All 1(21) | `Fixture 2 ; At Preset 21.21` | `{'ok': True, 'result': 'OK'}` |

**셋 다 거부 없이 수락됐다** — `pointing.py`의 포지션 프리셋 recall과 동일한 문법이
풀 번호만 바꿔 그대로 재사용 가능하다는 근거. `Group 11` 셀렉터로도(§1) 동일하게 수락됨을
이미 확인했다.

---

## 3. 해제(off) 문법 — 후보 3종 중 2종 수락, 1종 거부

| 후보 | 커맨드 | 결과 |
|---|---|---|
| `Off` | `Off` | `{'ok': True, 'result': 'OK'}` — **수락** |
| `At Preset 0` | `Fixture 2 ; At Preset 0` | `{'ok': True, 'result': 'OK'}` — **수락** |
| `Group 11 Off` | `Group 11 Off` | `{'ok': False, 'error': 'Not implemented'}` — **거부**(명시적 "Not implemented") |

`ClearAll`은 08~10번 문서에서 이미 매 시퀀스마다 반복 검증됐으므로 재검증하지 않았다
(항상 `ok:true`). **결론: 해제는 `Off` 단독 명령 또는 `Fixture <fids> ; At Preset 0`
둘 다 유효하고, 셀렉터 토큰에 `Off`를 이어붙이는 형태(`Group 11 Off`)는 이 응답기의
명령 실행 경로에서 거부된다** — "Not implemented"라는 정확한 에러 문자열까지 그대로
기록한다(추측 아님).

---

## 4. 큐 저장이 페이저 참조를 보존하는가 — 큐 생성은 성공, 참조 여부는 판독 불가

```
ClearAll
Group 11
At Preset 4.31                                    # Breathe Warm 리콜
Store Sequence 999 Cue 1 'PhaserTest' CueFade 2   → {'ok': True, 'result': 'OK'}
state DataPool/Sequences/999
  → children: [OffCue(i=1), CueZero(i=2, cueNo=0), PhaserTest(i=3, cueNo=1)]
prop DataPool/Sequences/999/3 | Name              → {'ok': True, 'value': 'PhaserTest'}
prop DataPool/Sequences/999/3 | CueFade            → {'ok': False, 'error': 'property not readable: CueFade'}
state DataPool/Sequences/999/3                    → children: [Part(i=1, name='PhaserTest')]
state DataPool/Sequences/999/3/1 (그 Part)        → childCount:0, children:[]  (더 이상 못 들어감)
Delete Sequence 999                                → {'ok': True}  (재조회로 삭제 확인)
```

**큐 생성 자체는 성공했다** — `CueNo=1`, 라벨 `PhaserTest`가 정확히 반영됐고 `Name`
프로퍼티는 읽힌다. 하지만 그 큐가 Preset 4.31에 대한 **참조**를 들고 있는지, 아니면
recall 시점의 값을 **평탄화(flatten)**해 담았는지는 Cue → Part 트리를 한 단계 더
내려가도(`childCount:0`) 여전히 읽을 수 없다 — §1과 동일한 구조적 한계(응답기가
Programmer/Cue-Part 내부 속성 트리를 노출하지 않음)가 여기서도 그대로 재발한다.
**판독 불가로 정직하게 남긴다.**

---

## 5. 라벨→슬롯 역인덱스 가능성 — **가능, 실측으로 입증됨**

`_paged_pool_children`(session.py:6749) 패턴을 그대로 재현해 Color 풀(4)을 오프셋
페이징으로 완전 열거:

| offset | 응답 |
|---|---|
| 0 | i=1~7(곡 큐 실물 라벨), i=11~19(Warm White~Magenta), `truncated:true` — **16개**에서 절단(24개 캡이 아니라 한글 라벨의 바이트 크기가 이번 창을 더 일찍 채웠다, §6 GAP) |
| 16 | i=20(Lavender)~i=38(Pulse RY) — **`i=31 → "Breathe Warm"` 여기서 직접 확인**, `truncated:true` |
| 32 | i=36~i=40(Wave WA~Slam RW), `truncated:false`(끝) |

`childCount:37`(전체) — 페이징 3회로 전 풀을 완전 열거했고, **핸드오프 문서가 제안한
카탈로그 10종(Breathe Warm=31 ~ Slam RW=40)이 라벨·슬롯 번호 그대로 실기에 존재함을
직접 관측으로 재확인**했다(별도 세션이 이미 구현·저장한 것으로 보임 — 이번 세션 범위
밖의 사전 상태).

**결론: 라벨→슬롯 역인덱스는 가능하다.** 앱이 슬롯 번호를 코드 상수로 몰라도, 페이지드
`state` 읽기의 `{"i": <slot>, "name": <label>}` 쌍을 순회하면 라벨 문자열로 슬롯을 찾는
사전을 런타임에 만들 수 있다 — `_paged_pool_children`이 이미 정확히 이 패턴을 구현하고
있다(신규 구현 불필요, 기존 몸통 재사용 가능이라는 근거를 이번 프로브가 실측으로 보강).

---

## 6. GAP — 이번 프로브가 채우지 못한 것

1. **recall이 페이저를 통째로 싣는지 여부**(§1) — 가장 중요한 미해결 항목. `state`/`prop`
   경로 둘 다 프로그래머 자체를 노출하지 않고(`resolve_path`에 Programmer/Selection
   별칭 없음), 대안 신호(재저장 자동 이름)도 중립이다. 확정하려면 라이브 시각 관찰이
   필요(구조적 한계, OSC/Lua 전용 저장소).
2. **큐가 프리셋 참조인지 평탄화인지**(§4) — Cue→Part 트리가 `childCount:0`으로 막혀
   더 내려갈 수 없다. §1과 같은 이유로 미해결.
3. **응답기 버전 문자열** — `Ping` exec가 `Illegal object`로 거부돼 버전 확인 생략
   (연결 자체는 다른 명령들의 `ok:true`로 충분히 확인됨).
4. **Color 풀 첫 페이지가 16개에서 절단된 이유** — `session.py` 주석은 24개 캡을
   말하지만 실측은 16개였다(한글 라벨 다수 포함 시 바이트 크기 캡이 먼저 걸린 것으로
   추정 — 확정 안 함, 이번 세션 범위 밖).

---

## 7. 정리(cleanup) 검증

```
DataPool/PresetPools/4  childCount: 37 (프로브 전후 동일)
DataPool/PresetPools/1  childCount: 27 (프로브 전후 동일)
DataPool/PresetPools/21 childCount: 26 (프로브 전후 동일 — 08~10번 문서 세션 이후
                                          콤보 페이저 10종이 별도로 커밋된 상태의 새 baseline,
                                          이번 프로브로 인한 변화 아님)
DataPool/Sequences/999  삭제 후 path segment not found 확인
```

`4.99`/`1.99`/`21.99`/`Sequence 999` 전부 삭제 후 재조회로 부재 확인 — 부작용 없이
정확히 원복됨.
