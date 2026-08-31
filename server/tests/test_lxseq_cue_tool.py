"""SPEC-COPILOT-LXSEQ-004 M3 (t209) -- import_lxseq_cues registration.

Scope: registration only. cue_mapper.py does not exist yet (sync lane, a
separate branch) so anything past header validation is expected to refuse
gracefully rather than reach the missing mapper. Console contact: 0.
"""

from __future__ import annotations

import json

from server.llm.types import ToolCall
from server.lxseq.cue_parser import CANONICAL_CUE_COLUMNS
from server.orchestrator.tools import TOOL_NAMES, build_toolset
from server.tests.test_lxseq_tool import Answers, FakeConsole, FakeDeploy, FakeExec, _b64


def _toolset():
    console = FakeConsole()
    return build_toolset(
        execution_port=FakeExec(console),
        state_port=console,
        property_port=console,
        deploy_pipeline=FakeDeploy(console),
        question_port=Answers(),
    )


def _dispatch(**arguments):
    registry = _toolset()
    return registry.dispatch(ToolCall(id="t209", name="import_lxseq_cues", arguments=arguments))


class TestRegistration:
    def test_the_tool_is_registered(self):
        assert "import_lxseq_cues" in TOOL_NAMES
        registry = _toolset()
        names = [d.name for d in registry.definitions()]
        assert "import_lxseq_cues" in names

    def test_the_schema_requires_bytes_and_sequence_name(self):
        registry = _toolset()
        definition = next(d for d in registry.definitions() if d.name == "import_lxseq_cues")
        assert set(definition.parameters["required"]) == {"file_content_base64", "sequence_name"}
        assert set(definition.parameters["properties"]) == {
            "file_content_base64",
            "action",
            "sequence_name",
            "preset_dim_content_base64",
            "preset_col_content_base64",
            "preset_bm_content_base64",
        }


class TestArgumentValidation:
    def test_missing_bytes_is_refused(self):
        execution = _dispatch()
        assert execution.result.is_error is True
        assert "file_content_base64" in execution.result.content

    def test_non_base64_is_refused(self):
        execution = _dispatch(file_content_base64="not base64 !!")
        assert execution.result.is_error is True

    def test_an_unknown_action_is_refused(self):
        execution = _dispatch(
            file_content_base64=_b64(b"x"), action="delete", sequence_name="Sugar"
        )
        assert execution.result.is_error is True
        assert "action" in execution.result.content

    def test_a_missing_sequence_name_is_refused(self):
        execution = _dispatch(file_content_base64=_b64(b"x"))
        assert execution.result.is_error is True
        assert "sequence_name" in execution.result.content


class TestHeaderValidation:
    def test_a_missing_column_is_refused_and_named(self):
        header = ",".join(c for c in CANONICAL_CUE_COLUMNS if c != "Snap")
        body = header + "\nQ010,BACK,55,,,,,,,,,,,,,\n"
        execution = _dispatch(file_content_base64=_b64(body.encode("utf-8")), sequence_name="Sugar")
        assert execution.result.is_error is True
        assert "Snap" in execution.result.content


class TestParserReachedButMapperPending:
    """cue_mapper.py belongs to the sync lane -- this card only proves the
    handler reaches that boundary and fails gracefully, not through it."""

    def test_a_well_formed_sheet_parses_then_refuses_gracefully(self):
        header = ",".join(CANONICAL_CUE_COLUMNS)
        rows = [
            ",".join(["Q010", "BACK", "55"] + [""] * 12 + ["Y", ""]),
            ",".join(["Q010", "LED-W", "60"] + [""] * 12 + ["", "video call"]),
        ]
        body = header + "\n" + "\n".join(rows) + "\n"
        execution = _dispatch(file_content_base64=_b64(body.encode("utf-8")), sequence_name="Sugar")
        # cue_mapper.py now exists (merged) and group_slots/preset_slots resolve
        # against a live console -- FakeConsole/FakeExec here answer with a
        # real-shaped (if empty) rig, so this should reach a clean result, not
        # an exception.
        assert execution.result.is_error is False
        payload = json.loads(execution.result.content)
        assert payload["read"] == 2
        assert payload["cue_numbers"] == ["Q010"]
        assert payload["video_call_rows"] == 1
