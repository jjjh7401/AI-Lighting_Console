# t450 — 콘솔에서 불이 안 켜진다: 읽기 전용 진단

- 카드: t450 (t442 블로커), 레인 lane-1 · 브랜치 `WT-console-output-diag` · 기준 origin/main `eba7ce65`
- 판정: **원인은 401 도 Rush Par 도 아니다. 이 쇼의 onPC 3D 창에서는 어떤 기구도 빛을 낸 적이 없다**(감독 답). 앱이 읽을 수 있는 쪽에서 이상값 두 개를 찾았다. **DMX 네트워크 출력이 꺼져 있고**(Art-Net·sACN `OUT=false`), **출력 줄이 유니버스 1 한 개만 덮는다**(401 은 유니버스 5). 3D 창이 빔을 안 그리는 직접 원인은 앱이 읽지 못하는 곳에 있다. 후보는 3D 창 렌더링 설정의 `Beam` 페이더(공식 문서) 또는 GPU 드라이버다. **어느 쪽인지는 재지 않았다.**
- 콘솔 쓰기 0 · exec 0 · 설정 변경 0 · 코드 수정 0. 보낸 요청은 `ping`·`state`·`props`·`introspect` 뿐이다.
- 응답기 `1.6.5` (`ping`), 날조 대조군 `state:ShowData/NoSuchT450` → `ok:false path segment not found` (`run1_output_roots.txt`)

## 1. 점검 순서 — 코드로 옮길 수 있는 형태 (t451 코파일럿 기능용)

항목마다 ① 읽는 경로·전역, ② 응답기 동사, ③ 정상/이상 판정 기준, ④ 이번 실측값을 적는다. 경로는 모두 응답기 1.6.5 의 `resolve_path` 기준이다(첫 마디 `Root`·`ShowData`·`Patch`·`Selection`·`Programmer` 는 전역 별칭, 나머지는 이름 또는 풀 번호).

