"""'파란' mirrors '푸른' in every alias/mood-keyword slot that carries it.

SPEC-COPILOT-SCENE-001's title sentence used '파란' where the look library
only knew '푸른' — the two are the same colour word, but the matcher is a
keyword surface (server/looks/matching.py), not a synonym engine, so a query
written in the SPEC's own words matched nothing. The fix mirrors '파란' next
to every '푸른' occurrence (worship.yaml, ballad.yaml, edm.yaml); this file
pins that a '파란'-only query — never '푸른' — reaches each mirrored look, and
that EVERY '푸른'-bearing entry has its twin in the SAME slot.

The per-slot invariant is the load-bearing half. The queries below travel more
than one slot: 'worship-blue-verse' answers '파란 벌스' through its alias AND
through the mood pair '파란'+'벌스', so dropping either slot alone leaves the
query test green — two doors, one net. The invariant closes that by asserting
the decision itself ("mirror '파란' beside '푸른' EVERYWHERE") rather than a
sample of its consequences, so a single dropped slot fails here, and so does a
future '푸른' added without a twin.
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


class TestEveryBlueGreenEntryHasATwin:
    """The user decision, asserted as data: mirror in EVERY slot that has it."""

    @staticmethod
    def _entries(library):
        """(look_id, slot, term) for every '푸른'-bearing alias/mood keyword."""
        return [
            (look.look_id, slot, term)
            for look in library.looks
            for slot in ("aliases", "mood_keywords")
            for term in getattr(look, slot)
            if "푸른" in term
        ]

    def test_every_blue_green_entry_has_a_blue_twin_in_the_same_slot(self, library):
        missing = [
            (look_id, slot, term)
            for look_id, slot, term in self._entries(library)
            if term.replace("푸른", "파란")
            not in getattr(next(k for k in library.looks if k.look_id == look_id), slot)
        ]
        assert missing == []

    def test_the_invariant_has_entries_to_check(self, library):
        # Non-vacuity: an empty '푸른' inventory satisfies the assertion above,
        # and would also be the shape if the asset files went missing.
        entries = self._entries(library)
        assert len(entries) == 5
        assert {slot for _id, slot, _term in entries} == {"aliases", "mood_keywords"}
        assert len({look_id for look_id, _slot, _term in entries}) == 3
