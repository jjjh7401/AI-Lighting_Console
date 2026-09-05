"""SPEC-COPILOT-LXSEQ-004 M3 (t209) -- import_lxseq_cues registration.

Scope: registration only. cue_mapper.py does not exist yet (sync lane, a
separate branch) so anything past header validation is expected to refuse
gracefully rather than reach the missing mapper. Console contact: 0.
"""

from __future__ import annotations

import base64
import io
import json
from pathlib import Path

import openpyxl
import pytest

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


# =========================================================================
# SPEC-COPILOT-MUSICSYNC-001 M1 — 시트 시간열 수용
#
# 이 절이 못 박는 것: 시트가 **이미 들고 있는** 시각을 잃지 않고 들여오되,
# 못 믿는 시각은 **발사되지 않는다.** 미확정을 0 으로 접으면 그 큐는 첫 박에
# 발사되고, 그 결함은 리허설이 아니라 본 공연에서 드러난다.
# =========================================================================

DERIVED_LITERAL = "리허설 LTC 대조 전까지 실행 확정본이 아님"


def _timed_cue_sheet(rows, *, head=None):
    """CUE 탭 + (선택) HEAD 탭. rows 는 (q, section, tc_in, tc_out, mood, fade).

    실측 정본과 같은 자리에 둔다 — 헤더 4행, 데이터 5행부터, 열 순서는
    `Q#`·`Section`·`TC In`·`TC Out`·`Dur`·`Mood`…(research.md §1.3).
    """
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
    for q, section, tc_in, tc_out, mood, fade in rows:
        ws.append([q, section, tc_in, tc_out, "", mood, "", "", "", "", "", "", fade, ""])
    if head is not None:
        head_ws = wb.create_sheet("HEAD")
        head_ws.append(("LX-SEQ v2.0 — 조명연출 시퀀스 큐시트",))
        for key, value in head:
            head_ws.append((key, value))
    buf = io.BytesIO()
    wb.save(buf)
    return base64.b64encode(buf.getvalue()).decode("ascii")


