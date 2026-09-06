"""카드 t307 — 회전이 한 바퀴 돌면 앞 큐와 같은 큐가 나온다.

t306 이 실측해 두고 고치지 않은 결함이다: 한 구간의 단위 수가 변주 수보다
많으면 회전이 처음으로 되돌아와 **앞 큐와 값이 같은 큐**가 선다. 16초 뒤에
똑같은 큐가 또 서는 것은 t305 가 이 기능을 세운 전제("같은 큐 둘은 큐 하나보다
나쁘다")를 정면으로 깬다.

정본(`LXSEQ_SAMPLE_01_Sugar_r3.timeline.html`)이 변주가 마를 때 하는 일은
**반복이 아니라 다른 축**이다 — CHORUS3 의 네 큐는 색이 겹치는 자리에서도
강도·무빙·이펙트로 갈라진다. 이 규칙에는 회전 말고 다른 축이 없으므로 없는
축을 지어내지 않고 큐 수에 상한을 씌우고, 그 사실을 사유로 낸다.

여기서 재는 것 셋:

1. 회전이 만든 큐들이 서로 **다르다**(같은 값이 두 번 안 나온다).
2. 상한이 걸린 구간은 사유를 밖에 낸다 — 조용히 얇아지지 않는다.
3. 두 경로(감독 인터뷰 · 업로드)가 같은 입력 모양에 **같은 답**을 낸다.
"""

from __future__ import annotations

from server.design.cue_density import (
    DEFAULT_VARIANT_LABEL,
    plan_cue_density,
    rotate_palette,
)
from server.looks.songcue import SONGCUE_VARIANT_LABEL

#: 3단위(48초 @120BPM · 8마디 16초) · 변주 2가지 — t306 이 중복을 실측한 모양.
_THREE_UNITS = [0, 48_000]
_BPM = 120.0
_METER = "4/4"


def _cues_for(index: int, plan) -> list:
    return [split for split in plan.splits if split.source_index == index]


def test_no_cue_repeats_an_earlier_cue_in_the_same_section():
    """회전으로 만든 큐가 서로 다르다 — 상한을 씌우기 전에는 셋째가 첫째와 같았다."""
    variants = ("amber", "magenta")
    plan = plan_cue_density(_THREE_UNITS, bpm=_BPM, meter=_METER, palette_sizes=[2, 2])
    rendered = [rotate_palette(variants, split.unit_index) for split in _cues_for(0, plan)]
    assert len(rendered) == len(set(rendered)), (
        "한 구간 안에서 같은 값의 큐가 두 번 섰다 — 16초 뒤의 똑같은 큐는 큐 하나보다 나쁘다"
    )


def test_the_cue_count_is_capped_at_the_variant_count():
    """3단위인데 변주가 둘이면 큐는 둘. 8마디 오프셋은 그대로다."""
    plan = plan_cue_density(_THREE_UNITS, bpm=_BPM, meter=_METER, palette_sizes=[2, 2])
    cues = _cues_for(0, plan)
    assert [split.unit_index for split in cues] == [0, 1]
    assert [split.start_ms for split in cues] == [0, 16_000]


def test_the_cap_says_why_and_names_the_section():
    """줄였다는 사실이 감독에게 나간다 — 얇아진 구간을 번호로 짚는다."""
    plan = plan_cue_density(_THREE_UNITS, bpm=_BPM, meter=_METER, palette_sizes=[2, 2])
    assert any("구간 1" in note and "2건으로" in note for note in plan.notes)
    assert any(DEFAULT_VARIANT_LABEL in note for note in plan.notes)


def test_a_section_within_its_variant_budget_is_untouched():
    """상한은 넘칠 때만 걸린다 — 2단위 · 변주 3가지는 그대로 큐 둘, 사유 없음."""
    plan = plan_cue_density([0, 32_000], bpm=_BPM, meter=_METER, palette_sizes=[3, 3])
    assert len(_cues_for(0, plan)) == 2
    assert plan.notes == ()


def test_an_unmeasured_variant_count_is_not_a_cap():
    """변주 수를 안 주면 중복이 난다고 주장할 근거가 없다 — 안 잰 것으로 안 줄인다."""
    plan = plan_cue_density(_THREE_UNITS, bpm=_BPM, meter=_METER)
    assert len(_cues_for(0, plan)) == 3
    assert plan.notes == ()


class TestBothPathsAgree:
    """감독 인터뷰 경로와 업로드 경로가 **같은 규칙**을 탄다.

    t306 이 남긴 갈림은 하나였다 — 업로드 경로에서는 중복 큐가 값 줄 충돌로
    접히고 그 수가 고지에 나오는데, 인터뷰 경로에는 그 방어가 없어 같은 큐가
    그냥 섰다. 상한을 공유 규칙(``plan_cue_density``)에 씌웠으므로 두 경로 모두
    중복 큐를 애초에 만들지 않는다. 아래는 그 동치를 값으로 잰다.
    """

    def test_the_same_shape_yields_the_same_cues_on_both_paths(self):
        interview = plan_cue_density(
            _THREE_UNITS,
            bpm=_BPM,
            meter=_METER,
            palette_sizes=[2, 2],
            variant_label=DEFAULT_VARIANT_LABEL,
        )
        upload = plan_cue_density(
            _THREE_UNITS,
            bpm=_BPM,
            meter=_METER,
            palette_sizes=[2, 2],
            song_end_ms=None,
            variant_label=SONGCUE_VARIANT_LABEL,
        )
        assert interview.splits == upload.splits
        assert interview.source_origins == upload.source_origins
        assert len(interview.notes) == len(upload.notes) == 1

    def test_only_the_wording_of_the_reason_differs(self):
        """두 경로가 돌리는 것의 **이름**만 다르다 — 규칙이 아니라 낱말이다."""
        interview = plan_cue_density(_THREE_UNITS, bpm=_BPM, meter=_METER, palette_sizes=[2, 2])
        upload = plan_cue_density(
            _THREE_UNITS,
            bpm=_BPM,
            meter=_METER,
            palette_sizes=[2, 2],
            variant_label=SONGCUE_VARIANT_LABEL,
        )
        assert DEFAULT_VARIANT_LABEL in interview.notes[0]
        assert SONGCUE_VARIANT_LABEL in upload.notes[0]
        assert (
            interview.notes[0].replace(DEFAULT_VARIANT_LABEL, SONGCUE_VARIANT_LABEL)
            == upload.notes[0]
        )
