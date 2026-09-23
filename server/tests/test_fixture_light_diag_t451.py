"""t451 — 코파일럿 조명 진단(``diagnose_fixture_light``) 시험.

가짜 콘솔은 t450 실측(``.moai/reports/t450/verdict.md`` §1)을 그대로 싣는다:
Art-Net·sACN ``OUT=false``, 데이터 줄은 유니버스 1 한 칸, 401 은 ``5.151``.
콘솔 쓰기 경로는 이 기능 어디에도 없어야 한다 — 마지막 두 시험이 그것을 잰다.
"""

from __future__ import annotations

import ast
import copy
import json
from pathlib import Path

from server.llm.types import ToolCall
from server.orchestrator.tools import TOOL_NAMES, build_toolset
from server.preshow.fixture_light import (
    ABSENT_PROBE_PATH,
    diagnose_fixture_light,
)

FIXTURES = "Patch/Stages/1/Fixtures"
TYPES = "Patch/FixtureTypes"
ARTNET = "Root/DeviceConfigurations/DMXProtocols/ArtNet"
SACN = "Root/DeviceConfigurations/DMXProtocols/sACN"
CHANNELS_9_2 = f"{TYPES}/9/DMXModes/2/DMXChannels"
CHANNELS_8_1 = f"{TYPES}/8/DMXModes/1/DMXChannels"


def _node(name: str, children: list[dict]) -> dict:
    return {
        "ok": True,
        "node": {"name": name, "class": name, "childCount": len(children), "enumeration": "ok"},
        "children": children,
        "truncated": False,
        "offset": 0,
    }


def _t450_tree() -> tuple[dict[str, dict], dict[str, dict[str, str]]]:
    """(state 응답, 경로별 속성값) — t450 실측값."""
    states = {
        "ShowData": _node("ShowData", [{"i": 13, "name": "Masters", "class": "Masters"}]),
        FIXTURES: _node(
            "Fixtures",
            [
                {"i": 1, "name": "KEY 101", "class": "Fixture"},
                {"i": 67, "name": "WASH-U 401", "class": "Fixture"},
                {"i": 68, "name": "WASH-U 402", "class": "Fixture"},
                {"i": 43, "name": "BACK 201", "class": "Fixture"},
            ],
        ),
        CHANNELS_8_1: _node(
            "DMXChannels",
            [
                {"i": i, "name": f"Aura_{n}", "class": "DMXChannel"}
                for i, n in enumerate(
                    ["Dimmer", "ColorRGB_R", "ColorRGB_G", "ColorRGB_B", "Zoom"], start=1
                )
            ],
        ),
        f"{ARTNET}/ArtNetDataCollect": _node(
            "ArtNetDataCollect", [{"i": 1, "name": "Art-Net-Data 1", "class": "Art-Net-Data"}]
        ),
        f"{SACN}/sACNDataCollect": _node(
            "sACNDataCollect", [{"i": 1, "name": "sACNData 1", "class": "sACNData"}]
        ),
        CHANNELS_9_2: _node(
            "DMXChannels",
            [
                {"i": i, "name": f"Main Module#2_{n}", "class": "DMXChannel"}
                for i, n in enumerate(
                    [
                        "Dimmer",
                        "Shutter1",
                        "ColorRGB_R",
                        "ColorRGB_G",
                        "ColorRGB_B",
                        "ColorRGB_W",
                        "COLORMIXER",
                        "Zoom",
                    ],
                    start=1,
                )
            ],
        ),
        f"{CHANNELS_9_2}/2/1/1": _node(
            "Shutter1 1",
            [
                {"i": 1, "name": "closed", "class": "ChannelSet"},
                {"i": 2, "name": "open", "class": "ChannelSet"},
            ],
        ),
    }
    props = {
        f"{FIXTURES}/1": {"FID": "101", "NAME": "KEY 101"},
        f"{FIXTURES}/67": {
            "FID": "401",
            "NAME": "WASH-U 401",
            "PATCH": "5.151",
            "FIXTURETYPE": "FixtureType 9",
            "MODE": "2 9 channel",
            "MASTERREACT": "Grand",
            "VISIBLE3D": "true",
        },
        f"{FIXTURES}/68": {"FID": "402", "NAME": "WASH-U 402"},
        "ShowData/Masters/Grand/Master": {"NORMEDVALUE": "100"},
        "ShowData/Masters/Grand/World": {"NORMEDVALUE": "100"},
        ARTNET: {"OUT": "false"},
        SACN: {"OUT": "false"},
        f"{ARTNET}/ArtNetDataCollect/1": {"ENABLED": "false", "LOCALUNIVERSE": "1", "AMOUNT": "1"},
        f"{SACN}/sACNDataCollect/1": {"ENABLED": "false", "LOCALUNIVERSE": "1", "AMOUNT": "1"},
        f"{CHANNELS_9_2}/2/1/1/2": {"NAME": "open", "DMXFROM": "526344", "DMXTO": "986895"},
        "Selection": {"COUNTTOTALSELECTED": "0"},
        f"{FIXTURES}/43": {
            "FID": "201",
            "NAME": "BACK 201",
            "PATCH": "4.001",
            "FIXTURETYPE": "FixtureType 8",
            "MODE": "1 Extended - Extended",
            "MASTERREACT": "Grand",
            "VISIBLE3D": "true",
        },
    }
    # 채널 기본값(24비트) — Rush Par 는 색이 전부 0, Aura 는 흰색(255)이 기본이다.
    for i in range(1, 9):
        props[f"{CHANNELS_9_2}/{i}/1/1"] = {"DEFAULT": "0"}
    for i in range(1, 6):
        props[f"{CHANNELS_8_1}/{i}/1/1"] = {"DEFAULT": str(255 * 65793 if i in (2, 3, 4) else 0)}
    return states, props


