"""M2 — 오디오 업로드 경로를 **WebSocket 층을 실제로 지나서** 판정한다.

AC-MUSICSYNC-013 · AC-MUSICSYNC-014 · REQ-MUSICSYNC-013 · REQ-MUSICSYNC-014.

⚠️ **이 파일의 존재 이유는 층이다.** 이 저장소는 정확히 같은 사고를 이미 겪었다 —
``parse_client_message`` 는 새 타입을 통과시키는데 ``server/web/app.py`` 에 디스패치
분기가 없어 메시지가 **조용히 버려졌고**, 기존 테스트가 전부 session 메서드를
직접 불러서 그 층을 지나지 않았기 때문에 아무도 몰랐다(``app.py:505-513`` 주석).

그러므로 아래 왕복 시험들은 ``session.upload_song_audio`` 를 **직접 부르지
않는다**. 직접 호출 시험은 app.py 의 분기를 지우고도 통과한다 — 즉 이 회귀를
판정할 수 없다. AC-MUSICSYNC-013 이 요구하는 「분기를 제거하면 실패하는 시험」은
반드시 ``client.websocket_connect`` 를 지나는 이 형태여야 한다.

콘솔 접촉: 0건. ``FakeConsole`` 만 쓰고 실기 포트로는 한 바이트도 나가지 않는다.
"""

from __future__ import annotations

import base64
import hashlib
import json

import pytest
from fastapi.testclient import TestClient

from server.safety.audit import AuditLog
from server.safety.gate import SafetyGate
from server.web.app import WebDeps, create_app
from server.web.approval_bridge import ApprovalChannel
from server.web.messages import (
    MAX_SONG_AUDIO_BYTES,
    PROTOCOL_VERSION,
    SONG_AUDIO_UPLOAD_EXTENSIONS,
    ProtocolError,
    SongAudioRejectedError,
    parse_client_message,
)

from .conftest import drain_until as _receive_until
from .conftest import recv_frame
from .fixtures.audio import synthesize_track
from .test_runner_self_correction import ScriptedProvider
from .test_safety_gate import FakeConsole

SMALL_WAV = synthesize_track(duration_ms=3000)
SMALL_WAV_B64 = base64.b64encode(SMALL_WAV).decode("ascii")
SMALL_WAV_SHA256 = hashlib.sha256(SMALL_WAV).hexdigest()


def _deps(tmp_path):
    console = FakeConsole()
    audit = AuditLog(tmp_path / "audit")
    channel = ApprovalChannel(timeout_seconds=2.0)
    gate = SafetyGate(console=console, audit=audit, approval_port=channel)
    return WebDeps(
        gate=gate,
        provider=ScriptedProvider([]),
        system_prefix="PREFIX",
        audit=audit,
        approval_channel=channel,
    )


def _send(ws, **fields):
    ws.send_text(json.dumps({"v": PROTOCOL_VERSION, **fields}, ensure_ascii=False))


def _frame(**overrides) -> str:
    payload = {
        "v": PROTOCOL_VERSION,
        "type": "song_audio_upload",
        "file_name": "track.wav",
        "mime_type": "audio/wav",
        "content_base64": SMALL_WAV_B64,
    }
    payload.update(overrides)
    return json.dumps(payload, ensure_ascii=False)


# =============================================================================
# 검증 층 — messages.py (AC-MUSICSYNC-014)
# =============================================================================


class TestTheFrameIsValidatedBeforeAnythingIsStored:
    def test_a_well_formed_frame_is_accepted(self):
        parsed = parse_client_message(_frame())
        assert parsed["type"] == "song_audio_upload"
        assert parsed["file_name"] == "track.wav"
        assert parsed["mime_type"] == "audio/wav"

    @pytest.mark.parametrize("extension", SONG_AUDIO_UPLOAD_EXTENSIONS)
    def test_every_declared_extension_is_accepted(self, extension):
        parsed = parse_client_message(_frame(file_name=f"track{extension}"))
        assert parsed["file_name"].endswith(extension)

    def test_an_unlisted_extension_is_refused_in_korean(self):
        with pytest.raises(SongAudioRejectedError) as caught:
            parse_client_message(_frame(file_name="track.pdf"))
        assert any("가" <= ch <= "힣" for ch in str(caught.value))

    def test_an_unlisted_mime_type_is_refused_in_korean(self):
        with pytest.raises(SongAudioRejectedError) as caught:
            parse_client_message(_frame(mime_type="application/pdf"))
        assert any("가" <= ch <= "힣" for ch in str(caught.value))

    def test_an_empty_payload_is_refused(self):
        with pytest.raises(SongAudioRejectedError):
            parse_client_message(_frame(content_base64=""))

    def test_non_base64_is_refused(self):
        with pytest.raises(SongAudioRejectedError):
            parse_client_message(_frame(content_base64="이건 base64 가 아니다"))

    def test_the_rejection_class_is_a_protocol_error_subclass(self):
        # 상류에서 「처리 전 거절」로 다루는 모든 자리가 그대로 동작해야 한다.
        assert issubclass(SongAudioRejectedError, ProtocolError)


