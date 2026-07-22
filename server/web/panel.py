"""Show-control panel server state (SHOWUI M2 — REQ-SHOWUI-001..005/022/023).

Three things live here, and deliberately nothing else:

1. :func:`build_catalog` — the rig-enumerated tile list, read through the SAME
   gate-audited ``state_port`` seam ``get_rig_context`` uses, reusing that
   tool's shape helpers so the real-`no` rule, the truncation signal and the
   unopened-vs-verified-empty distinction have exactly one implementation.
2. :class:`PinStore` — the chat-pinned tiles, persisted atomically to a JSON
   file under the per-user data dir so they survive a restart.
3. :class:`PanelStore` — the two halves composed, plus the membership predicate
   M3 checks a client-supplied target against before any bundle is built.

Chokepoint discipline (REQ-SHOWUI-007, AC-SHOWUI-006): this module holds NO
execution surface. It never imports the OSC send surface, and it never will —
firing a tile is M3's job and goes through ``gate.screen()``, the one screening
path. Reads ride the injected state port; writes go to a local file. Neither
can reach the console except through the gate that owns the link.
"""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from server.deploy.settings import user_data_dir
from server.llm.config import _CREDENTIAL_KEYS
from server.orchestrator.last_created import LastCreated
from server.orchestrator.ports import StateQueryPort
from server.orchestrator.tools import (
    REASON_UNREACHABLE,
    REASON_UNRESOLVED,
    drill_into,
    rig_object,
    rig_section,
)
from server.web.messages import PANEL_TARGET_KINDS, panel_item, panel_section

PIN_FILE_NAME = "panel_pins.json"

# The on-disk schema version. Bumped only on a BREAKING record change; an
# unreadable or unrecognised file degrades to an empty panel (see PinStore),
# never to a startup failure — a show must not be blocked by a pin file.
PIN_FILE_VERSION = 1

# The persisted fields of one pin. ``id`` is derived from the pair below and
# ``source`` is always "pin", so neither is stored: a stored ``id`` could drift
# out of agreement with the pair it is supposed to name.
_PIN_RECORD_FIELDS = ("kind", "target_kind", "target", "name", "appearance")

# Ceiling on second-level (page drill-down) queries per catalog build — the
# same reasoning as ``RIG_DRILLDOWN_QUERY_CAP``: each one is a UDP round trip
# through the gate + audit, so an unbounded walk would make a panel refresh
# cost scale with the size of the showfile.
PANEL_DRILLDOWN_QUERY_CAP = 16

# Every catalog tile's type badge. The rig snapshot carries a name and a number
# and nothing that separates a static look from a phaser, so the honest badge is
# the one that describes what the object IS (design.md §4 SEQ) rather than a
# guessed LOOK/FX. A wrong badge is cosmetic; a guessed one trains the operator
# to distrust all of them.
_CATALOG_ITEM_KIND = "sequence"

# Korean, because it is shown to the operator (PROTOCOL.md language rule).
PIN_SEED_UNAVAILABLE_MESSAGE = (
    "패널에 추가할 연출이 없습니다 — 채팅에서 연출을 먼저 만들어 주세요."
)


class PinSeedUnavailable(RuntimeError):
    """A pin was requested but the chat has not created a look yet.

    Explicit BY DESIGN (REQ-SHOWUI-004, acceptance.md §D edge case 7): silently
    ignoring the press leaves the operator pressing a button that does nothing
    and no way to learn why.
    """

    def __init__(self, message: str = PIN_SEED_UNAVAILABLE_MESSAGE) -> None:
        super().__init__(message)


class PinStoreError(ValueError):
    """A pin record was rejected before it could be written."""


@dataclass(frozen=True)
class SectionSpec:
    """One catalog source: where to read it and what it addresses."""

    name: str
    path: str
    target_kind: str
    drilldown: bool = False


# @MX:ANCHOR: [AUTO] the closed set of catalog sources. Consumed by the catalog
# builder, by the membership predicate through it, and (from M3) by every bundle
# the panel builds.
# @MX:REASON: REQ-SHOWUI-003 — "fixtures" is ABSENT here structurally, not
# filtered later: a fixture's `no` is its patch slot, not its fixture id, so a
# fixture tile would address the wrong thing on stage. A section can only become
# a tile source by being added to this tuple, and every `target_kind` here must
# be one the console actually fires (PANEL_TARGET_KINDS).
PANEL_CATALOG_SECTIONS = (
    SectionSpec(name="sequences", path="DataPool/Sequences", target_kind="sequence"),
    # A page's CHILDREN are the executors — the only surface that actually fires
    # a stored look — so this section's tiles come from the drill-down, not from
    # the pages themselves.
    SectionSpec(name="pages", path="DataPool/Pages", target_kind="executor", drilldown=True),
)


