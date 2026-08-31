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
            "fx_content_base64",
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


class TestSequenceNameQuoting:
    """'sequence_name' 은 자유 입력이다 -- 전송 명령이 홑따옴표로 감싸는데
    (Store Sequence ... '<name>' ...) 안에 홑따옴표가 있으면 그 자리에서
    문자열이 잘린다. 실기에서 이 실패로 6개 명령이 전멸했었다(리드 재현,
    2026-08-31) -- 이스케이프 없이 fail-closed.
    """

    def test_a_single_quote_in_the_sequence_name_is_refused(self):
        execution = _dispatch(file_content_base64=_b64(b"x"), sequence_name="Sugar's Show")
        assert execution.result.is_error is True
        assert "sequence_name" in execution.result.content
        assert chr(39) in execution.result.content


class TestCueBuilderQuoting:
    """🔴 빌더가 조립하는 명령엔 큰따옴표가 있으면 안 된다.

    server/bridge/protocol.py:_validate_rest 가 큰따옴표를 거절한다(MA3의
    플러그인 인자 종료 문자라서). ma3.txt 정본은 사람이 콘솔에 붙여넣는
    스크립트라 큰따옴표를 쓰지만, 우리 전송 경로는 다르다 -- 큐 빌더가
    ma3.txt 를 그대로 베껴 이 실패를 실기에서 냈다(리드 재현, 2026-08-31:
    Store Sequence 2 "Sugar" /NoConfirm -> 'command must not contain a
    double quote'). 소스 레벨로 못박는다 -- 다음 사람이 정본을 보고 다시
    큰따옴표로 되돌리는 것을 막는다.
    """

    def test_the_sequence_group_and_cue_store_lines_use_single_quotes(self):
        import inspect

        from server.orchestrator import tools as tools_module

        source = inspect.getsource(tools_module)
        assert "Store Sequence {sequence_placement_no} " + chr(39) in source
        assert "Store Sequence {sequence_placement_no} " + chr(34) not in source
        assert "Group " + chr(39) in source
        assert 'f"Group ' + chr(34) not in source
        assert "Store Cue {cueno} " + chr(39) in source
        assert "Store Cue {cueno} " + chr(34) not in source
