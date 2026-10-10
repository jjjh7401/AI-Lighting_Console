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
표시용으로 남는다.

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

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Literal, TypedDict

import yaml

from server.design.beat_grid_probes import (
    read_m1_probe_results,
    read_m1_probe_results_from_path,
)
from server.design.rig import resolve_layer_role

__all__ = [
    "DEFAULT_BAR_RANGE",
    "LOVE_ATTACK_TITLE",
    "BeatGridBrightness",
    "BeatGridCue",
    "BeatGridEntry",
    "BeatGridTrack",
    "BeatGridView",
    "SceneMemo",
    "attach_beat_grid_default",
    "attach_beat_grid_runtime_extras",
    "default_beat_grid",
    "find_overlapping_group_tracks",
    "normalize_beat_grid_cue",
    "validate_beat_grid_tracks",
]

#: REQ-LDBEAT-006(i-2)/(015)(c) — 밝기는 값/디머 프리셋/디머 효과 프리셋
#: 중 정확히 하나만 쓰는 단일모드다. 셋 다 비어 있으면(아직 미정) `None`.
BrightnessMode = Literal["value", "dimmer_preset", "dimmer_effect"]

#: REQ-LDBEAT-006(i-3)(D9 교정) — 효과 프리셋이 속한 풀의 종류.
EffectKind = Literal["position", "color", "dimmer", "mixed"]


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


class BeatGridCue(TypedDict):
    """격자 칸 하나(카드 t537 구조화, REQ-LDBEAT-006(i-1)~(i-7)). 단일
    ``label`` 서술 문자열이 아니라 속성별 구조화 필드 다섯 종
    (``brightness``·``position_preset_no``·``color_preset_no``·
    ``effect_preset_no``·``entry``)으로 저장된다. ``label``은 레거시
    호환 + 화면 표시용으로 남는다(삭제하지 않는다, REQ-006(ii-3))."""

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
    `None`이다 — 추측 0건."""
    raw_brightness = raw.get("brightness")
    brightness_source: Mapping[str, object] = (
        raw_brightness if isinstance(raw_brightness, Mapping) else {}
    )
    raw_entry = raw.get("entry")
    entry_source: Mapping[str, object] = raw_entry if isinstance(raw_entry, Mapping) else {}
    return BeatGridCue(
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
        ),
        source_ref=raw.get("source_ref"),  # type: ignore[typeddict-item]
    )


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
    바꾸지 않기 위해서다). 두 가지를 한다:

    1. **M1 판정 최신화**(REQ-LDBEAT-003(b)) — `progress_md_path`(없으면
       `beat_grid_probes.default_progress_md_path()`)를 그 자리에서 읽어
       ``beat_grid["probe_results"]``를 덮어쓴다. 표 부재·파싱 실패는
       9항목 전부 "미확인"으로 떨어진다(지어낸 PASS 0건).
    2. **레거시 칸 정규화**(REQ-LDBEAT-006(ii)) — 기존에 저장된 격자(커스텀
       이든 레거시 ``{bar,label}``뿐이든)의 모든 칸을 화면이 읽기 전에
       `normalize_beat_grid_cue`로 통과시켜, 구조화 필드가 없는 칸도
       `None`으로 채운 완전한 모양으로 보낸다 — ``label``은 그대로다.

    ``beat_grid`` 키가 없으면 아무것도 하지 않는다(ADDITIVE, no-op)."""
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
                track["cues"] = [normalize_beat_grid_cue(cue) for cue in raw_cues]
            normalized_tracks.append(track)
        grid["tracks"] = normalized_tracks
    from server.design.beat_grid_probes import default_progress_md_path

    path = progress_md_path if progress_md_path is not None else default_progress_md_path()
    grid["probe_results"] = read_m1_probe_results_from_path(path)
    merged["beat_grid"] = grid
    return merged
