# t432 선행 측정 — 우리 리그 기구의 원색 CIE x·y 를 콘솔 없이 읽을 수 있는가 (lane-1)

- 브랜치 `WT-color-xy-probe` · 기준 `origin/main@b782cf36`
- 리드 범위: 카드 t432의 **선행 측정만**. 코드 변경 없음. **콘솔 접속 금지**(lane-2 t474 사용 중)
- 도구: `.moai/reports/t432/gdtf_emitters.py`(GDTF `description.xml`의 색 태그를 원문 그대로 뽑는다. 해석하지 않음)

## 0. 판정

🔴 **콘솔 없이는 못 읽는다. 패치에 쓰는 8종 중 0종.** 저장소 안에 우리 기구의 좌표 자료가 없다. 다음 단계는 **콘솔 판독(읽기 전용)**이다. 콘솔 기구 타입마다 `PhysicalDescriptions` 노드가 있다는 것까지는 이미 캡처돼 있고, 그 안은 한 번도 열어 보지 않았다.

| 질문 | 답 | 근거 |
|---|---|---|
| GDTF 형식이 원색 x·y를 싣는가 | **싣는다** (양성 대조) | MAC Encore Performance CLD: `<Emitter Name="White" Color="0.324999,0.335004,100.004386">`, `<Filter Name="Cyan" Color="0.139005,0.135500,12.210178">` 외 3 — `run1_demo_mvr_gdtf.txt` |
| 저장소에 우리 기종의 GDTF가 있는가 | 8종 중 **2종**(Mac Aura XB, Rush Par 2 RGBW Zoom). 데모 MVR 안에 들어 있다 | `src/Demoshow_grandMA3.mvr`(= `server/tests/fixtures/vwx/demoshow_grandma3.mvr`, 같은 크기 315155) |
| 그 2종에서 x·y가 읽히는가 | **안 읽힌다.** `Emitter` 0 · `Filter` 0 · `Measurement` 0. `<ColorSpace Mode="sRGB"/>` 한 줄뿐이다 | `run1_demo_mvr_gdtf.txt` |
| 나머지 6종 | 저장소·로컬 어디에도 GDTF나 기구 라이브러리 파일이 없다 | §2 |

`ColorSpace Mode="sRGB"`는 좌표로 쓰지 않는다. 기구를 재서 얻은 원색이 아니라 "이 기구의 RGB는 sRGB로 친다"는 선언이다. 다섯 GDTF(데모 백드롭 LED 타일·계단 포함)가 전부 똑같이 이 한 줄만 달고 있다. 이걸 원색으로 쓰면 "기종마다 빨강이 다르다"는 이 카드의 전제 자체가 사라진다.

## 1. 우리 리그 (패치 86대, t442 실기 캡처 재집계)

`run4_fixture_types.txt`(t442)의 `FIXTURETYPE` 값을 이번에 다시 셌다(86 = 합계 일치).

| 타입 | 이름 | 대수 | 색 방식(t442 `run7_dmx_channels.txt` 채널 이름) | 저장소 GDTF |
|---|---|---|---|---|
| 8 | Mac Aura XB | 24 | RGB (`Aura_ColorRGB_R/G/B`) | 있음 — 좌표 없음 |
| 9 | Rush Par 2 RGBW Zoom | 20 | RGBW | 있음 — 좌표 없음 |
| 10 | Source 4 LED Series 3 Lustr X8 | 14 | 8색 LED (`DEEPRED·R·RY·GY·G·C·B·BM`) | 없음 |
| 4 | Robin Spiider | 8 | RGBW, 모듈 둘 | 없음 |
| 11 | Robin MegaPointe | 8 | 방전등 + 필터·휠(t442: 일부 채널 판독 실패) | 없음 |
| 13 | CuePix Blinder WW2 | 6 | 확인 안 함 | 없음 |
| 14 | Atomic 3000 LED | 4 | 확인 안 함 | 없음 |
| 15 | Unique 2 1 | 2 | 확인 안 함 | 없음 |

C3 설계에 걸리는 점:
- **Lustr X8**은 원색이 8개라 삼각형이 아니라 팔각형 색역이다. "원색 셋"이라는 틀로는 이 기구를 담을 수 없다
- **MegaPointe**는 원색 이미터가 없다. 색역을 정하는 건 흰 광원(Emitter) + CMY·휠 필터(Filter)다. Encore CLD GDTF가 바로 그 모양(`Emitter White` 1 + `Filter` 4)이라, 같은 방식의 자료가 있으면 읽을 수는 있다. 다만 x·y로 조합하는 방법은 RGB 기구와 다르다

## 2. 찾아본 곳

