"""SPEC-COPILOT-SHEETPIPE-001 (분할 B) — 판별된 바이트를 툴 인자까지 나른다.

A(`SPEC-COPILOT-FILEARG-001`)의 판별기가 "무엇인가"에 답한 **뒤**의 일 전부를
검증한다 — 세션 슬롯 · 실행 금지 · 넷 표시 · 래퍼 툴의 바이트 주입 · 거절 3종.

**판별 자체는 여기서 검증하지 않는다** — 그것은 `test_sheets_registry.py`가
소유한다. 여기가 묻는 것은 *그 판정을 받은 뒤 바이트가 어디로 가는가*다.
"""

from __future__ import annotations

import base64
import hashlib
import json

import pytest

from server.llm.types import ToolCall
from server.orchestrator.tools import (
    TOOL_NAMES,
    ExecutionContext,
    _error_result,
    build_toolset,
)
from server.web.session import UploadedSheet

from .test_runner_self_correction import ScriptedProvider
from .test_web_session import _session

WRAPPER = "import_uploaded_sheet"
TARGET = "import_lxseq_patch"

_HEADER = "FID,Group,FixtureType,Mode,Ch,Universe,Address,AddrRange,Position"


def _patch_csv_bytes() -> bytes:
    """거부·제외 0건인 깨끗한 패치 CSV."""
    rows = [
        _HEADER,
        "101,KEY,ETC S4 LED S3 Lustr X8,Direct 12ch,12,1,1,1.001–012,FOH",
        "102,KEY,ETC S4 LED S3 Lustr X8,Direct 12ch,12,1,13,1.013–024,FOH",
    ]
    return ("\n".join(rows) + "\n").encode("utf-8")


def _mixed_patch_csv_bytes() -> bytes:
    """세 통이 모두 채워지는 CSV — records · rejected · excluded.

    ``AC-SHEETPIPE-006`` ④의 픽스처다. 이 픽스처가 없으면 ④는 판별력이 없다.
    """
    rows = [
        _HEADER,
        "101,KEY,ETC S4 LED S3 Lustr X8,Direct 12ch,12,1,1,1.001–012,FOH",
        "102,KEY,ETC S4 LED S3 Lustr X8,Direct 12ch,0,1,13,1.013–024,FOH",
        "NOPE,KEY,ETC S4 LED S3 Lustr X8,Direct 12ch,12,1,25,1.025–036,FOH",
    ]
    return ("\n".join(rows) + "\n").encode("utf-8")


def _vectorworks_bytes() -> bytes:
    """`vectorworks` 판정을 받는 바이트 — 패치 열 집합이 **아니다**."""
    rows = [
        "Position\tInstrument Type\tChannel\tUnit Number\tPurpose",
        "FOH\tETC S4\t1\t1\tKey",
        "FOH\tETC S4\t2\t2\tKey",
    ]
    return ("\n".join(rows) + "\n").encode("utf-8")


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


class _NeverCalledExecutionPort:
    def execute(self, command: str):
        raise AssertionError(f"시트 경로는 콘솔에 발화하지 않는다: {command}")


class _NeverCalledStatePort:
    def query_state(self, probe: str):
        raise AssertionError(f"시트 경로는 콘솔 상태를 읽지 않는다: {probe}")


class _FakeUploadedSheet:
    """``UploadedSheetPort`` 대역 — 세션이 보관한 시트 1장."""

    def __init__(self, *, file_name=None, kind=None, content_base64=None):
        self.file_name = file_name
        self.kind = kind
        self.content_base64 = content_base64


def _registry(uploaded_sheet=None):
    return build_toolset(
        execution_port=_NeverCalledExecutionPort(),
        state_port=_NeverCalledStatePort(),
        uploaded_sheet=uploaded_sheet,
    )


def _payload(execution) -> dict:
    return json.loads(execution.result.content)


def _uploading_session(tmp_path):
    """업로드만 시키는 세션 — provider는 한 마디도 하지 않는다.

    ``ScriptedProvider``에 대본을 주지 않으므로 모델 호출이 일어나면 그 자리에서
    터진다. ``run_instruction`` 0회를 재는 데 쓰인다.
    """
    provider = ScriptedProvider([])
    session, _console, _audit, sent, _channel = _session(tmp_path, provider)
    return session, provider, sent


