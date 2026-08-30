# Mac Aura XB 모드 매핑 — 폭으로는 안 정해진다 (t128)

> 2026-08-30. 기준 `origin/main` `f871c76`. 리드 배차분.
> **콘솔 쓰기 0건** — 모든 preview 를 `--approve` 없이 돌렸고, 하네스가
> 「없으면 콘솔에 아무것도 닿지 않는다」고 명시한다.

---

## 0. 결론

**카드의 전제가 성립하지 않는다.** 「CSV 의 채널폭을 읽어 어느 모드인지 확정」은
원리적으로 불가하다 — 폭 25 는 6모드 중 3종을 남긴다.

**다만 막힌 것은 아니다.** 남은 세 후보 중 무엇을 골라도 **패치 결과가 완전히 같다.**
그러므로 이것은 주소 문제가 아니라 **색상 렌더링 결정**이고, 조명감독 몫이다.
GUI 작업은 필요 없지만 **결정은 필요하다.**

---

## 1. CSV 가 요구하는 것 (콘솔 무관)

    grep -c "Martin MAC Aura XB"  →  24
    Mode 열 분포: Extended 25ch 24 · 9ch 20 · Direct 12ch 14 · Mode 1 49ch 8
                  Mode 1 39ch 8 · 4ch 6 · Extended 14ch 4 · 2ch 2

**Aura XB 24행 = `Extended 25ch` 24행 = mode_unresolved 24건.** 정확히 일치한다.

행 형태(FID 201):

    201,BACK,Martin MAC Aura XB,Extended 25ch,25,4,1,4.001–025,업스테이지 트러스

즉 CSV 가 주는 신호는 **타입 이름 · 모드 문자열 · 폭 25** 셋뿐이다.

---

## 2. 콘솔이 답하는 것 (읽기 전용 실측)

착수 1번은 날조 대조군이었다.

    probe_preflight --listen-port 9005             →  responder_ok / online
    t95_state_dump --path 'DataPool/NoSuchPoolZZZ' →  path segment not found
                                                       (판별력 있음 — 침묵이 아니다)

그 다음 실제 조회:

    Patch/FixtureTypes             childCount 8 · truncated false
                                   슬롯 8 = "Mac Aura XB"
    Patch/FixtureTypes/8/DMXModes  childCount 6 · truncated false

`truncated false` 이고 `childCount` 와 반환 수가 같으므로 **부분집합이 아니다.**

### 2.1 6모드 × TotalFootprint — 6/6 개별 조회

| 슬롯 | 콘솔 이름 | TotalFootprint |
|---|---|---|
| 1 | `Extended - Extended` | **25** |
| 2 | `Extended - RAW` | **25** |
| 3 | `Extended - RGB` | **25** |
| 4 | `Standard - Extended` | 14 |
| 5 | `Standard - RAW` | 14 |
| 6 | `Standard - RGB` | 14 |

**표기 정정**: 실제 이름은 하이픈 **양옆에 공백**이 있다 — `Extended - RGB` 이지
`Extended-RGB` 가 아니다. `--mode-overrides` 리터럴을 쓸 때 걸리는 자리다.

### 2.2 그러므로 폭은 판별기가 아니다

CSV 의 폭 25 는 **Standard 3종만 떨어뜨린다.** Extended 3종이 남고, 셋의 폭이
전부 25 라서 폭으로는 더 좁혀지지 않는다.

도구도 이미 그렇게 답하고 있었다. `mode_unresolved` 행의 `detail` 이 6모드와 폭을
그대로 열거하고, 모드 이름을 지정해 재호출하라고 안내한다. **내 독립 측정과 완전히
일치한다.** 도구는 결함이 아니라 설계대로 동작하고 있다 — 「폭으로도 라벨로도 모드를
확정하지 못한 타입의 행은 만들지 않는다」가 그 계약이다.

---

## 3. 감독 원본에도 판별 정보가 없다

색상 하위모드를 정할 근거가 감독 산출물 어디에도 없다. 빌드 파이프라인의 원자료가
모드 선택 근거를 직접 적는다 — `90_빌드파이프라인/rig_data.py:158`:

