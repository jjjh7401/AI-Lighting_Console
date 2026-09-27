# t471 — 곡 큐 조립기 사전이동의 어둠 길이 검사·live_move 경고 (lane-1)

- 브랜치 `WT-composer-mib-check` · 기준 `origin/main@d59b5ecd` · 콘솔 쓰기 0
- 입력: `.moai/reports/t468/verdict.md` §4 (조립기 `_apply_mib`가 어둠 길이를 보지 않는다)
- 감독 지시: 어둠 길이는 음악이 정한다 → 늘리지 않고 경고만

## 0. 요약

| 항목 | 판정 |
|---|---|
| 조립기 사전이동에 어둠 길이 측정 | 🟢 `CueMibData.dark_window_seconds` = (켜지는 큐 시작 − 사전이동이 따라가는 앞 큐 시작) / 1000 |
| 모자라면 경고 | 🟢 `< resolver.MOVE_SECONDS + SETTLE_SECONDS`(4.6초)이면 `live_move=True`, 사유에 REQ-066 `live_move_note()` + 「어둠 N초 < 필요 4.6초」 |
| 어둠 늘리기 | 🟢 **하지 않음** — 사전이동 큐는 그대로 들어가고, 켜지는 큐 시각도 바뀌지 않는다(테스트로 고정) |
| `server/spatial/mib.py` `DEFAULT_MOVE_SECONDS 1.0`과의 관계 | ⚪ **합치지 않음** — §2 |
| 8곡 게이트 | 🟢 `PASS 75 · n/a 29 · FAIL 0` 유지 |
| 감독 화면 표시 | 🔴 **아직 안 보임** — 후속 제안 §4 |

## 1. 변경

`server/design/song_cue_composer.py`
- `CueMibData`에 `dark_window_seconds: float | None = None`과 `live_move: bool = False`를 추가하고 `to_dict()`에도 넣었다. `live_move`는 bool인지 검증한다
- `_apply_mib`가 앞 큐의 `timing.start_ms`를 추적하고, `_premove_window_seconds()`로 창을 잰다. 둘 중 하나라도 시각이 없으면 `None`(재지 못함)으로 두고 경고하지 않는다 — 부재는 「문제없음」의 증명이 아니므로 값 자체를 `None`으로 남긴다
- `_mib_premove`: 기준은 `server.concept.resolver.MOVE_SECONDS + SETTLE_SECONDS` — 컨셉 판정기(G12)와 **같은 상수 한 곳**을 쓴다. 문구는 `server.concept.mib.live_move_note()`를 재사용했다
- 새 import `server.concept.resolver`·`server.concept.mib`는 `server/concept` 내부만 가져다 쓴다(`resolver`→`cue_model`·`vocab`, `mib`→`resolver`·`cue_model`, `__init__` 비어 있음). 순환 참조 없음 — 아키텍처 테스트 포함 관련 테스트가 통과했다

`server/tests/test_song_cue_composer.py` `TestComposerMibDarkWindow` (5건)
- 어둠 2.0초 → `live_move=True`, 사유에 `live_move`, **켜지는 큐 `start_ms` 2000 그대로**, 사전이동 포지션 그대로
- 10초 → 경고 없음
- 문턱: 정확히 4.6초 → 경고 없음 / 0.1초 짧으면 → 경고 (상수를 import해서 계산하므로 상수가 바뀌면 따라간다)
- t464 실측 부족값 2.07초 → 경고
- `to_dict()`에 두 키가 실린다

## 2. `DEFAULT_MOVE_SECONDS 1.0`과 `MOVE_SECONDS 4.1` — 합치지 않는 이유

| 상수 | 뜻 | 쓰는 곳 |
|---|---|---|
| `server/spatial/mib.py` `DEFAULT_MOVE_SECONDS = 1.0` | 사전이동 큐 **자체의 포지션 페이드** 시간 | 공간 경로 사전이동 큐 |
| 조립기 `_mib_premove` `fade_seconds=1.0` | 같은 뜻(사전이동 큐의 페이드) — 리터럴 | 곡 큐 조립기 |
| `server/concept/resolver.py` `MOVE_SECONDS = 4.1` (+ `SETTLE_SECONDS 0.5`) | 사전이동이 **다 끝나는 데 필요한 어둠 길이** | 컨셉 판정기 G12, 이제 조립기 경고 |

- 페이드 1초는 「값이 1초에 걸쳐 바뀐다」는 뜻이고, 4.1초는 「기구가 실제로 도착하기까지 필요한 시간」이다(t464: 페이드 설정과 무관하게 60° 이동에 2.07초는 부족). 서로 다른 양이라 하나로 모으면 뜻이 틀어진다
- 두 페이드 1.0(공간 상수와 조립기 리터럴)은 같은 뜻이지만, 모으려면 조립기가 `server.spatial.mib`(→ `server.spatial.pointing`)를 가져와야 한다. 이번 카드의 경고 목적과 무관해서 건드리지 않았다

## 3. 증거

| 확인 | 명령 | 결과 |
|---|---|---|
| RED | `uv run pytest server/tests/test_song_cue_composer.py -k TestComposerMibDarkWindow -q` | `5 failed` — `pytest_red.txt` |
| GREEN | `uv run pytest server/tests/test_song_cue_composer.py -q` | `13 passed` — `pytest_green.txt` |
| 관련 테스트 | `uv run pytest -q server/tests -k "song_cue or composer or session or runbook or timeline or concept or mib or architecture or songcue"` | `1793 passed, 24 skipped` — `pytest_affected.txt` |
| 8곡 게이트 | `uv run python .moai/reports/t444/gen_gates_8songs.py` | `PASS 75 · n/a 29 · FAIL 0` — `gates_8songs_after.txt` |
| 린트 | `ruff check` / `ruff format --check` (고친 두 파일) | 통과 |
| 새 키를 고정하는 소비자 | `git grep source_cue_number -- ui src src-tauri docs server` | 조립기 밖 0건(`server/looks/songcue.py`의 같은 이름은 다른 레코드) |

## 4. 후속 제안 (범위 밖)

- **감독 화면에 경고가 안 보인다.** 런북 MIB 칸(`ui/src/components/runbookM7.ts` `mibCellText`)은 `section.mib`(bool: 사전이동 큐가 있는가) 하나만 보고 「사전이동 있음」을 띄운다. `live_move`는 조립기 데이터에만 있다. 제안: `server/web/session.py`의 구간 payload(`"mib": … in mib_section_indexes`, 2486행 근처)에 `live_move`를 싣고, UI는 「⚠ 어둠 N초 — 켜진 채 이동」처럼 표시

## 5. 안 잰 것 (Gaps)

- **실제 곡에서 경고가 몇 건 뜨는지**: 저장소의 8곡 기준선은 컨셉 판정기 입력이고 조립기 입력(`UnifiedSongLightingPlan`)이 아니다. 조립기를 실제 곡에 돌린 산출물이 없어서 재지 못했다
- `manual_go` 모드: 창은 곡 시각(`start_ms`)으로 재지만, 실제로는 조작자가 Go를 누르는 시점에 달렸다. 경고는 「곡 시각대로 누르면 모자란다」는 뜻이다
- 사전이동 큐 자체(페이드 1초 + 기구 속도)의 실제 도착 시간 — t468과 같은 한계(4.1초는 콘솔 자체 MIB 실측을 옮긴 값)
