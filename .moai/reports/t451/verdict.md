# t451 — 코파일럿 조명 진단 도구 `diagnose_fixture_light`

- 카드: t451 (클래스 C), 레인 lane-1 · 브랜치 `WT-copilot-light-check` · 기준 origin/main `f5283ea4`
- 판정: **PASS — 코파일럿이 「401 왜 안 켜져?」에 읽기 전용 점검으로 답한다.** 원인 후보와 「콘솔에서 확인할 곳」까지 알려 준다. 감독이 대화창에서 읽는 한국어 요약이 함께 나온다.
- 콘솔 쓰기 0. 응답기 Lua 변경 0(기존 `state`·`prop` 만 쓴다 → VERSION 변경·플러그인 재로드 불필요). 앱은 셔터를 건드리지 않는다(`server/looks/schema.py:16-17` 그대로).
- 범위 밖으로 둔 것: 타입 8·9(Mac Aura XB·Rush Par 2 RGBW)가 3D 에서 안 켜지는 **원인**. 감독 지시 「장비가 안 켜지는 건 콘솔 문제지 코파일럿 문제가 아니다」에 따라 추적을 멈췄다. 모은 판독은 §4 에 사실로만 남긴다.

## 1. 바뀐 것

| 파일 | 변경 |
|---|---|
| `server/preshow/fixture_light.py` (신규) | `diagnose_fixture_light(fid, *, state_port, property_port, compare_fid=None, …)` → `LightDiagnosis` (`findings` + 한국어 `summary`). 쓰기 경로 import 0 |
| `server/orchestrator/tools.py` | `TOOL_NAMES` · 핸들러 · `ToolDefinition` · `handlers` 4곳. 인자 `fid`(필수), `compare_fid`(선택, 감독이 「켜진다」고 알려 준 기구) |
| `server/orchestrator/runner.py` | 진행 표시 표에 `"diagnose_fixture_light": "기구 점등 진단(읽기 전용)"` |
| `server/tests/test_tools.py` | 닫힌 도구 수 39 → 40 |
| `server/tests/test_fixture_light_diag_t451.py` (신규) | 가짜 콘솔 시험 19건 |

### 점검 순서 (t450 §1 표 + 정정 반영)

1. 계기 생존 — 양성 대조 `ShowData` 가 읽히고, 날조 경로 `ShowData/__t451_no_such_object__` 가 **`path segment not found` 로** 거절돼야 한다. 침묵이나 다른 형태의 오류는 거절로 치지 않는다 → 진단을 멈춘다
2. 기구 찾기 — `Patch/Stages/1/Fixtures` 를 `paged_children` 로 페이징하고, 이름이 번호로 끝나는 칸부터 `FID` 를 대조한다
3. `compare_fid` 가 있으면 두 기구의 타입·모드·채널·색 기본값·3D 표시·마스터 반응을 나란히 → 차이가 **원인 후보 1순위**
4. 그랜드·월드 마스터 `NORMEDVALUE`
5. 3D 표시·마스터 반응·채널 구성·색 채널 기본값(`<채널>/1/1 DEFAULT`, 24비트 ÷ 65793)
6. 셔터 — open 구간을 읽고 **「콘솔 기구 시트에서 Shutter 가 open 인지」 안내**만 한다(값은 앱이 못 읽음)
7. 선택 수 `Selection COUNTTOTALSELECTED` (t248)
8. 네트워크 DMX 출력 — **「외부 출력용 참고」로만**, 3D 원인으로 올리지 않는다(t450 정정)
9. 앱이 확인 못함: 켜지는 기구(`compare_fid` 없을 때 요약 첫 줄에서 묻는다) · 3D Beam 페이더 · GPU 경고 · 프로그래머 값(「미확인」 고정)

상태는 여섯 가지다: `ok` · `abnormal`(읽은 값이 점등을 막음) · `candidate`(막을 수 있으나 미확정) · `info` · `unknown`(못 읽음 — `abnormal` 로 올리지 않는다) · `app_cannot_check`(볼 곳을 함께 준다).

## 2. 검증

### 가짜 콘솔 시험

```
uv run pytest -q -p no:cacheprovider server/tests/test_fixture_light_diag_t451.py server/tests/test_tools.py server/tests/test_runner_progress.py
105 passed in 0.52s
```