> 풋프린트 제조사 DMX 차트 재확인 완료 (Robe 공식 DMX 차트: MegaPointe M1=39ch ·
> Spiider M1=49ch / Martin: **Aura XB Ext=25ch** · Atomic 3000 LED Ext=14ch ·
> RUSH PAR 2=9ch)

**감독은 풋프린트로 골랐지 콘솔 모드 라벨로 고르지 않았다.** 그래서 `Extended`
까지만 있고 그 뒤의 `- Extended` / `- RAW` / `- RGB` 가 없다. 부재는 누락이 아니라
**선택 축이 달랐던 결과**다.

`04_grandMA3/*.ma3.txt` 도 봤다 — Aura 언급 0건이라 거기서도 안 나온다.

---

## 4. 셋 중 무엇을 골라도 패치 결과가 같다 (실측)

24개 FID 로 좁혀 네 번 preview 했다. 전부 `--approve` 없음 — **쓰기 0건.**

| override | 런 | 계획 | 건너뜀 | 사유 |
|---|---|---|---|---|
| (없음) | 0 | **0** | 24 | `mode_unresolved` 24 |
| `Extended - RGB` | 3 | **19** | 5 | `address_occupied` 5 |
| `Extended - RAW` | 3 | **19** | 5 | `address_occupied` 5 |
| `Extended - Extended` | 3 | **19** | 5 | `address_occupied` 5 |

**세 결과가 완전히 동일하다.** 폭이 같으니 주소 계획이 같다.

그러므로 선택은 **주소 문제가 아니라 색상 렌더링 문제**다. 패치를 진행하는 데는
어느 것을 골라도 지장이 없고, 무대에서 색이 어떻게 나오는지만 달라진다.

원자료: `baseline-preview.json` · `override-rgb.json` · `override-raw.json` ·
`override-ext.json` (같은 디렉터리).

### 4.1 권고 — 판정이 아니다

`preset-col.csv` 8건 중 **5건이 RGB 삼중값**(`R255 G180 B60` 형태)이고 3건이
색온도다. FX 스키마도 `ColorRGB_R/G/B` 를 낸다. 색 모델이 맞는 쪽은 `Extended - RGB`
로 **보인다.**

**다만 이것은 권고이고 판정이 아니다.** RAW · Extended 와의 실제 차이를 **안 쟀다** —
세 모드가 무대에서 색을 어떻게 다르게 내는지는 이 조사의 범위 밖이다.

### 4.2 결정 — `Extended - RGB` (리드, 2026-08-30)

리드가 이 조사 결과를 받아 **`Extended - RGB` 를 기본값으로** 정했다. 근거 셋:

    세 후보의 패치 계획이 완전히 동일하다   런 3 · 계획 19 · 건너뜀 5 (§4 실측)
    데이터 모델이 RGB 다                    preset-col 8건 중 5건이 RGB 삼중값 ·
                                            FX 스키마가 ColorRGB_R/G/B 를 낸다
    되돌릴 수 있다                          틀려도 24대 재패치 · 무대 손상 없음

**이것은 판정이 아니라 기본값이다.** 「RAW · Extended 와의 실제 차이는 안 쟀다」는
위 문장이 그대로 살아 있고, 리드도 안 쟀다. 되돌릴 수 있는 선택이라 조명감독의
결정 라운드를 쓰지 않은 것뿐이다.

⚠️ **이 선택이 콘솔에 닿는 것은 `--approve` 가 붙는 순간이고, 그 게이트에서 조명감독이
다시 본다.** 지금 정한 것은 preview 를 하나로 좁히는 범위까지다.

그리고 이 기본값은 **감독이 정한 값을 바꾸는 것이 아니다** — §3 이 잰 대로 감독
원본에는 색상 하위모드가 애초에 없다. 감독은 풋프린트로 골랐고, 그 축에서는
세 후보가 구별되지 않는다.

---

## 5. 🔴 부수 발견 — `address_occupied` 모집단이 7 이 아니라 12 다

Aura 24행이 풀리자 **5건이 새로 `address_occupied` 로 드러났다.** 앞선 사유가
뒤의 사유를 가리고 있었다.

전수 preview 의 기존 분포는 `type_unresolved` 54 · `mode_unresolved` 24 ·
`address_occupied` 7 이었다. Aura 를 풀면 그 24 중 19 가 계획으로, **5 가
`address_occupied` 로 이동**한다. 즉 실제 모집단은 **12** 다.

