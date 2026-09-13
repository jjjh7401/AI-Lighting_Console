"""t358 — 새 곡이 앞 곡의 룩으로 열리지 않는다.

정본은 ``docs/proposals/song-structure-lighting-standard.md`` §7(후반: 곡 사이에는
룩·고보·이펙트를 재사용하지 않는다) · §12 항목 2(룩을 이름 알파벳 순으로 고른다).

**고치기 전에 실측한 것**(2026-09-12, main fbf7b4f): ``busking.looks_for_genre`` 가
장르의 룩을 ``(dynamics, look_id)`` 로 정렬해 돌려주고 ``songcue._map_section_to_look``
이 그 선두(``matches[0]``)를 고른다. 두 값 모두 곡에 의존하지 않으므로, 같은 장르의
곡 B 의 첫 후렴은 곡 A 의 첫 후렴이 고른 **바로 그 룩**이다.

이 파일이 재는 것은 두 팔이다. 양성 — 기억을 들고 고르면 곡 B 가 다른 룩으로 열린다.
날조 대조군 — 같은 입력을 기억 **없이** 고르면 옛 동작(같은 룩)이 그대로 돌아온다.
뒤쪽이 없으면 앞쪽 단정이 공허할 수 있다: 두 곡의 룩이 원래부터 달랐을 수도 있으니까.
"""

from __future__ import annotations

import json

from server.llm.types import ToolCall
from server.looks.loader import load_library_from_dir
from server.looks.schema import LookLibrary
from server.looks.song_history import SongLookMemory
from server.looks.songcue import (
    LADDER_DIMMER_HIT,
    LOOK_POOL_EXHAUSTED,
    build_songcue_bundle,
    map_sections_to_looks,
    parse_sections,
)
from server.orchestrator.tools import build_toolset
from server.tests.busking_fixtures import FULL_RIG
from server.tests.test_looks_instantiate import _groups
from server.tests.test_looks_tool import _RecordingGate, _RecordingPort
from server.tests.test_songcue_tool import _look, _SongCueStatePort, _tree

#: 두 곡이 **같은 모양**이어야 「룩이 달라진 것은 곡이 달라서가 아니다」가 성립한다.
_THREE_CHORUSES = (("Chorus", "0:00"), ("Chorus", "0:40"), ("Chorus", "1:20"))


def _looks_of(selections) -> list[str]:
    return [selection.look.look_id for selection in selections]


class TestTheSecondSongOpensElsewhere:
    """양성 팔 — 곡 B 는 곡 A 의 룩으로 열리지 않고, 곡 B 안에서는 그 룩이 되돌아온다."""

    def test_song_b_avoids_song_a_while_its_own_choruses_keep_one_look(self):
        """정본 §7 의 비대칭을 **한 검사에서** 둘 다 단정한다.

        두 축이 한 코드 경로에서 갈리므로 따로 재면 한쪽만 참인 상태를 놓친다 — 곡 사이
        회피를 곡 안으로 흘리면 곡 B 의 후렴 2회차가 1회차를 피해 다른 룩으로 갈아타고,
        그 순간 「돌아와야 하는 것이 사라진다」는 t355 가 고친 결함이 되돌아온다.
        """
        library = load_library_from_dir()
        sections = parse_sections(_THREE_CHORUSES)

        song_a = map_sections_to_looks(sections, library, "edm")
        song_b = map_sections_to_looks(sections, library, "edm", used_look_ids=_looks_of(song_a))

        # ① 곡 사이 — 곡 B 는 곡 A 가 쓴 룩을 하나도 쓰지 않는다.
        assert _looks_of(song_a) == ["edm-drop-acid"] * 3
        assert _looks_of(song_b) == ["edm-drop-beams"] * 3
        assert not set(_looks_of(song_b)) & set(_looks_of(song_a))

        # ② 곡 안 — 곡 B 의 세 후렴은 **같은 룩**이고, 사다리로 회차마다 달라진다.
        bundle = build_songcue_bundle(
            "Song B",
            song_b,
            sequences_section=_sequences(),
            groups_section=_groups(*FULL_RIG),
        )
        assert len(bundle.stored_sections) == 3
        assert bundle.skipped == ()
        lines = [section.commands[2] for section in bundle.stored_sections]
        assert len(set(lines)) == 3, "세 회차의 값 라인이 서로 달라야 한다"
        assert bundle.stored_sections[0].ladder == ()
        assert LADDER_DIMMER_HIT in bundle.stored_sections[1].ladder

    def test_without_the_memory_song_b_opens_on_song_a_look(self):
        """날조 대조군 — 기억을 빼면 옛 ``matches[0]`` 동작이 그대로 돌아온다.

        위 단정이 「두 곡은 원래 다른 룩을 고른다」를 재고 있는 것이 아니라는 증거다.
        """
        library = load_library_from_dir()
        sections = parse_sections(_THREE_CHORUSES)

        song_a = map_sections_to_looks(sections, library, "edm")
        song_b = map_sections_to_looks(sections, library, "edm")

        assert _looks_of(song_b) == _looks_of(song_a)


