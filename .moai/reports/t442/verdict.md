# t442 — W 흰색 vs RGB 흰색 실기 육안 비교

- 카드: t442, 레인 lane-1 · 브랜치 `WT-white-eye-test` · 기준 origin/main `73966746`
- 판정: **BLOCKED — 비교 못 함. 콘솔에서 불이 켜지지 않는다. 감독이 직접 `Fixture 401 Full` 을 쳐도 마찬가지다.** 감독의 흰색 선택은 받지 못했다. 코드 수정 0.
- 막힌 곳은 명령 다음 단계다. 명령은 콘솔에 닿는다: 기구가 선택되고, Dim 100 이 들어가고, 명령줄 이력은 `OK` 다(감독 스크린샷). 그랜드 마스터는 100 이고, Blind·Freeze·Preview 는 꺼져 있다(감독 스크린샷). 남은 후보는 DMX 출력과 3D 창 표시다. **둘 중 무엇인지는 재지 않았다.**

## 1. 전제가 깨졌다 — LEDBeam 350 은 패치에 0대

배차서는 LEDBeam 350 을 대상으로 지정했다. 지금 패치를 전수로 읽어 보니 한 대도 없었다.

- `state:Patch/Stages/1/Fixtures` + offset 18·36·54·72 → 86대 (`run1_patch_root.txt`, `run2_patch_pages.txt`)
- 86대 전부 `props … NAME,FID,FIXTURETYPE,MODE,PATCH` (`run4_fixture_types.txt`)
- 패치에서 쓰는 타입은 10·13·14·15·11·4·8·9 뿐이다. `Patch/FixtureTypes/3` = "Robin LEDBeam 350" 은 타입 표에만 있다 (`run5`, `run6_type_no.txt`: 1~15 모두 `NO` = 슬롯 번호)

W 채널을 실제로 가진 기구 (`run7_dmx_channels.txt`, `…/DMXModes/<m>/DMXChannels` 판독):

| 타입 | 모드 | 기구 | W 채널 |
|---|---|---|---|
| 9 Rush Par 2 RGBW Zoom | 2 (8채널 전부 읽음) | 401~410, 421~430 (20대) | `Main Module#2_ColorRGB_W` |
| 4 Robin Spiider | 1 (26채널 중 23 읽음) | 521~528 (8대) | `RGBW Cluster_ColorRGB_W`, `Main Module_ColorRGB_W` |
| 8 Mac Aura XB · 11 MegaPointe · 14 Atomic · 10 Source4 | — | — | 없음 (8·11 은 일부 채널을 읽지 못했다) |

리드가 교체를 승인했다(Rush Par 401~404 + Spiider 521~522, Dimmer 100 추가). 감독은 Rush Par 401~404 를 골랐다. Spiider 는 쏘지 않았다.

Rush Par 모드 2 의 채널: `Dimmer, Shutter1, ColorRGB_R, ColorRGB_G, ColorRGB_B, ColorRGB_W, COLORMIXER, Zoom`.

## 2. 콘솔 쓰기 기록 (명령줄 + 응답 원문)

도구는 `tools/console_probe.py` exec 이다(`PYTHONPATH=.` 로 이 트리의 `server` 를 쓴다). 쓴 것은 프로그래머 값뿐이다. Store·Assign·Delete·쇼 저장은 0회다.

| # | 명령 | 응답 | 감독 관찰 |
|---|---|---|---|
| ① | `Fixture 401 Thru 404 ; At 100 ; Attribute 'ColorRGB_R' At 85 ; Attribute 'ColorRGB_G' At 95 ; Attribute 'ColorRGB_B' At 100 ; Attribute 'ColorRGB_W' At 0` | `{"kind": "result", "ok": true, "result": "OK"}` | 처음엔 「켜짐」이라고 답했다가 ②에서 「안 켜졌다」로 정정했다 |
| ② | `Fixture 401 Thru 404 ; At 100 ; Attribute 'ColorRGB_R' At 0 ; … 'ColorRGB_W' At 100` | `ok: true, "OK"` | 안 켜짐 |
| 진단1 | `Fixture 401 At 100` | `ok: true, "OK"` | 「장비 선택은 되는데 불은 안 켜진다」, 기구 시트는 Dim 100 · Shutter 닫힘/0 |
| 진단4 | `Fixture 401 ; Attribute 'Shutter1' At 4.7` | `ok: true, "OK"` | 「전혀 작동 안 한다. 내가 해도 안 켜진다」 |
| 되돌림 | `ClearAll` | `ok: true, "OK"` | — |

