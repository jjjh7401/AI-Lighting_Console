"""카드 t430 — ColorRGB_W 채널을 감독 확정 곡 큐 색 경로에 배선한다.

리드 결정 (c)(`.moai/reports/t430/verdict.md` §3): 이 카드는 판독·분기·
트래킹 누수 방지만 한다. 모든 색은 ``W At 0`` — 무대 색 변화는 0이다(W가
켜지긴 하지만 값은 항상 0). 어느 흰색에 W를 실제로 쓸지는 실기 측정 뒤
별도 카드의 몫이다.

이 파일이 지키는 것:

1. ``w_fids``를 안 주면(빈 집합, 기본값) ``_song_color_value_lines``는
   고치기 전과 **바이트 동일**하다 — 회귀 대조군.
2. W 가능 기구는 RGB 줄과 갈라진 별도 줄을 받고, 그 줄은 옛 형태 +
   ``Attribute 'ColorRGB_W' At 0`` 이다(§2 트래킹 누수 방지, verdict.md).
3. 판별 불가 기구는 W를 켜지 않는다(모르는 채널은 안 건드린다).
4. ``_w_capable_fids``(신규)와 ``_color_capable_fids``(기존, 회귀 없음)가
   같은 3단계 판독을 공유하되 서로 다른 판정 기준으로 갈린다.
5. 실제 ``_reviewed_song_commands`` 경로에서도 W 기구에만 W 줄이 붙는다.
"""

from __future__ import annotations

from server.design.color_names import resolve_color_name
from server.design.song_plan import TimingPlan
from server.tests.test_runner_self_correction import ScriptedProvider
from server.tests.test_song_cue_color_emission import (
    _FIDS,
    _color_lines,
    _composition,
    _Stub,
)
from server.tests.test_web_session import (
    _M0_COLOR_ASSIGNMENTS,
    _M0_COLOR_CHANNELS,
    _M0_COLOR_PAIRS,
    _color_fixture_props,
    _ColorChannelRegistry,
    _ColorRigPropPort,
    _session,
)
from server.web.session import (
    ChatSession,
    _color_apply_command,
    _song_color_value_lines,
)

# --------------------------------------------------------------------------
# §1~3 — _song_color_value_lines 단위 시험
# --------------------------------------------------------------------------


class TestNoWSetIsByteIdenticalToBeforeTheChange:
    """카드 조건 「w_fids 빈 집합(기본값) = 오늘과 바이트 동일」의 대조군."""

    def test_before_after_contrast_on_the_same_cue(self) -> None:
        cue = _composition(("blue", "cyan")).bundle.cues[0]
        fids = (1, 2, 3, 4)

        # 고치기 전 형태를 그대로 하드코드 — 회귀 대조군.
        before = (
            "Fixture 1 + 2 + 3 + 4 ; Attribute 'ColorRGB_R' At 5 ; "
            "Attribute 'ColorRGB_G' At 20 ; Attribute 'ColorRGB_B' At 100",
        )
        assert resolve_color_name("blue") == (5, 20, 100)

        lines_no_w, failure_no_w = _song_color_value_lines(cue, fids)
        assert (lines_no_w, failure_no_w) == (before, None)

        # w_fids를 명시적으로 빈 집합으로 줘도 동일(기본값 경로와 갈라지지 않음).
        lines_explicit_empty, _ = _song_color_value_lines(cue, fids, frozenset())
        assert lines_explicit_empty == before

    def test_w_set_rgb_only_line_is_byte_identical_to_the_old_form(self) -> None:
        """W 기구가 섞여도 RGB 전용 줄은 옛 형태와 글자 단위로 같다."""
        cue = _composition(("blue", "cyan")).bundle.cues[0]
        fids = (1, 2, 3, 4)
        w_fids = frozenset({2, 4})

        lines, failure = _song_color_value_lines(cue, fids, w_fids)
        assert failure is None
        assert len(lines) == 2

        rgb_only_line, w_line = lines
        assert rgb_only_line == _color_apply_command((1, 3), (5, 20, 100))
        assert w_line == _color_apply_command((2, 4), (5, 20, 100)) + (
            " ; Attribute 'ColorRGB_W' At 0"
        )


