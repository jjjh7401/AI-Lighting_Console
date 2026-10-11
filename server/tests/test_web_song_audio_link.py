"""곡별 영구 오디오 링크 — 세션·WS 왕복 (카드 t571, SPEC-LDBEAT-001 REQ-LDBEAT-024(c) 후속).

``server/web/song_audio_store.py`` 는 바이트 저장소 자체를 재는
``test_song_audio_link_store.py`` 가 판정한다. 이 파일이 재는 것은 그
저장소가 ``ChatSession``/``server/web/app.py`` 와 실제로 어떻게 엮이는가다 —
``test_web_song_audio.py`` 가 업로드 경로에 세운 것과 같은 두 켜(검증/보관
층은 거기서 이미 다룬다, 여기서는 디스패치 층 + 보관 연동만):

1. ``upload_song_audio`` 가 **지금 곡을 알 때만** 영구 링크를 쓴다
   (``_current_song_audio_key``).
2. ``song_audio_link_request`` 가 ``server/web/app.py`` 의 디스패치 분기를
   실제로 지나 ``session.request_song_audio_link`` 까지 닿는다
   (``song_audio_upload`` 분기 누락 사고의 재발 방지와 같은 이유 —
   ``app.py`` 주석 참조).
3. 큰 파일은 역방향 분할 트리오로 나간다.

콘솔 접촉: 0건. ``FakeConsole`` 만 쓴다.
"""

from __future__ import annotations

import base64
import hashlib
import json

from fastapi.testclient import TestClient

from server.safety.audit import AuditLog
from server.safety.gate import SafetyGate
from server.web.app import WebDeps, create_app
from server.web.approval_bridge import ApprovalChannel
from server.web.messages import MAX_SONG_AUDIO_CHUNK_BASE64_LENGTH, PROTOCOL_VERSION
from server.web.session import ChatSession, SongTimelineStore
from server.web.song_audio_store import SongAudioLinkStore

from .conftest import drain_until as _receive_until
from .conftest import recv_frame
from .fixtures.audio import synthesize_track
from .test_runner_self_correction import ScriptedProvider
from .test_safety_gate import FakeConsole

SMALL_WAV = synthesize_track(duration_ms=3000)
SMALL_WAV_B64 = base64.b64encode(SMALL_WAV).decode("ascii")
SMALL_WAV_SHA256 = hashlib.sha256(SMALL_WAV).hexdigest()

_TIMELINE = {"song_title": "Sugar", "sequence_number": 3}
_OTHER_TIMELINE = {"song_title": "Chandelier", "sequence_number": 7}


def _deps(tmp_path, *, timeline: dict | None = None):
    console = FakeConsole()
    audit = AuditLog(tmp_path / "audit")
    channel = ApprovalChannel(timeout_seconds=2.0)
    gate = SafetyGate(console=console, audit=audit, approval_port=channel)
    timeline_store = SongTimelineStore()
    if timeline is not None:
        timeline_store.latest = timeline
    return WebDeps(
        gate=gate,
        provider=ScriptedProvider([]),
        system_prefix="PREFIX",
        audit=audit,
        approval_channel=channel,
        song_timeline_store=timeline_store,
        song_audio_link_store=SongAudioLinkStore(),
    )


def _session(tmp_path, *, timeline: dict | None = None, song_audio_link_store=None, events=None):
    deps = _deps(tmp_path, timeline=timeline)
    sink = events if events is not None else []
    return ChatSession(
        gate=deps.gate,
        provider=deps.provider,
        system_prefix="PREFIX",
        audit=deps.audit,
        send_event=sink.append,
        approval_channel=deps.approval_channel,
        timeline_store=deps.song_timeline_store,
        song_audio_link_store=(
            song_audio_link_store
            if song_audio_link_store is not None
            else deps.song_audio_link_store
        ),
    )


def _send(ws, **fields):
    ws.send_text(json.dumps({"v": PROTOCOL_VERSION, **fields}, ensure_ascii=False))


# =============================================================================
# 보관 연동 — upload_song_audio 가 영구 링크를 쓰는가 (session.py)
# =============================================================================


