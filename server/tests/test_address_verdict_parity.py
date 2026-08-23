"""One predicate, three paths — the address verdict must not drift (card t26).

`Fit.unreadable` answers one question: was the address READ, or not? A parse
failure returns before placements are computed, so `placements` is empty; an
over-width address has placements and an error. Three call sites decide on that
distinction — the request path, the answer path, and `patch_fixtures`.

The history is why this file exists. Card t15 fixed the request path only, and
the answer path kept filing an over-width address as `unreadable_answer` —
the operator was told to rewrite a perfectly readable address. Fixing one site
again would leave the third to drift the next time.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from server.orchestrator.tools import ANSWER_CANCEL
from server.vwx.addressfit import Occupant, evaluate

from .test_vwx_addressfit import RecordingQuestionPort, _resolve

TOOLS = Path(__file__).resolve().parents[1] / "orchestrator" / "tools.py"

#: Reading fails before placements exist; over-width fails after. One input per branch.
UNREADABLE = ("세 점 일", 12)
OVER_WIDTH = ("1.506", 20)
FITS = ("1.001", 12)


def test_the_predicate_separates_unread_from_too_wide():
    """The distinction the three paths share, asserted once at its source."""
    unread = evaluate(UNREADABLE[0], count=1, width=UNREADABLE[1], occupants=())
    wide = evaluate(OVER_WIDTH[0], count=1, width=OVER_WIDTH[1], occupants=())
    fine = evaluate(FITS[0], count=1, width=FITS[1], occupants=())

    assert unread.unreadable is True
    assert wide.unreadable is False, "over-width was read — placements were computed"
    assert fine.unreadable is False


def test_over_width_is_the_input_that_makes_the_predicate_load_bearing():
    """Both branches carry an error; only `placements` tells them apart.

    Without this, a site could test `error` alone and still look correct.
    """
    unread = evaluate(UNREADABLE[0], count=1, width=UNREADABLE[1], occupants=())
    wide = evaluate(OVER_WIDTH[0], count=1, width=OVER_WIDTH[1], occupants=())

    assert unread.error and wide.error, "both must carry an error, else the test is vacuous"
    assert not unread.placements
    assert wide.placements


def _call_sites() -> list[str]:
    """Every line in tools.py that asks the shared predicate."""
    text = TOOLS.read_text(encoding="utf-8")
    return [line.strip() for line in text.splitlines() if re.search(r"\.unreadable\b", line)]


def test_three_paths_ask_the_shared_predicate():
    """Vacuity guard: finding zero sites must fail, not pass quietly."""
    sites = _call_sites()
    assert len(sites) == 3, f"expected request/answer/patch_fixtures, found {len(sites)}: {sites}"


def test_no_path_decides_readability_from_error_alone():
    """The shape that caused the defect: `elif <fit>.error:` deciding unreadable."""
    text = TOOLS.read_text(encoding="utf-8")
    offenders = [
        line.strip()
        for line in text.splitlines()
        if re.search(r"(if|elif)\s+\w*(fit|rechecked)\.error\s*:", line)
    ]
    assert offenders == [], offenders


@pytest.mark.parametrize(
    "requested,width,occupants",
    [
        (UNREADABLE[0], UNREADABLE[1], ()),
        (OVER_WIDTH[0], OVER_WIDTH[1], ()),
        (FITS[0], FITS[1], ()),
        ("1.001", 12, (Occupant(universe=1, address=1),)),
    ],
)
def test_the_three_failure_shapes_are_exclusive_and_total(requested, width, occupants):
    """The contract the docstring states: exactly one shape per failed Fit.

    Without this, a fourth shape could appear and every label site would guess.
    """
    fit = evaluate(requested, count=1, width=width, occupants=occupants)
    if fit.ok:
        assert not fit.unreadable
        return
    shapes = [
        fit.unreadable,
        bool(fit.error) and bool(fit.placements) and not fit.collisions,
        bool(fit.collisions),
    ]
    assert sum(shapes) == 1, (requested, shapes, fit.error, len(fit.placements))


class TestBothReadPathsLabelTheSameInputTheSameWay:
    """The predicate is shared; the branch that consumes it must be too.

    The tests above pin `Fit.unreadable`. They do not watch where a path goes
    AFTER asking it — so deleting the answer path\x27s `does_not_fit` branch left
    the suite green while «0대와 겹친다» came back (lead, mutation on #93).
    These two drive the real handler and compare the label it emits.
    """

    #: One occupant sitting on the requested address, so the tool asks instead
    #: of settling — the only way to reach the answer path.
    OCCUPIED = (Occupant(universe=3, address=1, name="이미 있는 장비"),)

    def test_the_request_path_calls_an_over_width_address_does_not_fit(self):
        payload = _resolve(
            RecordingQuestionPort(ANSWER_CANCEL),
            address=OVER_WIDTH[0],
            count=1,
            width=OVER_WIDTH[1],
            occupants=(),
        )

        assert payload["status"] == "does_not_fit"

    def test_the_answer_path_calls_the_same_address_the_same_thing(self):
        """The regression the lead found: this branch had no guard at all."""
        payload = _resolve(
            RecordingQuestionPort(OVER_WIDTH[0]),
            address="3.001",
            count=1,
            width=OVER_WIDTH[1],
            occupants=self.OCCUPIED,
        )

        assert payload["answered_address"] == OVER_WIDTH[0]
        assert payload["status"] == "does_not_fit", payload.get("guidance")
        assert payload["status"] != "still_occupied"
        assert payload["status"] != "unreadable_answer"

    def test_the_answer_path_still_names_an_unreadable_answer(self):
        """Control: moving the over-width case must not drag this one with it."""
        payload = _resolve(
            RecordingQuestionPort(UNREADABLE[0]),
            address="3.001",
            count=1,
            width=UNREADABLE[1],
            occupants=self.OCCUPIED,
        )

        assert payload["status"] == "unreadable_answer"
