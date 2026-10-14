"""M1 — 마디 지도 합성 단계 (SPEC-LDBARMAP-002, 카드 t647).

AC-LDBARENTRY-005(합성은 순수하고 번호 공간이 맞다) · AC-LDBARENTRY-007(합성 단계 쪽 —
두 배 BPM 채택은 저장하지 않는다) · REQ-LDBARENTRY-007(오프셋 점검은 디코드 전에).
세션 쪽 응답은 M2 의 몫이라 여기서 재지 않는다.

세션·콘솔·UI 없이 바이트와 오프셋만 쓴다. 실제 분석은 시험 안에서 합성한 클릭 트랙에
돌린다 — 저장소에 오디오 파일을 두지 않는다(REQ-LDBARENTRY-016). 단계 대역으로 도는
시험은 librosa 없이도 돈다.

콘솔 접촉: 0건.
"""

from __future__ import annotations

import io
import re
from collections.abc import Sequence
from pathlib import Path

import pytest

from server.audio import bar_map_entry
from server.audio.analyze import analysis_available
from server.audio.bar_map import (
    BarEvent,
    BarFeatures,
    BarFeaturesFailure,
    BarMapFailure,
    BeatGridFailure,
    BeatGridResult,
    BpmCandidateCheck,
    derive_bars,
    detect_beat_grid,
    extract_bar_features,
)
from server.audio.bar_map_entry import (
    KIND_FAILED,
    KIND_REJECTED,
    BarMapEntryFailure,
    first_beat_offset_problem,
    synthesize_bar_map,
)
from server.audio.bar_map_store import (
    BarMapStoreError,
    build_bar_map_payload,
    validate_bar_map,
)

#: 실제 오디오 분석(librosa)이 필요한 시험에만 건다 — 단계 대역으로 도는 시험은 어디서나 돈다.
requires_analysis = pytest.mark.skipif(
    not analysis_available(),
    reason="librosa 미설치 — 폴백 경로는 test_audio_fallback.py 가 판정한다",
)

#: hop_length(512)가 박 간격을 정확히 나누는 표본율 — 이 BPM 에서 박 하나가 정확히 30
#: 프레임이다. 나누어떨어지지 않으면 박 추적기의 프레임 양자화 잡음이 BPM 을 흔든다
#: (test_audio_bar_map.py 의 같은 표본율 주석 참조).
_CLICK_TRACK_SAMPLE_RATE = 24 * 1024
_CLICK_TRACK_BPM = 96.0
_CLICK_TRACK_DURATION_SEC = 30.0


def _synthesize_click_track() -> bytes:
    """알려진 BPM 의 클릭 트랙을 numpy 로 합성해 WAV 바이트열로 돌려준다.

    test_audio_bar_map.py 의 생성기와 같은 식이다(그 파일의 헬퍼는 비공개라 가져오지 않고
    의도적으로 다시 둔다)."""
    import numpy as np
    import soundfile as sf

    sample_rate = _CLICK_TRACK_SAMPLE_RATE
    beat_sec = 60.0 / _CLICK_TRACK_BPM
    n_samples = int(sample_rate * _CLICK_TRACK_DURATION_SEC)
    y = np.zeros(n_samples, dtype=np.float32)
    click_len = int(0.02 * sample_rate)
    t_click = np.arange(click_len) / sample_rate
    click = np.sin(2 * np.pi * 1200 * t_click) * np.exp(-t_click / 0.005)
    for i in range(int(_CLICK_TRACK_DURATION_SEC / beat_sec)):
        start = int(round(i * beat_sec * sample_rate))
        end = min(start + click_len, n_samples)
        y[start:end] += click[: end - start]
    buf = io.BytesIO()
    sf.write(buf, y, sample_rate, format="WAV", subtype="PCM_16")
    return buf.getvalue()


@pytest.fixture(scope="module")
def click_track() -> bytes:
    return _synthesize_click_track()


@pytest.fixture(scope="module")
def reference_grid(click_track: bytes) -> BeatGridResult:
    """같은 오디오에 대해 검출기를 직접 부른 결과 — 합성이 박을 더하거나 빼지 않았는지 대조한다."""
    grid = detect_beat_grid(click_track)
    assert isinstance(grid, BeatGridResult), grid
    return grid


# ---------------------------------------------------------------------------
# 단계 대역 — 합성의 세 분석 단계는 키워드 인자로 바꿔 끼운다(패키지를 monkeypatch 하지 않는다).
# ---------------------------------------------------------------------------


