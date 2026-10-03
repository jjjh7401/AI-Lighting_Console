# 카드 t501 — SPEC-LDRENDER-001 M3 후속 보고 (climax_return 큐 role 줄)

작성: lane (worktree `agent-a25cfae2cf937299a`)
범위: M4 보고서(`.moai/reports/t501/M4.md`) §4 Gaps 1 이 보고한 결함 —
climax_return 큐가 role별 디머/색 줄을 하나도 못 내서 AC-LDRENDER-001 이
곡마다 1개씩(8/120, 6.7%) FAIL 하는 문제를 닫는다.

## 1. 주장 (Claim)

1. **원인(코드 판독, 1회성 진단 재검증)**: `_song_color_value_lines`·
   `_role_color_value_lines`·`_role_dimmer_value_lines`·`_white_palette_name`
   네 함수 전부 `cue.kind != "section"`이면 아무 줄도 안 내는데,
   `position_cue_bundle`(`server/spatial/mib.py:143-181`)의 전체 기구
   키 디머 줄은 kind 와 무관하게 항상 나간다 — climax_return 큐에서 전체
   기구가 `key_pct` 하나로 재동기화되고, 그 재동기화를 바로잡을 role 델타
   줄이 없어 `ldrender_gate.layer_diversity`의 LIT 버킷이 무너진다.
2. **수정**: 네 함수가 공유하는 kind 허용집합을 `frozenset({"section",
   "climax_return"})`(명시 열거, `!=` 반전 금지)로 넓혔다 — `_climax_
   return()`(`song_cue_composer.py:1024-1049`)가 `dataclasses.replace`로
   climax 큐를 복제할 때 `dimmer`/`color` 필드를 교체 인자로 **주지
   않으므로**(원본 참조 그대로 남는다), climax_return 에도 role 줄을 내는
   것은 climax 큐 자신이 이미 가진 값을 재사용하는 것이지 새 값을 발명하는
   게 아니다. 블랙아웃(`cue.dimmer.blackout`)과 `mib_premove`는 이 허용집합
   밖에 그대로 남아 acceptance.md AC-001 의 명시 예외를 보존한다.
3. **측정**: AC-001 이 120개 구간 큐 전부(8곡, 14+18+8+14+13+24+18+11)에서
   PASS 한다(고치기 전 112/120, 93.3% — M4 측정값). 색(AC-004)·디머-전용
   집계는 이 수정으로 **달라지지 않는다**(변화-없음을 기대하고 재측정 —
   리드 예측 "층 대비는 색, 밝기 대비는 R5 이월"이 그대로 지켜진다).

## 2. 증거 (Evidence)

### 2.1 kind 결정의 근거 — `_climax_return()` 인용

```python
# song_cue_composer.py:1024-1049
def _climax_return(climax: ComposedCue, *, cue_number: float, cap_ms: int) -> ComposedCue:
    return dataclasses.replace(
        climax,
        kind="climax_return",
        cue_number=cue_number,
        cue_name=f"{climax.cue_name} Return",
        fade_seconds=0.0,
        position=dataclasses.replace(climax.position, stored=None),
        fx=CueFxData(requested=(), permitted=(), disabled=(), density=0, axis_budget=0),
        accents=(),
        accent_fixture=None,
        pre_drop_from=None,
        mib=CueMibData(),
        timing=dataclasses.replace(...),
    )
```

`dimmer`/`color`가 교체 인자 목록에 없다 — `dataclasses.replace`의미론상
원본 참조 그대로 남는다. `position`은 `stored=None`으로 명시 변경(재송신
안 함, 변경 없음), `fx`는 명시적으로 빈 값 교체(복사가 아니다).

### 2.2 수정 지점 (4곳, 공유 상수 하나)

```
$ grep -n "_ROLE_VALUE_LINE_KINDS\|cue.kind not in _ROLE_VALUE_LINE_KINDS" server/design/song_cue_render.py
588:_ROLE_VALUE_LINE_KINDS: frozenset[str] = frozenset({"section", "climax_return"})
594:    if cue.kind not in _ROLE_VALUE_LINE_KINDS or not cue.color.palette:
643:    if cue.kind not in _ROLE_VALUE_LINE_KINDS or len(palette) < 2:
725:    if cue.kind not in _ROLE_VALUE_LINE_KINDS:
815:    if cue.kind not in _ROLE_VALUE_LINE_KINDS:
```

