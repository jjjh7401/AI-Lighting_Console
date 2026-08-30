# `address_occupied` 12행 — 실측 전수 + 점유자

> t98 리드, 2026-08-30. **콘솔 쓰기 0** (`--approve` 없음).
> 응답기 **1.6.2** 구간. 기준 `origin/main` `3c07114`.

## 0. 왜 이 문서가 있나 — 「12」가 산수였다

리드가 앞서 `address_occupied` 를 **12행**이라 적었는데, 그건 **두 회차의 덧셈**이었다:

    7   전체 CSV preview (오버라이드 없음)          FID 521~527
    5   Aura 24행만 (--only-fids, run 레인)          FID 311~315
    --
    12  **더한 값 — 한 번에 잰 적이 없다**

t105 가 「12 중 5가 SIDE-R 인지, 아니면 두 회차 값이 다른지」를 물었다. 정당한 물음이다 —
두 회차는 **모집단이 다르다**(전체 86행 vs `--only-fids` 24행). 산수로 답하지 않고 쟀다.

    lxseq_e2e --action preview --mode-overrides '{"Martin MAC Aura XB": "Extended - RGB"}'
      (전체 CSV · --only-fids 없음)

## 1. 실측 — 12행이 맞다. 그리고 두 무리는 서로 겹치지 않는다

    미리보기 — 쓰기 0건. 런 4개 · 계획 20대 · 건너뛴 행 66건
    type_unresolved  54
    address_occupied 12
    mode_unresolved   0   ← 오버라이드가 24행을 전부 풀었다

| FID | 요구 주소 | 점유자 | 무리 |
|---|---|---|---|
| 521 | 3.1 | `Robin LEDBeam 350 21` | A — 유니버스 3 |
| 522 | 3.50 | `Robin LEDBeam 350 25` | A |
| 523 | 3.99 | `Robin LEDBeam 350 28` | A |
| 524 | 3.148 | `Robin LEDBeam 350 31` | A |
| 525 | 3.197 | `Robin LEDBeam 350 34` | A |
| 526 | 3.246 | `Robin LEDBeam 350 37` | A |
| 527 | 3.295 | `Robin LEDBeam 350 40` | A |
| 311 | 5.1 | `Sharpy Plus 41` | B — 유니버스 5 (`SIDE-R`) |
| 312 | 5.26 | `Sharpy Plus 42` | B |
| 313 | 5.51 | `Sharpy Plus 43` | B |
| 314 | 5.76 | `Sharpy Plus 44` | B |
| 315 | 5.101 | `Sharpy Plus 45` | B |

**A 7행 + B 5행 = 12행.** 덧셈이 맞았지만, 이제는 **한 번의 측정이 낸 값**이다.
B 는 `mode_unresolved` 가 가리고 있던 자리다 — 모드가 풀리자 드러났다.

## 2. 무리 A 와 B 는 성격이 다르다

    A  FID 521~527  요구 기종 Robe MegaPointe   점유자 Robin LEDBeam 350
       -> 다른 기종이 그 주소에 있다
    B  FID 311~315  요구 기종 Martin MAC Aura XB 점유자 Sharpy Plus
       -> 역시 다른 기종이다

**둘 다 「같은 장비가 이미 패치돼 있다」가 아니라 「다른 장비가 그 주소를 쓰고 있다」다.**
리드가 앞서 「우리 장비가 이미 그 자리에 있다 → 기존 패치가 CSV 의도를 만족할 수 있다」고
적었는데, **기종이 달라 그 가설은 성립하지 않는다.** t129 카드 본문의 그 전제를 고쳐라.

## 3. 오버라이드가 실제로 무엇을 열었나

    오버라이드 없음   런 1개 · 계획  1대 · 건너뜀 85 (type 54 / mode 24 / occupied  7)
    Extended - RGB    런 4개 · 계획 20대 · 건너뜀 66 (type 54 / mode  0 / occupied 12)

**계획 1대 → 20대.** 다만 24행 중 19행이 계획에 들어가고 5행이 점유에 걸렸다.

## 4. 안 잰 것

- **FID 316 이 왜 안 걸렸는지** — CSV 는 316도 요구하는데 skipped 에 없다. 계획에 들어간
  것으로 보이나 확인 안 했다
- **점유자들의 FID** — 이름(`Sharpy Plus 41`)만 답했고 그 장비의 FID 는 안 읽었다.
  CSV 의 다른 행이 그 FID 를 요구하는지 대조하려면 필요하다
- **CSV 주소가 틀린 것인지, 콘솔 패치가 틀린 것인지** — 어느 쪽이 정본인지는 감독 판단이다
- 무리 A 와 B 가 같은 원인인지 — 유니버스도 기종도 다르다. 한 원인으로 묶지 마라