class FakeConsole:
    """읽기 두 동사만 가진 콘솔 — 없는 경로는 실기 응답기와 같은 문구로 거절한다."""

    def __init__(self, states=None, props=None, *, absent_probe_rejected=True, silent=False):
        base_states, base_props = _t450_tree()
        self.states = base_states if states is None else states
        self.props = base_props if props is None else props
        self.absent_probe_rejected = absent_probe_rejected
        self.silent = silent
        self.calls: list[tuple[str, str]] = []

    def query_state(self, path: str, *, offset: int = 0) -> dict:
        self.calls.append(("state", path))
        if self.silent:
            raise TimeoutError(f"no state reply for {path!r} within 3.0s")
        if path == ABSENT_PROBE_PATH and not self.absent_probe_rejected:
            return _node("Ghost", [])  # 날조 경로를 받아 주는 죽은 계기
        if path not in self.states:
            raise RuntimeError(f"path segment not found: '{path.rsplit('/', 1)[-1]}' (in {path})")
        return copy.deepcopy(self.states[path])

    def query_property(self, path: str, property_name: str) -> dict:
        self.calls.append(("prop", f"{path}|{property_name}"))
        if self.silent:
            raise TimeoutError("no property reply within 3.0s")
        value = self.props.get(path, {}).get(property_name)
        if value is None:
            return {"ok": False, "error": f"property not readable: {property_name}"}
        return {"ok": True, "value": value}


def _run(console: FakeConsole, fid: int = 401):
    return diagnose_fixture_light(fid, state_port=console, property_port=console)


def _by_key(result) -> dict[str, dict]:
    return {f["key"]: f for f in result.to_dict()["findings"]}


