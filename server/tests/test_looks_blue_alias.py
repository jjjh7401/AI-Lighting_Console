"""'파란' mirrors '푸른' in every alias/mood-keyword slot that carries it.

SPEC-COPILOT-SCENE-001's title sentence used '파란' where the look library
only knew '푸른' — the two are the same colour word, but the matcher is a
keyword surface (server/looks/matching.py), not a synonym engine, so a query
written in the SPEC's own words matched nothing. The fix mirrors '파란' next
to every '푸른' occurrence (worship.yaml, ballad.yaml, edm.yaml); this file
pins that a '파란'-only query — never '푸른' — reaches each mirrored look, so
a regression that drops the mirrored alias/keyword fails here first.
"""

from __future__ import annotations

import pytest

from server.looks.loader import load_library_from_dir
from server.looks.matching import match_looks


@pytest.fixture(scope="module")
def library():
    return load_library_from_dir()


class TestBlueAliasMirrorsBlueGreen:
    def test_worship_blue_verse_is_reachable_by_the_mirrored_alias(self, library):
        result = match_looks("파란 벌스", library)
        assert result.selected is not None
        assert result.selected.look_id == "worship-blue-verse"
        assert result.fallback_reason is None

    def test_ballad_moonlight_is_reachable_by_the_mirrored_alias(self, library):
        result = match_looks("파란 밤", library)
        assert result.selected is not None
        assert result.selected.look_id == "ballad-moonlight"
        assert result.fallback_reason is None

    def test_edm_breakdown_is_reachable_by_the_mirrored_mood_keyword(self, library):
        # edm-breakdown-deep carries no '파란' alias, only the mirrored mood
        # keyword — pair it with the look's own alias 'breakdown' so the
        # query stays unambiguous, the same style test_an_alias_hit_selects_
        # its_look uses in test_looks_matching.py.
        result = match_looks("파란 브레이크다운", library)
        assert result.selected is not None
        assert result.selected.look_id == "edm-breakdown-deep"
        assert result.fallback_reason is None