class TestUploadPersistsOnlyWhenTheCurrentSongIsKnown:
    def test_a_known_song_persists_the_link(self, tmp_path):
        store = SongAudioLinkStore()
        session = _session(tmp_path, timeline=_TIMELINE, song_audio_link_store=store)
        session.upload_song_audio("track.wav", "audio/wav", SMALL_WAV_B64)
        key = (_TIMELINE["song_title"], _TIMELINE["sequence_number"])
        result = store.resolve(key)
        assert result.status == "found"
        assert result.data == SMALL_WAV
        assert result.record["sha256"] == SMALL_WAV_SHA256

    def test_an_unknown_song_leaves_the_store_untouched(self, tmp_path):
        store = SongAudioLinkStore()
        session = _session(tmp_path, timeline=None, song_audio_link_store=store)
        session.upload_song_audio("track.wav", "audio/wav", SMALL_WAV_B64)
        # 대조군(위 시험)이 "저장은 된다"를 이미 보였으니, 여기서 store 가
        # 비어 있다는 것은 "곡을 몰라서 안 썼다"지 저장소 자체가 공허해서가
        # 아니다.
        assert store._entries == []  # noqa: SLF001 — 의도적으로 내부를 본다(아무것도 안 썼다는 확인)

    def test_the_session_attachment_still_happens_without_a_known_song(self, tmp_path):
        # 영구 링크가 비어도 이번 세션의 첨부·분석 경로는 오늘과 똑같이 산다.
        session = _session(tmp_path, timeline=None)
        session.upload_song_audio("track.wav", "audio/wav", SMALL_WAV_B64)
        assert session.song_audio is not None
        assert session.song_audio.sha256 == SMALL_WAV_SHA256

    def test_a_second_upload_for_the_same_song_replaces_the_link(self, tmp_path):
        store = SongAudioLinkStore()
        session = _session(tmp_path, timeline=_TIMELINE, song_audio_link_store=store)
        session.upload_song_audio("first.wav", "audio/wav", SMALL_WAV_B64)
        other = synthesize_track(duration_ms=2000)
        session.upload_song_audio(
            "second.wav", "audio/wav", base64.b64encode(other).decode("ascii")
        )
        key = (_TIMELINE["song_title"], _TIMELINE["sequence_number"])
        result = store.resolve(key)
        assert result.record["file_name"] == "second.wav"
        assert result.data == other


# =============================================================================
# 요청 경로 — request_song_audio_link (session.py)
# =============================================================================


class TestRequestSongAudioLink:
    def test_an_unknown_song_answers_none(self, tmp_path):
        events: list[dict] = []
        session = _session(tmp_path, timeline=None, events=events)
        outcome = session.request_song_audio_link()
        assert outcome == {"status": "none"}
        assert events[-1] == {
            "v": PROTOCOL_VERSION,
            "type": "song_audio_link",
            "status": "none",
            "file_name": None,
            "mime_type": None,
            "content_base64": None,
            "sha256": None,
            "byte_length": None,
        }

    def test_a_song_with_no_saved_link_answers_none(self, tmp_path):
        events: list[dict] = []
        session = _session(tmp_path, timeline=_TIMELINE, events=events)
        outcome = session.request_song_audio_link()
        assert outcome == {"status": "none"}
        assert events[-1]["status"] == "none"

    def test_a_small_found_link_answers_in_one_frame(self, tmp_path):
        store = SongAudioLinkStore()
        key = (_TIMELINE["song_title"], _TIMELINE["sequence_number"])
        store.link(key, file_name="track.wav", mime_type="audio/wav", data=SMALL_WAV)
        events: list[dict] = []
        session = _session(tmp_path, timeline=_TIMELINE, song_audio_link_store=store, events=events)
        outcome = session.request_song_audio_link()
        assert outcome == {"status": "found", "chunked": False}
        assert len(events) == 1
        event = events[0]
        assert event["type"] == "song_audio_link"
        assert event["status"] == "found"
        assert event["file_name"] == "track.wav"
        assert event["mime_type"] == "audio/wav"
        assert event["sha256"] == SMALL_WAV_SHA256
        assert event["byte_length"] == len(SMALL_WAV)
        assert base64.b64decode(event["content_base64"]) == SMALL_WAV

    def test_a_missing_link_answers_missing_with_no_content(self, tmp_path):
        store = SongAudioLinkStore()
        key = (_TIMELINE["song_title"], _TIMELINE["sequence_number"])
        store.link(key, file_name="track.wav", mime_type="audio/wav", data=SMALL_WAV)
        # 저장소가 가리키는 파일을 지운다(메모리 모드라 블롭 딕셔너리를
        # 직접 비운다 — ``test_song_audio_link_store.py`` 가 디스크 모드의
        # 같은 결함을 재지만, 여기서는 세션 연동이 그 상태를 그대로
        # 전달하는지만 본다).
        store._memory_blobs.clear()  # noqa: SLF001 — 의도적으로 손상을 흉내낸다
        events: list[dict] = []
        session = _session(tmp_path, timeline=_TIMELINE, song_audio_link_store=store, events=events)
        outcome = session.request_song_audio_link()
        assert outcome == {"status": "missing"}
        assert events[-1]["status"] == "missing"
        assert events[-1]["content_base64"] is None

    def test_different_songs_get_their_own_answer(self, tmp_path):
        store = SongAudioLinkStore()
        store.link(
            (_TIMELINE["song_title"], _TIMELINE["sequence_number"]),
            file_name="a.wav",
            mime_type="audio/wav",
            data=SMALL_WAV,
        )
        events: list[dict] = []
        session = _session(
            tmp_path, timeline=_OTHER_TIMELINE, song_audio_link_store=store, events=events
        )
        outcome = session.request_song_audio_link()
        assert outcome == {"status": "none"}  # 저 곡엔 아무것도 링크되지 않았다


