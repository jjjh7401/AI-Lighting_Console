"""M2 — 마디 지도 진입 경로, 세션 메서드 (SPEC-LDBARMAP-002, 카드 t647).

``ChatSession.analyse_bar_map`` 만 다룬다. 합성 단계(``synthesize_bar_map``) 자체는
``test_audio_bar_map_entry.py``, 와이어 프레임은 M3 의 몫이다.

재는 지점은 반환값이 아니라 **연결이 주입한 송신 콜백이 받은 프레임**이다(AC-LDBARENTRY-015).
저장 관문의 거절 경로는 이벤트를 반환만 하고 보내지 않기 때문이다(``session.py``
``store_timeline_bar_map``). 그래서 모든 시험이 프레임 종류의 순서까지 단언한다.

실제 분석은 시험 안에서 합성한 클릭 트랙에만 돌린다 — 저장소에 오디오 파일을 두지 않는다
(REQ-LDBARENTRY-016). 한 시험은 실제 분석을 많아야 두 번 돈다(``faulthandler_timeout`` 이
60 초를 넘는 시험을 프로세스째 끊는다). 나머지는 단계 대역으로 돈다.

콘솔 접촉: 0건 — 콘솔 대역이 받은 호출 수를 직접 센다.
"""

from __future__ import annotations

import base64
import copy
import io
from pathlib import Path
from typing import NamedTuple

import pytest

from server.audio.analyze import MANUAL_BPM_FALLBACK_REASON, analysis_available
from server.audio.bar_map import (
    BarFeaturesFailure,
    BeatGridFailure,
    BeatGridResult,
    BpmCandidateCheck,
    derive_bars,
    detect_beat_grid,
    extract_bar_features,
)
from server.audio.bar_map_entry import BarMapEntryFailure
from server.audio.bar_map_store import BAR_MAP_KEY, build_bar_map_payload, validate_bar_map
from server.design.beat_grid_send import build_song_timing_from_bar_map
from server.safety.audit import AuditLog
from server.safety.console import ExecOutcome
from server.safety.gate import SafetyGate
from server.web.approval_bridge import ApprovalChannel
from server.web.session import (
    _BAR_MAP_ENTRY_REJECTED_SUMMARY,
    ChatSession,
    SongAudioUpload,
    SongTimelineStore,
)
from server.web.timeline_library import SongTimelineLibrary

#: 실제 오디오 분석(librosa)이 필요한 시험에만 건다 — 단계 대역으로 도는 시험은 어디서나 돈다.
requires_analysis = pytest.mark.skipif(
    not analysis_available(),
    reason="librosa 미설치 — 폴백 경로는 test_audio_fallback.py 가 판정한다",
)

#: 성공의 요약 라벨은 저장 관문이 정한다(``store_timeline_bar_map``) — 진입 경로가 바꾸지 않는다.
SUCCESS_SUMMARY = "마디 지도 저장"

#: hop_length(512)가 박 간격을 정확히 나누는 표본율 — 이 BPM 에서 박 하나가 정확히 30 프레임이다
#: (test_audio_bar_map_entry.py 의 같은 상수 주석 참조).
_CLICK_TRACK_SAMPLE_RATE = 24 * 1024
_CLICK_TRACK_BPM = 96.0
_CLICK_TRACK_DURATION_SEC = 30.0


def _click_track(duration_sec: float) -> bytes:
    """알려진 BPM 의 클릭 트랙을 numpy 로 합성해 WAV 바이트열로 돌려준다.

    test_audio_bar_map_entry.py 의 생성기와 같은 식이다(비공개 헬퍼는 가져오지 않고
    의도적으로 다시 둔다)."""
    import numpy as np
    import soundfile as sf

    sample_rate = _CLICK_TRACK_SAMPLE_RATE
    beat_sec = 60.0 / _CLICK_TRACK_BPM
    n_samples = int(sample_rate * duration_sec)
    y = np.zeros(n_samples, dtype=np.float32)
    click_len = int(0.02 * sample_rate)
    t_click = np.arange(click_len) / sample_rate
    click = np.sin(2 * np.pi * 1200 * t_click) * np.exp(-t_click / 0.005)
    for i in range(int(duration_sec / beat_sec)):
        start = int(round(i * beat_sec * sample_rate))
        end = min(start + click_len, n_samples)
        y[start:end] += click[: end - start]
    buf = io.BytesIO()
    sf.write(buf, y, sample_rate, format="WAV", subtype="PCM_16")
    return buf.getvalue()


