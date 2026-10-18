"""다른 브라우저에서 고른 곡도 서버 보관 음원으로 소리가 나야 한다 — 카드 WT-audio-other-browser.

감독 실측(2026-10-18): 새 곡 「FRESH TEST 1018-3」을 테스트 브라우저에서 올리고 분석했다. 감독이
자기 Chrome 에서 그 곡을 고르고 ▶ 하니 소리가 안 났다. 실제 보관 색인을 읽어 보니 업로드마다
음원이 **그때 열려 있던 앞 곡**의 열쇠에 묶였다(「FRESH TEST 1018-2」 → 1018-3.mp3, 「LOVE ATTACK」
→ FRESH TEST 1018.mp3). 새 곡의 열쇠에는 항목이 없었다. 업로드 시점에는 새 곡 작업본이 아직 없고
분석이 확정돼야 생기기 때문이다. 업로드한 브라우저만 자기 세션에 파일을 들고 있어 소리가 났다.

두 세션이 같은 타임라인 저장소·같은 음원 보관소를 쓰는 것이 같은 서버에 붙은 두 브라우저다.
콘솔 접촉 0건.
"""

from __future__ import annotations

import base64
import hashlib
from datetime import UTC, datetime

from server.design.analysis_timeline import ANALYSIS_SOURCE_KEY
from server.design.profile import resolve_bpm
from server.safety.audit import AuditLog
from server.safety.gate import SafetyGate
from server.web.approval_bridge import ApprovalChannel
from server.web.question import ConfirmedSongAnalysis, ConfirmedSongSection
from server.web.session import ChatSession, SongTimelineStore
from server.web.song_audio_store import SongAudioLinkStore
from server.web.timeline_library import SongTimelineLibrary

from .test_new_analysis_timeline import (
    _SECTIONS,
    _attach_console_groups,
    _bar_map,
    _Console,
    _old_timeline,
    _RefusingProvider,
)

OLD_AUDIO = b"RIFF-old-song-audio"
NEW_AUDIO = b"RIFF-new-song-audio"
OLD_SHA = hashlib.sha256(OLD_AUDIO).hexdigest()
NEW_SHA = hashlib.sha256(NEW_AUDIO).hexdigest()


def _browser(tmp_path, name, timelines, audio_links, sent):
    console = _Console()
    audit = AuditLog(tmp_path / f"audit-{name}")
    channel = ApprovalChannel(timeout_seconds=1.0)
    return ChatSession(
        gate=SafetyGate(console=console, audit=audit, approval_port=channel),
        provider=_RefusingProvider(),
        system_prefix="PREFIX",
        audit=audit,
        send_event=sent.append,
        approval_channel=channel,
        timeline_store=timelines,
        timeline_library=SongTimelineLibrary(tmp_path / f"library-{name}.json"),
        song_audio_link_store=audio_links,
    )


def _server(tmp_path):
    """앞 곡(분석한 곡, 음원 연결 있음)이 열린 서버."""
    timelines = SongTimelineStore()
    old = _old_timeline()
    old[ANALYSIS_SOURCE_KEY] = OLD_SHA
    timelines.latest = old
    audio_links = SongAudioLinkStore()
    audio_links.link(
        (old["song_title"], old["sequence_number"]),
        file_name="OLD SONG.wav",
        mime_type="audio/wav",
        data=OLD_AUDIO,
    )
    return timelines, audio_links


def _upload_and_analyse(session, monkeypatch) -> None:
    """업로드한 브라우저가 새 곡을 올리고 분석을 확정해 새 작업본을 연다."""
    session.upload_song_audio("NEW SONG.wav", "audio/wav", base64.b64encode(NEW_AUDIO).decode())
    audio = session._song_audio
    session._song_analysis = ConfirmedSongAnalysis(
        source_sha256=audio.sha256,
        source_file_name=audio.file_name,
        confirmed_at=datetime.now(UTC).isoformat(),
        bpm=resolve_bpm(measured_bpm=112.0, sheet_bpm=None, fx_rate=None, beats_per_cycle=None),
        sections=tuple(
            ConfirmedSongSection(
                index=index, label=label, start_ms=start, end_ms=end, d_level=level, selected=True
            )
            for index, (label, start, end, level) in enumerate(_SECTIONS)
        ),
    )
    monkeypatch.setattr("server.web.session.synthesize_bar_map", lambda _audio, _offset: _bar_map())
    _attach_console_groups(session)
    session.analyse_bar_map(1)


def _linked_audio(sent: list[dict]) -> bytes | None:
    """다른 브라우저가 받은 음원 바이트 — 한 프레임이든 분할이든 모아서 돌려준다."""
    single = [f for f in sent if f.get("type") == "song_audio_link"]
    if single and single[-1].get("status") == "found":
        return base64.b64decode(single[-1]["content_base64"])
    chunks = [f["content_base64"] for f in sent if f.get("type") == "song_audio_link_chunk"]
    return base64.b64decode("".join(chunks)) if chunks else None


def test_another_browser_gets_the_new_songs_audio_after_the_upload_browser_analysed_it(
    tmp_path, monkeypatch
) -> None:
    timelines, audio_links = _server(tmp_path)
    uploader = _browser(tmp_path, "upload", timelines, audio_links, [])
    _upload_and_analyse(uploader, monkeypatch)
    assert timelines.latest[ANALYSIS_SOURCE_KEY] == NEW_SHA  # 새 곡 작업본이 열렸다

    sent: list[dict] = []
    other = _browser(tmp_path, "other", timelines, audio_links, sent)
    other.request_song_audio_link()
    assert _linked_audio(sent) == NEW_AUDIO


