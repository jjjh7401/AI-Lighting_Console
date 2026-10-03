"""SPEC-LDRENDER-001 M6(REQ-LDRENDER-012, 카드 t501) — 효과 요청/허용/송신
3계 수치. ``song_cue_render._fx_report_counts`` (산출) +
``server.web.session._fx_report_note`` (회신 문면)를 직접 겨눈다.
"""

from __future__ import annotations

from dataclasses import dataclass

from server.design.song_cue_composer import CueFxData
from server.design.song_cue_render import _fx_report_counts
from server.web.session import _fx_report_note


@dataclass(frozen=True)
class _Dimmer:
    key_pct: float | None = 60.0
    blackout: bool = False


@dataclass(frozen=True)
class _Cue:
    kind: str
    cue_name: str
    dimmer: _Dimmer
    fx: CueFxData


@dataclass(frozen=True)
class _Bundle:
    cues: tuple


def _cue(cue_name: str, *, requested: tuple[str, ...], permitted: tuple[str, ...]) -> _Cue:
    fx = CueFxData(requested=requested, permitted=permitted, disabled=(), density=0, axis_budget=0)
    return _Cue(kind="section", cue_name=cue_name, dimmer=_Dimmer(), fx=fx)


class TestFxReportCounts:
    def test_a_song_with_no_fx_requests_counts_all_zero(self):
        bundle = _Bundle(cues=(_cue("인트로", requested=(), permitted=()),))
        assert _fx_report_counts(bundle, {}) == (0, 0, 0)

    def test_requested_counts_everything_the_design_layer_asked_for(self):
        bundle = _Bundle(
            cues=(
                _cue("벌스", requested=("slow pan",), permitted=()),
                _cue("후렴", requested=("dimmer chase", "pan sweep"), permitted=("dimmer chase",)),
            )
        )
        requested, permitted, _sent = _fx_report_counts(bundle, {})
        assert requested == 3  # slow pan + dimmer chase + pan sweep
        assert permitted == 1  # D레벨 예산이 하나만 허용

    def test_sent_requires_both_budget_and_a_resolved_pool_slot(self):
        # "후렴" -> "Wave CM" (coordinator table). Permitted but unresolved:
        # not sent. Permitted and resolved: sent.
        bundle = _Bundle(
            cues=(
                _cue("후렴", requested=("dimmer chase",), permitted=("dimmer chase",)),
                _cue("벌스", requested=("slow pan",), permitted=("slow pan",)),
            )
        )
        # Only "Wave CM" (the 후렴 cue's label) resolves; "Breathe Warm" (벌스) does not.
        _requested, _permitted, sent = _fx_report_counts(bundle, {"Wave CM": (4, 7)})
        assert sent == 1

    def test_a_permitted_cue_with_no_matching_catalog_label_is_not_sent(self):
        bundle = _Bundle(cues=(_cue("장면1", requested=("x",), permitted=("x",)),))
        # "장면1" never maps to a catalog label.
        requested, permitted, sent = _fx_report_counts(bundle, {"Wave CM": (4, 7)})
        assert (requested, permitted, sent) == (1, 1, 0)

    def test_sent_matches_the_req_010_gate_byte_for_byte(self):
        """REQ-LDRENDER-012(모듈 독스트링) — 이 함수의 "sent" 셈은
        ``_phaser_cue_value_lines`` 의 REQ-010 게이트(``cue.fx.permitted``
        비어있지 않음 + 라벨 해석 + 풀 슬롯 해석)와 같은 조건이어야 한다.
        permitted=() 면 라벨·풀이 둘 다 갖춰져도 sent=0 이다 — 두 곳이
        갈리면 보고가 실제 송신과 다른 숫자를 주장한다."""
        bundle = _Bundle(cues=(_cue("후렴", requested=("dimmer chase",), permitted=()),))
        requested, permitted, sent = _fx_report_counts(bundle, {"Wave CM": (4, 7)})
        assert (requested, permitted, sent) == (1, 0, 0)


class TestFxReportNote:
    def test_a_song_with_no_fx_requests_gets_no_note(self):
        bundle = _Bundle(cues=(_cue("인트로", requested=(), permitted=()),))
        assert _fx_report_note(bundle, {}) == ""

    def test_a_none_bundle_gets_no_note(self):
        assert _fx_report_note(None, {}) == ""

    def test_the_three_numbers_appear_distinctly(self):
        cue = _cue("후렴", requested=("dimmer chase", "pan sweep"), permitted=("dimmer chase",))
        bundle = _Bundle(cues=(cue,))
        note = _fx_report_note(bundle, {"Wave CM": (4, 7)})
        assert "요청 2" in note
        assert "허용 1" in note
        assert "송신 1" in note
