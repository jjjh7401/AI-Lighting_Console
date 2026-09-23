# t430 — ColorRGB_W 채널 배선 (색 C1)

- 카드: t430 (클래스 C), 레인 lane-2 · 브랜치 `WT-white-channel`
- 판정: **PASS — 배선 완료, 무대 색 변화 0.** 감독 결정 (c): 값 규칙은 보류하고 배선만 한다. 착수 승인은 감독이 레인 터미널에서 직접 했다.
- **미결: 값 규칙, 실기 육안 대기.** 어느 흰색을 W로 낼지((a)/(b))는 콘솔을 켜는 날, W 흰색과 RGB 흰색을 눈으로 비교한 뒤 정한다.

## 결과 (구현 후)

구현 커밋은 RED `6e90d6bf`와 GREEN `554d8b87`이다(기준 `71db5df3` = origin/main 합류본).

- `_fixture_color_channel_names`: 기존 3단계 판독을 공유 함수로 뽑았다. `_color_capable_fids`의 판정과 반환값은 그대로다(기존 테스트 통과).
- `_w_capable_fids`: 기구를 W 가능 / RGB 전용 / 판별 불가로 나눈다. `ColorRGB_W` 부분 문자열로 판정하며, 판독 실패나 절단이 있으면 판별 불가다.
- `_SongDesignState.w_fids`: 곡 디자인을 만들 때 한 번 계산한다. 열거가 실패하면 빈 집합이 되어 오늘과 동일하게 동작한다.
- `_song_color_value_lines(cue, fids, w_fids)`: 빈 집합이면 오늘과 바이트 동일하다. W 가능 기구만 따로 한 줄로 내고, 그 줄 끝에 `Attribute 'ColorRGB_W' At 0`을 붙인다.

### 전후 대조 (무대 색 변화 0의 증거)

같은 큐, 기구 1~4, W 가능 기구 {2, 4}로 비교했다.

```
Blue
  전(W없음): Fixture 1 + 2 + 3 + 4 ; Attribute 'ColorRGB_R' At 5 ; Attribute 'ColorRGB_G' At 20 ; Attribute 'ColorRGB_B' At 100
  후 RGB줄: Fixture 1 + 3 ; Attribute 'ColorRGB_R' At 5 ; Attribute 'ColorRGB_G' At 20 ; Attribute 'ColorRGB_B' At 100
  후 W줄  : Fixture 2 + 4 ; Attribute 'ColorRGB_R' At 5 ; Attribute 'ColorRGB_G' At 20 ; Attribute 'ColorRGB_B' At 100 ; Attribute 'ColorRGB_W' At 0
Cool White  (R85 G95 B100 — 전후 동일, W줄만 W 0 추가)
Warm White  (R100 G75 B40 — 전후 동일, W줄만 W 0 추가)
세 색 모두: RGB줄 == _color_apply_command([1,3], rgb) → True · W줄 == _color_apply_command([2,4], rgb) + " ; Attribute 'ColorRGB_W' At 0" → True
```

### 검증

```
.venv/bin/python -m pytest -q server/tests/test_song_cue_w_channel_t430.py server/tests/test_song_cue_color_emission.py \
  server/tests/test_web_session.py server/tests/test_write_dispatch_census.py
467 passed, 1 skipped in 6.48s        (레인 재실행)
RED: 17 failed, 2 passed              (구현 에이전트, 구현 전)
```

### 리뷰 메모

- **곡 디자인마다 콘솔 읽기가 늘어난다.** 쓰기는 0이다. 실측된 41대 리그 기준으로 속성 읽기 82회에 조합별 채널 페이지 몇 장이 더해진다(`_color_capable_fids` 독스트링의 예산과 같다). 실기에서 지연을 재지 않았다.
- **값 규칙을 켤 때의 전제**: 지금은 W가 어디서도 0 이외 값을 받지 않으므로 트래킹 누수가 없다. W를 실제로 켜는 날에는 E2~E7(페이저·프리셋 등)도 W를 명시해야 한다. 안 그러면 켜진 W가 다음 색으로 새어 나간다.
- 기존 테스트 두 곳을 이 변경에 맞춰 고쳤다. `test_web_session.py`의 골든 판독 순서에 W 판정용 패치 열거 1회를 추가했고, `test_song_cue_color_emission.py`의 대역 함수에 `w_fids` 인자를 추가했다.
- 구현 에이전트가 RED를 재현하려고 공유 stash를 썼다. 끝난 뒤 `git stash list`는 비어 있다. 다른 세션의 항목을 건드렸는지는 확인할 수 없다.

## 이하 — 계획 초안 (착수 전 기록, 그대로 보존)

- 기준 origin/main `a54db70e`

## 1. 전제 재측정 (기준 `a54db70e`)

| 전제 | 명령 | 결과 |
|---|---|---|
| W를 값으로 내는 생산 코드 0 | `grep -rn "ColorRGB_W" --include='*.py' server \| grep -v "^server/tests"` | `session.py:10332` 주석 1줄뿐 |
| 기구 능력 판독은 W를 구분하지 않음 | `session.py:10315` `_color_capable_fids` 독스트링 | 부분 문자열 `"ColorRGB"` 하나로 capable 판정. W 유무는 판정 결과에 남지 않는다 |
| 색을 내는 자리 | `grep -rn "'ColorRGB_R' At" server`(테스트 제외) | 아래 표 |