class _Step:
    """분석 단계 대역 — 호출 인자를 ``calls`` 에 기록하고, 정해 둔 값을 돌려주거나 예외를 낸다.

    합성은 모든 예외를 실패 객체로 바꾼다. 그래서 「불리면 안 되는 자리」는 예외가 아니라
    ``calls`` 기록으로 잰다 — AssertionError 를 내게 해도 합성이 삼켜 실패 객체로 돌려준다."""

    def __init__(self, result: object = None, *, raises: Exception | None = None) -> None:
        self.result = result
        self.raises = raises
        self.calls: list[tuple] = []

    def __call__(self, *args: object) -> object:
        self.calls.append(args)
        if self.raises is not None:
            raise self.raises
        return self.result


class _FlatFeatures:
    """특징 추출 대역 — 받은 마디 경계를 기록하고, 경계마다 평평한 특징 하나씩 돌려준다.

    평평한 특징(음량·저역 모두 중앙값 1배)은 실제 분류기가 사건을 내지 않는 값이다."""

    def __init__(self) -> None:
        self.boundaries: list[tuple[int, ...]] = []
        self.returned: tuple[BarFeatures, ...] = ()

    def __call__(
        self, audio_bytes: bytes, bar_boundaries_ms: Sequence[int]
    ) -> tuple[BarFeatures, ...]:
        self.boundaries.append(tuple(bar_boundaries_ms))
        self.returned = tuple(
            BarFeatures(bar=i + 1, volume_norm=1.0, low_band_norm=1.0)
            for i in range(len(bar_boundaries_ms))
        )
        return self.returned


class _LastBarKick:
    """분류기 대역 — 합성이 넘긴 마디별 특징을 기록하고 마지막 특징 마디에 kick_entry 하나를 낸다.

    합성 클릭 트랙은 실제 분류기로는 사건을 거의 내지 않는다. 이 대역이 사건 유무에 기대지
    않고 특징 번호와 저장 마디 번호의 대응을 잰다."""

    def __init__(self) -> None:
        self.received: list[BarFeatures] = []

    def __call__(self, features: Sequence[BarFeatures]) -> list[BarEvent]:
        self.received = list(features)
        if not self.received:
            return []
        last_bar = self.received[-1].bar
        return [BarEvent("kick_entry", last_bar, last_bar)]


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


# ---------------------------------------------------------------------------
# 실패 종류 — 거절(화면에 사유 문장을 그대로)과 분석 실패(원문은 로그에만)를 가른다.
# ---------------------------------------------------------------------------


def test_failure_kinds_are_distinct_and_the_default_is_an_analysis_failure() -> None:
    """종류를 적지 않은 실패는 분석 실패다 — 원문을 화면에 내지 않는 쪽이 기본이다."""
    assert KIND_REJECTED != KIND_FAILED
    assert BarMapEntryFailure("사유").kind == KIND_FAILED
    assert BarMapEntryFailure("사유", kind=KIND_REJECTED).kind == KIND_REJECTED


# ---------------------------------------------------------------------------
# REQ-LDBARENTRY-007 — 오프셋 점검은 오디오 디코드(박 격자 검출) 전에 한다.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("offset", [0, 3])
def test_req007_a_valid_offset_does_reach_the_detector(offset: int) -> None:
    """대조군 — 대역 주입이 실제로 이어져 있어야 아래 「불리지 않았다」가 공허하지 않다.

    같은 입구에서 유효한 오프셋의 검출 실패는 분석 실패(아래 오프셋 거절과 종류가 다르다)."""
    detect = _Step(BeatGridFailure("검출 사유"))
    result = synthesize_bar_map(b"not decoded", offset, detect=detect)
    assert len(detect.calls) == 1
    assert result == BarMapEntryFailure("검출 사유", kind=KIND_FAILED)


@pytest.mark.parametrize("bad_offset", [-1, 4, 99])
def test_req007_out_of_range_offset_fails_before_decode(bad_offset: int) -> None:
    detect = _Step(raises=AssertionError("오프셋 점검 전에 박 격자 검출이 불렸다"))
    result = synthesize_bar_map(b"not decoded", bad_offset, detect=detect)
    assert isinstance(result, BarMapEntryFailure), result
    assert "0~3" in result.reason
    assert result.kind == KIND_REJECTED
    assert detect.calls == []