| # | 점검 | ① 경로 | ② 동사 | ③ 판정 | ④ 이번 실측 |
|---|---|---|---|---|---|
| 0 | 계기 생존 | (없는 경로) `ShowData/<날조>` · `ping` | `state` · `ping` | 날조 경로는 반드시 `ok:false`, `ping` 에 `version` 이 온다. 아니면 이후 판독을 믿지 않는다 | `ok:false` · `1.6.5` |
| 1 | 기구 존재·주소 | `Patch/Stages/1/Fixtures/<slot>` (slot 은 `state` 페이징으로 찾음) | `props FID,NAME,PATCH,FIXTURETYPE,MODE` | `FID` 가 묻는 번호와 같고 `PATCH` 가 `<유니버스>.<주소>` 형식이다. 없으면 「패치에 없음」 | 401 → slot 67, `PATCH 5.151`, `FixtureType 9`, `2 9 channel` (`run7_lines.txt`) |
| 2 | 기구 채널 | `Patch/FixtureTypes/<N>/DMXModes/<m>/DMXChannels` | `state` (+`offset`) | Dimmer 채널이 있고, Shutter 가 있으면 켜짐 조건에 셔터 open 도 필요하다 | Rush Par 모드2: `Dimmer, Shutter1, R, G, B, W, COLORMIXER, Zoom` (t442 `run7`) |
| 3 | 셔터 open 범위 | `…/DMXChannels/<Shutter 칸>/1/1/<ChannelSet>` | `props NAME,DMXFROM,DMXTO` | 24비트 값 ÷ 65793 = DMX. open 범위를 벗어나면 이상 | closed 0~7 · open 8~15 · 16부터 strobe (t442 `diag3`) |
| 4 | 그랜드 마스터 | `ShowData/Masters/2/1` (Grand/Master) | `props NORMEDVALUE` | `0` 이면 이상(모든 출력 암전) | `100` (t442 `diag7`) |
| 5 | 월드 마스터 | `ShowData/Masters/2/2` (Grand/World) | `props NORMEDVALUE` | `0` 이면 이상 | `100` (t442 `diag7`) |
| 6 | 기구의 마스터 반응 | `Patch/Stages/1/Fixtures/<slot>` | `props MASTERREACT` | 정보용(어느 마스터에 묶였나) | `Grand` (`run9`) |
| 7 | 3D 표시 여부 | `Patch/Stages/1/Fixtures/<slot>` | `props VISIBLE3D,POSX,POSY,POSZ` | `VISIBLE3D=false` 면 이상 | `true`, `(-5.0, 5.2, 0.3)` (`run9`) |
| 8 | 🔴 **DMX 네트워크 출력 켜짐** | `Root/DeviceConfigurations/DMXProtocols/1` (ArtNet) · `…/2` (sACN) | `props OUT,IN,INTERFACE` | 실제 조명기·외부 시각화로 내보내려면 둘 중 하나가 `OUT=true` 여야 한다 | **ArtNet `OUT=false`, sACN `OUT=false`** · `INTERFACE 2.1` (`run6`) |
| 9 | 🔴 **출력 줄이 기구 유니버스를 덮나** | `…/DMXProtocols/1/1/<n>` (Art-Net-Data) · `…/2/1/<n>` (sACNData) | `state` 로 줄 목록, `props ENABLED,LOCALUNIVERSE,AMOUNT` | 기구 유니버스 U 가 `LOCALUNIVERSE ≤ U < LOCALUNIVERSE+AMOUNT` 인 `ENABLED=true` 줄이 있어야 한다 | 각 1줄: **`ENABLED=false`, `LOCALUNIVERSE 1`, `AMOUNT 1`** → 유니버스 5 미포함 (`run7`) |
| 10 | 선택 여부 | `Selection` (전역 별칭) | `props COUNTTOTALSELECTED` | 명령 뒤 선택 수가 오르면 명령이 닿은 것이다. 🔴 `state` 의 `childCount` 로 판정하지 말 것(§3) | 지금 `0` (t442 `ClearAll` 뒤) (`run1`) |
| 11 | 🔴 앱이 읽을 수 없음 — 3D 창 빔 표시 | 3D 창 MA 로고 → Rendering Settings → `Beam` 페이더 (공식 문서, 출처 1) | 없음 | 감독 눈으로만 확인. 0 이면 모든 빔이 안 보인다 | **안 잼** |
| 12 | 🔴 앱이 읽을 수 없음 — 3D 창 GPU 경고 | 3D 창 표시 (출처 1: onPC 에서 OpenGL 드라이버 문제가 있으면 경고를 대신 띄운다) | 없음 | 감독 눈으로만 확인 | **안 잼** |
| 13 | 🔴 앱이 읽을 수 없음 — 대조군 | 3D 창에서 켜지는 기구가 하나라도 있나 | 없음 | 하나라도 있으면 그 기구와 1~9 를 비교한다 | **「한 번도 없다」**(감독 답, 2026-09-23) |

### 판독 순서 제안

0 → 1 → 4·5 → 8·9 → 2·3 → 7 → 11~13. 계기 생존(0)을 먼저 확인하고, 모든 기구에 걸리는 전역 원인(마스터·출력)을 기구별 원인(채널·셔터·3D 배치)보다 먼저 본다. 이번 사례에서는 13 이 「한 번도 없다」라 기구별 원인이 처음부터 배제됐다. 13 을 **맨 먼저 묻는 편이 가장 싸다.**

## 2. 이번 사례의 해석

- 앱 쪽 이상값(8·9)은 **실제 조명기나 외부 시각화로 나가는 출력**을 설명한다. 감독은 onPC **내장 3D 창**을 보고 있었다. 내장 3D 창이 네트워크 출력(8·9)을 거쳐야 그리는지는 **확인하지 않았다.** 그래서 8·9 를 3D 창 원인으로 단정하지 않는다.
- 출처 3 의 검색 요약에는 「onPC 는 무료로 DMX 를 출력하지 않는다」는 문장이 있다. 이것은 검색 결과 요약일 뿐이고 **본문을 열어 확인하지 않았다.** 3D 창과의 관계도 모른다.
- 3D 창 원인 후보 두 개(11 `Beam` 페이더, 12 GPU)는 공식 문서(출처 1)를 직접 열어 확인했다. 이 쇼에서 해당하는지는 재지 않았다.

## 3. 겸사 — 「응답기가 선택·프로그래머를 못 읽는다」(t442 §3) 대조

lead-0902a 기록, t246, t248 판정서와 대조했다. 세 주장을 따로 적는다.

