"""Self-contained HTML rendering for paperwork documents.

Every renderer here returns ONE string: a full ``<html>`` document with its
CSS inlined in a ``<style>`` block. No external stylesheet, script, font, or
image reference — the point of "paperwork" is that the file opens and prints
correctly with nothing else present.
"""

from __future__ import annotations

from html import escape

from server.paperwork.data import MagicSheet, PatchSheet, PoolListing

_STYLE = """
  body { font-family: -apple-system, "Segoe UI", Helvetica, Arial, sans-serif;
         margin: 24px; color: #1a1a1a; }
  h1 { font-size: 20px; margin-bottom: 4px; }
  h2 { font-size: 15px; margin: 20px 0 6px; }
  .meta { color: #555; font-size: 12px; margin-bottom: 16px; }
  table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }
  th, td { border: 1px solid #ccc; padding: 4px 8px; font-size: 12px; text-align: left; }
  th { background: #f0f0f0; }
  .pool-name { font-weight: bold; background: #fafafa; }
  .empty { color: #888; font-style: italic; }
  .unavailable { color: #a00; }
  .tiles { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px; }
  .tile { border: 1px solid #ccc; border-radius: 3px; padding: 3px 8px; font-size: 12px; }
  .caveat { border-left: 3px solid #a00; background: #fff5f5; color: #7a0000;
            padding: 8px 10px; font-size: 12px; margin-bottom: 16px; }
  .badge { display: inline-block; padding: 1px 6px; border-radius: 3px;
           font-size: 11px; margin-left: 6px; }
  .badge-truncated { background: #fff3cd; color: #7a5b00; }
  /* 미번역 핸들 — 번역된 행과 눈으로 갈려야 한다. 색만으로 구별하지 않는다:
     테두리와 「미번역」이라는 글자가 함께 실려, 흑백 인쇄와 색을 못 가리는
     독자에게도 남는다. */
  .badge-untranslated { background: #fdecea; color: #7a1c12; border: 1px solid #d9534f; }
  td.untranslated { background: #fffafa; }
  @media print {
    body { margin: 0.5in; box-shadow: none; }
    thead { display: table-header-group; }
    tr, .meta, .caveat { break-inside: avoid; }
    * { print-color-adjust: exact; -webkit-print-color-adjust: exact; }
  }
"""


def _page(title: str, body: str) -> str:
    return (
        "<!doctype html>\n"
        '<html lang="ko">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{escape(title)}</title>\n"
        f"<style>{_STYLE}</style>\n</head>\n<body>\n"
        f'<div class="sheet">\n{body}\n</div>\n</body>\n</html>\n'
    )


def _bound_meta(sheet: PatchSheet) -> str:
    """The channel-width upper-bound line, or nothing.

    ``bound is None and bound_unavailable is None`` (the ``walk=None``
    default) renders NO line at all — an unasked question is not the same as
    an unanswered one, and printing "none" there would misreport a bound that
    was simply never sought. The asymmetric qualifier stays in the SAME
    sentence as the value on purpose (OVERLAP-001 M5): a reader who reads
    only the first clause must still see the "below is unsettled" half.
    """
    if sheet.bound is not None:
        source = f" (source: {escape(sheet.bound_source)})" if sheet.bound_source else ""
        return (
            '<div class="meta">채널폭 상계: '
            f"{sheet.bound}{source} — 이 값 이상의 간격은 겹침 없음 확인; "
            "이하는 미확정.</div>\n"
        )
    if sheet.bound_unavailable is not None:
        return (
            '<div class="meta unavailable">채널폭 상계 미확인: '
            f"{escape(sheet.bound_unavailable)}</div>\n"
        )
    return ""