class TestWLineTracking:
    """§2 트래킹 누수 방지 — W 가능 기구엔 항상 W 값을 명시한다."""

    def test_the_w_line_always_states_w_at_0(self) -> None:
        cue = _composition(("magenta", "red")).bundle.cues[0]
        _lines, _failure = _song_color_value_lines(cue, (10,), frozenset({10}))
        (line,) = _lines
        assert line.endswith("Attribute 'ColorRGB_W' At 0")

    def test_cool_white_cue_on_w_fixtures_carries_the_same_rgb_and_w0(self) -> None:
        cue = _composition(("Cool White", "cyan")).bundle.cues[0]
        r, g, b = resolve_color_name("Cool White")
        assert (r, g, b) == (85, 95, 100)

        lines, failure = _song_color_value_lines(cue, (5, 6), frozenset({5, 6}))
        assert failure is None
        (w_line,) = lines
        assert f"Attribute 'ColorRGB_R' At {r} ; Attribute 'ColorRGB_G' At {g} ; " in w_line
        assert f"Attribute 'ColorRGB_B' At {b} ; Attribute 'ColorRGB_W' At 0" in w_line

    def test_warm_white_cue_on_w_fixtures_carries_the_same_rgb_and_w0(self) -> None:
        cue = _composition(("Warm White", "cyan")).bundle.cues[0]
        r, g, b = resolve_color_name("Warm White")
        assert (r, g, b) == (100, 75, 40)

        lines, failure = _song_color_value_lines(cue, (5, 6), frozenset({5, 6}))
        assert failure is None
        (w_line,) = lines
        assert f"Attribute 'ColorRGB_R' At {r} ; Attribute 'ColorRGB_G' At {g} ; " in w_line
        assert f"Attribute 'ColorRGB_B' At {b} ; Attribute 'ColorRGB_W' At 0" in w_line


class TestRigMixShapes:
    """혼합·전W·빈 W 집합·판별 불가 배제."""

    def test_mixed_rig_splits_into_two_lines_in_fid_order(self) -> None:
        cue = _composition(("amber", "red")).bundle.cues[0]
        rgb = resolve_color_name("amber")
        fids = (1, 2, 3, 4)
        w_fids = frozenset({3})

        lines, _failure = _song_color_value_lines(cue, fids, w_fids)
        assert len(lines) == 2
        assert lines[0] == _color_apply_command((1, 2, 4), rgb)
        assert lines[1] == _color_apply_command((3,), rgb) + " ; Attribute 'ColorRGB_W' At 0"

    def test_all_w_rig_emits_only_the_w_line(self) -> None:
        cue = _composition(("green", "red")).bundle.cues[0]
        rgb = resolve_color_name("green")
        fids = (1, 2, 3, 4)
        w_fids = frozenset(fids)

        lines, _failure = _song_color_value_lines(cue, fids, w_fids)
        assert len(lines) == 1
        assert lines[0] == _color_apply_command(fids, rgb) + " ; Attribute 'ColorRGB_W' At 0"

    def test_empty_w_set_emits_only_the_rgb_line(self) -> None:
        cue = _composition(("green", "red")).bundle.cues[0]
        rgb = resolve_color_name("green")
        fids = (1, 2, 3, 4)

        lines, _failure = _song_color_value_lines(cue, fids, frozenset())
        assert lines == (_color_apply_command(fids, rgb),)

    def test_a_fid_absent_from_w_fids_stays_on_the_rgb_line(self) -> None:
        """판별 불가 기구는 w_fids에 안 들어오므로(§5) RGB 줄에 남는다 —
        이 경계는 상태 조립부(`_w_capable_fids` 호출부)가 지키고, 여기서는
        그 결과(멤버십 없음)가 값 라인 생성기에서 항등으로 이어짐을 잰다.
        """
        cue = _composition(("yellow", "red")).bundle.cues[0]
        fids = (1, 2, 3, 4)
        # 판별 불가 기구 3은 w_fids에 없다(호출부가 undetermined를 안 싣는다).
        w_fids = frozenset({2})

        lines, _failure = _song_color_value_lines(cue, fids, w_fids)
        rgb_only_line = next(line for line in lines if "ColorRGB_W" not in line)
        assert " 3 " in rgb_only_line or rgb_only_line.startswith("Fixture 1 + 3")


# --------------------------------------------------------------------------
# §4 — 판별기: _w_capable_fids (신규) / _color_capable_fids (회귀 없음)
# --------------------------------------------------------------------------


