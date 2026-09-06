"""리그를 보는 룩 선택 — cyc 없는 리그에서 조용한 구간이 큐를 못 받던 결함 (카드 t278).

결함의 자리는 ``songcue._map_section_to_look`` 이다. 요청한 다이내믹스에 맞는
**첫** 룩을 무조건 집는데, 그 선택은 리그를 모른다. cyc/호리 그룹이 없는 리그에서
그 첫 룩이 ``배경``·``탑`` 만 요구하면 번들 단계에서 ``role_unmapped`` 로 건너뛰어지고,
곡의 가장 조용한 구간(보통 인트로)은 큐를 하나도 못 받는다.

ballad 가 멀쩡했던 것은 선택기가 묶이는 룩을 **선호했기 때문이 아니다** — 그런 선호는
없었다. ballad 의 첫 D1 룩 ``ballad-moonlight`` 이 ``배경``+``백라이트`` 를 함께 갖고
있었고 ``_section_bundle`` 이 역할 **하나만** 묶여도 저장하기 때문이다. 이것을 확정하는
반증: worship 은 묶이는 D1 룩(``worship-scripture-key``, 프론트+스페셜)을 **이미
갖고 있었는데도** X 였다. ``worship-prayer-wash`` 가 먼저 정렬되고 아무도 그 너머를
보지 않았기 때문이다.

계측기 규율: O/X 판정은 페이로드 문자열 검색이 아니라 **기록 포트에 ``Store Sequence``
가 도달했는가**로 잰다. 도구 → 게이트 → ``run_commands`` → 실행 포트라는 실제 경로를
그대로 타므로, dedupe 에 접혀 발화되지 않은 커맨드는 도달하지 않는다.
:class:`TestInstrumentIsNotVacuous` 가 이 계측기의 음성 대조군이다.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from server.llm.types import ToolCall
from server.looks.busking import looks_for_genre
from server.looks.loader import load_library_from_dir
from server.looks.resolver import resolve_roles
from server.looks.schema import DYNAMICS_MAX, DYNAMICS_MIN
from server.looks.songcue import build_songcue_bundle, map_sections_to_looks, parse_sections
from server.orchestrator.tools import build_toolset
from server.tests.test_looks_tool import _RecordingPort
from server.tests.test_songcue_tool import _SongCueStatePort, _tree

_TOOL = "prepare_songcue"
_GENRES = ("ballad", "edm", "rock", "worship")

#: 실측 리그(86 fixture)의 그룹 이름 전량. 기존 테스트 리그(``_FULL_GROUPS``)와 달리
#: ``Cyc`` 도 ``Top`` 도 없다 — 바로 그 부재가 이 결함을 가리고 있었다.
_REAL_RIG = (
    "ALL",
    "KEY",
    "FOH",
    "BACK",
    "SIDE-L",
    "SIDE-R",
    "SIDE-ALL",
    "WASH-U",
    "WASH-D",
    "WASH-ALL",
    "MOVER-U",
    "MOVER-D",
    "MOVER-ALL",
    "BLIND",
    "STROBE",
    "HAZE",
    "ODD",
    "EVEN",
)

#: cyc 를 갖춘 대조 리그 — 역할 6종이 전부 묶인다. 무회귀 성질을 재는 자리.
_CYC_RIG = ("Back Wash", "FOH Wash", "Side L", "Top", "Cyc", "Special")

#: 어느 역할에도 안 걸리는 리그 — 계측기가 공허하지 않음을 보이는 음성 대조군.
_UNBINDABLE_RIG = ("FIXTURE-1", "FIXTURE-2", "FIXTURE-3")

#: 구간 어휘가 실제로 내는 다이내믹스 밴드 다섯. ``matching.DYNAMICS_TERMS`` 의
#: 값 집합과 1:1 이며, 감독이 구간에 붙이는 이름이 여기서 온다.
_SECTION_BANDS = (
    ("ambient", (1,)),
    ("intro", (1, 2)),
    ("verse", (2, 3)),
    ("build", (3,)),
    ("chorus", (4, 5)),
)

#: 이 카드가 고치는 밴드 — 요청 구간 안에 묶이는 룩이 **존재하는** 경우.
_REACHABLE_SECTIONS = ("intro", "verse", "build", "chorus")


@pytest.fixture(scope="module")
def library():
    return load_library_from_dir(Path("server/looks/library"))


def _numbered(names: tuple[str, ...]) -> tuple[tuple[int, str], ...]:
    return tuple((index, name) for index, name in enumerate(names, start=11))


def _groups_section(names: tuple[str, ...]) -> dict[str, object]:
    return {
        "objects": [{"no": number, "name": name} for number, name in _numbered(names)],
        "truncated": False,
    }


def _sequences_section() -> dict[str, object]:
    return {"objects": [{"no": 1, "name": "Sequence 1"}], "truncated": False}


def _stored_cues(library, genre: str, section_name: str, rig: tuple[str, ...]) -> list[str]:
    """도구를 실제로 발사하고 **기록 포트에 도달한** ``Store Sequence`` 줄을 돌려준다.

    페이로드를 문자열로 훑지 않는다: 발화 직전에 접히는 커맨드가 있기 때문에
    「번들에 들어 있다」와 「포트에 닿았다」는 같은 사실이 아니다.
    """
    port = _RecordingPort()
    registry = build_toolset(
        execution_port=port,
        state_port=_SongCueStatePort(_tree(groups=_numbered(rig))),
        bundle_gate=None,
        look_library=library,
    )
    execution = registry.dispatch(
        ToolCall(
            id="songcue-rig-aware",
            name=_TOOL,
            arguments={
                "song_title": "리그 인식 테스트",
                "genre": genre,
                "timecode_number": 7,
                "sections": [{"name": section_name, "start": "0:10"}],
            },
        )
    )
    assert execution.result.is_error is False, execution.result.content
    return [command for command in port.executed if command.startswith("Store Sequence")]


def _chosen(library, genre: str, rig: tuple[str, ...], *, dynamics: int):
    """그 다이내믹스를 명시했을 때 번들이 실제로 세운 룩과 건너뛴 사유."""
    section = parse_sections((("Custom", "0:10"),))[0]
    selections = map_sections_to_looks((section,), library, genre, explicit_dynamics={0: dynamics})
    bundle = build_songcue_bundle(
        "리그 인식 테스트",
        selections,
        sequences_section=_sequences_section(),
        groups_section=_groups_section(rig),
    )
    stored = bundle.sections[0]
    look = stored.selection.look
    return (
        bool(bundle.commands),
        look.look_id if look is not None else None,
        stored.skipped[0].reason if stored.skipped else None,
    )


def _naive_first_match(library, genre: str, band: tuple[int, ...]) -> str | None:
    """오늘의 규칙 그 자체 — 다이내믹스가 맞는 **첫** 룩. 무회귀 대조의 기준선이다."""
    for look in looks_for_genre(library, genre):
        if look.dynamics in band:
            return look.look_id
    return None


class TestRealRigCoverage:
    """실측 리그에서 구간이 큐를 받는가 — 이 카드가 고치는 결함 그 자체."""

    def test_the_real_rig_binds_four_of_six_roles(self, library):
        """전제 확인: 탑·배경이 안 묶이는 리그라는 것이 이 결함의 조건이다."""
        resolution = resolve_roles(_groups_section(_REAL_RIG))

        assert set(resolution.mapped) == {"백라이트", "프론트", "사이드", "스페셜"}
        assert {entry.role: entry.reason for entry in resolution.unmapped} == {
            "탑": "no_match",
            "배경": "no_match",
        }

    @pytest.mark.parametrize("genre", _GENRES)
    @pytest.mark.parametrize("section_name", _REACHABLE_SECTIONS)
    def test_every_named_section_reaches_the_console(self, library, genre, section_name):
        """4장르 × 구간 이름 4종이 전부 O — 인트로가 더는 침묵하지 않는다."""
        assert _stored_cues(library, genre, section_name, _REAL_RIG)

    @pytest.mark.parametrize("genre", ("edm", "rock", "worship"))
    def test_the_intro_was_silent_and_is_the_defect_this_card_closes(self, library, genre):
        """인트로는 밴드 (1, 2) 다. 고치기 전 이 셋은 전부 X 였다."""
        assert _stored_cues(library, genre, "intro", _REAL_RIG)


class TestRootFixSignature:
    """라이브러리를 한 줄도 안 고치고 worship D1 이 묶이는 룩을 고르는가.

    「라이브러리 변경 0건」자체는 여기서 재지 않는다 — 그 불변식의 주인은
    ``test_overlap_preserve.py`` 이고, ``server/looks/library/`` 는 그 게이트의
    ``_PRESERVE_PATHS`` 에 이미 들어 있어 매 스위트 실행마다 다시 확인된다.
    여기서 같은 것을 브랜치 기준으로 한 번 더 재면 기준이 흐르는 검사가 하나
    늘 뿐이다(머지 뒤에는 그 범위가 남의 변경까지 삼킨다).
    """

    def test_worship_d1_now_selects_the_bindable_look_that_already_existed(self, library):
        """``worship-scripture-key`` 는 처음부터 있었다 — 아무도 그 너머를 안 봤을 뿐이다."""
        stored, look_id, reason = _chosen(library, "worship", _REAL_RIG, dynamics=1)

        assert (stored, look_id, reason) == (True, "worship-scripture-key", None)


class TestCycRigIsUnchanged:
    """무회귀: cyc 를 갖춘 리그에서는 첫 룩이 이미 묶이므로 선택이 그대로여야 한다."""

    @pytest.mark.parametrize("genre", _GENRES)
    @pytest.mark.parametrize(("section_name", "band"), _SECTION_BANDS)
    def test_the_cyc_rig_still_stores_every_section(self, library, genre, section_name, band):
        assert _stored_cues(library, genre, section_name, _CYC_RIG)

    @pytest.mark.parametrize("genre", _GENRES)
    @pytest.mark.parametrize("dynamics", tuple(range(DYNAMICS_MIN, DYNAMICS_MAX + 1)))
    def test_the_cyc_rig_picks_the_same_look_as_the_naive_first_match(
        self, library, genre, dynamics
    ):
        """오늘의 규칙과 **같은 룩**을 고른다 — 출력이 바이트 동일하다는 성질."""
        stored, look_id, _reason = _chosen(library, genre, _CYC_RIG, dynamics=dynamics)

        assert stored is True
        assert look_id == _naive_first_match(library, genre, (dynamics,))


class TestInstrumentIsNotVacuous:
    """아무것도 안 묶이는 리그에서는 여전히 X 이고, 사유도 오늘의 것 그대로다."""

    @pytest.mark.parametrize("genre", _GENRES)
    def test_nothing_reaches_the_port_when_no_role_binds(self, library, genre):
        assert _stored_cues(library, genre, "chorus", _UNBINDABLE_RIG) == []

    @pytest.mark.parametrize("genre", _GENRES)
    def test_the_skip_reason_is_unchanged(self, library, genre):
        stored, look_id, reason = _chosen(library, genre, _UNBINDABLE_RIG, dynamics=4)

        assert stored is False
        assert reason == "role_unmapped"
        assert look_id == _naive_first_match(library, genre, (4,))


class TestWhatThisFixCannotReach:
    """정직한 기록: (1,) 만 요청하는 어휘는 edm·rock 에서 여전히 X 다.

    선택기가 못 고르는 것이 아니라 **고를 것이 없다** — 두 장르의 D1 룩은 각각
    하나뿐이고 그 룩의 역할은 ``배경`` 뿐이다. 이것을 O 로 만들려면 라이브러리에
    룩을 더해야 하는데, 그 대안은 cyc 리그 출력을 바꾸므로 이 카드가 기각했다.

    아래 단언은 **사유까지** 잰다. 라이브러리가 나중에 묶이는 D1 룩을 얻으면 이
    테스트가 실패하며, 그것이 이 기록을 갱신하라는 신호다.
    """

    @pytest.mark.parametrize("genre", ("edm", "rock"))
    def test_those_genres_have_exactly_one_d1_look_and_it_is_backdrop_only(self, library, genre):
        d1 = [look for look in looks_for_genre(library, genre) if look.dynamics == 1]

        assert [look.roles for look in d1] == [("배경",)]

    @pytest.mark.parametrize("genre", ("edm", "rock"))
    def test_the_ambient_only_band_still_has_no_cue(self, library, genre):
        assert _stored_cues(library, genre, "ambient", _REAL_RIG) == []

    @pytest.mark.parametrize("genre", ("ballad", "worship"))
    def test_the_ambient_only_band_is_covered_where_a_bindable_d1_exists(self, library, genre):
        assert _stored_cues(library, genre, "ambient", _REAL_RIG)


def test_the_matrix_is_recorded_for_the_report(library):
    """보고서에 싣는 O/X 행렬을 한 자리에서 만든다 — 요약이 아니라 실측이다."""
    matrix = {
        genre: "".join(
            "O" if _stored_cues(library, genre, name, _REAL_RIG) else "X"
            for name, _band in _SECTION_BANDS
        )
        for genre in _GENRES
    }

    assert matrix == {
        "ballad": "OOOOO",
        "edm": "XOOOO",
        "rock": "XOOOO",
        "worship": "OOOOO",
    }
