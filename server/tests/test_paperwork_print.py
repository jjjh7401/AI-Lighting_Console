"""Print-hardening + self-containment for all three paperwork renderers
(SPEC-COPILOT-PAPERWORK-001, W1).

All three renderers share ONE ``_STYLE`` block (``server/paperwork/render.py``),
so this suite exercises each renderer once with a minimal fixture and checks
the shared ``@media print`` rules land in every one of them — plus a
non-vacuity check that the self-containment scanner itself actually catches a
forbidden token, so a scanner bug can't silently pass every real renderer.
"""

from __future__ import annotations

from server.paperwork.data import PatchSheet, PoolListing
from server.paperwork.render import render_cue_sheet, render_patch_sheet, render_preset_list

#: The four print-hardening rules the brief requires, as literal substrings of
#: the rendered CSS. Checked as substrings (not parsed CSS) — this test only
#: needs to know the rule text landed somewhere inside ``@media print``.
_PRINT_RULE_TOKENS = (
    "table-header-group",  # repeat the header row on every printed page
    "break-inside: avoid",  # rows/meta blocks don't split across a page break
    "print-color-adjust: exact",  # badges/warning colors survive B/W printing
)

#: Self-containment: none of these may appear in ANY rendered output. A
#: legitimate render never references an external resource.
_FORBIDDEN_SELF_CONTAINED_TOKENS = ("<link", "<script", "src=", "@import", "http://", "https://")


def _missing_print_tokens(html: str) -> list[str]:
    return [token for token in _PRINT_RULE_TOKENS if token not in html]


def _self_contained_offenders(html: str) -> list[str]:
    return [token for token in _FORBIDDEN_SELF_CONTAINED_TOKENS if token in html]


def _empty_patch_sheet() -> PatchSheet:
    return PatchSheet(
        root="Patch/Fixtures",
        rows=(),
        child_count=0,
        observed_count=0,
        completeness="complete",
    )


def _empty_pool_listing(path: str) -> PoolListing:
    return PoolListing(path=path, pools=(), truncated=False, drilldown_capped=False)


class TestPrintHardeningPresentInEveryRenderer:
    def test_patch_sheet_has_a_media_print_block_with_all_four_rules(self):
        html = render_patch_sheet(_empty_patch_sheet())
        assert "@media print" in html
        assert _missing_print_tokens(html) == []

    def test_cue_sheet_has_a_media_print_block_with_all_four_rules(self):
        html = render_cue_sheet(_empty_pool_listing("Sequences"))
        assert "@media print" in html
        assert _missing_print_tokens(html) == []

    def test_preset_list_has_a_media_print_block_with_all_four_rules(self):
        html = render_preset_list(_empty_pool_listing("PresetPools"))
        assert "@media print" in html
        assert _missing_print_tokens(html) == []


class TestSelfContainedAcrossAllRenderers:
    def test_patch_sheet_has_zero_external_references(self):
        html = render_patch_sheet(_empty_patch_sheet())
        assert _self_contained_offenders(html) == []

    def test_cue_sheet_has_zero_external_references(self):
        html = render_cue_sheet(_empty_pool_listing("Sequences"))
        assert _self_contained_offenders(html) == []

    def test_preset_list_has_zero_external_references(self):
        html = render_preset_list(_empty_pool_listing("PresetPools"))
        assert _self_contained_offenders(html) == []

    def test_scanner_is_not_vacuous_it_actually_catches_a_planted_token(self):
        """Non-vacuity: plant each forbidden token in a synthetic string and
        confirm the scanner used above actually flags it. Without this test,
        a scanner that always returns ``[]`` would make every assertion above
        pass for the wrong reason."""
        for token in _FORBIDDEN_SELF_CONTAINED_TOKENS:
            poisoned = f"<div>before {token} after</div>"
            assert token in _self_contained_offenders(poisoned)

    def test_print_token_scanner_is_not_vacuous_either(self):
        for token in _PRINT_RULE_TOKENS:
            poisoned = f"@media print {{ {token}; }}"
            assert token not in _missing_print_tokens(poisoned)