# -- AC-SHEETPIPE-002 · 슬롯이 넷을 든다 -----------------------------------------


class TestSlot:
    def test_slot_holds_four(self, tmp_path):
        data = _patch_csv_bytes()
        session, _provider, _sent = _uploading_session(tmp_path)
        session.upload_vectorworks_export("rig.csv", _b64(data))

        sheet = session._uploaded_sheet
        assert isinstance(sheet, UploadedSheet)
        assert sheet.kind == "patch"
        assert sheet.content_base64 == _b64(data)
        # sha256/byte_length는 디코드된 바이트 기준 — base64 문자열이 아니다.
        assert sheet.sha256 == hashlib.sha256(data).hexdigest()
        assert sheet.byte_length == len(data)
        assert sheet.byte_length != len(_b64(data))

    def test_slot_replaced_wholesale_and_said_out_loud(self, tmp_path):
        session, _provider, sent = _uploading_session(tmp_path)
        session.upload_vectorworks_export("first.csv", _b64(_patch_csv_bytes()))
        first = session._uploaded_sheet
        session.upload_vectorworks_export("second.csv", _b64(_mixed_patch_csv_bytes()))
        second = session._uploaded_sheet

        assert second is not first
        assert second.file_name == "second.csv"
        assert "교체" in json.dumps(sent, ensure_ascii=False)

    def test_slot_is_independent_of_the_other_two(self, tmp_path):
        session, _provider, _sent = _uploading_session(tmp_path)
        session.upload_layout_image("sketch.png", "image/png", _b64(b"x" * 32))
        session.upload_vectorworks_export("rig.csv", _b64(_patch_csv_bytes()))

        # 시트 업로드가 이미지 슬롯을 지우지 않는다.
        assert session._layout_image is not None
        assert session._uploaded_sheet is not None
        # 그리고 이미지 업로드도 시트 슬롯을 지우지 않는다.
        session.upload_layout_image("sketch2.png", "image/png", _b64(b"y" * 32))
        assert session._uploaded_sheet is not None

    def test_slot_cleared_when_session_closes(self, tmp_path):
        session, _provider, _sent = _uploading_session(tmp_path)
        session.upload_vectorworks_export("rig.csv", _b64(_patch_csv_bytes()))
        assert session._uploaded_sheet is not None
        session.close()
        assert session._uploaded_sheet is None


# -- AC-SHEETPIPE-003 · 세션 생성 뒤 도착한 업로드를 툴이 본다 --------------------


class TestLateUpload:
    def test_late_upload_visible_to_wrapper(self, tmp_path):
        """시나리오 4 — 세션이 만들어진 뒤 도착한 시트를 래퍼가 본다.

        `AC-SHEETPIPE-002`가 전부 초록이어도 이것은 빨갈 수 있다: 슬롯은
        채워지고 안내도 뜨는데 툴이 보는 것만 어긋나기 때문이다. 읽기 통과
        뷰를 걷어내고 필드를 그대로 넘기면 여기가 빨개진다(뮤테이션 원장).
        """
        data = _patch_csv_bytes()
        session, _provider, _sent = _uploading_session(tmp_path)
        registry = session._registry  # 세션 생성 시점에 이미 만들어진 툴 집합

        # 형제 툴은 기록만 하고 실제로 돌지 않는다 — 이 기준이 재는 것은 콘솔
        # 패치가 되는가가 아니라 래퍼가 슬롯을 보는가다.
        seen: list[ToolCall] = []
        _intercept(registry, TARGET, seen)

        # 세션 생성 뒤 업로드.
        session.upload_vectorworks_export("rig.csv", _b64(data))

        execution = registry.dispatch(_wrapper_call(), ExecutionContext())

        # 슬롯을 보지 못했다면 no_uploaded_sheet로 거절하고 형제 툴을 부르지
        # 않았을 것이다.
        assert _payload(execution).get("reason") != "no_uploaded_sheet"
        assert len(seen) == 1
        assert seen[0].arguments["file_content_base64"] == _b64(data)


# -- AC-SHEETPIPE-004 · 시트 경로는 아무것도 실행하지 않는다 ----------------------


