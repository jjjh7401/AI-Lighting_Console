# t468 — SPEC-LDDESIGN-001 §F MIB 잠정값 확정·방출 점검 (lane-1)

- 브랜치 `WT-mib-timing` · 기준 `origin/main@7871767c` · 콘솔 쓰기 0
- 입력: `.moai/reports/t464/verdict.md` §3b (Spiider 팬 60°, onPC, 콘솔 자체 MIB `SEQUMIBMODE Early`: 어둠 2.07초 부족, 4.05초 충분)

## 0. 요약

| 항목 | 판정 | 근거 |
|---|---|---|
| ① 우리 MIB가 콘솔 MIB에 기대는가 | 🟢 **기대지 않는다** | §1. 두 경로 모두 어둠 속에 사전이동 큐를 직접 넣는다. `SEQUMIBMODE` 방출 0곳 |
| ② 시퀀스 생성 시 `SEQUMIBMODE Early` 방출 | ⚪ **하지 않음(불필요)** | ①이 근거. 켜면 우리 사전이동 큐와 콘솔 MIB, 옮기는 쪽이 둘이 된다 |
| ③ §F 이동 시간 교체 + 모자란 어둠 경고 | 🟢 **교체** `MOVE_SECONDS` 1.5→**4.1**, Mark 삽입 상한 4.0→`MOVE_SECONDS` | §2. RED→GREEN, 8곡 게이트 기준선 불변 |
| ④ plan §F·spec REQ-062 문구 | 🟢 manager-spec이 정정 | §3 |
| 곡 큐 조립기 어둠 길이 검사 | 🔴 **없음 — 범위 밖, 새 카드 제안** | §4 |

## 1. 판독 (코드, 읽기 전용)

- `git grep -i "SEQUMIBMODE|MIBMode|SEQUMIB" -- server` → **0건**
- 컨셉 판정기 `server/concept/mib.py` + `resolver.mib_verdict`: `dark`/`mark`/`live` 판정만 한다. `mark`면 REQ-063 Mark 큐(포지션만 변경, 밝기 0)를 쓰도록 설계됐다(`mark_cue_spec`). 이 판정은 콘솔 MIB를 전제하지 않는다
  - 소비처: `gates.py:453` `compute_mib_sequence` → G12 `g12_mib_no_live_moves`(live 1건이라도 있으면 FAIL), `session_bridge.py` 보고. `mark_cue_spec`·`resolve_position`의 생산 코드 호출처는 0곳이다(테스트에서만 쓴다)
- 곡 큐 조립기 `server/design/song_cue_composer.py` `_apply_mib`: 어둠 → 새 포지션으로 켜지는 큐 앞에 `mib_premove` 큐를 직접 끼운다(`fade_seconds=1.0`, `trigger="follow_previous"`, 번호는 중간값)
- 공간 경로 `server/spatial/mib.py` `apply_mib`: 같은 방식이다(`DEFAULT_MOVE_SECONDS = 1.0`, `TrigType 'Follow'`)
- 결론: 세 경로 모두 **명시적 사전이동 큐** 방식이다. 콘솔 기본값 `SEQUMIBMODE None`(t464 실측)이어도 동작에 영향이 없다 → ②는 하지 않는다

## 2. 변경 (③)

`server/concept/resolver.py`
- `MOVE_SECONDS: 1.5 → 4.1` (실측 충분값 4.05초 이상인 0.1초 격자값. `window`가 0.1초로 반올림되기 때문)
- `mark_insert_at = ts - min(window - 0.5, 4.0)` → `ts - min(window - SETTLE_SECONDS, MOVE_SECONDS)`
  - 옛 상한 4.0초는 실측 4.05초보다 짧다. 긴 어둠에서도 Mark 큐가 켜지는 큐보다 4.0초만 앞섰다
  - 리터럴 0.5는 같은 값의 `SETTLE_SECONDS`로 바꿨다
- 결과: `mark` 문턱 2.0초 → **4.6초**. 이보다 짧은 어둠의 포지션 변경은 `live`(G12 경고)로 판정된다. 감독 지시(어둠 길이는 음악이 정한다)에 따라 어둠을 늘리는 경로는 없다

`server/concept/evidence.py`: 주석만 고쳤다. `EVIDENCE_FOR_MIB_TIMING = "designed_rule"`은 유지한다(실측이 콘솔 자체 MIB 기준이고, 기구 1종·onPC 1회라서)

