"""카드 t308 — 마디 분할이 **실측 분석 결과 위에서** 걸리는가.

t305·t306 이 세운 분할 규칙의 시험은 전부 손으로 만든 ``ConfirmedSongAnalysis``
위에서 돌았다. 그래서 규칙 자체는 초록인데 **DSP 가 쪼갤 수 있는 구간을 실제로
내놓는지**는 아무도 안 쟀다. 그 구멍이 실제로 문제였다: 저장소의 유일한 합성
트랙(40초, 가장 긴 구간 16초)은 8마디 단위 둘(129.199 BPM 에서 29.72초)에
**원리적으로 못 닿는다**. 규칙이 옳아도 이 입력으로는 한 번도 안 걸린다.

이 파일은 그 두 축을 한 줄에 잇는다:

* 긴 구간 픽스처를 **분석기에 실제로 통과시켜** 나온 구간이 두 단위에 닿는지.
* 그 분석 결과를 그대로 ``plan_cue_density`` 에 먹여 큐가 늘어나는지.

2026-09-06 실측(카드 t308): 분절기에는 구간 길이 상한이 없다 —
``_MIN_SEGMENT_SECONDS`` 는 **하한**이고, 60초 구간을 의도한 입력은 59.98초
구간으로 돌아온다. 짧았던 것은 분절기가 아니라 픽스처였다. 이 시험이 초록인
한 그 사실이 유지된다.
"""

from __future__ import annotations

from server.audio.analyze import AnalysisResult, analyze
from server.design.cue_density import (
    BAR_UNIT_BARS,
    MIN_UNITS_TO_SPLIT,
    bar_milliseconds,
    plan_cue_density,
)

from .fixtures.audio import LONG_FIXTURE_DURATION_MS, synthesize_long_section_track


def _analysed() -> AnalysisResult:
    outcome = analyze(synthesize_long_section_track())
    assert isinstance(outcome, AnalysisResult), getattr(outcome, "reason", outcome)
    return outcome


def test_the_segmenter_emits_a_section_long_enough_to_split() -> None:
    """분절기가 두 단위에 닿는 구간을 **실제로** 내놓는다.

    상한이 생기면(또는 픽스처가 짧아지면) 여기서 깨진다 — 분할 기능이 조용히
    도달 불가가 되는 것을 막는 유일한 관문이다.
    """
    result = _analysed()
    unit_ms = bar_milliseconds(result.bpm, "4/4") * BAR_UNIT_BARS

    edges = [*result.boundaries_ms, LONG_FIXTURE_DURATION_MS]
    spans = zip(edges[:-1], edges[1:], strict=True)
    units = [int((end - start) // unit_ms) for start, end in spans]

    assert units, "구간이 하나도 없다 — 분석기가 경계를 못 냈다"
    assert max(units) >= MIN_UNITS_TO_SPLIT, (
        f"가장 긴 구간이 {max(units)}단위뿐 — 두 단위(8마디×2)에 못 닿아 분할이 "
        f"한 번도 안 걸린다. 측정 BPM {result.bpm:.3f}, 한 단위 {unit_ms / 1000:.2f}초"
    )


def test_the_analysed_sections_actually_produce_extra_cues() -> None:
    """분석 결과를 그대로 먹이면 구간 수보다 큐가 많다 — 손으로 만든 기록이 아니다."""
    result = _analysed()
    starts = list(result.boundaries_ms)

    plan = plan_cue_density(
        starts,
        bpm=result.bpm,
        meter="4/4",
        song_end_ms=LONG_FIXTURE_DURATION_MS,
    )

    assert plan.cue_count > len(starts), (
        f"구간 {len(starts)}개에서 큐 {plan.cue_count}장 — 분할이 한 건도 안 걸렸다. "
        f"사유: {plan.notes}"
    )
    # 구간마다 큐가 둘 이상 나온 구간이 최소 하나 있어야 「구간 안에서 자란다」가 참이다.
    origins = plan.source_origins
    assert any(origins.count(index) >= 2 for index in set(origins))


def test_bpm_absent_still_means_no_split_on_measured_sections() -> None:
    """실측 구간이라도 BPM 이 없으면 분할은 0건 — t305 의 판단이 이 경로에서도 산다."""
    result = _analysed()
    starts = list(result.boundaries_ms)

    plan = plan_cue_density(starts, bpm=None, meter="4/4", song_end_ms=LONG_FIXTURE_DURATION_MS)

    assert plan.cue_count == len(starts)
    assert plan.notes and "BPM 미선언" in plan.notes[0]