class TestNoExecution:
    def test_no_execution_on_sheet_upload(self, tmp_path, monkeypatch):
        session, provider, _sent = _uploading_session(tmp_path)

        instructions: list[str] = []
        original = type(session).run_instruction

        def _spy(self, text):
            instructions.append(text)
            return original(self, text)

        monkeypatch.setattr(type(session), "run_instruction", _spy)

        session.upload_vectorworks_export("rig.csv", _b64(_patch_csv_bytes()))

        # ① run_instruction 0회.
        assert instructions == []
        # ② 모델도 불리지 않았다.
        assert provider.calls == []
        # ③ 콘솔 포트는 대역이 터뜨린다 — 여기까지 왔으면 0회다.

    def test_no_execution_on_sheet_upload_parses_exactly_once(self, tmp_path, monkeypatch):
        """④ 파싱은 정확히 1회 — 0회여도 실패다(행 수를 낼 수 없으므로).

        정본(`server.lxseq.parser.parse_patch_csv`)이 아니라 소비 지점의
        이름을 감시한다. `from x import f`로 들여온 이름은 소비자 모듈에
        묶이므로 `x.f`를 패치하면 영원히 발화하지 않는다.
        """
        import server.web.session as session_module

        calls: list[str] = []
        real = session_module.parse_patch_csv

        def _spy(text):
            calls.append(text)
            return real(text)

        monkeypatch.setattr(session_module, "parse_patch_csv", _spy)

        session, _provider, _sent = _uploading_session(tmp_path)
        session.upload_vectorworks_export("rig.csv", _b64(_patch_csv_bytes()))

        assert len(calls) == 1


# -- AC-SHEETPIPE-005 · Vectorworks 가지는 오늘 그대로다 -------------------------


class TestVectorworksBranch:
    def test_vectorworks_branch_unchanged_fires_instruction(self, tmp_path, monkeypatch):
        from server.web.session import _VECTORWORKS_UPLOAD_INSTRUCTION

        session, _provider, _sent = _uploading_session(tmp_path)

        instructions: list[str] = []

        def _spy(self, text):
            instructions.append(text)
            return {}

        monkeypatch.setattr(type(session), "run_instruction", _spy)

        data = _vectorworks_bytes()
        session.upload_vectorworks_export("plot.txt", _b64(data))

        # ② 지시문이 그대로 발화한다 — 호출 1회, 인자 그대로.
        assert instructions == [_VECTORWORKS_UPLOAD_INSTRUCTION]
        # ① 기존 슬롯에 담기고 시트 슬롯은 비어 있다.
        assert session._vectorworks_upload.content_base64 == _b64(data)
        assert session._uploaded_sheet is None

    def test_vectorworks_branch_unchanged_rejects_unknown_kind(self, tmp_path, monkeypatch):
        """판별 불가는 슬롯에도, Vectorworks 경로에도 가지 않는다(plan §D.1 1)."""
        session, _provider, sent = _uploading_session(tmp_path)

        instructions: list[str] = []

        def _spy(self, text):
            instructions.append(text)
            return {}

        monkeypatch.setattr(type(session), "run_instruction", _spy)

        session.upload_vectorworks_export("junk.csv", _b64(b"\xff\xfe\x00\x01\x02"))

        assert instructions == []
        assert session._uploaded_sheet is None
        assert session._vectorworks_upload.content_base64 is None
        assert "unknown_sheet_kind" in json.dumps(sent, ensure_ascii=False)


# -- AC-SHEETPIPE-006 · 업로드 직후 넷이 보이고, 행 수에 이름이 붙는다 -------------


