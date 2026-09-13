"""t302 — 분석 절반과 타임라인 절반 사이의 이음매.

두 절반은 따로따로 실측돼 있었다: 업로드→`analyse_song_audio`→확인 카드→
`prepare_songcue`→실제 콘솔 쓰기(2026-09-06 실기), 그리고 두 축 타임라인 뷰→
코파일럿 큐 편집→초안→수락 카드→`Store Sequence N Cue M /Merge`(같은 날 가짜
콘솔). 이 사이가 이어지는지는 아무도 안 봤다.

안 이어져 있었다. 타임라인 payload 를 만드는 자리는 `_song_send_timeline` 하나뿐이고
그것을 부르는 것은 연출 인터뷰(`_song_design_interview`)뿐인데, 그 경로는 구간을
**지시문 문자열에서만** 읽었다. 그래서 감독이 곡을 올려 구간을 확인해 놓아도,
타임라인에 세우려면 같은 구간을 손으로 다시 적어야 했다.

여기 고정하는 것은 그 이음매다: 확정 기록이 있고 지시문이 구간을 안 들고 있으면
확정 구간이 기본값이 된다. 명시한 구간이 조용히 덮이지 않는 것도 같이 고정한다.
"""

from __future__ import annotations

from server.design.profile import BpmResolution
from server.web.question import ConfirmedSongAnalysis, ConfirmedSongSection

from .test_runner_self_correction import ScriptedProvider
from .test_web_session import TestSongDesignInterviewSession as _Harness
from .test_web_session import _session

#: 인터뷰 5장 + 리뷰 1장. 미해소 구간이 있으면 재질의 카드가 더 붙는데, 답을 다
#: 소진하면 채널이 UNANSWERED 를 돌려주므로 흐름은 그대로 끝까지 간다.
_INTERVIEW_ANSWERS = [
    "우주",
    "우주 색 조합",
    "Ring In",
    "우주 컨셉 우선 배치",
    "템포 맞춤 (BPM 기준)",
]

_NO_SECTIONS = "디자인 큐 시트, 시퀀스 110, 프리셋 21번부터, 타임코드 7"


def _confirmed(*spans: tuple[int, int, int], selected_all: bool = True) -> ConfirmedSongAnalysis:
    return ConfirmedSongAnalysis(
        source_sha256="0" * 64,
        source_file_name="synth_128bpm.wav",
        confirmed_at="2026-09-06T00:00:00+00:00",
        bpm=BpmResolution(bpm=128.0, source="measured", reason="측정값 채택", mismatches=()),
        sections=tuple(
            ConfirmedSongSection(
                index=index,
                label=f"{start // 60000}:{start // 1000 % 60:02d} · D{d}",
                start_ms=start,
                end_ms=end,
                d_level=d,
                selected=selected_all or index == 0,
            )
            for index, (start, end, d) in enumerate(spans)
        ),
    )


def _timeline_events(sent):
    return [event for event in sent if event.get("type") == "song_timeline"]


def _drive(tmp_path, instruction, analysis):
    harness = _Harness()
    session, _console, _audit, sent, _ = _session(tmp_path, ScriptedProvider([]))
    session._registry = harness._registry([])
    session._question_channel = harness._Channel(list(_INTERVIEW_ANSWERS))
    session._song_analysis = analysis
    session.run_instruction(instruction)
    return sent


def test_a_confirmed_song_reaches_the_timeline_without_retyping_its_sections(tmp_path):
    """이음매 그 자체 — 확정만 있고 지시문에 구간이 없어도 타임라인이 선다."""
    analysis = _confirmed((0, 24_000, 2), (24_000, 48_000, 3), (48_000, 72_000, 5))

    events = _timeline_events(_drive(tmp_path, _NO_SECTIONS, analysis))

    assert events, "확정 구간이 있는데 타임라인 이벤트가 하나도 안 나갔다"
    timeline = events[0]["timeline"]
    assert [section["start_ms"] for section in timeline["sections"]] == [0, 24_000, 48_000]
    assert [section["label"] for section in timeline["sections"]] == ["S1", "S2", "S3"]


def test_a_song_with_no_cue_sheet_fields_still_renders(tmp_path):
    """구간 이름·무드가 없는 곡도 렌더된다 — 부재는 거절 사유가 아니다."""
    analysis = _confirmed((0, 30_000, 3))

    events = _timeline_events(_drive(tmp_path, _NO_SECTIONS, analysis))

    assert events
    section = events[0]["timeline"]["sections"][0]
    assert section["label"] == "S1"
    assert "palette" in section and "position" in section


def test_explicit_sections_still_win_over_the_confirmed_record(tmp_path):
    """명시한 구간이 확정 기록에 조용히 덮이지 않는다."""
    analysis = _confirmed((0, 24_000, 2), (24_000, 48_000, 3))
    instruction = (
        "디자인 큐 시트, 시퀀스 110, 프리셋 21번부터, 타임코드 7: "
        "인트로 0:00 잔잔한 발라드, 후렴 0:40 클럽 드롭"
    )

    events = _timeline_events(_drive(tmp_path, instruction, analysis))

    assert events
    labels = [section["label"] for section in events[0]["timeline"]["sections"]]
    assert labels == ["인트로", "후렴"]