def _fixture_type_cell(row) -> str:
    """The Fixture Type cell, carrying the untranslated fact when there is one.

    REQ-READBACK2-008: honesty won at the READ boundary is dropped at the
    PRINT boundary unless it is rendered here — a reader holding the sheet
    cannot otherwise tell a translated name from a handle nobody could name.

    The badge carries the REASON verbatim, not a generic "failed": the reasons
    are kept apart upstream precisely because each calls for a different action
    (re-read the console vs. check the rig), and collapsing them here would
    undo that at the last step. It is added ONLY to an untranslated row, which
    is what makes the two kinds of row distinguishable at a glance.
    """
    value = escape(row.fixture_type or "")
    reason = row.fixture_type_untranslated
    if reason is None:
        return f"<td>{value}</td>"
    return (
        '<td class="untranslated">'
        f"{value}"
        f'<span class="badge badge-untranslated">미번역: {escape(reason)}</span>'
        "</td>"
    )


def render_patch_sheet(sheet: PatchSheet) -> str:
    """Render a PatchSheet to a printable self-contained HTML page."""
    rows_html = "".join(
        "<tr>"
        f"<td>{row.slot}</td>"
        f"<td>{escape(row.name or '')}</td>"
        f"<td>{row.universe if row.universe is not None else escape(row.patch_raw or '—')}</td>"
        f"<td>{row.address if row.address is not None else ''}</td>"
        f"{_fixture_type_cell(row)}"
        f"<td>{escape(row.mode or '')}</td>"
        "</tr>\n"
        for row in sheet.rows
    )
    if not rows_html:
        rows_html = '<tr><td colspan="6" class="empty">관측된 픽스처 없음</td></tr>\n'
    incomplete_badge = (
        ' <span class="badge badge-truncated">incomplete</span>'
        if sheet.completeness != "complete"
        else ""
    )
    body = (
        f"<h1>Patch Sheet{incomplete_badge}</h1>\n"
        f'<div class="meta">Root: {escape(sheet.root)} · '
        f"{sheet.observed_count} of {sheet.child_count} fixtures observed · "
        f"completeness: {escape(sheet.completeness)}</div>\n"
        f"{_bound_meta(sheet)}"
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
            f'<div class="meta">{escape(listing.path)}</div>\n'
            f'<p class="unavailable">조회 불가 ({escape(listing.unavailable_reason)}): '
            f"{escape(listing.unavailable_detail or '')}</p>\n"
        )
        return _page(title, body)

    sections = []
    for pool in listing.pools:
        pool_label = escape(pool.name) + (f" (#{pool.no})" if pool.no is not None else "")
        if pool.contents_unavailable:
            rows_html = '<tr><td colspan="2" class="unavailable">내용 판독 불가</td></tr>\n'
        elif not pool.items:
            rows_html = f'<tr><td colspan="2" class="empty">저장된 {item_header} 없음</td></tr>\n'
        else:
            rows_html = "".join(
                f"<tr><td>{item.no if item.no is not None else ''}</td>"
                f"<td>{escape(item.name)}</td></tr>\n"
                for item in pool.items
            )
        sections.append(
            '<table class="pool-table">\n'
            "<colgroup>"
            '<col class="col-no"><col class="col-val">'
            "</colgroup>\n"
            "<thead>"
            f'<tr><th colspan="2" class="pool-name">{pool_label}</th></tr>'
            f"<tr><th>#</th><th>{escape(item_header)}</th></tr>"
            f"</thead>\n<tbody>\n{rows_html}</tbody>\n</table>\n"
        )
    if not sections:
        sections.append(f'<p class="empty">{pool_header} 없음</p>\n')

    truncated_badge = (
        ' <span class="badge badge-truncated">truncated</span>' if listing.truncated else ""
    )
    capped_badge = (
        ' <span class="badge badge-truncated">drilldown capped</span>'
        if listing.drilldown_capped
        else ""
    )
    body = (
        '<div class="title-row">'
        f"<h1>{escape(title)}</h1>{truncated_badge}{capped_badge}</div>\n"
        f'<div class="meta">{escape(listing.path)} · '
        f"{len(listing.pools)} {pool_header.lower()}</div>\n" + "".join(sections)
    )
    return _page(title, body)


def render_cue_sheet(listing: PoolListing) -> str:
    """Render a PoolListing from build_cue_sheet."""
    return _render_pool_listing(
        listing, title="Cue Sheet", pool_header="Sequences", item_header="Cue"
    )


def render_preset_list(listing: PoolListing) -> str:
    """Render a PoolListing from build_preset_list."""
    return _render_pool_listing(
        listing,
        title="Preset List",
        pool_header="Preset Pools",
        item_header="Preset",
    )