class TestThePoolCanRunOut:
    """정본 §7 을 지킬 룩이 남지 않은 회차 — 재사용으로 내려앉되 **조용하지 않게**."""

    def test_every_look_used_reports_the_fallback_and_still_stores_the_cue(self):
        library = _two_chorus_looks()
        sections = parse_sections((("Chorus", "0:00"),))

        exhausted = map_sections_to_looks(
            sections, library, "rock", used_look_ids=("chorus-a", "chorus-b")
        )

        assert exhausted[0].reuse_reason == LOOK_POOL_EXHAUSTED
        # 큐를 버리지 않는다 — 재사용이 「큐 없음」보다 낫다.
        assert exhausted[0].look.look_id == "chorus-a"
        bundle = build_songcue_bundle(
            "Song C",
            exhausted,
            sequences_section=_sequences(),
            groups_section=_groups(*FULL_RIG),
        )
        assert len(bundle.stored_sections) == 1

    def test_one_look_left_is_not_a_fallback(self):
        """대조군 — 남은 룩이 하나라도 있으면 그것을 고르고 사유를 안 붙인다.

        위 단정이 「기억이 있으면 항상 고갈」을 재는 것이 아니라는 증거.
        """
        library = _two_chorus_looks()
        sections = parse_sections((("Chorus", "0:00"),))

        remaining = map_sections_to_looks(sections, library, "rock", used_look_ids=("chorus-a",))

        assert remaining[0].reuse_reason is None
        assert remaining[0].look.look_id == "chorus-b"


class TestNoHistoryIsByteIdentical:
    """기억이 없는 곡 하나는 고치기 전과 **바이트 동일**하다."""

    def test_an_empty_history_changes_neither_the_order_nor_the_commands(self):
        library = _two_chorus_looks()
        sections = parse_sections((("Verse", "0:00"), ("Chorus", "0:40")))

        without = map_sections_to_looks(sections, library, "rock")
        with_empty = map_sections_to_looks(sections, library, "rock", used_look_ids=())

        assert without == with_empty
        assert [selection.reuse_reason for selection in without] == [None, None]
        bundle = build_songcue_bundle(
            "Song",
            without,
            sequences_section=_sequences(),
            groups_section=_groups(*FULL_RIG),
        )
        # 카드 t363 이 이 기대값 두 자리를 바꿨다. **무기억 성질은 그대로다** — 이 검사가
        # 재는 것은 「기억을 안 넘긴 호출과 빈 기억을 넘긴 호출이 같은 명령을 낸다」이고,
        # 아래 두 변화는 둘 모두에 똑같이 적용된다:
        #   · 벌스가 55 → 25 로 내려간다. 다음 큐가 §6 chorus · drop 행이므로 드롭 앞
        #     감광이 걸리고, 목표는 §6 verse 행의 바닥 25 다(정본 §8 [HARD]).
        #   · Store 줄에 페이드가 붙는다 — 벌스 2초(§9 부드러운 전환), 후렴 0.2초(§9 극적인 컷).
        # 카드 t377 이 세 번째 변화를 더했다 — 이 픽스처의 룩이 프론트를 안 실어서
        # "Group 12" 프론트 필 두 줄이 큐마다 붙는다(정본 §6.2 [HARD]). 두 번째 큐가
        # 20 이 아니라 21 인 것은 `run_commands` 전곡 단위 중복 제거를 피하려는
        # 유일성 오르기다.
        assert bundle.commands == (
            "ChangeDestination Root",
            "ClearAll",
            "Group 11",
            "Attribute 'Dimmer' At 25",
            "Group 12",
            "Attribute 'Dimmer' At 20 ; Attribute 'ColorRGB_R' At 100 ; "
            "Attribute 'ColorRGB_G' At 75 ; Attribute 'ColorRGB_B' At 52",
            "Store Sequence 1 Cue 1 'Verse' CueFade 2",
            "Label Sequence 1 'Song'",
            "ClearAll",
            "ClearAll",
            "Group 11",
            "Attribute 'Dimmer' At 70",
            "Group 12",
            "Attribute 'Dimmer' At 21 ; Attribute 'ColorRGB_R' At 100 ; "
            "Attribute 'ColorRGB_G' At 75 ; Attribute 'ColorRGB_B' At 52",
            "Store Sequence 1 Cue 2 'Chorus' CueFade 0.2",
            "ClearAll",
        )


