"""`server/presets/store.py` — 일반형 프리셋 저장 빌더.

🔴 **이 파일은 보존 검사가 아니라 신규 커버리지다.**

이 함수는 `server/web/session.py` 에서 옮겨 왔는데, **옮기기 전에 이 함수를
직접 재는 검사가 0건이었다.** 그러므로 이동 후 전량이 초록인 것은
「깨진 게 없다」이지 **「이동이 옳다」가 아니다.** 전량 초록을 이동의 보증으로
쓰면, 원래 아무도 안 보던 함수를 아무도 안 보는 채로 옮긴 것이 된다.

그래서 독스트링이 명시한 규칙을 **표로 덮는다** — 양수 번호 · 빈 라벨 ·
따옴표 거부. 「한 입력에서 같다」로는 이동을 못 지킨다.

순수 함수 검증이다. 콘솔·네트워크 접촉 0.
"""

from __future__ import annotations

import pytest

from server.presets.store import preset_store_commands
from server.spatial.pointing import SpatialPointingError, position_preset_store_commands


class TestOutputShape:
    def test_without_a_label_it_emits_one_line(self):
        assert preset_store_commands(3, 7) == ("Store Preset 3.7",)

    def test_with_a_label_it_emits_the_label_on_its_own_line(self):
        assert preset_store_commands(3, 7, "ALL") == (
            "Store Preset 3.7",
            "Label Preset 3.7 'ALL'",
        )

    def test_a_label_is_stripped_before_use(self):
        assert preset_store_commands(1, 1, "  KEY  ")[1] == "Label Preset 1.1 'KEY'"


class TestRefusalTable:
    """독스트링이 명시한 규칙을 **표로** 덮는다. 한 입력으로는 못 지킨다."""

    @pytest.mark.parametrize("pool_no", [0, -1, -3, True, False, 1.5, "2", None])
    def test_a_non_positive_or_non_int_pool_is_refused(self, pool_no):
        """대칭 검증 — `preset_no` 만 지키고 `pool_no` 를 방치하면
        `Store Preset -3.31` 같은 기형 표적이 조립된다. 풀 번호는 응답기 목록에서
        오므로 신뢰 경계 밖이다."""
        with pytest.raises(SpatialPointingError):
            preset_store_commands(pool_no, 1)

    @pytest.mark.parametrize("preset_no", [0, -1, -99])
    def test_a_non_positive_preset_number_is_refused(self, preset_no):
        with pytest.raises(SpatialPointingError):
            preset_store_commands(1, preset_no)

    @pytest.mark.parametrize("label", ["", "   ", "\t"])
    def test_an_empty_label_is_refused(self, label):
        """빈 라벨은 `Label Preset 1.1 ''` 를 만든다 — 조용히 빈 이름이 붙는다."""
        with pytest.raises(SpatialPointingError):
            preset_store_commands(1, 1, label)

    @pytest.mark.parametrize("label", ["bad'name", 'bad"name', "a'b\"c"])
    def test_a_quoted_label_is_refused(self, label):
        """따옴표는 인용을 조기 종료해 명령 모양을 바꾼다 — 뭉개지 말고 거부한다."""
        with pytest.raises(SpatialPointingError):
            preset_store_commands(1, 1, label)

    def test_a_clean_label_is_the_control(self):
        """비공허성 — 위 거부들이 「무엇이든 거부한다」와 구분되어야 한다."""
        assert preset_store_commands(1, 1, "OK") == (
            "Store Preset 1.1",
            "Label Preset 1.1 'OK'",
        )


class TestCharacterIdentityWithThePositionBuilder:
    """독스트링이 주장하는 등가성을 **직접 잰다**.

    「`pool_no=2` 의 출력은 포지션 빌더와 문자 단위로 동일하다」 — 이 주장이
    검사되지 않으면 두 빌더가 조용히 갈라지고, 그때 어느 쪽이 옳은지 알 수 없다.
    """

    @pytest.mark.parametrize(
        "preset_no,label",
        [(1, None), (3, None), (11, "FAN OUT"), (7, "KEY"), (99, "A B C")],
    )
    def test_pool_two_matches_the_position_builder_character_for_character(self, preset_no, label):
        assert preset_store_commands(2, preset_no, label) == position_preset_store_commands(
            preset_no, label
        )

    def test_a_different_pool_does_not_match(self):
        """비공허성 — 등가성이 「무엇이든 같다」가 아니라 **풀 2에서만**임을 잰다."""
        assert preset_store_commands(3, 7) != position_preset_store_commands(7)

    def test_both_builders_refuse_the_same_bad_label(self):
        """규칙까지 같은지 — 출력만 같고 거부가 갈리면 등가가 아니다."""
        with pytest.raises(SpatialPointingError):
            preset_store_commands(2, 1, "bad'name")
        with pytest.raises(SpatialPointingError):
            position_preset_store_commands(1, "bad'name")


class TestTheMoveItself:
    def test_the_session_layer_no_longer_defines_it(self):
        """이동이 **복사**가 아니었는지 — 정의가 두 곳에 남으면 갈라진다."""
        from pathlib import Path

        source = Path("server/web/session.py").read_text(encoding="utf-8")
        assert "def _preset_store_commands(" not in source

    def test_the_session_layer_still_reaches_it(self):
        """그리고 세션 층이 여전히 같은 함수를 부른다."""
        import server.web.session as session

        assert session._preset_store_commands is preset_store_commands