class TestUploadNotice:
    def test_upload_notice_shows_four(self, tmp_path):
        data = _patch_csv_bytes()
        session, _provider, sent = _uploading_session(tmp_path)
        session.upload_vectorworks_export("rig.csv", _b64(data))

        surface = json.dumps(sent, ensure_ascii=False)
        assert "patch" in surface
        assert hashlib.sha256(data).hexdigest() in surface
        assert str(len(data)) in surface
        assert "records" in surface

    def test_upload_notice_names_every_bin(self, tmp_path):
        """③④ — 세 통이 전부 이름과 함께 나온다. 맨 숫자만이면 빨갛다."""
        session, _provider, sent = _uploading_session(tmp_path)
        session.upload_vectorworks_export("mixed.csv", _b64(_mixed_patch_csv_bytes()))

        surface = json.dumps(sent, ensure_ascii=False)
        for bin_name in ("records", "rejected", "excluded"):
            assert bin_name in surface, f"통 이름 '{bin_name}'이 표시에 없다"

    def test_upload_notice_fixture_actually_fills_all_three_bins(self):
        """④의 픽스처가 판별력을 갖는지 먼저 잰다 — 세 통이 전부 0이 아니어야 한다."""
        from server.lxseq.parser import parse_patch_csv

        parsed = parse_patch_csv(_mixed_patch_csv_bytes().decode("utf-8"))
        assert len(parsed.records) > 0
        assert len(parsed.rejected) > 0
        assert len(parsed.excluded) > 0

    def test_upload_notice_sha256_matches_the_original_file(self, tmp_path):
        """⑤ — 운영자가 `shasum -a 256 <파일>`과 대조할 수 있는 값이다."""
        data = _patch_csv_bytes()
        session, _provider, sent = _uploading_session(tmp_path)
        session.upload_vectorworks_export("rig.csv", _b64(data))

        assert hashlib.sha256(data).hexdigest() in json.dumps(sent, ensure_ascii=False)


# -- AC-SHEETPIPE-007 · 래퍼가 바이트를 주입한다 ---------------------------------


def _intercept(registry, tool_name, seen):
    """기록하고 원본을 부르지 않는다 — 형제 툴이 실제로 도는 것을 막는다.

    실제 세션의 레지스트리에서는 대상 툴이 콘솔을 읽으므로, 슬롯이 보이는지만
    재려는 기준이 콘솔 대역의 사정으로 빨개진다. 기록만 남기고 무해한 결과를
    돌려주어 그 잡음을 걷어낸다.
    """

    def _stub(call, context):
        seen.append(call)
        return _error_result(call, "intercepted by test")

    registry._handlers[tool_name] = _stub


def _spy_on(registry, tool_name, seen):
    """형제 툴의 소비 지점을 감시한다 — 핸들러 맵의 항목을 갈아 끼운다.

    기록만 하고 원본을 그대로 부른다. 예외를 던지는 감시자는 상위에서 삼켜지면
    "불리지 않았다"와 구분되지 않으므로 쓰지 않는다.
    """
    original = registry._handlers[tool_name]

    def _spy(call, context):
        seen.append(call)
        return original(call, context)

    registry._handlers[tool_name] = _spy


class TestWrapperInjects:
    def test_wrapper_injects_bytes_into_sibling_tool(self):
        data = _patch_csv_bytes()
        seen: list[ToolCall] = []
        registry = _registry(
            _FakeUploadedSheet(file_name="rig.csv", kind="patch", content_base64=_b64(data))
        )
        _spy_on(registry, TARGET, seen)
        registry.dispatch(_wrapper_call(action="preview"), ExecutionContext())

        assert len(seen) == 1, "형제 툴이 내부 ToolCall로 정확히 한 번 불려야 한다"
        forwarded = seen[0]
        assert forwarded.name == TARGET
        assert forwarded.arguments["file_content_base64"] == _b64(data)
        relayed = base64.b64decode(forwarded.arguments["file_content_base64"])
        assert hashlib.sha256(relayed).hexdigest() == hashlib.sha256(data).hexdigest()

    def test_wrapper_injects_only_whitelisted_arguments(self):
        """④ — 화이트리스트 밖의 인자는 형제 툴에 전달되지 않는다."""
        seen: list[ToolCall] = []
        registry = _registry(
            _FakeUploadedSheet(
                file_name="rig.csv", kind="patch", content_base64=_b64(_patch_csv_bytes())
            )
        )
        _spy_on(registry, TARGET, seen)

        poisoned = _wrapper_call(action="preview")
        poisoned.arguments["file_content_base64"] = _b64(b"POISON")
        registry.dispatch(poisoned, ExecutionContext())

        assert len(seen) == 1
        assert seen[0].arguments["file_content_base64"] == _b64(_patch_csv_bytes())
        assert base64.b64decode(seen[0].arguments["file_content_base64"]) != b"POISON"

    def test_wrapper_injects_target_read_from_the_registry_row(self, monkeypatch):
        """② 대상 툴 이름은 레지스트리 행이 지목한 것이며 하드코딩이 아니다.

        레지스트리 행의 대상을 갈아 끼우면 래퍼가 그 새 대상을 부른다.
        하드코딩돼 있으면 이 테스트가 빨개진다.
        """
        import server.orchestrator.tools as tools_module
        from server.sheets.registry import HANDLER_TAG_TOOL, Handler, SheetKindRow

        rerouted = SheetKindRow(
            kind="patch",
            predicate=tools_module.SHEET_REGISTRY[0].predicate,
            handler=Handler(HANDLER_TAG_TOOL, "precheck_vectorworks_diff"),
            passthrough_args=(),
        )
        monkeypatch.setattr(tools_module, "SHEET_REGISTRY", (rerouted,))

        seen: list[ToolCall] = []
        registry = _registry(
            _FakeUploadedSheet(
                file_name="rig.csv", kind="patch", content_base64=_b64(_patch_csv_bytes())
            )
        )
        _spy_on(registry, "precheck_vectorworks_diff", seen)

        registry.dispatch(_wrapper_call(), ExecutionContext())

        assert len(seen) == 1
        assert seen[0].name == "precheck_vectorworks_diff"


