"""Layout-image attachment channel tests (SPEC-COPILOT-IMGLAYOUT-001 M1).

Two layers, same split as the Vectorworks upload channel: ``messages.py``
validates the wire frame (MIME allowlist, base64, the 5 MiB cap) BEFORE
anything reaches session storage; ``ChatSession`` stores the most recent
image only (a new upload replaces it) and confirms with a plain Korean
``notice`` event — no model call, no analysis (that is M3's
``analyse_layout_image`` tool, invoked later from a chat turn).
"""

from __future__ import annotations

import base64
import json

import pytest

from server.web.messages import (
    LAYOUT_IMAGE_MIME_TYPES,
    MAX_LAYOUT_IMAGE_BYTES,
    PROTOCOL_VERSION,
    ProtocolError,
    parse_client_message,
)
from server.web.session import LayoutImageUpload

from .test_runner_self_correction import ScriptedProvider
from .test_web_session import _session

_PNG_MIME = "image/png"


def _raw(**fields) -> str:
    return json.dumps({"v": PROTOCOL_VERSION, "type": "layout_image_upload", **fields})


def _payload(n_bytes: int) -> str:
    """base64 for an ``n_bytes``-long decoded payload (byte-exact)."""
    return base64.b64encode(b"x" * n_bytes).decode()


class TestClientMessageParsing:
    def test_layout_image_upload_parses(self):
        message = parse_client_message(
            _raw(file_name="stage-sketch.png", mime_type=_PNG_MIME, content_base64=_payload(16))
        )
        assert message == {
            "v": PROTOCOL_VERSION,
            "type": "layout_image_upload",
            "file_name": "stage-sketch.png",
            "mime_type": _PNG_MIME,
            "content_base64": _payload(16),
        }

    @pytest.mark.parametrize("mime_type", ["image/jpeg", "image/webp"])
    def test_layout_image_upload_accepts_every_allowed_mime(self, mime_type):
        message = parse_client_message(
            _raw(file_name="ref.jpg", mime_type=mime_type, content_base64=_payload(16))
        )
        assert message["mime_type"] == mime_type

    def test_allowed_mime_set_matches_contract(self):
        # Contract §1: image/png, image/jpeg, image/webp — no more, no less.
        assert LAYOUT_IMAGE_MIME_TYPES == ("image/png", "image/jpeg", "image/webp")

    # -- 검증 거부 3종: MIME 화이트리스트 / base64 유효성 / 5MB 상한 -------------

    def test_rejects_unlisted_mime_type(self):
        with pytest.raises(ProtocolError):
            parse_client_message(
                _raw(file_name="plan.gif", mime_type="image/gif", content_base64=_payload(16))
            )

    def test_rejects_invalid_base64(self):
        with pytest.raises(ProtocolError):
            parse_client_message(
                _raw(file_name="plan.png", mime_type=_PNG_MIME, content_base64="not base64")
            )

    def test_rejects_oversized_payload(self):
        oversized = _payload(MAX_LAYOUT_IMAGE_BYTES + 1)
        with pytest.raises(ProtocolError):
            parse_client_message(
                _raw(file_name="plan.png", mime_type=_PNG_MIME, content_base64=oversized)
            )

    def test_rejects_missing_file_name(self):
        with pytest.raises(ProtocolError):
            parse_client_message(
                _raw(file_name="  ", mime_type=_PNG_MIME, content_base64=_payload(16))
            )

    def test_rejects_empty_content_base64(self):
        with pytest.raises(ProtocolError):
            parse_client_message(
                _raw(file_name="plan.png", mime_type=_PNG_MIME, content_base64="")
            )

    def test_layout_image_upload_registered_on_client_message_types(self):
        # The whole-message unknown-type rejection path (kept in this file
        # since it exercises the same allowlist the branch above lives on).
        assert (
            parse_client_message(
                _raw(file_name="p.png", mime_type=_PNG_MIME, content_base64=_payload(16))
            )["type"]
            == "layout_image_upload"
        )


class TestSessionStorageAndReplace:
    def test_upload_stores_and_confirms_with_a_notice(self, tmp_path):
        session, _console, _audit, sent, _channel = _session(tmp_path, ScriptedProvider([]))
        content = _payload(2048)  # 2048 decoded bytes -> "2KB" in the notice
        event = session.upload_layout_image("stage-sketch.png", _PNG_MIME, content)

        assert session._layout_image == LayoutImageUpload(
            file_name="stage-sketch.png", mime_type=_PNG_MIME, content_base64=content
        )
        assert event["type"] == "notice"
        assert "stage-sketch.png" in event["message"]
        assert "2KB" in event["message"]
        assert sent == [event]

    def test_a_new_upload_replaces_the_previous_one(self, tmp_path):
        session, _console, _audit, sent, _channel = _session(tmp_path, ScriptedProvider([]))
        session.upload_layout_image("first.png", _PNG_MIME, _payload(16))
        session.upload_layout_image("second.jpg", "image/jpeg", _payload(32))

        assert session._layout_image == LayoutImageUpload(
            file_name="second.jpg", mime_type="image/jpeg", content_base64=_payload(32)
        )
        # Only the most recent image is kept — no accumulation.
        assert session._layout_image.file_name != "first.png"
        assert len(sent) == 2  # one notice per upload, both surfaced

    def test_upload_does_not_start_a_model_instruction(self, tmp_path):
        # Unlike upload_vectorworks_export, this must NOT call run_instruction
        # — analysis is a tool the model reaches for later (M3), not an
        # automatic side effect of attaching a file.
        session, _console, _audit, sent, _channel = _session(tmp_path, ScriptedProvider([]))
        session.upload_layout_image("a.png", _PNG_MIME, _payload(16))
        assert all(event["type"] != "chat_response" for event in sent)
