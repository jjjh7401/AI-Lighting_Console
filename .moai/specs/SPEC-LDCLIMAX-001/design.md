# SPEC-LDCLIMAX-001 기술 설계

대상 파일: `server/looks/songcue.py`(경로 B — research.md §2). 이 파일은
"무엇을 어떻게 구현할지"의 스케치다 — 정확한 함수 시그니처·삽입 위치는 run
phase 에서 확정한다(이 문서는 착수 지점을 좁히는 용도이지 최종 코드가
아니다).

## 1. 데이터 모델 — 가장 되돌리기 비싼 결정

### 1.1 색 스냅 사다리 칸 (감독 결정 2026-09-20 반영 — plan.md §NC 해소)

```python
LADDER_COLOR_SNAP = "color_snap"
```

`_MARKING_ACCENTS` **상수 튜플 자체**(기존 줌→블라인더→아이리스)에는
더하지 않는다 — 연구 §4 결정, 유지. 대신 `_marking_accents`
(songcue.py:260) 시그니처에 `disable_color_snap: bool = False` 를
`allow_strobe` 와 나란히 추가하고, **거짓(기본값)이면** 후보 튜플 끝
(strobe 후보 뒤, `allow_strobe` 가 참이면)에 `LADDER_COLOR_SNAP` 을
**무조건** 덧붙인다 — 참일 때만 붙이던 이전 판(`allow_color_snap`)과
극성이 반대다.

순서(맨 끝)는 감독이 2026-09-20 에 확정한 연출 우선순위다 — zoom_pinch/
blinder_or_flash/iris_pinch/strobe_hit 와 같은 자격이되 이 넷보다
우선하지 않는다(plan.md §NC). 이전 판의 "최소 침습이라 잠정으로 맨 끝"
이라는 엔지니어링 근거는 폐기됐지만, 배치 자체("맨 끝")는 감독 결정과
일치해 그대로 유지한다.

**임시 안전판(`disable_color_snap`)**: 이 인자가 참이면 `color_snap` 을
후보에서 제외한다 — 첫 실기 콘솔 검증 세션까지의 킬스위치이며(REQ-012),
자동 회전을 켜는 스위치가 아니다. 그 세션이 통과하면(또는 발견된 결함이
후속 수정으로 닫히면) 이 인자는 후속 커밋에서 제거한다 — `allow_strobe`
처럼 영구히 남기지 않는다.

**`songcue.py:109-110` 배제 독스트링**은 이 결정으로 갱신한다 — "색
스냅도 뺀다..." 두 줄을 이 SPEC 의 정의(§7 이 요구하는 되돌아오는 색을
즉시 전환하는 것은 §7 위반이 아니다)로 교체하고 SPEC-LDCLIMAX-001 을
인용한다(plan.md M2, §B6).

**`_accent_is_effective` 의 dispatch 확장**: 오늘 이 함수는 축-보유
(`_MARKING_ACCENT_AXIS`)와 그룹-보유(`_ACCENT_FIXTURE_ROLE`) 두 갈래뿐이고
나머지는 `SongCueBundleError` 를 던진다(`songcue.py:204-221`). `color_snap`
은 어느 쪽도 아닌 **색 비교**(§7 집합 안인지, 직전 저장 큐와 다른지)라는
셋째 분기가 필요하다(REQ-002/004, plan.md §B5).

