# t229 — COL 켈빈 계열 (완료) · BM 계열 (미착수)

- 카드 t229 · 브랜치 `WT-kelvin-beam` · PR **#279** → main **`09bd3a7`**
- base `24f11e5` · 커밋 `1a21aaa`(변환) + `9bddc93`(PRESERVE 재고 목록)
- **콘솔 쓰기 0건.** 이 회차는 읽기만 했다.

## 1. 주장

COL.02(`~3200K`)·COL.03(`~5600K`)을 열었다. 정본 §10 이 「COL은 RGB/CCT 필수」라
켈빈 단독은 규격이 인정한 형태이고, 시트가 아니라 파서가 못 받고 있었다.
BM 계열은 **미착수** — 적용 경로 설계가 선행이다.

## 2. 증거

### 2.1 카드 정정 3건 (실측)

```
preset-col 8행 · storable 6 → 8
  HOLD COL.02 no_rgb_value      ← 카드는 COL.02 만 적었다
  HOLD COL.03 no_rgb_value      ← 같은 결함, 카드 누락
preset-bm  5행 · storable 0
  BM.01 probe_rejected + family_out_of_scope   ← 「사유 둘」은 여기다
  BM.02 family_out_of_scope
  BM.03 probe_rejected                          ← 하나뿐
  BM.04 probe_rejected
  BM.05 family_out_of_scope                     ← 카드는 BM.01~04 만 적었다
```
🔴 **t225 표가 「사유 둘」을 BM.03 에 붙였는데 실제로는 BM.01 이다.** 카드가 그
오류를 물려받았다. 「8큐 중 몇 행」 산수를 t225 표에서 그대로 인용하지 마라.

### 2.2 지뢰 재현 — 읽은 것이 아니라 돌려본 것

```
[대조군] 현재      planned 6 · refusal None · 발화 24 (적용 6 · 저장 6)
[재현] 판정기만 열면 planned 8 · refusal apply_untranslatable
                    untranslatable [COL.02, COL.03] · 발화 0
```
**2행을 얻으려다 8행을 다 잃는다.** 카드는 이 지뢰를 bm 전용으로 적었으나 COL 이
더 위험했다 — bm 은 지금 0행이라 잃을 것이 없고, col 은 6행이 나가는 중이다.

### 2.3 계수 검산 (독립 앵커)

```
Illuminant A 2856K   dx 0.0005 dy 0.0001   플랑크 복사체 — 맞아야 하는 자리
D65 6504K            dy 0.0054             주광 궤적 — 어긋나야 하는 자리
D50 5003K            dy 0.0070             〃
D65 백색점 → 행렬    (255,255,255)         규격의 정의를 재현
B/R 단조성 2000-10000K                     역전 0
```
출처: Kim et al. (2002) J. Korean Phys. Soc. 41(6) · IEC 61966-2-1.
**맞아야 할 자리에서 맞고 어긋나야 할 자리에서 어긋나는 대비**가 근거다.

### 2.4 근사 규모 (천연 대조군)

COL.01 은 시트에서 RGB·켈빈을 **둘 다** 싣는 유일한 행이다.
저자값 `R255 G180 B60` vs 변환값 `R255 G160 B66` — **G 가 20/255 어긋난다.**
그래서 RGB 가 있으면 저자값이 이긴다(`_col_components` 순서, 검사로 고정).

### 2.5 검증

```
신규 검사 17건 · 뮤테이션 6/6 잡힘 (앵커 매치 건수 전부 1건 확인 · 원본 복원)
uv run pytest server/tests/  → 10837 passed, 12 skipped
CI run 33513708922 · headSha 9bddc93 = PR headRefOid · conclusion success
ruff check server/            → 통과
```
`moai gate` 는 근거로 쓰지 않았다(t226 확정).

## 3. 콘솔 판독 — 같은 `0` 이 반대로 갈렸다

```
DataPool/PresetPools/5 (Beam)   childCount 0 · 수신 0
  대조: PresetPools/1 (Dimmer) 7/7 · PresetPools/4 (Color) 7/7
  판정: 계기 안 멀었다 → Beam 0 은 진짜 부재 ✅

Patch/FixtureTypes/8/AttributeDefinitions/Attributes   childCount 0 · 수신 0
  대조: FeatureGroups 0 · ActivationGroups 0 · DeactivationGroups 0 (형제 전부 0)
  판정: 🔴 이 깊이에서 계기가 눈멀었다 → 부재의 증거가 아니다
```
**결과: 「콘솔에 CCT 속성이 있는가」는 이 채널로 답이 안 나온다.** 선택지 (b)
(콘솔 CCT 속성 직접 전송)는 기각이 아니라 **열어둔 선택지**다 — RGB 근사가 무대에서
안 맞으면 다시 온다. 판정하려면 콘솔 쓰기 프로브가 선행이다.

