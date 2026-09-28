"""업로드 길(``prepare_songcue``) 입력 → 대화 길 조립기의 계획 — 카드 t480.

SPEC-LDDESIGN-001 REQ-003(AC-017) — 곡 큐를 만드는 길은 하나여야 한다. 대화 길은
감독 인터뷰로 ``UnifiedSongLightingPlan`` 을 짓고 ``compose_song_cue_bundle`` 로 큐를
만든다. 업로드 길도 같은 계획 조립(``_build_unified_song_plan``)과 같은 조립기를
거치도록, 업로드 입력을 그 계획 조립이 받는 모양으로만 바꾸는 것이 이 모듈의 일이다.
연출 판단(역할·D 레벨·팔레트·액센트·효과)은 여기서 하지 않는다 — 전부 계획 조립이 한다.

대화 길과 다른 점은 입력이 없어서 생기는 것뿐이고, 지어내지 않는다:

* 인터뷰 기록이 없으면 팔레트·컨셉이 비어 있다(대화 길에서 감독이 답하기 전과 같다).
* 색 대립 카드(컨셉 색 vs 팔레트)를 띄울 수 없으므로 ``palette_mode`` 는 기본값
  ``"palette"`` 다.
* 포지션 축은 호출자가 끄는 사유를 넘긴다(프리셋 시작 번호가 없으면 라벨을 찾을
  범위가 없다).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace

from server.design.interview import Q1_CONCEPT, Q2_PALETTE, Q2B_COLOR_USAGE, _palette_value_tokens
from server.design.profile import MusicProfile
from server.design.section_palette import role_for_songcue_label
from server.design.song_cue_render import (
    _build_unified_song_plan,
    _confirmed_section_names,
    _infer_confirmed_role,
    _record_value,
    _split_sections_for_density,
)
from server.design.song_plan import TimingPlan, UnifiedSongLightingPlan
from server.looks.songcue import SongCueSection
from server.spatial.position_cuesheet import PositionSheetSection


def upload_plan_sections(
    sections: Sequence[SongCueSection],
    *,
    explicit_dynamics: Mapping[int, int] | None,
    confirmed_default: bool,
) -> list[PositionSheetSection]:
    """업로드 구간 → 계획 조립이 받는 구간 목록.

    * 확정 분석 기본값(운영자가 이름을 안 붙인 확정 구간)은 대화 길의 같은 갈래
      (카드 t302·t393·t391)와 똑같이 D 레벨로 역할을 추정하고 역할+회차 이름을 붙인다
      — 같은 곡이 어느 문으로 들어와도 같은 이름·같은 역할이 나온다.
    * 이름이 있는 구간은 이름을 그대로 두고, 역할은 업로드 길 어휘 판정기
      (``role_for_songcue_label``, t441 이 두 길 색 동일에 쓴 것)로 정한다. 모르는
      어휘면 역할을 비워 계획 조립의 이름 판독에 맡긴다.
    * D 레벨은 명시값(``explicit_dynamics`` — 확정 기록의 실측 D 포함)만 싣는다.
      없으면 비워 계획 조립이 무드·역할 아크로 정하게 한다(대화 길과 같다).
    """
    dynamics = dict(explicit_dynamics or {})
    levels = [dynamics.get(section.index) for section in sections]
    if confirmed_default and levels and all(isinstance(level, int) for level in levels):
        confirmed_levels = [int(level) for level in levels if level is not None]
        roles = [
            _infer_confirmed_role(position, confirmed_levels) for position in range(len(sections))
        ]
        names = _confirmed_section_names(roles)
        return [
            PositionSheetSection(
                name=name, start_ms=section.start_ms, mood="", d_level=level, role=role
            )
            for section, name, level, role in zip(
                sections, names, confirmed_levels, roles, strict=True
            )
        ]
    planned: list[PositionSheetSection] = []
    for section, level in zip(sections, levels, strict=True):
        role = role_for_songcue_label(section.label or section.name)
        planned.append(
            PositionSheetSection(
                name=section.name,
                start_ms=section.start_ms,
                mood="",
                d_level=level,
                role=None if role == "other" else role,
            )
        )
    return planned


def upload_profile(
    *, bpm: float | None, genre: str | None, records: Sequence[object]
) -> MusicProfile:
    """인터뷰가 이미 끝났으면 그 답을 대화 길과 같은 방식으로 접는다
    (``DirectorInterview.working_profile`` — Q1 컨셉·Q2 팔레트 토큰)."""
    concept = _record_value(records, Q1_CONCEPT, None)
    palette = _record_value(records, Q2_PALETTE, None)
    return MusicProfile(
        bpm=bpm,
        genre=genre,
        concept=None if concept is None else str(concept),
        palette=() if palette is None else _palette_value_tokens(palette),
    )


def build_upload_song_plan(
    *,
    song_title: str,
    sections: Sequence[PositionSheetSection],
    bpm: float | None,
    genre: str | None,
    records: Sequence[object],
    rig: object,
    sequence_no: int,
    timing: TimingPlan,
    position_disabled_reason: str = "",
    blinder_group_no: int | None = None,
) -> tuple[UnifiedSongLightingPlan, tuple[str, ...]]:
    """업로드 입력으로 대화 길과 같은 계획을 짓는다 — ``(plan, density_notes)``.

    마디 분할도 대화 길과 같은 함수(``_split_sections_for_density`` — 팔레트 색 수
    기준)로 한다. 업로드 길이 따로 쓰던 룩 후보 수 기준 분할은 조립기로 합치면서
    쓰지 않는다(룩 라이브러리를 거치지 않으므로).
    """
    profile = upload_profile(bpm=bpm, genre=genre, records=records)
    color_usage = _record_value(records, Q2B_COLOR_USAGE, "modulate")
    split, origin, notes = _split_sections_for_density(
        list(sections),
        profile=profile,
        palette_mode="palette",
        concept_colors=(),
        color_usage=color_usage,
    )
    plan = _build_unified_song_plan(
        sections=split,
        profile=profile,
        rig=rig,
        records=records,
        timing=timing,
        sequence_no=sequence_no,
        section_origin=origin or None,
        position_disabled_reason=position_disabled_reason,
        blinder_group_no=blinder_group_no,
    )
    return replace(plan, song_title=song_title), tuple(notes)
