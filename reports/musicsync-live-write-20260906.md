# 실기 쇼파일 쓰기 회차 — 곡 → 큐 리스트 (2026-09-06)

기준 트리: main `54cc17c` · **실기 grandMA3 onPC, 라이브 잠금 끔, 실제 저장 수행** · 쇼파일 백업 선행

## 결론

곡 파일 하나가 **실기 쇼파일에 실제로 큐 리스트를 남겼다.** `Sequence 5 "Synth Test"` 와 `Timecode 7 "Synth Test Timecode"` 가 생겼고 콘솔에서 되읽어 확인했다.

동시에, **가짜 콘솔에서는 볼 수 없던 결함 하나를 잡았다**: 감독이 확인한 구간은 4개인데 큐는 **3개만** 생겼다. 첫 구간(0:00, D1, 이름 `Intro`)의 큐가 **경고 없이 사라진다.** → 카드 `t277`.

## 착수 전에 잰 것 (묻지 않고 진행한 근거)

2026-08-25 지시(「bypass 에서는 되돌릴 수 없는 콘솔 쓰기까지 판단해서 진행」)의 세 조건을 모두 실측했다:

| 조건 | 실측 |
|---|---|
| (a) 전제를 재었는가 | `DataPool/Sequences` → 점유 1·2·3·4·9·2000 → **슬롯 5 비어 있음**. `DataPool/Timecodes` → `childCount 0` → **7번 비어 있음**. 덮어쓸 대상 없음 |
| (b) 롤백 지점 | 세션 시작 백업이 실제로 실행됨 — 감사 로그 `{"command": "SaveShow", "kind": "backup", "ok": true}` (12:42:20) |
| (c) 안전 이음매 | 직전 라이브 잠금 회차에서 게이트가 26/26 을 `blocked / live lock active` 로 실제로 막는 것을 관측 |

## 실행

지시문: 「이 곡으로 큐 리스트 만들어줘. 제목 Synth Test, 장르 EDM, 타임코드 7번. 구간 이름은 Intro, Build, Drop, Outro 로 해줘」

- 미리보기 26개 → **「요청한 명령을 모두 실행했습니다 — 실행 완료 26」**
- 감사 로그 `executed` **27**(= SaveShow 1 + 명령 26), `blocked` 0

## 되읽기 (콘솔이 답한 값)

```
DataPool/Timecodes   → [(7, 'Synth Test Timecode')]
DataPool/Sequences   → [(1,'Default'), (2,'Sugar'), (3,'Sugar r3'), (4,'eset1Fade'),
                        (5,'Synth Test'), (9,'T215 SCRATCH DELETABLE'), (2000,'Sequence 2000')]
DataPool/Sequences/5 → [{cueNo:—, name:'OffCue'}, {cueNo:0,'CueZero'},
                        {cueNo:2,'Build'}, {cueNo:3,'Drop'}, {cueNo:4,'Outro'}]
```

시퀀스도 타임코드도 실제로 생겼다. `OffCue`·`CueZero` 는 MA3 가 스스로 붙이는 것이다.

## 🔴 발견 — 첫 구간의 큐가 사라진다 (카드 t277)

확정은 「구간 **4건** 채택 · 0건 제외」였는데, 저장된 감독용 큐는 `Build` · `Drop` · `Outro` **셋**이다. `cueNo 1` 이 없고 `Intro` 라는 이름은 **감사 로그 전체에 0건** — 즉 콘솔이 거절한 게 아니라 **앱이 애초에 보내지 않았다.**

```
$ grep -o '"command": "[^"]*Intro[^"]*"' audit-20260906.jsonl   → (출력 없음)
$ … | grep 'Store Sequence'
"Store Sequence 5 Cue 2 'Build'"   "Store Sequence 5 Cue 3 'Drop'"   "Store Sequence 5 Cue 4 'Outro'"
```

이름은 밀리지 않았다 — `Build` 는 15.952초(2번째 구간), `Drop` 은 32.02초(3번째), `Outro` 는 36.014초(4번째)에 정확히 붙었다. **없어진 것은 첫 구간(0:00) 자체**다.

