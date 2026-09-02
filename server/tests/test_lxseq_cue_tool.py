"""SPEC-COPILOT-LXSEQ-004 M3 (t209) -- import_lxseq_cues registration.

Scope: registration only. cue_mapper.py does not exist yet (sync lane, a
separate branch) so anything past header validation is expected to refuse
gracefully rather than reach the missing mapper. Console contact: 0.
"""

from __future__ import annotations

import base64
import io
import json

import openpyxl

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
            "cue_sheet_xlsx_base64",
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


def _cue_sheet_xlsx(rows):
    """최소 CUE 시트 -- 헤더 4행, 데이터 5행부터(정본과 같은 자리).
    rows 는 (q, section, mood, fade) 튜플의 목록."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "CUE"
    ws.append(("머리글 무시 1행",))
    ws.append(("머리글 무시 2행",))
    ws.append(())
    header = ["Q#", "Section", "TC In", "TC Out", "Dur", "Mood"]
    header += ["Color", "Intensity", "Fixture Group", "Movement", "Effect"]
    header += ["Transition", "Fade", "Note"]
    ws.append(header)
    for q, section, mood, fade in rows:
        row = [q, section, "", "", "", mood, "", "", "", "", "", "", fade, ""]
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return base64.b64encode(buf.getvalue()).decode("ascii")


class _AcceptAllApproval:
    def __init__(self):
        self.requests = []

    def request_approval(self, request):
        self.requests.append(request)
        return True


def _toolset_with_group(group_name, *, approval=None):
    console = FakeConsole(fixtures=[dict(name=group_name)])
    return build_toolset(
        execution_port=FakeExec(console),
        state_port=console,
        property_port=console,
        deploy_pipeline=FakeDeploy(console),
        question_port=Answers(),
        group_approval_port=approval,
    )


class TestCueSheetXlsx:
    """정본 CUE 시트(xlsx) -- 있으면 CueFade 근사 대신 정본 Fade 열,
    라벨을 Q#+Section+Mood 로 낸다. 없으면 지금 동작 그대로(리드 지시,
    2026-08-31). Q060/Q140 은 실기에서 근사가 0.0, 정본이 1.0으로 틀렸던
    두 큐다 -- 이 검사가 그 둘의 유일한 관측 가능한 차이다.
    """

    def _body(self):
        header = ",".join(CANONICAL_CUE_COLUMNS)
        row = ",".join(["Q010", "BACK", "55"] + [""] * 12 + ["", ""])
        return (header + "\n" + row + "\n").encode("utf-8")

    def test_the_sheet_omitted_keeps_the_approximation(self):
        registry = _toolset_with_group("BACK")
        execution = registry.dispatch(
            ToolCall(
                id="t209xlsx1",
                name="import_lxseq_cues",
                arguments=dict(file_content_base64=_b64(self._body()), sequence_name="TestSeq"),
            )
        )
        assert execution.result.is_error is False
        payload = json.loads(execution.result.content)
        note = payload["cue_manual_notes"]["Q010"]
        assert note["cue_fade_is_approximate"] is True
        assert "안 줌" in note["cue_fade_source"]

    def test_the_sheet_supplies_the_real_fade_and_label(self):
        approval = _AcceptAllApproval()
        registry = _toolset_with_group("BACK", approval=approval)
        cue_sheet = _cue_sheet_xlsx([("Q010", "CHORUS1", "유지, 회전", 1.0)])
        execution = registry.dispatch(
            ToolCall(
                id="t209xlsx2",
                name="import_lxseq_cues",
                arguments=dict(
                    file_content_base64=_b64(self._body()),
                    sequence_name="TestSeq",
                    action="apply",
                    cue_sheet_xlsx_base64=cue_sheet,
                ),
            )
        )
        assert execution.result.is_error is False
        payload = json.loads(execution.result.content)
        note = payload["cue_manual_notes"]["Q010"]
        assert note["cue_fade_is_approximate"] is False
        assert "정본" in note["cue_fade_source"]
        assert payload["applied"][0]["status"] == "ok"
        commands = [c["command"] for c in payload["applied"][0]["commands"]]
        store_cue = next(c for c in commands if c.startswith("Store Cue"))
        assert (
            store_cue == "Store Cue 10 'Q010 CHORUS1 유지' CueFade 1 Sequence 2 /Merge /NoConfirm"
        )

    def test_q060_and_q140_read_one_point_zero_from_the_canonical_sheet(self):
        """실기에서 틀렸던 정확한 두 큐 -- 근사면 0.0, 정본이면 1.0."""
        approval = _AcceptAllApproval()
        registry = _toolset_with_group("BACK", approval=approval)
        header = ",".join(CANONICAL_CUE_COLUMNS)
        row = ",".join(["Q060", "BACK", "55"] + [""] * 12 + ["", ""])
        body = (header + "\n" + row + "\n").encode("utf-8")
        cue_sheet = _cue_sheet_xlsx([("Q060", "CHORUS1", "유지, 회전", 1.0)])
        execution = registry.dispatch(
            ToolCall(
                id="t209xlsx3",
                name="import_lxseq_cues",
                arguments=dict(
                    file_content_base64=_b64(body),
                    sequence_name="TestSeq",
                    action="apply",
                    cue_sheet_xlsx_base64=cue_sheet,
                ),
            )
        )
        assert execution.result.is_error is False
        payload = json.loads(execution.result.content)
        commands = [c["command"] for c in payload["applied"][0]["commands"]]
        store_cue = next(c for c in commands if c.startswith("Store Cue"))
        assert "CueFade 1 " in store_cue

    def test_a_single_quote_in_mood_is_refused_fail_closed(self):
        registry = _toolset_with_group("BACK")
        cue_sheet = _cue_sheet_xlsx([("Q010", "INTRO", "Rock'n", 1.0)])
        execution = registry.dispatch(
            ToolCall(
                id="t209xlsx4",
                name="import_lxseq_cues",
                arguments=dict(
                    file_content_base64=_b64(self._body()),
                    sequence_name="TestSeq",
                    cue_sheet_xlsx_base64=cue_sheet,
                ),
            )
        )
        assert execution.result.is_error is True
        assert chr(39) in execution.result.content

    def test_missing_cue_sheet_tab_is_refused_with_a_reason(self):
        wb = openpyxl.Workbook()
        wb.active.title = "NOT_CUE"
        buf = io.BytesIO()
        wb.save(buf)
        bad_sheet = base64.b64encode(buf.getvalue()).decode("ascii")
        registry = _toolset_with_group("BACK")
        execution = registry.dispatch(
            ToolCall(
                id="t209xlsx5",
                name="import_lxseq_cues",
                arguments=dict(
                    file_content_base64=_b64(self._body()),
                    sequence_name="TestSeq",
                    cue_sheet_xlsx_base64=bad_sheet,
                ),
            )
        )
        assert execution.result.is_error is True
        assert "CUE" in execution.result.content


class _FailingOnMarkerExec:
    """모든 명령을 성공시키다가 marker 를 포함한 명령에서만 실패한다 --
    skipped_after_failure 단락(short-circuit) 검사에 쓴다."""

    def __init__(self, console, marker):
        self.console = console
        self.marker = marker
        self.sent = []

    def execute(self, command):
        self.sent.append(command)
        if self.marker in command:
            return type("R", (), {"command": command, "ok": False, "detail": "조작된 실패"})()
        return type("R", (), {"command": command, "ok": True, "detail": "OK"})()


class TestApplyPathBranches:
    """action='apply' 의 네 갈래 중 셋 -- 계획 없음 · 승인 거부 ·
    단락(short-circuit). 네 번째(preset_pool_lookup_failed fail-closed)는
    preset_slots 와 preset_pool_no_by_kind 가 tools.py 안에서 항상 같은
    루프로 함께 채워져 정상 입력으로는 못 갈라놓는다 -- 이 방어 분기는
    현재 도달 경로가 없다(별도 관측, 실행하지 않음)."""

    def _row(self, cue_no, group="BACK"):
        return ",".join([cue_no, group, "55"] + [""] * 12 + ["", ""])

    def _body(self, *cue_nos, group="BACK"):
        header = ",".join(CANONICAL_CUE_COLUMNS)
        rows = [self._row(q, group=group) for q in cue_nos]
        return (header + "\n" + "\n".join(rows) + "\n").encode("utf-8")

    def test_no_bundles_gives_a_notice_and_writes_nothing(self):
        """영상 콜만 있는 큐 -- refusal 없이 cue_bundles 가 0건이다."""
        header = ",".join(CANONICAL_CUE_COLUMNS)
        row = ",".join(["Q010", "LED-W", ""] + [""] * 11 + ["", "video call"])
        body = (header + "\n" + row + "\n").encode("utf-8")
        registry = _toolset_with_group("BACK")
        execution = registry.dispatch(
            ToolCall(
                id="t209apply1",
                name="import_lxseq_cues",
                arguments=dict(
                    file_content_base64=_b64(body), sequence_name="TestSeq", action="apply"
                ),
            )
        )
        assert execution.result.is_error is False
        payload = json.loads(execution.result.content)
        assert payload["cue_bundles_planned"] == 0
        assert "계획이 없다" in payload["notice"]
        assert "applied" not in payload

    def test_declined_approval_writes_nothing(self):
        """승인 포트를 안 주면 DenyAllApprovalPort 가 기본값이다 -- fail-closed."""
        registry = _toolset_with_group("BACK")
        execution = registry.dispatch(
            ToolCall(
                id="t209apply2",
                name="import_lxseq_cues",
                arguments=dict(
                    file_content_base64=_b64(self._body("Q010")),
                    sequence_name="TestSeq",
                    action="apply",
                ),
            )
        )
        assert execution.result.is_error is False
        payload = json.loads(execution.result.content)
        assert payload["approval"] == "declined"
        assert "승인이 나지 않아" in payload["notice"]
        assert "applied" not in payload

    def test_a_failed_cue_stops_the_rest_without_touching_them(self):
        """단락 -- 실패한 뒤로는 쏘지 않고 "안 건드렸다"를 기록으로 남긴다."""
        approval = _AcceptAllApproval()
        console = FakeConsole(fixtures=[dict(name="BACK")])
        exec_port = _FailingOnMarkerExec(console, marker="Store Cue 20")
        registry = build_toolset(
            execution_port=exec_port,
            state_port=console,
            property_port=console,
            deploy_pipeline=FakeDeploy(console),
            question_port=Answers(),
            group_approval_port=approval,
        )
        execution = registry.dispatch(
            ToolCall(
                id="t209apply3",
                name="import_lxseq_cues",
                arguments=dict(
                    file_content_base64=_b64(self._body("Q010", "Q020", "Q030")),
                    sequence_name="TestSeq",
                    action="apply",
                ),
            )
        )
        assert execution.result.is_error is False
        payload = json.loads(execution.result.content)
        applied = {e["cue_no"]: e for e in payload["applied"]}
        assert applied["Q010"]["status"] == "ok"
        assert applied["Q020"]["status"] == "failed"
        assert applied["Q030"]["status"] == "skipped_after_failure"
        # Q030 에 대해서는 명령을 아예 안 보냈다 -- 확실히 안 건드렸다
        assert not any("Store Cue 30" in c for c in exec_port.sent)