@dataclass(frozen=True)
class PanelCatalog:
    """One rig enumeration: the tiles, plus each section's own completeness.

    A refresh REPLACES this whole value rather than merging into the previous
    one (PROTOCOL.md "A refresh REPLACES the list"): merging would keep tiles
    for objects the showfile no longer has, and a tile that fires nothing is
    indistinguishable from a console that failed to answer.
    """

    items: tuple[dict, ...] = ()
    sections: tuple[dict, ...] = ()


def _reject_credential_keys(payload: object, *, context: str) -> None:
    """Refuse any credential-like key, at any depth, in a pin payload.

    Reuses the MVP provider loader's key list verbatim (``server.llm.config``)
    for the same reason the settings loader does: two lists would be two
    policies, and the weaker one would be the hole. Unlike that loader this one
    also walks LISTS, because the pin file's payload is a list of records.
    """
    if isinstance(payload, dict):
        for key, value in payload.items():
            if isinstance(key, str) and key.lower() in _CREDENTIAL_KEYS:
                raise PinStoreError(
                    f"credential-like key {key!r} found in {context} — the pin file "
                    "never carries credentials"
                )
            _reject_credential_keys(value, context=f"{context}.{key}")
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            _reject_credential_keys(value, context=f"{context}[{index}]")


def pin_store_path(file_name: str = PIN_FILE_NAME) -> Path:
    """The default pin file: ``<user-data-dir>/panel_pins.json``.

    The per-user DATA dir, not the config dir and not the bundle: a packaged app
    is read-only, and pins are runtime state the operator creates, not settings
    they configure.
    """
    return user_data_dir() / file_name


