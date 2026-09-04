# 프리셋 프로퍼티 되읽기 전수 스윕 — R2 측정

> SPEC-COPILOT-READBACK-001 M2 의 산출물. 읽기 전용 · **콘솔 쓰기 0건.**
> 판정: **미발견(measured-absent)** — 프리셋의 저장된 값(dim 퍼센트 · 색 RGB)을 답하는
> 판독 가능한 프로퍼티는 **이 채널에 없다.** 이것은 실패가 아니라 측정된 결과다
> (REQ-READBACK-012). 「못 찾았으니 다시 시도」가 아니라 「없다는 것을 쟀다」이다.

## 실행일

- **2026-09-04** (UTC). 스윕 도중 라이브 응답기 버전이 **1.6.3 → 1.6.4 로 바뀌었다**.
- 1.6.4 구간 시작 시각 `2026-09-04T10:09:46Z` — `date -u` 와 `ping` 을 같은 명령줄에서 찍었다.

### 마일스톤 도중 응답기 버전이 바뀐 사실

측정을 1.6.3 에 대고 한 번 끝낸 뒤, 운영자가 1.6.4 를 재임포트했다. 그래서 **전 구간을
1.6.4 에 대고 다시 쟀다.** 이 노트의 수치는 달리 적지 않는 한 전부 **1.6.4 실측**이며,
1.6.3 수치는 대조로만 남긴다.

배포 확인의 근거는 `ping` 뿐이다(REQ-READBACK-008). main 의 파일 내용은 증거가 아니다 —
이 저장소에는 live-1.6.1 / main-1.6.2 로 어긋난 전례가 있다.

```
$ uv run python -m server.tools.responder_roundtrip \
    --listen-port 9005 --skip-exec --expect-version 1.6.4 --path DataPool --wait 5
  [PASS] ping: ok
         live version=1.6.4 plugin=CopilotResponder
  [PASS] state: ok
         node={'childCount': 16, 'class': 'Pool', 'name': 'Default'} children=16
result: PASS
```

## 측정 대상과 계기

| 항목 | 값 |
|---|---|
| 주 대상 | `DataPool/PresetPools/Color/1` — 이름 `골드 앰버 (=P1)` · `OWNDATAPRESENT=true` |
| 부 대상 | `DataPool/PresetPools/Dimmer/1` — 이름 `풀` · `OWNDATAPRESENT=false` |
| 계기 | `server/tools/introspect_probe.py` (`introspect` 열거 · `props` 판독) |
| 채널 | OSC `127.0.0.1:8000` 송신 · 회신 수신 포트 **9005** |
| 응답기 | `CopilotResponder` **1.6.4** (`ping` 실측) |
| 콘솔 쓰기 | **0건** — `introspect` 와 `props` 는 둘 다 읽기 전용 |

경로 구분자는 **`/`** 다(`copilot_responder.lua:610` 의 `path:gmatch("[^/]+")`).
`.` 을 쓰면 문자열 전체가 한 세그먼트로 취급돼 `path segment not found` 로 떨어진다 —
이 노트를 재현할 때 가장 먼저 걸리는 함정이다.

**주 대상을 「값이 실제로 든」 프리셋으로 고른 이유**: 빈 프리셋을 재고 「값 프로퍼티가
없다」고 쓰면, 그것은 채널의 성질이 아니라 표본의 성질을 잰 것이다. `OWNDATAPRESENT=true`
인 개체를 주 대상으로 두어 그 교란을 없앴다.

## 열거 완전성 산술

AC-READBACK-010 이 요구하는 세 값을 모두 싣는다. 「전부 읽었다」는 이 셋이 정합할 때만 쓴다.

| 항목 | 값 |
|---|---|
| 콘솔이 보고한 `total` | **138** |
| 실제 도착한 이름 개수 | **138** (창별 27 + 28 + 26 + 26 + 26 + 5) |
| 마지막 창의 `truncated` | **false** |
| 병합 결과 `paging` | **complete** |
| 이름 중복 | 0 (고유 이름 138) |

```
windows: [ {offset 0,   received 27, truncated true},
           {offset 27,  received 28, truncated true},
           {offset 55,  received 26, truncated true},
           {offset 81,  received 26, truncated true},
           {offset 107, received 26, truncated true},
           {offset 133, received  5, truncated false} ]
27+28+26+26+26+5 = 138 = total
```

