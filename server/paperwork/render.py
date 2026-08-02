"""Self-contained HTML rendering for paperwork documents.

Every renderer here returns ONE string: a full ``<html>`` document with its
CSS inlined in a ``<style>`` block. No external stylesheet, script, font, or
image reference — the point of "paperwork" is that the file opens and prints
correctly with nothing else present.
"""

from __future__ import annotations

from html import escape

from server.paperwork.data import PatchSheet, PoolListing

_STYLE = """
  body { font-family: -apple-system, "Segoe UI", Helvetica, Arial, sans-serif;
         margin: 24px; color: #1a1a1a; }
  h1 { font-size: 20px; margin-bottom: 4px; }
  .meta { color: #555; font-size: 12px; margin-bottom: 16px; }
  table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }
  th, td { border: 1px solid #ccc; padding: 4px 8px; font-size: 12px; text-align: left; }
  th { background: #f0f0f0; }
  .pool-name { font-weight: bold; background: #fafafa; }
  .empty { color: #888; font-style: italic; }
  .unavailable { color: #a00; }
  .badge { display: inline-block; padding: 1px 6px; border-radius: 3px;
           font-size: 11px; margin-left: 6px; }
  .badge-truncated { background: #fff3cd; color: #7a5b00; }
  @media print { body { margin: 0.5in; } }
"""


def _page(title: str, body: str) -> str:
    return (
        "<!doctype html>\n"
        '<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        f"<title>{escape(title)}</title>\n"
        f"<style>{_STYLE}</style>\n</head>\n<body>\n{body}\n</body>\n</html>\n"
    )


def render_patch_sheet(sheet: PatchSheet) -> str:
    """Render a :class:`~server.paperwork.data.PatchSheet` to a printable
    self-contained HTML page."""
    rows_html = "".join(
        "<tr>"
        f"<td>{row.slot}</td>"
        f"<td>{escape(row.name or '')}</td>"
        f"<td>{row.universe if row.universe is not None else escape(row.patch_raw or '—')}</td>"
        f"<td>{row.address if row.address is not None else ''}</td>"
        f"<td>{escape(row.fixture_type or '')}</td>"
        f"<td>{escape(row.mode or '')}</td>"
        "</tr>\n"
        for row in sheet.rows
    )
    if not rows_html:
        rows_html = '<tr><td colspan="6" class="empty">No fixtures observed.</td></tr>\n'
    incomplete_badge = (
        '<span class="badge badge-truncated">incomplete</span>'
        if sheet.completeness != "complete"
        else ""
    )
    body = (
        f"<h1>Patch Sheet{incomplete_badge}</h1>\n"
        f'<div class="meta">Root: {escape(sheet.root)} · '
        f"{sheet.observed_count} of {sheet.child_count} fixtures observed · "
        f"completeness: {escape(sheet.completeness)}</div>\n"
        "<table>\n<thead><tr>"
        "<th>Slot</th><th>Name</th><th>Universe</th><th>Address</th>"
        "<th>Fixture Type</th><th>Mode</th>"
        "</tr></thead>\n<tbody>\n"
        f"{rows_html}"
        "</tbody>\n</table>\n"
    )
    return _page("Patch Sheet", body)


def _render_pool_listing(
    listing: PoolListing,
    *,
    title: str,
    pool_header: str,
    item_header: str,
) -> str:
    if listing.unavailable_reason is not None:
        body = (
            f"<h1>{escape(title)}</h1>\n"
            f'<div class="meta">Path: {escape(listing.path)}</div>\n'
            f'<p class="unavailable">Unavailable ({escape(listing.unavailable_reason)}): '
            f"{escape(listing.unavailable_detail or '')}</p>\n"
        )
        return _page(title, body)

    sections = []
    for pool in listing.pools:
        pool_label = escape(pool.name) + (f" (#{pool.no})" if pool.no is not None else "")
        if pool.contents_unavailable:
            rows_html = '<tr><td colspan="2" class="unavailable">contents unavailable</td></tr>\n'
        elif not pool.items:
            rows_html = (
                f'<tr><td colspan="2" class="empty">No {item_header.lower()} stored.</td></tr>\n'
            )
        else:
            rows_html = "".join(
                f"<tr><td>{item.no if item.no is not None else ''}</td>"
                f"<td>{escape(item.name)}</td></tr>\n"
                for item in pool.items
            )
        sections.append(
            "<table>\n<thead>"
            f'<tr><th colspan="2" class="pool-name">{pool_label}</th></tr>'
            f"<tr><th>#</th><th>{escape(item_header)}</th></tr>"
            f"</thead>\n<tbody>\n{rows_html}</tbody>\n</table>\n"
        )
    if not sections:
        sections.append(f'<p class="empty">No {pool_header.lower()} observed.</p>\n')

    truncated_badge = (
        '<span class="badge badge-truncated">truncated</span>' if listing.truncated else ""
    )
    capped_badge = (
        '<span class="badge badge-truncated">drilldown capped</span>'
        if listing.drilldown_capped
        else ""
    )
    body = (
        f"<h1>{escape(title)}{truncated_badge}{capped_badge}</h1>\n"
        f'<div class="meta">Path: {escape(listing.path)} · '
        f"{len(listing.pools)} {pool_header.lower()}</div>\n" + "".join(sections)
    )
    return _page(title, body)


def render_cue_sheet(listing: PoolListing) -> str:
    """Render a :class:`~server.paperwork.data.PoolListing` built from
    ``build_cue_sheet`` — one table per sequence, one row per cue."""
    return _render_pool_listing(
        listing, title="Cue Sheet", pool_header="Sequences", item_header="Cue"
    )


def render_preset_list(listing: PoolListing) -> str:
    """Render a :class:`~server.paperwork.data.PoolListing` built from
    ``build_preset_list`` — one table per preset-pool type, one row per
    stored preset."""
    return _render_pool_listing(
        listing, title="Preset List", pool_header="Preset Pools", item_header="Preset"
    )


__all__ = ["render_patch_sheet", "render_cue_sheet", "render_preset_list"]