감독 스크린샷의 명령줄 이력: `OK:Fixture 401 Full` · `OK:Full` — 감독이 직접 친 명령이다. 이것도 켜지지 않았다.

### 셔터 값 4.7% 를 고른 근거 (`diag3_shutter_ranges.txt`)

Shutter1 의 첫 채널 함수 "Shutter1 1" 에 ChannelSet 두 개가 있다. DMX 값은 24비트이고 65793 으로 나누면 0~255 가 된다.

- `closed` DMX 0~7 · `open` DMX 8~15 · 기본값 789516 = DMX 12 (open)
- 다음 함수 "Shutter1Strobe 2" 는 DMX 16 부터 시작한다 → 셔터를 **100% 로 쏘면 스트로브 범위다**

4.7% 는 퍼센트가 전 범위에 선형으로 걸리면 DMX 12(open)다(t134 에서 ColorRGB 로 실측한 선형성). 채널 함수 안쪽 범위로 걸리면 closed 쪽이다. 어느 쪽이든 스트로브 범위로는 가지 않는다. **이 채널에서 퍼센트가 어떻게 환산되는지는 재지 않았다.**

## 3. 🔴 계기가 눈을 가렸다 — 읽기 통로 두 개가 프로그래머 값을 보지 못한다

①·② 직후와 진단1 직후에 `state:Selection` → `childCount 0`, `state:Programmer/1`("Part Zero") → `childCount 0` 이 나왔다(`step1_cool_rgb.txt`, `diag1_single_line.txt`). 같은 시각 감독 화면에서는 401 이 선택되어 있었고 Dim 100 이었다. **응답기의 `Selection`·`Programmer` 별칭은 감독 화면의 선택·프로그래머를 보여 주지 않는다.** 되돌림 확인에 쓸 수 없는 계기다.

그래서 리드가 요구한 「ClearAll 뒤 한 대라도 읽어 값이 비었는지 확인」은 **하지 못했다.** 이 계기로 0이 나와도 증거가 되지 않는다.

①에서 읽은 값이 0이었는데 「켜짐」 답을 받고 ②로 넘어갔다. 계기와 눈이 어긋났을 때 그 모순부터 풀었어야 했다.

## 4. 원인 후보와 잰 것 (읽기 전용)

| 후보 | 잰 것 | 결과 |
|---|---|---|
| 명령이 콘솔에 안 닿음 | 감독 관찰 | 아니다 — 선택되고 Dim 100 |
| 셔터 닫힘 | 기구 시트(감독) · 셔터 open 값 발사 | 셔터를 열어도, 감독이 `Full` 을 쳐도 안 켜짐 → 단독 원인 아님 |
| 그랜드 마스터 0 | `props ShowData/Masters/2/1 NORMEDVALUE` → `100` (`diag7`) | 아니다 |
| Blind 모드 | Programmer 48개·UserProfiles/1 93개 속성 이름에 Blind 플래그 없음 (`diag8`, `diag9`) · 감독 스크린샷: `Freeze`·`Prvw`·`Blind` 키 표시등이 모두 회색(꺼짐) | 아니다 (감독 화면 관찰) |
| DMX 출력 꺼짐 / 3D 창이 라이브 출력을 안 비춤 | 재지 않음 | **미확인** |

## 5. 앱에 대한 사실 하나 (코드 판독)

앱은 셔터를 한 번도 건드리지 않는다. `server/looks/schema.py:16-17` 에 「`Shutter` 는 콘솔이 거부해서 들어가지 않았다. Strobe·셔터는 범위 밖」이라고 적혀 있다. 셔터가 닫힌 기구에는 앱의 색 큐가 켜지지 않을 수 있다. 이번에는 셔터를 열어도 켜지지 않았으므로 **이 문제가 여기서 원인이었는지는 판정할 수 없다.** 리드 판단을 위한 기록이다.

## 6. 안 잰 것

- 감독의 흰색 선택 (①~⑤ 비교) — 카드의 목적 자체
- DMX 출력 설정, 3D 창이 무엇을 보여 주는지 (Blind 는 감독 화면으로 꺼짐 확인)
- ClearAll 뒤 프로그래머가 비었는지 (§3: 계기가 보지 못한다)
- Shutter1 에서 퍼센트→DMX 환산
- Spiider 521~522 (쏘지 않음)
