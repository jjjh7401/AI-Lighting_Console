# 콘솔에 없는 픽스처 타입 — CSV 실측 전수표

> t98 리드 세션, 2026-08-30. 감독 요청 산출물.
> 근거: `lxseq_e2e --action preview` 의 `skipped[kind=type_unresolved]` 54행을
> `LXSEQ_RIG_01_ShowBase_r3.patch.csv` 의 FID 로 조인. **콘솔 쓰기 0.**

## 0. 먼저 정정 — 8종이 아니라 **6종**이다

인계 문서 §3 이 「없는 것」을 8종으로 적었으나, 54행을 전수로 조인하면 **6종**이다.
그 8종 목록은 콘솔에 **있는** 8종(`Patch/FixtureTypes` child_count 8)과 개수가 같아
혼동한 것으로 보인다. 아래가 실측이다.

## 1. 필요 목록 — 6종 / 54대 (전수, 54 of 54 커버)

| 대수 | 기종 (CSV 표기) | Mode | Ch | FID | 그룹 | 위치 |
|---:|---|---|---:|---|---|---|
| 20 | `Martin RUSH PAR 2 RGBW Z` | `9ch` | 9 | 401~430 | WASH-D · WASH-U | 다운/업스테이지 플로어 |
| 14 | `ETC S4 LED S3 Lustr X8` | `Direct 12ch` | 12 | 101~118 | FOH · KEY | FOH 브리지 · FOH 트러스 |
| 8 | `Robe MegaPointe` | `Mode 1 39ch` | 39 | 501~508 | MOVER-U | 업 트러스 |
| 6 | `Elation CUEPIX Blinder WW2` | `4ch` | 4 | 601~606 | BLIND | 다운 트러스 전면 |
| 4 | `Martin Atomic 3000 LED` | `Extended 14ch` | 14 | 611~614 | STROBE | 업 트러스 |
| 2 | `Look Unique 2.1` | `2ch` | 2 | 621~622 | HAZE | 무대 양측 플로어 |

**합계 54대.** CSV 전체는 86행이고, 나머지 32행은 다른 사유다
(`mode_unresolved` 24 · `address_occupied` 7 · 계획됨 1).

## 2. 콘솔에 이미 있는 8종 (대조군)

    Robin Esprite · Robin Forte HP · Robin LEDBeam 350 · Robin Spiider
    Xtylos · Sharpy Plus · Robin MMX Spot · Mac Aura XB

`Patch/FixtureTypes` child_count **8** · truncated **false** — 절단이 아니라 전수다.
날조 대조군 `Patch/FixtureTypesZZZNotAThing/9999` 선행 거절로 채널 신뢰성 확인.

## 3. 안 잰 것

- **CSV 의 Mode 문자열이 MA3 라이브러리의 모드 이름과 같은지** — 타입을 넣은 뒤에도
  `mode_unresolved` 로 다시 걸릴 수 있다. Mac Aura XB 가 정확히 그 형태다
  (타입은 있는데 CSV 의 `Martin MAC Aura XB` 가 콘솔 모드명과 안 맞는다 → t128)
- **기종명이 MA3 라이브러리의 정식 제조사 표기와 일치하는지** — `Martin RUSH PAR 2 RGBW Z`
  같은 표기가 라이브러리에서 어떤 이름으로 등재돼 있는지 안 봤다
- 타입 추가 후 54행이 실제로 계획에 들어가는지 (타입이 없어 preview 까지만)
