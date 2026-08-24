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
from fastapi.testclient import TestClient

from server.web.app import _PROTOCOL_ERROR_MESSAGE, create_app
from server.web.messages import (
    LAYOUT_IMAGE_MIME_TYPES,
    MAX_LAYOUT_IMAGE_BYTES,
    PROTOCOL_VERSION,
    LayoutImageRejectedError,
    ProtocolError,
    parse_client_message,
)
from server.web.session import LayoutImageUpload, _base64_decoded_size

from .conftest import recv_frame
from .test_runner_self_correction import ScriptedProvider
from .test_web_app import _deps, _send
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
    # LayoutImageRejectedError (a ProtocolError subclass) — the named class is
    # what lets app.py answer with the contract's kind="layout_image_rejected"
    # instead of the anonymous kind="protocol" (contract.md §1).

    def test_rejects_unlisted_mime_type(self):
        with pytest.raises(LayoutImageRejectedError):
            parse_client_message(
                _raw(file_name="plan.gif", mime_type="image/gif", content_base64=_payload(16))
            )

    def test_rejects_invalid_base64(self):
        with pytest.raises(LayoutImageRejectedError):
            parse_client_message(
                _raw(file_name="plan.png", mime_type=_PNG_MIME, content_base64="not base64")
            )

    def test_rejects_oversized_payload(self):
        oversized = _payload(MAX_LAYOUT_IMAGE_BYTES + 1)
        with pytest.raises(LayoutImageRejectedError):
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
            parse_client_message(_raw(file_name="plan.png", mime_type=_PNG_MIME, content_base64=""))

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
        # First upload: nothing was replaced, so the notice must not claim it.
        assert "교체" not in event["message"]
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
        # The session keeps ONE image; the second notice says the swap out
        # loud so the operator never believes both sketches are attached.
        assert "교체" not in sent[0]["message"]
        assert "교체" in sent[1]["message"]

    def test_upload_does_not_start_a_model_instruction(self, tmp_path):
        # Unlike upload_vectorworks_export, this must NOT call run_instruction
        # — analysis is a tool the model reaches for later (M3), not an
        # automatic side effect of attaching a file.
        session, _console, _audit, sent, _channel = _session(tmp_path, ScriptedProvider([]))
        session.upload_layout_image("a.png", _PNG_MIME, _payload(16))
        assert all(event["type"] != "chat_response" for event in sent)


class TestAppLevelRejection:
    """The WS layer's half of the contract: kind="layout_image_rejected".

    Same TestClient shape as test_web_app.py — the parse rejection happens in
    the app's receive loop, so a session-method test can never see it.
    """

    def test_a_rejected_upload_answers_with_the_contract_kind_and_reason(self, tmp_path):
        deps, _console, _gate = _deps(tmp_path, ScriptedProvider([]))
        with TestClient(create_app(deps)) as client, client.websocket_connect("/ws") as ws:
            recv_frame(ws)  # initial status
            _send(
                ws,
                type="layout_image_upload",
                file_name="plan.gif",
                mime_type="image/gif",
                content_base64=_payload(16),
            )
            event = recv_frame(ws)
        assert event["type"] == "error"
        assert event["kind"] == "layout_image_rejected"
        # The ACTUAL reason travels (contract.md §1) — safe because every
        # reason is a fixed server-authored phrase, never user input.
        allowed = ", ".join(LAYOUT_IMAGE_MIME_TYPES)
        assert event["message"] == f"layout_image_upload.mime_type must be one of: {allowed}"

    def test_other_protocol_errors_keep_the_generic_kind_and_message(self, tmp_path):
        # Regression guard: only the layout-image branch got the named kind.
        # Any other message type's ProtocolError must still surface as the
        # byte-identical generic answer (kind="protocol", fixed Korean text).
        deps, _console, _gate = _deps(tmp_path, ScriptedProvider([]))
        with TestClient(create_app(deps)) as client, client.websocket_connect("/ws") as ws:
            recv_frame(ws)  # initial status
            _send(ws, type="chat")  # ProtocolError: chat.text is missing
            event = recv_frame(ws)
        assert event["type"] == "error"
        assert event["kind"] == "protocol"
        assert event["message"] == _PROTOCOL_ERROR_MESSAGE


class TestAckSizeArithmetic:
    """IMG-SEC-05: the ack's size comes from length arithmetic, not a second
    5 MiB decode. The arithmetic must be EXACT for every padding shape."""

    # 3n / 3n+1 / 3n+2 decoded bytes → 0 / 2 / 1 trailing '=' — all three
    # padding cases base64 can produce.
    @pytest.mark.parametrize("n_bytes", [3072, 3073, 3074])
    def test_arithmetic_matches_a_real_decode_for_every_padding(self, n_bytes):
        encoded = _payload(n_bytes)
        assert _base64_decoded_size(encoded) == len(base64.b64decode(encoded)) == n_bytes

    def test_the_notice_reports_the_arithmetic_size(self, tmp_path):
        session, _console, _audit, _sent, _channel = _session(tmp_path, ScriptedProvider([]))
        # 5000 bytes: 5000 % 3 == 2 → one trailing '=' — a padded shape, and
        # the KB figure must still equal the decoded truth (5000 // 1024 == 4).
        event = session.upload_layout_image("pad.png", _PNG_MIME, _payload(5000))
        assert "(4KB)" in event["message"]