세 값이 정합하므로 **138개가 이 개체의 프로퍼티 이름 전부**다. 이 개수는 t95 가 기록한
138 과 일치한다(`test_overlap_preserve.py:180-186`). 두 대상(`Color/1` · `Dimmer/1`)의
이름 목록은 **순서까지 동일**했고, 1.6.3 과 1.6.4 사이에도 동일했다.

`childCount` 는 이 개체에서 **0** 이다 — 그것은 자식 노드 수이지 프로퍼티 수가 아니다.
프로퍼티 열거의 완전성을 판정하는 값은 위 표의 `total` / 도착 개수 / `truncated` 셋이다.

## 대조군

이 절이 없으면 모든 「판독 안 됨」이 **계기 고장**과 구별되지 않는다. 네 팔을 넣었다.

| 팔 | 넣은 것 | 답 | 무엇을 배제하는가 |
|---|---|---|---|
| **양성** | `NAME` (판독된다고 이미 알려진 프로퍼티) | `ok=true` · `t=string` · `v="골드 앰버 (=P1)"` | 계기가 죽어서 전부 실패한 것이 아니다 |
| **음성** | `__NOSUCHPROP_CONTROL__` (존재하지 않는 이름) | `ok=false` · `e="property not readable: __NOSUCHPROP_CONTROL__"` | 「없는 것은 없다고 답한다」 — 회신이 무조건 성공을 답하지 않는다 |
| **데이터 유무** | `Color/1`(`OWNDATAPRESENT=true`) vs `Dimmer/1`(`false`) | 판독 가능 집합 **117 / 21 로 완전히 동일**, 뒤집힌 이름 **0개** | 「빈 표본을 재서 없다고 했다」가 아니다 |
| **버전** | 1.6.3 vs 1.6.4 (같은 개체) | 판독 가능 집합 동일, **값이 바뀐 이름 정확히 3개** — 전부 테이블형 | 1.6.4 직렬화가 실제로 동작하며, 그래도 값은 안 나온다 |

**음성 대조군이 드러낸 한계**: 존재하지 않는 이름의 사유 문자열
(`property not readable: __NOSUCHPROP_CONTROL__`)은 **실재하지만 못 읽는 프로퍼티의 사유와
형식이 같다.** 이 문자열만으로는 「부재」와 「존재하되 비공개」를 가를 수 없다. 가르는 것은
`introspect` 열거 목록이다 — 목록에 **있으면서** 판독에 실패하면 존재하되 비공개, 목록에
**없으면** 부재다. 아래 21건은 전부 열거 목록 안에 있으므로 **부재가 아니라 비공개**다.

## 시도한 이름

열거된 138개 **전부**에 판독을 시도했다. 시도 138 / 도착 138 / 누락 0.
값은 `DataPool/PresetPools/Color/1`(1.6.4) 실측. 46자를 넘는 값은 표에서만 절단했다.

표의 `None` 은 **콘솔이 답한 문자열 리터럴**이지 파이썬 `None` 이나 판독 실패가 아니다
(회신 원문 `{"n":"X","ok":true,"t":"string","v":"None"}`). MAtricks 격자 프로퍼티가
설정되지 않았을 때 콘솔이 내놓는 값이며, `ok=true` 이므로 판독은 성공한 것이다.