`server/tests/test_concept_resolver.py` `TestMibTimingMeasured` (5건)
- 2.07초 창 → `live`
- 창 {문턱, 6.0, 40.0} → `mark`이고 `ts - mark_insert_at ≥ 4.05`
- 대조: Mark 큐가 어둠이 열리기 전에 나가지 않는다(`mark_insert_at ≥ ts - window`)

### 증거

| 확인 | 명령 | 결과 |
|---|---|---|
| RED (변경 전 코드) | `uv run pytest server/tests/test_concept_resolver.py -k MibTimingMeasured -q` | `4 failed, 1 passed` — `pytest_red.txt` (예: `assert (100.0 - 96.0) >= 4.05`) |
| GREEN | `uv run pytest server/tests/test_concept_resolver.py server/tests/test_concept_mib.py -q` | `62 passed` — `pytest_green.txt` |
| 관련 테스트 | `uv run pytest -q server/tests -k "concept or pilot or gate or session_bridge or mib or runbook"` | `1208 passed, 22 skipped` — `pytest_affected.txt` |
| 빠른 묶음 | `make test-fast` | exit 0 (이 목표는 성공 시 아무것도 출력하지 않는다) |
| 8곡 게이트 행렬 | `uv run python .moai/reports/t444/gen_gates_8songs.py` | `PASS 75 · n/a 29 · FAIL 0` — `gates_8songs_after.txt`. main의 `t444/gates_8songs.txt`와 같다 |
| 문턱 스윕 | `uv run python .moai/reports/t468/mib_threshold_sweep.py` | 문턱 2.0/2.1/4.1초 모두 G12 8/8. **양성 대조 100초 → 3/8**(바꿔 끼운 값이 실제로 읽힌다). 8곡 mark 어둠 창 최소 13.0초 — `mib_threshold_sweep.txt`, `_after.txt` |
| 린트 | `uv run ruff check` / `ruff format --check` (고친 파일 전부) | 통과 |

## 3. SPEC 문구 (④, manager-spec)

- `spec.md` REQ-LDDESIGN-062: 「plan.md §F 잠정값 — 이동 1.5초 + 정착 0.5초, M8 콘솔 프로브로 실측치 교체 예정」 → 「이동 4.1초 + 정착 0.5초, M8 실측 t464 — plan.md §F」. 근거 열에 `.moai/reports/t464/verdict.md`를 추가했다
- `plan.md` M5 항목, §E 체크 항목(체크는 하지 않고 「t468로 교체 완료」 주석만 추가), §F 항목: 실측값, 측정 조건, 한계(콘솔 자체 MIB·1종·1회), `designed_rule` 유지, SEQUMIBMODE 방출 불필요를 적었다
- 문구를 고정하는 테스트: `git grep "SPEC-LDDESIGN-001/(spec|plan).md" -- server/tests tools` → 0건

## 4. 범위 밖 — 새 카드 제안 (리드에게)

- **곡 큐 조립기 `_apply_mib`는 어둠 길이를 보지 않는다.** 조건은 `dark and 포지션 변경 and 켜짐`뿐이다. 어둠이 0.5초여도 `mib_premove`(페이드 1초)를 끼우고 아무 경고도 없다. 실제 콘솔로 나가는 쪽은 이 조립기다. 컨셉 판정기(G12)의 경고가 이 경로에는 닿지 않는다
- 제안: 조립기가 `reveal.start_ms - dark_cue.start_ms`를 `resolver.MOVE_SECONDS + SETTLE_SECONDS`와 비교해, 모자라면 `CueMibData`에 경고(REQ-066 `live_move`)를 싣는다. 공간 경로 `DEFAULT_MOVE_SECONDS = 1.0`(Mark 큐 자체의 페이드)과의 관계도 함께 정리한다

## 5. 안 잰 것 (Gaps)

- 우리가 넣는 **Mark/사전이동 큐 자체**의 이동 완료 시간 — 콘솔에서 재지 않았다(이 카드는 콘솔 쓰기 없음). 4.1초는 콘솔 자체 MIB 실측을 옮긴 값이다
- 다른 기구, 다른 이동 각도, 실기 콘솔 — t464와 같은 한계
- 문턱 4.6초가 실제 곡에서 경고를 얼마나 늘릴지 — 8곡에서는 0건(최소 창 13초)이지만, 어둠이 짧은 곡에는 영향이 있다
- `mark_insert_at` 값이 바뀐 곡의 화면(UI)·런북 표시 — 긴 창에서 Mark 시각이 0.1초 앞당겨진다. 그 값을 고정하는 테스트는 관련 테스트 1208건 중에 없었다
