"""트래킹 4모드 기본값 배정 + cue_only 누출 검사기 시험 — SPEC-LDDESIGN-001
M5 (REQ-LDDESIGN-053~057, 카드 t438).

``verify_no_cue_only_leak`` 은 프로퍼티 시험이다 — cue_only 행을 제거한
시퀀스와 비교해 값이 같은지를 판정한다(해석기 자체를 다시 만들지
않는다, REQ-057 은 이미 :mod:`server.concept.resolver` 가 보장한다).
"""

from __future__ import annotations

import pytest

from server.concept.resolver import resolve_sequence
from server.concept.tracking import (
    CUE_KIND_PHRASE,
    CUE_KIND_SAFETY_FIRST,
    CUE_KIND_SAFETY_LAST,
    CUE_KIND_SECTION,
    default_tracking,
    verify_no_cue_only_leak,
)


class TestDefaultTracking:
    """REQ-LDDESIGN-053~056."""

    def test_safety_first_is_block(self):
        assert default_tracking(CUE_KIND_SAFETY_FIRST) == "block"

    def test_safety_last_is_release(self):
        assert default_tracking(CUE_KIND_SAFETY_LAST) == "release"

    def test_section_is_track(self):
        assert default_tracking(CUE_KIND_SECTION) == "track"

    def test_phrase_is_cue_only(self):
        assert default_tracking(CUE_KIND_PHRASE) == "cue_only"

    def test_unknown_kind_raises(self):
        with pytest.raises(ValueError):
            default_tracking("unknown")


def _ac015_fixture():
    """AC-LDDESIGN-015 — 프레이즈 큐(Cue Only)가 밝기를 100 까지 올려도
    다음 구간 큐로 새지 않는다(두 구간 큐 사이에 삽입된 픽스처)."""
    return [
        {
            "section": "Chorus",
            "occurrence": 1,
            "ops": [{"op": "expand", "roles": ["KEY"], "dimmer": 60}],
            "tracking": "track",
        },
        {
            "section": "Chorus",
            "occurrence": 1,
            "ops": [{"op": "expand", "roles": ["WASH-U"], "dimmer": 100}],
            "tracking": "cue_only",
        },
        {
            "section": "Chorus",
            "occurrence": 2,
            "ops": [{"op": "add", "roles": ["FOH"], "dimmer": 40}],
            "tracking": "track",
        },
    ]


class TestVerifyNoCueOnlyLeak:
    """REQ-LDDESIGN-057/AC-LDDESIGN-015."""

    def test_ac015_fixture_has_no_leak(self):
        assert verify_no_cue_only_leak(_ac015_fixture()) is True

    def test_ac015_fixture_next_section_does_not_contain_phrase_group(self):
        states = resolve_sequence(_ac015_fixture())
        assert "WASH-U" not in states[2].dim
        assert states[2].dim == {"KEY": 60, "FOH": 40}

    def test_no_cue_only_rows_trivially_passes(self):
        rows = [
            {"section": "Intro", "occurrence": 1, "ops": [{"op": "retain"}], "tracking": "track"},
        ]
        assert verify_no_cue_only_leak(rows) is True

    def test_multiple_cue_only_rows_in_a_row(self):
        rows = [
            {
                "section": "Verse",
                "occurrence": 1,
                "ops": [{"op": "expand", "roles": ["KEY"], "dimmer": 30}],
                "tracking": "track",
            },
            {
                "section": "Verse",
                "occurrence": 1,
                "ops": [{"op": "add", "roles": ["BACK"], "dimmer": 50}],
                "tracking": "cue_only",
            },
            {
                "section": "Verse",
                "occurrence": 1,
                "ops": [{"op": "add", "roles": ["SIDE-L"], "dimmer": 50}],
                "tracking": "cue_only",
            },
            {
                "section": "Bridge",
                "occurrence": 1,
                "ops": [{"op": "retain"}],
                "tracking": "track",
            },
        ]
        assert verify_no_cue_only_leak(rows) is True
        states = resolve_sequence(rows)
        assert states[-1].dim == {"KEY": 30}