| # | 이름 | 선언 타입 | 판독 | lua 타입 | 값 또는 사유 |
|---:|---|---|---|---|---|
| 1 | `IGNORENETWORK` | UInt64 | 판독됨 | boolean | `false` |
| 2 | `STRUCTURELOCKED` | UInt64 | 판독됨 | boolean | `false` |
| 3 | `SYSTEMLOCKED` | UInt64 | 판독됨 | boolean | `false` |
| 4 | `LOCK` | UInt64 | 판독됨 | string | `(빈 문자열)` |
| 5 | `INDEX` | UInt32 | 판독됨 | number | `1` |
| 6 | `COUNT` | UInt32 | 판독됨 | number | `0` |
| 7 | `NO` | UInt32 | 판독됨 | number | `1` |
| 8 | `NAME` | String | 판독됨 | string | `골드 앰버 (=P1)` |
| 9 | `USEREXPANDED` | UInt64 | 판독됨 | boolean | `false` |
| 10 | `FADERENABLED` | Bool | 판독됨 | boolean | `false` |
| 11 | `OWNED` | Bool | 판독됨 | boolean | `false` |
| 12 | `HIDDEN` | UInt64 | 판독됨 | boolean | `false` |
| 13 | `DEPENDENCYEXPORT` | String | 판독됨 | string | `(빈 문자열)` |
| 14 | `MEMORYFOOTPRINT` | Int64 | 판독됨 | number | `2376` |
| 15 | `GUID` | Custom | **판독 안 됨** | — | `property not readable: GUID` |
| 16 | `SCRIBBLE` | Handle | **판독 안 됨** | — | `property not readable: SCRIBBLE` |
| 17 | `APPEARANCE` | Handle | **판독 안 됨** | — | `property not readable: APPEARANCE` |
| 18 | `NOTE` | String | 판독됨 | string | `(빈 문자열)` |
| 19 | `TAGS` | Custom | 판독됨 | string | `(빈 문자열)` |
| 20 | `PREVIEWCOPY` | Handle | **판독 안 됨** | — | `property not readable: PREVIEWCOPY` |
| 21 | `ACTIVE` | UInt8 | 판독됨 | boolean | `false` |
| 22 | `HASANYMATRICKSDATA` | Bool | 판독됨 | boolean | `false` |
| 23 | `SHUFFLEMODE` | UInt8 | 판독됨 | string | `Auto` |
| 24 | `INITIALNAME` | String | 판독됨 | string | `(빈 문자열)` |
| 25 | `INITIALMATRICKS` | Handle | **판독 안 됨** | — | `property not readable: INITIALMATRICKS` |
| 26 | `X` | Int32 | 판독됨 | string | `None` |
| 27 | `Y` | Int32 | 판독됨 | string | `None` |
| 28 | `Z` | Int32 | 판독됨 | string | `None` |
| 29 | `XBLOCK` | Int32 | 판독됨 | string | `None` |
| 30 | `YBLOCK` | Int32 | 판독됨 | string | `None` |
| 31 | `ZBLOCK` | Int32 | 판독됨 | string | `None` |
| 32 | `XGROUP` | Int32 | 판독됨 | string | `None` |
| 33 | `YGROUP` | Int32 | 판독됨 | string | `None` |
| 34 | `ZGROUP` | Int32 | 판독됨 | string | `None` |
| 35 | `XWINGS` | Int32 | 판독됨 | string | `None` |
| 36 | `YWINGS` | Int32 | 판독됨 | string | `None` |
| 37 | `ZWINGS` | Int32 | 판독됨 | string | `None` |
| 38 | `XWIDTH` | Int32 | 판독됨 | string | `None` |
| 39 | `YWIDTH` | Int32 | 판독됨 | string | `None` |
| 40 | `ZWIDTH` | Int32 | 판독됨 | string | `None` |
| 41 | `XSHUFFLE` | UInt32 | 판독됨 | string | `None` |
| 42 | `YSHUFFLE` | UInt32 | 판독됨 | string | `None` |
| 43 | `ZSHUFFLE` | UInt32 | 판독됨 | string | `None` |
| 44 | `XSHIFT` | Int32 | 판독됨 | string | `None` |
| 45 | `YSHIFT` | Int32 | 판독됨 | string | `None` |
| 46 | `ZSHIFT` | Int32 | 판독됨 | string | `None` |
| 47 | `XINV` | UInt32 | 판독됨 | boolean | `false` |
| 48 | `XINVB` | UInt32 | 판독됨 | boolean | `false` |
| 49 | `XINVG` | UInt32 | 판독됨 | boolean | `false` |
| 50 | `XINVW` | UInt32 | 판독됨 | boolean | `false` |
| 51 | `YINV` | UInt32 | 판독됨 | boolean | `false` |
| 52 | `YINVB` | UInt32 | 판독됨 | boolean | `false` |
| 53 | `YINVG` | UInt32 | 판독됨 | boolean | `false` |
| 54 | `YINVW` | UInt32 | 판독됨 | boolean | `false` |
| 55 | `ZINV` | UInt32 | 판독됨 | boolean | `false` |
| 56 | `ZINVB` | UInt32 | 판독됨 | boolean | `false` |
| 57 | `ZINVG` | UInt32 | 판독됨 | boolean | `false` |
| 58 | `ZINVW` | UInt32 | 판독됨 | boolean | `false` |
| 59 | `INVERTSTYLE` | UInt8 | 판독됨 | string | `Pan` |
| 60 | `INVERTX` | UInt32 | 판독됨 | boolean | `false` |
| 61 | `INVERTY` | UInt32 | 판독됨 | boolean | `false` |
| 62 | `INVERTZ` | UInt32 | 판독됨 | boolean | `false` |
| 63 | `ALIGNRANGEX` | UInt8 | 판독됨 | boolean | `false` |
| 64 | `ALIGNRANGEY` | UInt8 | 판독됨 | boolean | `false` |
| 65 | `ALIGNRANGEZ` | UInt8 | 판독됨 | boolean | `false` |
| 66 | `RELATIVEFADE` | UInt32 | 판독됨 | boolean | `true` |
| 67 | `RELATIVEDELAY` | UInt32 | 판독됨 | boolean | `true` |
| 68 | `RELATIVEPHASE` | UInt32 | 판독됨 | boolean | `true` |
| 69 | `RELATIVESPEED` | UInt32 | 판독됨 | boolean | `false` |
| 70 | `RELATIVE` | Bool | 판독됨 | boolean | `true` |
| 71 | `PHASERTRANSFORM` | UInt32 | 판독됨 | string | `None` |
| 72 | `FADEFROMX` | Int64Time | 판독됨 | string | `None` |
| 73 | `FADETOX` | Int64Time | 판독됨 | string | `None` |
| 74 | `DELAYFROMX` | Int64Time | 판독됨 | string | `None` |
| 75 | `DELAYTOX` | Int64Time | 판독됨 | string | `None` |
| 76 | `SPEEDFROMX` | Int64Time | 판독됨 | string | `None` |
| 77 | `SPEEDTOX` | Int64Time | 판독됨 | string | `None` |
| 78 | `PHASEFROMX` | Int32 | 판독됨 | string | `None` |
| 79 | `PHASETOX` | Int32 | 판독됨 | string | `None` |
| 80 | `FADEFROMY` | Int64Time | 판독됨 | string | `None` |
| 81 | `FADETOY` | Int64Time | 판독됨 | string | `None` |
| 82 | `DELAYFROMY` | Int64Time | 판독됨 | string | `None` |
| 83 | `DELAYTOY` | Int64Time | 판독됨 | string | `None` |
| 84 | `SPEEDFROMY` | Int64Time | 판독됨 | string | `None` |
| 85 | `SPEEDTOY` | Int64Time | 판독됨 | string | `None` |
| 86 | `PHASEFROMY` | Int32 | 판독됨 | string | `None` |
| 87 | `PHASETOY` | Int32 | 판독됨 | string | `None` |
| 88 | `FADEFROMZ` | Int64Time | 판독됨 | string | `None` |
| 89 | `FADETOZ` | Int64Time | 판독됨 | string | `None` |
| 90 | `DELAYFROMZ` | Int64Time | 판독됨 | string | `None` |
| 91 | `DELAYTOZ` | Int64Time | 판독됨 | string | `None` |
| 92 | `SPEEDFROMZ` | Int64Time | 판독됨 | string | `None` |
| 93 | `SPEEDTOZ` | Int64Time | 판독됨 | string | `None` |
| 94 | `PHASEFROMZ` | Int32 | 판독됨 | string | `None` |
| 95 | `PHASETOZ` | Int32 | 판독됨 | string | `None` |
| 96 | `DOSHUFFLE` | Method | 판독됨 | table | `{"Property":"DOSHUFFLE","Target":"Preset 4.1"}` |
| 97 | `MEMORYTYPE` | UInt8 | 판독됨 | string | `Compressed` |
| 98 | `MOVEGRIDCURSOR` | UInt8 | 판독됨 | string | `Append X` |
| 99 | `PRESERVEGRIDPOSITIONS` | UInt32 | 판독됨 | boolean | `false` |
| 100 | `SELECTIONDATA` | Custom | 판독됨 | table | `{}` |
| 101 | `INPUTFILTER` | Handle | **판독 안 됨** | — | `property not readable: INPUTFILTER` |
| 102 | `CUEPART` | UInt32 | 판독됨 | string | `Default` |
| 103 | `TYPE` | String | 판독됨 | string | `Preset` |
| 104 | `USER` | String | 판독됨 | string | `(빈 문자열)` |
| 105 | `FEATUREGROUP` | String | 판독됨 | string | `Color` |
| 106 | `TRIGGER` | String | 판독됨 | string | `(빈 문자열)` |
| 107 | `VALUESMODE` | UInt32 | 판독됨 | string | `Normal` |
| 108 | `MAGIC` | UInt32 | 판독됨 | boolean | `false` |
| 109 | `PRESETMODE` | UInt8 | 판독됨 | string | `Universal` |
| 110 | `STOREDDATA` | String | 판독됨 | string | `Universal` |
| 111 | `SPEEDMASTER` | Custom | 판독됨 | string | `None` |
| 112 | `SPEEDSCALE` | Int8 | 판독됨 | number | `0` |
| 113 | `PRESETDATA` | Custom | 판독됨 | string | `(빈 문자열)` |
| 114 | `OWNDATAPRESENT` | Bool | 판독됨 | boolean | `true` |
| 115 | `DIRECTPROGRAMMERCOOKING` | Bool | 판독됨 | boolean | `false` |
| 116 | `OWNNONCOOKEDDATAPRESENT` | UInt64 | 판독됨 | boolean | `true` |
| 117 | `MODE` | UInt8 | 판독됨 | number | `0` |
| 118 | `OFFFADE` | Int64Time | **판독 안 됨** | — | `property not readable: OFFFADE` |
| 119 | `RECIPETEMPLATE` | UInt32 | 판독됨 | boolean | `false` |
| 120 | `DELAYTOPHASE` | UInt32 | 판독됨 | boolean | `false` |
| 121 | `DEPENDENCIES` | Custom | 판독됨 | table | `{}` |
| 122 | `REFERENCES` | Custom | 판독됨 | string | `3154118741:8090489919094998016,3154118749:-620…(절단)` |
| 123 | `MAXDEPTH` | UInt64 | 판독됨 | number | `0` |
| 124 | `AUTOSTART` | UInt32 | **판독 안 됨** | — | `property not readable: AUTOSTART` |
| 125 | `AUTOSTOP` | UInt32 | **판독 안 됨** | — | `property not readable: AUTOSTOP` |
| 126 | `AUTOFIX` | UInt32 | **판독 안 됨** | — | `property not readable: AUTOFIX` |
| 127 | `AUTOSTOMP` | UInt32 | **판독 안 됨** | — | `property not readable: AUTOSTOMP` |
| 128 | `SOFTLTP` | UInt32 | **판독 안 됨** | — | `property not readable: SOFTLTP` |
| 129 | `SWAPPROTECT` | UInt32 | **판독 안 됨** | — | `property not readable: SWAPPROTECT` |
| 130 | `KILLPROTECT` | UInt32 | **판독 안 됨** | — | `property not readable: KILLPROTECT` |
| 131 | `USEEXECUTORTIME` | UInt32 | **판독 안 됨** | — | `property not readable: USEEXECUTORTIME` |
| 132 | `OFFWHENOVERRIDDEN` | UInt32 | **판독 안 됨** | — | `property not readable: OFFWHENOVERRIDDEN` |
| 133 | `AUTOPREPOS` | UInt32 | **판독 안 됨** | — | `property not readable: AUTOPREPOS` |
| 134 | `PRIORITY` | UInt8 | **판독 안 됨** | — | `property not readable: PRIORITY` |
| 135 | `PLAYBACKMASTER` | Custom | **판독 안 됨** | — | `property not readable: PLAYBACKMASTER` |
| 136 | `OUTPUTFILTER` | Handle | **판독 안 됨** | — | `property not readable: OUTPUTFILTER` |
| 137 | `EXECUTORDISPLAYMODE` | UInt8 | **판독 안 됨** | — | `property not readable: EXECUTORDISPLAYMODE` |
| 138 | `ACTION` | Custom | 판독됨 | number | `416` |