| 어디 | 명령 | 결과 |
|---|---|---|
| 저장소 전체 GDTF·MVR | `find . -iname '*.gdtf' -o -iname '*.mvr' …` (.venv·node_modules 제외) | MVR 2개(같은 파일), 별도 `.gdtf` 0개 |
| MVR 안 | `unzip -l src/Demoshow_grandMA3.mvr` | GDTF 5개: MAC Encore Performance CLD · Mac Aura XB · Rush Par 2 RGBW Zoom · Led Tile RGB8 Wall · LED steps small |
| 저장소 코드·문서의 색도 자료 | `grep -rIn "xyY\|cie ?1931\|chromaticit\|Emitters"` (server·docs·specs) | `server/lxseq/preset_parser.py`의 색온도→xy(플랑크 궤적), xy→sRGB(IEC 61966-2-1) 변환뿐. **기구별 원색 표는 없다** |
| Spiider·MegaPointe 자료 | `grep -rIl "spiider\|megapointe"` (reports 제외) | SPEC·CHANGELOG의 언급뿐. 기구 데이터 파일은 없다 |
| 로컬 디스크 GDTF | `mdfind -name .gdtf` | OneDrive에 3개(Ayrton MagicPanel FX, Astera Titan, Generic gsgs_test). **우리 기종이 아니다.** 게다가 클라우드 전용 파일이라 읽기가 실패했다(`head: Error reading`, zip 판독 `BadZipFile`). 내려받지 않았다 — `run2_local_led_gdtf.txt` |

### 판독 주의(도구 검증)

다섯 GDTF 전부 `ElementTree`가 `not well-formed`로 거부했다. 원인을 확인해 보니 `</GDTF>` 뒤에 붙은 NUL 바이트 한 개였다(Aura XB: 813번째 줄이 `b'\x00'`, 812번째 줄 끝이 `</GDTF>`). 문서는 끝까지 온전하다. 그래서 정규식으로 태그를 셌고, 같은 방식이 Encore CLD에서 `Emitter` 1·`Filter` 4를 잡아낸다. 0이 계기 탓이 아니라는 뜻이다(양성 대조).

## 3. 콘솔 판독이 필요한가: 필요하다. 읽기 전용 경로

- 이미 아는 것: `state:Patch/FixtureTypes/<n>`의 자식 3번이 `PhysicalDescriptions`다. 타입 8·9·10에서 캡처했다(`.moai/reports/t451/live_type_children.txt`)
- 모르는 것: 그 아래에 `Emitters`·`Filters`·`ColorSpace`가 있는지, 있다면 x·y 값이 채워져 있는지. MA3 기구 라이브러리 항목(GDTF에서 온 게 아닐 수도 있다)이 좌표를 싣는지는 이 저장소 어디에도 기록이 없다
- 제안 프로브(t474 끝난 뒤, 읽기만, 기종 8개):
  1. `state Patch/FixtureTypes/<n>/PhysicalDescriptions` → 자식 이름 목록
  2. 자식 중 `Emitters`/`Filters`/`ColorSpace`가 있으면 → `state …/Emitters`로 자식 목록 → 각 자식 `props …|NAME,COLOR,DOMINANTWAVELENGTH`(속성 이름은 판독 1로 확인한 뒤 확정. 지어낸 이름으로 쏘지 않는다)
  3. 양성 대조: 같은 쇼파일에 MAC Encore CLD 타입이 있으면 그것부터(데모 GDTF에 좌표가 있다고 아는 기종). 없으면 "값 없음"과 "읽는 방법 모름"을 가를 수 없다는 점을 판정에 적는다
- 콘솔에도 없으면 남는 길: 제조사 GDTF(GDTF-Share)를 받는다 — 받은 파일이 원색을 재서 실었는지는 파일마다 다르다(이번 5개 중 1개만 실었다). 그래도 없으면 C3은 **불가**(카드 문면 「못 읽으면 불가」)

## 4. 안 잰 것 (Gaps)

- 콘솔 `PhysicalDescriptions` 내부. 이 카드의 결론을 뒤집을 수 있는 유일한 자리다
- 데모 MVR 속 Aura XB·Rush Par GDTF가 콘솔에 들어 있는 같은 이름 타입과 **같은 개정판**인지(콘솔 타입의 `Revisions` 미판독). 콘솔 쪽 타입에는 좌표가 있을 수도 있다
- GDTF-Share 등 외부 자료(웹·계정 필요, 이번 범위 밖)
- CuePix Blinder WW2·Atomic 3000 LED·Unique 2 1의 색 방식(채널 미판독)
- OneDrive GDTF 3개의 내용(클라우드 전용이라 읽지 못함. 우리 기종도 아님)

## 5. 파일

- `gdtf_emitters.py`: 판독 스크립트(`uv run python .moai/reports/t432/gdtf_emitters.py <gdtf|mvr> …`)
- `run1_demo_mvr_gdtf.txt`: 데모 MVR GDTF 5개 판독
- `run2_local_led_gdtf.txt`: 로컬 OneDrive GDTF 판독 실패 기록

