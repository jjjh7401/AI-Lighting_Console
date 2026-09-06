"""Director-timeline library — named, versioned saves of the runbook timeline.

여러 곡을 미리 계획하고 버전을 나눠 보관했다가 다시 불러오는 저장소
(user request, 2026-08-14). Each entry is a full ``_song_timeline_payload``
projection plus bookkeeping (id / name / saved_at). The same name MAY appear
more than once on purpose — a name is a song, an entry is a version.

Persistence mirrors ``server.web.panel.PinStore`` and
``server.web.session.SongTimelineStore``: atomic same-dir temp + ``os.replace``
on write, fail-OPEN on read (a corrupt library degrades to empty, never a
startup failure). Safe to fail open because an entry is a read-only review
projection — loading one grants no console capability; every console write
still rides the approval gate.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import tempfile
import uuid
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path

__all__ = ["SongTimelineLibrary", "timeline_entry_summary"]

_LIBRARY_FILE_VERSION = 1


def timeline_entry_summary(entry: dict) -> dict:
    """The list-view projection of one entry — no section payload, so the
    library listing stays cheap even with many saved versions."""
    timeline = entry.get("timeline") or {}
    return {
        "id": entry.get("id"),
        "name": entry.get("name"),
        "saved_at": entry.get("saved_at"),
        "song_title": timeline.get("song_title"),
        "sequence_number": timeline.get("sequence_number"),
        "lifecycle": timeline.get("lifecycle"),
        "section_count": len(timeline.get("sections") or []),
    }


class SongTimelineLibrary:
    """Named timeline saves. Path-less instances (tests, bare WebDeps) stay
    memory-only; serve.py wires the persistent JSON path."""

    def __init__(
        self,
        path: Path | str | None = None,
        *,
        seed: Sequence[Mapping[str, object]] = (),
    ) -> None:
        """``seed`` 는 앱이 기본으로 싣고 다니는 항목들(예: 정본 Sugar 큐시트).

        저장 파일에 같은 ``id`` 가 이미 있으면 심지 않는다 — 감독이 그 위에 저장한
        판이 있으면 그 판이 이긴다. 심는 자리는 목록 앞이라 ``items()`` 의
        최신순 정렬에서 가장 오래된 것으로 내려간다. 읽기 경로의 fail-open 은
        그대로다: 파일이 없거나 깨져도 예외 없이 시드만 남는다.
        """
        self._path = Path(path) if path is not None else None
        self._seed = [dict(entry) for entry in seed]
        self._entries: list[dict] = self._load()

    # -- reads -----------------------------------------------------------------

    def items(self) -> list[dict]:
        """Every entry, newest first (a rehearsal reaches for the latest
        version of a song before an old one)."""
        return [dict(entry) for entry in reversed(self._entries)]

    def get(self, entry_id: str) -> dict | None:
        for entry in self._entries:
            if entry.get("id") == entry_id:
                return dict(entry)
        return None

    # -- writes ----------------------------------------------------------------

    def save(self, name: str, timeline: dict) -> dict:
        cleaned = (name or "").strip()
        if not cleaned:
            raise ValueError("timeline name must be non-empty")
        if not isinstance(timeline, dict) or not timeline:
            raise ValueError("timeline payload must be a non-empty dict")
        entry = {
            "id": uuid.uuid4().hex[:12],
            "name": cleaned,
            "saved_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "timeline": timeline,
        }
        entries = [*self._entries, entry]
        self._persist(entries)
        self._entries = entries  # committed only after the file swap succeeded
        return dict(entry)

    def auto_save(self, base_name: str, timeline: dict) -> dict:
        """Version-stamped snapshot: ``<base> (자동 vN)`` where N counts up
        per base name (handoff 2026-08-15 priority 3 — every approved console
        store leaves a recoverable library version without a manual save)."""
        base = (base_name or "").strip()
        if not base:
            raise ValueError("timeline base name must be non-empty")
        stamp = re.compile(rf"^{re.escape(base)} \(자동 v(?P<n>\d+)\)$")
        versions = [
            int(match.group("n"))
            for entry in self._entries
            if (match := stamp.match(str(entry.get("name") or ""))) is not None
        ]
        return self.save(f"{base} (자동 v{max(versions, default=0) + 1})", timeline)

    def remove(self, entry_id: str) -> bool:
        entries = [entry for entry in self._entries if entry.get("id") != entry_id]
        if len(entries) == len(self._entries):
            return False
        self._persist(entries)
        self._entries = entries
        return True

    # -- internals ---------------------------------------------------------------

    def _seeded(self, entries: list[dict]) -> list[dict]:
        present = {entry.get("id") for entry in entries}
        missing = [dict(entry) for entry in self._seed if entry.get("id") not in present]
        return [*missing, *entries]

    def _load(self) -> list[dict]:
        if self._path is None:
            return self._seeded([])
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return self._seeded([])
        if not isinstance(data, dict):
            return self._seeded([])
        entries = data.get("entries")
        if not isinstance(entries, list):
            return self._seeded([])
        kept: list[dict] = []
        for entry in entries:
            if (
                isinstance(entry, dict)
                and isinstance(entry.get("id"), str)
                and isinstance(entry.get("name"), str)
                and isinstance(entry.get("timeline"), dict)
            ):
                kept.append(entry)
        return self._seeded(kept)

    def _persist(self, entries: list[dict]) -> None:
        if self._path is None:
            return
        try:
            body = json.dumps(
                {"version": _LIBRARY_FILE_VERSION, "entries": entries},
                ensure_ascii=False,
            )
            self._path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp_name = tempfile.mkstemp(
                dir=str(self._path.parent), prefix=".timeline-library-", suffix=".tmp"
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    handle.write(body)
                os.replace(tmp_name, self._path)
            except BaseException:
                with contextlib.suppress(OSError):
                    os.unlink(tmp_name)
                raise
        except (OSError, TypeError, ValueError):
            # Best-effort persistence: the in-memory library keeps serving
            # this process even on a read-only disk.
            pass