@pytest.mark.parametrize("bad_offset", [True, 1.0, "1", None], ids=repr)
def test_req007_non_int_offset_fails_before_decode(bad_offset: object) -> None:
    detect = _Step(raises=AssertionError("오프셋 점검 전에 박 격자 검출이 불렸다"))
    result = synthesize_bar_map(b"not decoded", bad_offset, detect=detect)
    assert isinstance(result, BarMapEntryFailure), result
    assert "정수" in result.reason
    assert result.kind == KIND_REJECTED
    assert detect.calls == []


@pytest.mark.parametrize("offset", [0, 1, 2, 3])
def test_req007_offset_problem_is_none_for_every_valid_offset(offset: int) -> None:
    """세션이 base64 를 풀기 전에 부르는 공개 점검 — 쓸 수 있는 오프셋에는 사유가 없다."""
    assert first_beat_offset_problem(offset) is None


@pytest.mark.parametrize("bad_offset", [-1, 4, 99])
def test_req007_offset_problem_names_the_allowed_range(bad_offset: int) -> None:
    problem = first_beat_offset_problem(bad_offset)
    assert problem is not None
    assert "0~3" in problem


@pytest.mark.parametrize("bad_offset", [True, 1.0, "1", None], ids=repr)
def test_req007_offset_problem_demands_an_integer(bad_offset: object) -> None:
    problem = first_beat_offset_problem(bad_offset)
    assert problem is not None
    assert "정수" in problem


class _Opaque:
    """기본 ``repr`` 을 쓰는 임의의 객체 — 그 ``repr`` 에 객체 주소가 든다."""


@pytest.mark.parametrize("bad_offset", [object(), _Opaque()], ids=["object", "opaque"])
def test_req007_non_int_offset_text_does_not_echo_the_value(bad_offset: object) -> None:
    """정수가 아닌 값의 거절 문구는 입력값의 ``repr`` 을 싣지 않는다.

    직접 호출은 임의 객체를 받을 수 있고, 그 기본 ``repr`` 의 객체 주소(``0x…``)가 화면 문구에
    새면 호출마다 문구가 달라지고 내부 표현이 보인다."""
    # 대조군 — 이 객체의 repr 에는 실제로 주소가 든다. 안 들면 아래 단언이 공허하다.
    assert "object at 0x" in repr(bad_offset)
    problem = first_beat_offset_problem(bad_offset)
    assert problem is not None
    assert "정수" in problem
    assert "0x" not in problem, problem
    assert "object at" not in problem, problem


# ---------------------------------------------------------------------------
# AC-LDBARENTRY-005 — 합성은 순수하고 번호 공간이 맞다 (실제 분석, 합성 클릭 트랙).
# ---------------------------------------------------------------------------


@requires_analysis
def test_click_track_reads_as_its_known_bpm_with_a_keep_verdict(
    reference_grid: BeatGridResult,
) -> None:
    """전제 — 합성 클릭 트랙을 검출기가 알려진 BPM·유지(keep) 판정으로 읽는다.

    두 배로 채택되면 아래 시험이 합성 단계의 거절을 맞아 영문 모를 곳에서 깨진다."""
    error_pct = abs(reference_grid.bpm - _CLICK_TRACK_BPM) / _CLICK_TRACK_BPM * 100.0
    assert error_pct <= 1.0, f"bpm={reference_grid.bpm}"
    assert reference_grid.bpm_check.outcome == "keep"


@requires_analysis
@pytest.mark.parametrize("offset", [0, 1, 2, 3])
def test_ac005_pure_synthesis_from_bytes_and_offset(
    click_track: bytes, reference_grid: BeatGridResult, offset: int
) -> None:
    """(1)(2)(3)(5) — 세션·콘솔·UI 없이 바이트와 오프셋만으로 유효한 지도 사전이 나온다."""
    result = synthesize_bar_map(click_track, offset)
    assert isinstance(result, dict), result
    assert validate_bar_map(result) is None

    bars = result["bars"]
    # (2) 박이 빠지거나 겹치지 않는다 — 마디별 박을 이어 붙이면 검출기의 격자와 같다.
    assert [ms for bar in bars for ms in bar["beats_ms"]] == list(reference_grid.beat_times_ms)
    # (3) 못갖춘마디(마디 0)는 오프셋이 0보다 클 때만, 번호는 연속한다.
    first_bar = bars[0]["bar"]
    if offset > 0:
        assert first_bar == 0
        assert len(bars[0]["beats_ms"]) == offset
    else:
        assert first_bar == 1
    assert [bar["bar"] for bar in bars] == list(range(first_bar, first_bar + len(bars)))
    # (5)
    assert result["time_signature"] == [4, 4]
    assert result["first_beat_offset"] == offset