### 2.3 진단 — 실패 원인 실측 (Club Diver 큐 12/12.5, 1회성 조회)

M4 §Gaps 1 의 가설("FOH 가 베이스라인을 들고 있어서")을 착수 전 직접
`role_view` 를 찍어 대조했다(스크립트는 쓰고 지웠다 — 아래는 그 출력
인용):

```
cue 12 (section, 고치기 전/후 동일):     layer_diversity = 4
  back/mover : dim=80  rgb=Blue(5,20,100)
  side/wash  : dim=80  rgb=WarmWhite(100,75,40)
  key        : dim=100 rgb=Blue 또는 WarmWhite(물리적으로 KEY+FOH 혼재)
  effect     : dim=80(점등) rgb=Blue

cue 12.5 (climax_return, 고치기 전): layer_diversity = 2
  back/mover : dim=100(전체 기구 재동기화) rgb=Blue
  side/wash  : dim=100(전체 기구 재동기화) rgb=WarmWhite
  key        : dim=100 rgb=Blue 또는 WarmWhite  → back/mover·side/wash 와 병합(dim 도 100 으로 같아짐)
  effect     : dim=0(블라인더 꺼짐, LIT 아님)
```

**정정**: 진짜 원인은 "색이 사라져서"가 아니라 "디머가 유일한 분기 축이던
자리에서 재동기화로 평평해지자, 우연히 같은 색을 공유하던 역할들이 버킷에서
병합됐다"이다 — 색은 콘솔 트래킹으로 애초에 멀쩡히 보존돼 있었다.

```
cue 12.5 (climax_return, 고친 뒤): layer_diversity = 4  (cue 12 와 바이트 동일)
```

### 2.4 AC-001 재측정 (8곡, 기존 스크립트 재사용 — DSP 재실행 없음)

```
$ uv run python .moai/reports/t501/run_climaxfix_measurements.py
Club Diver: 구간 큐 14개 · LIT≥3 14개 · LIT<3 0개 · 색 4종 · 효과줄 0 · 경고 YES
Cut and Run: 구간 큐 18개 · LIT≥3 18개 · LIT<3 0개 · 색 3종 · 효과줄 0 · 경고 YES
Ice cream: 구간 큐 8개 · LIT≥3 8개 · LIT<3 0개 · 색 4종 · 효과줄 0 · 경고 YES
Morning: 구간 큐 14개 · LIT≥3 14개 · LIT<3 0개 · 색 3종 · 효과줄 0 · 경고 YES
Rain: 구간 큐 13개 · LIT≥3 13개 · LIT<3 0개 · 색 3종 · 효과줄 0 · 경고 no
Too Cool: 구간 큐 24개 · LIT≥3 24개 · LIT<3 0개 · 색 4종 · 효과줄 0 · 경고 YES
scott-buckley-neon: 구간 큐 18개 · LIT≥3 18개 · LIT<3 0개 · 색 4종 · 효과줄 0 · 경고 YES
걸그룹DinoDino_C_max최고품질: 구간 큐 11개 · LIT≥3 11개 · LIT<3 0개 · 색 4종 · 효과줄 0 · 경고 YES
```

**8곡 전체 before→after**

| 곡 | before(M4) LIT≥3/전체 | after(이 카드) LIT≥3/전체 |
|---|---|---|
| Club Diver | 13/14 | **14/14** |
| Cut and Run | 17/18 | **18/18** |
| Ice cream | 7/8 | **8/8** |
| Morning | 13/14 | **14/14** |
| Rain | 12/13 | **13/13** |
| Too Cool | 23/24 | **24/24** |
| scott-buckley-neon | 17/18 | **18/18** |
| 걸그룹DinoDino | 10/11 | **11/11** |
| **합계** | **112/120(93.3%)** | **120/120(100%)** |

남은 경고(색 수 4개·효과 송신 0줄)는 AC-001 과 무관한 M4 §Gaps 2/M6 영역
(이 카드 범위 밖) — AC-001 자체(LIT 층 3 미만 경고)는 8곡 전부 자취를
감췄다.

**디머-전용 대조(변화 없음을 기대, 확인됨)**: 8곡 전부 디머전용 최대버킷
여전히 2, `>=3`인 큐 0개 — M4 측정값과 바이트 동일. 전체상태(색+디머)
최소버킷만 2(climax_return 이 끌어내린 값)→4(climax 큐와 동일하게 복원)로
올랐다.