class TestT450Reproduction:
    def test_network_output_is_reference_only_never_a_3d_cause(self):
        # t450 정정: 3D 창에서 다른 기구는 켜진다 — OUT=false 는 외부 출력용 참고다.
        findings = _by_key(_run(FakeConsole()))
        assert findings["dmx_output"]["status"] == "info"
        assert findings["universe_coverage"]["status"] == "info"
        assert "5" in findings["universe_coverage"]["observed"]
        assert "3D 창의 원인이 아니다" in findings["dmx_output"]["detail"]
        for key in ("instrument", "fixture", "grand_master", "world_master", "visible_3d"):
            assert findings[key]["status"] == "ok", key

    def test_shutter_is_reported_with_its_open_range_as_a_condition(self):
        findings = _by_key(_run(FakeConsole()))
        assert findings["channels"]["status"] == "ok"
        assert "Shutter1" in findings["channels"]["observed"]
        shutter = findings["shutter_range"]
        # 셔터 값은 앱이 못 읽는다 — 「콘솔에서 열림 확인」 안내로만 낸다(앱은 셔터를 안 건드린다).
        assert shutter["status"] == "app_cannot_check"
        assert "Shutter" in shutter["where_to_look"]
        assert (
            "8" in shutter["observed"] and "15" in shutter["observed"]
        )  # 526344/65793, 986895/65793

    def test_what_the_app_cannot_read_is_said_honestly(self):
        findings = _by_key(_run(FakeConsole()))
        for key in ("beam_fader", "gpu_warning", "control_group"):
            assert findings[key]["status"] == "app_cannot_check", key
            assert findings[key]["where_to_look"], key
        assert findings["programmer_values"]["status"] == "unknown"
        assert "미확인" in findings["programmer_values"]["detail"]

    def test_the_korean_summary_names_the_output_and_the_beam_fader(self):
        summary = _run(FakeConsole()).summary
        assert "DMX 네트워크 출력 꺼짐" in summary
        assert "3D Beam 페이더 확인" in summary
        causes = summary.split("[앱이 확인 못함")[0]
        assert "DMX 네트워크 출력" not in causes  # 원인 후보 칸에는 없다
        # 대조군 질문이 맨 먼저 — t450 에서 가장 싼 판별자였다.
        assert summary.splitlines()[0].startswith("먼저 확인")

    def test_selection_is_read_from_count_total_selected(self):
        console = FakeConsole()
        findings = _by_key(_run(console))
        assert findings["selection"]["observed"] == "0"
        assert ("prop", "Selection|COUNTTOTALSELECTED") in console.calls

    def test_all_zero_color_defaults_are_a_candidate_cause(self):
        findings = _by_key(_run(FakeConsole()))
        assert findings["color_default"]["status"] == "candidate"
        assert "ColorRGB_W 0" in findings["color_default"]["observed"]
        summary = _run(FakeConsole()).summary
        assert "[원인 후보 — 이상]" in summary


class TestCompareWithALitFixture:
    def test_differences_from_a_lit_fixture_become_candidates(self):
        console = FakeConsole()
        result = diagnose_fixture_light(
            401, state_port=console, property_port=console, compare_fid=201
        )
        compare = _by_key(result)["compare"]
        assert compare["status"] == "candidate"
        assert "FixtureType 9 ↔ FixtureType 8" in compare["observed"]
        assert "Shutter1" in compare["observed"]  # 401 에만 있는 채널
        assert "ColorRGB_R 기본값: 0 ↔ 255" in compare["observed"]
        assert result.summary.splitlines()[0].startswith("먼저 확인: 켜지는 기구 201")
        first_cause = result.summary.split("[원인 후보 — 이상]")[1].splitlines()[1]
        assert first_cause.startswith("- 켜지는 기구 201 와 대조")  # 비교가 1순위
        assert "control_group" not in _by_key(result)

    def test_identical_fixtures_say_the_remaining_gap_is_programmer_values(self):
        console = FakeConsole()
        result = diagnose_fixture_light(
            401, state_port=console, property_port=console, compare_fid=401
        )
        compare = _by_key(result)["compare"]
        assert compare["status"] == "info"
        assert "프로그래머 값" in compare["detail"]