@pytest.fixture(scope="module")
def click_track() -> bytes:
    return _click_track(_CLICK_TRACK_DURATION_SEC)


# ---------------------------------------------------------------------------
# 시험 틀 — test_session_bar_map_store.py 와 같은 모양(그 파일에서 가져오지 않고 다시 둔다).
# ---------------------------------------------------------------------------


class _ConsoleStub:
    """콘솔 포트 대역 — 불린 모든 호출을 ``calls`` 에 기록한다. 이 경로에서는 0건이어야 한다."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, ...]] = []

    def execute(self, command: str) -> ExecOutcome:
        self.calls.append(("execute", command))
        return ExecOutcome(status="ok", detail="OK")

    def ping(self) -> bool:
        self.calls.append(("ping",))
        return True

    def query_state(self, path: str) -> dict:
        self.calls.append(("query_state", path))
        return {}


class _RefusingProvider:
    """모델을 부르면 시험이 깨진다 — 이 경로는 제공자 없이 동작해야 한다."""

    def complete(self, *args, **kwargs):  # pragma: no cover - 불려선 안 된다
        raise AssertionError("이 경로는 모델을 부르지 않는다")


class _Harness(NamedTuple):
    session: ChatSession
    console: _ConsoleStub
    store: SongTimelineStore
    sent: list[dict]
    library_path: Path


class _Snapshot(NamedTuple):
    timeline: dict | None
    depth: int


def _timeline(**overrides: object) -> dict:
    base = {"song_title": "TEST SONG", "sequence_number": 1}
    base.update(overrides)
    return base


def _make_harness(
    tmp_path: Path, *, with_timeline: bool = True, audio: bytes | None = None
) -> _Harness:
    """세션 하나와 그 곁의 기록 장치들. ``audio`` 가 있으면 ``upload_song_audio`` 로 첨부한다.

    첨부는 지시문 없이 보관만 하고 안내 프레임(``notice``)을 보낸다 — 시험이 재는 것은 진입
    메서드가 보낸 프레임이므로 첨부 직후 송신 기록을 비운다."""
    store = SongTimelineStore()
    if with_timeline:
        store.latest = _timeline()
    sent: list[dict] = []
    console = _ConsoleStub()
    audit = AuditLog(tmp_path / "audit")
    channel = ApprovalChannel(timeout_seconds=1.0)
    gate = SafetyGate(console=console, audit=audit, approval_port=channel)
    library_path = tmp_path / "library.json"
    session = ChatSession(
        gate=gate,
        provider=_RefusingProvider(),
        system_prefix="PREFIX",
        audit=audit,
        send_event=sent.append,
        approval_channel=channel,
        timeline_store=store,
        timeline_library=SongTimelineLibrary(library_path),
    )
    if audio is not None:
        session.upload_song_audio("test.wav", "audio/wav", base64.b64encode(audio).decode("ascii"))
        sent.clear()
    return _Harness(session, console, store, sent, library_path)


def _snapshot(h: _Harness) -> _Snapshot:
    return _Snapshot(copy.deepcopy(h.store.latest), h.session._draft_history.depth)


def _types(sent: list[dict]) -> list[str]:
    return [frame["type"] for frame in sent]


def _without(timeline: dict, *keys: str) -> dict:
    return {k: v for k, v in timeline.items() if k not in keys}


def _assert_rejected_and_untouched(h: _Harness, before: _Snapshot, *, reason: str) -> dict:
    """성공이 아닌 결과의 공통 조건 — 프레임은 ``chat_response`` 하나뿐이고, 타임라인·되돌리기
    깊이·콘솔 모두 호출 전과 같다. 그 ``chat_response`` 를 돌려준다."""
    assert _types(h.sent) == ["chat_response"], h.sent
    [response] = h.sent
    assert response["status"] == "ok"
    assert response["summary"] == _BAR_MAP_ENTRY_REJECTED_SUMMARY
    assert reason in response["text"], response["text"]
    assert h.store.latest == before.timeline
    assert h.session._draft_history.depth == before.depth
    assert h.console.calls == []
    return response


class _Step:
    """분석 단계 대역 — 호출 인자를 ``calls`` 에 기록하고 정해 둔 값을 돌려준다."""

    def __init__(self, result: object) -> None:
        self.result = result
        self.calls: list[tuple] = []

    def __call__(self, *args: object) -> object:
        self.calls.append(args)
        return self.result


def _fake_grid(
    *,
    outcome: str = "keep",
    raw_bpm: float = 96.0,
    bpm: float | None = None,
    step_ms: int = 625,
    beat_count: int = 24,
) -> BeatGridResult:
    """검출 결과 대역 — 오디오 없이 만든 박 격자. ``bpm`` 은 검출기의 최종 BPM(채택값)이다."""
    adopted = raw_bpm if bpm is None else bpm
    check = BpmCandidateCheck(
        raw_bpm=raw_bpm,
        half_bpm=raw_bpm / 2.0,
        double_bpm=raw_bpm * 2.0,
        n_pairs=20,
        w_mid=0.1,
        p_mid=0.001,
        w_odd=0.5,
        p_two=1.0,
        outcome=outcome,
        ambiguous=False,
        adopted_bpm=adopted,
        rationale="시험용 대역",
    )
    return BeatGridResult(
        beat_times_ms=tuple(500 + i * step_ms for i in range(beat_count)),
        bpm=adopted,
        bpm_confidence=1.0,
        bpm_check=check,
    )


def _valid_payload() -> dict:
    """저장 관문을 통과하는 작은 마디 지도 — 합성 단계를 대역으로 바꿀 때 돌려준다."""
    beats = list(range(0, 3 * 4 * 500, 500))
    return build_bar_map_payload(beats, 0, bpm=120.0, time_signature=(4, 4))


# ---------------------------------------------------------------------------
# AC-LDBARENTRY-003 — 싼 점검은 디코드 전에: 범위 밖 오프셋, 타임라인 없음.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad_offset", [-1, 4, 99])
def test_ac003_out_of_range_offset_is_refused_before_the_detector(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, bad_offset: int
) -> None:
    detector = _Step(BeatGridFailure("대역 사유"))
    monkeypatch.setattr("server.audio.bar_map_entry.detect_beat_grid", detector)
    h = _make_harness(tmp_path, audio=b"not decoded")
    before = _snapshot(h)

    h.session.analyse_bar_map(bad_offset)

    _assert_rejected_and_untouched(h, before, reason="0~3")
    assert detector.calls == []


def test_ac003_control_a_valid_offset_does_reach_the_detector(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """대조군 — 대역 바꿔 끼우기가 실제로 이어져 있어야 위의 「불리지 않았다」가 공허하지 않다."""
    detector = _Step(BeatGridFailure("대역 사유"))
    monkeypatch.setattr("server.audio.bar_map_entry.detect_beat_grid", detector)
    h = _make_harness(tmp_path, audio=b"not decoded")
    before = _snapshot(h)

    h.session.analyse_bar_map(0)

    assert len(detector.calls) == 1
    _assert_rejected_and_untouched(h, before, reason="대역 사유")


def test_ac003_missing_timeline_is_refused_before_the_detector(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    detector = _Step(BeatGridFailure("대역 사유"))
    monkeypatch.setattr("server.audio.bar_map_entry.detect_beat_grid", detector)
    h = _make_harness(tmp_path, with_timeline=False, audio=b"not decoded")
    before = _snapshot(h)
    assert before.timeline is None

    h.session.analyse_bar_map(0)

    _assert_rejected_and_untouched(h, before, reason="초안 타임라인이 아직 없습니다")
    assert detector.calls == []
    assert h.store.latest is None


# ---------------------------------------------------------------------------
# AC-LDBARENTRY-004 — 정상 경로: 저장·읽기·이벤트·깊이 (실제 분석).
# ---------------------------------------------------------------------------


@requires_analysis
def test_ac004_success_saves_reads_back_and_pushes_one_timeline(
    tmp_path: Path, click_track: bytes
) -> None:
    h = _make_harness(tmp_path, audio=click_track)
    before = _snapshot(h)
    assert before.depth == 0

    h.session.analyse_bar_map(0)

    # 실패하면 무슨 응답이 나갔는지 보이도록 프레임 전체를 메시지로 싣는다.
    assert _types(h.sent) == ["song_timeline", "chat_response"], h.sent
    saved = h.session.timeline_bar_map()
    assert saved is not None  # (1)
    assert saved == h.store.latest[BAR_MAP_KEY]  # (1)
    assert validate_bar_map(saved) is None  # (2)
    assert abs(saved["bpm"] - _CLICK_TRACK_BPM) / _CLICK_TRACK_BPM <= 0.01  # (3)
    assert h.session._draft_history.depth == before.depth + 1  # (4)
    # (5) 저장 관문이 얹는 「수정됨」 표식(draft)과 마디 지도 말고는 호출 전과 같다.
    assert _without(h.store.latest, BAR_MAP_KEY, "draft") == _without(
        before.timeline, BAR_MAP_KEY, "draft"
    )
    # (6)
    [pushed] = [f["timeline"] for f in h.sent if f["type"] == "song_timeline"]
    assert BAR_MAP_KEY in pushed
    [response] = [f for f in h.sent if f["type"] == "chat_response"]
    assert response["status"] == "ok"
    assert response["summary"] == SUCCESS_SUMMARY
    assert h.console.calls == []


# ---------------------------------------------------------------------------
# AC-LDBARENTRY-006 — 분석 실패는 타임라인을 건드리지 않는다.
# ---------------------------------------------------------------------------


def test_ac006_a_non_audio_bytes_report_the_detectors_own_reason(tmp_path: Path) -> None:
    bad_audio = b"not audio"
    expected = detect_beat_grid(bad_audio)
    assert isinstance(expected, BeatGridFailure)
    # 디코더의 사유는 예외 문구를 끼운다 — ``Error opening <_io.BytesIO object at 0x…>`` 처럼 호출마다
    # 달라지는 객체 주소가 든다. 같은 바이트열에 두 번 부른 사유가 글자까지 같다고 기대하지 않고,
    # 예외 문구 앞의 고정된 부분(단계가 붙인 말)을 대조한다.
    stable_reason = expected.reason.split(": ", 1)[0]
    h = _make_harness(tmp_path, audio=bad_audio)
    before = _snapshot(h)

    h.session.analyse_bar_map(0)

    _assert_rejected_and_untouched(h, before, reason=stable_reason)


@requires_analysis
def test_ac006_b_audio_shorter_than_two_seconds_reports_the_detectors_own_reason(
    tmp_path: Path,
) -> None:
    short_audio = _click_track(1.0)
    expected = detect_beat_grid(short_audio)
    assert isinstance(expected, BeatGridFailure)
    assert "너무 짧습니다" in expected.reason  # 의도한 실패 단계인지 못박는다
    h = _make_harness(tmp_path, audio=short_audio)
    before = _snapshot(h)

    h.session.analyse_bar_map(0)

    _assert_rejected_and_untouched(h, before, reason=expected.reason)


def test_ac006_c_analysis_unavailable_reports_the_fallback_reason(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """검출기가 부르는 ``analysis_available`` 은 ``server.audio.bar_map`` 의 이름이다. 그 이름을
    거짓으로 바꾸면 어떤 바이트열이든 디코드 전에 폴백 사유로 거절된다."""
    monkeypatch.setattr("server.audio.bar_map.analysis_available", lambda: False)
    h = _make_harness(tmp_path, audio=b"not decoded")
    before = _snapshot(h)

    h.session.analyse_bar_map(0)

    _assert_rejected_and_untouched(h, before, reason=MANUAL_BPM_FALLBACK_REASON)


def test_ac006_d_too_few_beats_report_the_feature_extractors_own_reason(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """박이 3개뿐이면 마디 경계가 2개 미만이다 — 실제 추출 함수가 디코드 전에 스스로 거절한다."""
    grid = _fake_grid(beat_count=3)
    bars = derive_bars(grid.beat_times_ms, 0)
    expected = extract_bar_features(b"unused", bars.bar_boundaries_ms)
    assert isinstance(expected, BarFeaturesFailure)
    monkeypatch.setattr("server.audio.bar_map_entry.detect_beat_grid", _Step(grid))
    h = _make_harness(tmp_path, audio=b"not decoded")
    before = _snapshot(h)

    h.session.analyse_bar_map(0)

    _assert_rejected_and_untouched(h, before, reason=expected.reason)


# ---------------------------------------------------------------------------
# AC-LDBARENTRY-007 (세션 쪽) — 두 배 BPM 채택은 저장하지 않는다.
# ---------------------------------------------------------------------------


def test_ac007_adopt_double_is_refused_with_the_reason_in_the_body(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    grid = _fake_grid(outcome="adopt_double", raw_bpm=96.0, bpm=192.0)
    detector = _Step(grid)
    monkeypatch.setattr("server.audio.bar_map_entry.detect_beat_grid", detector)
    h = _make_harness(tmp_path, audio=b"not decoded")
    before = _snapshot(h)

    h.session.analyse_bar_map(0)

    assert len(detector.calls) == 1  # 거절은 검출 뒤에 나온다 — 대역이 실제로 쓰였다
    response = _assert_rejected_and_untouched(h, before, reason="두 배")
    assert response["status"] == "ok"  # 실패용 새 상태값이 아니다(E2)
    assert h.session.timeline_bar_map() is None
    assert BAR_MAP_KEY not in h.store.latest


# ---------------------------------------------------------------------------
# AC-LDBARENTRY-008 — 분석 중 타임라인이 바뀌면 저장하지 않는다.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("replacement", ["other_song", "none"])
def test_ac008_song_changed_during_analysis_is_not_saved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, replacement: str
) -> None:
    h = _make_harness(tmp_path, audio=b"not decoded")
    other = _timeline(song_title="OTHER SONG", sequence_number=2)
    payload = _valid_payload()
    calls: list[tuple] = []

    def swap_then_return(audio_bytes: bytes, first_beat_offset: int) -> dict:
        calls.append((audio_bytes, first_beat_offset))
        h.store.latest = copy.deepcopy(other) if replacement == "other_song" else None
        return payload

    monkeypatch.setattr("server.web.session.synthesize_bar_map", swap_then_return)
    depth_before = h.session._draft_history.depth

    h.session.analyse_bar_map(0)

    assert len(calls) == 1  # 합성 대역이 실제로 쓰였다
    assert _types(h.sent) == ["chat_response"], h.sent  # (1) song_timeline 0개
    [response] = h.sent
    assert response["status"] == "ok"
    assert response["summary"] == _BAR_MAP_ENTRY_REJECTED_SUMMARY
    assert "바뀌어" in response["text"], response["text"]  # (1) 곡이 바뀌었음을 말한다
    if replacement == "other_song":
        assert h.store.latest == other  # (2) 바뀐 타임라인(B) 그대로
        assert BAR_MAP_KEY not in h.store.latest
    else:
        assert h.store.latest is None
    assert h.session._draft_history.depth == depth_before  # (3)
    assert h.console.calls == []


def test_ac008_control_a_reload_of_the_same_song_key_still_saves(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """대조군 — 대조는 곡 열쇠로 한다(REQ-LDBARENTRY-009). 같은 곡을 다시 불러온 경우(열쇠가
    같다)는 막지 못한다 — spec.md Gaps 15번에 수용한 한계로 적혀 있다. 이 시험이 그 경계를
    못박아, 대조가 「타임라인이 바뀌기만 하면 거절」로 넓어지는 변경을 잡는다."""
    h = _make_harness(tmp_path, audio=b"not decoded")
    payload = _valid_payload()

    def reload_same_song(audio_bytes: bytes, first_beat_offset: int) -> dict:
        h.store.latest = _timeline(extra_marker="reloaded")  # 다른 객체, 같은 곡 열쇠
        return payload

    monkeypatch.setattr("server.web.session.synthesize_bar_map", reload_same_song)

    h.session.analyse_bar_map(0)

    assert _types(h.sent) == ["song_timeline", "chat_response"], h.sent
    assert h.session.timeline_bar_map() == payload


# ---------------------------------------------------------------------------
# AC-LDBARENTRY-012 — 소비자 왕복 (실제 분석).
# ---------------------------------------------------------------------------


@requires_analysis
@pytest.mark.parametrize("offset", [0, 1])
def test_ac012_consumer_round_trip(tmp_path: Path, click_track: bytes, offset: int) -> None:
    h = _make_harness(tmp_path, audio=click_track)

    h.session.analyse_bar_map(offset)

    saved = h.session.timeline_bar_map()
    assert saved is not None, h.sent
    timing = build_song_timing_from_bar_map(saved)
    assert timing is not None  # (1)
    bars = {bar["bar"]: bar for bar in saved["bars"]}
    assert timing.downbeat_bar1_seconds == bars[1]["start_ms"] / 1000  # (2)
    assert timing.beats_per_bar == 4  # (3)
    assert timing.bpm == saved["bpm"]  # (3)
    if offset == 0:  # (4)
        assert timing.pickup_beats is None
    else:
        assert timing.pickup_beats == len(bars[0]["beats_ms"])

    # 참고 측정(문턱 없음) — 소비자는 bpm 으로 마디 시작을 계산하고 저장된 start_ms 는 쓰지 않는다.
    # 두 값이 얼마나 어긋나는지 1~5마디에서 잰다(ms). progress.md §E.2 에 적는다.
    gaps_ms = [
        (timing.bar_start_seconds(n) - bars[n]["start_ms"] / 1000) * 1000.0 for n in range(1, 6)
    ]
    print(
        f"AC-012 reference offset={offset} bpm={saved['bpm']!r} "
        "bar_start_seconds(n) - start_ms/1000 [ms] for bars 1..5: "
        + ", ".join(
            f"bar{n}(start_ms={bars[n]['start_ms']})={gap:+.6f}"
            for n, gap in zip(range(1, 6), gaps_ms, strict=True)
        )
    )


# ---------------------------------------------------------------------------
# AC-LDBARENTRY-013 — 접촉 경계 (실제 분석).
# ---------------------------------------------------------------------------


@requires_analysis
def test_ac013_no_console_no_library_no_bpm_confirmation_state(
    tmp_path: Path, click_track: bytes
) -> None:
    h = _make_harness(tmp_path, audio=click_track)
    # 표식은 ``upload_song_audio`` 뒤에 넣는다 — 업로드가 이전 확정 기록을 지운다.
    sentinel_bpm, sentinel_analysis = object(), object()
    h.session._song_bpm = sentinel_bpm
    h.session._song_analysis = sentinel_analysis
    assert not h.library_path.exists()

    h.session.analyse_bar_map(0)

    assert h.session.timeline_bar_map() is not None  # 저장 경로가 실제로 돌았다
    assert h.console.calls == []  # (1)
    assert not h.library_path.exists()  # (2)
    assert h.session._song_bpm is sentinel_bpm  # (3)
    assert h.session._song_analysis is sentinel_analysis  # (3)


# ---------------------------------------------------------------------------
# AC-LDBARENTRY-014 — 재실행은 교체하고, 되돌리기는 직전 값을 복원한다 (실제 분석 두 번).
# ---------------------------------------------------------------------------


@requires_analysis
def test_ac014_rerun_replaces_and_undo_restores_the_previous_value(
    tmp_path: Path, click_track: bytes
) -> None:
    """실제 분석을 오프셋마다 한 번씩 돈다(30 초 클릭 트랙에서 한 번에 0.2 초 안팎)."""
    h = _make_harness(tmp_path, audio=click_track)
    before = _snapshot(h)

    h.session.analyse_bar_map(0)
    v1 = copy.deepcopy(h.store.latest[BAR_MAP_KEY])
    depth_v1 = h.session._draft_history.depth
    assert v1["first_beat_offset"] == 0
    assert depth_v1 == before.depth + 1

    h.session.analyse_bar_map(1)

    v2 = h.store.latest[BAR_MAP_KEY]
    assert v2["first_beat_offset"] == 1  # (1)
    assert v2 != v1  # (1)
    assert h.session._draft_history.depth == depth_v1 + 1  # (2)
    h.session.undo_timeline_draft()
    assert h.store.latest[BAR_MAP_KEY] == v1  # (3)
    h.session.undo_timeline_draft()
    assert BAR_MAP_KEY not in h.store.latest  # (4)
    assert _without(h.store.latest, "draft") == _without(before.timeline, "draft")
    assert h.console.calls == []


# ---------------------------------------------------------------------------
# AC-LDBARENTRY-015 (세션 쪽) — 어떤 결과든 응답은 연결로 나간다.
# ---------------------------------------------------------------------------


def _run_scenario(name: str, tmp_path: Path, mp: pytest.MonkeyPatch) -> list[dict]:
    """분석 단계에 닿는 여섯 결과 중 하나를 만들고, 연결이 받은 프레임 전부를 돌려준다."""
    offset = 0
    audio = b"not decoded"
    with_timeline = True
    if name == "success":
        mp.setattr("server.web.session.synthesize_bar_map", lambda *args: _valid_payload())
    elif name == "timeline_missing":
        with_timeline = False
    elif name == "offset_out_of_range":
        offset = 4
    elif name == "analysis_failure":
        audio = b"not audio"
    elif name == "double_bpm":
        grid = _fake_grid(outcome="adopt_double", raw_bpm=96.0, bpm=192.0)
        mp.setattr("server.audio.bar_map_entry.detect_beat_grid", _Step(grid))
    elif name == "song_changed":
        holder: dict[str, _Harness] = {}

        def swap_then_return(audio_bytes: bytes, first_beat_offset: int) -> dict:
            holder["h"].store.latest = _timeline(song_title="OTHER SONG", sequence_number=2)
            return _valid_payload()

        mp.setattr("server.web.session.synthesize_bar_map", swap_then_return)
    else:  # pragma: no cover - 시험 작성 오류
        raise AssertionError(name)

    h = _make_harness(tmp_path / name, with_timeline=with_timeline, audio=audio)
    if name == "song_changed":
        holder["h"] = h
    h.session.analyse_bar_map(offset)
    assert h.console.calls == []
    return list(h.sent)


def test_ac015_every_outcome_that_reaches_analysis_sends_exactly_one_chat_response(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scenarios = (
        "success",
        "timeline_missing",
        "offset_out_of_range",
        "analysis_failure",
        "double_bpm",
        "song_changed",
    )
    frames: dict[str, list[dict]] = {}
    for name in scenarios:
        with monkeypatch.context() as mp:
            frames[name] = _run_scenario(name, tmp_path, mp)

    responses: dict[str, dict] = {}
    for name, sent in frames.items():
        chat_responses = [f for f in sent if f["type"] == "chat_response"]
        assert len(chat_responses) == 1, (name, _types(sent))
        assert chat_responses[0]["status"] == "ok", name
        responses[name] = chat_responses[0]

    # 성공: 저장 관문이 song_timeline 과 chat_response 를 보냈고, 진입 경로가 더하지 않았다.
    assert _types(frames["success"]) == ["song_timeline", "chat_response"]
    assert responses["success"]["summary"] == SUCCESS_SUMMARY
    # 거절 다섯: 진입 경로가 보낸 chat_response 하나뿐이다 — song_timeline 0개.
    for name in scenarios[1:]:
        assert _types(frames[name]) == ["chat_response"], name
        assert responses[name]["summary"] == _BAR_MAP_ENTRY_REJECTED_SUMMARY, name
    assert SUCCESS_SUMMARY != _BAR_MAP_ENTRY_REJECTED_SUMMARY


# ---------------------------------------------------------------------------
# 방어 점검 (AC 밖) — WS 분기가 먼저 막지만 세션도 직접 불려도 안전해야 한다.
# ---------------------------------------------------------------------------


def test_no_audio_attached_sends_one_error_frame_and_no_chat_response(tmp_path: Path) -> None:
    h = _make_harness(tmp_path)  # 첨부 없음
    before = _snapshot(h)
    assert h.session.song_audio is None

    h.session.analyse_bar_map(0)

    assert _types(h.sent) == ["error"], h.sent
    [frame] = h.sent
    assert frame["kind"] == "song_audio_missing"
    assert "첨부" in frame["message"]
    assert h.store.latest == before.timeline
    assert h.session._draft_history.depth == before.depth
    assert h.console.calls == []


def test_undecodable_base64_is_refused_with_one_chat_response(tmp_path: Path) -> None:
    h = _make_harness(tmp_path)
    # 와이어 검증을 통과한 업로드는 이럴 수 없다 — 세션이 직접 불려도 안전한지를 잰다.
    h.session._song_audio = SongAudioUpload(
        file_name="test.wav",
        mime_type="audio/wav",
        content_base64="@@ not base64 @@",
        sha256="0",
        byte_length=0,
    )
    before = _snapshot(h)

    h.session.analyse_bar_map(0)

    _assert_rejected_and_untouched(h, before, reason="base64")


def test_synthesis_receives_the_decoded_bytes_and_the_requested_offset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    audio = b"\x00\x01 attached bytes \xff"
    synthesis = _Step(BarMapEntryFailure("대역 사유"))
    monkeypatch.setattr("server.web.session.synthesize_bar_map", synthesis)
    h = _make_harness(tmp_path, audio=audio)
    before = _snapshot(h)

    h.session.analyse_bar_map(2)

    assert synthesis.calls == [(audio, 2)]
    _assert_rejected_and_untouched(h, before, reason="대역 사유")