class TestRequestSongAudioLinkChunksLargePayloads:
    """역방향 분할 — base64 가 ``MAX_SONG_AUDIO_CHUNK_BASE64_LENGTH`` 를 넘으면
    begin/chunk*/end 트리오가 나간다(REQ-MUSICSYNC-027 과 같은 이유의 반대쪽)."""

    def _linked_large_session(self, tmp_path, *, raw_byte_length: int):
        # base64 는 원본의 약 4/3 — 상한을 넘기려면 그만큼 큰 원본이 필요하다.
        data = (b"\x00\x01\x02\x03" * ((raw_byte_length // 4) + 1))[:raw_byte_length]
        store = SongAudioLinkStore()
        key = (_TIMELINE["song_title"], _TIMELINE["sequence_number"])
        store.link(key, file_name="big.wav", mime_type="audio/wav", data=data)
        events: list[dict] = []
        session = _session(tmp_path, timeline=_TIMELINE, song_audio_link_store=store, events=events)
        return session, events, data

    def test_a_payload_over_the_chunk_threshold_is_sent_as_a_trio(self, tmp_path):
        # base64 길이가 상한을 넘도록: 원본 바이트 ≈ 상한 * 3/4 + 여유.
        raw_len = (MAX_SONG_AUDIO_CHUNK_BASE64_LENGTH * 3 // 4) + 1024
        session, events, data = self._linked_large_session(tmp_path, raw_byte_length=raw_len)
        outcome = session.request_song_audio_link()
        assert outcome == {"status": "found", "chunked": True}
        assert events[0]["type"] == "song_audio_link_begin"
        assert events[0]["status"] == "found"
        assert events[0]["byte_length"] == len(data)
        assert events[-1] == {
            "v": PROTOCOL_VERSION,
            "type": "song_audio_link_end",
        }
        chunk_events = events[1:-1]
        assert len(chunk_events) == events[0]["chunk_count"]
        assert all(event["type"] == "song_audio_link_chunk" for event in chunk_events)
        assert [event["index"] for event in chunk_events] == list(range(len(chunk_events)))
        reassembled_b64 = "".join(event["content_base64"] for event in chunk_events)
        assert base64.b64decode(reassembled_b64) == data
        assert base64.b64decode(reassembled_b64) == data

    def test_a_payload_exactly_at_the_threshold_is_not_chunked(self, tmp_path):
        # 경계 대조군 — 상한 그대로면 단일 프레임이어야 한다(위 시험이
        # "크면 항상 쪼갠다"는 공허한 판정이 아님을 보장).
        store = SongAudioLinkStore()
        key = (_TIMELINE["song_title"], _TIMELINE["sequence_number"])
        # base64 길이가 정확히 상한이 되도록 원본 길이를 역산한다
        # (base64 는 3바이트 → 4문자, 상한은 4의 배수로 정의돼 있다).
        raw_len = (MAX_SONG_AUDIO_CHUNK_BASE64_LENGTH // 4) * 3
        data = (b"\x00\x01\x02\x03" * ((raw_len // 4) + 1))[:raw_len]
        encoded_len = len(base64.b64encode(data))
        assert encoded_len == MAX_SONG_AUDIO_CHUNK_BASE64_LENGTH, encoded_len
        store.link(key, file_name="exact.wav", mime_type="audio/wav", data=data)
        events: list[dict] = []
        session = _session(tmp_path, timeline=_TIMELINE, song_audio_link_store=store, events=events)
        outcome = session.request_song_audio_link()
        assert outcome == {"status": "found", "chunked": False}
        assert len(events) == 1


# =============================================================================
# 디스패치 층 — server/web/app.py 가 song_audio_link_request 를 실제로 받는가
# =============================================================================


class TestTheRequestTravelsTheWholeWireNotJustTheSessionMethod:
    """``song_audio_upload`` 분기 누락 사고(``app.py`` 주석)의 재발 방지와
    같은 이유 — 이 분기를 지우면 이 시험들은 프레임이 파싱은 되지만 응답이
    오지 않아 ``recv_frame``이 시간 상한에서 끊긴다."""

    def test_a_link_request_is_answered_over_the_wire(self, tmp_path):
        with (
            TestClient(create_app(_deps(tmp_path, timeline=_TIMELINE))) as client,
            client.websocket_connect("/ws") as ws,
        ):
            recv_frame(ws)  # 최초 status
            recv_frame(ws)  # 타임라인이 미리 심어져 있으면 접속 때 song_timeline 도 온다
            _send(ws, type="song_audio_link_request")
            event = recv_frame(ws)
        assert event["type"] == "song_audio_link"
        assert event["status"] == "none"  # 아직 아무것도 안 올렸다

    def test_an_uploaded_song_is_findable_through_a_later_request_on_the_same_connection(
        self, tmp_path
    ):
        with (
            TestClient(create_app(_deps(tmp_path, timeline=_TIMELINE))) as client,
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
            _receive_until(ws, "notice")
            _send(ws, type="song_audio_link_request")
            event = _receive_until(ws, "song_audio_link")
        assert event["status"] == "found"
        assert event["sha256"] == SMALL_WAV_SHA256
        assert base64.b64decode(event["content_base64"]) == SMALL_WAV

    def test_the_link_survives_a_brand_new_websocket_connection(self, tmp_path):
        # 저장소는 WebDeps 수준에서 프로세스 전체가 공유한다 — 연결 하나가
        # 올린 오디오를 **새** 연결(새 ChatSession)이 요청으로 찾아낸다.
        # (디스크 재시작 생존 자체는 store 단위 시험이 이미 쟀다 — 여기서는
        # "연결이 바뀌어도 ChatSession 이 같은 저장소를 본다"만 잰다.)
        deps = _deps(tmp_path, timeline=_TIMELINE)
        app = create_app(deps)
        with TestClient(app) as client:
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
            with client.websocket_connect("/ws") as ws:
                recv_frame(ws)
                _send(ws, type="song_audio_link_request")
                event = _receive_until(ws, "song_audio_link")
        assert event["status"] == "found"
        assert event["sha256"] == SMALL_WAV_SHA256

    def test_a_connection_with_no_known_song_gets_a_quiet_none(self, tmp_path):
        with (
            TestClient(create_app(_deps(tmp_path, timeline=None))) as client,
            client.websocket_connect("/ws") as ws,
        ):
            recv_frame(ws)
            _send(ws, type="song_audio_link_request")
            event = recv_frame(ws)
        assert event["type"] == "song_audio_link"
        assert event["status"] == "none"

    def test_the_connection_survives_a_missing_link_response(self, tmp_path):
        # 응답 뒤에도 연결이 멀쩡해야 한다 — 다음 프레임도 받을 수 있다.
        with (
            TestClient(create_app(_deps(tmp_path, timeline=_TIMELINE))) as client,
            client.websocket_connect("/ws") as ws,
        ):
            recv_frame(ws)
            recv_frame(ws)  # 타임라인이 미리 심어져 있으면 접속 때 song_timeline 도 온다
            _send(ws, type="song_audio_link_request")
            assert recv_frame(ws)["type"] == "song_audio_link"
            _send(ws, type="status_request")
            assert recv_frame(ws)["type"] == "status"
