"""Card t370 — three new movement candidates.

Source: docs/research/ma3-effects/17-fei-hu-ma2-video-patterns.md §6/§9.

`chase-horizontal`, `chase-bounce-run`, `sweep-vshape-swing` are added to
`server/fx/library/movement.yaml` on the doc's own "relatively safe" starting
set: Pan/Tilt/Dimmer only, no beam attribute — so nothing here waits on the
profile-verification layer §5.5 says a beam entry would need.

`test_fx_library.py` already runs its exhaustive census over every asset in
the directory, so these three are already covered by that suite's per-entry
checks (two steps, one attribute set, no repeated value, Korean alias/mood
keyword, a single speed source, a mood-table speed band), and
`test_scene_matching.py::TestFxPatternIdInference` already covers the
fx_id-carries-its-pattern-token convention these three now also follow. This
module adds the things those do not:

* the CARD'S OWN acceptance bar — each entry actually renders a real phaser
  bundle (a `Step 2` line, and every declared modifier axis actually read
  back rather than silently unemitted);
* that a one-step regression on any of the three is structurally impossible;
* that the doc's own natural-language phrasings (§8) actually route through
  `match_fx` to the right entry — NOT merely that the alias string exists.

The last point matters because `resolve_pattern` (matching.py) treats a bare
pattern word (스윕/웨이브/체이스/...) as a hard axis: a query containing one
narrows candidates to that SAME `pattern` band before any alias is scored, so
an alias containing a *different* pattern's word used to be present on an entry
and still unreachable through it (e.g. `sweep-club-xwave`'s own alias
"엑스축 웨이브" resolved to `wave-soft-rise` instead, because 웨이브 is itself a
`wave`-pattern word).

카드 t411 이 그 계열을 닫았다: `match_fx` 는 이름을 통째로 맞힌 항목이 딱 하나면
패턴 좁히기보다 **먼저** 그 항목을 고른다. 그래서 아래 `좌우로 달리게` 시험은
「못 찾는 게 낫다」에서 「자기 항목을 찾는다」로 바뀌었다. 패턴 판독 자체는
그대로이고(그 시험이 여전히 `pattern == "sweep"` 을 단언한다), 좁히기가 지는 것은
정확 일치라는 더 강한 증거가 있을 때뿐이다.

Nothing here touches a console: static repo data, the real loader, the real
matcher, and the real bundle builder — the same production path
`server/fx/tools.py` uses.
"""

from __future__ import annotations

import pytest

from server.fx.instantiate import build_fx_bundle
from server.fx.loader import FxSchemaError, load_library, load_library_from_dir
from server.fx.matching import match_fx
from server.fx.schema import MIN_STEPS

NEW_FX_IDS = ("chase-horizontal", "chase-bounce-run", "sweep-vshape-swing")

# doc §8 — the natural-language phrasings the card asked to be reachable.
EXPECTED_ALIASES = {
    "chase-horizontal": ("수평 체이스", "좌우로 달리게"),
    "chase-bounce-run": ("바운스 체이스", "통통 튀게", "런 이펙트"),
    "sweep-vshape-swing": ("V자로 흔들어", "대칭 팬 스윙"),
}

# The doc's own axis note per candidate (§6 "구현 메모"), read here as the
# non-empty declared axes that actually distinguish these three from the
# vanilla `sweep-*` / `chase-*` entries above them in the file.
EXPECTED_AXES = {
    "chase-horizontal": ("phase_from_x", "phase_to_x"),
    "chase-bounce-run": ("phase_from", "phase_to", "reverse", "x_wings"),
    "sweep-vshape-swing": ("relative", "x_wings"),
}

# Phrasings that `match_fx` is expected to route to the entry it names,
# uniquely and without a fallback. This is a STRICT subset of the doc's own
# phrasing list — see the module docstring for the one phrasing left out
# (좌우로 달리게) and why.
EXPECTED_MATCHES = {
    "수평 체이스": "chase-horizontal",
    "바운스 체이스": "chase-bounce-run",
    "통통 튀게": "chase-bounce-run",
    "런 이펙트": "chase-bounce-run",
    "V자로 흔들어": "sweep-vshape-swing",
    "대칭 팬 스윙": "sweep-vshape-swing",
}


@pytest.fixture(scope="module")
def library():
    """The real shipped library, loaded exactly the way production loads it."""
    return load_library_from_dir()


class TestTheThreeCandidatesAreShipped:
    @pytest.mark.parametrize("fx_id", NEW_FX_IDS)
    def test_the_entry_exists(self, library, fx_id):
        assert library.by_id(fx_id).fx_id == fx_id

    @pytest.mark.parametrize("fx_id", NEW_FX_IDS)
    def test_the_entry_declares_at_least_two_steps(self, library, fx_id):
        fx = library.by_id(fx_id)
        assert len(fx.steps) >= MIN_STEPS

    @pytest.mark.parametrize("fx_id", NEW_FX_IDS)
    def test_the_entrys_declared_axes_are_the_ones_the_doc_asked_for(self, library, fx_id):
        fx = library.by_id(fx_id)
        for axis in EXPECTED_AXES[fx_id]:
            value = getattr(fx, axis)
            assert value is not None and value is not False, (
                f"{fx_id} was expected to declare {axis!r} per the doc's own axis note"
            )

    @pytest.mark.parametrize("fx_id", NEW_FX_IDS)
    def test_the_doc_phrasings_are_present_as_aliases(self, library, fx_id):
        fx = library.by_id(fx_id)
        for phrase in EXPECTED_ALIASES[fx_id]:
            assert phrase in fx.aliases, f"{fx_id} is missing the doc phrasing {phrase!r}"