class TestTheProductionPathRemembers:
    """이 기억이 **앱에서** 산다는 증거 — 순수 함수가 아니라 ``prepare_songcue`` 로 잰다.

    부품이 초록인 것과 경로가 이어진 것은 다르다: ``used_look_ids`` 를 아무도 안 넘기면
    위 검사들은 전부 통과하면서 앱의 동작은 하나도 안 바뀐다.
    """

    def test_two_songs_in_one_session_do_not_share_a_look(self):
        memory = SongLookMemory()
        registry = _registry(memory=memory)

        first_execution, first = _dispatch(registry, "곡 A")
        _second_execution, second = _dispatch(registry, "곡 B")

        # 되풀이가 없으면 감독 고지에 한 글자도 안 붙는다 — 오늘의 문면과 바이트 동일.
        assert first_execution.operator_notice == ""
        assert first["cross_song_looks"]["memory_wired"] is True
        assert first["cross_song_looks"]["history_before"] == []
        assert first["cross_song_looks"]["stored_look_ids"] == ["chorus-a"]
        assert first["cross_song_looks"]["remembered"] == ["chorus-a"]

        assert second["cross_song_looks"]["history_before"] == ["chorus-a"]
        assert second["cross_song_looks"]["stored_look_ids"] == ["chorus-b"]
        assert second["cross_song_looks"]["reused_look_ids"] == []
        assert memory.used() == ("chorus-a", "chorus-b")

    def test_without_a_wired_memory_the_second_song_repeats_the_first(self):
        """날조 대조군 — 세션이 기억을 안 넘기면 앱은 고치기 전 그대로다."""
        registry = _registry(memory=None)

        _first_execution, first = _dispatch(registry, "곡 A")
        _second_execution, second = _dispatch(registry, "곡 B")

        assert first["cross_song_looks"]["memory_wired"] is False
        assert first["cross_song_looks"]["stored_look_ids"] == ["chorus-a"]
        assert second["cross_song_looks"]["stored_look_ids"] == ["chorus-a"]

    def test_the_third_song_reports_the_exhausted_pool_in_the_payload(self):
        memory = SongLookMemory()
        registry = _registry(memory=memory)

        _dispatch(registry, "곡 A")
        _dispatch(registry, "곡 B")
        third_execution, third = _dispatch(registry, "곡 C")

        exhausted = third["cross_song_looks"]["pool_exhausted_sections"]
        assert [entry["reason"] for entry in exhausted] == [LOOK_POOL_EXHAUSTED]
        assert exhausted[0]["name"] == "Chorus"
        assert third["cross_song_looks"]["reused_look_ids"] == ["chorus-a"]
        # 큐는 그래도 나갔다 — 보고가 있는 재사용이지 침묵이 아니다.
        assert third["report"]["summary"]["generated_count"] == 1
        # 모델이 옮겨 말해 주기를 기대하지 않는다 — 감독이 읽는 고지에 직접 실린다.
        assert "chorus-a" in third_execution.operator_notice
        assert "다시 썼습니다" in third_execution.operator_notice

    def test_a_refused_bundle_is_not_remembered(self):
        """콘솔에 0건이 나간 회차는 기억에 안 들어간다.

        들어가면 다음 곡이 **무대에 오른 적 없는** 룩을 피하게 되고, 팔레트가 이유 없이
        좁아진다. 게이트 거절은 그 갈래의 유일한 실측 가능한 형태다.
        """
        memory = SongLookMemory()
        registry = _registry(memory=memory, gate=_RecordingGate(cleared=False, status="rejected"))

        _execution, payload = _dispatch(registry, "곡 A")

        assert payload["cross_song_looks"]["stored_look_ids"] == ["chorus-a"]
        assert payload["cross_song_looks"]["remembered"] == []
        assert memory.used() == ()


def _two_chorus_looks() -> LookLibrary:
    """같은 세기(D4)의 룩 **둘** — 하나뿐이면 회피할 자리가 없어 무엇도 못 잰다."""
    return LookLibrary(
        schema_version=1,
        looks=(
            _look("verse", dynamics=2, value=55),
            _look("chorus-a", dynamics=4, value=70),
            _look("chorus-b", dynamics=4, value=60),
        ),
    )


def _registry(*, memory: SongLookMemory | None, gate=None):
    return build_toolset(
        execution_port=_RecordingPort(),
        state_port=_SongCueStatePort(_tree()),
        bundle_gate=gate,
        look_library=_two_chorus_looks(),
        song_look_memory=memory,
    )


def _dispatch(registry, song_title: str):
    execution = registry.dispatch(
        ToolCall(
            id=f"songcue-{song_title}",
            name="prepare_songcue",
            arguments={
                "song_title": song_title,
                "genre": "록",
                "timecode_number": 7,
                "sections": [{"name": "Chorus", "start": "0:10"}],
            },
        )
    )
    return execution, json.loads(execution.result.content)


def _sequences(*numbers: int) -> dict[str, object]:
    return {
        "objects": [{"no": number, "name": f"Sequence {number}"} for number in numbers],
        "truncated": False,
        "total": len(numbers),
    }
