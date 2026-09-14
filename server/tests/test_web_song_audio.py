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
import time

import pytest
from fastapi.testclient import TestClient

from server.safety.audit import AuditLog
from server.safety.gate import SafetyGate
from server.web.app import WebDeps, create_app
from server.web.approval_bridge import ApprovalChannel
from server.web.messages import (
    MAX_SONG_AUDIO_BYTES,
    MAX_SONG_AUDIO_CHUNK_BASE64_LENGTH,
    PROTOCOL_VERSION,
    SONG_AUDIO_UPLOAD_EXTENSIONS,
    ProtocolError,
    SongAudioAssembly,
    SongAudioRejectedError,
    parse_client_message,
)
from server.web.question import QuestionChannel

from .conftest import drain_until as _receive_until
from .conftest import recv_frame
from .fixtures.audio import synthesize_track
from .test_runner_self_correction import ScriptedProvider
from .test_safety_gate import FakeConsole

SMALL_WAV = synthesize_track(duration_ms=3000)
SMALL_WAV_B64 = base64.b64encode(SMALL_WAV).decode("ascii")
SMALL_WAV_SHA256 = hashlib.sha256(SMALL_WAV).hexdigest()


def _deps(tmp_path, *, question_channel=None):
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
        question_channel=question_channel,
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


class TestTheCapIsMeasuredOnDecodedBytes:
    """AC-MUSICSYNC-026 — 상한은 **디코드된 원본** 64 MiB 하나다.

    base64 문자열 길이 상한은 그 64 MiB 에서 **파생된 값**이지 별도 상한이
    아니다(REQ-MUSICSYNC-026). 2026-09-14 전에는 8 MiB 였고, 감독 곡 31.5MB 가
    어느 경로로도 안 올라갔다.
    """

    def test_the_cap_is_sixty_four_mebibytes(self):
        assert MAX_SONG_AUDIO_BYTES == 64 * 1024 * 1024 == 67108864

    def test_a_payload_over_the_cap_is_refused_with_the_number_in_the_reason(self):
        oversized = base64.b64encode(b"\x00" * (MAX_SONG_AUDIO_BYTES + 1)).decode("ascii")
        with pytest.raises(SongAudioRejectedError) as caught:
            parse_client_message(_frame(content_base64=oversized))
        reason = str(caught.value)
        assert any("가" <= ch <= "힣" for ch in reason), reason
        # 「상한 수치를 명시」 — 사람이 얼마나 줄여야 하는지 알 수 있어야 한다.
        assert "64 MiB" in reason
        assert str(MAX_SONG_AUDIO_BYTES) in reason

    def test_a_payload_exactly_at_the_cap_is_accepted(self):
        # 경계 대조군: 상한이 무엇이든 거절하는 검사면 위 시험은 공허하다.
        at_cap = base64.b64encode(b"\x00" * MAX_SONG_AUDIO_BYTES).decode("ascii")
        parsed = parse_client_message(_frame(content_base64=at_cap))
        assert parsed["content_base64"] == at_cap