색 값을 콘솔 명령으로 만드는 자리(모두 R/G/B 세 채널만 씀):

| # | 자리 | 경로 |
|---|---|---|
| E1 | `session.py:1337` `_song_color_value_lines` → `:4237` `_color_apply_command` | 감독 확정 곡 큐(M2) |
| E2 | `session.py:7206` `_color_apply_command` | 컬러 프리셋 번들 |
| E3 | `session.py:4280`, `:4408` | 컬러 페이저 스텝 |
| E4 | `server/presets/store.py:113` | 프리셋 저장 |
| E5 | `server/design/override_look.py:215` | 오버라이드 룩 |
| E6 | `server/design/cue_sheet_apply.py:434` | 큐시트 적용 |
| E7 | `server/looks/schema.py:41`, `server/fx/schema.py:49` | 룩 라이브러리·FX 밴드 채널 목록(R/G/B만 허용) |

## 2. 제안 범위

**E1(감독 확정 곡 큐)만 1단계로 한다.** 카드가 착수점으로 지정한 자리이자, 컨셉 색이 무대로 나가는 경로다. E2~E7은 이 카드에서 건드리지 않는다. **후속 후보로만 기록한다. 리드 지시에 따라 카드는 만들지 않았다.**

1. **능력 판독 확장**: `_color_capable_fids`와 같은 3단계 판독 결과에서 W 채널(`ColorRGB_W`) 유무를 기구별로 따로 돌려준다(W 가능 / RGB 전용 / 판별 불가). 기존 반환값과 호출자 동작은 바꾸지 않는다.
2. **E1 분기**: W 가능 기구와 RGB 전용 기구를 `Fixture` 줄 두 개로 나눈다. RGB 전용 기구에는 지금과 바이트 동일한 줄을 낸다(카드 조건 「W 없는 기구는 RGB로」).
3. **트래킹 누수 방지**: W 가능 기구의 색 줄에는 **항상 W 값을 명시**한다. 흰색이 아니면 `W At 0`이다. 이유: 콘솔은 값을 다음 큐로 이어간다(트래킹). 흰색 큐에서 W를 100으로 켠 뒤 다음 파랑 큐가 R/G/B만 적으면 W 100이 남아 파랑이 허옇게 뜬다.
4. **판별 불가 기구**: W를 켜지 않고 RGB만 낸다(모르는 채널을 켜지 않는다). 그 사실은 회신에 사유로 남긴다.
5. **콘솔 쓰기 0**: 가짜 포트 위의 명령 문자열만 시험한다.

## 3. 🔴 리드 결정이 필요한 것 — 어떤 색을 W로 낼지

t409 경계 때문에 레인은 이 규칙을 정하지 않는다. 판단에 쓸 사실만 적는다.

- 표준 팔레트의 흰색 계열은 이름 두 개다: `Warm White`(100,75,40), `Cool White`(85,95,100).
- 맨 `화이트`/`흰색`/`하양`은 지금도 해석 불가다(t409, `color_names.py:78~88`). 이 카드는 이 상태를 바꾸지 않는다.
- W 칩의 색온도는 **재지 않았다**. 문서 주석은 LEDBeam350에 W 채널이 있다는 것까지만 적었다. 칩의 색온도가 웜인지 쿨인지 모르면 어느 흰색에 W를 쓸지가 곧 무대 색 결정이다.

갈림(값 계산 방식):

| 안 | W 가능 기구에 내는 값 | 대가 |
|---|---|---|
| (a) W 대체 | Cool White만 `R0 G0 B0 W100` | 가장 단순하다. Warm White는 RGB 그대로 두고, 섞인 리그에서 두 흰색이 달라 보일 수 있다 |
| (b) 최소값 분리 | `W = min(r,g,b)`, RGB는 거기서 뺀다. 두 흰색 모두(예: Cool White → R0 G10 B15 W85) | 표준적인 RGB→RGBW 변환이다. W 칩 색온도를 모르면 결과 색이 틀린다 |
| (c) 보류 | 이 카드는 판독·분기·트래킹 방지(§2의 1·3·4)만 한다. 모든 색은 `W At 0`, 규칙은 실기 측정 뒤로 | 무대 색 변화 0이다. W가 여전히 안 켜져 카드 목표는 절반만 이룬다 |

레인 선호는 없다. (a)/(b)는 무대에 보이는 흰색을 바꾸는 결정이라, 감독 소관인지 리드가 판단할 일이다.

## 4. 안 잰 것

- W 칩의 색온도, RGB 혼합 흰색과 W 흰색의 밝기 차이(콘솔 측정 0회)
- E1의 `fids`가 컬러 가능 기구 전체인지 일부인지(`session.py:8221` 호출자의 출처 미확인)
- 실제 리그에서 W 가능 기구의 수(판독은 콘솔 접촉이 필요하다)