**AC-004 대조(변화 없음을 기대, 확인됨)**: 8곡 전부 고유 RGB 수·색변화
횟수·역할별 수신 색 확인(`back==dominant`·`side==accent`·`key==warmwhite`
전부 `True`)이 M4 측정값과 바이트 동일.

산출물: `.moai/reports/t501/ac001_8songs_climaxfix.{json,txt}`,
`dimmer_only_8songs_climaxfix.json`, `ac004_8songs_climaxfix.json` — M4 가
저장한 원본(`_climaxfix` 접미사 없는 동일 이름 파일)은 변경하지 않았다
(`git status --short .moai/reports/t501/`로 확인, `M` 표시 없음).

### 2.5 테스트 — 신규 `server/tests/test_song_cue_climax_return_t501.py` (15개)

```
$ PYTHONDONTWRITEBYTECODE=1 uv run pytest server/tests/test_song_cue_climax_return_t501.py -q
...............
15 passed in 0.19s
```

두 축 — 대역(stub) 11개(네 함수 각각 "climax_return 이 section 과 같은
줄" + "mib_premove 는 여전히 무 — 두 팔" + 블랙아웃 가드 보존 1건) +
`compose_song_cue_bundle` 실조립 통합 4개.

### 2.6 뮤테이션 (5건, §3.3 축 분리 규율)

| # | 변조 | 대상 | 죽은 테스트 수 |
|---|---|---|---|
| A | `_ROLE_VALUE_LINE_KINDS={"section"}`(climax_return 제거, 네 함수 동시) | `:588` | 7 |
| B | `_role_dimmer_value_lines` 가드만 되돌림 | `:815` | 2 |
| C | `_song_color_value_lines` 가드만 되돌림 | `:725` | 3 |
| D | `_white_palette_name` 가드만 되돌림 | `:594` | 1 |
| E | `_role_color_value_lines` 가드만 되돌림 | `:643` | 3 |

5건 전부 `PYTHONDONTWRITEBYTECODE=1`, 매 회차 `diff`로 변조 적용→복원→
무차이 확인 두 번씩, 각 뮤테이션이 정확히 그 축의 테스트만 죽였다(B/D 가
독립적으로 정확한 카디널리티를 내 축이 분리돼 있음을 교차 확인).

### 2.7 회귀 + 전체 스위트

```
$ PYTHONDONTWRITEBYTECODE=1 uv run pytest server/tests/test_layer_mapping_effect_role.py server/tests/test_layer_mapping_foh_front.py server/tests/test_design_rig.py server/tests/test_song_cue_color_emission.py server/tests/test_song_cue_white_preset_t453.py server/tests/test_seeded_song_apply.py server/tests/test_song_cue_composer.py server/tests/test_song_cue_arc_t462.py server/tests/test_song_cue_role_dimmer_t501.py server/tests/test_song_cue_role_color_t501.py server/tests/test_ldrender_gate.py server/tests/test_web_session.py server/tests/test_dedupe_value_lines_t476.py server/tests/test_song_readback_props_t479.py server/tests/test_song_cue_climax_return_t501.py -q
646 passed in 5.98s

$ PYTHONDONTWRITEBYTECODE=1 uv run pytest server/tests -q -p no:cacheprovider
14456 passed, 35 skipped in 233.67s
```

지정 범위 631→646(+15), 전체 스위트 14441→14456(+15) — 둘 다 신규 테스트
수와 정확히 일치(삭제 0·교체 0·FAIL 0, skipped 35 불변).

### 2.8 린트/포맷

```
$ uv run ruff check server/design/song_cue_render.py server/design/song_cue_composer.py server/tests/test_song_cue_climax_return_t501.py .moai/reports/t501/run_climaxfix_measurements.py
All checks passed!
$ uv run ruff format --check <동일 목록>
4 files already formatted
```

## 3. baseline 귀속 (Baseline-attribution)

- **착수 베이스라인**: `git fetch origin WT-ldrender-run` →
  `git merge --ff-only origin/WT-ldrender-run` → HEAD `61b1695b`(M4 완료
  커밋, `git log --oneline -1`로 확인).
- **지정 범위 회귀 베이스라인**: M4 보고서(`.moai/reports/t501/M4.md`
  §2.8)가 직접 잰 `631 passed`(이 카드가 재확인용으로 재실행하지는
  않았다 — M4 가 같은 커밋에서 직접 잰 값을 인용).
- **전체 스위트 베이스라인**: M4 보고서 §2.8 기록값 `14441 passed, 35
  skipped`(이 역시 M4 가 같은 커밋 `61b1695b`에서 직접 잰 값을 인용). 이
  카드 종료 시점 `14456 passed, 35 skipped`(§2.7, 직접 측정).

## 4. 미검증 (Gaps)

1. **AC-004(a) 웜화이트 집계 플래그(M4 §Gaps 2)는 그대로 미해소** — 이 카드
   범위 밖(배차서가 climax_return 결함만 지시).
2. **M6(효과 송신)·M5(effect 기구 분리)는 여전히 미착수** — 범위 밖.
3. **진단 스크립트는 저장하지 않았다** — 착수 전 1회성 조회(§2.3), 재사용
   하네스로 남기지 않음(M4 의 "상태 키 실측 증거"와 같은 선례).
4. **원곡 오디오 직접 재현 없음** — M3/M4 와 동일한 이 워크트리 제약
   (mp3/wav 0건) 계승.
5. **W 채널(`w_fids`)이 있는 리그에서의 climax_return 흰색 프리셋 recall 은
   실측 대상이 아니었다** — 8곡 측정에서 `w_fids` 가 항상 비어
   `_white_palette_name`의 climax_return 분기가 호출되지 않는다(코드
   판독: `server/web/session.py:7604-7613`, 합성 리그가 W 능력을 선언받지
   못함). 단위 테스트(`TestStubLevelWhitePaletteName`)로만 확인했고,
   `compose_song_cue_bundle`→`reviewed_song_commands` 종단 경로로 W 채널이
   있는 합성 리그를 돌리는 새 테스트는 추가하지 않았다.
6. **`_role_color_value_lines`를 kind 허용집합에 포함한 결정의 측정상
   효과는 0이다** — 이 8곡에서는 `_song_color_value_lines`가 내부 호출로
   이미 역할 색 델타를 끌어내므로, `_role_color_value_lines` 자신의 가드를
   단독으로 열었을 때의 차이는 단위 테스트(§2.6 뮤테이션 E)로만 확인했고
   8곡 측정의 수치 변화로는 분리 관측되지 않는다(C·E 가 같은 테스트를
   함께 죽인다는 것 자체가 이 결합을 보여준다, §2.6 설명 참조).

## 5. 잔여 위험 (Residual-risk)

- **"climax_return 이 전체적으로 climax 큐와 byte-identical 하다"는 이
  카드의 핵심 전제가 깨지는 미래 변경**(예: `_climax_return()`이 `dimmer`/
  `color`를 다시 계산하도록 바뀌는 경우)에서는 이 카드가 추가한 역할별
  델타 재사용이 **낡은 값**을 다시 내보낼 위험이 있다 — `test_climax_
  return_dimmer_and_color_are_the_same_object_as_the_climax_cue`가 `is`
  동일성을 직접 단언해 두어 그 전제가 깨지면 테스트가 먼저 빨개지도록
  했지만, 실기 연출 의미(복귀 큐에서 색이 **바뀌어야** 하는 경우가 생기면
  이 가정 자체를 재검토해야 한다)는 여전히 사람 판단의 몫이다.
- **8곡 표본 바깥의 리그(2-역할 잔여 리그, W 채널 보유 리그)에서 이 수정이
  같은 효과를 내는지는 측정하지 않았다** — acceptance.md 가 이미 플래그한
  "2-역할 잔여 리그는 구조적으로 LIT 3 에 도달 못한다"는 경계는 climax_
  return 에도 동일하게 적용될 것으로 추론되지만(§Gaps 5), 직접 재지
  않았다.
- **실기 육안 확인 없음** — AC-LDRENDER-016(사람 판정)은 이 카드의 범위가
  아니다. "복귀 큐에서 디머가 순간적으로 치솟는다"던 M4 §5 의 잔여 위험
  서술은 이 카드로 **기계 측정상** 해소됐지만(복귀 큐도 climax 큐와 같은
  role 디머 값을 받는다), 실기에서 체감이 달라지는지는 여전히 확인되지
  않았다.