**`LADDER_RUNGS` 포함**: `color_snap` 은 strobe 와 반대 극성(기본 활성)
이므로 zoom/iris/blinder 처럼 `LADDER_RUNGS`(songcue.py:124-129)에
포함하는 것이 이 상수의 기존 구분 기준("기본으로 도는 칸" vs "호출자
플래그로 꺼진 채 시작하는 칸")과 일관적이다. 이 갱신은
`test_every_ladder_rung_is_classified`(`test_songcue_ladder.py:470`)의
`_MARKING` 튜플 갱신과 짝을 이룬다(plan.md §B7).

### 1.2 절정 지속시간 상한 — 복귀 큐

```python
@dataclass(frozen=True)
class SongCueClimaxReturn:
    """절정 지속시간 상한이 끼워 넣은 복귀 큐 — 어느 절정 큐 뒤에, 몇 박
    뒤에, 무슨 이유로 삽입됐는지(REQ-LDCLIMAX-010).

    SongCueWithheldMovement/Darkness/Accent(SPEC-LDACCENT-001) 와 같은
    "조립 중에만 아는 부가 사실을 명시적으로 보고한다" 패턴을 따르되,
    이것은 유보가 아니라 **삽입** 보고라 별도 클래스로 둔다.
    """

    source_section: SongCueSection
    source_cue_number: int
    rung: str  # LADDER_BLINDER_OR_FLASH 또는 LADDER_STROBE_HIT
    cap_beats: float  # 2.0 또는 4.0
    inserted_cue_number: int
    inserted_start_ms: int
```

`SongCueBundle`(609행)에 `climax_returns: tuple[SongCueClimaxReturn, ...] =
()` 필드를 더한다 — `withheld_movement`/`withheld_darkness`/
`withheld_accents` 와 같은 자리, 같은 집계 패턴(`build_songcue_bundle` 이
섹션 전량에서 걷는다).

**큐 번호**: `SongCueSectionBundle.cue_number: int` 는 정수 고정(research.md
§3)이므로, 복귀 큐는 **뒤따르는 모든 큐의 번호를 1씩 미는** 재번호 매기기가
필요하다 — 소수점 큐 번호(`10.5`)를 새로 도입하지 않는다(이 파일 전역의
`int` 계약을 이 SPEC 하나가 깨는 것을 피한다). 재번호는 후처리 패스
마지막 단계에서 한 번에 수행하고, `_cue_names`(호출부 확인 필요)가 이름도
같은 순서로 다시 부여하는지 run phase 에서 검증한다.

## 2. 후처리 패스 — 조립 이후, 별도 함수

```python
def _apply_climax_duration_cap(
    bundle: SongCueBundle,
    *,
    bpm: float | None,
    meter: object = "4/4",
) -> SongCueBundle:
    """완성된 번들을 훑어 blinder_or_flash/strobe_hit 를 실은 큐마다 상한을
    계산하고, 다음 큐가 상한보다 늦게 오면 그 사이에 복귀 큐를 끼운다.

    bpm 이 None 이면 아무것도 하지 않는다(REQ-LDCLIMAX-009, cue_density.py
    의 "안 재고는 안 쓴다" 규율과 같은 방향) — 입력 그대로 반환.
    """
```

호출 위치: `build_songcue_bundle` 의 마지막 반환 직전(875행 함수 끝) —
사다리·프론트필·움직임·감광이 전부 확정된 뒤에만 "이 큐가 실제로
blinder_or_flash/strobe_hit 를 실었는가"를 알 수 있으므로, 조립 도중이
아니라 조립 **후**에 한 번 더 훑는다. 이렇게 하면 SPEC-LDACCENT-001 이
경고한 "여러 호출자에 컨텍스트를 빠짐없이 배선해야 하는" 취약점(그 SPEC
§B1)을 반복하지 않는다 — 새 함수 하나가 완성된 결과만 읽고 쓴다.

### 2.1 알고리즘 스케치

1. `bundle.sections` 를 순서대로 훑는다.
2. 각 섹션 번들의 `accent_fixture`(SongCueAccentFixture, songcue.py 근방
   555행)를 본다 — `rung` 이 `LADDER_BLINDER_OR_FLASH` 또는
   `LADDER_STROBE_HIT` 이면 절정 큐다.
3. `cap_beats = 2.0 if rung == LADDER_BLINDER_OR_FLASH else 4.0`
   (research.md §4 — §6 "백색 플래시"/"최강 효과" 두 행의 상한 값 각각의
   **상한 끝**을 채택한다. 범위의 정확히 어느 지점이 아니라 범위의 끝을
   쓰는 이유: 상한을 "넘지 않는다"는 요구를 range 안의 임의 지점을
   추측하지 않고 만족시키는 가장 보수적인 선택).
4. `cap_ms = section.start_ms + beats_to_seconds(cap_beats, bpm) * 1000`.
5. 다음 큐(있으면)의 `start_ms` 와 비교한다.
   - 다음 큐가 `cap_ms` 이전에 이미 시작하면 아무것도 안 한다
     (REQ-LDCLIMAX-008 — 자연 전환이 이미 상한을 지킨다).
   - 다음 큐가 없거나(마지막 절정 큐) `cap_ms` 이후에 시작하면, `cap_ms`
     시각에 복귀 큐를 끼운다.
6. 복귀 큐의 값 = **그 회차에서 사다리를 오르지 않았을 때의 기준 값** —
   같은 절정 큐를 만들 때 이미 계산됐던 "사다리 오르기 전" 룩(`_rung_applied`
   가 받는 `look` 인자, 아직 스텝을 적용하지 않은 상태)을 재사용한다. 새
   룩을 만들지 않는다 — 절정 큐 자신이 이미 들고 있던 pre-accent 값을 그대로
   재방출한다.
7. 삽입 뒤 후속 큐 번호를 1씩 밀고, `climax_returns` 에 `SongCueClimaxReturn`
   레코드를 더한다.

### 2.2 미검증 잔여 위험 (착수 전 고지)

- **`beats_per_bar`/`bar_milliseconds`(cue_density.py:139-161)와의 박자표
  해석 일치 여부** — 이 SPEC 은 `beats_to_seconds`(4/4 여부와 무관하게 박
  하나 = `60/bpm` 초)만 쓴다. `cue_density.py` 의 마디 분할은 박자표까지
  본다(`beats_per_bar`). 절정 상한은 정본이 "박" 단위로만 말하므로(마디가
  아니다) 박자표 의존이 없는 것이 맞다고 읽었지만, 실기 확인 전까지는
  가정이다.
- **재번호 매기기가 건드리는 다른 소비처** — `cue_number: int` 를 참조하는
  다운스트림(콘솔 전송, 리포트, `cue_sheet_apply.py` 등)이 삽입 이후의
  재번호를 다 받아들이는지는 이 SPEC 의 판정 범위 밖이다(§4 비목표 —
  로컬 pytest 만).

## 3. 색 스냅 큐 조립

```python
def _color_snap_applied(
    look: Look,
    *,
    returning_color: str,
) -> tuple[Look, float]:
    """색 스냅이 확정된 큐의 (룩, 강제 페이드) 쌍을 만든다.

    룩의 색 속성(ColorRGB_* 등)을 `returning_color` 로 강제하고, 페이드는
    무조건 0.0 을 반환한다(REQ-LDCLIMAX-003). `returning_color` 는 §7 색
    복귀 규율이 이미 고른 색(코러스 1이 쓴 색)이어야 한다(REQ-LDCLIMAX-002)
    — 이 함수 자신은 그 색이 유효한지 검증하지 않는다(호출자 책임, 효과
    판정은 `_accent_is_effective` 확장이 담당).
    """
```

호출 위치는 `_rung_applied`(songcue.py 2447행 근방, `_MARKING_ACCENT_AXIS`
분기)의 새 분기 — `rung == LADDER_COLOR_SNAP` 이면 `_stepped` 대신 이
함수를 부른다. 페이드 강제는 오늘 이 파일의 큐 조립 결과에 "페이드" 필드가
있는지부터 run phase 에서 확인해야 한다 — `ComposedCue.fade_seconds`
(경로 A)와 달리 경로 B(`SongCueSectionBundle`)의 필드 목록에서 페이드 시간의
정확한 이름을 이 조사 단계에서는 확정하지 못했다(§4 비목표에 남김, run
phase 착수 시 첫 조사 항목).

## 4. §6.1 일곱 수단 ↔ 이 저장소 표현 대조표 (조사 요약)

| §6.1 수단 | 이 저장소 표현 | 실제 값 변경 | 이 SPEC 의 취급 |
|---|---|---|---|
| 밝기 히트 | `LADDER_DIMMER_HIT` | O (`Dimmer` 스텝) | 손대지 않음(기존) |
| 무빙 버스트 | `MovementPlan`(별도 층, `_movement_carrier`) | O | 손대지 않음(기존, 사다리 밖) |
| **색 스냅** | 없음 → 이 SPEC 이 `LADDER_COLOR_SNAP` 신설 | 이 SPEC 이후 O | **이 SPEC 의 대상 1** |
| 백색 플래시 | `LADDER_BLINDER_OR_FLASH` | O(고정장비 명령) | 지속시간 상한 대상 |
| 드롭 직전 블랙아웃 | `_pre_drop_darkened` | O | 손대지 않음(기존, §8 축) |
| 짧은 스트로브 | `LADDER_STROBE_HIT` | O(고정장비 명령) | 지속시간 상한 대상 |
| 빔·포지션 히트 | `zoom_pinch`/`iris_pinch` | O | 손대지 않음(기존) |

이 표가 이 SPEC 의 정확한 경계다 — 일곱 수단 중 다섯은 이미 구현돼 있고,
이 SPEC 은 **색 스냅**(신설)과 **절정 지속시간 상한**(신설, 백색
플래시·스트로브 두 칸에만 적용) 둘만 더한다.

## 5. Out-of-scope 경계와의 관계

design.md 의 모든 결정은 §4 비목표(spec.md)의 경계 안에서만 유효하다 —
특히 경로 A(`AccentDecision`)는 이 설계가 건드리지 않는다.