@requires_analysis
@pytest.mark.parametrize("offset", [0, 1, 2, 3])
def test_ac005_bar_numbering_positive_control(click_track: bytes, offset: int) -> None:
    """(4)(4a)(4b)(4c) — 특징 번호와 저장 마디 번호가 같은 1-base 공간이다."""
    classifier = _LastBarKick()
    result = synthesize_bar_map(click_track, offset, classify=classifier)
    assert isinstance(result, dict), result

    # 전제 — 0개면 아래 단언이 사건 없이 공허하게 참이 된다.
    assert len(classifier.received) >= 1, "분류기가 받은 특징이 없다"
    assert len(result["events"]) >= 1, "저장된 사건이 없다"

    stored_bars = [bar["bar"] for bar in result["bars"] if bar["bar"] >= 1]
    # (4a) 특징 번호는 1, 2, …, n 이고 n 은 저장된 마디(마디 0 제외) 수와 같다.
    assert [f.bar for f in classifier.received] == list(range(1, len(classifier.received) + 1))
    assert len(classifier.received) == len(stored_bars)
    # (4b) 주입한 사건이 정확히 하나, 마지막 저장 마디에 놓인다.
    [event] = result["events"]
    assert event["kind"] == "kick_entry"
    assert event["start_bar"] == event["end_bar"] == max(bar["bar"] for bar in result["bars"])


# ---------------------------------------------------------------------------
# AC-LDBARENTRY-005 (6) — 곡·장비 고유값 정적 스캔 (닫힌 목록).
# ---------------------------------------------------------------------------

_FORBIDDEN_PATTERNS = (
    r"\bLOVE ATTACK\b",
    r"\b112(\.\d+)?\b",
    r"\b210\b",
    r"\bGroup\b",
    r"\bfid\b",
)

#: 훑는 파일 목록. 이 시험 파일은 정규식 목록 자신이 있어 뺀다. M2·M3 가 신규 시험 파일을
#: 만들면 여기에 더한다(AC-LDBARENTRY-005 (6) — 세션·메시지·와이어 시험 파일).
_SCANNED_FILES = (
    Path(bar_map_entry.__file__),
    Path(__file__).with_name("test_session_bar_map_entry.py"),
    Path(__file__).with_name("test_messages_bar_map_entry.py"),
    Path(__file__).with_name("test_web_bar_map_entry.py"),
)


@pytest.mark.parametrize("path", _SCANNED_FILES, ids=lambda p: p.name)
@pytest.mark.parametrize("pattern", _FORBIDDEN_PATTERNS)
def test_ac005_no_song_or_rig_specific_values(path: Path, pattern: str) -> None:
    source = path.read_text(encoding="utf-8")
    assert "synthesize_bar_map" in source  # 엉뚱한 파일을 훑어 공허하게 통과하지 않는다
    match = re.search(pattern, source)
    assert match is None, f"{path.name}: {match.group(0)!r}"


def _skeleton(pattern: str) -> str:
    """정규식에서 낱말만 남긴다 — 선택 소수부와 단어 경계를 걷어 낸 글자 그대로의 표본.

    표본을 정규식에서 뽑으므로, 고유값 낱말이 이 파일에 정규식 목록 말고는 글자 그대로
    다시 적히지 않는다."""
    return re.sub(r"\(.*\)\?", "", pattern).replace(r"\b", " ").strip()


@pytest.mark.parametrize("pattern", _FORBIDDEN_PATTERNS)
def test_ac005_scan_would_catch_an_injected_value(pattern: str) -> None:
    """스캔의 대조군(같은 프로세스 안 뮤테이션) — 실제 모듈 소스에 낱말 하나를 심으면 걸린다.

    위 스캔이 통과하는 것이 정규식 오타 때문이 아님을 보인다."""
    source = _SCANNED_FILES[0].read_text(encoding="utf-8")
    assert re.search(pattern, f"{source}\n# {_skeleton(pattern)}\n") is not None


@pytest.mark.parametrize("text", ["bpm_confidence", "confidence"])
def test_ac005_scan_patterns_respect_word_boundaries(text: str) -> None:
    """단어 경계 덕에 ``confidence`` 류 낱말은 장비 번호 정규식에 걸리지 않는다."""
    assert all(re.search(pattern, text) is None for pattern in _FORBIDDEN_PATTERNS)