def test_uploading_a_new_song_does_not_overwrite_the_open_songs_audio(
    tmp_path, monkeypatch
) -> None:
    timelines, audio_links = _server(tmp_path)
    old_key = (timelines.latest["song_title"], timelines.latest["sequence_number"])
    uploader = _browser(tmp_path, "upload", timelines, audio_links, [])
    uploader.upload_song_audio("NEW SONG.wav", "audio/wav", base64.b64encode(NEW_AUDIO).decode())
    assert audio_links.resolve(old_key).data == OLD_AUDIO


def test_a_song_whose_link_was_overwritten_still_plays_its_analysed_audio(tmp_path) -> None:
    # 이미 잘못 묶인 기존 기록(앞 곡 열쇠 → 새 곡 음원)이 있어도, 곡의 분석 해시가 가리키는 음원을
    # 준다. 해시로 찾은 음원은 다른 곡 열쇠에 보관돼 있던 바이트다.
    timelines, audio_links = _server(tmp_path)
    old = timelines.latest
    audio_links.link(
        ("SOMETHING ELSE", None), file_name="NEW SONG.wav", mime_type="audio/wav", data=NEW_AUDIO
    )
    audio_links.link(
        (old["song_title"], old["sequence_number"]),
        file_name="NEW SONG.wav",
        mime_type="audio/wav",
        data=NEW_AUDIO,
    )
    audio_links.link(
        ("KEEPER", None), file_name="OLD SONG.wav", mime_type="audio/wav", data=OLD_AUDIO
    )
    sent: list[dict] = []
    _browser(tmp_path, "other", timelines, audio_links, sent).request_song_audio_link()
    assert _linked_audio(sent) == OLD_AUDIO


# -- 이미 잘못 묶인 실제 기록(2026-10-18 보관 색인과 같은 꼴)을 앱이 바로잡는다 -------

LOVE_ATTACK_ORIGINAL = b"ID3-love-attack-original"  # 실기: LOVE ATTACK.mp3, sha 9ab52dfb…
FRESH_1018 = b"ID3-fresh-test-1018"  # 실기: FRESH TEST 1018.mp3 — 제목 태그만 다른 같은 노래


def _real_index_shape() -> SongAudioLinkStore:
    store = SongAudioLinkStore()
    for title in (
        "LOVE ATTACK 손설계+프리셋+TC3 1016 (자동 v2)",
        "LOVE ATTACK 분석 전 백업 (자동 v1)",
    ):
        store.link(
            (title, None),
            file_name="LOVE ATTACK.mp3",
            mime_type="audio/mpeg",
            data=LOVE_ATTACK_ORIGINAL,
        )
    # 「LOVE ATTACK」 열쇠는 다음 곡 업로드에 덮였다.
    store.link(
        ("LOVE ATTACK", None),
        file_name="FRESH TEST 1018.mp3",
        mime_type="audio/mpeg",
        data=FRESH_1018,
    )
    return store


def _love_attack_open() -> SongTimelineStore:
    timelines = SongTimelineStore()
    timelines.latest = {
        "song_title": "LOVE ATTACK",
        "sequence_number": None,
        ANALYSIS_SOURCE_KEY: hashlib.sha256(LOVE_ATTACK_ORIGINAL).hexdigest(),
    }
    return timelines


def test_opening_love_attack_plays_and_rebinds_the_original_audio(tmp_path) -> None:
    links = _real_index_shape()
    sent: list[dict] = []
    _browser(tmp_path, "director", _love_attack_open(), links, sent).request_song_audio_link()
    assert _linked_audio(sent) == LOVE_ATTACK_ORIGINAL
    rebound = links.resolve(("LOVE ATTACK", None))
    assert rebound.data == LOVE_ATTACK_ORIGINAL
    assert rebound.record["file_name"] == "LOVE ATTACK.mp3"
    assert rebound.record["sha256"] == hashlib.sha256(LOVE_ATTACK_ORIGINAL).hexdigest()


def test_reattaching_the_original_in_the_app_binds_it_to_the_open_song(tmp_path) -> None:
    links = SongAudioLinkStore()
    links.link(
        ("LOVE ATTACK", None),
        file_name="FRESH TEST 1018.mp3",
        mime_type="audio/mpeg",
        data=FRESH_1018,
    )
    session = _browser(tmp_path, "director", _love_attack_open(), links, [])
    session.upload_song_audio(
        "LOVE ATTACK.mp3", "audio/mpeg", base64.b64encode(LOVE_ATTACK_ORIGINAL).decode()
    )
    assert links.resolve(("LOVE ATTACK", None)).data == LOVE_ATTACK_ORIGINAL


def test_an_unanalysed_open_song_still_takes_the_upload_as_before(tmp_path) -> None:
    # 분석 해시가 없는 작업본(손 설계 곡)은 예전 그대로 지금 곡에 묶는다 — 곡을 다시 붙이는 경로.
    timelines = SongTimelineStore()
    timelines.latest = {"song_title": "HAND MADE", "sequence_number": 1}
    links = SongAudioLinkStore()
    session = _browser(tmp_path, "director", timelines, links, [])
    session.upload_song_audio("HAND.wav", "audio/wav", base64.b64encode(NEW_AUDIO).decode())
    assert links.resolve(("HAND MADE", 1)).data == NEW_AUDIO
