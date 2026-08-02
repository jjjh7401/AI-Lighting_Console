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

    def test_the_parity_guard_is_not_vacuous(self):
        # Non-vacuity: the guard above passes trivially on two empty tuples.
        assert "하는" in fx_matching._ENDINGS
        assert len(fx_matching._ENDINGS) >= 8


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