## 사유

판독에 실패한 **21건**. 사유 문자열을 콘솔이 답한 그대로 싣는다.
이 21건은 두 대상에서 동일했고 1.6.3 → 1.6.4 에서도 바뀌지 않았다.

사유 문자열의 형식은 전부 하나다:

```
property not readable: <이름>
```

| # | 이름 | 사유 문자열(원문) |
|---:|---|---|
| 1 | `GUID` | `property not readable: GUID` |
| 2 | `SCRIBBLE` | `property not readable: SCRIBBLE` |
| 3 | `APPEARANCE` | `property not readable: APPEARANCE` |
| 4 | `PREVIEWCOPY` | `property not readable: PREVIEWCOPY` |
| 5 | `INITIALMATRICKS` | `property not readable: INITIALMATRICKS` |
| 6 | `INPUTFILTER` | `property not readable: INPUTFILTER` |
| 7 | `OFFFADE` | `property not readable: OFFFADE` |
| 8 | `AUTOSTART` | `property not readable: AUTOSTART` |
| 9 | `AUTOSTOP` | `property not readable: AUTOSTOP` |
| 10 | `AUTOFIX` | `property not readable: AUTOFIX` |
| 11 | `AUTOSTOMP` | `property not readable: AUTOSTOMP` |
| 12 | `SOFTLTP` | `property not readable: SOFTLTP` |
| 13 | `SWAPPROTECT` | `property not readable: SWAPPROTECT` |
| 14 | `KILLPROTECT` | `property not readable: KILLPROTECT` |
| 15 | `USEEXECUTORTIME` | `property not readable: USEEXECUTORTIME` |
| 16 | `OFFWHENOVERRIDDEN` | `property not readable: OFFWHENOVERRIDDEN` |
| 17 | `AUTOPREPOS` | `property not readable: AUTOPREPOS` |
| 18 | `PRIORITY` | `property not readable: PRIORITY` |
| 19 | `PLAYBACKMASTER` | `property not readable: PLAYBACKMASTER` |
| 20 | `OUTPUTFILTER` | `property not readable: OUTPUTFILTER` |
| 21 | `EXECUTORDISPLAYMODE` | `property not readable: EXECUTORDISPLAYMODE` |