def test_without_a_confirmed_record_the_refusal_is_unchanged(tmp_path):
    """확정 기록이 없으면 오늘의 거절이 바이트 그대로 선다."""
    harness = _Harness()
    session, _console, _audit, sent, _ = _session(tmp_path, ScriptedProvider([]))
    session._registry = harness._registry([])
    session._question_channel = harness._Channel(list(_INTERVIEW_ANSWERS))

    event = session.run_instruction(_NO_SECTIONS)

    assert _timeline_events(sent) == []
    assert "곡 구간을 읽지 못해" in event["text"]


def test_confirmed_bpm_reaches_the_bar_boundary_split_without_retyping_it(tmp_path):
    """t381 — 이음매는 구간까지만 이어져 있었다. BPM 은 안 이어져 있었다.

    `_song_design_interview_run` 은 `MusicProfile.bpm` 을 지시문의 ``BPM 120``
    같은 문자열에서만 읽는다(``_SONG_BPM`` 정규식). 확정 분석이 이미 BPM 을
    쥐고 있어도 지시문에 다시 적지 않으면 `profile.bpm` 은 `None` 으로 남고,
    `_split_sections_for_density`(카드 t305, 마디 경계 큐 분할)는 `bpm=None`
    이면 **한 건도 쪼개지 않는다**(`cue_density.py` 의 명시된 규약) — 즉 확정
    BPM 이 있어도 마디 분할 기능이 조용히 꺼진다.

    40초짜리 첫 구간은 BPM 128 · 4/4 에서 21.3마디라 8마디 단위로 2건까지
    쪼개져야 한다(`floor(21.3/8)=2`). 확정 BPM 이 인터뷰 경로까지 이어지면
    타임라인에 구간 1개가 아니라 쪼개진 큐 여러 개로 선다.
    """
    analysis = _confirmed((0, 40_000, 3), (40_000, 80_000, 5))

    harness = _Harness()
    session, _console, _audit, sent, _ = _session(tmp_path, ScriptedProvider([]))
    session._registry = harness._registry([])
    session._question_channel = harness._Channel(list(_INTERVIEW_ANSWERS))
    session._song_analysis = analysis
    session._song_bpm = analysis.bpm  # analyse_song_audio 가 항상 같이 채우는 필드
    session.run_instruction(_NO_SECTIONS)

    events = _timeline_events(sent)
    assert events, "확정 구간이 있는데 타임라인 이벤트가 하나도 안 나갔다"
    starts = [section["start_ms"] for section in events[0]["timeline"]["sections"]]
    # BPM 이 이어졌다면 첫 40초 구간이 8마디 단위(≈15초)로 2조각 이상 쪼개져
    # 시작 시각이 3개 이상(0, ~15000, 40000, ...) 나와야 한다. BPM 이 안 이어지면
    # (오늘의 결함) 구간마다 하나씩, 시작 시각은 2개(0, 40000)뿐이다.
    assert len(starts) > 2, (
        f"확정 BPM 128 이 연출 인터뷰까지 이어지지 않았다 — 마디 분할이 꺼진 채로 "
        f"구간 2개 그대로 나왔다: {starts}"
    )


def test_explicit_bpm_in_the_instruction_still_wins_over_the_confirmed_record(tmp_path):
    """명시한 BPM 이 확정 기록에 조용히 덮이지 않는다 — 구간 기본값과 같은 규칙.

    BPM 40 을 지시문에 직접 적으면(8마디 = 48초) 40초짜리 구간은 아직
    한 마디 단위도 못 채워 쪼개지지 않는다. 확정 BPM(128)이 대신 쓰였다면
    8마디가 15초라 같은 구간이 쪼개졌을 것이다.
    """
    analysis = _confirmed((0, 40_000, 3), (40_000, 80_000, 5))
    instruction = "디자인 큐 시트, 시퀀스 110, 프리셋 21번부터, 타임코드 7, BPM 40"

    harness = _Harness()
    session, _console, _audit, sent, _ = _session(tmp_path, ScriptedProvider([]))
    session._registry = harness._registry([])
    session._question_channel = harness._Channel(list(_INTERVIEW_ANSWERS))
    session._song_analysis = analysis
    session._song_bpm = analysis.bpm  # analyse_song_audio 가 항상 같이 채우는 필드
    session.run_instruction(instruction)

    events = _timeline_events(sent)
    assert events
    starts = [section["start_ms"] for section in events[0]["timeline"]["sections"]]
    assert starts == [0, 40_000], f"지시문의 명시 BPM 40 이 확정 BPM 128 에 덮였다: {starts}"