# ---------------------------------------------------------------------------
# AC-LDBARENTRY-007 (합성 단계 쪽) — 두 배 BPM 채택은 저장하지 않는다 (결정 E1).
# ---------------------------------------------------------------------------


def test_ac007_adopt_double_is_rejected_and_nothing_downstream_runs() -> None:
    raw_bpm = 96.0
    grid = _fake_grid(outcome="adopt_double", raw_bpm=raw_bpm, bpm=raw_bpm * 2)
    detect, extract, classify = _Step(grid), _Step(), _Step()
    result = synthesize_bar_map(b"unused", 0, detect=detect, extract=extract, classify=classify)
    assert isinstance(result, BarMapEntryFailure), result
    assert "두 배" in result.reason
    assert result.kind == KIND_REJECTED  # 규칙이 결과를 거절했다 — 분석이 실패한 게 아니다(E1)
    assert len(detect.calls) == 1
    assert extract.calls == []
    assert classify.calls == []


def test_ac007_the_same_grid_with_a_keep_verdict_is_not_rejected() -> None:
    """대조군 — 거절은 채택 판정 하나에서만 나온다(격자·BPM 값 때문이 아니다)."""
    grid = _fake_grid(outcome="keep", raw_bpm=96.0, bpm=96.0)
    extract = _FlatFeatures()
    result = synthesize_bar_map(b"unused", 0, detect=_Step(grid), extract=extract)
    assert isinstance(result, dict), result
    assert extract.boundaries != []


# ---------------------------------------------------------------------------
# 단계 사이 배선 — 사유는 바뀌지 않고, 값은 제자리로 흐른다 (librosa 없이 돈다).
# ---------------------------------------------------------------------------


def test_detector_failure_reason_passes_through_unchanged() -> None:
    extract, classify = _Step(), _Step()
    result = synthesize_bar_map(
        b"unused",
        0,
        detect=_Step(BeatGridFailure("검출기 사유")),
        extract=extract,
        classify=classify,
    )
    assert result == BarMapEntryFailure("검출기 사유", kind=KIND_FAILED)
    assert extract.calls == []
    assert classify.calls == []


def test_empty_beat_grid_reports_derive_bars_own_reason() -> None:
    expected = derive_bars((), 0)
    assert isinstance(expected, BarMapFailure)
    extract = _Step()
    result = synthesize_bar_map(
        b"unused", 0, detect=_Step(_fake_grid(beat_count=0)), extract=extract
    )
    assert result == BarMapEntryFailure(expected.reason, kind=KIND_FAILED)
    assert extract.calls == []


def test_feature_failure_reason_passes_through_unchanged() -> None:
    classify = _Step()
    result = synthesize_bar_map(
        b"unused",
        0,
        detect=_Step(_fake_grid()),
        extract=_Step(BarFeaturesFailure("특징 사유")),
        classify=classify,
    )
    assert result == BarMapEntryFailure("특징 사유", kind=KIND_FAILED)
    assert classify.calls == []


def test_too_few_bars_reports_the_analyzers_own_reason() -> None:
    """박이 3개뿐이면 마디 경계가 2개 미만이다 — 실제 추출 함수가 디코드 전에 스스로 거절한다."""
    grid = _fake_grid(beat_count=3)
    bars = derive_bars(grid.beat_times_ms, 0)
    assert not isinstance(bars, BarMapFailure)
    expected = extract_bar_features(b"unused", bars.bar_boundaries_ms)
    assert isinstance(expected, BarFeaturesFailure)
    result = synthesize_bar_map(b"unused", 0, detect=_Step(grid))
    assert result == BarMapEntryFailure(expected.reason, kind=KIND_FAILED)


def _mask_object_addresses(text: str) -> str:
    return re.sub(r"0x[0-9a-fA-F]+", "0x…", text)


@pytest.mark.parametrize(
    "bad_audio",
    [b"\x00\x01\x02 not audio", b"", None],
    ids=["garbage", "empty", "not_bytes"],
)
def test_undecodable_audio_reports_the_detectors_own_reason(bad_audio: object) -> None:
    """실제 검출기가 못 읽는 입력 — 분석 라이브러리가 없는 환경이면 폴백 사유가 같은 자리로 온다."""
    expected = detect_beat_grid(bad_audio)
    assert isinstance(expected, BeatGridFailure)
    result = synthesize_bar_map(bad_audio, 0)
    assert isinstance(result, BarMapEntryFailure), result
    # 디코더 사유에 든 객체 주소(0x…)는 호출마다 달라져 주소만 가리고 대조한다.
    assert _mask_object_addresses(result.reason) == _mask_object_addresses(expected.reason)
    assert result.kind == KIND_FAILED  # 원문 사유 — 화면에 낼 문장이 아니라 로그에 남길 원문