| 대상 | ① 문서가 싣는다 | ② 이 빌드가 노출한다 | ③ 핸들이 `Children()` 에 응답한다 | 값이 보이는 속성 |
|---|---|---|---|---|
| `Selection()` | t235 (lead-0902a §2) | 감독 `HelpLua` 판독: `43 Selection`, `66 SelectionCount` (lead-0902a §2) | 응답한다 — `state:Selection` → `class Selection`, `enumeration ok` | **`props COUNTTOTALSELECTED`** — t248 이 `Fixture 501` 전후로 0→1→0 을 관측했다 |
| `Programmer()` | t235 | `41 Programmer(nothing): light_userdata:handle`, `42 ProgrammerPart` | 응답한다 — `state:Programmer` → `childCount 1` (`Part Zero`) | **없음(미확인)** — t442 에서 Dim 100 이 프로그래머에 있는 동안에도 `Programmer/1` `childCount 0`. t248 은 `ProgrammerPart COUNT` 가 선택에 안 움직였다고 기록했다. 값 적재를 비추는 속성은 아직 못 찾았다 |

**t442 §3 정정**: 「응답기가 감독 화면의 선택을 보지 못한다」는 **틀렸다.** 경로(`Selection`)는 맞았고, 틀린 것은 읽은 필드다. `state` 의 `childCount` 가 아니라 `props COUNTTOTALSELECTED` 를 읽었어야 한다(t248 이 이미 적어 둔 사실이다). 「프로그래머 **값**을 못 본다」는 여전히 맞다 — 선택과 값은 다른 주장이다. 이번 카드에서는 선택 수가 `0`(ClearAll 뒤)인 것만 읽었다. 선택 전후로 움직이는지는 쓰기가 필요해서 다시 재지 않았다.

## 4. 원문 파일

| 파일 | 내용 |
|---|---|
| `run1_output_roots.txt` | ping, 날조 대조군, Selection 선택 수, ShowData/Output·DMXRoot (둘 다 `childCount 0`) |
| `run2_root.txt` | Root 자식 22 |
| `run3_candidates.txt` | ShowData 나머지, DeviceConfigurations, Interfaces(`lo0`, `en0`), HardwareStatus |
| `run4_device_configs.txt` | OutputStations 4, DMXProtocols(ArtNet, sACN) |
| `run5_protocols.txt` | 프로토콜 속성 이름, 데이터 줄, onPC OutputStation 13 |
| `run6_protocol_values.txt` | 🔴 `OUT=false` ×2 |
| `run7_lines.txt` | 🔴 `ENABLED=false`, `LOCALUNIVERSE 1`, `AMOUNT 1`; 401 `PATCH 5.151` |
| `run8_fixture_fields.txt` | 기구 속성 이름 (3D 관련) |
| `run9_3d_placement.txt` | 401·402·201·501 의 위치·`VISIBLE3D`·`MASTERREACT` |

## 5. 출처 (WebSearch → 직접 연 것과 검색 결과만인 것을 가른다)

1. [grandMA3 2.2 — 3D Viewer](https://help.malighting.com/grandMA3/2.2/HTML/patch_3d_viewer.html) — **WebFetch 로 직접 확인.** "Beam: This is the visibility of the light beam from all fixtures." (Rendering Settings 페이더). "When on an onPC station, the driver of the GPU has issues with OpenGL, the 3D Viewer informs the user about the driver issue instead."
2. [MA Lighting Forum — 3D View problems - Beams disappear](https://forum.malighting.com/forum/thread/8599-3d-view-problems-beams-disappear-irresistibly/) — 검색 결과만, 본문 미확인.
3. [MA 3D 제품 페이지](https://www.malighting.com/product-archive/product/ma-3d-MA3D/) — 검색 요약의 「onPC 는 무료로 DMX 를 출력하지 않는다」가 어느 출처의 문장인지 확인하지 않았다. 본문 미확인.

## 6. 안 잰 것

- 3D 창 `Beam` 페이더 값, GPU 경고 표시 여부 (앱이 못 읽음, 감독에게 묻지 않았다 — 리드 지시 「감독 확인 최소」)
- 내장 3D 창이 네트워크 출력(8·9)을 거쳐야 그리는지
- onPC 가 하드웨어 없이 파라미터를 내보내는지(라이선스·세션)
- 출력 설정의 목적지 IP (`DESTINATIONIP` 은 읽기 실패 `ERR`)
- 프로그래머 **값** 적재를 비추는 속성
- `Selection COUNTTOTALSELECTED` 가 이번 콘솔에서도 선택 전후로 움직이는지(쓰기 필요 — 안 함)
