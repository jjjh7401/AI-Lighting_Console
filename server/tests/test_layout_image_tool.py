"""analyse_layout_image 툴 배선 테스트 (SPEC-COPILOT-IMGLAYOUT-001 M3 —
REQ-IMGLAYOUT-007/008/009). mock provider만 사용 — 실제 API 호출 없음.

``server/tests/test_vwx_tool.py``의 확립된 패턴을 따른다 — 등록은 dict 조회가
아니라 **디스패치**로 확인하고, 콘솔 실행 포트/상태 포트는 절대 호출되지
않음을 대역으로 확인한다(이 툴은 0 exec verbs, spec.md 원칙 3).
"""

from __future__ import annotations

import json

from server.llm.types import ModelTurn, ToolCall, Usage
from server.orchestrator.tools import TOOL_NAMES, build_toolset

TOOL = "analyse_layout_image"


class _NeverCalledExecutionPort:
    """이 툴은 콘솔에 발화하지 않는다 — 호출되면 즉시 실패한다."""

    def execute(self, command: str):
        raise AssertionError(f"analyse_layout_image must never call execution_port: {command}")


class _NeverCalledStatePort:
    """이 툴은 콘솔 상태를 읽지 않는다 — 호출되면 즉시 실패한다."""

    def query_state(self, path: str):
        raise AssertionError(f"analyse_layout_image must never call state_port: {path}")


class _FakeLayoutImageUpload:
    """``LayoutImageUploadPort`` 대역 — 세션이 보관한 이미지 1장."""

    def __init__(self, *, file_name=None, mime_type=None, content_base64=None):
        self.file_name = file_name
        self.mime_type = mime_type
        self.content_base64 = content_base64


class _MockVisionProvider:
    """``LLMProvider`` 대역 — ``.complete()`` 호출을 기록하고 고정 응답을 낸다."""

    def __init__(self, response_text: str):
        self._response_text = response_text
        self.calls: list[dict[str, object]] = []

    @property
    def name(self) -> str:
        return "mock"

    @property
    def model_id(self) -> str:
        return "mock-vision-1"

    @property
    def supports_prompt_caching(self) -> bool:
        return False

    def complete(self, *, system_prefix, conversation, tools=()):
        self.calls.append(
            {"system_prefix": system_prefix, "conversation": conversation, "tools": tools}
        )
        return ModelTurn(
            text=self._response_text,
            tool_calls=(),
            stop_reason="end",
            usage=Usage(),
            provider="mock",
        )


_VALID_RESPONSE = json.dumps(
    {
        "pattern": "rings",
        "layers": [{"count": 6, "note": "inner"}, {"count": 12, "note": "outer"}],
        "symmetry": "radial",
        "confidence": "high",
        "annotations": [
            {"text": "간격 2m", "interpreted": {"spacing": 2.0}, "applies_to": "outer ring"},
            {
                "text": "MMX x6",
                "interpreted": {"type_name": "MMX", "count": 6},
                "applies_to": "inner ring",
            },
        ],
        "unresolved": ["안쪽 링 반지름"],
    },
    ensure_ascii=False,
)


def _registry(*, vision_provider=None, layout_image_upload=None):
    return build_toolset(
        execution_port=_NeverCalledExecutionPort(),
        state_port=_NeverCalledStatePort(),
        vision_provider=vision_provider,
        layout_image_upload=layout_image_upload,
    )


def _dispatch(registry, **arguments):
    return registry.dispatch(ToolCall(id="i1", name=TOOL, arguments=arguments))


def _attached_image(**overrides):
    fields = {
        "file_name": "stage-sketch.png",
        "mime_type": "image/png",
        "content_base64": "ZmFrZS1ieXRlcw==",
    }
    fields.update(overrides)
    return _FakeLayoutImageUpload(**fields)


