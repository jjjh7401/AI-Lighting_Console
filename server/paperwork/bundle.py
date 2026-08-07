"""Handover pack: patch sheet + cue sheet + preset list + magic sheet + index,
one folder.

The proposal's payoff ("인수인계 용이") was never in the sheets themselves —
those already existed (T-J) — it was the LAST step: today they land as
unrelated files and the person taking over a show has no way to know which to
open first, or that one of them only saw HALF the rig. This module adds no new
observation axis; it calls the existing builders and writes one more file
(``index.html``) that links to them and states, up front, how much of the
console each one actually saw.

**Partial failure is not total failure.** A missing ``property_port`` or an
unreadable fixture inventory only takes down the patch sheet; a sequences or
preset-pools pool the console never answered only takes down that one sheet.
Every other document still generates, and the index records WHY the missing
one is missing — with one of the closed :data:`HANDOVER_STATUSES` words, never
an ad hoc string composed inline (see ``.moai/state/handoff/p0-shared-
contract.md`` §2.1: an unread value must say it was not read, never guess).

This module never imports the OSC send surface or any execution port —
``server/tests/test_paperwork_boundary.py`` sweeps every file in this package
for exactly that.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from html import escape
from pathlib import Path

from server.orchestrator.tools import DEFAULT_RIG_CONTEXT_PATHS
from server.paperwork.data import (
    MagicSheet,
    PatchSheet,
    PoolListing,
    build_cue_sheet,
    build_magic_sheet,
    build_patch_sheet,
    build_preset_list,
)
from server.paperwork.output import resolve_handover_dir, write_paperwork_html
from server.paperwork.render import (
    render_cue_sheet,
    render_magic_sheet,
    render_patch_sheet,
    render_preset_list,
)
from server.prechk.footprint import WalkOutcome
from server.prechk.inventory import InventoryReadError

# Closed status vocabulary (§2.1 of the shared contract) — a document's
# ``status`` is always one of exactly these three words, never composed
# ad hoc inside a builder below.
STATUS_GENERATED = "생성됨"
STATUS_QUERY_FAILED = "조회 실패"
STATUS_UNWIRED = "미배선"
HANDOVER_STATUSES = (STATUS_GENERATED, STATUS_QUERY_FAILED, STATUS_UNWIRED)

_INDEX_FILENAME = "index.html"
_PATCH_SHEET_FILENAME = "patch_sheet.html"
_CUE_SHEET_FILENAME = "cue_sheet.html"
_PRESET_LIST_FILENAME = "preset_list.html"
_MAGIC_SHEET_FILENAME = "magic_sheet.html"


@dataclass(frozen=True)
class HandoverDocument:
    """One document's outcome inside the pack — always present, generated or
    not, so the index can name every document it was supposed to produce."""

    kind: str
    title: str
    filename: str
    path: Path | None
    status: str
    detail: str | None = None


@dataclass(frozen=True)
class HandoverPack:
    """The whole handover folder: the index plus what became of each of the
    three documents it links to."""

    index_path: Path
    documents: tuple[HandoverDocument, ...]
    generated_at: str


class _InventoryAdapter:
    """The two reads ``build_patch_sheet`` needs, joined from the caller's
    ``state_port``/``property_port``.

    Mirrors ``server.orchestrator.tools``'s handler-local ``_InventoryPort`` —
    duplicated rather than imported, because that class lives inside a
    closure (not a module export) and this package must not gain a
    module-level import of ``server.orchestrator.tools`` beyond the one
    constant it already uses (see the deferred-import notes on
    ``build_patch_sheet``'s tool handler for why the reverse edge would
    cycle).
    """

    def __init__(self, state, prop) -> None:
        self._state = state
        self._prop = prop

    def query_state(self, path: str) -> dict:
        return self._state.query_state(path)

    def query_property(self, path: str, property_name: str) -> dict:
        return self._prop.query_property(path, property_name)


def _patch_sheet_document(
    state_port, property_port, walk: WalkOutcome | None
) -> tuple[HandoverDocument, PatchSheet | None]:
    doc = HandoverDocument(
        kind="patch_sheet",
        title="Patch Sheet",
        filename=_PATCH_SHEET_FILENAME,
        path=None,
        status=STATUS_UNWIRED,
        detail=None,
    )
    if property_port is None:
        # Same missing-capability wording precheck_patch/build_patch_sheet's
        # tool handler use — never silently drop the document, and never
        # answer "zero fixtures" when the capability is simply unwired.
        return (
            replace(
                doc,
                detail=(
                    "property reads are not wired — build_toolset needs property_port "
                    "(or a state_port that also implements query_property)"
                ),
            ),
            None,
        )
    try:
        sheet = build_patch_sheet(_InventoryAdapter(state_port, property_port), walk=walk)
    except InventoryReadError as error:
        return (
            replace(
                doc, status=STATUS_QUERY_FAILED, detail=f"fixture inventory unreadable: {error}"
            ),
            None,
        )
    return replace(doc, status=STATUS_GENERATED), sheet


def _pool_listing_document(
    listing: PoolListing, *, kind: str, title: str, filename: str
) -> HandoverDocument:
    if listing.unavailable_reason is not None:
        detail = listing.unavailable_reason
        if listing.unavailable_detail:
            detail = f"{listing.unavailable_reason}: {listing.unavailable_detail}"
        return HandoverDocument(
            kind=kind,
            title=title,
            filename=filename,
            path=None,
            status=STATUS_QUERY_FAILED,
            detail=detail,
        )
    return HandoverDocument(
        kind=kind, title=title, filename=filename, path=None, status=STATUS_GENERATED, detail=None
    )


def _magic_sheet_document(
    state_port, property_port, paths: dict
) -> tuple[HandoverDocument, MagicSheet | None]:
    doc = HandoverDocument(
        kind="magic_sheet",
        title="Magic Sheet (reduced)",
        filename=_MAGIC_SHEET_FILENAME,
        path=None,
        status=STATUS_UNWIRED,
        detail=None,
    )
    if property_port is None:
        # Coordinates live ONLY in properties, so an unwired property port
        # would produce a plan view that reads like a rig with no fixtures.
        # Recorded as unwired rather than generated-and-empty.
        return (
            replace(
                doc,
                detail=(
                    "property reads are not wired — build_toolset needs property_port "
                    "(or a state_port that also implements query_property)"
                ),
            ),
            None,
        )
    # No STATUS_QUERY_FAILED branch: build_magic_sheet degrades per SECTION,
    # so a dead group pool still yields a sheet. The per-section reasons ride
    # inside the document itself and the shortfall reaches the index through
    # _incompleteness_lines below.
    sheet = build_magic_sheet(
        _InventoryAdapter(state_port, property_port),
        groups_path=paths.get("groups", DEFAULT_RIG_CONTEXT_PATHS["groups"]),
        preset_pools_path=paths.get("preset_pools", DEFAULT_RIG_CONTEXT_PATHS["preset_pools"]),
        fixtures_path=paths.get("fixtures", DEFAULT_RIG_CONTEXT_PATHS["fixtures"]),
    )
    return replace(doc, status=STATUS_GENERATED), sheet


def _incompleteness_lines(
    patch_sheet: PatchSheet | None,
    cue_listing: PoolListing,
    preset_listing: PoolListing,
    magic_sheet: MagicSheet | None = None,
) -> tuple[str, ...]:
    """The facts that must reach the index's FIRST screen (§2.1): a reader
    who only skims the top must still learn that a listing is partial before
    mistaking it for the whole rig.

    NOT unified in WORDING with SPEC-COPILOT-TRUNCATE-001's structural
    disclosure, and the reason is recorded here so it is not re-raised as an
    inconsistency. That SPEC moves the KEY (``fixtures`` ->
    ``partial_fixtures`` + ``missing``) so a machine reading JSON cannot
    consume a partial read without noticing. ``build_magic_sheet`` DOES consume
    that reply and branches on exactly that key — the contract is honoured at
    the data layer, not paraphrased away.

    What is not carried over is the MECHANISM, because an index is read by a
    person and a person has no key to miss. The HTML form of "an incomplete
    read must not be skimmable as a complete one" is PLACEMENT: first screen,
    above the document list. What IS carried over is the part that survives the
    change of medium — REQ-TRUNCATE-004's rule that the shortfall is stated as
    arithmetic, never as an adjective. Hence the magic-sheet line below prints
    expected/received/unseen rather than the word "incomplete".

    The two remaining sheets predate that reply shape and reach completeness
    through the older ``server.prechk.inventory`` channel, so their lines keep
    that channel's vocabulary rather than borrowing one they cannot back.
    """
    lines: list[str] = []
    if patch_sheet is not None:
        line = (
            f"Patch Sheet — {patch_sheet.observed_count}/{patch_sheet.child_count}건 관측 "
            f"(completeness: {patch_sheet.completeness})"
        )
        # A reader who sees "4/4건 관측" next to "incomplete" cannot tell WHY, and
        # the natural reading — "the counts agree, so it is really complete" — is
        # exactly the misreading this summary exists to prevent. The counts agreeing
        # does NOT make the listing whole: `read_inventory` refuses `complete` when
        # the root enumeration came back SHORT even after per-slot recovery filled
        # the gap, and it also refuses when a whitelisted property could not be read
        # (server/prechk/inventory.py — `complete = not root_was_short and
        # missing_count == 0`). Neither cause is reachable from `PatchSheet`, so the
        # line names both possibilities rather than inventing the one that applies.
        if (
            patch_sheet.completeness != "complete"
            and patch_sheet.observed_count == patch_sheet.child_count
        ):
            line += (
                " — 열거 수는 일치하나 전량으로 볼 수 없다: 루트 열거가 절단됐거나"
                " 프로퍼티 판독에 실패했다. precheck_patch가 그 원인을 판정한다"
            )
        lines.append(line)
    lines.append(
        f"Cue Sheet — truncated={cue_listing.truncated}, "
        f"drilldown_capped={cue_listing.drilldown_capped}"
    )
    lines.append(
        f"Preset List — truncated={preset_listing.truncated}, "
        f"drilldown_capped={preset_listing.drilldown_capped}"
    )
    if magic_sheet is not None and not magic_sheet.placements_complete:
        expected, received, unseen = magic_sheet.placements_missing
        lines.append(
            "Magic Sheet — 배치 좌표가 전량이 아니다: "
            f"expected {expected if expected is not None else '?'}, "
            f"received {received}, unseen {unseen if unseen is not None else '?'}"
        )
    return tuple(lines)


_INDEX_STYLE = """
  body { font-family: -apple-system, "Segoe UI", Helvetica, Arial, sans-serif;
         margin: 24px; color: #1a1a1a; }
  h1 { font-size: 20px; margin-bottom: 4px; }
  h2 { font-size: 15px; margin: 20px 0 6px; }
  .meta { color: #555; font-size: 12px; margin-bottom: 16px; }
  table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }
  th, td { border: 1px solid #ccc; padding: 4px 8px; font-size: 12px; text-align: left; }
  th { background: #f0f0f0; }
  ul.incompleteness { margin: 0 0 20px; padding-left: 20px; font-size: 12px; }
  .status-생성됨 { color: #1a7a1a; }
  .status-조회 실패, .status-미배선 { color: #a00; }
  @media print {
    body { margin: 0.5in; }
    thead { display: table-header-group; }
    tr, .meta { break-inside: avoid; }
  }
"""


def _render_index_html(
    generated_at: str, documents: tuple[HandoverDocument, ...], incompleteness: tuple[str, ...]
) -> str:
    incompleteness_html = "".join(f"<li>{escape(line)}</li>\n" for line in incompleteness)
    row_parts: list[str] = []
    for doc in documents:
        if doc.path is not None:
            link_html = f'<a href="{escape(doc.filename)}">{escape(doc.title)}</a>'
        else:
            link_html = escape(doc.title)
        row_parts.append(
            "<tr>"
            f"<td>{link_html}</td>"
            f'<td class="status-{escape(doc.status)}">{escape(doc.status)}</td>'
            f"<td>{escape(doc.detail or '')}</td>"
            "</tr>\n"
        )
    rows_html = "".join(row_parts)
    body = (
        "<h1>Handover Pack</h1>\n"
        f'<div class="meta">Generated: {escape(generated_at)}</div>\n'
        "<h2>Incompleteness summary</h2>\n"
        f'<ul class="incompleteness">\n{incompleteness_html}</ul>\n'
        "<h2>Documents</h2>\n"
        "<table>\n<thead><tr><th>Document</th><th>Status</th><th>Detail</th></tr></thead>\n"
        f"<tbody>\n{rows_html}</tbody>\n</table>\n"
    )
    return (
        "<!doctype html>\n"
        '<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        "<title>Handover Pack</title>\n"
        f"<style>{_INDEX_STYLE}</style>\n</head>\n<body>\n{body}\n</body>\n</html>\n"
    )


def build_handover_pack(
    state_port,
    property_port=None,
    *,
    rig_paths: dict[str, str] | None = None,
    walk: WalkOutcome | None = None,
    directory: Path | None = None,
) -> HandoverPack:
    """Build all four paperwork documents plus an index, in one folder.

    Never raises on a single document's failure: a missing ``property_port``,
    an unreadable fixture inventory, or a pool the console never answered
    degrades that ONE document to a :data:`STATUS_UNWIRED`/
    :data:`STATUS_QUERY_FAILED` entry carrying why, while the other documents
    still generate. Only a failure to WRITE to disk (``OSError``) propagates —
    at that point nothing in the pack can be trusted to exist at all, so
    there is nothing partial left to report.

    ``walk`` threads the channel-width upper-bound
    ``server.prechk.footprint.WalkOutcome`` into the patch sheet exactly like
    ``build_patch_sheet`` itself: omitted, the patch sheet says nothing about
    a bound; present, ``build_patch_sheet`` folds it via
    ``footprint.upper_bound`` (never a raw ``max`` — see that module's
    docstring).
    """
    paths = rig_paths or {}
    target_dir = directory if directory is not None else resolve_handover_dir()

    patch_doc, patch_sheet = _patch_sheet_document(state_port, property_port, walk)
    if patch_sheet is not None:
        patch_path = write_paperwork_html(
            _PATCH_SHEET_FILENAME, render_patch_sheet(patch_sheet), directory=target_dir
        )
        patch_doc = replace(patch_doc, path=patch_path)

    cue_listing = build_cue_sheet(
        state_port,
        sequences_path=paths.get("sequences", DEFAULT_RIG_CONTEXT_PATHS["sequences"]),
    )
    cue_doc = _pool_listing_document(
        cue_listing, kind="cue_sheet", title="Cue Sheet", filename=_CUE_SHEET_FILENAME
    )
    if cue_doc.status == STATUS_GENERATED:
        cue_path = write_paperwork_html(
            _CUE_SHEET_FILENAME, render_cue_sheet(cue_listing), directory=target_dir
        )
        cue_doc = replace(cue_doc, path=cue_path)

    preset_listing = build_preset_list(
        state_port,
        preset_pools_path=paths.get("preset_pools", DEFAULT_RIG_CONTEXT_PATHS["preset_pools"]),
    )
    preset_doc = _pool_listing_document(
        preset_listing, kind="preset_list", title="Preset List", filename=_PRESET_LIST_FILENAME
    )
    if preset_doc.status == STATUS_GENERATED:
        preset_path = write_paperwork_html(
            _PRESET_LIST_FILENAME, render_preset_list(preset_listing), directory=target_dir
        )
        preset_doc = replace(preset_doc, path=preset_path)

    magic_doc, magic_sheet = _magic_sheet_document(state_port, property_port, paths)
    if magic_sheet is not None:
        magic_path = write_paperwork_html(
            _MAGIC_SHEET_FILENAME, render_magic_sheet(magic_sheet), directory=target_dir
        )
        magic_doc = replace(magic_doc, path=magic_path)

    generated_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    documents = (patch_doc, cue_doc, preset_doc, magic_doc)
    index_html = _render_index_html(
        generated_at,
        documents,
        _incompleteness_lines(patch_sheet, cue_listing, preset_listing, magic_sheet),
    )
    index_path = write_paperwork_html(_INDEX_FILENAME, index_html, directory=target_dir)

    return HandoverPack(index_path=index_path, documents=documents, generated_at=generated_at)


__all__ = [
    "HANDOVER_STATUSES",
    "STATUS_GENERATED",
    "STATUS_QUERY_FAILED",
    "STATUS_UNWIRED",
    "HandoverDocument",
    "HandoverPack",
    "build_handover_pack",
]