---

# 2단계 — 콘솔 판독 (2026-09-28, lane-1)

- 브랜치 `WT-color-xy-console` · 기준 `origin/main@b1ded510` · 콘솔 = t474 종료 뒤(리드 배차)
- 도구: `tools/console_probe.py`(state), `.moai/reports/t431/probe_t431.py`(state·introspect·props). **exec 0회, 콘솔 쓰기 0** — 모든 파일에서 `exec` 0건(`grep -c exec`), 응답 누락 0(`not_ok_or_timeout=0`)
- 판정: 🔴 **콘솔에서도 원색 좌표를 못 읽는다(현 응답기 1.6.5).** 좌표 칸은 구조상 존재하지만 응답기가 그 형(Custom)을 읽지 못한다. 좌표가 없어서가 아니라 **계기 한계**다(§2.2 대조군). 기종별 좌표 표는 만들 수 없다

## 2.1 콘솔에 있는 것 (state 열거 — 구조는 확실히 읽힘)

`Patch/FixtureTypes/<n>/PhysicalDescriptions`의 자식은 모든 타입에서 6개로 같다: `Emitters · CRIs · FTFilters · PhysicalProperties · ColorSpaceCollect · GamutCollect` (`c1_control_and_pd.txt`)

| 타입 | 이름 | 대수 | 이미터(콘솔 이름) | FTFilters | ColorSpace / Gamut / CRIs | 색 휠 |
|---|---|---|---|---|---|---|
| 8 | Mac Aura XB | 24 | R · G · B · White | 0 | 0 / 0 / 0 | — |
| 9 | Rush Par 2 RGBW Zoom | 20 | R · G · B · White | 0 | 0 / 0 / 0 | — |
| 10 | Source 4 LED S3 Lustr X8 | 14 | R · G · B · Amber · Lime · Cyan · Indigo (7) | 0 | 0 / 0 / 0 | — |
| 4 | Robin Spiider | 8 | R · G · B · White | 0 | 0 / 0 / 0 | 휠 `E` 1개 |
| 11 | Robin MegaPointe | 8 | R · G · B | 0 | 0 / 0 / 0 | `C1` 슬롯 14(dark red … congo blue) 외 휠 6 |
| 13 | CuePix Blinder WW2 | 6 | 없음 | 0 | 0 / 0 / 0 | — |
| 14 | Atomic 3000 LED | 4 | R · G · B | 0 | 0 / 0 / 0 | — |
| 15 | Unique 2 1 | 2 | 없음 | 0 | 0 / 0 / 0 | — |

근거 `c6_all_types.txt`(요청 120·응답 120), 요약 `c6_summary.txt`(`c6_summarize.py`)

- **필터·색공간·색역 자료는 8종 모두 0개다.** 이건 열거 결과라 "못 읽음"이 아니라 "없음"이다(state 가 `childCount 0` 을 돌려줌)
- Lustr X8은 콘솔상 이미터가 **7개**다. 채널은 8개(`DEEPRED·R·RY·GY·G·C·B·BM`, t442)라서 이름과 개수가 채널과 1:1로 맞지 않는다

## 2.2 좌표 칸은 있는데 읽히지 않는다 — 계기 한계 대조

- 이미터 객체의 필드 19개 전수(`introspect`, `total 19`, `c3`·`c5`): `COLOR`(형 **Custom**) · `INTENSITY`(Float) · `DOMINANTWAVELENGTH`(Float) · `DIODEPART`(String) 외 공통 필드. GDTF의 `Emitter@Color`(x,y,Y)가 들어갈 자리는 `COLOR` 하나다
- `COLOR` → `property not readable: COLOR`. 26개 이미터 전부 같다. 이름 변형(`Color`·`color`·`COLORX`·`CIEX`·`XYY` 등 11개)도 전부 거부(`c5`)
- **대조군**: 같은 객체의 `GUID`(형 Custom, 모든 객체가 반드시 값을 가진다)도 `property not readable: GUID`다(`c8`). 값이 확실히 있는 Custom 필드도 못 읽는다는 뜻이다. 따라서 `COLOR` 거부는 "비어 있음"의 증거가 아니다. 응답기 `safe_property`는 `handle:Get(name)`과 `handle[name]`만 시도하고, 둘 다 nil이면 이 문면을 낸다(`console/lua/copilot_responder.lua` 461~469행)
- 같은 Custom 형이라도 `TAGS`는 `""`로 읽혔다(`c8`). Custom 전체가 막힌 게 아니라 **필드마다 다르다** — `COLOR`·`GUID`·`FILTER`·`APPEARANCE`가 막혔다