class TestTheBuiltBundleActuallyPhasers:
    """The card's own acceptance bar: a real bundle, a real `Step 2` line."""

    @pytest.mark.parametrize("fx_id", NEW_FX_IDS)
    def test_the_bundle_contains_a_step_2_line(self, library, fx_id):
        fx = library.by_id(fx_id)
        commands = build_fx_bundle(fx, group=11, sequence=12).commands
        assert "Step 2" in commands, f"{fx_id} bundle carries no Step 2 line: {commands}"

    @pytest.mark.parametrize("fx_id", NEW_FX_IDS)
    def test_the_bundle_reports_the_full_step_count(self, library, fx_id):
        fx = library.by_id(fx_id)
        plan = build_fx_bundle(fx, group=11, sequence=12)
        assert plan.step_count == len(fx.steps) >= MIN_STEPS

    @pytest.mark.parametrize("fx_id", NEW_FX_IDS)
    def test_every_declared_matricks_axis_actually_emits_a_line(self, library, fx_id):
        # The design note left in movement.yaml for `chase-bounce-run`: a
        # modifier axis that is declared but never read back is silent on
        # stage even though every command line answers ok:true (the module's
        # own @MX:WARN).
        fx = library.by_id(fx_id)
        plan = build_fx_bundle(fx, group=11, sequence=12)
        for axis, literal in (
            ("phase_from_x", "PhaseFromX"),
            ("phase_to_x", "PhaseToX"),
            ("x_wings", "XWings"),
        ):
            declared = getattr(fx, axis)
            if declared is None:
                continue
            matching = [c for c in plan.commands if f"MAtricks '{literal}'" in c]
            assert matching, f"{fx_id} declares {axis}={declared}, expected a {literal} line"
        if fx.reverse:
            assert any("Thru -" in c for c in plan.commands), (
                f"{fx_id} declares reverse=true but no reversed Thru line was emitted"
            )


class TestOneStepIsStructurallyImpossible:
    """REQ trap #1 (00-summary-and-plan.md §1.4): a one-step entry is a silent
    no-op, not a smaller phaser — MIN_STEPS is the mechanical wall, not a
    convention any single asset can opt out of.
    """

    @pytest.mark.parametrize("fx_id", NEW_FX_IDS)
    def test_a_one_step_variant_of_each_new_entry_is_rejected_by_the_loader(self, library, fx_id):
        fx = library.by_id(fx_id)
        one_step_data = {
            "schema_version": 1,
            "fx": [
                {
                    "fx_id": fx.fx_id,
                    "display_name": fx.display_name,
                    "pattern": fx.pattern,
                    "steps": [{"Pan": -18}],
                }
            ],
        }
        with pytest.raises(FxSchemaError, match="steps?"):
            load_library(one_step_data, source="t370 one-step regression probe")


class TestTheDocPhrasingsActuallyRoute:
    """`match_fx`, not just `in fx.aliases` — a reachable alias is a routed
    one, and the two are not the same claim.
    """

    @pytest.mark.parametrize("query,expected_id", sorted(EXPECTED_MATCHES.items()))
    def test_the_phrase_selects_the_entry_it_names(self, library, query, expected_id):
        result = match_fx(query, library)
        assert result.selected is not None, (
            f"{query!r} was expected to select {expected_id!r}, got fallback "
            f"{result.fallback_reason!r}"
        )
        assert result.selected.fx_id == expected_id

    def test_the_former_gap_now_routes_to_its_own_entry(self, library):
        # 좌우로 달리게 is `chase-horizontal`'s own doc alias, but it also
        # contains 좌우 — a `sweep`-pattern axis word — so `resolve_pattern`
        # narrowed the candidate set to `sweep` entries before the alias was
        # ever scored, and `chase-horizontal` (pattern: chase) never entered
        # that set. This test used to hold the weaker bar "an honest miss over
        # a confident wrong answer", asserting the query must NOT resolve to
        # `chase-horizontal`.
        #
        # 카드 t411 이 그 전제를 뒤집었다: 정확 일치는 패턴 좁히기보다 먼저 이긴다
        # (`match_fx` 의 exact 경로). 사람이 그 항목의 이름을 통째로 적었으므로
        # `chase-horizontal` 은 「틀린 답」이 아니라 **바로 그 항목**이다. 그래서
        # 이 시험의 바는 「못 찾는 게 낫다」에서 「자기 항목을 찾는다」로 올라갔다.
        # 패턴 판독 자체는 그대로다 — 아래에서 여전히 sweep 으로 읽는다.
        result = match_fx("좌우로 달리게", library)
        assert result.pattern == "sweep"
        assert result.selected is not None
        assert result.selected.fx_id == "chase-horizontal"
