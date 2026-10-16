# live/p4_b — 항목 ④ 실기 판정 (2026-10-16)

효과 프리셋 `21.8 'WAVE PAN 2 BAR'` 와 `21.9 'WAVE PAN 2 BEAT'` 를 프리셋 계획 카드(PR #775 절차)로 저장했다.
승인 카드의 명령(21.9 기준):

```
ClearAll
Group 11
Attribute 'Pan' At Relative -12
Step 2
Attribute 'Pan' At Relative 12
Step accel-decel
Attribute 'Pan' At Speed 56.001
Store Preset 21.9 'WAVE PAN 2 BEAT' /Universal
Label
ClearAll
```

감독이 grandMA3 onPC 에서 `Group 11 At Preset 21.9` 를 호출하고 보고한 원문:

> 「좌우로 움직이고 불은 들어오지 않아」

해석: 무버가 좌우로 팬한다. 디머는 큐의 DIM 프리셋에서 오므로 불이 안 들어오는 것이 정상이다.
감독 원문에 번갈아/한꺼번에 여부는 없다 — 판정은 거기까지만 주장한다.
이 폴더에는 감독 원문과 승인 명령만 있다(기계 되읽기 로그 없음).
