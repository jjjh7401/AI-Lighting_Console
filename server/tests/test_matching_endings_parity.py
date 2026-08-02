"""Upstream vocabulary extension — the ending list and its two copies.

Origin: docs/proposals/2026-08-02-upstream-vocabulary-extension-proposal.md.
The SCENE headline sentence ("파란 백라이트가 천천히 웨이브하는 씬 만들어줘") fell
through both axes because 하는 (the adnominal form of 하다-verbs) was missing
from the closed `_ENDINGS` list, and 파란 was missing from the look assets.

Two structural facts this file pins:

1. `_ENDINGS` exists as an intentional per-package copy in fx and scene
   (the established precedent from the SCENE parallel wave — "각자 자기 본을
   가진 확립된 선례"). Nothing forced the copies to stay equal until now;
   decision ① of the proposal chose "edit both + a parity guard" over a
   cross-package import of a private constant. This guard IS that output:
   if the tuples ever diverge, the two surfaces (`find_fx` / `find_scene`)
   start answering the same sentence differently, silently.

2. The extension is exactly one entry, 하는 — measured, not a class of
   endings ("측정 없이 부류를 넓히지 말 것"). The queries below therefore use
   the 웨이브하는 surface form ONLY, never the bare stem, so that removing
   하는 from either copy kills them (mutation material by construction).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from server.fx import matching as fx_matching
from server.fx.loader import load_library_from_dir as load_fx_library_from_dir
from server.fx.matching import match_fx, resolve_pattern
from server.looks import matching as looks_matching
from server.scene import matching as scene_matching
from server.scene.loader import load_library_from_dir as load_scene_library_from_dir
from server.scene.matching import BOTH_MATCHED, match_scene

SERVER_DIR = Path(__file__).resolve().parents[1]

HEADLINE = "파란 백라이트가 천천히 웨이브하는 씬 만들어줘"


@pytest.fixture(scope="module")
def shipped_fx_library():
    return load_fx_library_from_dir(SERVER_DIR / "fx" / "library")


@pytest.fixture(scope="module")
def shipped_scene_library():
    return load_scene_library_from_dir(SERVER_DIR / "scene" / "library")


class TestEndingListParity:
    """Decision ①: the copies are legitimate, their divergence is not."""

    def test_fx_and_scene_ending_lists_are_identical_including_order(self):
        # Order matters: both tuples are joined into a regex alternation, so
        # an equal set with a different order is still a different matcher
        # wherever one ending is a prefix of another.
        assert fx_matching._ENDINGS == scene_matching._ENDINGS

    def test_the_parity_guard_is_not_vacuous_and_the_list_stays_closed(self):
        # Non-vacuity: the guard above passes trivially on two empty tuples.
        assert "하는" in fx_matching._ENDINGS
        # EXACT, not a lower bound. The list is CLOSED and the extension was
        # exactly one measured entry; a lower bound catches shrinkage but lets
        # the list GROW silently, which is the failure mode the proposal named
        # ("측정 없이 부류를 넓히지 말 것"). Widening it now costs one edit here,
        # which is the decision record the closed set is supposed to have.
        assert len(fx_matching._ENDINGS) == 8


class TestParticleListParity:
    """Candidate ⑦ — the OTHER copied list, which had no equality net at all.

    ``_PARTICLES`` exists three times (fx, scene, looks) and all three are
    byte-identical today. That is exactly SCENE lesson 16: the assets happen
    to agree, so deleting the agreement costs nothing TODAY and breaks
    silently in a future authoring session. The only net that existed was
    one-directional and behavioural — ``test_fx_matching.py``'s
    ``TestKoreanParticleParityWithLooks`` walks the looks list through the fx
    matcher — and the scene copy sat outside every net.

    Divergence is not forbidden by fiat; it is forbidden by DEFAULT. A future
    package that genuinely needs its own particle edits this guard on purpose,
    which is the record the copies never had.
    """

    def test_all_three_particle_lists_are_identical_including_order(self):
        assert fx_matching._PARTICLES == scene_matching._PARTICLES
        assert fx_matching._PARTICLES == looks_matching._PARTICLES

    def test_the_three_way_guard_is_not_vacuous_and_the_list_stays_closed(self):
        # Non-vacuity: three empty tuples would satisfy the assertions above.
        # The longest-first ordering matters too — 으로 before 로 is what keeps
        # 으로 from being consumed as 로 in the regex alternation.
        particles = fx_matching._PARTICLES
        assert len(particles) == 28
        assert particles.index("으로") < particles.index("로")

    def test_the_scene_surface_handles_every_looks_particle(self, shipped_scene_library):
        # The behavioural half, extended to the copy that had no net. The fx
        # half already lives in test_fx_matching.py; scene is added here rather
        # than there so both halves of "문이 둘이면 그물도 둘" are visible.
        for particle in looks_matching._PARTICLES:
            axis = match_scene(f"웨이브{particle}", shipped_scene_library).fx.selected
            assert axis == "wave-soft-rise", particle

    def test_only_the_looks_package_lacks_its_own_ending_list(self):
        # Why _ENDINGS is a two-way guard while _PARTICLES is three-way: LOOKS
        # carries no ending axis at all (proposal §2) — fx and scene both have
        # one, and the test two above asserts they agree. Pinned so that a
        # future looks _ENDINGS arrives with a decision, not by accident.
        assert not hasattr(looks_matching, "_ENDINGS")
        assert hasattr(fx_matching, "_ENDINGS")
        assert hasattr(scene_matching, "_ENDINGS")


class TestHaneunEnding:
    """The one measured extension: 웨이브하는 must reach the wave vocabulary."""

    def test_the_adnominal_form_resolves_to_the_wave_pattern(self):
        # 웨이브하는, never bare 웨이브: this assertion must die when 하는 is
        # removed from the fx copy (mutation material, proposal §4.5).
        assert resolve_pattern("웨이브하는") == "wave"

    def test_the_adnominal_form_selects_the_shipped_wave_fx(self, shipped_fx_library):
        result = match_fx("웨이브하는", shipped_fx_library)
        assert result.selected is not None
        assert result.selected.fx_id == "wave-soft-rise"

    def test_the_scene_fx_axis_gives_the_same_answer_as_find_fx(
        self, shipped_fx_library, shipped_scene_library
    ):
        # The property that killed option A in the SCENE cycle: the two
        # surfaces must not answer the same sentence differently. Now pinned.
        fx_answer = match_fx("웨이브하는", shipped_fx_library).selected.fx_id
        scene_axis = match_scene("웨이브하는", shipped_scene_library).fx.selected
        assert scene_axis == fx_answer == "wave-soft-rise"

    def test_an_ending_only_attaches_it_does_not_open_the_list(self):
        # The list stays closed: 하는 as a suffix of another word must not
        # let unrelated stems through (the 쓸어/쓸어담아 cost the fx comment
        # names). 웨이브하는구나 carries extra syllables past the ending.
        assert resolve_pattern("웨이브하는구나") is None

    def test_exactly_one_suffix_attaches_not_a_run_of_them(self):
        # `_SUFFIX` is `(?:...)?` — at most ONE. Relaxing it to `*` passes
        # every other assertion in this file while letting a stacked run of
        # particles and endings through, which is the same "open rule"
        # hazard the closed lists exist to avoid.
        assert resolve_pattern("웨이브로는") is None
        assert resolve_pattern("웨이브하는줘") is None
        # Non-vacuity: each of those stems resolves with ONE suffix.
        assert resolve_pattern("웨이브로") == "wave"
        assert resolve_pattern("웨이브하는") == "wave"


class TestHeadlineSentence:
    """Acceptance §4.1: the spec's own example finally executes."""

    def test_the_headline_sentence_matches_both_axes(self, shipped_scene_library):
        result = match_scene(HEADLINE, shipped_scene_library)
        assert result.kind == BOTH_MATCHED
        assert result.look.selected == "ballad-moonlight"
        assert result.fx.selected == "wave-soft-rise"
        assert result.selected is not None
        assert result.selected.scene_id == "ballad-moonlight-rise"

    def test_the_blue_twin_words_answer_identically(self, shipped_scene_library):
        # 파란 was mirrored beside 푸른 everywhere (user decision ③). The
        # mirror is faithful exactly when the two sentences are one answer.
        blue = match_scene(HEADLINE, shipped_scene_library)
        original = match_scene(HEADLINE.replace("파란", "푸른"), shipped_scene_library)
        assert blue.kind == original.kind == BOTH_MATCHED
        assert blue.selected.scene_id == original.selected.scene_id