class TestTheEightMebibyteCapIsMeasuredOnDecodedBytes:
    """AC-MUSICSYNC-014 — 상한은 **디코드된 원본** 8 MiB 하나다.

    ``messages.py:218`` 의 기존 검사와 같은 형태다. base64 문자열 길이 상한은
    그 8 MiB 에서 **파생된 값**이지 별도 상한이 아니다(REQ-MUSICSYNC-014).
    """

    def test_the_cap_is_eight_mebibytes(self):
        assert MAX_SONG_AUDIO_BYTES == 8 * 1024 * 1024

    def test_a_payload_over_the_cap_is_refused_with_the_number_in_the_reason(self):
        oversized = base64.b64encode(b"\x00" * (MAX_SONG_AUDIO_BYTES + 1)).decode("ascii")
        with pytest.raises(SongAudioRejectedError) as caught:
            parse_client_message(_frame(content_base64=oversized))
        reason = str(caught.value)
        assert any("가" <= ch <= "힣" for ch in reason), reason
        # 「상한 수치를 명시」 — 사람이 얼마나 줄여야 하는지 알 수 있어야 한다.
        assert "8 MiB" in reason
        assert str(MAX_SONG_AUDIO_BYTES) in reason

    def test_a_payload_exactly_at_the_cap_is_accepted(self):
        # 경계 대조군: 상한이 무엇이든 거절하는 검사면 위 시험은 공허하다.
        at_cap = base64.b64encode(b"\x00" * MAX_SONG_AUDIO_BYTES).decode("ascii")
        parsed = parse_client_message(_frame(content_base64=at_cap))
        assert parsed["content_base64"] == at_cap


# =============================================================================
# 디스패치 층 — app.py (AC-MUSICSYNC-013)
# =============================================================================


class TestTheUploadTravelsTheWholeWireNotJustTheSessionMethod:
    """AC-MUSICSYNC-013 — 이 클래스가 분기 회귀의 판정자다.

    ``server/web/app.py`` 의 ``song_audio_upload`` 디스패치 분기를 지우면 이
    시험들은 **실패한다**(프레임은 파싱되지만 아무 응답도 오지 않아
    ``recv_frame`` 이 시간 상한에서 끊긴다). session 메서드를 직접 부르는
    시험만으로는 그 층을 지나지 않아 그대로 통과해 버린다 — 그 사실이 이
    파일이 존재하는 이유다.
    """

    def test_a_song_audio_upload_is_stored_and_acked_over_the_wire(self, tmp_path):
        with (
            TestClient(create_app(_deps(tmp_path))) as client,
            client.websocket_connect("/ws") as ws,
        ):
            recv_frame(ws)  # 최초 status
            _send(
                ws,
                type="song_audio_upload",
                file_name="track.wav",
                mime_type="audio/wav",
                content_base64=SMALL_WAV_B64,
            )
            event = _receive_until(ws, "notice")
        assert "track.wav" in event["message"]
        assert "첨부됨" in event["message"]

    def test_the_ack_names_the_sha256_and_the_byte_count(self, tmp_path):
        # 운영자가 원본 파일의 ``shasum -a 256`` 값과 대조할 수 있어야 한다
        # (``UploadedSheet`` 가 세운 관례를 그대로 따른다).
        with (
            TestClient(create_app(_deps(tmp_path))) as client,
            client.websocket_connect("/ws") as ws,
        ):
            recv_frame(ws)
            _send(
                ws,
                type="song_audio_upload",
                file_name="track.wav",
                mime_type="audio/wav",
                content_base64=SMALL_WAV_B64,
            )
            event = _receive_until(ws, "notice")
        assert SMALL_WAV_SHA256 in event["message"]
        assert str(len(SMALL_WAV)) in event["message"]

    def test_the_payload_bytes_never_ride_back_out(self, tmp_path):
        with (
            TestClient(create_app(_deps(tmp_path))) as client,
            client.websocket_connect("/ws") as ws,
        ):
            recv_frame(ws)
            _send(
                ws,
                type="song_audio_upload",
                file_name="track.wav",
                mime_type="audio/wav",
                content_base64=SMALL_WAV_B64,
            )
            event = _receive_until(ws, "notice")
        assert SMALL_WAV_B64 not in json.dumps(event, ensure_ascii=False)

    def test_a_replacement_is_said_out_loud(self, tmp_path):
        # 침묵하면 운영자가 두 곡이 붙어 있다고 믿은 채 엉뚱한 곡으로 만든
        # 계획을 승인할 수 있다(``upload_layout_image`` 가 세운 이유).
        with (
            TestClient(create_app(_deps(tmp_path))) as client,
            client.websocket_connect("/ws") as ws,
        ):
            recv_frame(ws)
            for name in ("first.wav", "second.wav"):
                _send(
                    ws,
                    type="song_audio_upload",
                    file_name=name,
                    mime_type="audio/wav",
                    content_base64=SMALL_WAV_B64,
                )
                event = _receive_until(ws, "notice")
        assert "second.wav" in event["message"]
        assert "교체" in event["message"]

    def test_the_first_upload_does_not_claim_a_replacement(self, tmp_path):
        # 대조군: 교체 문구가 항상 붙으면 위 시험은 공허하다.
        with (
            TestClient(create_app(_deps(tmp_path))) as client,
            client.websocket_connect("/ws") as ws,
        ):
            recv_frame(ws)
            _send(
                ws,
                type="song_audio_upload",
                file_name="only.wav",
                mime_type="audio/wav",
                content_base64=SMALL_WAV_B64,
            )
            event = _receive_until(ws, "notice")
        assert "교체" not in event["message"]

    def test_a_rejected_upload_comes_back_under_its_own_error_kind(self, tmp_path):
        oversized = base64.b64encode(b"\x00" * (MAX_SONG_AUDIO_BYTES + 1)).decode("ascii")
        with (
            TestClient(create_app(_deps(tmp_path))) as client,
            client.websocket_connect("/ws") as ws,
        ):
            recv_frame(ws)
            _send(
                ws,
                type="song_audio_upload",
                file_name="huge.wav",
                mime_type="audio/wav",
                content_base64=oversized,
            )
            event = recv_frame(ws)
        assert event["type"] == "error"
        # 이름 붙은 종류여야 UI 가 「프레임이 깨졌다」와 「파일이 거절됐다」를
        # 가른다 — layout_image_rejected 가 세운 관례.
        assert event["kind"] == "song_audio_rejected"
        assert "8 MiB" in event["message"]

    def test_the_connection_survives_a_rejection(self, tmp_path):
        # 거절이 연결을 끊으면 운영자는 더 작은 파일을 다시 올릴 수 없다.
        oversized = base64.b64encode(b"\x00" * (MAX_SONG_AUDIO_BYTES + 1)).decode("ascii")
        with (
            TestClient(create_app(_deps(tmp_path))) as client,
            client.websocket_connect("/ws") as ws,
        ):
            recv_frame(ws)
            _send(
                ws,
                type="song_audio_upload",
                file_name="huge.wav",
                mime_type="audio/wav",
                content_base64=oversized,
            )
            assert recv_frame(ws)["type"] == "error"
            _send(ws, type="status_request")
            assert recv_frame(ws)["type"] == "status"