이 21건은 **「0 건」이 아니라 「재지 못함」**으로 분류한다(AC-READBACK-009). 값이 0 이라는
뜻이 아니라, 이 채널로는 값을 볼 수 없다는 뜻이다. 열거 목록에 이름이 있으므로 부재도 아니다.

## 판정 — 미발견

**값 프로퍼티를 하나도 찾지 못했다.** 판독된 117건 중 프리셋의 저장된 값
(dim 퍼센트 · 색 RGB)을 답하는 것은 **없다.** 값을 실을 법한 이름들의 실측:

| 이름 | 1.6.4 실측값 | 값인가 |
|---|---|---|
| `PRESETDATA` | `""` (빈 문자열) | 아니다 — 데이터가 든 프리셋에서도 비어 있다 |
| `STOREDDATA` | `"Universal"` | 아니다 — 모드 이름이다 |
| `SELECTIONDATA` | `{}` | 아니다 — **빈 테이블** |
| `DEPENDENCIES` | `{}` | 아니다 — **빈 테이블** |
| `DOSHUFFLE` | `{"Property":"DOSHUFFLE","Target":"Preset 4.1"}` | 아니다 — 메소드 핸들 메타 |
| `VALUESMODE` | `"Normal"` | 아니다 — 모드 이름 |
| `MEMORYFOOTPRINT` | `2376` | 아니다 — 바이트 수 |
| `OWNDATAPRESENT` | `true` | 아니다 — **데이터가 있다는 사실**만 말한다 |
| `REFERENCES` | `3154118741:8090489919094998016,…` (**절단됨**) | 미해독 — 아래 참조 |