대조: 같은 날 가짜 리그 회차(구간 3건)에서는 `Store Sequence 4 Cue 1 'S1'` 이 TrigTime 0 으로 정상 생성됐다. 그러니 「0:00 구간은 원래 안 만든다」가 아니다 — 구간 수, 혹은 실기 리그의 룩 매핑에 달린 문제다. **원인 미확정.**

왜 심각한가: 감독은 화면에서 4개를 확인했고 앱은 「모두 실행했습니다」라고 답했다. 첫 곡 구간에 조명이 없다는 사실은 **공연에서 처음 드러난다.**

## 안 잰 것

- 결함의 원인. 구간 수 의존인지, 실기 리그(그룹 18개)의 룩 매핑에서 첫 구간이 값 없이 접히는 것인지 미확정 — t277 이 잰다.
- 큐 내용의 조명적 타당성(디머 72/100/42, 색·줌·아이리스). 값이 들어갔다는 것만 확인했다.
- 타임코드 7이 시퀀스 5를 실제로 구동하는지(재생 검증). `Assign` 명령은 나갔고 되읽기로 존재만 확인했다.
- 이 회차가 남긴 것을 지우지 않았다. 되돌리려면 콘솔에서 `Delete Sequence 5` · `Delete Timecode 7`; 그 전 상태는 12:42:20 백업에 있다.

## 후속 (같은 날 처리됨)

**t277 닫힘 — PR #327 `cc1821f`.** 원인을 재현으로 확정했다: EDM D1 룩 `edm-ambient-hold` 가 역할 **배경**(별칭 `cyc`/`backdrop`)을 요구하는데 이 리그 그룹 18개에 CYC 계열이 없다 → `reason_kind: role_unaddressed`. 구간 수와 무관하다(같은 4구간이 CYC 있는 리그에서는 4건 다 저장된다).

**건너뜀 판단 자체는 옳다** — 그룹 없이 큐를 저장하면 더 나쁘다. 결함은 도구가 결과에 정직하게 실은 `unmapped_sections` 가 감독 화면에 닿지 않은 것이었다. 이제 명령 표 뒤에 한 줄이 붙는다(머지 뒤 실기 그룹명 + 진짜 룩 라이브러리로 실측한 문자열):

```
구간 4건 중 큐 3건만 저장했습니다 — 'Intro': 이 리그에 배경 역할 그룹이 없습니다.
```

건너뜀이 0건이면 빈 문자열 — 오늘 출력과 바이트 동일. 기존 시험이 이 결함을 못 잡은 이유(시험용 가짜 리그에 `Cyc` 가 있다)는 실기 그룹 이름 18개를 픽스처로 박아 막았다.

**화면에서 확인됨 (세 번째 실기 회차, 머지 후).** 같은 요청을 실기에 다시 걸어 브라우저에서 눈으로 봤다 — 캡처 `.moai/state/verify/t277-notice/notice-onscreen.jpeg`:

> 요청한 명령을 모두 실행했습니다. **구간 4건 중 큐 3건만 저장했습니다 — 'Intro': 이 리그에 배경 역할 그룹이 없습니다.**

두 문장이 나란히 서고 둘 다 참이다. 이 회차가 `Sequence 7 "Notice Check"` · `Timecode 9` 를 남겼다(저장된 큐는 여전히 `Build`·`Drop`·`Outro` 셋 — 고지는 그 사실을 숨기지 않고 말한다).

(두 번째 회차 `Sequence 6 "Notice Test"` · `Timecode 8` 은 브라우저 데몬이 끊겨 화면을 못 본 회차다. 콘솔 쪽은 정상 완료됐다.)

## 다음 손

1. t276 — 한글 큐 라벨.
2. 재생 검증(타임코드가 실제로 큐를 돌리는가)은 별도 회차.
3. 이 회차들이 남긴 것: `Sequence 5`·`6`, `Timecode 7`·`8`. 지우려면 콘솔에서 `Delete Sequence 5` / `Delete Sequence 6` / `Delete Timecode 7` / `Delete Timecode 8`.