class PinStore:
    """Chat-pinned tiles, persisted atomically and read fail-open.

    Ordering is append-only and never sorted (REQ-SHOWUI-005/017): a tile that
    moves under the operator's finger mid-show is a misfire waiting to happen.
    """

    def __init__(self, path: Path | str | None = None) -> None:
        self._path = Path(path) if path is not None else pin_store_path()
        self._pins: list[dict] = self._load()

    @property
    def path(self) -> Path:
        return self._path

    def items(self) -> list[dict]:
        """The pinned tiles, in pin order."""
        return [dict(pin) for pin in self._pins]

    def contains(self, target_kind: str, target: int) -> bool:
        return any(
            pin["target_kind"] == target_kind and pin["target"] == target for pin in self._pins
        )

    def add(self, item: dict) -> bool:
        """Append one tile and persist. Returns ``False`` if already pinned.

        The incoming dict is credential-checked BEFORE it is normalised, so an
        unexpected ``api_key`` is refused rather than quietly dropped: a caller
        that put one there has a defect worth surfacing.
        """
        _reject_credential_keys(item, context="pin item")
        pin = self._normalize(item)
        if self.contains(pin["target_kind"], pin["target"]):
            return False
        pins = [*self._pins, pin]
        self._save(pins)
        self._pins = pins  # committed only after the file swap succeeded
        return True

    def remove(self, target_kind: str, target: int) -> bool:
        """Unpin one tile and persist the removal (REQ-SHOWUI-023)."""
        pins = [
            pin
            for pin in self._pins
            if not (pin["target_kind"] == target_kind and pin["target"] == target)
        ]
        if len(pins) == len(self._pins):
            return False
        self._save(pins)
        self._pins = pins
        return True

    # -- internals ---------------------------------------------------------------

    @staticmethod
    def _normalize(item: dict) -> dict:
        """Rebuild the tile through the frozen item constructor.

        Every enum is re-validated here, so a record that cannot be addressed
        correctly is never stored and never restored.
        """
        name = item.get("name", "")
        appearance = item.get("appearance")
        if not isinstance(name, str):
            raise PinStoreError(f"pin name must be a string, got {name!r}")
        if appearance is not None and not isinstance(appearance, str):
            raise PinStoreError(
                f"pin appearance must be a colour string or null, got {appearance!r}"
            )
        try:
            return panel_item(
                kind=item.get("kind"),
                target_kind=item.get("target_kind"),
                target=item.get("target"),
                name=name,
                appearance=appearance,
                source="pin",
            )
        except ValueError as error:
            raise PinStoreError(str(error)) from error

    def _load(self) -> list[dict]:
        """Read the pin file, degrading to an empty panel on ANY defect.

        Fail-OPEN on read (acceptance.md §D edge case 9): a corrupt, truncated
        or hand-edited file must not stop the app from starting a show. The next
        write regenerates a valid file. Fail-open is safe here precisely because
        a pin grants no capability — every tile is still screened by the gate
        before anything reaches the console.

        Partial trust is refused on purpose: one unreadable record makes the
        WHOLE file suspect, and a silently half-restored panel would leave the
        operator reaching for a tile that is not there.
        """
        try:
            raw = self._path.read_text(encoding="utf-8")
        except OSError:
            return []
        try:
            data = json.loads(raw)
        except ValueError:
            return []
        if not isinstance(data, dict):
            return []
        records = data.get("pins")
        if not isinstance(records, list):
            return []
        if not all(isinstance(record, dict) for record in records):
            return []
        try:
            _reject_credential_keys(data, context=str(self._path))
            return [self._normalize(record) for record in records]
        except PinStoreError:
            return []

    def _save(self, pins: list[dict]) -> None:
        """Write the pin file atomically (temp in the SAME dir + ``os.replace``).

        Mirrors ``server/deploy/settings.py::save_user_settings``: a crash
        mid-write leaves the previous file untouched instead of a half-written
        one that the fail-open read would then silently discard.
        """
        payload = json.dumps(
            {
                "version": PIN_FILE_VERSION,
                "pins": [{field: pin[field] for field in _PIN_RECORD_FIELDS} for pin in pins],
            },
            ensure_ascii=False,
            indent=2,
        )
        self._path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(
            dir=str(self._path.parent), prefix=".panel-pins-", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
            os.replace(tmp_name, self._path)
        except BaseException:
            with contextlib.suppress(OSError):
                os.unlink(tmp_name)
            raise


def _tiles(objects: list[dict], target_kind: str) -> list[dict]:
    """Turn resolved rig objects into tiles, skipping the unaddressable ones.

    An object the responder could not number arrives without ``no`` (see
    ``rig_object``). That absence is meaningful: there is no address, so there
    is no tile. Inventing one from the list position is the exact defect
    REQ-SHOWUI-003 exists to prevent.
    """
    tiles = []
    for obj in objects:
        number = obj.get("no")
        if number is None:
            continue
        tiles.append(
            panel_item(
                kind=_CATALOG_ITEM_KIND,
                target_kind=target_kind,
                target=number,
                name=str(obj.get("name", "")),
                source="auto",
            )
        )
    return tiles


def build_catalog(
    state_port: StateQueryPort,
    *,
    paths: dict[str, str] | None = None,
    query_cap: int = PANEL_DRILLDOWN_QUERY_CAP,
) -> PanelCatalog:
    """Enumerate the console's fireable objects into panel tiles.

    ``paths`` overrides a section's object-tree path by name, for the same
    reason ``rig_paths`` exists: a showfile that keeps its pools elsewhere must
    be configurable rather than silently empty.

    Failure classification is the rig-context one and stays SPLIT
    (REQ-SHOWUI-002): if any sibling section answered, the console is
    demonstrably reachable and a failing path is a configuration defect
    (``path_not_resolved``); if nothing answered, no path can be blamed
    (``console_unreachable``). Merging the two is how two dead default rig paths
    survived a whole stage unnoticed.
    """
    overrides = dict(paths or {})
    items: list[dict] = []
    sections: list[dict | None] = []
    failed: list[tuple[int, str]] = []
    resolved = 0
    budget = query_cap

    for spec in PANEL_CATALOG_SECTIONS:
        path = overrides.get(spec.name, spec.path)
        try:
            payload = state_port.query_state(path)
        except Exception:
            # Position held; classified below, once every section's outcome is
            # known — the reason depends on whether ANY sibling answered.
            failed.append((len(sections), spec.name))
            sections.append(None)
            continue
        resolved += 1
        children = payload.get("children", [])
        objects = [rig_object(child) for child in children if isinstance(child, dict)]
        entry = rig_section(objects, payload)
        contents_unavailable = False
        if spec.drilldown:
            budget = drill_into(state_port, objects, path, entry, budget)
            contents_unavailable = any(obj.get("contents_unavailable") for obj in objects)
            for obj in objects:
                items.extend(_tiles(obj.get("contents", []), spec.target_kind))
        else:
            items.extend(_tiles(objects, spec.target_kind))
        sections.append(
            panel_section(
                name=spec.name,
                status="ok",
                truncated=bool(entry.get("truncated")),
                drilldown_capped=bool(entry.get("drilldown_capped")),
                contents_unavailable=contents_unavailable,
            )
        )

    status = REASON_UNRESOLVED if resolved else REASON_UNREACHABLE
    for index, name in failed:
        sections[index] = panel_section(name=name, status=status)
    return PanelCatalog(items=tuple(items), sections=tuple(s for s in sections if s is not None))


class PanelStore:
    """The panel's server-side truth: pinned tiles + the last rig enumeration."""

    def __init__(
        self,
        *,
        state_port: StateQueryPort,
        pins: PinStore,
        catalog_paths: dict[str, str] | None = None,
    ) -> None:
        self.state_port = state_port
        self.pins = pins
        self._catalog_paths = catalog_paths
        # No catalog until one is actually read. An empty panel is honest; a
        # guessed one is not.
        self._catalog = PanelCatalog()
        self._enumerated = False

    @property
    def catalog(self) -> PanelCatalog:
        return self._catalog

    def refresh_catalog(self) -> PanelCatalog:
        """Re-read the rig. REPLACES the previous enumeration, never merges."""
        self._catalog = build_catalog(self.state_port, paths=self._catalog_paths)
        self._enumerated = True
        return self._catalog

    def items(self) -> list[dict]:
        """Every tile, in grid order: pins first, then the rig enumeration.

        Pins lead because their positions must be the most stable thing on the
        grid (REQ-SHOWUI-017). They are the operator's own deliberate choices,
        while the auto half is replaced wholesale on every refresh — if the auto
        tiles came first, adding one sequence to the showfile would shift every
        pinned tile out from under the operator's finger.
        """
        return [*self.pins.items(), *self._catalog.items]

    def sections(self) -> list[dict]:
        return list(self._catalog.sections) if self._enumerated else []

    # @MX:ANCHOR: [AUTO] the membership half of REQ-SHOWUI-022. Built and tested
    # in M2; M3 calls it on every panel_execute / panel_stop / panel_unpin before
    # a bundle exists.
    # @MX:REASON: the target is client-controlled. Parse-time validation proves
    # it is a positive integer, not that it names a real object — without this
    # check a well-formed "Executor 9999" would reach gate.screen() as a
    # perfectly plausible command and fire at nothing (or at something).
    def contains(self, target_kind: str, target: int) -> bool:
        """True when this (class, number) pair is a tile the panel actually has."""
        if target_kind not in PANEL_TARGET_KINDS:
            return False
        if self.pins.contains(target_kind, target):
            return True
        return any(
            item["target_kind"] == target_kind and item["target"] == target
            for item in self._catalog.items
        )

    def pin_from_seed(self, seed: LastCreated | None) -> dict:
        """Pin the chat's last-created look (REQ-SHOWUI-004).

        The executor is preferred as the ADDRESS when the look was assigned to
        one — that is the surface which actually fires it — while the name keeps
        naming the sequence, which is the look's identity. With no seed at all
        this raises rather than returning ``None``: see :class:`PinSeedUnavailable`.
        """
        if seed is None or seed.sequence is None:
            raise PinSeedUnavailable()
        if seed.executor is not None:
            target_kind, target = "executor", seed.executor
        else:
            target_kind, target = "sequence", seed.sequence
        item = panel_item(
            kind=_CATALOG_ITEM_KIND,
            target_kind=target_kind,
            target=target,
            name=f"Sequence {seed.sequence}",
            source="pin",
        )
        self.pins.add(item)
        return item

    def unpin(self, target_kind: str, target: int) -> bool:
        """Remove one pinned tile; the removal is persisted (REQ-SHOWUI-023)."""
        return self.pins.remove(target_kind, target)
