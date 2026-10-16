"""박자 격자 데이터 모델 — 런북 모드 콘솔 그룹 트랙 × 마디 격자 (SPEC-LDBEAT-001 M2/M7).

이 모듈은 콘솔에 아무것도 쓰지 않는다. 입력도 출력도 순수 파이썬 사전뿐이다
(``cue_sheet_edit.py``와 같은 모양, t281). 저장은 M2가 확정한 임베드 설계를
따른다(spec.md §5 열린 결정 0'): 격자는 기존 ``timeline`` 사전의 새 키
``beat_grid`` 하나로 심는다 — ``SongTimelineStore``(``session.py:3486``)의
atomic JSON write와 ``TimelineDraftHistory``(``session.py:3831``,
``:8505``)의 전체-사전 되돌리기가 **코드 추가 없이** 격자도 덮는다. 격자
전용 독립 저장소는 M2에서 신설하지 않는다 — 이 설계를 바꾸려면 director와
재확인하고 이 주석과 progress.md를 함께 고친다.

트랙 모양(카드 t526 교정, REQ-LDBEAT-004): **줄 하나 = 콘솔 그룹 하나 =
시퀀스 하나**다. 트랙 식별자는 콘솔 그룹 번호/이름이고, "SCENE"·"BACK
PULSE" 같은 역할·효과 혼성 문자열을 식별자로 쓰지 않는다(§B 위험 9). 층
역할(``server.design.rig.RIG_LAYER_ROLES``)은 그 줄 옆의 이름표일 뿐이다.

칸 데이터 구조화(카드 t537, REQ-LDBEAT-006(i)~(iii)): 큐 칸(``BeatGridCue``)은
단일 ``label`` 서술 문자열이 아니라 속성별 구조화 필드(밝기·위치 프리셋·
색 프리셋·효과 프리셋·들어올 때)를 가진다. ``label``은 레거시 호환 + 화면
표시용으로 남는다. 칸 하나의 왼쪽·오른쪽 따로 색은 선택 키 ``split`` 이고, 모양·검증·화면용
값은 ``beat_grid_cell_split`` 이 맡는다(이 파일은 칸을 읽을 때 그 키를 지나가게만 한다).

리그·곡 일반화(카드 t537 추가 지시 2, 2026-10-10 감독 원칙 — "지금은 리그
하나·디자인 하나로 시험하지만, 조건은 언제든 바뀐다. 다른 장비·다른
디자인에서도 동작해야 한다"): 이 파일의 로더(``default_beat_grid``·
``_build_track_from_data``·``normalize_beat_grid_cue``)는 어떤 곡의
그룹 번호·그룹 이름·큐 내용도 몰라도 되는 일반 코드다. LOVE ATTACK 전용
값(그룹 4/7/11/12/14, "BACK"·"SIDE-ALL"·"MOVER-U"·"MOVER-D"·"BLIND"·
"STROBE", §4 전사값 넷, SCENE 메모 여섯)은 전부
``beat_grid_data/love_attack.yaml`` 데이터 파일 하나에만 산다. 다른
곡·다른 리그의 기본값은 같은 스키마의 새 YAML 파일 + ``_SONG_DEFAULT_FILES``
레지스트리 한 줄만 추가하면 된다 — 이 파일의 로직은 바꾸지 않는다.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Literal, NotRequired, TypedDict

import yaml

from server.design.beat_grid_console_audio_offset import CONSOLE_AUDIO_OFFSET_SECONDS
from server.design.beat_grid_probes import (
    read_m1_probe_results,
    read_m1_probe_results_from_path,
)
from server.design.rig import resolve_layer_role

__all__ = [
    "DEFAULT_BAR_RANGE",
    "LOVE_ATTACK_TITLE",
    "BeatGridAppMovement",
    "BeatGridBrightness",
    "BeatGridCellSplit",
    "BeatGridCellSplitSide",
    "BeatGridCue",
    "BeatGridEntry",
    "BeatGridEvidence",
    "BeatGridEvidenceApproval",
    "BeatGridTrack",
    "BeatGridView",
    "SceneCellAssignment",
    "SceneMemo",
    "CELL_HOLD",
    "EMPTY_PRESET_HOLD",
    "POOL_UNREAD_HOLD",
    "POSITION_CREATE_ON_APPLY",
    "apply_pending_approval",
    "attach_beat_grid_default",
    "attach_beat_grid_runtime_extras",
    "check_app_movement_axis_conflict",
    "check_evidence_approval",
    "classify_scene_cell_assignment",
    "classify_empty_preset",
    "default_beat_grid",
    "approved_preset_numbers",
    "empty_preset_cells",
    "find_overlapping_group_tracks",
    "normalize_beat_grid_cue",
    "pan_only_vertical_base_warning",
    "pending_preset_approvals",
    "pending_preset_fields",
    "preset_pool_no",
    "split_empty_preset_holds",
    "validate_beat_grid_tracks",
]

#: REQ-LDBEAT-006(i-2)/(015)(c) — 밝기는 값/디머 프리셋/디머 효과 프리셋
#: 중 정확히 하나만 쓰는 단일모드다. 셋 다 비어 있으면(아직 미정) `None`.
BrightnessMode = Literal["value", "dimmer_preset", "dimmer_effect"]

#: REQ-LDBEAT-006(i-3)(D9 교정) — 효과 프리셋이 속한 풀의 종류.
EffectKind = Literal["position", "color", "dimmer", "mixed"]

#: REQ-LDBEAT-006(iv-2) — §4 SCENE 칸 값이 트랙 큐로 옮겨지는지(``"track"``)
#: 메모로 남는지(``"memo"``).
SceneCellAssignment = Literal["track", "memo"]

#: REQ-LDBEAT-006(vi-4) — `app_movement`의 한 바퀴 주기는 음악 단위로만
#: 저장된다(초 단위 상수는 shall not).
AppMovementPeriodUnit = Literal["beat", "bar"]

#: REQ-LDBEAT-006(vii-2)(plan-audit iteration 1 D1 교정) — 증거 **강도**만
#: 담는 닫힌 집합. 승인 여부는 별도 `approval` 하위 객체가 담당한다(두 축은
#: 독립).
EvidenceGrade = Literal["measured", "measured_other_group", "name_only"]


def classify_scene_cell_assignment(
    *,
    named_group: str | None,
    confirmed_track_group_names: Sequence[str],
    group_has_existing_cue_at_bar: bool,
    named_role: str | None = None,
    confirmed_track_roles: Sequence[str | None] = (),
) -> SceneCellAssignment:
    """REQ-LDBEAT-006(iv-2)의 "세 조건" 규칙을 파라미터화한 순수 함수
    (plan-audit iteration 3 D4 — 이전까지는 ``beat_grid_data/*.yaml``을
    작성할 때 사람이 수동으로 재검토하던 판단이었다). 세 조건 — 그 칸이
    그룹을 **직접 지칭**하고, 그 그룹의 번호가 **이미 확인된 트랙**으로
    존재하며, 그 마디·트랙 자리에 **기존 큐와 충돌이 없을 때만** 값이
    (iv-1)의 메모가 아니라 해당 트랙의 큐로 옮겨진다 — 하나라도 거짓이면
    메모로 남는다.

    이 함수는 어떤 리그·곡의 그룹 이름도 모른다(카드 t537 추가 지시 2와
    같은 일반화 원칙) — ``named_group``/``confirmed_track_group_names``는
    호출자가 그 곡의 데이터에서 넘긴다.

    **규칙 확장(감독 결정 2026-10-10, 카드 t543)** — 칸이 그룹 이름 대신 층
    역할(예: 「워시」 → ``"wash"``)을 부르면 ``named_role``로 넘긴다. 그 역할을
    가진 확인된 트랙(``confirmed_track_roles``, 공용 판정기
    ``resolve_layer_role``의 결과)이 **정확히 하나**일 때만 조건 1·2가 참이다 —
    둘 이상이면 어느 줄인지 정할 수 없고, 없으면 갈 곳이 없어 메모로 남는다.
    그룹 이름 문자열 비교는 넓히지 않는다(다른 리그에서 이름이 달라도 역할은
    같은 판정기로 붙는다).
    """
    if named_group is None:
        if named_role is None:
            return "memo"
        if list(confirmed_track_roles).count(named_role) != 1:
            return "memo"
        return "memo" if group_has_existing_cue_at_bar else "track"
    if named_group not in confirmed_track_group_names:
        return "memo"
    if group_has_existing_cue_at_bar:
        return "memo"
    return "track"


class BeatGridBrightness(TypedDict):
    """REQ-LDBEAT-006(i-2) — 값(퍼센트) / 디머 프리셋 / 디머 효과 프리셋
    중 정확히 하나만 쓴다. ``mode``가 `None`이면 셋 다 미정이다."""

    mode: BrightnessMode | None
    value_percent: int | None
    preset_no: str | None


class BeatGridEntry(TypedDict):
    """REQ-LDBEAT-006(i-4) — "들어올 때"는 **마디 수**(``fade_bars``, 초
    아님 — 초 환산은 화면 표시 시점에 그 곡 BPM으로 계산한다)와 MIB
    모드다."""

    fade_bars: int | None
    mib_mode: str | None
    # 카드 t574 — SPEC-LDBEAT-001 0.5.0 REQ-LDBEAT-006(i-4a)~(i-4e). 전부 음악
    # 단위(박)이고 초는 저장하지 않는다. 미정(``None``)은 각 필드의 기본 동작을
    # 뜻한다 — trigger_beat: 1박(마디 시작), position_late_beats: 같이,
    # tracking: 정하지 않음. fade_beats 와 fade_bars 는 동시에 숫자일 수 없다.
    fade_beats: int | None
    trigger_beat: int | None
    delay_beats: int | None
    position_late_beats: int | None
    tracking: str | None


class BeatGridAppMovement(TypedDict):
    """REQ-LDBEAT-006(vi-1)~(vi-8), 카드 t548, 감독 결정 2026-10-10/11 —
    새 콘솔 프리셋 없이 앱이 커맨드로 만드는 두 단계 상대 페이저 움직임.
    ``effect_preset_no``+``effect_kind``(콘솔에 저장된 효과 프리셋)나
    ``position_preset_no``(정적 위치 프리셋)와는 구분되는 별도 자리다.

    - ``shape``는 ``server.spatial.position_fx.POSITION_FX_EFFECTS``와
      **같은** 닫힌 집합이다(vi-2) — 새 모양 이름을 발명하지 않는다.
    - ``axes``는 움직이는 속성을 명시적으로 담는다(vi-3) — ``shape``
      이름으로부터의 암묵적 추론은 하지 않는다.
    - ``period_unit``/``period_value``는 음악 단위(박/마디)로만 저장된다
      (vi-4) — 초 단위 상수는 `shall not`. 실제 콘솔 Speed는 에미터가
      그 곡 BPM으로 계산한다(저장 시점 계산 금지).
    - ``phase_spread``는 ``shape``와 독립적으로 위상 펼침 사용 여부를
      기록한다(vi-5).
    """

    shape: str | None
    axes: tuple[str, ...]
    period_unit: AppMovementPeriodUnit | None
    period_value: int | None
    phase_spread: bool | None


class BeatGridEvidenceApproval(TypedDict):
    """REQ-LDBEAT-006(vii-3), REQ-LDBEAT-015(g) — 감독의 레인 제안표 명시
    승인. 셋 다 채워져야(by/date/source) 승인 예외가 성립한다."""

    by: str | None
    date: str | None
    source: str | None


class BeatGridEvidence(TypedDict):
    """REQ-LDBEAT-006(vii-1)~(vii-3) — 칸별 근거 등급. ``source_ref``
    (§4 배치 규칙서 인용 전용, REQ-006(i-5))와는 다른 목적이고 서로의 값을
    바꾸지 않는다. ``grade``(증거 강도)와 ``approval``(승인 여부)은
    독립적인 두 축이다."""

    grade: EvidenceGrade | None
    approval: BeatGridEvidenceApproval | None


class BeatGridCellSplitSide(TypedDict):
    """칸 하나의 왼쪽 또는 오른쪽 한 쪽 — ``color`` 는 표준 팔레트 색 이름이고, 정하지
    않았으면 `None`이다. 화면용 ``color_rgb`` 는 저장하지 않는다(서빙 경계가 단다,
    ``beat_grid_cell_split.attach_cell_split_to_cues``)."""

    color: str | None


class BeatGridCellSplit(TypedDict):
    """칸 하나가 왼쪽·오른쪽을 따로 가질 때의 두 쪽(``split``) — 키는 정확히 이 둘이다."""

    left: BeatGridCellSplitSide
    right: BeatGridCellSplitSide


class BeatGridCue(TypedDict):
    """격자 칸 하나(카드 t537 구조화, REQ-LDBEAT-006(i-1)~(i-7); 카드 t548이
    ``app_movement``·``evidence`` 추가). 단일 ``label`` 서술 문자열이 아니라
    속성별 구조화 필드(밝기·위치 프리셋·색 프리셋·효과 프리셋·들어올 때·
    앱 무빙·근거 등급)로 저장된다. ``label``은 레거시 호환 + 화면
    표시용으로 남는다(삭제하지 않는다, REQ-006(ii-3))."""

    bar: int
    label: str
    brightness: BeatGridBrightness
    position_preset_no: str | None
    color_preset_no: str | None
    effect_preset_no: str | None
    effect_kind: EffectKind | None
    entry: BeatGridEntry
    #: 이 칸의 값이 비롯된 §4 파일 경로+행 번호(칸당 1개) — REQ-006(i-5).
    #: §4 출처가 없는 값(미정이거나 상대 서술)은 `None`이다.
    source_ref: str | None
    #: 카드 t548, REQ-LDBEAT-006(vi) — 앱 2단계 무빙. 없으면 `None`.
    app_movement: BeatGridAppMovement | None
    #: 카드 t548, REQ-LDBEAT-006(vii) — 칸별 근거 등급. 없으면 `None`.
    evidence: BeatGridEvidence | None
    #: 칸 하나의 왼쪽·오른쪽 따로 색(선택). 없으면 **키 자체가 없다** — `None` 도 싣지 않는다.
    split: NotRequired[BeatGridCellSplit]


class BeatGridTrack(TypedDict):
    """콘솔 그룹 트랙 하나. ``group_no``가 ``None``이면 이 플랜-phase/M1
    증거에서 그룹 번호가 아직 확인되지 않았다는 뜻이다(지어내지 않는다) —
    ``group_no_confirmed``가 그 구분을 명시적으로 싣는다."""

    group_no: int | None
    group_no_confirmed: bool
    group_name: str
    layer_role: str | None
    cues: list[BeatGridCue]


class SceneMemo(TypedDict):
    """카드 t537 ② 리드 추가 지시(2026-10-10) — §4 SCENE 열 값은 역할·효과
    혼성이라 단일 콘솔 그룹 트랙으로 지어낼 수 없다(SCENE은 카드 t526이
    이미 트랙에서 뺐다). 그 칸에 적힌 값은 트랙에 끼워 넣지 않고 이
    메모로만 남긴다 — 겹침 검증(REQ-LDBEAT-004(h))과는 완전히 독립이다."""

    bar: int
    text: str
    source_ref: str


class BeatGridView(TypedDict):
    song_title: str
    bar_range: dict[str, int]
    tracks: list[BeatGridTrack]
    scene_memos: list[SceneMemo]
    #: M1 9항목 판정(REQ-LDBEAT-003(b)) — `default_beat_grid`는 "미확인"
    #: 뼈대만 채운다. 실제 최신 값은 `attach_beat_grid_runtime_extras`가
    #: progress.md를 읽어 그 자리에서 다시 채운다(살아있는 소스).
    probe_results: dict[int, str]
    source: str
    note: str | None
    #: 카드 t570(REQ-LDBEAT-024(a)) — 「콘솔 같이」 토글이 쓸 음원 지연(초,
    #: 콘솔 타임코드 시작 기준). `beat_grid_console_audio_offset.py`의
    #: 데이터 파일 출처 값 그대로(t520 실측) — 코드 상수가 아니다. 출처가
    #: 없으면 `None`(지어내지 않음, 토글은 송신 경로 자체가 없어 이 카드
    #: 범위에서는 늘 비활성이다 — 이 값 유무와 무관).
    console_audio_offset_seconds: float | None


#: REQ-LDBEAT-005(a) — 초기 표시 범위. 정수, 1-base 위상 1 기준, 0 = 못갖춘마디
#: (`SPEC-LDBARMAP-001` §5 열린 결정 0과 같은 번호 공간, 카드 t529 맞춤).
DEFAULT_BAR_RANGE: tuple[int, int] = (0, 25)

#: 곡별 기본값을 가진 유일한 곡(배치 규칙서 §2~§4) — 이 상수는 "레지스트리
#: 조회 키"일 뿐이다. 그룹 번호·트랙 이름·큐 내용 같은 리그 전용 값은
#: 전혀 여기에 없다(전부 `beat_grid_data/love_attack.yaml`에 있다).
LOVE_ATTACK_TITLE = "LOVE ATTACK"

#: 곡별 기본값이 없을 때 화면이 보일 안내(AC-LDBEAT-007).
_NO_DEFAULT_NOTE = "이 곡의 기본값 없음"


def _group_key(name: str) -> str:
    return name.strip().casefold()


#: 곡 제목(정규화된 키) → 그 곡의 기본값 YAML 경로. 이 딕셔너리 **한 줄**이
#: "어느 곡이 기본값을 갖는가"를 정하는 유일한 곡-특정 결정이다 — 그
#: 안의 내용(그룹 번호·이름·큐)은 전부 데이터 파일에 있다. 다른 곡의
#: 기본값을 추가하려면 같은 스키마의 YAML 파일 + 이 딕셔너리 한 줄만
#: 필요하다(이 파일의 다른 로직은 바꾸지 않는다).
_SONG_DEFAULT_FILES: dict[str, Path] = {
    _group_key(LOVE_ATTACK_TITLE): Path(__file__).resolve().parent
    / "beat_grid_data"
    / "love_attack.yaml",
}


def _group_prefix(name: str) -> str | None:
    """하이픈 앞 접두 토큰(``server.design.rig.resolve_layer_role``의 접두
    매칭과 같은 분리 — ``side``/``wash``/``mover`` 계열의 "-ALL" 그룹이 같은
    접두를 가진 다른 그룹을 전부 포함한다는 사실을 가른다). 하이픈이 없으면
    ``None``(겹침 판정 대상이 아니다)."""
    key = _group_key(name)
    prefix, separator, _rest = key.partition("-")
    return prefix if separator else None


def find_overlapping_group_tracks(group_names: Sequence[str]) -> tuple[str, str] | None:
    """제안된 트랙 목록에서 같은 장비를 겹쳐 잡는 **첫** 두 그룹 이름을 돌려준다
    (REQ-LDBEAT-004(h)). 겹침 없으면 ``None``.

    이 함수는 어떤 리그에도 특정되지 않는다 — 콘솔 그룹 이름 문자열의
    접두/정확 일치 규칙만 본다(리그별 그룹 이름은 전혀 하드코딩돼 있지
    않다, 카드 t537 추가 지시 2). 두 가지 겹침 모양만 판정한다:

    1. **같은 그룹을 두 번** — 대소문자 무시 정확 일치.
    2. **"<접두>-ALL"이 같은 접두의 다른 그룹을 포함한다** — 예:
       "<접두>-ALL"은 "<접두>-A"·"<접두>-B" 같은 같은-접두 그룹을 전부
       담는다(이 리그의 t525 실측이 보여준 모양 — 어느 리그든 접두가
       같으면 똑같이 적용되고, 구체적 접두 이름은 전혀 하드코딩돼 있지
       않다).

    추측(RG5류 금지)이 아니라 바이트 정확 일치만 본다 — "<접두>-ALLX"처럼
    접두가 바이트 동일하지 않으면 겹침으로 안 본다.
    """
    seen: dict[str, str] = {}
    all_by_prefix: dict[str, str] = {}
    plain_by_prefix: dict[str, list[str]] = {}
    for name in group_names:
        key = _group_key(name)
        if key in seen:
            return (seen[key], name)
        seen[key] = name
        prefix = _group_prefix(name)
        if prefix is None:
            continue
        suffix = key.split("-", 1)[1]
        if suffix == "all":
            all_by_prefix[prefix] = name
        else:
            plain_by_prefix.setdefault(prefix, []).append(name)
    for prefix, all_name in all_by_prefix.items():
        for plain_name in plain_by_prefix.get(prefix, []):
            return (all_name, plain_name)
    return None


def validate_beat_grid_tracks(tracks: Sequence[Mapping[str, object]]) -> str | None:
    """단일-원인 거절 사유 하나(``cue_sheet_edit.py``와 같은 관행, REQ-LDBEAT-008) —
    겹침이 없으면 ``None``. 검증은 쓰기 전에 전부 끝낸다(부분 적용 금지) —
    이 함수는 아무것도 쓰지 않으므로 호출자가 그 원칙을 지킨다.

    **칸 레벨 구조화와 독립**(REQ-LDBEAT-006(iii), 카드 t537 재확인) — 이
    함수는 ``group_name``만 읽고 ``cues``의 어떤 필드도 읽지 않는다."""
    names = [str(track.get("group_name") or "") for track in tracks]
    conflict = find_overlapping_group_tracks(names)
    if conflict is None:
        return None
    first, second = conflict
    return (
        f"콘솔 그룹 '{first}'와 '{second}'는 같은 장비를 겹쳐 잡습니다 — "
        "두 그룹을 동시에 트랙으로 쓸 수 없습니다."
    )


def normalize_beat_grid_cue(raw: Mapping[str, object]) -> BeatGridCue:
    """레거시(``{bar,label}``만)·일부만 구조화된 선언(YAML 데이터 파일처럼
    값이 있는 필드만 적은 것) 둘 다 받아, 다섯 구조화 필드(+ ``effect_kind``
    · ``source_ref``)를 전부 채운 완전한 모양으로 돌려준다.

    **읽기 경로다 — 파서가 아니다**(REQ-LDBEAT-006(ii-2), AC-LDBEAT-016(g)):
    ``label`` 문자열의 내용을 파싱·분해·정규식 매칭해 구조화 필드를
    역산하지 않는다. ``raw``에 구조화 필드가 없으면 그 자리는 그대로
    `None`이다 — 추측 0건. 선택 키 ``split``(칸 하나의 왼쪽·오른쪽 따로 색)은 ``raw`` 에 있을
    때만 사본으로 옮긴다 — 없으면 결과에도 키가 없다."""
    raw_brightness = raw.get("brightness")
    brightness_source: Mapping[str, object] = (
        raw_brightness if isinstance(raw_brightness, Mapping) else {}
    )
    raw_entry = raw.get("entry")
    entry_source: Mapping[str, object] = raw_entry if isinstance(raw_entry, Mapping) else {}

    raw_app_movement = raw.get("app_movement")
    app_movement: BeatGridAppMovement | None = None
    if isinstance(raw_app_movement, Mapping):
        app_movement = BeatGridAppMovement(
            shape=raw_app_movement.get("shape"),  # type: ignore[typeddict-item]
            axes=tuple(raw_app_movement.get("axes") or ()),  # type: ignore[arg-type]
            period_unit=raw_app_movement.get("period_unit"),  # type: ignore[typeddict-item]
            period_value=raw_app_movement.get("period_value"),  # type: ignore[typeddict-item]
            phase_spread=raw_app_movement.get("phase_spread"),  # type: ignore[typeddict-item]
        )

    raw_evidence = raw.get("evidence")
    evidence: BeatGridEvidence | None = None
    if isinstance(raw_evidence, Mapping):
        raw_approval = raw_evidence.get("approval")
        approval: BeatGridEvidenceApproval | None = None
        if isinstance(raw_approval, Mapping):
            approval = BeatGridEvidenceApproval(
                by=raw_approval.get("by"),  # type: ignore[typeddict-item]
                date=raw_approval.get("date"),  # type: ignore[typeddict-item]
                source=raw_approval.get("source"),  # type: ignore[typeddict-item]
            )
        evidence = BeatGridEvidence(
            grade=raw_evidence.get("grade"),  # type: ignore[typeddict-item]
            approval=approval,
        )

    cue = BeatGridCue(
        bar=int(raw["bar"]),  # type: ignore[arg-type]
        label=str(raw.get("label") or ""),
        brightness=BeatGridBrightness(
            mode=brightness_source.get("mode"),  # type: ignore[typeddict-item]
            value_percent=brightness_source.get("value_percent"),  # type: ignore[typeddict-item]
            preset_no=brightness_source.get("preset_no"),  # type: ignore[typeddict-item]
        ),
        position_preset_no=raw.get("position_preset_no"),  # type: ignore[typeddict-item]
        color_preset_no=raw.get("color_preset_no"),  # type: ignore[typeddict-item]
        effect_preset_no=raw.get("effect_preset_no"),  # type: ignore[typeddict-item]
        effect_kind=raw.get("effect_kind"),  # type: ignore[typeddict-item]
        entry=BeatGridEntry(
            fade_bars=entry_source.get("fade_bars"),  # type: ignore[typeddict-item]
            mib_mode=entry_source.get("mib_mode"),  # type: ignore[typeddict-item]
            fade_beats=entry_source.get("fade_beats"),  # type: ignore[typeddict-item]
            trigger_beat=entry_source.get("trigger_beat"),  # type: ignore[typeddict-item]
            delay_beats=entry_source.get("delay_beats"),  # type: ignore[typeddict-item]
            position_late_beats=entry_source.get("position_late_beats"),  # type: ignore[typeddict-item]
            tracking=entry_source.get("tracking"),  # type: ignore[typeddict-item]
        ),
        source_ref=raw.get("source_ref"),  # type: ignore[typeddict-item]
        app_movement=app_movement,
        evidence=evidence,
    )
    # 칸 하나의 왼쪽·오른쪽 따로 색 — 이 함수는 화이트리스트라 안 옮기면 칸을 읽을 때마다
    # (기본값 로드 · 서빙 경계 · 편집 병합) 조용히 사라진다. 있을 때만 키를 싣고(없으면 키 자체가
    # 없다) 값은 검증 없이 사본으로 옮긴다 — 모양이 틀리면 그룹·마디 이름을 아는 서빙 경계
    # (`attach_cell_split_to_cues`)와 계획(`preset_plan`)이 알린다.
    raw_split = raw.get("split")
    if raw_split is not None:
        cue["split"] = copy.deepcopy(raw_split)  # type: ignore[typeddict-item]
    return cue


def _track(
    *,
    group_no: int | None,
    group_no_confirmed: bool,
    group_name: str,
    cues: list[BeatGridCue],
) -> BeatGridTrack:
    return BeatGridTrack(
        group_no=group_no,
        group_no_confirmed=group_no_confirmed,
        group_name=group_name,
        layer_role=resolve_layer_role(group_name),
        cues=cues,
    )


def _build_track_from_data(entry: Mapping[str, object]) -> BeatGridTrack:
    """YAML 데이터 한 트랙 항목 → `BeatGridTrack`. 이 함수는 어떤 리그에도
    특정되지 않는다 — 어느 그룹 이름·번호가 오든 그대로 옮긴다."""
    raw_cues = entry.get("cues")
    cues = [normalize_beat_grid_cue(cue) for cue in raw_cues] if isinstance(raw_cues, list) else []
    return _track(
        group_no=entry.get("group_no"),  # type: ignore[arg-type]
        group_no_confirmed=bool(entry.get("group_no_confirmed", False)),
        group_name=str(entry["group_name"]),
        cues=cues,
    )


def _build_scene_memo_from_data(entry: Mapping[str, object]) -> SceneMemo:
    return SceneMemo(
        bar=int(entry["bar"]),  # type: ignore[arg-type]
        text=str(entry["text"]),
        source_ref=str(entry["source_ref"]),
    )


def _load_song_default_document(song_title: str) -> Mapping[str, object] | None:
    """`song_title`의 기본값 YAML을 레지스트리에서 찾아 읽는다. 등록되지
    않은 곡은 `None`(강제 적용 없음, AC-LDBEAT-007) — 이 함수는 YAML의
    내용을 전혀 해석하지 않는다(그대로 파싱해 돌려줄 뿐)."""
    path = _SONG_DEFAULT_FILES.get(_group_key(song_title or ""))
    if path is None:
        return None
    with path.open("r", encoding="utf-8") as handle:
        document = yaml.safe_load(handle)
    return document if isinstance(document, Mapping) else None


def default_beat_grid(song_title: str) -> BeatGridView:
    """``song_title``의 곡별 기본값(REQ-LDBEAT-006). 등록된 곡은 그
    데이터 파일을 그대로 옮기고, 등록되지 않은 곡은 빈 트랙 + "이 곡의
    기본값 없음" 안내(AC-LDBEAT-007) — 강제 적용 없음.

    `probe_results`는 "미확인" 뼈대만 채운다 — 실제 최신 M1 판정은
    `attach_beat_grid_runtime_extras`가 progress.md를 읽어 채운다(REQ-
    LDBEAT-003(b), 이 함수 자체는 파일을 읽지 않는 순수 변환이라 round-
    trip 저장/복원 시험에서도 안정적인 뼈대를 돌려준다)."""
    bar_start, bar_end = DEFAULT_BAR_RANGE
    document = _load_song_default_document(song_title)
    if document is not None:
        raw_tracks = document.get("tracks")
        tracks = (
            [_build_track_from_data(entry) for entry in raw_tracks]
            if isinstance(raw_tracks, list)
            else []
        )
        raw_memos = document.get("scene_memos")
        scene_memos = (
            [_build_scene_memo_from_data(entry) for entry in raw_memos]
            if isinstance(raw_memos, list)
            else []
        )
        source = str(document.get("source") or "custom")
        note = document.get("note")
        note = str(note) if note is not None else None
    else:
        tracks = []
        scene_memos = []
        source = "empty"
        note = _NO_DEFAULT_NOTE
    return BeatGridView(
        song_title=song_title or "",
        bar_range={"start": bar_start, "end": bar_end},
        tracks=tracks,
        scene_memos=scene_memos,
        probe_results=read_m1_probe_results(None),
        source=source,
        note=note,
        console_audio_offset_seconds=CONSOLE_AUDIO_OFFSET_SECONDS,
    )


def attach_beat_grid_default(timeline: Mapping[str, object]) -> dict[str, object]:
    """``timeline`` 사전의 사본에 격자를 싣는다 — **있으면 보존, 없으면
    기본값**(REQ-LDBEAT-006, M2 임베드 설계). 원본은 건드리지 않는다
    (``cue_sheet_edit.py``와 같은 사본-후-머지 관행).

    이 함수는 콘솔에 아무것도 쓰지 않고, 타임라인의 다른 칸도 건드리지
    않는다 — 추가되는 키는 ``beat_grid`` 하나뿐이다. **이미 있는 격자는
    바이트까지 그대로 보존한다**(정규화하지 않는다) — 정규화·M1 최신화는
    `attach_beat_grid_runtime_extras`가 별도로 한다."""
    merged = dict(timeline)
    if merged.get("beat_grid") is not None:
        return merged
    song_title = str(merged.get("song_title") or "")
    merged["beat_grid"] = default_beat_grid(song_title)
    return merged


def attach_beat_grid_runtime_extras(
    payload: Mapping[str, object],
    *,
    progress_md_path: Path | None = None,
) -> dict[str, object]:
    """세션 서빙 경계에서만 호출하는 추가 단계(카드 t537) — ``attach_beat_
    grid_default``와는 별개다(그 함수의 "있으면 바이트 그대로 보존" 계약을
    바꾸지 않기 위해서다). 세 가지를 한다:

    1. **M1 판정 최신화**(REQ-LDBEAT-003(b)) — `progress_md_path`(없으면
       `beat_grid_probes.default_progress_md_path()`)를 그 자리에서 읽어
       ``beat_grid["probe_results"]``를 덮어쓴다. 표 부재·파싱 실패는
       9항목 전부 "미확인"으로 떨어진다(지어낸 PASS 0건).
    2. **레거시 칸 정규화**(REQ-LDBEAT-006(ii)) — 기존에 저장된 격자(커스텀
       이든 레거시 ``{bar,label}``뿐이든)의 모든 칸을 화면이 읽기 전에
       `normalize_beat_grid_cue`로 통과시켜, 구조화 필드가 없는 칸도
       `None`으로 채운 완전한 모양으로 보낸다 — ``label``은 그대로다.
    3. **승인 대기 배지 파생**(카드 t577, REQ-LDBEAT-015(h-1)) — 각 칸에
       `pending_preset_fields`(사람이 읽는 필드 이름 리스트, 비어 있으면
       그 칸은 승인 대기가 아니다)를 덧붙인다. 저장되는 값이 아니라 이
       서빙 경계에서만 파생되는 뷰 전용 필드다 — UI가 같은 판정을 다시
       유추하지 않게 한다(REQ-LDBEAT-015(h-1), M10 4단계).

    ``beat_grid`` 키가 없으면 아무것도 하지 않는다(ADDITIVE, no-op)."""
    from server.design.beat_grid_effect_presets import effect_shape_of_cue

    merged = dict(payload)
    grid = merged.get("beat_grid")
    if not isinstance(grid, Mapping):
        return merged
    grid = dict(grid)
    raw_tracks = grid.get("tracks")
    if isinstance(raw_tracks, list):
        normalized_tracks = []
        for track in raw_tracks:
            if not isinstance(track, Mapping):
                normalized_tracks.append(track)
                continue
            track = dict(track)
            raw_cues = track.get("cues")
            if isinstance(raw_cues, list):
                normalized_cues = []
                for raw_cue in raw_cues:
                    cue = dict(normalize_beat_grid_cue(raw_cue))
                    cue["pending_preset_fields"] = [  # type: ignore[typeddict-unknown-key]
                        _PENDING_PRESET_FIELD_LABELS.get(field, field)
                        for field, _value in pending_preset_fields(cue)
                    ]
                    shape = effect_shape_of_cue(cue, grid)
                    if shape is not None:
                        cue["effect_shape"] = shape  # type: ignore[typeddict-unknown-key]
                    normalized_cues.append(cue)
                track["cues"] = normalized_cues
            normalized_tracks.append(track)
        grid["tracks"] = normalized_tracks
    from server.design.beat_grid_probes import default_progress_md_path

    path = progress_md_path if progress_md_path is not None else default_progress_md_path()
    grid["probe_results"] = read_m1_probe_results_from_path(path)
    # 카드 t579(REQ-LDBEAT-010) — 「⚠ 실기 미확인」 배지를 달 칸. 방금 읽은
    # M1 표(위)와 실측 무빙 기록에서만 가른다 — 화면은 라벨 글자를 맞춰 보지
    # 않고 이 목록만 읽는다.
    from server.design.beat_grid_unverified import unverified_beat_grid_cells

    grid["unverified_cells"] = unverified_beat_grid_cells(grid)
    # 카드 t584 — 「움직임」 고르기 목록의 닫힌 어휘(같은 M1 표 기준).
    from server.design.beat_grid_edit import movement_vocabulary

    grid["movement_vocabulary"] = movement_vocabulary(grid["probe_results"])
    # 카드 t570(REQ-LDBEAT-024(a)) — 이 필드가 생기기 전에 저장된 격자도
    # 같은 쇼 전역 측정값을 받는다(곡별 데이터가 아니라 콘솔 전역 측정이라
    # `setdefault` — 이미 있으면(드물게 다른 값으로 저장돼 있으면) 덮어쓰지
    # 않는다).
    grid.setdefault("console_audio_offset_seconds", CONSOLE_AUDIO_OFFSET_SECONDS)
    merged["beat_grid"] = grid
    return merged


#: REQ-LDBEAT-006(vi-7) — `effect_kind` 값이 Pan·Tilt 둘 다(또는 어느
#: 쪽인지 모른다는 뜻의 "mixed") 움직일 수 있다고 보는 보수적 집합. 축을
#: 안 움직이는 `"color"`/`"dimmer"`는 여기 없다.
_EFFECT_KINDS_WITH_PAN_TILT_AMBIGUITY: frozenset[str] = frozenset({"position", "mixed"})


def check_app_movement_axis_conflict(cue: Mapping[str, object]) -> str | None:
    """REQ-LDBEAT-006(vi-7), AC-LDBEAT-016(t) — 한 칸이 `app_movement`와
    `effect_preset_no`(REQ-006(i-3))를 **같은 축**에 동시에 쓰면 거절한다.
    서로 다른 축(예: 밝기 효과 + 팬 흔들기)은 금지 대상이 아니다.

    `effect_kind`는 그 효과가 정확히 어느 축을 움직이는지 말하지 않는다
    (콘솔 프리셋 내부는 못 읽는다) — `"position"`·`"mixed"`는 Pan·Tilt
    어느 쪽이든 움직일 수 있다고 **보수적으로** 보고, `app_movement`의
    어떤 축과도 충돌로 본다. `"color"`·`"dimmer"`는 축을 움직이지
    않으므로 충돌이 없다."""
    movement = cue.get("app_movement")
    if not isinstance(movement, Mapping):
        return None
    axes = set(movement.get("axes") or ())
    if not axes:
        return None
    if cue.get("effect_preset_no") is None:
        return None
    effect_kind = cue.get("effect_kind")
    if effect_kind not in _EFFECT_KINDS_WITH_PAN_TILT_AMBIGUITY:
        return None
    return (
        f"app_movement 축 {sorted(axes)!r}과 effect_preset_no의 효과가 같은 축을 "
        "움직입니다 — 한 칸에 함께 쓸 수 없습니다(REQ-LDBEAT-006(vi-7))"
    )


def _cell_preset_numbers(cue: Mapping[str, object]) -> tuple[object, ...]:
    """이 칸이 쓰는 모든 프리셋 **번호** 필드 값(비어있지 않은 것만 걸러내지
    않고 그대로) — `check_evidence_approval`이 "프리셋 번호가 있는가"를
    판정하는 데 쓴다."""
    brightness = cue.get("brightness")
    brightness_preset_no = brightness.get("preset_no") if isinstance(brightness, Mapping) else None
    return (
        brightness_preset_no,
        cue.get("position_preset_no"),
        cue.get("color_preset_no"),
        cue.get("effect_preset_no"),
    )


def check_evidence_approval(cue: Mapping[str, object]) -> str | None:
    """REQ-LDBEAT-015(f)/(g), REQ-LDBEAT-006(vii-2)(vii-3),
    AC-LDBEAT-016(o)(p) — 프리셋 **번호**를 하나라도 쓰는 칸은 완전한
    `evidence.approval`(`by == "supervisor"` + `date` + `source` 셋 다)을
    갖춰야 한다. `evidence.grade`와는 독립 — `grade`가 `"name_only"`여도
    `approval`이 채워지면 통과한다(`grade` 자체는 이 검증에 영향을 주지
    않는다, D1 재구조화)."""
    if not any(value is not None for value in _cell_preset_numbers(cue)):
        return None
    evidence = cue.get("evidence")
    approval = evidence.get("approval") if isinstance(evidence, Mapping) else None
    if not isinstance(approval, Mapping):
        return "프리셋 번호가 있지만 evidence.approval이 없습니다 — REQ-LDBEAT-015(f) 위반"
    by = approval.get("by")
    date = approval.get("date")
    source = approval.get("source")
    if by != "supervisor" or not date or not source:
        return "evidence.approval이 불완전합니다(by/date/source 중 누락) — REQ-LDBEAT-015(f) 위반"
    return None


def pan_only_vertical_base_warning(cue: Mapping[str, object]) -> str | None:
    """감독 결정④(2026-10-10, 리드 경유) — Pan 단독 `app_movement`가
    `position_preset_no` 없이(REQ-LDBEAT-006(vi-8), 기본 위치=수직 중심)
    쓰이면 눈에 보이지 않을 수 있다. 거절이 아니라 **경고**다.

    non-null `position_preset_no`가 실제로 "수직"인지 판정하려면 이 SPEC의
    증거 범위 밖 데이터(그 프리셋이 가리키는 실제 틸트값)가 필요하다 —
    이 함수는 `position_preset_no is None`인 경우만 다룬다(§5 항목 8
    미해소분, 범위를 넓히지 않는다)."""
    movement = cue.get("app_movement")
    if not isinstance(movement, Mapping):
        return None
    axes = set(movement.get("axes") or ())
    if axes != {"Pan"}:
        return None
    if cue.get("position_preset_no") is not None:
        return None
    return (
        "⚠ Pan 단독 움직임이 기본 위치(수직) 중심입니다 — 기울인 위치 프리셋 없이는 "
        "눈에 보이지 않을 수 있습니다"
    )


#: REQ-LDBEAT-015(h-2) — 「⇪ 콘솔에 반영」 승인 카드가 "새로 만드는 프리셋
#: N개"로 열거할 때 보여줄 사람이 읽는 필드 이름. 칸 레벨(``evidence.
#: approval``은 칸 하나에 한 객체)이 아니라 필드 레벨로 쪼개 보여준다 —
#: 승인 카드는 어느 번호가 새로 생기는지 사람이 읽을 수 있어야 한다.
_PENDING_PRESET_FIELD_LABELS: dict[str, str] = {
    "brightness.preset_no": "디머/디머 효과 프리셋",
    "position_preset_no": "위치 프리셋",
    "color_preset_no": "색 프리셋",
    "effect_preset_no": "효과 프리셋",
}


def pending_preset_fields(cue: Mapping[str, object]) -> list[tuple[str, object]]:
    """카드 t577, REQ-LDBEAT-015(h-1)~(h-2) — 이 칸의 non-null 프리셋
    **번호** 필드 중, 그 칸의 완전한 `evidence.approval`로 아직 덮이지
    않은 것들 — `(필드 키, 번호)` 쌍의 리스트. `check_evidence_approval`
    이 `None`을 돌려주면(그 칸의 승인이 이미 완전하거나, 프리셋 번호가
    아예 없으면) 빈 리스트다 — "승인 대기"는 새 필드가 아니라
    `check_evidence_approval`과 non-null 번호의 교차로 파생되는 상태다
    (plan.md M10 1단계, 되돌리기 비용 최소화 결정)."""
    if check_evidence_approval(cue) is None:
        return []
    return _preset_number_fields(cue)


def _preset_number_fields(cue: Mapping[str, object]) -> list[tuple[str, object]]:
    """이 칸의 non-null 프리셋 **번호** 필드 전부 — 승인 여부와 무관하게
    `(필드 키, 번호)` 쌍으로 돌려준다(``pending_preset_fields``가 승인 대기
    칸에서 쓰는 같은 열거, 카드 t595가 승인된 칸의 빈 번호까지 보려고 뽑았다)."""
    fields: list[tuple[str, object]] = []
    brightness = cue.get("brightness")
    if isinstance(brightness, Mapping) and brightness.get("preset_no") is not None:
        fields.append(("brightness.preset_no", brightness["preset_no"]))
    for field in ("position_preset_no", "color_preset_no", "effect_preset_no"):
        value = cue.get(field)
        if value is not None:
            fields.append((field, value))
    return fields


def pending_preset_approvals(grid: Mapping[str, object]) -> list[dict[str, object]]:
    """카드 t577, REQ-LDBEAT-015(h-2) — `grid`(``BeatGridView``) 전수를
    순회해 승인 대기 칸·필드를 `{group_name, bar, field, field_label,
    value}` 사전 목록으로 돌려준다. 「⇪ 콘솔에 반영」 승인 카드의 "새로
    만드는 프리셋 N개" 열거, 그리고 승인 뒤 `apply_pending_approval`이
    그대로 받는 "열거된 집합"이 이 목록이다 — 카드가 보여준 것과 실제로
    승인이 적히는 대상이 바이트까지 같은 자료에서 나온다(과다·과소 열거를
    원리적으로 막는다)."""
    result: list[dict[str, object]] = []
    for track in grid.get("tracks") or []:
        if not isinstance(track, Mapping):
            continue
        group_name = track.get("group_name")
        for cue in track.get("cues") or []:
            if not isinstance(cue, Mapping):
                continue
            bar = cue.get("bar")
            for field, value in pending_preset_fields(cue):
                result.append(
                    {
                        "group_name": group_name,
                        "bar": bar,
                        "field": field,
                        "field_label": _PENDING_PRESET_FIELD_LABELS.get(field, field),
                        "value": value,
                    }
                )
    return result


def approved_preset_numbers(grid: Mapping[str, object]) -> list[dict[str, object]]:
    """카드 t600 — 이미 완전한 `evidence.approval`을 가진 칸의 프리셋 번호를
    ``pending_preset_approvals``와 같은 모양(+ ``"approved": True``)으로 돌려준다.

    반영은 이 번호도 승인 대기 번호와 같은 규칙(가드 D·t592 만들기)으로 가른다 —
    승인은 「그 번호를 쓴다」는 감독의 결정이지 「콘솔 풀에 그 slot 이 있다」는
    사실이 아니므로, 빈 번호를 가리킨 승인된 칸도 그대로 내보내면 빈 프리셋을
    부르는 큐가 나간다. 승인 기록 대상은 아니다(이미 승인됐다)."""
    result: list[dict[str, object]] = []
    for track in grid.get("tracks") or []:
        if not isinstance(track, Mapping):
            continue
        group_name = track.get("group_name")
        for cue in track.get("cues") or []:
            if not isinstance(cue, Mapping) or check_evidence_approval(cue) is not None:
                continue
            for field, value in _preset_number_fields(cue):
                result.append(
                    {
                        "group_name": group_name,
                        "bar": cue.get("bar"),
                        "field": field,
                        "field_label": _PENDING_PRESET_FIELD_LABELS.get(field, field),
                        "value": value,
                        "approved": True,
                    }
                )
    return result


#: 카드 t590(REQ-LDBEAT-015(i-1)) — 보류 표시 문구. 승인 카드와 시험이 같은 값을 읽는다.
EMPTY_PRESET_HOLD = "빈 프리셋 — 아직 콘솔에 만들 길 없음"
POOL_UNREAD_HOLD = "풀을 못 읽어 빈 프리셋인지 확인 못 함"
CELL_HOLD = "같은 칸에 보류 번호가 있어 함께 보류"
#: 카드 t595 — 빈 위치 번호 가운데 반영 때 t592 레시피로 만들 수 있는 것의 표식 문구.
POSITION_CREATE_ON_APPLY = (
    "빈 위치 프리셋 — 반영 때 목표 좌표로 만듦(그룹 소속·장비 좌표를 다 읽을 때만, 못 읽으면 보류)"
)


def preset_pool_no(value: object) -> int | None:
    """``"4.21"`` → ``4``. ``pool.slot`` 꼴이 아니면 ``None``(지어내지 않는다)."""
    pool, sep, slot = str(value).partition(".")
    if not sep or not pool.isdigit() or not slot.isdigit():
        return None
    return int(pool)


def classify_empty_preset(
    value: object,
    pool_slots: Mapping[int, Mapping[int, object] | None],
    *,
    unknown_pool_unread: bool,
) -> str | None:
    """번호 하나의 빈 프리셋 판정 — 보류(``split_empty_preset_holds``)와 격자 표식
    (``empty_preset_cells``)이 같은 판정을 쓰도록 한 자리에 둔다(카드 t595).

    ``EMPTY_PRESET_HOLD``(slot 없음·``pool.slot`` 꼴 아님) · ``POOL_UNREAD_HOLD``
    (풀을 못 읽음) · ``None``(slot 있음). ``pool_slots``에 그 풀 번호 키가 아예
    없을 때는 ``unknown_pool_unread``가 정한다 — 반영은 그 번호의 풀을 방금
    읽었으므로 「못 읽음」, 표식은 서버가 그 풀을 아직 읽지 않았으므로 판정 없음
    (``None``, 지어내지 않는다). 키는 ``in``으로 가린다(``.get()``은 없는 키와
    못 읽은 풀을 같은 ``None``으로 돌려준다)."""
    pool_no = preset_pool_no(value)
    if pool_no is None:
        return EMPTY_PRESET_HOLD
    if pool_no not in pool_slots:
        return POOL_UNREAD_HOLD if unknown_pool_unread else None
    slots = pool_slots[pool_no]
    if slots is None:
        return POOL_UNREAD_HOLD
    if int(str(value).partition(".")[2]) not in slots:
        return EMPTY_PRESET_HOLD
    return None


def empty_preset_cells(
    grid: Mapping[str, object],
    pool_slots: Mapping[int, Mapping[int, object] | None],
) -> list[dict[str, object]]:
    """카드 t595(REQ-LDBEAT-015(i-1) 「그 칸에 표시」) — 서버가 이미 읽은 풀
    (``pool_slots``: 풀 번호 → ``{slot: 이름}``, 못 읽었으면 ``None``)로 격자의
    빈 프리셋 칸을 가른다. UI 는 이 목록만 읽는다(번호를 다시 추측하지 않는다).

    승인 여부와 무관하게 칸의 모든 프리셋 번호를 본다 — 카드 t600 이후 반영은
    이미 승인된 칸의 빈 번호도 승인 대기 칸과 같은 규칙으로 보류하거나 만든다.
    아직 읽지 않은 풀의 번호는 판정하지 않는다(표식 없음).

    t592 이후 빈 **위치** 번호는 반영 때 만들어질 수 있다 — 칸(승인 여부 무관)이
    가리키고 격자 조건(``position_grid_blocker``: 목표 좌표·영문 이름·그룹 확인)이 다
    있으면 ``kind == "create_on_apply"``(남은 조건은 반영 때 읽는 그룹 소속·장비
    좌표뿐). 격자 조건이 빠졌으면 그 사유를 ``reason``에 붙인다. 카드 t593 부터 빈
    **효과** 번호도 같다 — 격자 조건(``effect_grid_blocker``: 레시피·템플릿·번호대·영문
    이름·그룹)이 다 있으면 ``create_on_apply``(남은 조건은 곡 BPM, 카드 t605 —
    반영당 하나 제약은 더 없다). 카드
    t594 부터 빈 **색** 번호도 같다 — 격자 조건(``color_grid_blocker``: RGB·영문
    이름·그룹)이 다 있으면 ``create_on_apply``(남은 조건은 반영 때 읽는 그룹 소속·
    장비 컬러 채널뿐).

    칸마다 ``{group_name, bar, state, fields: [{field, field_label, value, kind,
    reason}]}``. ``kind``: ``"empty"``/``"pool_unread"``/``"create_on_apply"``.
    ``state``: ``"create"``(빈 번호가 전부 반영 때 만들어짐) · ``"held"``(반영에서
    송신 보류 — 승인 대기 칸이든 승인된 칸이든, 카드 t600)."""
    # 순환 import 회피(그 모듈이 이 모듈을 import 한다).
    from server.design.beat_grid_color_presets import (
        COLOR_CREATE_ON_APPLY,
        color_grid_blocker,
    )
    from server.design.beat_grid_edit import load_preset_pool_policy
    from server.design.beat_grid_effect_presets import (
        EFFECT_CREATE_ON_APPLY,
        default_effect_library,
        effect_grid_blocker,
    )
    from server.design.beat_grid_position_presets import (
        POSITION_PRESET_POOL,
        position_grid_blocker,
    )

    # 카드 t593 — 빈 효과 번호도 반영 때 템플릿·주기 레시피로 만들어질 수 있다.
    effect_policy: Mapping[str, object] | None = None
    cells: list[dict[str, object]] = []
    for track in grid.get("tracks") or []:
        if not isinstance(track, Mapping):
            continue
        for cue in track.get("cues") or []:
            if not isinstance(cue, Mapping):
                continue
            fields: list[dict[str, object]] = []
            for field, value in _preset_number_fields(cue):
                reason = classify_empty_preset(value, pool_slots, unknown_pool_unread=False)
                if reason is None:
                    continue
                kind = "pool_unread" if reason == POOL_UNREAD_HOLD else "empty"
                if (
                    kind == "empty"
                    and field == "position_preset_no"
                    and preset_pool_no(value) == POSITION_PRESET_POOL
                ):
                    blocker = position_grid_blocker(grid, str(value))
                    if blocker is None:
                        kind = "create_on_apply"
                        reason = POSITION_CREATE_ON_APPLY
                    else:
                        reason = f"{reason}({blocker})"
                elif kind == "empty" and field == "effect_preset_no":
                    if effect_policy is None:
                        effect_policy = load_preset_pool_policy()
                    blocker = effect_grid_blocker(
                        grid, str(value), library=default_effect_library(), policy=effect_policy
                    )
                    if blocker is None:
                        kind = "create_on_apply"
                        reason = EFFECT_CREATE_ON_APPLY
                    else:
                        reason = f"{reason}({blocker})"
                elif kind == "empty" and field == "color_preset_no":
                    blocker = color_grid_blocker(grid, str(value))
                    if blocker is None:
                        kind = "create_on_apply"
                        reason = COLOR_CREATE_ON_APPLY
                    else:
                        reason = f"{reason}({blocker})"
                fields.append(
                    {
                        "field": field,
                        "field_label": _PENDING_PRESET_FIELD_LABELS.get(field, field),
                        "value": value,
                        "kind": kind,
                        "reason": reason,
                    }
                )
            if fields:
                # 카드 t600 — 승인된 칸도 반영 때 같은 규칙으로 가르므로 「approved
                # (그대로 나감)」 상태는 없다.
                state = "create" if all(f["kind"] == "create_on_apply" for f in fields) else "held"
                cells.append(
                    {
                        "group_name": track.get("group_name"),
                        "bar": cue.get("bar"),
                        "state": state,
                        "fields": fields,
                    }
                )
    return cells


def split_empty_preset_holds(
    pending: Sequence[Mapping[str, object]],
    pool_slots: Mapping[int, Mapping[int, object] | None],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """카드 t590, REQ-LDBEAT-015(i-1) — ``pending_preset_approvals``의 열거를
    (승인 기록 대상, 송신 보류)로 가른다.

    ``pool_slots``는 풀 번호 → 완전 판독한 ``{slot: 이름}``(못 읽었으면
    ``None``). slot 이 없는 번호는 아직 콘솔에 값을 만들 길이 없는 빈
    프리셋이고, 풀을 못 읽으면 비었는지 모르므로 같은 보류다. 보류는 **칸
    단위**다 — ``evidence.approval``이 칸 하나에 붙으므로, 칸에 보류 번호가
    하나라도 있으면 그 칸의 다른 번호도 승인 기록 대상에서 뺀다. 보류 항목은
    ``hold_reason``을 단 사본이다."""
    reasons: dict[int, str] = {}
    for index, entry in enumerate(pending):
        reason = classify_empty_preset(entry.get("value"), pool_slots, unknown_pool_unread=True)
        if reason is not None:
            reasons[index] = reason
    held_cells = {(pending[i].get("group_name"), pending[i].get("bar")) for i in reasons}
    approvable: list[dict[str, object]] = []
    held: list[dict[str, object]] = []
    for index, entry in enumerate(pending):
        if (entry.get("group_name"), entry.get("bar")) in held_cells:
            held.append({**entry, "hold_reason": reasons.get(index, CELL_HOLD)})
        else:
            approvable.append(dict(entry))
    return approvable, held


def approval_preview_tracks(
    tracks: Sequence[Mapping[str, object]],
    pending: Sequence[Mapping[str, object]],
    held: Sequence[Mapping[str, object]],
) -> list[Mapping[str, object]]:
    """카드 t615 (A) — 승인 카드에 승인 대기 칸의 줄을 싣기 위한 **미리보기 사본**.

    ``pending``(``pending_before``)이 열거한 칸 가운데, 보류가 걸리지 않고 열거된 (필드, 번호)가
    그 칸의 승인 대기 전부인 칸만 「승인되었다고 가정한」 ``evidence.approval`` 을 단 사본으로
    바꾼다. ``apply_pending_approval`` 이 승인을 적는 조건(카드가 보여 준 집합과 칸의 승인 대기가
    정확히 같을 때)과 같은 조건이므로, 카드에 보인 줄의 칸과 승인 뒤 적히는 칸이 같다.

    원본 격자와 게이트(``check_evidence_approval``)는 건드리지 않는다. 사본은 방출기에 넘겨
    줄을 만드는 데만 쓰고 어디에도 저장하지 않는다. 보류가 섞인 칸은 칸 전체를 빼서, 보류된
    번호가 승인 가정으로 나가지 않게 한다.
    """
    card: dict[tuple[object, object], set[tuple[str, object]]] = {}
    for entry in pending:
        key = (entry.get("group_name"), entry.get("bar"))
        card.setdefault(key, set()).add((str(entry.get("field")), entry.get("value")))
    held_keys = {(entry.get("group_name"), entry.get("bar")) for entry in held}
    previewed: list[Mapping[str, object]] = []
    for track in tracks:
        group_name = track.get("group_name")
        cues: list[object] = []
        for cue in track.get("cues") or []:
            if isinstance(cue, Mapping):
                key = (group_name, cue.get("bar"))
                if (
                    key in card
                    and key not in held_keys
                    and set(pending_preset_fields(cue)) == card[key]
                ):
                    evidence = cue.get("evidence")
                    grade = evidence.get("grade") if isinstance(evidence, Mapping) else None
                    approval = {"by": "supervisor", "date": "preview", "source": "apply-preview"}
                    cue = {**cue, "evidence": {"grade": grade, "approval": approval}}
            cues.append(cue)
        previewed.append({**track, "cues": cues})
    return previewed


def apply_pending_approval(
    grid: Mapping[str, object],
    pending: Sequence[Mapping[str, object]],
    *,
    by: str,
    date: str,
    source: str,
) -> dict[str, object]:
    """카드 t577, REQ-LDBEAT-015(h-2)(h-3)(h-4) — `pending`(``pending_
    preset_approvals``가 돌려준 열거)이 가리키는 칸에 **한해서만**
    `evidence.approval = {by, date, source}`를 기록한 **새 사본**을
    돌려준다. `grid` 자체는 건드리지 않는다(`copy.deepcopy`).

    `pending`에 없는 칸·트랙은 바이트까지 그대로 보존된다 — 승인 카드가
    구성된 **뒤** 다른 편집으로 추가된 새 번호(h-4)는 이 함수가 받는
    `pending`에 없으므로 자연히 승인되지 않는다. `evidence.grade`(증거
    강도)는 그대로 보존하고 `approval`만 갈아 끼운다 — 두 축은 독립이다
    (REQ-LDBEAT-006(vii-2)(vii-3))."""
    updated = copy.deepcopy(dict(grid))
    if not pending:
        return updated
    # 칸마다 카드가 보여준 (필드, 값) 집합 — 칸의 **지금** 승인 대기 필드가
    # 이 집합과 정확히 같을 때만 승인을 적는다. 승인 창이 떠 있는 동안 그
    # 칸 번호가 바뀌었거나 새 번호가 더해졌다면, 감독은 그 번호를 본 적이
    # 없으므로 승인 대기로 남긴다(h-4).
    card_fields: dict[tuple[object, object], set[tuple[str, object]]] = {}
    for entry in pending:
        key = (entry.get("group_name"), entry.get("bar"))
        card_fields.setdefault(key, set()).add((str(entry.get("field")), entry.get("value")))
    targets = set(card_fields)
    tracks = list(updated.get("tracks") or [])
    for track_index, track in enumerate(tracks):
        if not isinstance(track, Mapping):
            continue
        group_name = track.get("group_name")
        cues = list(track.get("cues") or [])
        changed = False
        for cue_index, cue in enumerate(cues):
            if not isinstance(cue, Mapping):
                continue
            key = (group_name, cue.get("bar"))
            if key not in targets:
                continue
            if set(pending_preset_fields(cue)) != card_fields[key]:
                continue
            existing_evidence = cue.get("evidence")
            grade = (
                existing_evidence.get("grade") if isinstance(existing_evidence, Mapping) else None
            )
            cues[cue_index] = {
                **cue,
                "evidence": {
                    "grade": grade,
                    "approval": {"by": by, "date": date, "source": source},
                },
            }
            changed = True
        if changed:
            new_track = dict(track)
            new_track["cues"] = cues
            tracks[track_index] = new_track
    updated["tracks"] = tracks
    return updated