def _classify_w(
    tmp_path,
    pairs=None,
    assignments=None,
    channels=None,
    *,
    page_size=None,
    legacy_pager=False,
    fail=(),
):
    """``TestColorCapabilityDiscrimination._discriminate``(test_web_session.py)
    와 같은 배선 — W 채널 판별기를 겨냥한다."""
    provider = ScriptedProvider([])
    session, _console, _audit, _sent, _ = _session(tmp_path, provider)
    calls: list = []
    session._registry = _ColorChannelRegistry(
        calls,
        channels=_M0_COLOR_CHANNELS if channels is None else channels,
        page_size=page_size,
        legacy_pager=legacy_pager,
    )
    port = _ColorRigPropPort(
        _color_fixture_props(_M0_COLOR_ASSIGNMENTS if assignments is None else assignments),
        fail=fail,
    )
    session._current_cue_port = port
    result = session._w_capable_fids(
        _M0_COLOR_PAIRS if pairs is None else pairs, probe_id_prefix="test-w-channel"
    )
    return session, result, calls, port


class TestWCapableFidsClassifier:
    """W present / RGB only / truncated or failed read → undetermined."""

    def test_the_measured_rig_splits_w_capable_and_rgb_only(self, tmp_path) -> None:
        # M0 리그: 슬롯3(fid12)만 LEDBeam350(+W). 나머지 4대는 W 채널이 없고
        # (MMX·Sharpy·Sphere) 전부 완전 판독이므로 rgb_only다.
        _session_obj, (w_capable, rgb_only, undetermined), _calls, _port = _classify_w(tmp_path)

        assert w_capable == [12]
        assert rgb_only == [10, 11, 40, 41]
        assert undetermined == []

    def test_a_w_only_emitter_is_w_capable_by_substring(self, tmp_path) -> None:
        _session_obj, (w_capable, rgb_only, undetermined), _calls, _port = _classify_w(
            tmp_path,
            pairs=[(1, 10)],
            assignments={1: (7, 2)},
            channels={(7, 2): ["Dimmer", "ColorRGB_W"]},
        )
        assert w_capable == [10]
        assert (rgb_only, undetermined) == ([], [])

    def test_a_property_failure_yields_undetermined_not_rgb_only(self, tmp_path) -> None:
        assignments = {1: (2, 1)}
        entries = _color_fixture_props(assignments)
        entries[("Patch/Stages/1/Fixtures/2", "FixtureType")] = "FixtureType 2"
        entries[("Patch/Stages/1/Fixtures/2", "Mode")] = "Mode 1"  # 무번호 모드 — 파싱 불가
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list = []
        session._registry = _ColorChannelRegistry(calls, channels=_M0_COLOR_CHANNELS)
        session._current_cue_port = _ColorRigPropPort(
            entries, fail={("Patch/Stages/1/Fixtures/1", "FixtureType")}
        )

        w_capable, rgb_only, undetermined = session._w_capable_fids(
            [(1, 10), (2, 11)], probe_id_prefix="test-w-channel"
        )
        assert (w_capable, rgb_only) == ([], [])
        assert undetermined == [10, 11]
        assert calls == []  # 판별 못 한 픽스처는 채널 조회 비용도 쓰지 않는다

    def test_a_truncated_unresolved_pager_yields_undetermined(self, tmp_path) -> None:
        channels = {(2, 1): [f"Channel {n}" for n in range(1, 27)] + ["ColorRGB_R"]}
        _session_obj, (w_capable, rgb_only, undetermined), calls, _port = _classify_w(
            tmp_path,
            pairs=[(1, 10)],
            assignments={1: (2, 1)},
            channels=channels,
            page_size=15,
            legacy_pager=True,
        )
        # 무진전 방어 — 에코 부재로 첫 창에서 멈춘다. ColorRGB_W 도 없으니
        # rgb_only 로 오판하면 침묵 축소다 — undetermined 여야 한다.
        assert (w_capable, rgb_only) == ([], [])
        assert undetermined == [10]
        assert len(calls) == 2

    def test_a_nameless_channel_child_blocks_a_rgb_only_verdict(self, tmp_path) -> None:
        _session_obj, (w_capable, rgb_only, undetermined), _calls, _port = _classify_w(
            tmp_path,
            pairs=[(1, 10)],
            assignments={1: (7, 1)},
            channels={(7, 1): ["Dimmer", None, "Gobo1"]},
        )
        assert (w_capable, rgb_only) == ([], [])
        assert undetermined == [10]