카드 t129 가 「7행」으로 서 있다 — 고쳐야 한다.

**이 형태는 오늘 세 번째다.** 하나의 거절 사유가 그 뒤의 사유를 가리는 축은
반복해서 나타나고, 첫 사유를 푸는 순간에만 드러난다.

---

## 6. 안 잰 것

- **세 Extended 모드의 실제 색상 거동 차이.** §4.1 의 권고는 시트의 색 표기와
  스키마 출력 형태를 근거로 한 것이지, 무대 결과를 잰 것이 아니다
- **`--approve` 경로 전량.** 이 회차는 preview 뿐이고, 계획 19대가 실제로 패치되는지는
  안 봤다
- **새로 드러난 `address_occupied` 5건의 점유자**가 누구인지. 사유 클래스만 셌고
  점유 FID·타입은 대조하지 않았다 (t129 몫)
- **다른 타입의 mode 모호성.** Aura XB 만 봤다. `Mode 1 49ch` · `Direct 12ch` 같은
  다른 모드 문자열도 같은 함정을 갖는지 안 쟀다
- **`type_unresolved` 54건**은 이 카드 범위 밖이라 손대지 않았다

---

## 7. 측정 조건과 귀속

    origin/main    f871c76
    트리           .claude/worktrees/t128 (WT-mode-mapping, origin/main 기준 신규)
    콘솔           app_gma3 pid 38706 · UDP 8000 송신 / 9005 수신
    콘솔 쓰기      0건 (--approve 미사용, 하네스가 무접촉을 보장)
    응답기         **1.6.1**

### 🔴 귀속의 한계 — 정직하게

응답기 버전은 **측정 4건이 끝난 뒤에** 쟀고 `1.6.1` 이었다
(`responder_roundtrip --expect-version 1.6.2` → FAIL, `state` 는 PASS).

**시작 시점 버전은 안 쟀다.** 따라서 「구간 내내 1.6.1 이었다」고 단정하지 못한다.
근거로 삼을 수 있는 것은 **모든 프로브가 응답했고 재적재로 보이는 침묵 구간이
없었다**는 것까지다.

이 회차 중 감독의 응답기 교체(1.6.1 → 1.6.2)가 예고됐다. 교체 후 같은 측정을
다시 하면 새 파서 기준의 값이 되며, **이 리포트의 수치는 1.6.1 귀속으로 읽어야 한다.**
붙여넣기가 왜 아직 안 먹었는지는 이 카드가 파고들지 않는다 — 별도 카드 몫이다.

---

## 8. 후속 — 응답기 1.6.2 에서 재측정 (귀속 승격)

§7 이 남긴 귀속 한계를 닫는다. 감독의 응답기 교체가 끝난 뒤 **같은 측정을 다시** 했다.

    responder_roundtrip --expect-version 1.6.2  →  PASS · live version=1.6.2
    t95_state_dump 'DataPool/NoSuchPoolZZZ'     →  path segment not found (대조군)
    lxseq_e2e preview --mode-overrides 'Extended - RGB'  (--approve 없음, 쓰기 0건)

| 응답기 | 런 | 건너뜀 | 사유 | 건너뛴 FID |
|---|---|---|---|---|
| 1.6.1 | 3 | 5 | `address_occupied` 5 | 311·312·313·314·315 |
| **1.6.2** | 3 | 5 | `address_occupied` 5 | 311·312·313·314·315 |

구조 비교 결과 `runs` 와 `skipped` 가 **완전히 동일**하다.

**그러므로 §4 의 측정 4건은 응답기 버전과 무관한 값으로 승격된다.** 다만 승격의 범위는
**이 축에 한해서**다 — 두 버전이 다른 축에서도 같은 답을 낸다는 뜻이 아니다.

§7 의 「종료 시점에 1.6.1 · 시작 시점 미측정」 문장은 **그대로 둔다.** 그 문장이
있어야 이 대조가 무엇을 대조한 것인지 읽히기 때문이다.

원자료: `override-rgb-162.json`.

### 8.1 건너뛴 5건의 정체 (t129 에 넘긴다)

FID **311~315** 로 전부 `SIDE-R` 블록이고 유니버스 5다. 점유자가 누구인지는
이 카드에서 안 쟀다.