# =============================================================================
# 보관 층 — session.py
# =============================================================================


def _session(tmp_path, events: list[dict] | None = None):
    from server.web.session import ChatSession

    deps = _deps(tmp_path)
    sink = events if events is not None else []
    return ChatSession(
        gate=deps.gate,
        provider=deps.provider,
        system_prefix="PREFIX",
        audit=deps.audit,
        send_event=sink.append,
        approval_channel=deps.approval_channel,
    )


class TestNothingIsStoredWhenTheFrameIsRefused:
    """validate-before-store — 거절된 프레임은 세션에 흔적을 남기지 않는다."""

    def test_the_session_holds_no_audio_after_a_refused_frame(self, tmp_path):
        session = _session(tmp_path)
        # 거절은 파싱 단계에서 난다 — 세션 메서드는 아예 불리지 않는다.
        with pytest.raises(SongAudioRejectedError):
            parse_client_message(_frame(file_name="track.pdf"))
        assert session.song_audio is None

    def test_an_accepted_frame_does_reach_the_session(self, tmp_path):
        # 대조군: 항상 None 이면 위 시험은 공허하다.
        session = _session(tmp_path)
        session.upload_song_audio("track.wav", "audio/wav", SMALL_WAV_B64)
        stored = session.song_audio
        assert stored is not None
        assert stored.file_name == "track.wav"
        assert stored.sha256 == SMALL_WAV_SHA256
        assert stored.byte_length == len(SMALL_WAV)

    def test_the_stored_sha256_is_of_the_decoded_bytes_not_the_base64_string(self, tmp_path):
        # 운영자가 ``shasum -a 256 track.wav`` 와 대조할 수 있어야 한다 —
        # base64 문자열의 해시를 담으면 그 대조가 언제나 어긋난다.
        session = _session(tmp_path)
        session.upload_song_audio("track.wav", "audio/wav", SMALL_WAV_B64)
        assert session.song_audio.sha256 == hashlib.sha256(SMALL_WAV).hexdigest()
        assert session.song_audio.sha256 != hashlib.sha256(SMALL_WAV_B64.encode()).hexdigest()
