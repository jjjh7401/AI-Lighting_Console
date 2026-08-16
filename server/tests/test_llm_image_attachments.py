"""LLM image-attachment wire tests (M2 — REQ-IMGLAYOUT-004/005/006, contract.md §2).

Mock-client tests pinning the per-adapter wire payload for an image-bearing
``UserMessage``, plus a byte-identical regression assertion for the
images-empty (default) path on each adapter that already had coverage.
"""

from __future__ import annotations

import base64
import json
import subprocess
from types import SimpleNamespace

from server.llm.anthropic_adapter import AnthropicAdapter
from server.llm.claude_code_adapter import ClaudeCodeAdapter
from server.llm.config import AnthropicSettings, GeminiSettings
from server.llm.gemini_adapter import GeminiAdapter
from server.llm.types import ImageAttachment, ToolDefinition, UserMessage

_PREFIX = "RULEBOOK PREFIX (fixed)"
_PNG_BYTES = b"\x89PNG\r\n\x1a\nfake-bytes-for-test"
_PNG_B64 = base64.b64encode(_PNG_BYTES).decode("ascii")

_TOOL = ToolDefinition(
    name="query_state",
    description="Query the console object tree.",
    parameters={"type": "object", "properties": {}},
)


def _image() -> ImageAttachment:
    return ImageAttachment(mime_type="image/png", content_base64=_PNG_B64)


# -- Anthropic --------------------------------------------------------------


class _FakeAnthropicMessages:
    def __init__(self, response):
        self.response = response
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


class _FakeAnthropicClient:
    def __init__(self, response):
        self.messages = _FakeAnthropicMessages(response)


def _anthropic_text_response(text: str = "done") -> SimpleNamespace:
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text)],
        stop_reason="end_turn",
        usage=SimpleNamespace(
            input_tokens=1,
            output_tokens=1,
            cache_read_input_tokens=0,
            cache_creation_input_tokens=0,
        ),
    )


class TestAnthropicImageWire:
    def test_images_present_become_a_block_array_with_text_last(self):
        client = _FakeAnthropicClient(_anthropic_text_response())
        adapter = AnthropicAdapter(AnthropicSettings(model="claude-opus-4-8"), client=client)
        adapter.complete(
            system_prefix=_PREFIX,
            conversation=[UserMessage(text="이 스케치대로 배치해줘", images=(_image(),))],
            tools=(_TOOL,),
        )
        content = client.messages.calls[0]["messages"][0]["content"]
        assert content == [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": _PNG_B64,
                },
            },
            {"type": "text", "text": "이 스케치대로 배치해줘"},
        ]

    def test_multiple_images_all_precede_the_single_text_block(self):
        client = _FakeAnthropicClient(_anthropic_text_response())
        adapter = AnthropicAdapter(AnthropicSettings(model="claude-opus-4-8"), client=client)
        adapter.complete(
            system_prefix=_PREFIX,
            conversation=[UserMessage(text="두 장 비교", images=(_image(), _image()))],
            tools=(),
        )
        content = client.messages.calls[0]["messages"][0]["content"]
        assert [block["type"] for block in content] == ["image", "image", "text"]

    def test_no_images_wire_payload_is_byte_identical_to_pre_image_shape(self):
        # Regression: default images=() must keep sending a plain string
        # content, not an empty-array-plus-text block wrapper.
        client = _FakeAnthropicClient(_anthropic_text_response())
        adapter = AnthropicAdapter(AnthropicSettings(model="claude-opus-4-8"), client=client)
        adapter.complete(
            system_prefix=_PREFIX,
            conversation=[UserMessage(text="보컬 그룹 만들어줘")],
            tools=(_TOOL,),
        )
        messages = client.messages.calls[0]["messages"]
        assert messages == [{"role": "user", "content": "보컬 그룹 만들어줘"}]


# -- Gemini -------------------------------------------------------------


class _FakeGeminiModels:
    def __init__(self, response):
        self.response = response
        self.calls: list[dict] = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


class _FakeGeminiClient:
    def __init__(self, response):
        self.models = _FakeGeminiModels(response)
        self.caches = None  # context_caching disabled in these tests


def _gemini_text_response(text: str = "done") -> SimpleNamespace:
    part = SimpleNamespace(text=text, function_call=None)
    content = SimpleNamespace(role="model", parts=[part])
    return SimpleNamespace(candidates=[SimpleNamespace(content=content)], usage_metadata=None)


class TestGeminiImageWire:
    def test_images_become_inline_data_parts_before_the_text_part(self):
        client = _FakeGeminiClient(_gemini_text_response())
        adapter = GeminiAdapter(
            GeminiSettings(model="gemini-2.5-pro", context_caching=False), client=client
        )
        adapter.complete(
            system_prefix=_PREFIX,
            conversation=[UserMessage(text="이 스케치대로 배치해줘", images=(_image(),))],
            tools=(),
        )
        contents = client.models.calls[0]["contents"]
        parts = contents[0].parts
        assert len(parts) == 2
        assert parts[0].inline_data.data == _PNG_BYTES
        assert parts[0].inline_data.mime_type == "image/png"
        assert parts[1].text == "이 스케치대로 배치해줘"

    def test_no_images_wire_payload_is_byte_identical_to_pre_image_shape(self):
        client = _FakeGeminiClient(_gemini_text_response())
        adapter = GeminiAdapter(
            GeminiSettings(model="gemini-2.5-pro", context_caching=False), client=client
        )
        adapter.complete(
            system_prefix=_PREFIX,
            conversation=[UserMessage(text="그룹 상태 알려줘")],
            tools=(),
        )
        contents = client.models.calls[0]["contents"]
        assert contents[0].role == "user"
        assert len(contents[0].parts) == 1
        assert contents[0].parts[0].text == "그룹 상태 알려줘"


# -- Claude Code (honest refusal) ----------------------------------------


class TestClaudeCodeImageRefusal:
    def test_images_present_refuses_honestly_without_invoking_the_cli(self):
        calls: list[list[str]] = []

        def runner(command, **_kwargs):
            calls.append(command)
            raise AssertionError("claude CLI must not be invoked when images are attached")

        adapter = ClaudeCodeAdapter("sonnet", runner=runner)
        turn = adapter.complete(
            system_prefix=_PREFIX,
            conversation=[UserMessage(text="이 스케치대로 배치해줘", images=(_image(),))],
            tools=(_TOOL,),
        )

        assert calls == []
        assert turn.provider == "claude_code"
        assert turn.tool_calls == ()
        assert turn.stop_reason == "end"
        assert "이미지를 읽을 수 없습니다" in turn.text

    def test_no_images_still_calls_the_cli_normally(self):
        def runner(command, **_kwargs):
            return subprocess.CompletedProcess(
                command,
                0,
                stdout=json.dumps({"structured_output": {"text": "ok", "tool_calls": []}}),
                stderr="",
            )

        adapter = ClaudeCodeAdapter("sonnet", runner=runner)
        turn = adapter.complete(
            system_prefix=_PREFIX,
            conversation=[UserMessage(text="hi")],
            tools=(_TOOL,),
        )
        assert turn.text == "ok"
