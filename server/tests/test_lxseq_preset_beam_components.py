"""t236 — bm 값을 성분 목록으로 가르는 술어와, **성분 수가 보존되는지**를 지키는 검사.

설계 정본: `.moai/reports/t229-bm/verdict.md` (main `9ba5bbf`). 그 8.1 절이 이 파일을
요구한다 — bm 은 col 과 달리 성분 개수가 **가변**이라, 「판정기와 판독기가 같은
술어를 부른다」만으로는 성분 유실이 안 막힌다.

    col   (R, G, B)   3성분 고정 -> 하나 흘리면 형태가 깨져서 바로 보인다
    bm    가변 목록                -> 하나 흘려도 여전히 목록이다. 안 보인다.

유실은 `apply_untranslatable` 보다 **조용한** 실패다. 그쪽은 0건으로 크게 실패하고
사람이 본다. 이쪽은 「성공」으로 보고되고 콘솔에는 절반만 들어간다 — 값은 되읽을 수
없으므로 틀린 것이 조용히 남는다.

🔴 **명령 빌더는 이 회차에 없다.** `Attribute 'Zoom' At 45` 의 `45` 가 도인지
퍼센트인지 **지금은** 이 채널로 못 잰다(응답기에 Programmer 판독 별칭이 없다 — t235).
「원리적으로」가 아니라 **아직 안 넣은 별칭** 때문이고, 여는 것은 감독 승인 사안이다.
그래서 이 파일이 겨누는 것은 「빌더가 성분을 안 버리는가」가 아니라 그 앞
단계다 — **술어 자신이 성분을 안 버리는가**, 그리고 **아직 빌더가 없다는 사실이
관측 가능한가**.

열리는 행 수는 0 -> 0 이다. 지금 5행을 막는 것은 어휘이지 적용 경로가 아니다.
이 파일의 값은 어휘를 여는 날 그 시트가 통째로 0건이 되는 것을 막는 것이다.

순수 함수 검증이다. 콘솔·네트워크 접촉 0.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from server.lxseq import preset_parser as parser_module
from server.lxseq.preset_parser import (
    HOLD_FAMILY_OUT_OF_SCOPE,
    HOLD_PROBE_REJECTED,
    HOLD_VALUE_NOT_MACHINE_READABLE,
    _bm_components,
    _bm_unreadable_segments,
    classify_storability,
    parse_preset_csv,
)

RIG = Path("src/Lighting_Designer/02_RIG팩")
BM = RIG / "LXSEQ_RIG_01_ShowBase_r3.preset-bm.csv"
SHEET_SPEC = Path("src/Lighting_Designer/01_스펙/LX-SEQ-SPEC-v2.1.md")

#: 정본 시트 5행이 실제로 가지는 성분. **손으로 적은 기대값**이다 — 술어의 출력을
#: 그대로 받아 적으면 술어가 무엇을 하든 통과하는 검사가 된다.
EXPECTED = dict(
    [
        ("BM.01", (("Zoom", "45°"), ("Gobo", "OPEN"), ("Prism", "OFF"))),
        ("BM.02", (("Zoom", "20°"), ("Gobo", "OPEN"))),
        ("BM.03", (("Zoom", "8°"), ("Prism", "3-facet ON"))),
        ("BM.04", (("Frost", "30%"),)),
        ("BM.05", None),  # `예비` 는 속성이 아니다 — 아래 전용 검사 참조
    ]
)


def _records():
    return parse_preset_csv(BM.read_text(encoding="utf-8-sig")).records


def _by_id():
    return dict((r.preset_id, r) for r in _records())


class TestTheSheetIsWhatWeMeasuredAgainst:
    """비공허성 앵커 — 「전부 통과」가 「행이 0개」로 통과하지 않게 총계를 같이 든다."""

    def test_the_sheet_still_has_exactly_five_rows(self):
        records = _records()
        assert len(records) == 5
        assert sorted(r.preset_id for r in records) == sorted(EXPECTED)

    def test_no_beam_row_is_storable_and_that_is_the_measured_zero(self):
        """0 -> 0. 이 카드는 행을 열지 않는다 — **총계 옆의 0** 으로 적는다."""
        records = _records()
        storable = [r for r in records if r.storable]
        assert (len(storable), len(records)) == (0, 5)


class TestTheComponentsAreWhatTheSheetSays:
    @pytest.mark.parametrize("preset_id", sorted(EXPECTED))
    def test_each_row_reads_into_its_expected_components(self, preset_id):
        record = _by_id()[preset_id]
        assert _bm_components(record.value_raw) == EXPECTED[preset_id]

    def test_the_readable_rows_carry_eight_components_in_total(self):
        """총계 — 어느 한 행이 성분을 흘리면 이 숫자가 먼저 움직인다."""
        total = sum(len(_bm_components(r.value_raw) or ()) for r in _records())
        assert total == 8


class TestNoComponentIsEverDropped:
    """🔴 설계 8.1 절이 요구한 검사. 이 클래스가 이 파일의 이유다."""

    def test_the_component_count_equals_the_segment_count(self):
        """성분 수 == 조각 수. **마지막 성분을 버리면 여기가 빨개진다.**"""
        for record in _records():
            components = _bm_components(record.value_raw)
            if components is None:
                continue
            segments = record.value_raw.split(parser_module._BM_SEGMENT_SEPARATOR)
            assert len(components) == len(segments), record.preset_id

    def test_every_segment_of_the_sheet_is_accounted_for(self):
        """조각은 성분이 되거나 **보고되거나** 둘 중 하나다 — 사라지는 조각은 없다.

        원자(`_bm_segment_component`)로 센다. `_bm_components` 로 세면 안 되는데,
        그것은 all-or-nothing 이라 못 읽는 조각이 하나만 있어도 0 을 답하기
        때문이다 — 그 0 을 「조각이 사라졌다」로 읽으면 검사가 거짓말을 한다.
        (이 검사는 처음에 그렇게 써서 BM.05 에서 빨개졌고, 틀린 쪽은 검사였다.)
        """
        for record in _records():
            segments = record.value_raw.split(parser_module._BM_SEGMENT_SEPARATOR)
            readable = [s for s in segments if parser_module._bm_segment_component(s) is not None]
            reported = _bm_unreadable_segments(record.value_raw)
            assert len(readable) + len(reported) == len(segments), record.preset_id

    def test_the_all_or_nothing_rule_is_what_zeroes_a_partly_read_row(self):
        """위 검사가 왜 원자로 세는지 — BM.05 는 조각 3 중 2 를 읽을 수 있는데도
        `_bm_components` 가 `None` 이다. 그것이 유실 방지의 형태다."""
        record = _by_id()["BM.05"]
        segments = record.value_raw.split(parser_module._BM_SEGMENT_SEPARATOR)
        readable = [s for s in segments if parser_module._bm_segment_component(s) is not None]
        assert (len(readable), len(segments)) == (2, 3)
        assert _bm_components(record.value_raw) is None

    def test_a_partially_readable_value_is_none_not_a_short_list(self):
        """all-or-nothing — 읽은 것만 돌려주는 것이 곧 성분 유실이다."""
        assert _bm_components("Zoom 45° · 예비") is None
        assert _bm_components("예비 · Zoom 45°") is None

    def test_an_attribute_with_no_value_is_not_a_component(self):
        """뮤테이션이 살아남아서 추가한 검사 — 속성 이름만 있고 값이 없는 조각을
        성분으로 치면 빈 값이 명령에 실린다. 빈 값은 콘솔에서 무엇이 되는지
        이 저장소가 모른다."""
        assert _bm_components("Zoom") is None
        assert _bm_components("Zoom 45° · Gobo") is None
        # 보고는 된다 — 조용히 사라지지 않는다.
        assert _bm_unreadable_segments("Zoom 45° · Gobo") == ("Gobo",)

    def test_two_attributes_crammed_into_one_segment_are_refused(self):
        """구분자 없이 붙은 조각을 통째로 앞 속성의 값으로 실으면 뒤가 사라진다."""
        assert _bm_components("Zoom 45 Iris 50") is None
        # 대조군 — 구분자가 있으면 둘 다 실린다.
        assert _bm_components("Zoom 45 · Iris 50") == (("Zoom", "45"), ("Iris", "50"))


class TestTheStructureAxisDoesNotAskAboutVocabulary:
    """🔴 이 술어를 어휘 목록에 붙이면 t135 의 트립와이어가 조용히 죽는다.

    이 카드가 실제로 한 번 그렇게 만들었고 전체 스위트가 잡았다. 그 검사는
    목록을 `Prism1` 로 치환하면 BM.03 이 **열린다**는 것을 쏴서 보여주는데,
    구조 축이 어휘를 물으면 `Prism` 이 목록에서 빠진 순간 조각을 못 읽게 되어
    그 행이 **다른 사유로** 막힌다 — 증명이 사라진 것을 아무도 못 본다.

    그래서 여기서 치환을 **직접 걸고** 구조 축이 안 흔들리는 것을 잰다.
    """

    def test_the_predicate_still_reads_bm03_under_the_prism1_substitution(self, monkeypatch):
        substituted = ("Focus", "Frost", "Prism1", "Shutter")
        monkeypatch.setattr(parser_module, "_PROBE_REJECTED", substituted)
        record = _by_id()["BM.03"]
        assert _bm_components(record.value_raw) == EXPECTED["BM.03"]

    def test_and_that_row_opens_for_the_vocabulary_reason_alone(self, monkeypatch):
        """t135 의 관측 창이 이 카드 뒤에도 살아 있다는 것 — 여기서 같이 든다."""
        substituted = ("Focus", "Frost", "Prism1", "Shutter")
        monkeypatch.setattr(parser_module, "_PROBE_REJECTED", substituted)
        opened = [r.preset_id for r in _records() if r.storable]
        assert opened == ["BM.03"]

    def test_an_unknown_leading_word_is_carried_verbatim(self):
        """구조 축은 이름을 판정하지 않는다 — 아는 이름인지는 어휘 축이 답한다."""
        assert _bm_components("Zorble 5") == (("Zorble", "5"),)


class TestTheLeftoverTokenIsReportedNotSwallowed:
    def test_bm05_is_held_for_the_spare_token_as_well_as_gobo(self):
        record = _by_id()["BM.05"]
        assert record.storable is False
        assert sorted(record.hold_classes) == sorted(
            [HOLD_FAMILY_OUT_OF_SCOPE, HOLD_VALUE_NOT_MACHINE_READABLE]
        )

    def test_the_refusal_names_the_segment_it_could_not_read(self):
        """사유 문면에 조각이 **그대로** 실린다 — 「형태가 아니다」만으로는 못 고친다."""
        _storable, reasons = classify_storability("preset-bm", "Gobo OPEN · 예비")
        detail = [r.detail for r in reasons if r.hold_class == HOLD_VALUE_NOT_MACHINE_READABLE]
        assert detail and "예비" in detail[0]

    def test_the_sheet_spec_defines_no_comment_token_convention(self):
        """이 판정의 근거 — 규약이 `예비` 를 주석으로 규정했다면 보고가 아니라
        **알고 무시**하는 것이 맞다. 규정이 생기면 이 검사가 먼저 빨개진다."""
        assert SHEET_SPEC.exists()
        assert "예비" not in SHEET_SPEC.read_text(encoding="utf-8")


class TestTheClassifierActuallyCallsThisPredicate:
    """「같은 술어를 쓴다」를 **문장이 아니라 치환으로** 잰다 — 사본이면 안 움직인다."""

    def test_making_the_predicate_blind_holds_a_value_that_was_storable(self, monkeypatch):
        assert classify_storability("preset-bm", "Zoom 45°") == (True, ())
        monkeypatch.setattr(parser_module, "_bm_components", lambda _v: None)
        storable, reasons = classify_storability("preset-bm", "Zoom 45°")
        assert storable is False
        assert [r.hold_class for r in reasons] == [HOLD_VALUE_NOT_MACHINE_READABLE]

    def test_making_the_predicate_all_seeing_strips_bm05s_second_reason(self, monkeypatch):
        monkeypatch.setattr(parser_module, "_bm_components", lambda _v: (("Gobo", "x"),))
        record = _by_id()["BM.05"]
        assert record.hold_classes == (HOLD_FAMILY_OUT_OF_SCOPE,)

    def test_the_vocabulary_axis_is_untouched_by_the_new_axis(self):
        """회귀 대조군 — 어휘로 막힌 두 행의 사유는 하나 그대로다(t135 가 고정한 창)."""
        assert _by_id()["BM.03"].hold_classes == (HOLD_PROBE_REJECTED,)
        assert _by_id()["BM.04"].hold_classes == (HOLD_PROBE_REJECTED,)


class TestTheBuilderIsDeliberatelyAbsent:
    """🔴 지뢰를 **관측 가능하게** 둔다. 못 고치는 것과 안 보이는 것은 다르다.

    설계 1절이 재현한 형태다 — bm 값이 storable 인데 적용 줄이 없으면 소비 루프가
    번들을 통째로 버린다(`apply_untranslatable`). 지금은 5행이 전부 어휘로 막혀 있어
    **가려져 있을 뿐**이다. 빌더가 생기는 날 이 클래스가 빨개지고, 고치는 사람이
    8.1 절의 성분 수 검사를 빌더 쪽에도 세워야 한다는 것을 그때 읽는다.
    """

    def test_the_one_attribute_table_still_has_no_bm_cell(self):
        """표에 칸을 넣으면 `dim_level_percent` 가 bm 값을 읽으려다 `None` 을 낸다 —
        지뢰를 다른 모양으로 다시 심는 것이다(설계 3.3 절)."""
        from server.orchestrator.tools import LXSEQ_PRESET_APPLY_ATTRIBUTE

        assert "preset-bm" not in LXSEQ_PRESET_APPLY_ATTRIBUTE
        assert dict([("preset-dim", "Dimmer")]) == LXSEQ_PRESET_APPLY_ATTRIBUTE

    def test_a_storable_bm_value_still_has_no_apply_command(self):
        """지금 이 자리가 지뢰다. 값은 읽히는데(성분 1개) 명령이 없다."""
        from server.orchestrator.tools import _lxseq_preset_apply_command

        assert classify_storability("preset-bm", "Zoom 45°") == (True, ())
        assert _bm_components("Zoom 45°") == (("Zoom", "45°"),)
        placement = SimpleNamespace(kind="preset-bm", value_raw="Zoom 45°")
        assert _lxseq_preset_apply_command(placement) is None

    def test_the_control_is_that_dim_does_have_one(self):
        """대조군 — 위 `None` 이 「이 함수가 늘 None」이어서 나온 것이 아니다."""
        from server.orchestrator.tools import _lxseq_preset_apply_command

        placement = SimpleNamespace(kind="preset-dim", value_raw="85%")
        assert _lxseq_preset_apply_command(placement) is not None