## 2.3 읽힌 값은 전부 기본값이다 (추론 — 좌표 측정 여부를 말해 주지 않음)

- 26개 이미터 전부 `INTENSITY=1.0` · `DOMINANTWAVELENGTH=0.0` · `DIODEPART=''`(`c6_summary.txt`). 기종이 달라도 값이 하나도 다르지 않다
- MegaPointe는 방전등(흰 광원 + CMY·휠)인데 콘솔에는 **R·G·B 이미터 3개**로 들어 있고 필터는 0개다. 물리적으로 맞지 않는 모양이다
- 이 두 가지는 "콘솔 기구 라이브러리가 색혼합용 기본 틀만 넣고 측정값은 넣지 않았다"와 들어맞는다. 그러나 `COLOR`를 못 읽으므로 **확정이 아니다** — 이 줄은 추론이다

## 2.4 휠 슬롯 색 (MegaPointe `C1`)

- 슬롯 필드에도 `COLOR`(Custom, 못 읽음)와 `FILTER`(Handle, 못 읽음 — FTFilters 가 0개라 연결 대상이 없다)가 있다(`c7`·`c9`)
- 읽히는 건 화면 표시용 견본색 `IMAGERGBA`뿐: dark red `6A0000FF` · congo blue `300050FF` · CTO 2700K `DE4400FF`. **UI 아이콘 색이지 측정 색도가 아니다.** 좌표로 쓰지 않는다

## 2.5 기종별 조합 방식 차이 (콘솔 구조로 확인한 것)

| 방식 | 기종 | C3에서 필요한 것 |
|---|---|---|
| RGB 3원색 | Aura XB 의 RGB 부분, Atomic | 이미터 3개 x·y → 삼각형 |
| RGBW | Rush Par 2, Spiider, Aura XB(White 포함) | 4개 x·y — 같은 색을 내는 조합이 여럿이라 선택 규칙 필요(t442: 흰색은 RGB+W 동시 켜기가 이김) |
| 7색 LED | Lustr X8 | 7개 x·y → 다각형. 채널 8개와 이미터 7개의 대응부터 확인해야 함 |
| 흰 광원 + 휠·CMY | MegaPointe | 이미터가 아니라 필터 x·y가 필요한데 콘솔엔 필터 0개, 이미터는 RGB 틀 |
| 색 없음 | CuePix Blinder WW2, Unique 2 1 | 이미터 0 — 색 축 대상 아님 |

## 2.6 결론과 남은 길

- 콘솔 판독(현 응답기)으로도 기종별 원색 x·y 표는 만들 수 없다. 카드 문면 「못 읽으면 불가」 기준으로는 **지금 C3 불가**
- 좌표를 얻을 수 있는 길(모두 이 카드 범위 밖이라 리드·감독 결정):
  1. **응답기 읽기 확장**: Custom 필드를 문자열로 읽는 경로(`Get`의 표시용 인자 등). 응답기 배포 = 콘솔 쪽 변경이라 감독 결정. 읽혀도 값이 채워져 있는지는 그때 판정(§2.3 추론이 맞으면 빈 값)
  2. **기구 타입 내보내기**: 콘솔에서 타입 4·11 등을 XML/GDTF로 내보내 파일로 읽기 — `exec` 한 번(쇼 변경은 없지만 콘솔 명령). 이번엔 쓰지 않았다
  3. **제조사 GDTF**(Robe·ETC·Martin): 받은 파일에 측정값이 실렸는지는 파일마다 다르다(1단계: 데모 5개 중 1개만 실음)
- 1·2로 읽어도 빈 값이면 3뿐이고, 3도 없으면 C3는 기구 독립 좌표 대신 기종별 RGBW 값 표(t453 방향)로 가야 한다

## 2.7 안 잰 것 (Gaps)

- `COLOR` 필드의 실제 내용 — 계기가 못 읽는다(§2.2). 비었는지 차 있는지 모른다
- `PhysicalProperties` 자식(열거 안 함, 색도와 무관한 것으로 보고 건너뜀)
- MegaPointe 외 다른 휠(`AnimationWheel`·`G1`·`G2`·`E*`)과 Spiider 휠 `E`의 슬롯
- 기구 타입 개정판(`Revisions`) — 라이브러리 출처·버전 미확인
- 내보내기(§2.6-2) — exec 라서 하지 않았다

## 2.8 파일

`c1_control_and_pd.txt` · `c2_emitters_first.txt` · `c3_emitter_introspect.txt` · `c4_spiider_emitters.txt` · `c5_color_variants.txt` · `c6_all_types.py`/`.txt` · `c6_summarize.py`/`c6_summary.txt` · `c7_megapointe_wheel.txt` · `c8_slot_and_custom_control.txt` · `c9_slot_filter.txt`
