"""M3-b 오프라인 — 인계와 되읽기 검증 (SPEC-COPILOT-MUSICSYNC-001).

AC-MUSICSYNC-022 · 023 · 024 · 025 + 030 · 031 의 오프라인 몫을 판정한다.

이 회차가 판정하지 **못하는** 것: 운영자가 실제로 녹화한 뒤의 되읽기 값.
그것은 실기 리허설의 몫이고, 여기서는 가짜 상태 포트로 되읽기 **모양**만
고정한다. 콘솔 접촉 0건.

설계서 §5 기준 **갈래 B** 가 배달본이다 — M3-a 가 `TrackGroup 1` 아래는 열었고
(`childCount 2`, `MarkerTrack` + `Track`) 재생 명령의 효과는 **증명하지 못했다**.
그래서 인계 목록에는 `Record Timecode <n>` **하나뿐**이고, 이벤트 내용 축은
`SongCueTimingSkip` 으로 좁혀진 채 판정이 `unverified` 를 넘지 않는다.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from server.looks.songcue import SongCueTimingSkip
from server.orchestrator.songcue_timecode import (
    DEFAULT_TIMECODE_POOL_PATH,
    TIMECODE_VERIFY_QUERY_CAP,
    VERDICT_INCONCLUSIVE,
    VERDICT_UNVERIFIED,
    BudgetedStateReader,
    TimecodeQueryBudgetExceeded,
    operator_handoff_commands,
    render_timecode_verification_report,
    verify_songcue_timecode,
)
from server.web.question import QuestionRequest, build_timecode_handoff_card

SERVER_DIR = Path(__file__).resolve().parents[1]

SLOT = 901
TIMECODE_NAME = "MSYNC SONG Timecode"
SEQUENCE_NAME = "MSYNC SONG"

#: 콘솔 명령 모양의 재생 동사들. 산문 오탐을 피하려고 **명령 모양**으로만 센다.
PLAYBACK_VERB_SHAPES = (
    "Go Timecode",
    "Go+ Timecode",
    "Pause Timecode",
    "Toggle Timecode",
    "Play Timecode",
)


def _pool_payload(*, child_count: int = 2, truncated: bool = False) -> dict:
    return {
        "node": {"class": "TimecodePool", "name": "Timecodes", "childCount": child_count},
        "children": [
            {"class": "Timecode", "i": 1, "name": "OTHER SHOW"},
            {"class": "Timecode", "i": SLOT, "name": TIMECODE_NAME},
        ],
        "truncated": truncated,
    }


def _slot_payload(*, name: str = TIMECODE_NAME, truncated: bool = False) -> dict:
    return {
        "node": {"class": "Timecode", "name": name, "childCount": 1},
        "children": [{"class": "TrackGroup", "i": 1, "name": "TrackGroup 1"}],
        "truncated": truncated,
    }


def _trackgroup_payload(*, truncated: bool = False) -> dict:
    return {
        "node": {"class": "TrackGroup", "name": "TrackGroup 1", "childCount": 2},
        "children": [
            {"class": "MarkerTrack", "i": 1, "name": "Marker"},
            {"class": "Track", "i": 2, "name": SEQUENCE_NAME},
        ],
        "truncated": truncated,
    }


class _FakeStatePort:
    """M3-a 2회차가 실제로 본 모양 그대로 답하는 가짜 포트."""

    def __init__(self, tree: dict[str, dict]) -> None:
        self.tree = tree
        self.asked: list[str] = []

    def query_state(self, path: str) -> dict:
        self.asked.append(path)
        try:
            return self.tree[path]
        except KeyError:  # pragma: no cover - 테스트가 경로를 틀렸다는 신호
            raise AssertionError(f"unexpected query path {path!r}") from None


def _healthy_port(**overrides: dict) -> _FakeStatePort:
    slot_path = f"{DEFAULT_TIMECODE_POOL_PATH}/{SLOT}"
    tree = {
        DEFAULT_TIMECODE_POOL_PATH: _pool_payload(),
        slot_path: _slot_payload(),
        f"{slot_path}/TrackGroup 1": _trackgroup_payload(),
    }
    tree.update(overrides)
    return _FakeStatePort(tree)


# ---------------------------------------------------------------------------
# AC-MUSICSYNC-023 — 준비 3줄과 인계 한 줄
# ---------------------------------------------------------------------------


class TestTheHandoffCarriesTheRecordVerbAndNothingElse:
    def test_the_handoff_command_list_is_exactly_the_record_verb(self):
        assert operator_handoff_commands(SLOT) == (f"Record Timecode {SLOT}",)

    def test_the_card_hands_that_one_command_to_the_operator(self):
        card = build_timecode_handoff_card(timecode_number=SLOT, timecode_name=TIMECODE_NAME)
        assert isinstance(card, QuestionRequest)
        assert card.commands == (f"Record Timecode {SLOT}",)

    def test_the_card_uses_todays_question_schema_unchanged(self):
        card = build_timecode_handoff_card(timecode_number=SLOT, timecode_name=TIMECODE_NAME)
        assert set(card.to_dict()) == {
            "prompt",
            "why",
            "steps",
            "commands",
            "options",
            "multi",
        }

    def test_no_playback_verb_is_handed_over_because_m3a_proved_no_effect(self):
        card = build_timecode_handoff_card(timecode_number=SLOT, timecode_name=TIMECODE_NAME)
        rendered = repr(card.to_dict())
        for shape in PLAYBACK_VERB_SHAPES:
            assert shape not in rendered, f"branch B hands over no playback verb, found {shape!r}"

    def test_the_probe_module_does_carry_those_shapes_so_the_scan_is_not_vacuous(self):
        """대조군 — 같은 문자열을 실제로 쓰는 자리가 있어야 위 검사가 눈이 있다."""
        probe = (SERVER_DIR / "tools" / "musicsync_m3a_probe.py").read_text(encoding="utf-8")
        assert any(shape.split()[0] in probe for shape in PLAYBACK_VERB_SHAPES)


# ---------------------------------------------------------------------------
# AC-MUSICSYNC-022 — 앱은 `Record Timecode` 를 쏘지 않는다
# ---------------------------------------------------------------------------


class TestTheAppNeverFiresTheRecordVerb:
    def test_the_literal_lives_in_exactly_one_non_test_module(self):
        hits = sorted(
            path.relative_to(SERVER_DIR).as_posix()
            for path in SERVER_DIR.rglob("*.py")
            if "tests/" not in path.relative_to(SERVER_DIR).as_posix()
            and "Record Timecode" in path.read_text(encoding="utf-8")
        )
        assert hits == ["orchestrator/songcue_timecode.py"], hits

    def test_the_handoff_string_is_never_built_into_an_execution_bundle(self):
        """인계 명령은 `run_commands`/`exec` 인자에 **들어가지 않는다.**

        `songcue_timecode.py` 의 AST 에서 실행 표면 식별자가 0건임을 본다 —
        `server/looks` 경계 검사(`test_looks_boundary.py`)와 같은 형태다.
        """
        source = (SERVER_DIR / "orchestrator" / "songcue_timecode.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        found: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                found.add(node.attr)
            elif isinstance(node, ast.Name):
                found.add(node.id)
        forbidden = {"run_commands", "send_command", "screen", "execution_port", "ConsoleLink"}
        assert not (found & forbidden), sorted(found & forbidden)


class TestPrepareSongcueSurfacesTheHandoffWithoutFiringIt:
    """준비 3줄은 앱이 쏘고, 녹화 명령은 payload 로 **넘긴다**."""

    @staticmethod
    def _payload() -> dict:
        from server.tests.test_songcue_tool import _call, _registry  # noqa: PLC0415

        _execution, payload = _call(_registry())
        return payload

    def test_the_prep_bundle_is_exactly_the_three_m0_lines(self):
        """이름 칸은 `'<ascii>'` 다 — 한국어 제목은 음역돼 실린다(spec.md §A.4)."""
        payload = self._payload()
        assert payload["timing"]["timecode_commands"] == [
            "Store Timecode 7",
            "Set Timecode 7 Property 'Name' 'Song 3 Timecode'",
            "Assign Sequence 3 At Timecode 7",
        ]

    def test_the_record_verb_is_offered_as_a_handoff_not_as_a_fired_command(self):
        payload = self._payload()
        assert payload["timing"]["operator_handoff"]["commands"] == ["Record Timecode 7"]

        fired = [entry["command"] for entry in payload["commands"]]
        assert all("Record Timecode" not in command for command in fired), fired

    def test_no_playback_verb_rides_along_in_the_handoff(self):
        payload = self._payload()
        handed = payload["timing"]["operator_handoff"]["commands"]
        for shape in PLAYBACK_VERB_SHAPES:
            assert all(shape not in command for command in handed), handed


# ---------------------------------------------------------------------------
# AC-MUSICSYNC-025 — 되읽기 네 축 · 조회 4회 이하 · truncated 는 무결론
# ---------------------------------------------------------------------------


class TestTheVerifierStaysInsideFourQueries:
    def test_the_budget_refuses_a_fifth_read(self):
        port = _FakeStatePort({"p": {"node": {}}})
        reader = BudgetedStateReader(port, cap=TIMECODE_VERIFY_QUERY_CAP)
        for _ in range(TIMECODE_VERIFY_QUERY_CAP):
            reader.query("p")
        assert reader.count == TIMECODE_VERIFY_QUERY_CAP == 4
        with pytest.raises(TimecodeQueryBudgetExceeded):
            reader.query("p")
        assert reader.count == TIMECODE_VERIFY_QUERY_CAP, "거절된 조회는 장부에 달리지 않는다"

    def test_branch_b_verification_spends_three_of_the_four(self):
        port = _healthy_port()
        result = verify_songcue_timecode(port, SLOT, TIMECODE_NAME, SEQUENCE_NAME)
        assert result.query_count == 3
        assert result.query_count <= TIMECODE_VERIFY_QUERY_CAP
        assert len(port.asked) == 3

    def test_the_event_axis_costs_the_fourth_query_only_when_a_probe_note_opens_it(self):
        slot_path = f"{DEFAULT_TIMECODE_POOL_PATH}/{SLOT}"
        port = _healthy_port(
            **{
                f"{slot_path}/TrackGroup 1/Track 2": {
                    "node": {"class": "Track", "name": SEQUENCE_NAME, "childCount": 3},
                    "children": [{"class": "TimecodeEvent", "i": 1, "name": "Cue 1"}],
                    "truncated": False,
                }
            }
        )
        result = verify_songcue_timecode(
            port,
            SLOT,
            TIMECODE_NAME,
            SEQUENCE_NAME,
            event_content_probe_note="M3-a run3 opened Track 2 events",
        )
        assert result.query_count == 4 <= TIMECODE_VERIFY_QUERY_CAP


class TestTruncatedIsNeverReadAsSuccess:
    @pytest.mark.parametrize("where", ["pool", "slot", "trackgroup"])
    def test_a_truncated_readback_is_inconclusive(self, where: str):
        slot_path = f"{DEFAULT_TIMECODE_POOL_PATH}/{SLOT}"
        overrides = {
            "pool": {DEFAULT_TIMECODE_POOL_PATH: _pool_payload(truncated=True)},
            "slot": {slot_path: _slot_payload(truncated=True)},
            "trackgroup": {f"{slot_path}/TrackGroup 1": _trackgroup_payload(truncated=True)},
        }[where]
        port = _healthy_port(**overrides)
        result = verify_songcue_timecode(port, SLOT, TIMECODE_NAME, SEQUENCE_NAME)
        assert result.verdict == VERDICT_INCONCLUSIVE
        assert "truncated" in result.reason

    def test_the_inconclusive_artifact_does_not_claim_everything_was_read(self):
        port = _healthy_port(**{DEFAULT_TIMECODE_POOL_PATH: _pool_payload(truncated=True)})
        result = verify_songcue_timecode(port, SLOT, TIMECODE_NAME, SEQUENCE_NAME)
        artifact = render_timecode_verification_report(result, baseline="fake port, offline")
        assert "전부 읽었다" not in artifact
        assert "all read" not in artifact


class TestTheOpenAxesAreRecordedWithValues:
    def test_the_three_open_axes_carry_their_observed_values(self):
        port = _healthy_port()
        result = verify_songcue_timecode(port, SLOT, TIMECODE_NAME, SEQUENCE_NAME)
        axes = {axis.axis: axis for axis in result.axes}
        assert set(axes) == {"pool_presence", "name_match", "trackgroup"}
        assert str(SLOT) in axes["pool_presence"].observed
        assert TIMECODE_NAME in axes["name_match"].observed
        assert axes["name_match"].matched is True
        assert "2" in axes["trackgroup"].observed
        assert "MarkerTrack" in axes["trackgroup"].observed
        assert SEQUENCE_NAME in axes["trackgroup"].observed

    def test_a_name_mismatch_is_recorded_as_a_value_not_swallowed(self):
        slot_path = f"{DEFAULT_TIMECODE_POOL_PATH}/{SLOT}"
        port = _healthy_port(**{slot_path: _slot_payload(name="SOMETHING ELSE")})
        result = verify_songcue_timecode(port, SLOT, TIMECODE_NAME, SEQUENCE_NAME)
        axes = {axis.axis: axis for axis in result.axes}
        assert axes["name_match"].matched is False
        assert "SOMETHING ELSE" in axes["name_match"].observed

    def test_the_event_axis_is_skipped_with_the_existing_descope_vocabulary(self):
        port = _healthy_port()
        result = verify_songcue_timecode(port, SLOT, TIMECODE_NAME, SEQUENCE_NAME)
        assert len(result.skipped) == 1
        skip = result.skipped[0]
        assert isinstance(skip, SongCueTimingSkip)
        assert skip.axis == "timecode_event_content"
        assert skip.reason

    def test_the_verdict_never_reaches_verified_under_branch_b(self):
        port = _healthy_port()
        result = verify_songcue_timecode(port, SLOT, TIMECODE_NAME, SEQUENCE_NAME)
        assert result.verdict == VERDICT_UNVERIFIED
        assert result.verdict != "verified"


# ---------------------------------------------------------------------------
# AC-MUSICSYNC-024 · 031 — 산출물이 5절이고, 좁힌 것을 스스로 말한다
# ---------------------------------------------------------------------------


class TestTheArtifactSaysWhatItCouldNotRead:
    @staticmethod
    def _artifact() -> str:
        port = _healthy_port()
        result = verify_songcue_timecode(port, SLOT, TIMECODE_NAME, SEQUENCE_NAME)
        return render_timecode_verification_report(
            result,
            baseline="fake state port, offline run, no console contact",
            residual_risks=("실기 되읽기 값은 리허설 전까지 미관측",),
        )

    def test_a_the_five_section_titles_are_each_present(self):
        artifact = self._artifact()
        for title in ("주장", "증거", "기준 귀속", "미검증", "잔여 위험"):
            assert artifact.count(title) >= 1, f"missing section title {title!r}"

    def test_b_the_unverified_section_carries_one_of_the_two_literals(self):
        artifact = self._artifact()
        section = artifact.split("## 미검증", 1)[1].split("## 잔여 위험", 1)[0]
        assert ("unverified" in section) or ("SongCueTimingSkip" in section)

    def test_c_the_verdict_field_is_never_verified(self):
        artifact = self._artifact()
        verdict_lines = [
            line for line in artifact.splitlines() if line.strip().startswith("verdict:")
        ]
        assert len(verdict_lines) == 1, verdict_lines
        value = verdict_lines[0].split(":", 1)[1].strip()
        assert value in {"unverified", "SongCueTimingSkip", "inconclusive"}
        assert value != "verified"