모든 판독은 `childCount` 와 **수신 길이를 나란히** 찍었다(14/14 · 7/7 · 0/0 · 7/7
· 15/15). 잘림 없음.

## 4. Color 풀 드리프트 — 리드 보고를 정정했다

t225 6종 → 현재 **7종**(슬롯 `1,2,3,4,5,6,32`, 32는 무명 `Preset 32`).
🔴 원인은 **미확정**이고, 「출처 미상의 새 프리셋」보다 **계기 잘림**이 더 그럴듯하다:
잘림은 **끝에서** 떨어지므로 6개를 받으면 정확히 `1~6` 이 되고 `32` 만 빠진다 —
t225 가 본 것과 일치한다. 리드가 감독 보고를 이 문면으로 정정했다.
**콘솔은 안 건드렸다. 슬롯 32 를 지우지 마라.**

## 5. 안 잰 것 (Gaps)

- 🔴 **콘솔 쓰기 0건.** 변환된 색이 **무대에서 눈으로 맞는지는 아무도 안 쟀다** —
  근사라는 사실 자체가 미검증 항목이다.
- **BM 계열 미착수.** 진단만 했다.
- 콘솔 CCT 속성 유무 — 계기가 그 깊이에서 눈멀어 못 쟀다(§3).
- Color 풀 슬롯 32 의 출처 — 미확정(§4).

## 6. BM 계열 — 다음 회차 재료 (설계가 선행이다)

### 6.1 무엇이 막는가 (행별 실측)

`Zoom` 은 **수용 어휘**다 — `PROBE_GATED_ATTRIBUTES == ("Zoom", "Iris")`.
막는 것은 같은 행에 함께 있는 다른 토큰이다.

| 행 | 값 | 막는 것 |
|---|---|---|
| BM.01 | `Zoom 45° · Gobo OPEN · Prism OFF` | Gobo(범위 밖) + Prism(거절) — **사유 둘** |
| BM.02 | `Zoom 20° · Gobo OPEN` | Gobo |
| BM.03 | `Zoom 8° · Prism 3-facet ON` | Prism |
| BM.04 | `Frost 30%` | Frost |
| BM.05 | `Gobo 슬롯2(브레이크업) · Zoom 25°` | Gobo |

- `_PROBE_REJECTED` = ("Focus","Frost","Prism","Shutter") — 라이브 프로브가 거절
- `_OUT_OF_SCOPE` = ("Gobo","Position","Control","Shapers","Video") — 풀 계열이 범위 밖
- 출처 등급이 갈린다: `Focus1`·`Frost1`·`Shutter1` 은 t135 가 **읽은** 이름,
  `Prism1` 은 **쏴서 `Failed` 를 받은** 이름, `Shutter1` 은 쏜 적 없음

### 6.2 🔴 「칸 하나 채우기」가 아니다

`LXSEQ_PRESET_APPLY_ATTRIBUTE = dict([("preset-dim", "Dimmer")])` 는
**한 종류 → 한 속성** 표이고, 소비 지점은 `Attribute <name> At <level>` **한 줄**을
만든다. 그런데 bm 값은 **복합·다속성·단위 혼재**다: `45°` · `3-facet ON` ·
`슬롯2` 는 dim 의 퍼센트 한 값과 형태가 다르다. 표 항목 하나로 안 들어간다.

### 6.3 지뢰는 그대로 살아 있다

bm 한 행이 저절로 storable 로 열리는 날 적용 줄이 없어 그 bm 임포트가 **통째로
0건**이 된다. col 에서 실측으로 재현한 그 형태다(§2.2). **칸(적용 경로)부터
설계하고 나서 행을 열어라.**

### 6.4 COL 이 남긴 패턴 — 그대로 쓸 것

`_col_components()` 단일 술어. 판정기와 판독기가 **같은 함수**를 쓰면 갈라질 수
없다. bm 도 같은 모양이어야 한다 — 「한 커밋에 넣는다」보다 **구조로 막는 것**이 강하다.

## 7. 계기 관측

- 🔴 **PRESERVE hunk 가드는 커밋된 상태를 잰다.** `BASE..HEAD` 를 diff 하므로 작업
  트리가 아니라 HEAD 를 본다. **커밋 전 「로컬 전체 초록」은 이 검사에 대해 아무
  뜻이 없다** — 커밋 후에야 빨개진다. 이번에 CI 에서 처음 걸렸다.
- `--unified=0` 은 삽입 지점에서 기존 hunk 를 쪼갠다. tools.py 에 25+/4− 만 더했는데
  hunk 시작점이 48 → 65 로 바뀌었다. **hunk 수를 변경 크기로 읽지 마라.**
- `gh pr checks` 가 push 직후 `no checks reported` 를 답한다. `gh run list --json
  headSha` 로 **새 헤드의 run 인지 대조**하고 그 run id 를 직접 지켜봐야 한다.