def test_builder_error_reason_passes_through_unchanged() -> None:
    """빌더가 스스로 검증해 낸 BarMapStoreError 문구를 그대로 싣는다(앞뒤로 덧붙이지 않는다).

    빌더의 오류도 분석 단계의 실패다 — 규칙이 요청을 거절한 게 아니라서 종류는 분석 실패다."""
    grid = _fake_grid()
    bad_events = [BarEvent("not_a_kind", 1, 1)]
    with pytest.raises(BarMapStoreError) as expected:
        build_bar_map_payload(
            grid.beat_times_ms, 0, bpm=grid.bpm, time_signature=(4, 4), events=bad_events
        )
    result = synthesize_bar_map(
        b"unused", 0, detect=_Step(grid), extract=_FlatFeatures(), classify=_Step(bad_events)
    )
    assert result == BarMapEntryFailure(str(expected.value), kind=KIND_FAILED)


@pytest.mark.parametrize("raising_step", ["detect", "extract", "classify"])
def test_no_exception_escapes_from_any_step(raising_step: str) -> None:
    """분석 단계가 예외를 내도 합성은 실패 객체를 돌려준다 — 예외가 새면 작업이 조용히 죽는다."""
    steps: dict[str, object] = {
        "detect": _Step(_fake_grid()),
        "extract": _FlatFeatures(),
        "classify": _Step([]),
    }
    steps[raising_step] = _Step(raises=RuntimeError("시험용 오류"))
    result = synthesize_bar_map(b"unused", 0, **steps)
    assert isinstance(result, BarMapEntryFailure), result
    assert "RuntimeError" in result.reason
    assert "시험용 오류" in result.reason
    assert result.kind == KIND_FAILED  # 예기치 않은 예외는 분석 실패다 — 문구는 로그로만 간다


@pytest.mark.parametrize("offset", [0, 1, 2, 3])
def test_features_and_events_flow_through_in_order(offset: int) -> None:
    grid = _fake_grid()
    extract = _FlatFeatures()
    classify = _Step([BarEvent("kick_entry", 2, 2)])
    result = synthesize_bar_map(
        b"unused", offset, detect=_Step(grid), extract=extract, classify=classify
    )
    assert isinstance(result, dict), result
    bars = derive_bars(grid.beat_times_ms, offset)
    assert not isinstance(bars, BarMapFailure)
    # 추출은 derive_bars 가 낸 마디 경계를 받고, 분류는 추출이 낸 특징을 그대로 받는다.
    assert extract.boundaries == [bars.bar_boundaries_ms]
    assert classify.calls == [(extract.returned,)]
    # 분류가 낸 사건은 저장 사전에 그대로 실린다.
    assert [(e["kind"], e["start_bar"], e["end_bar"]) for e in result["events"]] == [
        ("kick_entry", 2, 2)
    ]


def test_stored_bpm_is_the_detectors_final_bpm() -> None:
    """결정 E4 (가) — 출처를 가르려고 세 값을 일부러 다르게 둔다: 원시 BPM · 검출기 최종 BPM ·
    박 간격에서 나오는 값(500 ms = 120). 저장되는 값은 검출기의 최종 BPM 이다."""
    grid = _fake_grid(outcome="keep", raw_bpm=100.0, bpm=123.5, step_ms=500)
    result = synthesize_bar_map(b"unused", 0, detect=_Step(grid), extract=_FlatFeatures())
    assert isinstance(result, dict), result
    assert result["bpm"] == 123.5


def test_default_steps_are_resolved_at_call_time(monkeypatch: pytest.MonkeyPatch) -> None:
    """키워드 인자가 없으면 호출 시점에 모듈의 분석 함수 이름을 읽는다(import 때 묶지 않는다)."""
    detect, extract, classify = _Step(_fake_grid()), _FlatFeatures(), _Step([])
    monkeypatch.setattr(bar_map_entry, "detect_beat_grid", detect)
    monkeypatch.setattr(bar_map_entry, "extract_bar_features", extract)
    monkeypatch.setattr(bar_map_entry, "classify_bar_events", classify)
    result = synthesize_bar_map(b"unused", 0)
    assert isinstance(result, dict), result
    assert len(detect.calls) == 1
    assert len(extract.boundaries) == 1
    assert len(classify.calls) == 1