class TestTheAnalyseFrameIsValidatedLikeItsUploadSibling:
    """``song_audio_analyse`` — 분석을 **요청하는** 프레임 (REQ-MUSICSYNC-015).

    페이로드가 없다. 붙어 있는 곡은 이미 세션에 있고, 이 프레임이 나르는 것은
    「지금 재라」는 요청과 **대조용 부수 값** 셋뿐이다. 셋 다 선택이라 안 보내도
    되고, 보내면 종류를 잰다 — 숫자 자리에 문자열이 오면 하류
    (``resolve_bpm``)에서 터지고, 터진 자리에서는 「운영자가 오타를 냈다」가
    「분석이 실패했다」로 읽힌다.
    """

    def test_a_bare_analyse_frame_is_accepted_with_every_option_absent(self):
        parsed = parse_client_message(
            json.dumps({"v": PROTOCOL_VERSION, "type": "song_audio_analyse"}, ensure_ascii=False)
        )
        assert parsed["type"] == "song_audio_analyse"
        assert parsed["sheet_bpm"] is None
        assert parsed["fx_rate"] is None
        assert parsed["beats_per_cycle"] is None

    def test_the_sheet_tempo_rides_as_the_raw_string_the_importer_read(self):
        # ``HEAD.BPM`` 은 ``120 (고정)`` 처럼 온다 — 숫자로 미리 깎지 않는다.
        # 깎는 자리는 ``parse_sheet_bpm`` 하나뿐이어야 한다.
        parsed = parse_client_message(
            json.dumps(
                {
                    "v": PROTOCOL_VERSION,
                    "type": "song_audio_analyse",
                    "sheet_bpm": "120 (고정)",
                    "fx_rate": 25.0,
                    "beats_per_cycle": 4,
                },
                ensure_ascii=False,
            )
        )
        assert parsed["sheet_bpm"] == "120 (고정)"
        assert parsed["fx_rate"] == 25.0
        assert parsed["beats_per_cycle"] == 4.0

    @pytest.mark.parametrize("field", ["fx_rate", "beats_per_cycle"])
    def test_a_non_numeric_contrast_value_is_refused(self, field):
        with pytest.raises(ProtocolError):
            parse_client_message(
                json.dumps(
                    {"v": PROTOCOL_VERSION, "type": "song_audio_analyse", field: "빠르게"},
                    ensure_ascii=False,
                )
            )

    @pytest.mark.parametrize("field", ["fx_rate", "beats_per_cycle"])
    def test_a_boolean_is_not_a_number_here(self, field):
        # ``bool`` 은 파이썬에서 ``int`` 의 하위형이다 — 먼저 걸러 내지 않으면
        # ``True`` 가 1.0 으로 흘러 들어간다(``_is_object_number`` 가 세운 이유).
        with pytest.raises(ProtocolError):
            parse_client_message(
                json.dumps(
                    {"v": PROTOCOL_VERSION, "type": "song_audio_analyse", field: True},
                    ensure_ascii=False,
                )
            )

    def test_a_non_string_sheet_tempo_is_refused(self):
        with pytest.raises(ProtocolError):
            parse_client_message(
                json.dumps(
                    {"v": PROTOCOL_VERSION, "type": "song_audio_analyse", "sheet_bpm": 120},
                    ensure_ascii=False,
                )
            )


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
        assert "64 MiB" in event["message"]

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