# -- AC-SHEETPIPE-009 · 래퍼 스키마에 바이트 인자도 경로 인자도 없다 ---------------


class TestWrapperSchema:
    def _definition(self):
        registry = _registry()
        return next(d for d in registry.definitions() if d.name == WRAPPER)

    def test_wrapper_schema_has_no_byte_argument(self):
        schema = self._definition().parameters
        assert "file_content_base64" not in schema["properties"]

    def test_wrapper_schema_has_no_path_argument(self):
        schema = self._definition().parameters
        for name, spec in schema["properties"].items():
            lowered = name.lower()
            assert "path" not in lowered
            assert "filename" not in lowered
            assert lowered != "file"
            description = str(spec.get("description", ""))
            assert "경로" not in description
            assert "path" not in description.lower()

    def test_wrapper_schema_is_closed(self):
        schema = self._definition().parameters
        assert schema["additionalProperties"] is False

    def test_wrapper_schema_description_says_bytes_are_already_in_session(self):
        description = self._definition().description
        assert "세션" in description
        assert "base64" in description


# -- AC-SHEETPIPE-010 · 거절 3종이 이름으로 나온다 --------------------------------


class TestWrapperRefusal:
    def test_wrapper_refusal_no_uploaded_sheet(self):
        registry = _registry(_FakeUploadedSheet())
        execution = registry.dispatch(_wrapper_call(), ExecutionContext())
        payload = _payload(execution)

        assert execution.result.is_error
        assert payload["reason"] == "no_uploaded_sheet"
        # 다음에 무엇을 할지 알 수 있는 문장이 함께 나온다 …
        assert "올" in payload["error"]
        # … 그리고 바이트를 붙여넣으라고 하지 않는다.
        assert "붙여넣" not in payload["error"]

    def test_wrapper_refusal_no_uploaded_sheet_when_port_absent(self):
        """포트 자체가 배선되지 않아도 조용한 무동작이 아니라 이름 붙은 거절이다."""
        registry = _registry()
        execution = registry.dispatch(_wrapper_call(), ExecutionContext())
        assert execution.result.is_error
        assert _payload(execution)["reason"] == "no_uploaded_sheet"

    def test_wrapper_refusal_kind_action_mismatch(self):
        registry = _registry(
            _FakeUploadedSheet(
                file_name="rig.csv", kind="patch", content_base64=_b64(_patch_csv_bytes())
            )
        )
        execution = registry.dispatch(_wrapper_call(action="deploy"), ExecutionContext())
        payload = _payload(execution)

        assert execution.result.is_error
        assert payload["reason"] == "kind_action_mismatch"
        # 그 종류가 지원하는 action 목록이 함께 나온다.
        assert "preview" in payload["error"]
        assert "apply" in payload["error"]

    def test_wrapper_refusal_no_target_tool(self, monkeypatch):
        import server.orchestrator.tools as tools_module
        from server.sheets.registry import HANDLER_TAG_TOOL, Handler, SheetKindRow

        broken = SheetKindRow(
            kind="patch",
            predicate=tools_module.SHEET_REGISTRY[0].predicate,
            handler=Handler(HANDLER_TAG_TOOL, "no_such_tool"),
            passthrough_args=(),
        )
        monkeypatch.setattr(tools_module, "SHEET_REGISTRY", (broken,))

        registry = _registry(
            _FakeUploadedSheet(
                file_name="rig.csv", kind="patch", content_base64=_b64(_patch_csv_bytes())
            )
        )
        execution = registry.dispatch(_wrapper_call(), ExecutionContext())
        payload = _payload(execution)

        assert execution.result.is_error
        assert payload["reason"] == "no_target_tool"
        # 어느 종류의 어느 대상이 어느 등록부에 없는지 말한다.
        assert "patch" in payload["error"]
        assert "no_such_tool" in payload["error"]

    def test_wrapper_refusal_reasons_are_a_closed_set(self):
        from server.orchestrator.tools import SHEET_WRAPPER_REFUSALS

        assert SHEET_WRAPPER_REFUSALS == (
            "no_uploaded_sheet",
            "kind_action_mismatch",
            "no_target_tool",
        )

    def test_wrapper_refusal_never_calls_target_with_empty_bytes(self):
        """② 조용한 무동작도, 빈 바이트로 대상 툴을 부르는 일도 없다."""
        registry = _registry(_FakeUploadedSheet())
        called: list[ToolCall] = []
        _spy_on(registry, TARGET, called)

        execution = registry.dispatch(_wrapper_call(), ExecutionContext())

        assert called == []
        assert execution.result.is_error


