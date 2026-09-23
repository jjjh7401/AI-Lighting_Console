"""타이밍 필드 기본값 배정 시험 — SPEC-LDDESIGN-001 M5 (REQ-LDDESIGN-058~061,
카드 t438)."""

from __future__ import annotations

from server.concept.cue_model import Timing
from server.concept.timing import (
    CHORUS_ENTRY_ATTR_SPLIT,
    CHORUS_ENTRY_STAGGER,
    chorus_entry_timing,
    default_timing,
    emit_fade,
    outro_timing,
)


class TestDefaultTiming:
    """REQ-LDDESIGN-058 — 트리거·구간 종류에 따른 기본값."""

    def test_drop_trigger_is_snap(self):
        timing = default_timing(trigger="드롭 직전의 정적")
        assert timing.kind == "snap"
        assert 0.0 <= timing.seconds <= 0.3

    def test_instrument_add_trigger_is_short(self):
        timing = default_timing(trigger="악기 추가")
        assert timing.kind == "short"
        assert 1.0 <= timing.seconds <= 2.0

    def test_instrument_remove_trigger_is_short(self):
        timing = default_timing(trigger="악기 제거")
        assert timing.kind == "short"

    def test_director_only_trigger_is_long(self):
        timing = default_timing(trigger="코드·조성 변화")
        assert timing.kind == "long"
        assert 2.0 <= timing.seconds <= 4.0

    def test_outro_section_without_trigger_is_long(self):
        timing = default_timing(section="Outro")
        assert timing.kind == "long"

    def test_no_trigger_no_section_still_fills_kind_and_seconds(self):
        """AC-LDDESIGN-011 — 모든 시퀀스 큐가 timing.kind/seconds 를 갖는다."""
        timing = default_timing()
        assert timing.kind in ("snap", "short", "long")
        assert timing.seconds > 0

    def test_trigger_takes_priority_over_section(self):
        timing = default_timing(trigger="드롭 직전의 정적", section="Outro")
        assert timing.kind == "snap"


class TestChorusEntryTiming:
    """REQ-LDDESIGN-059/060 — 후렴 진입 큐: snap + stagger + attr_split."""

    def test_kind_is_snap(self):
        assert chorus_entry_timing().kind == "snap"

    def test_has_stagger_by_default(self):
        timing = chorus_entry_timing()
        assert timing.stagger == CHORUS_ENTRY_STAGGER
        assert timing.stagger is not None

    def test_custom_stagger_overridable(self):
        timing = chorus_entry_timing(stagger="0→0.2s 좌우 파동")
        assert timing.stagger == "0→0.2s 좌우 파동"

    def test_attr_split_separates_color_and_dimmer(self):
        timing = chorus_entry_timing()
        assert "color" in timing.attr_split
        assert "dimmer" in timing.attr_split
        assert timing.attr_split == CHORUS_ENTRY_ATTR_SPLIT


class TestOutroTiming:
    def test_kind_is_long(self):
        assert outro_timing().kind == "long"
        assert 2.0 <= outro_timing().seconds <= 4.0


class TestEmitFade:
    """REQ-LDDESIGN-061 — 새 문법 금지, 기존 store_with_fade 재사용."""

    def test_uses_cue_fade_keyword(self):
        timing = Timing(kind="short", seconds=1.5, attr_split=False, stagger=None)
        result = emit_fade("Store 1.1 Cue 1 'X'", timing)
        assert "CueFade 1.5" in result

    def test_never_emits_property_fade(self):
        timing = Timing(kind="long", seconds=3.0, attr_split=False, stagger=None)
        result = emit_fade("Store 1.1 Cue 2 'Y'", timing)
        assert "Property 'Fade'" not in result

    def test_delegates_to_store_with_fade_g_format(self):
        """cue_fade.store_with_fade 의 ``:g`` 포맷(2.0 → 2)이 그대로 나온다 —
        emit_fade 가 자체 포맷팅을 새로 만들지 않는다는 증거."""
        timing = Timing(kind="long", seconds=2.0, attr_split=False, stagger=None)
        result = emit_fade("Store 1.1 Cue 3 'Z'", timing)
        assert result.endswith("CueFade 2")