def render_magic_sheet(sheet: MagicSheet) -> str:
    """Render the REDUCED magic sheet: names, patch summary, placement table.

    The membership caveat is emitted BEFORE the group tiles and styled as a
    caveat rather than as metadata. Group names sitting above a fixture
    coordinate table is an open invitation to read membership off adjacency,
    and the one thing this document cannot support is that reading — see
    ``server.paperwork.data.GROUP_MEMBERSHIP_UNAVAILABLE``.
    """
    parts = ["<h1>Magic Sheet (reduced)</h1>\n"]

    if sheet.patch is not None:
        parts.append(
            '<div class="meta">Patch: '
            f"{sheet.patch.observed_count} of {sheet.patch.child_count} fixtures observed · "
            f"completeness: {escape(sheet.patch.completeness)}</div>\n"
        )
    else:
        parts.append(
            '<div class="meta unavailable">Patch summary unavailable: '
            f"{escape(sheet.patch_unavailable or '')}</div>\n"
        )

    parts.append("<h2>Groups</h2>\n")
    parts.append(f'<div class="caveat">{escape(sheet.group_membership_unavailable)}</div>\n')
    if sheet.groups_unavailable_reason is not None:
        parts.append(
            '<p class="unavailable">The group pool did not arrive: '
            f"{escape(sheet.groups_unavailable_reason)}</p>\n"
        )
    elif not sheet.group_names:
        parts.append('<p class="empty">No groups in this showfile.</p>\n')
    else:
        tiles = "".join(f'<span class="tile">{escape(name)}</span>' for name in sheet.group_names)
        parts.append(f'<div class="tiles">{tiles}</div>\n')

    parts.append("<h2>Preset pools</h2>\n")
    if sheet.presets_unavailable_reason is not None:
        parts.append(
            '<p class="unavailable">The preset pools did not arrive: '
            f"{escape(sheet.presets_unavailable_reason)}</p>\n"
        )
    elif not sheet.preset_names:
        parts.append('<p class="empty">No preset pools in this showfile.</p>\n')
    else:
        tiles = "".join(f'<span class="tile">{escape(name)}</span>' for name in sheet.preset_names)
        parts.append(f'<div class="tiles">{tiles}</div>\n')

    parts.append("<h2>Placement</h2>\n")
    expected, received, unseen = sheet.placements_missing
    if not sheet.placements_complete:
        # The shortfall as arithmetic, not as an adjective (TRUNCATE-001
        # REQ-004): a plan view gives a reader no way to notice an absent
        # fixture, so the count has to say how many are absent.
        parts.append(
            '<div class="caveat">배치 좌표가 전량이 아니다 — '
            f"expected {expected if expected is not None else '?'}, "
            f"received {received}, "
            f"unseen {unseen if unseen is not None else '?'}. "
            "아래 평면은 리그 전체가 아니다.</div>\n"
        )
    rows = "".join(
        "<tr>"
        f"<td>{row.fid if row.fid is not None else ''}</td>"
        f"<td>{escape(row.name)}</td>"
        f"<td>{row.x:g}</td><td>{row.y:g}</td><td>{row.z:g}</td>"
        "</tr>\n"
        for row in sheet.placements
    )
    if not rows:
        rows = '<tr><td colspan="5" class="empty">No coordinates read.</td></tr>\n'
    parts.append(
        "<table>\n<thead><tr>"
        "<th>FID</th><th>Name</th><th>X</th><th>Y</th><th>Z</th>"
        "</tr></thead>\n<tbody>\n"
        f"{rows}"
        "</tbody>\n</table>\n"
    )
    if sheet.placements_unreadable:
        items = "".join(f"<li>{escape(line)}</li>\n" for line in sheet.placements_unreadable)
        parts.append(f'<h2>Unreadable</h2>\n<ul class="unavailable">\n{items}</ul>\n')

    return _page("Magic Sheet", "".join(parts))


__all__ = [
    "render_patch_sheet",
    "render_cue_sheet",
    "render_preset_list",
    "render_magic_sheet",
]