# -- 등재 (AC-SHEETPIPE-008 보조) -------------------------------------------------


class TestRegistration:
    def test_wrapper_is_in_tool_names(self):
        assert WRAPPER in TOOL_NAMES

    def test_wrapper_is_dispatchable(self):
        """등재는 dict 조회가 아니라 디스패치로 확인한다."""
        registry = _registry()
        execution = registry.dispatch(_wrapper_call(), ExecutionContext())
        assert "unknown tool" not in execution.result.content

    def test_wrapper_has_a_korean_task_name(self):
        from server.orchestrator.runner import _TOOL_TASKS

        assert WRAPPER in _TOOL_TASKS

    def test_advertised_definitions_match_tool_names(self):
        registry = _registry()
        advertised = set(definition.name for definition in registry.definitions())
        assert advertised == set(TOOL_NAMES)


# -- 레지스트리 소비 계약 (B가 A를 읽는 방식) --------------------------------------


class TestRegistryConsumption:
    def test_sheet_registry_is_a_reference_not_a_copy(self):
        """B는 A의 레지스트리를 참조한다 — 사본을 만들지 않는다."""
        import server.orchestrator.tools as tools_module
        import server.sheets.registry as registry_module

        assert tools_module.SHEET_REGISTRY is registry_module.REGISTRY

    def test_only_tool_tagged_rows_are_reachable_from_the_wrapper(self):
        """session_method 종은 업로드 이음매에서 처분되므로 래퍼에 닿지 않는다.

        닿았다면 결함이다 — 세션 메서드는 ToolCall로 부를 대상이 아니다.
        """
        registry = _registry(
            _FakeUploadedSheet(
                file_name="plot.txt", kind="vectorworks", content_base64=_b64(_vectorworks_bytes())
            )
        )
        execution = registry.dispatch(_wrapper_call(), ExecutionContext())
        assert execution.result.is_error
        assert _payload(execution)["reason"] == "no_target_tool"


@pytest.mark.parametrize("action", ["preview", "apply"])
def test_patch_kind_supports_both_actions(action):
    from server.orchestrator.tools import SHEET_KIND_ACTIONS

    assert action in SHEET_KIND_ACTIONS["patch"]


def _wrapper_call(action=None):
    """래퍼 호출 하나. 인라인 dict 리터럴을 피해 조립한다."""
    args: dict[str, object] = dict()
    if action is not None:
        args["action"] = action
    return ToolCall(id="c1", name=WRAPPER, arguments=args)