리드가 요구한 단언(t450 실측 상황의 요약에 「DMX 네트워크 출력 꺼짐」「3D Beam 페이더 확인」이 있는지): `test_the_korean_summary_names_the_output_and_the_beam_fader`. 같은 시험이 「DMX 네트워크 출력」이 **원인 후보 칸에는 없음**도 단언한다.

전체 (`uv run pytest -q -p no:cacheprovider`, 이 트리): `14245 passed, 35 skipped, 1 warning in 190.91s` — `pytest_full.txt`. 첫 실행에서는 `test_runner_progress.py` 의 「등록된 도구마다 한국어 작업 이름」 검사가 새 도구 이름으로 1건 실패했다. `runner.py` 표에 이름을 넣어 고쳤다.

### 뮤테이션 — 시험이 결함을 잡는가

코드를 일부러 망가뜨리고 시험이 빨개지는지 확인했다. 모듈은 매번 원본으로 되돌렸다(`git diff` 로 확인).

| 망가뜨린 곳 | 결과 |
|---|---|
| 색 기본값 전부 0 판정 제거 | FAIL 1 |
| `dmx_output` 을 `abnormal` 로 | FAIL 3 (+등록 시험 1) |
| 계기 판정: 어떤 예외든 「살아 있음」 | 처음엔 **통과(공허)** → 시험 `test_a_timeout_on_the_fabricated_path_is_not_a_rejection` 추가 → FAIL 1 |

### 실기 읽기 전용 1회 (감독 콘솔, 응답기 1.6.5)

`.venv/bin/python .moai/reports/t451/live_run.py 401 101` → `requests=59 verbs=['prop', 'state'] elapsed=3.9s` (`live_final_401_vs_101.txt`)

요약 원문(감독이 대화창에서 보게 될 글):

```
먼저 확인: 켜지는 기구 101 와 기구 401 를 나란히 읽었습니다.

[원인 후보 — 이상] 1건
- 켜지는 기구 101 와 대조: 타입: FixtureType 9 ↔ FixtureType 10 · 모드: 2 9 channel ↔ 3 Direct · 401 에만 있는 채널: COLORMIXER, ColorRGB_W, Zoom · 101 에만 있는 채널: ColorRGB_BM, ColorRGB_C, ColorRGB_GY, ColorRGB_RY, DEEPRED, DimmerCurve, Fans — 켜지는 기구와 다른 점이다. 이 차이가 원인 후보다.

[앱이 확인 못함 — 볼 곳]
- 셔터 열림: open = DMX 8~15 — 이 기구는 셔터가 있어 열려 있어야 켜진다. 지금 셔터 값은 앱이 확인 못한다. (볼 곳: 콘솔 기구 시트에서 이 기구의 Shutter 가 open(DMX 8~15)인지)
- 3D 창 Beam 페이더 — 모든 기구의 빔이 안 보인다면 이것부터 본다. (볼 곳: 3D 창 MA 로고 → Rendering Settings → Beam 페이더)
- 3D 창 GPU 경고 (볼 곳: 3D 창에 OpenGL/GPU 드라이버 경고가 떠 있는지)
- 지금 들어간 디머·셔터·색 값 — 미확인 — 응답기는 프로그래머에 들어간 값(디머·셔터·색)을 비추지 못한다(t442·t450 §3). 콘솔의 기구 시트(Fixture Sheet)에서 이 기구 줄을 보라.

[참고 — 외부 출력용] DMX 네트워크 출력 꺼짐. 콘솔 내장 3D 창의 원인은 아니다.

모든 기구가 3D 창에서 안 보인다면 3D Beam 페이더 확인부터 하세요 (3D 창 MA 로고 → Rendering Settings → Beam).

[정상]
- 콘솔 응답: 양성 대조 읽힘 · 날조 경로 거절
- 기구 401: NAME WASH-U 401 · PATCH 5.151 · FIXTURETYPE FixtureType 9 · MODE 2 9 channel
- 그랜드 마스터: 100
- 월드 마스터: 100
- 3D 표시: true
- 채널 구성: Dimmer, Shutter1, ColorRGB_R, ColorRGB_G, ColorRGB_B, ColorRGB_W, COLORMIXER, Zoom
- 색 채널 기본값: ColorRGB_R 255, ColorRGB_G 255, ColorRGB_B 255, ColorRGB_W 0
```

