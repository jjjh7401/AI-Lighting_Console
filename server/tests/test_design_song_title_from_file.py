"""설계 초안 곡 이름 — 첨부 곡 파일 이름에서 후보를 만든다(리드 결정: 옵션 b).

설계 흐름은 곡 이름을 받지 않고 「Design Interview」로 고정했다. 그래서 LOVE ATTACK 을
첨부해도 곡별 기본 격자가 붙지 않았다. 첨부 파일 이름(확장자 뺀 것)을 후보로 쓰고, 감독이
화면에서 바꿀 수 있게 한다. 첨부가 없으면 예전처럼 「Design Interview」다.
"""

from __future__ import annotations

from server.design.beat_grid import attach_beat_grid_default
from server.design.profile import MusicProfile
from server.design.rig import build_rig_profile
from server.design.song_cue_render import (
    _DESIGN_INTERVIEW_TITLE,
    _build_unified_song_plan,
    design_song_title_from_file_name,
)
from server.design.song_plan import TimingPlan
from server.web.session import SongAudioUpload, SongTimelineStore

from .test_session_bar_map_store import _new_session
from .test_song_palette_occurrence_t402 import _confirmed_sections


def test_file_name_becomes_the_song_title_without_its_extension() -> None:
    assert design_song_title_from_file_name("LOVE ATTACK.mp3") == "LOVE ATTACK"
    assert design_song_title_from_file_name("Mr. Brightside.mp3") == "Mr. Brightside"
    assert design_song_title_from_file_name("  LOVE ATTACK  .m4a") == "LOVE ATTACK"
    assert design_song_title_from_file_name("LOVE ATTACK") == "LOVE ATTACK"


def test_directory_parts_are_dropped_before_the_name_is_taken() -> None:
    assert design_song_title_from_file_name("C:\\Music\\LOVE ATTACK.wav") == "LOVE ATTACK"
    assert design_song_title_from_file_name("/tmp/listen/LOVE ATTACK.flac") == "LOVE ATTACK"


def test_no_usable_name_keeps_the_generic_title() -> None:
    assert design_song_title_from_file_name(None) == _DESIGN_INTERVIEW_TITLE
    assert design_song_title_from_file_name("") == _DESIGN_INTERVIEW_TITLE
    assert design_song_title_from_file_name(".mp3") == _DESIGN_INTERVIEW_TITLE


def test_design_session_takes_the_attached_song_name(tmp_path) -> None:
    store = SongTimelineStore()
    session, _console = _new_session(tmp_path, store=store)
    assert session._design_song_title() == _DESIGN_INTERVIEW_TITLE  # 아직 첨부 없음

    session._song_audio = SongAudioUpload(
        file_name="LOVE ATTACK.mp3",
        mime_type="audio/mpeg",
        content_base64="",
        sha256="0" * 64,
        byte_length=1,
    )

    assert session._design_song_title() == "LOVE ATTACK"


def test_built_plan_carries_the_given_title_and_defaults_to_the_generic_one() -> None:
    kwargs = dict(
        sections=_confirmed_sections([2, 3, 4, 3]),
        profile=MusicProfile(),
        rig=build_rig_profile(patch=[], groups={}, coords=[]),
        records=(),
        timing=TimingPlan.manual_go(),
        sequence_no=120,
    )

    assert _build_unified_song_plan(**kwargs).song_title == _DESIGN_INTERVIEW_TITLE
    named = _build_unified_song_plan(**kwargs, song_title="LOVE ATTACK")
    assert named.song_title == "LOVE ATTACK"


def test_the_attached_name_brings_the_registered_default_grid() -> None:
    kwargs = dict(
        sections=_confirmed_sections([2, 3, 4, 3]),
        profile=MusicProfile(),
        rig=build_rig_profile(patch=[], groups={}, coords=[]),
        records=(),
        timing=TimingPlan.manual_go(),
        sequence_no=120,
    )
    plan = _build_unified_song_plan(**kwargs, song_title="LOVE ATTACK")

    grid = attach_beat_grid_default({"song_title": plan.song_title})["beat_grid"]

    assert grid["tracks"], "첨부한 곡 이름으로 LOVE ATTACK 기본 격자가 붙어야 한다"