class TestOtherCauses:
    def test_grand_master_at_zero_is_abnormal(self):
        console = FakeConsole()
        console.props["ShowData/Masters/Grand/Master"]["NORMEDVALUE"] = "0"
        findings = _by_key(_run(console))
        assert findings["grand_master"]["status"] == "abnormal"
        assert "그랜드 마스터" in _run(console).summary

    def test_enabled_output_covering_the_universe_is_reported_as_covered(self):
        console = FakeConsole()
        console.props[ARTNET]["OUT"] = "true"
        console.props[f"{ARTNET}/ArtNetDataCollect/1"].update(
            {"ENABLED": "true", "LOCALUNIVERSE": "1", "AMOUNT": "8"}
        )
        result = _run(console)
        findings = _by_key(result)
        assert findings["dmx_output"]["status"] == "info"
        assert findings["dmx_output"]["detail"].startswith("켜져 있다")
        assert "Art-Net 가 덮는다" in findings["universe_coverage"]["detail"]
        assert "DMX 네트워크 출력 꺼짐" not in result.summary

    def test_a_fixture_missing_from_the_patch_is_abnormal_and_skips_fixture_items(self):
        result = _run(FakeConsole(), fid=999)
        findings = _by_key(result)
        assert findings["fixture"]["status"] == "abnormal"
        assert "channels" not in findings
        assert "999" in result.summary

    def test_a_failed_read_is_unknown_never_abnormal(self):
        console = FakeConsole()
        del console.props["ShowData/Masters/Grand/World"]
        findings = _by_key(_run(console))
        assert findings["world_master"]["status"] == "unknown"


class TestInstrument:
    def test_a_console_that_accepts_a_fabricated_path_stops_the_diagnosis(self):
        console = FakeConsole(absent_probe_rejected=False)
        result = _run(console)
        assert result.stopped
        assert [f["key"] for f in result.to_dict()["findings"]] == ["instrument"]
        assert "믿을 수 없" in result.summary

    def test_a_timeout_on_the_fabricated_path_is_not_a_rejection(self):
        # 침묵은 거절과 다르다 — 「없다」는 응답만 계기가 살아 있다는 증거다.
        class TimesOutOnProbe(FakeConsole):
            def query_state(self, path, *, offset=0):
                if path == ABSENT_PROBE_PATH:
                    raise TimeoutError(f"no state reply for {path!r} within 3.0s")
                return super().query_state(path, offset=offset)

        result = _run(TimesOutOnProbe())
        assert result.stopped
        assert [f["key"] for f in result.to_dict()["findings"]] == ["instrument"]

    def test_a_silent_console_stops_the_diagnosis(self):
        result = _run(FakeConsole(silent=True))
        assert result.stopped
        assert "응답" in result.summary


class TestToolRegistration:
    def _registry(self, console):
        return build_toolset(execution_port=object(), state_port=console)

    def test_the_tool_is_declared_and_dispatches_a_summary(self):
        assert "diagnose_fixture_light" in TOOL_NAMES
        registry = self._registry(FakeConsole())
        call = ToolCall(id="c1", name="diagnose_fixture_light", arguments={"fid": 401})
        execution = registry.dispatch(call)
        payload = json.loads(execution.result.content)
        assert "DMX 네트워크 출력 꺼짐" in payload["summary"]
        assert execution.command_outcomes == ()

    def test_a_non_integer_fid_is_refused(self):
        registry = self._registry(FakeConsole())
        call = ToolCall(id="c1", name="diagnose_fixture_light", arguments={"fid": "401"})
        assert registry.dispatch(call).result.is_error


class TestReadOnly:
    def test_the_module_imports_nothing_that_can_write(self):
        source = Path("server/preshow/fixture_light.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported = {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        }
        assert not any(m.startswith(("server.bridge", "server.safety")) for m in imported)
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        assert "execution_port" not in names

    def test_only_read_verbs_reach_the_console(self):
        console = FakeConsole()
        _run(console)
        assert {verb for verb, _ in console.calls} <= {"state", "prop"}