### t450 손 판독과 도구 판독 대조

| 항목 | t450 손 판독 | 도구 판독 (같은 콘솔) |
|---|---|---|
| 401 패치 | `5.151`, `FixtureType 9`, `2 9 channel` | 같음 |
| 그랜드·월드 마스터 | 100 · 100 | 같음 |
| 3D 표시 | `true` | 같음 |
| 채널 | Dimmer, Shutter1, R, G, B, W, COLORMIXER, Zoom | 같음 |
| 셔터 open | DMX 8~15 | 같음 |
| ArtNet·sACN | `OUT=false` · 줄 `ENABLED=false`, 유니버스 1 | 같음 (`live_final_401_vs_101.txt` JSON) |

## 3. 설계 도중 바뀐 것 (리드·감독 정정)

1. **t450 결론 정정**: 「이 쇼의 3D 창은 어떤 기구도 켠 적이 없다」는 틀렸다. 감독 스크린샷에 여러 기구가 켜져 있었다. 안 켜지는 것은 타입 8·9 뿐이다. → 네트워크 출력을 참고 항목으로 내렸고, 「켜지는 기구와 나란히 읽기」를 핵심으로 올렸다. t450 판정서 머리에 정정 한 줄을 이 PR 에 넣었다.
2. **「색 값 0」 가설 기각**: 실측 색 기본값은 R·G·B 255(타입 8·9 모두)이고, 감독이 컬러 프리셋으로 색이 이미 들어가 있다고 확인했다. 1순위에서 내렸다. 도구는 기본값이 **전부 0 일 때만** 후보로 올린다.
3. **셔터**: 원인 추적 대신 「콘솔에서 열림 확인」 안내 항목으로만 둔다. 제품 결함 후보라는 제안은 리드가 철회했다.

## 4. 멈춘 추적 — 모은 판독 (사실만, 원인 판정 없음)

`live_colormixer.txt` · `live_type_children.txt` · `live_geometries*.txt` · `live_beam_props.txt` (전부 읽기 전용)

| 판독 | 타입 9 Rush Par (안 켜짐) | 타입 8 Mac Aura XB (안 켜짐) | 타입 10 Source4 (켜짐) |
|---|---|---|---|
| 색 채널 기본값 | R·G·B 255, W 0 | R·G·B 255 | (비교에서 차이 없음) |
| `COLORMIXER` 기본 | 0 = `ColorMacro 1 / Normal` (DMX 0~10) | 0 = `ColorMacro 1 / Normal` (DMX 0~9) | 채널 없음 |
| 지오메트리 | `Body/Main Module`(Beam) · `Body#2/Main Module#2`(Beam), 모드2 채널은 `Main Module#2_*` | `Aura`·`Aura#2`·`Aura#3`(Beam) + `Body#1~4` | `Body/Main Module`(Beam) |
| Beam `BEAMANGLE` / `FIELDANGLE` | 1.0 / 25.0 | 25.0 / 25.0 | 17.0 / 25.0 |
| Beam `LAMPTYPE` · `BEAMTYPE` | LED/Tungsten · Wash | LED · Wash | Tungsten · Spot |
| `LUMINOUSINTENSITY` | 10000 | 10000 | 10000 |

어느 칸도 「안 켜짐」을 설명한다고 판정하지 않았다. 판독으로 기각된 것은 둘이다: 색 기본값 0, 모드 채널이 Beam 이 아닌 지오메트리를 가리킨다는 가정(`Main Module#2` 는 Beam 이다).

## 5. 안 잰 것

- 타입 8·9 가 3D 에서 안 켜지는 원인 (감독 지시로 중단)
- LLM 이 실제 대화에서 이 도구를 고르는지 — 도구 설명(`ToolDefinition.description`)만 썼고 대화형 실행은 안 했다
- `compare_fid` 없이 부를 때 감독이 번호를 답하고 다시 부르는 두 단계 흐름 — 시험은 각 호출만 잰다
- 큰 리그에서의 판독 시간(86대 리그, 401 은 이름 순서 덕에 빨리 찾았다. 최악은 기구 수만큼 `FID` 판독)