class TestColorCapableFidsUnchanged:
    """``_color_capable_fids``는 회귀 없음 — 공유 판독으로 리팩터한 뒤에도
    기존 M0 가짜 채널표에서 예전과 같은 값을 낸다."""

    def test_the_measured_rig_still_splits_into_capable_and_excluded(self, tmp_path) -> None:
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list = []
        session._registry = _ColorChannelRegistry(calls, channels=_M0_COLOR_CHANNELS)
        session._current_cue_port = _ColorRigPropPort(_color_fixture_props(_M0_COLOR_ASSIGNMENTS))
        capable, excluded, undetermined = session._color_capable_fids(
            _M0_COLOR_PAIRS, probe_id_prefix="test-color"
        )
        assert capable == [10, 11, 12]
        assert excluded == [40, 41]
        assert undetermined == []

    def test_a_type_mode_combination_still_probes_its_channels_once(self, tmp_path) -> None:
        """비용 계약 불변 — 조합당 채널 조회 1회(공유 판독 캐시 확인)."""
        provider = ScriptedProvider([])
        session, _console, _audit, _sent, _ = _session(tmp_path, provider)
        calls: list = []
        session._registry = _ColorChannelRegistry(calls, channels=_M0_COLOR_CHANNELS)
        port = _ColorRigPropPort(_color_fixture_props(_M0_COLOR_ASSIGNMENTS))
        session._current_cue_port = port
        session._color_capable_fids(_M0_COLOR_PAIRS, probe_id_prefix="test-color")

        paths = [call.arguments["path"] for call in calls]
        assert len(paths) == 4
        assert len(set(paths)) == 4
        assert len(port.calls) == 2 * len(_M0_COLOR_PAIRS)


# --------------------------------------------------------------------------
# §5 — 실제 _reviewed_song_commands 경로를 통한 곡 흐름 시험
# --------------------------------------------------------------------------


def _commands_with_w(composition, w_fids=frozenset()):
    stub = _Stub()
    commands = ChatSession._reviewed_song_commands(
        stub,
        composition,
        sequence_no=210,
        preset_start=1,
        fids=list(_FIDS),
        timing=TimingPlan.timecode(9),
        layer_mapping=(),
        w_fids=w_fids,
    )
    return commands, stub


class TestSongFlowThroughReviewedSongCommands:
    """진짜 경로 — W 기구가 있는 곡에서만 W 줄이 붙는다."""

    def test_no_w_fixtures_means_no_w_lines(self) -> None:
        composition = _composition(("blue", "cyan"), ("amber", "red"))
        commands, _stub = _commands_with_w(composition)
        lines = _color_lines(commands)
        assert lines, commands
        assert not any("ColorRGB_W" in line for line in lines)

    def test_w_fixtures_get_a_separate_w_line_per_cue(self) -> None:
        # _FIDS = (1, 2, 3, 4) — 2, 4 만 W 가능이라고 가정.
        composition = _composition(("blue", "cyan"), ("amber", "red"))
        w_fids = frozenset({2, 4})
        commands, _stub = _commands_with_w(composition, w_fids)

        w_lines = [c for c in commands if "ColorRGB_W" in c]
        rgb_only_lines = [c for c in commands if "ColorRGB_R" in c and "ColorRGB_W" not in c]
        assert len(w_lines) == 2  # 구간 2개 각각 W 줄 1개
        assert len(rgb_only_lines) == 2
        for line in w_lines:
            assert line.startswith("Fixture 2 + 4 ;")
            assert line.endswith("Attribute 'ColorRGB_W' At 0")
        for line in rgb_only_lines:
            assert line.startswith("Fixture 1 + 3 ;")

    def test_unresolvable_colour_still_reports_failure_with_w_fids_set(self) -> None:
        """W 배선이 §「값을 지어내지 않는다」 계약을 깨지 않는지 대조."""
        composition = _composition(("gold", "cyan"))
        commands, stub = _commands_with_w(composition, frozenset({2, 4}))
        assert not any("ColorRGB" in c for c in commands)
        assert stub._last_color_failures
        assert any("gold" in reason for reason in stub._last_color_failures.values())