`OWNDATAPRESENT=true` 는 이 판정을 뒤집지 않고 **오히려 굳힌다**: 콘솔은 「데이터가 있다」고
답하면서 그 데이터의 값은 어느 프로퍼티로도 내주지 않는다. 슬롯 점유는 되읽히지만 값은
안 읽힌다 — `_VALUE_MATCH_REASON` 이 말해 온 그대로이며, 이제 그것이 **측정된 사실**이다.

### 1.6.4 가 B2 를 해소했다

M0 이 배포한 테이블 직렬화가 실제로 동작한다. 1.6.3 에서 `table: 0x…` 주소만 답하던 세
이름이 1.6.4 에서 JSON 을 답했고, **바뀐 값은 정확히 그 셋뿐**이다:

| 이름 | 1.6.3 | 1.6.4 |
|---|---|---|
| `SELECTIONDATA` | `table: 0x6000039c46c0` | `{}` |
| `DEPENDENCIES` | `table: 0x6000039cec00` | `{}` |
| `DOSHUFFLE` | `PropertyInvokeMeta: 0x6000039cb280` | `{"Property":"DOSHUFFLE","Target":"Preset 4.1"}` |

이것이 `plan.md §B` 의 **B2**(「`SELECTIONDATA`·`DEPENDENCIES` 의 실제 테이블 형상은
미관측」)에 대한 답이다. **Preset 개체에서 두 테이블은 비어 있다.** 오프라인 테스트가
「아무도 본 적 없는 형상」 위에서 통과하던 상태는 여기서 끝난다. 다만 이 관측은 **Preset
개체에 한정**된다 — Part 등 다른 클래스의 형상은 여전히 미관측이다.