class _CountingConsole(FakeConsole):
    """`query_state` 호출 수를 센다 — M1 이 조회를 **한 건도 더 내지 않음**을
    잰다(AC-MUSICSYNC-002). 세지 않으면 「증가 0」은 주장일 뿐이다."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.query_calls: list[str] = []

    def query_state(self, path: str, *args, **kwargs) -> dict:
        self.query_calls.append(path)
        return super().query_state(path, *args, **kwargs)


def _timing_registry(*, approval=None, exec_port=None, console=None):
    console = console if console is not None else _CountingConsole(fixtures=[dict(name="BACK")])
    exec_port = exec_port if exec_port is not None else FakeExec(console)
    registry = build_toolset(
        execution_port=exec_port,
        state_port=console,
        property_port=console,
        deploy_pipeline=FakeDeploy(console),
        question_port=Answers(),
        group_approval_port=approval,
    )
    return registry, console, exec_port


def _cue_ex_body(*cue_nos, group="BACK"):
    header = ",".join(CANONICAL_CUE_COLUMNS)
    rows = [",".join([q, group, "55"] + [""] * 12 + ["", ""]) for q in cue_nos]
    return (header + "\n" + "\n".join(rows) + "\n").encode("utf-8")


def _run(registry, *, body, cue_sheet=None, action="preview", call_id="musicsync"):
    arguments = dict(file_content_base64=_b64(body), sequence_name="TestSeq", action=action)
    if cue_sheet is not None:
        arguments["cue_sheet_xlsx_base64"] = cue_sheet
    execution = registry.dispatch(
        ToolCall(id=call_id, name="import_lxseq_cues", arguments=arguments)
    )
    return execution


def _timing_entry(payload, cue_no):
    return next(c for c in payload["cue_timing"]["cues"] if c["cue_no"] == cue_no)


class TestSheetTimeLandsOnTheCue:
    """AC-MUSICSYNC-001 — 시트의 시각이 큐에 실린다."""

    def test_preview_carries_the_two_timing_lines_side_by_side(self):
        registry, _console, _exec_port = _timing_registry()
        cue_sheet = _timed_cue_sheet([("Q010", "INTRO", "00:00.0", "00:08.0", "화사", 1.0)])
        execution = _run(registry, body=_cue_ex_body("Q010"), cue_sheet=cue_sheet)
        assert execution.result.is_error is False
        payload = json.loads(execution.result.content)
        commands = _timing_entry(payload, "Q010")["commands"]
        assert commands == [
            "Set Cue 10 Sequence 2 Property 'TrigType' 'Time'",
            "Set Cue 10 Sequence 2 Property 'TrigTime' 0",
        ]

    def test_the_trigtime_value_follows_format_seconds_semantics(self):
        from server.looks.songcue import _format_seconds

        registry, _console, _exec_port = _timing_registry()
        cue_sheet = _timed_cue_sheet([("Q050", "CHORUS1", "00:56.5", "01:12.0", "개방", 1.0)])
        execution = _run(registry, body=_cue_ex_body("Q050"), cue_sheet=cue_sheet)
        payload = json.loads(execution.result.content)
        entry = _timing_entry(payload, "Q050")
        assert entry["tc_in"]["ms"] == 56500
        assert entry["commands"][1].endswith(" " + _format_seconds(56500))


class TestOneApprovalBundleAndNoExtraQueries:
    """AC-MUSICSYNC-002 — 두 줄은 `Store Cue` 와 **같은 승인 번들** 안이고,
    preview 는 쓰기 0, 조회 증가 0 이다."""

    def test_the_three_lines_ride_one_approval_bundle(self):
        approval = _AcceptAllApproval()
        registry, _console, exec_port = _timing_registry(approval=approval)
        cue_sheet = _timed_cue_sheet([("Q010", "INTRO", "00:00.0", "00:08.0", "화사", 1.0)])
        execution = _run(registry, body=_cue_ex_body("Q010"), cue_sheet=cue_sheet, action="apply")
        assert execution.result.is_error is False
        assert len(approval.requests) == 1
        bundle = [item.command for item in approval.requests[0].items]
        assert any(c.startswith("Store Cue 10 ") for c in bundle)
        assert "Set Cue 10 Sequence 2 Property 'TrigType' 'Time'" in bundle
        assert "Set Cue 10 Sequence 2 Property 'TrigTime' 0" in bundle
        assert any("'TrigTime'" in c for c in exec_port.sent)

    def test_preview_writes_nothing_to_the_console(self):
        registry, _console, exec_port = _timing_registry()
        cue_sheet = _timed_cue_sheet([("Q010", "INTRO", "00:00.0", "00:08.0", "화사", 1.0)])
        _run(registry, body=_cue_ex_body("Q010"), cue_sheet=cue_sheet)
        assert exec_port.sent == []

    def test_the_query_state_count_does_not_grow_when_times_are_read(self):
        body = _cue_ex_body("Q010")
        cue_sheet = _timed_cue_sheet([("Q010", "INTRO", "00:00.0", "00:08.0", "화사", 1.0)])

        registry_a, console_a, _ = _timing_registry()
        _run(registry_a, body=body, call_id="musicsync-base")
        registry_b, console_b, _ = _timing_registry()
        _run(registry_b, body=body, cue_sheet=cue_sheet, call_id="musicsync-timed")

        assert len(console_b.query_calls) == len(console_a.query_calls)


class TestUndeterminedNeverFires:
    """AC-MUSICSYNC-003 [부정 대조군] — 못 믿는 시각은 한 줄도 안 낸다."""

    def test_needs_check_blank_and_malformed_are_three_distinct_reasons(self):
        registry, _console, _exec_port = _timing_registry()
        cue_sheet = _timed_cue_sheet(
            [
                ("Q010", "INTRO", "확인필요", "", "화사", 1.0),
                ("Q020", "VERSE1", "", "", "경쾌", 1.0),
                ("Q030", "VERSE1", "abc", "", "확장", 1.0),
                ("Q040", "PRE1", "00:40.0", "00:56.0", "축적", 1.0),
            ]
        )
        execution = _run(
            registry, body=_cue_ex_body("Q010", "Q020", "Q030", "Q040"), cue_sheet=cue_sheet
        )
        payload = json.loads(execution.result.content)
        reasons = {e["cue_no"]: e["reason"] for e in payload["cue_timing"]["undetermined"]}
        assert set(reasons) == {"Q010", "Q020", "Q030"}
        assert len(set(reasons.values())) == 3
        for cue_no in ("Q010", "Q020", "Q030"):
            assert _timing_entry(payload, cue_no)["commands"] == []
        # 다른 큐들의 번들은 그대로 만들어진다
        assert _timing_entry(payload, "Q040")["commands"] != []
        assert payload["cue_bundles_planned"] == 4


class TestNoInventedZero:
    """AC-MUSICSYNC-004 [부정 대조군] — 어디에도 0 이 지어지지 않는다."""

    def test_an_undetermined_cue_carries_no_number_and_emits_no_trigtime(self):
        registry, _console, _exec_port = _timing_registry()
        cue_sheet = _timed_cue_sheet([("Q010", "INTRO", "확인필요", "", "화사", 1.0)])
        execution = _run(registry, body=_cue_ex_body("Q010"), cue_sheet=cue_sheet)
        payload = json.loads(execution.result.content)
        entry = _timing_entry(payload, "Q010")
        assert entry["tc_in"]["ms"] is None
        assert "TrigTime 0" not in json.dumps(payload, ensure_ascii=False)

    def test_a_genuine_zero_is_the_only_cue_that_may_say_trigtime_zero(self):
        registry, _console, _exec_port = _timing_registry()
        cue_sheet = _timed_cue_sheet(
            [
                ("Q010", "INTRO", "00:00.0", "00:08.0", "화사", 1.0),
                ("Q020", "VERSE1", "확인필요", "", "경쾌", 1.0),
            ]
        )
        execution = _run(registry, body=_cue_ex_body("Q010", "Q020"), cue_sheet=cue_sheet)
        payload = json.loads(execution.result.content)
        assert _timing_entry(payload, "Q010")["commands"][1].endswith("'TrigTime' 0")
        assert _timing_entry(payload, "Q020")["commands"] == []


class TestMonotonicityViolationsAreASeparateList:
    """AC-MUSICSYNC-005 [부정 대조군] — 목록으로 나오고 재정렬되지 않는다."""

    def test_a_backwards_tc_in_is_listed_and_the_order_is_untouched(self):
        registry, _console, _exec_port = _timing_registry()
        cue_sheet = _timed_cue_sheet(
            [
                ("Q010", "INTRO", "00:10.0", "00:20.0", "화사", 1.0),
                ("Q020", "VERSE1", "00:05.0", "00:30.0", "경쾌", 1.0),
            ]
        )
        execution = _run(registry, body=_cue_ex_body("Q010", "Q020"), cue_sheet=cue_sheet)
        assert execution.result.is_error is False
        payload = json.loads(execution.result.content)
        violations = payload["cue_timing"]["monotonicity_violations"]
        backwards = [v for v in violations if v["kind"] == "tc_in_not_increasing"]
        assert len(backwards) == 1
        assert {backwards[0]["cue_no"], backwards[0]["other_cue_no"]} == {"Q010", "Q020"}
        # 시트 순서 그대로 -- 조용한 재정렬 금지
        assert [c["cue_no"] for c in payload["cue_timing"]["cues"]] == ["Q010", "Q020"]
        assert [b["cue_no"] for b in payload["planned_cues"]] == ["Q010", "Q020"]

    def test_a_tc_out_past_the_next_tc_in_is_a_separate_item(self):
        registry, _console, _exec_port = _timing_registry()
        cue_sheet = _timed_cue_sheet(
            [
                ("Q010", "INTRO", "00:00.0", "00:12.0", "화사", 1.0),
                ("Q020", "VERSE1", "00:08.0", "00:24.0", "경쾌", 1.0),
            ]
        )
        execution = _run(registry, body=_cue_ex_body("Q010", "Q020"), cue_sheet=cue_sheet)
        payload = json.loads(execution.result.content)
        kinds = [v["kind"] for v in payload["cue_timing"]["monotonicity_violations"]]
        assert "tc_out_overlaps_next_tc_in" in kinds

    def test_the_violation_is_not_mixed_into_the_cue_hold_vocabulary(self):
        registry, _console, _exec_port = _timing_registry()
        cue_sheet = _timed_cue_sheet(
            [
                ("Q010", "INTRO", "00:10.0", "00:20.0", "화사", 1.0),
                ("Q020", "VERSE1", "00:05.0", "00:30.0", "경쾌", 1.0),
            ]
        )
        execution = _run(registry, body=_cue_ex_body("Q010", "Q020"), cue_sheet=cue_sheet)
        payload = json.loads(execution.result.content)
        assert payload["cues_held"] == []
        assert payload["held"] == []
        held_text = json.dumps([payload["cues_held"], payload["held"]], ensure_ascii=False)
        assert "tc_in_not_increasing" not in held_text


class TestPreRollIsCarriedButNotProjected:
    """AC-MUSICSYNC-006 [부정 대조군] — 음수는 발화되고 타임라인에서만 빠진다."""

    def test_a_negative_tc_in_is_emitted_and_excluded_from_the_timeline(self):
        registry, _console, _exec_port = _timing_registry()
        cue_sheet = _timed_cue_sheet(
            [
                ("Q005", "PRE-ROLL", "-00:30.0", "00:00.0", "암전", 1.0),
                ("Q010", "INTRO", "00:00.0", "00:08.0", "화사", 1.0),
            ]
        )
        execution = _run(registry, body=_cue_ex_body("Q005", "Q010"), cue_sheet=cue_sheet)
        assert execution.result.is_error is False
        payload = json.loads(execution.result.content)
        assert _timing_entry(payload, "Q005")["commands"][1].endswith("'TrigTime' -30")
        timeline = payload["cue_timing"]["timeline"]
        assert timeline["excluded_preroll"] == ["Q005"]
        assert [s["label"] for s in timeline["sections"]] == ["Q010 INTRO"]

    def test_a_console_rejection_demotes_only_that_cue_and_writes_no_rollback(self):
        """🔴 B9 — 음수 `TrigTime` 인자의 콘솔 수용 여부는 **미측정**이다.
        여기서 재는 것은 콘솔의 답이 아니라 **거절을 받았을 때의 우리 거동**이다.
        """
        approval = _AcceptAllApproval()
        console = _CountingConsole(fixtures=[dict(name="BACK")])
        exec_port = _FailingOnMarkerExec(console, marker="'TrigTime' -30")
        registry, _console, _exec = _timing_registry(
            approval=approval, exec_port=exec_port, console=console
        )
        cue_sheet = _timed_cue_sheet(
            [
                ("Q005", "PRE-ROLL", "-00:30.0", "00:00.0", "암전", 1.0),
                ("Q010", "INTRO", "00:00.0", "00:08.0", "화사", 1.0),
            ]
        )
        execution = _run(
            registry,
            body=_cue_ex_body("Q005", "Q010"),
            cue_sheet=cue_sheet,
            action="apply",
        )
        assert execution.result.is_error is False
        payload = json.loads(execution.result.content)
        report = payload["timing_apply"]
        attempted = set(report["attempted"])
        applied = set(report["applied"])
        rejected = {entry["cue_no"] for entry in report["rejected"]}
        # 계수 판정 -- 합집합이 시도 전수, 교집합은 공집합
        assert applied | rejected == attempted
        assert applied & rejected == set()
        assert rejected == {"Q005"}
        # 거절된 큐만 미확정으로 강등된다
        demoted = {
            e["cue_no"]: e["reason"]
            for e in payload["cue_timing"]["undetermined"]
            if e["reason"] == "console_rejected"
        }
        assert set(demoted) == {"Q005"}
        # 되돌림 쓰기 0건 -- 콘솔로 나간 명령에 Delete/Remove 계열이 없다
        assert report["rollback_commands"] == []
        assert not any(c.startswith(("Delete", "Remove", "Off ")) for c in exec_port.sent)
        # 나머지 큐는 계속 나갔다 -- 단락되지 않는다
        assert any("Store Cue 10 " in c for c in exec_port.sent)


class TestDerivedWarningPropagates:
    """AC-MUSICSYNC-007 — `TC_METHOD: DERIVED` 경고가 세 곳에 리터럴로 실린다."""

    def _payload(self):
        registry, _console, _exec_port = _timing_registry()
        cue_sheet = _timed_cue_sheet(
            [("Q010", "INTRO", "00:00.0", "00:08.0", "화사", 1.0)],
            head=[
                ("BPM", "120 (고정)"),
                ("TC_SOURCE", "LTC"),
                ("TC_METHOD", "DERIVED — 마디연산(1마디=2.000s) 도출. 음원 청취 미검증."),
            ],
        )
        execution = _run(registry, body=_cue_ex_body("Q010"), cue_sheet=cue_sheet)
        assert execution.result.is_error is False
        return json.loads(execution.result.content)

    def test_the_result_payload_carries_the_literal(self):
        assert DERIVED_LITERAL in self._payload()["cue_timing"]["warning"]

    def test_the_timeline_projection_carries_the_literal(self):
        assert DERIVED_LITERAL in self._payload()["cue_timing"]["timeline"]["warning"]

    def test_the_cue_label_family_carries_the_literal(self):
        note = self._payload()["cue_manual_notes"]["Q010"]
        assert DERIVED_LITERAL in note["cue_label_warning"]

    def test_the_head_sheet_values_are_read(self):
        head = self._payload()["cue_timing"]["head"]
        assert head["bpm_raw"] == "120 (고정)"
        assert head["tc_source"] == "LTC"
        assert head["tc_method"].startswith("DERIVED")

    def test_a_non_derived_method_gets_no_warning(self):
        registry, _console, _exec_port = _timing_registry()
        cue_sheet = _timed_cue_sheet(
            [("Q010", "INTRO", "00:00.0", "00:08.0", "화사", 1.0)],
            head=[("TC_METHOD", "VERIFIED — 음원 청취 대조 완료.")],
        )
        execution = _run(registry, body=_cue_ex_body("Q010"), cue_sheet=cue_sheet)
        payload = json.loads(execution.result.content)
        assert payload["cue_timing"]["warning"] is None


class TestCsvOnlySaysItsHonestLimit:
    """AC-MUSICSYNC-008 — CSV 만 준 호출이 정직한 한계를 말한다."""

    def test_no_timing_lines_and_both_literals_in_the_reason(self):
        registry, _console, _exec_port = _timing_registry()
        execution = _run(registry, body=_cue_ex_body("Q010"))
        assert execution.result.is_error is False
        payload = json.loads(execution.result.content)
        assert payload["cue_timing"]["cues"] == []
        assert "'TrigTime'" not in json.dumps(payload, ensure_ascii=False)
        reason = payload["cue_timing"]["reason"]
        assert "시간 정보 없음" in reason
        assert "manual_go" in reason

    def test_the_seventeen_column_exact_set_is_untouched(self):
        from server.sheets.registry import CUE_ROW

        assert CANONICAL_CUE_COLUMNS == (
            "Q#",
            "Group",
            "Dim",
            "COL",
            "POS",
            "BM",
            "FX",
            "FX-Rate",
            "FX-Phase",
            "FX-Width",
            "I-Fade",
            "I-Delay",
            "P-Fade",
            "C-Fade",
            "B-Fade",
            "Snap",
            "Note",
        )
        assert CUE_ROW.predicate.required_columns == CANONICAL_CUE_COLUMNS

    def test_the_two_preserve_files_have_no_diff_against_the_base(self):
        """AC 문면의 「diff 가 비어 있다」를 기계로 잰다 -- git 이 없으면 건너뛴다
        (재지 못한 것을 통과로 적지 않는다)."""
        import subprocess

        root = Path(__file__).resolve().parents[2]
        paths = ["server/lxseq/cue_parser.py", "server/sheets/registry.py"]
        try:
            base = subprocess.run(
                ["git", "-C", str(root), "merge-base", "HEAD", "origin/main"],
                capture_output=True,
                text=True,
                check=False,
            )
            if base.returncode != 0:
                pytest.skip(f"origin/main 을 못 찾았다: {base.stderr.strip()}")
            diff = subprocess.run(
                ["git", "-C", str(root), "diff", "--name-only", base.stdout.strip(), "--", *paths],
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError:  # pragma: no cover - git 없는 환경
            pytest.skip("git 실행 파일이 없다")
        if diff.returncode != 0:
            pytest.skip(f"git diff 실패: {diff.stderr.strip()}")
        assert diff.stdout.strip() == ""


class TestCanonicalSheetTimesAreRead:
    """정본 곡파일 실물로 잰다 -- 합성 시트만으로는 실제 열 자리가 안 증명된다."""

    CANONICAL_XLSX = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "Lighting_Designer"
        / "03_곡파일_Sugar"
        / "LXSEQ_SAMPLE_01_Sugar_r3.xlsx"
    )

    def test_q010_reads_zero_and_eight_seconds_from_the_canonical_file(self):
        if not self.CANONICAL_XLSX.exists():  # pragma: no cover - 정본 부재 환경
            pytest.skip(f"정본 곡파일이 없다: {self.CANONICAL_XLSX}")
        registry, _console, _exec_port = _timing_registry()
        cue_sheet = base64.b64encode(self.CANONICAL_XLSX.read_bytes()).decode("ascii")
        execution = _run(registry, body=_cue_ex_body("Q010"), cue_sheet=cue_sheet)
        assert execution.result.is_error is False
        payload = json.loads(execution.result.content)
        entry = _timing_entry(payload, "Q010")
        assert entry["tc_in"]["ms"] == 0
        assert entry["tc_out"]["ms"] == 8000
        assert entry["commands"][1] == "Set Cue 10 Sequence 2 Property 'TrigTime' 0"
        head = payload["cue_timing"]["head"]
        assert head["bpm_raw"] == "120 (고정)"
        assert head["tc_source"] == "LTC"