class TestRegistrationByDispatch:
    """툴 등록 4지점 — 디스패치로 확인(dict 조회만으로 확인 안 함)."""

    def test_the_name_is_in_the_closed_tool_name_tuple(self):
        assert TOOL in TOOL_NAMES

    def test_the_definition_is_advertised(self):
        names = {definition.name for definition in _registry().definitions()}
        assert TOOL in names

    def test_dispatch_reaches_a_handler(self):
        provider = _MockVisionProvider(_VALID_RESPONSE)
        execution = _dispatch(
            _registry(vision_provider=provider, layout_image_upload=_attached_image()),
            description="원형 배치 스케치",
        )
        assert execution.result.name == TOOL
        assert execution.result.is_error is False

    def test_every_advertised_name_is_dispatchable(self):
        registry = _registry()
        advertised = {definition.name for definition in registry.definitions()}
        assert advertised == set(TOOL_NAMES)

    def test_definition_requires_description_only(self):
        definition = next(d for d in _registry().definitions() if d.name == TOOL)
        assert definition.parameters["required"] == ["description"]
        assert "file_content_base64" not in definition.parameters["properties"]
        assert "content_base64" not in definition.parameters["properties"]


class TestNormalParse:
    """정상 파싱 — 계약 §3 스키마 그대로 반환하고, 이미지가 provider로 조립된다."""

    def test_returns_the_contract_shape_verbatim(self):
        provider = _MockVisionProvider(_VALID_RESPONSE)
        execution = _dispatch(
            _registry(vision_provider=provider, layout_image_upload=_attached_image()),
            description="원형 배치 스케치, 안쪽 6대 바깥 12대",
        )
        assert execution.result.is_error is False
        payload = json.loads(execution.result.content)
        assert payload["pattern"] == "rings"
        assert payload["symmetry"] == "radial"
        assert payload["confidence"] == "high"
        assert payload["layers"] == [
            {"count": 6, "note": "inner"},
            {"count": 12, "note": "outer"},
        ]
        assert payload["annotations"][0]["text"] == "간격 2m"
        assert payload["annotations"][0]["interpreted"] == {"spacing": 2.0}
        assert payload["unresolved"] == ["안쪽 링 반지름"]

    def test_the_session_image_is_attached_to_the_model_call_not_the_arguments(self):
        provider = _MockVisionProvider(_VALID_RESPONSE)
        upload = _attached_image(mime_type="image/webp", content_base64="d2VicC1ieXRlcw==")
        _dispatch(
            _registry(vision_provider=provider, layout_image_upload=upload),
            description="원형 배치 스케치",
        )
        assert len(provider.calls) == 1
        conversation = provider.calls[0]["conversation"]
        assert len(conversation) == 1
        message = conversation[0]
        assert "원형 배치 스케치" in message.text
        assert len(message.images) == 1
        assert message.images[0].mime_type == "image/webp"
        assert message.images[0].content_base64 == "d2VicC1ieXRlcw=="
        # 계약 §3: 픽셀 비율 추정 금지를 프롬프트가 명시한다.
        assert "픽셀" in message.text or "추정" in message.text
        # 도구 자체는 provider에 다른 툴을 열어주지 않는다 — 비전 1회 호출.
        assert provider.calls[0]["tools"] == ()


class TestNoImageAttached:
    """이미지 부재 — 계약 §3 명시 오류 문구, provider는 아예 호출되지 않는다."""

    def test_no_upload_object_at_all(self):
        provider = _MockVisionProvider(_VALID_RESPONSE)
        execution = _dispatch(
            _registry(vision_provider=provider, layout_image_upload=None),
            description="원형 배치 스케치",
        )
        assert execution.result.is_error is True
        assert json.loads(execution.result.content)["error"] == "첨부된 이미지가 없습니다"
        assert provider.calls == []

    def test_upload_object_present_but_empty(self):
        provider = _MockVisionProvider(_VALID_RESPONSE)
        execution = _dispatch(
            _registry(vision_provider=provider, layout_image_upload=_FakeLayoutImageUpload()),
            description="원형 배치 스케치",
        )
        assert execution.result.is_error is True
        assert json.loads(execution.result.content)["error"] == "첨부된 이미지가 없습니다"
        assert provider.calls == []

    def test_vision_provider_unwired_is_a_distinct_error(self):
        """capability 미배선과 이미지 부재는 다른 오류다 — 둘 다 뭉개지 않는다."""
        execution = _dispatch(
            _registry(vision_provider=None, layout_image_upload=_attached_image()),
            description="원형 배치 스케치",
        )
        assert execution.result.is_error is True
        assert "vision_provider" in json.loads(execution.result.content)["error"]