def _session(tmp_path, events: list[dict] | None = None, *, question_channel=None):
    from server.web.session import ChatSession

    deps = _deps(tmp_path)
    sink = events if events is not None else []
    return ChatSession(
        gate=deps.gate,
        provider=deps.provider,
        system_prefix="PREFIX",
        audit=deps.audit,
        send_event=sink.append,
        question_channel=question_channel,
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


# =============================================================================
# 확인 카드 경로 — 분석 → 카드 → 사람 → BPM (AC-MUSICSYNC-015 · 016 · 018)
# =============================================================================


class _AnsweringChannel:
    """카드를 받아 미리 정한 답을 즉시 돌려주는 가짜 질문 통로.

    실제 :class:`QuestionChannel` 은 사람을 기다린다. 여기서 재려는 것은 기다림이
    아니라 **카드의 모양과 답이 흐르는 자리**이므로, 답을 고정해 두고 카드만
    붙잡는다. 붙잡은 카드가 이 시험들의 판정 대상이다.
    """

    def __init__(self, answer: str) -> None:
        self.answer = answer
        self.cards: list = []

    def bind(self, notify, *, session_key=None) -> None:  # pragma: no cover - 배선만
        pass

    def unbind(self, *, session_key=None) -> None:  # pragma: no cover - 배선만
        pass

    def ask(self, request, *, session_key=None) -> str:
        self.cards.append(request)
        return self.answer


class TestTheAnalysisPathAlwaysGoesThroughTheCard:
    """REQ-MUSICSYNC-015 — 확인 카드가 경로상 필수다.

    DSP 결과가 사람 확인 없이 하류로 흐르는 분기는 없다(design.md §6 W9).
    """

    def _analysed(self, tmp_path, answer: str, **kwargs):
        channel = _AnsweringChannel(answer)
        session = _session(tmp_path, question_channel=channel)
        session.upload_song_audio("track.wav", "audio/wav", SMALL_WAV_B64)
        session.analyse_song_audio(**kwargs)
        return session, channel

    def test_analysing_raises_exactly_one_card(self, tmp_path):
        _session_obj, channel = self._analysed(tmp_path, "확인")
        assert len(channel.cards) == 1

    def test_the_card_is_multi_select_with_one_option_per_section(self, tmp_path):
        _session_obj, channel = self._analysed(tmp_path, "확인")
        card = channel.cards[0]
        assert card.multi is True
        assert len(card.options) >= 1
        assert all(option.selected for option in card.options)

    def test_accepting_the_card_confirms_the_measured_tempo(self, tmp_path):
        session, _channel = self._analysed(tmp_path, "확인")
        assert session.song_bpm is not None
        assert session.song_bpm.source == "measured"
        # 3초 합성 트랙이라 정답 폭을 걸지 않는다 — 여기서 재는 것은 **자리**다.
        assert session.song_bpm.bpm is not None

    def test_a_typed_override_reaches_the_resolution(self, tmp_path):
        session, _channel = self._analysed(tmp_path, "BPM 130")
        assert session.song_bpm.bpm == 130.0
        assert session.song_bpm.source == "measured"

    def test_an_unanswered_card_confirms_nothing_and_the_default_stands(self, tmp_path):
        from server.web.question import UNANSWERED

        session, _channel = self._analysed(tmp_path, UNANSWERED)
        assert session.song_bpm.source == "default"
        assert session.song_bpm.bpm is None

    def test_with_no_channel_bound_nothing_is_confirmed(self, tmp_path):
        # 볼 사람이 없는 카드는 카드가 아니다 — 확정도 없다.
        session = _session(tmp_path)
        session.upload_song_audio("track.wav", "audio/wav", SMALL_WAV_B64)
        session.analyse_song_audio()
        assert session.song_bpm.source == "default"

    def test_analysing_with_no_audio_attached_says_so(self, tmp_path):
        events: list[dict] = []
        session = _session(tmp_path, events)
        event = session.analyse_song_audio()
        assert "오디오가 없습니다" in event["message"]
        assert session.song_bpm is None


class TestTheSheetTempoDisagreementIsReportedThroughTheSession:
    """AC-MUSICSYNC-018 — 어긋남은 채택 여부와 무관하게 사용자에게 보고된다."""

    def test_a_disagreeing_sheet_value_is_named_in_the_notice(self, tmp_path):
        events: list[dict] = []
        channel = _AnsweringChannel("BPM 128")
        session = _session(tmp_path, events, question_channel=channel)
        session.upload_song_audio("track.wav", "audio/wav", SMALL_WAV_B64)
        event = session.analyse_song_audio(sheet_bpm="120 (고정)")
        assert "128" in event["message"]
        assert "120" in event["message"]
        assert "어긋" in event["message"]
        assert session.song_bpm.bpm == 128.0
        assert session.song_bpm.source == "measured"

    def test_an_agreeing_sheet_value_raises_no_disagreement(self, tmp_path):
        # 대조군: 언제나 어긋남을 외치면 위 시험은 공허하다.
        channel = _AnsweringChannel("BPM 120")
        session = _session(tmp_path, question_channel=channel)
        session.upload_song_audio("track.wav", "audio/wav", SMALL_WAV_B64)
        event = session.analyse_song_audio(sheet_bpm="120 (고정)")
        assert "어긋" not in event["message"]

    def test_the_fx_rate_back_calculation_is_reported_but_never_adopted(self, tmp_path):
        channel = _AnsweringChannel("BPM 128")
        session = _session(tmp_path, question_channel=channel)
        session.upload_song_audio("track.wav", "audio/wav", SMALL_WAV_B64)
        event = session.analyse_song_audio(sheet_bpm="120 (고정)", fx_rate=25.0, beats_per_cycle=4)
        assert "FX-Rate" in event["message"]
        assert session.song_bpm.fx_rate_back_calculated == 100.0
        assert session.song_bpm.bpm == 128.0  # 역산값 100 은 채택되지 않았다


# =============================================================================
# 분석 방아쇠 — app.py 디스패치 (AC-MUSICSYNC-013 · AC-MUSICSYNC-015)
# =============================================================================


class TestTheAnalysisTriggerTravelsTheWholeWire:
    """M2 후속 — 위 세 클래스가 잰 경로를 **무엇이 부르는가**의 판정자다.

    ``analyse_song_audio`` 는 M2 에서 완성됐지만 실서비스에서 부르는 곳이
    없었다. 업로드 프레임은 바이트를 담고 멈추고, 분석·카드·BPM 확정은 시험만이
    부르는 죽은 경로였다 — 즉 REQ-MUSICSYNC-013 → 015 사슬이 끊겨 있었다.

    ⚠️ **판정 방식은 위 업로드 클래스와 같다.** ``server/web/app.py`` 의
    ``song_audio_analyse`` 디스패치 분기를 지우면 이 클래스의 시험들은
    **실패한다**(프레임은 파싱되지만 카드가 오지 않아 ``recv_frame`` 이 시간
    상한에서 끊긴다). ``session.analyse_song_audio`` 를 직접 부르는 시험은 그
    층을 지나지 않아 분기가 없어도 그대로 통과한다 — 그것이 이 클래스가 WS 왕복
    형태여야 하는 이유다.

    콘솔 접촉: 0건.
    """

    def _analysed_over_the_wire(self, tmp_path, answer: str, **analyse_fields):
        """업로드 → 분석 요청 → 카드 → 답 → 알림, 전부 와이어를 지나서."""
        channel = QuestionChannel(timeout_seconds=5.0)
        with (
            TestClient(create_app(_deps(tmp_path, question_channel=channel))) as client,
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
            _receive_until(ws, "notice")
            _send(ws, type="song_audio_analyse", **analyse_fields)
            card = _receive_until(ws, "question_request")
            # 답을 주어 분석 스레드를 놓아 준다 — 답이 없으면 상한까지 붙잡힌다.
            _send(ws, type="question_answer", request_id=card["request_id"], answer=answer)
            notice = _receive_until(ws, "notice")
        return card, notice

    def test_the_confirmation_card_arrives_over_the_wire(self, tmp_path):
        card, _notice = self._analysed_over_the_wire(tmp_path, "확인")
        # 카드의 모양은 M2 가 정했다(``build_song_confirmation_card``) — 여기서
        # 재는 것은 그 카드가 **와이어로 도착하는가**다.
        assert card["multi"] is True
        assert len(card["options"]) >= 1
        assert all(option["selected"] for option in card["options"])

    def test_the_answer_confirms_the_tempo_through_the_same_wire(self, tmp_path):
        _card, notice = self._analysed_over_the_wire(tmp_path, "BPM 130")
        assert "130" in notice["message"]
        assert "확정" in notice["message"]

    def test_a_disagreeing_sheet_tempo_is_reported_over_the_wire(self, tmp_path):
        # AC-MUSICSYNC-018 을 **와이어 위에서** 다시 잰다: 시트 120, 사람이 적은
        # 128 → 어긋남을 말하고 128 을 채택한다.
        _card, notice = self._analysed_over_the_wire(tmp_path, "BPM 128", sheet_bpm="120 (고정)")
        assert "128" in notice["message"]
        assert "120" in notice["message"]
        assert "어긋" in notice["message"]

    def test_analysing_with_no_audio_attached_comes_back_as_an_error(self, tmp_path):
        """첨부가 없으면 분석할 것이 없다 — 터지지 않고, 이유를 한국어로 말한다.

        ⚠️ **``kind`` 를 단언하는 것이 이 시험의 전부다.** 종류를 안 재고
        ``type == "error"`` 와 「한국어인가」만 재면 이 시험은 **공허하다** —
        타입이 아예 등록되지 않은 상태에서도 ``kind="protocol"`` 오류가 같은
        모양으로 돌아오고, 그 문구(``_PROTOCOL_ERROR_MESSAGE``) 또한 한국어다.
        즉 배선이 하나도 없어도 통과해 버린다(실제로 RED 회차에서 통과했다).
        이름 붙은 종류를 요구해야 「분기가 있고, 첨부 없음을 알아봤다」를 잰다.
        """
        with (
            TestClient(create_app(_deps(tmp_path, question_channel=QuestionChannel()))) as client,
            client.websocket_connect("/ws") as ws,
        ):
            recv_frame(ws)
            _send(ws, type="song_audio_analyse")
            event = recv_frame(ws)
        assert event["type"] == "error"
        assert event["kind"] == "song_audio_missing"
        assert any("가" <= ch <= "힣" for ch in event["message"]), event["message"]
        # 「무엇을 하라」가 있어야 운영자가 다음 행동을 안다.
        assert "첨부" in event["message"]

    def test_the_connection_survives_analysing_with_no_audio(self, tmp_path):
        # 오류가 연결을 끊으면 운영자는 곡을 첨부한 뒤 다시 시도할 수 없다.
        with (
            TestClient(create_app(_deps(tmp_path, question_channel=QuestionChannel()))) as client,
            client.websocket_connect("/ws") as ws,
        ):
            recv_frame(ws)
            _send(ws, type="song_audio_analyse")
            assert recv_frame(ws)["kind"] == "song_audio_missing"
            _send(ws, type="status_request")
            assert recv_frame(ws)["type"] == "status"


class TestTheCardSurvivesAReload:
    """t316 — 새로고침 한 번에 물음이 사라지지 않는가, **와이어 위에서**.

    실측 결함(2026-09-07, 브라우저): 확인 카드가 뜬 상태에서 앱을 다시 열면
    ``button.question-option`` 이 3 → 0 이 됐다. 화면에는 카드가 없고 서버는
    답을 기다리는 중 — 그 세션은 아무 신호 없이 통째로 막힌다.

    여기서 재는 것은 **재접속이 카드를 되돌리는가**다. 채널 단위 시험
    (``test_web_question_channel.py``) 은 ``bind``/``unbind`` 를 손으로 부르므로
    app.py 의 연결 수명 배선을 지나지 않는다 — 그 배선이 이 시험의 대상이다.

    콘솔 접촉: 0건.
    """

    @staticmethod
    def _await_disconnect(deps) -> None:
        """서버가 끊김을 **처리할 때까지** 기다린다.

        브라우저 새로고침은 벽시계로 그 사이를 벌어 주지만, 테스트에서는 닫자마자
        다음 연결을 연다. 이 대기가 없으면 서버가 아직 옛 소켓을 살아 있다고 읽는
        찰나에 새 연결이 붙어, 뒤이은 이벤트가 죽은 소켓으로 갈 수 있다 —
        시험이 간헐적으로 깨지는 자리다(실측 1회).
        """
        deadline = time.monotonic() + 10.0
        while deps.live_sockets and time.monotonic() < deadline:
            time.sleep(0.01)
        assert not deps.live_sockets, "서버가 끊김을 제때 처리하지 못했다"

    def test_the_card_comes_back_and_is_answerable_on_the_new_connection(self, tmp_path):
        channel = QuestionChannel(timeout_seconds=30.0)
        deps = _deps(tmp_path, question_channel=channel)
        client = TestClient(create_app(deps))
        with client:
            with client.websocket_connect("/ws") as ws:
                recv_frame(ws)  # 최초 status
                _send(
                    ws,
                    type="song_audio_upload",
                    file_name="track.wav",
                    mime_type="audio/wav",
                    content_base64=SMALL_WAV_B64,
                )
                _receive_until(ws, "notice")
                _send(ws, type="song_audio_analyse")
                first_card = _receive_until(ws, "question_request")
                assert first_card["options"], "카드에 선택지가 없으면 잴 것이 없다"
            # 여기서 새로고침이 일어난다 — 위 ``with`` 를 벗어나며 연결이 끊긴다.
            self._await_disconnect(deps)

            with client.websocket_connect("/ws") as ws2:
                restored = _receive_until(ws2, "question_request")
                # 같은 물음이어야 한다 — 같은 id, 같은 문구, 같은 선택지.
                assert restored["request_id"] == first_card["request_id"]
                assert restored["prompt"] == first_card["prompt"]
                assert restored["options"] == first_card["options"]

                # 그리고 되살아난 카드는 실제로 답할 수 있다 — 답이 분석 스레드에
                # 닿아야 확정 알림이 나온다.
                _send(
                    ws2,
                    type="question_answer",
                    request_id=restored["request_id"],
                    answer="BPM 130",
                )
                notice = _receive_until(ws2, "notice")
        assert "130" in notice["message"]
        assert "확정" in notice["message"]

    def test_the_same_card_answered_twice_is_refused(self, tmp_path):
        """중복 답은 거절이다 — 멱등이 아니라.

        옛 탭이 열린 채 새 탭에서 답하는 경우가 실물이다. 두 번째 답을 조용히
        받아들이면 감독은 반영됐다고 읽지만 아무것도 바뀌지 않는다.
        """
        channel = QuestionChannel(timeout_seconds=30.0)
        client = TestClient(create_app(_deps(tmp_path, question_channel=channel)))
        with client, client.websocket_connect("/ws") as ws:
            recv_frame(ws)
            _send(
                ws,
                type="song_audio_upload",
                file_name="track.wav",
                mime_type="audio/wav",
                content_base64=SMALL_WAV_B64,
            )
            _receive_until(ws, "notice")
            _send(ws, type="song_audio_analyse")
            card = _receive_until(ws, "question_request")
            _send(ws, type="question_answer", request_id=card["request_id"], answer="BPM 130")
            _receive_until(ws, "question_resolved")
            _send(ws, type="question_answer", request_id=card["request_id"], answer="BPM 90")
            second = _receive_until(ws, "error")
        assert second["kind"] == "protocol"

    def test_an_already_answered_question_is_not_re_asked_after_a_reload(self, tmp_path):
        """[HARD] 끝난 물음을 되살리면 이미 정해진 것을 다시 묻는다."""
        channel = QuestionChannel(timeout_seconds=30.0)
        deps = _deps(tmp_path, question_channel=channel)
        client = TestClient(create_app(deps))
        with client:
            with client.websocket_connect("/ws") as ws:
                recv_frame(ws)
                _send(
                    ws,
                    type="song_audio_upload",
                    file_name="track.wav",
                    mime_type="audio/wav",
                    content_base64=SMALL_WAV_B64,
                )
                _receive_until(ws, "notice")
                _send(ws, type="song_audio_analyse")
                card = _receive_until(ws, "question_request")
                _send(ws, type="question_answer", request_id=card["request_id"], answer="BPM 130")
                _receive_until(ws, "notice")  # 확정까지 끝났다
            self._await_disconnect(deps)

            with client.websocket_connect("/ws") as ws2:
                # 재접속 뒤 처음 오는 프레임은 status 여야 한다 — 카드가 아니라.
                for _ in range(5):
                    frame = recv_frame(ws2)
                    assert frame["type"] != "question_request", frame
                    if frame["type"] == "status":
                        break


# =============================================================================
# 분할 전송 — AC-MUSICSYNC-026 · AC-MUSICSYNC-027
# =============================================================================
#
# 한 프레임으로는 원리적으로 못 올린다: 31.5MB 의 base64 는 약 42MB 이고
# ``server/web/serve.py`` 의 ``uvicorn.run`` 은 ``ws_max_size`` 를 주지 않아
# 기본 16777216 이 프레임 천장이다. 그래서 곡은 begin · chunk · end 셋으로 온다.

UVICORN_DEFAULT_WS_MAX_SIZE = 16777216
DIRECTOR_SONG_BYTES = 33030144  # 감독 곡 31.5MB 급 — 구 상한 8 MiB 를 넘는다


def _chunks(data: bytes, raw_size: int) -> list[str]:
    return [
        base64.b64encode(data[i : i + raw_size]).decode("ascii")
        for i in range(0, len(data), raw_size)
    ]


def _begin(total, count, **overrides) -> dict:
    return parse_client_message(
        json.dumps(
            {
                "v": PROTOCOL_VERSION,
                "type": "song_audio_upload_begin",
                "file_name": "song.wav",
                "mime_type": "audio/wav",
                "total_bytes": total,
                "chunk_count": count,
                **overrides,
            },
            ensure_ascii=False,
        )
    )


def _chunk(index, content: str) -> dict:
    return parse_client_message(
        json.dumps(
            {
                "v": PROTOCOL_VERSION,
                "type": "song_audio_upload_chunk",
                "index": index,
                "content_base64": content,
            }
        )
    )


def _assemble(data: bytes, raw_size: int) -> dict:
    parts = _chunks(data, raw_size)
    assembly = SongAudioAssembly()
    assembly.begin(_begin(len(data), len(parts)))
    for index, part in enumerate(parts):
        assembly.add(_chunk(index, part))
    return assembly.finish()


class TestTheCapBoundaryIsOpenAtExactlyTheCap:
    """AC-MUSICSYNC-026 — 경계 대조군과 이번 개정이 연 크기."""

    def test_a_declared_total_exactly_at_the_cap_is_accepted(self):
        assert _begin(67108864, 23)["total_bytes"] == 67108864

    def test_a_declared_total_one_byte_over_is_refused_with_both_numbers(self):
        with pytest.raises(SongAudioRejectedError) as caught:
            _begin(67108865, 23)
        reason = str(caught.value)
        assert "64 MiB" in reason and "67108864" in reason
        assert "67108865" in reason  # 받은 크기가 함께 적힌다

    def test_the_director_song_size_now_assembles(self):
        data = b"\x01" * DIRECTOR_SONG_BYTES
        upload = _assemble(data, 3 * 1024 * 1024)
        assert base64.b64decode(upload["content_base64"]) == data
        assert upload["file_name"] == "song.wav"

    def test_the_rejection_reason_carries_no_user_text(self):
        with pytest.raises(SongAudioRejectedError) as caught:
            _begin(67108865, 23, file_name="비밀곡이름.wav")
        assert "비밀곡이름" not in str(caught.value)


class TestChunkedUploadAssembles:
    """AC-MUSICSYNC-027 — 조립 결과가 원본과 바이트 단위로 같다."""

    def test_thirty_mebibytes_assembles_to_the_same_sha256(self):
        data = bytes(range(256)) * (30 * 1024 * 1024 // 256)
        upload = _assemble(data, 3 * 1024 * 1024)
        assembled = base64.b64decode(upload["content_base64"])
        assert len(assembled) == len(data)
        assert hashlib.sha256(assembled).hexdigest() == hashlib.sha256(data).hexdigest()

    def test_the_chunk_ceiling_is_four_mebibytes_of_base64(self):
        assert MAX_SONG_AUDIO_CHUNK_BASE64_LENGTH == 4 * 1024 * 1024

    def test_a_full_size_chunk_frame_fits_under_the_uvicorn_ceiling(self):
        # 조각을 JSON 프레임으로 감싼 **실제 전송 바이트**를 잰다.
        frame = json.dumps(
            {
                "v": PROTOCOL_VERSION,
                "type": "song_audio_upload_chunk",
                "index": 999,
                "content_base64": "A" * MAX_SONG_AUDIO_CHUNK_BASE64_LENGTH,
            }
        )
        assert len(frame.encode("utf-8")) < UVICORN_DEFAULT_WS_MAX_SIZE

    def test_a_chunk_over_the_chunk_ceiling_is_refused(self):
        # [부정 대조군] 상한을 넓혀도 조각 천장은 살아 있다.
        oversized = "A" * (MAX_SONG_AUDIO_CHUNK_BASE64_LENGTH + 4)
        with pytest.raises(SongAudioRejectedError):
            _chunk(0, oversized)


class TestABrokenChunkedUploadStoresNothing:
    """AC-MUSICSYNC-027 부정 대조군 — 깨진 분할은 첨부로 승격되지 않는다."""

    DATA = bytes(range(256)) * 40  # 10240 바이트 → 4096 씩 3 조각

    def _parts(self):
        return _chunks(self.DATA, 4096)

    def test_a_missing_middle_chunk_is_refused_and_the_buffer_is_dropped(self):
        parts = self._parts()
        assembly = SongAudioAssembly()
        assembly.begin(_begin(len(self.DATA), len(parts)))
        assembly.add(_chunk(0, parts[0]))
        with pytest.raises(SongAudioRejectedError):
            assembly.add(_chunk(2, parts[2]))
        assert not assembly.active

    def test_reversed_order_is_refused(self):
        parts = self._parts()
        assembly = SongAudioAssembly()
        assembly.begin(_begin(len(self.DATA), len(parts)))
        with pytest.raises(SongAudioRejectedError):
            assembly.add(_chunk(1, parts[1]))
        assert not assembly.active

    def test_a_total_length_mismatch_is_refused_at_end(self):
        parts = self._parts()
        assembly = SongAudioAssembly()
        assembly.begin(_begin(len(self.DATA) + 1, len(parts)))
        for index, part in enumerate(parts):
            assembly.add(_chunk(index, part))
        with pytest.raises(SongAudioRejectedError):
            assembly.finish()
        assert not assembly.active

    def test_too_few_chunks_is_refused_at_end(self):
        parts = self._parts()
        assembly = SongAudioAssembly()
        assembly.begin(_begin(len(self.DATA), len(parts) + 1))
        for index, part in enumerate(parts):
            assembly.add(_chunk(index, part))
        with pytest.raises(SongAudioRejectedError):
            assembly.finish()

    def test_bytes_past_the_declared_total_are_refused_early(self):
        parts = self._parts()
        assembly = SongAudioAssembly()
        assembly.begin(_begin(5000, len(parts)))
        assembly.add(_chunk(0, parts[0]))
        with pytest.raises(SongAudioRejectedError):
            assembly.add(_chunk(1, parts[1]))

    def test_a_chunk_without_begin_is_refused(self):
        with pytest.raises(SongAudioRejectedError):
            SongAudioAssembly().add(_chunk(0, self._parts()[0]))

    def test_end_without_begin_is_refused(self):
        with pytest.raises(SongAudioRejectedError):
            SongAudioAssembly().finish()

    @pytest.mark.parametrize("bad", [True, -1, "1", 1.0])
    def test_index_must_be_a_real_non_negative_int(self, bad):
        with pytest.raises(SongAudioRejectedError):
            _chunk(bad, "AAAA")

    @pytest.mark.parametrize("total,count", [(True, 1), (0, 1), (10, 0), (10, False), ("10", 1)])
    def test_begin_counts_must_be_positive_ints(self, total, count):
        with pytest.raises(SongAudioRejectedError):
            _begin(total, count)

    def test_begin_checks_extension_like_the_single_frame(self):
        with pytest.raises(SongAudioRejectedError):
            _begin(10, 1, file_name="song.pdf")


class TestTheChunkedUploadTravelsTheWholeWire:
    """AC-MUSICSYNC-013 · 027 — ``app.py`` 의 세 분기를 지우면 이 시험이 실패한다."""

    def _send_chunked(self, ws, parts: list[str], *, total: int):
        _send(
            ws,
            type="song_audio_upload_begin",
            file_name="song.wav",
            mime_type="audio/wav",
            total_bytes=total,
            chunk_count=len(parts),
        )
        for index, part in enumerate(parts):
            _send(ws, type="song_audio_upload_chunk", index=index, content_base64=part)
        _send(ws, type="song_audio_upload_end")

    def test_a_chunked_upload_is_acked_with_the_whole_file_sha256(self, tmp_path):
        parts = _chunks(SMALL_WAV, len(SMALL_WAV) // 3 + 1)
        assert len(parts) == 3
        with (
            TestClient(create_app(_deps(tmp_path))) as client,
            client.websocket_connect("/ws") as ws,
        ):
            recv_frame(ws)
            self._send_chunked(ws, parts, total=len(SMALL_WAV))
            event = _receive_until(ws, "notice")
        assert "song.wav" in event["message"]
        assert SMALL_WAV_SHA256 in event["message"]
        assert str(len(SMALL_WAV)) in event["message"]

    def test_a_broken_chunked_upload_is_refused_and_stores_nothing(self, tmp_path):
        parts = _chunks(SMALL_WAV, len(SMALL_WAV) // 3 + 1)
        with (
            TestClient(create_app(_deps(tmp_path))) as client,
            client.websocket_connect("/ws") as ws,
        ):
            recv_frame(ws)
            self._send_chunked(ws, parts, total=len(SMALL_WAV) + 7)
            error = _receive_until(ws, "error")
            _send(ws, type="song_audio_analyse")
            missing = _receive_until(ws, "error")
        assert error["kind"] == "song_audio_rejected"
        assert any("가" <= ch <= "힣" for ch in error["message"])
        assert missing["kind"] == "song_audio_missing"