## 재지 못한 것

측정되지 않은 것을 측정된 것처럼 읽지 않도록 명시한다.

1. **`REFERENCES` 의 내용은 해독하지 않았다.** 데이터가 든 프리셋에서만 비고, 형식은
   `<정수>:<64비트 정수>` 쌍의 쉼표 목록이다(예 `3154118741:8090489919094998016`). 앞은
   픽스처 식별자로 보이고 뒤는 불투명한 64비트 패턴이다. **해독 계약이 없다** — 이것이
   값을 담고 있는지, 담았다면 어떤 인코딩인지 재지 않았다. 값 되읽기를 다시 열려면
   여기가 유일하게 남은 출발점이다. 별도 카드가 필요하다.
2. **`REFERENCES` 는 회신에서 절단된다** (`truncated: true`, 관측 길이 240자).
   1.6.3 에서도 같았다 — 1.6.4 가 만든 현상이 아니다. 전체 값은 이 채널로 못 봤다.
3. **Preset 이외 클래스의 테이블 형상은 미관측.** 위 B2 해소는 Preset 한정이다.
4. **프리셋 풀 2종(Color · Dimmer) 2개체만 전수 스윕했다.** Position/Gobo/Beam 등 다른
   featureGroup 은 열거 목록이 같은지 재지 않았다.
5. **기본 5초 타임아웃이 두 배치에서 회신을 놓쳤다**(1.6.3 구간). `--timeout-seconds 20`
   으로 재시도하니 둘 다 정상 판독됐다. 타임아웃은 **「판독 안 됨」이 아니라 「재지 못함」**
   이므로 그렇게 재분류해 다시 쟀다. 이 노트의 21건에는 타임아웃이 하나도 섞여 있지 않다.

## 이 측정이 코드에 미치는 영향

**미발견 경로**이므로 `preset_mapper.py` 의 `value_match` 는 **남는다.** 고정 테스트 3건
(`test_lxseq_preset_mapper.py:239-241, :443, :445-448`)은 **초록 그대로**다. 바뀌는 것은
`_VALUE_MATCH_REASON` 문면 하나 — 「이 채널로 읽히지 않는다」가 이제 **측정 일자와 근거를
동반한 사실**로 강화된다. `presets_api.py` 는 손대지 않는다: 콘솔 유래 값 필드를 만들
근거가 없고, 앱 팔레트 색을 그 자리에 놓는 것은 금지돼 있다(REQ-READBACK-013).

## 재현

```bash
uv run python -m server.tools.responder_roundtrip \
  --listen-port 9005 --skip-exec --expect-version 1.6.4 --path DataPool --wait 5

uv run python -m server.tools.introspect_probe \
  --path "DataPool/PresetPools/Color/1" --listen-port 9005 \
  --timeout-seconds 20 --all-pages

uv run python -m server.tools.introspect_probe \
  --path "DataPool/PresetPools/Color/1" --listen-port 9005 --timeout-seconds 20 \
  --names "NAME,PRESETDATA,STOREDDATA,SELECTIONDATA,DEPENDENCIES,REFERENCES,OWNDATAPRESENT,__NOSUCHPROP_CONTROL__"
```

판독은 이름당 최대 12개씩 12회로 나눠 보냈다. 한 회신의 페이로드 예산 때문이며, 배치마다
`truncated: false` 를 확인했다.

## 교차 참조

- `.moai/specs/SPEC-COPILOT-READBACK-001/` — `spec.md` · `plan.md §E M2` · `acceptance.md`
  (AC-READBACK-009 · 010 · 013 · 014)
- `server/lxseq/preset_mapper.py` — `_VALUE_MATCH_REASON`
- `console/lua/PROTOCOL.md` §4.6 · §4.7 · §4.8 — `props` / `introspect` 계약
- `docs/runbooks/console-channel-facts.md` §4 — 「테이블 주소」 항목이 이 측정으로 갱신 대상이 된다
- `server/tests/test_overlap_preserve.py:180-186` — t95 의 138 기록