class TestNonJsonModelResponse:
    """모델 비-JSON 응답 처리 — claude_code 어댑터의 정직한 거부 문구도 이 경로다."""

    def test_plain_prose_reply_is_refused_not_guessed(self):
        provider = _MockVisionProvider("이 이미지는 원형으로 배치된 조명 6대로 보입니다.")
        execution = _dispatch(
            _registry(vision_provider=provider, layout_image_upload=_attached_image()),
            description="원형 배치 스케치",
        )
        assert execution.result.is_error is True
        assert "JSON" in json.loads(execution.result.content)["error"]

    def test_claude_code_honest_refusal_text_is_treated_as_non_json(self):
        provider = _MockVisionProvider(
            "현재 프로바이더(claude_code)는 이미지를 읽을 수 없습니다. "
            "provider.toml에서 anthropic 또는 gemini로 전환하세요."
        )
        execution = _dispatch(
            _registry(vision_provider=provider, layout_image_upload=_attached_image()),
            description="원형 배치 스케치",
        )
        assert execution.result.is_error is True

    def test_json_array_instead_of_object_is_refused(self):
        provider = _MockVisionProvider(json.dumps(["rings", "radial"]))
        execution = _dispatch(
            _registry(vision_provider=provider, layout_image_upload=_attached_image()),
            description="원형 배치 스케치",
        )
        assert execution.result.is_error is True
        assert "객체" in json.loads(execution.result.content)["error"]


class TestPixelEstimationFieldsRejected:
    """픽셀 추정 필드 거부 — interpreted/최상위 모두 스키마 밖 키는 거부."""

    def test_extra_interpreted_key_is_rejected(self):
        response = json.dumps(
            {
                "pattern": "rings",
                "layers": [{"count": 6}],
                "symmetry": "radial",
                "confidence": "medium",
                "annotations": [
                    {
                        "text": "간격 2m",
                        "interpreted": {"spacing": 2.0, "estimated_px_ratio": 0.014},
                        "applies_to": "outer ring",
                    }
                ],
                "unresolved": [],
            }
        )
        provider = _MockVisionProvider(response)
        execution = _dispatch(
            _registry(vision_provider=provider, layout_image_upload=_attached_image()),
            description="원형 배치 스케치",
        )
        assert execution.result.is_error is True
        error = json.loads(execution.result.content)["error"]
        assert "스키마 밖 키" in error
        assert "estimated_px_ratio" in error

    def test_extra_top_level_key_is_rejected(self):
        response = json.dumps(
            {
                "pattern": "rings",
                "layers": [{"count": 6}],
                "symmetry": "radial",
                "confidence": "medium",
                "annotations": [],
                "unresolved": [],
                "pixel_scale_estimate": 0.5,
            }
        )
        provider = _MockVisionProvider(response)
        execution = _dispatch(
            _registry(vision_provider=provider, layout_image_upload=_attached_image()),
            description="원형 배치 스케치",
        )
        assert execution.result.is_error is True
        error = json.loads(execution.result.content)["error"]
        assert "스키마 밖 키" in error
        assert "pixel_scale_estimate" in error

    def test_unknown_pattern_value_is_rejected(self):
        response = json.dumps(
            {
                "pattern": "spiral",
                "layers": [{"count": 6}],
                "symmetry": "radial",
                "confidence": "medium",
                "annotations": [],
                "unresolved": [],
            }
        )
        provider = _MockVisionProvider(response)
        execution = _dispatch(
            _registry(vision_provider=provider, layout_image_upload=_attached_image()),
            description="원형 배치 스케치",
        )
        assert execution.result.is_error is True
        assert "pattern" in json.loads(execution.result.content)["error"]


class TestDescriptionParameter:
    def test_missing_description_is_rejected(self):
        provider = _MockVisionProvider(_VALID_RESPONSE)
        execution = _dispatch(
            _registry(vision_provider=provider, layout_image_upload=_attached_image()),
        )
        assert execution.result.is_error is True
        assert provider.calls == []

    def test_blank_description_is_rejected(self):
        provider = _MockVisionProvider(_VALID_RESPONSE)
        execution = _dispatch(
            _registry(vision_provider=provider, layout_image_upload=_attached_image()),
            description="   ",
        )
        assert execution.result.is_error is True
        assert provider.calls == []
